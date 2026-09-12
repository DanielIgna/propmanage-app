"""Self-Driving Automations — țintă: 90%+ autonomie fără intervenție umană.

5 automatizări safe, toate logate în playbook_executions + orchestrator ledger:
1. Low-Risk Autopilot: auto-închide TODO-uri Autonomy rezolvate + auto-aprobă approvals low-risk
2. Auto-Materialize: recomandările Autonomy devin automat TODO-uri (zilnic, după snapshot)
3. Stale Request Escalation: cereri fără oferte >24h → re-notificare specialiști, criterii lărgite
4. Weekly Lead Report: raport săptămânal lead-uri Design Interior către admini
5. (în orchestrator/playbooks.py) Self-Healing Smoke: retry automat + fix-uri din Bug Memory
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/self-driving", tags=["self-driving"])
logger = logging.getLogger("propmanage.self_driving")

DEFAULT_SETTINGS = {
    "low_risk_autopilot": True,
    "low_risk_actions": ["kyc_prevalidated", "content_publish", "auto_match_toggle"],
    "auto_materialize_todos": True,
    "stale_request_escalation": True,
    "lead_triage": True,
    "self_healing_smoke": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_settings() -> dict:
    doc = await db.self_driving_settings.find_one({"key": "main"}) or {}
    return {**DEFAULT_SETTINGS, **{k: doc[k] for k in DEFAULT_SETTINGS if k in doc}}


async def _log_run(job: str, status: str, detail: dict) -> None:
    await db.playbook_executions.insert_one({
        "playbook_id": f"self_driving:{job}",
        "status": status,
        "human_needed": False,
        "detail": detail,
        "ts": _now(),
    })


# ── 1. LOW-RISK AUTOPILOT (rulează la 2h) ─────────────────────────────────────
async def low_risk_autopilot_tick() -> dict:
    s = await get_settings()
    if not s["low_risk_autopilot"]:
        return {"status": "skipped"}
    out = {"todos_auto_closed": 0, "approvals_auto_approved": 0, "approvals_failed": 0}

    # a) TODO-uri generate de Autonomy a căror recomandare a dispărut → done automat
    try:
        from routes.autonomy import load_targets, compute_autonomy_scores
        cfg = await load_targets()
        report = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
        current_actions = {str(r.get("action", ""))[:60].lower() for r in (report.get("recommendations") or [])}
        todos = await db.admin_todos.find({"source": {"$regex": "^autonomy_v2:"}, "done": False}).to_list(100)
        for todo in todos:
            text = str(todo.get("text", ""))
            action_part = text.split("] ", 1)[-1][:60].lower()
            if action_part and action_part not in current_actions:
                await db.admin_todos.update_one(
                    {"id": todo["id"]},
                    {"$set": {"done": True, "done_at": _now(), "done_by": "autonomy:self_driving"}},
                )
                out["todos_auto_closed"] += 1
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[self-driving] todo auto-close fail: {e}")

    # b) Approvals pending cu acțiuni low-risk, mai vechi de 1h → auto-approve + execuție
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        pending = await db.admin_approvals.find({
            "status": "pending",
            "action": {"$in": s["low_risk_actions"]},
            "created_at": {"$lte": cutoff},
        }).to_list(20)
        if pending:
            from routes.admin_approvals import _exec_registered
            decider = {"email": "autonomy@propmanage.ai", "name": "Self-Driving Autopilot", "role": "admin"}
            for ap in pending:
                try:
                    result = await _exec_registered(ap["action"], ap.get("payload") or {}, decider)
                    await db.admin_approvals.update_one(
                        {"id": ap["id"]},
                        {"$set": {"status": "executed", "decided_by": decider["email"], "decided_at": _now(),
                                  "note": "Auto-aprobat de Self-Driving Autopilot (acțiune low-risk).", "exec_result": result}},
                    )
                    out["approvals_auto_approved"] += 1
                except Exception as e:  # noqa: BLE001
                    # rollback-safe: rămâne pending, marcăm eșecul, adminul decide manual
                    await db.admin_approvals.update_one(
                        {"id": ap["id"]},
                        {"$set": {"note": f"Auto-approve eșuat: {str(e)[:150]} — necesită decizie umană."}},
                    )
                    out["approvals_failed"] += 1
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[self-driving] approvals autopilot fail: {e}")

    await _log_run("low_risk_autopilot", "applied" if (out["todos_auto_closed"] or out["approvals_auto_approved"]) else "no_change", out)
    return {"status": "ok", **out}


# ── 2. AUTO-MATERIALIZE RECOMANDĂRI → TODO-uri (zilnic 03:45) ─────────────────
async def auto_materialize_tasks_job() -> dict:
    s = await get_settings()
    if not s["auto_materialize_todos"]:
        return {"status": "skipped"}
    try:
        from routes.autonomy import materialize_recommendations
        result = await materialize_recommendations(max_items=6, min_impact=0.5, dry_run=False)
        counts = result.get("counts", {})
        await _log_run("auto_materialize_todos", "applied" if counts.get("injected") else "no_change", counts)
        return {"status": "ok", **counts}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[self-driving] auto materialize fail: {e}")
        await _log_run("auto_materialize_todos", "error", {"error": str(e)[:200]})
        return {"status": "error"}


# ── 3. STALE REQUEST ESCALATION (la 6h) ───────────────────────────────────────
async def stale_request_escalation_tick() -> dict:
    s = await get_settings()
    if not s["stale_request_escalation"]:
        return {"status": "skipped"}
    from services import notify
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    stale = await db.requests.find({
        "status": "open",
        "created_at": {"$lte": cutoff},
        "autonomy_escalated_at": {"$exists": False},
    }).to_list(20)
    escalated = 0
    for req in stale:
        rid = str(req["_id"])
        offers = await db.marketplace_offers.count_documents({"request_id": rid, "status": {"$ne": "withdrawn"}})
        if offers > 0:
            continue
        # criterii lărgite: toți specialiștii verificați, nu doar cei cu specialitatea exactă
        specs = await db.users.find({"role": "specialist", "verified": True}).to_list(50)
        for sp in specs:
            try:
                await notify(
                    str(sp["_id"]),
                    "🔥 Cerere fără oferte — șansă mare de câștig",
                    f"«{req.get('title','Cerere')}» ({req.get('category','')}) așteaptă oferte de peste 24h. Fii primul care ofertează — vizibilitate bonus!",
                    type_="opportunity", link="/specialist",
                )
            except Exception:  # noqa: BLE001
                pass
        await db.requests.update_one(
            {"_id": req["_id"]},
            {"$set": {"autonomy_escalated_at": _now(), "visibility_boost": True}},
        )
        escalated += 1
    if escalated:
        try:
            from orchestrator.engine import write_ledger
            await write_ledger({
                "signal_kind": "stale_request", "playbook_id": "stale_request_escalation",
                "playbook_name": "Stale Request Escalation",
                "steps": [{"action": "re_notify_specialists", "ok": True, "detail": f"{escalated} cereri escaladate, specialiști re-notificați, boost vizibilitate"}],
                "outcome": "auto_resolved", "minutes_saved": escalated * 15, "escalated": False, "test": False,
            })
        except Exception:  # noqa: BLE001
            pass
    await _log_run("stale_request_escalation", "applied" if escalated else "no_change", {"escalated": escalated, "checked": len(stale)})
    return {"status": "ok", "escalated": escalated}


# ── 4. WEEKLY LEAD REPORT (luni 09:00) ────────────────────────────────────────
async def weekly_lead_report_job() -> dict:
    s = await get_settings()
    if not s["lead_triage"]:
        return {"status": "skipped"}
    from orchestrator.engine import notify_admins
    import leads_store
    s7 = await leads_store.summary(days=7)
    leads = await db.interior_design_leads.find({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()}}).to_list(500)
    contacted = sum(1 for x in leads if x.get("status") in ("contacted", "won"))
    src_txt = " · ".join(f"{k}: {v}" for k, v in s7.get("by_source", {}).items()) or "fără lead-uri noi"
    body = (f"Săptămâna trecută: {s7['total']} lead-uri TOTAL pe platformă ({s7['hot']} HOT 🔥) — {src_txt}. "
            f"Design Interior: {contacted} contactate. Triage-ul AI rulează automat pe toate sursele.")
    n = await notify_admins("📋 Raport săptămânal lead-uri (toate sursele)", body, link="/admin/interior-design")
    await _log_run("weekly_lead_report", "applied", {**s7, "admins_notified": n})
    return {"status": "ok", **s7}


# ── API ───────────────────────────────────────────────────────────────────────
_JOBS = {
    "low_risk_autopilot": low_risk_autopilot_tick,
    "auto_materialize_todos": auto_materialize_tasks_job,
    "stale_request_escalation": stale_request_escalation_tick,
    "weekly_lead_report": weekly_lead_report_job,
}


@router.get("/settings")
async def get_sd_settings(_admin=Depends(require_role("admin"))):
    return await get_settings()


@router.put("/settings")
async def put_sd_settings(payload: dict = Body(...), admin=Depends(require_role("admin"))):
    clean = {k: payload[k] for k in DEFAULT_SETTINGS if k in payload}
    if "low_risk_actions" in clean and not isinstance(clean["low_risk_actions"], list):
        clean.pop("low_risk_actions")
    await db.self_driving_settings.update_one(
        {"key": "main"},
        {"$set": {**clean, "updated_at": _now(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, **(await get_settings())}


@router.get("/status")
async def sd_status(_admin=Depends(require_role("admin"))):
    runs = await db.playbook_executions.find(
        {"playbook_id": {"$regex": "^self_driving:"}}, {"_id": 0}
    ).sort("ts", -1).to_list(20)
    return {"settings": await get_settings(), "recent_runs": runs}


@router.post("/run/{job}")
async def run_sd_job(job: str, _admin=Depends(require_role("admin"))):
    fn = _JOBS.get(job)
    if not fn:
        return {"ok": False, "error": "Job necunoscut", "available": list(_JOBS.keys())}
    result = await fn()
    return {"ok": True, "job": job, **result}
