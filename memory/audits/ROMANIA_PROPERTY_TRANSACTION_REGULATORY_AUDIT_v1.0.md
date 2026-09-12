# ROMANIA PROPERTY TRANSACTION — REGULATORY & TECHNICAL DOCUMENTATION AUDIT

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Classification**: Research-only · Domain C RO reality assessment
**Governance**: `STRATEGIC_KNOWLEDGE_DOMAINS_CHARTER_v1.0.md`
**Scope**: audit exhaustiv al documentației legal/reglementare/tehnice cerute la tranzacții imobiliare rezidențiale în Romania. Zero implementare. Zero produs. Comparație conceptuală cu FR (nu presupunere echivalență).

**Evidence Integrity**: Toate faptele sunt ancorate prin `[SRC]` la surse verificate (web_search 2026-02-06: legislatie.just.ro, ANRE, ISCIR, notariat, cadastru). Zero fabricație. Fără sursă = `[UNKNOWN]`.

---

## 1. Executive Summary

**Concluzie principală**: În Romania **există un ecosistem fragmentat** de cerințe legale, reglementare și tehnice pentru proprietăți rezidențiale, dar **NU există un „dossier unified"** echivalent DDT-ului francez. Cerințele sunt agregate **ad-hoc de notar** la tranzacție, iar owner-ul RO trebuie să le adune din surse multiple (primărie, ANRE, ISCIR, cadastru, auditor energetic, asociația de proprietari).

**Impact strategic pentru PropManage**:
- ✅ **Nevoia obiectivă există** — validat legal (Legea 372/2005 CPE, Legea 10/1995 Carte Tehnică, Ordin ANRE 179/2015 gaz)
- ✅ **Fragmentarea = oportunitate** de agregare digitală
- ✅ **Sancțiuni reale** = presiune legală pentru owner (5.000-20.000 lei carte tehnică; 1.500-15.000 lei ISCIR)
- ⚠️ **Zero validare owner-side** — nu știm încă dacă owners simt această fragmentare ca durere (necesită cohort interview validation)
- ❌ **NU justifică feature freeze exception** — respectăm BD-RDPE strict

**Verdict final** (§14): **DA — există nevoie obiectivă legală în RO**, potențial cel puțin la fel de puternică ca FR, dar cu structură foarte diferită. Validare owner-side rămâne obligatorie.

---

## 2. Cadrul general — cerințe legale la vânzare apartament RO

Sursele oficiale identificate [SRC: notariatstoica.ro + storia.ro + uniuneanotarilor.ro + rokman.ro + notari.pro]:

**Notarul public are obligația legală de a verifica existența și valabilitatea fiecărui act sub sancțiunea nulității tranzacției** [SRC 1].

---

## 3. Inventar documente cerute la tranzacție — clasificate per LEGALLY MANDATORY / CONDITIONAL / PRACTICAL / RECOMMENDED

### 3.1 LEGALLY MANDATORY (obligatoriu prin lege)

| # | Document | Bază legală | Emitent | Valabilitate | Sursă |
|---|---|---|---|---|---|
| L1 | Act proprietate (contract vânzare, moștenire, donație, titlu) | Codul Civil | Notar (istoric) / Judecătoresc | Permanentă | [SRC 2, 3] |
| L2 | Documentație cadastrală (încheiere intabulare, plan amplasament, releveu apartament, fișă imobil) | Legea 7/1996 | Expert cadastral autorizat | Actualizată | [SRC 3, 4, 5] |
| L3 | Extras Carte Funciară pentru autentificare | Legea 7/1996 | OCPI (solicitat de notar) | **10 zile lucrătoare** | [SRC 2, 5, 6] |
| L4 | Certificat atestare fiscală | Codul Fiscal | Primărie / DTL | **Luna emiterii** (unele surse: 30 zile) | [SRC 2, 4, 7] |
| L5 | **Certificat de Performanță Energetică (CPE)** | **Legea 372/2005** | **Auditor energetic atestat Ministerul Dezvoltării** | **10 ani** (excluzând renovări majore) | [SRC 1, 8, 9] |
| L6 | Acte identitate (originale) | Codul Civil | Instituție eliberare | Valabilitate ID | [SRC 2, 7, 8] |
| L7 | Adeverință asociație proprietari (achitare cote + fonduri reparații) | Legea 196/2018 | Asociația proprietari | Recentă | [SRC 4, 7, 8] |

