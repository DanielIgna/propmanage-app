"""Proiecte agricole Rădăcini: creare la semnarea acordului, membri, roluri, finalizare."""
import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify, today_bucharest
from .requests import _staff_can_read, get_parcel_doc

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

ROLES = ("coordinator", "participant")


def today_str() -> str:
    """Data de azi (AAAA-LL-ZZ) în Europe/Bucharest, ca în frontend."""
    return today_bucharest().isoformat()


def project_link(project_id) -> str:
    return f"/radacini/proiecte/{project_id}"


# ----------------------------------------------------------------- acces

def member_role(project: dict, user_id: str) -> Optional[str]:
    return next((m.get("role") for m in project.get("members", []) if m.get("user_id") == str(user_id)), None)


async def load_project(project_id: str, user: dict) -> tuple[dict, str, Optional[str]]:
    """(proiect, 'member'|'staff', rolul meu). 404 dacă userul nu are voie să-l vadă."""
    doc = await db.radacini_projects.find_one({"_id": oid_or_404(project_id)})
    if not doc:
        raise HTTPException(404, "Proiectul nu există.")
    role = member_role(doc, user["id"])
    if role:
        return doc, "member", role
    if await _staff_can_read(user, await get_parcel_doc(doc.get("parcel_id"))):
        return doc, "staff", None
    raise HTTPException(404, "Proiectul nu există.")


def need_member(access: str) -> None:
    if access != "member":
        raise HTTPException(403, "Doar membrii proiectului pot acționa.")


def need_coordinator(access: str, role: Optional[str]) -> None:
    need_member(access)
    if role != "coordinator":
        raise HTTPException(403, "Doar coordonatorii proiectului pot face această acțiune.")


def ensure_active(project: dict) -> None:
    if project.get("status") == "completed":
        raise HTTPException(409, "Proiectul este finalizat.")


def reviewer_ids(project: dict, author_id: str) -> list[str]:
    """Cine poate confirma contribuțiile unui autor: coordonatorii ≠ autor; dacă nu există
    (autorul e singurul coordonator), proprietarul."""
    members = project.get("members", [])
    coords = [m["user_id"] for m in members if m.get("role") == "coordinator" and m["user_id"] != author_id]
    if coords:
        return coords
    return [m["user_id"] for m in members if m.get("role") == "owner" and m["user_id"] != author_id]


