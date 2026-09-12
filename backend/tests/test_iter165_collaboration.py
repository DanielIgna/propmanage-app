"""Iter 165 — Collaborative Intelligence Engine (AIB-009) backend tests (HTTP, sync)."""
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
    s = _login("admin@propmanage.io", "1!nasov01ADMIN")
    s.post(f"{BASE_URL}/api/admin/ai-brain/processes/build", timeout=120)
    return s


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


def test_sla_sweep(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/ai-brain/collaboration/sweep", timeout=120)
    assert r.status_code == 200
    d = r.json()
    for f in ("processes_monitored", "instances_checked", "at_risk", "breached",
              "abandoned", "notifications_created", "escalations_proposed"):
        assert f in d
    assert d["processes_monitored"] >= 3
    assert d["instances_checked"] > 10


def test_notification_dedupe(admin_session):
    r1 = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/notifications", timeout=30)
    n1 = len(r1.json()["items"])
    admin_session.post(f"{BASE_URL}/api/admin/ai-brain/collaboration/sweep", timeout=120)
    r2 = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/notifications", timeout=30)
    n2 = len(r2.json()["items"])
    assert n2 == n1, f"sweep-ul repetat a duplicat notificările: {n1} → {n2}"


def test_notifications_prioritized_with_why(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/notifications", timeout=30)
    items = r.json()["items"]
    assert items, "datele demo au instanțe peste SLA — trebuiau notificări"
    prios = [n["priority"] for n in items]
    assert prios == sorted(prios, reverse=True)
    n0 = items[0]
    for f in ("target", "process_name", "state", "instances", "why", "priority"):
        assert f in n0
    assert n0["instances"] >= 1 and len(n0["why"]) > 30


def test_collaboration_overview(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/overview", timeout=30)
    assert r.status_code == 200
    d = r.json()
    t = d["totals"]
    for f in ("monitored", "instances", "at_risk", "breached", "abandoned",
              "notifications_active", "escalations"):
        assert f in t
    assert d["processes"], "sweep-ul trebuia să populeze procesele"
    p0 = d["processes"][0]
    assert "counts" in p0 and "breaches" in p0
    if p0["breaches"]:
        b = p0["breaches"][0]
        for f in ("entity", "state", "responsible_now", "sla", "handoff", "escalations"):
            assert f in b
        assert b["sla"]["level"] in ("breached", "abandoned")
        assert b["escalations"], "instanțele peste SLA trebuie să aibă escaladări propuse"
        assert b["escalations"][0]["action"] in ("reminder", "escalate", "reassign",
                                                 "close", "admin_intervention")
        assert b["escalations"][0]["why"]


def test_handoff_map(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/handoffs/proc_requests",
                          timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["handoffs"], "procesul requests are mai mulți actori — trebuiau transferuri"
    h = d["handoffs"][0]
    for f in ("from_actor", "to_actor", "at_state", "why", "transfers"):
        assert f in h
    actors = {a for h in d["handoffs"] for a in h["from_actor"] + h["to_actor"]}
    assert {"client", "specialist"} & actors


def test_client_collaboration_state(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/collaboration/state",
                           params={"path": "/client"}, timeout=30)
    assert r.status_code == 200
    st = r.json()
    assert st["found"]
    for f in ("responsible_now", "next_actors", "waiting_actors", "delayed_actors",
              "released_actors", "to_notify", "sla", "handoff", "escalations", "timeline"):
        assert f in st
    assert st["sla"]["level"] in ("ok", "at_risk", "breached", "abandoned", "done")
    assert "hours_in_stage" in st["sla"] and "sla_hours" in st["sla"] and "basis" in st["sla"]
    tl = st["timeline"]
    assert "events" in tl and "contributors" in tl and "created_by" in tl


def test_admin_inspect_collaboration(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/state",
                          params={"pid": "proc_requests", "email": "client@propmanage.io"},
                          timeout=30)
    assert r.status_code == 200 and r.json()["found"]


def test_mentor_includes_collaboration(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor", params={"path": "/client"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "collaboration" in d, "mentorul nu include colaborarea (AIB-009)"
    if d["collaboration"]:
        c = d["collaboration"]
        assert "you_act" in c and "responsible_now" in c and "message" in c and "sla" in c


def test_admin_decisions_include_escalations(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60)
    kinds = {d["kind"] for d in r.json()["items"]}
    assert "escalation" in kinds, f"deciziile admin nu includ escaladări SLA: {kinds}"


def test_collab_requires_auth():
    r = requests.get(f"{BASE_URL}/api/ai-brain/collaboration/state", timeout=15)
    assert r.status_code in (401, 403)


def test_collab_admin_only(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/collaboration/overview", timeout=15)
    assert r.status_code in (401, 403)
