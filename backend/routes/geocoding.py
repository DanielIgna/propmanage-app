"""Admin-only server-side geocoding endpoints.

Never exposes GOOGLE_MAPS_SERVER_API_KEY. Preview/apply only; no publish.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from geocoding import (
    address_is_sufficient,
    building_location_update,
    coords_are_protected,
    geocode_address,
    has_stored_coords,
    property_location_update,
    server_key_configured,
    should_write_coords,
)

from location_resolver import resolve_listing_map_location

logger = logging.getLogger("propmanage.geocoding.routes")

router = APIRouter(prefix="/api/admin/geocoding", tags=["geocoding"])


class PreviewIn(BaseModel):
    address: str = Field(..., min_length=3, max_length=400)
    city: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=16)


class ApplyIn(BaseModel):
    entity_type: str = Field(..., pattern="^(property|building|listing)$")
    entity_id: str = Field(..., min_length=8, max_length=40)
    address: Optional[str] = Field(default=None, max_length=400)
    city: Optional[str] = Field(default=None, max_length=120)
    postal_code: Optional[str] = Field(default=None, max_length=16)


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(404, "Entitate inexistentă")


async def _load_entity(entity_type: str, entity_id: str) -> dict:
    coll = {
        "property": db.properties,
        "building": db.buildings,
        "listing": db.verified_estate_listings,
    }[entity_type]
    doc = await coll.find_one({"_id": _oid(entity_id)})
    if not doc:
        raise HTTPException(404, "Entitate inexistentă")
    return doc


def _address_of(entity_type: str, entity: dict, override: Optional[str] = None) -> tuple[str, Optional[str]]:
    if override:
        return override, entity.get("city")
    if entity_type == "building":
        return (entity.get("address") or ""), entity.get("city")
    if entity_type == "listing":
        return (entity.get("address") or ""), entity.get("city")
    return (entity.get("address") or ""), entity.get("city")


async def apply_geocoding_to_entity(entity_type: str, entity: dict, *,
                                    address: Optional[str] = None,
                                    city: Optional[str] = None,
                                    postal_code: Optional[str] = None) -> dict:
    """Apply geocoding if allowed. Returns a structured result; never raises on Google failure."""
    addr, cty = _address_of(entity_type, entity, address)
    city = city or cty
    if coords_are_protected(entity):
        return {"applied": False, "reason": "protected", "entity_type": entity_type,
                "entity_id": str(entity["_id"]), "location": None}
    if has_stored_coords(entity):
        return {"applied": False, "reason": "already_has_coords", "entity_type": entity_type,
                "entity_id": str(entity["_id"]), "location": None}
    loc = await geocode_address(addr, city=city, postal_code=postal_code)
    applied = should_write_coords(entity, loc)
    if applied:
        coll = {
            "property": db.properties,
            "building": db.buildings,
            "listing": db.verified_estate_listings,
        }[entity_type]
        if entity_type == "building":
            update = building_location_update(entity, loc)
        else:
            update = property_location_update(loc)
        await coll.update_one({"_id": entity["_id"]}, {"$set": update})
    return {
        "applied": applied,
        "reason": "ok" if applied else (loc.get("verification_status") or loc.get("reason")),
        "entity_type": entity_type,
        "entity_id": str(entity["_id"]),
        "location": loc,
    }


async def geocode_property_after_create(prop_id: str, address: str, city: Optional[str] = None) -> None:
    """Fire-and-forget: never blocks / fails property creation."""
    try:
        doc = await db.properties.find_one({"_id": ObjectId(prop_id)})
        if not doc:
            return
        await apply_geocoding_to_entity("property", doc, address=address, city=city)
    except Exception as exc:  # noqa: BLE001
        logger.warning("geocode_property_after_create skipped: %s", type(exc).__name__)


async def geocode_building_after_create(building_id: str, address: str, city: Optional[str] = None) -> None:
    try:
        doc = await db.buildings.find_one({"_id": ObjectId(building_id)})
        if not doc:
            return
        await apply_geocoding_to_entity("building", doc, address=address, city=city)
    except Exception as exc:  # noqa: BLE001
        logger.warning("geocode_building_after_create skipped: %s", type(exc).__name__)


def schedule_geocode_property(prop_id: str, address: str, city: Optional[str] = None) -> None:
    try:
        asyncio.create_task(geocode_property_after_create(prop_id, address, city))
    except Exception:  # noqa: BLE001
        logger.warning("schedule geocode property failed")


def schedule_geocode_building(building_id: str, address: str, city: Optional[str] = None) -> None:
    try:
        asyncio.create_task(geocode_building_after_create(building_id, address, city))
    except Exception:  # noqa: BLE001
        logger.warning("schedule geocode building failed")


@router.get("/status")
async def geocoding_status(user: dict = Depends(require_role("admin", "operator"))):
    _ = user
    return {
        "configured": server_key_configured(),
        "provider": "google" if server_key_configured() else None,
        "browser_key_used_for_geocoding": False,
        "note": "Geocoding folosește exclusiv GOOGLE_MAPS_SERVER_API_KEY. Cheia nu este expusă.",
    }


@router.post("/preview")
async def geocoding_preview(body: PreviewIn, user: dict = Depends(require_role("admin", "operator"))):
    _ = user
    loc = await geocode_address(body.address, city=body.city, postal_code=body.postal_code)
    # Strip anything that could look like a secret; query is the normalized address only.
    safe = {k: v for k, v in loc.items() if k not in ("key", "api_key")}
    return {"location": safe, "configured": server_key_configured()}


@router.post("/apply")
async def geocoding_apply(body: ApplyIn, user: dict = Depends(require_role("admin", "operator"))):
    _ = user
    entity = await _load_entity(body.entity_type, body.entity_id)
    return await apply_geocoding_to_entity(
        body.entity_type, entity,
        address=body.address, city=body.city, postal_code=body.postal_code,
    )


# Known seed coordinates for the two demo published listings (from seed_demo_listings).
# Applied only when geocoding cannot produce a precise candidate AND the listing
# still has no coords. Provenance: manual/seed, neverificat — never "verified".
_SEED_LISTING_COORDS = {
    ("Apartament Premium 3 camere · Aviatorilor", "Bd. Aviatorilor, Sector 1"): {
        "lat": 44.4632, "lng": 26.0894,
        "source": "seed", "verification_status": "neverificat",
        "derived_from": "address", "method": "seed",
    },
    ("Vilă verificată · Pipera Premium", "Str. Erou Iancu Nicolae, Pipera"): {
        "lat": 44.5215, "lng": 26.1278,
        "source": "seed", "verification_status": "neverificat",
        "derived_from": "address", "method": "seed",
    },
}


NEGOIU_BUILDING_ID = "6a7724892e6529db42e95df1"
NEGOIU_LISTING_ID = "6a2d5857a791eb32710f9ffa"
NEGOIU_PROPERTY_ID = "6a367bbb23f65c42a043a0b5"
NEGOIU_GEOCODE_ADDRESS = "Aleea Negoiu nr 8D, Cluj-Napoca, 400676, România"


async def backfill_verified_listings() -> dict:
    """Populate coords for the 4 existing listings. Non-destructive. Preview DB only when called."""
    report = {"listings": [], "building": None, "links": []}
    # 1) Geocode the real Negoiu 8D building (PropManage-only, no HB coords).
    try:
        b = await db.buildings.find_one({"_id": ObjectId(NEGOIU_BUILDING_ID)})
    except Exception:
        b = None
    if b:
        bres = await apply_geocoding_to_entity(
            "building", b,
            address="Aleea Negoiu nr 8D sc 2",
            city="Cluj-Napoca",
            postal_code="400676",
        )
        report["building"] = bres
    # 2) Link the Negoiu draft listing to the existing building (non-commercial).
    listing_n = await db.verified_estate_listings.find_one({"_id": ObjectId(NEGOIU_LISTING_ID)})
    if listing_n and not listing_n.get("building_id") and b:
        await db.verified_estate_listings.update_one(
            {"_id": listing_n["_id"]},
            {"$set": {
                "building_id": NEGOIU_BUILDING_ID,
                "property_id": NEGOIU_PROPERTY_ID,
            }},
        )
        report["links"].append({
            "listing_id": NEGOIU_LISTING_ID,
            "building_id": NEGOIU_BUILDING_ID,
            "property_id": NEGOIU_PROPERTY_ID,
            "action": "linked_existing_building",
        })
    # 3) Walk all 4 listings.
    async for listing in db.verified_estate_listings.find({}):
        title = listing.get("title") or ""
        addr = listing.get("address") or ""
        city = listing.get("city") or ""
        item = {
            "id": str(listing["_id"]),
            "title": title,
            "status": listing.get("status"),
            "address": addr,
        }
        # Prefer linked building coords as display fallback — do not copy onto listing.
        bid = listing.get("building_id") or (NEGOIU_BUILDING_ID if str(listing["_id"]) == NEGOIU_LISTING_ID else None)
        building = None
        if bid:
            try:
                building = await db.buildings.find_one({"_id": ObjectId(bid)})
            except Exception:
                building = None
        prop = None
        if listing.get("property_id"):
            try:
                prop = await db.properties.find_one({"_id": ObjectId(listing["property_id"])})
            except Exception:
                prop = None
        resolved = resolve_listing_map_location(listing, prop, building)
        if resolved.get("available"):
            item["result"] = "uses_existing_or_building_fallback"
            item["location"] = {k: resolved.get(k) for k in
                                ("lat", "lng", "source", "verification_status", "derived_from", "method", "derived")}
            report["listings"].append(item)
            continue
        applied = await apply_geocoding_to_entity("listing", listing, address=addr, city=city)
        item["geocode"] = {
            "applied": applied.get("applied"),
            "reason": applied.get("reason"),
            "verification_status": (applied.get("location") or {}).get("verification_status"),
        }
        if applied.get("applied"):
            item["result"] = "geocoded"
            report["listings"].append(item)
            continue
        seed = _SEED_LISTING_COORDS.get((title, addr.strip()))
        listing2 = await db.verified_estate_listings.find_one({"_id": listing["_id"]})
        if seed and listing2 and not has_stored_coords(listing2) and not coords_are_protected(listing2):
            from geocoding import property_location_update as _plu
            payload = dict(seed)
            upd = _plu(payload)
            await db.verified_estate_listings.update_one({"_id": listing["_id"]}, {"$set": upd})
            item["result"] = "seed_coords_restored_neverificat"
            item["location"] = seed
        elif not address_is_sufficient(addr, city):
            item["result"] = "pending_insufficient_address"
        else:
            item["result"] = f"not_applied:{applied.get('reason')}"
        report["listings"].append(item)
    return report


@router.post("/backfill-listings")
async def geocoding_backfill_listings(user: dict = Depends(require_role("admin"))):
    """One-shot, non-destructive populate for the 4 existing listings. Admin only."""
    return await backfill_verified_listings()
