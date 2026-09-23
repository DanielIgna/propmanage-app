# D8 — MARKETPLACE COMMISSION DECISION SPECIFICATION

**Decision:** D8 — Canonical meaning and lifecycle of the Marketplace **job** platform commission after D6  
**Mode:** READ-ONLY. No implementation, schema, flags, prices, Model B enablement, Stripe, `/accept` change, commit, or deploy.  
**Given:** D1 = public Model B · D2 = Lead Credits on `submit_offer` · D6 = commercial relationship at `accept_offer` (`assigned` + `specialist_id` + `selected_offer_id` + offer `won`)  
**Date:** 2026-09-23

Payment, escrow, execution, confirmation and payout remain **distinct** from D6. D6 is **not** reinterpreted as payment or escrow.

**No implementation performed.**

---

# 1. Executive decision

## What the repository actually does

The only Marketplace job-payout path that applies a platform cut is:

```
POST /api/requests/{req_id}/confirm
  confirm_complete
  amount = requests.escrow_amount or 0
  specialist_amount = amount * 0.95
  users.wallet_balance += specialist_amount
  transactions.type = job_payment   # net only
```

FILE: `backend/routes/requests.py` `confirm_complete`

That is **not** a second charge to the client.  
That is **not** a posted `platform_commission` ledger row.  
That is a **hardcoded 5% withholding from the specialist wallet credit**.

Admin `platform_config.platform_commission_pct` (default 5.0) is **stored and editable** and **not read** by `/confirm`.  
House Health `lead_commission_pct` 15 / 10 / 5 applies to the **offer/apply fee** at `accept_offer` and is **never** the `* 0.95` calculator.  
Lead Credits and the 5–50 RON apply fee are **participation**, not this commission.

## D8 evidence-derived canonical rule (proposed for founder approval)

```
MARKETPLACE JOB COMMISSION
  = 5% of the applicable job amount
  = withheld from the specialist payout
  ≠ extra charge on the client
  ≠ Lead Credits
  ≠ 5–50 RON offer/apply fee
  ≠ House Health lead_commission_pct
  ≠ Verified Estate sale commission

CLIENT pays the gross job amount (when a payment exists).
SPECIALIST receives 95% net.
PLATFORM keeps 5% by omission (not posted today).

CURRENT REALIZATION EVENT = client confirmation (/confirm),
which is the same function as internal wallet payout.
```

D6 creates the pair. D8 does **not** become due at D6 in current code.

**STATUS:** **D8 — READY FOR FOUNDER APPROVAL** on meaning, bearer, rate, and separation.  
Realization **stay-at-confirm vs move-to-payment** remains a founder choice among the unranked models in §13. Gross-base SSOT remains open (D7 overlap).

---

# 2. Current runtime evidence

## 2.1 Confirm / payout (Marketplace job spine)

| | |
|---|---|
| File / symbol | `backend/routes/requests.py` `confirm_complete` |
| Route | `POST /api/requests/{req_id}/confirm` |
| Auth | `require_role("client")` + `client_id` match |
| Gate | `status == "completed"` only |
| Payment required? | **No** |
| Escrow required? | **No** |
| Trust / KYC / tier required? | **No** |
| Base | `amount = req.get("escrow_amount") or 0` |
| Rate | **Hardcoded** `* 0.95` — comment: “5% platform fee” is **not** in this function; that comment exists on disputes |
| Specialist credit | `$inc` `wallet_balance` by `specialist_amount` |
| Ledger | `transactions` `{type: job_payment, amount: specialist_amount}` — **net only** |
| Commission row | **NOT FOUND** |
| After | `status=confirmed`, `escrow_status=released` |
| Also | +100 `users.tokens`; `jobs_completed++` both parties |

Second confirm: status is no longer `completed` → 400. **No atomic claim.** Parallel double-confirm while still `completed` is an unguarded race.

## 2.2 Same `* 0.95` on sibling paths (not the public Marketplace spine)

