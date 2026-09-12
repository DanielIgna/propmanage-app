"""PropManage Backend — FastAPI app entry point.

After Phase B refactor, all endpoints live in routes/*.py modules.
This file only wires the app: CORS, lifecycle hooks, scheduler, router includes.
"""
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Internal foundation modules
from db import client
from seed import seed
from digest import run_daily_digests, BUCHAREST_TZ_NAME

# All API routers (registration order preserved) — see routes/register.py
from routes.register import ALL_ROUTERS

# Scheduled jobs, seeds & helpers exported by route modules
from routes.projects import auto_release_warranty_holds
from routes.admin import run_auto_match_cron_tick
from routes.admin_console import run_due_preset_schedules, run_incident_spike_alert_check
from routes.digital_twin import run_dt_auto_reminders
from routes.admin_ai import run_daily_ai_digest, send_daily_ai_digest_email, run_ai_effectiveness_alert_check
from routes.auth import run_auth_health_alert_check
from routes.public import record_health_ping
from routes.admin_smoketest import run_smoke_test_monitor_tick
from executive_briefing import run_exec_briefing_job
from routes.verified_estate import seed_demo_listings as seed_verified_estate_demo
from routes.settings_snapshots import take_auto_snapshot
from routes.autonomy import weekly_auto_tune_job
from autonomy.snapshots import take_autonomy_snapshot_with_reflex
from orchestrator.engine import orchestrator_retry_tick
from construction.taxonomy import construction_visibility_cron
from orchestrator.playbooks import marketplace_medic_cron
from orchestrator.playbooks_sprint3 import pattern_hunter_cron, finance_reconciler_cron, roadmap_advisor_cron
from maintenance import telemetry_retention_tick
from routes.house_health_billing import seed_default_plans as hh_seed_default_plans
from autonomy.founder_digest import weekly_founder_digest
from autonomy.autopilot import bootstrap_autonomy_defaults, daily_autopilot_sweep
from routes.ai_weekly_briefing import run_weekly_briefing_job
from routes.future_ideas_digest import run_future_ideas_digest_job
from routes.deprecation_pulse import run_deprecation_pulse_job
from routes.experience_tiers import run_promotion_job as run_experience_tier_promotion_job
from routes.feature_configurator import evaluate_quests_job
from routes.specialist_progression import run_auto_promotion
from routes.community import seed_community_demo
from routes.tier_milestones import cron_check_all_users
from routes.it_digest import run_weekly_it_sprint_digest, _get_settings as _it_digest_get_settings
from routes.legal import seed_default_legal_documents
from routes.demo_activity import schedule_log as _schedule_demo_log
from routes.site_menu import menu_popularity_reorder_tick
from autonomy.self_driving import (
    low_risk_autopilot_tick,
    auto_materialize_tasks_job,
    stale_request_escalation_tick,
    weekly_lead_report_job,
)
from middleware_scope import admin_scope_middleware
from admin_briefing_digest import run_morning_briefing_job
from backup_service import run_daily_backup_job
from dev_velocity_service import run_weekly_velocity_job
from onboarding_emails import run_onboarding_dispatch_job
from qa_automation import run_weekly_release_gate_job
from demo_reset import reset_demo_accounts

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="PropManage API")

# CORS: read from env, support "*" wildcard for dev OR comma-separated origins for prod.
# Default regex auto-permits both preview (*.preview.emergentagent.com) AND the production
# custom domain (*.propmanage.ro) so cookies/credentials work cross-origin out of the box.
_raw_origins = os.environ.get("CORS_ORIGINS", "*").strip()
_default_origin_regex = r"^https?://(.*\.)?(propmanage\.ro|propmanage\.io|preview\.emergentagent\.com|emergentagent\.com)$"
_origin_regex = os.environ.get("CORS_ORIGIN_REGEX") or _default_origin_regex
if _raw_origins == "*" or not _raw_origins:
    # Use empty allow_origins + regex so allow_credentials=True can still work
    # (browsers reject credentials only with literal "*", not with regex matches).
    _origins = []
    _allow_credentials = True
else:
    _origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    _allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=_origin_regex,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Admin-scope HTTP middleware (Milestone 2): URL-pattern → required-scope map
