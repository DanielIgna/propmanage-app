"""
Task 5 backend regression tests (iter187).
Ensures Task 1-4 infrastructure remains intact:
- /api/me/entitlements (tier + lifecycle + notice)
- /api/me/subscription/cancel behavior
- 402 on gated mutations for FREE users (POST /api/digital-twin/projects, /api/house-health/checkout-session)
- Admin bypass
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


def _register_free():
    """Create a fresh FREE user (no subscription)."""
    email = f"nudge{int(time.time())}{uuid.uuid4().hex[:6]}@example.com"
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "email": email,
            "password": "TestPass123!",
            "name": "Nudge Tester",
            "role": "client",
            "terms_accepted": True,
            "privacy_policy_accepted": True,
        },
        timeout=15,
    )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text[:200]}"
    return s, email


# ---------- Entitlements contract ----------
class TestEntitlementsContract:
    def test_free_user_entitlements(self):
        s, _ = _register_free()
        r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "tier" in data
        assert "lifecycle" in data
        assert "notice" in data
        assert data["tier"] in ("FREE", "CLIENT_FREE")
        # FREE user (never subscribed) should have no notice
        assert data["notice"] in (None, {}, "null") or data["notice"] is None
        assert data["lifecycle"] in ("never_subscribed", "expired", None)

    def test_client_premium_entitlements(self):
        s = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
        r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["tier"] != "FREE"
        # Client demo has premium; lifecycle should be active or admin_bypass or similar
        assert data["lifecycle"] in ("active", "admin_bypass", "cancelled_grace")

    def test_admin_entitlements_bypass(self):
        s = _login(ADMIN_EMAIL, ADMIN_PASSWORD)
        r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["lifecycle"] == "admin_bypass" or data["tier"] in ("ADMIN", "PREMIUM", "CLIENT_PREMIUM")


# ---------- 402 on gated mutations for FREE users ----------
class TestFreeUserGated402:
    def test_free_user_dt_project_post_returns_402(self):
        s, _ = _register_free()
        payload = {"name": "Test Project", "description": "regression"}
        r = s.post(f"{BASE_URL}/api/digital-twin/projects", json=payload, timeout=15)
        assert r.status_code == 402, f"Expected 402, got {r.status_code}: {r.text[:200]}"
        body = r.json()
        detail = body.get("detail") or {}
        # detail may be dict or string; if dict, verify feature field
        if isinstance(detail, dict):
            feature = detail.get("feature") or detail.get("required_feature")
            assert feature, f"402 must expose 'feature' or 'required_feature'; got detail={detail}"

    def test_free_user_house_health_checkout_returns_2xx_or_402(self):
        """Checkout session endpoint: FREE user without DT can hit it; should either
        create session (2xx) or return 402/400 gracefully — never 500."""
        s, _ = _register_free()
        r = s.post(f"{BASE_URL}/api/house-health/checkout-session", json={}, timeout=15)
        # We tolerate 400/402/404/200 depending on prerequisites, but never 500
        assert r.status_code != 500, f"Server error on checkout-session: {r.text[:200]}"


# ---------- Subscription cancel endpoint idempotent behaviour ----------
class TestCancelIdempotent:
    def test_cancel_no_sub_returns_404(self):
        s, _ = _register_free()
        r = s.post(f"{BASE_URL}/api/me/subscription/cancel", timeout=15)
        assert r.status_code in (404, 400), f"Expected 404/400 for FREE cancel, got {r.status_code}: {r.text[:200]}"


# ---------- Client-facing regressions ----------
class TestClientRegressions:
    def test_client_get_house_health_dashboard(self):
        s = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
        r = s.get(f"{BASE_URL}/api/house-health/dashboard", timeout=15)
        assert r.status_code == 200, r.text[:200]

    def test_client_can_post_dt_project(self):
        """PREMIUM client should NOT get 402 for POST digital-twin/projects."""
        s = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
        # Use unique name to avoid conflicts
        payload = {"name": f"Regression DT {uuid.uuid4().hex[:6]}", "description": "regression"}
        r = s.post(f"{BASE_URL}/api/digital-twin/projects", json=payload, timeout=20)
        assert r.status_code != 402, f"Premium client got 402 unexpectedly: {r.text[:200]}"
        assert r.status_code in (200, 201, 400, 409, 422), f"Unexpected status {r.status_code}: {r.text[:200]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
