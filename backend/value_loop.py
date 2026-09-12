"""Value Loop Engine (Board Decision 002) — Legea 8 + Property Value Index.

1. enrich_on_closure(): fiecare lucrare CONFIRMATĂ îmbogățește Digital Twin:
   garanție automată, sănătate actualizată (bounded, nu $inc infinit), jurnal de documentare,
   evenimente canonice pe Event Bus, re-scoring PVI.
2. PVI (Property Value Index): scor 0-100 de MATURITATE & DOCUMENTARE a proprietății
   (nu prețul casei). Crește după fiecare audit / lucrare / îmbogățire Twin.
   Prezentat în limbaj de beneficii, cu motive ✔ — indicator principal pentru
   Mission Control și CEO Copilot.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from bson import ObjectId

from db import db

logger = logging.getLogger("propmanage.value_loop")

# Luni de garanție implicite per categorie de lucrare
WARRANTY_MONTHS = {
    "instalatii": 24, "plumbing": 24, "electric": 24, "electricity": 24,
    "hvac": 24, "clima": 24, "roofing": 36, "termopane": 60,
    "interior_design": 12, "painting": 12, "zugravit": 12,
}
DEFAULT_WARRANTY_MONTHS = 12

# Ce componentă de sănătate îmbunătățește fiecare categorie (bounded +4, cap 100)
HEALTH_COMPONENT = {
    "instalatii": "utilities_health", "plumbing": "utilities_health",
    "electric": "utilities_health", "electricity": "utilities_health",
    "hvac": "utilities_health", "clima": "utilities_health",
    "roofing": "structure_health", "zidarie": "structure_health",
    "painting": "structure_health", "zugravit": "structure_health",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded(cur, inc, cap=100):
    return min(cap, (cur if isinstance(cur, (int, float)) else 0) + inc)


# ============================================================================
# PVI — Property Value Index
# ============================================================================
async def compute_pvi(prop_id: str) -> dict:
    """Scor 0-100 din 6 componente de maturitate/documentare, cu motive în limbajul clientului."""
    try:
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    except Exception:
        prop = None
    if not prop:
        return {"score": 0, "reasons": [], "updated_at": _now()}

    twin = await db.twins.find_one({"property_id": prop_id})
    twin_full = bool(prop.get("twin_unlocked")) or (twin or {}).get("status") in ("approved", "validated")
    twin_partial = bool(twin)

    confirmed = await db.requests.count_documents({"property_id": prop_id, "status": "confirmed"})
    warranties = await db.warranties.count_documents({"property_id": prop_id, "status": "active", "until": {"$gte": _now()}})
    hh_docs = await db.hh_evaluations.count_documents({"property_id": prop_id})
    twin_assets = len((twin or {}).get("assets") or [])
    kg_links = await db.entity_links.count_documents({"$or": [{"from_id": prop_id}, {"to_id": prop_id}]})
    has_health = prop.get("health_score") is not None
    identity_ok = bool(prop.get("address")) and bool(prop.get("rooms") or prop.get("surface"))

    components = [
        # (cheie, etichetă beneficii, puncte obținute, puncte maxime)
        ("twin", "Digital Twin complet", 20 if twin_full else (10 if twin_partial else 0), 20),
        ("works", "Proiecte finalizate & documentate", round(min(confirmed, 5) / 5 * 20), 20),
        ("audit", "Stare tehnică evaluată (audit)", 15 if has_health else 0, 15),
        ("installations", "Instalații documentate", 15 if (twin_assets > 0 or hh_docs > 0) else 0, 15),
        ("warranties", "Garanții active", round(min(warranties, 3) / 3 * 15), 15),
        ("identity", "Identitate & documente complete", (7 if identity_ok else 0) + (8 if kg_links > 0 else 0), 15),
    ]
    score = sum(c[2] for c in components)
    reasons = [{"key": k, "label": label, "done": pts >= mx * 0.99, "points": pts, "max": mx}
               for k, label, pts, mx in components]
    return {"score": min(score, 100), "reasons": reasons, "updated_at": _now()}


async def refresh_pvi(prop_id: str, trigger: str = "manual") -> dict:
    """Recalculează PVI, îl salvează pe proprietate + istoric, emite eveniment la schimbare."""
    pvi = await compute_pvi(prop_id)
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)}, {"pvi": 1})
    prev = ((prop or {}).get("pvi") or {}).get("score")
    await db.properties.update_one({"_id": ObjectId(prop_id)}, {"$set": {"pvi": pvi}})
    await db.pvi_history.insert_one({"property_id": prop_id, "score": pvi["score"], "trigger": trigger, "ts": _now()})
    if prev is not None and pvi["score"] != prev:
        try:
            from event_bus import emit
            await emit("property.pvi_updated", property_id=prop_id,
                       payload={"from": prev, "to": pvi["score"], "trigger": trigger})
        except Exception:  # noqa: BLE001
            pass
    return pvi


async def pvi_delta_6m(prop_id: str, current: int) -> int:
    """Δ puncte față de acum 6 luni (baseline = cel mai vechi scor din fereastră sau primul istoric)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=182)).isoformat()
    baseline = await db.pvi_history.find_one(
        {"property_id": prop_id, "ts": {"$gte": cutoff}}, sort=[("ts", 1)]
    ) or await db.pvi_history.find_one({"property_id": prop_id}, sort=[("ts", 1)])
    if not baseline:
        return 0
    return current - int(baseline.get("score") or 0)


