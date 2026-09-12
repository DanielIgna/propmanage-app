"""PropManage — Digital Twin module (Phase A: infrastructure).

Isolated module. Touches only its own collections:
  - digital_twin_projects
  - digital_twin_models  (placeholder, real upload comes in Phase B)
  - digital_twin_pins
  - digital_twin_comments

Subscription gate: user.digital_twin_pro == True (admin grants for now;
Stripe wiring is Phase E). Admin and operator can bypass.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
import base64
import io
import os
import re
import shutil
import uuid

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Body, Query, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger("propmanage.digital_twin")

from db import db
from deps import get_current_user, require_role
from core_utils import JWT_SECRET, JWT_ALGORITHM
import jwt as _jwt
import asyncio
import cloudconvert_client as _ccv
import blender_service as _blender
from email_service import (
    send_template,
    tpl_dt_pin_created,
    tpl_dt_comment_added,
    tpl_dt_pin_status_changed,
    tpl_dt_model_uploaded,
    tpl_dt_plan_uploaded,
    tpl_dt_issue_report,
    send_email_with_attachments,
)
from services import notify, log_event

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])


# ----------------- storage config -----------------

UPLOAD_ROOT = Path(os.environ.get("DT_UPLOAD_DIR") or "/app/backend/uploads/digital_twin")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = {".glb", ".gltf", ".skp", ".dae", ".obj", ".fbx", ".stl", ".ply"}
ALLOWED_PLAN_EXTS = {".pdf"}
# Extensions that can't be rendered in-browser; we store them as downloadable archives only.
DOWNLOAD_ONLY_EXTS = {".skp"}
# Extensions Blender can auto-convert to .glb headless on Linux
BLENDER_CONVERT_EXTS = {".dae", ".obj", ".fbx", ".stl", ".ply"}
import storage_service  # noqa: E402 — ST-001: limite dinamice + cote DT (bucket separat)

PLAN_TYPES = {"floorplan", "section", "elevation", "detail", "site", "other"}


# ----------------- helpers -----------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _user_filter(user_id: str) -> dict:
    """Build a Mongo filter that matches a user by id (string or ObjectId hex)."""
    try:
        return {"_id": ObjectId(user_id)}
    except (InvalidId, TypeError):
        return {"id": user_id}


async def _has_dt_access(user: dict) -> bool:
    """User has Digital Twin Advanced access?

    Sursă unică: entitlement layer (`F_DIGITAL_TWIN_ADVANCED`).
    Fallback: flag legacy `digital_twin_pro` acordat manual de admin (compatibilitate).
    Admin/operator/franchise_admin bypass automat prin entitlement layer.
    """
    # Sursă principală — entitlement layer
    try:
        from entitlements import F_DIGITAL_TWIN_ADVANCED, get_user_entitlements
        ent = await get_user_entitlements(user)
        if F_DIGITAL_TWIN_ADVANCED in set(ent.get("features") or []):
            return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[digital_twin] entitlement layer failed, fallback to legacy flag: %s", e)
    # Fallback legacy — flag setat manual pe user (nu spargem accesul preexistent)
    fresh = await db.users.find_one(_user_filter(user["id"]), {"digital_twin_pro": 1})
    return bool(fresh and fresh.get("digital_twin_pro"))


async def _ensure_dt_access(user: dict) -> None:
    if not await _has_dt_access(user):
        # Semantic corect: 402 Payment Required (același contract ca celelalte gate-uri)
        raise HTTPException(
            status_code=402,
            detail={
                "error": "entitlement_required",
                "feature": "digital_twin_advanced",
                "message": "Editarea avansată a Digital Twin necesită un plan eligibil. Activează planul potrivit pentru a continua.",
            },
        )


async def _ensure_dt_ingest_access(user: dict) -> None:
    """Decizia Fondator #4: aducerea/stocarea/versionarea modelului profesional PROPRIU NU e blocată
    de PREMIUM. Orice utilizator autentificat își poate crea containerul de proiect și încărca/gestiona
    modelul; proprietatea e verificată separat (_ensure_project_access). Funcțiile AVANSATE de
    vizualizare/exploatare (pins, comentarii, issue-reports, colaboratori, AI Q&A, retry conversii)
    rămân gated PREMIUM prin _ensure_dt_access.
    """
    if not user or not user.get("id"):
        raise HTTPException(status_code=401, detail="Autentificare necesară.")


# P1 — ProfessionalModel metadata: valori deterministe permise
_MODEL_STATUSES = {"processing", "ready", "stored", "superseded", "archived"}
# Vizibilitate minimă & deterministă (decizia #2): implicit intern (owner + operator + specialist asignat);
# `public` = opt-in explicit al proprietarului (expunere pe pașaportul public — nu implicit).
_MODEL_VISIBILITIES = {"internal", "public"}

# P0/STEP D — Trust & provenance readiness (pregătire pt AI-3D / import / professional; NU un al doilea maturity).
_MODEL_CONFIDENCE = {"inferred", "documented", "verified"}
_MODEL_VERIFICATION = {"owner_declared", "official_document", "professional_audit", "verified"}
_MODEL_SOURCES = {"owner_upload", "owner_declared", "uploaded", "specialist", "professional", "platform", "ai_generated", "imported"}


async def _resolve_property_anchor(property_id, user: dict, owner_id=None):
    """P0 — verifică ancora de proprietate a unui Digital Twin.

    Returnează (property_id | None, link_status). NU atribuie NICIODATĂ o proprietate care nu
    aparține contextului contului (anti-misassignment, regula Fondator). `owner_id` = proprietarul
    real al proiectului (ex: operator care creează pentru un client).
    """
    if not property_id:
        return None, "unresolved"
    try:
        prop = await db.properties.find_one({"_id": ObjectId(property_id)})
    except Exception:
        prop = None
    if not prop:
        raise HTTPException(404, "Proprietatea nu există.")
    role = user.get("active_view") or user.get("role")
    expected_owner = owner_id or (None if role in ("admin", "operator") else user["id"])
    if expected_owner is not None and str(prop.get("owner_id")) != str(expected_owner):
        raise HTTPException(403, "Proprietatea nu aparține contextului contului.")
    return property_id, "linked"


async def _kg_link_twin(property_id, node_type: str, node_id):
    """P0/STEP C — muchie SEMANTICĂ în Knowledge Graph (FK-ul rămâne pt integritate).

    KG = traversare de cunoaștere; FK = integritate/ownership. Nu înlocuim FK-urile cu KG.
    """
    if not (property_id and node_id):
        return
    try:
        from kg.links import link as _kg
        rel = "has_twin_project" if node_type == "twin_project" else "has_twin_model"
        await _kg("property", str(property_id), rel, node_type, str(node_id))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[kg] twin link failed ({node_type} {node_id}): {e}")


async def _ensure_project_access(project_id: str, user: dict) -> dict:
    """Returns project doc if user is owner, member, or admin/operator."""
    p = await db.digital_twin_projects.find_one({"id": project_id})
    if not p:
        raise HTTPException(404, "Project not found.")
    if user.get("role") in ("admin", "operator"):
        return p
    if p.get("owner_id") == user["id"]:
        return p
    members = p.get("members") or []
    if any(m.get("user_id") == user["id"] for m in members):
        return p
    raise HTTPException(403, "No access to this project.")


async def _project_stakeholders(project: dict, exclude_user_id: str | None = None) -> list:
    """All people who should be notified about a project event: owner + members.
    Excludes the actor and any without email. Returns list of {id, name, email}."""
    ids = [project.get("owner_id")]
    for m in (project.get("members") or []):
        if m.get("user_id"):
            ids.append(m["user_id"])
    ids = [i for i in ids if i and i != exclude_user_id]
    if not ids:
        return []
    out = []
    seen = set()
    for uid in ids:
        if uid in seen:
            continue
        seen.add(uid)
        u = await db.users.find_one(_user_filter(uid), {"_id": 1, "email": 1, "name": 1})
        if u and u.get("email"):
            out.append({"id": str(u["_id"]), "name": u.get("name") or u["email"], "email": u["email"]})
    return out


def _clean(d: dict) -> dict:
    """Remove Mongo _id before returning."""
    d.pop("_id", None)
    return d


# ----------------- subscription check -----------------

@router.get("/subscription")
async def my_subscription(user: dict = Depends(get_current_user)):
    """Tell the frontend whether user can access Digital Twin Advanced."""
    has = await _has_dt_access(user)
    tier_label = None
    tier = None
    try:
        from entitlements import get_user_entitlements
        ent = await get_user_entitlements(user)
        tier = ent.get("tier")
        tier_label = ent.get("tier_label")
    except Exception:  # noqa: BLE001
        pass
    return {
        "active": has,
        "reason": "role_bypass" if user.get("role") in ("admin", "operator") else ("entitled" if has else "inactive"),
        "tier": tier,
        "tier_label": tier_label,
        "required_feature": "digital_twin_advanced",
        "can_ingest": True,
        "cta_href": "/pricing",
    }


# ----------------- projects -----------------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    property_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)
    model_url: Optional[str] = Field(None, max_length=2000)  # Phase B: external .glb URL
    trimble_embed_url: Optional[str] = Field(None, max_length=2000)  # Trimble Connect 3D viewer share URL


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    model_url: Optional[str] = Field(None, max_length=2000)
    trimble_embed_url: Optional[str] = Field(None, max_length=2000)


@router.post("/projects")
async def create_project(payload: ProjectCreate, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    prop_anchor, link_status = await _resolve_property_anchor(payload.property_id, user)
    pid = _new_id()
    now = _now_iso()
    doc = {
        "id": pid,
        "name": payload.name.strip(),
        "property_id": prop_anchor,
        "property_link_status": link_status,
        "description": (payload.description or "").strip(),
        "model_url": (payload.model_url or "").strip() or None,
        "trimble_embed_url": (payload.trimble_embed_url or "").strip() or None,
        "owner_id": user["id"],
        "owner_name": user.get("name") or user.get("email"),
        "members": [],
        "model_count": 0,
        "plan_count": 0,
        "pin_count": 0,
        "created_at": now,
        "updated_at": now,
    }
    await db.digital_twin_projects.insert_one(doc)
    await _kg_link_twin(prop_anchor, "twin_project", pid)
    return _clean(doc)


class ProjectPropertyLink(BaseModel):
    property_id: str


@router.patch("/projects/{project_id}/property")
async def link_project_property(project_id: str, payload: ProjectPropertyLink,
                                user: dict = Depends(get_current_user)):
    """P0 — ancorează un proiect existent (unresolved) de o proprietate, verificat pe ownership.

    Cascadează property_id + status și pe modelele proiectului și scrie muchiile KG. Non-destructiv.
    """
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Doar proprietarul proiectului poate seta proprietatea.")
    prop_anchor, link_status = await _resolve_property_anchor(payload.property_id, user, owner_id=p.get("owner_id"))
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"property_id": prop_anchor, "property_link_status": link_status, "updated_at": _now_iso()}},
    )
    await db.digital_twin_models.update_many(
        {"project_id": project_id},
        {"$set": {"property_id": prop_anchor, "property_link_status": link_status}},
    )
    await _kg_link_twin(prop_anchor, "twin_project", project_id)
    async for m in db.digital_twin_models.find({"project_id": project_id}, {"id": 1}):
        await _kg_link_twin(prop_anchor, "twin_model", m["id"])
    return {"ok": True, "property_id": prop_anchor, "property_link_status": link_status}


@router.get("/projects")
async def list_projects(property_id: Optional[str] = Query(None),
                        user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    return await _list_projects_impl(user, property_id)


async def _list_projects_impl(user: dict, property_id):
    # Admin/operator see all; others see owned + member-of.
    if user.get("role") in ("admin", "operator"):
        q = {}
    else:
        q = {"$or": [{"owner_id": user["id"]}, {"members.user_id": user["id"]}]}
    if property_id:
        q = {"$and": [q, {"property_id": property_id}]} if q else {"property_id": property_id}
    items = []
    async for p in db.digital_twin_projects.find(q).sort("updated_at", -1).limit(200):
        items.append(_clean(p))
    return {"items": items, "count": len(items)}


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    # Attach lightweight counts.
    p["pin_count"] = await db.digital_twin_pins.count_documents({"project_id": project_id})
    p["model_count"] = await db.digital_twin_models.count_documents({"project_id": project_id})
    p["plan_count"] = await db.digital_twin_plans.count_documents({"project_id": project_id})
    return _clean(p)


class MemberAdd(BaseModel):
    user_id: str
    role: str = Field("specialist", pattern="^(specialist|client|architect|viewer)$")


@router.post("/projects/{project_id}/members")
async def add_member(project_id: str, payload: MemberAdd, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    p = await _ensure_project_access(project_id, user)
    # Only owner / admin / operator can add members.
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only project owner can add members.")
    target = await db.users.find_one(_user_filter(payload.user_id), {"_id": 1, "name": 1, "email": 1})
    if not target:
        raise HTTPException(404, "User not found.")
    existing = [m for m in (p.get("members") or []) if m.get("user_id") != payload.user_id]
    existing.append({
        "user_id": payload.user_id,
        "name": target.get("name") or target.get("email"),
        "role": payload.role,
        "added_at": _now_iso(),
    })
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"members": existing, "updated_at": _now_iso()}},
    )
    return {"ok": True, "members": existing}


@router.delete("/projects/{project_id}/members/{user_id}")
async def remove_member(project_id: str, user_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only project owner can remove members.")
    members = [m for m in (p.get("members") or []) if m.get("user_id") != user_id]
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"members": members, "updated_at": _now_iso()}},
    )
    return {"ok": True, "members": members}


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only owner can update.")
    updates = {k: (v.strip() if isinstance(v, str) else v) for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return _clean(p)
    updates["updated_at"] = _now_iso()
    await db.digital_twin_projects.update_one({"id": project_id}, {"$set": updates})
    p = await db.digital_twin_projects.find_one({"id": project_id})
    return _clean(p)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only owner can delete.")
    await db.digital_twin_projects.delete_one({"id": project_id})
    await db.digital_twin_models.delete_many({"project_id": project_id})
    await db.digital_twin_plans.delete_many({"project_id": project_id})
    pins = await db.digital_twin_pins.find({"project_id": project_id}, {"id": 1}).to_list(length=10000)
    pin_ids = [pin["id"] for pin in pins]
    if pin_ids:
        await db.digital_twin_comments.delete_many({"pin_id": {"$in": pin_ids}})
    await db.digital_twin_pins.delete_many({"project_id": project_id})
    # Remove any uploaded files
    project_dir = UPLOAD_ROOT / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)
    return {"ok": True}


# ----------------- model upload & serve (Phase B) -----------------

@router.post("/projects/{project_id}/upload")
async def upload_model(
    project_id: str,
    file: UploadFile = File(...),
    layer_type: Optional[str] = Query(None, description="structure | electric | plumbing | hvac | decor | other"),
    change_reason: Optional[str] = Query(None, max_length=300),
    user: dict = Depends(get_current_user),
):
    """Upload a .glb/.gltf model for the project. Stored locally and served via /files/.

    Each uploaded model is treated as an independent BUILDING LAYER (structure,
    electric, plumbing, hvac, ...). Multiple layers per project let the viewer
    render the X-Ray "glass walls" overlay business case.
    """
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only owner can upload models.")

    # Validate extension
    raw_name = file.filename or "model.glb"
    ext = Path(raw_name).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            400,
            "Format permis: .glb / .gltf (vizualizabil 3D) · .dae / .obj / .fbx / .stl / .ply (auto-conversie via Blender) · .skp (SketchUp, descărcabil — exportă .dae din SketchUp pentru randare browser).",
        )

    max_bytes = await storage_service.file_limit_bytes("digital_twin_model")
    dt_remaining = await storage_service.dt_remaining_bytes(p["owner_id"])
    safe_stem = uuid.uuid4().hex[:12]
    safe_name = f"{safe_stem}{ext}"

    # Stream into memory (chunked, with guards) then persist DURABLY to Object Storage.
    # Pod-local disk survives only as an on-demand cache (serve/convert restore it).
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)  # 1 MB
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise HTTPException(413, f"Fișier prea mare (max {max_bytes // (1024*1024)} MB).")
        if len(buf) > dt_remaining:
            raise HTTPException(413, "Cota de stocare Digital Twin este plină. Șterge modele vechi sau contactează echipa.")
    total = len(buf)
    if total == 0:
        raise HTTPException(400, "Fișierul este gol.")
    model_ct = {".glb": "model/gltf-binary", ".gltf": "model/gltf+json"}.get(ext, "application/octet-stream")
    try:
        object_path = await storage_service.store_dt_bytes("model", project_id, safe_name, bytes(buf), model_ct)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Upload failed: {e}") from e

    # Build the public URL. Use APP_PUBLIC_URL when set, else relative path the frontend will resolve.
    public_path = f"/api/digital-twin/files/{project_id}/{safe_name}"

    # Layer metadata — color & default opacity per building system. This mirrors
    # frontend's MultiLayerScene defaults so the viewer can apply consistent
    # "glass walls" visuals.
    LAYER_DEFAULTS = {
        "structure":  {"label": "Structură",   "color": "#c8b89a", "opacity": 1.00},
        "electric":   {"label": "Electricitate", "color": "#fbbf24", "opacity": 0.45},
        "plumbing":   {"label": "Apă/Canal",    "color": "#3b82f6", "opacity": 0.45},
        "hvac":       {"label": "Climatizare",  "color": "#10b981", "opacity": 0.45},
        "decor":      {"label": "Decor",        "color": "#a78bfa", "opacity": 0.85},
        "other":      {"label": "Alt strat",    "color": "#94a3b8", "opacity": 0.70},
    }
    norm_layer = (layer_type or "").strip().lower()
    if norm_layer not in LAYER_DEFAULTS:
        # Auto-detect from filename for backwards-compat (e.g. "electric_layer.glb")
        n = raw_name.lower()
        if any(k in n for k in ("electric", "elect", "el_")):
            norm_layer = "electric"
        elif any(k in n for k in ("plumb", "apa", "sanitar", "water")):
            norm_layer = "plumbing"
        elif any(k in n for k in ("hvac", "clima", "ventil")):
            norm_layer = "hvac"
        elif any(k in n for k in ("decor", "interior", "design", "mobil")):
            norm_layer = "decor"
        elif any(k in n for k in ("struct", "rezist", "arhitectur", "ar_")):
            norm_layer = "structure"
        else:
            norm_layer = "structure"  # first upload default
    layer_meta = LAYER_DEFAULTS[norm_layer]

    # Save model metadata + set as current model on project
    # Auto-conversion capability (server-side):
    #   .dae/.obj/.fbx/.stl/.ply → Blender headless (if Blender is installed)
    #   .skp (SketchUp) → NOT convertible server-side. CloudConvert does not accept .skp as
    #     input (and produces no GLB), and Blender has no SketchUp importer on Linux. We store
    #     the .skp INTACT + downloadable and guide the user to export .glb/.gltf/.dae from
    #     SketchUp (2025+: File → Export → glTF) or use the native Trimble Connect viewer.
    is_archive = ext in DOWNLOAD_ONLY_EXTS
    needs_blender = ext in BLENDER_CONVERT_EXTS  # DAE/OBJ/FBX/STL/PLY → GLB
    _will_convert = needs_blender and _blender.is_enabled()
    model_status = "processing" if _will_convert else ("ready" if (not is_archive and not needs_blender) else "stored")
    _role = user.get("active_view") or user.get("role")
    model_source = "specialist" if _role == "specialist" else ("platform" if _role in ("admin", "operator") else "owner_upload")
    model_doc = {
        "id": _new_id(),
        "project_id": project_id,
        "filename": raw_name,
        "stored_as": safe_name,
        "size_bytes": total,
        "url": public_path,
        "kind": "archive" if is_archive else ("source" if needs_blender else "model"),
        "ext": ext,
        "layer_type": norm_layer,
        "layer_label": layer_meta["label"],
        "layer_color": layer_meta["color"],
        "layer_opacity": layer_meta["opacity"],
        "layer_visible": True,
        "uploaded_by": user["id"],
        "uploaded_by_name": user.get("name") or user.get("email"),
        "uploaded_by_role": user.get("role"),
        "uploaded_at": _now_iso(),
        "object_path": object_path,
        # P1 — ProfessionalModel metadata (proveniență / versionare / vizibilitate / status)
        "property_id": p.get("property_id"),
        "source": model_source,
        "version": 1,
        "version_label": None,
        "status": model_status,
        "visibility": "internal",
        "change_reason": (change_reason or "").strip() or None,
        "supersedes": None,
        "superseded_by": None,
        # P0 — ancoră proprietate + STEP D trust/provenance readiness
        "property_link_status": "linked" if p.get("property_id") else "unresolved",
        "confidence": "documented",
        "verification_status": "owner_declared",
        "completeness": None,
    }
    # Auto-conversion path:
    #   .dae / .obj / .fbx / .stl / .ply → Blender headless (when installed)
    #   .skp → NOT convertible server-side → stored intact + clear guidance (no failing job)
    if needs_blender and _blender.is_enabled():
        model_doc["conversion_status"] = "pending"
        model_doc["conversion_percent"] = 0
        model_doc["conversion_started_at"] = _now_iso()
        model_doc["conversion_engine"] = "blender"
    elif is_archive and ext == ".skp":
        # Honest terminal state: stored intact, not an error, not retryable server-side.
        model_doc["conversion_status"] = "unsupported"
        model_doc["conversion_note"] = (
            "Fișier SketchUp stocat intact și descărcabil. Conversia automată în browser nu este "
            "posibilă pe server. Pentru vizualizare 3D în viewer: exportă din SketchUp .glb/.gltf "
            "(2025+: File → Export → glTF) sau .dae (COLLADA) și încarcă versiunea exportată. "
            "Alternativ, folosește tab-ul „Trimble Connect” pentru vizualizare nativă SketchUp."
        )
    await db.digital_twin_models.insert_one(model_doc)
    # ST-001: fișierul e deja durabil în Object Storage (store_dt_bytes la upload).
    await storage_service.add_usage(p["owner_id"], total, "digital_twin")
    await _kg_link_twin(p.get("property_id"), "twin_model", model_doc["id"])
    # Only set as the active model_url if it's actually viewable (.glb/.gltf)
    is_viewable = not is_archive and not needs_blender
    update_set = {"updated_at": _now_iso()}
    if is_viewable:
        update_set["model_url"] = public_path
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": update_set, "$inc": {"model_count": 1}},
    )
    # Fire-and-forget conversion: doesn't block the upload response.
    if model_doc.get("conversion_status") == "pending":
        engine = model_doc.get("conversion_engine")
        if engine == "blender":
            asyncio.create_task(_run_blender_conversion(model_doc["id"]))
        elif engine == "cloudconvert":
            asyncio.create_task(_run_skp_to_glb_conversion(model_doc["id"]))
    # Phase G: notify stakeholders the architect updated the model
    actor_name = user.get("name") or user.get("email") or "Utilizator"
    project_name = p.get("name", "Proiect")
    size_mb = total / (1024 * 1024)
    stakeholders = await _project_stakeholders(p, exclude_user_id=user["id"])
    for s in stakeholders:
        await notify(
            s["id"],
            "🏗️ Model 3D actualizat",
            f"{actor_name} a încărcat {raw_name} pe {project_name}",
            type_="dt_model",
            link="/digital-twin",
        )
        await send_template(
            tpl_dt_model_uploaded,
            s["name"], project_name, raw_name, size_mb, actor_name,
            to=s["email"],
        )
    return _clean(model_doc)


# ============= AI-3D — ORIENTATIVE MASSING GENERATOR (inferred) =============
# Generează un model 3D ORIENTATIV (massing) din camerele proprietății (2D twin).
# Marcat STRICT ca inferred (Trust Model 015). NU suprascrie un model documented/verified.

_AI3D_SYSTEM = (
    "Ești un asistent care propune un layout dreptunghiular SIMPLU (massing) al unei locuințe, "
    "pentru un model 3D ORIENTATIV. Primești o listă de camere (nume, tip, suprafață m²) și "
    "suprafața totală. Returnează STRICT un JSON array, fără text în plus, unde fiecare element are: "
    '{"name": str, "x": float, "z": float, "w": float, "d": float, "h": float}. '
    "Coordonate în metri, pe un plan (x = est, z = nord), origine (0,0). Camerele NU se suprapun, "
    "sunt aranjate compact într-un dreptunghi. w=lățime, d=adâncime, h=înălțime (2.6 dacă nu știi). "
    "Dacă o cameră are suprafață A, atunci w*d ≈ A. Fără explicații, DOAR JSON."
)


def _fallback_layout(rooms, prop):
    import math
    total_surface = float(prop.get("surface") or 0) or None
    n = len(rooms) or int(prop.get("rooms") or 3) or 3
    if not rooms:
        per = (total_surface / n) if total_surface else 16.0
        rooms = [{"name": f"Camera {i+1}", "area": per} for i in range(n)]
    cols = max(1, int(math.ceil(math.sqrt(len(rooms)))))
    x = z = 0.0
    col = 0
    row_depth = 0.0
    out = []
    for i, r in enumerate(rooms):
        area = float(r.get("area") or r.get("area_m2") or 16.0) or 16.0
        side = max(2.0, math.sqrt(area))
        w = side
        d = area / side if side else side
        out.append({"name": r.get("name") or f"Camera {i+1}", "x": round(x, 2), "z": round(z, 2),
                    "w": round(w, 2), "d": round(d, 2), "h": 2.6})
        x += w + 0.2
        row_depth = max(row_depth, d)
        col += 1
        if col >= cols:
            col = 0
            x = 0.0
            z += row_depth + 0.2
            row_depth = 0.0
    return out


async def _ai_infer_layout(rooms, prop):
    """Returns (layout, engine). Uses the canonical LLM (ai_core.call_llm); falls back to a deterministic grid."""
    import json as _json
    from ai_core.provider import call_llm
    payload_rooms = [{"name": r.get("name"), "type": r.get("type"), "area": r.get("area") or r.get("area_m2")} for r in rooms]
    user_msg = _json.dumps({"total_surface_m2": prop.get("surface"), "rooms": payload_rooms, "rooms_count": prop.get("rooms")}, ensure_ascii=False)
    try:
        res = await call_llm(_AI3D_SYSTEM, f"Camere:\n{user_msg}\n\nReturnează JSON array.", session_id=f"ai3d-{uuid.uuid4().hex[:8]}")
        txt = (res.get("text") or "").strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            if "\n" in txt:
                txt = txt.split("\n", 1)[1]
            if txt.lower().startswith("json"):
                txt = txt[4:]
        start = txt.find("[")
        end = txt.rfind("]")
        if start >= 0 and end > start:
            arr = _json.loads(txt[start:end + 1])
            layout = [x for x in arr if isinstance(x, dict) and all(k in x for k in ("x", "z", "w", "d"))]
            if layout:
                for x in layout:
                    x.setdefault("h", 2.6)
                    x.setdefault("name", "Camera")
                return layout, (res.get("model") or "ai")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai3d] layout inference failed: {e}")
    return _fallback_layout(rooms, prop), "fallback"


def _build_massing_glb(layout) -> bytes:
    import trimesh
    import numpy as np
    palette = [
        [200, 184, 154, 255], [154, 138, 114, 255], [106, 176, 212, 255],
        [212, 255, 58, 255], [167, 139, 250, 255], [16, 185, 129, 255], [148, 163, 184, 255],
    ]
    scene = trimesh.Scene()
    for i, r in enumerate(layout):
        w = max(0.5, float(r.get("w", 3)))
        d = max(0.5, float(r.get("d", 3)))
        h = max(0.5, float(r.get("h", 2.6)))
        x = float(r.get("x", 0))
        z = float(r.get("z", 0))
        box = trimesh.creation.box(extents=[w, h, d])
        box.apply_translation([x + w / 2.0, h / 2.0, z + d / 2.0])
        box.visual.face_colors = np.array(palette[i % len(palette)], dtype=np.uint8)
        scene.add_geometry(box, node_name=(r.get("name") or f"room{i}")[:40])
    glb = scene.export(file_type="glb")
    return glb if isinstance(glb, (bytes, bytearray)) else bytes(glb)


@router.post("/projects/{project_id}/ai-generate")
async def ai_generate_model(project_id: str, user: dict = Depends(get_current_user)):
    """AI-3D — generează un model GLB ORIENTATIV (inferred) din camerele proprietății.
    Trust Model 015: source=ai_generated, confidence=inferred, verification_status=None, completeness=30.
    NU suprascrie un model documented/verified existent (strat suplimentar, nu înlocuiește modelul real)."""
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Doar proprietarul proiectului poate genera modelul AI.")
    prop_id = p.get("property_id")
    if not prop_id:
        raise HTTPException(400, "Ancorează proiectul la o proprietate înainte de generarea AI (Property Anchor).")
    try:
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    except Exception:
        prop = None
    if not prop:
        raise HTTPException(404, "Proprietatea ancorată nu există.")
    twin = await db.twins.find_one({"property_id": prop_id})
    rooms = (twin or {}).get("rooms") or []
    layout, engine = await _ai_infer_layout(rooms, prop)
    try:
        glb = _build_massing_glb(layout)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Generarea 3D a eșuat: {e}") from e
    total = len(glb)
    safe_name = f"ai_{uuid.uuid4().hex[:12]}.glb"
    try:
        object_path = await storage_service.store_dt_bytes("model", project_id, safe_name, glb, "model/gltf-binary")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Stocarea modelului AI a eșuat: {e}") from e
    public_path = f"/api/digital-twin/files/{project_id}/{safe_name}"
    model_doc = {
        "id": _new_id(),
        "project_id": project_id,
        "filename": f"AI · model orientativ ({len(layout)} camere).glb",
        "stored_as": safe_name,
        "size_bytes": total,
        "url": public_path,
        "kind": "model",
        "ext": ".glb",
        "layer_type": "structure",
        "layer_label": "Structură (AI orientativ)",
        "layer_color": "#a78bfa",
        "layer_opacity": 0.85,
        "layer_visible": True,
        "uploaded_by": user["id"],
        "uploaded_by_name": user.get("name") or user.get("email"),
        "uploaded_by_role": user.get("role"),
        "uploaded_at": _now_iso(),
        "object_path": object_path,
        "property_id": prop_id,
        "source": "ai_generated",
        "version": 1,
        "version_label": "AI orientativ",
        "status": "ready",
        "visibility": "internal",
        "change_reason": f"AI-3D massing ({engine})",
        "supersedes": None,
        "superseded_by": None,
        "property_link_status": "linked",
        "confidence": "inferred",
        "verification_status": None,
        "completeness": 30,
        "ai_generated": True,
        "ai_engine": engine,
    }
    await db.digital_twin_models.insert_one(model_doc)
    await storage_service.add_usage(p["owner_id"], total, "digital_twin")
    await _kg_link_twin(prop_id, "twin_model", model_doc["id"])
    documented = await db.digital_twin_models.count_documents({
        "project_id": project_id, "confidence": {"$in": ["documented", "verified"]}, "kind": "model",
    })
    update_set = {"updated_at": _now_iso()}
    if not p.get("model_url") and documented == 0:
        update_set["model_url"] = public_path
    await db.digital_twin_projects.update_one({"id": project_id}, {"$set": update_set, "$inc": {"model_count": 1}})
    out = _clean(model_doc)
    out["note"] = "Model ORIENTATIV generat de AI (inferred). NU este un model profesional verificat."
    return out


# ============= AI DESIGN CONCEPTS — style + budget + materials (inferred) =============
# Extinde AI-3D: pornind de la contextul REAL al proprietății (DNA/camere) + preferințele
# clientului (stil, buget, materiale), produce un CONCEPT DE DESIGN orientativ:
#   • paletă de culori + plan de materiale + buget ESTIMATIV (nu preț garantat)
#   • un strat 3D „massing" colorat în stilul ales (model inferred, vizibil direct în Twin)
#   • (opțional) un RENDER vizual generat cu Gemini Nano Banana
# Trust: status=inferred, confidence=inferred, verification_status=None. Validabil ulterior de un profesionist.

DT_DESIGN_STYLES = [
    "Modern minimalist", "Scandinav", "Industrial", "Clasic elegant", "Rustic",
    "Contemporan", "Mediteranean", "Boho", "Japandi", "Art Deco", "Mid-century",
]
DT_DESIGN_MATERIALS = [
    "Lemn natural", "Marmură", "Beton aparent", "Metal negru", "Sticlă", "Ceramică",
    "Piatră naturală", "Textile naturale", "Cărămidă aparentă", "Parchet stejar", "Alamă",
]


def _hex_to_rgba(h):
    h = (h or "").strip().lstrip("#")
    try:
        if len(h) == 6:
            return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255]
    except Exception:  # noqa: BLE001
        pass
    return [167, 139, 250, 255]


def _build_massing_glb_colored(layout, palette_hex) -> bytes:
    """Ca _build_massing_glb, dar colorează camerele cu paleta conceptului de design."""
    import trimesh
    import numpy as np
    pal = [_hex_to_rgba(x) for x in (palette_hex or []) if x] or [[167, 139, 250, 255]]
    scene = trimesh.Scene()
    for i, r in enumerate(layout):
        w = max(0.5, float(r.get("w", 3)))
        d = max(0.5, float(r.get("d", 3)))
        h = max(0.5, float(r.get("h", 2.6)))
        x = float(r.get("x", 0))
        z = float(r.get("z", 0))
        box = trimesh.creation.box(extents=[w, h, d])
        box.apply_translation([x + w / 2.0, h / 2.0, z + d / 2.0])
        box.visual.face_colors = np.array(pal[i % len(pal)], dtype=np.uint8)
        scene.add_geometry(box, node_name=(r.get("name") or f"room{i}")[:40])
    glb = scene.export(file_type="glb")
    return glb if isinstance(glb, (bytes, bytearray)) else bytes(glb)


_DESIGN_SYSTEM = (
    "Ești designer de interior profesionist. Primești CONTEXTUL REAL al unei proprietăți (identitate, "
    "camere, suprafețe, documente, lucrări) și PREFERINȚELE clientului (stil, buget, materiale, priorități). "
    "Propui un CONCEPT DE DESIGN ORIENTATIV. Reguli STRICTE:\n"
    "- NU inventa date despre proprietate care nu apar în context.\n"
    "- Bugetul este ESTIMATIV (interval), calculat pe suprafață + materiale + stil; NU este preț garantat de execuție.\n"
    "- Respectă intervalul de buget al clientului dacă e specificat.\n"
    "Returnează STRICT un obiect JSON (fără text în plus) cu cheile:\n"
    '{"title": str, "summary": str, "style_rationale": str, '
    '"palette": [{"name": str, "hex": "#RRGGBB"}], '
    '"materials_plan": [{"surface": str, "material": str, "note": str}], '
    '"budget": {"currency": str, "items": [{"label": str, "low": number, "high": number}], "total_low": number, "total_high": number, "disclaimer": str}, '
    '"render_prompt": str}\n'
    "Textele descriptive în ROMÂNĂ. `render_prompt` în ENGLEZĂ, o descriere fotorealistă a camerei în stilul ales "
    "(materiale, culori, lumină, unghi), 1-2 propoziții. `palette` are 4-6 culori. Buget în moneda cerută."
)


async def _ai_design_concept(context: str, payload, prop: dict, rooms: list):
    """Returnează (concept_dict, engine). Fallback determinist dacă LLM eșuează."""
    import json as _json
    from ai_core.provider import call_llm
    surface = prop.get("surface")
    budget_line = "nespecificat"
    if payload.budget_min is not None or payload.budget_max is not None:
        budget_line = f"{payload.budget_min or 0}–{payload.budget_max or '∞'} {payload.currency}"
    ask = {
        "stil": payload.style,
        "camera_tinta": payload.room_name or "întreaga locuință",
        "buget": budget_line,
        "moneda": payload.currency,
        "materiale_preferate": payload.materials or [],
        "prioritati": payload.priorities or [],
        "note_client": payload.notes or "",
        "suprafata_totala_m2": surface,
        "camere": [{"nume": r.get("name"), "tip": r.get("type"), "arie_m2": r.get("area")} for r in (rooms or [])],
    }
    prompt = f"## CONTEXT PROPRIETATE (dovezi)\n{context}\n\n## CERINȚE CLIENT\n{_json.dumps(ask, ensure_ascii=False)}\n\nReturnează DOAR obiectul JSON."
    try:
        res = await call_llm(_DESIGN_SYSTEM, prompt, session_id=f"dt-design-{uuid.uuid4().hex[:8]}")
        txt = (res.get("text") or "").strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            if "\n" in txt:
                txt = txt.split("\n", 1)[1]
            if txt.lower().startswith("json"):
                txt = txt[4:]
        s = txt.find("{")
        e = txt.rfind("}")
        if s >= 0 and e > s:
            obj = _json.loads(txt[s:e + 1])
            if isinstance(obj, dict) and obj.get("palette"):
                obj.setdefault("budget", {})
                return obj, (res.get("model") or "ai")
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"[design] concept inference failed: {ex}")
    # Fallback determinist
    fallback = {
        "title": f"Concept {payload.style}",
        "summary": f"Concept orientativ în stil {payload.style} pentru {payload.room_name or 'locuință'}.",
        "style_rationale": "Generat automat (fallback) — deschide din nou pentru un concept AI complet.",
        "palette": [{"name": "Neutru cald", "hex": "#d6cbb8"}, {"name": "Antracit", "hex": "#2f3336"},
                    {"name": "Verde salvie", "hex": "#8a9a7b"}, {"name": "Alamă", "hex": "#b08d57"}],
        "materials_plan": [{"surface": "Pardoseală", "material": (payload.materials or ["Parchet stejar"])[0], "note": "orientativ"}],
        "budget": {"currency": payload.currency, "items": [], "total_low": payload.budget_min or 0,
                   "total_high": payload.budget_max or 0, "disclaimer": "Estimare orientativă, nu preț garantat."},
        "render_prompt": f"Photorealistic {payload.style} interior of a {payload.room_name or 'living room'}, natural light, cozy, high detail",
    }
    return fallback, "fallback"


async def _gen_design_render(prompt: str, project_id: str):
    """Generează un render vizual cu Gemini Nano Banana.
    Returnează (object_path|None, stored_as|None, mime|None, error|None)."""
    key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    if not key:
        return None, None, None, "Cheia AI pentru imagini nu este configurată."
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=key,
            session_id=f"dt-design-img-{uuid.uuid4().hex[:8]}",
            system_message="You generate photorealistic interior design concept renders. Output only the image.",
        ).with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
        full_prompt = (prompt or "Photorealistic modern interior render, natural light, high detail").strip()
        _text, images = await chat.send_message_multimodal_response(UserMessage(text=full_prompt))
        if not images:
            return None, None, None, "Modelul nu a returnat nicio imagine."
        img = images[0]
        image_bytes = base64.b64decode(img["data"])
        mime = img.get("mime_type") or "image/png"
        ext = ".png" if "png" in mime else (".jpg" if "jpe" in mime else ".png")
        safe_name = f"design_{uuid.uuid4().hex[:12]}{ext}"
        object_path = await storage_service.store_dt_bytes("model", project_id, safe_name, image_bytes, mime)
        return object_path, safe_name, mime, None
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"[design] render generation failed: {ex}")
        return None, None, None, str(ex)[:200]


class DesignConceptIn(BaseModel):
    room_name: Optional[str] = Field(None, max_length=120)
    style: str = Field(..., min_length=2, max_length=80)
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    currency: str = Field("RON", max_length=8)
    materials: List[str] = Field(default_factory=list)
    priorities: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=1000)
    generate_render: bool = True


@router.get("/design-options")
async def design_options(user: dict = Depends(get_current_user)):  # noqa: ARG001
    """Opțiuni selectabile pentru wizard-ul de concept (stiluri + materiale)."""
    return {"styles": DT_DESIGN_STYLES, "materials": DT_DESIGN_MATERIALS, "default_currency": "RON"}


@router.post("/projects/{project_id}/design-concepts")
async def create_design_concept(project_id: str, payload: DesignConceptIn, user: dict = Depends(get_current_user)):
    """AI Design Concept: stil + buget + materiale → concept orientativ (inferred) + strat 3D colorat + render opțional."""
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        raise HTTPException(403, "Doar proprietarul proiectului poate genera concepte de design.")
    prop_id = p.get("property_id")
    if not prop_id:
        raise HTTPException(400, "Ancorează proiectul la o proprietate înainte de conceptul AI (Property Anchor).")
    try:
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    except Exception:
        prop = None
    if not prop:
        raise HTTPException(404, "Proprietatea ancorată nu există.")
    twin = await db.twins.find_one({"property_id": prop_id})
    rooms = (twin or {}).get("rooms") or []
    # Reuse the evidence-first context builder from Q&A (grounded, no hallucination).
    try:
        from routes.digital_twin_qa import _build_context
        context = await _build_context(project_id)
    except Exception:  # noqa: BLE001
        context = f"Proprietate: {prop.get('name')}, {prop.get('surface')} m², {prop.get('rooms')} camere."

    concept, engine = await _ai_design_concept(context, payload, prop, rooms)

    # Build a colored massing GLB (inferred) tinted with the concept palette.
    layout, _eng = await _ai_infer_layout(rooms, prop)
    palette_hex = [c.get("hex") for c in (concept.get("palette") or []) if c.get("hex")]
    model_id = _new_id()
    model_public_path = None
    try:
        glb = _build_massing_glb_colored(layout, palette_hex)
        total = len(glb)
        safe_name = f"concept_{uuid.uuid4().hex[:12]}.glb"
        object_path = await storage_service.store_dt_bytes("model", project_id, safe_name, glb, "model/gltf-binary")
        model_public_path = f"/api/digital-twin/files/{project_id}/{safe_name}"
        model_doc = {
            "id": model_id,
            "project_id": project_id,
            "filename": f"Concept AI · {payload.style} ({len(layout)} camere).glb",
            "stored_as": safe_name,
            "size_bytes": total,
            "url": model_public_path,
            "kind": "model",
            "ext": ".glb",
            "layer_type": "decor",
            "layer_label": f"Concept AI · {payload.style}",
            "layer_color": (palette_hex[0] if palette_hex else "#a78bfa"),
            "layer_opacity": 0.9,
            "layer_visible": True,
            "uploaded_by": user["id"],
            "uploaded_by_name": user.get("name") or user.get("email"),
            "uploaded_by_role": user.get("role"),
            "uploaded_at": _now_iso(),
            "object_path": object_path,
            "property_id": prop_id,
            "source": "ai_generated",
            "version": 1,
            "version_label": "Concept AI Design",
            "status": "ready",
            "visibility": "internal",
            "change_reason": f"AI Design Concept ({engine})",
            "property_link_status": "linked",
            "confidence": "inferred",
            "verification_status": None,
            "completeness": 25,
            "ai_generated": True,
            "ai_engine": engine,
            "review_state": "none",
            "is_design_concept": True,
        }
        await db.digital_twin_models.insert_one(model_doc)
        await storage_service.add_usage(p["owner_id"], total, "digital_twin")
        await _kg_link_twin(prop_id, "twin_model", model_id)
        documented = await db.digital_twin_models.count_documents({
            "project_id": project_id, "confidence": {"$in": ["documented", "verified"]}, "kind": "model",
        })
        upd = {"updated_at": _now_iso()}
        if not p.get("model_url") and documented == 0:
            upd["model_url"] = model_public_path
        await db.digital_twin_projects.update_one({"id": project_id}, {"$set": upd, "$inc": {"model_count": 1}})
    except Exception as ex:  # noqa: BLE001
        logger.warning(f"[design] colored massing failed: {ex}")
        model_id = None

    concept_doc = {
        "id": _new_id(),
        "project_id": project_id,
        "property_id": prop_id,
        "owner_id": p.get("owner_id"),
        "created_by": user["id"],
        "created_by_name": user.get("name") or user.get("email"),
        "created_at": _now_iso(),
        "inputs": {
            "room_name": payload.room_name,
            "style": payload.style,
            "budget_min": payload.budget_min,
            "budget_max": payload.budget_max,
            "currency": payload.currency,
            "materials": payload.materials,
            "priorities": payload.priorities,
            "notes": payload.notes,
        },
        "concept": concept,
        "engine": engine,
        "model_id": model_id,
        "model_url": model_public_path,
        "render_url": None,
        "render_object_path": None,
        "render_mime": None,
        "render_error": None,
        "status": "inferred",
        "confidence": "inferred",
        "verification_status": None,
    }
    if payload.generate_render:
        obj_path, _stored, mime, err = await _gen_design_render(concept.get("render_prompt") or "", project_id)
        if obj_path:
            concept_doc["render_object_path"] = obj_path
            concept_doc["render_mime"] = mime
            concept_doc["render_url"] = f"/api/digital-twin/design-concepts/{concept_doc['id']}/render"
        concept_doc["render_error"] = err
    await db.digital_twin_design_concepts.insert_one(concept_doc)
    if model_id:
        await db.digital_twin_models.update_one({"id": model_id}, {"$set": {"design_concept_id": concept_doc["id"]}})
    out = _clean(dict(concept_doc))
    out["note"] = "Concept ORIENTATIV de design (inferred). Bugetul este estimativ, NU preț garantat de execuție. Necesită validare profesională."
    return out


@router.get("/projects/{project_id}/design-concepts")
async def list_design_concepts(project_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    await _ensure_project_access(project_id, user)
    items = []
    async for c in db.digital_twin_design_concepts.find({"project_id": project_id}).sort("created_at", -1).limit(50):
        items.append(_clean(c))
    return {"items": items, "count": len(items)}


@router.get("/design-concepts/{concept_id}")
async def get_design_concept(concept_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    c = await db.digital_twin_design_concepts.find_one({"id": concept_id})
    if not c:
        raise HTTPException(404, "Concept not found.")
    await _ensure_project_access(c["project_id"], user)
    return _clean(c)


@router.get("/design-concepts/{concept_id}/render")
async def get_design_concept_render(concept_id: str, user: dict = Depends(get_current_user)):
    """Servește imaginea-render a conceptului direct din Object Storage (access-controlled)."""
    await _ensure_dt_ingest_access(user)
    c = await db.digital_twin_design_concepts.find_one({"id": concept_id})
    if not c:
        raise HTTPException(404, "Concept not found.")
    await _ensure_project_access(c["project_id"], user)
    obj_path = c.get("render_object_path")
    if not obj_path:
        raise HTTPException(404, "Acest concept nu are un render vizual.")
    from storage_client import get_object
    try:
        data, ct = await asyncio.to_thread(get_object, obj_path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(404, "Render indisponibil.") from e
    return StreamingResponse(
        io.BytesIO(data),
        media_type=c.get("render_mime") or ct or "image/png",
        headers={"Cache-Control": "private, max-age=86400"},
    )


# ============= REAL MATERIALS + INDICATIVE PRICING (City Partners + market fallback) =============
# Concept materials are AI-inferred. We enrich them with REAL indicative prices:
#   1) City Partners product catalog (`city_partner_products`, admin-managed) — empty by default.
#   2) Fallback: real market observations (`price_observations`, PropManage price data).
# Nothing is invented: when no match exists we honestly return "preț orientativ indisponibil".

_MATERIAL_PRICE_CATEGORY = [
    (("parchet", "stejar", "laminat", "dușumea", "dusumea", "lemn"), "parchet"),
    (("marmur", "granit"), "faianta"),
    (("piatr", "piatră"), "faianta"),
    (("faian", "gresie", "ceramic", "plac"), "faianta"),
    (("gips", "rigips", "tavan"), "gips_carton"),
    (("vops", "zugrav", "lavabil", "glet"), "zugravit"),
    (("cărămid", "caramid", "zid", "beton", "bca"), "constructii"),
    (("fereas", "geam", "tâmpl", "tampl", "ușă", "usa", "pvc"), "tamplarie"),
    (("fațad", "fatad", "termo", "polistiren"), "fatade_termoizolatii"),
]


def _material_to_category(text: str) -> str:
    t = (text or "").lower()
    for kws, cat in _MATERIAL_PRICE_CATEGORY:
        if any(k in t for k in kws):
            return cat
    return "interior_design"


async def _match_partner_product(material: str, surface: str):
    """Match a concept material to a REAL City Partners product. Catalog empty by default → None."""
    material = (material or "").strip()
    if not material:
        return None
    if await db.city_partner_products.count_documents({}, limit=1) == 0:
        return None
    base = {"active": {"$ne": False}}
    prod = await db.city_partner_products.find_one({
        **base,
        "$or": [
            {"name": {"$regex": material, "$options": "i"}},
            {"tags": {"$in": [material.lower()]}},
        ],
    })
    if not prod:
        terms = [t.lower() for t in material.split() if len(t) > 2]
        if terms:
            prod = await db.city_partner_products.find_one({**base, "tags": {"$in": terms}})
    return prod


@router.get("/design-concepts/{concept_id}/materials")
async def concept_materials(concept_id: str, city: Optional[str] = Query(None),
                            user: dict = Depends(get_current_user)):
    """Feature D — map concept materials to REAL indicative prices (partner product or market fallback)."""
    await _ensure_dt_ingest_access(user)
    c = await db.digital_twin_design_concepts.find_one({"id": concept_id})
    if not c:
        raise HTTPException(404, "Concept not found.")
    await _ensure_project_access(c["project_id"], user)
    concept = c.get("concept") or {}
    plan = concept.get("materials_plan") or []
    currency = (concept.get("budget") or {}).get("currency") or "RON"
    from construction.prices import aggregate_prices
    out = []
    for m in plan:
        material = (m.get("material") or "").strip()
        surface = (m.get("surface") or "").strip()
        pricing = None
        source = None
        prod = await _match_partner_product(material, surface)
        if prod:
            pricing = {
                "label": prod.get("name"),
                "partner": prod.get("partner_name"),
                "brand": prod.get("brand"),
                "unit": prod.get("unit") or "buc",
                "price_low": prod.get("price_min"),
                "price_high": prod.get("price_max") if prod.get("price_max") is not None else prod.get("price_min"),
                "url": prod.get("url"),
            }
            source = "city_partner"
        else:
            cat = _material_to_category(f"{material} {surface}")
            try:
                rows = await aggregate_prices(cat, city or "București")
            except Exception:  # noqa: BLE001
                rows = []
            row = next((r for r in rows if r.get("experience_level") == "mid"), (rows[0] if rows else None))
            if row:
                pricing = {
                    "label": row.get("service"),
                    "unit": row.get("unit"),
                    "price_low": row.get("price_min"),
                    "price_high": row.get("price_max"),
                    "city": row.get("city"),
                    "preliminary": row.get("preliminary"),
                }
                source = "market_price"
        out.append({
            "surface": surface,
            "material": material,
            "note": m.get("note"),
            "pricing": pricing,
            "pricing_source": source,  # city_partner | market_price | None
        })
    return {
        "items": out,
        "count": len(out),
        "currency": currency,
        "disclaimer": (
            "Prețuri ORIENTATIVE (produse partener sau manoperă de piață PropManage). "
            "Nu reprezintă o ofertă fermă — pentru preț exact cere o ofertă unui specialist verificat."
        ),
    }


# ============= WINNER PICK — mark a preferred concept (Alegere câștigătoare) =============

class PreferIn(BaseModel):
    preferred: bool = True


@router.post("/projects/{project_id}/design-concepts/{concept_id}/prefer")
async def prefer_design_concept(project_id: str, concept_id: str, payload: PreferIn,
                                user: dict = Depends(get_current_user)):
    """Marchează un concept ca 'preferat' (câștigător). Debifează celelalte din proiect."""
    await _ensure_dt_ingest_access(user)
    proj = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and proj.get("owner_id") != user["id"]:
        raise HTTPException(403, "Doar proprietarul poate alege conceptul preferat.")
    c = await db.digital_twin_design_concepts.find_one({"id": concept_id, "project_id": project_id})
    if not c:
        raise HTTPException(404, "Concept not found.")
    if payload.preferred:
        await db.digital_twin_design_concepts.update_many(
            {"project_id": project_id, "id": {"$ne": concept_id}}, {"$set": {"preferred": False}})
        await db.digital_twin_design_concepts.update_one(
            {"id": concept_id},
            {"$set": {"preferred": True, "preferred_at": _now_iso(), "preferred_by": user["id"]}})
    else:
        await db.digital_twin_design_concepts.update_one({"id": concept_id}, {"$set": {"preferred": False}})
    return {"ok": True, "preferred": payload.preferred, "concept_id": concept_id}


# ============= OFFER FROM VERIFIED CONCEPT (Feature B) =============
# Transformă un concept VALIDAT PROFESIONAL într-o cerere reală de ofertă (db.requests),
# folosind fluxul de marketplace existent. Necesită confirmarea explicită a clientului.

class RequestOfferIn(BaseModel):
    confirm: bool = False
    note: Optional[str] = Field(None, max_length=600)
    category: str = Field("interior_design", max_length=60)


@router.post("/design-concepts/{concept_id}/request-offer")
async def request_offer_from_concept(concept_id: str, payload: RequestOfferIn,
                                     user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    c = await db.digital_twin_design_concepts.find_one({"id": concept_id})
    if not c:
        raise HTTPException(404, "Concept not found.")
    proj = await _ensure_project_access(c["project_id"], user)
    owner_id = proj.get("owner_id")
    if user.get("role") not in ("admin", "operator") and owner_id != user["id"]:
        raise HTTPException(403, "Doar proprietarul poate cere o ofertă din acest concept.")
    # STRICT: doar concept validat profesional.
    verified = c.get("status") == "verified" or c.get("confidence") == "verified"
    if not verified and c.get("model_id"):
        m = await db.digital_twin_models.find_one({"id": c["model_id"]}, {"confidence": 1})
        verified = bool(m and m.get("confidence") == "verified")
    if not verified:
        raise HTTPException(400, "Oferta se poate cere DOAR dintr-un concept validat profesional (verificat).")
    prop_id = c.get("property_id") or proj.get("property_id")
    if not prop_id:
        raise HTTPException(400, "Conceptul nu este ancorat la o proprietate.")
    try:
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    except Exception:
        prop = None
    if not prop:
        raise HTTPException(404, "Proprietatea nu există.")
    if str(prop.get("owner_id")) != str(owner_id):
        raise HTTPException(403, "Proprietatea nu aparține proprietarului conceptului.")
    if not payload.confirm:
        raise HTTPException(400, "Confirmarea explicită a clientului este necesară (confirm=true).")
    # Idempotență: nu dubla o cerere activă din același concept.
    existing = await db.requests.find_one({"concept_id": concept_id, "status": {"$in": ["open", "assigned", "in_progress"]}})
    if existing:
        return {"ok": True, "already_exists": True, "request_id": str(existing["_id"]),
                "offers_link": f"/client/requests/{str(existing['_id'])}/offers",
                "message": "Există deja o cerere de ofertă activă pentru acest concept."}
    concept = c.get("concept") or {}
    budget = concept.get("budget") or {}
    est = None
    if budget.get("total_low") is not None and budget.get("total_high") is not None:
        est = round((float(budget["total_low"]) + float(budget["total_high"])) / 2.0)
    elif budget.get("total_high"):
        est = float(budget["total_high"])
    mats = ", ".join([f"{m.get('surface')}: {m.get('material')}" for m in (concept.get("materials_plan") or [])][:8])
    title = f"Execuție concept: {concept.get('title') or c.get('inputs', {}).get('style') or 'Design interior'}"
    lines = [concept.get("summary") or "Cerere generată dintr-un concept de design validat profesional."]
    if mats:
        lines.append(f"Materiale (orientativ): {mats}.")
    if budget.get("total_low") or budget.get("total_high"):
        lines.append(f"Buget estimativ concept: {budget.get('total_low') or '—'}–{budget.get('total_high') or '—'} {budget.get('currency') or 'RON'} (orientativ).")
    if payload.note:
        lines.append(f"Notă client: {payload.note}")
    lines.append("Sursă: Digital Twin — concept validat profesional.")
    owner = await db.users.find_one(_user_filter(owner_id), {"name": 1, "email": 1})
    doc = {
        "property_id": prop_id,
        "category": payload.category or "interior_design",
        "title": title[:200],
        "description": "\n".join(lines)[:4000],
        "priority": "normal",
        "budget_estimate": est,
        "county": prop.get("county") or prop.get("zone") or prop.get("city"),
        "photos": None,
        "taxonomy_node_id": None,
        "subcategory": None,
        "client_id": owner_id,
        "client_name": (owner or {}).get("name") or proj.get("owner_name") or "Client",
        "property_name": prop.get("name"),
        "property_address": prop.get("address"),
        "status": "open",
        "specialist_id": None,
        "specialist_name": None,
        "escrow_amount": None,
        "created_at": _now_iso(),
        "source": "digital_twin_concept",
        "concept_id": concept_id,
        "dt_model_id": c.get("model_id"),
        "dt_project_id": c["project_id"],
    }
    res = await db.requests.insert_one(doc)
    req_id = str(res.inserted_id)
    await db.digital_twin_design_concepts.update_one({"id": concept_id}, {"$set": {
        "offer_request_id": req_id, "offer_requested_at": _now_iso(), "offer_requested_by": user["id"],
    }})
    # Ofertă cu Poze — attach the concept's AI render to the request so specialists see it.
    render_url = None
    render_path = c.get("render_object_path")
    if render_path:
        render_url = f"/api/requests/{req_id}/concept-render"
        await db.requests.update_one({"_id": res.inserted_id}, {"$set": {
            "dt_concept_render_path": render_path,
            "dt_concept_render_mime": c.get("render_mime"),
            "concept_render_url": render_url,
            "photos": [render_url],
        }})
    try:
        await log_event(req_id, "request.created", actor=user, property_id=prop_id,
                        payload={"title": title, "category": doc["category"], "source": "digital_twin_concept"})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[dt-offer] log_event failed: {e}")
    spec_query = {"role": "specialist", "$or": [{"specialty": doc["category"]}, {"specialty": None}]}
    specs = await db.users.find(spec_query).to_list(50)
    for s in specs:
        await notify(
            str(s["_id"]),
            f"Lead nou (concept validat): {title}",
            f"Cerere de ofertă dintr-un concept Digital Twin validat profesional. Buget estimativ: {est or '—'} RON.",
            type_="lead", link="/specialist",
        )
    return {"ok": True, "request_id": req_id, "offers_link": f"/client/requests/{req_id}/offers",
            "concept_render_url": render_url,
            "message": "Cererea de ofertă a fost trimisă către specialiștii verificați."}


# ============= PROFESSIONAL VALIDATION — inferred → review → verified =============
# Un profesionist (admin/operator sau membru architect/specialist) confirmă EXPLICIT un model inferat.
# NU convertim automat inferred → verified. Istoricul validării e păstrat (cine/când/ce/rezultat).

def _is_professional(user: dict, project: dict) -> bool:
    if user.get("role") in ("admin", "operator"):
        return True
    for m in (project.get("members") or []):
        if m.get("user_id") == user["id"] and m.get("role") in ("architect", "specialist"):
            return True
    return False


async def _log_validation(model: dict, action: str, from_conf, to_conf, user: dict, note: str | None):
    await db.digital_twin_validations.insert_one({
        "id": _new_id(),
        "model_id": model["id"],
        "project_id": model["project_id"],
        "property_id": model.get("property_id"),
        "design_concept_id": model.get("design_concept_id"),
        "action": action,
        "from_confidence": from_conf,
        "to_confidence": to_conf,
        "actor_id": user["id"],
        "actor_name": user.get("name") or user.get("email"),
        "actor_role": user.get("role"),
        "note": (note or "").strip() or None,
        "ts": _now_iso(),
    })


class ReviewRequestIn(BaseModel):
    note: Optional[str] = Field(None, max_length=600)


class ValidateIn(BaseModel):
    action: str = Field(..., pattern="^(confirm|reject)$")
    note: Optional[str] = Field(None, max_length=800)


@router.post("/models/{model_id}/request-review")
async def request_model_review(model_id: str, payload: ReviewRequestIn, user: dict = Depends(get_current_user)):
    """Trimite un model INFERAT la validare profesională (inferred → in_review). Nu schimbă confidence."""
    await _ensure_dt_ingest_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    proj = await _ensure_project_access(doc["project_id"], user)
    if user.get("role") not in ("admin", "operator") and proj.get("owner_id") != user["id"] and not _is_professional(user, proj):
        raise HTTPException(403, "Nu ai dreptul să trimiți acest model la validare.")
    if doc.get("confidence") != "inferred":
        raise HTTPException(400, "Doar modelele orientative (inferred) pot fi trimise la validare.")
    if doc.get("review_state") == "in_review":
        raise HTTPException(400, "Modelul este deja în curs de validare.")
    await db.digital_twin_models.update_one({"id": model_id}, {"$set": {
        "review_state": "in_review",
        "review_requested_by": user["id"],
        "review_requested_by_name": user.get("name") or user.get("email"),
        "review_requested_at": _now_iso(),
        "updated_at": _now_iso(),
    }})
    await _log_validation(doc, "request_review", doc.get("confidence"), doc.get("confidence"), user, payload.note)
    if doc.get("design_concept_id"):
        await db.digital_twin_design_concepts.update_one({"id": doc["design_concept_id"]}, {"$set": {"status": "in_review"}})
    refreshed = await db.digital_twin_models.find_one({"id": model_id})
    return _clean(refreshed)


@router.post("/models/{model_id}/validate")
async def validate_model(model_id: str, payload: ValidateIn, user: dict = Depends(get_current_user)):
    """Acțiune EXPLICITĂ a profesionistului: confirm → verified (professional_audit) sau reject → rămâne inferred."""
    await _ensure_dt_ingest_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    proj = await _ensure_project_access(doc["project_id"], user)
    if not _is_professional(user, proj):
        raise HTTPException(403, "Doar un profesionist (arhitect/specialist/operator/admin) poate valida un model.")
    from_conf = doc.get("confidence")
    now = _now_iso()
    if payload.action == "confirm":
        upd = {
            "confidence": "verified",
            "verification_status": "professional_audit",
            "review_state": "verified",
            "validated_by": user["id"],
            "validated_by_name": user.get("name") or user.get("email"),
            "validated_by_role": user.get("role"),
            "validated_at": now,
            "validation_note": (payload.note or "").strip() or None,
            "updated_at": now,
        }
        to_conf = "verified"
        concept_status = "verified"
    else:
        upd = {
            "review_state": "rejected",
            "rejected_by": user["id"],
            "rejected_by_name": user.get("name") or user.get("email"),
            "rejected_at": now,
            "validation_note": (payload.note or "").strip() or None,
            "updated_at": now,
        }
        to_conf = from_conf
        concept_status = "rejected"
    await db.digital_twin_models.update_one({"id": model_id}, {"$set": upd})
    await _log_validation(doc, payload.action, from_conf, to_conf, user, payload.note)
    if doc.get("design_concept_id"):
        cset = {"status": concept_status}
        if payload.action == "confirm":
            cset.update({"confidence": "verified", "verification_status": "professional_audit",
                         "validated_by_name": user.get("name") or user.get("email"), "validated_at": now})
        await db.digital_twin_design_concepts.update_one({"id": doc["design_concept_id"]}, {"$set": cset})
    # Feature C — notify the property owner + review requester about the validation outcome.
    try:
        owner_id = proj.get("owner_id")
        actor = user.get("name") or user.get("email") or "Un profesionist"
        fname = doc.get("filename") or "Modelul 3D"
        if owner_id and owner_id != user["id"]:
            if payload.action == "confirm":
                await notify(owner_id, "✅ Model validat profesional",
                             f"{actor} a verificat „{fname}”. Modelul este acum marcat ca verificat profesional.",
                             type_="dt_validation", link="/digital-twin")
            else:
                reason = (payload.note or "").strip()
                msg = f"{actor} a respins „{fname}” la validare. Modelul rămâne orientativ (AI)."
                if reason:
                    msg += f" Motiv: {reason}"
                await notify(owner_id, "⚠️ Model respins la validare", msg,
                             type_="dt_validation", link="/digital-twin")
        rr = doc.get("review_requested_by")
        if rr and rr not in (user["id"], owner_id):
            verdict = "validat" if payload.action == "confirm" else "respins"
            await notify(rr, f"Validare finalizată: {verdict}",
                         f"Modelul „{fname}” trimis de tine a fost {verdict} de {actor}.",
                         type_="dt_validation", link="/digital-twin")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[dt-validation] notify failed: {e}")
    refreshed = await db.digital_twin_models.find_one({"id": model_id})
    return _clean(refreshed)


@router.get("/models/{model_id}/validation-history")
async def model_validation_history(model_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    await _ensure_project_access(doc["project_id"], user)
    items = []
    async for v in db.digital_twin_validations.find({"model_id": model_id}).sort("ts", -1).limit(100):
        items.append(_clean(v))
    return {
        "items": items,
        "count": len(items),
        "current": {
            "confidence": doc.get("confidence"),
            "verification_status": doc.get("verification_status"),
            "review_state": doc.get("review_state") or "none",
            "validated_by_name": doc.get("validated_by_name"),
            "validated_at": doc.get("validated_at"),
        },
    }


@router.get("/professional/review-queue")
async def professional_review_queue(user: dict = Depends(get_current_user)):
    """Coada de modele trimise la validare (in_review), vizibilă profesioniștilor (admin/operator/architect/specialist)."""
    await _ensure_dt_ingest_access(user)
    is_priv = user.get("role") in ("admin", "operator")
    q = {"review_state": "in_review"}
    items = []
    async for m in db.digital_twin_models.find(q).sort("review_requested_at", -1).limit(200):
        proj = await db.digital_twin_projects.find_one({"id": m["project_id"]})
        if not proj:
            continue
        if not is_priv and not _is_professional(user, proj):
            continue
        items.append({
            "model_id": m["id"],
            "project_id": m["project_id"],
            "project_name": proj.get("name"),
            "filename": m.get("filename"),
            "confidence": m.get("confidence"),
            "is_design_concept": bool(m.get("is_design_concept")),
            "requested_by_name": m.get("review_requested_by_name"),
            "requested_at": m.get("review_requested_at"),
            "owner_name": proj.get("owner_name"),
        })
    return {"items": items, "count": len(items)}


# ============= CLOUDCONVERT SKP → GLB PIPELINE =============

LAYER_DEFAULTS_FOR_CONVERT = {
    "structure":  {"label": "Structură",   "color": "#c8b89a", "opacity": 1.00},
    "electric":   {"label": "Electricitate", "color": "#fbbf24", "opacity": 0.45},
    "plumbing":   {"label": "Apă/Canal",    "color": "#3b82f6", "opacity": 0.45},
    "hvac":       {"label": "Climatizare",  "color": "#10b981", "opacity": 0.45},
    "decor":      {"label": "Decor",        "color": "#a78bfa", "opacity": 0.85},
    "other":      {"label": "Alt strat",    "color": "#94a3b8", "opacity": 0.70},
}


async def _update_conversion(model_id: str, **fields) -> None:
    fields["updated_at"] = _now_iso()
    await db.digital_twin_models.update_one({"id": model_id}, {"$set": fields})


async def _run_blender_conversion(model_id: str) -> None:
    """Background task: convert .dae/.obj/.fbx/.stl/.ply → .glb via headless Blender.

    Inserts a new sibling `digital_twin_models` row marked as the converted
    `.glb` so MultiLayerScene picks it up automatically.
    """
    src = await db.digital_twin_models.find_one({"id": model_id})
    if not src:
        return
    project_id = src["project_id"]
    src_path = UPLOAD_ROOT / project_id / src["stored_as"]
    if not src_path.exists():
        restored = await storage_service.ensure_dt_local("model", project_id, src["stored_as"])
        if restored:
            src_path = restored
    if not src_path.exists():
        await _update_conversion(model_id, conversion_status="failed", conversion_error="Source file missing on disk.")
        return
    await _update_conversion(model_id, conversion_status="converting", conversion_percent=10)
    glb_safe = f"{uuid.uuid4().hex[:12]}.glb"
    glb_path = UPLOAD_ROOT / project_id / glb_safe
    try:
        result = await _blender.convert_to_glb(str(src_path), str(glb_path), timeout_sec=600)
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[Blender] conversion failed for {model_id}")
        await _update_conversion(model_id, conversion_status="failed", conversion_error=str(e))
        return
    bytes_written = int(result.get("bytes_written") or 0)
    await _update_conversion(model_id, conversion_status="downloading", conversion_percent=90)

    norm_layer = src.get("layer_type") or "structure"
    meta = LAYER_DEFAULTS_FOR_CONVERT.get(norm_layer, LAYER_DEFAULTS_FOR_CONVERT["structure"])
    glb_public_path = f"/api/digital-twin/files/{project_id}/{glb_safe}"
    try:
        glb_object_path = await storage_service.store_dt_bytes(
            "model", project_id, glb_safe, glb_path.read_bytes(), "model/gltf-binary")
    except Exception:  # noqa: BLE001
        glb_object_path = None
    converted_doc = {
        "id": _new_id(),
        "project_id": project_id,
        "filename": Path(src["filename"]).stem + ".glb",
        "stored_as": glb_safe,
        "size_bytes": bytes_written,
        "url": glb_public_path,
        "kind": "model",
        "ext": ".glb",
        "layer_type": norm_layer,
        "layer_label": meta["label"],
        "layer_color": meta["color"],
        "layer_opacity": meta["opacity"],
        "layer_visible": True,
        "uploaded_by": src.get("uploaded_by"),
        "uploaded_by_name": src.get("uploaded_by_name"),
        "uploaded_by_role": src.get("uploaded_by_role"),
        "uploaded_at": _now_iso(),
        "converted_from_id": model_id,
        "converted_from_filename": src.get("filename"),
        "conversion_engine": "blender",
        "object_path": glb_object_path,
    }
    await db.digital_twin_models.insert_one(converted_doc)
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"model_url": glb_public_path, "updated_at": _now_iso()},
         "$inc": {"model_count": 1}},
    )
    await _update_conversion(
        model_id,
        conversion_status="completed",
        conversion_percent=100,
        conversion_completed_at=_now_iso(),
        converted_model_id=converted_doc["id"],
    )
    logger.info(f"[Blender] {src.get('ext')}→GLB done: {model_id} → {converted_doc['id']} ({bytes_written} bytes)")


async def _run_skp_to_glb_conversion(model_id: str) -> None:
    archive = await db.digital_twin_models.find_one({"id": model_id})
    if not archive:
        return
    project_id = archive["project_id"]
    src_path = UPLOAD_ROOT / project_id / archive["stored_as"]
    if not src_path.exists():
        restored = await storage_service.ensure_dt_local("model", project_id, archive["stored_as"])
        if restored:
            src_path = restored
    if not src_path.exists():
        await _update_conversion(model_id, conversion_status="failed", conversion_error="Source .skp file missing on disk.")
        return

    # 1) Create CC job
    try:
        await _update_conversion(model_id, conversion_status="uploading", conversion_percent=5)
        cc_job = await _ccv.create_skp_to_glb_job()
        cc_job_id = cc_job["id"]
        await _update_conversion(model_id, cloudconvert_job_id=cc_job_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("[CloudConvert] create job failed")
        await _update_conversion(model_id, conversion_status="failed", conversion_error=f"Create job: {e}")
        return

    # 2) Upload the .skp file (uses the import/upload task's signed form)
    try:
        await _ccv.upload_file_for_import_task(cc_job, str(src_path), archive["filename"])
        await _update_conversion(model_id, conversion_status="converting", conversion_percent=20)
    except Exception as e:  # noqa: BLE001
        logger.exception("[CloudConvert] upload failed")
        await _update_conversion(model_id, conversion_status="failed", conversion_error=f"Upload: {e}")
        return

    # 3) Poll until job is finished or errored (max ~30 min)
    max_polls = 360  # 360 * 5s = 30 min
    finished_job = None
    for i in range(max_polls):
        await asyncio.sleep(5)
        try:
            job_state = await _ccv.get_job(cc_job_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[CloudConvert] poll error (attempt {i}): {e}")
            continue
        summary = _ccv.aggregate_job_status(job_state)
        # Map CloudConvert progress to our 20-85 range.
        pct = 20
        if summary["convert_percent"] is not None:
            pct = 20 + int(summary["convert_percent"] * 0.65)
        await _update_conversion(model_id, conversion_percent=pct)
        if summary["cc_status"] == "finished":
            finished_job = job_state
            break
        if summary["cc_status"] == "error":
            await _update_conversion(
                model_id,
                conversion_status="failed",
                conversion_error=summary.get("error_message") or "CloudConvert reported error.",
            )
            return
    if finished_job is None:
        await _update_conversion(model_id, conversion_status="failed", conversion_error="Conversion timeout (30 min).")
        return

    # 4) Pull export URL + stream the .glb to local disk
    try:
        export_url, export_filename = _ccv.extract_export_file_url(finished_job)
    except Exception as e:  # noqa: BLE001
        await _update_conversion(model_id, conversion_status="failed", conversion_error=f"Export URL: {e}")
        return

    await _update_conversion(model_id, conversion_status="downloading", conversion_percent=90)
    glb_safe = f"{uuid.uuid4().hex[:12]}.glb"
    glb_path = UPLOAD_ROOT / project_id / glb_safe
    try:
        bytes_written = await _ccv.download_file(export_url, str(glb_path))
    except Exception as e:  # noqa: BLE001
        logger.exception("[CloudConvert] download failed")
        await _update_conversion(model_id, conversion_status="failed", conversion_error=f"Download: {e}")
        return

    # 5) Insert the converted .glb as a sibling layer linked to the same project.
    norm_layer = archive.get("layer_type") or "structure"
    meta = LAYER_DEFAULTS_FOR_CONVERT.get(norm_layer, LAYER_DEFAULTS_FOR_CONVERT["structure"])
    glb_public_path = f"/api/digital-twin/files/{project_id}/{glb_safe}"
    try:
        glb_object_path = await storage_service.store_dt_bytes(
            "model", project_id, glb_safe, glb_path.read_bytes(), "model/gltf-binary")
    except Exception:  # noqa: BLE001
        glb_object_path = None
    converted_doc = {
        "id": _new_id(),
        "project_id": project_id,
        "filename": export_filename or (Path(archive["filename"]).stem + ".glb"),
        "stored_as": glb_safe,
        "size_bytes": bytes_written,
        "url": glb_public_path,
        "kind": "model",
        "ext": ".glb",
        "layer_type": norm_layer,
        "layer_label": meta["label"],
        "layer_color": meta["color"],
        "layer_opacity": meta["opacity"],
        "layer_visible": True,
        "uploaded_by": archive.get("uploaded_by"),
        "uploaded_by_name": archive.get("uploaded_by_name"),
        "uploaded_by_role": archive.get("uploaded_by_role"),
        "uploaded_at": _now_iso(),
        "converted_from_id": model_id,
        "converted_from_filename": archive.get("filename"),
        "object_path": glb_object_path,
    }
    await db.digital_twin_models.insert_one(converted_doc)
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"model_url": glb_public_path, "updated_at": _now_iso()},
         "$inc": {"model_count": 1}},
    )
    await _update_conversion(
        model_id,
        conversion_status="completed",
        conversion_percent=100,
        conversion_completed_at=_now_iso(),
        converted_model_id=converted_doc["id"],
    )
    logger.info(f"[CloudConvert] SKP→GLB done: {model_id} → {converted_doc['id']} ({bytes_written} bytes)")


@router.get("/conversions/{model_id}/status")
async def get_conversion_status(model_id: str, user: dict = Depends(get_current_user)):
    """Polling endpoint — frontend hits this every 5s while a .skp is converting.

    Returns:
      { status, percent, error, converted_model_id, converted_url }
    """
    await _ensure_dt_ingest_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    await _ensure_project_access(doc["project_id"], user)
    converted_url = None
    if doc.get("converted_model_id"):
        sibling = await db.digital_twin_models.find_one({"id": doc["converted_model_id"]})
        if sibling:
            converted_url = sibling.get("url")
    return {
        "model_id": model_id,
        "status": doc.get("conversion_status", "n/a"),
        "percent": doc.get("conversion_percent", 0),
        "error": doc.get("conversion_error"),
        "converted_model_id": doc.get("converted_model_id"),
        "converted_url": converted_url,
        "cc_job_id": doc.get("cloudconvert_job_id"),
        "started_at": doc.get("conversion_started_at"),
        "completed_at": doc.get("conversion_completed_at"),
    }


@router.post("/conversions/{model_id}/retry")
async def retry_conversion(model_id: str, user: dict = Depends(get_current_user)):
    """Re-trigger conversion (owner / admin / operator only). Auto-selects engine."""
    await _ensure_dt_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    proj = await _ensure_project_access(doc["project_id"], user)
    if user.get("role") not in ("admin", "operator") and proj.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only the project owner can retry conversion.")
    ext = doc.get("ext")
    if ext == ".skp":
        raise HTTPException(
            400,
            "Modelele SketchUp (.skp) nu pot fi convertite pe server (SketchUp nu oferă un SDK Linux, "
            "iar serviciile de conversie nu acceptă .skp → .glb). Fișierul e stocat intact și descărcabil. "
            "Exportă din SketchUp .glb/.gltf (2025+: File → Export → glTF) sau .dae (COLLADA) și încarcă "
            "versiunea exportată — sau folosește Trimble Connect pentru vizualizare nativă.",
        )
    if ext in BLENDER_CONVERT_EXTS:
        if not _blender.is_enabled():
            raise HTTPException(503, "Conversia Blender nu este disponibilă pe acest server.")
        engine = "blender"
        runner = _run_blender_conversion
    else:
        raise HTTPException(400, f"Format {ext} nu necesită conversie.")
    await _update_conversion(
        model_id,
        conversion_status="pending",
        conversion_percent=0,
        conversion_error=None,
        conversion_started_at=_now_iso(),
        conversion_engine=engine,
    )
    asyncio.create_task(runner(model_id))
    return {"ok": True, "model_id": model_id, "status": "pending", "engine": engine}


# ============= MULTI-LAYER VIEWER ENDPOINTS =============
@router.get("/projects/{project_id}/models")
async def list_project_models(project_id: str, user: dict = Depends(get_current_user)):
    """List all uploaded models for a project.

    Response is a superset serving both consumers:
      • multi-layer viewer → `models` (.glb/.gltf layers) + `archives` (.skp)
      • model versions list → `items` (everything, newest first) + `count`
    """
    await _ensure_dt_ingest_access(user)
    await _ensure_project_access(project_id, user)
    docs = await db.digital_twin_models.find({"project_id": project_id}).sort("uploaded_at", -1).to_list(50)
    items, models, archives = [], [], []
    for d in docs:
        clean = _clean(d)
        items.append(clean)
        if d.get("kind") == "archive":
            archives.append(clean)
        else:
            models.append(clean)
    return {
        "models": models,
        "archives": archives,
        "total": len(items),
        "items": items,
        "count": len(items),
    }


class _LayerUpdateIn(BaseModel):
    layer_type: Optional[str] = Field(None, max_length=20)
    layer_label: Optional[str] = Field(None, max_length=80)
    layer_color: Optional[str] = Field(None, max_length=20)
    layer_opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    layer_visible: Optional[bool] = None
    # P1 — ProfessionalModel metadata / versionare / vizibilitate
    version: Optional[int] = Field(None, ge=1, le=9999)
    version_label: Optional[str] = Field(None, max_length=60)
    status: Optional[str] = Field(None, max_length=20)
    visibility: Optional[str] = Field(None, max_length=30)
    source: Optional[str] = Field(None, max_length=40)
    change_reason: Optional[str] = Field(None, max_length=300)
    supersedes: Optional[str] = Field(None, max_length=40)
    # P0/STEP D — trust & provenance (readiness, non-breaking)
    confidence: Optional[str] = Field(None, max_length=20)
    verification_status: Optional[str] = Field(None, max_length=30)
    completeness: Optional[int] = Field(None, ge=0, le=100)


@router.patch("/models/{model_id}")
async def update_model_layer(
    model_id: str,
    payload: _LayerUpdateIn,
    user: dict = Depends(get_current_user),
):
    """Update a model's layer visuals AND ProfessionalModel metadata (version/status/visibility/source).

    Versionare non-destructivă: setând `supersedes=<model_id>`, modelul vechi e marcat
    `superseded_by` + `status=superseded` (rămâne în istoric, NU se șterge).
    """
    await _ensure_dt_ingest_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    # Only project members + admin/operator can edit
    await _ensure_project_access(doc["project_id"], user)
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(400, "Nothing to update.")
    if "status" in update and update["status"] not in _MODEL_STATUSES:
        raise HTTPException(400, f"status invalid. Permis: {', '.join(sorted(_MODEL_STATUSES))}")
    if "visibility" in update and update["visibility"] not in _MODEL_VISIBILITIES:
        raise HTTPException(400, f"visibility invalid. Permis: {', '.join(sorted(_MODEL_VISIBILITIES))}")
    if "confidence" in update and update["confidence"] not in _MODEL_CONFIDENCE:
        raise HTTPException(400, f"confidence invalid. Permis: {', '.join(sorted(_MODEL_CONFIDENCE))}")
    if "verification_status" in update and update["verification_status"] not in _MODEL_VERIFICATION:
        raise HTTPException(400, f"verification_status invalid. Permis: {', '.join(sorted(_MODEL_VERIFICATION))}")
    if "source" in update and update["source"] not in _MODEL_SOURCES:
        raise HTTPException(400, f"source invalid. Permis: {', '.join(sorted(_MODEL_SOURCES))}")
    supersedes = update.get("supersedes")
    if supersedes:
        if supersedes == model_id:
            raise HTTPException(400, "Un model nu se poate înlocui pe sine.")
        target = await db.digital_twin_models.find_one({"id": supersedes})
        if not target or target.get("project_id") != doc["project_id"]:
            raise HTTPException(400, "Modelul de înlocuit nu aparține aceluiași proiect.")
        await db.digital_twin_models.update_one(
            {"id": supersedes},
            {"$set": {"superseded_by": model_id, "status": "superseded", "updated_at": _now_iso()}},
        )
    update["updated_at"] = _now_iso()
    await db.digital_twin_models.update_one({"id": model_id}, {"$set": update})
    refreshed = await db.digital_twin_models.find_one({"id": model_id})
    return _clean(refreshed)


@router.delete("/models/{model_id}")
async def delete_model_layer(model_id: str, user: dict = Depends(get_current_user)):
    """Remove a model file from a project (owner / admin / operator only)."""
    await _ensure_dt_ingest_access(user)
    doc = await db.digital_twin_models.find_one({"id": model_id})
    if not doc:
        raise HTTPException(404, "Model not found.")
    proj = await _ensure_project_access(doc["project_id"], user)
    if user.get("role") not in ("admin", "operator") and proj.get("owner_id") != user["id"]:
        raise HTTPException(403, "Only the project owner can delete models.")
    # Best-effort filesystem cleanup — never block the DB delete on filesystem errors
    try:
        path = UPLOAD_ROOT / doc["project_id"] / doc["stored_as"]
        if path.exists():
            path.unlink()
    except Exception as _e:  # noqa: BLE001
        logger.warning(f"[dt] failed to remove file {doc.get('stored_as')}: {_e}")
    await db.digital_twin_models.delete_one({"id": model_id})
    await storage_service.add_usage(proj.get("owner_id"), -(doc.get("size_bytes") or 0), "digital_twin")
    # Decrement project counter
    await db.digital_twin_projects.update_one(
        {"id": doc["project_id"]},
        {"$inc": {"model_count": -1}, "$set": {"updated_at": _now_iso()}},
    )
    return {"ok": True, "id": model_id}


@router.get("/files/{project_id}/{filename}")
async def serve_model_file(project_id: str, filename: str, user: dict = Depends(get_current_user)):
    """Serve uploaded model files. Permission-checked: only project members + admin/operator."""
    await _ensure_dt_ingest_access(user)
    await _ensure_project_access(project_id, user)
    # Sanitize: filename must be a bare name, no path traversal
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        raise HTTPException(400, "Invalid filename.")
    file_path = UPLOAD_ROOT / project_id / filename
    if not file_path.exists() or not file_path.is_file():
        # Files live durably in Object Storage; disk is only a cache. Restore on demand.
        file_path = await storage_service.ensure_dt_local("model", project_id, filename)
        if not file_path or not file_path.exists():
            raise HTTPException(404, "Model file not found.")
    fn_lower = filename.lower()
    if fn_lower.endswith(".glb"):
        media = "model/gltf-binary"
    elif fn_lower.endswith(".gltf"):
        media = "model/gltf+json"
    elif fn_lower.endswith(".skp"):
        media = "application/octet-stream"
    elif fn_lower.endswith(".png"):
        media = "image/png"
    elif fn_lower.endswith((".jpg", ".jpeg")):
        media = "image/jpeg"
    elif fn_lower.endswith(".webp"):
        media = "image/webp"
    else:
        media = "application/octet-stream"
    return FileResponse(
        file_path,
        media_type=media,
        filename=filename,
        headers={"Cache-Control": "private, max-age=3600"},
    )


# ----------------- pins (3D markup) -----------------

class Pin3D(BaseModel):
    x: float
    y: float
    z: float


class PinCreate(BaseModel):
    model_id: Optional[str] = None
    position: Pin3D
    element_id: Optional[str] = None  # IFC GlobalId if available
    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    priority: str = Field("normal", pattern="^(low|normal|high|urgent)$")
    category: str = Field("general", pattern="^(general|structural|plumbing|electrical|hvac|finish|defect)$")


@router.post("/projects/{project_id}/pins")
async def create_pin(project_id: str, payload: PinCreate, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    project = await _ensure_project_access(project_id, user)
    pid = _new_id()
    doc = {
        "id": pid,
        "project_id": project_id,
        "model_id": payload.model_id,
        "position": payload.position.model_dump(),
        "element_id": payload.element_id,
        "title": payload.title.strip(),
        "description": (payload.description or "").strip(),
        "priority": payload.priority,
        "category": payload.category,
        "status": "open",
        "author_id": user["id"],
        "author_name": user.get("name") or user.get("email"),
        "author_role": user.get("role"),
        "comment_count": 0,
        "plan_anchors": [],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.digital_twin_pins.insert_one(doc)
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"updated_at": _now_iso()}, "$inc": {"pin_count": 1}},
    )
    # Notify stakeholders (fire-and-forget): in-app + email + push
    stakeholders = await _project_stakeholders(project, exclude_user_id=user["id"])
    actor_name = user.get("name") or user.get("email") or "Utilizator"
    project_name = project.get("name", "Proiect")
    for s in stakeholders:
        await notify(
            s["id"],
            f"📌 Pin nou pe {project_name}",
            f"{actor_name}: {doc['title']}",
            type_="dt_pin",
            link="/digital-twin",
        )
        await send_template(
            tpl_dt_pin_created,
            s["name"], project_name, doc["title"], doc["category"], doc["priority"], actor_name,
            to=s["email"],
        )
    return _clean(doc)


@router.get("/projects/{project_id}/pins")
async def list_pins(
    project_id: str,
    status: Optional[str] = Query(None, pattern="^(open|in_review|resolved|rejected)$"),
    category: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    await _ensure_dt_access(user)
    await _ensure_project_access(project_id, user)
    q = {"project_id": project_id}
    if status:
        q["status"] = status
    if category:
        q["category"] = category
    items = []
    async for p in db.digital_twin_pins.find(q).sort("created_at", -1).limit(500):
        items.append(_clean(p))
    return {"items": items, "count": len(items)}


class PinUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|in_review|resolved|rejected)$")
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|urgent)$")
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)


@router.patch("/pins/{pin_id}")
async def update_pin(pin_id: str, payload: PinUpdate, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    project = await _ensure_project_access(pin["project_id"], user)
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        return _clean(pin)
    old_status = pin.get("status")
    updates["updated_at"] = _now_iso()
    await db.digital_twin_pins.update_one({"id": pin_id}, {"$set": updates})
    pin_after = await db.digital_twin_pins.find_one({"id": pin_id})

    # Phase G: workflow notification on status change
    new_status = updates.get("status")
    if new_status and new_status != old_status:
        actor_name = user.get("name") or user.get("email") or "Utilizator"
        project_name = project.get("name", "Proiect")
        # Notify pin author (if not the actor) + all stakeholders
        recipients_ids = set()
        if pin.get("author_id") and pin["author_id"] != user["id"]:
            recipients_ids.add(pin["author_id"])
        stakeholders = await _project_stakeholders(project, exclude_user_id=user["id"])
        status_label = {"open": "Deschis", "in_review": "În analiză", "resolved": "Rezolvat", "rejected": "Respins"}.get(new_status, new_status)
        for s in stakeholders:
            recipients_ids.add(s["id"])
            await send_template(
                tpl_dt_pin_status_changed,
                s["name"], project_name, pin_after["title"], old_status, new_status, actor_name,
                to=s["email"],
            )
        # Always also email the original author if not the actor
        if pin.get("author_id") and pin["author_id"] != user["id"]:
            author = await db.users.find_one(_user_filter(pin["author_id"]), {"_id": 1, "email": 1, "name": 1})
            if author and author.get("email") and not any(s["id"] == pin["author_id"] for s in stakeholders):
                await send_template(
                    tpl_dt_pin_status_changed,
                    author.get("name") or author["email"], project_name, pin_after["title"], old_status, new_status, actor_name,
                    to=author["email"],
                )
        # In-app notification for everyone touched
        for uid in recipients_ids:
            await notify(
                uid,
                f"🔄 Pin {status_label.lower()}",
                f"{pin_after['title']} pe {project_name}",
                type_="dt_pin_status",
                link="/digital-twin",
            )
    return _clean(pin_after)


@router.delete("/pins/{pin_id}")
async def delete_pin(pin_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    proj = await _ensure_project_access(pin["project_id"], user)
    # Only author / project owner / admin / operator can delete.
    if (
        user.get("role") not in ("admin", "operator")
        and pin.get("author_id") != user["id"]
        and proj.get("owner_id") != user["id"]
    ):
        raise HTTPException(403, "Cannot delete this pin.")
    await db.digital_twin_pins.delete_one({"id": pin_id})
    await db.digital_twin_comments.delete_many({"pin_id": pin_id})
    await db.digital_twin_projects.update_one(
        {"id": pin["project_id"]},
        {"$inc": {"pin_count": -1}, "$set": {"updated_at": _now_iso()}},
    )
    return {"ok": True}


# ----------------- pin → plan anchors (Phase H: 3D ↔ 2D sync) -----------------

class PlanAnchorIn(BaseModel):
    plan_id: str
    page: int = Field(1, ge=1, le=200)
    x_pct: float = Field(..., ge=0.0, le=1.0)
    y_pct: float = Field(..., ge=0.0, le=1.0)


@router.post("/pins/{pin_id}/anchors")
async def add_pin_anchor(pin_id: str, payload: PlanAnchorIn, user: dict = Depends(get_current_user)):
    """Anchor a 3D pin to a (x_pct, y_pct) on a 2D plan PDF page."""
    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    await _ensure_project_access(pin["project_id"], user)
    # Verify the plan belongs to the same project
    plan = await db.digital_twin_plans.find_one({"id": payload.plan_id, "project_id": pin["project_id"]})
    if not plan:
        raise HTTPException(404, "Plan not found in this project.")
    # Bug fix: validate against the actual PDF page count if known
    plan_pages = int(plan.get("page_count") or 0)
    if plan_pages and payload.page > plan_pages:
        raise HTTPException(400, f"Pagina {payload.page} nu există. Planul are doar {plan_pages} pagini.")
    anchor = {
        "id": _new_id(),
        "plan_id": payload.plan_id,
        "plan_title": plan.get("title"),
        "page": payload.page,
        "x_pct": payload.x_pct,
        "y_pct": payload.y_pct,
        "created_at": _now_iso(),
        "created_by": user["id"],
        "created_by_name": user.get("name") or user.get("email"),
    }
    # Replace any existing anchor on the same (plan_id, page) to keep one marker per page per pin
    existing = [a for a in (pin.get("plan_anchors") or []) if not (a.get("plan_id") == payload.plan_id and int(a.get("page", 1)) == payload.page)]
    existing.append(anchor)
    await db.digital_twin_pins.update_one(
        {"id": pin_id},
        {"$set": {"plan_anchors": existing, "updated_at": _now_iso()}},
    )
    return {"ok": True, "anchor": anchor, "plan_anchors": existing}


@router.delete("/pins/{pin_id}/anchors/{anchor_id}")
async def remove_pin_anchor(pin_id: str, anchor_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    await _ensure_project_access(pin["project_id"], user)
    anchors = pin.get("plan_anchors") or []
    target = next((a for a in anchors if a.get("id") == anchor_id), None)
    if not target:
        raise HTTPException(404, "Anchor not found.")
    # Bug fix: any project member (verified via _ensure_project_access) can cleanup anchors.
    # _ensure_project_access already raised 403 for non-members. No extra owner-only gate.
    new_anchors = [a for a in anchors if a.get("id") != anchor_id]
    await db.digital_twin_pins.update_one(
        {"id": pin_id},
        {"$set": {"plan_anchors": new_anchors, "updated_at": _now_iso()}},
    )
    return {"ok": True, "plan_anchors": new_anchors}


# ----------------- Phase I: Issue Report PDF + Email -----------------

APP_URL = os.environ.get("APP_URL", "https://propmanage.io").rstrip("/")
REPORT_APPROVAL_TTL_DAYS = 30


def _make_report_approval_token(pin_id: str, report_id: str, recipient_email: str) -> str:
    payload = {
        "type": "dt_report_approval",
        "pin_id": pin_id,
        "report_id": report_id,
        "recipient": recipient_email.lower().strip(),
        "exp": datetime.now(timezone.utc) + timedelta(days=REPORT_APPROVAL_TTL_DAYS),
    }
    return _jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_report_approval_token(token: str) -> dict:
    try:
        data = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except _jwt.ExpiredSignatureError:
        raise HTTPException(410, "Linkul a expirat (valid 30 zile de la trimitere).")
    except Exception:
        raise HTTPException(400, "Token invalid.")
    if data.get("type") != "dt_report_approval":
        raise HTTPException(400, "Token de tip greșit.")
    return data


class IssueReportIn(BaseModel):
    recipient_email: Optional[str] = Field(None, description="Override recipient; if absent, use project owner email.")
    custom_message: Optional[str] = Field(None, max_length=4000)
    screenshot_3d: Optional[str] = Field(None, description="Base64 PNG capture of the viewer canvas.")
    include_thread: bool = True


@router.post("/pins/{pin_id}/issue-report")
async def send_issue_report(pin_id: str, payload: IssueReportIn, user: dict = Depends(get_current_user)):
    """Generate a PDF report for a pin and email it to the architect/owner.

    Includes: pin meta, description, optional custom message, 3D screenshot,
    2D plan extract from first anchor, comments thread.
    """
    from dt_issue_report import build_issue_report_pdf

    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    project = await _ensure_project_access(pin["project_id"], user)

    # Resolve recipient email
    recipient_email = (payload.recipient_email or "").strip().lower()
    recipient_name = None
    if not recipient_email:
        # Default: project owner
        owner_id = project.get("owner_id")
        if owner_id:
            owner = await db.users.find_one(_user_filter(owner_id), {"_id": 1, "email": 1, "name": 1})
            if owner and owner.get("email"):
                recipient_email = owner["email"]
                recipient_name = owner.get("name")
    if not recipient_email:
        raise HTTPException(400, "Nu există email destinatar (nu există owner sau email explicit).")
    if not recipient_name:
        # Try to resolve a friendly name for the override email
        u = await db.users.find_one({"email": recipient_email}, {"_id": 1, "email": 1, "name": 1})
        recipient_name = (u.get("name") if u else None) or recipient_email.split("@")[0]

    # Collect comments
    comments = []
    if payload.include_thread:
        async for c in db.digital_twin_comments.find({"pin_id": pin_id}).sort("created_at", 1):
            comments.append(_clean(c))

    # Plan extract from first anchor (if any)
    plan_file_path = None
    plan_page = 1
    plan_title = None
    anchors = pin.get("plan_anchors") or []
    if anchors:
        first = anchors[0]
        plan = await db.digital_twin_plans.find_one({"id": first.get("plan_id")})
        if plan:
            plan_title = plan.get("title")
            plan_page = int(first.get("page", 1))
            candidate = UPLOAD_ROOT / pin["project_id"] / "plans" / plan.get("stored_as", "")
            if candidate.exists() and candidate.is_file():
                plan_file_path = str(candidate)

    # Build PDF
    pdf_buf = build_issue_report_pdf(
        project=project,
        pin=pin,
        comments=comments,
        sender={"name": user.get("name") or user.get("email"), "email": user.get("email"), "role": user.get("role")},
        custom_message=payload.custom_message,
        screenshot_3d_b64=payload.screenshot_3d,
        plan_file_path=plan_file_path,
        plan_page=plan_page,
        plan_title=plan_title,
    )
    pdf_bytes = pdf_buf.getvalue()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    pdf_filename = f"raport_{pin.get('title', 'pin')[:40].replace(' ', '_')}.pdf"

    # Generate signed approval token (30-day TTL)
    report_id = _new_id()
    approval_token = _make_report_approval_token(pin_id, report_id, recipient_email)
    approval_url = f"{APP_URL}/report-respond/{approval_token}"

    # Send the email with attachment + approval CTAs
    tpl = tpl_dt_issue_report(
        recipient_name=recipient_name,
        project_name=project.get("name", "Proiect"),
        pin_title=pin.get("title", "—"),
        pin_category=pin.get("category", "general"),
        pin_priority=pin.get("priority", "normal"),
        pin_status=pin.get("status", "open"),
        sender_name=user.get("name") or user.get("email") or "Utilizator",
        sender_role=user.get("role") or "—",
        custom_message=payload.custom_message,
        approval_url=approval_url,
    )
    await send_email_with_attachments(
        to=recipient_email,
        subject=tpl["subject"],
        html=tpl["html"],
        attachments=[{"filename": pdf_filename, "content": pdf_b64, "type": "application/pdf"}],
    )

    # Log to pin history
    history_entry = {
        "id": report_id,
        "type": "issue_report_sent",
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "sender_id": user["id"],
        "sender_name": user.get("name") or user.get("email"),
        "sender_role": user.get("role"),
        "custom_message_preview": (payload.custom_message or "")[:120],
        "comment_count": len(comments),
        "has_screenshot": bool(payload.screenshot_3d),
        "has_plan_extract": bool(plan_file_path),
        "pdf_size_bytes": len(pdf_bytes),
        "approval_url": approval_url,
        "approval_status": "pending",
        "created_at": _now_iso(),
    }
    await db.digital_twin_pins.update_one(
        {"id": pin_id},
        {"$push": {"report_history": history_entry}, "$set": {"updated_at": _now_iso()}},
    )

    # In-app notification to recipient (if known user)
    recipient_user = await db.users.find_one({"email": recipient_email}, {"_id": 1})
    if recipient_user:
        rid = str(recipient_user["_id"])
        await notify(
            rid,
            f"🚨 Raport problemă: {pin.get('title', 'Pin')}",
            f"{history_entry['sender_name']} a trimis raport PDF pe {project.get('name', 'proiect')}",
            type_="dt_issue_report",
            link="/digital-twin",
        )

    return {
        "ok": True,
        "report": history_entry,
        "pdf_size_bytes": len(pdf_bytes),
        "recipient_email": recipient_email,
    }


# ----------------- Public approval endpoints (no auth — token-validated) -----------------

@router.get("/reports/approve/info", tags=["digital-twin-public"])
async def report_approval_info(token: str = Query(...)):
    """Resolve a signed approval token and return the linked report context (public, no auth)."""
    data = _decode_report_approval_token(token)
    pin = await db.digital_twin_pins.find_one({"id": data["pin_id"]})
    if not pin:
        raise HTTPException(404, "Pin-ul nu mai există.")
    report = next(
        (h for h in (pin.get("report_history") or []) if h.get("id") == data["report_id"]),
        None,
    )
    if not report:
        raise HTTPException(404, "Raportul nu a fost găsit.")
    project = await db.digital_twin_projects.find_one({"id": pin["project_id"]})
    return {
        "ok": True,
        "pin_title": pin.get("title"),
        "pin_category": pin.get("category"),
        "pin_priority": pin.get("priority"),
        "pin_status": pin.get("status"),
        "project_name": project.get("name") if project else "—",
        "sender_name": report.get("sender_name"),
        "recipient_name": report.get("recipient_name"),
        "recipient_email": report.get("recipient_email"),
        "custom_message_preview": report.get("custom_message_preview"),
        "comment_count": report.get("comment_count"),
        "has_screenshot": report.get("has_screenshot"),
        "has_plan_extract": report.get("has_plan_extract"),
        "created_at": report.get("created_at"),
        "approval_status": report.get("approval_status", "pending"),
        "decision": report.get("decision"),
        "decision_comment": report.get("decision_comment"),
        "decided_at": report.get("decided_at"),
    }


class ReportDecisionIn(BaseModel):
    token: str
    decision: str = Field(..., pattern="^(confirmed|needs_changes)$")
    comment: Optional[str] = Field(None, max_length=2000)


@router.post("/reports/approve/decide", tags=["digital-twin-public"])
async def report_approval_decide(payload: ReportDecisionIn):
    """Record the recipient's decision on a report (public, token-validated, single-use semantics)."""
    data = _decode_report_approval_token(payload.token)
    pin = await db.digital_twin_pins.find_one({"id": data["pin_id"]})
    if not pin:
        raise HTTPException(404, "Pin-ul nu mai există.")
    report = next(
        (h for h in (pin.get("report_history") or []) if h.get("id") == data["report_id"]),
        None,
    )
    if not report:
        raise HTTPException(404, "Raportul nu a fost găsit.")
    if report.get("approval_status") and report["approval_status"] != "pending":
        raise HTTPException(409, "Ai răspuns deja la acest raport. Nu poți schimba decizia ulterior.")

    now_iso = _now_iso()
    update = {
        "report_history.$[r].approval_status": payload.decision,
        "report_history.$[r].decision": payload.decision,
        "report_history.$[r].decision_comment": (payload.comment or "").strip(),
        "report_history.$[r].decided_at": now_iso,
        "report_history.$[r].decided_by_email": data["recipient"],
        "updated_at": now_iso,
    }
    await db.digital_twin_pins.update_one(
        {"id": data["pin_id"]},
        {"$set": update},
        array_filters=[{"r.id": data["report_id"]}],
    )

    # Notify the original sender (in-app + email if available)
    sender_id = report.get("sender_id")
    if sender_id:
        sender = await db.users.find_one(_user_filter(sender_id), {"_id": 1, "email": 1, "name": 1})
        decision_label = "Confirmat" if payload.decision == "confirmed" else "Necesită modificări"
        emoji = "✅" if payload.decision == "confirmed" else "📝"
        await notify(
            sender_id,
            f"{emoji} Raport {decision_label.lower()}: {pin.get('title', 'Pin')}",
            f"{report.get('recipient_name') or data['recipient']} a răspuns la raportul tău.",
            type_="dt_report_decision",
            link="/digital-twin",
        )
        if sender and sender.get("email"):
            from email_service import _layout, send_email  # noqa: PLC0415
            project = await db.digital_twin_projects.find_one({"id": pin["project_id"]})
            project_name = project.get("name", "Proiect") if project else "—"
            color = "#10b981" if payload.decision == "confirmed" else "#f59e0b"
            comment_block = ""
            if payload.comment and payload.comment.strip():
                comment_block = f"""
                  <div style="background:#0f172a; border-left:3px solid {color}; padding:14px 18px; border-radius:12px; margin:18px 0;">
                    <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:{color}; margin-bottom:6px;">Răspuns destinatar</div>
                    <div style="color:#e5e5e5; line-height:1.6; white-space:pre-wrap;">{payload.comment.strip()}</div>
                  </div>
                """
            html_body = f"""
              <p>Bună {sender.get('name') or sender['email']},</p>
              <p><strong style="color:{color};">{report.get('recipient_name') or data['recipient']}</strong> a răspuns la raportul tău pentru <em>"{pin.get('title')}"</em> din proiectul <strong>{project_name}</strong>.</p>
              <div style="background:{color}15; border:1px solid {color}40; border-radius:14px; padding:18px; margin:18px 0; text-align:center;">
                <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:{color}; margin-bottom:6px; font-weight:700;">Decizie</div>
                <div style="color:{color}; font-size:24px; font-weight:700;">{emoji} {decision_label}</div>
              </div>
              {comment_block}
            """
            tpl_html = _layout(
                "Răspuns la raport",
                f"{pin.get('title')} → {decision_label}",
                html_body,
                f"{APP_URL}/digital-twin",
                "Vezi pin-ul în viewer",
            )
            await send_email(sender["email"], f"{emoji} Răspuns raport: {pin.get('title')}", tpl_html)

    return {
        "ok": True,
        "decision": payload.decision,
        "decided_at": now_iso,
    }




