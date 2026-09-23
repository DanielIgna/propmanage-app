# D10 — PROPERTY / PROJECT / DIGITAL TWIN CANONICAL DOMAIN AUDIT

**Mode:** READ-ONLY. No code, schema, migrations, renames, merges, engines, tables, routes, APIs, prices, entitlements, Marketplace, HH, DT, PI, Knowledge Center, commit, or deploy.  
**Lenses:** Senior Software Architect · CTO · Product Architect · Domain Model Architect · Property Technology / Digital Twin  
**Date:** 2026-09-23  
**Given:** D9.5–D9.8. Stops at OBSERVE → EVIDENCE → ANALYZE → IMPACT.

**No implementation performed.**  
Canonicality is earned by **identity + writes + required FKs**, not by a name or a docstring.

---

# A. Executive summary

**What a Property is today:** a client-owned record in `db.properties` (`_id`, `owner_id`, address, type, surface, rooms) plus accumulated **fields** (health scores, `twin_unlocked`, DNA, optional `building_id`). Create requires **no** documents. Ownership is **self-asserted**.

**What a Project is today:** **G — multiple meanings.** At least five runtime objects use the word or the role:

| Object | Collection | “Project” sense |
|---|---|---|
| Designer project | `projects` | C + B — ClickUp / milestone escrow |
| Digital Twin project | `digital_twin_projects` | D — 3D container |
| Marketplace request | `requests` | E — job / intervention |
| Interior lead | `interior_design_leads` | C commercial intake — **no property_id** |
| VE order | `verified_estate_orders` | A + B service order |

**What Digital Twin is today:** **split.** 2D `twins` are **property-keyed**. 3D `digital_twin_projects` are **project-keyed** with **optional** `property_id` (`linked` / `unresolved`). Operator create **requires** `property_id` (P0.1). Client ingest does not always.

**What Property Memory is today:** **not one engine.** Vault docstring claims SSOT; **timeline** only merges requests + vault. PTR, Passport, PVI, warranties, HH, DT are **parallel read models** on `property_id`.

**What Property Intelligence is today:** **E — combination.** Real functions (maturity, assets, decay, PVI, HH recs, passport trust) + unused entitlement flag + GI-5P strategy.

**What an intervention is today:** primarily `requests` **on a required `property_id`**. Commercially a **job**; domain-wise an **intervention**. Offers collection unused in the inspected env (D9.7).

**Can Property be the POS anchor?** **Yes, as the existing identity** — most durable FKs already use `property_id`. It is **PARTIAL** as a digital asset (no required docs, Twin 3D optional, leads/orders often unlinked). **Do not create a new Property entity.**

---

# B. Canonical domain inventory

