"""Autonomy Orchestrator REST API (admin-only).

  GET  /api/admin/orchestrator/overview          — KPI today + playbooks
  GET  /api/admin/orchestrator/ledger            — recent ledger entries
  POST /api/admin/orchestrator/playbooks/{pid}/toggle
  POST /api/admin/orchestrator/simulate/{kind}   — fire a test signal
  POST /api/admin/orchestrator/retry-tick        — force retry queue processing
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Body, HTTPException

from db import db
from deps import require_role
from orchestrator.engine import emit_signal, is_playbook_enabled, set_playbook_enabled, orchestrator_retry_tick
from orchestrator.playbooks import PLAYBOOKS

logger = logging.getLogger("propmanage.orchestrator_routes")
router = APIRouter(prefix="/api/admin/orchestrator", tags=["admin-orchestrator"])


def _today_start() -> str:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


@router.get("/overview")
async def get_overview(user=Depends(require_role("admin"))):
    today = _today_start()
    today_entries = [d async for d in db.orchestrator_ledger.find({"ts": {"$gte": today}}, {"_id": 0})]
    total_agg = await db.orchestrator_ledger.aggregate([
        {"$group": {"_id": None, "minutes": {"$sum": "$minutes_saved"}, "count": {"$sum": 1}}}
    ]).to_list(1)

    playbooks = []
    for kind, pb in PLAYBOOKS.items():
        last = await db.orchestrator_ledger.find_one(
            {"playbook_id": pb["id"]}, {"_id": 0, "ts": 1, "outcome": 1}, sort=[("ts", -1)]
        )
        runs = await db.orchestrator_ledger.count_documents({"playbook_id": pb["id"]})
        playbooks.append({
            "id": pb["id"],
            "signal_kind": kind,
            "name": pb["name"],
            "description": pb["description"],
            "enabled": await is_playbook_enabled(pb["id"]),
            "last_run_at": (last or {}).get("ts"),
            "last_outcome": (last or {}).get("outcome"),
            "runs_total": runs,
        })

    return {
        "today": {
            "actions": len(today_entries),
            "minutes_saved": sum(e.get("minutes_saved") or 0 for e in today_entries),
            "auto_resolved": sum(1 for e in today_entries if e.get("outcome") == "auto_resolved"),
            "escalated": sum(1 for e in today_entries if e.get("escalated")),
        },
        "total_minutes_saved": (total_agg[0]["minutes"] if total_agg else 0),
        "total_actions": (total_agg[0]["count"] if total_agg else 0),
        "retry_pending": await db.orchestrator_retry_queue.count_documents({"status": "pending"}),
        "retry_blocked_config": await db.orchestrator_retry_queue.count_documents({"status": "blocked_by_config"}),
        "playbooks": playbooks,
    }


@router.get("/ledger")
async def get_ledger(limit: int = 50, user=Depends(require_role("admin"))):
    limit = max(1, min(int(limit), 200))
    items = [d async for d in db.orchestrator_ledger.find({}, {"_id": 0}).sort("ts", -1).limit(limit)]
    return {"items": items}


@router.post("/playbooks/{playbook_id}/toggle")
async def toggle_playbook(playbook_id: str, payload: dict = Body(...), user=Depends(require_role("admin"))):
    valid_ids = {pb["id"] for pb in PLAYBOOKS.values()}
    if playbook_id not in valid_ids:
        raise HTTPException(404, "Playbook inexistent")
    enabled = bool(payload.get("enabled"))
    await set_playbook_enabled(playbook_id, enabled, by=user.get("email") or "")
    return {"id": playbook_id, "enabled": enabled}


@router.post("/simulate/{kind}")
async def simulate_signal(kind: str, user=Depends(require_role("admin"))):
    """Fire a marked TEST signal so the admin can see the full cascade live."""
    if kind == "smoke_fail":
        payload = {
            "test": True,
            "failed": 2,
            "total": 12,
            "base_url": "https://simulated.propmanage.ro",
            "steps": [
                {"name": "login client", "ok": False, "error": "HTTP 500 (simulare)", "status_code": 500},
                {"name": "wallet balance", "ok": False, "error": "timeout după 10s (simulare)", "status_code": None},
            ],
        }
    elif kind == "autonomy_score_drop":
        payload = {"test": True, "drops": {"operational": 8.0}, "prev_general": 88, "new_general": 80, "tier": "autonomous"}
    elif kind == "webhook_fail":
        payload = {
            "test": True,
            "source": "resend_email",
            "to": user.get("email"),
            "subject": "[TEST] Orchestrator Retry Guardian",
            "html": "<p>Acest email a fost re-trimis automat de Webhook Retry Guardian (simulare).</p>",
        }
    elif kind == "category_visibility_refresh":
        payload = {"trigger": f"manual_simulate:{user.get('email')}"}
    elif kind == "dispute_opened":
        payload = {"test": True}
    elif kind == "kyc_prevalidated":
        payload = {"test": True, "user_name": "Specialist Test (simulare)", "recommendation": "approve",
                   "match_score": 94, "flags": ["face_match_good"]}
    elif kind == "marketplace_medic_scan":
        payload = {"test": True}
    elif kind in ("pattern_scan", "finance_reconcile", "roadmap_advise"):
        payload = {"test": True, "trigger": f"manual_simulate:{user.get('email')}"}
    else:
        raise HTTPException(400, "kind trebuie să fie unul dintre: smoke_fail | autonomy_score_drop | webhook_fail | category_visibility_refresh | dispute_opened | kyc_prevalidated | marketplace_medic_scan | pattern_scan | finance_reconcile | roadmap_advise")

    result = await emit_signal(kind, payload)
    return {"simulated": kind, **result}


@router.post("/retry-tick")
async def force_retry_tick(user=Depends(require_role("admin"))):
    return await orchestrator_retry_tick()


@router.post("/retry-queue/resume-blocked")
async def resume_blocked_emails(user=Depends(require_role("admin"))):
    """După repararea configurației (ex. domeniu Resend verificat), repune emailurile
    blocked_by_config în coadă și rulează imediat un tick."""
    from orchestrator.engine import write_ledger
    res = await db.orchestrator_retry_queue.update_many(
        {"status": "blocked_by_config"},
        {"$set": {"status": "pending", "attempts": 0,
                  "next_retry_at": datetime.now(timezone.utc).isoformat()}},
    )
    resumed = res.modified_count
    tick = await orchestrator_retry_tick() if resumed else None
    await write_ledger({
        "signal_kind": "webhook_fail",
        "playbook_id": "webhook_retry_guardian",
        "playbook_name": "Webhook Retry Guardian",
        "steps": [{"action": "resume_blocked_emails", "ok": True,
                   "detail": f"{resumed} emailuri blocate de config repuse în coadă de {user.get('email')}"
                             + (f" — tick imediat: {tick['sent']} trimise, {tick['blocked_config']} re-blocate" if tick else "")}],
        "outcome": "auto_resolved" if (tick and tick.get("sent")) else "monitored",
        "minutes_saved": 5 * resumed,
        "escalated": False,
        "test": False,
    })
    return {"resumed": resumed, "tick": tick}


# ============================================================================
# GUVERNANȚĂ AI (PM-AI-003): Authority Engine + Decision Memory + Self-Healing
# ============================================================================
@router.get("/governance")
async def get_governance(user=Depends(require_role("admin"))):
    from orchestrator.governance import (
        AUTHORITY_LEVELS, get_authority, compute_confidence, governance_snapshot,
    )
    playbooks = []
    for kind, pb in PLAYBOOKS.items():
        level = await get_authority(pb["id"])
        conf = await compute_confidence(pb["id"])
        playbooks.append({
            "id": pb["id"], "signal_kind": kind, "name": pb["name"],
            "authority_level": level,
            "authority": AUTHORITY_LEVELS[level],
            "confidence": conf["score"], "confidence_runs": conf["runs"],
            "enabled": await is_playbook_enabled(pb["id"]),
        })
    return {
        "levels": AUTHORITY_LEVELS,
        "playbooks": playbooks,
        "snapshot": await governance_snapshot(),
    }


@router.post("/playbooks/{playbook_id}/authority")
async def set_playbook_authority(playbook_id: str, payload: dict = Body(...), user=Depends(require_role("admin"))):
    from orchestrator.governance import set_authority
    valid_ids = {pb["id"] for pb in PLAYBOOKS.values()}
    if playbook_id not in valid_ids:
        raise HTTPException(404, "Playbook inexistent")
    level = payload.get("level")
    if not isinstance(level, int) or not 1 <= level <= 5:
        raise HTTPException(400, "level trebuie să fie întreg între 1 și 5")
    new_level = await set_authority(playbook_id, level, by=user.get("email") or "")
    return {"id": playbook_id, "authority_level": new_level}


@router.get("/decisions")
async def get_decisions(limit: int = 50, playbook_id: str = None, user=Depends(require_role("admin"))):
    limit = max(1, min(int(limit), 200))
    q = {"playbook_id": playbook_id} if playbook_id else {}
    items = [d async for d in db.orchestrator_decisions.find(q, {"_id": 0}).sort("ts", -1).limit(limit)]
    return {"items": items, "total": await db.orchestrator_decisions.count_documents(q)}


@router.post("/watchdog-tick")
async def force_watchdog_tick(user=Depends(require_role("admin"))):
    from orchestrator.governance import governance_watchdog_tick
    return await governance_watchdog_tick()


@router.post("/decision-review")
async def force_decision_review(user=Depends(require_role("admin"))):
    from orchestrator.governance import decision_review_cron
    return await decision_review_cron()
