"""Iteration 109 — XOS Multi-surface + Experience Profiles + Registry tenant.

Covers Etapa 1.2 (Multi-surface Layout Engine) and 1.3 (Role Experience Manager):
- GET /api/xos/layout/specialist_home returns 5 widgets (today_summary, cockpit, quests, tier_tools, tier_progress)
- GET /api/admin/xos/surfaces returns 2 surfaces (client_home 5 widgets, specialist_home 5 widgets)
- PUT /api/admin/xos/layout/specialist_home reorder+disable persists and reset restores
- GET/PUT /api/admin/experience-profiles/{role}
- GET /api/admin/xos/registry returns entries with tenant_id=main
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "1!nasov01ADMIN")
ADMIN = {"email": "admin@propmanage.io", "password": SEED_ADMIN_PASSWORD}

SPECIALIST_WIDGETS = ["today_summary", "cockpit", "quests", "tier_tools", "tier_progress"]
CLIENT_WIDGETS = ["hero", "quick_actions", "copilot", "contextual", "discover"]


# ─────────────────── Fixtures ───────────────────
@pytest.fixture(scope="module")
def public_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    if r.status_code != 200:
        # try Admin123!
        r = s.post(f"{API}/auth/login", json={"email": ADMIN["email"], "password": "Admin123!"}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


@pytest.fixture(scope="module", autouse=True)
def _cleanup(admin_client):
    yield
    # Restore specialist_home layout
    try:
        admin_client.post(f"{API}/admin/xos/layout/specialist_home/reset", timeout=15)
    except Exception:
        pass
    try:
        admin_client.post(f"{API}/admin/xos/layout/client_home/reset", timeout=15)
    except Exception:
        pass
    # Restore experience profiles defaults
    for role, defaults in [
        ("client", {"entry_route": "/client", "default_theme": "system", "layout_surface": "client_home"}),
        ("specialist", {"entry_route": "/specialist", "default_theme": "system", "layout_surface": "specialist_home"}),
        ("admin", {"entry_route": "/admin", "default_theme": "system", "layout_surface": ""}),
    ]:
        try:
            admin_client.put(f"{API}/admin/experience-profiles/{role}", json=defaults, timeout=15)
        except Exception:
            pass


# ─────────────────── Specialist Layout ───────────────────
class TestSpecialistLayout:
    def test_public_specialist_layout_no_auth(self, public_client):
        r = public_client.get(f"{API}/xos/layout/specialist_home", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("surface") == "specialist_home"
        items = data.get("items") or []
        ids = [i["id"] for i in items]
        for w in SPECIALIST_WIDGETS:
            assert w in ids, f"missing widget {w}, got {ids}"
        assert len(items) == 5
        for it in items:
            assert it.get("enabled") is True

    def test_public_client_layout_still_5(self, public_client):
        r = public_client.get(f"{API}/xos/layout/client_home", timeout=15)
        assert r.status_code == 200
        ids = [i["id"] for i in r.json()["items"]]
        for w in CLIENT_WIDGETS:
            assert w in ids

    def test_admin_surfaces_returns_2(self, admin_client):
        r = admin_client.get(f"{API}/admin/xos/surfaces", timeout=15)
        assert r.status_code == 200, r.text
        surfaces = r.json().get("surfaces") or []
        surface_map = {s["surface"]: s for s in surfaces}
        assert "client_home" in surface_map
        assert "specialist_home" in surface_map
        assert len(surface_map["client_home"]["widgets"]) == 5
        assert len(surface_map["specialist_home"]["widgets"]) == 5
        assert surface_map["specialist_home"]["label"] == "Dashboard Specialist · Oportunități"

    def test_put_specialist_layout_reorder_disable(self, admin_client, public_client):
        items = [
            {"id": "quests", "enabled": False},
            {"id": "today_summary", "enabled": True},
            {"id": "cockpit", "enabled": True},
            {"id": "tier_progress", "enabled": True},
            {"id": "tier_tools", "enabled": True},
        ]
        pr = admin_client.put(f"{API}/admin/xos/layout/specialist_home",
                              json={"items": items}, timeout=15)
        assert pr.status_code == 200, pr.text

        pub = public_client.get(f"{API}/xos/layout/specialist_home", timeout=15).json()
        pub_items = pub["items"]
        assert pub_items[0]["id"] == "quests"
        assert pub_items[0]["enabled"] is False
        assert pub_items[1]["id"] == "today_summary"

    def test_reset_specialist_restores(self, admin_client, public_client):
        rr = admin_client.post(f"{API}/admin/xos/layout/specialist_home/reset", timeout=15)
        assert rr.status_code == 200
        pub = public_client.get(f"{API}/xos/layout/specialist_home", timeout=15).json()
        assert pub["items"][0]["id"] == "today_summary"
        for it in pub["items"]:
            assert it["enabled"] is True


# ─────────────────── Experience Profiles ───────────────────
class TestExperienceProfiles:
    def test_get_profile_client(self, public_client):
        r = public_client.get(f"{API}/experience/profile/client", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["role"] == "client"
        assert data["entry_route"] == "/client"
        assert data["default_theme"] == "system"
        assert data["layout_surface"] == "client_home"

    def test_get_profile_specialist(self, public_client):
        r = public_client.get(f"{API}/experience/profile/specialist", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["entry_route"] == "/specialist"
        assert data["layout_surface"] == "specialist_home"

    def test_get_profile_admin(self, public_client):
        r = public_client.get(f"{API}/experience/profile/admin", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["entry_route"] == "/admin"

    def test_unknown_role_404(self, public_client):
        r = public_client.get(f"{API}/experience/profile/xyz", timeout=15)
        assert r.status_code == 404

    def test_admin_list_profiles(self, admin_client):
        r = admin_client.get(f"{API}/admin/experience-profiles", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data["profiles"]) == 3
        assert set(data["themes"]) == {"system", "dark", "light"}
        assert "specialist_home" in data["surfaces"]
        assert "client_home" in data["surfaces"]

    def test_put_profile_persists(self, admin_client, public_client):
        r = admin_client.put(f"{API}/admin/experience-profiles/client",
                             json={"entry_route": "/client/onboarding", "default_theme": "dark",
                                   "layout_surface": "client_home"}, timeout=15)
        assert r.status_code == 200, r.text
        # Verify via public GET
        pub = public_client.get(f"{API}/experience/profile/client", timeout=15).json()
        assert pub["entry_route"] == "/client/onboarding"
        assert pub["default_theme"] == "dark"

    def test_restore_client_profile(self, admin_client, public_client):
        r = admin_client.put(f"{API}/admin/experience-profiles/client",
                             json={"entry_route": "/client", "default_theme": "system",
                                   "layout_surface": "client_home"}, timeout=15)
        assert r.status_code == 200
        pub = public_client.get(f"{API}/experience/profile/client", timeout=15).json()
        assert pub["entry_route"] == "/client"
        assert pub["default_theme"] == "system"

    def test_put_unknown_role_404(self, admin_client):
        r = admin_client.put(f"{API}/admin/experience-profiles/xyz",
                             json={"entry_route": "/x"}, timeout=15)
        assert r.status_code == 404

    def test_put_invalid_route_rejected(self, admin_client):
        # entry_route without leading / is ignored -> 400 (nothing valid)
        r = admin_client.put(f"{API}/admin/experience-profiles/client",
                             json={"entry_route": "invalid", "default_theme": "invalid_theme"},
                             timeout=15)
        assert r.status_code == 400


# ─────────────────── Registry Tenant ───────────────────
class TestRegistry:
    def test_registry_all_tenant_main(self, admin_client):
        r = admin_client.get(f"{API}/admin/xos/registry", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        entries = data.get("entries") or []
        assert len(entries) >= 10  # 5 client + 5 specialist
        # tenant_id should be present on all
        missing_tenant = [e for e in entries if e.get("tenant_id") != "main"]
        assert not missing_tenant, f"Entries missing tenant_id=main: {[e['id'] for e in missing_tenant]}"
        # surfaces cover client_home + specialist_home
        surfaces = {e["surface"] for e in entries}
        assert "client_home" in surfaces
        assert "specialist_home" in surfaces
        # widget ids include specialist widgets
        ids = {e["id"] for e in entries}
        for w in SPECIALIST_WIDGETS:
            assert w in ids

    def test_admin_surfaces_requires_auth(self, public_client):
        r = public_client.get(f"{API}/admin/xos/surfaces", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_experience_profiles_requires_auth(self, public_client):
        r = public_client.get(f"{API}/admin/experience-profiles", timeout=15)
        assert r.status_code in (401, 403)
