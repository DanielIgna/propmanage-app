"""Database handle (single source of truth).

DB_BACKEND=mongo (default) → Motor/MongoDB.
DB_BACKEND=postgres        → pgmongo facade over Supabase Postgres (schema `app`), same API.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

DB_BACKEND = os.environ.get('DB_BACKEND', 'mongo').lower()

if DB_BACKEND == 'postgres':
    from pgmongo import PgDatabase

    db = PgDatabase(os.environ['SUPABASE_DB_URL'])
    client = db.client
    mongo_url = None
else:
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
