"""Marketing Performance Loop — Closed Feedback System.

Track actual campaign results (impressions/clicks/leads/spent) vs AI-predicted KPIs.
Claude analyzes historical accuracy → generates calibration learnings.
Future campaign drafts inject learnings into system prompt → continuous improvement.

Endpoints (super_admin / marketing_manager):
  POST /api/admin/marketing/campaigns/{id}/performance        — log actual results
  GET  /api/admin/marketing/campaigns/{id}/performance        — get all logs for campaign
  POST /api/admin/marketing/campaigns/{id}/complete           — mark as completed
  GET  /api/admin/marketing/performance/summary               — aggregate dashboard
  POST /api/admin/marketing/performance/learnings/generate    — Claude → calibration insights
  GET  /api/admin/marketing/performance/learnings/active      — active learnings (used by generator)

Collection: marketing_performance_logs
  { campaign_id, impressions, clicks, leads, conversions, spent_ron,
    started_at, ended_at, notes, deltas{}, logged_at, logged_by }

Collection: marketing_performance_learnings
  { generated_at, learnings: [{category, metric, observation, adjustment, confidence}],
    sample_size, period_days, generated_by, active: true }
"""
import json
import logging
import os
import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from routes.marketing_growth import _require_marketing

logger = logging.getLogger("propmanage.marketing_performance")
router = APIRouter(prefix="/api/admin/marketing", tags=["admin-marketing-performance"])


# ---------- Helpers ----------

def _safe_div(a, b):
    return round(a / b, 2) if b else 0


def _compute_deltas(predicted: dict, actual: dict) -> dict:
    """Compare actual vs predicted KPIs. Positive delta = actual exceeded prediction."""
    deltas = {}
    pairs = [
        ("impressions", "expected_impressions"),
        ("clicks", "expected_clicks"),
        ("leads", "expected_leads"),
    ]
    for a_key, p_key in pairs:
        p = float(predicted.get(p_key) or 0)
        a = float(actual.get(a_key) or 0)
        if p > 0:
            deltas[f"{a_key}_delta_pct"] = round((a - p) / p * 100, 1)
            deltas[f"{a_key}_predicted"] = p
            deltas[f"{a_key}_actual"] = a
    # CPC = spent / clicks (compare vs expected_cpc_ron)
    actual_cpc = _safe_div(float(actual.get("spent_ron") or 0), float(actual.get("clicks") or 0))
    predicted_cpc = float(predicted.get("expected_cpc_ron") or 0)
    if predicted_cpc > 0:
        deltas["cpc_actual_ron"] = actual_cpc
        deltas["cpc_predicted_ron"] = predicted_cpc
        deltas["cpc_delta_pct"] = round((actual_cpc - predicted_cpc) / predicted_cpc * 100, 1)
    # CPL = spent / leads
    cpl = _safe_div(float(actual.get("spent_ron") or 0), float(actual.get("leads") or 0))
    deltas["cpl_actual_ron"] = cpl
    return deltas


def _serialize_log(d: dict) -> dict:
    return {
        "id": str(d.get("_id")),
        "campaign_id": d.get("campaign_id"),
        "impressions": d.get("impressions"),
        "clicks": d.get("clicks"),
        "leads": d.get("leads"),
        "conversions": d.get("conversions"),
        "spent_ron": d.get("spent_ron"),
        "started_at": d.get("started_at"),
        "ended_at": d.get("ended_at"),
        "notes": d.get("notes"),
        "deltas": d.get("deltas") or {},
        "logged_at": d.get("logged_at"),
        "logged_by": d.get("logged_by"),
    }


# ---------- Models ----------

class PerformanceLog(BaseModel):
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    leads: int = Field(ge=0)
    conversions: int = Field(ge=0, default=0)
    spent_ron: float = Field(ge=0)
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    notes: Optional[str] = None


# ---------- 1. Log performance ----------

@router.post("/campaigns/{cid}/performance")
async def log_performance(cid: str, req: PerformanceLog, user=Depends(get_current_user)):
    _require_marketing(user)
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(400, "ID campanie invalid.")
    campaign = await db.marketing_campaigns.find_one({"_id": oid}, {"images": 0})
    if not campaign:
        raise HTTPException(404, "Campanie inexistentă.")
    if campaign.get("status") not in {"approved", "completed"}:
        raise HTTPException(400, "Performanța se poate loga doar pentru campanii aprobate sau finalizate.")

    deltas = _compute_deltas(campaign.get("kpis") or {}, req.model_dump())
    doc = {
        "campaign_id": cid,
        "service_category": campaign.get("service_category"),
        "county": campaign.get("county"),
        "objective": campaign.get("objective"),
        "impressions": req.impressions,
        "clicks": req.clicks,
        "leads": req.leads,
        "conversions": req.conversions,
        "spent_ron": req.spent_ron,
        "started_at": req.started_at,
        "ended_at": req.ended_at,
        "notes": (req.notes or "")[:500],
        "deltas": deltas,
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "logged_by": user.get("email"),
    }
    res = await db.marketing_performance_logs.insert_one(doc)
    doc["_id"] = res.inserted_id
    # Update campaign with last performance summary
    await db.marketing_campaigns.update_one(
        {"_id": oid},
        {"$set": {"last_performance": {
            "impressions": req.impressions, "clicks": req.clicks,
            "leads": req.leads, "spent_ron": req.spent_ron,
            "logged_at": doc["logged_at"],
        }}},
    )
    return _serialize_log(doc)


