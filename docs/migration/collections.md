# Inventar colecții Mongo → Supabase

Sursa: dump BSON producție 2026-10-09 (260 colecții, 130.375 documente). `refs` = apariții `db.<colecție>` în backend (fără teste).

Strategie: **core** → tabele normalizate; restul → tabele JSONB (`id`, `legacy_id`, `data jsonb`, `created_at`). Toate cu RLS fără politici publice (doar backend-ul accesează).

| categorie | colecții | documente |
|---|---|---|
| core | 72 | 16608 |
| config/altele | 62 | 4093 |
| intern | 85 | 35198 |
| log | 41 | 74476 |

Colecții folosite în cod dar absente în producție (create la nevoie, tabele JSONB): 86

## core

| colecție | documente | refs |
|---|---|---|
| `users` | 97 | 557 |
| `requests` | 105 | 328 |
| `properties` | 47 | 144 |
| `buildings` | 3408 | 71 |
| `digital_twin_models` | 8 | 54 |
| `disputes` | 4 | 54 |
| `digital_twin_projects` | 1 | 52 |
| `twins` | 9 | 47 |
| `projects` | 1 | 43 |
| `property_documents` | 13 | 41 |
| `transactions` | 121 | 39 |
| `verified_estate_listings` | 5 | 39 |
| `digital_twin_pins` | 0 | 35 |
| `leads` | 9 | 32 |
| `pages` | 20 | 32 |
| `reviews` | 5 | 32 |
| `payment_transactions` | 14 | 29 |
| `verified_estate_orders` | 3 | 29 |
| `hh_subscriptions` | 0 | 27 |
| `marketplace_partners` | 0 | 27 |
| `city_partners` | 1 | 24 |
| `concierge_messages` | 60 | 23 |
| `hh_evaluations` | 0 | 23 |
| `digital_twin_plans` | 0 | 22 |
| `city_partner_leads` | 0 | 21 |
| `notifications` | 10092 | 20 |
| `cms_content` | 9 | 19 |
| `pb_ledger` | 2 | 19 |
| `project_tasks` | 1 | 18 |
| `construction_taxonomy` | 203 | 17 |
| `hh_plans` | 3 | 17 |
| `kyc_documents` | 0 | 17 |
| `property_diagnostics` | 1 | 17 |
| `community_topics` | 343 | 16 |
| `maintenance_tasks` | 4 | 16 |
| `marketplace_leads` | 0 | 16 |
| `pb_campaigns` | 4 | 15 |
| `portfolio` | 4 | 15 |
| `site_menu` | 1 | 15 |
| `pb_community_deals` | 12 | 14 |
| `hh_documents` | 0 | 13 |
| `tenants` | 1 | 13 |
| `legal_documents` | 8 | 12 |
| `property_assets` | 4 | 12 |
| `service_contracts` | 0 | 12 |
| `dsar_requests` | 1 | 10 |
| `regions` | 174 | 10 |
| `hh_recommendations` | 0 | 9 |
| `warranties` | 3 | 9 |
| `digital_twin_comments` | 0 | 8 |
| `renewal_reminders` | 0 | 8 |
| `pages_versions` | 2 | 7 |
| `collaborator_contracts` | 0 | 6 |
| `referral_invites` | 1 | 6 |
| `user_vouchers` | 3 | 6 |
| `verified_estate_external_requests` | 0 | 6 |
| `verified_estate_inquiries` | 1 | 6 |
| `community_likes` | 0 | 5 |
| `community_replies` | 0 | 5 |
| `support_messages` | 0 | 5 |
| `gdpr_audit` | 1 | 4 |
| `push_subscriptions` | 7 | 4 |
| `specialist_entry_applications` | 4 | 4 |
| `verified_estate_sales` | 1 | 4 |
| `zones_custom` | 1 | 4 |
| `zones_disabled` | 0 | 4 |
| `chat_messages` | 6 | 2 |
| `hh_scores` | 0 | 2 |
| `task_comments` | 1 | 2 |
| `consent_audit_log` | 1629 | 1 |
| `payments` | 1 | 1 |
| `vouchers` | 149 | 1 |

