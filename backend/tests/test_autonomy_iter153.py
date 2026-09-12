"""Iteration 153 backend tests: Autonomy score + Journey Guardian re-audit loop."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read from frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PWD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PWD},
               timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


# ---- AUTONOMY SCORE ----

def test_repair_center_status_has_autonomy(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/status", timeout=45)
    assert r.status_code == 200
    data = r.json()
    assert "autonomy" in data, f"autonomy missing. keys={list(data.keys())}"
    a = data["autonomy"]
    assert "score" in a
    score = a["score"]
    assert isinstance(score, (int, float)), f"score type={type(score)}"
    assert 0 <= score <= 100
    assert "components" in a
    comps = a["components"]
    expected = {"auto_resolution", "autonomous_decisions", "cron_reliability",
                "journey_health", "self_healing_activity"}
    got = set(comps.keys()) if isinstance(comps, dict) else set(
        c.get("key") for c in comps
    )
    missing = expected - got
    assert not missing, f"Missing components: {missing}. Got: {got}"
    # each has score / weight / detail
    if isinstance(comps, dict):
        items = comps.values()
    else:
        items = comps
    for c in items:
        for k in ("score", "weight", "detail"):
            assert k in c, f"component missing '{k}': {c}"


def test_orchestrator_governance_has_autonomy_score(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/orchestrator/governance", timeout=45)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    snap = data.get("snapshot") or data
    assert "autonomy_score" in snap, f"autonomy_score missing. keys={list(snap.keys())}"


def test_ceo_briefing_has_ai_governance_autonomy(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ceo-briefing", timeout=45)
    assert r.status_code == 200
    data = r.json()
    # find item with key='ai_governance'
    items = data.get("items") or data.get("snapshot") or data.get("briefing") or []
    if isinstance(data, dict) and "snapshot" in data and isinstance(data["snapshot"], list):
        items = data["snapshot"]
    found = None
    def scan(obj):
        nonlocal found
        if found: return
        if isinstance(obj, dict):
            if obj.get("key") == "ai_governance":
                found = obj
                return
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
    scan(data)
    assert found is not None, f"ai_governance item missing. Top keys: {list(data.keys()) if isinstance(data, dict) else type(data)}"
    text_blob = str(found).lower()
    assert "autonomie" in text_blob, f"'autonomie' not in ai_governance item: {found}"


# ---- CLOSED LOOP: repair-center run -> guardian re-audit ----

def test_repair_run_triggers_guardian_reaudit(admin_session):
    # Kick off a run scoped to automation
    r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/run",
                           json={"domains": ["automation"]},
                           timeout=30)
    assert r.status_code in (200, 202), r.text[:300]
    body = r.json()
    assert body.get("started") is True or body.get("ok") is True, body

    # Poll for the new run to appear
    latest = None
    deadline = time.time() + 120
    initial_ts = None
    while time.time() < deadline:
        rr = admin_session.get(f"{BASE_URL}/api/admin/repair-center/runs?limit=1",
                               timeout=30)
        if rr.status_code == 200:
            j = rr.json()
            runs = (j.get("items") or j.get("runs")) if isinstance(j, dict) else j
            if runs:
                latest = runs[0]
                # detect completion: has journey_guardian OR status finished
                if latest.get("journey_guardian") is not None or latest.get("status") in ("done", "completed", "finished", "success"):
                    if latest.get("journey_guardian") is not None:
                        break
        time.sleep(3)
    assert latest is not None, "No repair run found"
    print(f"Latest run keys: {list(latest.keys())}")
    assert "journey_guardian" in latest, f"journey_guardian field missing from run. Keys={list(latest.keys())}"
    jg = latest["journey_guardian"]
    assert isinstance(jg, dict)
    for k in ("issues_found", "new_tasks", "auto_resolved"):
        assert k in jg, f"guardian result missing '{k}'. Got: {jg}"
