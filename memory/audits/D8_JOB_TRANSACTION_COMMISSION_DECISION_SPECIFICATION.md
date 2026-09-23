# D8_JOB_TRANSACTION_COMMISSION_DECISION_SPECIFICATION

**Decision:** D8 — Job transaction commission = **5% of applicable job value, borne by the specialist**  
**Mode:** READ-ONLY. No implementation, flags, prices, credits, Stripe, commit, or deploy.  
**Given:** D1 = Model B · D2 = Lead Credits on `submit_offer` · D6 = selection/`assigned` is de facto relationship; pay/escrow/execution/payout remain distinct  
**Date:** 2026-09-22

**Founder economic direction (accepted as D8 intent, not as “already implemented”):**

```
CLIENT pays 100% GROSS JOB VALUE
PROPManage intermediates
SPECIALIST bears 5% commission
SPECIALIST receives 95% NET PAYOUT
```

Example: 10,000 RON gross → 500 RON platform → 9,500 RON specialist.  
**Client is not charged an extra 5%.**

Do **not** mix with: Lead Credits · HH `lead_commission_pct` · subscription price · 5–50 RON apply fee.

---

# 1. Current implementation (traced)

| | |
|---|---|
| File / symbol | `backend/routes/requests.py` `confirm_complete` |
| Route | `POST /api/requests/{req_id}/confirm` |
| Auth | `require_role("client")` + `client_id` match |
| Request state required | `status == "completed"` only |
| Payment / escrow required | **No** |
| Amount base | `amount = req.get("escrow_amount") or 0` |
| Calculation | `specialist_amount = amount * 0.95` |
| Rate source | **Hardcoded 0.95** — not `platform_commission_pct` |
| Wallet | `$inc` specialist `wallet_balance` by `specialist_amount` |
| Ledger | `transactions` `{type: job_payment, amount: specialist_amount}` — **net only** |
| Request after | `status=confirmed`, `escrow_status=released` |
| Also | +100 `users.tokens`; `jobs_completed++` |

**Same 0.95 shortcut:** `disputes.resolve_dispute` (`pay_specialist` / `split`); `design.py` quote share; `demo_time_machine.SPECIALIST_SPLIT`.

**Commission is implicit.** There is no `platform_commission` field, no 5% row, no 500 in the 10,000 example. Only net credit.

---

# 2. Who pays whom (code vs target)

| Concept | Target | Current code |
|---|---|---|
| **CLIENT PAYMENT** | Gross job value | Checkout: `budget_estimate` (default 100) → DEMO/`payment_transactions` + `escrow_amount`. **Or** `POST .../escrow?amount=` **client-supplied**, no debit. **Or** never pay (`escrow_amount` null → confirm pays **0**) |
| **SPECIALIST COMMISSION** | 5% of job value, specialist-borne | **Not a charge line.** Platform “keeps” by never crediting 5% to the specialist |
| **SPECIALIST NET PAYOUT** | 95% | `wallet_balance` + `job_payment` = `escrow_amount * 0.95` |

**Economic direction matches the founder story only when `escrow_amount` equals the true gross and was actually paid.** The **representation** does not: client is not shown “you pay 10,000”; specialist is not shown “commission 500”; ledger has no platform 500.

The 5% is **not** a second amount billed to the client **in this function**. Risk of extra client charge exists only if product/UI later adds 5% on top of gross — **forbidden by invariant 21**.

---

# 3. Commission base — which field wins

| Field | Role | Controls `/confirm`? |
|---|---|---|
| `requests.budget_estimate` | Client estimate at create; checkout amount source | **Indirect** if checkout ran (copied into `escrow_amount`) |
| `marketplace_offers.fee_paid_total` / `selected_offer_fee` | Specialist **apply** fee (5–50) | **No** |
| `payment_transactions.amount` | Checkout session amount | Written to `escrow_amount` on paid/DEMO |
| `requests.escrow_amount` | Marker / checkout copy / `/escrow` amount | **YES — sole confirm base** |
| `selected_offer` job price | **No job-price field on offer** (`fee_ron` is participation) | **No** |
| Confirmed amount | Not a separate field | Confirm **reads** `escrow_amount`, does not take a new body amount |

