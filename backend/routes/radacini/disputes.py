"""Dispute și mediere Rădăcini: părțile unui obiect (contribuție, rezervare, recoltă, acord) deschid o dispută,
personalul (operator pe arie sau manager) o preia și o închide cu o rezoluție motivată."""
import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, audit_staff, load_owners, mark_demo, now_iso, oid_or_404, safe_notify
from .projects import reviewer_ids
from .staff import get_staff, require_staff

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

SCOPE_TYPES = ("contribution", "reservation", "harvest", "agreement")
ACTIVE = ("open", "in_mediation")
MAX_MESSAGES = 200
DISPUTES_LINK = "/radacini/dispute"


class DisputeIn(BaseModel):
    scope_type: str
    scope_id: str
    reason: str

    @field_validator("scope_type")
    @classmethod
    def _scope(cls, v: str) -> str:
        if v not in SCOPE_TYPES:
            raise ValueError("Tip de obiect necunoscut pentru dispută.")
        return v

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        v = v.strip()
        if not 10 <= len(v) <= 1000:
            raise ValueError("Motivul trebuie să aibă între 10 și 1000 de caractere.")
        return v


class MessageIn(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 1000:
            raise ValueError("Mesajul trebuie să aibă între 1 și 1000 de caractere.")
        return v


class ResolveIn(BaseModel):
    decision: str
    note: str

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        if v not in ("resolved", "rejected"):
            raise ValueError("Decizie invalidă. Alege resolved sau rejected.")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: str) -> str:
        v = v.strip()
        if not 3 <= len(v) <= 1000:
            raise ValueError("Nota de rezoluție este obligatorie (3–1000 de caractere).")
        return v


# ----------------------------------------------------------------- rezolvarea părților

async def _by_id(coll, id_: Optional[str]) -> Optional[dict]:
    if not (isinstance(id_, str) and len(id_) == 24 and ObjectId.is_valid(id_)):
        return None
    return await coll.find_one({"_id": ObjectId(id_)})


def _other(party_ids: list[str], uid: str) -> Optional[str]:
    return next((p for p in party_ids if p != uid), None)


async def resolve_scope(scope_type: str, scope_id: str, uid: str) -> dict:
    """{party_ids, against, locality} pentru obiectul disputat. 404 dacă nu există; 403 dacă `uid` nu e parte."""
    parties: list[str] = []
    against: Optional[str] = None
    locality = ""
    if scope_type == "contribution":
        c = await _by_id(db.radacini_contributions, scope_id)
        if not c:
            raise HTTPException(404, "Contribuția nu există.")
        project = await _by_id(db.radacini_projects, c.get("project_id")) or {}
        author = c["member_user_id"]
        reviewers = [c["reviewed_by"]] if c.get("reviewed_by") else (reviewer_ids(project, author) if project else [])
        coords = [m["user_id"] for m in project.get("members", []) if m.get("role") == "coordinator"]
        parties = list(dict.fromkeys([author, *reviewers, *coords]))
        locality = project.get("locality") or ""
        against = (reviewers[0] if reviewers else None) if uid == author else author
    elif scope_type == "reservation":
        r = await _by_id(db.radacini_reservations, scope_id)
        if not r:
            raise HTTPException(404, "Rezervarea nu există.")
        parties = [r["buyer_user_id"], r["seller_user_id"]]
        listing = await _by_id(db.radacini_listings, r.get("listing_id")) or {}
        locality = listing.get("locality") or ""
    elif scope_type == "harvest":
        h = await _by_id(db.radacini_harvests, scope_id)
        if not h:
            raise HTTPException(404, "Recolta nu există.")
        project = await _by_id(db.radacini_projects, h.get("project_id")) or {}
        owners = [m["user_id"] for m in project.get("members", []) if m.get("role") == "owner"]
        coords = [m["user_id"] for m in project.get("members", []) if m.get("role") == "coordinator"]
        parties = owners + coords
        locality = project.get("locality") or ""
        if uid in owners:
            against = coords[0] if coords else None
        else:
            against = owners[0] if owners else None
    else:  # agreement
        a = await _by_id(db.radacini_agreements, scope_id)
        if not a:
            raise HTTPException(404, "Acordul nu există.")
        parties = [str(p) for p in a.get("party_ids") or []]
        parcel = await _by_id(db.radacini_parcels, a.get("parcel_id")) or {}
        locality = parcel.get("locality") or (a.get("terms") or {}).get("parcel_snapshot", {}).get("locality") or ""
    if uid not in parties:
        raise HTTPException(403, "Doar părțile obiectului pot deschide o dispută.")
    if scope_type in ("reservation", "agreement"):
        against = _other(parties, uid)
    if not against or against == uid:
        against = _other(parties, uid)
    if not against:
        raise HTTPException(409, "Nu există o a doua parte pentru această dispută.")
    return {"party_ids": [uid, against], "against": against, "locality": locality}


