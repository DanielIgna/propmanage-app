"""PropManage router: matching."""
import logging
from typing import Optional
from fastapi import APIRouter, Depends

from db import db
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["matching"])

# ============= SMART MATCHING (Zone-based with fallback) =============

async def find_matching_specialists(category: str, user_zone: str, max_results: int = 5):
    """Smart match: primary (in-zone) + fallback (nearby zones with fee)"""
    # Primary: specialists in user's zone with the category
    primary = await db.users.find({
        "role": "specialist",
        "coverage_zones": user_zone,
        "service_categories": category,
        "availability_status": {"$ne": "offline"},
        "medic_suspended": {"$ne": True},
    }).sort([("rating", -1), ("reviews_count", -1)]).limit(max_results).to_list(max_results)
    
    # Fallback: other specialists (out of zone) sorted by rating, marked as fallback
    if len(primary) < max_results:
        fallback_q = {
            "role": "specialist",
            "service_categories": category,
            "availability_status": {"$ne": "offline"},
            "medic_suspended": {"$ne": True},
            "coverage_zones": {"$ne": user_zone},
        }
        already_ids = [s["_id"] for s in primary]
        if already_ids:
            fallback_q["_id"] = {"$nin": already_ids}
        fallback = await db.users.find(fallback_q).sort([("rating", -1)]).limit(max_results - len(primary)).to_list(max_results)
        for s in fallback:
            s["_fallback"] = True
        primary.extend(fallback)
    
    # Annotate matches with reason
    results = []
    for s in primary:
        match_reason = []
        if s.get("_fallback"):
            match_reason.append("Zonă apropiată · fee aplicabil")
        else:
            match_reason.append("Specialist în zona ta")
        if s.get("availability_status") == "available":
            match_reason.append("Disponibil acum")
        if (s.get("rating") or 0) >= 4.8:
            match_reason.append(f"Top rated ({s.get('rating')}★)")
        if s.get("verified"):
            match_reason.append("Verificat")
        
        results.append({
            "id": str(s["_id"]),
            "name": s.get("name"),
            "rating": s.get("rating"),
            "reviews_count": s.get("reviews_count", 0),
            "specialty": s.get("specialty"),
            "tier": s.get("tier"),
            "verified": s.get("verified", False),
            "availability_status": s.get("availability_status", "available"),
            "is_in_zone": not s.get("_fallback", False),
            "match_reasons": match_reason,
            "lead_fee": 0 if not s.get("_fallback") else 45,
        })
    return results


@router.get("/match")
async def smart_match(category: str, zone: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get smart-matched specialists for a category in user's (or given) zone"""
    user_zone = zone or user.get("zone") or "default"
    matches = await find_matching_specialists(category, user_zone)
    return {
        "zone": user_zone,
        "category": category,
        "matches": matches,
        "total": len(matches),
        "in_zone_count": sum(1 for m in matches if m["is_in_zone"]),
    }


