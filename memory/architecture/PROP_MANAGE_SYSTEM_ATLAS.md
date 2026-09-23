# PROP MANAGE — SYSTEM ATLAS

Version: 0.1 (targeted corrections 2026-09-22)
Status: Living Architecture Index
Purpose: Architecture + Security + Evidence Navigation
Authority: Index only — not a replacement for canonical SSOT

---

## 0. How to Use This Atlas

This Atlas is an **INDEX**. It is not a Source of Truth and must not compete with existing canonical artifacts.

| Layer | What it is | What it is not |
|---|---|---|
| Canonical SSOT / registries / MPS / Function Map / CSR / Enterprise Registry | Authoritative for their declared topics | Not replaced by this file |
| Code | Runtime evidence | Not automatically “documented” |
| This Atlas | Navigation, dependency map, security surface map, evidence index, audit status | Not a new engine, registry, or governance document |

Rules of reading:

- **Documented ≠ implemented.** A KC/registry/UI entry does not prove a live path.
- **Implemented ≠ connected.** A module can exist without a proven consumer.
- **Evidenced** means a named file, symbol, route, or test supports the claim.
- **Connected** means a caller → callee path is proven in code.
- **Automated** means a scheduler, hook, or script runs it without a human click.
- **Autonomous** means an existing autonomy loop can execute without human approval (subject to that loop’s own kill-switch / policy).
- **UNKNOWN** means not proven. UNKNOWN is not false, not defective, and not “missing.”
- When a canonical source already exists, this Atlas **references** it. Do not copy it wholesale.

Classification labels used below: **FACT** · **DOCUMENTED** · **IMPLEMENTED** · **EVIDENCED** · **CONNECTED** · **AUTOMATED** · **AUTONOMOUS** · **INFERRED** · **UNKNOWN**.

---

## 1. Executive System Map

Only components found in the repository. Do not treat this as an inventory of every file.

### PRODUCT

Marketplace of property owners (clients) and specialists; property records; service requests; matching; House Health / PVI-adjacent health; Digital Twin (2D `twins` + 3D `digital_twin_*`); document vault; HartaBlocuri / buildings; Verified Estate; PropBenefits; KYC/trust; community; interior design / service hub. Modules in this list are **IMPLEMENTED** as code where §3 names a backend file. **CONNECTED** only when that §3 row states a proven frontend/runtime path — otherwise connectivity is **UNKNOWN**. Canonical capability list: `memory/registries/FUNCTION_MAP.md`. Do not read this paragraph as a blanket CONNECTED claim.

### PLATFORM

React SPA (`frontend/src`) + FastAPI monolith (`backend/server.py`) + MongoDB (`backend/db.py`) + APScheduler jobs in `server.py` + Emergent object storage (`backend/storage_client.py`) + Stripe (`backend/routes/payments.py`). **IMPLEMENTED**.

### DATA

Mongo collections via `db` (`backend/db.py`). No separate ORM. Indexes: `backend/seed.py` (email unique, no collation) and `backend/migrations/create_indexes.py` (non-unique email). **IMPLEMENTED**. Live index state on a given deployment: **UNKNOWN**.

### KNOWLEDGE / GOVERNANCE

Filesystem KC (`memory/**/*.md`, `docs/**/*.md`) served by `backend/routes/knowledge_center.py`. Canonical maps: SSOT Registry, Function Map, Canonical System Registry, Enterprise Relationship Registry (`backend/data/enterprise_registry.json`), MPS family, PREFLIGHT protocol, Founder Gate FG-0 catalog. **DOCUMENTED** + (KC/ER/FG-0 status) **IMPLEMENTED** as read surfaces. Enforcement varies — see §7.

### AI / AUTOMATION

Concierge, copilot, admin AI, autonomy engine + FN-021 loop (`backend/autonomy/loop.py`), orchestrator, scheduled jobs. **IMPLEMENTED**. Execution is gated by existing kill-switch / admin-approvals / role checks — **CONNECTED** to those controls, not to FG-0 or PREFLIGHT HTTP. **AUTONOMOUS** only where `loop.py` / `self_driving.py` execute under their own policy (SAFE + kill-switch). Not a general autonomous OS.

### SECURITY

JWT cookie/Bearer (`deps.get_current_user`), `require_role`, `_enforce_admin_role`, `admin_scope` middleware, CSRF origin+`X-PM-Client` on `/api/admin` mutations, public rate-limit, Founder `_require_owner`, admin-approvals, impersonation blocks, GDPR routes. FG-0 is **not** runtime enforcement. **IMPLEMENTED** + **PARTIAL** coverage (see §6, §9).

---

## 2. Runtime Architecture

### Frontend

| | |
|---|---|
| Location | `frontend/src/` — entry routing `frontend/src/App.js`; auth `frontend/src/auth.js`; admin shell `frontend/src/pages/admin/` |
| Purpose | SPA: public marketing, client/specialist dashboards, admin/Founder consoles |
| Status | **IMPLEMENTED** · **CONNECTED** to `/api` via axios (`withCredentials`, `X-PM-Client`) |
| Dependencies | `REACT_APP_BACKEND_URL`; cookie session |
| Evidence | `frontend/src/App.js` (Routes from ~1710); `frontend/src/auth.js:5–10` |

### Backend

| | |
|---|---|
| Location | `backend/server.py` wires CORS, middleware, `ALL_ROUTERS`, APScheduler |
| Purpose | Single FastAPI app (“PropManage API”) |
| Status | **IMPLEMENTED** |
| Dependencies | `routes/register.py` (`ALL_ROUTERS`); `db.py`; `seed.py` at startup |
| Evidence | `backend/server.py:1–180`; `backend/routes/register.py` |

Route modules on disk: **183** files under `backend/routes/*.py` **FACT**. Registration is centralized in `routes/register.py`, not in `server.py`.

### API

| | |
|---|---|
| Location | Prefix `/api` on most routers; public `/api/public`, `/api/p`, GDPR `/api/gdpr`, Founder KC `/api/founder/knowledge` |
| Purpose | HTTP surface for product + admin + public |
| Status | **IMPLEMENTED** |
| Dependencies | FastAPI routers included in order from `ALL_ROUTERS` |
| Evidence | `backend/routes/register.py:188+`; individual `APIRouter(prefix=...)` |

### Database

| | |
|---|---|
| Location | `backend/db.py` — Motor `AsyncIOMotorClient(MONGO_URL)`, `db = client[DB_NAME]` |
| Purpose | Single Mongo handle for the monolith |
| Status | **IMPLEMENTED** |
| Dependencies | env `MONGO_URL`, `DB_NAME` |
| Evidence | `backend/db.py:1–12` |
| Sensitivity | **MIXED** (users, documents, payments, settings) |

No separate data-access layer. Routes call `db.<collection>` directly. **FACT**.

### Storage

| | |
|---|---|
| Location | `backend/storage_client.py` (Emergent objstore); `backend/storage_service.py`; routes `backend/routes/storage.py` |
| Purpose | Object bytes for document vault; quota/usage |
| Status | **IMPLEMENTED** · **CONNECTED** from `property_documents.py` |
| Dependencies | `EMERGENT_LLM_KEY`; `https://integrations.emergentagent.com/objstore/api/v1/storage` |
| Evidence | `storage_client.py:1–38`; `property_documents.py` `put_object` / `get_object` |
| Sensitivity | **SENSITIVE_PERSONAL** (property documents) |

### Authentication

| | |
|---|---|
| Location | `backend/routes/auth.py`; tokens `backend/core_utils.py`; session resolve `backend/deps.py` |
| Purpose | Register, login, OAuth, refresh, verify-email, password reset, `/me` |
| Status | **IMPLEMENTED** · **CONNECTED** |
| Dependencies | `JWT_SECRET`; cookies `access_token` / refresh; optional `Authorization: Bearer` |
| Evidence | §4 |
| Sensitivity | **CREDENTIAL/SECRET** |

### Authorization

| | |
|---|---|
| Location | `deps.require_role`; `sub_admin_deps.is_super_admin` / `require_admin_scope`; `middleware_scope.admin_scope_middleware`; KC `_require_owner`; `admin_accounts.PROTECTED_EMAILS` (narrow) |
| Purpose | Role + scope + Founder email ACL |
| Status | **IMPLEMENTED** · **PARTIAL**. `SCOPE_RULES` is a first-match prefix list. `_required_scope` returns `None` when no pattern matches (`middleware_scope.py:89–93`). Middleware then **skips** scope enforcement (`114–121`). There is **no** catch-all mapping unmatched `/api/admin/*` to `general`. Explicit `general` appears only on listed prefixes (e.g. `/api/admin/users`, `/config`, `/snapshots`). Non-admins are not blocked here. |
| Evidence | `middleware_scope.py:89–127`; §4, §9 |

### Background jobs

| | |
|---|---|
| Location | `backend/server.py` `AsyncIOScheduler` + `CronTrigger` (startup) |
| Purpose | Digests, backups, autonomy ticks, HH billing, matching, reminders, etc. |
| Status | **IMPLEMENTED** · **AUTOMATED** |
| Canonical count | CSR states **72 jobs** (`memory/registries/CANONICAL_SYSTEM_REGISTRY.md` row “Scheduler / cron jobs”). Atlas does not re-count. Treat CSR as authoritative for the number. |
| Evidence | `server.py:182+`; CSR scheduler row |

