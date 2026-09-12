"""Iter99 — Phase 4 Client Copilot + Admin Insights rule/LLM tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PWD = "Client123!"
ADMIN_EMAIL = "danieligna1@gmail.com"
ADMIN_PWD = "0108"
ADMIN_FALLBACK_EMAIL = "admin@propmanage.io"
ADMIN_FALLBACK_PWD = "1!nasov01ADMIN"


def _login(session, email, pwd):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=30)
    return r


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = _login(s, CLIENT_EMAIL, CLIENT_PWD)
    if r.status_code != 200:
        pytest.skip(f"Client login failed {r.status_code}: {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = _login(s, ADMIN_EMAIL, ADMIN_PWD)
    if r.status_code != 200:
        # try fallback
        r2 = _login(s, ADMIN_FALLBACK_EMAIL, ADMIN_FALLBACK_PWD)
        if r2.status_code != 200:
            pytest.skip(f"Admin login failed both users. owner:{r.status_code} fallback:{r2.status_code}")
    # verify /me is admin
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    if me.get("role") != "admin":
        pytest.skip(f"Not an admin: role={me.get('role')}")
    return s


# ---- Client Copilot ----
class TestClientCopilot:
    def test_copilot_shape(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/client/copilot", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "properties_count" in data
        assert "open_requests" in data
        assert "active_jobs" in data
        assert isinstance(data.get("actions"), list)
        assert len(data["actions"]) <= 3
        for a in data["actions"]:
            assert "kind" in a
            assert "priority" in a
            assert "text" in a
            assert "cta" in a

    def test_copilot_forbidden_for_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/client/copilot", timeout=30)
        assert r.status_code in (401, 403)

    def test_copilot_summary_llm_and_cache(self, client_session):
        # First call — could be cached from earlier tests
        t0 = time.time()
        r1 = client_session.get(f"{BASE_URL}/api/client/copilot/summary", timeout=60)
        dt1 = time.time() - t0
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert "summary" in d1
        assert "generated_at" in d1
        assert isinstance(d1["summary"], str)
        assert len(d1["summary"]) > 5
        # Second call — must be cached
        r2 = client_session.get(f"{BASE_URL}/api/client/copilot/summary", timeout=30)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("cached") is True, f"expected cached=true on second call, got {d2}"
        assert d2["summary"] == d1["summary"]
        print(f"[copilot/summary] first={dt1:.1f}s cached_first_call={d1.get('cached')}")


# ---- Admin Insights (rule) ----
class TestAdminInsightsRule:
    def test_rule_users(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/rule?module=users", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("bullets"), list)
        assert isinstance(d.get("alerts"), list)
        assert isinstance(d.get("recommendations"), list)
        assert len(d["bullets"]) >= 1

    def test_rule_bi(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/rule?module=bi", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("bullets"), list)
        assert len(d["bullets"]) >= 1

    def test_rule_invalid(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/rule?module=invalid", timeout=30)
        assert r.status_code == 400

    def test_rule_forbidden(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/insights/rule?module=users", timeout=30)
        assert r.status_code in (401, 403)


# ---- Admin Insights (LLM) ----
class TestAdminInsightsLLM:
    def test_llm_users(self, admin_session):
        t0 = time.time()
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=users", timeout=90)
        dt = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("bullets"), list)
        assert "generated_at" in d
        # Second call must be cached
        r2 = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=users", timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("cached") is True
        print(f"[llm/users] first={dt:.1f}s cached_on_first={d.get('cached')}")

    def test_llm_bi(self, admin_session):
        t0 = time.time()
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=bi", timeout=90)
        dt = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d.get("bullets"), list)
        r2 = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=bi", timeout=30)
        assert r2.status_code == 200
        assert r2.json().get("cached") is True
        print(f"[llm/bi] first={dt:.1f}s")

    def test_llm_invalid(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/insights/llm?module=nope", timeout=30)
        assert r.status_code == 400
