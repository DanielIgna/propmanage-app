"""Motor-compatible MongoDB facade over Supabase Postgres (schema `app`, one JSONB table per collection).

How a call is executed:
  1. The Mongo filter is translated into a SQL WHERE clause that selects a SUPERSET of
     the matching rows (indexed via GIN jsonb_path_ops / expression indexes). When the
     translation is exact, sort/skip/limit/count are pushed down to SQL too.
  2. The candidate documents are loaded into a throw-away in-memory mongomock collection,
     which applies the real Mongo semantics (filter, projection, sort, update operators,
     aggregation pipelines, upserts, find_one_and_*).
  3. Writes run in one transaction with row locks (SELECT ... FOR UPDATE); the changed,
     inserted and deleted documents are diffed and persisted.

Documents are stored as MongoDB Extended JSON (relaxed): ObjectId -> {"$oid"}, datetime -> {"$date"}.
"""
import asyncio
import logging
import re
import time
from typing import Any, Optional

import asyncpg
import mongomock
from bson import ObjectId, json_util
from bson.json_util import JSONMode, JSONOptions
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

log = logging.getLogger("propmanage.pgmongo")
RELAXED = JSONOptions(json_mode=JSONMode.RELAXED)
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_IN_MAX = 200
_ARRAY_TTL = 300.0
_ARRAY_CACHE: dict = {}


def _enc(value: Any) -> str:
    return json_util.dumps(value, json_options=RELAXED)


def _dec(text: str) -> dict:
    return json_util.loads(text)


def _id_key(value: Any) -> str:
    return str(value)


def _is_plain_scalar(v: Any) -> bool:
    return isinstance(v, (str, int, float, bool, ObjectId)) and not (isinstance(v, float) and v != v)


# --------------------------------------------------------------------------- SQL prefilter

class _Sql:
    """Accumulates SQL parameters while translating a filter."""

    def __init__(self):
        self.params: list = []

    def p(self, value: Any) -> str:
        self.params.append(value)
        return f"${len(self.params)}"


class _InlineSql(_Sql):
    """Renders parameters as SQL literals (DDL such as partial index predicates can't take $n)."""

    def p(self, value: Any) -> str:
        if isinstance(value, list):
            return "array[" + ", ".join(self.p(v) for v in value) + "]"
        return "'" + str(value).replace("'", "''") + "'"


_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _top_key(key: str) -> bool:
    return "." not in key and not key.startswith("$")


def _contains(sql: _Sql, key: str, value: Any) -> str:
    """Field equals scalar `value` OR is an array containing it (Mongo equality semantics)."""
    a = sql.p(_enc({key: value}))
    b = sql.p(_enc({key: [value]}))
    return f"(data @> {a}::jsonb or data @> {b}::jsonb)"


def _in_list(sql: _Sql, key: str, values: list) -> str:
    """Field equals one of `values`, or is an array containing one of them."""
    arr = sql.p([_enc(v) for v in values])
    f = f"(data->{sql.p(key)}::text)"
    return (f"(case jsonb_typeof({f}) when 'array' then exists (select 1 from jsonb_array_elements({f}) e "
            f"where e = any({arr}::jsonb[])) else coalesce({f} = any({arr}::jsonb[]), false) end)")


def _range(sql: _Sql, key: str, op: str, value: Any) -> Optional[str]:
    sym = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<="}[op]
    f = f"data->{sql.p(key)}::text"
    if isinstance(value, str):
        v = sql.p(value) + "::text"
        elem = f"(jsonb_typeof(e) = 'string' and (e #>> '{{}}') collate \"C\" {sym} {v} collate \"C\")"
        scalar = f"((({f}) #>> '{{}}') collate \"C\" {sym} {v} collate \"C\")"
        kind = "string"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        v = sql.p(str(value))
        elem = f"(jsonb_typeof(e) = 'number' and (e #>> '{{}}')::numeric {sym} {v}::text::numeric)"
        scalar = f"((({f}) #>> '{{}}')::numeric {sym} {v}::text::numeric)"
        kind = "number"
    else:
        return None
    return (f"(case jsonb_typeof({f}) when '{kind}' then {scalar} "
            f"when 'array' then exists (select 1 from jsonb_array_elements({f}) e where {elem}) "
            f"else false end)")


