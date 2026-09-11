"""PropManage router: admin."""
import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Body

from db import db
from core_utils import serialize_doc
from deps import require_role
from services import notify, log_event
from models import DocumentReviewIn, SpecialistRejectIn
from email_service import (
    send_template, tpl_specialist_verified, tpl_trust_badge_invite,
)
from demo_reset import reset_demo_accounts

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["admin"])


@router.post("/admin/demo/reset")
async def admin_trigger_demo_reset(user: dict = Depends(require_role("admin"))):
    """Manually trigger the nightly demo reset (idempotent).
    Used by CI/pytest conftest to ensure a clean baseline between test runs."""
    res = await reset_demo_accounts()
    return res


@router.get("/admin/beta-testers")
async def admin_beta_testers(
    days: int = 30,
    role: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Beta Testers dashboard — list users registered in the last N days with
    provenance (Google OAuth vs email register) + activity stats (login count,
    requests count, last_seen) so admin can monitor engagement during beta."""
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, days))).isoformat()

    q = {
        "created_at": {"$gte": cutoff},
        "email": {"$nin": [
            "admin@propmanage.io", "client@propmanage.io",
            "specialist@propmanage.io", "operator@propmanage.io",
            "danieligna1@gmail.com", "carlospacu@gmail.com",
        ]},
    }
    if role in ("client", "specialist", "operator"):
        q["role"] = role

    docs = await db.users.find(q, {
        "email": 1, "name": 1, "role": 1, "picture": 1, "phone": 1,
        "google_auth": 1, "created_at": 1, "last_seen": 1, "verified": 1,
        "wallet_balance": 1, "tokens": 1, "banned": 1,
    }).sort("created_at", -1).to_list(200)

    user_ids = [str(d["_id"]) for d in docs]

    # Activity stats (batched)
    req_counts = {}
    if user_ids:
        async for r in db.requests.aggregate([
            {"$match": {"$or": [
                {"client_id": {"$in": user_ids}},
                {"specialist_id": {"$in": user_ids}},
            ]}},
            {"$group": {"_id": None, "ids": {"$push": "$client_id"}, "sids": {"$push": "$specialist_id"}}},
        ]):
            for cid in r.get("ids") or []:
                req_counts[cid] = req_counts.get(cid, 0) + 1
            for sid in r.get("sids") or []:
                if sid:
                    req_counts[sid] = req_counts.get(sid, 0) + 1

    items = []
    for d in docs:
        uid = str(d["_id"])
        provenance = "google" if d.get("google_auth") else "email"
        items.append({
            "id": uid,
            "email": d.get("email"),
            "name": d.get("name") or "—",
            "role": d.get("role"),
            "picture": d.get("picture"),
            "phone": d.get("phone"),
            "provenance": provenance,
            "verified": bool(d.get("verified")),
            "banned": bool(d.get("banned")),
            "wallet_balance": d.get("wallet_balance", 0),
            "tokens": d.get("tokens", 0),
            "requests_count": req_counts.get(uid, 0),
            "created_at": d.get("created_at"),
            "last_seen": d.get("last_seen"),
        })

    counters = {
        "total": len(items),
        "by_role": {
            "client": sum(1 for x in items if x["role"] == "client"),
            "specialist": sum(1 for x in items if x["role"] == "specialist"),
            "operator": sum(1 for x in items if x["role"] == "operator"),
        },
        "by_provenance": {
            "google": sum(1 for x in items if x["provenance"] == "google"),
            "email": sum(1 for x in items if x["provenance"] == "email"),
        },
        "with_requests": sum(1 for x in items if x["requests_count"] > 0),
        "verified": sum(1 for x in items if x["verified"]),
    }

    return {"items": items, "counters": counters, "days": days}


# Regex patterns considered "test/seed/junk" accounts (kept conservative —
# never matches real-looking emails like @gmail.com / @yahoo.com etc.).
TEST_USER_PATTERNS = [
    r"^test_.*@test\.io$",
    r"^test_.*@propmanage\.io$",
    r"^beta_.*@example\.com$",
    r"^.*_[0-9a-f]{6,}@(test\.io|example\.com|propmanage\.io)$",
]


@router.get("/admin/test-users/preview")
async def admin_preview_test_users(user: dict = Depends(require_role("admin"))):
    """Lists accounts that match the test-user patterns. Always preview before delete."""
    q = {"$and": [
        {"$or": [{"email": {"$regex": p, "$options": "i"}} for p in TEST_USER_PATTERNS]},
        # never wipe the protected demo / admin accounts
        {"email": {"$nin": [
            "admin@propmanage.io", "client@propmanage.io",
            "specialist@propmanage.io", "operator@propmanage.io",
            "danieligna1@gmail.com", "carlospacu@gmail.com",
        ]}},
        {"role": {"$ne": "admin"}},
    ]}
    docs = await db.users.find(q, {"email": 1, "name": 1, "role": 1, "created_at": 1}).to_list(500)
    items = [{"id": str(d["_id"]), "email": d.get("email"), "name": d.get("name"),
              "role": d.get("role"), "created_at": d.get("created_at")} for d in docs]
    return {"items": items, "count": len(items), "patterns": TEST_USER_PATTERNS}


@router.post("/admin/test-users/cleanup")
async def admin_cleanup_test_users(
    confirm: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Delete all accounts that match the test-user patterns + their owned data.
    Body MUST include `confirm=STERGE` to actually delete. Returns counts per resource."""
    if confirm != "STERGE":
        raise HTTPException(400, "Confirmare obligatorie: trimite `?confirm=STERGE` pentru a executa.")

    # Pick targets
    q = {"$and": [
        {"$or": [{"email": {"$regex": p, "$options": "i"}} for p in TEST_USER_PATTERNS]},
        {"email": {"$nin": [
            "admin@propmanage.io", "client@propmanage.io",
            "specialist@propmanage.io", "operator@propmanage.io",
            "danieligna1@gmail.com", "carlospacu@gmail.com",
        ]}},
        {"role": {"$ne": "admin"}},
    ]}
    targets = await db.users.find(q, {"_id": 1, "email": 1}).to_list(500)
    target_ids = [str(t["_id"]) for t in targets]
    target_emails = [t.get("email") for t in targets]

    if not target_ids:
        return {"deleted_users": 0, "details": "Niciun user de test găsit."}

    # Cascade-delete owned data (best-effort; if a collection doesn't exist, ignore)
    from bson import ObjectId as _OID
    obj_ids = []
    for tid in target_ids:
        try:
            obj_ids.append(_OID(tid))
        except Exception:
            pass

    counts = {}
    async def _del(col_name, query):
        try:
            r = await db[col_name].delete_many(query)
            counts[col_name] = r.deleted_count
        except Exception:
            counts[col_name] = 0

    # Property-related
    await _del("properties", {"owner_id": {"$in": target_ids}})
    # Requests as client OR specialist
    await _del("requests", {"$or": [
        {"client_id": {"$in": target_ids}},
        {"specialist_id": {"$in": target_ids}},
    ]})
    # Reviews
    await _del("reviews", {"$or": [
        {"specialist_id": {"$in": target_ids}},
        {"client_id": {"$in": target_ids}},
    ]})
    # Portfolio + offers + disputes + notifications + chat
    await _del("portfolio", {"specialist_id": {"$in": target_ids}})
    await _del("offers", {"specialist_id": {"$in": target_ids}})
    await _del("disputes", {"$or": [{"opened_by": {"$in": target_ids}}, {"specialist_id": {"$in": target_ids}}, {"client_id": {"$in": target_ids}}]})
    await _del("notifications", {"user_id": {"$in": target_ids}})
    await _del("chat_messages", {"sender_id": {"$in": target_ids}})
    await _del("specialist_documents", {"specialist_id": {"$in": target_ids}})
    # Finally delete the users themselves
    await _del("users", {"_id": {"$in": obj_ids}})

    # Audit log
    await db.audit_log.insert_one({
        "actor": user["id"],
        "actor_role": "admin",
        "action": "admin.cleanup_test_users",
        "target_emails": target_emails,
        "counts": counts,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"deleted_users": counts.get("users", 0), "counts": counts, "emails": target_emails}

# ============= ADMIN =============
@router.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_role("admin"))):
    users_count = await db.users.count_documents({})
    specialists_count = await db.users.count_documents({"role": "specialist"})
    verified_count = await db.users.count_documents({"role": "specialist", "verified": True})
    pending_count = await db.users.count_documents({"role": "specialist", "verified": False})
    active_jobs = await db.requests.count_documents({"status": {"$in": ["assigned", "in_progress"]}})
    completed_jobs = await db.requests.count_documents({"status": "confirmed"})
    return {
        "users": users_count,
        "specialists": specialists_count,
        "verified": verified_count,
        "pending_verification": pending_count,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs
    }

