"""Rădăcini S9 C — calendar, finanțe, transparență, jurnal (HTTP, backend pornit cu RADACINI_ENABLED).

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s9c.py -q --noconftest
"""
import os
import uuid

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
            for d in requests.get(f"{R}/legal/documents", timeout=TIMEOUT).json()["items"]:
                s.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)
            return s
    pytest.skip(f"Login failed for {email}")


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


@pytest.fixture(scope="module")
def client():
    return _login("client@propmanage.io", ["Client123!"])


@pytest.fixture(scope="module")
def setup(admin, client):
    r = admin.post(f"{R}/assoc", json={"name": f"TEST-RAD-S9C {uuid.uuid4().hex[:6]}", "type": "composesorat",
                                       "localities": ["Test"], "description": "test", "legal": {}, "patrimony": []}, timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    aid = r.json().get("id") or r.json()["association"]["id"]
    for code, shares in (("M001", 0.5), ("M002", 0.25), ("M003", 0.25)):
        r = admin.post(f"{R}/assoc/{aid}/members", json={"code": code, "name": f"Membru {code}", "shares": shares,
                                                          "status": "unknown"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
    r = client.post(f"{R}/assoc/{aid}/claims", json={"kind": "self", "member_code": "M001", "note": "test", "document_ids": []},
                    timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    cid = r.json().get("id") or r.json()["claim"]["id"]
    r = admin.post(f"{R}/assoc/claims/{cid}/decide", json={"decision": "approve"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return aid


def test_obligations(admin, setup):
    r = admin.get(f"{R}/assoc/{setup}/obligations", params={"year": 2024}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    keys = {i["key"] for i in r.json()["items"]}
    assert {"balance", "budget", "pasture_plan", "registry_update", "aga_ordinary_04-30"} <= keys
    assert all(i["status"] == "missed" for i in r.json()["items"] if i["key"] == "balance")
    r = admin.post(f"{R}/assoc/{setup}/obligations/balance/evidence", json={"year": 2024, "note": "bilanț depus", "date": "2024-03-01"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    items = admin.get(f"{R}/assoc/{setup}/obligations", params={"year": 2024}, timeout=TIMEOUT).json()["items"]
    assert next(i for i in items if i["key"] == "balance")["status"] == "done"


def test_finance_flow(admin, client, setup):
    base = {"year": 2023, "revenues": {"lemn": 10000}, "expenses": {"salarii": 2000}, "net_profit": 8000}
    bad = admin.post(f"{R}/assoc/{setup}/finance/years", json={**base, "split": {
        "council": 5000, "reserve": 0, "charity": 0, "investment": 0, "members": 3000}}, timeout=TIMEOUT)
    assert bad.status_code == 400, bad.text
    bad = admin.post(f"{R}/assoc/{setup}/finance/years", json={**base, "split": {
        "council": 800, "reserve": 1600, "charity": 0, "investment": 0, "members": 1}}, timeout=TIMEOUT)
    assert bad.status_code == 400, bad.text
    ok = admin.post(f"{R}/assoc/{setup}/finance/years", json={**base, "split": {
        "council": 800, "reserve": 1600, "charity": 0, "investment": 0, "members": 5600}}, timeout=TIMEOUT)
    assert ok.status_code == 200, ok.text
    d = admin.post(f"{R}/assoc/{setup}/finance/years/2023/distribute", json={"aga_date": "2024-04-20"}, timeout=TIMEOUT)
    assert d.status_code == 200, d.text
    assert admin.post(f"{R}/assoc/{setup}/finance/years/2023/distribute", json={"aga_date": "2024-04-20"}, timeout=TIMEOUT).status_code == 409
    full = admin.get(f"{R}/assoc/{setup}/finance", timeout=TIMEOUT).json()
    assert len(full["distributions"]) == 3
    assert abs(sum(x["amount"] for x in full["distributions"]) - 5600) < 0.02
    assert full["totals"]["unpaid_count"] == 3
    mine = client.get(f"{R}/assoc/{setup}/finance", timeout=TIMEOUT).json()
    assert len(mine["distributions"]) == 1
    m = mine["distributions"][0]
    assert abs(m["amount"] - 2800) < 0.02 and m["prescribes_at"] == "2029-04-20" and "days_to_prescription" in m
    assert client.post(f"{R}/assoc/distributions/{m['id']}/paid", timeout=TIMEOUT).status_code == 403
    assert admin.post(f"{R}/assoc/distributions/{m['id']}/paid", timeout=TIMEOUT).status_code == 200
    assert admin.post(f"{R}/assoc/distributions/{m['id']}/paid", timeout=TIMEOUT).status_code == 409


def test_transparency(admin, setup):
    r = admin.get(f"{R}/assoc/{setup}/transparency", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    j = r.json()
    assert 0 <= j["score"] <= 100 and len(j["components"]) == 4
    assert all(c["explanation"] for c in j["components"])


def test_audit_summary_vs_full(admin, client, setup):
    a = admin.get(f"{R}/assoc/{setup}/audit", params={"limit": 50}, timeout=TIMEOUT).json()
    assert a["items"] and any("after" in e or "actor_user_id" in e for e in a["items"])
    m = client.get(f"{R}/assoc/{setup}/audit", timeout=TIMEOUT)
    assert m.status_code == 200, m.text
    for e in m.json()["items"]:
        assert set(e) == {"action", "actor_role", "target_type", "at"}


def test_alerts_mine(client, setup):
    r = client.get(f"{R}/assoc/alerts/mine", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    assert any(i["association_id"] == setup for i in r.json()["items"])
