"""
Iter 154 — Regression tests after removing ClientDashboardSwitch legacy path,
twin_orchestrator router, and dead routes.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CLIENT = ("client@propmanage.io", "Client123!")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")
SPECIALIST = ("specialist@propmanage.io", "Spec123!")
OPERATOR = ("operator@propmanage.io", "Op123!")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


# --- Twin Orchestrator router removed ---
def test_twin_orchestrator_insights_removed():
    admin = _login(*ADMIN)
    r = admin.get(f"{BASE_URL}/api/admin/twin-orchestrator/insights", timeout=15)
    assert r.status_code == 404, f"expected 404 (router removed), got {r.status_code}"


# --- Client digital twins still works ---
def test_client_digital_twins_available():
    client = _login(*CLIENT)
    r = client.get(f"{BASE_URL}/api/me/digital-twins", timeout=15)
    assert r.status_code == 200, f"expected 200, got {r.status_code} {r.text[:200]}"


# --- Orchestrator overview has expected fields ---
def test_orchestrator_overview_has_retry_fields():
    admin = _login(*ADMIN)
    r = admin.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=15)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    data = r.json()
    assert "retry_pending" in data, f"missing retry_pending: {list(data.keys())}"
    assert "retry_blocked_config" in data, f"missing retry_blocked_config: {list(data.keys())}"
    assert isinstance(data["retry_pending"], int)
    assert isinstance(data["retry_blocked_config"], int)


# --- Auth smoke checks for the other roles ---
@pytest.mark.parametrize("creds", [SPECIALIST, OPERATOR, ADMIN, CLIENT])
def test_login_all_demo_roles(creds):
    email, pw = creds
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"{email} login failed: {r.status_code} {r.text[:200]}"


# --- App settings no longer contains enable_twin_orchestrator ---
def test_app_settings_no_twin_orchestrator_field():
    admin = _login(*ADMIN)
    # Try common endpoints
    for path in ("/api/admin/settings", "/api/admin/app-settings", "/api/settings"):
        r = admin.get(f"{BASE_URL}{path}", timeout=10)
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                continue
            body = str(data)
            assert "enable_twin_orchestrator" not in body, f"stale field still present in {path}: {body[:300]}"
            return
    pytest.skip("no settings endpoint reachable; skipping stale-field check")
