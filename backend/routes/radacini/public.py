"""Endpointuri publice (fără cont) pentru pagina /radacini/descopera: piața și comunitățile deschise."""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from . import common
from .bridge import db, serialize_doc
from .common import RadaciniRoute, public_rate_limit
from .constants import LISTING_CATEGORY_IDS
from .market import EPS, _expired, _first_name, _qty, _public_filter, search_tokens, seller_ratings
from .projects import today_str

log = logging.getLogger(__name__)


async def public_pages_rate_limit(request: Request) -> None:
    """`public_rate_limit` din common.py acoperă doar /meta și /parcels*; rutele /public/* au aceeași limită
    (pe IP, cheie separată): fără credențiale `RADACINI_PUBLIC_RATE_LIMIT_PER_MIN` (60), 0 = dezactivat."""
    if request.method != "GET":
        return
    has_credentials = bool(request.cookies.get("access_token") or request.headers.get("authorization"))
    if has_credentials:
        limit = common._env_int("RADACINI_AUTH_RATE_LIMIT_PER_MIN", 600)
    else:
        limit = common._env_int("RADACINI_PUBLIC_RATE_LIMIT_PER_MIN", 60)
    if limit <= 0:
        return
    kind = "auth" if has_credentials else "anon"
    if not common._PUBLIC_RATE_LIMITER.hit(f"public-pages:{kind}:{common.client_ip(request)}", limit):
        raise HTTPException(429, "Prea multe cereri. Încearcă din nou într-un minut.", headers={"Retry-After": "60"})


router = APIRouter(
    route_class=RadaciniRoute, dependencies=[Depends(public_rate_limit), Depends(public_pages_rate_limit)]
)


@router.get("/public/listings")
async def public_listings(
    locality: Optional[str] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    if category and category not in LISTING_CATEGORY_IDS:
        raise HTTPException(400, "Categorie necunoscută.")
    flt: dict = {
        "status": "active",
        "quantity_available": {"$gte": EPS},
        "$or": [{"available_until": None}, {"available_until": {"$gte": today_str()}}],
        **_public_filter(),
    }
    if locality:
        flt["locality"] = locality
    if category:
        flt["category"] = category
    tokens = search_tokens(q) if q else []
    if len(tokens) == 1:
        flt["product_tokens"] = tokens[0]
    elif tokens:
        flt["$and"] = [{"product_tokens": t} for t in tokens]
    total = await db.radacini_listings.count_documents(flt)
    docs = await db.radacini_listings.find(flt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    docs = [d for d in docs if not _expired(d)]
    ratings = await seller_ratings([d["seller_user_id"] for d in docs])
    items = []
    for d in docs:
        items.append({
            "id": str(d["_id"]),
            "product": d.get("product"),
            "category": d.get("category"),
            "unit": d.get("unit"),
            "quantity_available": max(_qty(d["quantity_available"]), 0.0),
            "price_ron_per_unit": d.get("price_ron_per_unit"),
            "mode": d.get("mode"),
            "exchange_for": d.get("exchange_for"),
            "locality": d.get("locality"),
            "available_until": d.get("available_until"),
            "seller_name": _first_name(d.get("seller_name")),
            "seller_rating": ratings.get(d["seller_user_id"], {"avg": None, "count": 0}),
            "created_at": d.get("created_at"),
        })
    return {"items": items, "total": total}


@router.get("/public/communities")
async def public_communities(
    locality: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
):
    flt: dict = {"visibility": "open"}
    if os.environ.get("RADACINI_MARK_DEMO", "").lower() != "true":
        flt["is_demo"] = {"$ne": True}
    if locality:
        flt["locality"] = locality
    try:
        docs = await db.radacini_communities.find(flt).sort("members_count", -1).limit(200).to_list(200)
    except Exception:  # noqa: BLE001  colecția poate lipsi înainte de migrare
        log.warning("radacini: colecția radacini_communities nu poate fi citită", exc_info=True)
        return {"items": []}
    needle = (q or "").strip().lower()
    if needle:
        docs = [d for d in docs if needle in str(d.get("name") or "").lower()]
    items = []
    for d in docs[:limit]:
        out = serialize_doc(d)
        items.append({k: out.get(k) for k in ("id", "name", "locality", "description", "members_count")})
    return {"items": items}