@router.get("/admin/analytics")
async def admin_analytics(days: int = 14, user: dict = Depends(require_role("admin"))):
    """Live analytics: time-series of jobs/disputes/users + breakdowns by category/status"""
    if days < 1 or days > 90:
        days = 14
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    start_iso = start.isoformat()

    # Time-series via single aggregation pipeline per collection (batch-optimized)
    async def daily_buckets(collection, date_field):
        pipeline = [
            {"$match": {date_field: {"$gte": start_iso}}},
            {"$project": {"day": {"$substr": [f"${date_field}", 0, 10]}}},
            {"$group": {"_id": "$day", "count": {"$sum": 1}}},
        ]
        docs = await collection.aggregate(pipeline).to_list(200)
        return {d["_id"]: d["count"] for d in docs}

    jobs_created_map, jobs_confirmed_map, users_map, disputes_map = await asyncio.gather(
        daily_buckets(db.requests, "created_at"),
        daily_buckets(db.requests, "confirmed_at"),
        daily_buckets(db.users, "created_at"),
        daily_buckets(db.disputes, "created_at"),
    )

    series = []
    for i in range(days):
        day = (start + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        key = day.strftime("%Y-%m-%d")
        series.append({
            "date": day.strftime("%d %b"),
            "jobs_created": jobs_created_map.get(key, 0),
            "jobs_confirmed": jobs_confirmed_map.get(key, 0),
            "users": users_map.get(key, 0),
            "disputes": disputes_map.get(key, 0),
        })

    # Category + status breakdowns (parallel)
    cat_pipeline = [
        {"$match": {"created_at": {"$gte": start_iso}}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]

    cat_docs, status_docs, confirmed_requests, leads_count, disputes_total, disputes_open, disputes_resolved = await asyncio.gather(
        db.requests.aggregate(cat_pipeline).to_list(20),
        db.requests.aggregate(status_pipeline).to_list(20),
        db.requests.find({"status": "confirmed", "escrow_amount": {"$gt": 0}, "confirmed_at": {"$gte": start_iso}}).to_list(2000),
        db.requests.count_documents({"specialist_id": {"$ne": None}, "assigned_at": {"$gte": start_iso}}),
        db.disputes.count_documents({}),
        db.disputes.count_documents({"status": "open"}),
        db.disputes.count_documents({"status": "resolved"}),
    )

    by_category = [{"name": (d["_id"] or "other"), "value": d["count"]} for d in cat_docs]
    by_status = [{"name": d["_id"] or "unknown", "value": d["count"]} for d in status_docs]

    gmv = sum((r.get("escrow_amount") or 0) for r in confirmed_requests)
    platform_revenue_fees = gmv * 0.05
    lead_fees = leads_count * 45.0
    avg_job_value = (gmv / len(confirmed_requests)) if confirmed_requests else 0

    # Top specialists - batch lookup users in 1 query
    top_pipeline = [
        {"$match": {"status": "confirmed", "specialist_id": {"$ne": None}}},
        {"$group": {"_id": "$specialist_id", "jobs": {"$sum": 1}, "revenue": {"$sum": "$escrow_amount"}}},
        {"$sort": {"jobs": -1}},
        {"$limit": 5},
    ]
    top_docs = await db.requests.aggregate(top_pipeline).to_list(5)
    spec_ids = [ObjectId(t["_id"]) for t in top_docs if t.get("_id")]
    specs_lookup = {}
    if spec_ids:
        async for sp in db.users.find({"_id": {"$in": spec_ids}}):
            specs_lookup[str(sp["_id"])] = sp
    top_specialists = []
    for t in top_docs:
        sp = specs_lookup.get(t.get("_id"))
        if sp:
            top_specialists.append({
                "id": str(sp["_id"]),
                "name": sp.get("name", "—"),
                "specialty": sp.get("specialty"),
                "rating": sp.get("rating"),
                "jobs": t["jobs"],
                "revenue": t["revenue"],
            })

    return {
        "series": series,
        "by_category": by_category,
        "by_status": by_status,
        "gmv": round(gmv, 2),
        "platform_revenue": round(platform_revenue_fees + lead_fees, 2),
        "lead_fees": round(lead_fees, 2),
        "avg_job_value": round(avg_job_value, 2),
        "disputes": {"total": disputes_total, "open": disputes_open, "resolved": disputes_resolved},
        "top_specialists": top_specialists,
    }

@router.get("/admin/specialists/pending")
async def pending_specialists(user: dict = Depends(require_role("admin"))):
    docs = await db.users.find({"role": "specialist", "verified": False}).to_list(100)
    return [serialize_doc(d) for d in docs]

@router.post("/admin/specialists/{spec_id}/verify")
async def verify_specialist(spec_id: str, user: dict = Depends(require_role("admin"))):
    spec = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    if not spec:
        raise HTTPException(404, "Specialist not found")
    now_iso = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"_id": ObjectId(spec_id), "role": "specialist"},
        {"$set": {"verified": True, "tier": "VERIFIED", "verified_at": now_iso}}
    )
    await notify(spec_id, "Cont verificat ✓", "Felicitări! Contul tău este acum VERIFIED. Ai acces la marketplace-ul de premium leads.", type_="verification", link="/specialist")
    await send_template(tpl_specialist_verified, spec.get("name"), to=spec.get("email"))
    # Send the Trust Badge invite (encourages embed → organic backlinks)
    try:
        await send_template(tpl_trust_badge_invite, spec.get("name"), to=spec.get("email"))
    except Exception:  # noqa: BLE001
        pass
    # Tier milestone check after KYC approval (verified field changed)
    try:
        from routes.tier_milestones import check_tier_milestones
        await check_tier_milestones(spec_id)
    except Exception:
        pass
    # CIP-A: specialist verificat → recalculează vizibilitatea nomenclatorului
    try:
        from orchestrator.engine import emit_signal
        await emit_signal("category_visibility_refresh", {"trigger": f"specialist_verified:{spec_id}"})
    except Exception:  # noqa: BLE001
        pass
    # SEO: verification may push a service×city over the gate threshold → refresh sitemap.
    try:
        import asyncio
        from seo_regen import on_specialist_verification_changed
        asyncio.create_task(on_specialist_verification_changed(spec_id, source="admin_verify"))
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True}


