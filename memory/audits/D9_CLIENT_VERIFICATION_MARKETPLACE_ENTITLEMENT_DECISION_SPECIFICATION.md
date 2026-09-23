# D9 — CLIENT VERIFICATION + MARKETPLACE EXPERIENCE + HOUSE HEALTH ENTITLEMENT

**Decision:** D9 — How client identity, property ownership, trust, first Marketplace experiences, and House Health plans (79 / 249) relate  
**Mode:** READ-ONLY. No implementation, schema, DB, prices, plans, trials, entitlements, flags, Model B, credits, commission, Stripe, `/accept`, escrow, UI, commit, or deploy.  
**Given:** D1 = Model B · D2 = Lead Credits on `submit_offer` · D6 = relationship at `accept_offer` · D8 = job 5% ≠ HH · D11 = HH does **not** gate Marketplace  
**Date:** 2026-09-23

Do not confuse:

House Health trial ≠ HH subscription ≠ Lead Credits ≠ client wallet ≠ `users.tokens` ≠ property verification ≠ specialist verification ≠ “3 free Marketplace experiences.”

**No implementation performed.**

---

# 1. Executive snapshot

| Question | Evidence |
|---|---|
| Marketplace client gate today | Authenticated **client** + **owned** `property_id` on create. Nothing else. |
| Composed `CLIENT VERIFIED` | **No such state.** Signals exist; they are not composed. |
| “3 free experiences” | **E — NOT FOUND** |
| HH gates Marketplace? | **Still no** (D11 reconfirmed) |
| Plan ≈ 79 EUR | Seed **`premium` = 79**. Checkout charges `hh_plans.price_eur`. |
| Plan ≈ 249 EUR | **No runtime slug / hardcoded UI price.** PRD/founder intent only. |
| Trials | **UI PROMISE ≠ RUNTIME BEHAVIOR** |
| 79 vs 249 | **OPEN — FOUNDER PRICING DECISION** |

**STATUS:** DECISION SPECIFICATION — **READY FOR FOUNDER APPROVAL**

---

# PART 1 — Client identity

| Mechanism | DOCUMENTED | IMPLEMENTED | EVIDENCED | CONNECTED | AUTOMATED | AUTONOMOUS | UNKNOWN |
|---|---|---|---|---|---|---|---|
| Email/password register | Yes | `auth.register` | Inserts `users` | Login + cookies | `test_phase_gdpr_auth_extension` | No | — |
| Login + JWT cookies | Yes | `auth.login` | Cookies | All `Depends` | Many tests | No | — |
| Google OAuth | Yes | `auth` Google + Emergent session | Upsert by email | Sets `google_auth` | OAuth health log | No | Whether Google email is treated as verified on **new** OAuth rows (`email_verified` **not set** on insert) |
| Email verification | Yes | Token + set `email_verified=True` | Register starts `False` | **Not** a Marketplace/HH checkout gate. Experience tiers treat `email_verified or google_auth` | GDPR tests | No | Login allowed unverified |
| Phone verification | Field + admin filter | `phone_verified=False` at register | Consent backfill: **SMS not implemented** | Admin list only | Filter tests | No | **No writer** of true via SMS |
| Role `client` / `specialist` | Yes | Register `data.role` | Enforced `require_role` | Marketplace + HH | Dual-role tests | No | — |
| Dual-role | Yes | `become-specialist` / `become-client` / `switch-view` | Same user, `dual_role_enabled` | `deps` + request list | `test_auth_dual_role_healing` | Self-heal invalid flag | — |
| Ownership | Via properties | `owner_id = user.id` at create | GET IDOR fix exists | `create_request` | Ownership tests | No | Asserted, not proven |
| Profile completeness | Partial | Zone optional for client; phone required for specialist | — | Specialist register | — | No | No client “complete profile” gate |
| Identity fields | email, name, phone, picture | Yes | — | `/me` | — | No | — |
| Account status `banned` | Yes | Login rejects banned | `auth.login` | Auth only | — | No | Not re-checked on every Marketplace write beyond JWT user load |
| Duplicate email | Yes | Register 400 if email exists | Unique lookup | OAuth links existing email | Register tests | No | No unique index proven in this pass |
| Fraud / disposable email / device | — | **NOT FOUND** as Marketplace control | — | — | — | No | **UNKNOWN** beyond email uniqueness + banned |

