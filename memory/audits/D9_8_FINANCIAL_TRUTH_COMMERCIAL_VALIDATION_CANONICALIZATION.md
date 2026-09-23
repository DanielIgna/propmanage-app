# D9.8 — FINANCIAL TRUTH & COMMERCIAL VALIDATION CANONICALIZATION

**Mode:** READ-ONLY architectural design. No code, schema, pricing, Stripe, Marketplace, dashboard, registry, or Knowledge Center changes. No new engine. No commit. No deploy.  
**Roles (lenses, not runtime agents):** Senior Financial Systems Architect · CTO · Product/Commercial Architect  
**Date:** 2026-09-23  
**Evidence base:** D1–D9.7, repository writers/readers, `propmanage_db` snapshot in D9.7 (2026-09-23T12:43Z).

**Phase (Founder, accepted as context — not a metric):**

```
ONLINE → TRAFFIC → REAL USER INTERACTION → REQUESTS → OFFERS
  → FEEDBACK → SERVICE VALIDATION → ITERATION
```

Not yet: scale · revenue optimization · CAC/LTV · margin optimization · profit.

**Interpretive rules (this document):**

1. Absence of REAL CASH REVENUE is **expected** (Stripe integration incomplete). It is **not** a product failure and **not** a “revenue problem.”  
2. `hh_plans.premium.price_eur = 249` in the inspected DB is a **runtime / pricing hypothesis**. It is **not** a Founder-approved canonical price.  
3. Seed `79` is also **not** automatically canonical. Both are **NON-CANONICAL** until Founder approval.  
4. Subscription is the **main commercial hypothesis** for Digital Twin / property documentation (finance effort over time vs full upfront). Hypothesis ≠ implemented recurring Stripe billing.  
5. ~2 real-market Digital Twin tests = **partial utility evidence**, not unit economics. ~14 days distributed field+office and older/semi-pro equipment are **effort hypotheses to measure**, not costs to invent.  
6. Do not turn observations into decisions. Do not turn hypotheses into canonical values.

**No implementation performed.**

---

# A. Executive summary

PropManage already has **many money-shaped writers** and **several reporting readers**. They do not share one economic language.

The correct language for this phase is:

| Say this | Do not say this |
|---|---|
| Commercial / demand activity | “We have no business because MRR is 0” |
| Demo / placeholder payment activity | “Cockpit revenue 2300 RON” as board cash |
| Internal wallet / credits | “Specialist earned 50k” as P&L |
| Implied 5% on confirm | “Platform revenue” |
| Runtime 249 / seed 79 | “The price of Digital Twin” |
| Two field tests, ~14 day delivery | “SaaS unit economics proven” |

**Closest honest REAL CASH definition already in code:** War Room / Enterprise Health — Verified Estate `paid` AND `demo_mode ≠ true` (+ verified `manual_payments`). In the inspected environment that value is **0**. That is **consistent with incomplete Stripe**, not a verdict on the product.

**Proposed future reporting semantics (design only):** four **labels**, one screen, no new engine — reuse existing collections with **class tags**, not a fifth calculator.

---

# B. Current economic truth (inspected environment)

Facts from D9.7, **reclassified** for this phase:

| Fact | Class | Interpretation |
|---|---|---|
| Stripe key = demo placeholder | G / B | Integration incomplete — **expected** |
| Paid `payment_transactions` 9 / 2300 RON, all demo-flagged | **B** | Placeholder activity |
| 5 txs initiated / 65 EUR, unpaid | **G** | Intent / abandoned checkout — not cash |
| VE paid 2 / 2600 RON, both `demo_mode` | **B** | Not real VE cash |
| `hh_subscriptions` = 0 | — | No entitlement period in DB |
| Premium list price 249 EUR in DB | hypothesis | **NON-CANONICAL** |
| Seed Premium 79 EUR | seed default | **NON-CANONICAL** |
| Requests 118; assigned 112; confirmed 12; offers 0 | **E** | Demand + execution **without** Model B offers |
| Confirm escrow sum 2750; implied 5% = 137.50 | **C** | Internal haircut; **no platform cash row** |
| `job_payment` 25 / 2802.50 ≠ 12 × 0.95 | **G** | Ledger drift |
| Wallet Σ 50817.50 | **C** | Internal; ≫ job_payment |
| Lead Credits outstanding 1980 | **D** | Virtual; not revenue |
| Tokens 6950 | **D** | Virtual |
| `manual_payments` collection absent | — | Writer unused here |
| Founder: ~2 real DT field cases | **E + F** | Outside this DB as structured cost — **UNKNOWN** in ledgers |

