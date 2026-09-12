"""Marketplace Partners Ecosystem — backend.

Platforma este intermediar (NU comercializează direct). Generează lead-uri și
facilitează conectarea client-final ↔ partener marketplace (magazine, depozite,
fabrici, distribuitori, producători, showroom-uri, furnizori servicii).

Endpoints (admin):
  POST/GET/PATCH/DELETE  /api/admin/marketplace-partners                       CRUD
  POST                   /api/admin/marketplace-partners/{id}/commissions      set commission config
  POST                   /api/admin/marketplace-partners/{id}/policies         set discounts/promos
  POST                   /api/admin/marketplace-partners/{id}/create-login     issue creds
  POST                   /api/admin/marketplace-partners/{id}/presentation     generate AI pitch
  GET/POST/PATCH         /api/admin/marketplace-partners/{id}/leads
  GET                    /api/admin/marketplace-partners/stats
  POST                   /api/admin/marketplace-partners/copilot/analyze       AI Marketplace Copilot

Endpoints (partner self-service, role=marketplace_partner):
  GET  /api/marketplace-partner/me
  GET  /api/marketplace-partner/leads
  POST /api/marketplace-partner/leads
  GET  /api/marketplace-partner/stats

Collections:
  marketplace_partners       { company, cui, city, county, contact_name,
                               contact_email, contact_phone, website,
                               categories[], zones[], tier, status,
                               commissions{}, policies{}, package,
                               linked_user_id, notes }
  marketplace_leads          { partner_id, lead_name, lead_email, lead_phone,
                               product_category, stage, estimated_value,
                               revenue_generated, source, notes }
  marketplace_presentations  { partner_id, generated_at, payload }
  marketplace_nudges         { partner_id, generated_at, nudges }
"""
import logging
import os
import secrets
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import bcrypt

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.marketplace_partners")

admin_router = APIRouter(prefix="/api/admin/marketplace-partners", tags=["admin-marketplace-partners"])
partner_router = APIRouter(prefix="/api/marketplace-partner", tags=["marketplace-partner-portal"])

ALLOWED_STATUS = {"prospect", "onboarding", "active", "paused", "terminated"}
ALLOWED_TIERS = {"basic", "verified", "premium", "strategic", "exclusive"}
ALLOWED_PACKAGES = {"starter", "business", "premium", "enterprise"}
ALLOWED_LEAD_STAGES = {"new", "qualified", "contacted", "converted", "lost"}

CATEGORIES = [
    "Gresie și faianță", "Uși interior/exterior", "Sanitare", "Mobilier",
    "Vopsele și lavabile", "Instalații termice", "Instalații electrice", "HVAC",
    "Smart home", "Tâmplărie", "Acoperișuri", "Mobilier personalizat",
    "Electrocasnice", "Sisteme fotovoltaice", "Pompe de căldură",
    "Sisteme de securitate", "Materiale construcții", "Showroom", "Distribuitor",
    "Producător", "Depozit", "Fabrică", "Furnizor servicii",
]


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin poate gestiona Marketplace Partners.")


