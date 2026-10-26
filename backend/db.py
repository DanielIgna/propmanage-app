"""Database handle (single source of truth): Supabase Postgres via the pgmongo facade.

The codebase keeps its Motor-style API (db.<collection>.find/update_one/...); pgmongo stores
each collection as a JSONB table in schema PG_SCHEMA (default `app`).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from media_store import externalize_doc
from pgmongo import PgDatabase

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PG_POOL_MAX: conexiuni în pool (implicit 5). Pe pooler-ul Supabase în mod sesiune, fiecare conexiune ocupă un loc.
db = PgDatabase(os.environ['SUPABASE_DB_URL'], schema=os.environ.get('PG_SCHEMA', 'app'),
                max_size=max(1, int(os.environ.get('PG_POOL_MAX', '5') or 5)))
db.before_write = externalize_doc  # base64 media -> Storage links (media_store.MEDIA_FIELDS)
client = db.client
