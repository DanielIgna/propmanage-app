# D6 — COMMERCIAL RELATIONSHIP DECISION SPECIFICATION

**Decision:** D6 — When does PropManage create the **commercial relationship** between client and specialist?  
**Canonical public Marketplace event:** **A — Client selects an offer**  
**Runtime representation (reuse, no new engine):** `requests.status=assigned` + `specialist_id` + `selected_offer_id` + winning `marketplace_offers.status=won`  
**Mode:** READ-ONLY architectural decision. No implementation, flags, schema, Stripe, prices, credits, commit, or deploy.  
**Given:** D1 = public Marketplace is Model B · D2 = Lead Credits consumed on `submit_offer` (participation ≠ job)  
**Date:** 2026-09-23

D2 and D6 are **different events**. Do not collapse:

offer submitted ≠ offer selected ≠ payment initiated ≠ payment succeeded ≠ escrow held ≠ work started ≠ work completed ≠ client confirmed ≠ specialist paid ≠ platform commission recognized.

**No implementation performed.**

---

# 1. Executive decision

**For the public Marketplace (Model B), the commercial relationship is created when the client successfully selects an offer.**

| | |
|---|---|
| Canonical event | **A. Client selects an offer** |
| Route | `POST /api/requests/{req_id}/offers/{offer_id}/accept` |
| Symbol | `backend/routes/marketplace_offers.py` `accept_offer` |
| Actor | Client who owns the request (`require_role("client")` + `requests.client_id == user.id`) |
| Request after | `status=assigned`, `specialist_id` set, `selected_offer_id` set, `assigned_at` set |
| Offer after | Winner `won`; other open offers `lost` |
| Money at this event | **None** for the job. House Health `lead_commission_pct` is **captured**, not paid. Lead Credits are **not** consumed here (D2 = submit). |
| Work at this event | Notify says the specialist may start. `/start` is a **later**, separate event. |
| Payment / escrow | **Later and distinct.** Not required to create the relationship. |

This is the event the repository **already writes** on the Model B path. D6 names it. D6 does **not** invent a new collection, status, or activation engine.

**Rejected as the public D6 event:**

| Option | Why rejected as D6 |
|---|---|
| **B. Successful payment** | Checkout is optional, DEMO on this process, and eligible on `open` **without** a specialist. Payment must stay a later, distinct event (D7). |
| **C. Escrow successfully held** | `escrow_status=held` is an **internal escrow marker**. Client `/escrow` can set it without payment. Must not be called real custody and must not create the relationship. |
| **D. Explicit activation after selection/payment** | Would be a **new event/engine**. Existing `assigned` + `specialist_id` already bind the pair. Forbidden by reuse rule. |

**`/accept` classification (public Marketplace):** **DEPRECATE** as a public relationship writer. Residual waived / rebook / maintenance-direct / campaign / admin-match remain until **D13**. Do not delete in this decision.

---

# 2. Current runtime evidence

Traced from code. UI labels were not used as proof.

## 2.1 Lifecycle table

```
client
  → property
  → request
  → matching
  → offer
  → selection          ← D6 (public Marketplace)
  → checkout/payment
  → escrow marker
  → execution
  → confirmation
  → payout
  → commission
  → review
  → reputation
  → rebooking
```

