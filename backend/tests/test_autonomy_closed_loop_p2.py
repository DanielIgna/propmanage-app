"""P2 Closed-Loop Autonomy — regression proof (real DB, self-cleaning).

Verifies the invariants the Founder cares about:
 1. SAFE + governance ON  → auto todo + finding resolved + verified.
 2. SAFE + governance OFF → BLOCKED (no todo, finding not resolved).  [kill-switch respected]
 3. MEDIUM              → human approval (NEEDS_HUMAN), finding stays open, NO auto-exec.  [b1 gate]
 4. VERIFIED outcome    → exactly 1 reusable knowledge memory (source=verified_outcome), idempotent.
 5. Knowledge source is 'verified_outcome' (real), never 'autonomy_seed' (synthetic).
 6. Activity metrics + queue are derived from real ledgers and categorize correctly.

Run:  python3 -m tests.test_autonomy_closed_loop_p2
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import db
from autonomy import loop as L
from autonomy import activity as A

TAG = f"p2loop_{uuid.uuid4().hex[:8]}"
results = []


def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")


def _obs(detector, route, sev="low"):
    return {
        "detector": detector, "affected_route": route, "severity": sev, "confidence": 0.9,
        "raw_observation": {"tag": TAG}, "finding": f"{TAG} test finding",
        "hypothesis": "test", "recommended_action": f"{TAG} remediere",
        "verification_criteria": "test",
    }


async def cleanup():
    keys = [f"{L.SOURCE}:high_bounce_page:/{TAG}_safe",
            f"{L.SOURCE}:request_flow_abandonment:/{TAG}_medium",
            f"{L.SOURCE}:high_bounce_page:/{TAG}_gov"]
    await db.admin_ai_findings.delete_many({"composite_key": {"$in": keys}})
    await db.admin_todos.delete_many({"finding_key": {"$in": keys}})
    await db.admin_approvals.delete_many({"finding_key": {"$in": keys}})
    await db.ai_memories.delete_many({"source": "verified_outcome", "meta.finding_key": {"$in": keys}})


async def main():
    await cleanup()

    # 1) SAFE + governance ON
    obs = _obs("high_bounce_page", f"{TAG}_safe")
    f, _ = await L.get_or_create_finding(obs)
    act = await L.decide_and_act(f, autoexec_allowed=True)
    fdoc = await db.admin_ai_findings.find_one({"composite_key": f["composite_key"]})
    check("SAFE+ON → auto todo", act["action"]["type"] == "todo" and not act["human_gate"])
    check("SAFE+ON → finding resolved", fdoc["status"] == "resolved")
    ver = await L.verify(f, act)
    check("SAFE+ON → verify.ok", ver.get("ok") is True)

    # 4/5) VERIFIED → knowledge (idempotent, source=verified_outcome)
    step = {"action": act["action"], "actor": "autonomous", "human_gate": False,
            "verify": {"ok": True}, "finding_key": f["composite_key"],
            "detector": "high_bounce_page", "route": f"/{TAG}_safe", "recommended_action": f"{TAG} remediere"}
    k1 = await L.promote_verified_to_knowledge([step])
    k2 = await L.promote_verified_to_knowledge([step])  # rerun
    mem_ct = await db.ai_memories.count_documents({"source": "verified_outcome", "meta.finding_key": f["composite_key"]})
    check("VERIFIED → 1 knowledge memory created", k1["knowledge_records_created"] >= 1)
    check("Knowledge idempotent (rerun creates 0)", k2["knowledge_records_created"] == 0 and mem_ct == 1)
    mem = await db.ai_memories.find_one({"source": "verified_outcome", "meta.finding_key": f["composite_key"]})
    check("Knowledge source=verified_outcome (not autonomy_seed)", mem and mem.get("source") == "verified_outcome" and not str(mem.get("source")).startswith("autonomy_seed"))

    # 2) SAFE + governance OFF → BLOCKED
    obs_g = _obs("high_bounce_page", f"{TAG}_gov")
    fg, _ = await L.get_or_create_finding(obs_g)
    act_g = await L.decide_and_act(fg, autoexec_allowed=False)
    todo_g = await db.admin_todos.find_one({"finding_key": fg["composite_key"]})
    fgdoc = await db.admin_ai_findings.find_one({"composite_key": fg["composite_key"]})
    check("SAFE+OFF → blocked_governance", act_g["action"]["type"] == "blocked_governance" and act_g.get("blocked"))
    check("SAFE+OFF → NO todo created", todo_g is None)
    check("SAFE+OFF → finding NOT resolved", fgdoc["status"] != "resolved")

    # 3) MEDIUM → human approval, NO auto-exec (b1 gate preserved)
    obs_m = _obs("request_flow_abandonment", f"{TAG}_medium", sev="medium")
    fm, _ = await L.get_or_create_finding(obs_m)
    act_m = await L.decide_and_act(fm, autoexec_allowed=True)
    todo_m = await db.admin_todos.find_one({"finding_key": fm["composite_key"]})
    ap_m = await db.admin_approvals.find_one({"finding_key": fm["composite_key"], "status": "pending"})
    fmdoc = await db.admin_ai_findings.find_one({"composite_key": fm["composite_key"]})
    check("MEDIUM → human approval created", act_m["action"]["type"] == "approval" and act_m["human_gate"])
    check("MEDIUM → NO auto todo (gate preserved)", todo_m is None)
    check("MEDIUM → approval pending exists", ap_m is not None)
    check("MEDIUM → finding stays open (awaiting human)", fmdoc["status"] == "open")

    # 6) Activity read-model
    metrics = await A.compute_activity_metrics()
    q = await A.build_action_queue()
    check("metrics knowledge_records >= 1 (real)", (metrics.get("knowledge_records_from_verified_outcomes") or 0) >= 1)
    check("metrics has resolution + escalation rates keys", "autonomous_resolution_rate_pct" in metrics and "human_escalation_rate_pct" in metrics)
    cats = {it["category"] for it in q["queue"]}
    check("queue categorizes (has NEEDS_HUMAN + LEARNED)", "NEEDS_HUMAN" in cats and "LEARNED" in cats)
    check("queue MEDIUM approval shows as NEEDS_HUMAN",
          any(it.get("finding_key") == fm["composite_key"] and it["category"] == "NEEDS_HUMAN" for it in q["queue"]))

    await cleanup()

    passed = sum(1 for _, c, _ in results if c)
    total = len(results)
    print(f"\n=== P2 CLOSED-LOOP: {passed}/{total} PASS ===")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