---

# PART 2 — Property registration / ownership

FILE: `backend/routes/properties.py` `create_property`  
ROUTE: `POST /api/properties`  
AUTH: `require_role("client")`  
DB: `properties.owner_id = user.id`  
**No** `require_entitlement(F_PROPERTY_CREATE)` even though that flag exists on FREE.

| Question | Answer |
|---|---|
| 1. Can any authenticated client create a property? | **Yes.** Unlimited. No email/phone/HH check. |
| 2. Can a user claim another’s property? | **Not by ID.** GET/PUT/DELETE require `owner_id`. A user **can** create a **new** document with the same address as someone else — **no unique address/building key**. |
| 3. Ownership verified or asserted? | **Asserted.** `owner_id` is the creator. Documents / passport / DNA can add **evidence**, not legal title. |
| 4. Property registration sufficient for Marketplace? | **Yes today.** `create_request` only needs an owned property. |
| 5. Stronger property verification? | **Partial, other products:** document vault completeness; passport `_trust_score` (verified docs); twin `pending_validation` / `approved`; PI asset `source` (`owner_declared` vs `official_document`). **None** required for Marketplace. |
| 6. HartaBlocuri? | **External / imported building reference** (`hartablocuri.py`, `buildings.context.external_sources.hartablocuri`). Resident count via `properties.building_id`. **Not** ownership proof for a Marketplace client. |

Do **not** create a verification engine. Reuse: `owner_id` + optional document/passport/twin signals later.

---

# PART 3 — Client trust / verification signals

No composed `CLIENT VERIFIED` object.

| CURRENT SIGNAL | SOURCE | RUNTIME ENFORCED? | CONSUMERS | POSSIBLE ROLE | KEEP / CONNECT / EXTEND |
|---|---|---|---|---|---|
| JWT identity | `auth` | Yes on APIs | All routes | Identity | **KEEP** |
| `role=client` | `users.role` | `require_role` | Marketplace / HH | Actor type | **KEEP** |
| `email_verified` | `auth` verify | **No** on Marketplace/HH pay | Experience tiers, admin, insights | Contact trust | **CONNECT** later if founder wants |
| `google_auth` | OAuth | Treated as email-verified **only** in `experience_tiers.py` | Tiers | Weak contact trust | **CONNECT** carefully (OAuth insert omits `email_verified`) |
| `phone_verified` | Field default false | **No** (SMS missing) | Admin filter | Contact trust | **EXTEND** only if SMS exists |
| `users.verified` | Specialist KYC / review auto-upgrade | Copied to request `specialist_verified` | Matching/display | **Specialist**, not client | **KEEP** off client D9 |
| Property `owner_id` | Create property | Yes for request/property APIs | Marketplace | Property context | **KEEP** |
| Passport trust | `property_passport._trust_score` | Display / public card | Passport UI | Property evidence | **KEEP** ≠ client KYC |
| Document verified status | `property_documents` | Vault completeness | Passport, storage | Property evidence | **KEEP** |
| Twin approved | `twins.status` | HH eligibility mentions twin; DT edit gated by plan | HH / DT | Property digitalization | **KEEP** |
| PI asset source | `owner_declared` / `official_document` | On PI write | PI | Evidence grade | **KEEP**; **not** Marketplace gate |
| HH subscription | `hh_subscriptions` | HH/DT features | Entitlements | **Paid access**, not identity | **KEEP** separate |
| KYC | `kyc.py` | Specialist | Admin | Specialist identity | **KEEP** off client |
| Banned | `users.banned` | Login | Auth | Account block | **KEEP** |

**Enough components to compose CLIENT VERIFIED later?**  
**Yes, as a boolean derived from existing fields** (e.g. authenticated + `email_verified` + ≥1 `owner_id` property + optional doc/passport threshold).  
**No engine exists today.** Do not invent one in this spec.

---