| ENTITY | FILE / MODEL | PK | FKs | WRITERS | READERS | ROUTES | UI | PURPOSE | DATA | LIFECYCLE | STATUS | CANONICALITY |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Property | `properties.py` `PropertyIn` | `_id` | `owner_id`; opt `building_id` | client POST | list/get, DNA, PI, HH, DT, MP, integrity | `/api/properties` | Client dash, HH, Twin | Dwelling identity | name, address, type, surface, rooms, health_*, twin_unlocked, dna | create→update→delete if no active req | IMPLEMENTED · EVIDENCED | **Strongest identity candidate** — not a complete memory |
| Building | `building_identity.py` `buildings` | `_id` | property.building_id | confirm link | resolver, HartaBlocuri | building routes | admin / PTR | Building context | address match, sources | declared→linked | IMPLEMENTED · PARTIAL | Building ≠ unit; **not** the client POS hub |
| 2D Twin | `twin.py` / operator | `_id` | **`property_id` required in practice** | client submit, operator approve | list properties, PVI, PTR | twin routes | ClientTwin, Operator | Rooms/photos QA | rooms, photos, status | pending→approved | IMPLEMENTED · CONNECTED | **Property asset** when present |
| DT project (3D) | `digital_twin.py` | `id` / `_id` | `property_id` **optional**; owner_id | client/operator upload | viewer, pins, concept→request | `/api/digital-twin/*` | DigitalTwinPage, OperatorDT | 3D container | models, plans, pins | create→models→QA | IMPLEMENTED | **Split:** project asset; property when linked |
| DT model | same | model id | project_id, property_id cascade | upload/convert | viewer | same | same | File + metadata | GLB/SKP, status | inferred→verified / superseded | IMPLEMENTED | Child of DT project |
| Designer project | `projects.py` | `_id` | `client_id`; **`property_id` optional** | designer | members, milestones | `/api/projects` | design UI / demo | Multi-specialist + 4×25% | tasks, milestones | active→completed | IMPLEMENTED | **Different** from MP request |
| Marketplace request | `requests.py` `RequestIn` | `_id` | **`property_id` required**; client_id; specialist_id | client create | specialist, confirm, value_loop, timeline | `/api/requests` | Client/Specialist | Job / intervention | status, escrow_*, photos | open→…→confirmed | IMPLEMENTED · CONNECTED | **Canonical intervention** |
| Offer | `marketplace_offers` | id | request_id | submit_offer | accept_offer | marketplace_offers | OffersList (gated) | Model B | fee, status | unused in D9.7 env | IMPLEMENTED · island | Not the job |
| Vault doc | `property_documents.py` | id | **`property_id`**; opt request/model/asset | owner upload | timeline, PTR, passport | `/api/properties/.../documents` | HH docs, vault | Structured files | category, warranty_*, verification_status | versioned | IMPLEMENTED · CONNECTED | **Strongest memory fragment** |
| Warranty row | `value_loop` | id | property_id, request_id | confirm | PVI, PTR | implicit | DNA/PVI | Auto warranty | months, until | on confirm | IMPLEMENTED · PARTIAL | Parallel to vault garantie |
| Maintenance task | `maintenance_calendar.py` | id | **property_id** | client | tick, 1-click request | `/api/maintenance` | HH / calendar | Recurring plan | template, due | due→request | IMPLEMENTED · CONNECTED | Can spawn request |
| HH subscription | `hh_subscriptions` | user | **user_id** not property | billing | entitlements | HH checkout | /pricing | Access | plan, expires | 0 rows in D9.7 | IMPLEMENTED | **User-scoped** |
| HH evaluation | `hh_evaluations` | id | **property_id** | client/operator | HH UI, PI | house_health | HouseHealthPage | Questionnaire | scores, recs | submit | IMPLEMENTED · CONNECTED | Property-scoped |
| HH rec → request | `house_health_recommendations` | rec + request | property_id | publish | MP | publish | HH recs | Optional job | commission snapshot | — | IMPLEMENTED | Bridge E→request |
| PVI / maturity / DNA | `property_intelligence.py` `property_dna.py` `value_loop` | property | property_id / _id | hunter, confirm, APIs | CEO dash, DNA UI | `/properties/{id}/maturity` etc. | Client PI | Scores | L0–L5, PVI, dna | refresh | IMPLEMENTED | Flags unused (D9) |
| Passport | `property_passport.py` | property | property_id | compute | public page | public passport | PublicPassportPage | Trust 0–100 | badges | on read | IMPLEMENTED | Read model |
| Timeline | `property_timeline.py` | — | property_id | GET aggregate | client | `/properties/{id}/timeline` | Activity | Partial history | requests + vault | on read | IMPLEMENTED · PARTIAL | **Not** full memory |
| PTR | `property_technical_record.py` | — | property_id | GET aggregate | client | PTR routes | PropertyTechnicalRecord | Completeness | vault+twin+reqs+warranties | on read | IMPLEMENTED · PARTIAL | Another composer |
| VE order | `verified_estate.py` | _id | listing/property **optional** | checkout | War Room, EH | VE checkout | EstateBrowse | Service SKU | amount_ron, demo_mode | pending→paid | IMPLEMENTED | Order ≠ property |
| VE listing | same | _id | **property_id optional** | draft after pay | public | `/listings` | VE pages | Sale listing | gates | draft→published | IMPLEMENTED · PARTIAL | |
| Interior lead | `interior_design.py` | id | **no property_id** | landing form | admin | POST leads | /design-interior | Sales intake | contact | — | IMPLEMENTED | **NOT CONNECTED** to property |
| Activity events | `activity_events` / log_event | — | property_id **sometimes** | many | PTR count | — | ActivityTimeline | Audit log | mixed | — | PARTIAL | |
| KG links | `entity_links` | — | property ↔ twin nodes | DT `_kg_link_twin` | PVI identity | — | — | Graph | — | PARTIAL | |

---

# C. Property audit

**Can `db.properties` be the POS anchor?** It **already is the only client dwelling identity**. Do not invent another.

