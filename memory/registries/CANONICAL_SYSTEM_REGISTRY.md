# CANONICAL SYSTEM REGISTRY — v1.0

**Artifact Type**: REGISTRY
**Owner**: Fondator (danieligna1@gmail.com)
**Status**: LIVE
**Last update**: Iun 2026 (creat ca livrabil al Governance Hardening post-Task 8R)
**Purpose**: Registrul canonic sistem → implementare. Răspunde la întrebarea „există deja?" ÎNAINTE de orice implementare. Complementar cu `SSOT_REGISTRY.md` (topic → document) și `FUNCTION_MAP.md` (capabilități → status).
**Schema**: Sistem · Implementare canonică · Source of Truth · Rute API · Consumer frontend · Docs KC · Status · Verificat ultima dată

## Regula fundamentală
Înainte de a crea ORICE (rută, endpoint, colecție, pagină React, provider, serviciu, job, sistem de backup/config, pagină admin, feature flag, sistem de design/documentare): caută AICI + în `SSOT_REGISTRY` + `MASTER_PLATFORM_STATE` + cod. Dacă există echivalent → REUSE / EXTEND / CONSOLIDATE. O a doua implementare cere justificare explicită + aprobare canonică (Fondator). Zero fabricație: rândurile de mai jos provin din stare verificată (Task 7/8/8R + fix impersonare), nu din presupuneri.

## Entries

