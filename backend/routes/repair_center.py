"""Repair Center API — Health Repair Engine (PM-AI-REPAIR-001).

  GET  /api/admin/repair-center/status   — scoruri live + motoare + ultima rulare
  POST /api/admin/repair-center/run      — rulează ciclul (body: {domains: [...]} opțional)
  GET  /api/admin/repair-center/runs     — istoric rulări
"""
import logging

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role
from health_repair import DOMAIN_ENGINES, run_repair_cycle

logger = logging.getLogger("propmanage.repair_center")
router = APIRouter(prefix="/api/admin/repair-center", tags=["repair-center"])
_running_task = None


@router.get("/status")
async def repair_status(user=Depends(require_role("admin"))):
    from routes.enterprise_health import _get_formulas, _collect_metrics, _domain_result, DOMAIN_LABELS
    formulas = await _get_formulas()
    metrics = await _collect_metrics()
    last_run = await db.health_repair_runs.find_one({}, {"_id": 0}, sort=[("ts", -1)])
    # last_repair per domeniu — din cea mai recentă rulare care a atins domeniul
    last_by_domain = {}
    async for run in db.health_repair_runs.find({}, {"_id": 0, "ts": 1, "results": 1}).sort("ts", -1).limit(20):
        for r in run.get("results", []):
            if r["domain"] not in last_by_domain:
                last_by_domain[r["domain"]] = {**r, "_run_ts": run["ts"]}

    domains = []
    for key in DOMAIN_ENGINES:
        f = formulas.get(key)
        if not f or f.get("status") != "active":
            continue
        res = _domain_result(f, metrics)
        lr = last_by_domain.get(key)
        domains.append({
            "domain": key,
            "label": DOMAIN_LABELS.get(key, key),
            "score": res["score"],
            "warning_threshold": f.get("warning_threshold", 80),
            "has_engine": True,
            "last_repair": {"ts": lr["_run_ts"], "problems": len(lr["problems"]),
                            "actions": len(lr["actions"]), "delta": lr.get("delta")} if lr else None,
        })
    domains.sort(key=lambda d: d["score"])
    from orchestrator.governance import compute_autonomy_score
    return {"domains": domains, "last_run": last_run,
            "autonomy": await compute_autonomy_score(),
            "runs_total": await db.health_repair_runs.count_documents({})}


@router.post("/run")
async def repair_run(payload: dict = Body(default={}), user=Depends(require_role("admin"))):
    domains = payload.get("domains")
    if domains is not None:
        if not isinstance(domains, list) or not domains:
            raise HTTPException(400, "domains trebuie să fie o listă nevidă")
        invalid = [d for d in domains if d not in DOMAIN_ENGINES]
        if invalid:
            raise HTTPException(400, f"Domenii invalide: {invalid}. Valide: {list(DOMAIN_ENGINES)}")
    # Rulare în background — ciclul complet poate depăși timeout-ul gateway-ului.
    import asyncio
    global _running_task
    if _running_task and not _running_task.done():
        raise HTTPException(409, "Un ciclu de reparație rulează deja. Așteaptă finalizarea.")

    async def _guarded():
        try:
            await run_repair_cycle(domains=domains, trigger=f"manual:{user.get('email')}")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[repair-center] background cycle failed: {e}", exc_info=True)

    _running_task = asyncio.create_task(_guarded())
    return {"started": True, "domains": domains or "all"}


@router.get("/runs")
async def repair_runs(limit: int = 10, user=Depends(require_role("admin"))):
    limit = max(1, min(int(limit), 50))
    items = [d async for d in db.health_repair_runs.find({}, {"_id": 0}).sort("ts", -1).limit(limit)]
    return {"items": items}


# ============================================================================
# CUSTOMER JOURNEY GUARDIAN — audit continuu al călătoriei clientului
# ============================================================================
@router.get("/journey-guardian/status")
async def guardian_status(user=Depends(require_role("admin"))):
    last_run = await db.journey_guardian_runs.find_one({}, {"_id": 0}, sort=[("ts", -1)])
    tasks = [t async for t in db.journey_guardian_tasks.find(
        {"status": "open"}, {"_id": 0}).sort([("severity", 1), ("created_at", -1)]).limit(50)]
    resolved_total = await db.journey_guardian_tasks.count_documents({"status": "resolved"})
    return {"last_run": last_run, "open_tasks": tasks, "resolved_total": resolved_total}


