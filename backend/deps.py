"""FastAPI dependencies for auth (get_current_user, require_role)."""
import jwt
from typing import Optional
from bson import ObjectId
from fastapi import Request, Depends, HTTPException

import supabase_auth
from db import db
from core_utils import JWT_SECRET, JWT_ALGORITHM, serialize_doc


async def _user_from_token(token: str) -> tuple[Optional[dict], Optional[dict]]:
    """Resolve a token to (mongo_user, legacy_payload). Supabase JWTs first, then legacy HS256."""
    claims = supabase_auth.verify_token(token)
    if claims:
        return await db.users.find_one({"supabase_id": claims["sub"]}), None
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type")
    return await db.users.find_one({"_id": ObjectId(payload["sub"])}), payload


async def get_current_user(request: Request) -> dict:
    # Cookie first (impersonation tokens live there), then the Supabase Bearer token.
    h = request.headers.get("Authorization", "")
    candidates = [t for t in (request.cookies.get("access_token"), h[7:] if h.startswith("Bearer ") else None) if t]
    if not candidates:
        raise HTTPException(401, "Not authenticated")
    error = "Invalid token"
    for token in candidates:
        try:
            user, payload = await _user_from_token(token)
        except jwt.ExpiredSignatureError:
            error = "Token expired"
            continue
        except jwt.InvalidTokenError:
            continue
        if not user:
            error = "User not found"
            continue
        u = serialize_doc(user)
        # Attach impersonation context (if the token was minted by /admin/impersonate)
        if payload and payload.get("impersonation"):
            u["impersonation"] = payload["impersonation"]
        # Expose to middleware (e.g., demo activity logger)
        try:
            request.state.user = u
        except Exception:  # noqa: BLE001
            pass
        return u
    raise HTTPException(401, error)


def block_in_impersonation(user: dict, action: str = "această acțiune"):
    """Raise 403 if the current request is an admin acting on behalf of a target user.
    Used to protect destructive/credential-modifying endpoints (password, 2FA, delete account)."""
    if user.get("impersonation"):
        raise HTTPException(403, f"Nu poți efectua {action} în modul impersonare. Ieși din impersonare mai întâi.")


def block_impersonation_dep(action: str):
    """Dependency factory: rejects the request with 403 BEFORE body validation if the caller
    is in impersonation mode. Use this for endpoints whose body could fail Pydantic validation
    (otherwise the 422 would mask the 403)."""
    async def _dep(user: dict = Depends(get_current_user)):
        block_in_impersonation(user, action)
        return user
    return _dep


def require_role(*allowed):
    async def dep(user: dict = Depends(get_current_user)):
        if user.get("role") in allowed:
            return user
        # Dual-role: verified specialist with active_view=client can access client-only endpoints
        if (
            user.get("role") == "specialist"
            and user.get("dual_role_enabled") is True
            and user.get("active_view") in allowed
        ):
            return user
        raise HTTPException(403, "Insufficient permissions")
    return dep
