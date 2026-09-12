"""PM-PILOT-001 / PM-ADMIN-001 — Administrator Workspace + Building Dashboard + Health Score + Anunțuri.

Refolosește: buildings, community_campaigns (PM-002), maintenance_tasks (CX-4), requests, notifications.
Colecție nouă aditivă: building_announcements.
"""
import logging
import os
from datetime import datetime, timezone, date, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from db import db
from deps import get_current_user
from services import notify
from routes.community_buildings import (
    _building_property_ids, _building_owner_ids, _serialize_campaign, _first_name, detect_opportunities,
)

logger = logging.getLogger("propmanage.building_admin")
router = APIRouter(prefix="/api", tags=["building-admin"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _front() -> str:
    return os.environ.get("FRONTEND_URL", "https://propmanage.ro").rstrip("/")


class BuildingPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=120)
    address: Optional[str] = Field(default=None, min_length=3, max_length=250)
    city: Optional[str] = Field(default=None, max_length=80)
    construction_year: Optional[int] = Field(default=None, ge=1800, le=2100)
    floors: Optional[int] = Field(default=None, ge=1, le=60)
    apartments_total: Optional[int] = Field(default=None, ge=1, le=2000)


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    body: str = Field(min_length=3, max_length=3000)


async def _get_building(building_id: str) -> dict:
    if not ObjectId.is_valid(building_id):
        raise HTTPException(404, "Blocul nu există")
    b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    if not b:
        raise HTTPException(404, "Blocul nu există")
    return b


async def _is_member(building_id: str, user: dict) -> bool:
    return bool(await db.properties.find_one({"building_id": building_id, "owner_id": user["id"]}))


def _is_admin_of(b: dict, user: dict) -> bool:
    return user.get("role") == "admin" or b.get("administrator_id") == user["id"] or b.get("created_by") == user["id"]


async def compute_building_health(building_id: str, b: dict = None) -> dict:
    """Scor 0-100 din dovezi reale: acoperire mentenanță, punctualitate, reactivitate, activare, comunitate."""
    b = b or await _get_building(building_id)
    prop_ids = await _building_property_ids(building_id)
    today = date.today().isoformat()
    tasks = [t async for t in db.maintenance_tasks.find({"property_id": {"$in": prop_ids}, "active": True})]
    props_with_plan = {t["property_id"] for t in tasks}
    overdue = [t for t in tasks if t["next_due"] < today]
    reqs = [r async for r in db.requests.find(
        {"property_id": {"$in": prop_ids}, "status": {"$in": ["open", "assigned", "in_progress"]}})]
    stale_cut = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    stale_reqs = [r for r in reqs if (r.get("created_at") or "") < stale_cut and r.get("status") == "open"]
    recent_cut = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    campaigns_recent = await db.community_campaigns.count_documents(
        {"building_id": building_id, "created_at": {"$gte": recent_cut}})
    ann_recent = await db.building_announcements.count_documents(
        {"building_id": building_id, "created_at": {"$gte": recent_cut}})

    n_props = len(prop_ids)
    coverage = (len(props_with_plan) / n_props) if n_props else 0.0
    punctuality = (1 - len(overdue) / len(tasks)) if tasks else 0.0
    responsiveness = (1 - len(stale_reqs) / len(reqs)) if reqs else 1.0
    declared = b.get("apartments_total") or 0
    activation = min(1.0, n_props / declared) if declared else (0.5 if n_props >= 2 else 0.25 if n_props == 1 else 0.0)
    community = min(1.0, (campaigns_recent + ann_recent) / 2)

    components = [
        {"key": "coverage", "label": "Acoperire mentenanță", "weight": 30, "value": round(coverage * 100),
         "detail": f"{len(props_with_plan)}/{n_props} apartamente au plan de mentenanță"},
        {"key": "punctuality", "label": "Punctualitate revizii", "weight": 25, "value": round(punctuality * 100),
         "detail": f"{len(overdue)} din {len(tasks)} revizii au termen depășit" if tasks else "Niciun plan de mentenanță încă"},
        {"key": "responsiveness", "label": "Reactivitate la probleme", "weight": 20, "value": round(responsiveness * 100),
         "detail": f"{len(stale_reqs)} cereri deschise de peste 14 zile" if reqs else "Nicio cerere blocată"},
        {"key": "activation", "label": "Activare digitală", "weight": 15, "value": round(activation * 100),
         "detail": f"{n_props}/{declared} apartamente conectate" if declared else f"{n_props} apartamente conectate (total nedeclarat)"},
        {"key": "community", "label": "Activitate comunitară", "weight": 10, "value": round(community * 100),
         "detail": f"{campaigns_recent} campanii, {ann_recent} anunțuri în ultimele 60 zile"},
    ]
    score = round(sum(c["weight"] * c["value"] / 100 for c in components))
    status = "green" if score >= 70 else "yellow" if score >= 45 else "red"
    return {"score": score, "status": status, "components": components}


# ============= ADMINISTRATOR WORKSPACE =============

@router.get("/admin-workspace/portfolio")
async def admin_portfolio(user: dict = Depends(get_current_user)):
    """Portofoliul administratorului: toate blocurile administrate, cu indicatori 🟢🟡🔴."""
    q = {"$or": [{"administrator_id": user["id"]}, {"created_by": user["id"]}]}
    buildings = []
    today = date.today().isoformat()
    async for b in db.buildings.find(q).sort("created_at", -1):
        bid = str(b["_id"])
        prop_ids = await _building_property_ids(bid)
        owners = await _building_owner_ids(bid)
        open_reqs = await db.requests.count_documents(
            {"property_id": {"$in": prop_ids}, "status": {"$in": ["open", "assigned", "in_progress"]}})
        overdue = await db.maintenance_tasks.count_documents(
            {"property_id": {"$in": prop_ids}, "active": True, "next_due": {"$lt": today}})
        campaigns = await db.community_campaigns.count_documents(
            {"building_id": bid, "status": {"$in": ["open", "scheduled"]}})
        health = await compute_building_health(bid, b)
        buildings.append({
            "id": bid, "name": b["name"], "address": b.get("address"), "city": b.get("city"),
            "apartments_total": b.get("apartments_total"),
            "properties_count": len(prop_ids), "members_count": len(owners),
            "open_requests": open_reqs, "overdue_tasks": overdue, "active_campaigns": campaigns,
            "health": health,
        })
    totals = {
        "buildings": len(buildings),
        "apartments": sum(x["properties_count"] for x in buildings),
        "residents": sum(x["members_count"] for x in buildings),
        "open_requests": sum(x["open_requests"] for x in buildings),
        "active_campaigns": sum(x["active_campaigns"] for x in buildings),
        "green": sum(1 for x in buildings if x["health"]["status"] == "green"),
        "yellow": sum(1 for x in buildings if x["health"]["status"] == "yellow"),
        "red": sum(1 for x in buildings if x["health"]["status"] == "red"),
    }
    return {"buildings": buildings, "totals": totals}


@router.patch("/buildings/{building_id}")
async def update_building(building_id: str, data: BuildingPatch, user: dict = Depends(get_current_user)):
    b = await _get_building(building_id)
    if not _is_admin_of(b, user):
        raise HTTPException(403, "Doar administratorul blocului poate modifica datele")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(400, "Nimic de actualizat")
    await db.buildings.update_one({"_id": b["_id"]}, {"$set": update})
    return {"ok": True, **update}


@router.get("/buildings/{building_id}/preview")
async def building_preview(building_id: str, user: dict = Depends(get_current_user)):
    """Preview minimal pentru invitați (nume + activare) — fără date sensibile."""
    b = await _get_building(building_id)
    bid = str(b["_id"])
    return {"id": bid, "name": b["name"], "address": b.get("address"), "city": b.get("city"),
            "members_count": len(await _building_owner_ids(bid))}


@router.get("/buildings/{building_id}/dashboard")
async def building_dashboard(building_id: str, user: dict = Depends(get_current_user)):
    b = await _get_building(building_id)
    bid = str(b["_id"])
    is_admin = _is_admin_of(b, user)
    if not is_admin and not await _is_member(bid, user):
        raise HTTPException(403, "Nu faci parte din acest bloc")

    today = date.today().isoformat()
    horizon = (date.today() + timedelta(days=90)).isoformat()
    props = [p async for p in db.properties.find({"building_id": bid})]
    prop_ids = [str(p["_id"]) for p in props]
    tasks = [t async for t in db.maintenance_tasks.find({"property_id": {"$in": prop_ids}, "active": True})]
    reqs = [r async for r in db.requests.find(
        {"property_id": {"$in": prop_ids}, "status": {"$in": ["open", "assigned", "in_progress"]}})]
    owner_ids = list({p["owner_id"] for p in props})
    owners = {}
    async for u in db.users.find({"_id": {"$in": [ObjectId(o) for o in owner_ids if ObjectId.is_valid(o)]}}):
        owners[str(u["_id"])] = u.get("name")

    apartments = []
    for p in props:
        pid = str(p["_id"])
        p_tasks = [t for t in tasks if t["property_id"] == pid]
        apartments.append({
            "property_id": pid, "name": p.get("name"),
            "owner_first_name": _first_name(owners.get(p["owner_id"], "")),
            "active_tasks": len(p_tasks),
            "overdue_tasks": sum(1 for t in p_tasks if t["next_due"] < today),
            "open_requests": sum(1 for r in reqs if r.get("property_id") == pid),
        })

    upcoming = {}
    for t in tasks:
        if today <= t["next_due"] <= horizon:
            u = upcoming.setdefault(t["title"], {"title": t["title"], "category": t.get("category"),
                                                 "count": 0, "earliest": t["next_due"]})
            u["count"] += 1
            u["earliest"] = min(u["earliest"], t["next_due"])
    campaigns = [_serialize_campaign(c, user["id"]) async for c in
                 db.community_campaigns.find({"building_id": bid}).sort("created_at", -1).limit(10)]
    announcements = [{"id": str(a["_id"]), "title": a["title"], "body": a["body"],
                      "author_name": a.get("author_name"), "created_at": a["created_at"]}
                     async for a in db.building_announcements.find({"building_id": bid})
                     .sort("created_at", -1).limit(10)]
    return {
        "id": bid, "name": b["name"], "address": b.get("address"), "city": b.get("city"),
        "construction_year": b.get("construction_year"), "floors": b.get("floors"),
        "apartments_total": b.get("apartments_total"),
        "is_admin": is_admin,
        "members_count": len(owner_ids), "properties_count": len(props),
        "health": await compute_building_health(bid, b),
        "apartments": sorted(apartments, key=lambda a: (-a["overdue_tasks"], -a["open_requests"])),
        "upcoming_maintenance": sorted(upcoming.values(), key=lambda u: u["earliest"])[:10],
        "opportunities": await detect_opportunities(bid),
        "campaigns": campaigns,
        "announcements": announcements,
        "invite_link": f"{_front()}/register?binvite={bid}",
        "open_requests": len(reqs),
    }


# ============= ANUNȚURI (Community Center) =============

@router.post("/buildings/{building_id}/announcements")
async def create_announcement(building_id: str, data: AnnouncementIn, user: dict = Depends(get_current_user)):
    b = await _get_building(building_id)
    bid = str(b["_id"])
    if not _is_admin_of(b, user):
        raise HTTPException(403, "Doar administratorul blocului poate publica anunțuri")
    doc = {"building_id": bid, "title": data.title, "body": data.body,
           "author_id": user["id"], "author_name": user["name"], "created_at": _now()}
    res = await db.building_announcements.insert_one(doc)
    for oid in await _building_owner_ids(bid):
        if oid == user["id"]:
            continue
        await notify(oid, f"📢 {b['name']}: {data.title}", data.body[:200],
                     type_="building_announcement", link="/client?tab=property")
    return {"id": str(res.inserted_id), "title": data.title, "body": data.body,
            "author_name": user["name"], "created_at": doc["created_at"]}


@router.get("/buildings/{building_id}/announcements")
async def list_announcements(building_id: str, user: dict = Depends(get_current_user)):
    b = await _get_building(building_id)
    bid = str(b["_id"])
    if not _is_admin_of(b, user) and not await _is_member(bid, user):
        raise HTTPException(403, "Nu faci parte din acest bloc")
    return {"announcements": [{"id": str(a["_id"]), "title": a["title"], "body": a["body"],
                               "author_name": a.get("author_name"), "created_at": a["created_at"]}
                              async for a in db.building_announcements.find({"building_id": bid})
                              .sort("created_at", -1).limit(30)]}
