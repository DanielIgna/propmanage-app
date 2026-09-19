"""Building Identity Resolver — pilot (PropManage + HartaBlocuri + Google + client).

Reuses the canonical `buildings` collection. Does not create a parallel building
system. Resolve is read-only. Confirm writes only:
  * property.building_id + property.building_link (relation provenance)
  * an additive client observation under building.context.external_sources.client

Never overwrites HartaBlocuri or verified values. Never auto-confirms a match.

Match status (no numeric score):
  probable  — same street + locality + house number, plus at least one of
              {spatial ≤ 80 m, HartaBlocuri identity, name token}
  candidate — same street + locality + house number
              OR same street + locality + spatial ≤ 150 m + name token
  none      — otherwise

HartaBlocuri on the same street but a different house number is not a candidate.

8 vs 8D is recorded as a difference, not a rejection.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from geocoding import (
    SOURCE_GOOGLE,
    _valid_coord,
    geocode_address,
    normalize_address,
)
from hartablocuri_import import _haversine_m, _norm
from hartablocuri_read_layer import build_truth_layer

SOURCE_CLIENT = "client"
SOURCE_HARTABLOCURI = "hartablocuri"
SOURCE_PROPMANAGE = "propmanage"

STATUS_DECLARED = "declared"
STATUS_NEVERIFICAT = "neverificat"
STATUS_CANDIDATE = "candidate"
STATUS_PROBABLE = "probable"
STATUS_CONFIRMED = "confirmed"

_HOUSE = re.compile(r"\b(?:nr\.?\s*)?(\d+)([A-Za-z])?\b", re.IGNORECASE)
_STAIR = re.compile(r"\b(?:sc|scara)\s*\.?\s*(\d+|[A-Za-z])\b", re.IGNORECASE)
_POSTAL = re.compile(r"\b(\d{5,6})\b")
_STREET_STOP = {
    "nr", "numar", "numarul", "strada", "str", "aleea", "alee", "bd", "bulevardul",
    "calea", "sos", "soseaua", "piata", "bloc", "bl", "sc", "scara", "ap", "cluj",
    "napoca", "romania", "municipiu", "cartier",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_STAIR_TOKENS = {"sc", "scara"}
_AP_TOKENS = {"ap", "apartament", "apartamentul"}
_UNIT_NUM = re.compile(r"^\d+[a-z]?$", re.IGNORECASE)
_STAIR_COMPACT = re.compile(r"^sc(\d+[a-z]?|[a-z])$", re.IGNORECASE)
_AP_COMPACT = re.compile(r"^ap(\d+[a-z]?)$", re.IGNORECASE)


def detect_unit_granularity(*texts: Optional[str]) -> dict:
    """Detect stair/apartment markers as address tokens — never a substring of a street.

    "sc 2" / "scara 2" / "ap. 25" → granular.
    "Scărișoara" → token "scarisioara", not "sc".
    """
    blob = " ".join(str(t) for t in texts if t)
    tokens = _norm(blob).split()
    stair = None
    apartment = None
    has_stair = has_apartment = False

    def _take_label(nxt: str) -> Optional[str]:
        if not nxt:
            return None
        if _UNIT_NUM.fullmatch(nxt) or re.fullmatch(r"[a-z]", nxt):
            return nxt
        return None

    for i, tok in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        compact_sc = _STAIR_COMPACT.fullmatch(tok)
        if tok in _STAIR_TOKENS or compact_sc:
            has_stair = True
            label = compact_sc.group(1) if compact_sc else _take_label(nxt)
            if label and stair is None:
                stair = label
        compact_ap = _AP_COMPACT.fullmatch(tok)
        if tok in _AP_TOKENS or compact_ap:
            has_apartment = True
            label = compact_ap.group(1) if compact_ap else _take_label(nxt)
            if label and apartment is None:
                apartment = label
    return {
        "is_granular": has_stair or has_apartment,
        "has_stair": has_stair,
        "has_apartment": has_apartment,
        "stair": stair,
        "apartment": apartment,
    }


def address_has_unit_granularity(*texts: Optional[str]) -> bool:
    return detect_unit_granularity(*texts)["is_granular"]


async def resolve_from_db(db, address: str, *, city: Optional[str] = None,
                          postal_code: Optional[str] = None,
                          stair: Optional[str] = None,
                          extra_ids: Optional[list] = None) -> dict:
    """Reuse the identity resolver against existing buildings. Read-only."""
    query = parse_query(address, city=city, postal_code=postal_code, stair=stair)
    found, seen = [], set()
    filt = mongo_candidate_filter(query)
    if filt:
        async for b in db.buildings.find(filt).limit(40):
            bid = str(b["_id"])
            if bid in seen:
                continue
            seen.add(bid)
            found.append(b)
    for bid in extra_ids or []:
        if not bid or bid in seen:
            continue
        from bson import ObjectId
        if not ObjectId.is_valid(bid):
            continue
        b = await db.buildings.find_one({"_id": ObjectId(bid)})
        if b:
            seen.add(bid)
            found.append(b)
    return await resolve_identity(
        found, address=address, city=query.get("city") or city,
        postal_code=query.get("postal_code") or postal_code,
        stair=query.get("stair") or stair,
    )


async def granular_create_guard(db, *, name: Optional[str], address: Optional[str],
                                city: Optional[str] = None) -> Optional[dict]:
    """If name/address encode entrance/unit, do not create a Building. Return choices."""
    gran = detect_unit_granularity(name, address)
    if not gran["is_granular"]:
        return None
    resolved = await resolve_from_db(
        db, address or name or "", city=city, stair=gran.get("stair"),
    )
    candidates = resolved.get("candidates") or []
    if candidates:
        code = "granular_address_needs_choice"
        message = "Există clădiri candidate. Alege / confirmă clădirea."
    else:
        code = "granular_address_needs_building"
        message = ("Adresa conține scară sau apartament. Introduceți clădirea fără sc/ap "
                   "sau alegeți o clădire existentă.")
    return {
        "created": False,
        "code": code,
        "message": message,
        "granularity": {
            "stair": gran.get("stair"),
            "apartment": gran.get("apartment"),
            "has_stair": gran["has_stair"],
            "has_apartment": gran["has_apartment"],
        },
        "candidates": candidates,
        "auto_confirmed": False,
    }


def parse_query(address: str, city: Optional[str] = None,
                postal_code: Optional[str] = None,
                stair: Optional[str] = None) -> dict:
    raw = (address or "").strip()
    primary = normalize_address(raw)
    folded = _norm(primary)
    house_n, suffix = None, None
    for m in _HOUSE.finditer(primary):
        if len(m.group(1)) >= 5:
            continue  # postal / long numeric tokens are not house numbers
        house_n, suffix = m.group(1), (m.group(2) or "").upper() or None
        break
    if not stair:
        sm = _STAIR.search(raw)
        stair = sm.group(1) if sm else None
    if not postal_code:
        pm = _POSTAL.search(raw)
        postal_code = pm.group(1) if pm else None
    city = (city or "").strip() or None
    if not city and re.search(r"\bcluj[\s-]?napoca\b", folded):
        city = "Cluj-Napoca"
    tokens = [t for t in folded.split() if t not in _STREET_STOP and not re.fullmatch(r"\d+[a-z]?", t)]
    return {
        "raw": raw,
        "normalized": primary,
        "folded": folded,
        "street_tokens": tokens,
        "house_number": house_n,
        "suffix": suffix,
        "city": city,
        "postal_code": (str(postal_code).strip() if postal_code else None),
        "stair": (str(stair).strip() if stair else None),
    }


def _building_address_text(building: dict) -> str:
    ctx = building.get("context") or {}
    hb = ((ctx.get("external_sources") or {}).get("hartablocuri") or {})
    raw = hb.get("raw") or {}
    parts = [
        building.get("address"),
        building.get("name"),
        raw.get("adresa"),
        raw.get("nume"),
        ctx.get("norm_address"),
    ]
    return " ".join(str(p) for p in parts if p)


def _building_city(building: dict) -> str:
    ctx = building.get("context") or {}
    hb = ((ctx.get("external_sources") or {}).get("hartablocuri") or {}).get("raw") or {}
    return (building.get("city") or hb.get("city") or ctx.get("city") or "").strip()


def _building_coords(building: dict) -> tuple[Optional[float], Optional[float]]:
    ctx = building.get("context") or {}
    hb = ((ctx.get("external_sources") or {}).get("hartablocuri") or {}).get("raw") or {}
    gg = (ctx.get("external_sources") or {}).get(SOURCE_GOOGLE) or {}
    for lat, lng in (
        (ctx.get("lat"), ctx.get("lng")),
        (hb.get("lat"), hb.get("lng")),
        (gg.get("lat"), gg.get("lng")),
        (building.get("lat"), building.get("lng")),
    ):
        if _valid_coord(lat) and _valid_coord(lng):
            return float(lat), float(lng)
    return None, None


def _token_overlap(query_tokens: list[str], text: str) -> bool:
    folded = _norm(text)
    if not query_tokens or not folded:
        return False
    return all(t in folded for t in query_tokens if len(t) >= 4) or (
        any(t in folded for t in query_tokens if len(t) >= 5)
    )


def classify_building(query: dict, building: dict, *, google: Optional[dict] = None) -> Optional[dict]:
    """Return a match candidate or None. Never status=confirmed."""
    text = _building_address_text(building)
    folded = _norm(text)
    b_city = _building_city(building)
    street = _token_overlap(query["street_tokens"], text)
    locality = False
    q_city = _norm(query.get("city") or "")
    if q_city and _norm(b_city):
        locality = q_city in _norm(b_city) or _norm(b_city) in q_city
    elif q_city and q_city in folded:
        locality = True
    elif not q_city:
        locality = True  # city omitted — do not fail the street match

    b_parsed = parse_query(building.get("address") or "", b_city)
    hb_addr = (((building.get("context") or {}).get("external_sources") or {}).get("hartablocuri") or {}).get("raw") or {}
    if hb_addr.get("adresa"):
        hb_parsed = parse_query(hb_addr["adresa"], hb_addr.get("city") or b_city)
        if not b_parsed.get("house_number"):
            b_parsed = hb_parsed

    number = bool(query.get("house_number") and b_parsed.get("house_number")
                  and query["house_number"] == b_parsed["house_number"])
    suffix_same = (query.get("suffix") or None) == (b_parsed.get("suffix") or None)
    suffix_conflict = bool(query.get("house_number") and b_parsed.get("house_number")
                           and query["house_number"] == b_parsed["house_number"]
                           and (query.get("suffix") or "") != (b_parsed.get("suffix") or ""))

    blat, blng = _building_coords(building)
    glat = (google or {}).get("lat")
    glng = (google or {}).get("lng")
    distance_m = None
    spatial_near = spatial_close = False
    if _valid_coord(blat) and _valid_coord(blng) and _valid_coord(glat) and _valid_coord(glng):
        distance_m = round(_haversine_m(blat, blng, glat, glng), 1)
        spatial_near = distance_m <= 80
        spatial_close = distance_m <= 150

    ctx = building.get("context") or {}
    ext = ctx.get("external_sources") or {}
    has_hb = bool(ext.get("hartablocuri"))
    name = (building.get("name") or hb_addr.get("nume") or "")
    name_folded = _norm(name)
    name_hit = bool(name_folded) and any(
        t in name_folded for t in query["street_tokens"] if len(t) >= 4
    )

    signals = []
    if street:
        signals.append("street")
    if locality:
        signals.append("locality")
    if number:
        signals.append("address_number")
    if suffix_same and query.get("suffix"):
        signals.append("address_suffix")
    if spatial_near:
        signals.append("spatial_proximity")
    elif spatial_close:
        signals.append("spatial_proximity_loose")
    if has_hb:
        signals.append("external_source")
    if name_hit:
        signals.append("name")

    differences = []
    if suffix_conflict:
        differences.append({
            "field": "address_number",
            "client": f"{query['house_number']}{query.get('suffix') or ''}",
            "hartablocuri": f"{b_parsed.get('house_number') or ''}{b_parsed.get('suffix') or ''}",
            "note": "Sufixul de adresă diferă (ex. 8D vs 8). Nu respinge candidatul.",
        })
    q_addr = query.get("normalized")
    hb_only = hb_addr.get("adresa")
    if q_addr and hb_only and _norm(q_addr) != _norm(hb_only):
        differences.append({
            "field": "address",
            "client": q_addr,
            "hartablocuri": hb_only,
            "google": (google or {}).get("formatted_address"),
        })

    if street and locality and number and (spatial_near or has_hb or name_hit):
        status = STATUS_PROBABLE
    elif street and locality and number:
        status = STATUS_CANDIDATE
    elif street and locality and spatial_close and name_hit:
        status = STATUS_CANDIDATE
    else:
        return None

    return {
        "building_id": str(building.get("_id") or building.get("id") or ""),
        "name": building.get("name") or hb_addr.get("nume"),
        "address": building.get("address") or hb_addr.get("adresa"),
        "city": b_city or None,
        "status": status,
        "matched_by": signals,
        "differences": differences,
        "distance_m": distance_m,
        "sources_present": {
            SOURCE_PROPMANAGE: True,
            SOURCE_HARTABLOCURI: has_hb,
            SOURCE_GOOGLE: bool(google and _valid_coord(google.get("lat"))),
        },
        "auto_confirmed": False,
    }


def hartablocuri_facts(building: dict) -> Optional[dict]:
    hb = ((building.get("context") or {}).get("external_sources") or {}).get("hartablocuri")
    if not hb:
        return None
    raw = hb.get("raw") or {}
    plans = []
    for url in hb.get("plan_urls") or []:
        plans.append({
            "url": url,
            "source": "HartaBlocuri",
            "verification_status": STATUS_NEVERIFICAT,
            "local_copy": False,
        })
    return {
        "source": "HartaBlocuri",
        "source_record_id": hb.get("source_record_id"),
        "verification_status": hb.get("verification_status") or STATUS_NEVERIFICAT,
        "disclaimer": "Aceste informații provin din HartaBlocuri și nu au fost verificate de PropManage.",
        "reference_url": hb.get("reference_url"),
        "fields": {
            "name": raw.get("nume"),
            "address": raw.get("adresa"),
            "neighborhood": raw.get("neighborhood"),
            "uat": raw.get("uat"),
            "height_regime": raw.get("regim_inaltime"),
            "lift": raw.get("lift"),
            "stairs": raw.get("scari"),
            "levels": raw.get("niveluri"),
            "apartments": raw.get("apartamente"),
            "year_estimated": raw.get("construction_year") or raw.get("an_finalizare_raw"),
            "era": raw.get("era"),
            "structure": raw.get("structura"),
            "project": raw.get("proiect"),
        },
        "plans": plans,
        "truth_layer": build_truth_layer(raw),
    }


def mongo_candidate_filter(query: dict) -> Optional[dict]:
    """Narrow building search. None means do not scan the collection."""
    street_or = []
    for t in query.get("street_tokens") or []:
        if len(t) < 4:
            continue
        rx = {"$regex": re.escape(t), "$options": "i"}
        street_or.extend([
            {"address": rx},
            {"name": rx},
            {"context.norm_address": rx},
            {"context.external_sources.hartablocuri.raw.adresa": rx},
            {"context.external_sources.hartablocuri.raw.nume": rx},
        ])
    if not street_or:
        return None
    filt: dict = {"$or": street_or}
    house = query.get("house_number")
    if house:
        rxh = {"$regex": rf"\b{re.escape(house)}(?![0-9])", "$options": "i"}
        filt = {"$and": [filt, {"$or": [
            {"address": rxh},
            {"name": rxh},
            {"context.external_sources.hartablocuri.raw.adresa": rxh},
        ]}]}
    return filt


def _sanitize_client_observations(observations: list, *, property_id: Optional[str]) -> list:
    out = []
    for obs in observations or []:
        if not isinstance(obs, dict):
            continue
        item = {
            "source": SOURCE_CLIENT,
            "verification_status": obs.get("verification_status") or STATUS_DECLARED,
            "created_at": obs.get("created_at"),
            "relation": obs.get("relation"),
            "fields": dict(obs.get("fields") or {}),
        }
        if property_id and str(obs.get("property_id") or "") == str(property_id):
            item["property_id"] = property_id
            item["mine"] = True
        out.append(item)
    return out


def _address_conflicts(building: dict, property_doc: Optional[dict],
                       google: Optional[dict]) -> list:
    ctx = building.get("context") or {}
    existing = list(ctx.get("conflicts") or [])
    hb = ((ctx.get("external_sources") or {}).get("hartablocuri") or {}).get("raw") or {}
    values = []
    if building.get("address"):
        values.append({"source": SOURCE_PROPMANAGE, "value": building.get("address")})
    if (property_doc or {}).get("address"):
        values.append({"source": SOURCE_CLIENT, "value": property_doc.get("address")})
    if hb.get("adresa"):
        values.append({"source": SOURCE_HARTABLOCURI, "value": hb.get("adresa")})
    if (google or {}).get("formatted_address"):
        values.append({"source": SOURCE_GOOGLE, "value": google.get("formatted_address")})
    folded = {_norm(v["value"]) for v in values if v.get("value")}
    if len(folded) > 1:
        existing.append({
            "field": "address",
            "status": "unresolved",
            "values": values,
            "note": "Sursele diferă. Nicio valoare nu este suprascrisă.",
        })
    return existing


def serialize_google_observation(loc: Optional[dict]) -> Optional[dict]:
    if not loc:
        return None
    return {
        "source": SOURCE_GOOGLE,
        "verification_status": loc.get("verification_status") or STATUS_NEVERIFICAT,
        "stored": False,
        "fields": {
            k: loc.get(k)
            for k in ("lat", "lng", "formatted_address", "google_place_id",
                      "google_location_type", "query", "reason")
            if loc.get(k) is not None
        },
    }


def identity_profile(building: dict, *, property_doc: Optional[dict] = None) -> dict:
    """Authenticated owner view of a linked building. External facts stay unverified."""
    from location_resolver import resolve_property_map_location

    ctx = building.get("context") or {}
    ext = ctx.get("external_sources") or {}
    link = (property_doc or {}).get("building_link") or {}
    hb = hartablocuri_facts(building)
    google = ext.get(SOURCE_GOOGLE)
    prop_id = str((property_doc or {}).get("_id") or (property_doc or {}).get("id") or "") or None
    display = resolve_property_map_location(property_doc, building)
    return {
        "building_id": str(building.get("_id") or building.get("id") or ""),
        "canonical": {
            "name": building.get("name"),
            "address": building.get("address"),
            "city": building.get("city") or _building_city(building),
        },
        "external_identities": {
            SOURCE_HARTABLOCURI: {
                "source_record_id": (ext.get("hartablocuri") or {}).get("source_record_id"),
                "present": bool(ext.get("hartablocuri")),
            },
            SOURCE_GOOGLE: {
                "google_place_id": (google or {}).get("google_place_id"),
                "present": bool(google),
            },
        },
        "observations": {
            SOURCE_HARTABLOCURI: hb,
            SOURCE_GOOGLE: {
                "source": SOURCE_GOOGLE,
                "verification_status": (google or {}).get("verification_status"),
                "fields": {
                    k: (google or {}).get(k)
                    for k in ("formatted_address", "google_location_type", "lat", "lng")
                    if google and google.get(k) is not None
                },
            } if google else None,
            SOURCE_CLIENT: _sanitize_client_observations(
                (ext.get(SOURCE_CLIENT) or {}).get("observations") or [],
                property_id=prop_id,
            ),
            SOURCE_PROPMANAGE: {
                "source": SOURCE_PROPMANAGE,
                "address": building.get("address"),
                "name": building.get("name"),
            },
        },
        "relation": {
            "property_id": prop_id,
            "belongs_to": bool((property_doc or {}).get("building_id")),
            "confirmation_source": link.get("confirmation_source"),
            "confirmation_status": link.get("confirmation_status"),
            "confirmed_at": link.get("confirmed_at"),
            "not_confirmed": link.get("not_confirmed") or [
                "construction_year", "structure", "apartments", "typology",
                "height_regime", "lift",
            ],
        },
        "conflicts": _address_conflicts(building, property_doc, google),
        "display_location": display,
        "disclaimer": "Date externe HartaBlocuri — neverificate de PropManage" if hb else None,
    }


async def resolve_identity(buildings: list[dict], *,
                           address: str,
                           city: Optional[str] = None,
                           postal_code: Optional[str] = None,
                           stair: Optional[str] = None,
                           geocode_client: Any = None) -> dict:
    query = parse_query(address, city=city, postal_code=postal_code, stair=stair)
    google = await geocode_address(
        address, city=city, postal_code=postal_code, client=geocode_client,
    )
    candidates = []
    for b in buildings:
        hit = classify_building(query, b, google=google)
        if not hit:
            continue
        hit["hartablocuri"] = hartablocuri_facts(b)
        hit["prompt"] = {
            "title": "Am identificat o posibilă clădire asociată adresei dvs.",
            "disclaimer": (hit["hartablocuri"] or {}).get("disclaimer")
            or "Datele externe nu au fost verificate de PropManage.",
            "actions": ["confirm", "reject"],
        }
        candidates.append(hit)
    order = {STATUS_PROBABLE: 0, STATUS_CANDIDATE: 1}
    candidates.sort(key=lambda c: (
        order.get(c["status"], 9),
        0 if c.get("hartablocuri") else 1,
        c.get("distance_m") or 10**9,
    ))
    return {
        "query": query,
        "google": serialize_google_observation(google),
        "candidates": candidates,
        "auto_confirmed": False,
    }


def confirmation_payload(user: dict, property_id: str, building_id: str,
                         *, stair: Optional[str] = None,
                         apartment: Optional[str] = None,
                         resolver_status: Optional[str] = None,
                         matched_by: Optional[list] = None) -> dict:
    now = _now()
    link = {
        "confirmation_source": SOURCE_CLIENT,
        "confirmation_status": STATUS_DECLARED,
        "confirmed_at": now,
        "confirmed_by": user.get("id"),
        "resolver_status": resolver_status,  # probable/candidate = DETECTED match, not verified
        "matched_by": matched_by or [],  # resolver signals (Faza 7), not Claim Matching (Faza 9)
        "confirmed_fields": ["property_belongs_to_building"],
        "not_confirmed": [
            "construction_year", "structure", "apartments", "typology",
            "height_regime", "lift",
        ],
    }
    observation = {
        "source": SOURCE_CLIENT,
        "verification_status": STATUS_DECLARED,
        "created_at": now,
        "property_id": property_id,
        "relation": "belongs_to",
        "fields": {},
    }
    if stair:
        observation["fields"]["stair"] = str(stair)
        link["stair_declared"] = str(stair)
    if apartment:
        observation["fields"]["apartment"] = str(apartment)
        link["apartment_declared"] = str(apartment)
    return {"building_link": link, "observation": observation, "confirmed_at": now}
