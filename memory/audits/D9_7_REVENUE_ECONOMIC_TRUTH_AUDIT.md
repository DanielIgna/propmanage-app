# D9.7 — REVENUE & ECONOMIC TRUTH AUDIT

**Mode:** READ-ONLY. No formula, dashboard, DB, pricing, Marketplace, or Stripe changes. No new SSOT or engine. No commit/deploy.  
**Date:** 2026-09-23  
**Environment inspected:** local `backend/.env` → Mongo `propmanage_db` (ping OK).  
**Stripe key class:** `demo_placeholder` (not `sk_test_` / `sk_live_`).  
**Generated at:** 2026-09-23T12:43:39Z  

**No implementation performed.**  
PII not listed. Amounts below are **database facts**, not invented estimates.

**Stripe cash in this environment: not evidenced.** DEMO placeholder cannot produce live charges.

---

# Environment snapshot

| Item | Value |
|---|---|
| DB | `propmanage_db` |
| Stripe mode | **DEMO placeholder** |
| `hh_plans.premium.price_eur` | **249.0** (not seed 79) |
| `hh_plans.basic` / `pro` | 9 / 29 EUR |
| `hh_subscriptions` | **0 documents** |
| `marketplace_offers` | **0 documents** |
| `manual_payments` / `wallets` collection | **absent** |
| Wallet SSOT | `users.wallet_balance` |
| Lead Credits SSOT | `users.lead_credits` |

---

# 1. payment_transactions

**Source:** `db.payment_transactions`  
**Date range:** 2026-05-23 → 2026-09-07  
**Currency mix:** RON (9) + EUR (5)

| Class | COUNT | TOTAL VALUE | CURRENCY | REAL? |
|---|---|---|---|---|
| All | 14 | 2365.00 | mixed | — |
| `payment_status=paid` | 9 | 2300.00 | RON | **DEMO** (`demo=true` or demo session) |
| `payment_status=initiated` | 5 | 65.00 | EUR | **UNKNOWN** (no `demo` flag; **not paid**) |
| pending / failed / refunded / cancelled | 0 | — | — | none in this collection |
| TEST (`sk_test_` session) | 0 | — | — | Stripe is not test-key mode |
| REAL paid | **0** | **0** | — | do not include demo |

| Type | COUNT | VALUE |
|---|---|---|
| missing `type` | 12 | 1265 |
| `wallet_topup` | 2 | 1100 RON |

**paid_not_flagged_demo = 0.**  
**Duplicate `session_id`:** 0.  
**Negative amounts:** 0.  
**Missing currency/amount:** 0.

**Cockpit `sum(paid)` on this DB = 2300 RON, 100% DEMO.**

---

# 2. Verified Estate

**Source:** `verified_estate_orders` (2 docs). Currency field **missing** (`amount_ron` used).

| | COUNT | GROSS `amount_ron` | Class |
|---|---|---|---|
| All | 2 | 2600 | — |
| `status=paid` | 2 | 2600 | — |
| `demo_mode=true` | 2 | 2600 | **DEMO** |
| `demo_mode≠true` paid | **0** | **0** | REAL = empty |
| package=`bundle` | 2 | 2600 | amounts ≠ default 2400+15000 |

| Item | Value |
|---|---|
| Net / refunds / payouts | **UNKNOWN** (no fields / no `manual_payments`) |
| Commission collected | **UNKNOWN** (no sale close evidenced here) |
| Listings | 4 total, **2 published** |
| Code defaults | audit 2400 / twin 15000 RON — **not** what these 2 orders store (2600 bundle) |

**EH `real_revenue` on this DB = 0** (filter `paid` + `demo_mode≠true` + no `manual_payments`).  
**War Room `revenue_real` = 0; `revenue_demo` = 2600.**

---

# 3. House Health

| Plan slug | price_eur | trial_days | active |
|---|---|---|---|
| basic | 9 | 7 | true |
| pro | 29 | 14 | true |
| **premium** | **249** | 14 | true |

| Subscriptions | COUNT |
|---|---|
| Total | **0** |
| Active / expired / trial / paid | **0** |
| Demo subs | n/a |

| Revenue interpretation | Value |
|---|---|
| Paid HH txs | **0** (heuristic: 5 EUR rows are `initiated`, not paid) |
| Cockpit MRR (`active unexpired × price_eur × 4.98`) | **0** (no subs) |
| Recurring revenue | **0 evidenced** (module is one-shot +30d even when paid) |
| One-shot revenue | **0 evidenced** |
| Trial grants | **0** (`trial_days` is display-only) |

