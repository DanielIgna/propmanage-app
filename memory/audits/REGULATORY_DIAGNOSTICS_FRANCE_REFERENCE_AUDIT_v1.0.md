# REGULATORY DIAGNOSTICS FRANCE — REFERENCE AUDIT

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Classification**: Research-only · Domain C reference model
**Governance**: `STRATEGIC_KNOWLEDGE_DOMAINS_CHARTER_v1.0.md`
**Scope**: audit conceptual al modelului francez DDT/DPE ca REFERENCE model pentru Domain C. Zero specificație pentru PropManage. Zero implementare. Zero transfer automat la Romania.

**Evidence Integrity**: Faptele legislative franceze sunt ancorate prin `[SRC]` la surse oficiale verificate (service-public.gouv.fr, ecologie.gouv.fr, notaires.fr). Zero fabricație. Faptele fără sursă = `[UNKNOWN]`.

---

## 1. Executive Summary

Franța operează un sistem consolidat de diagnostice tehnice obligatorii la vânzarea/închirierea proprietăților rezidențiale, agregat într-un **Dossier de Diagnostic Technique (DDT)** anexat promisiunii de vânzare sau actului autentic [SRC: service-public.gouv.fr F10798].

**Valoarea reference-only pentru PropManage**:
- ✅ Model conceptual clar: **trigger legal → diagnostic → document → valabilitate → tranzacție**
- ✅ Existența unui **layer regulatoriu** independent de owner/administrator
- ✅ Profesioniști autorizați ca emitent (nu owner declaration)
- ✅ Valabilitate temporală explicită (10 ani DPE, 3 ani electricitate/gaz)

**Ce NU se transferă automat la Romania**:
- ❌ Lista specifică diagnostice
- ❌ Praguri temporale
- ❌ Termeni juridici
- ❌ Ecosystem profesional autorizat

**Verdict**: modelul francez oferă **framework conceptual valid**, dar aplicabilitatea în Romania trebuie validată separat prin `ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.md`.

---

## 2. Framework legal francez (Dossier de Diagnostic Technique)

**Sursa canonică**: `Service Public - fiche F10798` [SRC 1] + `Ministère de l'Écologie` [SRC 2] + `Chambre des Notaires` [SRC 3].

**Definiție DDT**: în cazul vânzării unei locuințe (casă sau apartament), vânzătorul trebuie să constituie un dossier care agregă diagnosticele obligatorii, anexat promisiunii de vânzare sau actului autentic [SRC 1, 2].

**Notă**: DDT este documentul-container. Conținutul variază după caracteristicile proprietății.

---

## 3. Diagnostice individuale — inventar factual verificat

Următoarele diagnostice sunt documentate în surse oficiale [SRC 1, 2, 3]. Pentru fiecare am identificat trigger, valabilitate, emitent.

### 3.1 DPE — Diagnostic de Performance Énergétique

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Orice vânzare de clădire închisă și acoperită (locuință) | [SRC 2] |
| Emitent | Diagnostician certificat | [SRC 2] |
| Valabilitate | **10 ani** | [SRC 2] |
| Statut juridic | **Opozabil** din 1 iulie 2021 (poate fi contestat legal) | [SRC 3 ecologie] |
| Producă | Etichetă energetică A→G + recomandări îmbunătățire | [SRC 2] |
| Obligatoriu la închiriere | DA | [SRC 2] |

**Notă**: DPE este cel mai puternic candidat de transferabilitate — existent și în legislația RO cu denumire diferită (Certificat de Performanță Energetică, Legea 372/2005) [SRC RO].

### 3.2 CREP — Constat de Risque d'Exposition au Plomb

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Locuință construită **înainte de 1 ianuarie 1949** | [SRC 1, 2] |
| Aplicabilitate PropManage RO | ⚠️ RELEVANT — multe blocuri comuniste postbelice construite după 1949, dar potențial relevant pentru case vechi & centre istorice | [Interpretare — necesită validare RO audit] |
| Producă | Rapport cu prezența și starea plumb în vopsele | [SRC 2] |

### 3.3 Amiante (Azbest)

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Permis de construire eliberat **înainte de 1 iulie 1997** | [SRC 1, 2] |
| Producă | État amiante: prezență/absență materiale conținând amiante, localizare, stare conservare | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ MEDIU — Azbest folosit în RO pre-1997 la placi ondulate, izolații industriale. Nu clar dacă există obligație tranzacție în RO. |

