"""Operations Center — inima operațională până la PMF (Directivă COO Operations Center).

Optimizat pentru VIZIBILITATE și EXECUȚIE, nu automatizare:
- pipeline unificat de leads cu stages complete + acțiuni rapide
- Specialist Gap Engine: fiecare cerere fără specialist devine Gap Record (filtrare/alocare/export)
- plăți manuale VERIFIED (cash/transfer/POS/link/stripe manual) legate de Lead + Client + Proiect
- raport COO zilnic + One Win Per Day log
"""
import csv
import io
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from bson import ObjectId
from bson.errors import InvalidId

from db import db
from deps import require_role
from services import notify, log_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/operations", tags=["operations-center"])

PIPELINE_STAGES = [
    "new", "contacted", "qualified", "audit_scheduled", "audit_completed",
    "offer_sent", "waiting_decision", "payment_received", "project_active",
    "completed", "follow_up", "lost",
]
MANUAL_METHODS = ["cash", "bank_transfer", "pos", "payment_link", "manual_stripe", "other"]
OPEN_REQ_EXCLUDE = ["completed", "cancelled", "closed", "rejected"]
UNASSIGNED_Q = {
    "status": {"$nin": OPEN_REQ_EXCLUDE},
    "$or": [{"specialist_id": None}, {"specialist_id": ""}, {"specialist_id": {"$exists": False}}],
}


def _clean_lead(l: dict) -> dict:
    meta = l.get("meta") or {}
    return {
        "id": str(l["_id"]),
        "name": l.get("name") or "",
        "email": l.get("email") or "",
        "phone": l.get("phone") or "",
        "city": l.get("city") or meta.get("city") or meta.get("county") or "",
        "source": l.get("source") or "",
        "stage": l.get("stage") or "new",
        "segment": l.get("segment"),
        "score": l.get("score"),
        "next_action": l.get("next_action") or "",
        "created_at": str(l.get("created_at") or ""),
        "updated_at": str(l.get("updated_at") or ""),
    }


def _clean_gap(g: dict) -> dict:
    return {
        "id": str(g["_id"]),
        "request_id": g.get("request_id"),
        "title": g.get("title") or "",
        "category": g.get("category") or "necategorizat",
        "city": g.get("city") or "",
        "client_name": g.get("client_name") or "",
        "client_id": g.get("client_id") or "",
        "est_lost_revenue_ron": g.get("est_lost_revenue_ron") or 0,
        "status": g.get("status") or "open",
        "detected_at": str(g.get("detected_at") or ""),
        "request_created_at": str(g.get("request_created_at") or ""),
        "assigned_specialist_name": g.get("assigned_specialist_name") or "",
        "assigned_at": str(g.get("assigned_at") or ""),
    }


def _clean_payment(p: dict) -> dict:
    return {
        "id": str(p["_id"]),
        "amount_ron": p.get("amount_ron") or 0,
        "method": p.get("method"),
        "reference": p.get("reference") or "",
        "status": p.get("status"),
        "source": p.get("source") or "manual",
        "lead_id": p.get("lead_id") or "",
        "lead_name": p.get("lead_name") or "",
        "request_id": p.get("request_id") or "",
        "request_title": p.get("request_title") or "",
        "order_id": p.get("order_id") or "",
        "customer_name": p.get("customer_name") or "",
        "customer_email": p.get("customer_email") or "",
        "verified_by": p.get("verified_by") or "",
        "verified_at": str(p.get("verified_at") or ""),
    }


