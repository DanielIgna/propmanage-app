"""Admin Accounts Manager — control over ALL admin-level accounts.

Distinct from demo_accounts.py (which targets only the 6 fixed demo emails).
This module lets super_admin manage ANY admin in the system:
  - List all (role in {admin, super_admin, marketing_manager, operator})
  - Block/unblock (toggle is_active)
  - Change role and admin_scope
  - Reset/change password
  - View sensitive metadata (last_login, created_at)

Super admin (admin@propmanage.io) is PROTECTED: cannot be blocked, demoted, or
have role changed by these endpoints. Password can be changed only by setting
a new one (no reset to default since super_admin password is not seeded).

All write operations require master code "0108".

Endpoints:
  GET  /api/admin/admin-accounts                — list all admins
  POST /api/admin/admin-accounts/block-toggle   — flip is_active
  POST /api/admin/admin-accounts/change-role    — set new role+scope
  POST /api/admin/admin-accounts/change-password — set new password
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.admin_accounts")
router = APIRouter(prefix="/api/admin/admin-accounts", tags=["admin-admin-accounts"])

MASTER_CODE = os.environ.get("DEMO_MASTER_CODE", "0108")
# Owner accounts — cannot be blocked or demoted (treated as super-admin)
PROTECTED_EMAILS = {"admin@propmanage.io", "danieligna1@gmail.com"}

ALLOWED_ROLES = {"admin", "marketing_manager", "operator", "specialist", "client"}
ALLOWED_SCOPES = {"general", "testing", "frontend", "backend", "security",
                  "marketing", "ops", "ai", "finance", "legal", "growth", ""}


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate gestiona conturile de admin.")


def _require_code(code: str) -> None:
    if (code or "").strip() != MASTER_CODE:
        raise HTTPException(403, "Cod master incorect.")


def _check_not_protected(email: str, action: str) -> None:
    if email in PROTECTED_EMAILS:
        raise HTTPException(400, f"Contul super-admin ({email}) este protejat și nu poate fi {action}.")


# ---------- Models ----------

class EmailCode(BaseModel):
    email: EmailStr
    master_code: str


class ChangeRoleReq(BaseModel):
    email: EmailStr
    new_role: str
    new_scope: Optional[str] = ""
    new_seniority: Optional[str] = "senior"
    master_code: str


class ChangePasswordReq(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8, max_length=128)
    master_code: str


# ---------- Endpoints ----------

@router.get("")
async def list_admins(user=Depends(get_current_user)):
    _require_super(user)
    # Match anyone with admin-level role
    cur = db.users.find(
        {"role": {"$in": ["admin", "super_admin", "marketing_manager", "operator"]}},
        {"password_hash": 0},
    ).sort("created_at", -1)
    items = []
    async for u in cur:
        email = u.get("email")
        items.append({
            "email": email,
            "name": u.get("name") or "—",
            "role": u.get("role") or "admin",
            "scope": u.get("admin_scope") or "—",
            "seniority": u.get("admin_seniority") or "—",
            "is_active": u.get("is_active") if u.get("is_active") is not None else True,
            "is_demo_sub_admin": bool(u.get("is_demo_sub_admin")),
            "is_protected": email in PROTECTED_EMAILS,
            "zone_role": u.get("zone_role"),
            "admin_zones": u.get("admin_zones"),
            "last_login_at": u.get("last_login_at"),
            "created_at": u.get("created_at"),
            "updated_at": u.get("updated_at"),
        })
    return {
        "items": items,
        "count": len(items),
        "protected_emails": sorted(PROTECTED_EMAILS),
        "allowed_roles": sorted(ALLOWED_ROLES),
        "allowed_scopes": sorted([s for s in ALLOWED_SCOPES if s]),
    }


@router.post("/block-toggle")
async def block_toggle(req: EmailCode, user=Depends(get_current_user)):
    _require_super(user)
    _require_code(req.master_code)
    _check_not_protected(req.email, "blocat")

    u = await db.users.find_one({"email": req.email})
    if not u:
        raise HTTPException(404, "Utilizator inexistent.")
    if u.get("role") not in {"admin", "super_admin", "marketing_manager", "operator"}:
        raise HTTPException(400, "Nu este cont admin.")

    new_active = not (u.get("is_active") if u.get("is_active") is not None else True)
    await db.users.update_one(
        {"_id": u["_id"]},
        {"$set": {"is_active": new_active,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info(f"[admin_accounts] {req.email} active={new_active} by {user.get('email')}")
    return {"ok": True, "email": req.email, "is_active": new_active,
            "message": "Activat." if new_active else "Blocat."}


@router.post("/change-role")
async def change_role(req: ChangeRoleReq, user=Depends(get_current_user)):
    _require_super(user)
    _require_code(req.master_code)
    _check_not_protected(req.email, "schimbat de rol")
    if req.new_role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Rol invalid. Permise: {sorted(ALLOWED_ROLES)}")
    scope = (req.new_scope or "").strip().lower()
    if scope and scope not in ALLOWED_SCOPES:
        raise HTTPException(400, f"Scope invalid. Permise: {sorted([s for s in ALLOWED_SCOPES if s])}")

    res = await db.users.update_one(
        {"email": req.email},
        {"$set": {"role": req.new_role, "admin_scope": scope,
                  "admin_seniority": req.new_seniority or "senior",
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Utilizator inexistent.")
    logger.info(f"[admin_accounts] {req.email} role→{req.new_role} scope→{scope} by {user.get('email')}")
    return {"ok": True, "email": req.email, "new_role": req.new_role, "new_scope": scope}


@router.post("/change-password")
async def change_password(req: ChangePasswordReq, user=Depends(get_current_user)):
    _require_super(user)
    _require_code(req.master_code)
    # Super admin's password CAN be changed here (it's the only way for super to
    # rotate their own pw without losing access). No protection needed for this op.
    if not any(c.isalpha() for c in req.new_password) or not any(c.isdigit() for c in req.new_password):
        raise HTTPException(400, "Parola trebuie să conțină litere și cifre.")

    pw_hash = bcrypt.hashpw(req.new_password.encode(), bcrypt.gensalt()).decode()
    res = await db.users.update_one(
        {"email": req.email},
        {"$set": {"password_hash": pw_hash, "is_active": True,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Utilizator inexistent.")
    logger.info(f"[admin_accounts] password changed for {req.email} by {user.get('email')}")
    return {"ok": True, "email": req.email, "message": "Parolă schimbată cu succes."}
