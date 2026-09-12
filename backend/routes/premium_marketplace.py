"""Sprint D — Premium Marketplace (extended profile for Nivel 3 / PREMIUM tier specialists).

Adds optional rich profile fields ONLY visible to PREMIUM tier specialists:
  - bio_extended (longer description)
  - portfolio_images (up to 12 URLs)
  - services_detailed (list of {name, description, price_range, duration})
  - certifications (list of {name, issuer, year})
  - team_members (list of {name, role, experience_years})
  - availability_calendar (next 14 days slots; future ML uses this)
  - languages, response_time_target_hours, accepts_emergency_calls

Endpoints:
  GET  /api/me/premium-profile          (specialist views own)
  PUT  /api/me/premium-profile          (specialist edits own)
  GET  /api/marketplace/premium         (public — list of premium specialists)
  GET  /api/specialists/{id}/premium    (public — single specialist premium card)

ZERO impact on existing fields. Stored as nested doc `users.premium_profile`.
Access to /premium endpoints is open to all, but only renders for PREMIUM tier.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.premium_marketplace")

router = APIRouter(prefix="/api", tags=["premium-marketplace"])


class ServiceItem(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    description: Optional[str] = Field(None, max_length=500)
    price_range: Optional[str] = Field(None, max_length=80)
    duration: Optional[str] = Field(None, max_length=80)


class CertificationItem(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    issuer: Optional[str] = Field(None, max_length=120)
    year: Optional[int] = Field(None, ge=1980, le=2100)


class TeamMember(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    role: Optional[str] = Field(None, max_length=80)
    experience_years: Optional[int] = Field(None, ge=0, le=80)


class PremiumProfileIn(BaseModel):
    bio_extended: Optional[str] = Field(None, max_length=3000)
    portfolio_images: Optional[List[str]] = Field(None, max_length=12)
    services_detailed: Optional[List[ServiceItem]] = Field(None, max_length=20)
    certifications: Optional[List[CertificationItem]] = Field(None, max_length=15)
    team_members: Optional[List[TeamMember]] = Field(None, max_length=10)
    languages: Optional[List[str]] = Field(None, max_length=8)
    response_time_target_hours: Optional[int] = Field(None, ge=1, le=168)
    accepts_emergency_calls: Optional[bool] = None
    showcase_video_url: Optional[str] = Field(None, max_length=300)


# ============================================================================
# Specialist edits own
# ============================================================================
@router.get("/me/premium-profile")
async def get_my_premium(user: dict = Depends(require_role("specialist"))):
    u = await db.users.find_one({"_id": ObjectId(user["id"])}, {"premium_profile": 1, "tier": 1})
    return {"tier": u.get("tier", "ENTRY"), "is_premium_eligible": (u.get("tier") == "PREMIUM"), "premium_profile": u.get("premium_profile") or {}}


@router.put("/me/premium-profile")
async def update_my_premium(data: PremiumProfileIn, user: dict = Depends(require_role("specialist"))):
    payload = data.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(400, "Nothing to update")
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"premium_profile": payload}})
    return {"ok": True, "updated_fields": list(payload.keys())}


# ============================================================================
# Public — marketplace list (PREMIUM only)
# ============================================================================
@router.get("/marketplace/premium")
async def list_premium_specialists(
    category: Optional[str] = None,
    zone: Optional[str] = None,
    limit: int = Query(20, le=50),
    skip: int = 0,
):
    """Public list of PREMIUM tier specialists with their extended profile."""
    filt = {"role": "specialist", "tier": "PREMIUM", "deleted": {"$ne": True}, "banned": {"$ne": True}}
    if category:
        filt["$or"] = [{"specialty": category}, {"service_categories": category}]
    if zone:
        filt["coverage_zones"] = zone
    total = await db.users.count_documents(filt)
    cursor = db.users.find(filt, {
        "name": 1, "specialty": 1, "service_categories": 1, "coverage_zones": 1,
        "rating": 1, "reviews_count": 1, "tier": 1, "premium_profile": 1,
        "phone": 1, "email": 1, "avatar_url": 1, "tier_warning_low_rating": 1,
    }).sort([("rating", -1), ("reviews_count", -1)]).skip(skip).limit(limit)
    items = []
    async for u in cursor:
        items.append({
            "id": str(u.pop("_id")),
            "name": u.get("name"),
            "specialty": u.get("specialty"),
            "service_categories": u.get("service_categories"),
            "coverage_zones": u.get("coverage_zones"),
            "rating": u.get("rating"),
            "reviews_count": u.get("reviews_count", 0),
            "tier": u.get("tier"),
            "avatar_url": u.get("avatar_url"),
            "low_rating_warning": bool(u.get("tier_warning_low_rating")),
            "premium_profile": u.get("premium_profile") or {},
        })
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/specialists/{specialist_id}/premium")
async def get_premium_card(specialist_id: str):
    """Public single premium card."""
    try:
        u = await db.users.find_one({"_id": ObjectId(specialist_id), "role": "specialist", "tier": "PREMIUM"}, {
            "name": 1, "specialty": 1, "service_categories": 1, "coverage_zones": 1,
            "rating": 1, "reviews_count": 1, "tier": 1, "premium_profile": 1,
            "avatar_url": 1, "tier_warning_low_rating": 1, "verified": 1,
        })
    except Exception:
        u = None
    if not u:
        raise HTTPException(404, "Specialist Premium nu există sau nu mai e activ")
    return {
        "id": str(u.pop("_id")),
        "name": u.get("name"),
        "specialty": u.get("specialty"),
        "service_categories": u.get("service_categories"),
        "coverage_zones": u.get("coverage_zones"),
        "rating": u.get("rating"),
        "reviews_count": u.get("reviews_count", 0),
        "tier": u.get("tier"),
        "verified": bool(u.get("verified")),
        "avatar_url": u.get("avatar_url"),
        "low_rating_warning": bool(u.get("tier_warning_low_rating")),
        "premium_profile": u.get("premium_profile") or {},
    }
