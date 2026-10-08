# 📖 EXECUTIVE DECISION REGISTER — PropManage
**Directiva 072 · Memoria instituțională a deciziilor · Început: Iulie 2026**

| ID | Data | Epic | Decizie Founder | Motiv | Beneficii așteptate | Riscuri | Cost/ROI est. | Status | Rezultat real | Lecții |
|---|---|---|---|---|---|---|---|---|---|---|
| D-001 | Iul 2026 | Verified Properties | Audit complet FĂRĂ cod înainte de orice implementare (Directiva 054) | Protejarea investiției, reuse-before-rebuild | Blueprint exact, zero cod redundant | Întârziere mică | ~2 credite / evită ~30 credite risipite | ✅ VALIDAT | Audit a găsit G1 (webhook rupt) — bug care ar fi ucis prima plată LIVE | Auditul înainte de cod = cel mai bun ROI din sesiune |
| D-002 | Iul 2026 | Verified Properties | **GO Faza A** (webhook Stripe VE + flux vânzare/comision + fix twin) — APPROVED WITH CONDITIONS, Board unanim | Singura lucrare care deblocheză venit real | Plăți LIVE funcționale, comision calculabil | Scăzut (modul izolat, feature flag) | 15–20 credite / amortizare la prima comandă | ✅ LIVRAT (iter_126: 100%) | În așteptarea validării comerciale | — |
| D-003 | Iul 2026 | Verified Properties | **STOP Fazele B–D** până la minim 1 tranzacție reală (condiția C3) | „Măsoară înainte să investești" (D058) | Economie 60–70 credite până la validare | Feature-gap la scalare (acceptat) | 0 / evită speculație | 🟡 ACTIV | — | — |
| D-004 | Iul 2026 | Governance | Directivele 055–087 salvate ca sistem permanent de guvernanță; agent = Executive Intelligence System | Instituționalizarea gândirii | Decizii consistente, memorie durabilă | Overhead documentare (mic) | ~3 credite | ✅ ACTIV | — | — |
| D-005 | Iul 2026 | EVO | **EVO livrat ca documente** (`ENTERPRISE_VALUE_OFFICE.md`), NU ca dashboard in-app | Founder's Compass: doar Q3=DA → efort minim justificat; dashboard in-app = credite fără impact pe venit | Evaluare completă la cost minim | Datele nu-s live (acceptat — reevaluare la milestone-uri) | ~3 credite vs ~15 pentru in-app | ✅ LIVRAT | — | Dashboard in-app doar dacă Founderul îl cere după prima plată |
| D-006 | Iul 2026 | War Room | War Room construit in-app (`/admin/war-room`), nu doc | D059 cere „LIVE permanent display"; datele se schimbă zilnic | Vizibilitate continuă blockers/milestones | — | inclus în Faza A | ✅ LIVRAT | — | — |
| D-007 | Iul 2026 | Growth OS | **GO Faza G1 Lead Engine** (2 lead magnets + 4 ghiduri + CTA + funnel); respinse: CRO fără trafic, National Index pe 0 date, AI-org ca microservicii | GAP analysis: 45% din Growth OS exista; pipeline gol = blocker intern #1 | Mașină de leads organică, cost/lead→0 | Rate limiting lipsă (TD-07) | ~20 credite | ✅ LIVRAT (iter_127: 100%) | — | GAP analysis înainte de epic = economie masivă |
| D13-1 | 24 Sep 2026 | Fulfillment governance | **APPROVED — X TBD.** `MULTI_OFFER → FALLBACK` only when age ≥ X and zero open offers. Full record below. Not the commercial-economy D13 (`/accept`). | An open paid offer must not be displaced. Auto-Match stays, under a separate authority after an explicit transition. | Client choice holds while any offer is open. System fill is possible only for an aged empty board. | X unset. Stale requests that still have open offers are out of scope. | No implementation in this decision. | ✅ APPROVED — X TBD | Not implemented. | One-hour Auto-Match gate is not X. |
| D13-2 | 24 Sep 2026 | Fulfillment governance | **APPROVED.** `DIRECT_REBOOK` is a strategy lock when `is_rebooking` is true and `specialist_id` is empty. Full record below. | A named specialist must not be silently replaced. Public offers and Auto-Match assignment are blocked while the lock holds. | Waived `/accept` stays the normal claim. Client may explicitly release into `MULTI_OFFER`. Admin override is a separate authority. | No timeout. Unanswered requests stay locked until release or admin override. | No implementation in this decision. No new engine. | ✅ APPROVED | Not implemented. | D13-1 X is not a Direct/Rebook timer. `direct_specialist_id` or `lead_fee_waived` alone is not this lock. |
| D13-3 | 24 Sep 2026 | Fulfillment governance | **APPROVED.** Health Repair has no independent commercial assignment authority. Trigger is not authority. Full record below. | An unfilled or old request must not be assigned merely because repair detected a gap. | Repair stays for detect, technical repair, notify, and identifying a fulfillment need. Strategy authority assigns. | Three trigger-policy details stay open. They do not grant repair assignment authority. | No implementation in this decision. No new engine. No new refund. | ✅ APPROVED | Not implemented. | `triggered_by.kind = repair` is not `AUTO_MATCH`, `SYSTEM_FALLBACK`, or `ADMIN`. |

