"""D13 slice 2 — strategy fields written on request creation.

Calls the real creators and reads the stored request documents.
"""
import asyncio
import uuid

import pytest
from bson import ObjectId
from fastapi import BackgroundTasks, HTTPException

from db import db
from fulfillment_commit import CAMPAIGN, DIRECT_REBOOK, MULTI_OFFER
from models import DesignConceptIn, RequestIn
from routes.community_buildings import accept_campaign_offer
from routes.design import create_design_concept_request
from routes.digital_twin import RequestOfferIn, request_offer_from_concept
from routes.house_health_recommendations import (
    PublishToMarketplaceIn,
    publish_to_marketplace,
)
from routes.maintenance_calendar import TaskRequestIn, request_from_task
from routes.opportunities import accept_opportunity
from routes.requests import create_request
from routes.trusted_specialists import RebookIn, rebook_specialist


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


def _assert_born(saved, strategy):
    assert saved["fulfillment_strategy"] == strategy
    assert saved["fulfillment_strategy_started_at"] == saved["created_at"]
    assert saved["fulfillment_strategy_started_at"]


class _World:
    def __init__(self):
        self.tag = uuid.uuid4().hex[:10]
        self.client_id = str(ObjectId())
        self.other_id = str(ObjectId())
        self.prop_id = ObjectId()
        self.spec_id = ObjectId()
        self.client = {
            "id": self.client_id,
            "name": "D13 Birth",
            "role": "client",
        }
        self.other = {
            "id": self.other_id,
            "name": "Other",
            "role": "client",
        }
        self.request_ids = []
        self.extra = []

    async def setup(self):
        await db.users.insert_one({
            "_id": self.spec_id,
            "role": "specialist",
            "name": "D13 Spec",
        })
        await db.properties.insert_one({
            "_id": self.prop_id,
            "owner_id": self.client_id,
            "name": f"D13B {self.tag}",
            "address": "Str. Birth 1",
            "twin_unlocked": True,
        })
        await db.requests.insert_one({
            "client_id": self.client_id,
            "specialist_id": str(self.spec_id),
            "status": "completed",
            "category": "plumbing",
            "title": f"D13B done {self.tag}",
        })

    async def cleanup(self):
        await db.users.delete_one({"_id": self.spec_id})
        await db.properties.delete_one({"_id": self.prop_id})
        await db.requests.delete_many({
            "$or": [
                {"client_id": self.client_id},
                {"title": {"$regex": self.tag}},
                {"d13_legacy_marker": self.tag},
            ],
        })
        for kind, value in self.extra:
            await db[kind].delete_many(value)
        await db.notifications.delete_many({"title": {"$regex": self.tag}})
        await db.email_log.delete_many({"subject": {"$regex": self.tag}})
        await db.activity_events.delete_many({
            "request_id": {"$in": self.request_ids},
        })


def _remember(world, result):
    rid = result.get("id") or result.get("request_id")
    if rid:
        world.request_ids.append(rid)
    return rid


async def _saved(rid):
    return await db.requests.find_one({"_id": ObjectId(rid)})


