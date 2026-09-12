"""Adaptive UX 2026 — Maturity levels & onboarding checklist endpoints.

Maturity levels for specialists determine progressive UI disclosure:
- ``beginner``     : not verified OR 0 accepted leads.
  UI exposes: profil, verificare, documente, mesaje, comenzi primite.
- ``intermediate`` : verified AND 1+ accepted lead.
  Adds: statistici, ofertare, marketing.
- ``advanced``     : verified AND 10+ completed leads.
  Adds: automatizări, AI suggestions, optimizări financiare.

Onboarding checklist:
- Per role, persisted on ``user.onboarding_checklist[]`` (list of completed step ids).
- Backend exposes default templates per role + endpoint to mark step done.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import get_current_user, require_role

logger = logging.getLogger("propmanage.adaptive_ux")

router = APIRouter(prefix="/api/ux", tags=["adaptive-ux"])
admin_router = APIRouter(prefix="/api/admin/ux", tags=["adaptive-ux-admin"])


# ============================================================================
# Maturity computation (specialist-only for now)
# ============================================================================
async def compute_maturity_for_user(user_doc: dict) -> str:
    """Pure function — derives maturity from user state + lead counters."""
    if user_doc.get("role") != "specialist":
        return "n_a"
    verified = bool(user_doc.get("verified"))
    if not verified:
        return "beginner"
    # Count accepted + completed leads from requests collection
    uid = str(user_doc["_id"])
    accepted = await db.requests.count_documents({"specialist_id": uid, "status": {"$in": ["in_progress", "completed", "review"]}})
    completed = await db.requests.count_documents({"specialist_id": uid, "status": "completed"})
    # Admin override has priority
    override = user_doc.get("maturity_override")
    if override in ("beginner", "intermediate", "advanced"):
        return override
    if completed >= 10:
        return "advanced"
    if accepted >= 1:
        return "intermediate"
    return "beginner"


@router.get("/me/maturity")
async def my_maturity(user=Depends(get_current_user)):
    """Returns current maturity level + counters + next unlock criteria."""
    full = await db.users.find_one({"_id": ObjectId(user["id"])})
    level = await compute_maturity_for_user(full or {})
    # Counters
    uid = user["id"]
    accepted = await db.requests.count_documents({"specialist_id": uid, "status": {"$in": ["in_progress", "completed", "review"]}}) if user.get("role") == "specialist" else 0
    completed = await db.requests.count_documents({"specialist_id": uid, "status": "completed"}) if user.get("role") == "specialist" else 0
    # Persist level on the user doc so other endpoints can read it cheaply
    if user.get("role") == "specialist" and full and full.get("maturity_level") != level:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"maturity_level": level, "maturity_computed_at": datetime.now(timezone.utc).isoformat()}})
    next_unlock = None
    if user.get("role") == "specialist":
        if level == "beginner":
            next_unlock = {
                "target": "intermediate",
                "criteria": "Verifică contul + acceptă primul lead.",
                "progress": {"verified": bool((full or {}).get("verified")), "leads_accepted": accepted},
            }
        elif level == "intermediate":
            next_unlock = {
                "target": "advanced",
                "criteria": "Finalizează 10 lucrări (curent: {}).".format(completed),
                "progress": {"leads_completed": completed, "target": 10},
            }
    return {
        "role": user.get("role"),
        "maturity_level": level,
        "counters": {"leads_accepted": accepted, "leads_completed": completed},
        "next_unlock": next_unlock,
        "override_active": bool((full or {}).get("maturity_override")),
    }


class MaturityOverrideIn(BaseModel):
    user_email: str
    level: Optional[str] = None  # beginner|intermediate|advanced or None=clear


@admin_router.post("/maturity-override")
async def admin_override_maturity(payload: MaturityOverrideIn, user=Depends(require_role("admin"))):
    if payload.level and payload.level not in ("beginner", "intermediate", "advanced"):
        raise HTTPException(400, "Level invalid.")
    target = await db.users.find_one({"email": payload.user_email})
    if not target:
        raise HTTPException(404, "Utilizator inexistent.")
    update = {"maturity_override": payload.level} if payload.level else {"maturity_override": None}
    await db.users.update_one({"_id": target["_id"]}, {"$set": update})
    return {"ok": True, "user_email": payload.user_email, "override": payload.level}


# ============================================================================
# Onboarding checklist
# ============================================================================
CHECKLIST_TEMPLATES = {
    "client": [
        {"id": "client_profile", "title": "Completează profilul", "icon": "👤", "cta_route": "/client?tab=settings"},
        {"id": "client_first_property", "title": "Adaugă o proprietate", "icon": "🏠", "cta_route": "/client?tab=property"},
        {"id": "client_notifications", "title": "Activează notificările", "icon": "🔔", "cta_route": "/client?tab=settings"},
        {"id": "client_first_request", "title": "Creează prima cerere", "icon": "📝", "cta_route": "/client?tab=request"},
        {"id": "client_explore_hh", "title": "Explorează House Health (opțional)", "icon": "❤", "cta_route": "/house-health/upgrade", "optional": True},
        {"id": "client_explore_twin", "title": "Activează Digital Twin (opțional)", "icon": "🏗", "cta_route": "/digital-twin", "optional": True},
    ],
    "specialist": [
        {"id": "spec_profile", "title": "Completează profilul", "icon": "👤", "cta_route": "/specialist?tab=settings"},
        {"id": "spec_documents", "title": "Încarcă documentele obligatorii", "icon": "📄", "cta_route": "/specialist?tab=settings"},
        {"id": "spec_kyc", "title": "Verifică identitatea", "icon": "🪪", "cta_route": "/specialist?tab=settings"},
        {"id": "spec_services", "title": "Configurează serviciile + zone", "icon": "🔧", "cta_route": "/specialist?tab=settings"},
        {"id": "spec_first_offer", "title": "Trimite prima ofertă", "icon": "💼", "cta_route": "/specialist?tab=opportunities"},
        {"id": "spec_notifications", "title": "Activează notificările push", "icon": "🔔", "cta_route": "/specialist?tab=notifications"},
    ],
}


@router.get("/checklist")
async def my_checklist(user=Depends(get_current_user)):
    role = user.get("role")
    template = CHECKLIST_TEMPLATES.get(role, [])
    if not template:
        return {"role": role, "items": [], "completed": 0, "total": 0, "percent": 0}
    full = await db.users.find_one({"_id": ObjectId(user["id"])})
    done = set((full or {}).get("onboarding_checklist") or [])
    items = []
    for step in template:
        items.append({**step, "completed": step["id"] in done})
    completed = sum(1 for it in items if it["completed"])
    total = len(items)
    return {
        "role": role,
        "items": items,
        "completed": completed,
        "total": total,
        "percent": int(round(100 * completed / total)) if total else 0,
        "dismissed": bool((full or {}).get("onboarding_dismissed")),
    }


class StepIn(BaseModel):
    step_id: str
    done: bool = True


@router.post("/checklist/step")
async def mark_step(payload: StepIn, user=Depends(get_current_user)):
    role = user.get("role")
    valid_ids = {s["id"] for s in CHECKLIST_TEMPLATES.get(role, [])}
    if payload.step_id not in valid_ids:
        raise HTTPException(400, "step_id necunoscut pentru rolul tău.")
    op = "$addToSet" if payload.done else "$pull"
    await db.users.update_one({"_id": ObjectId(user["id"])}, {op: {"onboarding_checklist": payload.step_id}})
    return {"ok": True, "step_id": payload.step_id, "done": payload.done}


@router.post("/checklist/dismiss")
async def dismiss_checklist(user=Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"onboarding_dismissed": True, "onboarding_dismissed_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True}
