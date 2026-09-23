# LEAD_CREDITS_MODEL_B_RECONCILIATION_AUDIT

**Mode:** READ-ONLY. Working tree inspected (including uncommitted Lead Credits).  
**No** file, DB, flag, commit, or deploy changes.  
**Date:** 2026-09-22

Product context: public Marketplace direction = **Model B**. Current consumption is **Model A `/accept`**.

Statuses: IMPLEMENTED · ENFORCED · RUNTIME-CONSUMED · AUTOMATED · DISCONNECTED · UNKNOWN

---

# 0. Verdict in one paragraph

The current Lead Credits **inventory** (field, 135 grant, missing=0, not tokens, not client-writable, atomic `$inc`, refund-on-failed-claim, ledger types) is **model-neutral** and can stay.  
The current Lead Credits **commercial hook** is **strictly Model A**: debit happens only inside `accept_request`, on the same request as immediate assignment.  
`marketplace_offers.submit_offer` / `accept_offer` **never read or write** `lead_credits`.  
Therefore the implementation **cannot safely serve public Model B unchanged**. Grant/storage/security can remain; **consumption must be re-anchored (D2)** or **confined to residual `/accept`**. Wallet fallback is the cash twin of that **same A event**, not a second product.

**Lead Credit ≠ House Health `lead_commission_pct`.** No runtime equation exists.

---

# 1. End-to-end trace

## 1.1 CREATION

| Path | File | Symbol | Route | DB | Tx | Runtime caller | Status |
|---|---|---|---|---|---|---|---|
| Native specialist register | `backend/routes/auth.py` | `register` user insert | `POST /api/auth/register` | `users.lead_credits = 135` if `role==specialist` else `0` | none | public register | **ENFORCED** |
| Client → specialist | `auth.py` | `become_specialist` `$set lead_credits: 135` | `POST /api/auth/become-specialist` | same field | none | dual-role activation | **ENFORCED** (idempotent `$set` after 400 guards) |
| Google OAuth new user (2 inserts) | `auth.py` ~1174, ~1313 | OAuth upsert | Google callbacks | `lead_credits: 0`, `role: client` | none | OAuth | **ENFORCED** |
| Repeat become-specialist | same | 400 if already dual/specialist | same | no second grant | — | — | **ENFORCED** |
| Existing users missing field | `requests.py` | `int(specialist.get("lead_credits") or 0)` | `/accept` | treat as 0 | — | accept | **ENFORCED** (no backfill) |
| Seed / demo writers | `seed.py`, `demo_reset.py` | wallet 500/800 historically | n/a | **no `lead_credits` grant found** in production register | — | fixtures | **UNKNOWN** for old rows (missing=0) |

Working-tree check vs stated facts: **all confirmed.** Native specialist 135 + wallet 0. Client/OAuth 0 until become-specialist. No 135 on Google insert.

## 1.2 STORAGE

| | |
|---|---|
| Field | `users.lead_credits` (integer-used; not a collection) |
| Schema model | **not** in `models.py` |
| Distinct from | `users.wallet_balance` (RON), `users.tokens` (client loyalty) |
| Status | IMPLEMENTED · PERSISTED on write paths above |

## 1.3 DISPLAY

| File | Symbol | Route | Status |
|---|---|---|---|
| `auth.py` | `GET /api/auth/me` → `serialize_doc(user)` | includes field if present | RUNTIME-CONSUMED |
| `ActivityTimeline.jsx` | `ScheduleProposalModal` | `user.lead_credits >= 45` → “45 Lead Credits” else “45 RON” | RUNTIME-CONSUMED |
| `SpecialistDashboard.jsx` | CTA | **hardcoded “Acceptă · 45 RON”** (ignores credits) | DISCONNECTED / stale |
| Admin dedicated credits UI | — | **NOT FOUND** | — |

## 1.4 CONSUMPTION

