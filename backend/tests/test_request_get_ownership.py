"""GET /api/requests/{req_id} participant authorization — closes the request GET IDOR.

Reuses the existing cookie-session + demo-account pattern (phase14 / property GET).
Authorization helper under test: _can_view_request_events (client_id, specialist_id, admin,
operator-if-twin-validator).
"""
import os
import uuid

import pytest
import requests

from tests.test_config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORDS,
    CLIENT_EMAIL,
    CLIENT_PASSWORD,
    OPERATOR_EMAIL,
    OPERATOR_PASSWORD,
    SPECIALIST_EMAIL,
    SPECIALIST_PASSWORD,
)

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"
SPEC2_EMAIL = "specialist2@propmanage.io"
SPEC2_PASSWORD = "Spec123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return s


def _login_admin():
    last = None
    for pw in ADMIN_PASSWORDS:
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": pw}, timeout=15)
        if r.status_code == 200:
            return s
        last = r
    raise AssertionError(f"admin login failed: {last.status_code} {last.text}")


def _register_other_client():
    s = requests.Session()
    email = f"TEST_req_get_{uuid.uuid4().hex[:8]}@propmanage.io"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "Other Client GET",
        "role": "client", "terms_accepted": True, "privacy_policy_accepted": True,
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    return s


@pytest.fixture(scope="module")
def assigned_request():
    client = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    spec = _login(SPECIALIST_EMAIL, SPECIALIST_PASSWORD)
    spec.post(f"{API}/auth/set-active-view", json={"view": "specialist"}, timeout=15)
    me = spec.get(f"{API}/auth/me", timeout=15).json()
    client_me = client.get(f"{API}/auth/me", timeout=15).json()
    listed = spec.get(f"{API}/requests", timeout=15).json()
    mine = [r for r in listed if r.get("specialist_id") == me.get("id") and r.get("client_id") == client_me.get("id")]
    if mine:
        return {"req_id": mine[0]["id"], "client": client, "spec": spec}

    props = client.get(f"{API}/properties", timeout=15)
    assert props.status_code == 200 and props.json(), props.text
    created = client.post(f"{API}/requests", json={
        "property_id": props.json()[0]["id"],
        "category": "plumbing",
        "title": "TEST_RequestGET_IDOR",
        "description": "ownership GET authorization",
        "priority": "normal",
        "budget_estimate": 120.0,
    }, timeout=15)
    assert created.status_code == 200, created.text
    req_id = created.json()["id"]
    me_spec = spec.get(f"{API}/auth/me", timeout=15).json()
    if int(me_spec.get("lead_credits") or 0) < 45 and float(me_spec.get("wallet_balance") or 0) < 45:
        spec.post(f"{API}/wallet/topup", params={"amount": 100}, timeout=15)
    off = spec.post(f"{API}/requests/{req_id}/offers", json={"message": "idor offer"}, timeout=15)
    assert off.status_code == 200, f"submit_offer failed: {off.status_code} {off.text[:200]}"
    acc = client.post(f"{API}/requests/{req_id}/offers/{off.json()['offer_id']}/accept", timeout=15)
    assert acc.status_code == 200, f"accept_offer failed: {acc.status_code} {acc.text[:200]}"
    return {"req_id": req_id, "client": client, "spec": spec}


def test_client_can_get_own_request(assigned_request):
    r = assigned_request["client"].get(f"{API}/requests/{assigned_request['req_id']}", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == assigned_request["req_id"]
    assert body.get("client_id")


def test_assigned_specialist_can_get_request(assigned_request):
    r = assigned_request["spec"].get(f"{API}/requests/{assigned_request['req_id']}", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == assigned_request["req_id"]
    me = assigned_request["spec"].get(f"{API}/auth/me", timeout=15).json()
    assert body.get("specialist_id") == me["id"]


def test_other_client_cannot_get_request(assigned_request):
    other = _register_other_client()
    r = other.get(f"{API}/requests/{assigned_request['req_id']}", timeout=15)
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"


def test_unassigned_specialist_cannot_get_request(assigned_request):
    other_spec = _login(SPEC2_EMAIL, SPEC2_PASSWORD)
    r = other_spec.get(f"{API}/requests/{assigned_request['req_id']}", timeout=15)
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"


def test_admin_and_operator_match_existing_request_policy(assigned_request):
    req_id = assigned_request["req_id"]

    admin = _login_admin()
    ra = admin.get(f"{API}/requests/{req_id}", timeout=15)
    assert ra.status_code == 200, f"admin GET: {ra.status_code} {ra.text[:200]}"
    assert ra.json()["id"] == req_id

    op = _login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    r_get = op.get(f"{API}/requests/{req_id}", timeout=15)
    r_tl = op.get(f"{API}/requests/{req_id}/timeline", timeout=15)
    assert r_get.status_code == r_tl.status_code, (
        f"operator GET {r_get.status_code} != timeline {r_tl.status_code} "
        f"(must match _can_view_request_events)"
    )
    if r_get.status_code == 200:
        assert r_get.json()["id"] == req_id


def test_unauthenticated_get_request_rejected(assigned_request):
    r = requests.get(f"{API}/requests/{assigned_request['req_id']}", timeout=15)
    assert r.status_code == 401, f"expected 401, got {r.status_code} {r.text[:200]}"


def test_nonexistent_and_invalid_request_return_404():
    client = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    missing = client.get(f"{API}/requests/000000000000000000000000", timeout=15)
    assert missing.status_code == 404, f"expected 404, got {missing.status_code} {missing.text[:200]}"
    invalid = client.get(f"{API}/requests/not-a-valid-id", timeout=15)
    assert invalid.status_code == 404, f"expected 404, got {invalid.status_code} {invalid.text[:200]}"
