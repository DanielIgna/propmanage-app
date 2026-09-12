"""Backend tests for Property Technical Record v1 (iter 181).

Tests vocabulary, building context, diagnostics, transaction readiness aggregation
and verifies existing flows remain intact.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
PROP_ID = "6a11d70e600be19667009c93"  # Skyline Loft A4 (fixed test property)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------
class TestVocabulary:
    def test_vocabulary_categories(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/technical-record/vocabulary")
        assert r.status_code == 200
        data = r.json()
        for key in ["diagnostic_types", "jurisdictions", "building_types",
                    "verification_levels", "source_types"]:
            assert key in data, f"missing {key}"
            assert isinstance(data[key], list) and len(data[key]) > 0
            assert "id" in data[key][0] and "label" in data[key][0]

        jur_ids = {x["id"] for x in data["jurisdictions"]}
        assert {"FR", "RO", "EU", "OTHER"} <= jur_ids


# ---------------------------------------------------------------------------
# Technical Record aggregation
# ---------------------------------------------------------------------------
class TestTechnicalRecord:
    def test_technical_record_structure(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/technical-record")
        assert r.status_code == 200, r.text
        d = r.json()
        # Core
        assert d["property_id"] == PROP_ID
        pc = d["property_core"]
        assert "identity" in pc and "stats" in pc and "digital_twin" in pc
        # Building context can be dict or None
        assert "building_context" in d
        # Regulatory diagnostics
        rd = d["regulatory_diagnostics"]
        assert "items" in rd and "total" in rd and "by_jurisdiction" in rd
        # Transaction readiness
        tr = d["transaction_readiness"]
        assert "overall_status" in tr and "criteria" in tr
        assert tr["overall_status"] in {"COMPLETE", "PARTIAL", "MISSING", "NOT_VERIFIED"}
        # Header
        h = d["header"]
        for k in ["property_name", "property_address", "documents_count",
                  "documents_verified", "last_updated", "overall_status"]:
            assert k in h
        # Endpoints
        assert "endpoints" in d and "diagnostics" in d["endpoints"]


# ---------------------------------------------------------------------------
# Building Context
# ---------------------------------------------------------------------------
class TestBuildingContext:
    def test_get_building_context(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/building-context")
        assert r.status_code == 200
        d = r.json()
        assert "building" in d and "attached" in d

    def test_post_building_context_upsert_unverified(self, client_session):
        payload = {
            "construction_year": 1985,
            "building_type": "block",
            "number_of_units": 24,
            "source_type": "external_reference",
            "source_name": "HartaBlocuri",
            "source_reference": "https://hartablocuri.ro/bloc/test-iter181",
            "context_notes": "TEST_iter181 context note",
        }
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/building-context", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        b = d["building"]
        assert b["verification_status"] == "unverified", \
            f"verification must be unverified, got {b['verification_status']}"
        assert b["construction_year"] == 1985
        assert b["building_type"] == "block"
        assert b["source_type"] == "external_reference"
        assert b["source_name"] == "HartaBlocuri"

    def test_patch_building_context_merge_non_destructive(self, client_session):
        # Fetch current building id
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/building-context")
        assert r.status_code == 200
        b = r.json().get("building")
        if not b:
            pytest.skip("no building attached")
        bid = b["id"]
        prior_year = b.get("construction_year")
        # Patch only number_of_units — construction_year must remain
        r2 = client_session.patch(f"{BASE_URL}/api/buildings/{bid}/context",
                                   json={"number_of_units": 42})
        assert r2.status_code == 200, r2.text
        b2 = r2.json()["building"]
        assert b2["number_of_units"] == 42
        assert b2["construction_year"] == prior_year, \
            "non-destructive merge failed: construction_year was overwritten"
        assert b2["verification_status"] == "unverified"

    def test_invalid_source_type_400(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/building-context",
                                 json={"source_type": "BAD_SOURCE"})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
class TestDiagnostics:
    def test_missing_jurisdiction_returns_422(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics",
                                 json={"diagnostic_type": "electrical"})
        # Pydantic missing required field → 422
        assert r.status_code == 422, r.text

    def test_unknown_jurisdiction_returns_400(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics",
                                 json={"diagnostic_type": "electrical", "jurisdiction": "XX"})
        assert r.status_code == 400, r.text

    def test_create_diagnostic_fr_unverified_owner_declared(self, client_session, created_diag_ids):
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics",
                                 json={"diagnostic_type": "energy_performance",
                                       "jurisdiction": "FR",
                                       "notes": "TEST_iter181 FR DPE"})
        assert r.status_code == 200, r.text
        d = r.json()["diagnostic"]
        assert d["jurisdiction"] == "FR"
        assert d["verification_status"] == "unverified"
        assert d["provenance"] == "declared"
        assert d["source"] == "owner_upload"
        created_diag_ids.append(d["id"])

    def test_create_diagnostic_ro(self, client_session, created_diag_ids):
        r = client_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics",
                                 json={"diagnostic_type": "electrical",
                                       "jurisdiction": "RO",
                                       "notes": "TEST_iter181 RO"})
        assert r.status_code == 200
        d = r.json()["diagnostic"]
        assert d["jurisdiction"] == "RO"
        assert d["verification_status"] == "unverified"
        created_diag_ids.append(d["id"])

    def test_admin_creates_documented_but_never_verified(self, admin_session, created_diag_ids):
        # Admin needs to access this specific property; if not permitted skip
        r = admin_session.post(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics",
                               json={"diagnostic_type": "asbestos",
                                     "jurisdiction": "FR",
                                     "notes": "TEST_iter181 admin doc"})
        if r.status_code == 403:
            pytest.skip("admin has no access to this property")
        assert r.status_code == 200, r.text
        d = r.json()["diagnostic"]
        assert d["provenance"] == "documented"
        assert d["verification_status"] == "unverified", \
            "diagnostic must NEVER auto-become verified"
        created_diag_ids.append(d["id"])

    def test_list_shows_created(self, client_session, created_diag_ids):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics")
        assert r.status_code == 200
        ids = {x["id"] for x in r.json()["diagnostics"]}
        for cid in created_diag_ids:
            assert cid in ids

    def test_patch_diagnostic_and_history(self, client_session, created_diag_ids):
        if not created_diag_ids:
            pytest.skip("no diag created")
        did = created_diag_ids[0]
        r = client_session.patch(f"{BASE_URL}/api/diagnostics/{did}",
                                  json={"findings": "TEST_iter181 updated findings"})
        assert r.status_code == 200
        d = r.json()["diagnostic"]
        assert d["findings"] == "TEST_iter181 updated findings"
        # history has at least 2 entries (create + edit)
        assert len(d.get("history", [])) >= 2
        events = [h.get("event") for h in d["history"]]
        assert "edit" in events

    def test_delete_soft_removes_from_list(self, client_session, created_diag_ids):
        if not created_diag_ids:
            pytest.skip("no diag")
        did = created_diag_ids[-1]
        r = client_session.delete(f"{BASE_URL}/api/diagnostics/{did}")
        assert r.status_code == 200
        # Verify no longer in list
        r2 = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/diagnostics")
        ids = {x["id"] for x in r2.json()["diagnostics"]}
        assert did not in ids


# ---------------------------------------------------------------------------
# Transaction Readiness
# ---------------------------------------------------------------------------
class TestTransactionReadiness:
    EXPECTED_CRITERIA = {
        "identity", "basic_info", "technical_documentation", "documents_available",
        "systems_documented", "intervention_history", "verification",
        "building_context", "regulatory_diagnostics", "warranties"
    }

    def test_readiness_10_criteria_no_numeric_score(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/transaction-readiness")
        assert r.status_code == 200
        d = r.json()
        assert len(d["criteria"]) == 10
        got = {c["id"] for c in d["criteria"]}
        assert got == self.EXPECTED_CRITERIA
        for c in d["criteria"]:
            assert c["status"] in {"COMPLETE", "PARTIAL", "MISSING", "NOT_VERIFIED"}
        assert d["overall_status"] in {"COMPLETE", "PARTIAL", "MISSING", "NOT_VERIFIED"}
        # No numeric score
        assert "score" not in d
        assert "disclaimer" in d

    def test_overall_is_worst_case(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties/{PROP_ID}/transaction-readiness")
        d = r.json()
        priority = {"MISSING": 3, "NOT_VERIFIED": 2, "PARTIAL": 1, "COMPLETE": 0}
        worst = max(priority[c["status"]] for c in d["criteria"])
        expected = {v: k for k, v in priority.items()}[worst]
        assert d["overall_status"] == expected


# ---------------------------------------------------------------------------
# Existing flows unaffected
# ---------------------------------------------------------------------------
class TestExistingFlowsUntouched:
    @pytest.mark.parametrize("path", [
        f"/api/properties/{PROP_ID}/dna",
        f"/api/properties/{PROP_ID}/completeness",
        f"/api/properties/{PROP_ID}/timeline",
        f"/api/properties/{PROP_ID}/documents",
        f"/api/properties/{PROP_ID}/assets",
    ])
    def test_endpoint_ok(self, client_session, path):
        r = client_session.get(f"{BASE_URL}{path}")
        assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def cleanup(client_session, created_diag_ids):
    yield
    for did in created_diag_ids:
        try:
            client_session.delete(f"{BASE_URL}/api/diagnostics/{did}")
        except Exception:
            pass
