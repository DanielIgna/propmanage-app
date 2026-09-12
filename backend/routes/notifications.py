"""PropManage router: notifications."""
import logging
from bson import ObjectId
from fastapi import APIRouter, Depends

from db import db
from core_utils import serialize_doc
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["notifications"])

# ============= EMAIL / NOTIFICATIONS / ACTIVITY LOG — helpers moved to services.py =============

@router.get("/notifications")
async def list_notifications(user: dict = Depends(get_current_user)):
    """Get in-app notifications for current user"""
    docs = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).limit(50).to_list(50)
    return [serialize_doc(d) for d in docs]


@router.post("/notifications/{notif_id}/read")
async def mark_read(notif_id: str, user: dict = Depends(get_current_user)):
    await db.notifications.update_one(
        {"_id": ObjectId(notif_id), "user_id": user["id"]},
        {"$set": {"read": True}}
    )
    return {"ok": True}


