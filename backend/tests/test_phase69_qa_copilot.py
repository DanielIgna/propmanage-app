"""Phase 69 QA Copilot - backend tests."""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE:
    # fall back to public URL in frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=ADMIN, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=CLIENT, timeout=20)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def created_session_id(admin_session):
    payload = {"title": "TEST_QA Phase69 session", "goal": "verify endpoints", "role_being_tested": "specialist", "area": "Marketplace"}
    r = admin_session.post(f"{BASE}/api/admin/qa-copilot/sessions", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "active"
    assert data["findings"] == []
    assert data["title"] == payload["title"]
    assert "id" in data
    return data["id"]


# --- create / list / get ---
def test_list_includes_session(admin_session, created_session_id):
    r = admin_session.get(f"{BASE}/api/admin/qa-copilot/sessions", timeout=20)
    assert r.status_code == 200
    data = r.json()
    items = data["items"]
    assert any(s["id"] == created_session_id for s in items)
    target = next(s for s in items if s["id"] == created_session_id)
    assert "finding_count" in target
    # newest first sort
    if len(items) >= 2:
        assert items[0]["created_at"] >= items[1]["created_at"]


def test_get_single_session(admin_session, created_session_id):
    r = admin_session.get(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == created_session_id
    assert "findings" in data


# --- auth gating ---
def test_non_admin_forbidden(client_session):
    r = client_session.get(f"{BASE}/api/admin/qa-copilot/sessions", timeout=20)
    assert r.status_code in (401, 403)


def test_no_auth_forbidden():
    r = requests.get(f"{BASE}/api/admin/qa-copilot/sessions", timeout=20)
    assert r.status_code in (401, 403)


# --- add finding (AI analysis - 5-20s) ---
@pytest.fixture(scope="module")
def created_finding_id(admin_session, created_session_id):
    body = {"text": "Specialistul Mihai Ionescu este din Bucuresti dar apare ca match pentru o cerere din Cluj. Nu se respecta filtrul geografic."}
    r = admin_session.post(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}/findings", json=body, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "id" in data
    assert data["text"] == body["text"].strip()
    a = data.get("ai_analysis") or {}
    assert "category" in a
    assert "severity" in a
    assert a["category"] in ["UI_UX", "DATA", "LOGIC_BUG", "MISSING_FEATURE", "INTEGRATION", "PERFORMANCE", "SECURITY"]
    assert a["severity"] in ["P0", "P1", "P2", "P3"]
    assert isinstance(a.get("suspected_files", []), list)
    assert isinstance(a.get("suggested_next_tests", []), list)
    assert isinstance(a.get("related_finding_ids", []), list)
    return data["id"]


def test_finding_persisted(admin_session, created_session_id, created_finding_id):
    r = admin_session.get(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert any(f["id"] == created_finding_id for f in data["findings"])


# --- generate prompt ---
def test_generate_prompt(admin_session, created_session_id, created_finding_id):
    r = admin_session.post(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}/generate-prompt", timeout=90)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "prompt" in data
    assert isinstance(data["prompt"], str)
    assert len(data["prompt"]) > 50


# --- patch (status=closed) ---
def test_patch_status_closed(admin_session, created_session_id):
    r = admin_session.patch(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", json={"status": "closed"}, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "closed"
    # reopen for next test continuity
    admin_session.patch(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", json={"status": "active"}, timeout=20)


def test_patch_invalid_status(admin_session, created_session_id):
    r = admin_session.patch(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", json={"status": "bogus"}, timeout=20)
    assert r.status_code == 400


# --- delete finding ---
def test_delete_finding(admin_session, created_session_id, created_finding_id):
    r = admin_session.delete(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}/findings/{created_finding_id}", timeout=20)
    assert r.status_code == 200
    g = admin_session.get(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", timeout=20)
    assert not any(f["id"] == created_finding_id for f in g.json()["findings"])


# --- delete session ---
def test_delete_session(admin_session, created_session_id):
    r = admin_session.delete(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", timeout=20)
    assert r.status_code == 200
    g = admin_session.get(f"{BASE}/api/admin/qa-copilot/sessions/{created_session_id}", timeout=20)
    assert g.status_code == 404


# --- requests endpoint: specialist_specialty etc. fields ---
def test_requests_returns_specialist_fields(client_session):
    r = client_session.get(f"{BASE}/api/requests", timeout=20)
    assert r.status_code == 200
    items = r.json()
    assigned = [x for x in items if x.get("specialist_id")]
    if not assigned:
        pytest.skip("No assigned requests found for client - skipping field presence test")
    sample = assigned[0]
    # fields should be present (may be empty string but key exists in serialized doc once accept ran)
    assert "specialist_specialty" in sample or "specialist_name" in sample
