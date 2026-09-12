"""GBOS P0 — Calendar mentenanță (CX-4): planuri recurente per proprietate → cereri repetate.

Colecție nouă aditivă: maintenance_tasks.
Bucla de creștere: task scadent → reminder → cerere 1-click (direct la specialistul de încredere, taxă lead 0).
"""
import logging
from datetime import datetime, timezone, date, timedelta
from typing import Optional, Literal

from bson import ObjectId
from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from services import notify, log_event

logger = logging.getLogger("propmanage.maintenance_calendar")
router = APIRouter(prefix="/api/maintenance", tags=["maintenance-calendar"])

DONE_STATUSES = ["completed", "confirmed"]

TEMPLATES = [
    {"key": "centrala_termica", "title": "Revizie centrală termică", "category": "hvac", "frequency_months": 12},
    {"key": "clima", "title": "Igienizare aer condiționat", "category": "hvac", "frequency_months": 12},
    {"key": "cos_fum", "title": "Curățare coș de fum", "category": "handyman", "frequency_months": 12},
    {"key": "jgheaburi", "title": "Curățare jgheaburi și burlane", "category": "handyman", "frequency_months": 6},
    {"key": "instalatie_electrica", "title": "Verificare instalație electrică", "category": "electric", "frequency_months": 24},
    {"key": "instalatie_sanitara", "title": "Verificare instalații sanitare", "category": "plumbing", "frequency_months": 12},
    {"key": "zugraveala", "title": "Împrospătare zugrăveală", "category": "zugravit", "frequency_months": 36},
    {"key": "ferestre", "title": "Reglaj și etanșare ferestre", "category": "handyman", "frequency_months": 24},
]
TEMPLATE_MAP = {t["key"]: t for t in TEMPLATES}


def _today() -> str:
    return date.today().isoformat()


def _status_for(next_due: str) -> str:
    today = _today()
    if next_due < today:
        return "overdue"
    if next_due <= (date.today() + timedelta(days=30)).isoformat():
        return "due_soon"
    return "ok"


class TaskIn(BaseModel):
    property_id: str
    template_key: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=200)
    category: Optional[str] = None
    frequency_months: Optional[int] = Field(default=None, ge=1, le=120)
    next_due: Optional[str] = None  # YYYY-MM-DD


class TaskRequestIn(BaseModel):
    mode: Literal["open", "direct"] = "open"
    specialist_id: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=3000)
    budget_estimate: Optional[float] = Field(default=None, ge=0)


@router.get("/templates")
async def maintenance_templates(user: dict = Depends(require_role("client"))):
    return {"templates": TEMPLATES}


@router.get("/tasks")
async def list_tasks(user: dict = Depends(require_role("client"))):
    props = {str(p["_id"]): p.get("name") for p in await db.properties.find({"owner_id": user["id"]}).to_list(50)}
    out = []
    async for t in db.maintenance_tasks.find({"owner_id": user["id"], "active": True}).sort("next_due", 1):
        out.append({
            "id": str(t["_id"]),
            "property_id": t["property_id"],
            "property_name": props.get(t["property_id"]),
            "title": t["title"],
            "category": t.get("category"),
            "frequency_months": t["frequency_months"],
            "next_due": t["next_due"],
            "last_done": t.get("last_done"),
            "last_request_id": t.get("last_request_id"),
            "status": _status_for(t["next_due"]),
        })
    return {"tasks": out, "properties_count": len(props)}


@router.post("/tasks")
async def create_task(data: TaskIn, user: dict = Depends(require_role("client"))):
    if not ObjectId.is_valid(data.property_id):
        raise HTTPException(404, "Property not found")
    prop = await db.properties.find_one({"_id": ObjectId(data.property_id), "owner_id": user["id"]})
    if not prop:
        raise HTTPException(404, "Property not found")

    tpl = TEMPLATE_MAP.get(data.template_key or "")
    title = data.title or (tpl and tpl["title"])
    category = data.category or (tpl and tpl["category"])
    freq = data.frequency_months or (tpl and tpl["frequency_months"])
    if not title or not freq:
        raise HTTPException(400, "title și frequency_months sunt obligatorii (sau un template_key valid)")

    dup = await db.maintenance_tasks.find_one({
        "owner_id": user["id"], "property_id": data.property_id, "title": title, "active": True})
    if dup:
        raise HTTPException(409, "Ai deja acest task în calendar pentru această proprietate")

    next_due = data.next_due or (date.today() + relativedelta(months=freq)).isoformat()
    try:
        date.fromisoformat(next_due)
    except ValueError:
        raise HTTPException(400, "next_due trebuie să fie YYYY-MM-DD")

    doc = {
        "owner_id": user["id"],
        "property_id": data.property_id,
        "template_key": data.template_key,
        "title": title,
        "category": category,
        "frequency_months": freq,
        "next_due": next_due,
        "last_done": None,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.maintenance_tasks.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    doc["status"] = _status_for(next_due)
    doc["property_name"] = prop.get("name")
    return doc


async def _get_owned_task(task_id: str, user: dict) -> dict:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(404, "Task not found")
    t = await db.maintenance_tasks.find_one({"_id": ObjectId(task_id), "owner_id": user["id"], "active": True})
    if not t:
        raise HTTPException(404, "Task not found")
    return t


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, user: dict = Depends(require_role("client"))):
    t = await _get_owned_task(task_id, user)
    next_due = (date.today() + relativedelta(months=t["frequency_months"])).isoformat()
    await db.maintenance_tasks.update_one({"_id": t["_id"]}, {"$set": {
        "last_done": _today(), "next_due": next_due, "last_reminded_at": None}})
    return {"ok": True, "next_due": next_due, "last_done": _today(), "status": _status_for(next_due)}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(require_role("client"))):
    t = await _get_owned_task(task_id, user)
    await db.maintenance_tasks.update_one({"_id": t["_id"]}, {"$set": {"active": False}})
    return {"ok": True}