@router.post("/admin/specialists/trust-badge/blast")
async def trust_badge_blast(user: dict = Depends(require_role("admin")), dry_run: bool = False):
    """One-shot: send the trust-badge invite email to ALL existing VERIFIED specialists.

    Idempotent via `trust_badge_invite_sent_at` flag — re-runs only target users who
    haven't received it yet. Pass `dry_run=true` to count without sending.
    """
    cursor = db.users.find(
        {"role": "specialist", "verified": True, "trust_badge_invite_sent_at": {"$exists": False}},
        {"email": 1, "name": 1},
    )
    targets: list[dict] = []
    async for d in cursor:
        if d.get("email"):
            targets.append({"id": str(d["_id"]), "email": d["email"], "name": d.get("name") or "Specialist"})
    if dry_run:
        return {"dry_run": True, "would_send_to": len(targets), "targets": [t["email"] for t in targets]}

    sent, failed = 0, 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for t in targets:
        try:
            await send_template(tpl_trust_badge_invite, t["name"], to=t["email"])
            await db.users.update_one(
                {"_id": ObjectId(t["id"])},
                {"$set": {"trust_badge_invite_sent_at": now_iso}},
            )
            sent += 1
        except Exception:  # noqa: BLE001
            failed += 1
    return {"sent": sent, "failed": failed, "total_targets": len(targets)}