**Do not treat 249 × 0 as “MRR policy.”** There is no payment/renewal evidence.  
**This environment’s Premium list price is 249, not 79.** Seed still says 79 if re-seeded on empty slug.

---

# 4. Marketplace

**Offers island:** collection exists, **0 offers**. Selection = Model A (`/accept`), not `accept_offer`.

| Funnel | COUNT / VALUE |
|---|---|
| requests | 118 |
| assigned + specialist | 112 |
| open | 6 |
| in_progress | 5 |
| completed (not confirmed) | 2 (escrow_sum 500) |
| **confirmed** | **12** |
| confirmed gross `escrow_amount` | **2750** (currency **UNKNOWN** — field has no currency) |
| implied D8 5% | 137.50 (arithmetic only) |
| implied specialist 95% | 2612.50 (arithmetic only) |
| selected_offer_id | **0** |
| confirmed with `demo` flag | **0** (flag unused on requests) |

**Escrow markers (not Stripe custody):**

| escrow_status | count | amount |
|---|---|---|
| released | 12 | 2750 |
| held | 10 | 2600 |
| paid | 2 | 1000 |
| null / none | 94 | 0 |

**Money classes**

| Class | Evidence |
|---|---|
| REAL MONEY | **0** Stripe; confirm credits **wallet** |
| INTERNAL WALLET | `users.wallet_balance` sum **50817.50**; `transactions.job_payment` 25 rows / 2802.50 |
| LEAD CREDITS | outstanding **1980**; `transactions.lead_credit` 4 / −180; `lead_fee` 57 / −2565 (mostly unmarked currency) |
| DEMO | 9 paid txs; VE 2; some `transactions.demo` (10 rows, −200) |
| TEST | Stripe not in test-key mode |

**Lead Credits are not revenue.**

---

# 5. D8 — 5%

**Runtime** (`routes/requests.py` `confirm_complete`):

```
source_amount     = request.escrow_amount or 0
specialist_amount = source_amount * 0.95
credit            = users.wallet_balance += specialist_amount
ledger            = transactions.insert { type: "job_payment", amount: specialist_amount }
platform take     = source_amount - specialist_amount   # implicit, NOT inserted
```

| Check | This DB |
|---|---|
| Formula | **0.95 hardcoded** |
| Platform revenue row | **MISSING** (no `platform_commission` tx) |
| job_payment rows | 25 / 2802.50 |
| confirmed jobs | 12 / escrow 2750 → 0.95 = 2612.50 |
| **Mismatch** | 25 ≠ 12 and 2802.50 ≠ 2612.50 — extra job_payments (demo time machine / disputes / old paths) |

**10% formula** (`financial_cockpit.py`): `released_escrow × 0.10` → on this DB **275.00** if it used confirmed/released 2750.  
**D8 implicit 5%** of same 2750 = **137.50**.  
**MISMATCH 2×.** Neither number is a cash deposit.

Design phases: `design_phase_payout` 1520 vs payment −1600 → **5% haircut also there** (1520/1600=0.95). Separate from Marketplace D8.

---

# 6. Financial Cockpit — KPI sheet

| KPI | FORMULA | SOURCE | FILTERS | DEMO FILTER | RANGE | CCY | REAL/DEMO/TEST | CONSUMER |
|---|---|---|---|---|---|---|---|---|
| revenue.total_paid | Σ amount | payment_transactions | payment_status=paid | **NONE** | all time | mixed as stored | **DEMO 2300 RON here** | Cockpit, CEO Dashboard |
| revenue.last_30d / prev | same | same | created_at window | **NONE** | 30/60d | same | DEMO if paid in window | growth_pct |
| pending_amount | Σ | payment_status in pending,initiated | none | all | **65 EUR initiated here** | UNKNOWN | Cockpit |
| escrow held/frozen/released | count + Σ escrow_amount | requests | escrow_status | none | all | unmarked | INTERNAL markers | Cockpit, CEO |
| mrr_eur | Σ plan.price_eur for status=active and expires_at≥now | hh_subscriptions × hh_plans | — | none | now | EUR | **0 here**; would be implied not cash | Cockpit, CEO |
| mrr_ron / arr_ron | mrr_eur × **4.98**; ×12 | hardcoded EUR_RON | — | — | — | RON | implied | same |
| commissions.released_escrow_take_est | released.amount × **0.10** | requests | escrow_status=released | none | all | unmarked | **WRONG vs D8 5%** | Cockpit |
| vat.estimated_30d | last_30d × **0.21** | derived | — | — | 30d | — | estimate | Cockpit |
| cash_flow_30d | daily Σ paid | payment_transactions | paid + day | **NONE** | 30d | — | DEMO here | Cockpit, CEO cash_ok |

