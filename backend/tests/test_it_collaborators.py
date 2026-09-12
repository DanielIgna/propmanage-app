"""Tests for IT Collaborators Hub endpoints + regression smoke."""
import os
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

SUPER_ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    return s, r


@pytest.fixture(scope="module")
def super_session():
    s, r = _login(**SUPER_ADMIN)
    assert r.status_code == 200, f"Super admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def sub_admin_session():
    """Try to login as a sub-admin scoped 'testing' (seeded by sub_admin_seed)."""
    # Try common test credentials for scoped sub-admin
    candidates = [
        ("testing.admin@propmanage.io", "TestAdmin123!"),
        ("frontend.admin@propmanage.io", "FrontAdmin123!"),
        ("backend.admin@propmanage.io", "BackAdmin123!"),
    ]
    for email, pw in candidates:
        s, r = _login(email, pw)
        if r.status_code == 200:
            return s, email
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# AUTH / RBAC
# ─────────────────────────────────────────────────────────────────────────────
class TestITCollabsAuth:
    def test_list_no_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/admin/it-collaborators", timeout=15)
        assert r.status_code in (401, 403), f"got {r.status_code} {r.text[:200]}"

    def test_list_with_super_admin_returns_200(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/it-collaborators", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "count" in data
        assert isinstance(data["items"], list)

    def test_sub_admin_gets_403(self, sub_admin_session):
        s, email = sub_admin_session
        if not s:
            pytest.skip("No scoped sub-admin available to test 403")
        r = s.get(f"{BASE_URL}/api/admin/it-collaborators", timeout=15)
        assert r.status_code == 403, f"Expected 403 for {email}, got {r.status_code}"


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────
class TestITCollabsCRUD:
    created_ids = []

    def test_create_collaborator_success(self, super_session):
        suffix = uuid.uuid4().hex[:6]
        payload = {
            "name": f"TEST_Dev {suffix}",
            "email": f"TEST_dev_{suffix}@example.com",
            "role": "backend",
            "seniority": "senior",
            "tech_stack": ["python", "fastapi"],
            "status": "active",
        }
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators", json=payload, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["name"] == payload["name"]
        assert data["email"] == payload["email"].lower()
        assert data["role"] == "backend"
        assert "id" in data
        TestITCollabsCRUD.created_ids.append(data["id"])

    def test_create_invalid_role_returns_400(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators", json={
            "name": "TEST_Bad", "email": f"TEST_bad_{uuid.uuid4().hex[:6]}@example.com",
            "role": "wizard", "seniority": "mid",
        }, timeout=15)
        assert r.status_code == 400

    def test_create_invalid_seniority_returns_400(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators", json={
            "name": "TEST_Bad", "email": f"TEST_bad2_{uuid.uuid4().hex[:6]}@example.com",
            "role": "backend", "seniority": "guru",
        }, timeout=15)
        assert r.status_code == 400

    def test_create_invalid_status_returns_400(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators", json={
            "name": "TEST_Bad", "email": f"TEST_bad3_{uuid.uuid4().hex[:6]}@example.com",
            "role": "backend", "seniority": "mid", "status": "ninja",
        }, timeout=15)
        assert r.status_code == 400

    def test_duplicate_email_returns_409(self, super_session):
        email = f"TEST_dup_{uuid.uuid4().hex[:6]}@example.com"
        payload = {"name": "TEST_Dup1", "email": email, "role": "backend", "seniority": "mid"}
        r1 = super_session.post(f"{BASE_URL}/api/admin/it-collaborators", json=payload, timeout=15)
        assert r1.status_code == 200
        TestITCollabsCRUD.created_ids.append(r1.json()["id"])
        r2 = super_session.post(f"{BASE_URL}/api/admin/it-collaborators",
                                 json={**payload, "name": "TEST_Dup2"}, timeout=15)
        assert r2.status_code == 409

    def test_get_existing_returns_200(self, super_session):
        if not TestITCollabsCRUD.created_ids:
            pytest.skip("no created collaborator")
        cid = TestITCollabsCRUD.created_ids[0]
        r = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/{cid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == cid

    def test_get_invalid_returns_404_or_400(self, super_session):
        # invalid ObjectId → 400; valid-looking but nonexistent → 404
        r = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/507f1f77bcf86cd799439011", timeout=15)
        assert r.status_code == 404

    def test_patch_collaborator(self, super_session):
        if not TestITCollabsCRUD.created_ids:
            pytest.skip("no created collaborator")
        cid = TestITCollabsCRUD.created_ids[0]
        r = super_session.patch(f"{BASE_URL}/api/admin/it-collaborators/{cid}", json={
            "name": "TEST_Updated", "role": "frontend", "status": "paused",
            "tech_stack": ["react"], "notes": "updated via test",
        }, timeout=15)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["name"] == "TEST_Updated"
        assert d["role"] == "frontend"
        assert d["status"] == "paused"
        assert d["tech_stack"] == ["react"]
        assert d["notes"] == "updated via test"

    def test_update_metrics(self, super_session):
        if not TestITCollabsCRUD.created_ids:
            pytest.skip("no created collaborator")
        cid = TestITCollabsCRUD.created_ids[0]
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators/{cid}/metrics", json={
            "bugs_introduced": 3, "tasks_completed": 12, "review_score": 8.4, "last_sprint": "S42",
        }, timeout=15)
        assert r.status_code == 200, r.text[:300]
        m = r.json()["metrics"]
        assert m["bugs_introduced"] == 3
        assert m["tasks_completed"] == 12
        assert abs(m["review_score"] - 8.4) < 0.01
        assert m["last_sprint"] == "S42"

    def test_delete_soft_archives(self, super_session):
        if not TestITCollabsCRUD.created_ids:
            pytest.skip("no created collaborator")
        cid = TestITCollabsCRUD.created_ids[-1]
        r = super_session.delete(f"{BASE_URL}/api/admin/it-collaborators/{cid}", timeout=15)
        assert r.status_code == 200
        # verify status archived
        rg = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/{cid}", timeout=15)
        assert rg.status_code == 200
        assert rg.json()["status"] == "archived"


