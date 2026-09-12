"""AI Command Center — unified daily feed + Top 5 AI recommendations.

The admin no longer hunts for information: the platform surfaces priorities.
Feed = today's stats + warnings (requests >48h, escrow held/frozen, incomplete
specialist profiles, open disputes). Claude turns the snapshot into 5 actions.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/command-center", tags=["command-center"])
logger = logging.getLogger("propmanage.command_center")

WAIT_STATUSES = ["open", "pending"]

# Modul → link direct în admin pentru butonul de execuție al recomandării.
MODULE_LINKS = {
    "escrow": "/admin/financial-cockpit",
    "financiar": "/admin/financial-cockpit",
    "finanțe": "/admin/financial-cockpit",
    "marketplace": "/admin/marketplace-intel",
    "specialiști": "/admin/users",
    "specialisti": "/admin/users",
    "utilizatori": "/admin/users",
    "dispute": "/admin",
    "suport": "/admin",
    "marketing": "/admin/marketing",
    "conversii": "/admin/analytics",
    "seo": "/admin/design-audit",
}


def _module_link(module: str) -> str:
    return MODULE_LINKS.get((module or "").strip().lower(), "/admin")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _build_feed() -> dict[str, Any]:
    now = _now()
    day_ago = _iso(now - timedelta(hours=24))
    d7 = _iso(now - timedelta(days=7))
    d14 = _iso(now - timedelta(days=14))
    h48 = _iso(now - timedelta(hours=48))

    new_requests_24h = await db.requests.count_documents({"created_at": {"$gte": day_ago}})
    new_users_24h = await db.users.count_documents({"created_at": {"$gte": day_ago}})
    completed_24h = await db.requests.count_documents({"completed_at": {"$gte": day_ago}})
    req_7d = await db.requests.count_documents({"created_at": {"$gte": d7}})
    req_prev_7d = await db.requests.count_documents({"created_at": {"$gte": d14, "$lt": d7}})
    marketplace_trend = round((req_7d - req_prev_7d) / req_prev_7d * 100, 1) if req_prev_7d else None

    waiting_48h = await db.requests.count_documents({"status": {"$in": WAIT_STATUSES}, "created_at": {"$lt": h48}})

    escrow_held_amount = 0.0
    escrow_held_count = 0
    escrow_frozen_count = 0
    async for r in db.requests.find({"escrow_status": {"$in": ["held", "frozen"]}}, {"escrow_status": 1, "escrow_amount": 1}):
        if r["escrow_status"] == "held":
            escrow_held_count += 1
            escrow_held_amount += float(r.get("escrow_amount") or 0)
        else:
            escrow_frozen_count += 1

    incomplete_specialists = await db.users.count_documents({
        "role": "specialist",
        "$or": [{"specialty": None}, {"specialty": {"$exists": False}}, {"verified": {"$ne": True}}],
    })
    open_disputes = await db.disputes.count_documents({"status": {"$in": ["open", "pending", "in_review"]}})
    pending_payments = await db.payment_transactions.count_documents({"payment_status": {"$in": ["pending", "initiated"]}})

    # ── Interconectare Business Health: departamentele ROȘII devin alerte ────
    from routes.business_health import compute_health
    health = await compute_health()
    red_departments = [d for d in health["departments"] if d["color"] == "red"]

    # ── Value Loop (Board Decision 002/003): PVI ca indicator strategic ──────
    from value_loop import value_loop_summary
    vl = await value_loop_summary()

    # ── GI-2: lead-uri fierbinți din Intent & Lead Intelligence ─────────────
    hot_leads = await db.lead_scores.count_documents({"tier": "hot"})
    qualified_leads = await db.lead_scores.count_documents({"tier": "qualified"})

    # ── GI-4a: venit atribuit deciziilor AI (Learning Engine) ───────────────
    from learning_engine import learning_stats
    lstats = await learning_stats()

    stats = [
        {"key": "new_requests", "label": "Cereri noi (24h)", "value": new_requests_24h, "icon": "inbox"},
        {"key": "new_users", "label": "Utilizatori noi (24h)", "value": new_users_24h, "icon": "users"},
        {"key": "completed", "label": "Lucrări finalizate (24h)", "value": completed_24h, "icon": "check"},
        {"key": "trend", "label": "Marketplace 7z vs 7z", "value": f"{'+' if (marketplace_trend or 0) >= 0 else ''}{marketplace_trend}%" if marketplace_trend is not None else "—", "icon": "trend"},
        {"key": "avg_pvi", "label": "PVI mediu ecosistem", "value": f"{vl['avg_pvi']}/100" if vl["properties_scored"] else "—", "icon": "gem"},
    ]

    warnings = []
    if waiting_48h:
        warnings.append({"key": "waiting_48h", "label": f"{waiting_48h} cereri așteaptă de peste 48h fără specialist", "severity": "high"})
    if escrow_held_amount:
        warnings.append({"key": "escrow_held", "label": f"Escrow de {escrow_held_amount:,.0f} lei neconfirmat ({escrow_held_count} cereri)", "severity": "high"})
    if escrow_frozen_count:
        warnings.append({"key": "escrow_frozen", "label": f"{escrow_frozen_count} escrow-uri înghețate (dispute active)", "severity": "high"})
    if open_disputes:
        warnings.append({"key": "disputes", "label": f"{open_disputes} dispute deschise necesită triaj", "severity": "medium"})
    if incomplete_specialists:
        warnings.append({"key": "incomplete_spec", "label": f"{incomplete_specialists} specialiști cu profil incomplet (fără specialitate sau neverificați)", "severity": "medium"})
    if pending_payments:
        warnings.append({"key": "pending_pay", "label": f"{pending_payments} plăți inițiate dar nefinalizate", "severity": "low"})
    if hot_leads:
        warnings.append({"key": "hot_leads", "label": f"{hot_leads} lead-uri fierbinți așteaptă contact — probabilitate mare de conversie", "severity": "medium", "link": "/admin/lead-intel"})
    for d in red_departments:
        warnings.append({
            "key": f"health_{d['key']}",
            "label": f"Business Health: {d['label']} în ROȘU (scor {d['score']}) — {d['detail']}",
            "severity": "high",
            "link": "/admin/business-health",
        })

    return {
        "generated_at": _iso(now),
        "stats": stats,
        "warnings": warnings,
        "health_overall": health["overall"],
        "health_overall_color": health["overall_color"],
        "raw": {
            "new_requests_24h": new_requests_24h, "new_users_24h": new_users_24h,
            "completed_24h": completed_24h, "req_7d": req_7d, "req_prev_7d": req_prev_7d,
            "marketplace_trend_pct": marketplace_trend, "waiting_48h": waiting_48h,
            "escrow_held_amount": escrow_held_amount, "escrow_held_count": escrow_held_count,
            "escrow_frozen_count": escrow_frozen_count, "incomplete_specialists": incomplete_specialists,
            "open_disputes": open_disputes, "pending_payments": pending_payments,
            "avg_pvi": vl["avg_pvi"], "active_warranties": vl["active_warranties"],
            "twin_enrichments": vl["twin_enrichments"],
            "hot_leads": hot_leads, "qualified_leads": qualified_leads,
            "ai_revenue_attributed_30d": lstats["revenue_attributed_30d_ron"],
            "ai_decisions_total": lstats["total_decisions"],
            "health_overall": health["overall"],
            "red_departments": [{"key": d["key"], "label": d["label"], "score": d["score"], "detail": d["detail"]} for d in red_departments],
        },
    }


@router.get("/feed")
async def command_feed(_admin=Depends(require_role("admin"))):
    return await _build_feed()


async def _generate_recos() -> dict[str, Any]:
    """Core logic — folosit de endpoint și de cron-ul de dimineață."""
    feed = await _build_feed()
    raw = feed["raw"]
    growth = await db.growth_insights.find_one({"_id": "latest"}) or {}
    beh = growth.get("behavior") or {}
    top_ux = (growth.get("ux_problems") or [])[:2]
    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești directorul de operațiuni AI al PropManage — marketplace românesc de servicii pentru proprietate "
            "cu escrow, specialiști verificați și lead fees. Primești snapshot-ul operațional + growth zilnic și returnezi "
            "TOP 5 acțiuni concrete pe care adminul să le facă AZI, ordonate după impact comercial. "
            "Răspunde STRICT JSON: {\"recommendations\": [{\"action\": str RO imperativ ≤120c, "
            "\"why\": str RO ≤150c, \"severity\": \"high|medium|low\", \"module\": str (ex: Escrow, Marketplace, Specialiști), "
            "\"category\": \"ux|marketing|comercial|operational|ceo\"}]}. "
            "Alege category corect: ux=interfață/abandon pagini/formulare; marketing=campanii/mesaje/surse trafic/momente trimitere; "
            "comercial=vânzare servicii/oportunități/specialiști/conversie; ceo=strategie/PVI/sănătate business; "
            "operational=DOAR escrow/dispute/plăți/procese interne. NU eticheta totul operational. "
            "Fii specific cifrelor primite, nu generic."
        )
        prompt = (
            f"Snapshot azi: cereri noi 24h={raw['new_requests_24h']}, useri noi={raw['new_users_24h']}, "
            f"finalizate={raw['completed_24h']}, trend marketplace 7z={raw['marketplace_trend_pct']}%, "
            f"cereri >48h fără specialist={raw['waiting_48h']}, escrow neconfirmat={raw['escrow_held_amount']:.0f} lei "
            f"({raw['escrow_held_count']} cereri), escrow înghețat={raw['escrow_frozen_count']}, "
            f"dispute deschise={raw['open_disputes']}, specialiști profil incomplet={raw['incomplete_specialists']}, "
            f"plăți nefinalizate={raw['pending_payments']}. "
            f"Business Health general={raw.get('health_overall')}. Departamente în ROȘU (prioritizează fix-urile lor): "
            + ("; ".join(f"{d['label']} scor {d['score']} ({d['detail']})" for d in raw.get("red_departments", [])) or "niciunul")
            + f". Value Loop: PVI mediu={raw.get('avg_pvi')}, garanții active={raw.get('active_warranties')}, "
            f"îmbogățiri Twin={raw.get('twin_enrichments')}. "
            f"Growth Intelligence (date reale): moment optim WhatsApp={beh.get('best_whatsapp_time', {}).get('text', 'necunoscut')}; "
            f"surse={beh.get('source_comparison', {}).get('text', 'fără date')}; "
            f"serviciu top={beh.get('top_service', {}).get('text', 'fără date')}. "
            f"Lead Intelligence: {raw.get('hot_leads', 0)} lead-uri fierbinți + {raw.get('qualified_leads', 0)} calificate așteaptă acțiune comercială. "
            f"Learning Engine: {raw.get('ai_decisions_total', 0)} decizii AI memorate, venit atribuit 30z={raw.get('ai_revenue_attributed_30d', 0)} RON. "
            f"Top probleme UX din comportament real: "
            + ("; ".join(p.get("label", "") for p in top_ux) or "niciuna detectată")
            + "."
        )
        result = await claude_json(system=system, prompt=prompt, session_prefix="command-center")
        recos = [
            {
                "action": str(r.get("action") or "")[:160],
                "why": str(r.get("why") or "")[:200],
                "severity": r.get("severity") if r.get("severity") in ("high", "medium", "low") else "medium",
                "module": str(r.get("module") or "")[:40],
                "category": r.get("category") if r.get("category") in ("ux", "marketing", "comercial", "operational", "ceo") else "operational",
            }
            for r in (result.get("recommendations") or [])[:5] if isinstance(r, dict) and r.get("action")
        ]
        if not recos:
            raise ValueError("Zero recomandări valide")
        ai_generated = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[command-center] LLM fail: {e} — fallback")
        recos = [
            {"action": f"Rezolvă cele {raw['waiting_48h']} cereri care așteaptă >48h", "why": "Cererile neonorate duc la abandon.", "severity": "high", "module": "Marketplace", "category": "operational"},
            {"action": f"Confirmă escrow-ul de {raw['escrow_held_amount']:.0f} lei", "why": "Banii blocați erodează încrederea.", "severity": "high", "module": "Escrow", "category": "operational"},
            {"action": f"Contactează {raw['incomplete_specialists']} specialiști cu profil incomplet", "why": "Profilele incomplete reduc conversia.", "severity": "medium", "module": "Specialiști", "category": "comercial"},
        ]
        ai_generated = False

    doc = {"generated_at": _iso(_now()), "recommendations": [{**r, "idx": i, "link": _module_link(r.get("module")), "done": False} for i, r in enumerate(recos)], "ai_generated": ai_generated, "snapshot": raw}
    await db.command_center_recos.update_one({"_id": "latest"}, {"$set": doc}, upsert=True)
    return {**doc, "warnings": feed["warnings"], "stats": feed["stats"]}


@router.post("/recommendations")
async def generate_recommendations(_admin=Depends(require_role("admin"))):
    return await _generate_recos()


async def morning_command_center() -> dict[str, Any]:
    """APScheduler callable — 07:00 Bucharest, zilnic (CAO Roadmap 2.1 + 2.2).
    1. Regenerează feed + Top 5 recomandări AI.
    2. Emite semnal orchestrator cu alertele high-severity → playbook business_alert_router.
    3. Trimite email digest super-adminilor (fondator).
    """
    result = await _generate_recos()
    warnings = result.get("warnings", [])
    high = [w for w in warnings if w.get("severity") == "high"]

    # 2. Semnal orchestrator (o dată pe zi, agregat)
    try:
        from orchestrator.engine import emit_signal
        await emit_signal("business_alert", {
            "date": _iso(_now())[:10],
            "high_warnings": [{"key": w["key"], "label": w["label"]} for w in high],
            "warnings_total": len(warnings),
            "health_overall": result.get("snapshot", {}).get("health_overall"),
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[command-center-cron] emit_signal fail: {e}")

    # 3. Email digest fondator
    sent = 0
    try:
        from autonomy.founder_digest import _get_super_admins
        from services import send_email
        admins = await _get_super_admins()
        recos = result.get("recommendations", [])
        stats_html = "".join(f"<li>{s['label']}: <b>{s['value']}</b></li>" for s in result.get("stats", []))
        warn_html = "".join(f"<li>⚠ {w['label']}</li>" for w in warnings[:8]) or "<li>Zero alerte — totul sub control.</li>"
        reco_html = "".join(f"<li><b>{r['action']}</b><br/><small>{r['why']}</small></li>" for r in recos) or "<li>—</li>"
        html = (
            f"<h2>🧠 AI Command Center — {_iso(_now())[:10]}</h2>"
            f"<h3>Astăzi</h3><ul>{stats_html}</ul>"
            f"<h3>Alerte ({len(warnings)})</h3><ul>{warn_html}</ul>"
            f"<h3>Top {len(recos)} recomandări AI</h3><ol>{reco_html}</ol>"
            f"<p><a href='{os.environ.get('PUBLIC_APP_URL', '')}/admin/command-center'>Deschide Command Center →</a></p>"
        )
        subject = f"🧠 Command Center: {len(high)} urgente · {len(recos)} recomandări AI azi"
        for adm in admins:
            try:
                await send_email(adm["email"], subject, html)
                sent += 1
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[command-center-cron] email fail {adm['email']}: {e}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[command-center-cron] digest fail: {e}")

    logger.info(f"[command-center-cron] done: {len(high)} high warnings, {sent} emails")
    return {"high_warnings": len(high), "emails_sent": sent, "recommendations": len(result.get('recommendations', []))}


@router.post("/recommendations/toggle")
async def toggle_recommendation(idx: int = Body(..., embed=True), _admin=Depends(require_role("admin"))):
    doc = await db.command_center_recos.find_one({"_id": "latest"})
    if not doc or not doc.get("recommendations"):
        raise HTTPException(404, "Nu există recomandări generate.")
    recos = doc["recommendations"]
    if idx < 0 or idx >= len(recos):
        raise HTTPException(400, f"Index invalid: {idx}")
    recos[idx]["done"] = not recos[idx].get("done", False)
    await db.command_center_recos.update_one({"_id": "latest"}, {"$set": {"recommendations": recos}})
    if recos[idx]["done"]:
        from learning_engine import ledger_entry
        await db.ai_decision_ledger.insert_one(ledger_entry(
            "command_center_reco", "command_center", recos[idx].get("action") or "",
            recos[idx].get("why") or "", "done", _admin.get("email") or "admin"))
    return {"idx": idx, "done": recos[idx]["done"]}


@router.get("/recommendations/latest")
async def latest_recommendations(_admin=Depends(require_role("admin"))):
    doc = await db.command_center_recos.find_one({"_id": "latest"}, {"_id": 0})
    return doc or {"recommendations": None}

