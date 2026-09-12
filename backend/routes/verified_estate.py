"""PropManage — Verified Estate Listings (Imobile Verificate).

Isolated module for premium real-estate listings where each property
MUST have a completed audit + published Digital Twin before becoming
visible to buyers.

Collections used (all NEW, no impact on existing):
  - verified_estate_listings
  - verified_estate_inquiries
  - verified_estate_external_requests

4 Gates enforced at API level:
  1. Listing creation requires audit_report_id (completed)
  2. Listing publish requires linked digital_twin (published)
  3. Listing publish requires >= 90% recommendations accepted by owner
  4. Final status="published" requires admin approval

Feature flag: FEATURE_VERIFIED_ESTATE (default: true)
"""
from datetime import datetime, timezone
from typing import Optional, List
import os
import uuid
import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from core_utils import serialize_doc
from email_service import send_email

logger = logging.getLogger("propmanage.verified_estate")

FEATURE_FLAG = os.environ.get("FEATURE_VERIFIED_ESTATE", "true").lower() == "true"

# Pricing (RON) — admin-configurable via env vars
PRICE_AUDIT_RON = float(os.environ.get("VE_PRICE_AUDIT_RON", "350"))
PRICE_TWIN_RON = float(os.environ.get("VE_PRICE_TWIN_RON", "950"))
COMMISSION_PCT = float(os.environ.get("VE_COMMISSION_PCT", "2.5"))

router = APIRouter(prefix="/api/verified-estate", tags=["verified-estate"])

ADMIN_NOTIFY_EMAIL = os.environ.get("ADMIN_NOTIFY_EMAIL") or os.environ.get("SUPPORT_CONTACT_EMAIL") or "contact@propmanage.ro"


async def _notify_admin(subject: str, body_html: str):
    """Fire-and-forget admin notification."""
    try:
        import asyncio
        asyncio.create_task(send_email(ADMIN_NOTIFY_EMAIL, subject, body_html))
    except Exception as e:
        logger.warning(f"Admin notify failed: {e}")


async def _create_draft_listing_from_order(order: dict):
    """After a successful paid order, auto-create a draft listing for admin review."""
    pkg = order.get("package", "")
    has_audit = pkg in ("audit", "bundle")
    has_twin = pkg in ("twin", "bundle")
    now = datetime.now(timezone.utc)
    addr = order.get("property_address", "")
    title_prefix = "Imobil în pregătire"
    listing_doc = {
        "_id": ObjectId(),
        "title": f"{title_prefix} · {addr[:60]}",
        "city": (addr.split(",")[-1].strip()[:80]) or "—",
        "address": addr,
        "price_ron": 0.0,
        "rooms": 0,
        "surface_sqm": 0.0,
        "floor": "",
        "year_built": None,
        "description": f"Listing creat automat după plata pachetului '{pkg}'. "
                       f"Așteaptă programare audit/twin și completare detalii de către agentul atribuit.\n\n"
                       f"Contact proprietar: {order.get('contact_name', '')} <{order.get('contact_email', '')}> {order.get('contact_phone', '')}\n"
                       f"Notițe: {order.get('notes', '')}",
        "transaction_type": "sale",
        "digital_twin_id": None,
        "audit_report_id": None,
        "audit_report_url": None,
        "cover_image_url": None,
        "gallery": [],
        "recommendations_total": 0,
        "recommendations_accepted": 0,
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "published_at": None,
        "view_count": 0,
        "inquiry_count": 0,
        "source_order_id": str(order.get("_id")),
        "owner_email": order.get("contact_email"),
        "owner_name": order.get("contact_name"),
        "owner_phone": order.get("contact_phone", ""),
        "pending_services": {"audit": has_audit, "twin": has_twin},
        "gates_status": _evaluate_gates({"audit_report_id": None, "digital_twin_id": None, "recommendations_total": 0, "recommendations_accepted": 0}),
    }
    await db.verified_estate_listings.insert_one(listing_doc)
    return str(listing_doc["_id"])


