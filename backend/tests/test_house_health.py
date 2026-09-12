"""House Health backend tests — F1 + F2 + F3.

Validates the end-to-end lifecycle:
 - eligibility & dashboard
 - equipment catalog
 - documents (local + external + ownership)
 - specialist evaluations (create + upload + submit)
 - admin approve/reject + audit
 - history merge + per-role evaluations listing
"""
import io
import os

import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
TWIN_ID = "2d0a899472b34e32a8eaf79b88d7c012"

CRED = {
    "client": {"email": "client@propmanage.io", "password": "Client123!"},
    "admin": {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD},
    "specialist": {"email": "specialist@propmanage.io", "password": "Spec123!"},
    "specialist2": {"email": "specialist2@propmanage.io", "password": "Spec123!"},
}


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    token = data.get("token") or data.get("access_token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(**CRED["client"])


@pytest.fixture(scope="module")
def admin_sess():
    return _login(**CRED["admin"])


@pytest.fixture(scope="module")
def specialist_sess():
    return _login(**CRED["specialist"])


@pytest.fixture(scope="module")
def specialist2_sess():
    try:
        return _login(**CRED["specialist2"])
    except AssertionError:
        return None


# ------------------ F1: eligibility, dashboard ------------------
class TestF1Eligibility:
    def test_eligibility_for_client(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/eligibility")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["enabled"] is True
        assert d["has_twin"] is True
        assert d["has_subscription"] is True
        assert d["twin"]["id"] == TWIN_ID

    def test_dashboard_not_locked(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/dashboard")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["enabled"] is True
        assert d.get("locked") is False
        assert d.get("twin", {}).get("id") == TWIN_ID
        assert d.get("subscription") is not None

    def test_equipment_catalog(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/equipment-catalog")
        assert r.status_code == 200
        d = r.json()
        for k in ("air", "thermal", "humidity", "electric", "radon"):
            assert k in d["equipment"], f"missing kind {k}"
        assert "kinds" in d and len(d["kinds"]) == 5


# ------------------ F2: documents ------------------
class TestF2Documents:
    created_local_id = None
    created_link_id = None

    def test_upload_local_doc(self, client_sess):
        files = {"file": ("test_doc.txt", io.BytesIO(b"hello world"), "text/plain")}
        data = {
            "twin_project_id": TWIN_ID,
            "category": "manuale",
            "description": "TEST_local_doc",
            "doc_date": "2026-01-15",
        }
        r = client_sess.post(f"{BASE_URL}/api/house-health/documents", data=data, files=files)
        assert r.status_code == 200, r.text
        doc = r.json()["document"]
        assert doc["storage"] == "local"
        assert doc["file_url"].startswith("/api/house-health/documents/")
        TestF2Documents.created_local_id = doc["id"]

    def test_reject_invalid_category(self, client_sess):
        data = {"twin_project_id": TWIN_ID, "category": "NOT_VALID", "external_link": "https://x", "external_type": "custom"}
        r = client_sess.post(f"{BASE_URL}/api/house-health/documents", data=data)
        assert r.status_code == 400

    def test_upload_external_link(self, client_sess):
        data = {
            "twin_project_id": TWIN_ID,
            "category": "cadastru",
            "description": "TEST_link",
            "external_link": "https://drive.google.com/abc",
            "external_type": "google_drive",
        }
        r = client_sess.post(f"{BASE_URL}/api/house-health/documents", data=data)
        assert r.status_code == 200, r.text
        doc = r.json()["document"]
        assert doc["storage"] == "external"
        assert doc["external_type"] == "google_drive"
        TestF2Documents.created_link_id = doc["id"]

    def test_reject_both_file_and_link(self, client_sess):
        files = {"file": ("a.txt", io.BytesIO(b"x"), "text/plain")}
        data = {
            "twin_project_id": TWIN_ID, "category": "cadastru",
            "external_link": "https://drive.google.com/abc", "external_type": "google_drive",
        }
        r = client_sess.post(f"{BASE_URL}/api/house-health/documents", data=data, files=files)
        assert r.status_code == 400

    def test_reject_neither(self, client_sess):
        data = {"twin_project_id": TWIN_ID, "category": "cadastru"}
        r = client_sess.post(f"{BASE_URL}/api/house-health/documents", data=data)
        assert r.status_code == 400

    def test_list_docs_owner(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/documents", params={"twin_project_id": TWIN_ID})
        assert r.status_code == 200
        items = r.json()["items"]
        ids = [d["id"] for d in items]
        assert TestF2Documents.created_local_id in ids
        assert TestF2Documents.created_link_id in ids

    def test_list_docs_403_for_non_owner(self, specialist_sess):
        r = specialist_sess.get(f"{BASE_URL}/api/house-health/documents", params={"twin_project_id": TWIN_ID})
        assert r.status_code == 403

    def test_delete_doc_404_for_non_owner(self, specialist_sess):
        r = specialist_sess.delete(f"{BASE_URL}/api/house-health/documents/{TestF2Documents.created_local_id}")
        assert r.status_code == 404

    def test_delete_docs_owner(self, client_sess):
        for did in [TestF2Documents.created_local_id, TestF2Documents.created_link_id]:
            r = client_sess.delete(f"{BASE_URL}/api/house-health/documents/{did}")
            assert r.status_code == 200, r.text


# ------------------ F3: evaluations lifecycle ------------------
class TestF3Evaluations:
    eval_id = None

    def test_client_cannot_create_evaluation(self, client_sess):
        r = client_sess.post(
            f"{BASE_URL}/api/house-health/evaluations",
            json={"twin_project_id": TWIN_ID, "kind": "air"},
        )
        assert r.status_code == 403

    def test_specialist_create_eval(self, specialist_sess):
        r = specialist_sess.post(
            f"{BASE_URL}/api/house-health/evaluations",
            json={
                "twin_project_id": TWIN_ID,
                "kind": "thermal",
                "observations": "TEST_obs",
                "equipment": ["Testo 860i"],
            },
        )
        assert r.status_code == 200, r.text
        e = r.json()["evaluation"]
        assert e["status"] == "draft"
        assert e["kind"] == "thermal"
        TestF3Evaluations.eval_id = e["id"]

    def test_specialist_upload_attachment(self, specialist_sess):
        eid = TestF3Evaluations.eval_id
        files = {"file": ("therm.txt", io.BytesIO(b"thermal data"), "text/plain")}
        r = specialist_sess.post(f"{BASE_URL}/api/house-health/evaluations/{eid}/upload", files=files)
        assert r.status_code == 200, r.text
        att = r.json()["attachment"]
        assert att["filename"] == "therm.txt"
        assert "url" in att

    def test_submit_eval(self, specialist_sess):
        eid = TestF3Evaluations.eval_id
        r = specialist_sess.post(f"{BASE_URL}/api/house-health/evaluations/{eid}/submit")
        assert r.status_code == 200
        assert r.json()["status"] == "pending_approval"

    def test_non_admin_cannot_approve(self, specialist_sess):
        eid = TestF3Evaluations.eval_id
        r = specialist_sess.post(
            f"{BASE_URL}/api/admin/house-health/evaluations/{eid}/approve",
            json={"note": "x"},
        )
        assert r.status_code in (401, 403)

    def test_admin_approve(self, admin_sess):
        eid = TestF3Evaluations.eval_id
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/house-health/evaluations/{eid}/approve",
            json={"note": "TEST_approval"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"

    def test_create_and_reject_eval(self, specialist_sess, admin_sess):
        # create another draft and reject
        r = specialist_sess.post(
            f"{BASE_URL}/api/house-health/evaluations",
            json={"twin_project_id": TWIN_ID, "kind": "electric"},
        )
        assert r.status_code == 200
        eid = r.json()["evaluation"]["id"]
        specialist_sess.post(f"{BASE_URL}/api/house-health/evaluations/{eid}/submit")
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/house-health/evaluations/{eid}/reject",
            json={"note": "TEST_reject_reason"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    def test_history_includes_approved(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/history/{TWIN_ID}")
        assert r.status_code == 200
        items = r.json()["items"]
        kinds = [i.get("kind") for i in items]
        assert "evaluation" in kinds  # at least one approved evaluation in history
        # find the one we just approved
        thermal_present = any(
            i.get("evaluation_kind") == "thermal" and i.get("id") == TestF3Evaluations.eval_id
            for i in items
        )
        assert thermal_present, f"approved thermal eval not in history: {items}"

    def test_list_evals_client_requires_twin(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/evaluations")
        assert r.status_code == 400

    def test_list_evals_client_owner(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/house-health/evaluations", params={"twin_project_id": TWIN_ID})
        assert r.status_code == 200
        items = r.json()["items"]
        # All items must belong to this twin
        for e in items:
            assert e["twin_project_id"] == TWIN_ID

    def test_list_evals_specialist_only_own(self, specialist_sess):
        r = specialist_sess.get(f"{BASE_URL}/api/house-health/evaluations")
        assert r.status_code == 200
        items = r.json()["items"]
        # All items must be owned by this specialist (cannot easily get id, so just ensure no foreign specialist emails)
        # Acceptable: all share same specialist_email
        if items:
            emails = {e.get("specialist_email") for e in items}
            assert emails == {CRED["specialist"]["email"]}, f"foreign specialists leaked: {emails}"

    def test_list_evals_admin_sees_all(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/house-health/evaluations")
        assert r.status_code == 200
        # admin endpoint returns up to 100 items, no specialist filter
        data = r.json()
        assert "items" in data
