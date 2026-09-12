"""Strategic City Partnership Program — backend.

V1 (current): non-exclusive collaboration framework. Partner brings clients.
Future enhancements (marketplace, specialist commissions) require addendums.

Endpoints (Admin / super-admin):
  POST   /api/admin/city-partners              create partner
  GET    /api/admin/city-partners              list partners
  GET    /api/admin/city-partners/{id}         partner detail
  PATCH  /api/admin/city-partners/{id}         update fields
  DELETE /api/admin/city-partners/{id}         soft-archive
  POST   /api/admin/city-partners/{id}/onboarding-step  update step 1-7
  POST   /api/admin/city-partners/{id}/create-login     issue partner credentials
  GET    /api/admin/city-partners/{id}/leads
  POST   /api/admin/city-partners/{id}/leads
  PATCH  /api/admin/city-partners/leads/{lead_id}
  GET    /api/admin/city-partners/stats        global stats

Endpoints (partner self-service, role=city_partner):
  GET  /api/partner/me                         my partner record
  GET  /api/partner/leads                      only my leads
  POST /api/partner/leads                      add a referral
  GET  /api/partner/stats                      my dashboard stats

Collections:
  city_partners      { _id, company, contact_name, contact_email, contact_phone,
                       city, county, units_managed, growth_rate, portfolio_type,
                       started_at, status (lead|onboarding|active|paused|terminated),
                       onboarding_step (0-7), onboarding_complete, territory_protected,
                       linked_user_id, notes, created_at, updated_at }

  city_partner_leads { _id, partner_id, lead_name, lead_email, lead_phone,
                       source, introduced_at, stage (introduced|contacted|onboarded|converted|lost),
                       conversion_date, revenue_generated, notes, created_at, updated_at }
"""
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from passlib.hash import bcrypt

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.city_partners")

admin_router = APIRouter(prefix="/api/admin/city-partners", tags=["admin-city-partners"])
partner_router = APIRouter(prefix="/api/partner", tags=["city-partner-portal"])
products_admin_router = APIRouter(prefix="/api/admin/city-partner-products", tags=["admin-city-partner-products"])

ALLOWED_STATUS = {"lead", "onboarding", "active", "paused", "terminated"}
ALLOWED_LEAD_STAGES = {"introduced", "contacted", "onboarded", "converted", "lost"}

ONBOARDING_STEPS = [
    "Prezentare oficială",
    "Introducere în ecosistem",
    "Prezentare pe grupurile disponibile",
    "Invitație către administratori",
    "Creare conturi platformă",
    "Urmărire social media",
    "Activare campanii locale",
]


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin poate gestiona City Partners.")