## config/altele

| colecție | documente | refs |
|---|---|---|
| `app_settings` | 3 | 32 |
| `onboarding_emails` | 93 | 26 |
| `design_tokens` | 1 | 23 |
| `admin_approvals` | 4 | 21 |
| `revenue_opportunities` | 98 | 20 |
| `admin_todos` | 15 | 18 |
| `platform_config` | 1 | 18 |
| `specialist_gaps` | 8 | 17 |
| `entity_links` | 15 | 14 |
| `landing_presets` | 3 | 14 |
| `feature_config` | 1 | 13 |
| `lead_scores` | 2764 | 13 |
| `marketing_campaigns` | 2 | 13 |
| `automation_rules` | 6 | 12 |
| `design_proposals` | 9 | 11 |
| `it_collaborators` | 0 | 11 |
| `twin_scheduled_actions` | 0 | 10 |
| `service_pages` | 1 | 9 |
| `audit_anomalies` | 6 | 8 |
| `nonconformities` | 7 | 8 |
| `price_observations` | 132 | 8 |
| `quests` | 6 | 8 |
| `seo_config` | 1 | 8 |
| `lead_magnet_leads` | 1 | 7 |
| `marketing_conversions` | 12 | 7 |
| `design_presets` | 6 | 6 |
| `eh_formulas` | 11 | 6 |
| `feature_pairs` | 7 | 6 |
| `storage_usage` | 7 | 6 |
| `user_quest_progress` | 262 | 6 |
| `fee_configs` | 1 | 5 |
| `interior_design_leads` | 4 | 5 |
| `marketing_attributions` | 118 | 5 |
| `auto_match_schedule` | 1 | 4 |
| `design_lock` | 1 | 4 |
| `docs_share_tokens` | 346 | 4 |
| `hh_scoring_config` | 1 | 4 |
| `pb_config` | 1 | 4 |
| `settings` | 1 | 4 |
| `tier_rules` | 1 | 4 |
| `twins_orphan_archive` | 18 | 4 |
| `beta_feedback` | 1 | 3 |
| `import_batches` | 1 | 3 |
| `interior_design_content` | 1 | 3 |
| `storage_configs` | 1 | 3 |
| `storage_meta` | 1 | 3 |
| `twin_action_tokens` | 0 | 3 |
| `twin_conversations` | 3 | 3 |
| `automation_emails` | 47 | 2 |
| `engagement_state` | 24 | 2 |
| `integration_health` | 1 | 2 |
| `lead_scores_meta` | 1 | 2 |
| `marketplace_intel_recos` | 1 | 2 |
| `pb_trust_scores` | 9 | 2 |
| `platform_settings` | 1 | 2 |
| `service_leads` | 0 | 2 |
| `tenant_migrations` | 1 | 2 |
| `visitor_identities` | 23 | 2 |
| `city_partner_nudges` | 0 | 1 |
| `marketplace_presentations` | 0 | 1 |
| `content_articles` | 1 | 0 |
| `security_config` | 1 | 0 |

## intern

