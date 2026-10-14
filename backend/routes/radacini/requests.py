"""Cereri de teren Rădăcini: trimitere, negociere (mesaje + contrapropuneri) și acceptare."""
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import (
    RadaciniRoute,
    check_price,
    load_owners,
    mark_demo,
    now_iso,
    oid_or_404,
    safe_notify,
    today_bucharest,
)
from .constants import LEGAL_GATE_MESSAGE, LEGAL_NOTICE, OFFER_MODEL_IDS, REQUESTABLE_MODEL_IDS
from .members import get_member_doc
from .staff import get_staff

router = APIRouter(route_class=RadaciniRoute)

ACTIVE_STATUSES = ("sent", "viewed", "negotiating")
EXPIRY_DAYS = 30
MIN_AREA_M2 = 100
ASSIGNED_ELSEWHERE_REASON = "Terenul a fost atribuit altui solicitant."


# ----------------------------------------------------------------- validări

class ProposalIn(BaseModel):
    """O propunere completă (cerere nouă sau contrapropunere)."""

    area_m2: int
    start_date: date
    end_date: date
    price_ron_per_year: Optional[float] = None
    harvest_share_percent: Optional[int] = None
    crops: list[str] = []
    note: Optional[str] = None

    @field_validator("price_ron_per_year")
    @classmethod
    def _price(cls, v: Optional[float]) -> Optional[float]:
        return check_price(v)

    @field_validator("crops")
    @classmethod
    def _crops(cls, v: list[str]) -> list[str]:
        return clean_crops(v)

    @field_validator("note")
    @classmethod
    def _note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 1000:
            raise ValueError("Mesajul are cel mult 1000 de caractere.")
        return v or None


class RequestIn(ProposalIn):
    model: str

    @field_validator("model")
    @classmethod
    def _model(cls, v: str) -> str:
        if v not in OFFER_MODEL_IDS:
            raise ValueError("Model necunoscut.")
        return v


