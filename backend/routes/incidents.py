"""PropManage — Status Page Incidents

Admin posts incidents manually (when auto-monitor or user reports detect issues).
Each incident has a lifecycle of status updates (investigating → identified →
monitoring → resolved). Listed publicly on /status for transparency.

Schema (db.incidents):
- id: ObjectId
- title: str (e.g. "Email delivery delayed")
- severity: "minor" | "major" | "critical"
- components: list[str] (e.g. ["email", "ai_concierge"])
- status: "investigating" | "identified" | "monitoring" | "resolved"
- started_at: ISO datetime
- resolved_at: ISO datetime | None
- duration_minutes: int | None (computed on close)
- updates: list[{posted_at, status, message, posted_by}]
- created_by: admin email
"""
import logging
from datetime import datetime, timezone
from typing import List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.incidents")

# Two routers: one admin-only, one public.
admin_router = APIRouter(prefix="/api/admin/incidents", tags=["admin-incidents"])
public_router = APIRouter(prefix="/api/public", tags=["public-status"])


VALID_SEVERITIES = {"minor", "major", "critical"}
VALID_STATUSES = {"investigating", "identified", "monitoring", "resolved"}
VALID_COMPONENTS = {"api", "database", "ai_concierge", "payments", "email",
                    "authentication", "push_notifications"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(doc: dict) -> dict:
    if not doc:
        return {}
    raw_id = doc.pop("_id", None)
    out = {**doc}
    if raw_id is not None:
        out["id"] = str(raw_id)
    return out


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=4, max_length=140)
    severity: str = Field(..., description="minor | major | critical")
    components: List[str] = Field(default_factory=list)
    message: str = Field(..., min_length=4, max_length=2000,
                         description="Initial update message")


class IncidentUpdate(BaseModel):
    status: str = Field(..., description="investigating | identified | monitoring | resolved")
    message: str = Field(..., min_length=4, max_length=2000)


@admin_router.post("")
async def create_incident(
    payload: IncidentCreate,
    user: dict = Depends(require_role("admin")),
):
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(400, f"Invalid severity. Use one of: {sorted(VALID_SEVERITIES)}")
    bad = [c for c in payload.components if c not in VALID_COMPONENTS]
    if bad:
        raise HTTPException(400, f"Invalid component(s): {bad}. Allowed: {sorted(VALID_COMPONENTS)}")

    now = _now()
    initial_update = {
        "posted_at": now,
        "status": "investigating",
        "message": payload.message,
        "posted_by": user.get("email"),
    }
    doc = {
        "title": payload.title.strip(),
        "severity": payload.severity,
        "components": payload.components,
        "status": "investigating",
        "started_at": now,
        "resolved_at": None,
        "duration_minutes": None,
        "updates": [initial_update],
        "created_by": user.get("email"),
    }
    res = await db.incidents.insert_one(doc)
    doc["_id"] = res.inserted_id
    logger.info(f"[Incidents] created by {user.get('email')}: {payload.title} ({payload.severity})")
    return _serialize(doc)


@admin_router.post("/{incident_id}/update")
async def post_update(
    incident_id: str,
    payload: IncidentUpdate,
    user: dict = Depends(require_role("admin")),
):
    if payload.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Use one of: {sorted(VALID_STATUSES)}")
    try:
        oid = ObjectId(incident_id)
    except InvalidId:
        raise HTTPException(400, "Invalid incident id") from None

    incident = await db.incidents.find_one({"_id": oid})
    if not incident:
        raise HTTPException(404, "Incident not found")
    if incident.get("status") == "resolved":
        raise HTTPException(409, "Incident is already resolved")

    now = _now()
    update_entry = {
        "posted_at": now,
        "status": payload.status,
        "message": payload.message,
        "posted_by": user.get("email"),
    }
    updates_op: dict = {
        "$push": {"updates": update_entry},
        "$set": {"status": payload.status, "updated_at": now},
    }
    # When resolving, compute duration_minutes from started_at
    if payload.status == "resolved":
        started_at = incident.get("started_at")
        try:
            started_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            duration = int((datetime.now(timezone.utc) - started_dt).total_seconds() // 60)
        except Exception:  # noqa: BLE001
            duration = None
        updates_op["$set"].update({
            "resolved_at": now,
            "duration_minutes": duration,
        })

    await db.incidents.update_one({"_id": oid}, updates_op)
    refreshed = await db.incidents.find_one({"_id": oid})
    logger.info(f"[Incidents] update {incident_id} → {payload.status} by {user.get('email')}")
    return _serialize(refreshed)


@admin_router.get("")
async def list_incidents_admin(
    days: int = Query(60, le=365),
    user: dict = Depends(require_role("admin")),
):
    """Admin view: full history with all metadata."""
    from datetime import timedelta as _td
    cutoff = (datetime.now(timezone.utc) - _td(days=days)).isoformat()
    cursor = db.incidents.find({"started_at": {"$gte": cutoff}}).sort("started_at", -1)
    items = [_serialize(d) async for d in cursor]
    return {"items": items, "count": len(items)}


@admin_router.delete("/{incident_id}")
async def delete_incident(
    incident_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Hard-delete an incident (e.g. if posted by mistake). Use sparingly."""
    try:
        oid = ObjectId(incident_id)
    except InvalidId:
        raise HTTPException(400, "Invalid incident id") from None
    res = await db.incidents.delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Incident not found")
    logger.warning(f"[Incidents] deleted {incident_id} by {user.get('email')}")
    return {"ok": True, "deleted": incident_id}


# ============================================================================
# PUBLIC ENDPOINT (for /status page)
# ============================================================================


@public_router.get("/status-incidents")
async def list_public_incidents(days: int = Query(30, le=90)):
    """Public list of recent incidents — visible on /status page.

    No sensitive data: created_by, posted_by fields are stripped.
    """
    from datetime import timedelta as _td
    cutoff = (datetime.now(timezone.utc) - _td(days=days)).isoformat()
    cursor = db.incidents.find({"started_at": {"$gte": cutoff}}).sort("started_at", -1)
    items = []
    async for d in cursor:
        d = _serialize(d)
        d.pop("created_by", None)
        # Strip 'posted_by' from each update
        d["updates"] = [{k: v for k, v in u.items() if k != "posted_by"} for u in d.get("updates", [])]
        items.append(d)
    # Lightweight summary for the page header
    active = [i for i in items if i.get("status") != "resolved"]
    return {
        "items": items,
        "count": len(items),
        "active_count": len(active),
        "days": days,
    }