### External services

| Service | Evidence | Status |
|---|---|---|
| MongoDB | `db.py` | **CONNECTED** |
| Stripe | `routes/payments.py` (`STRIPE_API_KEY`, webhook `/api/webhook/stripe`) | **CONNECTED** (demo placeholder key possible) |
| Emergent object storage | `storage_client.py` | **CONNECTED** |
| Emergent LLM | `email_service` / AI routes / `EMERGENT_LLM_KEY` | **CONNECTED** where those routes call it |
| Google OAuth | `auth.py` google_direct_callback / google_session_exchange | **CONNECTED** |
| Email (Resend/templates) | `backend/email_service.py` | **CONNECTED** (send is best-effort on register verify) |
| Geocoding | `routes/geocoding.py` | **IMPLEMENTED** — provider wiring **PARTIAL** |
| Twilio / SMS Founder Gate | FG-0 comments only | **DOCUMENTED** future; **NOT** runtime **FACT** (`founder_gate/__init__.py`) |

---

## 3. Product Module Map

Include only modules found in code or clearly documented with a runtime pointer. Canonical capability catalog remains `FUNCTION_MAP.md`. This table is a locator, not a second Function Map.

### 3.1 Authentication & session

| Field | Value |
|---|---|
| Purpose | Account create, login, OAuth, cookies, session `/api/auth/me` |
| Frontend | `pages/Auth.jsx`, `EmailVerifyPage`, `/login` `/register` `/verify-email` `/auth/callback` (`App.js`) |
| Backend | `routes/auth.py`, `deps.py`, `core_utils.py` |
| API | `/api/auth/*` including `GET /api/auth/me`. Distinct from `PATCH /api/me/consent`. |
| Data | `users`, `consent_audit_log` |
| External | Google OAuth; email templates |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `auth.py`; `deps.py:10–38` |
| Known gaps | See §4–§5, IDENT-* |

### 3.2 Properties

| Field | Value |
|---|---|
| Purpose | Owner property records |
| Frontend | Client dashboard / property pages under `frontend/src/pages/` |
| Backend | `routes/properties.py` |
| API | `/api` properties routes |
| Data | `properties` |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `properties.py`; used by DNA/docs/twin loaders |

### 3.3 Requests / matching / marketplace

| Field | Value |
|---|---|
| Purpose | Service requests, specialist matching, public marketplace |
| Frontend | `/marketplace`, client request offers (`App.js`) |
| Backend | `routes/requests.py`, `matching.py`, `marketplace.py`, `marketplace_offers.py`, `premium_marketplace.py` |
| API | `/api` request/marketplace prefixes |
| Data | `requests`, marketplace collections (names per route) |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `register.py` includes these routers |

### 3.4 House Health

| Field | Value |
|---|---|
| Purpose | Subscription health audit on Digital Twin owners |
| Frontend | `/house-health/:twinId`, `/admin/house-health` |
| Backend | `house_health.py`, `house_health_plans.py`, `house_health_recommendations.py`, `house_health_billing.py` |
| API | `/api/house-health/*`, `/api/admin/house-health/*` |
| Data | `hh_subscriptions`, `hh_evaluations`, `hh_measurements`, `hh_documents` (module docstring) |
| External | Billing path exists; Stripe vs wallet split **PARTIAL** |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `house_health.py:1–26` |

### 3.5 Digital Twin (3D) + 2D twins

| Field | Value |
|---|---|
| Purpose | 3D twin projects + 2D property twins; canonical umbrella is Property Twin |
| Frontend | `DigitalTwinPage.jsx`, `ClientTwinViewer.jsx`, `OperatorDigitalTwin.jsx`, `/admin/twin` |
| Backend | `digital_twin.py`, `operator_twins.py`, `twin.py` |
| API | `/api/digital-twin/*`, `/api/operator/digital-twin/*`, `/api/admin/digital-twin/*`, 2D via `operator_twins` |
| Data | `digital_twin_projects/models/pins/comments`; `twins` (2D) |
| State | **IMPLEMENTED** · **CONNECTED** |
| Canonical | `memory/audits/PROPERTY_TWIN_CANONICAL_v1.0.md`; CSR Property Twin rows |
| Evidence | `digital_twin.py:51`, `3305`, `3562` |
| Known gaps | Module comment: Stripe for `digital_twin_pro` “Phase E” — treat as **DOCUMENTED** intent vs current admin-grant **IMPLEMENTED** |

### 3.6 Property documents / vault

| Field | Value |
|---|---|
| Purpose | Property document vault + completeness |
| Frontend | House Health documents section; property UI |
| Backend | `property_documents.py`; access via `_load_property_for` |
| API | `/api/properties/{id}/documents`, `/api/documents/{id}` |
| Data | `property_documents` |
| External | Emergent objstore |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `property_documents.py`; `property_dna.py:48–58` |
| Sensitivity | **SENSITIVE_PERSONAL** |

### 3.7 Property DNA / intelligence / passport

| Field | Value |
|---|---|
| Purpose | Read projection of property identity; passport; PVI-adjacent intelligence |
| Frontend | Passport / GIS pages (`/property/:id/gis`) |
| Backend | `property_dna.py`, `property_intelligence.py`, `property_passport.py`, `property_technical_record.py` |
| API | `GET /api/properties/{id}/dna`; passport public + auth routes |
| Data | properties + linked collections |
| State | **IMPLEMENTED** · **CONNECTED** |
| Canonical | CSR “Property DNA”; `GI5P_PROPERTY_INTELLIGENCE.md` is **DOCUMENTED** — do not assume all GI5P claims are runtime |

### 3.8 HartaBlocuri / buildings

| Field | Value |
|---|---|
| Purpose | Building import, public bloc explorer, identity |
| Frontend | `/blocuri`, `/admin/hartablocuri`, `/admin/harta-blocuri` |
| Backend | `hartablocuri.py`, `community_buildings.py`, `building_identity.py`, `building_admin.py` |
| API | `/api/admin/hartablocuri/*`, `/api/public` hartablocuri |
| Data | buildings collections (per route) |
| State | **IMPLEMENTED** · **CONNECTED** |
| Canonical | `memory/audits/HARTABLOCURI_INTEGRATION.md` **DOCUMENTED**; runtime = routes above |
| Evidence | `hartablocuri.py:20–21`, `253+` |

### 3.9 Verified Estate

| Field | Value |
|---|---|
| Purpose | Verified listings marketplace |
| Frontend | `/imobile-verificate`, `/admin/imobile-verificate` |
| Backend | `verified_estate.py` (consumes `app_settings.pricing.commission_pct` — prior forensic) |
| API | verified-estate routes on `/api` |
| Data | listings collections |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `register.py` `verified_estate_router`; `server.py` demo seed |

### 3.10 Payments / wallet / Stripe

| Field | Value |
|---|---|
| Purpose | Checkout for escrow; wallet balance; webhooks |
| Frontend | Ops payments panel; checkout UI |
| Backend | `payments.py`, `wallet.py` |
| API | `POST /api/payments/checkout-session` (`require_role("client")`); `GET /api/payments/status/{session_id}`; `POST /api/webhook/stripe` (signature); `GET /api/transactions`; `POST /api/wallet/topup` |
| Data | `transactions`, `users.wallet_balance` |
| External | Stripe |
| State | **IMPLEMENTED** · **CONNECTED** |
| Sensitivity | **FINANCIAL** |
| Evidence | `payments.py:20–223`; `wallet.py:18–29` |
| Known gaps | `wallet/topup` increments balance in Mongo with only `get_current_user` — **FACT**. Intent (demo vs production) **UNKNOWN**. Verified Estate reads `app_settings.pricing.commission_pct` (**FACT**). `platform_config.platform_commission_pct` has **no proven sale consumer** in the audited code. Unresolved: whether any *other* product path reads `platform_commission_pct`. |

### 3.11 Notifications

| Field | Value |
|---|---|
| Purpose | In-app + admin notification center |
| Frontend | `NotificationCenterPage.jsx` |
| Backend | `notifications.py`, `notification_center.py` |
| API | `/api` notifications + admin center |
| Data | notification collections |
| State | **IMPLEMENTED** |
| Cross-engine edges | C12/C13 **DO_NOT_REGISTER** (EO 002 disposition) — do not treat BH/Lead Intel → Notification Center as ER edges |

### 3.12 Chat / Concierge / Copilot

| Field | Value |
|---|---|
| Purpose | Messaging; AI concierge; client copilot |
| Frontend | **CONNECTED = UNKNOWN** in this row — no specific `App.js` path or component file proven here |
| Backend | `chat.py`, `concierge.py`, `concierge_core.py`, `copilot.py`, `client_copilot.py` exist and are registered |
| State | **IMPLEMENTED** (backend modules). Frontend/runtime **CONNECTED = UNKNOWN** |
| Evidence | Backend files + `concierge_core.py` rate-limit/PII. Do not treat module existence as a proven UI path. |

### 3.13 Knowledge Center (runtime)

