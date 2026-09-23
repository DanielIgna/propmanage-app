# D7_PAYMENT_ESCROW_DECISION_SPECIFICATION

**Decision:** D7 — Payment and escrow architecture for Marketplace (including whether a **project** can be a **sequence of commercial stages**)  
**Mode:** READ-ONLY. No implementation, Stripe, prices, flags, commit, or deploy.  
**Given:** D1 = Model B · D2 = Lead Credits on `submit_offer` · D6 = selection/`assigned` is de facto relationship · D8 = client pays **gross**, specialist bears **5%**, net 95% (realization trigger still open)  
**Date:** 2026-09-22

Target conceptual model (specify only):

```
PROJECT → COMMERCIAL STAGE → INSTALLMENT/PAYMENT → ESCROW → WORK → CONFIRM → PAYOUT
```

Do **not** treat this as implemented.

---

# 1. Current Marketplace payment graph

Canonical **job** spine (not design, not DT, not partner CRM):

```
CLIENT
  → POST /api/payments/checkout-session          payments.create_checkout_session
       amount = budget_estimate (default 100)
       eligible request status: open | assigned
  → payment_transactions  (DEMO: paid immediately; live: initiated then poll/webhook)
  → transactions type=escrow_deposit             (checkout paths only)
  → requests.escrow_amount / escrow_status=held / paid_at
  → POST /api/requests/{id}/start                start_work   (NOT gated on held)
  → POST /api/requests/{id}/complete             complete_work
  → POST /api/requests/{id}/confirm              confirm_complete
       wallet += escrow_amount * 0.95
       transactions type=job_payment
       status=confirmed, escrow_status=released
```

| Step | File / symbol | Route | Auth | Persist |
|---|---|---|---|---|
| Checkout | `backend/routes/payments.py` `create_checkout_session` | `POST /api/payments/checkout-session` | client + `client_id` | `payment_transactions`; on DEMO also `escrow_*` + `escrow_deposit` |
| Status poll | `payment_status` | `GET /api/payments/status/{session_id}` | authenticated | may set held on live paid |
| Webhook | `stripe_webhook` | `POST /api/webhook/stripe` | Stripe sig / DEMO no-op | same held write; also HH activate |
| Marker escrow | `requests.place_escrow` | `POST /api/requests/{id}/escrow?amount=` | client owner | `escrow_amount`, `held` — **no** `payment_transactions`, **no** wallet debit |
| Start / complete | `start_work` / `complete_work` | `.../start` `.../complete` | assigned specialist (`specialist_id`) | `in_progress` / `completed` |
| Confirm / “payout” | `confirm_complete` | `.../confirm` | client owner + `completed` | wallet + `job_payment` |

---

# 2. Stripe reality (no secrets)

| | |
|---|---|
| Env | `STRIPE_API_KEY` via `backend/.env` / process env |
| Decision | `payments.py`: `DEMO_STRIPE = (key == "sk_test_emergent") or (not key.startswith(("sk_test_","sk_live_")))` |
| Target process | `GET /api/health` → `checks.stripe = "demo"` (2026-09-22) |
| **Job checkout on this process** | **Does not call Stripe.** DEMO inserts fake `cs_demo_*`, marks paid, sets held |
| Live path (if real `sk_test_`/`sk_live_`) | `StripeCheckout.create_checkout_session`; webhook/poll fulfill |
| HH billing | **No** DEMO short-circuit; missing key → 503 (separate stack) |
| Connect / custody | **NOT FOUND** |

**Terminology:** current job payment is an **internal DEMO payment + internal escrow marker**, not a Stripe charge and not Connect escrow.

---

# 3. What `escrow_status=held` means

**Internal escrow marker.**

| Writer | Payment required? | Amount | External money? |
|---|---|---|---|
| DEMO checkout | Simulated “paid” in same function | `budget_estimate` | **No** |
| Live checkout fulfill | After Stripe paid | `payment.amount` | Stripe session (if live key) |
| `place_escrow` | **No** | **Client query `amount`** | **No** |

- Work **not** blocked until held (`/start` ignores escrow).  
- Client **can** set held without paying.  
- Specialist **cannot** set held.  
- Held **can exist without payment**.

Not real custody.

