"""Backend tests for Health Repair Engine (PM-AI-REPAIR-001) — iteration 149."""
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


# --- Auth guard ---
def test_status_requires_auth(anon_session):
    r = anon_session.get(f"{BASE_URL}/api/admin/repair-center/status", timeout=30)
    assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


def test_run_requires_auth(anon_session):
    r = anon_session.post(f"{BASE_URL}/api/admin/repair-center/run", json={}, timeout=30)
    assert r.status_code in (401, 403)


def test_runs_requires_auth(anon_session):
    r = anon_session.get(f"{BASE_URL}/api/admin/repair-center/runs", timeout=30)
    assert r.status_code in (401, 403)


# --- Status ---
def test_status_domains_and_last_run(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/status", timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "domains" in data and "last_run" in data and "runs_total" in data
    domain_keys = {d["domain"] for d in data["domains"]}
    expected = {"revenue", "operations", "growth", "marketplace", "customer_trust",
                "product", "knowledge", "ux", "automation", "ai_learning", "technical_debt"}
    missing = expected - domain_keys
    assert not missing, f"missing domains: {missing}. got: {domain_keys}"
    for d in data["domains"]:
        assert "score" in d and "warning_threshold" in d and "has_engine" in d
        assert d["has_engine"] is True
    assert data["runs_total"] >= 1


# --- Runs history ---
def test_runs_history(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/runs?limit=5", timeout=30)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data and isinstance(data["items"], list)
    assert len(data["items"]) >= 1
    first = data["items"][0]
    assert "results" in first and "ts" in first
    # Existing full run should have 11 domain results
    full_runs = [it for it in data["items"] if len(it.get("results", [])) >= 11]
    assert full_runs, "expected at least one full 11-domain run in history"


# --- Validation ---
def test_run_invalid_domain(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/run",
                           json={"domains": ["inexistent"]}, timeout=30)
    assert r.status_code == 400


def test_run_empty_domains(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/run",
                           json={"domains": []}, timeout=30)
    assert r.status_code == 400


# --- Run technical_debt cycle (background) ---
def test_run_technical_debt_cycle(admin_session):
    # snapshot latest run ts before triggering
    r0 = admin_session.get(f"{BASE_URL}/api/admin/repair-center/runs?limit=1", timeout=30)
    assert r0.status_code == 200
    prev_ts = r0.json()["items"][0]["ts"] if r0.json()["items"] else None

    r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/run",
                           json={"domains": ["technical_debt"]}, timeout=30)
    assert r.status_code == 200, r.text
    assert r.json().get("started") is True

    # poll for new run
    deadline = time.time() + 90
    new_run = None
    while time.time() < deadline:
        time.sleep(5)
        rr = admin_session.get(f"{BASE_URL}/api/admin/repair-center/runs?limit=1", timeout=30)
        if rr.status_code != 200:
            continue
        items = rr.json().get("items", [])
        if items and items[0]["ts"] != prev_ts:
            new_run = items[0]
            break

    assert new_run is not None, "no new run appeared within 90s"
    assert str(new_run.get("trigger", "")).startswith("manual:"), f"trigger={new_run.get('trigger')}"
    results = new_run.get("results", [])
    assert len(results) >= 1
    td = next((x for x in results if x["domain"] == "technical_debt"), None)
    assert td is not None, f"technical_debt not in results: {[r['domain'] for r in results]}"
    assert "problems" in td and "actions" in td
    assert "score_before" in td and "score_after" in td and "delta" in td


# --- Real side-effects ---
def test_case_library_has_repair_engine_drafts(admin_session):
    # via orchestrator ledger check + case_library via any admin endpoint if exists
    # We'll validate ledger entry existence
    r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/ledger?limit=200", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or data.get("entries") or data
    if isinstance(items, dict):
        items = items.get("items", [])
    found = any(
        (it.get("playbook_id") == "health_repair_engine") or
        (it.get("playbook") == "health_repair_engine")
        for it in items
    )
    assert found, "no orchestrator ledger entry with playbook_id=health_repair_engine"