## D13-1 — MULTI_OFFER → FALLBACK = TIME + ZERO OPEN OFFERS

**Status:** APPROVED — X TBD  
**Date:** 24 Sep 2026  
**Recorded from:** Founder approval of the D13-1 analysis.  
**Implementation:** none. This row does not authorize code, Auto-Match, or marketplace changes.

This decision is fulfillment governance. It is not commercial-economy D13 in `memory/audits/MARKETPLACE_CANONICAL_DECISION_SPECIFICATION.md`, which remains the open question of residual `/accept`.

### Approved rule

Public requests classified `MULTI_OFFER` may transition to `FALLBACK` only when both are true:

1. The configured minimum age X has elapsed.
2. The request has zero open offers.

`X = TBD`. X stays configurable. The current one-hour Auto-Match age gate is not the approved value of X. X is set only after measuring: time to first offer, time to client selection, percentage of requests with zero offers, time requests remain open, requests reaching multiple offers, and stale-request distribution.

While the request remains `MULTI_OFFER`:

- Auto-Match may inspect candidates.
- Auto-Match may dry-run and calculate candidates.
- Auto-Match must not assign the request.
- No system authority may silently override client selection.

After the explicit transition `MULTI_OFFER → FALLBACK`, the request is eligible for authority `SYSTEM_FALLBACK`. The existing Auto-Match machinery may execute that assignment under `SYSTEM_FALLBACK`.

`AUTO_MATCH` and `SYSTEM_FALLBACK` stay separate authorities.

- `AUTO_MATCH` — the request was classified for automatic fulfillment from the beginning.
- `SYSTEM_FALLBACK` — the request started as `MULTI_OFFER` and explicitly transitioned to `FALLBACK`.

### Commercial protection

An open paid offer must not be displaced by this rule.

- One or more open offers block the transition.
- This decision introduces no refund policy.
- Existing Lead Credit / 45 RON rules stay unchanged.
- Existing technical-refund semantics stay unchanged (reversal only after a failed offer insert, not on loss or withdrawal).

### Concurrency invariant

The transition is conditional. It may commit only while:

- status = open
- fulfillment_strategy = MULTI_OFFER
- zero open offers
- the approved age condition is satisfied

It must not race through `submit_offer`, `accept_offer`, or another assignment path.

- If the client accept commits first: client selection wins, the fallback transition fails, and no specialist is overwritten.
- If the fallback transition commits first: the request is `FALLBACK`, `SYSTEM_FALLBACK` may assign afterward, and client selection on the old `MULTI_OFFER` path must no longer assign.

