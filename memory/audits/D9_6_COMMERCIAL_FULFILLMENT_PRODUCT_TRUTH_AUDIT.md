# D9.6 — COMMERCIAL FULFILLMENT + PRODUCT TRUTH AUDIT

**Mode:** READ-ONLY. No implementation, DB, pricing, UI, products, SKUs, entitlements, commit, or deploy.  
**Date:** 2026-09-23  
**Given:** D9.5 reconstruction, D9/D11, commercial economy audits.  
**Rule:** Marketing copy is not runtime evidence.

**No implementation performed.**  
Costs, margins, and live conversion not in ledgers = **UNKNOWN**. No invented estimates.

---

# How to read STATUS

| Tag | Meaning |
|---|---|
| **MARKETING_ONLY** | Copy / cards / modal. No dedicated runtime for that step. |
| **RUNTIME** | Code executes a customer-visible function for that object. |
| **PARTIAL** | A nearby runtime exists; it is not the promised product. |
| **NOT_CONNECTED** | CTA or promise does not land on a fulfillment path for that promise. |

---

# 1. The 17 stages

**Canonical commercial text:** `backend/service_content_design.py` → `process_phases`.  
**Pages that render it:** `/design-interior` (`InteriorDesignLanding.jsx` `#proces`), `ServiceHubLanding.jsx`, `ServiceDetailModal` kind=`process`, `SellMyProperty.jsx` “Vezi toate cele 17 etape”.  
**Guardian:** `journey_guardian.py` asserts **step count = 17** (content integrity, not a job state machine).

**There is no per-step CTA.** Steps 1–17 are cards. CTAs on the same page are **page-level**:

| CTA | Lands on |
|---|---|
| Hero: Solicită proiect / Cere ofertă / Consultanță designer | `#formular` LeadForm → `POST /interior-design/leads` → `interior_design_leads` |
| Vezi tot ce conține Digital Twin | `ServiceDetailModal` kind=twin → primary “Solicită Digital Twin” → **same lead form** |
| Află tot ce include Auditul | modal audit → “Solicită Audit” → **same lead form** |
| Pornește procesul | `#formular` |
| Vezi Imobilele Verificate | `/imobile-verificate` |
| LiDAR “Programează vizita” (`PublicDemoPage`, `LandingDemo3D`) | **`/register`** — not a scan booking |

---

## Stage-by-stage

### 01 — Consultanță inițială · Faza Descoperire

| Field | Evidence |
|---|---|
| Text | „Discutăm obiectivele, stilul de viață, bugetul și termenele. **Prima discuție este gratuită.**” |
| Page / CTA | `/design-interior` · „Programează consultanța gratuită” |
| Route / API | `POST /interior-design/leads` |
| DB | `interior_design_leads` |
| Price / payment | **Free** (copy). No checkout. |
| Fulfillment | Human sales — admin list `GET /admin/interior-design/leads` + PATCH status. **No calendar, no SLA runtime.** |
| Output | Lead row |
| DT / Memory | None |
| Marketplace | None |
| **STATUS** | **PARTIAL** — intake is RUNTIME; the conversation is HUMAN, untracked as a stage. |

### 02 — Audit tehnic al locuinței

| Field | Evidence |
|---|---|
| Text | „Evaluăm starea reală: instalații, structură, riscuri, eficiență energetică și posibilități de recompartimentare.” Plus long-form: IR, umiditate, MEP, raport (`audit.points`). |
| Page / CTA | `#audit` → modal → **lead form** (not VE checkout) |
| Nearby products | VE `package=audit` default **2400 RON** (`VE_PRICE_AUDIT_RON` / `app_settings.pricing.audit_ron`); HH evaluations; `ghiduri.js` 48h report copy |
| Price | 17-step: **unpriced**. VE: 2400 RON. Junior dashboard: „de la RON 1.500” (another number). |
| Payment | Lead: none. VE: Stripe/DEMO `verified_estate_orders`. |
| Fulfillment | **No IR/humidity/device pipeline in repo.** Operator/admin after paid VE order → draft listing. HH eval is software questionnaire, not field audit. |
| DT / Memory | Promised as Twin base. VE draft listing `gates` want `audit_report_id` — IDs start empty. |
| Marketplace | HH recs can publish later — not this step. |
| **STATUS** | **PARTIAL** — three “audits”; 17-step CTA is **MARKETING + lead**. Field instruments = **UNSUPPORTED**. |

