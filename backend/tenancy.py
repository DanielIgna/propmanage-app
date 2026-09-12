"""tenancy — fundația multi-tenant (Sprint 3 · Tenant Foundation).

Registru `tenants` (slug unic) + rezolvare tenant per request + clasificarea
colecțiilor pe tiere. FĂRĂ migrare de date în acest sprint: doar infrastructură.
Rezolvare tenant: header X-Tenant-ID (validat în registru) → user.tenant_id → "main".
"""
import logging
import re
from datetime import datetime, timezone

from fastapi import Request

from db import db

logger = logging.getLogger("propmanage.tenancy")

DEFAULT_TENANT = "main"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")

# ── Clasificarea colecțiilor (guvernanță migrare) ────────────────────────────
# T1 — date de business per francizat: PRIMESC tenant_id (valurile 1-3)
TIER1_TENANT_SCOPED = {
    # identitate & core business
    "users", "properties", "requests", "transactions", "payment_transactions",
    "payments", "reviews", "disputes", "notifications", "chat_messages",
    "support_messages", "projects", "project_tasks", "task_comments",
    "portfolio", "service_contracts", "collaborator_contracts", "nonconformities",
    "kyc_documents", "dsar_requests", "it_collaborators",
    # leads & parteneri (unified `leads` DEJA are tenant_id)
    "leads", "demo_leads", "city_partner_leads", "city_partners",
    "city_partner_nudges", "marketplace_leads", "marketplace_partners",
    "marketplace_presentations", "interior_design_leads", "service_leads",
    # AI & conversații (unified `ai_sessions` DEJA are tenant_id)
    "ai_sessions", "concierge_messages", "marketing_chat_sessions",
    "interior_assistant_sessions", "twin_conversations", "ai_messages",
    # digital twin & house health
    "twins", "twin_actions_log", "twin_scheduled_actions", "twin_action_tokens",
    "digital_twin_models", "digital_twin_pins", "digital_twin_plans",
    "digital_twin_projects", "digital_twin_comments",
    "hh_documents", "hh_evaluations", "hh_plans", "hh_recommendations",
    "hh_scores", "hh_subscriptions",
    # community & gamification & vouchere
    "community_topics", "community_replies", "community_likes",
    "quests", "user_quest_progress", "vouchers", "user_vouchers",
    "experience_tier_history",
    # verified estate
    "verified_estate_listings", "verified_estate_orders",
    "verified_estate_inquiries", "verified_estate_external_requests",
    # comunicare & tracking per tenant
    "email_log", "onboarding_emails", "automation_emails", "push_subscriptions",
    "lead_followup_log",
    "docs_share_tokens", "docs_send_events", "activity_events",
    "analytics_events", "analytics_sessions", "ab_events", "consent_audit_log",
    "legal_documents", "menu_clicks",
}

# T2 — configurare platformă: default global "main" + override per-tenant
TIER2_PLATFORM_CONFIG = {
    "settings", "app_settings", "security_config", "platform_config",
    "platform_settings", "site_menu", "site_content", "service_pages",
    "cms_content", "landing_presets", "design_tokens", "design_presets",
    "email_templates", "feature_config", "fee_configs", "fee_configs_history",
    "xos_widget_registry", "xos_layouts", "xos_layout_history", "experience_profiles", "ui_rules",
    "construction_taxonomy", "regions", "zones_custom", "zones_disabled",
    "concierge_settings", "automation_rules", "hh_scoring_config",
    "analytics_settings", "self_driving_settings", "interior_design_content",
    "policy_documents",
}

# T3 — sistem/ops HQ: rămân GLOBALE, nu primesc tenant_id
TIER3_SYSTEM_OPS_PREFIXES = (
    "admin_", "qa_", "smoke_test_", "autonomy_", "orchestrator_", "security_",
    "deprecation_", "future_ideas", "term_", "doc_", "design_audit",
    "platform_roadmap", "marketing_", "ai_doc", "ai_weekly", "ai_insights",
    "ai_agent", "ai_memories", "ai_match", "ai_pm",
)
TIER3_SYSTEM_OPS = {
    "audit_log", "hh_audit_log", "gdpr_audit", "impersonation_logs",
    "health_pings", "oauth_health", "backup_runs", "migration_backups",
    "manual_test_runs", "demo_reset_log", "demo_activity_logs",
    "scheduler_runs", "release_gates", "incidents", "incident_recipient_presets",
    "system_alerts", "architecture_reviews", "entity_links", "data_integrity_runs",
    "playbook_executions", "command_center_recos", "business_health_history",
    "financial_insights", "roadmap_advice", "growth_campaigns", "founder_digest_log",
    "price_observations", "feature_pairs", "strategic_cross_refs", "tenants",
    "auto_match_runs", "auto_match_schedule", "autopilot_runs", "boost_dev_runs",
    "dev_velocity_runs", "tier_promotion_runs", "notification_center_acks",
    "design_lock", "design_proposals", "app_settings_snapshots", "tenant_migrations",
    "preset_schedules", "preset_schedule_runs", "preset_send_history",
    "client_copilot_cache", "it_copilot_reports", "marketplace_copilot_reports",
    "marketplace_intel_recos", "ai_documents", "ab_experiments",
    "audit_anomalies", "automation_executions", "kg_entity_registry",
}


