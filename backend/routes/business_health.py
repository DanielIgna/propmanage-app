"""Business Health — 8 department scores computed from real platform data.

Each score 0-100 with color: green ≥80 · yellow ≥60 · red <60.
compute_health() is reused by Command Center (red dept → alert) and CEO Dashboard.
A daily snapshot is persisted into business_health_history (max 1/day) for trends.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/business-health", tags=["business-health"])
logger = logging.getLogger("propmanage.business_health")


def _color(score: float) -> str:
    return "green" if score >= 80 else "yellow" if score >= 60 else "red"


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


async def compute_health() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    d30 = (now - timedelta(days=30)).isoformat()
    d60 = (now - timedelta(days=60)).isoformat()

    # ── MARKETING: user acquisition growth 30d vs prev 30d ──────────────────
    users_30 = await db.users.count_documents({"created_at": {"$gte": d30}})
    users_prev = await db.users.count_documents({"created_at": {"$gte": d60, "$lt": d30}})
    growth = ((users_30 - users_prev) / users_prev * 100) if users_prev else (100 if users_30 else 0)
    marketing = _clamp(60 + growth * 0.8)

    # ── MARKETPLACE: fill rate — cereri cu specialist / total ────────────────
    total_req = await db.requests.count_documents({})
    filled = await db.requests.count_documents({"specialist_id": {"$nin": [None, ""]}})
    marketplace = _clamp((filled / total_req * 100)) if total_req else 50

    # ── ESCROW: released / (released + frozen) ───────────────────────────────
    released = await db.requests.count_documents({"escrow_status": "released"})
    frozen = await db.requests.count_documents({"escrow_status": "frozen"})
    escrow = _clamp(released / (released + frozen) * 100) if (released + frozen) else 90

    # ── SPECIALIȘTI: % verificați × 0.6 + % cu specialitate × 0.4 ────────────
    spec_total = await db.users.count_documents({"role": "specialist"})
    spec_verified = await db.users.count_documents({"role": "specialist", "verified": True})
    spec_complete = await db.users.count_documents({"role": "specialist", "specialty": {"$nin": [None, ""]}})
    specialists = _clamp((spec_verified / spec_total * 60 + spec_complete / spec_total * 40)) if spec_total else 50

    # ── SUPORT: dispute rezolvate / totale ───────────────────────────────────
    disp_total = await db.disputes.count_documents({})
    disp_resolved = await db.disputes.count_documents({"status": {"$in": ["resolved", "closed"]}})
    suport = _clamp(disp_resolved / disp_total * 100) if disp_total else 95

    # ── CONVERSII: plăți paid / (paid + pending + initiated) ─────────────────
    pay_total = await db.payment_transactions.count_documents({})
    pay_paid = await db.payment_transactions.count_documents({"payment_status": "paid"})
    conversii = _clamp(pay_paid / pay_total * 100) if pay_total else 50

    # ── SEO: media scorurilor de audit pe paginile publice (Design Audit) ────
    seo_scores = []
    async for row in db.design_audit_cache.find({"key": {"$in": ["landing", "marketplace", "preturi", "legal"]}}):
        r = row.get("result") or {}
        if r.get("mobile_score"):
            seo_scores.append((r["mobile_score"] + r.get("desktop_score", 0)) / 2)
    seo = _clamp(sum(seo_scores) / len(seo_scores)) if seo_scores else 65

    # ── FINANCIAR: revenue growth 30d vs prev 30d ────────────────────────────
    async def _rev(gte: str, lt: str | None = None) -> float:
        q: dict[str, Any] = {"payment_status": "paid", "created_at": {"$gte": gte}}
        if lt:
            q["created_at"]["$lt"] = lt
        total = 0.0
        async for p in db.payment_transactions.find(q, {"amount": 1}):
            total += float(p.get("amount") or 0)
        return total

    rev_30 = await _rev(d30)
    rev_prev = await _rev(d60, d30)
    rev_growth = ((rev_30 - rev_prev) / rev_prev * 100) if rev_prev else (100 if rev_30 else 0)
    financiar = _clamp(60 + rev_growth * 0.8)

    departments = [
        {"key": "marketing",   "label": "Marketing",   "score": marketing,   "detail": f"Creștere utilizatori 30z: {growth:+.0f}% ({users_30} vs {users_prev})"},
        {"key": "marketplace", "label": "Marketplace", "score": marketplace, "detail": f"Fill rate: {filled}/{total_req} cereri au specialist asignat"},
        {"key": "escrow",      "label": "Escrow",      "score": escrow,      "detail": f"{released} eliberate vs {frozen} înghețate"},
        {"key": "specialisti", "label": "Specialiști", "score": specialists, "detail": f"{spec_verified}/{spec_total} verificați · {spec_complete} cu specialitate"},
        {"key": "suport",      "label": "Suport",      "score": suport,      "detail": f"{disp_resolved}/{disp_total} dispute rezolvate"},
        {"key": "conversii",   "label": "Conversii",   "score": conversii,   "detail": f"{pay_paid}/{pay_total} plăți finalizate"},
        {"key": "seo",         "label": "SEO",         "score": seo,         "detail": f"Media audit pagini publice ({len(seo_scores)} auditate)" if seo_scores else "Fără audit recent — rulează Design Audit pe paginile publice"},
        {"key": "financiar",   "label": "Financiar",   "score": financiar,   "detail": f"Revenue 30z: {rev_30:,.0f} lei ({rev_growth:+.0f}% vs perioada anterioară)"},
    ]
    for d in departments:
        d["color"] = _color(d["score"])

    overall = round(sum(d["score"] for d in departments) / len(departments), 1)

    # Atribuire Google Ads → conversii (leagă marketingul de comportamentul real al clientului)
    attribution = None
    try:
        from routes.attribution import compute_attribution_summary
        attribution = await compute_attribution_summary(30)
        # atașează un rezumat pe departamentul Marketing (semnal REAL, fără a modifica scorul)
        for d in departments:
            if d["key"] == "marketing":
                d["attribution"] = {
                    "ad_visitors": attribution["ad_visitors"],
                    "conversions_ad_attributed": attribution["conversions_ad_attributed"],
                    "ad_signup_rate_pct": attribution["ad_signup_rate_pct"],
                    "ad_attributed_value_ron": attribution["ad_attributed_value_ron"],
                }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[business_health] attribution attach failed: {e}")

    return {
        "departments": departments,
        "overall": overall,
        "overall_color": _color(overall),
        "attribution": attribution,
        "generated_at": now.isoformat(),
    }


async def _snapshot_daily(health: dict[str, Any]) -> None:
    """Persist max one snapshot per calendar day for historic trends."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    existing = await db.business_health_history.find_one({"date": today})
    if existing:
        return
    await db.business_health_history.insert_one({
        "date": today,
        "overall": health["overall"],
        "scores": {d["key"]: d["score"] for d in health["departments"]},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


@router.get("")
async def business_health(_admin=Depends(require_role("admin"))):
    health = await compute_health()
    await _snapshot_daily(health)
    return health


@router.get("/history")
async def health_history(days: int = 30, _admin=Depends(require_role("admin"))):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max(7, min(days, 90)))).strftime("%Y-%m-%d")
    out = []
    async for row in db.business_health_history.find({"date": {"$gte": cutoff}}, {"_id": 0}).sort("date", 1):
        out.append(row)
    return {"history": out, "days": days}
