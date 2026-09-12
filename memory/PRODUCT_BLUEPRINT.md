# PROPMANAGE — PRODUCT ARCHITECTURE BLUEPRINT (Phase 0)
**Documentul care ghidează dezvoltarea următorilor 3 ani.**
Data: Iulie 2026 · Autor: Principal Product Architect · Status: FUNDAMENT — orice decizie de produs se validează contra acestui document.
Complementar cu: PLATFORM_AUDIT_2026.md (starea actuală), AUTONOMOUS_EVOLUTION_ROADMAP.md, CONSTRUCTION_INTELLIGENCE_ROADMAP.md.

---

# 1. PRODUCT VISION

## 1.1 Ce este PropManage? (răspunsul definitiv)

**PropManage este un Property Intelligence Operating System — sistemul de operare al locuinței, condus de AI.**

Nu este marketplace. Nu este CRM. Nu este ERP. Acestea sunt **organe**, nu identitatea. Definiția pe straturi:

```
┌─────────────────────────────────────────────────────────────┐
│  IDENTITATE:  Property Intelligence OS                       │
│  „Casa ta are un sistem de operare. Se numește PropManage." │
├─────────────────────────────────────────────────────────────┤
│  STRAT 4 · AUTONOMIE      Autonomy Engine + Orchestrator     │
│    platforma se operează singură; omul decide, nu execută    │
├─────────────────────────────────────────────────────────────┤
│  STRAT 3 · INTELIGENȚĂ    AI, Price Observatory, Pattern     │
│    Hunter, House Health scoring, triage, recomandări         │
├─────────────────────────────────────────────────────────────┤
│  STRAT 2 · TRANZACȚIE     Marketplace, Escrow, Wallet,       │
│    Dispute, Contracte, Token Economy                         │
├─────────────────────────────────────────────────────────────┤
│  STRAT 1 · DATE           Proprietate, Digital Twin, House   │
│    Health, Audit, Taxonomie construcții, Istoricul lucrărilor│
└─────────────────────────────────────────────────────────────┘
```

**Regula de aur a identității:** *Datele despre casă sunt produsul. Marketplace-ul este doar cea mai profitabilă consecință a lor.*
Competitorii pot copia un marketplace în 6 luni. Nu pot copia 3 ani de istoric structurat al fiecărei case (twin + health + audit + prețuri reale plătite).

## 1.2 Cele 3 promisiuni (una per parte a pieței)

| Către | Promisiunea | Metrica promisiunii |
|---|---|---|
| **Client** | „Casa ta se întreține aproape singură." | ore de grijă economisite / lună |
| **Specialist** | „Îți umplem calendarul și îți creștem venitul." | venit prin platformă vs. venit solo |
| **Piață/B2B** | „Adevărul despre orice imobil și orice preț." | acuratețea Observatory + Verified Estate |

## 1.3 Anti-viziune (ce refuzăm să devenim)
- ❌ Un director de anunțuri (fără escrow, fără date, fără răspundere) — asta e OLX Servicii.
- ❌ Un ERP greu, configurabil la infinit — ucide adopția rezidențială.
- ❌ Un chatbot generic peste un marketplace — AI-ul nostru execută, nu conversează decorativ.
- ❌ Feature factory: nicio funcție nouă fără loc clar în Ecosystem Map (§3) și un owner de strat.

## 1.4 North Star & metrici de gardă
- **North Star:** *Ore de muncă umană economisite lunar* (client + specialist + admin; sursa: orchestrator ledger + automatizări + auto-match).
- Gardă 1: GMV escrow lunar (sănătatea tranzacțională).
- Gardă 2: % case cu twin + health activ (sănătatea stratului de date).
- Gardă 3: NPS specialist (fără supply sănătos, totul moare).

---

## 1.5 PRINCIPIILE FUNDAMENTALE (ratificate de owner — prioritate peste orice implementare)

