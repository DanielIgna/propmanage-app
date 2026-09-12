"""Iter 160 — AI Mentor (AIB-004) backend tests (HTTP, sync)."""
import os

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def specialist_session():
    return _login("specialist@propmanage.io", "Spec123!")


@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", "1!nasov01ADMIN")


def test_mentor_client_actions_real(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=/client", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["role"] == "client"
    assert 1 <= len(d["actions"]) <= 3, "maximum trei acțiuni"
    for a in d["actions"]:
        assert a["cta_path"].startswith("/"), "acțiuni reale cu destinație în aplicație"
        assert a["title"] and a["reason"]


def test_mentor_role_aware(client_session, specialist_session, admin_session):
    c = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=/client", timeout=30).json()
    s = specialist_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=/specialist", timeout=30).json()
    a = admin_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=/admin", timeout=30).json()
    assert {c["role"], s["role"], a["role"]} == {"client", "specialist", "admin"}
    c_ids = {x["id"] for x in c["actions"]}
    s_ids = {x["id"] for x in s["actions"]}
    a_ids = {x["id"] for x in a["actions"]}
    assert not (c_ids & a_ids), "clientul nu vede recomandări de admin"
    assert not (s_ids & c_ids), "specialistul nu vede recomandări de client"


def test_mentor_onboarding_once_then_replay(client_session):
    mod = f"/marketplace"
    r1 = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path={mod}", timeout=30).json()
    r2 = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path={mod}", timeout=30).json()
    assert r2["onboarding"]["show"] is False, "onboarding-ul se arată o singură dată"
    r3 = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path={mod}&replay=true", timeout=30).json()
    assert r3["onboarding"]["show"] is True, "reluabil manual"


def test_mentor_include_guide_reuses_explainability(client_session):
    r = client_session.get(
        f"{BASE_URL}/api/ai-brain/mentor?path=/client&replay=true&include_guide=true", timeout=90).json()
    g = r["onboarding"]["guide"]
    assert g and len(g["explanation"]) > 200
    assert g["cached"] is True, "ghidul reutilizează cache-ul Explainability din AIB-003"


def test_mentor_tips_stuck_detection(client_session):
    for _ in range(5):
        client_session.post(f"{BASE_URL}/api/ai-brain/navigation", json={"path": "/house-health"}, timeout=15)
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=/house-health", timeout=30).json()
    assert any(t["kind"] == "stuck_loop" for t in r["tips"]), "detectează revenirea repetată pe aceeași pagină"


def test_smart_empty_state(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/mentor/empty-state",
                            json={"path": "/client", "resource": "requests"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "Nu ai creat" in d["reason"]
    assert d["cta_path"].startswith("/")
    assert d["next_step"]


def test_mentor_requires_auth():
    r = requests.get(f"{BASE_URL}/api/ai-brain/mentor?path=/client", timeout=15)
    assert r.status_code in (401, 403)


def test_mentor_invalid_path(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=xx", timeout=15)
    assert r.status_code == 400