**Authoritative runtime job value today = `requests.escrow_amount`.**  
**Intended agreed value** is **not** a single SSOT: estimate vs checkout vs client `/escrow` vs unpaid 0.

Trace:

```
Offer        → apply fee only (not job value)
Selection    → selected_offer_id; no job amount write
Payment      → amount = budget_estimate → escrow_amount
Escrow POST  → amount = client query param → escrow_amount  (overrides)
Confirm      → payout = escrow_amount * 0.95
```

Do not invent a new pricing source. A later D8 implementation must **name** which existing field is `gross_job_value` — founder still must pick if estimate ≠ paid ≠ marker.

---

# 4. Gross / commission / net

| | Field | Calc | Tx | API | UI | Persist | SSOT |
|---|---|---|---|---|---|---|---|
| **A. GROSS** | `escrow_amount` (de facto) | none | `escrow_deposit` (DEMO/live) may record client-side amount | checkout uses budget | timelines show escrow | `requests.escrow_amount` | **Ambiguous** |
| **B. COMMISSION** | **none** | implicit `amount - amount*0.95` | **none** | **none** | Legal/docs “5%” | **none** | Hardcoded 5% |
| **C. NET** | computed local `specialist_amount` | `* 0.95` | `job_payment` | confirm `{tokens_earned}` — **not** net amount in the return snippet | “Plată eliberată {specialist_amount}” notify | wallet + tx | Runtime calc |

**Commission is currently implicit rather than explicitly represented.**

**Future requirement (specify only):** persist or ledger-record three named values at realization:

`gross_job_value` → `platform_commission` (5%) → `specialist_net_payout`  
Reuse `requests` + `transactions`. No new engine. **Do not implement now.**

---

# 5. Possible realization events (no rank)

| Option | Repo support | Calc? | Money withheld? | Wallet net? | Commission tx? | Cancel / refund |
|---|---|---|---|---|---|---|
| **A. Select offer** | `accept_offer` — no 0.95 | No | No | No | No | Too early; D2 already charged participation |
| **B. Payment success** | Checkout/DEMO — no 0.95 | No | DEMO marks paid; no split | No | No | Pay can precede select (`open`) |
| **C. Escrow held** | Marker; `/escrow` no debit | No | Marker ≠ custody | No | No | Client can set held without pay |
| **D. Work start** | `/start` — no money | No | No | No | No | Unpaid start allowed |
| **E. Client confirms** | **`confirm_complete`** | **Yes** | Implicit (never credit 5%) | **Yes** `*0.95` | **No** explicit | If never confirm, 5% never “taken” |
| **F. Payout** | **Same function as E** | Same | Same | Same | Same | Payout **is** confirm in this repo |

**Current realization = E and F are one function.** Calculation and wallet net happen **together** at confirm. Nothing is withheld at pay/held.

Founder still must say whether realization **stays at confirm** or moves earlier (needs D7). This spec does **not** choose.

---

# 6. Calculation vs realization

| | Current |
|---|---|
| **CALCULATION** | Only at confirm/dispute/design: `* 0.95`. No stored quote of 5% at select/pay |
| **REALIZATION** | Same moment as calculation: specialist wallet += net. Platform share is the **omitted** 5% — not posted |

They **coincide** today. They **may** split later (e.g. calculate at pay, realize at confirm) — **not decided**.

---

# 7. D6 sequence (do not reopen)

```
Relationship (D6 de facto)  = assigned / accept_offer
Payment                     = checkout / DEMO
Escrow                      = internal held marker
Execution                   = /start
Confirmation                = /confirm
Payout                      = same /confirm
Commission realization      = same /confirm   ← D8 attaches HERE today
```

None of these may be collapsed in language. D8 must not debit Lead Credits or HH %.

---

# 8. Stripe / escrow reality

| Fact | Evidence |
|---|---|
| Target Stripe | DEMO (`/api/health` `stripe=demo`) |
| Real Stripe money | **Not** on this process |
| `payment_transactions` | DEMO insert paid; live on Checkout create + webhook/poll |
| `escrow_deposit` tx | DEMO/live checkout path; **not** on `place_escrow` |
| `escrow_status=held` | **Internal marker** |
| Specialist payout | **Internal wallet**, not Stripe Connect / Stripe Payout |