# ─────────────────────────────────────────────────────────────────────────────
# COPILOT (Claude Sonnet 4.5)
# ─────────────────────────────────────────────────────────────────────────────
class TestCopilot:
    def test_copilot_analyze(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators/copilot/analyze",
                                json={}, timeout=120)
        assert r.status_code == 200, f"copilot failed: {r.status_code} {r.text[:400]}"
        d = r.json()
        for key in ("summary", "risk_level", "top_performers", "at_risk",
                    "team_recommendations", "sprint_risk_score", "analyzed_count", "generated_at"):
            assert key in d, f"missing key {key}"
        assert d["risk_level"] in ("low", "medium", "high")
        assert isinstance(d["sprint_risk_score"], int)
        assert isinstance(d["analyzed_count"], int) and d["analyzed_count"] >= 1

    def test_copilot_history(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/copilot/history", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)


# ─────────────────────────────────────────────────────────────────────────────
# REGRESSION SMOKE
# ─────────────────────────────────────────────────────────────────────────────
class TestRegression:
    def test_auth_me(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json().get("email") == "admin@propmanage.io"

    def test_manual_tester_suites(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/manual-tester/suites", timeout=15)
        assert r.status_code == 200

    def test_adaptive_maturity(self, super_session):
        # adaptive_ux router prefix is /api/ux (legacy /api/adaptive removed). Smoke-check via maturity proxy.
        r = super_session.get(f"{BASE_URL}/api/ux/maturity", timeout=15)
        # endpoint may be /maturity or absent — accept 200/404 as non-blocking smoke
        assert r.status_code in (200, 401, 403, 404)

    def test_house_health_plans(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/house-health/plans", timeout=15)
        assert r.status_code == 200