| File | Symbol | Route | Field | Tx | Caller | Status |
|---|---|---|---|---|---|---|
| `requests.py` | `accept_request` | `POST /api/requests/{id}/accept` | `$inc lead_credits: -45` if `>= 45` | `type=lead_credit` `currency=lead_credits` `amount=-45` | SpecialistDashboard modal | **ENFORCED** |
| same | wallet branch | same | `$inc wallet_balance: -45` if credits fail | `type=lead_fee` `currency=RON` `amount=-45` | same | **ENFORCED** |
| same | waive | same | no debit if `direct_specialist_id==user` AND `lead_fee_waived` | none | rebook / maintenance-direct | **ENFORCED** |
| `marketplace_offers.py` | `submit_offer` / `accept_offer` | `/offers` | **no credit read/write** | `marketplace_offer_fee` wallet only | flag-gated apply | **DISCONNECTED** from credits |

Constants: `LEAD_CREDIT_COST = 45`, `LEAD_FEE_RON = 45.0` — hardcoded, **not** `platform_config.lead_fee_ron`.

## 1.5 REFUND

| File | Symbol | When | What |
|---|---|---|---|
| `requests.py` `accept_request` | claim `find_one_and_update {status:open}` fails | credits: `$inc +45`; wallet: `$inc +45` RON | **ENFORCED** |
| Ledger | refund is **balance increment only** — no compensating `lead_credit` tx on failed claim | | IMPLEMENTED |
| `withdraw_offer` | B | **no credit refund** (credits never spent); wallet apply fee **not** refunded | N/A to credits |

## 1.6 LEDGER

| type | currency | amount | Writer |
|---|---|---|---|
| `lead_credit` | `lead_credits` | −45 | `/accept` credit path only |
| `lead_fee` | `RON` | −45 | `/accept` wallet path only |
| `marketplace_offer_fee` | (RON implied) | −5..−50 | B submit — **not** a credit tx |

`bi_moe.py` aggregates `type ∈ [lead_fee, marketplace_offer_fee]` — treats A cash and B apply as “lead fees”, **ignores** `lead_credit`.

## 1.7 ADMIN

| Path | Behavior | Status |
|---|---|---|
| `platform_config.lead_fee_ron` default 45 | `admin_console.py` / `AdminPlatformTools.jsx` | CONFIGURED, **not consumed** by `/accept` |
| `admin.py` stats `lead_fees = leads_count * 45.0` | assumes every lead = 45 RON | MODEL-A analytics |
| `POST /admin/auto-match/run` | assigns **bypassing** 45 RON (and credits) | INTERNAL, fee-free |
| Admin `$set lead_credits` API | **NOT FOUND** | no dedicated mutate route |

## 1.8 API

| Route | Credits role |
|---|---|
| `POST /auth/register` | write 135/0 |
| `POST /auth/become-specialist` | `$set` 135 |
| OAuth inserts | write 0 |
| `GET /auth/me` | read via full user serialize |
| `PATCH /auth/profile` | **cannot** set `lead_credits` (`ProfileUpdateIn` allowlist) |
| `POST /requests/{id}/accept` | **only** consume + refund |
| `/offers*` | none |

## 1.9 TESTS

FILE: `backend/tests/test_lead_credits.py` — AUTOMATED (14 cases): native 135; client 0; OAuth source 0; become-specialist 135; repeat 400; 135→90→45→0 then wallet; insufficient reject; waived neither; tokens unchanged; profile cannot write; concurrent one 200 / credits=90.

**All tests assume `/accept` = consume event.** None cover `submit_offer` / `accept_offer`.

QA `qa_automation.py` QUOTE-01 / PAY-TX-LEAD / PAY-INSUFF still assume **wallet −45 on `/accept`** (stale vs credits-first). `PAY-INSUFF` zeros wallet only — new specialists can still accept with 135 credits.

---

# 2. Model A vs reusable

