"""Phase 1 · TD-08 — Politica unitară de retenție telemetrie (cron zilnic 03:40).
1. AGE_RETENTION: șterge rândurile mai vechi de N zile (după coloana created_at, direct în SQL —
   fără să citească documentele, deci fără egress).
2. RETENTION: păstrează ultimele N documente per colecție; restul se șterg.
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


# colecție -> (zile păstrate, filtru SQL suplimentar pe `data`)
AGE_RETENTION = {
    "health_pings": (14, ""),
    "smoke_test_runs": (30, ""),
    "agent_runs": (30, ""),
    "orchestrator_retry_queue": (30, "and coalesce(data->>'status', '') <> 'pending'"),
    "cs_findings": (90, ""),
    "email_log": (90, ""),
    "ai_brain_navigation": (90, ""),
    "notifications": (180, ""),
    "admin_actions_log": (365, ""),
    "analytics_events": (365, ""),
    "analytics_sessions": (365, ""),
}


async def _age_retention(out: dict) -> None:
    async with db._conn() as conn:
        for coll_name, (days, extra) in AGE_RETENTION.items():
            try:
                if not await db._exists(coll_name, conn):
                    continue
                status = await conn.execute(
                    f'delete from {db.schema}."{coll_name}" '
                    f"where created_at < now() - make_interval(days => $1) {extra}", days)
                n = int(status.split()[-1])
                if n:
                    out[coll_name] = n
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[retention] {coll_name}: {e}")


async def telemetry_retention_tick() -> dict:
    out = {}
    await _age_retention(out)
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
            out[coll_name] = out.get(coll_name, 0) + res.deleted_count
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[retention] {coll_name}: {e}")
    if out:
        logger.info(f"[retention] trimmed: {out}")
    return out
