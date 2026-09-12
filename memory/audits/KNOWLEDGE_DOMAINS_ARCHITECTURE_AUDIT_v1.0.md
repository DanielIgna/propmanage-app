# KNOWLEDGE DOMAINS — STRATEGIC ARCHITECTURE AUDIT

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Classification**: Strategic Architecture Audit — READ-ONLY
**Scope**: Analiza 3 domenii de cunoaștere (Core / Building Context / Regulatory Diagnostics) fără modificare de cod, DB, blueprint sau flowuri existente.
**Board Directive**: BD-RDPE (Research-Driven Product Evolution) — ACTIV

---

## 0. Executive Summary

Cele 3 domenii de cunoaștere pot coexista în infrastructura PropManage **fără conflict**, cu următoarele constatări:

1. **Domain A (PropManage Core)** este cel mai matur — 30+ colecții operaționale, model de provenance parțial deja implementat (`property_documents`, `property_assets`).
2. **Domain B (Building Context / HartaBlocuri)** este documentat conceptual în `BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md`, cu zero implementare în cod. Nu conflictuează cu Core.
3. **Domain C (Regulatory Diagnostics / DDT)** este COMPLET NOU — zero referință în codul existent. Poate atașa non-invaziv la `property_documents` cu extindere minimă a provenance-ului.

Verdict global: **Arhitectura curentă permite optionalitate strategică pentru toate 3 domenii**. Nu se recomandă convergență imediată. Se recomandă documentare separată în Knowledge Center + un singur bridge conceptual: **Property Identity ca ancoră comună**.

---

## 1. Current Architecture Understanding

### 1.1 PropManage Core — inventar factual

**Colecții MongoDB identificate direct în cod** (24 relevante):

| Categorie | Colecții | Rol |
|---|---|---|
| **Anchor** | `properties`, `users` | Identitate proprietate + owner |
| **Documents & Vault** | `property_documents` | Documentele proprietății cu provenance |
| **Property Intelligence** | `property_assets`, `property_maturity_history` | Echipamente/instalații + istoric maturitate |
| **Digital Twin** | `digital_twin_projects`, `_models`, `_plans`, `_pins`, `_comments`, `_qa_sessions` | Twin 3D + adnotări |
| **Health & Maintenance** | `health_history`, `health_pings`, `health_repair_runs`, `maintenance_logs`, `maintenance_tasks` | Sănătate + mentenanță |
| **Audit & Recommendations** | `audit_anomalies`, `audit_log`, `recommendations` | Audit tehnic + recomandări |
| **Building context (existing)** | `buildings`, `building_announcements` | Building operational (asociație), NU tipologic |
| **Twin Actions** | `twin_action_tokens`, `twin_actions_log`, `twin_conversations`, `twin_scheduled_actions` | Acțiuni pe Twin |
| **Specialists** | `specialist_entry_applications`, `specialist_followup_log`, `specialist_gaps` | Ecosystem profesional |

### 1.2 Provenance model **deja existent** (parțial)

**`property_documents`** are următoarele câmpuri (verificate direct în `/app/backend/routes/property_documents.py`):
```
source, provenance ("declared" | "documented"), verification_status ("verified" | "unverified"),
specialist_id, author_name, author_id, company, warranty_start, warranty_end,
version, prev_version_id, superseded, doc_date, uploaded_at,
related_request_id, related_asset_id, building_system, room
```

**`property_assets`** (verificat în `/app/backend/routes/property_intelligence.py`):
```
asset_type, installed_year, source, confidence, verification_status, maturity, slots, ok
```

**Concluzie critică**: PropManage are DEJA fundament pentru **provenance-first data model** în cele 2 colecții cheie (`property_documents`, `property_assets`). Aceasta este arhitectura pre-existentă care poate absorbi Domain C fără refactor major.

### 1.3 Documente conceptuale relevante deja emise

