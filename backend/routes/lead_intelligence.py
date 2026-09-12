"""Intent & Lead Intelligence API — Board Decision GI-2."""
from fastapi import APIRouter, Depends, Query

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/lead-intel", tags=["lead-intelligence"])

TIER_ORDER = ["client", "hot", "qualified", "prospect", "visitor"]


@router.get("/stats")
async def lead_stats(user: dict = Depends(require_role("admin"))):
    meta = await db.lead_scores_meta.find_one({"_id": "latest_scan"}, {"_id": 0}) or {}
    tiers = {t: 0 for t in TIER_ORDER}
    total = avg = 0
    async for d in db.lead_scores.aggregate([
        {"$group": {"_id": "$tier", "n": {"$sum": 1}, "avg": {"$avg": "$score"}}},
    ]):
        tiers[d["_id"]] = d["n"]
        total += d["n"]
        avg += (d.get("avg") or 0) * d["n"]
    signal_counts: dict = {}
    async for d in db.lead_scores.aggregate([
        {"$unwind": "$signals"},
        {"$group": {"_id": "$signals.label", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 8},
    ]):
        signal_counts[d["_id"]] = d["n"]
    return {
        "tiers": tiers, "total": total,
        "avg_score": round(avg / total, 1) if total else 0,
        "top_signals": [{"label": k, "count": v} for k, v in signal_counts.items()],
        "last_scan": meta,
        # Board 006: modelul de scoring v1 e ipoteză AI până la calibrarea Learning Engine (GI-4)
        "model_validation": "ai_hypothesis",
    }


@router.get("/leads")
async def list_leads(tier: str = Query("", pattern="^(|client|hot|qualified|prospect|visitor)$"),
                     limit: int = Query(50, ge=1, le=200),
                     user: dict = Depends(require_role("admin"))):
    q = {"tier": tier} if tier else {"tier": {"$ne": "visitor"}}
    docs = await db.lead_scores.find(q, {"_id": 0}).sort("score", -1).to_list(limit)
    return {"items": docs, "count": len(docs)}


@router.post("/run")
async def run_scan(user: dict = Depends(require_role("admin"))):
    from lead_intelligence import run_lead_scan
    return await run_lead_scan(trigger="manual")
