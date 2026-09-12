"""PropManage router: operator_twins."""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from core_utils import serialize_doc
from deps import get_current_user, require_role
from services import notify, log_event
from models import TwinUpsertIn, TwinValidateIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["operator_twins"])

# ============= OPERATOR (Maintenance validation) =============
@router.get("/operator/queue")
async def operator_queue(user: dict = Depends(require_role("operator", "admin"))):
    """Pending maintenance logs awaiting validation"""
    docs = await db.maintenance_logs.find({"status": "pending"}).to_list(50)
    return [serialize_doc(d) for d in docs]

@router.post("/operator/logs/{log_id}/validate")
async def validate_log(log_id: str, action: str, user: dict = Depends(require_role("operator", "admin"))):
    if action not in ["approve", "reject"]:
        raise HTTPException(400, "Invalid action")
    await db.maintenance_logs.update_one(
        {"_id": ObjectId(log_id)},
        {"$set": {"status": action, "validated_by": user["id"], "validated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"ok": True}

# ============= OPERATOR: DIGITAL TWIN =============
@router.post("/properties/{prop_id}/twin/request")
async def request_twin_validation(prop_id: str, user: dict = Depends(get_current_user)):
    """Client requests a Digital Twin model build/review by Operator"""
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if not prop:
        raise HTTPException(404, "Property not found")
    if prop.get("owner_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(403, "Not allowed")
    twin = await db.twins.find_one({"property_id": prop_id})
    now_iso = datetime.now(timezone.utc).isoformat()
    if twin:
        await db.twins.update_one(
            {"_id": twin["_id"]},
            {"$set": {"status": "pending_validation", "requested_at": now_iso}}
        )
    else:
        await db.twins.insert_one({
            "property_id": prop_id,
            "status": "pending_validation",
            "rooms": [],
            "assets": [],
            "requested_at": now_iso,
            "created_at": now_iso,
        })
    # Notify all operators
    ops = await db.users.find({"role": "operator"}).to_list(10)
    for op in ops:
        await notify(str(op["_id"]), "Twin nou de validat", f"Proprietatea '{prop.get('name','')}' așteaptă validarea Digital Twin.", type_="twin", link="/operator")
    await log_event(None, "twin.requested", actor=user, property_id=prop_id, payload={"property_name": prop.get("name")})
    return {"ok": True}

@router.get("/properties/{prop_id}/twin")
async def get_my_property_twin(prop_id: str, user: dict = Depends(get_current_user)):
    """Read-only twin view for the property OWNER (client), the assigned specialist
    of an active/historical request on this property, admin and operator."""
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if not prop:
        raise HTTPException(404, "Property not found")
    is_authorized = (
        prop.get("owner_id") == user["id"]
        or user.get("role") in ("admin", "operator")
    )
    if not is_authorized and user.get("role") == "specialist":
        # Allow specialists currently or previously assigned to any request on this property
        spec_request = await db.requests.find_one({
            "property_id": prop_id,
            "specialist_id": user["id"],
        })
        is_authorized = bool(spec_request)
    if not is_authorized:
        raise HTTPException(403, "Not allowed")
    twin = await db.twins.find_one({"property_id": prop_id})
    if not twin:
        return {"status": "not_requested", "rooms": [], "assets": []}
    return {
        "status": twin.get("status"),
        "rooms": twin.get("rooms") or [],
        "assets": twin.get("assets") or [],
        "notes": twin.get("notes"),
        "requested_at": twin.get("requested_at"),
        "validated_at": twin.get("validated_at"),
    }


@router.get("/properties/{prop_id}/spaces")
async def get_property_spaces(prop_id: str, user: dict = Depends(get_current_user)):
    """P1 — Room/Space ca ancoră canonică cross-system.

    Camerele NU se dublează: sursa e `twins.rooms[]` (uuid stabil + geometrie). Acest endpoint
    doar EXPUNE camerele existente ca „spaces" referențiabile de documente / modele / active / pini,
    fără colecție nouă și fără migrare. Autorizare identică cu vizualizarea twin-ului.
    """
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if not prop:
        raise HTTPException(404, "Property not found")
    is_authorized = (
        prop.get("owner_id") == user["id"]
        or user.get("role") in ("admin", "operator")
    )
    if not is_authorized and user.get("role") == "specialist":
        spec_request = await db.requests.find_one({"property_id": prop_id, "specialist_id": user["id"]})
        is_authorized = bool(spec_request)
    if not is_authorized:
        raise HTTPException(403, "Not allowed")
    twin = await db.twins.find_one({"property_id": prop_id})
    rooms = (twin.get("rooms") or []) if twin else []
    spaces = [
        {
            "space_id": r.get("id"),
            "name": r.get("name"),
            "type": r.get("type"),
            "area": r.get("area"),
            "source": "twin_2d",
        }
        for r in rooms if r.get("id")
    ]
    return {"property_id": prop_id, "count": len(spaces), "spaces": spaces}


@router.get("/properties/{prop_id}/digital-twin")
async def get_property_digital_twin(prop_id: str, user: dict = Depends(get_current_user)):
    """P1 — UNIFIED PROPERTY DIGITAL TWIN overview.

    Contractul „aceeași proprietate, două straturi": 2D (`twins`: camere/active) + 3D
    (`digital_twin_projects`/`models` ancorate de property_id în P0). Read-only, non-breaking.
    Autorizare identică cu vizualizarea twin-ului (owner/admin/operator/specialist asignat).
    """
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if not prop:
        raise HTTPException(404, "Property not found")
    is_authorized = (
        prop.get("owner_id") == user["id"]
        or user.get("role") in ("admin", "operator")
    )
    if not is_authorized and user.get("role") == "specialist":
        spec_request = await db.requests.find_one({"property_id": prop_id, "specialist_id": user["id"]})
        is_authorized = bool(spec_request)
    if not is_authorized:
        raise HTTPException(403, "Not allowed")

    twin = await db.twins.find_one({"property_id": prop_id})
    rooms = (twin.get("rooms") or []) if twin else []
    assets = (twin.get("assets") or []) if twin else []
    twin_2d = {
        "exists": bool(twin),
        "status": (twin.get("status") if twin else "not_requested"),
        "rooms_count": len(rooms),
        "assets_count": len(assets),
        "project_id": (twin.get("project_id") if twin else None),
    }

    projects = []
    async for p in db.digital_twin_projects.find({"property_id": prop_id}).sort("updated_at", -1).limit(50):
        models_count = await db.digital_twin_models.count_documents({"project_id": p["id"], "kind": {"$ne": "source"}})
        projects.append({
            "id": p["id"],
            "name": p.get("name"),
            "model_url": p.get("model_url"),
            "models_count": models_count,
            "property_link_status": p.get("property_link_status"),
            "updated_at": p.get("updated_at"),
        })
    has_model = any(pr.get("model_url") or pr.get("models_count") for pr in projects)
    twin_3d = {
        "exists": bool(projects),
        "has_model": has_model,
        "projects": projects,
    }

    return {
        "property_id": prop_id,
        "property_name": prop.get("name") or prop.get("address"),
        "twin_2d": twin_2d,
        "twin_3d": twin_3d,
    }


# ---------------------------------------------------------------------------
# CLIENT — Digital Twin summary across all owned properties
# Used by Settings → Digital Twin 3D section.
# ---------------------------------------------------------------------------
_TWIN_STATUS_RANK = {
    # Higher rank = more "available" to the user. Used to pick a primary twin.
    "approved": 5,
    "draft": 4,
    "needs_revision": 3,
    "pending_validation": 2,
    "not_requested": 1,
}

_TWIN_STATUS_LABEL = {
    "approved": "Disponibil",
    "draft": "În generare",
    "needs_revision": "Eșuat",
    "pending_validation": "În procesare",
    "not_requested": "Inexistent",
}


@router.get("/me/digital-twins")
async def my_digital_twins(user: dict = Depends(get_current_user)):
    """Return Digital Twin summary for the authenticated user's properties.

    Output shape:
        {
            "has_any": bool,              # User owns at least one property
            "has_available": bool,        # At least one twin in 'approved' state
            "primary": { ... } | None,    # Best twin to show first (highest rank)
            "twins": [
                {
                    "property_id": str,
                    "property_name": str,
                    "twin_id": str | None,
                    "status": str,         # raw status code
                    "status_label": str,   # localized Romanian label
                    "progress": int,       # 0-100 (rough estimate)
                    "model_url": None,     # placeholder for future GLB upload
                    "requested_at": iso,
                    "validated_at": iso,
                }
            ]
        }
    """
    props = await db.properties.find(
        {"owner_id": user["id"], "deleted": {"$ne": True}},
        {"_id": 1, "name": 1},
    ).to_list(50)
    if not props:
        return {"has_any": False, "has_available": False, "primary": None, "twins": []}

    prop_ids = [str(p["_id"]) for p in props]
    # Batch-fetch all twins for owned properties in one query
    twin_docs = await db.twins.find({"property_id": {"$in": prop_ids}}).to_list(len(prop_ids))
    twin_by_pid = {t["property_id"]: t for t in twin_docs}
    # Batch-fetch DT projects (Phase G) so the frontend can deep-link directly into
    # the 3D viewer when the architect has uploaded a GLB/GLTF model.
    dt_projects = await db.digital_twin_projects.find(
        {"property_id": {"$in": prop_ids}}
    ).to_list(len(prop_ids))
    dt_by_pid = {}
    for proj in dt_projects:
        pid = proj.get("property_id")
        if not pid:
            continue
        # Prefer the most recent project per property
        existing = dt_by_pid.get(pid)
        if not existing or (proj.get("updated_at") or "") > (existing.get("updated_at") or ""):
            dt_by_pid[pid] = proj

    items: list[dict] = []
    for p in props:
        pid = str(p["_id"])
        t = twin_by_pid.get(pid)
        proj = dt_by_pid.get(pid)
        status_code = (t or {}).get("status") or "not_requested"
        # If a DT project has a model_url, treat it as approved even if the legacy
        # twins doc isn't there — the architect has shipped a viewable model.
        if proj and proj.get("model_url"):
            status_code = "approved"
        # Rough progress estimate based on status (frontend can render bar)
        progress = {
            "approved": 100,
            "draft": 70,
            "needs_revision": 50,
            "pending_validation": 30,
            "not_requested": 0,
        }.get(status_code, 0)
        items.append({
            "property_id": pid,
            "property_name": p.get("name") or "Imobil",
            "twin_id": str(t["_id"]) if t else None,
            "status": status_code,
            "status_label": _TWIN_STATUS_LABEL.get(status_code, status_code),
            "progress": progress,
            # DT project info — frontend opens the real 3D viewer when these are set
            "dt_project_id": proj.get("id") if proj else None,
            "dt_project_name": proj.get("name") if proj else None,
            "model_url": (proj or {}).get("model_url"),
            "requested_at": (t or {}).get("requested_at"),
            "validated_at": (t or {}).get("validated_at"),
        })
    # Pick a primary twin: highest rank, ties broken by validated_at desc, then requested_at desc
    items_sorted = sorted(
        items,
        key=lambda x: (
            _TWIN_STATUS_RANK.get(x["status"], 0),
            x.get("validated_at") or "",
            x.get("requested_at") or "",
        ),
        reverse=True,
    )
    primary = items_sorted[0] if items_sorted else None
    has_available = any(x["status"] == "approved" for x in items)
    return {
        "has_any": True,
        "has_available": has_available,
        "primary": primary,
        "twins": items_sorted,
    }


@router.get("/operator/twins")
async def operator_list_twins(user: dict = Depends(require_role("operator", "admin"))):
    """List all twins (pending + approved) with batched enrichment"""
    docs = await db.twins.find({}).sort("requested_at", -1).to_list(100)
    # Defensive: filter out docs with missing / corrupt property_id (e.g. legacy 'None' string)
    prop_ids = []
    for d in docs:
        pid = d.get("property_id")
        if not pid or not isinstance(pid, str) or len(pid) != 24:
            continue
        try:
            prop_ids.append(ObjectId(pid))
        except Exception:
            continue
    props_map = {}
    owner_ids = set()
    if prop_ids:
        async for p in db.properties.find({"_id": {"$in": prop_ids}}):
            props_map[str(p["_id"])] = p
            if p.get("owner_id"): owner_ids.add(p["owner_id"])
    owners_map = {}
    if owner_ids:
        async for o in db.users.find({"_id": {"$in": [ObjectId(oid) for oid in owner_ids]}}):
            owners_map[str(o["_id"])] = o
    out = []
    for d in docs:
        d = serialize_doc(d)
        prop = props_map.get(d.get("property_id"))
        # Always set enriched fields (None if not found) so consumers can rely on keys existing
        d["property_name"] = prop.get("name") if prop else None
        d["property_address"] = prop.get("address") if prop else None
        d["property_type"] = prop.get("type") if prop else None
        d["property_surface"] = prop.get("surface") if prop else None
        d["property_rooms"] = prop.get("rooms") if prop else None
        owner = owners_map.get(prop.get("owner_id")) if prop else None
        d["owner_name"] = owner.get("name") if owner else None
        d["owner_email"] = owner.get("email") if owner else None
        out.append(d)
    return out

@router.get("/operator/twins/{prop_id}")
async def operator_get_twin(prop_id: str, user: dict = Depends(require_role("operator", "admin"))):
    twin = await db.twins.find_one({"property_id": prop_id})
    if not twin:
        # Return empty draft so operator can start editing
        prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
        if not prop:
            raise HTTPException(404, "Property not found")
        return {
            "property_id": prop_id,
            "status": "draft",
            "rooms": [],
            "assets": [],
            "property_name": prop.get("name"),
        }
    twin = serialize_doc(twin)
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if prop:
        twin["property_name"] = prop.get("name")
        twin["property_address"] = prop.get("address")
        twin["property_surface"] = prop.get("surface")
    return twin

@router.post("/operator/twins/{prop_id}")
async def operator_save_twin(prop_id: str, data: TwinUpsertIn, user: dict = Depends(require_role("operator", "admin"))):
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "rooms": [r.model_dump() for r in data.rooms],
        "assets": [a.model_dump() for a in data.assets],
        "model_url": data.model_url,
        "notes": data.notes,
        "updated_at": now_iso,
        "updated_by": user["id"],
    }
    existing = await db.twins.find_one({"property_id": prop_id})
    if existing:
        await db.twins.update_one({"_id": existing["_id"]}, {"$set": payload})
    else:
        payload["property_id"] = prop_id
        payload["status"] = "draft"
        payload["created_at"] = now_iso
        await db.twins.insert_one(payload)
    return {"ok": True}

@router.post("/operator/twins/{prop_id}/validate")
async def operator_validate_twin(prop_id: str, data: TwinValidateIn, user: dict = Depends(require_role("operator", "admin"))):
    twin = await db.twins.find_one({"property_id": prop_id})
    if not twin:
        raise HTTPException(404, "Twin not found")
    new_status = "approved" if data.action == "approve" else "needs_revision"
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.twins.update_one(
        {"_id": twin["_id"]},
        {"$set": {
            "status": new_status,
            "validation_notes": data.notes,
            "validated_at": now_iso,
            "validated_by": user["id"],
        }}
    )
    # Update property twin_unlocked flag
    if data.action == "approve":
        await db.properties.update_one(
            {"_id": ObjectId(prop_id)},
            {"$set": {"twin_unlocked": True}}
        )
    # Notify property owner
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if prop and prop.get("owner_id"):
        if data.action == "approve":
            await notify(prop["owner_id"], "Digital Twin aprobat", f"Twin-ul proprietății '{prop.get('name','')}' a fost validat și activat.", type_="twin", link="/client")
        else:
            await notify(prop["owner_id"], "Twin necesită revizie", f"Twin-ul proprietății '{prop.get('name','')}' necesită ajustări. {data.notes or ''}", type_="twin", link="/client")
    # Notify specialists with active (assigned/in_progress/completed) requests on this property
    notified_specialists = set()
    async for req in db.requests.find({
        "property_id": prop_id,
        "status": {"$in": ["assigned", "in_progress", "completed"]},
        "specialist_id": {"$ne": None},
    }, {"specialist_id": 1, "title": 1}):
        sid = req.get("specialist_id")
        if sid and sid not in notified_specialists:
            notified_specialists.add(sid)
            if data.action == "approve":
                await notify(
                    sid,
                    "🏠 Twin actualizat pe proprietatea ta de lucru",
                    f"Operatorul a validat 2D twin-ul proprietatii pe care lucrezi ('{prop.get('name', '')}'). Acum poti vedea camerele si asset-urile in profilul cererii.",
                    type_="twin_specialist_update",
                    link="/specialist",
                )
            else:
                await notify(
                    sid,
                    "⚠ Twin necesită revizie",
                    f"2D twin-ul proprietatii '{prop.get('name', '')}' (unde ai lucrare activa) a fost respins. Operatorul a notat: {(data.notes or '—')[:140]}",
                    type_="twin_specialist_update",
                    link="/specialist",
                )
    await log_event(None, "twin.validated", actor=user, property_id=prop_id,
                    payload={"action": data.action, "new_status": new_status, "notes": (data.notes or "")[:200], "specialists_notified": len(notified_specialists)})
    return {"ok": True, "status": new_status, "specialists_notified": len(notified_specialists)}