# ----------------- Sent reports dashboard + reminder (Phase I+) -----------------

@router.get("/reports/sent")
async def list_sent_reports(
    status: Optional[str] = Query(None, pattern="^(pending|confirmed|needs_changes|all)?$"),
    overdue_only: bool = Query(False),
    limit: int = Query(200, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    """List all issue reports the current user has sent (across all their pins)."""
    pipeline = [
        {"$match": {"report_history.sender_id": user["id"]}},
        {"$project": {
            "_id": 0,
            "pin_id": "$id",
            "pin_title": "$title",
            "pin_category": "$category",
            "pin_priority": "$priority",
            "pin_status": "$status",
            "project_id": "$project_id",
            "report_history": "$report_history",
        }},
        {"$unwind": "$report_history"},
        {"$match": {"report_history.sender_id": user["id"]}},
        {"$sort": {"report_history.created_at": -1}},
        {"$limit": limit},
    ]
    raw = await db.digital_twin_pins.aggregate(pipeline).to_list(length=limit)
    # Resolve project names in bulk
    project_ids = list({r["project_id"] for r in raw})
    projects = {}
    if project_ids:
        async for p in db.digital_twin_projects.find({"id": {"$in": project_ids}}, {"_id": 0, "id": 1, "name": 1}):
            projects[p["id"]] = p.get("name")

    now = datetime.now(timezone.utc)
    items = []
    for r in raw:
        h = r["report_history"]
        h_status = h.get("approval_status", "pending")
        if status and status != "all" and h_status != status:
            continue
        # Compute age in days
        created_at = h.get("created_at")
        age_days = 0
        try:
            if created_at:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_days = max(0, (now - dt).days)
        except Exception:  # noqa: BLE001
            age_days = 0
        is_overdue = h_status == "pending" and age_days >= 7
        if overdue_only and not is_overdue:
            continue
        items.append({
            "report_id": h.get("id"),
            "pin_id": r["pin_id"],
            "pin_title": r["pin_title"],
            "pin_category": r["pin_category"],
            "pin_priority": r["pin_priority"],
            "pin_status": r["pin_status"],
            "project_id": r["project_id"],
            "project_name": projects.get(r["project_id"], "—"),
            "recipient_email": h.get("recipient_email"),
            "recipient_name": h.get("recipient_name"),
            "approval_status": h_status,
            "decision_comment": h.get("decision_comment"),
            "decided_at": h.get("decided_at"),
            "created_at": created_at,
            "age_days": age_days,
            "is_overdue": is_overdue,
            "has_screenshot": h.get("has_screenshot"),
            "has_plan_extract": h.get("has_plan_extract"),
            "pdf_size_bytes": h.get("pdf_size_bytes"),
            "approval_url": h.get("approval_url"),
            "reminders_sent": h.get("reminders_sent", []),
            "reminder_count": len(h.get("reminders_sent", []) or []),
            "auto_reminders_enabled": h.get("auto_reminders_enabled", True),
            "reminder_thresholds_days": h.get("reminder_thresholds_days") or [7, 14, 21],
            "paused_until": h.get("paused_until"),
            "auto_reminders_stopped": h.get("auto_reminders_stopped", False),
            "auto_reminders_fired_thresholds": h.get("auto_reminders_fired_thresholds") or [],
            "last_auto_reminder_at": h.get("last_auto_reminder_at"),
        })

    # Counters for UI badges
    counters = {
        "total": 0,
        "pending": 0,
        "confirmed": 0,
        "needs_changes": 0,
        "overdue": 0,
    }
    # Recount (without filter) for accurate badges
    all_pipeline = [
        {"$match": {"report_history.sender_id": user["id"]}},
        {"$unwind": "$report_history"},
        {"$match": {"report_history.sender_id": user["id"]}},
        {"$project": {"_id": 0, "approval_status": "$report_history.approval_status", "created_at": "$report_history.created_at"}},
    ]
    async for r in db.digital_twin_pins.aggregate(all_pipeline):
        counters["total"] += 1
        st = r.get("approval_status", "pending")
        if st in counters:
            counters[st] += 1
        if st == "pending":
            try:
                dt = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                if (now - dt).days >= 7:
                    counters["overdue"] += 1
            except Exception:  # noqa: BLE001
                pass

    return {"items": items, "count": len(items), "counters": counters}


@router.post("/reports/{report_id}/remind")
async def send_report_reminder(
    report_id: str,
    payload: dict = Body(default_factory=dict),
    user: dict = Depends(get_current_user),
):
    """Re-send the approval email for a still-pending report (same token, no PDF regen)."""
    # Find the pin owning this report by sender_id + report_id (security)
    pin = await db.digital_twin_pins.find_one({
        "report_history.id": report_id,
        "report_history.sender_id": user["id"],
    })
    if not pin:
        raise HTTPException(404, "Raport inexistent sau nu ești expeditorul.")
    custom_note = (payload.get("note") or "").strip() if isinstance(payload, dict) else ""
    if len(custom_note) > 1000:
        raise HTTPException(400, "Notă prea lungă (max 1000 caractere).")
    try:
        result = await _dispatch_reminder(pin, report_id, custom_note=custom_note, actor=user, auto=False)
    except ValueError as e:
        raise HTTPException(409, str(e)) from e
    return {"ok": True, **result}


class ReminderSettings(BaseModel):
    auto_reminders_enabled: Optional[bool] = None
    thresholds_days: Optional[List[int]] = None
    paused_until: Optional[str] = None  # ISO date, e.g. "2026-03-01"
    stopped: Optional[bool] = None


@router.patch("/reports/{report_id}/reminder-settings")
async def update_reminder_settings(
    report_id: str,
    payload: ReminderSettings,
    user: dict = Depends(get_current_user),
):
    """Configure auto-reminder behavior for a specific report (per-report opt-out/snooze/stop)."""
    pin = await db.digital_twin_pins.find_one({
        "report_history.id": report_id,
        "report_history.sender_id": user["id"],
    })
    if not pin:
        raise HTTPException(404, "Raport inexistent sau nu ești expeditorul.")
    updates = {}
    if payload.auto_reminders_enabled is not None:
        updates["report_history.$.auto_reminders_enabled"] = payload.auto_reminders_enabled
    if payload.thresholds_days is not None:
        clean = sorted({int(d) for d in payload.thresholds_days if 1 <= int(d) <= 365})
        if not clean:
            raise HTTPException(400, "Trebuie cel puțin un prag de reminder (între 1-365 zile).")
        updates["report_history.$.reminder_thresholds_days"] = clean
    if payload.paused_until is not None:
        if payload.paused_until == "":
            updates["report_history.$.paused_until"] = None
        else:
            try:
                _ = datetime.fromisoformat(payload.paused_until)
            except Exception:
                raise HTTPException(400, "Format dată invalid (folosește YYYY-MM-DD).")
            updates["report_history.$.paused_until"] = payload.paused_until
    if payload.stopped is not None:
        updates["report_history.$.auto_reminders_stopped"] = payload.stopped
    if not updates:
        raise HTTPException(400, "Nimic de actualizat.")
    updates["updated_at"] = _now_iso()
    await db.digital_twin_pins.update_one(
        {"id": pin["id"], "report_history.id": report_id},
        {"$set": updates},
    )
    pin2 = await db.digital_twin_pins.find_one({"id": pin["id"]})
    report = next((h for h in pin2.get("report_history") or [] if h.get("id") == report_id), None)
    return {
        "ok": True,
        "report_id": report_id,
        "auto_reminders_enabled": report.get("auto_reminders_enabled", True),
        "reminder_thresholds_days": report.get("reminder_thresholds_days") or [7, 14, 21],
        "paused_until": report.get("paused_until"),
        "auto_reminders_stopped": report.get("auto_reminders_stopped", False),
        "auto_reminders_fired_thresholds": report.get("auto_reminders_fired_thresholds") or [],
    }


async def _dispatch_reminder(
    pin: dict,
    report_id: str,
    custom_note: str,
    actor: Optional[dict],
    auto: bool = False,
) -> dict:
    """Internal helper: send reminder email + log entry. Raises ValueError if not pending."""
    report = next((h for h in pin.get("report_history") or [] if h.get("id") == report_id), None)
    if not report:
        raise ValueError("Raport inexistent.")
    if report.get("approval_status", "pending") != "pending":
        raise ValueError("Raportul a primit deja un răspuns — reminder nu mai e necesar.")
    approval_url = report.get("approval_url")
    if not approval_url:
        raise ValueError("Raport vechi fără approval_url.")

    project = await db.digital_twin_projects.find_one({"id": pin["project_id"]})
    project_name = project.get("name", "Proiect") if project else "—"

    from email_service import _layout, send_email  # noqa: PLC0415
    days_pending = 0
    try:
        if report.get("created_at"):
            dt = datetime.fromisoformat(report["created_at"].replace("Z", "+00:00"))
            days_pending = max(0, (datetime.now(timezone.utc) - dt).days)
    except Exception:  # noqa: BLE001
        days_pending = 0

    sender_name = (actor.get("name") if actor else None) or (actor.get("email") if actor else None) or report.get("sender_name") or "Sistem"

    note_block = ""
    if custom_note:
        note_block = f"""
          <div style="background:#0f172a; border-left:3px solid #d4ff3a; padding:14px 18px; border-radius:12px; margin:18px 0;">
            <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#d4ff3a; margin-bottom:6px;">Notă suplimentară</div>
            <div style="color:#e5e5e5; line-height:1.6; white-space:pre-wrap;">{custom_note}</div>
          </div>
        """
    auto_label = "🤖 Reminder automat" if auto else "Reminder amabil"
    body = f"""
      <p>Bună {report.get('recipient_name') or report.get('recipient_email')},</p>
      <p>Acesta este un <strong style="color:#f59e0b;">{auto_label.lower()}</strong> pentru raportul trimis de <strong style="color:#10b981;">{sender_name}</strong> acum <strong>{days_pending} zile</strong> pe proiectul <em>"{project_name}"</em>.</p>
      <div style="background:#1a1a1f; border:1px solid #ffffff15; border-radius:14px; padding:18px; margin:18px 0;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:#888893; margin-bottom:6px;">Pin în așteptare</div>
        <div style="color:#ffffff; font-size:17px; font-weight:600;">{pin.get('title', '—')}</div>
      </div>
      {note_block}
      <div style="background:#1a1a1f; border:1px solid #ffffff15; border-radius:14px; padding:22px; margin:22px 0; text-align:center;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#d4ff3a; margin-bottom:10px; font-weight:700;">⚡ Răspuns rapid · fără login</div>
        <table border="0" cellpadding="0" cellspacing="0" style="margin:0 auto;">
          <tr>
            <td style="padding:0 6px;">
              <a href="{approval_url}?decision=confirmed" style="display:inline-block; padding:12px 22px; border-radius:999px; background:#10b981; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700;">✅ Confirmat</a>
            </td>
            <td style="padding:0 6px;">
              <a href="{approval_url}?decision=needs_changes" style="display:inline-block; padding:12px 22px; border-radius:999px; background:#f59e0b; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700;">📝 Necesită modificări</a>
            </td>
          </tr>
        </table>
      </div>
    """
    subject_prefix = "🤖 Reminder automat:" if auto else "⏰ Reminder:"
    html = _layout(
        f"{auto_label} raport problemă",
        f"{pin.get('title', '—')} · pending de {days_pending} zile",
        body,
        approval_url,
        "Răspunde acum",
    )
    await send_email(report["recipient_email"], f"{subject_prefix} {pin.get('title', 'Raport')} · {project_name}", html)

    reminder_entry = {
        "id": _new_id(),
        "sent_at": _now_iso(),
        "sent_by": actor["id"] if actor else "system",
        "sent_by_name": sender_name,
        "note": custom_note,
        "days_pending_at_send": days_pending,
        "automatic": auto,
    }
    await db.digital_twin_pins.update_one(
        {"id": pin["id"], "report_history.id": report_id},
        {"$push": {"report_history.$.reminders_sent": reminder_entry},
         "$set": {"updated_at": _now_iso()}},
    )

    recipient_user = await db.users.find_one({"email": report["recipient_email"]}, {"_id": 1})
    if recipient_user:
        title_emoji = "🤖" if auto else "⏰"
        await notify(
            str(recipient_user["_id"]),
            f"{title_emoji} Reminder raport: {pin.get('title', 'Pin')}",
            f"{sender_name} așteaptă răspunsul tău de {days_pending} zile.",
            type_="dt_report_reminder",
            link="/digital-twin",
        )

    return {
        "reminder": reminder_entry,
        "recipient_email": report["recipient_email"],
        "days_pending": days_pending,
    }


async def run_dt_auto_reminders() -> dict:
    """Daily job: scan pending reports + send reminders at configured thresholds (default 7/14/21 days)."""
    now = datetime.now(timezone.utc)
    today_iso = now.date().isoformat()
    sent = 0
    skipped = 0
    failed = 0
    seen = 0
    pipeline = [
        {"$match": {"report_history": {"$elemMatch": {"approval_status": "pending"}}}},
        {"$project": {"_id": 0, "id": 1, "title": 1, "project_id": 1, "report_history": 1}},
    ]
    async for pin in db.digital_twin_pins.aggregate(pipeline):
        for h in pin.get("report_history") or []:
            seen += 1
            if h.get("approval_status", "pending") != "pending":
                continue
            if h.get("auto_reminders_stopped"):
                skipped += 1
                continue
            if h.get("auto_reminders_enabled") is False:
                skipped += 1
                continue
            paused = h.get("paused_until")
            if paused and paused >= today_iso:
                skipped += 1
                continue
            if not h.get("approval_url"):
                skipped += 1
                continue
            try:
                dt = datetime.fromisoformat(h["created_at"].replace("Z", "+00:00"))
            except Exception:
                skipped += 1
                continue
            age_days = max(0, (now - dt).days)
            thresholds = h.get("reminder_thresholds_days") or [7, 14, 21]
            fired = set(h.get("auto_reminders_fired_thresholds") or [])
            due_threshold = None
            for th in sorted(thresholds):
                if age_days >= th and th not in fired:
                    due_threshold = th
                    break
            if due_threshold is None:
                continue
            try:
                await _dispatch_reminder(pin, h["id"], custom_note="", actor=None, auto=True)
                await db.digital_twin_pins.update_one(
                    {"id": pin["id"], "report_history.id": h["id"]},
                    {"$addToSet": {"report_history.$.auto_reminders_fired_thresholds": due_threshold},
                     "$set": {"report_history.$.last_auto_reminder_at": _now_iso()}},
                )
                sent += 1
            except Exception:  # noqa: BLE001
                failed += 1
    summary = {"checked_reports": seen, "sent": sent, "skipped": skipped, "failed": failed, "at": _now_iso()}
    # Persist last run summary for admin visibility
    await db.scheduler_runs.update_one(
        {"_id": "dt_auto_reminders"},
        {"$set": {"last_run": summary, "updated_at": _now_iso()}},
        upsert=True,
    )
    return summary


@router.get("/pins/{pin_id}/issue-report/preview")
async def preview_issue_report(pin_id: str, screenshot_3d: Optional[str] = Query(None), user: dict = Depends(get_current_user)):
    """Generate the PDF in-line WITHOUT sending email (for review/download)."""
    from dt_issue_report import build_issue_report_pdf

    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    project = await _ensure_project_access(pin["project_id"], user)

    comments = []
    async for c in db.digital_twin_comments.find({"pin_id": pin_id}).sort("created_at", 1):
        comments.append(_clean(c))

    plan_file_path = None
    plan_page = 1
    plan_title = None
    anchors = pin.get("plan_anchors") or []
    if anchors:
        first = anchors[0]
        plan = await db.digital_twin_plans.find_one({"id": first.get("plan_id")})
        if plan:
            plan_title = plan.get("title")
            plan_page = int(first.get("page", 1))
            candidate = UPLOAD_ROOT / pin["project_id"] / "plans" / plan.get("stored_as", "")
            if candidate.exists() and candidate.is_file():
                plan_file_path = str(candidate)

    pdf_buf = build_issue_report_pdf(
        project=project,
        pin=pin,
        comments=comments,
        sender={"name": user.get("name") or user.get("email"), "email": user.get("email"), "role": user.get("role")},
        screenshot_3d_b64=screenshot_3d,
        plan_file_path=plan_file_path,
        plan_page=plan_page,
        plan_title=plan_title,
    )
    return StreamingResponse(
        io.BytesIO(pdf_buf.getvalue()),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report_preview_{pin_id[:8]}.pdf"'},
    )


# ----------------- comments (per pin thread) -----------------

class CommentCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    attachments: Optional[list] = None  # storage URLs added in Phase B


@router.post("/pins/{pin_id}/comments")
async def add_comment(pin_id: str, payload: CommentCreate, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    project = await _ensure_project_access(pin["project_id"], user)
    doc = {
        "id": _new_id(),
        "pin_id": pin_id,
        "project_id": pin["project_id"],
        "author_id": user["id"],
        "author_name": user.get("name") or user.get("email"),
        "author_role": user.get("role"),
        "message": payload.message.strip(),
        "attachments": payload.attachments or [],
        "created_at": _now_iso(),
    }
    await db.digital_twin_comments.insert_one(doc)
    await db.digital_twin_pins.update_one(
        {"id": pin_id},
        {"$inc": {"comment_count": 1}, "$set": {"updated_at": _now_iso()}},
    )

    # Phase G: workflow notification on comment added
    actor_name = doc["author_name"] or "Utilizator"
    project_name = project.get("name", "Proiect")
    # Recipients: pin author (if not actor) + all project stakeholders + all previous commenters on this pin
    recipient_ids = set()
    if pin.get("author_id") and pin["author_id"] != user["id"]:
        recipient_ids.add(pin["author_id"])
    # Previous commenters in the thread
    async for prev in db.digital_twin_comments.find({"pin_id": pin_id, "author_id": {"$ne": user["id"]}}, {"author_id": 1}):
        if prev.get("author_id"):
            recipient_ids.add(prev["author_id"])
    stakeholders = await _project_stakeholders(project, exclude_user_id=user["id"])
    for s in stakeholders:
        recipient_ids.add(s["id"])
    # Email each unique recipient (resolve email for non-stakeholder IDs too)
    emailed = set()
    for s in stakeholders:
        if s["email"] not in emailed:
            emailed.add(s["email"])
            await send_template(
                tpl_dt_comment_added,
                s["name"], project_name, pin["title"], actor_name, user.get("role"), doc["message"],
                to=s["email"],
            )
    # Email pin author + thread commenters even if not stakeholders
    extra_ids = recipient_ids - {s["id"] for s in stakeholders}
    for uid in extra_ids:
        u = await db.users.find_one(_user_filter(uid), {"_id": 1, "email": 1, "name": 1})
        if u and u.get("email") and u["email"] not in emailed:
            emailed.add(u["email"])
            await send_template(
                tpl_dt_comment_added,
                u.get("name") or u["email"], project_name, pin["title"], actor_name, user.get("role"), doc["message"],
                to=u["email"],
            )
    # In-app notification
    for uid in recipient_ids:
        await notify(
            uid,
            "💬 Răspuns pe pin",
            f"{actor_name}: {pin['title']}",
            type_="dt_comment",
            link="/digital-twin",
        )
    return _clean(doc)


@router.get("/pins/{pin_id}/comments")
async def list_comments(pin_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_access(user)
    pin = await db.digital_twin_pins.find_one({"id": pin_id})
    if not pin:
        raise HTTPException(404, "Pin not found.")
    await _ensure_project_access(pin["project_id"], user)
    items = []
    async for c in db.digital_twin_comments.find({"pin_id": pin_id}).sort("created_at", 1):
        items.append(_clean(c))
    return {"items": items, "count": len(items)}


# ----------------- 2D Plans (PDF) — Phase F -----------------

class PlanCreateMeta(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    plan_type: str = Field("floorplan")


@router.post("/projects/{project_id}/plans")
async def upload_plan(
    project_id: str,
    file: UploadFile = File(...),
    title: str = Query(..., min_length=1, max_length=200),
    description: Optional[str] = Query(None, max_length=2000),
    plan_type: str = Query("floorplan"),
    user: dict = Depends(get_current_user),
):
    """Upload a 2D architectural PDF (floor plan, section, elevation, detail)."""
    await _ensure_dt_ingest_access(user)
    p = await _ensure_project_access(project_id, user)
    if user.get("role") not in ("admin", "operator") and p.get("owner_id") != user["id"]:
        # Project members can also upload plans (architects, specialists need to share schedules)
        is_member = any(m.get("user_id") == user["id"] for m in (p.get("members") or []))
        if not is_member:
            raise HTTPException(403, "Doar proprietarul sau membrii proiectului pot încărca planuri.")

    plan_type_clean = plan_type if plan_type in PLAN_TYPES else "other"

    raw_name = file.filename or "plan.pdf"
    ext = Path(raw_name).suffix.lower()
    if ext not in ALLOWED_PLAN_EXTS:
        raise HTTPException(400, "Format permis: .pdf")

    max_plan_bytes = await storage_service.file_limit_bytes("digital_twin_plan")
    dt_remaining = await storage_service.dt_remaining_bytes(p["owner_id"])
    safe_stem = uuid.uuid4().hex[:12]
    safe_name = f"{safe_stem}{ext}"

    # Stream into memory (chunked, with guards) then persist DURABLY to Object Storage.
    buf = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > max_plan_bytes:
            raise HTTPException(413, f"Fișier prea mare (max {max_plan_bytes // (1024*1024)} MB pentru PDF).")
        if len(buf) > dt_remaining:
            raise HTTPException(413, "Cota de stocare Digital Twin este plină. Șterge planuri/modele vechi sau contactează echipa.")
    total = len(buf)
    if total == 0:
        raise HTTPException(400, "Fișierul este gol.")
    try:
        plan_object_path = await storage_service.store_dt_bytes("plan", project_id, safe_name, bytes(buf), "application/pdf")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Upload failed: {e}") from e

    public_path = f"/api/digital-twin/plans/{project_id}/{safe_name}"
    # Extract page count via pypdf (bug fix: enable Phase H page validation)
    page_count = 0
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(bytes(buf)))
        page_count = len(reader.pages)
    except Exception:  # noqa: BLE001
        page_count = 0
    doc = {
        "id": _new_id(),
        "project_id": project_id,
        "filename": raw_name,
        "stored_as": safe_name,
        "size_bytes": total,
        "page_count": page_count,
        "url": public_path,
        "title": title.strip(),
        "description": (description or "").strip(),
        "plan_type": plan_type_clean,
        "uploaded_by": user["id"],
        "uploaded_by_name": user.get("name") or user.get("email"),
        "uploaded_at": _now_iso(),
        "object_path": plan_object_path,
    }
    await db.digital_twin_plans.insert_one(doc)
    await storage_service.add_usage(p["owner_id"], total, "digital_twin")
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"updated_at": _now_iso()}, "$inc": {"plan_count": 1}},
    )
    # Phase G: notify stakeholders a new 2D plan was uploaded
    actor_name = user.get("name") or user.get("email") or "Utilizator"
    project_name = p.get("name", "Proiect")
    stakeholders = await _project_stakeholders(p, exclude_user_id=user["id"])
    for s in stakeholders:
        await notify(
            s["id"],
            f"📐 Plan 2D nou: {doc['title']}",
            f"{actor_name} pe {project_name}",
            type_="dt_plan",
            link="/digital-twin",
        )
        await send_template(
            tpl_dt_plan_uploaded,
            s["name"], project_name, doc["title"], doc["plan_type"], actor_name,
            to=s["email"],
        )
    return _clean(doc)


@router.get("/projects/{project_id}/plans")
async def list_plans(
    project_id: str,
    plan_type: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    await _ensure_dt_ingest_access(user)
    await _ensure_project_access(project_id, user)
    q = {"project_id": project_id}
    if plan_type and plan_type in PLAN_TYPES:
        q["plan_type"] = plan_type
    items = []
    async for pl in db.digital_twin_plans.find(q).sort("uploaded_at", -1):
        items.append(_clean(pl))
    return {"items": items, "count": len(items)}


@router.get("/plans/{project_id}/{filename}")
async def serve_plan_file(project_id: str, filename: str, user: dict = Depends(get_current_user)):
    """Serve uploaded PDF plan. Permission-checked."""
    await _ensure_dt_ingest_access(user)
    await _ensure_project_access(project_id, user)
    if "/" in filename or "\\" in filename or filename.startswith(".."):
        raise HTTPException(400, "Invalid filename.")
    file_path = UPLOAD_ROOT / project_id / "plans" / filename
    if not file_path.exists() or not file_path.is_file():
        file_path = await storage_service.restore_dt_file("plan", project_id, filename)
        if not file_path:
            raise HTTPException(404, "Plan file not found.")
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Cache-Control": "private, max-age=3600"},
    )


class PlanUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    plan_type: Optional[str] = None


@router.patch("/plans/{plan_id}")
async def update_plan(plan_id: str, payload: PlanUpdate, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    plan = await db.digital_twin_plans.find_one({"id": plan_id})
    if not plan:
        raise HTTPException(404, "Plan not found.")
    proj = await _ensure_project_access(plan["project_id"], user)
    if (
        user.get("role") not in ("admin", "operator")
        and plan.get("uploaded_by") != user["id"]
        and proj.get("owner_id") != user["id"]
    ):
        raise HTTPException(403, "Cannot edit this plan.")
    updates = {k: (v.strip() if isinstance(v, str) else v) for k, v in payload.model_dump(exclude_none=True).items()}
    if "plan_type" in updates and updates["plan_type"] not in PLAN_TYPES:
        updates["plan_type"] = "other"
    if not updates:
        return _clean(plan)
    await db.digital_twin_plans.update_one({"id": plan_id}, {"$set": updates})
    plan = await db.digital_twin_plans.find_one({"id": plan_id})
    return _clean(plan)


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, user: dict = Depends(get_current_user)):
    await _ensure_dt_ingest_access(user)
    plan = await db.digital_twin_plans.find_one({"id": plan_id})
    if not plan:
        raise HTTPException(404, "Plan not found.")
    proj = await _ensure_project_access(plan["project_id"], user)
    if (
        user.get("role") not in ("admin", "operator")
        and plan.get("uploaded_by") != user["id"]
        and proj.get("owner_id") != user["id"]
    ):
        raise HTTPException(403, "Cannot delete this plan.")
    # Remove the physical file
    file_path = UPLOAD_ROOT / plan["project_id"] / "plans" / plan["stored_as"]
    file_path.unlink(missing_ok=True)
    await db.digital_twin_plans.delete_one({"id": plan_id})
    await storage_service.add_usage(proj.get("owner_id"), -(plan.get("size_bytes") or 0), "digital_twin")
    await db.digital_twin_projects.update_one(
        {"id": plan["project_id"]},
        {"$inc": {"plan_count": -1}, "$set": {"updated_at": _now_iso()}},
    )
    return {"ok": True}


# ----------------- operator: digital twin onboarding for clients -----------------

operator_router = APIRouter(prefix="/api/operator/digital-twin", tags=["digital-twin-operator"])


class SubGrant(BaseModel):
    user_id: str
    active: bool = True


@operator_router.post("/grant-access")
async def operator_grant_access(payload: SubGrant, user: dict = Depends(require_role("operator", "admin"))):
    """Operator (or admin) grants/revokes Digital Twin Pro access to a client.
    Audit-logged. Required so the operator can prepare projects for paying clients."""
    target = await db.users.find_one(_user_filter(payload.user_id))
    if not target:
        raise HTTPException(404, "Client inexistent.")
    if target.get("role") != "client":
        raise HTTPException(400, "Acces Digital Twin Pro se acordă doar clienților.")
    await db.users.update_one(
        _user_filter(payload.user_id),
        {"$set": {"digital_twin_pro": payload.active, "digital_twin_pro_updated_at": _now_iso()}},
    )
    await db.audit_log.insert_one({
        "actor": user["id"],
        "actor_role": user.get("role"),
        "action": "digital_twin.subscription." + ("grant" if payload.active else "revoke"),
        "target_user": payload.user_id,
        "via": "operator_panel" if user.get("role") == "operator" else "admin_panel",
        "created_at": _now_iso(),
    })
    if payload.active:
        await notify(
            payload.user_id,
            "🧊 Digital Twin Pro activat",
            f"{user.get('name') or 'Echipa PropManage'} ti-a activat accesul la modulul Digital Twin Pro. Mergi la 'Digital Twin' pentru a-ti vedea proiectul.",
            type_="dt_subscription",
            link="/digital-twin",
        )
    return {"ok": True, "user_id": payload.user_id, "active": payload.active}


@operator_router.get("/search-clients")
async def operator_search_clients(
    q: str = Query(..., min_length=2, max_length=120),
    user: dict = Depends(require_role("operator", "admin")),  # noqa: ARG001
):
    """Operator/admin search for CLIENTS (role=client) by name or email — for granting
    Digital Twin Pro access. Case-insensitive, substring match on name AND email.
    Returns `digital_twin_pro` so the UI can flag clients that already have access
    (prevents a second grant / duplicate relation). Restricted to role=client:
    operators never see specialists/admins/operators here."""
    pattern = {"$regex": re.escape(q.strip()), "$options": "i"}
    cursor = db.users.find(
        {"role": "client", "$or": [{"name": pattern}, {"email": pattern}]}
    ).limit(10)
    items = []
    async for u in cursor:
        items.append({
            "id": str(u["_id"]),
            "name": u.get("name"),
            "email": u.get("email"),
            "digital_twin_pro": bool(u.get("digital_twin_pro")),
        })
    return {"items": items, "count": len(items)}


@operator_router.get("/clients-queue")
async def operator_clients_queue(
    status: str = Query("all", pattern="^(all|needs_setup|in_progress|delivered)$"),
    user: dict = Depends(require_role("operator", "admin")),  # noqa: ARG001
):
    """Lists clients eligible for / using Digital Twin Pro. Three statuses:
       - needs_setup: digital_twin_pro=true AND project_count==0 (no project created yet)
       - in_progress: digital_twin_pro=true AND has projects but model_count==0
       - delivered: digital_twin_pro=true AND has projects with model uploaded
       - all: union of the above
    """
    cursor = db.users.find({"role": "client", "digital_twin_pro": True})
    items = []
    async for u in cursor:
        cid = str(u["_id"])
        project_count = await db.digital_twin_projects.count_documents({"owner_id": cid})
        model_count = 0
        plan_count = 0
        projects = []
        if project_count:
            async for p in db.digital_twin_projects.find({"owner_id": cid}).sort("updated_at", -1):
                model_count += p.get("model_count", 0)
                plan_count += p.get("plan_count", 0)
                projects.append({
                    "id": p["id"],
                    "name": p.get("name"),
                    "model_count": p.get("model_count", 0),
                    "plan_count": p.get("plan_count", 0),
                    "pin_count": p.get("pin_count", 0),
                    "updated_at": p.get("updated_at"),
                })
        if project_count == 0:
            client_status = "needs_setup"
        elif model_count == 0:
            client_status = "in_progress"
        else:
            client_status = "delivered"
        if status != "all" and status != client_status:
            continue
        items.append({
            "client_id": cid,
            "client_name": u.get("name") or u.get("email"),
            "client_email": u.get("email"),
            "client_phone": u.get("phone"),
            "zone": u.get("zone"),
            "granted_at": u.get("digital_twin_pro_updated_at"),
            "project_count": project_count,
            "model_count": model_count,
            "plan_count": plan_count,
            "projects": projects,
            "status": client_status,
        })
    items.sort(key=lambda x: (x["status"] != "needs_setup", x["status"] != "in_progress", -(len(x["projects"]) or 0)))
    counters = {
        "needs_setup": sum(1 for x in items if x["status"] == "needs_setup"),
        "in_progress": sum(1 for x in items if x["status"] == "in_progress"),
        "delivered": sum(1 for x in items if x["status"] == "delivered"),
        "total": len(items),
    }
    return {"items": items, "counters": counters}


class OperatorProjectCreate(BaseModel):
    client_id: str
    name: str = Field(..., min_length=2, max_length=200)
    property_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=2000)
    trimble_embed_url: Optional[str] = Field(None, max_length=2000)


