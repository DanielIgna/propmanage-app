"""Backend tests — PropManage TASK 1: Subscription/Entitlement Gate.

Auth uses httpOnly cookies -> use requests.Session per user.
"""
from __future__ import annotations

import os
import time

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} -> {r.status_code} {r.text}"
    return s


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def client_sess() -> requests.Session:
    return _login(CLIENT_EMAIL, CLIENT_PASSWORD)


@pytest.fixture(scope="session")
def admin_sess() -> requests.Session:
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="session")
def free_sess():
    """Fresh FREE client (no subscription). Best-effort cleanup at teardown."""
    unique = int(time.time() * 1000)
    email = f"free{unique}@example.com"
    password = "Free1234!"
    s = requests.Session()
    r = s.post(
        f"{API}/auth/register",
        json={
            "email": email,
            "password": password,
            "name": "Free Test User",
            "role": "client",
            "terms_accepted": True,
            "privacy_policy_accepted": True,
        },
        timeout=30,
    )
    assert r.status_code == 200, f"register free -> {r.status_code} {r.text}"
    yield {"email": email, "session": s}
    # Cleanup — try admin delete endpoint
    try:
        me = s.get(f"{API}/auth/me", timeout=10).json()
        uid = me.get("id") or me.get("_id")
        admin_s = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
        for url in (f"{API}/admin/users/{uid}", f"{API}/admin/accounts/{uid}"):
            try:
                admin_s.delete(url, timeout=10)
            except Exception:
                pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# /api/me/entitlements
# ---------------------------------------------------------------------------
class TestMeEntitlements:
    def test_client_premium(self, client_sess):
        r = client_sess.get(f"{API}/me/entitlements", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["tier"] == "CLIENT_PREMIUM", data
        assert data["is_admin_bypass"] is False
        feats = set(data["features"])
        assert {
            "property_create",
            "property_technical_record",
            "house_health_basic",
            "house_health_advanced",
            "digital_twin_advanced",
        } <= feats, feats
        assert data.get("subscription") and data["subscription"]["plan"] == "premium"

    def test_admin_bypass(self, admin_sess):
        r = admin_sess.get(f"{API}/me/entitlements", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_admin_bypass"] is True
        assert data["tier"] == "CLIENT_PREMIUM"
        feats = set(data["features"])
        assert {
            "property_create", "property_technical_record",
            "house_health_basic", "house_health_advanced", "digital_twin_advanced",
        } <= feats

    def test_free_user(self, free_sess):
        r = free_sess["session"].get(f"{API}/me/entitlements", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["tier"] == "FREE", data
        assert data["is_admin_bypass"] is False
        assert data["subscription"] is None
        feats = set(data["features"])
        assert feats == {"property_create", "property_technical_record"}, feats


# ---------------------------------------------------------------------------
# House Health gate
# ---------------------------------------------------------------------------
class TestHouseHealthGate:
    def test_dashboard_free_no_twin(self, free_sess):
        r = free_sess["session"].get(f"{API}/house-health/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        if data.get("enabled") is False:
            pytest.skip("House Health feature disabled")
        assert data.get("locked") is True
        # FREE user has no twin — order preserved: no_twin comes first
        assert data.get("lock_reason") == "no_twin", data

    def test_dashboard_client_premium_not_locked_by_sub(self, client_sess):
        r = client_sess.get(f"{API}/house-health/dashboard", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        if data.get("enabled") is False:
            pytest.skip("HH disabled")
        if data.get("locked"):
            assert data.get("lock_reason") != "no_subscription", data

    def test_documents_post_free_402(self, free_sess):
        r = free_sess["session"].post(
            f"{API}/house-health/documents",
            data={
                "twin_project_id": "nonexistent",
                "category": "cadastru",
                "external_link": "https://example.com/x",
                "external_type": "custom",
            },
            timeout=15,
        )
        assert r.status_code == 402, f"expected 402 got {r.status_code}: {r.text}"
        body = r.json()
        detail = body.get("detail") or body
        assert detail.get("error") == "entitlement_required"
        assert detail.get("feature") == "house_health_basic"
        assert detail.get("current_tier") == "FREE"

    def test_documents_post_premium_not_402(self, client_sess):
        r = client_sess.post(
            f"{API}/house-health/documents",
            data={
                "twin_project_id": "nonexistent-twin-id",
                "category": "cadastru",
                "external_link": "https://example.com/x",
                "external_type": "custom",
            },
            timeout=15,
        )
        assert r.status_code != 402, f"premium got 402: {r.text}"

    def test_eligibility_regression(self, client_sess):
        r = client_sess.get(f"{API}/house-health/eligibility", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "enabled" in data and "has_subscription" in data

    def test_documents_list_regression(self, client_sess):
        r = client_sess.get(
            f"{API}/house-health/documents",
            params={"twin_project_id": "any"},
            timeout=15,
        )
        assert r.status_code != 402, r.text


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
class TestAdminEntitlements:
    def test_catalog_admin(self, admin_sess):
        r = admin_sess.get(f"{API}/admin/entitlements/catalog", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tiers" in data and "features" in data
        tier_ids = [t["id"] for t in data["tiers"]]
        assert tier_ids == ["FREE", "CLIENT_BASIC", "CLIENT_PRO", "CLIENT_PREMIUM"]

    def test_catalog_client_forbidden(self, client_sess):
        r = client_sess.get(f"{API}/admin/entitlements/catalog", timeout=15)
        assert r.status_code == 403, r.text

    def test_admin_lookup_valid(self, admin_sess, client_sess):
        me = client_sess.get(f"{API}/auth/me", timeout=10).json()
        uid = me.get("id") or me.get("_id")
        assert uid, me
        r = admin_sess.get(f"{API}/admin/users/{uid}/entitlements", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("user_email") == CLIENT_EMAIL
        assert data["tier"] == "CLIENT_PREMIUM"
        assert "user_name" in data

    def test_admin_lookup_forbidden_for_client(self, client_sess):
        r = client_sess.get(
            f"{API}/admin/users/{'a' * 24}/entitlements",
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_admin_lookup_not_found(self, admin_sess):
        r = admin_sess.get(
            f"{API}/admin/users/{'a' * 24}/entitlements",
            timeout=15,
        )
        assert r.status_code == 404, r.text
