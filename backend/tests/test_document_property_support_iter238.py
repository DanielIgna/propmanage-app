"""Faza 10C — isolated DOCUMENT_PROPERTY_SUPPORT. No DB. No Building/Property writes."""
from __future__ import annotations

import ast
import copy
import inspect
import json

import claim_matching as cm
import document_property_support as dps
from document_property_support import (
    AMBIGUOUS,
    CONFLICTING,
    INSUFFICIENT,
    REASON_PROPERTY_ID_MISMATCH,
    SUPPORTING,
    is_address_compatible,
    rollup_document_property_support,
    rollup_property_document_support,
)

# Pilot IDs used only as fixture data — orchestrator must not special-case them.
G10 = "6aaadd4aaebd8dfb9c8aaf59"
EIGHT_D = "6a7724892e6529db42e95df1"
PTR = "6a9c6efff2ac8e128bd1d335"
PROP_AP25 = "6a367bbb23f65c42a043a0b5"

PROP_ID = "prop-negoiu-1"
DOC_A = "doc-a"
DOC_C = "doc-c"


def _prop(**kw) -> dict:
    base = {
        "_id": PROP_ID,
        "address": "Aleea Negoiu nr. 8",
        "type": "house",
        "surface": 54.2,
        "rooms": 3,
        "building_id": EIGHT_D,
        "building_link": {"status": "declared", "apartment_declared": None},
    }
    base.update(kw)
    return base


def _apt_prop(**kw) -> dict:
    base = _prop(type="apartment", apartment="25", name="Ap. 25 Aleea Negoiu")
    base.update(kw)
    return base


def _fact(fact_type: str, value, **extra) -> dict:
    row = {"fact_type": fact_type, "value": value, "subject": "document"}
    row.update(extra)
    return row


def _doc(doc_id=DOC_A, version=1, facts=None, **kw) -> dict:
    base = {
        "_id": doc_id,
        "property_id": PROP_ID,
        "version": version,
        "extracted_facts": list(facts or []),
        "deleted": False,
        "superseded": False,
        "category": kw.pop("category", "cadastru"),
    }
    base.update(kw)
    return base


def _roll(prop, doc):
    return rollup_document_property_support(prop, doc)


def _dump(payload) -> str:
    return json.dumps(payload, ensure_ascii=True, default=str)


# ── 1. property_id alone ───────────────────────────────────────────────────

def test_01_property_id_alone_is_not_supporting():
    out = _roll(_prop(), _doc(facts=[]))
    assert out["eligible"] is True
    assert out["support"] == INSUFFICIENT
    assert out["support"] != SUPPORTING


# ── 2. address exact / unit rule ───────────────────────────────────────────

def test_02_address_exact_house_is_supporting():
    out = _roll(_prop(), _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")]))
    assert out["support"] == SUPPORTING


def test_02b_address_exact_with_unit_claim_without_apartment_is_ambiguous():
    out = _roll(
        _apt_prop(),
        _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")]),
    )
    assert out["support"] == AMBIGUOUS


# ── 3. normalized address ──────────────────────────────────────────────────

def test_03_normalized_address_is_compatible():
    out = _roll(_prop(), _doc(facts=[_fact("address", "aleea negoiu nr 8")]))
    assert out["support"] == SUPPORTING
    assert any(m["result"] == "NORMALIZED_MATCH" for m in out["identity_matches"])


# ── 4. 8 vs 10 ─────────────────────────────────────────────────────────────

def test_04_eight_vs_ten_is_conflicting():
    out = _roll(_prop(), _doc(facts=[_fact("address", "Aleea Negoiu nr. 10")]))
    assert out["support"] == CONFLICTING
    assert out["unresolved_identity_conflicts"]


# ── 5 / 15. apartment match + address ──────────────────────────────────────

def test_05_apartment_match_with_address_is_supporting():
    out = _roll(
        _apt_prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("apartment", "25"),
        ]),
    )
    assert out["support"] == SUPPORTING


# ── 6 / 16. apartment conflict ─────────────────────────────────────────────