| Behavior | Classification | Why (evidence, not inference) |
|---|---|---|
| Debit inside `accept_request` | **MODEL-A-SPECIFIC** | Only consumer; first-wins + assign in same function |
| Atomic `{status:open}→assigned` after debit | **MODEL-A-SPECIFIC** | Immediate assignment |
| Refund if claim loses race | **MODEL-A-SPECIFIC** location; **MODEL-NEUTRAL** pattern | Race is A first-wins; `$inc` refund is generic |
| Wallet fallback in same function | **MODEL-A-SPECIFIC** location | Tied to `/accept` |
| `lead_fee_waived` + `direct_specialist_id` | **MODEL-A-SPECIFIC** residual (rebook) | Only evaluated in `/accept` |
| 135 grant on first specialist activation | **MODEL-NEUTRAL** | No marketplace model in grant |
| OAuth 0 / client 0 / missing=0 | **MODEL-NEUTRAL** | Identity, not A/B |
| Field + not client-writable | **MODEL-NEUTRAL** | — |
| Ledger types `lead_credit` / `lead_fee` | **MODEL-NEUTRAL** shapes; **A** writers today | — |
| `ScheduleProposalModal` credit copy | **MODEL-A-SPECIFIC** | Accept CTA |
| SpecialistDashboard “45 RON” | **MODEL-A-SPECIFIC** | Accept CTA |
| `submit_offer` 5–50 wallet | **MODEL-B** (not credits) | No `lead_credits` symbol in file |
| `accept_offer` HH capture | **MODEL-B** | Independent of credits |
| `leads_count * 45` admin revenue | **MODEL-A-SPECIFIC** | — |
| `platform_config.lead_fee_ron` | **UNKNOWN** intended model | unused |
| `/match` display `lead_fee` 0/45 | **MODEL-A** display | not charged |

---

# 3. Model B compatibility (two stories)

Current hook: **debit then immediately claim assignment**. Payment (credits or RON) **is** the assignment attempt.

### Story 1 — submit offer, client picks someone else

| Current credits | Actual B code |
|---|---|
| No debit | `submit_offer` wallet −5..50, `type=marketplace_offer_fee`, **no refund** on lose/withdraw |
| Credits stay 135 | Loser paid apply fee, not credits |

**Compatible only if D2 ≠ submit.** If D2 = submit, current code **does not** do that.

### Story 2 — submit offer, client selects this specialist

| Current credits | Actual B code |
|---|---|
| No debit on `accept_offer` | Sets `assigned` + `selected_offer_id`; HH % captured; **no** `lead_credit` / `lead_fee` |
| Win is free in credits | Apply fee already paid at submit |

**Compatible only if D2 = unused on B.** If D2 = selection, current code **does not** debit.

### Coupling points (exact)

1. `requests.accept_request` — sole credit consumer.  
2. `find_one_and_update {status:open}` — payment implies assignment.  
3. FE Accept CTA — only UX that mentions credits.  
4. `test_lead_credits.py` / QA — encode A coupling.  
5. **Zero** coupling in `marketplace_offers.py`.

---

# 4. Three semantics (do not choose)

| | **A. Consume on offer submit** | **B. Consume on specialist selection** | **C. Consume on commercial relationship** |
|---|---|---|---|
| Current code | **Incompatible** — debit not in `submit_offer` | **Closest meaning** (win), **wrong route** (`/accept` not `accept_offer`) | **Equals B in current B code** (selection writes `assigned`) |
| Reuse | field, 135, atomic `$inc`, ledger type | same + refund-if-assign-fails pattern | same as B unless D6 ≠ selection |
| Debit timing | at apply (now: wallet 5–50 instead) | at win (now: only `/accept`) | at `assigned` (same write as B today) |
| Refund timing | need new policy; B withdraw = no refund today | current: refund if claim fails | if D6=payment, refund if pay fails — **not implemented** |
| Failed selection | N/A if already paid to apply | no debit if never selected — **fits current meaning** | same as B |
| Abandoned offer | credits gone if A; today wallet gone | credits kept | credits kept |
| Multiple offers | 3 applies = 135 if cost=45; **stacks with 5–50 RON** unless apply fee removed | many applies, 3 wins = 135 | same as B |
| Abuse | apply-spam drains grant | apply-spam free in credits (wallet 5–50 still) | depends on D6 |
| Races | 5-offer cap; no A race on submit | A `/accept` vs B select if both public | same |
| Wallet fallback | would be cash apply **or** collide with 5–50 | cash twin of **win** (current) | same as B if D6=assigned |
| Ledger | new writer on `submit_offer`; conflict with `marketplace_offer_fee` | new writer on `accept_offer` | same as B |
| UX | pay to wait | pay when chosen (current promise) | same as B if D6=assigned |

