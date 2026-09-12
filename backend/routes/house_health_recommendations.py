"""House Health — F4.2: Recommendations CRUD (post-evaluation).

After a specialist evaluation is approved, the specialist (or admin) can attach
one or more recommendations with priority (urgent|recommended|monitor), cost
estimate, deadline, and category. These appear in the client UI under the
"Recomandări" tab and can later be auto-published to the marketplace (F4.4).

Endpoints:
    POST   /api/house-health/recommendations
    GET    /api/house-health/recommendations?twin_project_id=...
    PATCH  /api/house-health/recommendations/{id}
    DELETE /api/house-health/recommendations/{id}

Collection: ``hh_recommendations`` ``{id, evaluation_id, twin_project_id,
specialist_id, priority, category, title, description, estimated_cost_eur,
deadline, status (active|done|dismissed), created_at, updated_at}``.

Authorisation:
  - Create / Patch / Delete → specialist owner of the linked evaluation, OR admin.
  - List → owner of the twin (client), specialist owner, or admin.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

from db import db
from deps import get_current_user

logger = logging.getLogger("propmanage.house_health.recommendations")

router = APIRouter(prefix="/api/house-health", tags=["house-health"])

ALLOWED_PRIORITIES = ["urgent", "recommended", "monitor"]
ALLOWED_STATUSES = ["active", "done", "dismissed"]
ALLOWED_CATEGORIES = ["air", "thermal", "humidity", "electric", "radon", "structural", "docs", "other"]


class RecommendationIn(BaseModel):
    evaluation_id: str
    title: str = Field(..., max_length=200)
    description: str = Field("", max_length=2000)
    priority: str = "recommended"
    category: str = "other"
    estimated_cost_eur: Optional[float] = None
    deadline: Optional[str] = None  # ISO date, optional

    @validator("priority")
    def _p(cls, v):
        if v not in ALLOWED_PRIORITIES:
            raise ValueError(f"priority must be one of {ALLOWED_PRIORITIES}")
        return v

    @validator("category")
    def _c(cls, v):
        if v not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {ALLOWED_CATEGORIES}")
        return v


class RecommendationPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    estimated_cost_eur: Optional[float] = None
    deadline: Optional[str] = None
    status: Optional[str] = None

    @validator("priority")
    def _p(cls, v):
        if v is not None and v not in ALLOWED_PRIORITIES:
            raise ValueError(f"priority must be one of {ALLOWED_PRIORITIES}")
        return v

    @validator("status")
    def _s(cls, v):
        if v is not None and v not in ALLOWED_STATUSES:
            raise ValueError(f"status must be one of {ALLOWED_STATUSES}")
        return v


async def _can_mutate(rec_or_eval: dict, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    return rec_or_eval.get("specialist_id") == user["id"]


@router.post("/recommendations")
async def create_recommendation(payload: RecommendationIn, user=Depends(get_current_user)):
    if user.get("role") not in ("specialist", "admin"):
        raise HTTPException(403, "Doar specialiști/admini pot crea recomandări.")
    e = await db.hh_evaluations.find_one({"id": payload.evaluation_id})
    if not e:
        raise HTTPException(404, "Evaluarea atașată nu există.")
    if user.get("role") != "admin" and e.get("specialist_id") != user["id"]:
        raise HTTPException(403, "Doar specialistul care a făcut evaluarea poate adăuga recomandări.")
    rec_id = uuid.uuid4().hex
    doc = {
        "id": rec_id,
        "evaluation_id": payload.evaluation_id,
        "twin_project_id": e.get("twin_project_id"),
        "specialist_id": e.get("specialist_id"),
        "title": payload.title.strip(),
        "description": payload.description.strip(),
        "priority": payload.priority,
        "category": payload.category,
        "estimated_cost_eur": payload.estimated_cost_eur,
        "deadline": payload.deadline,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by_email": user.get("email"),
    }
    await db.hh_recommendations.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "recommendation": doc}


@router.get("/recommendations")
async def list_recommendations(
    twin_project_id: Optional[str] = None,
    evaluation_id: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_current_user),
):
    q = {}
    if twin_project_id:
        q["twin_project_id"] = twin_project_id
    if evaluation_id:
        q["evaluation_id"] = evaluation_id
    if priority:
        q["priority"] = priority
    if status:
        q["status"] = status

    # Scoping
    role = user.get("role")
    if role == "client":
        if not twin_project_id:
            raise HTTPException(400, "twin_project_id obligatoriu pentru client.")
        # verify ownership
        p = await db.digital_twin_projects.find_one(
            {"id": twin_project_id, "owner_id": user["id"]}, {"_id": 0, "id": 1}
        )
        if not p:
            raise HTTPException(403, "Nu ai acces la acest Digital Twin.")
    elif role == "specialist":
        q["specialist_id"] = user["id"]
    # admin: no extra filter

    items = []
    async for r in db.hh_recommendations.find(q, {"_id": 0}).sort("created_at", -1).limit(200):
        items.append(r)
    return {"items": items, "count": len(items)}


@router.patch("/recommendations/{rec_id}")
async def patch_recommendation(rec_id: str, payload: RecommendationPatch, user=Depends(get_current_user)):
    r = await db.hh_recommendations.find_one({"id": rec_id})
    if not r:
        raise HTTPException(404, "Recomandare inexistentă.")
    if not await _can_mutate(r, user):
        raise HTTPException(403, "Nu poți modifica această recomandare.")
    update = {k: v for k, v in payload.dict().items() if v is not None}
    if not update:
        return {"ok": True, "noop": True}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    update["updated_by_email"] = user.get("email")
    await db.hh_recommendations.update_one({"id": rec_id}, {"$set": update})
    fresh = await db.hh_recommendations.find_one({"id": rec_id}, {"_id": 0})
    return {"ok": True, "recommendation": fresh}


@router.delete("/recommendations/{rec_id}")
async def delete_recommendation(rec_id: str, user=Depends(get_current_user)):
    r = await db.hh_recommendations.find_one({"id": rec_id})
    if not r:
        raise HTTPException(404, "Recomandare inexistentă.")
    if not await _can_mutate(r, user):
        raise HTTPException(403, "Nu poți șterge această recomandare.")
    await db.hh_recommendations.delete_one({"id": rec_id})
    return {"ok": True, "deleted_id": rec_id}


# ============================================================================
# F4.4 — Marketplace Lead Automation
# ============================================================================
class PublishToMarketplaceIn(BaseModel):
    property_id: Optional[str] = None  # if not set, use first owned property
    extra_notes: Optional[str] = ""
    budget_estimate: Optional[float] = None


@router.post("/recommendations/{rec_id}/publish-to-marketplace")
async def publish_to_marketplace(
    rec_id: str,
    payload: PublishToMarketplaceIn,
    user=Depends(get_current_user),
):
    """Client publishes a high-priority recommendation as a marketplace request.

    Eligibility:
      - Recommendation priority must be 'urgent' or 'recommended' (monitor cannot publish).
      - Caller must own the linked Digital Twin (verified through twin_project_id).
      - Recommendation must not already have a linked marketplace_request_id.

    Commission tracking:
      - Active hh_subscriptions plan's ``lead_commission_pct`` is captured at
        publish time and stored on the request as ``house_health_source.commission_pct``
        for later reconciliation (paid at offer-accepted).
    """
    from bson import ObjectId

    r = await db.hh_recommendations.find_one({"id": rec_id})
    if not r:
        raise HTTPException(404, "Recomandare inexistentă.")
    if r.get("priority") not in ("urgent", "recommended"):
        raise HTTPException(400, "Doar recomandările urgent/recomandat pot fi publicate în marketplace.")
    if r.get("marketplace_request_id"):
        raise HTTPException(409, "Deja publicată în marketplace.")

    # Ownership check via twin
    twin_id = r.get("twin_project_id")
    twin = await db.digital_twin_projects.find_one(
        {"id": twin_id, "owner_id": user["id"]}, {"_id": 0}
    )
    if not twin:
        raise HTTPException(403, "Nu ești owner-ul acestui Digital Twin.")

    # Determine property
    prop = None
    if payload.property_id:
        try:
            prop = await db.properties.find_one(
                {"_id": ObjectId(payload.property_id), "owner_id": user["id"]}
            )
        except Exception:  # noqa: BLE001
            raise HTTPException(400, "property_id invalid.")
    if not prop:
        # fallback: first property of the owner
        prop = await db.properties.find_one({"owner_id": user["id"]})
    if not prop:
        raise HTTPException(400, "Trebuie să ai cel puțin o proprietate înregistrată.")

    # Capture commission from active subscription plan
    sub = await db.hh_subscriptions.find_one({"user_id": user["id"], "status": {"$in": ["active", "trial"]}})
    plan_slug = (sub or {}).get("plan")
    commission_pct = 10.0  # default
    plan_id = None
    if plan_slug:
        plan = await db.hh_plans.find_one({"slug": plan_slug, "active": True})
        if plan:
            commission_pct = float(plan.get("lead_commission_pct", 10.0))
            plan_id = plan.get("id")

    # Map HH category to marketplace category (passthrough)
    category_map = {
        "air": "ventilatie", "thermal": "termice", "humidity": "izolatii",
        "electric": "electric", "radon": "ventilatie", "structural": "structural",
        "docs": "consultanta", "other": "general",
    }
    mp_category = category_map.get(r.get("category"), "general")

    description_parts = [r.get("description", "").strip()]
    if payload.extra_notes:
        description_parts.append(f"\n\nNote client:\n{payload.extra_notes.strip()}")
    description_parts.append(
        f"\n\n— Generat automat din House Health (recomandare {r.get('priority')})."
    )
    description = "\n".join([p for p in description_parts if p]).strip() or r.get("title", "Recomandare House Health")

    # Build request doc (mirrors /api/requests POST minimum required fields)
    request_doc = {
        "property_id": str(prop["_id"]),
        "category": mp_category,
        "title": r.get("title", "Lucrare recomandată House Health"),
        "description": description,
        "priority": "urgent" if r.get("priority") == "urgent" else "high",
        "budget_estimate": payload.budget_estimate or r.get("estimated_cost_eur"),
        "photos": [],
        "client_id": user["id"],
        "client_name": user.get("name"),
        "property_name": prop.get("name"),
        "property_address": prop.get("address"),
        "status": "open",
        "specialist_id": None,
        "specialist_name": None,
        "escrow_amount": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        # House Health attribution metadata
        "house_health_source": {
            "recommendation_id": rec_id,
            "evaluation_id": r.get("evaluation_id"),
            "twin_project_id": twin_id,
            "plan_id": plan_id,
            "plan_slug": plan_slug,
            "commission_pct": commission_pct,
            "commission_status": "pending",  # pending → captured (on offer accept) → paid
            "published_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    res = await db.requests.insert_one(request_doc)
    request_id = str(res.inserted_id)

    # Link back to the recommendation
    await db.hh_recommendations.update_one(
        {"id": rec_id},
        {"$set": {
            "marketplace_request_id": request_id,
            "marketplace_published_at": datetime.now(timezone.utc).isoformat(),
            "marketplace_commission_pct": commission_pct,
        }},
    )

    await db.hh_audit_log.insert_one({
        "user_id": user["id"],
        "action": "recommendation_published_to_marketplace",
        "resource_id": rec_id,
        "request_id": request_id,
        "commission_pct": commission_pct,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    logger.info(
        "[house_health] rec=%s published to marketplace request=%s commission=%.1f%%",
        rec_id, request_id, commission_pct,
    )

    return {
        "ok": True,
        "request_id": request_id,
        "commission_pct": commission_pct,
        "plan_slug": plan_slug,
    }


@router.get("/marketplace-stats")
async def marketplace_stats(user=Depends(get_current_user)):
    """Aggregate stats per user/role on House Health → marketplace conversions.

    For clients: their own published recommendations + status of requests.
    For admin: platform-wide aggregated metrics for revenue dashboards.
    """
    if user.get("role") == "admin":
        # Platform-wide
        total_published = await db.requests.count_documents({"house_health_source": {"$exists": True}})
        pipeline = [
            {"$match": {"house_health_source": {"$exists": True}}},
            {"$group": {
                "_id": "$house_health_source.commission_status",
                "count": {"$sum": 1},
                "avg_commission": {"$avg": "$house_health_source.commission_pct"},
            }},
        ]
        by_status = []
        async for doc in db.requests.aggregate(pipeline):
            by_status.append({
                "status": doc["_id"],
                "count": doc["count"],
                "avg_commission_pct": round(doc.get("avg_commission") or 0, 2),
            })
        return {"role": "admin", "total_published": total_published, "by_status": by_status}

    # Client view
    items = []
    async for req in db.requests.find(
        {"house_health_source": {"$exists": True}, "client_id": user["id"]},
        {"_id": 1, "title": 1, "status": 1, "house_health_source": 1, "created_at": 1},
    ).sort("created_at", -1).limit(50):
        items.append({
            "request_id": str(req["_id"]),
            "title": req.get("title"),
            "status": req.get("status"),
            "created_at": req.get("created_at"),
            "commission_pct": req.get("house_health_source", {}).get("commission_pct"),
            "recommendation_id": req.get("house_health_source", {}).get("recommendation_id"),
        })
    return {"role": "client", "items": items, "count": len(items)}