### 3.4 État de l'installation intérieure d'électricité

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Instalație electrică **mai veche de 15 ani** | [SRC 1, 2] |
| Valabilitate | **3 ani** (max față de promisiunea vânzării) | [SRC 3 notaires] |
| Producă | Raport siguranță instalație | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ ÎNALTĂ — legat de FN-005 (Property Documents) + FN-008 (Community Buildings) unde installations electrice comune sunt subiect frecvent |

### 3.5 État de l'installation intérieure de gaz naturel

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Instalație gaz **mai veche de 15 ani** | [SRC 1, 2] |
| Valabilitate | **3 ani** | [SRC 3 notaires] |
| Producă | Raport siguranță instalație gaz | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ ÎNALTĂ — instalații gaz individuale foarte comune în blocurile RO. Verificări ISCIR/DISTRIGAZ pot fi echivalent RO. |

### 3.6 État des Risques et Pollutions (ERP)

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Locuință în zonă cu risc natural, tehnologic, minier sau seismic | [SRC 1, 2] |
| Producă | Info riscuri naturale + tehnologice + poluție sol | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ ÎNALTĂ — RO are cadrul PUG + zone risc seismic (București, Vrancea). Poate exista echivalent oficial. |

### 3.7 Asainissement non collectif (Sanitation)

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Locuință cu sistem individual canalizare (nu conectat la rețea publică) | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ MEDIU — rural RO frecvent case cu fose septice. Urban RO — irrelevant. |

### 3.8 Termites

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Locuință în zonă declarată contaminată prin decret prefectoral | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ SCĂZUT — nu există sistematizare zonă-per-zonă în RO similar |

### 3.9 Audit énergétique

| Aspect | Valoare | Sursă |
|---|---|---|
| Trigger | Locuință clasificată **F sau G** la DPE, vândută (impus progresiv din 2023-2025 pentru clasele F/G) | [SRC 2] |
| Producă | Recomandări renovare + estimare cost | [SRC 2] |
| Aplicabilitate PropManage RO | ⚠️ ÎNALTĂ VIITOR — RO va aplica directive UE similare treptat |

---

## 4. Provenance model observat în cadrul francez

Modelul francez are următoarele proprietăți provenance implicite:

```
diagnostic_type    → catalog fix (DPE, amiante, plomb, ...)
issued_by          → diagnostician certificat cu identifiant unic
issued_at          → data emiterii
valid_from         → data emiterii
valid_until        → issued_at + validity_period (10 ani DPE, 3 ani electric/gaz)
jurisdiction       → FR (naționale) + variații regionale (termite, ERP)
regulation_ref     → article de lege + decret aplicare
document_binary    → PDF semnat digital (progresiv)
legal_status       → opposable (DPE post 2021) | informative
transaction_bound  → obligatoriu la promise + acte
```

**Consecință**: modelul francez validează empiric structura provenance canonică definită în `STRATEGIC_KNOWLEDGE_DOMAINS_CHARTER_v1.0.md` §4. Aceleași câmpuri sunt necesare.

---

## 5. Ce este transferabil conceptual la Romania

### 5.1 Concepte transferabile (framework)
1. ✅ **Existența unui diagnostic set legally-required** — RO are Certificat de Performanță Energetică (Legea 372/2005)
2. ✅ **Trigger legal la tranzacție** — RO cere Certificat energetic la notariat [SRC RO]
3. ✅ **Emitent certificat autorizat** — RO are auditori energetici atestați de Ministerul Dezvoltării [SRC RO]
4. ✅ **Valabilitate temporală explicită** — RO: 10 ani pentru certificat energetic (identic Franței)
5. ✅ **Provenance model** — aceeași structură fields
6. ✅ **Digital layer opportunity** — DPE opposable post 2021 arată direcția digitală obligatorie

### 5.2 Concepte NEtransferabile (fără audit local)
1. ❌ Lista completă de diagnostice — RO are alt catalog
2. ❌ Praguri temporale exacte (3 ani vs 15 ani) — RO poate avea alte reguli
3. ❌ Termeni juridici (DDT, CREP, ERP) — nu se traduc mecanic
4. ❌ Ecosystem profesional — RO are alt set de certificări
5. ❌ Termite / plumb specific triggers — irrelevant sau irelevant contextual RO
6. ❌ Ideea „un singur dossier" — RO folosește documente separate agregate de notar

