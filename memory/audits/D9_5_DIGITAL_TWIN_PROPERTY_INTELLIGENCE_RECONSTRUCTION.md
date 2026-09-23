# D9.5 — DIGITAL TWIN + PROPERTY MEMORY + PROPERTY INTELLIGENCE + AUDITS + 79/249

**Mode:** READ-ONLY reconstruction. No implementation, schema, prices, UI, entitlements, Marketplace, trials, Stripe, new runtime agents, commit, or deploy.  
**Date:** 2026-09-23  
**Lenses:** CEO · CFO · CPO · CTO · Senior Architect · Marketplace/Trust · CX · Real Estate  
**Given:** D1/D2/D6/D8/D11/D9. Founder: **do not** cap clients at 3 free Marketplace requests. Protect liquidity; analyze spam/abuse/cost separately.

**No implementation performed.**

Commercial numbers that are not in code or ledgers are marked **UNKNOWN**. Do not invent LTV, take rate, or margins.

---

# 1. Executive reconstruction

PropManage already contains **several overlapping products**, not one implemented “Property OS.”

| Intended story (marketing / GI-5P / 17 etape) | What the repository actually is |
|---|---|
| One 17-step journey from consult → House Health | **CMS / landing content.** `journey_guardian` checks the **copy has 17 steps**. No runtime state machine walks a property through 1→17. |
| Digital Twin = LiDAR + BIM + history + warranties | **Two technical layers:** `twins` (2D rooms) + `digital_twin_projects` (3D GLB/SKP + PDF plans + pins). Ingest is largely **owner upload**. LiDAR/Matterport/BIM-as-authoring = **UI/marketing**, not a capture pipeline. |
| Property Memory | **Strategic doc** (`memory/GI5P_PROPERTY_INTELLIGENCE.md`). Runtime memory is **dispersed**: vault, warranties, PVI history, requests, value_loop, passport, maintenance. |
| Property Intelligence | **Partial runtime:** maturity L0–L5, asset slots, health decay, predictive candidates, PVI. **Not** gated by `F_PROPERTY_INTELLIGENCE`. GI-5P graph/memory is **not** a single engine. |
| Audits | At least **four different “audit” words**: interior-design **technical audit copy**; VE **audit_ron** professional service; HH **evaluations**; admin **UX design_audit**. Plus App.js disclaimer: platform QA ≠ legal energy audit. |
| 79 EUR | Seed **`hh_plans.premium` = 79**. SaaS checkout. |
| 249 EUR | **Not a SKU in source.** PRD/founder intent. Same Premium slug if DB overwritten. |
| Marketplace | Job spine (D1–D8). **Ungated** for clients with a property (D9/D11). |
| Sale / Verified Property | **Verified Estate** listings + `audit_ron`/`twin_ron` (defaults 2400 / 15000 RON) + sale commission + Passport trust. Separate from HH 79/249. |

**CEO:** The brand story is one integrated process; the P&L is at least **three money engines** (Marketplace job 5%, HH subscription, VE professional + sale commission).  
**CFO:** Recurring = HH (if paid). Transaction = Marketplace confirm haircut. Service = VE audit/twin RON and interior leads (often unpriced). 79 vs 249 and advertised trials are **promise risk**. All unit economics **UNKNOWN** without live volume.  
**CPO:** 17 stages sell a journey the app does not orchestrate.  
**CTO:** Reuse collections; do not add a Memory Engine.  
**Architect:** Property is the intended hub; Twin 2D/3D link is **PARTIAL**.  
**Trust:** Ownership is asserted; “Verified Property” is VE + passport scores, not legal title.  
**CX:** Customer can hear “LiDAR in 48h” (`PublicDemoPage.jsx`) and land on **upload-your-GLB**.  
**RE:** Sale path exists as VE + Passport, not as automatic “document → listing.”

---

# 2. 17 stages map

**Source of truth for names:** `backend/service_content_design.py` `process_phases` (also CMS `interior_design_content` / landing `InteriorDesignLanding.jsx`).  
**Guardian:** `journey_guardian.py` — fails if step count ≠ 17.

