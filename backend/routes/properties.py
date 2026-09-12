"""PropManage router: properties."""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from core_utils import serialize_doc, effective_role
from deps import get_current_user, require_role
from models import PropertyIn, PropertyUpdateIn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["properties"])

# ============= PROPERTIES (Client) =============# ============= PROPERTIES (Client) =============
@router.post("/properties")
async def create_property(data: PropertyIn, user: dict = Depends(require_role("client"))):
    doc = {
        **data.model_dump(),
        "owner_id": user["id"],
        "health_score": 75,
        "structure_health": 90,
        "utilities_health": 82,
        "documents_health": 100,
        "twin_unlocked": False,
        "wallet_unlocked": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    res = await db.properties.insert_one(doc)
    doc["id"] = str(res.inserted_id)
    doc.pop("_id", None)
    return doc

@router.get("/properties")
async def list_properties(user: dict = Depends(get_current_user)):
    eff = effective_role(user)
    # Clients (and dual-role specialists in client view) see their own properties
    q = {"owner_id": user["id"]} if eff in ("client", "specialist") else {}
    docs = await db.properties.find(q).to_list(100)
    # Enrich with twin status (one query for all)
    prop_ids = [str(d["_id"]) for d in docs]
    twin_map = {}
    if prop_ids:
        async for t in db.twins.find({"property_id": {"$in": prop_ids}}):
            twin_map[t["property_id"]] = t.get("status")
    out = []
    for d in docs:
        s = serialize_doc(d)
        s["twin_status"] = twin_map.get(s["id"])  # None | 'pending_validation' | 'approved' | 'needs_revision'
        out.append(s)
    return out

@router.get("/properties/{prop_id}")
async def get_property(prop_id: str, user: dict = Depends(get_current_user)):
    doc = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if not doc: raise HTTPException(404, "Property not found")
    return serialize_doc(doc)

@router.put("/properties/{prop_id}")
async def update_property(prop_id: str, data: PropertyUpdateIn, user: dict = Depends(require_role("client"))):
    """Update property (owner only)"""
    prop = await db.properties.find_one({"_id": ObjectId(prop_id), "owner_id": user["id"]})
    if not prop: raise HTTPException(404, "Property not found")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    if update:
        await db.properties.update_one({"_id": ObjectId(prop_id)}, {"$set": update})
    return serialize_doc(await db.properties.find_one({"_id": ObjectId(prop_id)}))

@router.delete("/properties/{prop_id}")
async def delete_property(prop_id: str, user: dict = Depends(require_role("client"))):
    """Delete property (owner only, no active requests)"""
    prop = await db.properties.find_one({"_id": ObjectId(prop_id), "owner_id": user["id"]})
    if not prop: raise HTTPException(404, "Property not found")
    # Check for active requests
    active = await db.requests.count_documents({
        "property_id": prop_id,
        "status": {"$in": ["assigned", "in_progress", "completed"]}
    })
    if active > 0:
        raise HTTPException(400, f"Cannot delete: {active} active request(s)")
    await db.properties.delete_one({"_id": ObjectId(prop_id)})
    return {"ok": True}

