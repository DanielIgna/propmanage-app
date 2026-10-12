"""Scheduler control — profiles, per-job edits, custom jobs, in-memory run history. Backs /admin/scheduler.

Profiles:
  full — every job on its original schedule.
  lite — only ESSENTIAL jobs run; THROTTLE_LITE ones run less often; everything else is paused
         (most jobs scan whole tables and burn database egress for reports nobody reads at low traffic).
Stored in db.scheduler_settings/_id="config":
  overrides   {job_id: {"enabled", "cron", "label", "category", "deleted"}} — win over the profile.
              A deleted code job is removed from the scheduler on every start and can be restored.
  custom_jobs [{"id", "task", "label", "category", "cron", "enabled"}] — extra schedules for the
              task of an existing code job (task = that job's id).

The scheduler only starts on Railway (or with SCHEDULER_ENABLED=true): a local backend must not run
cron jobs against the production database.
"""
import asyncio
import inspect
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone

import pytz
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED, EVENT_JOB_SUBMITTED
from apscheduler.triggers.cron import CronTrigger

from db import db

log = logging.getLogger("propmanage.job_control")
TZ = pytz.timezone("Europe/Bucharest")
PROFILES = ("full", "lite")

# job_id -> (category, description). Category drives the page grouping.
JOBS = {
    # business: e-mails, reminders, payments, marketplace flow
    "lead_followup_hourly": ("business", "Follow-up automat pentru lead-uri"),
    "specialist_followup_15min": ("business", "Follow-up specialiști pe cererile atribuite"),
    "daily_digest": ("business", "Digest zilnic pe e-mail pentru utilizatori"),
    "maintenance_due_daily": ("business", "Remindere mentenanță scadentă"),
    "renewal_reminder_daily": ("business", "Remindere de reînnoire abonament"),
    "warranty_auto_release": ("business", "Eliberare automată garanții (escrow)"),
    "dt_auto_reminders": ("business", "Remindere Digital Twin"),
    "onboarding_email_dispatch": ("business", "E-mailuri de onboarding"),
    "auto_match_cron_tick": ("business", "Potrivire automată cereri ↔ specialiști"),
    "automation_rules_tick": ("business", "Reguli Automation Center (DACĂ→ATUNCI)"),
    "preset_schedules": ("business", "Preseturi landing programate"),
    "orchestrator_retry_tick": ("business", "Reîncercare acțiuni eșuate (orchestrator)"),
    "sd_stale_request_escalation": ("business", "Escaladare cereri blocate"),
    "money_flow_guard_daily": ("business", "Verificare fluxuri de bani"),
    "finance_reconciler_daily": ("business", "Reconciliere financiară"),
    "sitemap_regen_daily": ("business", "Regenerare sitemap SEO"),
    "telemetry_retention_daily": ("business", "Curățare telemetrie veche"),
    "demo_accounts_reset": ("business", "Resetare conturi demo"),
    "daily_mongodb_backup": ("business", "Backup complet al bazei de date pe e-mail"),
    "email_drip_reminders": ("business", "E-mailuri drip (remindere)"),
    "email_weekly_newsletter": ("business", "Newsletter săptămânal"),
    # monitoring: health checks, sentinels, guardians
    "health_ping": ("monitoring", "Ping de sănătate (grafic /status)"),
    "smoke_test_monitor": ("monitoring", "Smoke tests automate"),
    "auth_health_alert": ("monitoring", "Alertă sănătate login Google"),
    "governance_watchdog": ("monitoring", "Watchdog guvernanță scheduler"),
    "audit_sentinel_hourly": ("monitoring", "Sentinel audit"),
    "incident_spike_alert": ("monitoring", "Alertă vârf de incidente"),
    "tenant_selfheal_nightly": ("monitoring", "Auto-reparare tenanți"),
    "cs_sentinel_daily": ("monitoring", "Customer Success Sentinel"),
    "health_repair_daily": ("monitoring", "Repair Engine — ciclu zilnic"),
    "journey_guardian_daily": ("monitoring", "Journey Guardian"),
    "architecture_guardian_daily": ("monitoring", "Architecture Guardian"),
    "product_guardian_daily": ("monitoring", "Product Guardian"),
    "marketplace_medic_daily": ("monitoring", "Marketplace Medic"),
    "construction_visibility_daily": ("monitoring", "Vizibilitate Construction"),
    "settings_snapshot_daily": ("monitoring", "Snapshot setări"),
    "autonomy_snapshot_daily": ("monitoring", "Snapshot autonomie"),
    # ai: autonomy, intelligence engines
    "sd_low_risk_autopilot": ("ai", "Autopilot AI — acțiuni cu risc mic"),
    "autonomy_operational_loop": ("ai", "Buclă operațională autonomă"),
    "sd_auto_materialize_todos": ("ai", "Generare automată TODO-uri"),
    "ai_sessions_sync": ("ai", "Sincronizare sesiuni AI"),
    "evolution_council_nightly": ("ai", "Evolution Council"),
    "autonomy_auto_tune_weekly": ("ai", "Auto-tune autonomie"),
    "autonomy_autopilot_daily": ("ai", "Autopilot zilnic"),
    "decision_review_daily": ("ai", "Revizuire decizii AI"),
    "ai_brain_discovery_daily": ("ai", "AI Brain — discovery"),
    "pattern_hunter_weekly": ("ai", "Pattern Hunter"),
    "roadmap_advisor_weekly": ("ai", "Roadmap Advisor"),
    "ai_daily_scan": ("ai", "Scanare AI zilnică"),
    "revenue_hunter_daily": ("ai", "Revenue Hunter"),
    "growth_intelligence_daily": ("ai", "Growth Intelligence"),
    "lead_intelligence_daily": ("ai", "Lead & Intent Intelligence"),
    "marketing_intelligence_daily": ("ai", "Marketing Intelligence"),
    "learning_outcomes_daily": ("ai", "Learning Engine — outcome scan"),
    "campaign_detection_daily": ("ai", "Detectare campanii"),
    "prop_benefits_daily": ("ai", "PropBenefits — scanare zilnică"),
    "specialist_auto_promotion_daily": ("ai", "Promovare automată specialiști"),
    "experience_tier_daily_promotion": ("ai", "Promovare Experience Tier"),
    "quests_daily_evaluation": ("ai", "Evaluare quests"),
    "tier_milestone_daily_sweep": ("ai", "Milestone-uri tier"),
    "menu_popularity_reorder_daily": ("ai", "Reordonare meniu după popularitate"),
    # reports: digests for founders/admins
    "morning_command_center": ("reports", "Morning Command Center"),
    "morning_briefing_digest": ("reports", "Morning Briefing"),
    "ai_daily_digest_email": ("reports", "Digest AI zilnic pe e-mail"),
    "ai_effectiveness_low_alert": ("reports", "Alertă eficiență AI scăzută"),
    "sd_weekly_lead_report": ("reports", "Raport săptămânal lead-uri"),
    "founder_digest_weekly": ("reports", "Founders' Digest"),
    "weekly_ai_briefing": ("reports", "Briefing AI săptămânal"),
    "future_ideas_digest": ("reports", "Digest idei viitoare"),
    "deprecation_pulse_weekly": ("reports", "Deprecation Pulse"),
    "it_sprint_digest_weekly": ("reports", "Digest sprint IT"),
    "weekly_dev_velocity": ("reports", "Dev Velocity"),
    "weekly_release_gate": ("reports", "Release Gate"),
    "weekly_exec_briefing": ("reports", "Executive Briefing"),
}

