"""Rădăcini S8 — termeni legali (HTTP, backend pornit).

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s8_legal.py -q --noconftest

Testul 428 are nevoie de un cont care nu a acceptat încă termenii curenți (bază curată sau versiune nouă);
altfel se sare cu un mesaj explicit (acceptările sunt permanente, nu există endpoint de revocare).
"""
import os

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
R = f"{API}/radacini"
TIMEOUT = 20
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))


def _login(email, passwords):
    s = requests.Session()
    for pwd in passwords:
        if s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT).status_code == 200:
            return s
    pytest.skip(f"Login failed for {email}")


@pytest.fixture(scope="module")
def anon():
    return requests.Session()


@pytest.fixture(scope="module")
def specialist():
    return _login("specialist@propmanage.io", ["Spec123!"])


@pytest.fixture(scope="module")
def client():
    return _login("client@propmanage.io", ["Client123!"])


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


def _docs(anon):
    r = anon.get(f"{R}/legal/documents", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return {d["type"]: d for d in r.json()["items"]}


def test_documents_public(anon):
    docs = _docs(anon)
    assert set(docs) == {"terms", "privacy"}
    for d in docs.values():
        assert d["version"] and len(d["body"]) > 2000 and "în revizuire juridică" in d["body"]


def test_me_requires_login(anon):
    assert anon.get(f"{R}/legal/me", timeout=TIMEOUT).status_code in (401, 403)
    assert anon.post(f"{R}/legal/accept", json={"type": "terms", "version": "x"}, timeout=TIMEOUT).status_code in (401, 403)


def test_accept_wrong_version_and_type(anon, specialist):
    r = specialist.post(f"{R}/legal/accept", json={"type": "terms", "version": "1999-old"}, timeout=TIMEOUT)
    assert r.status_code == 409
    assert specialist.post(f"{R}/legal/accept", json={"type": "nope", "version": "x"}, timeout=TIMEOUT).status_code == 400


def test_428_then_accept_unlocks_action(anon, specialist):
    me = specialist.get(f"{R}/legal/me", timeout=TIMEOUT).json()
    if me["ok"]:
        pytest.skip("Contul de test a acceptat deja termenii curenți (acceptările sunt permanente).")
    r = specialist.post(f"{R}/parcels", json={}, timeout=TIMEOUT)
    assert r.status_code == 428, r.text
    assert r.json()["detail"]["code"] == "terms_required"
    docs = _docs(anon)
    for d in docs.values():
        r = specialist.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    # după acceptare, ruta nu mai întoarce 428 (corpul gol e respins de validare, 400)
    assert specialist.post(f"{R}/parcels", json={}, timeout=TIMEOUT).status_code != 428


def test_accept_idempotent_and_status(anon, client):
    docs = _docs(anon)
    for _ in range(2):
        for d in docs.values():
            r = client.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)
            assert r.status_code == 200, r.text
    me = client.get(f"{R}/legal/me", timeout=TIMEOUT).json()
    assert me["ok"] is True
    assert {(x["type"], x["version"]) for x in me["required"]} == {(d["type"], d["version"]) for d in docs.values()}
    assert len(me["accepted"]) == 2


def test_admin_acceptances(admin, client, specialist):
    docs = requests.get(f"{R}/legal/documents", timeout=TIMEOUT).json()["items"]
    ver = docs[0]["version"]
    r = admin.get(f"{R}/admin/legal/acceptances", params={"version": ver}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items and all(i["version"] == ver for i in items)
    assert all(i["ip"] is not None for i in items)
    assert client.get(f"{R}/admin/legal/acceptances", timeout=TIMEOUT).status_code == 403


def test_export_includes_acceptances(client):
    r = client.get(f"{R}/me/export", timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(a["type"] == "terms" for a in r.json()["legal_acceptances"])
