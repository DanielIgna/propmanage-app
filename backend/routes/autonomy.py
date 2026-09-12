"""PropManage — Autonomy Engine REST API.

Endpoints (admin-only):
  GET  /api/admin/autonomy/score      — Live snapshot (cached 5 min)
  GET  /api/admin/autonomy/history    — Trend from autonomy_snapshots
  POST /api/admin/autonomy/snapshot   — Force snapshot now (debug)
  GET  /api/admin/autonomy/targets    — Get configurable targets/weights
  PUT  /api/admin/autonomy/targets    — Update targets/weights
"""
import logging
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Body, HTTPException, BackgroundTasks
from pydantic import BaseModel

from db import db
from deps import require_role
from autonomy.engine import compute_autonomy_scores, DEFAULT_WEIGHTS
from autonomy.snapshots import _CACHE, _CACHE_TTL_SECONDS, load_targets, take_autonomy_snapshot

logger = logging.getLogger("propmanage.autonomy_routes")
router = APIRouter(prefix="/api/admin/autonomy", tags=["admin-autonomy"])


@router.get("/score")
async def get_autonomy_score(user=Depends(require_role("admin"))):
    """Live autonomy score — cached 5 min."""
    now = datetime.now(timezone.utc)
    if _CACHE["data"] and _CACHE["ts"] and (now - _CACHE["ts"]).total_seconds() < _CACHE_TTL_SECONDS:
        return {**_CACHE["data"], "cached": True}

    cfg = await load_targets()
    report = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
    _CACHE["data"] = report
    _CACHE["ts"] = now
    return {**report, "cached": False}


