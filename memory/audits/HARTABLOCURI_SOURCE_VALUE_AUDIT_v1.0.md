# HARTABLOCURI — SOURCE, DATA QUALITY & STRATEGIC VALUE AUDIT

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Classification**: Research-only · Domain B pilot source assessment
**Governance**: `STRATEGIC_KNOWLEDGE_DOMAINS_CHARTER_v1.0.md`
**Scope**: audit valoare strategică HartaBlocuri ca RESEARCH ASSET pentru Domain B (Building Context). Zero implementare. Zero DB change. Zero integrare produsă.

**Evidence Integrity**: Toate faptele sunt ancorate prin `[SRC]` la surse verificate (web_search 2026-02-06). Faptele fără sursă externă sunt marcate `[UNKNOWN]`.

---

## 1. Executive Summary

HartaBlocuri este un **proiect voluntar independent** dezvoltat de Teoalida, care agregă informații despre blocurile din România cu granularitate variabilă și acoperire ne-uniformă. **NU este o instituție a statului. NU garantează acuratețe 100%. Datele sunt majoritar estimative (80% cercetare proprie, 10% surse oficiale, 10% contribuții utilizatori)** [SRC: hartablocuri.ro/despre].

**Poziționare canonică**:
- ✅ HartaBlocuri = **Research Asset / Reference Data Source** (Domain B)
- ❌ HartaBlocuri ≠ Verified Truth (Domain A)
- ❌ HartaBlocuri ≠ Infrastructură critică PropManage

**Verdict final** (secțiunea 14): **DA — HartaBlocuri are valoare strategică pentru PropManage ca Building Context research asset**, dar cu 6 condiții de acceptare a datelor. NU se integrează runtime. NU se face dependent produsul de această sursă.

---

## 2. Source Description

**Nume**: HartaBlocuri.ro
**Autor**: Teoalida (proiect independent, non-comercial predominant, cu opțiune vânzare bază de date brută)
**URL**: `https://www.hartablocuri.ro/`
**Model**: Hartă interactivă gratuită + bază de date Excel plătită
**Cluj-Napoca coverage 2025**: ~90% blocuri detaliate [SRC: hartablocuri.ro/cluj]
**Județe cu date detaliate finalizate 2025**: include Cluj (per anunț autor) [SRC: hartablocuri.ro]

---

## 3. Data Inventory

Câmpuri identificate în structura HartaBlocuri [SRC: hartablocuri.ro/despre + /cluj]:

| Câmp | Granularitate | Prezent HartaBlocuri | Aplicabilitate PropManage |
|---|---|---|---|
| Adresa | Bloc | ✅ | Cross-check cu `properties.address` |
| Numărul blocului | Bloc | ✅ | Identificare |
| Numărul de etaje | Bloc | ✅ | Cross-check cu `buildings.floors` |
| Anul construcției | Bloc (interval estimat!) | ✅ | Cross-check cu `buildings.construction_year` |
| Număr apartamente total | Bloc | ✅ | Cross-check cu `buildings.apartments_total` |
| Număr apartamente pe tip de camere | Bloc | ✅ | NU există în PropManage azi |
| Risc seismic | Bloc | ✅ | NU există în PropManage azi (potențial Domain B input) |
| Relevee (planuri de referință) | Bloc | ✅ (parțial) | Aliniat cu concept BTF-Audit §3.6 „Reference Plan" |
| Coordinate GPS | Bloc | ✅ | NU există în PropManage azi (potențial) |
| Model bloc / tipologie | Bloc | ✅ (etichete generice) | Aliniat cu concept BTF-Audit §3.4 „Typology Family" |
| Coloristica hartă (interval construcție) | Vizual | ✅ (1963-1970, 1970-1976, etc.) | Doar vizualizare, nu date structurate |

**Granularitate**:
- ✅ **Clădire** — nivel primar (fiecare rând = un bloc)
- ✅ **Adresă** — asociată clădirii
- ⚠️ **Scară** — [UNKNOWN dacă e prezent structurat sau doar în relevee]
- ⚠️ **Apartament** — parțial (număr per tip, dar nu apartament individual identificabil)

---

## 4. Provenance Assessment

Distribuția surselor de origine a datelor HartaBlocuri [SRC: hartablocuri.ro/despre]:

