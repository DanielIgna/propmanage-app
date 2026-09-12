# PROPMANAGE — AUDIT COMPLET DE PLATFORMĂ (Product · UX · Software Architecture)
**Data:** Iulie 2026 · **Autor:** Principal Product/UX/Software Architect (E1) · **Tip:** Analiză ZERO-COD (nicio modificare implementată)

---

## 0. METODOLOGIE & CIFRE BRUTE (inventar descoperit automat)

| Dimensiune | Valoare măsurată |
|---|---|
| Fișiere rute backend | **113 module** (~39.100 linii doar în /routes) |
| Colecții MongoDB utilizate | **185 colecții** |
| Pagini frontend | **~140 pagini** (86 doar în /pages/admin) |
| Linii frontend | **~67.700** |
| Componente shadcn/ui | 46 |
| Hooks custom | **doar 2** (use-toast, useSEO) — semnal de logică duplicată în pagini |
| Roluri hard: | client, specialist, admin, operator (+ partner, marketplace_partner, it_collaborator prin routere dedicate) |
| Tiers experiență | junior → regular → verified → pro (`experience_tiers.py`, TIER_FEATURES) |
| Zone admin | business (12 intrări), infrastructure (6), + AI Lab / Dev & QA / IT Hub — 15 secțiuni de meniu |
| Playbook-uri Autonomy Orchestrator | 7 active (smoke-fail, reflex, webhook retry, visibility gate, dispute triage, KYC reporter, marketplace medic) |
| Top 5 fișiere-gigant backend | admin_console.py (2.745), digital_twin.py (2.327), auth.py (1.631), admin_ai.py (1.540), gdpr.py (932) |
| Top 5 fișiere-gigant frontend | App.js (1.711), SettingsPanel (1.576), FutureIdeasVault (1.525), AdminAuditLog (1.104), AdminLayoutMetronic (1.036) |
| Colecții cele mai folosite | users (425 ref), requests (178), properties (44), admin_ai_findings (41), projects (38), digital_twin_pins (35) |

**Module descoperite** (nu doar cele enumerate în brief): Auth+KYC+GDPR, Requests/Projects/Disputes+NC, Properties+Digital Twin (pins/models/projects/QA), House Health (hh_plans), Wallet+Transactions+Payments (Stripe), Marketplace Servicii + Marketplace Parteneri (produse/leads/offers), Verified Estate (imobile verificate), City Partners, Strategic Partners, Community, Concierge AI, Analytics Growth (campanii QR), AI Governance + AI Findings + AI Repair Suggestions, Autonomy Engine + Autopilot + Orchestrator (nou), Construction Intelligence (taxonomie + Price Observatory — nou), QA Copilot + Smoke Test + Content/Term Audit, Onboarding Emails, Tier Milestones, Experience Spaces, Landing Presets, Sub-admins + Scope Matrix, IT Collaborators, Incidents, Todos, Tour, Help/Docs AI, Legal/Contracts, Notificări + Web Push, SEO (ghiduri/slugs), Settings Panel, Future Ideas Vault.

---

## 1. DIAGNOZA APLICAȚIEI

**PropManage este un „ecosistem de tip enterprise" construit în ritm de startup.** Amploarea funcțională este excepțională (185 colecții, 113 module API) și acoperă întregul lanț valoric: proprietate → sănătatea casei → cerere → matching → escrow → dispută → review → recurență, plus straturi B2B (parteneri, imobile verificate) și un strat de autonomie operațională unic pe piață.

**Diagnostic sintetic: „Featureship > Craftsmanship".** Platforma a acumulat funcții mai repede decât a consolidat fundațiile:
1. **Dualitate generațională UI** — coexistă Client V1 (939 linii) și Client V2 (clientv2/, design nou), Components.jsx vs ComponentsV2.jsx, OperatorTwin vs OperatorDigitalTwin. Utilizatorii trăiesc în două ere de design simultan.
2. **Admin = labirint funcțional** — 86 pagini, 15 secțiuni de meniu. Este un „panou cu meniuri", nu un centru de comandă. Informația există, dar prioritizarea o face omul, nu sistemul.
3. **Monolitism în fișiere-gigant** — admin_console.py (2.745 linii) și App.js (1.711 linii, rutare integrală ne-lazy) sunt puncte de fricțiune pentru dezvoltare și performanță.
4. **Stratul de autonomie este avansat, dar invizibil pentru utilizatorul final** — orchestratorul lucrează, dar valoarea lui nu e „vândută" în UI-urile de client/specialist.
5. **Gamification există fragmentar** (tiers, milestones, achievements pe alocuri) dar nu este un sistem unitar de progresie cu buclă de recompensă vizibilă.