def test_06_apartment_conflict_is_conflicting():
    out = _roll(
        _apt_prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("apartment", "12"),
        ]),
    )
    assert out["support"] == CONFLICTING


# ── 7. surface match with identity core ────────────────────────────────────

def test_07_surface_match_with_identity_core_is_supporting():
    out = _roll(
        _prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("surface_m2", "54,20"),
        ]),
    )
    assert out["support"] == SUPPORTING
    assert any(n.get("claim_type") == "PROPERTY_SURFACE" for n in out["supporting_notes"])


# ── 8. surface conflict is not identity CONFLICTING ────────────────────────

def test_08_surface_conflict_is_not_conflicting():
    out = _roll(
        _prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("surface_m2", "80"),
        ]),
    )
    assert out["support"] == SUPPORTING
    assert out["support"] != CONFLICTING


# ── 9. rooms do not change identity rollup ─────────────────────────────────

def test_09_rooms_do_not_change_identity_rollup():
    without = _roll(_prop(), _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")]))
    with_rooms = _roll(
        _prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("rooms", "2"),
        ]),
    )
    assert without["support"] == SUPPORTING
    assert with_rooms["support"] == SUPPORTING
    assert any(n.get("fact_type") == "rooms" for n in with_rooms["supporting_notes"])


def test_09b_rooms_alone_are_insufficient():
    out = _roll(_prop(), _doc(facts=[_fact("rooms", "3")]))
    assert out["support"] == INSUFFICIENT


# ── 10. CF without Property claim ──────────────────────────────────────────

def test_10_cf_alone_is_insufficient():
    out = _roll(_prop(), _doc(facts=[_fact("cf_number", "12345")]))
    assert out["support"] == INSUFFICIENT
    blob = _dump(out)
    assert "12345" not in blob


# ── 11. category only ──────────────────────────────────────────────────────

def test_11_category_only_is_insufficient():
    out = _roll(_prop(), _doc(facts=[], category="cadastru"))
    assert out["support"] == INSUFFICIENT


# ── 12. filename only ──────────────────────────────────────────────────────

def test_12_filename_only_is_insufficient():
    out = _roll(_prop(), _doc(facts=[], category=None, filename="act.pdf"))
    assert out["support"] == INSUFFICIENT


# ── 13. construction_year excluded ─────────────────────────────────────────

def test_13_construction_year_is_excluded():
    out = _roll(_prop(), _doc(facts=[_fact("construction_year", "1972")]))
    assert out["support"] == INSUFFICIENT
    blob = _dump(out).lower()
    assert "1972" not in blob
    assert "building" not in blob
    assert "PROPERTY_BUILDING_RELATION" not in _dump(out)


# ── 14 / 29. address without unit on multi-unit ────────────────────────────

def test_14_address_without_unit_on_multi_unit_is_ambiguous():
    out = _roll(
        _apt_prop(),
        _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")]),
    )
    assert out["support"] == AMBIGUOUS


