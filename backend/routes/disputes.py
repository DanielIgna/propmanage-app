"""PropManage router: disputes."""
import logging
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from db import db
from core_utils import serialize_doc
from deps import get_current_user, require_role
from services import notify, log_event
from models import DisputeOpenIn, DisputeResolveIn
from email_service import (
    send_template, tpl_dispute_opened, tpl_dispute_resolved,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["disputes"])

# ============= DISPUTES =============
@router.post("/requests/{req_id}/dispute")
async def open_dispute(req_id: str, data: DisputeOpenIn, user: dict = Depends(get_current_user)):
    """Client or assigned specialist opens a dispute on a job"""
    req = await db.requests.find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(404, "Request not found")
    # Authorization: must be the request's client or the assigned specialist
    role = None
    if req.get("client_id") == user["id"]:
        role = "client"
    elif req.get("specialist_id") == user["id"]:
        role = "specialist"
    else:
        raise HTTPException(403, "Not allowed")
    # Only allow disputes on jobs that have funds in escrow or work started
    if req.get("status") not in ["assigned", "in_progress", "completed"]:
        raise HTTPException(400, "Disputes can only be opened on active jobs")
    # Block dispute after escrow is released (prevents race with client.confirm())
    if req.get("escrow_status") == "released":
        raise HTTPException(400, "Plata a fost deja eliberată din escrow - dispută indisponibilă")
    # Prevent duplicates
    existing = await db.disputes.find_one({"request_id": req_id, "status": "open"})
    if existing:
        raise HTTPException(400, "An open dispute already exists for this job")
    dispute = {
        "request_id": req_id,
        "opened_by": user["id"],
        "opened_by_role": role,
        "opened_by_name": user.get("name"),
        "reason": data.reason,
        "evidence_urls": data.evidence_urls or [],
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.disputes.insert_one(dispute)
    # Mark request as disputed
    await db.requests.update_one(
        {"_id": ObjectId(req_id)},
        {"$set": {"disputed": True, "escrow_status": "frozen"}}
    )
    # Notify the other party + admin (best-effort: pick first admin)
    other_user_id = req.get("specialist_id") if role == "client" else req.get("client_id")
    other_user_doc = None
    if other_user_id:
        other_user_doc = await db.users.find_one({"_id": ObjectId(other_user_id)})
        await notify(other_user_id, "Dispută deschisă", f"O dispută a fost deschisă pe lucrarea '{req.get('title','')}'. Echipa admin va analiza cazul.", type_="dispute", link="/" + ("specialist" if role == "client" else "client"))
        if other_user_doc and other_user_doc.get("email"):
            await send_template(
                tpl_dispute_opened,
                other_user_doc.get("name", ""),
                req.get("title", ""),
                role,
                data.reason,
                "specialist" if role == "client" else "client",
                to=other_user_doc["email"],
            )
    admins = await db.users.find({"role": "admin"}).to_list(10)
    for a in admins:
        await notify(str(a["_id"]), "Nouă dispută", f"Dispută deschisă pe '{req.get('title','')}' de către {role}.", type_="dispute", link="/admin")
    await log_event(req_id, "dispute.opened", actor=user, payload={"reason": data.reason[:200], "opened_by_role": role})
    # Orchestrator: Dispute AI Triage (async, nu blochează răspunsul)
    try:
        import asyncio
        from orchestrator.engine import emit_signal
        asyncio.create_task(emit_signal("dispute_opened", {"dispute_id": str(result.inserted_id)}))
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": str(result.inserted_id)}

@router.get("/requests/{req_id}/dispute")
async def get_dispute_for_request(req_id: str, user: dict = Depends(get_current_user)):
    req = await db.requests.find_one({"_id": ObjectId(req_id)})
    if not req:
        raise HTTPException(404, "Request not found")
    if user["id"] not in [req.get("client_id"), req.get("specialist_id")] and user.get("role") != "admin":
        raise HTTPException(403, "Not allowed")
    doc = await db.disputes.find_one({"request_id": req_id})
    return serialize_doc(doc) if doc else None

@router.post("/admin/disputes/{dispute_id}/resolve")
async def resolve_dispute(dispute_id: str, data: DisputeResolveIn, user: dict = Depends(require_role("admin"))):
    dispute = await db.disputes.find_one({"_id": ObjectId(dispute_id)})
    if not dispute:
        raise HTTPException(404, "Dispute not found")
    if dispute.get("status") != "open":
        raise HTTPException(400, "Dispute already resolved")
    req = await db.requests.find_one({"_id": ObjectId(dispute["request_id"])})
    if not req:
        raise HTTPException(404, "Request not found")
    amount = req.get("escrow_amount") or 0
    client_id = req.get("client_id")
    specialist_id = req.get("specialist_id")
    
    if data.resolution == "refund_client":
        client_amount = amount
        specialist_amount = 0
    elif data.resolution == "pay_specialist":
        client_amount = 0
        specialist_amount = amount * 0.95  # 5% platform fee
    elif data.resolution == "split":
        pct = data.client_pct if data.client_pct is not None else 50
        if pct < 0 or pct > 100:
            raise HTTPException(400, "client_pct must be 0..100")
        client_amount = amount * (pct / 100)
        specialist_amount = (amount - client_amount) * 0.95
    else:
        raise HTTPException(400, "Invalid resolution")
    
    now_iso = datetime.now(timezone.utc).isoformat()
    if client_amount > 0 and client_id:
        await db.users.update_one({"_id": ObjectId(client_id)}, {"$inc": {"wallet_balance": client_amount}})
        await db.transactions.insert_one({
            "user_id": client_id, "type": "dispute_refund", "amount": client_amount,
            "request_id": dispute["request_id"], "created_at": now_iso,
        })
    if specialist_amount > 0 and specialist_id:
        await db.users.update_one({"_id": ObjectId(specialist_id)}, {"$inc": {"wallet_balance": specialist_amount}})
        await db.transactions.insert_one({
            "user_id": specialist_id, "type": "dispute_payment", "amount": specialist_amount,
            "request_id": dispute["request_id"], "created_at": now_iso,
        })
    
    await db.disputes.update_one(
        {"_id": ObjectId(dispute_id)},
        {"$set": {
            "status": "resolved",
            "resolution": data.resolution,
            "client_pct": data.client_pct,
            "client_amount": client_amount,
            "specialist_amount": specialist_amount,
            "notes": data.notes,
            "resolved_at": now_iso,
            "resolved_by": user["id"],
        }}
    )
    await db.requests.update_one(
        {"_id": ObjectId(dispute["request_id"])},
        {"$set": {"status": "confirmed", "escrow_status": "released", "disputed": False, "confirmed_at": now_iso}}
    )
    # Notify both parties
    if client_id:
        client_u = await db.users.find_one({"_id": ObjectId(client_id)})
        await notify(client_id, "Dispută rezolvată", f"Dispută rezolvată. Rambursare: {client_amount:.2f} RON.", type_="dispute", link="/client")
        if client_u and client_u.get("email") and client_amount > 0:
            await send_template(tpl_dispute_resolved, client_u.get("name", ""), req.get("title", ""), client_amount, "client", to=client_u["email"])
    if specialist_id:
        spec_u = await db.users.find_one({"_id": ObjectId(specialist_id)})
        await notify(specialist_id, "Dispută rezolvată", f"Dispută rezolvată. Plată: {specialist_amount:.2f} RON.", type_="dispute", link="/specialist")
        if spec_u and spec_u.get("email") and specialist_amount > 0:
            await send_template(tpl_dispute_resolved, spec_u.get("name", ""), req.get("title", ""), specialist_amount, "specialist", to=spec_u["email"])
    await log_event(dispute["request_id"], "dispute.resolved", actor=user,
                    payload={"client_amount": client_amount, "specialist_amount": specialist_amount, "client_pct": data.client_pct, "resolution": data.resolution[:200]})
    return {"ok": True, "client_amount": client_amount, "specialist_amount": specialist_amount}

