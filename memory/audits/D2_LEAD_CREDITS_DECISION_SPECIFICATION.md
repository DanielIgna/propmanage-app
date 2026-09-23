# D2_LEAD_CREDITS_DECISION_SPECIFICATION

**Decision:** D2 — Lead Credits = Marketplace opportunity **participation** currency  
**Canonical consume event:** Model B `submit_offer`  
**Mode:** READ-ONLY specification. No implementation, flags, prices, credits, Stripe, commit, or deploy.  
**Depends on:** D1 (public Marketplace = Model B)  
**Sources:** `PROP_MANAGE_COMMERCIAL_ECONOMY_MASTER_AUDIT.md`, `MARKETPLACE_CANONICAL_DECISION_SPECIFICATION.md`, `LEAD_CREDITS_MODEL_B_RECONCILIATION_AUDIT.md`, working-tree symbols below.  
**Date:** 2026-09-22

---

# 1. Context (not re-audited)

D1: public flow is Request → offers → client choice → commercial relationship → pay → execute → confirm → payout.

Current **ENFORCED** hook (working tree):

| Step | Symbol | Behavior |
|---|---|---|
| Grant | `auth.register` / `auth.become_specialist` | 135 on first specialist activation |
| Consume | `requests.accept_request` | −45 credits **or** −45 RON, then `{open}→assigned` |
| B apply | `marketplace_offers.submit_offer` | −5..50 RON `marketplace_offer_fee` — **no credits** |
| B select | `marketplace_offers.accept_offer` | assignment — **no credits** |

Reconciliation already proved: field, 135 grant, missing=0, atomic `$inc`, ledger types, profile lock, ≠ `users.tokens` **KEEP**. Consumption is **Model-A-specific**. Turning B on without moving the hook creates **two public lead prices**.

This document **moves the meaning**, not the code.

---

# 2. D2 decision (formal)

**LEAD CREDITS = MARKETPLACE OPPORTUNITY PARTICIPATION CURRENCY**

Under canonical Model B:

```
Specialist discovers eligible opportunity
  → chooses to participate
  → pays the applicable Lead Credit cost (or same-event cash fallback)
  → submits an offer
```

**Canonical consume event = `submit_offer`.**

Not: first-wins, public `/accept`, client selection, `/confirm`, payout.

The Lead Credit buys **the right to have an offer in the comparison set**. It does **not** buy the job.

---

# 3. Three economies (invariants)

| | Economy | Object | Event | Must not become |
|---|---|---|---|---|
| **A** | House Health lead attribution | `hh_plans.lead_commission_pct` (UI 15 / 10 / 5) | HH publish + B `accept_offer` capture | Lead Credits |
| **B** | Marketplace lead | Lead Credits / same-event wallet fallback | **`submit_offer` (D2)** | Job 5% or HH % |
| **C** | Job transaction | `confirm_complete` `amount * 0.95` | `/confirm` | Lead Credits |

Do not merge A, B, C. D8 / D11 remain open and **must not** be solved by wiring 15/10/5 into credits.

---

# 4. Semantic definition — LEAD CREDIT

**A Lead Credit is a server-controlled unit of specialist Marketplace participation inventory.**

| Clause | Definition |
|---|---|
| Represents | One increment of **paid participation** in a public Marketplace opportunity (standard size today: **45** per submission) |
| Consume event | Successful **`submit_offer`** (atomic with offer insert) |
| Does **not** represent | Selection, assignment, escrow, job value, subscription, loyalty, HH commission, or cash on the balance sheet |
| Guarantees selection? | **No** |
| Guarantees client/job payment? | **No** |
| Is money? | **No.** Wallet RON is a **fallback payment method for the same event**, not the credit itself |
| vs wallet | Optional cash substitute **for that same `submit_offer`**, same amount, same ledger semantics — not a second fee |
| vs `users.tokens` | Unrelated (client loyalty on `/confirm`) |
| vs subscription | Unrelated (HH/DT access) |
| vs `lead_commission_pct` | Unrelated (HH attribution on offer **fee**, not credits) |
| vs job 5% | Unrelated (`/confirm`) |

Do not call it a “lead token.” Term: **Lead Credit**.

