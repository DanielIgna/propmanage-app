"""AI Insights v2 — analiză LLM (Claude) per modul, cu cache 6h (control cost).

GET /api/admin/insights/llm?module={analytics|finance|marketplace|overview|control_tower}
Returnează {bullets, alerts, recommendations, generated_at, cached}.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/insights", tags=["ai-insights"])
logger = logging.getLogger("propmanage.ai_insights")

CACHE_HOURS = 6
MODULES = {"analytics", "finance", "marketplace", "overview", "control_tower", "users", "bi", "ai_control", "governance"}


async def _users_stats() -> dict:
    by_role = {}
    async for row in db.users.aggregate([{"$group": {"_id": "$role", "n": {"$sum": 1}}}]):
        by_role[row["_id"] or "—"] = row["n"]
    total = sum(by_role.values())
    since7 = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    return {
        "total": total,
        "by_role": by_role,
        "new_7d": await db.users.count_documents({"created_at": {"$gte": since7}}),
        "email_verified": await db.users.count_documents({"email_verified": True}),
        "banned": await db.users.count_documents({"banned": True}),
    }


async def _bi_stats() -> dict:
    since30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    new_30d = await db.requests.count_documents({"created_at": {"$gte": since30}})
    done_30d = await db.requests.count_documents({"status": {"$in": ["completed", "confirmed"]}, "created_at": {"$gte": since30}})
    return {
        "open_requests": await db.requests.count_documents({"status": "open"}),
        "active_jobs": await db.requests.count_documents({"status": {"$in": ["accepted", "in_progress"]}}),
        "new_requests_30d": new_30d,
        "completed_30d": done_30d,
        "completion_rate_pct": round(done_30d / new_30d * 100, 1) if new_30d else 0,
        "disputes_open": await db.disputes.count_documents({"status": "open"}),
    }


async def _ai_control_stats(user: dict) -> dict:
    from routes.ai_control import overview as ai_overview
    d = await ai_overview(admin=user)
    return {
        "provider": d["config"].get("provider"),
        "model": d["config"].get("model"),
        "ecosystem_enabled": bool(d["config"].get("enabled")),
        "memories_total": d["memory"].get("total", 0),
        "bugs_total": d["bugs"].get("total", 0),
        "agents_active": len([a for a in d["agents"] if a["status"] == "active"]),
        "agents_total": len(d["agents"]),
    }


async def _governance_stats(user: dict) -> dict:
    from routes.ai_governance import get_summary
    s = await get_summary(user=user)
    return {
        "agents_active": (s.get("by_lifecycle") or {}).get("active", 0),
        "agents_legacy": (s.get("by_lifecycle") or {}).get("legacy", 0),
        "agents_deprecated": (s.get("by_lifecycle") or {}).get("deprecated", 0),
        "activity_24h": s.get("global_activity_24h", 0),
        "activity_7d": s.get("global_activity_7d", 0),
        "phase": s.get("phase"),
    }


async def _context_for(module: str, user: dict) -> dict:
    if module == "analytics":
        from routes.analytics_growth import analytics_overview
        d = await analytics_overview("week", "", "", user)
        return {"kpi": d["kpi"], "kpi_prev": d.get("kpi_prev"), "sources": d["sources"][:5], "funnel": d["funnel"]}
    if module == "finance":
        total_wallet = 0
        async for row in db.users.aggregate([{"$group": {"_id": None, "s": {"$sum": "$wallet_balance"}}}]):
            total_wallet = row["s"]
        tx = []
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        async for row in db.transactions.aggregate([
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}, "total": {"$sum": "$amount"}}},
        ]):
            tx.append({"type": row["_id"], "count": row["count"], "total": row["total"]})
        return {"total_wallet": total_wallet, "tx_by_type_30d": tx}
    if module == "marketplace":
        by_status = {}
        async for row in db.marketplace_partners.aggregate([{"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
            by_status[row["_id"]] = row["n"]
        leads = await db.partner_leads.count_documents({})
        return {"partners_by_status": by_status, "total_leads": leads}
    if module == "overview" or module == "control_tower":
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        ledger = await db.orchestrator_ledger.find({"test": {"$ne": True}, "ts": {"$gte": since}}, {"_id": 0, "playbook_name": 1, "escalated": 1}).to_list(1000)
        by_pb = {}
        for x in ledger:
            k = x.get("playbook_name") or "—"
            by_pb.setdefault(k, {"runs": 0, "escalated": 0})
            by_pb[k]["runs"] += 1
            by_pb[k]["escalated"] += 1 if x.get("escalated") else 0
        return {
            "pulse": {
                "open_requests": await db.requests.count_documents({"status": "open"}),
                "active_jobs": await db.requests.count_documents({"status": {"$in": ["accepted", "in_progress"]}}),
                "kyc_pending": await db.users.count_documents({"kyc_status": "pending"}),
                "disputes_open": await db.disputes.count_documents({"status": "open"}),
            },
            "playbook_activity_7d": by_pb,
        }
    if module == "users":
        return await _users_stats()
    if module == "bi":
        return await _bi_stats()
    if module == "ai_control":
        return await _ai_control_stats(user)
    if module == "governance":
        return await _governance_stats(user)
    return {}


@router.get("/rule")
async def rule_insights(module: str, user=Depends(require_role("admin"))):
    """Insights rule-based (fără LLM) pentru modulele Users și BI — instant, cost zero."""
    if module == "users":
        s = await _users_stats()
        rate = round(s["email_verified"] / s["total"] * 100) if s["total"] else 0
        bullets = [
            f"{s['total']} utilizatori: {s['by_role'].get('client', 0)} clienți · {s['by_role'].get('specialist', 0)} specialiști · {s['by_role'].get('operator', 0)} operatori · {s['by_role'].get('admin', 0)} admini.",
            f"{s['new_7d']} utilizatori noi în ultimele 7 zile.",
            f"{rate}% dintre conturi au emailul verificat.",
        ]
        alerts = []
        if s["total"] and rate < 50:
            alerts.append(f"Rata de verificare email e sub 50% ({rate}%) — mulți useri nu primesc notificări.")
        if s["banned"]:
            bullets.append(f"{s['banned']} conturi banate.")
        recommendations = []
        if s["new_7d"] == 0:
            recommendations.append("Zero useri noi săptămâna asta — verifică funnel-ul de achiziție în Analytics & Growth.")
        if rate < 70 and s["total"]:
            recommendations.append("Trimite o campanie de re-verificare email către conturile neverificate.")
        return {"bullets": bullets, "alerts": alerts, "recommendations": recommendations}
    if module == "bi":
        s = await _bi_stats()
        bullets = [
            f"{s['new_requests_30d']} cereri noi în 30 zile, {s['completed_30d']} finalizate ({s['completion_rate_pct']}% completion rate).",
            f"{s['open_requests']} cereri deschise · {s['active_jobs']} lucrări active acum.",
        ]
        alerts = []
        if s["disputes_open"]:
            alerts.append(f"{s['disputes_open']} dispute deschise — necesită mediere.")
        if s["new_requests_30d"] >= 5 and s["completion_rate_pct"] < 30:
            alerts.append(f"Completion rate scăzut ({s['completion_rate_pct']}%) — multe cereri rămân nefinalizate.")
        recommendations = []
        if s["open_requests"] > s["active_jobs"] * 2 and s["open_requests"] > 5:
            recommendations.append("Cereri deschise mult peste lucrările active — verifică oferta de specialiști pe categoriile cerute (tab Demand Index).")
        return {"bullets": bullets, "alerts": alerts, "recommendations": recommendations}
    if module == "ai_control":
        s = await _ai_control_stats(user)
        bullets = [
            f"Model activ: {s['model']} ({s['provider']}) · {s['agents_active']}/{s['agents_total']} agenți activi.",
            f"{s['memories_total']} amintiri salvate în memoria cross-session · {s['bugs_total']} bug-uri indexate în istoricul de căutare.",
        ]
        alerts = []
        if not s["ecosystem_enabled"]:
            alerts.append("Ecosistemul de memorie AI este DEZACTIVAT — agenții nu rețin context între sesiuni.")
        recommendations = []
        if s["bugs_total"] == 0:
            recommendations.append("Rulează QA Playbook ca să populezi Bug Memory — căutarea AI devine utilă cu istoric.")
        return {"bullets": bullets, "alerts": alerts, "recommendations": recommendations}
    if module == "governance":
        s = await _governance_stats(user)
        bullets = [
            f"{s['agents_active']} agenți activi · {s['agents_legacy']} legacy · {s['agents_deprecated']} depreciati.",
            f"Activitate ecosistem: {s['activity_24h']} acțiuni în 24h · {s['activity_7d']} în 7 zile.",
            f"Fază curentă: {s['phase']}.",
        ]
        alerts = []
        if s["activity_7d"] > 0 and s["activity_24h"] > s["activity_7d"] / 7 * 3:
            alerts.append(f"Vârf de activitate AI: {s['activity_24h']} acțiuni/24h vs media zilnică ~{round(s['activity_7d'] / 7)} — verifică costurile.")
        recommendations = []
        if s["agents_legacy"] > 0:
            recommendations.append(f"{s['agents_legacy']} agenți legacy — planifică migrarea sau deprecation cu dată-țintă (Art. 3 din Constituție).")
        return {"bullets": bullets, "alerts": alerts, "recommendations": recommendations}
    raise HTTPException(400, "Modul necunoscut. Valide: users, bi, ai_control, governance")


@router.get("/llm")
async def llm_insights(module: str, force: bool = False, user=Depends(require_role("admin"))):
    if module not in MODULES:
        raise HTTPException(400, f"Modul necunoscut. Valide: {sorted(MODULES)}")

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CACHE_HOURS)).isoformat()
    if not force:
        cached = await db.ai_insights_cache.find_one({"module": module, "generated_at": {"$gte": cutoff}}, {"_id": 0})
        if cached:
            return {**cached["result"], "generated_at": cached["generated_at"], "cached": True}

    context = await _context_for(module, user)
    try:
        from orchestrator.llm import claude_json
        result = await claude_json(
            system=("Ești analistul de business al platformei PropManage (marketplace de lucrări + administrare "
                    "imobile, România). Primești datele unui modul și livrezi insights EXECUTABILE, concrete, în română. "
                    "Răspunde STRICT JSON: {\"bullets\": [max 4 constatări scurte], \"alerts\": [max 2 riscuri urgente sau gol], "
                    "\"recommendations\": [max 3 acțiuni concrete]}. Fii specific cu cifrele din date, fără generalități."),
            prompt=f"Modul: {module}\nDate curente:\n{context}\n\nAnalizează și livrează insights.",
            session_prefix=f"insights-{module}",
        )
        if not isinstance(result, dict) or "bullets" not in result:
            raise ValueError("Răspuns LLM invalid")
        payload = {
            "bullets": (result.get("bullets") or [])[:4],
            "alerts": (result.get("alerts") or [])[:2],
            "recommendations": (result.get("recommendations") or [])[:3],
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ai-insights] LLM fail ({module}): {e}")
        raise HTTPException(503, "Analiza AI e temporar indisponibilă — reîncearcă în câteva minute.")

    now = datetime.now(timezone.utc).isoformat()
    await db.ai_insights_cache.update_one(
        {"module": module},
        {"$set": {"module": module, "generated_at": now, "result": payload}},
        upsert=True,
    )
    return {**payload, "generated_at": now, "cached": False}
