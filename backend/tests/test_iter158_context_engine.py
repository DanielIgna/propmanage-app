"""Iter 158 — AI Brain Context Awareness Engine (AIB-002) backend tests (HTTP, sync)."""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", "1!nasov01ADMIN")


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


def test_my_context_resolves(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/context?path=/client", timeout=30)
    assert r.status_code == 200
    c = r.json()
    assert c["user"]["email"] == "client@propmanage.io"
    assert c["user"]["role"] == "client"
    assert c["location"]["module"] == "client"
    assert c["location"]["known_route"] is True
    assert "client" in c["permissions"]["effective_guards"]
    assert 0 < c["permissions"]["accessible_endpoints"] < c["permissions"]["total_endpoints"]


def test_context_actions_filtered_by_role(client_session, admin_session):
    rc = client_session.get(f"{BASE_URL}/api/ai-brain/context?path=/client", timeout=30).json()
    ra = admin_session.get(f"{BASE_URL}/api/ai-brain/context?path=/admin", timeout=30).json()
    assert all(a["guard"] in ("public", "authenticated", "client") for a in rc["available_actions"])
    assert ra["permissions"]["accessible_endpoints"] > rc["permissions"]["accessible_endpoints"]


def test_navigation_record_and_history(client_session):
    for p in ("/client", "/marketplace", "/client"):
        r = client_session.post(f"{BASE_URL}/api/ai-brain/navigation", json={"path": p}, timeout=15)
        assert r.status_code == 200
    r = client_session.get(f"{BASE_URL}/api/ai-brain/navigation", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["total_events"] >= 3
    assert d["events"][0]["path"] == "/client"
    assert any(m["module"] == "client" for m in d["top_modules"])


def test_navigation_invalid_path(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/navigation", json={"path": "javascript:x"}, timeout=15)
    assert r.status_code == 400


def test_conversation_continuity(client_session):
    sid = f"test-{uuid.uuid4().hex[:8]}"
    r = client_session.post(f"{BASE_URL}/api/ai-brain/conversation",
                            json={"session_id": sid, "content": "Ce este Digital Twin?",
                                  "entities": [{"type": "module", "id": "digital-twin"}]}, timeout=15)
    assert r.status_code == 200
    r = client_session.post(f"{BASE_URL}/api/ai-brain/conversation",
                            json={"session_id": sid, "role": "assistant",
                                  "content": "Digital Twin este copia digitală a proprietății."}, timeout=15)
    assert r.status_code == 200
    d = client_session.get(f"{BASE_URL}/api/ai-brain/conversation/{sid}", timeout=15).json()
    assert len(d["messages"]) == 2
    assert d["context"]["last_question"] == "Ce este Digital Twin?"
    assert d["context"]["topic"].startswith("Ce este Digital Twin")
    assert {"type": "module", "id": "digital-twin"} in d["context"]["entities"]
    lst = client_session.get(f"{BASE_URL}/api/ai-brain/conversations", timeout=15).json()
    assert any(s["session_id"] == sid for s in lst["items"])


def test_conversation_isolation(client_session, admin_session):
    sid = f"test-iso-{uuid.uuid4().hex[:8]}"
    client_session.post(f"{BASE_URL}/api/ai-brain/conversation",
                        json={"session_id": sid, "content": "privat"}, timeout=15)
    r = admin_session.get(f"{BASE_URL}/api/ai-brain/conversation/{sid}", timeout=15)
    assert r.status_code == 404, "conversația altui user nu e accesibilă direct"


def test_admin_inspector(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/context/inspect",
                          params={"email": "client@propmanage.io", "path": "/client"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["context"]["user"]["role"] == "client"
    assert "navigation" in d and "conversations" in d
    assert d["navigation"]["total_events"] >= 1


def test_inspector_requires_admin(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/context/inspect",
                           params={"email": "client@propmanage.io"}, timeout=15)
    assert r.status_code in (401, 403)


def test_context_requires_auth():
    r = requests.get(f"{BASE_URL}/api/ai-brain/context", timeout=15)
    assert r.status_code in (401, 403)
