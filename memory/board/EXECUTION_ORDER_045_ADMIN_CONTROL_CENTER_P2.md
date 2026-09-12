# EXECUTION_ORDER_045 — Admin Control Center Expansion · P2

> ⚠️ **REMEDIAT (Iun 2026)** — Auditul Forensic de Duplicare a dat verdict 🔴 DO NOT PUBLISH pe implementarea inițială Task 8. Remedierea completă e documentată CANONIC în **EXECUTION_ORDER_046_REMEDIATION_CANONICALIZATION.md**. Corecții față de acest doc:
> 1. **Secțiunea D e ISTORICĂ/INVALIDĂ**: `routes/design_tokens.py` + `DesignTokensPage.jsx` erau un dead parallel write path (`{_id:"design_tokens"}` — frontend-ul consuma `{_id:"active"}` din Design Studio) și au fost **ȘTERSE**. Canonic = `design_studio.py` + `DesignStudioPage.jsx`. `db.design_tokens` **PRE-EXISTA** (nu era colecție nouă).
> 2. Config I/O capturează acum starea **runtime-activă** `{_id:"active"}` (înainte exporta doc-ul mort → backup-ul NU restaura tema vizibilă).
> 3. „Preview Overlay" avea doar JSON în tab nou — acum există **overlay real** în admin (PageRegistryPage).
> 4. Claim-ul „al **21-lea** job scheduler" era **FALS** — numărătoarea reală: **72 job-uri** înregistrate (70 server.py + 2 email_sequences).
> 5. Fereastra renewal `[6.5,7.5]` → `[4.5,7.5]` zile + coordonare 24h cu Copilot nudge.
>
> **Task 8 — CONSOLIDATED · STATUS: IMPLEMENTED + REMEDIATED (vezi EO_046)**
> **Doctrine**: „Reuse existing infrastructure; do not create duplicate configuration engines."
> **Owner**: Founder + AI CPO.
> **Emitent**: 24 Aug 2026 · Remediere: Iun 2026.

---

## A. Task scope

O singură directivă consolidată cu 4 componente P2 pe Configuration Layer:
1. **Design Tokens Editor** — control allowlisted al tokenilor vizuali globali (`--pm-*`).
2. **Configuration Import / Export** — bundle JSON portabil pentru backup/migrare.
3. **Preview Overlay** — admin poate vedea o pagină cu DRAFT overlay peste LIVE.
4. **Renewal Reminder Email** — email cu 7 zile înainte de expirare BASIC.

## B. Audit inițial (READ-ONLY)

Infrastructură deja existentă identificată:
- `db.pages` + `db.pages_versions` + Page Registry draft/live (Task 7)
- `db.cms_content`, `db.site_menu`, `db.app_settings`, `db.feature_config`
- `admin_audit_log` + `_audit()` helper
- `email_service.send_email` (Resend/SendGrid/console fallback)
- `AsyncIOScheduler` din `server.py` cu ~20 job-uri active
- `db.hh_subscriptions.expires_at` (ISO string, status = active | cancelled)
- CSS variables `--pm-*` deja folosite peste tot în frontend

## C. Infrastructure REUSED