| n | Name | Phase | Commercial text (abbrev.) | Service / money | CTA | Checkout | Plan | Specialist | DT dep. | HH dep. | MP dep. | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Consultanță inițială | Descoperire | Prima discuție **gratuită** | Lead (`interior_design_leads`) | Landing / ServiceDetailModal | **No** stage checkout | No | Human sales | No | No | Optional later | DOCUMENTED · UI CONNECTED · **not** a request state |
| 2 | Audit tehnic al locuinței | Descoperire | Instalații, structură, energie | Copy + VE `audit_ron` is a **different** priced SKU | “Află tot ce include Auditul” | VE checkout **if** VE product | No HH | Promised field specialist | Promised as input to Twin | No | Can become request | DOCUMENTED · VE IMPLEMENTED separately · 17-step **not** runtime |
| 3 | Ridicare măsurători | Descoperire | Releveu | Unpriced | — | No | No | Promised | Feeds Twin copy | No | No | DOCUMENTED · UI |
| 4 | Scanare Digital Twin | Digitalizare | Scanăm locuința | VE `twin_ron` **or** DT upload | Twin details / LiDAR demo CTA | VE or none | HH Premium for **advanced** DT | Operator validation queue | **This is the Twin** | HH eligibility mentions twin | No | DOCUMENTED · DT **upload** IMPLEMENTED · **scan** UNKNOWN/UI |
| 5 | Model 3D | Digitalizare | Model exact | Same | Viewer | — | Entitlement for advanced | Optional professional validation | `digital_twin_models` | No | Concept→request exists | IMPLEMENTED (GLB etc.) |
| 6 | Planșe tehnice | Digitalizare | Planuri execuție | PDF `PLAN_TYPES` | Upload plan | — | Ingest open | — | `ALLOWED_PLAN_EXTS=.pdf` | No | No | IMPLEMENTED store · not BIM authoring |
| 7–11 | Arhitectură / Design / Materiale / Soluții / Bugetare | Proiectare | Design services | Interior assistant, concept AI, design `phases` | Design landing | Design phase pay **sibling** | No | Designers | Concept from Twin | No | Offers | PARTIAL (design module ≠ 17 orchestrator) |
| 12–15 | Management / Coordonare / Verificare / Recepție | Implementare | Escrow pe etape | Marketplace + design phases | Marketplace CTAs | Job DEMO checkout / design phase | No | Specialists | Photos/docs promised back to Twin | No | **Yes** (13 = offers) | Marketplace IMPLEMENTED · not bound to step numbers |
| 16 | Actualizarea Digital Twin | Viață lungă | Materiale, garanții, foto | value_loop on confirm; vault warranties | — | — | — | — | Intended write-back | No | After jobs | PARTIAL (`enrich_on_closure`) |
| 17 | House Health | Viață lungă | Monitorizare + istoric | HH subscription 9/29/79 | `/pricing` | HH Stripe | **This is HH** | Evaluations | Twin often required for HH UI | **Yes** | Publish rec→request | HH IMPLEMENTED · not “step 17” of a job |

**AUTOMATED:** guardian counts 17. **AUTONOMOUS:** no.  
**Do not confuse** this content with `requests.status` or design `phases[]`.

**CFO lens:** Stage 1 is explicitly free → CAC **UNKNOWN**. Stages 2/4 have **RON service prices** only on VE, not on the 17-step CMS. Stages 12–15 are Marketplace take-rate (D8 5% of `escrow_amount`, DEMO). Stage 17 is recurring EUR if subscribed.

---

# 3. Digital Twin map

## 3.1 What Digital Twin is in code

**Two complementary layers** (already stated in `DIGITAL_TWIN_FORENSIC_AUDIT`):

| Layer | Collections / files | Runtime |
|---|---|---|
| 2D Twin | `twins` — rooms, photos, operator approve (`twin.py`, `OperatorTwin`) | Client submit → `pending_validation` → approved |
| 3D / Professional | `digital_twin_projects`, `digital_twin_models`, `digital_twin_pins`, `digital_twin_comments` | Upload GLB/GLTF/SKP/…; PDF plans; pins/comments; AI Q&A; concept inference; validation `inferred→in_review→verified` |

Module docstring still says subscription = `digital_twin_pro` (legacy). **Runtime gate:** `F_DIGITAL_TWIN_ADVANCED` for **advanced** features; **ingest/version own model is not Premium-blocked** (`_ensure_dt_ingest_access`).

## 3.2 What it can keep

3D files, PDF plans (floorplan/section/…), pins, comments, collaborators, model metadata (`confidence`, `verification`, `source`, status, visibility), optional `property_id` + `property_link_status`, SketchUp/Trimble **URL** (validated host), AI concepts, issue reports.

## 3.3 What it cannot keep (as a unified store)

Legal BIM authoring, live LiDAR capture, Matterport pipeline, automatic warranty/invoice ledger (those live in `property_documents`), Marketplace job money, HH scores (separate `hh_*`).