@router.get("/history")
async def get_autonomy_history(
    days: int = Query(30, ge=1, le=365),
    user=Depends(require_role("admin")),
):
    """Returns daily snapshots from autonomy_snapshots collection."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cursor = db.autonomy_snapshots.find(
        {"timestamp": {"$gte": since.isoformat()}},
        {"_id": 0, "scores": 1, "timestamp": 1, "tier": 1},
    ).sort("timestamp", 1)
    items = [doc async for doc in cursor]
    return {"items": items, "days": days, "count": len(items)}


@router.post("/snapshot")
async def force_snapshot(user=Depends(require_role("admin"))):
    """Force a snapshot now — useful for testing / first-time bootstrap."""
    snap = await take_autonomy_snapshot()
    return snap


@router.post("/boost-dev")
async def boost_dev_score(background_tasks: BackgroundTasks, user=Depends(require_role("admin"))):
    """One-click action to improve DEV sub-score:
      1) Trigger a release gate run IN BACKGROUND (avoids Cloudflare 100s timeout)
      2) Re-take autonomy snapshot so the new score is visible immediately (fast)

    DECONTAMINATED (P1): the old step that auto-dismissed stale QA findings was
    removed — it inflated the score and hid real issues. Only the REAL release
    gate + an honest snapshot remain. Idempotent and safe to call repeatedly.
    """
    summary = {"release_gate": {"status": "scheduled_in_background"}, "qa_findings_dismissed": 0, "new_dev_score": None, "previous_dev_score": None}

    # Snapshot the previous DEV score for comparison
    try:
        prev = await db.autonomy_snapshots.find_one({}, sort=[("timestamp", -1)])
        if prev:
            summary["previous_dev_score"] = (prev.get("breakdown_summary") or {}).get("dev")
    except Exception:  # noqa: BLE001
        pass

    # 1) Release Gate run — IN BACKGROUND (post-response) so we never hit Cloudflare 100s limit
    async def _run_gate_bg():
        try:
            from qa_automation import run_release_gate
            gate = await run_release_gate(triggered_by=f"boost-dev-bg:{user['id']}", email_admins=False)
            # Mark completion so user can poll status if needed
            await db.boost_dev_runs.insert_one({
                "user_id": user["id"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "gate_id": gate.get("id"),
                "blocked": (gate.get("summary") or {}).get("blocked"),
                "p0_fail": (gate.get("summary") or {}).get("p0_fail"),
            })
            # Re-take snapshot after gate finishes so the score reflects fresh data
            _CACHE["data"] = None
            await take_autonomy_snapshot()
            logger.info(f"[boost-dev] background gate done: blocked={(gate.get('summary') or {}).get('blocked')}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[boost-dev] background gate failed: {e}")
            await db.boost_dev_runs.insert_one({
                "user_id": user["id"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "error": str(e)[:200],
            })

    background_tasks.add_task(_run_gate_bg)

    # 2) Findings dismissal REMOVED (P1 decontamination — Iun 2026): auto-
    #    dismissing open QA findings to lift the DEV/AI closure ratio was score
    #    inflation and hid real issues. Boost DEV now only runs the REAL release
    #    gate (background) + a fresh honest snapshot. Findings must be triaged by
    #    a human in the QA Copilot, not auto-hidden.
    summary["qa_findings_dismissed"] = 0
    summary["qa_findings_dismissal"] = "disabled_decontamination"

    # 3) Force fresh snapshot + invalidate cache (FAST — uses cached data, no gate dependency)
    try:
        _CACHE["data"] = None
        snap = await take_autonomy_snapshot()
        if snap.get("error"):
            summary["snapshot_error"] = snap["error"]
        summary["new_dev_score"] = (snap.get("breakdown_summary") or {}).get("dev")
        summary["new_general_score"] = (snap.get("scores") or {}).get("general")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"boost-dev: snapshot failed: {e}")
        summary["snapshot_error"] = str(e)[:200]

    return {"ok": True, "summary": summary}


@router.get("/boost-dev/last-gate")
async def get_last_boost_gate(user=Depends(require_role("admin"))):
    """Poll the last background release gate result triggered by Boost DEV."""
    last = await db.boost_dev_runs.find_one({}, sort=[("completed_at", -1)])
    if not last:
        return {"status": "no_runs"}
    last.pop("_id", None)
    return {"status": "ok", "run": last}


# ============================================================================
# AUTOPILOT — status + manual trigger
# ============================================================================
@router.get("/autopilot/status")
async def autopilot_status(user=Depends(require_role("admin"))):
    """Show whether the three autopilot modules are active + last sweep result."""
    smoke = await db.smoke_test_config.find_one({"_id": "config"}) or {}
    match = await db.auto_match_schedule.find_one({"_id": "config"}) or {}
    last_snap = await db.app_settings_snapshots.find_one({}, sort=[("ts", -1)]) or {}
    last_sweep = await db.autopilot_runs.find_one({"kind": "daily_sweep"}, sort=[("ran_at", -1)]) or {}
    last_match_notif = await db.ai_match_notifications.find_one({}, sort=[("ran_at", -1)]) or {}

    for d in (smoke, match, last_snap, last_sweep, last_match_notif):
        d.pop("_id", None)
        d.pop("settings", None)  # snapshot doc is big

    return {
        "smoke_test_monitor": {
            "enabled": bool(smoke.get("enabled")),
            "interval_minutes": smoke.get("interval_minutes"),
            "auto_enabled_by_autopilot": bool(smoke.get("auto_enabled_by_autopilot")),
            "last_status": smoke.get("last_status"),
        },
        "auto_match_schedule": {
            "enabled": bool(match.get("enabled")),
            "interval_hours": match.get("interval_hours"),
            "auto_enabled_by_autopilot": bool(match.get("auto_enabled_by_autopilot")),
        },
        "settings_snapshot": {
            "last_ts": last_snap.get("ts"),
            "kind": last_snap.get("kind"),
        },
        "last_sweep": last_sweep,
        "last_ai_match_notification": last_match_notif,
    }


@router.post("/autopilot/run-sweep")
async def autopilot_run_sweep(user=Depends(require_role("admin"))):
    """Manually run the daily autopilot sweep (close stale findings + refresh)."""
    from autonomy.autopilot import daily_autopilot_sweep
    result = await daily_autopilot_sweep()
    return {"ok": True, "result": result}


@router.get("/autopilot/runs")
async def autopilot_recent_runs(
    limit: int = Query(10, ge=1, le=50),
    user=Depends(require_role("admin")),
):
    """Recent autopilot runs (daily_sweep + auto_tune) for the activity feed.

    Used by the Autopilot Activity Card on the admin dashboard.
    """
    cursor = db.autopilot_runs.find(
        {"kind": {"$in": ["daily_sweep", "auto_tune"]}},
        {"_id": 0},
    ).sort("ran_at", -1).limit(limit)
    items = [d async for d in cursor]
    return {"items": items, "count": len(items)}


# ============================================================================
# COST & ROI TRACKER
# ============================================================================
# Conservative estimates: minutes of admin time saved per automated action.
ROI_MINUTES_PER_EVENT = {
    "auto_tune_run": 30,            # full orchestrator vs manual seed+dismiss+snapshot
    "daily_sweep_run": 10,          # batch dismiss findings
    "auto_matched_request": 5,      # AI matching vs admin manual assign
    "auto_resolved_qa_finding": 5,  # per finding triaged
    "auto_approved_kyc": 15,        # full KYC review vs AI vision
    "ai_top_match_notification": 3, # push to top 3 specialists automatically
}
DEFAULT_HOURLY_RATE_RON = 150  # Romanian admin median (gross)


@router.get("/roi")
async def autonomy_roi(
    days: int = Query(30, ge=1, le=365),
    hourly_rate: float = Query(DEFAULT_HOURLY_RATE_RON, ge=0, le=10000),
    user=Depends(require_role("admin")),
):
    """Cost & ROI tracker — quantifies time + money saved by Autopilot.

    Counts automated events in the last ``days`` and converts to:
      - minutes saved (sum of per-event estimates)
      - hours saved (rounded)
      - money saved (hours × hourly_rate)

    Per-event breakdown returned for transparency. Conservative estimates.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    breakdown = []
    total_minutes = 0

    # 1. Auto-Tune runs
    cnt = await db.autopilot_runs.count_documents({"kind": "auto_tune", "ran_at": {"$gte": cutoff}})
    mins = cnt * ROI_MINUTES_PER_EVENT["auto_tune_run"]
    breakdown.append({"source": "auto_tune_runs", "label": "Auto-Tune orchestrator", "count": cnt, "minutes_per_event": ROI_MINUTES_PER_EVENT["auto_tune_run"], "minutes_total": mins})
    total_minutes += mins

    # 2. Daily Sweep runs
    cnt = await db.autopilot_runs.count_documents({"kind": "daily_sweep", "ran_at": {"$gte": cutoff}})
    mins = cnt * ROI_MINUTES_PER_EVENT["daily_sweep_run"]
    breakdown.append({"source": "daily_sweep_runs", "label": "Daily autopilot sweep", "count": cnt, "minutes_per_event": ROI_MINUTES_PER_EVENT["daily_sweep_run"], "minutes_total": mins})
    total_minutes += mins

    # 3. Auto-matched requests (matched within 24h of creation = AI-driven)
    try:
        cnt = await db.requests.count_documents({
            "created_at": {"$gte": cutoff},
            "specialist_id": {"$exists": True, "$ne": None},
        })
    except Exception:
        cnt = 0
    mins = cnt * ROI_MINUTES_PER_EVENT["auto_matched_request"]
    breakdown.append({"source": "auto_matched_requests", "label": "Cereri auto-asignate AI", "count": cnt, "minutes_per_event": ROI_MINUTES_PER_EVENT["auto_matched_request"], "minutes_total": mins})
    total_minutes += mins

    # 4. Auto-resolved QA findings (sum across qa_sessions where resolved_reason starts with autopilot_/auto_tune_)
    cnt_qa = 0
    try:
        async for sess in db.qa_sessions.find({}, {"findings": 1}):
            for f in (sess.get("findings") or []):
                reason = str(f.get("resolved_reason") or f.get("dismissed_reason") or "")
                ts = f.get("resolved_at") or f.get("dismissed_at") or ""
                if reason.startswith(("autopilot_", "auto_tune_", "stale_auto_", "boost_dev_")) and ts >= cutoff:
                    cnt_qa += 1
    except Exception:
        cnt_qa = 0
    mins = cnt_qa * ROI_MINUTES_PER_EVENT["auto_resolved_qa_finding"]
    breakdown.append({"source": "auto_resolved_qa_findings", "label": "QA findings auto-rezolvate", "count": cnt_qa, "minutes_per_event": ROI_MINUTES_PER_EVENT["auto_resolved_qa_finding"], "minutes_total": mins})
    total_minutes += mins

    # 5. Auto-approved KYC documents (status=approved AND reviewed_by=system_ai)
    try:
        cnt = await db.kyc_documents.count_documents({
            "reviewed_at": {"$gte": cutoff},
            "auto_approved": True,
        })
    except Exception:
        cnt = 0
    mins = cnt * ROI_MINUTES_PER_EVENT["auto_approved_kyc"]
    breakdown.append({"source": "auto_approved_kyc", "label": "KYC auto-aprobate (AI Vision)", "count": cnt, "minutes_per_event": ROI_MINUTES_PER_EVENT["auto_approved_kyc"], "minutes_total": mins})
    total_minutes += mins

    # 6. AI top-match notifications (immediate push to top 3 specialists)
    try:
        cnt_match = 0
        async for n in db.ai_match_notifications.find({"ran_at": {"$gte": cutoff}}, {"notified_count": 1}):
            cnt_match += int(n.get("notified_count") or 0)
    except Exception:
        cnt_match = 0
    mins = cnt_match * ROI_MINUTES_PER_EVENT["ai_top_match_notification"]
    breakdown.append({"source": "ai_top_match_notifications", "label": "AI top-match notifications", "count": cnt_match, "minutes_per_event": ROI_MINUTES_PER_EVENT["ai_top_match_notification"], "minutes_total": mins})
    total_minutes += mins

    hours_saved = round(total_minutes / 60.0, 1)
    money_saved = round(hours_saved * hourly_rate, 0)

    return {
        "window_days": days,
        "hourly_rate_ron": hourly_rate,
        "total_minutes_saved": total_minutes,
        "hours_saved": hours_saved,
        "money_saved_ron": money_saved,
        "breakdown": breakdown,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# V2: TASK GENERATION (from recommendations → admin_todos)
# ============================================================================
_PRIORITY_TODO_MAP = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}
_AREA_LABEL = {
    "operational": "Operațional",
    "technical": "Tehnic",
    "security": "Securitate",
    "dev": "Dev",
    "ai": "AI",
}


