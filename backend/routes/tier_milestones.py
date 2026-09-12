"""
Tier Milestone Push Notifications (Feb 2026)
============================================
Sends a notification when a user crosses 50% / 75% / 100% on tier progression.
Mirrors the frontend tierProgression.js logic in Python.

Hook points (call check_tier_milestones(user_id) after):
  - Job confirmation (specialist + client jobs_completed change)
  - KYC approval (verified / kyc_status change)
  - Review submission (rating change)

Idempotency: stores `last_milestone_notified` on user document. Once a user
crossed 75%, they won't get the 50% notification again. Notification fires
only when the crossed level is HIGHER than last_milestone_notified.

Respects user preference `notify_tier_milestones` (default True).
"""
import logging
from typing import Optional
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends

from db import db
from deps import get_current_user

logger = logging.getLogger("propmanage.tier_milestones")
router = APIRouter(prefix="/api/tier-milestones", tags=["tier-milestones"])

# ============= LADDERS (mirror of frontend tierProgression.js) =============
SPECIALIST_LADDER = [
    {"from": "ENTRY", "to": "JUNIOR", "reqs": [("jobs_completed", 1)]},
    {"from": "JUNIOR", "to": "VERIFIED", "reqs": [("jobs_completed", 5), ("verified", 1)]},
    {"from": "VERIFIED", "to": "ADVANCED", "reqs": [("jobs_completed", 20), ("rating", 4.5)]},
    {"from": "ADVANCED", "to": "PREMIUM", "reqs": [("jobs_completed", 50), ("rating", 4.7)]},
    {"from": "PREMIUM", "to": "TOP", "reqs": [("jobs_completed", 100), ("rating", 4.9)]},
]
CLIENT_LADDER = [
    {"from": "JUNIOR", "to": "VERIFIED", "reqs": [("kyc_or_first_job", 1)]},
    {"from": "VERIFIED", "to": "PREMIUM", "reqs": [("jobs_completed", 5)]},
]

MILESTONES = [50, 75, 100]


def _measure(user: dict, key: str) -> float:
    """Mirror of frontend measure functions."""
    if key == "jobs_completed":
        return float(user.get("jobs_completed") or 0)
    if key == "rating":
        return float(user.get("rating") or 0)
    if key == "verified":
        return 1.0 if user.get("verified") else 0.0
    if key == "kyc_or_first_job":
        return 1.0 if (user.get("kyc_status") == "approved" or (user.get("jobs_completed") or 0) >= 1) else 0.0
    return 0.0


def _compute_progress(user: dict) -> Optional[dict]:
    """Returns {current_tier, next_tier, overall_pct, pending_label, all_done} or None if at top."""
    role = user.get("role")
    ladder = SPECIALIST_LADDER if role == "specialist" else CLIENT_LADDER if role == "client" else None
    if not ladder:
        return None
    current_tier = (user.get("tier") or ("ENTRY" if role == "specialist" else "JUNIOR")).upper()
    step = next((s for s in ladder if s["from"] == current_tier), None)
    if not step:
        return None
    pcts = []
    pending = None
    for key, minimum in step["reqs"]:
        current = _measure(user, key)
        pct = min(100.0, (current / minimum) * 100.0) if minimum > 0 else 100.0
        pcts.append(pct)
        if current < minimum and pending is None:
            pending = (key, current, minimum)
    overall = round(sum(pcts) / max(1, len(pcts)))
    return {
        "current_tier": current_tier,
        "next_tier": step["to"],
        "overall_pct": overall,
        "pending": pending,
        "all_done": pending is None,
    }


def _milestone_for_pct(pct: int) -> Optional[int]:
    """Returns highest milestone the user has crossed (e.g. 78 -> 75)."""
    for m in reversed(MILESTONES):
        if pct >= m:
            return m
    return None


