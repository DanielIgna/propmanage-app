"""Autonomy Orchestrator — Sprint 1 playbooks.

1. smoke_fail            → auto-create QA Copilot session with findings
2. autonomy_score_drop   → corrective autopilot sweep + recovery check
3. webhook_fail          → retry queue (email) / repeated-failure monitor (stripe)
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.orchestrator.playbooks")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# 1. SMOKE-FAIL → AUTO QA SESSION
# ============================================================================
async def handle_smoke_fail(payload: dict) -> dict:
    from orchestrator.engine import notify_admins
    steps_log = []
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # Self-Healing pas 1: retry imediat — majoritatea eșecurilor sunt flake-uri de rețea
    try:
        from autonomy.self_driving import get_settings as _sd_settings
        sd = await _sd_settings()
    except Exception:  # noqa: BLE001
        sd = {"self_healing_smoke": True}
    if sd.get("self_healing_smoke") and not payload.get("is_retry"):
        try:
            from routes.admin_smoketest import _run_smoke_sequence
            base_url = payload.get("base_url") or ""
            if base_url:
                retry_report = await _run_smoke_sequence(base_url)
                if retry_report.get("overall_ok"):
                    steps_log.append({"action": "self_healing_retry", "ok": True,
                                      "detail": "Retry imediat a TRECUT — eșecul inițial a fost flake. Zero intervenție umană."})
                    return {"steps": steps_log, "outcome": "self_healed_flake", "minutes_saved": 25, "escalate": False}
                steps_log.append({"action": "self_healing_retry", "ok": False,
                                  "detail": f"Retry a picat și el ({retry_report.get('failed')}/{retry_report.get('total')}) — eșec real, continui cu diagnoza."})
        except Exception as e:  # noqa: BLE001
            steps_log.append({"action": "self_healing_retry", "ok": False, "detail": f"Retry indisponibil: {str(e)[:120]}"})

    failed_steps = payload.get("steps") or []

    # Self-Healing pas 2: caută fix-uri cunoscute în Bug Memory (qa_sessions findings închise)
    known_fixes = []
    try:
        for s in failed_steps[:3]:
            name = str(s.get("name", ""))[:40]
            if not name:
                continue
            match = await db.qa_sessions.find_one(
                {"findings": {"$elemMatch": {"text": {"$regex": name, "$options": "i"}, "status": {"$in": ["closed", "resolved"]}}}},
                {"title": 1, "_id": 0},
            )
            if match:
                known_fixes.append(f"'{name}' → fix documentat în sesiunea QA: {match.get('title')}")
        if known_fixes:
            steps_log.append({"action": "bug_memory_lookup", "ok": True,
                              "detail": "Fix-uri cunoscute găsite: " + " | ".join(known_fixes)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[playbooks] bug memory lookup fail: {e}")

    lines = [
        f"- {s.get('name')}: {s.get('error') or ('HTTP ' + str(s.get('status_code')))}"
        for s in failed_steps
    ]
    finding_text = (
        f"Smoke test FAILED {payload.get('failed')}/{payload.get('total')} pe {payload.get('base_url')}:\n"
        + "\n".join(lines)
    )[:4000]
    finding = {
        "id": uuid.uuid4().hex,
        "text": finding_text,
        "status": "open",
        "severity": "high",
        "source": "orchestrator",
        "ts": _now(),
        "created_at": _now(),
        "ai_analysis": None,
    }

    existing = await db.qa_sessions.find_one({
        "auto_source": "orchestrator_smoke_fail",
        "status": "active",
        "created_at": {"$gte": today_start},
    })
    if existing:
        await db.qa_sessions.update_one(
            {"id": existing["id"]},
            {"$push": {"findings": finding}, "$set": {"updated_at": _now()}},
        )
        steps_log.append({
            "action": "append_finding_existing_session", "ok": True,
            "detail": f"Finding adăugat la sesiunea QA auto existentă '{existing.get('title')}'",
        })
    else:
        sid = uuid.uuid4().hex
        doc = {
            "id": sid,
            "title": f"AUTO · Smoke Test FAILED · {now.date().isoformat()}",
            "goal": "Sesiune creată automat de Autonomy Orchestrator la eșuarea smoke test-ului. Investighează pașii eșuați din findings.",
            "role_being_tested": "client",
            "area": "smoke-test",
            "status": "active",
            "findings": [finding],
            "generated_prompt": None,
            "owner_email": "orchestrator@propmanage.ai",
            "auto_source": "orchestrator_smoke_fail",
            "created_at": _now(),
            "updated_at": _now(),
        }
        await db.qa_sessions.insert_one(doc)
        steps_log.append({
            "action": "create_qa_session", "ok": True,
            "detail": f"Sesiune QA creată automat: '{doc['title']}' cu {len(failed_steps)} pași eșuați ca finding",
        })

    n = await notify_admins(
        "🤖 Orchestrator: sesiune QA auto-creată (smoke fail confirmat după retry)",
        f"Smoke test a eșuat ({payload.get('failed')}/{payload.get('total')}) și retry-ul automat a confirmat eșecul. "
        + ("Fix-uri cunoscute din Bug Memory: " + " | ".join(known_fixes) + ". " if known_fixes else "")
        + "Finding-urile au fost înregistrate automat în QA Copilot.",
        link="/admin/qa-copilot",
    )
    steps_log.append({"action": "notify_admins_inapp", "ok": True, "detail": f"{n} admini notificați in-app"})
    return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 20, "escalate": False}


# ============================================================================
# 2. AUTONOMY REFLEX (score drop → corrective sweep)
# ============================================================================
async def handle_autonomy_score_drop(payload: dict) -> dict:
    steps_log = []
    drops = payload.get("drops") or {}
    drop_txt = ", ".join(f"{k} −{v}pp" for k, v in drops.items()) or "necunoscut"

    if payload.get("test"):
        steps_log.append({
            "action": "corrective_sweep", "ok": True,
            "detail": f"SIMULARE — drop detectat ({drop_txt}); sweep-ul corectiv nu a fost rulat pe date reale",
        })
        steps_log.append({"action": "verify_recovery", "ok": True, "detail": "SIMULARE — recuperare confirmată"})
        return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 15, "escalate": False}

    from autonomy.autopilot import daily_autopilot_sweep
    sweep = await daily_autopilot_sweep()
    steps_log.append({
        "action": "corrective_sweep", "ok": True,
        "detail": (
            f"Drop detectat ({drop_txt}) → sweep corectiv rulat: "
            f"{sweep.get('qa_findings_resolved', 0)} QA findings rezolvate, "
            f"{sweep.get('ai_findings_dismissed', 0)} AI findings închise"
        ),
    })

    new_general = ((sweep.get("snapshot") or {}).get("general")) or 0
    prev_general = payload.get("prev_general") or 0
    recovered = new_general >= prev_general - 2
    steps_log.append({
        "action": "verify_recovery", "ok": recovered,
        "detail": f"Scor general după sweep: {new_general} (înainte de drop: {prev_general})",
    })

    if recovered:
        return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 15, "escalate": False}
    return {
        "steps": steps_log,
        "outcome": "escalated",
        "minutes_saved": 10,
        "escalate": True,
        "escalation_title": f"⚠ Autonomy score drop nerecuperat ({drop_txt})",
        "escalation_body": (
            f"Sweep-ul corectiv automat nu a readus scorul (acum {new_general}, anterior {prev_general}). "
            f"Verifică recomandările în Autonomy Engine."
        ),
        "escalation_link": "/admin/autonomy",
    }


# ============================================================================
# 3. WEBHOOK RETRY GUARDIAN
# ============================================================================
async def handle_webhook_fail(payload: dict) -> dict:
    source = payload.get("source") or "unknown"
    steps_log = []

    if source == "resend_email" and payload.get("to"):
        from orchestrator.engine import is_permanent_error, escalate_once
        err = payload.get("error") or ""
        if is_permanent_error(err):
            # LEARNING: eroare PERMANENTĂ de config detectată la prima trimitere —
            # nu programa niciun retry inutil, blochează direct și escaladează agregat.
            await db.orchestrator_retry_queue.insert_one({
                "id": uuid.uuid4().hex,
                "kind": "email",
                "payload": {"to": payload.get("to"), "subject": payload.get("subject"), "html": payload.get("html")},
                "attempts": 0,
                "max_attempts": 3,
                "status": "blocked_by_config",
                "last_detail": err,
                "created_at": _now(),
                "test": bool(payload.get("test")),
            })
            await escalate_once(
                "email_blocked_by_config",
                "🚨 Emailuri blocate de configurația Resend",
                f"Livrarea emailurilor eșuează cu eroare PERMANENTĂ de configurare: {err[:140]}. "
                "Verifică domeniul în Resend, apoi rulează «Reia emailurile blocate» din Orchestrator.",
            )
            steps_log.append({
                "action": "block_permanent_error", "ok": True,
                "detail": (
                    f"Eroare permanentă de config la prima trimitere — retry sărit complet, "
                    f"email păstrat recuperabil: {err[:120]}"
                ),
            })
            return {"steps": steps_log, "outcome": "blocked_config", "minutes_saved": 5, "escalate": False}
        await db.orchestrator_retry_queue.insert_one({
            "id": uuid.uuid4().hex,
            "kind": "email",
            "payload": {"to": payload.get("to"), "subject": payload.get("subject"), "html": payload.get("html")},
            "attempts": 0,
            "max_attempts": 3,
            "status": "pending",
            "next_retry_at": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
            "created_at": _now(),
            "test": bool(payload.get("test")),
        })
        steps_log.append({
            "action": "enqueue_email_retry", "ok": True,
            "detail": (
                f"Email '{(payload.get('subject') or '')[:60]}' pus în coada de retry "
                f"(max 3 încercări, backoff exponențial, primul retry în ~2 min)"
            ),
        })
        return {"steps": steps_log, "outcome": "retry_scheduled", "minutes_saved": 0, "escalate": False}

    if source == "stripe":
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        fails = await db.orchestrator_signals.count_documents({
            "kind": "webhook_fail",
            "payload.source": "stripe",
            "ts": {"$gte": cutoff},
        })
        steps_log.append({
            "action": "count_recent_stripe_failures", "ok": True,
            "detail": f"{fails} eșuări webhook Stripe în ultima oră (Stripe re-trimite automat evenimentul)",
        })
        if fails >= 3:
            return {
                "steps": steps_log,
                "outcome": "escalated",
                "minutes_saved": 5,
                "escalate": True,
                "escalation_title": "🚨 Webhook Stripe eșuează repetat",
                "escalation_body": f"{fails} eșuări de procesare webhook Stripe în ultima oră. Verifică cheile Stripe și logurile backend.",
            }
        return {"steps": steps_log, "outcome": "monitored", "minutes_saved": 5, "escalate": False}

    steps_log.append({"action": "classify_source", "ok": False, "detail": f"Sursă necunoscută: {source}"})
    return {"steps": steps_log, "outcome": "monitored", "minutes_saved": 0, "escalate": False}


# ============================================================================
# 4. CATEGORY VISIBILITY GATE (CIP-A Etapa 5)
# ============================================================================
async def handle_category_visibility(payload: dict) -> dict:
    from orchestrator.engine import notify_admins
    from construction.taxonomy import refresh_category_visibility
    steps_log = []
    res = await refresh_category_visibility()
    steps_log.append({
        "action": "recompute_visibility", "ok": True,
        "detail": (
            f"{res['visible_count']}/{res['total_nodes']} noduri vizibile public · "
            f"{res['visibility_changes']} schimbări de vizibilitate (trigger: {payload.get('trigger', 'necunoscut')})"
        ),
    })
    hp = res.get("hidden_with_potential") or []
    if hp:
        names = ", ".join(f"{h['name']} ({h['requests_90d']} cereri/90d)" for h in hp[:5])
        n = await notify_admins(
            "🏗️ Categorii ascunse cu potențial de business",
            f"{len(hp)} categorii au cereri de la clienți dar 0 specialiști verificați: {names}. Oportunitate de recrutare specialiști.",
            link="/admin/construction",
        )
        steps_log.append({
            "action": "flag_hidden_with_potential", "ok": True,
            "detail": f"{len(hp)} categorii cu cerere dar fără specialiști — {n} admini notificați",
        })
    else:
        steps_log.append({
            "action": "flag_hidden_with_potential", "ok": True,
            "detail": "Nicio categorie ascunsă cu cerere activă — acoperire OK",
        })
    return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 10, "escalate": False}


# ============================================================================
# 5. DISPUTE AI TRIAGE (Sprint 2)
# ============================================================================
DISPUTE_TRIAGE_SYSTEM = (
    "Ești arbitrul AI al platformei PropManage (marketplace servicii construcții România). "
    "Primești o dispută client-specialist și răspunzi DOAR cu JSON strict:\n"
    '{"category": "no_show|quality|price|communication|damage|other", '
    '"severity": "low|medium|high", "summary": "<1 frază în română>", '
    '"proposed_resolution": "<propunere concretă în română, 1-2 fraze>", '
    '"arguments": ["<arg1>", "<arg2>", "<arg3>"], '
    '"suggested_split": {"client_pct": <0-100>, "specialist_pct": <0-100>}}\n'
    "suggested_split = cum propui împărțirea sumei din escrow (client_pct = cât se returnează clientului). "
    "Fii echilibrat și bazează-te STRICT pe faptele furnizate. Nu inventa fapte."
)


async def compute_dispute_triage(dispute: dict, req: dict, test: bool = False) -> dict:
    """Reusable AI triage (Claude) → triage_doc. NU rezolvă disputa, doar clasifică + propune.
    Folosit atât de playbook-ul la deschidere, cât și de backfill-ul autonomiei (fără duplicare)."""
    if test:
        triage = {
            "category": "quality", "severity": "medium",
            "summary": "SIMULARE — clientul reclamă calitatea finisajului.",
            "proposed_resolution": "SIMULARE — refacere parțială de către specialist, escrow eliberat 70/30.",
            "arguments": ["Simulare argument 1", "Simulare argument 2", "Simulare argument 3"],
            "suggested_split": {"client_pct": 30, "specialist_pct": 70},
        }
    else:
        from orchestrator.llm import claude_json
        prompt = (
            f"Lucrare: {(req or {}).get('title', 'necunoscută')} · categoria {(req or {}).get('category', '?')} · "
            f"buget {(req or {}).get('budget_estimate', '?')} RON · escrow {(req or {}).get('escrow_amount', 0)} RON · "
            f"status {(req or {}).get('status', '?')}\n"
            f"Dispută deschisă de: {dispute.get('opened_by_role')}\n"
            f"Motiv invocat: {dispute.get('reason', '')[:1500]}"
        )
        triage = await claude_json(DISPUTE_TRIAGE_SYSTEM, prompt, "dispute_triage")
    return {
        "category": str(triage.get("category", "other"))[:30],
        "severity": str(triage.get("severity", "medium"))[:10],
        "summary": str(triage.get("summary", ""))[:400],
        "proposed_resolution": str(triage.get("proposed_resolution", ""))[:600],
        "arguments": [str(a)[:250] for a in (triage.get("arguments") or [])][:3],
        "suggested_split": triage.get("suggested_split") or {},
        "model": "claude-sonnet-4-5",
        "ran_at": _now(),
    }


async def handle_dispute_opened(payload: dict) -> dict:
    from bson import ObjectId
    from orchestrator.engine import notify_admins
    steps_log = []
    dispute_id = payload.get("dispute_id")
    dispute = await db.disputes.find_one({"_id": ObjectId(dispute_id)}) if dispute_id else None
    if not dispute and not payload.get("test"):
        return {"steps": [{"action": "load_dispute", "ok": False, "detail": f"Dispută {dispute_id} negăsită"}],
                "outcome": "error", "minutes_saved": 0, "escalate": False}
    req = await db.requests.find_one({"_id": ObjectId(dispute["request_id"])}) if dispute and dispute.get("request_id") else None

    try:
        triage_doc = await compute_dispute_triage(dispute, req, test=bool(payload.get("test")))
        steps_log.append({
            "action": "ai_classify", "ok": True,
            "detail": f"Categorie: {triage_doc.get('category')} · severitate: {triage_doc.get('severity')} · {str(triage_doc.get('summary', ''))[:120]}",
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[orchestrator] dispute triage LLM failed: {e}")
        return {"steps": [{"action": "ai_classify", "ok": False, "detail": str(e)[:200]}],
                "outcome": "error", "minutes_saved": 0, "escalate": False}

    if dispute:
        await db.disputes.update_one({"_id": dispute["_id"]}, {"$set": {"ai_triage": triage_doc}})
        steps_log.append({"action": "persist_triage", "ok": True, "detail": "Triage salvat pe dispută — vizibil în panoul admin"})
    else:
        steps_log.append({"action": "persist_triage", "ok": True, "detail": "SIMULARE — fără persistență (nicio dispută reală)"})

    n = await notify_admins(
        f"⚖️ Dispută triată AI: {triage_doc['category']} ({triage_doc['severity']})",
        f"„{(req or {}).get('title', 'lucrare')}\u201d — {triage_doc['summary']} Propunere: {triage_doc['proposed_resolution'][:150]}",
        link="/admin",
    )
    steps_log.append({"action": "notify_admins_inapp", "ok": True, "detail": f"{n} admini notificați cu propunerea de rezoluție"})
    return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 15, "escalate": False}


# ============================================================================
# 6. KYC PRE-VALIDATION REPORTER (Sprint 2 — recommendation mode, GDPR-safe)
# ============================================================================
async def handle_kyc_prevalidated(payload: dict) -> dict:
    from orchestrator.engine import notify_admins
    steps_log = []
    rec = payload.get("recommendation") or "review"
    score = payload.get("match_score")
    flags = payload.get("flags") or []
    name = payload.get("user_name") or "specialist"
    steps_log.append({
        "action": "ai_prevalidate_documents", "ok": True,
        "detail": f"KYC {name}: scor {score}/100 · flags: {', '.join(flags) or 'niciunul'} → {'RECOMANDAT SPRE APROBARE' if rec == 'approve' else 'NECESITĂ REVIEW MANUAL'}",
    })
    if rec == "approve":
        n = await notify_admins(
            f"✅ KYC pre-validat AI: {name} — recomandat spre aprobare",
            f"Scor potrivire {score}/100, fără flag-uri negative. Un click în coada KYC finalizează aprobarea (decizia rămâne umană).",
            link="/admin",
        )
    else:
        n = await notify_admins(
            f"🔍 KYC necesită review manual: {name}",
            f"Scor {score if score is not None else '—'}/100 · flags: {', '.join(flags) or 'analiză incompletă'}. Verifică documentele în coada KYC.",
            link="/admin",
        )
    steps_log.append({"action": "notify_admins_inapp", "ok": True, "detail": f"{n} admini notificați"})
    return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 8, "escalate": False}


# ============================================================================
# 7. MARKETPLACE MEDIC (Sprint 2 — auto-suspend / auto-reactivate)
# ============================================================================
MEDIC_DISPUTE_THRESHOLD = 3
MEDIC_REACTIVATE_DAYS = 30


async def handle_marketplace_medic(payload: dict) -> dict:
    from bson import ObjectId
    from orchestrator.engine import notify_admins
    steps_log = []
    now = datetime.now(timezone.utc)
    cutoff30 = (now - timedelta(days=30)).isoformat()

    per_spec: dict = {}
    async for d in db.disputes.find({"status": "open", "created_at": {"$gte": cutoff30}}, {"request_id": 1}):
        try:
            req = await db.requests.find_one({"_id": ObjectId(d["request_id"])}, {"specialist_id": 1})
        except Exception:  # noqa: BLE001
            req = None
        sid = (req or {}).get("specialist_id")
        if sid:
            per_spec[sid] = per_spec.get(sid, 0) + 1
    steps_log.append({
        "action": "scan_open_disputes_30d", "ok": True,
        "detail": f"{sum(per_spec.values())} dispute deschise (30d) pe {len(per_spec)} specialiști · prag suspendare: {MEDIC_DISPUTE_THRESHOLD}",
    })

    suspended, reactivated = [], []
    if not payload.get("test"):
        for sid, cnt in per_spec.items():
            if cnt < MEDIC_DISPUTE_THRESHOLD:
                continue
            u = await db.users.find_one({"_id": ObjectId(sid), "medic_suspended": {"$ne": True}})
            if not u:
                continue
            await db.users.update_one(
                {"_id": u["_id"]},
                {"$set": {"medic_suspended": True, "medic_suspended_at": _now(), "medic_suspend_reason": f"{cnt} dispute deschise în 30 zile"}},
            )
            suspended.append(f"{u.get('name')} ({cnt} dispute)")
            try:
                from services import notify
                await notify(sid, "Cont suspendat temporar din marketplace",
                             f"Ai {cnt} dispute deschise în ultimele 30 de zile. Profilul tău nu mai primește lucrări noi până la rezolvarea lor.",
                             type_="medic", link="/specialist")
            except Exception:  # noqa: BLE001
                pass

        reactivate_cutoff = (now - timedelta(days=MEDIC_REACTIVATE_DAYS)).isoformat()
        async for u in db.users.find({"medic_suspended": True}):
            sid = str(u["_id"])
            if per_spec.get(sid, 0) == 0 and (u.get("medic_suspended_at") or "") < reactivate_cutoff:
                await db.users.update_one(
                    {"_id": u["_id"]},
                    {"$set": {"medic_suspended": False, "medic_reactivated_at": _now()}},
                )
                reactivated.append(u.get("name") or sid)
                try:
                    from services import notify
                    await notify(sid, "Cont reactivat în marketplace",
                                 f"Felicitări — {MEDIC_REACTIVATE_DAYS} zile fără dispute. Profilul tău primește din nou lucrări.",
                                 type_="medic", link="/specialist")
                except Exception:  # noqa: BLE001
                    pass

    steps_log.append({
        "action": "apply_medic_actions", "ok": True,
        "detail": (
            f"Suspendați: {', '.join(suspended) or 'niciunul'} · Reactivați: {', '.join(reactivated) or 'niciunul'}"
            + (" (SIMULARE — fără modificări reale)" if payload.get("test") else "")
        ),
    })
    if suspended or reactivated:
        await notify_admins(
            "🩺 Marketplace Medic a acționat",
            f"Suspendați: {', '.join(suspended) or '—'} · Reactivați: {', '.join(reactivated) or '—'}",
            link="/admin/orchestrator",
        )
    actions = len(suspended) + len(reactivated)
    return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 5 + 12 * actions, "escalate": False}


async def marketplace_medic_cron() -> None:
    """Daily 05:10 — routed through the orchestrator."""
    from orchestrator.engine import emit_signal
    await emit_signal("marketplace_medic_scan", {"trigger": "cron_0510"})


async def handle_business_alert(payload: dict) -> dict:
    """CAO Roadmap 2.2 — alertele business devin semnale, nu doar UI.
    Primește digestul zilnic de la Command Center cron și notifică adminii
    o singură dată, agregat. Escaladează doar dacă există ≥5 urgențe."""
    from orchestrator.engine import notify_admins
    high = payload.get("high_warnings") or []
    total = payload.get("warnings_total", 0)
    health = payload.get("health_overall")
    steps = [{"action": "aggregate_business_alerts", "ok": True,
              "detail": f"{len(high)} urgente / {total} alerte · Business Health {health}"}]
    if high:
        lines = "\n".join(f"• {w.get('label')}" for w in high[:8])
        notified = await notify_admins(
            f"🚨 Command Center: {len(high)} urgențe azi (Health {health})",
            lines,
            link="/admin/command-center",
        )
        steps.append({"action": "notify_admins", "ok": True, "detail": f"{notified} admini notificați in-app"})
    return {
        "steps": steps,
        "outcome": "alerted" if high else "all_clear",
        "minutes_saved": 10 if high else 5,
        "escalate": len(high) >= 5,
        "escalation_title": f"🚨 {len(high)} urgențe business simultan — necesită om",
        "escalation_body": f"Business Health {health}. Vezi /admin/command-center.",
        "escalation_link": "/admin/command-center",
    }


# ============================================================================
# REGISTRY — signal kind → playbook
# ============================================================================
PLAYBOOKS = {
    "business_alert": {
        "id": "business_alert_router",
        "name": "Business Alert Router",
        "description": "Zilnic 07:00: alertele high-severity din Command Center (incl. departamentele Business Health în ROȘU) devin semnal orchestrator → notificare agregată adminilor + ledger. Escaladează cu email doar la ≥5 urgențe simultane (~10 min/zi).",
        "handler": handle_business_alert,
    },
    "smoke_fail": {
        "id": "smoke_fail_to_qa",
        "name": "Smoke-Fail → Auto QA Session",
        "description": "La eșuarea smoke test-ului: creează automat sesiune QA Copilot cu pașii eșuați ca findings + notifică adminii in-app. Elimină triajul manual (~20 min/incident).",
        "handler": handle_smoke_fail,
    },
    "autonomy_score_drop": {
        "id": "autonomy_reflex",
        "name": "Autonomy Reflex",
        "description": "La scădere >5pp a scorului de autonomie (general sau pe axă): rulează sweep corectiv + verifică recuperarea. Escaladează doar dacă scorul nu revine (~15 min/incident).",
        "handler": handle_autonomy_score_drop,
    },
    "webhook_fail": {
        "id": "webhook_retry_guardian",
        "name": "Webhook Retry Guardian",
        "description": "Email Resend eșuat → retry automat cu backoff (max 3). Webhook Stripe eșuat → monitorizare; alertă doar la ≥3 eșuări/oră (~10 min/incident).",
        "handler": handle_webhook_fail,
    },
    "category_visibility_refresh": {
        "id": "category_visibility_gate",
        "name": "Category Visibility Gate",
        "description": "CIP-A: recalculează automat vizibilitatea publică a nomenclatorului de construcții (nod vizibil = are ≥1 specialist verificat) la fiecare verificare specialist + zilnic 04:30. Flag-uiește categoriile ascunse cu cerere de la clienți (oportunitate recrutare).",
        "handler": handle_category_visibility,
    },
    "dispute_opened": {
        "id": "dispute_ai_triage",
        "name": "Dispute AI Triage",
        "description": "La deschiderea unei dispute: Claude clasifică (categorie + severitate), rezumă cazul și propune o rezoluție cu 3 argumente + împărțire escrow sugerată. Adminul primește cazul pre-lucrat (~15 min/dispută).",
        "handler": handle_dispute_opened,
    },
    "kyc_prevalidated": {
        "id": "kyc_prevalidation_reporter",
        "name": "KYC Pre-Validation (mod recomandare)",
        "description": "GDPR-safe: AI-ul pre-validează documentele KYC și marchează „Recomandat spre aprobare\u201d / „Necesită review\u201d — decizia finală rămâne la admin (1 click). Fără auto-aprobare (~8 min/dosar).",
        "handler": handle_kyc_prevalidated,
    },
    "marketplace_medic_scan": {
        "id": "marketplace_medic",
        "name": "Marketplace Medic",
        "description": f"Zilnic 05:10: suspendă automat specialiștii cu ≥{MEDIC_DISPUTE_THRESHOLD} dispute deschise/30 zile (excluși din matching & marketplace) și îi reactivează după {MEDIC_REACTIVATE_DAYS} zile curate. Menține calitatea marketplace-ului fără intervenție umană.",
        "handler": handle_marketplace_medic,
    },
}

from orchestrator.playbooks_sprint3 import SPRINT3_PLAYBOOKS  # noqa: E402
PLAYBOOKS.update(SPRINT3_PLAYBOOKS)

from orchestrator.playbooks_launch import LAUNCH_PLAYBOOKS  # noqa: E402
PLAYBOOKS.update(LAUNCH_PLAYBOOKS)