app.middleware("http")(admin_scope_middleware)

# CSRF origin guard (SEC-002 remediere Iun 2026): browserele trimit MEREU
# header-ul Origin pe mutații cross-site — dacă Origin există și NU e într-un
# domeniu permis, blocăm. Cererile fără Origin (curl/server-to-server/tests)
# trec — nu sunt vector CSRF de browser.
import re as _re  # noqa: E402
from urllib.parse import urlparse as _urlparse  # noqa: E402
from starlette.responses import JSONResponse as _JSONResponse  # noqa: E402

# Sufixe de host permise: domeniile produsului + infrastructura de preview
# (ingress-ul Emergent rescrie Origin către *.emergentcf.cloud).
_CSRF_ALLOWED_SUFFIXES = ("propmanage.ro", "propmanage.io",
                          "preview.emergentagent.com", "emergentagent.com",
                          "emergentcf.cloud", "localhost")


def _csrf_origin_ok(origin: str, host: str) -> bool:
    try:
        h = (_urlparse(origin).hostname or "").lower()
    except Exception:  # noqa: BLE001
        return False
    if not h:
        return False
    if host and h == host.split(":")[0].lower():
        return True  # same-origin
    return any(h == s or h.endswith("." + s) for s in _CSRF_ALLOWED_SUFFIXES)


