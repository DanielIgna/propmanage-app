"""Faza 10C — DOCUMENT_PROPERTY_SUPPORT orchestrator.

Pure functions over 9C MatchResult. No DB, routes, persistence, LLM, or UI.
Rollup is descriptive support, not verification or identity_verified.
"""
from __future__ import annotations

from typing import Any, Optional

from building_identity import detect_unit_granularity
from claim_matching import (
    CONFLICT,
    EXACT_MATCH,
    NORMALIZED_MATCH,
    NOT_COMPARABLE,
    PARTIAL_MATCH,
    PROPERTY_ADDRESS,
    PROPERTY_FLOOR,
    PROPERTY_STAIR,
    PROPERTY_SURFACE,
    PROPERTY_UNIT,
    match_claims,
    materialize_document_evidence,
    materialize_property_claims,
)

# ── Rollup vocabulary (10B) ────────────────────────────────────────────────

INSUFFICIENT = "INSUFFICIENT"
SUPPORTING = "SUPPORTING"
AMBIGUOUS = "AMBIGUOUS"
CONFLICTING = "CONFLICTING"

REASON_PROPERTY_ID_MISMATCH = "property_id_mismatch"

_IDENTITY_CLAIMS = frozenset({PROPERTY_ADDRESS, PROPERTY_UNIT})
_SUPPORTING_CLAIMS = frozenset({PROPERTY_SURFACE, PROPERTY_STAIR, PROPERTY_FLOOR})

_IDENTITY_FACT_TYPES = frozenset({"address", "street", "house_number", "apartment"})
_SUPPORTING_FACT_TYPES = frozenset({
    "surface_m2", "surface", "rooms", "stair", "floor",
})
_DOCUMENT_ONLY_FACT_TYPES = frozenset({
    "deed_number", "certificate_number", "issue_date", "energy_class",
})
_LEGAL_ONLY_FACT_TYPES = frozenset({"cf_number"})
_BUILDING_ONLY_FACT_TYPES = frozenset({"construction_year"})
_METADATA_FACT_TYPES = frozenset({"category", "filename", "title"})

_EXCLUDED_FROM_EVIDENCE = _BUILDING_ONLY_FACT_TYPES
_GRANULAR_TYPES = frozenset({"apartment", "unit"})
_UNIT_MATCHES = frozenset({EXACT_MATCH, NORMALIZED_MATCH})
_ADDRESS_MATCHES = frozenset({EXACT_MATCH, NORMALIZED_MATCH})


def _entity_id(snap: Optional[dict]) -> str:
    if not snap:
        return ""
    return str(snap.get("_id") or snap.get("id") or snap.get("property_id") or "")


def _document_id(snap: Optional[dict]) -> str:
    if not snap:
        return ""
    return str(snap.get("_id") or snap.get("id") or snap.get("document_id") or "")


def _document_version(snap: Optional[dict]) -> Any:
    if not snap:
        return ""
    if "version" in snap and snap.get("version") is not None:
        return snap.get("version")
    if snap.get("document_version") is not None:
        return snap.get("document_version")
    return ""


def _doc_property_id(snap: Optional[dict]) -> str:
    if not snap:
        return ""
    return str(snap.get("property_id") or "")


def _truthy_flag(snap: Optional[dict], key: str) -> bool:
    return bool(snap and snap.get(key) is True)


def _ineligible(reason: str, *, document_id: str = "", property_id: str = "") -> dict:
    out = {"eligible": False, "reason": reason}
    if document_id:
        out["document_id"] = document_id
    if property_id:
        out["property_id"] = property_id
    return out


def _acl_eligible(property_snapshot: dict, document_snapshot: dict) -> bool:
    prop_id = _entity_id(property_snapshot)
    doc_prop = _doc_property_id(document_snapshot)
    return bool(prop_id) and bool(doc_prop) and prop_id == doc_prop


def _fact_type(fact: dict) -> str:
    return str(fact.get("fact_type") or "")


def _fact_has_value(fact: Any) -> bool:
    if not isinstance(fact, dict):
        return False
    return fact.get("value") is not None


def _extracted_facts(document_snapshot: dict) -> list:
    facts = (document_snapshot or {}).get("extracted_facts") or []
    return [f for f in facts if _fact_has_value(f)]


def _facts_for_evidence(facts: list) -> list:
    return [f for f in facts if _fact_type(f) not in _EXCLUDED_FROM_EVIDENCE]


def _fact_types(facts: list) -> set[str]:
    return {_fact_type(f) for f in facts}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _claim_map(claims) -> dict:
    return {c.claim_id: c for c in claims}


def _match_claim_type(match, claims_by_id: dict) -> str:
    claim = claims_by_id.get(match.claim_ref)
    return claim.claim_type if claim else ""


def is_suffix_compatible_partial(match) -> bool:
    """10B: PARTIAL_MATCH is address-compatible only for house suffix (8 ↔ 8D)."""
    if match.result != PARTIAL_MATCH:
        return False
    if match.compared_field not in {"address", "house_number"}:
        return False
    note = (match.note or "").lower()
    return "suffix" in note


