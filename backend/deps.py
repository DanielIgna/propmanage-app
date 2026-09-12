"""FastAPI dependencies for auth (get_current_user, require_role)."""
import jwt
from bson import ObjectId
from fastapi import Request, Depends, HTTPException

from db import db
from core_utils import JWT_SECRET, JWT_ALGORITHM, serialize_doc


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            token = h[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(401, "User not found")
        u = serialize_doc(user)
        # Attach impersonation context (if the token was minted by /admin/impersonate)
        if payload.get("impersonation"):
            u["impersonation"] = payload["impersonation"]
        # Expose to middleware (e.g., demo activity logger)
        try:
            request.state.user = u
        except Exception:  # noqa: BLE001
            pass
        return u
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


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