async def mark_order_paid(session_id: str) -> bool:
    """Idempotent: mark a VE order paid (Stripe webhook or status poll).
    Creates draft listing + notifies admin + emails buyer. Returns True if transitioned."""
    order = await db.verified_estate_orders.find_one({"session_id": session_id})
    if not order or order.get("status") == "paid":
        return False
    now = datetime.now(timezone.utc)
    await db.verified_estate_orders.update_one(
        {"_id": order["_id"]}, {"$set": {"status": "paid", "paid_at": now}}
    )
    order["status"] = "paid"
    try:
        draft_id = await _create_draft_listing_from_order(order)
        await db.verified_estate_orders.update_one({"_id": order["_id"]}, {"$set": {"draft_listing_id": draft_id}})
    except Exception as e:
        logger.warning(f"Auto-create draft failed: {e}")
    label = order.get("label", order.get("package", ""))
    amount = float(order.get("amount_ron") or 0)
    await _notify_admin(
        f"[Imobile Verificate] 💰 PLATĂ CONFIRMATĂ · {order.get('package')} · {amount:.0f} RON",
        f"""<h2>Plată Stripe confirmată</h2>
        <p><strong>Pachet:</strong> {label}</p>
        <p><strong>Sumă:</strong> {amount:.0f} RON</p>
        <p><strong>Client:</strong> {order.get('contact_name', '')} · {order.get('contact_email', '')} · {order.get('contact_phone') or '—'}</p>
        <p><strong>Adresă proprietate:</strong> {order.get('property_address', '')}</p>
        <p><em>Listing draft creat automat în Admin Kanban. Programează auditul în 24h.</em></p>"""
    )
    try:
        import asyncio
        asyncio.create_task(send_email(
            order.get("contact_email"),
            f"Confirmare plată · {label} · {amount:.0f} RON",
            f"""<h2>Mulțumim, {order.get('contact_name', '')}!</h2>
            <p>Plata pentru <strong>{label}</strong> a fost confirmată.</p>
            <p>Echipa noastră te va contacta în maxim 24h pentru a programa auditul la <strong>{order.get('property_address', '')}</strong>.</p>
            <p>— Echipa PropManage Imobile Verificate</p>"""
        ))
    except Exception:
        pass
    logger.info(f"VE order {order['_id']} marked paid (session {session_id})")
    return True


def _ensure_enabled():
    if not FEATURE_FLAG:
        raise HTTPException(503, "Verified Estate module is currently disabled")


# ----------------- Schemas -----------------

class ListingCreate(BaseModel):
    title: str = Field(..., min_length=4, max_length=180)
    city: str = Field(..., min_length=2, max_length=80)
    address: Optional[str] = ""
    price_ron: float = Field(..., gt=0)
    rooms: int = Field(..., ge=0, le=20)
    surface_sqm: float = Field(..., gt=0)
    floor: Optional[str] = ""
    year_built: Optional[int] = None
    description: str = Field("", max_length=4000)
    transaction_type: str = Field("sale", pattern="^(sale|rent)$")
    # Geo coordinates (optional)
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Twin & audit linkage (mandatory for publish)
    digital_twin_id: Optional[str] = None
    audit_report_id: Optional[str] = None
    audit_report_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    gallery: List[str] = Field(default_factory=list)
    # Recommendations percentage (filled by audit flow)
    recommendations_total: int = 0
    recommendations_accepted: int = 0


class ListingPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_ron: Optional[float] = None
    cover_image_url: Optional[str] = None
    gallery: Optional[List[str]] = None
    digital_twin_id: Optional[str] = None
    audit_report_id: Optional[str] = None
    audit_report_url: Optional[str] = None
    recommendations_total: Optional[int] = None
    recommendations_accepted: Optional[int] = None


class InquiryCreate(BaseModel):
    listing_id: str
    name: str = Field(..., min_length=2, max_length=120)
    email: str = Field(..., min_length=4, max_length=180)
    phone: Optional[str] = ""
    message: str = Field("", max_length=2000)
    intent: str = Field("viewing", pattern="^(viewing|buy|info)$")


class ExternalAuditCreate(BaseModel):
    """Buyer found a property elsewhere (Imobiliare.ro, Storia, etc.)
    and wants PropManage to audit + create Twin for it."""
    external_listing_url: str = Field(..., min_length=8, max_length=500)
    property_address: str = Field(..., min_length=4, max_length=300)
    contact_name: str = Field(..., min_length=2, max_length=120)
    contact_email: str = Field(..., min_length=4, max_length=180)
    contact_phone: Optional[str] = ""
    notes: Optional[str] = ""
    budget_ron: Optional[float] = None


# ----------------- Helpers -----------------

def _serialize_listing(doc: dict) -> dict:
    """Serialize a Mongo listing doc for API responses."""
    out = serialize_doc(doc) if doc else None
    if not out:
        return out
    # Compute helpful derived fields
    total = out.get("recommendations_total") or 0
    accepted = out.get("recommendations_accepted") or 0
    pct = round((accepted / total * 100), 1) if total > 0 else 0.0
    out["recommendations_pct"] = pct
    # Trust score: A+ if 100% + has twin + has audit; A if >=95%; B if >=90%; C otherwise
    has_twin = bool(out.get("digital_twin_id"))
    has_audit = bool(out.get("audit_report_id"))
    if pct >= 100 and has_twin and has_audit:
        out["trust_score"] = "A+"
    elif pct >= 95 and has_twin and has_audit:
        out["trust_score"] = "A"
    elif pct >= 90 and has_twin and has_audit:
        out["trust_score"] = "B"
    else:
        out["trust_score"] = "C"
    return out


