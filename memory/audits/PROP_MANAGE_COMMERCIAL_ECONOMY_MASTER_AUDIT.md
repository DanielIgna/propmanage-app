# PROP_MANAGE_COMMERCIAL_ECONOMY_MASTER_AUDIT

**Mode:** READ-ONLY architecture + business-logic audit  
**Date:** 2026-09-22  
**Scope:** This repository + previously evidenced target runtime (Stripe DEMO on `:8001`)  
**Not done:** implementation, flags, pricing, commissions, Lead Credits, Stripe, DB writes, commit, deploy

Evidence labels used below (do not collapse):

| Label | Meaning |
|---|---|
| DOCUMENTED | Written in docs / legal / comments only |
| CONFIGURED | Admin/seed/default exists |
| PERSISTED | Stored in a collection/field |
| IMPLEMENTED | Code path exists |
| RUNTIME-CONSUMED | A live caller reads it |
| ENFORCED | Blocks or charges something |
| EVIDENCED | Observed on running process or tests |
| CONNECTED | Two systems actually pass data |
| AUTOMATED | Tested / scheduled |
| AUTONOMOUS | Self-running loop |
| UNKNOWN | Cannot be proven from this pass |

---

# 1 Executive Summary

PropManage already has **three separate commercial economies** that UI language treats as one “marketplace commission”:

| Economy | Who pays | What is charged | When | Runtime status |
|---|---|---|---|---|
| **House Health subscription** | Client | Plan `price_eur` (seed 9 / 29 / **79**; founder UI **249** for Premium) | Checkout after Stripe `paid` | IMPLEMENTED; **DEMO Stripe** on target process likely blocks real charge |
| **Model A assignment fee** | Specialist | 45 Lead Credits **or** 45 RON wallet | Successful `POST /api/requests/{id}/accept` | **ENFORCED** — current public marketplace |
| **Job payout cut** | Implicit (from client escrow amount) | Hardcoded **5%** (`amount * 0.95`) | `POST /api/requests/{id}/confirm` | **ENFORCED** — independent of HH plan |
| **HH “lead commission” 15/10/5%** | Accounting on specialist **offer fee**, not job escrow | `hh_plans.lead_commission_pct` | Captured only on Model B `accept_offer` for HH-published requests | **PARTIAL** — stored `captured`, **never `paid`**, **never applied to `/confirm`** |
| **Model B apply fee** | Specialist | 5–50 RON wallet (+ optional priority) | `POST /api/requests/{id}/offers` | IMPLEMENTED, flag-gated, specialist apply UI **unmounted** |

**Canonical public marketplace today is Model A (first-wins `/accept`).** Model B exists as code + client “Vezi ofertele” UI. Founder direction is Model B; that is a **decision**, not current runtime.

**The founder UI 15% / 10% / 5% is not the same commercial object as the hardcoded 5% at confirmation.** They do not share a calculator, a trigger, or a payer.

**No new boxes are required** to express Model B. The missing work is **semantic wiring and deprecation of competing paths**, after D1–D2–D6–D8–D10–D11.

---

# 2 Current Commercial Model

## 2.1 Mechanisms that exist

| # | Mechanism | Payer | Recipient | Trigger | Store | Calculator | Enforcer | Configurable? | Config consumed? | Status | Dependents |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | HH subscription | Client | Platform (Stripe / `payment_transactions`) | `POST /api/house-health/checkout-session` then paid | `hh_subscriptions`, `hh_plans` | `hh_plans.price_eur` | Billing activate on `paid` | Yes (admin plans) | **Yes** for price | Partial (no DEMO path; no native Stripe Subscription) | Entitlements, HH gates, DT advanced |
| 2 | HH trial days | — | Client (promised) | Displayed on pricing | `hh_plans.trial_days` | — | **No writer of `status=trial` found** | Yes | **Displayed only** | UI / CONFIGURED | None at charge time |
| 3 | Lead Credits 135/45 | Platform grant / specialist consume | Specialist inventory | First specialist activation; `/accept` | `users.lead_credits`, `transactions` type `lead_credit` | Constants 135 / 45 | Atomic debit on `/accept` | No | n/a | **ENFORCED** (Model A) | SpecialistDashboard / ScheduleProposalModal |
| 4 | 45 RON lead fee | Specialist wallet | Platform (wallet decrement) | `/accept` if credits insufficient | `users.wallet_balance`, `transactions` type `lead_fee` | `LEAD_FEE_RON=45` | Atomic wallet debit | Admin `lead_fee_ron` exists | **No** — hardcoded | **ENFORCED** | Same as #3 |
| 5 | Model B offer fee | Specialist wallet | Platform | `submit_offer` | `marketplace_offers`, `transactions` type `marketplace_offer_fee` | Client-chosen 5–50 + priority | Wallet check | `fee_configs` min/max | Partial (Pydantic 5–50 hardcoded) | Dormant unless flag on | Ranking, HH capture |
| 6 | Job escrow / checkout | Client | DB marker + optional Stripe | `/payments/checkout-session` or `/requests/{id}/escrow` | `payment_transactions`, `requests.escrow_*` | `budget_estimate` | DEMO short-circuit if `DEMO_STRIPE` | Stripe key | Yes | **DEMO** on target `:8001` | `/confirm` payout |
| 7 | Job payout 5% | Taken from escrow amount | Specialist 95%, platform implicit 5% | `/confirm` | `wallet_balance`, `transactions` type `job_payment` | `amount * 0.95` | Hardcoded | `platform_commission_pct` | **No** | **ENFORCED** | Disputes same 0.95 |
| 8 | HH lead commission 15/10/5 | Reconciliation on offer fee | Record only | HH publish → B `accept_offer` | `requests.house_health_source` | `offer_fee * pct/100` | Status `captured` only | `hh_plans.lead_commission_pct` | **Yes** on HH publish + B accept | **PARTIAL / not charged** | HH stats |
| 9 | Client loyalty tokens | Platform | Client | `/confirm` +100 | `users.tokens` | Constant 100 | Yes | No | n/a | **ENFORCED** | ≠ Lead Credits |
| 10 | Referral tokens | Platform | Sponsor | First confirmed request | `users.tokens` +500 | Constant | Yes | No | n/a | IMPLEMENTED | Twin unlock perk |
| 11 | VE commission | Seller / listing | Platform estimate | VE `admin_mark_sold` | `app_settings.pricing.commission_pct` | Default 0.0 in schema; env `VE_COMMISSION_PCT` 2.5 in tests | VE only | Yes | **VE only** | Other product | Not marketplace jobs |
| 12 | Welcome voucher 50% | — | Specialist | Native specialist register | `vouchers` | 50% | Issued | n/a | **Not applied** on `/accept` or `submit_offer` | DISCONNECTED | Email |
| 13 | Quest vouchers | — | User | Feature Configurator quests | `user_vouchers` | % | Issued | Yes | **Not** on marketplace fees | DISCONNECTED | Achievements |
| 14 | Partner commissions | Partner CRM | Stored `commissions{}` | Partner admin | `marketplace_partners` | — | **Not** read by `/confirm` | Yes | **No** | DISCONNECTED | KPI only |
| 15 | Design quote 5% | Quote price | Specialist 95% | Design flow | design routes | `* 0.95` | Separate product | No | n/a | Other product | Not job `/confirm` |
| 16 | Wallet top-up | User | `wallet_balance` | `wallet.py` | users / txs | Stripe or DEMO | Same DEMO formula | Key | Yes | Parallel to job escrow | Model A/B cash fees |

