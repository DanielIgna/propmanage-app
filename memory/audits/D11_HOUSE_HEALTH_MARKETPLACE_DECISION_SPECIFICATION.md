# D11 — HOUSE HEALTH ↔ MARKETPLACE COMMERCIAL RELATIONSHIP

**Decision:** D11 — What House Health is allowed to do to Marketplace access, participation, attribution, and job commission  
**Mode:** READ-ONLY. No implementation, schema, DB, prices, flags, Model B, `/accept`, credits, Stripe, escrow, commission, UI, commit, or deploy.  
**Given:** D1 = Model B · D2 = Lead Credits on `submit_offer` · D6 = relationship at `accept_offer` · D8 = Marketplace job commission is the 5% specialist haircut at `/confirm` and is **not** HH 15/10/5  
**Date:** 2026-09-23

D8 is **not** reopened by this document.

**No implementation performed.**

---

# 1. Executive decision

**What House Health currently does**

- Sells a **client subscription** (`hh_plans` → Stripe checkout → `hh_subscriptions`).  
- Gates **House Health module** features (`F_HOUSE_HEALTH_BASIC` / advanced) and **Digital Twin advanced** (`F_DIGITAL_TWIN_ADVANCED` = Premium in `entitlements.py`).  
- Can **publish** a recommendation as a normal Marketplace `request` with `house_health_source` metadata.  
- **Snapshots** `lead_commission_pct` (15 / 10 / 5 seed) onto that request.  
- **Captures** `offer_fee * (pct/100)` at Model B `accept_offer`. Status becomes `captured`. **`paid` is never written. No money moves.**

**What it does NOT do**

- Does **not** gate `POST /api/requests`, offer list, `accept_offer`, `/accept`, checkout, escrow, `/start`, or `/confirm`.  
- Does **not** change Lead Credits, apply fees, ranking, matching, verification, or D8’s `* 0.95`.  
- Does **not** grant the UI-advertised **trial days** (no runtime writer of `status=trial` from `trial_days`).  
- Does **not** implement “3 free client projects.”

**Marketplace entitlement gate:**  
**NO PROVEN RUNTIME MARKETPLACE ENTITLEMENT GATE.**

**15 / 10 / 5 meaning:** House Health **lead-attribution metadata** on the **offer/apply fee**, snapshotted at publish, captured at D6. Not job commission.

**79 vs 249:** seed Premium = **79 EUR**; public pricing UI **reads the DB**; **249 is not hardcoded** in `PricingPage.jsx`. Target DB value was not read in this task.  
**OPEN — FOUNDER PRICING DECISION.**

**D11 STATUS:** **READY FOR FOUNDER APPROVAL** on current runtime meaning. Future entitlement model (A–E) and Premium price remain founder choices — unranked.

---

# 2. Current runtime evidence (verified this pass)

| Object | File / symbol | Fact |
|---|---|---|
| Plan seed | `house_health_billing.DEFAULT_PLANS` | Basic 9 / Pro 29 / Premium **79**; trial_days 7 / 14 / 14; lead_commission_pct 15 / 10 / 5 |
| Seed insert | `seed_default_plans` | Inserts **only if slug missing** — does not overwrite env DB |
| Checkout amount | `house_health_billing.create_checkout_session` | `amount = float(plan.price_eur)` from **`hh_plans`**. Frontend sends **slug only** |
| Stripe | Same file | **No DEMO short-circuit.** Missing `STRIPE_API_KEY` → 503. Checkout is one-shot, **not** Stripe Subscription mode |
| Activation | `_activate_subscription_if_paid` | On paid: `hh_subscriptions.status=active`, `expires_at = now/existing + _billing_days` (30 / 365 / 90). **Does not read `trial_days`** |
| Public pricing UI | `PricingPage.jsx` | `GET /api/house-health/plans` → `plan.price_eur`. Displays `trial_days` if > 0 |
| HH feature gate | `house_health._assert_house_health_entitlement` | 402 unless `F_HOUSE_HEALTH_BASIC` (specialist/admin bypass) |
| DT gate | `digital_twin.py` | `F_DIGITAL_TWIN_ADVANCED` |
| Marketplace create | `requests.create_request` | Property ownership only — **no** `require_entitlement` |
| Offer submit / select | `marketplace_offers.py` | **No** HH subscription read except capture block on `accept_offer` |
| Confirm 5% | `requests.confirm_complete` | **Does not** read `house_health_source` |
| HH publish | `house_health_recommendations.publish` | Twin owner; writes request + `house_health_source`; % from active/trial sub plan or **default 10** |
| HH capture | `accept_offer` | `commission_amount = offer_fee * pct/100`; status `captured` |
| HH paid | — | **NOT FOUND** |