1. **PropManage nu administrează proprietăți. Administrează ciclul de viață al unei proprietăți.** Testul oricărei funcționalități: *„Cum ajută asta proprietatea să fie mai sănătoasă, mai valoroasă, mai ușor de administrat și mai ușor de tranzacționat?"* Fără răspuns clar → nu se construiește.
2. **Efect de rețea obligatoriu.** Fiecare modul nou consumă date din alte module ȘI produce date utile altora (Health → Twin → Audit → Marketplace → AI → Analytics → Observatory → Autonomy). Un modul care nu contribuie la buclă își reconsideră existența.
3. **AI nu este o funcționalitate — este stratul de orchestrare.** Nu „AI Features", ci AI prezent în fiecare flux important fără să pară modul separat: **observă → recomandă → execută unde are permisiuni → învață.**
4. **Fiecare utilizator simte că platforma lucrează pentru el.** Standardul tuturor dashboard-urilor = AI Workspace (§8): spații care generează acțiuni, nu pagini care afișează informații.
5. **Datele sunt activul principal.** Marketplace, escrow, wallet — importante, dar valoarea companiei = datele despre proprietăți + inteligența generată din ele. Orice dezvoltare îmbogățește baza de cunoștințe.
6. **Nicio funcționalitate fără clasificare.** Înainte de implementare, fiecare feature primește obligatoriu: **clasa** (CORE/AI/AUTONOMY/BUSINESS/PREMIUM/GROWTH/INFRASTRUCTURE/EXPERIMENTAL/LEGACY), **versiunea** în care intră, **dependențele** (contra §4), **impactul** asupra altor module, **KPI-urile** urmărite.

---

# 2. USER JOURNEYS (per persona)

> Format: Stadii → momentul adevărului (✦) → unde intervine AI Workspace-ul (⚙).

## 2.1 CLIENT — „proprietarul care nu vrea să se gândească la casă"
```
Descoperă (SEO preț/ghid, recomandare) → Se înregistrează → MISIUNE 1: adaugă
proprietatea → ✦ primește instant House Health preliminar + „harta riscurilor"
→ Twin light (5 min, ghidat) → prima cerere prin wizard (AI precompletează)
→ ✦ escrow = momentul încrederii → lucrare finalizată → review → ⚙ Home
Assistant preia: revizii sezoniere propuse, buget anual estimat, alerte
(centrala, garanții expiră) → upgrade Verified/Premium → recomandă vecinilor.
```
- **Bucla de retenție:** casa generează evenimente (sezon, vârstă instalații, istoricul din twin) → Home Assistant le transformă în acțiuni cu preț estimat → clientul aprobă cu 1 tap.
- **Eșecuri de evitat:** cerere fără ofertă în 24h (ucide încrederea la prima interacțiune); onboarding fără „aha" în primele 5 minute (health score preliminar E obligatoriu).

## 2.2 SPECIALIST — „meșterul care vrea calendar plin, nu marketing"
```
Invitat (funnel recrutare/organic) → înregistrare pre-completată pe categorie
→ MISIUNE: profil + KYC (⚙ AI validează pe loc: „recomandat spre aprobare")
→ ✦ prima oportunitate potrivită în <48h → ofertă → lucrare → ✦ prima plată
din escrow (fără să alerge după bani) → review → reputație compusă → ⚙
Business Assistant: „ești cu 12% sub media expert din Cluj; fă X ca să treci
la Verified" → subscripție pentru vizibilitate/leads → devine ambasador.
```
- **Bucla de venit:** reputație ↑ → matching prioritar → venit ↑ → dependență pozitivă de platformă.
- **Eșecuri de evitat:** KYC care durează zile (avem AI-recommendation — SLA țintă: decizie <4h); zile fără nicio oportunitate afișată (Assistant umple golul cu acțiuni de profil).

## 2.3 OPERATOR — „ochii platformei pe teren"
```
Cont creat de admin → coadă de verificări (imobile, twin-uri, audituri) →
programare vizite → colectare date structurate (foto, pins, măsurători) →
✦ raportul lui alimentează Verified Estate & House Health → sesizări NC →
⚙ Operations Assistant: rută optimă a zilei, ce lipsește fiecărui dosar,
prioritizare după valoarea comercială a imobilului.
```

## 2.4 ADMIN — „de la pompier la comandant"
```
Azi: patrulează 86 pagini. Țintă: ✦ deschide Control Tower → Attention Layer
(top 5 decizii care cer om AZI: escaladări, KYC review, dispute triate care
așteaptă mediere, categorii cu cerere fără supply) → decide cu 1 click pe
propunerile AI → restul e raportat retroactiv de Autonomy Report („platforma
a rezolvat singură 34 situații, ~6h economisite").
```
- **Principiu:** adminul nu mai caută probleme; problemele vin sortate, cu soluția atașată.

