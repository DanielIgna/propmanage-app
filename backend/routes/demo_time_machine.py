"""PropManage — Demo Payment Time Machine (Phase 48b).

Admin-only endpoints that fast-forward the payment + project lifecycle for demos.
Bypasses role checks to let admin "act as" client or specialist on any active item.

NOT exposed to non-admin users. Each action logs a demo_simulated flag for audit clarity.
"""
import logging
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Body, Query

from db import db
from deps import require_role
from services import log_event, notify

logger = logging.getLogger("propmanage.demo_time_machine")
router = APIRouter(prefix="/api/admin/demo-tools", tags=["admin-demo-tools"])

LEAD_FEE = 45.0
SPECIALIST_SPLIT = 0.95
PLATFORM_SPLIT = 0.05

# ============= LIST ACTIVE ITEMS =============

@router.get("/requests")
async def list_demo_requests(
    limit: int = Query(50, le=200),
    user: dict = Depends(require_role("admin")),
):
    """Return all requests with current status for simulation."""
    cursor = db.requests.find({}).sort("created_at", -1).limit(limit)
    items = []
    async for r in cursor:
        client = await db.users.find_one({"_id": ObjectId(r["client_id"])}) if r.get("client_id") else None
        specialist = None
        if r.get("specialist_id"):
            try:
                specialist = await db.users.find_one({"_id": ObjectId(r["specialist_id"])})
            except InvalidId:
                pass
        items.append({
            "id": str(r["_id"]),
            "title": r.get("title") or "—",
            "status": r.get("status"),
            "escrow_status": r.get("escrow_status"),
            "escrow_amount": r.get("escrow_amount") or 0,
            "category": r.get("category"),
            "created_at": r.get("created_at"),
            "client_name": client.get("name") if client else "—",
            "client_email": client.get("email") if client else "—",
            "specialist_name": specialist.get("name") if specialist else None,
            "specialist_email": specialist.get("email") if specialist else None,
        })
    return {"items": items}


@router.get("/projects")
async def list_demo_projects(
    limit: int = Query(50, le=200),
    user: dict = Depends(require_role("admin")),
):
    cursor = db.projects.find({"milestones": {"$exists": True, "$ne": []}}).sort("updated_at", -1).limit(limit)
    items = []
    async for p in cursor:
        milestones = p.get("milestones") or []
        items.append({
            "id": str(p["_id"]),
            "name": p.get("name") or "—",
            "total_budget": p.get("total_budget") or 0,
            "milestones": [
                {
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "pct": m.get("pct"),
                    "amount": m.get("amount"),
                    "status": m.get("status"),
                    "funded_at": m.get("funded_at"),
                    "released_at": m.get("released_at"),
                    "warranty_until": m.get("warranty_until"),
                }
                for m in milestones
            ],
        })
    return {"items": items}


# ============= REQUEST SIMULATION ACTIONS =============

async def _get_request(req_id: str) -> dict:
    try:
        oid = ObjectId(req_id)
    except InvalidId:
        raise HTTPException(400, "Invalid request id")
    r = await db.requests.find_one({"_id": oid})
    if not r:
        raise HTTPException(404, "Request not found")
    return r


@router.post("/requests/{req_id}/simulate-payment")
async def sim_payment(req_id: str, user: dict = Depends(require_role("admin"))):
    """Simulate client paying into escrow (virtual money)."""
    r = await _get_request(req_id)
    amount = float(r.get("escrow_amount") or r.get("budget") or 500)
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {
            "escrow_status": "paid",
            "escrow_amount": amount,
            "escrow_paid_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    await log_event(req_id, "escrow.paid", actor=user, payload={"amount": amount, "demo_simulated": True})
    return {"ok": True, "status": "escrow_paid", "amount": amount}


@router.post("/requests/{req_id}/simulate-specialist-accept")
async def sim_accept(req_id: str, payload: dict = Body(default={}), user: dict = Depends(require_role("admin"))):
    """Pick a specialist (any verified one) and mark as accepted."""
    r = await _get_request(req_id)
    spec_id = payload.get("specialist_id")
    if not spec_id:
        spec = await db.users.find_one({"role": "specialist"})
        if not spec:
            raise HTTPException(400, "No specialist available")
        spec_id = str(spec["_id"])
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {
            "specialist_id": spec_id,
            "status": "assigned",
            "assigned_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    await log_event(req_id, "request.accepted", actor=user, payload={"specialist_id": spec_id, "lead_fee": LEAD_FEE, "demo_simulated": True})
    try:
        await notify(r["client_id"], "Specialist alocat", "Demo: specialist alocat pe cererea ta.", type_="assignment", link="/client")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "status": "assigned", "specialist_id": spec_id}


@router.post("/requests/{req_id}/simulate-start")
async def sim_start(req_id: str, user: dict = Depends(require_role("admin"))):
    r = await _get_request(req_id)
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {"status": "in_progress", "started_at": datetime.now(timezone.utc).isoformat()}},
    )
    await log_event(req_id, "work.started", actor=user, payload={"demo_simulated": True})
    return {"ok": True, "status": "in_progress"}


