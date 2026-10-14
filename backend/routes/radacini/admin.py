"""Administrare Rădăcini (S5): KPI, flux de activitate, membri, moderare, cereri GDPR și audit.

Toate rutele cer rolul `manager` (super-adminul PropManage e tratat ca manager), prin `require_staff("manager")`.
Reguli de performanță (egress, vezi `pgmongo`): doar filtre de egalitate/`$in` mici/`$exists`/`$lt` pe câmpuri de
nivel superior (se traduc exact în SQL, cu GIN), proiecții, `.limit(N)` explicit și `$in` în bucăți de 100.
Fără `$regex` și fără chei cu punct (ar încărca toți candidații în memorie).
"""
import asyncio
import time
import unicodedata
from datetime import datetime, timezone
from typing import Iterable, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator, model_validator

from .bridge import block_in_impersonation, db, emit, serialize_doc
from .common import RadaciniRoute, audit_staff, now_iso, oid_or_404, safe_notify
from .constants import INTEREST_IDS, INTERESTS, LOCALITIES
from .market import MAX_CLOSE_NOTIFY, _pending_counts, listing_link
from .staff import require_staff

router = APIRouter(prefix="/admin", route_class=RadaciniRoute)

# O singură instanță a dependenței: FastAPI o evaluează o dată per cerere, iar fiecare rută o cere explicit.
_manager = require_staff("manager")

IN_CHUNK = 100  # `$in` peste 200 de valori nu se traduce în SQL (încarcă toată colecția)
KPI_TTL = 300.0  # secunde: cache în memorie (egress)
HARVEST_CAP = 5000  # recoltele confirmate însumate pentru kg totale
MEMBER_SCAN_CAP = 500  # membri parcurși când se caută după nume (`q`)
COUNT_CAP = 5000  # rânduri citite per bucată la numărarea terenurilor/proiectelor/anunțurilor unui membru

PARCEL_STATUSES = ("draft", "pending_verification", "published", "rejected", "paused")
REQUEST_STATUSES = ("sent", "viewed", "negotiating", "accepted", "declined", "withdrawn", "expired")
RESERVATION_STATUSES = ("requested", "confirmed", "picked_up", "cancelled", "no_show", "declined")
LISTING_STATUSES = ("active", "closed")
DELETION_STATUSES = ("pending", "done", "rejected")

# Evenimentele `radacini.*` emise în cod (grep `emit("radacini.`). Listă explicită, ca interogarea să rămână
# o căutare indexată pe `event_type` (un `$regex` ar încărca tot `activity_events`). Rezervările folosesc
# `emit(event, ...)` din `market._notify_other`. Un tip nou se adaugă aici.
EVENT_TYPES = (
    "radacini.activity_cancelled", "radacini.activity_created", "radacini.activity_done",
    "radacini.activity_joined", "radacini.activity_left", "radacini.activity_updated",
    "radacini.agreement_cancelled", "radacini.agreement_completed", "radacini.agreement_edited",
    "radacini.agreement_proposed", "radacini.agreement_signed",
    "radacini.allocation_created", "radacini.allocation_received", "radacini.allocation_removed",
    "radacini.contribution_logged", "radacini.contribution_reviewed",
    "radacini.deletion_requested", "radacini.deletion_resolved",
    "radacini.harvest_confirmed", "radacini.harvest_recorded",
    "radacini.listing_closed", "radacini.listing_created", "radacini.listing_updated",
    "radacini.member_updated",
    "radacini.parcel_submitted", "radacini.parcel_verified",
    "radacini.project_completed", "radacini.project_created",
    "radacini.project_crop_added", "radacini.project_crop_removed", "radacini.project_crop_updated",
    "radacini.project_member_added", "radacini.project_member_removed", "radacini.project_member_role_changed",
    "radacini.request_accepted", "radacini.request_countered", "radacini.request_created",
    "radacini.request_declined", "radacini.request_message", "radacini.request_withdrawn",
    "radacini.reservation_cancelled", "radacini.reservation_confirmed", "radacini.reservation_declined",
    "radacini.reservation_no_show", "radacini.reservation_picked_up", "radacini.reservation_rated",
    "radacini.reservation_requested",
)