| Path | File | Base | Ledger |
|---|---|---|---|
| Dispute `pay_specialist` | `disputes.resolve_dispute` | `escrow_amount * 0.95` | `dispute_payment` net |
| Dispute `split` | same | `(escrow_amount - client_slice) * 0.95` | `dispute_payment` + `dispute_refund` |
| Design phase complete | `design.complete_phase` | `quote["price"] * 0.95` | `design_phase_payout` |
| Demo time machine | `demo_time_machine.SPECIALIST_SPLIT = 0.95` | sim | sim |
| Admin analytics | `admin.py` `gmv * 0.05` | sum of confirmed `escrow_amount` | **Not a ledger post** |
| Admin dispute UI | `AdminModals.jsx` | displays `amount * 0.95` | UI only |

## 2.3 What does **not** apply 5%

| Event | File | Job 5%? |
|---|---|---|
| `submit_offer` | `marketplace_offers.py` | No — wallet 5–50 apply fee |
| `accept_offer` (D6) | `marketplace_offers.py` | No — HH % **captured** on apply fee |
| `accept_request` | `requests.py` | No — 45 credits or 45 RON lead |
| Checkout / webhook | `payments.py` | No split — records client amount + marker |
| `place_escrow` | `requests.py` | No — client `amount` → `held` |
| `/start` `/complete` | `requests.py` | No |

---

# 3. Commission concepts inventory

Do **not** merge these.

| Concept | Object | Typical value | Event | Payer | Runtime |
|---|---|---|---|---|---|
| **Marketplace job commission (D8)** | implicit `escrow_amount - escrow_amount*0.95` | 5% | `/confirm` | Specialist (withheld) | **RUNTIME-EFFECTIVE** hardcoded |
| **Lead Credits** | `users.lead_credits` | 135 grant / 45 consume | `/accept` today; D2 = `submit_offer` | Specialist | Separate economy |
| **Legacy /accept cash** | `LEAD_FEE_RON` / `lead_fee` tx | 45 RON | `/accept` wallet fallback | Specialist | Model A residual (D13) |
| **Offer / apply fee** | `marketplace_offers.fee_ron` + `priority_fee_ron` | 5–50 RON | `submit_offer` | Specialist wallet | Flag-gated; ≠ job 5% |
| **House Health lead attribution** | `hh_plans.lead_commission_pct` → `house_health_source` | 15 / 10 / 5 | Publish snapshot; **capture** on `accept_offer` | Not paid as money | Attribution metadata |
| **Admin platform %** | `platform_config.settings.platform_commission_pct` | default 5.0 | Admin PUT | — | **Persisted, unused** by `/confirm` |
| **Admin lead fee** | `platform_config.settings.lead_fee_ron` | default 45.0 | Admin PUT | — | **Unused** by `/accept` (`LEAD_FEE_RON = 45.0` constant) |
| **fee_configs** | `multi_offer_enabled`, min/max apply, ranking | — | B offers | — | Not job commission |
| **Verified Estate sale commission** | `app_settings.pricing.commission_pct` | VE product (tests 2.5) | VE sale UI / settings | Property sale | **Other product** |
| **Experience Spaces default** | `es_default_commission_pct` | 15 | ES config | Other product | **Other product** |
| **Partner commissions** | `docs_evidence_missing/partner_commissions.py` | — | — | — | **NOT IMPLEMENTED** |
| **Client tokens** | `users.tokens` +100 on confirm | loyalty | `/confirm` | Platform grants | ≠ commission |
| **3 free client projects** | — | — | — | — | **NOT IMPLEMENTED** |

---

# 4. Current 5% trace (D8.1 / D8.2 / D8.3 / D8.7)

## 4.1 D8.1 — What is the commission?

| Option | Evidence |
|---|---|
| **A. Charged to the client** | **No.** Checkout amount = server `budget_estimate`. Confirm does not add 5% to the client. |
| **B. Withheld from specialist payout** | **Yes.** Wallet credit is `* 0.95`. Platform never credits the omitted 5%. |
| **C. A fee charged to the specialist** | **No separate charge line.** Specialist is not debited 5%. The 5% is never taken as a fee transaction. |
| **D. Another documented mechanism** | Implicit haircut + analytics `gmv * 0.05`. |
| **E. Undefined** | Meaning is evidenced. **Representation** (posted commission) is missing. |

