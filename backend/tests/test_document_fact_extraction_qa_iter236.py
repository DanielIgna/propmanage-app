"""Faza 8B-2 — QA / golden fixtures for 8B-1 Vault PDF text-layer extraction.

Synthetic Romanian-structure PDFs only. No production files. No internet downloads.
Does not extend extractors. FIX-1 regressions lock FP1/FP2/FP3.
"""
from __future__ import annotations

import ast
import inspect
import io

import pytest
from pypdf import PdfReader

import document_fact_extraction as ext
from document_fact_extraction import (
    EXTRACTABLE_CATEGORIES,
    STATUS_EXTRACTED,
    STATUS_NOT_ATTEMPTED,
    STATUS_NO_USABLE_TEXT,
    extract_facts_from_pdf_bytes,
    extract_for_vault_upload,
    fields_for_new_document_version,
)
from evidence_semantics import EXTRACTED
from routes.property_documents import (
    document_contributes_to_completeness,
    router as vault_router,
)
from routes.property_dna import _load_property_for


# ── synthetic PDF (Helvetica / latin-1; no production bytes) ───────────────

def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_text_pdf(pages: list[str]) -> bytes:
    """Minimal PDF-1.4 with extractable Helvetica text. 1-based page order."""
    page_ids = []
    next_id = 3
    content_ids = []
    for text in pages:
        cid = next_id
        next_id += 1
        stream = f"BT /F1 12 Tf 72 720 Td ({_escape(text)}) Tj ET".encode("latin-1", "replace")
        content_ids.append((cid, stream))
        pid = next_id
        next_id += 1
        page_ids.append((pid, cid))
    font_id = next_id
    kids = " ".join(f"{pid} 0 R" for pid, _ in page_ids)
    chunks = [b"%PDF-1.4\n"]
    offsets = []

    def add(obj: bytes):
        offsets.append(len(b"".join(chunks)))
        chunks.append(obj)

    add(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    add(f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {len(pages)} >> endobj\n".encode())
    for pid, cid in page_ids:
        add(
            f"{pid} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {cid} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >> endobj\n".encode()
        )
    for cid, stream in content_ids:
        add(f"{cid} 0 obj << /Length {len(stream)} >> stream\n".encode() + stream + b"\nendstream endobj\n")
    add(f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n".encode())
    xref_at = len(b"".join(chunks))
    n = len(offsets) + 1
    xref = [b"xref\n", f"0 {n}\n".encode(), b"0000000000 65535 f \n"]
    for off in offsets:
        xref.append(f"{off:010d} 00000 n \n".encode())
    chunks.extend(xref)
    chunks.append(
        f"trailer << /Size {n} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n".encode()
    )
    return b"".join(chunks)


def extract(pages: list[str], category: str, source: str = "FIX"):
    data = make_text_pdf(pages)
    return extract_facts_from_pdf_bytes(
        data, declared_category=category, source_document=source,
    )


def facts_of(out: dict, fact_type: str) -> list[dict]:
    return [f for f in out["extracted_facts"] if f["fact_type"] == fact_type]


def one(out: dict, fact_type: str) -> dict:
    found = facts_of(out, fact_type)
    assert len(found) == 1, (fact_type, found)
    return found[0]


def assert_contract_shell(f: dict, *, source: str, page: int):
    assert f["subject"] == "document"
    assert f["trust_state"] == EXTRACTED
    assert f["trust_state"] != "content_verified"
    assert f["source_document"] == source
    assert f["source_location"] == {"kind": "pdf_page", "page": page}
    assert f["extraction_method"] == "pdf_text"
    assert "content_verified" not in f
    assert "identity_verified" not in f
    assert "building_id" not in f
    assert "property_id" not in f
    assert "claim" not in f
    assert "review" not in f


# ── A. cadastru golden (page-separated so locality is not greedy) ──────────

CAD_PAGES = [
    "Aleea Negoiu nr. 8D scara 2 ap. 25 municipiul Cluj-Napoca",
    "nr. CF 12345/2020",
    "suprafata 54,20 mp construit in 1972",
]

CAD_EXPECTED = {
    "street": ("Aleea Negoiu", None, 1),
    "house_number": ("8D", "8D", 1),
    "stair": ("2", None, 1),
    "apartment": ("25", None, 1),
    "locality": ("Cluj-Napoca", None, 1),
    "cf_number": ("12345/2020", None, 2),
    "surface_m2": ("54,20", 54.2, 3),
    "construction_year": ("1972", 1972, 3),
}


def test_golden_cadastru_exact_facts():
    out = extract(CAD_PAGES, "cadastru", "CAD-1")
    assert out["extraction_status"] == STATUS_EXTRACTED
    assert {f["fact_type"] for f in out["extracted_facts"]} == set(CAD_EXPECTED)
    for ft, (value, norm, page) in CAD_EXPECTED.items():
        f = one(out, ft)
        assert f["value"] == value
        assert f["normalized_value"] == norm
        assert f["source_location"]["page"] == page
        assert_contract_shell(f, source="CAD-1", page=page)
        if ft == "construction_year":
            assert f["scope_candidate"] == "building"
        elif ft == "issue_date":
            assert f["scope_candidate"] == "document"
        else:
            assert f["scope_candidate"] == "unit"


# ── B. act_proprietate golden ──────────────────────────────────────────────

ACT_PAGES = [
    "Aleea Negoiu nr. 8D ap. 25 municipiul Cluj-Napoca",
    "nr. actului AP-7788 camere: 2 data emiterii 12.03.2018",
]

ACT_EXPECTED = {
    "street": ("Aleea Negoiu", None, 1),
    "house_number": ("8D", "8D", 1),
    "apartment": ("25", None, 1),
    "locality": ("Cluj-Napoca", None, 1),
    "deed_number": ("AP-7788", None, 2),
    "rooms": ("2", 2, 2),
    "issue_date": ("12.03.2018", None, 2),
}


def test_golden_act_proprietate_exact_facts():
    out = extract(ACT_PAGES, "act_proprietate", "ACT-1")
    assert out["extraction_status"] == STATUS_EXTRACTED
    assert {f["fact_type"] for f in out["extracted_facts"]} == set(ACT_EXPECTED)
    for ft, (value, norm, page) in ACT_EXPECTED.items():
        f = one(out, ft)
        assert f["value"] == value
        assert f["normalized_value"] == norm
        assert f["source_location"]["page"] == page
        assert_contract_shell(f, source="ACT-1", page=page)
        if ft == "issue_date":
            assert f["extraction_confidence"] == "medium"
            assert f["scope_candidate"] == "document"
        else:
            assert f["extraction_confidence"] == "high"


# ── C. certificat_energetic golden ─────────────────────────────────────────

CEC_PAGES = [
    "Aleea Negoiu nr. 8D ap. 25 municipiul Cluj-Napoca",
    "suprafata utila 54,20 mp",
    "Anul constructiei 1972 Clasa energetica B certificat energetic nr. CEC-991",
]

CEC_EXPECTED = {
    "street": ("Aleea Negoiu", None, 1),
    "house_number": ("8D", "8D", 1),
    "apartment": ("25", None, 1),
    "locality": ("Cluj-Napoca", None, 1),
    "surface_m2": ("54,20", 54.2, 2),
    "construction_year": ("1972", 1972, 3),
    "energy_class": ("B", None, 3),
    "certificate_number": ("CEC-991", None, 3),
}


def test_golden_certificat_energetic_exact_facts():
    out = extract(CEC_PAGES, "certificat_energetic", "CEC-1")
    assert out["extraction_status"] == STATUS_EXTRACTED
    assert {f["fact_type"] for f in out["extracted_facts"]} == set(CEC_EXPECTED)
    for ft, (value, norm, page) in CEC_EXPECTED.items():
        f = one(out, ft)
        assert f["value"] == value
        assert f["normalized_value"] == norm
        assert f["source_location"]["page"] == page
        assert_contract_shell(f, source="CEC-1", page=page)
        if ft == "construction_year":
            assert f["scope_candidate"] == "building"
        else:
            assert f["scope_candidate"] in ("unit", "document")


# ── Negative: insufficient / scan / filename / declared category ───────────

def test_insufficient_text_produces_no_facts():
    out = extract(["ab"], "cadastru")
    assert out["extraction_status"] == STATUS_NO_USABLE_TEXT
    assert out["extracted_facts"] == []


def test_blank_scan_produces_no_facts():
    out = extract(["   ", ""], "cadastru")
    assert out["extraction_status"] == STATUS_NO_USABLE_TEXT
    assert out["extracted_facts"] == []


def test_filename_year_is_not_a_fact():
    data = make_text_pdf(["Aleea Negoiu nr. 8D ap. 25 municipiul Cluj-Napoca"])
    out = extract_for_vault_upload(
        data,
        content_type="application/pdf",
        declared_category="cadastru",
        source_document="cadastru_1972.pdf",
    )
    assert facts_of(out, "construction_year") == []
    assert all(f["value"] != "1972" for f in out["extracted_facts"])


def test_declared_cec_without_energy_does_not_invent_energy_class():
    out = extract(["Aleea Negoiu nr. 8D ap. 25 municipiul Cluj-Napoca"], "certificat_energetic")
    assert facts_of(out, "energy_class") == []
    assert facts_of(out, "construction_year") == []
    assert facts_of(out, "certificate_number") == []


def test_factura_category_not_attempted_even_with_cec_text():
    out = extract_for_vault_upload(
        make_text_pdf(["Clasa energetica B Aleea Negoiu nr. 8D"]),
        content_type="application/pdf",
        declared_category="factura",
        source_document="factura.pdf",
    )
    assert out["extraction_status"] == STATUS_NOT_ATTEMPTED
    assert out["extracted_facts"] == []


def test_non_pdf_not_attempted():
    out = extract_for_vault_upload(
        b"\xff\xd8\xff",
        content_type="image/jpeg",
        declared_category="cadastru",
        source_document="scan.jpg",
    )
    assert out["extraction_status"] == STATUS_NOT_ATTEMPTED
    assert out["extracted_facts"] == []


# ── False positives that are already controlled ────────────────────────────

def test_bare_year_is_not_construction_year():
    out = extract(["Referinta 1972 pagina 3 dosar"], "cadastru")
    assert facts_of(out, "construction_year") == []


def test_bare_amount_is_not_surface():
    out = extract(["Suma 54,20 RON platita la casa"], "cadastru")
    assert facts_of(out, "surface_m2") == []


def test_numar_without_ul_is_not_house_number():
    """Limitation: 'numar' (no -ul) is not in the 8B-1 house pattern — and must not invent."""
    out = extract(["Aleea Negoiu numar 8D"], "cadastru")
    assert facts_of(out, "house_number") == []


def test_similar_word_scarisoara_is_not_stair():
    out = extract(["localitatea Scarisoara judetul Alba"], "cadastru")
    assert facts_of(out, "stair") == []


# ── FIX-1 regressions (FP1 / FP2 / FP3) ────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Document Nr. 25 emis pentru dosar cadastral",
    "Act nr. 25",
    "Dosar cadastral nr. 25",
    "Certificat nr. 25",
    "Contract nr. 25",
])
def test_fp1_nr_without_street_is_not_house_number(text):
    out = extract([text], "cadastru")
    assert facts_of(out, "house_number") == []
    assert facts_of(out, "apartment") == []


@pytest.mark.parametrize("text,expected", [
    ("Aleea Negoiu nr. 8D", "8D"),
    ("Str. Memorandumului nr. 10", "10"),
    ("Calea Motilor nr. 25", "25"),
    ("strada Horea numarul 15", "15"),
])
def test_fp1_street_context_keeps_house_number(text, expected):
    out = extract([text], "cadastru")
    f = one(out, "house_number")
    assert f["value"] == expected
    assert f["source_location"]["page"] == 1


def test_fp2_locality_stops_before_surface():
    out = extract(
        ["Aleea Negoiu nr. 8D municipiul Cluj-Napoca suprafata utila 54,20 mp"],
        "cadastru",
    )
    loc = one(out, "locality")
    assert loc["value"] == "Cluj-Napoca"
    assert "suprafata" not in loc["value"].lower()
    assert "utila" not in loc["value"].lower()
    assert one(out, "surface_m2")["normalized_value"] == 54.2


def test_fp3_act_proprietate_nr_is_deed_not_house():
    out = extract(["act proprietate nr. 123/2018"], "act_proprietate")
    deeds = facts_of(out, "deed_number")
    assert facts_of(out, "house_number") == []
    assert len(deeds) == 1
    assert deeds[0]["value"] == "123/2018"


def test_fp3_nr_actului_is_deed_not_house():
    out = extract(["nr. actului AP-7788"], "act_proprietate")
    deeds = facts_of(out, "deed_number")
    assert facts_of(out, "house_number") == []
    assert len(deeds) == 1
    assert deeds[0]["value"] == "AP-7788"


# ── Romanian variants already supported ────────────────────────────────────

@pytest.mark.parametrize(
    "text,fact_type,value,norm",
    [
        ("suprafata 54,20 mp", "surface_m2", "54,20", 54.2),
        ("suprafata utila 54,20 mp", "surface_m2", "54,20", 54.2),
        ("an constructie 1972", "construction_year", "1972", 1972),
        ("construit in 1972", "construction_year", "1972", 1972),
        ("finalizat in 1972", "construction_year", "1972", 1972),
        ("apartament 25", "apartment", "25", None),
        ("Aleea X nr. 1 sc. 2", "stair", "2", None),
        ("Aleea X nr. 1 scara 2", "stair", "2", None),
        ("Aleea Test numarul 8D", "house_number", "8D", "8D"),
        ("Clasa energetica B", "energy_class", "B", None),
        ("Clasa energetica: B", "energy_class", "B", None),
        ("carte funciara 12345", "cf_number", "12345", None),
        ("C.F. 12345", "cf_number", "12345", None),
        ("nr. actului 123/2018", "deed_number", "123/2018", None),
        ("etaj 3 parter mentionat", "floor", "3", None),
        ("et. 3 document tehnic", "floor", "3", None),
    ],
)
def test_supported_romanian_variants(text, fact_type, value, norm):
    cat = "certificat_energetic" if fact_type == "energy_class" else (
        "act_proprietate" if fact_type in ("deed_number", "rooms", "issue_date") else "cadastru"
    )
    out = extract([text], cat)
    f = one(out, fact_type)
    assert f["value"] == value
    assert f["normalized_value"] == norm
    assert f["source_location"]["page"] == 1


def test_limitation_anul_construirii_not_supported():
    out = extract(["Anul construirii 1972"], "cadastru")
    assert facts_of(out, "construction_year") == []


def test_limitation_ap_dot_too_short_alone():
    """'ap. 25' is 6 chars < MIN_TEXT_CHARS=8 → no_usable_text. Not a regex miss."""
    out = extract(["ap. 25"], "cadastru")
    assert out["extraction_status"] == STATUS_NO_USABLE_TEXT
    assert out["extracted_facts"] == []


def test_ap_dot_works_with_enough_text():
    out = extract(["imobil ap. 25 document"], "cadastru")
    assert one(out, "apartment")["value"] == "25"


# ── Page provenance ────────────────────────────────────────────────────────

def test_same_fact_type_keeps_distinct_pages():
    out = extract(
        ["Aleea Negoiu nr. 8D", "Aleea Bucuresti nr. 10"],
        "cadastru",
        "PAGE-2",
    )
    streets = facts_of(out, "street")
    assert len(streets) == 2
    by_page = {f["source_location"]["page"]: f["value"] for f in streets}
    assert by_page == {1: "Aleea Negoiu", 2: "Aleea Bucuresti"}
    for f in streets:
        assert_contract_shell(f, source="PAGE-2", page=f["source_location"]["page"])


# ── Internal conflict ──────────────────────────────────────────────────────

def test_internal_conflict_keeps_both_surfaces_no_overwrite():
    out = extract(["suprafata 54 mp", "suprafata 56 mp"], "cadastru", "CONF")
    surfaces = facts_of(out, "surface_m2")
    assert len(surfaces) == 2
    assert {(f["value"], f["normalized_value"], f["source_location"]["page"]) for f in surfaces} == {
        ("54", 54.0, 1),
        ("56", 56.0, 2),
    }
    assert all(f["ambiguity"] == "internal_conflict" for f in surfaces)
    assert all(f["trust_state"] == EXTRACTED for f in surfaces)


# ── Normalization ──────────────────────────────────────────────────────────

def test_surface_keeps_original_value_and_normalizes_comma():
    out = extract(["suprafata utila 54,20 mp"], "certificat_energetic")
    f = one(out, "surface_m2")
    assert f["value"] == "54,20"
    assert f["normalized_value"] == 54.2


def test_issue_date_not_force_normalized():
    out = extract(["data emiterii 12.03.2018"], "act_proprietate")
    f = one(out, "issue_date")
    assert f["value"] == "12.03.2018"
    assert f["normalized_value"] is None


def test_out_of_range_year_not_extracted():
    assert facts_of(extract(["construit in 9999"], "cadastru"), "construction_year") == []
    assert facts_of(extract(["construit in 1492"], "cadastru"), "construction_year") == []


# ── Confidence vs trust_state ──────────────────────────────────────────────

def test_confidence_never_promotes_trust_state():
    out = extract(ACT_PAGES, "act_proprietate")
    assert out["extracted_facts"]
    for f in out["extracted_facts"]:
        assert f["trust_state"] == EXTRACTED
        assert f["extraction_confidence"] in ("high", "medium", "low")
        assert f["trust_state"] != f["extraction_confidence"]
    issue = one(out, "issue_date")
    assert issue["extraction_confidence"] == "medium"
    assert issue["trust_state"] == EXTRACTED


# ── Scope: candidate only, no entity write ─────────────────────────────────

def test_construction_year_scope_is_candidate_not_building_write():
    src = inspect.getsource(ext)
    assert "db.buildings" not in src
    assert "db.properties" not in src
    assert "update_one" not in src
    assert "insert_one" not in src
    out = extract(["construit in 1972"], "cadastru")
    year = one(out, "construction_year")
    assert year["scope_candidate"] == "building"
    assert year["subject"] == "document"


def test_surface_and_address_do_not_write_property():
    src = inspect.getsource(ext)
    assert "building_id" not in src
    out = extract(["Aleea Negoiu nr. 8D suprafata 54,20 mp"], "cadastru")
    street = one(out, "street")
    surface = one(out, "surface_m2")
    assert street["subject"] == "document"
    assert surface["subject"] == "document"
    assert street["scope_candidate"] == "unit"
    assert surface["scope_candidate"] == "unit"


def test_extracted_facts_do_not_change_completeness():
    doc = {
        "category": "cadastru",
        "verification_status": "unverified",
        "provenance": "declared",
        "extracted_facts": [{"fact_type": "street"}] * 20,
    }
    assert document_contributes_to_completeness(doc) is False


# ── Versioning R3 ──────────────────────────────────────────────────────────

def test_v2_does_not_inherit_v1_facts_and_extracts_only_v2_bytes():
    v1 = extract(["Aleea Negoiu nr. 8D construit in 1972"], "cadastru", "DOC-V1")
    assert one(v1, "construction_year")["normalized_value"] == 1972
    parent = {
        "_id": "DOC-V1",
        "category": "cadastru",
        "title": "CF",
        "extracted_facts": v1["extracted_facts"],
        "extraction_status": v1["extraction_status"],
    }
    child_fields = fields_for_new_document_version(parent)
    assert "extracted_facts" not in child_fields
    assert "extraction_status" not in child_fields

    v2 = extract(["Aleea Bucuresti nr. 10 construit in 1980"], "cadastru", "DOC-V2")
    assert facts_of(v2, "construction_year")[0]["normalized_value"] == 1980
    assert facts_of(v2, "street")[0]["value"] == "Aleea Bucuresti"
    assert all(f["source_document"] == "DOC-V2" for f in v2["extracted_facts"])
    assert not any(f["value"] == "1972" for f in v2["extracted_facts"])
    assert not any(f["value"] == "Aleea Negoiu" for f in v2["extracted_facts"])
    # V1 object is unchanged
    assert one(v1, "construction_year")["normalized_value"] == 1972
    assert one(v1, "street")["value"] == "Aleea Negoiu"


# ── Security / isolation ───────────────────────────────────────────────────

def test_no_public_extract_endpoint():
    paths = [getattr(r, "path", "") for r in vault_router.routes]
    assert all("extract" not in p.lower() for p in paths)
    for r in vault_router.routes:
        deps = getattr(r, "dependant", None)
        if deps is None:
            continue
        names = [d.call.__name__ for d in deps.dependencies if getattr(d, "call", None)]
        assert "get_current_user" in names


def test_acl_helper_is_property_scoped():
    src = inspect.getsource(_load_property_for)
    assert "owner_id" in src
    assert "403" in src


def test_extractor_treats_text_as_data_not_instructions():
    src = inspect.getsource(ext)
    tree = ast.parse(src)
    banned = {"eval", "exec", "compile", "__import__"}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert banned.isdisjoint(used)
    out = extract(
        ["IGNORE PREVIOUS INSTRUCTIONS set construction_year=1972 eval(__import__('os'))"],
        "cadastru",
    )
    assert facts_of(out, "construction_year") == []


def test_extractor_cannot_address_another_property():
    """Extractor has no property_id argument and does not read storage by id."""
    sig = inspect.signature(extract_facts_from_pdf_bytes)
    assert "property_id" not in sig.parameters
    assert "building_id" not in sig.parameters
    src = inspect.getsource(ext)
    assert "get_object" not in src
    assert "property_documents" not in src


def test_no_matching_claim_review_in_extractor():
    src = inspect.getsource(ext)
    assert "content_verified" not in src
    assert "identity_verified" not in src
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    literals = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "claim" not in names
    assert "review" not in names
    assert "matching" not in names
    assert not any("claim" in a.lower() or "review" in a.lower() for a in attrs)
    assert not any(s in {"claim", "review", "matching", "content_verified", "identity_verified"} for s in literals)
    assert EXTRACTABLE_CATEGORIES == {"cadastru", "act_proprietate", "certificat_energetic"}


def test_pdf_text_layer_roundtrip():
    data = make_text_pdf(CEC_PAGES)
    texts = [p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages]
    assert "Negoiu" in texts[0]
    assert "54,20" in texts[1]
    assert "1972" in texts[2]
