"""PM-AI-REPAIR-001 — Health Repair Engine.

Fiecare domeniu Enterprise Health sub prag primește: Detector (cauze reale din date)
→ Repairer (acțiuni de producție executate automat, refolosind motoarele existente)
→ Validator (recalcul scor). Persistă în db.health_repair_runs + Decision Memory.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.health_repair")

REPAIR_TARGET = 95


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


def _problem(metric: str, detail: str, root_cause: str, source: str, auto_fixable: bool = True) -> dict:
    return {"metric": metric, "detail": detail, "root_cause": root_cause,
            "source": source, "auto_fixable": auto_fixable}


def _action(name: str, ok: bool, detail: str) -> dict:
    return {"action": name, "ok": ok, "detail": str(detail)[:300]}


async def _safe(name: str, coro) -> dict:
    try:
        res = await coro
        return _action(name, True, res if isinstance(res, str) else str(res)[:250])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[repair] {name} failed: {e}")
        return _action(name, False, str(e)[:200])


# ============================================================================
# DETECTORI + REPARATORI per domeniu (refolosesc motoarele existente)
# ============================================================================
async def _detect_revenue(m: dict) -> list:
    probs = []
    pending = [o async for o in db.verified_estate_orders.find(
        {"status": "pending", "demo_mode": {"$ne": True}}, {"amount_ron": 1, "contact_email": 1})]
    if pending:
        total = sum(float(o.get("amount_ron") or 0) for o in pending)
        probs.append(_problem("orders_followup", f"{len(pending)} comenzi reale pending ({total:.0f} RON)",
                              "Comenzi neconvertite — lipsă follow-up de plată",
                              "verified_estate_orders / routes/first_revenue.py"))
    hot = await db.leads.count_documents({"segment": {"$in": ["hot", "warm"]}, "stage": "new"})
    if hot:
        probs.append(_problem("real_revenue", f"{hot} leads hot/warm în stage NEW",
                              "Leads calde necontactate — venit blocat în pipeline",
                              "leads / lead_followup.py"))
    return probs


async def _repair_revenue(probs: list) -> list:
    actions = []
    from revenue_hunter import run_revenue_hunter_tick
    actions.append(await _safe("revenue_hunter_tick", run_revenue_hunter_tick()))
    from lead_followup import run_followup_scan
    actions.append(await _safe("lead_followup_scan", run_followup_scan(manual=True)))
    pend = [p for p in probs if p["metric"] == "orders_followup"]
    if pend:
        from orchestrator.engine import notify_admins
        n = await notify_admins("💰 RepairEngine: comenzi pending de convertit",
                                f"{pend[0]['detail']}. Trimite link de plată manuală azi.",
                                link="/admin/command-center")
        actions.append(_action("notify_pending_orders", True, f"{n} admini notificați"))
    return actions


async def _detect_operations(m: dict) -> list:
    probs = []
    new_leads = await db.leads.count_documents({"stage": "new"})
    if new_leads:
        probs.append(_problem("leads_contact_rate", f"{new_leads} leads în stage NEW",
                              "Follow-up necontactat", "leads / lead_followup.py"))
    gaps = await db.specialist_gaps.count_documents({"status": "open"})
    if gaps:
        probs.append(_problem("gap_pressure", f"{gaps} cereri deschise fără specialist",
                              "Matching neexecutat sau lipsă ofertă", "specialist_gaps / routes/admin.py::execute_auto_match"))
    return probs


async def _repair_operations(probs: list) -> list:
    actions = []
    if any(p["metric"] == "gap_pressure" for p in probs):
        from routes.admin import execute_auto_match
        actions.append(await _safe("auto_match", execute_auto_match(
            limit=20, min_rating=0.0, dry_run=False,
            triggered_by={"id": "repair_engine", "kind": "repair", "label": "HealthRepairEngine"})))
    if any(p["metric"] == "leads_contact_rate" for p in probs):
        from lead_followup import run_followup_scan
        actions.append(await _safe("lead_followup_scan", run_followup_scan(manual=True)))
    return actions


async def _detect_growth(m: dict) -> list:
    probs = []
    if (m.get("lead_growth") or {}).get("score", 100) < 80:
        probs.append(_problem("lead_growth", m["lead_growth"]["detail"],
                              "Pipeline de achiziție încetinit", "leads / growth_intelligence.py"))
    if (m.get("email_capture") or {}).get("score", 100) < 80:
        probs.append(_problem("email_capture", m["email_capture"]["detail"],
                              "Captură email sub țintă — nurture inactiv", "lead_magnet_leads / lead_followup.py"))
    return probs


async def _repair_growth(probs: list) -> list:
    actions = []
    from lead_followup import run_nurture_scan
    actions.append(await _safe("nurture_scan", run_nurture_scan(manual=True)))
    from growth_intelligence import run_growth_scan
    actions.append(await _safe("growth_intelligence_scan", run_growth_scan(trigger="repair_engine")))
    return actions


async def _detect_marketplace(m: dict) -> list:
    probs = []
    unfilled = await db.requests.count_documents(
        {"specialist_id": {"$in": [None, ""]}, "status": {"$nin": ["completed", "cancelled", "closed", "rejected"]}})
    if unfilled:
        probs.append(_problem("fill_rate", f"{unfilled} cereri active fără specialist",
                              "Matching incomplet", "requests / routes/admin.py::execute_auto_match"))
    if (m.get("verified_rate") or {}).get("score", 100) < 80:
        probs.append(_problem("verified_rate", m["verified_rate"]["detail"],
                              "Specialiști neverificați reduc încrederea", "users / routes/kyc.py", auto_fixable=False))
    return probs


async def _repair_marketplace(probs: list) -> list:
    actions = []
    if any(p["metric"] == "fill_rate" for p in probs):
        from routes.admin import execute_auto_match
        actions.append(await _safe("auto_match", execute_auto_match(
            limit=20, min_rating=0.0, dry_run=False,
            triggered_by={"id": "repair_engine", "kind": "repair", "label": "HealthRepairEngine"})))
    from orchestrator.engine import emit_signal
    actions.append(await _safe("category_visibility_refresh",
                               emit_signal("category_visibility_refresh", {"trigger": "repair_engine"})))
    return actions


async def _detect_customer_trust(m: dict) -> list:
    probs = []
    done_no_review = 0
    async for r in db.requests.find(
            {"status": "completed", "created_at": {"$gte": _days_ago(60)},
             "review_nudge_sent": {"$ne": True}}, {"id": 1, "client_id": 1, "title": 1}).limit(50):
        rev = await db.reviews.count_documents({"request_id": r.get("id")}, limit=1)
        if not rev:
            done_no_review += 1
    if done_no_review:
        probs.append(_problem("review_freshness", f"{done_no_review} lucrări finalizate fără recenzie (60z)",
                              "Cerere de review netrimisă după finalizare", "requests+reviews / health_repair.py"))
    return probs


async def _repair_customer_trust(probs: list) -> list:
    sent = 0
    async for r in db.requests.find(
            {"status": "completed", "created_at": {"$gte": _days_ago(60)},
             "review_nudge_sent": {"$ne": True}}, {"id": 1, "client_id": 1, "title": 1}).limit(20):
        if await db.reviews.count_documents({"request_id": r.get("id")}, limit=1):
            continue
        if not r.get("client_id"):
            continue
        await db.notifications.insert_one({
            "user_id": str(r["client_id"]),
            "title": "Cum a fost lucrarea?",
            "message": f"Lasă o recenzie pentru „{(r.get('title') or 'lucrarea ta')[:60]}” — ajută comunitatea și specialiștii buni.",
            "type": "review_request", "link": "/client", "read": False, "created_at": _now(),
        })
        await db.requests.update_one({"_id": r["_id"]}, {"$set": {"review_nudge_sent": True, "review_nudge_at": _now()}})
        sent += 1
    return [_action("review_nudges", True, f"{sent} cereri de recenzie trimise clienților")]


async def _detect_product(m: dict) -> list:
    probs = []
    no_agg = await db.properties.count_documents({
        "health_score": {"$exists": False},
        "$or": [{"structure_health": {"$exists": True}}, {"utilities_health": {"$exists": True}},
                {"documents_health": {"$exists": True}}]})
    if no_agg:
        probs.append(_problem("health_coverage", f"{no_agg} proprietăți cu componente dar fără health_score agregat",
                              "Agregatul nu a fost calculat", "properties / property_intelligence.py"))
    missing = await db.properties.count_documents({"health_score": {"$exists": False}})
    if missing:
        probs.append(_problem("health_coverage", f"{missing} proprietăți fără Health Score",
                              "Onboarding incomplet — necesită date de la proprietar",
                              "properties", auto_fixable=False))
    return probs


async def _repair_product(probs: list) -> list:
    from property_intelligence import HEALTH_FIELDS
    fixed = 0
    async for p in db.properties.find({
            "health_score": {"$exists": False},
            "$or": [{f: {"$exists": True}} for f in HEALTH_FIELDS]}).limit(100):
        parts = [p.get(f) for f in HEALTH_FIELDS if isinstance(p.get(f), (int, float))]
        if not parts:
            continue
        score = min(100, round(sum(parts) / len(parts)))
        await db.properties.update_one({"_id": p["_id"]}, {"$set": {"health_score": score}})
        fixed += 1
    return [_action("backfill_health_score", True, f"{fixed} proprietăți cu health_score agregat calculat")]


async def _detect_knowledge(m: dict) -> list:
    probs = []
    candidates = 0
    async for r in db.requests.find({"status": "completed", "case_study_generated": {"$ne": True}},
                                    {"id": 1}).limit(30):
        candidates += 1
    if candidates:
        probs.append(_problem("case_studies", f"{candidates} lucrări finalizate fără studiu de caz",
                              "Case Library nealimentată din lucrări reale", "requests+case_library / health_repair.py"))
    return probs


async def _repair_knowledge(probs: list) -> list:
    created = 0
    async for r in db.requests.find({"status": "completed", "case_study_generated": {"$ne": True}}).limit(10):
        rev = await db.reviews.find_one({"request_id": r.get("id")}, {"rating": 1, "comment": 1})
        await db.case_library.insert_one({
            "id": uuid.uuid4().hex,
            "title": (r.get("title") or "Lucrare finalizată")[:120],
            "category": r.get("category") or r.get("specialty") or "general",
            "summary": (r.get("description") or "")[:400],
            "outcome": "Finalizată cu succes" + (f" · rating {rev['rating']}/5" if rev and rev.get("rating") else ""),
            "review_quote": (rev.get("comment") or "")[:300] if rev else "",
            "request_id": r.get("id"),
            "status": "draft",
            "generated_by": "repair_engine",
            "created_at": _now(),
        })
        await db.requests.update_one({"_id": r["_id"]}, {"$set": {"case_study_generated": True}})
        created += 1
    return [_action("case_study_drafts", True, f"{created} drafturi de studii de caz generate din lucrări reale")]


async def _detect_ux(m: dict) -> list:
    probs = []
    stale = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    for key in ("landing", "marketplace", "preturi", "legal"):
        row = await db.design_audit_cache.find_one({"key": key}, {"generated_at": 1, "result.mobile_score": 1})
        if not row or (row.get("generated_at") or "") < stale:
            probs.append(_problem("audit_coverage", f"Pagina '{key}' fără audit recent (>7z)",
                                  "Audit design expirat/lipsă", "design_audit_cache / routes/design_audit.py"))
        elif ((row.get("result") or {}).get("mobile_score") or 0) < 70:
            probs.append(_problem("design_audit_avg", f"Pagina '{key}' cu scor mobil scăzut",
                                  "Probleme UX pe mobil", "routes/design_audit.py", auto_fixable=False))
    return probs


async def _repair_ux(probs: list) -> list:
    actions = []
    from routes.design_audit import analyze_page
    for p in probs:
        if p["metric"] != "audit_coverage":
            continue
        key = p["detail"].split("'")[1]
        actions.append(await _safe(f"design_audit_{key}", analyze_page(key=key, force=True, _admin={})))
    if not actions:
        actions.append(_action("design_audits", True, "Toate paginile cheie au audit recent"))
    return actions


async def _detect_automation(m: dict) -> list:
    probs = []
    stuck = await db.orchestrator_retry_queue.count_documents({"status": "pending"})
    if stuck:
        probs.append(_problem("autonomy_operational", f"{stuck} retry-uri în coadă",
                              "Livrări eșuate în așteptare", "orchestrator_retry_queue / orchestrator/engine.py"))
    errors24 = await db.agent_runs.count_documents({"status": "error", "ts": {"$gte": _days_ago(1)}})
    if errors24:
        probs.append(_problem("autonomy_general", f"{errors24} erori cron în 24h",
                              "Joburi automate cu eșecuri", "agent_runs / orchestrator/governance.py"))
    return probs


async def _repair_automation(probs: list) -> list:
    actions = []
    from orchestrator.governance import governance_watchdog_tick
    actions.append(await _safe("self_healing_watchdog", governance_watchdog_tick()))
    from orchestrator.engine import orchestrator_retry_tick
    actions.append(await _safe("retry_tick", orchestrator_retry_tick()))
    return actions


async def _detect_ai_learning(m: dict) -> list:
    probs = []
    if (m.get("outcomes_tracked") or {}).get("score", 100) < 80:
        probs.append(_problem("outcomes_tracked", m["outcomes_tracked"]["detail"],
                              "Bucla de învățare nu urmărește rezultatele", "ai_outcomes / learning_engine.py"))
    unreviewed = await db.orchestrator_decisions.count_documents({"reviewed": False})
    if unreviewed:
        probs.append(_problem("decision_volume", f"{unreviewed} decizii AI ne-revizuite",
                              "Decision Review nerulat", "orchestrator_decisions / orchestrator/governance.py"))
    return probs


async def _repair_ai_learning(probs: list) -> list:
    actions = []
    from learning_engine import run_outcome_scan
    actions.append(await _safe("outcome_scan", run_outcome_scan(trigger="repair_engine")))
    from orchestrator.governance import decision_review_cron
    actions.append(await _safe("decision_review", decision_review_cron()))
    return actions


_INDEX_SPECS = [
    ("leads", [("stage", 1)]), ("leads", [("created_at", -1)]),
    ("requests", [("status", 1)]), ("requests", [("client_id", 1)]),
    ("notifications", [("user_id", 1), ("read", 1)]),
    ("orchestrator_ledger", [("ts", -1)]), ("orchestrator_decisions", [("ts", -1)]),
    ("agent_runs", [("ts", -1)]), ("reviews", [("request_id", 1)]),
    ("properties", [("owner_id", 1)]),
]


async def _detect_technical_debt(m: dict) -> list:
    probs = []
    missing = []
    for coll, keys in _INDEX_SPECS:
        info = await db[coll].index_information()
        want = "_".join(f"{k}_{d}" for k, d in keys)
        if want not in info:
            missing.append(f"{coll}({want})")
    if missing:
        probs.append(_problem("smoke_pass_rate", f"{len(missing)} indexuri DB lipsă: {', '.join(missing[:5])}",
                              "Interogări fără index pe colecții fierbinți", "MongoDB / health_repair.py"))
    last = await db.smoke_test_runs.find_one({}, {"ok": 1, "passed": 1, "total": 1}, sort=[("_id", -1)])
    if last and not last.get("ok"):
        probs.append(_problem("smoke_pass_rate", f"Ultimul smoke test: {last.get('passed')}/{last.get('total')}",
                              "Pași smoke eșuați", "smoke_test_runs / routes/admin_smoketest.py", auto_fixable=False))
    return probs


async def _repair_technical_debt(probs: list) -> list:
    created = []
    for coll, keys in _INDEX_SPECS:
        info = await db[coll].index_information()
        want = "_".join(f"{k}_{d}" for k, d in keys)
        if want not in info:
            await db[coll].create_index(keys)
            created.append(f"{coll}.{want}")
    return [_action("ensure_db_indexes", True,
                    f"{len(created)} indexuri create: {', '.join(created[:6])}" if created else "Toate indexurile există")]


DOMAIN_ENGINES = {
    "revenue": {"detect": _detect_revenue, "repair": _repair_revenue},
    "operations": {"detect": _detect_operations, "repair": _repair_operations},
    "growth": {"detect": _detect_growth, "repair": _repair_growth},
    "marketplace": {"detect": _detect_marketplace, "repair": _repair_marketplace},
    "customer_trust": {"detect": _detect_customer_trust, "repair": _repair_customer_trust},
    "product": {"detect": _detect_product, "repair": _repair_product},
    "knowledge": {"detect": _detect_knowledge, "repair": _repair_knowledge},
    "ux": {"detect": _detect_ux, "repair": _repair_ux},
    "automation": {"detect": _detect_automation, "repair": _repair_automation},
    "ai_learning": {"detect": _detect_ai_learning, "repair": _repair_ai_learning},
    "technical_debt": {"detect": _detect_technical_debt, "repair": _repair_technical_debt},
}


# ============================================================================
# BUCLA AUTONOMĂ: detect → repair → validate → measure
# ============================================================================
async def run_repair_cycle(domains: list = None, trigger: str = "cron") -> dict:
    from routes.enterprise_health import _get_formulas, _collect_metrics, _domain_result
    formulas = await _get_formulas()
    metrics = await _collect_metrics()

    targets = []
    for key, eng in DOMAIN_ENGINES.items():
        f = formulas.get(key)
        if not f or f.get("status") != "active":
            continue
        score = _domain_result(f, metrics)["score"]
        if domains is not None:
            if key in domains:
                targets.append((key, f, score))
        elif score < min(REPAIR_TARGET, f.get("warning_threshold", 80) + 15):
            targets.append((key, f, score))

    results = []
    for key, f, score_before in targets:
        eng = DOMAIN_ENGINES[key]
        try:
            problems = await eng["detect"](metrics)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[repair] detect {key} failed: {e}")
            problems = [_problem("detector", f"Detector eșuat: {e}", "Eroare internă detector", "health_repair.py", False)]
        actions = []
        if any(p.get("auto_fixable") for p in problems):
            try:
                actions = await eng["repair"](problems)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[repair] repair {key} failed: {e}")
                actions = [_action("repair", False, str(e)[:200])]
        results.append({"domain": key, "score_before": score_before, "problems": problems, "actions": actions})

    # Validare: recalculează scorurile după reparații
    if results:
        metrics_after = await _collect_metrics()
        for r in results:
            f = formulas[r["domain"]]
            r["score_after"] = _domain_result(f, metrics_after)["score"]
            r["delta"] = round(r["score_after"] - r["score_before"], 1)

    run = {
        "id": uuid.uuid4().hex, "ts": _now(), "trigger": trigger,
        "domains_scanned": len(DOMAIN_ENGINES), "domains_repaired": len(results),
        "total_problems": sum(len(r["problems"]) for r in results),
        "total_actions": sum(len(r["actions"]) for r in results),
        "results": results,
    }

    # Bucla autonomă: după reparații, Journey Guardian re-auditează și închide task-urile rezolvate.
    # (Trebuie să ruleze ÎNAINTE de persist ca să apară în /runs.)
    try:
        from journey_guardian import run_journey_guardian
        run["journey_guardian"] = await run_journey_guardian(trigger="repair_cycle")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[repair] guardian re-audit failed: {e}")

    # Architecture Guardian: după orice ciclu, verifică integritatea arhitecturii canonice.
    try:
        from architecture_guardian import run_architecture_guardian
        run["architecture_guardian"] = await run_architecture_guardian(trigger="repair_cycle")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[repair] architecture guardian failed: {e}")

    # Product Guardian: verifică experiența de produs (CTA, roluri, gates, funnel).
    try:
        from product_guardian import run_product_guardian
        run["product_guardian"] = await run_product_guardian(trigger="repair_cycle")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[repair] product guardian failed: {e}")

    try:
        await db.health_repair_runs.insert_one({**run})
        n = await db.health_repair_runs.estimated_document_count()
        if n > 400:
            cur = db.health_repair_runs.find({}, {"_id": 1}).sort("ts", -1).skip(300)
            old = [d["_id"] async for d in cur]
            if old:
                await db.health_repair_runs.delete_many({"_id": {"$in": old}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[repair] run persist failed: {e}")

    if results:
        from orchestrator.engine import write_ledger
        from orchestrator.governance import record_decision
        ok_actions = sum(1 for r in results for a in r["actions"] if a["ok"])
        await write_ledger({
            "signal_kind": "health_repair", "playbook_id": "health_repair_engine",
            "playbook_name": "Health Repair Engine",
            "steps": [{"action": f"repair_{r['domain']}", "ok": all(a['ok'] for a in r['actions']) if r['actions'] else True,
                       "detail": f"{len(r['problems'])} probleme, {len(r['actions'])} acțiuni, scor {r['score_before']}→{r.get('score_after', r['score_before'])}"}
                      for r in results],
            "outcome": "auto_resolved", "minutes_saved": 8 * ok_actions,
            "escalated": False, "test": False,
        })
        await record_decision({
            "signal_kind": "health_repair", "playbook_id": "health_repair_engine",
            "playbook_name": "Health Repair Engine", "authority_level": 4,
            "execution_mode": "execute", "confidence": 0.9, "decided": "executed",
            "outcome": "auto_resolved", "escalated": False,
            "context": {r["domain"]: f"{r['score_before']}→{r.get('score_after')}" for r in results},
            "test": False,
        })
    logger.info(f"[repair] cycle done: {len(results)} domenii reparate, {run['total_actions']} acțiuni")

    run.pop("_id", None)
    return run


async def repair_cycle_cron() -> dict:
    return await run_repair_cycle(trigger="cron")
