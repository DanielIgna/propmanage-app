"""Migrare reversibilă (Remediere Task 8 · Iun 2026).

Elimină doc-ul MORT db.design_tokens {_id:"design_tokens"} scris de dead-path-ul
Task 8. Runtime-ul folosește EXCLUSIV {_id:"active"} (Design Studio).

Siguranță:
- backup complet în db.migration_backups înainte de delete (reversibil)
- pre/post counts verificate
- idempotent (rulări repetate = no-op)

Rollback: reinserați `payload` din migration_backups doc cu
  migration = "remove_dead_design_tokens_doc".
"""
import asyncio
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MIGRATION_ID = "remove_dead_design_tokens_doc"


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    pre_count = await db.design_tokens.count_documents({})
    dead = await db.design_tokens.find_one({"_id": "design_tokens"})
    active = await db.design_tokens.find_one({"_id": "active"})

    print(f"PRE:  design_tokens docs = {pre_count}")
    print(f"      _id='active' exists      = {bool(active)}")
    print(f"      _id='design_tokens' dead = {bool(dead)}")

    if not active:
        print("ABORT: doc-ul canonic _id='active' lipsește — nu șterg nimic.")
        return

    if not dead:
        print("NO-OP: doc-ul mort nu (mai) există. Migrare deja aplicată.")
        return

    await db.migration_backups.insert_one({
        "migration": MIGRATION_ID,
        "collection": "design_tokens",
        "payload": dead,
        "reason": "Task 8 dead write path — runtime consumă doar _id='active' (design_studio)",
        "backed_up_at": datetime.now(timezone.utc).isoformat(),
        "rollback": "db.design_tokens.insert_one(payload)",
    })
    res = await db.design_tokens.delete_one({"_id": "design_tokens"})
    post_count = await db.design_tokens.count_documents({})
    post_active = await db.design_tokens.find_one({"_id": "active"})

    print(f"DELETED: {res.deleted_count} doc (backup în migration_backups)")
    print(f"POST: design_tokens docs = {post_count} (expected {pre_count - 1})")
    print(f"      _id='active' intact = {bool(post_active)}")
    assert res.deleted_count == 1
    assert post_count == pre_count - 1
    assert post_active is not None
    print("MIGRATION OK")


if __name__ == "__main__":
    asyncio.run(main())