---

## 2. PUNCTE FORTE (de protejat, nu de rescris)

1. **Autonomy Engine + Orchestrator (7 playbook-uri)** — diferențiator strategic real; ledger cu „minute umane salvate" este o metrică de business rară. ★★★★★
2. **Construction Intelligence (CIP-A/B)** — taxonomie ierarhică 203 noduri + visibility gate automat + Price Observatory cu trust grading: fundația unui avantaj de date național. ★★★★★
3. **Client V2 (clientv2/)** — direcția corectă: mobile-first, wizard curat, AmountInput, chips subcategorii, hint de preț. Este șablonul spre care trebuie migrat totul. ★★★★
4. **Fluxul financiar complet** — escrow, freeze la dispută, split la mediere (acum cu propunere AI), wallet, Stripe. Lanț de încredere end-to-end. ★★★★
5. **Guvernanța AI** — AI findings, repair suggestions, QA Copilot, smoke monitor, KYC vision cu mod-recomandare GDPR-safe: matur peste media pieței. ★★★★
6. **Infrastructura de QA internă** — smoke test E2E orar + QA sessions + content/term audit + test suites pytest per iterație. ★★★★
7. **Digital Twin + House Health** — active de retenție cu potențial de monetizare recurentă (hh_plans). ★★★
8. **Acoperire GDPR/legal** (932 linii gdpr.py, contracte, consimțăminte) — barieră de intrare pentru competitori. ★★★

---

## 3. PROBLEME IDENTIFICATE (ordonate după impact)

### P0 — impact critic asupra experienței și vitezei de dezvoltare
| # | Problemă | Dovadă | Efect |
|---|---|---|---|
| 3.1 | **Dualitatea V1/V2 la Client** | ClientDashboard.jsx (939 l.) + ClientDashboardSwitch + clientv2/ | Confuzie, dublă mentenanță, bug-uri fixate doar într-o versiune |
| 3.2 | **App.js monolitic, fără code-splitting** | 1.711 linii, importuri directe pentru ~140 pagini | Bundle inițial uriaș → TTI lent pe mobil (majoritatea clienților) |
| 3.3 | **Admin fără ierarhie a atenției** | 86 pagini / 15 secțiuni; KPI-uri fără praguri de alertă unificate | Adminul „patrulează" în loc să fie chemat; onboarding admin nou = zile |
| 3.4 | **Vocabular de categorii istoric dual** | users vechi cu `painting/carpentry/cleaning` vs. taxonomie `zugravit/...` (registerul a fost aliniat abia în CIP) | Matching-ul poate rata specialiști vechi; datele de coverage subestimate |

### P1 — impact mare
| # | Problemă | Dovadă | Efect |
|---|---|---|---|
| 3.5 | Fișiere-gigant backend | admin_console 2.745 l., digital_twin 2.327 l., auth 1.631 l. | Risc de regresie la fiecare edit; onboarding dev greu |
| 3.6 | Doar 2 hooks custom la 67k linii FE | hooks/ | Fetch/axios/toast/paginare re-implementate în zeci de pagini |
| 3.7 | Specialist Dashboard rămas în paradigma V1 | 4 taburi simple (jobs/opportunities/notifications/settings) | Cel mai important „furnizor" al marketplace-ului are cea mai săracă experiență |
| 3.8 | Notificările = listă plată, fără centre de acțiune | db.notifications (16 ref) | „Inbox blindness"; acțiunile propuse de AI nu sunt executabile din notificare |
| 3.9 | 185 colecții fără registru de scheme | fără models pentru majoritatea | Câmpuri divergente (ex. `ts` vs `created_at`), riscul de drift crește cu fiecare feature |
| 3.10 | Dublu sistem de niveluri nealiniat | experience_tiers (junior/regular/verified/pro) vs. brief-ul comercial (Junior/Verified/Premium) + tier badge separat pt. autonomie | Mesaj de progresie confuz pentru utilizator |