Onboarding math (descriptive only): **135 / 45 = 3** standard specialist participations.  
**≠** client “3 free projects” (D9, still open).

---

# 5. Consumption event and atomic invariant

**Target event:** `marketplace_offers.submit_offer`  
**Route (existing):** `POST /api/requests/{req_id}/offers`

Conceptual order (not implemented):

```
eligible open request
  → debit 45 Lead Credits (else same-event 45 RON)
  → insert marketplace_offers row
```

**Invariant — one commercial operation:**

| Outcome | Allowed |
|---|---|
| **A** | Valid offer **and** valid debit (credits or same-event wallet) |
| **B** | No offer **and** no debit |

**Forbidden:**

- Debit without a persisted offer  
- Offer without a valid debit (unless a **separate** D13 residual waive applies — not public B)  
- Double debit for one submission  
- Two active charges for the same submission (credits **and** 5–50 apply **and** 45 RON)

Reuse later: `find_one_and_update` / `$inc` / refund-on-failed-write from `accept_request` — **move the hook, do not invent an engine.**

---

# 6. Non-selection vs technical failure

| Case | Refund? | Reason |
|---|---|---|
| Client selects another specialist | **No** | Participation was delivered |
| Offer withdrawn by specialist | **No** (same commercial rule; today’s B withdraw already keeps apply fee) | Participation was delivered |
| Technical failure (insert/debit/claim fails, duplicate blocked after debit, request no longer `open` after debit) | **Yes** | Operation did not complete |
| Public `/accept` first-wins after D1 | **Must not** be a second public charge path | D13 |

**Invariant:** commercial loss ≠ technical failure.

---

# 7. Wallet fallback and 5–50 RON

**If** cash fallback is retained (amount unchanged in this spec: **45 RON**):

- Same event as credits: **`submit_offer`**  
- Same amount as the credit cost  
- One method wins: credits **or** wallet, not both  
- Ledger: keep `lead_credit` vs `lead_fee` meanings (credit units vs RON) — writer **moves** to submit  

**Existing Model B `OfferIn.fee_ron` 5–50 + `marketplace_offer_fee`:**

**Classification: LEGACY / TO BE RECONCILED.**

Repository role today: specialist-chosen **apply wallet fee** + ranking weight.  
It is **not** Lead Credits and **must not** silently coexist as a **second** participation charge for the same offer.

Later implementation must **replace or retire** that apply fee as the public participation price — not stack it on 45 credits. Ranking that uses `fee_ron` is a **follow-on** (D5), not D2.

Do not change amounts or code here.

---

# 8. 135 grant (unchanged)

| Activation | Credits |
|---|---|
| Native `register` `role=specialist` | 135 |
| `become_specialist` (`$set`, guarded) | 135 |
| Google OAuth new user | 0 (`role=client`) |
| Credits after OAuth | only via specialist activation |
| Missing/null | 0; no backfill |

**Do not change 135 or 45 in this decision.**  
135/45 = 3 specialist participations ≠ client D9.

---

# 9. `/accept` under D2 (D13 still open)

D2 states:

- Public Marketplace economics **must not** be defined by `accept_request` credit debit.  
- **Do not delete** `POST /api/requests/{id}/accept` as part of D2.  
- Residual uses already evidenced: rebook / maintenance-direct + `lead_fee_waived`. Campaign assigns **without** this route.  
- D13 decides deprecate vs INTERNAL-ONLY vs other.  
- Until D13: `/accept` may remain in the tree; it **must not** remain the **public first-wins commercial path**.

---

# 10. Security invariants (preserve)

1. Server-controlled field; not in `ProfileUpdateIn`.  
2. Debit atomic; cannot go negative (`$gte` then `$inc`).  
3. Refund only on **failed technical operation**, not on lose.  
4. Ledger records the event (`lead_credit` or same-event `lead_fee`).  
5. Specialist cannot set own participation **cost** (today they **can** set 5–50 `fee_ron` — that control **conflicts** with D2 and is part of LEGACY reconcile).  
6. Client cannot mint or debit credits.  
7. No new credit engine.

---

# 11. Before / after