def _field(sql: _Sql, key: str, cond: Any) -> tuple[str, bool]:
    """Translate one `key: condition`. Returns (sql, exact)."""
    if key == "_id":
        if _is_plain_scalar(cond):
            return f"id = {sql.p(_id_key(cond))}", True
        if isinstance(cond, dict) and set(cond) == {"$in"} and all(_is_plain_scalar(v) for v in cond["$in"]):
            return f"id = any({sql.p([_id_key(v) for v in cond['$in']])}::text[])", True
        return "true", False
    if not _top_key(key):
        return "true", False
    if cond is None:
        n = sql.p(_enc({key: [None]}))
        return f"(coalesce(data->{sql.p(key)}::text, 'null'::jsonb) = 'null'::jsonb or data @> {n}::jsonb)", True
    if _is_plain_scalar(cond):
        return _contains(sql, key, cond), True
    if not isinstance(cond, dict) or not cond or not all(k.startswith("$") for k in cond):
        return "true", False  # exact sub-document / list equality: let mongomock decide

    parts, exact = [], True
    for op, val in cond.items():
        if op == "$eq" and _is_plain_scalar(val):
            parts.append(_contains(sql, key, val))
        elif op == "$ne" and _is_plain_scalar(val):
            parts.append(f"not {_contains(sql, key, val)}")
        elif op in ("$in", "$nin") and isinstance(val, list) and 0 < len(val) <= _IN_MAX \
                and all(_is_plain_scalar(v) for v in val):
            if len(val) <= 3:  # few values: GIN-indexable containment
                clause = "(" + " or ".join(_contains(sql, key, v) for v in val) + ")"
            else:  # many values: read the field once (large docs are expensive to re-read)
                clause = _in_list(sql, key, val)
            parts.append(clause if op == "$in" else f"not {clause}")
        elif op in ("$gt", "$gte", "$lt", "$lte"):
            clause = _range(sql, key, op, val)
            if clause:
                parts.append(clause)
            else:
                exact = False
        elif op == "$exists":
            parts.append(f"{'' if val else 'not '}(data ? {sql.p(key)}::text)")
        else:
            exact = False  # $regex, $elemMatch, $size, $not, ... -> mongomock
    return (" and ".join(parts) if parts else "true"), exact


def _where(sql: _Sql, flt: Optional[dict]) -> tuple[str, bool]:
    if not flt:
        return "true", True
    parts, exact = [], True
    for key, cond in flt.items():
        if key in ("$and", "$or") and isinstance(cond, list) and cond:
            mark = len(sql.params)
            subs = [_where(sql, c) for c in cond]
            if key == "$and":
                parts.append("(" + " and ".join(s for s, _ in subs) + ")")
                exact &= all(e for _, e in subs)
            elif all(e for _, e in subs):
                parts.append("(" + " or ".join(s for s, _ in subs) + ")")
            else:
                del sql.params[mark:]  # clause dropped: its parameters must go too
                exact = False  # an untranslatable branch could match anything
        elif key.startswith("$"):
            exact = False  # $nor, $expr, $comment, ...
        else:
            s, e = _field(sql, key, cond)
            parts.append(s)
            exact &= e
    return (" and ".join(parts) if parts else "true"), exact


def _norm_sort(key_or_list, direction=None) -> list[tuple[str, int]]:
    if key_or_list is None:
        return []
    if isinstance(key_or_list, str):
        return [(key_or_list, direction if direction is not None else 1)]
    if isinstance(key_or_list, dict):
        return list(key_or_list.items())
    return [(k, d) for k, d in key_or_list]


def _order_by(sql: _Sql, sort: list[tuple[str, int]]) -> Optional[str]:
    """ORDER BY clause matching Mongo order for single-typed fields, or None if not pushable.

    On None, any parameters added while trying are rolled back."""
    mark = len(sql.params)
    clause = _order_by_inner(sql, sort)
    if clause is None:
        del sql.params[mark:]
    return clause