| Transition | Endpoint / function | DB state / field | Actor | Authorization | Payment dependency | DEMO / REAL | Enforced vs UI | Tests / callers |
|---|---|---|---|---|---|---|---|---|
| Client owns property | `properties` lookup inside `create_request` | `properties.owner_id` | Client | `require_role("client")` + owner match | None | REAL auth | **ENFORCED** | `test_property_get_ownership.py` |
| Create request | `POST /api/requests` `create_request` | `requests.status=open`, `specialist_id=None`, `escrow_amount=None` | Client | Role + owned `property_id` | None | REAL persist | **ENFORCED** | Many request tests |
| Notify specialists | same function | `notifications` | System | Category filter (loose) | None | REAL notify | ENFORCED notify; matching optional | — |
| AI match notify | `enqueue_ai_match_notifications` | none on request | System / background | Best-effort | None | REAL notify | **NOT** assignment | Autopilot |
| List open leads | `GET /api/requests` `list_requests` | `status=open` visible to specialists unless `direct_specialist_id` points elsewhere | Specialist / client / admin | Role query | None | REAL | **ENFORCED** | Specialist dashboard |
| Optional match | `GET /api/match` `matching.py` | Read-only specialist list | Authenticated | `get_current_user` | None | REAL query | **NOT** required to offer or assign | Admin auto-match uses `find_matching_specialists` |
| Submit offer | `POST /api/requests/{id}/offers` `submit_offer` | `marketplace_offers.status=open`; wallet `−(fee_ron+priority)` 5–50; `transactions.type=marketplace_offer_fee` | Specialist | `require_role("specialist")` + `fee_configs.multi_offer_enabled` + request `open` | Wallet RON apply fee (not job money; **not** Lead Credits today) | REAL wallet debit if flag on | **ENFORCED** when flag true; **400** when flag false | Flag-gated; `OfferApplyForm` **unmounted**; no `test_*offer*.py` |
| List offers | `GET /api/requests/{id}/offers` `list_offers` | `marketplace_offers` open | Client owner, admin, or offering specialist | RBAC in handler | None | REAL | **ENFORCED** | `OffersList` mounted on `ClientRequestOffersPage.jsx` |
| **Select offer (D6)** | `POST .../offers/{offer_id}/accept` `accept_offer` | Request `assigned` + `specialist_id` + `selected_offer_id`; offers `won`/`lost` | Client owner | Client + `status==open` + offer `open` | **None** | REAL persist | **ENFORCED** if called | Frontend `OffersList`; HH capture in same function |
| Model A take (not D1 public) | `POST /api/requests/{id}/accept` `accept_request` | Same `assigned` + `specialist_id`; **no** `selected_offer_id` | Specialist | Specialist; `direct_specialist_id` if set; 45 credits or 45 RON unless waived | Lead Credit / wallet **lead** fee | REAL debit | **ENFORCED**; **no flag check** | `ActivityTimeline.jsx`, `SpecialistDashboard.jsx`, many tests, `qa_automation.py` |
| Campaign assign | `POST /api/campaigns/{id}/accept-offer` | Inserts requests **already** `assigned` + `lead_fee_waived` + `is_campaign` | Campaign initiator / admin | Campaign owner or admin | None | REAL insert | **ENFORCED** | `test_community_buildings_iter146.py`, `BuildingHub.jsx` |
| Admin / cron assign | `execute_auto_match` | `assigned` + `auto_assigned_*`; fee bypass | Admin / cron | Admin route / scheduler | None | REAL | **ENFORCED** when run | `test_phase75_auto_match.py`, `test_phase76_auto_match_schedule.py` |
| Rebook create | `POST /api/trusted-specialists/{id}/rebook` | New request `open` + `direct_specialist_id` + `lead_fee_waived` + `is_rebooking`; **`specialist_id` still None** | Client | Prior `completed`/`confirmed` with that specialist + owned property | None | REAL | **ENFORCED** | `test_gbos_growth_iter145.py` |
| Maintenance-direct | `maintenance_calendar` direct mode | Same pattern as rebook (`open` + waived + `direct_specialist_id`) | Client | Prior completed/confirmed | None | REAL | **ENFORCED** | `test_gbos_growth_iter145.py` |
| Checkout | `POST /api/payments/checkout-session` `create_checkout_session` | `payment_transactions`; DEMO also `escrow_*` + `transactions.type=escrow_deposit` | Client owner | Client + `status in [open, assigned]` | This **is** the payment attempt | **DEMO on this process** (`GET /api/health` `stripe=demo`) | **ENFORCED** amount = server `budget_estimate` (default 100) | Payments tests if present; D7 spec |
| Payment poll | `GET /api/payments/status/{session_id}` | May set held on live paid | Authenticated | Session exists | Stripe status if not DEMO | DEMO short-circuit | ENFORCED idempotent fulfill | — |
| Webhook | `POST /api/webhook/stripe` | Held write / HH activate | Stripe / DEMO no-op | Signature / DEMO | Live paid | DEMO no-op | ENFORCED when live | — |
| Marker escrow | `POST /api/requests/{id}/escrow?amount=` `place_escrow` | `escrow_amount`, `escrow_status=held` | Client owner | Client | **None** | **Internal marker** | **ENFORCED** write; **not** payment | — |
| Start work | `POST /api/requests/{id}/start` `start_work` | `status=in_progress`, `started_at` | Assigned specialist | `specialist_id == user` only — **not** `assigned` check, **not** escrow | **None** | REAL | **ENFORCED** identity only | Phase / confirm tests |
| Complete | `POST .../complete` `complete_work` | `status=completed` | Assigned specialist | Same | None | REAL | **ENFORCED** | — |
| Confirm | `POST .../confirm` `confirm_complete` | `confirmed`, `escrow_status=released`; wallet `+ escrow_amount*0.95`; `job_payment` | Client owner | Client + `status==completed` | Uses `escrow_amount or 0` — **payment not required** | Internal wallet | **ENFORCED** | Confirm / lead-credit / phase tests |
| Review | `POST .../review` `review_specialist` | `reviews` + specialist `rating` / `reviews_count` | Client owner | Client + `specialist_id` present — **not** `confirmed` | None | REAL | **ENFORCED** pair only | Review tests |
| Reputation | rating / `jobs_completed` / tier hooks | `users.rating`, `jobs_completed`, optional `verified` at 10 reviews ≥ 4.8 | System on confirm/review | — | None | REAL | ENFORCED increments | `tier_milestones` |
| Rebook eligibility | `GET /api/trusted-specialists` | Aggregation of `completed`/`confirmed` | Client | Role | None | REAL | **ENFORCED** | `test_gbos_growth_iter145.py` |
| Dispute | `POST /api/requests/{id}/dispute` | `disputed=True`, `escrow_status=frozen` | Client or assigned specialist | Pair + status `assigned\|in_progress\|completed` + escrow not `released` | Marker may be absent | REAL persist | **ENFORCED** | Orchestrator `dispute_opened` |

