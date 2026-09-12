# BUILDING TYPOLOGY FOUNDATION — RESEARCH / ARCHITECTURE AUDIT

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Classification**: Foundation Audit — Research-only
**Board Directive**: BD-RDPE (Research-Driven Product Evolution) — Feature Freeze ACTIV
**Scope**: Foundation Audit **exclusiv conceptual**. Fără cod, fără UI, fără DB, fără API, fără Blueprint change, fără Roadmap change, fără metodologie change, fără Digital Twin change.

---

## 0. Executive Summary

Acest document răspunde întrebării: **poate PropManage susține conceptual, în viitor, o cercetare de tip „Building Typology / HartaBlocuri" fără a implementa încă un asemenea sistem?**

Verdict: **DA — dar exclusiv la nivelul unui pilot de validare a datelor de referință.** Infrastructura de research există (Interview Registry, Pattern Registry, Research Coverage Matrix, PROPERTY_DNA v2, Digital Twin Maturity L0-L5). Vocabularul canonic există parțial și trebuie **extins conceptual**, nu duplicat. Nu există niciun engine, niciun import extern, niciun matching, niciun scoring. Pipeline-ul metodologic (Interview → Observation → Emerging Pattern → Validated Pattern Candidate) rămâne intact.

Decision Gate: **A — NOT READY for build. READY for METHODOLOGY DESIGN + PILOT PROPOSAL only.**

---

## 1. Reuse Audit

### 1.1 Verdict global
**Reuse Audit: PASS · Duplicate Detected: NONE.**

Termenii `typology`, `tipologie`, `HartaBlocuri`, `reference plan`, `reference apartment`, `typology family`, `typology variant`, `reference 3D`, `typology match` **nu apar** în:
- `/app/memory/**` (toate registrele, audit-urile, documentele constituționale)
- `/app/docs/**` (blueprint, roadmap, playbook-uri)
- `/app/backend/**` (routes, modele, servicii)
- `/app/frontend/**` (componente, pagini)

Nu există entitate, tabel, colecție MongoDB, API route, componentă React, registry sau document care să conțină deja aceste concepte. **Toate conceptele Building Typology Foundation sunt introduse pentru prima dată de acest audit conceptual.**

### 1.2 Infrastructură existentă REUTILIZABILĂ (nu se dublează)

| Concept audit | Există deja în PropManage? | Ce reutilizăm | Ce completăm conceptual |
|---|---|---|---|
| **Building Instance** | ✅ DA — `buildings` collection (`/app/backend/routes/community_buildings.py`) cu câmpurile: `name`, `address`, `city`, `construction_year`, `floors`, `apartments_total` (via `BuildingPatch` în `building_admin.py`). | Entitatea „Building Instance" din audit = `buildings.*` din DB (deja în producție). | Vocabular: `Building Instance ≠ Typology`. |
| **Apartment Instance** | ✅ DA — `properties` collection, deja legată de `building_id`. | „Apartment Instance" = document `properties` cu `building_id` non-null. | Vocabular: `Apartment Instance ≠ Reference Apartment`. |
| **Provenance model** | ✅ DA — `PROPERTY_DNA v2` (memory/GI5P_PROPERTY_INTELLIGENCE.md, §2): fiecare atribut are `{valoare, sursă, confidence, verificat_la}`. | Reutilizăm modelul provenance-first pentru toate câmpurile Reference/Reported/Observed/Verified. | Vocabular: **Source Provenance ≠ Verification Status** (explicit în §3.7 mai jos). |
| **Digital Twin Maturity** | ✅ DA — `Digital Twin Maturity Score L0-L5` (GI5P §13). | Digital Twin = starea VERIFICATĂ / CURRENT a proprietății. Nu se confundă cu Reference Data. | Clarificare explicită (§5). |
| **Property Knowledge Graph** | ✅ DA — noduri `Property/Zone/Asset/Person/Document/Event/Risk/Service/Warranty/Lesson` + muchii tipizate (GI5P §9). | Building, Typology, Reference Plan sunt noduri **candidat** viitoare — nu se adaugă azi. | Vocabular: rămâne ipoteză research, nu decizie de graph store. |
| **Reference libraries (actuarial)** | ✅ DA — GI5P §7: „bibliotecă de referință (durate viață/revizii per activ, statică, versionată)". | Precedent conceptual pentru **Reference Data ≠ Verified Data** — deja practicat pe active. | Extensie conceptuală la nivel de clădire (fără a implementa). |
| **Evidence & Confidence** | ✅ DA — GI5P §10: „orice scor: componente + formulă versionată + dovezi (id-uri timeline) + surse". | Modelul Evidence din audit = același concept, aplicat clădirii. | Nimic nou de inventat. |
| **Interview → Pattern pipeline** | ✅ DA — `INTERVIEW_REGISTRY.md`, `PATTERN_REGISTRY.md`, `/admin/research-coverage`. | Orice observație despre tipologii intră aici, nu într-un sistem paralel. | Zero sistem paralel. |
| **Research Coverage Matrix** | ✅ DA — `ResearchCoveragePage.jsx` consumă `INTERVIEW_REGISTRY.md`. | Un viitor pilot Typology este raportat în aceeași infrastructură. | Zero UI nouă. |
| **SSOT Registry** | ✅ DA — `/app/memory/registries/SSOT_REGISTRY.md`. | Dacă vreodată se validează un concept Typology, se înregistrează aici — nu într-un registry separat. | Zero registry paralel. |

