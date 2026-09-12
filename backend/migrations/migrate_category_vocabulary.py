"""Phase 1 · TD-03 — Migrare vocabular istoric de categorii (one-off, cu backup).

painting→zugravit, carpentry→tamplarie, gardening→amenajari_exterioare,
cleaning→handyman, appliance_repair→handyman.
Backup: câmpurile originale în `migration_backups` înainte de modificare.
Rulare: python migrations/migrate_category_vocabulary.py
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient

MAPPING = {
    "painting": "zugravit",
    "carpentry": "tamplarie",
    "gardening": "amenajari_exterioare",
    "cleaning": "handyman",
    "appliance_repair": "handyman",
}


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    old_values = list(MAPPING.keys())
    q = {"role": "specialist", "$or": [
        {"specialty": {"$in": old_values}},
        {"service_categories": {"$in": old_values}},
    ]}
    migrated = 0
    async for u in db.users.find(q):
        await db.migration_backups.insert_one({
            "migration": "category_vocabulary_v1",
            "user_id": str(u["_id"]),
            "original": {"specialty": u.get("specialty"), "service_categories": u.get("service_categories")},
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        new_specialty = MAPPING.get(u.get("specialty"), u.get("specialty"))
        new_cats = list(dict.fromkeys(MAPPING.get(c, c) for c in (u.get("service_categories") or [])))
        await db.users.update_one(
            {"_id": u["_id"]},
            {"$set": {"specialty": new_specialty, "service_categories": new_cats}},
        )
        migrated += 1
        print(f"  migrated {u.get('email')}: {u.get('specialty')}→{new_specialty}, cats→{new_cats}")
    print(f"DONE: {migrated} specialiști migrați (backup în migration_backups)")

    # Requests istorice cu categorii vechi (afectează Observatory/analytics)
    for old, new in MAPPING.items():
        r = await db.requests.update_many({"category": old}, {"$set": {"category": new, "category_migrated_from": old}})
        if r.modified_count:
            print(f"  requests {old}→{new}: {r.modified_count}")


if __name__ == "__main__":
    asyncio.run(main())
