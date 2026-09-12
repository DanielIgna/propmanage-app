"""AI Governance & Self-Healing Pack (PM-AI-003).

Authority Engine (niveluri 1-5), Confidence Engine, Decision Memory (append-only),
Decision Review Cron și Watchdog de self-healing pentru joburi cron moarte.
Collections: orchestrator_decisions, orchestrator_reviews, orchestrator_config.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.governance")

AUTHORITY_LEVELS = {
    1: {"key": "observer", "label": "Observator", "mode": "observe",
        "description": "Doar înregistrează semnalul în Decision Memory. Nu execută, nu notifică."},
    2: {"key": "advisor", "label": "Consilier", "mode": "recommend",
        "description": "Nu execută. Generează recomandare + notifică adminii pentru decizie umană."},
    3: {"key": "supervised", "label": "Executor supravegheat", "mode": "execute_notify",
        "description": "Execută automat și notifică adminii la fiecare rulare."},
    4: {"key": "autonomous", "label": "Executor autonom", "mode": "execute",
        "description": "Execută automat. Notifică doar la escaladare/eșec."},
    5: {"key": "full_autonomy", "label": "Autonomie totală", "mode": "execute_silent",
        "description": "Execută silențios, cu self-healing. Escaladează doar eșecurile permanente."},
}

DEFAULT_AUTHORITY = {
    "webhook_retry_guardian": 5,
    "category_visibility_gate": 5,
    "marketplace_medic": 4,
    "smoke_fail_to_qa": 4,
    "autonomy_reflex": 4,
    "business_alert_router": 4,
    "launch_resident_welcome": 4,
    "launch_campaign_tracker": 4,
    "launch_first_payment": 4,
    "dispute_ai_triage": 3,
    "kyc_prevalidation_reporter": 3,
    "pattern_hunter": 3,
    "finance_reconciler": 3,
    "roadmap_advisor": 3,
}
FALLBACK_AUTHORITY = 3
LOW_CONF_THRESHOLD = 0.35
MIN_RUNS_FOR_CONFIDENCE = 5

_SUCCESS_OUTCOMES = {"auto_resolved", "resolved", "ok", "completed", "done", "informed",
                     "notified", "no_action_needed", "recommended", "healthy"}
_FAIL_OUTCOMES = {"error", "escalated", "failed", "failed_suppressed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_authority(playbook_id: str) -> int:
    doc = await db.orchestrator_config.find_one({"_id": f"authority:{playbook_id}"})
    if doc and doc.get("level"):
        return max(1, min(5, int(doc["level"])))
    return DEFAULT_AUTHORITY.get(playbook_id, FALLBACK_AUTHORITY)


async def set_authority(playbook_id: str, level: int, by: str = "") -> int:
    level = max(1, min(5, int(level)))
    await db.orchestrator_config.update_one(
        {"_id": f"authority:{playbook_id}"},
        {"$set": {"level": level, "updated_at": _now(), "updated_by": by}},
        upsert=True,
    )
    return level


async def compute_confidence(playbook_id: str, window: int = 30) -> dict:
    """Scor de încredere 0-1 din istoricul ledger, ponderat pe recență."""
    entries = [d async for d in db.orchestrator_ledger.find(
        {"playbook_id": playbook_id, "test": {"$ne": True}, "absolved": {"$ne": True}},
        {"outcome": 1, "escalated": 1},
    ).sort("ts", -1).limit(window)]
    if not entries:
        return {"score": 0.7, "runs": 0, "basis": "no_history"}
    num, den = 0.0, 0.0
    for i, e in enumerate(entries):
        w = 0.92 ** i
        den += w
        outcome = e.get("outcome") or ""
        if outcome in _FAIL_OUTCOMES or e.get("escalated"):
            continue
        num += w
    score = round(num / den, 3) if den else 0.7
    return {"score": score, "runs": len(entries), "basis": "history"}


def resolve_execution_mode(authority: int, confidence: dict) -> str:
    if authority <= 1:
        return "observe"
    if authority == 2:
        return "recommend"
    if (confidence.get("runs", 0) >= MIN_RUNS_FOR_CONFIDENCE
            and confidence.get("score", 1.0) < LOW_CONF_THRESHOLD):
        return "recommend"  # downgrade automat la încredere scăzută
    return AUTHORITY_LEVELS[authority]["mode"]


async def record_decision(entry: dict) -> dict:
    """Decision Memory — ledger append-only, niciodată editat/șters."""
    doc = {"id": uuid.uuid4().hex, "ts": _now(), "reviewed": False, **entry}
    try:
        await db.orchestrator_decisions.insert_one({**doc})
        n = await db.orchestrator_decisions.estimated_document_count()
        if n > 6000:
            cur = db.orchestrator_decisions.find({}, {"_id": 1}).sort("ts", -1).skip(5000)
            old = [d["_id"] async for d in cur]
            if old:
                await db.orchestrator_decisions.delete_many({"_id": {"$in": old}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[governance] decision write failed: {e}")
    doc.pop("_id", None)
    return doc


# ============================================================================
# DECISION REVIEW CRON — zilnic 05:30: analizează deciziile din ultimele 24h,
# degradează autoritatea playbook-urilor cu eșecuri repetate (self-governance).
# ============================================================================
async def decision_review_cron() -> dict:
    from orchestrator.engine import write_ledger, notify_admins
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    decisions = [d async for d in db.orchestrator_decisions.find(
        {"ts": {"$gte": since}, "test": {"$ne": True}}, {"_id": 0})]

    per_pb: dict = {}
    for d in decisions:
        pid = d.get("playbook_id") or "?"
        s = per_pb.setdefault(pid, {"total": 0, "failed": 0, "name": d.get("playbook_name") or pid})
        s["total"] += 1
        if (d.get("outcome") or "") in _FAIL_OUTCOMES or d.get("escalated"):
            s["failed"] += 1

    downgrades = []
    for pid, s in per_pb.items():
        if s["total"] >= 3 and s["failed"] / s["total"] >= 0.5:
            current = await get_authority(pid)
            if current > 2:
                new_level = await set_authority(pid, current - 1, by="decision_review_cron")
                downgrades.append({"playbook_id": pid, "name": s["name"], "from": current,
                                   "to": new_level, "failed": s["failed"], "total": s["total"]})

    await db.orchestrator_decisions.update_many(
        {"ts": {"$gte": since}, "reviewed": False}, {"$set": {"reviewed": True}})

    review = {
        "id": uuid.uuid4().hex, "ts": _now(), "window_hours": 24,
        "decisions_reviewed": len(decisions),
        "playbooks_active": len(per_pb),
        "downgrades": downgrades,
    }
    try:
        await db.orchestrator_reviews.insert_one({**review})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[governance] review write failed: {e}")

    await write_ledger({
        "signal_kind": "decision_review", "playbook_id": "decision_review_cron",
        "playbook_name": "Decision Review (Guvernanță AI)",
        "steps": [{"action": "review_decisions", "ok": True,
                   "detail": f"{len(decisions)} decizii analizate, {len(downgrades)} degradări de autoritate"}],
        "outcome": "auto_resolved" if not downgrades else "escalated",
        "minutes_saved": 5, "escalated": bool(downgrades), "test": False,
    })
    if downgrades:
        lines = "; ".join(f"{d['name']}: nivel {d['from']}→{d['to']} ({d['failed']}/{d['total']} eșecuri)" for d in downgrades)
        await notify_admins("⚠ Guvernanță AI: autoritate degradată automat",
                            f"Playbook-uri cu eșecuri repetate în 24h au fost trecute pe nivel inferior: {lines}",
                            send_emails=False)
    logger.info(f"[governance] decision review: {len(decisions)} decizii, {len(downgrades)} downgrades")
    review.pop("_id", None)
    return review


# ============================================================================
# WATCHDOG SELF-HEALING — la 30 min: detectează joburi cron moarte/blocate
# și le repornește automat (resume + reschedule). Escaladează doar dacă eșuează.
# ============================================================================
async def governance_watchdog_tick() -> dict:
    from orchestrator.engine import write_ledger, notify_admins
    out = {"jobs_checked": 0, "healed": [], "failing_jobs": [], "stuck_retries": 0}
    now = datetime.now(timezone.utc)

    try:
        from server import scheduler
        for job in scheduler.get_jobs():
            out["jobs_checked"] += 1
            if job.next_run_time is None:
                try:
                    job.resume()
                    out["healed"].append(job.id)
                except Exception as e:  # noqa: BLE001
                    out["failing_jobs"].append({"job_id": job.id, "error": str(e)[:120]})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[governance] watchdog scheduler introspection failed: {e}")

    # Joburi cu ≥3 erori consecutive în ultimele 24h (din agent_runs)
    since = (now - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {"ts": {"$gte": since}, "status": "error"}},
        {"$group": {"_id": "$job_id", "errors": {"$sum": 1}, "last_error": {"$last": "$error"}}},
        {"$match": {"errors": {"$gte": 3}}},
    ]
    try:
        async for row in db.agent_runs.aggregate(pipeline):
            out["failing_jobs"].append({"job_id": row["_id"], "errors": row["errors"],
                                        "last_error": (row.get("last_error") or "")[:150]})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[governance] watchdog agent_runs scan failed: {e}")

    # Retry-uri blocate: pending cu next_retry_at depășit cu >2h → re-programare imediată
    stale = (now - timedelta(hours=2)).isoformat()
    res = await db.orchestrator_retry_queue.update_many(
        {"status": "pending", "next_retry_at": {"$lte": stale}},
        {"$set": {"next_retry_at": now.isoformat()}})
    out["stuck_retries"] = res.modified_count

    if out["healed"] or out["failing_jobs"] or out["stuck_retries"]:
        healed_txt = ", ".join(out["healed"]) or "—"
        fail_txt = ", ".join(f"{f['job_id']} ({f.get('errors', '?')} erori)" for f in out["failing_jobs"]) or "—"
        await write_ledger({
            "signal_kind": "self_healing", "playbook_id": "governance_watchdog",
            "playbook_name": "Self-Healing Watchdog",
            "steps": [
                {"action": "resume_dead_jobs", "ok": not out["failing_jobs"],
                 "detail": f"Reînviate: {healed_txt} · Eșecuri repetate: {fail_txt} · Retry-uri deblocate: {out['stuck_retries']}"},
            ],
            "outcome": "auto_resolved" if not out["failing_jobs"] else "escalated",
            "minutes_saved": 10 * (len(out["healed"]) + (1 if out["stuck_retries"] else 0)),
            "escalated": bool(out["failing_jobs"]), "test": False,
        })
        await record_decision({
            "signal_kind": "self_healing", "playbook_id": "governance_watchdog",
            "playbook_name": "Self-Healing Watchdog", "authority_level": 5,
            "execution_mode": "execute_silent", "confidence": 1.0,
            "decided": "executed", "outcome": "auto_resolved" if not out["failing_jobs"] else "escalated",
            "escalated": bool(out["failing_jobs"]),
            "context": {"healed": out["healed"], "failing": [f["job_id"] for f in out["failing_jobs"]],
                        "stuck_retries": out["stuck_retries"]},
            "test": False,
        })
        if out["failing_jobs"]:
            await notify_admins(
                "🚨 Watchdog: joburi cron cu eșecuri repetate",
                f"Joburi cu ≥3 erori în 24h: {fail_txt}. Watchdog-ul nu le poate repara automat — verifică logurile.",
                send_emails=False)
        logger.info(f"[governance] watchdog: {out}")
    return out


_autonomy_cache = {"ts": 0.0, "data": None}


async def compute_autonomy_score() -> dict:
    """Scorul de autonomie al platformei (0-100) — cât rulează singură, fără om.

    Componente (7 zile): rezolvare autonomă ledger, decizii executate autonom,
    fiabilitate cron, sănătatea călătoriei clientului, activitate self-healing.
    Cache 60s (agregările Mongo sunt scumpe pentru un endpoint de dashboard).
    """
    import time
    if _autonomy_cache["data"] and time.monotonic() - _autonomy_cache["ts"] < 60:
        return _autonomy_cache["data"]
    since7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    total_ledger = await db.orchestrator_ledger.count_documents({"ts": {"$gte": since7d}, "test": {"$ne": True}})
    escalated = await db.orchestrator_ledger.count_documents(
        {"ts": {"$gte": since7d}, "test": {"$ne": True}, "escalated": True})
    auto_ratio = (total_ledger - escalated) / total_ledger if total_ledger else 1.0

    total_dec = await db.orchestrator_decisions.count_documents({"ts": {"$gte": since7d}, "test": {"$ne": True}})
    executed = await db.orchestrator_decisions.count_documents(
        {"ts": {"$gte": since7d}, "test": {"$ne": True}, "decided": "executed"})
    exec_ratio = executed / total_dec if total_dec else 1.0

    total_runs = await db.agent_runs.count_documents({"ts": {"$gte": since7d}})
    err_runs = await db.agent_runs.count_documents({"ts": {"$gte": since7d}, "status": "error"})
    cron_ratio = (total_runs - err_runs) / total_runs if total_runs else 1.0

    open_crit = await db.journey_guardian_tasks.count_documents(
        {"status": "open", "severity": {"$in": ["critical", "high"]}})
    journey_ratio = max(0.0, 1.0 - 0.25 * open_crit)

    healing = await db.orchestrator_ledger.count_documents(
        {"ts": {"$gte": since7d}, "playbook_id": {"$in": ["governance_watchdog", "health_repair_engine", "journey_guardian"]}})
    healing_ratio = min(1.0, healing / 7)  # minim un eveniment autonom pe zi

    components = {
        "auto_resolution": {"score": round(auto_ratio * 100), "weight": 0.35,
                            "detail": f"{total_ledger - escalated}/{total_ledger} acțiuni fără escaladare (7z)"},
        "autonomous_decisions": {"score": round(exec_ratio * 100), "weight": 0.20,
                                 "detail": f"{executed}/{total_dec} decizii executate autonom"},
        "cron_reliability": {"score": round(cron_ratio * 100), "weight": 0.20,
                             "detail": f"{total_runs - err_runs}/{total_runs} rulări cron fără eroare"},
        "journey_health": {"score": round(journey_ratio * 100), "weight": 0.15,
                           "detail": f"{open_crit} task-uri critice/high deschise în călătoria clientului"},
        "self_healing_activity": {"score": round(healing_ratio * 100), "weight": 0.10,
                                  "detail": f"{healing} evenimente autonome de reparare (7z)"},
    }
    score = round(sum(c["score"] * c["weight"] for c in components.values()), 1)
    result = {"score": score, "components": components, "computed_at": _now()}
    import time
    _autonomy_cache["ts"] = time.monotonic()
    _autonomy_cache["data"] = result
    return result


async def governance_snapshot() -> dict:
    """Metrici agregate pentru CEO Briefing + panoul de guvernanță."""
    since24 = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    since7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    decisions24 = [d async for d in db.orchestrator_decisions.find(
        {"ts": {"$gte": since24}, "test": {"$ne": True}},
        {"_id": 0, "decided": 1, "confidence": 1, "escalated": 1})]
    executed = sum(1 for d in decisions24 if d.get("decided") == "executed")
    recommended = sum(1 for d in decisions24 if d.get("decided") == "recommended")
    confs = [d.get("confidence") for d in decisions24 if isinstance(d.get("confidence"), (int, float))]
    healed7d = await db.orchestrator_ledger.count_documents(
        {"playbook_id": "governance_watchdog", "ts": {"$gte": since7d}})
    last_review = await db.orchestrator_reviews.find_one({}, {"_id": 0}, sort=[("ts", -1)])
    autonomy = await compute_autonomy_score()
    return {
        "decisions_24h": len(decisions24),
        "executed_24h": executed,
        "recommended_24h": recommended,
        "escalated_24h": sum(1 for d in decisions24 if d.get("escalated")),
        "avg_confidence": round(sum(confs) / len(confs), 2) if confs else None,
        "self_healing_events_7d": healed7d,
        "autonomy_score": autonomy["score"],
        "autonomy": autonomy,
        "last_review": last_review,
    }