### 1.3 Concepte ABSENTE (introduse conceptual, fără implementare)

| Concept | Există? | Statut audit |
|---|---|---|
| Typology | ❌ | Introdus conceptual (§4). |
| Typology Family | ❌ | Introdus conceptual (§4). |
| Typology Variant | ❌ | Introdus conceptual (§4). |
| Reference Plan | ❌ | Introdus conceptual (§4). |
| Reference Apartment | ❌ | Introdus conceptual (§4). |
| Reference 3D | ❌ | Introdus conceptual (§4). |
| Reference Data (as level) | ❌ (există doar ca practică actuarială pe active) | Formalizat conceptual (§5). |
| Official / Administrative Documentation | ❌ | Introdus conceptual (§5). |
| Reported Data (as formal level) | ❌ (există implicit în DNA v2) | Formalizat (§5). |
| Observed Data (as formal level) | ❌ (există implicit în Interview Repository) | Formalizat (§5). |
| Verified Data (as formal level) | ❌ (există implicit în DNA v2 `verificat_la`) | Formalizat (§5). |
| Current Property State (as formal level) | ❌ | Formalizat (§5). |
| Source Conflict Model | ❌ | Introdus conceptual (§8). |
| Typology Match Concept | ❌ | Introdus conceptual (§7). |
| Candidate Typology Risk Profile | ❌ | Introdus conceptual (§9). |

**Regulă strictă**: niciun concept nou nu creează entitate, colecție, API sau componentă frontend. Toate rămân **vocabular canonic în acest document**.

---

## 2. Existing Infrastructure Found

Următoarea infrastructură deja construită va susține (dacă și când Board Directive va permite) un viitor pilot Typology:

**Backend & Data**
- `buildings` collection (community_buildings.py + building_admin.py) — nod „Home Graph".
- `properties` collection cu `building_id` (aditiv, fără migrare necesară).
- `community_campaigns`, `maintenance_tasks`, `building_announcements` (funcționale, nu sunt afectate).
- Property DNA v2 model (documentat în GI5P, non-implementat integral).
- Reference libraries actuariale (concept existent pe active, GI5P §7).

**Research infrastructure**
- `/app/memory/audits/` — 10 interviuri validate (AP-001 → AP-010).
- `/app/memory/audits/PROPMANAGE_PRESIDENT_RESEARCH_COHORT_v1.0.md` — canonical master synthesis.
- `/app/memory/registries/INTERVIEW_REGISTRY.md` — SSOT interviuri.
- `/app/memory/registries/PATTERN_REGISTRY.md` — SSOT pattern-uri.
- `/app/memory/registries/SSOT_REGISTRY.md` — SSOT enterprise topics.
- `/app/frontend/src/pages/admin/ResearchCoveragePage.jsx` — Research Coverage Matrix (fondator).
- `/app/memory/audits/RESEARCH_REPORT_TEMPLATE.md`, `INTERVIEW_TEMPLATE.md`, `PATTERN_TEMPLATE.md`, `REUSE_AUDIT_TEMPLATE.md`.

**Governance**
- `BOARD_DIRECTIVE_RESEARCH_DRIVEN_EVOLUTION.md` — Feature Freeze activ.
- `MASTER_KNOWLEDGE_GOVERNANCE.md` — Constituția Artifact Types.

**Verdict**: infrastructura existentă acoperă complet Faza Research. Nu se creează nimic nou.

---

## 3. Canonical Vocabulary