**Consecință critică**: **CPE este ECHIVALENT DIRECT DPE francez** — 10 ani, emitent certificat, obligatoriu tranzacție. Vezi §7 comparație.

### 3.2 CONDITIONALLY MANDATORY (obligatoriu în anumite condiții)

| # | Document | Trigger | Bază legală | Sursă |
|---|---|---|---|---|
| C1 | Procură notarială | Vânzător absent | Codul Civil | [SRC 2, 8] |
| C2 | Certificat căsătorie/divorț | Regim matrimonial relevant | Codul Civil | [SRC 2, 7] |
| C3 | Certificat moștenitor | Vânzare bun moștenit | Codul Civil | [SRC 2] |
| C4 | Reconstituire Carte Tehnică | Bloc — dacă originalul lipsește | HG 273/1994 | [SRC RO carte tehnică 2, 3] |

### 3.3 PRACTICALLY REQUIRED (nu legal obligatoriu, dar cerut de partea terță — notar/bancă/cumpărător)

| # | Document | Cerut de | Sursă |
|---|---|---|---|
| P1 | Facturi utilități recente (electricitate, apă, gaz, întreținere) | Notar, cumpărător | [SRC 2, 7, 8] |
| P2 | Copie Carte Tehnică bloc (Capitole A-D) | Cumpărător info, bancă finanțare | [SRC RO carte tehnică 2, 3] |
| P3 | Documente ISCIR centrală termică (dacă există) | Cumpărător info | [SRC ISCIR 2, 3] |
| P4 | Fișa evidență ANRE gaz (verificare 2 ani + revizie 10 ani) | Cumpărător info, siguranță | [SRC ANRE 1, 4] |
| P5 | Expertiză tehnică bloc (seismic) | Bancă finanțare (frecvent) | [Interpretare — sursele confirmă existența dar nu obligativitate tranzacție] |

### 3.4 RECOMMENDED (nu obligatoriu, dar valoare adăugată)

| # | Document | Motivare | Sursă |
|---|---|---|---|
| R1 | Audit energetic aprofundat (dincolo de CPE) | Recomandare renovare | [SRC RO CPE 1] |
| R2 | Raport inspecție tehnică independentă | Cumpărător info | [Practică — necesită validare] |
| R3 | Istoric intervenții tehnice apartament | Cumpărător info | [Practică — necesită validare] |

### 3.5 NOT VERIFIED (cerințe incerte, necesar audit legal profund)

| # | Aspect | Status |
|---|---|---|
| NV1 | Există obligație audit **amiante** la vânzare RO? | [UNKNOWN — nu am găsit sursă legală explicită RO] |
| NV2 | Există obligație audit **plumb** vopsele RO? | [UNKNOWN — nu am găsit sursă legală explicită RO] |
| NV3 | Există **ERP-echivalent** (état des risques et pollutions) obligatoriu RO? | [UNKNOWN — poate fi în info urbanism, nu confirmat] |
| NV4 | Verificare **electrică ANRE** obligatorie la tranzacție (nu doar la vechime instalație)? | [UNKNOWN — găsit gaz obligatoriu, electric nesigur] |
| NV5 | Obligații locale (per primărie) suplimentare? | [UNKNOWN — variază per UAT] |

---

## 4. Cerințe legale specifice — deep dive

### 4.1 CPE (Certificat de Performanță Energetică) — Legea 372/2005

**Bază**: Legea nr. 372/2005 privind performanța energetică a clădirilor [SRC 1].

