"""E2E regression for the 3 production fixes:
#2 materialize (valid JSON + idempotent), #3 governance/budget enforcement, and
prep for #1 deep-link UI test (leaves a real SAFE todo + MEDIUM approval).
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from db import db
from autonomy.loop import run_loop_tick
from routes.autonomy import materialize_recommendations

PROBE = "/__loop_probe__"
TAG = "loopprobe_"
PROBE_KEY = f"analytics_loop:high_bounce_page:{PROBE}"
CLIENT_KEY = "analytics_loop:request_flow_abandonment:/client"


async def inject_bounce(n=35):
    day = datetime.now(timezone.utc).date().isoformat()
    docs = [{"session_id": f"{TAG}b_{i}_{uuid.uuid4().hex[:6]}", "visitor_id": f"{TAG}bv_{i}",
             "entry_path": PROBE, "pageviews": 1, "duration_ms": 3000, "day": day,
             "started_at": datetime.now(timezone.utc).isoformat(), "source": "direct"} for i in range(n)]
    await db.analytics_sessions.insert_many(docs)


async def set_autopilot(enabled: bool):
    await db.self_driving_settings.update_one({"key": "main"}, {"$set": {"low_risk_autopilot": enabled}}, upsert=True)


async def main():
    print("=== FIX #2: materialize valid JSON + idempotent ===")
    r1 = await materialize_recommendations(max_items=6)
    assert r1.get("ok") is True, "materialize must return ok"
    inj1 = r1["counts"]["injected"]
    r2 = await materialize_recommendations(max_items=6)
    inj2 = r2["counts"]["injected"]
    print(f"run1 injected={inj1} skipped={r1['counts']['skipped']} | run2 injected={inj2} skipped={r2['counts']['skipped']}")
    assert inj2 == 0, "second materialize must create NO duplicates (idempotent)"
    print("FIX #2 OK — idempotent, valid JSON, no crash")

    print("\n=== FIX #3: governance/budget — kill-switch enforced ===")
    await inject_bounce(35)
    await set_autopilot(False)  # kill-switch OFF
    rg = await run_loop_tick(triggered_by="e2e_gov_off")
    probe_step = next((s for s in rg["steps"] if s.get("route") == PROBE), None)
    probe_todo = await db.admin_todos.count_documents({"finding_key": PROBE_KEY, "done": False})
    probe_finding = await db.admin_ai_findings.find_one({"composite_key": PROBE_KEY}, {"_id": 0, "status": 1})
    print("governance:", rg["governance"], "| outcome:", rg["outcome"], "| blocked:", rg["actions_taken"].get("blocked_governance"))
    print("probe step decision:", probe_step and probe_step.get("decision"), "| probe todos:", probe_todo, "| finding:", probe_finding)
    assert rg["governance"]["low_risk_autopilot"] is False
    assert rg["actions_taken"].get("blocked_governance", 0) >= 1, "SAFE must be blocked by governance"
    assert probe_todo == 0, "NO todo may be created while autopilot OFF"
    assert probe_finding and probe_finding["status"] == "open", "finding stays open when blocked"
    assert probe_step and probe_step["action"]["type"] == "blocked_governance"

    print("\n=== FIX #3: re-enable → SAFE executes ===")
    await set_autopilot(True)
    re_run = await run_loop_tick(triggered_by="e2e_gov_on")
    probe_todo2 = await db.admin_todos.find_one({"finding_key": PROBE_KEY, "done": False}, {"_id": 0, "id": 1})
    probe_finding2 = await db.admin_ai_findings.find_one({"composite_key": PROBE_KEY}, {"_id": 0, "status": 1})
    print("after re-enable -> probe todo:", probe_todo2, "| finding:", probe_finding2)
    assert probe_todo2, "SAFE must create a todo once autopilot re-enabled"
    assert probe_finding2["status"] == "resolved"

    # artifacts for the UI deep-link test (#1)
    client_approval = await db.admin_approvals.find_one({"finding_key": CLIENT_KEY, "status": "pending"}, {"_id": 0, "id": 1})
    print("\n=== ARTIFACTS FOR UI DEEP-LINK TEST ===")
    print("SAFE_TODO_ID=", probe_todo2["id"])
    print("MEDIUM_APPROVAL_ID=", client_approval and client_approval["id"])
    print("\nALL BACKEND FIX ASSERTIONS PASSED ✅")


asyncio.run(main())
