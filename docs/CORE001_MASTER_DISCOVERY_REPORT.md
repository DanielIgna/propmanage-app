# MASTER DISCOVERY REPORT — CORE-001

*Generat: 2026-07-28T20:45:33.581375+00:00 · Live Product Map · AI Brain Product Intelligence Engine*

## 1. Rezumat executiv
- **19 module de produs** cartografiate canonic · completitudine medie **90%**.
- **6 fișiere frontend neconectate** (neimportate din App.js) · **4 zone de duplicare** identificate.
- Frontend: 323/372 fișiere accesibile din rădăcina aplicației.
- Regula 60%: dacă o implementare există în proporție de peste 60%, se REUTILIZEAZĂ și se EXTINDE — nu se rescrie.
- Ordinea aprobată post-CORE-001: PB-001 · PropBenefits Engine Foundation → FP-001 · FairPrice Engine → HH-Next · House Health Subscriptions.

## 2. Product Completeness × Business Value (per modul)

| Modul | Status | Completeness | Business Value | Priority Index |
|---|---|---|---|---|
| PropBenefits Engine | Planificat | 0% | 82 | 82 |
| FairPrice Engine | Candidat reutilizare | 17% | 64 | 53 |
| Buildings & Community | Activ | 80% | 74 | 15 |
| Calendar Mentenanță | Activ | 85% | 68 | 10 |
| Marketplace Core (Cereri & Oferte) | Activ | 90% | 76 | 8 |
| Tokens & Wallet | Candidat reutilizare | 89% | 58 | 6 |
| Subscriptions & Billing | Activ | 93% | 74 | 5 |
| Document Vault (Cartea Casei) | Activ | 93% | 50 | 4 |
| Digital Twin | Duplicat | 95% | 57 | 3 |
| House Health | Activ | 96% | 70 | 3 |
| Referral Engine | Activ | 95% | 65 | 3 |
| City Partners | Experimental | 94% | 47 | 3 |
| AI Brain | Activ | 100% | 36 | 0 |
| Guardian Kernel | Activ | 100% | 27 | 0 |
| Marketplace Public & Trust | Activ | 100% | 62 | 0 |
| Loyalty & Experience Tiers | Activ | 100% | 56 | 0 |
| Property Passport | Activ | 100% | 48 | 0 |
| Trusted Specialists & Rebooking | Activ | 100% | 66 | 0 |
| Orchestrator & Playbooks | Activ | 100% | 40 | 0 |

*Priority Index = Business Value × (100 − Completeness) / 100 — unde merită investit timpul de dezvoltare.*

## 3. Detaliu module (dovezi)

### PropBenefits Engine — 0% · BVS 82
PB-001 — motorul comercial de beneficii. NU există cod. Se construiește prin EXTENSIE (regula 60%): referral + tiers + wallet + campanii + billing.
- Backend: 0/1 fișiere · 0 endpoint-uri
- Frontend: 0/1 fișiere · 0 montate
- Date: 0/1 colecții cu date · goale: prop_benefits_ledger
  - ❌ Catalog beneficii
  - ❌ Ledger puncte/beneficii
  - ❌ UI beneficii montat
- **Candidat reutilizare (regula 60%)**: trust_growth.py · Referral Engine (~80% reutilizabil) · experience_tiers.py + tier_milestones.py · niveluri (~70%) · wallet.py + transactions · ledger de bază (~60%) · community_buildings.py · campanii de grup (~65%) · house_health_billing.py + payments.py · billing (~70%) · orchestrator playbooks + notificări (~90%)

### FairPrice Engine — 17% · BVS 64
NU există motor dedicat. Piese răspândite: fairness ranking (marketplace_offers), praguri HH, prețuri publice CMS. FP-001 le va consolida prin EXTENSIE.
- Backend: 0/1 fișiere · 0 endpoint-uri
- Date: 0/1 colecții cu date · goale: price_benchmarks
  - ✅ Fairness în ranking oferte (există — reutilizabil)
  - ✅ Praguri de preț House Health (există — reutilizabil)
  - ✅ Pagini publice de prețuri (există — reutilizabil)
  - ❌ Estimare preț per categorie de lucrare
  - ❌ Benchmark prețuri de piață
- **Candidat reutilizare (regula 60%)**: marketplace_offers.py · _fairness_boost + ranking policy · house_health_plans.py · praguri configurabile · PreturiPage/PreturiIndex · prezentare publică prețuri · requests.budget + offers.price · date istorice reale de preț

