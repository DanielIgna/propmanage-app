"""HartaBlocuri — discovery public „Găsește-ți blocul" + control import admin.

Public (fără auth): căutare blocuri după nume/adresă/localitate/cartier → funnel /register.
Admin: rulare import (idempotent), listă loturi (batches), raport, filtre sursă/status.
Refolosește colecția `buildings` existentă. NU creează sistem paralel.
"""
import logging
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from db import db
from deps import require_role
from hartablocuri_read_layer import build_truth_layer

logger = logging.getLogger("propmanage.hartablocuri")
router = APIRouter(prefix="/api", tags=["hartablocuri"])
public_router = APIRouter(prefix="/api/public", tags=["hartablocuri-public"])

HB_FILE_DEFAULT = "/app/backend/data/hartablocuri_cluj.xlsx"
HB_DATA_DIR = "/app/backend/data"


def _hb(b: dict) -> Optional[dict]:
    return ((b.get("context") or {}).get("external_sources") or {}).get("hartablocuri")


def _source_of(b: dict) -> str:
    ctx = b.get("context") or {}
    has_hb = bool((ctx.get("external_sources") or {}).get("hartablocuri"))
    is_import = b.get("source") == "hartablocuri_import"
    if has_hb and not is_import:
        return "both"
    if has_hb:
        return "hartablocuri"
    return "propmanage"


def _public_card(b: dict) -> dict:
    ctx = b.get("context") or {}
    hb = _hb(b) or {}
    raw = hb.get("raw") or {}
    _lat = ctx.get("lat") if isinstance(ctx.get("lat"), (int, float)) else raw.get("lat")
    _lng = ctx.get("lng") if isinstance(ctx.get("lng"), (int, float)) else raw.get("lng")
    return {
        "id": str(b["_id"]),
        "name": b.get("name"),
        "address": b.get("address"),
        "city": b.get("city") or raw.get("city"),
        "neighborhood": ctx.get("neighborhood") or raw.get("neighborhood"),
        "construction_year": ctx.get("construction_year"),
        "floors": ctx.get("floors"),
        "units": ctx.get("number_of_units"),
        # GRANIȚĂ PUBLIC/PRIVAT: doar coordonate APROXIMATE (~1km, rotunjite la 2 zecimale)
        # pentru discovery pe hartă. Coordonatele exacte rămân private (doar în GIS autentificat).
        "lat_approx": round(_lat, 2) if isinstance(_lat, (int, float)) else None,
        "lng_approx": round(_lng, 2) if isinstance(_lng, (int, float)) else None,
        "source": _source_of(b),
        "source_label": {"both": "PropManage + HartaBlocuri", "hartablocuri": "HartaBlocuri",
                         "propmanage": "PropManage"}[_source_of(b)],
        "verified": ctx.get("verification_status", "unverified") in ("verified", "documented"),
        "verification_note": "Date externe — neverificate de PropManage" if _source_of(b) != "propmanage"
                             and ctx.get("verification_status", "unverified") == "unverified" else None,
    }


# ============= PUBLIC DISCOVERY =============

@public_router.get("/buildings/search")
async def public_search_buildings(
    q: str = Query("", max_length=160),
    city: Optional[str] = Query(None, max_length=80),
    limit: int = Query(12, ge=1, le=30),
):
    """Căutare publică (fără auth) — discovery „Găsește-ți blocul". Nu expune date sensibile."""
    ql = q.strip()
    if len(ql) < 2 and not city:
        return {"buildings": [], "total": 0}
    conds = []
    if ql:
        rx = {"$regex": re.escape(ql), "$options": "i"}
        conds.append({"$or": [
            {"name": rx}, {"address": rx}, {"city": rx},
            {"context.neighborhood": rx},
            {"context.external_sources.hartablocuri.raw.adresa": rx},
        ]})
    if city:
        conds.append({"$or": [
            {"city": {"$regex": re.escape(city), "$options": "i"}},
            {"context.external_sources.hartablocuri.raw.city": {"$regex": re.escape(city), "$options": "i"}},
        ]})
    query = {"$and": conds} if len(conds) > 1 else (conds[0] if conds else {})
    out = [_public_card(b) async for b in db.buildings.find(query).limit(limit)]
    total = await db.buildings.count_documents(query)
    return {"buildings": out, "total": total}