| Sursă | Pondere | Confidence intrinsec |
|---|---|---|
| Cercetare proprie autor (Google Street View, imagini satelit) | 80% | **Medium-Low** (estimare vizuală) |
| Surse oficiale (liste reabilitare termică, expertize seismice) | 10% | **Medium-High** (documente oficiale, dar contextuale) |
| Contribuții utilizatori | 10% | **Low** (crowd-sourced, neverificat sistematic) |

**Anul construcției**: estimat pe intervale (ex: `1963-1970`, `1970-1976`), NU an exact. Estimarea se bazează pe modelul blocului și listele de reabilitare [SRC: hartablocuri.ro/despre].

**Consecință critică**: HartaBlocuri satisface definiția `Reference Data` din `BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` §3.9. **NU** satisface `Verified Data` (§3.13).

---

## 5. Data Quality Assessment

**Puncte forte**:
- Acoperire largă (~90% Cluj în 2025)
- Actualizare continuă (proiect activ, nu abandonat)
- Metodologie declarată transparent
- Include tipologii și geometrii de referință (relevee)
- Prețul de acces la baza Excel este accesibil pentru pilot (~180 € pentru Cluj menționat în conversație precedentă) [SRC: user context]

**Puncte slabe verificate**:
- **Autorul declară explicit**: „Nu este 100% corectă. Utilizatorii sunt încurajați să raporteze erori" [SRC: hartablocuri.ro/despre]
- **Nicio asociere cu instituții ale statului** [SRC: hartablocuri.ro/despre]
- **An construcție = interval estimat, nu valoare exactă**
- **Erori posibile** în adrese sau numărul de apartamente
- **Contribuții utilizatori** = neverificate sistematic
- **Licențierea datelor** = [UNKNOWN — necesită verificare directă cu autorul înainte de orice utilizare comercială]

---

## 6. Strategic Value

### 6.1 Valoare pentru PropManage (dacă e tratată corect ca Reference)

1. **Auto-completion candidate** pentru câmpurile lipsă la înregistrarea proprietății (an construcție, nr apartamente, tipologie candidat) — cu marcaj UNVERIFIED
2. **Cluster analysis** — identificarea proprietăților PropManage aflate în același bloc / aceeași tipologie pentru research
3. **Building typology seed** — populează Domain B vocabular canonic (BTF-Audit §3.3-3.5)
4. **Seismic risk contextual** — semnalizare non-blocantă
5. **Research validation** — cross-check cu Rachetă Interview Registry (AP-002/AP-004/AP-009/AP-010 sunt în Cluj și au anul declarat de președinte; comparație cu HartaBlocuri estimate = evidence pentru quality de estimation)

### 6.2 Valoare NU are

- **NU** este source of truth pentru Property Verified Data
- **NU** poate declanșa acțiuni automate (recomandări, alerte, updates la Digital Twin)
- **NU** poate elimina necesitatea input owner/specialist verificat
- **NU** poate fi expusă utilizatorului final ca „adevăr" fără disclaimer explicit

---

## 7. Potential Use Cases (5 identificate, NU features)

**IMPORTANT**: aceste use cases sunt exclusiv research hypotheses. Nu se convertesc în features fără validare.

### UC-1 · Property Onboarding Auto-Fill (research hypothesis)
La adăugarea unei proprietăți în PropManage, sistemul consultă HartaBlocuri pentru adresa introdusă și **sugerează** an construcție, tipologie, nr apartamente. Owner trebuie să **confirme sau infirme** manual. Câmpurile completate din HartaBlocuri poartă flag `source: hartablocuri`, `verification_status: unverified`.

### UC-2 · Cluster Discovery (research hypothesis)
Identifică ce proprietăți PropManage din același bloc sau aceeași tipologie de referință există, pentru pattern research (fără expunere UI la client).

### UC-3 · Typology Candidate Seeding (research hypothesis)
Populează registry Building Typology cu candidate din HartaBlocuri, ca sursă inițială pentru pilot conform BTF-Audit §11.

### UC-4 · Research Coverage Enrichment (research hypothesis)
La Research Coverage Matrix (`ResearchCoveragePage.jsx`), afișează contextul tipologiei pentru fiecare interviu AP-X, când există match în HartaBlocuri.