def _evaluate_gates(payload: dict) -> dict:
    """Return a dict with each Gate status (pass/fail + reason)."""
    audit_id = payload.get("audit_report_id")
    twin_id = payload.get("digital_twin_id")
    total = payload.get("recommendations_total") or 0
    accepted = payload.get("recommendations_accepted") or 0
    pct = (accepted / total * 100) if total > 0 else 0.0
    return {
        "gate_1_audit": {"ok": bool(audit_id), "reason": "Audit report ID missing" if not audit_id else ""},
        "gate_2_twin": {"ok": bool(twin_id), "reason": "Digital Twin ID missing" if not twin_id else ""},
        "gate_3_recommendations": {
            "ok": pct >= 90.0,
            "reason": f"Only {pct:.1f}% recommendations accepted (need >= 90%)" if pct < 90.0 else "",
            "pct": pct,
        },
    }


# ----------------- Public Endpoints -----------------

@router.get("/listings")
async def list_public_listings(
    city: Optional[str] = None,
    transaction_type: Optional[str] = Query(None, pattern="^(sale|rent)$"),
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    rooms: Optional[int] = None,
    limit: int = Query(24, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """Public endpoint — only returns published listings (passed all gates + admin approval)."""
    _ensure_enabled()
    query: dict = {"status": "published"}
    if city:
        query["city"] = {"$regex": f"^{city}", "$options": "i"}
    if transaction_type:
        query["transaction_type"] = transaction_type
    if rooms is not None:
        query["rooms"] = rooms
    if price_min is not None or price_max is not None:
        price_q: dict = {}
        if price_min is not None:
            price_q["$gte"] = price_min
        if price_max is not None:
            price_q["$lte"] = price_max
        query["price_ron"] = price_q

    cursor = db.verified_estate_listings.find(query).sort("published_at", -1).skip(skip).limit(limit)
    items = [_serialize_listing(d) async for d in cursor]
    total = await db.verified_estate_listings.count_documents(query)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    """Public detail endpoint for a single published listing."""
    _ensure_enabled()
    try:
        doc = await db.verified_estate_listings.find_one({"_id": ObjectId(listing_id), "status": "published"})
    except InvalidId:
        raise HTTPException(404, "Listing not found")
    if not doc:
        raise HTTPException(404, "Listing not found")
    return _serialize_listing(doc)


@router.post("/inquiries")
async def create_inquiry(body: InquiryCreate):
    """Public — a buyer expresses interest (viewing / buy / info)."""
    _ensure_enabled()
    try:
        listing = await db.verified_estate_listings.find_one({"_id": ObjectId(body.listing_id), "status": "published"})
    except InvalidId:
        raise HTTPException(404, "Listing not found")
    if not listing:
        raise HTTPException(404, "Listing not found")
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "listing_id": str(listing["_id"]),
        "listing_title": listing.get("title", ""),
        "name": body.name.strip(),
        "email": body.email.strip().lower(),
        "phone": body.phone or "",
        "message": body.message,
        "intent": body.intent,
        "status": "new",
        "created_at": now,
    }
    await db.verified_estate_inquiries.insert_one(doc)
    # increment inquiry counter for admin analytics
    await db.verified_estate_listings.update_one(
        {"_id": listing["_id"]},
        {"$inc": {"inquiry_count": 1}},
    )
    # Notify admin
    intent_label = {"viewing": "Programare vizionare", "buy": "Intenție de cumpărare", "info": "Cerere informații"}.get(body.intent, body.intent)
    await _notify_admin(
        f"[Imobile Verificate] {intent_label} · {body.name}",
        f"""<h2>Cerere nouă pe Imobile Verificate</h2>
        <p><strong>Tip:</strong> {intent_label}</p>
        <p><strong>Imobil:</strong> {listing.get('title', '')}</p>
        <p><strong>Nume:</strong> {body.name}<br/>
        <strong>Email:</strong> {body.email}<br/>
        <strong>Telefon:</strong> {body.phone or '—'}</p>
        <p><strong>Mesaj:</strong></p>
        <blockquote>{body.message or '(fără mesaj)'}</blockquote>"""
    )
    return {"ok": True, "inquiry_id": str(doc["_id"])}


@router.post("/external-audit-request")
async def create_external_audit_request(body: ExternalAuditCreate):
    """Public — buyer found property elsewhere, wants PropManage to audit it.
    Revenue stream extra (Traseu C)."""
    _ensure_enabled()
    now = datetime.now(timezone.utc)
    doc = {
        "_id": ObjectId(),
        "external_listing_url": body.external_listing_url.strip(),
        "property_address": body.property_address.strip(),
        "contact_name": body.contact_name.strip(),
        "contact_email": body.contact_email.strip().lower(),
        "contact_phone": body.contact_phone or "",
        "notes": body.notes or "",
        "budget_ron": body.budget_ron,
        "status": "new",
        "created_at": now,
    }
    await db.verified_estate_external_requests.insert_one(doc)
    await _notify_admin(
        f"[Imobile Verificate] Cerere audit EXTERN · {body.contact_name}",
        f"""<h2>Cerere audit pentru imobil extern</h2>
        <p><strong>URL imobil:</strong> <a href="{body.external_listing_url}">{body.external_listing_url}</a></p>
        <p><strong>Adresă:</strong> {body.property_address}</p>
        <p><strong>Contact:</strong> {body.contact_name} · {body.contact_email} · {body.contact_phone or '—'}</p>
        <p><strong>Buget:</strong> {body.budget_ron or '—'} RON</p>
        <p><strong>Notițe:</strong></p>
        <blockquote>{body.notes or '(fără notițe)'}</blockquote>"""
    )
    return {"ok": True, "request_id": str(doc["_id"])}


# ----------------- Admin / Operator Endpoints -----------------

@router.post("/admin/listings")
async def admin_create_listing(body: ListingCreate, user: dict = Depends(require_role("admin", "operator"))):
    """Admin/Operator creates a listing. Starts in `draft` status.
    Gates are evaluated but listing remains draft until admin publishes."""
    _ensure_enabled()
    now = datetime.now(timezone.utc)
    payload = body.model_dump()
    gates = _evaluate_gates(payload)
    payload.update({
        "_id": ObjectId(),
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "created_by": str(user.get("id")),
        "gates_status": gates,
        "published_at": None,
        "view_count": 0,
        "inquiry_count": 0,
    })
    await db.verified_estate_listings.insert_one(payload)
    return _serialize_listing(payload)


@router.get("/admin/listings")
async def admin_list_listings(
    status: Optional[str] = Query(None, pattern="^(draft|pending_review|published|sold|archived|rejected)$"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user: dict = Depends(require_role("admin", "operator")),
):
    """Admin list — shows ALL listings regardless of status."""
    _ensure_enabled()
    query: dict = {}
    if status:
        query["status"] = status
    cursor = db.verified_estate_listings.find(query).sort("updated_at", -1).skip(skip).limit(limit)
    items = [_serialize_listing(d) async for d in cursor]
    total = await db.verified_estate_listings.count_documents(query)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.patch("/admin/listings/{listing_id}")
async def admin_patch_listing(
    listing_id: str,
    body: ListingPatch,
    user: dict = Depends(require_role("admin", "operator")),
):
    _ensure_enabled()
    try:
        oid = ObjectId(listing_id)
    except InvalidId:
        raise HTTPException(404, "Listing not found")
    existing = await db.verified_estate_listings.find_one({"_id": oid})
    if not existing:
        raise HTTPException(404, "Listing not found")
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        return _serialize_listing(existing)
    merged = {**existing, **updates}
    updates["gates_status"] = _evaluate_gates(merged)
    updates["updated_at"] = datetime.now(timezone.utc)
    await db.verified_estate_listings.update_one({"_id": oid}, {"$set": updates})
    doc = await db.verified_estate_listings.find_one({"_id": oid})
    return _serialize_listing(doc)


@router.post("/admin/listings/{listing_id}/publish")
async def admin_publish_listing(listing_id: str, user: dict = Depends(require_role("admin", "operator"))):
    """Admin publishes a listing. Enforces all 4 gates strictly."""
    _ensure_enabled()
    try:
        oid = ObjectId(listing_id)
    except InvalidId:
        raise HTTPException(404, "Listing not found")
    doc = await db.verified_estate_listings.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Listing not found")
    gates = _evaluate_gates(doc)
    failed = [g for g, info in gates.items() if not info.get("ok")]
    if failed:
        raise HTTPException(400, {
            "error": "Listing does not meet Verified Estate quality gates",
            "gates_status": gates,
            "failed": failed,
        })
    now = datetime.now(timezone.utc)
    await db.verified_estate_listings.update_one(
        {"_id": oid},
        {"$set": {
            "status": "published",
            "published_at": now,
            "updated_at": now,
            "published_by": str(user.get("id")),
            "gates_status": gates,
        }},
    )
    refreshed = await db.verified_estate_listings.find_one({"_id": oid})
    return _serialize_listing(refreshed)


@router.post("/admin/listings/{listing_id}/archive")
async def admin_archive_listing(listing_id: str, user: dict = Depends(require_role("admin", "operator"))):
    _ensure_enabled()
    try:
        oid = ObjectId(listing_id)
    except InvalidId:
        raise HTTPException(404, "Listing not found")
    res = await db.verified_estate_listings.update_one(
        {"_id": oid},
        {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc)}},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Listing not found")
    return {"ok": True}


class MarkSoldRequest(BaseModel):
    sale_price_ron: float = Field(..., gt=0)
    buyer_name: Optional[str] = ""
    buyer_email: Optional[str] = ""
    notes: Optional[str] = ""


@router.post("/admin/listings/{listing_id}/mark-sold")
async def admin_mark_sold(listing_id: str, body: MarkSoldRequest, user: dict = Depends(require_role("admin", "operator"))):
    """Close a sale: computes the 2.5% commission (twin cost deducted per pricing policy),
    records the sale in `verified_estate_sales` and marks the listing as sold."""
    _ensure_enabled()
    try:
        oid = ObjectId(listing_id)
    except InvalidId:
        raise HTTPException(404, "Listing not found")
    listing = await db.verified_estate_listings.find_one({"_id": oid})
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing.get("status") != "published":
        raise HTTPException(400, "Doar listingurile publicate pot fi marcate ca vândute")

    comm_pct = COMMISSION_PCT
    twin_price = PRICE_TWIN_RON
    try:
        s = await db.app_settings.find_one({"_id": "app_settings"})
        if s and s.get("pricing"):
            comm_pct = float(s["pricing"].get("commission_pct", comm_pct))
            twin_price = float(s["pricing"].get("twin_ron", twin_price))
    except Exception:
        pass

    commission_gross = round(body.sale_price_ron * comm_pct / 100.0, 2)
    twin_deduction = 0.0
    src_order_id = listing.get("source_order_id")
    if src_order_id:
        try:
            src = await db.verified_estate_orders.find_one({"_id": ObjectId(src_order_id)})
            if src and src.get("status") == "paid" and src.get("package") in ("twin", "bundle"):
                twin_deduction = twin_price
        except Exception:
            pass
    commission_net = round(max(0.0, commission_gross - twin_deduction), 2)

    now = datetime.now(timezone.utc)
    sale_doc = {
        "_id": ObjectId(),
        "listing_id": str(oid),
        "listing_title": listing.get("title", ""),
        "sale_price_ron": body.sale_price_ron,
        "commission_pct": comm_pct,
        "commission_gross_ron": commission_gross,
        "twin_deduction_ron": twin_deduction,
        "commission_net_ron": commission_net,
        "buyer_name": (body.buyer_name or "").strip(),
        "buyer_email": (body.buyer_email or "").strip().lower(),
        "notes": body.notes or "",
        "sold_by": str(user.get("id")),
        "created_at": now,
    }
    await db.verified_estate_sales.insert_one(sale_doc)
    await db.verified_estate_listings.update_one(
        {"_id": oid},
        {"$set": {
            "status": "sold", "sold_at": now, "updated_at": now,
            "sale_price_ron": body.sale_price_ron, "sale_id": str(sale_doc["_id"]),
            "commission_net_ron": commission_net,
        }},
    )
    await _notify_admin(
        f"[Imobile Verificate] 🏆 VÂNZARE ÎNCHISĂ · {body.sale_price_ron:,.0f} RON · comision net {commission_net:,.0f} RON",
        f"""<h2>Vânzare finalizată</h2>
        <p><strong>Imobil:</strong> {listing.get('title', '')}</p>
        <p><strong>Preț vânzare:</strong> {body.sale_price_ron:,.0f} RON</p>
        <p><strong>Comision ({comm_pct}%):</strong> {commission_gross:,.0f} RON</p>
        <p><strong>Deducere Digital Twin:</strong> {twin_deduction:,.0f} RON</p>
        <p><strong>Comision NET:</strong> {commission_net:,.0f} RON</p>
        <p><strong>Cumpărător:</strong> {body.buyer_name or '—'} · {body.buyer_email or '—'}</p>"""
    )
    return {"ok": True, "sale": serialize_doc(sale_doc)}


@router.get("/admin/sales")
async def admin_list_sales(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user: dict = Depends(require_role("admin", "operator")),
):
    _ensure_enabled()
    cursor = db.verified_estate_sales.find({}).sort("created_at", -1).skip(skip).limit(limit)
    items = [serialize_doc(d) async for d in cursor]
    total = await db.verified_estate_sales.count_documents({})
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/admin/inquiries")
async def admin_list_inquiries(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user: dict = Depends(require_role("admin", "operator")),
):
    _ensure_enabled()
    cursor = db.verified_estate_inquiries.find({}).sort("created_at", -1).skip(skip).limit(limit)
    items = [serialize_doc(d) async for d in cursor]
    total = await db.verified_estate_inquiries.count_documents({})
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/admin/external-requests")
async def admin_list_external_requests(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user: dict = Depends(require_role("admin", "operator")),
):
    _ensure_enabled()
    cursor = db.verified_estate_external_requests.find({}).sort("created_at", -1).skip(skip).limit(limit)
    items = [serialize_doc(d) async for d in cursor]
    total = await db.verified_estate_external_requests.count_documents({})
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_role("admin", "operator"))):
    """Quick dashboard stats for Verified Estate admin panel."""
    _ensure_enabled()
    total_listings = await db.verified_estate_listings.count_documents({})
    published = await db.verified_estate_listings.count_documents({"status": "published"})
    drafts = await db.verified_estate_listings.count_documents({"status": "draft"})
    pending = await db.verified_estate_listings.count_documents({"status": "pending_review"})
    inquiries_open = await db.verified_estate_inquiries.count_documents({"status": "new"})
    external_open = await db.verified_estate_external_requests.count_documents({"status": "new"})
    sold = await db.verified_estate_listings.count_documents({"status": "sold"})

    async def _sum(coll, query, field):
        pipe = [{"$match": query}, {"$group": {"_id": None, "t": {"$sum": f"${field}"}}}]
        rows = await db[coll].aggregate(pipe).to_list(1)
        return round(rows[0]["t"], 2) if rows else 0.0

    commission_net_total = await _sum("verified_estate_sales", {}, "commission_net_ron")
    revenue_real = await _sum("verified_estate_orders", {"status": "paid", "demo_mode": {"$ne": True}}, "amount_ron")
    revenue_demo = await _sum("verified_estate_orders", {"status": "paid", "demo_mode": True}, "amount_ron")
    return {
        "listings_total": total_listings,
        "listings_published": published,
        "listings_draft": drafts,
        "listings_pending_review": pending,
        "listings_sold": sold,
        "commission_net_total_ron": commission_net_total,
        "orders_revenue_real_ron": revenue_real,
        "orders_revenue_demo_ron": revenue_demo,
        "inquiries_new": inquiries_open,
        "external_requests_new": external_open,
        "feature_enabled": FEATURE_FLAG,
    }