@router.post("/generate-tasks")
async def generate_tasks(
    payload: dict = Body(default={}),
    user=Depends(require_role("admin")),
):
    """Materialize current recommendations as actionable TODOs in admin_todos.
    Întoarce mereu JSON valid (și pe eroare), ca frontend-ul să nu primească HTML 500."""
    try:
        return await materialize_recommendations(
            max_items=int(payload.get("max_items", 6)),
            min_impact=float(payload.get("min_impact", 0.0)),
            dry_run=bool(payload.get("dry_run", False)),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("[autonomy] generate-tasks failed")
        return {"ok": False, "error": str(e)[:300], "counts": {"injected": 0, "skipped": 0, "considered": 0}}


async def materialize_recommendations(max_items: int = 6, min_impact: float = 0.0, dry_run: bool = False) -> dict:
    """Reusable: recomandările Autonomy → TODO-uri (de-dup pe text). Folosit și de Self-Driving cron."""

    # Always use a fresh report (no cache) so generated tasks reflect reality
    cfg = await load_targets()
    report = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
    recs = report.get("recommendations", []) or []
    recs = [r for r in recs if float(r.get("impact_points", 0)) >= min_impact][:max_items]

    now_iso = datetime.now(timezone.utc).isoformat()
    injected = []
    skipped = []
    for r in recs:
        area = r.get("area", "")
        area_label = _AREA_LABEL.get(area, area)
        priority = _PRIORITY_TODO_MAP.get(r.get("priority", "medium"), "medium")
        text = f"[Autonomy · {area_label}] {r.get('action','(no action)')}"
        text = text[:500]
        # de-dupe (case-insensitive) — re.escape ca textul cu [ ] ( ) · să nu producă regex invalid → 500
        existing = await db.admin_todos.find_one({"text": {"$regex": f"^{re.escape(text[:60])}", "$options": "i"}})
        if existing:
            skipped.append({"text": text, "reason": "duplicate"})
            continue
        todo_doc = {
            "id": str(uuid.uuid4()),
            "text": text,
            "priority": priority,
            "done": False,
            "source": f"autonomy_v2:{area}",
            "topic_title": f"Autonomy Engine · {area_label}",
            "created_at": now_iso,
            "meta": {
                "impact_points": r.get("impact_points"),
                "tier_at_creation": report.get("tier"),
                "general_score_at_creation": report.get("scores", {}).get("general"),
            },
        }
        if not dry_run:
            await db.admin_todos.insert_one({**todo_doc})
        injected.append({k: v for k, v in todo_doc.items() if k != "_id"})

    return {
        "ok": True,
        "dry_run": dry_run,
        "injected": injected,
        "skipped": skipped,
        "counts": {"injected": len(injected), "skipped": len(skipped), "considered": len(recs)},
        "general_score": report.get("scores", {}).get("general"),
        "tier": report.get("tier"),
    }


@router.get("/targets")
async def get_targets(user=Depends(require_role("admin"))):
    cfg = await load_targets()
    return cfg


@router.put("/targets")
async def update_targets(
    payload: dict = Body(...),
    user=Depends(require_role("admin")),
):
    weights = payload.get("weights")
    targets = payload.get("targets")
    if weights:
        expected = set(DEFAULT_WEIGHTS.keys())
        provided = set(weights.keys())
        if provided != expected:
            raise HTTPException(400, f"Weights must include exactly these keys: {sorted(expected)}")
        # Normalize: weights must sum to ~1.0
        total = sum(weights.values())
        if total <= 0:
            raise HTTPException(400, "Sum of weights must be > 0")
        weights = {k: v / total for k, v in weights.items()}
    update = {"updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": user["id"]}
    if weights:
        update["weights"] = weights
    if targets:
        update["targets"] = targets
    await db.autonomy_targets.update_one({"_id": "config"}, {"$set": update}, upsert=True)
    # Invalidate cache
    _CACHE["data"] = None
    return await load_targets()


@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = Query(20, ge=1, le=100),
    include_test: bool = Query(False, description="Include test alerts (synthetic) in the response"),
    user=Depends(require_role("admin")),
):
    """Recent autonomy tier-downgrade alerts (audit / dashboard widget).

    By default test alerts (``is_test=True``) are hidden — pass
    ``?include_test=true`` to see them.
    """
    q = {} if include_test else {"is_test": {"$ne": True}}
    cursor = db.autonomy_alerts.find(q, {"_id": 0}).sort("sent_at", -1).limit(limit)
    items = [d async for d in cursor]
    return {"items": items, "count": len(items)}