### UC-5 · Interview Address Verification (research hypothesis)
Pentru gap G2 din `RESEARCH_RECONCILIATION_AP001_AP010_v1.0.md` §J (9/10 interviuri cu adresă precisă UNKNOWN), HartaBlocuri poate ajuta la identificarea inversă a clădirii dacă știm coordonate approximative sau nume stradă.

**Toate aceste UC-uri necesită validare cost/benefit + evidence real înainte de a deveni features.**

---

## 8. Risks

| # | Risc | Severity | Mitigare recomandată |
|---|---|---|---|
| R1 | **Semantic collapse** — utilizatorul consideră datele HartaBlocuri ca „adevăr" | CRITICAL | Disclaimer explicit UI + provenance vizual (badge „Reference · Neverificat") |
| R2 | **Licensing risk** — utilizare comercială fără acord explicit autor | HIGH | Contact direct Teoalida înainte de orice pilot; verificare licență Excel base |
| R3 | **Source dependency** — dacă HartaBlocuri dispare/schimbă termeni, PropManage nu trebuie să se rupă | MEDIUM | Zero runtime dependency. Import batch only. Cache local. |
| R4 | **Stale data** — an construcție interval poate deveni invalid dacă bloc reabilitat/reconstruit | MEDIUM | Verificare cu owner obligatorie pentru trigger acțiune |
| R5 | **GDPR** — HartaBlocuri conține adrese, dar nu date personale (nu owners). Risc scăzut, dar contribuțiile utilizatori pot conține meta-date | LOW | Nu preluăm câmpuri „contributor notes" în PropManage |
| R6 | **Regulatory lock-in** — dacă în viitor apare o „hartă oficială" a statului, PropManage nu trebuie să fie captiv HartaBlocuri | LOW | Model provenance-first permite substituție source |
| R7 | **Confidence overestimation** — badge „Verificat vizual din Street View" NU este verificare tehnică | MEDIUM | Nicio dată HartaBlocuri nu poate ridica confidence-ul la `high` fără verificare independentă |
| R8 | **Coverage bias** — Cluj 90% dar restul țării mult mai puțin (10-40% posibil) | MEDIUM | Onboarding auto-fill nu poate promite acoperire; fallback graceful |

---

## 9. Domain B Boundary (per Charter)

**HartaBlocuri strict** aparține Domain B (Building Context). **NU** ajunge niciodată în Domain A (Property Truth) fără verificare independentă.

Attachment point conceptual (**fără implementare**):
```
properties.building_id (existent)
  → buildings (colecție existentă)
      → buildings.hartablocuri_ref_id      [FUTURE FIELD — nu se adaugă acum]
      → buildings.hartablocuri_typology    [FUTURE FIELD]
      → buildings.hartablocuri_year_range  [FUTURE FIELD]
      → buildings.hartablocuri_import_date [FUTURE FIELD]
      → buildings.hartablocuri_confidence  [FUTURE FIELD]
```

**Regulă**: aceste 5 câmpuri **NU se adaugă la schema DB azi**. Sunt candidate documentate în `BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` §4.

---

## 10. Relationship with Domain A

Domain A (`properties.*`) rămâne autoritativ. Domain B (`buildings.hartablocuri_*`) poate INFORMA, dar nu POATE ÎNLOCUI Domain A.

Flow conceptual autorizat (research-only):
```
HartaBlocuri (Reference)
    ↓
Building Context Attachment
    ↓ (owner/specialist verification obligatorie)
Property Attribute Candidate
    ↓ (approve/reject/edit explicit)
Property Verified Data (Domain A)
```

Flow NEAUTORIZAT:
```
HartaBlocuri → Property (direct write) ❌
HartaBlocuri → Digital Twin ❌
HartaBlocuri → House Health calculation input ❌
HartaBlocuri → Marketplace recommendation ❌
```

---

## 11. Research Hypotheses

Ipoteze care trebuie testate empiric (per BD-RDPE, prin Interview → Observation → Emerging Pattern):

- **H1**: Owners găsesc valoare în vederea contextului clădirii lor (tipologie, an, nr apartamente).
- **H2**: Owners acceptă că datele HartaBlocuri sunt estimative când li se explică sursa.
- **H3**: Auto-fill cu date HartaBlocuri **accelerează** rata de completare a profilului proprietății.
- **H4**: Pattern-uri de risc (seismic, an-related) pot fi observate cross-property în același bloc / tipologie.
- **H5**: Prețul de ~180 € pentru baza Cluj oferă ROI dacă ≥100 owners din Cluj folosesc PropManage și beneficiază de auto-fill.
- **H6**: Contribuțiile PropManage back to HartaBlocuri (crowd-sourced feedback) generează valoare bilaterală.