# Acțiunile scrise de `audit_staff` (prefixul `radacini.` e adăugat acolo). Aceeași logică: listă explicită.
AUDIT_ACTIONS = (
    "radacini.parcel.approve", "radacini.parcel.reject",
    "radacini.staff.add", "radacini.staff.remove",
    "radacini.test_accounts.ensure", "radacini.test_accounts.seed", "radacini.test_accounts.reset",
    "radacini.listing.close",
    "radacini.deletion.resolve",
)


# ------------------------------------------------------------------------------------------ helpere

def _chunks(items: list, size: int = IN_CHUNK) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _any_of(field: str, values: Iterable[str]) -> dict:
    """„câmpul e una dintre valori” ca `$or` de egalități: fiecare ramură se traduce în `data @> …` (GIN), spre
    deosebire de `$in` cu mai mult de 3 valori, care citește câmpul pe fiecare rând."""
    return {"$or": [{field: v} for v in values]}


def _fold(text) -> str:
    """Minuscule fără diacritice (căutare după nume, Python — fără `$regex`)."""
    s = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _first_name(name) -> str:
    parts = str(name or "").split()
    return parts[0] if parts else ""


def _valid_ids(ids: Iterable) -> list:
    return list(dict.fromkeys(i for i in ids if isinstance(i, str) and len(i) == 24 and ObjectId.is_valid(i)))


async def _user_info(user_ids: Iterable, fields: tuple = ("name",)) -> dict:
    """{user_id: {câmp: valoare}} din `users`, în bucăți de 100, doar cu proiecția cerută."""
    out: dict = {}
    for chunk in _chunks(_valid_ids(user_ids)):
        rows = await db.users.find(
            {"_id": {"$in": [ObjectId(i) for i in chunk]}}, {f: 1 for f in fields}
        ).limit(len(chunk)).to_list(len(chunk))
        for r in rows:
            out[str(r["_id"])] = {f: r.get(f) or "" for f in fields}
    return out


def _parse_before(before: Optional[str]) -> Optional[str]:
    """Data ISO primită → ISO UTC, comparabilă lexicografic cu `created_at` (scris de `datetime.now(utc).isoformat()`)."""
    if not before:
        return None
    try:
        dt = datetime.fromisoformat(before.strip().replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "Parametrul „before” trebuie să fie o dată ISO validă.") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _check_choice(value: Optional[str], allowed: Iterable[str], label: str) -> Optional[str]:
    if value in (None, ""):
        return None
    if value not in allowed:
        raise HTTPException(400, f"{label} necunoscut(ă).")
    return value


# ------------------------------------------------------------------------------------------ KPI

_KPI_CACHE: dict = {"at": 0.0, "data": None}
_KPI_LOCK: Optional[asyncio.Lock] = None


def _kpi_lock() -> asyncio.Lock:
    global _KPI_LOCK
    if _KPI_LOCK is None:
        _KPI_LOCK = asyncio.Lock()
    return _KPI_LOCK


def invalidate_kpi_cache() -> None:
    _KPI_CACHE["data"] = None


async def _by_status(collection, statuses: Iterable[str], extra: Optional[dict] = None) -> dict:
    return {s: await collection.count_documents({"status": s, **(extra or {})}) for s in statuses}


async def _compute_kpis() -> dict:
    # Interogări secvențiale, fiecare un `count(*)` exact în SQL (filtre pe câmpuri de nivel superior).
    members_by_interest = {i["id"]: await db.radacini_members.count_documents({"interests": i["id"]}) for i in INTERESTS}
    parcels_by_status = await _by_status(db.radacini_parcels, PARCEL_STATUSES, {"archived_at": {"$exists": False}})
    harvests = await db.radacini_harvests.find({"status": "confirmed"}, {"quantity_kg": 1}).limit(HARVEST_CAP).to_list(HARVEST_CAP)
    kg = sum(float(h.get("quantity_kg") or 0) for h in harvests)
    return {
        "members": await db.radacini_members.count_documents({}),
        "members_by_interest": members_by_interest,
        "parcels_by_status": parcels_by_status,
        "requests_by_status": await _by_status(db.radacini_land_requests, REQUEST_STATUSES),
        "agreements_signed": await db.radacini_agreements.count_documents({"status": "signed"}),
        "projects_active": await db.radacini_projects.count_documents({"status": "active"}),
        "harvest_kg_confirmed": round(kg, 3),
        "harvest_kg_capped": len(harvests) >= HARVEST_CAP,
        "listings_active": await db.radacini_listings.count_documents({"status": "active"}),
        "reservations_by_status": await _by_status(db.radacini_reservations, RESERVATION_STATUSES),
        "pending_verification": parcels_by_status["pending_verification"],
        "open_deletion_requests": await db.radacini_deletion_requests.count_documents({"status": "pending"}),
        "generated_at": now_iso(),
    }