@router.get("/admin/disputes")
async def list_disputes(user: dict = Depends(require_role("admin"))):
    docs = await db.disputes.find({}).sort("created_at", -1).to_list(50)
    # Batch enrich: collect all request_ids then fetch in 1 query, same for users
    req_ids = [ObjectId(d["request_id"]) for d in docs if d.get("request_id")]
    reqs_map = {}
    user_ids_set = set()
    if req_ids:
        async for r in db.requests.find({"_id": {"$in": req_ids}}):
            reqs_map[str(r["_id"])] = r
            if r.get("client_id"): user_ids_set.add(r["client_id"])
            if r.get("specialist_id"): user_ids_set.add(r["specialist_id"])
    users_map = {}
    if user_ids_set:
        async for u2 in db.users.find({"_id": {"$in": [ObjectId(uid) for uid in user_ids_set]}}):
            users_map[str(u2["_id"])] = u2
    out = []
    for d in docs:
        d = serialize_doc(d)
        req = reqs_map.get(d.get("request_id"))
        # Enriched fields are ALWAYS present (None/0 for orphaned disputes
        # whose request was deleted) — stable contract for the admin UI.
        d["request_title"] = req.get("title") if req else None
        d["request_status"] = req.get("status") if req else None
        d["escrow_amount"] = req.get("escrow_amount", 0) if req else 0
        client_u = users_map.get(req.get("client_id")) if req else None
        spec_u = users_map.get(req.get("specialist_id")) if req else None
        d["client_name"] = client_u.get("name") if client_u else None
        d["specialist_name"] = spec_u.get("name") if spec_u else None
        out.append(d)
    return out

