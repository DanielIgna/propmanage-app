"""Specialist Cockpit v1 (Blueprint Phase 3) — Pipeline & Bani + benchmark Observatory.

Business Assistant v1 (rule-based): „Cum câștigi mai mult luna asta?"
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/specialist/cockpit", tags=["specialist-cockpit"])


def _month_start(offset: int = 0) -> str:
    now = datetime.now(timezone.utc)
    y, m = now.year, now.month - offset
    while m <= 0:
        m += 12
        y -= 1
    return datetime(y, m, 1, tzinfo=timezone.utc).isoformat()


def _amount(r: dict) -> float:
    return float(r.get("final_price") or r.get("price") or r.get("budget_estimate") or 0)


@router.get("")
async def specialist_cockpit(user=Depends(require_role("specialist"))):
    sid = str(user.get("id") or user.get("_id"))
    specialty = user.get("specialty")

    # Pipeline
    leads_matched = await db.requests.count_documents({"status": "open", "category": specialty}) if specialty else 0
    leads_total = await db.requests.count_documents({"status": "open"})
    mine = await db.requests.find({"specialist_id": sid}, {"status": 1, "final_price": 1, "price": 1, "budget_estimate": 1, "confirmed_at": 1, "updated_at": 1, "created_at": 1}).to_list(2000)
    active = [r for r in mine if r.get("status") in ("accepted", "in_progress")]
    confirmed = [r for r in mine if r.get("status") == "confirmed"]

    # Bani: luna curentă vs luna trecută
    m0, m1 = _month_start(0), _month_start(1)
    def _when(r):
        return str(r.get("confirmed_at") or r.get("updated_at") or r.get("created_at") or "")
    this_month = sum(_amount(r) for r in confirmed if _when(r) >= m0)
    last_month = sum(_amount(r) for r in confirmed if m1 <= _when(r) < m0)
    trend = round((this_month - last_month) / last_month * 100) if last_month else None
    avg_job = round(sum(map(_amount, confirmed)) / len(confirmed)) if confirmed else 0

    # Benchmark Observatory (media pieței pentru categoria specialistului)
    benchmark = None
    if specialty:
        from construction.prices import aggregate_prices
        rows = await aggregate_prices(specialty)
        mids = [r for r in rows if r["experience_level"] == "mid"]
        experts = [r for r in rows if r["experience_level"] == "expert"]
        if rows:
            benchmark = {
                "category": specialty,
                "mid_avg": round(sum(r["price_med"] for r in mids) / len(mids)) if mids else None,
                "expert_avg": round(sum(r["price_med"] for r in experts) / len(experts)) if experts else None,
                "unit": rows[0]["unit"],
                "services": len({r["service"] for r in rows}),
            }

    # Business Assistant v1 — next best actions (rule-based)
    actions = []
    if leads_matched:
        actions.append({"kind": "leads", "text": f"{leads_matched} cereri deschise pe categoria ta te așteaptă — trimite oferte azi, primii care răspund câștigă lucrarea.", "cta": "opportunities"})
    if not user.get("verified"):
        actions.append({"kind": "kyc", "text": "Finalizează verificarea KYC — profilurile verificate primesc prioritate la matching și încrederea clienților.", "cta": "settings"})
    if (user.get("reviews_count") or 0) < 5:
        actions.append({"kind": "reviews", "text": "Cere recenzii clienților mulțumiți — sub 5 recenzii, algoritmul te afișează mai rar.", "cta": "jobs"})
    if benchmark and benchmark.get("expert_avg") and avg_job and avg_job < benchmark["expert_avg"]:
        actions.append({"kind": "pricing", "text": f"Câștigul tău mediu/lucrare ({avg_job} RON) e sub media expert de piață — calitatea ta ({user.get('rating') or '—'}★) susține tarife mai mari.", "cta": "opportunities"})
    if trend is not None and trend < 0:
        actions.append({"kind": "momentum", "text": f"Încasările au scăzut cu {abs(trend)}% față de luna trecută — răspunde la lead-uri în primele 2 ore ca să recuperezi.", "cta": "opportunities"})
    if not actions:
        actions.append({"kind": "steady", "text": "Totul arată bine — menține ritmul de răspuns la cereri și cere recenzii după fiecare lucrare finalizată.", "cta": "opportunities"})

    return {
        "pipeline": {
            "leads_matched": leads_matched,
            "leads_total": leads_total,
            "offers_active": len(active),
            "done_this_month": sum(1 for r in confirmed if _when(r) >= m0),
        },
        "money": {
            "this_month": round(this_month),
            "last_month": round(last_month),
            "trend_pct": trend,
            "avg_per_job": avg_job,
        },
        "benchmark": benchmark,
        "assistant_actions": actions[:4],
    }