### Audit

The transition records: previous strategy, new strategy, transition reason, the condition that triggered it, the X value used at the time, timestamp, and actor/trigger (`system`, or admin where applicable).

### Scope

Applies only to public `MULTI_OFFER` requests.

This decision does not decide: `DIRECT_REBOOK`, `CAMPAIGN`, `EMERGENCY`, `INSTANT_SERVICE`, `RECOMMENDATION`, native `AUTO_MATCH` requests, or Health Repair authority.

Health Repair remains undecided and is reserved as D13-3.

Offer expiration, refund, and stale-offer rules are not part of this decision. What happens when an offer stays open for a long time is a separate future decision.

## D13-2 — DIRECT / REBOOK PROTECTION

**Status:** APPROVED  
**Date:** 24 Sep 2026  
**Recorded from:** Founder approval of the D13-2 analysis.  
**Implementation:** none. This record does not authorize runtime changes. No new fulfillment engine is authorized.

### Core decision

A request created through the trusted rebook flow or the maintenance-calendar direct flow is `DIRECT_REBOOK` when `is_rebooking` is true and `specialist_id` is empty.

`DIRECT_REBOOK` is a strategy lock.

`is_rebooking` is the canonical existing marker. Do not introduce a second Direct/Rebook creator or a duplicate engine.

`direct_specialist_id` alone, or `lead_fee_waived` alone, is not sufficient to classify a request as `DIRECT_REBOOK`.

### Named specialist

While the request is `DIRECT_REBOOK` and unassigned, `direct_specialist_id` is the intended fulfillment target.

The normal assignment path is the existing specialist `/accept` flow (`requests.accept_request`). That accepted assignment stays fee-waived under the existing Direct/Rebook behavior.

### No automatic timeout

No Direct/Rebook timeout is approved.

Do not reuse D13-1 X, the current one-hour Auto-Match gate, or any other Auto-Match timing as a Direct/Rebook release timer.

An unanswered `DIRECT_REBOOK` request stays `DIRECT_REBOOK` until an explicitly authorized client release or admin override.

### Client release

The client who owns the request may explicitly release it from `DIRECT_REBOOK` into `MULTI_OFFER`.

This is a strategy transition. It is not D13-1 fallback, not Auto-Match, not Health Repair, and not an implicit timeout.

The release is owner-scoped, explicit, auditable, and concurrency-safe.

After that transition, normal `MULTI_OFFER` rules apply. D13-1 can apply only after the request is `MULTI_OFFER`.

### Public offers

While the request is `DIRECT_REBOOK`, public `submit_offer` is not permitted. Other specialists must not pay 45 Lead Credits or 45 RON to participate in a request still reserved for the named specialist.

After the explicit client release into `MULTI_OFFER`, public offers are permitted under existing D2 rules.

No new refund rule is introduced.

### Auto-Match

While `DIRECT_REBOOK` is active, Auto-Match may inspect or report the request if existing operational tooling needs visibility. Auto-Match must not assign it. This covers cron, manual Auto-Match, and any equivalent automatic Auto-Match execution.

`DIRECT_REBOOK` must not silently transition into `AUTO_MATCH` or `FALLBACK`.

### Health Repair

Health Repair must not bypass the `DIRECT_REBOOK` lock.

D13-3 remains the separate decision on Health Repair’s broader commercial assignment authority. D13-2 does not decide D13-3.

### Admin override

An explicit admin override is permitted. It must be distinguishable from `AUTO_MATCH`, `SYSTEM_FALLBACK`, and Health Repair. It is explicit and auditable.

Where applicable, the audit preserves: previous strategy, `DIRECT_REBOOK`, original `direct_specialist_id`, new specialist, new authority `ADMIN`, reason, actor, timestamp, and resulting strategy.

