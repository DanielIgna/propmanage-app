# TENANT FOUNDATION PLAN — Sprint 3 · Platform Core Initiative
*Generat: 2026-06 · Status: INFRASTRUCTURĂ LIVRATĂ (val 0) — FĂRĂ migrare de date*

## 1. Obiectiv
Pregătirea PropManage pentru francize (multi-tenant). Fiecare francizat = un **tenant**
cu propriile date de business, dar cu platforma (XOS, taxonomii, reguli) partajată de la HQ.

## 2. Ce s-a livrat în acest sprint (val 0 — infrastructură)
| Componentă | Fișier | Descriere |
|---|---|---|
| Registru tenants | colecția `tenants` | slug unic, name, plan (hq/franchise), status (draft/active/suspended), domain, regions, branding |
| Nucleu tenancy | `/app/backend/tenancy.py` | `DEFAULT_TENANT="main"`, rezolvare tenant per request, clasificarea colecțiilor, raport acoperire |
| API admin | `/app/backend/routes/tenants.py` | GET/POST `/api/admin/tenants`, PATCH `/{slug}`, GET `/coverage` (guvernanță) |
| API public | `GET /api/public/tenant-context` | tenantul rezolvat pentru requestul curent (consumat de frontend în val 2) |
| Seed idempotent | startup `server.py` | tenantul HQ `main` (plan=hq, activ, neștergibil) + index unic pe slug |
| Centralizare | `leads_store` / `settings_store` / `ai_session_store` | toate importă `DEFAULT_TENANT` din `tenancy.py` (o singură sursă de adevăr) |

## 3. Rezolvarea tenantului (ordinea de precedență)
1. **Header `X-Tenant-ID`** — validat contra registrului (doar tenants `active`); necunoscut → fallback `main` + warning în log
2. **`user.tenant_id`** — după val 1, fiecare utilizator e legat de un tenant la înregistrare
3. **Fallback `main`** — HQ; comportamentul actual rămâne 100% neschimbat

Viitor (val 3): rezolvare pe subdomeniu (`brasov.propmanage.ro` → tenant `brasov`), setată la nivel de reverse-proxy → header.

## 4. Clasificarea celor ~210 colecții (3 tiere)
Definită în `tenancy.py` (`classify_collection`); raport live: `GET /api/admin/tenants/coverage`.

### T1 — TENANT-SCOPED (~78 colecții) → primesc `tenant_id`
Date de business per francizat: `users`, `properties`, `requests`, `transactions`,
`reviews`, `disputes`, `notifications`, `leads`✅, `ai_sessions`✅, digital twin (9),
house health (6), community (3), verified estate (4), vouchere/gamification (5),
parteneri & leads legacy (9), comunicare/analytics (11) etc.
✅ = deja acoperite integral (Sprint 2).

### T2 — PLATFORM CONFIG (~29 colecții) → default global + override per-tenant
`settings`✅, `site_menu`✅, `site_content`✅, `service_pages`✅, `xos_widget_registry`✅,
`experience_profiles`✅, `ui_rules`✅, `design_tokens`, `regions`, `construction_taxonomy`,
`fee_configs`, `email_templates` etc.
Model: tenantul citește configul propriu → fallback la configul HQ (`main`). Façade-urile
din Sprint 2 fac acest fallback trivial de adăugat (un parametru `tenant` în `get_settings`).

### T3 — SYSTEM/OPS HQ (~100 colecții) → rămân GLOBALE, fără tenant_id
Tot ce e `admin_*`, `qa_*`, `autonomy_*`, `orchestrator_*`, `security_*`, loguri, health,
backups, roadmap, marketing HQ. Motorul de administrare al platformei aparține HQ.

### UNCLASSIFIED
Orice colecție nouă neclasificată apare explicit în raportul `/coverage` — regulă de
guvernanță: nicio colecție nouă fără clasificare de tier.

## 5. Valuri de migrare (FIECARE cu raport + STOP pentru aprobare)
| Val | Conținut | Risc | Notă |
|---|---|---|---|
| **0** ✅ | Infrastructură (acest sprint): registru, rezolvare, clasificare, raport | zero | fără schimbare de comportament |
| **1** ✅ | `users.tenant_id`: stamping la register (email + Google OAuth) + backfill idempotent `main` la startup (`backfill_user_tenants`) — LIVRAT | mic | 1207/1207 useri acoperiți |
| **2** ✅ | Backfill idempotent `tenant_id="main"` pe TOATE cele 78 colecții T1 + index `tenant_id` + marker `tenant_migrations` (wave 2) + `POST /api/admin/tenants/backfill` — LIVRAT: 96.135 docs, acoperire 100% | mic | filtrele pe citiri se activează în val 3, la primul francizat real |
| **3** | Restul T1 + override-uri T2 per tenant + rezolvare pe subdomeniu | mediu | activarea reală a primului francizat |

Regulă strangler (identică cu Sprint 2): backfill idempotent cu `main`, filtrele se adaugă
DOAR după ce acoperirea colecției e `full` — zero risc de a "pierde" date în citiri.

## 6. Decizii de arhitectură propuse (de ratificat de Owner)
- **D-T1**: Un singur DB Mongo, discriminare prin `tenant_id` (nu DB-per-tenant) — simplu, ieftin, suficient sub ~50 francizați.
- **D-T2**: Utilizatorii aparțin unui singur tenant (fără cont cross-franciză în val 1-3).
- **D-T3**: Adminul HQ vede toate tenants; adminul de franciză (rol viitor `franchise_admin`) vede doar tenantul lui.
- **D-T4**: Plățile/Stripe rămân pe contul HQ până la decizia de split financiar (Connect) — în afara scope-ului actual.
