"""Oportunități comerciale — Revenue Hunter (Sprint 2 / Felia 1, Board Review 001).

Client: inbox de decizii (vezi / acceptă / respinge) — aprobarea clientului = click.
Acceptarea creează o CERERE REALĂ (intră în pipeline-ul existent de matching).
Admin: statistici de conversie (Legea 21 — validare prin piață) + kill-switch + run manual.
"""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role
from event_bus import emit
from revenue_hunter import SERVICES, is_enabled, run_revenue_hunter_tick, scan_property_throttled
from services import notify

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["opportunities"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/client/opportunities")
async def my_opportunities(user: dict = Depends(require_role("client"))):
    """Oportunitățile active pentru proprietățile clientului (lazy scan cu throttle)."""
    props = await db.properties.find({"owner_id": user["id"]}).to_list(20)
    if await is_enabled():
        for p in props:
            try:
                await scan_property_throttled(p)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"lazy scan failed: {e}")
    prop_ids = [str(p["_id"]) for p in props]
    opps = []
    async for o in db.revenue_opportunities.find(
        {"property_id": {"$in": prop_ids}, "status": "active"}, {"_id": 0}
    ).sort("score", -1).limit(5):
        opps.append(o)
    return {"opportunities": opps}


@router.post("/client/opportunities/{opp_id}/accept")
async def accept_opportunity(opp_id: str, user: dict = Depends(require_role("client"))):
    """Aprobarea clientului → cerere reală în pipeline-ul existent (ciclul Constituției)."""
    opp = await db.revenue_opportunities.find_one({"id": opp_id, "owner_id": user["id"], "status": "active"})
    if not opp:
        raise HTTPException(404, "Oportunitatea nu există sau a fost deja procesată")
    prop = await db.properties.find_one({"_id": ObjectId(opp["property_id"]), "owner_id": user["id"]})
    if not prop:
        raise HTTPException(404, "Proprietatea nu există")

    meta = SERVICES.get(opp["service"], {})
    doc = {
        "property_id": opp["property_id"],
        "category": meta.get("category", "other"),
        "title": f"{opp['service_label']}: {prop.get('name', '')}",
        "description": f"{opp['benefit']} (Recomandare AI acceptată de client — Revenue Hunter)",
        "priority": "normal",
        "budget_estimate": opp.get("estimated_value_ron"),
        "county": prop.get("county") or prop.get("zone") or prop.get("city"),
        "photos": None, "taxonomy_node_id": None, "subcategory": opp["service"],
        "client_id": user["id"],
        "client_name": user["name"],
        "property_name": prop.get("name"),
        "property_address": prop.get("address"),
        "status": "open",
        "specialist_id": None, "specialist_name": None, "escrow_amount": None,
        "source": "revenue_hunter",
        "created_at": _now(),
    }
    res = await db.requests.insert_one(doc)
    req_id = str(res.inserted_id)

    await db.revenue_opportunities.update_one(
        {"id": opp_id}, {"$set": {"status": "accepted", "acted_at": _now(), "request_id": req_id}}
    )
    await emit("request.created", request_id=req_id, property_id=opp["property_id"], actor=user,
               payload={"title": doc["title"], "category": doc["category"], "source": "revenue_hunter"})
    await emit("recommendation.accepted", property_id=opp["property_id"], actor=user,
               payload={"service": opp["service"], "value": opp.get("estimated_value_ron"), "opp_id": opp_id})

    # GI-4a: decizia clientului intră în Ledger (SSoT decizii AI) → Outcome Tracker o urmărește
    from learning_engine import ledger_entry
    await db.ai_decision_ledger.insert_one(ledger_entry(
        "opportunity", "revenue_hunter", opp.get("title") or f"Oportunitate {opp['service_label']}",
        opp.get("benefit") or "", "accepted", user.get("email") or user["id"],
        target={"user_id": user["id"], "property_id": opp["property_id"], "service": opp["service"]},
        extra={"opp_id": opp_id, "request_id": req_id, "estimated_value_ron": opp.get("estimated_value_ron")}))

    # Rutare umană: serviciile PropManage (twin/audit) merg la admini; design → specialiști potriviți
    try:
        if opp["service"] in ("digital_twin", "audit_tehnic"):
            async for adm in db.users.find({"role": "admin"}).limit(5):
                await notify(str(adm["_id"]), f"💰 Comandă serviciu: {opp['service_label']}",
                             f"{user['name']} a acceptat recomandarea Revenue Hunter pentru {prop.get('name')} (~{opp.get('estimated_value_ron')} RON).",
                             type_="revenue", link="/admin")
        else:
            async for s in db.users.find({"role": "specialist", "specialty": doc["category"]}).limit(20):
                await notify(str(s["_id"]), f"Lead nou: {doc['title']}",
                             f"Cerere {opp['service_label']} — buget estimat {opp.get('estimated_value_ron')} RON.",
                             type_="lead", link="/specialist")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"opportunity notify failed: {e}")

    return {"ok": True, "request_id": req_id}


