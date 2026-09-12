"""Iter 157 — AI Brain Foundation & Discovery (AIB-001) backend tests (HTTP, sync)."""
import os

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}, timeout=15)
    assert r.status_code == 200
    return s


def test_discover_run(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/ai-brain/discover", timeout=120)
    assert r.status_code == 200
    d = r.json()
    c = d["counts"]
    assert c["routes"] > 100, "App.js are 130+ rute"
    assert c["apis"] > 500, "backend are sute de endpoint-uri"
    assert c["pages"] > 100
    assert c["services"] > 40
    assert c["roles"] >= 5
    assert c["modules"] > 10
    assert d["duration_ms"] < 30000


def test_status(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/status", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "active"
    assert "discovery" in d["capabilities"]
    assert d["last_run"] is not None
    assert d["registry"]["apis"] > 500
    assert d["guardians"]["platform_score"] is not None, "integrat cu Guardian Kernel"


@pytest.mark.parametrize("kind", ["modules", "routes", "pages", "components", "apis", "services", "roles", "menus"])
def test_registry_kinds(admin_session, kind):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/registry/{kind}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["kind"] == kind
    assert d["count"] > 0


def test_registry_query_filter(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/registry/apis?q=ai-brain", timeout=30)
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) >= 3, "endpoint-urile ai-brain trebuie să fie auto-descoperite"
    assert all("ai-brain" in str(e).lower() for e in data)


def test_registry_unknown_kind(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/registry/inexistent", timeout=15)
    assert r.status_code == 404


def test_requires_admin():
    r = requests.get(f"{BASE_URL}/api/admin/ai-brain/status", timeout=15)
    assert r.status_code in (401, 403)


def test_roles_discovered_from_db_and_code(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/registry/roles", timeout=30)
    data = r.json()["data"]
    assert "client" in data["all"] and "admin" in data["all"]
    assert "marketplace_partner" in data["all"]
    assert data["endpoint_guards"].get("admin", 0) > 100