# PART 4 — Marketplace client gate

UI visibility ≠ authorization.

| Action | Route / function | Required today | Not required |
|---|---|---|---|
| Create request | `POST /api/requests` `create_request` | Client role + `properties` `{_id, owner_id}` | email/phone verified, HH, quota, `CLIENT VERIFIED` |
| List / get request | `GET /api/requests` `GET .../{id}` | Auth + owner/specialist/admin view rules | HH |
| View offers | `GET /api/requests/{id}/offers` `list_offers` | Owner **or** admin **or** specialist with an offer | HH, verified |
| Accept offer | `POST .../offers/{id}/accept` `accept_offer` | Client + `client_id` + request `open` | Payment, HH, verified |
| `/accept` (legacy) | `POST /api/requests/{id}/accept` | **Specialist** | Client verification |
| Checkout job | `POST /api/payments/checkout-session` | Client owner; status `open\|assigned` | HH, verified |
| Marker escrow | `POST /api/requests/{id}/escrow` | Client owner | Payment, HH |
| Confirm | `POST .../confirm` | Client owner + `completed` | HH, verified, paid |
| Rebook | `POST /api/trusted-specialists/{id}/rebook` | Client + prior `completed\|confirmed` + owned property | HH |

**D11 reconfirmed:** no `hh_subscriptions` read on these Marketplace writes except HH **capture** inside `accept_offer` when `house_health_source` exists.

---

# PART 5 — “3 free Marketplace experiences”

Searched: free projects/requests, first 3, welcome/onboarding allowance, entitlement usage, request/project counters, campaign/referral allowances.

Nearby **non-matches:** storage quota (MB); DT FREE twin **container** tests; Lead Credits 135/45; FC quest “3 cereri”; experience “3 jobs”; HH `trial_days`; concierge LLM quota.

**Classification: E — NOT FOUND**

No A/B/C/D runtime quota for client Marketplace experiences.

---

# PART 6 — What “3 free” could mean (unranked)

Do **not** choose.

| | A. 3 free REQUESTS | B. 3 free CLIENT EXPERIENCES | C. 3 free COMMERCIAL RELATIONSHIPS | D. 3 free PROJECTS | E. 3 free CATEGORIES / OPPORTUNITIES | F. Other existing |
|---|---|---|---|---|---|---|
| Reuse | Count `requests` by `client_id` | Needs a defined “experience” event (create vs D6 vs confirm) | Count `assigned` / `selected_offer_id` (D6) | `digital_twin_projects` or `projects` — **wrong product** if used blindly | Distinct `category` on requests | Tokens, vouchers, HH trial — **wrong** |
| Billing | Waive client pay for first 3? | Same ambiguity | After D6; pay still D7 | DT ingest ≠ job | Narrow | Do not reuse credits |
| Entitlement | New counter on user/request | Same | Same | DT already has FREE container | Same | — |
| Abuse | Spam `open` requests | Depends on event | Harder (needs specialist + select) | Fake DT projects | Category farming | — |
| vs HH | Must stay separate | Same | Same | Easy to confuse with DT FREE | Same | HH trial ≠ this |
| vs property verification | Fake properties × 3 | Same | Same | Same | Same | — |
| vs D8 commission | Open if pay waived | Open | Open | Unrelated | Open | — |
| vs payment | May still pay job | Founder | Founder | Unrelated | Founder | — |
| vs trust | Weak if A | Stronger if B/C after D6 | Strongest | Weak | Medium | — |

---

# PART 7 — House Health plan audit (mandatory)

Runtime catalog (seed if slug missing):

| Slug | Seed `price_eur` | `trial_days` | `lead_commission_pct` | Entitlement tier |
|---|---|---|---|---|
| `basic` | 9 | 7 | 15 | `CLIENT_BASIC` |
| `pro` | 29 | 14 | 10 | `CLIENT_PRO` |
| `premium` | **79** | 14 | 5 | `CLIENT_PREMIUM` |

Founder commercial framing in this brief: **Plan ≈ 79** and **Plan ≈ 249**.  
Runtime has **three** slugs, not two. **249 is not a fourth slug.**