| Document | Rol | Status |
|---|---|---|
| `memory/PROPERTY_DNA.md` | Definiție Property DNA v2 (provenance-first) | ACTIVE (concept) |
| `memory/GI5P_PROPERTY_INTELLIGENCE.md` | Registry `PropertyAsset` + provenance actuarial + Digital Twin Maturity L0-L5 | ACTIVE (concept) |
| `memory/CONSTRUCTION_INTELLIGENCE_ROADMAP.md` | Roadmap construction intelligence | ACTIVE (concept) |
| `memory/PRODUCT_BLUEPRINT.md` | Blueprint produs | ACTIVE |
| `memory/audits/BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` | Vocabular Building Context (creat 2026-02-06) | ACTIVE (concept) |
| `memory/registries/FUNCTION_MAP.md` | Master Function Map (creat 2026-02-06) | ACTIVE |

---

## 2. PropManage Core Boundary

### 2.1 Definiție canonică (nu se modifică)
> „One property. One permanent technical identity. One evolving technical memory."

### 2.2 Perimetru închis (INTACT — nu se atinge)
- Property, Cartea Tehnică Digitală, Digital Twin, Documents, Plans, Installations, Equipment, Works, Guarantees, Specialists, Technical Audit, Risks, Recommendations, House Health, Property Value, Maintenance, History.

### 2.3 Concepte care aparțin Core-ului (chiar dacă unele lipsesc din implementare)
- **Property identity**: `properties._id` (canonical)
- **Property owner history**: `properties.owner_id` + `audit_log`
- **Property technical memory**: `property_documents` + `property_assets` + `digital_twin_*` + `maintenance_logs`
- **Property health / value**: `health_history` + `property_maturity_history`

### 2.4 Regulă boundary
Orice concept nou care se referă la o proprietate INDIVIDUALĂ VERIFICATĂ intră în Domain A.

---

## 3. Building Context Boundary

### 3.1 Definiție canonică (per Building Typology Foundation Audit v1.0)
Building Context = tipologie, geometrie de referință, dimensiuni, perioade de construcție, apartament de referință. **Reference data**, nu Verified.

### 3.2 Ce există deja în cod (utilizabil)
- Collection `buildings` cu câmpuri: `name`, `address`, `city`, `construction_year`, `floors`, `apartments_total`
- `property.building_id` (opțional) — link Property → Building deja disponibil

### 3.3 Ce NU există (per BTF-Audit v1.0)
- Typology / Family / Variant
- Reference Plan / Reference Apartment / Reference 3D
- HartaBlocuri as Reference Data Source
- Source Conflict Model

### 3.4 Regulă boundary
Orice concept care se referă la **o CLASĂ de clădiri** (nu o clădire individuală verificată) intră în Domain B.

Building Context **NU** înlocuiește Property identity. O proprietate individuală poate avea **cel mult un candidate Building Typology reference**, dar tipologia nu devine parte a Property Verified Truth fără verificare independentă.

### 3.5 Attachment point conceptual (fără implementare)
```
properties.building_id       ← EXISTS (relatie Property → Building operational)
buildings.typology_candidate ← NEW field (candidate, not verified — future work)
```

---

## 4. Regulatory Diagnostics Boundary

### 4.1 Definiție canonică (research-only)
Domain C = documentele tehnice legal-required generate în context de tranzacție (DDT / DPE / etc.). Regulatory Evidence.

### 4.2 Ce există deja în cod (relevant)
**ZERO** implementare directă. Termeni „diagnostic", „DPE", „asbestos", „regulatory", „compliance" nu apar în codul aplicației (verificat prin grep pe `/app/backend`).

### 4.3 Ce există conceptual utilizabil (fără redenumire)
- `property_documents.category` — poate include în viitor categorii precum `regulatory_diagnostic` (fără schema change — este string field)
- `property_documents.doc_date`, `warranty_start`, `warranty_end` — pot găzdui `issued_date` / `valid_from` / `valid_until` conceptual
- `property_documents.specialist_id` — deja permite atribuirea la profesionist autorizat
- `property_documents.verification_status` — deja are „verified" / „unverified"
- `property_documents.provenance` — „declared" vs „documented" — poate deveni „declared" / „documented" / **„regulatory"** (extindere valoare, nu schema)

### 4.4 Regulă boundary
Orice concept care se referă la **evidence tehnică generată de un profesionist autorizat pentru conformitate legală** intră în Domain C.

