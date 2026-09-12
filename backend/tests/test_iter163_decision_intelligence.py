"""Iter 163 — Decision Intelligence Engine (AIB-007) backend tests (HTTP, sync)."""
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
    # asigură registrul de procese (dependența AIB-006)
    a = _login("admin@propmanage.io", "1!nasov01ADMIN")
    a.post(f"{BASE_URL}/api/admin/ai-brain/processes/build", timeout=120)
    return s


def test_client_decisions_scored(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", params={"path": "/client"}, timeout=60)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "nicio decizie generată pentru client"
    scores = [d["score"] for d in items]
    assert scores == sorted(scores, reverse=True), "deciziile nu sunt sortate după scor"
    d = items[0]
    for f in ("id", "kind", "title", "score", "factors", "reasons",
              "resolves", "avoids_risk", "produces_impact", "after", "cta_path"):
        assert f in d, f"câmp lipsă: {f}"
    assert set(d["factors"]) == {"urgency", "impact", "unblocking", "readiness",
                                 "progress", "risk_of_inaction"}
    assert all(0 <= v <= 1 for v in d["factors"].values())
    assert 0 <= d["score"] <= 100
    assert d["reasons"], "decizia nu are argumentație"


def test_decision_simulate_no_execution(client_session):
    items = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    did = items[0]["id"]
    r = client_session.post(f"{BASE_URL}/api/ai-brain/decisions/simulate",
                            json={"decision_id": did}, timeout=30)
    assert r.status_code == 200
    sim = r.json()
    assert sim["found"] and sim["simulated"] is True and sim["executed"] is False
    for f in ("affected_modules", "affected_processes", "affected_users",
              "estimated_state_changes", "impact_summary", "risk_if_skipped"):
        assert f in sim


def test_decision_explain(client_session):
    items = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    did = items[0]["id"]
    r = client_session.post(f"{BASE_URL}/api/ai-brain/decisions/explain",
                            json={"decision_id": did,
                                  "question": "Ce se întâmplă dacă nu fac nimic?"}, timeout=90)
    assert r.status_code == 200
    d = r.json()
    assert d["found"] and len(d["explanation"]) > 50
    assert d["decision"]["id"] == did


def test_decision_explain_unknown(client_session):
    r = client_session.post(f"{BASE_URL}/api/ai-brain/decisions/explain",
                            json={"decision_id": "000000000000"}, timeout=30)
    assert r.status_code == 200 and r.json()["found"] is False


def test_admin_decisions_approvals(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "adminul trebuie să aibă decizii (aprobări/guardian)"
    kinds = {d["kind"] for d in items}
    assert kinds & {"pending_approval", "guardian_task"}, f"kinds admin neașteptate: {kinds}"


def test_admin_inspect_other_user(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/decisions/inspect",
                          params={"email": "client@propmanage.io"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert d["role"] == "client" and d["items"]
    # adminul poate simula decizia utilizatorului inspectat
    did = d["items"][0]["id"]
    rs = admin_session.post(f"{BASE_URL}/api/ai-brain/decisions/simulate",
                            json={"decision_id": did, "email": "client@propmanage.io"}, timeout=30)
    assert rs.status_code == 200 and rs.json()["found"]


def test_priorities_engine(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/decisions/priorities", timeout=30)
    assert r.status_code == 200
    items = r.json()["items"]
    assert isinstance(items, list)
    if items:
        assert items[0]["severity"] >= items[-1]["severity"]
        assert {"kind", "title", "detail"} <= set(items[0])


def test_decision_rules_transparency(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/ai-brain/decisions/rules", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert abs(sum(d["weights"].values()) - 1.0) < 0.01
    assert len(d["generators"]) >= 5 and len(d["factors"]) == 6


def test_mentor_uses_decisions(client_session):
    r = client_session.get(f"{BASE_URL}/api/ai-brain/mentor", params={"path": "/client"}, timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "decisions" in d, "mentorul nu include deciziile (AIB-007)"
    if d["decisions"]:
        assert d["actions"][0].get("score") is not None, "acțiunile nu poartă scorul deciziei"


def test_decisions_require_auth():
    r = requests.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=15)
    assert r.status_code in (401, 403)


def test_rules_admin_only(client_session):
    r = client_session.get(f"{BASE_URL}/api/admin/ai-brain/decisions/rules", timeout=15)
    assert r.status_code in (401, 403)


def test_non_admin_cannot_impersonate(client_session):
    items = client_session.get(f"{BASE_URL}/api/ai-brain/decisions", timeout=60).json()["items"]
    r = client_session.post(f"{BASE_URL}/api/ai-brain/decisions/simulate",
                            json={"decision_id": items[0]["id"], "email": "admin@propmanage.io"},
                            timeout=30)
    # email-ul e ignorat pentru non-admin — rulează pe propriul snapshot
    assert r.status_code == 200 and r.json()["found"]