async def _sync_gaps() -> None:
    """Cerere deschisă fără specialist → Gap Record (idempotent). Gaps rezolvate se închid automat."""
    now = datetime.now(timezone.utc).isoformat()
    open_ids = []
    async for req in db.requests.find(UNASSIGNED_Q).sort("created_at", 1).limit(500):
        rid = str(req["_id"])
        open_ids.append(rid)
        await db.specialist_gaps.update_one(
            {"request_id": rid},
            {"$set": {
                "title": req.get("title") or "",
                "category": req.get("category") or "necategorizat",
                "city": req.get("city") or req.get("county") or "",
                "client_name": req.get("client_name") or "",
                "client_id": str(req.get("client_id") or ""),
                "est_lost_revenue_ron": float(req.get("budget_estimate") or 0),
                "request_created_at": str(req.get("created_at") or ""),
                "status": "open",
                "updated_at": now,
            }, "$setOnInsert": {"detected_at": now}},
            upsert=True,
        )
    await db.specialist_gaps.update_many(
        {"status": "open", "request_id": {"$nin": open_ids}},
        {"$set": {"status": "resolved", "resolved_at": now, "resolved_via": "auto_sync"}},
    )


async def _resolve_zone(req: dict) -> str:
    zone = req.get("property_zone") or req.get("zone") or ""
    if not zone and req.get("property_id"):
        try:
            prop = await db.properties.find_one({"_id": ObjectId(req["property_id"])})
            if prop:
                zone = prop.get("zone") or prop.get("city") or ""
        except Exception:  # noqa: BLE001
            zone = ""
    return zone or "default"


