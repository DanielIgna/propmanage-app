# MARKETPLACE_CANONICAL_DECISION_SPECIFICATION

**Decision:** D1 — Canonical public Marketplace = **Model B**  
**Mode:** READ-ONLY specification. No implementation, flags, prices, credits, Stripe, commit, or deploy.  
**Sources:** repository code, `PROP_MANAGE_COMMERCIAL_ECONOMY_MASTER_AUDIT.md`, prior Marketplace decision map, System Atlas.  
**Date:** 2026-09-22

Status labels: DOCUMENTED · CONFIGURED · PERSISTED · IMPLEMENTED · RUNTIME-CONSUMED · ENFORCED · EVIDENCED · CONNECTED · DISCONNECTED · UNKNOWN

**Invariant for this document:** House Health subscription, Marketplace lead economy, and job transaction/payout are **three economies**. They are not one commission.

---

# 1. What D1 means

D1 is **not** `multi_offer_enabled = true`.

D1 is: **the public Marketplace architecture is Model B.**

```
CLIENT → REQUEST → MATCHING → MULTIPLE SPECIALISTS → OFFERS
      → CLIENT SELECTION → COMMERCIAL RELATIONSHIP
      → PAYMENT → ESCROW → EXECUTION → CONFIRMATION → PAYOUT
      → REPUTATION → House Health / Digital Twin feedback
```

| Stage | D1 meaning | Existing support | Assumes Model A today |
|---|---|---|---|
| Request lifecycle | `open` stays open while offers arrive | `requests.status=open` | `/accept` closes `open` immediately |
| Specialist discovery | See opportunity, do **not** take it | `GET /api/requests` (open list) | List CTA = Accept |
| Matching | Optional rank/filter of who *may* offer | `GET /api/match` PARTIAL | Not required to accept |
| Offer creation | Specialist submits, pays lead/access cost **if D2 says so** | `POST /offers` IMPLEMENTED, flag-gated | `/accept` = take job |
| Offer visibility | Client compares N offers | `GET /offers` + `OffersList` | No offer entity on A |
| Client selection | Client picks one offer | `POST /offers/{id}/accept` | Specialist self-assigns |
| Commercial relationship | Starts at a **named** event (D6) | Today = `assigned` + `specialist_id` | Same fields, A trigger |
| Payment | After selection (current checkout allows `open` or `assigned`) | `payments.create_checkout_session` | Same stack |
| Escrow | DB marker / DEMO checkout | `escrow_status` | Same; not Connect |
| Execution | `/start` | IMPLEMENTED | Same; not escrow-gated |
| Confirmation | `/confirm` | IMPLEMENTED `0.95` | Same job economy |
| Payout | Internal wallet | `job_payment` | Same |
| Reputation | Review after confirm | reviews / rating | Same |

**D1 does not, by itself:** turn on the flag, move 15/10/5 onto `/confirm`, redefine Lead Credits, create Stripe Connect, or invent request statuses.

---

# 2. Three economies (do not collapse)

| Economy | Object | Current trigger | Current value | Payer |
|---|---|---|---|---|
| **1. House Health subscription** | `hh_plans.price_eur` + `hh_subscriptions` | HH checkout `paid` | Seed 9 / 29 / **79**; UI Premium **249** | Client EUR |
| **2. Marketplace lead** | Credits / RON to **get onto a job** | Model A `/accept` | 45 credits or 45 RON | Specialist |
| **3. Job transaction** | Escrow → payout | `/confirm` | Hardcoded **5%** (`* 0.95`) | Taken from client escrow amount |

HH `lead_commission_pct` 15 / 10 / 5 is **attribution on HH-published leads**, captured only on Model B `accept_offer`, never applied to `/confirm`.  
FILE: `house_health_recommendations.py` · `marketplace_offers.py` · `requests.py:356`

---

# 3. D1.1 — Fate of `POST /api/requests/{id}/accept`

## 3.1 What the endpoint is

