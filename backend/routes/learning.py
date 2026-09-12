"""Learning Engine API — GI-4a (read-only + run). Ledger = SSoT pentru deciziile AI."""
from fastapi import APIRouter, Depends, Query

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/learning", tags=["learning-engine"])


@router.get("/stats")
async def stats(user: dict = Depends(require_role("admin"))):
    from learning_engine import learning_stats
    return await learning_stats()


@router.get("/ledger")
async def ledger(type: str = Query("", max_length=40), limit: int = Query(50, ge=1, le=200),
                 user: dict = Depends(require_role("admin"))):
    q = {"type": type} if type else {}
    docs = await db.ai_decision_ledger.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"items": docs, "count": len(docs)}


@router.post("/run")
async def run_scan(user: dict = Depends(require_role("admin"))):
    from learning_engine import run_outcome_scan
    return await run_outcome_scan(trigger="manual")