---

# 4. Amount fields

| Field | Writer | Reader | API | Meaning |
|---|---|---|---|---|
| `requests.budget_estimate` | `create_request` / HH publish | checkout | create body | Estimate — **checkout base** |
| `marketplace_offers.fee_ron` / `fee_paid_total` | `submit_offer` | ranking, `selected_offer_fee` | offer body 5–50 | **Participation**, not job value |
| `requests.selected_offer_fee` | `accept_offer` | unused by confirm | — | Copy of apply fee |
| `payment_transactions.amount` | checkout | fulfill → escrow | server-side | Session gross |
| `requests.escrow_amount` | checkout **or** `/escrow` | **`/confirm` `* 0.95`** | — | **Runtime job base** (D8) |
| `design` `phases[].price` | design quote | design pay/complete | design routes | **Design stage** price — not marketplace confirm |

**Conflicts:** estimate ≠ apply fee ≠ client `/escrow` amount ≠ unpaid `null` (confirm pays 0).  
**No new SSOT chosen here** — D8 already left “which field is gross” open.

---

# 5. Project vs job vs stage vs installment

| Concept | In repo? | Marketplace-connected? |
|---|---|---|
| **Property** | `properties` | Request `property_id` ENFORCED |
| **JOB / REQUEST** | `requests` | **Yes** — one `status`, one `escrow_amount`, one confirm |
| **COMMERCIAL STAGE** | `requests.phases[]` | **Design product only** (`design.py`) — pay/complete per phase, 95/5 |
| **INSTALLMENT** | Multiple `payment_transactions` **can** exist | Marketplace **runtime** overwrites a **single** `escrow_amount`; confirm does not sum rows |
| **PROJECT (interior/demo)** | `db.projects` + `milestones[]` | `demo_time_machine` **sim-**fund/release — **not** `payments.create_checkout_session` |
| **PROJECT (Digital Twin)** | `digital_twin_projects` | Container / models — **not** job money |
| **CRM “stage”** | ops/partner leads | Pipeline, **not** escrow |

`requests.py` has **no** `parent_`, `project_id`, or marketplace `phases`.

**Can `request` represent one commercial stage?** **Yes, as a document shape** (one relationship + one money cycle). The repo does **not** currently **link** N requests into one evolving project, and does **not** run marketplace checkout per design-style phase.

---

# 6. Target model vs existing

```
PROJECT
  STAGE 1 → amount → pay → escrow → work → confirm → payout
  STAGE 2 → …
```

| | Status | Reuse |
|---|---|---|
| **A. Exists** | One-shot request money cycle; design `phases[]` on a request; demo `projects.milestones`; DT project; `transactions` / `payment_transactions` collections (multi-row capable) | Job cycle + ledgers + (pattern) design phases |
| **B. Partial** | Design phases = staged pay/payout **off** the marketplace `/confirm` path; multiple payment rows **without** multi-escrow semantics |
| **C. Missing** | Marketplace parent project; installment vs remaining; advance as first-class; per-stage escrow; gate work on held; explicit gross/comm/net (D8); wallet withdrawal |
| **D. Reuse** | `requests` as **one stage**; `property_id` + `specialist_id` as implicit project key; `payment_transactions` as installment **records**; design `phases` as a **sibling pattern** (not auto-adopt) |
| **E. Would need change** | If one request must hold N marketplace installments: `escrow_amount` last-write-wins and single `/confirm` **cannot** without **MODIFY**. If N requests = N stages: **link field** is the gap — not a new payment engine |

**Do not create** a new project/billing/escrow engine by default.

---

# 7. Payment vs escrow vs later events

| Event | Intended | Current Marketplace code |
|---|---|---|
| **PAYMENT** | Client paid | DEMO fake paid **or** Stripe if live; `/escrow` ≠ payment |
| **ESCROW** | Held for the stage | **Internal marker** `held` |
| **EXECUTION AUTH** | May start | `specialist_id` + notify at select; `/start` ungated |
| **CONFIRMATION** | Client accepts work | `/confirm` requires `completed` |
| **PAYOUT** | Net entitlement | Same `/confirm` → **internal wallet** |

---

# 8. Lifecycle marks