FILE: `backend/routes/requests.py` `accept_request`  
AUTH: `require_role("specialist")`  
ENFORCED: atomic 45 credits **or** 45 RON unless `lead_fee_waived` + `direct_specialist_id == user.id`  
STATE: `{status: open}` → `assigned` + `specialist_id`  
**No flag check.** Always public-callable on any open request the specialist can see.

## 3.2 Production callers of **this** route

| Caller | Kind | Evidence |
|---|---|---|
| `ActivityTimeline.jsx` `ScheduleProposalModal` | Specialist public + waived | `POST ${API}/requests/${requestId}/accept` |
| `SpecialistDashboard.jsx` | Opens that modal; CTA “Acceptă · 45 RON” / “GRATUIT” | RUNTIME-CONSUMED |
| `test_lead_credits.py` and marketplace / phase tests | Automation | AUTOMATED |
| `qa_automation.py` PAY-TX-LEAD | QA expects `lead_fee` −45 | AUTOMATED |

## 3.3 Same word, **different** routes (do not merge)

| Route | File | Relation to `/accept` |
|---|---|---|
| `POST /api/requests/{id}/offers/{offer_id}/accept` | `marketplace_offers.accept_offer` | Model B **client** selection |
| `POST /api/campaigns/{id}/accept-offer` | `community_buildings.py` | Group campaign; **creates requests already `assigned`**; never calls `/accept` |
| `POST /api/client/opportunities/{id}/accept` | `opportunities.py` | Client opportunity, not job lead |
| `POST /api/legal/me/accept` | `legal.py` | Terms |

## 3.4 Who **creates** requests that later hit `/accept`

| Creator | Fields | Then `/accept`? |
|---|---|---|
| `POST /api/requests` | public `open` | **Yes — public A** |
| `trusted_specialists` rebook | `direct_specialist_id`, `lead_fee_waived`, `is_rebooking` | **Yes — waived** |
| `maintenance_calendar` + specialist | same waive/direct | **Yes — waived** |
| `maintenance_calendar` without specialist | public `open` | **Yes — public A** |
| `publish-to-marketplace` (HH) | `open` + `house_health_source` | **Yes if A**; B if flag + offers |
| Campaign `accept-offer` | already `assigned`, waived | **No** |

List filter already hides others’ directed leads:  
`status=open` AND `direct_specialist_id ∈ [None, me]` — `list_requests`.

## 3.5 Possible final roles (D13 — **not chosen**)

| Role | Existing dependency | Break if `/accept` removed | Break if left fully public | Conflicts with B? | Second lead economy? |
|---|---|---|---|---|---|
| **A. DEPRECATED** | Tests/QA/Legal copy | Rebook + maintenance direct lose a claim API unless replaced | N/A | Removes A race | Removes A lead fee |
| **B. INTERNAL / ADMIN** | No admin-only accept today | Need a new admin assign | If still specialist-callable, still public | Yes if public | Yes if still 45 |
| **C. REBOOK / EXISTING RELATIONSHIP** | `trusted_specialists`, `is_rebooking`, waive | Rebook notify + 0 RON claim die | Public open still first-wins | **No** if restricted to `direct_specialist_id` + waive | **No** if fee stays 0 |
| **D. CAMPAIGN / SPECIAL BYPASS** | Campaign already assigns **without** `/accept` | Campaign **does not** depend on this route | Irrelevant to campaign | Campaign is a **third** assign writer | Waived at create |
| **E. COMPATIBILITY / SPECIALIST FLOW** | `/match` does not call `/accept` | Match still works | Public A remains | Yes | Yes |
| **F. OTHER** | Maintenance calendar dual mode | Calendar public mode uses A | Same as public A | Yes for public mode | Yes |

**Evidence does not pick a single role.** Proven **non-public** uses of the **same endpoint** are rebook and maintenance-direct (waive). Campaign is a sibling assign path, not an `/accept` caller.