### P2 — impact mediu
| # | Problemă | Dovadă |
|---|---|---|
| 3.11 | Duplicate vizibile: Components vs ComponentsV2, OperatorTwin vs OperatorDigitalTwin, Dashboards.jsx agregator | ls pages/ |
| 3.12 | Meniul admin are intrări cu un singur utilizator real (FutureIdeasVault 1.525 l. în bundle) | pages/admin |
| 3.13 | Onboarding client = tur ghidat liniar, fără checklist persistent cu recompense | GettingStartedWidget există dar nu e „hub" |
| 3.14 | Query-uri N+1 punctuale (ex. medic scan face find per dispută; projects join în Python) | orchestrator/playbooks, construction.py |
| 3.15 | Politica de capare a colecțiilor de telemetrie inconsistentă (unele capate la 500, altele nelimitate: analytics_events, admin_audit_log) | grep _cap |
| 3.16 | Dark/light mode inconsistent: admin nou = dark stone, pagini V1 = light slate, register = dark olive | audituri vizuale |
| 3.17 | test_credentials.md a driftat de realitate de 2 ori într-o singură zi | istoricul sesiunii |

---

## 4. OPORTUNITĂȚI DE ÎMBUNĂTĂȚIRE (quick wins → strategice)

1. **Lazy-loading pe rute** (React.lazy pe cele 86 pagini admin + V1) — probabil cel mai mare câștig de performanță per oră investită.
2. **„Attention Layer" în admin**: un singur endpoint `/api/admin/attention` care agregă TOP 5 lucruri care cer omul azi (escaladări orchestrator, KYC review, dispute fără triage, hidden-with-potential, retry-queue failed) → un singur widget „Ce cere atenția ta azi".
3. **Promovarea ledger-ului de autonomie în business**: „Săptămâna asta platforma a lucrat singură X ore" — în Morning Briefing (făcut) + admin home + pitch investitori.
4. **Migrarea specialistului la V2** reutilizând 1:1 componentele clientv2/ui.jsx (CTA, Sheet, AmountInput) — cost mic, impact mare.
5. **Bucla completă de recrutare**: funnel-ul „Invită specialiști" (făcut) + pagină publică „Devino specialist în {categorie}" cu prețurile medii din Observatory ca argument de venit.
6. **SEO programatic din Price Observatory**: pagini „Cât costă {serviciu} în {oraș} (2026)" generate din agregate — trafic organic cu intenție de cumpărare.
7. **Migrare istorică de vocabular**: script one-off care mapează painting→zugravit, carpentry→tamplarie, gardening→amenajari_exterioare în users.service_categories (cu backup) → coverage real crește imediat.
8. **Un pachet de hooks standard**: useApi (axios+abort+toast), usePaginatedList, useRole, useTier — taie sute de linii duplicate.

---

## 5. RECOMANDĂRI UX

### 5.1 Client — de la dashboard la Copilot
- **Home = o singură întrebare: „Ce facem azi cu casa ta?"** Deasupra foldului: House Health Score + următoarea acțiune recomandată (1 card, 1 CTA), generată din reguli + AI (sezon, vârsta instalațiilor din Digital Twin, istoricul cererilor).
- **Feed de „momente", nu grilă de widget-uri**: fiecare card = o propoziție + o acțiune („Centrala nu a avut revizie de 11 luni → Programează, ~250 RON, 3 specialiști disponibili" — folosind Observatory + matching).
- **Progresie vizibilă Junior→Verified→Premium** cu un singur progress-ring persistent și „next unlock" explicit (aliniat la TIER_FEATURES, nu un sistem paralel).
- **Wizard**: păstrat (e bun), + pas 0 opțional „descrie liber, AI alege categoria" (LLM classify → precompletează categorie+subcategorie).

### 5.2 Specialist — cockpit de venit
- Home = **„Pipeline & Bani"**: oportunități noi potrivite (matching), lucrări active cu next-step, venit luna aceasta vs. media categoriei din Observatory („câștigi cu 12% sub media expert din Cluj → ridică-ți nivelul").
- **Reputația ca activ**: scor compus vizibil (rating, dispute rate, medic status, response time) + ce anume îl ridică.
- Calendar + disponibilitate ca first-class (azi îngropat în settings).

