# EXISTING BUSINESS / FINANCIAL / PRODUCT HEALTH ECOSYSTEM

**Mode:** READ-ONLY discovery + architecture reconstruction.  
**Date:** 2026-09-23  
**Constraint:** No implementation, schema, agents, services, tables, dashboards, pricing, Marketplace, Digital Twin, entitlements, commit, or deploy.

**No implementation performed.**

Financial figures that are not computed in code, or that mix demo/real without a filter, are marked **UNKNOWN** as *usable money truth*. Hardcoded estimates are named as such.

---

# Verdict in one paragraph

PropManage already has a **large observability + recommendation + scheduled-action estate**, not a single Business/Financial/Product Health system. At least **three independent health scores** (Business Health 8 departments, Enterprise Health 11 domains, Autonomy snapshots) feed **two different CEO surfaces** (CEO Dashboard vs CEO Briefing). **Revenue is defined at least four ways** and they contradict each other. **Lead Credits and wallets do not appear** in any of those financial/health aggregators. Automation Center is a **3-rule island**. Health Repair **does run detect→repair→validate on a daily cron** (semi-automated / bounded automated — not a closed economic loop). Weekly “CEO report” infrastructure exists as **8+ Monday emails and pages that do not share one payload**. Do not build a new Health OS. First decide which score and which revenue definition are canonical.

---

# PART 1 — Discovery complete

Surfaces found (runtime, not just docs):

| Cluster | Evidence |
|---|---|
| Health scores | `business_health.py`, `enterprise_health.py`, `autonomy/snapshots.py`, `health_repair.py`, House Health (property product — **different word**) |
| Money views | `financial_cockpit.py`, `first_revenue.py` (War Room), `marketing_growth.py` “financial”, `payments.py` DEMO, `wallet.py`, D8 confirm 0.95, `finance_reconciler` playbook |
| Executive | `ceo_dashboard.py`, `ceo_briefing.py`, `control_tower.py`, `command_center.py`, `evolution_council.py` |
| Product / UX | `beta_cockpit.py`, `health_repair` + guardians, `ai_brain/product_intelligence.py`, `design_audit.py`, `design_intelligence.py`, `architecture_board.py` |
| Growth / intel | `analytics_growth.py`, `growth_intelligence.py`, `lead_intelligence`, `marketing_intelligence.py`, `marketplace_intel.py`, `revenue_hunter.py` |
| AI / autonomy | `ai_governance/`, `orchestrator/`, `autonomy/`, `automation_center.py`, `ai_insights.py` |
| Knowledge | `knowledge_center.py` (founder docs), `ai_documents` / `ai_memories` / `case_library` (EH Knowledge domain) |
| Security | `oauth_health` + `auth_health_alert`, `ai_security.py`, `security_guard.py` |
| Reports | `executive_briefing.py`, `ai_weekly_briefing.py`, `founder_digest`, `dev_velocity_service`, `admin_briefing_digest`, Command Center morning email |
| Scheduler | `server.py` AsyncIOScheduler — **70+ jobs** Europe/Bucharest |

**House Health** (`hh_*`, client product) is **not** Business Health or Enterprise Health. Same English word, different product.

---

# PART 2 — Inventar real

STATUS only where evidenced. “File exists” ≠ IMPLEMENTED as a health system.

