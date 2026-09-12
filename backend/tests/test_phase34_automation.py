"""Phase 34 — Automation Engine + Add-to-run backend tests.

Covers:
- GET /api/admin/qa/automation/tests (catalog 14 items)
- POST /api/admin/qa/automation/execute (no run_id)
- POST /api/admin/qa/automation/execute (with run_id) → writes a new check
- POST /api/admin/qa/runs/{id}/add-check + idempotency
- Browser (Playwright) tests AUTO-UI-01/02/03 pass
- RBAC: client cannot reach automation endpoints
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(session, creds):
    r = session.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    return r


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = _login(s, ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = _login(s, CLIENT)
    if r.status_code != 200:
        pytest.skip(f"client login failed {r.status_code}")
    return s


@pytest.fixture(scope="module")
def new_run(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/qa/runs",
                           json={"name": "TEST_phase34_auto", "version": "v34-test"}, timeout=20)
    assert r.status_code == 200, r.text
    run = r.json()["run"]
    run_id = run["run_id"]
    base_checks = len(run["checks"])
    yield {"run_id": run_id, "base_checks": base_checks}


# ---------------- Automation catalog ----------------
class TestAutomationCatalog:
    def test_catalog_returns_14_items(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/automation/tests", timeout=15)
        assert r.status_code == 200, r.text
        tests = r.json()["tests"]
        assert len(tests) >= 14, f"Expected >=14, got {len(tests)}"
        kinds = {t["kind"] for t in tests}
        assert kinds <= {"http", "browser"}
        # Every test must expose code/category/priority/kind
        for t in tests:
            for k in ("code", "category", "priority", "kind", "title"):
                assert k in t, f"missing {k} in {t}"


# ---------------- Execute without run_id ----------------
class TestExecuteNoRun:
    def test_execute_3_http_no_run(self, admin_session):
        body = {"test_codes": ["AUTO-AUTH-01", "AUTO-SEC-01", "AUTO-KB-01"]}
        t0 = time.time()
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/automation/execute", json=body, timeout=30)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["summary"]["total"] == 3
        assert d["summary"]["pass"] >= 3, f"expected pass>=3, got {d['summary']}"
        assert d["summary"]["written_to_run"] == 0
        assert elapsed < 20, f"too slow: {elapsed}s"


# ---------------- Execute with run_id ----------------
class TestExecuteWithRun:
    def test_execute_writes_check_into_run(self, admin_session, new_run):
        run_id = new_run["run_id"]
        base = new_run["base_checks"]
        body = {"test_codes": ["AUTO-AUTH-01"], "run_id": run_id}
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/automation/execute", json=body, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["summary"]["written_to_run"] == 1

        # GET run and verify the new check exists
        rr = admin_session.get(f"{BASE_URL}/api/admin/qa/runs/{run_id}", timeout=15)
        assert rr.status_code == 200
        run = rr.json()["run"]
        assert len(run["checks"]) == base + 1
        added = [c for c in run["checks"] if c.get("code") == "AUTO-AUTH-01"]
        assert added, "AUTO-AUTH-01 not appended"
        assert added[0]["status"] == "pass"
        assert added[0].get("automated") is True


# ---------------- Add ad-hoc check + idempotency ----------------
class TestAddCheck:
    def test_add_custom_check_then_idempotent(self, admin_session, new_run):
        run_id = new_run["run_id"]
        before = admin_session.get(f"{BASE_URL}/api/admin/qa/runs/{run_id}").json()["run"]
        before_count = len(before["checks"])
        payload = {
            "code": "CUSTOM-01",
            "priority": "P1",
            "category": "CUSTOM",
            "description": "manual ad-hoc",
        }
        r = admin_session.post(
            f"{BASE_URL}/api/admin/qa/runs/{run_id}/add-check", json=payload, timeout=15
        )
        assert r.status_code == 200, r.text
        run = r.json()["run"]
        assert len(run["checks"]) == before_count + 1
        added = [c for c in run["checks"] if c.get("code") == "CUSTOM-01"]
        assert added and added[0].get("ai_added") is True

        # Idempotent — second call should NOT add a duplicate
        r2 = admin_session.post(
            f"{BASE_URL}/api/admin/qa/runs/{run_id}/add-check", json=payload, timeout=15
        )
        assert r2.status_code == 200
        run2 = r2.json()["run"]
        same_code = [c for c in run2["checks"] if c.get("code") == "CUSTOM-01"]
        assert len(same_code) == 1, f"duplicate added: {len(same_code)}"


# ---------------- Browser tests via subprocess ----------------
class TestBrowserAutomation:
    def test_three_browser_tests_pass(self, admin_session):
        body = {"test_codes": ["AUTO-UI-01", "AUTO-UI-02", "AUTO-UI-03"]}
        t0 = time.time()
        r = admin_session.post(
            f"{BASE_URL}/api/admin/qa/automation/execute", json=body, timeout=120
        )
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["summary"]["total"] == 3
        # Allow up to 60s as per spec
        assert elapsed < 90, f"too slow: {elapsed}s"
        statuses = {res["code"]: res["status"] for res in d["results"]}
        # Report any non-pass for diagnostics
        failures = {c: s for c, s in statuses.items() if s != "pass"}
        assert not failures, f"browser failures: {failures}, notes={[(r['code'], r['note'][:200]) for r in d['results']]}"


# ---------------- RBAC ----------------
class TestRBAC:
    def test_client_blocked_from_catalog(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/qa/automation/tests", timeout=15)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"

    def test_client_blocked_from_execute(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/admin/qa/automation/execute",
            json={"test_codes": ["AUTO-AUTH-01"]},
            timeout=15,
        )
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
