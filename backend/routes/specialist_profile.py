"""PropManage router: specialist_profile."""
import logging
from bson import ObjectId
from fastapi import APIRouter, HTTPException

from db import db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["specialist_profile"])

# ============= SPECIALIST PUBLIC PROFILE =============

@router.get("/specialists/{spec_id}/profile")
async def specialist_profile(spec_id: str):
    """Public profile for a specialist - no auth required"""
    try:
        spec = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    except Exception:
        raise HTTPException(404, "Specialist not found")
    if not spec:
        raise HTTPException(404, "Specialist not found")
    
    # Get reviews
    reviews = await db.reviews.find({"specialist_id": spec_id}).sort("created_at", -1).limit(20).to_list(20)
    
    # Get completed jobs count
    completed = await db.requests.count_documents({"specialist_id": spec_id, "status": "confirmed"})
    total_jobs = await db.requests.count_documents({"specialist_id": spec_id})
    disputed = await db.requests.count_documents({"specialist_id": spec_id, "disputed": True})

    # Compute Health Score (same formula as /marketplace/specialists)
    rating = float(spec.get("rating") or 0)
    reviews_count = int(spec.get("reviews_count") or 0)
    verified = bool(spec.get("verified"))
    score = rating * 6
    if reviews_count >= 10: score += 15
    elif reviews_count >= 5: score += 10
    elif reviews_count >= 1: score += 5
    if verified: score += 15
    if total_jobs >= 3:
        score += (completed / total_jobs) * 25
    else:
        score += 12
    if total_jobs >= 3:
        dispute_rate = disputed / total_jobs
        if dispute_rate == 0: score += 15
        elif dispute_rate < 0.05: score += 10
        elif dispute_rate < 0.10: score += 5
    else:
        score += 8
    score = max(0, min(100, round(score)))
    if score >= 80: tier_h, color, label = "excellent", "emerald", "Excelent"
    elif score >= 50: tier_h, color, label = "good", "amber", "Bun"
    else: tier_h, color, label = "developing", "rose", "În progres"
    health = {
        "score": score, "tier": tier_h, "color": color, "label": label,
        "components": {
            "rating": rating, "reviews": reviews_count, "verified": verified,
            "completed_jobs": completed, "total_jobs": total_jobs, "disputes": disputed,
        },
    }
    
    # Get specialties from past requests
    specialties_cursor = db.requests.aggregate([
        {"$match": {"specialist_id": spec_id, "status": "confirmed"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ])
    specialties = await specialties_cursor.to_list(10)
    
    return {
        "id": str(spec["_id"]),
        "name": spec.get("name"),
        # NOTE: email is PII — intentionally NOT exposed on public profile.
        # Avatar is exposed only as a sanitized URL/base64 thumbnail.
        "picture": spec.get("picture"),
        "specialty": spec.get("specialty"),
        "service_categories": spec.get("service_categories") or [],
        "coverage_zones": spec.get("coverage_zones") or [],
        "rating": spec.get("rating"),
        "reviews_count": spec.get("reviews_count", 0),
        "tier": spec.get("tier"),
        "verified": spec.get("verified", False),
        "completed_jobs": completed,
        "member_since": spec.get("created_at"),
        "health": health,
        "specialties": [{"category": s["_id"], "count": s["count"]} for s in specialties if s["_id"]],
        "reviews": [
            {
                "rating": r.get("rating"),
                "comment": r.get("comment"),
                "created_at": r.get("created_at"),
            } for r in reviews
        ],
    }