class OperatorTrimbleEmbedUpdate(BaseModel):
    trimble_embed_url: Optional[str] = Field(None, max_length=2000)


@operator_router.patch("/projects/{project_id}/trimble")
async def operator_set_trimble_embed(
    project_id: str,
    payload: OperatorTrimbleEmbedUpdate,
    user: dict = Depends(require_role("operator", "admin")),
):
    """Set / clear the Trimble Connect 3D Viewer iframe URL for a project.

    Pass an empty string or null to remove. The URL must be a Trimble Connect
    share / embed link (e.g. https://web.connect.trimble.com/projects/.../viewer/...).
    """
    project = await db.digital_twin_projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(404, "Project not found.")
    raw_url = (payload.trimble_embed_url or "").strip()
    if raw_url:
        if not (raw_url.startswith("https://") and ("trimble.com" in raw_url or "sketchup.com" in raw_url)):
            raise HTTPException(400, "URL invalid — folosește un link Trimble Connect / SketchUp (https://*.trimble.com/...).")
        new_value = raw_url
    else:
        new_value = None
    await db.digital_twin_projects.update_one(
        {"id": project_id},
        {"$set": {"trimble_embed_url": new_value, "updated_at": _now_iso()}},
    )
    return {"ok": True, "trimble_embed_url": new_value}