@router.post("/alerts/test")
async def trigger_test_alert(user=Depends(require_role("admin"))):
    """Force-trigger a tier-downgrade alert (super-admin only) for end-to-end test.

    Simulates a downgrade from self-driving → autonomous so admins can validate
    push + email dispatch without waiting for a real drop.
    """
    from sub_admin_deps import is_super_admin
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate trigger-a alerte de test.")

    from autonomy.alerts import check_and_alert_tier_downgrade
    now_iso = datetime.now(timezone.utc).isoformat()

    # Insert a synthetic "previous" snapshot 1h in the past at self-driving
    prev_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await db.autonomy_snapshots.insert_one({
        "snap_id": str(uuid.uuid4()),
        "timestamp": prev_ts,
        "scores": {"general": 92.0},
        "tier": "self-driving",
        "breakdown_summary": {"operational": 90, "technical": 95, "security": 95, "dev": 90, "ai": 88},
        "recommendations_count": 0,
        "synthetic_for_alert_test": True,
    })

    # Synthetic "current" snapshot at autonomous (lower tier)
    fake_current = {
        "snap_id": str(uuid.uuid4()),
        "timestamp": now_iso,
        "scores": {"general": 78.0},
        "tier": "autonomous",
        "breakdown_summary": {"operational": 75, "technical": 80, "security": 90, "dev": 75, "ai": 70},
        "recommendations_count": 3,
    }
    # Bypass dedupe by removing recent test alerts
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    await db.autonomy_alerts.delete_many({
        "prev_tier": "self-driving",
        "new_tier": "autonomous",
        "sent_at": {"$gte": cutoff},
    })
    result = await check_and_alert_tier_downgrade(fake_current)
    # Tag the alert as test so UI can filter it out by default
    if result.get("alerted") and (result.get("downgrade") or {}).get("sent_at"):
        await db.autonomy_alerts.update_one(
            {"sent_at": result["downgrade"]["sent_at"]},
            {"$set": {"is_test": True}},
        )
    # Cleanup the synthetic prev so it doesn't pollute trend data
    await db.autonomy_snapshots.delete_many({"synthetic_for_alert_test": True})
    return {"ok": True, "result": result}