- **Obligativitate**: OBLIGATORIE pentru tranzacție + închiriere
- **Emitent**: auditor energetic atestat de **Ministerul Dezvoltării**
- **Valabilitate**: **10 ani** (excluzând renovări majore care modifică caracteristici energetice)
- **Format**: original prezentat la autentificare notarială
- **Sancțiune**: sub sancțiunea nulității tranzacției [SRC 1]

**Directive UE alineare**: EPBD (Energy Performance Buildings Directive) — RO va aplica cerințe mai stricte 2027-2030 (previzibil).

### 4.2 Cartea Tehnică a Construcției — Legea 10/1995 + HG 273/1994

**Bază**: Legea nr. 10/1995 privind calitatea în construcții + HG 273/1994 Anexa 6 [SRC 1, 2, 3, 4].

- **Aplicabilitate**: **obligatorie pentru orice bloc de apartamente** [SRC 1]
- **Structura obligatorie** (4 capitole):
  - **A**: Documentația privind proiectarea (autorizații, avize, proiect tehnic, referate)
  - **B**: Documentația privind execuția (jurnal șantier, procese-verbale lucrări ascunse, certificate calitate)
  - **C**: Documentația privind recepția (procese-verbale recepție finală)
  - **D**: Documentația privind exploatarea, întreținerea, repararea, urmărirea comportării în timp și postutilizarea
- **Responsabilitate**: **asociația proprietari** (Legea 196/2018) cu administrator operațional [SRC 2, 3]
- **Predare**: la înstrăinarea apartamentului, cartea tehnică trebuie predată noului proprietar [SRC 4, 3]
- **Sancțiuni**: **5.000-10.000 lei** pentru neîntocmire/neținere la zi; **până la 20.000 lei** pentru neprezentare la control ISC [SRC 2]

