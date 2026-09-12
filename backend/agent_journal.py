"""Jurnalul central al agenților (Sprint 1 / Felia 1).

APScheduler listener → db.agent_runs: fiecare execuție a celor 51+ cron jobs este înregistrată
(ok / error / missed). Fundația de observabilitate pentru Mission Control (Prompt 003).
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED

from db import db

logger = logging.getLogger("propmanage.agent_journal")
_LOOP = None


def attach_journal(scheduler, loop) -> None:
    global _LOOP
    _LOOP = loop
    scheduler.add_listener(_on_job_event, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    logger.info("Agent journal attached — all scheduler runs are now recorded in agent_runs.")


def _on_job_event(event) -> None:
    exc = getattr(event, "exception", None)
    status = "error" if exc else ("missed" if event.code == EVENT_JOB_MISSED else "ok")
    doc = {
        "job_id": getattr(event, "job_id", "?"),
        "status": status,
        "error": str(exc)[:300] if exc else None,
        "scheduled_for": str(getattr(event, "scheduled_run_time", "") or ""),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        if _LOOP and _LOOP.is_running():
            asyncio.run_coroutine_threadsafe(_write(doc), _LOOP)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"agent journal schedule failed: {e}")


async def _write(doc: dict) -> None:
    try:
        await db.agent_runs.insert_one(doc)
        n = await db.agent_runs.estimated_document_count()
        if n > 6000:
            cur = db.agent_runs.find({}, {"_id": 1}).sort("ts", -1).skip(5000)
            old = [d["_id"] async for d in cur]
            if old:
                await db.agent_runs.delete_many({"_id": {"$in": old}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"agent journal write failed: {e}")