## 2.5 BUSINESS (owner/CEO — azi = fondatorul)
```
Întrebările lui: Crește GMV-ul? Unde pierdem bani? Ce oraș/categorie explodează?
→ ⚙ CEO Dashboard: P&L per motor de venit (comision/abonamente/B2B), funnel
achiziție (campanii QR → conversie), unit economics per categorie (din
Observatory + escrow real), alerte de anomalie (Finance Reconciler).
✦ momentul adevărului: primul raport lunar generat automat, trimis pe email.
```

## 2.6 INVESTITOR — „de ce valorează asta 10x?"
```
Nu are cont azi (corect). Primește: Data Room generat din platformă →
✦ metrici live: North Star, GMV, % case cu twin, ledger de autonomie
(„platforma rulează cu 0.5 FTE operațional"), harta acoperirii naționale.
→ V3.0: portal read-only cu metrici auditabile.
```

## 2.7 PARTENER (marketplace partners, city partners, strategic)
```
Onboarding de admin → ✦ primul lead livrat → dashboard partener (leads,
conversie, facturare) → ⚙ Partner Assistant (V2.5): calitatea lead-urilor,
sugestii de ofertă, benchmark categoric. B2B estate: imobil verificat →
certificat sănătate → listare premium.
```

---

# 3. ECOSYSTEM MAP — cum circulă informația (scheletul)

```
                                CLIENT
                                  │ creează
                                  ▼
   ┌─────────────────────── PROPRIETATE ────────────────────────┐
   │                           │                                │
   │        completează        ▼           inspectează          │
   │  DIGITAL TWIN ◄──── HOUSE HEALTH ────► AUDIT (operator)    │
   │  (structura fizică)  (scor + riscuri)  (adevăr verificat)  │
   └────────────┬─────────────┬────────────────┬────────────────┘
                │ generează   │ recomandă      │ certifică
                ▼             ▼                ▼
            CERERE ◄── AI RECOMMENDATIONS   VERIFIED ESTATE (B2B)
                │  (Home Assistant)
                ▼ matching (taxonomie CIP + visibility gate)
           SPECIALIST ──► OFERTĂ ──► PROIECT/LUCRARE
                │                        │
                │ reputație              ▼ bani blocați
             REVIEW ◄──────────── ESCROW/WALLET ──► TOKENI (earn/spend)
                │                        │
                │ conflict?              ▼
             DISPUTĂ ──► AI TRIAGE ──► MEDIERE ──► SPLIT
                                         │
   fiecare tranzacție & eveniment alimentează:
                                         ▼
        ANALYTICS ──► PRICE OBSERVATORY ──► SEO/GROWTH (achiziție nouă)
                │            │
                ▼            ▼
        PATTERN HUNTER   prețuri orientative în wizard (buclă închisă)
                │
                ▼ semnale
        AUTONOMY ENGINE + ORCHESTRATOR (7→12 playbooks)
                │ acționează asupra TUTUROR modulelor de mai sus
                ▼
        LEDGER „minute umane salvate" ──► CEO Dashboard / Investitor
```

**3 legi ale ecosistemului:**
1. **Legea îmbogățirii:** orice interacțiune trebuie să lase date structurate în Stratul 1 (o lucrare finalizată actualizează twin + health + observatory). Feature care consumă date fără să producă = taxă pe ecosistem.
2. **Legea semnalului:** modulele nu se apelează direct între ele pentru efecte cross-domain; publică semnale în Orchestrator (deja implementat — se generalizează).
3. **Legea buclei închise:** fiecare flux se termină acolo unde poate reporni (review → reputație → matching; observatory → SEO → client nou → observație nouă).

---

# 4. FEATURE DEPENDENCY MAP

> Săgeata = „are nevoie de". Nu construi nodul de sus fără fundația de jos.

```
NIVEL 0 · FUNDAȚII        Auth+Roluri → Proprietăți → Taxonomie CIP → Wallet
NIVEL 1 · DATE CASĂ       Digital Twin ──► House Health ──► Audit
                                │               │              │
NIVEL 2 · TRANZACȚIE      Cereri(wizard) ◄─────┘              │
                                │  matching (necesită taxonomie + gate)
                          Oferte/Proiecte ──► Escrow ──► Review/Reputație
                                │                │
NIVEL 3 · ÎNCREDERE       Dispute+Triage AI   KYC+AI ──► Verified Estate ◄── Audit
                                │
NIVEL 4 · INTELIGENȚĂ     Analytics ──► Price Observatory (necesită tranzacții+taxonomie)
                                │              │
                          Pattern Hunter   AI Recommendations (necesită health+twin+observatory)
                                │              │
NIVEL 5 · CREȘTERE        SEO programatic (necesită observatory) · Funnel recrutare
                          (necesită gate) · Token Economy (necesită wallet+misiuni)
NIVEL 6 · AUTONOMIE       Orchestrator playbooks (necesită TOATE semnalele de jos)
                          AI Workspaces per rol (necesită niv. 4 complet pe rolul respectiv)
```