Checkout: `POST /api/house-health/checkout-session` — amount from **DB** `price_eur`. No DEMO bypass (503 if no key). One-shot days via `_billing_days` (30/365/90), not Stripe Subscription.

Public UI: `PricingPage.jsx` reads API — **no hardcoded 249**.  
PRD: founder Premium 249 expected **per environment in `hh_plans`**.  
Target DB value: **not read in this file-only task** → **UNKNOWN**.

---

# PART 8 — Plan ≈ 79 EUR

Interpreted as **current seed `premium`**. If an environment overwrote `premium.price_eur` to 249, checkout would charge 249 for the **same slug**.

| Step | FILE | FUNCTION | ROUTE | DB FIELD | CALLER | STATUS |
|---|---|---|---|---|---|---|
| Price | `house_health_billing.py` / `house_health_plans.py` | seed / admin PATCH | Admin plans | `hh_plans.price_eur` | Admin, seeder | Seed **79**; env may differ |
| Plan record | same | `hh_plans` `{slug:premium}` | `GET /api/house-health/plans` | slug, features[], trial_days, lead_commission_pct | PricingPage, UpgradePage | **IMPLEMENTED** |
| Checkout | `create_checkout_session` | POST `/api/house-health/checkout-session` | `price_eur` → Stripe amount | Pricing CTA | **IMPLEMENTED** (needs real Stripe key) |
| Payment | `_activate_subscription_if_paid` | poll + `payments` webhook | `payment_transactions` | Frontend poll | **IMPLEMENTED** |
| Subscription | same | upsert | `hh_subscriptions` plan/status/expires_at | Activation | **IMPLEMENTED** `active` |
| Trial | — | — | `trial_days` unread | UI only | **NOT GRANTED** |
| Entitlement | `entitlements.get_user_entitlements` | `GET /api/me/entitlements` | plan slug → `CLIENT_PREMIUM` | HH/DT gates | **IMPLEMENTED** mapping |
| Feature access | `_resolve_features` | — | inherits FREE+BASIC+PRO+PREMIUM flags | See Part 10 | **PARTIAL** (flags vs route gates) |
| Expiration | `_fetch_active_subscription` | — | `expires_at` | Entitlements | **IMPLEMENTED** |
| Renewal | pay again extends `expires_at` | checkout | — | User | **PARTIAL** (not auto-Stripe sub) |
| Cancel | `cancel_my_subscription` | POST `/api/me/subscription/cancel` | status `cancelled` | Settings | **IMPLEMENTED** until expiry |
| UI | `PricingPage.jsx` | `/pricing` | displays `price_eur` | Public | **CONNECTED** to DB |

**What 79 Premium actually unlocks today (if slug=`premium` and sub active):**

| Promise (seed `features[]`) | Entitlement flag | Route enforced? |
|---|---|---|
| Digital Twins unlimited | `F_DIGITAL_TWIN_ADVANCED` (Premium exclusive in current `TIER_FEATURES`) | **PARTIAL** — `_ensure_dt_access` on advanced DT |
| Storage unlimited | storage tier via active HH sub | **PARTIAL** — MB quotas, not “unlimited” |
| Unlimited evaluations | — | **NOT FOUND** as a counter |
| Twin Orchestrator AI | — | **NOT FOUND** as this plan gate |
| Marketplace lead commission 5% | `lead_commission_pct=5` | **Metadata only** (D11) |
| Phone CSM | — | **NOT FOUND** |
| House Health basic/advanced | inherited flags | **BASIC enforced** (402); **ADVANCED flag unused on routes** |
| Property Intelligence | `F_PROPERTY_INTELLIGENCE` | **CONFIGURED BUT UNUSED** — PI API is ownership-only |
| Portfolio management | `F_PORTFOLIO_MANAGEMENT` | **CONFIGURED BUT UNUSED** |

PROMISED (seed/UI) ≠ fully IMPLEMENTED ≠ fully CONNECTED ≠ fully RUNTIME ENFORCED.

---

# PART 9 — Plan ≈ 249 EUR