def test_14b_granular_type_without_materialized_unit_is_ambiguous():
    prop = _prop(type="apartment")
    prop.pop("apartment", None)
    prop["name"] = "Unitate Aleea Negoiu"
    out = _roll(prop, _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")]))
    assert out["support"] == AMBIGUOUS


# ── 17. multi-document A SUPPORTING + C CONFLICTING ────────────────────────

def test_17_overall_conflicting_keeps_supporting_document():
    docs = [
        _doc(DOC_A, 1, [_fact("address", "Aleea Negoiu nr. 8")]),
        _doc(DOC_C, 1, [_fact("address", "Aleea Negoiu nr. 10")]),
    ]
    out = rollup_property_document_support(_prop(), docs)
    assert out["support"] == CONFLICTING
    by_id = {d["document_id"]: d for d in out["documents"]}
    assert by_id[DOC_A]["support"] == SUPPORTING
    assert by_id[DOC_C]["support"] == CONFLICTING
    assert "winner" not in out
    assert "best_match" not in out


# ── 18. V1 / V2 independent ────────────────────────────────────────────────

def test_18_v1_v2_are_independent():
    v1 = _roll(_prop(), _doc("doc-v", 1, [_fact("address", "Aleea Negoiu nr. 8")]))
    v2 = _roll(_prop(), _doc("doc-v", 2, [_fact("address", "Aleea Negoiu nr. 10")]))
    assert v1["support"] == SUPPORTING
    assert v2["support"] == CONFLICTING
    assert v1["document_version"] == 1
    assert v2["document_version"] == 2
    assert v1["support"] != v2["support"]


# ── 19. ACL mismatch ───────────────────────────────────────────────────────

def test_19_acl_property_id_mismatch_omits_evidence():
    other = _prop(_id="other-prop")
    doc = _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")])
    out = _roll(other, doc)
    assert out["eligible"] is False
    assert out["reason"] == REASON_PROPERTY_ID_MISMATCH
    assert "support" not in out
    assert "identity_matches" not in out
    assert "NO_MATCH" not in _dump(out)
    assert "NOT_COMPARABLE" not in _dump(out)
    assert "CONFLICT" not in _dump(out)


# ── 20–24. no mutations / no verified / pilots untouched ───────────────────

def test_20_21_no_building_or_building_id_mutation():
    prop = _apt_prop()
    before = copy.deepcopy(prop)
    _roll(prop, _doc(facts=[
        _fact("address", "Aleea Negoiu nr. 8"),
        _fact("apartment", "25"),
        _fact("construction_year", "1972"),
    ]))
    assert prop == before
    assert prop["building_id"] == EIGHT_D
    assert prop["building_link"] == before["building_link"]


def test_22_23_no_identity_or_content_verified():
    out = _roll(
        _apt_prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("apartment", "25"),
        ]),
    )
    blob = _dump(out)
    assert "identity_verified" not in blob
    assert "content_verified" not in blob
    assert "verified" not in blob
    tree = ast.parse(inspect.getsource(dps))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "identity_verified" not in names
    assert "content_verified" not in names


def test_24_g10_8d_ptr_untouched_and_not_special_cased():
    src = inspect.getsource(dps)
    assert G10 not in src
    assert EIGHT_D not in src
    assert PTR not in src
    assert PROP_AP25 not in src
    building = {"_id": G10, "address": "Gheorgheni 10", "building_id": G10}
    before = copy.deepcopy(building)
    prop = _prop(building_id=EIGHT_D)
    _roll(prop, _doc(facts=[_fact("address", "Aleea Negoiu nr. 8")]))
    assert building == before


# ── 25. no PII / raw PDF ───────────────────────────────────────────────────

def test_25_no_pii_or_raw_pdf_in_output():
    doc = _doc(facts=[_fact("address", "Aleea Negoiu nr. 8"), _fact("cf_number", "CF-SECRET-99")])
    doc.update({
        "pdf_bytes": b"%PDF-1.4 secret",
        "raw_text": "CNP 1234567890123 titular ION POPESCU",
        "text": "full document text",
        "owner_name": "Ion Popescu",
        "cnp": "1234567890123",
        "deed_number": "DEED-777",
    })
    out = _roll(_prop(), doc)
    blob = _dump(out)
    assert "pdf_bytes" not in blob
    assert "%PDF" not in blob
    assert "1234567890123" not in blob
    assert "Ion Popescu" not in blob
    assert "ION POPESCU" not in blob
    assert "CF-SECRET-99" not in blob
    assert "DEED-777" not in blob
    assert "full document text" not in blob


# ── 26. street-only PARTIAL ────────────────────────────────────────────────

def test_26_street_only_partial_is_not_supporting():
    out = _roll(_prop(), _doc(facts=[_fact("street", "Aleea Negoiu")]))
    assert out["support"] != SUPPORTING
    assert out["support"] in {AMBIGUOUS, INSUFFICIENT}
    for match in out["identity_matches"]:
        if match["result"] == "PARTIAL_MATCH":
            assert not is_address_compatible(type("M", (), match)())


# ── 27. locality-only ──────────────────────────────────────────────────────