ESSENTIAL = {
    "lead_followup_hourly", "specialist_followup_15min", "daily_digest", "maintenance_due_daily",
    "renewal_reminder_daily", "warranty_auto_release", "dt_auto_reminders", "onboarding_email_dispatch",
    "auto_match_cron_tick", "automation_rules_tick", "preset_schedules", "orchestrator_retry_tick",
    "sd_stale_request_escalation", "money_flow_guard_daily", "finance_reconciler_daily",
    "sitemap_regen_daily", "telemetry_retention_daily", "demo_accounts_reset", "daily_mongodb_backup",
    "email_drip_reminders", "email_weekly_newsletter",
}

# lite: rarer schedules for essential jobs that ran too often
THROTTLE_LITE = {
    "daily_mongodb_backup": {"day_of_week": "sun", "hour": 3, "minute": 30},
    "specialist_followup_15min": {"minute": 5},
    "onboarding_email_dispatch": {"minute": 50},
    "orchestrator_retry_tick": {"minute": "*/30"},
}

CUSTOM_PREFIX = "custom_"
_DOW = ["sun", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_BASE: dict = {}       # code job id -> {"func", "args", "kwargs", "trigger"} (captured before any change)
_HISTORY: dict = {}    # job_id -> {last_run, duration_ms, ok, error, runs, failures}
_STARTED: dict = {}    # job_id -> monotonic start of the running scheduled execution
_MANUAL: dict = {}     # job_id -> asyncio.Task of a "run now" execution
STOPPED = "oprit manual"


def scheduler_enabled() -> bool:
    flag = (os.environ.get("SCHEDULER_ENABLED") or "").strip().lower()
    if flag in ("true", "1", "yes"):
        return True
    if flag in ("false", "0", "no"):
        return False
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


def parse_cron(expr: str) -> CronTrigger:
    """5-field crontab (min hour day month day_of_week), Europe/Bucharest. Raises ValueError."""
    parts = (expr or "").split()
    if len(parts) != 5:
        raise ValueError("Programul trebuie să aibă 5 câmpuri: minut oră zi lună zi_săptămână")
    # crontab numbers days 0/7=Sunday, APScheduler 0=Monday: use names so both read the same
    parts[4] = re.sub(r"(?<![/\d])([0-7])(?!\d)", lambda m: _DOW[int(m.group(1))], parts[4])
    return CronTrigger.from_crontab(" ".join(parts), timezone=TZ)


def _crontab(trigger) -> str | None:
    if not isinstance(trigger, CronTrigger):
        return None
    f = {x.name: str(x) for x in trigger.fields}
    return " ".join(f.get(k, "*") for k in ("minute", "hour", "day", "month", "day_of_week"))


def _describe_trigger(trigger) -> str:
    if isinstance(trigger, CronTrigger):
        f = {x.name: str(x) for x in trigger.fields}
        parts = [f"{k}={f[k]}" for k in ("day_of_week", "day", "month", "hour", "minute") if f.get(k) not in (None, "*")]
        return "cron " + (" ".join(parts) if parts else "în fiecare minut")
    return str(trigger)


def _capture(scheduler) -> None:
    """Remember every code job (function + original trigger) the first time it is seen."""
    for job in scheduler.get_jobs():
        if not job.id.startswith(CUSTOM_PREFIX) and job.id not in _BASE:
            _BASE[job.id] = {"func": job.func, "args": job.args, "kwargs": job.kwargs, "trigger": job.trigger}


async def load_settings() -> dict:
    doc = await db.scheduler_settings.find_one({"_id": "config"}) or {}
    profile = doc.get("profile") or (os.environ.get("SCHEDULER_PROFILE") or "lite").strip().lower()
    return {"profile": profile if profile in PROFILES else "lite",
            "overrides": doc.get("overrides") or {}, "custom_jobs": doc.get("custom_jobs") or []}


def _plan(job_id: str, settings: dict) -> dict:
    """Effective state of a job: enabled, deleted, trigger, label, category, custom, task."""
    custom = next((c for c in settings["custom_jobs"] if c["id"] == job_id), None)
    if custom:
        return {"enabled": bool(custom.get("enabled", True)), "deleted": False, "custom": True,
                "task": custom["task"], "trigger": parse_cron(custom["cron"]), "throttled": False,
                "label": custom.get("label") or custom["task"],
                "category": custom.get("category") or JOBS.get(custom["task"], ("other",))[0]}
    lite = settings["profile"] == "lite"
    ov = settings["overrides"].get(job_id) or {}
    category, label = JOBS.get(job_id, ("other", job_id))
    throttle = THROTTLE_LITE.get(job_id) if lite and not ov.get("cron") else None
    if ov.get("cron"):
        trigger = parse_cron(ov["cron"])
    elif throttle:
        trigger = CronTrigger(timezone=TZ, **throttle)
    else:
        trigger = _BASE[job_id]["trigger"] if job_id in _BASE else None
    return {"enabled": bool(ov["enabled"]) if "enabled" in ov else ((job_id in ESSENTIAL) if lite else True),
            "deleted": bool(ov.get("deleted")), "custom": False, "task": job_id, "trigger": trigger,
            "throttled": bool(throttle), "label": ov.get("label") or label, "category": ov.get("category") or category}


async def apply_job_settings(scheduler, settings: dict | None = None) -> dict:
    settings = settings or await load_settings()
    _capture(scheduler)
    if not scheduler.running:  # pending jobs have no next_run_time yet; applied after start
        return settings
    wanted = list(_BASE) + [c["id"] for c in settings["custom_jobs"]]
    for job in scheduler.get_jobs():  # custom jobs removed from the config
        if job.id.startswith(CUSTOM_PREFIX) and job.id not in wanted:
            scheduler.remove_job(job.id)
    for job_id in wanted:
        try:
            plan = _plan(job_id, settings)
        except ValueError as e:
            log.warning(f"[job_control] {job_id}: invalid schedule ({e})")
            continue
        job = scheduler.get_job(job_id)
        if plan["deleted"]:
            if job:
                scheduler.remove_job(job_id)
            continue
        base = _BASE.get(plan["task"])
        if not base or plan["trigger"] is None:
            continue
        if not job:
            job = scheduler.add_job(base["func"], plan["trigger"], args=base["args"], kwargs=base["kwargs"],
                                    id=job_id, replace_existing=True, misfire_grace_time=3600, coalesce=True)
        elif str(plan["trigger"]) != str(job.trigger):
            job = scheduler.reschedule_job(job_id, trigger=plan["trigger"])
        if not plan["enabled"] and job.next_run_time is not None:
            scheduler.pause_job(job_id)
        elif plan["enabled"] and job.next_run_time is None:
            scheduler.resume_job(job_id)
    return settings


async def update_settings(scheduler, mutate) -> dict:
    """Load the config, let `mutate(settings)` change it, validate, persist and apply it."""
    _capture(scheduler)
    settings = await load_settings()
    mutate(settings)
    for jid in list(_BASE) + [c["id"] for c in settings["custom_jobs"]]:
        _plan(jid, settings)  # raises ValueError on a bad cron
    await db.scheduler_settings.update_one(
        {"_id": "config"},
        {"$set": {"profile": settings["profile"], "overrides": settings["overrides"],
                  "custom_jobs": settings["custom_jobs"], "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return await apply_job_settings(scheduler, settings)


def new_custom_id() -> str:
    return CUSTOM_PREFIX + uuid.uuid4().hex[:10]


def is_known(job_id: str, settings: dict) -> bool:
    return job_id in _BASE or any(c["id"] == job_id for c in settings["custom_jobs"])


# ---------------------------------------------------------------- run history (memory only)
def _on_event(event):
    jid = event.job_id
    if event.code == EVENT_JOB_SUBMITTED:
        _STARTED[jid] = time.monotonic()
        return
    h = _HISTORY.setdefault(jid, {"runs": 0, "failures": 0})
    started = _STARTED.pop(jid, None)
    h["last_run"] = datetime.now(timezone.utc).isoformat()
    h["duration_ms"] = int((time.monotonic() - started) * 1000) if started else None
    if event.code == EVENT_JOB_MISSED:
        h["ok"], h["error"] = False, "misfire (rulare ratată)"
        h["failures"] += 1
        return
    h["runs"] += 1
    h["ok"] = event.code == EVENT_JOB_EXECUTED
    exc = getattr(event, "exception", None)
    h["error"] = None if h["ok"] else (STOPPED if isinstance(exc, asyncio.CancelledError) else str(exc or "eroare")[:300])
    if not h["ok"]:
        h["failures"] += 1


def attach_history(scheduler) -> None:
    scheduler.add_listener(_on_event, EVENT_JOB_SUBMITTED | EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED)


async def _run_task(job_id: str, task: str) -> None:
    base = _BASE[task]
    h = _HISTORY.setdefault(job_id, {"runs": 0, "failures": 0})
    start = time.monotonic()
    try:
        res = base["func"](*base["args"], **base["kwargs"])
        if inspect.isawaitable(res):
            await res
        h["ok"], h["error"] = True, None
    except asyncio.CancelledError:
        h["ok"], h["error"] = False, STOPPED
        h["failures"] += 1
    except Exception as e:  # noqa: BLE001
        h["ok"], h["error"] = False, str(e)[:300]
        h["failures"] += 1
        log.warning(f"[job_control] manual run {job_id} failed: {e}")
    finally:
        h["runs"] += 1
        h["last_run"] = datetime.now(timezone.utc).isoformat()
        h["duration_ms"] = int((time.monotonic() - start) * 1000)
        _MANUAL.pop(job_id, None)


def run_now(job_id: str, task: str) -> bool:
    """Start a job's task immediately (even if paused/deleted), outside its schedule. False if already running."""
    if job_id in _MANUAL:
        return False
    _MANUAL[job_id] = asyncio.get_running_loop().create_task(_run_task(job_id, task))
    return True


def _scheduled_tasks(scheduler, job_id: str) -> list:
    """asyncio tasks of in-flight scheduled runs of a job (coroutine jobs only; thread jobs can't be stopped)."""
    try:
        futures = scheduler._lookup_executor("default")._pending_futures
    except Exception:  # noqa: BLE001
        return []
    out = []
    for f in list(futures):
        coro = f.get_coro() if isinstance(f, asyncio.Task) else None
        frame = getattr(coro, "cr_frame", None)
        job = frame.f_locals.get("job") if frame else None
        if job is not None and getattr(job, "id", None) == job_id and not f.done():
            out.append(f)
    return out


def is_running(scheduler, job_id: str) -> bool:
    return job_id in _MANUAL or job_id in _STARTED


def stop(scheduler, job_id: str) -> bool:
    """Cancel a running execution (manual or scheduled). True if something was cancelled."""
    tasks = ([_MANUAL[job_id]] if job_id in _MANUAL else []) + _scheduled_tasks(scheduler, job_id)
    for t in tasks:
        t.cancel()
    return bool(tasks)


async def snapshot(scheduler) -> dict:
    _capture(scheduler)
    settings = await load_settings()
    jobs, deleted = [], []
    for job_id in list(_BASE) + [c["id"] for c in settings["custom_jobs"]]:
        try:
            plan = _plan(job_id, settings)
        except ValueError:
            continue
        job = scheduler.get_job(job_id)
        ov = settings["overrides"].get(job_id) or {}
        row = {
            "id": job_id, "task": plan["task"], "label": plan["label"], "category": plan["category"],
            "enabled": plan["enabled"], "custom": plan["custom"], "essential": job_id in ESSENTIAL,
            "edited": bool(set(ov) - {"deleted"}),
            "schedule": _describe_trigger(plan["trigger"]), "cron": _crontab(plan["trigger"]) or "",
            "original_schedule": _describe_trigger(_BASE[job_id]["trigger"]) if job_id in _BASE else None,
            "throttled": plan["throttled"],
            "next_run": nxt.isoformat() if job and (nxt := getattr(job, "next_run_time", None)) else None,
            "history": _HISTORY.get(job_id),
            "is_running": is_running(scheduler, job_id),
        }
        (deleted if plan["deleted"] else jobs).append(row)
    jobs.sort(key=lambda j: (not j["enabled"], j["category"], j["label"].lower()))
    tasks = sorted(({"id": t, "label": JOBS.get(t, ("other", t))[1]} for t in _BASE), key=lambda t: t["label"].lower())
    return {
        "running": bool(scheduler.running), "enabled_here": scheduler_enabled(),
        "profile": settings["profile"],
        "overrides": sum(1 for v in settings["overrides"].values() if set(v) - {"deleted"}),
        "total": len(jobs), "active": sum(1 for j in jobs if j["enabled"]),
        "jobs": jobs, "deleted": deleted, "tasks": tasks,
        "categories": ["business", "monitoring", "ai", "reports", "other"],
    }
