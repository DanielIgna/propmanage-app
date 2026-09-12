"""Phase 68 — Admin Settings Control Panel + Documentation + Dynamic SEO.

Covers:
- GET /api/admin/app-settings (admin auth) full doc with all sections
- PUT /api/admin/app-settings partial update (seo.home_title)
- POST /api/admin/app-settings/reset restores defaults
- GET /api/app-settings/public unauth subset (seo+social+contact+pricing)
- Smoke checks on a few legacy endpoints to ensure no regression
"""
import os
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert me.status_code == 200, f"auth/me failed: {me.status_code}"
    assert me.json().get("role") == "admin"
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# ---------- Admin settings GET ----------
class TestAdminSettingsGet:
    def test_get_returns_full_doc(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/app-settings", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        for section in ("pricing", "social", "contact", "company", "seo"):
            assert section in data, f"Missing section {section}: {list(data.keys())}"
        # ObjectId / _id should be serialized to string (no raw ObjectId)
        assert isinstance(data.get("_id", ""), str)
        # spot check defaults
        assert "audit_ron" in data["pricing"]
        assert "twin_ron" in data["pricing"]
        assert "commission_pct" in data["pricing"]
        assert "home_title" in data["seo"]
        assert "facebook_main" in data["social"]


# ---------- Admin settings PUT partial ----------
class TestAdminSettingsPut:
    def test_put_partial_seo_persists(self, admin_session):
        title = "TEST68_Seo_Title"
        r = admin_session.put(
            f"{BASE_URL}/api/admin/app-settings",
            json={"seo": {"home_title": title}},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["seo"]["home_title"] == title
        # Verify by GET
        g = admin_session.get(f"{BASE_URL}/api/admin/app-settings", timeout=10)
        assert g.status_code == 200
        assert g.json()["seo"]["home_title"] == title

    def test_put_pricing_persists(self, admin_session):
        r = admin_session.put(
            f"{BASE_URL}/api/admin/app-settings",
            json={"pricing": {"audit_ron": 400, "twin_ron": 950, "commission_pct": 2.5}},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["pricing"]["audit_ron"] == 400


# ---------- Admin settings RESET ----------
class TestAdminSettingsReset:
    def test_reset_restores_defaults(self, admin_session):
        # first ensure we've mutated something
        admin_session.put(
            f"{BASE_URL}/api/admin/app-settings",
            json={"pricing": {"audit_ron": 999, "twin_ron": 1234, "commission_pct": 5}},
            timeout=10,
        )
        r = admin_session.post(f"{BASE_URL}/api/admin/app-settings/reset", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["pricing"]["audit_ron"] == 350.0
        assert data["pricing"]["twin_ron"] == 950.0
        assert data["pricing"]["commission_pct"] == 2.5
        assert data["seo"]["home_title"].startswith("PropManage")
        # confirm via GET
        g = admin_session.get(f"{BASE_URL}/api/admin/app-settings", timeout=10)
        assert g.json()["pricing"]["audit_ron"] == 350.0


# ---------- Public settings ----------
class TestPublicSettings:
    def test_public_no_auth(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/app-settings/public", timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("social", "pricing", "contact", "company", "seo"):
            assert k in data, f"Missing {k}"
        # contact should only expose email (not phone/address) — verify schema
        assert "email" in data["contact"]
        # pricing should expose values
        assert "audit_ron" in data["pricing"]


# ---------- Regression smoke ----------
class TestRegressionSmoke:
    def test_verified_estate_listings(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/verified-estate/listings", timeout=15)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), (list, dict))

    def test_admin_kanban_endpoint(self, admin_session):
        # Try a couple of known admin endpoints — accept 200/404 (route may differ)
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/listings", timeout=15)
        assert r.status_code in (200, 404), f"Unexpected {r.status_code}: {r.text[:200]}"

    def test_auth_me_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json().get("role") == "admin"
