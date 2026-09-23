"""D13 slice 1 — assignment commit, strategy transition, open-offer counter.

Calls the primitives directly. Does not exercise Auto-Match, repair, or routes.
"""
import asyncio
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from db import db
from fulfillment_commit import (
    ADMIN,
    AUTO_MATCH,
    CAMPAIGN,
    CLIENT_SELECTION,
    DIRECT_REBOOK,
    FALLBACK,
    MULTI_OFFER,
    SYSTEM_FALLBACK,
    claim_open_offer_slot,
    commit_assignment,
    commit_transition,
    release_open_offer_slot,
)

STARTED = "2020-01-01T00:00:00+00:00"
OWNER = {"id": "owner-d13", "name": "Owner", "role": "client"}
OTHER = {"id": "other-d13", "name": "Other", "role": "client"}
ADMIN_ACTOR = {"id": "admin-d13", "name": "Admin", "role": "admin"}
SYSTEM = {"id": "system", "name": "System", "role": "system"}


def _detach_motor_loop(loop):
    """Drop the singleton client's cached loop when it is this fixture's loop.

    Motor keeps the first loop it uses. Closing that loop makes a later
    Motor test raise ``Event loop is closed``.
    """
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


def _doc(**over):
    doc = {
        "_id": ObjectId(),
        "status": "open",
        "client_id": OWNER["id"],
        "specialist_id": None,
        "fulfillment_strategy": MULTI_OFFER,
        "fulfillment_strategy_started_at": STARTED,
        "assignment_version": 0,
        "open_offer_count": 0,
        "property_id": "prop-d13",
    }
    doc.update(over)
    return doc


async def _insert(doc):
    await db.requests.insert_one(doc)
    return str(doc["_id"])


async def _cleanup(rid):
    oid = ObjectId(rid)
    await db.requests.delete_one({"_id": oid})
    await db.activity_events.delete_many({"request_id": rid})


def _assign(rid, **over):
    payload = dict(
        request_id=rid,
        expected_strategy=MULTI_OFFER,
        expected_assignment_version=0,
        specialist_id="spec-d13",
        assignment_authority=CLIENT_SELECTION,
        assignment_trigger="client_accept",
        assignment_reason="client chose an offer",
        actor=OWNER,
        offer_id="offer-1",
    )
    payload.update(over)
    return commit_assignment(**payload)