| Field | Value |
|---|---|
| Purpose | Founder-only filesystem CMS + coverage/registry/inspector |
| Frontend | `/admin/knowledge-center`, `/admin/explorer`, `/admin/architecture` |
| Backend | `knowledge_center.py` prefix `/api/founder/knowledge` |
| Data | files on disk; `enterprise_registry.json`; coverage engines `knowledge_coverage.py` etc. |
| State | **IMPLEMENTED** · **CONNECTED** for listed GET routes; write-to-governance **not** this API (read-only KC) |
| Auth | `require_role("admin")` + `_require_owner` (OWNER_EMAIL) except `/access` |
| Evidence | `knowledge_center.py:20–22`, `170–172`, `333+` |

### 3.14 Admin console / app settings / CMS

| Field | Value |
|---|---|
| Purpose | Users, CMS, snapshots, settings |
| Frontend | Admin console, `AdminSettingsControl.jsx`, `AdminUsers.jsx` |
| Backend | `admin_console.py`, `app_settings.py`, `settings_snapshots.py`, `config_io.py` |
| API | `/api/admin/users/{id}` PATCH; `PUT /api/admin/app-settings`; snapshots; config IO |
| Data | `users`, `cms_content`, `app_settings` `_id=app_settings`, snapshot collections |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `admin_console.py:185–191`, `492–511` |

### 3.15 GDPR / legal

| Field | Value |
|---|---|
| Purpose | Export, erasure, consents, legal docs |
| Frontend | `/privacy`, legal pages |
| Backend | `gdpr.py`, `legal.py` |
| API | `/api/gdpr/me/*`, `/api/admin/gdpr`, legal routes |
| Data | users + consent logs |
| Sensitivity | **SENSITIVE_PERSONAL** |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `gdpr.py:29–30`, `299+` |

### 3.16 KYC / trust / reviews

| Field | Value |
|---|---|
| Purpose | Specialist verification (`users.verified`), trust, reviews |
| Frontend | `/kyc`, trust center, reviews |
| Backend | `kyc.py`, `trust.py`, `public_trust.py`, `reviews_v2.py`, `trusted_specialists.py` |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `kyc.py` writes `verified: True` |

### 3.17 Autonomy / approvals / orchestrator

| Field | Value |
|---|---|
| Purpose | Autonomy score, FN-021 loop, admin approvals, playbooks |
| Frontend | `/admin/autonomy`, `/admin/orchestrator`, `/admin/automation` |
| Backend | `autonomy.py`, `autonomy/loop.py`, `autonomy/self_driving.py`, `admin_approvals.py`, `orchestrator.py` |
| Data | `autonomy_snapshots`, `autonomy_alerts`, `autonomy_decisions`, approvals collections |
| State | **IMPLEMENTED** · **CONNECTED** · **AUTOMATED** (scheduler) · **AUTONOMOUS** only inside loop policy + kill-switch |
| Canonical | FN-002 / FN-021 in Function Map |
| Evidence | `autonomy/loop.py:208+` |

### 3.18 AI governance / control / activity

| Field | Value |
|---|---|
| Purpose | Admin AI control, governance page, activity, weekly briefing |
| Frontend | `/admin/ai-governance`, `/admin/ai-control`, `/admin/ai-security` |
| Backend | `ai_governance.py`, `ai_control.py`, `ai_activity.py`, `ai.py`, `admin_ai.py` |
| State | **IMPLEMENTED** |
| Relation to FG-0 | **NOT CONNECTED** (FG-0 does not intercept AI) **FACT** |

### 3.19 PropBenefits / entitlements / experience tiers

| Field | Value |
|---|---|
| Purpose | Membership benefits; feature entitlements; specialist/client tiers |
| Frontend | `useTier.js`, entitlement toast |
| Backend | `prop_benefits.py`, `propbenefits/eligibility.py`, `entitlements_api.py`, `experience_tiers.py` |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | eligibility reads `email_verified`; tiers treat `email_verified or google_auth` |

### 3.20 Tenants / franchise

| Field | Value |
|---|---|
| Purpose | Multi-tenant slug + franchise admin users |
| Backend | `tenants.py`, `tenancy.py` |
| Data | tenants; `users.tenant_id`; franchise_admin create sets `verified` + `email_verified` True |
| State | **IMPLEMENTED** · **CONNECTED** (startup backfill in `server.py`) |
| Evidence | `server.py:236–239`; `tenants.py` franchise create |

### 3.21 Impersonation / demo accounts

| Field | Value |
|---|---|
| Purpose | Admin “view as”; demo targets |
| Frontend | Admin layout QuickProfileSwitch |
| Backend | `impersonation.py`, `demo_accounts.py` |
| Canonical | CSR impersonation + demo rows |
| State | **IMPLEMENTED** · **CONNECTED** |
| Evidence | `core_utils.create_impersonation_token`; `deps.block_in_impersonation` |

### 3.22 Analytics / marketing / CEO / health dashboards

| Field | Value |
|---|---|
| Purpose | Growth analytics, CEO briefing, enterprise health, business health |
| Frontend | `/admin/ceo`, `/admin/enterprise-health`, `/admin/business-health`, analytics pages |
| Backend | `analytics_growth.py`, `ceo_briefing.py`, `ceo_dashboard.py`, `enterprise_health.py`, `business_health.py` |
| State | **IMPLEMENTED** |
| ER | C05/C06 registered e48/e49; D161↔Coverage consumer **HOLD** (only KC Coverage proven) |

### 3.23 Founder Gate (catalog)

| Field | Value |
|---|---|
| Purpose | Read-only critical-action catalog + flag display |
| Frontend | `/admin/founder-gate` |
| Backend | `founder_gate/`, `founder_gate_admin.py` |
| API | `GET /api/admin/founder-gate/status`, `/critical-actions` |
| State | **IMPLEMENTED** catalog · **NOT** enforcement (`enforcement_active: False`) |
| Evidence | `founder_gate_admin.py:31–48` |
| Note | `CRITICAL_ACTIONS` has **13** slugs (`registry.py`). Module comments say “12 actions” (`founder_gate/__init__.py`, `registry.py` header). **Source conflict** — count from list, not comments. |

### 3.24 Operating Manual

| Field | Value |
|---|---|
| Purpose | Founder-only operating manual |
| Backend | `operating_manual.py` prefix `/api/admin/operating-manual` — OWNER_EMAIL + admin |
| State | **IMPLEMENTED** · **CONNECTED** (same **identity** pattern as KC: admin + `_require_owner`). CSRF is **not** the same as KC: this prefix is under `/api/admin`. |
| Evidence | `operating_manual.py:17`, `19–24` |

### 3.25 Other implemented routers (locator only)

The following exist as route modules and are registered (or present on disk). Atlas does **not** expand each into a product claim: `projects`, `portfolio`, `design` / `design_studio` / `design_intelligence`, `regions`, `services_avail`, `security_guard`, `public`, `admin_seo`, `incidents`, `service_contracts`, `community`, `leads` / `lead_*`, `city_partners`, `marketplace_partners`, `strategic_partners`, `construction`, `kg`, `control_tower`, `xos`, `ux_lab`, `beta_*`, `pages_registry`, `site_menu`, `interior_design`, `service_hub`, `journey`, `engagement`, `capability_engine`, `first_revenue`, `operations_center`, `evolution_council`, `learning`, `repair_center`, `launch_sentinel`, `resend_diagnostics`, `geocoding`, `maintenance_calendar`, `renewal_reminders`, `config_io`, `settings_snapshots`, `admin_backups`, plus remaining `admin_*` / `ai_*` files in `backend/routes/`.

**Status:** **IMPLEMENTED** as code. Per-module **CONNECTED** to UI: **UNKNOWN** unless listed above or in Function Map / CSR.

---

## 4. Identity & Access Architecture

**HIGH PRIORITY.** Sources are **SEPARATE**. Do not collapse them.

### 4.1 Identity primitives