**REAL CASH REVENUE (class A) in this environment: 0.**  
**This is not a failure signal.**

---

# C. Financial source map

| SOURCE | PURPOSE | DATA TYPE | CLASS | WRITER | READER | CURRENT STATUS | CANONICAL? | EVIDENCE |
|---|---|---|---|---|---|---|---|---|
| `payment_transactions` | Checkout intents / Stripe-shaped rows | amount, currency, payment_status, demo | B if demo/placeholder; A only if live paid later | `payments.py`, `wallet.py` topup, HH billing | Financial Cockpit, BH conversii/financiar, CEO Dashboard | 14 rows; 9 paid = demo | **NON-CANONICAL** as “revenue” | D9.7; `DEMO_STRIPE` writes `demo: true` |
| `hh_plans` | List prices + copy features | price_eur, trial_days, lead_commission_pct | hypothesis | seed / admin PATCH | checkout, Cockpit MRR, Pricing UI | basic 9, pro 29, **premium 249** here | **NON-CANONICAL** prices | D9.7 vs seed 79 |
| `hh_subscriptions` | Entitlement window | status, expires_at, plan | D (access) until paid evidence | HH `_activate_subscription_if_paid` | Cockpit MRR, entitlements | **0 docs** | empty | D9.7 |
| HH checkout / webhook | Charge plan EUR | payment_transactions + activate | A **if** live paid; else B/G | `house_health_billing.py` | entitlements | 0 paid HH; one-shot +30d not Stripe Subscription | **NON-CANONICAL** “MRR” | module docstring: recurring later |
| `verified_estate_orders` | Audit / twin / bundle orders | amount_ron, demo_mode, package | A if paid !demo; B if demo | `verified_estate.py` checkout | EH real_revenue, War Room, CEO Briefing | 2 paid **demo** 2600 | **CANONICAL filter for VE cash** (result 0) | `demo_mode` |
| `verified_estate_listings` | Public listings + gates | status, commission settings | E (listing) / later A on sale | VE after pay + admin | public browse, War Room | 4 / 2 published | listing ≠ revenue | D9.6 gates |
| `app_settings.pricing` | VE RON overrides | audit_ron, twin_ron, commission_pct | hypothesis | admin | VE checkout | defaults 2400 / 15000 | **NON-CANONICAL** vs 2600 stored | D9.6 |
| `requests` | Jobs | status, escrow_amount, escrow_status | **E** + **C** markers | client create; `/accept`; pay; confirm | BH/EH fill, Marketing GMV, Cockpit escrow | 118; 12 confirmed | request ≠ revenue | D9.7 |
| `marketplace_offers` | Model B offers | status, fee | **E** | `submit_offer` | D1/D6 | **0 docs** | demand signal unused | D9.7 |
| `/accept` | Model A assign + credit debit | lead_credits / wallet | D or C | `requests.py` | tests | live path (0 offers) | participation cost ≠ revenue | D2/D8 |
| `confirm_complete` | Close job + 95% credit | escrow_amount × 0.95 | **C** | `requests.py` | wallet, transactions | 12 confirmed | **CANONICAL job haircut formula**; not cash | D8 |
| `users.wallet_balance` | Internal balance | float | **C** | confirm, topup, lead_fee, disputes, design phases | specialist UI, admin, Finance Reconciler | Σ 50817.50 | **NON-CANONICAL** as revenue | no withdraw |
| `users.lead_credits` | Participation inventory | int | **D** | auth grant; `/accept` consume | specialist | 1980 outstanding | not revenue | D2 |
| `users.tokens` | Perks / referral | int | **D** | confirm +100; referral +500 | client | 6950 | not revenue | `requests.py` |
| `transactions` | Internal ledger | type, amount, optional currency/demo | **C** / **D** / **B** | many writers | `/api/transactions`, integrity job | 132 rows; mixed types | **NON-CANONICAL** P&L | missing currency; job_payment 25≠12 |
| `job_payment` (type) | Specialist credit on confirm | amount = 95% | **C** | confirm | — | 2802.50 | not platform revenue | no 5% counterpart row |
| escrow fields | held/released/frozen/paid | markers | **C** | DEMO checkout + `/escrow` | Cockpit | not Stripe custody | escrow ≠ revenue | D7 |
| platform 5% | Implicit `amount - 0.95*amount` | none stored | **C** implied | confirm | **not a reader as cash** | 137.50 arithmetic | **CANONICAL rate (D8)**; **NON-CANONICAL** as booked revenue | no insert |
| Cockpit 10% est. | `released * 0.10` | derived | reporting error vs D8 | financial_cockpit | Cockpit UI | 275 on 2750 | **NON-CANONICAL** | hardcoded |
| `manual_payments` | Verified offline cash | amount_ron | **A** if verified | ops | EH real_revenue | collection **absent** here | unused | D9.7 |
| Stripe objects | External charges | — | A/B when integrated | not completed | `/api/health` stripe=demo | placeholder | **UNKNOWN** live | D9.7 |
| EUR_RON 4.98 | Display FX | constant | G | cockpit | MRR RON | hardcoded, no timestamp | **NON-CANONICAL** FX | code |
| Design `phases` pay/payout | Staged design | 0.95 pattern | **C** | `design.py` | — | 2 pay / 2 payout | sibling, not MP | D9.7 |
| Demo time machine | Simulated jobs | wallet | **B** | `demo_time_machine.py` | — | likely extra job_payments | not market | code |
| Interior leads | Consult demand | lead rows | **E** | `interior_design.py` | admin | unpriced | not revenue | D9.6 |
| HH `lead_commission_pct` 15/10/5 | Snapshot on publish | metadata | **G** vs D8 | HH publish | request field | not confirm haircut | **NON-CANONICAL** vs job 5% | D11 |

