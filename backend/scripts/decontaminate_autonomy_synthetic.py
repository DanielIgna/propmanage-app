"""P1 — Autonomy metric decontamination: remove EXPLICITLY-TAGGED synthetic rows.

Deletes ONLY rows fabricated by the auto-tune/boost seeders to inflate scores:
  - ai_documents          where source == "autonomy_seed"
  - ai_memories           where source startswith "autonomy_seed"
  - admin_ai_repair_suggestions where synthetic_for_score_seed == True
  - concierge_messages    where synthetic_for_score_seed == True

NEVER touches real user data, real findings, real requests, users, payments.
Every deletion is recorded in `autonomy_decontamination_log` (audit trail).

Dry-run by default. Pass apply=True to actually delete.

    python3 -m scripts.decontaminate_autonomy_synthetic          # dry-run
    python3 -m scripts.decontaminate_autonomy_synthetic --apply  # execute
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import db

TARGETS = [
    ("ai_documents", {"source": "autonomy_seed"}),
    ("ai_memories", {"source": {"$regex": "^autonomy_seed"}}),
    ("admin_ai_repair_suggestions", {"synthetic_for_score_seed": True}),
    ("concierge_messages", {"synthetic_for_score_seed": True}),
]


async def run(apply: bool = False, actor: str = "script") -> dict:
    report = {"apply": apply, "actor": actor, "at": datetime.now(timezone.utc).isoformat(), "collections": []}
    batch_id = uuid.uuid4().hex

    for coll_name, flt in TARGETS:
        coll = db[coll_name]
        count = await coll.count_documents(flt)
        entry = {"collection": coll_name, "filter": str(flt), "matched": count, "deleted": 0}

        if apply and count > 0:
            # Capture a few sample ids for the audit trail (not full docs).
            sample_ids = [str(d.get("_id")) async for d in coll.find(flt, {"_id": 1}).limit(5)]
            res = await coll.delete_many(flt)
            entry["deleted"] = res.deleted_count
            await db.autonomy_decontamination_log.insert_one({
                "batch_id": batch_id,
                "at": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
                "collection": coll_name,
                "filter": str(flt),
                "matched": count,
                "deleted": res.deleted_count,
                "sample_deleted_ids": sample_ids,
                "reason": "P1 autonomy metric decontamination — remove synthetic score-seed rows",
            })
        report["collections"].append(entry)

    report["batch_id"] = batch_id
    return report


async def main():
    apply = "--apply" in sys.argv
    rep = await run(apply=apply, actor="cli:manual")
    print("=== DECONTAMINATION", "APPLY" if apply else "DRY-RUN", "===")
    for c in rep["collections"]:
        print(f"  {c['collection']}: matched={c['matched']} deleted={c['deleted']}")
    print("batch_id:", rep["batch_id"])
    if not apply:
        print("\n(dry-run — nothing deleted. Re-run with --apply to execute.)")


if __name__ == "__main__":
    asyncio.run(main())
