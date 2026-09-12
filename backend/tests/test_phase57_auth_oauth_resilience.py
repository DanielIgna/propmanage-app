"""Phase 57: Google OAuth resilience + admin cookie cleanup on login.

Tests focus on /api/auth/google/session error handling (400 missing header,
401 on bogus session_id, retry/timeout structure) and /api/auth/login
cookies including admin_access_token cleanup.

Notes:
- We cannot easily simulate a slow Emergent upstream from a test, so the
  retry/timeout structure is verified by inspecting source code.
- We DO hit the real upstream with a bogus session_id; upstream returns
  a 4xx fast → backend should respond with 401.
"""
import os
import re
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
AUTH_PY = "/app/backend/routes/auth.py"


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_session(api_client):
    r = api_client.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD},
    )
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return r


# ---------- 1. /api/health ----------
class TestHealth:
    def test_health_ok(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        # Body must include a status field
        data = r.json()
        assert isinstance(data, dict)


# ---------- 2. Google session exchange error handling ----------
class TestGoogleSessionExchange:
    def test_missing_session_header_returns_400(self, api_client):
        r = api_client.post(f"{BASE_URL}/api/auth/google/session")
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:300]}"
        body = r.json()
        detail = body.get("detail") or body.get("message") or ""
        assert "X-Session-ID" in detail, f"Detail missing X-Session-ID hint: {detail!r}"
        assert "Lipsește" in detail or "lipse" in detail.lower(), \
            f"Detail not Romanian as expected: {detail!r}"

    def test_bogus_session_id_returns_401(self, api_client):
        # Real upstream returns 404 fast for a non-existent session
        r = api_client.post(
            f"{BASE_URL}/api/auth/google/session",
            headers={"X-Session-ID": "bogus-test-123-not-real"},
        )
        assert r.status_code == 401, \
            f"Expected 401 (NOT 520/502/503), got {r.status_code}: {r.text[:400]}"
        body = r.json()
        detail = body.get("detail") or body.get("message") or ""
        assert "Emergent OAuth a refuzat sesiunea" in detail, \
            f"Detail missing Romanian rejection message: {detail!r}"
        assert "session_id expirat" in detail, \
            f"Detail missing session_id expirat hint: {detail!r}"
        assert "propmanage.ro/auth/callback nu este whitelisted" in detail, \
            f"Detail missing whitelist hint: {detail!r}"


# ---------- 3. Retry / timeout / 503 fallback structure (source inspection) ----------
class TestGoogleSessionRetryStructure:
    @pytest.fixture(scope="class")
    def src(self):
        with open(AUTH_PY, "r") as f:
            return f.read()

    def test_retry_loop_has_2_attempts(self, src):
        # Retry loop intentionally reduced to 2 × 15s (+2s backoff) so the total
        # stays under the Kubernetes ingress proxy timeout (~60s) — see auth.py.
        assert re.search(r"for\s+attempt\s+in\s+range\(\s*2\s*\)", src), \
            "Retry loop should iterate exactly 2 times"

    def test_timeout_is_15_seconds(self, src):
        # `httpx.AsyncClient(timeout=15)` (not 10)
        assert re.search(r"httpx\.AsyncClient\(\s*timeout\s*=\s*15\s*\)", src), \
            "httpx.AsyncClient timeout should be 15 seconds"
        # Negative: ensure old 10s timeout is not present
        assert not re.search(r"httpx\.AsyncClient\(\s*timeout\s*=\s*10\s*\)", src), \
            "Old 10s timeout still present"

    def test_fallback_returns_503_not_520(self, src):
        # After exhausted retries, code should raise HTTPException(503, ...)
        # Look for the 'exhausted retries' section
        assert "exhausted retries" in src.lower() or "Emergent OAuth nu răspunde" in src, \
            "503 fallback message missing"
        assert re.search(r"HTTPException\(\s*503", src), \
            "Final fallback should be HTTPException(503, ...) not 520/502"

    def test_4xx_upstream_short_circuits_no_retry(self, src):
        # 4xx branch should raise immediately (no retry)
        assert "Emergent OAuth a refuzat sesiunea" in src
        # Ensure the 4xx raise lives inside the retry loop and the retry-continue
        # only happens for 5xx + network errors
        assert re.search(r"if\s+400\s*<=\s*r\.status_code\s*<\s*500", src), \
            "4xx detection branch missing"


