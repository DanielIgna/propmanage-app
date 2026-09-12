# MASTER ROADMAP & FINANCIAL PLAN 2026 — PropManage
**Răspuns la Board Directives 027 + 029 · Rol: CPO + CTO + CFO + PMO · Iun 2026**
Fundamentat pe date REALE din platformă: 30 module pe board (6 done, 15 in progress, 9 planned),
Autonomy 86.8 (axa umană 32.5 — bottleneck), Business Health 51.8, 1.214 useri (majoritatea demo),
130 proprietăți, 199 cereri (29 confirmate), 76 plăți, 2 abonamente, 94 oportunități active /
1 acceptată, 9 outcome-uri AI (gate GI-4c = 30).

---

## STEP 1 — MASTER INVENTORY

### ✅ COMPLETED (funcțional, testat)
Auth multi-rol + JWT + Google · Properties + Digital Twin 3D viewer · Marketplace (cereri,
oferte, matching, escrow, dispute, recenzii) · House Health (scoring, evaluări, planuri,
Stripe checkout) · GDPR/Trust/Legal (7 contracte) · Admin ecosystem (50+ pagini) ·
Design System + Design Intelligence · Command Center v1 · Business Health · Marketplace Intel
+ Radar · Financial Cockpit · Notification Center · Automation Center v1 (3 reguli + scheduler) ·
CEO Dashboard v1 · User Timeline · AI Search · Audit Sentinel · Demo/Admin Accounts Manager ·
IT Hub + Copilot · City/Marketplace/Strategic Partners · AI Marketing Department (BI, campanii
AI+imagini, Performance Loop) · Unified Leads + Franchise funnel · Specialist Follow-up ·
GI-1 Growth Intelligence · GI-2 Lead Intelligence · GI-3 Marketing Intelligence+ ·
GI-4a Learning Engine (Outcome Tracker + Ledger v2) · Property DNA v1 + Value Loop + PVI ·
Revenue Hunter · **GI-5P Sprint 1** (Maturity L0-L5, Asset Registry, Predictive actuarial) ·
Resend Self-Diagnostics · Autonomy Engine v1 (6 axe + HDI).

### 🔄 IN PROGRESS
GI-5P Sprint 2 (spec aprobat, așteaptă start) · module board 55-95% (ai_command_center 95,
business_health 90, marketplace_intel 90, notification 90, financial_cockpit 85, ceo 85,
automation 75, autonomy_levels 65, ai_insights 60, city_analytics 55, cao_p1 55, specialist_score 40).

### 🚫 BLOCKED
Resend DNS (acțiune user la Rackhost — checklist livrat) · GI-4c Calibrare (gate: ≥30 outcome-uri
reale; sunt 9) · Stripe LIVE key (user: claim account pentru producție).

### 📋 PLANNED (directive aprobate)
Integration Control Center (017/opțiunea B) · GI-4b AI Memory · GI-5 Constituția executabilă ·
Command Center 2.0 (020) · Mission Mode (021) · Adaptive Autonomy (022) · Autonomy Evolution +
Executive Advisor (024/025) · BIOS (019) · Business Digital Twin (026) · GI-5D Interior (după GI-5P).

### 🔮 FUTURE VISION
GI-6 Autonomous Business OS · GI-7 Cross-Domain · Energy/Insurance/Financial/Sustainability
Intelligence · IoT senzori · multi-tenant/franciză white-label · ML actuarial.

---

## STEP 2+3 — PHASE BREAKDOWN & WBS (credite: min/realistic/max)

### FAZA A — COMMERCIAL FOUNDATION 🔴 CRITICĂ · 33/49/68 credite · ~1,5-2 luni
Obiectiv: platforma VINDE. Valoare comercială directă. Risc tehnic mic (extensii).
| ID | Epic | Credite (m/r/M) | Depinde de | Paralel? |
|----|------|-----------------|------------|----------|
| A1 | GI-5P Sprint 2: DNA v2 provenance + Health Decay + Risk Engine | 12/16/22 | GI-5P S1 ✅ | cu A2,A3 |
| A2 | Resend DNS verify + config prod + docs | 1/2/4 | USER (Rackhost) | da |
| A3 | Integration Control Center (health, diagnostics, test, incident history) | 8/12/16 | resend_diag ✅ | cu A1 |
| A4 | GI-4b AI Memory (lecții → Command Center + Playbooks) | 6/9/12 | GI-4a ✅ | cu A5 |
| A5 | Commercial hardening: pagină prețuri publică, checkout polish, Stripe LIVE, e-mail tranzacțional live | 6/10/14 | A2 + Stripe key | da |