Do not call wallet credit a real Stripe payout. Do not design Connect here.

---

# 9. Target economics vs `amount * 0.95`

Target: 10,000 gross → 500 platform → 9,500 net.

Today: if `escrow_amount=10000`, wallet += 9500, **500 never written**.  
That is an **implementation shortcut / implicit representation**, not the explicit model.

---

# 10. Ledger

| Type | Records |
|---|---|
| `escrow_deposit` | Client-side amount (checkout); often `demo: true` |
| `job_payment` | Specialist **net** |
| `dispute_refund` / `dispute_payment` | Split; spec side still `*0.95` |
| `lead_credit` / `lead_fee` | A participation — **not** job 5% |
| `marketplace_offer_fee` | B apply 5–50 — **not** job 5% |
| **platform commission** | **NOT FOUND** |

Existing `transactions` **can** represent the split later (`platform_commission` + `job_payment`) without a new engine. **Not implemented.**

Admin GMV uses `escrow_amount` on confirmed; `platform_revenue_fees = gmv * 0.05` is **analytics**, not a ledger post (`admin.py`).

---

# 11. Admin configuration

| Config | Exists | Consumed by `/confirm`? |
|---|---|---|
| `platform_config.platform_commission_pct` default 5.0 | **Yes** (`admin_console.py`, `AdminPlatformTools.jsx`) | **No** — dead for job confirm |
| `fee_configs` | B flag / apply min-max / ranking | **No** job 5% |
| `app_settings.pricing.commission_pct` | VE sales | **VE only** |
| `hh_plans.lead_commission_pct` | 15/10/5 | HH publish + B capture — **not** confirm |
| Env | no job-commission env on this path | — |
| Hardcoded `0.95` | **Yes** | **Yes — runtime SSOT** |

Verified: admin can store 7.5% (`test_admin_console`); confirm still uses 0.95.

---

# 12. House Health — keep separate

`lead_commission_pct` 15/10/5: attribution on **apply fee** at `accept_offer`; status `captured`; never `/confirm`.  
**No runtime connection** to `amount * 0.95`. Premium UI “5%” is **numeric collision**, not this calculator. **D11 stays open.**

---

# 13. Lead Credits — keep separate

Credits: `accept_request` today; D2 = `submit_offer`.  
`confirm_complete` does not read `lead_credits`. **No accidental coupling.**

---

# 14. Offer fee ≠ job commission

| | Participation (D2 / legacy) | Job commission (D8) |
|---|---|---|
| Event | `submit_offer` | `/confirm` today |
| Amount | 45 credits or 5–50 RON apply | 5% of `escrow_amount` |
| Payer | Specialist | Specialist (implicit) |
| Ledger | `lead_credit` / `lead_fee` / `marketplace_offer_fee` | `job_payment` net only |

**Not the same event.** D2 will reconcile 5–50 vs credits; that does **not** implement D8.

---

# 15. Cancel / refund matrix (current)

| Scenario | 5% charged? | Calculated? | Retained? | Reversible? | Spec wallet? | Client money? | Explicit 5%? |
|---|---|---|---|---|---|---|---|
| 1. Select, no pay | No | No | No | n/a | No | None taken (unless `/escrow` marker) | No |
| 2. Payment fails | No | No | No | n/a | No | Unpaid | No |
| 3. Payment succeeds (DEMO) | Not yet | No | Marker only | n/a | No | DEMO record | No |
| 4. Escrow held | Not yet | No | Marker | n/a | No | `/escrow` = no debit | No |
| 5. Start | No | No | No | n/a | No | — | No |
| 6. Complete | No | No | No | n/a | No | — | No |
| 7. Confirm | **Implicit** | Yes `*0.95` | By omission | Only via later dispute | **Yes net** | Not returned | **No** |
| 8. Client cancel | **No first-class job cancel** | — | — | — | — | — | — |
| 9. Specialist cancel | **No first-class** | — | — | — | — | — | — |
| 10. Refund | Dispute `refund_client` → full `escrow_amount` to client wallet | 5% not taken | n/a | Admin | 0 | Internal wallet credit | No |
| 11. Partial | Dispute `split` | 5% on **specialist remainder** | Implicit | Admin | Net of remainder | Client slice to wallet | No |
| 12. Dispute | Implemented | Same 0.95 | Implicit | Admin resolve | `dispute_payment` | `dispute_refund` | No |
| 13. No confirmation | Never | No | No | n/a | No | Stuck as held marker / DEMO paid | No |