@router.get("/kpis")
async def kpis(_: dict = Depends(_manager)):
    """Indicatori calculați la cerere și păstrați 5 minute în memorie (per proces). Cererile expirate lazy
    (`expired`) apar doar după ce sunt citite; cele active mai vechi de 30 de zile încă n-au fost marcate."""
    def fresh() -> bool:
        return _KPI_CACHE["data"] is not None and time.monotonic() - _KPI_CACHE["at"] < KPI_TTL

    if fresh():
        return {**_KPI_CACHE["data"], "cached": True}
    async with _kpi_lock():
        if fresh():  # alt request a recalculat între timp
            return {**_KPI_CACHE["data"], "cached": True}
        data = await _compute_kpis()
        _KPI_CACHE["data"], _KPI_CACHE["at"] = data, time.monotonic()
    return {**data, "cached": False}


# ------------------------------------------------------------------------------------------ activitate

def _safe_payload(payload) -> dict:
    """Payload-ul evenimentului, fără chei care ar putea conține emailuri."""
    if not isinstance(payload, dict):
        return {}
    return {k: v for k, v in payload.items() if "email" not in str(k).lower()}


@router.get("/activity")
async def activity(
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = Query(None, max_length=64),
    _: dict = Depends(_manager),
):
    """Evenimentele `radacini.*` din `activity_events` (cele mai noi primele), cu prenumele actorului, fără email.
    Paginare: `before` = `created_at` al ultimului element primit (`next_before`)."""
    flt: dict = _any_of("event_type", EVENT_TYPES)
    cutoff = _parse_before(before)
    if cutoff:
        flt["created_at"] = {"$lt": cutoff}
    proj = {"event_type": 1, "actor_id": 1, "actor_name": 1, "actor_role": 1, "payload": 1, "created_at": 1}
    docs = await db.activity_events.find(flt, proj).sort("created_at", -1).limit(limit).to_list(limit)
    names = await _user_info(d.get("actor_id") for d in docs)
    items = []
    for d in docs:
        actor = names.get(str(d.get("actor_id")), {}).get("name") or d.get("actor_name")
        items.append({
            "id": str(d["_id"]),
            "type": d.get("event_type"),
            "actor_id": d.get("actor_id"),
            "actor_name": _first_name(actor),
            "actor_role": d.get("actor_role"),
            "payload": _safe_payload(d.get("payload")),
            "created_at": d.get("created_at"),
        })
    return {"items": items, "next_before": items[-1]["created_at"] if len(items) == limit else None}


# ------------------------------------------------------------------------------------------ membri

async def _count_per_user(collection, field: str, user_ids: list, extra: Optional[dict] = None) -> dict:
    """Câte documente are fiecare utilizator din `user_ids` (câmpul `field`, scalar sau listă), în bucăți de 100."""
    counts: dict = {}
    for chunk in _chunks(user_ids):
        rows = await collection.find({field: {"$in": chunk}, **(extra or {})}, {field: 1}).limit(COUNT_CAP).to_list(COUNT_CAP)
        wanted = set(chunk)
        for r in rows:
            value = r.get(field)
            for uid in (value if isinstance(value, list) else [value]):
                if uid in wanted:
                    counts[uid] = counts.get(uid, 0) + 1
    return counts


