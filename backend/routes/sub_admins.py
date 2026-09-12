"""Sub-Admin management — REST API (super-admin only).

Endpoints (mounted at /api/admin/sub-admins):
  GET    /                — list all sub-admins
  POST   /                — create a new sub-admin (custom email + password)
  PATCH  /{id}            — update scope/seniority/active
  POST   /{id}/reset-password — reset password (returns new one)
  DELETE /{id}            — soft-delete (sets is_active=False)

Only callable by a super admin (admin_scope="general") — enforced via the
``is_super_admin`` helper.

Additional helper endpoint:
  GET /me/scope           — any authenticated admin can read their own scope
  GET /audit              — super-admin: latest admin actions log
"""
import logging
import secrets
import string
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from db import db
from deps import get_current_user
from sub_admin_deps import (
    ALLOWED_SCOPES,
    ALLOWED_SENIORITY,
    is_super_admin,
)

logger = logging.getLogger("propmanage.sub_admins")
router = APIRouter(prefix="/api/admin/sub-admins", tags=["admin-sub-admins"])


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin (scope=general) poate gestiona sub-admini.")


def _strip(u: dict) -> dict:
    out = {
        "id": str(u.get("_id")),
        "email": u.get("email"),
        "name": u.get("name"),
        "admin_scope": u.get("admin_scope") or "general",
        "admin_seniority": u.get("admin_seniority") or "senior",
        "reports_to": u.get("reports_to"),
        "is_active": u.get("is_active", True),
        "created_at": u.get("created_at"),
        "updated_at": u.get("updated_at"),
        "last_seen": u.get("last_seen"),
        "is_demo_sub_admin": bool(u.get("is_demo_sub_admin")),
    }
    return out


def _random_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class SubAdminCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=80)
    admin_scope: str
    admin_seniority: str = Field(default="junior")
    reports_to: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=80)


class SubAdminPatch(BaseModel):
    admin_scope: Optional[str] = None
    admin_seniority: Optional[str] = None
    reports_to: Optional[str] = None
    is_active: Optional[bool] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)


@router.get("/me/scope")
async def my_scope(user: dict = Depends(get_current_user)):
    """Any logged-in admin can read their own scope (for UI sidebar filtering)."""
    if user.get("role") != "admin":
        raise HTTPException(403, "Admin role required")
    return {
        "admin_scope": user.get("admin_scope") or "general",
        "admin_seniority": user.get("admin_seniority") or "senior",
        "is_super_admin": is_super_admin(user),
        "reports_to": user.get("reports_to"),
        "email": user.get("email"),
        "name": user.get("name"),
    }


@router.get("")
async def list_sub_admins(user: dict = Depends(get_current_user)):
    _require_super(user)
    cursor = db.users.find(
        {"role": "admin"},
        sort=[("created_at", -1)],
    )
    items = [_strip(u) async for u in cursor]
    return {"items": items, "count": len(items)}


@router.post("")
async def create_sub_admin(payload: SubAdminCreate, user: dict = Depends(get_current_user)):
    _require_super(user)
    if payload.admin_scope not in ALLOWED_SCOPES:
        raise HTTPException(400, f"admin_scope must be in {sorted(ALLOWED_SCOPES)}")
    if payload.admin_seniority not in ALLOWED_SENIORITY:
        raise HTTPException(400, f"admin_seniority must be in {sorted(ALLOWED_SENIORITY)}")
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(409, "Email deja folosit")

    raw_pw = payload.password or _random_password()
    pw_hash = bcrypt.hashpw(raw_pw.encode(), bcrypt.gensalt()).decode()
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "email": payload.email,
        "name": payload.name,
        "role": "admin",
        "admin_scope": payload.admin_scope,
        "admin_seniority": payload.admin_seniority,
        "reports_to": payload.reports_to,
        "password_hash": pw_hash,
        "verified": True,
        "email_verified": True,
        "phone_verified": False,
        "wallet_balance": 0,
        "tokens": 0,
        "tier": "",
        "is_active": True,
        "created_at": now_iso,
        "updated_at": now_iso,
        "created_by": user["id"],
        "consent_grandfathered": True,
        "terms_accepted": True,
        "privacy_policy_accepted": True,
    }
    res = await db.users.insert_one(doc)
    return {
        "ok": True,
        "id": str(res.inserted_id),
        "email": payload.email,
        "name": payload.name,
        "admin_scope": payload.admin_scope,
        "admin_seniority": payload.admin_seniority,
        # IMPORTANT: returned ONLY at creation so admin can communicate it to the user.
        "initial_password": raw_pw,
    }