| Concern | Relationship | Evidence |
|---|---|---|
| Identity | DIRECT | `_id` + owner_id |
| Address | DIRECT | `address` (self-asserted); geocode best-effort |
| Building | PARTIAL | `building_id` + resolver; buildings collection reused |
| Apartment/unit | PARTIAL | `type`, `rooms`, `surface` — no cadastral unit id |
| Ownership | DIRECT (asserted) | `owner_id`; vault `act_proprietate` optional |
| Documents | DIRECT | vault `property_id` |
| Digital Twin 2D | DIRECT | `twins.property_id` |
| Digital Twin 3D | PARTIAL | optional + `property_link_status` |
| Designer `projects` | PARTIAL | optional property_id |
| Marketplace | DIRECT on create | `RequestIn.property_id` required; delete blocked if active req |
| Maintenance | DIRECT | `maintenance_tasks.property_id` |
| House Health access | INDIRECT | subscription on **user**; evals on property |
| Property Intelligence | DIRECT | fields + APIs on property |
| Verified Estate | PARTIAL | listing.property_id optional |
| Long-term history | PARTIAL | timeline ≠ all writers |
| Interior leads | NOT CONNECTED | no property_id |
| HH subscription | NOT CONNECTED to a property | user_id |

**`property_id` ABSENT (material):** `interior_design_leads`, `hh_subscriptions`, `marketplace_offers` (request-scoped), `users`, payment_transactions (job-scoped), many `transactions` rows.

---

# D. Project audit — what “Project” **does** mean

| Object | PURPOSE | OWNER | PROPERTY | CLIENT | SPECIALIST | COMMERCIAL | WORK | PAYMENT | DOCS | LIFECYCLE | vs PROPERTY |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `projects` | Designer coordination + 4 tranches | designer | optional | required client_id | members | budget_estimate | tasks/milestones | milestone escrow | comments | active/hold/done/cancel | PARTIAL |
| `digital_twin_projects` | 3D production | owner/operator | optional (required on operator) | via owner | collaborators | HH/VE/none | model QA | not this object | PDF plans | project+models | PARTIAL |
| `requests` | Marketplace job | client | **required** | client_id | specialist_id | escrow/confirm | status machine | DEMO + 0.95 | photos | open…confirmed | DIRECT |
| Interior lead | Sales | none | **none** | email | — | free consult | — | none | — | admin status | NONE |
| VE order | Audit/twin SKU | buyer | via listing | contact | operator | amount_ron | fulfillment out of band | Stripe/DEMO | gates IDs | pending/paid | PARTIAL |
| HH evaluation | Health questionnaire | client | **yes** | user | — | via HH sub | eval status | HH checkout | attachments | submitted | DIRECT |
| Maintenance task | Recurring reminder | client | **yes** | — | trusted spec 1-click | lead fee 0 path | due | none until request | — | due→request | DIRECT |
| Confirm intervention | same as request | — | yes | — | yes | 5% | confirmed | wallet | value_loop | — | DIRECT |

**Meanings present:** A commercial (VE, lead) · B delivery (`projects`, VE) · C design (`projects`, lead) · D Twin production · E Marketplace job · F admin demo milestones · **G all of the above.**

**Do not decide the word “Project” yet.**

---

# E. Digital Twin audit

| Layer | MARKETING | DOCUMENTED | IMPLEMENTED | CONNECTED | USED |
|---|---|---|---|---|---|
| 2D rooms/photos | yes | yes | yes | property_id | operator queue |
| 3D GLB/SKP upload | yes | yes | yes | optional property | ingest |
| Viewer / pins / measure | yes | yes | advanced = Premium flag | entitlement | UI |
| Installation map | X-Ray copy | layers if in file | PARTIAL | — | marketing-heavy |
| Plans PDF | yes | PLAN_TYPES | store | DT project | yes |
| BIM / LiDAR / Matterport / scan | yes | CMS | **no pipeline** | — | marketing |
| Operator workflow | yes | P0.1 | property_id **required** | yes | OperatorDigitalTwin |
| Client workflow | upload | — | property optional | link_status | DigitalTwinPage |
| Versioning | superseded | statuses | PARTIAL | — | PARTIAL |
| concept→request | yes | code | yes | property from project | CONNECTED |

**Is Twin an asset of the Property or of a Project?**

**SPLIT (evidenced):**

