"""Rădăcini app (slug `radacini`) — API module.

Data lives in the shared PropManage database, using collections prefixed `radacini_`
(access them as `db.radacini_<x>` from `db`). Auth is shared with PropManage via
`deps.get_current_user`. Any reused PropManage functionality must go through
`backend/routes/radacini/bridge.py`, the single import point for PropManage code.
"""
import os

from fastapi import APIRouter, Depends, HTTPException

from . import (
    assoc_accountability, assoc_core, assoc_demo, assoc_governance,
    activities, admin, agreements, communities, contributions, crops, decisions, disputes, gdpr, harvests,
    households, legal_terms, market, members, needs, parcels, photos, projects, public, requests, service_requests, staff,
    test_accounts,
)
from .bridge import get_current_user
from .common import public_rate_limit
from .constants import META

# Oprit implicit: un merge în `main` nu expune modulul. Se pornește explicit (1/true/yes), de ex. local prin launch.json.
RADACINI_ENABLED = os.environ.get("RADACINI_ENABLED", "false").strip().lower() in ("1", "true", "yes")


async def _enabled():
    if not RADACINI_ENABLED:
        raise HTTPException(404, "Not Found")


# `public_rate_limit` acoperă doar GET /meta și GET /parcels* (vezi common.py); restul rutelor trec nemodificate.
router = APIRouter(prefix="/api/radacini", tags=["radacini"], dependencies=[Depends(_enabled), Depends(public_rate_limit)])


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
router.include_router(legal_terms.router)
router.include_router(parcels.router)
# disputes înaintea staff: /staff/disputes trebuie potrivit înaintea rutelor /staff/{…}
router.include_router(disputes.router)
router.include_router(staff.router)
router.include_router(requests.router)
router.include_router(agreements.router)
router.include_router(projects.router)
router.include_router(crops.router)
router.include_router(activities.router)
router.include_router(contributions.router)
router.include_router(harvests.router)
router.include_router(market.router)
router.include_router(test_accounts.router)
router.include_router(gdpr.router)
# Composesorate (S9): rutele fixe (/assoc/alerts/mine, /assoc/claims/mine, /assoc/meetings/…)
# se montează înaintea celor cu parametru (/assoc/{id}).
router.include_router(assoc_demo.router)
router.include_router(assoc_accountability.router)
router.include_router(assoc_governance.router)
router.include_router(assoc_core.router)
router.include_router(admin.router)
router.include_router(communities.router)
router.include_router(households.router)
router.include_router(decisions.router)
router.include_router(public.router)
router.include_router(photos.router)
router.include_router(needs.router)
router.include_router(service_requests.router)
