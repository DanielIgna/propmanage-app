"""ASM-001 · Copilotul Casei — endpoints (compunere, zero logică proprie)."""
from fastapi import APIRouter, Depends

from deps import get_current_user
from propbenefits.copilot import copilot_dashboard, timeline

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    return await copilot_dashboard(user)


@router.get("/timeline")
async def my_timeline(user: dict = Depends(get_current_user)):
    return await timeline(user["id"], limit=20)
