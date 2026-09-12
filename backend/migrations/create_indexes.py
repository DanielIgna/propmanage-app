"""Phase 1 · TD-07 — Indexuri Mongo pe query-urile fierbinți (idempotent).
Rulare: python migrations/create_indexes.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from motor.motor_asyncio import AsyncIOMotorClient

INDEXES = [
    ("users", [("role", 1), ("verified", 1)]),
    ("users", [("service_categories", 1)]),
    ("users", [("medic_suspended", 1)]),
    ("users", [("email", 1)]),
    ("requests", [("status", 1), ("created_at", -1)]),
    ("requests", [("category", 1), ("created_at", -1)]),
    ("requests", [("client_id", 1)]),
    ("requests", [("specialist_id", 1)]),
    ("disputes", [("status", 1), ("created_at", -1)]),
    ("notifications", [("user_id", 1), ("read", 1), ("created_at", -1)]),
    ("transactions", [("user_id", 1), ("created_at", -1)]),
    ("price_observations", [("category", 1), ("city", 1)]),
    ("construction_taxonomy", [("parent_id", 1)]),
    ("construction_taxonomy", [("is_publicly_visible", 1)]),
    ("orchestrator_ledger", [("ts", -1)]),
    ("orchestrator_ledger", [("playbook_id", 1), ("ts", -1)]),
    ("orchestrator_signals", [("kind", 1), ("ts", -1)]),
    ("orchestrator_retry_queue", [("status", 1), ("next_retry_at", 1)]),
    ("analytics_events", [("created_at", -1)]),
    ("admin_audit_log", [("created_at", -1)]),
    ("qa_sessions", [("status", 1), ("created_at", -1)]),
    ("properties", [("owner_id", 1)]),
]


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for coll, keys in INDEXES:
        try:
            name = await db[coll].create_index(keys)
            print(f"  {coll}: {name}")
        except Exception as e:
            print(f"  {coll} {keys}: SKIP ({str(e)[:60]})")
    print(f"DONE: {len(INDEXES)} indexuri asigurate")


if __name__ == "__main__":
    asyncio.run(main())