@router.get("")
async def operations_center(user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    today_iso = now.isoformat()[:10]

    leads = []
    async for l in db.leads.find({}).sort("created_at", -1).limit(300):
        leads.append(_clean_lead(l))

    ve_orders_pending = []
    async for o in db.verified_estate_orders.find({"status": "pending"}).sort("created_at", -1).limit(30):
        ve_orders_pending.append({
            "id": str(o["_id"]), "session_id": o.get("session_id"), "package": o.get("package"),
            "label": o.get("label", ""), "amount_ron": o.get("amount_ron"),
            "contact_name": o.get("contact_name", ""), "contact_email": o.get("contact_email", ""),
            "contact_phone": o.get("contact_phone", ""), "property_address": o.get("property_address", ""),
            "created_at": str(o.get("created_at", "")), "demo_mode": o.get("demo_mode", False),
        })

    inquiries_new = await db.verified_estate_inquiries.count_documents({"status": "new"})
    external_new = await db.verified_estate_external_requests.count_documents({"status": "new"})

    # Specialist Gap Engine — sincronizare + sumar
    await _sync_gaps()
    gaps = []
    async for g in db.specialist_gaps.aggregate([
        {"$match": {"status": "open"}},
        {"$group": {"_id": "$category", "count": {"$sum": 1},
                    "est_lost_revenue": {"$sum": {"$ifNull": ["$est_lost_revenue_ron", 0]}}}},
        {"$sort": {"count": -1}}, {"$limit": 10},
    ]):
        gaps.append({
            "category": g["_id"] or "necategorizat", "waiting_requests": g["count"],
            "est_lost_revenue_ron": round(g["est_lost_revenue"], 0),
            "recommendation": f"Recrutează specialiști: {g['_id'] or 'necategorizat'}",
        })
    unassigned_total = sum(g["waiting_requests"] for g in gaps)

    # COO daily report
    new_leads_today = sum(1 for l in leads if l["created_at"][:10] == today_iso)
    revenue_pending = round(sum(o["amount_ron"] or 0 for o in ve_orders_pending if not o["demo_mode"]), 2)
    payments_received = await db.verified_estate_orders.count_documents({"status": "paid", "demo_mode": {"$ne": True}})
    mp = await db.manual_payments.aggregate([
        {"$match": {"status": "verified"}},
        {"$group": {"_id": None, "n": {"$sum": 1}, "total": {"$sum": {"$ifNull": ["$amount_ron", 0]}}}},
    ]).to_list(1)
    manual_count = mp[0]["n"] if mp else 0
    manual_total = round(mp[0]["total"], 2) if mp else 0
    stage_new = [l for l in leads if l["stage"] == "new"]
    oldest_waiting = min(stage_new, key=lambda l: l["created_at"], default=None)

    if payments_received == 0 and manual_count == 0 and revenue_pending == 0 and len(stage_new) == 0:
        bottleneck = "Pipeline gol — lipsesc vizitatorii/leads. Distribuie /scorul-casei."
        top_action = "Postează calculatorul Scorul Casei într-un grup Facebook local (15 min)."
    elif len(stage_new) > 0:
        bottleneck = f"{len(stage_new)} leads în stage NEW fără contact."
        top_action = f"Contactează cel mai vechi lead: {oldest_waiting.get('name') if oldest_waiting else '—'}."
    elif revenue_pending > 0:
        bottleneck = f"{revenue_pending:.0f} RON în comenzi neplătite."
        top_action = "Urmărește comenzile pending — oferă plată manuală (transfer/cash)."
    else:
        bottleneck = "Niciun bottleneck operațional intern."
        top_action = "Cere review + referral de la ultimul client servit."

    coo_report = {
        "new_leads_today": new_leads_today,
        "open_leads": len([l for l in leads if l["stage"] not in ("completed", "lost", "won")]),
        "revenue_pending_ron": revenue_pending,
        "payments_received_real": payments_received,
        "manual_payments_count": manual_count,
        "manual_payments_total_ron": manual_total,
        "requests_without_specialist": unassigned_total,
        "top_demand_category": gaps[0]["category"] if gaps else None,
        "oldest_waiting_lead": {"name": oldest_waiting["name"], "created_at": oldest_waiting["created_at"]} if oldest_waiting else None,
        "biggest_bottleneck": bottleneck,
        "top_founder_action": top_action,
    }

    win_today = await db.daily_wins.find_one({"day": today_iso})
    yesterday = (now - timedelta(days=1)).isoformat()[:10]
    win_yesterday = await db.daily_wins.find_one({"day": yesterday})

    return {
        "generated_at": now.isoformat(),
        "stages": PIPELINE_STAGES,
        "manual_methods": MANUAL_METHODS,
        "leads": leads,
        "ve_orders_pending": ve_orders_pending,
        "inquiries_new": inquiries_new,
        "external_requests_new": external_new,
        "gaps": gaps,
        "coo_report": coo_report,
        "one_win": {
            "today": {"text": win_today.get("text"), "day": today_iso} if win_today else None,
            "yesterday": {"text": win_yesterday.get("text"), "day": yesterday} if win_yesterday else None,
        },
    }


@router.patch("/leads/{lead_id}")
async def update_lead(lead_id: str, payload: dict = Body(...), user=Depends(require_role("admin"))):
    try:
        oid = ObjectId(lead_id)
    except InvalidId:
        raise HTTPException(404, "Lead inexistent")
    updates = {}
    stage = payload.get("stage")
    if stage:
        if stage not in PIPELINE_STAGES:
            raise HTTPException(400, f"Stage invalid. Permise: {', '.join(PIPELINE_STAGES)}")
        updates["stage"] = stage
        updates["ops_stage"] = stage
    if payload.get("next_action") is not None:
        updates["next_action"] = str(payload["next_action"])[:300]
    ops = {"$set": {**updates, "updated_at": datetime.now(timezone.utc).isoformat()}}
    note = (payload.get("note") or "").strip()
    if note:
        ops["$push"] = {"ops_notes": {"text": note[:500], "by": str(user.get("id")),
                                      "at": datetime.now(timezone.utc).isoformat()}}
    res = await db.leads.update_one({"_id": oid}, ops)
    if res.matched_count == 0:
        raise HTTPException(404, "Lead inexistent")
    return {"ok": True}


# ============================================================================
# SPECIALIST GAP ENGINE — filtrare, alocare, export
# ============================================================================
@router.get("/gaps")
async def list_gaps(status: str = Query("open"), category: str = Query(None),
                    city: str = Query(None), user=Depends(require_role("admin"))):
    await _sync_gaps()
    q = {}
    if status and status != "all":
        q["status"] = status
    if category:
        q["category"] = category
    if city:
        q["city"] = city
    records = []
    async for g in db.specialist_gaps.find(q).sort("detected_at", -1).limit(200):
        records.append(_clean_gap(g))

    open_gaps = []
    async for g in db.specialist_gaps.find({"status": "open"}).limit(500):
        open_gaps.append(_clean_gap(g))
    by_city, by_category = {}, {}
    for r in open_gaps:
        by_city[r["city"] or "necunoscut"] = by_city.get(r["city"] or "necunoscut", 0) + 1
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1
    summary = {
        "total_open": len(open_gaps),
        "waiting_customers": len({r["client_id"] for r in open_gaps if r["client_id"]}),
        "est_lost_revenue_ron": round(sum(r["est_lost_revenue_ron"] for r in open_gaps), 0),
        "by_city": by_city,
        "by_category": by_category,
    }
    return {"records": records, "summary": summary, "filters": {"status": status, "category": category, "city": city}}


@router.get("/gaps/export")
async def export_gaps(status: str = Query("all"), user=Depends(require_role("admin"))):
    await _sync_gaps()
    q = {} if status == "all" else {"status": status}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["detected_at", "status", "title", "category", "city", "client_name",
                "est_lost_revenue_ron", "request_created_at", "assigned_specialist", "request_id"])
    async for g in db.specialist_gaps.find(q).sort("detected_at", -1).limit(1000):
        r = _clean_gap(g)
        w.writerow([r["detected_at"], r["status"], r["title"], r["category"], r["city"],
                    r["client_name"], r["est_lost_revenue_ron"], r["request_created_at"],
                    r["assigned_specialist_name"], r["request_id"]])
    buf.seek(0)
    fname = f"specialist_gaps_{datetime.now(timezone.utc).isoformat()[:10]}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})