## 3.6 Can `/accept` stay in the codebase without competing?

**Yes, only if it is no longer a public take-job on ordinary `open` requests.**

Safe residual (conceptual, not implemented): keep function + tests for `{direct_specialist_id, lead_fee_waived}` (and optionally admin).  
Unsafe residual (current): any specialist `/accept` on public `open` **races** `accept_offer` (both require `status=open`).

Leaving the route in git **without** changing who may call it **is** a competing public path. D1 does not delete the file; D13 must name the residual.

---

# 4. D1.2 — Request state machine

## 4.1 Current states (IMPLEMENTED)

`open → assigned → in_progress → completed → confirmed`  
(+ `closed` in some job counters; **not** a first-class confirm state)

| Field | Meaning today |
|---|---|
| `status=open` | Unassigned; A or B may claim |
| `status=assigned` | `specialist_id` set — **de facto commercial row** |
| `specialist_id` | Winner (A or B) |
| `selected_offer_id` | Set **only** by B `accept_offer` |
| `escrow_status` | Separate from `status` (`held` / released / …) |

**No** request status `offers` / `selected` / `paid`.

## 4.2 Target Model B vs existing fields

| Conceptual B step | Reuse | Ambiguity | Implicit? |
|---|---|---|---|
| `open` (awaiting offers) | `status=open` | Same word as “anyone may `/accept`” | — |
| offers exist | `marketplace_offers` rows | Not a request status | Yes |
| `selected` | `selected_offer_id` + still `assigned` | Selection **is** assignment in current B | Same event as relation |
| commercial relationship | `assigned` + `specialist_id` | Payment not required | Yes — D6 |
| payment / escrow | `payment_transactions`, `escrow_*` | Checkout allows `open` **or** `assigned` | Not a status |
| `in_progress` / `completed` / `confirmed` | Existing | `/start` ignores escrow | Yes |

**Missing as a distinct persisted request status:** none required for B if `open` + offers collection + `assigned`/`selected_offer_id` are kept.

**Are “selected” and “commercial relationship” the same event?**  
**In current B code: yes** — `accept_offer` writes both `selected_offer_id` and `assigned`/`specialist_id` in one update.  
**Architecturally they may differ** if D6 = payment or escrow (D6 still open). Do not add a `selected` status unless D6 splits them.

Do not invent states for this decision.

---

# 5. D1.3 — Offer model (island vs runtime)

| Piece | Status |
|---|---|
| Collection `marketplace_offers` | IMPLEMENTED |
| Fields | `request_id`, `specialist_id`, `fee_ron`, `priority_fee_ron`, `fee_paid_total`, `message`, dates, hours, `status` open/won/lost/withdrawn, `sponsored`, scores |
| Create | `submit_offer` — flag **ENFORCED** |
| Fee | 5–50 RON wallet + optional priority; **no credits**; no refund on withdraw |
| Cap | 5 open offers / request |
| Ranking | hybrid fee×0.35 + rating×0.30 + tier×0.20 + recency×0.10 + fairness×0.05 |
| List | `GET /offers` — **not** flag-gated; owner / admin / own offerer |
| Client select | `accept_offer` — **not** flag-gated; client owner |
| Withdraw | specialist, no refund |
| Flag | `fee_configs.multi_offer_enabled` default **false** |
| Client UI | `OffersList` mounted (`JobsV2`, `ClientRequestOffersPage`) |
| Specialist UI | `OfferApplyForm` **zero importers** — DISCONNECTED |
| Target DB volume | UNKNOWN (prior fact-check not completed) |

**Entity ≠ Model B live.** Code default is A. Client UI can show an empty offers page. Specialist cannot submit from mounted UI.

HH capture on `accept_offer` is CONNECTED only for `house_health_source` requests.

---

# 6. D1.4 — Specialist side