def is_address_compatible(match) -> bool:
    """Identity address compatibility from a 9C PROPERTY_ADDRESS MatchResult."""
    if match.result in _ADDRESS_MATCHES:
        return True
    return is_suffix_compatible_partial(match)


def _address_matches(matches, claims_by_id: dict) -> list:
    return [m for m in matches if _match_claim_type(m, claims_by_id) == PROPERTY_ADDRESS]


def _unit_matches(matches, claims_by_id: dict) -> list:
    return [m for m in matches if _match_claim_type(m, claims_by_id) == PROPERTY_UNIT]


def _has_claim(claims, claim_type: str) -> bool:
    return any(c.claim_type == claim_type for c in claims)


def property_is_granular(property_snapshot: dict, claims) -> bool:
    """Unit granularity from existing 9C claims / type / detect_unit_granularity only."""
    if _has_claim(claims, PROPERTY_UNIT):
        return True
    if _has_claim(claims, PROPERTY_STAIR):
        return True
    ptype = str((property_snapshot or {}).get("type") or "").strip().lower()
    if ptype in _GRANULAR_TYPES:
        return True
    gran = detect_unit_granularity(
        (property_snapshot or {}).get("name"),
        (property_snapshot or {}).get("address"),
    )
    return bool(gran.get("is_granular"))


def _unit_resolution(property_snapshot: dict, claims, matches, claims_by_id: dict) -> str:
    """Return MATCH | CONFLICT | AMBIGUOUS | NOT_REQUIRED."""
    unit_hits = _unit_matches(matches, claims_by_id)
    if _has_claim(claims, PROPERTY_UNIT):
        if any(m.result == CONFLICT for m in unit_hits):
            return "CONFLICT"
        if any(m.result in _UNIT_MATCHES for m in unit_hits):
            return "MATCH"
        return "AMBIGUOUS"
    if property_is_granular(property_snapshot, claims):
        return "AMBIGUOUS"
    return "NOT_REQUIRED"


def _serialize_identity_match(match, claim_type: str) -> dict:
    return {
        "claim_type": claim_type,
        "result": match.result,
        "compared_field": match.compared_field,
        "note": match.note or "",
        "claim_normalized": _jsonable(match.claim_normalized),
        "evidence_normalized": _jsonable(match.evidence_normalized),
    }


def _identity_match_payloads(matches, claims_by_id: dict) -> list[dict]:
    out = []
    for match in matches:
        ctype = _match_claim_type(match, claims_by_id)
        if ctype not in _IDENTITY_CLAIMS:
            continue
        if match.result == NOT_COMPARABLE:
            continue
        out.append(_serialize_identity_match(match, ctype))
    out.sort(key=lambda r: (r["claim_type"], r["compared_field"], r["result"], r["note"]))
    return out


def _identity_conflicts(matches, claims_by_id: dict) -> list[dict]:
    out = []
    for match in matches:
        ctype = _match_claim_type(match, claims_by_id)
        if ctype not in _IDENTITY_CLAIMS:
            continue
        if match.result != CONFLICT:
            continue
        payload = _serialize_identity_match(match, ctype)
        payload["role"] = "unresolved_identity_conflict"
        out.append(payload)
    out.sort(key=lambda r: (r["claim_type"], r["compared_field"], r["note"]))
    return out


def _supporting_notes(facts: list, matches, claims_by_id: dict) -> list[dict]:
    notes = []
    seen = set()
    for match in matches:
        ctype = _match_claim_type(match, claims_by_id)
        if ctype not in _SUPPORTING_CLAIMS:
            continue
        if match.result == NOT_COMPARABLE:
            continue
        key = (ctype, match.result, match.compared_field)
        if key in seen:
            continue
        seen.add(key)
        notes.append({
            "claim_type": ctype,
            "result": match.result,
            "compared_field": match.compared_field,
            "role": "supporting_fact",
        })
    for fact in facts:
        ft = _fact_type(fact)
        if ft == "rooms":
            key = ("rooms", "secondary_fact")
            if key in seen:
                continue
            seen.add(key)
            notes.append({
                "fact_type": "rooms",
                "role": "secondary_fact",
            })
    notes.sort(key=lambda r: (
        r.get("claim_type") or r.get("fact_type") or "",
        r.get("result") or "",
        r.get("role") or "",
    ))
    return notes


def _has_identity_core_conflict(matches, claims_by_id: dict) -> bool:
    for match in matches:
        ctype = _match_claim_type(match, claims_by_id)
        if ctype in _IDENTITY_CLAIMS and match.result == CONFLICT:
            return True
    return False


def _has_address_compatibility(matches, claims_by_id: dict) -> bool:
    return any(is_address_compatible(m) for m in _address_matches(matches, claims_by_id))