@router.post("/requests/{req_id}/simulate-complete")
async def sim_complete(req_id: str, user: dict = Depends(require_role("admin"))):
    r = await _get_request(req_id)
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
    )
    await log_event(req_id, "work.completed", actor=user, payload={"demo_simulated": True})
    try:
        await notify(r["client_id"], "Lucrare finalizată", "Demo: specialistul a finalizat lucrarea.", type_="completion", link="/client")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "status": "completed"}


@router.post("/requests/{req_id}/simulate-confirm")
async def sim_confirm(req_id: str, user: dict = Depends(require_role("admin"))):
    """Simulate client confirming → escrow releases 95/5."""
    r = await _get_request(req_id)
    if not r.get("specialist_id"):
        raise HTTPException(400, "No specialist on request")
    amount = float(r.get("escrow_amount") or 0)
    specialist_amount = round(amount * SPECIALIST_SPLIT, 2)
    platform_amount = round(amount * PLATFORM_SPLIT, 2)
    # Credit specialist wallet
    try:
        await db.users.update_one(
            {"_id": ObjectId(r["specialist_id"])},
            {"$inc": {"wallet_balance": specialist_amount}},
        )
    except InvalidId:
        pass
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {
            "status": "confirmed",
            "escrow_status": "released",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "specialist_payout": specialist_amount,
            "platform_fee": platform_amount,
        }},
    )
    await log_event(req_id, "work.confirmed", actor=user, payload={
        "specialist_amount": specialist_amount,
        "platform_amount": platform_amount,
        "demo_simulated": True,
    })
    try:
        await notify(r["specialist_id"], "Plată eliberată", f"Demo: {specialist_amount:.2f} RON eliberat.", type_="payment", link="/specialist")
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "status": "confirmed", "specialist_amount": specialist_amount, "platform_amount": platform_amount}


@router.post("/requests/{req_id}/simulate-dispute")
async def sim_dispute(req_id: str, payload: dict = Body(default={}), user: dict = Depends(require_role("admin"))):
    r = await _get_request(req_id)
    reason = (payload.get("reason") or "Demo dispute").strip()[:300]
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {"status": "disputed", "disputed_at": datetime.now(timezone.utc).isoformat(), "dispute_reason": reason}},
    )
    # Insert dispute record
    await db.disputes.insert_one({
        "request_id": req_id,
        "client_id": r.get("client_id"),
        "specialist_id": r.get("specialist_id"),
        "reason": reason,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "demo_simulated": True,
    })
    await log_event(req_id, "dispute.opened", actor=user, payload={"reason": reason, "demo_simulated": True})
    return {"ok": True, "status": "disputed"}


@router.post("/requests/{req_id}/simulate-refund")
async def sim_refund(req_id: str, user: dict = Depends(require_role("admin"))):
    """Refund escrow back to client wallet."""
    r = await _get_request(req_id)
    amount = float(r.get("escrow_amount") or 0)
    try:
        await db.users.update_one(
            {"_id": ObjectId(r["client_id"])},
            {"$inc": {"wallet_balance": amount}},
        )
    except InvalidId:
        pass
    await db.requests.update_one(
        {"_id": r["_id"]},
        {"$set": {
            "status": "refunded",
            "escrow_status": "refunded",
            "refunded_at": datetime.now(timezone.utc).isoformat(),
            "refund_amount": amount,
        }},
    )
    await log_event(req_id, "escrow.refunded", actor=user, payload={"amount": amount, "demo_simulated": True})
    return {"ok": True, "status": "refunded", "amount_refunded": amount}


@router.post("/requests/{req_id}/reset")
async def reset_request(req_id: str, user: dict = Depends(require_role("admin"))):
    """Reset request back to initial 'open' state — replay flow from scratch."""
    r = await _get_request(req_id)
    await db.requests.update_one(
        {"_id": r["_id"]},
        {
            "$set": {
                "status": "open",
                "escrow_status": "pending",
            },
            "$unset": {
                "specialist_id": "",
                "assigned_at": "",
                "started_at": "",
                "completed_at": "",
                "confirmed_at": "",
                "disputed_at": "",
                "dispute_reason": "",
                "refunded_at": "",
                "refund_amount": "",
                "specialist_payout": "",
                "platform_fee": "",
                "escrow_paid_at": "",
            },
        },
    )
    # Clean associated disputes
    await db.disputes.delete_many({"request_id": req_id, "demo_simulated": True})
    await log_event(req_id, "demo.reset", actor=user, payload={"demo_simulated": True})
    return {"ok": True, "status": "open"}


# ============= MILESTONE SIMULATION =============

