"""Admin Zones — separarea Business Administration vs Infrastructure & Development.

Stare: PREPARED (permisiunile pe zone NU sunt încă enforced — toți adminii
actuali văd ambele zone). Registrul de zone + roluri este sursa de adevăr
pentru activarea ulterioară a permisiunilor.

Oglindit în frontend: /app/frontend/src/config/adminZones.js

Endpoints:
  GET  /api/admin/admin-zones          — registrul complet (zone + roluri)
  GET  /api/admin/admin-zones/me       — zonele curente ale adminului logat
  POST /api/admin/admin-zones/assign   — asignează zone_role unui admin (super-admin + cod master)
"""
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.admin_zones")
router = APIRouter(prefix="/api/admin/admin-zones", tags=["admin-zones"])

MASTER_CODE = os.environ.get("DEMO_MASTER_CODE", "0108")

ENFORCEMENT = "active"  # "prepared" → toți adminii văd ambele zone; "active" → enforce

ZONES = {
    "business": {
        "id": "business",
        "label": "Business Administration",
        "description": "Utilizatori, Marketplace, Cereri & Proiecte, Financiar, Conținut, Marketing, Suport, Statistici",
    },
    "infrastructure": {
        "id": "infrastructure",
        "label": "Infrastructure & Development",
        "description": "Sistem, Bază de date, API, Email/DNS, Storage, Security, Monitoring, Development",
    },
}

ZONE_ROLES = {
    "business_administrator": {"label": "Business Administrator", "zones": ["business"]},
    "operations_manager": {"label": "Operations Manager", "zones": ["business"]},
    "finance_manager": {"label": "Finance Manager", "zones": ["business"]},
    "marketplace_manager": {"label": "Marketplace Manager", "zones": ["business"]},
    "support_manager": {"label": "Support Manager", "zones": ["business"]},
    "content_manager": {"label": "Content Manager", "zones": ["business"]},
    "infrastructure_administrator": {"label": "Infrastructure Administrator", "zones": ["infrastructure"]},
    "developer": {"label": "Developer", "zones": ["infrastructure"]},
    "devops": {"label": "DevOps", "zones": ["infrastructure"]},
    "system_administrator": {"label": "System Administrator", "zones": ["infrastructure"]},
    "super_admin": {"label": "Super Admin", "zones": ["business", "infrastructure"]},
}


def _require_admin(user: dict) -> None:
    if user.get("role") not in {"admin", "super_admin"}:
        raise HTTPException(403, "Acces permis doar adminilor.")


class AssignZoneRoleReq(BaseModel):
    email: EmailStr
    zone_role: str
    master_code: str


@router.get("")
async def get_zones_registry(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return {"zones": ZONES, "roles": ZONE_ROLES, "enforcement": ENFORCEMENT}


@router.get("/me")
async def get_my_zones(user: dict = Depends(get_current_user)):
    _require_admin(user)
    zone_role: Optional[str] = user.get("zone_role")
    role_def = ZONE_ROLES.get(zone_role or "")
    if ENFORCEMENT != "active" or is_super_admin(user) or not role_def:
        # Super-adminii și adminii FĂRĂ zone_role asignat păstrează acces complet
        # (nu blocăm pe nimeni implicit — enforcement doar pe roluri asignate explicit).
        zones = ["business", "infrastructure"]
    else:
        zones = role_def["zones"]
    return {"zones": zones, "zone_role": zone_role, "enforcement": ENFORCEMENT}


@router.post("/assign")
async def assign_zone_role(req: AssignZoneRoleReq, user: dict = Depends(get_current_user)):
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super-admin poate asigna roluri de zonă.")
    if (req.master_code or "").strip() != MASTER_CODE:
        raise HTTPException(403, "Cod master incorect.")

    target = await db.users.find_one({"email": req.email})
    if not target:
        raise HTTPException(404, f"Nu există utilizator cu emailul {req.email}.")

    if req.zone_role == "none":
        # Elimină rolul de zonă → contul revine la acces complet (ambele zone)
        await db.users.update_one(
            {"email": req.email},
            {"$unset": {"zone_role": "", "admin_zones": ""},
             "$set": {"zone_role_assigned_at": datetime.now(timezone.utc).isoformat(),
                      "zone_role_assigned_by": user.get("email")}},
        )
        logger.info("Zone role ȘTERS pentru %s de către %s", req.email, user.get("email"))
        return {"ok": True, "email": req.email, "zone_role": None,
                "admin_zones": ["business", "infrastructure"], "enforcement": ENFORCEMENT,
                "note": "Rol de zonă eliminat — acces complet la ambele zone."}

    if req.zone_role not in ZONE_ROLES:
        raise HTTPException(400, f"Rol necunoscut: {req.zone_role}. Valide: {sorted(ZONE_ROLES)}")

    role_def = ZONE_ROLES[req.zone_role]
    await db.users.update_one(
        {"email": req.email},
        {"$set": {
            "zone_role": req.zone_role,
            "admin_zones": role_def["zones"],
            "zone_role_assigned_at": datetime.now(timezone.utc).isoformat(),
            "zone_role_assigned_by": user.get("email"),
        }},
    )
    logger.info("Zone role '%s' asignat pentru %s de către %s", req.zone_role, req.email, user.get("email"))
    return {
        "ok": True,
        "email": req.email,
        "zone_role": req.zone_role,
        "admin_zones": role_def["zones"],
        "enforcement": ENFORCEMENT,
        "note": "Rol salvat. Enforcement-ul pe zone va fi activat ulterior.",
    }