Auto-Match must not be reused as the representation of an admin override. The existing admin authorization model may be reused.

### Campaign boundary

Campaign requests are outside this decision. Campaign remains identified by its existing campaign semantics, including `is_campaign`.

### D13-1 compatibility

D13-1 stands: `MULTI_OFFER` may move to `FALLBACK` only when configured age X has elapsed and zero open offers exist. X remains TBD.

D13-1 X is not a Direct/Rebook timer. `DIRECT_REBOOK` does not enter `FALLBACK` through D13-1. Only an explicit release into `MULTI_OFFER` places the request on the normal `MULTI_OFFER` lifecycle.

### Fees

This decision introduces no new Lead Credit or RON refund policy. Existing D2 participation rules stay unchanged. No inferred refund is allowed.

### Approved invariants

1. `DIRECT_REBOOK` cannot be silently converted into `MULTI_OFFER`.
2. Generic Auto-Match cannot assign a `DIRECT_REBOOK` request.
3. Health Repair cannot bypass the `DIRECT_REBOOK` lock.
4. The named specialist remains the intended target until an explicit release or an approved admin override.
5. Assignment stays concurrency-safe so two commercial assignees cannot be committed through competing writers.
6. Public `submit_offer` cannot bypass the `DIRECT_REBOOK` boundary.
7. Any release or override is auditable.
8. Any fee or Lead Credit consequence is explicitly defined, never inferred.

### Future implementation boundary

Future implementation reuses existing architecture: `is_rebooking`, `direct_specialist_id`, `requests.accept_request`, `execute_auto_match`, `assign_gap`, `submit_offer`, `accept_offer`, existing authorization helpers, existing event/activity history, and existing configuration mechanisms.

No new fulfillment engine is authorized. A later implementation phase may add the minimum shared assignment and transition guards required to enforce this governance.

## D13-3 — HEALTH REPAIR AUTHORITY

**Status:** APPROVED  
**Date:** 24 Sep 2026  
**Recorded from:** Founder approval of the D13-3 analysis.  
**Implementation:** none. This record does not change runtime behavior. No new Repair Engine, Matching Engine, or Fulfillment Engine is authorized.

### Core decision

Health Repair does not have independent commercial assignment authority.

Health Repair remains an operational health and repair mechanism. It may detect, analyze, repair technical and data state, reconcile, notify, and identify a fulfillment need.

It must not independently choose and assign a commercial specialist merely because a request is old, unfilled, or detected as a gap.

### Trigger is not authority

`triggered_by.kind = "repair"` identifies how an action was initiated. It is not `AUTO_MATCH`, `SYSTEM_FALLBACK`, `ADMIN`, `DIRECT_REBOOK`, or `CLIENT_SELECTION`.

Health Repair must not become a hidden assignment authority by delegating directly to an assignment writer.

### Active strategy owns commercial authority

When fulfillment is required:

Health Repair detects or identifies a fulfillment need, then the active strategy and that strategy’s assignment authority perform assignment.

The exact trigger permissions for each strategy are constrained below. No new engine is authorized.

### DIRECT_REBOOK — D13-2 preserved

Health Repair must not assign a request while `is_rebooking` is true and `specialist_id` is empty.

It must not bypass the named specialist, invoke generic Auto-Match assignment, convert the request implicitly, use a timeout to release it, or represent an override as `repair`.

D13-2 remains authoritative.

### MULTI_OFFER — D13-1 preserved

Health Repair must not assign a public `MULTI_OFFER` request while that strategy remains `MULTI_OFFER`.

Open paid offers block system assignment. Health Repair must not bypass client selection, invent a fallback timer, or treat the one-hour Auto-Match gate as D13-1 X.

D13-1 remains: `MULTI_OFFER` moves to `FALLBACK` only after age ≥ X and zero open offers, through an explicit transition. X remains TBD. Health Repair must not silently perform that transition.