**Consecințe practice (dependențe critice de respectat):**
- *AI Workspace Client* fără House Health activ pe proprietate = recomandări goale → misiunea de onboarding trebuie să forțeze twin light + health ÎNAINTE de a promite asistentul.
- *Token Economy* fără catalog de cheltuire = datorie de produs → se lansează doar cu earn+spend simultan.
- *Verified Estate* la scară fără Operator tooling matur = gât de sticlă uman → Operations Assistant precede expansiunea B2B.
- *SEO din Observatory* fără trust grading vizibil = risc reputațional → paginile publice afișează doar agregate cu ≥2 surse sau marcaj „preliminar".

---

# 5. PRODUCT ROADMAP — 3 ANI (pe versiuni, nu pe faze)

> Fazele 1-5 din audit trăiesc ÎN interiorul versiunilor de mai jos.

### V2.0 — „Fundația Asistată" (T3-T4 2026)
Temă: stabilizare + primele AI Workspaces. Conține Phase 1 + 2 + începutul 3.
- Stabilizare tehnică (lazy-loading, vocabular unificat, indexuri, api client) — *Phase 1*
- **Admin → Executive Control Tower v1** (Attention Layer + Pulse + Autonomy Report) — *Phase 2*
- **Specialist Cockpit v1** (Pipeline & Bani + benchmark Observatory) — *Phase 3*
- Sistem de Misiuni unificat (onboarding gamificat, per rol)
- Criteriu de ieșire: Client V1 retras; North Star măsurat automat lunar.

### V2.5 — „Client Copilot & Growth" (T1-T2 2027)
Temă: partea de cerere devine asistată; achiziția devine organică.
- **Client → Home Assistant v1** (Next Best Action din health+twin+sezon+istoric)
- Wizard pas 0 AI (descriere liberă/foto → cerere precompletată)
- SEO programatic din Observatory (sute de pagini preț/oraș) + pagini „Devino specialist în X"
- Token Economy v1 (earn: misiuni/review-uri/recomandări · spend: boost cerere, rapoarte premium, prioritate)
- Partner Dashboard v1 · Operations Assistant v1 (rută + dosare)
- Criteriu de ieșire: ≥30% din cereri provin din recomandările asistentului sau SEO.

### V3.0 — „Intelligence Platform" (T3-T4 2027)
Temă: datele devin produs vandabil; autonomia devine completă pe operațiuni repetitive.
- Price Observatory public cu rapoarte de piață vandabile (CIP-C/D)
- Verified Estate × Twin: **Certificatul de Sănătate al Imobilului** (standard la vânzare/închiriere)
- Autonomy 2.0: Pattern Hunter, Finance Reconciler, Roadmap Advisor; triage cu auto-aplicare la praguri mici
- CEO Dashboard v1 + portal investitor read-only
- Dispute Triage v2 cu feedback loop de învățare
- Criteriu de ieșire: platforma rulează 7 zile fără intervenție admin pe operațiuni standard (măsurabil în ledger).

### V4.0 — „Ecosystem & Scale" (2028)
Temă: de la aplicație la infrastructură de piață.
- Marketplace Produse complet (materiale legate de deviz/proiect — azi embrionar în parteneri)
- Finanțare lucrări (BNPL/credit punte cu partener bancar; escrow-ul devine avantaj regulator)
- Asigurări parametrice pe House Health score (partener)
- Multi-property management (administratori de bloc/portofolii — upgrade natural al rolului operator)
- Criteriu de ieșire: ≥2 motoare de venit non-comision depășesc 25% din revenue.

### V-Enterprise (paralel cu V3.0+)
- Dezvoltatori imobiliari: twin la predare, garanții structurate, defect management
- Administratori de portofolii: sute de unități, SLA-uri, rapoarte flotă
- Bănci/asigurători: acces API la health/certificate (cu consimțământ)

### V-Europe (după validare RO, 2028+)
- Precondiții: taxonomie multi-limbă (schema deja permite), Observatory per țară, echivalări KYC/legal
- Strategie: un oraș-far per țară (nu țară întreagă), cu funnel-ul de recrutare deja automatizat