| Intended step | Current |
|---|---|
| Discover | `GET /api/requests` open (+ directed). `/match` optional. Notify on create. |
| Decide to participate | UI: **Accept**, not Apply |
| Create offer | API exists; **form unmounted**; 400 if flag off |
| Pay lead/access | **A:** 45 credits/RON on **win**. **B:** 5–50 RON on **submit**. Different event. |
| Wait | B: `status=open` on offer. A: no wait — already assigned |
| Client selects | B: `accept_offer`. A: specialist already won |
| Relationship starts | Both write `assigned` |

**Critical gap for Lead Credits:**  
Today credits buy **successful assignment** (`/accept`).  
B splits **submit** (wallet apply fee) from **selected** (no credit debit).  
D2 must name which of those two events (or D6) consumes 45 credits. That gap is why D2 is not implied by D1.

---

# 7. D1.5 — Client side

| Question | Evidence |
|---|---|
| Create request | `POST /api/requests` — `owner_id` ENFORCED |
| See specialists/offers | “Vezi ofertele” / HomeV2 compare if `offers` count > 0 |
| Ranked? | Yes if GET succeeds — hybrid default |
| Identity? | `specialist.name` + link `/specialist/:id` |
| Price shown? | **`total_fee_ron` = specialist apply fee**, not job `budget_estimate` |
| Verification? | `users.tier` badge (ENTRY/VERIFIED/PREMIUM), **not** KYC `users.verified` |
| Rating? | `RatingBadge` + low-rating warning |
| Compatibility? | **Not shown** on offer cards |
| Can select? | `Alege această ofertă` → `POST .../offers/{id}/accept` |
| Payment after? | Separate checkout; not in OffersList |

Client UI is **ahead** of specialist apply UI. Selection API is IMPLEMENTED; inventory of offers is starved if flag off / form unmounted.

---

# 8. D2 — Lead Credits under Model B (do not choose)

Current ENFORCED meaning: **45 credits (or 45 RON) on successful Model A `/accept`.**  
Grant: 135 on first specialist activation. ≠ `users.tokens`. ≠ HH sub.

| | Option A — consume on **offer submit** | Option B — consume on **selected** | Option C — consume when **relationship starts** | Option D — other evidence |
|---|---|---|---|---|
| Code fit | Would move debit to `submit_offer` (today wallet 5–50) | Closest to **current** meaning; hook `accept_offer` | **Same as B in current code** (selection = `assigned`) | Waive/rebook already 0; campaign skips `/accept` |
| Financial | 135 = 3 applies; stack with 5–50 RON = **double charge** unless B wallet fee removed | 135 = 3 **wins**; apply fee still 5–50 unless removed | Same as B unless D6 ≠ selection | Residual A-only |
| UX | Pay to wait; losers paid | Pay when chosen; apply maybe cheap/free | Same as B if D6=assigned | Direct jobs free |
| Abuse | Spam-apply drains 135 | Apply spam free (if no wallet fee) | Depends on D6 | Directed waive abuse if public |
| Refund | B withdraw = **no refund** today; credits would need policy | Failed A claim already refunds | If D6=payment, refund if pay fails | Waive: nothing to refund |
| Race | Two submits OK (cap 5) | Two clients N/A; A vs B still race if `/accept` public | If D6=payment, assign without pay | — |
| vs 45 RON | Cash twin of apply **or** keep 5–50 as cash apply | Cash twin of **win** (current) | Same as B if D6=assigned | — |
| vs HH `lead_commission_pct` | HH % of **offer fee** at B accept — different object | Same; still not `/confirm` 5% | Same | — |
| vs subscription | None today | None today | None today | — |
| vs Model B | Natural if credits **replace** apply wallet | Natural if credits **replace** A win fee | Needs D6 | Keep credits off B |
| Infra | `lead_credits` + `submit_offer` | `lead_credits` + `accept_offer` | same as B **or** checkout | waive flags |

**Option C is not a fourth event unless D6 ≠ selection.** Current architecture treats C = B.

Do not pick A/B/C/D here.

---