def _order_by_inner(sql: _Sql, sort: list[tuple[str, int]]) -> Optional[str]:
    out = []
    for key, d in sort:
        if not isinstance(d, int) or (key != "_id" and not _top_key(key)):
            return None
        direction = "desc" if d < 0 else "asc"
        if key == "_id":
            out.append(f"id {direction}")
            continue
        x = f"(data->{sql.p(key)}::text)"
        # Mongo BSON order: null/missing < numbers < strings (byte order) < objects < arrays < booleans
        out += [
            f"(case jsonb_typeof({x}) when 'number' then 1 when 'string' then 2 when 'object' then 3 "
            f"when 'array' then 4 when 'boolean' then 5 else 0 end) {direction}",
            f"(case when jsonb_typeof({x}) = 'number' then ({x} #>> '{{}}')::numeric end) {direction}",
            f"(case when jsonb_typeof({x}) = 'string' then ({x} #>> '{{}}') end) collate \"C\" {direction}",
            f"{x} {direction}",
        ]
    return ", ".join(out + ["id"])


# --------------------------------------------------------------------------- field pruning
# Large documents make every round trip expensive; when an operation provably needs only a few
# top-level fields we fetch just those (presence-preserving, via jsonb_each). None = whole document.

def _top(path: str) -> str:
    return path.split(".", 1)[0]


def _filter_fields(flt: Any, out: set) -> bool:
    """Collect top-level fields a filter reads. False if it can read arbitrary fields ($where/$expr)."""
    if not isinstance(flt, dict):
        return True
    for k, v in flt.items():
        if k in ("$and", "$or", "$nor"):
            if not all(_filter_fields(c, out) for c in (v or [])):
                return False
        elif k in ("$where", "$expr", "$text", "$jsonSchema"):
            return False
        elif k.startswith("$"):
            continue  # $comment etc.
        else:
            out.add(_top(k))
    return True


def _find_fields(flt, projection, sort) -> Optional[set]:
    if not isinstance(projection, dict) or not projection:
        return None
    vals = [v for k, v in projection.items() if k != "_id"]
    if not vals or any(v in (0, False) for v in vals):
        return None  # exclusion projection keeps everything else
    out = {"_id"} | {_top(k) for k in projection if k != "_id"}
    if not _filter_fields(flt or {}, out):
        return None
    out |= {_top(k) for k, _ in (sort or [])}
    return out


_FULL_DOC_STAGES = {"$unset", "$geoNear", "$replaceWith", "$merge", "$out", "$graphLookup",
                    "$setWindowFields", "$densify", "$fill", "$redact", "$documents", "$unionWith"}


def _pipeline_fields(pipeline: list) -> Optional[set]:
    """Top-level fields an aggregation pipeline can read, or None when it needs whole documents."""
    out: set = {"_id"}

    def refs(v) -> bool:
        if isinstance(v, str):
            if v.startswith("$$ROOT") or v.startswith("$$CURRENT"):
                return False
            if v.startswith("$") and not v.startswith("$$"):
                out.add(_top(v[1:]))
            return True
        if isinstance(v, dict):
            return all(refs(x) for x in v.values())
        if isinstance(v, list):
            return all(refs(x) for x in v)
        return True

    for stage in pipeline:
        if not isinstance(stage, dict) or len(stage) != 1:
            return None
        (name, spec), = stage.items()
        if name in _FULL_DOC_STAGES:
            return None
        if name == "$match":
            if not _filter_fields(spec, out) or not refs(spec):
                return None
        elif name == "$project":
            vals = [v for k, v in spec.items() if k != "_id"]
            if any(v in (0, False) for v in vals):
                return None
            out |= {_top(k) for k, v in spec.items() if v in (1, True)}
            if not refs(spec):
                return None
        elif name == "$lookup":
            if "pipeline" in spec:
                return None
            out.add(_top(spec.get("localField", "_id")))
        elif name == "$sort":
            out |= {_top(k) for k in spec}
        elif name == "$facet":
            for sub in spec.values():
                f = _pipeline_fields(sub)
                if f is None:
                    return None
                out |= f
        elif not refs(spec):
            return None
    return out


# --------------------------------------------------------------------------- mongomock bridge

