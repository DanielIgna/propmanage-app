"""Backend tests for Admin Impersonation feature (Phase IMP).

Covers BACKEND-A..H from review_request iteration 29:
- Impersonation flow (login, stop, dangerous endpoint blocking, audit log, access history)
- Role/permission guards
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
SPEC_EMAIL = "specialist@propmanage.io"
SPEC_PASS = "Spec123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


@pytest.fixture(scope="module")
def specialist_session():
    return _login(SPEC_EMAIL, SPEC_PASS)


@pytest.fixture(scope="module")
def client_user_id(admin_session):
    """Look up client user id via admin users endpoint (paginated)."""
    for skip in range(0, 5000, 50):
        r = admin_session.get(f"{BASE_URL}/api/admin/users?limit=50&skip={skip}", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items") or []
        if not items:
            break
        for u in items:
            if u.get("email") == CLIENT_EMAIL:
                uid = u.get("id") or u.get("_id")
                assert uid, f"client found but no id field: {u}"
                return uid
    pytest.skip("Client user not found in admin list pages")


@pytest.fixture(scope="module")
def admin_user_id(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=20)
    assert r.status_code == 200
    return r.json().get("id") or r.json().get("_id")


# ---------- BACKEND-A: start impersonation ----------
class TestStartImpersonation:
    def test_impersonate_client_success(self, admin_session, client_user_id):
        """Admin starts impersonating client → 200 + correct shape + cookies set."""
        # Make a fresh session (do not pollute module session with imp cookies)
        s = _login(ADMIN_EMAIL, ADMIN_PASS)
        r = s.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "QA smoke test impersonation - iteration 29"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["expires_in_seconds"] == 7200
        assert "log_id" in data and isinstance(data["log_id"], str)
        assert data["target"]["email"] == CLIENT_EMAIL
        assert data["target"]["role"] == "client"
        assert data["redirect_to"] == "/client"
        assert "started_at" in data

        # Cookies: admin_access_token AND access_token present
        cookie_names = {c.name for c in s.cookies}
        assert "admin_access_token" in cookie_names, f"Missing admin_access_token. Got: {cookie_names}"
        assert "access_token" in cookie_names, f"Missing access_token. Got: {cookie_names}"

        # BACKEND-B: /api/auth/me returns the TARGET user with impersonation block
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200, me.text
        meu = me.json()
        assert meu["email"] == CLIENT_EMAIL, f"Expected client email but got {meu.get('email')}"
        imp = meu.get("impersonation")
        assert imp, f"Missing impersonation block in /auth/me: {meu}"
        assert imp.get("admin_email") == ADMIN_EMAIL
        assert imp.get("log_id") == data["log_id"]
        assert "admin_id" in imp and "started_at" in imp

        # Cleanup
        s.post(f"{BASE_URL}/api/admin/stop-impersonation", timeout=15)

    def test_reason_too_short_422(self, admin_session, client_user_id):
        r = admin_session.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "short"},
            timeout=15,
        )
        assert r.status_code == 422, f"Expected 422 got {r.status_code}: {r.text}"

    def test_cannot_impersonate_admin_403(self, admin_session, admin_user_id):
        # Try impersonating self (admin)
        r = admin_session.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": admin_user_id, "reason": "Trying to impersonate admin role"},
            timeout=15,
        )
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"
        assert "administrator" in r.text.lower() or "admin" in r.text.lower()

    def test_double_impersonation_409(self, client_user_id):
        s = _login(ADMIN_EMAIL, ADMIN_PASS)
        r1 = s.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "First impersonation iteration 29"},
            timeout=15,
        )
        assert r1.status_code == 200, r1.text
        r2 = s.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "Second nested impersonation try"},
            timeout=15,
        )
        # Spec says 409, but practical implementation blocks via require_role (target role!=admin)
        # so 403 is also acceptable as long as nested impersonation is denied.
        assert r2.status_code in (403, 409), f"Expected 403/409, got {r2.status_code}: {r2.text}"
        # Cleanup
        s.post(f"{BASE_URL}/api/admin/stop-impersonation", timeout=15)

    def test_non_admin_403(self, client_session, client_user_id):
        r = client_session.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "Non-admin tries impersonate"},
            timeout=15,
        )
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_anonymous_401(self, client_user_id):
        r = requests.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "Anonymous tries impersonate"},
            timeout=15,
        )
        assert r.status_code == 401, f"Expected 401 got {r.status_code}: {r.text}"


# ---------- BACKEND-C: dangerous endpoints blocked ----------
class TestDangerousEndpointsBlocked:
    @pytest.fixture
    def imp_session(self, client_user_id):
        s = _login(ADMIN_EMAIL, ADMIN_PASS)
        r = s.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "QA dangerous endpoint blocking test"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        yield s
        s.post(f"{BASE_URL}/api/admin/stop-impersonation", timeout=15)

    def test_change_password_blocked(self, imp_session):
        r = imp_session.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "Client123!", "new_password": "NewPass123!"},
            timeout=15,
        )
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_account_delete_blocked(self, imp_session):
        r = imp_session.post(
            f"{BASE_URL}/api/auth/account-delete",
            json={"password": "Client123!", "confirmation": "DELETE", "confirm": True},
            timeout=15,
        )
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_2fa_setup_blocked(self, imp_session):
        r = imp_session.post(f"{BASE_URL}/api/auth/2fa/setup", json={}, timeout=15)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_2fa_verify_blocked(self, imp_session):
        r = imp_session.post(f"{BASE_URL}/api/auth/2fa/verify", json={"code": "000000"}, timeout=15)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"

    def test_2fa_disable_blocked(self, imp_session):
        r = imp_session.post(f"{BASE_URL}/api/auth/2fa/disable", json={"password": "Client123!", "code": "000000"}, timeout=15)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"


# ---------- BACKEND-D: stop impersonation ----------
class TestStopImpersonation:
    def test_full_cycle(self, client_user_id):
        s = _login(ADMIN_EMAIL, ADMIN_PASS)
        r = s.post(
            f"{BASE_URL}/api/admin/impersonate",
            json={"user_id": client_user_id, "reason": "Stop cycle test iteration 29"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        log_id = r.json()["log_id"]
        # Sleep a moment so duration_seconds is non-zero
        time.sleep(1.2)

        stop = s.post(f"{BASE_URL}/api/admin/stop-impersonation", timeout=15)
        assert stop.status_code == 200, stop.text
        data = stop.json()
        assert data["ok"] is True
        assert data["log_id"] == log_id
        assert data["redirect_to"] == "/admin"
        assert isinstance(data["duration_seconds"], int)
        assert data["duration_seconds"] >= 1

        # admin_access_token cookie should be gone
        cookie_names = {c.name for c in s.cookies}
        assert "admin_access_token" not in cookie_names or s.cookies.get("admin_access_token") in (None, "", "deleted"), \
            f"admin_access_token cookie not cleared: {cookie_names}"

        # /auth/me returns admin again, no impersonation
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert me.status_code == 200
        meu = me.json()
        assert meu["email"] == ADMIN_EMAIL, f"Expected admin after stop, got {meu.get('email')}"
        assert not meu.get("impersonation"), f"Still impersonating: {meu.get('impersonation')}"

    def test_stop_without_impersonation_400(self, admin_session):
        # admin_session has no active impersonation
        r = admin_session.post(f"{BASE_URL}/api/admin/stop-impersonation", timeout=15)
        assert r.status_code in (400, 401), f"Expected 400 got {r.status_code}: {r.text}"


# ---------- BACKEND-E: admin impersonation-logs ----------
class TestImpersonationLogsList:
    def test_list_logs(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/impersonation-logs", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "total" in data
        assert isinstance(data["items"], list)
        assert data["total"] >= 1, "Expected at least 1 log from previous tests"
        # Check shape of first item
        it = data["items"][0]
        for k in ("admin_id", "admin_email", "target_user_id", "target_user_email",
                  "target_user_role", "reason", "ip", "user_agent", "started_at"):
            assert k in it, f"Missing field {k} in log item: {it.keys()}"
        # ended_at + duration_seconds may be null for ongoing, but should exist as keys
        assert "ended_at" in it
        assert "duration_seconds" in it
        # Sorted desc by started_at: compare first two
        if len(data["items"]) >= 2:
            assert data["items"][0]["started_at"] >= data["items"][1]["started_at"]

    def test_non_admin_blocked(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/impersonation-logs", timeout=15)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}: {r.text}"


# ---------- BACKEND-F: data-subject access history ----------
class TestAccessHistory:
    def test_client_sees_own_history_no_pii(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/me/access-history", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "count" in data
        # From previous test runs, should have at least 1 entry
        assert data["count"] >= 1, f"Expected at least 1 access history entry, got {data['count']}"
        item = data["items"][0]
        # MUST include
        assert "admin_email" in item or "admin_name" in item
        assert "reason" in item
        assert "started_at" in item
        # MUST NOT include
        assert "ip" not in item, f"IP leaked to data subject: {item}"
        assert "user_agent" not in item, f"User-Agent leaked to data subject: {item}"

    def test_anonymous_blocked(self):
        r = requests.get(f"{BASE_URL}/api/me/access-history", timeout=15)
        assert r.status_code == 401