@router.post("/journey-guardian/run")
async def guardian_run(user=Depends(require_role("admin"))):
    from journey_guardian import run_journey_guardian
    return await run_journey_guardian(trigger=f"manual:{user.get('email')}")


# ============================================================================
# ARCHITECTURE GUARDIAN — impune arhitectura canonică (PM-GUARDIAN-001/002)
# ============================================================================
@router.get("/architecture-guardian/status")
async def arch_guardian_status(user=Depends(require_role("admin"))):
    last_run = await db.architecture_guardian_runs.find_one({}, {"_id": 0}, sort=[("ts", -1)])
    tasks = [t async for t in db.architecture_guardian_tasks.find(
        {"status": "open"}, {"_id": 0}).sort([("severity", 1), ("created_at", -1)]).limit(100)]
    resolved_total = await db.architecture_guardian_tasks.count_documents({"status": "resolved"})
    return {"last_run": last_run, "open_tasks": tasks, "resolved_total": resolved_total,
            "architecture_score": (last_run or {}).get("architecture_score")}


@router.post("/architecture-guardian/run")
async def arch_guardian_run(user=Depends(require_role("admin"))):
    from architecture_guardian import run_architecture_guardian
    return await run_architecture_guardian(trigger=f"manual:{user.get('email')}")


@router.post("/architecture-guardian/ignore")
async def arch_guardian_ignore(payload: dict = Body(...), user=Depends(require_role("admin"))):
    """Marchează un finding drept fals-pozitiv justificat (nu va mai genera task)."""
    key = (payload.get("key") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not key or not reason:
        raise HTTPException(400, "key și reason sunt obligatorii")
    from datetime import datetime, timezone
    await db.architecture_guardian_ignores.update_one(
        {"key": key},
        {"$set": {"reason": reason, "by": user.get("email"),
                  "ts": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    await db.architecture_guardian_tasks.update_many(
        {"key": key, "status": "open"},
        {"$set": {"status": "ignored", "resolved_at": datetime.now(timezone.utc).isoformat(),
                  "resolved_by": user.get("email"), "ignore_reason": reason}})
    return {"ignored": key}


# ============================================================================
# PRODUCT GUARDIAN — modulul de produs al Guardian Kernel (PM-GUARDIAN-003)
# ============================================================================
@router.get("/product-guardian/status")
async def product_guardian_status(user=Depends(require_role("admin"))):
    last_run = await db.product_guardian_runs.find_one({}, {"_id": 0}, sort=[("ts", -1)])
    tasks = [t async for t in db.product_guardian_tasks.find(
        {"status": "open"}, {"_id": 0}).sort([("severity", 1), ("created_at", -1)]).limit(100)]
    resolved_total = await db.product_guardian_tasks.count_documents({"status": "resolved"})
    return {"last_run": last_run, "open_tasks": tasks, "resolved_total": resolved_total,
            "product_score": (last_run or {}).get("product_score"),
            "platform_score": (last_run or {}).get("platform_score"),
            "ceo_summary": (last_run or {}).get("ceo_summary")}


@router.post("/product-guardian/run")
async def product_guardian_run(user=Depends(require_role("admin"))):
    from product_guardian import run_product_guardian
    return await run_product_guardian(trigger=f"manual:{user.get('email')}")


@router.post("/product-guardian/ignore")
async def product_guardian_ignore(payload: dict = Body(...), user=Depends(require_role("admin"))):
    key = (payload.get("key") or "").strip()
    reason = (payload.get("reason") or "").strip()
    if not key or not reason:
        raise HTTPException(400, "key și reason sunt obligatorii")
    from datetime import datetime, timezone
    await db.product_guardian_ignores.update_one(
        {"key": key},
        {"$set": {"reason": reason, "by": user.get("email"),
                  "ts": datetime.now(timezone.utc).isoformat()}}, upsert=True)
    await db.product_guardian_tasks.update_many(
        {"key": key, "status": "open"},
        {"$set": {"status": "ignored", "resolved_at": datetime.now(timezone.utc).isoformat(),
                  "resolved_by": user.get("email"), "ignore_reason": reason}})
    return {"ignored": key}