---

# 7. Enterprise Health (money)

| Metric | FORMULA | SOURCE | DEMO FILTER | This DB |
|---|---|---|---|---|
| real_revenue | Σ amount_ron paid / 5000 × 100 | VE orders + manual_payments verified (skip VE-sourced dup) | **demo_mode≠true** | **0 RON** |
| paying_customers | distinct emails | same | same | **0** |
| fill_rate etc. | request counts | requests | none | operational, not money |

**vs Cockpit:** EH money = VE real. Cockpit money = all paid txs. **MISMATCH by design.** Here: EH 0 vs Cockpit 2300 DEMO.

HH / Marketplace **not** in EH revenue formula.

---

# 8. Business Health (money-related)

| Dept | Formula | Source | Same as Cockpit? |
|---|---|---|---|
| conversii | paid / all txs × 100 | payment_transactions | **same collection**, different KPI (rate not sum) |
| financiar | 60 + 30d paid growth × 0.8 | payment_transactions paid | **same paid txs**, growth not totals |
| escrow | released / (released+frozen) | requests | **same escrow field**, not amounts |
| marketplace | assigned / all requests | requests | not money |

**Demo filter:** none. On this DB, conversii = 9/14, all 9 paid = DEMO.

---

# 9. CEO Dashboard

| Field | Source | Filters | Demo-safe? | Real-money-safe? |
|---|---|---|---|---|
| `revenue` | **Financial Cockpit** | paid txs | **NO** — would show 2300 DEMO | **NO** |
| `mrr_ron` / `arr_ron` | Cockpit HH formula | active subs | n/a | **0** (no subs); formula still implied |
| `escrow_held` | Cockpit | held | markers | INTERNAL |
| `cash_flow_status` | last_30d ≥ 80% prev_30d | paid txs | **NO** | **NO** |
| `business_score` | Business Health | mixed | contaminated conversii/financiar | not a money SSOT |

---

# 10. CEO Briefing

| Field | Source | This DB |
|---|---|---|
| snapshot Revenue | EH `real_revenue` detail | **0 RON venit real (țintă 5000)** |
| pending VE | `verified_estate_orders` pending !demo | 0 |
| Mission / War Room | first_revenue.war_room | demo 2600 / real 0 |

**vs CEO Dashboard:** **MISMATCH.** Dashboard would surface Cockpit 2300 paid (demo). Briefing surfaces EH **0 real VE**.

---

# 11. War Room

| Term | Definition in `first_revenue.py` | This DB |
|---|---|---|
| REAL REVENUE | VE `status=paid` AND `demo_mode≠true` | **0** |
| DEMO REVENUE | VE `status=paid` AND `demo_mode=true` | **2600** |
| TEST REVENUE | **not a War Room bucket** | n/a |

**Consistent with EH.** **Inconsistent with Cockpit / CEO Dashboard / BH financiar.**

---

# 12. Wallet

| Object | What it is | This DB | Class |
|---|---|---|---|
| `users.wallet_balance` | increment on confirm 95%, topup (can be DEMO), lead_fee debit | Σ **50817.50** (client 15850 + specialist 34967.50) | **INTERNAL ACCOUNTING** |
| `wallets` collection | — | absent | — |
| Withdraw / payout to bank | **not implemented** (topup only) | — | no REAL CASH out |
| Escrow | request fields | held 2600 / released 2750 | **INTERNAL MARKERS** |
| Tokens | `users.tokens` | 6950 (clients) | **TOKENS** not money |
| `transactions` | mixed types, often **no currency** | 132 rows | INTERNAL + some `demo` |

`job_payment` 2802.50 ≪ wallet 50817.50 → **seed / topup / time-machine inflation**. Not cash.

---

# 13. Lead Credits — **not revenue**