| Question | Evidence |
|---|---|
| Exists in runtime as amount? | **Only if** some env `hh_plans.premium.price_eur=249` (UNKNOWN here) |
| Exists as its own slug? | **No** in seed |
| Exists in PricingPage source? | **No hardcoded 249** |
| Same plan as 79? | **Same slug `premium` if founder only changes price** |
| Multiple Premium definitions? | Seed 79 + PRD 249 + badge “Property Intelligence” on Premium card |
| Checkout uses 79 or 249? | **Whatever is in DB `price_eur`** |
| Features | Same `CLIENT_PREMIUM` set as Part 8 |
| Status | **Undefined as a distinct SKU**; seed Premium is **79** |

**OPEN — FOUNDER PRICING DECISION**

Do not choose 79 vs 249. Do not assume screenshots are runtime.

---

# PART 10 — Entitlement vs product surfaces

`entitlements.py` is the **existing** translator. Specialist catalog is **experience_tier**, unused as Marketplace `Depends`.

| Feature | Classification |
|---|---|
| House Health dashboard / docs upload | **RUNTIME ENFORCED** `F_HOUSE_HEALTH_BASIC` (402 / locked card) |
| House Health “advanced” | Flag on PRO+; **CONFIGURED BUT UNUSED** as route Depends |
| HH score / evaluations | Behind HH module + twin eligibility — **PARTIAL** |
| PVI | `value_loop` on job confirm / DNA — **NOT** plan-gated |
| Digital Twin advanced edit | **RUNTIME ENFORCED** `F_DIGITAL_TWIN_ADVANCED` (+ legacy `digital_twin_pro`) |
| Smart Home | **NOT FOUND** as entitlement |
| Property monitoring | HH / PI fragments — **PARTIAL** / not plan-named |
| Documents / vault | Storage quota; HH upload uses HH gate — **PARTIAL** |
| Property Passport | Ownership + public page — **NOT** plan-gated |
| Maintenance calendar | **NOT** plan-gated |
| HH recommendations + publish | Twin owner; publish **not** `require_entitlement` — **PARTIAL** |
| Marketplace | **NOT FOUND** as entitlement (D11) |
| Trusted specialists / rebook | Prior jobs — **NOT** HH |
| Priority services | Seed copy — **UI ONLY** |
| Property verification | Passport/docs — **NOT** subscription |
| Support / CSM | **NOT FOUND** |
| Analytics (PI maturity/assets) | Authenticated owner — **NOT** `F_PROPERTY_INTELLIGENCE` |
| Portfolio / investor | Flag unused — **CONFIGURED BUT UNUSED** |

Do **not** create another entitlement system.

---

# PART 11 — Trials

| | UI / seed | Runtime |
|---|---|---|
| Basic 7 / Pro 14 / Premium 14 | Displayed if `trial_days > 0` | **`trial_days` never read by billing** |
| `status=trial` | Entitlement **would** honor it | Activation writes **`active`** after **paid** |
| Start / expire trial | — | **No grant writer** |
| Payment success | — | +30 days monthly (etc.) |
| Renewal / cancel / grace | Cancel + `expires_at`; grace **status supported in query**, not written by checkout | **PARTIAL** |

**UI PROMISE ≠ RUNTIME BEHAVIOR**  
Commercial/product defect for later repair. **Do not repair now.**

---

# PART 12 — House Health ↔ Marketplace (D11 hold)

Re-traced this session: `create_request`, `submit_offer`, `accept_offer` (except capture), checkout, escrow, confirm — **no plan gate**.

| Marketplace lever | Affected by HH plan? |
|---|---|
| Request create / offers / select | **No** |
| Ranking / Lead Credits / apply fee | **No** |
| Job commission / escrow / payout | **No** (D8) |
| Trust / property verification | **No** |
| HH-origin request | Publish + 15/10/5 metadata only |

Do not introduce a new dependency here.

---

# PART 13 — Verification vs subscription vs Marketplace entitlement

| Concept | Current code |
|---|---|
| CLIENT VERIFICATION | **No object** |
| HH SUBSCRIPTION | `hh_subscriptions` + entitlements |
| MARKETPLACE ENTITLEMENT | **Does not exist** (open access given property) |