def classify_collection(name: str) -> str:
    if name in TIER1_TENANT_SCOPED:
        return "T1"
    if name in TIER2_PLATFORM_CONFIG:
        return "T2"
    if name in TIER3_SYSTEM_OPS or name.startswith(TIER3_SYSTEM_OPS_PREFIXES):
        return "T3"
    return "UNCLASSIFIED"


# ── Registru tenants ─────────────────────────────────────────────────────────
async def ensure_main_tenant() -> None:
    """Seed idempotent: tenantul HQ 'main' există mereu."""
    now = datetime.now(timezone.utc).isoformat()
    await db.tenants.update_one(
        {"slug": DEFAULT_TENANT},
        {"$setOnInsert": {
            "slug": DEFAULT_TENANT, "name": "PropManage HQ", "plan": "hq",
            "status": "active", "domain": "propmanage.ro", "regions": [],
            "branding": {}, "created_at": now, "updated_at": now,
        }},
        upsert=True,
    )
    await db.tenants.create_index("slug", unique=True)


async def backfill_user_tenants() -> int:
    """Val 1, idempotent: orice user fără tenant_id primește 'main' (rulează la startup)."""
    r = await db.users.update_many(
        {"tenant_id": {"$exists": False}},
        {"$set": {"tenant_id": DEFAULT_TENANT}},
    )
    if r.modified_count:
        logger.info(f"[tenancy] backfill users tenant_id=main: {r.modified_count}")
    return r.modified_count


async def backfill_tier1_tenant_data(force: bool = False) -> dict:
    """Val 2, idempotent cu marker: toate colecțiile T1 primesc tenant_id='main' + index."""
    marker = await db.tenant_migrations.find_one({"wave": 2})
    if marker and not force:
        return {"skipped": True, "done_at": marker.get("done_at")}
    now = datetime.now(timezone.utc).isoformat()
    results, total = {}, 0
    for col in sorted(TIER1_TENANT_SCOPED):
        try:
            r = await db[col].update_many({"tenant_id": {"$exists": False}}, {"$set": {"tenant_id": DEFAULT_TENANT}})
            await db[col].create_index("tenant_id")
            if r.modified_count:
                results[col] = r.modified_count
                total += r.modified_count
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[tenancy] backfill {col} fail: {e}")
    await db.tenant_migrations.update_one(
        {"wave": 2},
        {"$set": {"wave": 2, "done_at": now, "backfilled_docs": total, "results": results}},
        upsert=True,
    )
    logger.info(f"[tenancy] Val 2 backfill: {total} docs în {len(results)} colecții")
    return {"skipped": False, "backfilled_docs": total, "collections": results}


async def get_tenant(slug: str) -> dict | None:
    return await db.tenants.find_one({"slug": slug}, {"_id": 0})


async def resolve_tenant_slug(request: Request, user: dict = None) -> str:
    """Ordinea: header X-Tenant-ID (doar tenant activ din registru) → user.tenant_id → main."""
    header = (request.headers.get("X-Tenant-ID") or "").strip().lower()
    if header and header != DEFAULT_TENANT and SLUG_RE.match(header):
        t = await db.tenants.find_one({"slug": header, "status": "active"})
        if t:
            return header
        logger.warning(f"[tenancy] X-Tenant-ID necunoscut/inactiv: {header} → fallback main")
    if user and user.get("tenant_id"):
        return user["tenant_id"]
    return DEFAULT_TENANT


async def get_tenant_id(request: Request) -> str:
    """FastAPI dependency — tenant curent pentru rute (val 2: injectat în store-uri)."""
    user = getattr(request.state, "user", None)
    return await resolve_tenant_slug(request, user)


def tenant_scope_for(user: dict) -> str | None:
    """Val 3: None = acces global (HQ admin); altfel tenantul userului (franchise_admin etc.)."""
    if (user or {}).get("role") == "admin":
        return None
    return (user or {}).get("tenant_id") or DEFAULT_TENANT


# ── Raport de acoperire (guvernanță) ─────────────────────────────────────────
async def coverage_report() -> dict:
    """Analiză live: acoperirea tenant_id pe colecțiile T1/T2 + colecții neclasificate."""
    names = await db.list_collection_names()
    tiers = {"T1": [], "T2": [], "T3": [], "UNCLASSIFIED": []}
    total_t1_docs = migrated_t1_docs = 0
    for name in sorted(names):
        tier = classify_collection(name)
        entry = {"collection": name}
        if tier in ("T1", "T2"):
            n = await db[name].count_documents({})
            t = await db[name].count_documents({"tenant_id": {"$exists": True}})
            entry.update({"docs": n, "with_tenant_id": t,
                          "coverage": "full" if n and t == n else ("partial" if t else "none")})
            if tier == "T1":
                total_t1_docs += n
                migrated_t1_docs += t
        tiers[tier].append(entry)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "collections": len(names),
            "t1_tenant_scoped": len(tiers["T1"]),
            "t2_platform_config": len(tiers["T2"]),
            "t3_system_ops": len(tiers["T3"]),
            "unclassified": len(tiers["UNCLASSIFIED"]),
            "t1_docs": total_t1_docs,
            "t1_docs_with_tenant_id": migrated_t1_docs,
        },
        "tiers": tiers,
    }