## 3.4 Answers

| # | Question | Answer |
|---|---|---|
| 1 | What is it? | Project container + models + 2D twin, not a single physics BIM. |
| 2 | Can store | See 3.2 |
| 3 | Cannot store | Native LiDAR/Matterport/BIM toolchain; fiscal e-Factura (`docs_evidence_missing`) |
| 4 | History? | Model statuses include `superseded`/`archived`; P1 metadata. Not a full property timeline engine. |
| 5 | Versioning? | **PARTIAL** — superseded/archive + ingest versioning intended; not a git-like BIM. |
| 6 | Project? | `digital_twin_projects` **is** the 3D project. `db.projects` (demo milestones) is **another** thing. |
| 7 | Property? | Optional `property_id`; backfill/unresolved link exists. **PARTIAL.** |
| 8 | Marketplace? | Verified concept can spawn `requests`. Not required for ordinary jobs. |
| 9 | House Health? | HH eligibility wants an active twin; publish uses `twin_project_id`. **PARTIAL.** |
| 10 | Maintenance? | Calendar is separate; passport reads maintenance for trust. No auto-sync to 3D. |
| 11 | Documents? | Vault is separate; plans are DT PDFs. Vault can `related_model_id`. **PARTIAL.** |
| 12 | Verified Estate? | VE sells **twin_ron** as a **service price**; not the same checkout as DT entitlement. |
| 13 | UI only | LiDAR 48h (`PublicDemoPage`), BIM/Matterport marketing, “scanăm noi” on 17-step page |
| 14 | Real runtime | Upload, convert (Blender/CloudConvert), viewer, pins, operator queues, entitlement 402 |

**LiDAR / Matterport:** marketing + old docs (iframe whitelist). **Not** a capture service in `digital_twin.py`.

---

# 4. Property Memory map

**Do not create a Property Memory Engine.** GI-5P named it; code did not unify it.

| Fragment | Where | Can correlate via |
|---|---|---|
| Works / interventions | `requests` + status/confirm | `property_id` |
| Documents / invoices / warranties / contracts | `property_documents` (`factura`, `garantie`, warranty_end) | `property_id` |
| Specialists | `specialist_id` on requests; trusted_specialists; reviews | client + property |
| Materials / equipment | PI asset slots; DT pins; vault notes | **PARTIAL** |
| Maintenance | `maintenance_tasks` | `property_id` |
| Photos before/after | request photos; twin photos; vault | Dispersed |
| Audits | HH evaluations; VE orders; interior leads | Different IDs |
| Projects | DT projects; design phases; demo `projects` | **Overlapping names** |
| Property changes | DNA / PI maturity; value_loop on confirm | `property_id` |

Conceptual correlation key already exists: **`property_id`**. Missing is a single read-model, not a new writer engine.

---

# 5. Property Intelligence map

| Function | Source | Runtime | Trigger | Output | Consumer |
|---|---|---|---|---|---|
| Maturity L0–L5 | `property_intelligence.refresh_maturity` | Yes | GET `/properties/{id}/maturity` | Level + gaps | Client/admin PI UI |
| Asset registry | `asset_slots` / POST assets | Yes | Owner/admin | Slots + source grade | PI API |
| Health decay | `apply_health_decay` | Yes | Revenue hunter / jobs | Updated health fields | Hunter, properties |
| Predictive candidates | `detect_predictive_candidates` | Yes | Hunter | Suggested works | Opportunities |
| PVI | `value_loop.compute_pvi` | Yes | Confirm, DNA view | Score + history | Confirm response, DNA, command center |
| HH recommendations | `hh_recommendations` | Yes | After evaluation | Recs; optional MP publish | Client HH UI |
| HH score | `hh_scores` | Yes | Evaluations | Score | HH dashboard |
| Passport trust | `property_passport._trust_score` | Yes | Public page | 0–100 + badges | Public / OG |
| Expiry / warranty | vault `warranty_end` + events | Yes | Upload | `warranty.registered` | Passport, lists |
| Alerts | notify + hunter + calendar tick | Partial | Various | Notifications | Users |
| Valuation / sale readiness | VE listing + trust copy | Partial | VE/sell pages | Listing, not AVM | Public VE |
| Specialist recs | HH publish + matching | Partial | Publish / match | Requests / match list | Marketplace |
| GI-5P Memory/Graph | Markdown only | **No unified engine** | — | — | Strategy |

