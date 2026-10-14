"""Gospodării și consimțământ (S6-B): cont familial, copii fără cont, adulți invitați.

Colecții: `radacini_households`, `radacini_consents`. Un utilizator e titular al cel mult unei gospodării
(upsert pe `owner_user_id`). Minorii: doar prenume + an de naștere, cu consimțământ parental înregistrat
(IP + user agent). Modificările gospodăriei sunt condiționate pe `rev` (409 la conflict).
"""
import ipaddress
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify

router = APIRouter(route_class=RadaciniRoute)

CONSENT_VERSION = "2026-10"
MAX_MEMBERS = 20


def _first_name(name: Optional[str]) -> str:
    parts = (name or "").split()
    return parts[0] if parts else "Membru"


def _consent_ip(request: Request) -> str:
    """Primul IP valid din X-Forwarded-For, altfel adresa conexiunii."""
    for part in request.headers.get("x-forwarded-for", "").split(","):
        part = part.strip()
        try:
            return str(ipaddress.ip_address(part))
        except ValueError:
            continue
    return request.client.host if request.client else "?"


class HouseholdIn(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _n(cls, v):
        v = (v or "").strip()
        if not (2 <= len(v) <= 60):
            raise ValueError("Numele gospodăriei are între 2 și 60 de caractere.")
        return v


class MemberIn(BaseModel):
    relation: str
    email: Optional[str] = None  # adult cu cont existent
    first_name: Optional[str] = None  # minor
    birth_year: Optional[int] = None
    parental_consent: bool = False

    @field_validator("relation")
    @classmethod
    def _r(cls, v):
        v = (v or "").strip()
        if not (1 <= len(v) <= 40):
            raise ValueError("Relația are între 1 și 40 de caractere.")
        return v


def _view(doc: dict, uid: str) -> dict:
    out = serialize_doc(doc)
    for k in ("rev", "is_demo", "member_ids", "invited_user_ids"):
        out.pop(k, None)
    out["is_owner"] = doc.get("owner_user_id") == uid
    return out


async def _cas(doc: dict, fields: dict) -> None:
    rev = doc.get("rev", 0)
    res = await db.radacini_households.update_one(
        {"_id": doc["_id"], "rev": rev}, {"$set": {**fields, "rev": rev + 1, "updated_at": now_iso()}})
    if res.modified_count != 1:
        raise HTTPException(409, "Gospodăria a fost modificată între timp. Reîncarcă pagina.")


async def _load(household_id: str) -> dict:
    doc = await db.radacini_households.find_one({"_id": oid_or_404(household_id)})
    if not doc:
        raise HTTPException(404, "Gospodăria nu există.")
    return doc


@router.get("/households/mine")
async def my_household(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    docs = await db.radacini_households.find({"owner_user_id": uid}).limit(1).to_list(1)
    if not docs:
        docs = await db.radacini_households.find({"member_ids": uid}).limit(1).to_list(1)
    invites = await db.radacini_households.find({"invited_user_ids": uid}).limit(20).to_list(20)
    owners = {}
    for d in invites:
        oid = d.get("owner_user_id") or ""
        o = await db.users.find_one({"_id": ObjectId(oid)}, {"name": 1}) if ObjectId.is_valid(oid) else None
        owners[str(d["_id"])] = _first_name((o or {}).get("name"))
    return {
        "household": _view(docs[0], uid) if docs else None,
        "invitations": [{"household_id": str(d["_id"]), "name": d.get("name"), "invited_by": owners.get(str(d["_id"]))}
                        for d in invites],
    }


@router.post("/households")
async def create_household(body: HouseholdIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    now = now_iso()
    doc = mark_demo({
        "name": body.name, "owner_user_id": uid,
        "members": [{"user_id": uid, "name": _first_name(user.get("name")), "relation": "titular",
                     "is_minor": False, "status": "active"}],
        "member_ids": [uid], "invited_user_ids": [], "rev": 0, "created_at": now, "updated_at": now,
    })
    res = await db.radacini_households.update_one({"owner_user_id": uid}, {"$setOnInsert": doc}, upsert=True)
    if res.upserted_id is None:
        raise HTTPException(409, "Ai deja o gospodărie.")
    doc["_id"] = res.upserted_id
    await emit("radacini.household_created", actor=user, payload={"household_id": str(res.upserted_id)})
    return {"household": _view(doc, uid)}


@router.post("/households/{household_id}/members")
async def add_member(household_id: str, body: MemberIn, request: Request, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    is_minor = not (body.email and body.email.strip())
    if is_minor:
        block_in_impersonation(user, "consimțământul parental")
    doc = await _load(household_id)
    if doc.get("owner_user_id") != uid:
        raise HTTPException(403, "Doar titularul poate adăuga membri.")
    members = list(doc.get("members") or [])
    if len(members) >= MAX_MEMBERS:
        raise HTTPException(409, f"O gospodărie are cel mult {MAX_MEMBERS} membri.")

    if is_minor:
        name = (body.first_name or "").strip()
        if not (1 <= len(name) <= 40) or len(name.split()) != 1:
            raise HTTPException(400, "Pentru un minor se completează doar prenumele (1–40 de caractere).")
        year = datetime.now(timezone.utc).year
        if body.birth_year is None or not (1900 <= body.birth_year <= year):
            raise HTTPException(400, f"Anul nașterii trebuie să fie între 1900 și {year}.")
        if body.parental_consent is not True:
            raise HTTPException(400, "Este necesar consimțământul parental pentru datele minorului.")
        entry = {"name": name, "relation": body.relation, "is_minor": True, "birth_year": body.birth_year}
        consent = mark_demo({
            "user_id": uid, "kind": "minor_data", "subject_name": name, "version": CONSENT_VERSION,
            "at": now_iso(), "ip": _consent_ip(request),
            "user_agent": (request.headers.get("user-agent") or "")[:300], "household_id": household_id,
        })
        cres = await db.radacini_consents.insert_one(consent)
        try:
            await _cas(doc, {"members": [*members, entry]})
        except Exception:
            await db.radacini_consents.delete_one({"_id": cres.inserted_id})
            raise
        await emit("radacini.household_minor_added", actor=user, payload={"household_id": household_id})
    else:
        email = body.email.strip().lower()
        target = await db.users.find_one({"email": email}, {"name": 1})
        if not target:
            raise HTTPException(404, "Nu există un cont cu acest email.")
        tid = str(target["_id"])
        if tid == uid:
            raise HTTPException(400, "Ești deja în gospodărie.")
        if any(m.get("user_id") == tid for m in members):
            raise HTTPException(409, "Persoana este deja în gospodărie sau are o invitație în așteptare.")
        entry = {"user_id": tid, "name": _first_name(target.get("name")), "relation": body.relation,
                 "is_minor": False, "status": "pending", "invited_at": now_iso()}
        await _cas(doc, {"members": [*members, entry], "invited_user_ids": [*(doc.get("invited_user_ids") or []), tid]})
        await safe_notify(tid, "Invitație într-o gospodărie",
                          f"{_first_name(user.get('name'))} te-a invitat în gospodăria „{doc['name']}”.",
                          link="/radacini/gospodaria", type_="household")
        await emit("radacini.household_invited", actor=user, payload={"household_id": household_id, "user_id": tid})
    fresh = await db.radacini_households.find_one({"_id": doc["_id"]}) or doc
    return {"household": _view(fresh, uid)}


@router.post("/households/{household_id}/accept")
async def accept_invitation(household_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    doc = await _load(household_id)
    members = list(doc.get("members") or [])
    idx = next((i for i, m in enumerate(members) if m.get("user_id") == uid and m.get("status") == "pending"), None)
    if idx is None:
        raise HTTPException(404, "Nu ai o invitație în această gospodărie.")
    members[idx] = {**members[idx], "status": "active", "accepted_at": now_iso()}
    await _cas(doc, {
        "members": members,
        "member_ids": [*(doc.get("member_ids") or []), uid],
        "invited_user_ids": [x for x in (doc.get("invited_user_ids") or []) if x != uid],
    })
    await safe_notify(doc["owner_user_id"], "Invitație acceptată",
                      f"{_first_name(user.get('name'))} a intrat în gospodăria „{doc['name']}”.",
                      link="/radacini/gospodaria", type_="household")
    await emit("radacini.household_accepted", actor=user, payload={"household_id": household_id})
    fresh = await db.radacini_households.find_one({"_id": doc["_id"]}) or doc
    return {"household": _view(fresh, uid)}


@router.delete("/households/{household_id}/members/{ref}")
async def remove_member(household_id: str, ref: str, user: dict = Depends(get_current_user)):
    """`ref` = index numeric în `members` sau `user_id`. Titularul scoate pe oricine (nu pe el însuși);
    un adult invitat/membru se poate scoate pe sine (refuz/ieșire)."""
    uid = str(user["id"])
    doc = await _load(household_id)
    members = list(doc.get("members") or [])
    if ref.isdigit() and len(ref) < 4:
        idx = int(ref)
        idx = idx if idx < len(members) else None
    else:
        idx = next((i for i, m in enumerate(members) if m.get("user_id") == ref), None)
    if idx is None:
        raise HTTPException(404, "Membrul nu există.")
    target = members[idx]
    is_owner = doc.get("owner_user_id") == uid
    if target.get("user_id") == doc.get("owner_user_id"):
        raise HTTPException(409, "Titularul nu poate fi scos. Șterge gospodăria.")
    if not is_owner and target.get("user_id") != uid:
        raise HTTPException(403, "Nu poți scoate acest membru.")
    tid = target.get("user_id")
    fields = {"members": [m for i, m in enumerate(members) if i != idx]}
    if tid:
        fields["member_ids"] = [x for x in (doc.get("member_ids") or []) if x != tid]
        fields["invited_user_ids"] = [x for x in (doc.get("invited_user_ids") or []) if x != tid]
    await _cas(doc, fields)
    await emit("radacini.household_member_removed", actor=user, payload={"household_id": household_id})
    fresh = await db.radacini_households.find_one({"_id": doc["_id"]}) or doc
    return {"household": _view(fresh, uid)}


@router.delete("/households/{household_id}")
async def delete_household(household_id: str, user: dict = Depends(get_current_user)):
    """Doar titularul. Înregistrările de consimțământ se păstrează ca dovadă."""
    doc = await _load(household_id)
    if doc.get("owner_user_id") != str(user["id"]):
        raise HTTPException(403, "Doar titularul poate șterge gospodăria.")
    await db.radacini_households.delete_one({"_id": doc["_id"]})
    await emit("radacini.household_deleted", actor=user, payload={"household_id": household_id})
    return {"ok": True}