| Primitive | Binding | Writer / reader (proven) | Notes |
|---|---|---|---|
| `users._id` | Session subject | JWT `sub` → `get_current_user` `find_one({_id})` | **FACT** `deps.py:19–22`. JWT email/role **not** used for lookup. |
| `users.email` | Login/OAuth/forgot lookup; ADMIN_EMAILS / OWNER_EMAIL match | PATCH `/api/admin/users/{id}` raw (no lowercase, no unique check in handler); register/OAuth/login `input.lower()` then exact `find_one({email})` | **FACT** |
| `users.role` | `require_role`; `_enforce_admin_role` | Register `data.role`; PATCH `UserUpdateIn.role`; enforce promote/demote; admin_accounts change-role | **FACT** |
| `users.admin_scope` | Super-admin vs sub-admin; enforce exemption | Sub-admin seed/create; admin_accounts; enforce `has_scope` | **FACT** `auth.py:52–64` |
| `ADMIN_EMAILS` | Env CSV, lowercased set | `_enforce_admin_role` on login, `GET /api/auth/me`, OAuth | **FACT** `auth.py:38–40`, `273`, `369`, `1181`, `1322` |
| `OWNER_EMAIL` | Env CSV, lowercased | KC + operating_manual `_require_owner` | **FACT** `knowledge_center.py:22`, `170–172` |
| `PROTECTED_EMAILS` | Hardcoded `admin@propmanage.io`, `danieligna1@gmail.com` | **Only** `admin_accounts.py` block/change-role | **FACT**. Does **not** wrap PATCH `/users/{id}` **FACT** |
| `founder_contact` | Nested `app_settings` field | PUT app-settings schema; FG-0 example slug | **IMPLEMENTED** persist field. **No** auth consumer found. **FACT** (prior identity audit) |
| JWT `sub` | `_id` string | `create_access_token` | **FACT** `core_utils.py:23–28` |
| JWT `email` / `role` | Claims only | Minted at login/register/OAuth; **unused** by `get_current_user` | **FACT** |
| `get_current_user` | Cookie `access_token` or Bearer | All protected routes | **FACT** `deps.py:10–38` |
| `require_role(*allowed)` | DB `user.role` (+ specialist dual-view) | Per-route Depends | **FACT** `deps.py:58–70` |
| `_enforce_admin_role` | lowercased email ∈ ADMIN_EMAILS **or** `admin_scope` → admin; else admin without list/scope → operator | login, `GET /api/auth/me`, OAuth only — **not** register, **not** PATCH | **FACT** |
| `is_super_admin` | `role==admin` AND `(admin_scope or "general")=="general"` | `sub_admin_deps.py:36–37` | **FACT**. Not a stored role named `super_admin`. |
| `_require_owner` | lowercased email ∈ OWNER_EMAILS | KC + operating_manual after admin role | **FACT**. Founder = **OWNER_EMAIL + admin** (admin required because routes use `require_role("admin")` first). |
| `admin_scope` middleware | JWT → user → SCOPE_RULES on `/api/admin/*` | `middleware_scope.py`; non-admins not blocked here | **FACT** |
| CSRF | POST/PUT/PATCH/DELETE `/api/admin` + Origin present: origin suffix allowlist **and** `X-PM-Client: propmanage-app` | `server.py:128–148` | Requests **without** Origin pass **FACT** |
| Cookies | `set_auth_cookies` | `core_utils.py:81+`; axios `withCredentials` | **FACT** |
| OAuth | Email-only lookup (`email.lower()`); sets `google_auth=True`; no `google_id` bind | `auth.py` google callbacks | **FACT** |
| Password login | `email.lower()` exact find; rate-limit; optional 2FA | `auth.py` login | Does **not** read `email_verified` **FACT** |
| Password reset | JWT `sub=_id`, email claim from request; consume by `_id` | Prior forensic: token email vs current `users.email` **ignored** | **IMPLEMENTED** |
| Email verification | Opaque token on user doc | §5 | Not a login gate **FACT** |
| `google_auth` | OAuth flag | Writers: OAuth paths; readers: login projection, password-link gate, experience_tiers | **FACT** |
| `users.verified` | Specialist/KYC-style flag | Register `False`; PATCH `UserUpdateIn.verified`; KYC approve `True`; matching/trust/digest | **FACT**. Distinct from `email_verified`. |

### 4.2 Roles (only those proven in code)

| Label | How it exists | Privilege |
|---|---|---|
| **USER / client** | `RegisterIn.role` default; OAuth insert `"role": "client"` | Client routes via `require_role("client")` or dual-view |
| **SPECIALIST** | Register `role=specialist` | Specialist routes; `users.verified` used as KYC/trust, not email verify |
| **ADMIN** | Whitelist promote; PATCH role; register schema **allows** `"admin"` (`models.py:5`, `auth.py:123`) without `_enforce` at register time | `require_role("admin")`; `/api/admin` |
| **SUPER-ADMIN** | Computed: admin + scope general (legacy missing scope = general) | `is_super_admin`; admin-accounts; some SCOPE_RULES `general` |
| **FOUNDER** | Not a `users.role`. Email ∈ `OWNER_EMAIL` **and** admin (KC/manual) | KC + operating_manual. Frontend also hardcodes emails in nav (**DOCUMENTED** UI, separate from `_require_owner`) |
| **OPERATOR** | Enforce demotion target; `RegisterIn` allows; admin_accounts ALLOWED_ROLES | `require_role("operator")` where used; not Founder |
| **franchise_admin** | Created in `tenants.py` | Tenant/franchise surfaces |
| **marketing_manager** | `admin_accounts.ALLOWED_ROLES` | **IMPLEMENTED** as allowed target role; full privilege map **PARTIAL** |
| Dual-role | `dual_role_enabled` + `active_view` | `require_role` specialist→client view **FACT** `deps.py:62–68` |

Do not invent additional role semantics.

### 4.3 Established email forensic findings (preserved)

All **FACT** / **IMPLEMENTED** / **CONNECTED** from prior read-only audits (2026-09-22 Cursor series) unless marked UNKNOWN:

1. `PATCH /api/admin/users/{id}` can set `users.email` **raw** (no lowercase). `UserUpdateIn` fields: name, email, role, verified, tier, banned (`admin_console.py:185–191`). Handler `$set`s provided keys (`492–506`).
2. Email PATCH does **not** by itself write `role` or `admin_scope` (only if those keys are also sent). Admin UI `AdminUsers.jsx` typically sends email+role+name+verified+tier together — **CONNECTED** UI, not a server allowlist.
3. `_enforce_admin_role` uses **lowercased** stored email vs `ADMIN_EMAILS` + `admin_scope`. After PATCH, next login/`/me`/OAuth can promote or demote.
4. `OWNER_EMAIL` is **independent** of `ADMIN_EMAILS`. Founder/KC = OWNER_EMAIL match + admin role.
5. `PROTECTED_EMAILS` does **not** protect PATCH `/users/{id}`.
6. Mixed-case stored email vs `input.lower()` lookup can miss → login/OAuth 401 or second-user create on register/OAuth.
7. Email mutation changes subsequent email-list privilege matching; existing JWT stays bound to `_id`.
8. `email_verified` is **not** on the admin / Founder / KC privilege path.

### 4.4 Register role note (evidence, not a fix)

`RegisterIn.role: Role` includes `"admin"` and `"operator"` (`models.py:5`, `19–23`). `register` writes `data.role` and issues cookies **without** calling `_enforce_admin_role` (`auth.py:94–176`). `get_current_user` / `require_role` read DB role. Enforce runs on login, `GET /api/auth/me`, OAuth only. **FACT**. Schema/register-handler behavior is **proven**. IDENT-U005 remaining unknown is only: does the **register UI** send `role=admin`? Do not label this a vulnerability in the Atlas.

---

## 5. Verification & Identity State

Three distinct “verified” concepts. Complete cross-map of all readers remains **OPEN** (IDENT-U001).

| Field | Writer | Reader | Purpose | Bound to | Privilege impact | Status |
|---|---|---|---|---|---|---|
| `email_verified` | Register `False`; verify-email `True`; resend does not set True; consent_backfill if missing `True`; sub-admin/franchise/impersonation-demo create `True` | verify/resend; `/me` serialize; admin list filter; banner; experience_tiers; PropBenefits eligibility; ai_insights counts | Prove inbox via token | **`users._id`** (flag on that document). **Not** rebound on email PATCH | **None** for admin / Founder / KC / login / OAuth / reset **FACT** | **IMPLEMENTED** · **CONNECTED** to tiers/benefits/UI |
| `email_verified_at` | verify-email `$set` | not a privilege reader found | Timestamp | `_id` | None found | **IMPLEMENTED** |
| `email_verification_token` | Register; resend (overwrite) | `GET /auth/verify-email` `find_one({token})` | Opaque `secrets.token_urlsafe(32)` — **not** JWT; no email/`sub`/`jti` | Document that currently stores the string | Sets `email_verified` on that `_id` only | **IMPLEMENTED** |
| `email_verification_expires_at` | Register/resend +24h | verify-email expiry check | TTL | same doc | None beyond verify | **IMPLEMENTED** |
| `google_auth` | OAuth create/update `True` | login fields; Google-password-link gate; experience_tiers OR with email_verified | OAuth-linked account | `_id` | Not admin/KC. Tiers treat as verified-equivalent **FACT** `experience_tiers.py:176` | **IMPLEMENTED** |
| `users.verified` | Register `False`; PATCH `verified`; KYC approve `True`; seeds | matching, trust, digest, command_center, community, adaptive_ux, tenants display, admin list | Specialist/KYC/trust flag | `_id` | **Not** Founder/KC. Marketplace/trust **CONNECTED** | **IMPLEMENTED** |

**Preserved finding:** `email_verified` is **not** part of the admin / Founder / KC privilege path. **FACT**.

**PATCH email:** does not change `email_verified`, does not invalidate tokens, does not require re-verify. Old token still verifies the **same `_id`** (possibly new email). Second account at old email gets its **own** token. **FACT** (verification audit).

OAuth insert does **not** set `email_verified` (field may be missing). **FACT**.

**OPEN AUDIT ITEM:** IDENT-U001 — full relationship of `email_verified` × `google_auth` × `users.verified` across all privilege/tier/KYC paths.

---

## 6. Security Surface Map