# ----------------------------------------------------------------- acces și vederi

def _is_party(doc: dict, uid: str) -> bool:
    return uid in (doc.get("party_ids") or [])


def _staff_in_area(staff: dict, doc: dict) -> bool:
    return staff["role"] == "manager" or not staff["areas"] or doc.get("locality") in staff["areas"]


async def _view(doc: dict) -> dict:
    out = serialize_doc(doc)
    names = await load_owners([doc.get("opened_by"), doc.get("against_user_id"), doc.get("mediator_user_id")])
    out["opened_by_name"] = names.get(doc.get("opened_by"), {}).get("name", "")
    out["against_name"] = names.get(doc.get("against_user_id"), {}).get("name", "")
    out["mediator_name"] = names.get(doc.get("mediator_user_id"), {}).get("name", "")
    return out


async def _load_dispute(dispute_id: str) -> dict:
    doc = await db.radacini_disputes.find_one({"_id": oid_or_404(dispute_id)})
    if not doc:
        raise HTTPException(404, "Disputa nu există.")
    return doc


def _notify_targets(doc: dict, exclude: str) -> list[str]:
    ids = list(doc.get("party_ids") or [])
    if doc.get("mediator_user_id"):
        ids.append(doc["mediator_user_id"])
    return [i for i in dict.fromkeys(ids) if i != exclude]


# ----------------------------------------------------------------- rute

@router.post("/disputes")
async def open_dispute(body: DisputeIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "deschiderea unei dispute")
    uid = str(user["id"])
    scope_id = body.scope_id.strip()
    info = await resolve_scope(body.scope_type, scope_id, uid)
    now = now_iso()
    doc = mark_demo({
        "scope_type": body.scope_type,
        "scope_id": scope_id,
        "opened_by": uid,
        "against_user_id": info["against"],
        "party_ids": info["party_ids"],
        "reason": body.reason,
        "status": "open",
        "messages": [],
        "locality": info["locality"],
        "created_at": now,
        "updated_at": now,
    })
    # O singură dispută deschisă pe obiect: upsert serializat de pgmongo (a doua cerere simultană → 409).
    ins = await db.radacini_disputes.update_one(
        {"scope_type": body.scope_type, "scope_id": scope_id, "status": {"$in": list(ACTIVE)}},
        {"$setOnInsert": doc},
        upsert=True,
    )
    if ins.upserted_id is None:
        raise HTTPException(409, "Există deja o dispută deschisă pentru acest obiect.")
    doc["_id"] = ins.upserted_id
    await safe_notify(
        info["against"],
        "Dispută deschisă",
        f"{user.get('name') or 'Un membru'} a deschis o dispută: {body.reason}",
        link=DISPUTES_LINK,
        type_="dispute",
    )
    await emit(
        "radacini.dispute_opened",
        actor=user,
        payload={"dispute_id": str(doc["_id"]), "scope_type": body.scope_type, "scope_id": scope_id},
    )
    return {"dispute": await _view(doc)}