**Insight cheie pentru PropManage**: Cartea Tehnică Digitală = concept **existent legal** și obligatoriu, dar în practică frecvent lipsă (evidence AP-002/AP-004 pentru „lipsă carte tehnică"). **Domain A + Domain C se intersectează exact aici**.

### 4.3 Instalații gaz — Ordin ANRE 179/2015

**Bază**: Ordin ANRE 179/2015 [SRC 4].

- **Verificare tehnică**: **min. o dată la 2 ani** [SRC 1, 4]
- **Revizie tehnică**: **min. o dată la 10 ani** [SRC 1, 4]
- **Emitent**: operator economic autorizat ANRE (OE) [SRC 4, 5]
- **Documentare**: **Fișa de evidență** — păstrată pe durata întregii vieți a instalației [SRC 1, 6]
- **Owner responsibility**: instalația de la contor înainte (owner-side)
- **Association responsibility**: coloane comune gaz + lifturi
- **Cerințe tranzacție**: verifică cea mai recentă fișă de evidență ANRE [SRC 1, 3, 5]

### 4.4 Centrala termică — ISCIR (Legea 64/2008)

**Bază**: Legea 64/2008 privind ISCIR [SRC 7].

- **Verificare**: **anuală obligatorie** [SRC 2]
- **Aplicabilitate**: centralele care folosesc combustibil (gaz, motorină) — recipiente sub presiune
- **Excludere**: centralele pur electrice (nu necesită ISCIR, dar rămân sub ANRE electric)
- **Emitent**: tehnician autorizat ISCIR
- **Sancțiuni**: 1.500-5.000 lei (inspecție lipsă); până la 15.000 lei (operare fără autorizare) [SRC 2]

### 4.5 Ecosystem responsabilitate — apartament vs. asociație

| Componentă | Responsabil | Sursă |
|---|---|---|
| Instalație gaz de la contor înainte | Owner apartament | [SRC ANRE 1] |
| Coloane comune gaz | Asociație | [SRC ANRE 1, 2] |
| Instalații electrice apartament | Owner | [SRC ISCIR 2] |
| Coloane electrice comune | Asociație | [SRC ISCIR 2] |
| Lifturi | Asociație (ISCIR) | [SRC ISCIR 2] |
| Centrala termică (individuală) | Owner (ISCIR) | [SRC ISCIR 3] |
| Carte Tehnică bloc | Asociație (administrator) | [SRC Legea 10/1995] |

---

## 5. Comparație conceptuală FR ↔ RO — matrice completă

| Aspect | FRANȚA (DDT) | ROMANIA | Echivalență |
|---|---|---|---|
| Certificat energetic | DPE, 10 ani, opposable din 2021 | **CPE, 10 ani, Legea 372/2005** | ✅ **ECHIVALENT 1:1** |
| Audit amiante | Pre-1997 permis | ❌ Nu găsit obligativitate tranzacție | ⚠️ **NU ECHIVALENT** |
| Audit plumb | Pre-1949 | ❌ Nu găsit obligativitate tranzacție | ⚠️ **NU ECHIVALENT** |
| Verificare electricitate | >15 ani, 3 ani valabilitate | ⚠️ Nu explicit la tranzacție, dar ANRE electric activ | ⚠️ **PARȚIAL** |
| Verificare gaz | >15 ani, 3 ani valabilitate | ✅ **ANRE 179/2015: 2 ani verificare + 10 ani revizie** — obligatoriu owner | ⚠️ **DIFERIT ca frecvență** dar echivalent conceptual |
| ISCIR centrală termică | ⚠️ Nu regăsit FR pe această formă | ✅ **Anual obligatoriu RO** | ⚠️ RO **MAI STRICT** |
| ERP (riscuri naturale/tehnologice) | Obligatoriu zone declarate | [UNKNOWN — poate în urbanism] | ⚠️ **UNKNOWN** |
| Termite | Zone declarate | ❌ Nu găsit | ⚠️ **NU APLICABIL** |
| Carte tehnică construcție | ⚠️ Nu echivalent FR direct | ✅ **Legea 10/1995 obligatoriu**, cu 4 capitole structurate | ⚠️ RO **UNIC (nu FR)** |
| Documente cadastru | Cadastru francez | ✅ OCPI, Carte Funciară | ✅ **ECHIVALENT** |
| Model tranzacție notar | ⚠️ Anexă DDT | ✅ Notar verifică individual fiecare document | ⚠️ RO **fragmentat** |
| Dossier unified | ✅ DDT | ❌ NU există | ⚠️ **GAP RO** |
| Sancțiuni tranzacție | Diverse | ✅ Nulitate tranzacție (CPE); amenzi ISC (carte tehnică) | ⚠️ **DIFERIT** |
| Digital opposabilitate | ✅ DPE post 2021 | ⚠️ CPE format hârtie predominant | ⚠️ RO **behind** |

**Insight cheie**:
- RO are **elemente similare** (CPE, gaz verification, cartea tehnică)
- RO are **elemente unice** (ISCIR anual, Legea 10/1995 carte tehnică structurată)
- RO nu are **DDT unified dossier** — **oportunitate strategică**
- RO nu are **digital opposabilitate** clară — **oportunitate viitor**

---

## 6. Provenance model observat RO

Câmpurile necesare pentru un document RO regulatoriu:

```
document_type       → CPE | fisa_evidenta_ANRE | ISCIR_authorization | carte_tehnica_bloc | extras_cf | ...
issued_by           → auditor_energetic_id | OE_ANRE_id | tehnician_ISCIR_id | OCPI | ...
issued_at           → data emiterii
valid_from          → data emiterii
valid_until         → issued_at + validity_period (10y CPE, 2y ANRE verif, 10y ANRE revizie, 1y ISCIR, 10 zile lucrătoare CF)
jurisdiction        → RO
regulation_ref      → "Legea 372/2005" | "Ordin ANRE 179/2015" | "Legea 64/2008 ISCIR" | "Legea 10/1995"
document_binary     → PDF sau hârtie scanat
legal_status        → obligatoriu | recomandat | condiționat
transaction_bound   → obligatoriu la notariat | opțional
```

**Aliniere cu Domain A**: câmpurile **coincid** cu provenance model canonic (Charter §4). Zero conflict.

---

## 7. Strategic Value & Opportunity for PropManage

### 7.1 Nevoie obiectivă validată (evidence legal)

RO are cerințe reale, cu sancțiuni reale, cu ecosystem profesional autorizat. **Fragmentarea este durerea potențială** — owner trebuie să adune din 5+ surse.

### 7.2 PropManage attachment opportunities (research hypotheses)

| # | Hipoteză | Ancoraj Domain existent |
|---|---|---|
| H-RO-1 | Digitalizarea Cărții Tehnice Digitale = feature legal-driven (nu doar convenience) | ⚡ DOMAIN A ↔ DOMAIN C intersection |
| H-RO-2 | Alerta pre-expiry CPE (owner primeşte notificare cu 6 luni înainte de expirare) = engagement anual | ⚡ DOMAIN A extension |
| H-RO-3 | Marketplace conectat cu auditori energetici certificați RO = entry point verificat | ⚡ FN-009 (Marketplace) extension |
| H-RO-4 | Marketplace ISCIR + ANRE = engagement recurent (anual/bianual) | ⚡ FN-009 extension |
| H-RO-5 | „Compliance-readiness score" per proprietate = value proposition owner | ⚡ FN-012 (Enterprise Health) analog |
| H-RO-6 | Digital Twin poate integra CPE ca dimensiune (etichetă energetică live) | ⚡ FN-006 (Digital Twin) extension |
| H-RO-7 | Digital dossier PropManage = echivalent DDT (fill gap RO) | ⚡ NEW capability |

### 7.3 Confluența cu Cohort Research (validare parțială deja)

Din `RESEARCH_RECONCILIATION_AP001_AP010_v1.0.md`:
- **AP-004** (Negoiu 10): raportat „**lipsă carte tehnică**" → confirmă H-RO-1 durerea reală
- **AP-002** (Mehedinți, Ilie): raportat „**lipsa trasabilității lucrărilor**" → confirmă H-RO-2/H-RO-3
- **AP-003** (Negoiu 8D): raportat „**stingătoare — motivat de incident anterior**" → confirmă existența compliance-anxiety

**3/10 interviuri deja confirmă parțial existența durerii legale**. Evidence in-house pre-existent care aliniază perfect cu Domain C.

---

## 8. Regulatory Lock-in Risks (RO-specifice)

| # | Risc | Severity | Mitigare |
|---|---|---|---|
| RLI-RO-1 | Modificare frecventă legislație (CPE, ANRE ordonanțe) | HIGH | Provenance-first cu `regulation_ref` versionat |
| RLI-RO-2 | Digital eIDAS RO — semnătură electronică calificată | MEDIUM | Nu implementăm eIDAS azi |
| RLI-RO-3 | Directive UE 2027-2030 vor impune restricții suplimentare | HIGH | Watchdog EPBD |
| RLI-RO-4 | Profesioniști autorizați rezistă digitalizare | MEDIUM | Colaborare, nu competiție |
| RLI-RO-5 | Ecosystem regional (variații primării) | MEDIUM | Domain C generic + `municipality` field |
| RLI-RO-6 | Data ownership post-transaction | HIGH | Legal review obligatoriu înainte de feature |
| RLI-RO-7 | Sancțiuni ISC pentru neprezentare cartea tehnică — PropManage poate ajuta, nu poate elibera de răspundere | MEDIUM | Disclaimer explicit „PropManage = organizer, nu emitent" |

---

## 9. Analogia „regulatory anxiety" — este validă pentru RO?

**Hipoteză principală (H-RO-VALIDATED?)**: Există „regulatory anxiety" la owners RO când tranzacționează?

Evidence colectate:
- ✅ **AP-002** raportează procese în instanță cauzate de „**lipsa documentelor și transparenței**" — direct evidence anxiety
- ✅ **AP-004** raportează „lipsă carte tehnică" ca subiect cheie
- ⚠️ **7/10 profile-only** — anxiety-related evidence lipsă
- ⚠️ **0/10 explicit chestionați** despre experiența tranzacțională

**Verdict**: Evidence **parțial pozitiv** dar **insuficient pentru validare completă**. Necesar cohort AP-011+ cu întrebare explicită.

---

## 10. Evidence Gaps

Pentru validare completă Domain C RO, ne trebuie:

- **G-RO-1** — 5+ interviuri owner post-tranzacție (întrebare: „ce documente ți-au fost cerute? cât ai stat să le aduni?")
- **G-RO-2** — 3+ interviuri notar (întrebare: „care documente lipsesc frecvent la clienți? care e blocajul cel mai mare?")
- **G-RO-3** — 3+ interviuri auditori energetici RO (business model, willingness to partner)
- **G-RO-4** — 3+ interviuri administratori (asociație) despre cartea tehnică
- **G-RO-5** — Legal review confirmă:
  - Există obligație amiante RO? plumb? ERP-echivalent?
  - Cum se implementează EPBD 2027-2030 RO?
  - Există intenție unificare tip DDT?
- **G-RO-6** — Piata de auditori CPE RO (câți sunt, unde, prețuri, digital adoption)

---

## 11. Recommendation

**Pentru Founder**:

### Sprint imediat (Research-only, zero cod)
1. 🟢 **Include în chestionarul AP-011+ minim 4 întrebări noi**:
   - „Ai vândut/închiriat proprietate în ultimii 5 ani?"
   - „Ce documente au fost cerute?"
   - „Cât timp ai stat să aduni cartea tehnică / CPE / ANRE?"
   - „Ai plătit servicii pentru asta? Cât?"
2. 🟢 **Interview țintit 2-3 notari** — pentru validare durere real-side
3. 🟢 **Interview țintit 2-3 auditori CPE RO** — pentru partnership opportunity

### Sprint 2-3 (research + light experiments)
4. 🟠 **Legal deep dive** — verificare NV1-NV5 (amiante, plumb, ERP, electric obligatoriu tranzacție)
5. 🟠 **RO Regulatory Roadmap 2030** — EPBD directive, digital opposabilitate CPE, alte tendințe

### Sprint 4+ (după validare completă)
6. 🔵 **Strategic Convergence Audit** — se autoriza NUMAI după toate 3 audituri livrate + cohort ≥ 15 + 3+ Validated Patterns.

**Ce NU recomand**:
- ❌ Feature nou Domain C în PropManage azi
- ❌ Marketing „PropManage regulatory-ready" fără feature
- ❌ Import mecanic model FR sau altele
- ❌ Achiziționare integrare cu auditori CPE fără interview
- ❌ Refuz de opționalitate — dacă evidence arată nevoia, mergem înainte; dacă nu, respectăm freeze

---

## 12. Convergence Gate (per Charter §5)

**Domain C RO → PropManage integration** este AUTORIZATĂ numai după:

- ✅ `HARTABLOCURI_SOURCE_VALUE_AUDIT_v1.0.md` livrat ✓
- ✅ `REGULATORY_DIAGNOSTICS_FRANCE_REFERENCE_AUDIT_v1.0.md` livrat ✓
- ✅ `ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.md` livrat (acest document) ✓
- ⏳ Cohort AP-011..AP-020 cu întrebări extinse
- ⏳ ≥ 5 interviuri owner post-tranzacție validate
- ⏳ ≥ 2 interviuri notari
- ⏳ Legal review complet (G-RO-5)
- ⏳ Board Directive explicit convergență
- ⏳ Strategic Convergence Audit v1.0

**Ordinea recomandată** (post-audit): sprint dedicat cohort AP-011..AP-020 cu focus tranzacțional.

---

## 13. Confirmări contractuale

- **PropManage Core**: **INTACT**
- **Product Blueprint**: **NO CHANGE**
- **Database schema**: **NO CHANGE**
- **API contracts**: **NO CHANGE**
- **Frontend flows**: **NO CHANGE**
- **Digital Twin**: **NO CHANGE**
- **HartaBlocuri integration**: **NOT PERFORMED**
- **DDT/DPE feature import**: **NOT PERFORMED**
- **Domain C module**: **NOT CREATED**
- **Feature Freeze BD-RDPE**: **RESPECTAT**

Optionalitatea strategică: **PRESERVED**.

---

## 14. Final Verdict

**Q: „Există în Romania o nevoie tehnică/reglementară similară cu modelul francez DDT/DPE?"**

**A**: **DA — parțial, dar cu structură fragmentată**.

Evidence:
- ✅ **CPE = echivalent DPE quasi-perfect** (Legea 372/2005)
- ✅ **ANRE gaz + ISCIR centrală = echivalente parțiale** (mai stricte pe ISCIR anual)
- ✅ **Cartea Tehnică Legea 10/1995 = UNIC RO** — nu are echivalent FR direct
- ✅ **Sancțiuni reale** (5.000-20.000 lei) = presiune legală obiectivă
- ⚠️ **NU există „dossier unified"** — GAP semnificativ = oportunitate strategică
- ⚠️ **Owner-side pain** = parțial validat prin AP-002/AP-004 (3/10 cohort), dar necesită validare explicită AP-011+

**Ideea de azi (Domain C driven by regulatory need)** este **potențial validată legal**, dar **necesită validare owner-side**.

**Digital Twin actual (Domain A)** **nu este înlocuit**. Poate deveni **infrastructura tehnică peste care Domain C se așează**, dacă și când validare completă permite convergență.

**Recomandare finală**: Sprint imediat = cohort AP-011+ cu focus tranzacțional. Rezultatele acelui sprint determină dacă Domain C merită înainte de features sau doar research continuu.

---

## 15. Deliverable Log

Acest audit produce **un singur artefact**:
- `/app/memory/audits/ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.md` (acest document)

Zero cod modificat. Zero DB. Zero blueprint. Zero convergence declared.

Cele 3 audituri (`HARTABLOCURI_...`, `REGULATORY_DIAGNOSTICS_FRANCE_...`, `ROMANIA_PROPERTY_TRANSACTION_...`) sunt acum LIVRATE. Al 4-lea (`STRATEGIC_CONVERGENCE_AUDIT_v1.0.md`) rămâne blocat până la finalizarea cohort research extension.

**End of ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.**

---

**Referințe canonice web verificate 2026-02-06**:
- [SRC 1] notariatstoica.ro/certificatul-energetic-pentru-vanzare-imobil (CPE Legea 372/2005)
- [SRC 2] uniuneanotarilor.ro (Uniunea Națională Notari Publici RO)
- [SRC 3] e-cadastru.ro (Acte cadastru)
- [SRC 4] notari.pro/contract/contract-de-vanzare-cumparare
- [SRC 5] rokman.ro (Ghid acte vânzare-cumpărare)
- [SRC 6] storia.ro/blog/ghid-imobiliar/acte-vanzare-apartament-taxe-notariale
- [SRC 7] imobox.ro (Documente 2025)
- [SRC 8] doctorulzilei.ro (Certificat energetic obligatoriu)
- [SRC 9] ceacteitrebuie.ro (Certificat energetic)
- [SRC ANRE 1] brig.ro/blog/obligatii-legale-instalatie-gaze-romania-2026
- [SRC ANRE 2] economisi.ro/energie/solutii-casa/iscir
- [SRC ANRE 3] smart21.ro (ISCIR control centrală)
- [SRC ANRE 4] engie.ro (Ordinul ANRE 179/2015)
- [SRC ANRE 5] delgaz.ro (Întrebări frecvente)
- [SRC ANRE 6] legislatie.just.ro (Ordinul ANRE 179/2015)
- [SRC ISCIR 7] iscir.ro (Legea 64/2008)
- [SRC RO carte tehnică 1] legislatie.just.ro (Legea 10/1995)
- [SRC RO carte tehnică 2] condoflow.ro (Carte tehnică 2026 obligații amenzi)
- [SRC RO carte tehnică 3] kapal.ro (Ce este cartea tehnică)
- [SRC RO carte tehnică 4] edirect.e-guvernare.ro (Legea 10/1995 text)
