"""PropManage router: admin_console (Metronic-style admin panel).

Provides:
- CMS content (key/value text) CRUD
- Email template editing
- Coverage zones (custom additions/disables on top of seed list)
- Trust score weights editor
- Platform settings (feature flags, commission, branding)
- Unified user management (list/filter/edit/ban)
- Finance overview, projects list, global search
- CSV exports (users, transactions, disputes)
- Live activity feed
"""
import csv
import io
import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from db import db
from core_utils import serialize_doc
from deps import require_role
from romania_zones import ROMANIAN_ZONES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin_console"])


# ============= AUDIT LOG HELPER =============
async def audit(action: str, actor: dict, target: Optional[dict] = None, before: Optional[dict] = None, after: Optional[dict] = None, note: Optional[str] = None):
    """Persist an admin action to the audit_log collection. Fire-and-forget (won't break request)."""
    try:
        await db.admin_audit_log.insert_one({
            "action": action,
            "actor_id": actor.get("id"),
            "actor_name": actor.get("name"),
            "actor_email": actor.get("email"),
            "target_type": (target or {}).get("type"),
            "target_id": (target or {}).get("id"),
            "target_label": (target or {}).get("label"),
            "before": before,
            "after": after,
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning(f"Audit log write failed for {action}: {exc}")


ROLLBACKABLE_ACTIONS = {"cms.update", "cms.reset", "settings.update", "trust_weights.update"}


# ============= DEFAULTS =============
DEFAULT_CMS = {
    "landing.promo_banner": "",
    "hero.badge": "CARTEA DIGITALĂ A CASEI TALE",
    "hero.title1": "Cartea de service",
    "hero.title2": "a casei",
    "hero.title3": "tale.",
    "hero.subtitle": "Documentele, istoricul lucrărilor și specialiștii verificați ai casei tale — într-un singur loc. Știi mereu ce s-a făcut, cine a făcut și cât a costat.",
    "hero.cta1": "Creează contul gratuit",
    "hero.cta1.variant_a": "Creează contul gratuit",
    "hero.cta1.variant_b": "Creează contul gratuit",
    "hero.cta2": "Vezi cum funcționează",
    "hero.cta2.variant_a": "Vezi cum funcționează",
    "hero.cta2.variant_b": "Vezi cum funcționează",
    "cta.badge": "CONT GRATUIT",
    "cta.title1": "Casa ta merită",
    "cta.title2": "o carte de service.",
    "cta.intro": "Contul e gratuit. Adaugi casa într-un minut, iar fiecare document și fiecare lucrare rămân în cartea casei — pentru totdeauna.",
    "cta.btn1": "Creează cont gratuit",
    "cta.btn1.variant_a": "Creează cont gratuit",
    "cta.btn1.variant_b": "Creează cont gratuit",
    "cta.btn2": "Vorbește cu un specialist",
    "cta.footer": "Fără card de credit · Contul rămâne gratuit",
    "label.request.create": "Cere o ofertă",
    "label.marketplace.cta": "Vezi marketplace",
    "label.dashboard.client": "Panou Client",
    "label.dashboard.specialist": "Panou Specialist",
    "category.hvac.name": "HVAC & Climatizare",
    "category.hvac.desc": "Instalare, reparație și mentenanță sisteme de aer condiționat și încălzire.",
    "category.plumbing.name": "Instalații sanitare",
    "category.plumbing.desc": "Reparații țevi, scurgeri, instalare obiecte sanitare, dezobturări.",
    "category.electric.name": "Sistem electric",
    "category.electric.desc": "Instalații electrice, panouri, prize, întrerupătoare, certificări.",
    "category.design.name": "Design interior",
    "category.design.desc": "Concepte design, randări, planuri tehnice, implementare la cheie.",
}

DEFAULT_EMAIL_TEMPLATES = {
    "welcome": {
        "subject": "Bine ai venit la PropManage!",
        "html": "<h1>Salut {{name}}!</h1><p>Contul tău PropManage este activ. Începe prin a adăuga prima proprietate.</p>",
    },
    "dispute_opened": {
        "subject": "Dispută deschisă — Cazul #{{case_id}}",
        "html": "<p>Bună {{name}},</p><p>Disputa pentru lucrarea <b>{{request_title}}</b> a fost deschisă. Echipa noastră o va analiza în 24h.</p>",
    },
    "dispute_resolved": {
        "subject": "Dispută rezolvată — Cazul #{{case_id}}",
        "html": "<p>Disputa a fost rezolvată în favoarea: <b>{{verdict}}</b>.</p><p>Detalii: {{details}}</p>",
    },
    "escrow_funded": {
        "subject": "Fonduri securizate în Escrow",
        "html": "<p>Suma de <b>{{amount}} RON</b> a fost securizată în escrow pentru lucrarea <b>{{request_title}}</b>.</p>",
    },
    "specialist_verified": {
        "subject": "Cont VERIFIED ✓",
        "html": "<p>Felicitări {{name}}! Contul tău este acum VERIFIED. Ai acces la marketplace-ul de leads premium.</p>",
    },
}

DEFAULT_TRUST_WEIGHTS = {
    "on_time": 0.30,
    "reviews": 0.30,
    "photos": 0.15,
    "complaints_penalty": 0.15,
    "verification_bonus": 0.10,
}
DEFAULT_SETTINGS = {
    "stripe_live": False,
    "resend_live": False,
    "platform_commission_pct": 5.0,
    "lead_fee_ron": 45.0,
    "primary_color": "#d4ff3a",
    "logo_text": "PropManage",
    "support_email": "contact@propmanage.ro",
    "maintenance_mode": False,
    # Landing page section visibility flags
    "landing_show_admin_trust": False,
    "landing_show_business_model": False,
    "landing_show_unit_economics": False,
    "landing_show_value_proposition": True,
    "landing_show_golden_path": True,
}


# ============= MODELS =============
class CMSEntryIn(BaseModel):
    key: str
    value: str
    expires_at: Optional[str] = None  # ISO datetime; only used for landing.promo_banner today


class EmailTemplateIn(BaseModel):
    subject: str
    html: str


class ZoneIn(BaseModel):
    country: str = "România"
    city: str
    zone: str


class TrustWeightsIn(BaseModel):
    on_time: float = Field(ge=0, le=1)
    reviews: float = Field(ge=0, le=1)
    photos: float = Field(ge=0, le=1)
    complaints_penalty: float = Field(ge=0, le=1)
    verification_bonus: float = Field(ge=0, le=1)


class SettingsIn(BaseModel):
    stripe_live: Optional[bool] = None
    resend_live: Optional[bool] = None
    platform_commission_pct: Optional[float] = Field(None, ge=0, le=50)
    lead_fee_ron: Optional[float] = Field(None, ge=0, le=10000)
    primary_color: Optional[str] = None
    logo_text: Optional[str] = None
    support_email: Optional[str] = None
    maintenance_mode: Optional[bool] = None
    landing_show_admin_trust: Optional[bool] = None
    landing_show_business_model: Optional[bool] = None
    landing_show_unit_economics: Optional[bool] = None
    landing_show_value_proposition: Optional[bool] = None
    landing_show_golden_path: Optional[bool] = None


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    verified: Optional[bool] = None
    tier: Optional[str] = None
    banned: Optional[bool] = None


# ============= CMS =============
@router.get("/cms")
async def list_cms(user: dict = Depends(require_role("admin"))):
    """Return merged: defaults + DB overrides. DB values win."""
    docs = await db.cms_content.find({}).to_list(500)
    overrides = {d["key"]: d.get("value", "") for d in docs}
    overrides_meta = {d["key"]: d for d in docs}
    out = []
    seen = set()
    for k, v in DEFAULT_CMS.items():
        seen.add(k)
        meta = overrides_meta.get(k)
        out.append({
            "key": k,
            "value": overrides.get(k, v),
            "default": v,
            "is_overridden": k in overrides,
            "updated_at": meta.get("updated_at") if meta else None,
            "updated_by": meta.get("updated_by") if meta else None,
            "expires_at": meta.get("expires_at") if meta else None,
        })
    # Custom keys created by admin not in defaults
    for k, v in overrides.items():
        if k in seen:
            continue
        meta = overrides_meta.get(k)
        out.append({
            "key": k,
            "value": v,
            "default": None,
            "is_overridden": True,
            "is_custom": True,
            "updated_at": meta.get("updated_at") if meta else None,
            "updated_by": meta.get("updated_by") if meta else None,
            "expires_at": meta.get("expires_at") if meta else None,
        })
    out.sort(key=lambda x: x["key"])
    return out


@router.put("/cms")
async def upsert_cms(data: CMSEntryIn, user: dict = Depends(require_role("admin"))):
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.cms_content.find_one({"key": data.key})
    update_doc = {
        "key": data.key,
        "value": data.value,
        "updated_at": now,
        "updated_by": user["id"],
    }
    if data.expires_at is not None:
        update_doc["expires_at"] = data.expires_at or None  # empty string → None (clears)
    await db.cms_content.update_one(
        {"key": data.key},
        {"$set": update_doc},
        upsert=True,
    )
    await audit("cms.update", user,
                target={"type": "cms_key", "id": data.key, "label": data.key},
                before={"value": (existing or {}).get("value"), "expires_at": (existing or {}).get("expires_at")} if existing else None,
                after={"value": data.value, "expires_at": data.expires_at})
    return {"ok": True, "key": data.key, "expires_at": update_doc.get("expires_at")}


@router.delete("/cms/{key}")
async def reset_cms(key: str, user: dict = Depends(require_role("admin"))):
    existing = await db.cms_content.find_one({"key": key})
    await db.cms_content.delete_one({"key": key})
    if existing:
        await audit("cms.reset", user,
                    target={"type": "cms_key", "id": key, "label": key},
                    before={"value": existing.get("value")})
    return {"ok": True, "reset": key}


# Public endpoint (no auth) - frontend reads merged CMS
@router.get("/cms/public", include_in_schema=False)
async def cms_public_redirect():
    raise HTTPException(404, "Use /api/cms/public instead")


# ============= EMAIL TEMPLATES =============
@router.get("/email-templates")
async def list_email_templates(user: dict = Depends(require_role("admin"))):
    docs = await db.email_templates.find({}).to_list(100)
    overrides = {d["template_id"]: d for d in docs}
    out = []
    for tid, default in DEFAULT_EMAIL_TEMPLATES.items():
        override = overrides.get(tid)
        out.append({
            "id": tid,
            "subject": override.get("subject") if override else default["subject"],
            "html": override.get("html") if override else default["html"],
            "default_subject": default["subject"],
            "default_html": default["html"],
            "is_overridden": bool(override),
            "updated_at": override.get("updated_at") if override else None,
        })
    return out


@router.put("/email-templates/{template_id}")
async def update_email_template(template_id: str, data: EmailTemplateIn, user: dict = Depends(require_role("admin"))):
    if template_id not in DEFAULT_EMAIL_TEMPLATES:
        raise HTTPException(404, "Template not found")
    await db.email_templates.update_one(
        {"template_id": template_id},
        {"$set": {
            "template_id": template_id,
            "subject": data.subject,
            "html": data.html,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user["id"],
        }},
        upsert=True,
    )
    return {"ok": True}


@router.delete("/email-templates/{template_id}")
async def reset_email_template(template_id: str, user: dict = Depends(require_role("admin"))):
    await db.email_templates.delete_one({"template_id": template_id})
    return {"ok": True}


# ============= ZONES =============
@router.get("/zones")
async def list_zones(user: dict = Depends(require_role("admin"))):
    """Return seed zones + custom additions, with disabled flag."""
    custom_docs = await db.zones_custom.find({}).to_list(500)
    disabled_docs = await db.zones_disabled.find({}).to_list(500)
    disabled_set = {(d["country"], d["city"], d["zone"]) for d in disabled_docs}

    out = []
    for country, city, zone in ROMANIAN_ZONES:
        out.append({
            "country": country,
            "city": city,
            "zone": zone,
            "source": "seed",
            "disabled": (country, city, zone) in disabled_set,
        })
    for c in custom_docs:
        out.append({
            "country": c.get("country", "România"),
            "city": c.get("city"),
            "zone": c.get("zone"),
            "source": "custom",
            "id": str(c["_id"]),
            "disabled": False,
        })
    return out


@router.post("/zones")
async def add_zone(data: ZoneIn, user: dict = Depends(require_role("admin"))):
    norm = {
        "country": data.country.strip(),
        "city": data.city.strip(),
        "zone": data.zone.strip(),
    }
    if not norm["city"] or not norm["zone"]:
        raise HTTPException(400, "City and zone required")
    # Case-insensitive duplicate check
    exists = await db.zones_custom.find_one({
        "country": {"$regex": f"^{norm['country']}$", "$options": "i"},
        "city": {"$regex": f"^{norm['city']}$", "$options": "i"},
        "zone": {"$regex": f"^{norm['zone']}$", "$options": "i"},
    })
    if exists:
        raise HTTPException(400, "Zone already exists")
    doc = dict(norm)
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    doc["created_by"] = user["id"]
    res = await db.zones_custom.insert_one(doc)
    return {"ok": True, "id": str(res.inserted_id)}


@router.delete("/zones/custom/{zone_id}")
async def remove_custom_zone(zone_id: str, user: dict = Depends(require_role("admin"))):
    await db.zones_custom.delete_one({"_id": ObjectId(zone_id)})
    return {"ok": True}


@router.post("/zones/toggle")
async def toggle_zone(data: ZoneIn, user: dict = Depends(require_role("admin"))):
    """Disable/enable a seed zone."""
    q = {"country": data.country, "city": data.city, "zone": data.zone}
    existing = await db.zones_disabled.find_one(q)
    if existing:
        await db.zones_disabled.delete_one(q)
        return {"ok": True, "disabled": False}
    await db.zones_disabled.insert_one({**q, "disabled_at": datetime.now(timezone.utc).isoformat(), "disabled_by": user["id"]})
    return {"ok": True, "disabled": True}


# ============= TRUST WEIGHTS =============
@router.get("/trust-weights")
async def get_trust_weights(user: dict = Depends(require_role("admin"))):
    doc = await db.platform_config.find_one({"key": "trust_weights"})
    if not doc:
        return {**DEFAULT_TRUST_WEIGHTS, "is_default": True}
    return {**doc.get("value", DEFAULT_TRUST_WEIGHTS), "updated_at": doc.get("updated_at"), "is_default": False}


@router.put("/trust-weights")
async def set_trust_weights(data: TrustWeightsIn, user: dict = Depends(require_role("admin"))):
    weights = data.model_dump()
    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        raise HTTPException(400, f"Weights must sum to 1.0 (got {total:.3f})")
    await db.platform_config.update_one(
        {"key": "trust_weights"},
        {"$set": {
            "key": "trust_weights",
            "value": weights,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user["id"],
        }},
        upsert=True,
    )
    return {"ok": True, **weights}


# ============= PLATFORM SETTINGS =============
@router.get("/settings")
async def get_settings(user: dict = Depends(require_role("admin"))):
    doc = await db.platform_config.find_one({"key": "settings"})
    base = dict(DEFAULT_SETTINGS)
    if doc:
        base.update(doc.get("value", {}))
        base["updated_at"] = doc.get("updated_at")
    return base


@router.put("/settings")
async def update_settings(data: SettingsIn, user: dict = Depends(require_role("admin"))):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nothing to update")
    doc = await db.platform_config.find_one({"key": "settings"})
    current = (doc or {}).get("value", {})
    merged = {**DEFAULT_SETTINGS, **current, **updates}
    await db.platform_config.update_one(
        {"key": "settings"},
        {"$set": {
            "key": "settings",
            "value": merged,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": user["id"],
        }},
        upsert=True,
    )
    await audit("settings.update", user,
                target={"type": "platform_settings", "id": "settings", "label": "Platform Settings"},
                before={k: current.get(k) for k in updates},
                after=updates)
    return {"ok": True, **merged}


# ============= USERS (Unified Management) =============
@router.get("/users")
async def list_users(
    user: dict = Depends(require_role("admin")),
    role: Optional[str] = None,
    q: Optional[str] = None,
    verified: Optional[bool] = None,
    banned: Optional[bool] = None,
    email_verified: Optional[bool] = None,
    phone_verified: Optional[bool] = None,
    marketing_consent: Optional[bool] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    filt = {}
    if role:
        filt["role"] = role
    if verified is not None:
        filt["verified"] = verified
    if banned is not None:
        filt["banned"] = banned
    if email_verified is not None:
        filt["email_verified"] = email_verified
    if phone_verified is not None:
        filt["phone_verified"] = phone_verified
    if marketing_consent is not None:
        filt["marketing_consent"] = marketing_consent
    if q:
        filt["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]
    total = await db.users.count_documents(filt)
    cursor = db.users.find(filt).sort("created_at", -1).skip(skip).limit(limit)
    items = [serialize_doc(d) async for d in cursor]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.patch("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdateIn, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(400, "Invalid user id")
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "Nothing to update")
    target_user = await db.users.find_one({"_id": oid}, {"name": 1, "email": 1, **{k: 1 for k in updates}})
    if not target_user:
        raise HTTPException(404, "User not found")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = user["id"]
    await db.users.update_one({"_id": oid}, {"$set": updates})
    await audit("user.update", user,
                target={"type": "user", "id": user_id, "label": target_user.get("email")},
                before={k: target_user.get(k) for k in updates if k not in ("updated_at", "updated_by")},
                after={k: v for k, v in updates.items() if k not in ("updated_at", "updated_by")})
    return {"ok": True}


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(400, "Invalid user id")
    target_user = await db.users.find_one({"_id": oid}, {"email": 1})
    await db.users.update_one(
        {"_id": oid},
        {"$set": {"banned": True, "banned_at": datetime.now(timezone.utc).isoformat(), "banned_by": user["id"]}},
    )
    await audit("user.ban", user,
                target={"type": "user", "id": user_id, "label": (target_user or {}).get("email")})
    return {"ok": True}


@router.post("/users/{user_id}/unban")
async def unban_user(user_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(400, "Invalid user id")
    target_user = await db.users.find_one({"_id": oid}, {"email": 1})
    await db.users.update_one(
        {"_id": oid},
        {"$unset": {"banned": "", "banned_at": "", "banned_by": ""}},
    )
    await audit("user.unban", user,
                target={"type": "user", "id": user_id, "label": (target_user or {}).get("email")})
    return {"ok": True}


# ============= GLOBAL SEARCH =============
@router.get("/search")
async def global_search(
    q: str = Query(..., min_length=2),
    user: dict = Depends(require_role("admin")),
):
    pattern = {"$regex": q, "$options": "i"}
    users = await db.users.find(
        {"$or": [{"name": pattern}, {"email": pattern}]}
    ).limit(8).to_list(8)
    requests = await db.requests.find(
        {"$or": [{"title": pattern}, {"description": pattern}]}
    ).limit(8).to_list(8)
    projects = await db.projects.find(
        {"name": pattern}
    ).limit(8).to_list(8)
    return {
        "users": [{"id": str(u["_id"]), "name": u.get("name"), "email": u.get("email"), "role": u.get("role")} for u in users],
        "requests": [{"id": str(r["_id"]), "title": r.get("title"), "status": r.get("status")} for r in requests],
        "projects": [{"id": str(p["_id"]), "name": p.get("name"), "status": p.get("status")} for p in projects],
    }


# ============= FINANCE OVERVIEW =============
@router.get("/finance/overview")
async def finance_overview(user: dict = Depends(require_role("admin"))):
    """Wallet totals + transaction sums."""
    users = await db.users.find({}, {"wallet_balance": 1, "name": 1, "email": 1, "role": 1}).to_list(2000)
    total_wallet = sum((u.get("wallet_balance") or 0) for u in users)
    top_wallets = sorted(
        [{"id": str(u["_id"]), "name": u.get("name"), "email": u.get("email"), "role": u.get("role"), "balance": u.get("wallet_balance") or 0} for u in users],
        key=lambda x: x["balance"], reverse=True
    )[:10]

    # tx totals last 30 days
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    pipeline = [
        {"$match": {"created_at": {"$gte": since}}},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
    ]
    tx_agg = await db.transactions.aggregate(pipeline).to_list(20)
    by_type = [{"type": t["_id"] or "unknown", "total": t["total"], "count": t["count"]} for t in tx_agg]

    # Escrow held
    escrow_held = 0
    async for r in db.requests.find({"status": {"$in": ["assigned", "in_progress", "completed"]}, "escrow_amount": {"$gt": 0}}):
        escrow_held += r.get("escrow_amount", 0)

    return {
        "total_wallet": round(total_wallet, 2),
        "escrow_held": round(escrow_held, 2),
        "top_wallets": top_wallets,
        "tx_by_type": by_type,
    }


# ============= PROJECTS LIST =============
@router.get("/projects")
async def admin_projects(
    user: dict = Depends(require_role("admin")),
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    filt = {}
    if status:
        filt["status"] = status
    total = await db.projects.count_documents(filt)
    cursor = db.projects.find(filt).sort("created_at", -1).skip(skip).limit(limit)
    docs = [serialize_doc(d) async for d in cursor]
    # Enrich names
    uids = set()
    for d in docs:
        if d.get("client_id"):
            uids.add(d["client_id"])
        if d.get("designer_id"):
            uids.add(d["designer_id"])
    umap = {}
    if uids:
        async for u in db.users.find({"_id": {"$in": [ObjectId(uid) for uid in uids]}}, {"name": 1, "email": 1}):
            umap[str(u["_id"])] = u
    for d in docs:
        d["client_name"] = (umap.get(d.get("client_id")) or {}).get("name")
        d["designer_name"] = (umap.get(d.get("designer_id")) or {}).get("name")
    return {"items": docs, "total": total}


# ============= CSV EXPORTS =============
def _csv_response(rows: List[dict], filename: str):
    if not rows:
        rows = [{"info": "no data"}]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/users.csv")
async def export_users(user: dict = Depends(require_role("admin"))):
    rows = []
    async for u in db.users.find({}):
        rows.append({
            "id": str(u["_id"]),
            "name": u.get("name", ""),
            "email": u.get("email", ""),
            "role": u.get("role", ""),
            "verified": u.get("verified", False),
            "tier": u.get("tier", ""),
            "wallet_balance": u.get("wallet_balance", 0),
            "created_at": u.get("created_at", ""),
            "banned": u.get("banned", False),
        })
    return _csv_response(rows, "users.csv")


@router.get("/export/transactions.csv")
async def export_transactions(user: dict = Depends(require_role("admin"))):
    rows = []
    async for t in db.transactions.find({}).sort("created_at", -1).limit(5000):
        rows.append({
            "id": str(t["_id"]),
            "user_id": t.get("user_id", ""),
            "type": t.get("type", ""),
            "amount": t.get("amount", 0),
            "created_at": t.get("created_at", ""),
        })
    return _csv_response(rows, "transactions.csv")


@router.get("/export/disputes.csv")
async def export_disputes(user: dict = Depends(require_role("admin"))):
    rows = []
    async for d in db.disputes.find({}).sort("created_at", -1):
        rows.append({
            "id": str(d["_id"]),
            "request_id": d.get("request_id", ""),
            "opened_by": d.get("opened_by", ""),
            "status": d.get("status", ""),
            "reason": (d.get("reason") or "")[:200],
            "verdict": d.get("verdict", ""),
            "created_at": d.get("created_at", ""),
        })
    return _csv_response(rows, "disputes.csv")


# ============= LIVE ACTIVITY FEED =============
@router.get("/activity-feed-live")
async def activity_feed_live(limit: int = Query(20, le=100), user: dict = Depends(require_role("admin"))):
    docs = await db.events.find({}).sort("created_at", -1).limit(limit).to_list(limit)
    # Enrich user names
    uids = {d.get("actor_id") for d in docs if d.get("actor_id")}
    umap = {}
    if uids:
        async for u in db.users.find({"_id": {"$in": [ObjectId(uid) for uid in uids if uid]}}, {"name": 1, "role": 1}):
            umap[str(u["_id"])] = u
    out = []
    for d in docs:
        actor = umap.get(d.get("actor_id"))
        out.append({
            "id": str(d.get("_id")),
            "type": d.get("type"),
            "message": d.get("message"),
            "created_at": d.get("created_at"),
            "actor_name": actor.get("name") if actor else None,
            "actor_role": actor.get("role") if actor else None,
        })
    return out


# ============= PUBLIC CMS (no auth) =============
public_router = APIRouter(prefix="/api", tags=["cms_public"])



@public_router.get("/cms/public")
async def get_public_cms():
    """Return merged defaults + overrides as flat dict (no auth). Includes landing visibility flags."""
    docs = await db.cms_content.find({}).to_list(500)
    now_iso = datetime.now(timezone.utc).isoformat()
    overrides = {}
    for d in docs:
        # Skip expired overrides → reveal defaults (or empty for custom keys)
        exp = d.get("expires_at")
        if exp and exp <= now_iso:
            continue
        overrides[d["key"]] = d.get("value", "")
    merged = {**DEFAULT_CMS, **overrides}
    # Append public settings (landing visibility flags only)
    settings_doc = await db.platform_config.find_one({"key": "settings"})
    base = dict(DEFAULT_SETTINGS)
    if settings_doc:
        base.update(settings_doc.get("value", {}))
    for flag in [
        "landing_show_admin_trust", "landing_show_business_model",
        "landing_show_unit_economics", "landing_show_value_proposition",
        "landing_show_golden_path"
    ]:
        merged[f"_settings.{flag}"] = bool(base.get(flag, False))
    return merged


# ============= A/B TESTING =============
class ABEventIn(BaseModel):
    experiment: str = Field(min_length=2, max_length=64)
    variant: str = Field(pattern="^(a|b)$")
    event: str = Field(pattern="^(impression|click)$")
    session_id: Optional[str] = None


@public_router.post("/ab/track")
async def ab_track(data: ABEventIn):
    """Track A/B test event. Public — no auth. Deduplicates impressions per (session, exp, variant)."""
    now = datetime.now(timezone.utc).isoformat()
    if data.event == "impression" and data.session_id:
        # 1 impression per session per (exp, variant)
        exists = await db.ab_events.find_one({
            "experiment": data.experiment,
            "variant": data.variant,
            "event": "impression",
            "session_id": data.session_id,
        })
        if exists:
            return {"ok": True, "deduplicated": True}
    await db.ab_events.insert_one({
        "experiment": data.experiment,
        "variant": data.variant,
        "event": data.event,
        "session_id": data.session_id,
        "created_at": now,
    })
    return {"ok": True}


@router.get("/ab/stats")
async def ab_stats(user: dict = Depends(require_role("admin"))):
    """Return per-experiment, per-variant counts + CTR."""
    pipeline = [
        {"$group": {
            "_id": {"experiment": "$experiment", "variant": "$variant", "event": "$event"},
            "count": {"$sum": 1},
        }},
    ]
    rows = await db.ab_events.aggregate(pipeline).to_list(200)
    # Reshape: experiment -> variant -> {impressions, clicks}
    exp_map = {}
    for r in rows:
        eid = r["_id"]["experiment"]
        var = r["_id"]["variant"]
        evt = r["_id"]["event"]
        exp_map.setdefault(eid, {}).setdefault(var, {"impressions": 0, "clicks": 0})[f"{evt}s"] = r["count"]

    out = []
    KNOWN = {
        "hero_cta1": {"label": "Hero CTA principal", "keys": ["hero.cta1.variant_a", "hero.cta1.variant_b"]},
        "hero_cta2": {"label": "Hero CTA secundar (Flux Complet)", "keys": ["hero.cta2.variant_a", "hero.cta2.variant_b"]},
        "cta_btn1": {"label": "CTA bottom — Creează cont", "keys": ["cta.btn1.variant_a", "cta.btn1.variant_b"]},
    }
    for eid, vmap in exp_map.items():
        meta = KNOWN.get(eid, {"label": eid, "keys": []})
        variants = []
        for v in ["a", "b"]:
            stats = vmap.get(v, {"impressions": 0, "clicks": 0})
            impr = stats.get("impressions", 0)
            clk = stats.get("clicks", 0)
            ctr = (clk / impr * 100) if impr else 0
            variants.append({
                "variant": v,
                "impressions": impr,
                "clicks": clk,
                "ctr": round(ctr, 2),
            })
        # Winner: highest CTR if both have >= 30 impressions
        winner = None
        if variants[0]["impressions"] >= 30 and variants[1]["impressions"] >= 30:
            if variants[0]["ctr"] > variants[1]["ctr"]:
                winner = "a"
            elif variants[1]["ctr"] > variants[0]["ctr"]:
                winner = "b"
        out.append({
            "experiment": eid,
            "label": meta["label"],
            "keys": meta["keys"],
            "variants": variants,
            "winner": winner,
        })
    # Ensure known experiments appear even with zero data
    for eid, meta in KNOWN.items():
        if not any(o["experiment"] == eid for o in out):
            out.append({
                "experiment": eid,
                "label": meta["label"],
                "keys": meta["keys"],
                "variants": [
                    {"variant": "a", "impressions": 0, "clicks": 0, "ctr": 0},
                    {"variant": "b", "impressions": 0, "clicks": 0, "ctr": 0},
                ],
                "winner": None,
            })
    return out


@router.delete("/ab/{experiment}/reset")
async def ab_reset(experiment: str, user: dict = Depends(require_role("admin"))):
    res = await db.ab_events.delete_many({"experiment": experiment})
    return {"ok": True, "deleted": res.deleted_count}


# ============= LANDING PRESETS =============
LANDING_FLAG_KEYS = [
    "landing_show_admin_trust",
    "landing_show_business_model",
    "landing_show_unit_economics",
    "landing_show_value_proposition",
    "landing_show_golden_path",
]
DEFAULT_PRESETS = [
    {
        "name": "Public Client",
        "description": "Pentru utilizatorul obișnuit — fără pitch investitor",
        "flags": {"landing_show_admin_trust": False, "landing_show_business_model": False,
                  "landing_show_unit_economics": False, "landing_show_value_proposition": True,
                  "landing_show_golden_path": True},
        "system": True,
    },
    {
        "name": "Pitch Investitor",
        "description": "Toate secțiunile vizibile, incl. Business Model + KPI financiari",
        "flags": {"landing_show_admin_trust": True, "landing_show_business_model": True,
                  "landing_show_unit_economics": True, "landing_show_value_proposition": True,
                  "landing_show_golden_path": True},
        "system": True,
    },
    {
        "name": "Demo Minimal",
        "description": "Doar Hero + Golden Path — pentru screenshot-uri marketing",
        "flags": {"landing_show_admin_trust": False, "landing_show_business_model": False,
                  "landing_show_unit_economics": False, "landing_show_value_proposition": False,
                  "landing_show_golden_path": True},
        "system": True,
    },
]


class PresetIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=300)
    flags: dict


async def _ensure_default_presets():
    """Idempotent — seed default presets if none of type system exist."""
    existing = await db.landing_presets.count_documents({"system": True})
    if existing < len(DEFAULT_PRESETS):
        for p in DEFAULT_PRESETS:
            await db.landing_presets.update_one(
                {"name": p["name"], "system": True},
                {"$setOnInsert": {
                    "name": p["name"],
                    "description": p["description"],
                    "flags": p["flags"],
                    "system": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )


@router.get("/landing-presets")
async def list_landing_presets(user: dict = Depends(require_role("admin"))):
    await _ensure_default_presets()
    docs = await db.landing_presets.find({}).sort([("system", -1), ("created_at", 1)]).to_list(100)
    out = []
    for d in docs:
        out.append({
            "id": str(d["_id"]),
            "name": d.get("name"),
            "description": d.get("description"),
            "flags": d.get("flags", {}),
            "system": bool(d.get("system", False)),
            "created_at": d.get("created_at"),
        })
    return out


@router.post("/landing-presets")
async def create_landing_preset(data: PresetIn, user: dict = Depends(require_role("admin"))):
    # Sanitize flags — keep only known keys
    flags = {k: bool(data.flags.get(k, False)) for k in LANDING_FLAG_KEYS}
    if await db.landing_presets.find_one({"name": data.name}):
        raise HTTPException(400, "Un preset cu acest nume există deja.")
    doc = {
        "name": data.name.strip(),
        "description": data.description,
        "flags": flags,
        "system": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
    }
    res = await db.landing_presets.insert_one(doc)
    await audit("preset.create", user,
                target={"type": "preset", "id": str(res.inserted_id), "label": data.name},
                after={"flags": flags})
    return {"ok": True, "id": str(res.inserted_id)}


@router.delete("/landing-presets/{preset_id}")
async def delete_landing_preset(preset_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(preset_id)
    except InvalidId:
        raise HTTPException(400, "Invalid preset id")
    doc = await db.landing_presets.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Preset not found")
    if doc.get("system"):
        raise HTTPException(400, "Preset-urile sistem nu pot fi șterse.")
    await db.landing_presets.delete_one({"_id": oid})
    await audit("preset.delete", user,
                target={"type": "preset", "id": preset_id, "label": doc.get("name")},
                before={"flags": doc.get("flags")})
    return {"ok": True}


@router.post("/landing-presets/{preset_id}/apply")
async def apply_landing_preset(preset_id: str, user: dict = Depends(require_role("admin"))):
    """Persist this preset's flags into platform settings."""
    try:
        oid = ObjectId(preset_id)
    except InvalidId:
        raise HTTPException(400, "Invalid preset id")
    preset = await db.landing_presets.find_one({"_id": oid})
    if not preset:
        raise HTTPException(404, "Preset not found")
    settings_doc = await db.platform_config.find_one({"key": "settings"})
    current = (settings_doc or {}).get("value", {})
    merged = {**DEFAULT_SETTINGS, **current, **preset.get("flags", {})}
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.platform_config.update_one(
        {"key": "settings"},
        {"$set": {
            "key": "settings", "value": merged,
            "updated_at": now_iso,
            "updated_by": user["id"],
        }},
        upsert=True,
    )
    # Log manual apply to history for full audit trail
    await db.preset_schedule_runs.insert_one({
        "schedule_id": None,
        "preset_id": preset_id,
        "preset_name": preset.get("name"),
        "flags": preset.get("flags", {}),
        "day_of_week": None,
        "time": None,
        "run_at": now_iso,
        "status": "applied",
        "trigger": "manual",
        "actor_id": user["id"],
        "actor_name": user.get("name"),
    })
    return {"ok": True, "applied": preset.get("name"), "flags": preset.get("flags")}


# ============= AUTO-SCHEDULE PRESETS =============
class ScheduleIn(BaseModel):
    preset_id: str
    days: List[int] = Field(min_length=1, max_length=7)  # 0=Monday ... 6=Sunday
    time: str = Field(pattern=r"^[0-2]\d:[0-5]\d$")  # HH:MM 24h
    enabled: bool = True


@router.get("/preset-schedules")
async def list_schedules(user: dict = Depends(require_role("admin"))):
    docs = await db.preset_schedules.find({}).sort("created_at", -1).to_list(100)
    # Enrich with preset names
    pids = [d.get("preset_id") for d in docs]
    pmap = {}
    if pids:
        pid_oids = [ObjectId(p) for p in pids if p]
        async for p in db.landing_presets.find({"_id": {"$in": pid_oids}}):
            pmap[str(p["_id"])] = p
    out = []
    for d in docs:
        preset = pmap.get(d.get("preset_id"))
        out.append({
            "id": str(d["_id"]),
            "preset_id": d.get("preset_id"),
            "preset_name": (preset or {}).get("name", "(șters)"),
            "days": d.get("days", []),
            "time": d.get("time"),
            "enabled": bool(d.get("enabled", True)),
            "last_run_at": d.get("last_run_at"),
            "created_at": d.get("created_at"),
        })
    return out


@router.post("/preset-schedules")
async def create_schedule(data: ScheduleIn, user: dict = Depends(require_role("admin"))):
    if any(d < 0 or d > 6 for d in data.days):
        raise HTTPException(400, "Days must be 0-6 (Monday-Sunday)")
    try:
        ObjectId(data.preset_id)
    except InvalidId:
        raise HTTPException(400, "Invalid preset id")
    preset = await db.landing_presets.find_one({"_id": ObjectId(data.preset_id)})
    if not preset:
        raise HTTPException(404, "Preset not found")
    doc = {
        "preset_id": data.preset_id,
        "days": sorted(set(data.days)),
        "time": data.time,
        "enabled": data.enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
    }
    res = await db.preset_schedules.insert_one(doc)
    return {"ok": True, "id": str(res.inserted_id)}


@router.patch("/preset-schedules/{schedule_id}")
async def toggle_schedule(schedule_id: str, enabled: bool, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(schedule_id)
    except InvalidId:
        raise HTTPException(400, "Invalid id")
    await db.preset_schedules.update_one({"_id": oid}, {"$set": {"enabled": enabled}})
    return {"ok": True}


@router.delete("/preset-schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(schedule_id)
    except InvalidId:
        raise HTTPException(400, "Invalid id")
    await db.preset_schedules.delete_one({"_id": oid})
    return {"ok": True}


async def run_due_preset_schedules():
    """Cron callable — runs every minute. Apply schedules whose (day, time) match now (Europe/Bucharest)."""
    import pytz as _pytz
    tz = _pytz.timezone("Europe/Bucharest")
    now = datetime.now(tz)
    weekday = now.weekday()  # 0=Monday
    hhmm = now.strftime("%H:%M")

    # Dedup window: same minute → skip if we already ran today's slot
    today_key = now.strftime("%Y-%m-%d")
    async for sched in db.preset_schedules.find({"enabled": True, "time": hhmm, "days": weekday}):
        last = sched.get("last_run_at") or ""
        if last.startswith(today_key) and last.endswith(hhmm):
            continue  # already ran this minute today
        # Apply preset
        try:
            preset = await db.landing_presets.find_one({"_id": ObjectId(sched["preset_id"])})
            if not preset:
                continue
            settings_doc = await db.platform_config.find_one({"key": "settings"})
            current = (settings_doc or {}).get("value", {})
            merged = {**DEFAULT_SETTINGS, **current, **preset.get("flags", {})}
            run_at_iso = datetime.now(timezone.utc).isoformat()
            await db.platform_config.update_one(
                {"key": "settings"},
                {"$set": {"key": "settings", "value": merged,
                          "updated_at": run_at_iso,
                          "updated_by": "scheduler"}},
                upsert=True,
            )
            await db.preset_schedules.update_one(
                {"_id": sched["_id"]},
                {"$set": {"last_run_at": f"{today_key}T{hhmm}"}}
            )
            # Log run to history
            await db.preset_schedule_runs.insert_one({
                "schedule_id": str(sched["_id"]),
                "preset_id": sched["preset_id"],
                "preset_name": preset.get("name"),
                "flags": preset.get("flags", {}),
                "day_of_week": weekday,
                "time": hhmm,
                "run_at": run_at_iso,
                "status": "applied",
                "trigger": "auto-scheduler",
            })
            logger.info(f"Scheduled preset applied: {preset.get('name')} at {hhmm}")
        except Exception as exc:
            await db.preset_schedule_runs.insert_one({
                "schedule_id": str(sched.get("_id")),
                "preset_id": sched.get("preset_id"),
                "preset_name": "(eroare)",
                "day_of_week": weekday,
                "time": hhmm,
                "run_at": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "trigger": "auto-scheduler",
                "error": str(exc)[:300],
            })
            logger.warning(f"Schedule run failed for {sched.get('_id')}: {exc}")


@router.get("/schedule-history")
async def schedule_history(    user: dict = Depends(require_role("admin")),
    preset_id: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    filt = {}
    if preset_id:
        filt["preset_id"] = preset_id
    cursor = db.preset_schedule_runs.find(filt).sort("run_at", -1).limit(limit)
    out = []
    async for d in cursor:
        out.append({
            "id": str(d["_id"]),
            "schedule_id": d.get("schedule_id"),
            "preset_id": d.get("preset_id"),
            "preset_name": d.get("preset_name"),
            "day_of_week": d.get("day_of_week"),
            "time": d.get("time"),
            "run_at": d.get("run_at"),
            "status": d.get("status"),
            "trigger": d.get("trigger"),
            "error": d.get("error"),
        })
    return out


# ============= AUDIT LOG ENDPOINTS =============
@router.get("/audit-log")
async def list_audit_log(
    user: dict = Depends(require_role("admin")),
    action: Optional[str] = None,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    q: Optional[str] = None,
    pinned: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, le=500),
    skip: int = 0,
):
    filt = {}
    if action:
        filt["action"] = action
    if actor_id:
        filt["actor_id"] = actor_id
    if target_type:
        filt["target_type"] = target_type
    if pinned is True:
        filt["pinned"] = True
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to
        filt["created_at"] = date_filter
    if q:
        filt["$or"] = [
            {"actor_name": {"$regex": q, "$options": "i"}},
            {"actor_email": {"$regex": q, "$options": "i"}},
            {"target_label": {"$regex": q, "$options": "i"}},
            {"note": {"$regex": q, "$options": "i"}},
            {"pinned_note": {"$regex": q, "$options": "i"}},
        ]
    total = await db.admin_audit_log.count_documents(filt)
    # Sort: pinned first, then newest
    cursor = db.admin_audit_log.find(filt).sort([("pinned", -1), ("created_at", -1)]).skip(skip).limit(limit)
    items = []
    async for d in cursor:
        items.append({
            "id": str(d["_id"]),
            "action": d.get("action"),
            "actor_id": d.get("actor_id"),
            "actor_name": d.get("actor_name"),
            "actor_email": d.get("actor_email"),
            "target_type": d.get("target_type"),
            "target_id": d.get("target_id"),
            "target_label": d.get("target_label"),
            "before": d.get("before"),
            "after": d.get("after"),
            "note": d.get("note"),
            "created_at": d.get("created_at"),
            "rollbackable": d.get("action") in ROLLBACKABLE_ACTIONS,
            "pinned": bool(d.get("pinned")),
            "pinned_note": d.get("pinned_note"),
            "pinned_at": d.get("pinned_at"),
            "pinned_by": d.get("pinned_by"),
            "pinned_by_name": d.get("pinned_by_name"),
        })
    pinned_total = await db.admin_audit_log.count_documents({"pinned": True})
    return {"items": items, "total": total, "skip": skip, "limit": limit, "pinned_total": pinned_total}


@router.get("/audit-log/actions")
async def audit_log_actions(user: dict = Depends(require_role("admin"))):
    """Return distinct action types + counts for filter dropdown."""
    pipeline = [
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    rows = await db.admin_audit_log.aggregate(pipeline).to_list(50)
    return [{"action": r["_id"], "count": r["count"]} for r in rows if r["_id"]]


@router.get("/audit-log/export.csv")
async def export_audit_log_csv(user: dict = Depends(require_role("admin"))):
    rows = []
    async for d in db.admin_audit_log.find({}).sort("created_at", -1).limit(5000):
        rows.append({
            "created_at": d.get("created_at", ""),
            "action": d.get("action", ""),
            "actor": d.get("actor_email", ""),
            "actor_name": d.get("actor_name", ""),
            "target_type": d.get("target_type", ""),
            "target_label": d.get("target_label", ""),
            "before": str(d.get("before") or "")[:200],
            "after": str(d.get("after") or "")[:200],
        })
    return _csv_response(rows, "audit_log.csv")


# ============= SNAPSHOTS (full-state bookmarks) =============
# Sistem CANONIC de snapshot/restore pentru configurația admin-owned.
# Include (post-remediere Iun 2026) și design_tokens RUNTIME-ACTIVE, pages,
# site_menu, feature_config. pages_versions = istoric append-only, NU se
# snapshot-uiește/restaurează niciodată (regulă comună cu config_io).
SNAPSHOT_PARTS = ["cms", "settings", "trust_weights", "presets",
                  "design_tokens", "pages", "site_menu", "feature_config"]


class SnapshotIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parts: List[str] = Field(default_factory=lambda: list(SNAPSHOT_PARTS))


@router.post("/snapshots")
async def create_snapshot(data: SnapshotIn, user: dict = Depends(require_role("admin"))):
    parts = [p for p in data.parts if p in SNAPSHOT_PARTS]
    if not parts:
        raise HTTPException(400, "Selectează cel puțin o componentă pentru snapshot")
    if await db.admin_snapshots.find_one({"name": data.name}):
        raise HTTPException(400, "Un snapshot cu acest nume există deja")
    snapshot_data = {}
    counts = {}
    if "cms" in parts:
        cms_docs = await db.cms_content.find({}).to_list(500)
        snapshot_data["cms"] = [{"key": d["key"], "value": d.get("value", "")} for d in cms_docs]
        counts["cms"] = len(snapshot_data["cms"])
    if "settings" in parts:
        s = await db.platform_config.find_one({"key": "settings"})
        snapshot_data["settings"] = (s or {}).get("value", {})
        counts["settings"] = len(snapshot_data["settings"] or {})
    if "trust_weights" in parts:
        t = await db.platform_config.find_one({"key": "trust_weights"})
        snapshot_data["trust_weights"] = (t or {}).get("value", {})
        counts["trust_weights"] = 1 if snapshot_data["trust_weights"] else 0
    if "presets" in parts:
        ps = await db.landing_presets.find({}).to_list(100)
        snapshot_data["presets"] = [
            {"name": p["name"], "description": p.get("description"), "flags": p.get("flags", {}), "system": bool(p.get("system"))}
            for p in ps
        ]
        counts["presets"] = len(snapshot_data["presets"])
    if "design_tokens" in parts:
        dt = await db.design_tokens.find_one({"_id": "active"})
        snapshot_data["design_tokens"] = {
            "tokens": (dt or {}).get("tokens") or {},
            "preset_id": (dt or {}).get("preset_id"),
        }
        counts["design_tokens"] = len(snapshot_data["design_tokens"]["tokens"] or {})
    if "pages" in parts:
        page_docs = await db.pages.find({}, {"_id": 0}).to_list(500)
        snapshot_data["pages"] = page_docs
        counts["pages"] = len(page_docs)
    if "site_menu" in parts:
        menu = await db.site_menu.find_one({"key": "main"}, {"_id": 0})
        snapshot_data["site_menu"] = menu or {}
        counts["site_menu"] = len((menu or {}).get("items") or [])
    if "feature_config" in parts:
        fc = await db.feature_config.find_one({"_id": "config"}, {"_id": 0})
        snapshot_data["feature_config"] = fc or {}
        counts["feature_config"] = len((fc or {}).get("features") or [])
    doc = {
        "name": data.name.strip(),
        "description": data.description,
        "parts": parts,
        "data": snapshot_data,
        "counts": counts,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "created_by_name": user.get("name"),
    }
    res = await db.admin_snapshots.insert_one(doc)
    await audit("snapshot.create", user,
                target={"type": "snapshot", "id": str(res.inserted_id), "label": data.name},
                after={"parts": parts, "counts": counts})
    return {"ok": True, "id": str(res.inserted_id), "counts": counts}


@router.get("/snapshots")
async def list_snapshots(user: dict = Depends(require_role("admin"))):
    docs = await db.admin_snapshots.find({}, {"data": 0}).sort("created_at", -1).to_list(100)
    return [
        {
            "id": str(d["_id"]),
            "name": d.get("name"),
            "description": d.get("description"),
            "parts": d.get("parts", []),
            "counts": d.get("counts", {}),
            "created_at": d.get("created_at"),
            "created_by_name": d.get("created_by_name"),
        }
        for d in docs
    ]


@router.get("/snapshots/{snapshot_id}")
async def get_snapshot(snapshot_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(snapshot_id)
    except InvalidId:
        raise HTTPException(400, "Invalid snapshot id")
    doc = await db.admin_snapshots.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Snapshot not found")
    return {
        "id": str(doc["_id"]),
        "name": doc.get("name"),
        "description": doc.get("description"),
        "parts": doc.get("parts", []),
        "counts": doc.get("counts", {}),
        "data": doc.get("data"),
        "created_at": doc.get("created_at"),
        "created_by_name": doc.get("created_by_name"),
    }


@router.post("/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str, user: dict = Depends(require_role("admin"))):
    """Restore the snapshot's saved state. CMS/settings/trust replaced; presets only re-create missing custom ones."""
    try:
        oid = ObjectId(snapshot_id)
    except InvalidId:
        raise HTTPException(400, "Invalid snapshot id")
    snap = await db.admin_snapshots.find_one({"_id": oid})
    if not snap:
        raise HTTPException(404, "Snapshot not found")
    data = snap.get("data", {})
    now_iso = datetime.now(timezone.utc).isoformat()
    restored = {}
    failed = []

    if "cms" in data:
        # Wipe current overrides and insert snapshot overrides
        await db.cms_content.delete_many({})
        if data["cms"]:
            await db.cms_content.insert_many([
                {"key": e["key"], "value": e.get("value", ""), "updated_at": now_iso, "updated_by": user["id"]}
                for e in data["cms"]
            ])
        restored["cms"] = len(data["cms"])

    if "settings" in data and data["settings"]:
        merged = {**DEFAULT_SETTINGS, **data["settings"]}
        await db.platform_config.update_one(
            {"key": "settings"},
            {"$set": {"key": "settings", "value": merged, "updated_at": now_iso, "updated_by": user["id"]}},
            upsert=True,
        )
        restored["settings"] = len(data["settings"])

    if "trust_weights" in data and data["trust_weights"]:
        await db.platform_config.update_one(
            {"key": "trust_weights"},
            {"$set": {"key": "trust_weights", "value": data["trust_weights"], "updated_at": now_iso, "updated_by": user["id"]}},
            upsert=True,
        )
        restored["trust_weights"] = 1

    if "presets" in data:
        # Re-create custom presets if missing by name (preserves system ones, doesn't duplicate)
        added = 0
        for p in data["presets"]:
            if p.get("system"):
                continue  # Don't touch system presets
            existing = await db.landing_presets.find_one({"name": p["name"]})
            if not existing:
                await db.landing_presets.insert_one({
                    "name": p["name"],
                    "description": p.get("description"),
                    "flags": p.get("flags", {}),
                    "system": False,
                    "created_at": now_iso,
                    "created_by": user["id"],
                    "restored_from_snapshot": str(oid),
                })
                added += 1
        restored["presets_added"] = added

    if "design_tokens" in data and (data.get("design_tokens") or {}).get("tokens"):
        try:
            from routes.design_studio import _reject_dangerous_deep
            _reject_dangerous_deep(data["design_tokens"]["tokens"])  # SEC-003
            await db.design_tokens.update_one(
                {"_id": "active"},
                {"$set": {"tokens": data["design_tokens"]["tokens"],
                          "preset_id": data["design_tokens"].get("preset_id") or "restored",
                          "updated_at": now_iso}},
                upsert=True,
            )
            restored["design_tokens"] = len(data["design_tokens"]["tokens"])
        except Exception as exc:  # noqa: BLE001
            failed.append({"part": "design_tokens", "error": str(exc)[:200]})

    if "pages" in data and isinstance(data.get("pages"), list):
        try:
            n = 0
            for p in data["pages"]:
                if isinstance(p, dict) and p.get("key"):
                    await db.pages.update_one({"key": p["key"]}, {"$set": {**p, "updated_at": now_iso}}, upsert=True)
                    n += 1
            restored["pages"] = n
        except Exception as exc:  # noqa: BLE001
            failed.append({"part": "pages", "error": str(exc)[:200]})

    if "site_menu" in data and data.get("site_menu"):
        try:
            m = data["site_menu"]
            await db.site_menu.update_one({"key": m.get("key") or "main"},
                                          {"$set": {**m, "updated_at": now_iso}}, upsert=True)
            restored["site_menu"] = len(m.get("items") or [])
        except Exception as exc:  # noqa: BLE001
            failed.append({"part": "site_menu", "error": str(exc)[:200]})

    if "feature_config" in data and data.get("feature_config"):
        try:
            await db.feature_config.update_one({"_id": "config"},
                                               {"$set": {**data["feature_config"], "updated_at": now_iso}}, upsert=True)
            restored["feature_config"] = 1
        except Exception as exc:  # noqa: BLE001
            failed.append({"part": "feature_config", "error": str(exc)[:200]})

    await audit("snapshot.restore", user,
                target={"type": "snapshot", "id": snapshot_id, "label": snap.get("name")},
                after={"restored": restored, "failed": failed or None})
    if failed:
        # NO false-success: dacă o parte a eșuat, restore-ul eșuează vizibil.
        raise HTTPException(500, {"message": "Restore parțial eșuat",
                                  "restored": restored, "failed": failed})
    return {"ok": True, "name": snap.get("name"), "restored": restored}


@router.delete("/snapshots/{snapshot_id}")
async def delete_snapshot(snapshot_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(snapshot_id)
    except InvalidId:
        raise HTTPException(400, "Invalid snapshot id")
    doc = await db.admin_snapshots.find_one({"_id": oid}, {"name": 1})
    if not doc:
        raise HTTPException(404, "Not found")
    await db.admin_snapshots.delete_one({"_id": oid})
    await audit("snapshot.delete", user,
                target={"type": "snapshot", "id": snapshot_id, "label": doc.get("name")})
    return {"ok": True}


@router.get("/audit-log/{entry_id}")
async def get_audit_entry(entry_id: str, user: dict = Depends(require_role("admin"))):
    """Fetch a single audit entry by id — used by shareable diff compare links."""
    try:
        oid = ObjectId(entry_id)
    except InvalidId:
        raise HTTPException(400, "Invalid entry id")
    d = await db.admin_audit_log.find_one({"_id": oid})
    if not d:
        raise HTTPException(404, "Audit entry not found")
    return {
        "id": str(d["_id"]),
        "action": d.get("action"),
        "actor_id": d.get("actor_id"),
        "actor_name": d.get("actor_name"),
        "actor_email": d.get("actor_email"),
        "target_type": d.get("target_type"),
        "target_id": d.get("target_id"),
        "target_label": d.get("target_label"),
        "before": d.get("before"),
        "after": d.get("after"),
        "note": d.get("note"),
        "created_at": d.get("created_at"),
        "rollbackable": d.get("action") in ROLLBACKABLE_ACTIONS,
        "pinned": bool(d.get("pinned")),
        "pinned_note": d.get("pinned_note"),
        "pinned_at": d.get("pinned_at"),
        "pinned_by": d.get("pinned_by"),
        "pinned_by_name": d.get("pinned_by_name"),
    }


@router.post("/audit-log/{entry_id}/pin")
async def toggle_pin_audit_entry(
    entry_id: str,
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    """Toggle pin state on an audit entry. Pinned entries surface at top + appear in Pinned Anomalies dashboard widget.
    Body: { pinned: bool (optional, default toggle), note: str (optional, max 240 chars) }
    """
    try:
        oid = ObjectId(entry_id)
    except InvalidId:
        raise HTTPException(400, "Invalid entry id")
    entry = await db.admin_audit_log.find_one({"_id": oid})
    if not entry:
        raise HTTPException(404, "Audit entry not found")

    current_pinned = bool(entry.get("pinned"))
    # Allow explicit pinned value, else toggle
    new_pinned = payload.get("pinned")
    if new_pinned is None:
        new_pinned = not current_pinned
    else:
        new_pinned = bool(new_pinned)

    note = (payload.get("note") or "").strip()[:240] if payload.get("note") else None

    if new_pinned:
        await db.admin_audit_log.update_one(
            {"_id": oid},
            {"$set": {
                "pinned": True,
                "pinned_note": note,
                "pinned_at": datetime.now(timezone.utc).isoformat(),
                "pinned_by": user["id"],
                "pinned_by_name": user.get("name") or user.get("email"),
            }},
        )
    else:
        await db.admin_audit_log.update_one(
            {"_id": oid},
            {"$set": {"pinned": False}, "$unset": {"pinned_note": "", "pinned_at": "", "pinned_by": "", "pinned_by_name": ""}},
        )

    return {"ok": True, "pinned": new_pinned, "pinned_note": note if new_pinned else None}


async def _build_incident_pdf_bytes(entry: dict, base_url: Optional[str], requested_by_label: str) -> bytes:
    """Generate the incident report PDF as bytes. Shared by the download endpoint and the email-report endpoint."""
    # Imports kept local — heavy modules
    import json as _json
    import os as _os
    import qrcode
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT

    # Register Unicode-aware fonts for full Romanian diacritics support (Ț, Ș, Ă, Î, Â)
    BASE_FONT = "Helvetica"
    BOLD_FONT = "Helvetica-Bold"
    MONO_FONT = "Courier"
    OBLIQUE_FONT = "Helvetica-Oblique"
    _dejavu_paths = {
        "DejaVu": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVu-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "DejaVu-Oblique": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "DejaVu-Mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    }
    if _os.path.exists(_dejavu_paths["DejaVu"]):
        try:
            for name, path in _dejavu_paths.items():
                if _os.path.exists(path) and name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
            BASE_FONT = "DejaVu"
            BOLD_FONT = "DejaVu-Bold" if _os.path.exists(_dejavu_paths["DejaVu-Bold"]) else "DejaVu"
            OBLIQUE_FONT = "DejaVu-Oblique" if _os.path.exists(_dejavu_paths["DejaVu-Oblique"]) else "DejaVu"
            MONO_FONT = "DejaVu-Mono" if _os.path.exists(_dejavu_paths["DejaVu-Mono"]) else "DejaVu"
        except Exception as e:  # noqa: BLE001
            logger.warning("PDF font registration failed: %s — falling back to Helvetica", e)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=1.6 * cm, bottomMargin=1.6 * cm,
        title=f"Incident Report — {entry.get('action')}",
        author="PropManage Audit System",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName=BOLD_FONT, fontSize=18, textColor=colors.HexColor("#0f172a"), spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading3"], fontName=BASE_FONT, fontSize=11, textColor=colors.HexColor("#64748b"), spaceAfter=8)
    label = ParagraphStyle("Lbl", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#64748b"), fontName=BOLD_FONT)
    val = ParagraphStyle("Val", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#0f172a"), fontName=BASE_FONT)
    note_style = ParagraphStyle("Note", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#92400e"),
                                fontName=OBLIQUE_FONT, backColor=colors.HexColor("#fef3c7"),
                                borderColor=colors.HexColor("#fbbf24"), borderWidth=0.5,
                                borderPadding=8, leftIndent=4, rightIndent=4)
    diff_style = ParagraphStyle("Diff", parent=styles["Code"], fontSize=8, fontName=MONO_FONT,
                                textColor=colors.HexColor("#0f172a"), leading=10, alignment=TA_LEFT)

    def fmt_value(v):
        if v is None:
            return "—"
        if isinstance(v, (dict, list)):
            try:
                return _json.dumps(v, indent=2, ensure_ascii=False)
            except Exception:
                return str(v)
        return str(v)

    def fmt_dt(iso):
        if not iso:
            return "—"
        try:
            return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M:%S UTC")
        except Exception:
            return str(iso)

    story = []
    story.append(Paragraph("PropManage — Incident Report", h1))
    story.append(Paragraph(f"Audit Entry · {entry.get('action', '—')}", h2))
    story.append(Spacer(1, 6))

    pinned = bool(entry.get("pinned"))
    meta_rows = [
        [Paragraph("ACȚIUNE", label), Paragraph(entry.get("action", "—"), val)],
        [Paragraph("ȚINTĂ", label), Paragraph(f"{entry.get('target_label') or '—'} <font color='#94a3b8'>({entry.get('target_type') or '—'})</font>", val)],
        [Paragraph("ACTOR", label), Paragraph(f"{entry.get('actor_name') or '—'} &lt;{entry.get('actor_email') or '—'}&gt;", val)],
        [Paragraph("DATA EVENIMENT", label), Paragraph(fmt_dt(entry.get("created_at")), val)],
        [Paragraph("ID INTRARE", label), Paragraph(f"<font name='{MONO_FONT}' size='9'>{str(entry['_id'])}</font>", val)],
        [Paragraph("PINNED", label), Paragraph("DA — anomalie marcată" if pinned else "Nu", val)],
    ]
    t = Table(meta_rows, colWidths=[3.5 * cm, 13 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    if pinned:
        pn = entry.get("pinned_note") or "(fără notă)"
        by = entry.get("pinned_by_name") or "—"
        at = fmt_dt(entry.get("pinned_at"))
        story.append(Paragraph(
            f"<b>Notă incident:</b> {pn}<br/><font size='8' color='#a16207'>Marcat de {by} la {at}</font>",
            note_style,
        ))
        story.append(Spacer(1, 12))

    before_txt = fmt_value(entry.get("before"))
    after_txt = fmt_value(entry.get("after"))
    diff_data = [
        [
            Paragraph("<b><font color='#dc2626'>ÎNAINTE</font></b>", val),
            Paragraph("<b><font color='#059669'>DUPĂ</font></b>", val),
        ],
        [
            Paragraph(f"<font name='{MONO_FONT}'>{before_txt.replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br/>') or '— gol —'}</font>", diff_style),
            Paragraph(f"<font name='{MONO_FONT}'>{after_txt.replace('<', '&lt;').replace('>', '&gt;').replace(chr(10), '<br/>') or '— gol —'}</font>", diff_style),
        ],
    ]
    diff_tbl = Table(diff_data, colWidths=[8.5 * cm, 8.5 * cm])
    diff_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, 1), colors.HexColor("#fef2f2")),
        ("BACKGROUND", (1, 0), (1, 1), colors.HexColor("#ecfdf5")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (0, 1), 0.5, colors.HexColor("#fecaca")),
        ("BOX", (1, 0), (1, 1), 0.5, colors.HexColor("#a7f3d0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("<b>Modificare detectată</b>", val))
    story.append(Spacer(1, 4))
    story.append(diff_tbl)
    story.append(Spacer(1, 14))

    if base_url:
        share_url = f"{base_url.rstrip('/')}/admin?audit_focus={str(entry['_id'])}"
        qr_img = qrcode.make(share_url)
        qr_buf = BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        qr_rl = RLImage(qr_buf, width=3 * cm, height=3 * cm)
        qr_table = Table([[qr_rl, Paragraph(
            f"<b>Acces live</b><br/><font size='8'>Scanează codul QR pentru a accesa această intrare în consola admin "
            f"(necesită login admin).</font><br/><br/><font name='{MONO_FONT}' size='7' color='#475569'>{share_url}</font>",
            val,
        )]], colWidths=[3.4 * cm, 13 * cm])
        qr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(KeepTogether([qr_table]))
        story.append(Spacer(1, 12))

    now_str = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    story.append(Paragraph(
        f"<font size='8' color='#94a3b8'>Document generat de <b>PropManage Audit System</b> la {now_str} "
        f"· Solicitat de {requested_by_label} "
        f"· Pentru audituri ISO/SOC2, post-mortems, rapoarte legale</font>",
        val,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


@router.get("/audit-log/{entry_id}/incident-report.pdf")
async def export_incident_report_pdf(
    entry_id: str,
    base_url: Optional[str] = None,
    user: dict = Depends(require_role("admin")),
):
    """Generate a PDF incident report for an audit entry. Designed for pinned anomalies,
    legal documentation, board meetings, post-mortems, and ISO/SOC2 compliance attachments.
    """
    try:
        oid = ObjectId(entry_id)
    except InvalidId:
        raise HTTPException(400, "Invalid entry id")
    entry = await db.admin_audit_log.find_one({"_id": oid})
    if not entry:
        raise HTTPException(404, "Audit entry not found")

    from io import BytesIO
    pdf_bytes = await _build_incident_pdf_bytes(
        entry, base_url, user.get("name") or user.get("email") or "Admin",
    )
    filename = f"incident-report-{entry_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/audit-log/{entry_id}/email-report")
async def email_incident_report(
    entry_id: str,
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Email an incident-report PDF to one or more recipients.
    Body: { recipients: [str, ...] (required, max 10), note: str (optional admin context),
            base_url: str (optional, for QR/deep link) }
    Uses Resend if RESEND_API_KEY is configured, otherwise prints to logs (console fallback).
    """
    import base64
    import re

    try:
        oid = ObjectId(entry_id)
    except InvalidId:
        raise HTTPException(400, "Invalid entry id")
    entry = await db.admin_audit_log.find_one({"_id": oid})
    if not entry:
        raise HTTPException(404, "Audit entry not found")

    recipients_raw = payload.get("recipients") or []
    if isinstance(recipients_raw, str):
        # allow comma-separated
        recipients_raw = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    email_re = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
    recipients = [r for r in recipients_raw if email_re.match(r)]
    invalid = [r for r in recipients_raw if r not in recipients]
    if not recipients:
        raise HTTPException(400, "Niciun destinatar valid. Verifică adresele de email.")
    if len(recipients) > 10:
        raise HTTPException(400, "Maxim 10 destinatari per email.")

    admin_note = (payload.get("note") or "").strip()[:500] or None
    base_url = payload.get("base_url") or None

    # Generate PDF (reuse helper)
    pdf_bytes = await _build_incident_pdf_bytes(
        entry, base_url, user.get("name") or user.get("email") or "Admin",
    )
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    pdf_filename = f"incident-report-{entry_id}.pdf"

    # Format action label + datetime for subject
    action = entry.get("action", "audit")
    target_label = entry.get("target_label") or entry.get("target_type") or "—"
    try:
        evt_dt = datetime.fromisoformat(str(entry.get("created_at")).replace("Z", "+00:00")).strftime("%d %b %Y")
    except Exception:
        evt_dt = ""
    pin_note = entry.get("pinned_note") or ""
    subject_tail = f" — {pin_note[:60]}" if pin_note else ""
    subject = f"[INCIDENT] {action} — {target_label} — {evt_dt}{subject_tail}"

    # Build minimalist HTML body (uses email_service layout)
    from email_service import _layout, send_email as _send_email  # type: ignore

    pinned_html = ""
    if entry.get("pinned"):
        pinned_html = f"""
          <div style="background:#fbbf2415; border-left:3px solid #fbbf24; padding:14px 18px; border-radius:12px; margin:18px 0;">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#fbbf24; margin-bottom:6px;">Notă incident</div>
            <div style="color:#e5e5e5; font-style:italic;">"{pin_note or '(fără notă)'}"</div>
            <div style="color:#888893; font-size:11px; margin-top:6px;">
              Marcat de {entry.get('pinned_by_name') or '—'}
            </div>
          </div>
        """
    admin_note_html = ""
    if admin_note:
        admin_note_html = f"""
          <div style="background:#1a1a1f; border-left:3px solid #d4ff3a; padding:14px 18px; border-radius:12px; margin:18px 0;">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d4ff3a; margin-bottom:6px;">Notă administrator</div>
            <div style="color:#e5e5e5;">{admin_note}</div>
          </div>
        """

    body_html = f"""
      <p>Salut,</p>
      <p>Adminul <strong>{user.get('name') or user.get('email')}</strong> a transmis acest raport de incident generat de PropManage Audit System.</p>
      <table border="0" cellpadding="0" cellspacing="0" style="width:100%; background:#1a1a1f; border-radius:14px; padding:18px; margin:18px 0;">
        <tr><td style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893; padding-bottom:6px;">Acțiune</td><td style="font-size:14px; color:#ffffff; padding-bottom:6px;">{action}</td></tr>
        <tr><td style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893; padding-bottom:6px;">Țintă</td><td style="font-size:14px; color:#ffffff; padding-bottom:6px;">{target_label}</td></tr>
        <tr><td style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893; padding-bottom:6px;">Actor</td><td style="font-size:13px; color:#c8c8cc; padding-bottom:6px;">{entry.get('actor_name') or '—'} &lt;{entry.get('actor_email') or '—'}&gt;</td></tr>
        <tr><td style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893;">Data</td><td style="font-size:13px; color:#c8c8cc;">{evt_dt or '—'}</td></tr>
      </table>
      {pinned_html}
      {admin_note_html}
      <p style="color:#a8a8b0; font-size:13px;">Atașat în acest email găsești PDF-ul cu raportul complet — include diff before/after, codul QR pentru acces live și header de audit ISO/SOC2.</p>
    """
    html = _layout(
        title="Raport de incident",
        preheader=f"Audit entry · {action} · {target_label}",
        body_html=body_html,
    )

    # Build attachment payload (Resend format)
    attachments = [{"filename": pdf_filename, "content": pdf_b64}]

    # Use extended send_email (passes attachments if supported)
    try:
        result = await _send_email(recipients, subject, html, attachments=attachments)
    except TypeError:
        # send_email doesn't support attachments yet — fallback without
        result = await _send_email(recipients, subject, html)
        result["warning"] = "Atașamentul PDF nu a putut fi trimis (provider nu suportă attachments)."

    # Audit log this email send
    await audit("incident.email_sent", user,
                target={"type": "audit_entry", "id": entry_id, "label": f"{action} → {target_label}"},
                note=f"Email trimis către {len(recipients)} destinatar(i) via {result.get('provider', '—')}")

    # Increment preset sent_count if a preset was used + log send history
    preset_id = payload.get("preset_id")
    if preset_id and result.get("ok"):
        try:
            poid = ObjectId(preset_id)
            await db.incident_recipient_presets.update_one(
                {"_id": poid},
                {"$inc": {"sent_count": 1}, "$set": {"last_used_at": datetime.now(timezone.utc).isoformat()}},
            )
            # Record send history for stats per preset
            await db.preset_send_history.insert_one({
                "preset_id": poid,
                "audit_entry_id": entry_id,
                "target_label": target_label,
                "action": action,
                "recipient_count": len(recipients),
                "sent_by": user["id"],
                "sent_by_name": user.get("name") or user.get("email"),
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "provider": result.get("provider"),
            })
        except (InvalidId, Exception):  # noqa: BLE001
            pass

    return {
        "ok": result.get("ok", False),
        "provider": result.get("provider"),
        "recipients": recipients,
        "invalid_recipients": invalid,
        "demo": result.get("demo", False),
        "error": result.get("error"),
        "warning": result.get("warning"),
        "id": result.get("id"),
    }


# ============= RECIPIENT PRESETS =============
# Reusable groups (e.g. "Compliance Team", "Board") for quick-pick in incident email modal.
import re as _re_email

_EMAIL_RE = _re_email.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _sanitize_emails(raw) -> tuple[list[str], list[str]]:
    """Returns (valid_emails_unique, invalid_inputs). Trims, lowercases, dedupes."""
    if isinstance(raw, str):
        raw = [r.strip() for r in raw.split(",")]
    elif not isinstance(raw, list):
        return [], []
    valid, invalid, seen = [], [], set()
    for e in raw:
        if not isinstance(e, str):
            continue
        e = e.strip().lower()
        if not e:
            continue
        if _EMAIL_RE.match(e):
            if e not in seen:
                seen.add(e)
                valid.append(e)
        else:
            invalid.append(e)
    return valid, invalid


def _serialize_preset(d: dict) -> dict:
    return {
        "id": str(d["_id"]),
        "name": d.get("name", "—"),
        "emails": d.get("emails", []),
        "sent_count": int(d.get("sent_count", 0) or 0),
        "created_at": d.get("created_at"),
        "created_by": d.get("created_by"),
        "created_by_name": d.get("created_by_name"),
        "last_used_at": d.get("last_used_at"),
    }


@router.get("/recipient-presets")
async def list_recipient_presets(user: dict = Depends(require_role("admin"))):
    """List all incident-email recipient presets, sorted by most-used first."""
    cursor = db.incident_recipient_presets.find({}).sort([("sent_count", -1), ("created_at", -1)])
    items = [_serialize_preset(d) async for d in cursor]
    return {"items": items, "total": len(items)}


@router.post("/recipient-presets")
async def create_recipient_preset(
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Create a new preset. Body: { name: str, emails: [str] }"""
    name = (payload.get("name") or "").strip()[:80]
    if not name:
        raise HTTPException(400, "Numele presetului este obligatoriu.")
    valid, invalid = _sanitize_emails(payload.get("emails") or [])
    if not valid:
        raise HTTPException(400, "Adaugă cel puțin o adresă de email validă.")
    if len(valid) > 25:
        raise HTTPException(400, "Maxim 25 emailuri per preset.")

    # Dedupe by name (case-insensitive)
    existing = await db.incident_recipient_presets.find_one({"name_lower": name.lower()})
    if existing:
        raise HTTPException(409, f"Un preset cu numele '{name}' există deja.")

    doc = {
        "name": name,
        "name_lower": name.lower(),
        "emails": valid,
        "sent_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user["id"],
        "created_by_name": user.get("name") or user.get("email"),
    }
    res = await db.incident_recipient_presets.insert_one(doc)
    doc["_id"] = res.inserted_id

    await audit("recipient_preset.create", user,
                target={"type": "recipient_preset", "id": str(res.inserted_id), "label": name},
                after={"name": name, "emails": valid},
                note=f"Preset cu {len(valid)} email(uri)")

    return {"ok": True, "preset": _serialize_preset(doc), "invalid_emails": invalid}


@router.patch("/recipient-presets/{preset_id}")
async def update_recipient_preset(
    preset_id: str,
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Update name and/or emails."""
    try:
        oid = ObjectId(preset_id)
    except InvalidId:
        raise HTTPException(400, "Invalid preset id")
    existing = await db.incident_recipient_presets.find_one({"_id": oid})
    if not existing:
        raise HTTPException(404, "Preset inexistent.")

    update = {}
    invalid_emails = []
    if "name" in payload:
        name = (payload.get("name") or "").strip()[:80]
        if not name:
            raise HTTPException(400, "Numele nu poate fi gol.")
        # dedupe except current
        clash = await db.incident_recipient_presets.find_one({"name_lower": name.lower(), "_id": {"$ne": oid}})
        if clash:
            raise HTTPException(409, f"Un preset cu numele '{name}' există deja.")
        update["name"] = name
        update["name_lower"] = name.lower()
    if "emails" in payload:
        valid, invalid_emails = _sanitize_emails(payload.get("emails") or [])
        if not valid:
            raise HTTPException(400, "Cel puțin o adresă validă.")
        if len(valid) > 25:
            raise HTTPException(400, "Maxim 25 emailuri per preset.")
        update["emails"] = valid

    if not update:
        return {"ok": True, "preset": _serialize_preset(existing), "invalid_emails": invalid_emails}

    before = {"name": existing.get("name"), "emails": existing.get("emails", [])}
    await db.incident_recipient_presets.update_one({"_id": oid}, {"$set": update})
    fresh = await db.incident_recipient_presets.find_one({"_id": oid})
    after = {"name": fresh.get("name"), "emails": fresh.get("emails", [])}

    await audit("recipient_preset.update", user,
                target={"type": "recipient_preset", "id": preset_id, "label": fresh.get("name")},
                before=before, after=after)

    return {"ok": True, "preset": _serialize_preset(fresh), "invalid_emails": invalid_emails}


@router.delete("/recipient-presets/{preset_id}")
async def delete_recipient_preset(preset_id: str, user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(preset_id)
    except InvalidId:
        raise HTTPException(400, "Invalid preset id")
    doc = await db.incident_recipient_presets.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Preset inexistent.")
    await db.incident_recipient_presets.delete_one({"_id": oid})
    # Also delete its send history
    await db.preset_send_history.delete_many({"preset_id": oid})
    await audit("recipient_preset.delete", user,
                target={"type": "recipient_preset", "id": preset_id, "label": doc.get("name")},
                before={"name": doc.get("name"), "emails": doc.get("emails", [])})
    return {"ok": True}


@router.get("/recipient-presets/{preset_id}/stats")
async def get_preset_stats(
    preset_id: str,
    days: int = Query(180, ge=30, le=365),
    user: dict = Depends(require_role("admin")),
):
    """Return send history + monthly aggregation for a recipient preset.
    Used by the 'Stats per Preset' panel — incident response cadence insights.
    """
    try:
        oid = ObjectId(preset_id)
    except InvalidId:
        raise HTTPException(400, "Invalid preset id")
    preset = await db.incident_recipient_presets.find_one({"_id": oid})
    if not preset:
        raise HTTPException(404, "Preset inexistent.")

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    # Recent sends (last 10, newest first)
    recent_cursor = db.preset_send_history.find(
        {"preset_id": oid}
    ).sort("sent_at", -1).limit(10)
    recent = []
    async for d in recent_cursor:
        recent.append({
            "audit_entry_id": d.get("audit_entry_id"),
            "target_label": d.get("target_label"),
            "action": d.get("action"),
            "recipient_count": d.get("recipient_count"),
            "sent_by_name": d.get("sent_by_name"),
            "sent_at": d.get("sent_at"),
            "provider": d.get("provider"),
        })

    # Monthly aggregation (YYYY-MM groups) over the requested window
    pipeline = [
        {"$match": {"preset_id": oid, "sent_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"$substr": ["$sent_at", 0, 7]},  # YYYY-MM
            "count": {"$sum": 1},
            "recipient_count_total": {"$sum": "$recipient_count"},
        }},
        {"$sort": {"_id": 1}},
    ]
    months = []
    async for d in db.preset_send_history.aggregate(pipeline):
        months.append({"month": d["_id"], "count": d["count"], "recipients": d["recipient_count_total"]})

    # Fill missing months with zero counts so the chart has continuous bars
    if months:
        from calendar import monthrange  # noqa: F401  (kept light; not actually needed)
        # Build full month list between first and now
        now = datetime.now(timezone.utc)
        first_m = months[0]["month"]
        try:
            y, m = int(first_m[:4]), int(first_m[5:7])
        except Exception:
            y, m = now.year, now.month
        full = []
        existing_map = {x["month"]: x for x in months}
        cur_y, cur_m = y, m
        while (cur_y, cur_m) <= (now.year, now.month):
            key = f"{cur_y:04d}-{cur_m:02d}"
            full.append(existing_map.get(key, {"month": key, "count": 0, "recipients": 0}))
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1
        months = full

    # Aggregate totals
    total_sends = preset.get("sent_count", 0) or 0
    first_send = None
    last_send = preset.get("last_used_at")
    first_doc = await db.preset_send_history.find_one({"preset_id": oid}, sort=[("sent_at", 1)])
    if first_doc:
        first_send = first_doc.get("sent_at")

    return {
        "preset": _serialize_preset(preset),
        "recent_sends": recent,
        "months": months,
        "total_sends": total_sends,
        "first_send": first_send,
        "last_send": last_send,
        "window_days": days,
    }


@router.get("/incident-cadence-heatmap")
async def incident_cadence_heatmap(
    days: int = Query(91, ge=30, le=365),
    user: dict = Depends(require_role("admin")),
):
    """GitHub-style activity heatmap for incident-response cadence across ALL presets.
    Returns daily aggregation for the last `days` days, plus weekday distribution.
    """
    from datetime import timedelta as _td
    today = datetime.now(timezone.utc).date()
    start_date = today - _td(days=days - 1)
    cutoff_iso = start_date.isoformat()  # YYYY-MM-DD compares fine with sent_at prefix

    # Aggregate by day from preset_send_history
    pipeline = [
        {"$match": {"sent_at": {"$gte": cutoff_iso}}},
        {"$group": {
            "_id": {"$substr": ["$sent_at", 0, 10]},  # YYYY-MM-DD
            "count": {"$sum": 1},
            "recipients": {"$sum": "$recipient_count"},
        }},
    ]
    raw = {}
    async for d in db.preset_send_history.aggregate(pipeline):
        raw[d["_id"]] = {"count": d["count"], "recipients": d.get("recipients", 0)}

    # Build full cell series with zero-fill
    cells = []
    weekday_dist = [0] * 7  # Mon=0..Sun=6
    total_sends = 0
    total_recipients = 0
    cur = start_date
    while cur <= today:
        key = cur.isoformat()
        d = raw.get(key, {"count": 0, "recipients": 0})
        cells.append({
            "date": key,
            "count": d["count"],
            "recipients": d["recipients"],
            "weekday": cur.weekday(),  # 0=Mon
        })
        weekday_dist[cur.weekday()] += d["count"]
        total_sends += d["count"]
        total_recipients += d["recipients"]
        cur += _td(days=1)

    # Active days + peak day
    active_days = sum(1 for c in cells if c["count"] > 0)
    peak = max(cells, key=lambda c: c["count"]) if cells else None

    return {
        "cells": cells,
        "days": days,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
        "total_sends": total_sends,
        "total_recipients": total_recipients,
        "active_days": active_days,
        "weekday_dist": weekday_dist,
        "peak": ({"date": peak["date"], "count": peak["count"]} if peak and peak["count"] > 0 else None),
    }


async def _compute_weekly_compare(alert_threshold_pct: int = 100) -> dict:
    """Internal helper — same logic as the endpoint but callable from cron jobs."""
    from datetime import timedelta as _td
    today = datetime.now(timezone.utc).date()
    monday_curr = today - _td(days=today.weekday())
    monday_prev = monday_curr - _td(days=7)
    sunday_prev = monday_curr - _td(days=1)
    sunday_curr = monday_curr + _td(days=6)

    cutoff_iso = monday_prev.isoformat()
    end_iso = (sunday_curr + _td(days=1)).isoformat()

    pipeline = [
        {"$match": {"sent_at": {"$gte": cutoff_iso, "$lt": end_iso}}},
        {"$group": {
            "_id": {"$substr": ["$sent_at", 0, 10]},
            "count": {"$sum": 1},
            "recipients": {"$sum": "$recipient_count"},
        }},
    ]
    raw = {}
    async for d in db.preset_send_history.aggregate(pipeline):
        raw[d["_id"]] = {"count": d["count"], "recipients": d.get("recipients", 0)}

    def _build_week(monday):
        cells, total, total_rec = [], 0, 0
        cur = monday
        for _ in range(7):
            key = cur.isoformat()
            d = raw.get(key, {"count": 0, "recipients": 0})
            cells.append({
                "date": key, "count": d["count"], "recipients": d["recipients"],
                "weekday": cur.weekday(), "is_future": cur > today,
            })
            total += d["count"]
            total_rec += d["recipients"]
            cur += _td(days=1)
        return cells, total, total_rec

    curr_cells, curr_total, curr_rec = _build_week(monday_curr)
    prev_cells, prev_total, prev_rec = _build_week(monday_prev)

    if prev_total == 0:
        delta_pct = None if curr_total > 0 else 0
    else:
        delta_pct = round(((curr_total - prev_total) / prev_total) * 100, 1)

    alert = False
    if delta_pct is not None and delta_pct >= alert_threshold_pct:
        alert = True
    elif delta_pct is None and curr_total > 0:
        alert = True

    return {
        "current": {
            "label": "Săptămâna curentă", "monday": monday_curr.isoformat(), "sunday": sunday_curr.isoformat(),
            "cells": curr_cells, "total_sends": curr_total, "total_recipients": curr_rec,
        },
        "previous": {
            "label": "Săptămâna trecută", "monday": monday_prev.isoformat(), "sunday": sunday_prev.isoformat(),
            "cells": prev_cells, "total_sends": prev_total, "total_recipients": prev_rec,
        },
        "delta_pct": delta_pct,
        "alert": alert,
        "alert_threshold_pct": alert_threshold_pct,
        "today": today.isoformat(),
    }


@router.get("/incident-cadence-weekly-compare")
async def incident_cadence_weekly_compare(
    alert_threshold_pct: int = Query(100, ge=10, le=500),
    user: dict = Depends(require_role("admin")),
):
    """Compare incident-response activity for the current week vs the previous week."""
    return await _compute_weekly_compare(alert_threshold_pct)


# ============= INCIDENT SPIKE AUTO-ALERT (multi-tier severity) =============
# Default tiers for fresh installs. Admin can override via UI.
DEFAULT_ALERT_TIERS = [
    {"name": "warning", "label": "Warning", "color": "#fbbf24", "threshold_pct": 50, "preset_id": None},
    {"name": "high", "label": "High", "color": "#f97316", "threshold_pct": 150, "preset_id": None},
    {"name": "critical", "label": "Critical", "color": "#dc2626", "threshold_pct": 300, "preset_id": None},
]


async def _get_spike_alert_settings() -> dict:
    """Load auto-alert settings. Migrates old single-preset shape → tiered shape automatically."""
    doc = await db.platform_settings.find_one({"_id": "incident_spike_alert"})
    if not doc:
        return {
            "enabled": False,
            "tiers": DEFAULT_ALERT_TIERS,
            "last_sent_week": None,
            "last_result": None,
        }
    tiers = doc.get("tiers")
    if not tiers:
        # Backward-compat: migrate old single-preset config to a single-tier list
        legacy_preset = doc.get("preset_id")
        legacy_thresh = int(doc.get("threshold_pct", 100))
        if legacy_preset:
            tiers = [
                {"name": "warning", "label": "Warning", "color": "#fbbf24",
                 "threshold_pct": legacy_thresh, "preset_id": legacy_preset},
            ] + [t for t in DEFAULT_ALERT_TIERS if t["name"] != "warning"]
        else:
            tiers = DEFAULT_ALERT_TIERS
    return {
        "enabled": bool(doc.get("enabled", False)),
        "tiers": tiers,
        "last_sent_week": doc.get("last_sent_week"),
        "last_result": doc.get("last_result"),
    }


async def _save_spike_alert_settings(updates: dict):
    await db.platform_settings.update_one(
        {"_id": "incident_spike_alert"},
        {"$set": updates},
        upsert=True,
    )


def _classify_tier(delta_pct, tiers: list) -> Optional[dict]:
    """Return the highest-severity tier whose threshold is met, else None.
    Tiers list is ordered low→high. Iterate reversed → return first match.
    """
    if delta_pct is None:
        # Infinite increase: hit highest configured tier (with a preset)
        for t in reversed(tiers):
            if t.get("preset_id"):
                return t
        return None
    for t in reversed(tiers):
        thresh = int(t.get("threshold_pct", 0) or 0)
        if delta_pct >= thresh and t.get("preset_id"):
            return t
    return None


async def _enrich_tiers_with_presets(tiers: list) -> list:
    """Attach preset object to each tier for the UI."""
    out = []
    for t in tiers:
        item = dict(t)
        pid = item.get("preset_id")
        if pid:
            try:
                pdoc = await db.incident_recipient_presets.find_one({"_id": ObjectId(pid)})
                item["preset"] = _serialize_preset(pdoc) if pdoc else None
            except (InvalidId, Exception):  # noqa: BLE001
                item["preset"] = None
        else:
            item["preset"] = None
        out.append(item)
    return out


@router.get("/incident-spike-alert/config")
async def get_spike_alert_config(user: dict = Depends(require_role("admin"))):
    """Read auto-alert configuration for incident spikes (multi-tier)."""
    settings = await _get_spike_alert_settings()
    return {**settings, "tiers": await _enrich_tiers_with_presets(settings["tiers"])}


@router.put("/incident-spike-alert/config")
async def update_spike_alert_config(
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Update auto-alert config. Body: { enabled, tiers: [{name, threshold_pct, preset_id, label, color}] }"""
    updates = {}
    if "enabled" in payload:
        updates["enabled"] = bool(payload["enabled"])

    if "tiers" in payload:
        new_tiers = payload.get("tiers") or []
        if not isinstance(new_tiers, list) or len(new_tiers) == 0:
            raise HTTPException(400, "Tiers trebuie să fie o listă cu cel puțin un element.")
        clean = []
        seen_names = set()
        for raw in new_tiers:
            if not isinstance(raw, dict):
                continue
            name = (raw.get("name") or "").strip().lower()[:24]
            if not name or name in seen_names:
                raise HTTPException(400, "Fiecare tier trebuie să aibă un `name` unic.")
            seen_names.add(name)
            try:
                tp = int(raw.get("threshold_pct", 100))
                if not (10 <= tp <= 1000):
                    raise ValueError()
            except (TypeError, ValueError):
                raise HTTPException(400, f"threshold_pct invalid pentru tier '{name}' (10-1000).")
            pid = raw.get("preset_id") or None
            if pid:
                try:
                    pdoc = await db.incident_recipient_presets.find_one({"_id": ObjectId(pid)})
                    if not pdoc:
                        raise HTTPException(404, f"Presetul tier-ului '{name}' nu există.")
                except InvalidId:
                    raise HTTPException(400, f"preset_id invalid pentru tier '{name}'.")
            clean.append({
                "name": name,
                "label": (raw.get("label") or name.title())[:40],
                "color": (raw.get("color") or "#fbbf24")[:16],
                "threshold_pct": tp,
                "preset_id": pid,
            })
        # Sort tiers ascending by threshold so classification works
        clean.sort(key=lambda x: x["threshold_pct"])
        updates["tiers"] = clean

    if updates:
        old = await _get_spike_alert_settings()
        await _save_spike_alert_settings(updates)
        await audit("incident_spike_alert.config_update", user,
                    target={"type": "platform_setting", "id": "incident_spike_alert", "label": "Auto-alert Incident Spike (multi-tier)"},
                    before={k: old.get(k) for k in updates},
                    after=updates)

    return await get_spike_alert_config(user)


async def _send_spike_alert_email(wc: dict, tier: dict, preset: dict, dry_run: bool = False) -> dict:
    """Send the spike-alert email for a specific severity tier.
    Returns dict with status. If dry_run=True, only generates content, doesn't send.
    """
    delta = wc.get("delta_pct")
    delta_label = "+∞%" if delta is None else f"{'+' if delta > 0 else ''}{delta}%"
    curr_total = wc["current"]["total_sends"]
    prev_total = wc["previous"]["total_sends"]
    week_label = f"{wc['current']['monday']} → {wc['current']['sunday']}"

    tier_emoji = {"warning": "🟡", "high": "🟠", "critical": "🔴"}.get(tier["name"], "⚠️")
    tier_label = (tier.get("label") or tier["name"]).upper()
    accent = tier.get("color") or "#fbbf24"

    subject = f"[INCIDENT SPIKE · {tier_label}] {delta_label} această săptămână ({curr_total} vs {prev_total})"

    # Build mini heatmap as HTML grid
    def _cells_html(cells, base):
        out = []
        for c in cells:
            cnt = c["count"]
            bg = ("#1a1a1f" if c["is_future"]
                  else "#1f2937" if cnt == 0
                  else base)
            out.append(
                f'<td style="width:32px;height:32px;background:{bg};border:1px solid #2a2a30;text-align:center;color:#fff;font-size:11px;font-weight:600;">{cnt or ""}</td>'
            )
        return "".join(out)

    weeks_html = f"""
      <table border="0" cellpadding="0" cellspacing="0" style="background:#1a1a1f; border-radius:14px; padding:18px; margin:18px 0; width:100%;">
        <tr>
          <td style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893; padding-bottom:6px;">Săptămâna trecută ({wc['previous']['monday']} → {wc['previous']['sunday']})</td>
          <td style="text-align:right; font-size:22px; color:#c8c8cc; font-weight:bold; padding-bottom:6px;">{prev_total}</td>
        </tr>
        <tr>
          <td colspan="2" style="padding-bottom:12px;">
            <table border="0" cellpadding="0" cellspacing="2"><tr>{_cells_html(wc['previous']['cells'], '#3b3b42')}</tr></table>
          </td>
        </tr>
        <tr>
          <td style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893; padding-bottom:6px;">Săptămâna curentă ({week_label})</td>
          <td style="text-align:right; font-size:22px; color:{accent}; font-weight:bold; padding-bottom:6px;">{curr_total}</td>
        </tr>
        <tr>
          <td colspan="2">
            <table border="0" cellpadding="0" cellspacing="2"><tr>{_cells_html(wc['current']['cells'], accent)}</tr></table>
          </td>
        </tr>
      </table>
    """

    body_html = f"""
      <p>Bună,</p>
      <p>Sistemul automat de monitoring a detectat un <strong>spike de activitate</strong> de incident response la nivel <strong>{tier_emoji} {tier_label}</strong>:</p>
      <div style="background:{accent}15; border-left:3px solid {accent}; padding:16px 18px; border-radius:12px; margin:18px 0;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:{accent}; margin-bottom:6px;">Variație vs săptămâna trecută · Severitate {tier_label}</div>
        <div style="font-size:32px; font-weight:bold; color:{accent};">{delta_label}</div>
        <div style="color:#a8a8b0; font-size:13px; margin-top:6px;">Prag tier {tier_label}: +{tier['threshold_pct']}%</div>
      </div>
      {weeks_html}
      <p style="color:#a8a8b0; font-size:13px;">Acțiuni recomandate pentru {tier_label}:</p>
      <ul style="color:#c8c8cc; font-size:13px;">
        <li>Verifică deploy-urile și modificările recente.</li>
        <li>Consultă audit log-ul pentru anomalii: <a style="color:#d4ff3a;" href="https://propmanage.ro/admin">consola admin</a></li>
        <li>Distribuie raportul către echipa relevantă dacă e necesar.</li>
      </ul>
    """

    from email_service import _layout, send_email as _send_email  # type: ignore
    html = _layout(
        title=f"{tier_emoji} Spike Activity Detected — {tier_label}",
        preheader=f"{delta_label} vs săpt. trecută",
        body_html=body_html,
    )

    recipients = preset.get("emails", [])
    if not recipients:
        return {"ok": False, "error": "Preset gol — niciun destinatar."}

    if dry_run:
        return {"ok": True, "dry_run": True, "subject": subject, "recipients_count": len(recipients), "tier": tier["name"]}

    result = await _send_email(recipients, subject, html)
    return {
        "ok": result.get("ok", False),
        "provider": result.get("provider"),
        "demo": result.get("demo", False),
        "subject": subject,
        "recipients_count": len(recipients),
        "tier": tier["name"],
        "error": result.get("error"),
    }


async def run_incident_spike_alert_check():
    """Cron job: runs every Monday 08:00 Europe/Bucharest. Picks the highest-severity tier matched.
    Deduplicates by `last_sent_week + tier` (one alert per week per tier max).
    """
    try:
        settings = await _get_spike_alert_settings()
        if not settings.get("enabled"):
            return

        tiers = settings.get("tiers", [])
        configured = [t for t in tiers if t.get("preset_id")]
        if not configured:
            logger.info("[SpikeAlert] enabled but no tier has preset configured — skipping")
            return

        wc = await _compute_weekly_compare(min(int(t.get("threshold_pct", 100)) for t in configured))
        matched = _classify_tier(wc.get("delta_pct"), tiers)
        if not matched:
            logger.info(f"[SpikeAlert] no tier matched (delta={wc.get('delta_pct')}%)")
            return

        # Dedupe: don't send same tier twice for same week
        week_key = wc["current"]["monday"]
        last_week = settings.get("last_sent_week")
        last_tier = (settings.get("last_result") or {}).get("tier")
        if last_week == week_key and last_tier == matched["name"]:
            logger.info(f"[SpikeAlert] already sent tier '{matched['name']}' for week {week_key} — skipping")
            return

        preset_doc = await db.incident_recipient_presets.find_one({"_id": ObjectId(matched["preset_id"])})
        if not preset_doc:
            logger.warning(f"[SpikeAlert] tier '{matched['name']}' preset not found — skipping")
            return
        preset = _serialize_preset(preset_doc)

        result = await _send_spike_alert_email(wc, matched, preset)
        await _save_spike_alert_settings({
            "last_sent_week": week_key,
            "last_result": {
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "ok": result.get("ok"),
                "delta_pct": wc.get("delta_pct"),
                "recipients_count": result.get("recipients_count"),
                "tier": matched["name"],
                "error": result.get("error"),
            },
        })
        await db.admin_audit_log.insert_one({
            "action": "incident_spike_alert.sent",
            "actor_id": "system",
            "actor_name": "Sistem (auto-alert)",
            "actor_email": "system@propmanage.ro",
            "target_type": "platform_setting",
            "target_id": "incident_spike_alert",
            "target_label": f"Spike Alert {week_key} · {matched['name']}",
            "before": None,
            "after": {
                "delta_pct": wc.get("delta_pct"),
                "tier": matched["name"],
                "current_total": wc["current"]["total_sends"],
                "previous_total": wc["previous"]["total_sends"],
            },
            "note": f"Tier {matched['name']} — email către {result.get('recipients_count', 0)} destinatari prin {result.get('provider')}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"[SpikeAlert] sent tier '{matched['name']}' for week {week_key}: delta={wc.get('delta_pct')}% → {result.get('recipients_count')} recipients via {result.get('provider')}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[SpikeAlert] error: {e}")


@router.post("/incident-spike-alert/test")
async def test_spike_alert(
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    """Manually trigger the spike-alert check (for testing).
    Body: { dry_run: bool, force_tier: str (optional — bypasses classification, sends specific tier) }
    """
    settings = await _get_spike_alert_settings()
    tiers = settings.get("tiers", [])
    configured = [t for t in tiers if t.get("preset_id")]
    if not configured:
        raise HTTPException(400, "Niciun tier are preset configurat. Setează unul din UI mai întâi.")

    force_tier_name = payload.get("force_tier")
    wc = await _compute_weekly_compare(min(int(t.get("threshold_pct", 100)) for t in configured))

    if force_tier_name:
        matched = next((t for t in tiers if t["name"] == force_tier_name and t.get("preset_id")), None)
        if not matched:
            raise HTTPException(400, f"Tier '{force_tier_name}' nu există sau nu are preset.")
    else:
        matched = _classify_tier(wc.get("delta_pct"), tiers)
        if not matched:
            return {
                "ok": False,
                "reason": "Niciun tier nu a fost depășit în acest moment",
                "delta_pct": wc.get("delta_pct"),
                "current": wc["current"]["total_sends"],
                "previous": wc["previous"]["total_sends"],
            }

    preset_doc = await db.incident_recipient_presets.find_one({"_id": ObjectId(matched["preset_id"])})
    if not preset_doc:
        raise HTTPException(404, f"Presetul tier-ului '{matched['name']}' nu a fost găsit.")
    preset = _serialize_preset(preset_doc)

    dry_run = bool(payload.get("dry_run"))
    result = await _send_spike_alert_email(wc, matched, preset, dry_run=dry_run)

    if not dry_run and result.get("ok"):
        await audit("incident_spike_alert.manual_test", user,
                    target={"type": "platform_setting", "id": "incident_spike_alert", "label": f"Spike Alert (manual test · {matched['name']})"},
                    after={"delta_pct": wc.get("delta_pct"), "tier": matched["name"], "recipients_count": result.get("recipients_count")},
                    note=f"Test manual tier '{matched['name']}' de către {user.get('name') or user.get('email')}")

    return {"ok": result.get("ok"), "delta_pct": wc.get("delta_pct"), "matched_tier": matched["name"], **result}


@router.post("/audit-log/{entry_id}/rollback")
async def rollback_audit_entry(entry_id: str, user: dict = Depends(require_role("admin"))):
    """Restore the `before` state of an audit entry. Idempotent within reason — creates a new audit entry."""
    try:
        oid = ObjectId(entry_id)
    except InvalidId:
        raise HTTPException(400, "Invalid entry id")
    entry = await db.admin_audit_log.find_one({"_id": oid})
    if not entry:
        raise HTTPException(404, "Audit entry not found")
    action = entry.get("action")
    if action not in ROLLBACKABLE_ACTIONS:
        raise HTTPException(400, f"Acțiunea '{action}' nu poate fi anulată automat.")

    now_iso = datetime.now(timezone.utc).isoformat()

    if action == "cms.update":
        target_key = entry.get("target_id")
        before_value = (entry.get("before") or {}).get("value")
        if not target_key:
            raise HTTPException(400, "Lipsește target_id")
        # Snapshot current to log rollback
        current = await db.cms_content.find_one({"key": target_key})
        current_value = (current or {}).get("value")
        if before_value is None:
            # Originally there was no override → delete current
            await db.cms_content.delete_one({"key": target_key})
        else:
            await db.cms_content.update_one(
                {"key": target_key},
                {"$set": {"key": target_key, "value": before_value, "updated_at": now_iso, "updated_by": user["id"]}},
                upsert=True,
            )
        await audit("cms.rollback", user,
                    target={"type": "cms_key", "id": target_key, "label": target_key},
                    before={"value": current_value},
                    after={"value": before_value},
                    note=f"Rollback to entry {entry_id}")
        return {"ok": True, "restored_to": before_value}

    if action == "cms.reset":
        # Reset deleted → rollback = re-create with the old value
        target_key = entry.get("target_id")
        before_value = (entry.get("before") or {}).get("value")
        if before_value is None:
            raise HTTPException(400, "Nu există valoare de restaurat.")
        current = await db.cms_content.find_one({"key": target_key})
        current_value = (current or {}).get("value")
        await db.cms_content.update_one(
            {"key": target_key},
            {"$set": {"key": target_key, "value": before_value, "updated_at": now_iso, "updated_by": user["id"]}},
            upsert=True,
        )
        await audit("cms.rollback", user,
                    target={"type": "cms_key", "id": target_key, "label": target_key},
                    before={"value": current_value},
                    after={"value": before_value},
                    note=f"Rollback (un-reset) of entry {entry_id}")
        return {"ok": True, "restored_to": before_value}

    if action == "settings.update":
        before_map = entry.get("before") or {}
        if not before_map:
            raise HTTPException(400, "Nu există valori 'înainte' de restaurat.")
        doc = await db.platform_config.find_one({"key": "settings"})
        current = (doc or {}).get("value", {})
        # Snapshot only fields we are rolling back
        snapshot = {k: current.get(k) for k in before_map.keys()}
        merged = {**DEFAULT_SETTINGS, **current, **before_map}
        await db.platform_config.update_one(
            {"key": "settings"},
            {"$set": {"key": "settings", "value": merged, "updated_at": now_iso, "updated_by": user["id"]}},
            upsert=True,
        )
        await audit("settings.rollback", user,
                    target={"type": "platform_settings", "id": "settings", "label": "Platform Settings"},
                    before=snapshot,
                    after=before_map,
                    note=f"Rollback to entry {entry_id}")
        return {"ok": True, "restored_keys": list(before_map.keys())}

    if action == "trust_weights.update":
        before_weights = entry.get("before") or {}
        if not before_weights:
            raise HTTPException(400, "Nu există ponderi vechi de restaurat.")
        total = sum(before_weights.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(400, "Ponderile salvate sunt inconsistente (suma ≠ 1.0).")
        doc = await db.platform_config.find_one({"key": "trust_weights"})
        current = (doc or {}).get("value", {})
        await db.platform_config.update_one(
            {"key": "trust_weights"},
            {"$set": {"key": "trust_weights", "value": before_weights, "updated_at": now_iso, "updated_by": user["id"]}},
            upsert=True,
        )
        await audit("trust_weights.rollback", user,
                    target={"type": "trust_weights", "id": "trust_weights", "label": "Trust Score Algorithm"},
                    before=current,
                    after=before_weights,
                    note=f"Rollback to entry {entry_id}")
        return {"ok": True, "restored_to": before_weights}

    raise HTTPException(400, "Acțiune nesuportată pentru rollback.")

