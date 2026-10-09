"""Copy every stored file from Emergent Object Storage to Supabase Storage.

Finds object paths by scanning all `app.*` tables for string values that start with
"propmanage/" (storage_path, object_path, render paths, nested attachments...), then
downloads each from Emergent and uploads it to the Supabase bucket under the same path.
Idempotent: objects already present in Supabase are skipped.

Needs EMERGENT_LLM_KEY, SUPABASE_URL, SUPABASE_SECRET_KEY, SUPABASE_DB_URL in backend/.env.
Usage: ./venv/bin/python supabase_migration/copy_objects.py [--dry-run]
"""
import argparse
import asyncio
import sys
from pathlib import Path

import asyncpg
import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import storage_client as sc  # noqa: E402

ENV = dotenv_values(Path(__file__).resolve().parent.parent / ".env")

PATHS_SQL = """
with recursive walk(v) as (
  select data from app.{t}
  union all
  select c.v from walk w cross join lateral (
    select e.value as v from jsonb_each(case when jsonb_typeof(w.v) = 'object' then w.v else '{{}}' end) e
    union all
    select a.value from jsonb_array_elements(case when jsonb_typeof(w.v) = 'array' then w.v else '[]' end) a
  ) c
)
select distinct v #>> '{{}}' from walk
where jsonb_typeof(v) = 'string' and (v #>> '{{}}') like 'propmanage/%'
"""


def exists_in_supabase(path: str) -> bool:
    r = requests.head(sc._sb_url(path), headers=sc._sb_headers(), timeout=30)
    return r.status_code == 200


async def collect_paths() -> dict[str, set]:
    conn = await asyncpg.connect(ENV["SUPABASE_DB_URL"], statement_cache_size=0)
    try:
        tables = [r[0] for r in await conn.fetch(
            "select table_name from information_schema.tables where table_schema = 'app' order by 1")]
        found = {}
        for t in tables:
            rows = await conn.fetch(PATHS_SQL.format(t=f'"{t}"'))
            for (p,) in rows:
                found.setdefault(p, set()).add(t)
        return found
    finally:
        await conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not ENV.get("EMERGENT_LLM_KEY"):
        raise SystemExit("EMERGENT_LLM_KEY missing in backend/.env (needed to read the old storage)")
    sc.EMERGENT_KEY = ENV["EMERGENT_LLM_KEY"]

    paths = asyncio.run(collect_paths())
    print(f"{len(paths)} object paths referenced in the database")
    copied = skipped = 0
    failed = []
    for path, tables in sorted(paths.items()):
        if exists_in_supabase(path):
            skipped += 1
            continue
        if args.dry_run:
            print(f"would copy {path}  ({', '.join(sorted(tables))})")
            continue
        try:
            data, ct = sc.emergent_get_object(path)
            sc._sb_put(path, data, ct)
            copied += 1
            print(f"copied  {len(data):>10} B  {path}")
        except Exception as e:  # noqa: BLE001
            failed.append(path)
            print(f"FAILED  {path}: {type(e).__name__} {getattr(getattr(e, 'response', None), 'status_code', '')}")
    print(f"\ncopied: {copied} | already in Supabase: {skipped} | failed: {len(failed)}")


if __name__ == "__main__":
    main()
