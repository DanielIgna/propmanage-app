"""Rute admin — follow-up automat lead-uri warm (P2)."""
from fastapi import APIRouter, Body, Depends

from db import db
from deps import require_role
from lead_followup import get_config, get_status, run_autonomous_cycle, run_followup_scan, run_nurture_scan, update_config

router = APIRouter(prefix="/api/admin/leads/followup", tags=["lead-followup"])


@router.get("/config")
async def followup_config(_admin=Depends(require_role("admin"))):
    return await get_config()


@router.put("/config")
async def followup_config_update(patch: dict = Body(...), admin=Depends(require_role("admin"))):
    return await update_config(patch, who=admin.get("email"))


@router.post("/run")
async def followup_run(dry_run: bool = True, sequence: str = "warm_48h", _admin=Depends(require_role("admin"))):
    """Rulare manuală. Default dry_run=true. sequence: warm_48h | nurture_7d."""
    if sequence == "nurture_7d":
        return await run_nurture_scan(manual=True, dry_run=dry_run)
    return await run_followup_scan(manual=True, dry_run=dry_run)


@router.get("/status")
async def followup_status(_admin=Depends(require_role("admin"))):
    """Stare autonomie L2: config, email gate, candidați, istoricul ciclurilor."""
    return await get_status()


@router.post("/run-cycle")
async def followup_run_cycle(_admin=Depends(require_role("admin"))):
    """Rulează manual ciclul autonom complet (același cod ca scheduler-ul orar)."""
    return await run_autonomous_cycle(trigger="manual")


@router.get("/log")
async def followup_log(limit: int = 50, _admin=Depends(require_role("admin"))):
    items = await db.lead_followup_log.find({}, {"_id": 0}).sort("at", -1).to_list(min(limit, 200))
    return {"items": items, "total": len(items)}