@router.post("/tasks/{task_id}/request")
async def request_from_task(task_id: str, data: TaskRequestIn, user: dict = Depends(require_role("client"))):
    """Cerere 1-click din task: publică pentru oferte SAU direct la specialistul de încredere (taxă lead 0)."""
    t = await _get_owned_task(task_id, user)
    prop = await db.properties.find_one({"_id": ObjectId(t["property_id"]), "owner_id": user["id"]})
    if not prop:
        raise HTTPException(404, "Property not found")

    direct_spec = None
    if data.mode == "direct":
        if not data.specialist_id or not ObjectId.is_valid(data.specialist_id):
            raise HTTPException(400, "specialist_id este obligatoriu pentru cererea directă")
        direct_spec = await db.users.find_one({"_id": ObjectId(data.specialist_id), "role": "specialist"})
        if not direct_spec:
            raise HTTPException(404, "Specialist inexistent")
        worked = await db.requests.find_one({
            "client_id": user["id"], "specialist_id": data.specialist_id, "status": {"$in": DONE_STATUSES}})
        if not worked:
            raise HTTPException(403, "Poți trimite direct doar către specialiști cu care ai finalizat o lucrare")

    doc = {
        "property_id": t["property_id"],
        "category": t.get("category") or "handyman",
        "title": t["title"],
        "description": data.description or f"Programare „{t['title']}” — mentenanță periodică (din calendarul proprietății).",
        "priority": "normal",
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
        "maintenance_task_id": task_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if direct_spec:
        doc.update({
            "direct_specialist_id": data.specialist_id,
            "direct_specialist_name": direct_spec.get("name"),
            "lead_fee_waived": True,
            "is_rebooking": True,
        })
    res = await db.requests.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    await db.maintenance_tasks.update_one({"_id": t["_id"]}, {"$set": {
        "last_request_id": doc["id"], "last_requested_at": datetime.now(timezone.utc).isoformat()}})
    await log_event(doc["id"], "request.created", actor=user, property_id=t["property_id"],
                    payload={"title": t["title"], "category": doc["category"], "priority": "normal",
                             "source": "maintenance_calendar", "mode": data.mode})

    if direct_spec:
        await notify(
            data.specialist_id,
            f"⭐ {user['name']} te-a re-angajat (mentenanță)",
            f"Cerere directă pentru tine: '{t['title']}'. Taxa de lead este 0 RON — răspunde rapid!",
            type_="rebook", link="/specialist")
    else:
        spec_query = {"role": "specialist"}
        if doc["category"]:
            spec_query = {"role": "specialist", "$or": [{"specialty": doc["category"]}, {"specialty": None}]}
        for s in await db.users.find(spec_query).to_list(50):
            await notify(str(s["_id"]), f"Lead nou: {t['title']}",
                         f"Solicitare normal în categoria {doc['category']}. Buget estimat: {data.budget_estimate or '—'} RON",
                         type_="lead", link="/specialist")
    return doc


async def maintenance_due_tick():
    """Zilnic: reminder pentru taskurile scadente în ≤7 zile (max 1 reminder / 6 zile / task)."""
    horizon = (date.today() + timedelta(days=7)).isoformat()
    stale = (datetime.now(timezone.utc) - timedelta(days=6)).isoformat()
    sent = 0
    async for t in db.maintenance_tasks.find({"active": True, "next_due": {"$lte": horizon}}):
        last = t.get("last_reminded_at")
        if last and last > stale:
            continue
        overdue = t["next_due"] < _today()
        await notify(
            t["owner_id"],
            f"🔧 {t['title']} — {'termen depășit' if overdue else 'scadentă în curând'}",
            f"Programată pentru {t['next_due']}. Solicită oferta în 1 click din calendarul de mentenanță.",
            type_="maintenance_due", link="/client?tab=property")
        await db.maintenance_tasks.update_one({"_id": t["_id"]}, {"$set": {
            "last_reminded_at": datetime.now(timezone.utc).isoformat()}})
        sent += 1
    if sent:
        logger.info(f"[maintenance] sent {sent} due reminders")
    return {"sent": sent}