@router.post("/seed-ai-data")
async def seed_ai_data(user=Depends(require_role("admin"))):
    """DEPRECATED (P1 decontamination — Iun 2026): no longer seeds synthetic data.

    This endpoint used to inject 17 fabricated internal docs + 100 synthetic
    memories to inflate the AI sub-score. Since scores now EXCLUDE synthetic
    seed rows, this "boost" is meaningless and would only pollute the DB, so it
    is now a NO-OP that simply reports the REAL knowledge-base counts.
    """
    from sub_admin_deps import is_super_admin
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate rula acest endpoint.")

    real_docs = await db.ai_documents.count_documents({"source": {"$ne": "autonomy_seed"}})
    real_mems = await db.ai_memories.count_documents({"source": {"$not": {"$regex": "^autonomy_seed"}}})
    seed_docs = await db.ai_documents.count_documents({"source": "autonomy_seed"})
    seed_mems = await db.ai_memories.count_documents({"source": {"$regex": "^autonomy_seed"}})

    return {
        "ok": True,
        "deprecated": True,
        "no_op": True,
        "message": (
            "Seed-ul de date sintetice a fost dezactivat. Scorul AI se calculează "
            "acum DOAR pe date reale; injectarea de docs/memorii sintetice nu mai "
            "influențează scorul și ar polua baza de date."
        ),
        "real_documents": real_docs,
        "real_memories": real_mems,
        "excluded_seed_documents": seed_docs,
        "excluded_seed_memories": seed_mems,
    }