Domain C **NU** înlocuiește Property Technical Audit intern (care poate exista din inspecție proprie, nu autorizat legal).

### 4.5 Attachment point conceptual (fără implementare)
Domain C se atașează 100% la `property_documents` prin extensie de valori enumerate — **nu necesită schema change**:
```
property_documents.category      = "regulatory_diagnostic" (new string value)
property_documents.provenance    = "regulatory" (new enum value)
property_documents.doc_date      = date of diagnostic
property_documents.warranty_end  = valid_until (reused conceptual)
property_documents.specialist_id = licensed_professional
property_documents.verification_status = "verified" (post-transaction)
```

**Câmpuri lipsă pentru Domain C complet** (dar nu urgent):
- `regulatory_type` (DPE / asbestos / lead / termite / etc.)
- `jurisdiction` (FR / RO / EU)
- `regulation_reference` (link către text legal)
- `issued_by_org` (nu doar specialist_id individual)

Aceste 4 câmpuri **NU se adaugă acum**. Rămân candidate pentru extensie viitoare validată.

---

## 5. Evidence / Provenance Concept — Canonical Model

### 5.1 Model canonic (unificat conceptual pentru toate 3 domenii)

Structura completă a unei EVIDENCE unit:
```
value               ← ce afirmă
source              ← identifier al sursei (URL/document/persoană)
source_type         ← Reference | Official | Reported | Observed | Verified  (per BTF-Audit v1.0)
date                ← când s-a produs
valid_from          ← când începe validitatea (DDT-specific)
valid_until         ← când expiră (DDT-specific)
confidence          ← low | medium | high
verification_status ← verified | partial | unverified | failed | unknown
verified_by         ← ID + role
verification_method ← visual | measurement | document_review | expert_report | multi_source
related_document    ← ref la property_documents
related_equipment   ← ref la property_assets
related_property    ← ref la properties (Domain A anchor)
related_building    ← ref la buildings (Domain B optional)
```

### 5.2 Realitatea implementării curente

| Câmp canonic | Present în cod? | Colecție |
|---|---|---|
| value | ✓ implicit | `property_assets.installed_year`, `property_documents.filename` |
| source | ✓ | `property_documents.source`, `property_assets.source` |
| source_type | ✗ (nu formalizat) | — |
| date | ✓ | `property_documents.doc_date`, `uploaded_at` |
| valid_from | ~ (partial) | `property_documents.warranty_start` |
| valid_until | ~ (partial) | `property_documents.warranty_end` |
| confidence | ✓ | `property_assets.confidence` |
| verification_status | ✓ | `property_documents.verification_status`, `property_assets.verification_status` |
| verified_by | ~ (partial) | `property_documents.specialist_id` |
| verification_method | ✗ | — |
| related_document | ✓ | `property_documents._id` self |
| related_equipment | ✓ | `property_documents.related_asset_id` |
| related_property | ✓ | `property_documents.property_id`, `property_assets.property_id` |
| related_building | ✗ (nu formalizat pe documents) | doar `properties.building_id` |

**Coverage curent**: **10/14 câmpuri deja există** (parțial sau complet). **4 câmpuri lipsesc** conceptual (source_type, verification_method, related_building direct pe evidence, cu extensii minore).

**Verdict**: Arhitectura curentă suportă provenance-first model. Extensiile pentru Domain B și C sunt aditive, nu destructive.

---

## 6. Relationship Map

### 6.1 Relația conceptuală (ipoteza)

