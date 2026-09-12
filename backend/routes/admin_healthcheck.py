"""PropManage — Admin Healthcheck + Morning Briefing routes.

Probe logic lives in `healthcheck_service.py` (shared with the daily
briefing digest — see admin_briefing_digest.py). This module exposes only
the HTTP endpoints.
"""
import logging

from fastapi import APIRouter, Depends

from deps import require_role
from healthcheck_service import compute_healthcheck_report
from admin_briefing_digest import compute_briefing_payload, send_morning_briefing_email

logger = logging.getLogger("propmanage.admin_healthcheck")
router = APIRouter(prefix="/api/admin/healthcheck", tags=["admin-healthcheck"])


@router.get("/run")
async def run_healthcheck(user: dict = Depends(require_role("admin"))):
    """Run all integration probes in parallel and return a structured report."""
    report = await compute_healthcheck_report()
    logger.info(f"[Healthcheck] done · ok={report['ok']} · {report['summary']}")
    return report


# ============================================================================
# MORNING BRIEFING — admin daily digest controls
# ============================================================================


briefing_router = APIRouter(prefix="/api/admin/morning-briefing", tags=["admin-morning-briefing"])


@briefing_router.get("/preview")
async def preview_morning_briefing(user: dict = Depends(require_role("admin"))):
    """Return the JSON payload that would be rendered into the daily email.
    Useful for debugging the cron output without sending an email.
    """
    return await compute_briefing_payload()


@briefing_router.post("/send-test")
async def send_morning_briefing_test(user: dict = Depends(require_role("admin"))):
    """Force-send the morning briefing email NOW (ignoring 'all OK' skip rule).
    Used by admins to verify Resend setup & email rendering.
    """
    result = await send_morning_briefing_email(force=True)
    logger.info(f"[MorningBriefing] manual send by {user.get('email')}: {result}")
    return result