| Sistem | Implementare canonică | Source of Truth | Rute API | Consumer frontend | Docs KC | Status | Verificat |
|---|---|---|---|---|---|---|---|
| Design Tokens (runtime) | `backend/routes/design_studio.py` | `db.design_tokens {_id:"active"}` (PRE-EXISTENT, nu „nou") | `/api/admin/design-studio/*` | `contexts/DesignTokensProvider.jsx` → CSS vars `--pm-*`; UI: `DesignStudioPage.jsx` (`/admin/design-studio`) | EO_046 §2 | CANONICAL | Task 8R (Iun 2026, 124/124 teste) |
| ~~Design Tokens (Task 8 path)~~ | ~~`routes/design_tokens.py` + `DesignTokensPage.jsx`~~ | ~~`{_id:"design_tokens"}`~~ | ~~`/api/admin/design-tokens`~~ | — | EO_046 §1 | **REMOVED** (dead write path; migrare reversibilă în `migration_backups`) | Task 8R |
| Snapshot config (canonic) | `backend/routes/admin_console.py` (SNAPSHOT_PARTS: cms, settings, trust_weights, presets, design_tokens, pages, site_menu, feature_config) | `db.admin_snapshots` | `/api/admin/snapshots*` | `AdminConsolePage` | EO_046 §4 | CANONICAL | Task 8R |
| Portabilitate config JSON | `backend/routes/config_io.py` (export/import fișier, dry-run implicit, no-false-success) | fișier JSON generat din runtime | `/api/admin/config/export`, `/api/admin/config/import` | `ConfigIOPage.jsx` (`/admin/config-io`) | EO_046 §3 | CANONICAL (rol: portabilitate, NU snapshot) | Task 8R |
| Snapshot automat app_settings | `backend/routes/settings_snapshots.py` (zilnic 04:00) | `db.app_settings_snapshots` | `/api/admin/app-settings/snapshots*` | AppSettings admin | EO_046 §4 | CANONICAL (scoped DOAR app_settings) | Task 8R |
| Disaster recovery full-DB | `backend/routes/admin_backups.py` (mongodump zilnic) | fișiere backup pe disc | `/api/admin/backup*` | Admin dashboard card BACKUP DB | EO_046 §4 | CANONICAL (nivel 5, ultimul resort) | Task 8R |
| Precedență backup/restore | Runtime → admin_snapshots → settings_snapshots → config_io → admin_backups; `pages_versions` NU se restaurează | EO_046 §4 | — | — | EO_046 §4 + MASTER_PLATFORM_STATE | CANONICAL | Task 8R |
| Preview pagini (draft) | `pages_registry.py::admin_preview` (non-mutant) + `PreviewOverlay` în `PageRegistryPage.jsx` | `db.pages` (draft/live) | `GET /api/admin/pages/{key}/preview` | overlay modal în admin | EO_046 §5 | CANONICAL (terminologie onestă: simulare post-publish) | Task 8R |
| Pages / SEO / H1 | `backend/routes/pages_registry.py` (Task 7) | `db.pages` + `db.pages_versions` (istoric append-only) | `/api/admin/pages*`, `/api/public/pages/*` | `PageRegistryPage.jsx`, `useDynamicSEO` | EO_044 | CANONICAL | Task 7 |
| Renewal reminder email | `backend/routes/renewal_reminders.py` (fereastră 4.5–7.5 zile, idempotent) | `db.renewal_reminders` (kind `basic_expiry_7d`) | `/api/admin/renewal-reminders/*` + job `renewal_reminder_daily` 09:15 | — (email) | EO_046 §6 | CANONICAL | Task 8R |
| Copilot renew nudge | `propbenefits/ai_agents.py` + `copilot.py` (coordonat 24h cu email prin ledger comun, kind `copilot_renew_nudge`) | `db.renewal_reminders` | `/api/client/copilot` (dashboard) | PropBenefits Copilot UI | EO_046 §6 | CANONICAL | Task 8R |
| Scheduler / cron jobs | `server.py` (`scheduler.add_job`, id unic + `replace_existing=True`) + `email_sequences.py` | registrul APScheduler — **72 job-uri** (70+2) | — | — | EO_046 §7 | CANONICAL (numără ÎNAINTE să declari „job nou") | Task 8R |
| Navigație admin (sidebar) | `AdminLayoutMetronic.jsx` (grupuri + intrări) | array-urile de meniu din fișier | — | tot admin-ul | EO_046 §1.9 | CANONICAL (o intrare per funcție reală; fără intrări moarte) | Task 8R |
| Impersonare admin („View as") | `backend/routes/impersonation.py` (GDPR-logged, TTL 2h, stash cookie) | `db.impersonation_logs` | `/api/admin/impersonate`, `/api/admin/stop-impersonation`, `/api/admin/impersonation-logs` | banner roșu + `QuickProfileSwitch` | acest registru | CANONICAL | Fix Iun 2026 |
| Conturi demo quick-switch | ALLOWLIST server-side `DEMO_IMPERSONATION_ACCOUNTS` în `impersonation.py` (14 emailuri @propmanage.io, creare idempotentă, `is_demo_account:true`) | `db.users` (emailurile din allowlist) | `POST /api/admin/impersonation/ensure-demo-target` | `QuickProfileSwitch` în `AdminLayoutMetronic.jsx` | acest registru | CANONICAL — **INTERZIS fallback pe useri reali** (incident prod 24 Aug 2026) | Fix Iun 2026 |
| Conturi demo sub-admin | `backend/routes/demo_accounts.py` + `sub_admin_seed.py` (5 emailuri fixe, master code) | `db.users` (`is_demo_sub_admin`) | `/api/admin/demo-accounts/*` | Demo Accounts admin | acest registru | CANONICAL (familie SEPARATĂ de quick-switch) | pre-existent |
| Audit admin | `db.admin_audit_log` + view unificat Config History | `db.admin_audit_log` | `GET /api/admin/config-history` (allowlist entity_type) | Config History UI | EO_046 | CANONICAL (NU crea al doilea sistem de audit) | Task 8R |
| Scope sub-admini | `backend/middleware_scope.py` SCOPE_RULES | regex → scope map în fișier | toate `/api/admin/*` | — | EO_046 §8 | CANONICAL — orice endpoint admin NOU trebuie mapat | Task 8R |
| Anti-CSRF admin | middleware `_csrf_origin_guard` în `server.py` + header `X-PM-Client` (axios global în `auth.js`) | `server.py` | mutații `/api/admin/*` | toate apelurile admin | EO_046 §8 | CANONICAL | Task 8R |
| Property Twin (umbrelă 2D+3D) | taxonomie: `PROPERTY_TWIN_CANONICAL_v1.0.md`; cod: `operator_twins.py` (2D) + `digital_twin.py` (3D) | `db.twins` (2D) + `db.digital_twin_projects/models/plans/pins` (3D) — ambele ancorate de `property_id` | `/api/properties/{id}/twin`, `/spaces`, `/digital-twin`; `/api/digital-twin/*` | `ClientTwinViewer.jsx` (`PropertyTwinModal` 2D/3D), `DigitalTwinViewer.jsx` | `PROPERTY_TWIN_CANONICAL_v1.0.md` | CANONICAL — NU migrare/merge/drop între straturi | P0/P1/P0.1 (Aug 2026, 15/15 teste) |
| Property Anchor (Twin↔property) | `digital_twin.py::_resolve_property_anchor` + `_kg_link_twin` | `digital_twin_projects.property_id` + `property_link_status` | `POST /api/digital-twin/projects`, `POST /api/operator/digital-twin/clients/{id}/projects` (property_id OBLIGATORIU), `PATCH /projects/{id}/property`, `POST /api/admin/digital-twin/backfill-property-links` | selector CreateModal client + `OperatorDigitalTwin.jsx` | `PROPERTY_TWIN_CANONICAL_v1.0.md` §2 | CANONICAL — anti-misassignment (owner-verified), ZERO auto-assign | iter201/iter203 |
| Property DNA (knowledge layer) | `property_dna.py` | proiecție read-only (Capability Map) | `GET /api/properties/{id}/dna` | DNA UI | `STRATEGIC_AUDIT_PROPERTY_TWIN_2026-08-28.md` §2 | CANONICAL — motoarele AI citesc DNA, nu structura fizică | Aug 2026 |
| Knowledge Graph (relații) | `kg/links.py`, `routes/kg.py` | `db.entity_links` | `kg.link/unlink/links_of` (admin) | — | `PROPERTY_TWIN_CANONICAL_v1.0.md` §3 | CANONICAL — relațiile canonice (nu FK împrăștiate) | Aug 2026 |
| Trust Model 015 (provenance) | `source`/`confidence`/`verification_status` pe assets/DNA/`digital_twin_models` | câmpuri pe documente | via PATCH model/asset | Trust badges | `PROPERTY_TWIN_CANONICAL_v1.0.md` §4 | CANONICAL — INFERRED→DOCUMENTED→VERIFIED; AI nu setează verified | Aug 2026 |

## Cum adaugi un rând
1. Verifică că sistemul NU are deja rând (sau că rândul existent trebuie actualizat, nu duplicat).
2. Completează DOAR din fapte verificate (cod/DB/teste), cu referință la task-ul care a verificat.
3. Statusuri permise: CANONICAL · LEGACY · DEPRECATED · CONFLICT · REMOVED.
4. La CONFLICT: aplică Protocolul de Conflict din `prompts/PREFLIGHT_GATE.md` — STOP + decizie Fondator.