```
┌──────────────────────────────────────────────────────────────┐
│                    DOMAIN B                                   │
│   BUILDING CONTEXT (Reference Data · Typology · HartaBlocuri) │
│                    buildings                                  │
└──────────────────────────┬───────────────────────────────────┘
                           │  building_id (optional)
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    DOMAIN A                                   │
│              PROPMANAGE CORE                                  │
│   PROPERTY (individual, verified, permanent identity)         │
│   ├── property_documents (evidence + provenance)              │
│   ├── property_assets (equipment + confidence)                │
│   ├── digital_twin_* (twin data)                              │
│   ├── health_history                                          │
│   └── maintenance_logs                                        │
└──────────────────────────┬───────────────────────────────────┘
                           │  property_id + related_document
                           ↓
┌──────────────────────────────────────────────────────────────┐
│                    DOMAIN C                                   │
│   REGULATORY DIAGNOSTICS (DDT · DPE · legal evidence)        │
│   → attaches to property_documents.category=                  │
│     "regulatory_diagnostic"                                   │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Anchor unic: `properties._id`

Toate 3 domenii pot converge **doar** prin Property Identity. Aceasta este ancora ne-negociabilă.

### 6.3 Non-relații (interzise)

- Building Context **NU** validează Property. O proprietate poate avea tipologie candidat greșită.
- Regulatory Evidence **NU** înlocuiește Property Documents interne (audit propriu).
- Building Context **NU** generează Regulatory Evidence (sunt surse diferite).

---

## 7. Potential Future Convergence

**HYPOTHESIS (needs validation)**:

```
BUILDING CONTEXT (candidate typology)
        ↓
PROPERTY IDENTITY (anchor)
        ↓
REGULATORY EVIDENCE (tranzacție)
        ↓
PROPERTY DOCUMENT MEMORY (permanent)
        ↓
DIGITAL TWIN (verified state)
        ↓
