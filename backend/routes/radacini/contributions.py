"""Contribuții în proiect: evidență append-only, fără bani/puncte/drepturi. Fără PATCH sau DELETE.

Corecția = o contribuție nouă cu `corrects_id`; cea veche rămâne în istoric și iese din totaluri.
"""
from datetime import date as _Date  # câmpul `date` umbrește tipul în modelele pydantic
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, check_finite, mark_demo, now_iso, oid_or_404, safe_notify
from .constants import CONTRIBUTION_KIND_IDS
from .projects import ensure_active, load_project, need_member, project_link, reviewer_ids, today_str

router = APIRouter(route_class=RadaciniRoute)

DEFAULT_UNITS = {"labor_hours": "ore", "money": "RON", "materials": "buc", "tools": "buc", "land": "m²"}
FIXED_UNITS = ("labor_hours", "money")


class ContributionIn(BaseModel):
    kind: str
    amount: float
    unit: Optional[str] = None
    description: str
    activity_id: Optional[str] = None
    date: Optional[_Date] = None
    corrects_id: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in CONTRIBUTION_KIND_IDS:
            raise ValueError("Tip de contribuție necunoscut.")
        return v

    @field_validator("amount")
    @classmethod
    def _amount(cls, v: float) -> float:
        check_finite(v, "Cantitatea trebuie să fie un număr pozitiv.")
        if not 0 < v <= 1_000_000_000:
            raise ValueError("Cantitatea trebuie să fie un număr pozitiv.")
        return v

    @field_validator("unit")
    @classmethod
    def _unit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 20:
            raise ValueError("Unitatea are cel mult 20 de caractere.")
        return v or None

    @field_validator("description")
    @classmethod
    def _description(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 300:
            raise ValueError("Descrierea trebuie să aibă între 3 și 300 de caractere.")
        return v


class ReviewIn(BaseModel):
    decision: str
    note: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        if v not in ("confirm", "dispute"):
            raise ValueError("Decizie invalidă.")
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


def compute_totals(items: list[dict]) -> list[dict]:
    """Totaluri pe (membru, tip, unitate). O contribuție corectată (corects_id) nu se mai numără,
    cât timp corecția nu a fost contestată."""
    corrected = {i["corrects_id"] for i in items if i.get("corrects_id") and i.get("status") != "disputed"}
    agg: dict = {}
    for i in items:
        if str(i["_id"]) in corrected or i.get("status") not in ("logged", "confirmed"):
            continue
        key = (i["member_user_id"], i["kind"], i["unit"])
        row = agg.setdefault(key, {
            "member_user_id": i["member_user_id"],
            "member_name": i.get("member_name", ""),
            "kind": i["kind"],
            "unit": i["unit"],
            "confirmed": 0.0,
            "pending": 0.0,
        })
        row["confirmed" if i["status"] == "confirmed" else "pending"] += i["amount"]
    rows = sorted(agg.values(), key=lambda r: (r["member_name"], r["kind"], r["unit"]))
    for r in rows:
        r["confirmed"] = round(r["confirmed"], 2)
        r["pending"] = round(r["pending"], 2)
    return rows


# ----------------------------------------------------------------- rute

@router.get("/projects/{project_id}/contributions")
async def list_contributions(project_id: str, member: Optional[str] = None, user: dict = Depends(get_current_user)):
    project, _, _ = await load_project(project_id, user)
    flt: dict = {"project_id": str(project["_id"])}
    if member:
        flt["member_user_id"] = member
    docs = await db.radacini_contributions.find(flt).to_list(5000)
    docs.sort(key=lambda c: (c.get("date") or "", c.get("created_at") or ""), reverse=True)
    corrected_by = {d["corrects_id"]: str(d["_id"]) for d in docs if d.get("corrects_id")}
    uid = str(user["id"])
    items = []
    for d in docs:
        item = serialize_doc(d)
        item["corrected_by_id"] = corrected_by.get(str(d["_id"]))
        item["can_review"] = d.get("status") == "logged" and uid in reviewer_ids(project, d["member_user_id"])
        items.append(item)
    return {"items": items, "totals": compute_totals(docs)}


@router.post("/projects/{project_id}/contributions")
async def create_contribution(project_id: str, body: ContributionIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "înregistrarea contribuției")
    uid = str(user["id"])
    project, access, _ = await load_project(project_id, user)
    need_member(access)
    ensure_active(project)
    pid = str(project["_id"])
    day = (body.date.isoformat() if body.date else today_str())
    if day > today_str():
        raise HTTPException(400, "Data contribuției nu poate fi în viitor.")
    unit = DEFAULT_UNITS[body.kind] if body.kind in FIXED_UNITS else (body.unit or DEFAULT_UNITS[body.kind])
    if body.activity_id:
        act = await db.radacini_activities.find_one({"_id": oid_or_404(body.activity_id)})
        if not act or act.get("project_id") != pid:
            raise HTTPException(400, "Activitatea aleasă nu aparține acestui proiect.")
    if body.corrects_id:
        old = await db.radacini_contributions.find_one({"_id": oid_or_404(body.corrects_id)})
        if not old or old.get("project_id") != pid:
            raise HTTPException(400, "Contribuția de corectat nu există în acest proiect.")
        if old["member_user_id"] != uid:
            raise HTTPException(403, "Poți corecta doar propriile contribuții.")
        if await db.radacini_contributions.find_one({"corrects_id": body.corrects_id, "status": {"$ne": "disputed"}}):
            raise HTTPException(409, "Contribuția a fost deja corectată.")
    name = next((m.get("name") for m in project["members"] if m["user_id"] == uid), None) or user.get("name") or ""
    doc = mark_demo({
        "project_id": pid,
        "member_user_id": uid,
        "member_name": name,
        "kind": body.kind,
        "amount": body.amount,
        "unit": unit,
        "description": body.description,
        "activity_id": body.activity_id,
        "date": day,
        "status": "logged",
        "corrects_id": body.corrects_id,
        "created_at": now_iso(),
    })
    await db.radacini_contributions.insert_one(doc)
    for rid in reviewer_ids(project, uid):
        await safe_notify(
            rid,
            "Contribuție de confirmat",
            f"{name or 'Un membru'} a înregistrat o contribuție în „{project['title']}”.",
            link=project_link(pid),
            type_="project",
        )
    await emit(
        "radacini.contribution_logged",
        actor=user,
        payload={"project_id": pid, "contribution_id": str(doc["_id"]), "kind": body.kind},
    )
    return {"contribution": serialize_doc(doc)}


@router.post("/contributions/{contribution_id}/review")
async def review_contribution(contribution_id: str, body: ReviewIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "evaluarea contribuției")
    uid = str(user["id"])
    doc = await db.radacini_contributions.find_one({"_id": oid_or_404(contribution_id)})
    if not doc:
        raise HTTPException(404, "Contribuția nu există.")
    project, access, _ = await load_project(doc["project_id"], user)
    need_member(access)
    ensure_active(project)
    if uid not in reviewer_ids(project, doc["member_user_id"]):
        raise HTTPException(
            403,
            "Contribuția o poate confirma un coordonator diferit de autor "
            "(sau proprietarul, dacă autorul este singurul coordonator).",
        )
    if body.decision == "dispute" and not body.note:
        raise HTTPException(400, "Nota este obligatorie când contești o contribuție.")
    if doc.get("status") != "logged":
        raise HTTPException(409, "Contribuția a fost deja evaluată.")
    status = "confirmed" if body.decision == "confirm" else "disputed"
    now = now_iso()
    changes = {"status": status, "reviewed_by": uid, "reviewed_at": now}
    if body.note:
        changes["review_note"] = body.note
    res = await db.radacini_contributions.update_one({"_id": doc["_id"], "status": "logged"}, {"$set": changes})
    if res.modified_count != 1:
        raise HTTPException(409, "Contribuția a fost deja evaluată.")
    await safe_notify(
        doc["member_user_id"],
        "Contribuție confirmată" if status == "confirmed" else "Contribuție contestată",
        (
            f"Contribuția ta din „{project['title']}” a fost confirmată."
            if status == "confirmed"
            else f"Contribuția ta din „{project['title']}” a fost contestată. Motiv: {body.note}"
        ),
        link=project_link(doc["project_id"]),
        type_="project",
    )
    await emit(
        "radacini.contribution_reviewed",
        actor=user,
        payload={"project_id": doc["project_id"], "contribution_id": contribution_id, "decision": body.decision},
    )
    return {"contribution": serialize_doc({**doc, **changes})}