_CITIES_CACHE = {"data": None, "ts": 0.0}
_CITIES_TTL = 300  # secunde


@public_router.get("/buildings/cities")
async def public_cities():
    """Localități disponibile pentru filtre discovery. Aggregation + cache (evită scan complet repetat)."""
    import time
    now = time.time()
    if _CITIES_CACHE["data"] is not None and (now - _CITIES_CACHE["ts"]) < _CITIES_TTL:
        return {"cities": _CITIES_CACHE["data"]}
    pipeline = [
        {"$project": {"city": {"$ifNull": ["$city", "$context.external_sources.hartablocuri.raw.city"]}}},
        {"$match": {"city": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$city", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 100},
    ]
    result = [{"name": d["_id"], "count": d["count"]} async for d in db.buildings.aggregate(pipeline)]
    _CITIES_CACHE["data"] = result
    _CITIES_CACHE["ts"] = now
    return {"cities": result}


@public_router.get("/buildings/{building_id}")
async def public_building_detail(building_id: str):
    if not ObjectId.is_valid(building_id):
        raise HTTPException(404, "Blocul nu există")
    b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    if not b:
        raise HTTPException(404, "Blocul nu există")
    card = _public_card(b)
    hb = _hb(b) or {}
    hb_raw = hb.get("raw") or {}
    card["hartablocuri"] = {
        "era": hb_raw.get("era"),
        "structura": hb_raw.get("structura"),
        "regim_inaltime": hb_raw.get("regim_inaltime"),
        "lift": hb_raw.get("lift"),
        "scari": hb_raw.get("scari"),
        "reference_url": hb.get("reference_url"),
        "verification_status": hb.get("verification_status"),
    } if hb else None
    # Truth Layer READ MODEL — derivat pur la citire (nu se salvează în DB)
    card["truth_layer"] = build_truth_layer(hb_raw) if hb else None
    if hb:
        card["county"] = hb_raw.get("judet")
        card["plan_urls"] = hb.get("plan_urls") or []
        from seo_clusters import MONETIZATION
        card["monetization"] = MONETIZATION
        # GRANIȚĂ PUBLIC/PRIVAT: NU expunem lat/lng exact, google_maps_url sau building_id-based access.
        # Discovery public → identificare → login → asociere → Private Property GIS (coordonate exacte).
        card["cta"] = {"identify": f"/register?binvite={card['id']}", "cartea_casei": "/cartea-casei"}
        card["private_note"] = "Coordonatele exacte și contextul complet sunt disponibile după conectarea proprietății."
    return {"building": card}


# ============= PUBLIC MAP + SEO CLUSTERS =============

@public_router.get("/maps/config")
async def public_maps_config():
    """Config strat de cartografiere (abstraction). Cheia din env; feature flag + fallback.
    NOTĂ: cheia server-side (GOOGLE_MAPS_SERVER_API_KEY) NU se expune niciodată clientului."""
    import os
    enabled = os.environ.get("GOOGLE_MAPS_ENABLED", "").strip().lower() in ("1", "true", "yes")
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    active = bool(enabled and key)
    return {"provider": "google" if active else "fallback", "enabled": active,
            "api_key": key if active else None, "fallback": not active,
            "attribution": "HartaBlocuri (date) · Google Maps (cartografiere)"}


@public_router.get("/blocuri/map")
async def public_map_markers(
    city: Optional[str] = Query(None, max_length=80),
    era: Optional[str] = Query(None, max_length=60),
    typology: Optional[str] = Query(None, max_length=8),
):
    """Hartă PUBLICĂ contextuală — AGREGATĂ pe cartier/localitate (centroid rotunjit ~1km).
    NU expune coordonate exacte sau date individuale ale clădirilor (granița public/privat)."""
    from collections import defaultdict
    q = {"context.external_sources.hartablocuri": {"$exists": True}}
    if city:
        q["city"] = {"$regex": re.escape(city), "$options": "i"}
    groups = defaultdict(lambda: {"count": 0, "lat_sum": 0.0, "lng_sum": 0.0})
    async for b in db.buildings.find(q, {"city": 1, "context": 1}):
        ctx = b.get("context") or {}
        raw = (ctx.get("external_sources") or {}).get("hartablocuri", {}).get("raw") or {}
        lat = ctx.get("lat") if isinstance(ctx.get("lat"), (int, float)) else raw.get("lat")
        lng = ctx.get("lng") if isinstance(ctx.get("lng"), (int, float)) else raw.get("lng")
        if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
            continue
        tl = build_truth_layer(raw) or {}
        if era and (raw.get("era") or "").strip().lower() != era.strip().lower():
            continue
        if typology and not any(p["code"] == typology.upper() for p in (tl.get("typology_profiles") or [])):
            continue
        key = (b.get("city") or "?", (ctx.get("neighborhood") or raw.get("neighborhood") or "—"))
        g = groups[key]
        g["count"] += 1
        g["lat_sum"] += lat
        g["lng_sum"] += lng
    out = []
    for (loc, nbh), g in groups.items():
        n = g["count"]
        out.append({
            "city": loc, "neighborhood": nbh, "count": n,
            # centroid rotunjit la ~1km (2 zecimale) — contextual, NU precis
            "lat": round(g["lat_sum"] / n, 2), "lng": round(g["lng_sum"] / n, 2),
            "approximate": True,
        })
    out.sort(key=lambda x: -x["count"])
    return {"areas": out, "total_buildings": sum(a["count"] for a in out),
            "note": "Zone agregate (centroid aproximativ). Coordonatele exacte sunt private."}


@public_router.get("/blocuri/clusters")
async def public_clusters(county: Optional[str] = Query(None, max_length=60)):
    """Clustere SEO publice — DOAR cele INDEX (publicate)."""
    from seo_clusters import list_clusters
    rows = await list_clusters(state="INDEX", county=county)
    slim = [{"slug": c["slug"], "value_label": c["value_label"], "dimension": c["dimension"],
             "county": c["county"], "locality": c["locality"], "building_count": c["building_count"]}
            for c in rows]
    return {"clusters": slim, "total": len(slim)}


@public_router.get("/blocuri/cluster")
async def public_cluster_detail(slug: str = Query(..., max_length=300)):
    """Detaliu cluster public — doar dacă este INDEX (publicat)."""
    from seo_clusters import get_cluster_by_slug
    c = await get_cluster_by_slug(slug)
    if not c or c["state"] != "INDEX":
        raise HTTPException(404, "Cluster indisponibil")
    return {"cluster": c}


# ============= ADMIN IMPORT CONTROL =============

class ImportRequest(BaseModel):
    file_path: Optional[str] = Field(default=None, max_length=500)
    limit: Optional[int] = Field(default=None, ge=1, le=100000)
    dry_run: bool = False


@router.post("/admin/hartablocuri/import")
async def admin_run_import(body: ImportRequest, user: dict = Depends(require_role("admin"))):
    from hartablocuri_import import run_import
    import os
    path = os.path.realpath(body.file_path or HB_FILE_DEFAULT)
    # Constrânge la directorul de date (previne path traversal / citire arbitrară)
    if os.path.commonpath([path, HB_DATA_DIR]) != HB_DATA_DIR or not path.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Fișier invalid. Sunt permise doar fișiere .xlsx din directorul de date.")
    if not os.path.exists(path):
        raise HTTPException(400, "Fișierul de import nu a fost găsit în directorul de date.")
    result = await run_import(path, limit=body.limit, dry_run=body.dry_run, triggered_by=user["id"])
    return result


@router.get("/admin/hartablocuri/batches")
async def admin_list_batches(user: dict = Depends(require_role("admin"))):
    batches = [{k: v for k, v in doc.items() if k != "_id"}
               async for doc in db.import_batches.find({}).sort("started_at", -1).limit(50)]
    return {"batches": batches}


@router.get("/admin/hartablocuri/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):
    total = await db.buildings.count_documents({})
    hb = await db.buildings.count_documents({"context.external_sources.hartablocuri": {"$exists": True}})
    imported = await db.buildings.count_documents({"source": "hartablocuri_import"})
    both = await db.buildings.count_documents({
        "context.external_sources.hartablocuri": {"$exists": True},
        "source": {"$ne": "hartablocuri_import"}})
    conflicts = await db.buildings.count_documents(
        {"context.conflicts": {"$elemMatch": {"status": "review"}}})
    # Overview read-only — doar indicatori calculabili sigur din datele existente
    with_year = await db.buildings.count_documents({"context.construction_year": {"$nin": [None, ""]}})
    with_floors = await db.buildings.count_documents({"context.floors": {"$nin": [None, ""]}})
    with_units = await db.buildings.count_documents({"context.number_of_units": {"$nin": [None, ""]}})
    incomplete = await db.buildings.count_documents({"$or": [
        {"context.construction_year": {"$in": [None, ""]}},
        {"context.floors": {"$in": [None, ""]}},
        {"context.number_of_units": {"$in": [None, ""]}},
    ]})
    loc_agg = await db.buildings.aggregate([
        {"$match": {"city": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$city"}}, {"$count": "n"}]).to_list(1)
    nbh_agg = await db.buildings.aggregate([
        {"$match": {"context.neighborhood": {"$nin": [None, ""]}}},
        {"$group": {"_id": "$context.neighborhood"}}, {"$count": "n"}]).to_list(1)
    return {
        "total_buildings": total,
        "with_hartablocuri": hb,
        "hartablocuri_only": imported,
        "matched_both_sources": both,
        "propmanage_only": total - hb,
        "with_conflicts": conflicts,
        "localities": (loc_agg[0]["n"] if loc_agg else 0),
        "neighborhoods": (nbh_agg[0]["n"] if nbh_agg else 0),
        "with_construction_year": with_year,
        "with_floors": with_floors,
        "with_units": with_units,
        "incomplete": incomplete,
    }


class ConflictResolve(BaseModel):
    field: str = Field(max_length=80)
    action: str = Field(pattern="^(confirm|reject)$")  # confirm=acceptă HartaBlocuri, reject=păstrează PropManage


# Câmpuri de context permise pentru rezolvare (allowlist — previne injecție de path în $set)
RESOLVABLE_FIELDS = {"construction_year", "floors", "number_of_units", "neighborhood"}


@router.get("/admin/hartablocuri/buildings/{building_id}")
async def admin_building_detail(building_id: str, user: dict = Depends(require_role("admin"))):
    """Detaliu complet bloc pentru Admin: context, proveniență HartaBlocuri, conflicte, typology."""
    if not ObjectId.is_valid(building_id):
        raise HTTPException(404, "Blocul nu există")
    b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    if not b:
        raise HTTPException(404, "Blocul nu există")
    ctx = b.get("context") or {}
    hb = _hb(b)
    return {
        "id": str(b["_id"]),
        "name": b.get("name"), "address": b.get("address"), "city": b.get("city"),
        "source": _source_of(b),
        "verification_status": ctx.get("verification_status", "unverified"),
        "context": {k: v for k, v in ctx.items() if k not in ("external_sources", "norm_address")},
        "conflicts": ctx.get("conflicts") or [],
        "typology": ctx.get("typology"),
        "hartablocuri": hb,
        "truth_layer": build_truth_layer((hb or {}).get("raw")) if hb else None,
        "residents_count": await db.properties.count_documents({"building_id": str(b["_id"])}),
    }


@router.post("/admin/hartablocuri/buildings/{building_id}/conflicts/resolve")
async def admin_resolve_conflict(building_id: str, body: ConflictResolve,
                                 user: dict = Depends(require_role("admin"))):
    """Rezolvă un conflict per câmp. confirm=valoarea HartaBlocuri devine activă; reject=rămâne PropManage.
    NU șterge valoarea originală HartaBlocuri; păstrează ambele valori + istoric.
    """
    if not ObjectId.is_valid(building_id):
        raise HTTPException(404, "Blocul nu există")
    if body.field not in RESOLVABLE_FIELDS:
        raise HTTPException(400, "Câmp de conflict invalid")
    b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    if not b:
        raise HTTPException(404, "Blocul nu există")
    ctx = b.get("context") or {}
    conflicts = ctx.get("conflicts") or []
    target = next((c for c in conflicts if c.get("field") == body.field and c.get("status") == "review"), None)
    if not target:
        raise HTTPException(404, "Conflict nerezolvat inexistent pentru acest câmp")
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    chosen = target["hartablocuri_value"] if body.action == "confirm" else target["propmanage_value"]
    set_ops = {}
    if body.action == "confirm":
        set_ops[f"context.{body.field}"] = target["hartablocuri_value"]
    target.update({
        "status": "confirmed" if body.action == "confirm" else "rejected",
        "chosen_value": chosen, "chosen_source": "HartaBlocuri" if body.action == "confirm" else "PropManage",
        "resolved_by": user["id"], "resolved_by_name": user.get("name"), "resolved_at": now,
    })
    history = ctx.get("conflict_history") or []
    history.append({**{k: target[k] for k in ("field", "propmanage_value", "hartablocuri_value",
                                              "status", "chosen_value", "chosen_source")},
                    "resolved_by_name": user.get("name"), "resolved_at": now})
    set_ops["context.conflicts"] = conflicts
    set_ops["context.conflict_history"] = history
    set_ops["context.updated_at"] = now
    await db.buildings.update_one({"_id": b["_id"]}, {"$set": set_ops})
    return {"ok": True, "field": body.field, "action": body.action, "chosen_value": chosen}


@router.get("/admin/hartablocuri/conflicts")
async def admin_list_conflicts(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                               unresolved_only: bool = Query(True),
                               user: dict = Depends(require_role("admin"))):
    """Listă blocuri cu conflicte + detaliile fiecărui conflict pentru review."""
    q = {"context.conflicts.0": {"$exists": True}}
    if unresolved_only:
        q = {"context.conflicts": {"$elemMatch": {"status": "review"}}}
    total = await db.buildings.count_documents(q)
    skip = (page - 1) * page_size
    out = []
    async for b in db.buildings.find(q).skip(skip).limit(page_size):
        ctx = b.get("context") or {}
        conflicts = ctx.get("conflicts") or []
        if unresolved_only:
            conflicts = [c for c in conflicts if c.get("status") == "review"]
        out.append({
            "id": str(b["_id"]), "name": b.get("name"), "address": b.get("address"),
            "city": b.get("city"), "conflicts": conflicts,
        })
    return {"buildings": out, "total": total, "page": page, "page_size": page_size}


@router.get("/admin/hartablocuri/buildings")
async def admin_list_buildings(
    q: str = Query("", max_length=160),
    source: str = Query("all", pattern="^(all|propmanage|hartablocuri|both)$"),
    status: str = Query("all", pattern="^(all|unverified|declared|documented|verified|conflict)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: dict = Depends(require_role("admin")),
):
    conds = []
    if q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        conds.append({"$or": [{"name": rx}, {"address": rx}, {"city": rx},
                              {"context.neighborhood": rx}]})
    if source == "hartablocuri":
        conds.append({"source": "hartablocuri_import"})
    elif source == "both":
        conds.append({"context.external_sources.hartablocuri": {"$exists": True},
                      "source": {"$ne": "hartablocuri_import"}})
    elif source == "propmanage":
        conds.append({"context.external_sources.hartablocuri": {"$exists": False}})
    if status == "conflict":
        conds.append({"context.conflicts": {"$elemMatch": {"status": "review"}}})
    elif status != "all":
        conds.append({"context.verification_status": status})
    query = {"$and": conds} if conds else {}
    total = await db.buildings.count_documents(query)
    skip = (page - 1) * page_size
    out = []
    async for b in db.buildings.find(query).skip(skip).limit(page_size):
        ctx = b.get("context") or {}
        open_conflicts = [c for c in (ctx.get("conflicts") or []) if c.get("status") == "review"]
        out.append({
            "id": str(b["_id"]), "name": b.get("name"), "address": b.get("address"),
            "city": b.get("city"), "neighborhood": ctx.get("neighborhood"),
            "construction_year": ctx.get("construction_year"),
            "floors": ctx.get("floors"), "units": ctx.get("number_of_units"),
            "source": _source_of(b),
            "verification_status": ctx.get("verification_status", "unverified"),
            "conflicts_count": len(open_conflicts),
            "residents_count": await db.properties.count_documents({"building_id": str(b["_id"])}),
        })
    return {"buildings": out, "total": total, "page": page, "page_size": page_size}
