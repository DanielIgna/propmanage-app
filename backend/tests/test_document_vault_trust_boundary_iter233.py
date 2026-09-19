"""Faza A — Document Vault trust boundary. Isolated. No Building / HB / identity writes."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

from routes.property_documents import (
    _completeness,
    declared_category_of,
    document_contributes_to_completeness,
)


def _run(coro):
    return asyncio.run(coro)


def _client_doc(cat, **extra):
    d = {
        "category": cat,
        "declared_category": cat,
        "verification_status": "unverified",
        "provenance": "declared",
        "source": "owner_upload",
        "deleted": False,
        "superseded": False,
    }
    d.update(extra)
    return d


def _verified_doc(cat, **extra):
    d = _client_doc(cat, verification_status="verified", provenance="declared", source="platform")
    d.update(extra)
    return d


def _specialist_doc(cat, **extra):
    d = _client_doc(cat, verification_status="unverified", provenance="documented", source="specialist")
    d.update(extra)
    return d


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, _n):
        return list(self._docs)


class _Coll:
    def __init__(self, *, docs=None, one=None, count=0):
        self._docs = docs or []
        self._one = one
        self._count = count

    def find(self, *_a, **_k):
        return _Cursor(self._docs)

    async def find_one(self, *_a, **_k):
        return self._one

    async def count_documents(self, *_a, **_k):
        return self._count


class _FakeDB:
    def __init__(self, docs):
        self.property_documents = _Coll(docs=docs)
        self.twins = _Coll(one=None)
        self.property_assets = _Coll(count=0)
        self.requests = _Coll(count=0)
        self.warranties = _Coll(count=0)
        self.maintenance_logs = _Coll(count=0)
        self.properties = _Coll(one={})


def _score(docs):
    with patch("routes.property_documents.db", _FakeDB(docs)):
        return _run(_completeness("prop1", {}))


def _item(compl, iid):
    return next(i for i in compl["items"] if i["id"] == iid)


def test_client_cadastru_stored_not_scored():
    doc = _client_doc("cadastru")
    assert document_contributes_to_completeness(doc) is False
    compl = _score([doc])
    cad = _item(compl, "cadastru")
    assert cad["earned"] == 0
    assert cad["done"] is False
    assert cad["declared"] is True
    assert cad["presence"] == "declared_only"
    assert compl["score"] == 0
    assert compl["docs_count"] == 1
    assert compl["contributing_docs_count"] == 0
    assert compl["declared_unverified_count"] == 1
    cad_missing = next(m for m in compl["missing"] if m["id"] == "cadastru")
    assert cad_missing["declared_pending"] is True


def test_client_act_proprietate_not_scored():
    compl = _score([_client_doc("act_proprietate")])
    act = _item(compl, "act_proprietate")
    assert act["earned"] == 0
    assert act["declared"] is True
    assert compl["score"] == 0


def test_client_factura_not_verified_and_not_scored():
    doc = _client_doc("factura")
    assert document_contributes_to_completeness(doc) is False
    compl = _score([doc])
    fac = _item(compl, "facturi")
    assert fac["earned"] == 0
    assert fac["presence"] == "declared_only"


def test_multiple_unverified_do_not_inflate_score():
    docs = [
        _client_doc("cadastru"),
        _client_doc("act_proprietate"),
        _client_doc("certificat_energetic"),
        _client_doc("plan_tehnic"),
        _client_doc("factura"),
        _client_doc("foto"),
        _client_doc("foto"),
        _client_doc("foto"),
        _client_doc("raport_inspectie"),
    ]
    compl = _score(docs)
    assert compl["docs_count"] == 9
    assert compl["contributing_docs_count"] == 0
    assert compl["score"] == 0
    assert all(
        i["earned"] == 0
        for i in compl["items"]
        if i["id"] in {
            "cadastru", "act_proprietate", "certificat_energetic", "plan_tehnic",
            "foto", "facturi", "audit",
        }
    )


def test_verified_document_still_scores():
    compl = _score([_verified_doc("cadastru")])
    cad = _item(compl, "cadastru")
    assert cad["earned"] == 6
    assert cad["done"] is True
    assert cad["presence"] == "trusted"
    assert compl["score"] == 6
    assert compl["contributing_docs_count"] == 1


def test_specialist_documented_still_scores():
    """Do not redefine specialist/documented semantics in Faza A."""
    compl = _score([_specialist_doc("act_proprietate")])
    act = _item(compl, "act_proprietate")
    assert act["earned"] == 10
    assert compl["score"] == 10


def test_legacy_category_field_without_declared_category():
    doc = {
        "category": "cadastru",
        "verification_status": "unverified",
        "provenance": "declared",
        "source": "owner_upload",
    }
    assert declared_category_of(doc) == "cadastru"
    compl = _score([doc])
    assert _item(compl, "cadastru")["earned"] == 0
    assert _item(compl, "cadastru")["declared"] is True


def test_legacy_verified_without_declared_category():
    doc = {"category": "cadastru", "verification_status": "verified", "provenance": "declared"}
    assert document_contributes_to_completeness(doc) is True
    assert _item(_score([doc]), "cadastru")["earned"] == 6


def test_deleted_or_superseded_never_contribute():
    assert document_contributes_to_completeness(_verified_doc("cadastru", deleted=True)) is False
    assert document_contributes_to_completeness(_verified_doc("cadastru", superseded=True)) is False


def test_journey_items_done_false_for_unverified_client():
    """House Journey L5 reads items[].done from this engine — unverified must not look verified."""
    compl = _score([
        _client_doc("act_proprietate"),
        _client_doc("cadastru"),
        _client_doc("certificat_energetic"),
    ])
    for iid in ("act_proprietate", "cadastru", "certificat_energetic"):
        assert _item(compl, iid)["done"] is False
    assert compl["score"] < 60


def test_trust_score_audit_not_from_unverified_client_report():
    """Trust Score audit must not treat a client-declared inspection report as verified evidence."""
    from routes.property_passport import _trust_score

    class _TrustDB(_FakeDB):
        def __init__(self, docs):
            super().__init__(docs)
            self.requests = _Coll(count=0)
            self.warranties = _Coll(count=0)
            self.maintenance_logs = _Coll(count=0)

    with patch("routes.property_passport.db", _TrustDB([_client_doc("raport_inspectie")])):
        trust = _run(_trust_score("aaaaaaaaaaaaaaaaaaaaaaaa"))
    audit = next(f for f in trust["factors"] if f["id"] == "audit")
    verified = next(f for f in trust["factors"] if f["id"] == "verified_docs")
    assert audit["earned"] == 0
    assert verified["earned"] == 0


def test_trust_score_verified_report_still_counts():
    from routes.property_passport import _trust_score

    class _TrustDB(_FakeDB):
        pass

    with patch("routes.property_passport.db", _TrustDB([_verified_doc("raport_inspectie")])):
        trust = _run(_trust_score("aaaaaaaaaaaaaaaaaaaaaaaa"))
    audit = next(f for f in trust["factors"] if f["id"] == "audit")
    verified = next(f for f in trust["factors"] if f["id"] == "verified_docs")
    assert audit["earned"] == 15
    assert verified["earned"] == 5


def test_upload_permissions_and_retrieval_fields_unchanged():
    """Client uploads remain allowed; retrieval still exposes category + verification_status."""
    from routes.property_documents import CATEGORIES, DOC_FIELDS
    assert "cadastru" in CATEGORIES
    assert "act_proprietate" in CATEGORIES
    assert "factura" in CATEGORIES
    assert "verification_status" in DOC_FIELDS
    assert "category" in DOC_FIELDS
    assert "declared_category" in DOC_FIELDS
    assert "history" in DOC_FIELDS


def test_copilot_book_payload_exposes_trust_boundary():
    compl = _score([_client_doc("cadastru")])
    assert compl["trust_boundary"] == "uploaded_ne_verified"
    assert compl["score_basis"] == "accepted_documentation"
    assert compl["items"][0]["done"] is False or _item(compl, "cadastru")["done"] is False