**No first-class request-cancel route** was found on `backend/routes/requests.py`.

---

# 3. Existing commercial surfaces

Status labels are **not collapsed**. A surface may be documented without being connected to D6.

| Surface | DOCUMENTED | IMPLEMENTED | EVIDENCED | CONNECTED to D6 pair-binding | AUTOMATED |
|---|---|---|---|---|---|
| **Marketplace Core** | `product_intelligence` key `marketplace_core` | `requests.py`, `marketplace_offers.py`, `matching.py` | Offer submit/select/assign code exists | **Yes** — `accept_offer` is the B writer; `/accept` is the A writer | `/accept` heavily tested; **no** dedicated `test_*offer*.py`; `OfferApplyForm` unmounted |
| **Marketplace Public & Trust** | `marketplace_public` | `marketplace.py`, `Marketplace.jsx`, `trust.py` / `public_trust.py` | Public specialist browse + card trust | **No** — browse/ranking only | `test_trust_growth_iter144.py` (trust rollup, not assignment) |
| **Trusted Specialists & Rebooking** | `trusted_specialists` | `trusted_specialists.py` | Rebook creates `open` + waive; list needs `completed`/`confirmed` | **Indirect** — rebook does **not** set `specialist_id`; later `/accept` does | `test_gbos_growth_iter145.py` |
| **Trust Score** | Multiple (marketplace cards, passport `_trust_score`, `propbenefits.trust_engine`) | Yes, several scores | Scores computed | **No** — ranking / display, not a gate on `accept_offer` | Passport trust tests; marketplace trust tests |
| **Specialist Verification / KYC** | `kyc.py` docstring; Atlas KYC row | `kyc.py` approve → `users.verified=True`, `tier=VERIFIED` | Flag written | **Copied** onto `specialist_verified` at assign; **not required** to submit or select | QA `PROFILE-SPEC-03`; KYC upload tests |
| **Property Passport** | `property_passport` | `property_passport.py` | Public QR / trust | **No** — not read by `accept_offer` | `test_cx3_passport_iter135.py` |
| **House Health** | `house_health` | plans, billing, recommendations | HH publish + `house_health_source` on request | **Attribution only** — `commission_status=captured` inside `accept_offer` | HH tests exist elsewhere; capture is try/except non-blocking |
| **Subscriptions & Billing** | `subscriptions_billing` | `house_health_billing.py` (no DEMO short-circuit) | HH Stripe checkout | **No** — different economy | HH billing tests if present |
| **Payment Transactions** | D7 + this spec | `payments.py` | `payment_transactions` rows | **No** — does not write `specialist_id` | D7 evidence; job checkout DEMO |
| **escrow_deposit / escrow_status** | D7 | Checkout path + `place_escrow` | Marker + optional `transactions.type=escrow_deposit` | **No** — may exist on `open` or after assign | — |
| **Stripe checkout/webhook** | D7 | `payments.py` | DEMO inserts fake `cs_demo_*`; live path exists in code | **No** | Health `checks.stripe=demo` (2026-09-22) |
| **Revenue War Room** | docs / `first_revenue.war_room` | `first_revenue.py`; CEO briefing reuses it | Aggregates paid orders / requests | **Observes** after the fact | — |
| **Beta Cockpit** | `/admin/beta-cockpit` | Admin UI + launch readiness | Gate metrics | **Observes** | `test_launch_readiness_iter139.py` route list |
| **AI Decision Ledger** | `ai_decision_ledger` | opportunities / learning / growth intel | Commercial-outcome scan | **Observes** opportunities, not Marketplace assign | `test_learning_engine_iter123.py` |
| **Lead & Intent Intelligence** | growth / opportunities / `lead_followup` | Partial | Intent ≠ job pair | **No** | Opportunity accept is a **different** `/client/opportunities/{id}/accept` |
| **Growth Intelligence** | `growth_intelligence.py` | Admin scan + daily job | Marketing insights | **No** | Agent registry documents ledger writes |

