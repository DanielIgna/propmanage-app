"""P3 Autonomy Expansion — Dispute triage + Project lifecycle (real DB, self-cleaning).

DISPUTES:
 - triage sets autonomy_triage (non-destructive), does NOT resolve, human_approval_required.
 - insufficient evidence explicitly flagged; priority deterministic.
 - no financial mutation (wallet untouched by triage).
PROJECT LIFECYCLE:
 - valid SAFE active→on_hold executes (stale+clean) + read-back verified.
 - invalid transition rejected.
 - blocked project cannot be archived (funded milestone / active task).
 - MEDIUM on_hold→archived requires human approval (no mutation without approval).
 - kill-switch blocks SAFE mutation.
 - idempotent; state verified after execution.
 - verified lifecycle outcome → knowledge only after real verification.
AUTONOMY:
 - single unified queue (dispute + lifecycle items), ledger gets lifecycle actions, metrics present.

Run:  python3 -m tests.test_autonomy_expansion_p3
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bson import ObjectId

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import db
from autonomy import disputes as D
from autonomy import lifecycle as LC
from autonomy import activity as A
from autonomy import loop as L

TAG = f"p3_{uuid.uuid4().hex[:8]}"
results = []
_ids = {"projects": [], "disputes": [], "requests": [], "users": [], "tasks": []}


def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")


async def cleanup():
    await db.projects.delete_many({"_p3": TAG})
    await db.disputes.delete_many({"_p3": TAG})
    await db.requests.delete_many({"_p3": TAG})
    await db.users.delete_many({"_p3": TAG})
    await db.project_tasks.delete_many({"_p3": TAG})
    await db.project_lifecycle_actions.delete_many({"project_id": {"$in": [str(x) for x in _ids["projects"]]}})
    await db.ai_memories.delete_many({"source": "verified_outcome", "meta.finding_key": {"$regex": TAG}})
    await db.admin_ai_findings.delete_many({"composite_key": {"$regex": TAG}})


def _iso(days_ago=0):
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


async def main():
    await cleanup()

    # ---------- DISPUTES ----------
    # user with wallet (to prove triage doesn't move money)
    ures = await db.users.insert_one({"_p3": TAG, "role": "client", "name": "P3 Client", "wallet_balance": 500.0,
                                      "email": f"{TAG}@test.local"})
    _ids["users"].append(ures.inserted_id)
    rres = await db.requests.insert_one({"_p3": TAG, "title": "P3 Lucrare parchet", "category": "parchet",
                                         "status": "in_progress", "escrow_amount": 1500,
                                         "client_id": str(ures.inserted_id), "created_at": _iso(10)})
    _ids["requests"].append(rres.inserted_id)
    # dispute with sufficient info
    d1 = await db.disputes.insert_one({"_p3": TAG, "request_id": str(rres.inserted_id), "opened_by_role": "client",
                                       "reason": "Parchetul montat are denivelări vizibile și rosturi neuniforme pe 10 mp.",
                                       "evidence_urls": ["http://x/photo1.jpg"], "status": "open", "created_at": _iso(9)})
    _ids["disputes"].append(d1.inserted_id)
    # dispute with insufficient info
    d2 = await db.disputes.insert_one({"_p3": TAG, "request_id": None, "opened_by_role": "client",
                                       "reason": "nasol", "evidence_urls": [], "status": "open", "created_at": _iso(1)})
    _ids["disputes"].append(d2.inserted_id)

    wallet_before = (await db.users.find_one({"_id": ures.inserted_id})).get("wallet_balance")
    dd1 = await db.disputes.find_one({"_id": d1.inserted_id})
    dd2 = await db.disputes.find_one({"_id": d2.inserted_id})
    r1 = await D.triage_one(dd1, use_llm=False)
    r2 = await D.triage_one(dd2, use_llm=False)
    t1 = (await db.disputes.find_one({"_id": d1.inserted_id})).get("autonomy_triage")
    t2 = (await db.disputes.find_one({"_id": d2.inserted_id})).get("autonomy_triage")
    wallet_after = (await db.users.find_one({"_id": ures.inserted_id})).get("wallet_balance")

    check("dispute triage sets autonomy_triage", bool(t1) and bool(t2))
    check("dispute status NOT changed by triage", (await db.disputes.find_one({"_id": d1.inserted_id}))["status"] == "open")
    check("human_approval_required always True", t1.get("human_approval_required") is True)
    check("insufficient_information flagged (d2)", t2.get("insufficient_information") is True and t2.get("status") == "waiting_information")
    check("sufficient-info dispute is ready_for_human (d1)", t1.get("status") == "ready_for_human")
    # determinism
    r1b = await D.triage_one(await db.disputes.find_one({"_id": d1.inserted_id}), use_llm=False, force=True)
    t1b = (await db.disputes.find_one({"_id": d1.inserted_id})).get("autonomy_triage")
    check("priority deterministic (same input → same priority)", t1.get("priority") == t1b.get("priority"))
    check("NO financial mutation from triage (wallet unchanged)", wallet_before == wallet_after == 500.0)

    # ---------- PROJECT LIFECYCLE ----------
    autonomy_actor = {"email": "autonomy@propmanage.ai", "name": "loop"}
    # P1: active + stale (40d) + clean → eligible SAFE on_hold
    p1 = await db.projects.insert_one({"_p3": TAG, "name": "P3 Stale Clean", "status": "active",
                                       "updated_at": _iso(40), "created_at": _iso(60), "members": []})
    _ids["projects"].append(p1.inserted_id)
    # P2: on_hold + funded milestone → archive blocked
    p2 = await db.projects.insert_one({"_p3": TAG, "name": "P3 OnHold Escrow", "status": "on_hold",
                                       "updated_at": _iso(40), "created_at": _iso(60), "members": [],
                                       "milestones": [{"id": "m1", "name": "Avans", "status": "funded"}]})
    _ids["projects"].append(p2.inserted_id)
    # P3b: active recent → NOT stale
    p3 = await db.projects.insert_one({"_p3": TAG, "name": "P3 Fresh", "status": "active",
                                       "updated_at": _iso(2), "created_at": _iso(5), "members": []})
    _ids["projects"].append(p3.inserted_id)

    pid1, pid2, pid3 = str(p1.inserted_id), str(p2.inserted_id), str(p3.inserted_id)

    # invalid transition
    inv = await LC.transition_project(pid1, "active_to_archived", actor=autonomy_actor)
    check("invalid transition rejected", inv["status"] == "rejected" and inv.get("error") == "transition_not_allowed")

    # kill-switch blocks SAFE
    ks = await LC.transition_project(pid1, "active_to_on_hold", actor=autonomy_actor, autoexec_allowed=False)
    check("kill-switch OFF blocks SAFE mutation", ks["status"] == "blocked_governance")
    check("kill-switch: project still active (no mutation)", (await db.projects.find_one({"_id": p1.inserted_id}))["status"] == "active")

    # NOT stale → not eligible
    fresh = await LC.transition_project(pid3, "active_to_on_hold", actor=autonomy_actor, autoexec_allowed=True)
    check("fresh project not eligible for on_hold", fresh["status"] == "blocked" and "not_stale" in str(fresh.get("reason")))

    # valid SAFE on_hold executes + verified
    ok = await LC.transition_project(pid1, "active_to_on_hold", actor=autonomy_actor, autoexec_allowed=True, reason="test")
    p1_after = (await db.projects.find_one({"_id": p1.inserted_id}))["status"]
    check("SAFE active→on_hold executed", ok["status"] == "executed" and ok.get("verified") is True)
    check("read-back verified (project is on_hold)", p1_after == "on_hold")

    # idempotent
    idem = await LC.transition_project(pid1, "active_to_on_hold", actor=autonomy_actor, autoexec_allowed=True)
    check("idempotent (already on_hold → wrong_state/idempotent, no crash)", idem["status"] in ("blocked", "idempotent"))

    # on_hold→archived requires human approval (no mutation)
    med = await LC.transition_project(pid1, "on_hold_to_archived", actor=autonomy_actor, autoexec_allowed=True)
    check("on_hold→archived requires human approval", med["status"] == "requires_human_approval")
    check("archive NOT executed without approval", (await db.projects.find_one({"_id": p1.inserted_id}))["status"] == "on_hold")

    # blocked project (funded milestone) cannot be archived even with approval
    blk = await LC.transition_project(pid2, "on_hold_to_archived", actor=autonomy_actor, autoexec_allowed=True, human_approved=True)
    check("archive blocked by escrow milestone", blk["status"] == "blocked" and any(b["type"] == "escrow_active" for b in blk.get("blockers", [])))
    check("blocked project still on_hold", (await db.projects.find_one({"_id": p2.inserted_id}))["status"] == "on_hold")

    # archive after approval on clean project (p1 has no blockers)
    arch = await LC.transition_project(pid1, "on_hold_to_archived", actor=autonomy_actor, autoexec_allowed=True, human_approved=True)
    check("on_hold→archived executes WITH approval + verified", arch["status"] == "executed" and arch.get("verified") is True)
    check("read-back verified (archived)", (await db.projects.find_one({"_id": p1.inserted_id}))["status"] == "archived")

    # ledger received actions
    ledger_ct = await db.project_lifecycle_actions.count_documents({"project_id": {"$in": [pid1, pid2, pid3]}})
    check("lifecycle ledger received actions", ledger_ct >= 5)

    # verified lifecycle outcome → knowledge only after real verification
    fkey = f"stale_project::{TAG}"
    await db.admin_ai_findings.insert_one({"composite_key": fkey, "pattern": "stale_project", "status": "triaged",
                                           "recommended_action": "on_hold", "affected_route": f"project:{pid1}",
                                           "entity_type": "project", "entity_id": pid1,
                                           "autonomy_action": {"type": "lifecycle", "transition": "active_to_on_hold",
                                                               "verified": True, "todo_id": None}})
    kb = await L.promote_verified_to_knowledge([])  # backfill path picks it up
    mem = await db.ai_memories.find_one({"source": "verified_outcome", "meta.finding_key": fkey})
    check("verified lifecycle outcome promoted to knowledge", bool(mem))

    # ---------- AUTONOMY read-model ----------
    act = await A.get_activity()
    m = act["metrics"]
    check("single unified queue returned", isinstance(act.get("queue"), list) and "counts" in act)
    check("metrics include disputes block", "disputes" in m and "disputes_total_open" in m["disputes"])
    check("metrics include lifecycle block", "lifecycle" in m and "lifecycle_actions_total" in m["lifecycle"])
    q_sources = {it.get("source") for it in act["queue"]}
    check("queue contains dispute + lifecycle items", "dispute" in q_sources and "project_lifecycle" in q_sources)

    await cleanup()

    passed = sum(1 for _, c, _ in results if c)
    total = len(results)
    print(f"\n=== P3 EXPANSION: {passed}/{total} PASS ===")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