### 03 — Ridicare măsurători

| Field | Evidence |
|---|---|
| Text | „Releveu precis al spațiului — baza oricărui proiect corect.” |
| CTA / API / price | **None dedicated** |
| Nearby | DT PDF plans; 2D twin rooms; tape measure in **Premium** viewer |
| Fulfillment | Promised surveyor — **no booking object** |
| **STATUS** | **MARKETING_ONLY** / **NOT_CONNECTED** |

### 04 — Scanare Digital Twin

| Field | Evidence |
|---|---|
| Text | „**Scanăm locuința** și construim copia ei digitală — mult mai mult decât un model 3D.” |
| CTA | Twin modal → lead form. Demo LiDAR → `/register`. |
| Runtime | **Owner upload** GLB/SKP/… (`digital_twin.py`). 2D `twins` submit. VE `package=twin` **15000 RON**. |
| Scan / LiDAR / Matterport | **MARKETING ONLY** (no ingest, no crew dispatch). |
| **STATUS** | **PARTIAL** — software ingest RUNTIME; „scanăm noi în 48h” **NOT_CONNECTED**. |

### 05 — Model 3D al proprietății

| Field | Evidence |
|---|---|
| Text | „Modelul tridimensional exact al spațiului…” |
| Runtime | `digital_twin_models` + viewer; Blender/CloudConvert subset; SKP download-only |
| Eligibility | Ingest: any authenticated owner. Advanced pins/QA: `F_DIGITAL_TWIN_ADVANCED` = **Premium** (code). UI lock screen says **„Pro și mai sus”** — **contradiction**. |
| Price | Software via HH Premium 79; service via VE 15000 RON; 17-step unpriced |
| **STATUS** | **RUNTIME** (upload/view) · fulfillment of „exact architectural model by us” = **PARTIAL / SERVICE missing** |

### 06 — Planșe tehnice

| Field | Evidence |
|---|---|
| Text | „Planuri de arhitectură, instalații și detalii de execuție…” |
| Runtime | PDF `PLAN_TYPES` on DT project — store, not CAD authoring |
| BIM | Capability editor mentions BIM/IFC/Matterport as **compatibility labels**. No BIM authoring. |
| **STATUS** | **PARTIAL** (PDF store) · BIM authoring **UNSUPPORTED** |

### 07 — Arhitectură de interior

| Text | „Recompartimentare, circulații, funcțiuni…” |
| Nearby | Interior assistant / concept inference from Twin; design module |
| Price | Personalized / lead |
| **STATUS** | **PARTIAL** |

### 08 — Design interior

| Text | „Concept, moodboard, randări 3D fotorealiste…” |
| Nearby | Design landing, `DesignLeadModal`, design `phases` staged pay (sibling product) |
| **STATUS** | **PARTIAL** — lead + design studio ≠ promised photoreal SLA |

### 09 — Alegerea materialelor

| Text | Finisaje / durabilitate / buget |
| Nearby | City partner products as **indicative** prices on DT concepts |
| **STATUS** | **PARTIAL** / mostly **MARKETING_ONLY** |

### 10 — Soluții tehnice

| Text | „Iluminat, HVAC, smart home, acustică — integrate de la început…” |
| Nearby | Viewer X-Ray marketing; PI asset slots |
| **STATUS** | **MARKETING_ONLY** as a sold stage · PI slots **PARTIAL** |

### 11 — Bugetare

| Text | „Buget detaliat pe capitole, cu alternative pe 3 niveluri…” |
| Nearby | No 3-tier budget engine found |
| **STATUS** | **NOT_CONNECTED** |

