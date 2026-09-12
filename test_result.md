#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
## Iteration 128 — Operations Center Complete (Gap Engine + Manual Payment Mode)
- Date: 2026-07-26
- Backend: /app/backend/routes/operations_center.py (rewritten)
  - GET /api/admin/operations — summary (leads now include `id`, gaps from specialist_gaps collection, coo_report with manual_payments)
  - PATCH /api/admin/operations/leads/{id} — stage/note/next_action (notes push to ops_notes array; sets ops_stage to survive legacy re-sync)
  - GET /api/admin/operations/gaps?status=&category=&city= — Gap Records (auto-synced from unassigned open requests)
  - GET /api/admin/operations/gaps/export?status= — CSV export
  - GET /api/admin/operations/gaps/{gap_id}/candidates — matching specialists (fallback: top verified)
  - POST /api/admin/operations/gaps/{gap_id}/assign — assigns specialist to request, resolves gap, notifies
  - GET/POST /api/admin/operations/manual-payments — VERIFIED payments ledger linked to Lead+Customer+Project (lead moves to payment_received, revenue_generated incremented)
  - POST /api/admin/operations/manual-payment — VE order manual payment (also writes ledger)
  - POST /api/admin/operations/win — One Win Per Day
- Frontend: OperationsCenter.jsx + OpsGapsPanel.jsx + OpsPaymentsPanel.jsx (route /admin/operations, admin only)
- Main agent self-test: full curl E2E passed (lead patch, gap assign, manual payment, CSV export, validations); smoke screenshots OK.

## Iteration 129 — Enterprise Health Engine (D122) + Formula Registry (D151)
- Date: 2026-07-26
- Backend: /app/backend/routes/enterprise_health.py (new) — prefix /api/admin/enterprise-health
  - GET '' — overall score + 11 domains (product, ux, operations, growth, marketplace, customer_trust, knowledge, revenue, automation, technical_debt, ai_learning) computed from REAL evidence; alerts for domains < warning_threshold (cause, business_impact, top 3 actions with estimated_gain_pts, estimated_effect); daily snapshot into enterprise_health_history
  - GET /formulas — registry list (11 formulas, seeded idempotently in eh_formulas)
  - GET /formulas/{key}/explain — calculation steps, weights, contributions, positive/negative contributors, confidence
  - PATCH /formulas/{key} — edit weights/thresholds/status; requires reason (400 otherwise); validations (invalid metric 400, negative weight 400, warn<=crit 400); versioning + audit into eh_formula_audit
  - POST /formulas/{key}/rollback — restores previous version
  - GET /formulas/{key}/audit — audit log
- Frontend: EnterpriseHealthPage.jsx + EhDomainCard.jsx, route /admin/enterprise-health, menu item in AdminLayoutMetronic
- Main agent self-test: full curl suite passed (summary, formulas, explain, PATCH+validations, rollback restores weights, audit trail); screenshots OK (overall 59 Critical, 9 alerts with actions).

## Iteration 148 — CORE-001 Discovery Center + Product Intelligence Engine
- Date: 2026-07-28
- Backend: /app/backend/ai_brain/product_intelligence.py (new) + endpoints in routes/ai_brain.py:
  - GET /api/admin/ai-brain/product-map?refresh= — Live Product Map (19 module canonice, completeness+BVS+priority, orphans, duplicates, consolidation roadmap)
  - POST /api/admin/ai-brain/product-map/snapshot {label} — snapshot istoric in db.product_map_snapshots
  - GET /api/admin/ai-brain/product-map/snapshots — list
  - GET /api/admin/ai-brain/product-map/snapshots/compare?a=&b= — diff completeness per modul
  - GET /api/admin/ai-brain/product-map/report — MASTER DISCOVERY REPORT markdown (+ scris in /app/docs/CORE001_MASTER_DISCOVERY_REPORT.md)
  - All admin-only (401 unauth verified)
- Frontend: components/DiscoveryCenter.jsx mounted in pages/admin/AIBrainPage.jsx (/admin/ai-brain), testids: discovery-center, dc-totals, dc-avg-completeness, dc-tab-{module,duplicate,orfane,roadmap,snapshots}, dc-module-{key}, dc-module-toggle-{key}, dc-refresh-btn, dc-report-btn, dc-snapshot-btn, dc-compare-btn
- Main agent self-test: full curl E2E passed (map refresh, 2 snapshots, compare with zero deltas, report 14KB, 401 unauth); screenshots OK (modules grid + roadmap tabs)

