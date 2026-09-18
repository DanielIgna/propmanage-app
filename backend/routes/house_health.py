"""House Health (Sănătatea Casei) — F1 + F2 + F3.

Premium subscription-based health audit module for Digital Twin owners.

Phase 1 endpoints:
    GET  /api/house-health/eligibility
    GET  /api/house-health/dashboard
    GET  /api/house-health/feature-flag

Phase 2 — Documents + History:
    POST   /api/house-health/documents             — upload local OR link extern
    GET    /api/house-health/documents             — list with filters
    DELETE /api/house-health/documents/{id}        — owner only
    GET    /api/house-health/history/{twin_id}     — chronological timeline

Phase 3 — Specialist evaluations + admin approval:
    POST  /api/house-health/evaluations            — create (specialist)
    POST  /api/house-health/evaluations/{id}/upload — attach files (specialist)
    POST  /api/house-health/evaluations/{id}/submit — submit for approval
    GET   /api/house-health/evaluations            — list for current user
    POST  /api/admin/house-health/evaluations/{id}/approve — admin approve
    POST  /api/admin/house-health/evaluations/{id}/reject  — admin reject

Collections:
    hh_subscriptions, hh_evaluations, hh_measurements, hh_documents,
    hh_recommendations, hh_scores, hh_plans, hh_scoring_config, hh_audit_log

Feature flag: ``app_settings.house_health.enabled`` (default False).
"""
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user, require_role
from entitlements import F_HOUSE_HEALTH_BASIC, get_user_entitlements
import storage_service
from storage_client import get_object as st_get_object, put_object as st_put_object

logger = logging.getLogger("propmanage.house_health")

router = APIRouter(prefix="/api/house-health", tags=["house-health"])
admin_router = APIRouter(prefix="/api/admin/house-health", tags=["house-health-admin"])

UPLOAD_DIR = storage_service.HH_DIR

ALLOWED_DOC_CATEGORIES = [
    "certificat_energetic", "carte_tehnica", "cadastru", "extras_cf",
    "facturi_renovari", "garantii", "manuale", "procese_verbale", "hh_report",
    "other",
]
ALLOWED_EXTERNAL_TYPES = ["google_drive", "dropbox", "onedrive", "custom"]
ALLOWED_EVAL_KINDS = ["air", "thermal", "humidity", "electric", "radon"]
EVAL_EQUIPMENT = {
    "air": ["Testo 405i", "Testo 605i", "CO2 detector (future)"],
    "thermal": ["Testo 860i"],
    "humidity": ["Bosch D-Tect 200C"],
    "electric": ["Testo 745", "UNI-T UT682D"],
    "radon": ["Radon detector (future)"],
}


async def _is_feature_enabled() -> bool:
    """Read the global feature flag from app_settings.house_health.enabled."""
    s = await db.app_settings.find_one({"_id": "house_health"})
    return bool((s or {}).get("enabled", False))


async def _user_has_active_twin(user_id: str) -> Optional[dict]:
    """Return the first DT project owned by user, or None."""
    p = await db.digital_twin_projects.find_one(
        {"owner_id": user_id},
        {"_id": 0, "id": 1, "name": 1, "property_id": 1, "created_at": 1},
    )
    return p