`/client/opportunities/{id}/accept` (`opportunities.py`, `HomeV2.jsx`, `PropertyHubV2.jsx`) is **not** Marketplace offer selection and **not** D6.

---

# 4. Existing commercial lifecycle (what the code uses)

| Concept | Intended meaning | What the code uses today |
|---|---|---|
| **OFFER SUBMITTED** | Specialist participates | `submit_offer` → `marketplace_offers.status=open` (flag-gated) |
| **OFFER SELECTED** | Client chose one | `accept_offer` → `selected_offer_id` + offer `won` |
| **COMMERCIAL RELATIONSHIP** | Platform recognizes the pair | **No dedicated object.** Same write as selection: `assigned` + `specialist_id` |
| **PAYMENT INITIATED** | Checkout started | Live: `payment_transactions.status=initiated`; DEMO skips to paid |
| **PAYMENT SUCCEEDED** | Money recorded | DEMO instant `paid`; live poll/webhook `paid` |
| **ESCROW HELD** | Held for work | `escrow_status=held` **internal marker** |
| **WORK STARTED** | Execution | `/start` → `in_progress` |
| **WORK COMPLETED** | Specialist marks done | `/complete` → `completed` |
| **CLIENT CONFIRMED** | Client accepts work | `/confirm` → `confirmed` |
| **SPECIALIST PAID** | Entitlement recorded | Same `/confirm` → internal `wallet_balance` + `job_payment` |
| **COMMISSION RECOGNIZED** | Platform 5% | Implicit `* 0.95` at confirm — no commission row (D8) |

`status=assigned` is written by: `accept_offer` · `accept_request` · campaign insert · `execute_auto_match`.

It currently means **all of**: specialist selected, de facto commercial pair, and (via notify + ungated `/start`) work permission. It does **not** mean payment or escrow.

---

# 5. Four candidate D6 events

## OPTION A — Client selects an offer  ← **CHOSEN**

Relationship exists when `accept_offer` succeeds.

| Topic | Evidence |
|---|---|
| `request.status` | `open` → `assigned` |
| `marketplace_offer` | Winner `won` + `won_at`; others `lost` + `lost_at` |
| When `specialist_id` is authoritative | **This write** |
| When specialist may start | Notify immediately; `/start` only checks `specialist_id` (today) |
| Cancellation | **No** request-cancel route on this spine |
| Select, never pays | Relationship **exists**; `/start` allowed; confirm with `escrow_amount` null → 0 payout |
| Payment succeeds, never starts | Relationship already exists; stays `assigned` |
| Escrow released / refunded | Confirm or dispute resolve later; does **not** unset `specialist_id` |
| Commission due | Still `/confirm` `* 0.95` (D8 realization still open) |
| Review / reputation | Review allowed once `specialist_id` is set |
| Rebooking | Later list uses `completed`/`confirmed` with this `specialist_id` |
| `/accept` | Parallel writer of the same fields **without** `selected_offer_id` — D13 |
| Lead Credits | **Not** consumed here (D2 = submit; today A-path consumes on `/accept`) |
| Stripe | Not called |
| Escrow marker | Not written |

## OPTION B — Successful payment

Relationship exists when `payment_transactions.payment_status=paid` (or DEMO equivalent) after selection.

| Topic | Evidence |
|---|---|
| `request.status` | **Unchanged by payment today** — already `assigned` or still `open` |
| Offer | Unchanged |
| `specialist_id` | May be **empty** — checkout allows `open` |
| Start | Still ungated by pay |
| Select, never pays | Would **not** be a relationship (new vs today) |
| Pay, never starts | Relationship would exist without execution |
| Escrow refund | No generic Stripe refund on job checkout |
| Commission | Still confirm unless D8 moves |
| `/accept` | Would still bind `specialist_id` before pay — conflict |
| Lead Credits | Unchanged |
| Stripe | DEMO = instant “success”; not production custody |
| Marker | DEMO sets held in the **same** function — would collapse B and C on DEMO |

**Rejected:** payment is a D7 event. Checkout can bind money to a request with **no specialist**. DEMO success is not a commercial activation policy.

## OPTION C — Escrow successfully held

Relationship exists when `escrow_status=held`.

| Topic | Evidence |
|---|---|
| Writers | DEMO checkout **or** `place_escrow` (client-chosen `amount`, **no debit**) |
| Payment required? | **No** on `/escrow` |
| External money? | **No** on this process |
| Start | Not gated on held |
| `/escrow` | Client-controlled commercial field |

**Rejected:** internal marker; client can fake “held”. Must not be called true escrow / Connect. Unsafe as D6.

## OPTION D — Explicit commercial activation after selection/payment

