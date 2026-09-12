"""Trust Score + Coverage scope (response radius) router."""
import logging
from typing import Optional, List, Literal
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from core_utils import serialize_doc
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["trust"])


# ============= MODELS =============
class CoverageScopeIn(BaseModel):
    scope: Literal["local", "regional", "national"]
    zones: Optional[List[str]] = None  # zones covered (required for local/regional)
    response_time_minutes: Optional[int] = Field(default=60, ge=15, le=1440)  # max time to arrive (default 1h)


# ============= TRUST SCORE =============
def _trust_level(score: float) -> str:
    if score >= 90:
        return "exemplary"  # Exemplar
    if score >= 75:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "improving"
    return "new"


@router.get("/specialists/{spec_id}/trust-score")
async def get_trust_score(spec_id: str):
    """Public endpoint: compute a dynamic Trust Score (0-100) for a specialist.

    Components:
      - Task on-time delivery rate (40%)
      - Positive feedback (comments on tasks they're assigned, completed projects) (20%)
      - Progress photos uploaded (attachments) (15%)
      - Absence of warranty disputes against them (25%)
    """
    try:
        spec = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    except Exception:
        raise HTTPException(404, "Specialist inexistent.")
    if not spec:
        raise HTTPException(404, "Specialist inexistent.")

    # 1. Task on-time delivery: % of assigned tasks completed before due_date
    tasks = await db.project_tasks.find({"assignee_id": spec_id}).to_list(500)
    total_tasks = len(tasks)
    on_time = 0
    completed = 0
    for t in tasks:
        if t.get("status") == "done":
            completed += 1
            if t.get("due_date"):
                try:
                    due = datetime.fromisoformat(t["due_date"]) if "T" in (t.get("due_date") or "") else datetime.fromisoformat(t["due_date"] + "T23:59:59+00:00")
                    updated = datetime.fromisoformat(t.get("updated_at"))
                    if updated <= due:
                        on_time += 1
                except Exception:
                    on_time += 1  # benefit of doubt if dates can't be parsed
            else:
                on_time += 1  # no deadline = on time
    on_time_rate = (on_time / completed) if completed > 0 else 0.5  # neutral for new specialists
    on_time_pts = on_time_rate * 40

    # 2. Positive feedback: avg rating + count of comments containing positive keywords
    reviews_count = spec.get("reviews_count") or 0
    rating = spec.get("rating") or 0
    # Heuristic: rating ≥ 4.5 = full pts, 4.0 = 75%, 3.5 = 50%
    rating_pts = max(0, min(20, (rating - 3.0) * 10)) if reviews_count > 0 else 10  # neutral for new

    # 3. Progress photos uploaded
    pipeline = [
        {"$match": {"assignee_id": spec_id}},
        {"$project": {"att_count": {"$size": {"$ifNull": ["$attachments", []]}}}},
        {"$group": {"_id": None, "total": {"$sum": "$att_count"}}},
    ]
    agg = await db.project_tasks.aggregate(pipeline).to_list(1)
    total_attachments = agg[0]["total"] if agg else 0
    # Each attachment worth ~1 pt up to 15
    attachment_pts = min(15, total_attachments)
    if completed == 0:
        attachment_pts = 7.5  # neutral for new

    # 4. Absence of warranty disputes (member of a project with warranty_dispute_open)
    projects_with_specialist = await db.projects.find({"members.user_id": spec_id}).to_list(500)
    disputes_against = 0
    total_projects_completed = 0
    for p in projects_with_specialist:
        for m in (p.get("milestones") or []):
            if m.get("is_final") and m.get("warranty_dispute_open"):
                disputes_against += 1
            if m.get("status") == "warranty_released":
                total_projects_completed += 1
    if total_projects_completed == 0:
        warranty_pts = 12.5  # neutral
    else:
        bad_rate = disputes_against / max(1, total_projects_completed)
        warranty_pts = max(0, 25 * (1 - bad_rate))

    total_score = round(on_time_pts + rating_pts + attachment_pts + warranty_pts, 1)
    return {
        "specialist_id": spec_id,
        "name": spec.get("name"),
        "score": total_score,
        "level": _trust_level(total_score),
        "factors": {
            "on_time_delivery": {
                "rate": round(on_time_rate * 100, 1),
                "completed_tasks": completed,
                "total_tasks": total_tasks,
                "points": round(on_time_pts, 1),
                "max_points": 40,
            },
            "positive_feedback": {
                "rating": rating,
                "reviews_count": reviews_count,
                "points": round(rating_pts, 1),
                "max_points": 20,
            },
            "progress_photos": {
                "uploaded": total_attachments,
                "points": round(attachment_pts, 1),
                "max_points": 15,
            },
            "warranty_clean": {
                "disputes": disputes_against,
                "projects_completed": total_projects_completed,
                "points": round(warranty_pts, 1),
                "max_points": 25,
            },
        },
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ============= COVERAGE SCOPE =============
@router.post("/specialists/coverage-scope")
async def set_coverage_scope(data: CoverageScopeIn, user: dict = Depends(get_current_user)):
    """Specialist sets their work scope: local (1+ zones), regional (multi-city), national (anywhere)."""
    if user.get("role") != "specialist":
        raise HTTPException(403, "Doar specialiștii pot configura aria de acoperire.")
    # Designers (interior_design) can pick national; others cap at regional
    is_designer = "interior_design" in (user.get("service_categories") or [])
    if data.scope == "national" and not is_designer:
        raise HTTPException(400, "Doar designerii de interior pot opera la nivel național. Specialiștii sunt limitați la nivel local/regional pentru a putea ajunge rapid.")
    update = {
        "coverage_scope": data.scope,
        "response_time_minutes": data.response_time_minutes or 60,
    }
    if data.zones:
        update["coverage_zones"] = data.zones
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})
    refreshed = await db.users.find_one({"_id": ObjectId(user["id"])})
    return serialize_doc(refreshed)


@router.get("/regions/grouped")
async def get_regions_grouped():
    """Return regions grouped by city (useful for cascading dropdowns)."""
    regions = await db.regions.find({}).sort([("city", 1), ("zone", 1)]).to_list(2000)
    grouped = {}
    for r in regions:
        city = r["city"]
        grouped.setdefault(city, []).append({"zone": r["zone"], "id": str(r["_id"])})
    return [{"city": c, "zones": z} for c, z in grouped.items()]
