"""Entitlements API — expune starea de entitlement pentru frontend + admin.

Endpoints:
  GET  /api/me/entitlements              — user curent (auto-hidratat)
  POST /api/me/subscription/cancel       — self-cancel (păstrează acces până la expires_at)
  GET  /api/admin/entitlements/catalog   — catalog tier→features (admin)
  GET  /api/admin/users/{user_id}/entitlements — lookup admin pe alt user
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user, require_role
from entitlements import get_tier_catalog, get_user_entitlements

router = APIRouter(prefix="/api", tags=["entitlements"])


@router.get("/me/entitlements")
async def me_entitlements(user: dict = Depends(get_current_user)):
    """Snapshot-ul de entitlement pentru user-ul curent. Frontend-ul îl folosește
    ca sursă unică pentru gating UI."""
    return await get_user_entitlements(user)


@router.post("/me/subscription/cancel")
async def cancel_my_subscription(user: dict = Depends(get_current_user)):
    """Self-cancel subscription. Access rămâne activ până la expires_at, apoi
    lifecycle devine automat 'expired' și user resolvă la FREE.

    Non-destructiv: NU șterge date, doar setează status='cancelled'.
    Reutilizează modelul existent (Stripe billing cycles pot fi oprite separat).
    """
    uid = str(user["id"])
    sub = await db.hh_subscriptions.find_one({"user_id": uid})
    if not sub:
        raise HTTPException(404, "Nu ai un abonament activ.")
    if sub.get("status") not in ("active", "trial", "grace"):
        # deja cancelled/expired — răspuns idempotent
        return await get_user_entitlements(user)
    now = datetime.now(timezone.utc).isoformat()
    await db.hh_subscriptions.update_one(
        {"user_id": uid},
        {"$set": {
            "status": "cancelled",
            "cancelled_at": now,
            "cancelled_by": uid,
            "updated_at": now,
        }},
    )
    return await get_user_entitlements(user)


@router.get("/admin/entitlements/catalog")
async def catalog(_admin: dict = Depends(require_role("admin"))):
    return get_tier_catalog()


@router.get("/admin/users/{user_id}/entitlements")
async def admin_lookup(user_id: str, _admin: dict = Depends(require_role("admin"))):
    """Admin verifică starea de entitlement a unui user oarecare (fără impersonation)."""
    try:
        u = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        u = None
    if not u:
        raise HTTPException(404, "Utilizator inexistent")
    # normalizează la formatul așteptat de get_user_entitlements
    target = {
        "id": str(u["_id"]),
        "role": u.get("role"),
        "active_view": u.get("active_view"),
    }
    ent = await get_user_entitlements(target)
    ent["user_email"] = u.get("email")
    ent["user_name"] = u.get("name")
    return ent