A new named event after selection and/or payment, distinct from `assigned`.

| Topic | Evidence |
|---|---|
| Existing object? | **None.** No `commercial_relationship` collection or activation route |
| Would require | New state or new write after `accept_offer` / paid |
| vs reuse rule | **New engine / new event** — forbidden unless existing fields cannot represent the pair |
| Existing fields | `assigned` + `specialist_id` + `selected_offer_id` **already** represent the pair |

**Rejected:** invents an activation step the repository does not have and does not need for D6.

---

# 6. Comparison matrix

| Topic | A Selection | B Payment success | C Held marker | D New activation event |
|---|---|---|---|---|
| Extra states / engines | **No** | Gate `assigned` on pay, or new meaning | Trust a client-writable marker | **Yes — new event** |
| Matches D1 sequence (select → relation → pay) | **Yes** | Inverts (relation after pay) | After marker | After select+pay |
| Matches current B code | **Yes** | No | No | No |
| Client choice is the deal | **Yes** | Choice is only a precursor | Choice is only a precursor | Choice is only a precursor |
| Pay-before-select hole | Still possible (checkout `open`) — D7 | Must forbid `open` checkout | Same | Same |
| Unpaid work today | Allowed | Forbidden by definition | Forbidden if held required | Depends on design |
| `/escrow` fake hold | Irrelevant to D6 | Irrelevant | **Unsafe** | If gated on held, same risk |
| DEMO Stripe | Orthogonal | DEMO = instant relation | DEMO sets held | Would fire on DEMO paid |
| D2 credits | Already spent at submit (target) | Unchanged | Unchanged | Unchanged |
| Job 5% | Still confirm (D8) | Still confirm unless moved | Same | Same |
| HH % capture | **At this event today** | Would desync | Would desync | Would desync unless moved |
| Compatible with distinct pay/escrow/exec/confirm/payout | **Yes** | Collapses relation with pay | Collapses relation with marker | Adds a sixth binding event |

---

# 7. Client trust

Inspected existing mechanisms only. **No Client Verification Engine proposed.**

| Signal | Where it exists | Enforced on create request? | Enforced on `accept_offer`? | Role vs D6 |
|---|---|---|---|---|
| Authenticated identity | JWT cookie + `require_role("client")` | **Yes** | **Yes** | **Prerequisite** (existing) |
| Owned property | `properties.owner_id == user.id` | **Yes** on `create_request` | **Indirect** (request already owned) | **Prerequisite** for the request, not re-checked as a new engine |
| Property registered | `properties` document | Must exist | Request must exist | Available / required for request create |
| Email verification | `users.email_verified`; `auth.py` verify routes | **No** | **No** | **Available only** (experience tiers / PropBenefits / admin filters) |
| Phone verification | `users.phone_verified` (consent backfill default false; SMS not implemented) | **No** | **No** | Available only |
| Google auth | Treated as email-verified in `experience_tiers.py` | Not on Marketplace write | No | Available only |
| Property Passport | `property_passport.py` | No | No | Evidence / viral surface — **not** a D6 gate |
| House Health | Subscription + recommendations | No | Only HH attribution if `house_health_source` present | Different economy |
| Digital Twin | Twin unlock / projects | No | No | Different product |

**Currently enforced for commercial activation (A):** authenticated client + ownership of the request.  
**Merely available:** email/phone verification, Passport, House Health, Twin.

D6 does **not** add client KYC. Founder may later require `email_verified` as a **reuse** of the existing flag — that is a policy add-on, not a new engine, and is **not** decided here.

---

# 8. Specialist trust

Inspected existing signals only. **No Trust Engine proposed.**

| Signal | Where | Used as D6 prerequisite today? | Correct use |
|---|---|---|---|
| `users.verified` | Register false; KYC approve true; review auto-upgrade at 10× ≥ 4.8 | **No** — copied to `specialist_verified` only | **Ranking / display / optional future gate** |
| KYC (`kyc_documents`, `kyc_status`) | `kyc.py` pipeline | **No** on submit or select | Verification flow — **not** relationship create |
| Tier / experience tier | `tier`, `experience_tiers.py` | Ranking weight in `_compute_score` (0.20) | **Ranking** |
| Capabilities / catalog | `capability_engine.py` | Not read by `accept_offer` | Progression |
| Certifications / documents | specialist documents + admin review | Not a select gate | Verification |
| Rating / reviews | `users.rating`, `reviews` | Ranking (0.30); review **after** `specialist_id` | **Reputation after the pair exists** |
| Trust Score (marketplace / PB / passport) | Several implementations | Card / ranking | **Ranking** |
| Complaints / disputes | `disputes.py` | Allowed **after** `assigned` | Post-relationship |
| Punctuality | Building health component, not specialist assign | No | Unrelated to D6 |
| `medic_suspended` | Marketplace public filter | Public browse; matching skip | **Eligibility to appear**, not D6 itself |