class MessageIn(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 2000:
            raise ValueError("Mesajul trebuie să aibă între 1 și 2000 de caractere.")
        return v


class ReasonIn(BaseModel):
    reason: Optional[str] = None

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Motivul are cel mult 500 de caractere.")
        return v or None


def clean_crops(v: list[str]) -> list[str]:
    crops = [c.strip() for c in v if c and c.strip()]
    if len(crops) > 20 or any(len(c) > 60 for c in crops):
        raise ValueError("Cel mult 20 de culturi, de maximum 60 de caractere fiecare.")
    return list(dict.fromkeys(crops))


def _as_date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def check_terms(t: dict, *, model: str, parcel_area: Optional[int], require_future_start: bool = True) -> None:
    """Validări contextuale comune propunerilor și termenilor acordului (400 la eroare)."""
    area = t.get("area_m2")
    if not isinstance(area, int) or area < MIN_AREA_M2:
        raise HTTPException(400, f"Suprafața trebuie să fie de cel puțin {MIN_AREA_M2} m².")
    if parcel_area and area > parcel_area:
        raise HTTPException(400, f"Suprafața nu poate depăși suprafața terenului ({parcel_area} m²).")
    start, end = _as_date(t["start_date"]), _as_date(t["end_date"])
    if require_future_start and start < today_bucharest():
        raise HTTPException(400, "Data de început nu poate fi în trecut.")
    if end <= start:
        raise HTTPException(400, "Data de final trebuie să fie după data de început.")
    share = t.get("harvest_share_percent")
    if model == "harvest_share":
        if share is None or not 1 <= share <= 90:
            raise HTTPException(400, "Procentul din recoltă trebuie să fie între 1 și 90.")
    elif model == "mixed":
        # Modelul mixt: preț și/sau procent din recoltă; procentul e opțional, dar dacă e dat, între 1 și 90.
        if share is not None and (isinstance(share, bool) or not isinstance(share, int) or not 1 <= share <= 90):
            raise HTTPException(400, "Procentul din recoltă trebuie să fie între 1 și 90.")
    elif share is not None:
        raise HTTPException(
            400, "Procentul din recoltă se completează doar la „Cultivare la parte din recoltă” sau „Model mixt”."
        )
    price = t.get("price_ron_per_year")
    if price is not None:
        if isinstance(price, bool) or not isinstance(price, (int, float)):
            raise HTTPException(400, "Prețul trebuie să fie un număr valid.")
        try:
            check_price(price)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None


# ----------------------------------------------------------------- helpers

def _parse_iso(value) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def refresh_expiry(doc: dict) -> dict:
    """Expirare leneșă: o cerere activă fără activitate de 30 de zile devine `expired` (salvat condiționat)."""
    if doc.get("status") not in ACTIVE_STATUSES:
        return doc
    last = _parse_iso(doc.get("last_activity_at") or doc.get("created_at"))
    if not last or datetime.now(timezone.utc) - last < timedelta(days=EXPIRY_DAYS):
        return doc
    now = now_iso()
    changes = {"status": "expired", "decided_at": now, "updated_at": now}
    res = await db.radacini_land_requests.update_one(
        {"_id": doc["_id"], "status": doc["status"]}, {"$set": changes}
    )
    if res.modified_count == 1:
        return {**doc, **changes}
    return await db.radacini_land_requests.find_one({"_id": doc["_id"]}) or doc


async def load_parcels(parcel_ids: Iterable[str]) -> dict:
    oids = {ObjectId(p) for p in parcel_ids if isinstance(p, str) and len(p) == 24 and ObjectId.is_valid(p)}
    if not oids:
        return {}
    docs = await db.radacini_parcels.find(
        {"_id": {"$in": list(oids)}}, {"title": 1, "locality": 1, "area_m2": 1, "status": 1, "owner_user_id": 1}
    ).to_list(len(oids))
    return {str(d["_id"]): d for d in docs}


async def get_parcel_doc(parcel_id: str) -> Optional[dict]:
    if not (isinstance(parcel_id, str) and len(parcel_id) == 24 and ObjectId.is_valid(parcel_id)):
        return None
    return await db.radacini_parcels.find_one({"_id": ObjectId(parcel_id)})


def _is_party(doc: dict, user: dict) -> bool:
    uid = str(user["id"])
    return uid in (str(doc.get("owner_user_id")), str(doc.get("requester_user_id")))


async def _staff_can_read(user: dict, parcel: Optional[dict]) -> bool:
    staff = await get_staff(user)
    if staff is None:
        return False
    if staff["role"] == "manager" or not staff["areas"]:
        return True
    return bool(parcel) and parcel.get("locality") in staff["areas"]


async def party_access(doc: dict, user: dict, parcel: Optional[dict] = None) -> str:
    """'party' pentru părți, 'staff' pentru citire de către personal; altfel 404 (nu dezvăluim existența)."""
    if _is_party(doc, user):
        return "party"
    if await _staff_can_read(user, parcel or await get_parcel_doc(doc.get("parcel_id"))):
        return "staff"
    raise HTTPException(404, "Cererea nu există.")


def _require_party(access: str) -> None:
    if access != "party":
        raise HTTPException(403, "Doar părțile pot acționa în această cerere.")


async def _load_request(request_id: str) -> dict:
    doc = await db.radacini_land_requests.find_one({"_id": oid_or_404(request_id)})
    if not doc:
        raise HTTPException(404, "Cererea nu există.")
    return await refresh_expiry(doc)


def _require_active(doc: dict) -> None:
    if doc.get("status") not in ACTIVE_STATUSES:
        raise HTTPException(409, "Cererea nu mai este activă.")


def _other_party(doc: dict, user: dict) -> str:
    uid = str(user["id"])
    return str(doc["requester_user_id"] if uid == str(doc["owner_user_id"]) else doc["owner_user_id"])


def _link(doc: dict) -> str:
    return f"/radacini/cereri/{doc['_id']}"


async def _enrich(docs: list[dict], viewer_id: str) -> list[dict]:
    """parcel_title, parcel_locality, counterpart_name — două interogări în lot, fără N+1."""
    parcels = await load_parcels(d.get("parcel_id") for d in docs)
    users = await load_owners(
        [d.get("owner_user_id") for d in docs] + [d.get("requester_user_id") for d in docs]
    )
    out = []
    for d in docs:
        item = serialize_doc(d)
        parcel = parcels.get(str(d.get("parcel_id")), {})
        owner_id, req_id = str(d.get("owner_user_id")), str(d.get("requester_user_id"))
        item["parcel_title"] = parcel.get("title", "")
        item["parcel_locality"] = parcel.get("locality", "")
        item["owner_name"] = users.get(owner_id, {}).get("name", "")
        item["requester_name"] = users.get(req_id, {}).get("name", "")
        item["counterpart_name"] = item["requester_name"] if viewer_id == owner_id else item["owner_name"]
        out.append(item)
    return out


def _proposal_dict(body: ProposalIn) -> dict:
    p = body.model_dump(mode="json", exclude={"model"})
    p["crops"] = p.get("crops") or []
    return p


async def _ensure_member(user: dict) -> dict:
    member = await get_member_doc(user["id"])
    if not member:
        raise HTTPException(400, "Completează profilul înainte de a trimite o cerere.")
    return member


# ----------------------------------------------------------------- rute

@router.post("/parcels/{parcel_id}/requests")
async def create_request(parcel_id: str, body: RequestIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "trimiterea cererii")
    # Poarta juridică: `sale` și `joint_project` se pot afișa în ofertă, dar nu se pot solicita (încă).
    if body.model not in REQUESTABLE_MODEL_IDS:
        raise HTTPException(409, LEGAL_GATE_MESSAGE)
    uid = str(user["id"])
    member = await _ensure_member(user)
    parcel = await db.radacini_parcels.find_one({"_id": oid_or_404(parcel_id)})
    if not parcel or parcel.get("archived_at"):
        raise HTTPException(404, "Terenul nu există.")
    if str(parcel.get("owner_user_id")) == uid:
        raise HTTPException(403, "Nu poți solicita propriul teren.")
    if parcel.get("status") != "published":
        raise HTTPException(409, "Terenul nu este disponibil pentru cereri.")
    if body.model not in (parcel.get("offer") or {}).get("models", []):
        raise HTTPException(400, "Modelul ales nu este oferit pentru acest teren.")
    proposal = _proposal_dict(body)
    check_terms(proposal, model=body.model, parcel_area=parcel.get("area_m2"))

    active_filter = {"parcel_id": parcel_id, "requester_user_id": uid, "status": {"$in": list(ACTIVE_STATUSES)}}
    # Cererile active expirate (30 de zile fără activitate) se închid mai întâi, ca să nu blocheze una nouă.
    for e in await db.radacini_land_requests.find(active_filter).to_list(20):
        if (await refresh_expiry(e)).get("status") in ACTIVE_STATUSES:
            raise HTTPException(409, "Ai deja o cerere activă pentru acest teren.")

    now = now_iso()
    doc = mark_demo({
        "parcel_id": parcel_id,
        "owner_user_id": str(parcel["owner_user_id"]),
        "requester_user_id": uid,
        "model": body.model,
        "proposal": proposal,
        "proposal_by_user_id": uid,
        "proposal_at": now,
        "proposals_history": [],
        "status": "sent",
        "last_activity_at": now,
        "created_at": now,
        "updated_at": now,
    })
    # Inserare ca upsert cu același filtru ca verificarea de mai sus: pgmongo serializează upsert-urile pe
    # colecție (lock advisory), deci două cereri simultane (același solicitant + teren) nu pot trece amândouă.
    res = await db.radacini_land_requests.update_one(active_filter, {"$setOnInsert": doc}, upsert=True)
    if res.upserted_id is None:
        raise HTTPException(409, "Ai deja o cerere activă pentru acest teren.")
    doc["_id"] = res.upserted_id
    if "grow" not in (member.get("interests") or []):
        await db.radacini_members.update_one(
            {"_id": member["_id"]}, {"$addToSet": {"interests": "grow"}, "$set": {"updated_at": now}}
        )
    await safe_notify(
        doc["owner_user_id"],
        "Cerere nouă pentru terenul tău",
        f"{user.get('name') or 'Un membru'} a solicitat „{parcel.get('title')}”.",
        link=_link(doc),
        type_="request",
    )
    await emit(
        "radacini.request_created",
        actor=user,
        payload={"request_id": str(doc["_id"]), "parcel_id": parcel_id, "model": body.model},
    )
    return {"request": serialize_doc(doc)}


async def _list_requests(user: dict, field: str) -> dict:
    uid = str(user["id"])
    docs = await db.radacini_land_requests.find({field: uid}).sort("updated_at", -1).to_list(200)
    docs = [await refresh_expiry(d) for d in docs]
    return {"items": await _enrich(docs, uid)}


# /requests/sent și /requests/received trebuie declarate înaintea lui /requests/{id}.

@router.get("/requests/sent")
async def list_sent(user: dict = Depends(get_current_user)):
    return await _list_requests(user, "requester_user_id")


@router.get("/requests/received")
async def list_received(user: dict = Depends(get_current_user)):
    return await _list_requests(user, "owner_user_id")


@router.get("/requests/{request_id}")
async def get_request(request_id: str, user: dict = Depends(get_current_user)):
    doc = await _load_request(request_id)
    parcel = await get_parcel_doc(doc.get("parcel_id"))
    access = await party_access(doc, user, parcel)
    if access == "party" and doc.get("status") == "sent" and str(doc["owner_user_id"]) == str(user["id"]):
        now = now_iso()
        res = await db.radacini_land_requests.update_one(
            {"_id": doc["_id"], "status": "sent"}, {"$set": {"status": "viewed", "updated_at": now}}
        )
        if res.modified_count == 1:
            doc = {**doc, "status": "viewed", "updated_at": now}
        else:
            doc = await _load_request(request_id)
    msgs = await db.radacini_request_messages.find({"request_id": str(doc["_id"])}).sort("created_at", 1).to_list(1000)
    users = await load_owners(m.get("sender_user_id") for m in msgs)
    messages = []
    for m in msgs:
        item = serialize_doc(m)
        item["sender_name"] = users.get(str(m.get("sender_user_id")), {}).get("name", "")
        messages.append(item)
    request = (await _enrich([doc], str(user["id"])))[0]
    if parcel:
        request["parcel_area_m2"] = parcel.get("area_m2")
    return {"request": request, "messages": messages}


@router.post("/requests/{request_id}/messages")
async def post_message(request_id: str, body: MessageIn, user: dict = Depends(get_current_user)):
    doc = await _load_request(request_id)
    _require_party(await party_access(doc, user))
    _require_active(doc)
    now = now_iso()
    res = await db.radacini_land_requests.update_one(
        {"_id": doc["_id"], "status": {"$in": list(ACTIVE_STATUSES)}},
        {"$set": {"status": "negotiating", "last_activity_at": now, "updated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea nu mai este activă.")
    msg = mark_demo({
        "request_id": str(doc["_id"]),
        "sender_user_id": str(user["id"]),
        "text": body.text,
        "created_at": now,
    })
    await db.radacini_request_messages.insert_one(msg)
    await safe_notify(
        _other_party(doc, user),
        "Mesaj nou la o cerere de teren",
        f"{user.get('name') or 'Cealaltă parte'}: {body.text[:120]}",
        link=_link(doc),
        type_="request",
    )
    await emit("radacini.request_message", actor=user, payload={"request_id": str(doc["_id"])})
    return {"message": serialize_doc(msg)}


@router.post("/requests/{request_id}/counter")
async def counter_request(request_id: str, body: ProposalIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "trimiterea contrapropunerii")
    doc = await _load_request(request_id)
    _require_party(await party_access(doc, user))
    _require_active(doc)
    parcel = await get_parcel_doc(doc["parcel_id"])
    proposal = _proposal_dict(body)
    check_terms(proposal, model=doc["model"], parcel_area=(parcel or {}).get("area_m2"))
    now = now_iso()
    old = doc.get("proposal") or {}
    res = await db.radacini_land_requests.update_one(
        {
            "_id": doc["_id"],
            "status": {"$in": list(ACTIVE_STATUSES)},
            "proposal_at": doc.get("proposal_at"),
        },
        {
            "$set": {
                "proposal": proposal,
                "proposal_by_user_id": str(user["id"]),
                "proposal_at": now,
                "status": "negotiating",
                "last_activity_at": now,
                "updated_at": now,
            },
            "$push": {
                "proposals_history": {
                    "proposal": old,
                    "by_user_id": str(doc.get("proposal_by_user_id") or doc.get("requester_user_id")),
                    "at": doc.get("proposal_at") or doc.get("created_at"),
                }
            },
        },
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea a fost modificată între timp. Reîncarcă pagina.")
    await safe_notify(
        _other_party(doc, user),
        "Contrapropunere nouă",
        f"{user.get('name') or 'Cealaltă parte'} a trimis o contrapropunere.",
        link=_link(doc),
        type_="request",
    )
    await emit("radacini.request_countered", actor=user, payload={"request_id": str(doc["_id"])})
    fresh = await db.radacini_land_requests.find_one({"_id": doc["_id"]})
    return {"request": serialize_doc(fresh)}


async def _close_request(request_id: str, user: dict, *, new_status: str, as_owner: bool, reason: Optional[str]):
    doc = await _load_request(request_id)
    _require_party(await party_access(doc, user))
    expected_uid = str(doc["owner_user_id"] if as_owner else doc["requester_user_id"])
    if str(user["id"]) != expected_uid:
        raise HTTPException(
            403, "Doar proprietarul poate refuza cererea." if as_owner else "Doar solicitantul poate retrage cererea."
        )
    _require_active(doc)
    now = now_iso()
    changes = {"status": new_status, "decided_at": now, "last_activity_at": now, "updated_at": now}
    if reason:
        changes["decline_reason"] = reason
    res = await db.radacini_land_requests.update_one(
        {"_id": doc["_id"], "status": {"$in": list(ACTIVE_STATUSES)}}, {"$set": changes}
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea nu mai este activă.")
    return {**doc, **changes}


@router.post("/requests/{request_id}/decline")
async def decline_request(request_id: str, body: ReasonIn, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "refuzarea cererii")
    doc = await _close_request(request_id, user, new_status="declined", as_owner=True, reason=body.reason)
    message = "Proprietarul a refuzat cererea."
    if body.reason:
        message += f" Motiv: {body.reason}"
    await safe_notify(doc["requester_user_id"], "Cerere refuzată", message, link=_link(doc), type_="request")
    await emit("radacini.request_declined", actor=user, payload={"request_id": str(doc["_id"])})
    return {"request": serialize_doc(doc)}


@router.post("/requests/{request_id}/withdraw")
async def withdraw_request(request_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "retragerea cererii")
    doc = await _close_request(request_id, user, new_status="withdrawn", as_owner=False, reason=None)
    await safe_notify(
        doc["owner_user_id"],
        "Cerere retrasă",
        f"{user.get('name') or 'Solicitantul'} și-a retras cererea.",
        link=_link(doc),
        type_="request",
    )
    await emit("radacini.request_withdrawn", actor=user, payload={"request_id": str(doc["_id"])})
    return {"request": serialize_doc(doc)}


@router.post("/requests/{request_id}/accept")
async def accept_request(request_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "acceptarea cererii")
    doc = await _load_request(request_id)
    _require_party(await party_access(doc, user))
    if str(user["id"]) != str(doc["owner_user_id"]):
        raise HTTPException(403, "Doar proprietarul poate accepta cererea.")
    _require_active(doc)
    if doc.get("model") not in REQUESTABLE_MODEL_IDS:  # cerere anterioară porții juridice
        raise HTTPException(409, LEGAL_GATE_MESSAGE)
    # Proprietarul acceptă doar propunerea celuilalt (nu o contrapropunere proprie).
    if str(doc.get("proposal_by_user_id")) == str(doc["owner_user_id"]):
        raise HTTPException(409, "Așteaptă răspunsul solicitantului.")
    parcel = await get_parcel_doc(doc["parcel_id"])
    if not parcel or parcel.get("archived_at"):
        raise HTTPException(409, "Terenul nu mai este disponibil.")
    if parcel.get("active_agreement_id"):
        raise HTTPException(409, "Terenul are deja un acord activ.")
    if parcel.get("status") != "published":
        raise HTTPException(409, "Terenul nu mai este disponibil.")

    now = now_iso()
    prev_status = doc["status"]
    proposal = doc.get("proposal") or {}
    names = await load_owners([doc["owner_user_id"], doc["requester_user_id"]])
    agreement = mark_demo({
        "_id": ObjectId(),
        "request_id": str(doc["_id"]),
        "parcel_id": doc["parcel_id"],
        "parties": [
            {"user_id": doc["owner_user_id"], "role": "owner", "name": names.get(doc["owner_user_id"], {}).get("name", "")},
            {"user_id": doc["requester_user_id"], "role": "cultivator", "name": names.get(doc["requester_user_id"], {}).get("name", "")},
        ],
        "party_ids": [doc["owner_user_id"], doc["requester_user_id"]],
        "model": doc["model"],
        "terms": {
            "area_m2": proposal.get("area_m2"),
            "start_date": proposal.get("start_date"),
            "end_date": proposal.get("end_date"),
            "price_ron_per_year": proposal.get("price_ron_per_year"),
            "harvest_share_percent": proposal.get("harvest_share_percent"),
            "crops": proposal.get("crops") or [],
            "custom_clauses": None,
            "parcel_snapshot": {
                "title": parcel.get("title"),
                "locality": parcel.get("locality"),
                "area_m2": parcel.get("area_m2"),
            },
        },
        "version": 1,
        "versions_history": [],
        "terms_by_user_id": str(user["id"]),
        "terms_at": now,
        "signatures": [],
        "status": "draft",
        "legal_notice": LEGAL_NOTICE,
        "created_at": now,
        "updated_at": now,
    })
    agreement_id = str(agreement["_id"])
    changes = {"status": "accepted", "decided_at": now, "last_activity_at": now, "updated_at": now, "agreement_id": agreement_id}
    # Filtru pe `proposal_at`: acordul se creează exact din propunerea citită (nu dintr-o contrapropunere nouă).
    res = await db.radacini_land_requests.update_one(
        {"_id": doc["_id"], "status": {"$in": list(ACTIVE_STATUSES)}, "proposal_at": doc.get("proposal_at")},
        {"$set": changes},
    )
    if res.modified_count != 1:
        fresh = await db.radacini_land_requests.find_one({"_id": doc["_id"]}, {"status": 1})
        if fresh and fresh.get("status") in ACTIVE_STATUSES:
            raise HTTPException(409, "Propunerea s-a schimbat între timp.")
        raise HTTPException(409, "Cererea nu mai este activă.")
    try:
        await db.radacini_agreements.insert_one(agreement)
    except Exception:
        await db.radacini_land_requests.update_one(
            {"_id": doc["_id"], "status": "accepted"},
            {
                "$set": {"status": prev_status, "updated_at": now_iso()},
                "$unset": {"agreement_id": "", "decided_at": ""},
            },
        )
        raise
    await safe_notify(
        doc["requester_user_id"],
        "Cerere acceptată",
        f"Proprietarul a acceptat cererea pentru „{parcel.get('title')}”. Acordul este în pregătire.",
        link=f"/radacini/acorduri/{agreement_id}",
        type_="request",
    )
    await emit(
        "radacini.request_accepted",
        actor=user,
        payload={"request_id": str(doc["_id"]), "agreement_id": agreement_id, "parcel_id": doc["parcel_id"]},
    )
    return {"request": serialize_doc({**doc, **changes}), "agreement": serialize_doc(agreement)}