### FAZA B — OPERATIONAL BRAIN 🟠 (autonomia percepută crește masiv) · 54/76/106 · ~3 luni
| ID | Epic | Credite | Depinde de | Paralel? |
|----|------|---------|------------|----------|
| B1 | Command Center 2.0 (Directive 020: 14 secțiuni, orchestrare, reuse ~60% module existente) | 22/30/42 | A3, A4 | cu B3 parțial |
| B2 | Mission Mode (021: mission engine, workflow, history, evolution, evening review) | 18/26/36 | B1 | nu (după B1) |
| B3 | Adaptive Autonomy (022: 4 moduri, Safe/Medium/Critical, Executive Memory) | 14/20/28 | Automation Center ✅ | cu B1 |

### FAZA C — EXECUTIVE ADVISOR & BIOS 🟡 · 52/74/104 · ~3 luni
| ID | Epic | Credite | Depinde de | Paralel? |
|----|------|---------|------------|----------|
| C1 | Autonomy Evolution (024: timeline permanent, event log, explain scores, deploy impact, revenue mode) | 14/20/28 | B3 | cu C2 |
| C2 | Executive Advisor (025: Explain Like I'm CEO, Forecast, Scenario Planner, Daily Brief) | 14/20/28 | C1 parțial | cu C1 |
| C3 | BIOS (019: unified timeline all-time, deployment markers, KPI graph relationships, module explainer, AI Investigator 2.0, A/B assistant) | 24/34/48 | B1 | cu C1/C2 parțial |

### FAZA D — BUSINESS DIGITAL TWIN & GI-5D 🟢 strategic · 58/84/118 · ~3-4 luni
| ID | Epic | Credite | Depinde de | Paralel? |
|----|------|---------|------------|----------|
| D1 | Business Digital Twin (026: business graph pe Event Bus + KG existente, time machine, cause-effect, health map, simulation) | 28/40/56 | C3 | cu D2 |
| D2 | GI-5D Interior Intelligence (arhitectură + MVP: Readiness Score, Style DNA, Budget Simulator, shopping lists) | 20/30/42 | GI-5P complet (A1) | cu D1 |
| D3 | GI-5 Constituție executabilă + GI-4c Calibrare | 10/14/20 | ≥30 outcome-uri REALE | da |

---

## STEP 4 — DEPENDENCY GRAPH & CRITICAL PATH
```
USER: Rackhost DNS ──► A2 Resend ──► A5 Commercial ──► 🚀 LANSARE COMERCIALĂ
USER: Stripe LIVE key ──────────────► A5
GI-5P S1 ✅ ──► A1 (S2) ──────────────► D2 GI-5D
resend_diag ✅ ──► A3 Control Center ──► B1 Command Center 2.0 ──► B2 Mission Mode
GI-4a ✅ ──► A4 AI Memory ──► B1
Automation ✅ ──► B3 Adaptive Autonomy ──► C1 ──► C2
B1 ──► C3 BIOS ──► D1 Business Digital Twin
DATE REALE (≥30 outcomes, ~2-3 luni post-lansare) ──► D3 Calibrare ──► autonomie >90% REALĂ
```
**CRITICAL PATH (venit)**: DNS + Stripe LIVE → A5 → Lansare. **~2-4 săptămâni.**
**CRITICAL PATH (autonomie >90%)**: A3→B1→B2→B3→C1/C2 + volum de date reale. **~8-10 luni.**

## STEP 5 — PARALLEL EXECUTION
Fluxuri paralele sigure: A1 ∥ A2 ∥ A3 (module diferite) · A4 ∥ A5 · B1 ∥ B3 · C1 ∥ C2 ∥ C3(parțial)
· D1 ∥ D2. **Timp economisit prin paralelizare: ~30-35%** (12 luni → ~8-9 luni de calendar
pentru A–C dacă sprinturile rulează consecutiv dens).

---

## STEP 6 — BUDGET (credite Emergent)
| Scenariu | A | B | C | D | TOTAL |
|----------|---|---|---|---|-------|
| Minim | 33 | 54 | 52 | 58 | **197** |
| **Realist** | 49 | 76 | 74 | 84 | **283** |
| Maxim | 68 | 106 | 104 | 118 | **396** |

- **Țintă „autonomie >90%, doar aprobări" (A+B+C1+C2)**: 119/165/230 → **recomandat ~190 credite** (realist + 15%)
- **Viziune completă 12 luni (A–D)**: realist 283 → **+15% buffer = 325 · +25% = 354**
- **Emergency buffer** (incidente, regresii majore, schimbări de scope Board): +30
- **RECOMANDARE CFO: rezervă ~350 credite pe 12 luni, achiziționate în tranșe trimestriale**
  (nu totul odată — Directiva 016: measure outcomes, adjust based on evidence).

## STEP 7 — MONTHLY CASH FLOW (scenariu realist, cumulativ)
| Luna | Credite | Module | Livrabile | Cumulativ |
|------|---------|--------|-----------|-----------|
| 1 | 18 | A1+A2 | GI-5P MVP complet, email live | 18 |
| 2 | 22 | A3+A4 | Control Center integrări, AI Memory | 40 |
| 3 | 10 | A5 | 🚀 **LANSARE COMERCIALĂ (MCP)** | 50 |
| 4 | 15 | B1½ | Command Center 2.0 (secț. 1-7) | 65 |
| 5 | 15 | B1½ | Command Center complet | 80 |
| 6 | 26 | B2 | Mission Mode live | 106 |
| 7 | 20 | B3 | Adaptive Autonomy (Explore/Guide/Assist) | 126 |
| 8 | 20 | C1 | Autonomy Timeline + Event Log + Deploy Impact | 146 |
| 9 | 20 | C2 | Explain CEO + Forecast + Daily Brief → **>90% autonomie operațională** | 166 |
| 10 | 17 | C3½ | BIOS: unified timeline + deployment markers | 183 |
| 11 | 31 | C3½+D3 | BIOS complet + Calibrare GI-4c (are date) | 214 |
| 12 | 40 | D1 | Business Digital Twin v1 | 254 |
| 13+ | ~30 | D2 | GI-5D Interior MVP | ~284 |

## STEP 8 — ROI PER FAZĂ
| Fază | Impact venit | Economii operaționale | Ore umane salvate | ROI / Payback |
|------|--------------|----------------------|-------------------|---------------|
| A | DIRECT: audituri, abonamente, comisioane pornesc | mic | ~5h/săpt | Payback 1-3 luni post-lansare · P0 |
| B | indirect (viteză răspuns → conversie) | MARE: admin de la ~3-4h/zi la <1h/zi | ~15-20h/săpt | 3-6 luni · P0 |
| C | retenție + decizie mai bună | mediu | ~5-8h/săpt | 6-9 luni · P1 |
| D | strategic: expansiune, franciză, GI-5D = linie nouă de venit (design interior) | mediu | — | 9-18 luni · P2 |

## STEP 9 — READINESS LEVEL (Arh/BE/FE/AI/UX/Test/Comercial/Docs/Deploy → medie)
| Modul | Scor | Notă |
|-------|------|------|
| Digital Twin proprietate | **82%** | Comercial gata; delivery semi-manual OK la lansare |
| Audit Tehnic (flux vânzare) | **80%** | Cerere→match→escrow→confirm există; lipsă: pagină ofertă publică |
| House Health + abonamente Stripe | **85%** | Blocat doar de cheia LIVE |
| Marketplace + specialiști | **75%** | Matching + escrow ✅; self-sustaining cere B3 |
| Property Intelligence GI-5P | **70%** | S1 ✅, S2 spec aprobat |
| Learning Engine | **60%** | GI-4a ✅; 4b planned; 4c blocat pe date |
| Lead/Growth/Marketing Intel | **85%** | funcționale |
| Command Center vs Directive 020 | **45%** | v1 există, orchestrarea 020 nu |
| Mission Mode | **0%** | |
| Autonomy Engine vs 024/025 | **55%** | scoruri+HDI ✅; timeline/explain/forecast nu |
| Integration Control Center | **25%** | resend diagnostics ✅ |
| BIOS / Analytics unificat | **40%** | analytics există, unified timeline nu |
| Business Digital Twin | **12%** | Event Bus + entity_links = fundație |

## STEP 10 — RISK MATRIX
| Risc | Prob. | Impact | Mitigare |
|------|-------|--------|----------|
| DATE: calibrare AI pe demo ≠ realitate | mare | mare | lansare devreme + gate GI-4c ≥30 outcome-uri reale |
| COMERCIAL: funnel nedovedit (1/94 oportunități acceptate — demo) | mare | mare | MCP rapid, măsurare GI-4a, Audit First |
| BUGET: cost LLM creștere (Claude per call) | medie | mediu | politica rule-based-first (deja aplicată), cache recos |
| TEHNIC: imagini base64 în Mongo, single instance | mică | mediu | migrare S3 la >100 campanii (deja în backlog) |
| SECURITATE: chei test în prod, master code static | medie | mare | rotire la lansare + env vars producție separate |
| REGRESIE: codebase mare | medie | mediu | testing_agent per sprint (practică curentă), suite pytest 124+ iterații |
| INTEGRARE: Resend/Stripe blocate pe user | certă | mare | checklist livrat; escaladare — fără ele NU există venit |
| AI: halucinație în recomandări | medie | mare | Directiva 015 enforced (provenance, confidence, No Fake Precision) |

## STEP 11 — ROAD TO 1.0
| Milestone | Când | Criteriu |
|-----------|------|----------|
| Alpha | ✅ ACUM | preview complet funcțional |
| Beta / MCP | Luna 1 | Resend live + Stripe LIVE + pagină prețuri |
| 🚀 Commercial Launch | Luna 2-3 | primul client plătitor real |
| RC / Production hardening | Luna 3 | zero incidente 30 zile, backup, monitoring |
| 10 clienți | Luna 4-5 | funnel dovedit |
| AI Operating System | Luna 6-7 | Command Center 2.0 + Mission Mode live |
| 100 clienți / marketplace self-sustaining | Luna 8-10 | tranzacții fără intervenție |
| **Autonomous Platform >90%** | **Luna 9-12** | HDI <10 pe volum real, doar aprobări |
| Business Digital Twin | Luna 12+ | graf viu + simulare |

## STEP 12 — MODULE NOI PROPUSE (care AR TREBUI să existe)
1. **e-Factura RO / facturare automată** 🔴 — obligație LEGALĂ în România pentru facturare;
   fără ea venitul B2B/B2C nu e conform. Impact: deblochează venit real. (~8-12 credite)
2. **Referral & Public Reviews Engine** — social proof pe paginile publice → conversie;
   cel mai ieftin canal de achiziție. (~6-10)
3. **Specialist Onboarding Autopilot** — KYC + verificare semi-automată → marketplace scaling
   fără efort uman (direct pe HDI). (~8-12)
4. **Churn Guard** — detectare abonamente în risc + winback automat → protejează MRR. (~5-8)
5. **SEO Data Content Engine** — rapoarte de piață per oraș generate din marketplace intel →
   trafic organic compus. (~6-10)
6. **Predictive Nudge Channel** — email/SMS pe riscuri EOL; per Directiva 016 se activează DOAR
   după ce recomandarea în-app își dovedește valoarea. (~4-6)

---

## SECȚIUNEA COMERCIALĂ (Directive 029)

### MCP — Minimum Commercial Platform (≠ MVP)
**Necesar înainte de venit recurent** (readiness tehnic actual ~90%):
1. Email tranzacțional live (Resend DNS — USER) 2. Stripe LIVE (USER: claim account)
3. Flux Audit Tehnic vandabil ✅ (există) 4. Abonamente House Health ✅ (există, seedate)
5. Onboarding client + proprietate ✅ 6. GDPR/legal ✅ 7. Suport (AI concierge) ✅
8. Pagină publică prețuri/ofertă audit (A5, ~jumătate din cele 10 credite)
9. **NON-COD: minim 5-10 specialiști reali verificați într-un oraș pilot** — fără ei marketplace-ul nu poate livra.

### Linii de business — readiness
| Linie | Status | Note |
|-------|--------|------|
| Audit Tehnic | ✅ READY | vârful de lance (Audit First 014) |
| Digital Twin | ✅ READY | delivery semi-manual acceptabil la start |
| Abonamente House Health | ✅ READY | doar cheia LIVE lipsește |
| Marketplace/specialiști | 🟡 NEEDS WORK | funcțional cu aprobări manuale (acceptabil la lansare) |
| Mentenanță predictivă | ✅ READY | upsell (GI-5P S1 live) |
| Design Interior | 🔮 AFTER LAUNCH | GI-5D |
| Verified Properties | 🟢 OPTIONAL | MVP există |
| Asociații/Comunități | 🔮 AFTER LAUNCH | |

### Commercial Critical Path (DOAR ce întârzie venitul)
1. Resend DNS (USER, zile) · 2. Stripe LIVE (USER, zile) · 3. Pagină prețuri + polish checkout
(~5-7 credite) · 4. Specialiști reali în orașul pilot (business dev, nu cod).
**TOT restul (Mission Mode, BIOS, Business Twin, chiar GI-5P S2) POATE AȘTEPTA lansarea.**

### Revenue Timeline
| Scenariu | Lansare | Prima factură | Primele abonamente | Primele comisioane | Tranzacții full-auto |
|----------|---------|---------------|--------------------|--------------------|----------------------|
| Optimist | 2 săpt | săpt 3 | luna 1 | luna 1-2 | luna 7-8 |
| **Realist** | **4 săpt** | **luna 2** | **luna 2-3** | **luna 3** | **luna 9-10** |
| Conservator | 8 săpt | luna 3 | luna 4 | luna 5 | luna 12 |

### Revenue Forecast (ipoteze: audit 800 RON, abonament mediu ~145 RON/lună, comision 10% × job mediu 2.500 RON; conversii NEDOVEDITE încă — estimări)
| Clienți | MRR estimat | Venit one-off/lună | Efort uman | Nivel automatizare necesar |
|---------|-------------|--------------------|-----------|----------------------------|
| 10 | ~2.000 RON | ~3-5.000 RON | 2-3h/zi | actual (Faza A) |
| 50 | ~10.000 RON | ~10-15.000 RON | 3-4h/zi | Faza B parțial |
| 100 | ~20-25.000 RON | ~20-30.000 RON | <2h/zi | Faza B completă |
| 500 | ~100-125.000 RON | ~80-120.000 RON | <2h/zi + 1 angajat | Faza C |
| 1000 | ~200-250.000 RON | ~150-250.000 RON | echipă 2-3 | >90% autonomie (C complet) |

### Recomandarea executivă (dacă aș fi CEO)
**DA — lansez în ~4 săptămâni**, într-UN oraș pilot, cu Auditul Tehnic ca produs de intrare
(Audit First) + abonamente House Health ca venit recurent. NU aștept Mission Mode/BIOS/BDT.
- **Credite până la primul venit real: ~12-20** (A2 + A5 + fixuri) — restul e acțiunea ta
  (DNS, Stripe, specialiști pilot).
- **NU are voie să întârzie lansarea**: Resend DNS, Stripe LIVE, pagina de prețuri, 5-10 specialiști reali.
- **Se amână INTENȚIONAT după ce clienții plătesc**: Mission Mode, BIOS, Business Digital Twin,
  GI-5D, calibrarea GI-4c (are nevoie fix de datele clienților reali ca să existe).
- Rațiune: Directiva 016 — arhitectura urmează dovezile; dovezile vin DOAR de la clienți plătitori.

---

## STEP 13 — EXECUTIVE SUMMARY (o pagină)
- **Cât mai e de construit?** 4 faze (A-D), 24 epics; platforma e ~70% construită tehnic,
  ~90% ready comercial (MCP).
- **Credite rămase (total viziune)**: minim 197 / **realist 283** / maxim 396.
- **Investiție minimă (doar venit)**: **~12-20 credite** + acțiunile tale (DNS, Stripe, specialiști).
- **Investiție recomandată 12 luni**: **~350 credite** (realist 283 + buffer 15% + emergency),
  cumpărate trimestrial, ajustate pe dovezi.
- **Autonomie >90% (doar aprobări)**: Fazele A+B+C1/C2 = **~165-190 credite · luna 9-12** —
  condiționată și de VOLUM DE DATE REALE, nu doar de cod (HDI actual 32.5 scade prin utilizare).
- **Ce se construiește primul**: A2+A5 (lansare) ∥ A1 (GI-5P S2) ∥ A3 (Control Center).
- **Ce rulează în paralel**: A1∥A2∥A3, B1∥B3, C1∥C2, D1∥D2 → economie ~30% timp.
- **Ce se amână**: tot ce nu e pe critical path-ul venitului (B, C, D — după lansare).
- **Platformă matură**: luna 8-10. **Contingency rezervat**: 15% standard + 30 credite emergency.
