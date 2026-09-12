"""Phase 72 — AI Dev Team + AI Security Center (READ-ONLY) tests."""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_user():
    return _login(CLIENT_EMAIL, CLIENT_PASSWORD)


# ---------- AI Dev Team ----------

class TestDevTeam:
    def test_agents_list(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/ai-dev-team/agents", timeout=15)
        assert r.status_code == 200, r.text
        agents = r.json().get("agents", {})
        for k in ("frontend", "backend", "qa", "security"):
            assert k in agents, f"missing agent: {k}"
            assert "label" in agents[k]

    def test_files_unfiltered(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/ai-dev-team/files", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "files" in data
        files = data["files"]
        assert isinstance(files, list)
        assert len(files) >= 100, f"expected 100+ files, got {len(files)}"
        assert data["total"] == len(files)

    def test_files_frontend_filter(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/ai-dev-team/files?kind=frontend", timeout=20)
        assert r.status_code == 200
        files = r.json()["files"]
        assert len(files) > 0
        assert all(p.startswith("frontend/src/") for p in files), "all should start with frontend/src/"

    def test_files_backend_filter(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/ai-dev-team/files?kind=backend", timeout=20)
        assert r.status_code == 200
        files = r.json()["files"]
        assert len(files) > 0
        assert all(p.startswith("backend/") for p in files)

    def test_files_non_admin_forbidden(self, client_user):
        r = client_user.get(f"{BASE_URL}/api/admin/ai-dev-team/files", timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}"

    def test_agents_non_admin_forbidden(self, client_user):
        r = client_user.get(f"{BASE_URL}/api/admin/ai-dev-team/agents", timeout=15)
        assert r.status_code == 403

    def test_analyze_path_traversal_rejected(self, admin):
        r = admin.post(
            f"{BASE_URL}/api/admin/ai-dev-team/analyze",
            json={"file": "../etc/passwd", "agent": "backend"},
            timeout=30,
        )
        assert r.status_code == 400, f"expected 400 for traversal, got {r.status_code}: {r.text}"

    def test_analyze_outside_index_rejected(self, admin):
        r = admin.post(
            f"{BASE_URL}/api/admin/ai-dev-team/analyze",
            json={"file": "backend/.env", "agent": "backend"},
            timeout=30,
        )
        assert r.status_code == 400

    def test_analyze_non_admin_forbidden(self, client_user):
        r = client_user.post(
            f"{BASE_URL}/api/admin/ai-dev-team/analyze",
            json={"file": "backend/ai_core/code_index.py", "agent": "backend"},
            timeout=30,
        )
        assert r.status_code == 403

    def test_analyze_backend_file(self, admin):
        """LLM call — allow up to 90s."""
        r = admin.post(
            f"{BASE_URL}/api/admin/ai-dev-team/analyze",
            json={"file": "backend/ai_core/code_index.py", "agent": "backend"},
            timeout=90,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "summary" in data and isinstance(data["summary"], str) and len(data["summary"]) > 0
        assert isinstance(data.get("issues"), list)
        assert isinstance(data.get("improvements"), list)
        assert isinstance(data.get("security_concerns"), list)
        assert isinstance(data.get("next_actions"), list)
        assert data.get("provider")
        assert data.get("model")
        assert data.get("agent") == "backend"

    def test_analyze_frontend_file(self, admin):
        r = admin.post(
            f"{BASE_URL}/api/admin/ai-dev-team/analyze",
            json={"file": "frontend/src/lib/i18n.js", "agent": "frontend"},
            timeout=90,
        )
        # Some envs may not have i18n.js — fall back
        if r.status_code == 400:
            pytest.skip("frontend/src/lib/i18n.js not in index")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "summary" in data


# ---------- AI Security Center ----------

class TestSecurityCenter:
    def test_overview_default(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/ai-security/overview", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("score"), int)
        assert 0 <= data["score"] <= 100
        assert data.get("threat_level") in ("low", "medium", "high", "critical")
        stats = data.get("stats", {})
        for k in ("events_24h", "failed_logins_24h", "active_incidents", "burst_ips"):
            assert k in stats, f"missing stats.{k}"
        assert isinstance(data.get("top_event_types"), list)
        assert isinstance(data.get("suspicious_ips"), list)
        assert isinstance(data.get("active_incidents"), list)

    def test_overview_72h_window(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/ai-security/overview?hours=72", timeout=20)
        assert r.status_code == 200
        assert r.json().get("snapshot_window_hours") == 72

    def test_overview_non_admin_forbidden(self, client_user):
        r = client_user.get(f"{BASE_URL}/api/admin/ai-security/overview", timeout=15)
        assert r.status_code == 403

    def test_analyze_non_admin_forbidden(self, client_user):
        r = client_user.post(f"{BASE_URL}/api/admin/ai-security/analyze", timeout=15)
        assert r.status_code == 403

    def test_analyze_returns_structure(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/ai-security/analyze", timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        # Either real analysis or graceful empty
        assert "summary" in data
        assert isinstance(data.get("threat_patterns", []), list)
        assert isinstance(data.get("recommendations", []), list)


# ---------- Ecosystem flag interaction ----------

class TestEcosystemFlag:
    def _set_enabled(self, admin, enabled: bool):
        r = admin.put(
            f"{BASE_URL}/api/admin/ai-control/config",
            json={"enabled": enabled},
            timeout=15,
        )
        assert r.status_code in (200, 204), f"set enabled failed: {r.status_code} {r.text}"

    def test_disable_blocks_llm_endpoints_then_restore(self, admin):
        # disable
        self._set_enabled(admin, False)
        try:
            time.sleep(0.5)
            # /files should still work
            r1 = admin.get(f"{BASE_URL}/api/admin/ai-dev-team/files", timeout=20)
            assert r1.status_code == 200, "files endpoint should still work"
            # /overview should still work
            r2 = admin.get(f"{BASE_URL}/api/admin/ai-security/overview", timeout=20)
            assert r2.status_code == 200, "overview should still work"
            # DevTeam analyze should fail w/ romanian error
            r3 = admin.post(
                f"{BASE_URL}/api/admin/ai-dev-team/analyze",
                json={"file": "backend/ai_core/code_index.py", "agent": "backend"},
                timeout=30,
            )
            # Returns error dict via HTTPException 400 OR JSON 200 with error key
            if r3.status_code == 400:
                assert "dezactivat" in (r3.text or "").lower()
            else:
                assert r3.status_code == 200
                assert "dezactivat" in (r3.json().get("error", "") or "").lower()
            # Security analyze: returns 200 with error key
            r4 = admin.post(f"{BASE_URL}/api/admin/ai-security/analyze", timeout=30)
            assert r4.status_code == 200
            assert "dezactivat" in (r4.json().get("error", "") or "").lower()
        finally:
            # always re-enable
            self._set_enabled(admin, True)