### Buildings & Community — 80% · BVS 74
Blocuri, campanii comune de mentenanță, workspace administrator, Building Health Score — pilotul celor 13 apartamente.
- Backend: 2/2 fișiere · 15 endpoint-uri
- Frontend: 3/3 fișiere · 3 montate
- Date: 0/2 colecții cu date · goale: buildings, community_campaigns
  - ✅ Building Health Score 5 componente
  - ✅ Campanii + auto-detecție nightly
  - ✅ Anunțuri + invitații bloc
  - ❌ Import Excel/CSV apartamente

### Calendar Mentenanță — 85% · BVS 68
Revizii recurente cu template-uri RO, remindere zilnice, cereri directe la specialistul de încredere (0 lei lead).
- Backend: 1/1 fișiere · 6 endpoint-uri
- Frontend: 1/1 fișiere · 1 montate
- Date: 0/1 colecții cu date · goale: maintenance_tasks
  - ✅ 8 template-uri revizii RO
  - ✅ Reminder tick zilnic
  - ✅ Cerere directă 0 lei din task

### Marketplace Core (Cereri & Oferte) — 90% · BVS 76
Fluxul central de venit: cereri client → oferte specialiști → acceptare → lucrare → recenzie.
- Backend: 3/3 fișiere · 17 endpoint-uri
- Frontend: 2/2 fișiere · 2 montate
- Date: 2/2 colecții cu date
  - ✅ Hybrid ranking + fairness rotation
  - ✅ Lead fee 45 RON + waive la rebooking
  - ✅ Cereri directe (direct_specialist_id)
  - ✅ Recenzii cu rebook/recommend

### Tokens & Wallet — 89% · BVS 58
Wallet simplu (wallet_balance pe users + transactions). Fără ledger dedicat, fără tokens de beneficii — fundația PB-001.
- Backend: 2/2 fișiere · 7 endpoint-uri
- Date: 2/2 colecții cu date
  - ✅ Top-up + istoric tranzacții
  - ✅ Plăți Stripe
  - ❌ Ledger unificat de beneficii/puncte
- **Candidat reutilizare (regula 60%)**: wallet.py · balance + tranzacții · payments.py · integrare Stripe funcțională · transactions collection · istoric existent

### Subscriptions & Billing — 93% · BVS 74
Stripe (test mode — claim LIVE pending), tranzacții, manual payments ledger, Money-Flow Guard.
- Backend: 3/3 fișiere · 6 endpoint-uri
- Frontend: 1/1 fișiere · 1 montate
- Date: 1/1 colecții cu date
  - ✅ Stripe checkout integrat
  - ✅ Money-Flow Guard (detecție LIVE/TEST)
  - ❌ e-Factura RO

### Document Vault (Cartea Casei) — 93% · BVS 50
Documente per proprietate pe object storage, completeness score 0-100 din 14 semnale, istoric imutabil.
- Backend: 2/2 fișiere · 8 endpoint-uri
- Frontend: 1/1 fișiere · 1 montate
- Date: 1/1 colecții cu date
  - ✅ Upload multipart + metadate D015
  - ✅ Completeness Score proprietate
  - ❌ Istoric imutabil + versiuni

### Digital Twin — 95% · BVS 57
Gemenii digitali ai proprietăților. ATENȚIE: 4 sisteme paralele (properties.dna, twins, digital_twin_projects, hh_*) — necesită unificare (G2).
- Backend: 4/4 fișiere · 60 endpoint-uri
- Frontend: 3/3 fișiere · 3 montate
- Date: 3/3 colecții cu date
  - ✅ Property DNA (SSOT declarat)
  - ✅ Twin viewer 3D
  - ❌ Colecție twin UNICĂ (unificare G2)
  - ✅ Timeline proprietate

### House Health — 96% · BVS 70
Abonamente premium de sănătate a casei: scoruri, evaluări specialiști, planuri, billing.
- Backend: 4/4 fișiere · 32 endpoint-uri
- Frontend: 3/3 fișiere · 3 montate
- Date: 4/4 colecții cu date
  - ✅ Scoring config + praguri
  - ✅ Billing Stripe conectat
  - ✅ Abonamente active (date reale)
  - ❌ Gating pe twin-ul validat (nu DT Pro)
  - ✅ UI billing conectat la abonare

### Referral Engine — 95% · BVS 65
Invitații cu recomandare pe roluri (client/specialist), claim idempotent, link-uri virale WhatsApp.
- Backend: 1/1 fișiere · 6 endpoint-uri
- Frontend: 1/1 fișiere · 1 montate
- Date: 2/2 colecții cu date
  - ✅ Invitații pe roluri + email
  - ✅ Claim idempotent cu recomandare
  - ✅ ReferralHub dual-variant montat
  - ❌ Recompensă materială la referral (bonus/token)