@router.get("/admin/specialists/{spec_id}")
async def admin_specialist_detail(spec_id: str, user: dict = Depends(require_role("admin"))):
    doc = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    if not doc:
        raise HTTPException(404, "Specialist not found")
    return serialize_doc(doc)

@router.post("/admin/specialists/{spec_id}/reject")
async def reject_specialist(spec_id: str, data: SpecialistRejectIn, user: dict = Depends(require_role("admin"))):
    spec = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    if not spec:
        raise HTTPException(404, "Specialist not found")
    await db.users.update_one(
        {"_id": ObjectId(spec_id)},
        {"$set": {
            "verified": False,
            "tier": "REJECTED",
            "rejection_reason": data.reason,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejected_by": user["id"],
        }}
    )
    await notify(spec_id, "Verificare respinsă", f"Cererea de verificare a fost respinsă. Motiv: {data.reason}", type_="verification", link="/specialist")
    return {"ok": True}

@router.post("/admin/specialists/{spec_id}/documents/{doc_id}/review")
async def review_specialist_document(spec_id: str, doc_id: str, data: DocumentReviewIn, user: dict = Depends(require_role("admin"))):
    spec = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    if not spec:
        raise HTTPException(404, "Specialist not found")
    docs = spec.get("documents") or []
    found = False
    for d in docs:
        if d.get("id") == doc_id:
            d["status"] = data.status
            d["reason"] = data.reason
            d["validated_at"] = datetime.now(timezone.utc).isoformat()
            d["validated_by"] = user["id"]
            found = True
            break
    if not found:
        raise HTTPException(404, "Document not found")
    await db.users.update_one({"_id": ObjectId(spec_id)}, {"$set": {"documents": docs}})
    title = "Document aprobat" if data.status == "approved" else "Document respins"
    msg = f"Documentul '{next((d['name'] for d in docs if d.get('id')==doc_id), '')}' a fost {('aprobat' if data.status=='approved' else 'respins')}."
    if data.reason:
        msg += f" Motiv: {data.reason}"
    await notify(spec_id, title, msg, type_="verification", link="/specialist")
    return {"ok": True}