**Evidence classification:** **B**, implemented as an **implicit payout haircut / hardcoded business rule**, not as a true posted platform-commission settlement.

Dispute comment: `specialist_amount = amount * 0.95  # 5% platform fee` — FILE: `disputes.py:118`.

## 4.2 D8.2 — Economic base

| Candidate | Used as `* 0.95` base? |
|---|---|
| **A. Total job price** | **No dedicated field.** Offer has no job-price. Intended meaning only if `escrow_amount` equals the agreed job. |
| **B. Specialist payout amount** | **No** (circular). Net is the **output**. |
| **C. Amount held in escrow** | **YES — runtime.** `requests.escrow_amount` |
| **D. Specialist offer/application fee** | **No** for D8. Used only by HH capture: `offer_fee * (commission_pct/100)` |
| **E. Other** | Design uses `phases[].price`. Admin GMV uses confirmed `escrow_amount`. Checkout writes `budget_estimate` into `escrow_amount`. `/escrow?amount=` can **overwrite** with a **client-supplied** number. Unpaid confirm uses **0**. |

**Explicit distinctions:**

| Name | Current field | Must not be called |
|---|---|---|
| Offer / apply fee | `fee_paid_total` / `selected_offer_fee` | Job price / D8 base |
| Job price | **No SSOT field** | Escrow / payout |
| Escrow amount | `requests.escrow_amount` | Real custody |
| Payout amount | local `specialist_amount` | Gross |
| Platform commission | **none persisted** | Lead Credits / HH % |

## 4.3 D8.3 — Percentage table

| Percentage | Source | Meaning | Event | Payer / payee | Runtime status | SSOT candidate? | Conflict? |
|---|---|---|---|---|---|---|---|
| **5% (0.95 haircut)** | Hardcoded in `confirm_complete`, `resolve_dispute`, `design.complete_phase`, `SPECIALIST_SPLIT` | Marketplace / design / demo specialist net | Confirm / dispute resolve / design phase | Specialist bears; platform keeps by omission | **RUNTIME-EFFECTIVE** Marketplace-specific (plus design/demo copies) | **Current rate SSOT = source code** | Conflicts with unused admin 5.0 if admin changes value |
| **5.0** | `platform_config.platform_commission_pct` default; `AdminPlatformTools.jsx` | Intended platform commission | Admin edit only | — | **Persisted but unused** by payout | Possible later rate SSOT | **Yes** — admin can store 7.5 (`test_admin_console`); confirm still 0.95 |
| **5 / 10 / 15** | `hh_plans.lead_commission_pct` seed Basic/Pro/Premium | HH lead **attribution** on **apply fee** | HH publish snapshot; capture at `accept_offer` | Not settled as money (`paid` never written) | **House Health-specific** | HH plan SSOT for **attribution only** | **Numeric collision** with job 5% on Premium — **different base and event** |
| **10 default** | `house_health_recommendations.py` if no plan | Fallback HH % | Publish | — | HH-specific | No | Same family as 15/10/5 |
| **2.5 / settings** | `app_settings.pricing.commission_pct` | Verified Estate sale | VE pricing | VE sale | **Partner/product-specific** | VE only | Must not become Marketplace job % |
| **15** | `experience_spaces.config.es_default_commission_pct` | Experience Spaces | ES | Other | Other product | No | Unrelated |
| **45 RON / 45 credits** | `LEAD_FEE_RON` / `LEAD_CREDIT_COST` | Participation | `/accept` | Specialist | Runtime Model A | D2 | **Not a percentage** |
| **5–50 RON** | `submit_offer` `fee_ron` | Participation apply | Submit | Specialist wallet | Flag-gated | D2 reconcile | **Not** job 5% |
| **gmv * 0.05** | `admin.py` dashboard | Analytics estimate of platform fees | Report | — | **Analytics only** | No | Assumes 5% of GMV; not a settlement |
| Ranking 0.05 fairness | `marketplace_offers._compute_score` | Offer rank weight | List offers | — | Ranking | No | Not money |