@router.get("/gaps/{gap_id}/candidates")
async def gap_candidates(gap_id: str, user=Depends(require_role("admin"))):
    from routes.matching import find_matching_specialists
    try:
        gap = await db.specialist_gaps.find_one({"_id": ObjectId(gap_id)})
    except InvalidId:
        raise HTTPException(404, "Gap inexistent")
    if not gap:
        raise HTTPException(404, "Gap inexistent")
    req = await db.requests.find_one({"_id": ObjectId(gap["request_id"])})
    if not req:
        raise HTTPException(404, "Cererea nu mai există")
    zone = await _resolve_zone(req)
    matches = await find_matching_specialists(gap.get("category") or "", zone, max_results=5)
    fallback = False
    if not matches:
        fallback = True
        matches = []
        async for s in db.users.find({"role": "specialist", "verified": True}).sort([("rating", -1), ("reviews_count", -1)]).limit(5):
            matches.append({"id": str(s["_id"]), "name": s.get("name"), "rating": s.get("rating"),
                            "reviews_count": s.get("reviews_count", 0), "is_in_zone": False,
                            "specialty": s.get("specialty"), "verified": True})
    return {"candidates": [{
        "id": m["id"], "name": m["name"], "rating": m.get("rating"),
        "reviews_count": m.get("reviews_count"), "in_zone": m.get("is_in_zone"),
        "specialty": m.get("specialty"), "verified": m.get("verified"),
    } for m in matches], "zone": zone, "fallback": fallback}