Definițiile de mai jos sunt **canonice** pentru toate viitoarele documente de research pe temă Typology. Se folosesc exclusiv aceste denumiri. Sinonimele („bloc-tip", „bloc-standard", „model de bloc") **nu se introduc**.

### 3.1 BUILDING (Building Instance)
O clădire reală, individuală, cu adresă unică. În PropManage = un document din colecția `buildings`. Deține: identitate, adresă, localizare, an construcție (estimat sau exact), nr. etaje, nr. scări, nr. apartamente.

**Regulă**: Building ≠ Typology. O clădire poate fi asociată cu o tipologie candidat, dar tipologia nu devine niciodată identitatea clădirii.

### 3.2 APARTMENT INSTANCE
Un apartament real, individual, într-o clădire reală. În PropManage = un document din colecția `properties` cu `building_id` non-null.

**Regulă**: Apartment Instance ≠ Reference Apartment. Un apartament real poate fi comparat cu un apartament de referință dintr-o tipologie, dar rămâne entitate distinctă.

### 3.3 TYPOLOGY
O clasă de clădiri cu caracteristici comune (formă, dimensiuni, perioadă construcție, configurație structurală, nivel confort). O tipologie **nu este o clădire**; este un tipar arhitectural.

**Regulă**: `TYPOLOGY ≠ BUILDING INSTANCE`. O tipologie poate avea 0, 1 sau N clădiri asociate ulterior.

### 3.4 TYPOLOGY FAMILY
Un grup de tipologii înrudite, adesea produse ale aceleiași perioade/politici de construcție (ex: familii tipologice interbelice, comuniste tip-bară, tip-turn, tip-lamă, dezvoltări post-2000 rezidențiale). Familia nu impune dimensiuni exacte, ci un „idiom" arhitectural.

**Regulă**: Family conține 1..N Typology.

### 3.5 TYPOLOGY VARIANT
O variație dimensională/configurațională a unei tipologii (ex: aceeași tipologie cu 4 etaje vs. 10 etaje, cu 2 scări vs. 4 scări). Varianta păstrează idiomul tipologiei părinte dar diferă la parametri.

**Regulă**: Typology conține 1..N Variant. Un Variant nu devine niciodată Typology autonomă.

### 3.6 REFERENCE PLAN
Un plan arhitectural de referință asociat unei tipologii/varianti (nivel, apartament, secțiune). Reference Plan este o **reprezentare de referință** — nu este planul real măsurat al unei clădiri specifice.

**Regulă**: Reference Plan este Reference Data (§5.1). Nu se ridică la Verified Data prin simpla asociere cu o clădire.

### 3.7 REFERENCE APARTMENT
Configurația de referință a unui apartament tipic dintr-o tipologie/varianta (rooms, suprafață aproximativă, poziție relativă, geometrie de referință).

**Regulă**: Reference Apartment ≠ Apartment Instance.

### 3.8 REFERENCE 3D
Un model 3D de referință asociat unei tipologii/varianti. **Nu** este Digital Twin. **Nu** este model real al clădirii. Este o reprezentare geometrică ideală/tipică.

**Regulă**: Reference 3D nu se importă, nu se generează, nu se stochează în acest sprint. Este strict concept.

### 3.9 REFERENCE DATA
Date provenite din surse externe (ex: HartaBlocuri, cataloage arhitecturale, cataloage IPCT/ISPCF, arhive publice) care descriu tipologia teoretică a unei clădiri sau categorii de clădiri.

**Regulă strictă**: Reference Data **nu se promovează niciodată automat** în Official, Reported, Observed, Verified sau Current State. Rămâne Reference până la o verificare independentă.

### 3.10 OFFICIAL / ADMINISTRATIVE DOCUMENTATION
Date provenite din surse oficiale/administrative (Primărie, Cadastru, ANRE, ISU, cărți tehnice, autorizații, procese-verbale). **Source Provenance ≠ Verification Status**: un document oficial NU devine automat Verified. Poate fi provenit oficial dar **conținutul** trebuie totuși verificat, mai ales dacă documentul este vechi sau contrazice starea observată.

**Regulă**: Official Documentation este o categorie separată de Reference Data. Ambele sunt input în modelul Evidence, dar cu ponderi și proceduri de verificare diferite.

### 3.11 REPORTED DATA
Date raportate voluntar de președinte, administrator, proprietar sau alt actor uman. Sunt subiect de verificare. Pot fi utile chiar dacă neverificate (ex: „aici a fost o infiltrație acum 3 ani"), dar nu constituie adevăr tehnic.

### 3.12 OBSERVED DATA
Date obținute prin observație directă în cadrul cercetării (interviuri, inspecții, fotografii, măsurători neutre de cercetător). Sunt cea mai puternică sursă neverificată.

### 3.13 VERIFIED DATA
Date confirmate printr-o procedură independentă (specialist, măsurare instrumentală, cross-check între ≥2 surse independente, audit tehnic formal). Verified Data poartă `verified_by`, `verification_method`, `date`, `confidence`.

**Regulă**: Verificarea nu este o etichetă declarativă. Este o procedură cu dovadă.

### 3.14 CURRENT PROPERTY STATE
Reprezentarea stării actuale documentate a proprietății, compusă din:
- Verified Data unde există,
- Observed Data unde nu există Verified,
- Reported Data unde nu există Observed,
- Absența explicită (UNKNOWN) unde nu există nimic.

**Regulă**: Current State este **rezultatul consolidării surselor**, nu o sursă primară.

### 3.15 DIGITAL TWIN
Reprezentarea vie a stării verificate/actuale a unei proprietăți (definit deja în PROPERTY_DNA.md și GI5P §13, cu Maturity L0-L5). Digital Twin **nu este** Reference Data. **Nu este** Reference 3D. **Nu este** ipoteză tipologică.

**Regulă**: Digital Twin = ceea ce **ȘTIM** despre proprietate cu dovadă. Restul rămâne în afara Digital Twin sau intră cu confidence explicit sub prag.

### 3.16 EVIDENCE
O unitate atomică de dovadă: `{source, source_type, date, confidence, evidence_status}`. Se atașează oricărui atribut care nu este ipoteză liberă.

### 3.17 VERIFICATION
Un act formal de verificare: `{verified_by, verification_method, date, confidence}`. Verification produce Verified Data.

---

## 4. Building Typology Foundation (Conceptual Data Model)

**IMPORTANT**: Structurile de mai jos sunt exclusiv **conceptuale**. Nu sunt schema DB. Nu sunt Pydantic models. Nu sunt API responses. Nu se implementează.

### 4.1 BUILDING (conceptual)
- identity (id, canonical name)
- address (street, number, city, region, country)
- location (coordinates, if known)
- construction_year (value, precision: `exact` | `estimated` | `unknown`)
- number_of_floors
- number_of_stairs
- apartment_count
- typology_candidate_ref (nullable, optional)
- current_state_ref (link to §4.7)

### 4.2 TYPOLOGY (conceptual)
- id
- family
- shape (bară, turn, lamă, punct, mixt, unknown)
- dimensions (approximate: length × width × height ranges)
- construction_period (start_year, end_year, source_context)
- comfort_level (1, 2, 3, deosebit, post-2000 rezidențial, custom)
- structural_configuration (panouri mari, cadre BA, zidărie portantă, mixt, unknown)
- default_variant_ref

### 4.3 TYPOLOGY VARIANT (conceptual)
- id
- parent_typology_ref
- variant_label
- floors_range
- stairs_range
- apartments_per_level_range
- notes

### 4.4 REFERENCE PLAN (conceptual)
- id
- source (ex: HartaBlocuri, catalog IPCT, arhivă publică)
- plan_type (level, section, apartment, façade)
- floor_configuration
- apartment_configuration (ref)
- confidence (low, medium, high)
- provenance_notes

### 4.5 REFERENCE APARTMENT (conceptual)
- id
- apartment_type (garsonieră, 2 camere, 3 camere, 4 camere, decomandat/semidecomandat/nedecomandat, unknown)
- rooms
- approximate_area
- position_in_building (colț, mijloc, capăt scară, unknown)
- reference_geometry_ref (link la Reference 3D dacă există)

### 4.6 REFERENCE 3D (conceptual)
- id
- reference_model (locator abstract; NU se stochează)
- source
- confidence
- status (candidate, available, deprecated)

### 4.7 EVIDENCE (conceptual)
- id
- attached_to (Building | Apartment | Typology | ReferencePlan | ...)
- source (identifier)
- source_type (Reference | Official | Reported | Observed | Verified)
- date
- confidence (low, medium, high)
- evidence_status (draft, active, contested, superseded)

### 4.8 VERIFICATION (conceptual)
- id
- attached_to
- verified_by (specialist_id, cross_check_procedure, instrument)
- verification_method (visual, measurement, document_review, expert_report, multi_source_cross_check)
- date
- confidence

**Regulă structurală**: `TYPOLOGY ≠ BUILDING INSTANCE`. Un Building are cel mult **una** `typology_candidate_ref` la un moment dat, dar tipologia rămâne separată. Schimbarea candidatului nu schimbă Building-ul.

**Zero implementation**: Nu se creează tabele, colecții, endpoint-uri, componente React. Documentul de față este singurul artefact.

---

## 5. Source Separation Model

Cinci niveluri **canonice**, ordonate de la sursă externă la stare curentă:

```
┌────────────────────────────────────────────────────────────┐
│  1. REFERENCE DATA                                         │
│     Surse externe (HartaBlocuri, cataloage IPCT/ISPCF,     │
│     arhive publice). Tipologie teoretică.                  │
│     → NU se promovează automat.                            │
├────────────────────────────────────────────────────────────┤
│  2. OFFICIAL / ADMINISTRATIVE DOCUMENTATION                │
│     Primărie, Cadastru, cărți tehnice, autorizații, ISU,   │
│     ANRE. Source Provenance ≠ Verification Status.         │
├────────────────────────────────────────────────────────────┤
│  3. REPORTED DATA                                          │
│     Președinte, administrator, proprietar (declarativ).    │
├────────────────────────────────────────────────────────────┤
│  4. OBSERVED DATA                                          │
│     Observație directă de cercetător (interviu, inspecție, │
│     fotografie, măsurare neutră).                          │
├────────────────────────────────────────────────────────────┤
│  5. VERIFIED DATA                                          │
│     Confirmare independentă (specialist, cross-check ≥2    │
│     surse independente, audit tehnic, măsurare             │
│     instrumentală).                                        │
├────────────────────────────────────────────────────────────┤
│  →  CURRENT PROPERTY STATE                                 │
│     Consolidarea celor de mai sus, cu marcaje UNKNOWN     │
│     unde nicio sursă nu există.                            │
├────────────────────────────────────────────────────────────┤
│  →  DIGITAL TWIN                                           │
│     Proiecția vie a Current Property State (Maturity L0-L5)│
│     Nu se confundă cu Reference Data.                      │
└────────────────────────────────────────────────────────────┘
```

**Reguli invariante**:
1. Reference Data ≠ Verified Data.
2. Official Documentation ≠ Verified Data.
3. Reported ≠ Observed.
4. Observed ≠ Verified.
5. Verified ≠ Current State (Current State e agregat, poate include niveluri inferioare acolo unde Verified lipsește).
6. Current State ≠ Digital Twin (Digital Twin adaugă maturity, timeline, health — funcțional).
7. Provenance provenit dintr-o sursă oficială **nu ridică** automat un fapt la Verified. Trebuie verificat conținutul.

Model conceptual condensat:

```
Reference / Official / Reported / Observed
        ↓
     Evidence
        ↓
   (Source Conflict? → §8)
        ↓
    Verification
        ↓
   Verified Fact
        ↓
  Current State
        ↓
  Digital Twin
```

---

## 6. HartaBlocuri Data Role

**Statut canonic**: HartaBlocuri este tratată exclusiv ca **REFERENCE DATA SOURCE**.

**Nu** este:
- Verified Data
- Digital Twin
- Ground Truth
- Official Documentation (chiar dacă unele câmpuri pot deriva din surse publice oficiale — provenance ≠ verification)
- Sursă unică de adevăr pentru nicio clădire

**Tipuri de informații de referință** pe care le-ar putea furniza (indicativ, non-exhaustiv, **availability = UNKNOWN până la audit sursă**):

| Câmp candidat | Rol | Nivel implicit | Note |
|---|---|---|---|
| address | Reference | 1 | Cross-check cu Building Instance address. |
| building_number | Reference | 1 | Idem. |
| coordinates | Reference | 1 | Necesar cross-check GPS/measurement. |
| estimated_construction_year | Reference | 1 | **Estimare**, nu an exact. |
| floors | Reference | 1 | Confruntat cu observație. |
| stairs | Reference | 1 | Idem. |
| apartments | Reference | 1 | Idem. |
| apartment_types | Reference | 1 | Reference Apartment candidate. |
| typology | Reference | 1 | Typology / Family / Variant candidate. |
| reference_plans | Reference | 1 | Reference Plan candidate. |
| reference_geometry | Reference | 1 | Reference 3D candidate. |
| dimensions | Reference | 1 | Ranges, nu valori exacte. |
| comfort_category | Reference | 1 | Ipoteză, necesită validare. |
| variants | Reference | 1 | Typology Variant candidate. |
| other_metadata | Reference | 1 | UNKNOWN până la audit. |

**Regulă strictă (disponibilitate)**:
Dacă nu s-a făcut audit direct al sursei HartaBlocuri, **disponibilitatea fiecărui câmp este `UNKNOWN`**. Nu se presupune că toate câmpurile există pentru toate clădirile. Nu se presupune că datele existente sunt corecte.

**Zero acțiune de acces automat**: acest audit nu autorizează nicio conexiune, scraping, import CSV, import DWG, import 3D sau achiziție de date HartaBlocuri. Rămâne exclusiv research conceptual.

---

## 7. Typology Match — Concept

**Statut**: exclusiv conceptual. Nu se implementează algoritm. Nu se calculează scoruri reale.

Un viitor `TYPOLOGY MATCH` ar exprima gradul de similitudine între o Building Instance și un candidat Typology/Variant.

**Formă conceptuală**:

```
Building Instance:    Strada X / Bloc Y
Reference Typology:   Bară / Confort 2 / 1970-1980
Match:                82%   (VALOARE ILUSTRATIVĂ — NEIMPLEMENTATĂ)
Status:               Candidate Match
Confidence:           Medium
Evidence:             { floors_match, apartments_match, façade_shape_match, ... }
```

**Reguli invariante**:
1. Scorul este ilustrativ. **NU** există formulă adoptată.
2. **NU** se scrie engine, funcție Python, endpoint, componentă React.
3. Un Match rămâne întotdeauna **Candidate** până la Verification independentă.
4. Un scor ridicat nu produce Verified Data. Doar reduce prioritatea de investigație.
5. Un Match cu confidence Low se raportează, nu se ascunde. Absența Match-ului este ea însăși evidence.

---

## 8. Source Conflict Model

Când două surse (Reference vs. Official, Official vs. Reported, Reported vs. Observed etc.) diferă asupra aceluiași atribut, **conflictul se păstrează ca informație de cercetare** și **nu se rezolvă automat** prin alegerea uneia dintre surse.

**Model conceptual**:

```
Reference: floors = 5
Official:  floors = 5
Reported:  floors = 5
Observed:  floors = 4   ← CONFLICT

→ Nu se suprascrie Reference/Official/Reported cu Observed.
→ Nu se ignoră Observed.
→ Se înregistrează Source Conflict cu toate valorile și sursele lor.
→ Se declanșează Verification (dacă e prioritar).
→ Verified Fact rezolvă conflictul cu evidence.
→ Current State reflectă Verified Fact.
→ Sursele conflictuale rămân în istoric.
```

**Structură conceptuală Source Conflict (non-implementată)**:
- `attribute_ref` (ex: `Building.floors`)
- `values` (list of `{value, source_type, source_id, date, confidence}`)
- `conflict_status` (open, under_verification, resolved)
- `resolution` (nullable: `{winning_value, verification_ref, date}`)

**Reguli invariante**:
1. Un conflict nu se închide prin vot majoritar de surse. Se închide prin Verification.
2. „Official spune X" **nu** are prioritate automată. Poate fi verificat sau contestat.
3. Absența datelor într-o sursă (UNKNOWN) **nu** produce conflict — produce doar acoperire redusă.
4. Un conflict rezolvat rămâne vizibil în istoric ca lecție de cercetare.

---

## 9. Research Integration Model

**Corelarea Typology cu President Interviews (AP-001…AP-010) — regulă strictă**:

Observațiile din interviuri sunt **evidence**, nu **truth of typology**. Vechea eroare uzuală (a asuma că problemele observate la o clădire dintr-o perioadă se aplică automat tuturor clădirilor din aceeași perioadă) **este interzisă metodologic**.

**Exemplu canonic (aplicat cohortei existente)**:

```
Typology (candidate):  Familia „post-1975 · bară · 4 etaje · scări multiple"
Building instances:    AP-002 (Mehedinți, 1976, 20 apt),
                       AP-004 (Negoiu 10, 1975, 40 apt),
                       AP-009 (Mehedinți 23, 1976, 104 apt),
                       AP-010 (Mehedinți 17, 1976, 104 apt)

Reported issue (AP-004): lipsă carte tehnică
Status pattern:          REPORTED EVIDENCE for AP-004
                         DO NOT TRANSFORM into „Risk of Typology X"

Pentru a deveni „Typology-level risk", trebuie:
  - ≥ 3 confirmări independente (metodologia existentă),
  - fiecare pe câte o clădire distinctă din aceeași tipologie candidat,
  - fiecare validată pe pipeline: Observation → Emerging Pattern → Validated Pattern Candidate.
```

**Regulă absolută**: o observație la o clădire nu se propagă la tipologie fără evidence independente adiționale. Pipeline-ul metodologic rămâne autoritatea.

**Legătură cu infrastructura existentă**: dacă și când pattern-uri legate de tipologii ar deveni Validated, ele se înregistrează în `PATTERN_REGISTRY.md`, nu într-un sistem nou. Fondatorul le vede prin `ResearchCoveragePage.jsx`.

---

## 10. Candidate Typology Risk Profile — Concept

**Statut**: exclusiv conceptual. Nu este engine. Nu este alertă. Nu este scoring produs.

Un viitor `CANDIDATE TYPOLOGY RISK PROFILE` ar grupa **observații de cercetare** repetate în cadrul unei tipologii candidat, cu statut `RESEARCH OBSERVATION`, niciodată `VALIDATED RISK` fără pipeline complet.

**Formă conceptuală**:

```
Typology X (candidate):  „post-1975 · bară · scări multiple"
Potential observations (research-only):
  - water infrastructure (raportat de AP-004, AP-009)
  - roof (raportat de AP-004)
  - documentation gaps (raportat de AP-004)
  - façade (neobservat încă)
Status: RESEARCH OBSERVATION
Not: Validated Risk
```

**Reguli invariante**:
1. `RESEARCH OBSERVATION` **nu** se transformă în `Validated Risk` fără metodologia standard.
2. Un profil de risc candidat **nu** produce niciodată o notificare către un utilizator PropManage.
3. Un profil de risc candidat **nu** intră în Health Engine, Risk Engine, Predictive Engine sau Digital Twin.
4. Rămâne document de research (în `/app/memory/audits/` dacă și când va exista).

---

## 11. Pilot Proposal — Research Validation Pilot

**Statut**: propunere conceptuală. Nu se demarează implementare fără o decizie explicită Fondator + Board Directive.

### 11.1 Scop
Pilotul are **strict** următoarele obiective de cercetare:
1. Compararea Reference Data (dacă ar exista) cu Official Documentation.
2. Compararea Reference + Official cu Observed Evidence (din interviuri și inspecții).
3. Identificarea diferențelor între surse.
4. Identificarea conflictelor între surse (§8).
5. Stabilirea gap-urilor de cercetare (câmpuri UNKNOWN sistematice).
6. Evaluarea conceptuală a nivelului de confidence per câmp per sursă.

**Ce NU face pilotul**:
- Nu implementează matching.
- Nu implementează scoring.
- Nu importă HartaBlocuri.
- Nu construiește Typology Engine.
- Nu construiește Matching Engine.
- Nu construiește UI.

### 11.2 Perimetru propus (5-10 clădiri din cohorta existentă)

Selecție candidat (subset AP-001…AP-010, ordonată logic pe factori de diversitate):

| # | Building | An | Apts | Rol în pilot |
|---|---|---|---|---|
| 1 | AP-002 (Mehedinți, Ilie) | 1976 | 20 | Familie candidat: comunist / bară / mic. |
| 2 | AP-004 (Negoiu 10) | 1975 | 40 | Familie candidat: comunist / bară / mediu. |
| 3 | AP-009 (Mehedinți 23) | 1976 | 104 | Familie candidat: comunist / bară / mare. |
| 4 | AP-010 (Mehedinți 17) | 1976 | 104 | Familie candidat: comunist / bară / mare (cross-check cu AP-009). |
| 5 | AP-003 (Negoiu 8D) | 2006 | 13 | Familie candidat: post-2000 / rezidențial / mic. |
| 6 | AP-008 (Predeal 34) | 2008 | 10+5 | Structură mixtă, unicat — testează limitele modelului. |
| 7 | AP-001 (Florești, Cluj) | 2019 | 16 | Post-2000 / rezidențial / mic. |
| 8 | AP-005 (Soporului 5) | 2018 | 130 | Post-2000 / rezidențial / mare. |
| 9 | AP-006 (West Conect) | 2019 | 286 | Post-2000 / rezidențial / foarte mare. |
| 10 | AP-007 (Kincsö Pál) | 2022 | 14 | Post-2000 / rezidențial / recent. |

### 11.3 Pentru fiecare clădire — checklist de pilot (research-only)

Pentru fiecare clădire selectată, cercetătorul completează manual, ca artefact markdown, în `/app/memory/audits/`:

1. **Building identity** — id, adresă, oraș.
2. **Reference typology (candidate)** — Familie propusă + Variant propus.
3. **Construction year** — value + precision (`exact` | `estimated` | `unknown`).
4. **Apartments** — count + source (Reference / Official / Reported / Observed).
5. **Stairs** — idem.
6. **Reference plan** — există candidat? sursă? disponibilitate? confidence?
7. **Typology match (conceptual)** — descriere textuală, fără scor numeric (§7).
8. **Evidence from president** — extras din interviul AP-* corespunzător (rezidat, nu re-interpretat).
9. **Verification status** — inexistent / parțial / complet, cu descriere.
10. **Confidence** — per câmp (low / medium / high / unknown).
11. **Mismatch / exceptions** — orice diferență între surse (§8).

**Format**: 1 fișier markdown per clădire, în `/app/memory/audits/PILOT_TYPOLOGY_AP-XXX.md` — **numai dacă și când pilotul este autorizat explicit**. Prezenta audit **nu autorizează** crearea acestor fișiere.

### 11.4 Ieșirea pilotului
Un singur raport de sinteză: `/app/memory/audits/PILOT_TYPOLOGY_SYNTHESIS_v1.0.md`. Fără cod. Fără UI. Fără DB.

Metrica de succes a pilotului = calitatea datelor de referință, nu construcția unui produs.

---

## 12. Data Gaps

Gap-uri observate în infrastructura de research și în cohorta existentă, relevante pentru orice viitor pilot Typology:

1. **Adresă precisă**: 9/10 interviuri sunt semi-anonymized. Fără adrese complete, un cross-check cu Reference Data este imposibil. **GAP MAJOR** (confirmat deja în `INTERVIEW_REGISTRY.md`).
2. **Vechime președinte**: 4/10 UNKNOWN. Nu blochează pilotul Typology, dar afectează pattern-uri de guvernanță asociate tipologiei.
3. **Platformă existentă**: 7/10 fără platformă declarată — nu afectează Typology, notat pentru completitudine.
4. **Localizare geografică**: 9/10 UNKNOWN. Blocant pentru corelații regionale de tipologie.
5. **Distribuție periodică**: 0 clădiri în intervalul 1980-2000 (GAP CONFIRMAT). Un pilot pe această fereastră necesită AP-011..AP-020.
6. **Reference Data**: 0% acoperire — nicio sursă externă nu a fost auditată la ora acestui document.
7. **Official Documentation**: 0% acoperire — nu s-a colectat sistematic.
8. **Reference Plans**: 0% acoperire.
9. **Reference 3D**: 0% acoperire.
10. **Cross-check floors/stairs/apts vs. surse independente**: neefectuat pentru nicio clădire.

---

## 13. Architecture Gaps

Gap-uri conceptuale (nu de implementare — orice implementare este **out of scope**):

1. **Formalizarea Source Provenance ≠ Verification Status**: model implicit în GI5P, dar nu formalizat ca vocabular canonic până la acest audit.
2. **Formalizarea Source Conflict Model**: absent înainte de acest audit. Introdus conceptual la §8.
3. **Reference Data ca categorie de nivel 1**: absent înainte de acest audit. Formalizat la §5.
4. **Building-level Typology mapping**: absent — nu există câmp `typology_candidate_ref` pe `buildings`. Rămâne absent și **nu se adaugă** în acest sprint.
5. **Reference Plan / Reference Apartment / Reference 3D**: absente. Rămân absente.
6. **Distincția Typology vs. Typology Family vs. Typology Variant**: absentă. Introdusă conceptual la §3-4.
7. **Pipeline research → typology**: absent formal. Reguli introduse la §9.

**Regulă**: aceste gap-uri se închid **conceptual** aici. Închiderea implementațională necesită Board Directive separată.

---

## 14. Decision Gate

Selecție: **A. NOT READY** pentru orice etapă implementațională (B, C, D).

Justificare:
- 0% acoperire Reference Data auditat.
- 0% acoperire Official Documentation colectată.
- Adresa precisă lipsește la 9/10 clădiri (gap critic).
- Pipeline metodologic încă nu are 3+ Validated Pattern Candidates specifice tipologiilor.
- Feature Freeze BD-RDPE este activ.

**Ce ESTE ready**:
- Vocabularul canonic (§3) — se poate cita în orice document viitor.
- Modelul conceptual (§4-§10) — se poate discuta cu experți externi (arhitect, cadastru, cercetător urban).
- Pilot Proposal (§11) — se poate autoriza separat dacă și când Fondatorul decide.

**Ce NU este ready**:
- Achiziție HartaBlocuri.
- Import planuri / DWG.
- Construcție Typology Engine.
- Matching Engine.
- Reference 3D.
- Data Acquisition automatizată.
- Orice API, UI sau DB legat de tipologie.

**Concluzia decision gate-ului**: rămânem la stadiul A. Reevaluare posibilă doar după completarea AP-011..AP-020 (target metodologic 15-20 Validated Interviews) și după autorizarea explicită a Pilot Proposal.

---

## 15. Recommended Next Research Step

**Un singur pas**: continuă cohorta de interviuri (AP-011 → AP-020) strict pe pipeline-ul existent (Observation → Emerging Pattern → Validated Pattern Candidate).

**Sub-pași metodologici opționali (doar dacă Fondatorul autorizează separat)**:
1. Adaugă în template-ul `INTERVIEW_TEMPLATE.md` un câmp opțional `building_reference_notes` unde cercetătorul consemnează observații arhitecturale factuale (formă, nr. scări, an aparent) — **fără interpretare tipologică**. *(Optional, nu este necesar pentru continuarea cohortei.)*
2. La momentul verificării adreselor semi-anonymized (dacă și când), se închide gap-ul #1 din §12 înainte de orice pilot.
3. Nu se demarează pilotul Typology până când există **cel puțin 3 Validated Pattern Candidates** independente specifice tipologiilor.

---

## 16. Backend Impact
**NO BACKEND CHANGE.**
Zero fișiere modificate în `/app/backend/**`. Zero rute noi. Zero modele Pydantic noi. Zero servicii noi. Zero migrări.

## 17. Frontend Impact
**NO FRONTEND CHANGE.**
Zero fișiere modificate în `/app/frontend/**`. Zero componente noi. Zero pagini noi. Zero rute noi. Zero style noi.

## 18. Database Impact
**NO DATABASE CHANGE.**
Zero colecții noi. Zero câmpuri adăugate. Zero indexe. Zero migrări. Zero seed data.

## 19. Blueprint Impact
**NO BLUEPRINT CHANGE.**
`/app/memory/PRODUCT_BLUEPRINT.md` rămâne intact. Vocabularul din §3 nu contrazice North Star, Strat 1-4, User Journeys, sau Principiile Fundamentale.

## 20. Roadmap Impact
**NO ROADMAP CHANGE.**
Zero modificări în `/app/memory/strategy/ROADMAP_V2.md`, `MASTER_ROADMAP_2026.md`, `AUTONOMOUS_EVOLUTION_ROADMAP.md`, `CONSTRUCTION_INTELLIGENCE_ROADMAP.md`. Building Typology nu se adaugă în roadmap.

## 21. Methodology Impact
**NO METHODOLOGY CHANGE.**
Pipeline-ul canonic rămâne:

```
Interview
   ↓
Observation
   ↓
Emerging Pattern
   ↓
Validated Pattern Candidate
   ↓
Research Report
   ↓
Product Blueprint
   ↓
Architecture Audit
   ↓
Roadmap
   ↓
Pilot
   ↓
Build
```

Building Typology Foundation Audit v1.0 se poziționează la **Architecture Audit** — un pas metodologic conceptual, fără Build.

---

## 22. Confirmări explicite (contractuale)

- **NO NEW USER FEATURES** — Confirmat.
- **NO BACKEND CHANGE** — Confirmat.
- **NO FRONTEND CHANGE** — Confirmat.
- **NO DATABASE CHANGE** — Confirmat.
- **NO API CHANGE** — Confirmat.
- **NO DIGITAL TWIN CHANGE** — Confirmat.
- **NO BLUEPRINT CHANGE** — Confirmat.
- **NO ROADMAP CHANGE** — Confirmat.
- **NO METHODOLOGY CHANGE** — Confirmat.

**Interdicții operaționale (contractuale)**:
- NU cumpără HartaBlocuri.
- NU importă HartaBlocuri.
- NU accesează automat surse externe.
- NU importă planuri (PDF, DWG, DXF, IFC).
- NU creează modele 3D.
- NU creează Typology Engine.
- NU creează Matching Engine.
- NU creează Building Health Engine.
- NU creează Risk Engine.
- NU modifică Digital Twin.
- NU modifică Product Blueprint.
- NU modifică Roadmap.
- NU modifică Marketplace.
- NU modifică Association Module.
- NU modifică Owner Journey.
- NU modifică President Journey.
- NU modifică metodologia de research.

---

## 23. Deliverable Log

Acest audit produce **un singur artefact**:
- `/app/memory/audits/BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` (acest document).

Nu se creează alte fișiere. Nu se modifică alte fișiere de research. Nu se atinge cod.

---

**End of BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.**