`F_PROPERTY_INTELLIGENCE` is **CONFIGURED BUT UNUSED** on these routes (D9).

---

# 6. Audit taxonomy

These are **different products**. The word “audit” is overloaded.

| | A. Energy / Building / Technical | B. Design / Renovation / Documentation | C. Digital Twin “audit” | D. Verified Property / RE |
|---|---|---|---|---|
| What it is | Promised instrumental diagnostics (IR, humidity, MEP) in **interior CMS**; HH evaluations; building health score | Interior design process + vault completeness | Operator/professional **model validation** | VE `audit_ron` + listing diligence |
| Input | Property, site visit (promised) | Brief, photos, plans | Uploaded model/photos | Seller order, docs |
| Process | **Copy** + HH eval workflow | Content + design module | Queue `in_review` | VE checkout + admin |
| Human | Promised specialist | Designer / PM | Operator / architect | VE operator |
| Tools | Promised IR etc. **not in repo as devices** | Design AI, phases | Viewer, Blender convert | Stripe VE, settings |
| Output | Report (promised); HH recs | Concept, plans, leads | `verified` model | Paid order, listing, sale |
| Price | VE default **2400 RON** (settings/env); 17-step audit **unpriced** | Personalized; design phases | Inside twin_ron **15000 RON** VE or HH Premium | `audit_ron` + `twin_ron` + `commission_pct` |
| Marketplace | Recs can publish | Implementation = MP | Concept→request | Separate product |
| Twin | “Base for Twin” in copy | Uses Twin optionally | **Is** Twin QA | Twin sold as add-on |
| History | HH + vault | Design + requests | Model status | VE orders |

**Admin `design_audit`:** UX scores for landing pages — **not** a property audit.

**App.js / Passport disclaimers:** not a legal energy certificate / expertiză tehnică.

**CFO:** Do not book 17-step “audit” revenue as VE `audit_ron` or HH 79.

---

# 7. 79 EUR reconstruction

| Item | Evidence |
|---|---|
| Where | `DEFAULT_PLANS` Premium `price_eur: 79.0`; checkout reads DB |
| Plan | `hh_plans.slug=premium` → tier `CLIENT_PREMIUM` |
| Promises | Seed features: unlimited twins, storage, evals, Twin Orchestrator, marketplace lead 5%, phone CSM |
| Entitlements | Inherits FREE+BASIC+PRO + DT advanced + PI + portfolio **flags** |
| Checkout | `POST /api/house-health/checkout-session` amount=`price_eur` EUR |
| Payment | Stripe one-shot (no DEMO short-circuit); activate `hh_subscriptions.active` + 30 days monthly |
| After pay | Entitlement refresh; HH basic + DT advanced **enforced**; PI/portfolio **not** route-enforced |
| Expires | `expires_at` |
| Renew | Pay again (not Stripe Subscription) |
| Trial | `trial_days: 14` **UI only** |
| Enforced benefits | HH 402, DT advanced 402, storage tier bump **PARTIAL** |

**CFO:** Recurring only if customers actually pay and renew. Take rate **UNKNOWN**. Cost-to-serve (storage, convert, support) **UNKNOWN**. Promise of CSM / unlimited evals = **uncovered** if sold as-is.

---

# 8. 249 EUR reconstruction

| Question | Finding |
|---|---|
| SKU? | **No** distinct slug |
| Plan? | Intended as Premium / Property Intelligence **price**, not a new product in seed |
| Marketing? | PRD Task 3; founder screenshots; **not** hardcoded in `PricingPage.jsx` |
| Checkout? | Only if `hh_plans.premium.price_eur=249` in **that environment** (UNKNOWN here) |
| Entitlement? | Same `CLIENT_PREMIUM` as 79 |
| DB seed? | **79**, not 249 |
| Runtime enforcement? | Same as §7 |
| Stripe Price ID? | Optional auto-provision unused by checkout |
| Subscription? | Same one-shot HH |
| Service fulfillment? | **None** beyond software gates — 249 does not dispatch LiDAR or audit crews |

**Missing if 249 is meant as a professional bundle:** crew, SLA, VE-like RON pricing, or a separate slug.  
**Do not auto-convert 249 into a subscription** — evidence only supports “Premium EUR price,” not a new fulfillment SKU.

Related **other** prices: VE twin **15000 RON**, audit **2400 RON** — do not equate to 249 EUR.

---

# 9. Economic model