def _build_message(progress: dict, milestone: int) -> tuple[str, str]:
    """Returns (title, body) localized in Romanian."""
    next_tier = progress["next_tier"]
    pending = progress["pending"]
    if milestone == 100:
        title = f"🎉 Ai îndeplinit toate cerințele pentru {next_tier}!"
        body = "Promovarea se face automat. Verifică tab-ul Notificări în curând."
    elif milestone == 75:
        title = f"🚀 75% până la {next_tier}!"
        if pending:
            key, current, minimum = pending
            if key == "rating":
                body = f"Ești foarte aproape. Mai ai nevoie de rating {minimum} (acum {current:.1f})."
            elif key == "verified":
                body = "Mai ai nevoie să-ți verifici contul."
            else:
                remaining = int(max(0, minimum - current))
                body = f"Mai ai doar {remaining} lucrări până acolo. Continuă!"
        else:
            body = "Aproape gata!"
    elif milestone == 50:
        title = f"💪 Ești la jumătatea drumului către {next_tier}!"
        if pending:
            key, current, minimum = pending
            if key == "rating":
                body = f"Ai 50% — mai ai nevoie de rating {minimum}."
            elif key == "verified":
                body = "Ai 50% — încarcă documentele de verificare ca să avansezi."
            else:
                remaining = int(max(0, minimum - current))
                body = f"Mai ai {remaining} lucrări. Drumul e clar!"
        else:
            body = "Continuă în același ritm."
    else:
        return None, None
    return title, body


async def check_tier_milestones(user_id: str) -> Optional[dict]:
    """
    Compute progress for user and emit a milestone notification if crossed
    a new level (50/75/100) compared to last_milestone_notified.
    Safe to call multiple times — idempotent per milestone.
    """
    try:
        from bson import ObjectId
        # Try multiple id formats — MongoDB ObjectId, string id, or as plain field
        user = None
        try:
            user = await db.users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            pass
        if not user:
            user = await db.users.find_one({"id": user_id})
        if not user:
            user = await db.users.find_one({"_id": user_id})
        if not user:
            return None
        # User opted out?
        if user.get("notify_tier_milestones") is False:
            return None
        progress = _compute_progress(user)
        if not progress:
            return None
        crossed = _milestone_for_pct(progress["overall_pct"])
        if crossed is None:
            return None
        last = user.get("last_milestone_notified") or {}
        last_tier = last.get("tier")
        last_pct = last.get("pct", 0)
        # If we're tracking the same next_tier and already notified at this or higher milestone, skip
        if last_tier == progress["next_tier"] and last_pct >= crossed:
            return None
        title, body = _build_message(progress, crossed)
        if not title:
            return None
        # Insert notification
        notif = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "message": body,
            "type": "tier_milestone",
            "read": False,
            "meta": {
                "milestone": crossed,
                "next_tier": progress["next_tier"],
                "overall_pct": progress["overall_pct"],
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.notifications.insert_one(notif)
        # Update last_milestone_notified
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_milestone_notified": {"tier": progress["next_tier"], "pct": crossed, "at": notif["created_at"]}}},
        )
        # Best-effort web push
        try:
            from services import send_web_push
            await send_web_push(user_id, title, body)
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[tier_milestone] web push skipped: {e}")
        logger.info(f"[tier_milestone] notified user={user_id} milestone={crossed} next_tier={progress['next_tier']}")
        return {"notified": True, "milestone": crossed, "next_tier": progress["next_tier"]}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[tier_milestone] check failed for {user_id}: {e}")
        return None


# ============= ENDPOINTS =============
@router.post("/check")
async def manual_check(user=Depends(get_current_user)):
    """Manually trigger a milestone check for the authenticated user."""
    user_id = user.get("id") or str(user.get("_id"))
    result = await check_tier_milestones(user_id)
    return {"ok": True, "result": result, "user_id": user_id}


@router.patch("/preferences")
async def set_preferences(payload: dict, user=Depends(get_current_user)):
    """Toggle the tier milestone notifications preference."""
    enabled = bool(payload.get("notify_tier_milestones", True))
    user_id = user.get("id") or str(user.get("_id"))
    await db.users.update_one(
        {"$or": [{"id": user_id}, {"_id": user_id}]},
        {"$set": {"notify_tier_milestones": enabled}},
    )
    return {"notify_tier_milestones": enabled}


@router.get("/preferences")
async def get_preferences(user=Depends(get_current_user)):
    """Get the current preference (default True if unset)."""
    return {
        "notify_tier_milestones": user.get("notify_tier_milestones", True),
        "last_milestone_notified": user.get("last_milestone_notified") or None,
    }


# ============= CRON =============
async def cron_check_all_users():
    """Daily cron — re-check all users that haven't been notified at 100% yet."""
    logger.info("[tier_milestone] cron starting")
    count = 0
    async for u in db.users.find({"role": {"$in": ["specialist", "client"]}, "notify_tier_milestones": {"$ne": False}}):
        uid = u.get("id") or str(u.get("_id"))
        result = await check_tier_milestones(uid)
        if result and result.get("notified"):
            count += 1
    logger.info(f"[tier_milestone] cron done. {count} notifications emitted.")
    return count