| COMPONENT | LOCATION | TYPE | PURPOSE | DATA SOURCE | INPUTS | OUTPUTS | API | DATABASE | SCHEDULER | CONSUMERS | STATUS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Business Health | `routes/business_health.py` | 8 dept scores 0–100 | Dept heat map | users, requests, disputes, payment_transactions, design_audit_cache | 30/60d windows | departments, overall | GET `/api/admin/business-health` | `business_health_history` (on GET, max 1/day) | **None dedicated** | Command Center, CEO Dashboard, UI | IMPLEMENTED · CONNECTED · **not AUTOMATED** (snapshot only if someone hits GET) |
| Enterprise Health | `routes/enterprise_health.py` | 11 domain + formula registry | Company health D122/D151 | 20+ collections; VE paid !demo + manual_payments | `eh_formulas` | domains, alerts, enterprise_score | `/api/admin/enterprise-health` | `eh_formulas`, `eh_formula_audit`, `enterprise_health_history` | History on GET | CEO Briefing, Repair, Evolution Council, UI | IMPLEMENTED · CONNECTED · DOCUMENTED |
| Financial Cockpit | `routes/financial_cockpit.py` | Money dashboard | Paid txs + escrow + HH MRR | `payment_transactions`, `requests`, `hh_*` | All `paid` txs **no demo filter** | revenue, escrow, mrr/arr, **10% take est.** | `/api/admin/financial-cockpit` | `financial_insights` | None | CEO Dashboard, UI, AI Insights finance | IMPLEMENTED · CONNECTED |
| Marketing Growth KPIs | `routes/marketing_growth.py` | Marketing dashboard | Users, LTV proxy, funnel | `users`, `requests.escrow_amount` confirmed | 30/60d | estimated_ltv, churn_rate, profit_estimated 25% | `/api/admin/marketing/dashboard` | none (live) | None | Marketing Department UI | IMPLEMENTED · **CONTRADICTS** Cockpit |
| War Room | `routes/first_revenue.py` | Mission dashboard | First real VE revenue | VE orders/listings, leads, analytics | `demo_mode` split | mission_100, revenue_real vs demo | GET `/api/admin/war-room` | `war_room_meta` | None | UI, CEO Briefing | IMPLEMENTED · CONNECTED · EVIDENCED |
| CEO Dashboard | `routes/ceo_dashboard.py` | Super-admin composite | One payload | **BH + Cockpit + CC feed** + PVI/maturity | live compose | business_score, mrr, top3 recos | GET `/api/admin/ceo` | reads `command_center_recos` | None | UI `/admin/ceo` | IMPLEMENTED · CONNECTED |
| CEO Briefing | `routes/ceo_briefing.py` | Daily decision page | One thing today | **EH + War Room** + leads/gaps/VE | live + upsert | briefing | GET `/api/admin/ceo-briefing` | `ceo_briefings` | **No cron** (GET or Evolution Council) | UI, Evolution Council | IMPLEMENTED · CONNECTED |
| Control Tower | `routes/control_tower.py` | Attention + 1 action | Sorted problems | ledger, KYC, disputes, retry queue | 7d | attention, pulse | GET + POST reconcile-orphans | `transactions` on action | None | UI, AI Insights | IMPLEMENTED · PARTIAL ACT |
| Command Center | `routes/command_center.py` | Ops feed + Top 5 | Daily priorities | requests, users, BH, growth_insights | live feed | recos, email, `business_alert` | `/api/admin/command-center/*` | `command_center_recos`, `ai_decision_ledger` | **07:00** | CEO Dashboard, Notification Center | IMPLEMENTED · AUTOMATED |
| Notification Center | `routes/notification_center.py` | Admin inbox | Ack-able feed | reuses `_build_feed` | feed | items | GET/POST ack | ack store | None | UI | IMPLEMENTED · CONNECTED to CC |
| Beta Cockpit | `routes/beta_cockpit.py` | Beta funnel | Real-user gates | analytics_sessions, users, properties | days window | funnel, VoC | `/api/admin/beta/*` | `beta_feedback` | None | UI; **purge-demo ACT** | IMPLEMENTED · CONNECTED |
| Beta Issues | frontend + admin beta issues | Issue board | Manual tickets | `beta_issues` (source war_room) | human | issues | POST `/api/admin/beta/issues` | issues | None | UI | IMPLEMENTED (manual) |
| Health Repair | `health_repair.py` | detect→repair→validate | Domain under threshold | EH metrics + ops collections | DOMAIN_ENGINES | `health_repair_runs` | via Repair Center | `health_repair_runs`, ledger | **06:20 daily** | Repair Center | IMPLEMENTED · AUTOMATED · **bounded AUTONOMOUS** |
| Repair Center | `routes/repair_center.py` | Control plane | Status + manual run + guardians | EH + run history | domain list | runs | `/api/admin/repair-center/*` | guardian task collections | Guardian crons 06:40–06:50 | UI | IMPLEMENTED · CONNECTED |
| Journey / Arch / Product Guardians | `*_guardian.py` | Auditors | Tasks for humans | funnel / atlas / CTA | scans | tasks | Repair Center | `*_guardian_tasks` | daily | Repair Center | IMPLEMENTED · recommend |
| Automation Center | `routes/automation_center.py` | 3 IF→THEN templates | Remind / badge / reactivation | requests, users | enabled rules | notifications, badges, email queue | `/api/admin/automation` | `automation_rules`, `automation_executions` | hourly `run_due_rules` | UI | IMPLEMENTED · **island** · AUTOMATED if enabled (default **disabled**) |
| Orchestrator | `orchestrator/` | Signal → playbook | Autonomy 2.0 | event bus | signals | ledger, notify, some DB writes | `/api/admin/orchestrator` | `orchestrator_*` | many event + cron | Autonomy UI | IMPLEMENTED · mixed authority |
| Autonomy Engine | `autonomy/` | Scores + self-driving | Platform autonomy % | snapshots | metrics | `autonomy_snapshots` | `/api/admin/autonomy` | snapshots, todos, approvals | 03:15 + loops | EH automation domain, UI | IMPLEMENTED · PARTIAL ACT |
| AI Insights | `routes/ai_insights.py` | On-demand Claude | Narrative | module context | module name | bullets, cache 6h | `/api/admin/insights/llm` | `ai_insights_cache` | None | cards on dashboards | IMPLEMENTED · recommend |
| AI Governance Center | `routes/ai_governance.py` + `agent_registry.py` | Catalog + snapshot | Who may do what | registry (metadata), governance_snapshot | — | dashboard | `/api/admin/ai-governance` | `orchestrator_decisions` | watchdog :07/:37 | CEO Briefing, UI | IMPLEMENTED · registry **not** runtime gate |
| Architecture Review Board | `routes/architecture_board.py` | Static catalog | Module list | hardcoded slugs | — | catalog | `/api/admin/architecture-board` | none | None | UI | IMPLEMENTED · OBSERVE |
| Knowledge Center | `routes/knowledge_center.py` | Founder docs | Search repo knowledge | files/JSON | query | pages | `/api/founder/knowledge/*` | mostly files | None | UI | IMPLEMENTED · **not** wired as briefing source except EH counts |
| Design Audit | `routes/design_audit.py` | UX page scores | Mobile/desktop | pages | cache 12h | `design_audit_cache` | admin design-audit | cache | Repair UX refresh | BH SEO, EH UX | IMPLEMENTED · CONNECTED to scores |
| Design Intelligence | `routes/design_intelligence.py` | UX proposals | Impact score | design_* | admin | proposals | `/api/admin/design-intelligence` | proposals | None | UI; apply = **admin only** | IMPLEMENTED · execute-with-approval |
| Product Intelligence (AI Brain) | `ai_brain/product_intelligence.py` | Code product map | Live map of routes/pages | filesystem | scan | `product_map_snapshots` | `/api/admin/ai-brain/product-map*` | snapshots | 06:35 discovery | Discovery Center | IMPLEMENTED · **≠** `property_intelligence.py` |
| Property Intelligence | `property_intelligence.py` | Property maturity | L0–L5, decay, risk | properties | owner APIs | maturity/risk | `/api/properties/...` | property fields | hunter refresh | CEO Dashboard KPIs | IMPLEMENTED · **not** Product Health |
| Growth Intelligence | `growth_intelligence.py` | Funnel insights | UX analytics | analytics_sessions | scan | `growth_insights` | growth-intel API | insights | 06:40 | Command Center | IMPLEMENTED · recommend |
| Marketplace Intel | `routes/marketplace_intel.py` | Supply/demand | Category deficit | requests, users | — | recos | `/api/admin/marketplace-intel` | `marketplace_intel_recos` | None | UI | IMPLEMENTED · recommend |
| Revenue Hunter | `revenue_hunter.py` | Opportunity rows | DNA → opportunities | properties, twins | daily | `revenue_opportunities` | no HTTP | opportunities, scans | 07:10 + Repair revenue | Repair, agent registry | IMPLEMENTED · **does not contact clients** |
| Weekly Exec Briefing | `executive_briefing.py` | Email 7d WoW | Users/jobs/disputes/gates | users, requests, disputes, release_gates | 7d/14d | HTML + `exec_briefings` | `/api/admin/exec-briefing/*` | `exec_briefings` | **Mon 09:45** | ADMIN_EMAILS | IMPLEMENTED · AUTOMATED |
| Weekly AI Briefing | `ai_weekly_briefing.py` | AI activity email | AI events | ledger/config | week | `ai_weekly_briefing_history` | admin widget | history | **Mon 09:00** | config recipients | IMPLEMENTED · AUTOMATED |
| Founders Digest | `founder_digest` | Weekly KPI email | Autonomy/autopilot | snapshots | week | email | — | none dedicated | **Mon 09:30** | super-admins | IMPLEMENTED · AUTOMATED |
| Dev Velocity | `dev_velocity_service.py` | Eng weekly | Commits/velocity | git/service | week | `dev_velocity_runs` | admin_dev_velocity | runs | **Mon 09:30** | ADMIN_EMAILS | IMPLEMENTED · AUTOMATED |
| Morning Briefing | `admin_briefing_digest` | Daily email if not ok | Healthcheck | healthcheck_service | live | email | — | **no history insert** | **09:00 if ≠ ok** | ADMIN_EMAIL | IMPLEMENTED · AUTOMATED |
| Evolution Council | `routes/evolution_council.py` | Nightly 5 Qs | Reuses EH + CEO Briefing | same | nightly | `evolution_council_reports` | `/api/admin/evolution-council` | reports | **23:45** | UI `/admin/evolution-council` | IMPLEMENTED · AUTOMATED · observe |
| Marketplace Medic | orchestrator playbook | Suspend specialists | Disputes/users | daily 05:10 | user flags | signal | users | **05:10** | specialists | IMPLEMENTED · AUTONOMOUS (L4) |
| Finance Reconciler | playbooks_sprint3 | Wallet/escrow check | wallets, txs, requests | daily 04:50 | **notify only** | signal | — | **04:50** | admins | IMPLEMENTED · observe/recommend |
| Auth Health | `routes/auth.py` | OAuth success rate | `oauth_health` | */15 | alerts | `/api/admin/auth-health` | `oauth_health`, `system_alerts` | */15 | AdminAuthHealthPage | IMPLEMENTED · AUTOMATED alerts |
| Feature flags | `admin_console` presets | Config | `landing_show_unit_economics` | admin | flags | preset_schedules */1m | settings | may flip flags | IMPLEMENTED |

