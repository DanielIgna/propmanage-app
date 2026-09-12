"""Beta Cockpit — EO-026 Public Beta Gate: funnel pe utilizatori REALI + Voice of Customer.

Include și unealta de purge date demo pentru producție (Phase 2: "No demo data").
"""
import os
import re
from datetime import datetime, timezone, timedelta
from statistics import median

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import get_current_user, require_role

router = APIRouter(prefix="/api", tags=["beta_cockpit"])

INTERNAL_RE = re.compile(r"@propmanage\.io$|@example\.|danieligna1@gmail\.com|test|demo", re.I)
REAL_FILTER = {"email": {"$not": INTERNAL_RE}, "is_demo_sub_admin": {"$ne": True}}
MASTER_CODE = os.environ.get("DEMO_MASTER_CODE", "0108")
FEEDBACK_FIELDS = ["confusing", "easy", "trust", "almost_quit", "impressed", "why"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _pct(x: int, base: int) -> int:
    return round(x * 100 / base) if base else 0


@router.get("/admin/beta/overview")
async def beta_overview(days: int = 30, admin: dict = Depends(require_role("admin"))):
    days = max(1, min(days, 90))
    since = (_now() - timedelta(days=days)).isoformat()

    vis = await db.analytics_sessions.aggregate([
        {"$match": {"started_at": {"$gte": since}}},
        {"$group": {"_id": "$visitor_id"}}, {"$count": "n"}]).to_list(1)
    n_visitors = vis[0]["n"] if vis else 0

    new_users = await db.users.find(
        {**REAL_FILTER, "created_at": {"$gte": since}, "role": {"$in": ["client", "specialist"]}},
        {"email": 1, "role": 1, "created_at": 1, "specialty": 1, "coverage_zones": 1, "verified": 1},
    ).to_list(5000)
    owners = [u for u in new_users if u["role"] == "client"]
    specs = [u for u in new_users if u["role"] == "specialist"]
    owner_ids = [str(u["_id"]) for u in owners]
    spec_ids = [str(u["_id"]) for u in specs]

    props = await db.properties.find(
        {"owner_id": {"$in": owner_ids}}, {"owner_id": 1, "passport": 1}).to_list(5000) if owner_ids else []
    owners_with_prop = {p["owner_id"] for p in props}
    prop_ids = [str(p["_id"]) for p in props]
    prop_owner = {str(p["_id"]): p["owner_id"] for p in props}
    docs = await db.property_documents.find(
        {"property_id": {"$in": prop_ids}, "deleted": {"$ne": True}},
        {"property_id": 1, "uploaded_at": 1}).to_list(10000) if prop_ids else []
    owners_with_doc = {prop_owner.get(d["property_id"]) for d in docs if prop_owner.get(d["property_id"])}
    passport_props = [p for p in props if (p.get("passport") or {}).get("enabled")]
    owners_with_passport = {p["owner_id"] for p in passport_props}
    slugs = [s for s in ((p.get("passport") or {}).get("slug") for p in passport_props) if s]
    shared_slugs = set(await db.passport_events.distinct(
        "slug", {"slug": {"$in": slugs}, "type": "share"})) if slugs else set()
    owners_shared = {p["owner_id"] for p in passport_props
                     if (p.get("passport") or {}).get("slug") in shared_slugs}

    returning = 0
    for uid in owner_ids:
        days_active = await db.analytics_sessions.distinct("day", {"user_id": uid})
        if len(days_active) >= 2:
            returning += 1

    first_doc_by_owner = {}
    for d in docs:
        o = prop_owner.get(d["property_id"])
        ts = d.get("uploaded_at") or ""
        if o and ts and (o not in first_doc_by_owner or ts < first_doc_by_owner[o]):
            first_doc_by_owner[o] = ts
    owner_created = {str(u["_id"]): u.get("created_at") for u in owners}
    ttfv = []
    for o, ts in first_doc_by_owner.items():
        try:
            a = datetime.fromisoformat(str(owner_created.get(o)).replace("Z", "+00:00"))
            b = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            m = (b - a).total_seconds() / 60
            if m >= 0:
                ttfv.append(m)
        except Exception:
            pass

    n_o = len(owners)
    steps = [
        {"id": "registered", "label": "Cont creat", "count": n_o, "pct": 100 if n_o else 0},
        {"id": "property", "label": "Proprietate adăugată", "count": len(owners_with_prop), "pct": _pct(len(owners_with_prop), n_o)},
        {"id": "document", "label": "Primul document", "count": len(owners_with_doc), "pct": _pct(len(owners_with_doc), n_o)},
        {"id": "passport", "label": "Pașaport generat", "count": len(owners_with_passport), "pct": _pct(len(owners_with_passport), n_o)},
        {"id": "shared", "label": "Pașaport partajat", "count": len(owners_shared), "pct": _pct(len(owners_shared), n_o)},
        {"id": "returning", "label": "Revenit în 7 zile", "count": returning, "pct": _pct(returning, n_o)},
    ]

    spec_profile = [u for u in specs if u.get("specialty") and (u.get("coverage_zones") or [])]
    spec_verified = [u for u in specs if u.get("verified")]
    accepted = await db.requests.distinct(
        "specialist_id", {"specialist_id": {"$in": spec_ids}}) if spec_ids else []
    reviewed = await db.reviews.distinct(
        "specialist_id", {"specialist_id": {"$in": spec_ids}}) if spec_ids else []

    pv = await db.passport_events.find(
        {"ts": {"$gte": since}}, {"type": 1, "visitor_id": 1, "src": 1}).to_list(50000)
    p_views = [e for e in pv if e["type"] == "view"]
    rollup = {
        "active_passports": await db.properties.count_documents({"passport.enabled": True}),
        "views": len(p_views),
        "unique_visitors": len({e.get("visitor_id") for e in p_views}),
        "qr_scans": len([e for e in p_views if e.get("src") == "qr"]),
        "shares": len([e for e in pv if e["type"] == "share"]),
        "og_fetches": len([e for e in pv if e["type"] == "og_fetch"]),
        "cta_clicks": len([e for e in pv if e["type"] == "cta_click"]),
        "registers": len([e for e in pv if e["type"] == "register"]),
    }

    support_requests = await db.support_messages.count_documents({"created_at": {"$gte": since}})
    fb = await db.beta_feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    voc = {"count": len(fb),
           "recommend_yes": len([f for f in fb if f.get("recommend") is True]),
           "recommend_no": len([f for f in fb if f.get("recommend") is False])}

    gates = [
        {"id": "onboarding", "label": "Onboarding complet fără ajutor (primul document)", "target_pct": 80, "actual_pct": _pct(len(owners_with_doc), n_o)},
        {"id": "passport", "label": "Generează pașaportul", "target_pct": 70, "actual_pct": _pct(len(owners_with_passport), n_o)},
        {"id": "share", "label": "Partajează pașaportul", "target_pct": 50, "actual_pct": _pct(len(owners_shared), n_o)},
        {"id": "returning", "label": "Revine în 7 zile", "target_pct": 50, "actual_pct": _pct(returning, n_o)},
    ]
    for g in gates:
        g["passed"] = n_o > 0 and g["actual_pct"] >= g["target_pct"]

    return {
        "window_days": days,
        "visitors": n_visitors,
        "registrations": {"total": len(new_users), "owners": n_o, "specialists": len(specs),
                          "visitor_conversion_pct": _pct(len(new_users), n_visitors)},
        "owner_funnel": steps,
        "ttfv_minutes_median": round(median(ttfv)) if ttfv else None,
        "specialist_funnel": [
            {"id": "registered", "label": "Cont creat", "count": len(specs)},
            {"id": "profile", "label": "Profil complet", "count": len(spec_profile)},
            {"id": "verified", "label": "Verificat", "count": len(spec_verified)},
            {"id": "accepted", "label": "Prima cerere acceptată", "count": len(accepted)},
            {"id": "reviewed", "label": "Prima recenzie", "count": len(reviewed)},
        ],
        "passports": rollup,
        "support_requests": support_requests,
        "voc": voc,
        "gates": gates,
        "note": "Doar utilizatori REALI — excluși: @propmanage.io, conturi demo/test, founder (Truth Engine).",
    }


@router.post("/feedback/beta")
async def submit_beta_feedback(body: dict = Body(...), user: dict = Depends(get_current_user)):
    """Voice of Customer — cele 6 întrebări din EO-026, un răspuns per user per zi."""
    answers = {k: str(body.get(k) or "")[:1000] for k in FEEDBACK_FIELDS}
    recommend = body.get("recommend")
    if recommend is None and not any(answers.values()):
        raise HTTPException(400, "Completează cel puțin un răspuns")
    now = _now().isoformat()
    await db.beta_feedback.update_one(
        {"user_email": user.get("email"), "day": now[:10]},
        {"$set": {**answers, "recommend": bool(recommend) if recommend is not None else None,
                  "role": user.get("role"), "name": user.get("name"), "created_at": now}},
        upsert=True)
    return {"ok": True, "message": "Mulțumim! Feedback-ul tău modelează direct roadmap-ul."}


@router.get("/admin/beta/feedback")
async def list_beta_feedback(admin: dict = Depends(require_role("admin"))):
    rows = await db.beta_feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"items": rows}


