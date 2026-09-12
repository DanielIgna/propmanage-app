"""Admin impersonation — GDPR-compliant 'View as User' workflow.

Workflow:
1. Admin POST /api/admin/impersonate {user_id, reason} → creates an impersonation_logs entry,
   stashes admin's current access_token into a `admin_access_token` cookie, and replaces
   `access_token` with an impersonation JWT (TTL 2h) for the target user.
2. While impersonating, every authenticated request sees user["impersonation"] populated.
3. Destructive endpoints (change_password, 2FA, account_delete) block via block_in_impersonation().
4. Admin POST /api/admin/stop-impersonation → marks log ended, restores admin_access_token →
   access_token, removes stash cookie.

Audit log:
- db.impersonation_logs: full record of who entered which account, when, why, IP, UA.
- Visible to admins (any) at /api/admin/impersonation-logs.
- Visible to data subject (the target user) at /api/me/access-history (GDPR data-subject access).
"""
import os
import secrets
import jwt
import bcrypt
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from db import db
from core_utils import (
    JWT_SECRET, JWT_ALGORITHM, create_impersonation_token, serialize_doc,
)
from deps import get_current_user, require_role


router = APIRouter(prefix="/api", tags=["impersonation"])

IMPERSONATION_TTL_SECONDS = 7200  # 2h (user choice 4.c)
ADMIN_STASH_COOKIE = "admin_access_token"
ACCESS_COOKIE = "access_token"
COOKIE_PATH = "/"

# Match auth cookie config so cross-site (e.g. propmanage.ro → emergent.host) works
_COOKIE_SAMESITE = (os.environ.get("COOKIE_SAMESITE") or "none").lower()
if _COOKIE_SAMESITE not in ("lax", "strict", "none"):
    _COOKIE_SAMESITE = "none"
_COOKIE_SECURE = (os.environ.get("COOKIE_SECURE") or "true").lower() != "false" or _COOKIE_SAMESITE == "none"


class ImpersonateIn(BaseModel):
    user_id: str
    reason: str = Field(..., min_length=10, max_length=500)


# ------------------------------------------------------------------
# Conturi DEMO pentru quick-switch ("Schimbă profilul" din admin).
# ALLOWLIST server-side — SINGURA sursă validă pentru "Intră rapid ca".
# Incident producție 24 Aug 2026: frontend-ul avea fallback pe PRIMUL user cu
# rolul respectiv când emailul demo lipsea din DB → admin a intrat în contul
# unui CLIENT REAL. Fallback-ul a fost eliminat; conturile se creează
# idempotent aici, marcate is_demo_account=True.
# ------------------------------------------------------------------
DEMO_IMPERSONATION_ACCOUNTS = {
    "client@propmanage.io":          {"name": "Andrei Popescu",               "role": "client",     "tier": "VERIFIED"},
    "client.beta@propmanage.io":     {"name": "Ana Beta (Client)",            "role": "client",     "tier": None},
    "specialist@propmanage.io":      {"name": "Mihai Ionescu",                "role": "specialist", "tier": "VERIFIED", "specialty": "hvac"},
    "spec.beta@propmanage.io":       {"name": "Radu Beta (Specialist)",       "role": "specialist", "tier": None,       "specialty": "hvac"},
    "operator@propmanage.io":        {"name": "Lucian Stan",                  "role": "operator",   "tier": None},
    "client.junior@propmanage.io":   {"name": "Andrei Junior (Client nou)",   "role": "client",     "tier": "JUNIOR"},
    "client.verified@propmanage.io": {"name": "Vlad Verified (Client)",       "role": "client",     "tier": "VERIFIED"},
    "client.premium@propmanage.io":  {"name": "Paul Premium (Client)",        "role": "client",     "tier": "PREMIUM"},
    "spec.entry@propmanage.io":      {"name": "Emil Entry (Specialist)",      "role": "specialist", "tier": "ENTRY",    "specialty": "electric"},
    "spec.junior@propmanage.io":     {"name": "Ion Junior (Specialist)",      "role": "specialist", "tier": "JUNIOR",   "specialty": "plumbing"},
    "spec.verified@propmanage.io":   {"name": "Vasile Verified (Specialist)", "role": "specialist", "tier": "VERIFIED", "specialty": "hvac"},
    "spec.advanced@propmanage.io":   {"name": "Adrian Advanced (Specialist)", "role": "specialist", "tier": "ADVANCED", "specialty": "renovation"},
    "spec.premium@propmanage.io":    {"name": "Petre Premium (Specialist)",   "role": "specialist", "tier": "PREMIUM",  "specialty": "hvac"},
    "spec.top@propmanage.io":        {"name": "Tudor Top (Specialist)",       "role": "specialist", "tier": "TOP",      "specialty": "renovation"},
}