**D6 prerequisite (existing):** specialist is the author of the **open** offer being accepted (`offer.specialist_id`).  
**Not a D6 prerequisite today:** `verified`, KYC approved, rating floor.

Those remain **ranking / reputation / eligibility-to-offer** signals. Making KYC mandatory to **submit** an offer is a D2/eligibility policy, not a D6 event change.

---

# 9. Payment / escrow evidence

Full graph is in D7. D6 only needs the distinction.

| Layer | What it is | What it is not |
|---|---|---|
| **DEMO Stripe payment** | `DEMO_STRIPE` true → insert `cs_demo_*`, `payment_status=paid`, `demo:true`; **does not call Stripe** | Live charge |
| **REAL Stripe payment** | Code path when key starts with `sk_test_` / `sk_live_`: Checkout + poll/webhook | Proven on **this** process (health `stripe=demo`) |
| **DATABASE ESCROW MARKER** | `requests.escrow_status=held` + `escrow_amount` | Custody |
| **TRUE PAYMENT ESCROW / CONNECT** | **NOT FOUND** | Do not describe the marker as Connect |

Checkout eligibility today: request `open` **or** `assigned`. Selection is **not** required to pay.  
`/start` does **not** require held.  
`/escrow` does **not** require payment.

Therefore payment and escrow **cannot** be the D6 event without rewriting those gates (D7), and even then they would collapse distinct economic events.

---

# 10. Commission separation

Do **not** merge:

| Concept | Object | Event today | Relation to D6 |
|---|---|---|---|
| House Health 15/10/5 | `hh_plans.lead_commission_pct` | **Captured** on `accept_offer` (on apply **fee**, not job value) | Happens **at** D6 on the B path; still ≠ job commission |
| Marketplace Lead Credits | `users.lead_credits` | Target D2 = `submit_offer`; runtime = `/accept` | **Before** D6 |
| 45 RON legacy assignment fee | `LEAD_FEE_RON` / `lead_fee` tx | `/accept` wallet fallback | Model A residual |
| Hardcoded 5% job commission | `amount * 0.95` | `/confirm` | **After** D6 |
| `platform_config` / `fee_configs` commission | Admin dead / unused for confirm | Not applied | Do not use as D6 |
| Partner / Verified Estate commission | Other products | Other checkouts | Unrelated |

**Which event should eventually make the Marketplace job commission commercially due?**  
Not D6. Current code: **`/confirm`**. Realization trigger remains **D8**. D6 only guarantees the pair exists before that calculation.

---

# 11. `/accept` reconciliation impact

## Classification

**DEPRECATE** as a **public Marketplace** commercial-relationship writer.

Not KEEP PUBLIC (would compete with D1).  
Not REDIRECT (that is implementation).  
Not REMOVE LATER in this document (residual callers exist).  
Residual waived/direct use is **isolated until D13** (functionally INTERNAL-ONLY for those paths, still a public HTTP route today).

## Current writers of `assigned` + `specialist_id`

| Path | Calls `/accept`? | Creates relationship how | Keep until D13? |
|---|---|---|---|
| Ordinary Marketplace (Model A live) | **Yes** — specialist | First-wins assign + 45 credits/RON | **Must not remain public** once B is live |
| Model B select | **No** — `accept_offer` | Client choice | **Canonical D6** |
| Rebooking | **Yes** — target specialist, fee waived | Client created `open` + `direct_specialist_id`; specialist `/accept` sets pair | **Yes** — product feature |
| Maintenance-direct | **Yes** — same waive pattern | Same | **Yes** |
| Campaign | **No** — insert `assigned` | `accept_campaign_offer` | **Yes** — sibling |
| Admin / cron auto-match | **No** | `execute_auto_match` | Operator residual |
| Tests / QA | **Yes** | Fixture path | Update when D13 lands |
| `ActivityTimeline.jsx` / Specialist dashboard | **Yes** | Public A UI | Public residual |

Do **not** remove `/accept` because Model B is canonical. Rebook and maintenance-direct **depend** on it to set `specialist_id` after a client-created direct `open` request.

D6 invariant: **at most one public writer of `assigned` on an ordinary open Marketplace request.** That writer is `accept_offer`.

---

# 12. Existing infrastructure reuse map

EXISTING COMPONENT → ROLE IN TARGET COMMERCIAL LIFECYCLE

