"""Faza 9C — isolated claim matching. No DB. No Building/Property writes."""
from __future__ import annotations

import ast
import inspect

import claim_matching as cm
from claim_matching import (
    AMBIGUOUS,
    BUILDING_APARTMENTS,
    BUILDING_CONSTRUCTION_YEAR,
    BUILDING_HEIGHT_REGIME,
    BUILDING_LIFT,
    BUILDING_STAIRS,
    BUILDING_STRUCTURE,
    CONFLICT,
    EXACT_MATCH,
    IDENTITY_CONFLICT,
    INTERNAL_CONFLICT,
    NORMALIZED_MATCH,
    NOT_COMPARABLE,
    NO_MATCH,
    PARTIAL_MATCH,
    PROPERTY_ADDRESS,
    PROPERTY_BUILDING_RELATION,
    PROPERTY_FLOOR,
    PROPERTY_STAIR,
    PROPERTY_SURFACE,
    PROPERTY_UNIT,
    SOURCE_CONFLICT,
    SRC_BUILDING_RECORD,
    SRC_GOOGLE,
    SRC_HB_PROMOTED,
    SRC_PROPERTY_RECORD,
    Claim,
    Evidence,
    detect_conflicts,
    is_self_match,
    match_claim_evidence,
    match_claims,
    materialize_building_claims,
    materialize_client_observations,
    materialize_document_evidence,
    materialize_google_evidence,
    materialize_hartablocuri_evidence,
    materialize_property_claims,
    materialize_relation_claims,
)
from evidence_semantics import DECLARED, EXTRACTED, OBSERVED

# Pilot IDs used only as fixture data — matcher must not special-case them.
G10 = "6aaadd4aaebd8dfb9c8aaf59"
EIGHT_D = "6a7724892e6529db42e95df1"
PTR = "6a9c6efff2ac8e128bd1d335"
PROP_AP25 = "6a367bbb23f65c42a043a0b5"


def _ev(**kw) -> Evidence:
    base = dict(
        source_type="document_extracted_fact",
        source_id="doc1",
        subject_type="document",
        subject_id="doc1",
        fact_type="address",
        raw_value="",
        normalized_value=None,
        trust_state=EXTRACTED,
        provenance=EXTRACTED,
    )
    base.update(kw)
    return Evidence(**base)


def _claim_addr(value, pid="p1"):
    return next(c for c in materialize_property_claims({"_id": pid, "address": value})
                if c.claim_type == PROPERTY_ADDRESS)


def test_exact_address_match():
    claim = _claim_addr("Aleea Negoiu nr. 8")
    ev = _ev(fact_type="address", raw_value="Aleea Negoiu nr. 8")
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}


def test_normalized_address_match():
    claim = _claim_addr("Aleea Negoiu nr. 8")
    ev = _ev(fact_type="address", raw_value="aleea negoiu nr 8")
    r = match_claim_evidence(claim, ev)
    assert r.result == NORMALIZED_MATCH


def test_eight_vs_8d_is_partial_not_conflict():
    claim = _claim_addr("Aleea Negoiu nr. 8")
    ev = _ev(fact_type="address", raw_value="Aleea Negoiu nr. 8D")
    r = match_claim_evidence(claim, ev)
    assert r.result == PARTIAL_MATCH
    assert r.result != CONFLICT
    assert "suffix" in (r.note or "")


def test_eight_vs_ten_is_conflict():
    claim = _claim_addr("Aleea Negoiu nr. 8")
    ev = _ev(fact_type="address", raw_value="Aleea Negoiu nr. 10")
    r = match_claim_evidence(claim, ev)
    assert r.result == CONFLICT


def test_surface_comma_normalized_match():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "surface": 54.2})
                 if c.claim_type == PROPERTY_SURFACE)
    ev = _ev(fact_type="surface_m2", raw_value="54,20", normalized_value=54.2)
    r = match_claim_evidence(claim, ev)
    assert r.result == NORMALIZED_MATCH
    assert r.claim_normalized == 54.2
    assert r.evidence_normalized == 54.2


def test_surface_54_vs_56_conflict():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "surface": 54})
                 if c.claim_type == PROPERTY_SURFACE)
    ev = _ev(fact_type="surface_m2", raw_value="56", normalized_value=56.0)
    r = match_claim_evidence(claim, ev)
    assert r.result == CONFLICT


def test_internal_conflict_keeps_both_surfaces():
    facts = [
        {"fact_type": "surface_m2", "value": "54", "normalized_value": 54.0, "source_document": "docX"},
        {"fact_type": "surface_m2", "value": "56", "normalized_value": 56.0, "source_document": "docX"},
    ]
    evs = materialize_document_evidence(facts, document_id="docX")
    assert len(evs) == 2
    conflicts = detect_conflicts([], evs, [])
    internals = [c for c in conflicts if c.conflict_type == INTERNAL_CONFLICT]
    assert internals
    assert set(internals[0].values) == {"54", "56"}


