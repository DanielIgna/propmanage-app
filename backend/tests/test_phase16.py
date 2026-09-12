# Phase 16 — Daily Digest Emails @ 19:00 Europe/Bucharest
# Verifies digest preview/trigger endpoints, role-specific content, opt-out flow, scheduler registration.
import os
import pytest
import requests
from dotenv import load_dotenv
from tests.test_config import OWNER_ADMIN_PASSWORD

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
OPERATOR = {"email": "operator@propmanage.io", "password": "Op123!"}


def _login(payload):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=payload, timeout=15)
    assert r.status_code == 200, f"login failed for {payload['email']}: {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def specialist_session():
    return _login(SPECIALIST)


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def operator_session():
    return _login(OPERATOR)


# ---------- POST /api/auth/digest/preview per role ----------
class TestDigestPreview:
    def _assert_shape(self, body):
        # Either non-empty digest OR explicit {empty: true}
        assert "summary" in body, f"missing summary in {body}"
        assert "cards" in body, f"missing cards in {body}"
        if body.get("empty"):
            assert body["summary"] == "Niciun conținut relevant astăzi."
            assert body["cards"] == ""
        else:
            assert "cta_label" in body
            assert "cta_link" in body
            assert isinstance(body["summary"], str) and len(body["summary"]) > 0

    def test_client_preview(self, client_session):
        r = client_session.post(f"{API}/auth/digest/preview", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        self._assert_shape(body)
        if not body.get("empty"):
            # client summary must mention notificări counts (per builder)
            assert "notificări" in body["summary"].lower() or "mesaje" in body["summary"].lower()
            assert body["cta_link"] == "/client"

    def test_specialist_preview(self, specialist_session):
        r = specialist_session.post(f"{API}/auth/digest/preview", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        self._assert_shape(body)
        if not body.get("empty"):
            # Specialist summary must include wallet + tier
            assert "RON" in body["summary"]
            assert "Tier" in body["summary"]
            assert body["cta_link"] == "/specialist"

    def test_admin_preview(self, admin_session):
        r = admin_session.post(f"{API}/auth/digest/preview", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        self._assert_shape(body)
        if not body.get("empty"):
            assert "Specialiști" in body["summary"] or "specialiști" in body["summary"]
            assert body["cta_link"] == "/admin"

    def test_operator_preview(self, operator_session):
        r = operator_session.post(f"{API}/auth/digest/preview", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        self._assert_shape(body)
        if not body.get("empty"):
            assert "twin" in body["summary"].lower()
            assert body["cta_link"] == "/operator"

    def test_preview_requires_auth(self):
        r = requests.post(f"{API}/auth/digest/preview", timeout=15)
        # Unauth → 401/403
        assert r.status_code in (401, 403), r.status_code


# ---------- POST /api/admin/digest/trigger ----------
class TestAdminTrigger:
    def test_admin_trigger_returns_counts(self, admin_session):
        r = admin_session.post(f"{API}/admin/digest/trigger", timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        counts = body.get("counts")
        assert isinstance(counts, dict)
        for k in ("client", "specialist", "admin", "operator", "skipped"):
            assert k in counts, f"missing {k} in counts: {counts}"
            assert isinstance(counts[k], int)
            assert counts[k] >= 0

    def test_non_admin_trigger_forbidden(self, client_session, specialist_session, operator_session):
        for s in (client_session, specialist_session, operator_session):
            r = s.post(f"{API}/admin/digest/trigger", timeout=15)
            assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# ---------- POST /api/auth/digest-preference + opt-out flow ----------
class TestDigestPreference:
    def test_set_disabled_then_enabled(self, client_session):
        # Disable
        r1 = client_session.post(f"{API}/auth/digest-preference", json={"enabled": False}, timeout=15)
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert b1.get("ok") is True
        assert b1.get("digest_disabled") is True

        # Verify GET /api/auth/me reflects the new preference
        me = client_session.get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json().get("digest_disabled") is True

        # Re-enable
        r2 = client_session.post(f"{API}/auth/digest-preference", json={"enabled": True}, timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("digest_disabled") is False

        me2 = client_session.get(f"{API}/auth/me", timeout=15)
        assert me2.json().get("digest_disabled") is False

    def test_optout_skipped_in_admin_trigger(self, client_session, admin_session):
        # Disable for client
        r0 = client_session.post(f"{API}/auth/digest-preference", json={"enabled": False}, timeout=15)
        assert r0.status_code == 200

        # Baseline: trigger and capture skipped
        r_base = admin_session.post(f"{API}/admin/digest/trigger", timeout=60)
        assert r_base.status_code == 200
        skipped_when_off = r_base.json()["counts"]["skipped"]
        client_when_off = r_base.json()["counts"]["client"]

        # Re-enable
        r1 = client_session.post(f"{API}/auth/digest-preference", json={"enabled": True}, timeout=15)
        assert r1.status_code == 200

        # Trigger again — client count should not decrease and may go up; skipped should be <= previous
        r_after = admin_session.post(f"{API}/admin/digest/trigger", timeout=60)
        assert r_after.status_code == 200
        skipped_when_on = r_after.json()["counts"]["skipped"]
        client_when_on = r_after.json()["counts"]["client"]

        # Enabling client should produce at least as many client emails as before (>=)
        assert client_when_on >= client_when_off
        # And skipped should not increase
        assert skipped_when_on <= skipped_when_off

    def test_preference_requires_auth(self):
        r = requests.post(f"{API}/auth/digest-preference", json={"enabled": True}, timeout=15)
        assert r.status_code in (401, 403)


# ---------- Scheduler registration (lightweight assertion via startup logs is out of scope; ----------
# ---------- ensure the endpoint is reachable as proxy that include_router executed correctly) ----
class TestSchedulerRouting:
    def test_digest_endpoints_registered(self, admin_session):
        # All three endpoints must respond (not 404)
        for path, payload in [
            ("/auth/digest/preview", None),
            ("/auth/digest-preference", {"enabled": True}),
            ("/admin/digest/trigger", None),
        ]:
            r = admin_session.post(f"{API}{path}", json=payload, timeout=30) if payload is not None \
                else admin_session.post(f"{API}{path}", timeout=30)
            assert r.status_code != 404, f"{path} not registered ({r.status_code}): {r.text}"


# ---------- Phase 14/15 regression sanity ----------
class TestRegression:
    def test_requests_have_last_event_key(self, client_session):
        r = client_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        for req in r.json():
            assert "last_event" in req

    def test_activity_timeline_endpoint(self, client_session):
        # Pick any request id and fetch its timeline
        reqs = client_session.get(f"{API}/requests", timeout=15).json()
        if not reqs:
            pytest.skip("no requests")
        rid = reqs[0]["id"]
        tl = client_session.get(f"{API}/requests/{rid}/timeline", timeout=15)
        assert tl.status_code == 200
        body = tl.json()
        # Endpoint returns {events: [...], request: {...}} (Phase 14 shape)
        assert isinstance(body, dict)
        assert isinstance(body.get("events"), list)