@router.post("/client/opportunities/{opp_id}/dismiss")
async def dismiss_opportunity(opp_id: str, user: dict = Depends(require_role("client"))):
    opp = await db.revenue_opportunities.find_one({"id": opp_id, "owner_id": user["id"], "status": "active"})
    if not opp:
        raise HTTPException(404, "Oportunitatea nu există sau a fost deja procesată")
    await db.revenue_opportunities.update_one({"id": opp_id}, {"$set": {"status": "dismissed", "acted_at": _now()}})
    await emit("recommendation.dismissed", property_id=opp["property_id"], actor=user,
               payload={"service": opp["service"], "opp_id": opp_id})
    from learning_engine import ledger_entry
    await db.ai_decision_ledger.insert_one(ledger_entry(
        "opportunity", "revenue_hunter", opp.get("title") or f"Oportunitate {opp.get('service_label')}",
        opp.get("benefit") or "", "dismissed", user.get("email") or user["id"],
        target={"user_id": user["id"], "property_id": opp["property_id"], "service": opp["service"]},
        extra={"opp_id": opp_id}))
    return {"ok": True}


# ============================================================================
# ADMIN — validare prin piață (Legea 21) + control agent
# ============================================================================
@router.get("/admin/revenue-hunter/stats")
async def revenue_hunter_stats(user: dict = Depends(require_role("admin"))):
    by_status: dict = {}
    async for d in db.revenue_opportunities.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        by_status[d["_id"]] = d["n"]
    by_service: dict = {}
    async for d in db.revenue_opportunities.aggregate([{"$group": {"_id": "$service", "n": {"$sum": 1}, "value": {"$sum": "$estimated_value_ron"}}}]):
        by_service[d["_id"]] = {"count": d["n"], "value_ron": round(d.get("value") or 0, 2)}
    pipeline_value = 0.0
    async for d in db.revenue_opportunities.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "v": {"$sum": "$estimated_value_ron"}}},
    ]):
        pipeline_value = round(d.get("v") or 0, 2)
    accepted = by_status.get("accepted", 0)
    dismissed = by_status.get("dismissed", 0)
    acted = accepted + dismissed
    return {
        "enabled": await is_enabled(),
        "by_status": by_status,
        "by_service": by_service,
        "active_pipeline_value_ron": pipeline_value,
        "conversion_rate": round(accepted / acted * 100, 1) if acted else None,
    }


@router.post("/admin/revenue-hunter/run")
async def revenue_hunter_run(user: dict = Depends(require_role("admin"))):
    return await run_revenue_hunter_tick()


@router.post("/admin/revenue-hunter/toggle")
async def revenue_hunter_toggle(body: dict = Body(...), user: dict = Depends(require_role("admin"))):
    from orchestrator.engine import set_playbook_enabled
    enabled = bool(body.get("enabled", True))
    await set_playbook_enabled("revenue_hunter", enabled, by=user.get("email", "admin"))
    return {"ok": True, "enabled": enabled}
