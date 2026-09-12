"""PropManage — Experience Tiers (Progressive Disclosure)

Progressive Disclosure system: users start with a simple UI ("junior") and
unlock more advanced features as they accumulate activity ("regular" →
"verified" → "pro"). Promotes founder's vision: friendly UX for newbies,
power tools for veterans.

Tiers per role:
  - client:     junior → regular → verified → pro
  - specialist: junior → regular → verified → pro

Promotion criteria (from /app/docs/OPERATING_MANUAL.md cap 11):
  junior → regular:   7 days active + 3 completed requests/offers
  regular → verified: 30 days active + 10 completed + rating >= 4.5
  verified → pro:     90 days + 30 completed + email verified + KYC complete

Storage:
  - users.experience_tier (string)
  - users.experience_tier_set_at (ISO date)
  - users.experience_tier_locked (bool — admin override prevents auto-promote)
  - experience_tier_history (collection: who promoted, when, from→to, reason)
  - experience_tier_config (singleton "config": criteria thresholds + enabled flag)

Endpoints (all admin-only except `/me/tier` which is user-self):
  GET  /api/admin/experience-tiers/config
  PUT  /api/admin/experience-tiers/config
  GET  /api/admin/experience-tiers/users
  GET  /api/admin/experience-tiers/users/{user_id}
  POST /api/admin/experience-tiers/users/{user_id}/override
  POST /api/admin/experience-tiers/users/{user_id}/unlock
  POST /api/admin/experience-tiers/run-promotion-job (manual trigger)
  GET  /api/admin/experience-tiers/stats
  GET  /api/me/experience-tier  (user-self)

Feature flag matrix (used by frontend `<TierGate>` component):
  - junior:    basic features only
  - regular:   + advanced filters, saved searches
  - verified:  + bulk operations, advanced analytics
  - pro:       + API access, priority support, custom reports
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role, get_current_user
from email_service import send_email, _layout

logger = logging.getLogger("propmanage.experience_tiers")
router = APIRouter(prefix="/api/admin/experience-tiers", tags=["experience-tiers"])
self_router = APIRouter(prefix="/api/me", tags=["experience-tiers"])

TIER_ORDER = ["junior", "regular", "verified", "pro"]

# Feature catalog — what each tier unlocks beyond the previous one.
TIER_FEATURES = {
    "junior": [
        "basic_dashboard", "simple_request_creation", "essential_messages",
    ],
    "regular": [
        "advanced_filters", "saved_searches", "request_templates",
        "comparison_view", "weekly_summary_email",
    ],
    "verified": [
        "bulk_operations", "advanced_analytics", "priority_matching",
        "custom_notifications", "export_data",
    ],
    "pro": [
        "api_access", "white_label_reports", "priority_support",
        "early_access_features", "dedicated_account_manager",
    ],
}

DEFAULT_CONFIG = {
    "enabled": True,
    "criteria": {
        "junior_to_regular": {
            "min_days_active": 7,
            "min_completed_actions": 3,
        },
        "regular_to_verified": {
            "min_days_active": 30,
            "min_completed_actions": 10,
            "min_rating": 4.5,
        },
        "verified_to_pro": {
            "min_days_active": 90,
            "min_completed_actions": 30,
            "require_email_verified": True,
            "require_kyc": True,
        },
    },
}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
async def _load_config() -> dict:
    doc = await db.experience_tier_config.find_one({"_id": "config"})
    if not doc:
        return {**DEFAULT_CONFIG}
    out = {
        "enabled": bool(doc.get("enabled", True)),
        "criteria": doc.get("criteria") or DEFAULT_CONFIG["criteria"],
    }
    return out


def _next_tier(current: str) -> Optional[str]:
    try:
        idx = TIER_ORDER.index(current)
    except ValueError:
        return TIER_ORDER[0]
    if idx + 1 >= len(TIER_ORDER):
        return None
    return TIER_ORDER[idx + 1]


def _tier_index(tier: str) -> int:
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 0


def _unlocked_features(tier: str) -> list:
    """All features unlocked at the given tier (inclusive of lower tiers)."""
    idx = _tier_index(tier)
    out = []
    for t in TIER_ORDER[: idx + 1]:
        out.extend(TIER_FEATURES.get(t, []))
    return out


async def _user_progress(user: dict, cfg: dict) -> dict:
    """Compute the user's progress towards the next tier."""
    user_id = str(user.get("_id") or user.get("id"))
    role = user.get("role", "client")
    current_tier = user.get("experience_tier") or "junior"

    # Days since signup
    created_at = user.get("created_at")
    days_active = 0
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if isinstance(created_at, str) else created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days_active = (datetime.now(timezone.utc) - dt).days
        except Exception:  # noqa: BLE001
            pass

    # Completed actions
    completed_count = 0
    if role == "client":
        completed_count = await db.requests.count_documents({
            "client_id": user_id,
            "status": {"$in": ["completed", "confirmed"]},
        })
    elif role == "specialist":
        completed_count = await db.requests.count_documents({
            "assigned_specialist_id": user_id,
            "status": {"$in": ["completed", "confirmed"]},
        })

    # Rating (specialist-side)
    rating = float(user.get("rating") or 0.0)

    # KYC / email verification (best-effort)
    email_verified = bool(user.get("email_verified") or user.get("google_auth"))
    kyc_complete = bool(user.get("verified") and user.get("kyc_status") in (None, "verified", "approved"))

    nxt = _next_tier(current_tier)
    eligible_for = None
    requirements = []
    if nxt:
        c = cfg["criteria"]
        key = f"{current_tier}_to_{nxt}"
        crit = c.get(key, {})
        checks = []
        if "min_days_active" in crit:
            ok = days_active >= int(crit["min_days_active"])
            checks.append(("days_active", days_active, crit["min_days_active"], ok))
        if "min_completed_actions" in crit:
            ok = completed_count >= int(crit["min_completed_actions"])
            checks.append(("completed_actions", completed_count, crit["min_completed_actions"], ok))
        if "min_rating" in crit:
            ok = rating >= float(crit["min_rating"])
            checks.append(("rating", rating, crit["min_rating"], ok))
        if crit.get("require_email_verified"):
            checks.append(("email_verified", email_verified, True, email_verified))
        if crit.get("require_kyc"):
            checks.append(("kyc_complete", kyc_complete, True, kyc_complete))

        all_met = all(c[3] for c in checks)
        if all_met:
            eligible_for = nxt
        requirements = [
            {"name": n, "current": cur, "needed": need, "satisfied": ok}
            for n, cur, need, ok in checks
        ]

    return {
        "user_id": user_id,
        "email": user.get("email"),
        "role": role,
        "current_tier": current_tier,
        "next_tier": nxt,
        "eligible_for": eligible_for,
        "days_active": days_active,
        "completed_actions": completed_count,
        "rating": rating,
        "email_verified": email_verified,
        "kyc_complete": kyc_complete,
        "requirements": requirements,
        "locked": bool(user.get("experience_tier_locked", False)),
        "unlocked_features": _unlocked_features(current_tier),
    }