async def value_loop_summary() -> dict:
    """Indicatori strategici Value Loop pentru Mission Control / CEO Copilot."""
    scored, avg = 0, 0
    async for d in db.properties.aggregate([
        {"$match": {"pvi.score": {"$exists": True}}},
        {"$group": {"_id": None, "avg": {"$avg": "$pvi.score"}, "n": {"$sum": 1}}},
    ]):
        avg, scored = round(d.get("avg") or 0, 1), d.get("n", 0)
    total = await db.properties.estimated_document_count()
    warranties = await db.warranties.count_documents({"status": "active"})
    enriched = await db.activity_events.count_documents({"event_type": "twin.enriched"})
    return {
        "avg_pvi": avg, "properties_scored": scored, "properties_total": total,
        "active_warranties": warranties, "twin_enrichments": enriched,
    }


# ============================================================================
# JOB CLOSURE ENRICHMENT — Legea 8
# ============================================================================
async def enrich_on_closure(req: dict, actor: dict) -> dict:
    """La confirmarea lucrării: garanție + sănătate + documentare + PVI. Best-effort per pas."""
    prop_id = req.get("property_id")
    req_id = str(req.get("_id") or req.get("id") or "")
    if not prop_id:
        return {}
    category = (req.get("category") or "").lower()
    result: dict = {}

    # 1. Garanție automată (idempotent per cerere)
    try:
        if not await db.warranties.find_one({"request_id": req_id}):
            months = WARRANTY_MONTHS.get(category, DEFAULT_WARRANTY_MONTHS)
            until = (datetime.now(timezone.utc) + timedelta(days=30 * months)).isoformat()
            warranty = {
                "id": uuid.uuid4().hex, "property_id": prop_id, "request_id": req_id,
                "title": req.get("title"), "category": category,
                "specialist_id": req.get("specialist_id"), "specialist_name": req.get("specialist_name"),
                "months": months, "starts_at": _now(), "until": until,
                "status": "active", "created_at": _now(),
            }
            await db.warranties.insert_one(warranty)
            result["warranty_months"] = months
            from event_bus import emit
            await emit("warranty.created", request_id=req_id, property_id=prop_id, actor=actor,
                       payload={"months": months, "until": until, "title": req.get("title")})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[value_loop] warranty failed: {e}")

    # 2. Sănătate — actualizare BOUNDED (înlocuiește $inc-ul nelimitat istoric)
    try:
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
        if prop:
            sets = {"documents_health": _bounded(prop.get("documents_health"), 2)}
            comp = HEALTH_COMPONENT.get(category)
            if comp:
                sets[comp] = _bounded(prop.get(comp), 4)
            merged = {**prop, **sets}
            parts = [merged.get(f) for f in ("structure_health", "utilities_health", "documents_health")
                     if isinstance(merged.get(f), (int, float))]
            if parts:
                sets["health_score"] = min(100, round(sum(parts) / len(parts)))
            sets["last_enriched_at"] = _now()
            await db.properties.update_one({"_id": ObjectId(prop_id)},
                                           {"$set": sets, "$inc": {"twin_works_documented": 1}})
            result["health_score"] = sets.get("health_score")
            from event_bus import emit
            await emit("health.updated", request_id=req_id, property_id=prop_id,
                       payload={"health_score": sets.get("health_score"), "trigger": "job_closure"})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[value_loop] health update failed: {e}")

    # 3. Documentarea Twin-ului (eveniment canonic — timeline-ul Cărții Casei)
    try:
        from event_bus import emit
        await emit("twin.enriched", request_id=req_id, property_id=prop_id, actor=actor,
                   payload={"title": req.get("title"), "category": category,
                            "photos": len(req.get("photos") or []),
                            "value_ron": req.get("escrow_amount")})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[value_loop] twin event failed: {e}")

    # 4. PVI re-scoring — bucla de valoare se închide
    try:
        result["pvi"] = await refresh_pvi(prop_id, trigger="job_closure")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[value_loop] pvi refresh failed: {e}")
    return result
