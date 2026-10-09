"""Differential test: real MongoDB vs the pgmongo adapter on the same production data.

1. Restores a mongodump archive into a LOCAL Mongo database (`--mongo-db`, default pgmongo_verify).
2. Auto-generates queries per collection from real field values (eq, $in, $ne, $nin, $exists,
   ranges, null, $or, sort+skip+limit, projection, count, distinct, $group aggregation)
   and compares Mongo's answer with the adapter's (Supabase must hold the same dump:
   run import_mongo_dump.py first).
3. Replays a write scenario (insert/update/$inc/$push/upsert/find_one_and_update/delete)
   on a scratch collection in both stores and compares the final state.

Usage: ./venv/bin/python supabase_migration/verify_adapter.py backups/<dump>.tar.gz [--max-colls N]
"""
import argparse
import asyncio
import json
import os
import random
import sys
import tarfile
import tempfile
from pathlib import Path

import bson
from bson import ObjectId
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pgmongo import PgDatabase, _enc  # noqa: E402

ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
random.seed(7)


def canon(v):
    """Key-order-insensitive encoding (jsonb does not keep key order; Mongo semantics don't depend on it)."""
    return json.dumps(json.loads(_enc(v)), sort_keys=True)


def norm(docs):
    return sorted(canon(d) for d in docs)


def scalar(v):
    return isinstance(v, (str, int, float, bool)) and not (isinstance(v, float) and v != v)


def cases_for(docs):
    """Yield (label, kind, args) query cases built from real values."""
    fields = {}
    for d in docs[:200]:
        for k, v in d.items():
            if k != "_id" and scalar(v):
                fields.setdefault(k, []).append(v)
            elif isinstance(v, list) and v and scalar(v[0]):
                fields.setdefault(k, []).append(v[0])
    some_id = docs[0]["_id"]
    yield "by_id", "find", ({"_id": some_id},)
    yield "id_in", "find", ({"_id": {"$in": [d["_id"] for d in docs[:3]]}},)
    yield "all_count", "count", ({},)
    for k, vals in list(fields.items())[:8]:
        v = random.choice(vals)
        yield f"{k}=", "find", ({k: v},)
        yield f"{k} count", "count", ({k: v},)
        yield f"{k} $in", "find", ({k: {"$in": list({*vals[:3], v})}},)
        yield f"{k} $ne", "count", ({k: {"$ne": v}},)
        yield f"{k} $nin", "count", ({k: {"$nin": vals[:2]}},)
        yield f"{k} $exists", "count", ({k: {"$exists": True}},)
        yield f"{k} !$exists", "count", ({k: {"$exists": False}},)
        yield f"{k} null", "count", ({k: None},)
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            yield f"{k} $gte", "count", ({k: {"$gte": v}},)
            yield f"{k} range", "find", ({k: {"$gt": min(vals), "$lte": max(vals)}},)
        yield f"{k} $or", "find", ({"$or": [{k: v}, {"_id": some_id}]},)
        yield f"{k} sort desc lim", "sorted", ({}, [(k, -1)], 0, 5)
        yield f"{k} sort asc skip", "sorted", ({k: {"$exists": True}}, [(k, 1)], 2, 4)
        yield f"{k} proj", "find_proj", ({k: v}, {k: 1})
        yield f"{k} distinct", "distinct", (k, {})
        yield f"{k} group", "agg", ([{"$match": {k: {"$exists": True}}},
                                     {"$group": {"_id": f"${k}", "n": {"$sum": 1}}}],)


async def run_case(coll, kind, args):
    if kind == "find":
        return norm(await coll.find(*args).to_list(None))
    if kind == "find_proj":
        return norm(await coll.find(*args).to_list(None))
    if kind == "count":
        return await coll.count_documents(*args)
    if kind == "distinct":
        return sorted(map(canon, await coll.distinct(*args)))
    if kind == "agg":
        return norm(await coll.aggregate(*args).to_list(None))
    if kind == "sorted":
        flt, sort, skip, limit = args
        docs = await coll.find(flt).sort(sort).skip(skip).limit(limit).to_list(None)
        key = sort[0][0]
        return [canon(d.get(key)) for d in docs]  # compare sort keys (ties may differ in _id)
    raise ValueError(kind)


