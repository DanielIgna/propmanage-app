"""GBOS P0 — 'Specialiștii mei de încredere' + Rebooking 1-click (cerere directă, taxă lead 0)."""
import logging
from datetime import datetime, timezone
from typing import Optional, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from db import db
from deps import require_role
from services import notify, log_event
from routes.trust_growth import rebook_rollup

logger = logging.getLogger("propmanage.trusted_specialists")
router = APIRouter(prefix="/api", tags=["trusted-specialists"])

DONE_STATUSES = ["completed", "confirmed"]


class RebookIn(BaseModel):
    property_id: str
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=3000)
    category: Optional[str] = None
    priority: Literal["low", "normal", "medium", "high", "urgent"] = "normal"
    budget_estimate: Optional[float] = Field(default=None, ge=0)

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, v):
        v = str(v or "normal").lower().strip()
        return "normal" if v in ("medium", "med", "") else v


@router.get("/trusted-specialists")
async def my_trusted_specialists(user: dict = Depends(require_role("client"))):
    """Specialiști cu care ownerul a finalizat cel puțin o lucrare, cu context de re-angajare."""
    groups = []
    async for g in db.requests.aggregate([
        {"$match": {"client_id": user["id"], "specialist_id": {"$nin": [None, ""]},
                    "status": {"$in": DONE_STATUSES}}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$specialist_id",
            "jobs_together": {"$sum": 1},
            "last_job_at": {"$first": "$created_at"},
            "last_job_title": {"$first": "$title"},
            "last_category": {"$first": "$category"},
            "last_property_id": {"$first": "$property_id"},
            "categories": {"$addToSet": "$category"},
            "specialist_name": {"$first": "$specialist_name"},
        }},
        {"$sort": {"jobs_together": -1, "last_job_at": -1}},
    ]):
        groups.append(g)
    if not groups:
        return {"specialists": []}

    ids = [g["_id"] for g in groups]
    obj_ids = [ObjectId(i) for i in ids if ObjectId.is_valid(i)]
    users_map = {}
    async for u in db.users.find({"_id": {"$in": obj_ids}}):
        users_map[str(u["_id"])] = u
    my_ratings = {}
    async for row in db.reviews.aggregate([
        {"$match": {"client_id": user["id"], "specialist_id": {"$in": ids},
                    "direction": {"$ne": "specialist_to_client"}}},
        {"$group": {"_id": "$specialist_id", "avg": {"$avg": "$rating"}, "n": {"$sum": 1}}},
    ]):
        my_ratings[row["_id"]] = row

    out = []
    for g in groups:
        sid = g["_id"]
        u = users_map.get(sid) or {}
        rating = my_ratings.get(sid)
        out.append({
            "specialist_id": sid,
            "name": u.get("name") or g.get("specialist_name") or "Specialist",
            "specialty": u.get("specialty") or u.get("category"),
            "city": u.get("city") or u.get("location"),
            "verified": bool(u.get("verified")),
            "active": bool(u),
            "jobs_together": g["jobs_together"],
            "last_job_at": g.get("last_job_at"),
            "last_job_title": g.get("last_job_title"),
            "last_category": g.get("last_category"),
            "last_property_id": g.get("last_property_id"),
            "categories": [c for c in (g.get("categories") or []) if c],
            "my_rating": round(rating["avg"], 1) if rating else None,
            "my_reviews": rating["n"] if rating else 0,
            "rebook": await rebook_rollup(sid),
        })
    return {"specialists": out}


@router.post("/trusted-specialists/{specialist_id}/rebook")
async def rebook_specialist(specialist_id: str, data: RebookIn, user: dict = Depends(require_role("client"))):
    """Rebooking 1-click: cerere DIRECTĂ către un specialist cu care ai mai lucrat (taxă lead 0)."""
    if not ObjectId.is_valid(specialist_id):
        raise HTTPException(404, "Specialist inexistent")
    spec = await db.users.find_one({"_id": ObjectId(specialist_id), "role": "specialist"})
    if not spec:
        raise HTTPException(404, "Specialist inexistent")
    worked = await db.requests.find_one({
        "client_id": user["id"], "specialist_id": specialist_id, "status": {"$in": DONE_STATUSES}})
    if not worked:
        raise HTTPException(403, "Poți re-angaja doar specialiști cu care ai finalizat o lucrare")
    if not ObjectId.is_valid(data.property_id):
        raise HTTPException(404, "Property not found")
    prop = await db.properties.find_one({"_id": ObjectId(data.property_id), "owner_id": user["id"]})
    if not prop:
        raise HTTPException(404, "Property not found")

    category = data.category or worked.get("category")
    doc = {
        "property_id": data.property_id,
        "category": category,
        "title": data.title,
        "description": data.description,
        "priority": data.priority,
        "budget_estimate": data.budget_estimate,
        "county": prop.get("county") or prop.get("zone") or prop.get("city"),
        "photos": None,
        "client_id": user["id"],
        "client_name": user["name"],
        "property_name": prop["name"],
        "property_address": prop.get("address"),
        "status": "open",
        "specialist_id": None,
        "specialist_name": None,
        "escrow_amount": None,
        "direct_specialist_id": specialist_id,
        "direct_specialist_name": spec.get("name"),
        "lead_fee_waived": True,
        "is_rebooking": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.requests.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    await log_event(doc["id"], "request.rebooked", actor=user, property_id=data.property_id,
                    payload={"specialist_id": specialist_id, "title": data.title, "category": category})
    await notify(
        specialist_id,
        f"⭐ {user['name']} te-a re-angajat",
        f"Cerere directă pentru tine: '{data.title}' ({category}). Taxa de lead este 0 RON — răspunde rapid!",
        type_="rebook",
        link="/specialist",
    )
    return doc
