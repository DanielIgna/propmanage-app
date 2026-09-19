"""Building Identity Graph — authenticated client pilot (resolve / confirm / reject).

Read-only resolve. Confirm writes only Property→Building plus an additive client
observation. Never overwrites HartaBlocuri or verified values. Never writes
Google onto an existing building from this router.
"""
from __future__ import annotations

import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from building_identity import (
    confirmation_payload,
    identity_profile,
    mongo_candidate_filter,
    parse_query,
    resolve_identity,
)
from db import db
from deps import require_role

logger = logging.getLogger("propmanage.building_identity")
router = APIRouter(prefix="/api/buildings/identity", tags=["building-identity"])


class ResolveIn(BaseModel):
    address: str = Field(..., min_length=3, max_length=400)
    city: Optional[str] = Field(default=None, max_length=80)
    postal_code: Optional[str] = Field(default=None, max_length=12)
    stair: Optional[str] = Field(default=None, max_length=12)
    property_id: Optional[str] = None


class ConfirmIn(BaseModel):
    property_id: str
    building_id: str
    stair: Optional[str] = Field(default=None, max_length=12)
    apartment: Optional[str] = Field(default=None, max_length=12)
    resolver_status: Optional[str] = Field(default=None, max_length=20)
    matched_by: Optional[list] = None


class RejectIn(BaseModel):
    property_id: str
    building_id: str


async def _owned_property(property_id: str, user: dict) -> dict:
    if not property_id or not ObjectId.is_valid(property_id):
        raise HTTPException(400, "property_id invalid")
    prop = await db.properties.find_one({"_id": ObjectId(property_id), "owner_id": user["id"]})
    if not prop:
        raise HTTPException(404, "Property not found")
    return prop


async def _load_candidates(query: dict, extra_ids: Optional[list] = None) -> list:
    filt = mongo_candidate_filter(query)
    found = []
    seen = set()
    if filt:
        async for b in db.buildings.find(filt).limit(40):
            bid = str(b["_id"])
            if bid in seen:
                continue
            seen.add(bid)
            found.append(b)
    for bid in extra_ids or []:
        if not bid or bid in seen or not ObjectId.is_valid(bid):
            continue
        b = await db.buildings.find_one({"_id": ObjectId(bid)})
        if b:
            seen.add(bid)
            found.append(b)
    return found


@router.post("/resolve")
async def resolve_building_identity(data: ResolveIn, user: dict = Depends(require_role("client"))):
    prop = None
    rejected = set()
    extra = []
    if data.property_id:
        prop = await _owned_property(data.property_id, user)
        rejected = {
            str(r.get("building_id"))
            for r in (prop.get("building_identity_rejections") or [])
            if r.get("building_id")
        }
        if prop.get("building_id"):
            extra.append(prop["building_id"])
    address = data.address or (prop or {}).get("address") or ""
    city = data.city or (prop or {}).get("city")
    query = parse_query(address, city=city, postal_code=data.postal_code, stair=data.stair)
    buildings = await _load_candidates(query, extra_ids=extra)
    result = await resolve_identity(
        buildings,
        address=address,
        city=query.get("city") or city,
        postal_code=query.get("postal_code") or data.postal_code,
        stair=query.get("stair") or data.stair,
    )
    result["candidates"] = [
        c for c in result["candidates"] if c.get("building_id") not in rejected
    ]
    result["rejected_ids"] = sorted(rejected)
    result["already_linked_building_id"] = (prop or {}).get("building_id")
    return result


@router.post("/confirm")
async def confirm_building_identity(data: ConfirmIn, user: dict = Depends(require_role("client"))):
    prop = await _owned_property(data.property_id, user)
    if not ObjectId.is_valid(data.building_id):
        raise HTTPException(400, "building_id invalid")
    building = await db.buildings.find_one({"_id": ObjectId(data.building_id)})
    if not building:
        raise HTTPException(404, "Blocul nu există")
    payload = confirmation_payload(
        user, data.property_id, data.building_id,
        stair=data.stair,
        apartment=data.apartment,
        resolver_status=data.resolver_status,
        matched_by=data.matched_by,
    )
    await db.properties.update_one(
        {"_id": prop["_id"], "owner_id": user["id"]},
        {"$set": {
            "building_id": data.building_id,
            "building_link": payload["building_link"],
        }},
    )
    await db.buildings.update_one(
        {"_id": building["_id"]},
        {"$push": {"context.external_sources.client.observations": payload["observation"]}},
    )
    updated_prop = await db.properties.find_one({"_id": prop["_id"]})
    updated_b = await db.buildings.find_one({"_id": building["_id"]})
    return {
        "ok": True,
        "building_id": data.building_id,
        "property_id": data.property_id,
        "confirmation_source": "client",
        "confirmation_status": "declared",
        "confirmed_at": payload["confirmed_at"],
        "confirmed": ["property_belongs_to_building"],
        "not_confirmed": payload["building_link"]["not_confirmed"],
        "identity_profile": identity_profile(updated_b, property_doc=updated_prop),
    }


@router.post("/reject")
async def reject_building_identity(data: RejectIn, user: dict = Depends(require_role("client"))):
    from datetime import datetime, timezone

    prop = await _owned_property(data.property_id, user)
    if not data.building_id:
        raise HTTPException(400, "building_id este obligatoriu")
    rec = {
        "building_id": data.building_id,
        "source": "client",
        "status": "declared",
        "rejected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.properties.update_one(
        {"_id": prop["_id"], "owner_id": user["id"]},
        {"$push": {"building_identity_rejections": rec}},
    )
    return {"ok": True, "rejected": rec}
