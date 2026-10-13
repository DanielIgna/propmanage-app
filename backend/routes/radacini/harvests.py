"""Recolte și alocări: coordonatorul înregistrează, proprietarul confirmă, coordonatorii împart.

Fără plăți: platforma doar consemnează cine primește ce cantitate din recoltă.
"""
import logging
from datetime import date as _Date  # câmpul `date` umbrește tipul în modelele pydantic
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify
from .crops import resolve_crop
from .projects import (
    ensure_active,
    load_project,
    member_role,
    need_coordinator,
    need_member,
    today_str,
)

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

MAX_HARVEST_KG = 1_000_000
EPS = 1e-6


def harvest_link(project_id) -> str:
    return f"/radacini/proiecte/{project_id}?tab=recolta"


def _qty(v: float) -> float:
    return round(float(v), 3)


# ----------------------------------------------------------------- scheme

class HarvestIn(BaseModel):
    crop_plan_id: Optional[str] = None
    crop: Optional[str] = None
    quantity_kg: float
    date: Optional[_Date] = None
    note: Optional[str] = None

    @field_validator("crop")
    @classmethod
    def _crop(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not 2 <= len(v) <= 60:
            raise ValueError("Cultura trebuie să aibă între 2 și 60 de caractere.")
        return v

    @field_validator("quantity_kg")
    @classmethod
    def _quantity(cls, v: float) -> float:
        if not 0 < v <= MAX_HARVEST_KG:
            raise ValueError("Cantitatea recoltei trebuie să fie între 0 și 1 000 000 kg.")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Nota are cel mult 500 de caractere.")
        return v or None


class AllocationIn(BaseModel):
    member_user_id: str
    quantity_kg: float

    @field_validator("quantity_kg")
    @classmethod
    def _quantity(cls, v: float) -> float:
        if not 0 < v <= MAX_HARVEST_KG:
            raise ValueError("Cantitatea alocată trebuie să fie pozitivă.")
        return v


# ----------------------------------------------------------------- helpers

def _owner(project: dict) -> Optional[dict]:
    return next((m for m in project.get("members", []) if m.get("role") == "owner"), None)


def _member_name(project: dict, user_id: str) -> str:
    return next((m.get("name") for m in project.get("members", []) if m.get("user_id") == user_id), None) or ""


def _allocated_sum(allocs: list[dict]) -> float:
    return _qty(sum(a.get("quantity_kg") or 0 for a in allocs))


async def _load_harvest(harvest_id: str, user: dict) -> tuple[dict, dict, str, Optional[str]]:
    harvest = await db.radacini_harvests.find_one({"_id": oid_or_404(harvest_id)})
    if not harvest:
        raise HTTPException(404, "Recolta nu există.")
    project, access, role = await load_project(harvest["project_id"], user)
    return harvest, project, access, role


def _harvest_view(h: dict, project: dict, allocs: Optional[list[dict]] = None) -> dict:
    out = serialize_doc(h)
    out.pop("rev", None)
    out["recorded_by_name"] = _member_name(project, h.get("recorded_by", ""))
    if allocs is not None:
        allocated = _allocated_sum(allocs)
        out["allocated_kg"] = allocated
        out["remaining_kg"] = max(_qty(h["quantity_kg"] - allocated), 0.0)
    return out


async def _agreement_percent(project: dict) -> int:
    """Procentul din recoltă al proprietarului, doar dacă acordul e `harvest_share`."""
    agreement_id = project.get("agreement_id")
    if not agreement_id or len(str(agreement_id)) != 24 or not ObjectId.is_valid(str(agreement_id)):
        return 0
    agreement = await db.radacini_agreements.find_one({"_id": ObjectId(str(agreement_id))})
    if not agreement or agreement.get("model") != "harvest_share":
        return 0
    pct = (agreement.get("terms") or {}).get("harvest_share_percent") or 0
    return pct if isinstance(pct, (int, float)) and pct > 0 else 0


async def _create_owner_allocation(harvest: dict, project: dict, actor: dict) -> Optional[dict]:
    """Alocarea automată (`agreement_share`) a proprietarului. Idempotentă; erorile se loghează."""
    try:
        hid = str(harvest["_id"])
        owner = _owner(project)
        pct = await _agreement_percent(project)
        if not owner or pct <= 0:
            return None
        if await db.radacini_allocations.find_one({"harvest_id": hid, "basis": "agreement_share"}):
            return None
        qty = round(harvest["quantity_kg"] * pct / 100, 1)
        if qty <= 0:
            return None
        doc = mark_demo({
            "harvest_id": hid,
            "project_id": harvest["project_id"],
            "member_user_id": owner["user_id"],
            "member_name": owner.get("name", ""),
            "quantity_kg": qty,
            "basis": "agreement_share",
            "status": "allocated",
            "created_by": str(actor.get("id", "")),
            "created_at": now_iso(),
        })
        await db.radacini_allocations.insert_one(doc)
        await safe_notify(
            owner["user_id"],
            "Parte din recoltă alocată",
            f"Ți s-au alocat {qty} kg din recolta de {harvest['crop']} conform acordului.",
            link=harvest_link(harvest["project_id"]),
            type_="project",
        )
        await emit(
            "radacini.allocation_created",
            actor=actor,
            payload={"project_id": harvest["project_id"], "harvest_id": hid, "allocation_id": str(doc["_id"]), "basis": "agreement_share"},
        )
        return doc
    except Exception:  # noqa: BLE001
        log.exception("radacini: alocarea automată nu a putut fi creată pentru recolta %s", harvest.get("_id"))
        return None


# ----------------------------------------------------------------- recolte

@router.get("/projects/{project_id}/harvests")
async def list_harvests(project_id: str, user: dict = Depends(get_current_user)):
    project, _, _ = await load_project(project_id, user)
    pid = str(project["_id"])
    docs = await db.radacini_harvests.find({"project_id": pid}).to_list(2000)
    docs.sort(key=lambda h: (h.get("date") or "", h.get("created_at") or ""), reverse=True)
    allocs = await db.radacini_allocations.find({"project_id": pid}).to_list(10000)
    by_harvest: dict = {}
    for a in allocs:
        by_harvest.setdefault(a["harvest_id"], []).append(a)
    totals: dict = {}
    for h in docs:
        row = totals.setdefault(h["crop"], {"crop": h["crop"], "quantity_kg": 0.0, "pending_kg": 0.0})
        row["quantity_kg" if h.get("status") == "confirmed" else "pending_kg"] += h["quantity_kg"]
    rows = sorted(totals.values(), key=lambda r: r["crop"])
    for r in rows:
        r["quantity_kg"] = _qty(r["quantity_kg"])
        r["pending_kg"] = _qty(r["pending_kg"])
    return {
        "items": [_harvest_view(h, project, by_harvest.get(str(h["_id"]), [])) for h in docs],
        "totals": rows,
    }


@router.post("/projects/{project_id}/harvests")
async def create_harvest(project_id: str, body: HarvestIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    project, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    pid = str(project["_id"])
    day = body.date.isoformat() if body.date else today_str()
    if day > today_str():
        raise HTTPException(400, "Data recoltei nu poate fi în viitor.")
    plan = None
    if body.crop_plan_id:
        plan = await db.radacini_crop_plans.find_one({"_id": oid_or_404(body.crop_plan_id)})
        if not plan or plan.get("project_id") != pid:
            raise HTTPException(400, "Planul de cultură ales nu aparține acestui proiect.")
        crop = plan["crop"]
    elif body.crop:
        crop = resolve_crop(body.crop)["crop"]
    else:
        raise HTTPException(400, "Alege o cultură din plan sau scrie numele culturii.")
    owner = _owner(project)
    auto_confirm = bool(owner) and owner["user_id"] == uid
    now = now_iso()
    doc = mark_demo({
        "project_id": pid,
        "crop_plan_id": body.crop_plan_id,
        "crop": crop,
        "quantity_kg": _qty(body.quantity_kg),
        "date": day,
        "note": body.note,
        "recorded_by": uid,
        "status": "confirmed" if auto_confirm else "recorded",
        "rev": 0,
        "created_at": now,
    })
    if auto_confirm:
        doc["confirmed_by"] = uid
        doc["confirmed_at"] = now
    await db.radacini_harvests.insert_one(doc)
    if plan is not None:
        await db.radacini_crop_plans.update_one(
            {"_id": plan["_id"]}, {"$set": {"status": "harvested", "updated_at": now}}
        )
    await emit(
        "radacini.harvest_recorded",
        actor=user,
        payload={"project_id": pid, "harvest_id": str(doc["_id"]), "crop": crop, "quantity_kg": doc["quantity_kg"]},
    )
    if auto_confirm:
        await _create_owner_allocation(doc, project, user)
        await emit("radacini.harvest_confirmed", actor=user, payload={"project_id": pid, "harvest_id": str(doc["_id"])})
    elif owner:
        await safe_notify(
            owner["user_id"],
            "Recoltă de confirmat",
            f"{user.get('name') or 'Un coordonator'} a înregistrat {doc['quantity_kg']} kg de {crop} în „{project['title']}”.",
            link=harvest_link(pid),
            type_="project",
        )
    return {"harvest": _harvest_view(doc, project)}


@router.post("/harvests/{harvest_id}/confirm")
async def confirm_harvest(harvest_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    harvest, project, access, role = await _load_harvest(harvest_id, user)
    need_member(access)
    if role != "owner":
        raise HTTPException(403, "Recolta o confirmă proprietarul terenului.")
    ensure_active(project)
    now = now_iso()
    res = await db.radacini_harvests.update_one(
        {"_id": harvest["_id"], "status": "recorded"},
        {"$set": {"status": "confirmed", "confirmed_by": uid, "confirmed_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Recolta a fost deja confirmată.")
    harvest = {**harvest, "status": "confirmed", "confirmed_by": uid, "confirmed_at": now}
    await _create_owner_allocation(harvest, project, user)
    if harvest.get("recorded_by") and harvest["recorded_by"] != uid:
        await safe_notify(
            harvest["recorded_by"],
            "Recoltă confirmată",
            f"Recolta de {harvest['crop']} ({harvest['quantity_kg']} kg) din „{project['title']}” a fost confirmată. Poți aloca cantitățile.",
            link=harvest_link(project["_id"]),
            type_="project",
        )
    await emit(
        "radacini.harvest_confirmed",
        actor=user,
        payload={"project_id": str(project["_id"]), "harvest_id": harvest_id},
    )
    allocs = await db.radacini_allocations.find({"harvest_id": harvest_id}).to_list(2000)
    return {"harvest": _harvest_view(harvest, project, allocs)}


# ----------------------------------------------------------------- alocări

@router.get("/harvests/{harvest_id}/allocations")
async def list_allocations(harvest_id: str, user: dict = Depends(get_current_user)):
    harvest, _, access, _ = await _load_harvest(harvest_id, user)
    need_member(access)
    docs = await db.radacini_allocations.find({"harvest_id": str(harvest["_id"])}).to_list(2000)
    docs.sort(key=lambda a: a.get("created_at") or "")
    allocated = _allocated_sum(docs)
    return {
        "items": [serialize_doc(a) for a in docs],
        "allocated_kg": allocated,
        "remaining_kg": max(_qty(harvest["quantity_kg"] - allocated), 0.0),
    }


@router.post("/harvests/{harvest_id}/allocations")
async def create_allocation(harvest_id: str, body: AllocationIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    harvest, project, access, role = await _load_harvest(harvest_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    if harvest.get("status") != "confirmed":
        raise HTTPException(409, "Alocările se pot face doar după confirmarea recoltei de către proprietar.")
    target = body.member_user_id
    if not member_role(project, target):
        raise HTTPException(400, "Primitorul trebuie să fie membru al proiectului.")
    qty = _qty(body.quantity_kg)
    hid = str(harvest["_id"])
    existing = await db.radacini_allocations.find({"harvest_id": hid}).to_list(2000)
    if _allocated_sum(existing) + qty > harvest["quantity_kg"] + EPS:
        raise HTTPException(400, "Cantitatea depășește recolta rămasă.")
    doc = mark_demo({
        "harvest_id": hid,
        "project_id": harvest["project_id"],
        "member_user_id": target,
        "member_name": _member_name(project, target),
        "quantity_kg": qty,
        "basis": "manual",
        "status": "allocated",
        "created_by": uid,
        "created_at": now_iso(),
    })
    # Serializare: inserăm, apoi creștem `rev` pe recoltă doar dacă nu s-a schimbat între timp.
    # Dacă altcineva a alocat în paralel, `rev` nu mai corespunde → retragem alocarea și răspundem 409.
    await db.radacini_allocations.insert_one(doc)
    rev = harvest.get("rev", 0)
    res = await db.radacini_harvests.update_one({"_id": harvest["_id"], "rev": rev}, {"$set": {"rev": rev + 1}})
    if res.modified_count != 1:
        await db.radacini_allocations.delete_one({"_id": doc["_id"]})
        raise HTTPException(409, "Recolta a fost modificată între timp. Reîncearcă.")
    if target != uid:
        await safe_notify(
            target,
            "Parte din recoltă alocată",
            f"Ți s-au alocat {qty} kg din recolta de {harvest['crop']} în „{project['title']}”.",
            link=harvest_link(project["_id"]),
            type_="project",
        )
    await emit(
        "radacini.allocation_created",
        actor=user,
        payload={"project_id": harvest["project_id"], "harvest_id": hid, "allocation_id": str(doc["_id"]), "basis": "manual"},
    )
    return {"allocation": serialize_doc(doc)}


async def _load_allocation(allocation_id: str) -> dict:
    alloc = await db.radacini_allocations.find_one({"_id": oid_or_404(allocation_id)})
    if not alloc:
        raise HTTPException(404, "Alocarea nu există.")
    return alloc


@router.delete("/allocations/{allocation_id}")
async def delete_allocation(allocation_id: str, user: dict = Depends(get_current_user)):
    alloc = await _load_allocation(allocation_id)
    project, access, role = await load_project(alloc["project_id"], user)
    need_coordinator(access, role)
    ensure_active(project)
    if alloc.get("basis") != "manual":
        raise HTTPException(409, "Alocarea din acord nu poate fi ștearsă.")
    if alloc.get("status") != "allocated":
        raise HTTPException(409, "Alocarea a fost deja primită.")
    res = await db.radacini_allocations.delete_one({"_id": alloc["_id"], "status": "allocated", "basis": "manual"})
    if res.deleted_count != 1:
        raise HTTPException(409, "Alocarea a fost modificată între timp.")
    if alloc["member_user_id"] != str(user["id"]):
        await safe_notify(
            alloc["member_user_id"],
            "Alocare anulată",
            f"Alocarea de {alloc['quantity_kg']} kg din „{project['title']}” a fost anulată.",
            link=harvest_link(project["_id"]),
            type_="project",
        )
    await emit(
        "radacini.allocation_removed",
        actor=user,
        payload={"project_id": alloc["project_id"], "harvest_id": alloc["harvest_id"], "allocation_id": allocation_id},
    )
    return {"ok": True}


@router.post("/allocations/{allocation_id}/received")
async def allocation_received(allocation_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    alloc = await _load_allocation(allocation_id)
    if alloc.get("member_user_id") != uid:
        raise HTTPException(403, "Doar primitorul poate confirma primirea.")
    now = now_iso()
    res = await db.radacini_allocations.update_one(
        {"_id": alloc["_id"], "status": "allocated"},
        {"$set": {"status": "received", "received_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Primirea a fost deja confirmată.")
    creator = alloc.get("created_by")
    if creator and creator != uid:
        await safe_notify(
            creator,
            "Cantitate primită",
            f"{alloc.get('member_name') or 'Un membru'} a confirmat primirea a {alloc['quantity_kg']} kg.",
            link=harvest_link(alloc["project_id"]),
            type_="project",
        )
    await emit(
        "radacini.allocation_received",
        actor=user,
        payload={"project_id": alloc["project_id"], "harvest_id": alloc["harvest_id"], "allocation_id": allocation_id},
    )
    return {"allocation": serialize_doc({**alloc, "status": "received", "received_at": now})}