| # | Event | Status |
|---|---|---|
| 1 | Stage proposal | **PARTIAL** — B offer is **participation** (D2), not a job-price proposal; design quotes are stage prices |
| 2 | Client accepts stage | **EXISTING** as D6 `accept_offer` (pair), not “accept amount” |
| 3 | Payment initiated | **EXISTING** checkout (also on `open`) |
| 4 | Payment succeeds | **PARTIAL** DEMO / live |
| 5 | Escrow held | **EXISTING** marker; **DISCONNECTED** from real money on `/escrow` |
| 6 | Work authorized | **IMPLICIT** at assignment |
| 7–8 | Start / complete | **EXISTING** |
| 9 | Client confirms | **EXISTING** |
| 10 | Commission calculated | **IMPLICIT** `*0.95` at confirm (D8) |
| 11 | Payout released | **EXISTING** wallet — same function |
| 12 | Review | **EXISTING** (needs `specialist_id` only) |

---

# 9. Partial / advance / multiple — **runtime**

| Capability | Runtime? | Evidence |
|---|---|---|
| Full payment of checkout amount | DEMO/live one session | One `budget_estimate` |
| Advance / partial of a larger agreed total | **No** marketplace rule | No remaining-balance field |
| Multiple payments | Rows **can** insert | Confirm uses **one** `escrow_amount` (last writer) |
| Multiple escrow deposits | Marker overwritten | Single field |
| Multiple confirmations | **No** — `confirmed` is terminal on that request | One `/confirm` |
| Staged payout | **Design `phases`** yes; marketplace `/confirm` **once** | `design_phase_payout` vs `job_payment` |

**Do not equate “collection can store many documents” with “marketplace supports installments.”**

---

# 10. Commission × payment (D8 not finalized)

Per **paid installment**, D8 math **can** apply: gross_i × 5% → net_i, using existing `* 0.95` **if** each installment has its own realization event and base.

Today: **one** `escrow_amount` × 0.95 at **one** confirm.  
Design: **each** `phases[].price` × 0.95 at **phase-complete**.

**Lead Credits ≠ job commission ≠ HH `lead_commission_pct`.** Unchanged.

---

# 11–12. Refund / failure (actual)

| Scenario | Current |
|---|---|
| Select, never pay | `assigned`; work allowed; confirm net **0** if no `escrow_amount` |
| Payment fails | Live unpaid; DEMO typically succeeds; `assigned` unchanged |
| Pay succeeds, no held | Unusual on DEMO (same fn); `/escrow` can held without pay |
| Held, no start | Stays `assigned`; dispute if assigned+ |
| Start, client cancel | **No** first-class job-cancel route |
| Complete, no confirm | No `job_payment` |
| Confirm | Net wallet; implicit 5% |
| Refund / partial | **Disputes only** (`refund_client` / `split` / `pay_specialist` + 0.95 on spec slice) — **internal wallet**, not Stripe refund |
| Offer withdraw | Apply fee kept (D2 commercial loss) |
| Next stage | **No** marketplace “create next stage” — client can **create another request** on the same property |

**Policies still required for staged jobs:** advance vs remaining; commission on paid vs committed; cancel mid-stage; who may open Stage N.

---

# 13. Security / authorization

| Action | Who |
|---|---|
| Checkout | Client owner; amount **server** `budget_estimate` |
| `/escrow` | Client owner; amount **client-controlled** |
| Change held | Checkout/webhook/system or client `/escrow` |
| Confirm / trigger payout | Client owner (if `completed`) |
| Alter net | Implicit 0.95; specialist cannot set rate |
| Request status start/complete | Specialist with `specialist_id` |
| Admin | Auto-match assign; dispute resolve; demo milestone sim |

**Trust boundary:** `/escrow` manufactures held + confirm base without payment. Checkout on `open` pays **before** a specialist is chosen.

---

# 14. Wallet reality

| | |
|---|---|
| Credited | `/confirm` `job_payment`; disputes; design phase payout; topup |
| Amount | Net `* 0.95` (job/design) or topup face value |
| What it is | **`users.wallet_balance` internal accounting** |
| Withdrawal / Stripe payout | **NOT FOUND** on wallet routes (list + topup + Stripe topup checkout only) |
| Topup | `POST /wallet/topup` **direct `$inc`** (no Stripe) **and** Stripe/DEMO topup session |