def test_source_conflict_hb_40_vs_ptr_13():
    claims = materialize_building_claims({"_id": "b-ptr", "context": {"number_of_units": 13}})
    hb = materialize_hartablocuri_evidence(
        {"raw": {"apartamente": 40}, "source_record_id": "hb-1"},
        building_id="b-hb",
    )
    out = match_claims(claims, hb)
    apt = next(c for c in claims if c.claim_type == BUILDING_APARTMENTS)
    hit = next(r for r in out["matches"] if r.claim_ref == apt.claim_id)
    assert hit.result == CONFLICT
    assert any(c.conflict_type == SOURCE_CONFLICT for c in out["conflicts"])


def test_stair_label_match():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "stair": "2"})
                 if c.claim_type == PROPERTY_STAIR)
    ev = _ev(fact_type="stair", raw_value="2", normalized_value="2")
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}


def test_hb_stairs_count_not_comparable_to_property_stair():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "stair": "2"})
                 if c.claim_type == PROPERTY_STAIR)
    hb = materialize_hartablocuri_evidence({"raw": {"scari": 2}}, building_id="b1")
    stairs_ev = next(e for e in hb if e.fact_type == "stairs")
    r = match_claim_evidence(claim, stairs_ev)
    assert r.result == NOT_COMPARABLE


def test_apartment_25_match():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "apartment": "25"})
                 if c.claim_type == PROPERTY_UNIT)
    ev = _ev(fact_type="apartment", raw_value="25")
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}


def test_apartment_25_vs_12_conflict():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "apartment": "25"})
                 if c.claim_type == PROPERTY_UNIT)
    ev = _ev(fact_type="apartment", raw_value="12")
    r = match_claim_evidence(claim, ev)
    assert r.result == CONFLICT


def test_floor_p_vs_parter():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "floor": "P"})
                 if c.claim_type == PROPERTY_FLOOR)
    ev = _ev(fact_type="floor", raw_value="parter")
    r = match_claim_evidence(claim, ev)
    assert r.result == NORMALIZED_MATCH
    assert r.claim_normalized == "parter"
    assert r.evidence_normalized == "parter"


def test_building_floors_not_comparable_to_property_floor():
    claim = next(c for c in materialize_property_claims({"_id": "p1", "floor": "3"})
                 if c.claim_type == PROPERTY_FLOOR)
    ev = _ev(fact_type="floors", raw_value=4, source_type=SRC_BUILDING_RECORD,
             source_id="other-b", subject_type="building", subject_id="other-b")
    r = match_claim_evidence(claim, ev)
    assert r.result == NOT_COMPARABLE


def test_missing_floor_does_not_invent_claim():
    claims = materialize_property_claims({"_id": "p1", "address": "Aleea Negoiu nr. 8"})
    assert all(c.claim_type != PROPERTY_FLOOR for c in claims)


def test_year_1972_match():
    claims = materialize_building_claims({"_id": "b1", "context": {"construction_year": 1972}})
    claim = next(c for c in claims if c.claim_type == BUILDING_CONSTRUCTION_YEAR)
    ev = _ev(fact_type="construction_year", raw_value="1972", normalized_value=1972)
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}


def test_year_1972_vs_1980_conflict():
    claims = materialize_building_claims({"_id": "b1", "context": {"construction_year": 1972}})
    claim = next(c for c in claims if c.claim_type == BUILDING_CONSTRUCTION_YEAR)
    ev = _ev(fact_type="construction_year", raw_value="1980", normalized_value=1980)
    r = match_claim_evidence(claim, ev)
    assert r.result == CONFLICT


def test_structure_compatible_same_token():
    claims = materialize_building_claims({"_id": "b1", "context": {"structure": "beton"}})
    claim = next(c for c in claims if c.claim_type == BUILDING_STRUCTURE)
    ev = _ev(fact_type="structure", raw_value="Beton", source_type=SRC_HB_PROMOTED,
             source_id="hb", subject_type="building", subject_id="b1")
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}


def test_structure_unknown_not_comparable():
    claims = materialize_building_claims({"_id": "b1", "context": {"structure": "necunoscut"}})
    claim = next(c for c in claims if c.claim_type == BUILDING_STRUCTURE)
    ev = _ev(fact_type="structure", raw_value="panouri")
    r = match_claim_evidence(claim, ev)
    assert r.result == NOT_COMPARABLE


