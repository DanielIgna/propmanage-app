# MASTER PRODUCT AUDIT v2.0 — PropManage
**Board de audit:** Product Architect · Enterprise Software Architect · UX Director · Design System Lead · Business Consultant · AI Systems Architect · Marketplace Expert · SaaS Scaling Consultant · Franchise Consultant · CTO
**Data:** Iunie 2026 · **Referință:** PRODUCT_BLUEPRINT.md (Phase 0) · **Regim:** AUDIT-ONLY — zero modificări de cod/design.

**Cifre de bază (măsurate direct în cod):** 135 module de rute backend · 217 colecții MongoDB referențiate · 106 pagini/componente admin · 63 pagini frontend · ~25 cron jobs APScheduler · 5 colecții separate de lead-uri · 4 sisteme de conținut paralele.

---

# EXECUTIVE SUMMARY

**Verdict general: 78/100 — produs coerent ca viziune, dar cu fragmentare accelerată la nivel de execuție.**

PropManage a rămas fidel identității de **Property Intelligence OS**: stratul de date (Twin, House Health, Audit), stratul de tranzacție (Marketplace, Escrow), stratul de inteligență (AI, Observatory) și stratul de autonomie (Orchestrator, Self-Driving) există și se hrănesc reciproc — bucla din Blueprint §1.5.2 funcționează.

**Cele 3 riscuri sistemice (în ordinea gravității):**
1. **Entropie administrativă** — 106 pagini admin pentru un business operat de 1-2 oameni. Fiecare sprint a adăugat 2-4 dashboard-uri noi în loc să consolideze. Admin-ul devine el însuși un produs care cere mentenanță. Încalcă Legea lui Hick chiar în casa celui care a cerut-o.
2. **Fragmentare a datelor** — 5 colecții de lead-uri, 4 sisteme de config (app_settings, platform_config, platform_settings, security_config), 4 sisteme de conținut (cms_content, site_content, interior_design_content, landing_presets). Fiecare e corect izolat; împreună fac Knowledge Graph-ul imposibil fără un strat de unificare.
3. **Scalare single-instance** — APScheduler în proces, rate-limits în memorie, contoare in-memory. Corect azi (1 pod), blocant pentru multi-tenant/franciză (N pods = N cron-uri duplicate).

**Vestea bună:** XOS Faza 1 (Menu Manager, Layout Builder, UI Rules, Content Manager) este exact fundația corectă pentru franciză și demonstrează că direcția „config din DB, nu din cod" e deja internalizată.

---

# FAZA 1 · PRODUCT COHERENCE — 82/100

## Module aliniate cu viziunea Property Intelligence OS ✅
| Modul | Strat Blueprint | Verdict |
|---|---|---|
| Digital Twin, House Health, Verified Estate | Strat 1 · Date | ✅ nucleul identității |
| Marketplace, Escrow, Wallet, Dispute, Contracte | Strat 2 · Tranzacție | ✅ „consecință", nu identitate |
| Price Observatory, Pattern Hunter, AI Insights, Lead Triage | Strat 3 · Inteligență | ✅ |
| Autonomy Engine, Orchestrator, Self-Driving, Menu Optimizer | Strat 4 · Autonomie | ✅ diferențiator real |
| XOS (Menu/Layout/Rules/Content) | Infrastructură XOS | ✅ pregătește franciza |