### V-API (începe devreme, crește continuu)
- Etapa 1 (V2.5): webhooks parteneri + read-only API (listări, prețuri agregate)
- Etapa 2 (V3.0): API public cu chei — health score, certificat, taxonomie, prețuri (freemium/metered)
- Etapa 3 (V4.0): App marketplace intern (integrări terți pe orchestrator ca platformă de evenimente)

### V-White Label (doar după V3.0)
- Ținte: francize de mentenanță, utilități, retaileri DIY, asociații de proprietari mari
- Precondiție tehnică: tema/tokens layer formalizat (design system §5 audit) + feature flags per tenant
- Decizie de amânat conștient: multi-tenancy real e scump; nu înainte de a domina piața proprie.

---

# 6. MODULE OWNERSHIP (clasificarea întregului inventar)

| Clasă | Definiție & regulă de investiție | Module |
|---|---|---|
| **CORE** (nu se negociază; orice regresie = P0) | primesc refactor și teste prioritar | Auth+Roluri, Proprietăți, Cereri+Matching, Escrow/Wallet/Plăți, Dispute, Review, Notificări, Taxonomie CIP, KYC |
| **AI** (diferențiatorul; buget LLM controlat prin Gateway) | AI Recommendations, Dispute Triage, KYC Vision, Concierge, QA Copilot, AI Findings/Repair, Pattern Hunter (viitor) |
| **AUTONOMIE** (sistemul nervos; doar prin semnale) | Autonomy Engine, Autopilot, Orchestrator+playbooks, Smoke Monitor, Morning Briefing |
| **PREMIUM** (monetizare directă; se măsoară în revenue) | House Health plans, Digital Twin avansat, Client Premium, Subscripții specialiști (viitor), Rapoarte Observatory (viitor) |
| **BUSINESS/B2B** | Verified Estate, Marketplace/City/Strategic Partners, Contracts, CEO Dashboard (viitor) |
| **GROWTH** | Analytics campanii+QR, SEO/ghiduri/slugs, Landing presets, Onboarding emails, Funnel recrutare, Referral |
| **INFRASTRUCTURE** | GDPR, Legal, Audit log, Security, Sub-admins+Scopes, App settings, Backups, Incidents |
| **EXPERIMENTAL** (time-boxed: promovare sau eliminare în 2 cicluri) | Community, Experience Spaces, Interior Design flows, Concierge bubble, Token Economy v0 |
| **LEGACY** (înghețate; doar bugfix critic; țintă de retragere) | ClientDashboard V1, Components.jsx (v1), OperatorTwin (dublura), Dashboards.jsx agregator, FutureIdeasVault (mutat în proces, nu pagină) |

**Reguli de guvernanță:**
1. Un modul EXPERIMENTAL nu poate primi dependențe din CORE (doar invers).
2. LEGACY nu primește feature-uri — cine cere feature pe legacy finanțează migrarea.
3. Fiecare modul nou se naște cu clasă declarată în acest tabel (PR-ul o menționează).

---

# 7. TECHNICAL DEBT REGISTER

> Scală: Prioritate P0-P3 · Impact/Cost 1-5 · Riscul = ce se întâmplă dacă ignorăm.

