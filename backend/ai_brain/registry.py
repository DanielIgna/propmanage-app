"""AI Brain · Knowledge Registry — stochează și interoghează informațiile descoperite.

Un snapshot per kind în db.ai_brain_registry (upsert) + istoric rulări în db.ai_brain_runs.
"""
from datetime import datetime, timezone

from db import db

KINDS = ("modules", "routes", "pages", "components", "apis", "services", "roles", "menus")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def store(kind: str, data, run_id: str) -> int:
    count = len(data) if isinstance(data, list) else sum(
        len(v) if isinstance(v, (list, dict)) else 1 for v in data.values()) if isinstance(data, dict) else 1
    await db.ai_brain_registry.update_one(
        {"kind": kind},
        {"$set": {"kind": kind, "data": data, "count": count, "run_id": run_id, "updated_at": _now()}},
        upsert=True)
    return count


async def get(kind: str, q: str = "", limit: int = 200) -> dict:
    doc = await db.ai_brain_registry.find_one({"kind": kind}, {"_id": 0})
    if not doc:
        return {"kind": kind, "count": 0, "data": [], "updated_at": None}
    data = doc["data"]
    if q and isinstance(data, list):
        ql = q.lower()
        data = [d for d in data if ql in str(d).lower()]
    if isinstance(data, list):
        data = data[:limit]
    return {"kind": kind, "count": doc["count"], "data": data,
            "updated_at": doc["updated_at"], "filtered": bool(q)}


async def counts() -> dict:
    out = {}
    async for doc in db.ai_brain_registry.find({}, {"kind": 1, "count": 1, "updated_at": 1}):
        out[doc["kind"]] = doc["count"]
    return out
