"""Server-side address → lat/lng (Google Geocoding API).

Rules:
  * Uses GOOGLE_MAPS_SERVER_API_KEY only. Never the browser key.
  * Never logs the key or a URL that contains it.
  * Never overwrites verified / user-confirmed / manually-verified coordinates.
  * Ambiguous Google results are NOT picked arbitrarily.
  * Failure is non-fatal: caller keeps the address and marks location pending.

Provenance is stored in the existing HartaBlocuri pattern
(`context.external_sources.<source>`) for buildings, and a `location` object
on properties/listings — same vocabulary, not a parallel trust system.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger("propmanage.geocoding")

GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
SOURCE_GOOGLE = "google_geocoding"
SOURCE_HARTABLOCURI = "hartablocuri"
SOURCE_MANUAL = "manual"
SOURCE_SEED = "seed"

STATUS_VERIFIED = "verified"
STATUS_NEVERIFICAT = "neverificat"
STATUS_UNVERIFIED = "unverified"
STATUS_PENDING = "pending"
STATUS_UNAVAILABLE = "unavailable"
STATUS_NEEDS_VERIFICATION = "needs_verification"
STATUS_UNCONFIGURED = "unconfigured"
STATUS_INSUFFICIENT_ADDRESS = "insufficient_address"

# location_type values we accept as a single candidate (not a guess).
_PRECISE_TYPES = {"ROOFTOP", "RANGE_INTERPOLATED"}

_PROTECTED_STATUSES = {STATUS_VERIFIED, "documented"}
_PROTECTED_SOURCES = {
    "verified", "professional_audit", "admin_verified", "user_confirmed",
}

# Secondary unit tokens — kept out of the primary geocoding query so
# "8 D, sc 2" still resolves to the building, not a missing subunit.
_SECONDARY_TAIL = re.compile(
    r"[,;\s]+(?:sc(?:ara)?|ap(?:art(?:ament)?)?|bl(?:oc)?|et(?:aj)?|apt\.?|"
    r"tr(?:onson)?|scara|apartament)\b.*$",
    re.IGNORECASE,
)
_NR_SPACED_LETTER = re.compile(
    r"\b(nr\.?\s*)(\d+)\s+([A-Za-z])\b",
    re.IGNORECASE,
)
_BARE_SPACED_LETTER = re.compile(
    r"\b(\d+)\s+([A-Za-z])\b",
)
_KEY_IN_TEXT = re.compile(r"(key=)[^&\s]+", re.IGNORECASE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(text: str) -> str:
    return _KEY_IN_TEXT.sub(r"\1REDACTED", text or "")


def server_key_configured() -> bool:
    key = (os.environ.get("GOOGLE_MAPS_SERVER_API_KEY") or "").strip()
    return bool(key) and key not in ("CHANGE_ME", "your-key-here", "undefined")


def get_server_key() -> Optional[str]:
    if not server_key_configured():
        return None
    return os.environ.get("GOOGLE_MAPS_SERVER_API_KEY", "").strip()


def normalize_address(address: str) -> str:
    """Canonicalize Romanian street-number variants without dropping the building.

    "8 D" / "8D" / "nr 8 D, sc 2" → primary "… nr. 8D"
    Secondary identifiers (sc, ap, et) are stripped from the geocoding query.
    """
    raw = (address or "").strip()
    if not raw:
        return ""
    text = re.sub(r"\s+", " ", raw)
    text = _SECONDARY_TAIL.sub("", text).strip(" ,;")
    def _nr_repl(m):
        prefix = m.group(1)
        if "nr." not in prefix.lower():
            prefix = re.sub(r"nr", "nr.", prefix, flags=re.I)
        return f"{prefix.strip()} {m.group(2)}{m.group(3).upper()}"
    text = _NR_SPACED_LETTER.sub(_nr_repl, text)
    text = re.sub(r"\bnr(?!\.)\s+", "nr. ", text, flags=re.IGNORECASE)
    text = _BARE_SPACED_LETTER.sub(lambda m: f"{m.group(1)}{m.group(2).upper()}", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;")
    return text


def compose_geocode_query(address: str, city: Optional[str] = None,
                          postal_code: Optional[str] = None,
                          country: str = "România") -> str:
    primary = normalize_address(address)
    parts = []
    if primary:
        parts.append(primary)
    city_n = (city or "").strip()
    if city_n and city_n.lower() not in primary.lower():
        parts.append(city_n)
    pc = (postal_code or "").strip()
    if pc and pc not in primary:
        parts.append(pc)
    if country and country.lower() not in primary.lower():
        parts.append(country)
    return ", ".join(p for p in parts if p)


def address_is_sufficient(address: str, city: Optional[str] = None) -> bool:
    """Refuse geocoding when the query cannot identify a building."""
    text = f"{address or ''} {city or ''}".strip()
    if len(text) < 6:
        return False
    has_street = bool(re.search(
        r"\b(str(?:ada)?|bd\.?|bulevardul|alee[a]?|calea|pia(?:ța|ta)|sos(?:eaua)?)\b",
        text, re.IGNORECASE))
    has_house = bool(re.search(r"\bnr\.?\s*\d", text, re.IGNORECASE))
    has_compact = bool(re.search(r"\b\d+[A-Za-z]\b", text))
    has_postal = bool(re.search(r"\b\d{5,6}\b", text))
    stripped = re.sub(r"\bsector(?:ul)?\s*\d+\b", " ", text, flags=re.IGNORECASE)
    has_other_num = bool(re.search(r"\b\d+\b", stripped))
    if has_street and (has_house or has_compact or has_postal or has_other_num):
        return True
    if has_postal and has_street:
        return True
    return False


def _valid_coord(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and -90 <= float(value) <= 180


def has_stored_coords(entity: dict) -> bool:
    if not entity:
        return False
    loc = entity.get("location") or {}
    if _valid_coord(loc.get("lat")) and _valid_coord(loc.get("lng")):
        return True
    if _valid_coord(entity.get("lat")) and _valid_coord(entity.get("lng")):
        return True
    ctx = entity.get("context") or {}
    if _valid_coord(ctx.get("lat")) and _valid_coord(ctx.get("lng")):
        return True
    hb = ((ctx.get("external_sources") or {}).get("hartablocuri") or {}).get("raw") or {}
    if _valid_coord(hb.get("lat")) and _valid_coord(hb.get("lng")):
        return True
    gg = (ctx.get("external_sources") or {}).get(SOURCE_GOOGLE) or {}
    if _valid_coord(gg.get("lat")) and _valid_coord(gg.get("lng")):
        return True
    return False


def coords_are_protected(entity: dict) -> bool:
    """Never overwrite verified / user-confirmed / documented coordinates."""
    if not entity:
        return False
    loc = entity.get("location") or {}
    statuses = {
        str(loc.get("verification_status") or "").lower(),
        str(entity.get("location_verification_status") or "").lower(),
        str((entity.get("context") or {}).get("location_verification_status") or "").lower(),
    }
    sources = {
        str(loc.get("source") or "").lower(),
        str(entity.get("location_source") or "").lower(),
        str((entity.get("context") or {}).get("location_source") or "").lower(),
    }
    if statuses & _PROTECTED_STATUSES:
        return True
    if sources & _PROTECTED_SOURCES:
        return True
    if loc.get("verified") is True:
        return True
    ctx = entity.get("context") or {}
    ctx_status = str(ctx.get("verification_status") or "").lower()
    if ctx_status in _PROTECTED_STATUSES and has_stored_coords(entity):
        return True
    return False


def build_location_payload(lat: float, lng: float, *, source: str,
                           verification_status: str, derived_from: str,
                           method: str, extra: Optional[dict] = None) -> dict:
    payload = {
        "lat": round(float(lat), 6),
        "lng": round(float(lng), 6),
        "source": source,
        "verification_status": verification_status,
        "derived_from": derived_from,
        "method": method,
        "geocoded_at": _now_iso() if method in ("geocoding", SOURCE_GOOGLE) else None,
    }
    if extra:
        payload.update(extra)
    return payload


def pending_location(status: str, reason: str) -> dict:
    return {
        "lat": None,
        "lng": None,
        "source": None,
        "verification_status": status,
        "derived_from": "address",
        "method": "geocoding",
        "geocoded_at": _now_iso(),
        "reason": reason,
    }


def _classify_google_results(data: dict) -> dict:
    status = (data or {}).get("status") or "UNKNOWN"
    results = (data or {}).get("results") or []
    if status not in ("OK", "ZERO_RESULTS"):
        # REQUEST_DENIED / OVER_QUERY_LIMIT / INVALID_REQUEST — not fatal to the caller
        err = (data or {}).get("error_message") or ""
        # error_message is Google's public reason (API disabled / restriction), never a secret.
        reason = f"google_status:{status}"
        if err:
            reason = f"{reason}:{err.split('.')[0][:80]}"
        return pending_location(STATUS_UNAVAILABLE, reason)
    if status == "ZERO_RESULTS" or not results:
        return pending_location(STATUS_UNAVAILABLE, "zero_results")
    if len(results) != 1:
        return pending_location(STATUS_NEEDS_VERIFICATION, f"ambiguous_results:{len(results)}")
    hit = results[0]
    geom = hit.get("geometry") or {}
    loc = geom.get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    loc_type = geom.get("location_type") or ""
    if not (_valid_coord(lat) and _valid_coord(lng)):
        return pending_location(STATUS_UNAVAILABLE, "missing_latlng")
    if loc_type not in _PRECISE_TYPES:
        return pending_location(STATUS_NEEDS_VERIFICATION, f"imprecise:{loc_type or 'unknown'}")
    return build_location_payload(
        lat, lng,
        source=SOURCE_GOOGLE,
        verification_status=STATUS_NEVERIFICAT,
        derived_from="address",
        method="geocoding",
        extra={
            "google_location_type": loc_type,
            "google_place_id": hit.get("place_id"),
            "formatted_address": hit.get("formatted_address"),
            "partial_match": bool(hit.get("partial_match")),
        },
    )


async def geocode_address(address: str, *, city: Optional[str] = None,
                          postal_code: Optional[str] = None,
                          country: str = "România",
                          client: Optional[httpx.AsyncClient] = None) -> dict:
    """Geocode an address. Returns a location payload; never raises for Google errors."""
    if not address_is_sufficient(address, city):
        return pending_location(STATUS_INSUFFICIENT_ADDRESS, "address_insufficient")
    key = get_server_key()
    if not key:
        logger.info("geocoding skipped: server key not configured")
        return pending_location(STATUS_UNCONFIGURED, "missing_server_key")
    query = compose_geocode_query(address, city=city, postal_code=postal_code, country=country)
    params = {
        "address": query,
        "key": key,
        "region": "ro",
        "language": "ro",
        "components": "country:RO",
    }
    own_client = client is None
    try:
        cli = client or httpx.AsyncClient(timeout=12.0)
        try:
            resp = await cli.get(GOOGLE_GEOCODE_URL, params=params)
        finally:
            if own_client:
                await cli.aclose()
        # Never log params (contain the key) or the request URL.
        logger.info("geocoding response status_code=%s google_body_status_pending_parse", resp.status_code)
        if resp.status_code >= 400:
            logger.warning("geocoding http_error status=%s", resp.status_code)
            return pending_location(STATUS_UNAVAILABLE, f"http_{resp.status_code}")
        data = resp.json()
        gstatus = data.get("status")
        n = len(data.get("results") or [])
        logger.info("geocoding google_status=%s results=%s", gstatus, n)
        out = _classify_google_results(data)
        out["query"] = query
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("geocoding failed: %s", _redact(type(exc).__name__))
        return pending_location(STATUS_UNAVAILABLE, "exception")


def should_write_coords(entity: dict, candidate: dict) -> bool:
    if coords_are_protected(entity):
        return False
    if has_stored_coords(entity):
        return False
    if not candidate:
        return False
    if not (_valid_coord(candidate.get("lat")) and _valid_coord(candidate.get("lng"))):
        return False
    return True


def property_location_update(candidate: dict) -> dict:
    """Fields to $set on a property or listing. Keeps top-level lat/lng for GIS/map."""
    loc = {
        "lat": candidate.get("lat"),
        "lng": candidate.get("lng"),
        "source": candidate.get("source") or SOURCE_GOOGLE,
        "verification_status": candidate.get("verification_status") or STATUS_NEVERIFICAT,
        "derived_from": candidate.get("derived_from") or "address",
        "method": candidate.get("method") or "geocoding",
        "geocoded_at": candidate.get("geocoded_at") or _now_iso(),
    }
    for k in ("google_location_type", "google_place_id", "formatted_address", "query", "reason"):
        if candidate.get(k) is not None:
            loc[k] = candidate[k]
    return {
        "lat": loc["lat"],
        "lng": loc["lng"],
        "location": loc,
    }


def building_location_update(building: dict, candidate: dict) -> dict:
    """Non-destructive merge into building.context + external_sources.google_geocoding."""
    ctx = dict(building.get("context") or {})
    ext = dict(ctx.get("external_sources") or {})
    rec = {
        "source_name": SOURCE_GOOGLE,
        "verification_status": candidate.get("verification_status") or STATUS_NEVERIFICAT,
        "derived_from": candidate.get("derived_from") or "address",
        "method": candidate.get("method") or "geocoding",
        "geocoded_at": candidate.get("geocoded_at") or _now_iso(),
        "lat": candidate.get("lat"),
        "lng": candidate.get("lng"),
        "query": candidate.get("query"),
        "google_location_type": candidate.get("google_location_type"),
        "google_place_id": candidate.get("google_place_id"),
        "formatted_address": candidate.get("formatted_address"),
    }
    ext[SOURCE_GOOGLE] = rec
    ctx["external_sources"] = ext
    if not _valid_coord(ctx.get("lat")):
        ctx["lat"] = candidate.get("lat")
    if not _valid_coord(ctx.get("lng")):
        ctx["lng"] = candidate.get("lng")
    ctx.setdefault("verification_status", STATUS_UNVERIFIED)
    ctx["updated_at"] = _now_iso()
    return {"context": ctx}


async def safe_geocode_entity(entity: dict, address: str, *,
                              city: Optional[str] = None,
                              postal_code: Optional[str] = None) -> dict:
    """Geocode helper that never overwrites protected coords. Returns {applied, location}."""
    if coords_are_protected(entity):
        return {"applied": False, "reason": "protected", "location": None}
    if has_stored_coords(entity):
        return {"applied": False, "reason": "already_has_coords", "location": None}
    loc = await geocode_address(address, city=city, postal_code=postal_code)
    return {
        "applied": should_write_coords(entity, loc),
        "reason": loc.get("verification_status") if not should_write_coords(entity, loc) else "ok",
        "location": loc,
    }
