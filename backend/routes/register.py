"""Central router registry — all API routers in registration order.

server.py imports ALL_ROUTERS from here and includes them in order.
When adding a new route module, append its router(s) HERE (not in server.py)
and remember to classify the module in an admin zone (see
frontend/src/config/adminZones.js — business vs infrastructure).
"""
from routes.auth import router as auth_router
from routes.properties import router as properties_router
from routes.requests import router as requests_router
from routes.operator import router as operator_nonconformity_router
from routes.operator_twins import router as operator_twins_router
from routes.wallet import router as wallet_router
from routes.admin import router as admin_router
from routes.specialist_docs import router as specialist_docs_router
from routes.disputes import router as disputes_router
from routes.design import router as design_router
from routes.portfolio import router as portfolio_router
from routes.payments import router as payments_router
from routes.chat import router as chat_router
from routes.specialist_profile import router as specialist_profile_router
from routes.notifications import router as notifications_router
from routes.ai import router as ai_router
from routes.marketplace import router as marketplace_router
from routes.property_timeline import router as property_timeline_router
from routes.regions import router as regions_router
from routes.matching import router as matching_router
from routes.services_avail import router as services_avail_router
from routes.projects import router as projects_router
from routes.trust import router as trust_router
from routes.root import router as root_router
from routes.admin_console import router as admin_console_router, public_router as cms_public_router
from routes.admin_ai import router as admin_ai_router
from routes.security_guard import router as security_guard_router
from routes.concierge import router as concierge_router, admin_router as concierge_admin_router
from routes.public import router as public_router, admin_router as public_admin_router
from routes.admin_seo import router as admin_seo_router
from routes.demo_time_machine import router as demo_time_machine_router
from routes.gdpr import router as gdpr_router, admin_router as gdpr_admin_router
from routes.digital_twin import router as digital_twin_router, admin_router as digital_twin_admin_router, operator_router as digital_twin_operator_router
from routes.impersonation import router as impersonation_router
from routes.admin_smoketest import router as admin_smoketest_router
from routes.admin_healthcheck import router as admin_healthcheck_router, briefing_router as admin_morning_briefing_router
from routes.admin_data_integrity import router as admin_data_integrity_router
from routes.admin_backups import router as admin_backups_router
from routes.public_trust import router as public_trust_router
from routes.admin_exec_briefing import router as admin_exec_briefing_router
from routes.admin_qa_maintenance import router as admin_qa_maintenance_router
from routes.admin_dev_velocity import router as admin_dev_velocity_router
from routes.docs_routes import admin_router as admin_docs_router, public_router as public_help_router
from routes.incidents import admin_router as incidents_admin_router, public_router as incidents_public_router
from routes.admin_onboarding import router as admin_onboarding_router
from routes.admin_qa_playbook import router as admin_qa_playbook_router
from routes.admin_content_audit import router as admin_content_audit_router
from routes.admin_term_audit import router as admin_term_audit_router
from routes.verified_estate import router as verified_estate_router
from routes.app_settings import router as app_settings_router, public_router as app_settings_public_router
from routes.qa_copilot import router as qa_copilot_router
from routes.ai_control import router as ai_control_router
from routes.digital_twin_qa import router as dt_qa_router
from routes.docs_ai import router as docs_ai_router
from routes.ai_dev_team import router as ai_dev_team_router
from routes.ai_security import router as ai_security_router
from routes.settings_snapshots import router as settings_snapshots_router
from routes.service_contracts import router as service_contracts_router
from routes.autonomy import router as autonomy_router
from routes.twin import router as twin_router
from routes.house_health import router as house_health_router, admin_router as house_health_admin_router
from routes.house_health_plans import public_router as hh_plans_public_router, admin_router as hh_plans_admin_router
from routes.house_health_recommendations import router as hh_recommendations_router
from routes.house_health_billing import router as hh_billing_router
from routes.manual_tester import router as manual_tester_router
from routes.adaptive_ux import router as adaptive_ux_router, admin_router as adaptive_ux_admin_router
from routes.admin_tour import router as admin_tour_router
from routes.ai_activity import router as ai_activity_router
from routes.ai_weekly_briefing import router as ai_weekly_briefing_router
from routes.admin_todos import router as admin_todos_router
from routes.experience_spaces_bootstrap import router as es_bootstrap_router
from routes.future_ideas import router as future_ideas_router
from routes.future_ideas_digest import router as future_ideas_digest_router
from routes.founder_gate_admin import router as founder_gate_admin_router
from routes.ai_governance import router as ai_governance_router
from routes.bug_memory_aggregator import router as bug_memory_router
from routes.deprecation_pulse import router as deprecation_pulse_router
from routes.architecture_board import router as architecture_board_router
from routes.ai_pm import router as ai_pm_router
from routes.operating_manual import router as operating_manual_router
from routes.knowledge_center import router as knowledge_center_router
from routes.experience_tiers import router as experience_tiers_router, self_router as experience_tiers_self_router
from routes.feature_configurator import router as feature_configurator_router, self_router as feature_configurator_self_router
from routes.specialist_progression import router_admin as sp_admin_router, router_public as sp_public_router
from routes.reviews_v2 import router as reviews_v2_router
from routes.marketplace_offers import router as marketplace_offers_router
from routes.premium_marketplace import router as premium_marketplace_router
from routes.bi_moe import router as bi_moe_router
from routes.community import router as community_router
from routes.tier_milestones import router as tier_milestones_router
from routes.sub_admins import router as sub_admins_router
from routes.admin_approvals import router as admin_approvals_router
from routes.kyc import router as kyc_router
from routes.it_collaborators import router as it_collaborators_router
from routes.it_digest import router as it_digest_router
from routes.legal import router as legal_router, admin_router as legal_admin_router
from routes.city_partners import admin_router as city_partners_admin_router, partner_router as city_partners_portal_router, products_admin_router as city_partner_products_router
from routes.marketplace_partners import admin_router as marketplace_admin_router, partner_router as marketplace_portal_router
from routes.strategic_partners import router as strategic_partners_router
from routes.marketing_growth import router as marketing_growth_router
from routes.marketing_campaigns import router as marketing_campaigns_router
from routes.marketing_performance import router as marketing_performance_router
from routes.demo_accounts import router as demo_accounts_router
from routes.admin_accounts import router as admin_accounts_router
from routes.admin_zones import router as admin_zones_router
from routes.analytics_growth import router as analytics_track_router, admin_router as analytics_admin_router
from routes.demo_activity import router as demo_activity_router
from routes.orchestrator import router as orchestrator_router
from routes.repair_center import router as repair_center_router
from routes.ai_brain import router as ai_brain_router, user_router as ai_brain_user_router
from routes.construction import router as construction_router
from routes.kg import router as kg_router
from routes.control_tower import router as control_tower_router
from routes.specialist_cockpit import router as specialist_cockpit_router
from routes.ai_insights import router as ai_insights_router
from routes.client_copilot import router as client_copilot_router
from routes.design_audit import router as design_audit_router
from routes.design_studio import router as design_studio_router
from routes.design_intelligence import router as design_intelligence_router
from routes.platform_roadmap import router as platform_roadmap_router
from routes.command_center import router as command_center_router
from routes.business_health import router as business_health_router
from routes.marketplace_intel import router as marketplace_intel_router
from routes.financial_cockpit import router as financial_cockpit_router
from routes.automation_center import router as automation_center_router
from routes.ceo_dashboard import router as ceo_dashboard_router
from routes.notification_center import router as notification_center_router
from routes.audit_sentinel import router as audit_sentinel_router
from routes.user_timeline import router as user_timeline_router
from routes.ai_search import router as ai_search_router
from routes.interior_design import router as interior_design_router
from routes.site_menu import router as site_menu_router
from routes.xos import router as xos_router
from routes.ux_lab import router as ux_lab_router
from autonomy.self_driving import router as self_driving_router
from routes.leads import router as leads_router
from routes.tenants import router as tenants_router, public_router as tenants_public_router
from routes.service_hub import router as service_hub_router
from routes.lead_followup import router as lead_followup_router
from routes.specialist_followup import router as specialist_followup_router
from routes.property_dna import router as property_dna_router
from routes.property_documents import router as property_documents_router
from routes.property_passport import router as property_passport_router, public_router as passport_public_router
from routes.property_technical_record import router as property_technical_record_router
from routes.entitlements_api import router as entitlements_api_router
from routes.passport_analytics import router as passport_analytics_router
from routes.beta_cockpit import router as beta_cockpit_router
from routes.beta_issues import router as beta_issues_router
from routes.pages_registry import router as pages_registry_router, public_router as pages_registry_public_router
from routes.config_io import router as config_io_router
from routes.renewal_reminders import router as renewal_reminders_router
from routes.trust_growth import router as trust_growth_router
from routes.trusted_specialists import router as trusted_specialists_router
from routes.maintenance_calendar import router as maintenance_calendar_router
from routes.community_buildings import router as community_buildings_router
from routes.building_admin import router as building_admin_router
from routes.hartablocuri import router as hartablocuri_router, public_router as hartablocuri_public_router
from routes.launch_sentinel import router as launch_sentinel_router
from routes.prop_benefits import user_router as prop_benefits_user_router, admin_router as prop_benefits_admin_router
from routes.storage import user_router as storage_user_router, admin_router as storage_admin_router
from routes.copilot import router as copilot_router
from routes.journey import router as journey_router, fairprice_router as journey_fairprice_router
from routes.engagement import router as engagement_router
from routes.capability_engine import router as capability_engine_router
from routes.property_intelligence import router as property_intelligence_router
from routes.resend_diagnostics import router as resend_diagnostics_router
from routes.first_revenue import router as first_revenue_router
from routes.lead_magnets import router as lead_magnets_router
from routes.operations_center import router as operations_center_router
from routes.enterprise_health import router as enterprise_health_router
from routes.ceo_briefing import router as ceo_briefing_router
from routes.evolution_council import router as evolution_council_router
from routes.opportunities import router as opportunities_router
from routes.growth_intelligence import router as growth_intelligence_router
from routes.lead_intelligence import router as lead_intelligence_router
from routes.marketing_intelligence import router as marketing_intelligence_router
from routes.learning import router as learning_router