| Existing component | Role |
|---|---|
| `requests` + `status` / `specialist_id` / `selected_offer_id` | **Commercial pair + job spine** |
| `marketplace_offers` | Offer lifecycle (`open`/`won`/`lost`/`withdrawn`) |
| `submit_offer` | D2 participation (target) |
| `accept_offer` | **D6 event** |
| `GET /api/match` + ranking | Discovery / ranking — not the relationship |
| JWT + `require_role` + property `owner_id` | Client identity / ownership |
| `users.email_verified` / KYC / `users.verified` | Available trust — not new engines |
| Marketplace / PB / Passport trust scores | Ranking / public trust |
| `trusted_specialists` + rebook | Repeat relationship **after** `completed`/`confirmed` |
| `payments.create_checkout_session` + `payment_transactions` | Payment (D7) |
| `escrow_status` / `escrow_amount` | Internal hold marker (D7) |
| `/start` `/complete` | Execution |
| `/confirm` + `job_payment` + `wallet_balance` | Confirmation + **internal** payout (D8) |
| `reviews` + rating + `jobs_completed` | Reputation |
| `disputes` | Post-relationship conflict |
| `transactions` | Ledger fragments (offer fee, escrow_deposit, job_payment, lead_credit, lead_fee) |
| HH `house_health_source` capture | Attribution at selection — not job 5% |
| War Room / Beta Cockpit / AI ledger / growth intel | Observe — do not create the pair |
| `/accept` | Residual assign for waived/direct until D13 |

If it already exists, D6 does **not** replace it.

---

# 13. Target state / event model

Smallest model. **No new state** unless an existing one cannot represent the lifecycle.

| Layer | Existing field / state | D6 meaning |
|---|---|---|
| **REQUEST STATE** | `open` → `assigned` → `in_progress` → `completed` → `confirmed` | `assigned` = pair exists (D6). Later states = execution/confirm. |
| **OFFER STATE** | `open` / `won` / `lost` / `withdrawn` | `won` = the selected offer. |
| **COMMERCIAL RELATION STATE** | **Reuse** `assigned` + `specialist_id` + `selected_offer_id` | **No new field.** Implicit relation = these three. |
| **PAYMENT STATE** | `payment_transactions.payment_status` pending/paid (+ DEMO) | Distinct. Not D6. |
| **ESCROW STATE** | `escrow_status` held/released/frozen | Distinct marker. Not D6. |
| **EXECUTION STATE** | `in_progress` / `completed` | Distinct. `/start` after D6. |
| **PAYOUT STATE** | `confirmed` + `job_payment` + wallet inc | Distinct. `/confirm`. |

Public Model B event order (conceptual, not all gated today):

```
request.created          (open)
offer.submitted          (D2 target)
offer.accepted           (D6)  → assigned + specialist_id + selected_offer_id
[payment / escrow]       (D7)  → optional / DEMO / marker today
work.started
work.completed
work.confirmed           (D8 realization today)
review / reputation
rebook                   (new open request; pair via residual /accept)
```

Do **not** add `commercial_status=active`. That would be Option D.

---

# 14. D6 canonical event

### D6 — COMMERCIAL RELATIONSHIP EVENT

**A. Client selects an offer.**

**Why this is compatible:**

| Constraint | Compatibility |
|---|---|
| **D1 Model B** | D1 sequence is offers → **client choice** → relationship → payment. A is that choice. |
| **D2 Lead Credits** | Credits buy participation at `submit_offer`. D6 does **not** debit again. |
| **Client choice** | The client is the actor. Specialist cannot self-create the public pair. |
| **Stripe** | Uninvolved. DEMO/live payment stays D7. |
| **Escrow** | Marker stays D7. Held ≠ relationship. |
| **Commission** | Job 5% stays a later D8 event (`/confirm` today). HH 15/10/5 capture already sits on `accept_offer` — same moment as D6, different economy. |
| **Cancellation / refund** | Pair exists even if unpaid; refunds attach to payment rows (D7), not to “whether the pair existed”. |
| **Execution** | `/start` remains a later event. D6 does not require pay-before-work; D7 decides that gate. |
| **Reputation** | Review already keys off `specialist_id`. Rebook already keys off later `completed`/`confirmed`. |
| **Rebooking** | Repeat hiring reuses the **completed pair**, then a new request. It does not redefine D6. |

**Why not B/C/D:** payment is DEMO and can precede selection; held is a client-writable marker; a new activation event is an unnecessary engine.

---

# 15. Invariants