async def _user_active_subscription(user_id: str) -> Optional[dict]:
    """Return active hh_subscriptions doc for user (status=active OR trial)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    sub = await db.hh_subscriptions.find_one({
        "user_id": user_id,
        "status": {"$in": ["active", "trial", "grace"]},
        "$or": [
            {"expires_at": {"$gt": now_iso}},
            {"expires_at": None},
            {"expires_at": {"$exists": False}},
        ],
    }, {"_id": 0})
    return sub


async def _assert_house_health_entitlement(user: dict) -> dict:
    """Central gate: aruncă 402 dacă user-ul nu are house_health_basic.
    Specialiștii care produc evaluări sunt exceptați (role check separat)."""
    role = user.get("active_view") or user.get("role")
    if role == "specialist":
        return user
    ent = await get_user_entitlements(user)
    if F_HOUSE_HEALTH_BASIC in set(ent["features"]):
        return user
    raise HTTPException(
        status_code=402,
        detail={
            "error": "entitlement_required",
            "feature": F_HOUSE_HEALTH_BASIC,
            "current_tier": ent["tier"],
            "current_tier_label": ent["tier_label"],
            "message": "House Health Basic este inclus în abonamentul PropManage. Activează abonamentul pentru a accesa această funcție.",
        },
    )


@router.get("/feature-flag")
async def feature_flag(user=Depends(get_current_user)):
    """Lightweight check used by ClientDashboard to decide if card renders."""
    enabled = await _is_feature_enabled()
    return {"enabled": enabled}


@router.get("/eligibility")
async def eligibility(user=Depends(get_current_user)):
    """Check if the current user can access House Health.

    Returns:
        {
          enabled: bool (feature flag),
          has_twin: bool,
          has_subscription: bool,
          twin: {id, name, property_id} or None,
          subscription: {plan, status, expires_at} or None,
          gate_message: str
        }
    """
    enabled = await _is_feature_enabled()
    if not enabled:
        return {
            "enabled": False,
            "has_twin": False,
            "has_subscription": False,
            "twin": None,
            "subscription": None,
            "gate_message": "Modulul House Health nu este activat pe această platformă.",
        }

    twin = await _user_has_active_twin(user["id"])
    sub = await _user_active_subscription(user["id"])

    if not twin:
        gate = "Serviciul House Health este disponibil doar proprietăților cu Digital Twin activ."
    elif not sub:
        gate = "Activează un abonament House Health pentru a accesa secțiunile."
    else:
        gate = ""

    return {
        "enabled": True,
        "has_twin": bool(twin),
        "has_subscription": bool(sub),
        "twin": twin,
        "subscription": (
            {
                "plan": sub.get("plan"),
                "status": sub.get("status"),
                "expires_at": sub.get("expires_at"),
            }
            if sub
            else None
        ),
        "gate_message": gate,
    }


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    """Payload for the HouseHealth card on ClientDashboard.

    Returns nullable fields so the UI can render a graceful skeleton when
    data is not yet populated (typical for F1 — fresh module).
    """
    enabled = await _is_feature_enabled()
    if not enabled:
        return {"enabled": False}

    twin = await _user_has_active_twin(user["id"])
    sub = await _user_active_subscription(user["id"])

    if not twin:
        return {
            "enabled": True,
            "locked": True,
            "lock_reason": "no_twin",
            "lock_message": "Serviciul House Health este disponibil doar proprietăților cu Digital Twin activ.",
        }

    # Central entitlement gate — FREE users see locked upgrade state
    role = user.get("active_view") or user.get("role")
    if role not in ("admin", "operator", "franchise_admin", "specialist"):
        ent = await get_user_entitlements(user)
        if F_HOUSE_HEALTH_BASIC not in set(ent["features"]):
            return {
                "enabled": True,
                "locked": True,
                "lock_reason": "no_subscription",
                "lock_message": "House Health Basic este inclus în abonamentul PropManage. Activează abonamentul pentru a accesa această funcție.",
                "required_tier": "CLIENT_BASIC",
                "current_tier": ent["tier"],
                "cta_label": "Activează PropManage Basic",
            }

    twin_id = twin.get("id")

    # Score (latest)
    score_doc = await db.hh_scores.find_one({"twin_project_id": twin_id}, sort=[("computed_at", -1)])
    score_overall = (score_doc or {}).get("overall")
    classification = (score_doc or {}).get("classification")

    # Last + next evaluation
    last_eval = await db.hh_evaluations.find_one(
        {"twin_project_id": twin_id, "status": "approved"},
        sort=[("date", -1)],
    )
    last_eval_date = (last_eval or {}).get("date")
    next_eval_date = None
    if last_eval_date:
        try:
            d = datetime.fromisoformat(last_eval_date.replace("Z", "+00:00"))
            next_eval_date = d.replace(year=d.year + 1).isoformat()
        except Exception:  # noqa: BLE001
            next_eval_date = None

    # Document count
    docs_count = await db.hh_documents.count_documents({"twin_project_id": twin_id})

    # Last report (most recent doc with category=hh_report or last approved eval)
    last_report = await db.hh_documents.find_one(
        {"twin_project_id": twin_id, "category": "hh_report"},
        sort=[("doc_date", -1)],
    )

    return {
        "enabled": True,
        "locked": not sub,
        "lock_reason": None if sub else "no_subscription",
        "lock_message": "" if sub else "Activează un abonament House Health pentru a accesa secțiunile.",
        "twin": twin,
        "subscription": sub,
        "score_overall": score_overall,
        "classification": classification,
        "last_evaluation_date": last_eval_date,
        "next_evaluation_date": next_eval_date,
        "documents_count": docs_count,
        "last_report_id": (last_report or {}).get("id"),
    }


# ============================================================================
# Phase 2 — Documents
# ============================================================================
async def _assert_twin_owner(twin_id: str, user_id: str):
    """Raise 403 if user doesn't own the digital twin project."""
    p = await db.digital_twin_projects.find_one(
        {"id": twin_id, "owner_id": user_id}, {"_id": 0, "id": 1}
    )
    if not p:
        raise HTTPException(403, "Nu ai acces la acest Digital Twin.")