async def _get_project_and_milestone(project_id: str, mid: str):
    try:
        oid = ObjectId(project_id)
    except InvalidId:
        raise HTTPException(400, "Invalid project id")
    proj = await db.projects.find_one({"_id": oid})
    if not proj:
        raise HTTPException(404, "Project not found")
    milestones = proj.get("milestones") or []
    idx = next((i for i, m in enumerate(milestones) if m.get("id") == mid), -1)
    if idx == -1:
        raise HTTPException(404, "Milestone not found")
    return proj, milestones, idx


@router.post("/projects/{project_id}/milestones/{mid}/sim-fund")
async def sim_milestone_fund(project_id: str, mid: str, user: dict = Depends(require_role("admin"))):
    proj, milestones, idx = await _get_project_and_milestone(project_id, mid)
    m = milestones[idx]
    if m.get("status") != "pending_funding":
        raise HTTPException(400, f"Milestone status is '{m.get('status')}', not pending_funding")
    milestones[idx]["status"] = "funded"
    milestones[idx]["funded_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.update_one({"_id": proj["_id"]}, {"$set": {"milestones": milestones}})
    await log_event(None, "milestone.funded", actor=user, payload={"project_id": project_id, "mid": mid, "amount": m.get("amount"), "demo_simulated": True})
    return {"ok": True, "status": "funded"}


@router.post("/projects/{project_id}/milestones/{mid}/sim-release")
async def sim_milestone_release(project_id: str, mid: str, user: dict = Depends(require_role("admin"))):
    """Release milestone — final tranche goes to warranty_hold (30 days)."""
    proj, milestones, idx = await _get_project_and_milestone(project_id, mid)
    m = milestones[idx]
    if m.get("status") != "funded":
        raise HTTPException(400, f"Milestone status is '{m.get('status')}', not funded")
    is_final = (idx == len(milestones) - 1)
    now_iso = datetime.now(timezone.utc).isoformat()
    if is_final:
        milestones[idx]["status"] = "warranty_hold"
        milestones[idx]["warranty_started_at"] = now_iso
        milestones[idx]["warranty_until"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    else:
        milestones[idx]["status"] = "released"
        milestones[idx]["released_at"] = now_iso
    # Credit designer/specialist wallet 95%
    designer_id = proj.get("designer_id")
    amount = float(m.get("amount") or 0)
    spec_amount = round(amount * SPECIALIST_SPLIT, 2)
    if designer_id:
        try:
            await db.users.update_one({"_id": ObjectId(designer_id)}, {"$inc": {"wallet_balance": spec_amount}})
        except InvalidId:
            pass
    await db.projects.update_one({"_id": proj["_id"]}, {"$set": {"milestones": milestones}})
    await log_event(None, "milestone.released", actor=user, payload={
        "project_id": project_id, "mid": mid, "amount": amount, "specialist_credited": spec_amount,
        "is_final": is_final, "demo_simulated": True,
    })
    return {"ok": True, "status": milestones[idx]["status"], "specialist_credited": spec_amount, "is_final": is_final}


@router.post("/projects/{project_id}/milestones/{mid}/sim-warranty-fast-forward")
async def sim_warranty_ff(project_id: str, mid: str, user: dict = Depends(require_role("admin"))):
    """Skip the 30-day warranty wait → immediately release final tranche."""
    proj, milestones, idx = await _get_project_and_milestone(project_id, mid)
    m = milestones[idx]
    if m.get("status") != "warranty_hold":
        raise HTTPException(400, f"Milestone status is '{m.get('status')}', not warranty_hold")
    now_iso = datetime.now(timezone.utc).isoformat()
    milestones[idx]["status"] = "warranty_released"
    milestones[idx]["warranty_released_at"] = now_iso
    await db.projects.update_one({"_id": proj["_id"]}, {"$set": {"milestones": milestones}})
    await log_event(None, "milestone.warranty_released", actor=user, payload={
        "project_id": project_id, "mid": mid, "fast_forwarded": True, "demo_simulated": True,
    })
    return {"ok": True, "status": "warranty_released"}


@router.post("/projects/{project_id}/sim-reset")
async def reset_project_milestones(project_id: str, user: dict = Depends(require_role("admin"))):
    """Reset all milestones back to pending_funding."""
    try:
        oid = ObjectId(project_id)
    except InvalidId:
        raise HTTPException(400, "Invalid project id")
    proj = await db.projects.find_one({"_id": oid})
    if not proj:
        raise HTTPException(404, "Project not found")
    milestones = proj.get("milestones") or []
    for m in milestones:
        m["status"] = "pending_funding"
        for k in ("funded_at", "released_at", "warranty_started_at", "warranty_until", "warranty_released_at"):
            m.pop(k, None)
    await db.projects.update_one({"_id": oid}, {"$set": {"milestones": milestones}})
    await log_event(None, "project.milestones_reset", actor=user, payload={"project_id": project_id, "demo_simulated": True})
    return {"ok": True, "milestones_reset": len(milestones)}