1. Offer submitted ≠ offer selected.  
2. Offer selected **is** the public commercial relationship (D6).  
3. Payment ≠ relationship.  
4. Escrow marker ≠ relationship and ≠ real custody.  
5. Execution ≠ confirmation ≠ payout.  
6. Lead Credits ≠ job commission ≠ House Health lead attribution.  
7. At most **one** `specialist_id` per request.  
8. Public ordinary `open` requests: **only** `accept_offer` writes the pair.  
9. No client-controlled field (`place_escrow` amount, self-set commission) may create or authorize D6.  
10. D6 must not consume Lead Credits.  
11. DEMO checkout must not be specified as production custody.  
12. No new relationship engine while `assigned` + `specialist_id` + `selected_offer_id` can represent the pair.  
13. Rebook / campaign / admin-match are **residual writers**, not the public D6 event.  
14. Selection must not silently be called payment.

---

# 16. Open decisions (not solved here)

| Decision | What remains open | What D6 already fixes |
|---|---|---|
| **D7 Payment / Escrow** | Pay-before-work? Escrow mandatory? Checkout on `open`? Advance/partial? Real vs DEMO? | Relationship exists **before** those gates |
| **D8 Commission** | Realization trigger; gross SSOT; explicit ledger; refund vs 5% | Pair exists; 5% is **not** due at D6 unless D8 later says so |
| **D9 Client 3-free experiences** | What unit is “free” (create vs select vs pay vs confirm) | D6 = select. D9 may count this event or another — founder later |
| **D10 Subscriptions** | HH/DT subscription vs Marketplace | Unrelated economy |
| **D11 House Health 15/10/5** | Whether capture stays on `accept_offer`; whether % is on apply fee vs job | Capture **time** currently = D6; amounts must not merge |
| **D13 Legacy `/accept`** | Isolate rebook/maintenance vs public A; flag; UI | Public writer = `accept_offer`; `/accept` = **DEPRECATE** for ordinary opens |

---

# 17. Implementation impact map

**No implementation authorized.**

If later authorized, D6 as A is **naming + isolation**, not a new state machine:

| Change | Needed for D6 itself? | Notes |
|---|---|---|
| New collection / `commercial_status` | **No** | Would be Option D |
| Enable `multi_offer_enabled` | **No** | D1/D13 runtime, not D6 definition |
| Move Lead Credit debit to `submit_offer` | **No** | D2 |
| Forbid checkout on `open` | **No** | D7 hygiene once D6 = selection |
| Gate `/start` on payment/held | **No** | D7 |
| Hide / isolate public `/accept` | **D13** | Required so two public writers cannot bind one `open` request |
| Tests for `accept_offer` | When B is enabled | Missing dedicated offer tests today |
| Mount `OfferApplyForm` | When B is enabled | Submit UI currently unmounted |

---

# 18. Test implications

| Area | Today | When D6 is implemented (later) |
|---|---|---|
| `accept_offer` | Frontend caller only; **no** `test_*offer*.py` | Must assert `assigned` + `specialist_id` + `selected_offer_id` + won/lost + **no** credit debit + **no** escrow write |
| `/accept` on ordinary open | Many tests treat this as the pair | D13 must stop using it as the public Marketplace fixture |
| Rebook / maintenance | `test_gbos_growth_iter145.py` expects `/accept` waived | Keep until a residual assign path exists |
| Campaign | Inserts `assigned` | Sibling — do not force through `accept_offer` |
| Checkout on `open` | Allowed | D7 must decide; D6 tests must **not** require pay to set the pair |
| Confirm 0.95 | Exists | Must not move to D6 |
| Review without confirm | Allowed if `specialist_id` set | Compatible with D6 = selection |

---

# 19. Risks

| Risk | Evidence | Severity if D6 = A |
|---|---|---|
| Unpaid work | `/start` ungated; notify “Poți începe” | Policy — D7, not a reason to move D6 to payment |
| Two public assign writers | `/accept` has no flag | **D13 blocker** for a clean public B |
| Pay without specialist | Checkout `open` | Money can exist without a D6 pair — D7 |
| Client-fake escrow | `/escrow?amount=` | Must not be mistaken for D6 or custody |
| Model B island | Flag default false; apply form unmounted | D6 is decided; runtime still A |
| HH capture at select | On apply fee, not job value | Do not treat as job commission |
| Review before confirm | Allowed | Reputation can start at D6 — acceptable; tightening is optional later |
| Auto-match / campaign assign | Bypass client offer choice | Residual — must not overwrite a B `selected_offer_id` on an ordinary public open |
| Calling DEMO paid “activation” | Same function as held | Would make every demo checkout a relationship — rejected |

---

# 20. Explicit statement

**No implementation performed.**

No application code, database schema, configuration, Marketplace flag, `/accept` deletion, Stripe, prices, credits, commit, or deploy was changed by this decision.

---

# STATUS

**DECISION SPECIFICATION — READY FOR FOUNDER APPROVAL**

D6 canonical public event: **client selects an offer** (`accept_offer` → `assigned` + `specialist_id` + `selected_offer_id`).

No implementation authorized.

**STOP.**
