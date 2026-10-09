"""Object storage client — Supabase Storage, private bucket (Document Vault, House Health, Digital Twin).

put_object(path, data, content_type) -> {"path", "size"}; get_object(path) -> (bytes, content_type).
Server-side only (secret key). Object paths look like "propmanage/properties/<id>/<uuid>.pdf".
"""
import os
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

# ---------------------------------------------------------------- Supabase Storage
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.environ.get("SUPABASE_SECRET_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "propmanage-files")


_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/!-_.*'() &$@=;:+,?")


def _sb_key(path: str) -> str:
    """Supabase keys must be ASCII-safe: deterministically escape other chars (ă -> _u0103_)."""
    return "".join(c if c in _SAFE else f"_u{ord(c):04x}_" for c in path)


def _sb_url(path: str) -> str:
    return f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{quote(_sb_key(path))}"


def _sb_headers(extra: dict | None = None) -> dict:
    h = {"apikey": SUPABASE_SECRET_KEY, "Authorization": f"Bearer {SUPABASE_SECRET_KEY}"}
    return {**h, **(extra or {})}


def _sb_put(path: str, data: bytes, content_type: str) -> dict:
    resp = requests.post(_sb_url(path), data=data, timeout=120,
                         headers=_sb_headers({"Content-Type": content_type, "x-upsert": "true"}))
    resp.raise_for_status()
    return {"path": path, "size": len(data)}


def _sb_get(path: str):
    resp = requests.get(_sb_url(path), headers=_sb_headers(), timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------------------------------------------------------------- public API
def put_object(path: str, data: bytes, content_type: str) -> dict:
    return _sb_put(path, data, content_type)


def get_object(path: str):
    return _sb_get(path)
