"""GET /api/properties/{prop_id} ownership — closes the property GET IDOR.

Reuses the existing cookie-session + demo-account pattern (phase4 / CX-2).
"""
import os
import uuid

import requests

from tests.test_config import (
    ADMIN_EMAIL,
    ADMIN_PASSWORDS,
    CLIENT_EMAIL,
    CLIENT_PASSWORD,
    OPERATOR_EMAIL,
    OPERATOR_PASSWORD,
)

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"


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
    email = f"TEST_prop_get_{uuid.uuid4().hex[:8]}@propmanage.io"
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "Other Client GET",
        "role": "client", "terms_accepted": True, "privacy_policy_accepted": True,
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    return s


def _owner_property_id(owner):
    listed = owner.get(f"{API}/properties", timeout=15)
    assert listed.status_code == 200, listed.text
    props = listed.json()
    assert props, "owner has no properties"
    return props[0]["id"]


def test_owner_can_get_own_property():
    owner = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    prop_id = _owner_property_id(owner)
    r = owner.get(f"{API}/properties/{prop_id}", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == prop_id
    assert "address" in body or "name" in body


def test_other_authenticated_user_cannot_get_property():
    owner = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    prop_id = _owner_property_id(owner)
    other = _register_other_client()
    r = other.get(f"{API}/properties/{prop_id}", timeout=15)
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"


def test_admin_and_operator_can_get_property():
    owner = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    prop_id = _owner_property_id(owner)

    admin = _login_admin()
    ra = admin.get(f"{API}/properties/{prop_id}", timeout=15)
    assert ra.status_code == 200, f"admin GET: {ra.status_code} {ra.text[:200]}"
    assert ra.json()["id"] == prop_id

    op = _login(OPERATOR_EMAIL, OPERATOR_PASSWORD)
    ro = op.get(f"{API}/properties/{prop_id}", timeout=15)
    assert ro.status_code == 200, f"operator GET: {ro.status_code} {ro.text[:200]}"
    assert ro.json()["id"] == prop_id


def test_unauthenticated_get_property_rejected():
    owner = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    prop_id = _owner_property_id(owner)
    r = requests.get(f"{API}/properties/{prop_id}", timeout=15)
    assert r.status_code == 401, f"expected 401, got {r.status_code} {r.text[:200]}"


def test_nonexistent_property_returns_404():
    owner = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    r = owner.get(f"{API}/properties/000000000000000000000000", timeout=15)
    assert r.status_code == 404, f"expected 404, got {r.status_code} {r.text[:200]}"
