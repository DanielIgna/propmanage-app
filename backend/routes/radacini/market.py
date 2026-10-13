"""Piața locală: anunțuri, rezervări (plata la ridicare sau schimb) și ratingul vânzătorilor.

Fără plăți online și fără monedă internă: platforma consemnează doar rezervarea.
`quantity_available` se modifică exclusiv prin actualizări condiționate cu `$inc`
(confirmarea scade, anularea / neprezentarea returnează), ca să nu existe supravânzare.
"""
import logging
import re
import statistics
import unicodedata
from datetime import date as _Date  # nu denumim câmpuri `date` în modele pydantic
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from .bridge import db, emit, get_current_user, serialize_doc
from .common import RadaciniRoute, mark_demo, now_iso, oid_or_404, safe_notify
from .constants import (
    LISTING_CATEGORY_IDS,
    LISTING_MODE_IDS,
    LISTING_UNIT_IDS,
    LOCALITIES,
    RESERVATION_MODE_IDS,
)
from .members import get_member_doc
from .projects import member_role, today_str

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

EPS = 1e-6
MAX_PRICE = 10_000
MAX_QTY = 1_000_000_000
ACTIVE_RES = ("requested", "confirmed")
RESERVATIONS_LINK = "/radacini/rezervari"


def listing_link(listing_id) -> str:
    return f"/radacini/piata/{listing_id}"


def _qty(v) -> float:
    return round(float(v), 3)


# ----------------------------------------------------------------- produs și preț de referință