| Measure | Value | Confidence |
|---|---|---|
| Outstanding (`users.lead_credits`) | **1980** (26 users have field; specialists only) | EVIDENCED |
| `transactions.lead_credit` | 4 rows, −180, currency=`lead_credits` | PARTIAL ledger |
| `transactions.lead_fee` | 57 rows, −2565, currency mostly missing | **RON-like debit**, not credits |
| Granted (auth 135) | cannot reconstruct full history from balances alone | **UNKNOWN** |
| Refunded | no dedicated type found | **UNKNOWN** |
| Consumed | `/accept` path + 4 lead_credit txs; offers path unused (0 offers) | PARTIAL |

Histogram / per-user grant sources: not dumped (PII). Outstanding + ledger ≠ closed-loop grant/consume report.

---

# 14. Currency / FX

| Conversion | Rate | Source | Timestamp | Usage |
|---|---|---|---|---|
| EUR→RON | **4.98 hardcoded** | `financial_cockpit.py` `EUR_RON` | none | MRR/ARR display |
| VE | RON field | `amount_ron` | order dates | EH / War Room |
| HH plans | EUR | `price_eur` | — | checkout amount |
| MP txs paid | RON | payment_transactions | 2026-05–09 | Cockpit |
| HH initiated | EUR | payment_transactions | — | pending 65 |
| Marketing Growth VAT | **0.19** | marketing_growth.py | — | **≠ Cockpit 0.21** |
| Confirm / wallet | unmarked | escrow_amount | — | D8 |

No configured FX feed. No FX timestamp.

---

# 15. Data quality

| Issue | Evidence |
|---|---|
| Demo contamination | 9/9 paid txs; 2/2 VE paid; Cockpit/BH/CEO Dashboard |
| Test contamination | Stripe not test-key; **UNKNOWN** if any row is leftover test |
| Duplicate txs | session_id dups 0 |
| Missing currency | VE orders; most `transactions`; request escrow |
| Missing timestamps | some escrow_status without paid_at **UNKNOWN** |
| Impossible / negative | wallet/credits ≥0; pt amounts ≥0 |
| Inconsistent commission | Cockpit 10% vs D8 5% vs HH lead 15/10/5 vs design 5% |
| job_payment vs confirmed | 25 vs 12; 2802.50 vs 2612.50 |
| Orphans | `marketplace_offers` empty vs 112 assigned; initiated HH 65 EUR no subs |
| VE amount vs SKU | 2600 bundle vs 17400 default |
| Wallet ≫ job_payment | 50817 vs 2802 |
| Premium 249 vs seed 79 | **this DB already 249** |
| `escrow_fund` −12000 vs `escrow_release` +9000 | demo/time-machine style INTERNAL |

---

# 16. Economic truth table

| DOMAIN | SOURCE | REAL | DEMO | TEST | INTERNAL | UNKNOWN | REVENUE? | ECONOMIC ACTIVITY? | SSOT CANDIDATE? |
|---|---|---|---|---|---|---|---|---|---|
| VE | verified_estate_orders | **0** | 2600 paid | 0 | — | currency missing | DEMO only | yes (2 demo orders) | **best REAL filter exists** (empty here) |
| HH | plans + subs + txs | **0** | 0 paid | — | 5 initiated EUR | what 65 is | no | checkout attempts | list price 249 evidenced |
| Marketplace | requests + confirm | **0 cash** | unflagged jobs | — | escrow + wallet | ccy | **no platform cash row** | **yes** (118 req, 12 confirm) | activity yes; money no |
| Wallet | users.wallet_balance | 0 bank | some topup demo | — | **50817** | composition | **no** | yes internal | internal ledger only |
| Lead Credits | users + tx | n/a | — | — | 1980 + fees | grants | **no** | yes specialist | inventory |
| Tokens | users.tokens | n/a | — | — | 6950 | — | **no** | perk | no |
| Payments | payment_transactions | **0** | 2300 | 0 | initiated 65 EUR | — | DEMO | yes | contaminated |
| Subscriptions | hh_subscriptions | 0 | 0 | 0 | 0 | — | no | no | empty |
| Commission | implicit 5% / cockpit 10% | 0 cash | — | — | 137.5 vs 275 arithmetic | which jobs real | **no cash** | yes implied | **not** |
| Escrow | request fields | 0 Stripe | DEMO checkout path | — | held/released | — | no | yes markers | markers |
| Payout | wallet credit | 0 withdraw | — | — | job_payment 2802 | extras | no | yes | internal |

