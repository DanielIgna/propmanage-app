"""Rădăcini S9 — scenariul demo „Composesoratul Demo Valea Verde” (HTTP, backend pornit).

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s9_demo.py -q --noconftest

admin = super-admin. Testul curăță scenariul demo la început și la sfârșit.
"""
import os

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
R = f"{API}/radacini"
TIMEOUT = 60
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
NAME = "Composesoratul Demo Valea Verde"
S: dict = {}


def _accept_terms(s):
    docs = s.get(f"{R}/legal/documents", timeout=TIMEOUT).json().get("items", [])
    for d in docs:
        s.post(f"{R}/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    for pwd in ADMIN_PASSWORDS:
        if s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": pwd}, timeout=TIMEOUT).status_code == 200:
            _accept_terms(s)
            return s
    pytest.skip("Login failed for admin")


def test_01_reset_then_seed(admin):
    admin.post(f"{R}/assoc/demo/reset", timeout=TIMEOUT)  # rezultatul se ignoră
    r = admin.post(f"{R}/assoc/demo/seed", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    S["aid"] = r.json()["association_id"]
    assert r.json()["members"] == 60
    assert admin.post(f"{R}/assoc/demo/seed", timeout=TIMEOUT).status_code == 409


def test_02_listed(admin):
    items = admin.get(f"{R}/assoc", timeout=TIMEOUT).json()["items"]
    me = [i for i in items if i["id"] == S["aid"]]
    assert me and me[0]["name"] == NAME and me[0]["members_count"] == 60
    assert me[0]["total_area_ha"] == 380


def test_03_participation_gap(admin):
    p = admin.get(f"{R}/assoc/{S['aid']}/participation", timeout=TIMEOUT).json()
    assert p["gap_to_quorum"] > 0 and not p["quorum_met"]
    assert p["by_status"]["deceased"]["count"] == 8 and p["by_status"]["heir_pending"]["count"] == 2


def test_04_transparency_low(admin):
    t = admin.get(f"{R}/assoc/{S['aid']}/transparency", timeout=TIMEOUT).json()
    assert t["score"] < 60, t


def test_05_finance_near_prescription(admin):
    f = admin.get(f"{R}/assoc/{S['aid']}/finance", timeout=TIMEOUT).json()
    assert len(f["years"]) == 2
    assert f["totals"]["near_prescription_count"] > 0 and f["totals"]["near_prescription_amount"] > 0
    assert any(d["near_prescription"] and (d["days_to_prescription"] or 0) < 150 for d in f["distributions"])


def test_06_meetings_and_requests(admin):
    ms = admin.get(f"{R}/assoc/{S['aid']}/meetings", timeout=TIMEOUT).json()["items"]
    assert any(m["held_without_quorum"] for m in ms) and any(m["status"] == "convened" for m in ms)
    rq = admin.get(f"{R}/assoc/{S['aid']}/requests", timeout=TIMEOUT).json()["items"]
    assert sum(1 for r in rq if r["overdue"]) == 1
    ps = admin.get(f"{R}/assoc/{S['aid']}/petitions", timeout=TIMEOUT).json()["items"]
    assert ps and not ps[0]["threshold_met"] and ps[0]["signatures_count"] == 4


def test_07_reset(admin):
    r = admin.post(f"{R}/assoc/demo/reset", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    items = admin.get(f"{R}/assoc", timeout=TIMEOUT).json()["items"]
    assert all(i["id"] != S["aid"] for i in items)
