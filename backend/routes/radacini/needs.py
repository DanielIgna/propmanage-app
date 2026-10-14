"""Necesar pe proiect (semințe, unelte, materiale, servicii): promisiuni atomice și contribuții la „adus”."""
import logging
import math
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify
from .projects import ensure_active, load_project, need_coordinator, need_member, project_link, today_str

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

NEED_KINDS = ("seeds", "tools", "materials", "service")
MAX_QTY = 1_000_000
_CAS_TRIES = 6


def _qty(v: float, message: str) -> float:
    if not math.isfinite(v) or not 0 < v <= MAX_QTY:
        raise ValueError(message)
    return round(v, 3)


class NeedIn(BaseModel):
    kind: str
    item: str
    quantity: float
    unit: str

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in NEED_KINDS:
            raise ValueError("Tip de necesar necunoscut.")
        return v

    @field_validator("item")
    @classmethod
    def _item(cls, v: str) -> str:
        v = " ".join(v.split())
        if not 2 <= len(v) <= 80:
            raise ValueError("Denumirea trebuie să aibă între 2 și 80 de caractere.")
        return v

    @field_validator("quantity")
    @classmethod
    def _quantity(cls, v: float) -> float:
        return _qty(v, "Cantitatea trebuie să fie un număr pozitiv.")

    @field_validator("unit")
    @classmethod
    def _unit(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 20:
            raise ValueError("Unitatea are între 1 și 20 de caractere.")
        return v


class PledgeIn(BaseModel):
    quantity: float

    @field_validator("quantity")
    @classmethod
    def _quantity(cls, v: float) -> float:
        return _qty(v, "Cantitatea promisă trebuie să fie un număr pozitiv.")


def _pledged(need: dict) -> float:
    return round(sum(p.get("quantity", 0) for p in need.get("pledges", [])), 3)


def _fulfilled(need: dict) -> float:
    return round(sum(p.get("quantity", 0) for p in need.get("pledges", []) if p.get("fulfilled")), 3)


def _view(need: dict, uid: str) -> dict:
    out = serialize_doc(need)
    out.pop("rev", None)
    out["pledged_total"] = _pledged(need)
    out["fulfilled_total"] = _fulfilled(need)
    out["remaining"] = round(max(need["quantity"] - _pledged(need), 0), 3)
    out["pledges"] = [
        {**p, "index": i, "mine": p.get("user_id") == uid} for i, p in enumerate(need.get("pledges", []))
    ]
    return out


async def _load_need(need_id: str, user: dict) -> tuple[dict, dict, str, Optional[str]]:
    need = await db.radacini_project_needs.find_one({"_id": oid_or_404(need_id)})
    if not need:
        raise HTTPException(404, "Necesarul nu există.")
    project, access, role = await load_project(need["project_id"], user)
    return need, project, access, role


async def _cas(need: dict, fields: dict) -> bool:
    rev = need.get("rev", 0)
    res = await db.radacini_project_needs.update_one(
        {"_id": need["_id"], "rev": rev},
        {"$set": {**fields, "rev": rev + 1, "updated_at": now_iso()}},
    )
    return res.modified_count == 1


async def _reload(need: dict) -> dict:
    fresh = await db.radacini_project_needs.find_one({"_id": need["_id"]})
    if not fresh:
        raise HTTPException(404, "Necesarul nu există.")
    return fresh


# ----------------------------------------------------------------- rute

@router.get("/projects/{project_id}/needs")
async def list_needs(project_id: str, user: dict = Depends(get_current_user)):
    project, _, _ = await load_project(project_id, user)
    docs = await db.radacini_project_needs.find({"project_id": str(project["_id"])}).to_list(500)
    docs.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    uid = str(user["id"])
    return {"items": [_view(d, uid) for d in docs]}


@router.post("/projects/{project_id}/needs")
async def create_need(project_id: str, body: NeedIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "adăugarea necesarului")
    project, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    pid = str(project["_id"])
    if await db.radacini_project_needs.count_documents({"project_id": pid, "status": {"$ne": "cancelled"}}) >= 200:
        raise HTTPException(409, "Ai atins numărul maxim de necesare pentru proiect.")
    now = now_iso()
    doc = mark_demo({
        "project_id": pid,
        "kind": body.kind,
        "item": body.item,
        "quantity": body.quantity,
        "unit": body.unit,
        "status": "needed",
        "pledges": [],
        "created_by": str(user["id"]),
        "rev": 0,
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_project_needs.insert_one(doc)
    await emit("radacini.need_created", actor=user, payload={"project_id": pid, "need_id": str(doc["_id"])})
    return {"need": _view(doc, str(user["id"]))}


@router.post("/needs/{need_id}/pledge")
async def pledge_need(need_id: str, body: PledgeIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "promisiunea de necesar")
    uid = str(user["id"])
    need, project, access, _ = await _load_need(need_id, user)
    need_member(access)
    ensure_active(project)
    name = next((m.get("name") for m in project["members"] if m["user_id"] == uid), None) or user.get("name") or ""
    for _ in range(_CAS_TRIES):
        if need.get("status") != "needed":
            raise HTTPException(409, "Necesarul nu mai primește promisiuni.")
        if _pledged(need) + body.quantity > need["quantity"] + 1e-9:
            raise HTTPException(
                400,
                f"Cantitatea promisă depășește necesarul. Mai sunt disponibile "
                f"{round(max(need['quantity'] - _pledged(need), 0), 3)} {need['unit']}.",
            )
        pledge = {"user_id": uid, "name": name, "quantity": body.quantity, "at": now_iso(), "fulfilled": False}
        if await _cas(need, {"pledges": [*need.get("pledges", []), pledge]}):
            break
        need = await _reload(need)
    else:
        raise HTTPException(409, "Necesarul a fost modificat între timp. Reîncearcă.")
    await emit(
        "radacini.need_pledged", actor=user,
        payload={"project_id": need["project_id"], "need_id": need_id, "quantity": body.quantity},
    )
    return {"need": _view(await _reload(need), uid)}


@router.post("/needs/{need_id}/pledges/{index}/fulfilled")
async def fulfil_pledge(need_id: str, index: int, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "marcarea promisiunii ca adusă")
    uid = str(user["id"])
    need, project, access, _ = await _load_need(need_id, user)
    need_member(access)
    ensure_active(project)
    for _ in range(_CAS_TRIES):
        pledges = need.get("pledges", [])
        if not 0 <= index < len(pledges):
            raise HTTPException(404, "Promisiunea nu există.")
        p = pledges[index]
        if p.get("user_id") != uid:
            raise HTTPException(403, "Doar cel care a promis poate marca „adus”.")
        if p.get("fulfilled"):
            return {"need": _view(need, uid)}  # idempotent
        if need.get("status") == "cancelled":
            raise HTTPException(409, "Necesarul a fost anulat.")
        contribution_id = ObjectId()
        new_pledges = [
            {**q, "fulfilled": True, "fulfilled_at": now_iso(), "contribution_id": str(contribution_id)}
            if i == index else q
            for i, q in enumerate(pledges)
        ]
        changes: dict = {"pledges": new_pledges}
        if round(sum(q["quantity"] for q in new_pledges if q.get("fulfilled")), 3) >= need["quantity"] - 1e-9:
            changes["status"] = "covered"
        if await _cas(need, changes):
            break
        need = await _reload(need)
    else:
        raise HTTPException(409, "Necesarul a fost modificat între timp. Reîncearcă.")
    contribution = mark_demo({
        "_id": contribution_id,
        "project_id": need["project_id"],
        "member_user_id": uid,
        "member_name": p.get("name") or user.get("name") or "",
        "kind": "tools" if need["kind"] == "tools" else "materials",
        "amount": p["quantity"],
        "unit": need["unit"][:20],
        "description": f"Adus pentru necesar: {need['item']}"[:300],
        "activity_id": None,
        "date": today_str(),
        "status": "logged",
        "corrects_id": None,
        "need_id": need_id,
        "created_at": now_iso(),
    })
    try:
        await db.radacini_contributions.insert_one(contribution)
    except Exception:  # noqa: BLE001
        log.exception("radacini: contribuția pentru necesarul %s nu a putut fi creată", need_id)
    for m in project.get("members", []):
        if m.get("role") == "coordinator" and m["user_id"] != uid:
            await safe_notify(
                m["user_id"], "Necesar acoperit parțial" if changes.get("status") != "covered" else "Necesar acoperit",
                f"{p.get('name') or 'Un membru'} a adus {p['quantity']} {need['unit']} ({need['item']}) în „{project['title']}”.",
                link=project_link(project["_id"]), type_="project",
            )
    await emit(
        "radacini.need_fulfilled", actor=user,
        payload={"project_id": need["project_id"], "need_id": need_id, "contribution_id": str(contribution_id)},
    )
    return {"need": _view(await _reload(need), uid)}


@router.post("/needs/{need_id}/cancel")
async def cancel_need(need_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "anularea necesarului")
    need, project, access, role = await _load_need(need_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    for _ in range(_CAS_TRIES):
        if need.get("status") == "cancelled":
            return {"need": _view(need, str(user["id"]))}
        if need.get("status") != "needed":
            raise HTTPException(409, "Un necesar acoperit nu se mai poate anula.")
        if any(p.get("fulfilled") for p in need.get("pledges", [])):
            raise HTTPException(409, "Necesarul are deja cantități aduse și nu se mai poate anula.")
        if await _cas(need, {"status": "cancelled"}):
            break
        need = await _reload(need)
    else:
        raise HTTPException(409, "Necesarul a fost modificat între timp. Reîncearcă.")
    fresh = await _reload(need)
    for p in fresh.get("pledges", []):
        if p.get("user_id") != str(user["id"]):
            await safe_notify(
                p["user_id"], "Necesar anulat",
                f"Necesarul „{fresh['item']}” din „{project['title']}” a fost anulat.",
                link=project_link(project["_id"]), type_="project",
            )
    await emit("radacini.need_cancelled", actor=user, payload={"project_id": fresh["project_id"], "need_id": need_id})
    return {"need": _view(fresh, str(user["id"]))}