def _scratch(name: str, docs: list[dict]):
    coll = mongomock.MongoClient()["pg"][name]
    if docs:
        coll.insert_many(docs)
    return coll


class _Results:
    """Minimal pymongo-like result objects."""

    class InsertOne:
        def __init__(self, inserted_id):
            self.inserted_id, self.acknowledged = inserted_id, True

    class InsertMany:
        def __init__(self, ids):
            self.inserted_ids, self.acknowledged = ids, True

    class BulkWrite:
        def __init__(self):
            self.inserted_count = self.matched_count = self.modified_count = 0
            self.deleted_count = self.upserted_count = 0
            self.upserted_ids: dict = {}
            self.acknowledged = True


# --------------------------------------------------------------------------- cursors

class PgCursor:
    def __init__(self, coll: "PgCollection", flt, projection, sort=None, skip=0, limit=0):
        self._coll, self._flt, self._proj = coll, flt or {}, projection
        self._sort: list = _norm_sort(sort)
        self._skip, self._limit = skip or 0, limit or 0
        self._docs: Optional[list] = None

    def sort(self, key_or_list, direction=None):
        self._sort = _norm_sort(key_or_list, direction)
        return self

    def skip(self, n: int):
        self._skip = n or 0
        return self

    def limit(self, n: int):
        self._limit = n or 0
        return self

    def batch_size(self, _n):
        return self

    async def _run(self) -> list:
        if self._docs is None:
            self._docs = await self._coll._find_docs(self._flt, self._proj, self._sort, self._skip, self._limit)
        return self._docs

    async def to_list(self, length: Optional[int] = None):
        docs = await self._run()
        return docs[:length] if length else list(docs)

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for d in await self._run():
            yield d

    async def next(self):
        docs = await self._run()
        if not docs:
            raise StopAsyncIteration
        return docs.pop(0)


class PgAggCursor:
    def __init__(self, coll: "PgCollection", pipeline: list, kwargs: dict):
        self._coll, self._pipeline, self._kw = coll, pipeline, kwargs
        self._docs: Optional[list] = None

    async def _run(self):
        if self._docs is None:
            self._docs = await self._coll._aggregate(self._pipeline, self._kw)
        return self._docs

    async def to_list(self, length: Optional[int] = None):
        docs = await self._run()
        return docs[:length] if length else list(docs)

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for d in await self._run():
            yield d


# --------------------------------------------------------------------------- collection

