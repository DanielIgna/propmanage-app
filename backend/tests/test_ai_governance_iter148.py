"""PM-AI-003 Governance backend tests (iter 148)"""
import os
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
PID = "smoke_fail_to_qa"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module", autouse=True)
def restore_level(admin_session):
    yield
    # Always restore to level 4 at end
    admin_session.post(f"{BASE}/api/admin/orchestrator/playbooks/{PID}/authority", json={"level": 4}, timeout=15)


def test_governance_endpoint_shape(admin_session):
    r = admin_session.get(f"{BASE}/api/admin/orchestrator/governance", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "levels" in data
    assert set(data["levels"].keys()) >= {"1", "2", "3", "4", "5"} or set(map(int, data["levels"].keys() if all(isinstance(k, str) for k in data["levels"].keys()) else data["levels"].keys())) >= {1,2,3,4,5}
    assert "playbooks" in data and isinstance(data["playbooks"], list)
    for pb in data["playbooks"]:
        assert "authority_level" in pb
        assert "confidence" in pb
        assert "confidence_runs" in pb
        assert "enabled" in pb
    snap = data["snapshot"]
    for k in ["decisions_24h", "executed_24h", "recommended_24h", "avg_confidence", "self_healing_events_7d"]:
        assert k in snap, f"missing snapshot key {k}"


def test_authority_invalid_level_400(admin_session):
    for bad in [0, 6, "abc", None]:
        r = admin_session.post(f"{BASE}/api/admin/orchestrator/playbooks/{PID}/authority", json={"level": bad}, timeout=15)
        assert r.status_code == 400, f"expected 400 for level={bad}, got {r.status_code}"


def test_authority_level2_recommend_flow(admin_session):
    # Set to level 2 (recommend)
    r = admin_session.post(f"{BASE}/api/admin/orchestrator/playbooks/{PID}/authority", json={"level": 2}, timeout=15)
    assert r.status_code == 200
    assert r.json()["authority_level"] == 2

    r = admin_session.post(f"{BASE}/api/admin/orchestrator/simulate/smoke_fail", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    ledger = data.get("ledger") or {}
    assert ledger.get("outcome") == "recommended", f"expected outcome=recommended got {ledger.get('outcome')} / full {data}"
    assert ledger.get("execution_mode") == "recommend", f"expected execution_mode=recommend got {ledger.get('execution_mode')}"


def test_authority_level4_execute_flow(admin_session):
    r = admin_session.post(f"{BASE}/api/admin/orchestrator/playbooks/{PID}/authority", json={"level": 4}, timeout=15)
    assert r.status_code == 200

    r = admin_session.post(f"{BASE}/api/admin/orchestrator/simulate/smoke_fail", timeout=30)
    assert r.status_code == 200
    ledger = r.json().get("ledger") or {}
    assert ledger.get("outcome") == "auto_resolved", f"got {ledger}"
    assert ledger.get("execution_mode") == "execute"


def test_decisions_memory_populated(admin_session):
    r = admin_session.get(f"{BASE}/api/admin/orchestrator/decisions?limit=20", timeout=15)
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    assert isinstance(items, list) and len(items) >= 2
    it = items[0]
    for key in ("decided", "outcome", "authority_level", "confidence"):
        assert key in it, f"decision missing {key}: {it}"


def test_watchdog_tick(admin_session):
    r = admin_session.post(f"{BASE}/api/admin/orchestrator/watchdog-tick", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "jobs_checked" in data
    assert data["jobs_checked"] > 50, f"expected >50, got {data['jobs_checked']}"
    for key in ("healed", "failing_jobs", "stuck_retries"):
        assert key in data, f"missing {key}"


def test_decision_review(admin_session):
    r = admin_session.post(f"{BASE}/api/admin/orchestrator/decision-review", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "decisions_reviewed" in data
    assert "downgrades" in data


def test_ceo_briefing_has_ai_governance(admin_session):
    r = admin_session.get(f"{BASE}/api/admin/ceo-briefing", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "ai_governance" in data, f"missing ai_governance key. keys={list(data.keys())}"
    snapshot = data.get("snapshot") or []
    keys_present = [i.get("key") for i in snapshot if isinstance(i, dict)]
    assert "ai_governance" in keys_present, f"snapshot missing ai_governance item: keys={keys_present}"
