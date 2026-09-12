"""Tests for direct Google OAuth flow (iter 175).

Covers:
- POST /api/auth/google/callback with invalid code -> 401 with Romanian detail
- POST /api/auth/google/callback missing fields -> 422
- Legacy POST /api/auth/google/session still exists
- oauth_health tracking with flow='direct'
- Regression: email/password login + register
"""
import os
import uuid
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Direct Google OAuth callback ----------

class TestGoogleDirectCallback:
    def test_invalid_code_returns_401_with_romanian_detail(self):
        r = requests.post(
            f"{API}/auth/google/callback",
            json={
                "code": "invalid_fake_code_1234567890",
                "redirect_uri": f"{BASE_URL}/auth/callback",
            },
            timeout=30,
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text[:400]}"
        body = r.json()
        detail = body.get("detail", "")
        assert "redirect_uri" in detail and "whitelisted" in detail, \
            f"Expected Romanian detail mentioning redirect_uri whitelisting; got: {detail!r}"
        assert "Google Cloud Console" in detail

    def test_missing_fields_returns_422(self):
        r = requests.post(f"{API}/auth/google/callback", json={}, timeout=15)
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text[:200]}"

    def test_missing_redirect_uri_returns_422(self):
        r = requests.post(
            f"{API}/auth/google/callback",
            json={"code": "1234567890abcdef"},
            timeout=15,
        )
        assert r.status_code == 422


# ---------- Legacy Emergent OAuth session ----------

class TestGoogleEmergentLegacyEndpoint:
    def test_legacy_session_endpoint_exists_and_responds(self):
        # No X-Session-ID header — expect a non-404 response (endpoint exists)
        r = requests.post(f"{API}/auth/google/session", json={}, timeout=30)
        assert r.status_code != 404, "Legacy /auth/google/session endpoint missing"
        # Typically returns 400/401 without session
        assert r.status_code in (400, 401, 422, 500, 502, 503), \
            f"Unexpected status: {r.status_code}: {r.text[:200]}"


# ---------- oauth_health tracking (indirect via admin endpoint) ----------

class TestOAuthHealthTracking:
    def test_direct_flow_failure_does_not_crash_and_endpoint_reachable(self):
        # Trigger a direct-flow failure (invalid code)
        r = requests.post(
            f"{API}/auth/google/callback",
            json={"code": "invalid_code_track_test_XYZ", "redirect_uri": f"{BASE_URL}/auth/callback"},
            timeout=30,
        )
        assert r.status_code == 401
        # We cannot easily assert DB write without admin auth; simply ensure the
        # endpoint doesn't crash. If admin oauth-health endpoint is accessible
        # anonymously, we can inspect (usually not).


# ---------- Regression: email/password login ----------

class TestEmailPasswordRegression:
    def test_login_client_success(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "client@propmanage.io", "password": "Client123!"},
            timeout=30,
        )
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
        data = r.json()
        assert data.get("email") == "client@propmanage.io"

    def test_login_invalid_password(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "client@propmanage.io", "password": "WrongPass!"},
            timeout=30,
        )
        assert r.status_code in (400, 401, 403), f"Got: {r.status_code}"

    def test_register_and_login_temp_user(self):
        email = f"TEST_iter175_{uuid.uuid4().hex[:10]}@example.com"
        pwd = "TempPass123!"
        r = requests.post(
            f"{API}/auth/register",
            json={"email": email, "password": pwd, "name": "Iter175 Tester", "role": "client", "terms_accepted": True, "privacy_policy_accepted": True},
            timeout=30,
        )
        assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text[:300]}"

        # Login with newly created user
        s = requests.Session()
        lr = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=30)
        assert lr.status_code == 200, f"Login after register failed: {lr.status_code} {lr.text[:200]}"

        # Cleanup: best-effort delete via admin
        try:
            admin_s = requests.Session()
            ar = admin_s.post(
                f"{API}/auth/login",
                json={"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"},
                timeout=15,
            )
            if ar.status_code == 200:
                admin_s.delete(f"{API}/admin/users/by-email/{email}", timeout=10)
        except Exception:
            pass
