"""AI Brain · Core — punctul unic de acces al subsistemului AI Brain.

Sprint 1 (AIB-001): orchestrează Discovery Engine → Knowledge Registry și expune status.
Integrat cu Guardian Kernel: fiecare descoperire se loghează în orchestrator_ledger,
iar status-ul agregă scorurile guardienilor.
"""
import logging
import time
import uuid
from datetime import datetime, timezone

from db import db
from ai_brain import discovery, registry

logger = logging.getLogger("propmanage.ai_brain")

VERSION = "1.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_discovery(trigger: str = "cron") -> dict:
    t0 = time.monotonic()
    run_id = uuid.uuid4().hex

    routes = discovery.discover_routes()
    pages = discovery.discover_pages()
    components = discovery.discover_components()
    apis = discovery.discover_apis()
    services = discovery.discover_services()
    modules = discovery.discover_modules(apis, routes)
    roles = await discovery.discover_roles(apis)
    menus = await discovery.discover_menus()

    counts = {}
    for kind, data in (("routes", routes), ("pages", pages), ("components", components),
                       ("apis", apis), ("services", services), ("modules", modules),
                       ("roles", roles), ("menus", menus)):
        counts[kind] = await registry.store(kind, data, run_id)
    counts["roles"] = len(roles["all"])
    counts["components"] = len(components["app"]) + len(components["ui"])

    duration_ms = round((time.monotonic() - t0) * 1000)
    # AIB-005: reconstruiește Knowledge Graph după fiecare discovery
    graph_meta = None
    try:
        from ai_brain.graph import build_graph
        graph_meta = await build_graph()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai-brain] graph build failed: {e}")
    # AIB-006: reconstruiește Process Registry (după graf — adaugă noduri process:proc_*)
    proc_meta = None
    try:
        from ai_brain.process import build_processes
        proc_meta = await build_processes(run_id)
        counts["processes"] = proc_meta["total"]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai-brain] process build failed: {e}")
    # AIB-009: SLA sweep + notificări inteligente după fiecare discovery
    sla_meta = None
    try:
        from ai_brain.collaboration import sla_sweep
        sla_meta = await sla_sweep(run_id)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai-brain] sla sweep failed: {e}")
    run = {"id": run_id, "ts": _now(), "trigger": trigger,
           "duration_ms": duration_ms, "counts": counts, "graph": graph_meta,
           "processes": proc_meta, "sla": sla_meta}
    await db.ai_brain_runs.insert_one({**run})

    from orchestrator.engine import write_ledger
    await write_ledger({
        "signal_kind": "ai_brain", "playbook_id": "ai_brain_discovery",
        "playbook_name": "AI Brain Discovery",
        "steps": [{"action": "discover_application", "ok": True,
                   "detail": f"Aplicație cartografiată în {duration_ms}ms: {counts['modules']} module, "
                             f"{counts['routes']} rute, {counts['pages']} pagini, {counts['apis']} API-uri, "
                             f"{counts['services']} servicii, {counts['roles']} roluri"}],
        "outcome": "auto_resolved", "minutes_saved": 5, "escalated": False, "test": False,
    })
    logger.info(f"[ai-brain] discovery done in {duration_ms}ms: {counts}")
    run.pop("_id", None)
    return run


async def ai_brain_status() -> dict:
    last_run = await db.ai_brain_runs.find_one({}, {"_id": 0}, sort=[("ts", -1)])
    arch = await db.architecture_guardian_runs.find_one({}, {"architecture_score": 1}, sort=[("ts", -1)])
    prod = await db.product_guardian_runs.find_one({}, {"product_score": 1, "platform_score": 1}, sort=[("ts", -1)])
    return {
        "status": "active" if last_run else "never_ran",
        "version": VERSION,
        "capabilities": ["discovery", "knowledge_registry", "context", "explainability",
                         "mentor", "knowledge_graph", "process_intelligence",
                         "decision_intelligence", "adaptive_intelligence",
                         "collaborative_intelligence", "certification"],
        "last_run": last_run,
        "registry": {**await registry.counts(),
                     "processes": await db.ai_brain_processes.count_documents({})},
        "certification": await db.ai_brain_certification.find_one(
            {}, {"_id": 0, "verdict": 1, "scores": 1, "version": 1, "generated_at": 1},
            sort=[("generated_at", -1)]),
        "guardians": {
            "architecture_score": (arch or {}).get("architecture_score"),
            "product_score": (prod or {}).get("product_score"),
            "platform_score": (prod or {}).get("platform_score"),
        },
    }