### 12 — Management implementare

| Text | „Un singur punct de contact care orchestrează furnizori, comenzi și echipe.” |
| Nearby | Marketplace request + design phases PM |
| **STATUS** | **PARTIAL** — jobs exist; not a dedicated PM SKU |

### 13 — Coordonare echipe

| Text | „Specialiști verificați din rețea, selectați prin cereri de ofertă comparate transparent.” |
| Runtime | `requests` + `marketplace_offers` (D1 Model B gated; live often Model A `/accept`) |
| Payment | DEMO checkout optional; D8 5% at confirm |
| **STATUS** | **RUNTIME** (Marketplace) — not bound to „step 13” |

### 14 — Verificarea execuției

| Text | „Controale de calitate pe fiecare etapă, documentate în platformă.” |
| Nearby | `/complete`, photos, disputes; demo `projects.milestones` |
| **STATUS** | **PARTIAL** — no QA checklist product |

### 15 — Recepția lucrării

| Text | „Recepție formală cu punctaj… se închide doar când e conformă cu proiectul.” |
| Runtime | Client `/confirm` — **self-asserted**, not a scored conformity gate |
| **STATUS** | **PARTIAL** |

### 16 — Actualizarea Digital Twin

| Text | „Tot ce s-a executat intră în copia digitală: materiale, instalații, garanții, fotografii.” |
| Runtime | `value_loop.enrich_on_closure` on **confirm**: warranty row, bounded health bump, twin event, PVI — **not** a full 3D model rewrite |
| **STATUS** | **PARTIAL** |

### 17 — House Health

| Text | „Monitorizare și întreținere planificată — locuința rămâne sănătoasă, iar tu ai istoricul complet.” |
| Runtime | `hh_*`, evaluations, recs, optional publish→request, `/pricing` checkout |
| Price | Seed Basic 9 / Pro 29 / **Premium 79** EUR |
| **STATUS** | **RUNTIME** (SaaS) — not „step 17 of a job”; trial **UI-only** |

---

# 2. Product truth (promise → evidence → runtime → fulfillment)

| PROMISE | EVIDENCE | RUNTIME | FULFILLMENT | Class |
|---|---|---|---|---|
| Un singur proces 17 etape, zero improvizație | CMS + guardian count | Cards only | None as orchestrator | **UNSUPPORTED** as product |
| Prima discuție gratuită | Copy + lead form | Lead insert | Human, unscheduled | **PARTIAL** |
| Audit instrumental (IR, umiditate, MEP) | CMS `audit.points`, ghiduri 48h | VE order + HH eval + lead | No device/report pipeline | **UNSUPPORTED** (instruments) · VE pay **PARTIAL** |
| Scanăm locuința / LiDAR 48h | CMS + `/demo` + App.js | Upload + `/register` CTA | No LiDAR job | **UNSUPPORTED** |
| Twin = BIM + instalații + istoric + garanții | `digital_twin.contains[]` | 2D+3D files, vault/warranties **separate** | Modular note admits config | **PARTIAL** |
| Planșe de execuție pe care lucrează echipele | CMS | PDF upload | Not authored CAD | **PARTIAL** |
| Randări fotorealiste | CMS step 8 | Design/AI concepts | No render farm | **UNSUPPORTED** / UNKNOWN if out-of-band |
| Buget 3 niveluri | CMS step 11 | — | — | **UNSUPPORTED** |
| Escrow protejează plățile (positioning badges) | Copy | `escrow_status` marker; DEMO Stripe | Not Stripe custody (D7) | **PARTIAL** / **UNSUPPORTED** as bank escrow |
| Specialiști verificați + oferte transparente | Step 13 | Offers island + `/accept` | Model B default off | **PARTIAL** |
| Recepție cu punctaj de conformitate | Step 15 | `/confirm` | Self-asserted | **UNSUPPORTED** as scored reception |
| Tot ce s-a executat intra în Twin | Step 16 | value_loop on confirm | Metadata, not 3D rebuild | **PARTIAL** |
| House Health = istoric complet + monitorizare | Step 17 + plans | HH module | Software; CSM promised on Premium | **PARTIAL** |
| Trial 14 zile | `trial_days` on plans | Display | Not granted | **UNSUPPORTED** |
| Premium: Twin unlimited, storage unlimited, CSM, lead 5% | seed `features[]` | DT advanced + HH 402; storage **PARTIAL**; CSM **none**; lead 5% ≠ D8 job 5% | Software gates only | **PARTIAL** |
| DT Advanced inclus în **Pro** | `DigitalTwinPage.jsx` lock copy | Entitlements: **Premium only** | — | **CONTRADICTED** |
| Imobil listat doar după 4 gates (audit, twin, 90% recs, admin) | `WhyUsPage` FAQ | `_evaluate_gates` + publish filter | Draft after pay starts with **empty IDs** | **PARTIAL** (gates exist; auto-pass **not** proven) |
| Comision vânzare 2.5%; twin scăzut din comision | WhyUs / EstateBrowse | `commission_pct` settings + calculator copy | Live default **UNKNOWN** (code has configurable %) | **PARTIAL** |
| 7–10 zile / express 3–4 zile audit+twin | WhyUs FAQ | — | No SLA object | **UNSUPPORTED** |
| „Fără abonament” pe design landing | Lead form footer | True for leads | Conflicts with HH 79 sell | **PARTIAL** (different products) |