Incorrect collapses in **copy**, not in Marketplace runtime:

- Seed “comision marketplace lead” on HH cards ≠ D8  
- `upgradeNudge` DT → Pro vs code DT → Premium  
- Seed Basic “1 Digital Twin inclus” vs `TIER_FEATURES` DT on Premium  
- Experience tiers treat Google as email-verified; Marketplace ignores both  

Preserve: identity ≠ subscription ≠ verification ≠ payment ≠ D6 relationship.

---

# PART 14 — Abuse / fraud (for a future 3-free)

| Vector | EXISTING CONTROL | MISSING | UNKNOWN |
|---|---|---|---|
| Duplicate email accounts | Register unique email; OAuth merges same email | Unique index not proven here | — |
| Disposable email | — | **MISSING** | — |
| Fake properties | Owner-scoped APIs | **MISSING** uniqueness / proof | — |
| Claim others’ property by id | Owner match | Claim-by-address | — |
| Repeat free usage | No quota | **Entire quota missing** | — |
| Multi-account same property | — | **MISSING** | — |
| Google OAuth dup | Same email links | Other emails | — |
| Repeat requests | No cap | **MISSING** | — |
| Self-dealing | `submit_offer` blocks `client_id == specialist` | Dual-role other paths | Partial |
| Dual-role | Self-heal; view switch | Using client view + specialist accept on own lead | Tests exist |

Do not create controls now.

---

# PART 15 — Future invariants (do not implement)

- Client cannot self-grant verification, subscription, or free quota.  
- Frontend cannot alter plan, trial, or Marketplace quota.  
- Ownership cannot rest only on a client-invented identifier without server bind to `users.id`.  
- Expired subscription cannot keep paid HH/DT entitlement (`expires_at` already checked).  
- Verification and quota consumption must be server-authoritative.  
- Commercial state must be auditable.  
- identity ≠ subscription ≠ verification ≠ Marketplace entitlement ≠ Lead Credits ≠ client quota ≠ HH trial.  
- payment ≠ subscription entitlement ≠ D6 relationship.

---

# PART 16 — Existing SSOT candidates

| | Candidate | Conflict |
|---|---|---|
| **A. Identity** | `users._id` + email | OAuth vs password `email_verified` |
| **B. Ownership** | `properties.owner_id` | Asserted vs evidenced docs |
| **C. Client verification** | **None composed** | Many unused signals |
| **D. HH plan** | `hh_plans` slug | Seed features[] vs `TIER_FEATURES` |
| **E. HH price** | `hh_plans.price_eur` | Seed 79 vs founder 249; nudge hardcode 9 |
| **F. Subscription** | `hh_subscriptions` | — |
| **G. Trial** | `trial_days` display vs no writer | **Conflict** |
| **H. Entitlement** | `entitlements.py` | Specialist FC catalog unused on routes; PI/portfolio flags unused |
| **I. Marketplace quota** | **None** | — |
| **J. Marketplace access** | JWT + client + owned property | — |
| **K. HH lead attribution** | `house_health_source` snapshot | ≠ D8 |

Do **not** create a new SSOT.

---

# PART 17 — Legacy reconciliation

| Mechanism | Classification |
|---|---|
| JWT / role / banned | **KEEP** |
| `email_verified` / `phone_verified` | **CONNECT** if D9 verification uses them; phone **DECISION REQUIRED** (no SMS) |
| `users.verified` / KYC | **KEEP** as specialist |
| `properties.owner_id` | **KEEP** as ownership assertion |
| Passport / vault / twin status | **KEEP** as property evidence; **CONNECT** later if composed trust |
| HartaBlocuri | **KEEP** as building reference — not title |
| HH / `hh_plans` / billing / entitlements | **KEEP** as subscription product |
| Feature configurator specialist catalog | **KEEP** off client Marketplace |
| Vouchers / quests / tokens / wallet | **KEEP** ≠ 3-free |
| Marketplace requests / offers / D6 | **KEEP** |
| Lead Credits / `/accept` | **KEEP** / **DEPRECATE** public A (D13) |
| Seed trial_days UI | **DECISION REQUIRED** (promise vs grant) |
| Premium 79 vs 249 | **DECISION REQUIRED** |
| 3-free | **DECISION REQUIRED** (definition) then EXTEND a **counter**, not a new OS |
| `F_PROPERTY_CREATE` unused on POST | **CONNECT** or ignore |
| PI / portfolio flags unused | **CONNECT** to match 249/PI promise |

