"""Rădăcini — jobul de retenție `scripts/radacini_retention.py` (direct pe bază, fără backend pornit).

    ./venv/bin/python -m pytest tests/test_radacini_retention.py -q --noconftest

Documentele de test au câmpul `retention_test` = „TEST-RAD-…” și se șterg la final (testul rulează jobul doar
pe ele, prin `scope`).
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from scripts import radacini_retention as ret

NOW = datetime(2026, 10, 27, tzinfo=timezone.utc)
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
SCOPE = {"retention_test": TAG}
COLLS = ("radacini_location_access_log", "radacini_land_requests", "radacini_request_messages",
         "radacini_listings", "radacini_reports", "notifications", "radacini_households", "radacini_members")


def ago(days: int) -> str:
    return (NOW - timedelta(days=days)).isoformat()


def test_adult_minors_and_inactive():
    hh = [{"_id": "h1", "members": [{"is_minor": True, "birth_year": 2008}, {"is_minor": True, "birth_year": 2016}]},
          {"_id": "h2", "members": [{"is_minor": False}]}]
    assert ret.adult_minors(hh, 2026) == [{"household_id": "h1", "count": 1}]
    members = [{"user_id": "a"}, {"user_id": "b"}, {"user_id": "c"}]
    seen = {"a": ago(800), "b": ago(10)}
    assert ret.inactive_users(members, seen, ago(730)) == ["a"]
    assert ret.radacini_notifications([{"_id": 1, "link": "/radacini/x"}, {"_id": 2, "link": "/app"}]) == [1]


async def _scenario():
    from db import db

    async def ins(coll, doc):
        return (await db[coll].insert_one({**doc, **SCOPE})).inserted_id

    try:
        await ins("radacini_location_access_log", {"parcel_id": "p", "at": ago(400)})
        await ins("radacini_location_access_log", {"parcel_id": "p", "at": ago(10)})
        old_req = await ins("radacini_land_requests", {"status": "rejected", "updated_at": ago(800)})
        await ins("radacini_request_messages", {"request_id": str(old_req), "body": "x"})
        await ins("radacini_land_requests", {"status": "accepted", "agreement_id": "a1", "updated_at": ago(800)})
        await ins("radacini_land_requests", {"status": "sent", "updated_at": ago(800)})
        await ins("radacini_listings", {"status": "closed", "updated_at": ago(800)})
        await ins("radacini_listings", {"status": "active", "updated_at": ago(800)})
        rep = await ins("radacini_reports", {"status": "resolved", "resolved_at": ago(800),
                                             "reporter_id": "u", "reporter_name": "TEST-RAD"})
        await ins("radacini_members", {"user_id": "u-ret"})
        await ins("notifications", {"user_id": "u-ret", "link": "/radacini/x", "created_at": ago(400)})
        await ins("notifications", {"user_id": "u-ret", "link": "/dashboard", "created_at": ago(400)})
        await ins("radacini_households", {"owner_user_id": "u", "members": [
            {"name": "TEST", "is_minor": True, "birth_year": NOW.year - 18}]})

        report = await ret.run(apply=False, now=NOW, scope=SCOPE)
        counts = {k: v["count"] for k, v in report.items()}
        assert counts == {"location_access_log": 1, "land_requests": 1, "listings": 1, "reports": 1,
                          "notifications": 1, "adult_minors": 1, "inactive_accounts": 0}
        assert await db.radacini_location_access_log.count_documents(SCOPE) == 2  # raportul nu modifică

        applied = await ret.run(apply=True, now=NOW, scope=SCOPE)
        assert applied["land_requests"]["cascade"] == 1
        assert await db.radacini_location_access_log.count_documents(SCOPE) == 1
        assert await db.radacini_land_requests.count_documents(SCOPE) == 2
        assert await db.radacini_request_messages.count_documents(SCOPE) == 0
        assert await db.radacini_listings.count_documents(SCOPE) == 1
        assert await db.notifications.count_documents(SCOPE) == 1
        assert await db.radacini_households.count_documents(SCOPE) == 1  # minorii: doar raport
        doc = await db.radacini_reports.find_one({"_id": rep})
        assert "reporter_id" not in doc and "reporter_name" not in doc and doc["status"] == "resolved"
    finally:
        for c in COLLS:
            await db[c].delete_many(SCOPE)


def test_retention_job_on_test_data():
    asyncio.run(_scenario())