---

# 3. Digital Twin fulfillment

| Capability | Class | Runtime evidence |
|---|---|---|
| **2D** | SOFTWARE | `twins` rooms/photos, operator `pending_validation` → approved |
| **3D** | SOFTWARE | `digital_twin_projects/models/pins/comments`; viewer |
| **Scanare** | MARKETING ONLY | No capture job |
| **LiDAR** | MARKETING ONLY | CTA → `/register` |
| **Matterport** | MARKETING / EXTERNAL TOOL (old iframe whitelist, futureIdeas) | Not a pipeline |
| **BIM** | MARKETING + UI label | Viewer „BIM-style”; no IFC authoring |
| **Instalații** | PARTIAL SOFTWARE | Layers/X-Ray if in model; not auto-mapped MEP |
| **Measurements** | SOFTWARE (advanced) | Tape in Premium viewer; not survey deliverable |
| **Plans** | SOFTWARE | PDF store |
| **Conversion** | SOFTWARE + EXTERNAL TOOL | Blender/CloudConvert subset; SKP URL Trimble |
| **Operator workflow** | HUMAN FULFILLMENT | `OperatorDigitalTwin`, 2D approve, model `in_review`→`verified` |
| **QA / verification** | SOFTWARE + HUMAN | Status enums; operator |
| **Delivery** | SOFTWARE | Viewer / download. Crew delivery **MISSING** |

**Two commercial objects named Twin:** HH entitlement (EUR) vs VE `twin_ron` (RON service). 17-step copy is a **third**, unpriced.

---

# 4. 79 EUR

```
PROMISE (seed Premium features + PI badge on pricing)
  → PAYMENT  POST /api/house-health/checkout-session  amount = hh_plans.price_eur (seed 79)
  → ACTIVATION  hh_subscriptions.status=active + expires_at ≈ +30 days  (one-shot, not Stripe Subscription)
  → ENTITLEMENT  CLIENT_PREMIUM → DT advanced + PI + portfolio flags (inheritance via _resolve_features)
  → RUNTIME  HH 402, DT advanced 402; PI routes NOT gated by F_PROPERTY_INTELLIGENCE (D9)
  → FULFILLMENT  software only — no LiDAR, no CSM ticket, no unlimited-eval crew
  → EXPIRY  expires_at
  → RENEWAL  pay again
```

**Contradictions**

