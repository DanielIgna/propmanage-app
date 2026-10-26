"""Rădăcini app (slug `radacini`) — API module.

Data lives in the shared PropManage database, using collections prefixed `radacini_`
(access them as `db.radacini_<x>` from `db`). Auth is shared with PropManage via
`deps.get_current_user`. Any reused PropManage functionality must go through
`backend/routes/radacini/bridge.py`, the single import point for PropManage code.
"""
import os

from fastapi import APIRouter, Depends, HTTPException, Request

from . import (
    assoc_accountability, assoc_core, assoc_demo, assoc_governance,
    activities, admin, agreements, communities, contributions, crops, decisions, disputes, gdpr, harvests,
    households, legal_terms, market, members, monitoring, needs, parcels, photos, projects, public, reports, requests, service_requests, staff,
    test_accounts,
)
from .bridge import get_current_user, is_super_admin
from .common import public_rate_limit
from .constants import META

# Oprit implicit: un merge în `main` nu expune modulul. Se pornește explicit (1/true/yes), de ex. local prin launch.json.
RADACINI_ENABLED = os.environ.get("RADACINI_ENABLED", "false").strip().lower() in ("1", "true", "yes")


# Beta închis: dacă lista e setată (emailuri separate prin virgulă), doar acele conturi (plus super-adminul
# și sesiunile de test pornite de el) folosesc modulul. Goală = acces pentru oricine are cont.
RADACINI_ALLOWED_EMAILS = {
    e.strip().lower() for e in os.environ.get("RADACINI_ALLOWED_EMAILS", "").split(",") if e.strip()
}
_BETA_OPEN_PATHS = {"/api/radacini/health", "/api/radacini/meta", "/api/radacini/legal/documents", "/api/radacini/operator"}
BETA_CLOSED_DETAIL = {"code": "beta_closed", "message": "Rădăcini e în beta închis. Accesul se face doar pe bază de invitație."}


async def _enabled(request: Request):
    if not RADACINI_ENABLED:
        raise HTTPException(404, "Not Found")
    if RADACINI_ALLOWED_EMAILS and request.url.path not in _BETA_OPEN_PATHS:
        user = await get_current_user(request)
        email = str(user.get("email") or "").strip().lower()
        if not (email in RADACINI_ALLOWED_EMAILS or is_super_admin(user) or user.get("impersonation")):
            raise HTTPException(403, BETA_CLOSED_DETAIL)


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


# Datele operatorului platformei (pagina „Despre și contact”), din variabile de mediu: nu sunt în cod,
# le completează fondatorul pe Railway. Câmpurile goale nu se afișează.
_OPERATOR_FIELDS = {
    "name": "RADACINI_OPERATOR_NAME", "legal_form": "RADACINI_OPERATOR_LEGAL_FORM", "cui": "RADACINI_OPERATOR_CUI",
    "reg_no": "RADACINI_OPERATOR_REG_NO", "address": "RADACINI_OPERATOR_ADDRESS", "email": "RADACINI_OPERATOR_EMAIL",
    "phone": "RADACINI_OPERATOR_PHONE", "dpo_email": "RADACINI_OPERATOR_DPO_EMAIL",
}


@router.get("/operator")
async def operator_info():
    data = {k: os.environ.get(v, "").strip() for k, v in _OPERATOR_FIELDS.items()}
    return {"operator": {k: v for k, v in data.items() if v}, "complete": all(data[k] for k in ("name", "address", "email"))}


router.include_router(members.router)
router.include_router(legal_terms.router)
router.include_router(parcels.router)
# disputes înaintea staff: /staff/disputes trebuie potrivit înaintea rutelor /staff/{…}
router.include_router(disputes.router)
router.include_router(reports.router)
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
router.include_router(monitoring.router)
router.include_router(admin.router)
router.include_router(communities.router)
router.include_router(households.router)
router.include_router(decisions.router)
router.include_router(public.router)
router.include_router(photos.router)
router.include_router(needs.router)
router.include_router(service_requests.router)