@router.post("/documents")
async def upload_document(
    twin_project_id: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    doc_date: str = Form(""),
    expires_at: str = Form(""),
    external_link: str = Form(""),
    external_type: str = Form(""),
    file: Optional[UploadFile] = File(None),
    user=Depends(get_current_user),
):
    """Upload a document — either as local file OR external link.

    For local: multipart with ``file`` field.
    For external: ``external_link`` + ``external_type`` (google_drive/dropbox/onedrive/custom).
    Exactly one source must be provided.
    """
    if not await _is_feature_enabled():
        raise HTTPException(403, "House Health nu este activ.")
    await _assert_house_health_entitlement(user)
    if category not in ALLOWED_DOC_CATEGORIES:
        raise HTTPException(400, f"Categorie invalidă. Permise: {ALLOWED_DOC_CATEGORIES}")
    await _assert_twin_owner(twin_project_id, user["id"])

    has_file = file is not None and getattr(file, "filename", "")
    has_link = bool(external_link.strip())
    if has_file and has_link:
        raise HTTPException(400, "Trimite ori fișier, ori link — nu ambele.")
    if not has_file and not has_link:
        raise HTTPException(400, "Trebuie să încarci un fișier sau să dai un link extern.")

    doc_id = uuid.uuid4().hex
    record = {
        "id": doc_id,
        "user_id": user["id"],
        "twin_project_id": twin_project_id,
        "category": category,
        "description": description.strip()[:500],
        "doc_date": doc_date or None,
        "expires_at": expires_at or None,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by_email": user.get("email"),
    }

    if has_file:
        contents = await file.read()
        limit = await storage_service.file_limit_bytes("house_health_doc")
        if len(contents) > limit:
            raise HTTPException(413, f"Fișierul depășește {storage_service.fmt_bytes(limit)}.")
        ext = Path(file.filename or "").suffix.lower().lstrip(".")
        if (file.content_type or "").startswith("image/"):
            contents, _cm = await storage_service.maybe_compress_image(contents, ext)
        await storage_service.check_quota(user["id"], len(contents), "personal")
        safe_name = f"{doc_id}_{Path(file.filename).name[:80]}"
        object_path = f"propmanage/house_health/{doc_id}/{safe_name}"
        await asyncio.to_thread(st_put_object, object_path, contents, file.content_type or "application/octet-stream")
        record["storage"] = "object"
        record["object_path"] = object_path
        record["filename"] = file.filename
        record["file_url"] = f"/api/house-health/documents/{doc_id}/download"
        record["size_bytes"] = len(contents)
        record["mime"] = file.content_type
    else:
        if external_type not in ALLOWED_EXTERNAL_TYPES:
            raise HTTPException(400, f"Tip link invalid. Permise: {ALLOWED_EXTERNAL_TYPES}")
        record["storage"] = "external"
        record["external_type"] = external_type
        record["external_link"] = external_link.strip()[:1000]

    await db.hh_documents.insert_one(record)
    record.pop("_id", None)
    return {"ok": True, "document": record}