# 9. 45 RON — reclassification

**Verified:** 45 RON is the **Model A assignment cash fallback** when credits < 45.  
FILE: `requests.py` `LEAD_FEE_RON` / wallet branch.  
**Not** Model B offer fee (5–50). **Not** job 5%. **Not** a Beta flag. **Not** read from `platform_config.lead_fee_ron`.

Other “45” meanings (do not merge): `/match` display-only fallback; Legal/tour copy; SpecialistDashboard CTA that **ignores** credits.

**If Model B is canonical, 45 RON must be re-anchored or confined:**

- If D2 = selected/win: 45 RON can remain the cash twin of a **win** on `accept_offer` (or residual `/accept`).  
- If D2 = submit: 45 RON would collide with 5–50 apply — **decision required**.  
- If D2 = unused on B: 45 RON remains **A/residual only**.  
- Admin `lead_fee_ron` stays dead until D8/D2 names a consumer.

Do not change the number in this spec.

---

# 10. D6 — Commercial relationship (do not choose)

Current architecture **effectively** starts the relation at **`status=assigned` + `specialist_id`** (A `/accept` or B `accept_offer` or campaign insert).

| Candidate | Route | State | Money | Auth | Cancel / refund | Reputation |
|---|---|---|---|---|---|---|
| **A. Offer submit** | `submit_offer` | offer `open`; request still `open` | −5–50 RON, no refund | specialist + flag | Withdraw keeps fee | None |
| **B. Client selection** | `accept_offer` | `assigned` + `selected_offer_id` | no extra; HH % captured | client owner | Losers’ fees kept | None yet |
| **C. Payment success** | checkout / DEMO | `escrow_status=held` | client budget | client; status open **or** assigned | DEMO fake paid | None |
| **D. Escrow held** | checkout **or** `place_escrow` | marker; `/escrow` **no wallet debit** | marker ≠ custody | client | — | None |
| **E. Work start** | `/start` | `in_progress` | none | assigned specialist | Start **not** escrow-gated | None |
| **F. Other** | Campaign create `assigned`; rebook still `open` until `/accept` | — | waived | — | — | — |

Payment, escrow, and start are **not** the current relationship event. Reviews attach after confirm.

If D6 stays “selection/assignment”, **no new collection** is required.

---

# 11. D8 — Commission separation (preserve)

| | HH 15 / 10 / 5 | Lead 45 credits / 45 RON | Job 5% |
|---|---|---|---|
| Meaning | `hh_plans.lead_commission_pct` on **HH-sourced** requests | Model A **assignment** access | Platform cut of **escrow amount** |
| Calculated | publish: read plan; B accept: `offer_fee * pct/100` | constants 45 | `amount * 0.95` |
| Persisted | `house_health_source.commission_pct` / `_amount` | `transactions` lead_credit / lead_fee | `job_payment` 95% |
| Paid? | Status `captured` only; **`paid` NOT FOUND** | Yes (credits or wallet) | Implicit (specialist gets 95%) |
| Payer | Accounting on specialist **apply fee** | Specialist | Taken from client escrow |
| Receiver | Record / audit | Platform (debit) | Specialist wallet + implicit platform |
| Trigger | HH publish + B `accept_offer` | `/accept` | `/confirm` |

**15/10/5 is lead attribution on HH→marketplace publishes, not transaction commission, not a discount on `/confirm`, not specialist eligibility.**  
Premium UI “5%” **collides numerically** with job 5% — they are **not** the same calculator.

`platform_config.platform_commission_pct` is CONFIGURED, **not** RUNTIME-CONSUMED by `/confirm`.

---

# 12. D10 / D11 — Subscription × Marketplace (do not choose)

## 12.1 Price conflict

| Plan | Seed `price_eur` | Founder UI |
|---|---|---|
| Basic | 9 | 9 EUR |
| Pro | 29 | 29 EUR |
| Premium | **79** | **249 EUR** |

