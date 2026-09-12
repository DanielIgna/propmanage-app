"""CEO Briefing Engine (Directiva 152) — un singur briefing executiv pe zi, o singură pagină.

Nu dashboards. Nu rapoarte. Compune engine-urile existente (Enterprise Health D122,
War Room / Mission 100, Operations Center, Gap Engine) într-o pagină de decizie:
status → UN SINGUR lucru de făcut azi → top 5 riscuri → top 5 oportunități → focus Founder.
Noise filter: ascunde tot ce nu influențează deciziile de azi.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import require_role
from routes.enterprise_health import (
    DOMAIN_LABELS, _band, _build_alert, _collect_metrics, _domain_result, _get_formulas,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/ceo-briefing", tags=["ceo-briefing"])

DOMAIN_PRIORITY = ["revenue", "operations", "growth", "marketplace", "customer_trust",
                   "product", "knowledge", "ux", "ai_learning", "automation", "technical_debt"]
STATUS_RO = {"critical": "CRITIC", "at_risk": "LA RISC", "needs_attention": "NECESITĂ ATENȚIE",
             "healthy": "SĂNĂTOS", "excellent": "EXCELENT", "world_class": "WORLD CLASS"}


@router.get("")
async def ceo_briefing(user=Depends(require_role("admin"))):
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # ── Enterprise Health (reuse D122) ──────────────────────────────────────
    formulas = await _get_formulas()
    metrics = await _collect_metrics()
    domains, alerts = {}, []
    for key in DOMAIN_LABELS:
        f = formulas[key]
        if f.get("status") != "active":
            continue
        res = _domain_result(f, metrics)
        domains[key] = res
        if res["score"] < f.get("warning_threshold", 80):
            alerts.append(_build_alert(key, f, res))
    overall = round(sum(r["score"] for r in domains.values()) / len(domains), 1) if domains else 0
    band = _band(overall)
    from routes.enterprise_health import compute_enterprise_score
    es = await compute_enterprise_score({k: v["score"] for k, v in domains.items()}, overall)

    sorted_by_score = sorted(domains.items(), key=lambda kv: kv[1]["score"])
    weakest = sorted_by_score[:2]
    strongest = [kv for kv in reversed(sorted_by_score)][:2]
    strongest_txt = ", ".join(f"{DOMAIN_LABELS[k]} {round(v['score'])}" for k, v in strongest)
    weakest_txt = ", ".join(f"{DOMAIN_LABELS[k]} ({round(v['score'])})" for k, v in weakest)
    reason = (
        f"Platforma este solidă tehnic ({strongest_txt}). "
        f"Constrângerea principală nu mai este software-ul, ci: {weakest_txt}."
    )

    # ── Mission 100 + blockers (reuse War Room) ─────────────────────────────
    mission_pct, blockers = None, []
    try:
        from routes.first_revenue import war_room
        wr = await war_room(user=user)
        mission_pct = (wr.get("mission_100") or {}).get("progress_pct")
        for v in wr.values():
            if isinstance(v, dict) and v.get("top_blockers"):
                blockers = list(v["top_blockers"])[:3]
                break
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[CEO Briefing] war_room reuse failed: {e}")

    # ── Context operațional ─────────────────────────────────────────────────
    hot_leads = await db.leads.count_documents({"segment": {"$in": ["hot", "warm"]},
                                                "stage": {"$in": ["new", "contacted", "qualified"]}})
    new_today = await db.leads.count_documents({"created_at": {"$gte": today}})
    open_gaps = await db.specialist_gaps.count_documents({"status": "open"})
    gap_value = 0
    async for g in db.specialist_gaps.find({"status": "open"}, {"est_lost_revenue_ron": 1}):
        gap_value += g.get("est_lost_revenue_ron") or 0
    pending_sum, pending_n = 0.0, 0
    async for o in db.verified_estate_orders.find({"status": "pending", "demo_mode": {"$ne": True}}, {"amount_ron": 1}):
        pending_sum += float(o.get("amount_ron") or 0)
        pending_n += 1

    # ── ONE THING TODAY (secțiunea cea mai importantă) ──────────────────────
    top_alert = None
    for key in DOMAIN_PRIORITY:
        top_alert = next((a for a in alerts if a["domain"] == key), None)
        if top_alert:
            break
    if top_alert and top_alert["domain"] == "revenue" and hot_leads > 0:
        action = (f"Contactează cei mai buni {min(hot_leads, 10)} leads (hot/warm), oferă plată manuală "
                  f"(transfer/cash) și programează {min(5, max(1, hot_leads // 2))} întâlniri de audit.")
        why = f"Revenue este domeniul critic ({top_alert['score']}/100): {top_alert['cause']}."
    elif top_alert:
        action = top_alert["top_actions"][0]["action"] if top_alert["top_actions"] else f"Îmbunătățește {top_alert['label']}."
        why = f"{top_alert['label']} este sub prag ({top_alert['score']}/100): {top_alert['cause']}."
    else:
        action = "Cere review + referral de la ultimii clienți serviți — compune încrederea."
        why = "Toate domeniile sunt peste prag. Compune capitalul de încredere (PR-006)."
    effect_pts = 0.0
    if top_alert:
        effect_pts = sum(a.get("estimated_gain_pts", 0) for a in top_alert["top_actions"])
    conf_map = {"high": 94, "medium": 78, "low": 62}
    domain_conf = domains[top_alert["domain"]]["confidence"] if top_alert else "high"
    one_thing = {
        "action": action,
        "why": why,
        "expected_roi": f"+{effect_pts:.0f} puncte {top_alert['label']}" if top_alert else "Încredere + referrals",
        "expected_rot": "~2 ore de execuție",
        "expected_health_impact": f"+{effect_pts / max(1, len(domains)):.1f} puncte Enterprise Health",
        "confidence_pct": conf_map.get(domain_conf, 78),
    }

    # ── Snapshot (noise-filtered, o linie per secțiune D152) ────────────────
    def _line(key, label, line):
        d = domains.get(key)
        return {"key": key, "label": label, "line": line,
                "score": d["score"] if d else None,
                "color": _band(d["score"])["color"] if d else "#a8a29e"}

    snapshot = [
        {"key": "mission", "label": "Mission 100", "line": f"{mission_pct if mission_pct is not None else '—'}% progres total",
         "score": mission_pct, "color": "#d4ff3a"},
        _line("revenue", "Revenue", metrics["real_revenue"]["detail"]),
        _line("customer_trust", "Activitate clienți", f"{new_today} leads noi azi · {hot_leads} hot/warm active · {metrics['avg_rating']['detail']}"),
        _line("marketplace", "Marketplace", f"{metrics['fill_rate']['detail']} · {open_gaps} gaps deschise"),
        _line("operations", "Operations", metrics["leads_contact_rate"]["detail"]),
        _line("growth", "Growth", metrics["lead_growth"]["detail"]),
        _line("knowledge", "Knowledge", metrics["case_studies"]["detail"]),
        _line("ai_learning", "AI Learning", metrics["outcomes_tracked"]["detail"]),
    ]

    # ── Top riscuri (max 5) ─────────────────────────────────────────────────
    risks = [{"title": f"{a['label']} {a['score']}/100", "severity": a["severity"], "why": a["cause"]}
             for a in sorted(alerts, key=lambda a: a["score"])]
    for b in blockers:
        if len(risks) >= 5:
            break
        risks.append({"title": str(b), "severity": "blocker", "why": "Acțiune manuală Founder necesară."})
    risks = risks[:5]

    # ── Top oportunități (max 5) ────────────────────────────────────────────
    opportunities = []
    if pending_n:
        opportunities.append({"title": f"{pending_sum:.0f} RON în {pending_n} comenzi pending",
                              "action": "Convertible AZI cu plată manuală (Operations Center)."})
    if hot_leads:
        opportunities.append({"title": f"{hot_leads} leads hot/warm necontactate complet",
                              "action": "Fiecare conversie = primul venit real + studiu de caz."})
    if open_gaps:
        opportunities.append({"title": f"{open_gaps} cereri fără specialist (~{gap_value:.0f} RON)",
                              "action": "Alocă din Gap Engine sau recrutează pe categoriile cerute (D119)."})
    done_req = await db.requests.count_documents({"status": "completed"})
    if done_req:
        opportunities.append({"title": f"{done_req} proiecte finalizate fără studiu de caz",
                              "action": "Transformă-le în Case Library → SEO + trust + knowledge (D112)."})
    rev30 = await db.reviews.count_documents({"created_at": {"$gte": today[:8] + "01"}})
    if rev30 < 5:
        opportunities.append({"title": "Recenzii puține luna aceasta",
                              "action": "Cere review de la ultimii clienți — trust compounds (PR-006)."})
    opportunities = opportunities[:5]

    # ── Launch Sentinel (Firul B) — funnel „Primii 13" + Money-Flow în briefing ──
    launch = None
    try:
        from routes.launch_sentinel import launch_summary
        launch = await launch_summary()
        snapshot.insert(1, {"key": "launch", "label": "Lansare · Primii 13", "line": launch["line"],
                            "score": None, "color": launch["color"]})
        risks = (launch["risks"] + risks)[:5]
        opportunities = (launch["opportunities"] + opportunities)[:5]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[CEO Briefing] launch sentinel reuse failed: {e}")

    # ── Founder Focus ───────────────────────────────────────────────────────
    healthy = [k for k, v in domains.items() if v["score"] >= 80]
    focus = {
        "ignore_today": [f"{DOMAIN_LABELS[k]} ({round(domains[k]['score'])}) — sănătos, zero atenție azi" for k in healthy]
                        or ["Nimic — toate domeniile cer atenție."],
        "delegate": [
            "Alocarea specialiștilor pe gaps → candidații sunt deja calculați în Gap Engine.",
            "Follow-up comenzi pending → trimite link/instrucțiuni de plată manuală.",
        ],
        "founder_only": ([one_thing["action"]] + [str(b) for b in blockers])[:3],
    }

    # ── Execuție autonomă 24h (D156 L2 · EXECUTION ORDER 001) ───────────────
    autonomous_execution = None
    try:
        from lead_followup import build_execution_report_24h
        autonomous_execution = await build_execution_report_24h()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[CEO Briefing] autonomous report failed: {e}")

    # ── Guvernanță AI (PM-AI-003) — decizii, încredere, self-healing ────────
    ai_governance = None
    try:
        from orchestrator.governance import governance_snapshot
        ai_governance = await governance_snapshot()
        snapshot.append({"key": "ai_governance", "label": "Guvernanță AI",
                         "line": f"{ai_governance['decisions_24h']} decizii 24h · {ai_governance['executed_24h']} executate · "
                                 f"{ai_governance['recommended_24h']} recomandate · încredere medie {ai_governance['avg_confidence'] or '—'} · "
                                 f"autonomie {ai_governance.get('autonomy_score', '—')}/100",
                         "score": ai_governance.get("autonomy_score"), "color": "#d4ff3a"})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[CEO Briefing] governance snapshot failed: {e}")

    briefing = {
        "day": today,
        "generated_at": now.isoformat(),
        "enterprise_status": {"status": STATUS_RO.get(band["key"], band["label"]), "band": band,
                              "overall": overall, "reason": reason, "escalated": overall < 60,
                              "enterprise_score": es["score"], "enterprise_score_band": es["band"]},
        "one_thing": one_thing,
        "autonomous_execution": autonomous_execution,
        "launch": launch,
        "ai_governance": ai_governance,
        "snapshot": snapshot,
        "top_risks": risks,
        "top_opportunities": opportunities,
        "founder_focus": focus,
    }
    await db.ceo_briefings.update_one({"day": today}, {"$set": briefing}, upsert=True)
    return briefing