---

# PART 3 — Existing financial health

## Money classes (do not merge)

| Class | Where it lives | In Financial Cockpit? | In Enterprise Health “Revenue”? | In Marketing Growth “revenue”? |
|---|---|---|---|---|
| **REAL MONEY (VE, !demo)** | `verified_estate_orders` paid `demo_mode≠true` + `manual_payments` verified | **No** | **Yes** (`real_revenue`, target 5000 RON) | **No** |
| **DEMO MONEY (VE)** | same collection `demo_mode=true` | No | Excluded | No |
| **DEMO / TEST Stripe (Marketplace checkout)** | `payments.py` `DEMO_STRIPE` writes `payment_transactions` / request paid with `demo_mode` | **Not filtered** — all `payment_status=paid` summed | No | No |
| **INTERNAL WALLET** | `wallet.py` specialist balance (D8 95% credit) | **No** | **No** | **No** |
| **LEAD CREDITS** | `users.lead_credits` | **No** | **No** | **No** |
| **TOKENS / entitlements** | HH subscription status | Only as **MRR = active plan × price_eur × 4.98** | No | No |
| **ATTRIBUTION METADATA** | `routes.attribution` attached to BH Marketing (does not change score) | No | No | Partial Ads |

## Per-item reconstruction

| Item | SOURCE OF TRUTH | CALCULATION | STORAGE | API | UI | REFRESH | CONSUMER |
|---|---|---|---|---|---|---|---|
| Revenue (Cockpit) | `payment_transactions` paid | sum `amount` | none (live) | financial-cockpit | Financial Cockpit, CEO Dashboard | on GET | CEO, insights |
| Revenue (EH) | VE paid !demo + manual | sum `amount_ron` vs 5000 | none (live) | enterprise-health | EH, CEO Briefing | on GET / repair | Repair, Briefing |
| Revenue (Marketing) | `requests` confirmed `escrow_amount` | sum escrow | none | marketing/dashboard | Marketing Dept | on GET | Marketing |
| MRR | `hh_subscriptions` active unexpired × `hh_plans.price_eur` | EUR→RON `* 4.98` | none | cockpit | Cockpit, CEO | on GET | CEO Dashboard |
| ARR | `mrr_ron * 12` | derived | none | cockpit | same | on GET | same |
| Payments / orders | txs + VE orders | status filters | collections | payments / VE | War Room splits demo | event | fragmented |
| Subscriptions | `hh_subscriptions` | status+expires | Mongo | HH + cockpit | HH admin, Cockpit | on GET | Cockpit |
| Stripe | `payments.py` DEMO vs test/live | checkout/webhook | txs | payments | health.stripe | event | **not** a finance cube |
| Commissions | D8 `* 0.95` at `/confirm` | implicit haircut | request/wallet | requests | none as KPI | on confirm | **not** in Cockpit |
| Cockpit “commission” | released escrow × **0.10 hardcoded** | estimate | none | cockpit | Cockpit | on GET | **CONTRADICTS D8 5%** |
| Marketplace revenue | confirm haircut + optional checkout | D8 | wallet / txs | requests | none unified | event | UNKNOWN as dashboard |
| Specialist fees / Lead Credits | credits consume on offer/accept | D2 | `users.lead_credits` | requests | specialist UI | event | **not in health** |
| Wallet | specialist internal | topup / confirm credit | wallets | wallet | specialist | event | Finance Reconciler **notify** |
| Escrow | `requests.escrow_status/amount` | held/frozen/released | requests | cockpit, BH | Cockpit, BH | on GET | D7 still DEMO-capable |
| Refunds | UNKNOWN as aggregated KPI | — | disputes? | — | — | — | MISSING |
| Payouts | wallet credit, no withdraw | D8 | wallets | — | — | event | MISSING as finance KPI |
| Platform commission | D8 5% vs cockpit 10% vs HH copy 5% | **conflict** | — | — | — | — | CONTRADICTED |
| Costs | **MISSING** (no cost ledger) | — | — | — | — | — | MISSING |
| Margins | Marketing `profit_estimated = total_revenue * 0.25` | **hardcoded 25%** | none | marketing | Marketing | on GET | not real margin |
| Cash flow | Cockpit daily paid 30d | sum by date | none | cockpit | Cockpit | on GET | CEO `cash_flow_status` 80% WoW heuristic |
| Failed / unpaid | cockpit `pending/initiated` sum; BH conversii paid/total | counts | txs | cockpit, BH | BH Conversii | on GET | PARTIAL |
| Demo vs real | War Room + EH filter VE; Cockpit **does not** | — | `demo_mode` on VE/payments | war-room | War Room | on GET | **split only on VE path** |