class PgCollection:
    def __init__(self, database: "PgDatabase", name: str):
        self.database, self.name = database, name

    @property
    def full_name(self):
        return f"{self.database.schema}.{self.name}"

    @property
    def _t(self) -> str:
        return f'{self.database.schema}."{self.name}"'

    # ---- reads
    async def _select(self, conn, flt, *, sort=None, skip=0, limit=0, lock=False,
                      fields: Optional[set] = None) -> tuple[list[dict], bool]:
        """Return (candidate docs, pushed_down). pushed_down=True means skip/limit/sort were applied in SQL."""
        if not await self.database._exists(self.name, conn):
            return [], False
        sql = _Sql()
        where, exact = _where(sql, flt)
        order, pushed = "created_at, id", False
        tail = ""
        if exact and (skip or limit) and not await self._sort_has_arrays(conn, sort or []):
            ob = _order_by(sql, sort or [])
            if ob:
                order, pushed = ob, True
                if limit:
                    tail += f" limit {int(limit)}"
                if skip:
                    tail += f" offset {int(skip)}"
        if fields:
            col = (f"(select coalesce(jsonb_object_agg(e.key, e.value), '{{}}'::jsonb) from jsonb_each(data) e "
                   f"where e.key = any({sql.p(sorted(fields))}::text[]))::text")
        else:
            col = "data::text"
        q = f"select {col} from {self._t} where {where} order by {order}{tail}"
        if lock:
            q += " for update"
        rows = await conn.fetch(q, *sql.params)
        return [_dec(r[0]) for r in rows], pushed

    async def _sort_has_arrays(self, conn, sort) -> bool:
        """Mongo sorts arrays by their min/max element, which SQL can't mirror: don't push those down."""
        now = time.monotonic()
        for key, _ in sort:
            if key == "_id" or not _top_key(key):
                continue
            ck = (self.name, key)
            hit = _ARRAY_CACHE.get(ck)
            if hit is None or now - hit[1] > _ARRAY_TTL:
                has = await conn.fetchval(f"select exists (select 1 from {self._t} "
                                          f"where jsonb_typeof(data->$1::text) = 'array')", key)
                _ARRAY_CACHE[ck] = hit = (has, now)
            if hit[0]:
                return True
        return False

    async def _find_docs(self, flt, projection, sort, skip, limit) -> list:
        async with self.database._conn() as conn:
            docs, pushed = await self._select(conn, flt, sort=sort, skip=skip, limit=limit,
                                              fields=_find_fields(flt, projection, sort))
        cur = _scratch(self.name, docs).find(flt or {}, projection)
        if sort:
            cur = cur.sort(sort)
        if not pushed:
            if skip:
                cur = cur.skip(skip)
            if limit:
                cur = cur.limit(limit)
        return list(cur)

    def find(self, filter=None, projection=None, *args, sort=None, skip=0, limit=0, **_kw):
        if args:  # pymongo positional: find(filter, projection, skip, limit, ...)
            skip = args[0] if len(args) > 0 else skip
            limit = args[1] if len(args) > 1 else limit
        return PgCursor(self, filter, projection, sort, skip, limit)

    async def find_one(self, filter=None, projection=None, *args, sort=None, **_kw):
        if filter is not None and not isinstance(filter, dict):
            filter = {"_id": filter}
        docs = await self._find_docs(filter, projection, _norm_sort(sort), 0, 1)
        return docs[0] if docs else None

    async def count_documents(self, filter=None, skip=0, limit=0, **_kw) -> int:
        async with self.database._conn() as conn:
            if not await self.database._exists(self.name, conn):
                return 0
            sql = _Sql()
            where, exact = _where(sql, filter)
            if exact:
                n = await conn.fetchval(f"select count(*) from {self._t} where {where}", *sql.params)
                n = max(0, n - (skip or 0))
                return min(n, limit) if limit else n
            need: set = {"_id"}
            docs, _ = await self._select(conn, filter, fields=need if _filter_fields(filter or {}, need) else None)
        return len(await self._find_docs_from(docs, filter, skip, limit))

    async def _find_docs_from(self, docs, flt, skip, limit):
        cur = _scratch(self.name, docs).find(flt or {})
        if skip:
            cur = cur.skip(skip)
        if limit:
            cur = cur.limit(limit)
        return list(cur)

    async def estimated_document_count(self, **_kw) -> int:
        async with self.database._conn() as conn:
            if not await self.database._exists(self.name, conn):
                return 0
            return await conn.fetchval(f"select count(*) from {self._t}")

    async def distinct(self, key, filter=None, **_kw):
        async with self.database._conn() as conn:
            need: set = {"_id", _top(key)}
            docs, _ = await self._select(conn, filter, fields=need if _filter_fields(filter or {}, need) else None)
        return _scratch(self.name, docs).distinct(key, filter or {})

    def aggregate(self, pipeline, **kwargs):
        return PgAggCursor(self, list(pipeline), kwargs)

    async def _aggregate(self, pipeline, kwargs):
        first = pipeline[0].get("$match") if pipeline and isinstance(pipeline[0], dict) else None
        async with self.database._conn() as conn:
            docs, _ = await self._select(conn, first, fields=_pipeline_fields(pipeline))
        return list(_scratch(self.name, docs).aggregate(pipeline, **{k: v for k, v in kwargs.items() if k == "allowDiskUse"}))

    # ---- writes
    async def _write(self, flt, op, *, upsert=False, all_rows=False):
        """Run `op(mongomock_collection)` on the locked candidate rows and persist the diff."""
        async with self.database._conn() as conn:
            async with conn.transaction():
                await self.database._ensure(self.name, conn)
                if upsert:
                    await conn.execute("select pg_advisory_xact_lock(hashtext($1))", self.full_name)
                docs, _ = await self._select(conn, None if all_rows else flt, lock=True)
                before = {_id_key(d["_id"]): _enc(d) for d in docs}
                scratch = _scratch(self.name, docs)
                result = op(scratch)
                await self._persist(conn, before, list(scratch.find({})))
                return result

    async def _persist(self, conn, before: dict, after_docs: list):
        after = {_id_key(d["_id"]): d for d in after_docs}
        ups, ins = [], []
        for k, d in after.items():
            enc = _enc(d)
            if k not in before:
                ins.append((k, enc, d["_id"].generation_time if isinstance(d["_id"], ObjectId) else None))
            elif before[k] != enc:
                ups.append((k, enc))
        dels = [k for k in before if k not in after]
        if ups:
            try:
                await conn.executemany(f"update {self._t} set data = $2::jsonb, updated_at = now() where id = $1", ups)
            except asyncpg.UniqueViolationError as e:
                raise DuplicateKeyError(f"E11000 duplicate key error collection: {self.full_name} {e.detail}") from e
        if ins:
            await self._insert_rows(conn, ins)
        if dels:
            await conn.execute(f"delete from {self._t} where id = any($1::text[])", dels)

    async def _insert_rows(self, conn, rows):
        try:
            await conn.executemany(
                f"insert into {self._t} (id, data, created_at) values ($1, $2::jsonb, coalesce($3, now()))", rows)
        except asyncpg.UniqueViolationError as e:
            raise DuplicateKeyError(f"E11000 duplicate key error collection: {self.full_name} {e.detail}") from e

    async def insert_one(self, document, *_a, **_kw):
        document.setdefault("_id", ObjectId())
        _id = document["_id"]
        async with self.database._conn() as conn:
            await self.database._ensure(self.name, conn)
            await self._insert_rows(conn, [(_id_key(_id), _enc(document),
                                            _id.generation_time if isinstance(_id, ObjectId) else None)])
        return _Results.InsertOne(_id)

    async def insert_many(self, documents, ordered=True, *_a, **_kw):
        docs = list(documents)
        for d in docs:
            d.setdefault("_id", ObjectId())
        rows = [(_id_key(d["_id"]), _enc(d), d["_id"].generation_time if isinstance(d["_id"], ObjectId) else None)
                for d in docs]
        async with self.database._conn() as conn:
            await self.database._ensure(self.name, conn)
            if ordered:
                async with conn.transaction():
                    await self._insert_rows(conn, rows)
            else:
                for r in rows:
                    try:
                        await self._insert_rows(conn, [r])
                    except DuplicateKeyError:
                        log.warning("insert_many(ordered=False): duplicate %s in %s", r[0], self.name)
        return _Results.InsertMany([d["_id"] for d in docs])

    async def update_one(self, filter, update, upsert=False, array_filters=None, **_kw):
        return await self._write(filter, lambda c: c.update_one(filter, update, upsert=upsert,
                                                                array_filters=array_filters), upsert=upsert)

    async def update_many(self, filter, update, upsert=False, array_filters=None, **_kw):
        return await self._write(filter, lambda c: c.update_many(filter, update, upsert=upsert,
                                                                 array_filters=array_filters), upsert=upsert)

    async def replace_one(self, filter, replacement, upsert=False, **_kw):
        return await self._write(filter, lambda c: c.replace_one(filter, replacement, upsert=upsert), upsert=upsert)

    async def delete_one(self, filter, **_kw):
        return await self._write(filter, lambda c: c.delete_one(filter))

    async def delete_many(self, filter, **_kw):
        return await self._write(filter, lambda c: c.delete_many(filter))

    async def find_one_and_update(self, filter, update, projection=None, sort=None, upsert=False,
                                  return_document=ReturnDocument.BEFORE, array_filters=None, **_kw):
        return await self._write(filter, lambda c: c.find_one_and_update(
            filter, update, projection=projection, sort=sort, upsert=upsert,
            return_document=return_document, array_filters=array_filters), upsert=upsert)

    async def find_one_and_replace(self, filter, replacement, projection=None, sort=None, upsert=False,
                                   return_document=ReturnDocument.BEFORE, **_kw):
        return await self._write(filter, lambda c: c.find_one_and_replace(
            filter, replacement, projection=projection, sort=sort, upsert=upsert,
            return_document=return_document), upsert=upsert)

    async def find_one_and_delete(self, filter, projection=None, sort=None, **_kw):
        return await self._write(filter, lambda c: c.find_one_and_delete(filter, projection=projection, sort=sort))

    async def bulk_write(self, requests, ordered=True, **_kw):
        res = _Results.BulkWrite()
        for i, op in enumerate(requests):
            kind = type(op).__name__
            if kind == "InsertOne":
                await self.insert_one(op._doc)
                res.inserted_count += 1
                continue
            if kind in ("UpdateOne", "UpdateMany"):
                fn = self.update_one if kind == "UpdateOne" else self.update_many
                r = await fn(op._filter, op._doc, upsert=bool(op._upsert), array_filters=op._array_filters)
            elif kind == "ReplaceOne":
                r = await self.replace_one(op._filter, op._doc, upsert=bool(op._upsert))
            elif kind in ("DeleteOne", "DeleteMany"):
                fn = self.delete_one if kind == "DeleteOne" else self.delete_many
                r = await fn(op._filter)
                res.deleted_count += r.deleted_count
                continue
            else:
                raise NotImplementedError(f"bulk_write op {kind}")
            res.matched_count += r.matched_count
            res.modified_count += r.modified_count
            if getattr(r, "upserted_id", None) is not None:
                res.upserted_count += 1
                res.upserted_ids[i] = r.upserted_id
        return res

    # ---- indexes / admin
    async def create_index(self, keys, unique=False, name=None, sparse=False,
                           partialFilterExpression=None, **_kw) -> str:
        """Only UNIQUE indexes are materialised (they enforce behaviour; lookups use the GIN index).

        Mongo semantics: a missing field counts as null (coalesce), `sparse` skips docs missing
        all keys, `partialFilterExpression` becomes the index WHERE clause.
        """
        spec = _norm_sort(keys)
        idx_name = name or "_".join(f"{k}_{d}" for k, d in spec)
        if not unique:
            return idx_name
        if not spec or any(k == "_id" or not _top_key(k) or not _KEY_RE.match(k) for k, _ in spec):
            log.warning("create_index %s %s: unique index on nested/_id keys not supported", self.name, idx_name)
            return idx_name
        cols = ", ".join(f"(coalesce(data->'{k}', 'null'::jsonb))" for k, _ in spec)
        where = []
        if sparse:
            where.append("(" + " or ".join(f"data ? '{k}'" for k, _ in spec) + ")")
        if partialFilterExpression:
            sql = _InlineSql()
            clause, exact = _where(sql, partialFilterExpression)
            if not exact:
                log.warning("create_index %s %s: partial filter not translatable, skipped", self.name, idx_name)
                return idx_name
            where.append(clause)
        pg_name = f"{self.name}__{idx_name}"[:60]
        stmt = f'create unique index if not exists "{pg_name}" on {self._t} ({cols})'
        if where:
            stmt += " where " + " and ".join(where)
        try:
            async with self.database._conn() as conn:
                await self.database._ensure(self.name, conn)
                await conn.execute(stmt)
        except Exception as e:  # noqa: BLE001 — duplicates in data must not crash startup
            log.warning("create_index %s %s skipped: %s", self.name, idx_name, e)
        return idx_name

    async def create_indexes(self, indexes, **_kw):
        return [await self.create_index(i.document["key"], **{k: v for k, v in i.document.items() if k != "key"})
                for i in indexes]

    async def index_information(self) -> dict:
        info = {"_id_": {"v": 2, "key": [("_id", 1)]}}
        async with self.database._conn() as conn:
            rows = await conn.fetch("select indexname, indexdef from pg_indexes where schemaname = $2 "
                                    "and tablename = $1 and indexdef like '%(data -> %'", self.name, self.database.schema)
        for r in rows:
            m = re.search(r"\(data -> '([^']+)'::text\)", r["indexdef"])
            if m:
                info[r["indexname"]] = {"v": 2, "key": [(m.group(1), 1)], "unique": "UNIQUE" in r["indexdef"]}
        return info

    async def drop(self):
        async with self.database._conn() as conn:
            await conn.execute(f"drop table if exists {self._t}")
        self.database._known.discard(self.name)

    def __getattr__(self, item):  # sub-collections "a.b" are not supported
        raise AttributeError(f"PgCollection has no attribute {item!r}")