@operator_router.get("/clients/{client_id}/properties")
async def operator_list_client_properties(
    client_id: str,
    user: dict = Depends(require_role("operator", "admin")),  # noqa: ARG001
):
    """P0.1 — proprietățile clientului pentru selectorul de ancorare (Property Anchor) la
    crearea unui Digital Twin din zona Operator. Read-only, reutilizează db.properties (SSOT),
    NU creează un nou sistem de identitate/linking."""
    client = await db.users.find_one(_user_filter(client_id))
    if not client:
        raise HTTPException(404, "Client inexistent.")
    items = []
    async for p in db.properties.find({"owner_id": client_id}).sort("created_at", -1):
        items.append({
            "id": str(p["_id"]),
            "name": p.get("name") or "Proprietate",
            "address": p.get("address"),
            "type": p.get("type"),
        })
    return {"items": items}


@operator_router.post("/clients/{client_id}/projects")
async def operator_create_project_for_client(
    client_id: str,
    payload: OperatorProjectCreate,
    user: dict = Depends(require_role("operator", "admin")),
):
    """Creates a Digital Twin project owned by the client (not the operator).
    The operator is recorded as `created_by_operator_id` for audit / project routing.

    P0.1 — Operator Property Anchor: `property_id` este OBLIGATORIU pe fluxul operator (spre
    deosebire de fluxul client, unde standalone rămâne permis). Elimină sursa de orfanare a
    modelelor create de operator. Ancorarea reutilizează integral infrastructura P0
    (`_resolve_property_anchor` anti-misassignment + KG + moștenire pe modele)."""
    if payload.client_id != client_id:
        raise HTTPException(400, "client_id mismatch.")
    client = await db.users.find_one(_user_filter(client_id))
    if not client:
        raise HTTPException(404, "Client inexistent.")
    if (client.get("role") or "").lower() != "client":
        raise HTTPException(400, "Doar clientii pot avea proiecte Digital Twin.")
    if not client.get("digital_twin_pro"):
        raise HTTPException(400, "Clientul nu are acces Digital Twin Pro. Acordă mai întâi accesul.")
    if not payload.property_id:
        raise HTTPException(400, "Selectează proprietatea clientului pentru a ancora Digital Twin-ul (Property Anchor).")
    prop_anchor, link_status = await _resolve_property_anchor(payload.property_id, user, owner_id=client_id)
    pid = _new_id()
    now = _now_iso()
    doc = {
        "id": pid,
        "name": payload.name.strip(),
        "description": (payload.description or "").strip(),
        "model_url": None,
        "trimble_embed_url": (payload.trimble_embed_url or "").strip() or None,
        "owner_id": client_id,
        "owner_name": client.get("name") or client.get("email"),
        "property_id": prop_anchor,
        "property_link_status": link_status,
        "members": [],
        "model_count": 0,
        "plan_count": 0,
        "pin_count": 0,
        "created_at": now,
        "updated_at": now,
        "created_by_operator_id": user["id"],
        "created_by_operator_name": user.get("name") or user.get("email"),
    }
    await db.digital_twin_projects.insert_one(doc)
    await _kg_link_twin(prop_anchor, "twin_project", pid)
    await db.audit_log.insert_one({
        "actor": user["id"],
        "actor_role": user.get("role"),
        "action": "digital_twin.project.create_for_client",
        "target_user": client_id,
        "project_id": pid,
        "created_at": now,
    })
    await notify(
        client_id,
        "🏗️ Proiect Digital Twin creat",
        f"{user.get('name') or 'Echipa PropManage'} a creat proiectul '{payload.name}' pentru tine. Va incarca in curand modelul 3D si planurile.",
        type_="dt_project",
        link="/digital-twin",
    )
    return _clean(doc)