---

# 5. House Health 15 / 10 / 5 trace (D8.9)

| Step | Evidence |
|---|---|
| Seed | `house_health_billing.DEFAULT_PLANS`: Basic **15**, Pro **10**, Premium **5** |
| Admin edit | `house_health_plans.py` + `AdminHouseHealthPage.jsx` |
| Publish | `publish` copies plan % onto `requests.house_health_source.commission_pct`, status **`pending`** |
| Capture | `accept_offer`: `commission_amount = offer_fee * (commission_pct/100)`; status **`captured`**; `hh_audit_log` `commission_captured` |
| Paid | Comment says `pending → captured → paid`. **`commission_status=paid` is never written** |
| `/confirm` | Does **not** read `house_health_source` |

UI copy (`RecommendationsSection.jsx`): “Comisionul platformei: X% **din fee-ul lead-ului**.”

**D8.9 determination from evidence:**

| Option | Evidence |
|---|---|
| **A. Completely separate from Marketplace job commission** | **Supported.** Different base (apply fee vs `escrow_amount`), different event (select vs confirm), no money settlement, Premium 5% is coincidence. |
| **B. Become the source of Marketplace commission** | **Contradicted** by runtime. Wiring this into `/confirm` would silently replace hardcoded 5% with 15/10/5 and change the base. |
| **C. Renamed later** | Possible product language; not required by code. |
| **D. Remain attribution metadata only** | **Matches current behavior** (`captured`, never `paid`). |
| **E. Other** | — |

**Architectural conclusion for D8:** treat HH `lead_commission_pct` as **A + D** — separate economy, attribution metadata only.  
**D11** may still decide whether captured HH amounts are ever invoiced. That is **not** D8.

If the founder wants HH % to **become** the job commission, that is **OPEN — FOUNDER DECISION REQUIRED** under D11, and it would **conflict** with the evidenced 5% job haircut.

---

# 6. Admin configuration trace (D8.12)

## 6.1 `platform_config.platform_commission_pct`

| | |
|---|---|
| Stored | `db.platform_config` `{key: "settings", value.platform_commission_pct}` |
| Default | `5.0` in `admin_console.DEFAULT_SETTINGS` |
| Editable | `PUT /api/admin/settings` `update_settings` |
| Who | `require_role("admin")` |
| UI | `frontend/src/pages/admin/AdminPlatformTools.jsx` `settings-commission` |
| Read by `/confirm`? | **No** |
| Read by disputes / design / payments? | **No** |
| Tests | `test_admin_console.py` persists 7.5 then restores 5.0 — **does not assert payout change** |
| Conflict | **Yes** — dead knob vs hardcoded 0.95 |
| Classification | **Dead configuration knob** for Marketplace payout |

## 6.2 Related knobs

| Knob | Stored | Editable | Consumed by job payout? |
|---|---|---|---|
| `lead_fee_ron` | same settings doc | Admin | **No** — `/accept` uses constant 45 |
| `fee_configs` | `fee_configs` singleton | `specialist_progression.py` | **No** job 5%; B flag / apply bounds / ranking |
| `hh_plans.lead_commission_pct` | `hh_plans` | Admin HH | **No** job 5% |
| `app_settings.pricing.commission_pct` | app settings | `AdminSettingsControl.jsx` | **VE only** |
| `es_default_commission_pct` | ES config | Admin ES | **ES only** |

**Do not assume configuration = runtime.** Runtime job rate = **`0.95` in source.**

---

# 7. D8 event candidates (D8.4)

D6 is fixed: relationship begins at client offer selection.  
Commission **due** is a **different** event.