---

# 3. D11.1 — House Health’s role vs Marketplace

| Claim | Classification | Evidence |
|---|---|---|
| **A. Grants Marketplace access** | **NOT FOUND** | `create_request` / offer / select ungated by `hh_subscriptions` |
| **B. Additional Marketplace visibility** | **UI ONLY** / **NOT FOUND** | Plan `features[]` copy (“recomandări prioritate”, “comision marketplace lead minim”). Ranking formula does not read HH |
| **C. Changes Lead Credit economics** | **NOT FOUND** | Credits on `/accept`; D2 = `submit_offer`. No HH read |
| **D. Changes offer / apply fee** | **NOT FOUND** | 5–50 from offer body + wallet |
| **E. Changes job commission** | **NOT FOUND** | D8 `* 0.95` independent |
| **F. Changes ranking** | **NOT FOUND** | `marketplace_offers._compute_score` = fee/rating/tier/recency/fairness |
| **G. Changes verification** | **NOT FOUND** | KYC / `users.verified` / email_verified unrelated to HH plan |
| **H. Changes matching** | **NOT FOUND** | `matching.py` has no HH fields |
| **I. Changes Marketplace limits** | **NOT FOUND** | Offer cap 5 is global; no plan quota on requests |
| **J. Changes nothing operationally on the job spine** | **IMPLEMENTED** for ordinary create/accept/pay/confirm | True except the publish/attribution bridge |
| **K. Other documented behavior** | **IMPLEMENTED (partial)** | (1) Entitlement gates **HH/DT products**. (2) Publish rec → `request` + attribution. (3) Capture metadata at D6. (4) `GET .../marketplace-stats` aggregates `house_health_source` |

Do not infer A–I from upgrade copy or seed `features[]`.

---

# 4. D11.2 — Client House Health → Marketplace

| Client capability | HH plan effect |
|---|---|
| Create Marketplace request | **None.** Auth + owned `property_id` |
| Number of requests / projects | **No quota** |
| View offers | Request owner / admin / offering specialist — **not** HH |
| Select specialist (`accept_offer`) | Client owns request — **not** HH (HH only captured if `house_health_source` present) |
| Property / client verification | **None** |
| Access to specialists | Public marketplace browse ungated by HH |
| Priority / matching / support | Seed/UI language only |
| Escrow / payment | Job checkout is `payments.py` (DEMO); HH checkout is a **different** Stripe session |

**Is there `House Health subscription → Marketplace entitlement`?**

`entitlements.py` maps `hh_subscriptions` → client tiers → **HH/DT feature flags**.  
`require_entitlement()` exists. **Marketplace `create_request`, `list_requests`, `accept_offer`, `submit_offer`, checkout, `/confirm` do not use it.**

**NO PROVEN RUNTIME MARKETPLACE ENTITLEMENT GATE.**

---

# 5. D11.3 — Specialist House Health → Marketplace

`entitlements.py`: specialist is **not** a paying HH user. Specialist “Pro/Verified” = `experience_tier`, not `hh_plans`.

| Specialist capability | HH subscription effect |
|---|---|
| Submit offers | **None** (`multi_offer_enabled` + wallet apply fee) |
| Lead Credits | **None** |
| Wallet / apply fee | **None** |
| Ranking / visibility | Specialist `tier` in ranking ≠ HH plan |
| Verified / KYC | **None** |
| Matching / compatibility | **None** |
| Job commission | **None** (D8) |
| Access to requests | Open-list rules; `direct_specialist_id` |
| Offer count / priority | Global cap 5; sponsored = extra apply RON |

**“Pro/Premium” on specialist UI ≠ House Health plan.**  
`App.js` “Comision standard 15%” on specialist tiers is **landing copy**, not `hh_plans` and not `/confirm`.

Specialists creating HH **evaluations** bypass the client HH 402 (`role == specialist`).

---

# 6. D11.4 — 15 / 10 / 5 evidence table

Do **not** reinterpret as D8 job commission.

