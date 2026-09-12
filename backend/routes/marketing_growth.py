"""AI Marketing & Growth Department — Phase 1 (Core AI Brain).

Modul intern de marketing, BI și growth pentru super_admin / marketing_manager.

Endpoints (super_admin sau role=marketing_manager):
  GET  /api/admin/marketing/dashboard           — KPI executive în timp real
  POST /api/admin/marketing/insights            — Claude analizează datele → insights
  POST /api/admin/marketing/recommendations     — Claude → recomandări marketing+business
  POST /api/admin/marketing/copilot             — chat conversațional pe date reale
  GET  /api/admin/marketing/segments            — segmentare clienți (premium/VIP/risc)
  GET  /api/admin/marketing/forecast            — predictive analytics
  GET  /api/admin/marketing/growth              — oportunități creștere
  GET  /api/admin/marketing/future-ideas        — backlog Faza 2/3

Collections create:
  marketing_insights        { generated_at, payload, generated_by }
  marketing_recommendations { generated_at, payload, generated_by }
  marketing_chat_sessions   { session_id, messages[], created_by, updated_at }
"""
import json
import logging
import os
import statistics
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.marketing_growth")
router = APIRouter(prefix="/api/admin/marketing", tags=["admin-marketing"])

# ---------- RBAC ----------

def _require_marketing(user: dict) -> None:
    if is_super_admin(user):
        return
    if user.get("role") == "marketing_manager":
        return
    if user.get("role") == "admin" and (user.get("admin_scope") or "general").lower() in {"general", "ai", "marketing"}:
        return
    raise HTTPException(403, "Acces refuzat — necesită super_admin sau marketing_manager.")


# ---------- Helpers ----------

def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def _safe_sum(col, field: str, match: dict | None = None) -> float:
    pipeline = []
    if match:
        pipeline.append({"$match": match})
    pipeline.append({"$group": {"_id": None, "t": {"$sum": f"${field}"}}})
    total = 0.0
    async for r in col.aggregate(pipeline):
        total = float(r.get("t") or 0)
    return total


# ---------- 1. EXECUTIVE DASHBOARD ----------