@app.middleware("http")
async def _csrf_origin_guard(request, call_next):
    """CSRF guard pe mutațiile /api/admin (SEC-002).

    Blocăm DOAR cereri de browser (au header Origin) care fie vin de pe un
    origin nepermis, fie nu poartă header-ul custom X-PM-Client (formularele
    HTML cross-site nu pot seta headere custom; fetch cross-site credentialed
    pică la preflight). Cererile fără Origin (curl/server-to-server/tests)
    nu sunt vector CSRF de browser și trec.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/admin"):
        origin = request.headers.get("origin")
        if origin:
            origin_ok = _csrf_origin_ok(origin, request.headers.get("host", ""))
            header_ok = request.headers.get("x-pm-client") == "propmanage-app"
            if not origin_ok or not header_ok:
                logging.getLogger("propmanage.csrf").warning(
                    "[csrf] blocked origin=%r origin_ok=%s header_ok=%s method=%s path=%s",
                    origin, origin_ok, header_ok, request.method, request.url.path)
                return _JSONResponse({"detail": "Cross-site request blocked (CSRF guard)"}, status_code=403)
    return await call_next(request)


# Rate limiting pe endpoint-urile publice (TD-07, EO-026 Phase 1)
from rate_limit import rate_limit_middleware  # noqa: E402
app.middleware("http")(rate_limit_middleware)


@app.middleware("http")
async def _demo_activity_middleware(request, call_next):
    """Log every API call made by demo sub-admins (fire-and-forget)."""
    import time as _t
    start = _t.time()
    response = await call_next(request)
    try:
        # Only act on /api/* paths
        if request.url.path.startswith("/api/"):
            # Try to resolve user from request state (set by deps.get_current_user)
            user = getattr(request.state, "user", None)
            if user:
                duration_ms = int((_t.time() - start) * 1000)
                _schedule_demo_log(user, request, response.status_code, duration_ms)
    except Exception:  # noqa: BLE001
        pass
    return response


logger = logging.getLogger(__name__)
logger.info(f"CORS configured: origins={_origins} regex={_origin_regex} credentials={_allow_credentials}")

# Register all routers (order preserved — see routes/register.py)
for r in ALL_ROUTERS:
    app.include_router(r)

# Daily digest scheduler (19:00 Europe/Bucharest)
scheduler = AsyncIOScheduler(timezone=pytz.timezone(BUCHAREST_TZ_NAME))


async def _lead_followup_tick():
    from lead_followup import run_autonomous_cycle
    await run_autonomous_cycle(trigger="scheduler")


async def _specialist_followup_tick():
    from specialist_followup import run_all_sequences
    await run_all_sequences()


async def _tenant_selfheal_tick():
    # Val 2 self-healing: orice insert T1 rămas fără tenant_id primește 'main' noaptea
    from tenancy import backfill_tier1_tenant_data
    await backfill_tier1_tenant_data(force=True)


async def _maintenance_due_tick():
    from routes.maintenance_calendar import maintenance_due_tick
    await maintenance_due_tick()


async def _campaign_detection_tick():
    from routes.community_buildings import campaign_detection_tick
    await campaign_detection_tick()


async def _pb_daily_tick():
    from routes.prop_benefits import pb_daily_tick
    await pb_daily_tick()


async def _cs_sentinel_tick():
    from routes.launch_sentinel import cs_sentinel_tick
    await cs_sentinel_tick()


async def _money_flow_tick():
    from routes.launch_sentinel import money_flow_tick
    await money_flow_tick()


async def _sitemap_regen_tick():
    from routes.public import write_sitemap_file
    await write_sitemap_file()


@app.on_event("startup")
async def startup():
    await seed()
    try:
        from tenancy import ensure_main_tenant, backfill_user_tenants, backfill_tier1_tenant_data
        await ensure_main_tenant()
        await backfill_user_tenants()
        await backfill_tier1_tenant_data()
        from kg.registry import seed_registry
        await seed_registry()
    except Exception as e:
        logger.warning(f"Tenant seed failed: {e}")
    try:
        await hh_seed_default_plans()
    except Exception as e:
        logger.warning(f"House Health plans seed failed: {e}")
    # Demo seeds — DOAR când SEED_DEMO_DATA=true (EO-026: producția rulează fără date demo)
    seed_demo = (os.environ.get("SEED_DEMO_DATA") or "").strip().lower() == "true"
    if seed_demo:
        try:
            await seed_verified_estate_demo()
        except Exception as e:
            logger.warning(f"Verified Estate demo seed failed: {e}")
        try:
            await seed_community_demo()
        except Exception as e:
            logger.warning(f"Community demo seed failed: {e}")
        try:
            from tier_demo_seed import seed_tier_demo_users
            await seed_tier_demo_users()
        except Exception as e:
            logger.warning(f"Tier demo seed failed: {e}")
    # GDPR Phase 1 — backfill existing users with consent + verification fields (idempotent)
    try:
        from consent_backfill import run_consent_backfill
        await run_consent_backfill()
    except Exception as e:
        logger.warning(f"Consent backfill failed: {e}")
    # Autonomy autopilot — enable smoke-monitor, auto-match schedule, fresh snapshot (idempotent)
    try:
        await bootstrap_autonomy_defaults()
    except Exception as e:
        logger.warning(f"Autonomy autopilot bootstrap failed: {e}")
    # CIP-A: seed nomenclator construcții + gate inițial de vizibilitate (idempotent)
    try:
        from construction.taxonomy import seed_construction_taxonomy, refresh_category_visibility
        await seed_construction_taxonomy()
        await refresh_category_visibility()
    except Exception as e:
        logger.warning(f"Construction taxonomy bootstrap failed: {e}")
    # CIP-B: seed Price Observatory cu date orientative (idempotent)
    try:
        from construction.prices import seed_price_observations
        await seed_price_observations()
    except Exception as e:
        logger.warning(f"Price observatory bootstrap failed: {e}")
    # Sub-admin RBAC — seed demo scoped admins (testing/frontend/backend/security)
    if seed_demo:
        try:
            from sub_admin_seed import seed_sub_admins
            await seed_sub_admins()
        except Exception as e:
            logger.warning(f"Sub-admin seed failed: {e}")
    try:
        await seed_default_legal_documents()
    except Exception as e:
        logger.warning(f"Legal docs seed failed: {e}")
    # SEO — scrie sitemap.xml la rădăcina domeniului (frontend/public/sitemap.xml)
    try:
        from routes.public import write_sitemap_file
        await write_sitemap_file()
    except Exception as e:
        logger.warning(f"Sitemap file generation failed: {e}")
    if not scheduler.running:
        scheduler.add_job(
            _lead_followup_tick,
            CronTrigger(minute=25, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="lead_followup_hourly",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        # Faza 3 — specialist_entry follow-up (reminder 1h + nurture 24h). Rulează la fiecare 15 min.
        scheduler.add_job(
            _specialist_followup_tick,
            CronTrigger(minute="*/15", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="specialist_followup_15min",
            replace_existing=True,
            misfire_grace_time=900,
        )
        scheduler.add_job(
            _tenant_selfheal_tick,
            CronTrigger(hour=4, minute=15, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="tenant_selfheal_nightly",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            run_daily_digests,
            CronTrigger(hour=19, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="daily_digest",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # CX-4: remindere mentenanță (09:00) — taskuri scadente în ≤7 zile
        scheduler.add_job(
            _maintenance_due_tick,
            CronTrigger(hour=9, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="maintenance_due_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # PM-002/PM-003: detecție automată campanii comune (08:30)
        scheduler.add_job(
            _campaign_detection_tick,
            CronTrigger(hour=8, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="campaign_detection_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # SEO: regenerare sitemap.xml static (03:30) — reflectă specialiști/pagini noi
        scheduler.add_job(
            _sitemap_regen_tick,
            CronTrigger(hour=3, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="sitemap_regen_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # PB-001: PropBenefits (08:45) — expirare beneficii + activare referral + snapshot Subscription Health
        scheduler.add_job(
            _pb_daily_tick,
            CronTrigger(hour=8, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="prop_benefits_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Firul B: CS Sentinel (09:30) — remindere onboarding/activare pentru administratori
        scheduler.add_job(
            _cs_sentinel_tick,
            CronTrigger(hour=9, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="cs_sentinel_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Firul B: Money-Flow Guard (07:45) — Stripe/email/coadă retry + detecție prima plată
        scheduler.add_job(
            _money_flow_tick,
            CronTrigger(hour=7, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="money_flow_guard_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            take_auto_snapshot,
            CronTrigger(hour=4, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="settings_snapshot_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            menu_popularity_reorder_tick,
            CronTrigger(hour=4, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="menu_popularity_reorder_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Task 8 · Renewal Reminder — daily at 09:15 Bucharest.
        try:
            from routes.renewal_reminders import renewal_reminder_tick
            scheduler.add_job(
                renewal_reminder_tick,
                CronTrigger(hour=9, minute=15, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
                id="renewal_reminder_daily",
                replace_existing=True,
                misfire_grace_time=3600,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("renewal_reminder scheduler wire failed: %s", exc)
        # Self-Driving Automations — țintă 90%+ autonomie
        scheduler.add_job(
            low_risk_autopilot_tick,
            CronTrigger(hour="*/2", minute=10, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="sd_low_risk_autopilot",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        scheduler.add_job(
            auto_materialize_tasks_job,
            CronTrigger(hour=3, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="sd_auto_materialize_todos",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            stale_request_escalation_tick,
            CronTrigger(hour="*/6", minute=20, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="sd_stale_request_escalation",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        # Operational Autonomy Loop (FN-021) — Analytics→Finding→Decizie→Acțiune→Verify→Learn
        try:
            from autonomy.loop import run_loop_tick as _op_loop_tick
            scheduler.add_job(
                lambda: _op_loop_tick(triggered_by="scheduler"),
                CronTrigger(hour="*/3", minute=35, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
                id="autonomy_operational_loop",
                replace_existing=True,
                misfire_grace_time=1800,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("operational_loop scheduler wire failed: %s", exc)
        scheduler.add_job(
            weekly_lead_report_job,
            CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="sd_weekly_lead_report",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        from ai_session_store import sync_all as ai_sessions_sync
        scheduler.add_job(
            ai_sessions_sync,
            CronTrigger(minute="*/30", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="ai_sessions_sync",
            replace_existing=True,
            misfire_grace_time=900,
        )
        scheduler.add_job(
            take_autonomy_snapshot_with_reflex,
            CronTrigger(hour=3, minute=15, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="autonomy_snapshot_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # AI 27 — Enterprise Evolution Council: ședința automată nightly (Rezoluția 003)
        from routes.evolution_council import run_evolution_council
        scheduler.add_job(
            run_evolution_council,
            CronTrigger(hour=23, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="evolution_council_nightly",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Auto-Tune weekly orchestrator — every Monday 04:00 Europe/Bucharest.
        # Self-healing: keeps platform in self-driving tier without manual action.
        scheduler.add_job(
            weekly_auto_tune_job,
            CronTrigger(day_of_week="mon", hour=4, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="autonomy_auto_tune_weekly",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Weekly Founders' Digest — Monday 09:30 (after Auto-Tune 04:00, after
        # AI Briefing 09:00). Sends a 1-email-per-week summary to super-admins.
        scheduler.add_job(
            weekly_founder_digest,
            CronTrigger(day_of_week="mon", hour=9, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="founder_digest_weekly",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Sprint A — Auto-promotion engine: daily 03:30 (after autonomy snapshot)
        scheduler.add_job(
            run_auto_promotion,
            CronTrigger(hour=3, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="specialist_auto_promotion_daily",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Auto-match cron tick — runs hourly, executes only when due
        # per `auto_match_schedule` config (enabled + interval_hours).
        scheduler.add_job(
            run_auto_match_cron_tick,
            CronTrigger(minute=23, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="auto_match_cron_tick",
            replace_existing=True,
            misfire_grace_time=600,
        )
        # Weekly AI Briefing email — Mondays 09:00 Europe/Bucharest
        scheduler.add_job(
            run_weekly_briefing_job,
            CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="weekly_ai_briefing",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Future Ideas Vault — weekly digest, Mondays 09:15 (after AI briefing)
        scheduler.add_job(
            run_future_ideas_digest_job,
            CronTrigger(day_of_week="mon", hour=9, minute=15, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="future_ideas_digest",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # AI Governance — Deprecation Pulse, Thursdays 09:30 Europe/Bucharest
        scheduler.add_job(
            run_deprecation_pulse_job,
            CronTrigger(day_of_week="thu", hour=9, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="deprecation_pulse_weekly",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Experience Tiers — daily auto-promotion, 03:30 Europe/Bucharest
        scheduler.add_job(
            run_experience_tier_promotion_job,
            CronTrigger(hour=3, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="experience_tier_daily_promotion",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Quests — daily evaluation + voucher issuance, 03:45 Europe/Bucharest
        scheduler.add_job(
            evaluate_quests_job,
            CronTrigger(hour=3, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="quests_daily_evaluation",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Tier milestones — daily sweep for missed 50/75/100% notifications, 04:00 Europe/Bucharest
        scheduler.add_job(
            cron_check_all_users,
            CronTrigger(hour=4, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="tier_milestone_daily_sweep",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Autonomy autopilot daily sweep — 04:15 Europe/Bucharest (after tier milestones)
        scheduler.add_job(
            daily_autopilot_sweep,
            CronTrigger(hour=4, minute=15, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="autonomy_autopilot_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        from routes.automation_center import run_due_rules
        scheduler.add_job(
            run_due_rules,
            CronTrigger(minute=12, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="automation_rules_tick",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        from routes.command_center import morning_command_center
        scheduler.add_job(
            morning_command_center,
            CronTrigger(hour=7, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="morning_command_center",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        from routes.audit_sentinel import run_sentinel_scan
        scheduler.add_job(
            run_sentinel_scan,
            CronTrigger(minute=40, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="audit_sentinel_hourly",
            replace_existing=True,
            misfire_grace_time=1800,
        )
        scheduler.add_job(
            auto_release_warranty_holds,
            CronTrigger(hour=6, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="warranty_auto_release",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        scheduler.add_job(
            run_due_preset_schedules,
            CronTrigger(minute="*", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="preset_schedules",
            replace_existing=True,
            misfire_grace_time=60,
        )
        scheduler.add_job(
            run_incident_spike_alert_check,
            CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="incident_spike_alert",
            replace_existing=True,
            misfire_grace_time=86400,
        )
        scheduler.add_job(
            run_daily_ai_digest,
            CronTrigger(hour=3, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="ai_daily_scan",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            send_daily_ai_digest_email,
            CronTrigger(hour=8, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="ai_daily_digest_email",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        scheduler.add_job(
            run_ai_effectiveness_alert_check,
            CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="ai_effectiveness_low_alert",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Google OAuth early-warning: check every 15 min, alert if success rate < 80% in last hour
        scheduler.add_job(
            run_auth_health_alert_check,
            CronTrigger(minute="*/15", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="auth_health_alert",
            replace_existing=True,
            misfire_grace_time=900,
        )
        scheduler.add_job(
            reset_demo_accounts,
            CronTrigger(hour=2, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="demo_accounts_reset",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # IT Sprint Health Digest — weekly AI-powered founder email (default Sun 18:00 Europe/Bucharest)
        try:
            _digest_settings = await _it_digest_get_settings()
            scheduler.add_job(
                run_weekly_it_sprint_digest,
                CronTrigger(
                    day_of_week=_digest_settings.get("day_of_week", "sun"),
                    hour=int(_digest_settings.get("hour", 18)),
                    minute=int(_digest_settings.get("minute", 0)),
                    timezone=pytz.timezone(BUCHAREST_TZ_NAME),
                ),
                id="it_sprint_digest_weekly",
                replace_existing=True,
                misfire_grace_time=7200,
            )
            logger.info(f"IT Sprint Digest scheduled: {_digest_settings.get('day_of_week','sun')} {_digest_settings.get('hour',18):02d}:{_digest_settings.get('minute',0):02d} Europe/Bucharest")
        except Exception as e:
            logger.warning(f"IT Sprint Digest schedule failed: {e}")
        scheduler.add_job(
            record_health_ping,
            CronTrigger(minute="*/15", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="health_ping",
            replace_existing=True,
            misfire_grace_time=900,
        )
        scheduler.add_job(
            run_dt_auto_reminders,
            CronTrigger(hour=8, minute=15, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="dt_auto_reminders",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Email lifecycle sequences: drip reminders + weekly newsletter (Phase 67)
        try:
            from email_sequences import register_email_sequence_jobs
            register_email_sequence_jobs(scheduler)
        except Exception as e:
            logger.warning(f"Failed to register email sequence jobs: {e}")
        # Smoke Test auto-monitor — runs every 30 min, alerts admins on failure
        scheduler.add_job(
            run_smoke_test_monitor_tick,
            CronTrigger(minute="*/30", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="smoke_test_monitor",
            replace_existing=True,
            misfire_grace_time=600,
        )
        # Autonomy Orchestrator — retry queue tick (Webhook Retry Guardian), every 5 min
        scheduler.add_job(
            orchestrator_retry_tick,
            CronTrigger(minute="*/5", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="orchestrator_retry_tick",
            replace_existing=True,
            misfire_grace_time=300,
        )
        # PM-AI-003: Self-Healing Watchdog — la 30 min repornește joburile cron moarte
        from orchestrator.governance import governance_watchdog_tick, decision_review_cron
        scheduler.add_job(
            governance_watchdog_tick,
            CronTrigger(minute="7,37", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="governance_watchdog",
            replace_existing=True,
            misfire_grace_time=900,
        )
        # PM-AI-003: Decision Review — zilnic 05:30, degradează autoritatea playbook-urilor cu eșecuri
        scheduler.add_job(
            decision_review_cron,
            CronTrigger(hour=5, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="decision_review_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # PM-AI-REPAIR-001: Health Repair Engine — zilnic 06:20 (detect → repair → validate)
        from health_repair import repair_cycle_cron
        scheduler.add_job(
            repair_cycle_cron,
            CronTrigger(hour=6, minute=20, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="health_repair_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Customer Journey Guardian — zilnic 06:50, audit călătoria clientului + task-uri CTO AI
        from journey_guardian import run_journey_guardian
        scheduler.add_job(
            run_journey_guardian,
            CronTrigger(hour=6, minute=50, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="journey_guardian_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Architecture Guardian — zilnic 06:40, impune arhitectura canonică + task-uri CTO AI
        from architecture_guardian import run_architecture_guardian
        scheduler.add_job(
            run_architecture_guardian,
            CronTrigger(hour=6, minute=40, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="architecture_guardian_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Product Guardian — zilnic 06:45, CTA/roluri/gates/funnel + task-uri CTO AI
        from product_guardian import run_product_guardian
        scheduler.add_job(
            run_product_guardian,
            CronTrigger(hour=6, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="product_guardian_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # AI Brain Discovery — zilnic 06:35, recartografiază structura aplicației
        from ai_brain.core import run_discovery as ai_brain_discovery
        scheduler.add_job(
            ai_brain_discovery,
            CronTrigger(hour=6, minute=35, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="ai_brain_discovery_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # CIP-A: Category Visibility Gate — daily 04:30 (via Orchestrator playbook)
        scheduler.add_job(
            construction_visibility_cron,
            CronTrigger(hour=4, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="construction_visibility_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Sprint 2: Marketplace Medic — daily 05:10 (via Orchestrator playbook)
        scheduler.add_job(
            marketplace_medic_cron,
            CronTrigger(hour=5, minute=10, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="marketplace_medic_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Sprint 3: Pattern Hunter — weekly Monday 06:00
        scheduler.add_job(
            pattern_hunter_cron,
            CronTrigger(day_of_week="mon", hour=6, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="pattern_hunter_weekly",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Sprint 3: Finance Reconciler — daily 04:50
        scheduler.add_job(
            finance_reconciler_cron,
            CronTrigger(hour=4, minute=50, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="finance_reconciler_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Sprint 3: Roadmap Advisor — weekly Friday 09:00
        scheduler.add_job(
            roadmap_advisor_cron,
            CronTrigger(day_of_week="fri", hour=9, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="roadmap_advisor_weekly",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Phase 1 (TD-08): retenție telemetrie — daily 03:40
        scheduler.add_job(
            telemetry_retention_tick,
            CronTrigger(hour=3, minute=40, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="telemetry_retention_daily",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Morning Briefing digest — daily 09:00, sent only when warn/fail
        scheduler.add_job(
            run_morning_briefing_job,
            CronTrigger(hour=9, minute=0, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="morning_briefing_digest",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        # Daily MongoDB backup — 03:30 (before AI scan at 03:00 doesn't matter; this is its own slot)
        scheduler.add_job(
            run_daily_backup_job,
            CronTrigger(hour=3, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="daily_mongodb_backup",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Weekly Dev Velocity — Mondays 09:30 Europe/Bucharest
        scheduler.add_job(
            run_weekly_velocity_job,
            CronTrigger(day_of_week="mon", hour=9, minute=30, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="weekly_dev_velocity",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Specialist onboarding email drip — every 15 minutes
        scheduler.add_job(
            run_onboarding_dispatch_job,
            CronTrigger(minute="*/15", timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="onboarding_email_dispatch",
            replace_existing=True,
            misfire_grace_time=900,
        )
        # Weekly Release Gate — Mondays 08:45 Europe/Bucharest
        # Silent unless any P0 fails (only then admins get alerted)
        scheduler.add_job(
            run_weekly_release_gate_job,
            CronTrigger(day_of_week="mon", hour=8, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="weekly_release_gate",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Weekly Executive Briefing — Mondays 09:45 Europe/Bucharest (after morning briefing + release gate)
        scheduler.add_job(
            run_exec_briefing_job,
            CronTrigger(day_of_week="mon", hour=9, minute=45, timezone=pytz.timezone(BUCHAREST_TZ_NAME)),
            id="weekly_exec_briefing",
            replace_existing=True,
            misfire_grace_time=7200,
        )
        # Sprint 2 (Board Review 001): Revenue Hunter — oportunități comerciale zilnice
        async def _revenue_hunter_tick():
            from revenue_hunter import run_revenue_hunter_tick
            await run_revenue_hunter_tick()
        scheduler.add_job(
            _revenue_hunter_tick,
            CronTrigger(hour=7, minute=10, timezone=pytz.timezone("Europe/Bucharest")),
            id="revenue_hunter_daily", replace_existing=True, misfire_grace_time=3600,
        )
        # Sprint GI-1 (Board 004/005/006): Growth Intelligence — scan zilnic pe date reale
        async def _growth_intel_tick():
            from growth_intelligence import run_growth_scan
            await run_growth_scan(trigger="cron")
        scheduler.add_job(
            _growth_intel_tick,
            CronTrigger(hour=6, minute=40, timezone=pytz.timezone("Europe/Bucharest")),
            id="growth_intelligence_daily", replace_existing=True, misfire_grace_time=3600,
        )
        # Sprint GI-2 (Board GI-2): Intent & Lead Intelligence — scoring zilnic înaintea Revenue Hunter
        async def _lead_intel_tick():
            from lead_intelligence import run_lead_scan
            await run_lead_scan(trigger="cron")
        scheduler.add_job(
            _lead_intel_tick,
            CronTrigger(hour=6, minute=50, timezone=pytz.timezone("Europe/Bucharest")),
            id="lead_intelligence_daily", replace_existing=True, misfire_grace_time=3600,
        )
        # Sprint GI-3 (Board 007): Marketing Intelligence+ — recomandări executive zilnice
        async def _marketing_intel_tick():
            from marketing_intelligence import run_marketing_scan
            await run_marketing_scan(trigger="cron")
        scheduler.add_job(
            _marketing_intel_tick,
            CronTrigger(hour=6, minute=55, timezone=pytz.timezone("Europe/Bucharest")),
            id="marketing_intelligence_daily", replace_existing=True, misfire_grace_time=3600,
        )
        # GI-4a: Learning Engine — outcome scan zilnic (după toate motoarele)
        async def _learning_tick():
            from learning_engine import run_outcome_scan
            await run_outcome_scan(trigger="cron")
        scheduler.add_job(
            _learning_tick,
            CronTrigger(hour=7, minute=20, timezone=pytz.timezone("Europe/Bucharest")),
            id="learning_outcomes_daily", replace_existing=True, misfire_grace_time=3600,
        )
        scheduler.start()
        # Felia 1 (Sprint 1): jurnalul central al agenților — toate execuțiile cron în agent_runs
        try:
            import asyncio as _asyncio
            from agent_journal import attach_journal
            attach_journal(scheduler, _asyncio.get_running_loop())
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Agent journal attach failed: {e}")
        # Record an immediate ping on startup so sparkline is non-empty from minute 1.
        try:
            await record_health_ping()
        except Exception:  # noqa: BLE001
            pass
        logger.info("Daily digest scheduler started (19:00 Europe/Bucharest).")
        logger.info("Warranty auto-release scheduler started (06:00 Europe/Bucharest).")
        logger.info("Preset schedules scheduler started (every minute, Europe/Bucharest).")
        logger.info("Incident spike alert scheduler started (Monday 08:00 Europe/Bucharest).")
        logger.info("AI daily auto-scan scheduler started (03:00 Europe/Bucharest).")
        logger.info("AI daily digest email scheduler started (08:00 Europe/Bucharest).")
        logger.info("AI effectiveness low-alert scheduler started (Monday 09:00 Europe/Bucharest).")
        logger.info("Demo accounts auto-reset scheduler started (daily 02:00 Europe/Bucharest).")
        logger.info("Health ping scheduler started (every 15 min, powers /status sparkline).")
        logger.info("Smoke Test auto-monitor scheduler started (every 30 min — alerts on FAIL).")
        logger.info("Morning Briefing digest scheduler started (daily 09:00 Europe/Bucharest).")
        logger.info("Daily MongoDB backup scheduler started (03:30 Europe/Bucharest, emails admin).")
        logger.info("Weekly Dev Velocity scheduler started (Mondays 09:30 Europe/Bucharest).")
        logger.info("Autonomy snapshot scheduler started (daily 03:15 Europe/Bucharest).")
        logger.info("Autonomy Auto-Tune scheduler started (Mondays 04:00 Europe/Bucharest, self-healing + adaptive escalation).")
        logger.info("Founders' Digest scheduler started (Mondays 09:30 Europe/Bucharest, 1 email/week to super-admins).")
        # Hydrate Twin scheduled actions from DB (re-register all active ones)
        try:
            from twin_schedule import hydrate_schedules_on_startup
            n = await hydrate_schedules_on_startup(scheduler)
            logger.info(f"Twin Scheduled Actions: hydrated {n} active schedules from DB.")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Twin schedule hydration failed: {e}")
        logger.info("Weekly AI Briefing scheduler started (Mondays 09:00 Europe/Bucharest).")
        logger.info("Future Ideas digest scheduler started (Mondays 09:15 Europe/Bucharest).")


@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    client.close()