Do not invent a generic refund API — it is **not** there.

---

# 16. Security (report only)

| Control | Can it change 5% or net? |
|---|---|
| Client confirm | Cannot pass a rate; **can** have set `escrow_amount` via `/escrow?amount=` | **Authorization gap** — client-controlled **base** |
| Client checkout | Amount from **server** `budget_estimate` | Client can set estimate at **create** |
| Specialist offer | `fee_ron` is apply fee, not confirm base | Does **not** set job 5% |
| Request/profile PATCH | No commission fields on profile | — |
| Wallet | Specialist cannot self-credit job 5% | Confirm/dispute/admin |
| Admin settings | Writes `platform_commission_pct` | **Does not** change confirm (dead) — **false sense of control** |
| Direct `escrow_amount` | Only if some other writer; confirm trusts stored value | Tamper of that field = tamper of net |

No client/specialist API sets the **rate**. The **base** is the gap.

---

# 17. Legacy reconciliation (later)

| Mechanism | Economic role | Model | Behavior | Later | Reason |
|---|---|---|---|---|---|
| Hardcoded `0.95` at `/confirm` | Job commission realization | Job | ENFORCED implicit | **MODIFY** (explicit gross/comm/net; maybe read config) | Founder 5% + explicit ledger |
| `platform_commission_pct` | Intended rate SSOT | Job | Dead | **DECISION REQUIRED** | Wire vs keep hardcoded |
| `fee_configs` | B apply / flag | Lead | Not job 5% | **KEEP** off D8 | Different economy |
| `hh_plans.lead_commission_pct` | HH attribution | HH | Capture not pay | **KEEP** | D11 |
| Lead Credits | Participation | Lead | `/accept` now; D2 submit | **KEEP** separate | D2 |
| 5–50 apply fee | Legacy participation | Lead | Wallet on submit | **DECISION REQUIRED** (D2) | ≠ job 5% |
| Wallet `job_payment` | Net payout | Job | Internal | **KEEP** | Not Stripe payout |
| `transactions` | Ledger | All | Can add commission type | **KEEP** / **MODIFY** | No new engine |
| Escrow marker | Not custody | Pay | `held` | **KEEP** as marker until D7 | ≠ commission |
| `payment_transactions` | Client pay record | Pay | DEMO/live | **KEEP** | Gross candidate |
| Disputes `*0.95` | Same implicit 5% | Job | ENFORCED | **MODIFY** with confirm | Consistency |
| Design `*0.95` | Other product | Design | Separate | **INTERNAL-ONLY** / keep split | Not marketplace job |
| Admin `gmv*0.05` | Analytics | Job | Estimate | **KEEP** as report | Not realization |

---

# 18. Dependency map

| | Relation to D8 |
|---|---|
| **D1** | Same 5% on B jobs; confirm already path-agnostic if `escrow_amount` set |
| **D2** | Must not realize 5% at `submit_offer` |
| **D6** | Relationship ≠ commission; attach realization **after** pair exists (today: confirm) |
| **D7** | If realization moves to pay/held, needs real vs DEMO / marker rules — **not designed here** |
| **D9** | Free client jobs: is 5% still due? **Open** |
| **D11** | HH 15/10/5 ≠ this 5% |
| **D13** | `/accept` must not become a second job-commission event |

---

# 19. Target economic invariants