@router.post("/admin/beta/purge-demo")
async def purge_demo_data(body: dict = Body(...), admin: dict = Depends(require_role("admin"))):
    """Șterge datele demo seed (producție — EO-026 'No demo data'). dry_run=true implicit.

    Șterge userii @propmanage.io (cu excepția admin@propmanage.io) + cascada lor:
    proprietăți, cereri, documente, twins, portofoliu. Gated cu cod master.
    """
    if str(body.get("master_code") or "") != MASTER_CODE:
        raise HTTPException(400, "Cod master invalid")
    dry_run = bool(body.get("dry_run", True))
    demo_users = await db.users.find(
        {"email": {"$regex": "@propmanage\\.io$", "$options": "i"}}, {"email": 1}).to_list(5000)
    demo_users = [u for u in demo_users if u["email"].lower() != "admin@propmanage.io"]
    ids = [str(u["_id"]) for u in demo_users]
    oids = [u["_id"] for u in demo_users]
    props = await db.properties.find({"owner_id": {"$in": ids}}, {"_id": 1}).to_list(10000)
    prop_ids = [str(p["_id"]) for p in props]
    prop_oids = [p["_id"] for p in props]
    req_q = {"$or": [{"client_id": {"$in": ids}}, {"specialist_id": {"$in": ids}}]}
    counts = {
        "users": len(ids),
        "properties": len(prop_ids),
        "requests": await db.requests.count_documents(req_q) if ids else 0,
        "documents": await db.property_documents.count_documents({"property_id": {"$in": prop_ids}}) if prop_ids else 0,
        "twins": await db.twins.count_documents({"property_id": {"$in": prop_ids}}) if prop_ids else 0,
        "portfolio": await db.portfolio.count_documents({"specialist_id": {"$in": ids}}) if ids else 0,
    }
    if not dry_run and ids:
        if prop_ids:
            await db.property_documents.delete_many({"property_id": {"$in": prop_ids}})
            await db.twins.delete_many({"property_id": {"$in": prop_ids}})
        await db.requests.delete_many(req_q)
        await db.portfolio.delete_many({"specialist_id": {"$in": ids}})
        await db.properties.delete_many({"_id": {"$in": prop_oids}})
        await db.users.delete_many({"_id": {"$in": oids}})
    return {"dry_run": dry_run, "counts": counts,
            "note": "În producție setează SEED_DEMO_DATA diferit de 'true' ca datele demo să NU fie recreate la restart."}
