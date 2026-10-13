"""Terenuri Rădăcini: CRUD proprietar, listare publică și ciclul de publicare."""
import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator, model_validator

from .bridge import block_in_impersonation, db, emit, get_current_user, serialize_doc
from .common import (
    RadaciniRoute,
    check_finite,
    check_price,
    get_optional_user,
    load_owners,
    mark_demo,
    now_iso,
    oid_or_404,
)
from .constants import COUNTY, LOCALITIES, OFFER_MODEL_IDS, WATER_SOURCE_IDS
from .members import get_member_doc
from .projects import release_parcel
from .staff import get_staff

router = APIRouter(route_class=RadaciniRoute)

_NON_NULL_FIELDS = ("title", "county", "locality", "lat", "lng", "area_m2", "offer")
# Câmpurile verificate de personal: dacă un teren suspendat le schimbă, trebuie reverificat (revine în `draft`).
_CONTENT_FIELDS = (
    "title", "county", "locality", "lat", "lng", "area_m2",
    "access", "water_sources", "current_crops", "description", "offer",
)
_CHANGED = "Terenul s-a schimbat între timp. Reîncarcă pagina."


class OfferIn(BaseModel):
    models: list[str]
    terms: Optional[str] = None
    price_ron_per_year: Optional[float] = None
    harvest_share_percent: Optional[int] = None

    @field_validator("models")
    @classmethod
    def _models(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Alege cel puțin un model de ofertă.")
        if any(m not in OFFER_MODEL_IDS for m in v):
            raise ValueError("Model de ofertă necunoscut.")
        return list(dict.fromkeys(v))

    @field_validator("terms")
    @classmethod
    def _terms(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("Condițiile au cel mult 2000 de caractere.")
        return v or None

    @field_validator("price_ron_per_year")
    @classmethod
    def _price(cls, v: Optional[float]) -> Optional[float]:
        return check_price(v)

    @model_validator(mode="after")
    def _harvest_share(self):
        if "harvest_share" in self.models:
            if self.harvest_share_percent is None or not 1 <= self.harvest_share_percent <= 90:
                raise ValueError("Procentul din recoltă trebuie să fie între 1 și 90.")
        elif self.harvest_share_percent is not None:
            raise ValueError("Procentul din recoltă se completează doar la „Cultivare la parte din recoltă”.")
        return self


class ParcelPatch(BaseModel):
    """Câmpurile unui teren; la PATCH sunt toate opționale (doar cele trimise se schimbă)."""

    title: Optional[str] = None
    county: Optional[str] = None
    locality: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    area_m2: Optional[int] = None
    access: Optional[str] = None
    water_sources: Optional[list[str]] = None
    current_crops: Optional[list[str]] = None
    description: Optional[str] = None
    availability_from: Optional[date] = None
    availability_to: Optional[date] = None
    offer: Optional[OfferIn] = None

    @field_validator("title")
    @classmethod
    def _title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not 3 <= len(v) <= 120:
            raise ValueError("Titlul trebuie să aibă între 3 și 120 de caractere.")
        return v

    @field_validator("county")
    @classmethod
    def _county(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != COUNTY:
            raise ValueError("Județul trebuie să fie Cluj.")
        return v

    @field_validator("locality")
    @classmethod
    def _locality(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in LOCALITIES:
            raise ValueError("Localitate necunoscută.")
        return v

    @field_validator("lat")
    @classmethod
    def _lat(cls, v: Optional[float]) -> Optional[float]:
        check_finite(v, "Latitudinea este în afara zonei Rădăcini.")
        if v is not None and not 43.5 <= v <= 48.5:
            raise ValueError("Latitudinea este în afara zonei Rădăcini.")
        return v

    @field_validator("lng")
    @classmethod
    def _lng(cls, v: Optional[float]) -> Optional[float]:
        check_finite(v, "Longitudinea este în afara zonei Rădăcini.")
        if v is not None and not 20 <= v <= 30:
            raise ValueError("Longitudinea este în afara zonei Rădăcini.")
        return v

    @field_validator("area_m2")
    @classmethod
    def _area(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 100 <= v <= 10_000_000:
            raise ValueError("Suprafața trebuie să fie între 100 și 10 000 000 m².")
        return v

    @field_validator("water_sources")
    @classmethod
    def _water(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        if any(w not in WATER_SOURCE_IDS for w in v):
            raise ValueError("Sursă de apă necunoscută.")
        return list(dict.fromkeys(v))

    @field_validator("current_crops")
    @classmethod
    def _crops(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        crops = [c.strip() for c in v if c and c.strip()]
        if len(crops) > 20 or any(len(c) > 60 for c in crops):
            raise ValueError("Cel mult 20 de culturi, de maximum 60 de caractere fiecare.")
        return list(dict.fromkeys(crops))

    @field_validator("access", "description")
    @classmethod
    def _text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("Textul are cel mult 2000 de caractere.")
        return v

    @model_validator(mode="after")
    def _availability(self):
        if self.availability_from and self.availability_to and self.availability_to < self.availability_from:
            raise ValueError("Data de final a disponibilității este înaintea celei de început.")
        return self


class ParcelCreate(ParcelPatch):
    title: str
    county: str = COUNTY
    locality: str
    lat: float
    lng: float
    area_m2: int
    offer: OfferIn


def _first_name(name: Optional[str]) -> str:
    parts = (name or "").split()
    return parts[0] if parts else "Proprietar"


def _public_view(doc: dict, owner: dict) -> dict:
    out = serialize_doc(doc)
    for key in ("owner_user_id", "verification", "archived_at", "active_agreement_id"):
        out.pop(key, None)
    out["lat"] = round(out["lat"], 2)
    out["lng"] = round(out["lng"], 2)
    out["owner_name"] = _first_name(owner.get("name"))
    return out


async def _heal_completed(doc: dict) -> dict:
    """Terenuri rămase legate de un acord al cărui proiect e finalizat (date dinainte de eliberarea automată)
    sunt eliberate acum: fără `active_agreement_id`, suspendate."""
    aid = doc.get("active_agreement_id")
    if not aid:
        return doc
    done = await db.radacini_projects.find_one({"agreement_id": str(aid), "status": "completed"}, {"_id": 1})
    if not done:
        return doc
    await release_parcel(str(doc["_id"]), str(aid))
    return await db.radacini_parcels.find_one({"_id": doc["_id"]}) or doc


async def _owned_or_404(parcel_id: str, user: dict) -> dict:
    doc = await db.radacini_parcels.find_one({"_id": oid_or_404(parcel_id)})
    if not doc or doc.get("archived_at") or str(doc.get("owner_user_id")) != str(user["id"]):
        raise HTTPException(404, "Terenul nu există.")
    return await _heal_completed(doc)


def _ensure_no_active_agreement(doc: dict) -> None:
    if doc.get("active_agreement_id"):
        raise HTTPException(409, "Terenul are un acord activ.")


async def _transition(doc: dict, changes: dict, *, no_agreement: bool = False) -> dict:
    """Schimbare atomică: se aplică doar dacă terenul e încă în starea citită (și, opțional, fără acord activ);
    altfel 409."""
    flt: dict = {"_id": doc["_id"], "status": doc.get("status"), "archived_at": {"$exists": False}}
    if no_agreement:
        flt["active_agreement_id"] = {"$exists": False}
    changes = {**changes, "updated_at": now_iso()}
    res = await db.radacini_parcels.update_one(flt, {"$set": changes})
    if res.modified_count != 1:
        raise HTTPException(409, _CHANGED)
    return {**doc, **changes}


async def _is_agreement_party(parcel_id: str, user_id: str) -> bool:
    """Părțile unui acord semnat pe teren (proprietar/cultivator) văd terenul chiar dacă e suspendat."""
    ag = await db.radacini_agreements.find_one(
        {"parcel_id": parcel_id, "party_ids": user_id, "status": "signed"}, {"_id": 1}
    )
    return ag is not None


def _staff_in_scope(staff: dict, doc: dict) -> bool:
    """Managerii (și super-adminul) văd tot; operatorii fără zone la fel; ceilalți doar zonele lor."""
    return staff["role"] == "manager" or not staff["areas"] or doc.get("locality") in staff["areas"]


# Ordinea contează: /parcels/mine trebuie declarat înaintea lui /parcels/{parcel_id}.


@router.get("/parcels/mine")
async def list_my_parcels(user: dict = Depends(get_current_user)):
    docs = (
        await db.radacini_parcels.find({"owner_user_id": str(user["id"]), "archived_at": {"$exists": False}})
        .sort("updated_at", -1)
        .to_list(200)
    )
    return {"items": [serialize_doc(d) for d in docs]}


@router.get("/parcels")
async def list_public_parcels(
    locality: Optional[str] = None,
    model: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    if model is not None and model not in OFFER_MODEL_IDS:
        raise HTTPException(400, "Model de ofertă necunoscut.")
    flt: dict = {"status": "published", "archived_at": {"$exists": False}}
    if os.environ.get("RADACINI_MARK_DEMO", "").lower() != "true":
        flt["is_demo"] = {"$ne": True}  # datele de test/demo nu apar în lista publică
    if locality:
        flt["locality"] = locality
    if model:
        flt["offer.models"] = model
    total = await db.radacini_parcels.count_documents(flt)
    docs = await db.radacini_parcels.find(flt).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)
    owners = await load_owners(d.get("owner_user_id") for d in docs)
    items = [_public_view(d, owners.get(str(d.get("owner_user_id")), {})) for d in docs]
    return {"items": items, "total": total}


@router.post("/parcels")
async def create_parcel(body: ParcelCreate, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    member = await get_member_doc(uid)
    if not member:
        raise HTTPException(400, "Completează profilul înainte de a adăuga un teren.")
    now = now_iso()
    if "land" not in (member.get("interests") or []):
        await db.radacini_members.update_one(
            {"_id": member["_id"]}, {"$addToSet": {"interests": "land"}, "$set": {"updated_at": now}}
        )
    data = body.model_dump(mode="json")
    data["access"] = data["access"] or ""
    data["description"] = data["description"] or ""
    data["water_sources"] = data["water_sources"] or []
    data["current_crops"] = data["current_crops"] or []
    doc = mark_demo({
        "owner_user_id": uid,
        **data,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_parcels.insert_one(doc)
    return {"parcel": serialize_doc(doc)}


@router.get("/parcels/{parcel_id}")
async def get_parcel(parcel_id: str, user: Optional[dict] = Depends(get_optional_user)):
    doc = await db.radacini_parcels.find_one({"_id": oid_or_404(parcel_id)})
    if not doc or doc.get("archived_at"):
        raise HTTPException(404, "Terenul nu există.")
    owner_id = str(doc.get("owner_user_id"))
    if user and owner_id == str(user["id"]):
        return {"parcel": serialize_doc(doc)}
    if user:
        staff = await get_staff(user)
        if staff and _staff_in_scope(staff, doc):
            owner = (await load_owners([owner_id])).get(owner_id, {})
            out = serialize_doc(doc)
            out["owner_name"] = owner.get("name", "")
            out["owner_email"] = owner.get("email", "")
            return {"parcel": out}
    if doc.get("status") != "published" and not (user and await _is_agreement_party(str(doc["_id"]), str(user["id"]))):
        raise HTTPException(404, "Terenul nu există.")
    owner = (await load_owners([owner_id])).get(owner_id, {})
    return {"parcel": _public_view(doc, owner)}


@router.patch("/parcels/{parcel_id}")
async def patch_parcel(parcel_id: str, body: ParcelPatch, user: dict = Depends(get_current_user)):
    doc = await _owned_or_404(parcel_id, user)
    _ensure_no_active_agreement(doc)
    status = doc.get("status")
    if status not in ("draft", "rejected", "paused"):
        raise HTTPException(409, "Terenul poate fi editat doar în ciornă, respins sau suspendat.")
    changes = body.model_dump(mode="json", exclude_unset=True)
    for key in _NON_NULL_FIELDS:
        if key in changes and changes[key] is None:
            raise HTTPException(400, f"Câmpul {key} nu poate fi gol.")
    frm = changes.get("availability_from", doc.get("availability_from"))
    to = changes.get("availability_to", doc.get("availability_to"))
    if frm and to and to < frm:
        raise HTTPException(400, "Data de final a disponibilității este înaintea celei de început.")
    if not changes:
        return {"parcel": serialize_doc(doc)}
    if status == "rejected":
        changes["status"] = "draft"
    elif status == "paused" and any(k in changes and changes[k] != doc.get(k) for k in _CONTENT_FIELDS):
        # Un teren suspendat a fost deja verificat; dacă i se schimbă conținutul sau locația, trebuie reverificat.
        changes["status"] = "draft"
    doc = await _transition(doc, changes, no_agreement=True)
    return {"parcel": serialize_doc(doc)}


@router.post("/parcels/{parcel_id}/submit")
async def submit_parcel(parcel_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "trimiterea terenului la verificare")
    doc = await _owned_or_404(parcel_id, user)
    if doc.get("status") not in ("draft", "rejected"):
        raise HTTPException(409, "Terenul nu poate fi trimis la verificare în starea actuală.")
    doc = await _transition(doc, {"status": "pending_verification"}, no_agreement=True)
    await emit(
        "radacini.parcel_submitted",
        actor=user,
        payload={"parcel_id": str(doc["_id"]), "locality": doc.get("locality")},
    )
    return {"parcel": serialize_doc(doc)}


@router.post("/parcels/{parcel_id}/pause")
async def pause_parcel(parcel_id: str, user: dict = Depends(get_current_user)):
    doc = await _owned_or_404(parcel_id, user)
    if doc.get("status") != "published":
        raise HTTPException(409, "Doar un teren publicat poate fi suspendat.")
    doc = await _transition(doc, {"status": "paused"})
    return {"parcel": serialize_doc(doc)}


@router.post("/parcels/{parcel_id}/resume")
async def resume_parcel(parcel_id: str, user: dict = Depends(get_current_user)):
    doc = await _owned_or_404(parcel_id, user)
    _ensure_no_active_agreement(doc)
    if doc.get("status") != "paused":
        raise HTTPException(409, "Doar un teren suspendat poate fi reluat.")
    doc = await _transition(doc, {"status": "published"}, no_agreement=True)
    return {"parcel": serialize_doc(doc)}


@router.delete("/parcels/{parcel_id}")
async def delete_parcel(parcel_id: str, user: dict = Depends(get_current_user)):
    block_in_impersonation(user, "ștergerea terenului")
    doc = await _owned_or_404(parcel_id, user)
    _ensure_no_active_agreement(doc)
    if doc.get("status") == "pending_verification":
        raise HTTPException(409, "Terenul așteaptă verificarea și nu poate fi șters acum.")
    await _transition(doc, {"archived_at": now_iso()}, no_agreement=True)
    return {"ok": True}