**CFO:** There is **no single revenue SSOT**. Using CEO Dashboard “revenue” as board money is **unsafe** if DEMO Stripe txs exist.

---

# PART 4 — Business health (what exists / what does not)

| Metric | Exists? | Where | Note |
|---|---|---|---|
| users / registered | YES | BH Marketing, Marketing Growth, Exec Briefing | counts |
| active users | PARTIAL | Marketing `last_login_at`/`updated_at` 30d | proxy |
| verified users (client) | NO composed state | D9 | SELF_ASSERTED |
| properties | PARTIAL | Beta Cockpit, EH product coverage | not BH 8 |
| projects | CONTRADICTED name | DT / demo / request | no single count |
| requests / offers / specialists | YES | BH, EH, Marketplace Intel, Marketing | fill rate = assigned / all time |
| conversion (payments) | PARTIAL | BH conversii = paid/all txs | includes demo if paid |
| conversion (MP funnel) | PARTIAL | Marketing: confirmed/all requests | mixes cancelled+open as abandoned |
| request→offer | MISSING as KPI | D-series | UNKNOWN |
| offer→selection | MISSING as KPI | D6 | UNKNOWN |
| selection→execution | MISSING | `/start` ungated | UNKNOWN |
| execution→payment | MISSING | pay optional | UNKNOWN |
| payment→payout | MISSING | confirm 95% | UNKNOWN as dashboard |
| activation | PARTIAL | Beta gates | not BH |
| retention | PARTIAL | Marketing active/total | rough |
| repeat usage | PARTIAL | recurring = >1 confirmed request | |
| Marketplace liquidity | PARTIAL | fill rate (lifetime assigned) | not open-book liquidity |
| subscription conversion | PARTIAL | cockpit active_subs | no trial→paid (trial UI-only) |
| churn | PARTIAL | Marketing 60d no login; Pattern Hunter specialist 21d | not subscription churn |
| LTV | PARTIAL | `escrow_sum / client_count` | **not** SaaS LTV |
| CAC | **MISSING** | static App.js copy only | |
| revenue per user | MISSING | | |
| revenue per property | MISSING | | |
| revenue per specialist | PARTIAL | Marketing avg of **top 20** confirmed escrow | biased |

BH snapshot is **on-demand**, not a nightly job. History can have **gaps**.

---

# PART 5 — Product health

| System | OBSERVES | MEASURES | ANALYZES | RECOMMENDS | CAN CHANGE | CONSUMER |
|---|---|---|---|---|---|---|
| **EH Product domain** | properties health_score, DNA, twin_unlocked | coverage % vs 90 | weighted score | via EH alerts | **nothing** | EH, Briefing |
| **Beta Cockpit** | sessions, users, properties, docs, passport | funnel gates | drop-offs | none automated | **purge-demo** | Founder UI |
| **Beta Issues** | human tickets | severity | none | none | insert issue | War Room UI |
| **Health Repair (product domain)** | EH product metrics + case/design | score vs threshold | detectors | then repairers | case drafts, design audit refresh | cron 06:20 |
| **AI Brain Product Intelligence** | **codebase** routes/pages | product map | discovery | none product UX | registry/graph | Discovery Center |
| **UX analytics / Growth Intel** | analytics_sessions | funnels | insights docs | insights | **writes insights only** | GI page, CC |
| **Design Audit** | public pages | mobile/desktop score | cache | “run audit” copy | cache rows | BH SEO, EH UX |
| **Design Intelligence** | design tokens/pages | impact score | proposals | proposals | **only after admin apply** | DI page |
| **Evolution Council** | EH + briefing | 5 questions | narrative | priorities | reports collection | nightly, UI |
| **Architecture Review Board** | static module list | none live | none | none | nothing | UI |
| **Feature Configurator / presets** | flags | on/off | none | none | **can flip flags on schedule** | admin |

**Product Health is not one engine.** EH “Product” is property-genome coverage. AI Brain “Product Intelligence” is a **code map**. They share a name only.

---

# PART 6 — Repair / self-healing

```
DETECT (domain detectors + EH score < threshold)
  → REPAIR (reuse existing engines: auto_match, lead_followup, nurture, revenue_hunter,
            review notifications, case_library drafts, design_audit refresh,
            category_visibility signal, governance/retry ticks, index creation)
  → VALIDATE (recompute EH metrics; score_after / delta)
  → persist health_repair_runs + orchestrator ledger + record_decision L4
  → also run Journey / Architecture / Product Guardians
```

| Piece | Evidence |
|---|---|
| Detectors | `_detect_*` per 11 EH domains |
| Repair rules | if `auto_fixable` then `_repair_*` |
| Actions | match, notify, scan, insert notification, emit_signal — **not** schema/price changes |
| Validators | `_collect_metrics` after |
| Evidence | `health_repair_runs` (trimmed >400) |
| Audit trail | `orchestrator_ledger`, `orchestrator_decisions` |
| Approval gates | **None on cron** (authority_level 4 execute) |
| Rollback | **MISSING** for mutations (e.g. auto_match) |
| Learning | ledger + `ai_outcomes` daily scan — **not** formula auto-rewrite |

**Classification: AUTOMATED + bounded AUTONOMOUS, not fully autonomous economic control.**

Why not “manual”: cron `health_repair_daily` 06:20 + Repair Center POST /run.  
Why not “fully autonomous”: many repairs are **notify/scan**; `verified_rate` is `auto_fixable=False`; no rollback; Founder Gate not in the loop; score can stay red after “repair”.

---

# PART 7 — AI ecosystem (execution proof)

Registry (`ai_governance/agent_registry.py`) is **catalog metadata**. Runtime authority = orchestrator governance + cron.

