"""App-wide Settings — centralized configuration for social links, pricing,
commissions, contact info, and other knobs that admin needs to control
WITHOUT code changes.

Single MongoDB document with `_id = "app_settings"`.
All endpoints are admin/operator-gated except the public GET subset.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from core_utils import serialize_doc

logger = logging.getLogger("propmanage.app_settings")

router = APIRouter(prefix="/api/admin/app-settings", tags=["admin-settings"])
public_router = APIRouter(prefix="/api/app-settings", tags=["app-settings-public"])


DEFAULT_SETTINGS = {
    "_id": "app_settings",
    "social": {
        "facebook_main": "https://www.facebook.com/share/1GEh9j9wDF/",
        "facebook_estate": "",
        "instagram_main": "",
        "instagram_estate": "",
        "youtube": "",
        "linkedin": "",
    },
    "pricing": {
        "audit_ron": 350.0,
        "twin_ron": 950.0,
        "commission_pct": 2.5,
    },
    "contact": {
        "email": "contact@propmanage.ro",
        "phone": "",
        "address": "",
    },
    "company": {
        "name": "PropManage",
        "tagline": "Property Operating System",
    },
    "seo": {
        "home_title": "PropManage · Proprietatea ta, perfecționată digital",
        "home_description": "Audit tehnic + Digital Twin 3D pentru fiecare imobil. Comision 2.5%. Cumpără cu încredere. Vinde cu credibilitate.",
        "estate_title": "Imobile Verificate · Audit + Digital Twin · PropManage",
        "estate_description": "Imobile premium cu audit tehnic și Digital Twin 3D. Vezi exact ce cumperi înainte de prima vizionare.",
        "whyus_title": "De ce PropManage · Imobile cu Audit + Digital Twin · Comision 2.5%",
        "whyus_description": "O platformă imobiliară unde fiecare imobil are audit + Digital Twin obligatorii. Comision 2.5%. Mai puține surprize.",
        "sell_title": "Vinde-ți imobilul cu PropManage · Comision 2.5%",
        "sell_description": "Audit + Digital Twin + listing public verificat. Te ajutăm să vinzi mai repede și la preț corect. Comision avantajos.",
        "client_title": "Spațiul tău · PropManage",
        "client_description": "Gestionează-ți proprietățile, urmărește audituri și Digital Twin-uri, vezi rapoartele tale.",
        "specialist_title": "Workspace Specialist · PropManage",
        "specialist_description": "Programări audituri, creare Digital Twin, raporte și recomandări către clienți.",
        "og_image": "",
    },
    "updated_at": None,
    "updated_by": None,
}


async def get_or_init_settings() -> dict:
    """Idempotent — returns settings doc, creating defaults on first call."""
    doc = await db.app_settings.find_one({"_id": "app_settings"})
    if not doc:
        doc = {**DEFAULT_SETTINGS, "updated_at": datetime.now(timezone.utc)}
        await db.app_settings.insert_one(doc)
    # Backfill any missing keys for forward compatibility
    changed = False
    for top_key, default_val in DEFAULT_SETTINGS.items():
        if top_key in ("_id", "updated_at", "updated_by"):
            continue
        if top_key not in doc:
            doc[top_key] = default_val
            changed = True
        elif isinstance(default_val, dict):
            for sub_key, sub_default in default_val.items():
                if sub_key not in doc[top_key]:
                    doc[top_key][sub_key] = sub_default
                    changed = True
    if changed:
        await db.app_settings.update_one({"_id": "app_settings"}, {"$set": doc})
    return doc


# ---------- Schemas ----------

class SocialLinks(BaseModel):
    facebook_main: Optional[str] = ""
    facebook_estate: Optional[str] = ""
    instagram_main: Optional[str] = ""
    instagram_estate: Optional[str] = ""
    youtube: Optional[str] = ""
    linkedin: Optional[str] = ""


class PricingSettings(BaseModel):
    audit_ron: float = Field(..., ge=0)
    twin_ron: float = Field(..., ge=0)
    commission_pct: float = Field(..., ge=0, le=100)


class ContactSettings(BaseModel):
    email: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""


class CompanySettings(BaseModel):
    name: Optional[str] = ""
    tagline: Optional[str] = ""


class SEOSettings(BaseModel):
    home_title: Optional[str] = None
    home_description: Optional[str] = None
    estate_title: Optional[str] = None
    estate_description: Optional[str] = None
    whyus_title: Optional[str] = None
    whyus_description: Optional[str] = None
    sell_title: Optional[str] = None
    sell_description: Optional[str] = None
    client_title: Optional[str] = None
    client_description: Optional[str] = None
    specialist_title: Optional[str] = None
    specialist_description: Optional[str] = None
    og_image: Optional[str] = None


class FounderContact(BaseModel):
    """Primary owner contact — used for critical alerts + dual-verification gates."""
    name: Optional[str] = ""
    email: Optional[str] = ""
    backup_email: Optional[str] = ""  # secondary recipient for security/data alerts
    phone: Optional[str] = ""
    country: Optional[str] = "RO"
    is_primary_owner: Optional[bool] = True
    sms_verification_enabled: Optional[bool] = False  # toggle when Twilio is integrated


class AppSettingsUpdate(BaseModel):
    social: Optional[SocialLinks] = None
    pricing: Optional[PricingSettings] = None
    contact: Optional[ContactSettings] = None
    company: Optional[CompanySettings] = None
    seo: Optional[SEOSettings] = None
    founder_contact: Optional[FounderContact] = None
    enable_founder_gate: Optional[bool] = None  # Founder Approval Gate feature flag (default OFF)


# ---------- Public (read-only safe subset) ----------

@public_router.get("/public")
async def get_public_settings():
    """Public read-only subset used by Footer / public pages."""
    doc = await get_or_init_settings()
    return {
        "social": doc.get("social", {}),
        "pricing": doc.get("pricing", {}),
        "contact": {"email": doc.get("contact", {}).get("email", "")},
        "company": doc.get("company", {}),
        "seo": doc.get("seo", {}),
    }


# ---------- Admin ----------

@router.get("")
async def get_all_settings(user: dict = Depends(require_role("admin", "operator"))):
    doc = await get_or_init_settings()
    return serialize_doc(doc)


@router.put("")
async def update_settings(body: AppSettingsUpdate, user: dict = Depends(require_role("admin", "operator"))):
    """Partial update — only fields present in payload are modified."""
    update: Dict[str, Any] = {}
    payload = body.model_dump(exclude_none=True)
    for section, section_value in payload.items():
        if isinstance(section_value, dict):
            for sub_key, sub_value in section_value.items():
                update[f"{section}.{sub_key}"] = sub_value
    if not update:
        raise HTTPException(400, "No fields provided")
    update["updated_at"] = datetime.now(timezone.utc)
    update["updated_by"] = str(user.get("id") or user.get("email"))
    await db.app_settings.update_one({"_id": "app_settings"}, {"$set": update}, upsert=True)
    doc = await db.app_settings.find_one({"_id": "app_settings"})
    # settings_store sync (2.2): oglindim în registrul unificat `settings`
    try:
        from settings_store import put_settings
        await put_settings("app", {k: v for k, v in doc.items() if k != "_id"}, who=update["updated_by"])
    except Exception as e:  # noqa: BLE001
        logging.getLogger("propmanage.app_settings").warning(f"settings_store sync fail: {e}")
    return serialize_doc(doc)


@router.post("/reset")
async def reset_settings(user: dict = Depends(require_role("admin"))):
    """Reset to factory defaults (admin only — destructive)."""
    now = datetime.now(timezone.utc)
    fresh = {**DEFAULT_SETTINGS, "updated_at": now, "updated_by": str(user.get("id"))}
    await db.app_settings.replace_one({"_id": "app_settings"}, fresh, upsert=True)
    return serialize_doc(fresh)