def test_public_create_request_is_multi_offer(eloop):
    async def _case():
        world = _World()
        await world.setup()
        try:
            legacy_id = ObjectId()
            await db.requests.insert_one({
                "_id": legacy_id,
                "d13_legacy_marker": world.tag,
                "status": "open",
                "client_id": "historical",
                "created_at": "2019-01-01T00:00:00+00:00",
            })
            created = await create_request(
                RequestIn(
                    property_id=str(world.prop_id),
                    category="plumbing",
                    title=f"D13B req {world.tag}",
                    description="Public request",
                ),
                BackgroundTasks(),
                world.client,
            )
            rid = _remember(world, created)
            saved = await _saved(rid)
            _assert_born(saved, MULTI_OFFER)
            assert saved["status"] == "open"
            assert saved["specialist_id"] is None
            assert "assignment_version" not in saved
            event = await db.activity_events.find_one({
                "request_id": rid,
                "event_type": "request.created",
            })
            assert event is not None
            released = await db.activity_events.count_documents({
                "request_id": rid,
                "event_type": "request.strategy_released",
            })
            assert released == 0
            legacy = await db.requests.find_one({"_id": legacy_id})
            assert "fulfillment_strategy" not in legacy
            assert "fulfillment_strategy_started_at" not in legacy
            with pytest.raises(HTTPException) as denied:
                await create_request(
                    RequestIn(
                        property_id=str(world.prop_id),
                        category="plumbing",
                        title=f"D13B denied {world.tag}",
                        description="Not the owner",
                    ),
                    BackgroundTasks(),
                    world.other,
                )
            assert denied.value.status_code == 404
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_maintenance_open_and_direct(eloop):
    async def _case():
        world = _World()
        await world.setup()
        task_id = ObjectId()
        try:
            await db.maintenance_tasks.insert_one({
                "_id": task_id,
                "owner_id": world.client_id,
                "property_id": str(world.prop_id),
                "active": True,
                "title": f"D13B task {world.tag}",
                "category": "plumbing",
                "frequency_months": 6,
                "next_due": "2026-10-01",
            })
            world.extra.append((
                "maintenance_tasks",
                {"_id": task_id},
            ))
            opened = await request_from_task(
                str(task_id),
                TaskRequestIn(mode="open", description="open slot"),
                world.client,
            )
            open_id = _remember(world, opened)
            open_saved = await _saved(open_id)
            _assert_born(open_saved, MULTI_OFFER)
            assert open_saved["status"] == "open"
            assert "is_rebooking" not in open_saved

            direct = await request_from_task(
                str(task_id),
                TaskRequestIn(
                    mode="direct",
                    specialist_id=str(world.spec_id),
                    description="direct slot",
                ),
                world.client,
            )
            direct_id = _remember(world, direct)
            direct_saved = await _saved(direct_id)
            _assert_born(direct_saved, DIRECT_REBOOK)
            assert direct_saved["status"] == "open"
            assert direct_saved["specialist_id"] is None
            assert direct_saved["is_rebooking"] is True
            assert direct_saved["lead_fee_waived"] is True
            assert direct_saved["direct_specialist_id"] == str(world.spec_id)
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_rebook_specialist_is_direct_rebook(eloop):
    async def _case():
        world = _World()
        await world.setup()
        try:
            created = await rebook_specialist(
                str(world.spec_id),
                RebookIn(
                    property_id=str(world.prop_id),
                    title=f"D13B rebook {world.tag}",
                    description="Please return",
                    category="plumbing",
                ),
                world.client,
            )
            rid = _remember(world, created)
            saved = await _saved(rid)
            _assert_born(saved, DIRECT_REBOOK)
            assert saved["status"] == "open"
            assert saved["specialist_id"] is None
            assert saved["is_rebooking"] is True
            assert saved["lead_fee_waived"] is True
            event = await db.activity_events.find_one({
                "request_id": rid,
                "event_type": "request.rebooked",
            })
            assert event is not None
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_design_house_health_and_revenue_hunter(eloop):
    async def _case():
        world = _World()
        await world.setup()
        room_id = f"room-{world.tag}"
        twin_project_id = f"hh-{world.tag}"
        rec_id = f"rec-{world.tag}"
        opp_id = f"opp-{world.tag}"
        try:
            await db.twins.insert_one({
                "property_id": str(world.prop_id),
                "status": "approved",
                "rooms": [{
                    "id": room_id,
                    "name": "Living",
                    "type": "living",
                    "area": 20,
                }],
            })
            world.extra.append((
                "twins",
                {"property_id": str(world.prop_id)},
            ))
            design = await create_design_concept_request(
                DesignConceptIn(
                    property_id=str(world.prop_id),
                    room_ids=[room_id],
                    tokens_to_use=0,
                ),
                {**world.client, "tokens": 0},
            )
            design_id = _remember(world, design)
            design_saved = await _saved(design_id)
            _assert_born(design_saved, MULTI_OFFER)
            assert design_saved["status"] == "open"
            assert design_saved["category"] == "interior_design"

            await db.digital_twin_projects.insert_one({
                "id": twin_project_id,
                "owner_id": world.client_id,
            })
            await db.hh_recommendations.insert_one({
                "id": rec_id,
                "priority": "recommended",
                "category": "electric",
                "title": f"D13B hh {world.tag}",
                "description": "Publish this",
                "twin_project_id": twin_project_id,
            })
            world.extra.append((
                "digital_twin_projects",
                {"id": twin_project_id},
            ))
            world.extra.append(("hh_recommendations", {"id": rec_id}))
            world.extra.append((
                "hh_audit_log",
                {"resource_id": rec_id},
            ))
            published = await publish_to_marketplace(
                rec_id,
                PublishToMarketplaceIn(property_id=str(world.prop_id)),
                world.client,
            )
            hh_id = _remember(world, published)
            hh_saved = await _saved(hh_id)
            _assert_born(hh_saved, MULTI_OFFER)
            assert hh_saved["status"] == "open"
            source = hh_saved["house_health_source"]
            assert source["recommendation_id"] == rec_id

            await db.revenue_opportunities.insert_one({
                "id": opp_id,
                "owner_id": world.client_id,
                "property_id": str(world.prop_id),
                "status": "active",
                "service": "predictive_maintenance",
                "service_label": f"D13B hunter {world.tag}",
                "benefit": "Plan the work",
                "estimated_value_ron": 0,
                "title": f"D13B opp {world.tag}",
            })
            world.extra.append(("revenue_opportunities", {"id": opp_id}))
            accepted = await accept_opportunity(opp_id, world.client)
            hunter_id = _remember(world, accepted)
            world.extra.append((
                "ai_decision_ledger",
                {"request_id": hunter_id},
            ))
            hunter_saved = await _saved(hunter_id)
            _assert_born(hunter_saved, MULTI_OFFER)
            assert hunter_saved["source"] == "revenue_hunter"
            assert hunter_saved["status"] == "open"
            assert hunter_saved["specialist_id"] is None
        finally:
            await world.cleanup()

    _run(eloop, _case())