| NAME | ROLE | INPUTS | OUTPUTS | ACTIONS | AUTHORITY | APPROVAL | LOGGING | SCHEDULER | CLASS |
|---|---|---|---|---|---|---|---|---|---|
| Health Repair Engine | domain fix loop | EH | runs | match/notify/scan | L4 | none on cron | ledger + runs | 06:20 | execute-autonomous (bounded) |
| Revenue Hunter | opportunities | properties | opportunity rows | insert + PI refresh | suggest | n/a | scans | 07:10 | **NOT client-autonomous** |
| Command Center morning | recos + email | feed | recos, `business_alert` | email + signal | L4 notify | none | recos | 07:00 | execute (notify) |
| Marketplace Medic | specialist hygiene | disputes | `medic_suspended` | **suspend/reactivate** | L4 | none | ledger | 05:10 | execute-autonomous |
| Finance Reconciler | consistency | wallets/txs | alerts | notify | L3 | human fix | ledger | 04:50 | observe/recommend |
| Pattern Hunter | patterns | requests/users | findings | notify | L3 | none | `pattern_findings` | Mon 06:00 | recommend |
| Roadmap Advisor | weekly priorities | ledger | `roadmap_advice` | Claude + notify | L3 | human | ledger | Fri 09:00 | recommend |
| Growth / Lead / Marketing Intel | scans | analytics | insight docs | write insights | suggest | human for contact | collections | 06:40–06:55 | **NOT AUTONOMOUS** |
| Self-Driving | low-risk todos | settings | executed approvals | close todos | configurable | 1h delay listed actions | playbook_executions | */2h | execute-autonomous (narrow) |
| Operational Loop | findings | analytics | todos/approvals | SAFE todo / MEDIUM approval | policy | MEDIUM+ | `autonomy_loop_runs` | */3h | mixed |
| Design Intelligence | UX | design | proposals | apply | admin | **explicit apply** | proposals | none | execute-with-approval |
| AI Insights | LLM cards | module | bullets | cache | none | on-demand | cache | none | recommend |
| Evolution Council | nightly Qs | EH+briefing | report | none | observe | none | reports | 23:45 | observe |
| Twin Orchestrator | DT jobs | user jobs | reminders | user-confirmed | approval | twin confirm | twin actions | 08:15 reminders | execute-with-approval |
| Knowledge Center | docs | files | search | none | read | — | — | none | observe |
| Dispute triage | LLM | dispute | triage text | persist + notify | L3 | human resolve | ledger | event | recommend |

UI “Autonom” = **authority label**, not proof of unsupervised production impact. Governance watchdog can **downgrade** playbooks to observe/recommend.

---

# PART 8 — Automation Center

```
IF (template condition + param)
  THEN executor
  ACTION notification | badge | queue email
  RESULT automation_executions row
```

| | |
|---|---|
| Triggers | hourly scheduler if `enabled` and interval elapsed |
| Rules | **exactly 3**, seeded `enabled: False` |
| Actions | admin notify; `fast_response_badge`; `automation_emails` queued |
| History | `automation_executions` |
| Failures | log + skip (no retry queue) |
| Permissions | admin PATCH enable |

**Connected to:**

| Surface | Connection |
|---|---|
| Health | **DOCUMENTED ONLY** (EH automation domain uses **autonomy snapshots**, not these 3 rules) |
| Revenue | **UNKNOWN / none** |
| Marketplace | PARTIAL (`request_reminder` on stuck requests) |
| Customer | PARTIAL (reactivation queue — send pipeline UNKNOWN if not drained) |
| Product | none |
| Security | none |
| AI | none (not orchestrator) |
| Notifications | **CONNECTED** (in-app insert) |

**Do not confuse** Automation Center with Orchestrator playbooks or Health Repair. Three stacks.

---

# PART 9 — Executive Control Tower

| Surface | DATA SOURCE | FREQUENCY | CALCULATION | DECISION | ACTION |
|---|---|---|---|---|---|
| CEO Dashboard | BH + Cockpit + CC + PI | on open | compose | human | **none** |
| CEO Briefing | EH + War Room + ops | on open / council | one_thing heuristic | human | **none** (persists doc) |
| Control Tower | ledger/KYC/disputes | on open | sort attention | human | **reconcile orphans** |
| War Room | VE + leads + analytics | on open | mission % | human | meta insert |
| Beta Cockpit | analytics + entities | on open | funnel | human | purge-demo |
| Business Health | 8 formulas | on open | scores | human | none |
| Enterprise Health | 11 formulas | on open | scores + formula PATCH | admin can **edit formulas** | config, not ops |
| AI Governance | snapshot + registry | on open | counts | human | none |
| Architecture Board | static | on open | none | none | none |
| Security | oauth_health, AI Security | */15 alerts | rates | human | alert email |
| Command Center | feed + LLM recos | 07:00 + on open | recos | toggle done | email + signal |
| Repair Center | EH + runs | 06:20 + manual | cycle | implicit cron | **executes repairs** |

| Layer | What is actually that |
|---|---|
| **OBSERVABILITY** | BH, EH, Cockpit, War Room, Beta, Auth Health, analytics |
| **ANALYSIS** | AI Insights, GI scans, Marketplace Intel, Pattern Hunter |
| **DECISION SUPPORT** | CEO Briefing one_thing, Command Center Top 5, Evolution Council, Roadmap Advisor |
| **EXECUTION** | Health Repair, Medic, auto_match, Self-Driving, Automation rules, Control Tower reconcile, preset flags |

These four layers **share nav**, not one control loop.

**CONTRADICTION:** CEO Dashboard `business_score` ≠ CEO Briefing `enterprise_score`. Same executive, two denominators.

---

# PART 10 — Weekly reporting