---

# PART 18 — 79 / 249 commercial product repair map

No new engines. Repair/connect **existing** pieces later.

| PLAN | PROMISED VALUE | CURRENT RUNTIME | GAP | EXISTING SYSTEM | REPAIR LATER | PRIORITY |
|---|---|---|---|---|---|---|
| Premium seed **79** | Investor / PI / unlimited DT / min lead % / CSM | Checkout 79 if DB seed; `CLIENT_PREMIUM` flags; DT gate; HH basic 402; PI **ungated**; 15/10/5 metadata; no trial; no CSM | Promise vs flags vs gates | `hh_plans` + entitlements + DT/HH routes | Align `features[]` with `TIER_FEATURES`; wire unused flags **or** stop promising them | High if sold |
| **249** PI / Premium | Founder/PRD / screenshots | **No distinct SKU**; UI follows DB | Price + product identity | Same `premium` row **or** new slug later | Founder sets `price_eur` and benefit list | High if sold |
| Basic 9 / Pro 29 | HH tiers + trial + DT counts in copy | 9/29 checkout; trials not granted; DT copy vs Premium-only flag | Copy vs gate | same | Align copy | Medium |
| Trials 7/14/14 | Free days | Paid + 30 days | **UI PROMISE ≠ RUNTIME** | `trial_days` + `status=trial` already in entitlement **reader** | Writer on start — later | High if advertised |
| Marketplace benefits on HH cards | Reduced lead commission | Capture metadata only | Customer may think job 5% changes | `house_health_source` | Do not wire into D8 | High (legal/copy) |
| 3-free | Discussed product | **Missing** | Entire feature | `requests` counter **if** founder picks A/B/C | After definition | Founder |
| Marketplace gated on HH | Not current D11 | Ungated | Only if Model B chosen | `require_entitlement` | Do not add unless founder | Founder |

---

# PART 19 — Target lifecycles (do not merge)

```
VISITOR → ACCOUNT → IDENTITY → PROPERTY REGISTERED
  → PROPERTY / CLIENT TRUST        (signals exist; not composed)
  → MARKETPLACE ELIGIBLE           (today = client + owned property)
  → FREE MARKETPLACE EXPERIENCES   (NOT FOUND)
  → REQUEST → OFFERS → SELECTION (D6)
  → PAYMENT → EXECUTION → CONFIRM (D8)
  → PROPERTY HISTORY (reviews, PVI, vault)
  → HOUSE HEALTH / LONG-TERM SUPPORT   (optional, separate purchase)
```

```
HOUSE HEALTH SUBSCRIPTION
  → PLAN (hh_plans)
  → TRIAL (displayed, not granted)
  → PAYMENT (Stripe one-shot)
  → ENTITLEMENT (tier + features)
  → FEATURE ACCESS (HH basic + DT advanced enforced; much else unused)
  → RENEWAL / EXPIRATION / CANCEL
```

Code proves a connection **only** at: HH publish → request + attribution. Not at access or D8.

---

# PART 20 — “One customer → one identity → one property context → multiple services”

| Layer | Already supported? | Smallest gap |
|---|---|---|
| One identity | `users._id` | OAuth `email_verified` consistency |
| One property context | `properties` + `property_id` on requests | Ownership is asserted; optional evidence unused for eligibility |
| Multiple services | Marketplace, HH, DT, PI, passport, vault, calendar, VE | Entitlement flags not all wired; copy over-promises |
| Multiple projects / interventions | Many `requests` per property; design `phases`; no Marketplace parent project (D7) | 3-free + stages are definition, not a new OS |
| Long-term history | Confirm value-loop, reviews, documents, passport | Not gated on “verified client” |