| | A submit_offer | B accept_offer (D6) | C payment success | D escrow held | E work completed | F client confirms | G payout |
|---|---|---|---|---|---|---|---|
| Job 5% in code? | No | No | No | No | No | **Yes `* 0.95`** | **Same function as F** |
| Relationship exists? | No | **Yes (D6)** | Maybe (pay allowed on `open`) | Maybe | Yes if started | Yes | Yes |
| Calculated? | No | HH % on apply fee only | No | No | No | **Yes** | Yes |
| Withheld? | Apply fee / credits (D2) | No job 5% | No | Marker only | No | **Implicit** | Implicit |
| Settled? | Participation | HH captured ≠ paid | DEMO paid record | Marker | No | **Wallet net** | Same |
| Lead Credits? | D2 target | Must not | Must not | Must not | Must not | Must not | Must not |

**Current:**  
`commercial relationship begins` = D6 (`accept_offer`)  
`commission becomes due` = **not separately modeled**  
`commission is calculated` = `/confirm` (and dispute/design copies)  
`commission is withheld` = same moment (never credit 5%)  
`commission is settled` = same moment (internal wallet net)

They **coincide** at F/G today. They **must remain distinguishable** in language.

---

# 8. Payment / escrow / confirmation relationship (D8.8)

```
request (D6 assigned)
  → POST /payments/checkout-session     budget_estimate → payment_transactions
  → DEMO: paid immediately + escrow_amount + escrow_status=held + escrow_deposit (demo:true)
     LIVE path exists in code; this process is DEMO (GET /api/health stripe=demo)
  → OR POST /requests/{id}/escrow?amount=   client amount → held, NO payment_transactions
  → /start /complete   (not gated on held)
  → /confirm           escrow_amount * 0.95 → wallet + job_payment
```

| Question | Evidence |
|---|---|
| What Stripe does today on this process | **Nothing.** `DEMO_STRIPE` inserts `cs_demo_*`. |
| Internal escrow fields | `escrow_amount`, `escrow_status` (`held` / `released` / `frozen`) = **internal marker** |
| Where money moves | DEMO: nowhere external. Live: Stripe Checkout to platform (if real key). Specialist: **internal `wallet_balance` only** |
| Stripe Connect | **NOT FOUND** in payment/payout code. Mentioned in seed FAQ / founder_gate copy — **not implemented** |
| Platform fee transfer | **NOT FOUND** (`application_fee` / Connect transfer absent on job path) |
| Specialist Stripe payout | **NOT FOUND.** `wallet.py` has top-up, **no withdraw** |
| DEMO? | **Yes** for job checkout on the verified process |

Do not call the DB marker real escrow. Do not call wallet credit a Stripe payout.

---

# 9. Failure / cancellation / refund (D8.5 / D8.6)

## 9.1 Client selects → payment fails

| Object | Current representation | Missing |
|---|---|---|
| Request | Stays `assigned` (D6 already written) | No “unpaid assigned” state |
| `selected_offer_id` | Remains | — |
| `specialist_id` | Remains | — |
| Commercial relationship | **Exists** (D6) | — |
| Commission | **Not calculated** | — |
| Offer status | Winner stays `won` | — |
| Lead Credits | Not touched at D6 | D2 already spent at submit (target) |
| Wallet | No job movement | DEMO rarely “fails” |
| Escrow | Not held unless `/escrow` or prior DEMO | Live unpaid = no held from checkout |

**Already represented:** pair persists without pay.  
**Missing:** payment-failure policy; no auto-unassign; no commission accrual.

## 9.2 Payment succeeds, work never starts

| Mechanism | Exists? | Commission |
|---|---|---|
| First-class client cancel | **NOT FOUND** on `requests.py` | — |
| First-class specialist cancel | **NOT FOUND** | — |
| Timeout / auto-release | **NOT FOUND** on this spine | — |
| Dispute | Yes if status `assigned\|in_progress\|completed` and escrow not `released` | 5% only if resolve `pay_specialist` / `split` |
| Refund API | **NOT FOUND** (no Stripe refund on job checkout) | — |
| Dispute `refund_client` | Credits **full** `escrow_amount` to **client wallet** | 5% **not taken** |