- 2D `twins` → **property**.  
- 3D container → **`digital_twin_projects`**; property is a **link**, not the PK.  
- Integrity job treats **orphan 2D twins** (property_id missing in properties).  
- PVI “twin” component reads **2D twin + `twin_unlocked`**, not necessarily a verified 3D model.

---

# F. Property Memory audit

**Unified Property Memory engine:** **does not exist.**  
Vault module **documents** itself as “memoria permanentă” — that is **DOCUMENTED intent**, not a single store.

| Fragment | ID | In timeline GET? | In PTR? | In Passport? |
|---|---|---|---|---|
| Vault | property_id | **yes** | yes | yes |
| Requests | property_id | **yes** | counts | indirect |
| Warranties collection | property_id | no (vault warranty_end yes) | yes | yes |
| 2D / 3D Twin | property_id / optional | **no** | 2D yes | twin badge |
| HH evals | property_id | **no** | no | health |
| Maintenance | property_id | **no** (timeline comment says logs; code uses requests+docs) | no | tasks |
| VE / leads | optional / none | no | no | no |
| Photos | request/vault/twin | if vault | if vault | if vault |
| activity_events | sometimes | no | count | — |

**Common identifier that could later aggregate:** `property_id` (string of Property `_id`).  
**Existing composers (reuse, do not add engine):** `property_timeline`, PTR, Passport, PVI. Timeline is the **narrowest** “history API” and is **incomplete**.

---

# G. Property Intelligence audit

| Capability | SOURCE | PROPERTY LINK | READ MODEL | WRITER | ROUTE | ENFORCEMENT | USERS |
|---|---|---|---|---|---|---|---|
| Maturity L0–L5 | property_intelligence | yes | live | refresh | GET maturity | **not** F_PROPERTY_INTELLIGENCE | client/admin |
| Asset slots | same | yes | slots | POST | PI routes | same | owner |
| Health decay | same | property fields | in-place | hunter | — | — | hunter |
| Predictive candidates | same | yes | opportunities | hunter | — | — | revenue_opportunities |
| PVI | value_loop | yes | score + history | confirm / GET | DNA / confirm | — | CEO, client |
| DNA | property_dna | fields on property | property | client | DNA routes | — | client |
| Passport trust | property_passport | yes | 0–100 | on read | public | — | public |
| HH recommendations | hh_recommendations | yes | recs | after eval | HH | — | client; publish→MP |

**Classification: E — combination.** Real domain functions + recommendation layer + strategy docs. **Not** one Intelligence product.

---

# H. Verified Property / Verified Estate

Verification evidence lives on **several objects**, not a property state machine.

| Evidence | Belongs to | Accumulate on property? |
|---|---|---|
| VE order | order | only if listing.property_id set |
| Gate IDs (audit_report, twin) | listing | PARTIAL |
| Vault `verification_status` | document | yes, per file |
| evidence_semantics | **read-time words** | does **not** persist VERIFIED |
| Passport score | computed on property | yes as score, not legal verify |
| User `verified` | specialist KYC | not the dwelling |

**SELF_ASSERTED** — property owner_id, address.  
**DOCUMENT UPLOADED** — vault.  
**EVIDENCE REVIEWED** — operator twin approve; vault status if used.  
**VERIFIED** as property-level enum: **UNKNOWN / absent.**  
`evidence_semantics.py`: *Identity Gate does not exist yet.*

---

# I. Marketplace ↔ Property

**Create request:** loads property by `property_id` + `owner_id`; copies name/address; `log_event(..., property_id=...)`.  
**Delete property:** blocked if assigned/in_progress/completed requests exist.  
**Offers:** no property_id (request-scoped).  
**Confirm:** value_loop uses request.property_id.  
**D9.7:** 118 requests, 0 offers.

**Answer:** A Marketplace request is **both**:

- commercially an **independent job** (escrow, 5%, wallet), and  
- domain-wise an **intervention on a property** (`property_id` **required** at create).

It is **not** a child of `projects` or `digital_twin_projects`.

---

# J. House Health ↔ Property

| Relation | Runtime? |
|---|---|
| USER ↔ subscription | **yes** (user_id) |
| PROPERTY ↔ evaluation / recs | **yes** (property_id) |
| DIGITAL TWIN | eligibility / UI “twin” — **PARTIAL** (EH twin_unlocked; not a paywall on MP) |
| PROPERTY INTELLIGENCE | scores coexist; PI flag unused |
| MARKETPLACE | publish rec → request **yes**; D11 HH does not gate MP |
| VERIFIED ESTATE | **not** the same checkout |

