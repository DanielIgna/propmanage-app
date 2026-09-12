# MASTER_PLATFORM_STATE — 2026-07-31

> **Status oficial**: Single Source of Truth pentru starea reală de implementare a PropManage.
> **Regulă de aur**: dacă apare diferență între cod și documentație, **codul are prioritate** și acest audit reflectă codul.
> **Frecvență update**: la fiecare audit major. Fiecare versiune se păstrează sub `/app/memory/audits/MASTER_PLATFORM_STATE_YYYY-MM-DD.md`. Copia canonică `MASTER_PLATFORM_STATE.md` reflectă întotdeauna cea mai recentă.
> **Comparabil**: fiecare secțiune are metric-uri numerice pentru diff vs versiunile anterioare.

---

## Relații cu alte documente oficiale (Dependency Map)

| Document | Rol | Relație cu acest audit |
|---|---|---|
| `/app/memory/PRD.md` | Product Requirements (ce vrem) | AUDIT verifică conformitatea implementării cu PRD. |
| `/app/memory/PRODUCT_BLUEPRINT.md` | Arhitectura de produs | AUDIT raportează procentul de conformitate cu Blueprint. |
| `/app/memory/product/02_INFORMATION_ARCHITECTURE.md` | IA + Dashboard OS | AUDIT verifică prezența dashboard-urilor definite. |
| `/app/memory/board/ROADMAP_V2.md` | Roadmap oficial | AUDIT raportează implementation progress vs milestones. |
| `Sprint 1 Consolidation Report` (în chat, va migra aici) | Discovery arhitectural | AUDIT extinde acel raport cu cifre exacte. |
| `Sprint 1.5 Ownership Matrix` (în chat, va migra aici) | Cine deține ce | AUDIT confirmă owner-ul fiecărui modul. |
| `/app/memory/metrics/ENTERPRISE_HEALTH.md` | Formule health | AUDIT raportează scorurile actuale. |
| `/app/memory/ENTERPRISE_STANDARDS.md` | Standarde de cod/arhitectură | AUDIT identifică zone de non-conformitate. |
| Knowledge Center (`/api/founder/knowledge`) | Consumatorul acestui doc în Admin | Categorie `Platform Audits` — vezi mai jos. |

**Rol SSOT**: Acest document este singurul care declară `implementation_status = TRUE` pentru un modul. Orice alt doc care afirmă „implementat" fără corespondent aici este considerat aspirational.

---

## 1. Enterprise Inventory

**Cifre absolute (audit 2026-07-31):**

| Categorie | Count |
|---|---|
| Backend route modules (`/app/backend/routes/*.py`) | **172** |
| Backend engines & services la root (`/app/backend/*.py`) | **63** |
| Frontend pages (`.jsx`/`.js` în `/pages`) | **222** |
| Admin pages (`/pages/admin/`) | **127** |
| React admin routes în `App.js` | **79** |
| MongoDB collections active (grep `db.<name>`) | **~120** unice |
| Scheduled jobs (`AsyncIOScheduler` în `server.py`) | **~15** |
| API prefixes major | `/api/admin/*`, `/api/founder/*`, `/api/ai-brain/*`, `/api/ux/*`, `/api/*` (public/user) |

**Statusul modulelor top-level** (categorii):

