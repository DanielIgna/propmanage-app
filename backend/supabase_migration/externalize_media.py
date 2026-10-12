"""One-off: move existing base64 media (media_store.MEDIA_FIELDS) from documents to Storage.

Run AFTER deploying routes/media.py (the new links must resolve). Idempotent; --dry-run only counts.
    ./venv/bin/python supabase_migration/externalize_media.py [--dry-run]
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import db  # noqa: E402
from media_store import MEDIA_FIELDS, externalize_doc  # noqa: E402


async def main(dry: bool) -> None:
    for coll_name, fields in MEDIA_FIELDS.items():
        coll = db[coll_name]
        moved = 0
        async for doc in coll.find({"$or": [{f: {"$exists": True}} for f in fields]}, {f: 1 for f in fields}):
            if "base64" not in str([doc.get(f) for f in fields]) and not any(
                    isinstance(i, dict) and i.get("data") for f in fields for i in (doc.get(f) or []) if isinstance(doc.get(f), list)):
                continue
            if dry:
                moved += 1
                continue
            new = await externalize_doc(coll_name, doc)
            changed = {f: new[f] for f in fields if new and f in new and new[f] != doc.get(f)}
            if changed:
                await coll.update_one({"_id": doc["_id"]}, {"$set": changed})
                moved += 1
        print(f"{coll_name}: {'would move' if dry else 'moved'} {moved} document(s)")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
