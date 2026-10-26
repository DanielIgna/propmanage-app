"""Rădăcini — raportarea conținutului (DSA), starea sistemului și datele operatorului (HTTP, backend pornit).

    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_reports.py -q --noconftest

Raportările de test au detaliile cu prefixul „TEST-RAD-” (le șterge `radacini_purge_demo --tests-only`).
"""
import os
import uuid

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
R = f"{API}/radacini"
TIMEOUT = 30
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
S: dict = {}


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
def spec():
    return _login("specialist@propmanage.io", ["Spec123!"])


def _report(s, **over):
    body = {"target_type": "user", "target_id": S["spec_id"], "reason": "abuse", "details": f"{TAG} mesaje jignitoare"}
    body.update(over)
    return s.post(f"{R}/reports", json=body, timeout=TIMEOUT)


def test_01_create_and_validate(client, spec):
    S["spec_id"] = spec.get(f"{R}/me", timeout=TIMEOUT).json()["id"]
    S["client_id"] = client.get(f"{R}/me", timeout=TIMEOUT).json()["id"]
    assert requests.post(f"{R}/reports", json={}, timeout=TIMEOUT).status_code == 401
    assert _report(client, reason="nope").status_code == 400
    assert _report(client, target_type="planet").status_code == 400
    assert _report(client, target_id="0" * 24).status_code == 404
    assert _report(client, target_id=S["client_id"]).status_code == 400  # nu te poți raporta pe tine
    r = _report(client)
    assert r.status_code == 200, r.text
    rep = r.json()["report"]
    assert rep["status"] == "open" and rep["reason_label"] and "reporter_id" not in rep
    S["rid"] = rep["id"]
    assert _report(client).status_code == 409  # o singură raportare deschisă pe același conținut


def test_02_mine_and_staff_access(client, admin):
    mine = client.get(f"{R}/reports/mine", timeout=TIMEOUT).json()["items"]
    assert any(i["id"] == S["rid"] for i in mine)
    assert client.get(f"{R}/staff/reports", timeout=TIMEOUT).status_code == 403
    r = admin.get(f"{R}/staff/reports?status=open", timeout=TIMEOUT)
    assert r.status_code == 200
    item = next(i for i in r.json()["items"] if i["id"] == S["rid"])
    assert item["reporter_id"] == S["client_id"] and item["target_owner_id"] == S["spec_id"]
    assert r.json()["open_count"] >= 1


def test_03_resolve(client, admin):
    url = f"{R}/staff/reports/{S['rid']}/resolve"
    assert client.post(url, json={"decision": "no_action", "note": "ok"}, timeout=TIMEOUT).status_code == 403
    assert admin.post(url, json={"decision": "ban", "note": "x x x"}, timeout=TIMEOUT).status_code == 400
    assert admin.post(url, json={"decision": "user_warned", "note": ""}, timeout=TIMEOUT).status_code == 400
    r = admin.post(url, json={"decision": "user_warned", "note": "Am trimis un avertisment."}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    assert r.json()["report"]["status"] == "resolved"
    assert admin.post(url, json={"decision": "no_action", "note": "din nou"}, timeout=TIMEOUT).status_code == 409
    mine = client.get(f"{R}/reports/mine", timeout=TIMEOUT).json()["items"]
    me = next(i for i in mine if i["id"] == S["rid"])
    assert me["decision"] == "user_warned" and me["decision_note"] == "Am trimis un avertisment."
    # după închidere se poate raporta din nou același conținut
    assert _report(client).status_code == 200


def test_04_gdpr_export(client):
    r = client.get(f"{R}/me/export", timeout=60)
    assert r.status_code == 200
    reps = r.json().get("content_reports") or r.json().get("data", {}).get("content_reports") or []
    assert any(TAG in (x.get("details") or "") for x in reps)


def test_05_system_status(admin, client):
    assert client.get(f"{R}/admin/system", timeout=TIMEOUT).status_code == 403
    r = admin.get(f"{R}/admin/system", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["db"]["ok"] is True and j["config"]["enabled"] is True
    assert {"reports_open", "disputes_open", "parcels_pending", "deletion_pending"} <= set(j["queues"])
    assert isinstance(j["warnings"], list) and isinstance(j["recent_errors"], list)


def test_06_operator_public():
    r = requests.get(f"{R}/operator", timeout=TIMEOUT)
    assert r.status_code == 200
    assert isinstance(r.json()["operator"], dict) and isinstance(r.json()["complete"], bool)
