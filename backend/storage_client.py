"""Object storage client — persistent file storage (Document Vault, House Health, Digital Twin).

STORAGE_BACKEND=supabase  → Supabase Storage, private bucket `propmanage-files` (secret key, server-side only).
STORAGE_BACKEND=emergent  → Emergent Object Storage (legacy, default while not migrated).

Same API for both: put_object(path, data, content_type) -> {"path", "size"}; get_object(path) -> (bytes, content_type).
Object paths are unchanged between backends (e.g. "propmanage/properties/<id>/<uuid>.pdf").
"""
import os
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "emergent").lower()

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


# ---------------------------------------------------------------- Emergent Object Storage (legacy)
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("ANTHROPIC_API_KEY")

_storage_key = None


def init_storage() -> str:
    global _storage_key
    if _storage_key:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def emergent_put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if resp.status_code == 403:
        global _storage_key
        _storage_key = None
        key = init_storage()
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def emergent_get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ---------------------------------------------------------------- public API
def put_object(path: str, data: bytes, content_type: str) -> dict:
    if STORAGE_BACKEND == "supabase":
        return _sb_put(path, data, content_type)
    return emergent_put_object(path, data, content_type)


def get_object(path: str):
    if STORAGE_BACKEND == "supabase":
        return _sb_get(path)
    return emergent_get_object(path)