# ----------------- Pricing / Stripe Checkout (ETAPA 2) -----------------

@router.post("/admin/run-newsletter-now")
async def admin_run_newsletter_now(user: dict = Depends(require_role("admin", "operator"))):
    """Manual trigger for weekly newsletter (for admin testing)."""
    _ensure_enabled()
    from email_sequences import run_weekly_newsletter
    sent = await run_weekly_newsletter()
    return {"ok": True, "emails_sent": sent}


@router.post("/admin/run-drip-now")
async def admin_run_drip_now(user: dict = Depends(require_role("admin", "operator"))):
    """Manual trigger for drip reminder job."""
    _ensure_enabled()
    from email_sequences import run_drip_reminder_for_pending_orders
    sent = await run_drip_reminder_for_pending_orders()
    return {"ok": True, "reminders_sent": sent}


@router.get("/pricing")
async def get_pricing():
    """Public pricing for audit + Twin + commission.
    Reads from app_settings doc if present, falls back to env vars."""
    _ensure_enabled()
    audit = PRICE_AUDIT_RON
    twin = PRICE_TWIN_RON
    comm = COMMISSION_PCT
    try:
        s = await db.app_settings.find_one({"_id": "app_settings"})
        if s and s.get("pricing"):
            p = s["pricing"]
            audit = float(p.get("audit_ron", audit))
            twin = float(p.get("twin_ron", twin))
            comm = float(p.get("commission_pct", comm))
    except Exception:
        pass
    return {
        "audit_ron": audit,
        "twin_ron": twin,
        "commission_pct": comm,
        "currency": "ron",
        "bundle_ron": audit + twin,
        "notes": "La finalizarea vânzării, costul Digital Twin se scade din comision.",
    }