@router.post("/gaps/{gap_id}/assign")
async def assign_gap(gap_id: str, payload: dict = Body(...), user=Depends(require_role("admin"))):
    specialist_id = payload.get("specialist_id")
    try:
        gap = await db.specialist_gaps.find_one({"_id": ObjectId(gap_id)})
        spec = await db.users.find_one({"_id": ObjectId(specialist_id), "role": "specialist"})
    except (InvalidId, TypeError):
        raise HTTPException(404, "Gap sau specialist inexistent")
    if not gap:
        raise HTTPException(404, "Gap inexistent")
    if gap.get("status") != "open":
        raise HTTPException(400, "Gap-ul nu mai este deschis")
    if not spec:
        raise HTTPException(404, "Specialist inexistent")
    req = await db.requests.find_one({"_id": ObjectId(gap["request_id"])})
    if not req:
        raise HTTPException(404, "Cererea nu mai există")
    if req.get("specialist_id"):
        raise HTTPException(400, "Cererea are deja specialist alocat")

    now = datetime.now(timezone.utc).isoformat()
    await db.requests.update_one({"_id": req["_id"]}, {"$set": {
        "status": "assigned",
        "specialist_id": str(spec["_id"]),
        "specialist_name": spec.get("name"),
        "specialist_specialty": spec.get("specialty") or "",
        "specialist_verified": bool(spec.get("verified")),
        "assigned_at": now,
        "assigned_via": "operations_center",
        "assigned_by": str(user.get("id")),
    }})
    await db.specialist_gaps.update_one({"_id": gap["_id"]}, {"$set": {
        "status": "assigned", "assigned_specialist_id": str(spec["_id"]),
        "assigned_specialist_name": spec.get("name"), "assigned_by": str(user.get("id")),
        "assigned_at": now,
    }})
    try:
        if req.get("client_id"):
            await notify(req["client_id"], f"Specialist alocat: {spec.get('name')}",
                         f"Am alocat un specialist pentru '{req.get('title', '')}'.",
                         type_="assignment", link="/client")
        await notify(str(spec["_id"]), "Cerere alocată din Operations Center",
                     f"Ai primit o cerere nouă: {req.get('title', '')}.",
                     type_="assignment", link="/specialist")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Ops] gap assign notify failed: {e}")
    try:
        await log_event(str(req["_id"]), "request.assigned",
                        actor={"id": str(user.get("id")), "name": user.get("email")},
                        payload={"specialist_id": str(spec["_id"]), "via": "operations_center"})
    except Exception:  # noqa: BLE001
        pass
    logger.info(f"[Ops] Gap {gap_id} assigned to {spec.get('name')} by {user.get('id')}")
    return {"ok": True, "specialist_name": spec.get("name")}


# ============================================================================
# MANUAL PAYMENT MODE — plăți VERIFIED legate de Lead + Client + Proiect
# ============================================================================
@router.get("/manual-payments")
async def list_manual_payments(user=Depends(require_role("admin"))):
    payments = []
    async for p in db.manual_payments.find({}).sort("verified_at", -1).limit(100):
        payments.append(_clean_payment(p))
    total = round(sum(p["amount_ron"] for p in payments if p["status"] == "verified"), 2)
    return {"payments": payments, "totals": {"count": len(payments), "total_ron": total}}