| Model | Exists? |
|---|---|
| **A. SaaS subscription** | **Yes** — HH `hh_plans` / `hh_subscriptions` |
| **B. Professional service** | **Yes** — VE audit/twin RON; interior leads (often unpriced); DT operator labor |
| **C. Marketplace commission** | **Yes** — D8 `* 0.95` at confirm (implicit) |
| **D. Transaction fee** | Same as C + Stripe fees **UNKNOWN** incidence |
| **E. Recurring service** | HH if renewed; maintenance calendar **not** billed per task |
| **F. Financing / installment** | **PARTIAL** — design `phases` pay; D7 no Marketplace installment engine; **no** consumer financing product |
| **G. Hybrid SaaS + service** | **Positioned** (17 steps + HH + VE); **not** one checkout |
| **H. Property documentation service** | Vault + completeness — **software**; paid only via HH/storage or VE |
| **I. Verified Property service** | **Yes** — VE listing + commission on sale |

Do **not** pick the “correct” model. The repo **already runs several**.

---

# 10. Marketplace economic health (no 3-request cap)

Founder: unlimited **real, relevant** requests. Analyze hygiene, not a quota engine.

| Funnel | Current | Economic risk | Existing protection | Missing (do not build now) |
|---|---|---|---|---|
| Spam / fake / duplicate requests | Unlimited create | Specialist attention; notify blast on create | Auth + owned property; offer self-deal block | Rate/quality **UNKNOWN** |
| Abandoned `open` | Stays open | Noise in specialist list | — | Expiry policy |
| Low quality | Free-text create | Wasted Lead Credits (D2 on submit) | Credits/apply fee **on specialist**, not client | Client cost-to-post = ~0 |
| Lead Credit waste | Specialist pays to offer | Specialist CAC | 5–50 / 45 credits | — |
| request→offer | Flag-gated B; live often A `/accept` | Conversion **UNKNOWN** | — | — |
| offer→selection | `accept_offer` | D6 | — | — |
| selection→execution | `/start` ungated | Unpaid work (D7) | — | — |
| execution→payment | Pay optional | Confirm can pay 0 | — | — |
| payment→payout | Confirm 95% wallet | DEMO money | Status≠completed blocks re-confirm | Race on confirm |

**Protect health without blocking the client:** specialist-side participation cost (already), ranking, request quality signals, specialist mute/report — **reuse**, don’t cap volume.

**CFO:** Client-side free posting = high liquidity, **cost-to-serve and specialist burnout UNKNOWN**. Monetize via jobs (D8), HH, VE — not by rationing requests.

---

# 11. Client verification model

Do **not** create `CLIENT VERIFIED`.

| Signal | Classification |
|---|---|
| Account email/password or Google | **SELF_ASSERTED** identity (Google email not always `email_verified`) |
| `email_verified` | **DOCUMENTED** process; **not** Marketplace-enforced |
| Property `owner_id` | **SELF_ASSERTED** ownership |
| Uploaded vault docs | **DOCUMENTED** (files exist); **EVIDENCED** if `official_document` / verified status |
| Passport / PI source | **EVIDENCED** (scored); not legal **VERIFIED** |
| Twin operator approve | **EVIDENCED** / operator **VERIFIED** for that twin |
| Marketplace history / offers / D6 / confirm | **EVIDENCED** behavior |
| Specialist confirmation `/complete` | **SELF_ASSERTED** by specialist |
| Client `/confirm` | **SELF_ASSERTED** acceptance |

Platform **VERIFIED** as a composed client state: **UNKNOWN / absent**.

---

# 12. Verified Property / sale model

**Can documentation become a sale-trust product today?**  
**PARTIAL — yes, as Verified Estate + Passport, not as auto-listing from the vault.**

Mechanisms:

- `verified_estate.py` listings, public browse, `GET /pricing` audit+twin+commission  
- Twin cost deducted from sale commission (copy + calculator)  
- `PublicPassportPage` trust score + badges (disclaimer: not legal energy cert)  
- Vault completeness + warranties  
- HH/PVI as “house story” **not** wired as listing requirement  

Closest unused glue: `property_id` shared across vault, twin, passport, VE listing.

---

# 13. Existing components to reuse

`properties`, `property_documents`, `twins`, `digital_twin_*`, `property_intelligence` + PVI, `value_loop`, `property_passport`, `hh_*`, `entitlements`, `requests`/`marketplace_offers`, `maintenance_tasks`, `verified_estate`, `reviews`, `activity_events`, interior `process_phases` **as content**, design `phases` as staged pay **pattern**.

---

# 14. Duplicates / overlaps