PricingPage reads **DB** `hh_plans`. Seed inserts only if slug missing. Target persisted Premium: **UNKNOWN**.

## 12.2 Trial

`trial_days` 7 / 14: UI + admin. Activation uses **30 days after paid**. **No writer** of `status=trial`. UI ≠ runtime grant.

## 12.3 What subscription **does** today

- Persists `hh_subscriptions`; entitlements `CLIENT_*`.  
- **ENFORCED** on House Health module and Digital Twin **advanced**.  
- Stamps `lead_commission_pct` on HH **publish**.  
- Does **not** gate `POST /api/requests`.  
- Does **not** change `/accept` 45 or `/confirm` 0.95.  
- Does **not** change specialist eligibility or `/match`.

## 12.4 Could subscription affect? (map only)

| | Supported by repo today? |
|---|---|
| **A. Marketplace access** | No on generic requests; HH publish needs twin owner, not a plan gate in that function |
| **B. Lead economics** | Only HH % stamp / B capture — not 45 |
| **C. Transaction commission** | **No** |
| **D. Specialist eligibility** | **No** (specialist entitlements = `experience_tier`) |
| **E. Ranking** | **No** (B uses specialist `users.tier`) |
| **F. Support / priority** | Seed **copy** on plans; not marketplace runtime |
| **G. Multiple** | Access (HH/DT) + attribution % only |
| **H. Other** | Recommendation → request CONNECTED |

Do not choose A–H.

---

# 13. Client trust ≠ subscription ≠ free user

**“Verified Client” is not a runtime rule.**

| Primitive | Marketplace create |
|---|---|
| Auth | ENFORCED |
| `properties.owner_id` | ENFORCED |
| Email / phone | NOT gated (`phone_verified` has no SMS) |
| History / HH sub | NOT gated |
| Client KYC | NOT FOUND |

Do not build a verification engine. Do not equate D9 free experiences with trust.

---

# 14. D9 — Three free experiences

**Does not exist** as a client request quota.

Closest reuse (after D1+D9, not now): Lead Credits pattern (wrong actor), job-count promotion (wrong meaning), quest “3 cereri” (achievement), `trial_days` (display only), DT free ingest (not jobs).

---

# 15. Payment / escrow boundary (DEMO — no Connect design)

```
request → [offers] → selection (assigned)
      → checkout (DEMO on target :8001) OR /escrow marker
      → escrow_status=held
      → /start (NOT gated)
      → /complete → /confirm → wallet +95%
```

| Question | Answer |
|---|---|
| What creates payment? | Checkout (DEMO fake or Stripe) |
| What creates escrow status? | Checkout success **or** `/escrow` marker |
| Work gated by escrow? | **No** |
| `held` means? | DB field, not Stripe custody |
| Wallet? | Internal accounting |
| Where is 5%? | `/confirm` only |

Model B conceptually needs: selection **before** pay (already the natural order if checkout stays on `assigned`). Checkout **also** allows `open` — pre-select pay is possible today. D6/D7 must say if that remains allowed. **Do not design Connect.**

---

# 16. Target graph (existing boxes + D1 direction)

```
CLIENT                         EXISTING
  → TRUST + PROPERTY           PARTIAL (auth+owner; “verified client” MISSING)
  → REQUEST                    EXISTING
  → MATCHING                   PARTIAL (optional /match; score DISCONNECTED)
  → MULTIPLE SPECIALISTS       PARTIAL (list exists; take-job CTA)
  → OFFERS                     PARTIAL (API+collection; apply UI MISSING; flag)
  → CLIENT SELECTION           PARTIAL (UI+API; inventory starved)
  → COMMERCIAL RELATIONSHIP    EXISTING as assigned (D6 open)
  → PAYMENT                    EXISTING DEMO
  → ESCROW                     PARTIAL marker
  → EXECUTION                  EXISTING
  → CONFIRMATION               EXISTING
  → PAYOUT                     EXISTING wallet
  → REPUTATION                 EXISTING
  → HH / DT                    PARTIAL publish; loop-back MISSING
```

