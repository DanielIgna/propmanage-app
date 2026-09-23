# D10.1 — PROPERTY ASSET & INTERVENTION LIFECYCLE AUDIT

**Mode:** READ-ONLY. Continuation of D10. No implementation, rename, merge, migrate, refactor, entity, engine, commit, or deploy.  
**Date:** 2026-09-23  
**Stops at:** OBSERVE → EVIDENCE → ANALYZE → IMPACT  
**Does not** design Property OS or resolve D10 naming collisions.

**No implementation performed.**

---

# A. Executive summary

A Property can **remember** completed Marketplace work **if** `property_id` was set: the `requests` row remains, `value_loop` writes a `warranties` row, bumps health fields, emits `activity_events`, and refreshes PVI. Photos stay on the **request**, not auto-copied to Vault. The **property timeline API does not read `activity_events`** — it recomposes only requests + vault documents.

House Health clinical records hang on **`twin_project_id`**, not on Property. 3D Twin hangs on **`digital_twin_projects`**, with optional Property link. Interior leads and some VE orders never enter the property graph.

**How much POS exists:** identity + required intervention FK + several writers after `/confirm` + three incomplete history readers.  
**Where work disappears:** leads; unlinked 3D/HH; designer projects without `property_id`; confirm events that the timeline composer ignores; no vault/twin 3D rewrite on job close.

---

# B. Property asset inventory

Only links **evidenced** in code. No inferred edges.

| OBJECT | PROPERTY LINK | DIRECT / INDIRECT | FK | WRITER | READER | LIFECYCLE | PURPOSE | EVIDENCE |
|---|---|---|---|---|---|---|---|---|
| Vault `property_documents` | yes | DIRECT | `property_id` | owner upload | timeline, PTR, passport | version / deleted | files + warranty_* | `property_documents.py` |
| 2D `twins` | yes | DIRECT | `property_id` | client request, operator | list properties, PVI, PTR | pending_validation → approved | rooms/photos | `operator_twins.py` insert |
| 3D `digital_twin_projects` | optional | DIRECT if set | `property_id`, `property_link_status` | client/operator | viewer, HH (via twin id) | project+models | 3D container | `digital_twin.py` |
| DT models / plans / pins | via project | INDIRECT | project_id; model may cascade property_id | upload | viewer | processing→ready/superseded | files | same |
| `requests` | **required on create** | DIRECT | `property_id` | client | timeline, value_loop, delete-guard | open…confirmed | job | `RequestIn` |
| `marketplace_offers` | via request | INDIRECT | request_id | submit_offer | accept_offer | unused in D9.7 | Model B | no property_id |
| `maintenance_tasks` | yes | DIRECT | `property_id` | client | calendar, 1-click req | due → request | plan | `maintenance_calendar.py` |
| HH evaluations / scores / hh_documents | via **twin project** | **INDIRECT** | `twin_project_id` | specialist/admin | HH UI | draft→approved | assessment | `house_health.py` create **no property_id** |
| HH recs / published request | yes on publish | DIRECT | `property_id` | publish | MP | — | optional job | `house_health_recommendations.py` |
| VE listing | optional | DIRECT if set | `property_id` | draft after pay | public | draft→published | sale | `verified_estate.py` |
| VE order | via listing | INDIRECT | listing | checkout | War Room | pending/paid | SKU | D10 |
| Passport | computed | DIRECT read | prop `_id` | GET | public | on read | trust score | `property_passport.py` |
| PTR | computed | DIRECT read | prop_id | GET | client | on read | completeness | `property_technical_record.py` |
| PVI / maturity / DNA | on property | DIRECT | `_id` | confirm, hunter, APIs | CEO, DNA | refresh | scores | `value_loop`, PI |
| `warranties` | yes | DIRECT | `property_id`, `request_id` | `enrich_on_closure` | PVI, PTR | active until | auto warranty | `value_loop.py` |
| Contracts / receipts | if vault category | DIRECT | property_id | upload | vault | — | `contract` / `factura` | CATEGORIES |
| Photos | request.photos or vault `foto` or twin | DIRECT or on request | property_id on req/doc | upload | request/vault | persist on parent | not auto-promoted | request doc |
| Measurements | HH eval.measurements or viewer | INDIRECT (HH) / session | twin_project_id | eval / UI | HH | on eval | not property-native | HH create |
| Plans | DT PDF | INDIRECT | DT project | upload | DT | stored | `digital_twin_plans` | |
| Installations / equipment / materials | PI slots, twin assets, vault notes | PARTIAL DIRECT | property / twin | PI/twin | PI | — | not a dedicated asset ledger | PI / 2D assets[] |
| `activity_events` | often | DIRECT if set | `property_id` | `event_bus.emit` | PTR **count**; **not** timeline GET | append-only | event log | `event_bus.py` |
| Designer `projects` | optional | DIRECT if set | `property_id` | designer | project UI | active→completed | coordination | `projects.py` |
| Interior leads | **none** | — | — | landing | admin | — | sales | D10 |
| Wallet / job_payment | user / request | INDIRECT | request_id | confirm | wallet | — | money not property | D8 |