@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    _require_marketing(user)
    now = datetime.now(timezone.utc)
    iso_30 = _iso_days_ago(30)
    iso_60 = _iso_days_ago(60)
    iso_7 = _iso_days_ago(7)

    # USERS
    total_users = await db.users.count_documents({})
    new_users_30 = await db.users.count_documents({"created_at": {"$gte": iso_30}})
    new_users_prev_30 = await db.users.count_documents({"created_at": {"$gte": iso_60, "$lt": iso_30}})
    # active = avut activitate în 30z (login, request, etc.) — proxy: updated_at sau last_login_at
    active_users = await db.users.count_documents({
        "$or": [{"last_login_at": {"$gte": iso_30}}, {"updated_at": {"$gte": iso_30}}]
    })
    inactive_users = max(0, total_users - active_users)
    retention = round((active_users / total_users * 100), 1) if total_users else 0
    # churn rough = clienți care nu mai au activitate de 60+ zile
    churn_users = await db.users.count_documents({
        "role": "client",
        "created_at": {"$lt": iso_60},
        "$and": [
            {"last_login_at": {"$lt": iso_60}},
        ],
    })
    total_clients_for_churn = await db.users.count_documents({"role": "client", "created_at": {"$lt": iso_60}})
    churn_rate = round((churn_users / total_clients_for_churn * 100), 1) if total_clients_for_churn else 0

    # CLIENTS
    total_clients = await db.users.count_documents({"role": "client"})
    new_clients_30 = await db.users.count_documents({"role": "client", "created_at": {"$gte": iso_30}})
    # recurenți = client cu > 1 request confirmed
    recurring_pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": "$client_id", "n": {"$sum": 1}}},
        {"$match": {"n": {"$gt": 1}}},
        {"$count": "recurring"},
    ]
    recurring_clients = 0
    async for r in db.requests.aggregate(recurring_pipeline):
        recurring_clients = r.get("recurring", 0)

    # avg order value + LTV (proxy)
    total_revenue = await _safe_sum(db.requests, "escrow_amount", {"status": "confirmed"})
    confirmed_count = await db.requests.count_documents({"status": "confirmed"})
    avg_order = round(total_revenue / confirmed_count, 2) if confirmed_count else 0
    ltv = round(total_revenue / total_clients, 2) if total_clients else 0

    # SPECIALISTS
    total_specialists = await db.users.count_documents({"role": "specialist"})
    active_specialists = await db.users.count_documents({"role": "specialist", "verified": True})
    inactive_specialists = max(0, total_specialists - active_specialists)
    # occupancy = % din specialiști care au job activ
    busy_pipeline = [
        {"$match": {"status": {"$in": ["assigned", "in_progress"]}, "specialist_id": {"$ne": None}}},
        {"$group": {"_id": "$specialist_id"}},
        {"$count": "busy"},
    ]
    busy_specialists = 0
    async for r in db.requests.aggregate(busy_pipeline):
        busy_specialists = r.get("busy", 0)
    occupancy_rate = round((busy_specialists / active_specialists * 100), 1) if active_specialists else 0
    occupancy_rate = min(occupancy_rate, 100.0)

    # revenue per specialist (top spec)
    rev_per_spec_pipeline = [
        {"$match": {"status": "confirmed", "specialist_id": {"$ne": None}}},
        {"$group": {"_id": "$specialist_id", "rev": {"$sum": "$escrow_amount"}}},
        {"$sort": {"rev": -1}},
        {"$limit": 20},
    ]
    rev_per_spec = [r async for r in db.requests.aggregate(rev_per_spec_pipeline)]
    avg_revenue_per_specialist = round(
        statistics.mean([r["rev"] for r in rev_per_spec]) if rev_per_spec else 0, 2
    )

    # accept rate proxy
    accepted = await db.requests.count_documents({"status": {"$in": ["assigned", "in_progress", "confirmed"]}})
    posted = await db.requests.count_documents({})
    accept_rate = round((accepted / posted * 100), 1) if posted else 0

    # FINANCIAL
    monthly_revenue = await _safe_sum(db.requests, "escrow_amount",
                                       {"status": "confirmed", "confirmed_at": {"$gte": iso_30}})
    prev_monthly = await _safe_sum(db.requests, "escrow_amount",
                                    {"status": "confirmed", "confirmed_at": {"$gte": iso_60, "$lt": iso_30}})
    revenue_growth = round(((monthly_revenue - prev_monthly) / prev_monthly * 100), 1) if prev_monthly else 0
    profit_estimated = round(total_revenue * 0.25, 2)  # estimat 25% margin
    taxes_collected = round(total_revenue * 0.19, 2)   # TVA 19% proxy

    # Revenue per service category
    rev_by_cat_pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": "$category", "rev": {"$sum": "$escrow_amount"}, "count": {"$sum": 1}}},
        {"$sort": {"rev": -1}},
        {"$limit": 10},
    ]
    revenue_by_category = []
    async for r in db.requests.aggregate(rev_by_cat_pipeline):
        revenue_by_category.append({
            "category": r["_id"] or "—",
            "revenue": round(r["rev"], 2),
            "orders": r["count"],
        })

    # Revenue per county
    rev_by_county_pipeline = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": "$county", "rev": {"$sum": "$escrow_amount"}, "count": {"$sum": 1}}},
        {"$sort": {"rev": -1}},
        {"$limit": 10},
    ]
    revenue_by_county = []
    async for r in db.requests.aggregate(rev_by_county_pipeline):
        revenue_by_county.append({
            "county": r["_id"] or "—",
            "revenue": round(r["rev"], 2),
            "orders": r["count"],
        })

    # Daily revenue last 30d for chart
    daily_rev_pipeline = [
        {"$match": {"status": "confirmed", "confirmed_at": {"$gte": iso_30}}},
        {"$group": {"_id": {"$substr": ["$confirmed_at", 0, 10]},
                    "rev": {"$sum": "$escrow_amount"}, "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    daily_revenue = [
        {"date": r["_id"], "revenue": round(r["rev"], 2), "orders": r["n"]}
        async for r in db.requests.aggregate(daily_rev_pipeline)
    ]

    # MARKETPLACE
    most_ordered_pipeline = [
        {"$group": {"_id": "$category", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 5},
    ]
    most_ordered = [
        {"category": r["_id"] or "—", "orders": r["n"]}
        async for r in db.requests.aggregate(most_ordered_pipeline)
    ]
    # Funnel
    funnel_new = await db.requests.count_documents({})
    funnel_assigned = await db.requests.count_documents({"status": {"$in": ["assigned", "in_progress", "confirmed"]}})
    funnel_confirmed = await db.requests.count_documents({"status": "confirmed"})
    funnel_abandoned = await db.requests.count_documents({"status": {"$in": ["cancelled", "open"]}})
    conversion_rate = round((funnel_confirmed / funnel_new * 100), 1) if funnel_new else 0
    abandonment_rate = round((funnel_abandoned / funnel_new * 100), 1) if funnel_new else 0
    completion_rate = round((funnel_confirmed / funnel_assigned * 100), 1) if funnel_assigned else 0

    return {
        "generated_at": now.isoformat(),
        "users": {
            "total": total_users,
            "new_30d": new_users_30,
            "new_30d_growth": round(((new_users_30 - new_users_prev_30) / new_users_prev_30 * 100), 1) if new_users_prev_30 else 0,
            "active": active_users,
            "inactive": inactive_users,
            "retention_rate": retention,
            "churn_rate": churn_rate,
        },
        "clients": {
            "total": total_clients,
            "new_30d": new_clients_30,
            "recurring": recurring_clients,
            "avg_order_value": avg_order,
            "estimated_ltv": ltv,
        },
        "specialists": {
            "total": total_specialists,
            "active": active_specialists,
            "inactive": inactive_specialists,
            "occupancy_rate": occupancy_rate,
            "avg_revenue_per_specialist": avg_revenue_per_specialist,
            "accept_rate": accept_rate,
        },
        "financial": {
            "total_revenue": round(total_revenue, 2),
            "monthly_revenue": round(monthly_revenue, 2),
            "monthly_growth_pct": revenue_growth,
            "profit_estimated": profit_estimated,
            "taxes_collected": taxes_collected,
            "by_category": revenue_by_category,
            "by_county": revenue_by_county,
            "daily_last_30d": daily_revenue,
        },
        "marketplace": {
            "most_ordered": most_ordered,
            "funnel": {
                "posted": funnel_new,
                "assigned": funnel_assigned,
                "confirmed": funnel_confirmed,
                "abandoned": funnel_abandoned,
            },
            "conversion_rate": conversion_rate,
            "abandonment_rate": abandonment_rate,
            "completion_rate": completion_rate,
        },
    }


# ---------- 2. AI BUSINESS INTELLIGENCE ENGINE ----------

async def _build_ai_context() -> dict:
    """Build compact data snapshot to feed Claude."""
    iso_30 = _iso_days_ago(30)
    iso_60 = _iso_days_ago(60)
    # demand by category (last 30d vs prev 30d)
    async def _by_cat(date_range):
        pipe = [
            {"$match": {"created_at": date_range}},
            {"$group": {"_id": "$category", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
        ]
        return [{"category": r["_id"] or "—", "n": r["n"]}
                async for r in db.requests.aggregate(pipe)]

    cur_demand = await _by_cat({"$gte": iso_30})
    prev_demand = await _by_cat({"$gte": iso_60, "$lt": iso_30})

    # county distribution
    by_county_pipe = [
        {"$group": {"_id": "$county", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}}, {"$limit": 20},
    ]
    by_county = [{"county": r["_id"] or "—", "n": r["n"]}
                 async for r in db.requests.aggregate(by_county_pipe)]

    # specialists per category
    spec_per_cat_pipe = [
        {"$match": {"role": "specialist"}},
        {"$group": {"_id": "$specialty", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]
    spec_per_cat = [{"specialty": r["_id"] or "—", "specialists": r["n"]}
                    async for r in db.users.aggregate(spec_per_cat_pipe)]

    # abandonment rate
    total_req = await db.requests.count_documents({})
    abandoned = await db.requests.count_documents({"status": {"$in": ["cancelled", "open"]}})

    return {
        "demand_current_30d": cur_demand[:10],
        "demand_previous_30d": prev_demand[:10],
        "geography_top_counties": by_county[:10],
        "specialists_per_category": spec_per_cat[:15],
        "totals": {
            "total_requests": total_req,
            "abandoned": abandoned,
            "abandonment_rate_pct": round(abandoned / total_req * 100, 1) if total_req else 0,
        },
    }


def _claude_chat(session_id: str, system: str):
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing.")
    from emergentintegrations.llm.chat import LlmChat
    return LlmChat(api_key=key, session_id=session_id, system_message=system)\
        .with_model("anthropic", "claude-sonnet-4-5-20250929")


def _extract_json(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise HTTPException(502, "AI nu a returnat JSON valid.")
    return json.loads(text[i:j + 1])


@router.post("/insights")
async def generate_insights(user=Depends(get_current_user)):
    """Claude analizează datele platformei → insights factuale (română)."""
    _require_marketing(user)
    ctx = await _build_ai_context()
    from emergentintegrations.llm.chat import UserMessage
    system = (
        "Ești AI Business Intelligence Engine pentru PropManage (platformă property "
        "management România). Primești date agregate. Generezi 6-10 INSIGHTS "
        "factuale, scurte, în română, cu metrici numerice (ex: 'Cererea pentru "
        "HVAC a crescut cu X% în ultimele 30 zile'). Răspuns DOAR JSON: "
        "{insights: [{title, body (max 200c), severity ('info'|'warning'|'critical'), "
        "category ('demand'|'geo'|'specialists'|'clients'), metric (string opțional)}]}"
    )
    chat = _claude_chat(f"mkt_bi_{_uuid.uuid4().hex[:8]}", system)
    raw = await chat.send_message(UserMessage(text=json.dumps(ctx, ensure_ascii=False)))
    data = _extract_json(raw)
    items = (data.get("insights") or [])[:12]
    out = {
        "insights": [{
            "title": str(i.get("title") or "")[:120],
            "body": str(i.get("body") or "")[:250],
            "severity": str(i.get("severity") or "info"),
            "category": str(i.get("category") or "demand"),
            "metric": str(i.get("metric") or "")[:80],
        } for i in items],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.get("email"),
    }
    await db.marketing_insights.insert_one(out.copy())
    return out


@router.get("/insights/recent")
async def recent_insights(limit: int = 5, user=Depends(get_current_user)):
    _require_marketing(user)
    cur = db.marketing_insights.find({}).sort("generated_at", -1).limit(min(limit, 20))
    items = []
    async for d in cur:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items, "count": len(items)}


# ---------- 3. AI RECOMMENDATION ENGINE ----------

@router.post("/recommendations")
async def recommendations(user=Depends(get_current_user)):
    _require_marketing(user)
    ctx = await _build_ai_context()
    from emergentintegrations.llm.chat import UserMessage
    system = (
        "Ești AI Recommendation Engine pentru PropManage. Primești date agregate. "
        "Generezi recomandări concrete în română pentru marketing și business. "
        "JSON only: {marketing: [{action, audience, budget_ron (number), "
        "expected_impact (max 100c), priority ('high'|'medium'|'low')}], "
        "business: [{action, why (max 150c), priority}]}"
    )
    chat = _claude_chat(f"mkt_rec_{_uuid.uuid4().hex[:8]}", system)
    raw = await chat.send_message(UserMessage(text=json.dumps(ctx, ensure_ascii=False)))
    data = _extract_json(raw)
    out = {
        "marketing": [{
            "action": str(i.get("action") or "")[:200],
            "audience": str(i.get("audience") or "")[:120],
            "budget_ron": int(i.get("budget_ron") or 0),
            "expected_impact": str(i.get("expected_impact") or "")[:150],
            "priority": str(i.get("priority") or "medium"),
        } for i in (data.get("marketing") or [])[:8]],
        "business": [{
            "action": str(i.get("action") or "")[:200],
            "why": str(i.get("why") or "")[:200],
            "priority": str(i.get("priority") or "medium"),
        } for i in (data.get("business") or [])[:8]],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.get("email"),
    }
    await db.marketing_recommendations.insert_one(out.copy())
    return out


# ---------- 4. MARKETING COPILOT (conversational) ----------

class CopilotMsg(BaseModel):
    session_id: Optional[str] = None
    message: str


@router.post("/copilot")
async def copilot(req: CopilotMsg, user=Depends(get_current_user)):
    _require_marketing(user)
    if not (req.message or "").strip():
        raise HTTPException(400, "Mesaj gol.")
    sid = req.session_id or f"mkt_chat_{_uuid.uuid4().hex[:10]}"
    ctx = await _build_ai_context()
    from emergentintegrations.llm.chat import UserMessage
    system = (
        "Ești AI Marketing Copilot pentru PropManage. Răspunzi STRICT pe baza datelor "
        "agregate primite (date reale platformă, România). Răspunsuri scurte, în română, "
        "cu cifre concrete unde e posibil. Refuzi politicos întrebări non-marketing. "
        f"DATE AGREGATE: {json.dumps(ctx, ensure_ascii=False)}"
    )
    chat = _claude_chat(sid, system)
    raw = await chat.send_message(UserMessage(text=req.message))
    reply = (raw or "").strip()[:2000]

    # persist conversation
    await db.marketing_chat_sessions.update_one(
        {"session_id": sid},
        {"$set": {"updated_at": datetime.now(timezone.utc).isoformat(), "created_by": user.get("email")},
         "$push": {"messages": {"$each": [
             {"role": "user", "text": req.message[:1500], "ts": datetime.now(timezone.utc).isoformat()},
             {"role": "assistant", "text": reply, "ts": datetime.now(timezone.utc).isoformat()},
         ]}}},
        upsert=True,
    )
    return {"session_id": sid, "reply": reply}


@router.get("/copilot/history")
async def copilot_history(session_id: str, user=Depends(get_current_user)):
    _require_marketing(user)
    doc = await db.marketing_chat_sessions.find_one({"session_id": session_id})
    if not doc:
        return {"session_id": session_id, "messages": []}
    return {"session_id": session_id, "messages": doc.get("messages") or []}


# ---------- 5. CUSTOMER SEGMENTATION ----------

@router.get("/segments")
async def segments(user=Depends(get_current_user)):
    _require_marketing(user)
    iso_60 = _iso_days_ago(60)
    iso_30 = _iso_days_ago(30)

    # spend per client
    spend_pipe = [
        {"$match": {"status": "confirmed"}},
        {"$group": {"_id": "$client_id", "spend": {"$sum": "$escrow_amount"}, "n": {"$sum": 1},
                    "last": {"$max": "$confirmed_at"}}},
    ]
    rows = [r async for r in db.requests.aggregate(spend_pipe)]
    spends = [r["spend"] for r in rows] or [0]
    spends.sort()
    p90 = spends[int(len(spends) * 0.9)] if spends else 0
    p70 = spends[int(len(spends) * 0.7)] if spends else 0

    vip = [r for r in rows if r["spend"] >= p90 and p90 > 0]
    premium = [r for r in rows if p70 <= r["spend"] < p90 and p70 > 0]
    active = [r for r in rows if r.get("last", "") >= iso_30]
    inactive = [r for r in rows if r.get("last", "") < iso_60]
    at_risk = [r for r in rows if iso_60 <= r.get("last", "") < iso_30]

    return {
        "buckets": {
            "vip": {"count": len(vip), "label": "VIP (top 10% spend)", "action": "upsell + early access"},
            "premium": {"count": len(premium), "label": "Premium (top 30%)", "action": "cross-sell servicii complementare"},
            "active_30d": {"count": len(active), "label": "Activi (30 zile)", "action": "fidelizare review request"},
            "at_risk": {"count": len(at_risk), "label": "Risc abandon (30-60 zile)", "action": "campanie reactivare"},
            "inactive": {"count": len(inactive), "label": "Inactivi (60+ zile)", "action": "win-back + cupon"},
        },
        "total_clients_with_orders": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------- 6. PREDICTIVE ANALYTICS (forecast) ----------

@router.get("/forecast")
async def forecast(user=Depends(get_current_user)):
    """Linear trend forecast pe baza ultimelor 60 zile."""
    _require_marketing(user)
    iso_60 = _iso_days_ago(60)
    pipe = [
        {"$match": {"status": "confirmed", "confirmed_at": {"$gte": iso_60}}},
        {"$group": {"_id": {"$substr": ["$confirmed_at", 0, 10]},
                    "rev": {"$sum": "$escrow_amount"}, "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    daily = [r async for r in db.requests.aggregate(pipe)]
    if len(daily) < 7:
        return {"history": daily, "forecast_30d": [], "note": "Date insuficiente (< 7 zile)."}

    revs = [r["rev"] for r in daily]
    orders = [r["n"] for r in daily]
    n = len(revs)
    # simple linear regression on revenue
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(revs) / n
    num = sum((xs[i] - mean_x) * (revs[i] - mean_y) for i in range(n))
    den = sum((x - mean_x) ** 2 for x in xs) or 1
    slope = num / den
    intercept = mean_y - slope * mean_x
    avg_orders = statistics.mean(orders) if orders else 0
    forecast = []
    for k in range(1, 31):
        pred_rev = max(0, intercept + slope * (n + k))
        forecast.append({"day": k, "predicted_revenue": round(pred_rev, 2), "predicted_orders": round(avg_orders)})

    total_forecast_30d = sum(f["predicted_revenue"] for f in forecast)
    return {
        "history_last_60d": daily,
        "forecast_30d": forecast,
        "summary": {
            "expected_revenue_next_30d": round(total_forecast_30d, 2),
            "expected_orders_next_30d": round(avg_orders * 30),
            "trend": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
            "trend_slope": round(slope, 2),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------- 7. GROWTH ENGINE ----------

@router.get("/growth")
async def growth(user=Depends(get_current_user)):
    _require_marketing(user)
    iso_30 = _iso_days_ago(30)

    # underserved counties = high demand, low specialist coverage
    demand_pipe = [
        {"$match": {"created_at": {"$gte": iso_30}}},
        {"$group": {"_id": "$county", "demand": {"$sum": 1}}},
        {"$sort": {"demand": -1}},
        {"$limit": 20},
    ]
    demand_by_county = {r["_id"]: r["demand"] async for r in db.requests.aggregate(demand_pipe)}

    spec_pipe = [
        {"$match": {"role": "specialist"}},
        {"$group": {"_id": "$county", "specialists": {"$sum": 1}}},
    ]
    spec_by_county = {r["_id"]: r["specialists"] async for r in db.users.aggregate(spec_pipe)}

    underserved = []
    for county, demand in demand_by_county.items():
        if not county:
            continue
        specs = spec_by_county.get(county, 0)
        ratio = round(demand / specs, 1) if specs else demand
        if ratio >= 3 or specs == 0:
            underserved.append({
                "county": county,
                "demand_30d": demand,
                "specialists": specs,
                "demand_per_specialist": ratio,
                "opportunity": "Recrutare specialiști" if specs > 0 else "Lansare oraș nou",
            })
    underserved.sort(key=lambda x: -x["demand_per_specialist"])

    # high-growth categories (last 30d vs prev 30d)
    async def _cat_count(start, end):
        pipe = [{"$match": {"created_at": {"$gte": start, "$lt": end} if end else {"$gte": start}}},
                {"$group": {"_id": "$category", "n": {"$sum": 1}}}]
        return {r["_id"]: r["n"] async for r in db.requests.aggregate(pipe)}

    cur = await _cat_count(iso_30, None)
    prev = await _cat_count(_iso_days_ago(60), iso_30)
    high_growth = []
    for cat, n in cur.items():
        if not cat:
            continue
        p = prev.get(cat, 0)
        if p >= 3 and n > p:
            growth_pct = round((n - p) / p * 100, 1)
            if growth_pct >= 20:
                high_growth.append({"category": cat, "current": n, "previous": p, "growth_pct": growth_pct})
    high_growth.sort(key=lambda x: -x["growth_pct"])

    return {
        "underserved_geo": underserved[:10],
        "high_growth_categories": high_growth[:8],
        "new_markets_suggested": [u for u in underserved if u["specialists"] == 0][:5],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------- 8. FUTURE IDEAS (Faza 2 + 3 backlog) ----------

FUTURE_IDEAS_CATALOG = [
    {
        "phase": "Faza 2 — Content & Automation",
        "items": [
            {"id": "social_studio", "title": "Social Media AI Studio",
             "description": "Generare AI postări, carusele, stories, reels, scripturi video pentru Facebook/Instagram/LinkedIn/TikTok/YouTube. 3 variante + scor impact.",
             "priority": "P1", "effort_days": 5},
            {"id": "content_calendar", "title": "AI Content Calendar",
             "description": "Calendar editorial lunar/săptămânal auto-generat cu zile internaționale relevante + workflow aprobare.",
             "priority": "P1", "effort_days": 3},
            {"id": "campaign_generator", "title": "AI Campaign Generator",
             "description": "Selectezi obiectiv+serviciu+oraș+buget → AI generează avatar client, audiență, texte ads, imagini recomandate, KPI estimați.",
             "priority": "P1", "effort_days": 4},
            {"id": "automation_center", "title": "AI Automation Center",
             "description": "Automatizări email: welcome, review request, reactivare, abandon order, onboarding specialist, newsletter sezonier.",
             "priority": "P1", "effort_days": 4},
            {"id": "seo_engine", "title": "SEO AI Engine",
             "description": "Generare articole SEO, meta titles/descriptions, FAQ schema, pagini locale (oraș + serviciu).",
             "priority": "P2", "effort_days": 4},
        ],
    },
    {
        "phase": "Faza 3 — External Integrations",
        "items": [
            {"id": "meta_ads", "title": "Meta Ads API Integration",
             "description": "OAuth Meta + analiză CPC/CPM/CTR/CPA/ROAS + recomandări scalare/oprire campanii.",
             "priority": "P2", "effort_days": 7, "requires_keys": ["META_APP_ID", "META_APP_SECRET"]},
            {"id": "google_ads", "title": "Google Ads + Analytics + GTM",
             "description": "OAuth Google + dashboard CPC/cost per lead/ROAS unificat.",
             "priority": "P2", "effort_days": 7, "requires_keys": ["GOOGLE_ADS_DEV_TOKEN", "GOOGLE_OAUTH_CLIENT"]},
            {"id": "social_connectors", "title": "Social Media Connectors",
             "description": "Conectare Facebook Pages / Instagram Business / LinkedIn / TikTok Business / YouTube. Programare + publicare automată + draft + aprobare.",
             "priority": "P2", "effort_days": 8},
            {"id": "brand_monitoring", "title": "Brand Monitoring",
             "description": "Social listening, sentiment analysis, monitorizare concurență.",
             "priority": "P3", "effort_days": 6},
        ],
    },
    {
        "phase": "Faza 4 — Enterprise Hardening",
        "items": [
            {"id": "multi_tenant", "title": "Multi-Tenant Architecture",
             "description": "tenant_id pe toate documentele + izolare DB + sub-domenii per tenant.",
             "priority": "P3", "effort_days": 14},
            {"id": "microservices", "title": "Microservices Split",
             "description": "Separare BI engine + AI workers + queue jobs în servicii dedicate.",
             "priority": "P3", "effort_days": 21},
            {"id": "image_studio", "title": "AI Image Studio (Gemini Nano Banana)",
             "description": "Generare imagini sociale + reclame + thumbnails cu Gemini Nano Banana.",
             "priority": "P1", "effort_days": 3},
        ],
    },
]


@router.get("/future-ideas")
async def future_ideas(user=Depends(get_current_user)):
    _require_marketing(user)
    return {"phases": FUTURE_IDEAS_CATALOG, "generated_at": datetime.now(timezone.utc).isoformat()}


# ---------- 9. RECENT RECOMMENDATIONS (feed) ----------

@router.get("/recommendations/recent")
async def recent_recommendations(limit: int = 5, user=Depends(get_current_user)):
    _require_marketing(user)
    cur = db.marketing_recommendations.find({}).sort("generated_at", -1).limit(min(limit, 20))
    items = []
    async for d in cur:
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items, "count": len(items)}