1. Seed **79** vs PRD/founder **249** (same slug).  
2. `trial_days: 14` advertised, **not granted**.  
3. Plan copy: Twin included on Basic/Pro vs entitlements **Premium-only** advanced DT.  
4. Lock UI: „Pro și mai sus” vs code Premium.  
5. `upgradeNudge` maps DT → Pro (D11).  
6. „Comision marketplace lead 5%” vs D8 **job** 5% vs HH publish `lead_commission_pct` snapshot (15/10/5) — **three 5%s**.  
7. CSM / unlimited evals / unlimited storage — **promise > enforcement**.  
8. Pricing page „Property Intelligence” badge vs PI **unenforced**.  
9. Checkout can be blocked if Stripe DEMO (economy audit).  
10. Manual tester still expects „Premium 79€” cards.

---

# 5. 249 EUR — do not create

| Question | Finding |
|---|---|
| Where | `memory/PRD.md` Task 3; founder screenshots in prior audits; **not** in `PricingPage.jsx`; **not** in seed |
| Promises | Same Premium card **if** env `price_eur=249` — UNKNOWN here |
| Looks like | Price change on `slug=premium`, **or** a professional bundle people confuse with VE RON |
| Fulfillment if sold as SaaS | Same as §4 — software gates |
| Fulfillment if sold as „Property Intelligence + Twin + audit” | Would need VE-like crew + SLA — **not in 249** |
| Ops cost | UNKNOWN (no SKU, no hours) |
| Existing components that could support a **software** 249 | `hh_plans` overwrite, same checkout, same entitlements |
| Existing components that could support a **service** 249 | VE orders, operator Twin, vault, HH — **still no crew dispatch** |
| Missing | Distinct slug, fulfillment SOP, cost model, demo filter, trial policy |

**Do not decide the price. Do not create a SKU.**

Related prices (do not equate): VE audit **2400 RON**, twin **15000 RON**, Junior „de la 1500 RON”, HH 9/29/79 EUR.

---

# 6. Verified Property

```
AUDIT (promised field) → DOCUMENTATION (vault) → DIGITAL TWIN (2D/3D)
  → VERIFICATION (gates + admin) → PASSPORT (public trust score)
  → LISTING (published) → BUYER TRUST (FAQ + badges)
```

| Step | Marketing claim | Actual runtime |
|---|---|---|
| Audit | Accredited specialists, 7–10 days, IR | VE checkout → `verified_estate_orders`; draft listing; `audit_report_id` **empty at create** |
| Documentation | Complete technical file | `property_documents` optional; not auto-required for publish in this pass beyond gates IDs |
| Digital Twin | Mandatory 3D tour on every listing | Gate 2 wants `digital_twin_id`; paid twin package does not auto-attach a scanned model |
| Verification | 4 obligatory gates + 90% recs | `_evaluate_gates`; public list = published + gates + admin. **Enforcement quality UNKNOWN** without live listings |
| Passport | Trust 0–100, disclaimer ≠ legal energy cert | `property_passport` RUNTIME |
| Listing | Browse `/imobile-verificate` | `GET /listings` published only |
| Buyer trust | „100% cu Digital Twin”, 2.5% commission | Copy + configurable `commission_pct`; twin deducted **in calculator copy** |

**Can documentation raise sale trust today?** **PARTIAL** — Passport + VE listing machinery. **Not** automatic vault→verified listing.

---

# 7. Economics (no invented numbers)