| colecție | documente | refs |
|---|---|---|
| `admin_ai_findings` | 42 | 62 |
| `ai_brain_graph_edges` | 5463 | 27 |
| `qa_sessions` | 14 | 24 |
| `ai_memories` | 113 | 23 |
| `ai_brain_processes` | 45 | 19 |
| `orchestrator_ledger` | 500 | 19 |
| `admin_ai_repair_suggestions` | 43 | 18 |
| `autonomy_snapshots` | 368 | 18 |
| `ai_documents` | 17 | 17 |
| `orchestrator_retry_queue` | 1962 | 17 |
| `ai_brain_navigation` | 3042 | 14 |
| `ai_decision_ledger` | 5 | 14 |
| `agent_runs` | 5140 | 13 |
| `architecture_guardian_tasks` | 5 | 13 |
| `growth_campaigns` | 4 | 13 |
| `ai_brain_decision_feedback` | 237 | 12 |
| `ai_brain_explanations` | 24 | 12 |
| `ai_brain_graph_nodes` | 2284 | 12 |
| `orchestrator_decisions` | 2748 | 12 |
| `autopilot_runs` | 90 | 11 |
| `ai_brain_notifications` | 18 | 10 |
| `ai_sessions` | 17 | 10 |
| `product_guardian_tasks` | 14 | 10 |
| `release_gates` | 11 | 10 |
| `ai_brain_decisions` | 39 | 9 |
| `autonomy_alerts` | 9 | 9 |
| `health_repair_runs` | 96 | 9 |
| `admin_ai_health_history` | 120 | 8 |
| `ai_brain_sla_status` | 7 | 8 |
| `command_center_recos` | 1 | 8 |
| `copilot_timeline` | 56 | 8 |
| `design_audit_cache` | 7 | 8 |
| `journey_guardian_tasks` | 8 | 8 |
| `term_clusters` | 5 | 8 |
| `admin_ai_sessions` | 5 | 7 |
| `xos_widget_registry` | 10 | 7 |
| `ai_brain_process_stats_history` | 1434 | 6 |
| `ai_brain_registry` | 8 | 6 |
| `cs_findings` | 6829 | 6 |
| `kg_entity_registry` | 27 | 6 |
| `playbook_executions` | 1878 | 6 |
| `admin_ai_messages` | 22 | 5 |
| `ai_weekly_briefing_history` | 1 | 5 |
| `architecture_guardian_runs` | 166 | 5 |
| `ai_brain_runs` | 74 | 4 |
| `ai_outcomes` | 5 | 4 |
| `ai_weekly_briefing_config` | 1 | 4 |
| `enterprise_health_history` | 9 | 4 |
| `growth_insights` | 1 | 4 |
| `marketing_insights` | 1 | 4 |
| `orchestrator_config` | 2 | 4 |
| `orchestrator_escalation_dedup` | 1 | 4 |
| `admin_ai_scans` | 174 | 3 |
| `ai_match_notifications` | 92 | 3 |
| `ai_messages` | 34 | 3 |
| `autonomy_loop_runs` | 7 | 3 |
| `boost_dev_runs` | 1 | 3 |
| `business_health_history` | 23 | 3 |
| `case_library` | 2 | 3 |
| `data_integrity_runs` | 9 | 3 |
| `evolution_council_reports` | 74 | 3 |
| `manual_test_runs` | 10 | 3 |
| `orchestrator_signals` | 500 | 3 |
| `product_guardian_runs` | 171 | 3 |
| `admin_ai_alert_config` | 1 | 2 |
| `ai_brain_graph_meta` | 1 | 2 |
| `ai_brain_mentor_seen` | 123 | 2 |
| `ai_insights_cache` | 4 | 2 |
| `capability_catalog` | 1 | 2 |
| `copilot_reports` | 24 | 2 |
| `cs_money_flow` | 1 | 2 |
| `exec_briefings` | 24 | 2 |
| `journey_guardian_runs` | 173 | 2 |
| `orchestrator_reviews` | 167 | 2 |
| `pattern_findings` | 15 | 2 |
| `revenue_hunter_scans` | 47 | 2 |
| `security_ai_runs` | 3 | 2 |
| `tier_promotion_runs` | 130 | 2 |
| `war_room_meta` | 1 | 2 |
| `ceo_briefings` | 74 | 1 |
| `data_integrity_actions` | 18 | 1 |
| `founder_digest_log` | 19 | 1 |
| `growth_insights_history` | 155 | 1 |
| `marketing_insights_history` | 78 | 1 |
| `roadmap_advice` | 14 | 1 |

## log