## Iteration 149 — PB-001 PropBenefits Engine Foundation
- Date: 2026-07-28
- Backend NEW domain /app/backend/propbenefits/: config.py (pb_config singleton + seed 4 campanii), ledger.py (Benefits Wallet: grant/use/expire, pb_ledger), campaigns.py (Campaign Engine CRUD+claim atomic cu buget/limite), eligibility.py (user_context + 10 reguli), membership.py (6 niveluri Explorer→Elite din puncte configurabile), opportunities.py (Opportunity Engine + AI Recommendation targeting determinist explicabil), referral_ext.py (beneficii DOAR la abonament activ/primul serviciu plătit — pb_referral_pending), health.py (Subscription Health per user, Ecosystem Health global, Subscription Impact Score per modul CORE-001), ai_agents.py (AI Success Manager + AI Growth Advisor cu LLM prin ai_core.call_llm)
- Routes: /api/benefits/{opportunities,wallet,membership,claim/{cid},use/{bid},success-manager} (user) + /api/admin/prop-benefits/{overview,campaigns CRUD,config GET/PATCH,subscription-health,ecosystem-health,impact-scores,growth-advisor,run-tick} (admin)
- Hooks: trust_growth.py claim→on_referral_claimed · house_health_billing.py activare→activate_for_user · server.py scheduler tick 08:45 · ai_brain/mentor.py folosește success_manager
- Frontend: components/PropBenefitsHub.jsx (tab Beneficii în ClientDashboardV2, deep-link ?tab=benefits, buton settings mobil) · pages/admin/PropBenefitsAdminPage.jsx (/admin/prop-benefits: campanii CRUD fără cod, config niveluri/puncte/referral, subscription health list, growth advisor, ecosystem health) · DiscoveryCenter tab „Impact abonamente"
- Testids: pb-hub, pb-membership, pb-level-badge, pb-next-action, pb-opportunities, pb-opp-{cid}, pb-claim-{cid}, pb-locked, pb-wallet, pb-wallet-tab-*, pb-use-{bid}, pb-message · pbadmin-page, pbadmin-kpis, pbadmin-tab-*, pbadmin-new-campaign, pbadmin-campaign-form, pbadmin-f-*, pbadmin-form-save, pbadmin-camp-{id}, pbadmin-edit-{id}, pbadmin-config, pbadmin-run-tick, pbadmin-advisor-refresh · dc-impact
- Main agent self-test E2E curl: opportunities targetate (locked cu unlock), claim OK + dublu 409, use OK, wallet counts, success-manager next action, admin CRUD + validare 400, config PATCH, run-tick (expire+referral+health snapshot), referral flow COMPLET (invite→claim→pending→plată simulată→tick→activated→beneficii ambele părți), growth advisor LLM RO 2000+ chars, mentor integration, 401 unauth, 403 client pe admin. Screenshots: pb hub client (dark theme OK) + admin (KPIs, campanii, ecosystem). Test data cleaned.

## Iteration 150 — PB-002 PropBenefits Everywhere
- Backend: summaries.py (pulse/specialist/building/marketplace-flags/context-banner), community_deals.py (12 seed, support idempotent, admin CRUD), north_star() în health.py, Success Manager house-centric, North Star în promptul Growth Advisor
- Frontend: components/pb/PbEverywhere.jsx montat în HomeV2, SpecialistDashboard (rail + merge xosLayout), AdministratorWorkspace, HouseHealthPage, DigitalTwinPage, Marketplace, PropBenefitsHub (Community Deals), PropBenefitsAdminPage (North Star + Deals tab)
- Testing: iteration_168 (backend 100%), fixes: xosLayout merge pentru widget-uri noi + test mentor pe source_action_id → suite PB-001+PB-002: 44 passed 1 skipped
- Known pre-existing: ServiceGate 'specialisti' redirect pe /marketplace pentru client logat (strip-ul nu se poate exersa în UI demo; API OK)

## Iteration 151 — PB-003 Community Trust & Recommendation Engine
- Backend: propbenefits/trust_engine.py (recommendation engine cu AI classify, trust score explicabil + cache, ambassador + promovare, rewards DOAR la efect real, deal signals + demand + priority, trust graph în ai_brain, community growth 6 răspunsuri); config: recommendation_reward + ambassador (get_config merge defaults); success_manager: slot community_action + almost_ambassador impact 9
- Routes: POST/GET /api/benefits/recommendations(+/mine), /ambassador, /community-deals/{id}/signal + /why, /trust/{id}; admin /community-growth; tick extins (validate+trust+graph)
- Marketplace: _trust extins cu pb_trust_scores batch (trust_score/confirmed_jobs/ambassadors/community_value)
- Frontend: PostJobGrowthLoop pjl-recommend, AmbassadorCard, deals cu 4 semnale, Marketplace trust badges, Admin GrowthPanel
- Testing: iteration_169 backend 100% frontend 100%; fix post-test: community_action slot (xfail→pass); suite totală 63 passed 2 skipped
