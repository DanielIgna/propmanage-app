# PropManage — Manual de Operare Strategie & R&D

> **Pentru tine, fondatorul.** Acest manual îți arată EXACT cum să coordonezi platforma 100% din Admin Dashboard, fără să scrii cod și fără să strici nimic.
> Dacă termenii sunt confuzi, urmează doar pașii literali în ordinea în care apar. Fiecare modul are: **ce face**, **când îl folosești**, **pași concreți**, **ce afectează dacă greșești**, **cum repari**.

---

## 📌 Cuprins rapid

1. [Principii de siguranță (CITEȘTE PRIMUL)](#1-principii)
2. [Smart Pipeline — fluxul pentru orice idee nouă](#2-pipeline)
3. [AI Governance Center — observabilitatea ecosistemului AI](#3-governance)
4. [Architecture Review Board — anti-redundanță](#4-arch)
5. [AI Product Manager — idee → Epic/Features/Stories](#5-aipm)
6. [Deprecation Pulse — alarme retragere agenți](#6-pulse)
7. [Bug Memory Aggregator — vizibilitate findings](#7-bugmem)
8. [Autonomy Engine — recomandări automate (cum activezi zona DEV)](#8-autonomy)
9. [Founder Approval Gate — gardian acțiuni critice](#9-foundergate)
10. [Future Ideas Vault — backlog strategic](#10-futureideas)
11. [Stagii Progressive Disclosure (Junior → Verified → Pro)](#11-stages)
12. [Roadmap: ce mai e de făcut per modul](#12-roadmap)
13. [Cheat-sheet: scenarii frecvente](#13-cheatsheet)

---

<a id="1-principii"></a>
## 1. 🛡️ Principii de siguranță (CITEȘTE PRIMUL)

### Regula de aur
> **Nimic nu se șterge real fără confirmare.** Toate operațiunile distructive sunt fie soft-deletes (poți reveni), fie protejate de snapshots automate, fie blocate de Founder Gate.

### Cele 4 plase de siguranță

| Plasa | Ce face | Unde o găsești |
|-------|---------|----------------|
| **Settings Snapshots** | Salvează zilnic toate setările + restaurare cu 1 click | `/admin/snapshots` |
| **Founder Gate (FG-0)** | Definește 13 acțiuni critice care necesită confirmare în viitor | `/admin/founder-gate` |
| **Deprecation Plan** | Marchezi agenții ca depreciați fără să-i ștergi cod | `/admin/ai-governance` → tab Deprecation Plan |
| **Architecture Board** | Verifici dacă o idee se suprapune cu module existente | `/admin/architecture-board` |

### Reguli obligatorii înainte de orice schimbare majoră
1. **Verifică Settings Snapshots** — există unul în ultimele 24h? Dacă nu, forțează unul: `/admin/snapshots` → "Crează snapshot acum"
2. **Rulează Architecture Board** — orice idee mai mare de 1h de dezvoltare trebuie să treacă prin verdict
3. **Folosește `dry_run`** când e disponibil — vezi rezultatul fără să-l aplici
4. **Nu schimba `enable_founder_gate` în `true`** până nu activezi FG-1 (Twilio) — momentan e DEFERRED

### Cum repari dacă ai greșit ceva
- **Ai schimbat setări greșite** → `/admin/snapshots` → restore din ultimul snapshot bun
- **Un agent face spam** → marchează-l deprecated în Governance (nu-l șterge)
- **Un TODO greșit** → șterge-l din `/admin/todo` (nu afectează codul)
- **Un breakdown AI PM greșit** → șterge-l din `/admin/ai-pm` (nu afectează nimic altceva)
- **Un review Architecture greșit** → șterge-l din `/admin/architecture-board` (read-only, n-a generat cod)

---

<a id="2-pipeline"></a>
## 2. 🔀 Smart Pipeline — fluxul ÎN ORDINE pentru orice idee nouă

**Aceasta este "rețeta" pe care trebuie să o respecți de fiecare dată.**

```
   IDEEA TA
      ↓
  [1] Architecture Review Board   ← Verifică dacă există deja
      ↓ verdict ≠ reject_duplicate
  [2] Future Ideas Vault          ← Documentează ca propunere
      ↓ aprobat de tine
  [3] AI Product Manager          ← Descompune în Epic > Features > Stories
      ↓
  [4] Inject TODOs                ← Buton din AI PM
      ↓
  [5] Trimite agentului Emergent  ← (mie sau în chat) cu refință la TODO
      ↓
  [6] Verifică în preview         ← Tu testezi
      ↓
  [7] Deploy în producție         ← Butonul "Deploy" din Emergent
```

### Exemplu concret pas-cu-pas

> Vrei să adaugi: "Sistem de fidelizare clienți cu puncte și recompense"

**PAS 1** — Architecture Board
- Mergi la `/admin/architecture-board`
- Titlu: `Sistem fidelizare clienți`
- Descriere: `Clienții acumulează puncte la fiecare comandă completată, le pot folosi pentru reduceri la viitoarele cereri.`
- Scope: `1 backend route + 1 secțiune nouă în /client/dashboard`
- Apasă "Verifică suprapuneri"
- **Ce primești**: verdict `build_new` sau `extend_existing` (dacă marketplace_requests are deja sistem de tracking)
- **Decizie**: dacă `reject_duplicate` → oprește. Dacă `extend_existing` → notează care modul extinzi. Dacă `build_new` → continuă.

**PAS 2** — Future Ideas Vault (opțional pentru idei mici)
- Pentru idei mari (>3 zile dev) documentezi în `/admin/future-ideas`
- Pentru idei mici, sari peste

**PAS 3** — AI Product Manager
- Mergi la `/admin/ai-pm`
- Titlu + descriere identice cu PAS 1
- Context (opțional): `Avem 200 clienți activi, conversion baseline 12%, vrem fidelizare ca să crească RFM.`
- Apasă "Descompune ideea"
- **Ce primești**: Epic + 3 features prioritizate (P0/P1/P2/P3) + max 2 stories per feature + riscuri + out-of-scope

**PAS 4** — Injectează în TODO
- În același ecran, după ce vezi rezultatul, apasă "Injectează în TODO"
- **Ce se întâmplă**: features-urile devin task-uri în `/admin/todo` cu source `ai_pm:<id>`
- **Implicații**: TODO-urile sunt vizibile când îi ceri agentului Emergent să construiască — îi dai referința "construiește TODO-urile cu source ai_pm:XYZ"

**PAS 5** — Cere implementare
- În chat-ul Emergent: `Implementează TODO-urile cu source ai_pm:XYZ din /admin/todo. Folosește breakdown-ul existent.`
- Agentul (eu) îți va răspunde cu plan + îți cere confirmări dacă e nevoie

**PAS 6** — Testează în preview
- Verifică funcționalitatea în preview (URL-ul `*.preview.emergentagent.com`)
- Dacă ceva nu merge, raportează: "Pe preview, când fac X, văd Y"

**PAS 7** — Deploy
- Doar dacă e ok în preview, apasă butonul "Deploy" din interfața Emergent
- Schimbările ajung pe `https://propmanage.ro`

### Ce afectezi dacă SARI peste pași?
- **Sari peste Architecture Board** → risc construiești ceva deja existent (duplicat de cod, mai greu de întreținut)
- **Sari peste AI PM** → agentul Emergent nu are scope clar, întreabă mai mult sau face presupuneri
- **Sari peste preview test** → bug ajunge direct în producție pe propmanage.ro, clienții reali îl văd
- **Sari peste TODO injection** → agentul nu are istoric, contextul se pierde între sesiuni

---

<a id="3-governance"></a>
## 3. 🛡️ AI Governance Center (`/admin/ai-governance`)

### Ce face
Centru de observabilitate pentru toți cei 20+ agenți AI ai platformei. Vezi cine face ce, când, cât costă, și cine e sănătos.

### Cele 7 tab-uri și cum le folosești

#### Tab 1: **Agenți**
- Listă completă agenți grupați pe categorie
- Pe fiecare card vezi: nume, slug, lifecycle (active/legacy/deprecated/experimental), permission_level, activitate 24h/7d
- **Buton "Marchează ca depreciat"** pe fiecare → modal cu reason + replacement + target_retirement_date
- **Implicații marcare depreciat**: NU oprește agentul, doar îl etichetează ca "în retragere". Apare în Deprecation Plan + Pulse.

#### Tab 2: **Health** (NOU)
- 5 KPI: Overall, Healthy, Degraded, Silent, Deprecated
- Listă sortată: degraded/silent/error/healthy/deprecated
- Status derivat din activitate (zero activity 7d = silent; 7d active dar 24h zero = degraded)
- **Când acționezi**: dacă vezi un agent "silent" timp îndelungat → consideră deprecation

#### Tab 3: **Permissions** (NOU)
- Matrice 5 niveluri risc: read (0) → suggest (1) → execute-with-approval (2) → execute (3) → autonomous (4)
- **Risk hotspots**: agenți activi cu permisiuni înalte (execute/autonomous) — auditează lunar
- **Când acționezi**: orice nou agent cu permission `execute` sau `autonomous` trebuie să apară aici cu hotspot și să-l revizuiești

#### Tab 4: **Costuri**
- Estimare lunară EUR per agent (best-effort, bazat pe calls/săptămână + cost mediu per call)
- **Implicații**: dacă vezi costuri mari pe un agent legacy → candidat la deprecation
- Suma reală e în Profile → Universal Key → Billing

#### Tab 5: **Audit Trail**
- Eveniment unificat pe ultimele 50 acțiuni (chat sessions, dev team analyses, security alerts, etc.)
- **Când folosești**: pentru investigații post-incident

#### Tab 6: **Deprecation Plan**
- Timeline retragere agenți depreciati + impact snapshot (data sources, provider, activitate la decizie)
- Candidați propuși (legacy ne-tratați)
- Istoric restaurări
- **Buton "Restaurează"** pe fiecare deprecation → readuce agentul la lifecycle original

#### Tab 7: **Deprecation Pulse** (NOU)
- Schedule email săptămânal joi 09:30 cu 3 alerte: retrageri viitoare, overlap colecții, provider risk
- **CONFIGURARE OBLIGATORIE LA START**:
  1. Adaugă email-urile destinatare (al tău + backup): `founder@propmanage.ro, backup@gmail.com`
  2. Setează fereastra alertă: `30 zile` (default)
  3. Apasă "Activ"
  4. Apasă "Salvează config"
  5. (Opțional) Apasă "Trimite acum" — vezi cum arată

### Ce afectezi dacă greșești în Governance
- Marchezi greșit deprecated un agent → nimic critic, doar îl restaurezi din tab Deprecation Plan
- Activezi Pulse cu email greșit → primesc destinatarii greșiți emails. Editezi configul.
- **Nu există ștergere reală** în Governance — totul e overlay non-distructiv

---

<a id="4-arch"></a>
## 4. 🧭 Architecture Review Board (`/admin/architecture-board`)

### Ce face
Verifică dacă o idee se suprapune cu cele ~36 module existente. AI (Claude Haiku) îți dă verdict + sugestii.

### Cele 4 verdicts și ce să faci

| Verdict | Înseamnă | Acțiunea ta |
|---------|----------|-------------|
| `build_new` | Idee nouă, fără suprapunere semnificativă | Continuă spre AI PM |
| `extend_existing` | >50% overlap, ar trebui să extinzi modul existent | Cere agentului să EXTINDĂ acel modul, nu să creeze unul nou |
| `merge_proposal` | Suprapunere moderată, ar trebui să comasezi cu propunerea X | Documentează ca merge în Future Ideas |
| `reject_duplicate` | 95%+ overlap, este duplicat | NU construi. Folosește modulul existent. |

### Pași concreți
1. Mergi la `/admin/architecture-board`
2. Completează titlu (3-200 caractere), descriere (10-4000), scope (opțional)
3. Apasă "Verifică suprapuneri" (durează ~6-10s)
4. Citește: verdict, overlap_score, overlapping_modules, suggested_actions, rationale
5. **Decide**:
   - Dacă verdict îți place → continuă pipeline
   - Dacă nu ești de acord cu AI → revizuiește descrierea și reîncearcă

### Ce afectezi dacă greșești
- Trimiți review cu descriere proastă → AI dă verdict prost → tu construiești greșit. **Soluție**: refă review-ul cu descriere mai bună, șterge-l pe cel vechi.
- Reviews-uri NU triggerează cod. Sunt 100% diagnostic.

---

<a id="5-aipm"></a>
## 5. 🎯 AI Product Manager (`/admin/ai-pm`)

### Ce face
Transformă o idee într-o ierarhie clară: **Epic → Features → User Stories → Acceptance Criteria**.

### Pași concreți
1. Mergi la `/admin/ai-pm`
2. Titlu + descriere (obligatorii) + context business (opțional, dar îmbunătățește calitatea)
3. Apasă "Descompune ideea" (durează ~15-20s)
4. **Ce primești**:
   - **Epic**: titlu + goal + success_metric
   - **Features** (max 3): cu prioritate (P0/P1/P2/P3) + effort în zile + max 2 stories
   - **Stories**: format "Ca [user], vreau [X], ca să [Y]" + acceptance criteria + technical notes
   - **Riscuri** (max 3): titlu + mitigare + severitate
   - **Out of scope**: ce NU intră în versiunea curentă

### Cum injectezi în lucru
- După breakdown, apasă **"Injectează în TODO"**
- Toate features-urile devin task-uri în `/admin/todo` cu source `ai_pm:<id>`
- **Implicații**: agentul Emergent îi va vedea când îi ceri să construiască — îi dai context complet fără să fii nevoit să-l rescrii

### Ce afectezi dacă greșești
- Breakdown greșit → șterge-l, refă-l. NU se generează cod automat.
- Injectezi TODO-uri pe care nu le mai vrei → șterge-le din `/admin/todo`

---

<a id="6-pulse"></a>
## 6. 🔔 Deprecation Pulse (`/admin/ai-governance` → tab Deprecation Pulse)

### Ce face
Email săptămânal joi 09:30 (Europe/Bucharest) cu 3 alerte:
1. **Retrageri viitoare**: agenți deprecati cu target_retirement_date < 30 zile
2. **Overlap colecții**: agenți activi care folosesc data_sources marcate pentru retragere
3. **Provider risk**: agenți pe provideri flag-uiți (gpt_4o, claude_haiku — sunset risk)

### Configurare obligatorie (5 minute, o singură dată)
1. Tab "Deprecation Pulse"
2. Recipient: `founder@propmanage.ro` (sau email-ul tău principal)
3. Fereastră alertă: `30` (default)
4. Click "Activ" (toggle)
5. Click "Salvează config"
6. Click "Trimite acum" → verifică inbox

### Ce afectezi dacă greșești
- Email greșit → schimbi destinatarii și reactivezi
- Cantitate mare emails → mărește fereastra (>30 zile) sau dezactivează temporar

---

<a id="7-bugmem"></a>
## 7. 🐛 Bug Memory Aggregator (`/admin/bug-memory`)

### Ce face
Vedere unificată a TUTUROR findings de bugs din platformă:
- **QA Copilot findings** (din sesiuni manuale)
- **AI Investigator findings** (din analize automate)

### Când folosești
- Înainte de a începe un feature nou: caută bug-uri legate de același modul
- După un incident: caută cuvinte cheie din eroare ("timeout", "401", "undefined")
- Săptămânal: scan rapid Top 20 P0/P1

### Pași concreți
1. Mergi la `/admin/bug-memory`
2. Vezi stats: QA findings + AI findings + total
3. Filtre: severity (P0/P1/P2/P3), source (qa_copilot/ai_investigator)
4. Search box: caută text (>= 2 caractere)

### Ce afectezi
- 0% impact — read-only. Acțiunile pe findings rămân în modulele originale.

---

<a id="8-autonomy"></a>
## 8. 🤖 Autonomy Engine (`/admin/autonomy`)

### Ce face
Calculează zilnic scoruri de "autonomie" platformă pe 5 zone:

| Zonă | Greutate default | Ce măsoară |
|------|------------------|------------|
| **operational** | 30% | Auto-match, completed requests, scheduler health, incidente deschise |
| **technical** | 25% | Smoke tests pass rate, snapshot freshness |
| **security** | 20% | Threat scores, audit gaps |
| **dev** | 10% | Activitate AI Dev Team, QA Copilot, code coverage |
| **ai** | 15% | Cost AI per session, AI investigations resolved |

### Cum activezi zona "DEV" mai puternic
**Zona DEV este DEJA activă** (10% din scor general). Dacă vrei să o crești în prioritate:

1. Mergi la `/admin/autonomy` (sau direct: API config endpoint)
2. Caută secțiunea "Greutăți & Țintă" (dacă există UI) sau folosește endpoint:
   ```
   PUT /api/admin/autonomy/targets
   { "weights": { "operational": 0.25, "technical": 0.20, "security": 0.20, "dev": 0.25, "ai": 0.10 } }
   ```
3. **Implicații**: dev score va influența mai mult general score → recomandările dev vor apărea mai sus

### Cum materializezi recomandări ca TODO-uri
1. Pe pagina `/admin/autonomy`, în secțiunea "Recomandări prioritizate"
2. Apasă **"Materializează ca TODO-uri →"**
3. Apare modal de confirmare
4. Sunt create max 6 TODO-uri (cu dedupe — nu se duplică dacă există deja)
5. Le vezi în `/admin/todo` cu source `autonomy_v2:<area>`

### Ce afectezi dacă greșești greutățile
- Greutăți însumează 1.0 ideal, dar engine-ul nu va crăpa dacă nu
- Nu se șterge nimic real — doar prioritizarea recomandărilor se schimbă
- **Repair**: pune greutățile înapoi la default (30/25/20/10/15)

---

<a id="9-foundergate"></a>
## 9. 🚪 Founder Approval Gate (`/admin/founder-gate`)

### Ce face
Registry hardcoded cu 13 acțiuni critice care, în viitor, vor necesita aprobare dublă (email + SMS).

**Status actual**: `enable_founder_gate = false` (foundation only). FG-1 Twilio SMS este **DEFERRED** până validăm beta-ul.

### Acțiuni înregistrate (read-only deocamdată)
- Change Stripe destination account
- Bulk delete users / properties / requests
- Disable critical schedulers
- Change founder contact emails
- Promote agent to "autonomous" permission
- ... (vezi lista completă în `/admin/founder-gate`)

### Ce nu trebuie să faci
- ❌ NU activa `enable_founder_gate = true` până nu integrăm Twilio. Altfel acțiunile critice vor fi blocate fără mecanism de aprobare.

### Când vom activa FG-1
- După testare beta cu primii 10 clienți reali
- După ce decizi să integrăm Twilio (cont, număr RO, ~2-5€/lună)

---

<a id="10-futureideas"></a>
## 10. 💡 Future Ideas Vault (`/admin/future-ideas`)

### Ce face
Backlog strategic cu propuneri R&D. Fiecare propunere are: descriere, complexitate, risc, ROI estimat, decision log.

### Cum o folosești
1. Pentru idei MARI (>3 zile dev) → documentează aici ÎNTÂI
2. Pentru idei mici → sari direct la AI PM
3. Apasă "Aprobă" sau "Respinge" pe fiecare propunere → se salvează în decision_log

### Email săptămânal
- Lunea 09:15 primești digest cu propunerile noi/modificate

---

<a id="11-stages"></a>
## 11. 🎓 Stagii Progressive Disclosure (Junior → Verified → Pro)

**Status actual**: Sistemul Progressive Disclosure este **IMPLEMENTAT** și funcțional. Gestionare 100% din `/admin/experience-tiers`.

### Cum îl folosești în 5 pași

1. **Mergi la `/admin/experience-tiers`** → tab Overview vezi distribuția actuală
2. **Rulează "Dry-run"** ca să vezi câți useri sunt eligibili pentru promovare fără să-i promovezi
3. **Rulează "Rulează acum"** dacă vrei să-i promovezi imediat
4. **Tab Useri**: vezi fiecare user + cerințele lipsă; folosește "Override" pentru cazuri speciale (VIP, beta testers)
5. **Tab Configurare**: dezactivează cron-ul temporar dacă vrei, sau modifică praguri (via API PUT)

### Cum aplici tier-gating în pagini Client/Specialist/Operator
Primitivele sunt în `/app/frontend/src/lib/experienceTier.jsx`. Cere agentului:
```
Aplică TierGate cu min="verified" pe butonul "Bulk Export" din ClientDashboard.
Pentru juniori, afișează <UpgradeHint requiredTier="verified" />.
```

### Schema implementată

```
experience_tier: "junior" | "regular" | "verified" | "pro"
experience_tier_locked: bool   // admin override blochează auto-promotion
experience_tier_set_at: ISO    // ultima schimbare
```

### Cron automat
- Rulează **zilnic la 03:30 Europe/Bucharest**
- Scanează toți userii cu role `client` sau `specialist`
- Promovează automat pe cei eligibili (sărit userii locked)
- Audit log în collection `experience_tier_history`

### Triggers automate de promovare (configurabile)
| Tier | Criteriu (default) |
|------|-----------------|
| junior → regular | 7 zile activ + 3 cereri/oferte completate |
| regular → verified | 30 zile activ + 10 cereri completate + rating >= 4.5 |
| verified → pro | 90 zile + 30 cereri completate + email verificat + KYC complet |

### Features per tier (cum afectează UI)
- **Junior**: basic_dashboard, simple_request_creation, essential_messages
- **Regular**: + advanced_filters, saved_searches, request_templates, comparison_view, weekly_summary_email
- **Verified**: + bulk_operations, advanced_analytics, priority_matching, custom_notifications, export_data
- **Pro**: + api_access, white_label_reports, priority_support, early_access_features, dedicated_account_manager

### Cum folosești primitivele în cod (pentru tine — informativ)
```jsx
import { useTier, TierGate, TierBadge, UpgradeHint } from "../lib/experienceTier";

// 1) Hook pentru logică
const { tier, meetsTier, hasFeature } = useTier();
if (hasFeature("bulk_operations")) { ... }

// 2) Component gate
<TierGate min="regular" fallback={<UpgradeHint requiredTier="regular" />}>
  <AdvancedFilters />
</TierGate>

// 3) Badge profil
<TierBadge />
```

### Ce afectezi în RĂU dacă greșești
- Configurezi criteriile prea strict → niciun user nu promovează → UI simplu permanent (nu e dramatic)
- Configurezi prea relaxat → toți devin "pro" repede → UI complex pentru începători (frustration)
- Override manual greșit → un user vede UI greșit → tu schimbi din admin în secunde
- **Soluție rollback**: din Admin → tab Useri → găsește user → "Override" către tier-ul anterior

### Cum testezi UI-ul progressive cu conturi de test
1. Logează-te ca admin → `/admin/experience-tiers` → tab Useri
2. Selectează un cont de test (ex: `client@propmanage.io`) → click "Override"
3. Setează tier "junior" → check "Lock" → submit
4. Logout, login cu acel cont → vezi UI simplificat
5. Repetă cu "verified" → vezi UI complet
6. Inversezi cu "Override" back la junior + Unlock

---

<a id="12-roadmap"></a>
## 12. 🗺️ Ce mai e de făcut per modul (Roadmap detaliat)

### AI Governance Center — completitudine 75%
**Ce funcționează**:
- ✅ Agent registry (20 agenți indexați)
- ✅ Cost tracking (estimare)
- ✅ Audit trail unificat
- ✅ Health monitoring (NOU)
- ✅ Permissions matrix (NOU)
- ✅ Deprecation plan + Pulse (NOU)

**Ce MAI e de făcut**:
- 🟠 **Token-level cost tracking** — momentan estimăm prin calls × cost mediu. Pentru exact, ar trebui logged tokens per call.
- 🟠 **Real-time alerting** — momentan polling. Ideal websocket pentru alarme instant când un agent devine `error`.
- 🟢 **Performance benchmarks per agent** — timpi de răspuns 95th percentile, error rates.
- 🟢 **Cost forecasting** — predicție următoarea lună bazat pe trend.

### Founder Approval Gate — completitudine 25% (intentat, FG-1 DEFERRED)
**Ce funcționează**: FG-0 (foundation, registry 13 acțiuni)

**Ce MAI e de făcut**:
- ⏸️ **FG-1: Twilio SMS integration** — DEFERRED (după beta validation)
- ⏸️ **FG-2: TOTP fallback** (Google Authenticator) — DEFERRED
- ⏸️ **FG-3: Enforcement layer** — middleware care interceptează acțiunile critice și cere aprobare
- ⏸️ **FG-4: Audit log per acțiune protejată** — cine a aprobat, când, IP

### Architecture Review Board — completitudine 80%
**Ce funcționează**: catalog 36 module, AI overlap detection, verdict + suggested actions

**Ce MAI e de făcut**:
- 🟢 **Auto-update catalog** — momentan static în cod. Ideal scan auto al modulelor backend + admin pages.
- 🟢 **Link review → AI PM** — buton "Continuă în AI PM" direct din review result
- 🟢 **Export decision history** — PDF cu toate review-urile pentru audit

### AI Product Manager — completitudine 70%
**Ce funcționează**: breakdown Epic > Features > Stories + inject TODOs

**Ce MAI e de făcut**:
- 🟠 **Refinement mode** — buton "Refine" care ia un breakdown existent și-l rafinează cu feedback adițional
- 🟠 **Estimation re-calibration** — comparare effort estimat vs real (după ce TODOs sunt done)
- 🟢 **Multi-language** — momentan doar română, pentru clienți EN
- 🟢 **Templates per categorie** — preset-uri pentru "feature marketplace", "feature UX", etc.

### Bug Memory Aggregator — completitudine 90%
**Ce funcționează**: stats, search, filtre, unified feed

**Ce MAI e de făcut**:
- 🟢 **Auto-cluster bugs** — gruparea findings similare cu embeddings
- 🟢 **Resolved status sync** — când rezolvi un bug în QA Copilot, să se reflecte automat aici

### Autonomy Engine — completitudine 65% (acum cu V2 task generation)
**Ce funcționează**: 5 zone scoring, recomandări, snapshots zilnice, V2 task gen

**Ce MAI e de făcut**:
- 🟠 **Auto-execution mode** — pentru recomandări `low risk + high impact`, execute automat (cu Founder Gate)
- 🟢 **Custom KPI builder** — definești propriile signals dincolo de cele 5 zone default
- 🟢 **Tier promotion automation** — promovare auto user-tier (vezi cap 11)

### Smart Pipeline (idea → arch → pm → todos) — completitudine 30%
**Ce mai e de făcut**:
- 🟠 **Buton "Smart Pipeline"** unic care face toți 4 pașii dintr-un click
- 🟠 **Status tracking per idee** — vezi unde e fiecare idee în pipeline (arch_done / pm_done / todos_injected / built / deployed)
- 🟢 **Pipeline analytics** — câte idei aprobate vs respinse, timp mediu de la submit la deploy

---

<a id="13-cheatsheet"></a>
## 13. 🎯 Cheat-sheet: scenarii frecvente

### Scenariu 1: "Vreau să adaug o funcție nouă"
1. `/admin/architecture-board` → verifică suprapuneri
2. Dacă verdict ok → `/admin/ai-pm` → descompune
3. Inject TODOs → cere agentului să construiască
4. Test preview → deploy

### Scenariu 2: "Un agent face spam / nu mai funcționează"
1. `/admin/ai-governance` → tab Health → verifică status
2. Dacă "silent" sau "degraded" îndelung → tab Agenți → "Marchează ca depreciat"
3. Setezi target_retirement_date și replacement
4. NU se șterge cod, doar etichetare. Apare în Pulse-ul săptămânal.

### Scenariu 3: "Vreau să șterg date vechi în siguranță"
1. **NU șterge direct.** În schimb:
2. `/admin/snapshots` → "Crează snapshot acum" (ca plasă de siguranță)
3. Cere-mi (în chat): `Vreau să șterg cererile mai vechi de 1 an care sunt 'cancelled'. Fă-o cu dry_run primul.`
4. Eu îți arăt CE s-ar șterge (fără să-l fac)
5. Tu confirmi → execut

### Scenariu 4: "Pagina X nu mai merge în producție"
1. Verifică în PREVIEW dacă bug-ul există acolo
2. Dacă în preview merge → e problemă de deploy → contactează Emergent Support
3. Dacă în preview NU merge → spune-mi `Pe preview, când fac X, văd Y. Iată screenshot.`
4. Eu reproduc + fix + tu testezi în preview + redeploy

### Scenariu 5: "Vreau să rollback la o versiune anterioară"
1. **NU folosi git reset** (perde munca curentă)
2. În Emergent platform, folosește **butonul "Rollback"** (gratis, fără credite)
3. Selectezi checkpoint-ul anterior bun
4. Toată platforma revine la acel moment

### Scenariu 6: "Costul AI a crescut suspect"
1. `/admin/ai-governance` → tab Costuri
2. Sortează după "estimated_monthly_eur"
3. Top 3 agenți → verifică în tab Audit Trail dacă rulează prea des
4. Dacă unul e legacy + cost mare → marchează deprecated

### Scenariu 7: "Vreau să dau acces unui nou admin"
1. Creezi user-ul cu role `admin`
2. Cere-mi: `Adaugă admin@nume.com ca admin secundar. Vreau să poată vedea Governance dar NU să schimbe deprecations.`
3. Eu implementez fine-grained permissions (după FG-3 Enforcement layer e gata)

---

## 🔑 Demo Accounts Manager (`/admin/demo-accounts`)

**Scop:** 6 conturi destinate colaboratorilor externi care explorează platforma pe zona lor de expertiză. Tu controlezi parolele cu codul master **0108**.

**Cele 6 conturi pre-seedate:**
| Email | Parola implicită | Scope | Rol |
|---|---|---|---|
| `testing.admin@propmanage.io`   | `Test!Demo2026Strong`  | testing   | admin |
| `frontend.admin@propmanage.io`  | `Front!Demo2026Strong` | frontend  | admin |
| `backend.admin@propmanage.io`   | `Back!Demo2026Strong`  | backend   | admin |
| `security.admin@propmanage.io`  | `Sec!Demo2026Strong`   | security  | admin |
| `general.admin@propmanage.io`   | `Gen!Demo2026Strong`   | general   | admin |
| `marketing.admin@propmanage.io` | `Mkt!Demo2026Strong`   | marketing | marketing_manager |

**Acțiuni disponibile (super-admin only):**
- **Vezi parola** — click pe iconița ochi în UI.
- **Copy parola** — click iconița clipboard. Trimit-o prin email/Signal colaboratorului.
- **Reset implicit** — readuce parola la valoarea hardcoded (din `/app/backend/sub_admin_seed.py`). Util dacă un colaborator a schimbat-o.
- **Schimbă parola** — setezi una custom (min 8 caractere, litere + cifre).

**Cod master:** `0108` (hardcoded în `/app/backend/routes/demo_accounts.py` constant `MASTER_CODE`). Schimbă-l direct în fișier dacă vrei să-l rotești.

**Audit:** fiecare reset/schimbare e logată în `/var/log/supervisor/backend.*.log` cu email-ul super-adminului care a făcut acțiunea.

---

## 🛡️ Admin Accounts Manager (`/admin/admin-accounts`)

**Scop:** control complet asupra TUTUROR conturilor cu rol admin (inclusiv demo, operatori, marketing manager, conturi externe ca `carlospacu@gmail.com` și `danieligna1@gmail.com`).

**Ce poți face:**
- **Listă completă** — toți admin/super_admin/marketing_manager/operator cu filtru pe rol + search după email/nume.
- **Blochează / Activează** un cont — flag `is_active`. Userii blocați NU se pot loga (utile când apare ceva suspect).
- **Schimbă rolul + scope** — promovezi/demotezi între `admin`, `marketing_manager`, `operator`, `specialist`, `client` cu scope opțional (general/testing/frontend/backend/security/marketing/ops/ai/finance/legal/growth).
- **Schimbă parola** — direct pentru orice admin (inclusiv super-admin propriu pentru rotation).

**Cont PROTEJAT:** `admin@propmanage.io` (tu) — nu poate fi blocat sau demotat. Poate doar avea parola schimbată (de tine).

**Cod master:** `0108` pentru toate operațiile de scriere.

### Scenariu 9: "Vreau să verific accesul unui admin extern"
1. `/admin/admin-accounts` → search după email (ex: `carlospacu`)
2. Vezi rol curent, scope, ultimul login, status activ
3. Decizie:
   - Suspect → click **Ban** (rosu) → cod 0108 → blocat instant
   - Schimbă scope/rol → click **UserCog** (violet) → alege rol + scope + cod 0108
   - Rotire parolă → click **KeyRound** (fuchsia) → parolă nouă + cod 0108

### Scenariu 10: "Am blocat din greșeală un admin"
1. `/admin/admin-accounts` → filter "BLOCAT" sau scroll
2. Click iconița **Play** (verde) → cod 0108 → cont activat din nou

### Scenariu 11: "Vreau să schimb parola super-admin (propriul cont)"
1. `/admin/admin-accounts` → găsește rândul `admin@propmanage.io` (badge PROTECT)
2. Click **KeyRound** → parolă nouă min 8 chars + cod 0108
3. ATENȚIE: salvează parola într-un password manager înainte de submit. Dacă o uiți, recuperarea cere intervenție directă în DB.

---

## 📞 Când să-mi ceri ajutor

- **Înainte de orice schimbare majoră**: cere-mi review (nu coda fără să discutăm)
- **Când vezi un bug**: dă-mi screenshot + steps to reproduce
- **Când vrei o funcție nouă**: trece prin Architecture Board PRIMUL, apoi pipeline normal
- **Când nu înțelegi un mesaj de eroare**: copiază-l și întreabă

---

*Manual versiune 1.1 — Feb 26, 2026. Re-citește când platforma evoluează semnificativ.*

---

# PARTEA II — Modulele din Iunie 2026 (Command Center, Autonomie, Design)

> ⚠️ **CONFIDENȚIAL — doar pentru owner (danieligna1@gmail.com).** Din 11 Iunie 2026 acest manual este vizibil DOAR pentru tine. Ceilalți admini primesc 403.

## 14. 🧠 AI Command Center (`/admin/command-center`)
**Ce face**: centrul tău de comandă zilnic. Feed cu cifrele de azi + alerte (cereri >48h, escrow neconfirmat, specialiști incompleți, dispute) + Top 5 recomandări AI generate de Claude pe datele reale.
**Cum operezi**: dimineața primești automat EMAIL cu digestul (cron 07:00). În pagină: apasă «Generează» pentru recomandări proaspete → fiecare are buton «Deschide» (te duce direct la modul) și cerc de bifare «rezolvat». Alertele HEALTH vin automat din Business Health (departament ROȘU = alertă aici).
**Dacă greșești**: nimic ireversibil — recomandările se regenerează, bifările se pot debifa.

## 15. 📊 Business Health (`/admin/business-health`)
**Ce face**: 8 scoruri pe departamente (Marketing/Marketplace/Escrow/Specialiști/Suport/Conversii/SEO/Financiar), VERDE ≥80 / GALBEN ≥60 / ROȘU <60, formule deterministe pe datele din DB.
**Cum operezi**: doar citești. Snapshot-ul se salvează singur zilnic → sparkline-urile arată trendul. Roșu = apare automat în Command Center + Notification Center.

## 16. 🗺 Roadmap · Evoluție (`/admin/roadmap`)
**Ce face**: board-ul tău de evoluție — 21+ module cu «✓ construit / ○ de construit», ROȘU urgent / GALBEN prioritar / VERDE îmbunătățire, progres %.
**Cum operezi**: expandează un modul → poți schimba prioritatea/statusul/progresul cu butoanele. «Analizează cu AI» → Claude îți spune ce să construiești săptămâna asta. Board-ul e sursa de adevăr — eu (agentul) îl actualizez după fiecare sesiune.

## 17. 📡 Marketplace Intelligence (`/admin/marketplace-intel`)
**Ce face**: cerere vs capacitate per categorie (capacitate = specialiști × 4 lucrări/lună) cu % DEFICIT/SUPRAOFERTĂ + City Analytics pe județe + Radar trenduri ±% 30 zile.
**Cum operezi**: «Recomandă» → AI îți spune unde recrutezi și unde promovezi. Categoriile 🔥 hot (creștere ≥30%) sunt oportunități de campanie.

## 18. 💰 Financial Cockpit (`/admin/financial-cockpit`)
**Ce face**: Revenue 30z cu growth, Escrow complet (blocat/înghețat/eliberat), MRR/ARR din abonamente, TVA estimat 21%, Cash Flow 30 zile, AI Insights financiare.
**Cum operezi**: citești + «Generează insights» pentru analiza AI a cifrelor.

## 19. ⚙️ Automation Center (`/admin/automation`)
**Ce face**: reguli Dacă→Atunci cu executor REAL: reminder cereri blocate (notifică adminii), badge ⚡ Fast Response, reactivare clienți inactivi (coadă email).
**Cum operezi**: activează regula cu switch-ul → **scheduler-ul le rulează SINGUR** (orar, max 1×/interval — implicit 24h). Poți schimba parametrul (ore/minute/zile) direct în card. «Rulează acum» = execuție manuală imediată. Istoricul execuțiilor e jos.
**⚠️ Important**: regulă DEZACTIVATĂ = dependență de om = scade scorul HDI (vezi §22).

## 20. 👑 CEO Dashboard (`/admin/ceo`) — DOAR TU
**Ce face**: vederea ta strategică: Business Score, Revenue ▲%, Cash Flow OK/ATENȚIE, Escrow, MRR/ARR, «AI spune: prioritățile tale azi» (top 3 nerezolvate), puls departamente.
**Acces**: doar super-admin general. Sub-adminii scoped primesc 403.

## 21. 🔔 Notification Center (`/admin/notification-center`)
**Ce face**: «Ai N lucruri importante» — TOT ce cere atenție, într-un singur loc: alerte operaționale + Business Health roșu + recomandări AI nerezolvate + anomalii Audit Sentinel. Sortate pe severitate, cu buton «Rezolvă» (link direct).
**Cum operezi**: bifezi cercul = ascuns până mâine (ack per zi). Item-ele se regenerează zilnic.

## 22. 🤖 Human Dependency Index — a 5-a axă Autonomy Engine (`/admin` → AI Lab → Autonomy)
**Ce face**: O SINGURĂ CIFRĂ care îți arată cât de aproape e platforma de a funcționa singură. 100 = zero intervenții umane pendinte. Formula: penalizează cereri blocate >48h, escrow neconfirmat, dispute deschise, reguli de automatizare OPRITE, recomandări AI nebifate, anomalii de audit.
**Cum îl crești**: activează regulile din Automation, triază disputele, confirmă escrow-urile, bifează recomandările rezolvate.

## 23. 🔍 AI Search (`/admin/ai-search`)
**Ce face**: vorbești cu datele. Exemple: «cereri peste 20.000 lei», «specialiști fără portofoliu», «cereri din Cluj», «plăți peste 500 lei». Claude traduce în filtre sigure (doar câmpuri whitelisted) → tabel cu rezultate.

## 24. 🕐 User Timeline (`/admin/user-timeline`)
**Ce face**: cronologia completă a oricărui utilizator: cont → verificare → cereri → asignări → escrow → plăți → review-uri. Cauți după email/nume, selectezi, vezi tot.

## 25. 🛡 Audit Sentinel (rulează singur, orar)
**Ce face**: detectează anomalii în loguri: >200 request-uri/oră per user, ≥10 erori 4xx în fereastră scurtă, ≥5 acțiuni admin refuzate/oră (tentative out-of-scope). Anomaliile noi → notificare in-app + apar în Notification Center.
**Cum operezi**: nimic — e autonom. Verifici anomaliile în Notification Center; se pot rezolva via API sau se rezolvă natural (dedupe pe zi).

## 26. 🎨 Design Studio + Design Intelligence (`/admin/design-studio`, `/admin/design-intelligence`)
**Ce face**: Design Studio = tokens, teme, presets, Palette Cascade (5 culori → 20 tokens). Design Intelligence = Layout/Component Optimizer AI cu Impact Score per propunere + Evolution Engine (Propus→Testare→Aprobat→Aplicat LIVE, cu rollback).
**Regula de aur**: NIMIC nu se aplică pe platformă fără aprobarea ta. Orice aplicare de tokens are snapshot → «Rollback» readuce exact starea anterioară.

## 27. ⏰ Ce rulează SINGUR (cron-uri relevante pentru tine)
| Când | Ce | Efect |
|---|---|---|
| 07:00 zilnic | Command Center morning | Feed + recomandări regenerate + **EMAIL către tine** + semnal orchestrator (alerte HEALTH) |
| Orar (min :12) | Automation rules tick | Rulează regulile ACTIVE al căror interval a expirat |
| Orar (min :40) | Audit Sentinel scan | Detectează anomalii în loguri |
| 03:15 zilnic | Autonomy snapshot | Istoric scoruri (inclusiv HDI) |
| La primul GET/zi | Business Health snapshot | Alimentează sparkline-urile |
| 05:10 zilnic | Marketplace Medic | Suspendă specialiști cu ≥dispute prag |
| Luni 09:30 | Founder Digest | Email KPI săptămânal |

## 28. 🏛 Viziunea XOS (Experience OS) — pe board, de construit
Direcția aprobată: «platforma care construiește alte platforme» — Layout Builder, Widget Manager, Role Experience, Franchise/White-Label per oraș, Visibility Engine, Content Manager. Stadiul real: Design Tokens ✓, Theme Manager ✓, Component Library ✓, AI Experience Optimizer ✓ (= Design Intelligence). Restul sunt pe `/admin/roadmap` grupate sub «Experience OS».

## 29. 🆘 Cheat-sheet rapid
- **«Ce fac azi?»** → CEO Dashboard sau emailul de la 07:00.
- **«De ce a scăzut scorul general de autonomie?»** → Autonomy Engine → axa Human — vezi exact ce așteaptă om.
- **«Vreau să găsesc ceva în date»** → AI Search, scrii în română.
- **«Ce s-a întâmplat cu utilizatorul X?»** → User Timeline.
- **«Ce a făcut platforma singură?»** → Orchestrator → Ledger + Automation → Istoric execuții.
- **«Vreau altă culoare/temă»** → Design Studio (nu cere cod).
