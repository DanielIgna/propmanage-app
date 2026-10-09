-- PropManage: MongoDB collections → JSONB tables (phase 1 of the Supabase migration).
-- Schema `app` is NOT exposed through the Data API; only the backend (direct Postgres
-- connection) reads/writes it. RLS is enabled with no policies as defense in depth.

create schema if not exists app;
revoke all on schema app from public, anon, authenticated;

-- One table per Mongo collection: `id` = Mongo _id (ObjectId hex or string), `data` = full document.
create or replace function app.create_collection(name text)
returns void
language plpgsql
set search_path = ''
as $$
begin
  if name !~ '^[a-z][a-z0-9_]*$' then
    raise exception 'invalid collection name: %', name;
  end if;
  execute format(
    'create table if not exists app.%I (
       id text primary key,
       data jsonb not null,
       created_at timestamptz not null default now(),
       updated_at timestamptz not null default now()
     )', name);
  execute format('alter table app.%I enable row level security', name);
  execute format('create index if not exists %I on app.%I using gin (data jsonb_path_ops)', name || '_data_gin', name);
end;
$$;

revoke execute on function app.create_collection(text) from public, anon, authenticated;

do $$
declare
  c text;
begin
  foreach c in array array[
    'ab_events', 'ab_experiments', 'activity_events', 'admin_actions_log', 'admin_ai_alert_config', 'admin_ai_alert_history',
    'admin_ai_findings', 'admin_ai_health_history', 'admin_ai_messages', 'admin_ai_repair_suggestions', 'admin_ai_scans', 'admin_ai_sessions',
    'admin_approvals', 'admin_audit_log', 'admin_snapshots', 'admin_todo_state', 'admin_todos', 'agent_runs',
    'ai_brain_certification', 'ai_brain_decision_feedback', 'ai_brain_decisions', 'ai_brain_explanations', 'ai_brain_graph_edges', 'ai_brain_graph_meta',
    'ai_brain_graph_nodes', 'ai_brain_mentor_seen', 'ai_brain_navigation', 'ai_brain_notifications', 'ai_brain_process_stats_history', 'ai_brain_processes',
    'ai_brain_registry', 'ai_brain_runs', 'ai_brain_sla_status', 'ai_decision_ledger', 'ai_doc_chunks', 'ai_documents',
    'ai_insights_cache', 'ai_match_notifications', 'ai_memories', 'ai_messages', 'ai_outcomes', 'ai_sessions',
    'ai_weekly_briefing_config', 'ai_weekly_briefing_history', 'analytics_events', 'analytics_sessions', 'analytics_settings', 'app_settings',
    'app_settings_snapshots', 'architecture_guardian_ignores', 'architecture_guardian_runs', 'architecture_guardian_tasks', 'audit_anomalies', 'audit_log',
    'auto_match_runs', 'auto_match_schedule', 'automation_emails', 'automation_executions', 'automation_rules', 'autonomy_alerts',
    'autonomy_decontamination_log', 'autonomy_loop_runs', 'autonomy_snapshots', 'autonomy_targets', 'autopilot_runs', 'backup_runs',
    'beta_feedback', 'beta_issues', 'boost_dev_runs', 'building_announcements', 'buildings', 'business_health_history',
    'capability_catalog', 'case_library', 'ceo_briefings', 'chat_messages', 'city_partner_leads', 'city_partner_nudges',
    'city_partner_products', 'city_partners', 'client_copilot_cache', 'client_junior_requests', 'cms_content', 'collaborator_contracts',
    'command_center_recos', 'community_campaigns', 'community_likes', 'community_replies', 'community_topics', 'concierge_conversations',
    'concierge_messages', 'concierge_settings', 'consent_audit_log', 'construction_taxonomy', 'contact_playbooks', 'content_articles',
    'copilot_reports', 'copilot_timeline', 'cs_findings', 'cs_money_flow', 'daily_wins', 'data_integrity_actions',
    'data_integrity_runs', 'demo_activity_logs', 'demo_leads', 'demo_reset_log', 'deprecation_pulse_config', 'deprecation_pulse_history',
    'design_audit_cache', 'design_lock', 'design_presets', 'design_proposals', 'design_tokens', 'dev_velocity_runs',
    'digital_twin_comments', 'digital_twin_design_concepts', 'digital_twin_models', 'digital_twin_pins', 'digital_twin_plans', 'digital_twin_projects',
    'digital_twin_qa_sessions', 'digital_twin_validations', 'disputes', 'doc_conflicts', 'doc_overrides', 'docs_send_events',
    'docs_share_tokens', 'dsar_requests', 'eh_formula_audit', 'eh_formulas', 'email_log', 'email_templates',
    'engagement_state', 'enterprise_health_history', 'entity_links', 'events', 'evolution_council_reports', 'exec_briefings',
    'experience_profiles', 'experience_tier_config', 'experience_tier_history', 'fairprice_signals', 'feature_config', 'feature_pairs',
    'fee_configs', 'fee_configs_history', 'financial_insights', 'founder_digest_log', 'franchise_applications', 'future_ideas_digest_config',
    'future_ideas_digest_history', 'future_ideas_status', 'gdpr_audit', 'gdpr_breach_drills', 'geo_ip_cache', 'growth_campaigns',
    'growth_insights', 'growth_insights_history', 'health_history', 'health_pings', 'health_repair_runs', 'hh_audit_log',
    'hh_documents', 'hh_evaluations', 'hh_plans', 'hh_recommendations', 'hh_scores', 'hh_scoring_config',
    'hh_subscriptions', 'impersonation_logs', 'import_batches', 'incident_recipient_presets', 'incidents', 'integration_health',
    'interior_assistant_sessions', 'interior_design_content', 'interior_design_leads', 'it_collaborators', 'it_copilot_reports', 'journey_guardian_runs',
    'journey_guardian_tasks', 'kg_entity_registry', 'kyc_documents', 'landing_presets', 'lead_followup_log', 'lead_followup_runs',
    'lead_magnet_leads', 'lead_scores', 'lead_scores_meta', 'leads', 'legal_documents', 'maintenance_logs',
    'maintenance_tasks', 'manual_payments', 'manual_test_runs', 'marketing_attributions', 'marketing_campaigns', 'marketing_chat_sessions',
    'marketing_conversions', 'marketing_insights', 'marketing_insights_history', 'marketing_performance_learnings', 'marketing_performance_logs', 'marketing_recommendations',
    'marketplace_copilot_reports', 'marketplace_intel_recos', 'marketplace_leads', 'marketplace_offers', 'marketplace_partners', 'marketplace_presentations',
    'menu_clicks', 'migration_backups', 'nonconformities', 'notification_center_acks', 'notifications', 'oauth_health',
    'onboarding_emails', 'orchestrator_config', 'orchestrator_decisions', 'orchestrator_escalation_dedup', 'orchestrator_ledger', 'orchestrator_retry_queue',
    'orchestrator_reviews', 'orchestrator_signals', 'pages', 'pages_versions', 'partner_leads', 'passport_events',
    'pattern_findings', 'payment_transactions', 'payments', 'pb_advisor_reports', 'pb_campaigns', 'pb_community_deals',
    'pb_config', 'pb_deal_signals', 'pb_ledger', 'pb_referral_pending', 'pb_subscription_health', 'pb_trust_scores',
    'platform_config', 'platform_roadmap', 'platform_roadmap_analysis', 'platform_settings', 'playbook_executions', 'policy_documents',
    'portfolio', 'preset_schedule_runs', 'preset_schedules', 'preset_send_history', 'price_observations', 'product_guardian_ignores',
    'product_guardian_runs', 'product_guardian_tasks', 'product_map_snapshots', 'project_lifecycle_actions', 'project_tasks', 'projects',
    'properties', 'property_assets', 'property_diagnostics', 'property_documents', 'property_maturity_history', 'push_subscriptions',
    'pvi_history', 'qa_runs', 'qa_sessions', 'quests', 'recommendations', 'referral_invites',
    'regions', 'release_gates', 'renewal_reminders', 'requests', 'revenue_hunter_scans', 'revenue_opportunities',
    'reviews', 'roadmap_advice', 'scheduler_runs', 'security_ai_runs', 'security_config', 'security_events',
    'security_rate_buckets', 'self_driving_settings', 'seo_config', 'seo_events', 'service_availability', 'service_contracts',
    'service_leads', 'service_pages', 'settings', 'site_content', 'site_menu', 'smoke_test_config',
    'smoke_test_runs', 'specialist_entry_applications', 'specialist_followup_log', 'specialist_gaps', 'storage_configs', 'storage_meta',
    'storage_migrations', 'storage_usage', 'strategic_cross_refs', 'stripe_customers', 'stripe_subscriptions', 'support_messages',
    'system_alerts', 'task_comments', 'tenant_migrations', 'tenants', 'term_clusters', 'term_inconsistencies',
    'tier_promotion_runs', 'tier_rules', 'transactions', 'twin_action_tokens', 'twin_actions_log', 'twin_conversations',
    'twin_scheduled_actions', 'twins', 'twins_orphan_archive', 'ui_rules', 'user_quest_progress', 'user_vouchers',
    'users', 'ux_lab_events', 'verified_estate_external_requests', 'verified_estate_inquiries', 'verified_estate_listings', 'verified_estate_orders',
    'verified_estate_sales', 'visitor_identities', 'vouchers', 'wallet', 'wallets', 'war_room_meta',
    'warranties', 'xos_layout_history', 'xos_layouts', 'xos_widget_registry', 'zones_custom', 'zones_disabled'
  ] loop
    perform app.create_collection(c);
  end loop;
end;
$$;