async def write_scenario(coll):
    await coll.delete_many({})
    a = ObjectId()
    await coll.insert_one({"_id": a, "name": "a", "n": 1, "tags": ["x"], "nested": {"k": 1}})
    await coll.insert_many([{"name": f"b{i}", "n": i, "status": "open"} for i in range(5)])
    await coll.update_one({"_id": a}, {"$inc": {"n": 5}, "$push": {"tags": "y"}, "$set": {"nested.k": 2}})
    await coll.update_many({"status": "open", "n": {"$gte": 2}}, {"$set": {"status": "closed"}})
    await coll.update_one({"name": "zz"}, {"$set": {"n": 99}, "$setOnInsert": {"_id": "fixed-upsert"}}, upsert=True)
    r = await coll.find_one_and_update({"name": "a"}, {"$addToSet": {"tags": "x"}, "$unset": {"nested": ""}},
                                       return_document=ReturnDocument.AFTER)
    await coll.delete_one({"name": "b0"})
    await coll.replace_one({"name": "b1"}, {"name": "b1", "replaced": True})
    after = await coll.find({}, {"_id": 0}).to_list(None)  # generated ObjectIds differ per store
    r.pop("_id", None)
    return norm(after), canon(r), await coll.count_documents({"status": "closed"})


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive")
    ap.add_argument("--mongo-db", default="pgmongo_verify")
    ap.add_argument("--max-colls", type=int, default=1000)
    ap.add_argument("--skip-restore", action="store_true")
    ap.add_argument("--kinds", help="only these case kinds, e.g. sorted,count")
    args = ap.parse_args()

    mclient = AsyncIOMotorClient(ENV["MONGO_URL"])
    mdb = mclient[args.mongo_db]
    pg = PgDatabase(ENV["SUPABASE_DB_URL"], max_size=10)

    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(args.archive) as tar:
            tar.extractall(tmp, filter="data")
        dump_dir = next(Path(p) for p, _, fs in os.walk(tmp) if any(f.endswith(".bson") for f in fs))
        data = {}
        for f in sorted(dump_dir.glob("*.bson")):
            raw = f.read_bytes()
            docs = bson.decode_all(raw) if raw else []
            if docs:
                data[f.stem] = docs
        if not args.skip_restore:
            await mclient.drop_database(args.mongo_db)
            for name, docs in data.items():
                await mdb[name].insert_many(docs)
            print(f"restored {len(data)} collections into local Mongo `{args.mongo_db}`")

    sem = asyncio.Semaphore(8)
    stats = {"total": 0, "fails": 0}

    async def check(name, docs):
        async with sem:
            for label, kind, cargs in cases_for(docs):
                if args.kinds and kind not in args.kinds.split(","):
                    continue
                stats["total"] += 1
                try:
                    exp = await run_case(mdb[name], kind, cargs)
                except Exception:  # noqa: BLE001 — Mongo itself rejects the generated query
                    continue
                try:
                    got = await run_case(pg[name], kind, cargs)
                except Exception as e:  # noqa: BLE001
                    got = f"ERROR {type(e).__name__}: {e}"
                if exp != got:
                    stats["fails"] += 1
                    print(f"FAIL {name} | {label} | mongo={str(exp)[:150]} | pg={str(got)[:150]}", flush=True)

    await asyncio.gather(*(check(n, d) for n, d in list(data.items())[:args.max_colls]))
    print(f"\nread cases: {stats['total']} | failures: {stats['fails']}")

    m = await write_scenario(mdb["pgmongo_write_test"])
    p = await write_scenario(pg["pgmongo_write_test"])
    print("write scenario:", "OK" if m == p else f"FAIL\n mongo={m}\n pg={p}")
    await pg["pgmongo_write_test"].drop()
    await mclient.drop_database(args.mongo_db)


if __name__ == "__main__":
    asyncio.run(main())