def _serialize(d: dict) -> dict:
    if not d:
        return d
    return {
        "id": str(d.get("_id")),
        "company": d.get("company"),
        "cui": d.get("cui"),
        "city": d.get("city"),
        "county": d.get("county"),
        "contact_name": d.get("contact_name"),
        "contact_email": d.get("contact_email"),
        "contact_phone": d.get("contact_phone"),
        "website": d.get("website"),
        "categories": d.get("categories") or [],
        "zones": d.get("zones") or [],
        "tier": d.get("tier") or "basic",
        "status": d.get("status") or "prospect",
        "package": d.get("package"),
        "commissions": d.get("commissions") or {},
        "policies": d.get("policies") or {},
        "linked_user_id": str(d.get("linked_user_id")) if d.get("linked_user_id") else None,
        "notes": d.get("notes"),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


def _serialize_lead(d: dict) -> dict:
    if not d:
        return d
    return {
        "id": str(d.get("_id")),
        "partner_id": str(d.get("partner_id")) if d.get("partner_id") else None,
        "lead_name": d.get("lead_name"),
        "lead_email": d.get("lead_email"),
        "lead_phone": d.get("lead_phone"),
        "product_category": d.get("product_category"),
        "stage": d.get("stage") or "new",
        "estimated_value": d.get("estimated_value") or 0,
        "revenue_generated": d.get("revenue_generated") or 0,
        "source": d.get("source"),
        "notes": d.get("notes"),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


# ─── Pydantic ─────────────────────────────────────────────────────────────
class PartnerCreate(BaseModel):
    company: str = Field(min_length=2, max_length=200)
    cui: Optional[str] = None
    contact_name: str = Field(min_length=2, max_length=120)
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    city: str = Field(min_length=2, max_length=80)
    county: Optional[str] = None
    categories: List[str] = []
    zones: List[str] = []
    tier: str = "basic"
    status: str = "prospect"
    package: Optional[str] = None
    notes: Optional[str] = None


class PartnerPatch(BaseModel):
    company: Optional[str] = None
    cui: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    categories: Optional[List[str]] = None
    zones: Optional[List[str]] = None
    tier: Optional[str] = None
    status: Optional[str] = None
    package: Optional[str] = None
    notes: Optional[str] = None


class CommissionsConfig(BaseModel):
    type: Optional[str] = None  # percent | fixed | per_lead | per_sale | subscription
    percent: Optional[float] = None
    fixed_amount: Optional[float] = None
    per_lead: Optional[float] = None
    per_sale: Optional[float] = None
    monthly_subscription: Optional[float] = None
    onboarding_fee: Optional[float] = None
    promotion_fee: Optional[float] = None
    admin_fee: Optional[float] = None
    notes: Optional[str] = None


class PoliciesConfig(BaseModel):
    client_discount_pct: Optional[float] = None
    specialist_discount_pct: Optional[float] = None
    promotions: Optional[List[str]] = None
    seasonal_campaigns: Optional[List[str]] = None
    coupons: Optional[List[str]] = None
    bonuses: Optional[List[str]] = None


class LeadCreate(BaseModel):
    lead_name: str = Field(min_length=2, max_length=200)
    lead_email: Optional[EmailStr] = None
    lead_phone: Optional[str] = None
    product_category: Optional[str] = None
    stage: str = "new"
    estimated_value: Optional[float] = 0
    source: Optional[str] = None
    notes: Optional[str] = None


class LeadPatch(BaseModel):
    stage: Optional[str] = None
    estimated_value: Optional[float] = None
    revenue_generated: Optional[float] = None
    notes: Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN — CRUD + stats
# ═════════════════════════════════════════════════════════════════════════════
@admin_router.get("")
async def list_partners(
    status: Optional[str] = None,
    tier: Optional[str] = None,
    category: Optional[str] = None,
    user=Depends(get_current_user),
):
    _require_super(user)
    q = {}
    if status and status != "all":
        q["status"] = status
    if tier and tier != "all":
        q["tier"] = tier
    if category:
        q["categories"] = category
    cur = db.marketplace_partners.find(q).sort("created_at", -1)
    items = [_serialize(d) async for d in cur]
    return {"items": items, "count": len(items)}


@admin_router.post("")
async def create_partner(payload: PartnerCreate, user=Depends(get_current_user)):
    _require_super(user)
    if payload.status not in ALLOWED_STATUS:
        raise HTTPException(400, f"status invalid; permis: {sorted(ALLOWED_STATUS)}")
    if payload.tier not in ALLOWED_TIERS:
        raise HTTPException(400, f"tier invalid; permis: {sorted(ALLOWED_TIERS)}")
    if payload.package and payload.package not in ALLOWED_PACKAGES:
        raise HTTPException(400, f"package invalid; permis: {sorted(ALLOWED_PACKAGES)}")
    existing = await db.marketplace_partners.find_one({"contact_email": payload.contact_email.lower()})
    if existing:
        raise HTTPException(409, f"Există deja partener cu emailul {payload.contact_email}.")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        **payload.dict(),
        "contact_email": payload.contact_email.lower(),
        "commissions": {},
        "policies": {},
        "linked_user_id": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.marketplace_partners.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize(doc)


@admin_router.get("/stats")
async def global_stats(user=Depends(get_current_user)):
    _require_super(user)
    total = await db.marketplace_partners.count_documents({})
    by_status = {s: await db.marketplace_partners.count_documents({"status": s}) for s in ALLOWED_STATUS}
    by_tier = {t: await db.marketplace_partners.count_documents({"tier": t}) for t in ALLOWED_TIERS}
    total_leads = await db.marketplace_leads.count_documents({})
    leads_by_stage = {st: await db.marketplace_leads.count_documents({"stage": st}) for st in ALLOWED_LEAD_STAGES}
    rev_pipe = [{"$group": {"_id": None, "total": {"$sum": "$revenue_generated"}}}]
    revenue = 0
    async for r in db.marketplace_leads.aggregate(rev_pipe):
        revenue = r.get("total") or 0
    # top categories from partners
    cat_counts = {}
    async for p in db.marketplace_partners.find({"status": {"$ne": "terminated"}}):
        for c in p.get("categories") or []:
            cat_counts[c] = cat_counts.get(c, 0) + 1
    top_categories = sorted(cat_counts.items(), key=lambda x: -x[1])[:8]
    return {
        "total_partners": total,
        "by_status": by_status,
        "by_tier": by_tier,
        "total_leads": total_leads,
        "leads_by_stage": leads_by_stage,
        "total_revenue": revenue,
        "top_categories": [{"name": k, "count": v} for k, v in top_categories],
        "available_categories": CATEGORIES,
        "tiers": sorted(ALLOWED_TIERS),
        "packages": sorted(ALLOWED_PACKAGES),
    }


@admin_router.get("/{partner_id}")
async def get_partner(partner_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    doc = await db.marketplace_partners.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Partener inexistent.")
    return _serialize(doc)


@admin_router.patch("/{partner_id}")
async def patch_partner(partner_id: str, payload: PartnerPatch, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    update = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "status" in update and update["status"] not in ALLOWED_STATUS:
        raise HTTPException(400, "status invalid")
    if "tier" in update and update["tier"] not in ALLOWED_TIERS:
        raise HTTPException(400, "tier invalid")
    if "package" in update and update["package"] not in ALLOWED_PACKAGES:
        raise HTTPException(400, "package invalid")
    if "contact_email" in update:
        update["contact_email"] = str(update["contact_email"]).lower()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.marketplace_partners.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(404, "Partener inexistent.")
    return _serialize(res)


@admin_router.delete("/{partner_id}")
async def archive_partner(partner_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    res = await db.marketplace_partners.update_one(
        {"_id": oid},
        {"$set": {"status": "terminated", "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Partener inexistent.")
    return {"ok": True, "archived": True}


@admin_router.post("/{partner_id}/commissions")
async def set_commissions(partner_id: str, payload: CommissionsConfig, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    cfg = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    res = await db.marketplace_partners.find_one_and_update(
        {"_id": oid},
        {"$set": {"commissions": cfg, "updated_at": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(404, "Partener inexistent.")
    return _serialize(res)


@admin_router.post("/{partner_id}/policies")
async def set_policies(partner_id: str, payload: PoliciesConfig, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    cfg = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    res = await db.marketplace_partners.find_one_and_update(
        {"_id": oid},
        {"$set": {"policies": cfg, "updated_at": datetime.now(timezone.utc).isoformat()}},
        return_document=True,
    )
    if not res:
        raise HTTPException(404, "Partener inexistent.")
    return _serialize(res)


@admin_router.post("/{partner_id}/create-login")
async def create_partner_login(partner_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    p = await db.marketplace_partners.find_one({"_id": oid})
    if not p:
        raise HTTPException(404, "Partener inexistent.")
    email = (p.get("contact_email") or "").lower()
    if p.get("linked_user_id"):
        try:
            existing_oid = p["linked_user_id"] if isinstance(p["linked_user_id"], ObjectId) else ObjectId(str(p["linked_user_id"]))
            existing_user = await db.users.find_one({"_id": existing_oid})
        except Exception:
            existing_user = None
        if existing_user:
            return {"ok": True, "already_exists": True, "user_id": str(existing_user["_id"]), "email": existing_user["email"]}
    existing = await db.users.find_one({"email": email})
    if existing:
        await db.marketplace_partners.update_one(
            {"_id": oid},
            {"$set": {"linked_user_id": str(existing["_id"]), "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "linked_existing": True, "user_id": str(existing["_id"]), "email": email}
    temp_password = secrets.token_urlsafe(12).replace("_", "X").replace("-", "Y")[:14] + "!1M"
    new_user = {
        "email": email,
        "password_hash": bcrypt.hash(temp_password),
        "name": p.get("contact_name") or p.get("company"),
        "role": "marketplace_partner",
        "phone": p.get("contact_phone"),
        "verified_email": True,
        "terms_accepted": True,
        "privacy_policy_accepted": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "marketplace_partner_id": str(p["_id"]),
    }
    ures = await db.users.insert_one(new_user)
    await db.marketplace_partners.update_one(
        {"_id": oid},
        {"$set": {"linked_user_id": str(ures.inserted_id), "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "created": True, "user_id": str(ures.inserted_id), "email": email, "temp_password": temp_password}


# ─── Leads (admin) ────────────────────────────────────────────────────────
@admin_router.get("/{partner_id}/leads")
async def list_leads(partner_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    cur = db.marketplace_leads.find({"partner_id": oid}).sort("created_at", -1)
    items = [_serialize_lead(d) async for d in cur]
    return {"items": items, "count": len(items)}


@admin_router.post("/{partner_id}/leads")
async def create_lead(partner_id: str, payload: LeadCreate, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    p = await db.marketplace_partners.find_one({"_id": oid})
    if not p:
        raise HTTPException(404, "Partener inexistent.")
    if payload.stage not in ALLOWED_LEAD_STAGES:
        raise HTTPException(400, "stage invalid")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "partner_id": oid,
        "lead_name": payload.lead_name,
        "lead_email": (str(payload.lead_email).lower() if payload.lead_email else None),
        "lead_phone": payload.lead_phone,
        "product_category": payload.product_category,
        "stage": payload.stage,
        "estimated_value": payload.estimated_value or 0,
        "revenue_generated": 0,
        "source": payload.source or "admin",
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.marketplace_leads.insert_one(doc)
    doc["_id"] = res.inserted_id
    from leads_store import sync_lead
    await sync_lead("marketplace_partner", doc)
    return _serialize_lead(doc)


@admin_router.patch("/leads/{lead_id}")
async def patch_lead(lead_id: str, payload: LeadPatch, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    update = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "stage" in update and update["stage"] not in ALLOWED_LEAD_STAGES:
        raise HTTPException(400, "stage invalid")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.marketplace_leads.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(404, "Lead inexistent.")
    from leads_store import sync_lead
    await sync_lead("marketplace_partner", res)
    return _serialize_lead(res)


# ═════════════════════════════════════════════════════════════════════════════
# AI COPILOT + Business Presentation Engine
# ═════════════════════════════════════════════════════════════════════════════
async def _claude_json(system: str, prompt: str, session_prefix: str) -> dict:
    """Helper: call Claude Sonnet 4.5 and parse JSON response."""
    import json
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=key,
        session_id=f"{session_prefix}_{_uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    raw = await chat.send_message(UserMessage(text=prompt))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise HTTPException(502, "AI nu a returnat JSON valid.")
    return json.loads(text[i:j + 1])


@admin_router.post("/copilot/analyze")
async def marketplace_copilot_analyze(user=Depends(get_current_user)):
    """AI Marketplace Copilot — analizează parteneri activi, identifică oportunități."""
    _require_super(user)
    partners = []
    async for p in db.marketplace_partners.find({"status": {"$ne": "terminated"}}).limit(50):
        cnt = await db.marketplace_leads.count_documents({"partner_id": p["_id"]})
        conv = await db.marketplace_leads.count_documents({"partner_id": p["_id"], "stage": "converted"})
        partners.append({
            "company": p.get("company"),
            "city": p.get("city"),
            "tier": p.get("tier"),
            "status": p.get("status"),
            "categories": p.get("categories") or [],
            "leads_total": cnt,
            "leads_converted": conv,
        })
    if not partners:
        raise HTTPException(404, "Nu există parteneri activi de analizat.")
    import json
    system = (
        "Ești un Marketplace Strategy Advisor pentru PropManage (proptech RO). "
        "Analizezi parteneri marketplace (magazine, depozite, fabrici, distribuitori). "
        "Răspunzi DOAR cu JSON valid în limba română: "
        "{summary, hot_categories:[{name, reason}], "
        "top_converters:[{company, reason}], underperformers:[{company, action}], "
        "pricing_recommendations:[str], commercial_opportunities:[str], "
        "growth_score(0-100)}."
    )
    report = await _claude_json(system, "Date parteneri marketplace:\n" + json.dumps(partners, ensure_ascii=False, indent=2), "mkt_copilot")
    out = {
        "summary": str(report.get("summary") or "")[:1500],
        "hot_categories": (report.get("hot_categories") or [])[:8],
        "top_converters": (report.get("top_converters") or [])[:6],
        "underperformers": (report.get("underperformers") or [])[:6],
        "pricing_recommendations": (report.get("pricing_recommendations") or [])[:8],
        "commercial_opportunities": (report.get("commercial_opportunities") or [])[:8],
        "growth_score": int(report.get("growth_score") or 0),
        "analyzed_count": len(partners),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.marketplace_copilot_reports.insert_one({**out, "generated_by": user.get("email")})
    return out


@admin_router.post("/{partner_id}/presentation")
async def generate_presentation(partner_id: str, user=Depends(get_current_user)):
    """Business Integration Presentation Engine — AI-generated personalized pitch."""
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    p = await db.marketplace_partners.find_one({"_id": oid})
    if not p:
        raise HTTPException(404, "Partener inexistent.")

    # Ecosystem context (aggregate basic stats)
    total_clients = await db.users.count_documents({"role": "client"})
    total_specialists = await db.users.count_documents({"role": "specialist"})
    total_partners = await db.marketplace_partners.count_documents({"status": "active"})

    ctx = {
        "partner": {
            "company": p.get("company"),
            "city": p.get("city"),
            "categories": p.get("categories") or [],
            "tier": p.get("tier"),
            "website": p.get("website"),
        },
        "ecosystem": {
            "total_clients": total_clients,
            "total_specialists": total_specialists,
            "total_marketplace_partners": total_partners,
        },
    }
    import json
    system = (
        "Ești un B2B Sales Strategist pentru PropManage. Generezi o PREZENTARE personalizată "
        "pentru un partener marketplace potențial (magazin/fabrică/distribuitor). "
        "Răspunzi DOAR cu JSON valid în limba română cu schema: "
        "{slides: [{title (max 80c), bullets:[max 4 strings, max 140c fiecare]}], "
        "key_takeaway, estimated_opportunity_text}. "
        "Slide-uri obligatorii: 1) Prezentarea platformei, 2) Dimensiunea ecosistemului, "
        "3) Tipurile de clienți, 4) Modul de integrare al partenerului, 5) Beneficiile colaborării, "
        "6) Estimarea oportunităților comerciale, 7) Canalele de promovare disponibile, "
        "8) Scenarii de monetizare, 9) Avantajele competitive. "
        "Personalizează concret pe categoria și locația partenerului."
    )
    report = await _claude_json(system, json.dumps(ctx, ensure_ascii=False, indent=2), "mkt_pitch")
    out = {
        "partner_id": str(p["_id"]),
        "partner_company": p.get("company"),
        "slides": (report.get("slides") or [])[:12],
        "key_takeaway": str(report.get("key_takeaway") or "")[:500],
        "estimated_opportunity_text": str(report.get("estimated_opportunity_text") or "")[:500],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.get("email"),
    }
    await db.marketplace_presentations.insert_one({**out})
    return out


# ═════════════════════════════════════════════════════════════════════════════
# PARTNER PORTAL (role=marketplace_partner)
# ═════════════════════════════════════════════════════════════════════════════
async def _require_marketplace_partner(user: dict) -> dict:
    if user.get("role") != "marketplace_partner":
        raise HTTPException(403, "Acces restricționat la partenerii marketplace.")
    pid = user.get("marketplace_partner_id")
    if not pid:
        raise HTTPException(404, "Cont nelegat de niciun partener.")
    try:
        pid_obj = pid if isinstance(pid, ObjectId) else ObjectId(str(pid))
    except Exception:
        raise HTTPException(404, "partner_id invalid.")
    p = await db.marketplace_partners.find_one({"_id": pid_obj})
    if not p:
        raise HTTPException(404, "Partener inexistent.")
    if p.get("status") == "terminated":
        raise HTTPException(403, "Colaborarea a fost încheiată.")
    return p


@partner_router.get("/me")
async def my_partner(user=Depends(get_current_user)):
    p = await _require_marketplace_partner(user)
    return {"partner": _serialize(p), "user": {"name": user.get("name"), "email": user.get("email")}}


@partner_router.get("/leads")
async def my_leads(user=Depends(get_current_user)):
    p = await _require_marketplace_partner(user)
    cur = db.marketplace_leads.find({"partner_id": p["_id"]}).sort("created_at", -1)
    items = [_serialize_lead(d) async for d in cur]
    return {"items": items, "count": len(items)}


@partner_router.post("/leads")
async def add_my_lead(payload: LeadCreate, user=Depends(get_current_user)):
    p = await _require_marketplace_partner(user)
    if payload.stage not in ALLOWED_LEAD_STAGES:
        raise HTTPException(400, "stage invalid")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "partner_id": p["_id"],
        "lead_name": payload.lead_name,
        "lead_email": (str(payload.lead_email).lower() if payload.lead_email else None),
        "lead_phone": payload.lead_phone,
        "product_category": payload.product_category,
        "stage": payload.stage,
        "estimated_value": payload.estimated_value or 0,
        "revenue_generated": 0,
        "source": payload.source or "marketplace_portal",
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.marketplace_leads.insert_one(doc)
    doc["_id"] = res.inserted_id
    from leads_store import sync_lead
    await sync_lead("marketplace_partner", doc)
    return _serialize_lead(doc)


@partner_router.get("/stats")
async def my_stats(user=Depends(get_current_user)):
    p = await _require_marketplace_partner(user)
    pid = p["_id"]
    total = await db.marketplace_leads.count_documents({"partner_id": pid})
    by_stage = {st: await db.marketplace_leads.count_documents({"partner_id": pid, "stage": st}) for st in ALLOWED_LEAD_STAGES}
    rev = 0
    async for r in db.marketplace_leads.aggregate([
        {"$match": {"partner_id": pid}},
        {"$group": {"_id": None, "total": {"$sum": "$revenue_generated"}}},
    ]):
        rev = r.get("total") or 0
    conv_rate = round((by_stage.get("converted", 0) / total * 100), 1) if total else 0
    return {
        "partner": {
            "company": p.get("company"),
            "tier": p.get("tier"),
            "status": p.get("status"),
            "categories": p.get("categories") or [],
            "package": p.get("package"),
        },
        "leads_total": total,
        "leads_by_stage": by_stage,
        "revenue_generated": rev,
        "conversion_rate": conv_rate,
    }