@router.get("/members")
async def members(
    q: Optional[str] = Query(None, max_length=80),
    interest: Optional[str] = Query(None, max_length=40),
    locality: Optional[str] = Query(None, max_length=80),
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(50, ge=1, le=50),
    _: dict = Depends(_manager),
):
    """Membri Rădăcini cu numele, localitatea, interesele și contoarele (terenuri nearhivate, proiecte, anunțuri
    active). Fără email. `profilul` Rădăcini nu stochează numele, deci `q` caută (fără diacritice, fără majuscule)
    în numele din `users` doar printre cei mai recenți `MEMBER_SCAN_CAP` membri care trec de celelalte filtre;
    `scan_truncated` arată că lista poate fi incompletă."""
    flt: dict = {}
    if _check_choice(interest, INTEREST_IDS, "Interes"):
        flt["interests"] = interest
    if _check_choice(locality, LOCALITIES, "Localitate"):
        flt["locality"] = locality
    needle = _fold(q).strip() if q else ""
    proj = {"user_id": 1, "interests": 1, "county": 1, "locality": 1, "created_at": 1}

    names: dict = {}
    scan_truncated = False
    if needle:
        scanned = await db.radacini_members.find(flt, proj).sort("created_at", -1).limit(MEMBER_SCAN_CAP).to_list(MEMBER_SCAN_CAP)
        scan_truncated = len(scanned) >= MEMBER_SCAN_CAP
        names = await _user_info(m.get("user_id") for m in scanned)
        matched = [m for m in scanned if needle in _fold(names.get(m.get("user_id"), {}).get("name"))]
        total = len(matched)
        docs = matched[skip:skip + limit]
    else:
        total = await db.radacini_members.count_documents(flt)
        docs = await db.radacini_members.find(flt, proj).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
        names = await _user_info(m.get("user_id") for m in docs)

    uids = [m["user_id"] for m in docs if m.get("user_id")]
    parcels = await _count_per_user(db.radacini_parcels, "owner_user_id", uids, {"archived_at": {"$exists": False}})
    projects = await _count_per_user(db.radacini_projects, "member_ids", uids)
    listings = await _count_per_user(db.radacini_listings, "seller_user_id", uids, {"status": "active"})
    items = []
    for m in docs:
        uid = m.get("user_id")
        items.append({
            "id": str(m["_id"]),
            "user_id": uid,
            "name": names.get(uid, {}).get("name", ""),
            "county": m.get("county"),
            "locality": m.get("locality"),
            "interests": m.get("interests") or [],
            "created_at": m.get("created_at"),
            "counts": {"parcels": parcels.get(uid, 0), "projects": projects.get(uid, 0), "listings": listings.get(uid, 0)},
        })
    return {"items": items, "total": total, "skip": skip, "limit": limit, "scan_truncated": scan_truncated}


# ------------------------------------------------------------------------------------------ terenuri

def _parcel_row(doc: dict, owner_name: str) -> dict:
    """Vedere de moderare: fără descriere/acces; coordonatele sunt rotunjite la 2 zecimale. Locația exactă se citește
    doar prin `GET /parcels/{id}`, care o consemnează în jurnalul de acces (o listă nu trebuie să genereze zeci de intrări)."""
    out = {k: doc.get(k) for k in (
        "title", "county", "locality", "area_m2", "status", "owner_user_id", "active_agreement_id",
        "created_at", "updated_at", "is_demo",
    )}
    out["id"] = str(doc["_id"])
    out["owner_name"] = owner_name
    out["lat"] = round(float(doc["lat"]), 2) if doc.get("lat") is not None else None
    out["lng"] = round(float(doc["lng"]), 2) if doc.get("lng") is not None else None
    out["exact_location"] = False
    out["offer_models"] = list((doc.get("offer") or {}).get("models") or [])
    ver = doc.get("verification") or {}
    out["verification"] = {k: ver.get(k) for k in ("at", "decision", "note")} if ver else None
    return out


@router.get("/parcels")
async def parcels(
    status: Optional[str] = Query(None, max_length=40),
    locality: Optional[str] = Query(None, max_length=80),
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(50, ge=1, le=50),
    _: dict = Depends(_manager),
):
    flt: dict = {"archived_at": {"$exists": False}}
    if _check_choice(status, PARCEL_STATUSES, "Stare"):
        flt["status"] = status
    if _check_choice(locality, LOCALITIES, "Localitate"):
        flt["locality"] = locality
    total = await db.radacini_parcels.count_documents(flt)
    docs = await db.radacini_parcels.find(flt).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)
    owners = await _user_info(d.get("owner_user_id") for d in docs)
    items = [_parcel_row(d, owners.get(str(d.get("owner_user_id")), {}).get("name", "")) for d in docs]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


# ------------------------------------------------------------------------------------------ anunțuri

def _listing_row(doc: dict, pending: dict) -> dict:
    out = serialize_doc(doc)
    out.pop("product_tokens", None)  # intern: doar pentru căutare
    out["pending_reservations"] = pending.get(str(doc["_id"]), 0)
    return out