Subscription sits on **HH/DT access** and **HH lead % stamp**, not on the job 5% edge.  
CONFLICTING: public `/accept` vs B; Premium 79 vs 249; HH 5% vs confirm 5%; `trial_days` vs paid+30.

---

# 17. Migration map A → B

| Item | Current | Required for B | Dependencies | Risk | Decision |
|---|---|---|---|---|---|
| 1. `/accept` | Public first-wins | Residual or gone | D13 | Race if both public | **D13** |
| 2. Specialist CTA | Accept 45 RON / credits | Apply offer | D1, form mount | Empty B if CTA stays A | Product |
| 3. Lead Credits | Debit on A win | New anchor | D2 | Double charge vs 5–50 | **D2** |
| 4. 45 RON | A cash fallback | Re-anchor or confine | D2 | Two lead prices | D2 |
| 5. Offers collection | Island | Canonical store | flag + UI | — | D1 (done as direction) |
| 6. Offer submit | Flag 400; form unmounted | Public path | flag **after** D13 | Turning flag on **without** D13 = race | Flag ≠ D1 |
| 7. Offer visibility | GET ungated | Same + consistent flag | D13 | GET works, submit doesn’t | Hygiene |
| 8. Client selection | Mounted | Canonical | offers exist | Select empty list | — |
| 9. Request states | 5 statuses | Reuse | D6 | Extra statuses unnecessary | D6 |
| 10. Notifications | A + B events exist | Prefer B events | — | Dual notify | — |
| 11. Payment | After assign (or open) | After D6 event | D6 D7 | DEMO | D7 later |
| 12. Escrow | Marker | Same until D7 | D7 | “held” ≠ custody | Do not Connect now |
| 13. Confirmation | 0.95 | Unchanged unless D8 | D8 D11 | Silent merge with HH % | **D8 D11** |
| 14. Commission | Three objects | Keep separate | D8 D11 | UI “5%” confusion | **D11** |
| 15. Analytics | 45×accept | Will lie if B | D2 | Wrong revenue | After D2 |
| 16. Admin | Dead A knobs; live B flag | Don’t activate dead knobs | D8 | False SSOT | D8 |
| 17. Tests | A-centric credits | Rewrite to D2 event | D2 D13 | CI green on wrong model | After D2 |
| 18. QA | PAY-TX-LEAD −45 | Same | D2 | QA fights B | After D2 |

---

# 18. Architectural invariants (migration)

1. **One** canonical **public** Marketplace model (D1 = B).  
2. A and B must not both take the same public `open` request.  
3. `lead_credits` ≠ `users.tokens`.  
4. Lead economy ≠ job `/confirm` 5%.  
5. HH `lead_commission_pct` must not silently become job payout commission.  
6. Subscription ≠ verification.  
7. Verification ≠ subscription.  
8. Stripe DEMO / `escrow_status=held` ≠ real custody / Connect.  
9. `properties.owner_id` remains ENFORCED on create.  
10. Client must not set own commission, verification, or plan price (HH checkout already uses server `price_eur`; `/escrow` **amount** is client-supplied — existing risk, do not expand).  
11. Reuse `requests`, offers, credits, wallet, `hh_plans`, `fee_configs`, entitlements — no second Marketplace engine.  
12. Campaign / rebook assign writers are **not** specialist types and **not** HH plans.  
13. PARTNER ≠ SPECIALIST.  
14. Enabling `multi_offer_enabled` is **not** completing D1.  
15. `OfferApplyForm` existing is not “B live”.  
16. Confirm `0.95` stays the job-economy calculator until D8 explicitly retargets it.

---

# 19. FINAL DECISION PACKAGE

### D1 — Canonical Marketplace

