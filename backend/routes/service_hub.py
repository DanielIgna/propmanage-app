"""Service Hub — pagini de servicii CMS-driven pe modelul Interior Intelligence (P1).

Generic: GET /api/services/{slug}/content (seed lazy în service_pages),
POST /api/services/{slug}/leads (→ service_leads + unified leads_store),
admin GET/PUT content. Sluguri înregistrate: design-exterior, arhitectura.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from db import db
from deps import require_role
from service_content_arhitectura import DEFAULT_CONTENT as ARHITECTURA
from service_content_exterior import DEFAULT_CONTENT as EXTERIOR

router = APIRouter(prefix="/api", tags=["service-hub"])
logger = logging.getLogger("propmanage.service_hub")

SERVICES = {"design-exterior": EXTERIOR, "arhitectura": ARHITECTURA}
_ALLOWED_KEYS = {"active", "seo", "brand", "hero", "journey", "positioning", "benefits",
                 "process_phases", "highlight", "implementation", "ecosystem", "faq",
                 "budgets", "local_cities", "seo_article"}


async def _get_content(slug: str) -> dict:
    default = SERVICES.get(slug)
    if default is None:
        raise HTTPException(404, "Serviciu necunoscut.")
    doc = await db.service_pages.find_one({"slug": slug})
    if not doc:
        seeded = {**default, "slug": slug, "tenant_id": "main",
                  "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": "seed"}
        await db.service_pages.update_one({"slug": slug}, {"$set": seeded}, upsert=True)
        return seeded
    doc.pop("_id", None)
    return doc


@router.get("/services/{slug}/content")
async def public_content(slug: str):
    content = await _get_content(slug)
    if not content.get("active", True):
        raise HTTPException(404, "Serviciul este momentan dezactivat.")
    return content


class LeadIn(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    city: str | None = None
    budget: str | None = None
    message: str | None = None


@router.post("/services/{slug}/leads")
async def create_lead(slug: str, payload: LeadIn, request: Request):
    if slug not in SERVICES:
        raise HTTPException(404, "Serviciu necunoscut.")
    from tenancy import resolve_tenant_slug
    tenant_id = await resolve_tenant_slug(request)
    lead = {
        "id": uuid.uuid4().hex, "service": slug,
        "name": payload.name.strip()[:120], "email": payload.email.lower(),
        "phone": (payload.phone or "").strip()[:30], "city": (payload.city or "")[:60],
        "budget": (payload.budget or "")[:60], "message": (payload.message or "")[:2000],
        "status": "new", "tenant_id": tenant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.service_leads.insert_one(dict(lead))
    try:
        from leads_store import sync_lead
        await sync_lead(slug.replace("-", "_"), lead)
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "lead_id": lead["id"], "message": "Mulțumim! Te contactăm în 24-48h."}


@router.get("/admin/services/{slug}/content")
async def admin_get_content(slug: str, _admin=Depends(require_role("admin"))):
    return await _get_content(slug)


@router.put("/admin/services/{slug}/content")
async def admin_put_content(slug: str, patch: dict = Body(...), admin=Depends(require_role("admin"))):
    if slug not in SERVICES:
        raise HTTPException(404, "Serviciu necunoscut.")
    clean = {k: v for k, v in patch.items() if k in _ALLOWED_KEYS}
    if not clean:
        raise HTTPException(400, "Nicio cheie validă de actualizat.")
    await _get_content(slug)  # asigură seed
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    clean["updated_by"] = admin.get("email")
    await db.service_pages.update_one({"slug": slug}, {"$set": clean})
    return await _get_content(slug)


@router.get("/admin/services/{slug}/leads")
async def admin_leads(slug: str, limit: int = 100, _admin=Depends(require_role("admin"))):
    items = await db.service_leads.find({"service": slug}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 500))
    return {"items": items, "total": len(items)}
