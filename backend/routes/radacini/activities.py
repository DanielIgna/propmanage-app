"""Activități de proiect: calendar, înscriere cu locuri limitate, marcare făcut/anulat."""
import re
from datetime import date
from datetime import date as _Date  # câmpul `date` umbrește tipul în modelele pydantic
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, check_finite, mark_demo, now_iso, oid_or_404, safe_notify
from .constants import ACTIVITY_TYPE_IDS
from .projects import ensure_active, load_project, need_coordinator, need_member, project_link

router = APIRouter(route_class=RadaciniRoute)

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class _Common(BaseModel):
    @field_validator("type", check_fields=False)
    @classmethod
    def _v_type(cls, v):
        if v is not None and v not in ACTIVITY_TYPE_IDS:
            raise ValueError("Tip de activitate necunoscut.")
        return v

    @field_validator("title", check_fields=False)
    @classmethod
    def _v_title(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not 3 <= len(v) <= 120:
            raise ValueError("Titlul trebuie să aibă între 3 și 120 de caractere.")
        return v

    @field_validator("start_time", check_fields=False)
    @classmethod
    def _v_time(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _TIME_RE.match(v):
            raise ValueError("Ora de început trebuie să fie în formatul HH:MM.")
        return v

    @field_validator("duration_h", check_fields=False)
    @classmethod
    def _v_duration(cls, v):
        check_finite(v, "Durata trebuie să fie între 0 și 24 de ore.")
        if v is not None and not 0 < v <= 24:
            raise ValueError("Durata trebuie să fie între 0 și 24 de ore.")
        return v

    @field_validator("slots", check_fields=False)
    @classmethod
    def _v_slots(cls, v):
        if v is not None and not 1 <= v <= 500:
            raise ValueError("Numărul de locuri trebuie să fie între 1 și 500.")
        return v

    @field_validator("notes", check_fields=False)
    @classmethod
    def _v_notes(cls, v):
        if v is None:
            return None
        v = v.strip()
        if len(v) > 1000:
            raise ValueError("Notele au cel mult 1000 de caractere.")
        return v or None


class ActivityIn(_Common):
    type: str
    title: str
    date: date
    start_time: Optional[str] = None
    duration_h: Optional[float] = None
    slots: Optional[int] = None
    crop_plan_id: Optional[str] = None
    notes: Optional[str] = None


class ActivityPatch(_Common):
    type: Optional[str] = None
    title: Optional[str] = None
    date: Optional[_Date] = None
    start_time: Optional[str] = None
    duration_h: Optional[float] = None
    slots: Optional[int] = None
    crop_plan_id: Optional[str] = None
    notes: Optional[str] = None


# ----------------------------------------------------------------- helpers

def _link(act: dict) -> str:
    return project_link(act["project_id"])


def _view(act: dict, project: dict, uid: str) -> dict:
    out = serialize_doc(act)
    out.pop("rev", None)
    names = {m["user_id"]: m.get("name", "") for m in project.get("members", [])}
    parts = act.get("participants") or []
    out["participant_names"] = [names.get(p, "") for p in parts]
    out["joined"] = uid in parts
    slots = act.get("slots")
    out["slots_left"] = None if slots is None else max(slots - len(parts), 0)
    return out


async def _check_crop_plan(project_id: str, crop_plan_id: Optional[str]) -> None:
    if not crop_plan_id:
        return
    crop = await db.radacini_crop_plans.find_one({"_id": oid_or_404(crop_plan_id)})
    if not crop or crop.get("project_id") != project_id:
        raise HTTPException(400, "Cultura aleasă nu aparține acestui proiect.")


async def _load_activity(activity_id: str, user: dict):
    act = await db.radacini_activities.find_one({"_id": oid_or_404(activity_id)})
    if not act:
        raise HTTPException(404, "Activitatea nu există.")
    project, access, role = await load_project(act["project_id"], user)
    return act, project, access, role


def _need_scheduled(act: dict) -> None:
    if act.get("status") != "scheduled":
        raise HTTPException(409, "Activitatea nu mai este programată.")


async def _cas(act: dict, fields: dict) -> dict:
    """Actualizare condiționată pe `rev` și pe starea `scheduled` (409 la conflict)."""
    rev = act.get("rev", 0)
    changes = {**fields, "rev": rev + 1, "updated_at": now_iso()}
    res = await db.radacini_activities.update_one(
        {"_id": act["_id"], "status": "scheduled", "rev": rev}, {"$set": changes}
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Activitatea a fost modificată între timp. Reîncarcă pagina.")
    return {**act, **changes}


# ----------------------------------------------------------------- rute

@router.get("/projects/{project_id}/activities")
async def list_activities(
    project_id: str,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    project, _, _ = await load_project(project_id, user)
    flt: dict = {"project_id": str(project["_id"])}
    rng: dict = {}
    for key, val in (("$gte", from_), ("$lte", to)):
        if val:
            if not _DATE_RE.match(val):
                raise HTTPException(400, "Datele trebuie să fie în formatul AAAA-LL-ZZ.")
            rng[key] = val
    if rng:
        flt["date"] = rng
    docs = await db.radacini_activities.find(flt).to_list(1000)
    docs.sort(key=lambda a: (a.get("date") or "", a.get("start_time") or "", a.get("created_at") or ""))
    uid = str(user["id"])
    return {"items": [_view(d, project, uid) for d in docs]}


@router.post("/projects/{project_id}/activities")
async def create_activity(project_id: str, body: ActivityIn, user: dict = Depends(get_current_user)):
    project, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    pid = str(project["_id"])
    await _check_crop_plan(pid, body.crop_plan_id)
    now = now_iso()
    doc = mark_demo({
        "project_id": pid,
        **body.model_dump(mode="json"),
        "participants": [],
        "status": "scheduled",
        "rev": 0,
        "created_by": str(user["id"]),
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_activities.insert_one(doc)
    for m in project["members"]:
        if m["user_id"] != str(user["id"]):
            await safe_notify(
                m["user_id"],
                "Activitate nouă în proiect",
                f"„{doc['title']}” — {doc['date']}. Poți să te înscrii din calendar.",
                link=project_link(pid),
                type_="project",
            )
    await emit("radacini.activity_created", actor=user, payload={"project_id": pid, "activity_id": str(doc["_id"])})
    return {"activity": _view(doc, project, str(user["id"]))}


@router.patch("/activities/{activity_id}")
async def patch_activity(activity_id: str, body: ActivityPatch, user: dict = Depends(get_current_user)):
    act, project, access, role = await _load_activity(activity_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    _need_scheduled(act)
    changes = body.model_dump(mode="json", exclude_unset=True)
    for key in ("type", "title", "date"):
        if key in changes and changes[key] is None:
            raise HTTPException(400, f"Câmpul {key} nu poate fi gol.")
    if "crop_plan_id" in changes:
        await _check_crop_plan(act["project_id"], changes["crop_plan_id"])
    slots = changes.get("slots", act.get("slots"))
    if slots is not None and slots < len(act.get("participants") or []):
        raise HTTPException(400, "Numărul de locuri nu poate fi mai mic decât al participanților înscriși.")
    if not changes:
        return {"activity": _view(act, project, str(user["id"]))}
    updated = await _cas(act, changes)
    await emit("radacini.activity_updated", actor=user, payload={"project_id": act["project_id"], "activity_id": activity_id})
    return {"activity": _view(updated, project, str(user["id"]))}


@router.post("/activities/{activity_id}/join")
async def join_activity(activity_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    act, project, access, _ = await _load_activity(activity_id, user)
    need_member(access)
    ensure_active(project)
    _need_scheduled(act)
    parts = list(act.get("participants") or [])
    if uid in parts:
        raise HTTPException(409, "Participi deja la această activitate.")
    slots = act.get("slots")
    if slots is not None and len(parts) >= slots:
        raise HTTPException(409, "Nu mai sunt locuri libere.")
    updated = await _cas(act, {"participants": [*parts, uid]})
    await emit("radacini.activity_joined", actor=user, payload={"project_id": act["project_id"], "activity_id": activity_id})
    return {"activity": _view(updated, project, uid)}


@router.post("/activities/{activity_id}/leave")
async def leave_activity(activity_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    act, project, access, _ = await _load_activity(activity_id, user)
    need_member(access)
    ensure_active(project)
    _need_scheduled(act)
    parts = list(act.get("participants") or [])
    if uid not in parts:
        raise HTTPException(409, "Nu participi la această activitate.")
    updated = await _cas(act, {"participants": [p for p in parts if p != uid]})
    await emit("radacini.activity_left", actor=user, payload={"project_id": act["project_id"], "activity_id": activity_id})
    return {"activity": _view(updated, project, uid)}


@router.post("/activities/{activity_id}/done")
async def done_activity(activity_id: str, user: dict = Depends(get_current_user)):
    act, project, access, role = await _load_activity(activity_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    _need_scheduled(act)
    updated = await _cas(act, {"status": "done", "done_at": now_iso(), "done_by": str(user["id"])})
    await emit("radacini.activity_done", actor=user, payload={"project_id": act["project_id"], "activity_id": activity_id})
    return {"activity": _view(updated, project, str(user["id"]))}


@router.post("/activities/{activity_id}/cancel")
async def cancel_activity(activity_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    act, project, access, role = await _load_activity(activity_id, user)
    need_coordinator(access, role)
    ensure_active(project)
    _need_scheduled(act)
    updated = await _cas(act, {"status": "cancelled", "cancelled_at": now_iso(), "cancelled_by": uid})
    for p in act.get("participants") or []:
        if p != uid:
            await safe_notify(
                p,
                "Activitate anulată",
                f"Activitatea „{act['title']}” din {act['date']} a fost anulată.",
                link=_link(act),
                type_="project",
            )
    await emit("radacini.activity_cancelled", actor=user, payload={"project_id": act["project_id"], "activity_id": activity_id})
    return {"activity": _view(updated, project, uid)}