**HIGH PRIORITY.** Do not mark **vulnerable** unless a complete path is proven. Use AUDITED / PARTIAL / UNKNOWN / EXTERNAL / NOT_APPLICABLE.

Sensitivity: PUBLIC · INTERNAL · PERSONAL · SENSITIVE_PERSONAL · FINANCIAL · CREDENTIAL/SECRET · MIXED · UNKNOWN.

### 6.1 Authentication

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Register | `POST /api/auth/register` | Public | Writes requested `role` | n/a | PERSONAL + CREDENTIAL | Consent gates; email uniqueness exact | AUDITED | Role includes admin in schema; no enforce at register | `auth.py:94`; `models.py:5` |
| Login | `POST /api/auth/login` | Public | Then `_enforce_admin_role` | n/a | CREDENTIAL | Password; login rate-limit; 2FA optional | AUDITED | Lookup case-sensitive on stored email | `auth.py:237+` |
| OAuth | google callbacks / session exchange | Provider | Enforce after load | n/a | PERSONAL | Email-only bind | AUDITED | No `google_id`; case miss → new user | `auth.py` OAuth blocks |
| `GET /api/auth/me` | `auth.py` `/auth/me` | JWT | Enforce | n/a | PERSONAL | JWT | AUDITED | Not `PATCH /api/me/consent` | `auth.py:300`, `361–370` |
| Refresh / cookies | `set_auth_cookies` | Cookie | — | n/a | CREDENTIAL | HttpOnly (see `core_utils`) | PARTIAL | Cookie flags not re-read this pass | `core_utils.py:81` |
| Password reset | forgot/reset | Token JWT | Consume by `_id` | n/a | CREDENTIAL | Token + jti (prior audit) | AUDITED | Token email claim unused vs current email | `auth.py` |
| Verify email | `GET /api/auth/verify-email` | Token query | Token holder `_id` | n/a | PERSONAL | Opaque token + expiry | AUDITED | Survives email PATCH | `auth.py:1713–1735` |
| Resend verify | `POST /api/auth/resend-verification` | JWT | Self | n/a | PERSONAL | 5 min in-memory limit | AUDITED | Sends to **current** `users.email` | `auth.py:1740–1761` |

### 6.2 Authorization

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Role gate | `require_role` | JWT | DB role | n/a | MIXED | Role + dual-view | AUDITED | JWT.role unused | `deps.py:58–70` |
| Scope dep | `require_admin_scope` | JWT | admin + scope | listed | INTERNAL | Super-admin bypass | AUDITED | Not on every handler | `sub_admin_deps.py` |
| Scope MW | `admin_scope_middleware` | JWT if present | Sub-admins only | First matching `SCOPE_RULES` prefix | INTERNAL | First-match regex; skip if no match | AUDITED | Unmapped `/api/admin/*` → `_required_scope` is `None` → **no** scope check. Not `general`. | `middleware_scope.py:89–121` |
| Founder ACL | `_require_owner` | admin JWT | OWNER_EMAIL | n/a | INTERNAL | Email set | AUDITED | Independent of ADMIN_EMAILS | `knowledge_center.py:170` |

### 6.3 Admin endpoints

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| User PATCH | `PATCH /api/admin/users/{id}` | JWT | `require_role("admin")` | MW general-ish | PERSONAL + privilege | Admin role; audit log | AUDITED | No PROTECTED_EMAILS; raw email; verified/role in same schema | `admin_console.py:492` |
| App settings | `PUT /api/admin/app-settings` | JWT | `require_role("admin", "operator")` | `backend` **only if** `role==admin` (MW skips non-admins) | MIXED / FINANCIAL | CSRF (`/api/admin`); scope MW for admin+scope | AUDITED | Persist loop drops non-dict keys (e.g. `enable_founder_gate` bool) — prior audit **FACT**. Operators skip scope MW. | `app_settings.py:182`; `middleware_scope.py:67`, `126–127` |
| Admin accounts | `/api/admin/admin-accounts/*` | JWT | `is_super_admin` + master code | general | CREDENTIAL | PROTECTED_EMAILS + code | AUDITED | Master code default env `0108` | `admin_accounts.py:39–60` |
| Impersonate | `/api/admin/impersonate` | JWT | admin + security scope map | security | PERSONAL | CSRF; GDPR log; TTL | AUDITED | — | CSR + `impersonation.py` |
| Config IO / snapshots / backups | config_io, settings_snapshots, admin_backups | JWT | admin | backend/ops | MIXED | CSRF + role | PARTIAL | Alternate writers of `app_settings` (reset/restore/import) — prior audit | those modules |
| Founder Gate API | `/api/admin/founder-gate/*` | JWT | admin | general | INTERNAL | Read-only | AUDITED | No enforcement | `founder_gate_admin.py` |

### 6.4 Founder endpoints

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| KC | `/api/founder/knowledge/*` | JWT | admin + OWNER_EMAIL | n/a (prefix is **not** `/api/admin`) | INTERNAL | `_require_owner` | AUDITED | CSRF guard applies to `/api/admin` mutations only. Audited KC operations are **GET**. | `knowledge_center.py:20` |
| Operating manual | `/api/admin/operating-manual` | JWT | admin + OWNER_EMAIL | Unmapped in `SCOPE_RULES` → MW skip | INTERNAL | `_require_owner`; CSRF **does** cover this `/api/admin` prefix | AUDITED | Not the KC CSRF gap. Identity pattern matches KC; CSRF prefix does not. | `operating_manual.py:17`, `19–24` |
| `/access` | KC access | admin only | no owner check | n/a | INTERNAL | role | AUDITED | Any admin can hit `/access` | `knowledge_center.py:333–335` |

### 6.5 Public endpoints

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Public API | `/api/public/*`, `/api/p/`, `/api/track`, `/api/go/` | None | None | n/a | PUBLIC / MIXED | In-memory rate-limit 120/min/IP | AUDITED | Other public routers may sit **outside** these prefixes | `rate_limit.py:8–34` |
| Stripe webhook | `POST /api/webhook/stripe` | Signature | n/a | n/a | FINANCIAL | Stripe signature | PARTIAL | Demo key path | `payments.py:209` |
| HartaBlocuri public | `hartablocuri` `public_router` | None | — | n/a | PUBLIC | rate-limit if under `/api/public` | PARTIAL | Confirm prefix | `hartablocuri.py:21` |
| Passport public | `passport_public_router` | varies | — | n/a | PERSONAL? | per-route | UNKNOWN | Full ACL not re-traced this pass | `property_passport.py` |

### 6.6 User-owned endpoints

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Property DNA/docs | `_load_property_for` | JWT | owner `_id` **or** admin/operator/franchise_admin | n/a | SENSITIVE_PERSONAL | Owner check | AUDITED | Dual-view uses `active_view` | `property_dna.py:48–58` |
| Wallet topup | `POST /api/wallet/topup` | JWT | self | n/a | FINANCIAL | Auth only; amount 0–10000 | PARTIAL | No Stripe; direct `$inc` | `wallet.py:23–29` |
| GDPR self | `/api/gdpr/me/*` | JWT | self | n/a | SENSITIVE_PERSONAL | Auth | PARTIAL | Bulk export vs FG slug unmapped | `gdpr.py:299+` |

### 6.7 File/document access

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Vault file | `GET /api/documents/{id}/file` | JWT | property ACL | n/a | SENSITIVE_PERSONAL | `_load_doc_for` → property owner | AUDITED | Storage key = Emergent | `property_documents.py:91–99`, `382` |
| HH documents | house_health document routes | JWT | owner (module docstring) | n/a | SENSITIVE_PERSONAL | per-route | PARTIAL | Not re-traced line-by-line this pass | `house_health.py` |
| Digital twin files | `digital_twin.py` uploads | JWT | twin ACL | n/a | MIXED | module gates | PARTIAL | Large module; not fully mapped here | `digital_twin.py` |

### 6.8 Personal data

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| User list/update | admin users | admin | role | general | PERSONAL | admin + CSRF | AUDITED | Email/role PATCH | `admin_console.py` |
| GDPR export/erasure | gdpr | user/admin | self / admin gdpr | security MW | SENSITIVE_PERSONAL | role + scope map `/api/admin/gdpr` | PARTIAL | FG `gdpr_bulk_export` not wired | `gdpr.py`; FG registry |
| Consent log | `_record_consent` | register/settings | append-only | n/a | PERSONAL | write-only log | AUDITED | — | `auth.py:71–82` |
| Impersonation logs | impersonation | admin | security | security | PERSONAL | CSR allowlist | AUDITED | — | CSR |

### 6.9 Financial/payment operations

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Checkout | `POST /api/payments/checkout-session` | JWT | client | n/a | FINANCIAL | role | AUDITED | Demo Stripe key | `payments.py:30–32` |
| Commission / pricing | `PUT /api/admin/app-settings` `pricing.*` | JWT | `require_role("admin", "operator")` | `backend` if admin | FINANCIAL | CSRF; **not** FG | AUDITED | VE sale path reads `app_settings.pricing.commission_pct`. `platform_commission_pct` has no proven sale consumer. | `app_settings.py:182`; `verified_estate.py` |
| Wallet | `wallet.py` | JWT | self | n/a | FINANCIAL | auth | PARTIAL | Topup without PSP | `wallet.py` |
| HH billing | `house_health_billing.py` | mixed | — | n/a | FINANCIAL | per-route | PARTIAL | Not fully mapped this pass | module + cron seed |