Entitlements stay user-tier. **Do not modify.**

---

# K. Actual domain graph (from code)

```
USER (client)
 ├── DIRECT IMPLEMENTED → PROPERTY (owner_id)
 │     ├── DIRECT → vault documents
 │     ├── DIRECT → 2D twins
 │     ├── PARTIAL → digital_twin_projects (optional property_id)
 │     ├── DIRECT → requests (required) → specialist, escrow, confirm → value_loop
 │     ├── DIRECT → maintenance_tasks → (can create) request
 │     ├── DIRECT → hh_evaluations / hh recs → (optional) request
 │     ├── DIRECT → PI / DNA / PVI fields
 │     ├── PARTIAL → building_id → buildings
 │     ├── PARTIAL → designer projects.property_id
 │     ├── PARTIAL → VE listing.property_id
 │     └── PARTIAL composers: timeline (req+vault), PTR, passport
 ├── DIRECT → hh_subscriptions (NO property)
 ├── NOT CONNECTED → interior_design_leads
 └── tokens / wallet (user, not property)

USER (designer)
 └── DIRECT → projects (client_id, optional property)

USER (operator)
 └── DIRECT → 2D approve; 3D operator create REQUIRES property_id

request ── PARTIAL ── digital_twin concept spawn
document ── PARTIAL ── related_model_id / related_request_id
```

No single `USER → PROPERTY → PROJECT → SERVICE` spine. Closest spine:

```
USER → PROPERTY → REQUEST (intervention)
                → VAULT / 2D TWIN / HH EVAL / MAINTENANCE
                → (optional) DT PROJECT / DESIGNER PROJECT / VE LISTING
```

---

# L. Duplication / overlap (do not merge)

| Overlap | Evidence | Why | Actual difference | Risk | Action |
|---|---|---|---|---|---|
| Property vs apartment | type/rooms vs buildings | unit vs building | building_id optional | address ambiguity | DO NOT MERGE |
| `projects` vs DT project | two collections | both “project” | design vs 3D | Founder confusion | DO NOT MERGE |
| `projects` vs request | both delivery | jobs vs ClickUp | MP required property; designer optional | double job systems | DO NOT MERGE |
| Twin vs DT project | twins vs digital_twin_projects | both Twin | 2D vs 3D | PVI sees 2D | DO NOT MERGE |
| Passport vs VE | both “trust/sale” | public score vs listing | compute vs gates | “verified” overload | DO NOT MERGE |
| PI vs health_score vs HH | three health languages | scores everywhere | PI/PVI vs property fields vs evals | dashboard contradiction | DO NOT MERGE |
| Vault vs “Memory” | docstring SSOT | intent vs composers | vault is files; timeline incomplete | false SSOT | DO NOT MERGE |
| Audit vs VE audit vs HH eval vs design_audit | D9.6 | word | four products | commercial lie | DO NOT MERGE |
| Maintenance vs request | calendar spawns request | same work | plan vs job | OK as chain | KEEP CHAIN |
| Warranty vault vs warranties coll | two | confirm vs upload | parallel | duplicate warranties | DO NOT MERGE yet |
| Timeline vs PTR vs Passport | three GET aggregators | same key | different slices | drift | CONSOLIDATE later **as reads only** |

---

# M. Property lifecycle (do not assume)

| Transition | Status |
|---|---|
| PROPERTY CREATED | **IMPLEMENTED** |
| → DOCUMENTED | **PARTIAL** (vault optional) |
| → AUDITED | **PARTIAL** (HH eval / VE / CMS) **NOT CONNECTED** as one |
| → DIGITAL TWIN CREATED | **PARTIAL** (upload / 2D; scan NOT CONNECTED) |
| → PROJECT STARTED | **UNKNOWN which project** — request / designer / DT |
| → INTERVENTION | **IMPLEMENTED** (request) |
| → COMPLETION | **IMPLEMENTED** (`/complete`) |
| → DOCUMENTATION | **PARTIAL** (value_loop + optional vault) |
| → MAINTENANCE | **PARTIAL** (calendar) |
| → VERIFICATION | **PARTIAL** (passport/VE) **no property VERIFIED** |
| → PROPERTY INTELLIGENCE | **PARTIAL** (refresh/hunter) |
| → FUTURE INTERVENTION | **PARTIAL** (new request; hunter candidates) |