---

## 12. Evidence Gaps

Ce NU știm încă (necesar înainte de pilot autorizat):

- **G1** — Licența exactă a bazei de date Excel (uz personal vs. comercial)
- **G2** — Termeni de utilizare + atribuire obligatorie
- **G3** — Format exact al bazei Excel (schema, coloane, valori nule)
- **G4** — Frecvența actualizărilor
- **G5** — Ce se întâmplă la eroare raportată (cât durează correction cycle)
- **G6** — Există API? SDK? Sau doar Excel static?
- **G7** — Acoperire reală per județ (dincolo de Cluj)
- **G8** — Există date pentru case (nu doar blocuri)? [Verdict actual: pare exclusiv blocuri]
- **G9** — Există planuri (relevee) accesibile digital, sau doar imagini pe hartă?

---

## 13. Recommendation

**Recomandare Founder-facing**:

1. 🟢 **Contact direct Teoalida** — clarificare licență + termeni (5-10 min email). **Blocant pentru orice pilot**.
2. 🟡 **Achiziționare bază Cluj (~180 €)** — DOAR după G1-G3 clarificat. Buget mic pentru research asset.
3. 🟡 **Audit format bazei Excel** — 1-2h post-achiziție. Raportează schema exactă în EKC.
4. 🟢 **Cross-check cu cohort research** — verifică AP-002/AP-004/AP-009/AP-010 (toate Cluj, toate cu an declarat) contra HartaBlocuri estimate. Măsoară acuratețea estimation.
5. 🟠 **Pilot conceptual atașare la 5-10 clădiri PropManage** — per BTF-Audit §11. **Zero cod**. Doar manual mapping ca artefact markdown.
6. 🔵 **Rezultatul pilotului** determină dacă merită investiție cod.

**Ce NU recomand**:
- ❌ Automatizare import HartaBlocuri în DB
- ❌ UI feature „HartaBlocuri Explorer" în PropManage
- ❌ Runtime API call to HartaBlocuri
- ❌ Marketing „PropManage integrated cu HartaBlocuri" înainte de licență clarificată

---

## 14. Convergence Gate (per Charter §5)

Convergență HartaBlocuri → PropManage este AUTORIZATĂ numai după:

- ✅ Licența clarificată explicit cu autorul (G1-G2)
- ✅ Cross-check quality: min. 3/4 AP-uri Cluj cu match acurat pe an (interval)
- ✅ Pilot conceptual 5-10 clădiri completat cu raport
- ✅ Owner interview validează H1+H2 (min. 3 confirmări independente)
- ✅ Cost/benefit analysis documentat
- ✅ Founder Board Directive explicit

Până atunci: **HartaBlocuri rămâne Research Asset extern. NU produs.**

---

## 15. Final Verdict

**Q: „Is HartaBlocuri strategically valuable for PropManage as Building Context research?"**

**A**: **YES**, cu condiționări clare:

- **DA** ca Research Asset pentru validarea Domain B și accelerarea pilotului Typology (per BTF-Audit).
- **DA** ca sursă suplimentară de context clădire, sub disclaimer explicit „Reference · Neverificat".
- **DA** ca instrument de cross-check pentru cohort research (AP-uri Cluj).
- **NU** ca infrastructură produs.
- **NU** ca sursă a Digital Twin.
- **NU** ca dependency runtime.

**Valoarea reală**: 180 € pentru baza Cluj = cost minor pentru un experiment de cercetare care poate valida Domain B ca direcție strategică sau o poate infirma. **ROI-ul este research validation, nu feature delivery.**

---

## 16. Deliverable Log

Acest audit produce **un singur artefact**:
- `/app/memory/audits/HARTABLOCURI_SOURCE_VALUE_AUDIT_v1.0.md` (acest document)

Zero cod modificat. Zero DB. Zero UI. Zero integrare runtime. Zero contact făcut cu Teoalida (rămâne acțiune Founder).

**End of HARTABLOCURI_SOURCE_VALUE_AUDIT_v1.0.**