# ----------------- admin: subscription grant -----------------

admin_router = APIRouter(prefix="/api/admin/digital-twin", tags=["digital-twin-admin"])


@admin_router.post("/backfill-property-links")
async def backfill_property_links(user: dict = Depends(require_role("admin"))):  # noqa: ARG001
    """P0 — backfill SAFE, determinist, auditabil. ZERO auto-assignment: proiectele fără
    property_id NU sunt atribuite arbitrar, ci marcate `unresolved` (regula Fondator).
    Idempotent. Scrie muchiile KG pentru cele deja legate."""
    projects_total = already_linked = marked_unresolved = 0
    async for p in db.digital_twin_projects.find({}):
        projects_total += 1
        if p.get("property_id"):
            already_linked += 1
            if p.get("property_link_status") != "linked":
                await db.digital_twin_projects.update_one({"id": p["id"]}, {"$set": {"property_link_status": "linked"}})
            await _kg_link_twin(p.get("property_id"), "twin_project", p["id"])
        elif p.get("property_link_status") != "unresolved":
            await db.digital_twin_projects.update_one({"id": p["id"]}, {"$set": {"property_link_status": "unresolved"}})
            marked_unresolved += 1
        else:
            marked_unresolved += 1
    models_total = models_linked = 0
    async for m in db.digital_twin_models.find({}):
        models_total += 1
        st = "linked" if m.get("property_id") else "unresolved"
        if m.get("property_link_status") != st:
            await db.digital_twin_models.update_one({"id": m["id"]}, {"$set": {"property_link_status": st}})
        if m.get("property_id"):
            models_linked += 1
            await _kg_link_twin(m.get("property_id"), "twin_model", m["id"])
    return {
        "projects_total": projects_total,
        "projects_already_linked": already_linked,
        "projects_marked_unresolved": marked_unresolved,
        "projects_auto_assigned": 0,
        "models_total": models_total,
        "models_linked": models_linked,
        "models_unresolved": models_total - models_linked,
        "note": "Zero auto-assignment. Proiectele fără property_id rămân 'unresolved' și se ancorează manual via PATCH /projects/{id}/property.",
    }