| ID | Datorie | Prio | Impact | Cost | Risc dacă ignorăm | Dependențe |
|---|---|---|---|---|---|---|
| TD-01 | App.js monolitic, fără lazy-loading (1.711 l., ~140 pagini importate eager) | P0 | 5 | 2 | TTI mobil degradează cu fiecare pagină nouă; scor SEO scade | niciuna — start imediat |
| TD-02 | Dualitate Client V1/V2 (939 l. legacy + switch) | P0 | 5 | 3 | bug-uri fixate într-o singură versiune; confuzie utilizatori | paritate V2 (Interior Design, Job Filters) |
| TD-03 | Vocabular categorii istoric (painting/carpentry/... în users vechi) | P0 | 4 | 1 | matching ratează specialiști; coverage/gate subraportate | backup înainte de migrare |
| TD-04 | admin_console.py 2.745 l. + digital_twin.py 2.327 l. + auth.py 1.631 l. | P1 | 4 | 3 | fiecare edit = risc regresie; onboarding dev lent | TD-01 nu e necesar; se face pe module atinse |
| TD-05 | ~30 instanțe axios.create locale, fără interceptori comuni | P1 | 3 | 2 | tratare 401/erori inconsistentă; cod duplicat | se rezolvă odată cu paginile atinse |
| TD-06 | 185 colecții fără registru de scheme / response models | P1 | 4 | 2 | drift de câmpuri; bug-uri de contract FE-BE | generare semi-automată |
| TD-07 | Indexuri Mongo lipsă pe query-uri fierbinți (users role/categories, requests status, notifications user_id) | P1 | 4 | 1 | degradare la 10k+ utilizatori | audit query-uri întâi |
| TD-08 | Fără TTL/cap pe telemetrie (analytics_events, audit_log) | P2 | 3 | 1 | creștere disc necontrolată | — |
| TD-09 | Doar 2 hooks custom; fetch/paginate/toast duplicate în zeci de pagini | P2 | 3 | 2 | viteza de dezvoltare scade constant | lib/api.js (TD-05) |
| TD-10 | Duplicate FE: ComponentsV2, OperatorTwin/OperatorDigitalTwin, Dashboards.jsx | P2 | 2 | 2 | confuzie „care e sursa"; bundle umflat | TD-02 pentru client |
| TD-11 | Dublu sistem de niveluri (experience_tiers vs. mesaj comercial vs. autonomy tier badge) | P2 | 3 | 2 | progresie confuză; gamification diluat | decizia de naming din Blueprint §2 |
| TD-12 | Statusuri/enums definite dublu FE+BE (STATUS_LABEL vs. literals backend) | P2 | 2 | 2 | drift la adăugare status nou | TD-06 |
| TD-13 | Apeluri LLM împrăștiate (kyc, admin_ai, marketplace, orchestrator) fără buget/cache/log unic | P2 | 3 | 2 | cost LLM impredictibil la scară | AI Gateway (V2.5) |
| TD-14 | Joins în Python (medic scan per-dispută; projects→properties) | P3 | 2 | 2 | latență la volume mari | TD-07 întâi |
| TD-15 | Teme vizuale neformalizate (dark ops vs light client vs olive register) | P3 | 2 | 3 | „AI slop" perception; efort dublu la fiecare ecran | tokens layer în design system |
| TD-16 | test_credentials/PRD drift (proces, nu cod) | P3 | 2 | 1 | teste pe credențiale greșite | disciplină la finish (regulă existentă) |

**Politica de rambursare a datoriei:** fiecare versiune (V2.0, V2.5...) rezervă **20% din capacitate** pentru TD-uri, în ordinea Prio → Impact/Cost. TD-urile P0 blochează lansarea versiunii în care sunt scadente (TD-01/02/03 = scadente în V2.0).

---

# 8. FILOSOFIA „AI WORKSPACE PER ROL" (extensia cerută — nucleul viziunii UX)

**Principiu:** *Niciun rol nu mai primește „un dashboard". Fiecare rol primește un spațiu de lucru asistat, care propune acțiuni, nu afișează informații.*

Anatomia standard a unui AI Workspace (identică pentru toate rolurile — un singur pattern de construit):
```
┌────────────────────────────────────────────────────────┐
│ 1. FOCUS: „Ce contează ACUM" (max 3 iteme, cu 1-tap    │
│    accept/amână/deleagă) — alimentat de semnale        │
│ 2. FEED: momente & recomandări cu context și preț/     │
│    impact estimat (nu carduri statice)                 │
│ 3. PULSE: 3-5 indicatori personali cu trend + prag     │
│ 4. LEDGER: „ce a făcut asistentul pentru tine" —       │
│    transparența autonomiei (încredere prin vizibilitate)│
└────────────────────────────────────────────────────────┘
```