# --------------------------------------------------------------------------- database

# Same DDL as app.create_collection() (supabase/migrations), usable for any schema (e.g. app_test).
_CREATE_TABLE_SQL = """
create schema if not exists "{s}";
create table if not exists "{s}"."{t}" (
  id text primary key,
  data jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table "{s}"."{t}" enable row level security;
create index if not exists "{t}_data_gin" on "{s}"."{t}" using gin (data jsonb_path_ops);
"""


class _Admin:
    def __init__(self, database: "PgDatabase"):
        self._db = database

    async def command(self, cmd, *_a, **_kw):
        return await self._db.command(cmd)


class PgDatabase:
    def __init__(self, dsn: str, schema: str = "app", max_size: int = 5):
        if not _NAME_RE.match(schema):
            raise ValueError(f"invalid schema name {schema!r}")
        self._dsn, self.schema, self.name, self._max = dsn, schema, schema, max_size
        self._pool: Optional[asyncpg.Pool] = None
        self._loop = None
        self._lock: Optional[asyncio.Lock] = None
        self._known: set = set()
        self.admin = _Admin(self)
        self.client = self  # db.client.admin.command("ping") / client.close()

    async def _get_pool(self) -> asyncpg.Pool:
        loop = asyncio.get_running_loop()
        if self._pool is None or self._loop is not loop:
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=self._max,
                                                   statement_cache_size=0, command_timeout=60)
            self._loop = loop
        return self._pool

    def _conn(self):
        db = self

        class _Acq:
            async def __aenter__(self):
                self._cm = (await db._get_pool()).acquire()
                return await self._cm.__aenter__()

            async def __aexit__(self, *exc):
                return await self._cm.__aexit__(*exc)

        return _Acq()

    async def _exists(self, name: str, conn) -> bool:
        if name in self._known:
            return True
        ok = await conn.fetchval("select to_regclass($1) is not null", f'{self.schema}."{name}"')
        if ok:
            self._known.add(name)
        return ok

    async def _ensure(self, name: str, conn):
        if not await self._exists(name, conn):
            if not _NAME_RE.match(name):
                raise ValueError(f"invalid collection name {name!r}")
            await conn.execute(_CREATE_TABLE_SQL.format(s=self.schema, t=name))
            self._known.add(name)

    def __getitem__(self, name: str) -> PgCollection:
        return PgCollection(self, name)

    def __getattr__(self, name: str) -> PgCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return PgCollection(self, name)

    def get_collection(self, name: str, **_kw) -> PgCollection:
        return PgCollection(self, name)

    async def list_collection_names(self, **_kw) -> list[str]:
        async with self._conn() as conn:
            rows = await conn.fetch("select table_name from information_schema.tables "
                                    "where table_schema = $1 order by 1", self.schema)
        return [r[0] for r in rows]

    async def command(self, cmd, *_a, **_kw):
        name = cmd if isinstance(cmd, str) else next(iter(cmd))
        if name == "dbstats":
            async with self._conn() as conn:
                size = await conn.fetchval("select coalesce(sum(pg_total_relation_size(c.oid)), 0) from pg_class c "
                                           "join pg_namespace n on n.oid = c.relnamespace "
                                           "where n.nspname = $1 and c.relkind = 'r'", self.schema)
            return {"ok": 1.0, "db": self.name, "dataSize": int(size), "storageSize": int(size)}
        if name == "ping":
            async with self._conn() as conn:
                await conn.fetchval("select 1")  # raises if Postgres is unreachable, like Mongo's ping
        return {"ok": 1.0}

    def close(self):
        if self._pool is not None:
            pool, self._pool = self._pool, None
            try:
                asyncio.get_running_loop().create_task(pool.close())
            except RuntimeError:
                pass


def is_pg(database: Any) -> bool:
    return isinstance(database, PgDatabase)


__all__ = ["PgDatabase", "PgCollection", "is_pg"]
