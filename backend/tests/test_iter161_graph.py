"""Iter 161 — Knowledge Intelligence Engine (AIB-005) backend tests (HTTP, sync)."""
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


def test_graph_build(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/ai-brain/graph/build", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert d["nodes"] > 1500 and d["edges"] > 3000
    for kind in ("module", "route", "component", "api", "service", "entity", "role", "process"):
        assert d["by_kind"].get(kind, 0) > 0, f"lipsesc nodurile de tip {kind}"


def test_graph_overview(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/overview", timeout=30)
    d = r.json()
    assert d["nodes"] > 1500
    for rel in ("renders", "in_module", "links_to", "calls", "requires_role", "defined_in", "touches", "triggers"):
        assert d["by_rel"].get(rel, 0) > 0, f"lipsește relația {rel}"


def test_dependency_engine(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/node",
                          params={"id": "entity:twins"}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["degree"]["in"] > 5, "colecția twins e folosită de multe servicii"
    assert all(e["rel"] == "touches" for e in d["used_by"][:5])


def test_impact_engine(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/impact",
                          params={"id": "entity:properties"}, timeout=30)
    d = r.json()
    assert d["total_affected"] > 20, "modificarea colecției properties afectează multe noduri"
    assert "service" in d["by_kind"] and "api" in d["by_kind"]


def test_cross_navigation(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/modules/digital-twin/related", timeout=30)
    related = {x["module"] for x in r.json()["related"]}
    assert len(related) >= 3
    assert "house-health" in related or "client" in related or "admin" in related


def test_mentor_includes_related_modules(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor?path=/client", timeout=30).json()
    assert isinstance(r.get("related_modules"), list)
    mods = {m["module"] for m in r["related_modules"]}
    assert "admin" not in mods, "hub-urile generice sunt excluse pentru utilizatori"


def test_explain_relationship_grounded(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/relationship",
                            json={"question": "De ce există House Health și cum se leagă de Digital Twin?"},
                            timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert len(d["explanation"]) > 200
    assert any("house" in n.lower() or "twin" in n.lower() for n in d["matched_nodes"])


def test_explain_relationship_cache(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/explain/relationship",
                            json={"question": "De ce există House Health și cum se leagă de Digital Twin?"},
                            timeout=30)
    assert r.json()["cached"] is True


def test_graph_search_and_404(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/search",
                          params={"q": "house", "kind": "module"}, timeout=15)
    assert any("house" in n["id"] for n in r.json()["items"])
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/node",
                          params={"id": "module:inexistent-xyz"}, timeout=15)
    assert r.status_code == 404


def test_graph_requires_admin(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/graph/overview", timeout=15)
    assert r.status_code in (401, 403)
