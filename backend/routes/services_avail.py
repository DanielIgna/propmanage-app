"""PropManage router: services_avail."""
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends

from db import db
from core_utils import serialize_doc
from deps import require_role
from models import ServiceAvailabilityIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["services_avail"])

# ============= SERVICE AVAILABILITY (Admin-controlled per region) =============

@router.get("/services/availability")
async def get_service_availability(zone: Optional[str] = None, user: Optional[dict] = None):
    """Returns which services are available in user's zone"""
    # Public endpoint - no auth required for browsing
    q = {}
    if zone:
        q["zone"] = zone
    docs = await db.service_availability.find(q).to_list(200)
    
    # Default services if none configured
    default_services = ["plumbing", "electric", "hvac", "maintenance", "interior_design"]
    result = {}
    for s in default_services:
        result[s] = {"state": "active", "min_specialists": 1}
    for d in docs:
        if d.get("service"):
            result[d["service"]] = {
                "state": d.get("state", "active"),
                "min_specialists": d.get("min_specialists", 1),
                "region_id": d.get("region_id"),
            }
    return result


@router.post("/admin/services/availability")
async def set_service_availability(data: ServiceAvailabilityIn, user: dict = Depends(require_role("admin"))):
    """Admin: enable/disable/limit services per region"""
    await db.service_availability.update_one(
        {"region_id": data.region_id, "service": data.service},
        {"$set": {**data.model_dump(), "updated_by": user["id"], "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"ok": True, **data.model_dump()}


@router.get("/admin/services")
async def admin_list_services(user: dict = Depends(require_role("admin"))):
    """Admin: list all service availability configurations"""
    docs = await db.service_availability.find({}).to_list(500)
    return [serialize_doc(d) for d in docs]