async def _send_tier_celebration(user_id: str, user_email: str, from_tier: str, to_tier: str):
    """Best-effort celebration on tier promotion: email + in-app notification + dashboard banner flag.

    Failures here MUST NOT break the promotion itself.
    """
    if from_tier == to_tier:
        return
    # New features unlocked (only the delta — what's new at the to_tier)
    new_features = TIER_FEATURES.get(to_tier, [])
    feature_labels_ro = {
        "advanced_filters": "Filtre avansate",
        "saved_searches": "Căutări salvate",
        "request_templates": "Șabloane cereri",
        "comparison_view": "Vedere comparativă",
        "weekly_summary_email": "Email sumar săptămânal",
        "bulk_operations": "Operațiuni în masă",
        "advanced_analytics": "Analize avansate",
        "priority_matching": "Matching prioritar",
        "custom_notifications": "Notificări personalizate",
        "export_data": "Export date",
        "api_access": "Acces API",
        "white_label_reports": "Rapoarte white-label",
        "priority_support": "Support prioritar",
        "early_access_features": "Acces early la features",
        "dedicated_account_manager": "Account manager dedicat",
    }
    pretty_features = [feature_labels_ro.get(f, f) for f in new_features]

    tier_label_ro = {"junior": "Junior", "regular": "Regular", "verified": "Verificat", "pro": "Pro"}
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1) Mark dashboard banner pending (consumed on next login)
    try:
        oid = ObjectId(user_id)
        await db.users.update_one(
            {"_id": oid},
            {"$set": {
                "tier_celebration_pending": {
                    "from": from_tier,
                    "to": to_tier,
                    "new_features": new_features,
                    "created_at": now_iso,
                }
            }},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tier_celebration] banner flag failed: {e}")

    # 2) In-app notification (best-effort)
    try:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": "tier_promotion",
            "title": f"🎉 Felicitări! Ai fost promovat la {tier_label_ro.get(to_tier, to_tier)}",
            "message": f"Ai deblocat {len(new_features)} funcții noi pe platformă.",
            "data": {"from": from_tier, "to": to_tier, "new_features": new_features},
            "read": False,
            "created_at": now_iso,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tier_celebration] notification insert failed: {e}")

    # 3) Email (Resend via email_service.send_email)
    if user_email:
        try:
            features_html = "".join([
                f'<li style="padding:6px 0;color:#d4d4d8;font-size:14px;">✨ {f}</li>'
                for f in pretty_features
            ]) or '<li style="color:#a1a1aa;font-size:13px;">Funcționalitățile complete devin disponibile pe dashboard.</li>'
            body = f"""
            <tr><td style="padding:32px;">
              <div style="font-size:11px;letter-spacing:.08em;color:#d4ff3a;text-transform:uppercase;margin-bottom:8px;">Promovare automată</div>
              <h1 style="margin:0 0 12px 0;font-size:28px;color:#fff;line-height:1.2;">🎉 Felicitări!</h1>
              <p style="margin:0 0 14px 0;font-size:15px;color:#d4d4d8;line-height:1.6;">
                Ai fost promovat de la <strong style="color:#fff;">{tier_label_ro.get(from_tier, from_tier)}</strong>
                la <strong style="color:#d4ff3a;">{tier_label_ro.get(to_tier, to_tier)}</strong>
                pentru activitatea ta pe PropManage.
              </p>
              <div style="background:#1a1a1d;border:1px solid #ffffff15;border-radius:14px;padding:18px;margin:20px 0;">
                <div style="font-size:11px;letter-spacing:.08em;color:#a1a1aa;text-transform:uppercase;margin-bottom:8px;">Ai deblocat</div>
                <ul style="margin:0;padding:0 0 0 4px;list-style:none;">{features_html}</ul>
              </div>
              <p style="margin:0;font-size:13px;color:#a1a1aa;line-height:1.5;">
                Funcționalitățile noi apar automat pe dashboard la următoarea conectare. Mulțumim că faci parte din ecosistemul PropManage.
              </p>
            </td></tr>
            """
            html = _layout(
                title="Felicitări — promovare PropManage",
                preheader=f"Ai fost promovat la {tier_label_ro.get(to_tier, to_tier)} — vezi ce ai deblocat",
                body_html=body,
                cta_url="https://propmanage.ro/dashboard",
                cta_label="Vezi dashboard-ul",
            )
            await send_email(
                user_email,
                f"🎉 Ai fost promovat la {tier_label_ro.get(to_tier, to_tier)} pe PropManage",
                html,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[tier_celebration] email send failed for {user_email}: {e}")


async def _set_tier(user_id: str, new_tier: str, reason: str, by_email: str, locked: bool = False):
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        oid = ObjectId(user_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(400, f"Invalid user_id: {user_id}")
    existing = await db.users.find_one({"_id": oid}, {"experience_tier": 1, "email": 1})
    if not existing:
        raise HTTPException(404, f"User not found: {user_id}")
    prev = existing.get("experience_tier") or "junior"
    update = {
        "experience_tier": new_tier,
        "experience_tier_set_at": now_iso,
    }
    if locked is not None:
        update["experience_tier_locked"] = bool(locked)
    await db.users.update_one({"_id": oid}, {"$set": update})
    await db.experience_tier_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": existing.get("email"),
        "from": prev,
        "to": new_tier,
        "reason": reason,
        "by_email": by_email,
        "at": now_iso,
    })
    # Trigger celebration only on actual upward promotions (not lateral/downgrade)
    if prev != new_tier and _tier_index(new_tier) > _tier_index(prev):
        try:
            await _send_tier_celebration(user_id, existing.get("email"), prev, new_tier)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[tier_celebration] outer hook failed: {e}")
    return {"user_id": user_id, "from": prev, "to": new_tier, "locked": locked, "at": now_iso}


