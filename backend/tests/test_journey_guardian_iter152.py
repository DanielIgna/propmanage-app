"""Iteration 152 — Customer Journey Guardian backend tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: try reading frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break
    except Exception:
        pass

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


def _get_menu(session):
    r = session.get(f"{BASE_URL}/api/admin/site-menu", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _put_menu(session, doc):
    body = {"items": doc.get("items", [])}
    r = session.put(f"{BASE_URL}/api/admin/site-menu", json=body, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _find_service(doc, sid):
    for g in doc.get("items", []):
        if g.get("id") == "servicii":
            for c in g.get("children", []) or []:
                if c.get("id") == sid:
                    return c, g
    return None, None


def test_guardian_status_initial(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/journey-guardian/status", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "open_tasks" in data
    assert "resolved_total" in data
    # Expect the mobilier task to be present initially
    keys = [t.get("key") for t in data["open_tasks"]]
    print(f"Initial open task keys: {keys}")


def test_guardian_run_and_no_duplicates(admin_session):
    # First run
    r1 = admin_session.post(f"{BASE_URL}/api/admin/repair-center/journey-guardian/run", timeout=30)
    assert r1.status_code == 200, r1.text
    run1 = r1.json()
    assert "issues_found" in run1
    assert "new_tasks" in run1
    assert "by_severity" in run1
    print(f"First run: {run1}")

    # Second run — should not duplicate
    r2 = admin_session.post(f"{BASE_URL}/api/admin/repair-center/journey-guardian/run", timeout=30)
    assert r2.status_code == 200, r2.text
    run2 = r2.json()
    print(f"Second run: {run2}")
    assert run2["new_tasks"] == 0, f"expected 0 new tasks on second run, got {run2['new_tasks']}"


def test_guardian_status_has_mobilier_task(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/journey-guardian/status", timeout=15)
    assert r.status_code == 200
    data = r.json()
    mobilier_task = next(
        (t for t in data["open_tasks"] if t.get("key") == "service_no_providers:mobilier"), None)
    assert mobilier_task is not None, f"mobilier task not in open_tasks: {[t.get('key') for t in data['open_tasks']]}"
    assert mobilier_task.get("severity") == "medium"
    assert mobilier_task.get("assigned_to") == "cto_ai"
    assert "affected" in mobilier_task
    assert "expected" in mobilier_task
    assert "business_impact" in mobilier_task


def test_guardian_auto_resolve_and_restore(admin_session):
    # Add a provider to mobilier service
    doc = _get_menu(admin_session)
    svc, group = _find_service(doc, "mobilier")
    assert svc is not None, "mobilier service not found in admin site-menu"
    original_providers = list(svc.get("providers") or [])
    svc["providers"] = original_providers + [{
        "name": "TEST_ITER152_Partner",
        "url": "https://example.com/test",
        "active": True,
    }]
    _put_menu(admin_session, doc)

    try:
        # Run guardian → task should auto-resolve
        r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/journey-guardian/run", timeout=30)
        assert r.status_code == 200
        run = r.json()
        print(f"Run after provider add: {run}")
        assert run["auto_resolved"] >= 1, f"expected auto_resolved>=1, got {run['auto_resolved']}"

        # Verify task no longer in open
        rs = admin_session.get(f"{BASE_URL}/api/admin/repair-center/journey-guardian/status", timeout=15)
        data = rs.json()
        keys = [t.get("key") for t in data["open_tasks"]]
        assert "service_no_providers:mobilier" not in keys, f"mobilier task still open: {keys}"
    finally:
        # Restore original state (mobilier without providers, task open)
        doc2 = _get_menu(admin_session)
        svc2, _ = _find_service(doc2, "mobilier")
        svc2["providers"] = original_providers
        _put_menu(admin_session, doc2)

        # Run guardian again → task should be re-opened
        r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/journey-guardian/run", timeout=30)
        assert r.status_code == 200
        run = r.json()
        print(f"Run after restore: {run}")

        rs = admin_session.get(f"{BASE_URL}/api/admin/repair-center/journey-guardian/status", timeout=15)
        data = rs.json()
        keys = [t.get("key") for t in data["open_tasks"]]
        assert "service_no_providers:mobilier" in keys, f"mobilier task should be re-opened: {keys}"