| Collision | Systems |
|---|---|
| “Twin” | `twins` vs `digital_twin_projects` vs VE `twin_ron` vs HH “twin included” copy |
| “Audit” | CMS technical audit vs VE audit vs HH eval vs admin UX audit |
| “Project” | DT project vs demo `projects` vs Marketplace request vs design phases |
| “Premium / 5%” | HH lead 5% vs D8 job 5% vs VE commission % |
| “Verified” | Specialist KYC, twin model verified, VE listing, passport badges |
| Pricing | HH EUR vs VE RON vs unpriced 17-step modules |
| Intelligence | `property_intelligence.py` vs `ai_brain/product_intelligence.py` vs GI-5P |

---

# 15. Missing links

- 17-step orchestrator  
- LiDAR/Matterport fulfillment  
- Property Memory read API  
- `F_PROPERTY_INTELLIGENCE` on PI routes  
- Trial grant  
- 249 SKU  
- Twin write-back from every job (only confirm value_loop **PARTIAL**)  
- Financing  
- Client spam controls (by design: no volume cap)  
- e-Factura  

Missing **link** ≠ permission to build an engine.

---

# 16. Contradictions

- 17 steps “we scan” vs DT **owner upload** vs demo **LiDAR 48h**  
- Seed Basic “1 Twin inclus” vs DT advanced = Premium flag  
- `upgradeNudge` DT → Pro vs entitlements Premium  
- Module docstring `digital_twin_pro` vs entitlements  
- Premium 79 seed vs 249 PRD  
- Trial UI vs paid+30  
- Passport “not energy audit” vs CMS “eficiență energetică” in step 2  
- HH “marketplace commission 5%” vs D8 job 5%  

---

# 17. UNKNOWNs

Target DB `premium.price_eur`; live Stripe charges; LTV/CAC/conversion/take rate; cost of convert/storage/operator minutes; whether anyone bought VE audit/twin; 17-step close rate; spam rate; whether 249 is advertised live.

---

# 18–22. Risks (lenses)

**Commercial:** Selling 17-step / LiDAR / CSM / trials / 249 without fulfillment; mixing VE RON with HH EUR in the customer’s head.  
**Architecture:** New Memory/OS would duplicate `property_id` fragments.  
**Product:** Journey promised, modules optional, no conductor.  
**Trust:** Asserted ownership + “Verified” overload.  
**Security:** Unlimited requests + notify-all specialists; DT files; client `/escrow` amount (D7); confirm race (D8).

---

# 23. Founder decisions required

1. Are the **17 stages** a **narrative** (KEEP as CMS) or a **product to orchestrate** later?  
2. Is **249** a **price change** on `premium`, a **second SKU**, or a **professional bundle** (closer to VE RON)?  
3. What is sold at **79** vs VE **2400/15000 RON** — do not merge in copy.  
4. Marketplace stays **uncapped** (accepted here) — which **hygiene** (not quota) is acceptable?  
5. Trial: stop advertising or grant later.  
6. Is “Digital Twin” software access, a **scan service**, or both (two prices)?  

Do not decide these in code.

---

# 24. Recommended next audit

**D9.6 — Fulfillment vs narrative:** map each 17-step CTA to an **exact** route or `NOT CONNECTED`, plus a **price-list inventory** (HH EUR, VE RON, design phases, Marketplace escrow) so sales cannot quote the wrong engine.

Optional later: target-env read of `hh_plans.premium.price_eur` (no change).

---

# Final architecture arrows (do not assume they exist)

```
PROPERTY
→ PROPERTY DOCUMENTATION     PARTIAL (vault; create property has no docs)
→ DIGITAL TWIN               PARTIAL (optional property_id; 2D + 3D)
→ PROPERTY MEMORY            PARTIAL / UNKNOWN as a product (fragments only)
→ PROPERTY INTELLIGENCE      PARTIAL (PI + PVI + HH; unused flag)
→ AUDITS / HEALTH / MAINT.   PARTIAL (several “audits”; calendar separate)
→ PROJECTS                   CONTRADICTED names (DT vs demo vs request)
→ MARKETPLACE                PARTIAL (request.property_id; Twin/HH optional)
→ EXECUTION                  SUPPORTED (request spine)
→ VERIFICATION               PARTIAL (many meanings)
→ PROPERTY HISTORY           PARTIAL (confirm loop, vault, PVI)
→ VERIFIED PROPERTY / SALE   PARTIAL (VE + passport; not auto from memory)
```

---

**No implementation performed.**  
**STOP.**