# ----------------------------------------------------------------------
# Promotion job (cron-friendly)
# ----------------------------------------------------------------------
async def run_promotion_job(dry_run: bool = False) -> dict:
    """Scan users + auto-promote those who meet criteria. Skip locked users."""
    cfg = await _load_config()
    if not cfg["enabled"] and not dry_run:
        return {"skipped": "disabled", "promoted": 0}

    promoted = []
    skipped_locked = 0
    scanned = 0
    cursor = db.users.find({
        "role": {"$in": ["client", "specialist"]},
        "experience_tier_locked": {"$ne": True},
    })
    async for u in cursor:
        scanned += 1
        prog = await _user_progress(u, cfg)
        if prog["eligible_for"]:
            if not dry_run:
                await _set_tier(
                    user_id=str(u["_id"]),
                    new_tier=prog["eligible_for"],
                    reason="auto_promotion_job",
                    by_email="system@autopromote",
                )
            promoted.append({
                "user_id": str(u["_id"]),
                "email": u.get("email"),
                "from": prog["current_tier"],
                "to": prog["eligible_for"],
            })

    # Count locked separately
    skipped_locked = await db.users.count_documents({
        "role": {"$in": ["client", "specialist"]},
        "experience_tier_locked": True,
    })

    return {
        "scanned": scanned,
        "promoted_count": len(promoted),
        "promoted": promoted[:50],
        "skipped_locked": skipped_locked,
        "dry_run": dry_run,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }


