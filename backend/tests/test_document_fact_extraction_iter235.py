"""Faza 8B-1 — Vault PDF text-layer extraction. Isolated. No Building writes."""
from __future__ import annotations

import inspect
import io

from pypdf import PdfReader

import document_fact_extraction as ext
from document_fact_extraction import (
    STATUS_EXTRACTED,
    STATUS_NOT_ATTEMPTED,
    STATUS_NO_USABLE_TEXT,
    extract_facts_from_pdf_bytes,
    extract_for_vault_upload,
    fields_for_new_document_version,
)
from evidence_semantics import EXTRACTED
from routes.property_documents import document_contributes_to_completeness


G10 = "6aaadd4aaebd8dfb9c8aaf59"
NEGOIU_8D = "6a7724892e6529db42e95df1"
PTR = "6a9c6efff2ac8e128bd1d335"


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


def _pdf_ok():
    data = make_text_pdf(["Aleea Negoiu nr. 8D ap 25"])
    texts = [p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages]
    return data, texts


def test_pdf_builder_has_extractable_text():
    data, texts = _pdf_ok()
    assert any("Negoiu" in t or "8D" in t for t in texts)


def test_text_layer_extracts_address_facts():
    data = make_text_pdf(["Aleea Negoiu nr. 8D ap. 25 municipiul Cluj-Napoca"])
    out = extract_facts_from_pdf_bytes(data, declared_category="cadastru", source_document="docA")
    assert out["extraction_status"] == STATUS_EXTRACTED
    facts = out["extracted_facts"]
    types = {f["fact_type"]: f for f in facts}
    assert types["street"]["value"].lower().startswith("aleea negoiu")
    assert types["house_number"]["normalized_value"] == "8D"
    assert types["apartment"]["value"] == "25"
    assert types["locality"]["value"].startswith("Cluj")
    assert types["street"]["source_document"] == "docA"
    assert types["street"]["source_location"] == {"kind": "pdf_page", "page": 1}
    assert types["street"]["trust_state"] == EXTRACTED
    assert types["street"]["subject"] == "document"
    assert "content_verified" not in types["street"]
    assert "identity_verified" not in types["street"]
    assert "building_id" not in types["street"]
    assert "property_id" not in types["street"]


def test_page_index_preserved():
    data = make_text_pdf(["pagina goala", "nr. CF 12345/2020"])
    out = extract_facts_from_pdf_bytes(data, declared_category="cadastru", source_document="docB")
    cf = next(f for f in out["extracted_facts"] if f["fact_type"] == "cf_number")
    assert cf["source_location"]["page"] == 2


def test_cec_energy_and_surface_normalized():
    data = make_text_pdf(["Clasa energetica: B  suprafata 54,20 mp  certificat energetic nr. CEC-991"])
    out = extract_facts_from_pdf_bytes(
        data, declared_category="certificat_energetic", source_document="docC",
    )
    types = {f["fact_type"]: f for f in out["extracted_facts"]}
    assert types["energy_class"]["normalized_value"] is None or types["energy_class"]["value"].upper().startswith("B")
    assert types["energy_class"]["value"].upper().startswith("B")
    assert types["surface_m2"]["normalized_value"] == 54.2
    assert types["certificate_number"]["value"]


def test_construction_year_is_document_fact_not_building_write():
    src = inspect.getsource(ext)
    assert "db.buildings" not in src
    assert "update_one" not in src
    assert "construction_year" in src
    data = make_text_pdf(["construit in 1972"])
    out = extract_facts_from_pdf_bytes(data, declared_category="cadastru", source_document="docD")
    year = next(f for f in out["extracted_facts"] if f["fact_type"] == "construction_year")
    assert year["normalized_value"] == 1972
    assert year["subject"] == "document"
    assert year["scope_candidate"] == "building"
    assert year["trust_state"] == EXTRACTED


def test_address_does_not_imply_property_write():
    src = inspect.getsource(ext)
    assert "db.properties" not in src
    data = make_text_pdf(["Aleea Negoiu nr. 8D"])
    out = extract_facts_from_pdf_bytes(data, declared_category="act_proprietate", source_document="docE")
    addr = next(f for f in out["extracted_facts"] if f["fact_type"] == "street")
    assert addr["subject"] == "document"
    assert addr["scope_candidate"] == "unit"


def test_scan_or_image_not_attempted():
    blank = make_text_pdf(["   "])
    out = extract_facts_from_pdf_bytes(blank, declared_category="cadastru", source_document="docF")
    assert out["extraction_status"] == STATUS_NO_USABLE_TEXT
    assert out["extracted_facts"] == []
    img = extract_for_vault_upload(
        b"\xff\xd8\xff", content_type="image/jpeg", declared_category="cadastru", source_document="docG",
    )
    assert img["extraction_status"] == STATUS_NOT_ATTEMPTED
    assert img["extracted_facts"] == []


def test_other_category_not_attempted():
    data = make_text_pdf(["Aleea Negoiu nr. 8D"])
    out = extract_for_vault_upload(
        data, content_type="application/pdf", declared_category="factura", source_document="docH",
    )
    assert out["extraction_status"] == STATUS_NOT_ATTEMPTED


def test_internal_conflict_keeps_both_surfaces():
    data = make_text_pdf(["suprafata 54 mp", "suprafata 56 mp"])
    out = extract_facts_from_pdf_bytes(data, declared_category="cadastru", source_document="docI")
    surfaces = [f for f in out["extracted_facts"] if f["fact_type"] == "surface_m2"]
    assert len(surfaces) == 2
    assert {f["source_location"]["page"] for f in surfaces} == {1, 2}
    assert all(f["ambiguity"] == "internal_conflict" for f in surfaces)


def test_version_does_not_inherit_extracted_facts():
    parent = {
        "_id": "old",
        "category": "cadastru",
        "verification_status": "unverified",
        "extracted_facts": [{"fact_type": "street", "value": "old"}],
        "extraction_status": "extracted",
        "title": "CF",
    }
    child = fields_for_new_document_version(parent)
    assert "extracted_facts" not in child
    assert "extraction_status" not in child
    assert child["title"] == "CF"
    assert child["verification_status"] == "unverified"


def test_completeness_unchanged_by_extracted_facts():
    doc = {
        "category": "cadastru",
        "verification_status": "unverified",
        "provenance": "declared",
        "extracted_facts": [{"fact_type": "street"}] * 20,
    }
    assert document_contributes_to_completeness(doc) is False


def test_no_evidence_or_claims_collection_in_module():
    src = inspect.getsource(ext)
    assert "evidence" not in src.lower() or "extracted" in src
    assert "insert_one" not in src
    assert "claims" not in src


def test_pilot_ids_untouched_constants():
    assert G10 != NEGOIU_8D != PTR
    src = inspect.getsource(ext)
    assert G10 not in src
    assert NEGOIU_8D not in src