@admin_router.get("/unresolved-projects")
async def list_unresolved_projects(user: dict = Depends(require_role("admin", "operator"))):  # noqa: ARG001
    """P0.1+ — proiecte 3D neancorate (istorice) + candidați de proprietate (ale ownerului),
    pentru ancorare MANUALĂ via PATCH /projects/{id}/property. ZERO auto-assign / ZERO inferență riscantă."""
    items = []
    q = {"$or": [
        {"property_id": None}, {"property_id": {"$exists": False}}, {"property_id": ""},
        {"property_link_status": "unresolved"},
    ]}
    async for p in db.digital_twin_projects.find(q).sort("created_at", -1).limit(300):
        if p.get("property_id"):
            continue  # already anchored — never touch
        owner_id = p.get("owner_id")
        owner = await db.users.find_one(_user_filter(owner_id), {"name": 1, "email": 1}) if owner_id else None
        cand = []
        if owner_id:
            async for pr in db.properties.find({"owner_id": owner_id}).sort("created_at", -1):
                cand.append({
                    "id": str(pr["_id"]),
                    "name": pr.get("name") or "Proprietate",
                    "address": pr.get("address"),
                    "type": pr.get("type"),
                    "surface": pr.get("surface"),
                    "rooms": pr.get("rooms"),
                    "health_score": pr.get("health_score"),
                })
        items.append({
            "id": p["id"], "name": p.get("name"), "created_at": p.get("created_at"),
            "owner_id": owner_id, "owner_name": (owner or {}).get("name") or (owner or {}).get("email") or "—",
            "model_count": p.get("model_count", 0), "plan_count": p.get("plan_count", 0),
            "property_link_status": p.get("property_link_status") or "unresolved",
            "candidate_properties": cand,
        })
    return {"items": items, "count": len(items)}