@router.patch("/{admin_id}")
async def patch_sub_admin(
    admin_id: str,
    payload: SubAdminPatch,
    user: dict = Depends(get_current_user),
):
    _require_super(user)
    try:
        oid = ObjectId(admin_id)
    except Exception:
        raise HTTPException(400, "Invalid id")
    target = await db.users.find_one({"_id": oid, "role": "admin"})
    if not target:
        raise HTTPException(404, "Sub-admin not found")
    # Prevent the super-admin from accidentally demoting themselves
    if str(target["_id"]) == user["id"] and payload.admin_scope and payload.admin_scope != "general":
        raise HTTPException(400, "Nu poți schimba propriul scope (general) — ar duce la lockout.")

    update = {}
    if payload.admin_scope is not None:
        if payload.admin_scope not in ALLOWED_SCOPES:
            raise HTTPException(400, f"admin_scope must be in {sorted(ALLOWED_SCOPES)}")
        update["admin_scope"] = payload.admin_scope
    if payload.admin_seniority is not None:
        if payload.admin_seniority not in ALLOWED_SENIORITY:
            raise HTTPException(400, f"admin_seniority must be in {sorted(ALLOWED_SENIORITY)}")
        update["admin_seniority"] = payload.admin_seniority
    if payload.reports_to is not None:
        update["reports_to"] = payload.reports_to or None
    if payload.is_active is not None:
        update["is_active"] = bool(payload.is_active)
    if payload.name is not None:
        update["name"] = payload.name
    if not update:
        raise HTTPException(400, "Nothing to update")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_by"] = user["id"]
    await db.users.update_one({"_id": oid}, {"$set": update})
    fresh = await db.users.find_one({"_id": oid})
    return {"ok": True, "item": _strip(fresh)}