**Do not create a Property Operating System.**  
Smallest gaps: compose verification from existing signals **if** founder wants a gate; add a **server counter** if founder defines 3-free; align HH price/copy/gates on existing `hh_plans` + `entitlements.py`.

---

# PART 21 — D9 decision package

### D9 — CURRENT EVIDENCE

A client can register (unverified), create unlimited self-asserted properties, and run the full Marketplace job spine. HH is a separate paid product that unlocks HH/DT (partially). 15/10/5 is attribution metadata. Job 5% is D8.

### D9 — CLIENT VERIFICATION

Reusable: JWT, role, `email_verified`, `google_auth`, `owner_id`, passport/docs/twin/PI source.  
Not reusable as client verify: specialist `verified`/KYC, HH subscription, Lead Credits.  
**No composed CLIENT VERIFIED.**

### D9 — 3 FREE MARKETPLACE EXPERIENCES

**E — NOT FOUND.** Interpretations A–F unranked. Must not reuse HH trial, credits, tokens, or DT FREE projects.

### D9 — HOUSE HEALTH 79 EUR

Seed **Premium = 79**. Checkout/UI follow `hh_plans`. Maps to `CLIENT_PREMIUM`. DT advanced + HH basic enforced. PI/portfolio/CSM/unlimited evals/true unlimited storage **not** fully enforced. Trial not granted. Lead 5% is HH metadata, not D8.

### D9 — HOUSE HEALTH 249 EUR

**No distinct runtime plan.** Intended price **OPEN — FOUNDER PRICING DECISION.** Same Premium feature set if only `price_eur` changes.

### D9 — TRIALS

**UI PROMISE ≠ RUNTIME BEHAVIOR.** Billing writes paid `active` + billing-period days.

### D9 — ENTITLEMENTS

Enforced: HH basic, DT advanced (and expiry).  
Unused flags: HH advanced, PI, portfolio, `F_PROPERTY_CREATE` on create.  
Marketplace: not an entitlement.

### D9 — REPAIR MAP

See Part 18. Reuse `hh_plans`, `hh_subscriptions`, `entitlements.py`, DT/HH gates, `requests` counts. No new OS.

### D9 — FOUNDER DECISIONS REQUIRED

1. Exact definition of “3 free” (A–F).  
2. Exact Premium price: **79 vs 249** (and whether they are one slug or two products).  
3. Intended benefits if UI/seed/entitlements disagree.  
4. Whether HH should **ever** gate Marketplace (D11 models A–E).  
5. Whether CLIENT VERIFIED is required before Marketplace (compose existing signals or keep asserted ownership).  
6. Whether advertised trials must be granted.

Do **not** decide these here.

### D9 — ARCHITECTURAL INVARIANTS

- identity ≠ subscription  
- subscription ≠ verification  
- verification ≠ Marketplace entitlement  
- Marketplace entitlement ≠ Lead Credits  
- Lead Credits ≠ client quota  
- client quota ≠ House Health trial  
- payment ≠ subscription entitlement  
- payment ≠ commercial relationship (D6)  
- frontend cannot grant commercial state  
- reuse existing systems before proposing new ones  
- D8 5% ≠ HH 15/10/5  
- ownership assertion ≠ legal title  

### D9 — IMPLEMENTATION BLOCKERS

- Founder answers on 3-free definition, 79 vs 249, and whether Marketplace stays ungated.  
- If trials or 249 are **currently advertised as live**, that is a **commercial defect** (repair later), not a missing engine.  
- Target `hh_plans.premium.price_eur` still **UNKNOWN** without a DB read.

### D9 — NON-BLOCKERS

Wiring unused PI/portfolio flags; SMS; HartaBlocuri-as-title; Model B flag; D2 debit move; D13 `/accept`; Stripe Connect; new verification engine.

### STATUS

**DECISION SPECIFICATION — READY FOR FOUNDER APPROVAL**

No implementation authorized.

---

# Explicit statement

**No implementation performed.**

No source, schema, DB, prices, plans, trials, entitlements, flags, UI, tests, commit, or deploy was changed.

**STOP.**