| Rol | Workspace | Întrebarea la care răspunde | Surse de semnale (există deja) | Exemple de acțiuni propuse |
|---|---|---|---|---|
| Client | **Home Assistant** | „Ce facem azi cu casa ta?" | health, twin, sezon, istoric cereri, observatory | „Programează revizia centralei (~250 RON, 3 specialiști liberi joi)" |
| Specialist | **Business Assistant** | „Cum câștigi mai mult luna asta?" | matching, reputație, observatory benchmark, calendar | „Acceptă lucrarea X (potrivire 92%); ridică tariful la mp cu 8% — ești sub media expert Cluj" |
| Operator | **Operations Assistant** | „Care e ruta și ce lipsește dosarelor?" | cozi verificare, twin QA, incident/NC | „3 vizite azi în sectorul 3; dosarul Y n-are poze fațadă" |
| Admin | **Executive Control Tower** | „Ce decizii cer om azi?" | orchestrator escalations, KYC review, dispute triate, gate/hidden-potential | „Aprobă KYC (AI: recomandat) · Mediază disputa Z (AI propune 70/30)" |
| Business | **CEO Dashboard** | „Unde crește și unde curge?" | escrow, abonamente, campanii, observatory, reconciler | „Cluj +34% cereri electric; deschide recrutare — link generat" |
| Infrastructure | **DevOps Control Center** | „E sănătos sistemul fără să mă uit?" | smoke, healthcheck, retry queue, autonomy score, QA | „Retry queue: 3 failed — cauza: DNS Resend (acțiune externă)" |

**Reguli de implementare a filosofiei (pentru toate fazele viitoare):**
1. **Un singur motor de recomandări** (`recommendation service`) cu adaptoare per rol — nu 6 implementări.
2. Fiecare recomandare are schema fixă: `{situație, propunere, impact_estimat, acțiune_1tap, sursa_semnalului}` și lasă urmă în ledger când e acceptată.
3. **AI-ul execută prin aceleași API-uri ca omul** (fără căi privilegiate) — auditabilitate totală.
4. Escaladarea e inversă: workspace-ul rezolvă → propune → doar apoi întreabă. (Aceeași filosofie ca orchestratorul, adusă la nivel de utilizator.)
5. Ordinea construcției urmează Dependency Map: Control Tower (semnale există azi) → Business Assistant (matching+observatory există) → Home Assistant (necesită health activ în masă) → restul.

---

# 9. ORDINEA DE EXECUȚIE CONFIRMATĂ

```
Phase 0  ✅ ACEST DOCUMENT (Blueprint)
Phase 1  Stabilizare tehnică            → plătește TD-01/03/05/07/08 (V2.0)
Phase 2  Admin Command Center           → Control Tower v1 (V2.0)
Phase 3  Specialist Cockpit             → Business Assistant v1 (V2.0)
Phase 4  Client Copilot                 → Home Assistant v1 (V2.5)
Phase 5  Marketplace Intelligence       → Observatory public + SEO (V2.5→V3.0)
Phase 6  Autonomy Engine 2.0            → Pattern Hunter & co (V3.0)
```

**Definiția de „gata" pentru Phase 0:** acest document este aprobat de owner și devine referință obligatorie: orice cerere viitoare de feature primește răspunsul „în ce strat, ce clasă de modul, ce versiune și ce dependențe are conform Blueprint-ului?"

---

# 10. PRODUCT CONSTITUTION — reguli care NU pot fi încălcate

> Ratificată de owner. Orice PR/feature care încalcă un articol se respinge indiferent de urgență.

**Art. 1** — Nu se dezvoltă funcționalități izolate. Fiecare feature consumă și produce date în ecosistem (Principiul 2).
**Art. 2** — Nu se dublează logica existentă. Nu se creează al doilea mod de a face același lucru. (Cauza directă a TD-02/TD-10 — nu se repetă.)
**Art. 3** — LEGACY nu primește funcționalități noi. Cine cere feature pe legacy finanțează migrarea.
**Art. 4** — AI execută doar prin API-urile oficiale, cu aceleași permisiuni ca un utilizator uman, și lasă urmă în ledger. Fără căi privilegiate.
**Art. 5** — Toate modulele și componentele se construiesc reutilizabil (un pattern, adaptoare per rol/context — vezi motorul unic de recomandări §8).
**Art. 6** — Orice feature nou îmbogățește ecosistemul de date (Principiul 5). Feature care doar consumă = taxă; se respinge sau se re-proiectează.
**Art. 7** — Mobile-first este obligatoriu pentru orice ecran de Client și Specialist.
**Art. 8** — Performanța și experiența utilizatorului au aceeași prioritate ca funcționalitatea. Un feature lent sau confuz nu e „gata".
**Art. 9** — Efectele cross-modul circulă prin semnale (Orchestrator), nu prin apeluri directe.
**Art. 10** — Orice feature intră cu clasificare completă (clasă/versiune/dependențe/impact/KPI — Principiul 6) și cu data-testid pe elementele interactive.
**Art. 11** — Deciziile automate cu impact legal/financiar asupra persoanelor rămân în mod „recomandare" până la aviz juridic explicit (precedent: KYC).
**Art. 12** — Blueprint-ul are întâietate: conflictul între o cerere de feature și Blueprint se rezolvă întâi la nivel de Blueprint (amendament), apoi în cod.