1. Client sees agreed **gross** job value.  
2. Client pays **gross** through marketplace payment (when payment exists).  
3. Specialist **bears** 5% PropManage job commission.  
4. Specialist receives **net** after that commission.  
5. `gross_job_value` ≠ `platform_commission`.  
6. `platform_commission` ≠ `specialist_net_payout`.  
7. Three values must not stay one ambiguous `amount * 0.95` in the **target** model (current code **is** that ambiguity).  
8. ≠ Lead Credits.  
9. ≠ HH lead attribution.  
10. ≠ offer participation cost.  
11. Not charged twice.  
12. Not charged because an offer exists.  
13. Not charged because a Lead Credit was consumed.  
14. Corresponds to an actual job transaction.  
15. Calculation ≠ realization (must be distinguishable).  
16. Realization trigger defined **before** production payment architecture.  
17. Refund/cancel treatment defined **before** production payment architecture.  
18. One authoritative job-value base.  
19. No client-controlled field authorizes/alters the **rate**; client `/escrow` amount must not remain an unchecked **base**.  
20. No specialist-controlled field alters the **rate**.  
21. Client must not be charged an **additional** 5% on top of gross.

---

# 20. Critical question

**Can PropManage evolve from `specialist_payout = amount * 0.95` to explicit `gross → 5% → net` while reusing request, offer, payment, escrow, and transactions?**

**Yes.** There is **no missing box**.

**Reuse:** `requests` (`escrow_amount` as *current* base until SSOT named), `confirm_complete` / disputes as realization points, `transactions` for a future explicit commission row + existing `job_payment` net, `payment_transactions` as client gross record, wallet as internal net payout, admin `%` as optional later SSOT.

**Not a new engine.**

**Precise blockers (decision/quality, not “build a system”):**

1. **Base ambiguity:** `budget_estimate` vs checkout vs client `/escrow` vs 0.  
2. **Commission not posted** — analytics invent 5%.  
3. **Realization = confirm only** — unpaid/unconfirmed jobs never realize 5% (may be intended).  
4. **DEMO / marker ≠ money** — cannot treat omission of 5% as cash retained until D7.  
5. **`/escrow` amount** is client-controlled.

None of these require a new commission product.

---

# 21. FINAL D8 DECISION PACKAGE

### D8 — CURRENT EVIDENCE

`/confirm` credits the specialist **`escrow_amount * 0.95`** in the **internal wallet**, logs **`job_payment` net only**, and never writes 5%. Rate is **hardcoded**. Admin `platform_commission_pct` is **unused**. HH 15/10/5 and Lead Credits are **disconnected**. Stripe on target is **DEMO**. Held is an **internal marker**.

### D8 — FOUNDER DECISION (economic — established)

> PropManage charges the **specialist** a **5%** commission on the **applicable job transaction value**.  
> The **client pays the gross** job value.  
> The specialist receives the **net** after that commission.

**Still for the founder (not chosen here):**

| Question | Why it is not implied |
|---|---|
| **Realization trigger** | Today = confirm. Moving to pay/held/start is D7+D8, not automatic |
| **Authoritative gross base** | Estimate vs paid vs marker |
| **Refund/cancel** | Only dispute paths exist; no job-cancel |
| **Explicit ledger row for 5%** | Economically yes for audit; not required to *compute* 0.95 |
| **Payment/escrow dependency** | Confirm does not require held/paid |
| **Payout dependency** | Payout **is** confirm today |

### D8 — ARCHITECTURAL INVARIANTS

Section 19, plus: do not implement Connect; do not merge HH % or credits; do not add 5% on the client invoice; one public job-commission event.

### D8 — IMPLEMENTATION BLOCKERS

- Founder answers on **realization trigger** and **gross SSOT** (and `/escrow` base) before production money.  
- D7 if realization is claimed to be “real withheld funds.”  
- Explicit gross/comm/net **representation** if the founder requires it in ledger/API (code can stay 0.95 until then).

### D8 — NON-BLOCKERS

- Enabling Model B flag  
- Implementing D2 debit move  
- D13 residual `/accept`  
- D9  
- D11  
- Premium 79 vs 249  
- Wiring `platform_commission_pct` (optional after SSOT)  
- New collections / engines  
- Changing the **5** to another percent

### STATUS

**DECISION SPECIFICATION — READY FOR FOUNDER APPROVAL**

Economic rule (5%, specialist-borne, client pays gross) is specified.  
Realization trigger, job-value SSOT, explicit ledger, and refund policy are **open**.  
**No implementation authorized.**

---

**STOP.** File: `memory/audits/D8_JOB_TRANSACTION_COMMISSION_DECISION_SPECIFICATION.md`
