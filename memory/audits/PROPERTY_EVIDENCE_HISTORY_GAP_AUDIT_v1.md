# PROPERTY EVIDENCE & HISTORY GAP AUDIT v1.0

**Mode:** READ-ONLY. No code, schema, entities, Memory/Evidence engines, refactor, rename, merge, branch, commit, deploy.  
**Date:** 2026-09-23  
**Given:** D10, D10.1. Stops at OBSERVE → EVIDENCE → ANALYZE → IMPACT → recommended next step.

**No implementation performed.**  
Demo vs real cash (D9.7/D9.8) does not change this evidence graph: jobs still persist as `requests`.

---

# A. EXECUTIVE FINDING

- **Cartea Casei credibilă din mecanismele existente: PARTIAL.**  
- **Property identity:** SUPPORTED (`db.properties`, required `property_id` on `POST /api/requests`).  
- **That work was opened / assigned / started / marked complete / client-confirmed:** SUPPORTED as **status + `activity_events` on the request**.  
- **What the specialist actually did (notes, after photos, materials, location):** **NOT SUPPORTED** as a first-class write. `POST /requests/{id}/complete` sets only `status=completed` + `completed_at` (`requests.py`).  
- **Photos:** PARTIAL — `RequestIn.photos` at **create** only. No specialist photo attach on complete.  
- **Documents:** PARTIAL — Vault `related_request_id` **IMPLEMENTED** (`property_documents.py` Form) but **not AUTOMATED** from complete/confirm.  
- **5-year retrieval of the request row:** SUPPORTED if Mongo retention holds (UNKNOWN ops policy).  
- **Property timeline as Cartea Casei:** PARTIAL — `GET /properties/{id}/timeline` composes requests + vault; **does not read `activity_events`**. Request-level `GET /requests/{id}/timeline` **does** read `activity_events`.  
- **Recommendation → later job:** PARTIAL — only if published via `POST .../recommendations/{id}/publish-to-marketplace` (`house_health_source.recommendation_id` ↔ `marketplace_request_id`). Manual 2027 request **NOT CONNECTED** to a 2026 rec.  
- **HH rec states:** `active | done | dismissed` only — **not** planned / in_progress / evidenced / verified. `done` is a PATCH, not wired to `/confirm`.  
- **Health-score risk: EVIDENCED.** `value_loop.enrich_on_closure` increments `utilities_health` / `health_score` on `/confirm` **without** requiring photos, vault, or specialist notes. Recommendation or request **alone** can raise the score after client confirm.  
- **`completed` ≠ verified:** EVIDENCED. Complete = specialist self-asserted; confirm = client self-asserted; vault `verification_status` starts `unverified` except admin/operator upload.  
- **2D Twin location of a pipe repair:** NOT CONNECTED. 3D pins exist on DT project, not on request.  
- **Future owner dossier:** PARTIAL — can list jobs and uploaded docs; cannot prove work quality or unused recs vs later jobs unless HH-publish path was used.  
- **OAER-style provenance:** PARTIAL capability (vault provenance declared/documented; events; specialist_id on request). Not a legal archive.

**Poate PropManage astăzi să construiască o Cartea Casei credibilă?**  
**PARTIAL** — destule primitive pentru un **read model** și pentru un **prim slice Work Update**. Nu destule pentru un dosar verificat.

---

# B. CURRENT PROPERTY EVIDENCE GRAPH

```
USER (client)
  IMPLEMENTED → PROPERTY (owner_id)     properties.py POST /api/properties

PROPERTY
  IMPLEMENTED → REQUEST                  RequestIn.property_id required
       IMPLEMENTED → specialist_id       POST /requests/{id}/accept
       IMPLEMENTED → status machine      start / complete / confirm
       IMPLEMENTED → photos[]            only at CREATE
       IMPLEMENTED → activity_events     event_bus.emit (request_id, property_id derived)
       IMPLEMENTED → warranties          value_loop on confirm
       IMPLEMENTED → health_* / PVI      value_loop on confirm (no evidence gate)
       NOT CONNECTED → vault auto
       NOT CONNECTED → 2D/3D geometry
       NOT CONNECTED → DT pin / room

PROPERTY
  IMPLEMENTED → property_documents       property_id + optional related_request_id
  IMPLEMENTED → twins (2D)               property_id
  PARTIAL → digital_twin_projects        property_id optional
       IMPLEMENTED → hh_evaluations      twin_project_id  (NOT property_id)
       IMPLEMENTED → hh_recommendations  twin_project_id
            PARTIAL → REQUEST            publish-to-marketplace only

PROPERTY
  IMPLEMENTED → maintenance_tasks
       PARTIAL → REQUEST                 1-click create

USER
  NOT CONNECTED → interior_design_leads → PROPERTY

GET /properties/{id}/timeline     COMPOSE: requests + vault   (not activity_events)
GET /requests/{id}/timeline       READ: activity_events
Passport / PTR                    COMPOSE on read
```

---

# C. EVIDENCE LINEAGE MATRIX