async def cas_update(project: dict, fields: dict) -> None:
    """Actualizare condiționată pe `rev` (409 dacă proiectul s-a schimbat între timp)."""
    rev = project.get("rev", 0)
    res = await db.radacini_projects.update_one(
        {"_id": project["_id"], "rev": rev},
        {"$set": {**fields, "rev": rev + 1, "updated_at": now_iso()}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Proiectul a fost modificat între timp. Reîncarcă pagina.")


async def release_parcel(parcel_id, agreement_id: str, status: str = "paused") -> bool:
    """Eliberează terenul legat de un acord: scoate `active_agreement_id` (doar dacă încă e al acordului dat)
    și setează `status` (implicit `paused`: proprietarul îl poate edita, relua sau șterge). True dacă s-a schimbat."""
    if not (isinstance(parcel_id, str) and len(parcel_id) == 24 and ObjectId.is_valid(parcel_id)):
        return False
    res = await db.radacini_parcels.update_one(
        {"_id": ObjectId(parcel_id), "active_agreement_id": str(agreement_id)},
        {"$unset": {"active_agreement_id": ""}, "$set": {"status": status, "updated_at": now_iso()}},
    )
    return res.modified_count == 1


async def agreement_party_ids(project: dict) -> set:
    """Utilizatorii-părți ai acordului din care provine proiectul (proprietar + cultivator)."""
    aid = project.get("agreement_id")
    if not (isinstance(aid, str) and len(aid) == 24 and ObjectId.is_valid(aid)):
        return set()
    ag = await db.radacini_agreements.find_one({"_id": ObjectId(aid)}, {"party_ids": 1})
    return {str(u) for u in (ag or {}).get("party_ids", [])}


# ----------------------------------------------------------------- creare din acord

async def create_project_for_agreement(agreement: dict, actor: Optional[dict] = None) -> Optional[dict]:
    """Creează proiectul unui acord semnat. Idempotent și sigur la concurență (upsert pe `agreement_id`,
    serializat de pgmongo cu un lock advisory); erorile se loghează, nu se propagă."""
    try:
        agreement_id = str(agreement["_id"])
        terms = agreement.get("terms") or {}
        snap = terms.get("parcel_snapshot") or {}
        now = now_iso()
        members = []
        for p in agreement.get("parties", []):
            members.append({
                "user_id": p["user_id"],
                "name": p.get("name", ""),
                "role": "owner" if p.get("role") == "owner" else "coordinator",
                "joined_at": now,
            })
        project = mark_demo({
            "agreement_id": agreement_id,
            "parcel_id": agreement.get("parcel_id"),
            "title": snap.get("title") or "Proiect agricol",
            "locality": snap.get("locality") or "",
            "area_m2": terms.get("area_m2") or snap.get("area_m2"),
            "start_date": terms.get("start_date"),
            "end_date": terms.get("end_date"),
            "members": members,
            "member_ids": [m["user_id"] for m in members],
            "status": "active",
            "rev": 0,
            "created_at": now,
            "updated_at": now,
        })
        res = await db.radacini_projects.update_one(
            {"agreement_id": agreement_id}, {"$setOnInsert": project}, upsert=True
        )
        if res.upserted_id is None:  # există deja (creat de o cerere concurentă sau de un apel anterior)
            return await db.radacini_projects.find_one({"agreement_id": agreement_id})
        project["_id"] = res.upserted_id
        for m in members:
            await safe_notify(
                m["user_id"],
                "Proiect agricol creat",
                f"Proiectul „{project['title']}” a fost creat din acordul semnat.",
                link=project_link(project["_id"]),
                type_="project",
            )
        await emit(
            "radacini.project_created",
            actor=actor or {},
            payload={"project_id": str(project["_id"]), "agreement_id": agreement_id, "parcel_id": project["parcel_id"]},
        )
        return project
    except Exception:  # noqa: BLE001
        log.exception("radacini: proiectul nu a putut fi creat pentru acordul %s", agreement.get("_id"))
        return None


# ----------------------------------------------------------------- scheme

class InviteIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or len(v) > 254:
            raise ValueError("Email invalid.")
        return v


class RoleIn(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def _role(cls, v: str) -> str:
        if v not in ROLES:
            raise ValueError("Rol invalid. Alege coordonator sau participant.")
        return v


def _view(project: dict, role: Optional[str], access: str) -> dict:
    out = serialize_doc(project)
    out.pop("rev", None)
    out["role"] = role
    out["access"] = access
    return out


# ----------------------------------------------------------------- rute

@router.get("/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    # Completare: acordurile semnate înainte de S3 (sau a căror creare de proiect a eșuat) primesc proiectul acum.
    # Se încarcă doar ID-urile; documentele complete doar pentru acordurile fără proiect (rar).
    signed_ids = [
        str(a["_id"])
        for a in await db.radacini_agreements.find({"party_ids": uid, "status": "signed"}, {"_id": 1}).to_list(200)
    ]
    if signed_ids:
        have = {
            p["agreement_id"]
            for p in await db.radacini_projects.find(
                {"agreement_id": {"$in": signed_ids}}, {"agreement_id": 1}
            ).to_list(200)
        }
        for aid in signed_ids:
            if aid not in have:
                agreement = await db.radacini_agreements.find_one({"_id": ObjectId(aid)})
                if agreement:
                    await create_project_for_agreement(agreement, user)
    docs = await db.radacini_projects.find({"member_ids": uid}).sort("updated_at", -1).to_list(200)
    docs = [d for d in docs if member_role(d, uid)]
    ids = [str(d["_id"]) for d in docs]
    crops: dict = {}
    upcoming: dict = {}
    pending: dict = {}
    to_review: dict = {}
    if ids:
        today = today_str()
        for c in await db.radacini_crop_plans.find({"project_id": {"$in": ids}}, {"project_id": 1}).to_list(5000):
            crops[c["project_id"]] = crops.get(c["project_id"], 0) + 1
        acts = await db.radacini_activities.find(
            {"project_id": {"$in": ids}, "status": "scheduled"}, {"project_id": 1, "date": 1}
        ).to_list(5000)
        for a in acts:
            if (a.get("date") or "") >= today:
                upcoming[a["project_id"]] = upcoming.get(a["project_id"], 0) + 1
        by_id = {str(d["_id"]): d for d in docs}
        contribs = await db.radacini_contributions.find(
            {"project_id": {"$in": ids}, "status": "logged"}, {"project_id": 1, "member_user_id": 1}
        ).to_list(5000)
        for c in contribs:
            pid = c["project_id"]
            pending[pid] = pending.get(pid, 0) + 1
            if uid in reviewer_ids(by_id[pid], c["member_user_id"]):
                to_review[pid] = to_review.get(pid, 0) + 1
    items = []
    for d in docs:
        pid = str(d["_id"])
        item = _view(d, member_role(d, uid), "member")
        item["counts"] = {
            "crop_plans": crops.get(pid, 0),
            "upcoming_activities": upcoming.get(pid, 0),
            "pending_contributions": pending.get(pid, 0),
            "contributions_to_review": to_review.get(pid, 0),
        }
        items.append(item)
    return {"items": items}


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    doc, access, role = await load_project(project_id, user)
    return {"project": _view(doc, role, access)}


@router.post("/projects/{project_id}/members")
async def add_member(project_id: str, body: InviteIn, user: dict = Depends(get_current_user)):
    doc, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(doc)
    target = await db.users.find_one({"email": body.email})
    if not target:
        raise HTTPException(404, "Nu există un cont PropManage cu acest email.")
    tid = str(target["_id"])
    if member_role(doc, tid):
        raise HTTPException(409, "Utilizatorul este deja membru al proiectului.")
    now = now_iso()
    # Nu stocăm emailul ca nume (ar apărea în proiect pentru toți membrii).
    member = {"user_id": tid, "name": target.get("name") or "Membru", "role": "participant", "joined_at": now}
    await cas_update(doc, {"members": [*doc["members"], member], "member_ids": [*doc["member_ids"], tid]})
    await safe_notify(
        tid,
        "Ai fost adăugat într-un proiect",
        f"{user.get('name') or 'Un coordonator'} te-a adăugat în proiectul „{doc['title']}”.",
        link=project_link(doc["_id"]),
        type_="project",
    )
    await emit(
        "radacini.project_member_added",
        actor=user,
        payload={"project_id": str(doc["_id"]), "member_user_id": tid},
    )
    fresh = await db.radacini_projects.find_one({"_id": doc["_id"]}) or doc
    return {"project": _view(fresh, role, access)}


@router.patch("/projects/{project_id}/members/{member_user_id}")
async def change_member_role(project_id: str, member_user_id: str, body: RoleIn, user: dict = Depends(get_current_user)):
    doc, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    ensure_active(doc)
    current = member_role(doc, member_user_id)
    if not current:
        raise HTTPException(404, "Membrul nu există în proiect.")
    if current == "owner":
        raise HTTPException(409, "Rolul proprietarului nu se schimbă.")
    if current == body.role:
        return {"project": _view(doc, role, access)}
    members = [{**m, "role": body.role} if m["user_id"] == member_user_id else m for m in doc["members"]]
    if not any(m["role"] == "coordinator" for m in members):
        raise HTTPException(409, "Proiectul trebuie să aibă cel puțin un coordonator.")
    await cas_update(doc, {"members": members})
    await safe_notify(
        member_user_id,
        "Rolul tău în proiect s-a schimbat",
        f"Ești acum {'coordonator' if body.role == 'coordinator' else 'participant'} în „{doc['title']}”.",
        link=project_link(doc["_id"]),
        type_="project",
    )
    await emit(
        "radacini.project_member_role_changed",
        actor=user,
        payload={"project_id": str(doc["_id"]), "member_user_id": member_user_id, "role": body.role},
    )
    fresh = await db.radacini_projects.find_one({"_id": doc["_id"]}) or doc
    return {"project": _view(fresh, member_role(fresh, user["id"]), access)}


@router.delete("/projects/{project_id}/members/{member_user_id}")
async def remove_member(project_id: str, member_user_id: str, user: dict = Depends(get_current_user)):
    doc, access, role = await load_project(project_id, user)
    need_member(access)
    is_self = member_user_id == str(user["id"])
    if not is_self and role != "coordinator":
        raise HTTPException(403, "Doar coordonatorii pot elimina alți membri.")
    ensure_active(doc)
    current = member_role(doc, member_user_id)
    if not current:
        raise HTTPException(404, "Membrul nu există în proiect.")
    if current == "owner":
        raise HTTPException(409, "Proprietarul nu poate fi eliminat din proiect.")
    if member_user_id in await agreement_party_ids(doc):
        raise HTTPException(409, "Părțile acordului nu pot fi eliminate din proiect.")
    members = [m for m in doc["members"] if m["user_id"] != member_user_id]
    if not any(m["role"] == "coordinator" for m in members):
        raise HTTPException(409, "Nu poți elimina ultimul coordonator.")
    await cas_update(doc, {"members": members, "member_ids": [m["user_id"] for m in members]})
    # Îl scoatem din activitățile programate la care era înscris.
    pid = str(doc["_id"])
    acts = await db.radacini_activities.find({"project_id": pid, "status": "scheduled"}).to_list(1000)
    for a in acts:
        if member_user_id in (a.get("participants") or []):
            await db.radacini_activities.update_one(
                {"_id": a["_id"], "rev": a.get("rev", 0)},
                {"$set": {
                    "participants": [p for p in a["participants"] if p != member_user_id],
                    "rev": a.get("rev", 0) + 1,
                    "updated_at": now_iso(),
                }},
            )
    if not is_self:
        await safe_notify(
            member_user_id,
            "Ai fost eliminat dintr-un proiect",
            f"Nu mai ești membru în „{doc['title']}”.",
            link="/radacini/proiecte",
            type_="project",
        )
    await emit(
        "radacini.project_member_removed",
        actor=user,
        payload={"project_id": pid, "member_user_id": member_user_id, "self": is_self},
    )
    return {"ok": True}


@router.post("/projects/{project_id}/complete")
async def complete_project(project_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "finalizarea proiectului")
    doc, access, role = await load_project(project_id, user)
    need_coordinator(access, role)
    if doc.get("status") != "active":
        raise HTTPException(409, "Proiectul este deja finalizat.")
    if await db.radacini_harvests.find_one({"project_id": str(doc["_id"]), "status": "recorded"}, {"_id": 1}):
        raise HTTPException(409, "Există recolte neconfirmate.")
    now = now_iso()
    res = await db.radacini_projects.update_one(
        {"_id": doc["_id"], "status": "active"},
        {"$set": {"status": "completed", "completed_at": now, "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Proiectul este deja finalizat.")
    # Terenul revine proprietarului (suspendat: îl poate edita, relua sau șterge). Dacă eșuează, deblocarea
    # leneșă din parcels.py o va face la următoarea acțiune a proprietarului.
    try:
        await release_parcel(doc.get("parcel_id"), doc.get("agreement_id"))
    except Exception:  # noqa: BLE001
        log.exception("radacini: terenul nu a putut fi eliberat la finalizarea proiectului %s", doc["_id"])
    for m in doc["members"]:
        if m["user_id"] != str(user["id"]):
            await safe_notify(
                m["user_id"],
                "Proiect finalizat",
                f"Proiectul „{doc['title']}” a fost marcat ca finalizat.",
                link=project_link(doc["_id"]),
                type_="project",
            )
    await emit("radacini.project_completed", actor=user, payload={"project_id": str(doc["_id"])})
    fresh = await db.radacini_projects.find_one({"_id": doc["_id"]}) or doc
    return {"project": _view(fresh, role, access)}