| Mechanism | Generator | Scheduler | Sources | Storage | Delivery | Recipients | WoW compare |
|---|---|---|---|---|---|---|---|
| Weekly Exec Briefing | `executive_briefing.py` | Mon 09:45 | users, requests, disputes, release_gates | `exec_briefings` | email | ADMIN_EMAILS | **Yes** 7d vs prior 7d |
| Weekly AI Briefing | `ai_weekly_briefing` | Mon 09:00 | AI activity | `ai_weekly_briefing_history` | email | config | PARTIAL |
| Founders Digest | `founder_digest` | Mon 09:30 | autonomy | none dedicated | email | super-admins | PARTIAL |
| Dev Velocity | `dev_velocity_service` | Mon 09:30 | git/velocity | `dev_velocity_runs` | email | ADMIN_EMAILS | PARTIAL |
| Future Ideas Digest | future_ideas | Mon 09:15 | ideas | history | email | config | n/a |
| Weekly lead report | self_driving | Mon 09:00 | leads | — | **in-app only** | admins | n/a |
| IT Sprint Digest | it_digest | weekly (default Sun) | IT | settings | email | configured | n/a |
| Release gate | qa_automation | Mon 08:45 | gates | — | email if P0 | admins | n/a |
| Deprecation pulse | deprecation | Thu 09:30 | code | — | scan | — | n/a |
| CEO Briefing page | `ceo_briefing` | **no weekly job** | EH | `ceo_briefings` by **day** | page | admin open | no week rollup |
| Morning digest | briefing_digest | daily 09:00 if not ok | healthcheck | **no persist** | email | ADMIN_EMAIL | no |
| CC morning | command_center | daily 07:00 | feed | recos latest | email | super-admins | no |
| Daily AI digest | admin_ai | daily 08:00 | findings | — | email | admins | no |
| Daily role digest | digest.py | 19:00 | role | — | email | users | no |

**Duplicates:** Monday morning can send **Exec + AI + Founder + Velocity + Ideas + Lead + Release** without a shared outline. CEO Briefing ≠ Exec Briefing (names collide).

---

# PART 11 — Metric lineage (only evidenced arrows)

### Marketplace request (partial)

```
requests insert
  → (optional) analytics_events / notify specialists
  → BH marketplace fill = count(specialist_id) / count(*)     [lifetime, on GET]
  → EH fill_rate same idea
  → Marketing funnel confirmed/all
  → Command Center new_requests_24h
  → CEO Dashboard marketplace_trend_pct (from CC raw)
  → CEO Briefing marketplace line (EH metrics)
  → Repair if fill low → auto_match
  → Weekly Exec Briefing job counts
```

**No** single conversion metric → Business Health → CEO report → approved action → validation.  
Command Center toggle writes `ai_decision_ledger` (done flag), **not** outcome of the request.

### Revenue (broken lineage)

```
payment_transactions.paid ──► Financial Cockpit ──► CEO Dashboard.revenue
verified_estate_orders.paid !demo ──► EH real_revenue ──► CEO Briefing
requests.escrow confirmed ──► Marketing estimated_ltv / profit*0.25
confirm * 0.95 ──► wallet          [NOT in any of the three dashboards]
lead_credits consume ──► users     [NOT in any dashboard]
```

### Health score (parallel)

```
compute_health() ──► BH history (if GET) ──► CEO Dashboard.business_score
_collect_metrics() ──► EH history (if GET) ──► CEO Briefing.enterprise_score
                     ──► Health Repair threshold
autonomy snapshot ──► EH automation domain
```

---

# PART 12 — Cross-system connections

| Relation | Status | Evidence |
|---|---|---|
| Financial Health ↔ Business Health | **PARTIAL** | BH “financiar” uses same txs as Cockpit, **different formula** (growth vs totals). No import. |
| Financial Health ↔ Marketplace | **PARTIAL / CONTRADICTED** | Cockpit escrow + 10% est.; actual take D8 5%; Marketing uses escrow GMV |
| Financial Health ↔ Product | **DOCUMENTED ONLY** | no shared module |
| Financial Health ↔ Growth | **PARTIAL** | Marketing dashboard own “financial” |
| Business Health ↔ Product Health | **PARTIAL** | both read `design_audit_cache` (SEO vs UX) |
| Product Health ↔ Repair | **CONNECTED** | `_detect_product` / `_repair_product` |
| Repair ↔ Automation Center | **UNKNOWN / none** | Repair does not enable the 3 rules |
| Automation Center ↔ AI | **DOCUMENTED ONLY** | comment “Autonomy Level 3”; not orchestrator |
| AI ↔ Knowledge Center | **DOCUMENTED ONLY** | KC is files; EH Knowledge counts `ai_documents` |
| AI ↔ CEO Briefing | **CONNECTED** | `governance_snapshot` + autonomous_execution 24h |
| Marketplace ↔ Revenue | **PARTIAL** | War Room VE; Cockpit txs; not unified |
| Marketplace ↔ Trust | **PARTIAL** | EH customer_trust + Medic + reviews |
| Marketplace ↔ Customer | **PARTIAL** | requests + notifications |
| Digital Twin ↔ Property Intelligence | **PARTIAL** | hunter / maturity / twin_unlocked in EH Product |
| Property Intelligence ↔ Business | **PARTIAL** | CEO Dashboard maturity/risk; **not** BH 8 |
| Security ↔ Health | **PARTIAL** | Auth health; EH technical uses smoke + AI scan, **not** oauth |
| Security ↔ AI | **PARTIAL** | `ai_security.py` |
| Security ↔ Marketplace | **UNKNOWN** | Medic is dispute-based, not WAF |

---

# PART 13 — Data quality

| Issue | Evidence |
|---|---|
| Duplicate metrics | fill_rate in BH and EH; revenue in 4 places; two CEO scores |
| Conflicting sources | Cockpit txs vs EH VE vs Marketing escrow vs D8 wallet |
| Hardcoded KPIs | EUR_RON 4.98; VAT 21% cockpit vs 19% marketing; commission 10%; profit 25%; EH revenue target 5000; email capture 100; LTV = GMV/clients |
| Stale values | BH/EH history only if page opened; `financial_insights` latest overwrite; CC recos `_id: latest` |
| Demo values | Cockpit/BH may include DEMO paid txs; War Room/EH exclude VE demo |
| Test values | `DEMO_STRIPE` path |
| Missing timestamps | various count-all-time fill rates |
| Missing attribution | Cockpit no demo flag; Lead Credits absent |
| Missing snapshots | no nightly BH job |
| Frontend-only calc | unit economics **copy** in App.js; flag `landing_show_unit_economics` |
| Independent calcs | VAT 21 vs 19; take 10 vs 5 |

---

# PART 14 — Financial Health Filter (exists as reusable parts — not as a filter)

**Do not implement.** Inventory only.

