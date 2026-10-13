"""Rădăcini app (slug `radacini`) — API module.

Data lives in the shared PropManage database, using collections prefixed `radacini_`
(access them as `db.radacini_<x>` from `db`). Auth is shared with PropManage via
`deps.get_current_user`. Any reused PropManage functionality must go through
`backend/routes/radacini/bridge.py`, the single import point for PropManage code.
"""
import os

from fastapi import APIRouter, Depends, HTTPException

from . import agreements, members, parcels, requests, staff
from .bridge import get_current_user
from .constants import META

RADACINI_ENABLED = os.environ.get("RADACINI_ENABLED", "true").lower() in ("1", "true", "yes")


async def _enabled():
    if not RADACINI_ENABLED:
        raise HTTPException(404, "Not Found")


router = APIRouter(prefix="/api/radacini", tags=["radacini"], dependencies=[Depends(_enabled)])


@router.get("/health")
async def health():
    return {"ok": True, "app": "radacini"}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role"),
    }


@router.get("/meta")
async def meta():
    return META


router.include_router(members.router)
router.include_router(parcels.router)
router.include_router(staff.router)
router.include_router(requests.router)
router.include_router(agreements.router)