**C is not a distinct event unless D6 ≠ selection.**

---

# 5. 45 RON / 45 credits / lead_fee map

| Occurrence | Belongs to |
|---|---|
| `LEAD_FEE_RON` / wallet `/accept` | **MODEL A** |
| `LEAD_CREDIT_COST` / credit `/accept` | **MODEL A** (cash twin) |
| `lead_fee` tx | **MODEL A** |
| `lead_credit` tx | **MODEL A** writer; type reusable |
| `lead_fee_waived` + `direct_specialist_id` | **MODEL A** residual (rebook/maintenance); campaign sets waive but **skips** `/accept` |
| `platform_config.lead_fee_ron` | **LEGACY** unused |
| Admin `leads_count * 45` | **MODEL A** |
| `/match` `lead_fee: 45` | **MODEL A** display |
| SpecialistDashboard / Legal / RoleTour / docs “45 RON/lead” | **MODEL A** / **DOCUMENTED** |
| ActivityTimeline credits vs 45 RON | **MODEL A** (updated for credits) |
| QA QUOTE-01 / PAY-TX-LEAD | **MODEL A** (stale vs credits-first) |
| `OfferIn` 5–50 / `marketplace_offer_fee` | **MODEL B** (not 45) |
| `hh_plans.lead_commission_pct` | **neither** (HH attribution) |
| `ghiduri.js` “28-45 RON/mp” | unrelated labor price |
| `demo_time_machine.LEAD_FEE` | **LEGACY** demo |
| `futureIdeas.js` 45 RON | **DOCUMENTED** idea, not runtime |

**45 RON is not a Model B offer fee and not Beta-flagged.**

---

# 6. House Health relationship

| | Lead Credits | `hh_plans.lead_commission_pct` |
|---|---|---|
| Actor | Specialist inventory | Client plan attribute |
| Trigger | `/accept` | HH publish stamp; B `accept_offer` capture |
| Unit | 45 credits or 45 RON | % of **offer fee** |
| Paid? | Yes (or waived) | `captured` only, never `paid` |

**INDEPENDENT.** No file references both. No code assumes Lead Credit = HH commission.

`marketplace_offers.accept_offer` can capture HH % **without** touching credits — **runtime disconnected**.

---

# 7. Wallet fallback

| Question | Evidence |
|---|---|
| When? | After credit `find_one_and_update` fails (`lead_credits < 45` or missing) |
| Then? | Atomic `wallet_balance >= 45` or 400 |
| Model-A-specific? | **Location yes** (only in `/accept`). **Pattern** (credits then RON) is portable |
| Sense under B? | Yes **if** D2 names one event and 5–50 apply is removed or redefined |
| Two payment paths? | **Already:** credits **or** 45 RON on A; **plus** 5–50 RON on B submit if flag on → **three** cash/credit paths |
| Coexist with offer economics? | **Conflict** if both public: win/apply priced twice unless D2 + apply fee are reconciled |

Do not change it in this audit.

---

# 8. Security / authorization

| Actor | Can write `lead_credits`? |
|---|---|
| Client | **No** — grant 0; profile allowlist excludes field |
| Specialist | **No** via profile; consume only via `/accept` (own id) |
| `PATCH /auth/profile` | `ProfileUpdateIn`: name, phone, zone, avatar, categories, zones only. Extra JSON dropped. **AUTOMATED** |
| Generic mass-assign | Not on this field |
| Admin dedicated API | **NOT FOUND** |
| Backend-only | `register`, `become_specialist`, `accept_request` debit/refund |
| OAuth | insert 0 only; existing-user patch does **not** touch credits |
| Tests | Mongo `$set` in fixtures only |

**Unauthorized creation:** no client/specialist self-grant found.  
**Unauthorized debit:** only by calling `/accept` as that specialist (intended).  
**Admin auto-match:** assigns **without** debit (bypass, not credit mint).  
**GDPR export:** includes user doc + transactions (read).

No fix in this pass.

---

# 9. Legacy reconciliation map

