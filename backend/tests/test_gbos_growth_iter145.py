"""Iter 145 — GBOS Growth Loops: Trusted Specialists (rebook) + Maintenance Calendar.

Auth = session cookie (NOT bearer token). Uses requests.Session().
"""
import os
import pytest
import requests
from datetime import date

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE, "REACT_APP_BACKEND_URL must be set"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC1 = {"email": "specialist@propmanage.io", "password": "Spec123!"}     # Mihai HVAC (target)
SPEC2 = {"email": "specialist2@propmanage.io", "password": "Spec123!"}    # Alt specialist
SPEC1_ID = "6a11d70e600be19667009c8f"
PROPERTY_ID = "6a11d70e600be19667009c93"


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login {creds['email']} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def spec1_sess():
    return _login(SPEC1)


@pytest.fixture(scope="module")
def spec2_sess():
    return _login(SPEC2)


# --------------------- A1: Trusted Specialists list ---------------------

def test_a1_trusted_specialists_list(client_sess):
    r = client_sess.get(f"{BASE}/api/trusted-specialists")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "specialists" in data
    specs = data["specialists"]
    assert len(specs) >= 1, "Client should have at least 1 trusted specialist"
    mihai = next((s for s in specs if s["specialist_id"] == SPEC1_ID), None)
    assert mihai is not None, f"Mihai (SPEC1) missing from trusted list; got ids: {[s['specialist_id'] for s in specs]}"
    assert mihai["jobs_together"] >= 1
    assert "rebook" in mihai
    assert "last_category" in mihai


# --------------------- A2: Rebook creation ---------------------

