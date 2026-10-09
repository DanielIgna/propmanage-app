"""Database handle (single source of truth): Supabase Postgres via the pgmongo facade.

The codebase keeps its Motor-style API (db.<collection>.find/update_one/...); pgmongo stores
each collection as a JSONB table in schema PG_SCHEMA (default `app`).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from pgmongo import PgDatabase

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

db = PgDatabase(os.environ['SUPABASE_DB_URL'], schema=os.environ.get('PG_SCHEMA', 'app'))
client = db.client