**Commission if never confirmed:** **deferred** — never calculated, never withheld, never settled.  
**Reversible?** There is nothing to reverse until confirm/dispute.  
**Policy:** **currently undefined** beyond “no confirm ⇒ no 5%.”

Do not invent a timeout or refund policy here.

## 9.3 Client confirms (D8.7)

Exact path: §2.1 + §8.

The current 5% is:

| Label | Fits evidence? |
|---|---|
| True posted platform commission | **No** — no commission record |
| **Payout haircut** | **Yes** |
| Accounting approximation | Admin `gmv*0.05` is approximation; confirm is live haircut |
| **Hardcoded business rule** | **Yes** |
| Other | Implicit retention by omission |

---

# 10. Verification conditionality (D8.10)

| Signal | Current runtime on `/confirm` `* 0.95` | Target possibility | Undecided? |
|---|---|---|---|
| Verified client | **Not read** | Could reuse `email_verified` | Yes — not D8 |
| Property registered | Request already required a property at create | — | — |
| Verified specialist | Copied to `specialist_verified` at assign; **not** a confirm gate | Could gate payout | Yes |
| Specialist tier | Used in offer ranking; **not** confirm | Could vary % | Yes — would break single 5% |
| KYC | Sets `verified`; **not** confirm | Could gate payout | Yes |
| Capabilities | Not read | — | — |
| Compatibility / match | Optional discovery | — | — |
| House Health plan | Not read at confirm | Must **not** silently change job 5% | D11 |
| Other trust scores | Ranking / cards | — | — |

**CURRENT RUNTIME:** commission is **not** conditional on trust.  
**TARGET POSSIBILITY:** existing flags could be reused later.  
**UNDECIDED:** whether they should. **Do not create a verification rule in D8.**

---

# 11. Three free client projects (D8.11)

Inspected: entitlements, HH trials, DT FREE projects, quests, Lead Credits, `jobs_completed`.

| Nearby object | = Marketplace “3 free client projects”? |
|---|---|
| 135 / 45 Lead Credits | **No** (specialist) |
| Experience tier “3 completed jobs” | **No** (promotion) |
| FC quest “3 cereri / 30z” | **No** (achievement) |
| HH `trial_days` | **No** (display; not a job quota) |
| DT FREE project (`test_dt_p1_consolidation_iter200`) | **No** (twin container) |
| `entitlements.py` | HH/DT features; **`create_request` / `/confirm` do not use `require_entitlement`** |

**NOT IMPLEMENTED / NO RUNTIME SOURCE FOUND.**

Do **not** mix D9 quota with D8 commission. If D9 later waives client payment, founder must still say whether the 5% specialist haircut applies (open).

---

# 12. Security invariants (D8.13)

Future implementation (not now) must preserve:

1. Commission rate **cannot** be client-controlled.  
2. Percentage **cannot** be supplied by the frontend as authoritative.  
3. Calculation **must** be server-side.  
4. Payout **cannot** bypass the commission (no confirm path that credits 100% of job value).  
5. Duplicate confirmation **must not** duplicate commission or payout. Today: status gate only; **no atomic claim**.  
6. Retry / webhook **must not** double-charge commission. Checkout does not compute 5% today; fulfill is idempotent on `payment_status`. Confirm is a separate race.  
7. Failed payment **must not** create a settled commission. Today it does not.  
8. Refunds / cancellations need a **deterministic** treatment (currently only dispute resolve).  
9. Ledger entries must be **traceable** (today: net `job_payment` only; 5% not posted).  
10. Do not rely on float as money SSOT if production requires minor units. **Current architecture uses `float` `* 0.95`.** No integer bani/cents on this path.  
11. Lead Credits **must never** silently become RON.  
12. House Health attribution % **must not** silently become Marketplace job commission.  
13. `/escrow?amount=` is a **client-controlled base** — authorization gap for the **amount**, not the rate.  
14. Admin `platform_commission_pct` must not be treated as live until it is actually read.  
15. One job confirmation → at most one 5% realization.

---

# 13. SSOT analysis (D8.14)

**Do not create a new SSOT.**