### 6.10 External integrations

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Stripe | payments + webhook | key/sig | n/a | n/a | FINANCIAL / CREDENTIAL | API key env | PARTIAL | Placeholder key | `payments.py:22` |
| Emergent storage | `storage_client` | `EMERGENT_LLM_KEY` | server-side | n/a | CREDENTIAL + files | server only | PARTIAL | Key shared with LLM | `storage_client.py:6` |
| Google OAuth | auth.py | provider | n/a | n/a | PERSONAL | email match | AUDITED | §4 |
| Email | `email_service.py` | server | n/a | n/a | PERSONAL | templates | PARTIAL | Provider config **UNKNOWN** this pass |
| Geocoding | `geocoding.py` | varies | — | n/a | INTERNAL | — | UNKNOWN | Provider/key | module exists |

### 6.11 Background/scheduled operations

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| APScheduler | `server.py` jobs | Process | none (in-process) | n/a | MIXED | Startup only | PARTIAL | Job privilege = process credentials | `server.py:232+` |
| Autonomy ticks | `loop.py`, `self_driving.py` | Scheduler | kill-switch + policy | n/a | MIXED | `autoexec_allowed` / low_risk | AUDITED as existence | Not PREFLIGHT/FG | `autonomy/loop.py:208` |
| Backups | `backup_service.py` | Scheduler / admin | admin backups | ops | MIXED | role | PARTIAL | — | `server.py` import; `admin_backups.py` |

### 6.12 Secrets/configuration

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Env secrets | `JWT_SECRET`, `MONGO_URL`, `STRIPE_API_KEY`, `OWNER_EMAIL`, `ADMIN_EMAILS`, `EMERGENT_LLM_KEY`, `DEMO_MASTER_CODE` | Host | — | n/a | CREDENTIAL/SECRET | env / `.env` via `db.py` load_dotenv | PARTIAL | Live values not inspected (read-only Atlas) | `db.py`; `core_utils.py:8`; `admin_accounts.py:39` |
| App settings | `db.app_settings` | JWT | `require_role("admin", "operator")` on PUT | `backend` if admin | MIXED | CSRF | AUDITED | Alternate writers; bool persist; operators skip scope MW | `app_settings.py:182`; prior FG-0 field/writer audits |
| Config import | `config_io.py` | admin | — | frontend/backend | MIXED | dry-run default (CSR) | PARTIAL | Can `$set` settings | CSR + module |

### 6.13 AI/autonomy operations

| Surface | Route/function | Auth | Authz | Scope | Sensitivity | Protection | Audit | Gap | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Concierge | concierge routes | JWT | user | ai (admin) | PERSONAL | PII filter + rate-limit | PARTIAL | — | `concierge_core.py` |
| Autonomy loop | `/api/admin/autonomy/loop/*` + cron | admin / scheduler | ops scope + kill-switch | ops | MIXED | FN-021 + approvals for non-SAFE | AUDITED | Duplicate-engine risk if new approval system added | Function Map FN-021; `loop.py` |
| Admin AI | `ai_control`, `ai_dev_team`, etc. | admin | ai scope | ai | INTERNAL | role + MW | PARTIAL | FG AI-structural slugs UNMAPPED (prior FG-0 map) | FG registry + those routes |

---

## 7. Governance & Control Plane

Canonical sources remain authoritative. Atlas indexes them.

| Control | Canonical / document | Runtime | Enforcement | Status | Known gaps | Dependencies |
|---|---|---|---|---|---|---|
| **SSOT Registry** | `memory/registries/SSOT_REGISTRY.md` | KC lists files; no SSOT engine | Human / agent protocol | **DOCUMENTED**. Runtime consume = KC file serve **CONNECTED** | Not auto-enforced on HTTP | MKG |
| **Knowledge Center** | MKG; EO 002 | `knowledge_center.py`; `knowledge_coverage.py`; `knowledge_history.py`; `knowledge_reconciliation.py` | Founder ACL | **IMPLEMENTED** read + coverage | Lifecycle is derived metadata, not a second SoT | OWNER_EMAIL; ER JSON |
| **Function Map** | `memory/registries/FUNCTION_MAP.md` | Admin Function Map page (FN-003 family) | None on HTTP | **DOCUMENTED** + UI **CONNECTED** | Map status ≠ runtime proof | KC |
| **Canonical System Registry** | `memory/registries/CANONICAL_SYSTEM_REGISTRY.md` | None as DB | PREFLIGHT human lookup | **DOCUMENTED** | — | PREFLIGHT |
| **Enterprise Registry** | EO 002 PHASE_SPECS + `backend/data/enterprise_registry.json` | KC registry/inspector/explorer | Evidence-gated graph, **not** inventory | **IMPLEMENTED** JSON + KC consumers | Node inclusion = Founder decision; C01–C13 disposition recorded | D161 |
| **MPS** | SSOT: `memory/audits/MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md`; siblings exist | KC documents | None | **DOCUMENTED**. Family **AMBIGUOUS** for single OwnerDocument (prior discovery) | Do not pick a winner here | SSOT |
| **PREFLIGHT** | `memory/prompts/PREFLIGHT_GATE.md` | `production_safety_check.py` file-exists / static checks (deploy script) | **Human/agent protocol**, not HTTP middleware | **DOCUMENTED**. Script **IMPLEMENTED** as CLI | **Preserved:** not a runtime HTTP enforcement mechanism | CSR, Function Map, MKG |
| **Founder Gate FG-0** | `backend/founder_gate/__init__.py`, `registry.py` | Read-only admin API | `enforcement_active: False`; `is_critical_action` unused by middleware | **IMPLEMENTED** catalog only | **Preserved:** not active runtime enforcement. Do not propose FG-1/FG-2 here. | `enable_founder_gate` flag (persist issue) |
| **AI Governance** | `memory/product/09_AI_GOVERNANCE.md` **DOCUMENTED**; routes `ai_governance.py` | Admin page + API | Per-route admin | **IMPLEMENTED** UI/API ≠ FG | Not wired to FG-0 | admin role |
| **Admin approvals** | Function Map / autonomy docs | `admin_approvals.py` | Human approve/reject | **IMPLEMENTED** · **CONNECTED** to autonomy medium actions | Not PREFLIGHT | `sub_admin_deps` |
| **Autonomy controls** | FN-002 / FN-021 | `autonomy/loop.py` kill-switch `self_driving_settings` | Kill-switch + class SAFE/MEDIUM | **IMPLEMENTED** · **AUTOMATED** | Do not create a second approval engine | scheduler |
| **Production safety check** | CSR / scripts | `backend/scripts/production_safety_check.py` | Deploy-time script | **IMPLEMENTED** (CLI) | Not request-time | server.py source scan |

---

## 8. System Dependency Map

Notation:

```
──────  PROVEN RUNTIME CONNECTION
- - -  DOCUMENTED / NON-RUNTIME RELATIONSHIP
?????? UNKNOWN / NOT PROVEN
```

```
[React SPA] ────── axios + cookies + X-PM-Client ────── [FastAPI server.py]
[server.py] ────── include ALL_ROUTERS ────── [routes/*.py]
[routes] ────── db.<collection> ────── [Mongo]
[deps.get_current_user] ────── JWT.sub ────── [users._id]
[login /me OAuth] ────── _enforce_admin_role ────── [ADMIN_EMAILS env + users.admin_scope]
[KC + operating_manual] ────── _require_owner ────── [OWNER_EMAIL env]
[admin_scope_middleware] ────── SCOPE_RULES ────── [/api/admin/* sub-admins]
[CSRF guard] ────── Origin + X-PM-Client ────── [/api/admin mutations only]
[property_documents] ────── _load_property_for ────── [properties.owner_id]
[property_documents] ────── put_object/get_object ────── [Emergent objstore]
[payments] ────── StripeCheckout ────── [Stripe]
[verified_estate] ────── pricing.commission_pct ────── [app_settings]
[KC] ────── read ────── [enterprise_registry.json]
[KC Coverage] ────── knowledge_coverage.py ────── [memory/ + docs/]
[scheduler] ────── CronTrigger ────── [autonomy / backups / HH / matching / …]
[FN-021 loop] ────── kill-switch ────── [self_driving_settings]
[FN-021 loop] ────── admin_approvals ────── [human approve]

[SSOT / Function Map / CSR / MPS / PREFLIGHT.md] - - - [agents / humans]
[FG-0 registry] - - - [admin UI catalog]
[FG-0] ?????? [HTTP mutation intercept]     # proven ABSENT (enforcement_active False)
[PREFLIGHT.md] ?????? [FastAPI middleware]  # proven ABSENT
[founder_contact] ?????? [auth / KC]        # no consumer found
[platform_config.platform_commission_pct] ?????? [sale path other than VE]  # VE sale consumer is app_settings.pricing.commission_pct
[D161 classes] ?????? [CEO Briefing / Inspector / Explorer live counts]
[PROTECTED_EMAILS] ?????? [PATCH /users/{id}]  # proven ABSENT
```

