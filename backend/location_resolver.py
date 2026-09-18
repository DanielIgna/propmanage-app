"""Resolve a display location with provenance. Read-time, non-destructive.

Priority (display):
  1. property coordinates verified
  2. property coordinates manually supplied but unverified
  3. building coordinates verified
  4. building coordinates from HartaBlocuri / external source, neverified
  5. stored geocoding candidate (property/building)
  6. no coordinates → map unavailable

Does NOT copy building coordinates onto the property document.
"""
from __future__ import annotations

from typing import Optional

from geocoding import (
    SOURCE_GOOGLE,
    SOURCE_HARTABLOCURI,
    SOURCE_MANUAL,
    STATUS_NEVERIFICAT,
    STATUS_UNVERIFIED,
    STATUS_UNAVAILABLE,
    STATUS_VERIFIED,
    _valid_coord,
)

_VERIFIED = {STATUS_VERIFIED, "documented"}


def _pack(lat, lng, *, source, verification_status, derived_from, method,
          extra: Optional[dict] = None) -> dict:
    out = {
        "lat": float(lat),
        "lng": float(lng),
        "source": source,
        "verification_status": verification_status,
        "derived_from": derived_from,
        "method": method,
        "available": True,
    }
    if extra:
        out.update({k: v for k, v in extra.items() if v is not None})
    return out


def _unavailable(reason: str = "no_coordinates") -> dict:
    return {
        "lat": None,
        "lng": None,
        "source": None,
        "verification_status": STATUS_UNAVAILABLE,
        "derived_from": None,
        "method": None,
        "available": False,
        "reason": reason,
    }


def _from_location_obj(loc: dict, derived_from: str) -> Optional[dict]:
    if not loc:
        return None
    lat, lng = loc.get("lat"), loc.get("lng")
    if not (_valid_coord(lat) and _valid_coord(lng)):
        return None
    return _pack(
        lat, lng,
        source=loc.get("source") or SOURCE_MANUAL,
        verification_status=loc.get("verification_status") or STATUS_UNVERIFIED,
        derived_from=loc.get("derived_from") or derived_from,
        method=loc.get("method") or "stored",
        extra={
            "geocoded_at": loc.get("geocoded_at"),
            "google_location_type": loc.get("google_location_type"),
        },
    )


def _from_top_level(entity: dict, derived_from: str, source_default: str = SOURCE_MANUAL) -> Optional[dict]:
    lat, lng = entity.get("lat"), entity.get("lng")
    if not (_valid_coord(lat) and _valid_coord(lng)):
        return None
    loc = entity.get("location") or {}
    return _pack(
        lat, lng,
        source=loc.get("source") or source_default,
        verification_status=loc.get("verification_status") or STATUS_UNVERIFIED,
        derived_from=loc.get("derived_from") or derived_from,
        method=loc.get("method") or "stored",
        extra={"geocoded_at": loc.get("geocoded_at")},
    )


def extract_building_location(building: Optional[dict]) -> Optional[dict]:
    """Return stored building coords with provenance, or None."""
    if not building:
        return None
    ctx = building.get("context") or {}
    ext = ctx.get("external_sources") or {}
    hb = ext.get("hartablocuri") or {}
    hb_raw = hb.get("raw") or {}
    gg = ext.get(SOURCE_GOOGLE) or {}

    lat = ctx.get("lat") if _valid_coord(ctx.get("lat")) else None
    lng = ctx.get("lng") if _valid_coord(ctx.get("lng")) else None
    if lat is None and _valid_coord(hb_raw.get("lat")):
        lat, lng = hb_raw.get("lat"), hb_raw.get("lng")
    if lat is None and _valid_coord(gg.get("lat")):
        lat, lng = gg.get("lat"), gg.get("lng")
    if not (_valid_coord(lat) and _valid_coord(lng)):
        return None

    ctx_status = str(ctx.get("verification_status") or "").lower()
    hb_status = str(hb.get("verification_status") or "").lower()
    has_hb = bool(hb)

    if ctx_status in _VERIFIED:
        source = SOURCE_HARTABLOCURI if has_hb and not gg else (gg.get("source_name") or SOURCE_MANUAL)
        # Verified building context: still label HB when that is the coordinate origin.
        if has_hb and not gg:
            source = SOURCE_HARTABLOCURI
        return _pack(
            lat, lng,
            source=source,
            verification_status=STATUS_VERIFIED,
            derived_from="building",
            method="building_context",
            extra={"building_id": str(building.get("_id") or building.get("id") or "")},
        )

    if has_hb and (
        (lat == hb_raw.get("lat") and lng == hb_raw.get("lng"))
        or (ctx.get("lat") == hb_raw.get("lat") and has_hb)
        or not gg
    ):
        return _pack(
            lat, lng,
            source=SOURCE_HARTABLOCURI,
            verification_status=hb_status or STATUS_NEVERIFICAT,
            derived_from="building",
            method="hartablocuri_import",
            extra={
                "building_id": str(building.get("_id") or building.get("id") or ""),
                "provenance_label": "derivat din clădire · HartaBlocuri · neverificat",
            },
        )

    if gg and _valid_coord(gg.get("lat")):
        return _pack(
            gg.get("lat"), gg.get("lng"),
            source=SOURCE_GOOGLE,
            verification_status=gg.get("verification_status") or STATUS_NEVERIFICAT,
            derived_from="building",
            method="geocoding",
            extra={
                "building_id": str(building.get("_id") or building.get("id") or ""),
                "geocoded_at": gg.get("geocoded_at"),
                "provenance_label": "derivat din clădire · geocoding · neverificat",
            },
        )

    return _pack(
        lat, lng,
        source=ctx.get("source_name") or SOURCE_MANUAL,
        verification_status=ctx_status or STATUS_UNVERIFIED,
        derived_from="building",
        method="building_context",
        extra={"building_id": str(building.get("_id") or building.get("id") or "")},
    )