| Cluster | Modules count | Status implementare |
|---|---|---|
| Identity & tenancy | 4 (auth, users, admin_accounts, impersonation) | ✅ COMPLET |
| Health & metrics scoring | 3 sisteme paralele (business_health, enterprise_health, autonomy) | ✅ IMPLEMENTAT · 🟡 DRIFT (duplicat) |
| AI Governance & Intelligence | 13 module (ai_brain, ai_governance, ai_pm, ai_dev_team, ai_control, ai_activity, ai_search, ai_security, ai_insights, ai_weekly_briefing, ai.py, kg, learning_engine, agent_journal) | ✅ IMPLEMENTAT · 🟡 fără registry unificat |
| Autonomy | 6 (engine, autopilot, self_driving, snapshots, alerts, founder_digest) + roadmap_advisor | ✅ COMPLET |
| Orchestration | 4 (engine, playbooks, governance, playbooks_sprint3) + retry_queue | ✅ COMPLET |
| Executive Dashboards | 9 pagini (CEO, ControlTower, CommandCenter, Ops, CEOBriefing, MorningBriefing, EnterpriseExplorer, FinancialCockpit, FirstRevenueWarRoom) | ✅ IMPLEMENTAT · 🔴 DUPLICAT major |
| Knowledge & Memory | 5 (knowledge_center, kg, ai_memories, agent_journal, learning_engine) | ✅ IMPLEMENTAT · 🟡 DRIFT graph |
| Digital Twin | 5 collections (`digital_twin_projects/models/plans/pins/twins`) + `twin_schedule` | ✅ IMPLEMENTAT · 🟡 storage fragmentat |
| Marketplace | 6 (requests, offers, partners, leads, gaps, reviews) | ✅ COMPLET |
| Property & Estate | 8 (properties, buildings, portfolio, documents, intelligence, verified_estate_*, house_health_*) | ✅ COMPLET |
| Payments & Finance | 5 (transactions, payment_transactions, pb_ledger, wallet, escrow, stripe_*) | ✅ COMPLET |
| Growth / Marketing / Revenue Intelligence | 9 module | ✅ IMPLEMENTAT · 🔴 DUPLICAT major |
| QA / Content / Maintenance | 12+ module (qa_playbook, qa_maintenance, content_audit, term_audit, smoketest, content_audit, journey_guardian, health_repair, repair_center, product_guardian, architecture_guardian, design_audit) | ✅ COMPLET |
| Content & SEO | service_pages + service_content_* + seo | ✅ COMPLET (recent fixed) |
| Storage | storage_service + storage_client + storage_configs + kyc | ✅ COMPLET |
| Event Bus & Comms | event_bus + notifications + concierge_messages | ✅ IMPLEMENTAT · 🟡 fără catalog consumers |
| Nav & UX | adaptive_ux + onboarding + ux_lab + admin_tour | ✅ COMPLET |

---

