"""Iter 159 — AI Brain Explainability Engine (AIB-003) backend tests (HTTP, sync)."""
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
def admin_session():
    return _login("admin@propmanage.io", "1!nasov01ADMIN")


def test_explain_page_grounded(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/page",
                            json={"path": "/client"}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert len(d["explanation"]) > 300, "explicație substanțială, nu generică"
    assert d["grounded_on"]["component"] == "ClientDashboardV2", "Context First: componenta reală a rutei"
    assert "##" in d["explanation"], "structură Markdown cu secțiuni"


def test_explain_page_cache(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/page",
                            json={"path": "/client"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["cached"] is True, "a doua cerere identică vine din cache (cost zero)"


def test_explain_page_role_scoped_cache(admin_session):
    # Cache-ul e per rol — adminul pe aceeași rută NU primește explicația clientului necesar
    r = admin_session.post(f"{BASE_URL}/api/ai-brain/explain/page",
                           json={"path": "/admin/ai-brain"}, timeout=90)
    assert r.status_code == 200
    assert r.json()["grounded_on"]["component"] == "AIBrainPage"


def test_explain_component(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/ai-brain/explain/component",
                           json={"path": "/admin/ai-brain", "component": "ai-brain-discover-btn"},
                           timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert d["found_in"] and "AIBrainPage" in d["found_in"], "grounding pe fișierul sursă real"
    assert len(d["explanation"]) > 100


def test_explain_process(client_session):
    # generează traseu de navigare real întâi
    for p in ("/client", "/marketplace"):
        client_session.post(f"{BASE_URL}/api/ai-brain/navigation", json={"path": p}, timeout=15)
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/process",
                            json={"path": "/marketplace"}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert len(d["explanation"]) > 100
    assert isinstance(d["trail"], list)


def test_explain_requires_auth():
    r = requests.post(f"{BASE_URL}/api/ai-brain/explain/page", json={"path": "/client"}, timeout=15)
    assert r.status_code in (401, 403)


def test_explain_invalid_path(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/page", json={"path": "x"}, timeout=15)
    assert r.status_code == 400