def test_height_p4_match():
    claims = materialize_building_claims({"_id": "b1", "context": {"height_regime": "P+4"}})
    claim = next(c for c in claims if c.claim_type == BUILDING_HEIGHT_REGIME)
    ev = _ev(fact_type="height_regime", raw_value="P+4")
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}


def test_floors_numeric_vs_height_not_comparable():
    claims = materialize_building_claims({"_id": "b1", "context": {"height_regime": "P+4"}})
    claim = next(c for c in claims if c.claim_type == BUILDING_HEIGHT_REGIME)
    ev = _ev(fact_type="floors", raw_value=4)
    r = match_claim_evidence(claim, ev)
    assert r.result == NOT_COMPARABLE


def test_lift_true_match():
    claims = materialize_building_claims({"_id": "b1", "context": {"lift": "da"}})
    claim = next(c for c in claims if c.claim_type == BUILDING_LIFT)
    ev = _ev(fact_type="lift", raw_value="are lift")
    r = match_claim_evidence(claim, ev)
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}
    assert r.claim_normalized is True
    assert r.evidence_normalized is True


def test_lift_true_vs_false_conflict():
    claims = materialize_building_claims({"_id": "b1", "context": {"lift": True}})
    claim = next(c for c in claims if c.claim_type == BUILDING_LIFT)
    ev = _ev(fact_type="lift", raw_value="nu")
    r = match_claim_evidence(claim, ev)
    assert r.result == CONFLICT


def test_property_record_self_match_blocked():
    claims = materialize_property_claims({"_id": "p1", "surface": 54.2})
    claim = next(c for c in claims if c.claim_type == PROPERTY_SURFACE)
    ev = Evidence(
        source_type=SRC_PROPERTY_RECORD, source_id="p1",
        subject_type="property", subject_id="p1",
        fact_type="surface", raw_value=54.2, normalized_value=54.2,
        trust_state=DECLARED, provenance=DECLARED,
    )
    assert is_self_match(claim, ev) is True
    assert match_claim_evidence(claim, ev) is None
    out = match_claims(claims, [ev])
    assert out["matches"] == []


def test_extracted_fact_remains_subject_document():
    evs = materialize_document_evidence(
        [{"fact_type": "construction_year", "value": "1972", "normalized_value": 1972,
          "source_document": "docA", "scope_candidate": "building"}],
        document_id="docA",
    )
    assert evs[0].subject_type == "document"
    assert evs[0].subject_id == "docA"
    assert evs[0].trust_state == EXTRACTED


def test_scope_candidate_building_does_not_write():
    src = inspect.getsource(cm)
    assert "db.buildings" not in src
    assert "update_one" not in src
    assert "insert_one" not in src
    claims = materialize_building_claims({"_id": "b1", "context": {"construction_year": 1972}})
    evs = materialize_document_evidence(
        [{"fact_type": "construction_year", "value": "1972", "source_document": "docA",
          "scope_candidate": "building"}],
        document_id="docA",
    )
    r = match_claim_evidence(claims[0], evs[0])
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH}
    assert evs[0].subject_type == "document"


def test_google_cannot_create_year_evidence():
    evs = materialize_google_evidence({
        "formatted_address": "Aleea Negoiu 8, Cluj-Napoca",
        "construction_year": 1972,
        "fields": {"formatted_address": "Aleea Negoiu 8, Cluj-Napoca", "year": 1972},
    })
    assert evs
    assert all(e.fact_type == "address" for e in evs)
    assert not any(e.fact_type == "construction_year" for e in evs)


def test_google_address_remains_observed():
    evs = materialize_google_evidence({"formatted_address": "Aleea Negoiu nr. 8"})
    assert evs[0].source_type == SRC_GOOGLE
    assert evs[0].trust_state == OBSERVED
    claim = _claim_addr("Aleea Negoiu nr. 8")
    r = match_claim_evidence(claim, evs[0])
    assert r.result in {EXACT_MATCH, NORMALIZED_MATCH, PARTIAL_MATCH, AMBIGUOUS}
    assert evs[0].trust_state == OBSERVED
    assert not hasattr(r, "trust_state")


def test_ledger_is_not_accepted_as_evidence():
    ledger = {
        "collection": "hartablocuri_source_records",
        "link_status": "none",
        "excel_row": 12,
        "source_snapshot_id": "snap-1",
        "nume": "Bloc G10",
        "apartamente": 40,
    }
    assert materialize_hartablocuri_evidence(ledger) == []
    assert materialize_hartablocuri_evidence({
        "link_status": "none", "excel_row": 3, "raw": {"apartamente": 40},
    }) == []