### FALLBACK

After the D13-1 transition, the commercial assignment authority is `SYSTEM_FALLBACK`, not `repair`.

Health Repair may trigger or participate in that path only if a future implementation explicitly permits that trigger. This decision does not grant Health Repair automatic `SYSTEM_FALLBACK` authority. No second fallback rule is created.

### Native AUTO_MATCH

`AUTO_MATCH` remains an independent fulfillment authority. Calling `execute_auto_match` with `triggered_by.kind = "repair"` does not make Health Repair that authority.

If Health Repair is later permitted to trigger native `AUTO_MATCH`, the assignment authority recorded must remain `AUTO_MATCH`, and the trigger must remain Health Repair. Those are separate. This permission is not granted universally by D13-3.

### ADMIN

`ADMIN` remains a separate assignment authority. A Health Repair action must not be represented as an admin override.

An admin override of a Direct/Rebook request remains the D13-2 `ADMIN` authority and keeps that decision’s audit semantics.

### Campaign

Campaign is outside this authority decision. Do not classify a request as `DIRECT_REBOOK` from `direct_specialist_id` alone or `lead_fee_waived` alone. Campaign semantics stay on the existing campaign fields and lifecycle.

### Emergency, Instant Service, Recommendation

D13-3 does not define commercial authority for `EMERGENCY`, `INSTANT_SERVICE`, or `RECOMMENDATION`. Those strategies are not fully implemented. Health Repair must not invent assignment behavior for them.

A future strategy decision must say whether Health Repair may detect them, whether it may trigger fulfillment, and which authority assigns.

### Approved invariants

1. Health Repair is not an independent commercial assignment authority.
2. Health Repair must not override client selection.
3. Health Repair must not bypass `DIRECT_REBOOK`.
4. Health Repair must not assign `MULTI_OFFER` while that strategy is active, in particular while open offers exist.
5. Health Repair must not create an implicit fallback rule.
6. Health Repair must distinguish technical repair from commercial fulfillment.
7. If fulfillment is required, the active strategy and its assignment authority stay explicit.
8. A repair trigger must not be confused with the authority that performs the assignment.
9. Any future repair-triggered fulfillment must preserve strategy, authority, trigger, reason, specialist, and timestamp in the audit trail.
10. Health Repair must not silently bypass Lead Credit or commercial fee rules.
11. Assignment must be concurrency-safe with client selection, Auto-Match, admin assignment, Direct/Rebook acceptance, and any future fulfillment authority.

### Reuse

Future implementation reuses `health_repair.py`, `DOMAIN_ENGINES`, Repair Center, `health_repair_runs`, `execute_auto_match`, `matching.py`, the existing assignment writers, activity events / the event bus, existing authorization, existing configuration, and the existing Auto-Match scheduler.

Do not create duplicate engines. The later implementation may constrain `_repair_operations` and `_repair_marketplace` so they no longer produce unauthorized commercial assignments.

Any shared conditional assignment or transition mechanism required by D13-1, D13-2, and D13-3 belongs to that later implementation phase. This decision does not implement it.

### Open implementation policy questions

These stay open. They must not be decided silently, and they are not permission for Health Repair to become a commercial authority:

A. Whether Health Repair may trigger `SYSTEM_FALLBACK` after a valid D13-1 transition.  
B. Whether Health Repair may trigger native `AUTO_MATCH` for requests already classified `AUTO_MATCH`.  
C. How Emergency and Instant Service will expose their own authorities.

### Fees

D13-3 introduces no new Lead Credit or RON refund policy. Existing D2 participation and technical-refund semantics stay unchanged. No refund may be inferred from a repair-triggered event.

## Review trimestrial (primul: Oct 2026)
- Cele mai bune decizii · Cele mai scumpe greșeli · ROI maxim/minim · Recomandări

*Regulă: orice decizie importantă viitoare primește un rând AICI înainte de implementare.*