## Module cu derivă de direcție ⚠️
1. **Community / Blog** (`community.py`, seed demo) — miroase a rețea socială. *De ce e derivă:* nu produce date despre proprietăți și nu consumă din buclă. *Salvare:* dacă devine „întrebări despre casa mea" legate de Twin/Health → se aliniază. Ca forum generic → anti-viziune.
2. **Token Economy / Gamification tiers** — construit înaintea masei critice de utilizatori. Blueprint permite (Strat 2), dar ordinea e inversată: gamificarea fără lichiditate de marketplace = mecanica fără combustibil.
3. **Cluster-ul admin de meta-management** (AI Dev Team, AI Product Manager, Dev Velocity, IT Copilot, Architecture Board, Roadmap Advisor, Future Ideas Vault, Deprecation Pulse...) — acestea administrează *dezvoltarea produsului*, nu *proprietățile*. Sunt utile ownerului, dar sunt un al doilea produs ascuns („Emergent-inside-PropManage"). *Risc:* efortul de mentenanță crește liniar cu numărul lor; valoarea nu.
4. **Demo/City Partners/Marketing Department** — B2B growth tools legitime (clasa GROWTH), dar fiecare cu propriul model de lead → fragmentare (vezi Faza 2).

**Concluzie Faza 1:** identitatea NU e amenințată de un modul anume, ci de **acumulare fără consolidare**. Regula din Blueprint §1.5.6 („nicio funcționalitate fără clasificare") a fost respectată ca spirit, dar nu există procesul invers: **retragerea** modulelor care nu și-au dovedit KPI-urile.

---

# FAZA 2 · ARCHITECTURE CONSISTENCY — 71/100

## 2.1 Duplicări de date (cel mai mare risc structural)
| Suprapunere | Colecții | Impact | Risc | Recomandare (fără implementare) |
|---|---|---|---|---|
| **Lead-uri (5 sisteme)** | `marketplace_leads`, `city_partner_leads`, `partner_leads`, `interior_design_leads`, `demo_leads` | Niciun „single view of lead"; triage AI rulează doar pe interior_design | MEDIU→MARE pe măsură ce apar servicii noi (Design Exterior etc. vor naște `exterior_design_leads`...) | Model unificat `leads` cu `source` + `pipeline`; views per serviciu |
| **Config (4 sisteme)** | `app_settings`, `platform_config`, `platform_settings`, `security_config` | Nimeni nu știe unde trăiește o setare; snapshots (settings_snapshots) acoperă doar o parte | MEDIU | Registru unic `settings` cu namespace-uri |
| **Conținut (4 sisteme)** | `cms_content`, `site_content`, `interior_design_content`, `landing_presets` | Content Manager XOS editează `site_content`, dar landing-ul are texte și în i18n hardcodat + `cms_content` | MARE pt. franciză (white-label cere UN singur loc) | Consolidare sub XOS Content cu chei namespaced |
| **Sesiuni AI chat (N sisteme)** | `concierge_messages`, `marketing_chat_sessions`, `interior_assistant_sessions`, `twin_conversations`, `chat_messages` | Fiecare asistent își reimplementa istoricul | MIC (funcțional) / MEDIU (cost mentenanță) | Un serviciu `ai_sessions` cu `agent_type` |
| **Findings QA (3 sisteme)** | `qa_sessions.findings`, `admin_ai_findings`, `term_inconsistencies` | Bug Memory Aggregator există tocmai pentru că sursele-s fragmentate | MEDIU | Aggregatorul să devină scriere-unică, nu doar citire |

## 2.2 Logică repetată în cod
- **Rate limiting** implementat de 2 ori independent (auth.py `_login_attempts`, interior_design.py `_ai_hits`) — ambele in-memory, ambele pierdute la reload, ambele fără X-Forwarded-For inițial (fixat doar la assistant). *Recomandare:* un util `rate_limit(key, max, window)`.
- **Pattern „settings doc cu key=main"** reimplementat în ≥6 module (site_menu, site_content, ui_rules, self_driving_settings, xos_layouts, monitor config) — corect ca idee, dar fiecare cu propriul sanitizer.
- **`notify_admins` vs `services.notify` vs email direct** — 3 căi de notificare; Notification Center le agregă parțial.
- **Seed-uri idempotente** — 10+ blocuri try/except identice în `server.py` startup (135 linii doar bootstrap). Funcționează, dar e un „God startup".

## 2.3 Naming inconsistent
- `digital_twin_*` (5 colecții) vs `twins` — două generații ale aceluiași concept, ambele active în cod.
- Română/engleză amestecate în ID-uri de meniu, chei config și label-uri (acceptabil pt. piață RO, dar va durea la white-label internațional).
- `pm-btn`/`btn-accent`/`DSButton` — 3 sisteme de butoane (vezi Faza 5).

## 2.4 Dependențe circulare & cuplaj
- `orchestrator.playbooks` ← importă din → `autonomy.self_driving` ← importă din → `routes.autonomy` ← emite semnale către → orchestrator. Ciclul e rupt azi doar prin importuri lazy în interiorul funcțiilor (pattern fragil dar funcțional). *Risc:* refactor-ul unui modul rupe lanțul la runtime, nu la import.
- `App.js` (~1.700 linii) conține LandingPage + Hero + 15 secțiuni + tot routing-ul. Orice conflict de merge trece pe aici.

## 2.5 Categorii istorice
- `ClientDashboard` (legacy) + `ClientDashboardV2` cu feature-flag localStorage — corect ca migrare, dar fără dată de sunset. Legacy-ul nu primește XOS layout (rulează doar pe V2) → experiențe divergente.
- Rute marketplace vechi (`/marketplace?categorie=X`) folosite ca destinații pentru servicii fără pagini dedicate — decizie pragmatică documentată, dar e datorie de conținut SEO.

---

# FAZA 3 · BUSINESS HEALTH AUDIT — scorul actual e onest, dar îngust

**Ce măsoară azi (8 departamente):** Marketing (creștere useri), Marketplace (fill rate), Escrow, Specialiști, Suport, Conversii, SEO, Financiar. Toate formule deterministe pe DB — **corect, explicabil, fără estimări**. 

**Ce lipsește (și de ce contează):**
| Dimensiune propusă | Sursă de date DEJA existentă în DB | De ce e potrivit |
|---|---|---|
| AI Effectiveness | `admin_ai_findings` (closed vs open), ai-health-score | AI e stratul 3 din identitate — azi nu apare în BH |
| Automation/Autonomy | `orchestrator_ledger` (minutes_saved), `playbook_executions` | North Star = ore economisite; BH nu-l vede |
| User Satisfaction | `reviews` (rating mediu, MultiDimReviews), NPS lipsă | promisiunile din Blueprint §1.2 au metrici — nemăsurate |
| Data Quality | % proprietăți cu twin+health activ (Gardă 2 din Blueprint!) | garda oficială nu e în scorecard |
| Security | `kyc_documents`, `security_config`, findings critice | există AI Security Center dar separat de BH |
| Performance/Infra | `health_pings`, smoke_test_runs | uptime-ul e măsurat dar nu agregat în BH |
| Technical Debt | Deprecation Pulse + TD list | invizibil în scor → nu se prioritizează |
| Knowledge Graph | # relații twin↔request↔review↔price | inexistent azi (vezi secțiunea KG) |
| Franchise Readiness | scor Faza 8 | pregătirea de scalare = sănătate de business |

**Propunere de structură (explicabilă, nu doar procent):**
```
BH v2 = 4 piloni ponderați, fiecare cu 3-5 KPI-uri cu formulă vizibilă:
  DEMAND  (Marketing, SEO, Conversii, Leads unificate)       ×0.25
  SUPPLY  (Specialiști, Fill rate, NPS specialist)           ×0.25
  ENGINE  (AI, Autonomy minutes_saved, Data Quality, Infra)  ×0.30  ← identitatea
  TRUST   (Escrow, Dispute, Reviews, Security, Suport)       ×0.20
Fiecare KPI: valoare, formulă, țintă, trend 30z, "de ce contează" (1 frază).
```
*Argument:* ENGINE primește ponderea cea mai mare pentru că Blueprint spune explicit: datele+inteligența sunt produsul; marketplace-ul e consecința.

---

# FAZA 4 · UX AUDIT

**Metodă:** eșantion reprezentativ (nu am acces la heatmaps reale — Clarity e în roadmap). Scoruri 0-100.

| Ecran | UX | Cognitiv | Consistență | Accesibilitate | Business Value | Observații cheie |
|---|---|---|---|---|---|---|
| Landing `/` | 82 | 74 | 85 | 70 | 95 | Hero puternic; 8+ secțiuni = scroll lung; bannere stivuite (demo+promo+announcement) pot ocupa 3 rânduri (Miller ⚠) |
| `/design-interior` | 88 | 82 | 90 | 78 | 92 | Cel mai coerent funnel; CTA triplu clar (Hick ✅); formular lung dar progresiv |
| Mobile drawer (SiteNav) | 90 | 88 | 92 | 82 | 90 | Font mare, taps generoase (Fitts ✅); 6 grupuri top-level (Hick ✅) |
| Client Dashboard V2 | 85 | 84 | 88 | 75 | 88 | Hero adaptiv contextual = progressive disclosure exemplar; XOS layout ✅ |
| Client Dashboard legacy | 62 | 55 | 60 | 65 | 60 | Divergent vizual de V2; candidat la sunset |
| Admin Dashboard (Metronic) | 72 | 58 | 80 | 70 | 85 | Sidebar cu 10 secțiuni × 3-15 iteme = 70+ destinații (Hick ✗✗); căutarea ⌘K salvează situația |
| Autonomy Engine | 80 | 70 | 78 | 72* | 82 | Info-dens dar ierarhizat; *fix light-mode aplicat în iter 109 |
| Business Health | 84 | 80 | 86 | 78 | 88 | Model de claritate: scor→formulă→trend |
| Menu Manager / XOS Builder | 86 | 82 | 84 | 76 | 90 | Drag&drop intuitiv; iconul ca text-input e slab (ar merita picker) |
| Marketplace public | 74 | 68 | 76 | 72 | 85 | Filtrarea pe `?categorie=` fără UI vizibil de filtre active |

**Constatări transversale:**
- **Jakob ✅** — pattern-uri familiare (drawer, cards, escrow ca la Upwork).
- **Nielsen #1 (vizibilitatea stării)** — foarte bine la orchestrator/autonomy (ledger, statusuri); slab la formulare publice lungi (fără progres salvat).
- **Accesibilitate: cel mai slab capitol transversal (~72-78)** — contrast bun post-fix, dar: focus states inconsistente, aria-labels sporadice, navigare exclusiv-tastatură netestată. Nu există audit axe-core automatizat.
- **Mobile-first** — public: da; admin: nu (tabelele Menu Manager pe 390px cer scroll orizontal).
- **Cognitive load admin** — problema #1 UX a platformei: 106 pagini, multe cu >1 idee pe ecran.

---

# FAZA 5 · DESIGN SYSTEM AUDIT

| Inconsistență | Dovadă | Clasificare |
|---|---|---|
| **3 sisteme de butoane** — `pm-btn` (tokens), `btn-accent` (landing), `DSButton`/shadcn (admin nou) + butoane Tailwind ad-hoc în paginile noi (XOS, MenuManager) | grep în cod | **P0** — orice pagină nouă alege aleator |
| **2 tokeni de culoare pt. același verde-lime** — `#d4ff3a` hardcodat în ~40 fișiere vs `--pm-primary` din Palette Cascade | index.css + pages | **P0** — Palette Cascade nu poate re-tema paginile hardcodate → blocant white-label |
| **Dark hardcodat pe ~21 pagini admin** reparat prin CSS override global (`html[data-theme=light] .bg-[#0e0e10]…`) | index.css 703+ | **P1** — fix-ul e corect ca triaj, dar e datorie: paginile ar trebui să folosească tokens |
| **Carduri: ≥4 stiluri** — pm-card, AdminCard, glass-strong, rounded-2xl ad-hoc | vizual + cod | **P1** |
| **2 familii tipografice de titlu** — serif (landing/autonomy) vs sans-black (admin Metronic) | vizual | **P2** — poate fi decizie intenționată public vs admin; nescrisă nicăieri |
| **Iconografie** — lucide consistent ✅, dar mărimi variate (w-3.5/4/5) fără scară documentată | cod | **P2** |
| **Spacing** — mx-5/px-6/p-4 amestecate în aceleași contexte | cod | **P2** |
| **Tabele** — Menu Manager (inputs inline) vs AdminCard tables vs shadcn table nefolosit | cod | **P2** |

**Concluzie:** există UN design system (tokens + Palette Cascade + shadcn) dar **acoperă ~60% din suprafață**; restul e pre-tokens. Riscul nu e estetic, ci de franciză: white-label = schimbi 5 culori și TOT produsul se re-temează — azi nu e adevărat.

---

# FAZA 6 · AI AUDIT

**Inventar: ~19 subsisteme AI** (concierge, copilot client, interior assistant, marketing chat, twin QA, AI search, insights, weekly briefing, exec briefing, UX audit, design audit, dispute triage, pattern hunter, finance reconciler, roadmap advisor, QA copilot, security center, dev team, governance).

| Categorie | Constatare |
|---|---|
| **AI duplicat / unificabil** | 4 chat-asistenți separați (concierge, interior, marketing, twin QA) cu 4 istorice, 4 system-prompts, 0 memorie comună. *Unificare:* un Agent Runtime cu `agent_profile` + memorie per user. |
| **AI cu valoare nedovedită** | AI Dev Team, AI Product Manager, Roadmap Advisor — generează text pentru owner; niciun KPI de acțiuni rezultate. Candidați la „observe-only" sau sunset. |
| **AI cu cea mai mare valoare/cost** | Lead Triage (determinist!), dispute triage, smoke self-healing, auto-match — execută, nu conversează. Exact filosofia Blueprint §1.5.3. |
| **AI lipsă (goluri reale)** | 1) **Property Copilot proactiv** — „acoperișul tău are 12 ani, în zona ta reparațiile costă X" (are TOATE datele: twin+health+observatory, nu le unește). 2) **Next-Best-Action pentru specialist** (există doar pt. client). 3) **Churn predictor** pe clients inactivi. |
| **AI → Knowledge Graph** | Niciun agent nu interoghează relații (casă↔lucrări↔prețuri↔recenzii); toți citesc colecții izolat. KG-ul ar transforma 19 agenți mediocri în 5 agenți excelenți. |
| **AI → Analytics/Heatmap** | UX Inspector există dar rulează pe descrieri statice, nu pe Clarity real (integrarea e în roadmap-ul DSE — corect prioritizată P1). |
| **AI → Feedback** | Reviews multi-dim există, dar nu hrănesc matching-ul (specialistul cu 5★ la „curățenie" nu e boostat la cereri unde clientul a cerut curățenie). |
| **AI autonom (potențial)** | Menu optimizer ✅ (implementat), lead triage ✅; următorii candidați: price suggestions auto-publish cu guard-rails, review-based matching weights. |

---

# FAZA 7 · MARKETPLACE AUDIT

| Componentă | Stare | Blocaj identificat |
|---|---|---|
| Matching | Auto-match cron ✅ | Nu folosește reviews multi-dim și nici istoricul de prețuri; matching pe specialitate+zonă e v1 |
| Lead-uri | 5 sisteme (vezi F2) | Lead-ul de interior design NU devine automat request în marketplace → funnel rupt între servicii |
| Escrow | Funcțional, warranty holds auto-release ✅ | Stripe test mode (blocat pe chei live de la owner) |
| Wallet | Funcțional | Token economy fără sink-uri reale de valoare (ce cumperi cu tokens?) |
| Dispute | AI triage ✅ | Fluxul de rezoluție finală rămâne 100% uman — corect legal, dar SLA nemăsurat |
| Timeline/Contracte | Există | Contractele nu se generează automat din request+offer (template manual) |
| Review | Multi-dim ✅ | Nu influențează matching (buclă nefolosită — cel mai ieftin win din marketplace) |
| Tier/Gamification | Construit complet | Suprad dimensionat pentru volumul actual; cost mentenanță > valoare azi |
| Business Assistant | Există pt. specialist | Nu vede pipeline-ul de lead-uri escaladate (stale requests) |
| **Blocaj #1 structural** | | **Cold start pe supply**: 16/372 specialiști verificați (4%). Toate mecanismele (escrow, tiers, escalation) presupun supply lichid. Nicio funcție nu rezolvă asta mai bine decât recrutarea targetată pe categoriile cu cereri fără oferte (semnalul EXISTĂ în handle_category_visibility — nefolosit ca playbook de recrutare). |

---

# FAZA 8 · FRANCHISE READINESS — **34/100**

| Capabilitate | Stare | Gap |
|---|---|---|
| Multi-Tenant | ❌ Not Ready | O singură DB logică; zero `tenant_id`/`city_id` pe colecțiile core (users, requests, properties) |
| White Label | ⚠️ 40% | Palette Cascade + tokens există, dar #d4ff3a hardcodat în ~40 fișiere; logo/brand din cod |
| Branding configurabil | ⚠️ | Company identity în Settings Control ✅, dar nefolosit de landing |
| Design configurabil | ✅ 70% | Design Studio + Palette Cascade — cea mai avansată piesă |
| Content configurabil | ⚠️ 50% | XOS Content Manager nou ✅, dar acoperă banner+hero; restul în i18n/cod |
| Role configurabile | ⚠️ | RBAC sub-admini cu scopes ✅; rolurile client/specialist hardcodate |
| Module configurabile | ⚠️ 45% | UI Rules + Layout Builder pot ascunde; nu pot dezactiva backend per tenant |
| Orașe independente | ⚠️ 30% | City Partners există ca CRM de parteneri, nu ca tenant izolat |
| Dashboard per franciză | ❌ | Toate dashboard-urile agregă global |
| Business Rules locale | ❌ | Comisioane/tarife globale (Settings Control e global) |
| Marketplace local | ⚠️ | Filtrare pe county există în requests; nu și izolare |
| Taxe locale | ❌ | Un singur set de tarife |
| Campanii locale | ⚠️ | marketing_campaigns fără scoping |
| AI Rules locale | ❌ | Toate pragurile AI globale |

**Ce lipsește fundamental (în ordine):** (1) `tenant_id` pe colecțiile core + middleware de scoping (există deja `middleware_scope` pentru admin — pattern extensibil!), (2) config ierarhic global→tenant, (3) eliminarea hardcodărilor de brand. **Estimare board:** franciza e la 2-3 faze de dezvoltare distanță, nu la una.

---

# FAZA 9 · SELF-CONFIGURATION READINESS (Experience OS)

| Capabilitate | Verdict | Explicație |
|---|---|---|
| Menu Builder | ✅ **Ready** | Live: CMS, vizibilitate, ordine, autonomy reorder |
| Design Tokens | ✅ **Ready** | Palette Cascade derivă 20 tokens; gap: adopție 60% |
| Visibility/Rule Engine | ✅ **Ready (v1)** | UI Rules cu 4 condiții; lipsesc: condiții compuse OR, targete pe rute |
| Layout Builder | ⚠️ **Partially** | 1 suprafață (client_home); arhitectura suportă extindere ușoară |
| Widget Builder | ⚠️ **Partially** | Widgets = registru hardcodat; nu se pot CREA widget-uri noi din admin |
| Dashboard Builder | ⚠️ **Partially** | Doar client V2; admin/specialist neacoperite |
| Content Manager | ⚠️ **Partially** | Banner+hero+chei libere; nu acoperă i18n existent |
| Role Experience Manager | ⚠️ **Partially** | UI Rules pe rol ✅; nu există „profil de experiență" per rol ca entitate |
| AI Experience Optimizer | ❌ **Not Ready** | DSE roadmap există (Clarity, self-healing UX) — neînceput |
| Component Library | ⚠️ **Partially** | shadcn + design-system.jsx; nefolosit uniform (F5) |
| No-Code Administration | ⚠️ **Partially** | Pentru meniu/layout/rules/content DA; pentru module/roluri/tarife NU |

**Sinteză:** XOS = **55% ready**. Drumul corect e deja trasat; riscul e să se construiască widget-uri noi hardcodate în paralel cu builderul (s-a întâmplat deja: SelfDrivingPanel e hardcodat în AutonomyEnginePage, nu e widget XOS).

---

# FAZA 10 · TECHNICAL DEBT (listă nouă, post-sprinturi recente)

| # | Item | Clasa | Detaliu |
|---|---|---|---|
| TD-1 | **State in-memory nepersistent** (rate limits ×2, retry counters) | **Critical** | Pierdut la fiecare hot-reload; incorect la >1 replică |
| TD-2 | **APScheduler in-process, ~25 joburi** | **Critical** (pt. scalare) | Multi-replică = execuție duplicată (emailuri duble, escaladări duble). Necesită lock distribuit sau worker dedicat |
| TD-3 | **#d4ff3a + dark colors hardcodate** vs tokens | **High** | Blochează white-label; CSS override-ul din iter 109 e paliativ |
| TD-4 | **App.js 1.700 linii** (Landing inline + tot routing-ul) | **High** | Merge conflicts, bundle, lizibilitate; lazy loading există dar structura nu |
| TD-5 | **5 colecții lead + 4 config + 4 content** | **High** | Vezi F2 — fiecare feature nou adâncește divergența |
| TD-6 | **Importuri lazy anti-circulare** (orchestrator↔autonomy↔routes) | **Medium** | Fragil la refactor; merită un modul `core/events` |
| TD-7 | **ClientDashboard legacy fără sunset** | **Medium** | Dublă mentenanță UX |
| TD-8 | **Colecții fantomă `twins` vs `digital_twin_*`** | **Medium** | Două generații active |
| TD-9 | **God startup în server.py** (10+ seeds inline) | **Medium** | Mutare în `bootstrap.py` cu registry |
| TD-10 | **Zero teste automate pe frontend** (doar testing-agent ad-hoc) | **Medium** | Bug-ul menuStats (iter 108) ar fi fost prins de un render-test |
| TD-11 | **Accesibilitate netestată** (fără axe-core în CI) | **Medium** | Vezi F4 |
| TD-12 | **Secrets în .env cu caractere $ (bcrypt history)** | **Low** | Documentat în memorie; risc de regresie la re-setare |
| TD-13 | **menu_clicks fără TTL index** | **Low** | Creștere nelimitată; agregarea filtrează 30z dar datele rămân |
| TD-14 | **Emoji în UI ca iconografie** (📊🤖🔥 în stringuri) | **Low** | Contravine ghidului intern (lucide-only) |

---

# FAZA 11 · PRODUCT CONFLICTS ⚔️ (decizia aparține administratorului)

### C1. Admin atotputernic vs. Legea lui Hick
- **De ce apare:** fiecare capacitate nouă (corectă individual) primește pagină proprie → 106 pagini.
- **Varianta A — consolidare agresivă** (5-7 hub-uri: Operations, Growth, Intelligence, Experience, System): + cognitive load ↓↓, onboarding franciză simplu; − efort mare, risc de regresii, pierzi deep-links existente.
- **Varianta B — status quo + căutare ⌘K ca interfață primară:** + zero efort, puterea rămâne; − entropia crește cu fiecare sprint, imposibil de predat unui angajat/franchisee.
- **Impact lung:** A = produs vandabil ca franciză; B = produs operabil doar de fondator. **Risc A:** 2-3 săptămâni de muncă fără feature nou vizibil.

### C2. Viteza AI-driven vs. Design System
- **De ce apare:** paginile se nasc mai repede decât se tokenizează.
- **A — „gate" strict (nicio pagină fără tokens/DSButton):** coerență, white-label real; − încetinește fiecare livrare cu ~10-15%.
- **B — livrezi rapid, tokenizezi în valuri (ca fix-ul light-mode):** viteză; − fiecare val de curățenie costă mai mult decât precedentul.
- **Impact lung:** fără A, franciza white-label rămâne promisiune.

### C3. Marketplace lichiditate vs. Property Intelligence purity
- **De ce apare:** venitul pe termen scurt vine din marketplace; identitatea din date.
- **A — focus 100% supply/demand (recrutare specialiști, SEO servicii):** cashflow, validare; − riscă să transforme produsul în „încă un marketplace" (anti-viziune).
- **B — focus date (twin, health, observatory):** șanț competitiv; − arde bani fără venit imediat.
- **Blueprint-ul zice explicit B-cu-A-drept-consecință; realitatea cere cash. Conflict legitim de secvențiere, nu de viziune.**

### C4. Autonomie totală vs. răspundere legală
- **De ce apare:** Self-Driving aprobă/execută; dispute și escrow au implicații legale.
- **A — extinzi auto-approve la tot ce e reversibil:** HDI 90+; − o eroare pe bani reali = încredere distrusă + expunere legală.
- **B — pragul actual (low-risk whitelist):** sigur; − HDI plafonat ~85.
- **Notă board:** ireversibil ≠ automatizabil. Lista albă pe acțiuni reversibile e singura cale sănătoasă; 90% se atinge prin VOLUM de acțiuni mici, nu prin riscuri mari.

### C5. Franciză multi-tenant vs. simplitatea actuală a datelor
- **De ce apare:** tenant_id retrofitting pe 217 colecții e majoră.
- **A — retrofit acum (devreme):** cost minim azi vs. exponențial mâine; − muncă „invizibilă".
- **B — amâni până la primul contract de franciză:** efort just-in-time; − primul contract va aștepta 2-3 luni de refactor.

### C6. XOS Widget Builder vs. widget-uri hardcodate rapide
- **De ce apare:** e mai rapid să scrii un panel React decât să extinzi registrul XOS (dovadă: SelfDrivingPanel).
- **A — regulă: orice widget nou intră prin registrul XOS:** builderul devine real; − friction pe fiecare feature.
- **B — hardcodezi și migrezi „mai târziu":** viteză; − „mai târziu" = niciodată, XOS rămâne demo.

### C7. Knowledge Graph vs. colecții izolate
- **De ce apare:** KG cere identificatori comuni și relații; azi lead≠request≠project≠review sunt lumi paralele.
- **A — strat de linkage (property_id obligatoriu peste tot):** deblochează Property Copilot (F6); − disciplină pe fiecare insert.
- **B — agregare la citire (cum face Bug Memory Aggregator):** fără migrare; − scump la query, imposibil pt. AI real-time.

---

# FAZA 12 · EVOLUTION ROADMAP (propunere de restructurare)

**Ce eliminăm/înghețăm din roadmap-ul curent (cu argument):**
- ❄️ Gamification/tiers noi — până la lichiditate marketplace (F7 blocaj #1).
- ❄️ Agenți AI meta (Dev Team, PM) — observe-only, zero investiție nouă.
- ❄️ Developer Mode Design Studio (P2 istoric) — sub valoarea consolidării DS.

**Ce comasăm:**
- „Pagini dedicate servicii" + „SEO landing engine" → un singur **Service Page Factory** pe modelul interior_design (content din DB, deja dovedit).
- Bug Memory + QA findings + term audit → **un singur Findings Store**.

**Roadmap propus (secvențiat pe deblocări, nu pe dorințe):**
```
FAZA A (consolidare, 1-2 sprinturi) — "plătește datoria care blochează totul"
  A1. Unificare leads (TD-5) + lead→request bridge (F7)     [deblochează: funnel unic + triage global]
  A2. Token adoption: #d4ff3a → var(--pm-primary) (TD-3)     [deblochează: white-label]
  A3. Scheduler lock / idempotență joburi (TD-2)             [deblochează: multi-replica]
FAZA B (venit, 1-2 sprinturi) — "lichiditate"
  B1. Recruitment playbook pe categorii cu cereri fără oferte (semnal existent)
  B2. Service Page Factory: Design Exterior, Renovări (clone interior-design)
  B3. Reviews → matching weights (cel mai ieftin win din F7)
FAZA C (identitate, 2 sprinturi) — "Property Intelligence real"
  C1. property_id linkage peste requests/reviews/prices (C7-A)
  C2. Property Copilot proactiv (F6 gap #1) — primul consumator KG
FAZA D (scalare) — "franciză"
  D1. tenant_id pe colecții core + scoping middleware (C5-A)
  D2. Config ierarhic global→tenant (comisioane, tarife, AI thresholds)
  D3. XOS Widget Registry obligatoriu (C6-A) + Layout pe 3 suprafețe
```

---

# KNOWLEDGE GRAPH READINESS — **25/100**
- ✅ Există noduri bogate (properties, twins, requests, reviews, prices, health).
- ❌ Lipsesc muchiile: `property_id` inconsistent propagat (reviews→request→property e traversabil; leads/observatory/community NU).
- ❌ Niciun strat de query pe relații; agenții AI citesc colecții brute.
- **Primul pas concret (fără graph DB):** convenție `property_id` + `person_id` obligatorii pe orice insert nou + 3 agregări materializate (property_timeline, specialist_track_record, price_evidence). Suficient pentru Property Copilot.

---

# TOP RECOMANDĂRI PRIORITIZATE (selecție 25 din 50 — restul sunt derivate)
Format: Impact / Complexitate / Risc / Dependențe / Prioritate / Blueprint-compliant

| # | Recomandare | I | C | R | Dep | P | BP✓ |
|---|---|---|---|---|---|---|---|
| 1 | Unificare model leads + bridge lead→request | ★★★★★ | M | M | — | **P0** | ✅ §3 |
| 2 | Reviews multi-dim → matching weights | ★★★★★ | S | S | — | **P0** | ✅ §1.5.2 |
| 3 | Recruitment playbook (categorii cu demand, 0 supply) | ★★★★★ | S | S | semnal existent | **P0** | ✅ |
| 4 | Token adoption sweep (#d4ff3a→--pm-primary) | ★★★★ | M | S | — | **P0** | ✅ |
| 5 | Scheduler idempotency/lock | ★★★★ | M | M | — | **P0** | ✅ infra |
| 6 | Blueprint Compatibility Gate (regulă permanentă — vezi Decision Log) | ★★★★★ | S | — | — | **P0** | ✅ definițional |
| 7 | property_id linkage convention | ★★★★★ | M | S | 1 | **P1** | ✅ §1.5.5 |
| 8 | BH v2 (4 piloni, incl. Autonomy+Data Quality) | ★★★★ | M | S | — | **P1** | ✅ §1.4 |
| 9 | Service Page Factory (clone interior-design) | ★★★★ | S | S | — | **P1** | ✅ |
| 10 | Consolidare admin în 5-7 hub-uri (C1-A) | ★★★★ | L | M | — | **P1** | ✅ Hick |
| 11 | Agent Runtime unificat (4 chats→1) | ★★★ | M | M | — | **P1** | ✅ §1.5.3 |
| 12 | Findings Store unic | ★★★ | M | S | — | **P1** | ✅ |
| 13 | Property Copilot proactiv | ★★★★★ | L | M | 7 | **P1** | ✅ inima viziunii |
| 14 | Sunset ClientDashboard legacy | ★★★ | S | M | — | **P1** | ✅ |
| 15 | Config registry unic (4→1) | ★★★ | M | M | — | **P1** | ✅ |
| 16 | XOS: widget registry obligatoriu + 2 suprafețe noi | ★★★ | M | S | — | **P1** | ✅ XOS |
| 17 | Rate-limit util comun + persistent | ★★ | S | S | — | **P2** | ✅ |
| 18 | axe-core accessibility în testing loop | ★★★ | S | S | — | **P2** | ✅ |
| 19 | App.js split (Landing în pages/) | ★★ | M | M | — | **P2** | ✅ |
| 20 | TTL index menu_clicks + capped analytics | ★ | S | S | — | **P2** | ✅ |
| 21 | Icon picker vizual în Menu Manager | ★★ | S | S | — | **P2** | ✅ |
| 22 | tenant_id pe colecții core | ★★★★ | XL | L | 1,15 | **P2→P0 la primul contract** | ✅ §fr |
| 23 | NPS in-app (client + specialist) | ★★★ | S | S | — | **P2** | ✅ §1.2 |
| 24 | Community re-anchor la proprietăți sau sunset | ★★ | M | M | — | **P2** | ⚠️ de decis |
| 25 | Token economy: definire sink-uri sau înghețare | ★★ | S | S | — | **P2** | ⚠️ de decis |

## QUICK WINS (sub 1 zi fiecare, valoare imediată)
1. Reviews→matching (rec #2) · 2. Recruitment alert playbook (#3) · 3. TTL menu_clicks (#20) · 4. NPS 1-întrebare post-confirmare (#23) · 5. Sunset banner pe legacy dashboard (#14, pas 1) · 6. Icon picker (#21).

## LONG TERM VISION (board-consensus)
PropManage câștigă dacă în 3 ani propoziția *„casa mea are un istoric complet și un sistem care o întreține singur"* e adevărată pentru 10.000 de case. Tot ce nu servește direct această propoziție (gamification prematură, agenți meta, community generică) e opțional. Marketplace-ul rămâne motorul de monetizare; datele rămân șanțul. Franciza e mecanismul de distribuție — dar numai după FAZA A+C din roadmap, altfel se francizează entropia.

---

# DECISION LOG (decizii cerute administratorului — nimic implementat)
| ID | Decizie cerută | Opțiuni | Recomandarea board-ului (neobligatorie) |
|---|---|---|---|
| D1 | Conflict C1: consolidare admin? | A / B | A, eșalonat pe 3 sprinturi |
| D2 | Conflict C2: DS gate obligatoriu? | A / B | A, cu excepții documentate |
| D3 | Conflict C3: secvențiere cash vs date | A / B | B1-B3 întâi (cash), apoi C (date) — exact roadmap-ul propus |
| D4 | Conflict C4: extindere auto-approve | A / B | B + volum (whitelist doar reversibile) |
| D5 | Conflict C5: tenant_id acum sau la contract | A / B | A-light: doar convenția pe inserturi noi, migrare la contract |
| D6 | Conflict C6: XOS registry obligatoriu | A / B | A |
| D7 | Community & Token economy: pivot sau îngheț | pivot/îngheț/sunset | îngheț + re-evaluare la 1.000 utilizatori activi |
| D8 | **REGULĂ PERMANENTĂ (cerută de owner, ratificată de board):** *Nicio funcționalitate nouă nu se implementează fără verificare de compatibilitate cu PRODUCT_BLUEPRINT.md, Product Constitution, Experience OS și Knowledge Graph* — checklist: (1) se aliniază viziunii? (2) creează duplicări/conflicte? (3) afectează UX (Hick/Miller/Fitts)? (4) compatibilă multi-tenant/franciză? (5) respectă Design System? (6) produce ȘI consumă date din buclă (§1.5.2)? | adoptare imediată | **DA — se adoptă ca gate obligatoriu în procesul de dezvoltare, începând cu următorul feature.** |

---
*Audit realizat exclusiv prin analiză statică de cod, DB schema și documentație. Niciun cod modificat, nicio componentă creată, niciun design schimbat.*