**No coherent end-to-end lifecycle object.**

---

# N. Canonicality matrix

| DOMAIN | CURRENT OBJECT | CANONICAL? | EVIDENCE | OVERLAP | RISK | FUTURE ROLE | DECISION? |
|---|---|---|---|---|---|---|---|
| Property | `properties` | **Yes as identity** | owner_id, required on requests | vs building | incomplete asset | POS hub **as-is** | none to replace |
| Project | many | **No single** | 5+ objects | naming | wrong merge | keep distinct | **what “Project” means in UI** |
| Digital Twin | twins + DT projects | **Split** | optional 3D link | marketing | asset ownership | property-linked 3D | link policy |
| Property Memory | fragments + 3 composers | **No** | timeline subset | vault claim | fake SSOT | read compose later | do not build engine |
| Property Intelligence | module + PVI + HH | **Fragment** | real APIs | health words | unused flag | keep functions | none |
| Marketplace request | `requests` | **Yes as intervention/job** | required property_id | vs `projects` | two delivery stacks | stay job-on-property | none |
| Intervention | = request (+ maint spawn) | **Yes de facto** | FK | — | — | — | none |
| Verified Property | VE listing + passport | **No property enum** | gates, score | “verified” | trust | stay VE+passport | none |
| House Health | user sub + property eval | **Split user/property** | D11 | Twin copy | — | stay | none |
| Documents | vault | **Yes for files** | property_id, categories | warranties coll | — | stay | none |
| Maintenance | maintenance_tasks | **Yes for plans** | property_id | vs request | — | stay | none |

---

# O. Cross-functional lens (no scores)

| Lens | Material finding |
|---|---|
| CEO | POS story needs Property hub — **identity already exists**; journey 17 is not this graph |
| CFO | Jobs hang on property; money still class B/C (D9.8) |
| CPO | “Project” in nav/UI is overloaded |
| CTO | Required FK on requests is the strongest invariant; DT 3D is weaker |
| Architecture | Three history composers; do not add a fourth engine |
| Trust | No property VERIFIED; ownership asserted |
| Security | Property GET ownership exists (prior fix); delete vs active req |
| Data | Leads/orders often off-graph |

**UNKNOWN:** % of DT projects with `property_link_status=linked` in live data (not re-queried here).

---

# P. Critical architectural findings

1. **`properties` is the canonical dwelling.** Sufficient as POS identity. Insufficient as automatic memory.  
2. **“Project” is not a domain type; it is a label collision.**  
3. **Marketplace request is the canonical intervention** and **already property-scoped**.  
4. **Digital Twin is split** (2D property / 3D project).  
5. **Memory is `property_id` + parallel readers**, not an engine.  
6. **Interior leads sit outside the graph.**  
7. **HH money is user-scoped; HH clinical data is property-scoped.**  
8. **Do not merge** `projects` with `requests` or `digital_twin_projects`.

---

# Q. Unknowns / gaps

Live % linked 3D twins; whether designer `projects` are used in prod; timeline consumers vs PTR; vault `verification_status` value distribution; 2 founder DT cases’ property_ids (D9.8); cadastral identity.

---

# R. Founder decisions (no implementation)

1. In product language, is **“Project”** banned except designer `projects`, or aliased to **request**?  
2. Must **every** 3D Twin be property-linked (operator already; client optional)?  
3. Should **leads** require a property before they are “real work”?  
4. Is **timeline** the future history surface (extend readers) vs leave three composers?  
5. Confirm: **do not** build Property Memory Engine.

---

# S. Recommended next audit

**D10.1 — property_id coverage fact-check (read-only):** counts of requests/docs/twins/DT projects/HH evals/VE listings **with vs without** `property_id` / `linked` in `propmanage_db`. No schema change.

---

# T. DO NOT CHANGE YET

Code, schemas, names, merges, new Property, new Memory/OS engine, new Project unification, Marketplace A/B, HH entitlements, DT ingest rules, PI flags, prices, commits, deploys.

Do not “fix” optional 3D `property_id` in this audit.  
Do not collapse Twin 2D/3D.  
Do not treat vault docstring as implemented SSOT.

**STOP.** Discovery only.
