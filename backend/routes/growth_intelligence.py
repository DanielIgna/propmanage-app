"""Growth Intelligence API — Board Decision 004/005/006 (Sprint GI-1)."""
from fastapi import APIRouter, Depends, Query

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/growth-intel", tags=["growth-intelligence"])


@router.get("/latest")
async def latest_insights(user: dict = Depends(require_role("admin"))):
    doc = await db.growth_insights.find_one({"_id": "latest"})
    if not doc:
        from growth_intelligence import run_growth_scan
        return await run_growth_scan(trigger="first_view")
    doc.pop("_id", None)
    return doc


@router.post("/run")
async def run_scan(user: dict = Depends(require_role("admin"))):
    from growth_intelligence import run_growth_scan
    return await run_growth_scan(trigger="manual")


@router.get("/behavior")
async def behavior(days: int = Query(60, ge=7, le=180), user: dict = Depends(require_role("admin"))):
    from growth_intelligence import analyze_behavior
    return await analyze_behavior(days=days)
