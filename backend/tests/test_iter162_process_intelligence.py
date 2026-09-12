"""Iter 162 — Process Intelligence Engine (AIB-006) backend tests (HTTP, sync)."""
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
def admin_session():
    return _login("admin@propmanage.io", "1!nasov01ADMIN")


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


def test_processes_build(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/ai-brain/processes/build", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 15, f"prea puține procese descoperite: {d}"
    assert d["by_kind"].get("business", 0) >= 5
    assert d["by_kind"].get("automated", 0) >= 5
    assert d["transitions"] > 20 and d["states"] > 30
    assert "specialist" in d["actors"] and "client" in d["actors"]


def test_processes_list_and_requests_process(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/processes", timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    req = next((p for p in items if p["id"] == "proc_requests"), None)
    assert req is not None, "procesul marketplace (requests) nu a fost descoperit"
    assert req["kind"] == "business"
    for s in ("open", "assigned", "in_progress", "completed"):
        assert s in req["states"], f"stare lipsă: {s}"
    assert "specialist" in req["actors"] and "client" in req["actors"]
    assert req["steps"], "pașii nu sunt ordonați"
    assert req["terminal_states"], "lipsesc stările terminale"


def test_process_detail_transitions(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/processes/proc_requests", timeout=30)
    assert r.status_code == 200
    p = r.json()
    assert p["transitions"], "lipsesc tranzițiile"
    t = p["transitions"][0]
    assert t["to"] and t["endpoint"]["method"] and t["endpoint"]["path"].startswith("/api")
    assert t["actor"]
    assert isinstance(p.get("stats"), dict) and "total" in p["stats"]
    assert "by_status" in p["stats"] and "abandon_points" in p["stats"]


def test_process_relations_exist(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/processes", timeout=30)
    items = r.json()["items"]
    rels = [rel for p in items for rel in p.get("relations") or []]
    assert rels, "nicio relație între procese descoperită"
    assert any(rel["rel"] in ("references", "co_writes") for rel in rels)


def test_process_detail_404(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/processes/proc_inexistent", timeout=15)
    assert r.status_code == 404


def test_admin_state_inspect(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/processes/proc_requests/state",
                          params={"email": "client@propmanage.io"}, timeout=30)
    assert r.status_code == 200
    st = r.json()
    assert st["found"] is True
    assert st["status"] in ("not_started", "in_progress", "completed")
    assert "steps" in st and "blockers" in st and "who_acts" in st
    if st["status"] != "not_started":
        assert st["current_state"] in st["process"]["steps"]
        assert isinstance(st["timeline"], list)


def test_my_process_state(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/process/state", params={"path": "/client"}, timeout=30)
    assert r.status_code == 200
    st = r.json()
    assert "found" in st
    if st["found"]:
        assert "process" in st and "blockers" in st


def test_process_state_requires_auth():
    r = requests.get(f"{BASE_URL}/api/ai-brain/process/state", timeout=15)
    assert r.status_code in (401, 403)


def test_mentor_includes_process(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor", params={"path": "/client"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "process" in d, "mentorul nu include starea procesului (AIB-006)"


def test_explain_process_grounded(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/process", json={"path": "/client"}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert d.get("explanation")
    assert "process_state" in d


def test_graph_has_process_nodes(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/search",
                          params={"q": "proc_requests", "kind": "process"}, timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(n["id"] == "process:proc_requests" for n in items), "graful nu conține nodurile de proces"
    rn = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/node",
                           params={"id": "process:proc_requests"}, timeout=30)
    assert rn.status_code == 200
    d = rn.json()
    rels = {e["rel"] for e in d["depends_on"] + d["used_by"]}
    assert "manages" in rels and "involves" in rels


def test_status_includes_processes(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/status", timeout=30)
    d = r.json()
    assert "process_intelligence" in d["capabilities"]
    assert d["registry"].get("processes", 0) >= 15


def test_processes_admin_only(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/processes", timeout=15)
    assert r.status_code in (401, 403)