Do not promote `- - -` or `??????` to `──────`.

---

## 9. Existing Security Controls

Inventory only. No new controls proposed.

| Control | Protects | Where | Enforcement point | Limitations | Audit |
|---|---|---|---|---|---|
| JWT HS256 | Session authenticity | `core_utils.py`, `deps.py` | Cookie/Bearer decode | Email/role claims unused; 24h access | AUDITED |
| `require_role` | Route role | `deps.py` | Depends | DB role; register can write admin until enforce | AUDITED |
| `_enforce_admin_role` | Admin whitelist drift | `auth.py` | login, `GET /api/auth/me`, OAuth | Not PATCH, not register | AUDITED |
| `admin_scope` + MW | Sub-admin blast radius | `middleware_scope.py`, `sub_admin_deps.py` | HTTP `/api/admin` + deps | Unmapped prefix → `None` → skip (not `general`); non-admins skipped in MW | AUDITED |
| CSRF Origin + `X-PM-Client` | Browser CSRF on admin mutations | `server.py:128–148`; `auth.js:10` | `/api/admin` mutating methods | No Origin → pass; `/api/founder` not covered | AUDITED |
| Founder ACL | KC / manual | `_require_owner` | After admin role | Email-env; PATCH email can change match | AUDITED |
| Admin approvals | Medium autonomy / junior actions | `admin_approvals.py` | Approve/reject routes | Not FG | AUDITED |
| Autonomy kill-switch | Loop auto-exec | `autonomy/loop.py` | `autoexec_allowed` / settings | Separate from FG/PREFLIGHT | AUDITED |
| PROTECTED_EMAILS | Block/demote via admin-accounts | `admin_accounts.py` | Those endpoints only | Not PATCH users | AUDITED |
| Master code | Admin-accounts writes | `DEMO_MASTER_CODE` default `0108` | `_require_code` | Default in source | AUDITED |
| Impersonation block | Password/2FA/delete | `block_in_impersonation` | Selected deps | Not global | AUDITED |
| Production safety check | Deploy readiness | `scripts/production_safety_check.py` | CLI | Not HTTP | AUDITED as script |
| Audit logging | Admin mutations (users, etc.) | `audit(...)` in admin_console; `admin_actions_log` | After some writes | Not all routes | PARTIAL |
| Public rate-limit | Abuse on public prefixes | `rate_limit.py` | Middleware | In-memory; prefix-limited | AUDITED |
| Login rate-limit | Password spray | `auth.py` `_check_login_rate_limit` | Login | In-memory | AUDITED |
| Concierge rate-limit + PII | AI chat abuse / leak | `concierge_core.py` | Concierge | That surface only | PARTIAL |
| Consent audit log | GDPR evidence | `consent_audit_log` | Register/settings | — | AUDITED |
| Email unique index (seed) | Duplicate email | `seed.py` `create_index("email", unique=True)` no collation | Mongo | Case-sensitive; migrations file differs; live **UNKNOWN** | PARTIAL |
| Stripe signature | Webhook spoof | `payments.py` | Webhook | Demo key | PARTIAL |
| FG-0 catalog | Documentation of intended critical actions | `founder_gate/registry.py` | **None** | `is_critical_action` unused | AUDITED |

---

## 10. Open Questions & Unresolved Items

This is **not** a list of 22 UNKNOWNs. IDs are stable locators. **UNKNOWN = not proven, not false.**

CLOSED findings (PREFLIGHT not HTTP, FG-0 not enforcement, CSRF no-Origin by design) live in §11, not here.

### UNKNOWN / NOT PROVEN

| ID | Title | Category | Why it matters | Evidence | Next safe investigation |
|---|---|---|---|---|---|
| IDENT-U002 | Live unique `users.email` index | Identity | Duplicate accounts | seed vs `migrations/create_indexes.py` | Inspect index list on a non-prod snapshot **without writes** if Founder authorizes |
| IDENT-U003 | Unique index on `email_verification_token` | Identity | Token collision | None in repo (`auth.py:1718`) | Same as IDENT-U002 |
| IDENT-U005 | Does the **register UI** send `role=admin`? | Identity | Schema already proven (`models.py:5`; `auth.py:123` writes `data.role`). Only the frontend payload is unproven. | Register handler + `RegisterIn` | Read-only trace of `Auth.jsx` / register form body |
| SEC-U006 | Wallet topup product intent | Financial | Direct `$inc` proven (`wallet.py:23–29`); demo vs production **not proven** | `wallet.py` | Confirm product intent |
| ARCH-U002 | Architecture Navigator widget vs runtime | Architecture | Menu ≠ implementation | `/admin/architecture` | Use ER + code, not UI |
| ARCH-U003 | Full CONNECTED map of 183 route files | Architecture | Atlas lists locators, not each consumer | `register.py` | Module-by-module only when needed |

### HOLD

| ID | Title | Category | Why it matters | Evidence | Notes |
|---|---|---|---|---|---|
| SEC-U001 | PATCH `/users/{id}` outside PROTECTED_EMAILS | Security | Email/role/verified of any `_id` | `admin_console.py:492`; `admin_accounts.py:41` | Investigation closed; no fix in Atlas |
| SEC-U002 | Mixed-case email vs lowercased login/OAuth | Security | Miss / second user | `auth.py` login/register/OAuth | No implementation in Atlas |
| SEC-U003 | `platform_commission_pct` consumers besides VE | Financial | VE sale path is **proven**: `verified_estate.py` reads `app_settings.pricing.commission_pct`. `platform_config.platform_commission_pct` has **no proven sale consumer**. Unresolved: any *other* product sale path. | `verified_estate.py`; `admin_console.py` | Not “which VE price is live” |
| SEC-U004 | `enable_founder_gate` bool persist | Config | Flag may not save via PUT | `app_settings.py` persist loop | — |
| SEC-U007 | OAuth email-only (no `google_id`) | Identity | Bind by email string | `auth.py` OAuth insert | — |
| SEC-U008 | Password-reset email claim unused | Identity | Reset follows `_id` after email PATCH | `auth.py` reset | — |
| ARCH-U001 | ER node inclusion frontier | Architecture | Registry ≠ inventory | EO 002 SCOPE | Founder |
| GOV-U001 | D161 ↔ Coverage on CEO/Inspector/Explorer | Governance | Second D161 cite | Only KC Coverage proven | Do not convert Coverage statuses to D161 classes |
| GOV-U004 | FG-0 slugs UNMAPPED / EXTERNAL / FUTURE | Governance | HTTP interceptor would miss most | `founder_gate/registry.py` | No FG-2 in Atlas |

### AMBIGUOUS

| ID | Title | Category | Why it matters | Evidence | Notes |
|---|---|---|---|---|---|
| GOV-U005 | MPS family OwnerDocument | Governance | SSOT row vs sibling MPS files | SSOT + `memory/audits/MASTER_PLATFORM_STATE*` | Founder, not Atlas |

### PARTIAL

| ID | Title | Category | Why it matters | Evidence | What is proven vs open |
|---|---|---|---|---|---|
| IDENT-U001 | Three “verified” flags not fully cross-mapped | Identity | Wrong flag may be read as the other | §5; `experience_tiers.py:176`; `kyc.py` | Some readers proven; complete map not done |
| IDENT-U004 | JWT.email after PATCH | Identity | Claim vs DB email diverge | `core_utils.py:23–28`; `deps.py:22` | Lookup-by-`_id` proven; impact beyond session **PARTIAL** |
| SEC-U009 | `/api/founder` outside CSRF prefix | Security | Different CSRF coverage than `/api/admin` | `server.py:138`; `knowledge_center.py:20` | Prefix fact proven. Audited KC ops are GET. Operating Manual is **not** this gap. |

---

## 11. Completed / Closed Investigations

Most identity/security forensics exist as **Cursor conversation reports** (2026-09-22), not as additional KC files. Dates below only when a file or commit records them. Implementation was **not** authorized by those audits.

