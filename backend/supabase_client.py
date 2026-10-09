"""Supabase client handle (alongside Mongo in db.py)."""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv(Path(__file__).parent / '.env')


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Server-side client. Uses the secret key when set (bypasses RLS), else the publishable key."""
    url = os.environ['SUPABASE_URL']
    key = os.environ.get('SUPABASE_SECRET_KEY') or os.environ['SUPABASE_PUBLISHABLE_KEY']
    return create_client(url, key)
