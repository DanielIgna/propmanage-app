"""Sprint B — Multi-dimensional Reviews + Cross-Reviews + Double-blind reveal.

Backward compatible: legacy `POST /api/requests/{id}/review` (single rating) keeps working untouched.
New endpoints are versioned with /-v2 suffix.

Collections:
  - reviews (existing) — extended with new fields scores{}, dimension_avg, hidden_until
  - reviews_meta — tracks double-blind state per (request_id, direction)

Direction model:
  - direction="client_to_specialist" — classic review (client → specialist)
  - direction="specialist_to_client" — reverse review (specialist → client)

Double-blind:
  - Each review is HIDDEN from the OTHER party until either:
    a) The other party also submits their review (mutual reveal), OR
    b) 7 days pass from the FIRST review timestamp
  - During hidden window, only platform admins + the author can see their own review.

Dimensions:
  Client→Specialist (8):
    timeliness, quality, offer_adherence, communication,
    professionalism, cleanliness, documentation, recommendation
  Specialist→Client (5):
    seriousness, responsiveness, commitment, punctuality, collaboration

The user.rating field (legacy) = average of all client→specialist dimension averages.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user, require_role

logger = logging.getLogger("propmanage.reviews_v2")

router = APIRouter(prefix="/api", tags=["reviews-v2"])

# Dimension keys — DO NOT change once shipped (data format compat)
DIMS_C2S = ("timeliness", "quality", "offer_adherence", "communication", "professionalism", "cleanliness", "documentation", "recommendation")
DIMS_S2C = ("seriousness", "responsiveness", "commitment", "punctuality", "collaboration")

DOUBLE_BLIND_DAYS = 7


# ============================================================================
# Pydantic models
# ============================================================================
class ScoresC2S(BaseModel):
    timeliness: Optional[int] = Field(None, ge=1, le=5)
    quality: Optional[int] = Field(None, ge=1, le=5)
    offer_adherence: Optional[int] = Field(None, ge=1, le=5)
    communication: Optional[int] = Field(None, ge=1, le=5)
    professionalism: Optional[int] = Field(None, ge=1, le=5)
    cleanliness: Optional[int] = Field(None, ge=1, le=5)
    documentation: Optional[int] = Field(None, ge=1, le=5)
    recommendation: Optional[int] = Field(None, ge=1, le=5)


class ScoresS2C(BaseModel):
    seriousness: Optional[int] = Field(None, ge=1, le=5)
    responsiveness: Optional[int] = Field(None, ge=1, le=5)
    commitment: Optional[int] = Field(None, ge=1, le=5)
    punctuality: Optional[int] = Field(None, ge=1, le=5)
    collaboration: Optional[int] = Field(None, ge=1, le=5)


class ReviewC2SIn(BaseModel):
    scores: ScoresC2S
    comment: Optional[str] = None
    # GBOS P0.3 — Trust Marketplace
    would_hire_again: Optional[Literal["yes", "no", "not_sure"]] = None
    would_recommend: Optional[bool] = None


class ReviewS2CIn(BaseModel):
    scores: ScoresS2C
    comment: Optional[str] = None


# ============================================================================
# Helpers
# ============================================================================
def _avg(scores_dict: dict, dims: tuple) -> float:
    vals = [scores_dict.get(d) for d in dims if isinstance(scores_dict.get(d), (int, float))]
    return round(sum(vals) / len(vals), 2) if vals else 0.0


async def _try_mutual_reveal(req_id: str):
    """If both directions have a review, set hidden_until=now on both so they are revealed immediately."""
    c2s = await db.reviews.find_one({"request_id": req_id, "direction": "client_to_specialist", "version": 2})
    s2c = await db.reviews.find_one({"request_id": req_id, "direction": "specialist_to_client", "version": 2})
    if c2s and s2c:
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.reviews.update_many(
            {"request_id": req_id, "version": 2, "hidden_until": {"$exists": True}},
            {"$set": {"hidden_until": now_iso, "revealed_via": "mutual"}},
        )
        return True
    return False


# ============================================================================
# 1. CLIENT → SPECIALIST (multi-dim)
# ============================================================================
@router.post("/requests/{req_id}/review-v2")
async def submit_review_c2s(req_id: str, data: ReviewC2SIn, user: dict = Depends(require_role("client"))):
    req = await db.requests.find_one({"_id": ObjectId(req_id), "client_id": user["id"]})
    if not req:
        raise HTTPException(404, "Request not found")
    if not req.get("specialist_id"):
        raise HTTPException(400, "No specialist assigned")
    # Anti-self-review check: client + specialist must be DIFFERENT user ids
    if req["specialist_id"] == user["id"]:
        raise HTTPException(400, "Self-review nu este permis")
    # 1 review per (client, specialist, request)
    existing = await db.reviews.find_one({"request_id": req_id, "client_id": user["id"], "direction": "client_to_specialist", "version": 2})
    if existing:
        raise HTTPException(409, "Ai trimis deja review pentru această cerere")
    scores = data.scores.model_dump(exclude_none=True)
    if len(scores) < 3:
        raise HTTPException(400, "Trebuie să evaluezi cel puțin 3 dimensiuni")
    dim_avg = _avg(scores, DIMS_C2S)
    now = datetime.now(timezone.utc)
    hidden_until = (now + timedelta(days=DOUBLE_BLIND_DAYS)).isoformat()
    await db.reviews.insert_one({
        "request_id": req_id,
        "client_id": user["id"],
        "specialist_id": req["specialist_id"],
        "direction": "client_to_specialist",
        "version": 2,
        "scores": scores,
        "rating": dim_avg,    # also store as legacy avg
        "dimension_avg": dim_avg,
        "comment": (data.comment or "").strip()[:2000],
        "would_hire_again": data.would_hire_again,
        "would_recommend": data.would_recommend,
        "created_at": now.isoformat(),
        "hidden_until": hidden_until,    # double-blind window
        "revealed_via": None,
    })
    # Update legacy specialist.rating with running average across V2 reviews
    cur = db.reviews.find({"specialist_id": req["specialist_id"], "version": 2, "direction": "client_to_specialist"}, {"dimension_avg": 1})
    vals = [d.get("dimension_avg") async for d in cur if isinstance(d.get("dimension_avg"), (int, float))]
    new_rating = round(sum(vals) / len(vals), 2) if vals else dim_avg
    await db.users.update_one({"_id": ObjectId(req["specialist_id"])}, {"$set": {"rating": new_rating, "reviews_count": len(vals)}})
    # Award tokens to client
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$inc": {"tokens": 20}})
    # Attempt mutual reveal
    revealed = await _try_mutual_reveal(req_id)
    return {"ok": True, "dimension_avg": dim_avg, "double_blind_until": hidden_until, "mutual_reveal": revealed}


# ============================================================================
# 2. SPECIALIST → CLIENT (reverse)
# ============================================================================
@router.post("/requests/{req_id}/review-client-v2")
async def submit_review_s2c(req_id: str, data: ReviewS2CIn, user: dict = Depends(require_role("specialist"))):
    req = await db.requests.find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(404, "Request not found")
    if req.get("specialist_id") != user["id"] and req.get("accepted_by") != user["id"]:
        raise HTTPException(403, "Nu ai lucrat la această cerere")
    if not req.get("client_id"):
        raise HTTPException(400, "No client on this request")
    if req["client_id"] == user["id"]:
        raise HTTPException(400, "Self-review nu este permis")
    existing = await db.reviews.find_one({"request_id": req_id, "specialist_id": user["id"], "direction": "specialist_to_client", "version": 2})
    if existing:
        raise HTTPException(409, "Ai trimis deja review pentru acest client")
    scores = data.scores.model_dump(exclude_none=True)
    if len(scores) < 2:
        raise HTTPException(400, "Trebuie să evaluezi cel puțin 2 dimensiuni")
    dim_avg = _avg(scores, DIMS_S2C)
    now = datetime.now(timezone.utc)
    hidden_until = (now + timedelta(days=DOUBLE_BLIND_DAYS)).isoformat()
    await db.reviews.insert_one({
        "request_id": req_id,
        "client_id": req["client_id"],
        "specialist_id": user["id"],
        "direction": "specialist_to_client",
        "version": 2,
        "scores": scores,
        "rating": dim_avg,
        "dimension_avg": dim_avg,
        "comment": (data.comment or "").strip()[:2000],
        "created_at": now.isoformat(),
        "hidden_until": hidden_until,
        "revealed_via": None,
    })
    # Update client.client_rating (separate from specialist rating!)
    cur = db.reviews.find({"client_id": req["client_id"], "version": 2, "direction": "specialist_to_client"}, {"dimension_avg": 1})
    vals = [d.get("dimension_avg") async for d in cur if isinstance(d.get("dimension_avg"), (int, float))]
    client_rating = round(sum(vals) / len(vals), 2) if vals else dim_avg
    await db.users.update_one({"_id": ObjectId(req["client_id"])}, {"$set": {"client_rating": client_rating, "client_reviews_count": len(vals)}})
    revealed = await _try_mutual_reveal(req_id)
    return {"ok": True, "dimension_avg": dim_avg, "double_blind_until": hidden_until, "mutual_reveal": revealed}


# ============================================================================
# 3. READ — apply double-blind filter
# ============================================================================
def _is_visible(review: dict, viewer_user_id: Optional[str], is_admin: bool) -> bool:
    """Decide if a review is visible to the viewer based on double-blind rules."""
    if is_admin:
        return True
    if viewer_user_id and review.get(("specialist_id" if review["direction"] == "specialist_to_client" else "client_id")) == viewer_user_id:
        # The author can always see their own review
        return True
    # Check double-blind window
    hidden_until = review.get("hidden_until")
    if not hidden_until:
        return True
    try:
        return datetime.fromisoformat(hidden_until.replace("Z", "+00:00")) < datetime.now(timezone.utc)
    except ValueError:
        return True


@router.get("/reviews/specialist/{specialist_id}")
async def get_specialist_reviews(specialist_id: str, viewer: Optional[dict] = None, limit: int = Query(20, le=100), skip: int = 0):
    """Public — but applies double-blind filter."""
    try:
        viewer = await get_current_user(None) if not viewer else viewer
    except Exception:
        viewer = None
    is_admin = bool(viewer and viewer.get("role") == "admin")
    viewer_id = viewer.get("id") if viewer else None
    cur = db.reviews.find({"specialist_id": specialist_id, "direction": "client_to_specialist", "version": 2}).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    aggregate = {d: [] for d in DIMS_C2S}
    async for r in cur:
        rid = str(r.pop("_id"))
        r["id"] = rid
        visible = _is_visible(r, viewer_id, is_admin)
        if not visible:
            items.append({"id": rid, "hidden": True, "hidden_until": r.get("hidden_until"), "created_at": r.get("created_at")})
            continue
        items.append(r)
        for d in DIMS_C2S:
            v = (r.get("scores") or {}).get(d)
            if isinstance(v, (int, float)):
                aggregate[d].append(v)
    agg_summary = {d: round(sum(v) / len(v), 2) if v else 0.0 for d, v in aggregate.items()}
    overall = round(sum(v for v in agg_summary.values() if v > 0) / max(1, sum(1 for v in agg_summary.values() if v > 0)), 2)
    return {"items": items, "aggregate": agg_summary, "overall": overall, "total": len(items)}


@router.get("/reviews/client/{client_id}")
async def get_client_reviews(client_id: str, viewer: Optional[dict] = None, limit: int = Query(20, le=100), skip: int = 0):
    try:
        viewer = await get_current_user(None) if not viewer else viewer
    except Exception:
        viewer = None
    is_admin = bool(viewer and viewer.get("role") == "admin")
    viewer_id = viewer.get("id") if viewer else None
    cur = db.reviews.find({"client_id": client_id, "direction": "specialist_to_client", "version": 2}).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    aggregate = {d: [] for d in DIMS_S2C}
    async for r in cur:
        rid = str(r.pop("_id"))
        r["id"] = rid
        visible = _is_visible(r, viewer_id, is_admin)
        if not visible:
            items.append({"id": rid, "hidden": True, "hidden_until": r.get("hidden_until"), "created_at": r.get("created_at")})
            continue
        items.append(r)
        for d in DIMS_S2C:
            v = (r.get("scores") or {}).get(d)
            if isinstance(v, (int, float)):
                aggregate[d].append(v)
    agg_summary = {d: round(sum(v) / len(v), 2) if v else 0.0 for d, v in aggregate.items()}
    overall = round(sum(v for v in agg_summary.values() if v > 0) / max(1, sum(1 for v in agg_summary.values() if v > 0)), 2)
    return {"items": items, "aggregate": agg_summary, "overall": overall, "total": len(items)}


@router.get("/reviews/pending-for-me")
async def pending_reviews(user: dict = Depends(get_current_user)):
    """For dashboard widget: list completed requests where this user hasn't reviewed yet."""
    direction = "client_to_specialist" if user.get("role") == "client" else "specialist_to_client"
    filter_key = "client_id" if direction == "client_to_specialist" else "specialist_id"
    # find user's completed requests
    reqs_cur = db.requests.find({filter_key: user["id"], "status": {"$in": ["completed", "closed"]}}, {"_id": 1, "title": 1, "created_at": 1})
    out = []
    async for r in reqs_cur:
        rid = str(r["_id"])
        already = await db.reviews.find_one({"request_id": rid, filter_key: user["id"], "direction": direction, "version": 2})
        if not already:
            out.append({"request_id": rid, "title": r.get("title", ""), "completed_at": r.get("created_at")})
    return {"items": out[:50], "direction": direction}


# ============================================================================
# 4. ADMIN reveal queue (mod manual de revelare timpurie pe motiv legal)
# ============================================================================
@router.post("/admin/reviews/{review_id}/force-reveal")
async def admin_force_reveal(review_id: str, user: dict = Depends(require_role("admin"))):
    await db.reviews.update_one({"_id": ObjectId(review_id)}, {"$set": {"hidden_until": datetime.now(timezone.utc).isoformat(), "revealed_via": f"admin:{user['id']}"}})
    return {"ok": True}
