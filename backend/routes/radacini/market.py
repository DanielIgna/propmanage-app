"""Piața locală: anunțuri, rezervări (plata la ridicare sau schimb) și ratingul vânzătorilor.

Fără plăți online și fără monedă internă: platforma consemnează doar rezervarea.
`quantity_available` se modifică exclusiv prin actualizări condiționate cu `$inc`
(confirmarea scade, anularea / neprezentarea returnează), ca să nu existe supravânzare.
"""
import logging
import math
import os
import re
import statistics
import unicodedata
from datetime import date as _Date  # nu denumim câmpuri `date` în modele pydantic
from typing import Iterable, Optional

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
    LOCALITY_CENTERS,
    MAX_LISTING_PRICE_RON,
    MAX_LISTING_QTY,
    RESERVATION_MODE_IDS,
)
from .geo import haversine_km
from .members import get_member_doc
from .projects import member_role, today_str

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

EPS = 1e-6
MAX_PRICE = MAX_LISTING_PRICE_RON
MAX_QTY = MAX_LISTING_QTY
ACTIVE_RES = ("requested", "confirmed")
RESERVATIONS_LINK = "/radacini/rezervari"
IN_CHUNK = 100  # pgmongo traduce `$in` în SQL doar până la 200 de valori; peste, încarcă toată colecția
REF_SAMPLE = 1000  # cele mai recente anunțuri luate în calcul pentru mediana unui produs
RATING_SCAN_LIMIT = 20000  # doar la calculul inițial al statisticilor unui vânzător
MAX_TOKENS = 40  # intrări `product_tokens` per anunț
MAX_QUERY_TOKENS = 5
MAX_CLOSE_NOTIFY = 200  # notificări trimise la închiderea unui anunț
LIST_CAP = 500
QTY_MESSAGE = "Cantitatea trebuie să fie între 0,001 și 1 000 000."
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def listing_link(listing_id) -> str:
    return f"/radacini/piata/{listing_id}"


def _qty(v) -> float:
    return round(float(v), 3)


def _checked_qty(v: float) -> float:
    """Cantitate finită, rotunjită la 0,001 și validată DUPĂ rotunjire (0,0004 devine 0 → respinsă)."""
    if not math.isfinite(v):
        raise ValueError(QTY_MESSAGE)
    r = _qty(v)
    if not 0 < r <= MAX_QTY:
        raise ValueError(QTY_MESSAGE)
    return r


