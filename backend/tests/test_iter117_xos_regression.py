"""Iter 117 XOS 2026 redesign regression tests.

Covers backend endpoints touched by the redesign:
- POST /api/public/client-junior/request (public lead creation)
- GET /api/track/config (used by AssistantDock)
- GET /api/concierge/settings/public (client token)
- POST /api/cookies/consent
- GET /api/client/copilot (client token)
- GET /api/specialist/cockpit (specialist token)
- POST /api/auth/register (specialist ENTRY)
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

CLIENT = ("client@propmanage.io", "Client123!")
SPEC = ("specialist@propmanage.io", "Spec123!")


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _login(session, email, pwd):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    j = r.json()
    return j.get("access_token") or j.get("token")


@pytest.fixture(scope="module")
def client_token(s):
    return _login(s, *CLIENT)


@pytest.fixture(scope="module")
def spec_token(s):
    return _login(s, *SPEC)


# ---------------- Public endpoints ----------------
def test_track_config(s):
    r = s.get(f"{BASE_URL}/api/track/config")
    assert r.status_code == 200, r.text[:200]
    j = r.json()
    # AssistantDock uses whatsapp link + maybe ai flags
    assert isinstance(j, dict)


def test_client_junior_public_request(s):
    payload = {
        "name": f"TEST_XOS_{uuid.uuid4().hex[:6]}",
        "phone": "0722333444",
        "email": f"test_xos_{uuid.uuid4().hex[:6]}@example.com",
        "category": "zugraveli",
        "category_label": "Zugrăveli",
        "answers": {"where": "apartament", "size": "medium", "when": "asap"},
        "consent": True,
    }
    r = s.post(f"{BASE_URL}/api/public/client-junior/request", json=payload)
    assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
    j = r.json()
    # Should return an id/number identifying the request
    assert any(k in j for k in ("request_number", "number", "id", "lead_id", "request_id")), j


def test_cookies_consent(s):
    r = s.post(
        f"{BASE_URL}/api/cookies/consent",
        json={"accepted": True, "categories": ["necessary", "analytics"]},
    )
    assert r.status_code in (200, 201, 204), f"{r.status_code} {r.text[:200]}"


# ---------------- Auth-gated ----------------
def test_concierge_public_settings(s, client_token):
    r = s.get(
        f"{BASE_URL}/api/concierge/settings/public",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert r.status_code == 200, r.text[:200]


def test_client_copilot(s, client_token):
    r = s.get(
        f"{BASE_URL}/api/client/copilot",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert r.status_code == 200, r.text[:200]


def test_specialist_cockpit(s, spec_token):
    r = s.get(
        f"{BASE_URL}/api/specialist/cockpit",
        headers={"Authorization": f"Bearer {spec_token}"},
    )
    assert r.status_code == 200, r.text[:200]


def test_register_specialist_entry(s):
    email = f"TEST_xos_spec_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "Spec123!Test",
        "name": "Test XOS Spec",
        "role": "specialist",
        "terms_accepted": True,
        "privacy_policy_accepted": True,
        "phone": "0722555111",
        "service_categories": ["zugravit"],
        "coverage_zones": ["bucuresti"],
    }
    r = s.post(f"{BASE_URL}/api/auth/register", json=payload)
    assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
