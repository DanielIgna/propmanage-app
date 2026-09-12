"""PropManage router: property_timeline."""
import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from core_utils import serialize_doc
from deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["property_timeline"])

# ============= PROPERTY TIMELINE =============

@router.get("/properties/{prop_id}/timeline")
async def property_timeline(prop_id: str, user: dict = Depends(get_current_user)):
    """Chronological list of all events for a property"""
    prop = await db.properties.find_one({"_id": ObjectId(prop_id)})
    if not prop: raise HTTPException(404, "Property not found")
    
    # Aggregate all events: requests + maintenance logs
    requests_docs = await db.requests.find({"property_id": prop_id}).to_list(200)
    
    events = []
    for r in requests_docs:
        events.append({
            "type": "request_created",
            "title": r.get("title"),
            "description": f"Solicitare {r.get('category', '')} ({r.get('priority', '')})",
            "timestamp": r.get("created_at"),
            "status": r.get("status"),
            "request_id": str(r["_id"]),
        })
        if r.get("assigned_at"):
            events.append({
                "type": "specialist_assigned",
                "title": f"Specialist alocat: {r.get('specialist_name','')}",
                "description": r.get("title"),
                "timestamp": r["assigned_at"],
                "request_id": str(r["_id"]),
            })
        if r.get("completed_at"):
            events.append({
                "type": "work_completed",
                "title": f"Finalizat: {r.get('title','')}",
                "description": f"De {r.get('specialist_name','')}",
                "timestamp": r["completed_at"],
                "request_id": str(r["_id"]),
            })
        if r.get("confirmed_at"):
            events.append({
                "type": "confirmed",
                "title": f"Confirmat & plătit: {r.get('escrow_amount','—')} RON",
                "description": r.get("title"),
                "timestamp": r["confirmed_at"],
                "request_id": str(r["_id"]),
            })
    
    # Documents (CX-2 — Cartea Casei: fiecare document = eveniment în memorie)
    doc_rows = await db.property_documents.find({"property_id": prop_id, "deleted": {"$ne": True}}).to_list(300)
    for d in doc_rows:
        events.append({
            "type": "document_uploaded",
            "title": f"Document: {d.get('title', '')}",
            "description": f"{d.get('category', '')}" + (f" · {d.get('company')}" if d.get("company") else ""),
            "timestamp": d.get("uploaded_at"),
            "doc_id": str(d["_id"]),
        })
        if d.get("warranty_end"):
            events.append({
                "type": "warranty_registered",
                "title": f"Garanție înregistrată: {d.get('title', '')}",
                "description": f"Valabilă până la {d.get('warranty_end')}",
                "timestamp": d.get("uploaded_at"),
                "doc_id": str(d["_id"]),
            })

    # Sort newest first
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return {
        "property": serialize_doc(prop),
        "events": events,
        "total": len(events),
    }