def test_client_selection_on_multi_offer(eloop):
    async def _case():
        rid = await _insert(_doc())
        try:
            result = await _assign(rid, matching_policy="category_zone")
            assert result["ok"] is True
            saved = result["request"]
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] == "spec-d13"
            assert saved["assignment_authority"] == CLIENT_SELECTION
            assert saved["assignment_trigger"] == "client_accept"
            assert saved["assignment_reason"] == "client chose an offer"
            assert saved["matching_policy"] == "category_zone"
            assert saved["selected_offer_id"] == "offer-1"
            assert saved["assignment_version"] == 1
            assert saved["fulfillment_strategy_started_at"] == STARTED
            assert "auto_assigned_via" not in saved
            assert "assigned_via" not in saved
            event = await db.activity_events.find_one({
                "request_id": rid,
                "event_type": "request.assigned",
            })
            assert event["payload"]["assignment_authority"] == CLIENT_SELECTION
            assert event["payload"]["offer_id"] == "offer-1"
            assert event["payload"]["assignment_version"] == 1
            assert event["actor_id"] == OWNER["id"]
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_wrong_authority_rejected(eloop):
    async def _case():
        rid = await _insert(_doc())
        try:
            result = await _assign(rid, assignment_authority=AUTO_MATCH)
            assert result["ok"] is False
            assert result["reason"] == "authority_not_allowed"
            assert result["request"] is None
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["specialist_id"] is None
            assert saved["assignment_version"] == 0
            events = await db.activity_events.count_documents({
                "request_id": rid,
            })
            assert events == 0
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_wrong_strategy_rejected(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            result = await _assign(rid)
            assert result["reason"] == "strategy_mismatch"
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["status"] == "open"
            assert saved["specialist_id"] is None
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_wrong_version_is_not_retried(eloop):
    async def _case():
        rid = await _insert(_doc(assignment_version=4))
        try:
            result = await _assign(rid, expected_assignment_version=0)
            assert result["reason"] == "version_mismatch"
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["assignment_version"] == 4
            assert saved["specialist_id"] is None
            assert saved["status"] == "open"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_already_assigned_rejected(eloop):
    async def _case():
        rid = await _insert(_doc(specialist_id="someone"))
        try:
            result = await _assign(rid)
            assert result["reason"] == "already_assigned"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_non_open_rejected(eloop):
    async def _case():
        rid = await _insert(_doc(status="in_progress"))
        try:
            result = await _assign(rid)
            assert result["reason"] == "not_open"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_concurrent_assignments_one_winner(eloop):
    async def _case():
        rid = await _insert(_doc())
        try:
            first, second = await asyncio.gather(
                _assign(rid, specialist_id="spec-a"),
                _assign(rid, specialist_id="spec-b"),
            )
            assert [first["ok"], second["ok"]].count(True) == 1
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["status"] == "assigned"
            assert saved["specialist_id"] in ("spec-a", "spec-b")
            assert saved["assignment_version"] == 1
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_direct_rebook_authority(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            result = await _assign(
                rid,
                expected_strategy=DIRECT_REBOOK,
                assignment_authority=DIRECT_REBOOK,
                assignment_trigger="direct_accept",
                assignment_reason="named specialist accepted",
                offer_id=None,
            )
            assert result["ok"] is True
            saved = result["request"]
            assert saved["specialist_id"] == "spec-d13"
            assert saved["assignment_authority"] == DIRECT_REBOOK
            assert "selected_offer_id" not in saved
            assert "auto_assigned_via" not in saved
            assert "assigned_via" not in saved
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_direct_rebook_admin_requires_explicit_path(eloop):
    async def _case():
        bare = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        flagged = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        client_flag = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            denied = await _assign(
                bare,
                expected_strategy=DIRECT_REBOOK,
                assignment_authority=ADMIN,
                actor=ADMIN_ACTOR,
                explicit_admin_override=False,
            )
            assert denied["reason"] == "admin_override_required"
            still = await db.requests.find_one({"_id": ObjectId(bare)})
            assert still["status"] == "open"

            spoofed = await _assign(
                client_flag,
                expected_strategy=DIRECT_REBOOK,
                assignment_authority=ADMIN,
                actor=OWNER,
                explicit_admin_override=True,
            )
            assert spoofed["reason"] == "admin_override_required"

            allowed = await _assign(
                flagged,
                expected_strategy=DIRECT_REBOOK,
                assignment_authority=ADMIN,
                assignment_trigger="admin_override",
                assignment_reason="explicit admin override",
                actor=ADMIN_ACTOR,
                explicit_admin_override=True,
                assigned_via="operations_center",
                offer_id="must-not-stick",
            )
            assert allowed["ok"] is True
            saved = allowed["request"]
            assert saved["assigned_via"] == "operations_center"
            assert saved["assigned_by"] == ADMIN_ACTOR["id"]
            assert "auto_assigned_via" not in saved
            assert "selected_offer_id" not in saved
        finally:
            await _cleanup(bare)
            await _cleanup(flagged)
            await _cleanup(client_flag)

    _run(eloop, _case())


def test_direct_rebook_rejects_client_selection(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            result = await _assign(rid, expected_strategy=DIRECT_REBOOK)
            assert result["reason"] == "authority_not_allowed"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_fallback_authority_matrix(eloop):
    async def _case():
        ok_id = await _insert(_doc(fulfillment_strategy=FALLBACK))
        auto_id = await _insert(_doc(fulfillment_strategy=FALLBACK))
        multi_id = await _insert(_doc())
        try:
            ok = await _assign(
                ok_id,
                expected_strategy=FALLBACK,
                assignment_authority=SYSTEM_FALLBACK,
                assignment_trigger="cron",
                assignment_reason="fallback window elapsed",
                actor=SYSTEM,
                offer_id="nope",
            )
            assert ok["ok"] is True
            assert ok["request"]["auto_assigned_via"] == "cron"
            assert ok["request"]["assignment_authority"] == SYSTEM_FALLBACK
            assert "selected_offer_id" not in ok["request"]
            assert "assigned_via" not in ok["request"]

            wrong = await _assign(
                auto_id,
                expected_strategy=FALLBACK,
                assignment_authority=AUTO_MATCH,
                actor=SYSTEM,
            )
            assert wrong["reason"] == "authority_not_allowed"

            blocked = await _assign(
                multi_id,
                assignment_authority=SYSTEM_FALLBACK,
                actor=SYSTEM,
            )
            assert blocked["reason"] == "authority_not_allowed"
        finally:
            await _cleanup(ok_id)
            await _cleanup(auto_id)
            await _cleanup(multi_id)

    _run(eloop, _case())


def test_release_direct_rebook_to_multi_offer(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            result = await commit_transition(
                request_id=rid,
                expected_strategy=DIRECT_REBOOK,
                expected_assignment_version=0,
                target_strategy=MULTI_OFFER,
                actor=OWNER,
                reason="client released the named specialist",
            )
            assert result["ok"] is True
            saved = result["request"]
            assert saved["fulfillment_strategy"] == MULTI_OFFER
            assert saved["assignment_version"] == 1
            assert saved["specialist_id"] in (None, "")
            assert saved["status"] == "open"
            assert saved["fulfillment_strategy_started_at"] != STARTED
            started = datetime.fromisoformat(
                saved["fulfillment_strategy_started_at"],
            )
            assert started > datetime(2024, 1, 1, tzinfo=timezone.utc)
            event = await db.activity_events.find_one(
                {"request_id": rid, "event_type": "request.strategy_released"}
            )
            assert event["payload"]["previous_strategy"] == DIRECT_REBOOK
            assert event["payload"]["new_strategy"] == MULTI_OFFER
            assert event["payload"]["assignment_version"] == 1
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_release_requires_owner(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            result = await commit_transition(
                request_id=rid,
                expected_strategy=DIRECT_REBOOK,
                expected_assignment_version=0,
                target_strategy=MULTI_OFFER,
                actor=OTHER,
                reason="not the owner",
            )
            assert result["reason"] == "not_owner"
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["fulfillment_strategy"] == DIRECT_REBOOK
            assert saved["assignment_version"] == 0
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_fallback_transition_is_explicit_only(eloop):
    async def _case():
        denied_id = await _insert(_doc())
        allowed_id = await _insert(_doc())
        try:
            denied = await commit_transition(
                request_id=denied_id,
                expected_strategy=MULTI_OFFER,
                expected_assignment_version=0,
                target_strategy=FALLBACK,
                actor=OWNER,
                reason="client cannot fall back",
                transition_authority=SYSTEM_FALLBACK,
            )
            assert denied["reason"] == "transition_not_allowed"
            untouched = await db.requests.find_one({
                "_id": ObjectId(denied_id),
            })
            assert untouched["fulfillment_strategy"] == MULTI_OFFER
            assert untouched["assignment_version"] == 0

            allowed = await commit_transition(
                request_id=allowed_id,
                expected_strategy=MULTI_OFFER,
                expected_assignment_version=0,
                target_strategy=FALLBACK,
                actor=SYSTEM,
                reason="explicit system fallback",
                transition_authority=SYSTEM_FALLBACK,
            )
            assert allowed["ok"] is True
            saved = allowed["request"]
            assert saved["fulfillment_strategy"] == FALLBACK
            assert saved["status"] == "open"
            assert saved["specialist_id"] in (None, "")
            assert saved["assignment_version"] == 1
            assert saved["fulfillment_strategy_started_at"] != STARTED
            event = await db.activity_events.find_one(
                {
                    "request_id": allowed_id,
                    "event_type": "request.strategy_transition",
                },
            )
            assert event["payload"]["new_strategy"] == FALLBACK
        finally:
            await _cleanup(denied_id)
            await _cleanup(allowed_id)

    _run(eloop, _case())


def test_concurrent_transitions_one_winner(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            call = dict(
                request_id=rid,
                expected_strategy=DIRECT_REBOOK,
                expected_assignment_version=0,
                target_strategy=MULTI_OFFER,
                actor=OWNER,
                reason="release",
            )
            first, second = await asyncio.gather(
                commit_transition(**call),
                commit_transition(**call),
            )
            assert [first["ok"], second["ok"]].count(True) == 1
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["assignment_version"] == 1
            assert saved["fulfillment_strategy"] == MULTI_OFFER
            assert saved["specialist_id"] in (None, "")
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_assignment_and_transition_share_one_version(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        try:
            assigned, moved = await asyncio.gather(
                _assign(
                    rid,
                    expected_strategy=DIRECT_REBOOK,
                    assignment_authority=DIRECT_REBOOK,
                    assignment_trigger="direct_accept",
                    assignment_reason="named specialist",
                    offer_id=None,
                ),
                commit_transition(
                    request_id=rid,
                    expected_strategy=DIRECT_REBOOK,
                    expected_assignment_version=0,
                    target_strategy=MULTI_OFFER,
                    actor=OWNER,
                    reason="release",
                ),
            )
            assert [assigned["ok"], moved["ok"]].count(True) == 1
            saved = await db.requests.find_one({"_id": ObjectId(rid)})
            assert saved["assignment_version"] == 1
            if assigned["ok"]:
                assert saved["status"] == "assigned"
                assert saved["fulfillment_strategy"] == DIRECT_REBOOK
            else:
                assert saved["status"] == "open"
                assert saved["fulfillment_strategy"] == MULTI_OFFER
                assert saved["specialist_id"] in (None, "")
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_open_offer_counter_is_conditional(eloop):
    async def _case():
        open_id = await _insert(_doc())
        rebook_id = await _insert(_doc(fulfillment_strategy=DIRECT_REBOOK))
        assigned_id = await _insert(_doc(
            status="assigned",
            specialist_id="spec-d13",
        ))
        try:
            claimed = await claim_open_offer_slot(open_id)
            assert claimed["ok"] is True
            assert claimed["open_offer_count"] == 1
            saved = await db.requests.find_one({"_id": ObjectId(open_id)})
            assert saved["assignment_version"] == 0
            assert saved["status"] == "open"

            again = await claim_open_offer_slot(open_id)
            assert again["open_offer_count"] == 2

            released = await release_open_offer_slot(open_id)
            assert released["open_offer_count"] == 1
            await release_open_offer_slot(open_id)
            empty = await release_open_offer_slot(open_id)
            assert empty["ok"] is False
            floor = await db.requests.find_one({"_id": ObjectId(open_id)})
            assert floor["open_offer_count"] == 0
            assert floor["assignment_version"] == 0

            wrong = await claim_open_offer_slot(rebook_id)
            assert wrong["reason"] == "strategy_mismatch"
            rebook = await db.requests.find_one({"_id": ObjectId(rebook_id)})
            assert rebook.get("open_offer_count") == 0

            taken = await claim_open_offer_slot(assigned_id)
            assert taken["ok"] is False
            assigned = await db.requests.find_one({
                "_id": ObjectId(assigned_id),
            })
            assert assigned.get("open_offer_count") == 0
        finally:
            await _cleanup(open_id)
            await _cleanup(rebook_id)
            await _cleanup(assigned_id)

    _run(eloop, _case())


def test_missing_assignment_version_assigns(eloop):
    async def _case():
        doc = _doc()
        doc.pop("assignment_version")
        rid = await _insert(doc)
        try:
            result = await _assign(rid, expected_assignment_version=0)
            assert result["ok"] is True
            assert result["request"]["assignment_version"] == 1
            assert result["request"]["specialist_id"] == "spec-d13"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_missing_assignment_version_transitions(eloop):
    async def _case():
        doc = _doc(fulfillment_strategy=DIRECT_REBOOK)
        doc.pop("assignment_version")
        rid = await _insert(doc)
        try:
            result = await commit_transition(
                request_id=rid,
                expected_strategy=DIRECT_REBOOK,
                expected_assignment_version=0,
                target_strategy=MULTI_OFFER,
                actor=OWNER,
                reason="release without a stored version",
            )
            assert result["ok"] is True
            saved = result["request"]
            assert saved["assignment_version"] == 1
            assert saved["fulfillment_strategy"] == MULTI_OFFER
            assert saved["specialist_id"] in (None, "")
            assert saved["status"] == "open"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())


def test_null_assignment_version_is_not_incremented(eloop):
    async def _case():
        assigned_id = await _insert(_doc(assignment_version=None))
        released_id = await _insert(_doc(
            fulfillment_strategy=DIRECT_REBOOK,
            assignment_version=None,
        ))
        invalid_id = await _insert(_doc(assignment_version="nope"))
        try:
            assigned = await _assign(
                assigned_id,
                expected_assignment_version=0,
            )
            assert assigned["ok"] is False
            assert assigned["reason"] == "version_mismatch"
            saved = await db.requests.find_one({"_id": ObjectId(assigned_id)})
            assert saved["assignment_version"] is None
            assert saved["status"] == "open"
            assert saved["specialist_id"] is None

            released = await commit_transition(
                request_id=released_id,
                expected_strategy=DIRECT_REBOOK,
                expected_assignment_version=0,
                target_strategy=MULTI_OFFER,
                actor=OWNER,
                reason="null version",
            )
            assert released["ok"] is False
            assert released["reason"] == "version_mismatch"
            still = await db.requests.find_one({
                "_id": ObjectId(released_id),
            })
            assert still["assignment_version"] is None
            assert still["fulfillment_strategy"] == DIRECT_REBOOK

            invalid = await _assign(
                invalid_id,
                expected_assignment_version=0,
            )
            assert invalid["reason"] == "version_mismatch"
            bad = await db.requests.find_one({"_id": ObjectId(invalid_id)})
            assert bad["assignment_version"] == "nope"
            assert bad["status"] == "open"
        finally:
            await _cleanup(assigned_id)
            await _cleanup(released_id)
            await _cleanup(invalid_id)

    _run(eloop, _case())


def test_campaign_authority_and_unknown_authority(eloop):
    async def _case():
        rid = await _insert(_doc(fulfillment_strategy=CAMPAIGN))
        try:
            ok = await _assign(
                rid,
                expected_strategy=CAMPAIGN,
                assignment_authority=CAMPAIGN,
                assignment_trigger="campaign_accept",
                assignment_reason="campaign offer accepted",
                offer_id=None,
            )
            assert ok["ok"] is True
            assert "selected_offer_id" not in ok["request"]
            assert "auto_assigned_via" not in ok["request"]
            repair = await _assign(
                rid,
                expected_assignment_version=1,
                expected_strategy=CAMPAIGN,
                assignment_authority="repair",
            )
            assert repair["reason"] == "authority_not_allowed"
        finally:
            await _cleanup(rid)

    _run(eloop, _case())