class EnsureDemoIn(BaseModel):
    email: str


@router.post("/admin/impersonation/ensure-demo-target")
async def ensure_demo_target(data: EnsureDemoIn, admin: dict = Depends(require_role("admin"))):
    """Rezolvă STRICT (și creează idempotent dacă lipsește) un cont demo de
    quick-switch. Refuză orice email din afara allowlist-ului — NICIODATĂ
    fallback pe utilizatori reali."""
    email = (data.email or "").strip().lower()
    spec = DEMO_IMPERSONATION_ACCOUNTS.get(email)
    if not spec:
        raise HTTPException(400, "Emailul nu este pe lista conturilor demo de impersonare.")

    existing = await db.users.find_one({"email": email})
    if existing:
        if existing.get("role") != spec["role"]:
            raise HTTPException(409, f"Contul {email} există dar are rolul '{existing.get('role')}' "
                                     f"(așteptat: {spec['role']}). Impersonare refuzată.")
        return {"ok": True, "created": False,
                "user": {"id": str(existing["_id"]), "email": email,
                         "name": existing.get("name"), "role": existing.get("role")}}

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "email": email,
        "name": spec["name"],
        "role": spec["role"],
        "tier": spec.get("tier"),
        "phone": "+40 712 000 000",
        # parolă aleatoare, ne-comunicată — contul e folosit DOAR prin impersonare
        "password_hash": bcrypt.hashpw(secrets.token_urlsafe(24).encode(), bcrypt.gensalt()).decode(),
        "email_verified": True,
        "is_active": True,
        "is_demo_account": True,
        "created_at": now,
        "updated_at": now,
    }
    if spec.get("specialty"):
        doc["specialty"] = spec["specialty"]
    res = await db.users.insert_one(doc)
    try:
        await db.admin_audit_log.insert_one({
            "action": "impersonation.demo_account_created",
            "actor_id": admin.get("id"), "actor_email": admin.get("email"),
            "target": {"type": "user", "id": str(res.inserted_id), "label": email},
            "after": {"role": spec["role"], "tier": spec.get("tier"), "is_demo_account": True},
            "created_at": now,
        })
    except Exception:
        pass
    return {"ok": True, "created": True,
            "user": {"id": str(res.inserted_id), "email": email,
                     "name": spec["name"], "role": spec["role"]}}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return (request.client.host if request.client else "?") or "?"


@router.post("/admin/impersonate")
async def start_impersonation(
    data: ImpersonateIn,
    request: Request,
    response: Response,
    current: dict = Depends(get_current_user),
):
    """Start an impersonation session. Admin only."""
    # GDPR: refuse nested impersonation BEFORE role gating so the 409 surfaces
    # (under nested-impersonation the current session role == target's role, not 'admin').
    if current.get("impersonation"):
        raise HTTPException(409, "Ești deja în modul impersonare. Ieși mai întâi.")
    if current.get("role") != "admin":
        raise HTTPException(403, "Insufficient permissions")
    admin = current

    target = await db.users.find_one({"_id": ObjectId(data.user_id)})
    if not target:
        raise HTTPException(404, "Utilizator inexistent")
    target_role = target.get("role", "client")

    # GDPR/Policy: do not allow impersonating other admins (user choice 3.a — clients/specialists/operators only)
    if target_role == "admin":
        raise HTTPException(403, "Nu poți impersona alt administrator.")

    # Need the admin's current access_token to stash (so 'Ieși' can restore it)
    current_token = request.cookies.get(ACCESS_COOKIE)
    if not current_token:
        # Fallback: also check Authorization header (rare in cookie-auth app)
        h = request.headers.get("Authorization", "")
        if h.startswith("Bearer "):
            current_token = h[7:]
    if not current_token:
        raise HTTPException(401, "Sesiunea admin nu poate fi salvată (lipsește access_token).")

    now = datetime.now(timezone.utc)
    log_doc = {
        "admin_id": admin["id"],
        "admin_email": admin.get("email"),
        "admin_name": admin.get("name"),
        "target_user_id": str(target["_id"]),
        "target_user_email": target.get("email"),
        "target_user_name": target.get("name"),
        "target_user_role": target_role,
        "reason": data.reason.strip(),
        "ip": _client_ip(request),
        "user_agent": (request.headers.get("user-agent") or "")[:300],
        "started_at": now.isoformat(),
        "ended_at": None,
        "duration_seconds": None,
        "ttl_seconds": IMPERSONATION_TTL_SECONDS,
    }
    res = await db.impersonation_logs.insert_one(log_doc)
    log_id = str(res.inserted_id)

    imp_token = create_impersonation_token(
        target_user_id=str(target["_id"]),
        target_email=target.get("email", ""),
        target_role=target_role,
        admin_id=admin["id"],
        admin_email=admin.get("email", ""),
        log_id=log_id,
        ttl_seconds=IMPERSONATION_TTL_SECONDS,
    )

    # Stash the admin's existing token so /stop-impersonation can restore it
    response.set_cookie(
        ADMIN_STASH_COOKIE, current_token,
        httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE,
        max_age=IMPERSONATION_TTL_SECONDS, path=COOKIE_PATH,
    )
    response.set_cookie(
        ACCESS_COOKIE, imp_token,
        httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE,
        max_age=IMPERSONATION_TTL_SECONDS, path=COOKIE_PATH,
    )

    return {
        "ok": True,
        "log_id": log_id,
        "target": {
            "id": str(target["_id"]),
            "email": target.get("email"),
            "name": target.get("name"),
            "role": target_role,
        },
        "started_at": now.isoformat(),
        "expires_in_seconds": IMPERSONATION_TTL_SECONDS,
        "redirect_to": f"/{target_role}",
    }


