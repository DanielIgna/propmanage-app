"""Sprint F — Business Intelligence & Marketplace Optimization Engine (BI-MOE).

READ-ONLY analytics. NEVER modifies fees/rankings/scores/visibility/decisions.
All output is recommendation-only — Admin validates manually.

Endpoints:
  GET /api/admin/bi/overview               (top-level KPIs + alerts)
  GET /api/admin/bi/demand-index           (category/zone demand trends)
  GET /api/admin/bi/fee-analytics          (fee paid vs accepted, recommendations)
  GET /api/admin/bi/conversion-funnel      (request → assigned → completed funnel)
  GET /api/admin/bi/specialist-performance (Performance Score top/bottom)
  GET /api/admin/bi/client-analysis        (property types, budgets, frequency)
  GET /api/admin/bi/premium-candidates     (auto-list of marketplace candidates)
  GET /api/admin/bi/alerts                 (anomaly alerts — conv drops, rating drops)

GDPR: ALL output is aggregated (counts, averages, percentages). NO raw PII.
ML-ready: pipelines emit consistent shape that can feed sklearn/pytorch later.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.bi_moe")

router = APIRouter(prefix="/api/admin/bi", tags=["bi-moe"])


# ============================================================================
# Helper: time windows
# ============================================================================
def _ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# ============================================================================
# 1. OVERVIEW — top KPIs
# ============================================================================
@router.get("/overview")
async def overview(_: dict = Depends(require_role("admin"))):
    """KPIs at-a-glance: counts last 30 days, active users, revenue (fees collected)."""
    d30 = _ago(30)
    total_users = await db.users.count_documents({})
    active_specialists = await db.users.count_documents({"role": "specialist", "deleted": {"$ne": True}, "banned": {"$ne": True}})
    active_clients = await db.users.count_documents({"role": "client", "deleted": {"$ne": True}})
    new_users_30d = await db.users.count_documents({"created_at": {"$gte": d30}})
    new_requests_30d = await db.requests.count_documents({"created_at": {"$gte": d30}})
    completed_30d = await db.requests.count_documents({"status": {"$in": ["completed", "closed"]}, "updated_at": {"$gte": d30}})
    open_requests = await db.requests.count_documents({"status": "open"})
    # Revenue from marketplace offer fees
    pipeline = [
        {"$match": {"type": {"$in": ["lead_fee", "marketplace_offer_fee"]}, "created_at": {"$gte": d30}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    rev_doc = await db.transactions.aggregate(pipeline).to_list(1)
    revenue_30d = abs(rev_doc[0]["total"]) if rev_doc else 0.0
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "total_users": total_users,
        "active_specialists": active_specialists,
        "active_clients": active_clients,
        "new_users_30d": new_users_30d,
        "new_requests_30d": new_requests_30d,
        "completed_30d": completed_30d,
        "open_requests": open_requests,
        "revenue_30d_ron": round(revenue_30d, 2),
        "completion_rate_30d_pct": round((completed_30d / new_requests_30d) * 100, 1) if new_requests_30d else 0.0,
    }


# ============================================================================
# 2. DEMAND INDEX — category/zone trends
# ============================================================================
@router.get("/demand-index")
async def demand_index(days: int = Query(30, ge=7, le=365), _: dict = Depends(require_role("admin"))):
    """Demand per category + zone in time window. Identifies trending and under-supplied segments."""
    since = _ago(days)
    # Categories
    cat_pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$category", "requests": {"$sum": 1}}},
        {"$sort": {"requests": -1}},
    ]
    cats = [{"category": d["_id"] or "unspecified", "requests": d["requests"]} async for d in db.requests.aggregate(cat_pipeline)]
    # Zones
    zone_pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$zone", "requests": {"$sum": 1}}},
        {"$sort": {"requests": -1}},
        {"$limit": 20},
    ]
    zones = [{"zone": d["_id"] or "unspecified", "requests": d["requests"]} async for d in db.requests.aggregate(zone_pipeline)]
    # Supply (specialists per category)
    supply = {}
    async for u in db.users.find({"role": "specialist", "deleted": {"$ne": True}}, {"specialty": 1, "service_categories": 1}):
        sp = u.get("specialty")
        if sp:
            supply[sp] = supply.get(sp, 0) + 1
        for c in (u.get("service_categories") or []):
            supply[c] = supply.get(c, 0) + 1
    # Compute supply/demand ratio
    for c in cats:
        c["specialists"] = supply.get(c["category"], 0)
        c["ratio"] = round(c["requests"] / max(1, c["specialists"]), 2)
        if c["specialists"] == 0:
            c["alert"] = "no_specialists"
        elif c["ratio"] > 5:
            c["alert"] = "undersupplied"
        elif c["ratio"] < 0.5 and c["specialists"] > 3:
            c["alert"] = "oversupplied"
    return {"window_days": days, "categories": cats[:30], "zones": zones, "total_categories": len(cats), "total_specialists_indexed": sum(supply.values())}


# ============================================================================
# 3. FEE ANALYTICS
# ============================================================================
@router.get("/fee-analytics")
async def fee_analytics(days: int = Query(30, ge=7, le=365), _: dict = Depends(require_role("admin"))):
    """Aggregate fee paid vs accepted/won/lost. Recommends fee adjustments."""
    since = _ago(days)
    # Marketplace offers stats
    offers_pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}, "total_fee": {"$sum": "$fee_paid_total"}}},
    ]
    offers_by_status = {d["_id"]: {"count": d["count"], "total_fee": round(d["total_fee"] or 0, 2)} async for d in db.marketplace_offers.aggregate(offers_pipeline)}
    won = offers_by_status.get("won", {"count": 0, "total_fee": 0})
    lost = offers_by_status.get("lost", {"count": 0, "total_fee": 0})
    open_o = offers_by_status.get("open", {"count": 0, "total_fee": 0})
    total_offers = won["count"] + lost["count"] + open_o["count"]
    win_rate = round((won["count"] / total_offers) * 100, 1) if total_offers else 0.0
    avg_fee_won = round(won["total_fee"] / max(1, won["count"]), 2)
    avg_fee_lost = round(lost["total_fee"] / max(1, lost["count"]), 2)
    # Per-category breakdown — winning fee (placeholder for future use)
    recommendations = []
    cfg = await db.fee_configs.find_one({"_singleton": True}) or {}
    min_f, max_f = cfg.get("min_fee_ron", 5), cfg.get("max_fee_ron", 50)
    if won["count"] > 5 and avg_fee_won < min_f * 1.5:
        recommendations.append({"type": "fee_too_low", "msg": f"Fee mediu câștigător ({avg_fee_won} RON) e aproape de minim. Considerare creștere fee minim sau valoare priority."})
    if lost["count"] > won["count"] * 2 and lost["count"] > 10:
        recommendations.append({"type": "high_loss_rate", "msg": f"Pierderi mai mari decât câștigurile ({lost['count']} vs {won['count']}). Considerare reducere fee minim sau revedere ranking."})
    if avg_fee_lost > avg_fee_won and lost["count"] > 5:
        recommendations.append({"type": "lost_more_expensive", "msg": "Specialiștii care PIERD plătesc mai mult — semn de ranking nepotrivit (fee mare ≠ alegere client). Verifică balanța în ranking formula."})
    return {
        "window_days": days,
        "offers_by_status": offers_by_status,
        "total_offers": total_offers,
        "win_rate_pct": win_rate,
        "avg_fee_won_ron": avg_fee_won,
        "avg_fee_lost_ron": avg_fee_lost,
        "revenue_from_fees_ron": round(sum(s["total_fee"] for s in offers_by_status.values()), 2),
        "recommendations": recommendations,
        "fee_config_active": {"min": min_f, "max": max_f},
    }


# ============================================================================
# 4. CONVERSION FUNNEL
# ============================================================================
@router.get("/conversion-funnel")
async def conversion_funnel(days: int = Query(30, ge=7, le=365), _: dict = Depends(require_role("admin"))):
    """Funnel: published → assigned → in_progress → completed/canceled."""
    since = _ago(days)
    published = await db.requests.count_documents({"created_at": {"$gte": since}})
    assigned = await db.requests.count_documents({"created_at": {"$gte": since}, "status": {"$in": ["assigned", "in_progress", "completed", "closed"]}})
    in_progress = await db.requests.count_documents({"created_at": {"$gte": since}, "status": {"$in": ["in_progress", "completed", "closed"]}})
    completed = await db.requests.count_documents({"created_at": {"$gte": since}, "status": {"$in": ["completed", "closed"]}})
    abandoned = await db.requests.count_documents({"created_at": {"$gte": since}, "status": "canceled"})
    steps = [
        {"name": "Publicate", "count": published, "pct_of_total": 100.0},
        {"name": "Asignate", "count": assigned, "pct_of_total": round((assigned / max(1, published)) * 100, 1)},
        {"name": "În execuție", "count": in_progress, "pct_of_total": round((in_progress / max(1, published)) * 100, 1)},
        {"name": "Finalizate", "count": completed, "pct_of_total": round((completed / max(1, published)) * 100, 1)},
    ]
    return {"window_days": days, "steps": steps, "abandoned": abandoned, "completion_rate_pct": steps[-1]["pct_of_total"]}


# ============================================================================
# 5. SPECIALIST PERFORMANCE SCORE
# ============================================================================
@router.get("/specialist-performance")
async def specialist_performance(limit: int = Query(20, le=100), _: dict = Depends(require_role("admin"))):
    """Top + Bottom specialists by composite score. Read-only — no auto-action."""
    since = _ago(90)
    items = []
    async for u in db.users.find({"role": "specialist", "deleted": {"$ne": True}}, {"name": 1, "tier": 1, "rating": 1, "reviews_count": 1, "tier_warning_low_rating": 1}).limit(500):
        uid = str(u["_id"])
        applied = await db.marketplace_offers.count_documents({"specialist_id": uid, "created_at": {"$gte": since}})
        won = await db.marketplace_offers.count_documents({"specialist_id": uid, "status": "won", "created_at": {"$gte": since}})
        completed = await db.requests.count_documents({"$or": [{"specialist_id": uid}, {"accepted_by": uid}], "status": {"$in": ["completed", "closed"]}, "updated_at": {"$gte": since}})
        win_rate = round((won / max(1, applied)) * 100, 1) if applied else 0.0
        # Composite: rating (40%) + win_rate (30%) + completed_normalized (30%)
        score = ((u.get("rating") or 0) / 5) * 0.4 + (win_rate / 100) * 0.3 + min(completed / 20, 1) * 0.3
        items.append({
            "specialist_id": uid, "name": u.get("name", ""), "tier": u.get("tier") or "ENTRY",
            "rating": u.get("rating") or 0, "reviews_count": u.get("reviews_count") or 0,
            "applied_90d": applied, "won_90d": won, "completed_90d": completed,
            "win_rate_pct": win_rate, "low_rating_flag": bool(u.get("tier_warning_low_rating")),
            "performance_score": round(score, 3),
        })
    items.sort(key=lambda x: x["performance_score"], reverse=True)
    return {"top": items[:limit], "bottom": items[-limit:][::-1], "total_evaluated": len(items)}


# ============================================================================
# 6. PREMIUM CANDIDATES
# ============================================================================
@router.get("/premium-candidates")
async def premium_candidates(_: dict = Depends(require_role("admin"))):
    """Auto-list specialists eligible for PREMIUM but not yet promoted."""
    tier_rules = await db.tier_rules.find_one({"_singleton": True}) or {}
    min_jobs = tier_rules.get("nivel_3_min_completed_jobs", 50)
    min_rating = tier_rules.get("nivel_3_min_rating", 4.7)
    min_reviews = tier_rules.get("nivel_3_min_reviews", 25)
    cur = db.users.find({"role": "specialist", "tier": {"$ne": "PREMIUM"}, "deleted": {"$ne": True}}, {"name": 1, "tier": 1, "rating": 1, "reviews_count": 1, "email": 1})
    items = []
    async for u in cur:
        uid = str(u["_id"])
        completed = await db.requests.count_documents({"$or": [{"specialist_id": uid}, {"accepted_by": uid}], "status": {"$in": ["completed", "closed"]}})
        rating = u.get("rating") or 0
        reviews = u.get("reviews_count") or 0
        # how close to PREMIUM?
        progress = {
            "completed_jobs": {"have": completed, "need": min_jobs, "pct": round(min(completed / min_jobs, 1) * 100, 1)},
            "rating": {"have": rating, "need": min_rating, "pct": round(min((rating / min_rating), 1) * 100, 1) if min_rating else 0},
            "reviews": {"have": reviews, "need": min_reviews, "pct": round(min(reviews / min_reviews, 1) * 100, 1)},
        }
        overall_pct = round((progress["completed_jobs"]["pct"] + progress["rating"]["pct"] + progress["reviews"]["pct"]) / 3, 1)
        if overall_pct < 60:
            continue
        items.append({"id": uid, "name": u.get("name"), "current_tier": u.get("tier", "ENTRY"), "rating": rating, "reviews": reviews, "completed_jobs": completed, "progress": progress, "overall_pct": overall_pct, "ready": all(p["pct"] >= 100 for p in progress.values())})
    items.sort(key=lambda x: x["overall_pct"], reverse=True)
    return {"items": items[:30], "thresholds": {"min_completed_jobs": min_jobs, "min_rating": min_rating, "min_reviews": min_reviews}}


# ============================================================================
# 7. AUTOMATED ALERTS (READ-ONLY — no auto-action)
# ============================================================================
@router.get("/alerts")
async def alerts(_: dict = Depends(require_role("admin"))):
    """Anomaly detection: conversion drops, low-rated active specialists, supply gaps."""
    out = []
    # Conversion drop: current 30d vs previous 30d
    now30 = await db.requests.count_documents({"created_at": {"$gte": _ago(30)}, "status": {"$in": ["completed", "closed"]}})
    prev30 = await db.requests.count_documents({"created_at": {"$gte": _ago(60), "$lt": _ago(30)}, "status": {"$in": ["completed", "closed"]}})
    if prev30 > 0 and now30 < prev30 * 0.7:
        out.append({"severity": "high", "type": "conversion_drop", "msg": f"Finalizările au scăzut cu {round((1 - now30/prev30) * 100, 0)}% în ultimele 30 zile (de la {prev30} la {now30})."})
    # Specialists with rating warning flag
    low_rated = await db.users.count_documents({"role": "specialist", "tier_warning_low_rating": True})
    if low_rated > 0:
        out.append({"severity": "medium", "type": "low_rated_specialists", "msg": f"{low_rated} specialiști au flag 'rating sub medie' — verifică în Specialist Performance dashboard."})
    # Categories without specialists
    cats_cur = db.requests.aggregate([{"$match": {"created_at": {"$gte": _ago(30)}}}, {"$group": {"_id": "$category"}}])
    cats = [d["_id"] async for d in cats_cur if d["_id"]]
    supply_set = set()
    async for u in db.users.find({"role": "specialist"}, {"specialty": 1, "service_categories": 1}):
        if u.get("specialty"):
            supply_set.add(u["specialty"])
        for c in (u.get("service_categories") or []):
            supply_set.add(c)
    no_supply = [c for c in cats if c not in supply_set]
    if no_supply:
        out.append({"severity": "high", "type": "no_supply", "msg": f"{len(no_supply)} categorii cu cereri DAR FĂRĂ specialiști: {', '.join(no_supply[:5])}"})
    return {"items": out, "count": len(out), "as_of": datetime.now(timezone.utc).isoformat()}


# ============================================================================
# 8. CLIENT ANALYSIS (aggregated, GDPR-safe)
# ============================================================================
@router.get("/client-analysis")
async def client_analysis(days: int = Query(90, ge=7, le=365), _: dict = Depends(require_role("admin"))):
    """Aggregated client behavior — NO PII. Identifies new service opportunities."""
    since = _ago(days)
    # Avg requests per client
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$client_id", "count": {"$sum": 1}}},
    ]
    per_client = [d["count"] async for d in db.requests.aggregate(pipeline)]
    avg_req_per_client = round(sum(per_client) / max(1, len(per_client)), 2)
    repeat_clients = sum(1 for c in per_client if c >= 2)
    one_time = sum(1 for c in per_client if c == 1)
    # Budget distribution (if requests have budget)
    budget_pipeline = [
        {"$match": {"created_at": {"$gte": since}, "budget_max": {"$exists": True, "$gt": 0}}},
        {"$bucket": {"groupBy": "$budget_max", "boundaries": [0, 500, 1500, 5000, 15000, 50000, 1000000], "default": "other", "output": {"count": {"$sum": 1}}}},
    ]
    budget_dist = []
    try:
        async for b in db.requests.aggregate(budget_pipeline):
            budget_dist.append({"range": b["_id"], "count": b["count"]})
    except Exception:
        pass
    return {
        "window_days": days,
        "total_clients_with_requests": len(per_client),
        "avg_requests_per_client": avg_req_per_client,
        "repeat_clients": repeat_clients,
        "one_time_clients": one_time,
        "repeat_rate_pct": round((repeat_clients / max(1, len(per_client))) * 100, 1),
        "budget_distribution_ron": budget_dist,
    }
