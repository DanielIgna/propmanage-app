# FAZA 10C — DOCUMENT_PROPERTY_SUPPORT

**Status:** PASS / CLOSED  
**Tip:** Architecture / Evidence Pipeline / Contract Implementation  
**Verdict implementare:** PASS (2026-09-19)  
**Artifact Type:** DOCUMENT  
**OwnerDocument (SSOT):** acest fișier  
**Knowledge Center category:** Platform Audits (`memory/audits/`)

## Dependențe

| Strat | Referință | Note KC |
|---|---|---|
| Evidence Contract v1.0 | `backend/evidence_semantics.py` | Faza 7B — **nu există încă document KC dedicat** |
| 9C Claim Matching | `backend/claim_matching.py` | **nu a fost modificat în 10C**; **nu există încă document KC dedicat** |
| 10B Document↔Property Contract | contract de design (sesiune 10B) | **nu există încă document KC dedicat** |
| 8B Fact Extraction | `backend/document_fact_extraction.py` | **nu există încă document KC dedicat** |
| Trust Boundary | `backend/tests/test_document_vault_trust_boundary_iter233.py` | **nu există încă document KC dedicat** |
| Building Identity | `backend/building_identity.py` | 10C folosește doar `detect_unit_granularity`; **nu există încă document KC dedicat** |
| Document Vault (storage) | `memory/board/EXECUTION_ORDER_CX2_PROPERTY_DNA_DOCUMENT_VAULT.md` | `property_documents.property_id` = storage/ACL, nu identity |
| HartaBlocuri / Building | `memory/audits/HARTABLOCURI_INTEGRATION.md` | 10C nu scrie Building / HB |
| Truth Engine (vocabular guvernanță) | `memory/board/directives/BOARD_DIRECTIVE_161_TRUTH_ENGINE.md` | D161 ≠ Evidence Contract 7B; nu se unifică |

---

## A. Scop

10C este un **orchestrator pur** între:

```
Property snapshot
        → 9C claims
document extracted evidence
        → 9C MatchResult
        → DOCUMENT_PROPERTY_SUPPORT
```

Nu este matcher. Nu este Identity Gate. Nu este Review. Nu persistă.

Funcții:

- `rollup_document_property_support(property_snapshot, document_snapshot)`
- `rollup_property_document_support(property_snapshot, document_snapshots)`

---

## B. Ce este DOCUMENT_PROPERTY_SUPPORT

Enum exact:

- `INSUFFICIENT`
- `SUPPORTING`
- `AMBIGUOUS`
- `CONFLICTING`

**Explicit:**

- `SUPPORTING` ≠ `VERIFIED`
- `SUPPORTING` ≠ `content_verified`
- `SUPPORTING` ≠ `identity_verified`

Nu există winner / best_match / Trust Score / completeness în acest rollup.

---

## C. Storage vs Content

```
STORAGE RELATION
property_documents.property_id
        ≠
CONTENT EVIDENCE
extracted_facts
        ↓
9C Evidence / Claims
        ↓
9C MatchResult
        ↓
10C DOCUMENT_PROPERTY_SUPPORT
```

- `document.property_id` = storage / ACL relation
- `extracted_facts` = content evidence
- Niciunul nu este identity verification

---

## D. Identity Core

- `PROPERTY_ADDRESS`
- `PROPERTY_UNIT` atunci când este relevant

Supporting / discriminative (nu identity core):

- `PROPERTY_STAIR` / `PROPERTY_FLOOR` — supporting
- `PROPERTY_SURFACE` — supporting / discriminative

Nu există în taxonomia 9C și **nu se adaugă**:

- `PROPERTY_ROOMS`
- `PROPERTY_CF`

---

## E. Address compatibility

Acceptat pentru identity compatibility:

- `EXACT_MATCH`
- `NORMALIZED_MATCH`
- suffix-compatible `PARTIAL_MATCH` **doar** 8 ↔ 8D (nota 9C conține `suffix`)

Nu este acceptat ca `SUPPORTING`:

- street-only `PARTIAL_MATCH`
- locality-only
- `AMBIGUOUS`
- `NO_MATCH`
- `NOT_COMPARABLE`

`PARTIAL_MATCH` nu înseamnă automat compatibility.

---

## F. Unit rule

Granularitate **doar** din infrastructura existentă:

1. `PROPERTY_UNIT` materializat
2. `PROPERTY_STAIR` materializat
3. `properties.type` explicit `apartment` / `unit`
4. `detect_unit_granularity` existent

Dacă Property are unit discriminator: documentul trebuie să conțină unitate compatibilă (`EXACT_MATCH` / `NORMALIZED_MATCH`).

Dacă unitatea este necesară dar lipsește: `AMBIGUOUS`.

Dacă Property nu este granulară: address compatibility poate fi suficientă pentru `SUPPORTING`.

---

## G. Conflict rules

