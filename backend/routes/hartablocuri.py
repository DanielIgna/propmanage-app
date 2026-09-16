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

logger = logging.getLogger("propmanage.hartablocuri")
router = APIRouter(prefix="/api", tags=["hartablocuri"])
public_router = APIRouter(prefix="/api/public", tags=["hartablocuri-public"])

HB_FILE_DEFAULT = "/app/backend/data/hartablocuri_cluj.xlsx"


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
    return {
        "id": str(b["_id"]),
        "name": b.get("name"),
        "address": b.get("address"),
        "city": b.get("city") or raw.get("city"),
        "neighborhood": ctx.get("neighborhood") or raw.get("neighborhood"),
        "construction_year": ctx.get("construction_year"),
        "floors": ctx.get("floors"),
        "units": ctx.get("number_of_units"),
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


@public_router.get("/buildings/cities")
async def public_cities():
    """Localități disponibile (din HartaBlocuri + PropManage) pentru filtre discovery."""
    cities = {}
    async for b in db.buildings.find({}, {"city": 1, "context.external_sources.hartablocuri.raw.city": 1}):
        c = b.get("city") or (_hb(b) or {}).get("raw", {}).get("city")
        if c:
            cities[c] = cities.get(c, 0) + 1
    ordered = sorted(cities.items(), key=lambda x: -x[1])
    return {"cities": [{"name": c, "count": n} for c, n in ordered]}


@public_router.get("/buildings/{building_id}")
async def public_building_detail(building_id: str):
    if not ObjectId.is_valid(building_id):
        raise HTTPException(404, "Blocul nu există")
    b = await db.buildings.find_one({"_id": ObjectId(building_id)})
    if not b:
        raise HTTPException(404, "Blocul nu există")
    card = _public_card(b)
    hb = _hb(b) or {}
    card["hartablocuri"] = {
        "era": (hb.get("raw") or {}).get("era"),
        "structura": (hb.get("raw") or {}).get("structura"),
        "regim_inaltime": (hb.get("raw") or {}).get("regim_inaltime"),
        "lift": (hb.get("raw") or {}).get("lift"),
        "scari": (hb.get("raw") or {}).get("scari"),
        "reference_url": hb.get("reference_url"),
        "verification_status": hb.get("verification_status"),
    } if hb else None
    return {"building": card}


# ============= ADMIN IMPORT CONTROL =============

class ImportRequest(BaseModel):
    file_path: Optional[str] = Field(default=None, max_length=500)
    limit: Optional[int] = Field(default=None, ge=1, le=100000)
    dry_run: bool = False


@router.post("/admin/hartablocuri/import")
async def admin_run_import(body: ImportRequest, user: dict = Depends(require_role("admin"))):
    from hartablocuri_import import run_import
    path = body.file_path or HB_FILE_DEFAULT
    import os
    if not os.path.exists(path):
        raise HTTPException(400, f"Fișierul nu există: {path}. Încarcă-l în {HB_FILE_DEFAULT} întâi.")
    result = await run_import(path, limit=body.limit, dry_run=body.dry_run, triggered_by=user["id"])
    result.pop("error_samples", None) if False else None
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
    conflicts = await db.buildings.count_documents({"context.conflicts.0": {"$exists": True}})
    return {
        "total_buildings": total,
        "with_hartablocuri": hb,
        "hartablocuri_only": imported,
        "matched_both_sources": both,
        "propmanage_only": total - hb,
        "with_conflicts": conflicts,
    }


class ConflictResolve(BaseModel):
    field: str = Field(max_length=80)
    action: str = Field(pattern="^(confirm|reject)$")  # confirm=acceptă HartaBlocuri, reject=păstrează PropManage


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
        conds.append({"$or": [{"name": rx}, {"address": rx}, {"city": rx}]})
    if source == "hartablocuri":
        conds.append({"source": "hartablocuri_import"})
    elif source == "both":
        conds.append({"context.external_sources.hartablocuri": {"$exists": True},
                      "source": {"$ne": "hartablocuri_import"}})
    elif source == "propmanage":
        conds.append({"context.external_sources.hartablocuri": {"$exists": False}})
    if status == "conflict":
        conds.append({"context.conflicts.0": {"$exists": True}})
    elif status != "all":
        conds.append({"context.verification_status": status})
    query = {"$and": conds} if conds else {}
    total = await db.buildings.count_documents(query)
    skip = (page - 1) * page_size
    out = []
    async for b in db.buildings.find(query).skip(skip).limit(page_size):
        ctx = b.get("context") or {}
        out.append({
            "id": str(b["_id"]), "name": b.get("name"), "address": b.get("address"),
            "city": b.get("city"), "neighborhood": ctx.get("neighborhood"),
            "source": _source_of(b),
            "verification_status": ctx.get("verification_status", "unverified"),
            "conflicts_count": len(ctx.get("conflicts") or []),
            "residents_count": await db.properties.count_documents({"building_id": str(b["_id"])}),
        })
    return {"buildings": out, "total": total, "page": page, "page_size": page_size}
