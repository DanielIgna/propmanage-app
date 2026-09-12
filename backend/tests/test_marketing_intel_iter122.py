"""GI-3 / Board 007 — Marketing Intelligence+ backend tests."""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_user():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def anon():
    return requests.Session()


# ----- Security -----
@pytest.mark.parametrize("path,method", [
    ("/api/admin/marketing-intel/latest", "GET"),
    ("/api/admin/marketing-intel/run", "POST"),
    ("/api/admin/marketing-intel/opportunity-queue", "GET"),
    ("/api/admin/marketing-intel/playbooks", "GET"),
])
def test_security_401(anon, path, method):
    r = anon.request(method, f"{BASE}{path}", timeout=15)
    assert r.status_code in (401, 403), f"{path} => {r.status_code}"


@pytest.mark.parametrize("path,method", [
    ("/api/admin/marketing-intel/latest", "GET"),
    ("/api/admin/marketing-intel/opportunity-queue", "GET"),
])
def test_security_403_for_client(client_user, path, method):
    r = client_user.request(method, f"{BASE}{path}", timeout=15)
    assert r.status_code == 403, f"{path} => {r.status_code}"


# ----- Run scan -----
def test_run_scan_shape(admin):
    r = admin.post(f"{BASE}/api/admin/marketing-intel/run", timeout=90)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for k in ("generated_at", "send_windows", "channels", "messages",
              "commercial", "recommendations", "queue_size", "queue_value_ron"):
        assert k in d, f"missing {k}"
    sw = d["send_windows"]
    assert "avg_conversion_pct" in sw
    assert "overall" in sw and "whatsapp" in sw
    for sub in ("overall", "whatsapp"):
        assert "text" in sw[sub] and "validation" in sw[sub]
    assert "channels" in d["channels"] and "best" in d["channels"]
    assert "campaigns" in d["messages"] and "best_campaign" in d["messages"] and "ab_winners" in d["messages"]
    com = d["commercial"]
    for k in ("top_revenue", "best_converting", "promote_now", "losing_clients"):
        assert k in com
    recs = d["recommendations"]
    assert isinstance(recs, list) and len(recs) >= 1
    for rec in recs:
        # Board 007: each rec MUST have motiv + încredere + impact + KPI
        for f in ("title", "reason", "confidence", "confidence_label",
                  "impact_estimate", "kpi", "category"):
            assert f in rec and rec[f] != "", f"reco missing {f}: {rec}"


def test_latest_persisted(admin):
    r = admin.get(f"{BASE}/api/admin/marketing-intel/latest", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "recommendations" in d and "send_windows" in d


# ----- Opportunity queue -----
def test_opportunity_queue(admin):
    r = admin.get(f"{BASE}/api/admin/marketing-intel/opportunity-queue", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert set(("items", "count", "total_value_ron")).issubset(d.keys())
    items = d["items"]
    assert isinstance(items, list)
    if items:
        prev = None
        for it in items:
            for f in ("type", "ref_id", "name", "probability_pct", "service",
                      "service_label", "value_ron", "urgency", "signals", "priority"):
                assert f in it, f"queue item missing {f}"
            assert it["type"] in ("opportunity", "lead")
            assert it["urgency"] in ("high", "medium", "low")
            if prev is not None:
                assert it["priority"] <= prev, "queue not sorted desc by priority"
            prev = it["priority"]
        # hot leads urgency=high check
        for it in items:
            if it["type"] == "lead" and it.get("lead_tier") == "hot":
                assert it["urgency"] == "high"


# ----- Playbook E2E -----
@pytest.fixture(scope="module")
def queue_item(admin):
    r = admin.get(f"{BASE}/api/admin/marketing-intel/opportunity-queue", timeout=30)
    items = r.json().get("items") or []
    if not items:
        pytest.skip("no queue items")
    return items[0]


@pytest.fixture(scope="module")
def generated_playbook(admin, queue_item):
    r = admin.post(f"{BASE}/api/admin/marketing-intel/playbook",
                   json={"target_type": queue_item["type"], "ref_id": queue_item["ref_id"]},
                   timeout=90)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_playbook_shape(generated_playbook):
    pb = generated_playbook
    for f in ("id", "why", "content", "ai_generated", "status"):
        assert f in pb
    assert pb["status"] == "generated"
    assert isinstance(pb["why"], list) and len(pb["why"]) >= 1
    c = pb["content"]
    for k in ("whatsapp_message", "email_subject", "email_body", "notification_text"):
        assert c.get(k), f"content missing {k}"


def test_playbook_decision_edited(admin, generated_playbook):
    pid = generated_playbook["id"]
    r = admin.post(f"{BASE}/api/admin/marketing-intel/playbook/{pid}/decision",
                   json={"action": "edited", "final_message": "test editat iter122"}, timeout=30)
    assert r.status_code == 200
    assert r.json().get("status") == "edited"


def test_playbook_decision_invalid(admin, generated_playbook):
    pid = generated_playbook["id"]
    r = admin.post(f"{BASE}/api/admin/marketing-intel/playbook/{pid}/decision",
                   json={"action": "bogus"}, timeout=15)
    assert r.status_code == 400


def test_playbook_not_found(admin):
    r = admin.post(f"{BASE}/api/admin/marketing-intel/playbook/nonexistent999/decision",
                   json={"action": "sent"}, timeout=15)
    assert r.status_code == 404


def test_playbook_target_invalid(admin):
    r = admin.post(f"{BASE}/api/admin/marketing-intel/playbook",
                   json={"target_type": "bogus", "ref_id": "x"}, timeout=15)
    assert r.status_code == 400


def test_playbook_ref_missing(admin):
    r = admin.post(f"{BASE}/api/admin/marketing-intel/playbook",
                   json={"target_type": "lead", "ref_id": "nonexistent_visitor_xxx"}, timeout=15)
    assert r.status_code == 404


def test_playbooks_list(admin, generated_playbook):
    r = admin.get(f"{BASE}/api/admin/marketing-intel/playbooks", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and "count" in d
    assert any(p.get("id") == generated_playbook["id"] for p in d["items"])


# ----- Regression -----
@pytest.mark.parametrize("path", [
    "/api/admin/lead-intel/stats",
    "/api/admin/growth-intel/latest",
    "/api/admin/command-center/feed",
    "/api/admin/ceo",
])
def test_regression(admin, path):
    r = admin.get(f"{BASE}{path}", timeout=60)
    assert r.status_code == 200, f"{path} => {r.status_code}"