| Evidence | Source | Property link | Intervention link | History | Verification | Status |
|---|---|---|---|---|---|---|
| Request title/desc/category | client create | **required** | is the intervention | timeline compose + row | self-asserted | IMPLEMENTED |
| Request.photos | client at create | via request | on request | not vault; not after-work | none | PARTIAL |
| Specialist “what I did” | — | — | — | — | — | **NOT CONNECTED** |
| `/complete` | specialist | via request | status | activity `work.completed` | self-asserted | IMPLEMENTED |
| `/confirm` | client | via request | status | activity + warranty + health | self-asserted | IMPLEMENTED |
| Vault file | owner/spec/admin upload | **required** | optional `related_request_id` | timeline if uploaded | unverified unless admin/operator | IMPLEMENTED · not AUTOMATED |
| HH evaluation | specialist | **INDIRECT** twin | evaluation_id | HH UI | draft/approved | IMPLEMENTED |
| HH recommendation | specialist | via twin | `marketplace_request_id` if published | rec.status | not verified | IMPLEMENTED · PARTIAL link |
| 2D twin rooms/photos | client/operator | **required** | none to request | twin doc | operator approve | IMPLEMENTED |
| 3D model / pins | DT project | optional | pin ≠ request | DT | model verification enum | PARTIAL |
| `twin.enriched` event | confirm | property_id | request_id | activity_events only | not Twin write | EVIDENCED · not geometry |
| Warranty auto | confirm | property_id | request_id | warranties + PVI | not reviewed | IMPLEMENTED |
| Review | `POST .../review` | via request | request | reviews | client opinion | IMPLEMENTED |
| Offer | Model B | via request | request | unused env | — | IMPLEMENTED island |
| Lead interior | form | **absent** | none | admin list | — | NOT CONNECTED |
| Claim matching | address/unit claims | property snapshot | not work | — | identity claims | IMPLEMENTED (not job evidence) |

---

# D. WORK UPDATE GAP

**Poate un specialist să înregistreze astăzi ce a făcut și să rămână permanent legat de Property?**  
**PARTIAL.**

**What exists**

1. Status: `POST /api/requests/{id}/start` → `in_progress`; `POST .../complete` → `completed` (`requests.py`). Auth: `specialist_id` match.  
2. Events: `log_event` → `event_bus.emit` → `activity_events` with `request_id`; `property_id` **derived** from request if omitted (`event_bus.py`).  
3. Persistence of the **job**: `requests` document with `property_id` forever.  
4. Optional Vault: specialist/admin upload can set `related_request_id`, `provenance=documented` (`property_documents.py`).  
5. Request timeline: client + assigned specialist + admin + twin-validating operator (`_can_view_request_events`).

**Where it is lost**

- **No work-update body** on complete (no notes, materials, after-photos, room, system).  
- **No PATCH** on `requests` for specialist progress photos.  
- **Complete is not evidence** — only a status.  
- **Property timeline does not list** `work.completed` from `activity_events`.  
- **Confirm raises health** without those artifacts (`value_loop.enrich_on_closure`).

**5 years:** the request row is recoverable **if** stored. The **content of the work** is only title/description from  the **client’s original post**, plus any vault files someone later attached.

**Twin / exact location:** NOT CONNECTED from the job.  
**Finished?** Status `completed`/`confirmed` = **declared**, not evidenced.

---

# E. RECOMMENDATION → COMPLETION GAP

| Desired | Exists? | What exists |
|---|---|---|
| RECOMMENDED | PARTIAL | HH `priority` in `urgent\|recommended\|monitor`; rec `status=active` |
| PLANNED | **NO** explicit | publish creates `request.status=open` — not named planned |
| IN_PROGRESS | PARTIAL | `request.status=in_progress` — **not** written back to rec |
| COMPLETED | PARTIAL | `request` completed/confirmed; rec `status=done` **manual PATCH** |
| EVIDENCED | **NO** as rec/request state | vault optional, unlinked by default |
| VERIFIED | **NO** on this chain | vault `verified` only admin/operator upload; VE listing gates; operator 2D twin |

**2026 rec → 2027 job:** lineage **IMPLEMENTED only** on HH publish (`recommendation_id` / `marketplace_request_id`). Breaks if: new request created in `/api/requests`; rec marked `done` without a request; HH eval on unlinked twin; category mismatch.

**Health:** confirm can look “better” without the rec being `done` and without evidence — **recommendation ≠ work**, but **confirm ≈ healthier** in code.

---

# F. DIGITAL TWIN GAP

| | 2D `twins` | 3D `digital_twin_projects` |
|---|---|---|
| PROPERTY | SUPPORTED (`property_id`) | PARTIAL (optional; operator required) |
| SYSTEM | PARTIAL (`assets[]` / rooms) | PARTIAL (layers if in file) |
| COMPONENT | PARTIAL | PARTIAL (pins, not MEP catalog) |
| LOCATION | PARTIAL (room) | PARTIAL (pins) |
| INTERVENTION | NOT CONNECTED to request | PARTIAL (concept→request) |
| EVIDENCE | operator photos/approve | model file + validation |
| HISTORY | one twin, little versioning | PARTIAL superseded/archived |

`twin.enriched` (`value_loop.py`): **event**, not a Twin asset update.