| Stage | Source | Collection / field | Event | Caller | Payer | Payee | Money moves? | Metadata? | Snapshot? | Settled? | Affects payout? | Analytics? | Ranking? | Offer price? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Seed / admin write | `DEFAULT_PLANS` / `house_health_plans` PATCH | `hh_plans.lead_commission_pct` | Admin save / seed | Admin | — | — | No | Plan config | — | No | No | No | No | No |
| Publish read | Active/trial `hh_subscriptions.plan` → `hh_plans` | copied to `requests.house_health_source.commission_pct` | Publish rec → request | Client twin owner | — | — | No | Yes | **Yes** | No (`pending`) | No | `hh_audit_log` publish | No | No |
| Default if no sub | hardcoded `10.0` | same field | Publish without plan | same | — | — | No | Yes | Yes | No | No | — | No | No |
| Rec link | same % | `hh_recommendations.marketplace_commission_pct` | Publish | same | — | — | No | Yes | Yes | No | No | — | No | No |
| Capture | snapshot % × `fee_paid_total` | `house_health_source.commission_amount` / `commission_status=captured` | `accept_offer` (D6) | Client select | **Not charged** | **Not paid** | **No** | Yes | Yes | **No** (`paid` never written) | **No** | `hh_audit_log` `commission_captured`; `marketplace-stats` avg % | No | Uses apply fee as **base only** |
| Confirm | — | — | `/confirm` | — | — | — | D8 5% only | — | — | — | **No HH %** | Admin GMV uses escrow, not HH % | No | No |

UI: `RecommendationsSection.jsx` — “X% **din fee-ul lead-ului**.”  
`HouseHealthUpgradePage.jsx` shows `lead_commission_pct` on the plan card.

---

# 7. D11.5 — Recommendation → Marketplace flow

```
HH evaluation (specialist)
  → hh_recommendations (specialist/admin)
  → POST publish (client twin owner)
       → requests insert  status=open  + house_health_source (pct pending)
  → specialists may submit_offer   (flag; no HH gate)
  → accept_offer (D6)              capture HH % on apply fee
  → payment / escrow / start       ordinary Marketplace (D7)
  → /confirm                       D8 5% only
```

| Link | Status |
|---|---|
| Recommendation create | **IMPLEMENTED** |
| Publish → Marketplace request | **IMPLEMENTED** |
| Lead attribution metadata | **IMPLEMENTED** (snapshot + capture) |
| Specialist selection | Ordinary D6 — **not** HH-forced |
| Offer creation | Ordinary B path — **not** auto-created from rec |
| Commission capture | **IMPLEMENTED** metadata |
| Commission settlement | **NOT FOUND** |
| Conversion tracking | **PARTIAL** — `GET /api/house-health/marketplace-stats` counts published / status / avg pct |
| Auto-publish | Docstring mentions F4.4 later; publish is **manual** |

Publish does **not** require an active subscription (defaults to 10%). It **does** require twin ownership and rec priority `urgent`/`recommended`.

---

# 8. D11.6 — Trials

| Claim | UI / seed | Runtime |
|---|---|---|
| Basic 7 days | `trial_days: 7`; PricingPage / UpgradePage render if > 0 | **Not granted** |
| Pro 14 days | same | **Not granted** |
| Premium 14 days | same | **Not granted** |
| Trial start | — | **No writer** of `status=trial` from `trial_days` |
| Trial expiration | Entitlement layer **would** honor `status=trial` + `expires_at` if such a row existed | Rows are created as **`active` after paid** |
| Activation | Paid checkout → `active` + 30/365/90 days | **IMPLEMENTED** |
| Renewal | One-shot pay extends `expires_at` | **PARTIAL** — not Stripe Subscription auto-renew |
| Cancel | `POST /api/me/subscription/cancel` → `cancelled`; access until `expires_at` | **IMPLEMENTED** |
| Entitlement | `entitlements._fetch_active_subscription` includes `trial` | **CONFIGURED BUT UNUSED** by billing writer |

**UI PROMISE ≠ PROVEN RUNTIME.**

---

# 9. D11.7 — Plan pricing SSOT

| Source | Values | Role |
|---|---|---|
| `hh_plans.price_eur` in **DB** | Env-specific; seed fills only empty slugs | **Checkout + public API SSOT** |
| `DEFAULT_PLANS` | 9 / 29 / **79** | Seed if missing |
| `PricingPage.jsx` / `HouseHealthUpgradePage.jsx` | `plan.price_eur` from API | **UI reads SSOT** — not hardcoded 249 |
| `upgradeNudge.js` | Basic **9** hardcoded in CTA copy | **UI-only nudge** — not checkout |
| Admin `AdminHouseHealthPage.jsx` | Edits DB `price_eur` | Writer of SSOT |
| `stripe_price_id` | Optional auto-provision | **Unused by checkout** (amount+currency session) |
| App settings VE prices | Audit/twin RON | **Other product** |
| Hardcoded 249 in frontend | **NOT FOUND** | — |

