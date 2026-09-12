"""Backend tests for Property Technical Record v2 (iter 182).

Covers:
  - Diagnostic verification chain (admin verify/reject with evidence rules)
  - Diagnostic document_ref validation + document_snapshot on create
  - Building verify + building-context re-modification -> unverified
  - Building neighbours + buildings search + attach-building
  - Documents picker
  - Transaction readiness PDF export
  - viewer.is_verifier flag in technical-record response
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
PROP_ID = "6a11d70e600be19667009c93"  # Skyline Loft A4


# --- Fixtures ---------------------------------------------------------------
@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "client@propmanage.io", "password": "Client123!"
    }, timeout=30)
    assert r.status_code == 200, f"Client login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@propmanage.io", "password": "1!nasov01ADMIN"
    }, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code}")
    tok = r.json().get("token") or r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def created_diag_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(created_diag_ids, client_session):
    yield
    for did in created_diag_ids:
        try:
            client_session.delete(f"{BASE_URL}/api/diagnostics/{did}", timeout=15)
        except Exception:
            pass


def _make_diag(session, doc_ref=None, source_ref=None):
    payload = {
        "diagnostic_type": "electrical",
        "jurisdiction": "RO",
        "issuing_professional": "TEST_iter182 Prof",
        "findings": "TEST_iter182 findings",
    }
    if doc_ref:
        payload["document_ref"] = doc_ref
    if source_ref:
        payload["source_reference"] = source_ref
    return session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics", json=payload, timeout=20)


# --- Viewer flag ------------------------------------------------------------
class TestViewerFlag:
    def test_client_viewer_is_not_verifier(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/technical-record")
        assert r.status_code == 200
        v = r.json().get("viewer")
        assert v is not None
        assert v.get("role") == "client"
        assert v.get("is_verifier") is False

    def test_admin_viewer_is_verifier(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/technical-record")
        assert r.status_code == 200
        v = r.json().get("viewer")
        assert v.get("is_verifier") is True


# --- Documents picker -------------------------------------------------------
class TestDocumentsPicker:
    def test_picker_returns_list(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/documents-picker")
        assert r.status_code == 200
        data = r.json()
        assert "documents" in data and isinstance(data["documents"], list)
        assert "total" in data
        # If any docs, each doc has id/title/category
        for d in data["documents"]:
            assert "id" in d


# --- Diagnostic verify / reject flow ---------------------------------------
class TestVerifyRejectFlow:
    def test_client_cannot_verify(self, client_session, admin_session, created_diag_ids):
        r = _make_diag(client_session, source_ref="TEST_iter182 SRC-1")
        assert r.status_code == 200, r.text
        did = r.json()["diagnostic"]["id"]
        created_diag_ids.append(did)

        rv = client_session.post(f"{BASE_URL}/api/admin/diagnostics/{did}/verify", json={}, timeout=20)
        assert rv.status_code == 403

    def test_admin_verify_without_evidence_fails(self, client_session, admin_session, created_diag_ids):
        # Create diagnostic with NO document_ref and NO source_reference
        payload = {"diagnostic_type": "electrical", "jurisdiction": "RO",
                   "findings": "TEST_iter182 no-evidence"}
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        did = r.json()["diagnostic"]["id"]
        created_diag_ids.append(did)

        rv = admin_session.post(f"{BASE_URL}/api/admin/diagnostics/{did}/verify", json={}, timeout=20)
        assert rv.status_code == 400
        assert "evident" in rv.text.lower() or "verificat" in rv.text.lower()

    def test_admin_verify_with_source_reference(self, client_session, admin_session, created_diag_ids):
        r = _make_diag(client_session, source_ref="TEST_iter182 SRC-verify")
        assert r.status_code == 200
        did = r.json()["diagnostic"]["id"]
        created_diag_ids.append(did)

        rv = admin_session.post(
            f"{BASE_URL}/api/admin/diagnostics/{did}/verify",
            json={"notes": "TEST_iter182 verified"}, timeout=20)
        assert rv.status_code == 200, rv.text
        d = rv.json()["diagnostic"]
        assert d["verification_status"] == "verified"
        assert d["confidence"] == "high"
        assert d.get("verified_at")
        assert d.get("verified_by")
        assert any(h.get("event") == "verify" for h in d.get("history", []))

    def test_admin_reject_short_reason_fails(self, client_session, admin_session, created_diag_ids):
        r = _make_diag(client_session, source_ref="TEST_iter182 SRC-reject")
        assert r.status_code == 200
        did = r.json()["diagnostic"]["id"]
        created_diag_ids.append(did)

        # No reason
        rv = admin_session.post(f"{BASE_URL}/api/admin/diagnostics/{did}/reject", json={}, timeout=20)
        assert rv.status_code in (400, 422)
        # Too short
        rv2 = admin_session.post(f"{BASE_URL}/api/admin/diagnostics/{did}/reject", json={"reason": "ab"}, timeout=20)
        assert rv2.status_code in (400, 422)

    def test_admin_reject_valid_reason(self, client_session, admin_session, created_diag_ids):
        r = _make_diag(client_session, source_ref="TEST_iter182 SRC-reject-valid")
        did = r.json()["diagnostic"]["id"]
        created_diag_ids.append(did)

        # First verify
        rv = admin_session.post(f"{BASE_URL}/api/admin/diagnostics/{did}/verify", json={}, timeout=20)
        assert rv.status_code == 200

        # Then reject
        rr = admin_session.post(
            f"{BASE_URL}/api/admin/diagnostics/{did}/reject",
            json={"reason": "TEST_iter182 evidence insuficientă"}, timeout=20)
        assert rr.status_code == 200, rr.text
        d = rr.json()["diagnostic"]
        assert d["verification_status"] == "unverified"
        assert d.get("rejection_reason", "").startswith("TEST_iter182")
        assert any(h.get("event") == "reject" for h in d.get("history", []))


# --- Diagnostic document_ref + snapshot ------------------------------------
class TestDiagnosticDocumentRef:
    def test_invalid_document_ref_rejected(self, client_session, created_diag_ids):
        # Non-existent doc id
        payload = {"diagnostic_type": "electrical", "jurisdiction": "RO",
                   "document_ref": "000000000000000000000000"}
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics", json=payload, timeout=20)
        assert r.status_code == 400

    def test_valid_document_ref_creates_snapshot(self, client_session, created_diag_ids):
        # Fetch a document via picker
        rp = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/documents-picker")
        docs = rp.json().get("documents", [])
        if not docs:
            pytest.skip("no documents available for picker test")
        doc = docs[0]
        r = _make_diag(client_session, doc_ref=doc["id"])
        assert r.status_code == 200, r.text
        d = r.json()["diagnostic"]
        created_diag_ids.append(d["id"])
        snap = d.get("document_snapshot")
        assert snap and snap.get("id") == doc["id"]
        assert "title" in snap and "category" in snap and "filename" in snap and "uploaded_at" in snap


# --- Building neighbours / search / attach / verify -------------------------
class TestBuildingAxis:
    def test_neighbours(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/building-neighbours")
        assert r.status_code == 200
        data = r.json()
        assert "neighbours" in data
        assert "shared_context_verified" in data
        # Property itself not in neighbours
        for n in data["neighbours"]:
            assert n["id"] != PROP_ID

    def test_search_short_query_empty(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/search?q=x")
        assert r.status_code == 200
        assert r.json()["buildings"] == []

    def test_search_returns_units_registered(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/search?q=Skyline")
        assert r.status_code == 200
        buildings = r.json()["buildings"]
        # Skyline building might exist; validate schema when present
        for b in buildings:
            assert "id" in b and "units_registered" in b

    def test_attach_building_not_found(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/properties/{PROP_ID}/attach-building",
            json={"building_id": "000000000000000000000000"}, timeout=20)
        assert r.status_code == 404

    def test_admin_verify_building_and_context_reset(self, client_session, admin_session):
        # Fetch current building
        rc = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/building-context")
        b = rc.json().get("building")
        if not b:
            pytest.skip("no building attached")
        bid = b["id"]

        # Client cannot verify building
        rc2 = client_session.post(f"{BASE_URL}/api/admin/buildings/{bid}/verify", json={}, timeout=20)
        assert rc2.status_code == 403

        # Admin verifies
        ra = admin_session.post(f"{BASE_URL}/api/admin/buildings/{bid}/verify", json={"notes": "TEST_iter182"}, timeout=20)
        assert ra.status_code == 200, ra.text
        assert ra.json()["building"]["verification_status"] == "verified"

        # Now client updates context -> should reset to unverified
        rmod = client_session.post(
            f"{BASE_URL}/api/properties/{PROP_ID}/building-context",
            json={"context_notes": "TEST_iter182 modify"}, timeout=20)
        assert rmod.status_code == 200, rmod.text
        assert rmod.json()["building"]["verification_status"] == "unverified"


# --- PDF export -------------------------------------------------------------
class TestReadinessPDF:
    def test_pdf_download(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/transaction-readiness.pdf", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert r.content[:4] == b"%PDF"
        assert len(r.content) > 1024


# --- Regression -------------------------------------------------------------
class TestRegression:
    def test_technical_record_still_works(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/technical-record")
        assert r.status_code == 200
        data = r.json()
        for k in ["property_core", "regulatory_diagnostics", "transaction_readiness", "header", "viewer"]:
            assert k in data

    def test_transaction_readiness_json_10_criteria(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/transaction-readiness")
        assert r.status_code == 200
        data = r.json()
        assert len(data["criteria"]) == 10
        assert "overall_status" in data
        assert "disclaimer" in data