| Metric | Status | Reuse exactly |
|---|---|---|
| Revenue | PARTIAL | Pick SSOT: EH VE real **or** Cockpit txs **or** D8 confirm — **not all three** |
| Cost | **MISSING** | none |
| Margin | PARTIAL | Marketing `* 0.25` — **not reusable as truth** |
| Cash Flow | PARTIAL | Cockpit `cash_flow_30d` (paid txs) |
| Conversion | PARTIAL | BH conversii; Marketing funnel — different |
| LTV | PARTIAL | Marketing `estimated_ltv` (escrow/clients) |
| CAC | **MISSING** | — |
| Take Rate | **MISSING** as field | D8 5% is the **runtime** take; Cockpit 10% is **wrong reuse** |
| Cost-to-Serve | **MISSING** | — |
| Marketplace Liquidity | PARTIAL | fill_rate + Marketplace Intel + gaps |
| Churn | PARTIAL | Marketing + Pattern Hunter |
| Retention | PARTIAL | Marketing retention_rate |
| ARPU | **MISSING** (static ~64€ copy) | — |
| Revenue per Property | **MISSING** | — |
| Revenue per Specialist | PARTIAL | Marketing top-20 mean |
| Revenue per Project | **MISSING** | — |

A “Financial Health Filter” **does not exist**. Closest composers: `financial_cockpit` + War Room demo split + D8 confirm. They are **not wired**.

---

# PART 15 — Future integrated map (existing only)

| Stage | EXISTING COMPONENT | MISSING CONNECTION | DUPLICATE | UNKNOWN |
|---|---|---|---|---|
| OBSERVE | analytics, requests, txs, VE, oauth_health, smoke | no event bus for all money types | 3 health engines | live volume |
| MEASURE | BH, EH, Cockpit, Marketing, War Room | no SSOT | 4 revenues | — |
| ANALYZE | AI Insights, GI, MP Intel, Pattern Hunter | not feeding one brief | many insight collections | quality |
| CORRELATE | CEO Dashboard compose; Briefing compose | BH ≠ EH | two CEO pages | — |
| REPORT | 8+ weekly/daily emails | no 20-point CEO week | Monday pile-up | open rates |
| DECIDE | Briefing one_thing; CC Top 5 | no persist of Founder decision except toggle | — | — |
| APPROVE | Founder Gate page exists; Repair cron **skips** it | Repair L4 vs FG | — | — |
| ACT | Repair, Medic, auto_match, automation rules | Automation ≠ Repair | auto_match called from several jobs | overlap |
| VALIDATE | Repair score_after; EH history | no “did last week’s action work” | guardian re-audit | — |
| LEARN | `ai_outcomes`, learning_outcomes_daily | not closed to formulas | — | — |

**No new engine proposed.** Canonicalize **one score + one money definition**, then wire existing composers.

---

# PART 16 — Weekly CEO report (can infrastructure produce it?)

Do **not** generate the report. Coverage of the 20 asked sections:

| # | Section | Can existing mechanisms produce it? |
|---|---|---|
| 1 | What happened | **PARTIAL** — Exec Briefing 7d deltas; CC feed; no unified week |
| 2 | What improved | **PARTIAL** — EH/BH history **if** pages were opened; Repair deltas |
| 3 | What deteriorated | same | 
| 4 | Revenue | **PARTIAL / UNSAFE** — 4 definitions; demo leak in Cockpit |
| 5 | Costs | **NO** |
| 6 | Margin | **NO** (hardcoded 25% only) |
| 7 | Marketplace | **PARTIAL** — fill, intel, funnel; not offer/select/pay stages |
| 8 | Product | **PARTIAL** — EH product + Beta + guardians |
| 9 | Users | **YES** — several |
| 10 | Properties | **PARTIAL** — Beta/EH coverage |
| 11 | Specialists | **YES** — counts, verified, Medic |
| 12 | Conversion | **PARTIAL** — conflicting funnels |
| 13 | Security | **PARTIAL** — auth health, AI security; not in Exec Briefing body |
| 14 | Technical health | **PARTIAL** — smoke in EH; release gate email |
| 15 | Customer trust | **PARTIAL** — EH domain + reviews |
| 16 | AI/automation | **PARTIAL** — AI weekly + governance snapshot |
| 17 | Critical risks | **PARTIAL** — Briefing top_risks (on GET, not weekly email) |
| 18 | Recommended actions | **PARTIAL** — one_thing, CC recos, Council |
| 19 | Actions already taken | **PARTIAL** — `health_repair_runs`, ledger, autonomous_execution 24h (not week) |
| 20 | Validation of previous actions | **MISSING** as a weekly closed loop |

**Infrastructure cannot honestly produce a complete weekly CEO financial+ops report today** without mixing demo money and omitting cost/margin/CAC.

---

# PART 17 — Governance (who may OBSERVE / ANALYZE / RECOMMEND / APPROVE / EXECUTE)

| Actor | OBSERVE | ANALYZE | RECOMMEND | APPROVE | EXECUTE |
|---|---|---|---|---|---|
| **Founder / super-admin** | All CEO/EH/War Room/KC | yes | yes | Founder Gate, formula PATCH, DI apply | purge-demo, reconcile, enable rules |
| **Admin** | BH, Cockpit, CC, Automation, most intel | yes | yes | enable automation; toggle recos | Repair POST /run |
| **CFO role** | **no distinct role** | uses Cockpit if admin | — | — | — |
| **CPO / CTO** | **no distinct roles** | pages exist | — | — | — |
| **Operator** | Twin queues, ops | — | — | twin approve | twin validation |
| **AI Agent** | snapshots | Claude insights | yes | **must not** (registry ≠ gate) | L4 Repair, Medic, emails, auto_match |
| **Automation** | rule match | none | none | admin enable | 3 executors if enabled |

**Rules (existing series, restated):** AI must not redefine canonical truth; must not change governance without Founder Gate; must not turn UNKNOWN into FALSE.

**Risk:** Health Repair and Marketplace Medic **already execute without Founder Gate**. That is current runtime, not a proposal.

---

# PART 18 — Final verdict

### A. Existing systems
Many **parallel** admin products: BH, EH, Cockpit, War Room, two CEO pages, Control Tower, Command Center, Repair, Automation (3 rules), Orchestrator, Autonomy, 70+ crons, 8+ reports.

### B. Existing financial health
Cockpit (txs+escrow+HH MRR) + EH real VE + Marketing GMV + War Room split. **No cost, no real margin, no Lead Credits, no wallet, no D8 take.**