@router.get("/documents")
async def list_documents(
    twin_project_id: str,
    category: Optional[str] = None,
    user=Depends(get_current_user),
):
    """List documents for a twin (must be owner)."""
    if not await _is_feature_enabled():
        raise HTTPException(403, "House Health nu este activ.")
    await _assert_twin_owner(twin_project_id, user["id"])
    q = {"twin_project_id": twin_project_id}
    if category:
        q["category"] = category
    items = []
    async for d in db.hh_documents.find(q, {"_id": 0}).sort("uploaded_at", -1):
        items.append(d)
    return {"items": items, "count": len(items)}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user=Depends(get_current_user)):
    d = await db.hh_documents.find_one({"id": doc_id, "user_id": user["id"]}, {"_id": 0})
    if not d:
        raise HTTPException(404, "Document inexistent sau nu îți aparține.")
    if d.get("storage") == "local":
        for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
            try:
                f.unlink()
            except OSError:
                pass
    await db.hh_documents.delete_one({"id": doc_id})
    if d.get("size_bytes"):
        await storage_service.add_usage(user["id"], -d["size_bytes"], "personal")
    return {"ok": True, "deleted_id": doc_id}


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str, user=Depends(get_current_user)):
    from fastapi.responses import FileResponse, Response
    d = await db.hh_documents.find_one({"id": doc_id, "user_id": user["id"]}, {"_id": 0})
    if not d or d.get("storage") not in ("local", "object"):
        raise HTTPException(404, "Document inexistent.")
    if d.get("storage") == "object" and d.get("object_path"):
        data, ct = await asyncio.to_thread(st_get_object, d["object_path"])
        return Response(content=data, media_type=d.get("mime") or ct,
                        headers={"Content-Disposition": f'attachment; filename="{d.get("filename") or "document"}"'})
    for f in UPLOAD_DIR.glob(f"{doc_id}_*"):
        return FileResponse(path=str(f), filename=d.get("filename", "document"), media_type=d.get("mime") or "application/octet-stream")
    raise HTTPException(404, "Fișier dispărut de pe disc.")


# ============================================================================
# Phase 2 — History timeline
# ============================================================================
@router.get("/history/{twin_id}")
async def history_timeline(twin_id: str, user=Depends(get_current_user)):
    if not await _is_feature_enabled():
        raise HTTPException(403, "House Health nu este activ.")
    await _assert_twin_owner(twin_id, user["id"])

    events = []
    async for e in db.hh_evaluations.find(
        {"twin_project_id": twin_id, "status": "approved"}, {"_id": 0}
    ).sort("date", -1):
        events.append({
            "kind": "evaluation",
            "evaluation_kind": e.get("kind"),
            "title": f"Evaluare {e.get('kind', '')}",
            "date": e.get("date"),
            "specialist_id": e.get("specialist_id"),
            "id": e.get("id"),
        })
    async for d in db.hh_documents.find(
        {"twin_project_id": twin_id, "category": "hh_report"}, {"_id": 0}
    ).sort("doc_date", -1):
        events.append({
            "kind": "report",
            "title": d.get("description") or "Raport House Health",
            "date": d.get("doc_date") or d.get("uploaded_at"),
            "id": d.get("id"),
        })
    events.sort(key=lambda x: x.get("date") or "", reverse=True)
    return {"items": events, "count": len(events)}