def product_key(text: str) -> str:
    """Cheia produsului: litere mici, fără diacritice, spații comprimate."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def median_price(prices: list[float]) -> Optional[float]:
    """Mediana prețurilor; `None` dacă există mai puțin de 2 prețuri."""
    if len(prices) < 2:
        return None
    return round(float(statistics.median(prices)), 2)


async def reference_prices(listings: list[dict]) -> dict:
    """{(product_key, unit): mediană|None} pentru anunțurile date — o singură interogare."""
    keys = sorted({l["product_key"] for l in listings if l.get("product_key")})
    if not keys:
        return {}
    rows = await db.radacini_listings.find(
        {"status": "active", "quantity_available": {"$gt": 0}, "product_key": {"$in": keys}},
        {"product_key": 1, "unit": 1, "price_ron_per_unit": 1},
    ).to_list(20000)
    groups: dict = {}
    for r in rows:
        price = r.get("price_ron_per_unit")
        if isinstance(price, (int, float)) and price > 0:
            groups.setdefault((r["product_key"], r["unit"]), []).append(float(price))
    wanted = {(l["product_key"], l["unit"]) for l in listings}
    return {k: median_price(groups.get(k, [])) for k in wanted}


async def seller_ratings(seller_ids: list[str]) -> dict:
    """{seller_user_id: {avg, count}} dintr-o singură interogare."""
    ids = sorted({s for s in seller_ids if s})
    if not ids:
        return {}
    rows = await db.radacini_reservations.find(
        {"seller_user_id": {"$in": ids}, "rating": {"$exists": True}},
        {"seller_user_id": 1, "rating": 1},
    ).to_list(50000)
    return _aggregate_ratings(rows)


def _aggregate_ratings(rows: list[dict]) -> dict:
    acc: dict = {}
    for r in rows:
        if isinstance(r.get("rating"), (int, float)):
            acc.setdefault(r["seller_user_id"], []).append(r["rating"])
    return {sid: {"avg": round(sum(v) / len(v), 2), "count": len(v)} for sid, v in acc.items()}


# ----------------------------------------------------------------- scheme

class _ListingCommon(BaseModel):
    @field_validator("product", check_fields=False)
    @classmethod
    def _v_product(cls, v):
        if v is None:
            return None
        v = " ".join(v.split())
        if not 2 <= len(v) <= 80:
            raise ValueError("Produsul trebuie să aibă între 2 și 80 de caractere.")
        return v

    @field_validator("category", check_fields=False)
    @classmethod
    def _v_category(cls, v):
        if v is not None and v not in LISTING_CATEGORY_IDS:
            raise ValueError("Categorie necunoscută.")
        return v

    @field_validator("unit", check_fields=False)
    @classmethod
    def _v_unit(cls, v):
        if v is not None and v not in LISTING_UNIT_IDS:
            raise ValueError("Unitate necunoscută.")
        return v

    @field_validator("quantity_total", check_fields=False)
    @classmethod
    def _v_quantity(cls, v):
        if v is not None and not 0 < v <= MAX_QTY:
            raise ValueError("Cantitatea trebuie să fie un număr pozitiv.")
        return v

    @field_validator("price_ron_per_unit", check_fields=False)
    @classmethod
    def _v_price(cls, v):
        if v is not None and not 0 < v <= MAX_PRICE:
            raise ValueError("Prețul trebuie să fie între 0 și 10 000 RON.")
        return v

    @field_validator("mode", check_fields=False)
    @classmethod
    def _v_mode(cls, v):
        if v is not None and v not in LISTING_MODE_IDS:
            raise ValueError("Mod necunoscut.")
        return v

    @field_validator("exchange_for", check_fields=False)
    @classmethod
    def _v_exchange(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not 3 <= len(v) <= 300:
            raise ValueError("Ce primești în schimb trebuie să aibă între 3 și 300 de caractere.")
        return v

    @field_validator("locality", check_fields=False)
    @classmethod
    def _v_locality(cls, v):
        if v is not None and v not in LOCALITIES:
            raise ValueError("Localitate necunoscută.")
        return v

    @field_validator("pickup_details", check_fields=False)
    @classmethod
    def _v_pickup(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not 3 <= len(v) <= 300:
            raise ValueError("Detaliile de ridicare trebuie să aibă între 3 și 300 de caractere.")
        return v


class ListingIn(_ListingCommon):
    product: str
    category: str
    unit: str
    quantity_total: float
    price_ron_per_unit: Optional[float] = None
    mode: str
    exchange_for: Optional[str] = None
    locality: str
    pickup_details: str
    available_until: Optional[_Date] = None
    project_id: Optional[str] = None


class ListingPatch(_ListingCommon):
    product: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    quantity_total: Optional[float] = None
    price_ron_per_unit: Optional[float] = None
    mode: Optional[str] = None
    exchange_for: Optional[str] = None
    locality: Optional[str] = None
    pickup_details: Optional[str] = None
    available_until: Optional[_Date] = None
    project_id: Optional[str] = None


class ReservationIn(BaseModel):
    quantity: float
    mode: str
    exchange_offer: Optional[str] = None
    message: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def _quantity(cls, v: float) -> float:
        if not 0 < v <= MAX_QTY:
            raise ValueError("Cantitatea trebuie să fie un număr pozitiv.")
        return v

    @field_validator("mode")
    @classmethod
    def _mode(cls, v: str) -> str:
        if v not in RESERVATION_MODE_IDS:
            raise ValueError("Modul rezervării este necunoscut.")
        return v

    @field_validator("exchange_offer")
    @classmethod
    def _offer(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not 3 <= len(v) <= 300:
            raise ValueError("Oferta de schimb trebuie să aibă între 3 și 300 de caractere.")
        return v

    @field_validator("message")
    @classmethod
    def _message(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 300:
            raise ValueError("Mesajul are cel mult 300 de caractere.")
        return v or None


class RatingIn(BaseModel):
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def _rating(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError("Evaluarea trebuie să fie între 1 și 5.")
        return v

    @field_validator("comment")
    @classmethod
    def _comment(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 300:
            raise ValueError("Comentariul are cel mult 300 de caractere.")
        return v or None


# ----------------------------------------------------------------- helpere anunțuri

def _check_mode_fields(data: dict) -> None:
    mode = data.get("mode")
    if mode in ("sale", "both") and data.get("price_ron_per_unit") is None:
        raise HTTPException(400, "Prețul pe unitate este obligatoriu pentru vânzare.")
    if mode in ("exchange", "both") and not data.get("exchange_for"):
        raise HTTPException(400, "Spune ce ai primi în schimb.")


async def _check_project(project_id: Optional[str], uid: str) -> None:
    if not project_id:
        return
    if not (isinstance(project_id, str) and len(project_id) == 24 and ObjectId.is_valid(project_id)):
        raise HTTPException(400, "Proiectul ales nu există.")
    project = await db.radacini_projects.find_one({"_id": ObjectId(project_id)})
    if not project or not member_role(project, uid):
        raise HTTPException(400, "Poți lega un anunț doar de un proiect în care ești membru.")


async def _require_profile(user: dict, action: str) -> None:
    if not await get_member_doc(user["id"]):
        raise HTTPException(400, f"Completează profilul înainte de {action}.")


async def _present_listings(docs: list[dict], uid: str, with_pending: bool = False) -> list[dict]:
    """Anunțuri pregătite pentru răspuns: preț de referință și rating, fără interogări pe element."""
    prices = await reference_prices(docs)
    ratings = await seller_ratings([d["seller_user_id"] for d in docs])
    pending: dict = {}
    if with_pending and docs:
        rows = await db.radacini_reservations.find(
            {"listing_id": {"$in": [str(d["_id"]) for d in docs]}, "status": "requested"}, {"listing_id": 1}
        ).to_list(20000)
        for r in rows:
            pending[r["listing_id"]] = pending.get(r["listing_id"], 0) + 1
    out = []
    for d in docs:
        item = serialize_doc(d)
        item["quantity_total"] = _qty(d["quantity_total"])
        item["quantity_available"] = max(_qty(d["quantity_available"]), 0.0)
        item["reference_price"] = prices.get((d["product_key"], d["unit"]))
        item["seller_rating"] = ratings.get(d["seller_user_id"], {"avg": None, "count": 0})
        item["is_mine"] = d["seller_user_id"] == uid
        if with_pending:
            item["pending_reservations"] = pending.get(str(d["_id"]), 0)
        out.append(item)
    return out


async def _load_listing(listing_id: str) -> dict:
    doc = await db.radacini_listings.find_one({"_id": oid_or_404(listing_id)})
    if not doc:
        raise HTTPException(404, "Anunțul nu există.")
    return doc


async def _load_own_listing(listing_id: str, user: dict) -> dict:
    doc = await _load_listing(listing_id)
    if doc["seller_user_id"] != str(user["id"]):
        raise HTTPException(403, "Doar vânzătorul poate modifica anunțul.")
    return doc


# ----------------------------------------------------------------- rute: anunțuri

@router.get("/listings")
async def list_listings(
    locality: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    mode: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    flt: dict = {
        "status": "active",
        "quantity_available": {"$gt": 0},
        # Anunțurile expirate (available_until trecut) nu mai apar în piață.
        "$or": [{"available_until": None}, {"available_until": {"$gte": today_str()}}],
    }
    if locality:
        flt["locality"] = locality
    if category:
        flt["category"] = category
    if mode:
        if mode not in LISTING_MODE_IDS:
            raise HTTPException(400, "Mod necunoscut.")
        flt["mode"] = "both" if mode == "both" else {"$in": [mode, "both"]}
    key = product_key(q) if q else ""
    if key:
        flt["product_key"] = {"$regex": re.escape(key)}
    total = await db.radacini_listings.count_documents(flt)
    docs = await db.radacini_listings.find(flt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"items": await _present_listings(docs, str(user["id"])), "total": total}


@router.get("/listings/mine")
async def my_listings(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    docs = await db.radacini_listings.find({"seller_user_id": uid}).sort("created_at", -1).to_list(500)
    return {"items": await _present_listings(docs, uid, with_pending=True)}


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    doc = await _load_listing(listing_id)
    item = (await _present_listings([doc], uid))[0]
    mine = await db.radacini_reservations.find_one(
        {"listing_id": str(doc["_id"]), "buyer_user_id": uid, "status": {"$in": list(ACTIVE_RES)}}
    )
    item["my_reservation"] = serialize_doc(mine) if mine else None
    return {"listing": item}


@router.post("/listings")
async def create_listing(body: ListingIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    await _require_profile(user, "a publica un anunț")
    data = body.model_dump(mode="json")
    _check_mode_fields(data)
    if data.get("available_until") and data["available_until"] < today_str():
        raise HTTPException(400, "Data limită nu poate fi în trecut.")
    await _check_project(data.get("project_id"), uid)
    qty = _qty(body.quantity_total)
    now = now_iso()
    doc = mark_demo({
        "seller_user_id": uid,
        "seller_name": user.get("name") or "",
        "product": data["product"],
        "product_key": product_key(data["product"]),
        "category": data["category"],
        "unit": data["unit"],
        "quantity_total": qty,
        "quantity_available": qty,
        "price_ron_per_unit": data.get("price_ron_per_unit") if data["mode"] != "exchange" else None,
        "mode": data["mode"],
        "exchange_for": data.get("exchange_for") if data["mode"] != "sale" else None,
        "locality": data["locality"],
        "pickup_details": data["pickup_details"],
        "available_until": data.get("available_until"),
        "project_id": data.get("project_id"),
        "status": "active",
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_listings.insert_one(doc)
    await emit(
        "radacini.listing_created",
        actor=user,
        payload={"listing_id": str(doc["_id"]), "product_key": doc["product_key"], "locality": doc["locality"]},
    )
    return {"listing": (await _present_listings([doc], uid))[0]}


@router.patch("/listings/{listing_id}")
async def patch_listing(listing_id: str, body: ListingPatch, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    doc = await _load_own_listing(listing_id, user)
    if doc.get("status") != "active":
        raise HTTPException(409, "Anunțul este închis.")
    changes = body.model_dump(mode="json", exclude_unset=True)
    for key in ("product", "category", "unit", "quantity_total", "mode", "locality", "pickup_details"):
        if key in changes and changes[key] is None:
            raise HTTPException(400, f"Câmpul {key} nu poate fi gol.")
    merged = {**doc, **changes}
    _check_mode_fields(merged)
    if changes.get("available_until") and changes["available_until"] < today_str():
        raise HTTPException(400, "Data limită nu poate fi în trecut.")
    if changes.get("project_id"):
        await _check_project(changes["project_id"], uid)
    reserved = _qty(doc["quantity_total"] - doc["quantity_available"])
    if "unit" in changes and changes["unit"] != doc["unit"] and reserved > EPS:
        raise HTTPException(409, "Unitatea nu se mai poate schimba: există cantitate rezervată.")
    sets = {k: v for k, v in changes.items() if k != "quantity_total"}
    if "product" in sets:
        sets["product_key"] = product_key(sets["product"])
    if merged["mode"] == "exchange":
        sets["price_ron_per_unit"] = None
    if merged["mode"] == "sale":
        sets["exchange_for"] = None
    sets["updated_at"] = now_iso()
    flt: dict = {"_id": doc["_id"], "status": "active"}
    update: dict = {"$set": sets}
    if "quantity_total" in changes:
        new_total = _qty(changes["quantity_total"])
        if new_total < reserved - EPS:
            raise HTTPException(400, "Cantitatea totală nu poate scădea sub cantitatea deja rezervată și confirmată.")
        delta = _qty(new_total - doc["quantity_total"])
        if abs(delta) > EPS:
            update["$inc"] = {"quantity_total": delta, "quantity_available": delta}
            if delta < 0:
                flt["quantity_available"] = {"$gte": -delta - EPS}
    res = await db.radacini_listings.update_one(flt, update)
    if res.modified_count != 1:
        fresh = await db.radacini_listings.find_one({"_id": doc["_id"]})
        if not fresh or fresh.get("status") != "active":
            raise HTTPException(409, "Anunțul este închis.")
        raise HTTPException(409, "Cantitatea rezervată s-a schimbat între timp. Reîncarcă pagina.")
    fresh = await db.radacini_listings.find_one({"_id": doc["_id"]}) or doc
    await emit("radacini.listing_updated", actor=user, payload={"listing_id": listing_id})
    return {"listing": (await _present_listings([fresh], uid))[0]}


@router.post("/listings/{listing_id}/close")
async def close_listing(listing_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    doc = await _load_own_listing(listing_id, user)
    now = now_iso()
    res = await db.radacini_listings.update_one(
        {"_id": doc["_id"], "status": "active"}, {"$set": {"status": "closed", "updated_at": now}}
    )
    if res.modified_count != 1:
        raise HTTPException(409, "Anunțul este deja închis.")
    pending = await db.radacini_reservations.find({"listing_id": listing_id, "status": "requested"}).to_list(1000)
    for r in pending:
        upd = await db.radacini_reservations.update_one(
            {"_id": r["_id"], "status": "requested"},
            {"$set": {"status": "cancelled", "cancel_reason": "listing_closed", "updated_at": now}},
        )
        if upd.modified_count == 1:
            await safe_notify(
                r["buyer_user_id"],
                "Anunț închis",
                f"Anunțul „{doc['product']}” a fost închis, iar rezervarea ta a fost anulată.",
                link=listing_link(listing_id),
                type_="market",
            )
    await emit("radacini.listing_closed", actor=user, payload={"listing_id": listing_id, "cancelled": len(pending)})
    fresh = {**doc, "status": "closed", "updated_at": now}
    return {"listing": (await _present_listings([fresh], uid))[0]}


# ----------------------------------------------------------------- helpere rezervări

async def _load_reservation(reservation_id: str, user: dict) -> tuple[dict, dict, str]:
    """(rezervare, anunț, 'buyer'|'seller'); 404 pentru cei care nu sunt părți."""
    uid = str(user["id"])
    res = await db.radacini_reservations.find_one({"_id": oid_or_404(reservation_id)})
    if not res or uid not in (res.get("buyer_user_id"), res.get("seller_user_id")):
        raise HTTPException(404, "Rezervarea nu există.")
    listing = await db.radacini_listings.find_one({"_id": ObjectId(res["listing_id"])}) or {}
    return res, listing, "buyer" if res["buyer_user_id"] == uid else "seller"


def _res_view(res: dict, listing: Optional[dict], side: str) -> dict:
    out = serialize_doc(res)
    out["quantity"] = _qty(res["quantity"])
    out["listing_product"] = (listing or {}).get("product", "")
    out["listing_unit"] = (listing or {}).get("unit", "")
    out["listing_status"] = (listing or {}).get("status")
    out["counterpart_name"] = (res.get("seller_name") if side == "buyer" else res.get("buyer_name")) or ""
    out["side"] = side
    return out


async def _set_status(res: dict, from_status: str, to_status: str, extra: Optional[dict] = None) -> dict:
    """Tranziție condiționată (409 dacă starea s-a schimbat). Întoarce documentul actualizat."""
    now = now_iso()
    fields = {"status": to_status, "updated_at": now, **(extra or {})}
    upd = await db.radacini_reservations.update_one({"_id": res["_id"], "status": from_status}, {"$set": fields})
    if upd.modified_count != 1:
        raise HTTPException(409, "Starea rezervării s-a schimbat între timp. Reîncarcă pagina.")
    return {**res, **fields}


async def _return_quantity(listing_id: str, qty: float) -> None:
    await db.radacini_listings.update_one(
        {"_id": ObjectId(listing_id)}, {"$inc": {"quantity_available": _qty(qty)}, "$set": {"updated_at": now_iso()}}
    )


async def _notify_other(res: dict, side: str, title: str, text: str, event: str, user: dict, listing_id: str) -> None:
    other = res["seller_user_id"] if side == "buyer" else res["buyer_user_id"]
    await safe_notify(other, title, text, link=RESERVATIONS_LINK, type_="market")
    await emit(event, actor=user, payload={"reservation_id": str(res["_id"]), "listing_id": listing_id})


# ----------------------------------------------------------------- rute: rezervări

@router.post("/listings/{listing_id}/reservations")
async def create_reservation(listing_id: str, body: ReservationIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    listing = await _load_listing(listing_id)
    if listing["seller_user_id"] == uid:
        raise HTTPException(403, "Nu poți rezerva din propriul anunț.")
    await _require_profile(user, "a rezerva")
    if listing.get("status") != "active":
        raise HTTPException(409, "Anunțul este închis.")
    if listing.get("available_until") and listing["available_until"] < today_str():
        raise HTTPException(409, "Anunțul a expirat.")
    qty = _qty(body.quantity)
    if qty <= 0 or qty > listing["quantity_available"] + EPS:
        raise HTTPException(400, "Cantitatea cerută depășește cantitatea disponibilă.")
    allowed = {"sale": ("cash_on_pickup",), "exchange": ("exchange",), "both": ("cash_on_pickup", "exchange")}
    if body.mode not in allowed[listing["mode"]]:
        raise HTTPException(400, "Anunțul nu acceptă acest mod de rezervare.")
    if body.mode == "exchange" and not body.exchange_offer:
        raise HTTPException(400, "Spune ce oferi în schimb.")
    dup = await db.radacini_reservations.find_one(
        {"listing_id": listing_id, "buyer_user_id": uid, "status": {"$in": list(ACTIVE_RES)}}
    )
    if dup:
        raise HTTPException(409, "Ai deja o rezervare activă pentru acest anunț.")
    now = now_iso()
    doc = mark_demo({
        "listing_id": listing_id,
        "seller_user_id": listing["seller_user_id"],
        "seller_name": listing.get("seller_name", ""),
        "buyer_user_id": uid,
        "buyer_name": user.get("name") or "",
        "quantity": qty,
        "mode": body.mode,
        "exchange_offer": body.exchange_offer if body.mode == "exchange" else None,
        "message": body.message,
        "status": "requested",
        "created_at": now,
        "updated_at": now,
    })
    await db.radacini_reservations.insert_one(doc)
    await safe_notify(
        listing["seller_user_id"],
        "Rezervare nouă",
        f"{doc['buyer_name'] or 'Un membru'} a cerut {qty} {listing['unit']} din „{listing['product']}”.",
        link=RESERVATIONS_LINK,
        type_="market",
    )
    await emit(
        "radacini.reservation_requested",
        actor=user,
        payload={"reservation_id": str(doc["_id"]), "listing_id": listing_id, "quantity": qty},
    )
    return {"reservation": _res_view(doc, listing, "buyer")}


@router.get("/reservations/mine")
async def my_reservations(role: str = "buyer", user: dict = Depends(get_current_user)):
    if role not in ("buyer", "seller"):
        raise HTTPException(400, "Rolul trebuie să fie buyer sau seller.")
    uid = str(user["id"])
    docs = await db.radacini_reservations.find({f"{role}_user_id": uid}).sort("created_at", -1).to_list(500)
    ids = sorted({d["listing_id"] for d in docs})
    listings: dict = {}
    if ids:
        rows = await db.radacini_listings.find({"_id": {"$in": [ObjectId(i) for i in ids]}}).to_list(len(ids))
        listings = {str(r["_id"]): r for r in rows}
    return {"items": [_res_view(d, listings.get(d["listing_id"]), role) for d in docs]}


@router.post("/reservations/{reservation_id}/confirm")
async def confirm_reservation(reservation_id: str, user: dict = Depends(get_current_user)):
    res, listing, side = await _load_reservation(reservation_id, user)
    if side != "seller":
        raise HTTPException(403, "Doar vânzătorul poate confirma rezervarea.")
    if res["status"] != "requested":
        raise HTTPException(409, "Rezervarea nu mai poate fi confirmată.")
    qty = _qty(res["quantity"])
    # Scădere atomică: reușește doar dacă anunțul e activ și are destulă cantitate.
    dec = await db.radacini_listings.update_one(
        {"_id": ObjectId(res["listing_id"]), "status": "active", "quantity_available": {"$gte": qty - EPS}},
        {"$inc": {"quantity_available": -qty}, "$set": {"updated_at": now_iso()}},
    )
    if dec.modified_count != 1:
        fresh = await db.radacini_listings.find_one({"_id": ObjectId(res["listing_id"])})
        if not fresh or fresh.get("status") != "active":
            raise HTTPException(409, "Anunțul este închis.")
        raise HTTPException(409, "Cantitatea disponibilă nu mai este suficientă.")
    try:
        res = await _set_status(res, "requested", "confirmed")
    except HTTPException:
        await _return_quantity(res["listing_id"], qty)
        raise
    await _notify_other(
        res, side, "Rezervare confirmată",
        f"Rezervarea ta pentru „{listing.get('product', '')}” a fost confirmată. Vezi detaliile de ridicare.",
        "radacini.reservation_confirmed", user, res["listing_id"],
    )
    fresh_listing = await db.radacini_listings.find_one({"_id": ObjectId(res["listing_id"])}) or listing
    return {"reservation": _res_view(res, fresh_listing, side)}


@router.post("/reservations/{reservation_id}/decline")
async def decline_reservation(reservation_id: str, user: dict = Depends(get_current_user)):
    res, listing, side = await _load_reservation(reservation_id, user)
    if side != "seller":
        raise HTTPException(403, "Doar vânzătorul poate refuza rezervarea.")
    res = await _set_status(res, "requested", "declined")
    await _notify_other(
        res, side, "Rezervare refuzată",
        f"Rezervarea ta pentru „{listing.get('product', '')}” a fost refuzată.",
        "radacini.reservation_declined", user, res["listing_id"],
    )
    return {"reservation": _res_view(res, listing, side)}


@router.post("/reservations/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: str, user: dict = Depends(get_current_user)):
    res, listing, side = await _load_reservation(reservation_id, user)
    status = res["status"]
    if status not in ACTIVE_RES:
        raise HTTPException(409, "Rezervarea nu mai poate fi anulată.")
    if side == "seller" and status != "confirmed":
        raise HTTPException(403, "Vânzătorul poate anula doar rezervările confirmate; refuză cererea nouă.")
    res = await _set_status(res, status, "cancelled", {"cancelled_by": side})
    if status == "confirmed":
        await _return_quantity(res["listing_id"], res["quantity"])
    await _notify_other(
        res, side, "Rezervare anulată",
        f"Rezervarea pentru „{listing.get('product', '')}” a fost anulată de {'cumpărător' if side == 'buyer' else 'vânzător'}.",
        "radacini.reservation_cancelled", user, res["listing_id"],
    )
    return {"reservation": _res_view(res, listing, side)}


@router.post("/reservations/{reservation_id}/picked-up")
async def reservation_picked_up(reservation_id: str, user: dict = Depends(get_current_user)):
    res, listing, side = await _load_reservation(reservation_id, user)
    if side != "seller":
        raise HTTPException(403, "Doar vânzătorul poate marca predarea.")
    res = await _set_status(res, "confirmed", "picked_up")
    await _notify_other(
        res, side, "Produs ridicat",
        f"Ridicarea pentru „{listing.get('product', '')}” a fost consemnată. Poți evalua vânzătorul.",
        "radacini.reservation_picked_up", user, res["listing_id"],
    )
    return {"reservation": _res_view(res, listing, side)}


@router.post("/reservations/{reservation_id}/no-show")
async def reservation_no_show(reservation_id: str, user: dict = Depends(get_current_user)):
    res, listing, side = await _load_reservation(reservation_id, user)
    if side != "seller":
        raise HTTPException(403, "Doar vânzătorul poate marca neprezentarea.")
    res = await _set_status(res, "confirmed", "no_show")
    await _return_quantity(res["listing_id"], res["quantity"])
    await _notify_other(
        res, side, "Neprezentare consemnată",
        f"Pentru rezervarea la „{listing.get('product', '')}” s-a consemnat că nu te-ai prezentat.",
        "radacini.reservation_no_show", user, res["listing_id"],
    )
    return {"reservation": _res_view(res, listing, side)}


@router.post("/reservations/{reservation_id}/rate")
async def rate_reservation(reservation_id: str, body: RatingIn, user: dict = Depends(get_current_user)):
    res, listing, side = await _load_reservation(reservation_id, user)
    if side != "buyer":
        raise HTTPException(403, "Doar cumpărătorul poate evalua vânzătorul.")
    if res["status"] != "picked_up":
        raise HTTPException(409, "Poți evalua doar o rezervare ridicată.")
    now = now_iso()
    fields = {"rating": body.rating, "rating_comment": body.comment, "rated_at": now, "updated_at": now}
    upd = await db.radacini_reservations.update_one(
        {"_id": res["_id"], "status": "picked_up", "rating": {"$exists": False}}, {"$set": fields}
    )
    if upd.modified_count != 1:
        raise HTTPException(409, "Rezervarea a fost deja evaluată.")
    await safe_notify(
        res["seller_user_id"],
        "Evaluare primită",
        f"Ai primit {body.rating}/5 pentru „{listing.get('product', '')}”.",
        link=RESERVATIONS_LINK,
        type_="market",
    )
    await emit(
        "radacini.reservation_rated",
        actor=user,
        payload={"reservation_id": reservation_id, "listing_id": res["listing_id"], "rating": body.rating},
    )
    return {"reservation": _res_view({**res, **fields}, listing, side)}


@router.get("/sellers/{user_id}/rating")
async def seller_rating(user_id: str, user: dict = Depends(get_current_user)):
    rows = await db.radacini_reservations.find(
        {"seller_user_id": user_id, "rating": {"$exists": True}}, {"seller_user_id": 1, "rating": 1}
    ).to_list(50000)
    agg = _aggregate_ratings(rows).get(user_id)
    return agg or {"avg": None, "count": 0}