## 2.2 Who is the customer of each economy

- **Client pays** for House Health (EUR) and for job escrow (RON `budget_estimate`).
- **Specialist pays** to **get the job** (Model A 45 credits/RON, or Model B 5–50 RON apply).
- **Platform keeps** assignment/apply fees + implicit 5% of released escrow.
- **HH 15/10/5 is not proven as a second cash charge.** It is a **stored percentage** on HH-sourced requests.

## 2.3 What does *not* exist as a live rule

- Client request quota / “3 free projects”
- Subscription-based change of the `/confirm` 5%
- Verified-client or verified-specialist change of any marketplace fee
- Stripe Connect specialist payout
- Native recurring Stripe Subscriptions (HH is one-shot Checkout + `expires_at` += 30 days)

---

# 3 Subscription Architecture

## 3.1 Objects

| Object | Collection / file | Role |
|---|---|---|
| Plan definition | `hh_plans` | Admin SSOT for price, trial display, features list, `lead_commission_pct` |
| Seed defaults | `house_health_billing.DEFAULT_PLANS` | Inserted only if slug missing |
| Subscription | `hh_subscriptions` `{user_id, plan, plan_id, status, expires_at}` | Access window |
| Entitlement translation | `backend/entitlements.py` | `plan` slug → `CLIENT_*` tier → feature set |
| Checkout | `POST /api/house-health/checkout-session` | Amount from `hh_plans.price_eur` |
| Activation | `_activate_subscription_if_paid` | On Stripe `paid` → `status=active`, extend `expires_at` |
| Webhook hook | `payments.stripe_webhook` → `_activate_subscription_if_paid` | CONNECTED |
| Public pricing UI | `frontend/src/pages/PricingPage.jsx` | Reads `GET /api/house-health/plans` |
| Upgrade UI | `HouseHealthUpgradePage.jsx` | Shows `lead_commission_pct` |
| Admin UI | `AdminHouseHealthPage.jsx` | CRUD plans including commission % |

## 3.2 Plan matrix — code seed vs founder UI

| Plan | Seed `price_eur` | Founder UI | Seed `trial_days` | Founder UI trial | Seed `lead_commission_pct` | Founder UI % |
|---|---|---|---|---|---|---|
| Basic `slug=basic` | **9.0** | 9 EUR | 7 | 7-day | **15** | 15% |
| Pro `slug=pro` | **29.0** | 29 EUR | 14 | 14-day | **10** | 10% |
| Premium `slug=premium` | **79.0** | **249 EUR** | 14 | 14-day | **5** | 5% |

FILE: `backend/routes/house_health_billing.py` `DEFAULT_PLANS`  
STATUS: CONFIGURED (seed) · IMPLEMENTED (admin can overwrite) · PERSISTED value in **target DB = UNKNOWN** (no completed DB fact-check this series)

`PricingPage.jsx` has **zero hardcoded prices**. It prints `plan.price_eur` from API.  
`memory/PRD.md` states founder Premium **249€** is expected **per environment in `hh_plans`**, not in seed.

**Premium 249 EUR:** UI PRESENT (founder screenshots + pricing page if DB says 249) · CONFIGURED in seed as **79** · PERSISTED target value **UNKNOWN** · READ BY RUNTIME (checkout uses DB price) · ENFORCED only if Stripe is not DEMO/missing.

## 3.3 Trial

| Layer | `trial_days` |
|---|---|
| Seed / admin form / PricingPage / UpgradePage | PRESENT |
| `_activate_subscription_if_paid` | Uses `_billing_days(billing_period)` → **30 days after paid**, not `trial_days` |
| Writer of `hh_subscriptions.status = "trial"` | **NOT FOUND** |
| Reader of `status in [active, trial]` | `house_health.py`, `house_health_recommendations.py` |

**Trial is UI/CONFIGURED, not ENFORCED as a free grant.**

## 3.4 Entitlement mapping (actual)

FILE: `backend/entitlements.py`

| `hh_plans.slug` | Tier | Features granted (plus all lower) |
|---|---|---|
| none | FREE | `property_create`, `property_technical_record` |
| `basic` | CLIENT_BASIC | + `house_health_basic` |
| `pro` | CLIENT_PRO | + `house_health_advanced` |
| `premium` | CLIENT_PREMIUM | + `digital_twin_advanced`, `property_intelligence`, `portfolio_management` |

Gates that **actually 402**:

- House Health dashboard / module: `F_HOUSE_HEALTH_BASIC` — `house_health._assert_house_health_entitlement` / dashboard lock  
- Digital Twin **advanced** ops: `F_DIGITAL_TWIN_ADVANCED` — `digital_twin._ensure_dt_access`  
- DT **ingest/create container**: `_ensure_dt_ingest_access` — **not** PREMIUM (founder decision #4)

`require_entitlement()` exists as a FastAPI Depends factory. **Marketplace `create_request` / `/accept` do not use it.**

Specialist entitlements come from `experience_tier`, not HH pay. Specialist feature catalog is **not used as route Depends** on accept/match.

## 3.5 Stripe for subscriptions vs marketplace

| | Marketplace job checkout | HH subscription checkout |
|---|---|---|
| File | `payments.py` `create_checkout_session` | `house_health_billing.py` `create_checkout_session` |
| DEMO short-circuit | **Yes** (`DEMO_STRIPE`) | **No** — missing key → **503** |
| Price source | `requests.budget_estimate` | `hh_plans.price_eur` |
| Target `:8001` `/api/health` | `checks.stripe=demo` | Same env key |

**EVIDENCED:** target process Stripe mode = DEMO (2026-09-22). HH paid checkout on this process is **not proven live**.

## 3.6 Does 15/10/5 reach marketplace charging?

**No — not the job `/confirm` 5%, and not Model A `/accept`.**

Path that **does** read HH %:

1. Client publishes HH recommendation → `publish_to_marketplace`  
2. Reads active `hh_subscriptions` + `hh_plans.lead_commission_pct` (default **10** if no plan)  
3. Stores `requests.house_health_source.commission_pct`  
4. **Only if Model B** `accept_offer`: `commission_amount = offer_fee * pct/100`, status `captured`  
5. Comment says `pending → captured → paid`. **No code sets `paid`.**  
6. `/confirm` still does `amount * 0.95` and **never reads** `house_health_source`.

Disconnect points:

- Generic `POST /api/requests` does **not** attach `house_health_source`.  
- Model A `/accept` does **not** capture HH commission.  
- Flag off → Model B capture never runs.  
- Capture is on **specialist apply fee**, not client job amount.

---

# 4 Marketplace Runtime

## 4.1 Current runtime graph (what actually runs)

```
CLIENT (JWT, role=client)
  → PROPERTY (properties.owner_id)                    ENFORCED on create
  → POST /api/requests                                status=open
       notify specialists; optional AI match enqueue
  → GET /api/requests                                 specialists see open leads
  → [optional] GET /api/match                         zone+category+rating; NOT required
  → POST /api/requests/{id}/accept                    Model A CANONICAL
       45 credits OR 45 RON OR lead_fee_waived
       status=assigned + specialist_id
  → POST /api/payments/checkout-session               DEMO on target
       OR POST /api/requests/{id}/escrow              marker only, no wallet debit
       escrow_status=held (DB)
  → POST /api/requests/{id}/start                     NOT gated on escrow
       status=in_progress
  → POST /api/requests/{id}/complete                  status=completed
  → POST /api/requests/{id}/confirm                   95% wallet; +100 tokens
       status=confirmed; escrow released (field)
  → review / rating
```

Parallel **partial** path:

```
HH rec (urgent/recommended) + twin owner
  → POST .../publish-to-marketplace                   creates request + house_health_source
  → [if flag] POST /offers                            5–50 RON
  → GET /offers (client UI mounted)
  → POST /offers/{id}/accept                          assigned + selected_offer_id
       HH commission captured (not paid)
  → same start/complete/confirm as above
```

`OfferApplyForm` is **exported but has zero importers**. Specialist applies via unmounted form. Client can open `/client/requests/:id/offers` (`JobsV2` “Vezi ofertele”).

## 4.2 Transition table

| Transition | Route | Function | Entity | Auth | Commercial | Financial | Notify / event |
|---|---|---|---|---|---|---|---|
| Create | `POST /api/requests` | `create_request` | `requests` | `require_role("client")` + `owner_id` | none | none | `request.created`, lead notify |
| HH publish | `POST /house-health/recommendations/{id}/publish-to-marketplace` | `publish_to_marketplace` | `requests` + `hh_recommendations` | twin `owner_id` | stamps HH % | none | audit log |
| Match | `GET /api/match` | `smart_match` | users | authenticated | display `lead_fee` 0/45 | **not charged** | — |
| Accept A | `POST /api/requests/{id}/accept` | `accept_request` | requests, users, transactions | specialist | assignment | credits or 45 RON | client notify, `request.accepted` |
| Offer B | `POST /api/requests/{id}/offers` | `submit_offer` | marketplace_offers | specialist + flag | apply | wallet 5–50 | `offer.submitted` |
| Select B | `POST .../offers/{id}/accept` | `accept_offer` | requests, offers | client owner | assignment | none extra; HH capture | `offer.accepted` |
| Pay | `POST /api/payments/checkout-session` | `create_checkout_session` | payment_transactions | client owner, status open/assigned | escrow | DEMO or Stripe | `escrow.paid` |
| Escrow marker | `POST /api/requests/{id}/escrow` | `place_escrow` | requests | client | marker | **no debit** | — |
| Start | `POST .../start` | `start_work` | requests | assigned specialist | none | none | `work.started` |
| Complete | `POST .../complete` | `complete_work` | requests | assigned specialist | none | none | `work.completed` |
| Confirm | `POST .../confirm` | `confirm_complete` | requests, users | client | 5% cut | +95% wallet, +100 tokens | confirm events |
| Review | request review endpoints | reviews | reviews / rating | client | reputation | none | — |

## 4.3 Statuses actually used on `requests`

Documented in `create_request`: `open, assigned, in_progress, completed, confirmed`.  
Also used elsewhere: `closed` (progression counts).  
**No** request status `accepted` / `selected` / `paid`. Payment lives on `escrow_status` and `payment_transactions`.

---

# 5 Model A vs Model B

| | Model A | Model B |
|---|---|---|
| Canonical today | **YES** | **NO** |
| Route | `/accept` | `/offers`, `/offers/{id}/accept` |
| Flag | none (always on) | `fee_configs.multi_offer_enabled` default **false** |
| Specialist UI | `ScheduleProposalModal`, SpecialistDashboard “Acceptă · 45 RON” | `OfferApplyForm` **unmounted** |
| Client UI | implicit after assign | `JobsV2` / `ClientRequestOffersPage` **mounted** |
| Fee | 45 credits / 45 RON / waive | 5–50 RON wallet, no credits |
| Storage | `specialist_id` | `marketplace_offers` + `selected_offer_id` |
| HH 15/10/5 capture | **No** | **Yes** (HH-sourced only) |
| Tests | `test_lead_credits.py`, marketplace flow | PRD Sprint C; not default e2e |
| Reachable if flag off | Yes | Submit **400**; GET/accept_offer **ungated in code** |

**Race if both active:** `/accept` does not check the flag. First A assign sets `status=assigned`. B accept requires `status=open`. First writer wins. **Potential conflict in code.** Real dual usage in target DB: **UNKNOWN** (offers fact-check not completed).

`/accept` already has `lead_fee_waived` + `direct_specialist_id` (rebook/campaign). That is the **existing** non-public path — fate still D13.

### A → B migration dependency map

```
D1 = B (or sequenced)
  → D13 /accept residual (rebook/campaign/compat only?)
  → D2 credits event (apply vs win vs unused)
  → Mount OfferApplyForm; change SpecialistDashboard CTA
  → Gate GET/accept_offer with the same flag (today ungated)
  → Rewrite tests/QA that expect −45 on /accept
  → HH 15/10/5 only becomes reachable if B is the publish path
  → D8: confirm 5% still independent unless explicitly unified
  → Analytics that assume 45×assignment
```

If D1 = A remains: **no migration**. B stays island. Client “Vezi ofertele” remains a UX inconsistency.

---

# 6 Lead Credits

## 6.1 Current semantics (do not redefine)

**A Lead Credit currently buys one unit of Model A successful assignment access, at 45 credits per won `/accept`, with 45 RON wallet fallback.**

It does **not** buy: list view, match, apply (B), client selection, escrow, or subscription.

## 6.2 Lifecycle

| Event | File | Behavior |
|---|---|---|
| Native register `role=specialist` | `auth.py` | `lead_credits: 135`, `wallet_balance: 0` |
| Become-specialist | `auth.py` | `$set lead_credits: 135` after dual-role 400 guards (not `$inc`) |
| Google OAuth new user | `auth.py` | `lead_credits: 0` (OAuth is client) |
| `/accept` success | `requests.py` | atomic −45 credits else −45 RON; refund if claim fails |
| `/accept` waived | same | neither |
| Profile PATCH | not client-writable | tests assert |

Distinct from: `users.tokens` (client loyalty), `wallet_balance` (RON), vouchers, entitlements, quests.

Ledger: `transactions` `{type: lead_credit, currency: lead_credits}` vs `{type: lead_fee, currency: RON}`.

Frontend: `ActivityTimeline.jsx` ScheduleProposalModal. SpecialistDashboard still shows “45 RON” on one CTA (**UI drift**).

Admin visibility of balances: via user admin, not a dedicated credits console (no extra engine).

Target-env **usage volume**: UNKNOWN (DB fact-check interrupted). Code is **IMPLEMENTED + AUTOMATED** (`test_lead_credits.py`).

## 6.3 If Model B becomes canonical — options (not a choice)

| Anchor | Consequence |
|---|---|
| **Offer submission** | 45 credits per apply; 135 = 3 applies; wallet fallback competes with 5–50 RON apply fee — **double charge risk** unless B wallet fee is removed |
| **Lead access** (see list / details) | Changes “assignment” into “browse”; 135 empties on views; `/accept` residual must not also charge |
| **Client selection / win** | Closest to **current** meaning (successful assignment). B `accept_offer` would consume credits **or** keep B wallet apply fee — pick one |
| **Commercial relationship** (D6 event) | Same as win if D6 = assignment; different if D6 = payment |
| **Unused** | Credits remain A-only / residual `/accept`; B uses wallet 5–50 only |

Do not invent a new credit system.

---

# 7 Lead Fees (45 RON)

| Kind | Evidence | Meaning |
|---|---|---|
| Hardcoded `LEAD_FEE_RON = 45.0` | `requests.py` | **Model A assignment cash fallback** — ENFORCED |
| `LEAD_CREDIT_COST = 45` | same | Credit twin of the same event |
| `platform_config.lead_fee_ron` default 45 | `admin_console.py` | CONFIGURED, **not read by `/accept`** |
| `/match` display `lead_fee` 0 in-zone / 45 fallback | `matching.py` | UI annotation, **not charged** |
| Model B `fee_ron` 5–50 | `OfferIn` | **Different fee** — apply, not 45 |
| Legal/tour copy “45 RON / lead” | `LegalPages.jsx`, `RoleTour.jsx` | DOCUMENTED Model A |
| SpecialistDashboard “Acceptă · 45 RON” | ignores credits | UI residue |
| `demo_time_machine.LEAD_FEE` | demo | not production register |

**45 RON is the Model A assignment cash price.** It is not the Model B offer fee, not HH subscription, not the 5% job cut.

Beta-only? **No code flag** scopes it to Beta. It is the live A rule.

---

# 8 Commission Architecture

## 8.1 Matrix

| Dimension | Value | Source | Runtime consumer | Trigger | Payer | Recipient | Status |
|---|---|---|---|---|---|---|---|
| Job confirm (all requests) | **5%** implicit | Hardcoded `0.95` | `confirm_complete`, `disputes.py` | Client confirm | Escrow amount | Spec 95% / platform 5% | **ENFORCED** |
| Admin `platform_commission_pct` | default 5 | `platform_config` | **none on confirm** | Admin PUT | — | — | Dead config |
| HH Basic | 15 | `hh_plans.lead_commission_pct` seed | HH publish + B accept capture | HH rec → marketplace | Offer fee (accounting) | Record `captured` | **PARTIAL** |
| HH Pro | 10 | same | same | same | same | same | **PARTIAL** |
| HH Premium | 5 | same | same | same | same | same | **PARTIAL** |
| No HH sub on publish | **10** default | `house_health_recommendations.py:252` | publish | HH publish | — | stamp | IMPLEMENTED |
| HH commission `paid` | — | comment only | **none** | — | — | — | NOT FOUND |
| Verified client | — | — | — | — | — | — | NOT FOUND |
| Verified specialist | display only | KYC / match badge | not on fees | — | — | — | DISCONNECTED |
| Specialist `users.tier` | ranking weight 0.20 | `marketplace_offers` | B list sort | — | — | — | B only |
| Category / zone | `fee_configs.rules` | effective-fee API | **not `/accept`** | — | — | — | Partial / unused by A |
| Partner `commissions{}` | stored | partners | **not confirm** | — | — | — | DISCONNECTED |
| VE sale | `app_settings.pricing.commission_pct` | VE mark-sold | VE | listing | VE | **Other product** |
| Experience Spaces default | 15 | `experience_spaces/config.py` | ES module | — | — | Other product |
| App.js specialist card “15%” | hardcoded copy | `App.js` ~808 | marketing UI | — | — | DOCUMENTED / UI |
| Design quotes | 5% | `design.py` `* 0.95` | design | quote | — | Other product |
| Financial cockpit | 10% of released escrow | estimate comment | admin estimate | — | — | NOT the confirm calculator |

## 8.2 Are “HH 15/10/5” and “confirm 5%” the same?

**No.** Proof:

- Different bases: offer fee vs `escrow_amount` / `budget_estimate`.  
- Different events: B `accept_offer` vs `/confirm`.  
- Different code: `marketplace_offers.py` vs `requests.py:356`.  
- Confirm does not read `hh_plans` or `house_health_source`.  
- HH 5% on Premium coinciding with job 5% is **numeric collision**, not a shared SSOT.

---

# 9 Commercial Configuration / SSOT

| Rule | Actual SSOT today | Duplicate / dead |
|---|---|---|
| Model A assignment price | `LEAD_FEE_RON` / `LEAD_CREDIT_COST` | `platform_config.lead_fee_ron` |
| Job platform cut | hardcoded `0.95` | `platform_config.platform_commission_pct` |
| HH subscription price | `hh_plans.price_eur` (DB; seed 9/29/79) | Founder 249 if DB overwritten |
| HH trial | **None enforced** | `hh_plans.trial_days` display |
| HH lead % | `hh_plans.lead_commission_pct` at publish | default 10 if no plan |
| Model B on/off | `fee_configs.multi_offer_enabled` | GET/accept_offer ignore flag |
| Model B apply bounds | `OfferIn` 5–50 | `fee_configs` min/max (display/effective-fee) |
| VE commission | `app_settings.pricing.commission_pct` | Founder Gate slug `modify_commission_pct` |
| Client HH/DT access | `entitlements.py` + `hh_subscriptions` | Feature Configurator specialist catalog (unused on routes) |
| Stripe mode | `STRIPE_API_KEY` shape → `DEMO_STRIPE` | health `/api/health` classifier |

**There is no single commercial policy engine.** Closest reusable stores:

- **`hh_plans`** for client subscription + HH-sourced lead %  
- **`fee_configs`** for Model B flag + apply range  
- **Hardcoded A constants** until D8 says otherwise  

Do **not** create a new policy engine. Clean consumers first.

---

# 10 Client Trust

| Primitive | Exists | Enforced on marketplace request? |
|---|---|---|
| Authentication | JWT cookie | **Yes** |
| Email verification | `email_verified` optional | **No** |
| Phone | `phone_verified` field; SMS “not implemented” | **No** |
| Property ownership | `properties.owner_id` | **Yes** on `create_request` |
| Property completeness | DNA / vault scores | **No** on request |
| House Health subscription | `hh_subscriptions` | **No** on generic request; HH module 402 |
| Request history | `requests` | **No** eligibility rule |
| Client KYC | **NOT FOUND** | — |
| `users.tier` as Verified Client | FE / seed values | **No** marketplace gate |

**“Verified Client” is not a runtime concept.** Composable later from: auth + `owner_id` + optional email + optional HH sub. Do not build a new engine.

---

# 11 Specialist Trust

| Class | Signals | On `/accept` today |
|---|---|---|
| IDENTITY | KYC docs, `users.verified` | **Not required** |
| PROFESSIONAL VERIFICATION | admin `verify_specialist` sets `verified=True`, `tier=VERIFIED` | **Not required** |
| CAPABILITY | `capabilities[]`, catalog | **Not required** |
| REPUTATION | rating, reviews, jobs | **Not required**; used in `/match` sort and B ranking |
| MATCHING INPUT | category, zone, availability ≠ offline | `/match` only |
| COMMERCIAL ELIGIBILITY | credits ≥45 or wallet ≥45 or waive | **Yes** |
| PAYMENT CAPABILITY | same | **Yes** |

Do not merge KYC = `users.tier` = `experience_tier` = capability Nivel 2. KYC `$set tier=VERIFIED` can overwrite ADVANCED/TOP (**CONFLICTING** writers).

---

# 12 Subscription × Trust × Marketplace

```
CLIENT TRUST ──────────────── DISCONNECTED from request create
        +
PROPERTY STATE (owner_id) ── IMPLEMENTED / ENFORCED
        +
HOUSE HEALTH SUBSCRIPTION ── IMPLEMENTED for HH/DT modules;
                             DISCONNECTED from generic marketplace fees
        +
MARKETPLACE REQUEST ──────── IMPLEMENTED (A)
        +
SPECIALIST ELIGIBILITY ───── IMPLEMENTED as money only
        +
MODEL B OFFER ────────────── PARTIAL (flag + unmounted apply UI)
        +
CLIENT SELECTION ─────────── PARTIAL (client offers UI mounted; apply starved)
        +
COMMERCIAL RELATION ──────── IMPLEMENTED as status=assigned + specialist_id
        +
PAYMENT ──────────────────── IMPLEMENTED; DEMO on target
        +
ESCROW ───────────────────── DB marker; DISCONNECTED from /start
        +
COMMISSION ───────────────── ENFORCED 5% at confirm;
                             HH 15/10/5 PARTIAL on B+HH only
```

HH → marketplace **does** exist as: recommendation publish → request + `house_health_source`. That is the **only** subscription→marketplace **data** edge. It is **not** an entitlement gate on all requests.

Chicken-and-egg (product, not a new engine):

- HH dashboard wants an **active Digital Twin** *and* `house_health_basic`.  
- Advanced DT exploitation is **PREMIUM** (`F_DIGITAL_TWIN_ADVANCED`).  
- Seed Basic text: “1 Digital Twin inclus”.  
- Ingest/create of a twin container is **not** PREMIUM-gated.  

STATUS: **CONFLICTING claims** (seed/UI vs entitlement vs HH eligibility).

---

# 13 Three Free Experiences

| Nearby object | Meaning | = 3 free client projects? |
|---|---|---|
| 135 credits / 45 | **Specialist** assignments | **No** |
| Experience 3 completed jobs | Promotion criterion | **No** |
| FC quest “3 cereri / 30z” | Achievement + voucher | **No** |
| HH `trial_days` | Display; not granted | **No** |
| DT FREE project container | Twin ingest, not marketplace jobs | **No** |

**GAP.** Reuse later (after D1): request counter, or specialist-style credit, or HH trial writer.  
**≠ Verified Client.**

---

# 14 Stripe / Payment / Escrow

## 14.1 Target environment (already fact-checked)

| Item | Result |
|---|---|
| `GET /api/health` `checks.stripe` | `demo` |
| Effective marketplace checkout | **DEMO** |
| `DEMO_STRIPE` env var | **unset** (computed in `payments.py`) |
| Key class | UNKNOWN missing vs `sk_test_emergent`; **not** real test/live |

FILE: `backend/routes/payments.py` `create_checkout_session`  
EVIDENCED: 2026-09-22 on `127.0.0.1:8001`

## 14.2 What “escrow” is

| Concept | Status |
|---|---|
| REAL Stripe payment | Only if key is `sk_test_` / `sk_live_` and DEMO false |
| DB payment record | `payment_transactions` |
| DB escrow marker | `requests.escrow_status=held` |
| Internal wallet | `wallet_balance` + `job_payment` |
| Stripe Connect / custody | **NOT FOUND** |
| Execution gated by payment | **No** (`/start` ignores escrow) |
| Payout gated by confirm | **Yes** (`/confirm` requires `completed`) |
| Specialist Stripe payout | **No** — internal wallet increment |

`POST /requests/{id}/escrow`: sets marker, **does not debit wallet**.

## 14.3 Two checkout stacks

1. Job escrow — DEMO-aware.  
2. HH subscription — **not** DEMO-aware; 503 if key missing.

Do not design Connect in this audit.

---

# 15 House Health × Digital Twin × Marketplace

Intended loop vs status:

| Edge | Status |
|---|---|
| Property → HH observation | PARTIAL (HH needs twin + sub) |
| Observation → recommendation | IMPLEMENTED (`hh_recommendations`) |
| Recommendation → marketplace request | IMPLEMENTED (`publish-to-marketplace`) |
| Request → specialist | Model A default; B optional |
| Work → result | IMPLEMENTED (start/complete/confirm) |
| Result → Digital Twin update | **NOT FOUND** as automatic write from confirm |
| Twin → health update → next rec | PARTIAL (manual / later eval) |

This is **not** a closed autonomous loop.

---

# 16 Matching / Compatibility / Reputation

| Mechanism | Influences discovery? | Match? | Offers? | Eligibility? |
|---|---|---|---|---|
| `GET /match` zone+category+rating+verified badge | Optional API | Yes | No | No |
| Open request list | Yes (almost unfiltered) | — | — | Money on accept |
| Compatibility score | Stored on PUT | **Not** in `/match` or accept | No | No |
| B hybrid ranking | — | — | Yes if B on | No |
| `users.verified` | Badge in match | Sort annotation | B tier weight uses `users.tier` not KYC | No |
| Marketplace Intelligence | Admin demand/supply | No | No | No |

Reuse `/match` + stored score + B ranking. **No new matcher.**

---

# 17 Partners

**PARTNER ≠ SPECIALIST.**

Collections: `marketplace_partners`, `city_partners`, `marketplace_leads`, `city_partner_leads`.  
Roles: `marketplace_partner`, `city_partner`.  
Strategic dashboard: partner↔partner, not jobs.

`commissions{}` **not** consumed by `/confirm`.  
Keep B2B CRM separate. Optional later read for intel — not a merge.

---

# 18 Infrastructure Reuse Map

| Current system | Purpose | Consumers | Commercial relevance | Reuse for Model B? | Conflicts | Action |
|---|---|---|---|---|---|---|
| `requests` | Job object | A + B + HH publish | Core | **Yes** | — | Keep |
| `/accept` | First-wins / waive | Live A | Assignment fee | Residual only if D13 | Races B | Decide fate |
| `marketplace_offers` | Multi-apply | Flagged | Apply fee + ranking | **Yes** | Flag vs ungated GET | Wire, don’t rewrite |
| `lead_credits` | Specialist 3 assigns | `/accept` | A money | Only if D2 says | ≠ tokens | Don’t clone |
| `wallet_balance` | RON | accept, offers, confirm, wallet | Yes | Yes | — | Keep |
| `transactions` | Ledger | all money paths | Yes | Yes | types already distinct | Keep |
| `payment_transactions` | Checkout | jobs + HH | Yes | Yes | two stacks | Keep |
| escrow fields | Marker | payments, confirm | Partial | After D7 | ≠ Connect | Don’t pretend custody |
| `hh_plans` / `hh_subscriptions` | Client product | entitlements, HH, publish % | Yes | For D10/D11 | 15/10/5 ≠ confirm 5% | Don’t merge blindly |
| `entitlements.py` | Feature translation | HH, DT | Access not job fees | Gate HH loop only | Specialist catalog unused | Don’t replace |
| `fee_configs` | B flag + ranges | `submit_offer` | Yes | **Yes** | Dead vs A constants | Don’t new engine |
| `platform_config` | Admin numbers | settings UI | Intended A fees | After D8 | Unused | Don’t “activate” blindly |
| `app_settings` | VE pricing | VE | Other product | No for jobs | Founder Gate name collision | Keep separate |
| matching / capability | Rank/filter | optional | Quality | Inputs | Score unused by match | Compose |
| KYC / verified | Identity | admin, match badge | Trust | Gate/rank later | tier overwrite | Don’t new KYC |
| reviews / rating | Reputation | match, B rank | Yes | Yes | — | Keep |
| notifications | UX | accept/offer | — | Yes | — | Keep |
| marketplace_intel | Admin | demand/supply | Later metrics | Add reads | Limited inputs | No new intel |
| partners | B2B CRM | admin | Separate | No as specialists | — | Keep separate |
| vouchers / quests | Promo | unused on fees | Weak | Optional later | — | Don’t use as credits |
| Feature Configurator | Catalog | not route Depends | No | No as SSOT | — | Don’t elevate |

---

# 19 UI Promise vs Runtime Truth

| Claim / UI | Source file | Backend | Persistence | Runtime consumer | Enforced? | Status |
|---|---|---|---|---|---|---|
| Basic 9 EUR | PricingPage / seed | `hh_plans.price_eur` | `hh_plans` | HH checkout | If Stripe paid | CONFIGURED 9 · target DB UNKNOWN |
| Pro 29 EUR | same | same | same | same | same | same |
| Premium 249 EUR | Founder UI / PRD | seed **79** | DB can override | checkout uses DB | If DB=249 and Stripe live | **UI vs seed CONFLICT**; target DB UNKNOWN |
| Basic 15% / Pro 10% / Premium 5% | `HouseHealthUpgradePage.jsx` | `lead_commission_pct` | `hh_plans` + `house_health_source` | HH publish + B capture | **Not** on `/confirm` or `/accept` | UI PRESENT · PARTIAL capture |
| Trial 7/14 days | Pricing + admin | `trial_days` | `hh_plans` | **Display** | **No grant path** | UI only |
| “Specialists verified” | match badge, KYC | `users.verified` | users | display / admin | **Not** accept gate | PARTIAL |
| Marketplace benefits on HH cards | seed `features[]` | copied to `hh_plans` | plans | Pricing list | Access via entitlements, **not** job fees | MIXED |
| Stripe payment language | checkout UIs | two stacks | — | payments / HH billing | Job = DEMO here | EVIDENCED DEMO |
| Escrow language | payments + `/escrow` | marker + DEMO | `escrow_status` | confirm reads amount | Not custody | DOCUMENTED ≠ Connect |
| “Commission reduced” Pro/Premium | seed feature strings | `lead_commission_pct` | HH source | B capture only | Not job 5% | UI overclaim vs confirm |
| Property Intelligence | Pricing badge + `F_PROPERTY_INTELLIGENCE` | entitlements | sub plan | PI module (separate) | Not marketplace | Other product |
| Legal “45 RON / lead + 95%” | `LegalPages.jsx` | A + confirm | — | matches A runtime | Yes for A | DOCUMENTED ≈ A |
| App.js specialist “comision 15%” | `App.js` | none | — | marketing | **No** | UI only |
| SpecialistDashboard “45 RON” | dashboard | credits exist | — | stale vs credits UI | Misleading | UI drift |
| Matching `lead_fee` 45 | `/match` | not charged | — | display | **No** | UI only |

---

# 20 Security / Authorization

| Transition | Auth | Notes / risks (report only) |
|---|---|---|
| Create request | client + `owner_id` | Property IDOR mitigated by `_load_property_for` (prior fix) |
| List requests | specialists see **open** broadly | Not compatibility-gated |
| `/accept` | specialist | First-wins; credits/wallet server-side; **not** client-writable credits |
| Submit offer | specialist + flag | Self-apply blocked; max 5 |
| List offers | owner / admin / offerer | GET **not** flag-gated |
| Accept offer | client owner | **not** flag-gated |
| Job checkout | client + `client_id` | Amount server-side from budget |
| `/escrow` | client | Client-supplied `amount` **is** a client-controlled commercial field on the marker path |
| `/start` `/complete` | assigned specialist | No escrow check |
| `/confirm` | client owner | Releases wallet; 5% not admin-overridable in this function |
| HH checkout | authenticated | Price from plan, not client amount |
| HH publish | twin owner | Fallback “first property” if `property_id` omitted — weaker binding |
| Lead credits | server only | Tests: profile cannot set |
| Admin plans / fee_configs / platform_config | admin | Can change displayed HH % and B flag; **cannot** change confirm 0.95 without code |
| Stripe webhook | DEMO no-ops | Live path exists |

IDOR: property/request GET were fixed in prior P1 work. Offers GET is scoped.  
Payment bypass: `/start` without held escrow. `/escrow` without wallet debit. DEMO checkout marks paid without Stripe.

---

# 21 State / Event Model

## 21.1 Request states (actual)

`open → assigned → in_progress → completed → confirmed`  
(+ `closed` in some counters)

## 21.2 Events vs implicit

| Meaning | Explicit event / field | Implicit? |
|---|---|---|
| Request creation | `request.created` | No |
| Specialist discovery | list / match / notify | Implicit |
| Offer creation | `offer.submitted` + `marketplace_offers` | Only if B |
| Offer selection | `offer.accepted` + `selected_offer_id` | Only if B |
| Commercial relationship | `status=assigned` + `specialist_id` | **This is the de facto relation** — no separate collection |
| Payment | `escrow.paid` / payment_transactions | Optional vs start |
| Escrow | `escrow_status` | Marker |
| Work start | `work.started` | Not payment-gated |
| Completion | `work.completed` | No |
| Confirmation | confirm handler | Payout + tokens |
| Payout | `job_payment` tx | Wallet, not Stripe |
| Review | reviews | After |
| HH commission | `commission_status` pending/captured | `paid` never written |

---

# 22 Target Architecture

Founder direction + **existing boxes only**:

```
Client
  → Trust / Property          EXISTING (auth + owner_id); composed “verified” MISSING
  → Request                   EXISTING
  → Matching                  PARTIAL (optional /match; score DISCONNECTED)
  → Multiple specialists      PARTIAL (B storage; apply UI unmounted)
  → Offers                    EXISTING collection; flag
  → Client choice             PARTIAL (UI mounted)
  → Commercial relationship   EXISTING as assigned row
  → Payment                   EXISTING DEMO
  → Escrow                    PARTIAL (marker)
  → Execution                 EXISTING
  → Confirmation              EXISTING
  → Payout                    EXISTING wallet
  → Reputation                EXISTING
  → HH / DT feedback          PARTIAL publish; loop back MISSING
  → Subscription              EXISTING for HH/DT access;
                              CONFLICTING if treated as job-commission SSOT
```

Do not add engines. Wire: B flag + apply UI, D2 event, D8 consumer, D13 residual `/accept`.

---

# 23 Decision Map

Do **not** choose for the founder.

### D1 — Canonical marketplace model  
**STILL OPEN** (direction stated B; runtime still A)  
Evidence: A live; B partial.  
Options: A remains · B canonical · sequenced (B then A fallback).  
Depends: nothing. Blocks D2, D13, D14.  
Do not change flags yet.

### D2 — Lead Credit semantic anchor under B  
**STILL OPEN**  
Current: successful A assignment.  
Options: apply / access / win / unused.  
Depends: D1.  
Do not change credit code yet.

### D3 — Client trust rule  
**STILL OPEN** (can defer)  
Options: stay role+property · compose email/ownership/HH · (no new engine).  
Depends: D6 if relation requires “verified client”.

### D4 — Specialist eligibility  
**STILL OPEN** (can defer)  
Today: money only.  
Options: keep · add KYC gate · add KYC as rank only.

### D5 — Matching / compatibility role  
**STILL OPEN** (after D1)  
Reuse `/match` + score. No new engine.

### D6 — Event that creates commercial relationship  
**STILL OPEN**  
Today: `assigned`.  
Options: assignment · payment · escrow held · verified∩selected.  
Blocks D7/D8 event choice.

### D7 — Payment / escrow boundary  
**STILL OPEN** (Connect deferred)  
Today: DEMO + marker; start ungated.  
Do not implement Connect in the next coding step.

### D8 — Commission SSOT + event  
**STILL OPEN**  
Today: confirm `0.95`. HH 15/10/5 is another object.  
Options: keep split · wire confirm to `platform_commission_pct` · wire confirm to `hh_plans` · keep HH % as lead-fee attribution only.  
Depends: D1, D6, D11.

### D9 — Three free client experiences  
**STILL OPEN / OUT OF SCOPE** until promised  
GAP. ≠ verification.

### D10 — Subscription → marketplace entitlement  
**STILL OPEN**  
Today: HH/DT access only; generic requests ungated.  
Options: stay · require HH to create requests · require HH only for publish path (already implicit).

### D11 — Subscription commission relationship  
**STILL OPEN**  
Today: HH % ≠ job 5%.  
Must decide if Premium “5%” is **job cut**, **lead-fee attribution**, or **copy**.  
Depends: D8. Do not change 5% or 15/10/5 until this is named.

### D12 — Reputation → marketplace  
**STILL OPEN** (parallel)  
Today: optional match / B rank. Not eligibility.

### D13 — `/accept` final role  
**STILL OPEN**  
Options: public A · internal rebook/campaign/waive only · deprecate.  
Evidence already supports waive/direct.  
Depends: D1.

### D14 — A→B migration dependencies  
**STILL OPEN** until D1=B  
See §5. Do not migrate tests/UI until D1+D2+D6.

---

# 24 Open Unknowns

1. Target DB `fee_configs.multi_offer_enabled` (fact-check interrupted).  
2. Target `marketplace_offers` volume / dual A+B usage.  
3. Target `hh_plans.premium.price_eur` (79 seed vs 249 UI).  
4. Target `hh_plans.lead_commission_pct` overrides.  
5. Whether any `hh_subscriptions.status=trial` rows exist (no writer found).  
6. Stripe key missing vs placeholder (both DEMO).  
7. `/start` without escrow frequency in data.  
8. Lead Credits balances/tx volume in target DB.  
9. Whether any client field writer sets `users.tier` as “Verified Client”.  
10. Whether `require_entitlement` is wired to any marketplace route besides HH/DT (search: no).  

---

# 25 CEO / CTO / Architect Conclusion

### A. WHAT PROPMANAGE ALREADY HAS

A working Model A job spine; Lead Credits; wallet ledger; DEMO/Stripe checkout; HH plans + subscriptions + entitlements; HH→request publish; Model B offers module; matching; KYC; reviews; partner CRMs; intel; admin knobs.

### B. WHAT ACTUALLY WORKS AT RUNTIME

`owner_id` → request → `/accept` (45 credits/RON) → optional DEMO pay → start/complete → confirm 95/5 + tokens.  
HH/DT **access** gates for those modules.  
Target Stripe = **DEMO**.

### C. WHAT EXISTS BUT IS DISCONNECTED

`platform_config` fees; HH 15/10/5 vs `/confirm`; Model B apply UI; compatibility score vs `/match`; vouchers vs fees; partner commissions; specialist entitlement catalog; `trial_days`; escrow vs `/start`.

### D. WHAT IS ONLY UI / DOCUMENTATION

Trial as a free grant; Premium 249 if only in screenshots; App.js “15%”; match `lead_fee` 45; “escrow” as Stripe custody; “commission reduced” as job-cut; SpecialistDashboard 45 RON ignoring credits.

### E. WHERE COMMERCIAL RULES ARE DUPLICATED

Job 5% vs admin 5% vs HH Premium 5% vs VE % vs design 0.95 vs cockpit 10% estimate.  
45 hardcoded vs `lead_fee_ron`.  
Apply 5–50 in Pydantic vs `fee_configs`.  
Four specialist “tier” vocabularies.

### F. WHERE MONEY / CREDITS CAN CURRENTLY MOVE

−45 credits or −45 RON on A accept; −5–50 RON on B offer; DEMO/Stripe client checkout; +95% wallet on confirm; +100/+500 tokens; HH EUR checkout (if key real); wallet top-up.

### G. WHAT THE CURRENT MARKETPLACE MODEL REALLY IS

**Model A first-wins.** Model B is a **partial, flag-off (code default) island** with client UI ahead of specialist apply UI.

### H. WHAT MUST CHANGE FOR MODEL B

A decision, then: apply UI, `/accept` residual, credit event, flag consistency, tests/QA, and an explicit statement that HH 15/10/5 is or is not the job commission.

### I. WHAT MUST NOT BE BUILT AGAIN

New credit system · new verification engine · new matcher · new intel · new policy engine · partner-as-specialist · treating UI `users.tier` as eligibility · Connect/escrow product before D7.

### J. MINIMUM ARCHITECTURAL DECISIONS BEFORE CODING

**D1, D2 (if not staying on A), D6, D8, D11 (name the two “5%”), D13.**

### K. MOST IMPORTANT OPEN UNKNOWNs

Target flag + offers volume; Premium 249 in DB; Stripe missing vs placeholder; whether founder “15/10/5” is meant to replace confirm `0.95`.

### L. RECOMMENDED ORDER OF ARCHITECTURAL DECISIONS

```
D1 Canonical model
  → D13 /accept residual
  → D2 Lead Credit anchor
  → D6 Commercial-relation event
  → D11 What HH % means
  → D8 Job commission SSOT
  → D10 Sub → marketplace access (if any)
  → D7 Escrow boundary (Connect later)
  → D5 / D4 / D12 (rank vs gate)
  → D3 / D9 (later)
  → D14 migrate only after the above
```

---

**STOP.** This file is the audit. No implementation, flag, price, commission, credit, Stripe, or subscription change follows from it.

*Report path: `memory/audits/PROP_MANAGE_COMMERCIAL_ECONOMY_MASTER_AUDIT.md`*