class CheckoutRequest(BaseModel):
    package: str = Field(..., pattern="^(audit|twin|bundle)$")
    contact_name: str = Field(..., min_length=2, max_length=120)
    contact_email: str = Field(..., min_length=4, max_length=180)
    contact_phone: Optional[str] = ""
    property_address: str = Field(..., min_length=4, max_length=300)
    notes: Optional[str] = ""


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest, request: Request):
    """Create Stripe Checkout session for audit/twin/bundle.
    Falls back to DEMO mode if Stripe key is the emergent placeholder.
    Stores order intent in `verified_estate_orders` collection."""
    _ensure_enabled()

    # lazy imports to keep module isolated
    import stripe as _stripe
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    STRIPE_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
    demo_mode = (STRIPE_KEY == "sk_test_emergent") or not STRIPE_KEY.startswith(("sk_test_", "sk_live_"))
    _stripe.api_key = STRIPE_KEY

    if body.package == "audit":
        amount = PRICE_AUDIT_RON
        label = "Audit complet imobil"
    elif body.package == "twin":
        amount = PRICE_TWIN_RON
        label = "Digital Twin creation"
    else:
        amount = PRICE_AUDIT_RON + PRICE_TWIN_RON
        label = "Bundle: Audit + Digital Twin"
    # Override with settings if available
    try:
        s = await db.app_settings.find_one({"_id": "app_settings"})
        if s and s.get("pricing"):
            p = s["pricing"]
            if body.package == "audit":
                amount = float(p.get("audit_ron", amount))
            elif body.package == "twin":
                amount = float(p.get("twin_ron", amount))
            else:
                amount = float(p.get("audit_ron", PRICE_AUDIT_RON)) + float(p.get("twin_ron", PRICE_TWIN_RON))
    except Exception:
        pass

    origin = (
        os.environ.get("FRONTEND_PUBLIC_URL")
        or request.headers.get("origin")
        or request.headers.get("referer", "").rstrip("/")
    )
    if not origin:
        raise HTTPException(400, "Missing origin header")

    now = datetime.now(timezone.utc)
    order_id = str(ObjectId())

    base_order = {
        "_id": ObjectId(order_id),
        "package": body.package,
        "amount_ron": amount,
        "label": label,
        "contact_name": body.contact_name,
        "contact_email": body.contact_email.lower().strip(),
        "contact_phone": body.contact_phone or "",
        "property_address": body.property_address,
        "notes": body.notes or "",
        "status": "pending",
        "demo_mode": demo_mode,
        "created_at": now,
    }

    if demo_mode:
        # Simulate immediate success
        fake_session = f"cs_demo_ve_{uuid.uuid4().hex[:16]}"
        base_order.update({
            "session_id": fake_session,
            "status": "paid",
            "paid_at": now,
        })
        await db.verified_estate_orders.insert_one(base_order)
        # Auto-create draft listing for admin moderation
        try:
            draft_id = await _create_draft_listing_from_order(base_order)
            await db.verified_estate_orders.update_one({"_id": base_order["_id"]}, {"$set": {"draft_listing_id": draft_id}})
        except Exception as e:
            logger.warning(f"Auto-create draft failed: {e}")
        # Notify admin + send confirmation to buyer
        await _notify_admin(
            f"[Imobile Verificate] Plată DEMO · {body.package} · {amount} RON",
            f"""<h2>Comandă nouă (mod DEMO)</h2>
            <p><strong>Pachet:</strong> {label}</p>
            <p><strong>Sumă:</strong> {amount:.0f} RON</p>
            <p><strong>Client:</strong> {body.contact_name} · {body.contact_email} · {body.contact_phone or '—'}</p>
            <p><strong>Adresă proprietate:</strong> {body.property_address}</p>
            <p><strong>Notițe:</strong> {body.notes or '—'}</p>
            <p><em>Listing draft creat automat în Admin Kanban.</em></p>"""
        )
        try:
            import asyncio
            asyncio.create_task(send_email(
                body.contact_email,
                f"Confirmare comandă · {label} · {amount:.0f} RON",
                f"""<h2>Mulțumim, {body.contact_name}!</h2>
                <p>Am primit comanda ta pentru <strong>{label}</strong> (mod DEMO — fără tranzacție reală).</p>
                <p>Echipa noastră te va contacta în maxim 24h pentru a programa auditul la <strong>{body.property_address}</strong>.</p>
                <p>— Echipa PropManage Imobile Verificate</p>"""
            ))
        except Exception:
            pass
        return {
            "checkout_url": f"{origin}/imobile-verificate/sell?paid=1&session_id={fake_session}&demo=1",
            "session_id": fake_session,
            "demo_mode": True,
            "order_id": order_id,
        }

    # REAL Stripe
    webhook_url = f"{origin}/api/webhook/stripe"
    checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url=webhook_url)
    success_url = f"{origin}/imobile-verificate/sell?paid=1&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/imobile-verificate/sell?cancelled=1"
    checkout_req = CheckoutSessionRequest(
        amount=amount,
        currency="ron",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "verified_estate_order_id": order_id,
            "package": body.package,
            "contact_email": body.contact_email,
        },
    )
    try:
        session = await checkout.create_checkout_session(checkout_req)
    except Exception as e:
        raise HTTPException(500, f"Stripe error: {e}")

    base_order.update({"session_id": session.session_id})
    await db.verified_estate_orders.insert_one(base_order)
    return {"checkout_url": session.url, "session_id": session.session_id, "order_id": order_id}


