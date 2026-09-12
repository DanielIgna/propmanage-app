"""Phase 70 — AI Control Center backend tests.

Covers:
- /api/admin/ai-control/{overview, config, providers, memories, bugs/search, graph}
- Memory engine auto-persist via QA Copilot finding
- Feature flag ai_ecosystem.enabled short-circuits memory.remember()
- Non-admin (client) gets 403
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

def _get_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        # Fall back to reading frontend/.env
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass
    return url.rstrip("/")

BASE_URL = _get_base_url()
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"


# ----- Auth fixtures -----
def _login(session: requests.Session, email: str, password: str):
    r = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PASS)
    yield s
    # Ensure ecosystem re-enabled at end of suite
    try:
        s.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": True}, timeout=20)
    except Exception:
        pass


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    _login(s, CLIENT_EMAIL, CLIENT_PASS)
    return s


# ----- Overview & Config -----
class TestOverviewAndConfig:
    def test_overview_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/overview", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("config", "memory", "bugs", "graph", "agents", "providers"):
            assert key in data, f"missing key {key}"
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) == 6, f"expected 6 agents got {len(data['agents'])}"
        ids = {a["id"] for a in data["agents"]}
        assert ids == {"concierge", "ai_investigator", "qa_copilot", "memory_engine", "bug_memory", "knowledge_graph"}
        assert isinstance(data["providers"], dict)
        assert set(data["providers"].keys()) == {"anthropic", "openai", "gemini", "ollama"}

    def test_config_defaults(self, admin_session):
        # Ensure enabled=true first so defaults check works
        admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={
            "enabled": True, "provider": "anthropic",
            "model": "claude-sonnet-4-5-20250929",
            "temperature": 0.3, "max_tokens": 2048,
        }, timeout=20)
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/config", timeout=20)
        assert r.status_code == 200
        cfg = r.json()
        assert cfg["enabled"] is True
        assert cfg["provider"] == "anthropic"
        assert cfg["model"] == "claude-sonnet-4-5-20250929"
        assert float(cfg["temperature"]) == 0.3
        assert int(cfg["max_tokens"]) == 2048

    def test_update_temperature_persists(self, admin_session):
        r = admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={"temperature": 0.7}, timeout=20)
        assert r.status_code == 200, r.text
        assert float(r.json()["temperature"]) == 0.7
        # reload
        r2 = admin_session.get(f"{BASE_URL}/api/admin/ai-control/config", timeout=20)
        assert float(r2.json()["temperature"]) == 0.7
        # restore
        admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={"temperature": 0.3}, timeout=20)

    def test_reject_inactive_provider(self, admin_session):
        r = admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={"provider": "ollama"}, timeout=20)
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"

    def test_reject_unknown_provider(self, admin_session):
        r = admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={"provider": "bogus"}, timeout=20)
        assert r.status_code == 400

    def test_providers_endpoint(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/providers", timeout=20)
        assert r.status_code == 200
        prov = r.json()["providers"]
        assert prov["anthropic"]["active"] is True
        assert prov["openai"]["active"] is True
        assert prov["gemini"]["active"] is True
        assert prov["ollama"]["active"] is False


# ----- Memory engine + QA Copilot integration -----
class TestMemoryEngine:
    def test_memory_filters(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/memories", params={"scope": "qa_copilot", "limit": 10}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        for m in data["items"]:
            assert m["scope"] == "qa_copilot"
            assert "_id" not in m, "Mongo _id should be excluded"

    def test_qa_finding_creates_memory(self, admin_session):
        # Create a fresh QA session
        sess_r = admin_session.post(
            f"{BASE_URL}/api/admin/qa-copilot/sessions",
            json={"title": "TEST_Phase70 mem-link", "role_being_tested": "client", "area": "memory engine test"},
            timeout=20,
        )
        assert sess_r.status_code in (200, 201), sess_r.text
        sid = sess_r.json()["id"]

        baseline_r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/memories", params={"user_id": ADMIN_EMAIL, "scope": "qa_copilot"}, timeout=20)
        baseline = baseline_r.json().get("total", 0)

        # Add a finding (this triggers ai_memory.remember inside qa_copilot route)
        f_r = admin_session.post(
            f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}/findings",
            json={"text": "TEST_Phase70 specialist Cluj nu apare in lista cand caut HVAC verificat"},
            timeout=60,  # claude call inside
        )
        assert f_r.status_code in (200, 201), f_r.text

        time.sleep(1.0)  # let insert flush
        after_r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/memories", params={"user_id": ADMIN_EMAIL, "scope": "qa_copilot"}, timeout=20)
        after = after_r.json().get("total", 0)
        assert after >= baseline + 1, f"expected memory count to grow (baseline {baseline} -> {after})"

        # Cleanup session
        admin_session.delete(f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}", timeout=20)

    def test_delete_single_memory(self, admin_session):
        items = admin_session.get(f"{BASE_URL}/api/admin/ai-control/memories", params={"user_id": ADMIN_EMAIL, "limit": 1}, timeout=20).json().get("items", [])
        if not items:
            pytest.skip("no memory to delete")
        mid = items[0]["id"]
        r = admin_session.delete(f"{BASE_URL}/api/admin/ai-control/memories/{mid}", timeout=20)
        assert r.status_code == 200
        assert r.json().get("deleted") is True
        # Verify gone
        r404 = admin_session.delete(f"{BASE_URL}/api/admin/ai-control/memories/{mid}", timeout=20)
        assert r404.status_code == 404

    def test_reset_memories_for_user(self, admin_session):
        # First seed a memory: create a finding so we have at least one
        sess = admin_session.post(f"{BASE_URL}/api/admin/qa-copilot/sessions", json={"title": "TEST_Phase70 reset seed", "role_being_tested": "client"}, timeout=20).json()
        sid = sess["id"]
        admin_session.post(f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}/findings", json={"text": "TEST_Phase70 reset seed finding"}, timeout=60)
        time.sleep(0.5)
        r = admin_session.post(f"{BASE_URL}/api/admin/ai-control/memories/reset", json={"user_id": ADMIN_EMAIL}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "deleted_count" in d and d["deleted_count"] >= 1
        admin_session.delete(f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}", timeout=20)


# ----- Bug Memory -----
class TestBugMemory:
    def test_search_returns_items(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/bugs/search", params={"q": "specialist"}, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data
        # Don't assert >0 — depends on existing data — just shape
        for it in data["items"]:
            assert "source" in it and it["source"] in ("qa_copilot", "ai_investigator")
            assert "score" in it
            assert "severity" in it
            assert "category" in it

    def test_search_min_length(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/bugs/search", params={"q": "a"}, timeout=20)
        assert r.status_code in (400, 422), f"expected validation error got {r.status_code}"


# ----- Knowledge Graph -----
class TestKnowledgeGraph:
    def test_graph_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/graph", params={"user_id": ADMIN_EMAIL}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data and "edges" in data
        # admin user node should exist if user found
        if data["nodes"]:
            assert any(n["type"] == "user" for n in data["nodes"])
            assert "center_user_id" in data

    def test_graph_client(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-control/graph", params={"user_id": CLIENT_EMAIL}, timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data and "edges" in data


# ----- Auth gating -----
class TestAuthGating:
    def test_client_blocked_overview(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/ai-control/overview", timeout=20)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_client_blocked_config(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/ai-control/config", timeout=20)
        assert r.status_code in (401, 403)

    def test_client_blocked_memories(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/ai-control/memories", timeout=20)
        assert r.status_code in (401, 403)


# ----- Feature flag kill-switch -----
class TestFeatureFlag:
    def test_disable_then_remember_skips(self, admin_session):
        # Disable
        r = admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": False}, timeout=20)
        assert r.status_code == 200
        assert r.json()["enabled"] is False

        # Verify legacy modules still work: list sessions
        list_r = admin_session.get(f"{BASE_URL}/api/admin/qa-copilot/sessions", timeout=20)
        assert list_r.status_code == 200, f"qa_copilot list broken when ecosystem disabled: {list_r.text}"

        # Create a session + finding — memory should NOT be created
        sess = admin_session.post(f"{BASE_URL}/api/admin/qa-copilot/sessions", json={"title": "TEST_Phase70 flag off", "role_being_tested": "client"}, timeout=20).json()
        sid = sess["id"]
        before = admin_session.get(f"{BASE_URL}/api/admin/ai-control/memories", params={"user_id": ADMIN_EMAIL, "scope": "qa_copilot"}, timeout=20).json()["total"]
        admin_session.post(f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}/findings", json={"text": "TEST_Phase70 flag off finding"}, timeout=60)
        time.sleep(0.5)
        after = admin_session.get(f"{BASE_URL}/api/admin/ai-control/memories", params={"user_id": ADMIN_EMAIL, "scope": "qa_copilot"}, timeout=20).json()["total"]
        assert after == before, f"memory should not grow when ecosystem disabled (before {before} -> after {after})"
        admin_session.delete(f"{BASE_URL}/api/admin/qa-copilot/sessions/{sid}", timeout=20)

        # Re-enable
        r2 = admin_session.put(f"{BASE_URL}/api/admin/ai-control/config", json={"enabled": True}, timeout=20)
        assert r2.status_code == 200
        assert r2.json()["enabled"] is True
