# EXECUTION_ORDER_046 — Remediere & Canonicalizare Task 8 (Admin Config/Design)

> **STATUS: IMPLEMENTED · SECURITY VALIDATED · Preview verificat E2E**
> **Tip**: P0 / Release-blocker remediation (răspuns la verdictul 🔴 DO NOT PUBLISH al Auditului Forensic de Duplicare)
> **Owner**: Founder + AI CPO · **Emitent**: Iun 2026
> **Doc înlocuit parțial**: EXECUTION_ORDER_045 (secțiunile D, F-frontend, H-A, I, Artefacte — vezi banner-ul de remediere din EO_045)

---

## 1. BLOCKERELE ORIGINALE (audit forensic) — toate ÎNCHISE

| # | Blocker | Status |
|---|---|---|
| 1 | Design Tokens avea un dead parallel write path (`routes/design_tokens.py` → `{_id:"design_tokens"}`) | ✅ FIXED — fișier ȘTERS, path unic canonic |
| 2 | `db.design_tokens` tratat fals ca NOU (pre-exista, folosit activ de Design Studio) | ✅ FIXED — clasificat corect PRE-EXISTENT, doc corectat |
| 3 | Config I/O exporta/importa `{_id:"design_tokens"}` (mort) în loc de `{_id:"active"}` (runtime) | ✅ FIXED — citește/scrie EXCLUSIV starea runtime-activă |
| 4 | 4 sisteme paralele de config/restore fără precedență definită | ✅ FIXED — model de precedență documentat (secțiunea 4) |
| 5 | „Preview Overlay" fals etichetat (JSON în tab nou, zero renderer) | ✅ FIXED — overlay REAL în admin (modal cu H1/subtitle/SERP/OG, non-mutant) |
| 6 | Coordonare Renewal email ↔ PropBenefits Copilot nudge inexistentă | ✅ FIXED — ledger comun idempotent, fereastră 24h |
| 7 | Claim fals „al 21-lea scheduled job" | ✅ FIXED — numărătoare reală: **72 job-uri** (70 în server.py + 2 email_sequences), 0 duplicate |
| 8 | Documentația nu recunoștea că `db.design_tokens` pre-exista | ✅ FIXED — corectat în EO_045/MASTER_STATE/PRD |
| 9 | 4 intrări design în sidebar (una moartă) | ✅ FIXED — intrarea moartă „Design Tokens" eliminată; ruta redirectează la Design Studio |

## 2. SOURCE OF TRUTH — Design Tokens (canonic, unic)

| Aspect | Canonic |
|---|---|
| SOURCE OF TRUTH | `db.design_tokens` doc `{_id: "active"}` — `{tokens, preset_id, updated_at}` |
| WRITE PATH (unic) | `routes/design_studio.py` (PUT /tokens, /reset, /presets/apply, /palette-cascade) |
| READ RUNTIME | `GET /api/admin/design-studio/tokens` (public read, fără date sensibile) |
| FRONTEND CONSUMER | `contexts/DesignTokensProvider.jsx` → CSS vars `--pm-*` pe `<html>` |
| ADMIN UI | `pages/admin/DesignStudioPage.jsx` (`/admin/design-studio`) |
| AUDIT | `admin_audit_log` cu `target.type="design_tokens"` (vizibil în Config History) |
| BACKUP CANONIC | Admin Console Snapshots (`db.admin_snapshots`, partea `design_tokens`) |
| PORTABILITATE JSON | `routes/config_io.py` export/import — capturează `{_id:"active"}` |

**Capabilități portate din dead-path înainte de ștergere** (nimic pierdut):
- Sanitizare anti CSS/JS injection (`_reject_dangerous_deep`) pe TOATE write path-urile: PUT tokens, preset apply, palette-cascade, config import, snapshot restore
- Audit unificat în `admin_audit_log` pe update/reset/preset_apply/palette_cascade
- Validare hex pe palette-cascade (400 la non-hex)