def test_digital_twin_concept_and_campaign(eloop):
    async def _case():
        world = _World()
        await world.setup()
        project_id = f"proj-{world.tag}"
        concept_id = f"concept-{world.tag}"
        campaign_id = ObjectId()
        try:
            await db.digital_twin_projects.insert_one({
                "id": project_id,
                "owner_id": world.client_id,
                "property_id": str(world.prop_id),
            })
            await db.digital_twin_design_concepts.insert_one({
                "id": concept_id,
                "project_id": project_id,
                "property_id": str(world.prop_id),
                "status": "verified",
                "concept": {
                    "title": f"D13B concept {world.tag}",
                    "summary": "Validated concept",
                    "budget": {"total_low": 100, "total_high": 200},
                },
            })
            world.extra.append(("digital_twin_projects", {"id": project_id}))
            world.extra.append((
                "digital_twin_design_concepts",
                {"id": concept_id},
            ))
            offered = await request_offer_from_concept(
                concept_id,
                RequestOfferIn(confirm=True, category="interior_design"),
                world.client,
            )
            concept_req = _remember(world, offered)
            concept_saved = await _saved(concept_req)
            _assert_born(concept_saved, MULTI_OFFER)
            assert concept_saved["source"] == "digital_twin_concept"
            assert concept_saved["status"] == "open"
            assert concept_saved["specialist_id"] is None

            await db.community_campaigns.insert_one({
                "_id": campaign_id,
                "status": "open",
                "created_by": world.client_id,
                "category": "plumbing",
                "title": f"D13B campaign {world.tag}",
                "building_name": "Bloc",
                "building_id": f"b-{world.tag}",
                "participants": [{
                    "owner_id": world.client_id,
                    "owner_name": "D13 Birth",
                    "property_id": str(world.prop_id),
                }],
                "offers": [{
                    "specialist_id": str(world.spec_id),
                    "specialist_name": "D13 Spec",
                    "price_per_unit": 120,
                }],
            })
            world.extra.append((
                "community_campaigns",
                {"_id": campaign_id},
            ))
            await accept_campaign_offer(
                str(campaign_id),
                {"specialist_id": str(world.spec_id)},
                world.client,
            )
            campaign_saved = await db.requests.find_one({
                "campaign_id": str(campaign_id),
                "client_id": world.client_id,
            })
            world.request_ids.append(str(campaign_saved["_id"]))
            _assert_born(campaign_saved, CAMPAIGN)
            assert campaign_saved["status"] == "assigned"
            assert campaign_saved["specialist_id"] == str(world.spec_id)
            assert campaign_saved["is_campaign"] is True
            assert campaign_saved["lead_fee_waived"] is True
        finally:
            await world.cleanup()

    _run(eloop, _case())
