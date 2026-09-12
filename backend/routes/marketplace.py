"""PropManage router: marketplace."""
import logging
from typing import Optional
from fastapi import APIRouter

from db import db
# (models import * removed — no symbols from models are used in this file)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["marketplace"])

# ============= PUBLIC MARKETPLACE =============

@router.get("/marketplace/specialists")
async def public_marketplace(
    category: Optional[str] = None,
    verified_only: bool = False,
    min_rating: Optional[float] = None,
    sort: str = "rating",  # rating, reviews, recent
    zone: Optional[str] = None,
    city: Optional[str] = None,
    style: Optional[str] = None,
):
    """Public endpoint: browse all specialists with filters. No auth required.

    Optional filters:
      - category: matches primary specialty OR service_categories.
      - zone:     matches a single coverage zone (sector/cartier).
      - city:     expands to ALL zones inside that city (uses regions collection).
      - style:    matches at least one portfolio item with that style.
    """
    q = {"role": "specialist", "deleted": {"$ne": True}, "medic_suspended": {"$ne": True}}
    if category:
        q["$or"] = [{"specialty": category}, {"service_categories": category}]
    if verified_only:
        q["verified"] = True
    if min_rating is not None:
        q["rating"] = {"$gte": min_rating}
    if zone:
        q["coverage_zones"] = zone
    elif city:
        # Expand city → all its zones, then match if specialist covers ANY of them.
        city_zones = await db.regions.distinct("zone", {"city": city})
        if city_zones:
            q["coverage_zones"] = {"$in": city_zones}
        else:
            # Unknown city → empty result set (avoid leaking unfiltered list).
            return []

    sort_map = {
        "rating": [("rating", -1), ("reviews_count", -1)],
        "reviews": [("reviews_count", -1)],
        "recent": [("created_at", -1)],
    }
    cursor = db.users.find(q).sort(sort_map.get(sort, sort_map["rating"]))
    docs = await cursor.to_list(100)

    # Style filter: keep only those with at least one portfolio item matching style
    if style and docs:
        spec_ids = [str(d["_id"]) for d in docs]
        matching = await db.portfolio.distinct(
            "specialist_id",
            {"specialist_id": {"$in": spec_ids}, "style": style}
        )
        matching_set = set(matching)
        docs = [d for d in docs if str(d["_id"]) in matching_set]

    # ===== HEALTH SCORE (P2 — sugestie main agent) =====
    # Batch-compute per-specialist signals: total/disputed/confirmed/portfolio counts.
    health_map = {}
    if docs:
        spec_ids = [str(d["_id"]) for d in docs]
        # Aggregate requests grouped by specialist_id
        async for row in db.requests.aggregate([
            {"$match": {"specialist_id": {"$in": spec_ids}}},
            {"$group": {
                "_id": "$specialist_id",
                "total":     {"$sum": 1},
                "confirmed": {"$sum": {"$cond": [{"$eq": ["$status", "confirmed"]}, 1, 0]}},
                "disputed":  {"$sum": {"$cond": [{"$eq": ["$disputed", True]}, 1, 0]}},
            }},
        ]):
            health_map[row["_id"]] = row
        # Batch count portfolio items
        portfolio_counts = {}
        async for row in db.portfolio.aggregate([
            {"$match": {"specialist_id": {"$in": spec_ids}}},
            {"$group": {"_id": "$specialist_id", "n": {"$sum": 1}}},
        ]):
            portfolio_counts[row["_id"]] = row["n"]

    def _compute_health(d):
        sid = str(d["_id"])
        stats = health_map.get(sid, {"total": 0, "confirmed": 0, "disputed": 0})
        rating = float(d.get("rating") or 0)
        reviews = int(d.get("reviews_count") or 0)
        verified = bool(d.get("verified"))
        total = stats["total"]
        confirmed = stats["confirmed"]
        disputed = stats["disputed"]

        # Rating component (max 30)
        score = rating * 6  # 5★ → 30

        # Reviews component (max 15) — diminishing returns
        if reviews >= 10: score += 15
        elif reviews >= 5: score += 10
        elif reviews >= 1: score += 5

        # Verified bonus (max 15)
        if verified: score += 15

        # Completion rate (max 25) — confirmed / total
        if total >= 3:
            completion_rate = confirmed / total
            score += completion_rate * 25
        elif total >= 1:
            # No penalty for low volume — neutral grant
            score += 12
        else:
            # Brand-new specialist — neutral
            score += 12

        # Dispute penalty / bonus (max 15)
        if total >= 3:
            dispute_rate = disputed / total
            if dispute_rate == 0: score += 15
            elif dispute_rate < 0.05: score += 10
            elif dispute_rate < 0.10: score += 5
            # else 0
        else:
            score += 8  # neutral for low volume

        score = max(0, min(100, round(score)))
        if score >= 80:
            tier, color, label = "excellent", "emerald", "Excelent"
        elif score >= 50:
            tier, color, label = "good", "amber", "Bun"
        else:
            tier, color, label = "developing", "rose", "În progres"

        return {
            "score": score,
            "tier": tier,
            "color": color,
            "label": label,
            "components": {
                "rating": rating,
                "reviews": reviews,
                "verified": verified,
                "completed_jobs": confirmed,
                "total_jobs": total,
                "disputes": disputed,
            },
            "portfolio_count": portfolio_counts.get(sid, 0) if docs else 0,
        }

    # ===== GBOS P0.3 — Trust rollup (Rebook + Recomandări) batch =====
    trust_map = {}
    if docs:
        async for row in db.reviews.aggregate([
            {"$match": {"specialist_id": {"$in": spec_ids},
                        "direction": {"$ne": "specialist_to_client"},
                        "would_hire_again": {"$in": ["yes", "no", "not_sure"]}}},
            {"$group": {"_id": {"s": "$specialist_id", "a": "$would_hire_again"}, "n": {"$sum": 1}}},
        ]):
            t = trust_map.setdefault(row["_id"]["s"], {"yes": 0, "no": 0, "not_sure": 0, "recommenders": set()})
            t[row["_id"]["a"]] = row["n"]
        async for r in db.reviews.find({"specialist_id": {"$in": spec_ids},
                                        "direction": {"$ne": "specialist_to_client"},
                                        "would_recommend": {"$in": [True, False]}}, {"specialist_id": 1, "client_id": 1, "would_recommend": 1}):
            t = trust_map.setdefault(r["specialist_id"], {"yes": 0, "no": 0, "not_sure": 0, "recommenders": set(), "rec_yes": 0, "rec_no": 0})
            t.setdefault("rec_yes", 0); t.setdefault("rec_no", 0)
            if r.get("would_recommend") is True:
                t["rec_yes"] += 1
                t["recommenders"].add(r.get("client_id"))
            else:
                t["rec_no"] += 1
        async for r in db.recommendations.find({"specialist_id": {"$in": spec_ids}}, {"specialist_id": 1, "owner_id": 1}):
            trust_map.setdefault(r["specialist_id"], {"yes": 0, "no": 0, "not_sure": 0, "recommenders": set(), "rec_yes": 0, "rec_no": 0})["recommenders"].add(r.get("owner_id"))

    # ===== PB-003 — Community Trust Score batch (cache pb_trust_scores) =====
    pb_trust = {}
    if docs:
        async for row in db.pb_trust_scores.find({"specialist_id": {"$in": spec_ids}},
                                                 {"_id": 0, "specialist_id": 1, "score": 1, "recommendations": 1,
                                                  "recommendations_validated": 1, "confirmed_jobs": 1,
                                                  "ambassadors": 1, "community_value": 1}):
            pb_trust[row["specialist_id"]] = row

    def _trust(sid):
        pt = pb_trust.get(sid) or {}
        base = {"trust_score": pt.get("score"),
                "recommendations": pt.get("recommendations", 0),
                "recommendations_validated": pt.get("recommendations_validated", 0),
                "confirmed_jobs": pt.get("confirmed_jobs", 0),
                "ambassadors": pt.get("ambassadors", 0),
                "community_value": pt.get("community_value", 0)}
        t = trust_map.get(sid)
        if not t:
            return {**base, "rebook_pct": None, "rebook_total": 0, "rebook_show": False,
                    "recommend_pct": None, "recommend_total": 0, "recommend_show": False, "recommenders": 0}
        total = t["yes"] + t["no"] + t["not_sure"]
        rec_total = t.get("rec_yes", 0) + t.get("rec_no", 0)
        return {
            **base,
            "rebook_pct": round(t["yes"] * 100 / total) if total else None,
            "rebook_total": total,
            "rebook_show": total >= 5,
            "recommend_pct": round(t.get("rec_yes", 0) * 100 / rec_total) if rec_total else None,
            "recommend_total": rec_total,
            "recommend_show": rec_total >= 5,
            "recommenders": len([x for x in t["recommenders"] if x]),
        }

    return [{
        "id": str(d["_id"]),
        "name": d.get("name"),
        "picture": d.get("picture"),
        "avatar": d.get("avatar"),
        "specialty": d.get("specialty"),
        "service_categories": d.get("service_categories", []),
        "coverage_zones": d.get("coverage_zones", []),
        "rating": d.get("rating"),
        "reviews_count": d.get("reviews_count", 0),
        "tier": d.get("tier"),
        "verified": d.get("verified", False),
        "availability_status": d.get("availability_status"),
        "health": _compute_health(d),
        "trust": _trust(str(d["_id"])),
        "portfolio_count": _compute_health(d)["portfolio_count"],
    } for d in docs]


@router.get("/marketplace/filters")
async def marketplace_filters(category: Optional[str] = None):
    """Returns available zones + styles for filter dropdowns (scoped by category if provided)."""
    spec_query = {"role": "specialist", "deleted": {"$ne": True}}
    if category:
        spec_query["$or"] = [{"specialty": category}, {"service_categories": category}]
    zones = await db.users.distinct("coverage_zones", spec_query)
    zones = sorted([z for z in zones if z])

    portfolio_query = {}
    if category:
        portfolio_query["category"] = category
        # Restrict styles to portfolios of specialists in scope
        spec_ids = await db.users.distinct("_id", spec_query)
        portfolio_query["specialist_id"] = {"$in": [str(s) for s in spec_ids]}
    styles = await db.portfolio.distinct("style", portfolio_query)
    styles = sorted([s for s in styles if s])

    return {"zones": zones, "styles": styles}


