"""Evidence Contract v1.0 FINAL — read-time semantic vocabulary (Faza 7B).

Mapping only. Not a DB enum. Not a store. Not a global trust state.

Does NOT persist: content_verified, identity_verified, detected_type,
reviewed_type, matched, reviewed.

Does NOT unify Vault / PTR / Google / HartaBlocuri / Digital Twin / DNA /
Knowledge Center under one operational enum — those domains keep their
own field values.

identity_verified is intentionally not exposed: Identity Gate does not exist yet.
"""
from __future__ import annotations

# Canonical mapping words (in-process only)
DECLARED = "declared"
PRESENT = "present"
OBSERVED = "observed"
DETECTED = "detected"
ROLE_VERIFIED = "role_verified"
PRIVILEGED_DECLARED = "privileged_declared"
EXTRACTED = "extracted"

WHO_CLIENT = "client"
WHO_SPECIALIST = "specialist"
WHO_PLATFORM = "platform"

_SOURCE_WHO = {
    "owner_upload": WHO_CLIENT,
    "specialist": WHO_SPECIALIST,
    "platform": WHO_PLATFORM,
}

_RESOLVER_DETECTED = {"probable", "candidate"}

# Resolver matched_by is Faza 7 detected signals, not Faza 9 Claim Matching.
MATCHED_BY_MEANING = "resolver_signals_not_claim_match"

# properties.address / name / city — semantic read, no new DB fields.
PROPERTY_IDENTITY_FIELDS_ARE = "client_declared_input"


def vault_who_provided(doc: dict) -> str:
    src = str((doc or {}).get("source") or "")
    return _SOURCE_WHO.get(src, src or "unknown")


def vault_trust_state(doc: dict) -> str:
    """DB verification_status=verified is LEGACY ROLE STATE, never content_verified."""
    status = str((doc or {}).get("verification_status") or "").lower()
    if status == "verified":
        return ROLE_VERIFIED
    return DECLARED


def vault_provenance_class(doc: dict) -> str:
    """DB provenance=documented is privileged/platform-declared, not content_verified."""
    provenance = str((doc or {}).get("provenance") or "").lower()
    if provenance == "documented":
        return PRIVILEGED_DECLARED
    return DECLARED


def vault_document_semantics(doc: dict) -> dict:
    """Read-model for Vault payloads. Does not write. Does not change scoring."""
    doc = doc or {}
    return {
        "who_provided": vault_who_provided(doc),
        "presence": PRESENT,
        "category_state": DECLARED,
        "trust_state": vault_trust_state(doc),
        "provenance_class": vault_provenance_class(doc),
        "content_verified": False,
    }


def identity_link_semantics(link: dict) -> dict:
    """building_link is a declared relation. resolver_status is a detected match."""
    link = link or {}
    status = str(link.get("confirmation_status") or "")
    resolver = str(link.get("resolver_status") or "")
    return {
        "confirmation_state": DECLARED if status == "declared" else (status or "absent"),
        "resolver_state": DETECTED if resolver in _RESOLVER_DETECTED else (resolver or None),
        "matched_by_meaning": MATCHED_BY_MEANING,
    }


def google_observation_semantics(loc: dict) -> dict:
    """Google is an address/location observation. Operational statuses stay operational."""
    loc = loc or {}
    return {
        "source_class": "google",
        "trust_state": OBSERVED,
        "operational_status": loc.get("verification_status"),
    }


def hartablocuri_observation_semantics(hb: dict) -> dict:
    """HartaBlocuri is an external observation, never official truth."""
    hb = hb or {}
    return {
        "source_class": "hartablocuri",
        "trust_state": OBSERVED,
        "verification_status": hb.get("verification_status") or "neverificat",
    }
