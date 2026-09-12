"""Phase F: Digital Twin 2D Plans (PDF) — backend API tests.
Tests upload/list/serve/patch/delete + permissions + path-traversal validation.
"""
import os
import io
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

# Minimal valid PDF (1 blank page, ~300 bytes)
MINIMAL_PDF = (
    b"%PDF-1.1\n%\xc7\xec\x8f\xa2\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Resources<<>>/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 8>>stream\nBT ET\nendstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000018 00000 n \n0000000060 00000 n \n"
    b"0000000108 00000 n \n0000000182 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n232\n%%EOF\n"
)


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def specialist_session():
    return _login("specialist@propmanage.io", "Spec123!")


@pytest.fixture(scope="module")
def project_id(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_PhaseF_Plans",
        "description": "Phase F test project",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    # Teardown
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture
def uploaded_plan(admin_session, project_id):
    files = {"file": ("test.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    r = admin_session.post(
        f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
        params={"title": "TEST Plan Floor", "description": "demo", "plan_type": "floorplan"},
        files=files, timeout=20,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    yield data
    admin_session.delete(f"{BASE_URL}/api/digital-twin/plans/{data['id']}")


# --------- Upload ----------
class TestUpload:
    def test_upload_pdf_success(self, admin_session, project_id):
        files = {"file": ("plan.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
            params={"title": "TEST Upload A", "plan_type": "section"},
            files=files, timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["title"] == "TEST Upload A"
        assert d["plan_type"] == "section"
        assert d["filename"] == "plan.pdf"
        assert d["url"].startswith(f"/api/digital-twin/plans/{project_id}/")
        assert d["size_bytes"] == len(MINIMAL_PDF)
        assert "_id" not in d
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/digital-twin/plans/{d['id']}")

    def test_upload_rejects_non_pdf(self, admin_session, project_id):
        files = {"file": ("plan.txt", io.BytesIO(b"hello"), "text/plain")}
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
            params={"title": "TEST Bad Ext"},
            files=files, timeout=15,
        )
        assert r.status_code == 400

    def test_upload_increments_plan_count(self, admin_session, project_id, uploaded_plan):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}", timeout=10)
        assert r.status_code == 200
        assert r.json().get("plan_count", 0) >= 1


# --------- List ----------
class TestList:
    def test_list_plans(self, admin_session, project_id, uploaded_plan):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        ids = [p["id"] for p in data["items"]]
        assert uploaded_plan["id"] in ids

    def test_list_filter_by_type(self, admin_session, project_id, uploaded_plan):
        r = admin_session.get(
            f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
            params={"plan_type": "floorplan"}, timeout=10,
        )
        assert r.status_code == 200
        for p in r.json()["items"]:
            assert p["plan_type"] == "floorplan"

    def test_list_filter_no_match(self, admin_session, project_id, uploaded_plan):
        r = admin_session.get(
            f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
            params={"plan_type": "elevation"}, timeout=10,
        )
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()["items"]]
        assert uploaded_plan["id"] not in ids


# --------- Serve file ----------
class TestServe:
    def test_serve_pdf_auth(self, admin_session, project_id, uploaded_plan):
        url = f"{BASE_URL}{uploaded_plan['url']}"
        r = admin_session.get(url, timeout=15)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_serve_pdf_unauth(self, project_id, uploaded_plan):
        url = f"{BASE_URL}{uploaded_plan['url']}"
        r = requests.get(url, timeout=10)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_path_traversal_blocked(self, admin_session, project_id, uploaded_plan):
        # Use raw path to bypass requests' normalization
        url = f"{BASE_URL}/api/digital-twin/plans/{project_id}/..%2Fsomething"
        r = admin_session.get(url, timeout=10)
        # filename validation rejects ".." prefix => 400, or 404 if file doesn't exist
        assert r.status_code in (400, 404)

    def test_serve_nonexistent(self, admin_session, project_id):
        url = f"{BASE_URL}/api/digital-twin/plans/{project_id}/nonexistent12345.pdf"
        r = admin_session.get(url, timeout=10)
        assert r.status_code == 404


# --------- Patch ----------
class TestPatch:
    def test_patch_metadata(self, admin_session, uploaded_plan):
        pid = uploaded_plan["id"]
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/plans/{pid}",
            json={"title": "TEST Updated Title", "plan_type": "elevation"}, timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "TEST Updated Title"
        assert r.json()["plan_type"] == "elevation"


# --------- Delete ----------
class TestDelete:
    def test_delete_plan(self, admin_session, project_id):
        files = {"file": ("del.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
            params={"title": "TEST Delete Me"}, files=files, timeout=15,
        )
        assert r.status_code == 200
        plan = r.json()
        pre = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}", timeout=10).json()
        pre_count = pre.get("plan_count", 0)

        r = admin_session.delete(f"{BASE_URL}/api/digital-twin/plans/{plan['id']}", timeout=10)
        assert r.status_code == 200

        # File should be gone
        rr = admin_session.get(f"{BASE_URL}{plan['url']}", timeout=10)
        assert rr.status_code == 404

        post = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}", timeout=10).json()
        assert post.get("plan_count", 0) == max(0, pre_count - 1)


# --------- Permissions ----------
class TestPermissions:
    def test_client_no_dt_pro_403(self, client_session, project_id):
        # Client doesn't have digital_twin_pro flag; list should 403
        r = client_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans", timeout=10)
        assert r.status_code == 403

        files = {"file": ("c.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
        r2 = client_session.post(
            f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
            params={"title": "TEST Client"}, files=files, timeout=15,
        )
        assert r2.status_code == 403

    def test_non_member_specialist(self, specialist_session, project_id):
        # Specialist has no DT Pro by default; should get 403 (DT gate or project gate)
        r = specialist_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans", timeout=10)
        assert r.status_code == 403


# --------- Admin stats ----------
class TestAdminStats:
    def test_admin_stats_has_plans(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/digital-twin/stats", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "plans" in d
        assert isinstance(d["plans"], int)
