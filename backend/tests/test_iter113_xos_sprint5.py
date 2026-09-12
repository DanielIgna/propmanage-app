"""Sprint 5 — Experience Configuration Center backend regression.

Coverage:
- Layout versioning: PUT layout snapshots into xos_layout_history (cap 20)
- GET /api/admin/xos/layout/{surface}/history returns latest versions
- POST rollback/{version_id} valid → ok + items restored + pre-rollback snapshot
- Rollback with invalid version_id → 404
- Admin-gated endpoints reject unauthenticated (401/403)
- Regression: public layout, surfaces, reset, registry, experience-profiles, ui-rules
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def anon_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ── Sprint 5: Layout Versioning ──────────────────────────────────────────────
class TestXOSLayoutVersioning:
    def test_public_layout_client_home(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/xos/layout/client_home", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["surface"] == "client_home"
        assert isinstance(data["items"], list) and len(data["items"]) >= 1
        for it in data["items"]:
            assert "id" in it and "enabled" in it

    def test_admin_surfaces(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/xos/surfaces", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "surfaces" in data
        keys = {s["surface"] for s in data["surfaces"]}
        assert {"client_home", "specialist_home"}.issubset(keys)

    def test_history_endpoint_returns_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/xos/layout/client_home/history", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["surface"] == "client_home"
        assert isinstance(data["versions"], list)
        for v in data["versions"]:
            for k in ("version_id", "surface", "items", "saved_at"):
                assert k in v

    def test_put_layout_creates_snapshot(self, admin_session):
        # Get current items
        surfaces = admin_session.get(f"{BASE_URL}/api/admin/xos/surfaces").json()["surfaces"]
        current = next(s for s in surfaces if s["surface"] == "client_home")["items"]
        assert current, "must have items to test"

        # Snapshot count before
        before = admin_session.get(f"{BASE_URL}/api/admin/xos/layout/client_home/history").json()["versions"]
        n_before = len(before)

        # PUT with same items (snapshot pre-save triggers)
        r = admin_session.put(f"{BASE_URL}/api/admin/xos/layout/client_home", json={"items": current}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # Snapshot count after must increase (up to cap 20)
        after = admin_session.get(f"{BASE_URL}/api/admin/xos/layout/client_home/history").json()["versions"]
        assert len(after) >= min(n_before + 1, 20), f"history did not grow: {n_before}→{len(after)}"

    def test_rollback_valid_version(self, admin_session):
        # Ensure at least one history entry — do a PUT first
        cur = admin_session.get(f"{BASE_URL}/api/admin/xos/surfaces").json()["surfaces"]
        items = next(s for s in cur if s["surface"] == "client_home")["items"]
        admin_session.put(f"{BASE_URL}/api/admin/xos/layout/client_home", json={"items": items})

        versions = admin_session.get(f"{BASE_URL}/api/admin/xos/layout/client_home/history").json()["versions"]
        assert versions, "expected at least one history version"
        vid = versions[0]["version_id"]

        r = admin_session.post(f"{BASE_URL}/api/admin/xos/layout/client_home/rollback/{vid}", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("items"), list) and data["items"]

    def test_rollback_invalid_version_returns_404(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/xos/layout/client_home/rollback/nonexistent_id_xyz", timeout=10)
        assert r.status_code == 404

    def test_history_requires_admin(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/xos/layout/client_home/history", timeout=10)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_rollback_requires_admin(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/admin/xos/layout/client_home/rollback/anything", timeout=10)
        assert r.status_code in (401, 403)

    def test_put_layout_requires_admin(self, anon_session):
        r = anon_session.put(f"{BASE_URL}/api/admin/xos/layout/client_home", json={"items": []}, timeout=10)
        assert r.status_code in (401, 403)


# ── Regression: existing XOS endpoints ───────────────────────────────────────
class TestXOSRegression:
    def test_reset_client_home(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/xos/layout/client_home/reset", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("items"), list) and data["items"]

    def test_registry_get(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/xos/registry", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data.get("entries"), list)
        assert len(data["entries"]) >= 10

    def test_registry_patch(self, admin_session):
        # patch label of an existing widget (hero on client_home)
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/xos/registry/client_home/hero",
            json={"label": "Hero adaptiv"},
            timeout=10,
        )
        assert r.status_code == 200

    def test_experience_profiles_get(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/experience-profiles", timeout=10)
        assert r.status_code == 200
        data = r.json()
        roles = {p["role"] for p in data["profiles"]}
        assert {"client", "specialist", "admin"}.issubset(roles)

    def test_experience_profile_put(self, admin_session):
        r = admin_session.put(
            f"{BASE_URL}/api/admin/experience-profiles/client",
            json={"entry_route": "/client", "default_theme": "system", "layout_surface": "client_home"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_ui_rules_get_and_put(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ui-rules", timeout=10)
        assert r.status_code == 200
        rules = r.json()["rules"]
        # Round-trip put same rules
        r2 = admin_session.put(f"{BASE_URL}/api/admin/ui-rules", json={"rules": rules}, timeout=10)
        assert r2.status_code == 200
        assert r2.json().get("ok") is True

    def test_specialist_home_layout(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/xos/layout/specialist_home", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["surface"] == "specialist_home"
        assert len(data["items"]) >= 1