**Do not propose a Revenue SSOT in this document.**

---

# 17. Cross-system comparison (this environment)

| | Financial Cockpit | Enterprise Health | Business Health | CEO Dashboard | CEO Briefing | War Room |
|---|---|---|---|---|---|---|
| **REVENUE** | 2300 paid (would) | **0 real VE** | growth on same 2300 | **Cockpit 2300** | **EH 0** | real 0 / demo 2600 |
| vs others | — | **MISMATCH** Cockpit | **MISMATCH** (score not 2300) | **MATCH** Cockpit | **MISMATCH** Dashboard | **MATCH** EH real; **MISMATCH** Cockpit |
| **TRANSACTIONS** | 14 / 9 paid | VE 2 | 9/14 rate | via Cockpit | VE pending 0 | VE counts |
| | | **MISMATCH** | **MISMATCH** meaning | MATCH Cockpit | MISMATCH | MISMATCH Cockpit |
| **MRR** | 0 | not used | not used | 0 | not used | not used |
| | MATCH (empty) | — | — | MATCH Cockpit | — | — |
| **COMMISSION** | 10% × released ≈ 275 | no | no | no | no | sale % settings |
| | **MISMATCH** D8 5% (137.5) | — | — | — | — | UNKNOWN vs D8 |
| **MARKETPLACE** | escrow buckets | fill_rate | fill_rate | new_requests_24h | fill + gaps | not GMV |

---

# 18. Final verdict

1. **Closest definition of REAL REVENUE already in code:** Enterprise Health / War Room — `verified_estate_orders.paid` AND `demo_mode≠true` (+ verified `manual_payments`). **In this environment that number is 0.**  
   Marketplace confirm 5% and HH paid checkout **could** be real later; they are **not** real here (no cash, DEMO Stripe, 0 HH payments).

2. **DEMO/TEST contaminated:** Cockpit `total_paid` (2300); BH conversii/financiar; CEO Dashboard `revenue` / cash_flow; VE paid (2600); some `transactions` (`demo` on 10 rows). Stripe mode itself is DEMO.

3. **Duplicates / parallel books:** four “revenues” (txs, VE, escrow GMV, implied 5%); two 5%/10% takes; job_payment vs confirmed; wallet vs job_payment; EUR vs RON without FX time.

4. **Contradictions:** 10% vs 5%; CEO Dashboard vs CEO Briefing; Premium **249 in this DB** vs seed **79**; VE 2600 vs SKU 17400; VAT 21 vs 19; fill/assignment 112 vs 0 offers.

5. **Trustworthy as facts:** Stripe is placeholder; 0 HH subs; 0 real VE; 0 paid non-demo txs; Premium price 249; 118 requests / 12 confirmed / 0 offers; D8 formula `* 0.95`; wallet and credits are internal.

6. **UNKNOWN:** whether any human paid real money in another environment; full credit grant/consume history; composition of 50817 wallet; why 25 job_payments vs 12 confirms; identity of 65 EUR initiated; live VE commission on the 2 published listings; FX 4.98 validity.

7. **Keep:** War Room / EH `demo_mode` split; D8 `* 0.95` as the **runtime** job take; `demo` on payment_transactions; Lead Credits as non-revenue; empty-sub MRR = 0 (honest here).

8. **Repair later (not now):** Cockpit/BH/CEO Dashboard demo filter; 10% estimate; job_payment vs confirm reconcile; currency on escrow/VE/transactions; Premium seed vs DB 249 documentation.

9. **Do not change yet:** prices, Marketplace, Stripe, dashboards, formulas, a new SSOT engine.

10. **Founder decisions:**  
    - Accept **0 real revenue** in this DB as the operating fact?  
    - Is **249** the intended Premium (this DB already) or revert to 79?  
    - When money exists, is REAL = VE only, or VE + HH paid + job 5%? (**do not implement SSOT now**)  
    - Treat wallet/credits as never-P&L?  
    - DEMO Stripe: stay demo or move test/live (ops, not this audit)?

---

**Closest honest sentence for this environment:**

> There is **economic activity** (requests, demo payments, demo VE, internal wallets, lead credits) and **no evidenced real cash revenue**. The only code path that already refuses to call demo VE “real” is War Room / Enterprise Health — and it reads **zero**.

**STOP.** No SSOT proposed. No implementation.