@router.post("/{admin_id}/reset-password")
async def reset_sub_admin_password(admin_id: str, user: dict = Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(admin_id)
    except Exception:
        raise HTTPException(400, "Invalid id")
    target = await db.users.find_one({"_id": oid, "role": "admin"})
    if not target:
        raise HTTPException(404, "Sub-admin not found")
    new_pw = _random_password()
    pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    await db.users.update_one(
        {"_id": oid},
        {"$set": {
            "password_hash": pw_hash,
            "password_reset_at": datetime.now(timezone.utc).isoformat(),
            "password_reset_by": user["id"],
        }},
    )
    return {"ok": True, "email": target.get("email"), "new_password": new_pw}


@router.delete("/{admin_id}")
async def deactivate_sub_admin(admin_id: str, user: dict = Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(admin_id)
    except Exception:
        raise HTTPException(400, "Invalid id")
    if str(oid) == user["id"]:
        raise HTTPException(400, "Nu te poți dezactiva pe tine.")
    await db.users.update_one(
        {"_id": oid, "role": "admin"},
        {"$set": {
            "is_active": False,
            "deactivated_at": datetime.now(timezone.utc).isoformat(),
            "deactivated_by": user["id"],
        }},
    )
    return {"ok": True, "deactivated": admin_id}


@router.get("/audit")
async def audit_log(
    limit: int = 100,
    scope: Optional[str] = None,
    outcome: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    _require_super(user)
    limit = min(max(int(limit), 1), 500)
    q: dict = {}
    if scope:
        q["scope"] = scope.lower()
    if outcome in ("allowed", "denied"):
        q["outcome"] = outcome
    cursor = db.admin_actions_log.find(q, {"_id": 0}).sort("ts", -1).limit(limit)
    items = [d async for d in cursor]
    # Aggregate counts per scope (for chips in UI)
    counts: dict = {}
    async for d in db.admin_actions_log.aggregate([
        {"$group": {"_id": "$scope", "n": {"$sum": 1}}},
    ]):
        counts[d.get("_id") or "unknown"] = d.get("n", 0)
    return {"items": items, "count": len(items), "scope_counts": counts}


@router.get("/productivity")
async def productivity_scores(user: dict = Depends(get_current_user)):
    """Per-admin productivity score (super-only).

    Score formula (0-100):
      base = success_rate * 60                         # quality (allowed / total actions)
      + activity_factor * 25                           # active days ratio in last 30d
      + approvals_factor * 15                          # approvals reviewed bonus
    Clamped 0..100. Zero-activity → score 0.

    Also returns a 7-day mini history (one score per day) for sparkline rendering.
    """
    _require_super(user)
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff_30d = (now - timedelta(days=30)).isoformat()
    cutoff_7d = (now - timedelta(days=7)).isoformat()

    # 1. Pull all admins
    admins = []
    async for a in db.users.find({"role": "admin"}):
        admins.append(a)

    # 2. Aggregate actions per email (last 30d), success rate, last seen, active days
    actions_by_email: dict = {}
    # Also a per-email per-day bucket for the 7-day sparkline (last 7 days only)
    daily_by_email: dict = {}
    async for log in db.admin_actions_log.find(
        {"ts": {"$gte": cutoff_30d}},
        {"_id": 0, "user_email": 1, "outcome": 1, "ts": 1, "path": 1, "method": 1},
    ):
        email = log.get("user_email")
        if not email:
            continue
        rec = actions_by_email.setdefault(email, {
            "total": 0,
            "allowed": 0,
            "denied": 0,
            "last_ts": None,
            "active_days": set(),
            "unique_paths": set(),
        })
        rec["total"] += 1
        if log.get("outcome") == "allowed":
            rec["allowed"] += 1
        elif log.get("outcome") == "denied":
            rec["denied"] += 1
        ts_str = log.get("ts") or ""
        try:
            if not rec["last_ts"] or ts_str > rec["last_ts"]:
                rec["last_ts"] = ts_str
            rec["active_days"].add(ts_str[:10])
        except Exception:  # noqa: BLE001
            pass
        if log.get("path"):
            rec["unique_paths"].add(log["path"])
        # Bucket into per-day for last 7d
        if ts_str >= cutoff_7d:
            day_key = ts_str[:10]
            day_bucket = daily_by_email.setdefault(email, {}).setdefault(day_key, {"a": 0, "d": 0})
            if log.get("outcome") == "allowed":
                day_bucket["a"] += 1
            elif log.get("outcome") == "denied":
                day_bucket["d"] += 1

    # 3. Approvals decided & requested per admin id
    approvals_decided: dict = {}
    approvals_requested: dict = {}
    async for ap in db.admin_approvals.find(
        {},
        {"_id": 0, "decided_by": 1, "decided_by_email": 1, "requested_by": 1, "status": 1},
    ):
        if ap.get("decided_by") and ap.get("status") in {"approved", "rejected"}:
            approvals_decided[ap["decided_by"]] = approvals_decided.get(ap["decided_by"], 0) + 1
        if ap.get("requested_by"):
            approvals_requested[ap["requested_by"]] = approvals_requested.get(ap["requested_by"], 0) + 1

    # Pre-compute the 7-day labels (oldest -> newest)
    today = now.date()
    day_labels = [(today - timedelta(days=6 - i)).isoformat() for i in range(7)]

    # 4. Build per-admin records + compute score
    items = []
    for a in admins:
        email = a.get("email")
        admin_id = str(a.get("_id"))
        rec = actions_by_email.get(email, {})
        total = rec.get("total", 0)
        allowed = rec.get("allowed", 0)
        denied = rec.get("denied", 0)
        active_days = len(rec.get("active_days", set()))
        unique_paths = len(rec.get("unique_paths", set()))
        last_ts = rec.get("last_ts")

        # Sub-scores
        success_rate = (allowed / total) if total > 0 else 0.0
        activity_factor = min(active_days / 20.0, 1.0)  # 20+ active days in 30d = full
        approvals_reviewed = approvals_decided.get(admin_id, 0)
        approvals_factor = min(approvals_reviewed / 5.0, 1.0)  # 5+ decisions = full

        score = 0.0
        if total > 0:
            score = (success_rate * 60.0) + (activity_factor * 25.0) + (approvals_factor * 15.0)
        score = round(min(max(score, 0.0), 100.0), 1)

        # 7-day sparkline: daily score = success_rate of that day * 100 (capped 0-100)
        # If a day has 0 actions → 0 for that point (idle).
        days_data = daily_by_email.get(email, {})
        sparkline = []
        for day in day_labels:
            bucket = days_data.get(day)
            if not bucket or (bucket["a"] + bucket["d"]) == 0:
                sparkline.append(0)
            else:
                day_total = bucket["a"] + bucket["d"]
                day_score = (bucket["a"] / day_total) * 100
                sparkline.append(round(day_score, 1))

        items.append({
            "id": admin_id,
            "email": email,
            "name": a.get("name"),
            "admin_scope": a.get("admin_scope") or "general",
            "admin_seniority": a.get("admin_seniority") or "senior",
            "is_active": a.get("is_active", True),
            "score": score,
            "sparkline": sparkline,
            "sparkline_days": day_labels,
            "metrics": {
                "actions_30d": total,
                "allowed": allowed,
                "denied": denied,
                "success_rate_pct": round(success_rate * 100, 1),
                "active_days_30d": active_days,
                "unique_paths_30d": unique_paths,
                "approvals_reviewed": approvals_reviewed,
                "approvals_requested": approvals_requested.get(admin_id, 0),
                "last_action_ts": last_ts,
            },
        })

    items.sort(key=lambda x: (x["score"], x["metrics"]["actions_30d"]), reverse=True)
    return {"items": items, "count": len(items)}
