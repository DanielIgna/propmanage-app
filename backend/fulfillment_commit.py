"""D13 assignment and strategy-transition commits.

One conditional update on the request document. Not a fulfillment engine.
Authority and legal transitions are governance invariants, not settings.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument

from db import db
from services import log_event

MULTI_OFFER = "MULTI_OFFER"
DIRECT_REBOOK = "DIRECT_REBOOK"
FALLBACK = "FALLBACK"
AUTO_MATCH = "AUTO_MATCH"
CAMPAIGN = "CAMPAIGN"

CLIENT_SELECTION = "CLIENT_SELECTION"
AUTHORITY_DIRECT_REBOOK = "DIRECT_REBOOK"
SYSTEM_FALLBACK = "SYSTEM_FALLBACK"
AUTHORITY_AUTO_MATCH = "AUTO_MATCH"
ADMIN = "ADMIN"
AUTHORITY_CAMPAIGN = "CAMPAIGN"

# Governance invariant. Not an Admin setting.
AUTHORITY_BY_STRATEGY = {
    MULTI_OFFER: frozenset({CLIENT_SELECTION}),
    DIRECT_REBOOK: frozenset({AUTHORITY_DIRECT_REBOOK, ADMIN}),
    FALLBACK: frozenset({SYSTEM_FALLBACK}),
    AUTO_MATCH: frozenset({AUTHORITY_AUTO_MATCH}),
    CAMPAIGN: frozenset({AUTHORITY_CAMPAIGN}),
}

# (current, target) -> required caller context
RELEASE_TO_MULTI_OFFER = (DIRECT_REBOOK, MULTI_OFFER)
ENTER_FALLBACK = (MULTI_OFFER, FALLBACK)

SNAPSHOT_KEYS = (
    "specialist_name",
    "specialist_specialty",
    "specialist_city",
    "specialist_verified",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _oid(request_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(request_id)
    except (InvalidId, TypeError):
        return None


def _empty_specialist() -> dict:
    return {"$or": [
        {"specialist_id": None},
        {"specialist_id": ""},
        {"specialist_id": {"$exists": False}},
    ]}


def _version_clause(expected: int) -> dict:
    """Version 0 matches a stored 0 or a missing field.

    Explicit null is not version 0. ``$inc`` cannot update a null, so the
    predicate must not select it.
    """
    if expected == 0:
        return {"$or": [
            {"assignment_version": 0},
            {"assignment_version": {"$exists": False}},
        ]}
    return {"assignment_version": expected}


def _open_predicate(
    oid: ObjectId,
    strategy: str,
    expected_version: int,
    extra: Optional[list] = None,
) -> dict:
    clauses = [
        {"_id": oid},
        {"status": "open"},
        {"fulfillment_strategy": strategy},
        _empty_specialist(),
        _version_clause(expected_version),
    ]
    if extra:
        clauses.extend(extra)
    return {"$and": clauses}


def _no(reason: str) -> dict:
    return {"ok": False, "reason": reason, "request": None}


def _specialist_empty(doc: dict) -> bool:
    return doc.get("specialist_id") in (None, "")


def _version_is(doc: dict, expected: int) -> bool:
    if expected == 0 and "assignment_version" not in doc:
        return True
    return doc.get("assignment_version") == expected


async def _explain_miss(
    oid: ObjectId,
    strategy: str,
    expected_version: int,
    owner_id: Optional[str] = None,
) -> str:
    doc: Any = await db.requests.find_one(  # type: ignore[func-returns-value]
        {"_id": oid},
    )
    if not doc:
        return "not_found"
    if doc.get("status") != "open":
        return "not_open"
    if not _specialist_empty(doc):
        return "already_assigned"
    if doc.get("fulfillment_strategy") != strategy:
        return "strategy_mismatch"
    if not _version_is(doc, expected_version):
        return "version_mismatch"
    if owner_id is not None and doc.get("client_id") != owner_id:
        return "not_owner"
    return "conflict"


def _legacy_assignment_fields(
    authority: str,
    trigger: str,
    actor: dict,
    offer_id: Optional[str],
    assigned_via: Optional[str],
    now: str,
) -> dict:
    """Mirrors that belong to this authority only."""
    fields: dict = {}
    if authority == CLIENT_SELECTION and offer_id:
        fields["selected_offer_id"] = offer_id
    elif authority in (AUTHORITY_AUTO_MATCH, SYSTEM_FALLBACK):
        fields["auto_assigned_via"] = trigger
        fields["auto_assigned_at"] = now
        fields["auto_assigned_by_admin"] = (actor or {}).get("id")
    elif authority == ADMIN:
        fields["assigned_via"] = assigned_via or "admin"
        fields["assigned_by"] = (actor or {}).get("id")
    return fields


async def commit_assignment(
    *,
    request_id: str,
    expected_strategy: str,
    expected_assignment_version: int,
    specialist_id: str,
    assignment_authority: str,
    assignment_trigger: str,
    assignment_reason: str,
    actor: dict,
    offer_id: Optional[str] = None,
    matching_policy: Optional[str] = None,
    explicit_admin_override: bool = False,
    specialist_snapshot: Optional[dict] = None,
    assigned_via: Optional[str] = None,
) -> dict:
    """Assign one open request.

    A zero-match does not write, notify, debit, or close offers.
    """
    allowed = AUTHORITY_BY_STRATEGY.get(expected_strategy)
    if not allowed or assignment_authority not in allowed:
        return _no("authority_not_allowed")
    if assignment_authority == ADMIN:
        if not explicit_admin_override or (actor or {}).get("role") != "admin":
            return _no("admin_override_required")
    if not specialist_id:
        return _no("authority_not_allowed")

    oid = _oid(request_id)
    if oid is None:
        return _no("not_found")

    now = _now()
    update_set = {
        "status": "assigned",
        "specialist_id": specialist_id,
        "assigned_at": now,
        "assignment_authority": assignment_authority,
        "assignment_trigger": assignment_trigger,
        "assignment_reason": assignment_reason,
    }
    if matching_policy:
        update_set["matching_policy"] = matching_policy
    if specialist_snapshot:
        for key in SNAPSHOT_KEYS:
            value = specialist_snapshot.get(key)
            if value is not None:
                update_set[key] = value
    update_set.update(_legacy_assignment_fields(
        assignment_authority,
        assignment_trigger,
        actor,
        offer_id,
        assigned_via,
        now,
    ))

    claimed: Any = await db.requests.find_one_and_update(
        _open_predicate(oid, expected_strategy, expected_assignment_version),
        {"$set": update_set, "$inc": {"assignment_version": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        return _no(await _explain_miss(
            oid, expected_strategy, expected_assignment_version,
        ))

    version = claimed.get("assignment_version")
    await log_event(
        request_id,
        "request.assigned",
        actor=actor,
        property_id=claimed.get("property_id"),
        payload={
            "previous_strategy": expected_strategy,
            "new_strategy": expected_strategy,
            "assignment_authority": assignment_authority,
            "assignment_trigger": assignment_trigger,
            "assignment_reason": assignment_reason,
            "specialist_id": specialist_id,
            "offer_id": offer_id,
            "timestamp": now,
            "assignment_version": version,
        },
    )
    return {"ok": True, "reason": None, "request": claimed}


async def commit_transition(
    *,
    request_id: str,
    expected_strategy: str,
    expected_assignment_version: int,
    target_strategy: str,
    actor: dict,
    reason: str,
    transition_authority: Optional[str] = None,
) -> dict:
    """Change strategy without assigning a specialist."""
    pair = (expected_strategy, target_strategy)
    if pair == RELEASE_TO_MULTI_OFFER:
        role = (actor or {}).get("role")
        if role != "client" or not (actor or {}).get("id"):
            return _no("not_owner")
        event_type = "request.strategy_released"
        owner_id = actor["id"]
    elif pair == ENTER_FALLBACK:
        system_role = (actor or {}).get("role") == "system"
        if transition_authority != SYSTEM_FALLBACK or not system_role:
            return _no("transition_not_allowed")
        event_type = "request.strategy_transition"
        owner_id = None
    else:
        return _no("transition_not_allowed")

    oid = _oid(request_id)
    if oid is None:
        return _no("not_found")

    extra = [{"client_id": owner_id}] if owner_id else None
    now = _now()
    claimed: Any = await db.requests.find_one_and_update(
        _open_predicate(
            oid, expected_strategy, expected_assignment_version, extra,
        ),
        {"$set": {
            "fulfillment_strategy": target_strategy,
            "fulfillment_strategy_started_at": now,
        }, "$inc": {"assignment_version": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        return _no(await _explain_miss(
            oid, expected_strategy, expected_assignment_version, owner_id,
        ))

    version = claimed.get("assignment_version")
    await log_event(
        request_id,
        event_type,
        actor=actor,
        property_id=claimed.get("property_id"),
        payload={
            "previous_strategy": expected_strategy,
            "new_strategy": target_strategy,
            "reason": reason,
            "timestamp": now,
            "assignment_version": version,
            "fulfillment_strategy_started_at": now,
        },
    )
    return {"ok": True, "reason": None, "request": claimed}


async def claim_open_offer_slot(request_id: str) -> dict:
    """Increment open_offer_count on an open MULTI_OFFER request.

    Does not debit, insert an offer, or change assignment_version.
    """
    oid = _oid(request_id)
    if oid is None:
        return _no("not_found")
    claimed: Any = await db.requests.find_one_and_update(
        {"_id": oid, "status": "open", "fulfillment_strategy": MULTI_OFFER},
        {"$inc": {"open_offer_count": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        reason = await _explain_miss(oid, MULTI_OFFER, 0)
        if reason == "version_mismatch":
            reason = "conflict"
        return _no(reason)
    return {
        "ok": True,
        "reason": None,
        "request": claimed,
        "open_offer_count": claimed.get("open_offer_count"),
    }


async def release_open_offer_slot(request_id: str) -> dict:
    """Decrement after an open offer is withdrawn or an insert fails.

    The counter never goes below zero.
    """
    oid = _oid(request_id)
    if oid is None:
        return _no("not_found")
    claimed: Any = await db.requests.find_one_and_update(
        {"_id": oid, "open_offer_count": {"$gte": 1}},
        {"$inc": {"open_offer_count": -1}},
        return_document=ReturnDocument.AFTER,
    )
    if not claimed:
        return _no("conflict")
    return {
        "ok": True,
        "reason": None,
        "request": claimed,
        "open_offer_count": claimed.get("open_offer_count"),
    }
