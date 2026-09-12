"""PM-002 — Community Maintenance Engine: Buildings (Home Graph node) + Campanii comune.

Colecții noi aditive: buildings, community_campaigns. Properties primesc building_id (aditiv).
Bucla: proprietăți în același bloc → scadențe comune detectate → campanie → oferte grupate →
lucrări directe (taxă lead 0) pentru fiecare apartament → twin actualizat per apartament.
"""
import logging
import re
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user, require_role
from services import notify, log_event

logger = logging.getLogger("propmanage.community_buildings")
router = APIRouter(prefix="/api", tags=["community-buildings"])

DONE_STATUSES = ["completed", "confirmed"]
CAT_LABELS = {
    "zugravit": "Zugrăvit", "parchet": "Parchet", "faianta": "Faianță / Gresie", "handyman": "Handyman",
    "gips_carton": "Gips-carton", "hvac": "HVAC / Climatizare", "electric": "Electric", "plumbing": "Sanitar",
    "interior_design": "Design Interior",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first_name(name: str) -> str:
    return (name or "Proprietar").split(" ")[0]


class BuildingIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    address: str = Field(min_length=3, max_length=250)
    city: Optional[str] = Field(default=None, max_length=80)
    property_id: Optional[str] = None


class CampaignIn(BaseModel):
    building_id: str
    category: str
    property_id: str
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    window_end: Optional[str] = None  # YYYY-MM-DD


class OfferIn(BaseModel):
    price_per_unit: float = Field(gt=0)
    message: Optional[str] = Field(default=None, max_length=1000)


async def _building_property_ids(building_id: str) -> list:
    return [str(p["_id"]) async for p in db.properties.find({"building_id": building_id}, {"_id": 1})]


async def _building_owner_ids(building_id: str) -> list:
    return await db.properties.distinct("owner_id", {"building_id": building_id})


def _serialize_campaign(c: dict, user_id: str = None) -> dict:
    participants = c.get("participants") or []
    return {
        "id": str(c["_id"]),
        "building_id": c["building_id"],
        "building_name": c.get("building_name"),
        "category": c["category"],
        "category_label": CAT_LABELS.get(c["category"], c["category"]),
        "title": c["title"],
        "description": c.get("description"),
        "status": c["status"],
        "source": c.get("source", "manual"),
        "created_by": c.get("created_by"),
        "created_by_name": c.get("created_by_name"),
        "window_end": c.get("window_end"),
        "participants_count": len(participants),
        "participants": [{"property_id": p["property_id"], "owner_first_name": _first_name(p.get("owner_name"))}
                         for p in participants],
        "joined_by_me": any(p.get("owner_id") == user_id for p in participants) if user_id else False,
        "offers": c.get("offers") or [],
        "accepted_offer": c.get("accepted_offer"),
        "created_at": c.get("created_at"),
    }


async def detect_opportunities(building_id: str) -> list:
    """Scadențe comune: ≥2 proprietăți din bloc cu aceeași categorie de mentenanță în ≤60 zile."""
    prop_ids = await _building_property_ids(building_id)
    if len(prop_ids) < 2:
        return []
    horizon = (date.today() + timedelta(days=60)).isoformat()
    active_cats = await db.community_campaigns.distinct(
        "category", {"building_id": building_id, "status": {"$in": ["open", "scheduled"]}})
    groups = {}
    async for t in db.maintenance_tasks.find({
            "property_id": {"$in": prop_ids}, "active": True, "next_due": {"$lte": horizon},
            "category": {"$nin": [None, ""] + list(active_cats)}}):
        g = groups.setdefault(t["category"], {"properties": set(), "earliest": t["next_due"]})
        g["properties"].add(t["property_id"])
        g["earliest"] = min(g["earliest"], t["next_due"])
    return [{"category": cat, "category_label": CAT_LABELS.get(cat, cat),
             "properties": len(g["properties"]), "earliest_due": g["earliest"]}
            for cat, g in groups.items() if len(g["properties"]) >= 2]


# ============= BUILDINGS =============

@router.post("/buildings")
async def create_building(data: BuildingIn, user: dict = Depends(require_role("client"))):
    dup = await db.buildings.find_one({"name": {"$regex": f"^{re.escape(data.name)}$", "$options": "i"},
                                       "address": {"$regex": f"^{re.escape(data.address)}$", "$options": "i"}})
    if dup:
        raise HTTPException(409, "Blocul există deja — folosește căutarea și alătură-te")
    doc = {"name": data.name, "address": data.address, "city": data.city,
           "administrator_id": user["id"],
           "created_by": user["id"], "created_by_name": user["name"], "created_at": _now()}
    res = await db.buildings.insert_one(doc)
    bid = str(res.inserted_id)
    if data.property_id and ObjectId.is_valid(data.property_id):
        await db.properties.update_one(
            {"_id": ObjectId(data.property_id), "owner_id": user["id"]}, {"$set": {"building_id": bid}})
    return {"id": bid, "name": data.name, "address": data.address, "city": data.city}


@router.get("/buildings/search")
async def search_buildings(q: str = "", user: dict = Depends(get_current_user)):
    if len(q.strip()) < 2:
        return {"buildings": []}
    regex = {"$regex": re.escape(q.strip()), "$options": "i"}
    out = []
    async for b in db.buildings.find({"$or": [{"name": regex}, {"address": regex}]}).limit(10):
        bid = str(b["_id"])
        out.append({"id": bid, "name": b["name"], "address": b.get("address"), "city": b.get("city"),
                    "members_count": len(await _building_owner_ids(bid))})
    return {"buildings": out}


@router.post("/buildings/{building_id}/join")
async def join_building(building_id: str, body: dict, user: dict = Depends(require_role("client"))):
    if not ObjectId.is_valid(building_id) or not await db.buildings.find_one({"_id": ObjectId(building_id)}):
        raise HTTPException(404, "Blocul nu există")
    property_id = body.get("property_id")
    if not property_id or not ObjectId.is_valid(property_id):
        raise HTTPException(400, "property_id este obligatoriu")
    r = await db.properties.update_one(
        {"_id": ObjectId(property_id), "owner_id": user["id"]}, {"$set": {"building_id": building_id}})
    if r.matched_count == 0:
        raise HTTPException(404, "Property not found")
    try:
        from orchestrator.engine import emit_signal
        await emit_signal("resident_joined", {"building_id": building_id, "owner_id": user["id"]})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[buildings] resident_joined signal failed: {e}")
    return {"ok": True}


@router.get("/buildings/mine")
async def my_buildings(user: dict = Depends(require_role("client"))):
    my_props = [p async for p in db.properties.find({"owner_id": user["id"]})]
    building_ids = sorted({p.get("building_id") for p in my_props if p.get("building_id")})
    out = []
    for bid in building_ids:
        b = await db.buildings.find_one({"_id": ObjectId(bid)}) if ObjectId.is_valid(bid) else None
        if not b:
            continue
        owners = await _building_owner_ids(bid)
        campaigns = [_serialize_campaign(c, user["id"]) async for c in
                     db.community_campaigns.find({"building_id": bid, "status": {"$in": ["open", "scheduled"]}})
                     .sort("created_at", -1).limit(10)]
        announcements = [{"id": str(a["_id"]), "title": a["title"], "body": a["body"],
                          "author_name": a.get("author_name"), "created_at": a["created_at"]}
                         async for a in db.building_announcements.find({"building_id": bid})
                         .sort("created_at", -1).limit(3)]
        out.append({
            "id": bid, "name": b["name"], "address": b.get("address"), "city": b.get("city"),
            "members_count": len(owners),
            "properties_count": len(await _building_property_ids(bid)),
            "my_property_ids": [str(p["_id"]) for p in my_props if p.get("building_id") == bid],
            "is_admin": b.get("administrator_id") == user["id"] or b.get("created_by") == user["id"],
            "opportunities": await detect_opportunities(bid),
            "campaigns": campaigns,
            "announcements": announcements,
        })
    return {"buildings": out, "me": user["id"],
            "my_properties": [{"id": str(p["_id"]), "name": p.get("name"),
                               "building_id": p.get("building_id")} for p in my_props]}


# ============= CAMPAIGNS =============

async def _notify_campaign_audience(campaign: dict, cid: str):
    """Notifică ownerii din bloc + specialiștii de încredere ai comunității (sau verificați pe categorie)."""
    owners = await _building_owner_ids(campaign["building_id"])
    joined = {p["owner_id"] for p in campaign.get("participants") or []}
    for oid in owners:
        if oid in joined or oid == campaign.get("created_by"):
            continue
        await notify(oid, f"🏢 Campanie comună în blocul tău: {campaign['title']}",
                     f"{len(joined)} vecini participă deja. Prin volum obțineți un preț mai bun — alătură-te cu 1 click.",
                     type_="campaign", link="/client?tab=property")
    trusted = await db.requests.distinct("specialist_id", {
        "client_id": {"$in": owners}, "status": {"$in": DONE_STATUSES},
        "category": campaign["category"], "specialist_id": {"$nin": [None, ""]}})
    if not trusted:
        trusted = [str(s["_id"]) for s in await db.users.find(
            {"role": "specialist", "specialty": campaign["category"], "verified": True}).limit(20).to_list(20)]
    for sid in trusted:
        await notify(sid, f"🏢 Campanie de grup: {campaign['title']}",
                     f"{max(len(joined), 1)}+ apartamente din același bloc cer {CAT_LABELS.get(campaign['category'], campaign['category'])}. Trimite o ofertă de grup (preț/apartament) — taxă lead 0.",
                     type_="campaign", link="/specialist")


@router.post("/campaigns")
async def create_campaign(data: CampaignIn, user: dict = Depends(require_role("client"))):
    if not ObjectId.is_valid(data.building_id):
        raise HTTPException(404, "Blocul nu există")
    b = await db.buildings.find_one({"_id": ObjectId(data.building_id)})
    if not b:
        raise HTTPException(404, "Blocul nu există")
    prop = await db.properties.find_one({"_id": ObjectId(data.property_id), "owner_id": user["id"],
                                         "building_id": data.building_id})
    if not prop:
        raise HTTPException(403, "Poți porni campanii doar cu o proprietate din acest bloc")
    dup = await db.community_campaigns.find_one({
        "building_id": data.building_id, "category": data.category, "status": {"$in": ["open", "scheduled"]}})
    if dup:
        raise HTTPException(409, "Există deja o campanie activă pe această categorie în bloc")
    title = data.title or f"{CAT_LABELS.get(data.category, data.category)} — tot blocul"
    doc = {
        "building_id": data.building_id, "building_name": b["name"],
        "category": data.category, "title": title, "description": data.description,
        "status": "open", "source": "manual", "window_end": data.window_end,
        "created_by": user["id"], "created_by_name": user["name"],
        "participants": [{"property_id": data.property_id, "owner_id": user["id"],
                          "owner_name": user["name"], "joined_at": _now()}],
        "offers": [], "accepted_offer": None, "created_at": _now(),
    }
    res = await db.community_campaigns.insert_one(doc)
    cid = str(res.inserted_id)
    await _notify_campaign_audience(doc, cid)
    return _serialize_campaign({**doc, "_id": res.inserted_id}, user["id"])


@router.get("/campaigns/mine")
async def my_campaigns(user: dict = Depends(get_current_user)):
    if user.get("role") == "specialist" and user.get("active_view") != "client":
        q = {"status": "open", "$or": [
            {"category": user.get("specialty")},
            {"offers.specialist_id": user["id"]},
        ]}
        if not user.get("specialty"):
            # fără specialitate: doar campaniile unde a ofertat deja (nu expunem tot)
            q = {"offers.specialist_id": user["id"]}
        out = [_serialize_campaign(c, user["id"]) async for c in
               db.community_campaigns.find(q).sort("created_at", -1).limit(20)]
        for c in out:
            c["my_offer"] = next((o for o in c["offers"] if o["specialist_id"] == user["id"]), None)
        return {"campaigns": out, "role": "specialist"}
    my_props = [p async for p in db.properties.find({"owner_id": user["id"]}, {"building_id": 1})]
    bids = sorted({p.get("building_id") for p in my_props if p.get("building_id")})
    out = [_serialize_campaign(c, user["id"]) async for c in
           db.community_campaigns.find({"building_id": {"$in": bids}}).sort("created_at", -1).limit(30)]
    return {"campaigns": out, "role": "client"}


@router.post("/campaigns/{campaign_id}/join")
async def join_campaign(campaign_id: str, body: dict, user: dict = Depends(require_role("client"))):
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(404, "Campania nu există")
    c = await db.community_campaigns.find_one({"_id": ObjectId(campaign_id)})
    if not c:
        raise HTTPException(404, "Campania nu există")
    if c["status"] != "open":
        raise HTTPException(400, "Campania nu mai acceptă înscrieri")
    property_id = body.get("property_id")
    if not property_id or not ObjectId.is_valid(property_id):
        raise HTTPException(400, "property_id este obligatoriu")
    prop = await db.properties.find_one({"_id": ObjectId(property_id), "owner_id": user["id"],
                                         "building_id": c["building_id"]})
    if not prop:
        raise HTTPException(403, "Proprietatea nu face parte din acest bloc")
    if any(p["property_id"] == property_id for p in c.get("participants") or []):
        raise HTTPException(409, "Ești deja înscris cu această proprietate")
    await db.community_campaigns.update_one({"_id": c["_id"]}, {"$push": {"participants": {
        "property_id": property_id, "owner_id": user["id"], "owner_name": user["name"], "joined_at": _now()}}})
    if c.get("created_by") and c["created_by"] != user["id"]:
        await notify(c["created_by"], f"➕ {_first_name(user['name'])} s-a alăturat campaniei",
                     f"„{c['title']}” are acum {len(c.get('participants') or []) + 1} participanți.",
                     type_="campaign", link="/client?tab=property")
    return {"ok": True, "participants_count": len(c.get("participants") or []) + 1}


@router.post("/campaigns/{campaign_id}/offer")
async def campaign_offer(campaign_id: str, data: OfferIn, user: dict = Depends(require_role("specialist"))):
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(404, "Campania nu există")
    c = await db.community_campaigns.find_one({"_id": ObjectId(campaign_id)})
    if not c:
        raise HTTPException(404, "Campania nu există")
    if c["status"] != "open":
        raise HTTPException(400, "Campania nu mai primește oferte")
    offer = {"specialist_id": user["id"], "specialist_name": user["name"],
             "verified": bool(user.get("verified")), "price_per_unit": data.price_per_unit,
             "message": data.message, "created_at": _now()}
    await db.community_campaigns.update_one({"_id": c["_id"]},
                                            {"$pull": {"offers": {"specialist_id": user["id"]}}})
    await db.community_campaigns.update_one({"_id": c["_id"]}, {"$push": {"offers": offer}})
    for p in c.get("participants") or []:
        await notify(p["owner_id"], f"💰 Ofertă de grup: {data.price_per_unit} RON/apartament",
                     f"{user['name']} a trimis o ofertă pentru „{c['title']}”.",
                     type_="campaign_offer", link="/client?tab=property")
    return {"ok": True}


@router.post("/campaigns/{campaign_id}/accept-offer")
async def accept_campaign_offer(campaign_id: str, body: dict, user: dict = Depends(require_role("client", "admin"))):
    if not ObjectId.is_valid(campaign_id):
        raise HTTPException(404, "Campania nu există")
    c = await db.community_campaigns.find_one({"_id": ObjectId(campaign_id)})
    if not c:
        raise HTTPException(404, "Campania nu există")
    if c["status"] != "open":
        raise HTTPException(400, "Campania nu mai e deschisă")
    if user.get("role") != "admin" and c.get("created_by") != user["id"]:
        raise HTTPException(403, "Doar inițiatorul campaniei poate accepta oferta")
    sid = body.get("specialist_id")
    offer = next((o for o in c.get("offers") or [] if o["specialist_id"] == sid), None)
    if not offer:
        raise HTTPException(404, "Oferta nu există")

    participants = c.get("participants") or []
    props = {}
    obj_ids = [ObjectId(p["property_id"]) for p in participants if ObjectId.is_valid(p["property_id"])]
    async for pr in db.properties.find({"_id": {"$in": obj_ids}}):
        props[str(pr["_id"])] = pr
    created_requests = []
    for p in participants:
        pr = props.get(p["property_id"]) or {}
        doc = {
            "property_id": p["property_id"], "category": c["category"], "title": c["title"],
            "description": f"Campanie comună „{c['title']}” — {c.get('building_name')}. Preț de grup: {offer['price_per_unit']} RON/apartament.",
            "priority": "normal", "budget_estimate": offer["price_per_unit"],
            "county": pr.get("county") or pr.get("zone") or pr.get("city"), "photos": None,
            "client_id": p["owner_id"], "client_name": p.get("owner_name"),
            "property_name": pr.get("name"), "property_address": pr.get("address"),
            "status": "assigned", "specialist_id": sid, "specialist_name": offer["specialist_name"],
            "assigned_at": _now(), "escrow_amount": None,
            "direct_specialist_id": sid, "direct_specialist_name": offer["specialist_name"],
            "lead_fee_waived": True, "is_campaign": True, "campaign_id": campaign_id,
            "created_at": _now(),
        }
        res = await db.requests.insert_one(doc)
        rid = str(res.inserted_id)
        created_requests.append(rid)
        await log_event(rid, "request.created", actor=user, property_id=p["property_id"],
                        payload={"source": "community_campaign", "campaign_id": campaign_id,
                                 "title": c["title"], "category": c["category"], "priority": "normal"})
        await notify(p["owner_id"], f"✅ Campania „{c['title']}” e programată",
                     f"{offer['specialist_name']} va executa lucrarea la {offer['price_per_unit']} RON/apartament. Lucrarea ta apare în „Lucrări”.",
                     type_="campaign", link="/client?tab=jobs")
    await db.community_campaigns.update_one({"_id": c["_id"]}, {"$set": {
        "status": "scheduled", "accepted_offer": offer, "request_ids": created_requests,
        "scheduled_at": _now()}})
    await notify(sid, f"🎉 Ai câștigat campania de grup: {c['title']}",
                 f"{len(participants)} lucrări directe (taxă lead 0) au fost create — le găsești în „Lucrările mele”.",
                 type_="campaign", link="/specialist?tab=jobs")
    try:
        from orchestrator.engine import emit_signal
        await emit_signal("campaign_scheduled", {"campaign_id": campaign_id, "title": c["title"],
                                                 "building_id": c["building_id"],
                                                 "requests_created": len(created_requests)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[campaigns] campaign_scheduled signal failed: {e}")
    return {"ok": True, "requests_created": len(created_requests), "status": "scheduled"}


# ============= AUTO-DETECTION (nightly) =============

async def campaign_detection_tick():
    """PM-003: detectează automat scadențe comune (≥3 apartamente) și creează campanii + notificări."""
    created = 0
    async for b in db.buildings.find({}):
        bid = str(b["_id"])
        for opp in await detect_opportunities(bid):
            if opp["properties"] < 3:
                continue
            title = f"{opp['category_label']} — tot blocul"
            doc = {"building_id": bid, "building_name": b["name"], "category": opp["category"],
                   "title": title, "description": f"Detectat automat: {opp['properties']} apartamente au aceeași scadență de mentenanță.",
                   "status": "open", "source": "auto", "window_end": None,
                   "created_by": None, "created_by_name": "PropManage AI",
                   "participants": [], "offers": [], "accepted_offer": None, "created_at": _now()}
            res = await db.community_campaigns.insert_one(doc)
            await _notify_campaign_audience(doc, str(res.inserted_id))
            created += 1
    if created:
        logger.info(f"[campaigns] auto-created {created} community campaigns")
    return {"created": created}
