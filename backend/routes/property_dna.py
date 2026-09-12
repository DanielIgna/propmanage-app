"""Property DNA API (Sprint 1 / Felia 1 — Prompt 005).

GET /api/properties/{prop_id}/dna — proiecția logică canonică a proprietății, organizată pe
Capability Map. Read-only, ZERO migrare: agregă colecțiile existente (properties, twins,
digital_twin_*, hh_*, requests, activity_events, entity_links, service_contracts).
Motoarele AI și Mission Control vor consuma ACEST contract, nu structura fizică a bazei.

GET /api/admin/agent-runs — jurnalul central al agenților (observabilitate cron/agenți).
"""
import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["property_dna"])

EVENT_TITLES = {
    "request.created": "Cerere creată",
    "request_created": "Cerere creată",
    "request.auto_assigned": "Specialist alocat automat (AI)",
    "request.assigned": "Specialist alocat",
    "request.completed": "Lucrare finalizată de specialist",
    "request.confirmed": "Lucrare confirmată de client",
    "offer.submitted": "Ofertă primită",
    "offer.accepted": "Ofertă acceptată",
    "escrow.funded": "Avans plătit (escrow)",
    "escrow.released": "Plată eliberată din escrow",
    "review.submitted": "Recenzie acordată",
    "dispute.opened": "Dispută deschisă",
    "dispute.resolved": "Dispută rezolvată",
    "twin.requested": "Digital Twin solicitat",
    "twin.validated": "Digital Twin validat",
    "warranty.expiring": "Garanție aproape de expirare",
    "warranty.registered": "Garanție înregistrată",
    "document.uploaded": "Document adăugat în cartea casei",
    "document.updated": "Document actualizat (versiune nouă)",
}


def _title_for(ev: dict) -> str:
    et = ev.get("event_type") or ""
    return EVENT_TITLES.get(et, et.replace(".", " ").replace("_", " ").capitalize())


async def _load_property_for(user: dict, prop_id: str) -> dict:
    try:
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    except Exception:
        prop = None
    if not prop:
        raise HTTPException(404, "Proprietatea nu există")
    role = user.get("active_view") or user.get("role")
    if role not in ("admin", "operator", "franchise_admin") and str(prop.get("owner_id")) != str(user.get("id")):
        raise HTTPException(403, "Nu ai acces la această proprietate")
    return prop