def test_27_locality_only_is_not_supporting():
    out = _roll(
        _prop(address="Aleea Negoiu nr. 8, Cluj-Napoca"),
        _doc(facts=[_fact("locality", "Cluj-Napoca")]),
    )
    assert out["support"] != SUPPORTING
    assert out["support"] == INSUFFICIENT


# ── 28. 8 ↔ 8D + apartment match ───────────────────────────────────────────

def test_28_suffix_partial_with_apartment_is_supporting():
    out = _roll(
        _apt_prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8D"),
            _fact("apartment", "25"),
        ]),
    )
    assert out["support"] == SUPPORTING
    assert any(
        m["claim_type"] == "PROPERTY_ADDRESS" and m["result"] == "PARTIAL_MATCH"
        for m in out["identity_matches"]
    )


# ── 29. 8 ↔ 8D without apartment on multi-unit ─────────────────────────────

def test_29_suffix_partial_without_apartment_on_multi_unit_is_ambiguous():
    out = _roll(
        _apt_prop(),
        _doc(facts=[_fact("address", "Aleea Negoiu nr. 8D")]),
    )
    assert out["support"] == AMBIGUOUS


# ── 30. address + surface conflict + rooms conflict ────────────────────────

def test_30_address_exact_surface_and_rooms_conflict_stays_supporting():
    out = _roll(
        _prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("surface_m2", "80"),
            _fact("rooms", "1"),
        ]),
    )
    assert out["support"] == SUPPORTING


# ── 31. address exact + stair conflict is not identity CONFLICTING ─────────

def test_31_stair_conflict_is_not_identity_conflicting():
    prop = _prop(stair="2")
    out = _roll(prop, _doc(facts=[
        _fact("address", "Aleea Negoiu nr. 8"),
        _fact("stair", "A"),
    ]))
    assert out["support"] != CONFLICTING
    assert out["support"] in {SUPPORTING, AMBIGUOUS}


# ── 32. CF + address determined by address/unit ────────────────────────────

def test_32_cf_plus_address_is_determined_by_address():
    out = _roll(
        _prop(),
        _doc(facts=[
            _fact("address", "Aleea Negoiu nr. 8"),
            _fact("cf_number", "99999"),
        ]),
    )
    assert out["support"] == SUPPORTING
    assert all(m["claim_type"] != "PROPERTY_CF" for m in out["identity_matches"])
    assert "99999" not in _dump(out)


# ── 33. V1 superseded excluded from overall ────────────────────────────────

def test_33_superseded_v1_excluded_from_overall():
    docs = [
        _doc("doc-v", 1, [_fact("address", "Aleea Negoiu nr. 10")], superseded=True),
        _doc("doc-v2", 2, [_fact("address", "Aleea Negoiu nr. 8")], superseded=False),
    ]
    out = rollup_property_document_support(_prop(), docs)
    assert out["support"] == SUPPORTING
    by_id = {d["document_id"]: d for d in out["documents"]}
    if "doc-v" in by_id:
        assert by_id["doc-v"]["included_in_overall"] is False
        assert by_id["doc-v"]["support"] == CONFLICTING
    assert by_id["doc-v2"]["included_in_overall"] is True


# ── 34. all INSUFFICIENT ───────────────────────────────────────────────────

def test_34_all_insufficient_overall_insufficient():
    docs = [
        _doc("d1", 1, [_fact("surface_m2", "54.20")]),
        _doc("d2", 1, [_fact("cf_number", "1")]),
    ]
    out = rollup_property_document_support(_prop(), docs)
    assert out["support"] == INSUFFICIENT
    assert all(d["support"] == INSUFFICIENT for d in out["documents"] if d.get("eligible"))


# ── 35. only AMBIGUOUS ─────────────────────────────────────────────────────

def test_35_only_ambiguous_overall_ambiguous():
    docs = [
        _doc("d1", 1, [_fact("address", "Aleea Negoiu nr. 8")]),
    ]
    out = rollup_property_document_support(_apt_prop(), docs)
    assert out["documents"][0]["support"] == AMBIGUOUS
    assert out["support"] == AMBIGUOUS


# ── 36. metadata-only ──────────────────────────────────────────────────────