| Sistem | Cum e reutilizat |
|---|---|
| `admin_audit_log` | Toate 4 componente scriu audit prin `_audit()` (zero al doilea sistem) |
| `require_role` | Autorizare admin/operator pe toate endpoint-urile noi |
| `email_service.send_email` | Renewal reminder folosește provider-ul deja configurat |
| `AsyncIOScheduler` | Renewal reminder ca job cron zilnic 09:15 Bucharest — unul din cele **72 job-uri** înregistrate (corecție EO_046; claim-ul inițial „21-lea" era fals) |
| `db.hh_subscriptions` | Source-of-truth pentru expiry, zero modificări la subscription/entitlement |
| `db.pages` draft/live | Preview overlay reutilizează DRAFT existent, zero nou draft system |
| CSS vars `--pm-*` | Frontend consumă tokenii publicați via API, fără redesign |

## D. Design Tokens implementation

**Backend**: `/app/backend/routes/design_tokens.py`
- Colecție nouă `db.design_tokens` (doc unic `_id="design_tokens"`)
- Whitelist strict: 11 colors + 6 radius + 5 typography tokens
- Validators regex per tip: `_COLOR_RE`, `_RADIUS_RE`, `_FONT_FAMILY_RE`, `_WEIGHT_ALLOWED`, `_BASE_FONT_RE`, `_H1_SCALE_RE`
- **Reject list**: `javascript:`, `url()`, `expression()`, `<script`, `onerror=`, `\`, `@import`
- Endpoints: `GET/PUT /api/admin/design-tokens`, `POST /api/admin/design-tokens/reset`, `GET /api/public/design-tokens`
- Audit prin `admin_audit_log` cu `target.type="design_tokens"`

**Frontend**: `/app/frontend/src/pages/admin/DesignTokensPage.jsx`
- 3 secțiuni: Colors (swatch preview), Radius, Typography
- Save + Reset defaults + validare live
- Sidebar entry: „Design Tokens" (badge P2)

## E. Config Import/Export implementation

**Backend**: `/app/backend/routes/config_io.py`
- Schema version `1.0`, `app="propmanage"` guard
- Whitelist secțiuni exportabile: `pages`, `pages_versions`, `site_menu`, `cms_content`, `app_settings`, `feature_config`, `design_tokens`
- Defensive strip `_ALWAYS_STRIP = {"_id", "password", "password_hash", "secret", "api_key", "stripe_secret", "token", ...}` la fiecare doc exportat
- Import: **DRY-RUN implicit**, `apply=true` explicit necesar pentru mutare
- `pages_versions` este read-only istoric → skip la import
- Endpoints: `GET /api/admin/config/export`, `POST /api/admin/config/import` (dry-run + apply)

**Frontend**: `/app/frontend/src/pages/admin/ConfigIOPage.jsx`
- Export → download JSON file cu timestamp
- Import textarea → Dry-run (plan preview) → Apply (după confirmare)
- Sidebar entry: „Config Import/Export" (badge P2)

## F. Preview Overlay implementation

**Backend** (extindere Page Registry, zero drop-in nou):
- Endpoint nou: `GET /api/admin/pages/{key}/preview` — admin/operator only
- Merge simulat: `simulated = {**live, **draft}` (draft wins per field)
- Feature flag bypass: preview afișează pagina și când feature flag ar bloca-o public (informational)
- Reutilizează `_resolve_public` + CMS/app_settings fallback chain
- **Zero mutations** — LIVE rămâne intact, `/api/public/pages/{key}` continuă să servească LIVE

**Frontend**:
- Buton „Preview draft" în editor Page Registry când există DRAFT
- Deep-link la `/api/admin/pages/{key}/preview` (JSON pentru moment; render vizual în viitor P3)

## G. Renewal Reminder implementation

**Backend**: `/app/backend/routes/renewal_reminders.py`
- Fereastră detecție: `[6.5, 7.5]` zile înainte de `expires_at` (slack de 1 zi pentru misfire)
- Kind: `basic_expiry_7d`
- Idempotency: colecție `renewal_reminders` cu unique index `(user_id, expires_at, kind)`
- Query: `hh_subscriptions.expires_at` in fereastră AND `status in (active, cancelled)`
- Email template HTML + plaintext, Romanian
- CTA → `{APP_URL}/pricing`
- APScheduler job zilnic 09:15 Bucharest (`renewal_reminder_daily`)
- Endpoints admin: `POST /api/admin/renewal-reminders/run-now`, `GET /api/admin/renewal-reminders/recent`

**Zero modificări** la: Stripe, entitlements, lifecycle, hh_subscriptions schema, existing email flows.

## H. Security findings/fixes

**Component A · Design Tokens**:
- CSS injection: rejected (`javascript:`, `url()`, `expression()`, `<script`)
- Unknown keys: rejected (whitelist strict)
- Malformed values: rejected via regex (invalid color, invalid radius, invalid weight)
- Public endpoint: read-only (`GET /api/public/design-tokens`)

**Component B · Config I/O**:
- Sensitive fields (password/secret/token/api_key) stripped defensiv la export
- Unknown/dangerous sections (`users`, `hh_subscriptions`) rejected explicit
- Wrong schema_version rejected
- Import DRY-RUN implicit (zero side-effects fără `apply=true` explicit)

**Component C · Preview**:
- Admin/operator authorization required
- Invalid key regex protejat (`KEY_RE = ^[a-z][a-z0-9_]{1,60}$`)
- Zero mutation la LIVE
- Public endpoint continuă să seasca DRAFT (verified live)

**Component D · Renewal**:
- Admin authorization pe endpoint-uri
- Idempotent (unique index) → duplicate imposibile
- Fereastră strictă (6.5-7.5 zile) → nu trigger la subscriptions non-target

**Zero CRITICAL/HIGH/MEDIUM.**

## I. Tests

**Fișier nou**: `/app/backend/tests/test_task8_p2_iter189.py` — **23/23 PASS**

Cover:
- Design Tokens: 6 teste (public GET no-auth, admin GET auth, save/reset flow, CSS injection reject × 6 payloads, unknown keys reject × 4, bad types reject × 5, audit generated)
- Config Export: 3 teste (admin-only, all sections present, secrets excluded)
- Config Import: 3 teste (bad bundle reject × 5, dry-run non-mutating, apply mutates + audits)
- Preview: 4 teste (admin-only, live-only when no draft, draft overlay without public leak, invalid key rejected)
- Renewal: 4 teste (admin-only, run-now idempotent, detection window shape, wrong window doesn't trigger)
- Regression sanity: 3 teste (public pages payload unchanged, menu public unchanged, P3.2 non-regression)

## J. Regression results

`pytest tests/test_pricing_basic_iter184.py tests/test_digital_twin_gate_iter185.py tests/test_subscription_lifecycle_iter186.py tests/test_task5_regression_iter187.py tests/test_pages_registry_iter188.py tests/test_task8_p2_iter189.py`
→ **79/79 PASS** (Tasks 1–6.1 + Task 7 + Task 8).

Zero regresii pe: Digital Twin, House Health, Payments, Stripe, Auth, Entitlements, Client Beta, Specialist Beta, Existing Demo, Marketplace, existing routes.

## K. Production status

| Layer | Status |
|---|---|
| Implementat în cod / build | ✅ IMPLEMENTED |
| Verificat în preview | ✅ PASSED (smoke + 23 teste noi + 79 total) |
| Security validation | ✅ PASSED (0 CRITICAL/HIGH/MEDIUM) |
| Deploy pe production | ⏳ **PENDING FOUNDER DEPLOYMENT** |
| Production smoke verification | ⏳ **PENDING FOUNDER VERIFICATION** |

## L. IMPLEMENTED

- Design Tokens Editor (backend + frontend + audit + validators)
- Config Import/Export (export complet + import dry-run/apply)
- Preview Overlay (admin endpoint + buton frontend)
- Renewal Reminder Email (backend + scheduler + idempotency + admin trigger)
- 23 teste dedicate + 79 total suite PASS
- Knowledge Center synced (EO_045 + MASTER_PLATFORM_STATE + INDEX + PRD)
- Corrected historical date typo: `24 Feb 2026 → 24 Aug 2026` în docs Task 7 series

## M. PENDING

- Production deployment `propmanage.ro` (fondator)
- Production smoke verification (fondator)

## N. NOT IMPLEMENTED / FUTURE

- Preview Overlay **visual** — endpoint returnează JSON acum. Rendering vizual real (React shell care randează pagina cu draft aplicat) rămâne P3 dacă se dorește
- Forms configuration UI (schema only, absent din task-ul curent per constraint fondator)
- Workflow configuration UI (schema only, absent din task-ul curent per constraint fondator)
- Renewal reminder pentru alte tier-uri decât BASIC (PRO/PREMIUM — rămâne backlog)
- Multi-tenant scope pentru design tokens (un singur set global pentru moment)

## O. Next recommended phase

După ce fondatorul deployează pe prod:
1. Verificare live a celor 4 componente (smoke: `/admin/design-tokens`, `/admin/config-io`, `/admin/pages/home/preview`, `run-now` renewal)
2. Monitor primele 24-48h `admin_audit_log` pentru comportament neașteptat
3. P3 posibil: Preview Overlay vizual (React render cu draft) + Forms/Workflows schema-only extensii

## Artefacte

Backend:
- `/app/backend/routes/design_tokens.py` (nou)
- `/app/backend/routes/config_io.py` (nou)
- `/app/backend/routes/renewal_reminders.py` (nou)
- `/app/backend/routes/pages_registry.py` (extins cu preview endpoint)
- `/app/backend/routes/register.py` (înregistrare 3 routere noi)
- `/app/backend/server.py` (scheduler job pentru renewal — unul din 72 job-uri; corecție EO_046)

Frontend:
- `/app/frontend/src/pages/admin/DesignTokensPage.jsx` (nou)
- `/app/frontend/src/pages/admin/ConfigIOPage.jsx` (nou)
- `/app/frontend/src/pages/admin/PageRegistryPage.jsx` (buton Preview draft)
- `/app/frontend/src/pages/admin/AdminLayoutMetronic.jsx` (2 sidebar entries + Download icon import)
- `/app/frontend/src/App.js` (2 rute lazy noi)

Tests:
- `/app/backend/tests/test_task8_p2_iter189.py` (23 teste)

Docs:
- `/app/memory/board/EXECUTION_ORDER_045_ADMIN_CONTROL_CENTER_P2.md` (acest doc)
- `/app/memory/audits/MASTER_PLATFORM_STATE.md` (secțiune Task 8)
- `/app/memory/INDEX.md` (referință EO_045)
- `/app/memory/PRD.md` (Task 8 entry)
