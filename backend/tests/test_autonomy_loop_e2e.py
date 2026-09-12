"""Controlled E2E for the Operational Autonomy Loop (FN-021).
Covers: SAFE→todo, MEDIUM→approval, idempotency (no dup on re-run), LEARN (auto-resolve).
Injects controlled analytics signals (tagged 'loopprobe_'), runs the real loop, verifies
DB artifacts, then cleans up ALL injected data + test artifacts.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app/backend")
from db import db
from autonomy.loop import run_loop_tick

PROBE = "/__loop_probe__"
TAG = "loopprobe_"
PROBE_KEY = f"analytics_loop:high_bounce_page:{PROBE}"
CLIENT_KEY = "analytics_loop:request_flow_abandonment:/client"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def inject_bounce(n=35):
    day = datetime.now(timezone.utc).date().isoformat()
    docs = [{
        "session_id": f"{TAG}b_{i}_{uuid.uuid4().hex[:6]}", "visitor_id": f"{TAG}bv_{i}",
        "entry_path": PROBE, "pageviews": 1, "duration_ms": 3000, "day": day,
        "started_at": now_iso(), "source": "direct",
    } for i in range(n)]
    await db.analytics_sessions.insert_many(docs)


async def inject_conversion(n=14):
    """Visitors with BOTH request_started + request_created → raises /client conversion > 40%."""
    day = datetime.now(timezone.utc).date().isoformat()
    docs = [{
        "session_id": f"{TAG}c_{i}_{uuid.uuid4().hex[:6]}", "visitor_id": f"{TAG}cv_{i}",
        "entry_path": "/client", "pageviews": 3, "duration_ms": 30000, "day": day,
        "started_at": now_iso(), "source": "direct",
        "intent_client_flow_opened": True, "intent_request_started": True, "intent_request_created": True,
    } for i in range(n)]
    await db.analytics_sessions.insert_many(docs)


async def clear_injected():
    r = await db.analytics_sessions.delete_many({"session_id": {"$regex": f"^{TAG}"}})
    return r.deleted_count


async def cleanup_test_artifacts():
    await db.admin_ai_findings.delete_many({"composite_key": PROBE_KEY})
    await db.admin_todos.delete_many({"finding_key": PROBE_KEY})


async def count_todos(key):
    return await db.admin_todos.count_documents({"source": "analytics_loop", "finding_key": key})


async def main():
    print("=== SETUP: inject bounce signal (35 sessions on probe) ===")
    await inject_bounce(35)

    print("\n=== RUN #1 (SAFE + MEDIUM should fire) ===")
    r1 = await run_loop_tick(triggered_by="e2e_test_1")
    print("outcome:", r1["outcome"], "findings_created:", r1["findings_created"], "actions:", r1["actions_taken"])
    probe_finding = await db.admin_ai_findings.find_one({"composite_key": PROBE_KEY}, {"_id": 0, "status": 1, "autonomy_action": 1, "severity": 1})
    client_finding = await db.admin_ai_findings.find_one({"composite_key": CLIENT_KEY}, {"_id": 0, "status": 1, "autonomy_action": 1})
    probe_todos = await count_todos(PROBE_KEY)
    client_approval = await db.admin_approvals.find_one({"finding_key": CLIENT_KEY, "status": "pending"}, {"_id": 0, "id": 1, "action": 1, "status": 1})
    print("SAFE probe finding:", probe_finding, "| probe todos:", probe_todos)
    print("MEDIUM client finding:", client_finding, "| client approval:", client_approval)
    assert probe_finding and probe_finding["status"] == "resolved", "SAFE finding must be resolved"
    assert probe_todos == 1, "SAFE must create exactly 1 todo"
    assert client_finding and client_finding["status"] == "open", "MEDIUM finding must stay open"
    assert client_approval, "MEDIUM must create a pending approval"

    print("\n=== RUN #2 (IDEMPOTENCY: no duplicates) ===")
    r2 = await run_loop_tick(triggered_by="e2e_test_2")
    probe_todos2 = await count_todos(PROBE_KEY)
    client_approvals2 = await db.admin_approvals.count_documents({"finding_key": CLIENT_KEY, "status": "pending"})
    probe_findings2 = await db.admin_ai_findings.count_documents({"composite_key": PROBE_KEY})
    client_findings2 = await db.admin_ai_findings.count_documents({"composite_key": CLIENT_KEY})
    print("after run2 -> probe todos:", probe_todos2, "| client pending approvals:", client_approvals2,
          "| probe findings:", probe_findings2, "| client findings:", client_findings2)
    assert probe_todos2 == 1, "no duplicate todo on re-run"
    assert client_approvals2 == 1, "no duplicate approval on re-run"
    assert probe_findings2 == 1 and client_findings2 == 1, "no duplicate findings on re-run"
    print("IDEMPOTENCY OK — findings_created run2:", r2["findings_created"], "actions:", r2["actions_taken"])

    print("\n=== HUMAN APPROVAL (MEDIUM gate) — approve the client proposal ===")
    from routes.admin_approvals import _exec_registered
    ap = await db.admin_approvals.find_one({"finding_key": CLIENT_KEY, "status": "pending"})
    exec_res = await _exec_registered(ap["action"], ap.get("payload") or {}, {"email": "admin@propmanage.io", "role": "admin"})
    await db.admin_approvals.update_one({"id": ap["id"]}, {"$set": {"status": "executed"}})
    client_finding_after = await db.admin_ai_findings.find_one({"composite_key": CLIENT_KEY}, {"_id": 0, "status": 1})
    print("approval exec result:", exec_res, "| client finding after approve:", client_finding_after)
    assert client_finding_after["status"] == "resolved", "approved MEDIUM must resolve finding"

    print("\n=== LEARN (signal disappears → auto-resolve) ===")
    # Re-open a fresh MEDIUM by clearing resolution, then clear the signal and re-run.
    await db.admin_ai_findings.update_one({"composite_key": CLIENT_KEY},
        {"$set": {"status": "open"}, "$unset": {"resolved_at": "", "autonomy_action": ""}})
    await inject_conversion(16)  # push /client conversion above 40% → abandonment signal clears
    r3 = await run_loop_tick(triggered_by="e2e_test_learn")
    client_finding_learn = await db.admin_ai_findings.find_one({"composite_key": CLIENT_KEY}, {"_id": 0, "status": 1, "resolution_note": 1})
    print("LEARN result:", r3["learned"], "| client finding:", client_finding_learn)
    assert r3["learned"]["auto_resolved"] >= 1 or client_finding_learn["status"] == "resolved", "LEARN must auto-resolve vanished signal"

    print("\n=== CLEANUP ===")
    deleted = await clear_injected()
    await cleanup_test_artifacts()
    # remove approvals + todos created for the client key during test
    await db.admin_approvals.delete_many({"finding_key": CLIENT_KEY})
    await db.admin_todos.delete_many({"finding_key": CLIENT_KEY})
    await db.admin_ai_findings.delete_many({"composite_key": {"$in": [PROBE_KEY, CLIENT_KEY]}})
    await db.autonomy_loop_runs.delete_many({"triggered_by": {"$regex": "^e2e_test"}})
    print("cleaned injected sessions:", deleted, "+ test findings/todos/approvals/runs")
    print("\nALL E2E ASSERTIONS PASSED ✅")


asyncio.run(main())
