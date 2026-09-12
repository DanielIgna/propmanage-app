"""PropBenefits · Benefits Wallet (PB-001.1) — ledger de beneficii și drepturi.

NU sunt bani, NU sunt criptomonede. Colecție: pb_ledger.
Statusuri: available · used · expired · pending_activation.
"""
import uuid
from datetime import datetime, timezone, timedelta

from db import db


def _now():
    return datetime.now(timezone.utc)


def _iso(dt=None) -> str:
    return (dt or _now()).isoformat()


async def grant(user_id: str, benefit: dict, source: str, campaign_id: str = None,
                status: str = "available", expires_days: int = None) -> dict:
    exp_days = expires_days or benefit.get("expires_days") or 90
    entry = {
        "id": uuid.uuid4().hex[:12],
        "user_id": user_id,
        "benefit_key": benefit.get("benefit_key", "generic"),
        "title": benefit.get("title", "Beneficiu"),
        "instructions": benefit.get("instructions", ""),
        "value_estimate": float(benefit.get("value_estimate", 0)),
        "campaign_id": campaign_id,
        "source": source,
        "status": status,
        "granted_at": _iso(),
        "expires_at": _iso(_now() + timedelta(days=exp_days)),
        "used_at": None,
        "history": [{"at": _iso(), "event": "granted", "source": source}],
    }
    await db.pb_ledger.insert_one({**entry})
    return entry


async def use_benefit(user_id: str, benefit_id: str) -> dict:
    doc = await db.pb_ledger.find_one({"id": benefit_id, "user_id": user_id})
    if not doc:
        return {"error": "not_found"}
    if doc["status"] != "available":
        return {"error": f"status_{doc['status']}"}
    if doc.get("expires_at") and doc["expires_at"] < _iso():
        await db.pb_ledger.update_one({"id": benefit_id}, {"$set": {"status": "expired"},
                                      "$push": {"history": {"at": _iso(), "event": "expired"}}})
        return {"error": "status_expired"}
    await db.pb_ledger.update_one({"id": benefit_id}, {
        "$set": {"status": "used", "used_at": _iso()},
        "$push": {"history": {"at": _iso(), "event": "used"}}})
    return {"ok": True}


async def wallet_summary(user_id: str) -> dict:
    now = _iso()
    items = await db.pb_ledger.find({"user_id": user_id}, {"_id": 0}).sort("granted_at", -1).to_list(200)
    buckets = {"available": [], "used": [], "expired": [], "pending_activation": []}
    for it in items:
        st = it["status"]
        if st == "available" and it.get("expires_at") and it["expires_at"] < now:
            st = "expired"
        buckets.setdefault(st, []).append(it)
    return {
        "available": buckets["available"], "used": buckets["used"],
        "expired": buckets["expired"], "pending": buckets["pending_activation"],
        "counts": {k: len(v) for k, v in buckets.items()},
        "total_value_available": round(sum(i.get("value_estimate", 0) for i in buckets["available"]), 2),
    }


async def expire_tick() -> int:
    now = _iso()
    res = await db.pb_ledger.update_many(
        {"status": "available", "expires_at": {"$lt": now}},
        {"$set": {"status": "expired"}, "$push": {"history": {"at": now, "event": "expired"}}})
    return res.modified_count


async def user_claims_for_campaign(user_id: str, campaign_id: str) -> int:
    return await db.pb_ledger.count_documents({"user_id": user_id, "campaign_id": campaign_id})
