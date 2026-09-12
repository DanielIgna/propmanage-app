"""Admin endpoints for the specialist onboarding email drip queue."""
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role
from onboarding_emails import (
    dispatch_due_onboarding_emails,
    cancel_user_onboarding,
    enqueue_specialist_onboarding,
)

router = APIRouter(prefix="/api/admin/onboarding", tags=["admin-onboarding"])


@router.get("/queue")
async def queue_overview(_admin=Depends(require_role("admin"))):
    """Aggregate stats + last 50 rows for the onboarding email queue."""
    pending = await db.onboarding_emails.count_documents({"sent": False})
    sent = await db.onboarding_emails.count_documents({"sent": True, "skipped": {"$ne": True}, "cancelled": {"$ne": True}})
    skipped = await db.onboarding_emails.count_documents({"skipped": True})
    cancelled = await db.onboarding_emails.count_documents({"cancelled": True})
    failed = await db.onboarding_emails.count_documents({"sent": False, "attempts": {"$gte": 3}})
    recent_cursor = db.onboarding_emails.find().sort("created_at", -1).limit(50)
    rows = []
    async for r in recent_cursor:
        r["id"] = str(r.pop("_id"))
        rows.append(r)
    return {
        "stats": {
            "pending": pending,
            "sent": sent,
            "skipped": skipped,
            "cancelled": cancelled,
            "failed": failed,
        },
        "recent": rows,
    }


@router.post("/dispatch-now")
async def dispatch_now(_admin=Depends(require_role("admin"))):
    """Force-run the dispatcher immediately (instead of waiting for the 15-min tick)."""
    summary = await dispatch_due_onboarding_emails()
    return {"ok": True, "summary": summary}


@router.post("/cancel/{user_id}")
async def cancel(user_id: str, _admin=Depends(require_role("admin"))):
    n = await cancel_user_onboarding(user_id)
    return {"ok": True, "cancelled_rows": n}


@router.post("/enqueue/{user_id}")
async def enqueue(user_id: str, _admin=Depends(require_role("admin"))):
    """Manually enqueue the drip for an existing specialist (re-onboarding)."""
    from bson import ObjectId
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(400, "Invalid user id")
    if not user:
        raise HTTPException(404, "User not found")
    if user.get("role") != "specialist":
        raise HTTPException(400, "Onboarding drip is only for specialists")
    n = await enqueue_specialist_onboarding(user_id, user["email"], user.get("name", ""))
    return {"ok": True, "enqueued": n, "already_scheduled": n == 0}