| Investigation | Status | Date | Source | Conclusion | Implementation required? | CLOSED / HOLD / OPEN |
|---|---|---|---|---|---|---|
| Phase 6 Governance Integration | Audit complete | 2026-09-21 | `docs/audits/PHASE_6_GOVERNANCE_INTEGRATION_AUDIT.md` | Phases 2–5 sit under existing MKG; no parallel Truth Engine | No | CLOSED (audit) |
| Phase 7 Evidence Wiring | Audit complete | 2026-09-22 | `docs/audits/PHASE_7_GOVERNANCE_EVIDENCE_WIRING_AUDIT.md` | Wiring gaps mapped; not implemented | No | CLOSED (audit) |
| ER candidate C01–C13 + SCOPE | Recorded | Commits `f6a4c63`, `8351e17`, `efc746f` (repo) | `enterprise_registry.json` e48/e49; `EXECUTION_ORDER_002_PHASE_SPECS.md` SCOPE + disposition | C05/C06 REGISTERED; rest HOLD/DO_NOT_REGISTER; ER is relationship graph | No new edges | CLOSED (disposition) / HOLD (C01–C03, C07, C08, C10) |
| D161 ↔ Knowledge Coverage | Audit complete | 2026-09-22 (chat) | Cursor forensic | Only KC Coverage consumes Phase 2 counts | No | HOLD |
| PREFLIGHT audit | Audit complete | 2026-09-22 (chat) | Cursor forensic + `PREFLIGHT_GATE.md` | Human protocol + CLI file checks; not HTTP | No | CLOSED (finding) |
| Founder Gate FG-0 semantic | Audit complete | 2026-09-22 (chat) | `founder_gate/*` | Catalog; flag; `enforcement_active` False | No | CLOSED (finding) |
| FG-0 endpoint mapping | Audit complete | 2026-09-22 (chat) | Cursor forensic | LIVE / UNMAPPED / EXTERNAL / FUTURE mix; interceptor insufficient | No | HOLD (slugs remain) |
| App-settings critical mutation + alternate writers | Audit complete | 2026-09-22 (chat) | Cursor forensic | PUT persist + reset/restore/import writers | No | HOLD |
| Identity / privilege source | Audit complete | 2026-09-22 (chat) | Cursor forensic | OWNER / ADMIN / PROTECTED / founder_contact / role / scope are separate | No | CLOSED (map) |
| Admin role durability | Audit complete | 2026-09-22 (chat) | Cursor forensic | PATCH role vs `_enforce_admin_role` 8-case matrix | No | CLOSED (map) |
| `users.email` mutation | Audit complete | 2026-09-22 (chat) | Cursor forensic | Raw PATCH; uniqueness/case; privilege match | No | HOLD (behavior) |
| Auth / email flow continuation | Audit complete | 2026-09-22 (chat) | Cursor forensic | Login/OAuth/register/reset after PATCH | No | HOLD |
| Email verification / identity continuity | Audit complete | 2026-09-22 (chat) | Cursor forensic | Flag/token bound to `_id`; not privilege | No | CLOSED (map) / OPEN IDENT-U001 |
| KC ↔ code forensic / Connection Map / CSR discovery | Audit complete | 2026-09-21–22 (chat) | Cursor forensic | Documented ≠ implemented | No | CLOSED (maps) |
| CSRF no-Origin pass | Finding recorded | — | `server.py:135–137` | Requests without Origin are not treated as browser CSRF | No | CLOSED (by design) — was SEC-U005 |

---

## 12. Decisions / HOLD / CLOSED

### DECISIONS

Supported by committed/canonical evidence only:

- Enterprise Registry is an **evidence-gated relationship graph, not an inventory catalog**. `EXECUTION_ORDER_002_PHASE_SPECS.md` SCOPE.
- C05 Enterprise Health → Evolution Council and C06 CEO Briefing → Evolution Council are **REGISTERED** (e48, e49) with type `engine_feeds_engine`.
- Candidate disposition **alone authorizes no new edge or node**. Same file, CANDIDATE DISPOSITION.
- Artifact types and KC constitution remain MKG / SSOT — Atlas does not change them.
- Property Twin 2D+3D are **both** canonical (CSR / PROPERTY_TWIN_CANONICAL) — do not merge/drop layers.
- FG-0 feature flag **must stay off by default**; module comments forbid intercept in FG-0. `founder_gate/__init__.py`.
- Do not create a second autonomy/approval engine; FN-021 + `admin_approvals` + kill-switch already exist.

### HOLD

- C01, C02, C03, C07, C08, C10 — Founder scope.
- D161 ↔ Coverage second surface.
- FG-0 remaining slugs (no FG-2).
- Email PATCH / case / second-account / verification-after-PATCH **behaviors** (mapped; no fix authorized).
- IDENT-U001 three verified flags.
- `platform_commission_pct` sale consumers **other than** Verified Estate (VE uses `app_settings.pricing.commission_pct`); `enable_founder_gate` persist.
- ER node inclusion beyond SCOPE sentence.

### CLOSED

- Phase 6 / Phase 7 audits (as audits).
- PREFLIGHT = protocol, not HTTP interceptor (finding). GOV-U002.
- FG-0 = catalog, `enforcement_active` False (finding). GOV-U003.
- CSRF: requests without Origin pass the `/api/admin` guard (by design). SEC-U005.
- Identity source separation map.
- Role durability matrix.
- Email verification binding to `_id` (map).
- C05/C06 registration + C04/C09/C11–C13 DO_NOT_REGISTER recording.

---

## 13. Architect Entry Points

| Question | Start here | Canonical source | Runtime source | Relevant audit | Current status |
|---|---|---|---|---|---|
| How does authentication work? | §4, §6.1 | CSR impersonation/CSRF rows | `auth.py`, `deps.py`, `core_utils.py` | Auth/email audits | IMPLEMENTED |
| Who is Founder? | §4.2 | OWNER_EMAIL env; KC docstring | `knowledge_center._require_owner` | Identity source audit | IMPLEMENTED (email+admin) |
| Who can become admin? | §4.1 `_enforce_admin_role` + PATCH + register schema | — | `auth.py:43–65`; `admin_console.py`; `admin_accounts.py` | Role durability | IMPLEMENTED (multiple writers) |
| Where are personal data APIs? | §6.8 | GDPR legal docs | `gdpr.py`, `admin_console` users | — | IMPLEMENTED |
| Where are documents protected? | §3.6, §6.7 | Vault / D015 docs | `property_documents.py`, `property_dna._load_property_for` | — | IMPLEMENTED owner/admin |
| How does HartaBlocuri integrate? | §3.8 | `memory/audits/HARTABLOCURI_INTEGRATION.md` | `hartablocuri.py` + buildings routes | — | IMPLEMENTED + DOCUMENTED |
| Where are financial actions protected? | §6.9 | FG-0 catalog (intent only) | `payments.py`, `wallet.py`, `app_settings` | App-settings / FG-0 | PARTIAL (FG not enforcing) |
| Where is AI allowed to act? | §6.13, §7 | FN-002 / FN-021; `09_AI_GOVERNANCE.md` | `autonomy/loop.py`, concierge, admin AI | Phase 7; FG-0 AI slugs | IMPLEMENTED with kill-switch; not FG |
| What is not implemented? | FG enforcement; PREFLIGHT HTTP; Twilio | `founder_gate/__init__.py`; `PREFLIGHT_GATE.md` | Absent middleware | FG-0 / PREFLIGHT audits | DOCUMENTED only |
| What is currently UNKNOWN? | §10 | — | — | This Atlas | See IDENT/SEC/ARCH/GOV IDs |
| What is the Function Map? | Do not copy | `memory/registries/FUNCTION_MAP.md` | Admin Function Map UI | FN-003 | LIVE registry |
| What is SSOT for a topic? | Look up topic | `memory/registries/SSOT_REGISTRY.md` | KC file serve | — | Active rows only |
| Does a system already exist? | CSR first | `memory/registries/CANONICAL_SYSTEM_REGISTRY.md` | Named runtime column | PREFLIGHT | CANONICAL rows |
| What relationships are proven? | ER JSON + EO 002 | EO 002 PHASE_SPECS | `enterprise_registry.json`; KC `/registry` | C01–C13 | Graph, not inventory |

---

## 14. Change Impact Checklist

Documentation only. Not an automated gate.

1. Identify affected module (this Atlas §3 + Function Map + CSR).
2. Identify canonical source (SSOT row / CSR / Twin canon / EO / MKG).
3. Identify runtime paths (route file, `ALL_ROUTERS`, frontend `App.js`).
4. Identify dependencies (§8 notation: only `──────` is proven).
5. Identify security/data impact (§6 sensitivity + identity §4).
6. Identify existing control (§9) — reuse before adding.
7. Check duplicate architecture risk (CSR “REUSE / EXTEND / CONSOLIDATE”; do not add a second approval/Truth/FG engine).
8. Implement (only if Founder/task authorizes — not this Atlas).
9. Test.
10. Audit (label FACT / UNKNOWN; do not infer edges).
11. Update **this Atlas** (version bump in §15) after material architecture/security findings.
12. Record decision in the **existing** canonical home if architectural (not a new governance file).

PREFLIGHT (`memory/prompts/PREFLIGHT_GATE.md`) remains the human/agent protocol for steps 1–7 before code.

---

## 15. Atlas Change History

### v0.1

Initial consolidation of existing architecture/security forensic work.

Sources used: repository runtime (`backend/`, `frontend/src`), canonical registries under `memory/registries/` and `memory/board/EXECUTION_ORDER_002_PHASE_SPECS.md`, `memory/prompts/PREFLIGHT_GATE.md`, `docs/audits/PHASE_6_*` and `PHASE_7_*`, and the 2026-09-22 read-only forensic series (identity, email, verification, FG-0, PREFLIGHT, ER disposition).

### v0.1 targeted corrections (2026-09-22)

Documentation-only. Admin scope skip-if-None; session route `/api/auth/me`; app-settings `admin`+`operator`; Operating Manual CSRF under `/api/admin`; §10 split (not 22 UNKNOWNs); IDENT-U005 / VE commission narrowed; PRODUCT and Chat/Concierge statuses made conservative. No runtime or governance changes.

---

*End of System Atlas v0.1. Index only.*