# ============================================================================
# Phase 3 — Specialist Evaluations
# ============================================================================
class EvaluationCreate(BaseModel):
    twin_project_id: str
    kind: str = Field(..., description="air|thermal|humidity|electric|radon")
    date: Optional[str] = None
    equipment: Optional[List[str]] = None
    observations: Optional[str] = None
    measurements: Optional[dict] = None
    zones: Optional[List[str]] = None
    severity: Optional[str] = None  # for humidity
    radon_avg: Optional[float] = None
    radon_period: Optional[str] = None


@router.post("/evaluations")
async def create_evaluation(payload: EvaluationCreate, user=Depends(get_current_user)):
    if not await _is_feature_enabled():
        raise HTTPException(403, "House Health nu este activ.")
    if user.get("role") not in ("specialist", "admin"):
        raise HTTPException(403, "Doar specialiști/admini pot crea evaluări.")
    if payload.kind not in ALLOWED_EVAL_KINDS:
        raise HTTPException(400, f"Kind invalid. Permise: {ALLOWED_EVAL_KINDS}")

    eval_id = uuid.uuid4().hex
    doc = {
        "id": eval_id,
        "twin_project_id": payload.twin_project_id,
        "kind": payload.kind,
        "date": payload.date or datetime.now(timezone.utc).isoformat(),
        "specialist_id": user["id"],
        "specialist_email": user.get("email"),
        "status": "draft",
        "equipment": payload.equipment or [],
        "observations": payload.observations or "",
        "measurements": payload.measurements or {},
        "zones": payload.zones or [],
        "severity": payload.severity,
        "radon_avg": payload.radon_avg,
        "radon_period": payload.radon_period,
        "attachments": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.hh_evaluations.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "evaluation": doc}