@router.get("/listings")
async def listings(
    status: Optional[str] = Query(None, max_length=40),
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(50, ge=1, le=50),
    _: dict = Depends(_manager),
):
    flt: dict = {}
    if _check_choice(status, LISTING_STATUSES, "Stare"):
        flt["status"] = status
    total = await db.radacini_listings.count_documents(flt)
    docs = await db.radacini_listings.find(flt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    pending = await _pending_counts([str(d["_id"]) for d in docs]) if docs else {}
    return {"items": [_listing_row(d, pending) for d in docs], "total": total, "skip": skip, "limit": limit}


class CloseListingIn(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def _reason(cls, v: str) -> str:
        v = " ".join((v or "").split())
        if not 3 <= len(v) <= 300:
            raise ValueError("Motivul trebuie să aibă între 3 și 300 de caractere.")
        return v


@router.post("/listings/{listing_id}/close")
async def close_listing(listing_id: str, body: CloseListingIn, staff: dict = Depends(_manager)):
    """Moderare: aceeași semantică ca `POST /listings/{id}/close` al vânzătorului (rezervările `requested` se
    anulează, cumpărătorii sunt notificați), plus notificarea vânzătorului și auditul. Motivul ajunge doar la
    vânzător (notificare) și în audit; nu se salvează pe anunț, pe care îl pot citi și cumpărătorii cu rezervare
    (pe anunț rămâne doar `moderated_at`)."""
    user = staff["user"]
    block_in_impersonation(user, "moderarea anunțurilor")
    doc = await db.radacini_listings.find_one({"_id": oid_or_404(listing_id)})
    if not doc:
        raise HTTPException(404, "Anunțul nu există.")
    now = now_iso()
    res = await db.radacini_listings.update_one(
        {"_id": doc["_id"], "status": "active"},
        {"$set": {"status": "closed", "updated_at": now, "moderated_at": now}},
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Anunțul este deja închis.")
    invalidate_kpi_cache()
    lid = str(doc["_id"])
    pending_flt = {"listing_id": lid, "status": "requested"}
    buyers = await db.radacini_reservations.find(pending_flt, {"buyer_user_id": 1}).limit(MAX_CLOSE_NOTIFY).to_list(MAX_CLOSE_NOTIFY)
    upd = await db.radacini_reservations.update_many(
        pending_flt, {"$set": {"status": "cancelled", "cancel_reason": "listing_closed", "updated_at": now}}
    )
    product = doc.get("product") or "anunțul tău"
    for buyer_id in dict.fromkeys(r["buyer_user_id"] for r in buyers):
        await safe_notify(
            buyer_id,
            "Anunț închis",
            f"Anunțul „{product}” a fost închis, iar rezervarea ta a fost anulată.",
            link=listing_link(lid),
            type_="market",
        )
    await safe_notify(
        doc.get("seller_user_id"),
        "Anunțul tău a fost închis de echipa Rădăcini",
        f"Anunțul „{product}” a fost închis. Motiv: {body.reason}",
        link=listing_link(lid),
        type_="moderation",
    )
    await audit_staff(user, "listing.close", "radacini_listing", lid, {
        "seller_user_id": doc.get("seller_user_id"),
        "product": product,
        "reason": body.reason,
        "cancelled_reservations": upd.modified_count,
    })
    await emit("radacini.listing_closed", actor=user, payload={"listing_id": lid, "cancelled": upd.modified_count, "moderated": True})
    fresh = {**doc, "status": "closed", "updated_at": now, "moderated_at": now}
    return {"listing": _listing_row(fresh, {}), "reason": body.reason, "cancelled_reservations": upd.modified_count}


# ------------------------------------------------------------------------------------------ cereri GDPR

@router.get("/deletion-requests")
async def deletion_requests(
    status: Optional[str] = Query(None, max_length=40),
    skip: int = Query(0, ge=0, le=100_000),
    limit: int = Query(50, ge=1, le=100),
    _: dict = Depends(_manager),
):
    """Cererile de ștergere (cele mai noi primele). Includ numele și emailul contului, necesare ca managerul să
    găsească datele de șters; nu se mai expun în altă parte a administrării."""
    flt: dict = {}
    if _check_choice(status, DELETION_STATUSES, "Stare"):
        flt["status"] = status
    total = await db.radacini_deletion_requests.count_documents(flt)
    docs = await db.radacini_deletion_requests.find(flt).sort("at", -1).skip(skip).limit(limit).to_list(limit)
    users = await _user_info(
        [d.get("user_id") for d in docs] + [d.get("resolved_by") for d in docs], ("name", "email"))
    items = []
    for d in docs:
        item = serialize_doc(d)
        who = users.get(str(d.get("user_id")), {})
        item["user_name"], item["user_email"] = who.get("name", ""), who.get("email", "")
        if d.get("resolved_by"):
            item["resolved_by_name"] = users.get(str(d["resolved_by"]), {}).get("name", "")
        items.append(item)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


class ResolveIn(BaseModel):
    decision: str
    note: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def _decision(cls, v: str) -> str:
        if v not in ("done", "rejected"):
            raise ValueError("Decizie invalidă. Alege „done” sau „rejected”.")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 1000:
            raise ValueError("Nota are cel mult 1000 de caractere.")
        return v or None

    @model_validator(mode="after")
    def _reject_needs_note(self):
        if self.decision == "rejected" and (not self.note or len(self.note) < 3):
            raise ValueError("Motivul respingerii este obligatoriu (cel puțin 3 caractere).")
        return self


@router.post("/deletion-requests/{request_id}/resolve")
async def resolve_deletion_request(request_id: str, body: ResolveIn, staff: dict = Depends(_manager)):
    """Marchează o cerere `pending` ca `done` (ștergerea s-a făcut manual, în afara platformei) sau `rejected`,
    și notifică utilizatorul. Tranziția e atomică: a doua rezolvare primește 409."""
    user = staff["user"]
    block_in_impersonation(user, "rezolvarea cererii de ștergere")
    doc = await db.radacini_deletion_requests.find_one({"_id": oid_or_404(request_id)})
    if not doc:
        raise HTTPException(404, "Cererea nu există.")
    now = now_iso()
    changes = {"status": body.decision, "resolved_at": now, "resolved_by": str(user["id"]), "resolution_note": body.note}
    res = await db.radacini_deletion_requests.update_one({"_id": doc["_id"], "status": "pending"}, {"$set": changes})
    if res.modified_count != 1:
        raise HTTPException(409, "Cererea a fost deja rezolvată.")
    invalidate_kpi_cache()
    uid = str(doc.get("user_id"))
    if body.decision == "done":
        title, message = "Cererea de ștergere a fost procesată", "Datele tale din Rădăcini au fost șterse sau anonimizate."
        if body.note:
            message += f" {body.note}"
    else:
        title, message = "Cererea de ștergere a fost respinsă", f"Cererea ta de ștergere a datelor nu a putut fi îndeplinită: {body.note}"
    await safe_notify(uid, title, message, link="/radacini/setari", type_="gdpr")
    await audit_staff(user, "deletion.resolve", "radacini_deletion_request", doc["_id"], {
        "user_id": uid, "decision": body.decision, "note": body.note,
    })
    await emit("radacini.deletion_resolved", actor=user, payload={"request_id": str(doc["_id"]), "decision": body.decision})
    return {"request": serialize_doc({**doc, **changes})}


# ------------------------------------------------------------------------------------------ audit

@router.get("/audit")
async def audit_log(
    limit: int = Query(50, ge=1, le=100),
    before: Optional[str] = Query(None, max_length=64),
    _: dict = Depends(_manager),
):
    """Intrările de audit Rădăcini din jurnalul admin PropManage (`admin_audit_log`), cele mai noi primele.
    Filtrate pe lista explicită `AUDIT_ACTIONS` (fără `$regex`); emailul actorului nu se returnează."""
    flt: dict = _any_of("action", AUDIT_ACTIONS)
    cutoff = _parse_before(before)
    if cutoff:
        flt["created_at"] = {"$lt": cutoff}
    proj = {"action": 1, "actor_id": 1, "actor_name": 1, "target_type": 1, "target_id": 1, "after": 1, "note": 1, "created_at": 1}
    docs = await db.admin_audit_log.find(flt, proj).sort("created_at", -1).limit(limit).to_list(limit)
    items = [{
        "id": str(d["_id"]),
        "action": d.get("action"),
        "actor_id": d.get("actor_id"),
        "actor_name": d.get("actor_name"),
        "target_type": d.get("target_type"),
        "target_id": d.get("target_id"),
        "details": d.get("after"),
        "note": d.get("note"),
        "created_at": d.get("created_at"),
    } for d in docs]
    return {"items": items, "next_before": items[-1]["created_at"] if len(items) == limit else None}
