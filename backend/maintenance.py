"""Phase 1 · TD-08 — Politica unitară de retenție telemetrie (cron zilnic 03:40).
Păstrează ultimele N documente per colecție de telemetrie; restul se șterg.
"""
import logging

from db import db

logger = logging.getLogger("propmanage.maintenance")

RETENTION = {
    "analytics_events": ("created_at", 100_000),
    "admin_audit_log": ("created_at", 50_000),
    "orchestrator_signals": ("ts", 2_000),
    "orchestrator_ledger": ("ts", 5_000),
    "notifications": ("created_at", 100_000),
}


async def telemetry_retention_tick() -> dict:
    out = {}
    for coll_name, (field, keep) in RETENTION.items():
        try:
            coll = db[coll_name]
            total = await coll.estimated_document_count()
            if total <= keep:
                continue
            pivot = await coll.find({}, {field: 1}).sort(field, -1).skip(keep).limit(1).to_list(1)
            if not pivot:
                continue
            res = await coll.delete_many({field: {"$lt": pivot[0][field]}})
            out[coll_name] = res.deleted_count
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[retention] {coll_name}: {e}")
    if out:
        logger.info(f"[retention] trimmed: {out}")
    return out
