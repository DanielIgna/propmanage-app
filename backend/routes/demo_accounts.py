"""Demo Accounts Manager — super admin only.

Allows super_admin to:
  - List all demo sub-admin accounts (5 fixed emails)
  - Reset password to default (from sub_admin_seed.SUB_ADMINS)
  - Set custom password

All write operations require master code "0108" passed in body.
"""
import logging
import os
from datetime import datetime, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin
from sub_admin_seed import SUB_ADMINS, get_default_password, list_demo_emails

logger = logging.getLogger("propmanage.demo_accounts")
router = APIRouter(prefix="/api/admin/demo-accounts", tags=["admin-demo-accounts"])

# Master code required for password operations. Configurable via env var DEMO_MASTER_CODE.
MASTER_CODE = os.environ.get("DEMO_MASTER_CODE", "0108")

DEMO_EMAILS = set(list_demo_emails())


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate gestiona aceste conturi.")


def _require_master_code(code: str) -> None:
    if (code or "").strip() != MASTER_CODE:
        raise HTTPException(403, "Cod master incorect.")


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ---------- Models ----------

class ResetReq(BaseModel):
    email: EmailStr
    master_code: str


class SetPasswordReq(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8, max_length=128)
    master_code: str


# ---------- Endpoints ----------

@router.get("")
async def list_demo_accounts(user=Depends(get_current_user)):
    _require_super(user)
    items = []
    for spec in SUB_ADMINS:
        u = await db.users.find_one({"email": spec["email"]})
        items.append({
            "email": spec["email"],
            "name": spec["name"],
            "role": spec["role"],
            "scope": spec["admin_scope"],
            "default_password": spec["password"],  # visible only to super_admin
            "exists": bool(u),
            "is_active": bool(u and u.get("is_active", True)),
            "last_login_at": u.get("last_login_at") if u else None,
            "updated_at": u.get("updated_at") if u else None,
        })
    return {
        "items": items,
        "count": len(items),
        "master_code_required": True,
        "master_code_hint": "Codul de 4 cifre setat în /app/backend/routes/demo_accounts.py",
    }


@router.post("/reset-password")
async def reset_password(req: ResetReq, user=Depends(get_current_user)):
    _require_super(user)
    _require_master_code(req.master_code)
    if req.email not in DEMO_EMAILS:
        raise HTTPException(400, "Email-ul nu este pe lista de conturi demo.")
    default = get_default_password(req.email)
    if not default:
        raise HTTPException(500, "Parola implicită nu este definită în seed.")
    pw_hash = _hash(default)
    res = await db.users.update_one(
        {"email": req.email, "is_demo_sub_admin": True},
        {"$set": {"password_hash": pw_hash, "is_active": True,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not res.matched_count:
        # try without the demo flag (in case it was missing)
        res = await db.users.update_one(
            {"email": req.email},
            {"$set": {"password_hash": pw_hash, "is_demo_sub_admin": True,
                      "is_active": True,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    if not res.matched_count:
        raise HTTPException(404, "Cont demo inexistent în baza de date.")

    logger.info(f"[demo_accounts] password reset to default for {req.email} by {user.get('email')}")
    return {
        "ok": True,
        "email": req.email,
        "new_password": default,
        "message": "Parolă resetată la valoarea implicită.",
    }


@router.post("/set-password")
async def set_password(req: SetPasswordReq, user=Depends(get_current_user)):
    _require_super(user)
    _require_master_code(req.master_code)
    if req.email not in DEMO_EMAILS:
        raise HTTPException(400, "Email-ul nu este pe lista de conturi demo.")
    # basic strength check (at least 1 letter + 1 number)
    if not any(c.isalpha() for c in req.new_password) or not any(c.isdigit() for c in req.new_password):
        raise HTTPException(400, "Parola trebuie să conțină litere și cifre.")
    pw_hash = _hash(req.new_password)
    res = await db.users.update_one(
        {"email": req.email},
        {"$set": {"password_hash": pw_hash, "is_demo_sub_admin": True, "is_active": True,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if not res.matched_count:
        raise HTTPException(404, "Cont demo inexistent.")
    logger.info(f"[demo_accounts] custom password set for {req.email} by {user.get('email')}")
    return {"ok": True, "email": req.email, "message": "Parolă personalizată salvată."}
