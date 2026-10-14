"""Rădăcini S9-A — teste HTTP: asociații, registru, import CSV, participare, revendicări.

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s9a.py -q --noconftest

admin = super-admin (manager), specialist = utilizator care revendică, client = utilizator fără legătură.
Asociația creată poartă numele TEST-RAD-<hex> (nu există rută de ștergere; purja o curăță după nume).
"""
import io
import os
import uuid

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
CLIENT = ("client@propmanage.io", ["Client123!"])
SPECIALIST = ("specialist@propmanage.io", ["Spec123!"])
R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20
S: dict = {}

CSV = (
    "code,name,shares,sources,status,locality\n"
    "M001,Ion Test,0.5,Nr 1 = 0.5,unknown,Ciunca\n"
    "M002,Maria Test,1/4,Nr 2 = 0.25|Nr 3 = 0,unknown,Ciunca\n"
    "M003,Vasile Test,0.25,,unknown,Ciunca\n"
    "M004,Fara Cote,abc,,unknown,Ciunca\n"
    "M001,Duplicat,0.1,,unknown,Ciunca\n"
)


def _accept_terms(s):
    docs = s.get(f"{R}/legal/documents", timeout=TIMEOUT).json().get("items", [])
    for d in docs:
        s.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)


def _login(email, passwords):
    s = requests.Session()
    last = None
    for pwd in passwords:
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT)
        last = r.status_code
        if r.status_code == 200:
            _accept_terms(s)
            return s
    pytest.skip(f"Login failed for {email} (last={last})")


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


@pytest.fixture(scope="module")
def spec():
    return _login(*SPECIALIST)


@pytest.fixture(scope="module")
def client():
    return _login(*CLIENT)


def _err(r, code):
    assert r.status_code == code, f"expected {code}, got {r.status_code}: {r.text[:300]}"


def test_01_create_and_import(admin):
    r = admin.post(f"{R}/assoc", json={
        "name": f"{TAG} Composesorat", "type": "composesorat", "localities": ["Ciunca"],
        "patrimony": [{"cf": "1", "area_ha": 12.5, "category": "pășune"}]}, timeout=TIMEOUT)
    _err(r, 201)
    S["aid"] = r.json()["association"]["id"]
    r = admin.post(f"{R}/assoc/{S['aid']}/members/import",
                   files={"file": ("reg.csv", io.BytesIO(CSV.encode()), "text/csv")}, timeout=TIMEOUT)
    _err(r, 200)
    body = r.json()
    assert body["imported"] == 3
    assert len(body["errors"]) == 2 and all("line" in e for e in body["errors"])


def test_02_public_and_registry_access(admin, spec):
    a = S["aid"]
    r = requests.get(f"{R}/assoc", timeout=TIMEOUT)
    _err(r, 200)
    mine = [x for x in r.json()["items"] if x["id"] == a]
    assert mine and mine[0]["members_count"] == 3 and mine[0]["total_area_ha"] == 12.5
    assert "transparency_score" in mine[0]
    pub = requests.get(f"{R}/assoc/{a}", timeout=TIMEOUT)
    _err(pub, 200)
    assert pub.json()["my"] is None
    _err(admin.get(f"{R}/assoc/{a}/members", timeout=TIMEOUT), 200)
    assert admin.get(f"{R}/assoc/{a}/members", timeout=TIMEOUT).json()["total"] == 3
    _err(spec.get(f"{R}/assoc/{a}/members", timeout=TIMEOUT), 403)
    _err(spec.post(f"{R}/assoc", json={"name": f"{TAG} X"}, timeout=TIMEOUT), 403)


def test_03_claim_self_flow(admin, spec):
    a = S["aid"]
    r = spec.post(f"{R}/assoc/{a}/claims", json={"kind": "self", "member_code": "M002", "note": "Sunt eu"}, timeout=TIMEOUT)
    _err(r, 201)
    cid = r.json()["claim"]["id"]
    _err(spec.post(f"{R}/assoc/{a}/claims", json={"kind": "self", "member_code": "M003"}, timeout=TIMEOUT), 409)
    assert spec.get(f"{R}/assoc/{a}/me", timeout=TIMEOUT).json()["role"] == "claimant"
    assert any(c["id"] == cid for c in spec.get(f"{R}/assoc/claims/mine", timeout=TIMEOUT).json()["items"])
    _err(spec.post(f"{R}/assoc/claims/{cid}/decide", json={"decision": "approve"}, timeout=TIMEOUT), 403)
    _err(admin.post(f"{R}/assoc/claims/{cid}/decide", json={"decision": "reject"}, timeout=TIMEOUT), 400)
    _err(admin.post(f"{R}/assoc/claims/{cid}/decide", json={"decision": "approve"}, timeout=TIMEOUT), 200)
    _err(admin.post(f"{R}/assoc/claims/{cid}/decide", json={"decision": "approve"}, timeout=TIMEOUT), 409)
    me = spec.get(f"{R}/assoc/{a}/me", timeout=TIMEOUT).json()
    assert me["role"] == "member" and me["member"]["code"] == "M002" and me["member"]["shares"] == 0.25
    _err(spec.get(f"{R}/assoc/{a}/members", timeout=TIMEOUT), 403)


def test_04_participation(admin, spec):
    a = S["aid"]
    p = admin.get(f"{R}/assoc/{a}/participation", timeout=TIMEOUT).json()
    assert p["total_shares"] == 1.0 and p["members_count"] == 3
    assert p["active_members"] == 1 and p["active_shares"] == 0.25
    assert p["quorum_needed_shares"] == 0.5 and p["gap_to_quorum"] == 0.25 and p["quorum_met"] is False
    _err(spec.get(f"{R}/assoc/{a}/participation", timeout=TIMEOUT), 200)


def test_05_patch_member(admin, client):
    a = S["aid"]
    rows = admin.get(f"{R}/assoc/{a}/members", params={"q": "M003"}, timeout=TIMEOUT).json()["items"]
    mid = rows[0]["id"]
    _err(admin.patch(f"{R}/assoc/{a}/members/{mid}", json={"shares": 0.3}, timeout=TIMEOUT), 400)
    _err(admin.patch(f"{R}/assoc/{a}/members/{mid}", json={"shares": -1, "reason": "test"}, timeout=TIMEOUT), 400)
    r = admin.patch(f"{R}/assoc/{a}/members/{mid}", json={"shares": 0.3, "reason": "corectare registru"}, timeout=TIMEOUT)
    _err(r, 200)
    assert r.json()["member"]["shares"] == 0.3
    _err(admin.patch(f"{R}/assoc/{a}/members/{mid}", json={"status": "contacted"}, timeout=TIMEOUT), 200)
    _err(client.patch(f"{R}/assoc/{a}/members/{mid}", json={"status": "active"}, timeout=TIMEOUT), 403)
    _err(admin.post(f"{R}/assoc/{a}/members", json={"code": "M001", "name": "Dup", "shares": 1}, timeout=TIMEOUT), 409)


def test_06_heir_claim(admin, client):
    a = S["aid"]
    r = client.post(f"{R}/assoc/{a}/claims", json={"kind": "heir", "member_code": "M001", "relation": "fiu", "note": "x"}, timeout=TIMEOUT)
    _err(r, 201)
    cid = r.json()["claim"]["id"]
    r = admin.post(f"{R}/assoc/claims/{cid}/decide", json={"decision": "approve"}, timeout=TIMEOUT)
    _err(r, 200)
    me = client.get(f"{R}/assoc/{a}/me", timeout=TIMEOUT).json()
    assert me["member"]["status"] == "heir_pending"