def _chunks(items: list, size: int = IN_CHUNK) -> Iterable[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _public_filter() -> dict:
    """Anunțurile demo (`is_demo`) nu apar în piața publică decât când serverul le marchează chiar el
    (RADACINI_MARK_DEMO=true, mediu local de test)."""
    if os.environ.get("RADACINI_MARK_DEMO", "").lower() == "true":
        return {}
    return {"is_demo": {"$ne": True}}


def _first_name(name) -> str:
    parts = str(name or "").split()
    return parts[0] if parts else ""


def _expired(listing: dict) -> bool:
    until = listing.get("available_until")
    return bool(until) and until < today_str()


# ----------------------------------------------------------------- produs și preț de referință

def product_key(text: str) -> str:
    """Cheia produsului: litere mici, fără diacritice, spații comprimate."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def product_tokens(text: str) -> list[str]:
    """Cuvintele produsului (normalizate cu `product_key`) + prefixele de cel puțin 3 litere ale fiecărui cuvânt,
    cel mult `MAX_TOKENS`. Cuvintele întregi vin primele, apoi prefixele în ordinea lungimii, ca tăierea la
    limită să păstreze prefixele scurte (cele mai folosite la căutare)."""
    words = list(dict.fromkeys(_TOKEN_RE.findall(product_key(text))))
    out = list(words)
    longest = max((len(w) for w in words), default=0)
    for n in range(3, longest):
        out.extend(w[:n] for w in words if len(w) > n)
    return list(dict.fromkeys(out))[:MAX_TOKENS]


def search_tokens(q: str) -> list[str]:
    """Cuvintele căutării care se potrivesc cu `product_tokens` (toate trebuie să existe în anunț).
    Cuvintele de sub 3 litere se ignoră, cu excepția cazului în care sunt singurele."""
    words = list(dict.fromkeys(_TOKEN_RE.findall(product_key((q or "")[:200]))))
    long_words = [w for w in words if len(w) >= 3]
    return (long_words or words[:1])[:MAX_QUERY_TOKENS]


def median_price(prices: list[float]) -> Optional[float]:
    """Mediana prețurilor; `None` dacă există mai puțin de 2 prețuri."""
    if len(prices) < 2:
        return None
    return round(float(statistics.median(prices)), 2)


async def reference_prices(listings: list[dict]) -> dict:
    """{(product_key, unit): mediană|None} pentru anunțurile date. Interogări cu proiecție și limită explicită
    (cele mai recente `REF_SAMPLE` anunțuri per grup de chei), nu scanări ale întregii colecții."""
    keys = sorted({l["product_key"] for l in listings if l.get("product_key")})
    if not keys:
        return {}
    groups: dict = {}
    for chunk in _chunks(keys):
        rows = await db.radacini_listings.find(
            {
                "status": "active",
                "quantity_available": {"$gte": EPS},
                "product_key": {"$in": chunk},
                **_public_filter(),
            },
            {"product_key": 1, "unit": 1, "price_ron_per_unit": 1},
        ).sort("created_at", -1).limit(REF_SAMPLE).to_list(REF_SAMPLE)
        for r in rows:
            price = r.get("price_ron_per_unit")
            if isinstance(price, (int, float)) and price > 0:
                groups.setdefault((r["product_key"], r["unit"]), []).append(float(price))
    wanted = {(l["product_key"], l["unit"]) for l in listings}
    return {k: median_price(groups.get(k, [])) for k in wanted}


# ----------------------------------------------------------------- rating vânzători (agregat)
# `radacini_seller_stats` {seller_user_id, rating_sum, rating_count}: actualizat cu `$inc` la fiecare evaluare,
# ca citirea ratingului să nu scaneze rezervările. Lipsa documentului se acoperă o singură dată, din rezervări.

def _rating_view(total: float, count: int) -> dict:
    return {"avg": round(total / count, 2) if count else None, "count": int(count)}


async def _rating_totals(seller_ids: list[str]) -> dict:
    """{seller: (sumă, număr)} calculat din rezervările evaluate (proiecție minimă, limită explicită)."""
    acc: dict = {}
    for chunk in _chunks(seller_ids):
        rows = await db.radacini_reservations.find(
            {"seller_user_id": {"$in": chunk}, "rating": {"$exists": True}},
            {"seller_user_id": 1, "rating": 1},
        ).limit(RATING_SCAN_LIMIT).to_list(RATING_SCAN_LIMIT)
        for r in rows:
            if isinstance(r.get("rating"), (int, float)):
                total, count = acc.get(r["seller_user_id"], (0, 0))
                acc[r["seller_user_id"]] = (total + r["rating"], count + 1)
    return acc


async def _seed_seller_stats(seller_ids: list[str], persist_empty: bool = True) -> dict:
    """Creează (o singură dată, upsert `$setOnInsert`) documentele de statistici lipsă. {seller: rating_view}."""
    totals = await _rating_totals(seller_ids)
    now = now_iso()
    out = {}
    for sid in seller_ids:
        total, count = totals.get(sid, (0, 0))
        if count or persist_empty:
            await db.radacini_seller_stats.update_one(
                {"seller_user_id": sid},
                {"$setOnInsert": mark_demo({"rating_sum": total, "rating_count": count, "created_at": now, "updated_at": now})},
                upsert=True,
            )
        out[sid] = _rating_view(total, count)
    return out


async def seller_ratings(seller_ids: list[str]) -> dict:
    """{seller_user_id: {avg, count}} din documentele agregate (o interogare per 100 de vânzători)."""
    ids = sorted({s for s in seller_ids if s})
    if not ids:
        return {}
    out: dict = {}
    for chunk in _chunks(ids):
        rows = await db.radacini_seller_stats.find(
            {"seller_user_id": {"$in": chunk}}, {"seller_user_id": 1, "rating_sum": 1, "rating_count": 1}
        ).limit(len(chunk)).to_list(len(chunk))
        for r in rows:
            out[r["seller_user_id"]] = _rating_view(r.get("rating_sum") or 0, r.get("rating_count") or 0)
    missing = [i for i in ids if i not in out]
    if missing:
        out.update(await _seed_seller_stats(missing))
    return out


async def _ensure_seller_stats(seller_id: str) -> None:
    """Înainte de `$inc`: documentul trebuie să existe, altfel evaluările mai vechi s-ar pierde din agregat."""
    if not await db.radacini_seller_stats.find_one({"seller_user_id": seller_id}, {"_id": 1}):
        await _seed_seller_stats([seller_id])


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
        return None if v is None else _checked_qty(v)

    @field_validator("price_ron_per_unit", check_fields=False)
    @classmethod
    def _v_price(cls, v):
        if v is None:
            return None
        if not math.isfinite(v):
            raise ValueError("Prețul trebuie să fie un număr valid.")
        r = round(v, 2)  # validat după rotunjire: 0,004 RON ar deveni 0
        if not 0 < r <= MAX_PRICE:
            raise ValueError("Prețul trebuie să fie între 0,01 și 10 000 RON.")
        return r

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
        return _checked_qty(v)

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


async def _pending_counts(listing_ids: list[str]) -> dict:
    counts: dict = {}
    for chunk in _chunks(listing_ids):
        rows = await db.radacini_reservations.find(
            {"listing_id": {"$in": chunk}, "status": "requested"}, {"listing_id": 1}
        ).limit(20000).to_list(20000)
        for r in rows:
            counts[r["listing_id"]] = counts.get(r["listing_id"], 0) + 1
    return counts


async def _present_listings(docs: list[dict], uid: str, with_pending: bool = False) -> list[dict]:
    """Anunțuri pregătite pentru răspuns: preț de referință și rating, fără interogări pe element.
    Ceilalți utilizatori văd doar prenumele vânzătorului."""
    prices = await reference_prices(docs)
    ratings = await seller_ratings([d["seller_user_id"] for d in docs])
    pending = await _pending_counts([str(d["_id"]) for d in docs]) if with_pending and docs else {}
    out = []
    for d in docs:
        item = serialize_doc(d)
        item.pop("product_tokens", None)  # intern: doar pentru căutare
        item["quantity_total"] = _qty(d["quantity_total"])
        item["quantity_available"] = max(_qty(d["quantity_available"]), 0.0)
        item["reference_price"] = prices.get((d["product_key"], d["unit"]))
        item["seller_rating"] = ratings.get(d["seller_user_id"], {"avg": None, "count": 0})
        item["is_mine"] = d["seller_user_id"] == uid
        if not item["is_mine"]:
            item["seller_name"] = _first_name(d.get("seller_name"))
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
    near_locality: Optional[str] = None,
    radius_km: Optional[float] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    distances: Optional[dict] = None
    if near_locality is not None or radius_km is not None:
        center = LOCALITY_CENTERS.get(near_locality or "")
        if not center:
            raise HTTPException(400, "Localitate necunoscută.")
        radius = 10.0 if radius_km is None else radius_km
        if not (math.isfinite(radius) and 1 <= radius <= 100):
            raise HTTPException(400, "Raza trebuie să fie între 1 și 100 km.")
        distances = {
            name: round(haversine_km(center[0], center[1], c[0], c[1]), 1)
            for name, c in LOCALITY_CENTERS.items()
            if haversine_km(center[0], center[1], c[0], c[1]) <= radius
        }
    flt: dict = {
        "status": "active",
        "quantity_available": {"$gte": EPS},  # sub EPS = epuizat (resturi de virgulă mobilă după `$inc`)
        # Anunțurile expirate (available_until trecut) nu mai apar în piață.
        "$or": [{"available_until": None}, {"available_until": {"$gte": today_str()}}],
        **_public_filter(),
    }
    if distances is not None:
        names = [n for n in distances if not locality or n == locality]
        if not names:
            return {"items": [], "total": 0}
        flt["locality"] = names[0] if len(names) == 1 else {"$in": names}
    elif locality:
        flt["locality"] = locality
    if category:
        flt["category"] = category
    if mode:
        if mode not in LISTING_MODE_IDS:
            raise HTTPException(400, "Mod necunoscut.")
        flt["mode"] = "both" if mode == "both" else {"$in": [mode, "both"]}
    # Căutare fără $regex (care ar încărca toate anunțurile active în memorie): fiecare cuvânt al căutării
    # trebuie să fie un cuvânt sau un prefix (≥ 3 litere) din `product_tokens` → `@>` pe array, tradus în SQL.
    tokens = search_tokens(q) if q else []
    if len(tokens) == 1:
        flt["product_tokens"] = tokens[0]
    elif tokens:
        flt["$and"] = [{"product_tokens": t} for t in tokens]
    if distances is not None:
        # Sortare după distanța față de centrul localității (în Python, pe cel mult LIST_CAP anunțuri recente).
        docs = await db.radacini_listings.find(flt).sort("created_at", -1).limit(LIST_CAP).to_list(LIST_CAP)
        docs.sort(key=lambda d: distances.get(d.get("locality"), 0.0))  # stabil: în aceeași localitate rămâne ordinea recentă
        page = docs[skip:skip + limit]
        items = await _present_listings(page, str(user["id"]))
        for item in items:
            item["distance_km"] = distances.get(item.get("locality"))
        return {"items": items, "total": len(docs)}
    total = await db.radacini_listings.count_documents(flt)
    docs = await db.radacini_listings.find(flt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"items": await _present_listings(docs, str(user["id"])), "total": total}


@router.get("/listings/mine")
async def my_listings(user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    docs = await db.radacini_listings.find({"seller_user_id": uid}).sort("created_at", -1).limit(LIST_CAP).to_list(LIST_CAP)
    return {"items": await _present_listings(docs, uid, with_pending=True)}


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    doc = await _load_listing(listing_id)
    lid = str(doc["_id"])
    if doc["seller_user_id"] != uid and (doc.get("status") != "active" or _expired(doc)):
        # Anunț închis sau expirat: îl văd doar vânzătorul și cei care au rezervat din el.
        has_res = await db.radacini_reservations.find_one({"listing_id": lid, "buyer_user_id": uid}, {"_id": 1})
        if not has_res:
            raise HTTPException(404, "Anunțul nu există.")
    item = (await _present_listings([doc], uid))[0]
    mine = await db.radacini_reservations.find_one(
        {"listing_id": lid, "buyer_user_id": uid, "status": {"$in": list(ACTIVE_RES)}}
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
        "product_tokens": product_tokens(data["product"]),
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
    # Cantitate rezervată = rezervările `requested` + `confirmed` (PLAN: „rezervată sau confirmată”).
    active = await db.radacini_reservations.find(
        {"listing_id": str(doc["_id"]), "status": {"$in": list(ACTIVE_RES)}}, {"quantity": 1}
    ).limit(2000).to_list(2000)
    reserved = max(_qty(sum(r.get("quantity") or 0 for r in active)), _qty(doc["quantity_total"] - doc["quantity_available"]))
    if "unit" in changes and changes["unit"] != doc["unit"] and active:
        raise HTTPException(409, "Unitatea nu se mai poate schimba: există rezervări în curs.")
    if "mode" in changes and changes["mode"] != doc["mode"] and active:
        # Include și trecerea la un mod incompatibil cu rezervările în așteptare / confirmate.
        raise HTTPException(409, "Modul anunțului nu se mai poate schimba: există rezervări în curs.")
    sets = {k: v for k, v in changes.items() if k != "quantity_total"}
    if "product" in sets:
        sets["product_key"] = product_key(sets["product"])
        sets["product_tokens"] = product_tokens(sets["product"])
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
            raise HTTPException(400, "Cantitatea totală nu poate scădea sub cantitatea deja rezervată sau confirmată.")
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
    fresh = await _settle_available(await db.radacini_listings.find_one({"_id": doc["_id"]}) or doc)
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
    lid = str(doc["_id"])
    pending_flt = {"listing_id": lid, "status": "requested"}
    # Cumpărătorii de notificat (cel mult MAX_CLOSE_NOTIFY), apoi o singură scriere care anulează toate cererile.
    buyers = await db.radacini_reservations.find(pending_flt, {"buyer_user_id": 1}).limit(MAX_CLOSE_NOTIFY).to_list(MAX_CLOSE_NOTIFY)
    upd = await db.radacini_reservations.update_many(
        pending_flt, {"$set": {"status": "cancelled", "cancel_reason": "listing_closed", "updated_at": now}}
    )
    for buyer_id in dict.fromkeys(r["buyer_user_id"] for r in buyers):
        await safe_notify(  # rulează în fundal (nu blochează cererea)
            buyer_id,
            "Anunț închis",
            f"Anunțul „{doc['product']}” a fost închis, iar rezervarea ta a fost anulată.",
            link=listing_link(listing_id),
            type_="market",
        )
    await emit("radacini.listing_closed", actor=user, payload={"listing_id": listing_id, "cancelled": upd.modified_count})
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


async def _settle_available(listing: dict) -> dict:
    """După `$inc`, resturile de virgulă mobilă (ex. 1e-16) se tratează ca 0: le scriem 0.0, condiționat
    (nu atingem cantitatea dacă între timp a revenit o rezervare anulată)."""
    avail = listing.get("quantity_available")
    if isinstance(avail, (int, float)) and avail != 0 and abs(avail) < EPS:
        await db.radacini_listings.update_one(
            {"_id": listing["_id"], "quantity_available": {"$lt": EPS}}, {"$set": {"quantity_available": 0.0}}
        )
        return {**listing, "quantity_available": 0.0}
    return listing


async def _notify_other(res: dict, side: str, title: str, text: str, event: str, user: dict, listing_id: str) -> None:
    other = res["seller_user_id"] if side == "buyer" else res["buyer_user_id"]
    await safe_notify(other, title, text, link=RESERVATIONS_LINK, type_="market")
    await emit(event, actor=user, payload={"reservation_id": str(res["_id"]), "listing_id": listing_id})


# ----------------------------------------------------------------- rute: rezervări

@router.post("/listings/{listing_id}/reservations")
async def create_reservation(listing_id: str, body: ReservationIn, user: dict = Depends(get_current_user)):
    uid = str(user["id"])
    listing = await _load_listing(listing_id)
    listing_id = str(listing["_id"])
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
    # O singură rezervare activă per (anunț, cumpărător), fără fereastră între verificare și inserare: upsert
    # cu `$setOnInsert`. pgmongo serializează upsert-urile unei colecții cu un lock advisory, așa că la două
    # cereri simultane (dublu-click) a doua vede rezervarea primei și nu inserează nimic → 409. Nu e nevoie de
    # documente-lock separate, care ar trebui curățate la fiecare tranziție finală a rezervării.
    ins = await db.radacini_reservations.update_one(
        {"listing_id": listing_id, "buyer_user_id": uid, "status": {"$in": list(ACTIVE_RES)}},
        {"$setOnInsert": doc},
        upsert=True,
    )
    if ins.upserted_id is None:
        raise HTTPException(409, "Ai deja o rezervare activă pentru acest anunț.")
    doc["_id"] = ins.upserted_id
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
    docs = await db.radacini_reservations.find({f"{role}_user_id": uid}).sort("created_at", -1).limit(LIST_CAP).to_list(LIST_CAP)
    ids = sorted({d["listing_id"] for d in docs})
    listings: dict = {}
    if ids:
        rows = await db.radacini_listings.find({"_id": {"$in": [ObjectId(i) for i in ids]}}).limit(len(ids)).to_list(len(ids))
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
    fresh_listing = await _settle_available(
        await db.radacini_listings.find_one({"_id": ObjectId(res["listing_id"])}) or listing
    )
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
    await _ensure_seller_stats(res["seller_user_id"])  # înainte de evaluare: agregatul trebuie să conțină și evaluările vechi
    upd = await db.radacini_reservations.update_one(
        {"_id": res["_id"], "status": "picked_up", "rating": {"$exists": False}}, {"$set": fields}
    )
    if upd.modified_count != 1:
        raise HTTPException(409, "Rezervarea a fost deja evaluată.")
    try:
        await db.radacini_seller_stats.update_one(
            {"seller_user_id": res["seller_user_id"]},
            {
                "$inc": {"rating_sum": body.rating, "rating_count": 1},
                "$set": {"updated_at": now},
                "$setOnInsert": mark_demo({"created_at": now}),
            },
            upsert=True,
        )
    except Exception:  # noqa: BLE001 - evaluarea e deja salvată; agregatul se poate reface din rezervări
        log.exception("radacini: agregatul de rating nu a putut fi actualizat pentru %s", res["seller_user_id"])
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
    if not (isinstance(user_id, str) and len(user_id) == 24 and ObjectId.is_valid(user_id)):
        return {"avg": None, "count": 0}
    stats = await db.radacini_seller_stats.find_one({"seller_user_id": user_id})
    if stats:
        return _rating_view(stats.get("rating_sum") or 0, stats.get("rating_count") or 0)
    # Lipsă: se calculează o dată din rezervări; se salvează doar dacă există evaluări (nu creăm documente
    # pentru orice id cerut).
    return (await _seed_seller_stats([user_id], persist_empty=False))[user_id]