class BulkAnchorIn(BaseModel):
    project_ids: List[str] = Field(..., min_length=1, max_length=100)
    property_id: str = Field(..., min_length=3)


@admin_router.get("/properties/{property_id}/preview")
async def property_anchor_preview(property_id: str, user: dict = Depends(require_role("admin", "operator"))):  # noqa: ARG001
    """Preview al proprietății țintă înainte de ancorarea în masă (nume, adresă, tip, suprafață, sănătate)."""
    try:
        pr = await db.properties.find_one({"_id": ObjectId(property_id)})
    except Exception:
        pr = None
    if not pr:
        raise HTTPException(404, "Proprietatea nu există.")
    owner = await db.users.find_one(_user_filter(str(pr.get("owner_id"))), {"name": 1, "email": 1}) if pr.get("owner_id") else None
    twin = await db.twins.find_one({"property_id": property_id}, {"rooms": 1})
    return {
        "id": property_id,
        "name": pr.get("name") or "Proprietate",
        "address": pr.get("address"),
        "type": pr.get("type"),
        "surface": pr.get("surface"),
        "rooms": pr.get("rooms"),
        "health_score": pr.get("health_score"),
        "owner_id": str(pr.get("owner_id")) if pr.get("owner_id") else None,
        "owner_name": (owner or {}).get("name") or (owner or {}).get("email") or "—",
        "twin_rooms_count": len((twin or {}).get("rooms") or []),
    }