## 2. Enterprise Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FOUNDER / ADMIN UI                              │
│  Knowledge Center │ CEO Dashboard │ Control Tower │ Command Center │ ... │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │ HTTP /api/founder/* /api/admin/*
┌──────────────────────────────▼──────────────────────────────────────────┐
│                       EXECUTIVE LAYER (Consumers)                        │
│  ceo_dashboard · control_tower · command_center · operations · ceo_brief │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
        ┌──────────────────────┴─────────────────────┐
        │                                            │
┌───────▼────────┐  ┌─────────────────┐  ┌──────────▼──────────┐
│ HEALTH SCORING │  │  AI GOVERNANCE  │  │ AUTONOMY & ORCHEST. │
│ business_health│  │  ai_governance  │  │  autonomy/engine    │
│ enterprise_hlth│  │  ai_brain       │  │  orchestrator/eng.  │
│ autonomy/score │  │  ai_pm          │  │  journey_guardian   │
└───────┬────────┘  └────────┬────────┘  └──────────┬──────────┘
        │                    │                       │
        ▼                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PRODUCT DOMAINS (Owners of data)                 │
│                                                                       │
│  Marketplace │ Digital Twin │ Verified Estate │ House Health │ Wallet │
│  Payments    │ Properties   │ Growth Intel    │ Marketing    │ Leads  │
└─────────────────────┬───────────────────────────┬───────────────────┘
                      │                           │
              ┌───────▼────────┐          ┌──────▼──────┐
              │   MONGODB      │          │  EVENT BUS  │
              │ 120+ collections│         │ pub-sub     │
              └────────────────┘          └─────────────┘
```

**Regula**: fluxul e **bottom → top**. Data se calculează în Product Domains, se agreghează în Health Scoring/AI Governance/Autonomy, se afișează în Executive Layer. Retur, doar prin Event Bus (write-back controlat).

---

## 3. Knowledge Inventory

Documente `/app/memory/*.md` — **33 fișiere root + subfoldere structurate**:

| Categorie | Fișiere reprezentative |
|---|---|
| **Constitution** | `constitution/` (folder), `CONSTITUTIA_*` |
| **Board Directives & Resolutions** | `board/BOARD_DIRECTIVES.md`, `BOARD_LAWS.md`, `BOARD_RESOLUTIONS.md`, `BOARD_CHARTERS.md` |
| **Strategy** | `board/GRAND_STRATEGY_2035.md`, `ROADMAP_V2.md`, `EXPONENTIAL_GROWTH_ENGINE.md`, `ENTERPRISE_EVOLUTION_ENGINE.md` |
| **Product Blueprint** | `product/00_PRODUCT_CONSTITUTION.md`, `01_PRODUCT_VISION.md`, `02_INFORMATION_ARCHITECTURE.md`, `03_DASHBOARD_OS.md`, `04_USER_JOURNEYS.md` |
| **Metrics** | `metrics/ENTERPRISE_HEALTH.md`, `ENTERPRISE_SCORE.md`, `ENTERPRISE_MATURITY_INDEX.md`, `NORTH_STAR_TRUSTED_PROPERTIES.md` |
| **Architecture** | `AI_CORE_ARCHITECTURE.md`, `DESIGN_SYSTEM.md`, `ENTERPRISE_STANDARDS.md`, `ENTERPRISE_PRINCIPLES.md`, `ENTERPRISE_PLAYBOOKS.md` |
| **Governance** | `governance/`, `GOVERNANCE_HIERARCHY.md`, `ENTERPRISE_COUNCIL_GOVERNANCE.md`, `ENTERPRISE_EVOLUTION_CONTRACT.md` |
| **Audits** | `PLATFORM_AUDIT_2026.md`, `AUDIT_AI_OS_2026.md`, `GI_COHERENCE_REVIEW.md` |
| **Memory & Rules** | `MEMORY_RULES.md`, `PROTOCOL_DE_LUCRU.md`, `INDEX.md`, `LEARNINGS.md`, `BUGS.md` |
| **Product Domain Docs** | `PROPERTY_DNA.md`, `GI5_BUSINESS_OS.md`, `GI5P_PROPERTY_INTELLIGENCE.md`, `CONSTRUCTION_INTELLIGENCE_ROADMAP.md`, `VALUE_LOOP.md`, `UX_REDESIGN_CLIENT_V2_FAZA1.md` |
| **Prompts** | `prompts/` (system prompts pentru AI operations) |
| **Test Credentials** | `test_credentials.md` |

**Total docs**: ~50 fișiere + subfoldere.

**Knowledge Coverage estimat**: 75% — există doc pentru majoritatea zonelor strategice, dar 25% din module tehnice (route-uri specifice, engine-uri de nișă) sunt subdocumentate.

---

## 4. Engines Inventory

**Backend engines (rulate ca servicii/module la root `/app/backend/`):**

| Engine | File | Purpose | Status | Owner (per Ownership Matrix) |
|---|---|---|---|---|
| Autonomy Engine | `autonomy/engine.py` | Scor 6 dimensiuni autonomie | ✅ Live | Autonomy Engine SSOT |
| Autopilot | `autonomy/autopilot.py` | Auto-actions on low autonomy | ✅ Live (03:30 daily) | Autonomy |
| Self-Driving Roadmap | `autonomy/self_driving.py` + `roadmap_advisor.py` | Auto-generate roadmap items | ✅ Live | Autonomy |
| Founder Digest | `autonomy/founder_digest.py` | Daily 19:00 digest | ✅ Live | Autonomy |
| Orchestrator Engine | `orchestrator/engine.py` | Cross-module workflows | ✅ Live | Orchestrator |
| Playbooks | `orchestrator/playbooks.py` + `playbooks_sprint3.py` | Predefined orchestration flows | ✅ Live | Orchestrator |
| Orchestrator Governance | `orchestrator/governance.py` | Guardrails pentru playbook-uri | ✅ Live | Orchestrator |
| Journey Guardian | `journey_guardian.py` | Reguli journey user | ✅ Live | Journey Guardian SSOT |
| Health Repair | `health_repair.py` | Auto-fix journey issues | ✅ Live | Health Repair |
| Product Guardian | `product_guardian.py` | Product rules enforcement | ✅ Live | Product Guardian |
| Architecture Guardian | `architecture_guardian.py` | Architecture rules | ✅ Live | Architecture Guardian |
| Growth Intelligence | `growth_intelligence.py` | Growth metrics | ✅ Live | Growth (canonic) |
| Marketing Intelligence | `marketing_intelligence.py` | AI marketing recs | ✅ Live | 🟡 candidat merge |
| Marketing Growth | `marketing_growth.py` | Funnel data | ✅ Live | 🟡 candidat merge |
| Analytics Growth | `analytics_growth.py` | Session/event analytics | ✅ Live | 🟡 candidat merge |
| Revenue Hunter | `revenue_hunter.py` | Revenue opportunities | ✅ Live | Revenue |
| First Revenue Service | `first_revenue.py` | Pre-PMF war room | ✅ Live | Growth |
| Lead Intelligence | `lead_intelligence.py` | Lead scoring & routing | ✅ Live | Lead |
| Marketplace Intel | `marketplace_intel.py` | Marketplace insights | ✅ Live | Marketplace |
| Property Intelligence | `property_intelligence.py` | Per-property AI | ✅ Live | Property |
| Learning Engine | `learning_engine.py` | Pattern extraction din decision ledger | ✅ Live | Learning |
| Agent Journal | `agent_journal.py` | Audit journal AI agents | ✅ Live | AI Journal |
| Event Bus | `event_bus.py` | Pub-sub cross-module | ✅ Live · 🟡 fără catalog | Event Bus |
| Truth Engine | (referit în docs, funcționalitate distribuită în `enterprise_health` + `ai_governance/audit-trail`) | Validare adevăr platform-wide | 🟡 PARȚIAL implementat (fără endpoint dedicat) | — |
| Decision Engine | (funcționalitate distribuită în `ai_governance` + `orchestrator/governance`) | Deciziile automate | 🟡 PARȚIAL (fragmentat pe 3 ledgers) | — |
| Evolution Council | Referit în docs `board/*` | Council-based evolution | ❌ **DOCUMENTAT DAR NU ESTE COD** — doar semantic în Board Directives |

**Note critice**:
- **Truth Engine** — nu există fișier dedicat; funcționalitatea e distribuită. **Trebuie declarat oficial** dacă e OWNER `enterprise_health.formulas_registry` sau alt modul.
- **Decision Engine** — la fel, distribuit. **Trebuie declarat oficial** înainte de consolidare.
- **Evolution Council** — nume folosit în docs strategice, dar nu există modul cod. **Aspirational only.**

---

## 5. API Inventory

**Prefixes majore active** (extras din `routes/*.py`):

| Prefix | Modules count | Consumer principal |
|---|---|---|
| `/api/admin/*` | ~110 modules | Admin frontend |
| `/api/founder/*` | 1 (`knowledge_center`) | Founder-only UI |
| `/api/ai-brain/*` (user-facing) | 1 (secondary router in `ai_brain.py`) | Client copilot context |
| `/api/ux/*` | 2 (`adaptive_ux` + admin sub-router) | Frontend UX |
| `/api/*` (public/user) | ~55 modules | Client + specialist + public |

**Endpoint count estimat**: ~1200-1500 endpoints (mediana ~7-10 per module × 172 modules).

**Autentificare & scoping**:
- Toate `/api/*` trec prin `deps.get_current_user` (soft-required per route).
- Toate cu date de tenant trec prin `middleware_scope.py`.
- Rate limiting: existent pe endpoint-uri sensibile (auth login, verify email).

**Documentare API**: FastAPI auto-generează `/docs` (Swagger) — expus doar în dev.

---

## 6. Database Inventory

**MongoDB — 120+ collections active**, top folosite:

| Collection | Usages în cod | Rol |
|---|---|---|
| `users` | 562 | Identity SSOT |
| `requests` | 308 | Marketplace requests |
| `properties` | 130 | Property SSOT |
| `leads` | 45 | Growth funnel |
| `admin_ai_findings` | 43 | AI findings |
| `transactions` | 42 | Raw Stripe |
| `disputes` | 40 | Support |
| `digital_twin_projects` | 40 | Twin SSOT |
| `projects` | 38 | General projects |
| `twins` | 34 | 🟠 LEGACY |
| `digital_twin_pins` | 34 | Twin annotations |
| `verified_estate_listings` | 33 | Verified estate |
| `reviews` | 33 | Ratings SSOT |
| `property_documents` | 32 | Vault |
| `recommendations` | 31 | AI recs |
| `verified_estate_orders` | 29 | Order flow |
| `revenue_opportunities` | 28 | Revenue Hunter |
| `qa_sessions` | 28 | QA runs |
| `digital_twin_models` | 28 | 🟡 candidat merge |
| `payment_transactions` | 27 | Payment state machine |
| `notifications` | 27 | Notifications |
| `marketplace_partners` | 27 | Specialists |
| `app_settings` | 27 | Platform config |
| `ai_brain_graph_edges` | 27 | 🟡 duplicat cu kg |
| `onboarding_emails` | 26 | Onboarding |
| `ai_decision_ledger` | 24 | AI decisions SSOT |
| `hh_evaluations` | 23 | House Health |
| `concierge_messages` | 23 | AI chat |
| `city_partners` | 23 | City-level partners |
| `digital_twin_plans` | 21 | 🟡 candidat merge |
| `city_partner_leads` | 21 | City leads |
| `orchestrator_ledger` | 20 | Orchestrator SSOT |
| `hh_subscriptions` | 19 | HH subscriptions |
| `community_campaigns` | 19 | Marketing |
| `ai_brain_processes` | 19 | AI processes |
| `platform_config` | 18 | Feature flags |
| `pb_ledger` | 18 | Business ledger SSOT |
| `autonomy_snapshots` | 18 | Autonomy history |
| `analytics_sessions` | 18 | Analytics |
| `ai_memories` | 18 | AI memory store |
| `admin_ai_repair_suggestions` | 18 | Repair |
| `orchestrator_retry_queue` | 17 | Retry state |
| ... (80+ collections cu <15 usages) | | |

**Indexes**: definite parțial în `migrations/create_indexes.py`.
**Retention**: NU există retention policy formală (TD7 identificat).

---

## 7. Dashboard Inventory

**Frontend admin dashboards** (79 rute admin, 127 pagini admin):

**Executive/Overview:**
- `AdminOverview` — general overview
- `CEODashboardPage` — strategic view
- `CeoBriefingPage` — text briefing
- `ControlTowerPage` — operational
- `CommandCenterPage` — daily feed + top 5
- `OperationsCenter` — COO scope până la PMF
- `MorningBriefingPage` — 8:00 briefing
- `EnterpriseExplorerPage` — deep-dive KPI
- `FirstRevenueWarRoom` — pre-PMF
- `FinancialCockpitPage` — financial-only

**Health & Autonomy:**
- `BusinessHealthPage`
- `EnterpriseHealthPage`
- `AutonomyEnginePage`
- `AutonomyOrchestratorPage`
- `EnterpriseMaturityPage`

**AI & Governance:**
- `AIBrainPage`
- `AIControlCenterPage`
- `AISecurityCenterPage`
- `AutomationCenterPage`
- `AIActivityStream`
- `AIAdminTour`
- `AIProductManagerPage`
- `AIDevTeamPage`
- `AIGovernancePage`

**Domain:**
- `KnowledgeCenter`
- `RepairCenter`
- `NotificationCenter`
- `StrategicPartnersDashboard`
- `MarketplaceAdmin*` (multiple)
- `DigitalTwinAdmin*`
- `PropertyAdmin*`
- `HouseHealthAdmin*`
- `PaymentsAdmin*`
- `SpecialistsAdmin*`
- `WalletAdmin*`
- `EscrowAdmin*`

**QA & Content:**
- `QAPlaybookPage`
- `SmokeTestPage`
- `ContentAuditPage`
- `TermAuditPage`
- `DesignAuditPage`

**Growth & Marketing:**
- Marketing dashboards
- Community campaigns
- Referral tracking

**Client-facing dashboards** (`/pages/client*` + `/pages/clientv2/`):
- `ClientDashboardV2` (v2 in progress)
- `PropertyHubV2`
- `HomeV2`
- `JobsV2`
- `RequestWizard`
- `DocumentVault` (recent fixed pentru mobile)
- Public landing pages: `InteriorDesignLanding`, `ArhitecturaLanding`, `ExteriorLanding`, `HouseHealthLanding`, etc.

**Total dashboards estimate**: ~40 admin dashboards + ~15 client dashboards + ~20 public/landing pages = **~75 vederi principale**.

---

## 8. Automation Inventory

**Scheduled jobs (AsyncIOScheduler în `server.py`)**:

| Job | Frequency | Purpose |
|---|---|---|
| Founder Digest | Daily 19:00 (Europe/Bucharest) | Digest email pentru founder |
| Autonomy Snapshot | Daily | Snapshot al scorurilor autonomy |
| Autopilot Cycle | Daily 03:30 | Auto-actions pentru autonomy < target |
| Auto-Tune | Periodic | Tune parameters |
| Orchestrator Retry Tick | Continuous | Process retry queue |
| Marketplace Medic Cron | Periodic | Health check marketplace |
| Pattern Hunter | Periodic | Extract patterns din data |
| Finance Reconciler | Periodic | Reconciliere pb_ledger vs transactions |
| Roadmap Advisor | Periodic | Auto-suggest roadmap items |
| Watchdog | Continuous | Health check services |
| Decision Review Cron | Periodic | Review recent AI decisions |
| Twin Schedules Hydrate | On startup | Hydrate scheduled twin actions |
| Lead Follow-up | Periodic | Auto-follow-up leads |

**Automation modules (non-scheduled)**:
- `orchestrator/playbooks.py` — event-triggered workflows
- `journey_guardian.py` — trigger on route access
- `event_bus.py` — pub-sub
- `notifications.py` — email + in-app

---

## 9. AI Inventory

**AI Agents (moduluri care iau decizii AI):**

| Agent | Module | Rol |
|---|---|---|
| AI Copilot | `assistant_widget` + backend routes | Client-facing chat AI |
| AI PM | `routes/ai_pm.py` | Feature breakdown → todos |
| AI Dev Team | `routes/ai_dev_team.py` | Automated dev tasks |
| AI Governance | `routes/ai_governance.py` + `ai_governance/agent_registry.py` | Meta-agent (guvernează pe ceilalți) |
| AI Brain | `routes/ai_brain.py` + `ai_brain/` | Discovery + processes + certification |
| AI Control | `routes/ai_control.py` | Kill-switch + pause |
| AI Search | `routes/ai_search.py` | Semantic search |
| AI Security | `routes/ai_security.py` | Anomaly detection |
| AI Insights | `routes/ai_insights.py` | Periodic insights |
| AI Weekly Briefing | `routes/ai_weekly_briefing.py` | Weekly digest |
| AI Activity Stream | `routes/ai_activity.py` | Real-time feed |
| Autonomy Autopilot | `autonomy/autopilot.py` | Auto-actions on low autonomy |
| Self-Driving Roadmap | `autonomy/self_driving.py` | Auto-generate roadmap |
| Founder Digest AI | `autonomy/founder_digest.py` | Daily summary |
| Learning Engine | `learning_engine.py` | Extract patterns din decisions |
| Concierge | `routes/concierge.py` | AI concierge messages |

**AI Providers utilizați** (via `emergentintegrations`):
- Claude Sonnet 4.5 / Opus (via Emergent LLM Key) — text generation
- Gemini Nano Banana — image generation (dacă e activ)
- OpenAI GPT — fallback text

**AI Costs tracking**: `ai_agent_usage_daily` collection + `/api/admin/ai-governance/costs`.

---

## 10. Dependency Inventory

**Backend Python deps**: FastAPI, motor (async Mongo), pydantic, APScheduler, resend, stripe, emergentintegrations, pytz, python-jose, passlib.
**Frontend Node deps**: React 18/19, react-router-dom v7, shadcn/ui, tailwindcss, lucide-react, sonner, axios, framer-motion.

**Cross-module dependencies critice**:

```
autonomy/engine.py ─────► autonomy_snapshots (write)
                    │
                    └───► ai_decision_ledger (write via autopilot)

business_health.py ─────► users, requests, transactions, disputes, marketplace_partners,
                          verified_estate_orders, payments (read)

enterprise_health.py ───► ~28 metrici (majoritatea collections)
                    │
                    └───► formulas_registry (own)

orchestrator/engine.py ─► orchestrator_ledger (write)
                    │
                    └───► orchestrator_retry_queue (r/w)
                    │
                    └───► event_bus (publish)

journey_guardian.py ────► component_registry (read hard-coded)
                    │
                    └───► health_repair (invoke)

knowledge_center.py ────► /app/memory/ (filesystem read-only)

ai_governance/registry ─► ai_decision_ledger, ai_agent_usage_daily
                    │
                    └───► ai_governance_audit_log

event_bus.py ───────────► many consumers (fără catalog — HR3)
```

---

## 11. Duplicate Analysis

Confirmate din Sprint 1:

| # | Zonă duplicată | Impact |
|---|---|---|
| D1 | **3 sisteme health scoring paralele** (business_health, enterprise_health, autonomy) | HIGH — divergence risk |
| D2 | **6+ executive dashboards** (CEO, ControlTower, CommandCenter, CEOBriefing, MorningBriefing, EnterpriseExplorer) | HIGH — cognitive load |
| D3 | **3 decision ledgers** (`ai_decision_ledger`, `orchestrator_ledger`, `admin_audit_log`) | HIGH — audit fragmentation |
| D4 | **10 AI modules** fără registry unificat | MEDIUM |
| D5 | **5 twin collections** (`digital_twin_projects/models/plans/pins/twins`) | MEDIUM |
| D6 | **2 knowledge graphs** (`kg` + `ai_brain/graph`) | MEDIUM |
| D7 | **3 memory stores** (`ai_memories`, `knowledge_center`, `agent_journal`) | MEDIUM |
| D8 | **9 growth/marketing/intelligence modules** cu overlap major | HIGH — un metric are 3 surse |
| D9 | Duplicate helpers `_pct`, `_clamp`, `_band` în 3+ files | LOW — refactor trivial (LR1) |

---

## 12. Dead Code Analysis

Suspecte candidate (necesită confirmare cu logs de acces):

- Collection `twins` (LEGACY) — datele ar putea fi migrate în `digital_twin_projects` și collection dropped.
- `enable_twin_orchestrator` field — deja marcat în `test_iter154_client_v2_regression.py` ca stale.
- Pagini admin cu <10 accesuri în 30 zile — nu există audit acces per admin page (TD6).
- Route-uri cu 0 consumers frontend — nu există audit endpoint-vs-frontend-imports (candidat sprint viitor).
- Fișiere test `test_iter*.py` per iterație (multe iterații completate) — pot fi arhivate.

---

## 13. Missing Architecture

Componente arhitecturale absente sau incomplete:

| Missing | Impact | Prioritate |
|---|---|---|
| **Unified Metrics Service** | Fiecare dashboard calculează propriu → divergence | P0 (M1 Sprint 2) |
| **Unified Decision Ledger** | Audit fragmentat pe 3 stores | P0 (M3 Sprint 2) |
| **AI Agent Registry consolidat** | Ai_brain, ai_pm, ai_dev_team nu se auto-înregistrează | P1 (M4 Sprint 2) |
| **Event Bus catalog de consumers** | Nu știi cine ascultă ce → refactor orb | P1 |
| **Executive Layer unificat** (`ExecutiveHub`) | 6+ dashboards fragmentate | P2 (M2 Sprint 4) |
| **Twin storage consolidat** | 5 collections legacy overlap | P2 (M5) |
| **Growth/Marketing/Intel consolidat** | 9 modules fragmentate | P2 (M6) |
| **Knowledge Layer consolidat** | knowledge_center + kg + ai_brain/graph = 3 grafuri paralele | P2 (M7) |
| **Truth Engine oficial** | Distribuit, fără endpoint dedicat | P1 |
| **Evolution Council în cod** | Documentat în board, dar nu există modul | P3 |
| **Retention Policy pentru MongoDB** | ~30 collections cu <100 docs (posibil test data) | P2 |
| **Master routing map** | 172 route files fără index navigabil | P1 |

---

## 14. Reusable Components

Componente/pattern-uri identificate ca reutilizabile:

| Component | Locație | Reuse potențial |
|---|---|---|
| `PyObjectId` + `BaseDocument` (MongoDB) | `models/base.py` | ✅ deja folosit consistent |
| `deps.get_current_user` | `deps.py` | ✅ SSOT auth |
| `middleware_scope.py` (tenancy) | root | ✅ deja aplicat |
| `_pct`, `_clamp`, `_band` (score math) | duplicat în 3 files | 🟡 candidat consolidare (LR1) |
| `Section` component (frontend) | `InteriorDesignLanding.jsx` (local) | 🟡 candidat mutare în `components/ui/` |
| `ServiceDetailModal` (ecosystem) | `components/ecosystem/` | ✅ deja SSOT pentru modal ecosistem |
| `EcosystemFlow` | `components/ecosystem/` | ✅ SSOT canonical flow |
| `use*` React hooks (custom) | `/frontend/src/hooks/` | Various |
| Shadcn UI | `/frontend/src/components/ui/` | ✅ SSOT UI primitives |

---

## 15. Monetization Components

Situația reală a componentelor de monetizare:

| Component | Status | Owner | Notă |
|---|---|---|---|
| **Subscription** | ✅ IMPLEMENTAT | `hh_subscriptions` + `routes/subscriptions.py` (House Health subscription) | Testat pe HH; extensibil |
| **Marketplace fees / commission** | ✅ IMPLEMENTAT | `routes/marketplace.py` + `pb_ledger` | Commission % configurable |
| **Wallet** | ✅ IMPLEMENTAT | `routes/wallet.py` | Balance + hold + release specialist |
| **Payments — Stripe** | ✅ INTEGRAT | `routes/stripe_*` | Test mode; **live claim pending** (P1) |
| **Escrow** | ✅ IMPLEMENTAT | `routes/escrow.py` + `payment_transactions` state | Freeze/release live |
| **Digital Twin** — pricing | ✅ IMPLEMENTAT | `verified_estate.py::PRICE_AUDIT_RON=2400`, `PRICE_TWIN_RON` | Production has 2400 audit / 15000 twin |
| **House Health** — pricing | ✅ IMPLEMENTAT | `hh_plans` + `hh_subscriptions` | Multiple tiers |
| **Verified Estate Orders** | ✅ IMPLEMENTAT | `verified_estate_orders` collection | Stripe payment flow live |
| **Lead Management** | ✅ IMPLEMENTAT | `leads` + `lead_intelligence.py` | Growth funnel activ |
| **Deals / Offers** | ✅ IMPLEMENTAT | `marketplace_offers` collection | Offer management activ |
| **Referral** | 🟡 PARȚIAL | Există `referrals` colecție, nu am confirmat UI activ | Verificare necesară |
| **Concept Design Rezidențial** — pricing (2.200 lei/cameră) | ✅ AFIȘAT (recent fixed) | `service_content_design.py` v8 | Frontend nou implementat |

---

## 16. Product Readiness

**Ready for production**:
- ✅ Core marketplace flow (request → match → offer → deal → dispute if needed)
- ✅ Digital Twin creation + payments (Verified Estate flow)
- ✅ House Health subscription tiers + AI evaluations
- ✅ Property Vault (mobile fixed recently)
- ✅ Client dashboards V2 (5 pagini)
- ✅ Multi-tenancy + admin impersonation
- ✅ Resend email integration (verified DNS + operational)
- ✅ Autonomy Engine + Autopilot + Founder Digest (live schedule)
- ✅ Journey Guardian + Health Repair
- ✅ SEO landing pages (Interior/Arhitectură/Exterior — recent updated content)

**NOT ready / needs work**:
- ❌ Stripe LIVE mode (**user manual claim pending**)
- ❌ Production seed cleanup (**demo data purge pending**)
- 🟡 3 sisteme health scoring paralele (DRIFT risk pentru production alerting)
- 🟡 Referral system UI (backend există, UI neconfirmat)
- 🟡 Digital Twin viewer 3D (există model, UI needs testing)
- 🟡 Admin bundle size (79 lazy routes — perf audit needed)

---

## 17. Executive Summary — Top 20 Priorities

Ordonate după **impact asupra lansării + monetizare**:

| # | Prioritate | Impact | Effort | Blocker? |
|---|---|---|---|---|
| **P0-1** | **Stripe LIVE claim** (user manual action) | Direct revenue enablement | Manual (user) | ❌ blocher pentru monetizare reală |
| **P0-2** | **Purge demo data on production** + reseed cu date reale | Curățenia producție | Manual (user) | ❌ blocher lansare |
| **P0-3** | Fix orice discrepanță preț Concept Design / Audit Digital Twin (deja aliniat 2400 lei) | Consistență cross-page | ✅ DONE (recent fix) | — |
| **P0-4** | **Redeploy producție cu ultimele fixuri** (design-interior text v8 + hash-modal + `_get_content` fix) | Prezența textului nou pe live | Manual (user redeploy) | ❌ blocker prezentare |
| **P1-5** | **M4** — AI Agent Registry consolidat | Single view AI capabilities | Low | — |
| **P1-6** | **M3** — Unified Decision Ledger | Audit consolidat | Medium | — |
| **P1-7** | **LR1** — Extract `metrics_common.py` | Fundament consolidare | Low | — |
| **P1-8** | **Referral system UI** — confirmare + activare | Growth loop | Medium | — |
| **P1-9** | **Truth Engine oficial** — declarare owner + endpoint dedicat | Governance | Medium | — |
| **P1-10** | **Master routing map** — index navigabil peste 172 route files | Discoverability | Low | — |
| **P2-11** | **M1** — Unified Metrics Service | End of health scoring divergence | Medium-High | — |
| **P2-12** | **M2** — ExecutiveHub (consolidare 6 dashboards) | Executive velocity | Medium | — |
| **P2-13** | **Twin Viewer 3D UI testing** | User confidence | Medium | — |
| **P2-14** | **Admin bundle perf audit** — lazy routes 79 | Perf | Low-Medium | — |
| **P2-15** | **Event Bus consumer catalog** | Prevent blind refactors | Low | — |
| **P3-16** | **M5** — Twin storage consolidation | Data hygiene | High (data migration) | — |
| **P3-17** | **M6** — Growth/Marketing/Intelligence merge | Cognitive load | High | — |
| **P3-18** | **M7** — Knowledge Layer consolidation | Long-term coherence | High | — |
| **P3-19** | **Retention Policy MongoDB** | Data hygiene | Low | — |
| **P3-20** | **Test iter files** — archive completed iterations | Repo hygiene | Trivial | — |

---

## Metadata audit

- **Versiune**: 2026-07-31
- **Auditor**: E1 (Emergent agent)
- **Preview URL testat**: `https://phased-document.preview.emergentagent.com`
- **Producție**: `https://propmanage.ro` (NU testat activ pentru acest audit — reflectă codul din preview)
- **Metodologie**: analiză statică cod + inventory endpoints/collections + verificare live pe API-uri Preview.
- **Comparație vs versiuni anterioare**: Baseline. Prima versiune formală.
- **Next audit scheduled**: după Sprint 2 (M3 + M4 + LR1 completed) sau la orice deploy major.

---

**⚠️ Reguli de update**:
1. La fiecare audit major, agent (sau operator) creează `MASTER_PLATFORM_STATE_YYYY-MM-DD.md` în acest folder.
2. Se copiază peste `MASTER_PLATFORM_STATE.md` (canonic latest).
3. Se face diff cu versiunea anterioară → **Architecture Delta** intră în CEO Briefing.
4. Knowledge Center detectează automat noile fișiere prin `PATH_RULES`.
5. Nu se șterge nicio versiune anterioară — istoria este imutabilă.