**Conflicts:** seed 79 vs founder/PRD 249; nudge Basic 9 vs DB if admin changed Basic; seed `features[]` (“Digital Twin inclus”) vs `TIER_FEATURES` (DT advanced = **Premium only**); `upgradeNudge` maps DT advanced to **CLIENT_PRO**.

**1. Runtime SSOT for charge:** `hh_plans.price_eur` (server).  
**2. UI source:** same API (plus nudge hardcode 9).  
**3. Checkout source:** same field.  
**4. Conflicts:** 79 seed / 249 founder / unknown target DB.  
**5. Dead:** `stripe_price_id` for current checkout.

---

# 10. D11.8 — Premium 79 vs 249

| Fact | Evidence |
|---|---|
| Seed Premium | **79.0 EUR** |
| Pricing page | Displays **whatever is in `hh_plans`** |
| 249 in application source | **Not hardcoded** in pricing/checkout |
| 249 in docs | `memory/PRD.md` Task 3: *prod will show founder Premium 249 because it reads `hh_plans` per environment* |
| Multiple plans | slugs `basic` / `pro` / `premium` / optional `custom`→PRO tier. No separate “249” slug in seed |
| Target DB `price_eur` | **Not queried in this read-only file task** → **UNKNOWN** |

**249 is not proven as current runtime.**  
**79 is the seed default, active only if that slug was never overwritten.**  
**OPEN — FOUNDER PRICING DECISION.**  
This document does **not** choose 79 or 249.

---

# 11. D11.9 — “3 free client projects”

Nearby objects that are **not** this quota: 135/45 Lead Credits; experience “3 jobs”; FC quest “3 cereri”; HH `trial_days`; DT FREE twin project tests; `entitlements` FREE = property create + technical record only.

**NOT IMPLEMENTED / NO RUNTIME SOURCE FOUND.**

Keep separate:

3 free Marketplace experiences ≠ client verification ≠ House Health trial ≠ Lead Credits.

---

# 12. D11.10 — Verified client

| Signal | Exists | Combined with HH into “verified client”? |
|---|---|---|
| Authenticated JWT | Yes | No compositional rule |
| `email_verified` | Yes | **Not** required for HH checkout or Marketplace create |
| `phone_verified` | Field; SMS not implemented | No |
| Owned / registered property | Yes for `create_request` and HH publish property | Independent of subscription |
| KYC | Specialist-oriented | No client KYC-from-HH |
| Entitlements tier | Yes | Means **paid/accessible HH plan**, not identity verification |

**No existing rule:** authenticated + verified contact + owned property + active subscription → verified client.

HH subscription is **access to HH/DT features**, not a verification badge.

---

# 13. D11.11 — Commercial percentage separation

| # | Mechanism | Payer | Payee | Base | Trigger / event | Runtime | Ledger | Refund | SSOT |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Lead Credits | Specialist | Platform inventory | 45 units | `/accept` now; D2 = `submit_offer` | Runtime A | `lead_credit` | No refund on consume | `users.lead_credits` |
| 2 | Apply / offer fee | Specialist | Platform wallet | 5–50 RON | `submit_offer` | Flag-gated | `marketplace_offer_fee` | Withdraw = no refund | Offer body + wallet |
| 3 | HH `lead_commission_pct` | Nobody (unsettle) | Nobody | **Apply fee** | Publish snapshot; capture at D6 | Metadata | `hh_audit_log` only | n/a | `hh_plans` → request snapshot |
| 4 | Marketplace job commission (D8) | Specialist (haircut) | Platform by omission | `escrow_amount` | `/confirm` | Hardcoded 5% | `job_payment` **net** | Dispute only | Code `0.95` |
| 5 | Verified Estate commission | Seller (VE product) | VE | Sale price | VE settings / UI | Other product | VE orders | VE-specific | `app_settings.pricing.commission_pct` |
| 6 | Partner commissions | — | — | — | — | **NOT IMPLEMENTED** | — | — | missing file |
| 7 | Other | ES default 15%; landing “15%”; ghiduri 4% VERIFIED | Copy / other products | — | — | **UI / docs** | — | — | Do not use |