LONG-TERM PROPERTY MEMORY (cross-owner)
```

### 7.1 Ce ar debloca convergența (evidence needed)

1. **Legal validation** — care diagnostics sunt legal-required în RO/FR (Domain C)
2. **Market validation** — DDT-driven owner engagement (interviu proprietari RO care au trecut prin tranzacție)
3. **Data flow validation** — HartaBlocuri data quality audit (Domain B)
4. **Data model validation** — provenance-first extension în producție (Domain A)
5. **Comparative analysis** — cost/benefit convergență vs. separare

### 7.2 Convergence gate

Convergența nu se autoriza înainte de a avea:
- ≥ 3 pattern-uri validate pe DDT-driven demand (metodologia BD-RDPE)
- Auditul unei surse HartaBlocuri reale (Domain B)
- Un pilot Regulatory Diagnostics în 1 mediu limitat (Domain C)

---

## 8. Current Conflicts

**Zero conflicte de rulare** identificate. Detaliat:

| Potențial conflict | Verificare | Verdict |
|---|---|---|
| Naming collision `Building` vs. `Building Instance` | `buildings` collection are semantic operational (asociație de proprietari). Building Context (Domain B) folosește același termen dar în sens tipologic. | ⚠️ **Naming ambiguity** — nu conflict tehnic, dar necesită clarificare vocabulară. Rezolvare: BTF-Audit deja separă `Building Instance` (Domain A operational) de `Typology` (Domain B). |
| `property_documents.category` overload | Category este string liber în cod, nu enum strict. | ✓ NO CONFLICT — permite extensie fără migrare |
| `property_documents.provenance` overload | Actualmente 2 valori (`declared`, `documented`). Extensie la `regulatory` = aditiv. | ✓ NO CONFLICT |
| Digital Twin vs. Reference 3D | Digital Twin = Verified state al proprietății individuale. Reference 3D = Building Typology geometric model. | ✓ Semantic separat deja în BTF-Audit §3.15 |
| Property Value vs. Regulatory transaction value | Valoare proprietate (Core) ≠ valoare tranzacție (Regulatory). | ✓ NO CONFLICT — sunt câmpuri distincte |

**Verdict**: nu există conflict tehnic runtime-blocker. Există **naming ambiguity minoră** pe termenul „Building" — deja documentată în BTF-Audit v1.0 §3.1-3.5.

---

## 9. Missing Capabilities

Capabilități care lipsesc pentru a putea onest suporta cele 3 domenii, în ordinea priorității de research (**NU implementare**):

### 9.1 P0 — Blocante pentru orice pilot cross-domain
1. **Formalized `source_type` enum** pe evidence (Reference / Official / Reported / Observed / Verified). Deja definit conceptual în BTF-Audit v1.0 §3.9-3.13.
2. **`valid_from`/`valid_until` semantics** clarificate — actualmente `warranty_start/end` este reused ambiguu.

### 9.2 P1 — Necesare pentru Domain C viitor
3. **`regulatory_type` enum** pentru clasificare DDT (DPE / asbestos / lead / gas / electric / termites / ...)
4. **`jurisdiction` field** pe evidence regulatorie (RO / FR / EU)
5. **`verification_method` field** — deja documentat în BTF-Audit §3.17

### 9.3 P2 — Nice-to-have pentru Domain B
6. **`typology_candidate_ref` field** pe `buildings` — deja documentat conceptual BTF-Audit §4.1
7. **Source Conflict Model** ca structură persistentă — deja documentat BTF-Audit §8

### 9.4 P3 — Governance (deferrat)
8. **Property Transfer History** — actualmente `properties.owner_id` este single-value. Un `ownership_history` array ar susține „property preserves technical memory across owners".
9. **Immutable evidence layer** — pentru documente regulatorii, o strategie append-only cu hash verification (blockchain nu e recomandat, dar `sha256` per document ar fi minim).

**IMPORTANT**: Aceste 9 capabilități **NU se implementează acum**. Sunt candidate documentate pentru cercetare separată sub BD-RDPE.

---

## 10. Recommended Knowledge Center Structure

Extensie **exclusiv documentară** (fără cod) în Knowledge Center pentru a organiza cele 3 domenii separat:

### 10.1 Categorie nouă: `Knowledge Domains`

```
memory/
├── knowledge_domains/                     ← NEW FOLDER
│   ├── DOMAIN_A_PROPMANAGE_CORE.md        ← Trage din PRODUCT_BLUEPRINT + PROPERTY_DNA
│   ├── DOMAIN_B_BUILDING_CONTEXT.md       ← Trimite la BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0
│   └── DOMAIN_C_REGULATORY_DIAGNOSTICS.md ← NEW research doc
```

### 10.2 Convenții obligatorii pentru fiecare fișier Domain

Fiecare document Domain trebuie să declare:
- **Boundary rule** (ce aparține domeniului)
- **Non-relations** (ce NU aparține)
- **Attachment points** conceptuale la alte domenii (fără schema change)
- **Convergence gate** (ce evidence deblochează integrarea)

### 10.3 Function Map integration

Master Function Map (`FUNCTION_MAP.md`) va conține un câmp nou `knowledge_domain` per funcție:
- FN-005 Property Documents → `A`
- FN-006 Digital Twin → `A`
- FN-008 Community Buildings → `A + B (operational)`
- FN-XXX (viitor) Regulatory Documents → `C`

**Zero implementare azi**. Doar convenția.

### 10.4 Vocabulary source of truth

`BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` §3 devine vocabular canonic. Toate documentele viitoare trebuie să folosească termenii de acolo (`Building Instance`, `Typology`, `Reference Data`, `Verified Data`, etc.).

---

## 11. Risks of Premature Integration

### 11.1 Risc 1 — Semantic collapse
Dacă Domain B (Reference) devine sursă primară pentru Property Verified Truth, PropManage își pierde thesis-ul „One verified technical identity". **CRITICAL**.

### 11.2 Risc 2 — Regulatory lock-in
Dacă Domain C devine prea rapid partea centrală a produsului, PropManage devine dependent de:
- Legislație locală (schimbări legale → schimbări forțate produs)
- Certificări profesionale (specialiști autorizați ca gatekeepers)
- Jurisdicții multiple simultan (FR ≠ RO ≠ IT ≠ etc.)

Actualmente PropManage funcționează în RO. Adăugarea Domain C ar necesita audit legal complet pentru fiecare țară țintă.

### 11.3 Risc 3 — Data flow reversal
Convergence-ul propus (`Building → Property → Regulatory → Twin`) sugerează un flow unidirectional. În realitate, Property Digital Twin (Domain A output) ar putea INFORMA Regulatory Evidence (ex: „DPE prezis: C" pe baza Twin data). Această relație inversă este premature de modelat.

### 11.4 Risc 4 — Feature freeze violation
Sub BD-RDPE, orice feature nou trebuie validat prin metodologia Research → Observation → Emerging Pattern → Validated. Domain C introdus prea rapid ca feature ar viola directiva.

### 11.5 Risc 5 — Cognitive overload pentru utilizatorul final
Dacă cei 3 domenii apar în UI simultan (Property Documents + Building Info + Regulatory Panel), utilizatorul este copleșit. Cost UX invizibil dar real.

### 11.6 Risc 6 — Data ownership ambiguity
- Cine deține un DPE? Emitent (specialist) sau proprietar?
- Ce se întâmplă la vânzare? Documentul rămâne cu proprietatea sau se transferă la nou owner?
- Cadru GDPR pentru transferul între owners?
Toate necesită validare legală înainte de implementare.

---

## 12. Recommended Next Research Steps

Priorități strict per Board Directive BD-RDPE:

### 12.1 Sprint imediat următor (Research-only, zero cod)
1. **Continuare cohortă AP-011..AP-020** — prioritar (per BD-RDPE și RES-RECONCILE-v1.0). Include o întrebare nouă: „ai trecut prin tranzacție imobiliară în ultimii 5 ani? ce documente ți-au fost cerute?"
2. **Rezolvă WTP gap** — 0/10 în cohorta actuală au evidence WTP explicit.

### 12.2 Sprint 2-3 după cohort ≥15
3. **Regulatory landscape audit — ROMÂNIA** — cadrul legal actual pentru transferul proprietăților în RO:
   - Cerințe legale pentru vânzare
   - Certificate energetice existente (există DPE-echivalent în RO? Da: „Certificat de Performanță Energetică")
   - Cadastru + carte funciară
   - Rol notar
   - Documente obligatorii vs. opționale
4. **HartaBlocuri source audit** — 1 pilot pe 5 clădiri (per BTF-Audit §11)
5. **DDT French deep-dive** — traducere completă + validare cu profesionist francez

### 12.3 Sprint după validare (≥1 an)
6. **Convergence proposal** — doar după toate research-urile de mai sus. Include:
   - Business case
   - Technical proposal
   - Legal review
   - GDPR review
   - Cost/benefit
   - Rollback plan

---

## 13. Deliverable Log

Acest audit produce **un singur artefact**:
- `/app/memory/audits/KNOWLEDGE_DOMAINS_ARCHITECTURE_AUDIT_v1.0.md` (acest document)

Nu se creează alte fișiere în acest sprint. Nu se modifică cod. Nu se modifică DB. Nu se atinge Blueprint, Roadmap, Digital Twin, sau flow-uri existente. Nu se creează Domain C skeleton acum (așteaptă cohortă research).

**Documente referite**:
- `memory/PROPERTY_DNA.md` — reference for provenance model
- `memory/GI5P_PROPERTY_INTELLIGENCE.md` — reference for Digital Twin Maturity
- `memory/audits/BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` — Domain B vocabular canonic
- `memory/audits/RESEARCH_RECONCILIATION_AP001_AP010_v1.0.md` — research state actual
- `memory/registries/FUNCTION_MAP.md` — Function inventory
- `memory/PRODUCT_BLUEPRINT.md` — Product vision (INTACT)

---

## 14. Final Confirmări (contractuale)

- **PropManage Core vision**: **INTACT**
- **Product Blueprint**: **NO CHANGE**
- **Database schema**: **NO CHANGE**
- **API contracts**: **NO CHANGE**
- **Frontend flows**: **NO CHANGE**
- **Existing modules names**: **NO RENAME**
- **Existing functionality**: **NO DELETION**
- **Cross-domain merge**: **NOT PERFORMED** — cele 3 domenii rămân separate până la validare
- **Convergence decision**: **NOT MADE**
- **Research methodology**: **NO CHANGE** (Interview → Observation → Emerging → Validated → Report)

Optionalitatea strategică este PRESERVED. Arhitectura poate evolua în oricare din cele 3 direcții separate SAU integrat, în funcție de evidence viitor.

**End of KNOWLEDGE_DOMAINS_ARCHITECTURE_AUDIT_v1.0.**
