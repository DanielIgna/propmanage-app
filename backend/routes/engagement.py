"""UX-001 · Engagement routes — compunere, zero logică proprie."""
from fastapi import APIRouter, Depends

from deps import get_current_user
from propbenefits.achievements import engagement_summary

router = APIRouter(prefix="/api/engagement", tags=["engagement"])


@router.get("/summary")
async def summary(user: dict = Depends(get_current_user)):
    return await engagement_summary(user)