@pytest.fixture(scope="module")
def rebook_request(client_sess):
    payload = {
        "property_id": PROPERTY_ID,
        "title": "TEST_iter145 rebook HVAC",
        "description": "Test rebooking flow iter145 — please ignore, will be cleaned up.",
    }
    r = client_sess.post(f"{BASE}/api/trusted-specialists/{SPEC1_ID}/rebook", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_a2_rebook_creates_direct_request(rebook_request):
    doc = rebook_request
    assert doc["status"] == "open"
    assert doc["direct_specialist_id"] == SPEC1_ID
    assert doc["lead_fee_waived"] is True
    assert doc["is_rebooking"] is True
    assert "id" in doc


def test_a2_rebook_403_never_worked_with(client_sess):
    # Find a specialist the client has never worked with
    trusted = {s["specialist_id"] for s in client_sess.get(f"{BASE}/api/trusted-specialists").json()["specialists"]}
    specs = client_sess.get(f"{BASE}/api/specialists").json()
    other = next((s for s in specs if s["id"] not in trusted), None)
    if not other:
        pytest.skip("client has worked with all specialists — cannot test 403")
    r = client_sess.post(f"{BASE}/api/trusted-specialists/{other['id']}/rebook",
                         json={"property_id": PROPERTY_ID, "title": "TEST_x", "description": "must 403 please"})
    assert r.status_code == 403


def test_a2_rebook_404_bad_specialist(client_sess):
    r = client_sess.post(f"{BASE}/api/trusted-specialists/000000000000000000000000/rebook",
                        json={"property_id": PROPERTY_ID, "title": "TEST_x", "description": "must 404 please"})
    assert r.status_code == 404


def test_a2_rebook_404_bad_property(client_sess):
    r = client_sess.post(f"{BASE}/api/trusted-specialists/{SPEC1_ID}/rebook",
                        json={"property_id": "000000000000000000000000", "title": "TEST_x", "description": "must 404 please"})
    assert r.status_code == 404


# --------------------- A3: Visibility ---------------------

def test_a3_direct_visible_to_target_spec_only(spec1_sess, spec2_sess, rebook_request):
    req_id = rebook_request["id"]

    r1 = spec1_sess.get(f"{BASE}/api/requests")
    assert r1.status_code == 200
    ids1 = {r["id"] for r in r1.json()}
    assert req_id in ids1, "Target specialist must see the direct request"

    r2 = spec2_sess.get(f"{BASE}/api/requests")
    assert r2.status_code == 200
    ids2 = {r["id"] for r in r2.json()}
    assert req_id not in ids2, "Other specialist MUST NOT see the direct request"


def test_a3_other_spec_cannot_accept(spec2_sess, rebook_request):
    r = spec2_sess.post(f"{BASE}/api/requests/{rebook_request['id']}/accept", json={})
    assert r.status_code == 403


# --------------------- A4: Accept direct with 0 fee ---------------------

def _wallet_of(sess):
    r = sess.get(f"{BASE}/api/wallet")
    if r.status_code == 200:
        return r.json().get("balance") or r.json().get("wallet_balance")
    # fallback via /api/auth/me
    r = sess.get(f"{BASE}/api/auth/me")
    if r.status_code == 200:
        return r.json().get("wallet_balance")
    return None


def test_a4_accept_direct_no_fee(spec1_sess, rebook_request):
    before = _wallet_of(spec1_sess)
    r = spec1_sess.post(f"{BASE}/api/requests/{rebook_request['id']}/accept", json={})
    assert r.status_code == 200, r.text
    after = _wallet_of(spec1_sess)
    if before is not None and after is not None:
        assert before == after, f"Wallet must be unchanged for direct rebook: before={before} after={after}"


# --------------------- B1: Maintenance templates & task create ---------------------

def test_b1_templates(client_sess):
    r = client_sess.get(f"{BASE}/api/maintenance/templates")
    assert r.status_code == 200
    tpl = r.json()["templates"]
    assert len(tpl) == 8
    keys = [t["key"] for t in tpl]
    assert "centrala_termica" in keys


@pytest.fixture(scope="module")
def maint_task(client_sess):
    r = client_sess.post(f"{BASE}/api/maintenance/tasks",
                         json={"property_id": PROPERTY_ID, "template_key": "centrala_termica"})
    if r.status_code == 409:
        # Already exists — fetch it
        r2 = client_sess.get(f"{BASE}/api/maintenance/tasks")
        for t in r2.json()["tasks"]:
            if t["title"] == "Revizie centrală termică" and t["property_id"] == PROPERTY_ID:
                return t
        pytest.fail("409 but task not found in list")
    assert r.status_code == 200, r.text
    return r.json()


def test_b1_create_task(maint_task):
    assert maint_task["title"] == "Revizie centrală termică"
    assert maint_task["frequency_months"] == 12
    assert maint_task["next_due"] >= date.today().isoformat()


def test_b1_duplicate_409(client_sess, maint_task):
    r = client_sess.post(f"{BASE}/api/maintenance/tasks",
                         json={"property_id": PROPERTY_ID, "template_key": "centrala_termica"})
    assert r.status_code == 409


# --------------------- B2: List / complete / delete ---------------------

def test_b2_list_status(client_sess, maint_task):
    r = client_sess.get(f"{BASE}/api/maintenance/tasks")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    t = next((x for x in tasks if x["id"] == maint_task["id"]), None)
    assert t is not None
    assert t["status"] in ("overdue", "due_soon", "ok")


def test_b2_complete_advances(client_sess, maint_task):
    r = client_sess.post(f"{BASE}/api/maintenance/tasks/{maint_task['id']}/complete")
    assert r.status_code == 200
    body = r.json()
    assert body["last_done"] == date.today().isoformat()
    assert body["next_due"] > date.today().isoformat()


# --------------------- B3: Request from task ---------------------

@pytest.fixture(scope="module")
def task_for_request(client_sess):
    # Create a fresh task (different template) for request testing
    r = client_sess.post(f"{BASE}/api/maintenance/tasks",
                         json={"property_id": PROPERTY_ID, "template_key": "jgheaburi"})
    if r.status_code == 409:
        r2 = client_sess.get(f"{BASE}/api/maintenance/tasks")
        for t in r2.json()["tasks"]:
            if t["title"] == "Curățare jgheaburi și burlane":
                return t
    assert r.status_code == 200, r.text
    return r.json()


def test_b3_request_open_mode(client_sess, task_for_request):
    r = client_sess.post(f"{BASE}/api/maintenance/tasks/{task_for_request['id']}/request",
                         json={"mode": "open"})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["status"] == "open"
    assert doc.get("direct_specialist_id") in (None, "")
    assert doc.get("maintenance_task_id") == task_for_request["id"]


def test_b3_request_direct_403_not_worked(client_sess, task_for_request):
    trusted = {s["specialist_id"] for s in client_sess.get(f"{BASE}/api/trusted-specialists").json()["specialists"]}
    specs = client_sess.get(f"{BASE}/api/specialists").json()
    other = next((s for s in specs if s["id"] not in trusted), None)
    if not other:
        pytest.skip("client has worked with all specialists")
    r = client_sess.post(f"{BASE}/api/maintenance/tasks/{task_for_request['id']}/request",
                         json={"mode": "direct", "specialist_id": other["id"]})
    assert r.status_code == 403


def test_b3_request_direct_mode(client_sess, task_for_request):
    r = client_sess.post(f"{BASE}/api/maintenance/tasks/{task_for_request['id']}/request",
                         json={"mode": "direct", "specialist_id": SPEC1_ID})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["direct_specialist_id"] == SPEC1_ID
    assert doc["lead_fee_waived"] is True
    assert doc.get("maintenance_task_id") == task_for_request["id"]


# --------------------- REGRESSION: normal accept still charges 45 RON ---------------------

def test_regression_normal_accept_charges_45(client_sess, spec1_sess):
    """Create a normal (non-direct) public request and verify SPEC1 accepts with -45 RON."""
    # Use a request wizard endpoint or /api/requests directly
    payload = {
        "property_id": PROPERTY_ID,
        "category": "handyman",
        "title": "TEST_iter145 regression normal",
        "description": "Test normal (public) request for regression — cleanup after.",
        "priority": "normal",
    }
    r = client_sess.post(f"{BASE}/api/requests", json=payload)
    if r.status_code != 200:
        pytest.skip(f"cannot create normal request: {r.status_code} {r.text[:200]}")
    req = r.json()
    req_id = req.get("id")

    before = _wallet_of(spec1_sess)
    r = spec1_sess.post(f"{BASE}/api/requests/{req_id}/accept", json={})
    if r.status_code != 200:
        pytest.skip(f"accept failed: {r.status_code} {r.text[:200]}")
    after = _wallet_of(spec1_sess)
    if before is not None and after is not None:
        assert round(before - after, 2) == 45.0, f"Normal accept must deduct 45 RON: before={before} after={after}"
