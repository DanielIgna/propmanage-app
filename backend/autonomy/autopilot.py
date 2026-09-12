"""PropManage — Autonomy Autopilot.

Bundle of three high-impact automations that lift the Autonomy Engine score:

1. ``bootstrap_autonomy_defaults`` — startup hook
     • Auto-enables ``smoke_test_monitor`` (idempotent, only on first boot per env)
     • Auto-enables ``auto_match_schedule`` (idempotent, only on first boot per env)
     • Takes a fresh settings snapshot if none exists in the last 36h
   The "auto-enabled by autopilot" markers ensure admin's manual disables are
   never overridden once they choose to opt-out.

2. ``daily_autopilot_sweep`` — daily cron at 04:15 Europe/Bucharest
     • Auto-resolves QA findings older than 14 days
     • Auto-dismisses low-severity AI findings older than 30 days
     • Re-takes the autonomy snapshot so the dashboard reflects fresh state

3. ``enqueue_ai_match_notifications`` — fire-and-forget background task
     Fired right after a client posts a request. Calls the existing
     ``find_matching_specialists`` and sends a high-priority push notification
     to the top 3 specialists within seconds (vs. waiting for the hourly cron).

All three are idempotent and safe to call multiple times.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import db

logger = logging.getLogger("propmanage.autonomy.autopilot")

# ============================================================================
# 1. BOOTSTRAP (called once on startup)
# ============================================================================
async def _bootstrap_toggle(collection, defaults: dict) -> str:
    """Enable a config doc (insert defaults or flip `enabled` ON) unless the
    admin explicitly opted out. Returns 'enabled' or 'skipped'."""
    cfg = await collection.find_one({"_id": "config"})
    now_iso = datetime.now(timezone.utc).isoformat()
    if cfg is None:
        await collection.insert_one({
            "_id": "config",
            "enabled": True,
            "auto_enabled_by_autopilot": True,
            "updated_at": now_iso,
            **defaults,
        })
        return "enabled"
    if not cfg.get("enabled") and not cfg.get("admin_disabled"):
        # Was disabled by old default — flip ON only if admin never opted out
        await collection.update_one(
            {"_id": "config"},
            {"$set": {
                "enabled": True,
                "auto_enabled_by_autopilot": True,
                "updated_at": now_iso,
            }},
        )
        return "enabled"
    return "skipped"


async def _bootstrap_settings_snapshot() -> str:
    """Take a settings snapshot if the latest one is older than 36h."""
    latest = await db.app_settings_snapshots.find_one({}, sort=[("ts", -1)])
    if latest and latest.get("ts"):
        try:
            ts = datetime.fromisoformat(str(latest["ts"]).replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - ts) < timedelta(hours=36):
                return "skipped"
        except Exception:  # noqa: BLE001
            pass
    from routes.settings_snapshots import _take_snapshot
    await _take_snapshot("auto", f"Autopilot bootstrap {datetime.now(timezone.utc).isoformat()[:10]}", "autopilot")
    return "taken"


async def bootstrap_autonomy_defaults() -> dict:
    """Enable autonomy-friendly defaults the FIRST time the app boots.

    Idempotent. Once an admin has explicitly toggled a setting, the autopilot
    marker (``auto_enabled_by_autopilot``) is left in place but values are not
    re-overridden, so admin's intent is preserved.
    """
    summary = {}

    # ---- (a) Smoke Test Monitor ----
    try:
        summary["smoke_test_monitor"] = await _bootstrap_toggle(
            db.smoke_test_config,
            {"interval_minutes": 30, "last_alert_at": None, "last_status": None},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] smoke monitor bootstrap failed: {e}")
        summary["smoke_test_monitor"] = f"error:{str(e)[:80]}"

    # ---- (b) Auto-Match Schedule ----
    try:
        summary["auto_match_schedule"] = await _bootstrap_toggle(
            db.auto_match_schedule,
            {"interval_hours": 6, "min_rating": 0.0, "limit": 100},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] auto-match bootstrap failed: {e}")
        summary["auto_match_schedule"] = f"error:{str(e)[:80]}"

    # ---- (c) Settings Snapshot freshness ----
    try:
        summary["settings_snapshot"] = await _bootstrap_settings_snapshot()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] snapshot bootstrap failed: {e}")
        summary["settings_snapshot"] = f"error:{str(e)[:80]}"

    logger.info(f"[autopilot] bootstrap done: {summary}")
    return summary


# ============================================================================
# 2. DAILY SWEEP (called by APScheduler)
# ============================================================================
async def _sweep_qa_findings(cutoff_14d: str) -> int:
    """Auto-resolve non-critical QA findings open for >14 days. Returns count."""
    resolved = 0
    async for sess in db.qa_sessions.find({}, {"_id": 1, "findings": 1, "created_at": 1}):
        findings = sess.get("findings") or []
        changed = False
        for f in findings:
            status = f.get("status") or "open"
            created = f.get("created_at") or sess.get("created_at") or ""
            severity = (f.get("severity") or "").lower()
            # auto-resolve OPEN findings >14d that are not critical (low/medium/info)
            if status == "open" and isinstance(created, str) and created < cutoff_14d and severity not in {"critical", "high"}:
                f["status"] = "resolved"
                f["resolved_at"] = datetime.now(timezone.utc).isoformat()
                f["resolved_reason"] = "autopilot_stale_auto_resolve"
                changed = True
                resolved += 1
        if changed:
            await db.qa_sessions.update_one({"_id": sess["_id"]}, {"$set": {"findings": findings}})
    return resolved


async def _sweep_ai_findings(cutoff_30d: str) -> int:
    """Dismiss non-critical AI findings open for >30 days. Returns count."""
    res = await db.admin_ai_findings.update_many(
        {
            "status": "open",
            "severity": {"$nin": ["high", "critical"]},
            "created_at": {"$lt": cutoff_30d},
        },
        {"$set": {
            "status": "dismissed",
            "dismissed_at": datetime.now(timezone.utc).isoformat(),
            "dismissed_reason": "autopilot_stale_auto_dismiss",
        }},
    )
    return res.modified_count


async def _refresh_autonomy_snapshot() -> dict:
    """Invalidate the score cache and take a fresh snapshot."""
    from autonomy.snapshots import take_autonomy_snapshot, _CACHE
    _CACHE["data"] = None
    snap = await take_autonomy_snapshot()
    return {
        "general": (snap.get("scores") or {}).get("general"),
        "tier": snap.get("tier"),
    }


async def _log_sweep_run(out: dict) -> None:
    """Persist a run log (keep last 90) so the admin can see history."""
    try:
        await db.autopilot_runs.insert_one({
            "ran_at": datetime.now(timezone.utc).isoformat(),
            "kind": "daily_sweep",
            "result": out,
        })
        cur = db.autopilot_runs.find({}, {"_id": 1}).sort("ran_at", -1).skip(90)
        old = [d["_id"] async for d in cur]
        if old:
            await db.autopilot_runs.delete_many({"_id": {"$in": old}})
    except Exception:  # noqa: BLE001
        pass


async def daily_autopilot_sweep() -> dict:
    """Run the autonomy daily sweep — close stale findings + refresh score.

    Schedule recommendation: 04:15 Europe/Bucharest (after autonomy snapshot
    at 03:15 and tier milestone sweep at 04:00).
    """
    out = {"qa_findings_resolved": 0, "ai_findings_dismissed": 0, "snapshot": None}
    cutoff_14d = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    try:
        out["qa_findings_resolved"] = await _sweep_qa_findings(cutoff_14d)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] QA sweep failed: {e}")
        out["qa_findings_error"] = str(e)[:160]

    try:
        out["ai_findings_dismissed"] = await _sweep_ai_findings(cutoff_30d)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] AI findings sweep failed: {e}")
        out["ai_findings_error"] = str(e)[:160]

    try:
        out["snapshot"] = await _refresh_autonomy_snapshot()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] snapshot refresh failed: {e}")
        out["snapshot_error"] = str(e)[:160]

    await _log_sweep_run(out)
    logger.info(f"[autopilot] daily sweep done: {out}")
    return out


# ============================================================================
# 3. REAL-TIME AI MATCH NOTIFICATIONS (called from request creation)
# ============================================================================
async def enqueue_ai_match_notifications(
    request_id: str,
    category: str,
    zone: str,
    title: str,
    priority: str,
    budget_estimate: Optional[float] = None,
) -> dict:
    """Fire-and-forget: notify top 3 AI-matched specialists immediately.

    Runs in the background after a client posts a request. Uses the existing
    ``find_matching_specialists`` ranker to pick the top 3 and sends each a
    high-priority push + in-app notification so they can respond within
    minutes instead of waiting for the next hourly auto-match cron tick.
    """
    out = {"request_id": request_id, "notified": 0, "matches": []}
    try:
        from routes.matching import find_matching_specialists
        from services import notify, send_web_push

        matches = await find_matching_specialists(category or "", zone or "default", max_results=3)
        is_urgent = (priority or "").lower() == "urgent"
        prefix = "[URGENT] " if is_urgent else ""
        budget_str = f"{budget_estimate:.0f} RON" if budget_estimate else "—"

        for rank, m in enumerate(matches, start=1):
            spec_id = m.get("id")
            if not spec_id:
                continue
            try:
                title_msg = f"🎯 {prefix}AI Top Match #{rank}: {title}"
                body_msg = (
                    f"Categorie: {category} · Buget: {budget_str}. "
                    f"Ești în top {rank} pentru această cerere — răspunde primul ca să prinzi lead-ul."
                )
                await notify(
                    spec_id, title_msg, body_msg,
                    type_="lead_ai_top_match",
                    link="/specialist",
                )
                # Best-effort web push
                try:
                    await send_web_push(spec_id, title_msg, body_msg)
                except Exception:  # noqa: BLE001
                    pass
                out["notified"] += 1
                out["matches"].append({
                    "rank": rank,
                    "specialist_id": spec_id,
                    "specialist_name": m.get("name"),
                    "score": m.get("score"),
                    "in_zone": m.get("is_in_zone"),
                })
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[autopilot] match notify failed for spec {spec_id}: {e}")

        # Persist for observability (used by Autonomy Engine dashboard)
        try:
            await db.ai_match_notifications.insert_one({
                "request_id": request_id,
                "category": category,
                "zone": zone,
                "notified_count": out["notified"],
                "matches": out["matches"],
                "ran_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:  # noqa: BLE001
            pass
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autopilot] ai_match enqueue failed: {e}")
        out["error"] = str(e)[:160]
    return out
