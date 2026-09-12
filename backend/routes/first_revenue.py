"""First Revenue War Room — Board Directives 059 + 068.

Single decision-system endpoint: milestones (firsts), integration status
(Stripe/Resend/Checkout), blockers (founder vs dev), sales pipeline,
morning briefing. Read-only aggregation over existing collections.
"""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/war-room", tags=["war-room"])

MISSION_START_KEY = "war_room"


def _stripe_mode() -> str:
    key = os.environ.get("STRIPE_API_KEY", "")
    if key.startswith("sk_live_"):
        return "live"
    if key.startswith("sk_test_") and key != "sk_test_emergent":
        return "test"
    return "demo"


def _iso(dt) -> str | None:
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


async def _first(coll: str, query: dict, sort_field: str = "created_at"):
    return await db[coll].find_one(query, sort=[(sort_field, 1)])


@router.get("")
async def war_room(user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)

    meta = await db.war_room_meta.find_one({"_id": MISSION_START_KEY})
    if not meta:
        meta = {"_id": MISSION_START_KEY, "started_at": now.isoformat()}
        await db.war_room_meta.insert_one(meta)
    started = datetime.fromisoformat(meta["started_at"])
    days_since_start = max(0, (now - started).days)

    # ---------- Milestones (the "firsts") ----------
    first_paid_any = await _first("verified_estate_orders", {"status": "paid"})
    first_paid_real = await _first("verified_estate_orders", {"status": "paid", "demo_mode": {"$ne": True}})
    first_audit = await _first("verified_estate_orders", {"status": "paid", "package": {"$in": ["audit", "bundle"]}})
    first_bundle = await _first("verified_estate_orders", {"status": "paid", "package": "bundle"})
    first_twin = await _first("verified_estate_orders", {"status": "paid", "package": {"$in": ["twin", "bundle"]}})
    first_real_listing = await _first(
        "verified_estate_listings",
        {"status": {"$in": ["published", "sold"]}, "source_order_id": {"$exists": True}},
        sort_field="published_at",
    )
    first_sale = await _first("verified_estate_sales", {})
    first_buyer = await _first("verified_estate_inquiries", {"intent": "buy"})

    def _m(mid, label, doc, at_field="created_at", detail=""):
        return {
            "id": mid, "label": label, "done": bool(doc),
            "at": _iso(doc.get(at_field)) if doc else None,
            "detail": detail if not doc else (detail or ""),
        }

    milestones = [
        _m("first_customer", "Primul client (comandă plătită)", first_paid_any, "paid_at",
           "Nicio comandă plătită încă (nici demo)"),
        _m("first_real_payment", "💰 PRIMA PLATĂ REALĂ", first_paid_real, "paid_at",
           "MISIUNEA PRINCIPALĂ — plată LIVE, non-demo"),
        _m("first_audit_sold", "Primul Audit vândut", first_audit, "paid_at", "Pachet audit sau bundle plătit"),
        _m("first_bundle_sold", "Primul Bundle vândut", first_bundle, "paid_at", "Audit + Twin împreună"),
        _m("first_digital_twin", "Primul Digital Twin comandat", first_twin, "paid_at", "Pachet twin sau bundle plătit"),
        _m("first_verified_property", "Prima proprietate verificată reală", first_real_listing, "published_at",
           "Listing publicat provenit dintr-o comandă reală"),
        _m("first_commission", "Primul comision (vânzare)", first_sale, "created_at",
           "Nicio vânzare marcată încă în Kanban"),
        _m("first_buyer", "Primul cumpărător (intenție fermă)", first_buyer, "created_at",
           "Nicio cerere cu intent=buy încă"),
        {"id": "first_invoice", "label": "Prima factură (e-Factura RO)", "done": False, "at": None,
         "detail": "Backlog P1 — obligatoriu legal înainte de volum B2B"},
    ]

    # ---------- Integration status ----------
    stripe_mode = _stripe_mode()
    resend_doc = await db.integration_health.find_one({"_id": "resend"}) or {}
    feature_on = os.environ.get("FEATURE_VERIFIED_ESTATE", "true").lower() == "true"
    integrations = {
        "stripe": {
            "mode": stripe_mode,
            "ok": stripe_mode == "live",
            "label": {"live": "LIVE — plăți reale active", "test": "TEST — chei sk_test_",
                      "demo": "DEMO — placeholder Emergent"}[stripe_mode],
        },
        "resend": {
            "status": resend_doc.get("status", "unknown"),
            "ok": resend_doc.get("status") == "operational",
            "root_cause": resend_doc.get("root_cause"),
            "recommended_action": resend_doc.get("recommended_action"),
            "checked_at": resend_doc.get("checked_at"),
        },
        "checkout": {
            "enabled": feature_on,
            "ok": feature_on,
            "label": "Checkout Verified Estate activ" if feature_on else "Feature flag OPRIT",
        },
    }

    # ---------- Pipeline ----------
    orders_pending = await db.verified_estate_orders.count_documents({"status": "pending"})
    orders_paid_real = await db.verified_estate_orders.count_documents({"status": "paid", "demo_mode": {"$ne": True}})
    orders_paid_demo = await db.verified_estate_orders.count_documents({"status": "paid", "demo_mode": True})

    async def _sum(coll, query, field):
        pipe = [{"$match": query}, {"$group": {"_id": None, "t": {"$sum": f"${field}"}}}]
        rows = await db[coll].aggregate(pipe).to_list(1)
        return round(rows[0]["t"], 2) if rows else 0.0

    revenue_real = await _sum("verified_estate_orders", {"status": "paid", "demo_mode": {"$ne": True}}, "amount_ron")
    revenue_demo = await _sum("verified_estate_orders", {"status": "paid", "demo_mode": True}, "amount_ron")
    commission_net = await _sum("verified_estate_sales", {}, "commission_net_ron")
    sales_count = await db.verified_estate_sales.count_documents({})
    inquiries_new = await db.verified_estate_inquiries.count_documents({"status": "new"})
    external_new = await db.verified_estate_external_requests.count_documents({"status": "new"})
    listings_published = await db.verified_estate_listings.count_documents({"status": "published"})

    pipeline = {
        "orders_pending": orders_pending,
        "orders_paid_real": orders_paid_real,
        "orders_paid_demo": orders_paid_demo,
        "revenue_real_ron": revenue_real,
        "revenue_demo_ron": revenue_demo,
        "sales_count": sales_count,
        "commission_net_ron": commission_net,
        "inquiries_new": inquiries_new,
        "external_requests_new": external_new,
        "listings_published": listings_published,
    }

    # ---------- Blockers ----------
    blockers = []
    if stripe_mode != "live":
        blockers.append({
            "id": "stripe_live", "owner": "founder", "severity": "critical", "external": True,
            "title": "Stripe LIVE neactivat",
            "action": "Revendică/activează contul Stripe LIVE și pune cheia sk_live_ în backend/.env (producție).",
        })
    if integrations["resend"]["status"] != "operational":
        blockers.append({
            "id": "resend_dns", "owner": "founder", "severity": "critical", "external": True,
            "title": "Emailuri tranzacționale blocate (Resend/DNS)",
            "action": integrations["resend"].get("recommended_action")
            or "Rulează diagnosticul Resend din admin și fixează DNS pe Rackhost.",
        })
    if not first_real_listing:
        blockers.append({
            "id": "no_real_listing", "owner": "ops", "severity": "high", "external": False,
            "title": "Nicio proprietate reală publicată",
            "action": "Finalizează audit + twin pentru primul imobil real și publică-l din Kanban.",
        })
    if inquiries_new == 0 and external_new == 0 and orders_pending == 0:
        blockers.append({
            "id": "empty_pipeline", "owner": "founder", "severity": "high", "external": False,
            "title": "Pipeline comercial gol (0 leads active)",
            "action": "Pornește achiziția: promovează /imobile-verificate/sell către primii 10 proprietari.",
        })

    founder_actions = [b for b in blockers if b["owner"] == "founder"]
    dev_actions = [b for b in blockers if b["owner"] != "founder"]

    briefing = {
        "q1_revenue_today": "Contactează cererile noi din pipeline și împinge comenzile pending spre plată."
        if (inquiries_new or orders_pending) else "Generează primele leads: distribuie pagina /imobile-verificate/sell.",
        "q2_trust_today": "Publică primul imobil real verificat — dovada publică a modelului."
        if not first_real_listing else "Cere feedback/review de la clienții existenți.",
        "q3_simplicity_today": "Verifică fluxul de checkout end-to-end pe mobil.",
        "top_blockers": [b["title"] for b in blockers][:5],
    }

    # ---------- Mission 100 (D109) — măsurat de la startul misiunii ----------
    start_iso = meta["started_at"]
    both = lambda f: {"$or": [{f: {"$gte": started}}, {f: {"$gte": start_iso}}]}  # noqa: E731
    m_rows = await db.analytics_events.aggregate([
        {"$match": {"ts": {"$gte": start_iso}}},
        {"$group": {"_id": "$visitor_id"}}, {"$count": "n"},
    ]).to_list(1)
    m_visitors = m_rows[0]["n"] if m_rows else 0
    m_scores = await db.lead_magnet_leads.count_documents({"magnet": "health_score", "created_at": {"$gte": start_iso}})
    m_emails = await db.lead_magnet_leads.count_documents({"created_at": {"$gte": start_iso}})
    m_qualified = await db.leads.count_documents({"segment": {"$in": ["hot", "warm"]}, "created_at": {"$gte": start_iso}})
    m_audits = await db.verified_estate_orders.count_documents(
        {"status": "paid", "demo_mode": {"$ne": True}, "package": {"$in": ["audit", "bundle"]}, **both("paid_at")})
    m_twins = await db.verified_estate_orders.count_documents(
        {"status": "paid", "demo_mode": {"$ne": True}, "package": {"$in": ["twin", "bundle"]}, **both("paid_at")})
    m_reviews = await db.reviews.count_documents(both("created_at"))
    m_referrals = await db.leads.count_documents({"source": "referral", "created_at": {"$gte": start_iso}})
    mission_targets = [
        {"id": "visitors", "label": "Vizitatori", "target": 100, "actual": m_visitors},
        {"id": "property_scores", "label": "Scoruri Casa (calculator)", "target": 100, "actual": m_scores},
        {"id": "emails", "label": "Emailuri capturate", "target": 100, "actual": m_emails},
        {"id": "qualified_leads", "label": "Leads calificate (hot/warm)", "target": 50, "actual": m_qualified},
        {"id": "audits", "label": "Audituri plătite (real)", "target": 10, "actual": m_audits},
        {"id": "twins", "label": "Digital Twins plătite (real)", "target": 5, "actual": m_twins},
        {"id": "reviews", "label": "Recenzii clienți", "target": 5, "actual": m_reviews},
        {"id": "referrals", "label": "Referrals", "target": 3, "actual": m_referrals},
    ]
    mission_100 = {
        "targets": mission_targets,
        "progress_pct": round(sum(min(1.0, t["actual"] / t["target"]) for t in mission_targets) / len(mission_targets) * 100, 1),
        "complete": all(t["actual"] >= t["target"] for t in mission_targets),
    }

    first_payment_done = bool(first_paid_real)
    return {
        "mission": "FIRST REVENUE",
        "mission_complete": first_payment_done,
        "mission_100": mission_100,
        "days_since_start": days_since_start,
        "days_to_first_payment": (
            max(0, (datetime.fromisoformat(_iso(first_paid_real.get("paid_at"))) - started).days)
            if first_payment_done and first_paid_real.get("paid_at") else None
        ),
        "generated_at": now.isoformat(),
        "milestones": milestones,
        "integrations": integrations,
        "pipeline": pipeline,
        "blockers": blockers,
        "founder_actions": founder_actions,
        "dev_actions": dev_actions,
        "briefing": briefing,
    }