**Audits:** no single `audits` collection. VE order, HH eval, CMS copy, admin design_audit — see D9.6.  
**Passport / PTR:** readers, not stores.

---

# C. Intervention / work inventory

| OBJECT | LEAD? | COMMERCIAL? | WORK? | PROJECT? | TX? | PROPERTY | CLIENT | SPECIALIST | STATUS | PAYMENT | RESULT/DOCS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Marketplace request | becomes lead for specialists | yes | **yes** | no (word) | escrow/confirm | **required** | client_id | specialist_id | open…confirmed | DEMO + 0.95 | request + value_loop |
| Offer | supply intent | fee | no | no | apply fee | via request | — | specialist | 0 rows env | credits/wallet | — |
| selected_offer_id | — | — | — | — | — | via request | — | — | unused env | — | — |
| Assignment `/accept` | — | yes | starts job | no | credit debit | via request | — | set | assigned | D2 | — |
| Interior design lead | **yes** | later | no | no | no | **none** | email | — | admin | none | none |
| Designer `projects` | no | budget/milestones | yes | **yes** (C/B) | 4×25% | optional | client_id | members | active… | milestone | tasks, not vault |
| DT project | no | HH/VE/none | production | **yes** (D) | not this row | optional / required operator | owner | collab | models | — | models/plans |
| VE order | no | **yes** | fulfillment out-of-band | no | Stripe/DEMO | optional | contact | operator | pending/paid | amount_ron | draft listing; empty gate IDs |
| “Audit” | mixed | VE or lead | promised field | no | VE or 0 | optional | — | — | — | — | no IR store |
| Maintenance task | reminder | when → request | plan | no | 0 until req | **yes** | owner | trusted 1-click | due | — | new request |
| HH evaluation | no | via user sub | assessment | no | HH checkout | **via twin project** | owner of twin | specialist author | draft/approved | user sub | eval + attachments on twin id |

Do not merge.

---

# D. Lead → work transition map

Desired-looking chain vs evidence:

```
LEAD → PROPERTY IDENTIFIED → REQUEST → OFFER → ACCEPTANCE → WORK → COMPLETION → RESULT → PROPERTY HISTORY
```

| Transition | Interior lead | Marketplace | Digital Twin | Verified Estate | Maintenance |
|---|---|---|---|---|---|
| LEAD | IMPLEMENTED (`interior_design_leads`) | request notify = lead | LiDAR CTA `/register` NOT CONNECTED | inquiry / order pending | task due |
| PROPERTY IDENTIFIED | **NOT CONNECTED** | **IMPLEMENTED** (required) | PARTIAL (optional / operator required) | PARTIAL (listing.property_id) | **IMPLEMENTED** |
| REQUEST | NOT CONNECTED | **IMPLEMENTED** | PARTIAL (concept→request) | NOT CONNECTED (order ≠ request) | PARTIAL (1-click create request) |
| OFFER | NOT CONNECTED | **PARTIAL** (Model B unused) | — | — | — |
| ACCEPTANCE | — | **IMPLEMENTED** `/accept` | — | pay order | — |
| WORK | human out-of-band | `/start`…`/complete` | upload/convert/QA | **UNKNOWN** crew | after request exists |
| COMPLETION | NOT CONNECTED | `/confirm` | model status | paid ≠ delivered | request confirm |
| RESULT | none on property | value_loop + request row | files on DT project | draft listing | same as request |
| PROPERTY HISTORY | **NOT CONNECTED** | PARTIAL (timeline composer) | PARTIAL if linked | PARTIAL | PARTIAL |