def extract_property_own_location(prop: Optional[dict]) -> Optional[dict]:
    if not prop:
        return None
    loc = _from_location_obj(prop.get("location") or {}, derived_from="property")
    if loc:
        loc["derived_from"] = loc.get("derived_from") or "property"
        return loc
    return _from_top_level(prop, derived_from="property")


def resolve_property_map_location(prop: Optional[dict],
                                  building: Optional[dict] = None) -> dict:
    """Display location for a property. Never mutates stored documents."""
    own = extract_property_own_location(prop)
    bld = extract_building_location(building)

    if own and str(own.get("verification_status") or "").lower() in _VERIFIED:
        own["priority"] = 1
        return own
    if own:
        # manual / geocoding on the property itself, unverified
        own["priority"] = 2
        return own
    if bld and str(bld.get("verification_status") or "").lower() in _VERIFIED:
        bld["priority"] = 3
        bld["derived"] = True
        return bld
    if bld:
        bld["priority"] = 4 if bld.get("source") == SOURCE_HARTABLOCURI else 5
        bld["derived"] = True
        if bld.get("source") == SOURCE_HARTABLOCURI:
            bld.setdefault("provenance_label", "derivat din clădire · HartaBlocuri · neverificat")
        elif bld.get("source") == SOURCE_GOOGLE:
            bld.setdefault("provenance_label", "derivat din clădire · geocoding · neverificat")
        else:
            bld.setdefault("provenance_label", "derivat din clădire · neverificat")
        return bld
    return _unavailable("no_coordinates")


def resolve_listing_map_location(listing: Optional[dict],
                                 prop: Optional[dict] = None,
                                 building: Optional[dict] = None) -> dict:
    """Public listing map location. Listings are for-sale (exact coords allowed)."""
    listing = listing or {}
    own = _from_location_obj(listing.get("location") or {}, derived_from="listing")
    if not own:
        own = _from_top_level(listing, derived_from="listing")
    if own and str(own.get("verification_status") or "").lower() in _VERIFIED:
        own["priority"] = 1
        return own
    if own:
        own["priority"] = 2
        return own
    resolved = resolve_property_map_location(prop, building)
    if resolved.get("available"):
        # Keep listing-level display fields; provenance stays honest.
        resolved["derived"] = True
        return resolved
    return _unavailable("no_coordinates")


def public_listing_geo_fields(resolved: dict) -> dict:
    """Fields merged into the public listing serializer."""
    if not resolved or not resolved.get("available"):
        return {
            "lat": None,
            "lng": None,
            "location": {
                "available": False,
                "verification_status": resolved.get("verification_status") if resolved else STATUS_UNAVAILABLE,
                "reason": (resolved or {}).get("reason") or "no_coordinates",
            },
        }
    loc = {
        "lat": resolved["lat"],
        "lng": resolved["lng"],
        "source": resolved.get("source"),
        "verification_status": resolved.get("verification_status"),
        "derived_from": resolved.get("derived_from"),
        "method": resolved.get("method"),
        "derived": bool(resolved.get("derived")),
        "available": True,
    }
    if resolved.get("provenance_label"):
        loc["provenance_label"] = resolved["provenance_label"]
    if resolved.get("geocoded_at"):
        loc["geocoded_at"] = resolved["geocoded_at"]
    return {
        "lat": resolved["lat"],
        "lng": resolved["lng"],
        "location": loc,
    }