**ȘTERSE** (dovedit redundante — zero consumatori runtime):
- `/app/backend/routes/design_tokens.py` (router + public router, dezînregistrate din register.py)
- `/app/frontend/src/pages/admin/DesignTokensPage.jsx`
- Doc mort `{_id:"design_tokens"}` din `db.design_tokens` — **migrare reversibilă** cu backup complet în `db.migration_backups` (`migration="remove_dead_design_tokens_doc"`, pre=2 → post=1 doc, `_id:"active"` intact)
- Sidebar entry „Design Tokens"; ruta `/admin/design-tokens` → redirect 1:1 la `/admin/design-studio` (bookmarks safe)

## 3. CONFIG I/O — rol clarificat

`config_io.py` = **strat de PORTABILITATE JSON brut** (migrare între medii, backup fișier descărcabil). RETAINED pentru că:
- e singurul mecanism de export/import cross-environment pentru pages/menu/CMS/settings/features/tokens
- dry-run implicit + apply explicit + audit + secrets stripped (acum RECURSIV, nested keys incluse)

Corecții aplicate:
- secțiunea `design_tokens` citește/scrie `{_id:"active"}` (forma `{tokens, preset_id}`); bundle-urile vechi fără cheia `tokens` sunt respinse cu 400
- **NO false-success**: validare completă pre-apply (dry-run intern) + per-secțiune try/except; dacă o secțiune eșuează la apply → HTTP 500 cu `failed_sections` + ce s-a aplicat; UI-ul afișează eroarea (nu raportează succes)
- sanitizare `_reject_dangerous_deep` pe TOATE secțiunile importate

## 4. PRECEDENȚĂ BACKUP/RESTORE (model deterministic)

| Nivel | Sistem | Scop | Colecție |
|---|---|---|---|
| 1 · RUNTIME | Design Studio / Page Registry / CMS / App Settings / Feature Config | sursa adevărului live | colecțiile respective |
| 2 · SNAPSHOT CANONIC | **Admin Console Snapshots** (create/restore manual, named) | bookmark-uri de stare config | `admin_snapshots` |
| 3 · SNAPSHOT AUTOMAT scoped | `settings_snapshots.py` (zilnic 04:00, DOAR app_settings) | plasă de siguranță app_settings | `app_settings_snapshots` |
| 4 · PORTABILITATE | `config_io.py` export/import JSON | migrare între medii | fișier JSON (fără storage propriu) |
| 5 · DISASTER RECOVERY | `admin_backups.py` (mongodump zilnic) | full-DB restore | fișiere backup |

Reguli de conflict:
- **Runtime-ul e mereu autoritar** — snapshot/import nu „câștigă" decât când adminul execută explicit restore/apply.
- Restore-ul canonic (nivel 2) scrie DIRECT în runtime (nivel 1) și e auditat; extins acum cu părțile `design_tokens` (runtime-active), `pages`, `site_menu`, `feature_config`.
- `pages_versions` = istoric append-only, NU se restaurează niciodată (regulă comună nivel 2 + 4).
- Restore parțial eșuat → HTTP 500 cu `restored` + `failed` per parte (no false-success).

## 5. PREVIEW — terminologie onestă + implementare reală

- Backend: `GET /api/admin/pages/{key}/preview` (nemodificat semantic, non-mutant); fix: `feature_flag_would_block` calculat REAL (înainte era hardcodat `False`).
- Frontend: butonul „Preview draft" NU mai deschide JSON în tab — deschide un **overlay real** în admin (`PreviewOverlay` în PageRegistryPage.jsx): banner „MOD PREVIEW · simulare post-publish · LIVE neatins", H1 + subtitle randate, snippet Google SERP, card Open Graph, vizibilitate desktop/mobil, avertisment feature-flag, închidere sigură. Zero mutații (doar GET).

## 6. RENEWAL ↔ COPILOT — coordonare idempotentă 24h