---

# 2 / D. Economic truth classes (canonical classification — design)

These are **semantic classes** for humans and future reports. They are **not** a new collection or engine.

### A. REAL CASH REVENUE

Money that left a customer’s **external** payment instrument and is available to the company (or clearly receivable under a completed live processor).

**Today:** none evidenced (Stripe incomplete; VE paid rows are demo; HH unpaid).  
**Already-coded approximation:** VE `paid` + `demo_mode≠true` + `manual_payments.verified`.

### B. DEMO / TEST ECONOMIC ACTIVITY

Processor placeholder, `demo: true`, `demo_mode: true`, `cs_demo_*`, time-machine, seed money.

**Today:** 2300 RON paid txs; 2600 RON VE; subset of `transactions`.

### C. INTERNAL ACCOUNTING

Balances and markers **inside** PropManage that do not move bank cash: `wallet_balance`, escrow_status, implicit 5%, `job_payment`, topup without live Stripe.

### D. VIRTUAL ECONOMY

Lead Credits, tokens, entitlements, trial_days display, “unlimited twins” flags.

### E. COMMERCIAL ACTIVITY / DEMAND SIGNALS

Traffic, sessions, requests, offers (when present), leads, listings published, confirmations as **service events**, founder field tests.

**This is the primary health class for the current phase.**

### F. COST / DELIVERY EFFORT

Hours, travel, equipment, rework, operator time. **Not in a ledger today.** Founder estimate ~14 days / case is **class F hypothesis**, class G in the database.

### G. UNKNOWN

Unflagged rows, missing currency, job_payment vs confirm drift, 65 EUR initiated, 249 vs 79, willingness-to-pay.

---

### Why common objects are not revenue