def test_no_trust_state_on_match_result():
    claim = _claim_addr("Aleea Negoiu nr. 8")
    ev = _ev(fact_type="address", raw_value="Aleea Negoiu nr. 8")
    r = match_claim_evidence(claim, ev)
    assert "trust_state" not in r.__dataclass_fields__
    assert "winner" not in r.__dataclass_fields__
    assert "score" not in r.__dataclass_fields__


def test_no_verified_flags_in_module():
    src = inspect.getsource(cm)
    assert "content_verified" not in src
    assert "identity_verified" not in src
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "eval" not in names and "exec" not in names


def test_no_mutation_of_entity_snapshots():
    prop = {"_id": "p1", "address": "Aleea Negoiu nr. 8", "surface": 54, "building_id": "b-x"}
    building = {"_id": "b-x", "address": "Aleea Negoiu nr. 8", "context": {"construction_year": 1972}}
    prop_copy, b_copy = dict(prop), {"context": dict(building["context"]), **{k: v for k, v in building.items() if k != "context"}}
    materialize_property_claims(prop)
    materialize_building_claims(building)
    materialize_relation_claims(prop)
    match_claims(materialize_property_claims(prop), materialize_document_evidence(
        [{"fact_type": "surface_m2", "value": "54", "source_document": "d"}]
    ))
    assert prop == prop_copy
    assert building["context"] == b_copy["context"]
    assert prop["building_id"] == "b-x"


def test_pilot_ids_are_fixture_data_not_matcher_logic():
    src = inspect.getsource(cm)
    assert G10 not in src
    assert EIGHT_D not in src
    assert PTR not in src
    assert PROP_AP25 not in src
    prop = {"_id": PROP_AP25, "address": "Aleea Negoiu nr 8 D", "building_id": EIGHT_D}
    rel = materialize_relation_claims(prop)
    assert rel[0].claimed_value == EIGHT_D
    support_x = _ev(fact_type="building_ref", raw_value=EIGHT_D, normalized_value=EIGHT_D,
                    source_type="client_declaration", source_id=PROP_AP25)
    other = _ev(fact_type="building_ref", raw_value=G10, normalized_value=G10,
                source_type=SRC_HB_PROMOTED, source_id="hb-g10",
                subject_type="building", subject_id=G10)
    assert match_claim_evidence(rel[0], support_x).result == EXACT_MATCH
    assert match_claim_evidence(rel[0], other).result == CONFLICT
    out = match_claims(rel, [other])
    assert any(c.conflict_type == IDENTITY_CONFLICT for c in out["conflicts"])
    ptr_claim = materialize_relation_claims({"_id": PROP_AP25, "building_id": PTR})
    assert match_claim_evidence(ptr_claim[0], support_x).result == CONFLICT


def test_v1_v2_results_are_independent():
    claim = next(c for c in materialize_building_claims(
        {"_id": "b1", "context": {"construction_year": 1972}}
    ) if c.claim_type == BUILDING_CONSTRUCTION_YEAR)
    v1 = materialize_document_evidence(
        [{"fact_type": "construction_year", "value": "1972", "source_document": "V1"}],
        document_id="V1",
    )
    v2 = materialize_document_evidence(
        [{"fact_type": "construction_year", "value": "1980", "source_document": "V2"}],
        document_id="V2",
    )
    r1 = match_claims([claim], v1)
    r2 = match_claims([claim], v2)
    assert r1["matches"][0].result in {EXACT_MATCH, NORMALIZED_MATCH}
    assert r2["matches"][0].result == CONFLICT
    assert all("V2" not in m.evidence_ref for m in r1["matches"])
    assert all("V1" not in m.evidence_ref for m in r2["matches"])
    r1_again = match_claims([claim], v1)
    assert r1_again["matches"][0].result == r1["matches"][0].result


def test_client_observations_declared_only():
    evs = materialize_client_observations([
        {"property_id": "p1", "fields": {"stair": "2", "apartment": "25"}},
    ])
    assert {e.fact_type for e in evs} == {"stair", "apartment"}
    assert all(e.trust_state == DECLARED for e in evs)


def test_missing_house_is_ambiguous_or_partial():
    claim = _claim_addr("Aleea Negoiu")
    ev = _ev(fact_type="address", raw_value="Aleea Negoiu")
    r = match_claim_evidence(claim, ev)
    assert r.result in {AMBIGUOUS, PARTIAL_MATCH, NO_MATCH}


def test_import_graph_has_no_db_routes_ledger_llm():
    src = inspect.getsource(cm)
    assert "from db" not in src
    assert "import db" not in src
    assert "hartablocuri_source_ledger" not in src
    assert "fastapi" not in src.lower()
    assert "call_llm" not in src
    assert "ai_docs" not in src
    assert "document_fact_extraction" not in src
    assert "tenancy" not in src