# ============================================================================
# BULK AUTO-MATCH — Admin tool to assign pending open requests
# ============================================================================
@router.post("/admin/auto-match/preview")
async def auto_match_preview(user: dict = Depends(require_role("admin"))):
    """Preview unmatched open requests + best specialist suggestion per each.

    Read-only. Returns the list with proposed assignments so admin can review
    before executing the bulk operation.
    """
    from routes.matching import find_matching_specialists

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    cursor = db.requests.find({
        "status": "open",
        "specialist_id": {"$in": [None, ""]},
        "created_at": {"$lt": cutoff.isoformat()},
    }).sort("created_at", 1).limit(100)

    items = []
    async for req in cursor:
        category = req.get("category") or ""
        # Best-effort zone resolve
        zone = req.get("property_zone") or req.get("zone") or ""
        if not zone and req.get("property_id"):
            prop = await db.properties.find_one({"_id": ObjectId(req["property_id"])})
            if prop:
                zone = prop.get("zone") or prop.get("city") or "default"
        zone = zone or "default"

        matches = await find_matching_specialists(category, zone, max_results=3)
        best = matches[0] if matches else None
        items.append({
            "request_id": str(req["_id"]),
            "title": req.get("title"),
            "category": category,
            "client_name": req.get("client_name"),
            "property_address": req.get("property_address"),
            "created_at": req.get("created_at"),
            "best_match": {
                "id": best["id"],
                "name": best["name"],
                "rating": best.get("rating"),
                "in_zone": best.get("is_in_zone"),
                "reasons": best.get("match_reasons", []),
            } if best else None,
            "alternatives_count": max(0, len(matches) - 1),
        })

    return {
        "items": items,
        "total_unmatched": len(items),
        "with_match_available": sum(1 for i in items if i["best_match"]),
        "no_match_available": sum(1 for i in items if not i["best_match"]),
    }


@router.post("/admin/auto-match/run")
async def auto_match_run(
    payload: dict = Body(default={}),
    user: dict = Depends(require_role("admin")),
):
    """Bulk-assign unmatched open requests to their best-fit specialist.

    Admin-driven matching — bypasses the 45 RON lead fee (admin tool).
    Each assignment is logged + the specialist + client receive notification.

    Body:
      {
        "limit": 50,            # cap on how many to assign in one run
        "min_rating": 4.0,      # skip specialists below this rating
        "dry_run": false        # if true, returns plan without writing
      }
    """
    limit = int(payload.get("limit") or 50)
    min_rating = float(payload.get("min_rating") or 0.0)
    dry_run = bool(payload.get("dry_run") or False)
    return await execute_auto_match(
        limit=limit, min_rating=min_rating, dry_run=dry_run,
        triggered_by={"id": user["id"], "kind": "admin_manual", "label": user.get("email")},
    )


