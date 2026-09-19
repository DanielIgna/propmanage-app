"""Faza 7B — Evidence Contract alignment. Isolated. No Building / HB / identity writes."""
from __future__ import annotations

import inspect

import evidence_semantics as sem
from evidence_semantics import (
    DECLARED,
    DETECTED,
    OBSERVED,
    PRESENT,
    PRIVILEGED_DECLARED,
    PROPERTY_IDENTITY_FIELDS_ARE,
    ROLE_VERIFIED,
    google_observation_semantics,
    hartablocuri_observation_semantics,
    identity_link_semantics,
    vault_document_semantics,
)
from routes.property_documents import document_contributes_to_completeness


G10 = "6aaadd4aaebd8dfb9c8aaf59"
NEGOIU_8D = "6a7724892e6529db42e95df1"
PTR = "6a9c6efff2ac8e128bd1d335"


def test_module_is_mapping_only_no_db():
    src = inspect.getsource(sem)
    assert "from db import" not in src
    assert "insert_one" not in src
    assert "content_verified" not in src or "False" in src
    assert "identity_verified" not in inspect.getsource(sem.vault_document_semantics)


def test_client_upload_present_declared_not_content_verified():
    doc = {
        "source": "owner_upload",
        "declared_category": "cadastru",
        "category": "cadastru",
        "verification_status": "unverified",
        "provenance": "declared",
    }
    c = vault_document_semantics(doc)
    assert c["presence"] == PRESENT
    assert c["category_state"] == DECLARED
    assert c["who_provided"] == "client"
    assert c["trust_state"] == DECLARED
    assert c["provenance_class"] == DECLARED
    assert c["content_verified"] is False
    assert document_contributes_to_completeness(doc) is False


def test_admin_verified_is_role_verified_not_content_verified():
    doc = {
        "source": "platform",
        "category": "cadastru",
        "verification_status": "verified",
        "provenance": "documented",
    }
    c = vault_document_semantics(doc)
    assert c["trust_state"] == ROLE_VERIFIED
    assert c["who_provided"] == "platform"
    assert c["provenance_class"] == PRIVILEGED_DECLARED
    assert c["content_verified"] is False
    assert document_contributes_to_completeness(doc) is True
    assert "identity_verified" not in c


def test_documented_contributes_but_is_not_content_verified():
    doc = {
        "source": "specialist",
        "category": "act_proprietate",
        "verification_status": "unverified",
        "provenance": "documented",
    }
    c = vault_document_semantics(doc)
    assert c["trust_state"] == DECLARED
    assert c["provenance_class"] == PRIVILEGED_DECLARED
    assert c["content_verified"] is False
    assert document_contributes_to_completeness(doc) is True


def test_identity_link_declared_not_identity_verified():
    link = {
        "confirmation_status": "declared",
        "resolver_status": "probable",
        "matched_by": ["street", "house_number"],
    }
    s = identity_link_semantics(link)
    assert s["confirmation_state"] == DECLARED
    assert s["resolver_state"] == DETECTED
    assert s["matched_by_meaning"] == "resolver_signals_not_claim_match"
    assert "identity_verified" not in s


def test_resolver_candidate_is_detected_not_verified():
    s = identity_link_semantics({"confirmation_status": "declared", "resolver_status": "candidate"})
    assert s["resolver_state"] == DETECTED


def test_google_is_observed():
    g = google_observation_semantics({"verification_status": "neverificat", "formatted_address": "x"})
    assert g["trust_state"] == OBSERVED
    assert g["source_class"] == "google"
    assert g["operational_status"] == "neverificat"


def test_hartablocuri_is_observed_neverificat():
    h = hartablocuri_observation_semantics({"verification_status": "neverificat"})
    assert h["trust_state"] == OBSERVED
    assert h["source_class"] == "hartablocuri"
    assert h["verification_status"] == "neverificat"


def test_property_address_is_semantic_declared_not_a_new_field():
    assert PROPERTY_IDENTITY_FIELDS_ARE == "client_declared_input"


def test_pilot_building_ids_unchanged_constants():
    """7B does not write Buildings. IDs remain the canonical pilot set."""
    assert G10 != NEGOIU_8D != PTR
    assert len(G10) == len(NEGOIU_8D) == len(PTR) == 24


def test_vault_out_exposes_contract_and_keeps_legacy_fields():
    from bson import ObjectId
    from routes.property_documents import _out

    out = _out({
        "_id": ObjectId("aaaaaaaaaaaaaaaaaaaaaaaa"),
        "source": "platform",
        "category": "cadastru",
        "declared_category": "cadastru",
        "verification_status": "verified",
        "provenance": "documented",
        "history": [],
    })
    assert out["verification_status"] == "verified"
    assert out["provenance"] == "documented"
    assert out["source"] == "platform"
    assert out["contract"]["trust_state"] == ROLE_VERIFIED
    assert out["contract"]["who_provided"] == "platform"
    assert out["contract"]["content_verified"] is False
    assert "identity_verified" not in out
    assert "identity_verified" not in out["contract"]