Future implementation must not use row 3 as row 4.

---

# 14. D11.12 — Entitlement options (unranked)

Do **not** rank. Do **not** choose.

### MODEL A — HH completely separate from Marketplace access

| | |
|---|---|
| Reuse | Current `create_request` ungated; HH stays on HH/DT routes |
| Evidence | **Matches Marketplace spine today** |
| New logic | None for access |
| Conflicts | None with D1/D2/D6/D8 |
| Unresolved | Why sell “marketplace lead commission” on HH cards |

### MODEL B — HH subscription grants Marketplace entitlement

| | |
|---|---|
| Reuse | `require_entitlement` + `hh_subscriptions` |
| Evidence | Gate exists but is **not** on Marketplace routes |
| New logic | Wire Depends on create/select (and decide FREE users) |
| Conflicts | Would block current open Marketplace; D9 “3 free” undefined |
| Unresolved | Which feature flag; specialist side |

### MODEL C — HH benefits, Marketplace stays independently accessible

| | |
|---|---|
| Reuse | Publish bridge + attribution + HH module gates |
| Evidence | **Closest to implemented K** |
| New logic | Optional product benefits only |
| Conflicts | None if 15/10/5 stay metadata (D8) |
| Unresolved | What “benefit” means besides capture |

### MODEL D — HH plan changes Marketplace economics

| | |
|---|---|
| Reuse | `lead_commission_pct` or plan slug |
| Evidence | Capture exists; **no** payout/credit change |
| New logic | Would have to alter D8, credits, or apply fee by plan |
| Conflicts | **D8** if % becomes job commission; **D2** if credits change |
| Unresolved | Forbidden unless founder explicitly overrides D8 |

### MODEL E — Hybrid / existing documented

| | |
|---|---|
| Reuse | C + optional later B for some actions (e.g. only HH-publish) |
| Evidence | Publish already HH-flavored; ordinary request is A |
| New logic | Keep two request origins |
| Conflicts | Low if D8 untouched |
| Unresolved | Whether HH-origin requests get different economics |

---

# 15. D11.13 — Automation / AI / analytics consumers

Existing consumers of HH↔Marketplace **data** (not builders):

| Surface | What it consumes |
|---|---|
| `GET /api/house-health/marketplace-stats` | Counts `house_health_source`, avg captured % |
| `hh_audit_log` | publish / capture / subscription_activated |
| `financial_cockpit.py` | `hh_plans.price_eur`, active `hh_subscriptions` |
| `analytics_growth.py` | Subscription **counts** in date windows |
| `propbenefits/*` | Active sub for eligibility / health |
| `launch_sentinel.py` | Active sub counts |
| `renewal_reminders.py` | `expires_at` |
| `RecommendationsSection.jsx` | Publish CTA + % copy |
| `manual_tester.py` | Expects HH-source badge on published request |
| House Health dashboard / eligibility | Twin + sub + entitlement — **HH product**, not job spine |
| Matching / Twin Orchestrator / Marketplace Intelligence | **No `house_health_source` read found** |
| Notifications | Ordinary request/offer notifies after publish (new `request` + later offers) |

---

# 16. D11.14 — Security / entitlement invariants (future)

1. Frontend cannot self-select a paid plan as charged amount (already: slug only).  
2. Frontend cannot self-grant Marketplace entitlement.  
3. Frontend cannot modify commission percentage authoritatively.  
4. Subscription status is server-authoritative (`hh_subscriptions`).  
5. Expired subscription cannot silently retain paid HH/DT entitlement (`expires_at` check exists).  
6. HH percentage cannot silently become Marketplace job commission (D8).  
7. Lead Credits cannot silently become subscription entitlement.  
8. Marketplace access cannot depend only on UI visibility (today it does not depend on HH at all).  
9. Displayed price is not payment state (`upgradeNudge` 9 ≠ charged price if DB differs).  
10. Trial state must be server-authoritative (**today UI trial ≠ server trial**).  
11. Commercial state must be auditable (`hh_audit_log`, `payment_transactions`, request snapshot).

---

# 17. D11.15 — Existing SSOT candidates (no new SSOT)

