"""Autonomy snapshots + score cache — shared between routes and autopilot.

Extracted from routes/autonomy.py to break the circular dependency
routes/autonomy.py ↔ autonomy/autopilot.py. Both now import from here.
"""
import logging
import uuid

from db import db
from autonomy.engine import compute_autonomy_scores, DEFAULT_WEIGHTS, DEFAULT_TARGETS

logger = logging.getLogger("propmanage.autonomy_snapshots")

# Simple in-memory cache for the live score (5 min TTL)
_CACHE = {"data": None, "ts": None}
_CACHE_TTL_SECONDS = 300


async def load_targets() -> dict:
    doc = await db.autonomy_targets.find_one({"_id": "config"})
    if not doc:
        return {"weights": DEFAULT_WEIGHTS, "targets": DEFAULT_TARGETS}
    return {
        "weights": doc.get("weights") or DEFAULT_WEIGHTS,
        "targets": doc.get("targets") or DEFAULT_TARGETS,
    }


async def take_autonomy_snapshot() -> dict:
    """Compute current autonomy + persist to autonomy_snapshots.

    Called daily at 03:15 Europe/Bucharest by the scheduler.
    Safe to call multiple times per day (creates separate doc per call).
    """
    try:
        cfg = await load_targets()
        report = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
        doc = {
            "snap_id": str(uuid.uuid4()),
            "timestamp": report["computed_at"],
            "scores": report["scores"],
            "tier": report["tier"],
            "breakdown_summary": {
                k: report["breakdown"][k]["score"]
                for k in ("operational", "technical", "security", "dev", "ai")
            },
            "recommendations_count": len(report["recommendations"]),
        }
        await db.autonomy_snapshots.insert_one(doc)
        logger.info(f"Autonomy snapshot recorded: general={report['scores']['general']} tier={report['tier']}")
        # Cleanup: keep max 400 snapshots
        cur = db.autonomy_snapshots.find({}, {"_id": 1}).sort("timestamp", -1).skip(400)
        old_ids = [d["_id"] async for d in cur]
        if old_ids:
            await db.autonomy_snapshots.delete_many({"_id": {"$in": old_ids}})
        doc.pop("_id", None)

        # Tier downgrade alert (fire-and-forget — never blocks snapshot)
        try:
            from autonomy.alerts import check_and_alert_tier_downgrade
            await check_and_alert_tier_downgrade(doc)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[autonomy.snapshot] alert check failed: {e}")

        return doc
    except Exception as e:  # noqa: BLE001
        logger.error(f"Autonomy snapshot failed: {e}", exc_info=True)
        return {"error": str(e)}


DROP_THRESHOLD_PP = 5


async def take_autonomy_snapshot_with_reflex() -> dict:
    """Scheduler entry-point: snapshot + Autonomy Reflex signal on >5pp drop.

    The orchestrator playbook re-snapshots via the plain take_autonomy_snapshot,
    so no signal loop is possible.
    """
    prev = await db.autonomy_snapshots.find_one({}, sort=[("timestamp", -1)])
    doc = await take_autonomy_snapshot()
    if doc.get("error") or not prev:
        return doc
    try:
        drops = {}
        prev_axes = prev.get("breakdown_summary") or {}
        new_axes = doc.get("breakdown_summary") or {}
        for axis, new_v in new_axes.items():
            old_v = prev_axes.get(axis)
            if old_v is not None and (old_v - new_v) > DROP_THRESHOLD_PP:
                drops[axis] = round(old_v - new_v, 1)
        prev_general = (prev.get("scores") or {}).get("general") or 0
        new_general = (doc.get("scores") or {}).get("general") or 0
        if (prev_general - new_general) > DROP_THRESHOLD_PP:
            drops["general"] = round(prev_general - new_general, 1)
        if drops:
            from orchestrator.engine import emit_signal
            await emit_signal("autonomy_score_drop", {
                "drops": drops,
                "prev_general": prev_general,
                "new_general": new_general,
                "tier": doc.get("tier"),
            })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autonomy.snapshot] reflex signal failed: {e}")
    return doc