```
CURRENT (A):
  Specialist → accept_request → −45 credits|RON → assigned immediately

TARGET (B / D2):
  Specialist → eligible open request → submit_offer
            → −45 credits|same-event RON → offer row
            → client may select or reject
            → no automatic assignment
```

**Logic that must later move** from `accept_request` to `submit_offer` (or a shared helper called **only** from submit for public B):

- `LEAD_CREDIT_COST` / `LEAD_FEE_RON` debit order  
- waive check **only if** D13 residual still uses `/accept` (not public submit)  
- failed-write refund  
- `lead_credit` / `lead_fee` insert  
- `paid_with` / `lead_credits_after` response fields (if exposed on offer create)

**Must not move to `accept_offer`:** that would be D2-option-B (selection), which this specification **rejects**.

---

# 12. Code impact map (later — not now)

| FILE / SYMBOL | CURRENT ROLE | D2 IMPACT | ACTION LATER | DEPENDENCY | RISK |
|---|---|---|---|---|---|
| `backend/routes/requests.py` `LEAD_CREDIT_COST` / `LEAD_FEE_RON` | A constants | Shared amounts | **KEEP** values; **REDIRECT** consumer | D2 impl | Dual consumers if `/accept` still public |
| `requests.accept_request` | Sole debit + assign | Must not define public economy | **INTERNAL-ONLY** or stop debit on public opens | D13 | Race with B |
| `requests.create_request` | Create `open` | None | **KEEP** | — | — |
| `auth.register` `lead_credits: 135 if specialist` | Grant | None | **KEEP** | — | — |
| `auth.become_specialist` `$set 135` | Grant | None | **KEEP** | — | — |
| `auth` OAuth inserts `lead_credits: 0` | Grant 0 | None | **KEEP** | — | — |
| `auth.ProfileUpdateIn` / `update_profile` | Cannot write credits | None | **KEEP** | — | — |
| `auth.get_me` serialize | Display | None | **KEEP** | — | — |
| `marketplace_offers.submit_offer` | Wallet 5–50, no credits | **Becomes** debit+insert | **REFACTOR** | Reconcile `OfferIn.fee_ron` | Double charge if both kept |
| `marketplace_offers.accept_offer` | Select + HH capture | No credit debit | **KEEP** (no credit hook) | D6 | Wrong if someone “fixes” D2 here |
| `marketplace_offers.withdraw_offer` | No refund | Align with commercial-loss | **KEEP** policy | — | — |
| `OfferIn.fee_ron` 5–50 | Specialist-set apply price | LEGACY vs D2 | **RECONCILE** (retire as participation fee) | D5 ranking | Ranking uses fee |
| `transactions` `lead_credit` / `lead_fee` | Written by `/accept` | Writer moves | **KEEP** types | — | Analytics miss credits (`bi_moe`) |
| `ActivityTimeline.jsx` `ScheduleProposalModal` | Accept + credits copy | Public CTA wrong | **REFACTOR** / residual only | D13 | Users still first-wins |
| `SpecialistDashboard.jsx` “Acceptă · 45 RON” | A CTA | Stale | **REFACTOR** → apply | D13 + mount `OfferApplyForm` | B starved |
| `MarketplaceOffers.jsx` `OfferApplyForm` | Unmounted; charges wallet 5–50 | Must use D2 price | **REFACTOR** + **mount** | Flag after D13 | Flag-on race |
| `MarketplaceOffers.jsx` `OffersList` | Client select | No credit change | **KEEP** | Offers exist | Empty list |
| `admin_console.py` `lead_fee_ron` | Dead 45 | Still not SSOT unless wired | **DEPRECATE** or wire **after** D2 | D8 | False SSOT |
| `admin.py` `leads_count * 45` | A revenue | Lies under B | **REFACTOR** | D2 live | Overstate cash |
| `admin.py` `auto_match_run` | Assign, bypass fee | Not public B | **INTERNAL-ONLY** | D13 | Silent free jobs |
| `matching.py` display `lead_fee` 0/45 | A annotation | Misleading | **DEPRECATE** display | — | — |
| `qa_automation.py` QUOTE-01 / PAY-TX-LEAD / PAY-INSUFF | −45 wallet on `/accept` | Wrong event | **REPLACE** | D2 impl | CI/QA fight B |
| `test_lead_credits.py` | Encodes `/accept` | Wrong event | **MODIFY** / add submit cases | D2 impl | Green on A |
| Legal / `docs_content` / `RoleTour` “45 RON / accept” | A copy | Wrong event | **REDIRECT** copy | After impl | Trust |