| colecție | documente | refs |
|---|---|---|
| `admin_audit_log` | 26 | 22 |
| `analytics_sessions` | 4388 | 21 |
| `smoke_test_runs` | 7666 | 13 |
| `activity_events` | 1121 | 12 |
| `admin_actions_log` | 5000 | 12 |
| `analytics_events` | 22041 | 12 |
| `demo_leads` | 4 | 11 |
| `impersonation_logs` | 450 | 11 |
| `app_settings_snapshots` | 50 | 10 |
| `hh_audit_log` | 13 | 9 |
| `oauth_health` | 298 | 8 |
| `seo_events` | 11 | 8 |
| `auto_match_runs` | 200 | 7 |
| `passport_events` | 31 | 7 |
| `pb_deal_signals` | 5 | 7 |
| `smoke_test_config` | 1 | 7 |
| `backup_runs` | 111 | 6 |
| `demo_activity_logs` | 176 | 6 |
| `lead_followup_log` | 5 | 6 |
| `audit_log` | 4 | 5 |
| `specialist_followup_log` | 4 | 5 |
| `ab_events` | 4809 | 4 |
| `health_pings` | 16222 | 4 |
| `menu_clicks` | 350 | 4 |
| `analytics_settings` | 1 | 3 |
| `automation_executions` | 1654 | 3 |
| `experience_tier_history` | 2 | 3 |
| `fairprice_signals` | 18 | 3 |
| `pvi_history` | 56 | 3 |
| `security_rate_buckets` | 33 | 3 |
| `docs_send_events` | 344 | 2 |
| `email_log` | 9113 | 2 |
| `geo_ip_cache` | 2 | 2 |
| `interior_assistant_sessions` | 2 | 2 |
| `marketing_chat_sessions` | 0 | 2 |
| `scheduler_runs` | 1 | 2 |
| `ux_lab_events` | 53 | 2 |
| `demo_reset_log` | 159 | 1 |
| `fee_configs_history` | 3 | 1 |
| `property_maturity_history` | 49 | 1 |
| `twin_actions_log` | 0 | 1 |

## Doar în cod

`ab_experiments`, `admin_ai_alert_history`, `admin_snapshots`, `admin_todo_state`, `ai_brain_certification`, `ai_doc_chunks`, `architecture_guardian_ignores`, `autonomy_decontamination_log`, `autonomy_targets`, `beta_issues`, `building_announcements`, `city_partner_products`, `client_copilot_cache`, `client_junior_requests`, `com`, `command`, `community_campaigns`, `concierge_conversations`, `concierge_settings`, `contact_playbooks`, `daily_wins`, `deprecation_pulse_config`, `deprecation_pulse_history`, `dev_velocity_runs`, `digital_twin_design_concepts`, `digital_twin_qa_sessions`, `digital_twin_validations`, `doc_conflicts`, `doc_overrides`, `eh_formula_audit`, `email_templates`, `events`, `experience_profiles`, `experience_tier_config`, `financial_insights`, `franchise_applications`, `future_ideas_digest_config`, `future_ideas_digest_history`, `future_ideas_status`, `gdpr_breach_drills`, `health_history`, `incident_recipient_presets`, `incidents`, `it_copilot_reports`, `lead_followup_runs`, `list_collection_names`, `maintenance_logs`, `manual_payments`, `marketing_performance_learnings`, `marketing_performance_logs`, `marketing_recommendations`, `marketplace_copilot_reports`, `marketplace_offers`, `migration_backups`, `name`, `notification_center_acks`, `partner_leads`, `pb_advisor_reports`, `pb_referral_pending`, `pb_subscription_health`, `platform_roadmap`, `platform_roadmap_analysis`, `policy_documents`, `preset_schedule_runs`, `preset_schedules`, `preset_send_history`, `product_guardian_ignores`, `product_map_snapshots`, `project_lifecycle_actions`, `qa_runs`, `recommendations`, `security_events`, `self_driving_settings`, `service_availability`, `site_content`, `storage_migrations`, `strategic_cross_refs`, `stripe_customers`, `stripe_subscriptions`, `system_alerts`, `term_inconsistencies`, `ui_rules`, `wallet`, `wallets`, `xos_layout_history`, `xos_layouts`
