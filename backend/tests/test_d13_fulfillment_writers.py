"""D13 slice 3 — production assignment writers use commit_assignment.

Calls the route functions and reads the stored documents.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException

from db import db
from fulfillment_commit import (
    ADMIN,
    AUTHORITY_AUTO_MATCH,
    AUTHORITY_DIRECT_REBOOK,
    AUTO_MATCH,
    CAMPAIGN,
    CLIENT_SELECTION,
    DIRECT_REBOOK,
    FALLBACK,
    MULTI_OFFER,
)
from health_repair import _repair_marketplace, _repair_operations
from routes.admin import execute_auto_match
from routes.community_buildings import accept_campaign_offer
from routes.demo_time_machine import sim_accept
from routes.marketplace_offers import OfferIn, accept_offer, submit_offer
from routes.operations_center import assign_gap
from routes.requests import accept_request


def _detach_motor_loop(loop):
    from db import client

    cached = getattr(client, "_io_loop", None)
    if cached is loop or (cached is not None and cached.is_closed()):
        client._io_loop = None


@pytest.fixture(scope="module")
def eloop():
    loop = asyncio.new_event_loop()
    _detach_motor_loop(loop)
    yield loop
    _detach_motor_loop(loop)
    if not loop.is_closed():
        loop.close()


def _run(eloop, coro):
    return eloop.run_until_complete(coro)


class _World:
    def __init__(self):
        self.tag = str(ObjectId())
        self.client_id = ObjectId()
        self.spec_id = ObjectId()
        self.other_spec_id = ObjectId()
        self.admin_id = ObjectId()
        self.request_ids = []
        self.offer_ids = []
        self.gap_ids = []
        self.client = {
            "id": str(self.client_id),
            "name": "D13 Client",
            "role": "client",
            "email": f"d13c-{self.tag}@example.com",
        }
        self.spec = {
            "id": str(self.spec_id),
            "name": "D13 Spec",
            "role": "specialist",
            "email": f"d13s-{self.tag}@example.com",
        }
        self.other_spec = {
            "id": str(self.other_spec_id),
            "name": "D13 Other",
            "role": "specialist",
        }
        self.admin = {
            "id": str(self.admin_id),
            "name": "D13 Admin",
            "role": "admin",
            "email": f"d13a-{self.tag}@example.com",
        }

    async def setup_users(self):
        await db.users.insert_many([
            {
                "_id": self.client_id,
                "name": "D13 Client",
                "role": "client",
                "email": self.client["email"],
                "lead_credits": 0,
                "wallet_balance": 0,
            },
            {
                "_id": self.spec_id,
                "name": "D13 Spec",
                "role": "specialist",
                "email": self.spec["email"],
                "specialty": "hvac",
                "city": "Bucuresti",
                "verified": True,
                "rating": 5,
                "reviews_count": 4,
                "coverage_zones": ["d13-zone"],
                "service_categories": ["hvac"],
                "availability_status": "available",
                "lead_credits": 90,
                "wallet_balance": 200.0,
            },
            {
                "_id": self.other_spec_id,
                "name": "D13 Other",
                "role": "specialist",
                "verified": True,
                "rating": 4,
                "lead_credits": 90,
                "wallet_balance": 200.0,
            },
            {
                "_id": self.admin_id,
                "name": "D13 Admin",
                "role": "admin",
                "email": self.admin["email"],
            },
        ])

    async def cleanup(self):
        if self.request_ids:
            oids = [ObjectId(r) for r in self.request_ids]
            await db.requests.delete_many({"_id": {"$in": oids}})
            await db.activity_events.delete_many({"request_id": {"$in": self.request_ids}})
            await db.marketplace_offers.delete_many({"request_id": {"$in": self.request_ids}})
        if self.gap_ids:
            await db.specialist_gaps.delete_many({"_id": {"$in": self.gap_ids}})
        await db.users.delete_many({
            "_id": {"$in": [self.client_id, self.spec_id, self.other_spec_id, self.admin_id]},
        })
        await db.notifications.delete_many({
            "user_id": {"$in": [str(self.client_id), str(self.spec_id), str(self.other_spec_id)]},
        })
        await db.community_campaigns.delete_many({"title": f"D13W {self.tag}"})


def _request(world, strategy, **over):
    doc = {
        "_id": ObjectId(),
        "status": "open",
        "client_id": str(world.client_id),
        "specialist_id": None,
        "title": f"D13W {world.tag}",
        "category": "hvac",
        "property_zone": "d13-zone",
        "fulfillment_strategy": strategy,
        "fulfillment_strategy_started_at": "2020-01-01T00:00:00+00:00",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "direct_specialist_id": str(world.spec_id) if strategy == DIRECT_REBOOK else None,
        "lead_fee_waived": strategy == DIRECT_REBOOK,
    }
    doc.update(over)
    return doc


async def _insert_request(world, strategy, **over):
    doc = _request(world, strategy, **over)
    await db.requests.insert_one(doc)
    rid = str(doc["_id"])
    world.request_ids.append(rid)
    return rid


async def _offer(world, rid, spec_id, status="open"):
    doc = {
        "_id": ObjectId(),
        "request_id": rid,
        "specialist_id": str(spec_id),
        "specialist_name": "D13 Spec",
        "status": status,
        "fee_paid_total": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.marketplace_offers.insert_one(doc)
    oid = str(doc["_id"])
    world.offer_ids.append(oid)
    return oid


async def _saved(rid):
    return await db.requests.find_one({"_id": ObjectId(rid)})


async def _credits(spec_id):
    user = await db.users.find_one({"_id": spec_id})
    return int(user.get("lead_credits") or 0), float(user.get("wallet_balance") or 0)


def test_accept_offer_multi_offer(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            rid = await _insert_request(world, MULTI_OFFER)
            winner = await _offer(world, rid, world.spec_id)
            loser = await _offer(world, rid, world.other_spec_id)
            await accept_offer(rid, winner, world.client)
            saved = await _saved(rid)
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] == str(world.spec_id)
            assert saved["assignment_authority"] == CLIENT_SELECTION
            assert saved["assignment_version"] == 1
            assert saved["selected_offer_id"] == winner
            won = await db.marketplace_offers.find_one({"_id": ObjectId(winner)})
            lost = await db.marketplace_offers.find_one({"_id": ObjectId(loser)})
            assert won["status"] == "won"
            assert lost["status"] == "lost"
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_concurrent_accept_offer_one_winner(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            rid = await _insert_request(world, MULTI_OFFER)
            first = await _offer(world, rid, world.spec_id)
            second = await _offer(world, rid, world.other_spec_id)
            results = await asyncio.gather(
                accept_offer(rid, first, world.client),
                accept_offer(rid, second, world.client),
                return_exceptions=True,
            )
            successes = [r for r in results if not isinstance(r, Exception)]
            failures = [r for r in results if isinstance(r, HTTPException)]
            assert len(successes) == 1
            assert len(failures) == 1
            assert failures[0].status_code == 409
            saved = await _saved(rid)
            won = await db.marketplace_offers.count_documents(
                {"request_id": rid, "status": "won"},
            )
            assert won == 1
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] in (str(world.spec_id), str(world.other_spec_id))
            winner_offer = await db.marketplace_offers.find_one(
                {"request_id": rid, "status": "won"},
            )
            assert saved["specialist_id"] == winner_offer["specialist_id"]
            assert saved["selected_offer_id"] == str(winner_offer["_id"])
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_accept_offer_rejects_other_strategies(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            for strategy in (DIRECT_REBOOK, FALLBACK, AUTO_MATCH, CAMPAIGN):
                status = "assigned" if strategy == CAMPAIGN else "open"
                specialist = str(world.spec_id) if strategy == CAMPAIGN else None
                rid = await _insert_request(
                    world, strategy, status=status, specialist_id=specialist,
                )
                offer_id = await _offer(world, rid, world.other_spec_id)
                before = await _saved(rid)
                with pytest.raises(HTTPException) as exc:
                    await accept_offer(rid, offer_id, world.client)
                assert exc.value.status_code == 400
                saved = await _saved(rid)
                assert saved["specialist_id"] == before["specialist_id"]
                assert saved["status"] == before["status"]
                offer = await db.marketplace_offers.find_one({"_id": ObjectId(offer_id)})
                assert offer["status"] == "open"
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_direct_accept_assigns_and_keeps_waiver(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            rid = await _insert_request(world, DIRECT_REBOOK)
            await _offer(world, rid, world.other_spec_id)
            credits_before, wallet_before = await _credits(world.spec_id)
            result = await accept_request(rid, None, world.spec)
            saved = await _saved(rid)
            credits_after, wallet_after = await _credits(world.spec_id)
            assert result["paid_with"] == "waived"
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] == str(world.spec_id)
            assert saved["assignment_authority"] == AUTHORITY_DIRECT_REBOOK
            assert saved["assignment_version"] == 1
            assert credits_after == credits_before
            assert wallet_after == wallet_before
            leftover = await db.marketplace_offers.count_documents(
                {"request_id": rid, "status": "open"},
            )
            assert leftover == 0
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_direct_accept_rejects_multi_offer_and_other_specialist(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            public_id = await _insert_request(world, MULTI_OFFER)
            with pytest.raises(HTTPException) as public_exc:
                await accept_request(public_id, None, world.spec)
            assert public_exc.value.status_code == 400
            public_saved = await _saved(public_id)
            assert public_saved["status"] == "open"
            assert public_saved["specialist_id"] is None

            direct_id = await _insert_request(world, DIRECT_REBOOK)
            with pytest.raises(HTTPException) as other_exc:
                await accept_request(direct_id, None, world.other_spec)
            assert other_exc.value.status_code == 403
            direct_saved = await _saved(direct_id)
            assert direct_saved["status"] == "open"
            assert direct_saved["specialist_id"] is None
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_submit_offer_only_on_multi_offer(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            public_id = await _insert_request(world, MULTI_OFFER)
            await submit_offer(public_id, OfferIn(message="hello"), world.spec)
            credits, wallet = await _credits(world.spec_id)
            assert credits == 45
            assert wallet == 200.0
            offer = await db.marketplace_offers.find_one({
                "request_id": public_id,
                "specialist_id": str(world.spec_id),
            })
            assert offer["status"] == "open"
            world.offer_ids.append(str(offer["_id"]))
            saved = await _saved(public_id)
            assert saved["status"] == "open"
            assert saved["specialist_id"] is None

            for strategy in (DIRECT_REBOOK, FALLBACK, AUTO_MATCH, CAMPAIGN):
                status = "assigned" if strategy == CAMPAIGN else "open"
                specialist = str(world.spec_id) if strategy == CAMPAIGN else None
                rid = await _insert_request(
                    world, strategy, status=status, specialist_id=specialist,
                )
                before_c, before_w = await _credits(world.spec_id)
                with pytest.raises(HTTPException) as exc:
                    await submit_offer(rid, OfferIn(message="no"), world.spec)
                assert exc.value.status_code == 400
                after_c, after_w = await _credits(world.spec_id)
                assert after_c == before_c
                assert after_w == before_w
                count = await db.marketplace_offers.count_documents({
                    "request_id": rid,
                    "specialist_id": str(world.spec_id),
                })
                assert count == 0
        finally:
            await world.cleanup()

    _run(eloop, _case())


async def _run_auto_match_isolated(world, rid):
    others = []
    async for doc in db.requests.find({
        "fulfillment_strategy": AUTO_MATCH,
        "status": "open",
        "_id": {"$ne": ObjectId(rid)},
    }):
        others.append(doc)
    result = await execute_auto_match(
        limit=20,
        min_rating=0,
        dry_run=False,
        triggered_by={"id": str(world.admin_id), "kind": "admin_manual", "label": "d13"},
    )
    for doc in others:
        await db.requests.replace_one({"_id": doc["_id"]}, doc)
    return result


def test_auto_match_skips_other_strategies_and_assigns_native(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        try:
            public_id = await _insert_request(world, MULTI_OFFER, created_at=old)
            direct_id = await _insert_request(world, DIRECT_REBOOK, created_at=old)
            native_id = await _insert_request(world, AUTO_MATCH, created_at=old)
            await _run_auto_match_isolated(world, native_id)
            public = await _saved(public_id)
            direct = await _saved(direct_id)
            native = await _saved(native_id)
            assert public["status"] == "open"
            assert public["specialist_id"] is None
            assert direct["status"] == "open"
            assert direct["specialist_id"] is None
            assert native["status"] == "assigned"
            assert native["specialist_id"] == str(world.spec_id)
            assert native["assignment_authority"] == AUTHORITY_AUTO_MATCH
            assert native["assignment_version"] == 1
            assert native.get("auto_assigned_via") == "admin_manual"
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_health_repair_does_not_assign(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        try:
            rid = await _insert_request(world, MULTI_OFFER, created_at=old)
            native_id = await _insert_request(world, AUTO_MATCH, created_at=old)
            await _repair_operations([{"metric": "gap_pressure"}])
            await _repair_marketplace([{"metric": "fill_rate"}])
            for current in (rid, native_id):
                saved = await _saved(current)
                assert saved["status"] == "open"
                assert saved["specialist_id"] is None
                assert saved.get("auto_assigned_via") is None
                assert "assignment_authority" not in saved
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_operations_override_only_on_direct_rebook(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            for strategy in (MULTI_OFFER, AUTO_MATCH):
                rid = await _insert_request(world, strategy)
                gap_id = ObjectId()
                await db.specialist_gaps.insert_one({
                    "_id": gap_id,
                    "request_id": rid,
                    "status": "open",
                    "category": "hvac",
                })
                world.gap_ids.append(gap_id)
                with pytest.raises(HTTPException) as exc:
                    await assign_gap(str(gap_id), {"specialist_id": str(world.spec_id)}, world.admin)
                assert exc.value.status_code == 400
                saved = await _saved(rid)
                assert saved["status"] == "open"
                assert saved["specialist_id"] is None

            rid = await _insert_request(world, DIRECT_REBOOK)
            gap_id = ObjectId()
            await db.specialist_gaps.insert_one({
                "_id": gap_id,
                "request_id": rid,
                "status": "open",
                "category": "hvac",
            })
            world.gap_ids.append(gap_id)
            await assign_gap(str(gap_id), {"specialist_id": str(world.spec_id)}, world.admin)
            saved = await _saved(rid)
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] == str(world.spec_id)
            assert saved["assignment_authority"] == ADMIN
            assert saved["assignment_version"] == 1
            assert saved["assigned_via"] == "operations_center"
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_sim_accept_does_not_mutate_assignment(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        try:
            rid = await _insert_request(world, MULTI_OFFER)
            before = await _saved(rid)
            result = await sim_accept(rid, {"specialist_id": str(world.spec_id)}, world.admin)
            saved = await _saved(rid)
            assert result["mutated"] is False
            assert saved["status"] == before["status"]
            assert saved["specialist_id"] == before["specialist_id"]
            assert saved.get("assigned_at") == before.get("assigned_at")
            assert "assignment_authority" not in saved
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_campaign_born_assigned_with_authority(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        campaign_id = ObjectId()
        prop_id = ObjectId()
        try:
            await db.properties.insert_one({
                "_id": prop_id,
                "owner_id": str(world.client_id),
                "name": "D13 Apt",
                "address": "Strada 1",
            })
            await db.community_campaigns.insert_one({
                "_id": campaign_id,
                "status": "open",
                "created_by": str(world.client_id),
                "category": "hvac",
                "title": f"D13W {world.tag}",
                "building_name": "Bloc",
                "building_id": f"b-{world.tag}",
                "participants": [{
                    "owner_id": str(world.client_id),
                    "owner_name": "D13 Client",
                    "property_id": str(prop_id),
                }],
                "offers": [{
                    "specialist_id": str(world.spec_id),
                    "specialist_name": "D13 Spec",
                    "price_per_unit": 80,
                }],
            })
            await accept_campaign_offer(
                str(campaign_id),
                {"specialist_id": str(world.spec_id)},
                world.client,
            )
            saved = await db.requests.find_one({"campaign_id": str(campaign_id)})
            world.request_ids.append(str(saved["_id"]))
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] == str(world.spec_id)
            assert saved["fulfillment_strategy"] == CAMPAIGN
            assert saved["assignment_authority"] == CAMPAIGN
            assert saved["assignment_version"] == 1
            assert saved["lead_fee_waived"] is True
            assert saved["is_campaign"] is True
            offers = await db.marketplace_offers.count_documents(
                {"request_id": str(saved["_id"])},
            )
            assert offers == 0
        finally:
            await db.properties.delete_one({"_id": prop_id})
            await world.cleanup()

    _run(eloop, _case())


def test_auto_match_does_not_replace_client_selection(eloop):
    async def _case():
        world = _World()
        await world.setup_users()
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        try:
            rid = await _insert_request(world, MULTI_OFFER, created_at=old)
            winner = await _offer(world, rid, world.spec_id)
            await accept_offer(rid, winner, world.client)
            await _run_auto_match_isolated(world, rid)
            saved = await _saved(rid)
            assert saved["specialist_id"] == str(world.spec_id)
            assert saved["assignment_authority"] == CLIENT_SELECTION
            assert saved["selected_offer_id"] == winner
        finally:
            await world.cleanup()

    _run(eloop, _case())
