"""Supabase Auth bridge.

Supabase owns identity + sessions (JWTs). Mongo `users` keeps profile/role and
links to Supabase via `supabase_id`. The Mongo bcrypt hash stays authoritative
for passwords (admin tools, seeds and partner flows still write it), and every
login syncs it into Supabase, so existing users migrate lazily.
"""
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx
import jwt
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')
log = logging.getLogger("propmanage.supabase_auth")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_PUBLISHABLE = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
_SECRET = os.environ.get("SUPABASE_SECRET_KEY", "")
_AUTH = f"{SUPABASE_URL}/auth/v1"


def enabled() -> bool:
    return bool(SUPABASE_URL and _PUBLISHABLE and _SECRET)


@lru_cache(maxsize=1)
def _jwks() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{_AUTH}/.well-known/jwks.json", cache_keys=True, lifespan=3600)


def verify_token(token: str) -> Optional[dict]:
    """Return Supabase JWT claims, or None if the token is not a valid Supabase access token."""
    if not enabled() or not token:
        return None
    try:
        if jwt.get_unverified_header(token).get("alg") == "HS256":
            return None  # legacy PropManage token
        key = _jwks().get_signing_key_from_jwt(token)
        return jwt.decode(token, key.key, algorithms=["ES256", "RS256"],
                          audience="authenticated", issuer=_AUTH)
    except jwt.PyJWTError:
        return None


def _admin_headers() -> dict:
    return {"apikey": _SECRET, "Authorization": f"Bearer {_SECRET}"}


async def _password_grant(email: str, password: str) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(f"{_AUTH}/token", params={"grant_type": "password"},
                         headers={"apikey": _PUBLISHABLE},
                         json={"email": email, "password": password})
    return r.json() if r.status_code == 200 else None


async def _admin(method: str, path: str, json: Optional[dict] = None) -> httpx.Response:
    async with httpx.AsyncClient(timeout=10) as c:
        return await c.request(method, f"{_AUTH}/admin{path}", headers=_admin_headers(), json=json)


async def _find_id_by_email(email: str) -> Optional[str]:
    page = 1
    while True:
        r = await _admin("GET", f"/users?page={page}&per_page=1000")
        users = r.json().get("users", []) if r.status_code == 200 else []
        for u in users:
            if (u.get("email") or "").lower() == email:
                return u["id"]
        if len(users) < 1000:
            return None
        page += 1


async def ensure_user(email: str, password: str, mongo_id: str, supabase_id: Optional[str]) -> str:
    """Create the Supabase user (or reset its password to match Mongo). Returns supabase_id."""
    meta = {"mongo_id": mongo_id}
    if supabase_id:
        r = await _admin("PUT", f"/users/{supabase_id}", {"password": password, "app_metadata": meta})
        if r.status_code == 200:
            return supabase_id
    r = await _admin("POST", "/users", {"email": email, "password": password,
                                        "email_confirm": True, "app_metadata": meta})
    if r.status_code in (200, 201):
        return r.json()["id"]
    existing = await _find_id_by_email(email)
    if existing:
        r = await _admin("PUT", f"/users/{existing}", {"password": password, "app_metadata": meta})
        if r.status_code == 200:
            return existing
    raise RuntimeError(f"Supabase user sync failed ({r.status_code}): {r.text[:200]}")


async def session_for(user: dict, password: str) -> tuple[dict, Optional[str]]:
    """Sign the (already Mongo-verified) user into Supabase.

    Returns (session, new_supabase_id). new_supabase_id is set when Mongo needs updating.
    """
    email = user["email"].lower()
    sb_id = user.get("supabase_id")
    if sb_id:
        session = await _password_grant(email, password)
        if session:
            return session, None
    new_id = await ensure_user(email, password, str(user["_id"]), sb_id)
    session = await _password_grant(email, password)
    if not session:
        raise RuntimeError("Supabase sign-in failed after sync")
    return session, (new_id if new_id != sb_id else None)


async def delete_user(supabase_id: str) -> None:
    r = await _admin("DELETE", f"/users/{supabase_id}")
    if r.status_code not in (200, 204, 404):
        log.warning("Supabase delete failed (%s): %s", r.status_code, r.text[:200])


def public_session(session: dict) -> dict:
    """Subset of the GoTrue session the frontend needs for supabase.auth.setSession()."""
    return {k: session.get(k) for k in ("access_token", "refresh_token", "expires_at", "expires_in")}


async def set_password(supabase_id: Optional[str], password: str) -> None:
    """Best-effort push of a Mongo-side password change into Supabase."""
    if not (enabled() and supabase_id):
        return
    r = await _admin("PUT", f"/users/{supabase_id}", {"password": password})
    if r.status_code != 200:
        log.warning("Supabase password sync failed (%s): %s", r.status_code, r.text[:200])
