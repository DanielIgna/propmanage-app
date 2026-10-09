"""Import a mongodump archive (admin "dump-bson" backup) into Supabase schema `app`.

Each collection lands in `app.<collection>` as (id, data jsonb, created_at):
  - id   = str(_id) (ObjectId hex or the original string id)
  - data = the full document as MongoDB Extended JSON (relaxed), so ObjectId/datetime
           round-trip as {"$oid": ...} / {"$date": ...}
Idempotent: each collection is truncated and reloaded inside its own transaction.

Usage:
  ./venv/bin/python supabase_migration/import_mongo_dump.py backups/propmanage-bson-dump-XXXX.tar.gz [--only users,requests]
"""
import argparse
import asyncio
import os
import tarfile
import tempfile
from pathlib import Path

import asyncpg
import bson
from bson import json_util
from bson.json_util import JSONOptions, JSONMode
from bson.objectid import ObjectId
from dotenv import dotenv_values

ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
RELAXED = JSONOptions(json_mode=JSONMode.RELAXED)
BATCH = 1000


def find_dump_dir(root: Path) -> Path:
    for dirpath, _, files in os.walk(root):
        if any(f.endswith(".bson") for f in files):
            return Path(dirpath)
    raise SystemExit("No .bson files found in archive")


def to_row(doc: dict):
    _id = doc["_id"]
    created = _id.generation_time if isinstance(_id, ObjectId) else None
    return str(_id), json_util.dumps(doc, json_options=RELAXED), created


async def import_collection(conn, name: str, path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    docs = bson.decode_all(raw) if raw else []
    rows = [to_row(d) for d in docs]
    async with conn.transaction():
        await conn.execute("select app.create_collection($1)", name)
        await conn.execute(f'truncate app."{name}"')
        for i in range(0, len(rows), BATCH):
            await conn.executemany(
                f'insert into app."{name}" (id, data, created_at) '
                f"values ($1, $2::jsonb, coalesce($3, now()))",
                rows[i:i + BATCH],
            )
        loaded = await conn.fetchval(f'select count(*) from app."{name}"')
    return len(docs), loaded


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archive", help="tar.gz from /api/admin/backups/dump-bson, or an extracted dump dir")
    ap.add_argument("--only", help="comma-separated collection names")
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else None
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(args.archive)
        if src.is_file():
            with tarfile.open(src) as tar:
                tar.extractall(tmp, filter="data")
            src = Path(tmp)
        dump_dir = find_dump_dir(src)

        conn = await asyncpg.connect(ENV["SUPABASE_DB_URL"], statement_cache_size=0)
        try:
            mismatches, total = [], 0
            for f in sorted(dump_dir.glob("*.bson")):
                name = f.stem
                if only and name not in only:
                    continue
                expected, loaded = await import_collection(conn, name, f)
                total += loaded
                flag = "" if expected == loaded else "  <-- MISMATCH"
                if flag:
                    mismatches.append(name)
                print(f"{name:45} {expected:>7} -> {loaded:>7}{flag}")
            print(f"\nTotal rows: {total} | mismatches: {mismatches or 'none'}")
        finally:
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