async def run_auto_tune_orchestration(triggered_by: str = "manual") -> dict:
    """Reusable Auto-Tune orchestrator — callable from HTTP endpoint AND cron.

    ``triggered_by`` is logged in ``autopilot_runs`` (e.g. ``manual:<user_id>``,
    ``cron_weekly``). Idempotent — safe to call multiple times.

    DECONTAMINATED (P1 — Iun 2026): this orchestrator NO LONGER injects synthetic
    seed data (docs/memories/repair decisions/concierge traffic) and NO LONGER
    mass-dismisses open QA findings. Those steps existed only to inflate the
    autonomy/AI-Health scores with fabricated data — exactly what the founder
    asked to stop. Auto-Tune is now an HONEST recompute: it recalculates the
    scores from REAL signals and takes a fresh snapshot. Nothing is fabricated,
    nothing real is auto-dismissed.
    """
    report = {"steps": [], "triggered_by": triggered_by, "decontaminated": True}

    cfg = await load_targets()
    before_report = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
    report["before"] = {"scores": before_report["scores"], "tier": before_report["tier"]}

    # Steps 1-4 (synthetic seeding + mass finding-dismissal) REMOVED — these
    # contaminated the metrics with fabricated data. Recorded as skipped for
    # transparency in the run report.
    report["steps"].append({
        "name": "synthetic_seeding", "status": "skipped",
        "note": "Dezactivat: nu se mai injectează date sintetice (docs/memorii/repair/concierge).",
    })
    report["steps"].append({
        "name": "mass_dismiss_findings", "status": "skipped",
        "note": "Dezactivat: nu se mai marchează automat findings-uri reale ca 'dismissed'.",
    })

    # Step 5: Snapshot + invalidate cache
    snap = {}
    try:
        _CACHE["data"] = None
        snap = await take_autonomy_snapshot()
        report["steps"].append({"name": "refresh_snapshot", "status": "ok"})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[auto-tune] refresh_snapshot failed: {e}")
        report["steps"].append({"name": "refresh_snapshot", "status": "error", "error": str(e)[:160]})

    # AI Health refresh + persist today's row
    try:
        from routes.admin_ai import (
            _compute_findings_score, _compute_effectiveness_score, _compute_concierge_score,
        )
        f = await _compute_findings_score(7)
        e = await _compute_effectiveness_score(7)
        c = await _compute_concierge_score(7)
        ai_overall = round(0.40 * f["score"] + 0.35 * e["score"] + 0.25 * c["score"])
        today = datetime.now(timezone.utc).date().isoformat()
        await db.admin_ai_health_history.update_one(
            {"day": today},
            {"$set": {
                "day": today, "overall": ai_overall,
                "findings_score": f["score"], "effectiveness_score": e["score"], "concierge_score": c["score"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        report["ai_health"] = {
            "overall": ai_overall, "findings": f["score"],
            "effectiveness": e["score"], "concierge": c["score"],
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[auto-tune] ai_health recompute failed: {e}")
        report["ai_health"] = {"error": str(e)[:160]}

    report["after"] = {"scores": (snap or {}).get("scores"), "tier": (snap or {}).get("tier")}
    if report["after"]["scores"] and report["before"]["scores"]:
        report["delta_general"] = round(
            report["after"]["scores"].get("general", 0) - report["before"]["scores"].get("general", 0), 1
        )

    # Audit log
    try:
        await db.autopilot_runs.insert_one({
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "kind": "auto_tune",
            "triggered_by": triggered_by,
            "decontaminated": True,
            "result": {
                "delta_general": report.get("delta_general"),
                "tier_after": report["after"]["tier"],
                "ai_health_overall": (report.get("ai_health") or {}).get("overall"),
                "steps_ok": sum(1 for s in report["steps"] if s.get("status") == "ok"),
                "steps_total": len(report["steps"]),
            },
        })
    except Exception:  # noqa: BLE001
        pass

    logger.info(
        f"[auto-tune] done ({triggered_by}): tier={report['after']['tier']} "
        f"ai_health={(report.get('ai_health') or {}).get('overall')}"
    )
    return report


async def weekly_auto_tune_job() -> dict:
    """APScheduler callable — runs Auto-Tune every Monday 04:00 Europe/Bucharest.

    DECONTAMINATED (P1 — Iun 2026): the previous "adaptive escalation" second
    pass (mass-dismiss all open low/medium AI findings + re-seed 20 synthetic
    repair decisions) was pure score inflation and has been REMOVED. The weekly
    job now only performs the HONEST recompute + snapshot. If the tier is below
    ``self-driving`` that reflects the REAL state and is left visible — the
    platform must earn the tier from real signals, not fabricated data.
    """
    primary = await run_auto_tune_orchestration(triggered_by="cron_weekly")
    tier_after = (primary.get("after") or {}).get("tier")

    # Second-pass aggressive sweep REMOVED (contaminated metrics). Honest tier
    # is left as-is. Alert super-admins on a genuine sub-self-driving tier so a
    # human can act on the REAL gap instead of auto-hiding it.
    if tier_after and tier_after != "self-driving":
        logger.info(f"[auto-tune] honest tier={tier_after} below self-driving — left visible (no auto-heal).")

    primary["secondary_pass"] = None
    return primary


@router.post("/auto-tune")
async def auto_tune(user=Depends(require_role("admin"))):
    """One-click orchestrator: maximizes Autonomy + AI Health scores in one call.

    Super-admin only. See ``run_auto_tune_orchestration`` for step details.
    """
    from sub_admin_deps import is_super_admin
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate rula Auto-Tune.")
    report = await run_auto_tune_orchestration(triggered_by=f"manual:{user['id']}")
    return {"ok": True, "report": report}


@router.post("/founder-digest/send-now")
async def trigger_founder_digest(user=Depends(require_role("admin"))):
    """Force-send the weekly founders' digest right now (super-admin only).

    Useful for previewing the digest without waiting for Monday 09:30 cron.
    """
    from sub_admin_deps import is_super_admin
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate trimite digest-ul manual.")
    from autonomy.founder_digest import weekly_founder_digest
    result = await weekly_founder_digest()
    return {"ok": True, "result": result}


# ═══════════════════════ OPERATIONAL AUTONOMY LOOP (FN-021) ═══════════════════════
# Închide bucla Analytics → Finding → Decizie → Acțiune → Verify → Learn.
# Reutilizează admin_ai_findings + admin_todos + admin_approvals + self_driving.
from autonomy import loop as autonomy_loop  # noqa: E402


@router.post("/loop/run")
async def run_operational_loop(user=Depends(require_role("admin"))):
    """Rulează o iterație completă a buclei operaționale (OBSERVE→...→LEARN)."""
    result = await autonomy_loop.run_loop_tick(triggered_by=f"manual:{user.get('email','admin')}")
    return {"ok": True, "run": result}


@router.get("/loop/runs")
async def list_operational_loop_runs(limit: int = Query(10, ge=1, le=50), user=Depends(require_role("admin"))):
    """Ultimele rulări ale buclei (ledger autonomy_loop_runs)."""
    runs = await db.autonomy_loop_runs.find({}, {"_id": 0}).sort("started_at", -1).to_list(limit)
    return {"items": runs}


@router.get("/loop/policy")
async def get_operational_loop_policy(user=Depends(require_role("admin"))):
    """Politica de acțiune + pragurile deterministe + descrierea etapelor buclei."""
    return {
        "action_policy": autonomy_loop.ACTION_POLICY,
        "policy_description": autonomy_loop.POLICY_DESCRIPTION,
        "thresholds": {
            "bounce_min_sessions": autonomy_loop.BOUNCE_MIN_SESSIONS,
            "bounce_min_pct": autonomy_loop.BOUNCE_MIN_PCT,
            "funnel_min_started": autonomy_loop.FUNNEL_MIN_STARTED,
            "funnel_max_conversion_pct": autonomy_loop.FUNNEL_MAX_CONVERSION_PCT,
            "max_findings_per_run": autonomy_loop.MAX_FINDINGS_PER_RUN,
            "dedup_window_hours": autonomy_loop.DEDUP_WINDOW_HOURS,
            "lookback_days": autonomy_loop.ANALYTICS_LOOKBACK_DAYS,
        },
        "stages": ["OBSERVE", "DETECT", "FINDING", "DECIDE/POLICY/RISK", "ACT", "VERIFY", "RECORD", "LEARN"],
    }


@router.get("/activity")
async def get_autonomy_activity(user=Depends(require_role("admin"))):
    """Read-model UNIFICAT: coada de acțiuni + metrici REALE de autonomie.
    Proiectează artefactele existente (findings/todos/approvals/loop_runs/playbook_executions/
    ai_memories + semnale bottleneck) — CE A FĂCUT / AȘTEAPTĂ / A EȘUAT / NECESITĂ OM / A ÎNVĂȚAT."""
    from autonomy import activity
    return await activity.get_activity()


@router.post("/disputes/triage")
async def trigger_dispute_triage(
    limit: int = Query(30, ge=1, le=50),
    use_llm: bool = Query(True),
    force: bool = Query(False),
    user=Depends(require_role("admin")),
):
    """Backfill bounded de triaj pe disputele deschise (reutilizează triajul Claude existent).
    Non-destructiv: adaugă analiză, NU rezolvă disputele. Idempotent."""
    from autonomy import disputes
    result = await disputes.triage_open_disputes(limit=limit, use_llm=use_llm, force=force)
    return {"ok": True, **result, "metrics": await disputes.dispute_metrics()}


class LifecycleTransitionIn(BaseModel):
    transition: str  # active_to_on_hold | on_hold_to_archived
    reason: Optional[str] = None


@router.post("/projects/{project_id}/lifecycle")
async def admin_project_lifecycle(project_id: str, body: LifecycleTransitionIn, user=Depends(require_role("admin"))):
    """API ÎNGUST de lifecycle (nu update generic). Tranziții explicite validate.
    SAFE (active→on_hold) se poate executa direct; MEDIUM (on_hold→archived) întoarce
    `requires_human_approval` → creează o aprobare în admin_approvals (gate uman)."""
    from autonomy.lifecycle import transition_project, ALLOWED_TRANSITIONS
    if body.transition not in ALLOWED_TRANSITIONS:
        raise HTTPException(400, f"Tranziție nepermisă. Permise: {list(ALLOWED_TRANSITIONS)}")
    res = await transition_project(project_id, body.transition, actor=user,
                                   autoexec_allowed=True, reason=body.reason or f"Admin {user.get('email','')}")
    # MEDIUM → creează aprobare umană (reutilizează admin_approvals)
    if res.get("status") == "requires_human_approval":
        approval_id = str(uuid.uuid4())
        await db.admin_approvals.insert_one({
            "id": approval_id, "action": "project_lifecycle_transition",
            "payload": {"project_id": project_id, "transition": body.transition, "reason": body.reason or "archivare"},
            "scope": "general", "requested_by": "admin", "requested_by_email": user.get("email"),
            "requested_by_seniority": "junior", "reason": f"Arhivare proiect {project_id} (necesită aprobare senior).",
            "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {**res, "approval_created": approval_id}
    return res


@router.get("/projects/lifecycle/audit")
async def get_lifecycle_audit(limit: int = Query(20, ge=1, le=100), user=Depends(require_role("admin"))):
    """Ledger de audit al tranzițiilor de lifecycle."""
    items = await db.project_lifecycle_actions.find({}, {"_id": 0}).sort("requested_at", -1).to_list(limit)
    return {"items": items}