| Product | PRICE | REVENUE | DIRECT COST | FULFILLMENT COST | PLATFORM COST | SPECIALIST COST | PAYMENT COST | COMMISSION | MARGIN |
|---|---|---|---|---|---|---|---|---|---|
| 17-step journey | Unpriced / custom | Lead only | UNKNOWN | UNKNOWN | form + notify | UNKNOWN | 0 on lead | — | UNKNOWN |
| Consult lead | 0 | 0 | UNKNOWN | human time UNKNOWN | insert | 0 | 0 | — | UNKNOWN (CAC) |
| VE Audit | 2400 RON default | order if paid !demo | UNKNOWN | field UNKNOWN | Stripe/DEMO | specialist UNKNOWN | UNKNOWN | sale `commission_pct` later | UNKNOWN |
| VE Twin | 15000 RON default | same | UNKNOWN | scan/model UNKNOWN | convert/storage UNKNOWN | operator UNKNOWN | UNKNOWN | twin vs sale calc | UNKNOWN |
| VE Bundle | sum | same | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| HH Premium 79 | 79 EUR seed | if Stripe paid | UNKNOWN | none (software) | storage/convert UNKNOWN | 0 | Stripe UNKNOWN | lead 5% **copy** | UNKNOWN |
| HH 249 | not a SKU | UNKNOWN | — | — | — | — | — | — | UNKNOWN |
| Marketplace job | client escrow | D8 5% of confirm amount | UNKNOWN | 0 platform crew | notify-all | credits 45 / apply fee | DEMO possible | **5%** | UNKNOWN |
| Design phases | per phase | sibling module | UNKNOWN | designer | Stripe/DEMO | designer | UNKNOWN | — | UNKNOWN |

**Reporting:** War Room / EH `real_revenue` see VE !demo. Cockpit sums **all** paid txs (may include DEMO). 17-step revenue **not** a line item.

---

# 8. Property Memory — where a delivered result *can* land

There is **no Memory Engine**. Correlation key: `property_id`.

| Deliverable | property | twin 2D/3D | documents | history | maintenance | passport | verified property |
|---|---|---|---|---|---|---|---|
| Lead (step 1) | no | no | no | admin lead list | no | no | no |
| VE audit order | optional on order | gate ID later | if uploaded | order row | no | if health/docs | draft listing |
| HH evaluation | yes | eligibility mentions twin | recs | `hh_evaluations` | recs→calendar PARTIAL | health component | not auto |
| Uploaded 3D/PDF | `property_id` optional | **yes** | plans on DT; vault `related_model_id` PARTIAL | model status | no | twin badge PARTIAL | gate 2 if ID set |
| Marketplace confirm | yes | value_loop event **PARTIAL** | warranty row | request + PVI | no auto task | trust inputs | no auto listing |
| Vault invoice/warranty | yes | no auto | **yes** | events | warranty_end | **yes** | not auto |
| Photos before/after | request/twin/vault | if uploaded | if uploaded | dispersed | no | if in vault | if on listing |
| Passport page | yes | reads twin | reads vault | events | reads tasks | **is** the page | public trust, not listing |

---

# 9. Final table

| PROMISE | PRODUCT | RUNTIME | FULFILLMENT | MONEY | DATA | MEMORY | STATUS |
|---|---|---|---|---|---|---|---|
| 17-step OS | Interior CMS | Cards + guardian count | None | Unpriced | `interior_design_content` | no | MARKETING_ONLY |
| Free consult | Lead | `interior_design_leads` | Human unscheduled | 0 | lead | no | PARTIAL |
| Technical audit | CMS / VE / HH | Lead **or** VE pay **or** HH eval | Field tools MISSING | 2400 RON **or** 0 **or** HH | orders / evals | PARTIAL | PARTIAL · instruments UNSUPPORTED |
| Survey | Copy | — | — | — | — | — | NOT_CONNECTED |
| We scan / LiDAR | Demo + CMS | `/register` | — | — | — | — | NOT_CONNECTED |
| Digital Twin software | DT 2D+3D | Upload, viewer, operator QA | Owner/operator | HH 79 and/or VE 15000 | twins, digital_twin_* | PARTIAL | RUNTIME + SERVICE gap |
| Plans / BIM | PDF + labels | PDF | No BIM | — | plans | PARTIAL | PARTIAL |
| Design 7–11 | Leads + design module | Partial | Custom | Quote | leads / phases | PARTIAL | PARTIAL |
| Budget 3 tiers | Copy | — | — | — | — | — | NOT_CONNECTED |
| Implement 12–15 | Marketplace | Request spine | Specialists | escrow / D8 5% | requests | value_loop PARTIAL | RUNTIME (not numbered) |
| Twin update | value_loop | On confirm | Metadata | — | warranties, health, PVI | PARTIAL | PARTIAL |
| House Health | HH SaaS | Checkout + module | Software | 9/29/79 | hh_* | evals + recs | RUNTIME |
| Trial 14d | Plan field | Display | None | 0 promised | — | — | UNSUPPORTED |
| Premium 79 | hh_plans.premium | Checkout | Software | 79 seed | subscription | no | PARTIAL vs copy |
| Premium 249 | PRD / env | Same slug IF DB=249 | Same as 79 | UNKNOWN | same | no | NOT A SKU |
| Verified listing | VE | Orders, gates, publish | Admin + promised crew | RON + commission | listings, passport | PARTIAL | PARTIAL |
| Escrow bank | Badge | Status field | DEMO | escrow_amount | requests | — | PARTIAL / UNSUPPORTED |