---

# 13. Test impact map (do not edit tests now)

| Test / runner | Encodes | Later |
|---|---|---|
| `test_lead_credits.py` grant / OAuth / profile / missing=0 | Inventory | **KEEP** |
| `test_lead_credits.py` 135→90→45→0 then wallet on **`/accept`** | A consume | **MODIFY** → same math on **`submit_offer`** |
| `test_lead_credits.py` waived `/accept` | Residual | **KEEP** until D13; not public B |
| `test_lead_credits.py` concurrent `/accept` | A race | **REPLACE** with concurrent submit / cap-5 |
| `test_phase31` / `test_gbos_growth` “−45 RON on accept” | A cash | **MODIFY** or confine to residual |
| `test_community_buildings` no `lead_fee` on campaign | Campaign skip | **KEEP** |
| QA QUOTE-01, PAY-TX-LEAD | `/accept` + `lead_fee` −45 | **REPLACE** |
| QA PAY-INSUFF (wallet 0) | Ignores 135 credits | **REPLACE** |
| Offer submit 5–50 tests (Sprint C) | B apply wallet | **MODIFY** after reconcile |
| **New:** submit debit + no assign | D2 | **NEW TEST REQUIRED** |
| **New:** lose / withdraw = no credit refund | D2 | **NEW TEST REQUIRED** |
| **New:** technical fail = refund, no offer | D2 | **NEW TEST REQUIRED** |
| **New:** cannot stack credits + 5–50 on one submit | D2 | **NEW TEST REQUIRED** |
| **New:** `accept_offer` does not debit credits | D2 | **NEW TEST REQUIRED** |
| **New:** public `/accept` rejected or no-debit | D1+D13 | **NEW TEST REQUIRED** after D13 |

---

# 14. Migration invariants (before any D2 code)

1. One public participation event: **offer submission**.  
2. Lead Credit consumed **exactly once** per successful submission.  
3. Technical failure reverses debit; commercial rejection does not.  
4. Public `/accept` cannot run a second first-wins economy.  
5. Existing balances remain valid (no conversion, no backfill).  
6. `users.tokens` separate.  
7. `lead_commission_pct` separate.  
8. `/confirm` 5% separate.  
9. Wallet fallback, if kept, is the **same** event and amount.  
10. 5–50 apply fee **cannot** silently coexist as a second charge.  
11. No duplicate commercial charge.  
12. No new Lead Credit engine.  
13. 135 grant paths unchanged.  
14. D13 not “solved” by deleting `/accept` in the D2 patch.

---

# 15. What D2 does **not** decide

| ID | Still open |
|---|---|
| **D6** | Event that **is** the commercial relationship (today = `assigned`; not submit) |
| **D8** | Job commission SSOT (`0.95` vs admin %) |
| **D11** | HH sub → marketplace access / % vs job cut |
| **D13** | Final `/accept` role |
| **D9** | Client 3 free experiences |
| **Pricing** | Premium seed 79 vs UI 249 |
| **Amounts** | 135 and 45 stay; not a commercial reprice |
| **Flag** | `multi_offer_enabled` is not authorized by this spec |

---

# 16. FINAL DECISION STATEMENT

**D2:**

> Lead Credits are the Marketplace participation currency for specialists under the canonical Model B flow. The canonical consumption event is offer submission. A successful commercial submission consumes the applicable Lead Credit amount; technical failure reverses the debit; commercial non-selection does not refund the credit. Lead Credits remain separate from House Health lead attribution and from job transaction commission.

**STATUS:** DECISION SPECIFICATION — READY FOR FOUNDER APPROVAL

No implementation has been authorized by this document.

---

**STOP.** File: `memory/audits/D2_LEAD_CREDITS_DECISION_SPECIFICATION.md`