@router.get("/checkout/status/{session_id}")
async def get_checkout_status(session_id: str):
    """Polled by frontend after redirect to confirm payment.
    For REAL Stripe orders still pending, verifies status directly with Stripe
    (robust even if webhook is missed) and marks the order paid."""
    _ensure_enabled()
    order = await db.verified_estate_orders.find_one({"session_id": session_id})
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("status") == "pending" and not order.get("demo_mode"):
        try:
            from emergentintegrations.payments.stripe.checkout import StripeCheckout
            STRIPE_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")
            checkout = StripeCheckout(api_key=STRIPE_KEY, webhook_url="")
            st = await checkout.get_checkout_status(session_id)
            if st.payment_status == "paid":
                await mark_order_paid(session_id)
                order = await db.verified_estate_orders.find_one({"session_id": session_id})
        except Exception as e:
            logger.warning(f"Stripe status poll failed for {session_id}: {e}")
    return serialize_doc(order)


@router.get("/admin/orders")
async def admin_list_orders(
    status: Optional[str] = Query(None, pattern="^(pending|paid|failed)$"),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    user: dict = Depends(require_role("admin", "operator")),
):
    _ensure_enabled()
    query = {}
    if status:
        query["status"] = status
    cursor = db.verified_estate_orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
    items = [serialize_doc(d) async for d in cursor]
    total = await db.verified_estate_orders.count_documents(query)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