@router.get("/campaigns/{cid}/performance")
async def get_performance(cid: str, user=Depends(get_current_user)):
    _require_marketing(user)
    cur = db.marketing_performance_logs.find({"campaign_id": cid}).sort("logged_at", -1)
    items = [_serialize_log(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.post("/campaigns/{cid}/complete")
async def mark_completed(cid: str, user=Depends(get_current_user)):
    _require_marketing(user)
    try:
        oid = ObjectId(cid)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    res = await db.marketing_campaigns.update_one(
        {"_id": oid, "status": "approved"},
        {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat(),
                  "completed_by": user.get("email")}},
    )
    if not res.matched_count:
        raise HTTPException(400, "Doar campaniile aprobate pot fi marcate finalizate.")
    return {"ok": True, "status": "completed"}


# ---------- 2. Aggregate summary ----------

@router.get("/performance/summary")
async def performance_summary(user=Depends(get_current_user)):
    _require_marketing(user)

    total_logs = await db.marketing_performance_logs.count_documents({})
    if total_logs == 0:
        return {
            "logs_count": 0,
            "totals": {"spent_ron": 0, "leads": 0, "clicks": 0, "impressions": 0},
            "accuracy": {},
            "top_performers": [],
            "worst_performers": [],
            "by_category": [],
            "note": "Niciun log de performanță încă. Logați rezultate reale pentru campaniile aprobate.",
        }

    # totals
    agg_pipe = [
        {"$group": {"_id": None,
                    "spent": {"$sum": "$spent_ron"},
                    "leads": {"$sum": "$leads"},
                    "clicks": {"$sum": "$clicks"},
                    "impressions": {"$sum": "$impressions"},
                    "conversions": {"$sum": "$conversions"}}},
    ]
    totals = {"spent_ron": 0, "leads": 0, "clicks": 0, "impressions": 0, "conversions": 0}
    async for r in db.marketing_performance_logs.aggregate(agg_pipe):
        totals = {
            "spent_ron": round(r.get("spent", 0), 2),
            "leads": r.get("leads", 0),
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "conversions": r.get("conversions", 0),
        }

    # accuracy — avg absolute delta_pct across logs
    deltas_pipe = [
        {"$project": {
            "imp_d": {"$abs": "$deltas.impressions_delta_pct"},
            "clk_d": {"$abs": "$deltas.clicks_delta_pct"},
            "lead_d": {"$abs": "$deltas.leads_delta_pct"},
            "cpc_d": {"$abs": "$deltas.cpc_delta_pct"},
        }},
        {"$group": {"_id": None,
                    "imp": {"$avg": "$imp_d"}, "clk": {"$avg": "$clk_d"},
                    "lead": {"$avg": "$lead_d"}, "cpc": {"$avg": "$cpc_d"}}},
    ]
    accuracy = {}
    async for r in db.marketing_performance_logs.aggregate(deltas_pipe):
        accuracy = {
            "impressions_avg_abs_delta_pct": round(r.get("imp") or 0, 1),
            "clicks_avg_abs_delta_pct": round(r.get("clk") or 0, 1),
            "leads_avg_abs_delta_pct": round(r.get("lead") or 0, 1),
            "cpc_avg_abs_delta_pct": round(r.get("cpc") or 0, 1),
        }

    # top + worst by lead delta (most leads vs predicted = best)
    cur = db.marketing_performance_logs.find({}).sort([("deltas.leads_delta_pct", -1)]).limit(3)
    top = [_serialize_log(d) async for d in cur]
    cur = db.marketing_performance_logs.find({}).sort([("deltas.leads_delta_pct", 1)]).limit(3)
    worst = [_serialize_log(d) async for d in cur]

    # by category
    cat_pipe = [
        {"$group": {"_id": "$service_category",
                    "leads": {"$sum": "$leads"}, "spent": {"$sum": "$spent_ron"},
                    "n": {"$sum": 1}}},
        {"$sort": {"leads": -1}}, {"$limit": 10},
    ]
    by_category = []
    async for r in db.marketing_performance_logs.aggregate(cat_pipe):
        by_category.append({
            "category": r["_id"] or "—",
            "leads": r["leads"],
            "spent_ron": round(r["spent"], 2),
            "cpl_ron": _safe_div(r["spent"], r["leads"]),
            "campaigns_count": r["n"],
        })

    return {
        "logs_count": total_logs,
        "totals": totals,
        "accuracy": accuracy,
        "top_performers": top,
        "worst_performers": worst,
        "by_category": by_category,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------- 3. Generate learnings (Claude) ----------

@router.post("/performance/learnings/generate")
async def generate_learnings(user=Depends(get_current_user)):
    _require_marketing(user)
    # Build context: top 30 most recent logs with category + objective + deltas
    cur = db.marketing_performance_logs.find({}, {
        "service_category": 1, "county": 1, "objective": 1, "deltas": 1,
        "impressions": 1, "clicks": 1, "leads": 1, "spent_ron": 1,
    }).sort("logged_at", -1).limit(30)
    logs = [{
        "category": d.get("service_category"),
        "county": d.get("county"),
        "objective": d.get("objective"),
        "actual": {"impressions": d.get("impressions"), "clicks": d.get("clicks"),
                   "leads": d.get("leads"), "spent_ron": d.get("spent_ron")},
        "deltas": d.get("deltas") or {},
    } async for d in cur]

    if len(logs) < 3:
        raise HTTPException(400, "Insuficiente date (necesare minim 3 loguri de performanță).")

    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY missing.")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    system = (
        "Ești un AI Marketing Performance Analyst pentru PropManage. Primești "
        "loguri istorice ale campaniilor cu predicted vs actual. Identifici "
        "tipare sistematice de eroare în predicții și generezi ÎNVĂȚĂMINTE de "
        "calibrare (ajustări) pentru campaniile viitoare. Răspuns DOAR JSON: "
        "{learnings: [{category (sau '*' pentru general), metric ('cpc'|'leads'|"
        "'clicks'|'impressions'|'cpl'), observation (max 200c, română), "
        "adjustment (max 150c, ex: 'Crește expected_cpc_ron cu +18% pentru HVAC'), "
        "confidence ('high'|'medium'|'low'), sample_size (number)}]}"
    )
    chat = LlmChat(api_key=key, session_id=f"perf_{_uuid.uuid4().hex[:8]}", system_message=system)\
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    raw = await chat.send_message(UserMessage(text=json.dumps(logs, ensure_ascii=False)))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise HTTPException(502, "AI nu a returnat JSON valid.")
    data = json.loads(text[i:j + 1])

    # Deactivate previous learnings
    await db.marketing_performance_learnings.update_many(
        {"active": True}, {"$set": {"active": False}},
    )
    doc = {
        "learnings": [{
            "category": str(l.get("category") or "*")[:80],
            "metric": str(l.get("metric") or "")[:30],
            "observation": str(l.get("observation") or "")[:250],
            "adjustment": str(l.get("adjustment") or "")[:200],
            "confidence": str(l.get("confidence") or "medium"),
            "sample_size": int(l.get("sample_size") or 0),
        } for l in (data.get("learnings") or [])[:12]],
        "sample_size": len(logs),
        "active": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": user.get("email"),
    }
    await db.marketing_performance_learnings.insert_one(doc)
    return {
        "learnings": doc["learnings"],
        "sample_size": doc["sample_size"],
        "generated_at": doc["generated_at"],
        "message": f"Învățăminte regenerate pe baza a {len(logs)} loguri. Vor fi aplicate automat la următoarele drafts.",
    }


@router.get("/performance/learnings/active")
async def active_learnings(user=Depends(get_current_user)):
    _require_marketing(user)
    doc = await db.marketing_performance_learnings.find_one({"active": True})
    if not doc:
        return {"learnings": [], "active": False}
    return {
        "id": str(doc["_id"]),
        "learnings": doc.get("learnings") or [],
        "sample_size": doc.get("sample_size"),
        "generated_at": doc.get("generated_at"),
        "active": True,
    }


# ---------- 4. Helper for generator integration ----------

async def get_active_calibration_hint() -> Optional[str]:
    """Return human-readable calibration string to inject into draft generator system prompt."""
    doc = await db.marketing_performance_learnings.find_one({"active": True})
    if not doc or not doc.get("learnings"):
        return None
    lines = ["CALIBRARE BAZATĂ PE PERFORMANȚE ISTORICE (aplică ajustările)::"]
    for l in doc["learnings"][:8]:
        cat = l.get("category") or "*"
        lines.append(f"- [{cat}/{l.get('metric')}] {l.get('observation')} → {l.get('adjustment')} (confidence={l.get('confidence')})")
    return "\n".join(lines)