- **Candidat reutilizare (regula 60%)**: trust_growth.py · fluxul complet invite→claim→notify · ReferralHub.jsx · UI client+specialist

### City Partners — 94% · BVS 47
Program de parteneriat strategic pe orașe (V1 non-exclusiv): parteneri, lead-uri, onboarding 7 pași.
- Backend: 1/1 fișiere · 16 endpoint-uri
- Frontend: 2/2 fișiere · 2 montate
- Date: 2/2 colecții cu date
  - ✅ CRUD parteneri + onboarding
  - ✅ Self-service partener (role)
  - ❌ Comisioane marketplace (V2)
  - ✅ Parteneri activi (date reale)

### AI Brain — 100% · BVS 36
Ecosistemul de inteligență al platformei: Discovery, Context, Explainability, Mentor, Knowledge Graph, Process, Decision, Adaptive, Collaborative, Certification.
- Backend: 9/9 fișiere · 53 endpoint-uri
- Frontend: 7/7 fișiere · 7 montate
- Date: 5/5 colecții cu date
  - ✅ Discovery Engine automat
  - ✅ Knowledge Graph construit
  - ✅ Certificare v1.0.0
  - ✅ Mentor + Explainability

### Guardian Kernel — 100% · BVS 27
Gardienii autonomi de arhitectură și produs — protejează logica de cod și arhitectura canonică.
- Backend: 3/3 fișiere · 0 endpoint-uri
- Date: 2/2 colecții cu date
  - ✅ Scor arhitectură calculat
  - ✅ Scor produs calculat

### Marketplace Public & Trust — 100% · BVS 62
Vitrina publică de specialiști cu Trust Layer (rebook %, recomandări, badges).
- Backend: 3/3 fișiere · 9 endpoint-uri
- Frontend: 2/2 fișiere · 2 montate
- Date: 1/1 colecții cu date
  - ✅ Trust rollup pe carduri
  - ✅ Early-access empty state
  - ✅ Filtru defensiv REJECTED/SUSPENDED

### Loyalty & Experience Tiers — 100% · BVS 56
Progressive disclosure + progresie 7 niveluri specialiști + recompense de loialitate (rebooking 0 RON). Gamification (QuestPanel/TierCelebration) parțial demontată.
- Backend: 4/4 fișiere · 32 endpoint-uri
- Frontend: 4/4 fișiere · 4 montate
- Date: 2/2 colecții cu date
  - ✅ Tiers automate cu criterii
  - ✅ Progresie 7 niveluri data-driven
  - ✅ Recompensă loialitate: rebooking gratuit
  - ✅ Vouchere / quests montate în UI
- **Candidat reutilizare (regula 60%)**: experience_tiers.py · motor tiers configurabil · tier_milestones.py · praguri + celebrări · lib/QuestPanel + TierCelebrationBanner · UI gamification existent

### Property Passport — 100% · BVS 48
Pașaport public per proprietate cu QR, trust score verificabil, analytics GDPR-safe, buclă virală.
- Backend: 2/2 fișiere · 10 endpoint-uri
- Frontend: 2/2 fișiere · 2 montate
- Date: 1/1 colecții cu date
  - ✅ QR + OG social previews
  - ✅ Analytics + conversii first-touch
  - ✅ Privacy toggles server-side

### Trusted Specialists & Rebooking — 100% · BVS 66
Specialiștii de încredere ai clientului + rebooking 1-click cu lead fee 0 — venit din repetare.
- Backend: 1/1 fișiere · 2 endpoint-uri
- Frontend: 2/2 fișiere · 2 montate
- Date: 1/1 colecții cu date
  - ✅ Agregare lucrări + rebook rollup
  - ✅ Rebook direct cu fee 0
  - ✅ Post-Job Growth Loop montat

### Orchestrator & Playbooks — 100% · BVS 40
Event-driven orchestrator cu 14 playbooks, ledger, semnale de lansare, minutes_saved.
- Backend: 3/3 fișiere · 11 endpoint-uri
- Date: 1/1 colecții cu date
  - ✅ Ledger cu playbooks
  - ✅ Semnale de lansare (resident/campaign/payment)

## 4. Duplicate identificate