# ----------------------------------------------------------------------
# Admin API
# ----------------------------------------------------------------------
class ConfigPatch(BaseModel):
    enabled: Optional[bool] = None
    criteria: Optional[dict] = None


class OverrideIn(BaseModel):
    tier: str = Field(...)
    reason: str = Field(default="admin_manual_override", max_length=300)
    lock: bool = Field(default=True, description="If true, blocks future auto-promotions for this user.")


@router.get("/config")
async def get_config(user=Depends(require_role("admin"))):
    return await _load_config()


@router.put("/config")
async def update_config(patch: ConfigPatch, user=Depends(require_role("admin"))):
    update = {}
    if patch.enabled is not None:
        update["enabled"] = patch.enabled
    if patch.criteria is not None:
        update["criteria"] = patch.criteria
    if update:
        await db.experience_tier_config.update_one(
            {"_id": "config"}, {"$set": update}, upsert=True,
        )
    return await _load_config()


@router.get("/users")
async def list_users_with_tiers(
    limit: int = 50,
    role: Optional[str] = None,
    tier: Optional[str] = None,
    user=Depends(require_role("admin")),
):
    q: dict = {"role": {"$in": ["client", "specialist"]}}
    if role:
        q["role"] = role
    if tier:
        q["experience_tier"] = tier
    cfg = await _load_config()
    items = []
    cursor = db.users.find(q).limit(limit)
    async for u in cursor:
        prog = await _user_progress(u, cfg)
        items.append(prog)
    return {"items": items, "count": len(items)}


