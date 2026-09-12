"""Sprint 1 / Felia 1 — regression tests: event_bus + Property DNA + agent runs."""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to reading frontend/.env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

CLIENT = ("client@propmanage.io", "Client123!")
SPECIALIST = ("specialist@propmanage.io", "Spec123!")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=20)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(*CLIENT)


@pytest.fixture(scope="module")
def specialist_sess():
    return _login(*SPECIALIST)


@pytest.fixture(scope="module")
def admin_sess():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def client_property_id(client_sess):
    r = client_sess.get(f"{BASE_URL}/api/properties", timeout=15)
    assert r.status_code == 200, r.text
    props = r.json()
    assert isinstance(props, list) and len(props) > 0, "client has no properties"
    return str(props[0].get("id") or props[0].get("_id"))


# ── Regression: request lifecycle (log_event delegates to event_bus) ─────────
class TestRequestLifecycleRegression:
    def test_create_request_no_500(self, client_sess, client_property_id):
        payload = {
            "property_id": client_property_id,
            "category": "zugravit",
            "title": "TEST_DNA_ regression zugravit",
            "description": "Test regresie event bus - flux request",
        }
        r = client_sess.post(f"{BASE_URL}/api/requests", json=payload, timeout=25)
        assert r.status_code in (200, 201), f"create request failed: {r.status_code} {r.text}"
        data = r.json()
        assert "id" in data or "_id" in data or "request_id" in data, data
        pytest.request_id = str(data.get("id") or data.get("_id") or data.get("request_id"))

    def test_request_visible_in_my(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/requests", timeout=15)
        assert r.status_code == 200
        items = r.json()
        titles = [i.get("title", "") for i in items]
        assert any("TEST_DNA_" in t for t in titles), f"created req not in my list: {titles[:5]}"

    def test_specialist_can_list_requests(self, specialist_sess):
        # specialist listing: /api/requests (specialist sees open + assigned)
        r = specialist_sess.get(f"{BASE_URL}/api/requests", timeout=15)
        assert r.status_code == 200, f"specialist list: {r.status_code} {r.text[:200]}"


# ── DNA API ──────────────────────────────────────────────────────────────────
class TestPropertyDNA:
    def test_dna_owner_ok(self, client_sess, client_property_id):
        # small delay to ensure event bus wrote the event
        time.sleep(1.0)
        r = client_sess.get(f"{BASE_URL}/api/properties/{client_property_id}/dna", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "dna_completeness" in d and 0 <= d["dna_completeness"] <= 100
        caps = d.get("capabilities", {})
        assert len(caps) == 10, f"expected 10 capabilities, got {len(caps)}: {list(caps.keys())}"
        assert caps["works"]["data"]["total"] > 0, caps["works"]
        # timeline should exist
        assert isinstance(d.get("timeline"), list) and len(d["timeline"]) > 0
        # look for a "Cerere creată" (request.created) type after our creation
        types = [e.get("type") for e in d["timeline"]]
        assert any("request" in (t or "") and "creat" in (t or "") for t in types) or \
               any("request.created" == t or "request_created" == t for t in types), \
               f"no request.created event in timeline: {types[:10]}"

    def test_dna_specialist_forbidden(self, specialist_sess, client_property_id):
        r = specialist_sess.get(f"{BASE_URL}/api/properties/{client_property_id}/dna", timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:150]}"

    def test_dna_unauth(self, client_property_id):
        r = requests.get(f"{BASE_URL}/api/properties/{client_property_id}/dna", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# ── Admin agent runs ────────────────────────────────────────────────────────
class TestAgentRuns:
    def test_admin_can_read(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/agent-runs", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("runs", "total_recorded", "errors_recorded", "top_failing"):
            assert k in d, f"missing key {k}: {list(d.keys())}"
        assert isinstance(d["runs"], list)

    def test_client_forbidden(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/admin/agent-runs", timeout=15)
        assert r.status_code == 403


# ── Smoke: dashboards ───────────────────────────────────────────────────────
class TestSmoke:
    def test_client_me(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200

    def test_specialist_me(self, specialist_sess):
        r = specialist_sess.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200
