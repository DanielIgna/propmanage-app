# PropManage — Construction Intelligence Platform
**Analiză de fezabilitate + poziționare vs roadmap-ul existent**  
Data: Feb 2026 · Autor: Emergent (E1) · **Zero cod scris.**

---

## 0. Verdict rapid (TL;DR pentru fondator)

Construction Intelligence Platform (CIP) este **cea mai valoroasă direcție strategică propusă până acum** — dar este și **cel mai mare undertaking** (estimat 10-15 sprints).

**Recomandarea mea de ordonare** (contrar cronologiei „la rând după ce-i pregătit"):

> **Împarte CIP în 4 tranșe** și rulează-le **intercalat** cu Autonomy Orchestrator, NU secvențial. Motiv: Autonomy Orchestrator (P1) e prerequisit pentru Etapele 9-11 din CIP (data quality, price observatory reliability, AI learning loop). Fără el, CIP va cere intervenție manuală constantă — exact opusul obiectivului tău declarat.

**Ordinea propusă (detaliată în §5):**
1. **Autonomy Orchestrator Sprint 1** (~30 credite) → *fundație tehnică*
2. **CIP Tranșa A** — Etapele 3-6 (Nomenclator + Category Hierarchy + Visibility Gate + Admin Overview) → *pozitionare pe piață*
3. **Autonomy Orchestrator Sprint 2** (Dispute/KYC AI) → *unlock scaling*
4. **CIP Tranșa B** — Etapele 7-8 (Price Observatory + Experience Levels) → *diferențiere unică pe piață*
5. **CIP Tranșa C** — Etapele 9-10 (Data Collection Pipeline + Extended DB) → *acumulare date*
6. **CIP Tranșa D** — Etapele 11-12 (AI Learning + Dashboard) → *inteligența emerge natural*

---

## 1. Analiză reutilizare — ce EXISTĂ vs. ce trebuie construit

### 1.1 Componente reutilizabile din arhitectura curentă

| Cerință CIP | Ce există deja | Verdict |
|---|---|---|
| Categorii servicii | `seo_slugs.py` (~7 categorii flat) + `service_categories` pe specialist | 🟡 Trebuie **extins** de la flat la ierarhic |
| Orașe / regiuni | `seo_slugs.py` orașe + `regions.py` + `city_partners.py` | 🟢 **Reutilizabil ca atare** |
| Specialiști + verificare | `specialist_profile.py`, `kyc.py`, `specialist_progression.py`, `verified_estate.py` | 🟢 **Reutilizabil** — flag `is_verified` există |
| Proiecte finalizate | `projects.py`, `requests.py` (status `confirmed`) | 🟡 Există dar **nu are câmpuri de învățare** (cost final, materiale, durată reală vs estimată) |
| Admin control central | 80+ pagini admin, `AdminOverview`, `AdminUsers` | 🟢 **Adaugă pagini noi**, nu rescrie |
| Marketplace filtrare | `marketplace.py` (`marketplace_filters`) | 🟢 Extins natural cu filtru ierarhic |
| Statistici + KPI | `admin_dev_velocity`, `bi_moe.py`, `analytics_growth.py` | 🟢 **Reutilizabil** — CIP Dashboard = pagină nouă peste engine-ul BI existent |
| AI Governance | `ai_governance.py`, `ai_control.py` | 🟢 CIP AI learning se supune același governance |
| Autonomy scoring | `autonomy/engine.py` | 🟢 Adaugă axă nouă: `data_quality` |
| Pattern learning | Bug Memory + Pattern Hunter (P3 Autonomy) | 🟢 **Reutilizabil** pentru „learn from completed projects" |

### 1.2 Componente care trebuie **extinse** (nu construite de la zero)

| Componenta | Extensie necesară |
|---|---|
| `service_categories` schema | De la `string[]` flat → tree hierarchic (`category → subcategory → specialization → service`) |
| `projects` collection | Adăugat: `actual_cost`, `actual_duration`, `materials_used[]`, `estimated_vs_actual_delta` |
| `requests` categorization | Legare la ierarhia nouă (backward compatible cu `category` string) |
| `admin_data_integrity` | Nou check: „categorii publice fără specialist activ" |
| Autopilot sweep | Nou job: `refresh_category_visibility` (rulează la 04:30) |
| Marketplace filters | Filtru pe tree, nu string; auto-hide categorii goale |
| SEO slugs | Auto-generare din nomenclator (nu hardcodat) |

### 1.3 Componente **noi** obligatorii (nu există echivalent)

1. **`construction_taxonomy` collection** — tree ierarhic servicii (~2000-5000 noduri estimat pentru acoperire completă piață RO).
2. **`price_observations` collection** — observații de preț (city × category × experience_level × source × timestamp).
3. **`materials_catalog` collection** — nomenclator materiale (~10.000-50.000 SKU estimat).
4. **`labor_norms` collection** — norme productivitate/consum/durată (~5.000 înregistrări).
5. **`project_learnings` collection** — record anonimizat per proiect finalizat (feed pentru AI).
6. **`construction_intelligence` route + admin pages** — 4-5 pagini noi (Taxonomy Manager, Price Observatory, Materials Catalog, CI Dashboard, Data Ingestion).
7. **Data ingestion pipeline** — endpoint-uri pentru introducere preț (manual admin + import CSV + integrare AI parsing telefoane/emailuri).

### 1.4 Componente **redundante evitabile**

- ❌ NU crea sistem separat de „admin control central" — extinde `AdminOverview` + adaugă tab „Construction Intelligence".
- ❌ NU crea sistem separat de statistici — extinde `bi_moe` + `analytics_growth` cu KPI-uri construction.
- ❌ NU crea sistem separat de verificare specialiști — folosește `verified_estate` + `kyc` existent.
- ❌ NU crea sistem separat de vizibilitate — folosește pattern-ul din marketplace filters + un playbook în Autonomy Orchestrator.

---

## 2. Analiza pe etape a propunerii tale

### Etapa 1 (Analiza arhitecturii) — ✅ DONE prin acest document

### Etapa 2 (Construction Intelligence layer) — 🟢 **VALID**
- Recomandare: creează un namespace clar `/app/backend/construction/` + `/app/frontend/src/pages/admin/construction/`.
- Prefix API: `/api/construction/*`.

### Etapa 3 (Nomenclator complet exterior+interior) — 🔴 **CEA MAI MARE MUNCĂ**
- **Realistic:** cerința ta listează ~80 categorii de bază. Cu 3-5 nivele de granularitate → **2000-5000 noduri** de completat.
- **Problemă:** nomenclatorul nu poate fi generat AI curat — trebuie **cross-check uman cu constructori reali** ca să fie util.
- **Recomandare:** MVP cu 50 categorii top × 3-5 servicii fiecare = ~200 noduri. Extindere iterativă.
- **Reutilizează:** taxonomii publice existente (COR — Codul Ocupațiilor România; CAEN pentru firme). Import inițial de acolo.

### Etapa 4 (Structură ierarhică) — 🟢 **VALID**
- Schema propusă e corectă. Un singur amendament: adaugă `parent_id` + `depth_level` (0-N) în loc de nivele hard-coded → flexibilitate viitor.

### Etapa 5 (Vizibilitate condiționată) — 🟢 **BRILLIANT + REUTILIZABIL**
- Această regulă e un **playbook perfect pentru Autonomy Orchestrator**.
- Playbook: `refresh_category_visibility` → rulează la fiecare specialist create/verify/suspend → recalculează `is_publicly_visible` per nod.
- **Bonus:** poți afișa admin-ului „categorii ascunse cu potențial" (cerere clienți dar 0 specialiști) → oportunitate de recrutare specialiști.

### Etapa 6 (Admin principal control central) — 🟢 **VALID**
- Adaugă în `AdminOverview` un card nou „Construction Intelligence" + pagină dedicată `/admin/construction`.
- Filtrele cerute (categorie/oraș/specialist/stadiu/valoare/user) există parțial în `admin/projects` — se extind.
- Export CSV/PDF: reutilizezi `analytics_growth.py` PDF pipeline (deja construit cu reportlab).

### Etapa 7 (Price Observatory) — 🔴 **VALID DAR RISCANT**
- Schema propusă (city × category × UM × min/med/prem × trust score) e corectă.
- **Riscul real:** date de calitate slabă → observator inutil.
- **Mitigare:** `trust_grade` obligatoriu; observații cu <3 surse marcate „preliminary".
- **Reutilizează:** Pattern Hunter (P3) pentru detectare outliers.

### Etapa 8 (Niveluri experiență) — 🟢 **VALID**
- Există deja `specialist_progression.py` cu tier-uri. Extindere naturală: `experience_years` calculat din progresie + `tier` (Beginner/Mid/Expert).
- Backward compatible cu `experience_tiers.py`.

### Etapa 9 (Colectare date) — 🔴 **BOTTLENECK-UL PRINCIPAL**
- Aici e „gap-ul real" al propunerii. Restul e software; asta e **operațiune umană** (apeluri telefonice, cross-check).
- **Recomandare:** construiește **Data Ingestion Console** pentru admin/sub-admin cu:
  - Formular rapid „adaugă preț observat" (UI mobil-first pentru telefoane)
  - Import CSV bulk
  - AI email parser (Emergent LLM Key + Nano Banana OCR pentru poze cu oferte)
  - Auto-scraping public (oferte firme, portaluri specializate) — cu respectare robots.txt + GDPR
- **Fără infrastructura asta, CIP rămâne un schelet gol.**

### Etapa 10 (Baza materiale/manoperă) — 🟡 **AMÂNABIL**
- MVP-ul poate porni cu **doar categorii + prețuri**. Materials catalog + labor norms sunt Phase 2 din CIP.
- Recomandare: startuiește cu ~500 SKU-uri materiale top + extinzi în timp.

### Etapa 11 (AI Learning) — 🟢 **PLUG-INTO EXISTING**
- Fluxul: `request` → `confirmed` → hook care declanșează formular „post-project" (client + specialist confirmă cost real, durată reală, materiale) → anonymize → `project_learnings`.
- **Reutilizează:** `ai_governance.py` pentru guvernanță pe agentul de învățare.
- **AI Agent nou:** `PriceLearner` — rulează weekly, ajustează `price_observations` cu date reale.

### Etapa 12 (Dashboard Construction Intelligence) — 🟢 **VALID, REUTILIZĂM STACK-UL**
- Frontend: reutilizezi componentele din `AnalyticsGrowthPage` (chart-uri, KPI cards).
- Indicatorii propuși sunt corecți. **Adăugări** recomandate de mine:
  - `Data Coverage Index` (cât % din categorii × orașe au date suficiente)
  - `Price Volatility Index` (cât variază prețurile lună de lună — semnal inflație)
  - `Specialist Density` (specialiști activi/1000 locuitori per oraș)
  - `Category Momentum` (categorii în creștere/scădere cerere)

### Etapa 13 (Principii) — ✅ TOTAL DE ACORD

---

## 3. Complexitate & efort (realistic)

| Tranșă | Ce include | Sprints | Credite estimate |
|---|---|---|---|
| **CIP-A** — Etapele 2, 3 (MVP), 4, 5, 6 | Layer + taxonomy schema + hierarchy + visibility gate + admin overview | 3 | ~90-120 |
| **CIP-B** — Etapele 7, 8 | Price Observatory + Experience Levels | 2 | ~60-80 |
| **CIP-C** — Etapele 9, 10 | Data Ingestion Console + Materials/Labor DB (MVP) | 3 | ~90-120 |
| **CIP-D** — Etapele 11, 12 | AI Learning loop + CI Dashboard | 2 | ~60-90 |
| **Total CIP** | | **10 sprints** | **~300-410 credite** |
| **Autonomy Orchestrator Sprint 1** | Core + 3 playbooks P1 | 1 | ~30-40 |
| **Autonomy Sprint 2** (Dispute/KYC AI) | | 2 | ~60-80 |

**Buget total realistic pentru transformarea completă:** ~400-500 credite pentru CIP + Autonomy P1+P2. **Nu se face în o săptămână.**

---

## 4. Recomandare ordine — argumentată

### 4.1 De ce Autonomy Sprint 1 înainte de CIP?
**3 motive concrete:**
1. **CIP Etapa 5 (visibility gate)** este exact tipul de logic pe care Autonomy Orchestrator o rulează frumos ca playbook. Fără orchestrator, o construiești ad-hoc și trebuie rescrisă mai târziu.
2. **CIP Etapa 11 (AI Learning)** are nevoie de Pattern Hunter (P3 Autonomy) pentru clustering date. Poți construi hack-ul, dar duplici efort.
3. **CIP Etapa 9 (data collection)** produce date pline de erori inițial. Data Integrity Auto-Fix (P1 Autonomy) previne acumularea de garbage.

### 4.2 De ce CIP-A înainte de Autonomy Sprint 2?
1. **Diferențiere de piață**: nomenclatorul + gating vizibilitate + admin control sunt vizibile clienților/investitorilor. Autonomy Sprint 2 (Dispute/KYC AI) este invizibil dar critic pt scalare.
2. **CIP-A e independentă tehnic** de Autonomy 2 — poți face în paralel dacă ai bandwidth, sau secvențial.
3. **Positioning pentru investitori/parteneri**: „prima Construction Intelligence Platform din RO" e story mult mai puternic decât „auto-triage dispute".

### 4.3 De ce CIP-B (Price Observatory) merită prioritizare mare
Aceasta este **piesa unică de piață**. Nu există în RO un Zillow/Wren pentru construcții. CIP-A fără CIP-B = doar un marketplace cu ierarhie mai bună. CIP-A+B = *the thing*.

### 4.4 De ce CIP-C și CIP-D pot aștepta
- Fără date acumulate, dashboard-ul (D) e gol.
- Materials/Labor DB (C parte 2) beneficiază de datele adunate în B.
- Aceste tranșe se dezvoltă natural după 3-6 luni de operare CIP-A+B.

---

## 5. Ordinea finală recomandată (concret, prioritizat)

```
LUNA 1 (~30-40 credite)
├── Autonomy Orchestrator Sprint 1
│   ├── Orchestrator core (bus + correlator + executor + ledger)
│   ├── Playbook: smoke_fail → auto QA session
│   ├── Playbook: autonomy_score_drop → auto sweep
│   └── Playbook: webhook_fail → retry backoff
│
LUNA 2-3 (~90-120 credite)
├── CIP-A: Fundația Construction Intelligence
│   ├── construction_taxonomy schema (tree)
│   ├── MVP 200 noduri (importate + curated)
│   ├── Migrare service_categories → hierarchy (backward compat)
│   ├── Visibility gate playbook (folosește Orchestrator!)
│   ├── Admin: /admin/construction — taxonomy manager + project central
│   └── Client/specialist UI adaptată la hierarchy
│
LUNA 4 (~60-80 credite)
├── Autonomy Orchestrator Sprint 2 (opțional intercalat)
│   ├── Dispute AI Triage
│   ├── KYC Auto-Approve (unlock scaling)
│   └── Marketplace Medic
│
LUNA 5-6 (~60-80 credite)
├── CIP-B: Price Observatory (piesa unică!)
│   ├── price_observations collection + trust grading
│   ├── Admin Data Ingestion Console (formular rapid + CSV import)
│   ├── Experience levels integration
│   └── Public: „prețuri orientative" per categorie × oraș
│
LUNA 7-9 (~90-120 credite)
├── CIP-C: Data Collection Pipeline extins
│   ├── AI email/telefon parser (LLM key + OCR)
│   ├── Materials catalog MVP (500 SKU)
│   ├── Labor norms MVP (300 înregistrări)
│   └── Public trust scoring
│
LUNA 10-12 (~60-90 credite)
├── CIP-D: AI Learning + Dashboard
│   ├── project_learnings pipeline (post-confirmed hook)
│   ├── PriceLearner agent (weekly)
│   ├── CI Dashboard cu KPI-uri complete
│   └── „PropManage Construction Index" public (marketing gold)
```

**Efort total:** ~400-500 credite spread pe ~12 luni.  
**Positioning result:** cea mai completă platformă de Construction Intelligence din RO + platformă self-driving.

---

## 6. Riscuri de care trebuie să știi (honest)

1. **Nomenclatorul e uman-intensiv.** AI poate genera candidați dar validarea cere expert construcții.
2. **Colectarea prețurilor e continuă — necesită dedicație (fondator sau angajat).** Automatizarea AI ajută 40-60% dar restul e telefon/relații.
3. **GDPR pe project_learnings** — anonimizarea trebuie validată legal. Buget avocat: obligatoriu.
4. **Concurență viitoare.** Odată public, oricine te poate copia. Advantage-ul e **date + specialiști aflow + brand**. Fereastra e ~12-18 luni.
5. **Dashboard-ul devine util doar după ~1000 proiecte finalizate în platformă.** Până atunci, arată gol. Plan A: seed cu date parteneri / cercetare externă.

---

## 7. Ce răspund la întrebările tale finale

> **Este bine să implementez CIP înainte de ce-i deja pregătit în lucru?**  
Nu în totalitate. **Da parțial** — CIP-A (Etapele 3-6) poate începe după Autonomy Sprint 1. CIP-B (Price Observatory) e diferențiatorul de piață și merită prioritizat. CIP-C/D beneficiază de restul Autonomy.

> **CIP e prioritate absolută?**  
Din perspectiva **valorii de piață**: DA, e cea mai puternică direcție strategică propusă vreodată în chat-urile noastre.  
Din perspectiva **execution safety**: NU sări peste Autonomy Sprint 1 (30 credite). E jena tehnică minoră pentru un unlock enorm.

> **Recomandare finală într-o frază:**  
> **Autonomy Sprint 1 → CIP-A → CIP-B → (Autonomy 2 sau CIP-C/D în funcție de bandwidth) → restul iterativ.**

---

**Documente relevante:**
- `/app/memory/AUTONOMOUS_EVOLUTION_ROADMAP.md` (roadmap autonomy)
- `/app/memory/CONSTRUCTION_INTELLIGENCE_ROADMAP.md` (acest document)
- `/app/memory/BUGS.md` (tracker QA)
- `/app/memory/PRD.md` (product requirements master)