---

# E. Marketplace request lifecycle

```
CREATE (property required)
  → OPEN
  → /accept  (Model A; Model B accept_offer unused in env)
  → ASSIGNMENT (specialist_id)
  → /start   (ungated vs pay — D7)
  → WORK     (in_progress)
  → /complete
  → /confirm (client; status must be completed)
  → PAYMENT/PAYOUT  wallet += escrow*0.95; payment_transactions optional DEMO
  → status=confirmed, escrow_status=released
```

**After `/confirm`, what persists on the Property?**

| Target | Created / updated? | Evidence |
|---|---|---|
| Request row | **yes** — stays forever with property_id, photos, escrow_amount, confirmed_at | `requests.update` |
| Wallet | **yes** on **specialist user**, not property | `wallet_balance` |
| `transactions` job_payment | **yes** — user ledger | D8 |
| Client tokens | **yes** +100 on user | confirm |
| `warranties` | **yes** if property_id and no prior row for request_id | `enrich_on_closure` |
| Property health fields | **yes** bounded + `twin_works_documented` + `last_enriched_at` | same |
| PVI | **yes** `refresh_pvi(trigger=job_closure)` | same |
| Twin 2D/3D **geometry** | **no** — only `emit("twin.enriched")` | comment “documentarea Twin-ului” is an **event**, not a model write |
| Vault document | **no** auto insert | — |
| Maintenance task | **no** | — |
| `activity_events` | **yes** — `work.confirmed`, `warranty.created`, `health.updated`, `twin.enriched` | `log_event` / `emit` |
| Timeline **API** | **yes for request statuses**; **no for those activity_events** | `property_timeline.py` only reads requests + vault |
| Passport | **indirect** next read (warranties, health, works) | compute |
| PTR | **indirect** counts / warranties | compute |
| Reviews | only if client later reviews | separate |

If `property_id` missing on confirm (should not happen for API-created jobs): `enrich_on_closure` returns `{}` — **nothing** on property.

---

# F. Digital Twin lifecycle

### A. 2D Twin

```
CREATE  client POST …/twin → insert or reset pending_validation (property_id REQUIRED)
  → CAPTURE  rooms/photos in operator/client flows (not LiDAR)
  → PROCESS  operator review
  → STORE    db.twins
  → VIEW     GET …/twin (owner, assigned specialist, admin, operator)
  → UPDATE   re-request validation
  → VERSION  no model versions — one twin per property_id typical
  → COMPLETE approved / needs_revision
```

**Persistent property asset:** **YES** (the `twins` document).  
**Old versions:** **UNKNOWN / no** (overwrite status, not a version chain).

### B. 3D Digital Twin Project

```
CREATE  digital_twin_projects (client: property optional; operator: property REQUIRED P0.1)
  → UPLOAD  GLB/SKP/… → digital_twin_models (version: 1, superseded_by)
  → PROCESS Blender/CloudConvert subset (async)
  → STORE   files + metadata statuses processing|ready|stored|superseded|archived
  → VIEW    viewer; pins/comments if entitled
  → UPDATE  new models; link property
  → VERSION fields exist (version, superseded_by); not a full BIM history UI
  → COMPLETE operator/professional verification statuses
```

**When property_id required:** operator create. **Optional:** client create / list filter.  
**Persistent property asset:** **YES if linked**; else **project-only**.  
**Old versions:** **PARTIAL** — superseded/archived statuses; accessibility **UNKNOWN** without UI proof.  
**Client vs operator:** operator cannot skip property; client can.

HH then attaches to **this project id**, not to Property.

---

# G. Property memory / history evidence

No Memory Engine (D10). What **acts** as persistence:

| Mechanism | Kind | After job tomorrow? |
|---|---|---|
| `requests` with property_id | **A PERSISTED FACT** + photos | **yes** |
| `warranties` from confirm | **A** | **yes** |
| property health_* / twin_works_documented | **D STATUS** | **yes** |
| PVI history | **D** / score | **yes** if refresh ran |
| `activity_events` | **C EVENT** | **yes stored**; **not** in timeline GET |
| Vault file | **B DOCUMENT** | only if someone uploaded |
| Timeline GET | composed **C** from req+vault | sees request + vault; **misses** confirm events, HH, DT, maintenance, VE |
| PTR / Passport | composed **D** | next view |
| HH recs | **E RECOMMENDATION** | if eval on twin project |
| job_payment / wallet | **F TRANSACTION** | user, not property |
| Twin geometry update | **G NOTHING** from confirm | — |

**If a specialist finishes work on Property X today, X can remember tomorrow:**

- That a request existed (title, category, specialist, dates, escrow, photos on the request).  
- An auto warranty row + slightly higher health + new PVI.  
- Events in `activity_events` **if** something queries that collection (PTR counts them; timeline does not list them).  

X **cannot** automatically remember: a vault invoice, an updated 3D model, an HH eval (unless on a linked twin project and HH UI), a lead, or a designer project without `property_id`.

---

# H. Result / knowledge retention matrix

| Intervention | Persistent property knowledge? | Evidence |
|---|---|---|
| DIGITAL TWIN 2D | **YES** | `twins.property_id` |
| DIGITAL TWIN 3D | **PARTIAL** | files on project; property optional |
| AUDIT (VE) | **PARTIAL** | order/listing; `audit_report_id` empty at draft |
| AUDIT (HH eval) | **PARTIAL** | persisted on **twin_project_id** |
| AUDIT (CMS/17-step) | **NO** | lead only |
| MAINTENANCE | **PARTIAL** | task + spawned request |
| MARKETPLACE WORK | **PARTIAL** | request + value_loop; no vault/3D |
| VERIFIED ESTATE | **PARTIAL** | listing/order; not a property VERIFIED enum |
| DESIGN PROJECT | **PARTIAL** / **NO** if no property_id | `projects` optional FK |
| HOUSE HEALTH eval | **PARTIAL** | twin-scoped; user sub not on property |
| INTERIOR LEAD | **NO** | no property_id |

---

# I. Property timeline audit

| Implementation | Source | Event types | FKs | Writer | Reader / UI | Retention | Kind |
|---|---|---|---|---|---|---|---|
| `GET /properties/{id}/timeline` | live query requests + vault | request_created, specialist_assigned, work_completed, confirmed, document_uploaded, warranty_registered (**vault warranty_end only**) | property_id, request_id, doc_id | none (compose) | Marketplace.jsx, PTR | limit 200 req / 300 docs | **B composed + C partial** |
| `GET /requests/{id}/timeline` | request events | request-scoped | request_id | — | ActivityTimeline.jsx | — | **request log**, not property |
| `activity_events` via `event_bus.emit` | insert | work.confirmed, twin.*, warranty.created, health.updated, twin.requested, request.created, … | property_id, request_id, actor_id, created_at | many | PTR **count**; orchestrator if playbook | append | **A real event log** |
| Passport events | computed | warranty etc. | property | GET | public | — | **B** |
| Value_loop “Cartea Casei” comment | emit twin.enriched | — | property | confirm | **not in timeline GET** | — | **C unused by composer** |

**Verdict:** Timeline UI for a **property** is **C partial composed read model**. A **real event log exists** (`activity_events`) and is **not** what `/properties/{id}/timeline` returns.

---

# J. Actual Property → Intervention → Result graph