| Current path | Model | Reusable? | Conflict with B? | Later action |
|---|---|---|---|---|
| `users.lead_credits` field | Neutral | Yes | No | **KEEP** |
| 135 grant register / become-specialist | Neutral | Yes | No | **KEEP** |
| OAuth / client 0; missing=0 | Neutral | Yes | No | **KEEP** |
| Profile not writable | Neutral | Yes | No | **KEEP** |
| Atomic `$inc` + failed-claim refund | Neutral pattern | Yes | No | **KEEP** (move hook) |
| `lead_credit` / `lead_fee` tx shapes | Neutral | Yes | No | **KEEP** |
| Debit in `accept_request` | A | Hook only | **Yes** if `/accept` stays public | **DECISION REQUIRED** (D2+D13) |
| Wallet fallback in `accept_request` | A location | Pattern yes | Yes if dual public prices | **DECISION REQUIRED** |
| Waive / rebook `/accept` | A residual | Yes for D13 | No if not public | **INTERNAL-ONLY** candidate |
| Campaign waive without `/accept` | Other assign | n/a | No credit involvement | **KEEP** (out of credits) |
| `submit_offer` 5–50 | B | Yes | Double lead price vs 45 | **DECISION REQUIRED** |
| `accept_offer` no credits | B | — | If D2=selection, missing debit | **REDIRECT** later |
| ActivityTimeline credit CTA | A | Copy reusable | Yes as public take-job | **REFACTOR** / **INTERNAL-ONLY** |
| SpecialistDashboard “45 RON” | A | No | Yes | **REFACTOR** |
| `lead_fee_ron` admin | Legacy | After D2 | False SSOT | **DEPRECATE** or wire after D2 |
| Admin `* 45` revenue | A | No | Lies under B | **REFACTOR** |
| `bi_moe` lead_fee + offer_fee | Both cash | Partial | Ignores credits | **REFACTOR** |
| QA −45 wallet on accept | A stale | No | Fights credits **and** B | **REFACTOR** |
| `test_lead_credits.py` | A consumer | Patterns yes | Locks D2 to `/accept` | **REFACTOR** after D2 |
| `/match` display 45 | A | No | Misleading | **DEPRECATE** display |
| Docs/legal 45 RON/lead | A | — | Yes | **REDIRECT** copy after D2 |
| HH `lead_commission_pct` | Other economy | Yes as HH | If merged with credits | **KEEP** separate |
| Admin auto-match fee bypass | Internal A | — | Silent free assign | **INTERNAL-ONLY** |

---

# 10. Critical question

**If Model B is the only public Marketplace model:**

### Can remain unchanged

- `users.lead_credits`  
- 135 on first specialist activation (`register` specialist, `become-specialist` `$set`)  
- Client / Google OAuth `0`  
- missing/null = 0, no backfill  
- distinct from `tokens` / wallet / vouchers / entitlements  
- `ProfileUpdateIn` exclusion  
- Atomic `$inc` / refund-on-failed-mutation **pattern**  
- Transaction type names `lead_credit` and `lead_fee`  
- Independence from HH `lead_commission_pct`

### Must change (after D2 + D13)

- **The consume function:** today only `accept_request`  
- If D2 = selection: debit (+ fallback + ledger) must run on `accept_offer` (or shared helper called from there), **not** on public first-wins  
- If D2 = submit: debit on `submit_offer`; **must** reconcile with 5–50 `marketplace_offer_fee` (do not leave both)  
- If D2 = unused on B: public B must **not** call `/accept` debit  
- Specialist public CTA, tests, QA, admin `×45`, Legal/docs that say “pay 45 to accept”  
- Wallet fallback **moves with** the chosen event or is dropped if B apply wallet remains the cash path

### Must no longer participate in **public** Marketplace transactions

- `POST /api/requests/{id}/accept` as the **normal** take-job / credit charge  
- First-wins race with `accept_offer`  
- SpecialistDashboard “Acceptă · 45 RON” on ordinary open leads  
- Analytics that assume every public lead = 45 RON cash  

`/accept` **may** still debit/waive for **residual** rebook/maintenance-direct **if D13 says INTERNAL-ONLY** — that is not public Model B.

---

**STOP.** File: `memory/audits/LEAD_CREDITS_MODEL_B_RECONCILIATION_AUDIT.md`  
No other files modified. D2 remains unchosen.