---

## 6. Opportunities for PropManage

**Framework conceptual observabil**:

```
Legal Trigger (transaction/rental)
    ↓
Diagnostic Requirement Set (jurisdiction-specific)
    ↓
Certified Professional Assessment
    ↓
Document Emission (with validity)
    ↓
Transaction Attachment
    ↓
Long-term Property Memory (potential — Domain A bridge)
```

### 6.1 Oportunități PropManage (research hypotheses)

1. **H1** — Digitalizarea agregării documentelor pentru tranzacții RO poate fi valoroasă (owner adună azi ad-hoc)
2. **H2** — Alerta pre-expiry (10 ani înainte de expirare CPE) poate genera engagement
3. **H3** — Marketplace conectat cu auditori energetici certificați RO poate fi entry point
4. **H4** — Digital Twin poate reflecta rezultatele CPE (etichetă energetică ca dimensiune Twin)
5. **H5** — Compliance-readiness score la nivel proprietate poate fi valoare (proprietar știe „ești gata de vânzare?")

**IMPORTANT**: Toate aceste ipoteze necesită validare prin cohort research (BD-RDPE) înainte de a deveni features.

---

## 7. Regulatory Lock-in Risks

| # | Risc | Severity | Mitigare |
|---|---|---|---|
| RLI-1 | **Legislation change**: DPE reguli s-au schimbat în FR (opposabilitate 2021, F/G restrictions). RO poate schimba brusc. | HIGH | Provenance-first model + versionare legislație explicită |
| RLI-2 | **Jurisdictional expansion**: dacă PropManage crește la RO+FR+IT, fiecare are alt catalog. | HIGH | Domain C generic, dar `jurisdiction` field obligatoriu |
| RLI-3 | **Professional gatekeeping**: auditori certificați pot bloca digital penetration | MEDIUM | Colaborare, nu competiție |
| RLI-4 | **Digital signature standards** — EU eIDAS variază per țară | MEDIUM | Nu ne facem SSO/eIDAS azi |
| RLI-5 | **Data ownership post-transaction** — cine deține DPE-ul (owner nou vs vechi vs auditor)? | HIGH | Necesită research legal RO |

---

## 8. Comparație conceptuală FR ↔ RO (evidence-based)

| Aspect | Franța | Romania |
|---|---|---|
| Certificat energetic | DPE, 10 ani, opposable din 2021 [SRC FR] | CPE, 10 ani, obligatoriu tranzacție [SRC RO — Legea 372/2005] |
| Emitent | Diagnostician certifié | Auditor energetic atestat Ministerul Dezvoltării [SRC RO] |
| Trigger tranzacție | Anexă la promisă/acte | Prezentare original la autentificare notarială [SRC RO] |
| Set larg de diagnostice | DA (7+ diagnostice după caz) | ⚠️ NU este echivalent complet (verifică în Audit RO) |
| Amiante audit | Obligatoriu pre-1997 | [UNKNOWN — vezi Audit RO] |
| Plumb (CREP) | Obligatoriu pre-1949 | [UNKNOWN — vezi Audit RO] |
| Instalații electrice | Obligatoriu >15 ani | [UNKNOWN — verifică ANRE] |
| Instalații gaz | Obligatoriu >15 ani | [UNKNOWN — verifică ANRE/DISTRIGAZ] |
| Risc seismic | ERP obligatoriu în zone | [Necunoscut] — RO are zone seismice active |
| Dossier unified | DA (DDT container) | ⚠️ NU — documente separate agregate ad-hoc de notar/vânzător [SRC RO] |

**Insight cheie**: DPE ↔ CPE = echivalent aproape 1:1. Restul = gap semnificativ care necesită audit RO.

---

## 9. Research Hypotheses (pentru validation viitoare)

1. **H-FR-1** — Modelul „unified dossier" (DDT) este superior modelului RO de agregare ad-hoc?
2. **H-FR-2** — Alerte pre-expiry CPE ar produce engagement în RO?
3. **H-FR-3** — Colaborare cu auditori certificați RO poate fi entry point marketplace?
4. **H-FR-4** — Există „regulatory anxiety" la owners RO când tranzactionează?
5. **H-FR-5** — Digital Twin ar putea integra un compliance-readiness score?

Fiecare H necesită Interview → Observation → Emerging Pattern → Validated Pattern (BD-RDPE).

---

## 10. Evidence Gaps

- **G1** — Lista exactă documente obligatorii RO (vezi Audit RO)
- **G2** — Există echivalent RO pentru amiante audit? Electricitate audit? Gaz audit?
- **G3** — Cum se face verificarea autenticității CPE azi în RO (hârtie vs digital)?
- **G4** — Frecvența erorilor/fraudei CPE RO
- **G5** — Directive UE viitoare care vor obliga extra diagnostice RO în 2027-2030

---

## 11. Recommendation

**Pentru Founder**:

1. 🟢 **Preserve modelul francez ca reference** — nu ca specificație. Fișier acesta rămâne canonical în EKC.
2. 🟢 **Continuă cu `ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.md`** — imediat, prioritar.
3. 🟠 **Nu construi Domain C features până la validare RO completă** — chiar și CPE integration ar trebui să aștepte confirmarea nevoii owner (interview validation).
4. 🟢 **Explorează directive UE 2027-2030** — EPBD (Energy Performance Buildings Directive) va impune mai mult în toate țările UE. RO va urma.
5. 🔵 **Watchdog directive UE** — creează research task „RO Regulatory Roadmap 2030" pentru anticipare.

**Ce NU recomand**:
- ❌ Import mecanic al listei franceze de diagnostice în PropManage
- ❌ Marketing „PropManage FR-inspired regulatory platform" înainte de validare RO
- ❌ Refuz de opționalitate — dacă RO audit arată nevoie, mergem înainte; dacă nu, respectăm feature freeze

---

## 12. Convergence Gate (per Charter §5)

Convergence de la Domain C reference (FR model) la Domain C RO implementation este AUTORIZATĂ numai după:

- ✅ `ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.md` livrat
- ✅ Cross-check FR ↔ RO documentat (§8 aici este seed)
- ✅ ≥ 5 interviuri owner RO cu întrebare explicită „ai avut nevoie de CPE la vânzare/închiriere?"
- ✅ ≥ 3 Validated Pattern Candidates specifice pe „regulatory anxiety" RO
- ✅ Legal review RO complet

---

## 13. Final Verdict

Modelul francez DDT/DPE oferă **framework conceptual valoros** pentru Domain C, dar **NU** este specificație pentru PropManage. Este **reference model** care:

- ✅ **Validează empiric** provenance model (câmpuri deja documentate în Charter)
- ✅ **Confirmă** că există un market real pentru „regulatory technical documentation"
- ✅ **Oferă vocabular** conceptual (trigger, valabilitate, emitent, opozabil)
- ❌ **NU dictează** ce diagnostice trebuie în PropManage
- ❌ **NU garantează** aplicabilitate RO
- ❌ **NU justifică** un feature freeze exception

**Valoarea reference-only**: framework mental pentru evaluarea Audit RO.

---

## 14. Deliverable Log

Acest audit produce **un singur artefact**:
- `/app/memory/audits/REGULATORY_DIAGNOSTICS_FRANCE_REFERENCE_AUDIT_v1.0.md` (acest document)

Zero cod modificat. Zero DB. Zero transfer mecanic legislație. Zero merge cu Domain A/B.

**End of REGULATORY_DIAGNOSTICS_FRANCE_REFERENCE_AUDIT_v1.0.**

---

**Referințe canonice web verificate 2026-02-06**:
- [SRC 1] service-public.gouv.fr/particuliers/vosdroits/F10798 (DDT overview)
- [SRC 2] ecologie.gouv.fr/politiques-publiques/diagnostics-techniques-immobiliers (Ministère écologie)
- [SRC 3 ecologie] ecologie.gouv.fr/politiques-publiques/diagnostic-performance-energetique-dpe (DPE)
- [SRC 3 notaires] notaires.fr/fr/immobilier-fiscalite/diagnostics/les-diagnostics-techniques-immobiliers (Notaires validity)
- [SRC RO] notariatstoica.ro/certificatul-energetic-pentru-vanzare-imobil (CPE RO Legea 372/2005)