async def execute_auto_match(
    limit: int = 50,
    min_rating: float = 0.0,
    dry_run: bool = False,
    triggered_by: Optional[dict] = None,
) -> dict:
    """Core auto-match logic — usable from HTTP handler or scheduler.

    triggered_by: {"id": "...", "kind": "admin_manual"|"cron", "label": "..."}
    """
    from routes.matching import find_matching_specialists

    triggered_by = triggered_by or {"id": "system", "kind": "cron", "label": "cron"}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    cursor = db.requests.find({
        "status": "open",
        "specialist_id": {"$in": [None, ""]},
        "created_at": {"$lt": cutoff.isoformat()},
    }).sort("created_at", 1).limit(limit)

    assigned = []
    skipped = []
    async for req in cursor:
        category = req.get("category") or ""
        zone = req.get("property_zone") or req.get("zone") or ""
        if not zone and req.get("property_id"):
            try:
                prop = await db.properties.find_one({"_id": ObjectId(req["property_id"])})
                if prop:
                    zone = prop.get("zone") or prop.get("city") or "default"
            except Exception:
                zone = "default"
        zone = zone or "default"

        matches = await find_matching_specialists(category, zone, max_results=5)
        best = None
        for m in matches:
            if (m.get("rating") or 0) >= min_rating:
                best = m
                break

        if not best:
            skipped.append({
                "request_id": str(req["_id"]),
                "reason": "no_eligible_specialist",
                "category": category,
            })
            continue

        if dry_run:
            assigned.append({
                "request_id": str(req["_id"]),
                "specialist_id": best["id"],
                "specialist_name": best["name"],
                "dry_run": True,
            })
            continue

        try:
            spec = await db.users.find_one({"_id": ObjectId(best["id"])})
            update = {
                "status": "assigned",
                "specialist_id": best["id"],
                "specialist_name": spec.get("name"),
                "specialist_specialty": spec.get("specialty") or spec.get("category") or "",
                "specialist_city": spec.get("city") or spec.get("location") or "",
                "specialist_verified": bool(spec.get("verified")),
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "auto_assigned_by_admin": triggered_by.get("id"),
                "auto_assigned_at": datetime.now(timezone.utc).isoformat(),
                "auto_assigned_via": triggered_by.get("kind"),
            }
            await db.requests.update_one({"_id": req["_id"]}, {"$set": update})

            try:
                await notify(
                    req["client_id"],
                    f"Specialist alocat automat: {spec.get('name')}",
                    f"{'Cron' if triggered_by.get('kind') == 'cron' else 'Admin'} a alocat un specialist potrivit pentru '{req.get('title','')}'. Verifică detaliile.",
                    type_="assignment", link="/client",
                )
                await notify(
                    best["id"],
                    "Cerere alocată automat",
                    f"Ai primit o cerere via auto-match: {req.get('title','')}. Lead fee gratuit (admin-driven).",
                    type_="assignment", link="/specialist",
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[auto-match] notify failed for {req['_id']}: {e}")

            actor = {"id": triggered_by.get("id"), "name": triggered_by.get("label") or triggered_by.get("kind")}
            try:
                await log_event(str(req["_id"]), "request.auto_assigned", actor=actor,
                                payload={"specialist_id": best["id"], "via": triggered_by.get("kind")})
            except Exception:
                pass

            assigned.append({
                "request_id": str(req["_id"]),
                "specialist_id": best["id"],
                "specialist_name": spec.get("name"),
            })
        except Exception as e:  # noqa: BLE001
            logger.exception(f"[auto-match] failed for request {req['_id']}: {e}")
            skipped.append({
                "request_id": str(req["_id"]),
                "reason": f"error: {str(e)[:120]}",
            })

    result = {
        "ok": True,
        "dry_run": dry_run,
        "assigned_count": len(assigned),
        "skipped_count": len(skipped),
        "assigned": assigned,
        "skipped": skipped,
        "triggered_by": triggered_by,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Persist run history (skip dry-runs to avoid noise)
    if not dry_run:
        try:
            await db.auto_match_runs.insert_one({
                "executed_at": result["executed_at"],
                "triggered_by": triggered_by,
                "assigned_count": result["assigned_count"],
                "skipped_count": result["skipped_count"],
                "limit": limit,
                "min_rating": min_rating,
            })
            # Keep only last 200 runs
            cur = db.auto_match_runs.find({}, {"_id": 1}).sort("executed_at", -1).skip(200)
            old_ids = [d["_id"] async for d in cur]
            if old_ids:
                await db.auto_match_runs.delete_many({"_id": {"$in": old_ids}})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[auto-match] failed to persist run history: {e}")

    return result


# ============================================================================
# AUTO-MATCH SCHEDULE (config + cron tick)
# ============================================================================
DEFAULT_AUTO_MATCH_SCHEDULE = {
    "enabled": False,
    "interval_hours": 6,
    "min_rating": 0.0,
    "limit": 100,
}


async def _load_auto_match_schedule() -> dict:
    doc = await db.auto_match_schedule.find_one({"_id": "config"})
    if not doc:
        return DEFAULT_AUTO_MATCH_SCHEDULE.copy()
    return {
        "enabled": bool(doc.get("enabled", False)),
        "interval_hours": int(doc.get("interval_hours") or 6),
        "min_rating": float(doc.get("min_rating") or 0.0),
        "limit": int(doc.get("limit") or 100),
    }


@router.get("/admin/auto-match/schedule")
async def get_auto_match_schedule(user: dict = Depends(require_role("admin"))):
    cfg = await _load_auto_match_schedule()
    last_run = await db.auto_match_runs.find_one({}, sort=[("executed_at", -1)])
    last_cron = await db.auto_match_runs.find_one({"triggered_by.kind": "cron"}, sort=[("executed_at", -1)])
    if last_run:
        last_run.pop("_id", None)
    if last_cron:
        last_cron.pop("_id", None)
    return {
        "schedule": cfg,
        "last_run": last_run,
        "last_cron_run": last_cron,
    }


@router.put("/admin/auto-match/schedule")
async def update_auto_match_schedule(
    payload: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    cfg = await _load_auto_match_schedule()
    if "enabled" in payload:
        cfg["enabled"] = bool(payload["enabled"])
    if "interval_hours" in payload:
        h = int(payload["interval_hours"])
        if h < 1 or h > 24:
            raise HTTPException(400, "interval_hours must be between 1 and 24")
        cfg["interval_hours"] = h
    if "min_rating" in payload:
        cfg["min_rating"] = float(payload["min_rating"])
    if "limit" in payload:
        cfg["limit"] = int(payload["limit"])
    cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
    cfg["updated_by"] = user["id"]
    await db.auto_match_schedule.update_one({"_id": "config"}, {"$set": cfg}, upsert=True)
    return await _load_auto_match_schedule()


async def run_auto_match_cron_tick() -> dict:
    """APScheduler callback — runs every hour, executes auto-match only when due.

    Reads `auto_match_schedule.enabled` and `interval_hours` from MongoDB and
    skips if disabled or if the last cron run was within interval_hours.
    """
    try:
        cfg = await _load_auto_match_schedule()
        if not cfg["enabled"]:
            return {"skipped": "disabled"}
        last = await db.auto_match_runs.find_one(
            {"triggered_by.kind": "cron"}, sort=[("executed_at", -1)],
        )
        now = datetime.now(timezone.utc)
        if last and last.get("executed_at"):
            try:
                last_ts = datetime.fromisoformat(last["executed_at"].replace("Z", "+00:00"))
                if (now - last_ts) < timedelta(hours=cfg["interval_hours"]):
                    return {"skipped": "not_due", "next_due_in_sec": int((timedelta(hours=cfg["interval_hours"]) - (now - last_ts)).total_seconds())}
            except Exception:
                pass
        result = await execute_auto_match(
            limit=cfg["limit"], min_rating=cfg["min_rating"], dry_run=False,
            triggered_by={"id": "system", "kind": "cron", "label": f"cron@{cfg['interval_hours']}h"},
        )
        logger.info(f"[auto-match-cron] assigned={result['assigned_count']} skipped={result['skipped_count']}")
        return result
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[auto-match-cron] failed: {e}")
        return {"error": str(e)}