| Concern | Existing candidate | Notes |
|---|---|---|
| **A. HH plan** | `hh_plans` slug / id | Admin-managed |
| **B. HH price** | `hh_plans.price_eur` | Checkout reads this |
| **C. HH trial** | `hh_plans.trial_days` | **Display only** today |
| **D. HH entitlement** | `hh_subscriptions` + `entitlements.py` | Already the feature translator |
| **E. HH lead attribution %** | `hh_plans.lead_commission_pct` snapshotted on `house_health_source` | Capture uses snapshot, not live plan |
| **F. Marketplace access** | JWT + role + property owner | **Not** HH |
| **G. Marketplace commission** | Hardcoded `0.95` at `/confirm` (D8) | `platform_commission_pct` unused |

---

# 18. D11.16 — Legacy reconciliation

| Mechanism | Classification |
|---|---|
| `hh_plans` | **KEEP** as HH product catalog |
| `hh_subscriptions` | **KEEP** as HH/DT access |
| Recommendation publish → request | **KEEP** as the only HH→Marketplace **data** bridge |
| `lead_commission_pct` snapshot / capture | **KEEP** as attribution metadata; **do not REDIRECT** into D8 |
| `accept_offer` capture block | **KEEP** (D6 moment); money settlement **UNKNOWN** / D11 founder if ever paid |
| Marketplace offers / select | **KEEP** independent of HH |
| `/accept` | **DEPRECATE** as public Marketplace writer (D13); **not** an HH event |
| Lead Credits | **KEEP** separate (D2) |
| Wallet apply fee | **KEEP** separate |
| Platform `* 0.95` | **KEEP** as D8 |
| `fee_configs` | **KEEP** off HH |
| Admin `platform_commission_pct` | Dead for job payout (D8) |
| Pricing UI | **KEEP** as reader of `hh_plans` |
| HH checkout | **KEEP** as subscription purchase |
| Seed `features[]` vs entitlements map | **UNKNOWN** / reconcile later (copy ≠ flags) |
| `trial_days` UI | **DEPRECATE as a promise** until a writer exists — or implement later (not now) |
| `upgradeNudge` hardcoded 9 / Pro-for-DT | **INTERNAL-ONLY** copy; not SSOT |
| App.js specialist “15%” | **HISTORICAL / UI** — not HH |

---

# 19. D11.17 — Target relationship map (specify only)

Two flows. **Do not merge.**

```
CLIENT
  → PROPERTY / TRUST          (owner_id; not “verified client”)
  → HOUSE HEALTH (if applicable)   HH/DT entitlement; optional
  → MARKETPLACE REQUEST       create_request  OR  HH publish
  → SPECIALIST ELIGIBILITY    open list / match / flag
  → OFFERS                    submit_offer (D2)
  → CLIENT SELECTION          accept_offer (D6)
  → COMMERCIAL RELATIONSHIP   assigned + specialist_id + selected_offer_id
  → PAYMENT                   D7
  → ESCROW                    internal marker (D7)
  → EXECUTION                 /start
  → CONFIRMATION              /confirm
  → 5% MARKETPLACE JOB COMMISSION   D8
  → PAYOUT                    internal wallet
```

```
HOUSE HEALTH
  → PLAN lead_commission_pct
  → PUBLISH snapshot on house_health_source
  → LEAD ATTRIBUTION
  → 15 / 10 / 5 METADATA
  → CAPTURE at D6 on apply fee
  → (no settlement today)
```

---

# 20. Founder decisions still required

1. **Entitlement model A / C / B / D / E** (unranked).  
2. **Premium price 79 vs 249** (and whether target DB already differs).  
3. Whether `trial_days` should ever be granted.  
4. Whether captured HH % is ever invoiced (must not become D8).  
5. D9 “3 free” — still nonexistent.  
6. Align seed `features[]` / nudges with `TIER_FEATURES` (DT = Premium in code).

This document does **not** make a commercial recommendation.

---

# 21. D11 STATUS

**READY FOR FOUNDER APPROVAL**

| Question | Answer from evidence |
|---|---|
| What HH currently does | Client subscription; HH/DT feature gates; optional rec→request; 15/10/5 snapshot + capture |
| What it does NOT do | Gate Marketplace; change credits, apply fee, ranking, matching, verification, D8 5% |
| Gates Marketplace? | **No** |
| Changes Marketplace job commission? | **No** |
| What 15/10/5 means | Attribution metadata on **apply fee**, not job payout |
| Undecided | Future entitlement model; 79 vs 249; trial grant; whether capture is ever money; D9 |

No implementation authorized.

---

# 22. Explicit statement

**No implementation performed.**

No application code, schema, database, pricing, flags, UI, tests, commit, or deploy was changed.

**STOP.**