---

# 11. LIVING PRODUCT — Blueprint-ul ca organism viu

1. **Sincronizare obligatorie:** Blueprint-ul se actualizează la fiecare versiune majoră (V2.0, V2.5, V3.0…) — secțiunile §5 (roadmap), §6 (ownership), §7 (TD register) primesc revizie de versiune.
2. **Ritual de intrare a modulelor noi:** înainte de implementare, orice modul nou primește o fișă de integrare (clasă, strat, dependențe contra §4, efect de rețea contra §3, KPI) — anexată la PRD și reflectată în Blueprint.
3. **Ritual de ieșire:** modulele EXPERIMENTAL sunt evaluate la fiecare 2 cicluri: promovare (cu clasă nouă) sau eliminare. Modulele LEGACY au dată-țintă de retragere.
4. **Audit de sincronizare:** la fiecare versiune majoră se rulează un mini-audit (stil PLATFORM_AUDIT) care confirmă că aplicația și Blueprint-ul nu au divergat; divergențele devin TD-uri.
5. **Proprietate:** owner-ul produsului ratifică amendamentele; agentul de dezvoltare propune, nu decide unilateral asupra Constituției.

---

# 12. PROPERTY KNOWLEDGE GRAPH — avantajul competitiv pe termen lung

**Concept (ratificat de owner):** toate entitățile platformei nu sunt tabele izolate, ci **noduri într-un graf de cunoștințe al proprietății**:

```
   PROPRIETATE ──are──► CAMERE ──conțin──► INSTALAȚII/ECHIPAMENTE
        │                                       │
     deținută de                        întreținute prin
        ▼                                       ▼
     CLIENT ──deschide──► CERERI ──devin──► INTERVENȚII/PROIECTE
                              │                 │
                        executate de      folosesc
                              ▼                 ▼
                        SPECIALIȘTI       MATERIALE ──au──► COSTURI
                              │                                │
                        evaluați prin                   agregate în
                              ▼                                ▼
                          REVIEWS          AUDITURI      PRICE OBSERVATORY
                              │                │               │
                              └────► RECOMANDĂRI AI ◄──────────┘
                                          │
                                   DOCUMENTE · TRANZACȚII · GARANȚII
```

**Ce deblochează graful (imposibil cu colecții disparate):**
- *Explicabilitate:* „Recomand revizia centralei pentru că are 7 ani, ultima intervenție a fost în 2024, iar 3 case similare din zona ta au avut defecțiuni iarna asta."
- *Predicție:* durata de viață rămasă a echipamentelor din case comparabile → mentenanță predictivă.
- *Automatizare complexă:* orchestratorul poate raționa pe lanțuri de noduri (instalație → garanție expiră → specialistul care a montat-o → ofertă de revizie pre-aprobată).
- *Valoare de exit:* graful complet al ciclului de viață a mii de proprietăți este activul care nu poate fi replicat.

**Strategie de implementare (pragmatică, fără big-bang):**
- **Etapa KG-0 (V2.0):** *graful logic peste Mongo* — nu se schimbă baza de date. Se formalizează un registru de relații (`entity_links`: {from_type, from_id, rel, to_type, to_id}) + convenția ca orice feature nou să scrie legăturile pe care le creează (Art. 6 devine măsurabil).
- **Etapa KG-1 (V2.5):** serviciul de interogare a grafului (walk pe relații) alimentează motorul unic de recomandări (§8) — primele recomandări explicabile.
- **Etapa KG-2 (V3.0):** evaluare pragmatică a unui strat de graf dedicat (doar dacă volumele o cer); embeddings pe noduri pentru similaritate (case comparabile, specialiști similari).
- **Regulă imediată (de azi):** orice colecție/feature nou definește explicit ce noduri și ce relații adaugă în graf — parte din fișa de integrare (§11.2).

---

## STATUS RATIFICARE
- **Blueprint v1.1 — VALIDAT de owner (Iulie 2026)** cu amendamentele: Principii Fundamentale (§1.5), Product Constitution (§10), Living Product (§11), Property Knowledge Graph (§12).
- **Phase 1 — APROBATĂ**, cu condiția: fiecare modificare tehnică se verifică și prin prisma Blueprint-ului (fără optimizări locale care creează datorie arhitecturală).