### 4 sisteme Digital Twin paralele
- Elemente: properties.dna (property_dna.py) · twins (twin.py, operator) · digital_twin_projects (digital_twin.py, Pro) · hh_* (house_health.py)
- Impact: House Health cere proiect DT Pro în loc de twin-ul validat; date fragmentate; scoruri concurente.
- Recomandare: Unificare pe digital_twin_projects (gap G2) — migrarea colecției twins + gating HH pe twin-ul real.

### 4 componente viewer twin în frontend
- Elemente: DigitalTwinViewer.jsx · ClientTwinViewer.jsx · OperatorTwin.jsx · OperatorDigitalTwin.jsx
- Impact: Logică de randare duplicată, bug-uri fixate în 4 locuri.
- Recomandare: Un viewer canonic cu prop-uri de rol; celelalte devin wrappere subțiri sau se elimină.

### 2 sisteme de recenzii (v1 + v2)
- Elemente: requests.py · ReviewIn (v1) · reviews_v2.py (multi-dimensional)
- Impact: Câmpurile would_hire_again/would_recommend întreținute în paralel.
- Recomandare: Unificare pe reviews_v2 cu adapter pentru v1; NU se rescrie — se extinde v2 (regula 60%).

### Dashboard-uri legacy vs V2
- Elemente: pages/Dashboards.jsx (legacy) · pages/clientv2/ClientDashboardV2.jsx · pages/SpecialistDashboard.jsx
- Impact: Cod mort/parțial mort în bundle; confuzie la modificări.
- Recomandare: Audit rutele care mai folosesc Dashboards.jsx → retragere controlată.

## 5. Fișiere frontend neconectate (6)
- `hooks/use-toast.js`
- `lib/TierToolsPanel.jsx`
- `lib/api.js`
- `lib/apiBase.js`
- `lib/featureMatrix.js`
- `lib/utils.js`

## 6. Roadmap de Consolidare (impact × risc)

| # | Acțiune | Impact | Risc | Efort | De ce |
|---|---|---|---|---|---|
| 1 | Ledger unificat Tokens/Wallet pentru PB-001 | 5/5 | 2/5 | M | PropBenefits are nevoie de un ledger canonic de puncte/beneficii. Există wallet_balance + transactions + payment_transactions — se EXTIND într-un serviciu unic. |
| 2 | Unificare Digital Twin (G2): twins → digital_twin_projects | 5/5 | 4/5 | L | 4 sisteme paralele fragmentează datele; House Health e blocat pe DT Pro în loc de twin-ul validat. |
| 3 | Consolidare piese pricing → FairPrice Engine (FP-001) | 4/5 | 2/5 | M | Fairness ranking, praguri HH și prețuri publice există separat — FP-001 le unifică prin extensie, cu date istorice din requests/offers. |
| 4 | Split bundle admin (main.js ~2.3MB) | 3/5 | 2/5 | M | Paginile admin încarcă bundle-ul principal; code splitting suplimentar reduce TTI pentru clienți reali. |
| 5 | Unificare recenzii v1/v2 | 3/5 | 3/5 | M | Două scheme de recenzii întreținute în paralel; datele Rebook Score trebuie să curgă dintr-o singură sursă. |
| 6 | Consolidare viewere twin (4 → 1 canonic) | 3/5 | 3/5 | M | Logică de randare duplicată în 4 componente. |
| 7 | Decizie gamification: QuestPanel + TierCelebration | 2/5 | 1/5 | S | Componente funcționale demontate parțial din V2 — se decid: remontare în PB-001 (recomandat) sau eliminare. |
| 8 | Curățenie 6 fișiere frontend neconectate | 2/5 | 1/5 | S | Fișiere neimportate din App.js — cod mort sau componente demontate (listă în tab-ul Neconectate). |
| 9 | Retragere Dashboards.jsx legacy | 2/5 | 3/5 | S | Cod potențial mort după migrarea la V2. |

## 7. Pregătire PB-001 — PropBenefits Engine
PB-001 se construiește prin **EXTENSIE**, nu de la zero. Active reutilizabile:
- trust_growth.py · Referral Engine (~80% reutilizabil)
- experience_tiers.py + tier_milestones.py · niveluri (~70%)
- wallet.py + transactions · ledger de bază (~60%)
- community_buildings.py · campanii de grup (~65%)
- house_health_billing.py + payments.py · billing (~70%)
- orchestrator playbooks + notificări (~90%)

*Raport generat automat de AI Brain · Product Intelligence Engine (CORE-001). Live Product Map se recalculează la fiecare accesare; snapshot-urile păstrează istoricul.*