**Direction specified:** public Marketplace = **Model B** (multi-offer + client choice).  
**Runtime today:** Model A `/accept` is ENFORCED and canonical.  
**Meaning:** public take-job is selection of an offer, not specialist first-wins. Payment/escrow/execution/confirm/payout/reputation **reuse** the existing post-`assigned` spine.  
**Not implied:** flipping the flag, merging commissions, or deleting `/accept` from the repo.

### D2 — Lead Credits

Unresolved anchors (do not select):

- **A.** Consume on offer **submit**  
- **B.** Consume on **selected**  
- **C.** Consume when **relationship starts** (equals B unless D6 ≠ selection)  
- **D.** Unused on B / residual A and waive only  

Current evidence: **B/C on `/accept`**. B apply fee is a **second** lead price (5–50 RON).

### D6 — Commercial Relationship

Candidates: submit · **selection** · payment · escrow held · start · campaign-create.  
**Current effective trigger:** `assigned` + `specialist_id` (selection in B, `/accept` in A).  
Payment/escrow/start are **not** that event today.

### D8 — Commission Architecture

Keep three objects: HH `lead_commission_pct` (attribution, partial) · lead 45 credits/RON (A assignment) · job `* 0.95` (confirm).  
Do not merge. Admin `%` unused. VE/design/partner % are other products.

### D10/D11 — Subscription

HH sub **ENFORCED** for HH/DT access; **stamps** 15/10/5 on HH publish; **does not** change generic marketplace access, 45, or confirm 5%.  
Seed Premium **79** vs UI **249**. Trial display ≠ grant.  
Whether sub should later affect access / lead / job cut / rank is **unchosen**.

### D13 — `/accept`

**Proven callers:** SpecialistDashboard / ScheduleProposalModal; tests; QA.  
**Proven create-then-accept:** public requests; **rebook**; **maintenance-direct** (waive).  
**Not a caller:** campaign (assigns at insert).  
Possible roles: deprecate · admin · **rebook** · campaign-adjacent (weak) · compatibility (unsupported) · keep public (conflicts D1).  
**Not chosen.** Residual is possible **if** public first-wins is removed.

### MODEL A → MODEL B BLOCKERS

1. D13 — public `/accept` races B.  
2. D2 — credits vs 5–50 apply (double economy).  
3. Specialist apply UI unmounted + flag off.  
4. D6 if relation is not selection (would require extra wiring).  
5. D8/D11 if founder intends HH 15/10/5 to **be** the job cut (it is not today — changing that is a **new** decision, not a flip).

### MODEL A → MODEL B NON-BLOCKERS

- New request statuses  
- New credit / verification / matching / intel / policy engines  
- Stripe Connect / real escrow  
- Partner merge  
- Wiring dead `lead_fee_ron` / `platform_commission_pct`  
- Unifying four specialist ladders  
- Client “Verified” engine  
- 3-free implementation  
- Changing 45 or 5% **values**  
- Premium 249 vs 79 (pricing SSOT is `hh_plans` DB, not D1)

### DO NOT BUILD

Second offer engine · second request collection · new credits · new KYC · new matcher · new commission engine · Connect · quota engine · partner-as-specialist · treating UI/docs as runtime.

### NEXT FOUNDER DECISIONS

1. **D13** — residual `/accept` (rebook/maintenance-direct vs deprecate vs other).  
2. **D2** — when 45 credits (and 45 RON) fire under B; whether B 5–50 remains.  
3. **D6** — if relationship is **not** selection, say so; else it is already `assigned`.  
4. **D11** — is HH 15/10/5 allowed to stay attribution-only, or must it replace job 5%?  
5. **D10** — does HH sub gate **creating** marketplace requests, or only HH/DT + publish stamp?  
6. **D9** — are 3 free client experiences a real promise? (separate from trust)  
7. **Premium price** — 79 seed vs 249 UI (commercial, not D1 architecture).

---

**STOP.** File: `memory/audits/MARKETPLACE_CANONICAL_DECISION_SPECIFICATION.md`  
No other files modified. No implementation.
