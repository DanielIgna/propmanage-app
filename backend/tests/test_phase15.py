# Phase 15 — LastActionBanner / last_event enrichment on GET /api/requests
# Verifies that each request returned by /api/requests carries a 'last_event' field
# matching the most-recent activity event for that request (or None).
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


# ---------- field shape ----------
class TestLastEventField:
    def test_requests_have_last_event_key(self, client_session):
        r = client_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0, "client should have requests"
        for req in data:
            assert "last_event" in req, f"missing last_event on request {req.get('id')}"

    def test_last_event_shape_when_present(self, client_session):
        r = client_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        data = r.json()
        any_event = False
        for req in data:
            ev = req.get("last_event")
            if ev is None:
                continue
            any_event = True
            for k in ("event_type", "actor_name", "actor_role", "created_at"):
                assert k in ev, f"last_event missing {k}"
            assert isinstance(ev["event_type"], str) and "." in ev["event_type"]
            assert isinstance(ev["actor_name"], str) and len(ev["actor_name"]) > 0
            assert ev["actor_role"] in {"client", "specialist", "admin", "operator", "system"}
            assert "payload" in ev  # may be {} but key present
        assert any_event, "expected at least one request with last_event populated"

    def test_last_event_matches_timeline_first(self, client_session):
        """last_event should equal events[-1] (most recent) from /timeline."""
        r = client_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        for req in r.json():
            if not req.get("last_event"):
                continue
            tl = client_session.get(f"{API}/requests/{req['id']}/timeline", timeout=15)
            if tl.status_code != 200:
                continue
            events = tl.json().get("events") or []
            if not events:
                continue
            latest = events[-1]  # timeline returns ASC per prior phase
            assert req["last_event"]["event_type"] == latest["event_type"], (
                f"mismatch for {req['id']}: banner={req['last_event']['event_type']} vs timeline={latest['event_type']}"
            )
            assert req["last_event"]["actor_name"] == latest["actor_name"]
            return  # one verification is enough
        pytest.skip("No request with last_event + timeline events available")


# ---------- regression: filters & RBAC still work + carry field ----------
class TestRegression:
    def test_client_filter_status(self, client_session):
        r = client_session.get(f"{API}/requests?status=open", timeout=15)
        assert r.status_code == 200
        for req in r.json():
            assert req.get("status") == "open"
            assert "last_event" in req

    def test_client_filter_category(self, client_session):
        r = client_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        cats = {x.get("category") for x in r.json() if x.get("category")}
        if not cats:
            pytest.skip("no categories present")
        cat = next(iter(cats))
        r2 = client_session.get(f"{API}/requests?category={cat}", timeout=15)
        assert r2.status_code == 200
        for req in r2.json():
            assert req["category"] == cat
            assert "last_event" in req

    def test_client_text_search(self, client_session):
        r = client_session.get(f"{API}/requests?q=z", timeout=15)
        assert r.status_code == 200
        for req in r.json():
            assert "last_event" in req

    def test_specialist_sees_open_and_own(self, specialist_session):
        r = specialist_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for req in data:
            assert "last_event" in req

    def test_admin_sees_all(self, admin_session):
        r = admin_session.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        for req in data:
            assert "last_event" in req

    def test_unauthenticated_blocked(self):
        r = requests.get(f"{API}/requests", timeout=15)
        assert r.status_code in (401, 403)


# ---------- Phase 14 regression: timeline still functional ----------
class TestPhase14Regression:
    def test_timeline_endpoint_works(self, client_session):
        r = client_session.get(f"{API}/requests", timeout=15)
        ids = [x["id"] for x in r.json() if x.get("last_event")]
        assert ids, "no request with events to test timeline"
        tl = client_session.get(f"{API}/requests/{ids[0]}/timeline", timeout=15)
        assert tl.status_code == 200
        body = tl.json()
        assert "events" in body and isinstance(body["events"], list)
        assert "request" in body
