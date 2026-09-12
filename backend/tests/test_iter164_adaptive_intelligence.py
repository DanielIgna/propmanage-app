"""Iter 164 — Adaptive Intelligence Engine (AIB-008) backend tests (HTTP, sync)."""
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
    s = _login("client@propmanage.io", "Client123!")
    a = _login("admin@propmanage.io", "1!nasov01ADMIN")
    a.post(f"{BASE_URL}/api/admin/ai-brain/processes/build", timeout=120)
    return s


def test_decisions_have_confidence_and_adaptive(client_session):
    items = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    assert items
    d = items[0]
    assert "confidence" in d and 0 < d["confidence"] < 100
    assert d["confidence_factors"] and len(d["confidence_factors"]) >= 3
    assert "adaptive" in d and "adjustment" in d["adaptive"]
    assert "base_score" in d and "role_acceptance" in d["adaptive"]


def test_seen_count_increments(client_session):
    i1 = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    i2 = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    common = {d["id"]: d for d in i1} .keys() & {d["id"] for d in i2}
    assert common, "nicio decizie stabilă între generări"
    did = next(iter(common))
    c1 = next(d for d in i1 if d["id"] == did)["seen_count"]
    c2 = next(d for d in i2 if d["id"] == did)["seen_count"]
    assert c2 == c1 + 1
    assert next(d for d in i2 if d["id"] == did)["first_seen_at"] == \
        next(d for d in i1 if d["id"] == did)["first_seen_at"]


def test_explicit_feedback_loop(client_session):
    items = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    did = items[0]["id"]
    r = client_session.post(f"{BASE_URL}/api/ai-brain/decisions/feedback",
                            json={"decision_id": did, "action": "accepted"}, timeout=15)
    assert r.status_code == 200 and r.json()["ok"]
    r2 = client_session.post(f"{BASE_URL}/api/ai-brain/decisions/feedback",
                             json={"decision_id": did, "action": "invalid_x"}, timeout=15)
    assert r2.status_code == 400


def test_dismissed_penalizes_score(client_session):
    items = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    target = items[-1]
    client_session.post(f"{BASE_URL}/api/ai-brain/decisions/feedback",
                        json={"decision_id": target["id"], "action": "dismissed"}, timeout=15)
    items2 = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    after = next((d for d in items2 if d["id"] == target["id"]), None)
    if after:  # decizia poate rămâne, dar penalizată explicit
        assert after["adaptive"]["adjustment"] <= -25
        assert any("respins" in r for r in after["adaptive"]["reasons"])


def test_user_behavior_profile(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/profile", timeout=30)
    assert r.status_code == 200
    p = r.json()
    for f in ("top_modules", "usual_start_module", "common_flows", "feedback",
              "followed", "ignored", "persistent_recommendations"):
        assert f in p
    assert p["role"] == "client"
    assert p["followed"] >= 1  # feedback-ul explicit de mai sus


def test_role_profiles(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/adaptive/roles", timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    roles = {i["role"] for i in items}
    assert "client" in roles and "specialist" in roles
    cl = next(i for i in items if i["role"] == "client")
    assert cl["followed"] + cl["ignored"] >= 1
    assert "top_modules" in cl and "users" in cl


def test_process_learning(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/adaptive/processes", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for f in ("bottlenecks", "delayed_stages", "abandoned_processes",
              "efficient_processes", "possibly_unused_states", "degradations"):
        assert f in d
    assert d["bottlenecks"], "nu s-au identificat blocaje (datele demo au multe)"
    assert {"process", "state", "stuck"} <= set(d["bottlenecks"][0])


def test_adaptive_overview(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/adaptive/overview", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for f in ("feedback_totals", "followed", "ignored", "by_kind",
              "recalibrations", "avg_confidence", "decisions_tracked"):
        assert f in d
    assert d["followed"] + d["ignored"] >= 1
    assert d["avg_confidence"] is None or 0 < d["avg_confidence"] < 100


def test_admin_behavior_inspect(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/adaptive/behavior",
                          params={"email": "client@propmanage.io"}, timeout=30)
    assert r.status_code == 200 and r.json()["role"] == "client"
    r404 = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/adaptive/behavior",
                             params={"email": "nimeni@x.ro"}, timeout=15)
    assert r404.status_code == 404


def test_mentor_personal_insights(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor", params={"path": "/client"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "insights" in d, "mentorul nu include insights (AIB-008)"
    for ins in d["insights"]:
        assert "kind" in ins and "text" in ins
    if d.get("decisions"):
        assert d["actions"][0].get("confidence") is not None


def test_adaptive_admin_only(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/adaptive/overview", timeout=15)
    assert r.status_code in (401, 403)


def test_profile_requires_auth():
    r = requests.get(f"{BASE_URL}/api/ai-brain/profile", timeout=15)
    assert r.status_code in (401, 403)