# Registration order matters — kept identical to the original server.py loop.
ALL_ROUTERS = (
    auth_router, properties_router, requests_router,
    operator_nonconformity_router, operator_twins_router,
    wallet_router, admin_router, specialist_docs_router,
    disputes_router, design_router, portfolio_router,
    payments_router, chat_router, specialist_profile_router,
    notifications_router, ai_router, marketplace_router,
    property_timeline_router, regions_router, matching_router,
    services_avail_router, projects_router, trust_router, root_router,
    admin_console_router, cms_public_router, admin_ai_router,
    security_guard_router, concierge_router, concierge_admin_router,
    public_router,
    public_admin_router,
    admin_seo_router,
    demo_time_machine_router,
    gdpr_router, gdpr_admin_router,
    digital_twin_router, digital_twin_admin_router, digital_twin_operator_router,
    impersonation_router,
    admin_smoketest_router,
    admin_healthcheck_router,
    admin_morning_briefing_router,
    admin_data_integrity_router,
    admin_backups_router,
    public_trust_router,
    admin_exec_briefing_router,
    admin_qa_maintenance_router,
    admin_dev_velocity_router,
    admin_docs_router,
    public_help_router,
    incidents_admin_router,
    incidents_public_router,
    admin_onboarding_router,
    admin_qa_playbook_router,
    admin_content_audit_router,
    admin_term_audit_router,
    verified_estate_router,
    app_settings_router,
    app_settings_public_router,
    qa_copilot_router,
    ai_control_router,
    dt_qa_router,
    docs_ai_router,
    ai_dev_team_router,
    ai_security_router,
    settings_snapshots_router,
    service_contracts_router,
    autonomy_router,
    twin_router,
    house_health_router,
    house_health_admin_router,
    hh_plans_public_router,
    hh_plans_admin_router,
    hh_recommendations_router,
    hh_billing_router,
    manual_tester_router,
    adaptive_ux_router,
    adaptive_ux_admin_router,
    admin_tour_router,
    ai_activity_router,
    ai_weekly_briefing_router,
    admin_todos_router,
    es_bootstrap_router,
    future_ideas_router,
    future_ideas_digest_router,
    founder_gate_admin_router,
    ai_governance_router,
    bug_memory_router,
    orchestrator_router,
    repair_center_router,
    ai_brain_router,
    ai_brain_user_router,
    construction_router,
    deprecation_pulse_router,
    architecture_board_router,
    ai_pm_router,
    operating_manual_router,
    knowledge_center_router,
    experience_tiers_router,
    experience_tiers_self_router,
    feature_configurator_router,
    feature_configurator_self_router,
    sp_admin_router,
    sp_public_router,
    reviews_v2_router,
    marketplace_offers_router,
    premium_marketplace_router,
    bi_moe_router,
    community_router,
    tier_milestones_router,
    sub_admins_router,
    admin_approvals_router,
    kyc_router,
    it_collaborators_router,
    it_digest_router,
    legal_router,
    legal_admin_router,
    city_partners_admin_router,
    city_partners_portal_router,
    city_partner_products_router,
    marketplace_admin_router,
    marketplace_portal_router,
    strategic_partners_router,
    marketing_growth_router,
    marketing_campaigns_router,
    marketing_performance_router,
    demo_accounts_router,
    admin_accounts_router,
    admin_zones_router,
    analytics_track_router,
    analytics_admin_router,
    demo_activity_router,
    kg_router,
    control_tower_router,
    specialist_cockpit_router,
    ai_insights_router,
    client_copilot_router,
    design_audit_router,
    design_studio_router,
    design_intelligence_router,
    platform_roadmap_router,
    command_center_router,
    business_health_router,
    marketplace_intel_router,
    financial_cockpit_router,
    automation_center_router,
    ceo_dashboard_router,
    notification_center_router,
    audit_sentinel_router,
    user_timeline_router,
    ai_search_router,
    interior_design_router,
    site_menu_router,
    xos_router,
    self_driving_router,
    leads_router,
    tenants_router,
    tenants_public_router,
    service_hub_router,
    lead_followup_router,
    specialist_followup_router,
    property_dna_router,
    property_documents_router,
    property_passport_router,
    passport_public_router,
    property_technical_record_router,
    entitlements_api_router,
    passport_analytics_router,
    beta_cockpit_router,
    beta_issues_router,
    pages_registry_router,
    pages_registry_public_router,
    config_io_router,
    renewal_reminders_router,
    trust_growth_router,
    trusted_specialists_router,
    maintenance_calendar_router,
    community_buildings_router,
    building_admin_router,
    hartablocuri_router,
    hartablocuri_public_router,
    launch_sentinel_router,
    prop_benefits_user_router,
    prop_benefits_admin_router,
    storage_user_router,
    storage_admin_router,
    copilot_router,
    journey_router,
    journey_fairprice_router,
    engagement_router,
    capability_engine_router,
    opportunities_router,
    growth_intelligence_router,
    lead_intelligence_router,
    marketing_intelligence_router,
    learning_router,
    property_intelligence_router,
    resend_diagnostics_router,
    first_revenue_router,
    lead_magnets_router,
    operations_center_router,
    enterprise_health_router,
    ceo_briefing_router,
    evolution_council_router,
    ux_lab_router,
)
