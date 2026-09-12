"""P1 Decontamination — regression proof (real DB, self-cleaning).

Verifies:
 1. Autonomy AI sub-score EXCLUDES synthetic seed docs/memories.
 2. AI-Health effectiveness + concierge EXCLUDE synthetic seed rows.
 3. run_auto_tune_orchestration injects ZERO synthetic data and is flagged
    decontaminated (no score inflation on run).

Run:  python3 -m tests.test_decontamination_p1
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import db
from autonomy.engine import _score_ai
from routes.admin_ai import _compute_effectiveness_score, _compute_concierge_score
from routes.autonomy import run_auto_tune_orchestration

MARK = f"p1test_{uuid.uuid4().hex[:8]}"
results = []


def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")


async def cleanup():
    await db.ai_documents.delete_many({"_p1_test": MARK})
    await db.ai_memories.delete_many({"_p1_test": MARK})
    await db.admin_ai_repair_suggestions.delete_many({"_p1_test": MARK})
    await db.concierge_messages.delete_many({"_p1_test": MARK})


async def main():
    now = datetime.now(timezone.utc).isoformat()
    await cleanup()

    # BEFORE
    ai_before = await _score_ai()
    eff_before = await _compute_effectiveness_score(7)
    con_before = await _compute_concierge_score(7)

    # Inject synthetic (tagged) rows that WOULD inflate if counted.
    await db.ai_documents.insert_many([
        {"id": uuid.uuid4().hex, "title": f"{MARK} seed doc {i}", "source": "autonomy_seed", "_p1_test": MARK, "created_at": now}
        for i in range(30)
    ])
    await db.ai_memories.insert_many([
        {"id": uuid.uuid4().hex, "summary": f"{MARK} seed mem {i}", "source": "autonomy_seed:admin_actions_log", "_p1_test": MARK, "created_at": now}
        for i in range(120)
    ])
    await db.admin_ai_repair_suggestions.insert_many([
        {"id": uuid.uuid4().hex, "status": "applied", "synthetic_for_score_seed": True, "_p1_test": MARK, "created_at": now}
        for _ in range(20)
    ])
    await db.concierge_messages.insert_many([
        {"id": uuid.uuid4().hex, "role": "assistant", "blocked": False, "synthetic_for_score_seed": True, "_p1_test": MARK, "created_at": now}
        for _ in range(25)
    ])

    # AFTER injecting synthetic — decontaminated calc must be UNCHANGED.
    ai_after = await _score_ai()
    eff_after = await _compute_effectiveness_score(7)
    con_after = await _compute_concierge_score(7)

    check("AI sub-score ignores 30 synthetic docs + 120 synthetic memories",
          ai_after["score"] == ai_before["score"],
          f"(before={ai_before['score']} after={ai_after['score']})")
    check("AI raw docs_count unchanged by synthetic docs",
          ai_after["signals"]["raw"]["docs_count"] == ai_before["signals"]["raw"]["docs_count"],
          f"(docs={ai_after['signals']['raw']['docs_count']})")
    check("AI raw exposes excluded_seed_docs count",
          ai_after["signals"]["raw"]["excluded_seed_docs"] >= 30)
    check("Effectiveness score ignores 20 synthetic applied decisions",
          eff_after["score"] == eff_before["score"],
          f"(before={eff_before['score']} after={eff_after['score']})")
    check("Concierge score ignores 25 synthetic non-blocked messages",
          con_after["score"] == con_before["score"],
          f"(before={con_before['score']} after={con_after['score']})")

    # auto-tune must NOT create synthetic data and must flag decontaminated.
    seed_docs_pre = await db.ai_documents.count_documents({"source": "autonomy_seed", "_p1_test": {"$ne": MARK}})
    rep = await run_auto_tune_orchestration(triggered_by="p1_regression_test")
    seed_docs_post = await db.ai_documents.count_documents({"source": "autonomy_seed", "_p1_test": {"$ne": MARK}})
    real_synth_repair = await db.admin_ai_repair_suggestions.count_documents({"synthetic_for_score_seed": True, "_p1_test": {"$ne": MARK}})
    real_synth_con = await db.concierge_messages.count_documents({"synthetic_for_score_seed": True, "_p1_test": {"$ne": MARK}})

    check("auto-tune flagged decontaminated", rep.get("decontaminated") is True)
    check("auto-tune injected ZERO new seed docs", seed_docs_post == seed_docs_pre, f"(pre={seed_docs_pre} post={seed_docs_post})")
    check("auto-tune left ZERO synthetic repair rows (excl. this test)", real_synth_repair == 0)
    check("auto-tune left ZERO synthetic concierge rows (excl. this test)", real_synth_con == 0)
    check("auto-tune delta_general == 0 (no inflation)", rep.get("delta_general") == 0.0, f"(delta={rep.get('delta_general')})")
    steps = {s["name"]: s["status"] for s in rep.get("steps", [])}
    check("auto-tune synthetic_seeding step is skipped", steps.get("synthetic_seeding") == "skipped")
    check("auto-tune mass_dismiss_findings step is skipped", steps.get("mass_dismiss_findings") == "skipped")

    await cleanup()

    passed = sum(1 for _, c, _ in results if c)
    total = len(results)
    print(f"\n=== P1 DECONTAMINATION: {passed}/{total} PASS ===")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