@router.post("/admin/stop-impersonation")
async def stop_impersonation(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
):
    """Stop the current impersonation session and restore the admin cookie."""
    imp = user.get("impersonation") or {}
    if not imp:
        raise HTTPException(400, "Nu ești în modul impersonare.")

    admin_token = request.cookies.get(ADMIN_STASH_COOKIE)
    if not admin_token:
        raise HTTPException(409, "Cookie-ul admin lipsește; deconectează-te și reconectează-te.")

    # Validate the stashed token is a real, non-expired admin access token
    try:
        payload = jwt.decode(admin_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(409, "Cookie admin invalid (type).")
        if payload.get("impersonation"):
            raise HTTPException(409, "Cookie admin invalid (nested impersonation).")
    except jwt.ExpiredSignatureError:
        raise HTTPException(409, "Sesiunea admin a expirat. Loghează-te din nou.")
    except jwt.InvalidTokenError:
        raise HTTPException(409, "Cookie admin invalid.")

    # Mark the log entry as ended
    log_id = imp.get("log_id")
    started_iso = imp.get("started_at")
    duration = None
    try:
        if started_iso:
            duration = int((datetime.now(timezone.utc) - datetime.fromisoformat(started_iso)).total_seconds())
    except Exception:
        duration = None
    if log_id:
        try:
            await db.impersonation_logs.update_one(
                {"_id": ObjectId(log_id)},
                {"$set": {
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": duration,
                }}
            )
        except Exception:
            pass  # don't block exit on logging failure

    # Restore admin cookie
    response.set_cookie(
        ACCESS_COOKIE, admin_token,
        httponly=True, secure=_COOKIE_SECURE, samesite=_COOKIE_SAMESITE,
        max_age=86400, path=COOKIE_PATH,
    )
    response.delete_cookie(ADMIN_STASH_COOKIE, path=COOKIE_PATH)

    return {"ok": True, "log_id": log_id, "duration_seconds": duration, "redirect_to": "/admin"}


@router.get("/admin/impersonation-logs")
async def list_impersonation_logs(
    skip: int = 0,
    limit: int = 50,
    target_user_id: Optional[str] = None,
    admin_id: Optional[str] = None,
    admin: dict = Depends(require_role("admin")),
):
    """List impersonation history. Admin-wide audit view."""
    limit = max(1, min(limit, 200))
    q = {}
    if target_user_id:
        q["target_user_id"] = target_user_id
    if admin_id:
        q["admin_id"] = admin_id
    total = await db.impersonation_logs.count_documents(q)
    cursor = db.impersonation_logs.find(q).sort("started_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append(serialize_doc(doc))
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/me/access-history")
async def my_access_history(user: dict = Depends(get_current_user), limit: int = 100):
    """GDPR data-subject access: a user sees every admin impersonation against their account."""
    limit = max(1, min(limit, 500))
    cursor = db.impersonation_logs.find(
        {"target_user_id": user["id"]},
    ).sort("started_at", -1).limit(limit)
    items = []
    async for doc in cursor:
        d = serialize_doc(doc)
        # Hide IP / UA to the data subject (admin-only fields)
        d.pop("ip", None)
        d.pop("user_agent", None)
        items.append(d)
    return {"items": items, "count": len(items)}
