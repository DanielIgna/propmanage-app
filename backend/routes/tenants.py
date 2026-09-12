"""Rute tenants — registru francize (Sprint 3 · Tenant Foundation)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from tenancy import DEFAULT_TENANT, SLUG_RE, coverage_report, resolve_tenant_slug

router = APIRouter(prefix="/api/admin/tenants", tags=["tenants"])
public_router = APIRouter(prefix="/api/public", tags=["tenants"])

VALID_STATUS = {"draft", "active", "suspended"}


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=120)
    domain: str | None = None
    regions: list[str] = []


class TenantPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    domain: str | None = None
    regions: list[str] | None = None
    branding: dict | None = None


@router.get("")
async def list_tenants(user: dict = Depends(require_role("admin"))):
    items = await db.tenants.find({}, {"_id": 0}).sort("created_at", 1).to_list(100)
    return {"items": items, "total": len(items)}


@router.post("", status_code=201)
async def create_tenant(body: TenantCreate, user: dict = Depends(require_role("admin"))):
    slug = body.slug.strip().lower()
    if not SLUG_RE.match(slug):
        raise HTTPException(400, "Slug invalid: doar litere mici, cifre și cratimă (2-32 caractere)")
    if await db.tenants.find_one({"slug": slug}):
        raise HTTPException(409, f"Tenantul '{slug}' există deja")
    now = datetime.now(timezone.utc).isoformat()
    doc = {"slug": slug, "name": body.name.strip(), "plan": "franchise",
           "status": "draft", "domain": body.domain, "regions": body.regions,
           "branding": {}, "created_at": now, "updated_at": now,
           "created_by": str(user.get("id") or user.get("email"))}
    await db.tenants.insert_one(dict(doc))
    return doc


@router.patch("/{slug}")
async def patch_tenant(slug: str, body: TenantPatch, user: dict = Depends(require_role("admin"))):
    existing = await db.tenants.find_one({"slug": slug})
    if not existing:
        raise HTTPException(404, "Tenant inexistent")
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if "status" in updates:
        if updates["status"] not in VALID_STATUS:
            raise HTTPException(400, f"Status invalid — permise: {sorted(VALID_STATUS)}")
        if slug == DEFAULT_TENANT and updates["status"] != "active":
            raise HTTPException(400, "Tenantul HQ 'main' nu poate fi dezactivat")
    if not updates:
        raise HTTPException(400, "Nimic de actualizat")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.tenants.update_one({"slug": slug}, {"$set": updates})
    return await db.tenants.find_one({"slug": slug}, {"_id": 0})


@router.get("/coverage")
async def tenant_coverage(user: dict = Depends(require_role("admin"))):
    """Raport de guvernanță: acoperirea tenant_id pe colecții (T1/T2/T3)."""
    return await coverage_report()


@router.post("/backfill")
async def tenant_backfill(force: bool = False, user: dict = Depends(require_role("admin"))):
    """Val 2: re-rulează backfill-ul tenant_id='main' pe colecțiile T1 (idempotent)."""
    from tenancy import backfill_tier1_tenant_data
    return await backfill_tier1_tenant_data(force=force)


# ── Val 3: administratori de franciză ────────────────────────────────────────
class FranchiseAdminIn(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=2, max_length=120)


@router.get("/{slug}/admins")
async def list_franchise_admins(slug: str, user: dict = Depends(require_role("admin"))):
    if not await db.tenants.find_one({"slug": slug}):
        raise HTTPException(404, "Tenant inexistent")
    items = await db.users.find({"role": "franchise_admin", "tenant_id": slug},
                                {"_id": 0, "email": 1, "name": 1, "created_at": 1}).to_list(50)
    return {"items": items, "total": len(items)}


@router.post("/{slug}/admins", status_code=201)
async def create_franchise_admin(slug: str, body: FranchiseAdminIn, user: dict = Depends(require_role("admin"))):
    tenant = await db.tenants.find_one({"slug": slug})
    if not tenant:
        raise HTTPException(404, "Tenant inexistent")
    if slug == DEFAULT_TENANT:
        raise HTTPException(400, "HQ 'main' folosește rolul admin, nu franchise_admin")
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Email invalid")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Există deja un utilizator cu acest email")
    from core_utils import hash_password
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({
        "email": email, "password_hash": hash_password(body.password), "name": body.name.strip(),
        "role": "franchise_admin", "tenant_id": slug, "verified": True, "email_verified": True,
        "terms_accepted": True, "privacy_policy_accepted": True, "created_at": now,
        "created_by": str(user.get("email")),
    })
    return {"ok": True, "email": email, "role": "franchise_admin", "tenant_id": slug}


@public_router.get("/tenant-context")
async def tenant_context(request: Request):
    """Tenantul rezolvat pentru requestul curent (consumat de frontend în val 2)."""
    slug = await resolve_tenant_slug(request)
    t = await db.tenants.find_one({"slug": slug}, {"_id": 0, "slug": 1, "name": 1, "branding": 1, "status": 1})
    return {"tenant_id": slug, "tenant": t}
