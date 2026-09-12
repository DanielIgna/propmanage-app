"""CIP-A — Construction Intelligence REST API.

Public:
  GET  /api/construction/taxonomy/public       — arbore doar noduri vizibile
Admin:
  GET    /api/construction/taxonomy            — arbore complet + flags
  POST   /api/construction/taxonomy            — nod nou
  PATCH  /api/construction/taxonomy/{id}       — redenumire / activare
  DELETE /api/construction/taxonomy/{id}       — doar noduri fără copii
  POST   /api/construction/refresh-visibility  — gate prin Orchestrator
  GET    /api/construction/overview            — KPI + hidden-with-potential
  GET    /api/construction/projects            — vedere centrală cereri (filtre)
  GET    /api/construction/projects/export     — CSV
"""
import csv
import io
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Body, HTTPException, Query
from fastapi.responses import StreamingResponse

from db import db
from deps import require_role
from construction.taxonomy import (
    build_tree, refresh_category_visibility, slugify, seed_construction_taxonomy,
)

logger = logging.getLogger("propmanage.construction_routes")
router = APIRouter(prefix="/api/construction", tags=["construction"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(n: dict) -> dict:
    n = dict(n)
    n.pop("_id", None)
    return n


# ============================ TAXONOMY ============================
@router.get("/taxonomy/public")
async def public_taxonomy():
    nodes = [_clean(d) async for d in db.construction_taxonomy.find({"is_publicly_visible": True})]
    return {"tree": build_tree(nodes), "count": len(nodes)}


@router.get("/taxonomy")
async def full_taxonomy(user=Depends(require_role("admin"))):
    nodes = [_clean(d) async for d in db.construction_taxonomy.find({})]
    return {
        "tree": build_tree(nodes),
        "count": len(nodes),
        "visible_count": sum(1 for n in nodes if n.get("is_publicly_visible")),
    }


@router.post("/taxonomy")
async def create_node(payload: dict = Body(...), user=Depends(require_role("admin"))):
    name = (payload.get("name") or "").strip()
    if len(name) < 2:
        raise HTTPException(400, "Numele trebuie să aibă minim 2 caractere")
    parent_id = payload.get("parent_id")
    if parent_id:
        parent = await db.construction_taxonomy.find_one({"id": parent_id})
        if not parent:
            raise HTTPException(404, "Nodul părinte nu există")
        if parent.get("depth_level", 0) >= 2:
            raise HTTPException(400, "Adâncime maximă 3 niveluri (categorie → subcategorie → serviciu)")
        depth = parent["depth_level"] + 1
        legacy = parent["legacy_category"]
    else:
        depth = 0
        legacy = payload.get("legacy_category") or slugify(name)
    siblings = await db.construction_taxonomy.count_documents({"parent_id": parent_id})
    doc = {
        "id": uuid.uuid4().hex,
        "name": name,
        "slug": slugify(name),
        "parent_id": parent_id,
        "depth_level": depth,
        "legacy_category": legacy,
        "is_active": True,
        "is_publicly_visible": False,
        "specialist_count": 0,
        "order": siblings,
        "source": "admin",
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db.construction_taxonomy.insert_one({**doc})
    await refresh_category_visibility()
    fresh = await db.construction_taxonomy.find_one({"id": doc["id"]})
    return _clean(fresh)


@router.patch("/taxonomy/{node_id}")
async def patch_node(node_id: str, payload: dict = Body(...), user=Depends(require_role("admin"))):
    node = await db.construction_taxonomy.find_one({"id": node_id})
    if not node:
        raise HTTPException(404, "Nod inexistent")
    updates = {}
    if "name" in payload:
        name = (payload["name"] or "").strip()
        if len(name) < 2:
            raise HTTPException(400, "Nume invalid")
        updates["name"] = name
        updates["slug"] = slugify(name)
    if "is_active" in payload:
        updates["is_active"] = bool(payload["is_active"])
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    updates["updated_at"] = _now()
    await db.construction_taxonomy.update_one({"id": node_id}, {"$set": updates})
    if "is_active" in updates:
        await refresh_category_visibility()
    fresh = await db.construction_taxonomy.find_one({"id": node_id})
    return _clean(fresh)


@router.delete("/taxonomy/{node_id}")
async def delete_node(node_id: str, user=Depends(require_role("admin"))):
    children = await db.construction_taxonomy.count_documents({"parent_id": node_id})
    if children > 0:
        raise HTTPException(409, f"Nodul are {children} sub-noduri — șterge-le sau mută-le mai întâi")
    res = await db.construction_taxonomy.delete_one({"id": node_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Nod inexistent")
    return {"deleted": True}


@router.post("/refresh-visibility")
async def refresh_visibility(user=Depends(require_role("admin"))):
    """Manual trigger — routed through Autonomy Orchestrator (playbook + ledger)."""
    from orchestrator.engine import emit_signal
    result = await emit_signal("category_visibility_refresh", {"trigger": f"manual:{user.get('email')}"})
    return result


@router.post("/seed")
async def force_seed(user=Depends(require_role("admin"))):
    out = await seed_construction_taxonomy()
    await refresh_category_visibility()
    return out


# ============================ OVERVIEW ============================
@router.get("/overview")
async def overview(user=Depends(require_role("admin"))):
    nodes = [_clean(d) async for d in db.construction_taxonomy.find({})]
    roots = [n for n in nodes if n.get("depth_level") == 0]
    from construction.taxonomy import get_specialist_counts, _requests_per_category
    counts = await get_specialist_counts()
    demand = await _requests_per_category()
    coverage = [
        {
            "legacy_category": r["legacy_category"],
            "name": r["name"],
            "specialists": counts.get(r["legacy_category"], 0),
            "requests_90d": demand.get(r["legacy_category"], 0),
            "visible": bool(r.get("is_publicly_visible")),
            "active": bool(r.get("is_active", True)),
        }
        for r in sorted(roots, key=lambda x: x.get("order", 0))
    ]
    hidden_with_potential = [c for c in coverage if c["specialists"] == 0 and c["requests_90d"] > 0]
    return {
        "total_nodes": len(nodes),
        "visible_nodes": sum(1 for n in nodes if n.get("is_publicly_visible")),
        "root_categories": len(roots),
        "roots_visible": sum(1 for r in roots if r.get("is_publicly_visible")),
        "coverage": coverage,
        "hidden_with_potential": hidden_with_potential,
    }


# ============================ PRICE OBSERVATORY (CIP-B) ============================
@router.get("/prices/public")
async def public_prices(category: Optional[str] = None, city: Optional[str] = None):
    """Prețuri orientative publice, agregate per categorie × oraș × UM × nivel experiență."""
    from construction.prices import aggregate_prices
    rows = await aggregate_prices(category, city)
    return {
        "items": rows,
        "count": len(rows),
        "disclaimer": "Prețuri orientative bazate pe observații de piață. Cele marcate „preliminar\u201d provin din cercetare de piață, nu din tranzacții pe platformă.",
    }


@router.get("/prices/seo-pages")
async def seo_price_pages_index():
    """Public — lista paginilor SEO de prețuri (/preturi)."""
    from construction.price_seo import list_seo_pages
    return {"items": await list_seo_pages()}


@router.get("/prices/seo-pages/{slug}")
async def seo_price_page_detail(slug: str, city: Optional[str] = None):
    """Public — datele complete pentru o pagină SEO de prețuri (/preturi/{slug})."""
    from construction.price_seo import build_seo_page
    page = await build_seo_page(slug, city)
    if not page:
        raise HTTPException(404, "Pagina de prețuri nu există")
    return page


@router.get("/prices/seo-pages/{slug}/pulse")
async def seo_price_page_pulse(slug: str):
    """Public — Market Pulse (Faza 5): cerere reală + ofertă activă pe categoria paginii."""
    from datetime import datetime, timedelta, timezone
    from construction.price_seo import PRICE_SEO
    meta = PRICE_SEO.get(slug)
    if not meta:
        raise HTTPException(404, "Pagina de prețuri nu există")
    cat = meta["category"]
    since30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    requests_30d = await db.requests.count_documents({"category": cat, "created_at": {"$gte": since30}})
    open_now = await db.requests.count_documents({"category": cat, "status": "open"})
    specialists = await db.users.count_documents({
        "role": "specialist", "banned": {"$ne": True}, "deleted": {"$ne": True},
        "$or": [{"specialty": cat}, {"service_categories": cat}],
    })
    return {"category": cat, "requests_30d": requests_30d, "open_now": open_now, "active_specialists": specialists}


@router.get("/prices")
async def list_price_observations(
    category: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = 200,
    user=Depends(require_role("admin")),
):
    q = {}
    if category and category != "all":
        q["category"] = category
    if city and city != "all":
        q["city"] = city
    limit = max(1, min(int(limit), 500))
    items = [_clean(d) async for d in db.price_observations.find(q).sort("created_at", -1).limit(limit)]
    return {"items": items, "count": len(items)}


def _validate_price_row(row: dict) -> Optional[str]:
    from construction.prices import UNITS, EXPERIENCE_LEVELS
    if not row.get("category"):
        return "categoria lipsește"
    if not (row.get("service") or "").strip():
        return "serviciul lipsește"
    if not (row.get("city") or "").strip():
        return "orașul lipsește"
    if (row.get("unit") or "") not in UNITS:
        return f"unitate invalidă (permise: {', '.join(sorted(UNITS))})"
    if (row.get("experience_level") or "mid") not in EXPERIENCE_LEVELS:
        return "nivel experiență invalid (beginner/mid/expert)"
    try:
        pmin, pmed, pmax = float(row["price_min"]), float(row["price_med"]), float(row["price_max"])
    except (KeyError, TypeError, ValueError):
        return "prețurile min/med/max trebuie să fie numere"
    if not (0 < pmin <= pmed <= pmax):
        return "condiția 0 < min ≤ med ≤ max nu e respectată"
    return None


@router.post("/prices")
async def add_price_observation(payload: dict = Body(...), user=Depends(require_role("admin"))):
    err = _validate_price_row(payload)
    if err:
        raise HTTPException(400, err)
    doc = {
        "id": uuid.uuid4().hex,
        "category": payload["category"],
        "service": payload["service"].strip()[:120],
        "city": payload["city"].strip()[:60],
        "unit": payload["unit"],
        "price_min": float(payload["price_min"]),
        "price_med": float(payload["price_med"]),
        "price_max": float(payload["price_max"]),
        "experience_level": payload.get("experience_level") or "mid",
        "source": "admin_manual",
        "notes": (payload.get("notes") or "")[:300],
        "created_by": user.get("email") or "",
        "created_at": _now(),
    }
    await db.price_observations.insert_one({**doc})
    return _clean(doc)


@router.delete("/prices/{obs_id}")
async def delete_price_observation(obs_id: str, user=Depends(require_role("admin"))):
    res = await db.price_observations.delete_one({"id": obs_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Observație inexistentă")
    return {"deleted": True}


@router.post("/prices/import-csv")
async def import_prices_csv(payload: dict = Body(...), user=Depends(require_role("admin"))):
    """Body: {"csv": "category,service,city,unit,price_min,price_med,price_max,experience_level\\n..."}"""
    raw = (payload.get("csv") or "").strip()
    if not raw:
        raise HTTPException(400, "CSV gol")
    reader = csv.DictReader(io.StringIO(raw))
    required = {"category", "service", "city", "unit", "price_min", "price_med", "price_max"}
    if not reader.fieldnames or not required.issubset({(f or "").strip() for f in reader.fieldnames}):
        raise HTTPException(400, f"Header CSV invalid. Coloane obligatorii: {', '.join(sorted(required))} (+opțional experience_level, notes)")
    imported, errors = 0, []
    for i, row in enumerate(reader, start=2):
        row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
        err = _validate_price_row(row)
        if err:
            errors.append(f"linia {i}: {err}")
            continue
        await db.price_observations.insert_one({
            "id": uuid.uuid4().hex,
            "category": row["category"],
            "service": row["service"][:120],
            "city": row["city"][:60],
            "unit": row["unit"],
            "price_min": float(row["price_min"]),
            "price_med": float(row["price_med"]),
            "price_max": float(row["price_max"]),
            "experience_level": row.get("experience_level") or "mid",
            "source": "csv_import",
            "notes": (row.get("notes") or "")[:300],
            "created_by": user.get("email") or "",
            "created_at": _now(),
        })
        imported += 1
    return {"imported": imported, "errors": errors[:20], "error_count": len(errors)}


@router.get("/prices/export")
async def export_prices_csv(user=Depends(require_role("admin"))):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["category", "service", "city", "unit", "price_min", "price_med", "price_max",
                     "experience_level", "source", "notes", "created_at"])
    async for r in db.price_observations.find({}).sort("category", 1):
        writer.writerow([r.get("category"), r.get("service"), r.get("city"), r.get("unit"),
                         r.get("price_min"), r.get("price_med"), r.get("price_max"),
                         r.get("experience_level"), r.get("source"), r.get("notes"), r.get("created_at")])
    buf.seek(0)
    fname = f"price_observatory_{datetime.now(timezone.utc).date().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


# ============================ PROJECT CENTRAL ============================
async def _query_projects(
    category: Optional[str], city: Optional[str], status: Optional[str],
    q: Optional[str], min_value: Optional[float], max_value: Optional[float],
    limit: int,
) -> list:
    query: dict = {}
    if category and category != "all":
        query["category"] = category
    if status and status != "all":
        query["status"] = status
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"title": rx}, {"client_name": rx}, {"specialist_name": rx}]
    if min_value is not None or max_value is not None:
        rng = {}
        if min_value is not None:
            rng["$gte"] = min_value
        if max_value is not None:
            rng["$lte"] = max_value
        query["budget_estimate"] = rng

    items = []
    async for d in db.requests.find(query).sort("created_at", -1).limit(int(limit) * 3):
        items.append(d)

    # Attach city from properties (batch)
    prop_ids = {d.get("property_id") for d in items if d.get("property_id")}
    cities = {}
    obj_ids = []
    for pid in prop_ids:
        try:
            obj_ids.append(ObjectId(pid))
        except Exception:  # noqa: BLE001
            pass
    if obj_ids:
        async for p in db.properties.find({"_id": {"$in": obj_ids}}, {"city": 1, "zone": 1}):
            cities[str(p["_id"])] = p.get("city") or p.get("zone") or ""

    out = []
    for d in items:
        row = {
            "id": str(d.get("_id")),
            "title": d.get("title"),
            "category": d.get("category"),
            "subcategory": d.get("subcategory"),
            "status": d.get("status"),
            "budget_estimate": d.get("budget_estimate"),
            "escrow_amount": d.get("escrow_amount"),
            "client_name": d.get("client_name"),
            "specialist_name": d.get("specialist_name"),
            "city": cities.get(d.get("property_id"), ""),
            "created_at": d.get("created_at"),
        }
        if city and city.lower() not in (row["city"] or "").lower():
            continue
        out.append(row)
        if len(out) >= limit:
            break
    return out


@router.get("/projects")
async def project_central(
    category: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    min_value: Optional[float] = Query(default=None),
    max_value: Optional[float] = Query(default=None),
    limit: int = 100,
    user=Depends(require_role("admin")),
):
    limit = max(1, min(int(limit), 500))
    items = await _query_projects(category, city, status, q, min_value, max_value, limit)
    return {"items": items, "count": len(items)}


@router.get("/projects/export")
async def export_projects_csv(
    category: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
    min_value: Optional[float] = Query(default=None),
    max_value: Optional[float] = Query(default=None),
    user=Depends(require_role("admin")),
):
    items = await _query_projects(category, city, status, q, min_value, max_value, 2000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Titlu", "Categorie", "Subcategorie", "Status", "Buget (RON)",
                     "Escrow (RON)", "Client", "Specialist", "Oraș", "Creat la"])
    for r in items:
        writer.writerow([r["id"], r["title"], r["category"], r.get("subcategory") or "",
                         r["status"], r.get("budget_estimate") or "", r.get("escrow_amount") or "",
                         r.get("client_name") or "", r.get("specialist_name") or "",
                         r.get("city") or "", r.get("created_at") or ""])
    buf.seek(0)
    fname = f"construction_projects_{datetime.now(timezone.utc).date().isoformat()}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