def test_36_metadata_only_is_insufficient():
    out = _roll(_prop(), _doc(
        facts=[],
        category="cadastru",
        filename="x.pdf",
        title="Extras CF",
        extraction_status="empty",
    ))
    assert out["support"] == INSUFFICIENT


# ── 37. subject=document accepted; not converted to Property ───────────────

def test_37_document_subject_fact_is_not_converted_to_property_entity():
    facts = [_fact("address", "Aleea Negoiu nr. 8", subject="document")]
    out = _roll(_prop(), _doc(facts=facts))
    assert out["support"] == SUPPORTING
    blob = _dump(out)
    assert "subject_type\":\"property\"" not in blob.replace(" ", "")
    assert facts[0]["subject"] == "document"


# ── extras required by the phase ───────────────────────────────────────────

def test_deleted_document_excluded_from_aggregation():
    docs = [
        _doc("gone", 1, [_fact("address", "Aleea Negoiu nr. 10")], deleted=True),
        _doc("keep", 1, [_fact("surface_m2", "54.20")]),
    ]
    out = rollup_property_document_support(_prop(), docs)
    ids = {d["document_id"] for d in out["documents"]}
    assert "gone" not in ids
    assert out["support"] == INSUFFICIENT


def test_output_is_deterministic():
    prop = _apt_prop()
    doc = _doc(facts=[
        _fact("apartment", "25"),
        _fact("address", "Aleea Negoiu nr. 8"),
        _fact("surface_m2", "54.20"),
    ])
    a = _roll(prop, doc)
    b = _roll(prop, doc)
    assert a == b
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_no_side_effects_on_document_or_ledger_snapshots():
    prop = _apt_prop()
    facts = [_fact("address", "Aleea Negoiu nr. 8"), _fact("apartment", "25")]
    doc = _doc(facts=facts)
    doc["extracted_facts"] = facts
    ledger = {"collection": "hartablocuri_source_records", "link_status": "none", "building_id": None}
    import_batches = [{"id": "batch-1"}]
    external_sources = {"hartablocuri": {"status": "observed"}}
    resolver = {"status": "probable"}
    before = {
        "prop": copy.deepcopy(prop),
        "doc": copy.deepcopy(doc),
        "facts": copy.deepcopy(facts),
        "ledger": copy.deepcopy(ledger),
        "import_batches": copy.deepcopy(import_batches),
        "external_sources": copy.deepcopy(external_sources),
        "resolver": copy.deepcopy(resolver),
    }
    _roll(prop, doc)
    rollup_property_document_support(prop, [doc])
    assert prop == before["prop"]
    assert doc == before["doc"]
    assert facts == before["facts"]
    assert ledger == before["ledger"]
    assert import_batches == before["import_batches"]
    assert external_sources == before["external_sources"]
    assert resolver == before["resolver"]


def test_module_is_pure_no_db_routes_llm():
    src = inspect.getsource(dps)
    assert "from db" not in src
    assert "import db" not in src
    assert "pymongo" not in src
    assert "MongoClient" not in src
    assert "insert_one" not in src
    assert "update_one" not in src
    assert "insert_many" not in src
    assert "fastapi" not in src.lower()
    assert "call_llm" not in src
    assert "ai_docs" not in src
    assert "openai" not in src.lower()
    assert "document_fact_extraction" not in src
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "eval" not in names and "exec" not in names


def test_does_not_modify_9c_surface():
    src = inspect.getsource(cm)
    assert "DOCUMENT_PROPERTY_SUPPORT" not in src
    assert "rollup_document_property_support" not in src


def test_suffix_rule_rejects_street_only_partial():
    house = _roll(_prop(), _doc(facts=[_fact("address", "Aleea Negoiu nr. 8D")]))
    street = _roll(_prop(), _doc(facts=[_fact("street", "Aleea Negoiu")]))
    assert house["support"] == SUPPORTING
    assert street["support"] != SUPPORTING
    suffix_hits = [m for m in house["identity_matches"] if m["result"] == "PARTIAL_MATCH"]
    assert suffix_hits
    assert "suffix" in (suffix_hits[0].get("note") or "").lower()