@router.post("/evaluations/{eval_id}/upload")
async def upload_evaluation_file(
    eval_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    e = await db.hh_evaluations.find_one({"id": eval_id})
    if not e:
        raise HTTPException(404, "Evaluare inexistentă.")
    if e.get("specialist_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Doar specialistul evaluării poate încărca.")

    contents = await file.read()
    limit = await storage_service.file_limit_bytes("house_health_eval")
    if len(contents) > limit:
        raise HTTPException(413, f"Fișier > {storage_service.fmt_bytes(limit)}.")
    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if (file.content_type or "").startswith("image/"):
        contents, _cm = await storage_service.maybe_compress_image(contents, ext)
    await storage_service.check_quota(user["id"], len(contents), "personal")
    att_id = uuid.uuid4().hex
    safe_name = f"eval_{eval_id}_{att_id}_{Path(file.filename).name[:80]}"
    object_path = f"propmanage/house_health/eval/{eval_id}/{safe_name}"
    await asyncio.to_thread(st_put_object, object_path, contents, file.content_type or "application/octet-stream")
    attachment = {
        "id": att_id,
        "filename": file.filename,
        "url": f"/api/house-health/evaluations/{eval_id}/files/{att_id}",
        "object_path": object_path,
        "uploaded_by": user["id"],
        "mime": file.content_type,
        "size_bytes": len(contents),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.hh_evaluations.update_one({"id": eval_id}, {"$push": {"attachments": attachment}})
    await storage_service.add_usage(user["id"], len(contents), "personal")
    return {"ok": True, "attachment": attachment}


@router.get("/evaluations/{eval_id}/files/{att_id}")
async def download_eval_file(eval_id: str, att_id: str, user=Depends(get_current_user)):
    from fastapi.responses import FileResponse, Response
    e = await db.hh_evaluations.find_one({"id": eval_id}, {"attachments": 1})
    att = next((a for a in (e or {}).get("attachments", []) if a.get("id") == att_id), None)
    if att and att.get("object_path"):
        data, ct = await asyncio.to_thread(st_get_object, att["object_path"])
        return Response(content=data, media_type=att.get("mime") or ct)
    for f in UPLOAD_DIR.glob(f"eval_{eval_id}_{att_id}_*"):
        return FileResponse(path=str(f))
    raise HTTPException(404, "Fișier inexistent.")


@router.post("/evaluations/{eval_id}/submit")
async def submit_evaluation(eval_id: str, user=Depends(get_current_user)):
    """Submit a draft evaluation for admin approval."""
    e = await db.hh_evaluations.find_one({"id": eval_id})
    if not e:
        raise HTTPException(404, "Evaluare inexistentă.")
    if e.get("specialist_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Doar specialistul poate submite.")
    if e.get("status") not in ("draft", "rejected"):
        raise HTTPException(400, f"Status curent {e.get('status')} nu permite submit.")
    await db.hh_evaluations.update_one(
        {"id": eval_id},
        {"$set": {"status": "pending_approval", "submitted_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "status": "pending_approval"}


@router.get("/evaluations")
async def list_evaluations(
    twin_project_id: Optional[str] = None,
    status: Optional[str] = None,
    user=Depends(get_current_user),
):
    if not await _is_feature_enabled():
        raise HTTPException(403, "House Health nu este activ.")
    q = {}
    if twin_project_id:
        q["twin_project_id"] = twin_project_id
    if status:
        q["status"] = status
    # Clients see only their twin's evals; specialists see theirs; admins see all
    if user.get("role") == "client":
        if not twin_project_id:
            raise HTTPException(400, "twin_project_id obligatoriu pentru client.")
        await _assert_twin_owner(twin_project_id, user["id"])
    elif user.get("role") == "specialist":
        q["specialist_id"] = user["id"]
    items = []
    async for e in db.hh_evaluations.find(q, {"_id": 0}).sort("date", -1).limit(100):
        items.append(e)
    return {"items": items, "count": len(items)}


# ============================================================================
# Phase 3 — Admin approval
# ============================================================================
@admin_router.get("/evaluations")
async def admin_list_evaluations(
    status: Optional[str] = None,
    user=Depends(require_role("admin")),
):
    q = {}
    if status:
        q["status"] = status
    items = []
    async for e in db.hh_evaluations.find(q, {"_id": 0}).sort("submitted_at", -1).limit(200):
        items.append(e)
    return {"items": items, "count": len(items)}


class ApprovalAction(BaseModel):
    note: Optional[str] = None


@admin_router.post("/evaluations/{eval_id}/approve")
async def admin_approve_evaluation(eval_id: str, payload: ApprovalAction, user=Depends(require_role("admin"))):
    e = await db.hh_evaluations.find_one({"id": eval_id})
    if not e:
        raise HTTPException(404, "Evaluare inexistentă.")
    await db.hh_evaluations.update_one(
        {"id": eval_id},
        {"$set": {
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": user.get("email"),
            "approval_note": (payload.note or "")[:500],
        }},
    )
    await db.hh_audit_log.insert_one({
        "user_id": user["id"],
        "action": "evaluation_approved",
        "resource_id": eval_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "status": "approved"}


@admin_router.post("/evaluations/{eval_id}/reject")
async def admin_reject_evaluation(eval_id: str, payload: ApprovalAction, user=Depends(require_role("admin"))):
    e = await db.hh_evaluations.find_one({"id": eval_id})
    if not e:
        raise HTTPException(404, "Evaluare inexistentă.")
    await db.hh_evaluations.update_one(
        {"id": eval_id},
        {"$set": {
            "status": "rejected",
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": user.get("email"),
            "rejection_reason": (payload.note or "")[:500],
        }},
    )
    await db.hh_audit_log.insert_one({
        "user_id": user["id"],
        "action": "evaluation_rejected",
        "resource_id": eval_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "status": "rejected"}


@router.get("/equipment-catalog")
async def equipment_catalog(user=Depends(get_current_user)):
    """Static catalog of allowed equipment per evaluation kind."""
    return {"equipment": EVAL_EQUIPMENT, "kinds": ALLOWED_EVAL_KINDS, "doc_categories": ALLOWED_DOC_CATEGORIES, "external_types": ALLOWED_EXTERNAL_TYPES}