@router.get("/users/{user_id}")
async def get_user_tier(user_id: str, user=Depends(require_role("admin"))):
    try:
        oid = ObjectId(user_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Invalid user_id")
    u = await db.users.find_one({"_id": oid})
    if not u:
        raise HTTPException(404, "User not found")
    cfg = await _load_config()
    prog = await _user_progress(u, cfg)
    history_cur = db.experience_tier_history.find({"user_id": user_id}).sort("at", -1).limit(20)
    history = []
    async for h in history_cur:
        h.pop("_id", None)
        history.append(h)
    prog["history"] = history
    return prog


@router.post("/users/{user_id}/override")
async def override_tier(user_id: str, payload: OverrideIn, user=Depends(require_role("admin"))):
    if payload.tier not in TIER_ORDER:
        raise HTTPException(400, f"Invalid tier. Must be one of {TIER_ORDER}")
    result = await _set_tier(
        user_id=user_id,
        new_tier=payload.tier,
        reason=payload.reason or "admin_manual_override",
        by_email=user.get("email", "admin"),
        locked=payload.lock,
    )
    return result


@router.post("/users/{user_id}/unlock")
async def unlock_tier(user_id: str, user=Depends(require_role("admin"))):
    try:
        oid = ObjectId(user_id)
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Invalid user_id")
    res = await db.users.update_one({"_id": oid}, {"$set": {"experience_tier_locked": False}})
    if res.matched_count == 0:
        raise HTTPException(404, "User not found")
    return {"ok": True, "user_id": user_id, "locked": False}


@router.post("/run-promotion-job")
async def trigger_promotion_job(payload: dict = Body(default={}), user=Depends(require_role("admin"))):
    dry_run = bool(payload.get("dry_run", False))
    return await run_promotion_job(dry_run=dry_run)


@router.get("/stats")
async def get_stats(user=Depends(require_role("admin"))):
    """Distribution of users per tier, per role."""
    pipeline = [
        {"$match": {"role": {"$in": ["client", "specialist"]}}},
        {"$group": {
            "_id": {"tier": {"$ifNull": ["$experience_tier", "junior"]}, "role": "$role"},
            "count": {"$sum": 1},
        }},
    ]
    grid = {r: {t: 0 for t in TIER_ORDER} for r in ["client", "specialist"]}
    total_per_role = {"client": 0, "specialist": 0}
    async for doc in db.users.aggregate(pipeline):
        t = doc["_id"]["tier"]
        r = doc["_id"]["role"]
        c = doc["count"]
        if r in grid and t in grid[r]:
            grid[r][t] = c
            total_per_role[r] += c
    # Locked count
    locked = await db.users.count_documents({
        "role": {"$in": ["client", "specialist"]},
        "experience_tier_locked": True,
    })
    return {
        "distribution": grid,
        "totals_per_role": total_per_role,
        "locked_count": locked,
        "tiers": TIER_ORDER,
        "features_per_tier": TIER_FEATURES,
    }


@router.get("/history")
async def history(limit: int = 50, user=Depends(require_role("admin"))):
    cursor = db.experience_tier_history.find({}, {"_id": 0}).sort("at", -1).limit(limit)
    items = []
    async for d in cursor:
        items.append(d)
    return {"items": items, "count": len(items)}


# ----------------------------------------------------------------------
# Self-service: user's own tier
# ----------------------------------------------------------------------
@self_router.get("/experience-tier")
async def my_tier(user=Depends(get_current_user)):
    """Return the current user's tier + features + progress to next."""
    try:
        oid = ObjectId(user["id"])
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Invalid user")
    u = await db.users.find_one({"_id": oid})
    if not u:
        raise HTTPException(404, "User not found")
    cfg = await _load_config()
    return await _user_progress(u, cfg)


@self_router.get("/tier-celebration")
async def get_tier_celebration(user=Depends(get_current_user)):
    """Return the pending celebration banner (if any) for the current user."""
    try:
        oid = ObjectId(user["id"])
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Invalid user")
    u = await db.users.find_one({"_id": oid}, {"tier_celebration_pending": 1})
    pending = (u or {}).get("tier_celebration_pending")
    if not pending:
        return {"pending": None}
    feature_labels_ro = {
        "advanced_filters": "Filtre avansate",
        "saved_searches": "Căutări salvate",
        "request_templates": "Șabloane cereri",
        "comparison_view": "Vedere comparativă",
        "weekly_summary_email": "Email sumar săptămânal",
        "bulk_operations": "Operațiuni în masă",
        "advanced_analytics": "Analize avansate",
        "priority_matching": "Matching prioritar",
        "custom_notifications": "Notificări personalizate",
        "export_data": "Export date",
        "api_access": "Acces API",
        "white_label_reports": "Rapoarte white-label",
        "priority_support": "Support prioritar",
        "early_access_features": "Acces early la features",
        "dedicated_account_manager": "Account manager dedicat",
    }
    new_features_pretty = [feature_labels_ro.get(f, f) for f in (pending.get("new_features") or [])]
    return {
        "pending": {
            "from": pending.get("from"),
            "to": pending.get("to"),
            "new_features": pending.get("new_features") or [],
            "new_features_pretty": new_features_pretty,
            "created_at": pending.get("created_at"),
        }
    }


@self_router.post("/tier-celebration/dismiss")
async def dismiss_tier_celebration(user=Depends(get_current_user)):
    """Clear the pending celebration banner once the user has seen it."""
    try:
        oid = ObjectId(user["id"])
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Invalid user")
    await db.users.update_one({"_id": oid}, {"$unset": {"tier_celebration_pending": ""}})
    return {"ok": True}