| Candidate | Can it be the D8 rate SSOT? | Can it be the D8 base SSOT? |
|---|---|---|
| Hardcoded `0.95` | **It already is** the runtime rate | No |
| `platform_config.platform_commission_pct` | Stored 5.0; **unused** — reuse **later** if wired | No |
| `fee_configs` | Lead/B apply — **wrong economy** | No |
| `hh_plans.lead_commission_pct` | **Wrong economy** | No |
| Request / job snapshot | No rate snapshot today | `escrow_amount` is **de facto base** (ambiguous) |
| `payment_transactions.amount` | No | Gross **candidate** when checkout ran |
| `budget_estimate` | No | Checkout input; not confirm base unless copied |

**Prefer reuse:** keep computing at `confirm_complete`; optionally **later** read `platform_commission_pct` instead of `0.95`; persist gross / commission / net on the **existing** `requests` + `transactions` documents.  
**Wiring config is a founder choice**, not implied by D8 meaning.

---

# 14. Legacy reconciliation map (D8.15)

| Path | Current economic role | Classification |
|---|---|---|
| `/confirm` `* 0.95` | Job commission realization | **KEEP** as realization point; **MODIFY** later if explicit ledger / config read |
| Internal wallet `job_payment` | Specialist **net** | **KEEP** |
| `payment_transactions` | Client payment record | **KEEP** (gross candidate) |
| `escrow_deposit` | Checkout-side amount (often DEMO) | **KEEP** as pay record; ≠ commission |
| `accept_offer` | D6 + HH capture | **KEEP** as D6; HH capture **INTERNAL-ONLY** attribution |
| Legacy `/accept` | Model A assign + 45 credits/RON | **DEPRECATE** as public writer (D13); **not** a job-commission event |
| HH `lead_commission_pct` | Attribution on apply fee | **KEEP** separate (D11) |
| `platform_commission_pct` | Dead admin knob | **DECISION REQUIRED** (wire vs leave unused) |
| `fee_configs` | B flag / apply | **KEEP** off D8 |
| Admin `gmv * 0.05` | Analytics | **KEEP** as report |
| Design `* 0.95` | Other product | **INTERNAL-ONLY** (same numeric rule, different spine) |
| Dispute `* 0.95` | Same implicit 5% | **KEEP** aligned with confirm |
| VE / ES / partner % | Other products | **KEEP** isolated |
| 5–50 apply fee | Participation | **DECISION REQUIRED** under D2 — ≠ D8 |

---

# 15. D8 decision options (D8.16)

Unranked. Not “best.”

### MODEL A — Commission due at client selection (D6)

| | |
|---|---|
| Trigger | `accept_offer` |
| Economic base | Undefined today (no job price on offer; HH uses apply fee) |
| Reversibility | Would charge before pay/work; refund undefined |
| Payment failure | Commission already due while unpaid |
| Cancellation | No cancel route |
| Refund | None |
| Reuse | Would overload D6 |
| Conflict with code | **Total** — `accept_offer` has no `* 0.95` |
| Open questions | What amount? Unpaid jobs? |

### MODEL B — Due after successful payment / escrow

| | |
|---|---|
| Trigger | Paid and/or `held` |
| Economic base | `payment_transactions.amount` or `escrow_amount` |
| Reversibility | Needs refund rules (missing) |
| Payment failure | Not due |
| Cancellation | Undefined |
| Refund | Dispute only today |
| Reuse | Checkout + marker exist; **no** 5% there |
| Conflict with code | Confirm still haircuts later (double-risk if both fire) |
| Open questions | DEMO = due? `/escrow` without pay = due? D7 |

### MODEL C — Due only at successful confirmation / payout

| | |
|---|---|
| Trigger | `/confirm` (current `* 0.95`) |
| Economic base | `escrow_amount` (current) |
| Reversibility | After confirm, only via new reverse (not built); dispute blocked once `released` |
| Payment failure | Never due |
| Cancellation before confirm | Never due |
| Refund | Dispute before release |
| Reuse | **Matches runtime** |
| Conflict with code | None for the trigger; base/`/escrow`/float still messy |
| Open questions | Unconfirmed completed work never yields 5%; confirm without payment yields 5% of 0 or of a fake marker |