def _serialize(doc: dict) -> dict:
    if not doc:
        return doc
    return {
        "id": str(doc.get("_id")),
        "company": doc.get("company"),
        "contact_name": doc.get("contact_name"),
        "contact_email": doc.get("contact_email"),
        "contact_phone": doc.get("contact_phone"),
        "city": doc.get("city"),
        "county": doc.get("county"),
        "units_managed": doc.get("units_managed") or 0,
        "growth_rate": doc.get("growth_rate"),
        "portfolio_type": doc.get("portfolio_type"),
        "started_at": doc.get("started_at"),
        "status": doc.get("status") or "lead",
        "onboarding_step": doc.get("onboarding_step") or 0,
        "onboarding_complete": bool(doc.get("onboarding_complete")),
        "territory_protected": bool(doc.get("territory_protected")),
        "linked_user_id": str(doc.get("linked_user_id")) if doc.get("linked_user_id") else None,
        "notes": doc.get("notes"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
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
        "source": d.get("source"),
        "introduced_at": d.get("introduced_at"),
        "stage": d.get("stage") or "introduced",
        "conversion_date": d.get("conversion_date"),
        "revenue_generated": d.get("revenue_generated") or 0,
        "notes": d.get("notes"),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────
class PartnerCreate(BaseModel):
    company: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=120)
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    city: str = Field(min_length=2, max_length=80)
    county: Optional[str] = None
    units_managed: Optional[int] = 0
    growth_rate: Optional[str] = None
    portfolio_type: Optional[str] = None
    started_at: Optional[str] = None
    status: str = "lead"
    notes: Optional[str] = None


class PartnerPatch(BaseModel):
    company: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    units_managed: Optional[int] = None
    growth_rate: Optional[str] = None
    portfolio_type: Optional[str] = None
    started_at: Optional[str] = None
    status: Optional[str] = None
    territory_protected: Optional[bool] = None
    notes: Optional[str] = None


class OnboardingStepUpdate(BaseModel):
    step: int = Field(ge=0, le=len(ONBOARDING_STEPS))


class LeadCreate(BaseModel):
    lead_name: str = Field(min_length=2, max_length=200)
    lead_email: Optional[EmailStr] = None
    lead_phone: Optional[str] = None
    source: Optional[str] = None
    stage: str = "introduced"
    notes: Optional[str] = None


class LeadPatch(BaseModel):
    lead_name: Optional[str] = None
    lead_email: Optional[EmailStr] = None
    lead_phone: Optional[str] = None
    source: Optional[str] = None
    stage: Optional[str] = None
    conversion_date: Optional[str] = None
    revenue_generated: Optional[float] = None
    notes: Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN — CRUD
# ═════════════════════════════════════════════════════════════════════════════
@admin_router.get("")
async def list_partners(
    status: Optional[str] = None,
    city: Optional[str] = None,
    user=Depends(get_current_user),
):
    _require_super(user)
    q = {}
    if status and status != "all":
        q["status"] = status
    if city:
        q["city"] = {"$regex": f"^{city}$", "$options": "i"}
    cur = db.city_partners.find(q).sort("created_at", -1)
    items = [_serialize(d) async for d in cur]
    return {"items": items, "count": len(items)}


@admin_router.post("")
async def create_partner(payload: PartnerCreate, user=Depends(get_current_user)):
    _require_super(user)
    if payload.status not in ALLOWED_STATUS:
        raise HTTPException(400, f"status invalid; permis: {sorted(ALLOWED_STATUS)}")
    existing = await db.city_partners.find_one({"contact_email": payload.contact_email.lower()})
    if existing:
        raise HTTPException(409, f"Există deja partener cu emailul {payload.contact_email}.")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "company": payload.company,
        "contact_name": payload.contact_name,
        "contact_email": payload.contact_email.lower(),
        "contact_phone": payload.contact_phone,
        "city": payload.city,
        "county": payload.county,
        "units_managed": payload.units_managed or 0,
        "growth_rate": payload.growth_rate,
        "portfolio_type": payload.portfolio_type,
        "started_at": payload.started_at,
        "status": payload.status,
        "onboarding_step": 0,
        "onboarding_complete": False,
        "territory_protected": False,
        "linked_user_id": None,
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.city_partners.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize(doc)


@admin_router.get("/stats")
async def global_stats(user=Depends(get_current_user)):
    _require_super(user)
    total = await db.city_partners.count_documents({})
    by_status = {}
    for s in ALLOWED_STATUS:
        by_status[s] = await db.city_partners.count_documents({"status": s})

    # Total leads + by stage
    total_leads = await db.city_partner_leads.count_documents({})
    leads_by_stage = {}
    for st in ALLOWED_LEAD_STAGES:
        leads_by_stage[st] = await db.city_partner_leads.count_documents({"stage": st})

    # Top partners by lead count
    top_pipeline = [
        {"$group": {"_id": "$partner_id", "lead_count": {"$sum": 1}, "revenue": {"$sum": "$revenue_generated"}}},
        {"$sort": {"lead_count": -1}},
        {"$limit": 5},
    ]
    top_partners = []
    async for row in db.city_partner_leads.aggregate(top_pipeline):
        if not row.get("_id"):
            continue
        p = await db.city_partners.find_one({"_id": row["_id"]})
        if p:
            top_partners.append({
                "partner_id": str(p["_id"]),
                "company": p.get("company"),
                "city": p.get("city"),
                "lead_count": row["lead_count"],
                "revenue": row.get("revenue") or 0,
            })
    return {
        "total_partners": total,
        "by_status": by_status,
        "total_leads": total_leads,
        "leads_by_stage": leads_by_stage,
        "top_partners": top_partners,
    }


@admin_router.get("/{partner_id}")
async def get_partner(partner_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    doc = await db.city_partners.find_one({"_id": oid})
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
    if "contact_email" in update:
        update["contact_email"] = str(update["contact_email"]).lower()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.city_partners.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
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
    res = await db.city_partners.update_one(
        {"_id": oid},
        {"$set": {"status": "terminated", "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Partener inexistent.")
    return {"ok": True, "archived": True}


@admin_router.post("/{partner_id}/onboarding-step")
async def set_onboarding_step(partner_id: str, payload: OnboardingStepUpdate, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    step = max(0, min(payload.step, len(ONBOARDING_STEPS)))
    update = {
        "onboarding_step": step,
        "onboarding_complete": step >= len(ONBOARDING_STEPS),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Auto-promote status: onboarding → active when complete
    if step >= len(ONBOARDING_STEPS):
        existing = await db.city_partners.find_one({"_id": oid})
        if existing and existing.get("status") == "onboarding":
            update["status"] = "active"
    res = await db.city_partners.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(404, "Partener inexistent.")
    return _serialize(res)


@admin_router.post("/{partner_id}/create-login")
async def create_partner_login(partner_id: str, user=Depends(get_current_user)):
    """Creates a `city_partner` user account linked to this partner record."""
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    p = await db.city_partners.find_one({"_id": oid})
    if not p:
        raise HTTPException(404, "Partener inexistent.")
    if p.get("linked_user_id"):
        try:
            existing_oid = p["linked_user_id"] if isinstance(p["linked_user_id"], ObjectId) else ObjectId(str(p["linked_user_id"]))
            existing_user = await db.users.find_one({"_id": existing_oid})
        except Exception:
            existing_user = None
        if existing_user:
            return {"ok": True, "already_exists": True, "user_id": str(existing_user["_id"]), "email": existing_user["email"]}

    email = (p.get("contact_email") or "").lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        # Just link it
        await db.city_partners.update_one(
            {"_id": oid},
            {"$set": {"linked_user_id": str(existing["_id"]), "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"ok": True, "linked_existing": True, "user_id": str(existing["_id"]), "email": email}

    temp_password = secrets.token_urlsafe(12).replace("_", "X").replace("-", "Y")[:14] + "!1A"
    pwd_hash = bcrypt.hash(temp_password)
    new_user = {
        "email": email,
        "password_hash": pwd_hash,
        "name": p.get("contact_name") or p.get("company"),
        "role": "city_partner",
        "phone": p.get("contact_phone"),
        "verified_email": True,
        "terms_accepted": True,
        "privacy_policy_accepted": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "partner_id": str(p["_id"]),  # store as STRING so serialize_doc doesn't choke on ObjectId
    }
    ures = await db.users.insert_one(new_user)
    await db.city_partners.update_one(
        {"_id": oid},
        {"$set": {"linked_user_id": str(ures.inserted_id), "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "created": True, "user_id": str(ures.inserted_id), "email": email, "temp_password": temp_password}


# ─── Leads (admin side) ────────────────────────────────────────────────────
@admin_router.get("/{partner_id}/leads")
async def list_leads(partner_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    cur = db.city_partner_leads.find({"partner_id": oid}).sort("created_at", -1)
    items = [_serialize_lead(d) async for d in cur]
    return {"items": items, "count": len(items)}


@admin_router.post("/{partner_id}/leads")
async def create_lead(partner_id: str, payload: LeadCreate, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(partner_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    partner = await db.city_partners.find_one({"_id": oid})
    if not partner:
        raise HTTPException(404, "Partener inexistent.")
    if payload.stage not in ALLOWED_LEAD_STAGES:
        raise HTTPException(400, "stage invalid")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "partner_id": oid,
        "lead_name": payload.lead_name,
        "lead_email": (str(payload.lead_email).lower() if payload.lead_email else None),
        "lead_phone": payload.lead_phone,
        "source": payload.source,
        "introduced_at": now,
        "stage": payload.stage,
        "conversion_date": None,
        "revenue_generated": 0,
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.city_partner_leads.insert_one(doc)
    doc["_id"] = res.inserted_id
    from leads_store import sync_lead
    await sync_lead("city_partner", doc)
    return _serialize_lead(doc)


@admin_router.patch("/leads/{lead_id}")
async def patch_lead(lead_id: str, payload: LeadPatch, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    update = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "stage" in update:
        if update["stage"] not in ALLOWED_LEAD_STAGES:
            raise HTTPException(400, "stage invalid")
        if update["stage"] == "converted" and not update.get("conversion_date"):
            update["conversion_date"] = datetime.now(timezone.utc).isoformat()
    if "lead_email" in update:
        update["lead_email"] = str(update["lead_email"]).lower()
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.city_partner_leads.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(404, "Lead inexistent.")
    from leads_store import sync_lead
    await sync_lead("city_partner", res)
    return _serialize_lead(res)


# ═════════════════════════════════════════════════════════════════════════════
# PARTNER PORTAL — self-service (role=city_partner)
# ═════════════════════════════════════════════════════════════════════════════
async def _require_partner(user: dict) -> dict:
    if user.get("role") != "city_partner":
        raise HTTPException(403, "Acces restricționat la partenerii strategici.")
    pid = user.get("partner_id")
    if not pid:
        raise HTTPException(404, "Contul nu este legat de un partener activ.")
    try:
        pid_obj = pid if isinstance(pid, ObjectId) else ObjectId(str(pid))
    except Exception:
        raise HTTPException(404, "partner_id invalid.")
    p = await db.city_partners.find_one({"_id": pid_obj})
    if not p:
        raise HTTPException(404, "Partener inexistent.")
    if p.get("status") == "terminated":
        raise HTTPException(403, "Colaborarea a fost încheiată.")
    return p


@partner_router.get("/me")
async def partner_me(user=Depends(get_current_user)):
    p = await _require_partner(user)
    return {
        "partner": _serialize(p),
        "onboarding_steps": ONBOARDING_STEPS,
        "user": {"name": user.get("name"), "email": user.get("email")},
    }


@partner_router.get("/leads")
async def partner_my_leads(user=Depends(get_current_user)):
    p = await _require_partner(user)
    cur = db.city_partner_leads.find({"partner_id": p["_id"]}).sort("created_at", -1)
    items = [_serialize_lead(d) async for d in cur]
    return {"items": items, "count": len(items)}


@partner_router.post("/leads")
async def partner_add_lead(payload: LeadCreate, user=Depends(get_current_user)):
    p = await _require_partner(user)
    if payload.stage not in ALLOWED_LEAD_STAGES:
        raise HTTPException(400, "stage invalid")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "partner_id": p["_id"],
        "lead_name": payload.lead_name,
        "lead_email": (str(payload.lead_email).lower() if payload.lead_email else None),
        "lead_phone": payload.lead_phone,
        "source": payload.source or "partner_portal",
        "introduced_at": now,
        "stage": payload.stage,
        "conversion_date": None,
        "revenue_generated": 0,
        "notes": payload.notes,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.city_partner_leads.insert_one(doc)
    doc["_id"] = res.inserted_id
    from leads_store import sync_lead
    await sync_lead("city_partner", doc)
    return _serialize_lead(doc)


@partner_router.get("/stats")
async def partner_my_stats(user=Depends(get_current_user)):
    p = await _require_partner(user)
    pid = p["_id"]
    total = await db.city_partner_leads.count_documents({"partner_id": pid})
    by_stage = {}
    for st in ALLOWED_LEAD_STAGES:
        by_stage[st] = await db.city_partner_leads.count_documents({"partner_id": pid, "stage": st})
    revenue_pipe = [
        {"$match": {"partner_id": pid}},
        {"$group": {"_id": None, "total": {"$sum": "$revenue_generated"}}},
    ]
    revenue = 0
    async for r in db.city_partner_leads.aggregate(revenue_pipe):
        revenue = r.get("total") or 0
    conv_rate = round((by_stage.get("converted", 0) / total * 100), 1) if total else 0
    return {
        "partner": {
            "company": p.get("company"),
            "city": p.get("city"),
            "status": p.get("status"),
            "onboarding_step": p.get("onboarding_step", 0),
            "onboarding_steps_total": len(ONBOARDING_STEPS),
        },
        "leads_total": total,
        "leads_by_stage": by_stage,
        "revenue_generated": revenue,
        "conversion_rate": conv_rate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI City Partner Copilot — personalized weekly nudges (Claude Sonnet 4.5)
# ─────────────────────────────────────────────────────────────────────────────
@partner_router.post("/copilot/nudges")
async def partner_copilot_nudges(user=Depends(get_current_user)):
    """Generates 3 personalized action nudges for the logged-in partner.

    Response: {nudges: [{title, body, priority}], generated_at}
    """
    p = await _require_partner(user)
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing.")

    # Build context: partner profile + lead breakdown
    by_stage = {}
    for st in ALLOWED_LEAD_STAGES:
        by_stage[st] = await db.city_partner_leads.count_documents({"partner_id": p["_id"], "stage": st})
    recent_leads = []
    async for d in db.city_partner_leads.find({"partner_id": p["_id"]}).sort("created_at", -1).limit(8):
        recent_leads.append({
            "name": d.get("lead_name"),
            "stage": d.get("stage"),
            "introduced_at": d.get("introduced_at"),
            "source": d.get("source"),
        })

    import json, uuid as _uuid
    context = {
        "partner": {
            "company": p.get("company"),
            "city": p.get("city"),
            "status": p.get("status"),
            "onboarding_step": p.get("onboarding_step", 0),
            "units_managed": p.get("units_managed"),
            "portfolio_type": p.get("portfolio_type"),
        },
        "leads_by_stage": by_stage,
        "recent_leads": recent_leads,
    }

    system = (
        "Ești un Growth Coach pentru parteneri locali ai PropManage. "
        "Primești date despre un partener (administrator imobile / dezvoltator) și generezi "
        "EXACT 3 nudge-uri practice și personalizate pentru SĂPTĂMÂNA aceasta. "
        "Stil: concis, prietenos, în română, fără jargon. Răspunzi DOAR cu JSON valid: "
        "{nudges: [{title (max 60 char), body (max 240 char, mentionează nume concrete dacă există), priority('high'|'medium'|'low')}]}. "
        "Folosește numele clienților concreți din `recent_leads` când e relevant. "
        "Dacă datele sunt sărace, propune acțiuni de explorare (ex: aducere primul lead)."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=key,
            session_id=f"city_partner_copilot_{_uuid.uuid4().hex[:8]}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        raw = await chat.send_message(UserMessage(text=json.dumps(context, ensure_ascii=False)))
        text = (raw or "").strip()
        if text.startswith("```"):
            text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
        i, j = text.find("{"), text.rfind("}")
        if i == -1 or j <= i:
            raise HTTPException(502, "AI nu a returnat JSON valid.")
        payload = json.loads(text[i:j + 1])
        nudges = []
        for n in (payload.get("nudges") or [])[:3]:
            nudges.append({
                "title": str(n.get("title") or "")[:80],
                "body": str(n.get("body") or "")[:300],
                "priority": (n.get("priority") or "medium").lower(),
            })
        out = {
            "nudges": nudges,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        # Persist last run for caching / audit
        await db.city_partner_nudges.insert_one({
            "partner_id": p["_id"],
            **out,
        })
        return out
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[city_partner_copilot] failed: {e}")
        raise HTTPException(500, f"Eroare AI: {str(e)[:200]}")



# ═════════════════════════════════════════════════════════════════════════════
# CITY PARTNER PRODUCTS — real material catalog (admin-managed, EMPTY by default)
# Consumed by Digital Twin design concepts for REAL indicative material prices.
# Never seeded with fake data: stays empty until a super-admin adds real products.
# ═════════════════════════════════════════════════════════════════════════════
class ProductIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    brand: Optional[str] = None
    category: Optional[str] = None
    unit: str = "buc"
    price_min: float = Field(ge=0)
    price_max: Optional[float] = Field(default=None, ge=0)
    currency: str = "RON"
    partner_id: Optional[str] = None
    url: Optional[str] = None
    tags: list = Field(default_factory=list)
    active: bool = True


class ProductPatch(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    currency: Optional[str] = None
    partner_id: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[list] = None
    active: Optional[bool] = None


def _serialize_product(d: dict) -> dict:
    if not d:
        return d
    return {
        "id": str(d.get("_id")),
        "name": d.get("name"),
        "brand": d.get("brand"),
        "category": d.get("category"),
        "unit": d.get("unit") or "buc",
        "price_min": d.get("price_min"),
        "price_max": d.get("price_max"),
        "currency": d.get("currency") or "RON",
        "partner_id": str(d["partner_id"]) if d.get("partner_id") else None,
        "partner_name": d.get("partner_name"),
        "url": d.get("url"),
        "tags": d.get("tags") or [],
        "active": bool(d.get("active", True)),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


async def _resolve_partner(partner_id):
    if not partner_id:
        return None, None
    try:
        pdoc = await db.city_partners.find_one({"_id": ObjectId(partner_id)})
    except Exception:
        return None, None
    if not pdoc:
        return None, None
    return pdoc["_id"], pdoc.get("company")


@products_admin_router.get("")
async def list_products(q: Optional[str] = None, user=Depends(get_current_user)):
    _require_super(user)
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"brand": {"$regex": q, "$options": "i"}},
            {"tags": {"$in": [q.lower()]}},
        ]
    cur = db.city_partner_products.find(query).sort("created_at", -1)
    items = [_serialize_product(d) async for d in cur]
    return {"items": items, "count": len(items)}


@products_admin_router.post("")
async def create_product(payload: ProductIn, user=Depends(get_current_user)):
    _require_super(user)
    now = datetime.now(timezone.utc).isoformat()
    partner_ref, partner_name = await _resolve_partner(payload.partner_id)
    doc = {
        "name": payload.name,
        "brand": payload.brand,
        "category": payload.category,
        "unit": payload.unit or "buc",
        "price_min": payload.price_min,
        "price_max": payload.price_max if payload.price_max is not None else payload.price_min,
        "currency": payload.currency or "RON",
        "partner_id": partner_ref,
        "partner_name": partner_name,
        "url": payload.url,
        "tags": [str(t).lower().strip() for t in (payload.tags or []) if str(t).strip()],
        "active": payload.active,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    res = await db.city_partner_products.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _serialize_product(doc)


@products_admin_router.patch("/{product_id}")
async def patch_product(product_id: str, payload: ProductPatch, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    update = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "tags" in update:
        update["tags"] = [str(t).lower().strip() for t in update["tags"] if str(t).strip()]
    if "partner_id" in update:
        partner_ref, partner_name = await _resolve_partner(update["partner_id"])
        update["partner_id"] = partner_ref
        update["partner_name"] = partner_name
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.city_partner_products.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(404, "Produs inexistent.")
    return _serialize_product(res)


@products_admin_router.delete("/{product_id}")
async def delete_product(product_id: str, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(product_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    res = await db.city_partner_products.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Produs inexistent.")
    return {"ok": True, "deleted": True}
