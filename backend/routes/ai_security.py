"""AI Security Center router — read-only security analytics + AI recommendations."""
import logging
from fastapi import APIRouter, Depends, Query

from deps import require_role
from ai_core.security_guardian import overview, ai_recommendations, log_ai_security_run

logger = logging.getLogger("propmanage.ai_security_route")

router = APIRouter(prefix="/api/admin/ai-security", tags=["admin-ai-security"])


@router.get("/overview")
async def sec_overview(hours: int = Query(default=24, ge=1, le=168), admin=Depends(require_role("admin"))):
    return await overview(hours=hours)


@router.post("/analyze")
async def sec_analyze(hours: int = Query(default=24, ge=1, le=168), admin=Depends(require_role("admin"))):
    """Trigger an AI analysis of the recent security window (Claude). Stores the run."""
    result = await ai_recommendations(hours=hours)
    await log_ai_security_run(result)
    return result