| Object | Why ≠ REAL CASH REVENUE |
|---|---|
| **Lead Credits** | Inventory granted/consumed to **participate**. No customer cash. Consuming 45 credits does not create company income. |
| **Wallet balance** | Internal number. Confirm **credits** 95%; there is **no withdraw**. Topup can be DEMO. Σ 50817 is not a bank statement. |
| **Escrow** | Status + `escrow_amount` on the request. DEMO checkout writes `held` without Stripe custody (D7). Released ≠ payout to IBAN. |
| **Request** | Demand / job record. 118 requests can exist with 0 cash. |
| **Offer** | Specialist intent. 0 offers here; even if N>0, an offer is not a charge. |
| **Subscription entitlement** | `hh_subscriptions.active` is **access**. Cockpit `price × active` is **implied**, and the writer is one-shot +30 days, not a Stripe Subscription. 0 subs ⇒ implied MRR 0, still not “proven recurring.” |
| **Demo payment** | Explicitly marked; processor is placeholder. Booking it as A **lies**. |

---

# 3 / E. Marketplace economic reconciliation

**Authoritative gross (D8 intent + runtime input):**  
`requests.escrow_amount` at `confirm_complete` (fallback `0`).

**Intended flow (D1/D6/D8/D7) vs this DB:**

```
CLIENT REQUEST          RUNTIME (118)
    → OFFER             NOT USED (0 marketplace_offers) — Model A /accept
    → OFFER SELECTION   /accept → assigned + specialist_id
    → RELATIONSHIP      D6: assigned
    → PAYMENT           optional; DEMO checkout writes payment_transactions + held
    → ESCROW            marker, not custody
    → EXECUTION         /start ungated (D7)
    → CONFIRMATION      /confirm if status=completed
    → SPECIALIST PAYOUT users.wallet_balance += escrow * 0.95
    → PLATFORM 5%       implicit; NOT stored
```

| Quantity | Formula / source | This DB | Class |
|---|---|---|---|
| Gross | `escrow_amount` on confirmed | 2750 | C / E (value claimed) |
| Specialist net | `gross * 0.95` | 2612.50 arithmetic | C |
| Platform 5% | `gross * 0.05` | 137.50 arithmetic | C implied |
| Wallet credit | same as net, on confirm | mixed into 50817 | C |
| `job_payment` | should equal net | 25 rows / 2802.50 | **G vs 12×0.95** |
| Escrow released | status + amount | 12 / 2750 | C |
| Payment tx | should fund gross | 9 paid demo 2300 RON | **B ≠ 2750** |

**5% vs 10%:** D8 runtime `* 0.95`. Cockpit `released * 0.10`. **Do not fix in this task.**  
**Do not mix** with HH `lead_commission_pct`, apply fee 5–50, VE sale commission.

**Gross authority:** `escrow_amount` at confirm — **not** `payment_transactions.amount` (can differ; DEMO; budget_estimate at checkout).

---

# 4 / F. HH / VE / Digital Twin — three economic maps

Do **not** collapse these.

### House Health (software access hypothesis)

