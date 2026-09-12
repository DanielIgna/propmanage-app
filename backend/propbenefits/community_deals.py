"""PropBenefits · Community Deals (PB-002) — negocierea comunității, nu doar a ta.

REGULĂ: nu promitem procente. Beneficiile depind de acordurile comerciale și de
puterea comunității PropManage la momentul lansării.
"""
import uuid
from datetime import datetime, timezone

from db import db

DEAL_STATUSES = ["in_lucru", "negociere", "pilot", "lansat", "arhivat"]
DISCLAIMER = ("Beneficiile vor depinde de acordurile comerciale și de puterea "
              "comunității PropManage la momentul lansării.")

SEED_DEALS = [
    {"emoji": "🇮🇹", "title": "Gresie & faianță din Italia", "category": "Finisaje", "status": "negociere", "order": 1},
    {"emoji": "🇪🇸", "title": "Gresie & faianță din Spania", "category": "Finisaje", "status": "in_lucru", "order": 2},
    {"emoji": "🛋", "title": "Mobilier din Germania", "category": "Mobilier", "status": "negociere", "order": 3},
    {"emoji": "🛋", "title": "Mobilier din Italia", "category": "Mobilier", "status": "in_lucru", "order": 4},
    {"emoji": "🛋", "title": "Mobilier din Olanda", "category": "Mobilier", "status": "in_lucru", "order": 5},
    {"emoji": "🛋", "title": "Mobilier din Suedia", "category": "Mobilier", "status": "in_lucru", "order": 6},
    {"emoji": "🛋", "title": "Mobilier din Danemarca", "category": "Mobilier", "status": "in_lucru", "order": 7},
    {"emoji": "🎨", "title": "Design interior", "category": "Servicii", "status": "negociere", "order": 8},
    {"emoji": "🚿", "title": "Baie complet amenajată", "category": "Renovare", "status": "in_lucru", "order": 9},
    {"emoji": "⚡", "title": "Pompe de căldură", "category": "Energie", "status": "negociere", "order": 10},
    {"emoji": "☀️", "title": "Panouri fotovoltaice", "category": "Energie", "status": "negociere", "order": 11},
    {"emoji": "🏠", "title": "City Partner Cluj", "category": "Parteneriat local", "status": "pilot", "order": 12},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ensure_deals_seed():
    if await db.pb_community_deals.count_documents({}, limit=1):
        return
    for d in SEED_DEALS:
        await db.pb_community_deals.insert_one({
            "id": uuid.uuid4().hex[:12], **d,
            "description": "", "supporter_ids": [], "active": True,
            "created_at": _now(), "updated_at": _now(),
        })


async def list_deals(user_id: str = None, include_archived: bool = False) -> list:
    await ensure_deals_seed()
    q = {} if include_archived else {"status": {"$ne": "arhivat"}, "active": True}
    out = []
    async for d in db.pb_community_deals.find(q, {"_id": 0}).sort("order", 1):
        supporters = d.pop("supporter_ids", []) or []
        d["supporters"] = len(supporters)
        if user_id is not None:
            d["supported_by_me"] = user_id in supporters
        out.append(d)
    return out


async def support_deal(deal_id: str, user_id: str) -> dict:
    res = await db.pb_community_deals.update_one(
        {"id": deal_id}, {"$addToSet": {"supporter_ids": user_id}, "$set": {"updated_at": _now()}})
    if not res.matched_count:
        return {"error": "Deal inexistent."}
    d = await db.pb_community_deals.find_one({"id": deal_id}, {"_id": 0, "supporter_ids": 1, "title": 1})
    return {"ok": True, "supporters": len(d.get("supporter_ids") or []),
            "message": f"Susținerea ta contează — cu cât comunitatea e mai mare, cu atât „{d['title']}” devine mai valoros."}


ALLOWED = ("emoji", "title", "category", "status", "description", "order", "active")


async def upsert_deal(data: dict, deal_id: str = None) -> dict:
    if "status" in data and data["status"] not in DEAL_STATUSES:
        raise ValueError(f"status invalid — permise: {', '.join(DEAL_STATUSES)}")
    clean = {k: v for k, v in data.items() if k in ALLOWED}
    clean["updated_at"] = _now()
    if deal_id:
        res = await db.pb_community_deals.update_one({"id": deal_id}, {"$set": clean})
        if not res.matched_count:
            raise LookupError("Deal inexistent.")
        return await db.pb_community_deals.find_one({"id": deal_id}, {"_id": 0, "supporter_ids": 0})
    if not str(clean.get("title", "")).strip():
        raise ValueError("Titlul este obligatoriu.")
    doc = {"id": uuid.uuid4().hex[:12], "emoji": clean.get("emoji", "🤝"), "title": clean["title"],
           "category": clean.get("category", ""), "status": clean.get("status", "in_lucru"),
           "description": clean.get("description", ""), "order": int(clean.get("order", 99)),
           "active": True, "supporter_ids": [], "created_at": _now(), "updated_at": _now()}
    await db.pb_community_deals.insert_one({**doc})
    doc.pop("supporter_ids")
    return doc
