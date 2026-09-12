"""Rute admin — follow-up automat specialist_entry (Faza 3)."""
from fastapi import APIRouter, Body, Depends

from db import db
from deps import require_role
from specialist_followup import (
    get_config, update_config,
    run_reminder_scan, run_nurture_scan,
)

router = APIRouter(prefix="/api/admin/specialist-followup", tags=["specialist-followup"])


@router.get("/config")
async def specialist_followup_config(_admin=Depends(require_role("admin"))):
    return await get_config()


@router.put("/config")
async def specialist_followup_config_update(patch: dict = Body(...),
                                            admin=Depends(require_role("admin"))):
    return await update_config(patch, who=admin.get("email"))


@router.post("/run")
async def specialist_followup_run(dry_run: bool = True, sequence: str = "reminder_1h",
                                  _admin=Depends(require_role("admin"))):
    """Rulare manuală. Default dry_run=true. sequence: reminder_1h | nurture_24h."""
    if sequence == "nurture_24h":
        return await run_nurture_scan(manual=True, dry_run=dry_run)
    return await run_reminder_scan(manual=True, dry_run=dry_run)


@router.get("/log")
async def specialist_followup_log(limit: int = 50, _admin=Depends(require_role("admin"))):
    items = await db.specialist_followup_log.find({}, {"_id": 0}).sort("at", -1).to_list(min(limit, 200))
    return {"items": items, "total": len(items)}