@router.get("/properties/{prop_id}/dna")
async def property_dna(prop_id: str, user: dict = Depends(get_current_user)):
    """Proiecția Property DNA — identitatea logică vie a proprietății (Prompt 005)."""
    prop = await _load_property_for(user, prop_id)

    # ── works: cereri/lucrări legate de proprietate ──────────────────────────
    reqs = await db.requests.find({"property_id": prop_id}).sort("created_at", -1).to_list(300)
    by_status: dict = {}
    for r in reqs:
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
    active = [r for r in reqs if r.get("status") not in ("confirmed", "cancelled")]

    # ── financial: investiția totală prin platformă + garanții ──────────────
    total_invested = sum(float(r.get("escrow_amount") or 0) for r in reqs if r.get("status") == "confirmed")
    warranties_active = await db.warranties.count_documents({"property_id": prop_id, "status": "active"})

    # ── twin: starea Digital Twin ────────────────────────────────────────────
    twin = await db.twins.find_one({"property_id": prop_id})
    twin_models = await db.digital_twin_models.count_documents({"property_id": prop_id})
    twin_projects = await db.digital_twin_projects.count_documents({"property_id": prop_id})
    twin_assets = len((twin or {}).get("assets") or [])

    # ── health: House Health + scoruri ───────────────────────────────────────
    health_score = prop.get("health_score")

    # ── relations: Knowledge Graph ───────────────────────────────────────────
    kg_links = await db.entity_links.count_documents({"$or": [{"from_id": prop_id}, {"to_id": prop_id}]})

    # ── documents: Document Vault (CX-2 — sursa reală) + mentenanță ─────────
    doc_rows = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}, {"category": 1}
    ).to_list(500)
    docs_count = len(doc_rows)
    docs_by_cat: dict = {}
    for _d in doc_rows:
        docs_by_cat[_d.get("category", "?")] = docs_by_cat.get(_d.get("category", "?"), 0) + 1
    maint_count = await db.maintenance_logs.count_documents({"property_id": prop_id})

    # ── timeline: evenimente canonice + repere derivate din lucrări ─────────
    from event_bus import capability_of
    events = []
    seen = set()
    async for ev in db.activity_events.find({"property_id": prop_id}).sort("created_at", -1).limit(40):
        etype_norm = (ev.get("event_type") or "").replace("_", ".")
        seen.add((etype_norm, ev.get("request_id")))
        events.append({
            "type": ev.get("event_type"),
            "capability": ev.get("capability") or capability_of(ev.get("event_type")),
            "title": _title_for(ev),
            "actor": ev.get("actor_name"),
            "timestamp": ev.get("created_at"),
            "request_id": ev.get("request_id"),
        })
    for r in reqs[:30]:
        rid = str(r["_id"])
        for field, etype, title in (
            ("created_at", "request.created", f"Cerere: {r.get('title', '')}"),
            ("completed_at", "request.completed", f"Finalizat: {r.get('title', '')}"),
            ("confirmed_at", "request.confirmed", f"Confirmat & plătit: {r.get('title', '')}"),
        ):
            if r.get(field) and (etype, rid) not in seen:
                events.append({
                    "type": etype, "capability": "works", "title": title,
                    "actor": r.get("specialist_name") or "—", "timestamp": r[field], "request_id": rid,
                })
    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    events = events[:30]

    # ── recommendations: oportunități comerciale active (Revenue Hunter) ────
    active_opps = await db.revenue_opportunities.count_documents({"property_id": prop_id, "status": "active"})
    top_opp = await db.revenue_opportunities.find_one(
        {"property_id": prop_id, "status": "active"}, {"_id": 0, "title": 1, "service_label": 1}, sort=[("score", -1)]
    )

    capabilities = {
        "identity": {
            "populated": bool(prop.get("name") or prop.get("address")),
            "data": {"name": prop.get("name"), "address": prop.get("address"), "type": prop.get("type"),
                     "rooms": prop.get("rooms"), "surface": prop.get("surface"), "created_at": prop.get("created_at")},
        },
        "health": {
            "populated": health_score is not None,
            "data": {"health_score": health_score, "structure": prop.get("structure_health"),
                     "utilities": prop.get("utilities_health"), "documents": prop.get("documents_health")},
        },
        "twin": {
            "populated": bool(twin or twin_models or twin_projects),
            "data": {"status": (twin or {}).get("status"), "models": twin_models,
                     "projects": twin_projects, "assets": twin_assets, "unlocked": bool(prop.get("twin_unlocked"))},
        },
        "works": {
            "populated": len(reqs) > 0,
            "data": {"total": len(reqs), "active": len(active), "by_status": by_status,
                     "recent": [{"title": r.get("title"), "status": r.get("status")} for r in reqs[:3]]},
        },
        "financial": {
            "populated": total_invested > 0 or warranties_active > 0,
            "data": {"total_invested_ron": round(total_invested, 2),
                     "confirmed_works": by_status.get("confirmed", 0), "warranties": warranties_active},
        },
        "documents": {
            "populated": docs_count > 0,
            "data": {"count": docs_count, "by_category": docs_by_cat, "twin_assets": twin_assets},
        },
        "relations": {
            "populated": kg_links > 0,
            "data": {"knowledge_graph_links": kg_links},
        },
        "maintenance": {"populated": maint_count > 0, "data": {"logs": maint_count}},
        "sensors": {"populated": False, "data": {}},
        "recommendations": {
            "populated": active_opps > 0,
            "data": {"active": active_opps, "top": (top_opp or {}).get("title")},
        },
    }
    populated = sum(1 for c in capabilities.values() if c["populated"])
    completeness = round(populated / len(capabilities) * 100)

    # ── PVI — Property Value Index (Board Decision 002) ─────────────────────
    from value_loop import pvi_delta_6m, refresh_pvi
    pvi = prop.get("pvi")
    if not pvi:
        pvi = await refresh_pvi(prop_id, trigger="dna_view")
    delta = await pvi_delta_6m(prop_id, pvi["score"])

    return {
        "property_id": prop_id,
        "dna_completeness": completeness,
        "capabilities_populated": populated,
        "capabilities_total": len(capabilities),
        "capabilities": capabilities,
        "pvi": {"score": pvi["score"], "delta_6m": delta, "reasons": pvi.get("reasons", [])},
        "timeline": events,
    }


# ============================================================================
# VALUE LOOP — indicatori pentru Mission Control / CEO Copilot (Board Decision 002)
# ============================================================================
@router.get("/admin/value-loop/stats")
async def value_loop_stats(user: dict = Depends(get_current_user)):
    role = user.get("active_view") or user.get("role")
    if role != "admin":
        raise HTTPException(403, "Doar admin")
    from value_loop import value_loop_summary
    return await value_loop_summary()


# ============================================================================
# AGENT RUNS — jurnalul central al agenților/cron-jobs (admin)
# ============================================================================
@router.get("/admin/agent-runs")
async def agent_runs(limit: int = 50, user: dict = Depends(get_current_user)):
    role = user.get("active_view") or user.get("role")
    if role != "admin":
        raise HTTPException(403, "Doar admin")
    limit = max(1, min(limit, 200))
    runs = []
    async for r in db.agent_runs.find({}, {"_id": 0}).sort("ts", -1).limit(limit):
        runs.append(r)
    total = await db.agent_runs.estimated_document_count()
    errors = await db.agent_runs.count_documents({"status": "error"})
    pipeline = [
        {"$match": {"status": "error"}},
        {"$group": {"_id": "$job_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 5},
    ]
    top_failing = [{"job_id": d["_id"], "errors": d["count"]} async for d in db.agent_runs.aggregate(pipeline)]
    return {"runs": runs, "total_recorded": total, "errors_recorded": errors, "top_failing": top_failing}