Not a real payout rail.

---

# 15. Ledgers

| Store | Typical types | Collapsed? |
|---|---|---|
| `payment_transactions` | Checkout session (job or HH) | One session ≠ installment plan |
| `transactions` | `escrow_deposit`, `job_payment`, `lead_*`, `marketplace_offer_fee`, `dispute_*`, `design_phase_*`, `topup` | **No** `platform_commission` row (D8) |
| `/escrow` | **No** ledger row | Marker-only |

Client pay, marker, commission, and net are **not** four clean posts on the marketplace path.

---

# 16. Multi-stage compatibility test (architecture only)

Example: Stage1 1000 → 50/950; Stage2 5000 with 1500 advance; Stage3 remainder.

| Need | Existing structure | Marketplace runtime |
|---|---|---|
| Three commercial units | Three `requests` **or** three `phases[]` | **One** request = **one** confirm |
| 1500 advance on 5000 | A checkout/tx of 1500 | No “remaining 3500” field |
| Commission per paid amount | `* 0.95` on **that** base | Would work **per confirm/phase-complete** if each unit is separate |
| Separate escrow per stage | Separate `escrow_amount` **per request** or per `phases[]` | Single field on one request |

**Possible without a new engine:** Stage = **request** (or **design-like phase**). Advance = **a payment row whose amount < agreed** — **agreed total is not stored** on marketplace requests today.

---

# 17. No premature engines

**Already enough to start (smallest gap, not a build list):**

- `requests` + `offers` + `payment_transactions` + `transactions` + wallet  
- Design `phases` as **evidence** that staged pay/payout **already exists** on `requests` in another product  
- `property_id` + `specialist_id` to group stages **informally**

**Smallest architectural gap:** Marketplace has **one money cycle per request** (`escrow_amount` + one `/confirm`) and **no parent link**. That is a **composition/linking** gap, not a missing Stripe/wallet/escrow product.

Do **not** build a new payment, escrow, wallet, project, or billing engine to express D7.

---

# 18. Legacy reconciliation (later)

| Mechanism | Current role | Target role | Later | Reason |
|---|---|---|---|---|
| Checkout | DEMO or Stripe session; amount = estimate | Client **gross** for a **stage/installment** | **KEEP** / **MODIFY** eligibility (`assigned` only if D6/D7 require) | Exists |
| `payment_transactions` | Session record | Installment record | **KEEP** | Can be many rows |
| `escrow_deposit` | Checkout ledger | Optional client-pay line | **KEEP** | Missing on `/escrow` |
| `escrow_status` | Internal marker | Per-stage held | **KEEP** as marker until real custody | Not Connect |
| `POST .../escrow` | Client-set held + base | Unsafe as money | **DEPRECATE** or bind to a payment | Trust gap |
| `/confirm` | One-shot net payout | Per-stage realization (D8) | **KEEP** per stage unit | Don’t merge with credits |
| Wallet | Internal net | Internal until withdraw exists | **KEEP** | Not Stripe payout |
| `transactions` | Mixed types | Per-event lines | **KEEP** | Add commission later (D8) |
| `budget_estimate` | Checkout base | Estimate only | **DECISION REQUIRED** | vs paid vs marker |
| Offer `fee_ron` | Participation | Stay D2 | **KEEP** off D7 | ≠ job value |
| `requests.phases` | **Design** stages | Pattern for marketplace stages **or** stay design-only | **DECISION REQUIRED** | Do not silently reuse |
| `projects.milestones` | Demo/interior sim | **Not** marketplace checkout | **INTERNAL-ONLY** | Disconnected |
| DT projects | Twin | Not money | **KEEP** separate | — |

---

# 19. Dependencies

| | |
|---|---|
| **D1** | Checkout/confirm already path-agnostic if `assigned` + amount set |
| **D2** | Pay/escrow must **not** consume credits |
| **D6** | Pay-on-`open` vs relationship-first |
| **D8** | Gross/comm/net per installment; realization still open |
| **D9** | Is a “free experience” a stage, a request, or a waived payment? |
| **D11** | HH checkout is a **second** Stripe stack (no DEMO) |
| **D13** | `/accept` must not invent a second pay path |