def _has_identity_relevant_facts(facts: list) -> bool:
    types = _fact_types(facts)
    return bool(types & _IDENTITY_FACT_TYPES)


def _comparable_fact_types(facts: list) -> set[str]:
    return _fact_types(facts) - _EXCLUDED_FROM_EVIDENCE - _DOCUMENT_ONLY_FACT_TYPES - _LEGAL_ONLY_FACT_TYPES - _METADATA_FACT_TYPES


def _decide_support(
    *,
    facts: list,
    matches,
    claims_by_id: dict,
    address_ok: bool,
    unit_state: str,
    identity_conflict: bool,
) -> str:
    if identity_conflict:
        return CONFLICTING
    if address_ok and unit_state == "MATCH":
        return SUPPORTING
    if address_ok and unit_state == "NOT_REQUIRED":
        return SUPPORTING
    if address_ok and unit_state == "AMBIGUOUS":
        return AMBIGUOUS
    if _has_identity_relevant_facts(facts):
        return AMBIGUOUS
    return INSUFFICIENT


def _empty_support_payload(
    property_snapshot: dict,
    document_snapshot: dict,
    support: str,
) -> dict:
    return {
        "eligible": True,
        "document_id": _document_id(document_snapshot),
        "document_version": _document_version(document_snapshot),
        "property_id": _entity_id(property_snapshot),
        "support": support,
        "identity_matches": [],
        "supporting_notes": [],
        "unresolved_identity_conflicts": [],
    }


def rollup_document_property_support(
    property_snapshot: dict,
    document_snapshot: dict,
) -> dict:
    """Pure DOCUMENT_PROPERTY_SUPPORT for one document version snapshot."""
    prop = property_snapshot or {}
    doc = document_snapshot or {}
    if not _acl_eligible(prop, doc):
        return _ineligible(
            REASON_PROPERTY_ID_MISMATCH,
            document_id=_document_id(doc),
            property_id=_entity_id(prop),
        )

    facts = _extracted_facts(doc)
    if not _comparable_fact_types(facts):
        payload = _empty_support_payload(prop, doc, INSUFFICIENT)
        if facts:
            payload["supporting_notes"] = _supporting_notes(facts, [], {})
        return payload

    claims = materialize_property_claims(prop)
    evidence = materialize_document_evidence(
        _facts_for_evidence(facts),
        document_id=_document_id(doc),
    )
    matched = match_claims(claims, evidence)
    matches = list(matched.get("matches") or [])
    claims_by_id = _claim_map(claims)

    identity_conflict = _has_identity_core_conflict(matches, claims_by_id)
    address_ok = _has_address_compatibility(matches, claims_by_id)
    unit_state = _unit_resolution(prop, claims, matches, claims_by_id)
    support = _decide_support(
        facts=facts,
        matches=matches,
        claims_by_id=claims_by_id,
        address_ok=address_ok,
        unit_state=unit_state,
        identity_conflict=identity_conflict,
    )

    return {
        "eligible": True,
        "document_id": _document_id(doc),
        "document_version": _document_version(doc),
        "property_id": _entity_id(prop),
        "support": support,
        "identity_matches": _identity_match_payloads(matches, claims_by_id),
        "supporting_notes": _supporting_notes(facts, matches, claims_by_id),
        "unresolved_identity_conflicts": _identity_conflicts(matches, claims_by_id),
    }


def _overall_support(supports: list[str]) -> str:
    if any(s == CONFLICTING for s in supports):
        return CONFLICTING
    if any(s == SUPPORTING for s in supports):
        return SUPPORTING
    if any(s == AMBIGUOUS for s in supports):
        return AMBIGUOUS
    return INSUFFICIENT


def rollup_property_document_support(
    property_snapshot: dict,
    document_snapshots: list,
) -> dict:
    """Pure property-level aggregation. No winner. Superseded versions stay out of overall."""
    docs = []
    overall_supports = []
    unresolved = []
    for raw in document_snapshots or []:
        snap = raw or {}
        if _truthy_flag(snap, "deleted"):
            continue
        result = rollup_document_property_support(property_snapshot, snap)
        current = not _truthy_flag(snap, "superseded")
        entry = dict(result)
        entry["included_in_overall"] = bool(result.get("eligible")) and current
        docs.append(entry)
        if entry["included_in_overall"]:
            overall_supports.append(result.get("support") or INSUFFICIENT)
            for conflict in result.get("unresolved_identity_conflicts") or []:
                item = dict(conflict)
                item["document_id"] = result.get("document_id")
                unresolved.append(item)

    unresolved.sort(key=lambda r: (
        r.get("document_id") or "",
        r.get("claim_type") or "",
        r.get("compared_field") or "",
        r.get("note") or "",
    ))
    return {
        "eligible": True,
        "property_id": _entity_id(property_snapshot),
        "support": _overall_support(overall_supports),
        "documents": docs,
        "unresolved_identity_conflicts": unresolved,
    }