@admin_router.post("/bulk-anchor")
async def bulk_anchor_projects(payload: BulkAnchorIn, user: dict = Depends(require_role("admin", "operator"))):
    """P0.1++ — ancorează MAI MULTE proiecte neancorate la ACEEAȘI proprietate, într-o singură confirmare.

    ZERO auto-assign: fiecare proiect trebuie confirmat explicit de operator (lista vine din UI).
    Verificare ownership per proiect (proprietatea trebuie să aparțină ownerului proiectului).
    Non-destructiv: nu se șterge nimic; proiectele deja ancorate sunt sărite (skipped)."""
    try:
        prop = await db.properties.find_one({"_id": ObjectId(payload.property_id)})
    except Exception:
        prop = None
    if not prop:
        raise HTTPException(404, "Proprietatea țintă nu există.")
    prop_owner = str(prop.get("owner_id")) if prop.get("owner_id") else None
    results = []
    anchored = 0
    for pid in payload.project_ids:
        p = await db.digital_twin_projects.find_one({"id": pid})
        if not p:
            results.append({"project_id": pid, "ok": False, "error": "Proiect inexistent."})
            continue
        if p.get("property_id"):
            results.append({"project_id": pid, "ok": False, "skipped": True, "error": "Deja ancorat."})
            continue
        if prop_owner is not None and str(p.get("owner_id")) != prop_owner:
            results.append({"project_id": pid, "ok": False, "error": "Proprietatea nu aparține ownerului proiectului."})
            continue
        await db.digital_twin_projects.update_one(
            {"id": pid},
            {"$set": {"property_id": payload.property_id, "property_link_status": "linked", "updated_at": _now_iso()}},
        )
        await db.digital_twin_models.update_many(
            {"project_id": pid},
            {"$set": {"property_id": payload.property_id, "property_link_status": "linked"}},
        )
        await _kg_link_twin(payload.property_id, "twin_project", pid)
        async for m in db.digital_twin_models.find({"project_id": pid}, {"id": 1}):
            await _kg_link_twin(payload.property_id, "twin_model", m["id"])
        anchored += 1
        results.append({"project_id": pid, "ok": True, "property_id": payload.property_id})
    return {
        "ok": True,
        "anchored_count": anchored,
        "requested": len(payload.project_ids),
        "property_id": payload.property_id,
        "property_name": prop.get("name"),
        "results": results,
    }
async def grant_subscription(payload: SubGrant, user: dict = Depends(require_role("admin"))):
    """Admin can manually grant/revoke Digital Twin Pro access until Stripe wiring."""
    r = await db.users.update_one(
        _user_filter(payload.user_id),
        {"$set": {"digital_twin_pro": payload.active, "digital_twin_pro_updated_at": _now_iso()}},
    )
    if not r.matched_count:
        raise HTTPException(404, "User not found.")
    await db.audit_log.insert_one({
        "actor": user["id"],
        "action": "digital_twin.subscription." + ("grant" if payload.active else "revoke"),
        "target_user": payload.user_id,
        "created_at": _now_iso(),
    })
    return {"ok": True, "user_id": payload.user_id, "active": payload.active}


@admin_router.get("/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):  # noqa: ARG001
    return {
        "projects": await db.digital_twin_projects.count_documents({}),
        "models": await db.digital_twin_models.count_documents({}),
        "plans": await db.digital_twin_plans.count_documents({}),
        "pins": await db.digital_twin_pins.count_documents({}),
        "comments": await db.digital_twin_comments.count_documents({}),
        "pro_users": await db.users.count_documents({"digital_twin_pro": True}),
    }



@admin_router.post("/auto-reminders/run-now")
async def admin_run_auto_reminders_now(user: dict = Depends(require_role("admin"))):  # noqa: ARG001
    """Manually trigger the auto-reminder scheduler (idempotent — won't double-fire same threshold)."""
    return await run_dt_auto_reminders()


@admin_router.get("/auto-reminders/last-run")
async def admin_auto_reminders_last_run(user: dict = Depends(require_role("admin"))):  # noqa: ARG001
    doc = await db.scheduler_runs.find_one({"_id": "dt_auto_reminders"})
    return doc.get("last_run") if doc else {"never_ran": True}