---

# 20. Critical questions (factual)

1. **Sequence of stages without a new project engine?** **Yes** — N `requests` on the same `property_id` (and specialist), **or** reuse design `phases` **if** founder adopts that pattern. Missing is **explicit grouping**, not a project product.  
2. **One request = one commercial stage?** **Yes** (current marketplace semantics).  
3. **Multiple payments against one relationship?** **Records:** yes. **Runtime:** no — last `escrow_amount` + one confirm.  
4. **Escrow per payment/stage?** Per **request** or per **design phase**, yes. Per installment **on one request**, no.  
5. **Commission per paid installment?** **Mathematically** yes (`* 0.95` on that base). **Operationally** only if each installment has its own confirm/phase-complete.  
6. **Gross / commission / net split?** **Not explicit** (D8). Same shortcut can apply **per** unit.  
7. **Refunds vs correct payment/commission?** Only **dispute** wallet moves; **no** Stripe refund; **no** installment pointer.  
8. **Smallest gap?** Link/compose stages + stop treating one `escrow_amount` as a running total; fix `/escrow` as money; decide work-gated-on-pay. **Not** a new engine.

---

# 21. FINAL D7 DECISION PACKAGE

### D7 — CURRENT EVIDENCE

Job checkout on the target process is **DEMO**: fake session, `payment_transactions` paid, `escrow_status=held` **internal marker**. `/escrow` sets the same marker **without payment**. `/start` is **not** payment-gated. `/confirm` pays **internal wallet** `escrow_amount * 0.95` once. No wallet withdrawal. Design `requests.phases` already does **multi pay/payout** for **interior design**, disconnected from this checkout. `projects.milestones` is **demo/sim**.

### D7 — TARGET COMMERCIAL MODEL (entities only)

```
PROJECT     = property (+ specialist pair) grouping   [EXISTING keys; no parent collection required]
STAGE       = one `request`  (or, if chosen later, one design-like phase)
PAYMENT     = `payment_transactions` row (+ checkout)
ESCROW      = per-stage `escrow_status` marker until real custody exists
EXECUTION   = /start
CONFIRM     = /confirm (or phase-complete)
COMMISSION  = D8 5% on that stage’s gross (implicit today)
PAYOUT      = wallet `job_payment` (internal)
```

No new engines.

### D7 — FOUNDER DECISIONS REQUIRED

1. Must **payment** (not the marker) precede **work**?  
2. Is **escrow marker** mandatory, or only real payment?  
3. Is every **stage** a **new request**, or phases **on** one request?  
4. Advances / partials: allowed? Commission on **paid** or **committed**?  
5. Refund / cancel mid-stage (beyond disputes)?  
6. D8 realization: still **confirm**, or at **payment**?  
7. May checkout remain available on `open` (pay before specialist)?

### D7 — ARCHITECTURAL INVARIANTS

Payment ≠ escrow ≠ execution ≠ confirmation ≠ payout.  
Gross ≠ commission ≠ net.  
Lead Credits ≠ job commission.  
Client payment record ≠ specialist `wallet_balance`.  
One payment must not double-payout; one stage must not double-commission.  
A payment must point at **one** stage.  
No client-controlled field (`/escrow` amount) may create a payout.  
DEMO / held ≠ Connect custody.  
Do not build a second Marketplace payment engine.

### D7 — IMPLEMENTATION BLOCKERS

- Founder answers above **before** production money or multi-stage product.  
- `/escrow` as payout base if left client-arbitrary.  
- Claiming “real escrow” while DEMO + marker.  
- Treating design `phases` as marketplace without an explicit adopt/reject.

### D7 — NON-BLOCKERS

- Stripe Connect  
- Wallet withdrawal rail  
- Implementing D2/D1 flags  
- D9 / D11 / D13  
- Changing 5%  
- New project/billing collections  
- Premium 79 vs 249

### STATUS

**DECISION SPECIFICATION — READY FOR FOUNDER APPROVAL**

No implementation authorized.

---

**STOP.** File: `memory/audits/D7_PAYMENT_ESCROW_DECISION_SPECIFICATION.md`