### 5.3 Admin — de la meniuri la centru de comandă
- **Home nou = 3 straturi**: (1) Attention Layer (ce cere omul azi), (2) Pulse (KPI cu praguri și trend, nu valori brute), (3) Autonomy Report (ce a rezolvat platforma singură — ledger).
- Meniul din 15 secțiuni → **4 huburi**: Operațiuni (cereri/dispute/KYC/utilizatori), Business (financiar/marketplace/parteneri/growth), Platformă (construcție/imobile/twin/conținut), Sistem & AI (autonomie/QA/securitate/config). Restul devin căutabile prin CommandPalette (există deja!) promovat ca navigare primară (⌘K).
- **Fiecare listă primește „bulk + saved filters"** (dispute, KYC, parteneri) — pattern unic reutilizabil.

### 5.4 Onboarding premium (toate rolurile)
- Înlocuirea turului liniar cu **„Misiuni"**: checklist persistent 5-7 pași per rol, fiecare cu recompensă concretă (tokeni, badge, deblocare feature din TIER_FEATURES), progres salvat server-side, reluabil.
- Client: adaugă proprietate → completează Digital Twin light → prima cerere → activează House Health → invită un vecin.
- Specialist: profil complet → KYC (cu AI care spune „recomandat spre aprobare" în timp real) → portofoliu 3 poze → prima ofertă → primul review.
- **Empty-states = onboarding contextual** (fiecare listă goală vinde acțiunea următoare, nu afișează „niciun rezultat").

### 5.5 Design System
- Un singur **tokens layer** (culori/spacing/typography) cu 2 teme oficiale: „Client Light" (slate+verde #34C759) și „Ops Dark" (stone+violet/amber) — astăzi ambele există dar neformalizate.
- Standardizare pe clientv2/ui.jsx + shadcn ca **singura** sursă: CTA, Card, Sheet, Badge, Stat, EmptyState, DataTable — și interzicerea stilurilor ad-hoc noi.
- Iconografie: exclusiv lucide-react (există emoji-uri reziduale în register/SPECIALTIES — de înlocuit la migrare).

---

## 6. RECOMANDĂRI PRODUCT

1. **North Star Metric propus:** „Ore de muncă umană economisite pe lună" (agregat: orchestrator ledger + cereri rezolvate fără admin + auto-match) — unește autonomia cu valoarea de business.
2. **Monetizare pe 4 motoare**, toate deja semi-construite: (a) comision marketplace, (b) abonamente House Health/Premium client, (c) subscripții specialiști (vizibilitate + leads, argumentate cu Observatory), (d) B2B: Verified Estate + City/Strategic Partners.
3. **Token Economy**: azi tokenii sunt periferici; recomand definirea unei bucle închise: câștigi (misiuni, review-uri, recomandări) → cheltui (boost cerere, raport House Health premium, prioritate matching). Fără buclă de cheltuire, tokenii sunt datorie de produs.
4. **Unificarea nivelurilor**: un singur sistem public — Client: Junior/Verified/Premium; Specialist: Entry/Junior/Verified/Premium — mapat interior pe TIER_ORDER existent (junior/regular/verified/pro), redenumit doar în stratul de prezentare.
5. **Verified Estate = capul de pod B2B**: leagă-l de Digital Twin + House Health ca „certificat de sănătate al imobilului" la vânzare — diferențiator imobiliar național.
6. **FutureIdeasVault → proces**: idei votate → trimise în ROADMAP.md → arhivate; nu pagină de 1.500 linii în bundle-ul admin.

---

## 7. RECOMANDĂRI SOFTWARE ARCHITECTURE

1. **Descompunerea giganților (fără schimbare de comportament):**
   - admin_console.py → admin_console/{users,finance,platform,tools}.py
   - digital_twin.py → digital_twin/{models,pins,projects,viewer}.py
   - auth.py → auth/{login,register,recovery,sessions,rate_limit}.py
   - App.js → routes/{public,client,specialist,admin,partner}.jsx cu React.lazy + Suspense per zonă.
2. **Stratificare țintă backend:** routes (subțiri) → services (logica) → repositories (acces db) — de aplicat progresiv, începând cu modulele atinse de fiecare task nou („boy-scout rule", nu big-bang).
3. **Registrul evenimentelor = orchestratorul** (deja există emit_signal): orice modul nou care are efecte cross-domain publică semnal, nu apelează direct alt modul — păstrează cuplarea mică.
4. **Un singur client HTTP frontend** (`lib/api.js`: axios cu baseURL, credentials, interceptor 401→login, toast pe erori) — elimină cele ~30 de instanțe `axios.create` locale.
5. **Contracte API stabile**: pentru endpointurile consumate de >1 pagină, definire Pydantic response models (azi multe returnează dict-uri libere).
6. **Politică unitară de telemetrie**: TTL/cap pentru analytics_events, orchestrator_*, admin_audit_log (indexuri TTL Mongo) — previne creșterea necontrolată.
7. **Feature flags formalizate**: azi app_settings + platform_config amestecă config și flags; separă `feature_flags` cu default-uri în cod și override în DB, citite printr-un singur helper.

---

## 8. RECOMANDĂRI DATABASE (analiză, fără migrații acum)

1. **Registru de scheme**: document `DB_REGISTRY.md` generat semi-automat (colecție → câmpuri → producători/consumatori). Cu 185 colecții, este obligatoriu pentru scalare în echipă.
2. **Convenții de normalizat la scriere nouă** (nu migrare retroactivă): `id` uuid-hex uniform (unele colecții folosesc _id Mongo ca string public — ex. requests), `created_at/updated_at` ISO-UTC peste tot (există `ts` în telemetrie — acceptabil dacă e documentat).
3. **Indexuri recomandate** (de verificat înainte): users(role, verified, service_categories), users(medic_suspended), requests(status, category, created_at), disputes(status, created_at), notifications(user_id, read, created_at), price_observations(category, city), construction_taxonomy(parent_id), orchestrator_ledger(ts), transactions(user_id, created_at).
4. **Duplicate conceptuale de urmărit**: `specialty` vs `service_categories` (păstrate ambele, dar orice logică nouă trebuie să citească doar prin helperul get_specialist_counts-style); statusuri de cerere definite în mai multe locuri (FE STATUS_LABEL vs BE) → un singur enum sursă.
5. **Nomenclatoare**: taxonomia CIP este acum sursa de adevăr pentru categorii — orice listă statică de categorii din FE (CATS din wizard, SPECIALTIES din register) ar trebui, în faza următoare, hidratată din `/api/construction/taxonomy/public` cu fallback static.
6. **Relații lipsă (soft)**: dispute → specialist_id denormalizat (azi derivat prin request la fiecare scan — vezi 3.14); request → city denormalizat (azi join la properties pentru filtre).

---

## 9. RECOMANDĂRI AI

1. **Un „AI Gateway" intern unic** (extinderea orchestrator/llm.py): toate apelurile LLM trec printr-un helper cu buget/zi, cache pe input identic, log în `ai_calls` (cost & latență) — azi apelurile sunt împrăștiate (kyc, marketplace_partners, admin_ai, orchestrator).
2. **Copilot Client (faza 1 ieftină)**: nu chat liber, ci **acțiuni generative țintite**: descriere liberă → clasificare cerere; poza problemei → categorie + severitate + preț orientativ (vision, ca la KYC); rezumatul lunar al casei (template + date, LLM doar pentru fraze).
3. **Dispute Triage v2**: învățare din decizia adminului (accepted/edited/rejected pe propunerea AI → stocat → prompt few-shot îmbunătățit; ulterior praguri de auto-aplicare la disputele mici, cu opt-in).
4. **Pattern Hunter (Sprint 3 din roadmap)**: agregări zilnice pe semnale (dispute pe categorie/oraș, drop-uri de conversie pe funnel, categorii cu cerere crescândă) → findings în admin_ai_findings, cu acțiuni sugerate executabile.
5. **Guardrails standard**: toate output-urile LLM validate pe schemă (json strict — deja practicat), niciodată scriere directă în producție fără ledger, marcare vizibilă „AI" în UI (deja la triage — de generalizat).
6. **KYC**: menținerea modului recomandare până la aviz juridic; adăugarea „explainability" (de ce review: care flag) — parțial există prin flags, de afișat mai clar.

---

## 10. ROADMAP ETAPIZAT

> Impact: 🟢mic 🟡mediu 🔴mare · Complexitate: ▲mică ▲▲medie ▲▲▲mare

### Phase 1 — „Stabilizare & Viteză" (fundații, 1-2 săptămâni de lucru efectiv)
| Item | Impact | Complexitate |
|---|---|---|
| React.lazy + split pe zone în App.js | 🔴 perf mobil | ▲▲ |
| lib/api.js unic + interceptori (înlocuire progresivă) | 🟡 | ▲ |
| Migrare vocabular categorii istorice (painting→zugravit etc., cu backup) | 🔴 matching corect | ▲ |
| Indexuri DB din §8.3 | 🟡 | ▲ |
| DB_REGISTRY.md generat + convenții scriere | 🟡 | ▲ |
| TTL/cap telemetrie | 🟢 | ▲ |

### Phase 2 — „Admin Command Center" (1-2 săptămâni)
| Item | Impact | Complexitate |
|---|---|---|
| /api/admin/attention + widget „Ce cere atenția ta azi" | 🔴 | ▲▲ |
| Admin Home restructurat: Attention / Pulse / Autonomy Report | 🔴 | ▲▲ |
| Meniu → 4 huburi + CommandPalette ca navigare primară | 🟡 | ▲▲ |
| Descompunere admin_console.py (fără schimbare API) | 🟡 dev-speed | ▲▲ |
| Saved filters + bulk actions pattern (dispute, KYC) | 🟡 | ▲▲ |

### Phase 3 — „Specialist V2 + Onboarding Misiuni" (2-3 săptămâni)
| Item | Impact | Complexitate |
|---|---|---|
| Specialist Dashboard V2 (cockpit Pipeline & Bani, pe ui.jsx existent) | 🔴 supply-side | ▲▲▲ |
| Benchmark venit vs. Observatory în profil specialist | 🟡 retenție | ▲ |
| Sistem „Misiuni" cu recompense per rol (server-side, persistent) | 🔴 activare | ▲▲ |
| Unificarea publică a nivelurilor (redenumire pe TIER_ORDER) | 🟡 claritate | ▲ |
| Empty-states contextuale standard | 🟢 | ▲ |

### Phase 4 — „Client Copilot + SEO Growth" (3-4 săptămâni)
| Item | Impact | Complexitate |
|---|---|---|
| Home client = Next Best Action (reguli + sezon + twin + istoric) | 🔴 retenție | ▲▲▲ |
| Wizard pas 0: descriere liberă → AI precompletează | 🟡 conversie | ▲▲ |
| Pagini SEO programatice din Price Observatory („Cât costă X în Y") | 🔴 achiziție | ▲▲ |
| Pagină publică „Devino specialist în {categorie}" (funnel recrutare complet) | 🟡 supply | ▲ |
| AI Gateway unic + ai_calls ledger | 🟡 cost control | ▲▲ |
| Retragere Client V1 (după paritate V2: Interior Design, Job Filters) | 🔴 igienă | ▲▲ |

### Phase 5 — „Autonomie 2.0 & Scară" (continuu)
| Item | Impact | Complexitate |
|---|---|---|
| Autonomy Sprint 3: Pattern Hunter + Finance Reconciler + Roadmap Advisor | 🔴 | ▲▲▲ |
| Dispute Triage v2 cu feedback loop + auto-aplicare praguri mici | 🟡 | ▲▲ |
| Token Economy buclă închisă (earn/spend) | 🔴 monetizare | ▲▲▲ |
| Verified Estate × Digital Twin „certificat de sănătate imobil" | 🔴 B2B | ▲▲▲ |
| Stratificare services/repositories pe module noi (boy-scout) | 🟡 | continuu |
| CIP-C/D (Experience levels în matching, market reports vandabile) | 🔴 | ▲▲▲ |

---

## ANEXĂ — Reguli de aur pentru orice implementare viitoare
1. Orice ecran nou se construiește pe clientv2/ui.jsx + shadcn — zero stiluri ad-hoc noi.
2. Orice efect cross-modul trece prin orchestrator (semnal), nu prin apel direct.
3. Orice apel LLM trece prin AI Gateway și lasă urmă în ledger.
4. Orice listă nouă are: empty-state cu acțiune, filtre salvabile, data-testid.
5. Nicio funcție „ascunsă": dacă un rol are dreptul, o găsește din meniu sau ⌘K în ≤2 pași.