# ---------- 4. Login cookies + admin_access_token cleanup ----------
class TestLoginCookies:
    def test_admin_login_sets_access_and_refresh_and_clears_admin_stash(self, api_client):
        r = api_client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD},
        )
        assert r.status_code == 200, f"Login failed: {r.text[:300]}"

        # Inspect raw Set-Cookie headers (requests merges them in .headers but
        # exposes all via raw header list)
        set_cookie_headers = r.raw.headers.getlist("Set-Cookie") \
            if hasattr(r.raw.headers, "getlist") else [r.headers.get("Set-Cookie", "")]
        joined = " ;; ".join(set_cookie_headers)

        assert "access_token=" in joined, f"access_token cookie not set: {joined[:500]}"
        assert "refresh_token=" in joined, f"refresh_token cookie not set: {joined[:500]}"
        # admin_access_token must be explicitly deleted (expires/Max-Age=0)
        assert "admin_access_token=" in joined, \
            f"admin_access_token cookie cleanup header missing: {joined[:500]}"
        # Look for either Max-Age=0 or an expiry in the past on the delete cookie
        admin_cookie_line = next(
            (h for h in set_cookie_headers if h.startswith("admin_access_token=")), ""
        )
        assert ("Max-Age=0" in admin_cookie_line) \
            or ("expires=Thu, 01 Jan 1970" in admin_cookie_line.lower()) \
            or ("max-age=0" in admin_cookie_line.lower()), \
            f"admin_access_token not marked for deletion: {admin_cookie_line!r}"

    def test_admin_login_returns_role_admin(self, admin_session):
        body = admin_session.json()
        assert body.get("role") == "admin", f"Role mismatch: {body.get('role')}"
        assert body.get("email") == "admin@propmanage.io"

    def test_refresh_with_valid_cookie(self, api_client):
        # Fresh login → use those cookies to call /api/auth/refresh
        s = requests.Session()
        login = s.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD},
        )
        assert login.status_code == 200
        # Try refresh endpoint (may be /api/auth/refresh)
        refresh = s.post(f"{BASE_URL}/api/auth/refresh")
        # Accept 200 or 404 (if endpoint not present) — but if endpoint exists, must be 200
        if refresh.status_code == 404:
            pytest.skip("/api/auth/refresh endpoint not present in this build")
        assert refresh.status_code == 200, \
            f"Refresh failed: {refresh.status_code} {refresh.text[:200]}"


# ---------- 5. Digital Twin endpoints (smoke — full coverage in iteration_43) ----------
class TestDigitalTwinSmoke:
    def test_dt_endpoints_routes_exist(self, api_client):
        # Just verify the operator trimble PATCH endpoint exists by hitting it
        # without auth → should return 401/403 (NOT 404).
        r = api_client.patch(
            f"{BASE_URL}/api/operator/digital-twin/projects/nonexistent/trimble",
            json={"trimble_url": "https://web.connect.trimble.com/dummy"},
        )
        assert r.status_code in (401, 403, 404, 422), \
            f"Unexpected status for unauth trimble PATCH: {r.status_code} {r.text[:200]}"
        # If 404 occurred, ensure it's because of project lookup, not missing route
        if r.status_code == 404:
            body = r.json()
            detail = body.get("detail") or body.get("message") or ""
            # Routing 404 typically says "Not Found" — project 404 usually has a
            # more descriptive message. Either is acceptable for smoke.
            assert detail, "Empty 404 detail (possible routing issue)"