@router.get("/disputes/mine")
async def my_disputes(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    docs = await db.radacini_disputes.find(
        {"$or": [{"party_ids": uid}, {"mediator_user_id": uid}]}
    ).sort("created_at", -1).limit(200).to_list(200)
    return {"items": [serialize_doc(d) for d in docs]}


@router.get("/staff/disputes")
async def staff_disputes(
    status: Optional[str] = Query(None),
    staff: dict = Depends(require_staff("operator", "manager")),
):
    if status is not None and status not in ("open", "in_mediation", "resolved", "rejected", "active"):
        raise HTTPException(400, "Stare necunoscută.")
    flt: dict = {}
    if status in (None, "active"):
        flt["status"] = {"$in": list(ACTIVE)}
    else:
        flt["status"] = status
    if staff["role"] == "operator" and staff["areas"]:
        flt["locality"] = {"$in": list(staff["areas"])}
    docs = await db.radacini_disputes.find(flt).sort("created_at", 1).limit(200).to_list(200)
    return {"items": [await _view(d) for d in docs]}


@router.get("/disputes/{dispute_id}")
async def get_dispute(dispute_id: str, user: dict = Depends(get_current_user)):
    doc = await _load_dispute(dispute_id)
    uid = str(user["id"])
    if not (_is_party(doc, uid) or doc.get("mediator_user_id") == uid):
        staff = await get_staff(user)
        if not (staff and _staff_in_area(staff, doc)):
            raise HTTPException(404, "Disputa nu există.")
    return {"dispute": await _view(doc)}


@router.post("/disputes/{dispute_id}/messages")
async def add_message(dispute_id: str, body: MessageIn, user: dict = Depends(get_current_user)):
    doc = await _load_dispute(dispute_id)
    uid = str(user["id"])
    if not (_is_party(doc, uid) or doc.get("mediator_user_id") == uid):
        raise HTTPException(404, "Disputa nu există.")
    if doc.get("status") not in ACTIVE:
        raise HTTPException(409, "Disputa este închisă.")
    if len(doc.get("messages") or []) >= MAX_MESSAGES:
        raise HTTPException(409, "S-a atins numărul maxim de mesaje.")
    msg = {"user_id": uid, "name": user.get("name") or "", "text": body.text, "at": now_iso()}
    res = await db.radacini_disputes.update_one(
        {"_id": doc["_id"], "status": {"$in": list(ACTIVE)}},
        {"$push": {"messages": msg}, "$set": {"updated_at": msg["at"]}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Disputa este închisă.")
    for target in _notify_targets(doc, uid):
        await safe_notify(
            target, "Mesaj nou în dispută", f"{msg['name'] or 'Un participant'}: {body.text}",
            link=DISPUTES_LINK, type_="dispute",
        )
    await emit("radacini.dispute_message", actor=user, payload={"dispute_id": dispute_id})
    return {"message": msg}


@router.post("/disputes/{dispute_id}/take")
async def take_dispute(dispute_id: str, staff: dict = Depends(require_staff("operator", "manager"))):
    user = staff["user"]
    uid = str(user["id"])
    doc = await _load_dispute(dispute_id)
    if not _staff_in_area(staff, doc):
        raise HTTPException(403, "Disputa nu este în zona ta de lucru.")
    if _is_party(doc, uid):
        raise HTTPException(403, "Nu poți media o dispută în care ești parte.")
    now = now_iso()
    res = await db.radacini_disputes.update_one(
        {"_id": doc["_id"], "status": "open"},
        {"$set": {"status": "in_mediation", "mediator_user_id": uid, "taken_at": now, "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Disputa a fost deja preluată sau închisă.")
    doc = {**doc, "status": "in_mediation", "mediator_user_id": uid, "taken_at": now, "updated_at": now}
    await audit_staff(user, "dispute.take", "radacini_dispute", doc["_id"], {
        "scope_type": doc.get("scope_type"), "scope_id": doc.get("scope_id"),
        "locality": doc.get("locality"), "staff_role": staff["role"],
    })
    for target in doc.get("party_ids") or []:
        await safe_notify(
            target, "Dispută în mediere", "Un mediator Rădăcini a preluat disputa.",
            link=DISPUTES_LINK, type_="dispute",
        )
    await emit("radacini.dispute_taken", actor=user, payload={"dispute_id": dispute_id})
    return {"dispute": await _view(doc)}


@router.post("/disputes/{dispute_id}/resolve")
async def resolve_dispute(dispute_id: str, body: ResolveIn, staff: dict = Depends(require_staff("operator", "manager"))):
    user = staff["user"]
    block_in_impersonation(user, "închiderea unei dispute")
    uid = str(user["id"])
    doc = await _load_dispute(dispute_id)
    if not _staff_in_area(staff, doc):
        raise HTTPException(403, "Disputa nu este în zona ta de lucru.")
    if doc.get("status") != "in_mediation":
        raise HTTPException(409, "Disputa trebuie preluată înainte de a fi închisă." if doc.get("status") == "open"
                            else "Disputa este deja închisă.")
    if doc.get("mediator_user_id") != uid and staff["role"] != "manager":
        raise HTTPException(403, "Doar mediatorul sau un manager poate închide disputa.")
    now = now_iso()
    resolution = {"decision": body.decision, "note": body.note, "by": uid, "at": now}
    res = await db.radacini_disputes.update_one(
        {"_id": doc["_id"], "status": "in_mediation"},
        {"$set": {"status": body.decision, "resolution": resolution, "resolved_at": now, "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Disputa este deja închisă.")
    doc = {**doc, "status": body.decision, "resolution": resolution, "resolved_at": now, "updated_at": now}
    await audit_staff(user, "dispute.resolve", "radacini_dispute", doc["_id"], {
        "scope_type": doc.get("scope_type"), "scope_id": doc.get("scope_id"),
        "locality": doc.get("locality"), "decision": body.decision, "note": body.note,
    })
    title = "Dispută rezolvată" if body.decision == "resolved" else "Dispută respinsă"
    for target in doc.get("party_ids") or []:
        await safe_notify(target, title, f"Rezoluție: {body.note}", link=DISPUTES_LINK, type_="dispute")
    await emit("radacini.dispute_resolved", actor=user, payload={"dispute_id": dispute_id, "decision": body.decision})
    return {"dispute": await _view(doc)}