Identity-core conflict (`PROPERTY_ADDRESS` sau `PROPERTY_UNIT`) → `CONFLICTING`.

**Nu** produc identity `CONFLICTING`:

- surface
- rooms
- stair
- floor
- CF
- construction_year

---

## H. Building boundary

10C **NU**:

- modifică `building_id`
- modifică `building_link`
- produce `PROPERTY_BUILDING_RELATION`
- produce `identity_verified`
- decide G10 vs 8D vs PTR

Pilot IDs (doar fixture în teste, nu logică):

- G10 `6aaadd4aaebd8dfb9c8aaf59`
- Negoiu 8D `6a7724892e6529db42e95df1`
- PTR Building `6a9c6efff2ac8e128bd1d335`

**G10 ↔ 8D rămâne INDETERMINATE.**

`construction_year` este Building-only: exclus din DOCUMENT_PROPERTY_SUPPORT.

---

## I. Versioning

- V1 → propriile facts / matches / support
- V2 → propriile facts / matches / support
- V2 **nu** moștenește rezultatele V1
- 10C respectă snapshot-ul primit; nu implementează inheritance

---

## J. Multi-document aggregation

Se consideră doar documente curente: `deleted != true` și `superseded != true`.

Overall:

1. orice `CONFLICTING` → `CONFLICTING`
2. altfel orice `SUPPORTING` → `SUPPORTING`
3. altfel orice `AMBIGUOUS` → `AMBIGUOUS`
4. altfel → `INSUFFICIENT`

Fără winner. Documentele SUPPORTING rămân listate când există conflict. Câmp aditiv de agregare: `included_in_overall`.

---

## K. ACL

Documentul trebuie să aparțină Property-ului cerut (`document.property_id` == property id).

Mismatch:

- `eligible=false`
- `reason=property_id_mismatch`
- evidence omitted
- **nu** devine `NO_MATCH` / `NOT_COMPARABLE` / `CONFLICT`

Payload-ul ineligible poate include `document_id` / `property_id` pentru corelare. GET `/api/properties/{id}` ACL rămâne SECURITY BACKLOG (în afara 10C).

---

## L. Security

- fără LLM
- fără OCR / vision
- fără raw PDF în AI
- fără PII inutil (CNP, owner name, CF, deed identifiers, full text)
- fără public exposure implicit (fără UI, fără Public Passport)
- fără DB writes / events / cache persistent

---

## Implementation reference

| Fișier | Rol |
|---|---|
| `backend/document_property_support.py` | orchestrator pur 10C |
| `backend/tests/test_document_property_support_iter238.py` | teste dedicate |
| `backend/claim_matching.py` | 9C — **neschimbat** |
| `backend/evidence_semantics.py` | Evidence Contract — **neschimbat** |

**Confirmat:**

- 10C este pure orchestration peste 9C
- nu există persistence
- nu există endpoint
- nu există UI
- nu există al doilea matcher

---

## Test evidence (2026-09-19)

Dedicated: **42 passed** (`test_document_property_support_iter238.py`)  
Relevant regression: **197 passed** (9C, Evidence Contract, 8B, Trust Boundary, Identity, Create Guard, HartaBlocuri ledger/truth)  
Combined: **239 passed** (`--noconftest`)

Acoperire dedicată:

- exact address, normalized address
- 8 ↔ 8D, 8 vs 10
- apartment match / conflict
- surface, rooms, CF, construction year
- multi-unit ambiguity
- multi-document conflicts
- V1 / V2 independente
- ACL mismatch
- no building / `building_id` mutation
- no `identity_verified` / `content_verified`
- G10 / 8D / PTR isolation
- no PII / raw document content

---

## Architectural decisions

| ID | Decizie |
|---|---|
| AD-10C-01 | 10C nu creează un al doilea matcher. |
| AD-10C-02 | 9C rămâne singurul comparator. |
| AD-10C-03 | DOCUMENT_PROPERTY_SUPPORT este read-model / payload-only. |
| AD-10C-04 | `PROPERTY_ROOMS` nu se adaugă în 9C. |
| AD-10C-05 | `PROPERTY_CF` nu se inventează. |
| AD-10C-06 | `construction_year` este Building-only. |
| AD-10C-07 | `SUPPORTING` nu înseamnă `VERIFIED`. |
| AD-10C-08 | 10C nu produce Property→Building relation. |
| AD-10C-09 | G10 / 8D / PTR nu sunt rezolvate prin Document↔Property. |
| AD-10C-10 | Nu există winner selection între documente conflictuale. |

---

## Open / next phase (separate)

10C este **CLOSED**. Fazele următoare sunt **separate** și **neimplementate aici**:

- Document ↔ Building
- Operator Review
- Identity Gate

`SUPPORTING` **nu** produce automat `identity_verified`.

---

## Runtime boundary

Acest document este Knowledge Center only.

Nu este importat de `document_property_support.py`.  
Nu schimbă runtime-ul Document↔Property.