---

# G. FUTURE OWNER TEST

Assume they inherit Property X and owner-scoped APIs (or public Passport only).

| | |
|---|---|
| **Can see** | Property fields; request list (if authorized); vault docs; 2D twin if any; Passport badges; PTR compose; PVI/health numbers |
| **Can demonstrate** | That jobs were **declared** opened/confirmed; specialist **name/id** on request; timestamps; files **if uploaded** |
| **Lost** | Specialist narrative; after photos unless vault; exact pipe location; 2026 rec↔2027 job unless HH publish; HH eval if twin unlinked; interior leads |
| **Self-asserted** | Address, ownership, client request text, `/complete`, `/confirm`, client reviews |
| **Documented** | Vault with provenance declared/documented |
| **Verified** | Almost never for work; admin/operator vault `verified`; 2D operator approve; VE gates if listing |

Public Passport: trust score + disclaimer — **not** the full job file.

---

# H. CRITICAL CONTRADICTIONS (runtime only)

1. **Docstring / comment “Cartea Casei” / “documentarea Twin-ului”** vs **no Twin write** — `value_loop.py` emits `twin.enriched` only.  
2. **`GET /properties/{id}/timeline` titled as all events** vs **omits `activity_events`** (`property_timeline.py`).  
3. **`/complete` + `/confirm` imply done** vs **no evidence required**; **health_score rises anyway**.  
4. **Vault `verification_status=verified` on admin/operator upload** vs **file content not reviewed** (`property_documents.py` role shortcut).  
5. **HH rec `done` vs request `confirmed`** — independent; one can be true without the other.

Not contradictions: Model A vs B; 17-step marketing; demo Stripe (money class, not evidence class).

---

# I. MINIMUM IMPLEMENTATION DELTA (do not implement)

Goal: `SPECIALIST → WORK UPDATE → EVIDENCE → PROPERTY → HISTORY` on **existing** objects.

| # | Existing | Gap | Proposed connection | Files / endpoints | DB | Tests | Auth | Risk |
|---|---|---|---|---|---|---|---|---|
| 1 | `requests` + `complete_work` | no payload | Optional body: notes, after_photos[], materials?, room? stored **on the request** | `requests.py` `POST /complete` | additive fields on `requests` | specialist-only; client cannot forge; empty body still allowed or Founder-gated | same `specialist_id` | do not treat as verified |
| 2 | Vault `related_request_id` | unused on close | After photos: write vault `foto` **or** keep on request.photos — pick **one**; prefer vault + `related_request_id` + `property_id` from request | `property_documents.py` upload helper called from complete **or** client confirm | `property_documents` rows | ownership = request specialist or client | IDOR on property_id | don’t auto `verified` |
| 3 | `event_bus.emit` | property timeline ignores it | Extend **composer** `GET /properties/{id}/timeline` to include **filtered** `activity_events` (work.*, document.*, warranty.*) — not all platform events | `property_timeline.py` | **no** new collection | property ownership like GET property | don’t leak other properties | keep technical log on `/requests/{id}/timeline` + admin stream |
| 4 | `value_loop.enrich_on_closure` | health up without evidence | **Do not expand this in v1.** Either skip health inc unless vault/photo present, or leave as-is and **exclude health from “Cartea Casei verified” copy**. Founder pick | `value_loop.py` | none if deferred | regression on confirm | — | false “fixed” |
| 5 | HH `marketplace_request_id` | only publish path | Out of v1 unless Founder wants rec link; do not build matcher | — | — | — | — | — |

**Not in minimum delta:** new Memory Engine, new Property, new Evidence Engine, Twin pin binding, rec state machine, legislative archive.

---

# J. FOUNDER QUESTIONS (repo cannot answer)

1. Is v1 Work Update allowed to be **self-asserted specialist notes + optional photos**, without calling it verified?  
2. Must `/complete` **require** at least one photo/file, or remain optional (liquidity vs dossier)?  
3. Should property timeline show **filtered activity_events**, or stay a compose of requests+vault only?  
4. May we **stop incrementing health on confirm** until evidence exists, or is that a later slice?  
5. Is HH publish the **only** supported rec→job link, or must a 2027 manual request also attach to a 2026 rec?  
6. Future owner: **Passport-only** public story vs **full job file** after sale — which is v1?

(Max 6. No questions the code already answers.)

---

# K. STOP / GO

**GO — putem începe implementarea controlată Work Update → Evidence → Property → Property History.**

Nu există o problemă care să oblige un Property nou sau un Memory Engine.  
Primitivele runtime-relevante sunt: `properties`, `requests` (`property_id` obligatoriu), Vault (`related_request_id`), `activity_events`, `GET /properties/{id}/timeline`, `GET /requests/{id}/timeline`.

Următorul slice (numai după aprobare Founder pe J.1–J.4): **additive fields + optional vault attach + timeline composer filter** — fără a trata `completed`/`confirmed` ca `verified`, fără a crește health din „recomandare”.

**STOP nu se aplică.** Riscul de health fals este un **constraint al slice-ului**, nu un blocaj de domeniu.

---

**STOP after GO/STOP.** No implementation.
