"""Marketplace Intelligence — demand vs supply per category with deficit %.

Demand = requests in the last 30d (fallback 90d if sparse). Supply = active
specialists per specialty, capacity = supply × JOBS_PER_SPECIALIST_MONTH.
AI recommends where to invest (recruiting vs demand generation).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/marketplace-intel", tags=["marketplace-intel"])
logger = logging.getLogger("propmanage.marketplace_intel")

JOBS_PER_SPECIALIST_MONTH = 4

# Normalize seeded variants to canonical categories.
CATEGORY_ALIASES = {
    "electrical": "electric", "hvac": "hvac", "HVAC": "hvac", "ventilatie": "hvac",
    "zugravit": "handyman", "general": "handyman",
}
CATEGORY_LABELS = {
    "electric": "Electricieni", "hvac": "HVAC & Climatizare", "plumbing": "Instalatori",
    "interior_design": "Design Interior", "handyman": "Handyman & Reparații",
}


def _canon(cat: str | None) -> str | None:
    if not cat:
        return None
    c = cat.strip()
    return CATEGORY_ALIASES.get(c, CATEGORY_ALIASES.get(c.lower(), c.lower()))


async def _build_supply_demand() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    d30 = (now - timedelta(days=30)).isoformat()
    d90 = (now - timedelta(days=90)).isoformat()

    demand: dict[str, int] = {}
    window = "30 zile"
    count_30 = await db.requests.count_documents({"created_at": {"$gte": d30}})
    date_filter = {"$gte": d30} if count_30 >= 10 else {"$gte": d90}
    if count_30 < 10:
        window = "90 zile"
    async for r in db.requests.find({"created_at": date_filter}, {"category": 1}):
        c = _canon(r.get("category"))
        if c:
            demand[c] = demand.get(c, 0) + 1

    supply: dict[str, int] = {}
    async for u in db.users.find({"role": "specialist"}, {"specialty": 1}):
        c = _canon(u.get("specialty"))
        if c:
            supply[c] = supply.get(c, 0) + 1

    categories = []
    for cat in sorted(set(demand) | set(supply)):
        d = demand.get(cat, 0)
        s = supply.get(cat, 0)
        capacity = s * JOBS_PER_SPECIALIST_MONTH
        if d > capacity:
            status = "deficit"
            pct = round((d - capacity) / d * 100)
        elif capacity > d * 2 and s > 0:
            status = "surplus"
            pct = round((capacity - d) / capacity * 100)
        else:
            status = "balanced"
            pct = 0
        categories.append({
            "key": cat,
            "label": CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()),
            "demand": d,
            "supply": s,
            "capacity": capacity,
            "status": status,
            "pct": pct,
        })
    categories.sort(key=lambda c: (-1 if c["status"] == "deficit" else 1, -c["pct"], -c["demand"]))
    return {
        "categories": categories,
        "window": window,
        "jobs_per_specialist": JOBS_PER_SPECIALIST_MONTH,
        "generated_at": now.isoformat(),
    }


@router.get("/supply-demand")
async def supply_demand(_admin=Depends(require_role("admin"))):
    return await _build_supply_demand()


@router.post("/recommend")
async def recommend(_admin=Depends(require_role("admin"))):
    data = await _build_supply_demand()
    rows = "\n".join(
        f"- {c['label']}: cerere={c['demand']} · specialiști={c['supply']} · capacitate={c['capacity']} · {c['status']} {c['pct']}%"
        for c in data["categories"]
    )
    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești strategul de marketplace al PropManage (servicii property România). Primești balanța "
            "cerere vs ofertă per categorie și recomanzi UNDE să investească adminul: recrutare specialiști "
            "pentru deficit, generare cerere pentru supraofertă. Răspunde STRICT JSON: "
            "{\"summary\": str RO ≤250c, \"recommendations\": [{\"category\": str, \"action\": str RO ≤140c, "
            "\"type\": \"recruit|promote|monitor\", \"priority\": \"high|medium|low\"}]}. Max 5, concrete."
        )
        result = await claude_json(system=system, prompt=f"Fereastră: {data['window']}.\n{rows}", session_prefix="mkt-intel")
        payload = {
            "summary": str(result.get("summary") or "")[:300],
            "recommendations": [
                {
                    "category": str(r.get("category") or "")[:60],
                    "action": str(r.get("action") or "")[:180],
                    "type": r.get("type") if r.get("type") in ("recruit", "promote", "monitor") else "monitor",
                    "priority": r.get("priority") if r.get("priority") in ("high", "medium", "low") else "medium",
                }
                for r in (result.get("recommendations") or [])[:5] if isinstance(r, dict) and r.get("action")
            ],
            "ai_generated": True,
        }
        if not payload["recommendations"]:
            raise ValueError("Zero recomandări")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[mkt-intel] LLM fail: {e} — fallback")
        deficits = [c for c in data["categories"] if c["status"] == "deficit"]
        payload = {
            "summary": "Analiză rule-based (LLM indisponibil). Recrutează pe categoriile cu deficit.",
            "recommendations": [
                {"category": c["label"], "action": f"Recrutează specialiști — deficit {c['pct']}% ({c['demand']} cereri vs capacitate {c['capacity']})",
                 "type": "recruit", "priority": "high"}
                for c in deficits[:5]
            ],
            "ai_generated": False,
        }

    doc = {"generated_at": datetime.now(timezone.utc).isoformat(), **payload}
    await db.marketplace_intel_recos.update_one({"_id": "latest"}, {"$set": doc}, upsert=True)
    return doc


@router.get("/recommend/latest")
async def latest_recommend(_admin=Depends(require_role("admin"))):
    doc = await db.marketplace_intel_recos.find_one({"_id": "latest"}, {"_id": 0})
    return doc or {"recommendations": None}


@router.get("/by-county")
async def by_county(_admin=Depends(require_role("admin"))):
    """Demand vs supply per county — requires county on requests + specialists."""
    now = datetime.now(timezone.utc)
    d90 = (now - timedelta(days=90)).isoformat()

    demand: dict[str, int] = {}
    async for r in db.requests.find({"created_at": {"$gte": d90}, "county": {"$nin": [None, ""]}}, {"county": 1}):
        demand[r["county"]] = demand.get(r["county"], 0) + 1

    supply: dict[str, int] = {}
    async for u in db.users.find({"role": "specialist", "county": {"$nin": [None, ""]}}, {"county": 1}):
        supply[u["county"]] = supply.get(u["county"], 0) + 1

    counties = []
    for county in sorted(set(demand) | set(supply)):
        d = demand.get(county, 0)
        s = supply.get(county, 0)
        capacity = s * JOBS_PER_SPECIALIST_MONTH * 3  # fereastră 90z ≈ 3 luni
        if d > capacity:
            status = "deficit"
            pct = round((d - capacity) / d * 100)
        elif capacity > d * 2 and s > 0:
            status = "surplus"
            pct = round((capacity - d) / capacity * 100)
        else:
            status = "balanced"
            pct = 0
        counties.append({"county": county, "demand": d, "supply": s, "capacity": capacity, "status": status, "pct": pct})
    counties.sort(key=lambda c: (-1 if c["status"] == "deficit" else 1, -c["pct"], -c["demand"]))
    return {"counties": counties, "window": "90 zile", "generated_at": now.isoformat()}


@router.get("/radar")
async def marketplace_radar(_admin=Depends(require_role("admin"))):
    """Marketplace Radar (modulul 8) — trenduri ±% pe 30 zile vs 30 anterioare, per categorie."""
    now = datetime.now(timezone.utc)
    d30 = (now - timedelta(days=30)).isoformat()
    d60 = (now - timedelta(days=60)).isoformat()

    cur: dict[str, int] = {}
    prev: dict[str, int] = {}
    async for r in db.requests.find({"created_at": {"$gte": d60}}, {"category": 1, "created_at": 1}):
        c = _canon(r.get("category"))
        if not c:
            continue
        if r["created_at"] >= d30:
            cur[c] = cur.get(c, 0) + 1
        else:
            prev[c] = prev.get(c, 0) + 1

    trends = []
    for cat in sorted(set(cur) | set(prev)):
        c_now, c_prev = cur.get(cat, 0), prev.get(cat, 0)
        if c_prev:
            pct = round((c_now - c_prev) / c_prev * 100)
        else:
            pct = 100 if c_now else 0
        trends.append({
            "key": cat,
            "label": CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()),
            "current_30d": c_now,
            "previous_30d": c_prev,
            "trend_pct": pct,
            "direction": "up" if pct > 5 else "down" if pct < -5 else "flat",
            "hot": pct >= 30 and c_now >= 3,
        })
    trends.sort(key=lambda t: -t["trend_pct"])
    return {"trends": trends, "hot_count": sum(1 for t in trends if t["hot"]), "generated_at": now.isoformat()}