### MODEL D — Existing documented siblings

| | |
|---|---|
| Trigger | Design phase complete; dispute resolve; demo split |
| Economic base | Phase price / escrow remainder |
| Meaning | Same numeric 95/5, **other products or exception paths** |
| Reuse | Pattern already copied |
| Conflict | Must not silently become the public Marketplace rule |
| Open questions | Keep copies aligned vs isolate |

---

# 16. Exact founder decision required (D8.17)

**D8 — READY FOR FOUNDER APPROVAL**

Proposed canonical rule (from repository evidence, not preference):

1. **What:** Marketplace job commission is a **5% withholding from the specialist payout**, not an extra client charge and not a separate specialist invoice line.  
2. **Base (runtime):** `requests.escrow_amount` (de facto). Founder must still name the **authoritative gross** if estimate ≠ paid ≠ `/escrow` ≠ 0.  
3. **Rate:** **5%**, currently hardcoded. Admin `platform_commission_pct` is **not** live.  
4. **When (runtime):** calculated, withheld, and settled together at **`/confirm`** (Model C in the unranked list). D6 does **not** make it due.  
5. **Separation:** Lead Credits ≠ apply fee ≠ HH 15/10/5 ≠ VE/ES/partner % ≠ D8.  
6. **Money:** DEMO checkout + internal wallet; **not** Stripe Connect.

**Still for the founder (not implied by code):**

| Question | Why open |
|---|---|
| Stay on Model C vs move to A/B | A/B contradict current code; moving needs D7 |
| Gross SSOT field | `escrow_amount` is last-write-wins and client-writable via `/escrow` |
| Explicit ledger row for 5% | Economically cleaner; not required to compute 0.95 |
| Wire `platform_commission_pct` | Dead knob vs hardcoded |
| Refund / cancel / no-show | Only dispute exists |
| D9 free jobs: is 5% still due? | D9 not implemented |
| D11: ever settle HH captured % as money? | Captured ≠ paid |

---

# 17. Open questions

1. Realization stay at confirm or move with D7 payment/escrow?  
2. Which existing amount is `gross_job_value`?  
3. Post `platform_commission` on `transactions` or keep implicit haircut?  
4. Close `/escrow` as a client-controlled payout base?  
5. Atomic confirm to prevent double wallet credit?  
6. Integer minor units vs current float?  
7. Align design/dispute copies when Marketplace rule is approved?  
8. D9 interaction.  
9. D11 HH captured amounts.  
10. D13 `/accept` must not become a second D8 event.

---

# 18. Impact map for later implementation

**No implementation authorized.**

If later authorized, **smallest change** (reuse, no new engine):

| Work | Needed to *define* D8? | Needed to *match* explicit gross/comm/net? |
|---|---|---|
| New commission engine | **No** | **No** |
| Change `/confirm` formula | **No** if 5% / specialist-borne stays | Only if rate/base/event changes |
| Insert `transactions.type=platform_commission` | No | If founder wants posted 5% |
| Snapshot rate on request | No | If admin % becomes live |
| Read `platform_commission_pct` | No | If founder retires hardcoded 0.95 |
| Enable Model B | **No** | Orthogonal |
| Move D2 credits | **No** | Orthogonal |
| Delete `/accept` | **No** | D13 |
| Stripe Connect | **No** | D7 production money |
| D9 quota | **No** | Separate |

---

# 19. Explicit statement

**No implementation performed.**

No application code, schema, migration, flag, UI, test, Stripe, price, `/accept`, commit, or deploy was changed.

---

# STATUS

**D8 — READY FOR FOUNDER APPROVAL**

Canonical evidenced rule: **5% specialist-borne payout haircut on `escrow_amount` at `/confirm`**, separate from Lead Credits, apply fees, and House Health 15/10/5.

Realization-move, gross SSOT, explicit ledger, and refund policy remain founder questions.

No implementation authorized.

**STOP.**