- Ledger comun: `db.renewal_reminders` (kind diferențiază: `basic_expiry_7d` = email; `copilot_renew_nudge` = nudge in-app servit, idempotent/zi via unique index existent).
- Copilot (copilot.py): când servește `renew_subscription` → scrie ledger-ul.
- Email tick: dacă nudge-ul Copilot a fost servit în ultimele 24h → **amână** (skip fără ledger de sent → re-încearcă a doua zi). Fereastra a fost lărgită `[6.5,7.5] → [4.5,7.5]` zile ca amânarea să nu scoată email-ul din fereastră.
- Copilot: dacă email-ul de renewal a fost trimis în ultimele 24h → nu generează candidatul `renew_subscription` în acea zi.
- Ambele sisteme rămân funcționale; niciun mesaj de renewal duplicat în aceeași fereastră de 24h.

## 7. SCHEDULER — numărătoare reală

- **72 job-uri înregistrate**: 70 în `server.py` (`scheduler.add_job`, toate cu id unic + `replace_existing=True`) + 2 în `email_sequences.py` (`email_drip_reminders`, `email_weekly_newsletter`).
- 0 duplicate, 0 orphan detectate. `renewal_reminder_daily` (09:15 Bucharest) e UNUL dintre cele 72 — claim-ul „al 21-lea job" din EO_045 era fals.

## 8. SECURITY AUDIT post-remediere (agent dedicat) + fixuri

| ID | Sev | Finding | Fix aplicat |
|---|---|---|---|
| SEC-001 | HIGH | Sub-adminii cu scope limitat puteau muta config prin endpoint-uri neacoperite de middleware-ul de scope | `middleware_scope.py` extins: `/api/admin/config*` + `/api/admin/snapshots` → **general**; `/api/admin/pages` + `/api/admin/config-history` → **frontend**; `/api/admin/renewal-reminders` → **ops** |
| SEC-002 | MED | CSRF pe mutații admin bodyless (cookie SameSite=None) | Middleware CSRF guard în `server.py`: mutațiile `/api/admin/*` cu header `Origin` prezent cer origin permis **ȘI** header custom `X-PM-Client: propmanage-app` (setat global de axios în `auth.js`; formularele HTML nu pot seta headere custom; fetch cross-site credentialed pică la preflight). Cereri fără Origin (curl/server/tests) nu sunt vector de browser și trec. Notă infra: ingress-ul de preview rescrie Origin — de aceea apărarea primară e header-ul custom. |
| SEC-003 | LOW | Sanitizare inconsistentă pe write path-uri | `_reject_dangerous_deep` aplicat uniform: preset apply, snapshot restore (design_tokens), toate secțiunile config import |
| Hardening | P3 | `_strip_sensitive` doar top-level | făcut RECURSIV (nested dicts + liste) |

## 9. TESTE (post-remediere)

- `tests/test_task8_p2_iter189.py` **rescris**: 29 teste — design studio canonic (public read, PUT admin, CSS injection reject, audit în config-history, rute legacy 404), config I/O (export runtime shape, import dry-run/apply/wrong-shape/injection), snapshot canonic capture→restore design tokens (E2E real), preview (non-mutant, flag honest), renewal (idempotent), CSRF guard, scope map.
- Regresie completă `iter181–189`: **124/124 PASS** (PTR v1/v2, entitlements, pricing, DT gate, lifecycle, nudges, pages registry, task8 remediat).
- E2E browser verificat: token schimbat în Design Studio → `--pm-primary` se schimbă LIVE pe homepage-ul public → reset OK; redirect `/admin/design-tokens` → `/admin/design-studio` OK; Preview Overlay randează draft-ul real și se închide sigur; draft discard OK.

## 10. INTEGRITATE DATE

- Migrare: `scripts/migration_remove_dead_design_tokens_doc.py` — pre 2 docs → post 1 doc; backup complet în `migration_backups`; `_id:"active"` verificat intact; rollback documentat în script.
- Zero pierderi: users/properties/subscriptions/pages/cms neatinse (verificat prin regresia 124/124).

## 11. NU S-A SCHIMBAT (No-Break Contract respectat)

Auth, admin login, property flows, Demo, Client Beta, Specialist Beta, Digital Twin, marketplace, dashboards, rute existente, permisiuni operator, Stripe/entitlements/lifecycle, App.js structură (doar redirect-ul 1:1), schema colecțiilor existente.