### C. Existing business health
8 heuristic department scores + Marketing KPI pack + Beta funnel. History on-demand.

### D. Existing product health
EH Product (twin/DNA coverage) + Beta + guardians + AI Brain **code map** + Design Audit/Intelligence. Not one score.

### E. Existing analytics
First-party `analytics_*`, Growth Intel, Lead Intel, Marketing Intel, A/B `ab_events`, attribution attach on BH.

### F. Existing automation
Automation Center (3 disabled templates) ≠ Orchestrator playbooks ≠ Repair ≠ Self-Driving.

### G. Existing AI ecosystem
Large. Most scans **recommend**. Proven autonomous **writes**: Repair (bounded), Medic, retries, emails, auto_match, some flag/todo execution.

### H. Existing executive reporting
CEO Dashboard (BH money) + CEO Briefing (EH money) + Control Tower + War Room.

### I. Existing weekly reporting
Multiple Monday emails; **no** 20-section CEO pack.

### J. Existing repair/self-healing
Real detect→repair→validate cron. Semi/bounded automated. No rollback.

### K. Existing metric lineage
Observe → several measures → several UIs. **Breaks before one decision/action/validation chain.**

### L. Existing cross-system connections
Some **imports** (CEO→BH/Cockpit/CC; Briefing→EH/War Room; Repair→EH; CC→BH). Most namesake pairs **PARTIAL** or **DOCUMENTED ONLY**.

### M. Duplicate mechanisms
3 health scores; 4 revenues; 2 CEO scores; 8 Monday reports; 3 automation stacks; 2 “Product Intelligence”; 2 “audit” (UX vs property); House Health vs Business Health.

### N. Broken connections
Cockpit 10% ≠ D8 5%; Cockpit/BH unfiltered demo txs ≠ EH/War Room real VE; Automation ≠ Health; Lead Credits/wallet absent from finance; BH history not scheduled.

### O. Missing capabilities
Cost, CAC, ARPU, take_rate field, cost-to-serve, revenue/property, weekly action validation, refunds/payouts KPI, MP stage conversion.

### P. Data quality risks
Hardcoded FX/VAT/margin/targets; latest-doc overwrite; lifetime fill rate; demo leak.

### Q. Financial risks
Board may read DEMO as revenue; take-rate overstated 10 vs 5; 25% “profit”; MRR from one-shot HH treated as subscription ARR.

### R. Product risks
Nav implies one OS; Founder sees two different “health” numbers the same morning.

### S. Architecture risks
New Health Filter/engine would be a **fifth** composer. Overlapping crons call `auto_match` and hunter independently.

### T. Governance risks
L4 Repair/Medic execute without Founder Gate; formula registry can change EH meaning; AI registry is not enforcement.

### U. Security risks
Medic auto-suspend; purge-demo destructive; unlimited request notify (D9.5); Control Tower reconcile writes `transactions`.

---

## What to do with what exists (no build)

1. **PĂSTRAT**  
   War Room demo/real split; EH `real_revenue` filter; D8 confirm as **actual** marketplace take; Repair run log; Exec Briefing WoW email; Founder Gate + formula audit; Design Intelligence apply-gate; Automation rules default **off**.

2. **CONECTAT** (conceptually, later Founder-approved)  
   One money feed into both CEO surfaces; Lead Credits + wallet as **non-revenue** lines; D8 5% instead of cockpit 10%; BH nightly snapshot **or** stop claiming history; drain `automation_emails`.

3. **CONSOLIDAT**  
   Pick **one** company score (BH **or** EH) for “the number”; pick **one** weekly email outline; treat Automation/Orchestrator/Repair as **three tools**, name them as such in nav.

4. **REPARAT**  
   Demo filter on Cockpit/BH if those stay money-facing; VAT 21 vs 19; lifetime fill vs active fill.

5. **DEPRECIAT** (recommendation only — do not delete now)  
   Cockpit `released_escrow_take_est` 10%; Marketing `profit_estimated`; App.js ARPU/CAC copy as if measured; treating AI Brain map as Product Health.

6. **Lipsește cu adevărat**  
   Cost ledger; CAC; closed-loop weekly validation; single revenue SSOT; client verification (D9); MP stage conversion; Financial Health Filter as a product.

---

# Commercial & financial lens (no invented numbers)

| Mechanism | Who pays | For what | When | PropManage cost | Specialist cost | Margin | Cash-flow | Liquidity | Conversion / LTV | Recurring vs txn vs service | Take | Cost-to-serve | Abuse | Uncovered promise |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| HH MRR in Cockpit | Client | software gates | one-shot +30d | UNKNOWN | 0 | UNKNOWN | if paid | n/a | UNKNOWN | recurring **if** renew | n/a | UNKNOWN | trial advertised not granted | trial / CSM |
| Cockpit “revenue” | mixed | txs marked paid | checkout | UNKNOWN | — | UNKNOWN | **DEMO possible** | — | UNKNOWN | mixed | **10% fake** | UNKNOWN | demo counted | “complete money view” |
| EH real_revenue | VE buyer | audit/twin RON | VE paid | UNKNOWN | operator | UNKNOWN | real if !demo | — | vs 5000 target | service | VE commission | UNKNOWN | — | target arbitrary |
| D8 job | Client escrow / specialist haircut | job | confirm | Stripe UNKNOWN | 5% + credits | UNKNOWN | wallet not cash-out | posting free | UNKNOWN | transaction | **5%** | notify-all | spam | unpaid `/start` |
| Lead Credits | Specialist | participate | offer/accept | grant 135 | 45 | UNKNOWN | inventory | helps specialists ration | UNKNOWN | not revenue | n/a | — | — | **invisible to CFO UI** |
| Repair auto_match | platform | fill | cron | compute | attention | n/a | n/a | may force matches | UNKNOWN | n/a | n/a | UNKNOWN | bad matches | “self-healing” |

---

# Recommended next audit (not implementation)

**Money SSOT fact-check (read-only):** for a target environment, count rows in `payment_transactions` (paid, demo vs not), `verified_estate_orders` (paid demo vs real), `hh_subscriptions` active, `wallets`, `lead_credits`, and confirm `/confirm` 0.95 — **without** changing anything. That tells which of the four “revenues” is non-zero.

**STOP.** No implementation performed.