# ----------------- Seed helper (called from server startup) -----------------

async def seed_demo_listings():
    """Idempotent seed of 2 demo listings so the public /imobile-verificate page
    is never empty during ETAPA 1. Only runs if collection is completely empty."""
    if not FEATURE_FLAG:
        return
    count = await db.verified_estate_listings.count_documents({})
    if count > 0:
        return
    now = datetime.now(timezone.utc)
    demo = [
        {
            "_id": ObjectId(),
            "title": "Apartament Premium 3 camere · Aviatorilor",
            "city": "București",
            "address": "Bd. Aviatorilor, Sector 1",
            "price_ron": 285000.0,
            "rooms": 3,
            "surface_sqm": 92.0,
            "floor": "4/8",
            "year_built": 2019,
            "lat": 44.4632,
            "lng": 26.0894,
            "description": "Apartament complet renovat, vedere parc, finisaje premium. "
                           "Audit tehnic complet realizat: instalații electrice 2024, "
                           "hidraulice 2023, fără reparații necesare. Digital Twin disponibil "
                           "pentru vizionare 3D înainte de programarea unei vizionări fizice.",
            "transaction_type": "sale",
            "digital_twin_id": "demo-twin-1",
            "audit_report_id": "demo-audit-1",
            "audit_report_url": "/demo/audit-report-1.pdf",
            "cover_image_url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1200&q=80",
                "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1200&q=80",
            ],
            "recommendations_total": 10,
            "recommendations_accepted": 10,
            "status": "published",
            "created_at": now,
            "updated_at": now,
            "published_at": now,
            "view_count": 0,
            "inquiry_count": 0,
            "gates_status": {
                "gate_1_audit": {"ok": True, "reason": ""},
                "gate_2_twin": {"ok": True, "reason": ""},
                "gate_3_recommendations": {"ok": True, "reason": "", "pct": 100.0},
            },
        },
        {
            "_id": ObjectId(),
            "title": "Vilă verificată · Pipera Premium",
            "city": "București",
            "address": "Str. Erou Iancu Nicolae, Pipera",
            "price_ron": 685000.0,
            "rooms": 5,
            "surface_sqm": 240.0,
            "floor": "P+1",
            "year_built": 2017,
            "lat": 44.5215,
            "lng": 26.1278,
            "description": "Vilă individuală cu curte 320 m², garaj dublu, sistem inteligent "
                           "smart-home preinstalat. Audit complet: structură A+, instalații A, "
                           "izolație termică B+ (recomandare panouri solare acceptată de proprietar). "
                           "Toate cele 12 recomandări PropManage acceptate și implementate.",
            "transaction_type": "sale",
            "digital_twin_id": "demo-twin-2",
            "audit_report_id": "demo-audit-2",
            "audit_report_url": "/demo/audit-report-2.pdf",
            "cover_image_url": "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=1200&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1568605114967-8130f3a36994?w=1200&q=80",
                "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=1200&q=80",
            ],
            "recommendations_total": 12,
            "recommendations_accepted": 12,
            "status": "published",
            "created_at": now,
            "updated_at": now,
            "published_at": now,
            "view_count": 0,
            "inquiry_count": 0,
            "gates_status": {
                "gate_1_audit": {"ok": True, "reason": ""},
                "gate_2_twin": {"ok": True, "reason": ""},
                "gate_3_recommendations": {"ok": True, "reason": "", "pct": 100.0},
            },
        },
    ]
    await db.verified_estate_listings.insert_many(demo)
    logger.info(f"Seeded {len(demo)} demo Verified Estate listings")
