"""Learning Engine GI-4a — Outcome Tracker (arhitectură aprobată & frozen, Board 008/010/011).

Leagă fiecare decizie AI din ai_decision_ledger de rezultatul REAL prin ferestre de atribuire:
  engagement (revenire, 7z) → conversion (cont creat, 7z) → request (cerere, 30z) → revenue (RON, 30z).
Atribuire last-touch (documentat în arhitectură). Scorurile = proiecții; ledger-ul = adevărul.
Rule-based, zero LLM. Intrările fără target → outcome 'untracked'.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.learning")

ENGAGEMENT_WINDOW_DAYS = 7
REVENUE_WINDOW_DAYS = 30
OUTCOME_RANK = {"revenue": 5, "request": 4, "conversion": 3, "engagement": 2, "no_effect": 1}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ledger_entry(entry_type: str, source_agent: str, recommendation: str, reason: str,
                 action: str, approved_by: str, target: dict | None = None,
                 confidence: str = "ai_hypothesis", extra: dict | None = None) -> dict:
    """Constructor unic pentru intrări ledger (Legea Vocabularului — un singur format)."""
    return {
        "ledger_id": uuid.uuid4().hex, "type": entry_type, "source_agent": source_agent,
        "recommendation": recommendation[:300], "reason": (reason or "")[:400],
        "confidence": confidence, "status": "decided", "action": action,
        "approved_by": approved_by, "decided_at": _now(), "created_at": _now(),
        "result": "pending_outcome", "target": target or {}, **(extra or {}),
    }


async def _observe_target(target: dict, decided_at: str) -> dict | None:
    """Cel mai puternic outcome observat pentru target după decizie (last-touch)."""
    user_id = target.get("user_id")
    visitor_id = target.get("visitor_id")
    best = None

    def better(kind, data=None):
        nonlocal best
        if best is None or OUTCOME_RANK.get(kind, 0) > OUTCOME_RANK.get(best["kind"], 0):
            best = {"kind": kind, **(data or {})}

    if user_id:
        req_q = {"client_id": user_id, "created_at": {"$gt": decided_at}}
        revenue = 0.0
        req_count = 0
        async for r in db.requests.find(req_q, {"status": 1, "escrow_amount": 1}):
            req_count += 1
            if r.get("status") == "confirmed":
                revenue += float(r.get("escrow_amount") or 0)
        if revenue > 0:
            better("revenue", {"revenue_ron": round(revenue, 2), "requests": req_count})
        elif req_count:
            better("request", {"requests": req_count})

    if best is None and visitor_id:
        sessions = await db.analytics_sessions.find(
            {"visitor_id": visitor_id, "started_at": {"$gt": decided_at}},
            {"funnel_account_created": 1}).to_list(200)
        if any(s.get("funnel_account_created") for s in sessions):
            better("conversion", {"sessions_after": len(sessions)})
        elif sessions:
            better("engagement", {"sessions_after": len(sessions)})

    return best


async def run_outcome_scan(trigger: str = "manual") -> dict:
    """Procesează deciziile fără outcome final. Idempotent (consumator independent — Legea Cuplării)."""
    now = datetime.now(timezone.utc)
    processed = finalized = 0
    kinds: dict = {}
    q = {"status": "decided", "$or": [{"outcome": {"$exists": False}}, {"outcome.final": {"$ne": True}}]}
    async for entry in db.ai_decision_ledger.find(q).limit(500):
        processed += 1
        decided_at = entry.get("decided_at") or entry.get("created_at") or _now()
        target = entry.get("target") or {}
        try:
            decided_dt = datetime.fromisoformat(decided_at.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            decided_dt = now
        age_days = (now - decided_dt).days

        if not target.get("user_id") and not target.get("visitor_id"):
            outcome = {"kind": "untracked", "final": True, "observed_at": _now()}
        elif entry.get("action") in ("ignored", "dismissed"):
            outcome = {"kind": "no_effect", "final": True, "observed_at": _now(),
                       "note": "recomandare respinsă de operator/client"}
        elif entry.get("request_id"):
            # oportunitate acceptată → urmărește direct cererea legată (dovada cea mai puternică)
            from bson import ObjectId
            try:
                req = await db.requests.find_one({"_id": ObjectId(entry["request_id"])},
                                                 {"status": 1, "escrow_amount": 1})
            except Exception:  # noqa: BLE001
                req = None
            if req and req.get("status") == "confirmed":
                outcome = {"kind": "revenue", "revenue_ron": round(float(req.get("escrow_amount") or 0), 2),
                           "final": True, "observed_at": _now()}
            elif age_days > REVENUE_WINDOW_DAYS:
                outcome = {"kind": "request", "final": True, "observed_at": _now(),
                           "note": "cerere creată, neconfirmată în fereastră"}
            else:
                outcome = {"kind": "request", "final": False, "observed_at": _now()}
        else:
            observed = await _observe_target(target, decided_at)
            if observed:
                final = observed["kind"] == "revenue" or age_days > REVENUE_WINDOW_DAYS
                outcome = {**observed, "final": final, "observed_at": _now()}
            elif age_days > REVENUE_WINDOW_DAYS:
                outcome = {"kind": "no_effect", "final": True, "observed_at": _now()}
            else:
                continue  # încă în fereastră, fără semnal — rămâne pending

        prev_kind = (entry.get("outcome") or {}).get("kind")
        await db.ai_decision_ledger.update_one(
            {"ledger_id": entry["ledger_id"]},
            {"$set": {"outcome": outcome, "result": outcome["kind"]}})
        if outcome.get("final"):
            finalized += 1
        kinds[outcome["kind"]] = kinds.get(outcome["kind"], 0) + 1
        if prev_kind != outcome["kind"]:
            await db.ai_outcomes.insert_one({
                "ledger_id": entry["ledger_id"], "type": entry.get("type"),
                "kind": outcome["kind"], "revenue_ron": outcome.get("revenue_ron", 0),
                "recorded_at": _now(), "trigger": trigger,
            })
            try:
                from event_bus import emit
                await emit("learning.outcome_recorded", payload={
                    "ledger_id": entry["ledger_id"], "type": entry.get("type"),
                    "kind": outcome["kind"], "revenue_ron": outcome.get("revenue_ron", 0)})
            except Exception:  # noqa: BLE001
                pass

    summary = {"trigger": trigger, "processed": processed, "finalized": finalized,
               "outcomes": kinds, "generated_at": _now()}
    logger.info(f"[learning] outcome scan ({trigger}): {summary}")
    return summary


async def learning_stats(days: int = 30) -> dict:
    """KPI-urile Learning Engine (consumate de UI + Command Center)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    total = await db.ai_decision_ledger.count_documents({})
    decided = await db.ai_decision_ledger.count_documents({"status": "decided"})
    by_kind: dict = {}
    revenue = 0.0
    async for d in db.ai_decision_ledger.aggregate([
        {"$match": {"outcome.kind": {"$exists": True}}},
        {"$group": {"_id": "$outcome.kind", "n": {"$sum": 1},
                    "rev": {"$sum": {"$ifNull": ["$outcome.revenue_ron", 0]}}}},
    ]):
        by_kind[d["_id"]] = d["n"]
        revenue += d.get("rev") or 0
    revenue_30d = 0.0
    async for d in db.ai_outcomes.aggregate([
        {"$match": {"kind": "revenue", "recorded_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "rev": {"$sum": "$revenue_ron"}}},
    ]):
        revenue_30d = round(d.get("rev") or 0, 2)
    positive = sum(v for k, v in by_kind.items() if k in ("engagement", "conversion", "request", "revenue"))
    tracked = sum(v for k, v in by_kind.items() if k != "untracked")
    by_type: list = []
    async for d in db.ai_decision_ledger.aggregate([
        {"$group": {"_id": "$type", "decisions": {"$sum": 1},
                    "with_outcome": {"$sum": {"$cond": [{"$in": ["$outcome.kind", ["engagement", "conversion", "request", "revenue"]]}, 1, 0]}},
                    "revenue": {"$sum": {"$ifNull": ["$outcome.revenue_ron", 0]}}}},
        {"$sort": {"decisions": -1}},
    ]):
        by_type.append({"type": d["_id"], "decisions": d["decisions"],
                        "with_outcome": d["with_outcome"], "revenue_ron": round(d["revenue"] or 0, 2)})
    return {
        "total_decisions": total, "decided": decided,
        "outcomes_by_kind": by_kind,
        "outcome_rate_pct": round(positive / tracked * 100, 1) if tracked else 0.0,
        "revenue_attributed_ron": round(revenue, 2),
        "revenue_attributed_30d_ron": revenue_30d,
        "by_type": by_type,
        "attribution_model": "last_touch",  # documentat în arhitectura GI-4 (frozen)
    }