| Topic | Evidence |
|---|---|
| Model | SaaS **hypothesis**; writer is **one-shot** activate + `expires_at` ≈ +30 days |
| Payment state | 0 paid HH txs; 5 initiated EUR |
| Trial | `trial_days` 7/14 on plans; **not granted** |
| Price sources | seed 9/29/**79**; **this DB premium 249** |
| Runtime price | checkout uses `hh_plans.price_eur` |
| Entitlement | `CLIENT_*` + flags; DT advanced = Premium in `entitlements.py` |
| Actual payment | **none** |

**249:** runtime hypothesis for a **plan slug**, not a Founder-canonical DT service price, not VE 15000 RON.

### Verified Estate (professional service + listing)

| Package | Price source | Payment | Class here |
|---|---|---|---|
| audit | env/settings ~2400 RON | Stripe/DEMO order | 0 real; demo bundles 2600 |
| twin | ~15000 RON | same | same |
| bundle | sum | same | 2 demo paid |
| sale commission | `commission_pct` | on sale, not on order | UNKNOWN collected |
| demo_mode | on order | **canonical VE cash filter** | all paid = demo |

### Digital Twin (do not one-bucket)

| Aspect | What it is | Economic class |
|---|---|---|
| **SOFTWARE** | 2D `twins` + 3D upload/viewer/pins | D (entitlement) / product |
| **SERVICE** | VE twin_ron / “we scan” copy | B in DB; A when live paid |
| **FIELD WORK** | Founder ~2 cases, ~14 days, older gear | **F** — not in Mongo |
| **DOCUMENTATION** | PDF plans, vault, warranties | D / E |
| **PROPERTY ASSET CREATION** | Model + memory fragments | asset, not revenue |
| **SUBSCRIPTION HYPOTHESIS** | Finance DT work over months via HH-like plan | **hypothesis**; billing is not recurring Stripe |

Selling “Digital Twin” as a single SKU **mixes F-cost with D-access**. That is a commercial design problem, not a dashboard bug.

---

# 5 / G. Digital Twin commercial validation model

**Do not evaluate as mature SaaS.**

### Evidence state (Founder + repo)

| Item | Status |
|---|---|
| ~2 real market tests | **E** — utility partially confirmed |
| Known limitations | process + equipment (solvable) |
| ~14 days field + office, distributed | **F hypothesis** — not timesheeted |
| Semi-pro / older equipment | **F** — no asset register |
| Efficiency expected to improve | **hypothesis** |
| Property-specific effort | **UNKNOWN** (varies by dwelling) |
| Willingness to pay | **UNKNOWN** (249/79/15000/unpriced 17-step all in market language) |

### What must be measured before price / unit economics (no engine — a **checklist**)

| Measure | Existing source? | Gap |
|---|---|---|
| Actual hours total | no | UNKNOWN |
| Field hours | no | UNKNOWN |
| Office hours | no | UNKNOWN |
| Equipment cost | no | UNKNOWN |
| Travel | no | UNKNOWN |
| Processing / convert time | convert logs **PARTIAL** | not costed |
| Documentation time | vault timestamps **PARTIAL** | not hours |
| Rework | model `superseded` **PARTIAL** | not labeled rework |
| Client feedback | `beta_feedback`, reviews, leads | not bound to the 2 cases in a typed way |
| Delivered outputs | DT project + files | exists |
| Willingness to pay | checkout attempts, VE pending, HH initiated | **weak** (65 EUR initiated) |
| Conversion | request/lead → pay | 0 real pay |
| Repeatability | n=2 | UNKNOWN |

**Until F is measured, 249 and 79 remain hypotheses, not prices to optimize.**

---

# 6 / H. Commercial validation health (lightweight, existing sources only)

Appropriate for ~2 months online. **No new KPIs invented as targets. No scores.**

| Signal | Existing source | Class | This env | Missing |
|---|---|---|---|---|
| DEMAND | requests created; interior_design_leads; VE inquiries | E | 118 requests | quality/spam **UNKNOWN** |
| TRAFFIC | `analytics_sessions` / `analytics_events` | E | not re-aggregated in D9.7 | treat as **UNKNOWN** here |
| REQUESTS | `requests` | E | 118 | — |
| OFFERS | `marketplace_offers` | E | **0** | Model B not live |
| CONVERSIONS | request→assigned→confirmed; checkout paid !demo | E / A | 112 assigned, 12 confirmed, **0 real pay** | offer→select N/A |
| SERVICES DELIVERED | confirmed; DT models; VE paid !demo; HH evals | E | 12 confirm; VE demo only | 2 founder DT cases **not in a typed collection** |
| FEEDBACK | reviews, beta_feedback, disputes | E | exists as modules | case-linked **UNKNOWN** |
| TIME/EFFORT | — | F | — | **UNKNOWN** (14d not stored) |
| PAYMENT READINESS | initiated txs; VE pending !demo; escrow held | E | 65 EUR initiated; held 10 / 2600 | not live Stripe |
| REPEATABILITY | recurring clients (Marketing Growth) | E | query exists | n small |

**Commercial Validation Health (narrative, not a score):**  
Demand and job flow are **observable**. Offer marketplace is **unused**. Real cash is **not expected yet**. Delivery effort for Twin is **known qualitatively, unmeasured quantitatively**.

---

# 7 / I. CEO reporting lineage + future semantic model

### Current definitions (do not change)

| Surface | “Revenue” | MRR | Marketplace | Payments | Demo |
|---|---|---|---|---|---|
| Financial Cockpit | Σ paid txs **no demo filter** | price × active subs × 4.98 | escrow buckets; **10%** take est. | same txs | unlabeled |
| Enterprise Health | VE paid !demo / 5000 | none | fill_rate | VE + manuals | excluded from real_revenue |
| Business Health | 30d paid **growth score** | none | fill lifetime | paid/all **rate** | unlabeled |
| CEO Dashboard | **Cockpit revenue** | Cockpit MRR | CC 24h counts | Cockpit | **not demo-safe** |
| CEO Briefing | **EH real_revenue line** | none | fill + gaps | VE pending !demo | inherits EH |
| War Room | real vs demo VE **split** | none | mission/leads | VE | **explicit demo** |

**Contradiction:** same morning, Dashboard can show 2300 and Briefing 0. Both are “true” to their formula. Neither is class A.

### Proposed future **semantic** model (design only — do not implement)

One reporting vocabulary, **four lines**, mapped to **existing** sources:

| Line | Label | Source to reuse | Class |
|---|---|---|---|
| 1 | **Real cash (A)** | EH/War Room VE filter + future live Stripe paid !demo + verified manual | A |
| 2 | **Demo / test activity (B)** | txs `demo` + VE `demo_mode` + time-machine | B |
| 3 | **Marketplace activity (E)** | requests / offers / assigned / confirmed counts + GMV as **escrow_amount** labeled GMV not revenue | E + C |
| 4 | **Internal / virtual (C+D)** | wallet Σ, credits, tokens, implied 5% — **footnotes** | C/D |

**Rules:** never sum 1+2+3+4 into “Revenue.”  
**MRR:** show only with caption *implied access, not cash* and only after live paid renewals exist; until then **“n/a — Stripe incomplete.”**  
**249/79:** show as *list price on slug premium (hypothesis)* if shown at all.

No new engine: this is **labeling and captioning** of existing composers.

---

# 8. Revenue vs economic activity

```
REVENUE (A)           external cash to company
    ≠ GMV             sum of job/VE prices (C/E) — 2750 confirmed escrow
    ≠ ESCROW          marker (C)
    ≠ WALLET MOVEMENT credit/debit (C)
    ≠ LEAD CREDITS    inventory (D)
    ≠ REQUEST VOLUME  demand (E) — 118
    ≠ OFFER VOLUME    supply intent (E) — 0
    ≠ COMMERCIAL INTENT initiated checkout, leads (E/G)
    ≠ ENTITLEMENT     HH access (D)
    ≠ FIELD EFFORT    hours (F)
```

| Concept | Belongs in |
|---|---|
| REVENUE | Class A line only |
| GMV | Marketplace / VE **volume** footnotes |
| ESCROW | Trust/ops markers |
| WALLET | Internal accounting |
| LEAD CREDITS | Marketplace participation health |
| REQUESTS / OFFERS | Commercial Validation Health |
| INTENT | Payment readiness |
| EFFORT | DT validation checklist |

---

# 9. Transversal health lens (no invented scores)

| Lens | Observation | Score |
|---|---|---|
| **CEO / Business** | Online, demand exists (118 requests), cash not the question this phase | **UNKNOWN as “healthy revenue”** — **activity visible** |
| **CFO / Financial** | Books mix A/B/C/D; 10% vs 5%; 0 class A | **Truth risk**, not P&L failure |
| **CPO / Product** | 17-step story vs modules; Twin = software+service+field | validation, not scale |
| **CTO / Technical** | DEMO Stripe; one-shot HH; Model A live | integration incomplete by design |
| **Architecture** | Many writers, no class tags on rows | do not add a fifth calculator |
| **Trust / Risk** | Dashboard 2300 vs Briefing 0; “escrow” language | **mislabeled money** |
| **Security / Governance** | Founder Gate unused by Repair; wallet topup DEMO | unchanged here |
| **Data / Knowledge** | 2 DT cases not typed in DB; 14d not stored | **UNKNOWN** effort |
| **Commercial Validation** | Demand yes; offers no; cash N/A; Twin n=2 qualitative | **early, evidence-bearing** |

---

# 10. Decision discipline

```
OBSERVE → EVIDENCE → ANALYZE → IMPACT
  → DECISION → APPROVAL/GATE → IMPLEMENT → TEST → VALIDATE → MEASURE AGAIN
```

This document stops at **ANALYZE**.  
Examples of **not-decisions:** “set price to 249,” “turn on Stripe live,” “filter Cockpit,” “create SSOT engine,” “cap requests.”

---

# J. Contradictions / risks

| Type | Item |
|---|---|
| Reporting | Cockpit/CEO Dashboard treat demo paid as revenue |
| Reporting | 10% vs D8 5% |
| Reporting | Briefing 0 vs Dashboard 2300 |
| Pricing | 249 runtime vs 79 seed vs VE RON vs unpriced 17-step — **none Founder-canonical** |
| Ledger | job_payment 25 ≠ confirm 12 |
| Product | Twin software vs field 14d vs subscription hypothesis |
| Trust | Escrow word vs marker |
| Phase risk | Reading class A = 0 as “product failed” |

---

# K. Unknowns

Live Stripe in other environments; grant/consume credit history; wallet composition; 65 EUR initiated identity; whether 2 DT cases have property_ids; actual hours vs 14d; WTP; traffic totals this week; spam rate; VE 2600 vs 17400 SKU; FX 4.98.

---

# L. Decisions requiring Founder approval (not implementation)

1. Confirm **phase language**: optimize validation (E/F), not CAC/LTV.  
2. When Stripe is live: is class A = VE only, or VE + HH paid + (later) job 5% **cash**?  
3. Is **249** a list-price experiment to keep, revert, or ignore? **Do not canonize.**  
4. Is **subscription** still the financing hypothesis for Twin field work? (Billing today is one-shot.)  
5. Must the ~2 DT cases be written into an existing collection (property + notes) — **or leave outside the DB**?  
6. Reporting captions: may we treat War Room/EH as the only “real cash” line **when** cash exists?  
7. Marketplace: stay Model A (0 offers) or enable Model B for offer-volume validation?  
8. 10% Cockpit line: hide/caption later — **not now**.

---

# M. Recommended next audit

**D9.9 — Commercial Validation Instrumentation (read-only):** map the 2 founder DT cases and the 118 requests onto **existing** fields (`property_id`, reviews, beta_feedback, analytics) and list **the smallest write** that would record hours/effort **if** later approved — without designing a new engine or a price.

Optional: Stripe completion runbook (ops), still no price change.

---

# N. MUST NOT be changed yet

- Production code, schemas, migrations  
- Pricing (79, 249, 9, 29, 2400, 15000, D8 5%)  
- Stripe keys / DEMO behavior  
- Marketplace accept/offer/confirm logic  
- Dashboards / Cockpit / EH formulas  
- Registries / Knowledge Center  
- No new engine, SSOT service, or “Financial Health Filter”  
- No commit / deploy  
- Do not “fix” 10% vs 5% in this phase  
- Do not treat 0 class A as a defect to patch with fake MRR  
- Do not canonize 249 or 79  
- Do not convert Lead Credits or wallet into revenue  
- Do not cap client requests to manufacture conversion  

---

# Keep / connect / wait (design posture)

| KEEP | CONNECT (later, approved) | WAIT |
|---|---|---|
| VE/War Room `demo_mode` split | Captions on CEO surfaces | Stripe live |
| D8 `* 0.95` as job formula | Class labels on reports | Price canon |
| Demand data (requests) | Optional hours on DT cases | Unit economics |
| Subscription as **hypothesis** | — | Recurring billing |
| n=2 qualitative Twin evidence | — | Scale KPIs |

**STOP.** Evidence and design only. No implementation.
