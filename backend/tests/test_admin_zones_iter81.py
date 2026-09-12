"""Backend tests for the new Admin Zones separation (iter 81).

Covers:
- GET  /api/admin/admin-zones             — registry (zones + 11 roles + enforcement)
- GET  /api/admin/admin-zones/me          — current admin zones
- POST /api/admin/admin-zones/assign      — valid / wrong master code / invalid role
- REGRESSION: GET /api/admin/zones        — geographic-coverage zones untouched
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

SUPER_ADMIN = {"email": "danieligna1@gmail.com", "password": "0108"}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=SUPER_ADMIN, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    yield s


# --- Registry -----------------------------------------------------------------
class TestAdminZonesRegistry:
    def test_registry_returns_zones_roles_enforcement(self, admin_session):
        r = admin_session.get(f"{API}/admin/admin-zones", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert set(data.keys()) >= {"zones", "roles", "enforcement"}
        assert set(data["zones"].keys()) == {"business", "infrastructure"}
        assert data["zones"]["business"]["label"] == "Business Administration"
        assert data["zones"]["infrastructure"]["label"] == "Infrastructure & Development"
        assert len(data["roles"]) == 11, f"expected 11 roles, got {len(data['roles'])}"
        assert data["enforcement"] == "prepared"
        # super_admin role covers both zones
        assert data["roles"]["super_admin"]["zones"] == ["business", "infrastructure"]


# --- /me ----------------------------------------------------------------------
class TestAdminZonesMe:
    def test_me_returns_both_zones_because_prepared(self, admin_session):
        r = admin_session.get(f"{API}/admin/admin-zones/me", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["enforcement"] == "prepared"
        assert set(data["zones"]) == {"business", "infrastructure"}


# --- /assign ------------------------------------------------------------------
class TestAdminZonesAssign:
    TARGET_EMAIL = "testing.admin@propmanage.io"

    def test_assign_valid(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/admin-zones/assign",
            json={"email": self.TARGET_EMAIL, "zone_role": "developer", "master_code": "0108"},
            timeout=15,
        )
        # 404 is acceptable if the target user does not yet exist in this env;
        # in that case skip so we don't fail the suite for a data prerequisite.
        if r.status_code == 404:
            pytest.skip(f"Target admin {self.TARGET_EMAIL} not present in DB")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["zone_role"] == "developer"
        assert data["admin_zones"] == ["infrastructure"]
        assert data["enforcement"] == "prepared"

    def test_assign_wrong_master_code(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/admin-zones/assign",
            json={"email": self.TARGET_EMAIL, "zone_role": "developer", "master_code": "WRONG"},
            timeout=15,
        )
        assert r.status_code == 403
        assert "master" in r.json().get("detail", "").lower()

    def test_assign_invalid_zone_role(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/admin-zones/assign",
            json={"email": self.TARGET_EMAIL, "zone_role": "NOT_A_ROLE", "master_code": "0108"},
            timeout=15,
        )
        assert r.status_code == 400
        assert "necunoscut" in r.json().get("detail", "").lower()


# --- Regression: old geographic-coverage /api/admin/zones ---------------------
class TestGeographicZonesRegression:
    def test_geographic_zones_still_returned(self, admin_session):
        r = admin_session.get(f"{API}/admin/zones", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        # first entry should be a Romanian/Bucharest sector
        first = data[0]
        assert first.get("country") == "România"
        assert first.get("city") == "București"


# --- Regression: admin overview / smoke pages still respond ------------------
class TestAdminPagesSmoke:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/admin/marketplace-partners",
            "/api/admin/demo-accounts",
            "/api/auth/me",
        ],
    )
    def test_smoke_get(self, admin_session, path):
        r = admin_session.get(f"{BASE_URL}{path}", timeout=15)
        # 200 or 204 acceptable; 404 means route doesn't exist which we flag
        assert r.status_code in (200, 204), f"{path} → {r.status_code}: {r.text[:200]}"