@router.post("/manual-payments")
async def register_generic_payment(payload: dict = Body(...), user=Depends(require_role("admin"))):
    """Plată manuală VERIFIED — legată obligatoriu de client, opțional de lead + proiect."""
    method = payload.get("method")
    if method not in MANUAL_METHODS:
        raise HTTPException(400, f"Metodă invalidă. Permise: {', '.join(MANUAL_METHODS)}")
    try:
        amount = float(payload.get("amount_ron") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "Sumă invalidă")
    if amount <= 0:
        raise HTTPException(400, "Suma trebuie să fie pozitivă")

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "amount_ron": round(amount, 2),
        "method": method,
        "reference": (payload.get("reference") or "").strip()[:200],
        "status": "verified",
        "source": "operations_center",
        "customer_name": (payload.get("customer_name") or "").strip()[:150],
        "customer_email": (payload.get("customer_email") or "").strip().lower()[:150],
        "lead_id": "", "lead_name": "", "request_id": "", "request_title": "", "order_id": "",
        "verified_by": str(user.get("id")),
        "verified_at": now,
        "created_at": now,
    }

    lead_id = payload.get("lead_id")
    if lead_id:
        try:
            lead = await db.leads.find_one({"_id": ObjectId(lead_id)})
        except InvalidId:
            raise HTTPException(404, "Lead inexistent")
        if not lead:
            raise HTTPException(404, "Lead inexistent")
        doc["lead_id"] = str(lead["_id"])
        doc["lead_name"] = lead.get("name") or ""
        if not doc["customer_name"]:
            doc["customer_name"] = lead.get("name") or ""
        if not doc["customer_email"]:
            doc["customer_email"] = lead.get("email") or ""

    request_id = payload.get("request_id")
    if request_id:
        try:
            req = await db.requests.find_one({"_id": ObjectId(request_id)})
        except InvalidId:
            raise HTTPException(404, "Proiect inexistent")
        if not req:
            raise HTTPException(404, "Proiect inexistent")
        doc["request_id"] = str(req["_id"])
        doc["request_title"] = req.get("title") or ""

    if not doc["customer_name"]:
        raise HTTPException(400, "Numele clientului este obligatoriu (sau alege un lead)")

    res = await db.manual_payments.insert_one(doc)

    if doc["lead_id"]:
        await db.leads.update_one({"_id": ObjectId(doc["lead_id"])}, {
            "$set": {"stage": "payment_received", "ops_stage": "payment_received", "updated_at": now},
            "$inc": {"revenue_generated": doc["amount_ron"]},
        })
    logger.info(f"[Ops] Manual payment VERIFIED: {doc['amount_ron']} RON {method} by={user.get('id')}")
    return {"ok": True, "payment_id": str(res.inserted_id)}


@router.post("/manual-payment")
async def register_manual_payment(payload: dict = Body(...), user=Depends(require_role("admin"))):
    """Plată manuală VERIFIED pentru comenzi Imobile Verificate — până la Stripe LIVE."""
    order_id = payload.get("order_id")
    method = payload.get("method")
    reference = (payload.get("reference") or "").strip()[:200]
    if method not in MANUAL_METHODS:
        raise HTTPException(400, f"Metodă invalidă. Permise: {', '.join(MANUAL_METHODS)}")
    try:
        oid = ObjectId(order_id)
    except (InvalidId, TypeError):
        raise HTTPException(404, "Comandă inexistentă")
    order = await db.verified_estate_orders.find_one({"_id": oid})
    if not order:
        raise HTTPException(404, "Comandă inexistentă")
    if order.get("status") == "paid":
        raise HTTPException(400, "Comanda este deja plătită")

    now = datetime.now(timezone.utc).isoformat()
    await db.verified_estate_orders.update_one(
        {"_id": oid},
        {"$set": {"payment_method": method, "payment_reference": reference,
                  "manual_payment": True, "manual_verified": True,
                  "verified_by": str(user.get("id")), "demo_mode": False}},
    )
    from routes.verified_estate import mark_order_paid
    await mark_order_paid(order.get("session_id"))
    await db.manual_payments.insert_one({
        "amount_ron": float(order.get("amount_ron") or 0),
        "method": method, "reference": reference, "status": "verified",
        "source": "verified_estate_order", "order_id": str(oid),
        "lead_id": "", "lead_name": "", "request_id": "",
        "request_title": order.get("label") or order.get("package") or "",
        "customer_name": order.get("contact_name") or "",
        "customer_email": order.get("contact_email") or "",
        "verified_by": str(user.get("id")), "verified_at": now, "created_at": now,
    })
    logger.info(f"[Ops] Manual payment VERIFIED: order={order_id} method={method} by={user.get('id')}")
    return {"ok": True, "order_id": order_id, "method": method}


@router.post("/win")
async def set_daily_win(payload: dict = Body(...), user=Depends(require_role("admin"))):
    """One Win Per Day — înregistrează victoria zilei."""
    text = (payload.get("text") or "").strip()[:300]
    if not text:
        raise HTTPException(400, "Textul victoriei este obligatoriu")
    day = datetime.now(timezone.utc).isoformat()[:10]
    await db.daily_wins.update_one(
        {"day": day},
        {"$set": {"text": text, "by": str(user.get("id")), "at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "day": day}