```
PROPERTY
  ├── IMPLEMENTED → REQUEST (create)
  │     ├── PARTIAL → OFFER (code; 0 in env)
  │     ├── IMPLEMENTED → /accept ASSIGNMENT
  │     ├── IMPLEMENTED → /start /complete /confirm
  │     ├── IMPLEMENTED → RESULT: request persisted + warranties + health + PVI + activity_events
  │     ├── NOT CONNECTED → vault auto
  │     ├── NOT CONNECTED → 3D model write
  │     └── PARTIAL → timeline composer (request fields only)
  ├── IMPLEMENTED → 2D TWIN
  ├── PARTIAL → 3D DT PROJECT → HH EVAL (twin_project_id)
  ├── IMPLEMENTED → VAULT (manual)
  ├── IMPLEMENTED → MAINTENANCE → (PARTIAL) REQUEST
  ├── PARTIAL → DESIGNER PROJECT
  ├── PARTIAL → VE LISTING/ORDER
  └── NOT CONNECTED → INTERIOR LEAD
```

---

# K. Context loss / orphan analysis

| OBJECT | CURRENT LINK | RISK | EVIDENCE |
|---|---|---|---|
| Interior lead | none | work never becomes property history | no property_id |
| 3D DT project | optional property_id | Twin/HH orphaned from dwelling | `_resolve_property_anchor`; client create |
| HH evaluation | twin_project_id | assessment lost if project unlinked/deleted | `create_evaluation` |
| Designer project | optional property_id | delivery history off-graph | `ProjectIn.property_id` Optional |
| VE order | listing optional property | paid service not on Property X | D10 |
| Confirm without property_id | enrich no-op | **G NOTHING** | `if not prop_id: return {}` |
| Request photos | on request | exist but not vault/timeline as documents | request.photos |
| `activity_events` | property_id often | **stored but invisible** on property timeline | composer omission |
| `twin.enriched` | event only | looks like Twin update; **is not** | value_loop §3 |
| Offers | request only | no property query | schema |
| job_payment | user | cash memory ≠ property memory | D8 |
| Orphan 2D twin | property_id stale | integrity job exists | `admin_data_integrity.py` |
| Vault without upload after job | — | job has no invoice in Cartea Casei | no auto write |

Do not fix.

---

# L. Cross-functional lens

| Lens | Material |
|---|---|
| CEO | Completed jobs **do** leave a scar on the property — thin (request + scores), not a dossier |
| CFO | Payout is on the specialist; property remembers escrow_amount on the request, not platform 5% |
| CPO | “Cartea Casei” in comments ≠ timeline contents |
| CTO | Two histories: `activity_events` vs compose GET |
| Architecture | HH→twin_project is the sharpest hidden hop |
| Trust | Passport may rise after confirm without a reviewed document |
| Security | Specialists can read 2D twin if historically assigned |
| Data | Leads and unlinked 3D are the largest knowledge leaks |

UNKNOWN: % of DT projects unlinked; whether anyone reads `activity_events` in a UI besides PTR count.

---

# M. Critical findings

1. **`/confirm` is the only automatic property-knowledge write** for Marketplace work (warranty, health, PVI, events).  
2. **It does not file documents or update 3D.**  
3. **Property timeline ignores the event log it conceptually belongs to.**  
4. **HH memory is Twin-project-scoped, not Property-scoped.**  
5. **2D Twin is a true property asset; 3D is a project asset that may attach.**  
6. **Leads never become property history.**  
7. Enough POS exists to **remember that work happened**; not enough to **reuse a professional dossier** without extra uploads/links.

---

# N. Unknowns

Live link rates; UI for superseded 3D models; request timeline vs property timeline user paths; 2 founder field cases’ IDs; whether `twin_works_documented` is shown anywhere.

---

# O. Founder decisions later (not now)

1. Should confirm **require** a vault artifact?  
2. Must HH evals carry `property_id` as well as `twin_project_id`?  
3. Should property timeline **read** `activity_events`?  
4. Client 3D create: keep optional property or match operator?  
5. Are interior leads allowed to stay off-graph?

No decisions in this document.

---

# P. Recommended next audit

**D10.2 — History reader coverage (read-only):** list every UI that claims “istoric / Cartea Casei / timeline” and map it to `property_timeline` vs `activity_events` vs `requests/{id}/timeline` vs PTR vs Passport. Still no engine.

---

# Q. DO NOT CHANGE YET

Confirm/value_loop, timeline composer, HH twin_project_id, DT optional property, leads, Marketplace A/B, schemas, Memory Engine, merges, prices, commit, deploy.

**STOP.**