---

# 10. Risk map

**COMMERCIAL** — Selling a journey the app does not run; LiDAR CTA registers an account; three audit prices (free lead / 1500 / 2400); 79 vs 249; trial; „fără abonament” next to HH.  
**FULFILLMENT** — No crew, SLA, IR kit, or 3-tier budget; operator Twin is upload QA, not scan.  
**FINANCIAL** — VE RON vs HH EUR vs job 5% vs lead 5%; DEMO in Cockpit; all margins UNKNOWN.  
**PRODUCT** — Step cards without step CTAs; lock screen vs entitlements; two Twins.  
**ARCHITECTURE** — Do not add a 17-step engine or Memory Engine; `property_id` already correlates.  
**TRUST** — WhyUs 4 gates vs empty IDs on draft; `/confirm` ≠ scored reception; Passport disclaimer vs energetic-audit copy.  
**SECURITY** — `/register` from LiDAR (account spam); file uploads; VE DEMO orders.  
**DATA** — Lead not attached to `property_id`; Twin link optional; Memory fragments.

---

# 11. Recommendation (no implementation)

| Action | What |
|---|---|
| **KEEP** | 17 stages as **narrative CMS**; DT 2D+3D ingest; VE priced SKUs; HH checkout; Marketplace spine; Passport; value_loop; lead form; gates code; War Room demo split. |
| **CONNECT** (later, Founder-approved) | Twin modal CTA → VE twin checkout **or** DT upload, not only lead; Audit CTA → VE audit **or** honest „call us”; LiDAR CTA → lead/ops, not silent `/register`; confirm → vault/twin write-back already PARTIAL. |
| **REPAIR** | Lock copy Pro vs Premium; trial advertising vs grant; cockpit 10% vs D8 5%; Junior 1500 vs VE 2400. |
| **CONSOLIDATE** | One public meaning of „Audit”, „Twin”, „5%”. One Premium price (79 **or** 249 — **DECIDE**, don’t invent a third SKU). |
| **DEPRECATE** (copy only, don’t delete code) | LiDAR 48h as if scheduled; IR/BIM as included default; „recepție cu punctaj”; bank-grade escrow; CSM until staffed. |
| **DECIDE** (Founder, before any build) | See below. |

### Founder decisions required before implementation

1. Are the **17 stages** a **story** (KEEP) or a product to orchestrate? (D9.5 open.)  
2. **Audit** sold to consumers = VE 2400 RON, HH eval, or unpriced lead — **one** public offer.  
3. **Digital Twin** sold = software access (79/249), VE 15000 RON scan service, or both with **two labels**.  
4. **249** = overwrite Premium, second slug, or not used. **Do not create it in this audit.**  
5. Trial: stop copy or grant later.  
6. LiDAR: stop CTA or define a real booking object (not authorized here).  
7. Verified listing: gates must be true before „100% Twin” copy, or soften copy.  
8. Marketplace stays uncapped (founder) — hygiene ≠ 17-step gate.

**Do not implement a fulfillment engine to close these gaps.** Closest existing objects: `interior_design_leads`, `verified_estate_orders`, `digital_twin_*`, `hh_subscriptions`, `requests`, `property_documents`, `property_passport`.

**STOP.**
