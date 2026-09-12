"""PropManage router: operator."""
import logging
from typing import Optional, Literal
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from core_utils import serialize_doc
from deps import require_role
from services import notify, log_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["operator"])

# ============= OPERATOR NON-CONFORMITY FLAG =============
class NonConformityIn(BaseModel):
    target_type: Literal["request", "property", "twin"]
    target_id: str
    reason: str = Field(min_length=5, max_length=2000)
    severity: Literal["low", "medium", "high"] = "medium"

@router.post("/operator/flag-nonconformity")
async def operator_flag_nonconformity(data: NonConformityIn, user: dict = Depends(require_role("operator"))):
    """Operator flags a request/property/twin as non-conformant. Notifies all admins + logs event."""
    # Validate target exists
    related_request_id = None
    related_property_id = None
    if data.target_type == "request":
        r = await db.requests.find_one({"_id": ObjectId(data.target_id)})
        if not r: raise HTTPException(404, "Cerere inexistentă.")
        related_request_id = data.target_id
        related_property_id = r.get("property_id")
    elif data.target_type == "property":
        p = await db.properties.find_one({"_id": ObjectId(data.target_id)})
        if not p: raise HTTPException(404, "Proprietate inexistentă.")
        related_property_id = data.target_id
    elif data.target_type == "twin":
        t = await db.twins.find_one({"_id": ObjectId(data.target_id)})
        if not t: raise HTTPException(404, "Twin inexistent.")
        related_property_id = t.get("property_id")

    doc = {
        "operator_id": user["id"],
        "operator_name": user["name"],
        "target_type": data.target_type,
        "target_id": data.target_id,
        "related_request_id": related_request_id,
        "related_property_id": related_property_id,
        "reason": data.reason,
        "severity": data.severity,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.nonconformities.insert_one(doc)
    flag_id = str(res.inserted_id)
    # Log event
    await log_event(related_request_id, "operator.flagged_nonconformity", actor=user,
                    property_id=related_property_id,
                    payload={"target_type": data.target_type, "target_id": data.target_id, "severity": data.severity, "reason": data.reason[:200]})
    # Notify all admins
    async for admin in db.users.find({"role": "admin"}):
        await notify(
            str(admin["_id"]),
            f"⚠ Sesizare operator ({data.severity})",
            f"{user['name']} a raportat o neconformitate pe {data.target_type}. Motiv: {data.reason[:140]}",
            type_="nonconformity",
            link="/admin"
        )
    # Notify the assigned specialist (and client, if any) when the flag targets a request
    if related_request_id:
        try:
            req = await db.requests.find_one({"_id": ObjectId(related_request_id)})
        except Exception:
            req = None
        if req:
            sev_label = {"low": "minoră", "medium": "medie", "high": "majoră", "critical": "critică"}.get(data.severity, data.severity)
            if req.get("specialist_id"):
                await notify(
                    req["specialist_id"],
                    f"⚠ Sesizare pe lucrarea ta ({sev_label})",
                    f"Operatorul {user['name']} a raportat o neconformitate pe '{req.get('title', 'cererea')}'. Motiv: {data.reason[:140]}",
                    type_="nonconformity_specialist",
                    link="/specialist",
                )
            if req.get("client_id"):
                await notify(
                    req["client_id"],
                    f"ℹ Sesizare pe lucrarea ta ({sev_label})",
                    f"Operatorul {user['name']} a raportat o problemă pe lucrarea ta. Admin-ul verifică situația.",
                    type_="nonconformity_client",
                    link="/client",
                )
    return {"ok": True, "id": flag_id}

@router.get("/admin/nonconformities")
async def list_nonconformities(user: dict = Depends(require_role("admin")), status: Optional[str] = None):
    q = {} if not status else {"status": status}
    docs = await db.nonconformities.find(q).sort("created_at", -1).to_list(200)
    return [serialize_doc(d) for d in docs]

class NonConformityResolveIn(BaseModel):
    resolution: str = Field(min_length=3, max_length=1000)

@router.post("/admin/nonconformities/{flag_id}/resolve")
async def resolve_nonconformity(flag_id: str, data: NonConformityResolveIn, user: dict = Depends(require_role("admin"))):
    flag = await db.nonconformities.find_one({"_id": ObjectId(flag_id)})
    if not flag: raise HTTPException(404, "Sesizare inexistentă.")
    await db.nonconformities.update_one(
        {"_id": ObjectId(flag_id)},
        {"$set": {
            "status": "resolved",
            "resolution": data.resolution,
            "resolved_by": user["id"],
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    await log_event(flag.get("related_request_id"), "admin.resolved_nonconformity", actor=user,
                    property_id=flag.get("related_property_id"),
                    payload={"flag_id": flag_id, "resolution": data.resolution[:200]})
    # Notify operator
    await notify(
        flag["operator_id"],
        "Sesizarea ta a fost rezolvată",
        f"Admin {user['name']}: {data.resolution[:200]}",
        type_="nonconformity_resolved",
        link="/operator"
    )
    return {"ok": True}

