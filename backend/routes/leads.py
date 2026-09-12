"""Leads unificate — single view of lead (Sprint 2 · 2.1; Val 3: scoping pe tenant)."""
from fastapi import APIRouter, Depends

import leads_store
from deps import require_role
from tenancy import tenant_scope_for

router = APIRouter(prefix="/api/admin/leads", tags=["leads"])


@router.get("")
async def unified_leads(source: str = None, stage: str = None, segment: str = None, limit: int = 200,
                        tenant: str = None, user=Depends(require_role("admin", "franchise_admin"))):
    scope = tenant_scope_for(user)
    eff_tenant = scope or tenant  # franchise_admin: forțat pe tenantul lui; admin HQ: filtru opțional
    return {"leads": await leads_store.list_leads(source, stage, segment, min(limit, 500), tenant=eff_tenant),
            "sources": list(leads_store.LEGACY_SOURCES.keys()),
            "tenant": eff_tenant}


@router.get("/summary")
async def leads_summary(days: int = 30, tenant: str = None,
                        user=Depends(require_role("admin", "franchise_admin"))):
    scope = tenant_scope_for(user)
    return await leads_store.summary(days, tenant=scope or tenant)


@router.post("/migrate")
async def run_migration(_admin=Depends(require_role("admin"))):
    return {"ok": True, "migrated": await leads_store.migrate_all()}
