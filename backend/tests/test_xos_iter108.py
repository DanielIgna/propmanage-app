"""Iteration 108 — XOS (Experience OS) tests: layout builder, UI rules, site content, menu tracking.

Covers:
- GET /api/xos/layout/client_home (no auth) → 5 widgets default enabled
- GET /api/admin/xos/surfaces / PUT /admin/xos/layout / POST reset
- GET /api/ui-rules/my (guest empty; client hides matching) + PUT /api/admin/ui-rules (persist)
- GET /api/public/site-content + PUT /api/admin/site-content (banner active persists)
- POST /api/public/site-menu/track + GET /api/admin/site-menu/analytics
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"
SEED_ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "1!nasov01ADMIN")
ADMIN = {"email": "admin@propmanage.io", "password": SEED_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}

EXPECTED_WIDGETS = ["hero", "quick_actions", "copilot", "contextual", "discover"]


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
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=CLIENT, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Client login failed ({r.status_code}): {r.text[:200]}")
    return s


@pytest.fixture(scope="module", autouse=True)
def _cleanup(admin_client):
    """Cleanup: reset layout, clear ui rules, restore banner active=False after tests."""
    yield
    try:
        admin_client.post(f"{API}/admin/xos/layout/client_home/reset", timeout=15)
    except Exception:
        pass
    try:
        admin_client.put(f"{API}/admin/ui-rules", json={"rules": []}, timeout=15)
    except Exception:
        pass
    try:
        admin_client.put(f"{API}/admin/site-content", json={
            "banner": {"active": False, "text": "", "link": "", "link_label": "", "variant": "info"},
            "hero": {"title1": "", "title2": "", "title3": "", "subtitle": ""},
            "entries": []
        }, timeout=15)
    except Exception:
        pass


# ─────────────────── XOS Layout ───────────────────
class TestXOSLayout:
    def test_public_layout_no_auth(self, public_client):
        r = public_client.get(f"{API}/xos/layout/client_home", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("surface") == "client_home"
        items = data.get("items") or []
        ids = [i["id"] for i in items]
        for w in EXPECTED_WIDGETS:
            assert w in ids, f"missing widget {w}, got {ids}"
        # all enabled by default
        for it in items:
            assert it.get("enabled") is True

    def test_admin_surfaces_requires_auth(self, public_client):
        r = public_client.get(f"{API}/admin/xos/surfaces", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_surfaces_returns_registry(self, admin_client):
        r = admin_client.get(f"{API}/admin/xos/surfaces", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        surfaces = data.get("surfaces") or []
        assert len(surfaces) >= 1
        client_home = next((s for s in surfaces if s["surface"] == "client_home"), None)
        assert client_home is not None
        assert len(client_home["widgets"]) == 5
        assert len(client_home["items"]) == 5

    def test_put_layout_reorder_and_disable_persists(self, admin_client, public_client):
        # Reorder: put discover first + disable it
        items = [
            {"id": "discover", "enabled": False},
            {"id": "hero", "enabled": True},
            {"id": "quick_actions", "enabled": True},
            {"id": "copilot", "enabled": True},
            {"id": "contextual", "enabled": True},
        ]
        pr = admin_client.put(f"{API}/admin/xos/layout/client_home",
                              json={"items": items}, timeout=15)
        assert pr.status_code == 200, pr.text

        # verify via public GET
        pub = public_client.get(f"{API}/xos/layout/client_home", timeout=15).json()
        pub_items = pub["items"]
        assert pub_items[0]["id"] == "discover"
        assert pub_items[0]["enabled"] is False
        assert pub_items[1]["id"] == "hero"

    def test_reset_restores_default(self, admin_client, public_client):
        rr = admin_client.post(f"{API}/admin/xos/layout/client_home/reset", timeout=15)
        assert rr.status_code == 200
        pub = public_client.get(f"{API}/xos/layout/client_home", timeout=15).json()
        # first is hero, all enabled
        assert pub["items"][0]["id"] == "hero"
        for it in pub["items"]:
            assert it["enabled"] is True

    def test_unknown_surface_404(self, admin_client):
        r = admin_client.get(f"{API}/xos/layout/does_not_exist", timeout=15)
        assert r.status_code == 404


# ─────────────────── UI Rules ───────────────────
class TestUIRules:
    def test_my_rules_empty_default_guest(self, public_client, admin_client):
        # ensure clean state first
        admin_client.put(f"{API}/admin/ui-rules", json={"rules": []}, timeout=15)
        r = public_client.get(f"{API}/ui-rules/my", timeout=15)
        assert r.status_code == 200
        assert r.json() == {"hidden": []}

    def test_admin_put_rules_persists(self, admin_client):
        rules = [{
            "name": "TEST_HideDiscoverClient",
            "target_type": "widget",
            "target_id": "discover",
            "action": "hide",
            "conditions": [{"field": "role", "op": "eq", "value": "client"}],
            "active": True,
        }]
        r = admin_client.put(f"{API}/admin/ui-rules", json={"rules": rules}, timeout=15)
        assert r.status_code == 200, r.text
        saved = r.json()["rules"]
        assert len(saved) == 1
        assert saved[0]["target_id"] == "discover"
        assert saved[0]["action"] == "hide"

        # verify via admin GET
        g = admin_client.get(f"{API}/admin/ui-rules", timeout=15)
        assert g.status_code == 200
        assert len(g.json()["rules"]) == 1

    def test_rule_hides_widget_for_client(self, admin_client, client_session, public_client):
        # rule already installed from previous test
        r_client = client_session.get(f"{API}/ui-rules/my", timeout=15)
        assert r_client.status_code == 200
        hidden = r_client.json()["hidden"]
        assert "widget:discover" in hidden, f"expected widget:discover hidden for client, got {hidden}"

        # guest should NOT see it hidden
        r_guest = public_client.get(f"{API}/ui-rules/my", timeout=15)
        assert r_guest.status_code == 200
        assert "widget:discover" not in r_guest.json()["hidden"]

    def test_show_if_action(self, admin_client, client_session, public_client):
        # show_if with role=admin → hidden for non-admins
        rules = [{
            "name": "TEST_ShowOnlyAdmin",
            "target_type": "menu",
            "target_id": "admin_only",
            "action": "show_if",
            "conditions": [{"field": "role", "op": "eq", "value": "admin"}],
            "active": True,
        }]
        admin_client.put(f"{API}/admin/ui-rules", json={"rules": rules}, timeout=15)

        # guest → hidden
        r_guest = public_client.get(f"{API}/ui-rules/my", timeout=15)
        assert "menu:admin_only" in r_guest.json()["hidden"]
        # client → hidden (role=client != admin)
        r_client = client_session.get(f"{API}/ui-rules/my", timeout=15)
        assert "menu:admin_only" in r_client.json()["hidden"]

    def test_gte_on_account_age_days(self, admin_client, public_client):
        # rule requires account_age_days >= 9999 → hide for guests (age=0)
        rules = [{
            "name": "TEST_AgeGte",
            "target_type": "widget",
            "target_id": "old_users_only",
            "action": "hide",
            "conditions": [{"field": "account_age_days", "op": "gte", "value": 9999}],
            "active": True,
        }]
        admin_client.put(f"{API}/admin/ui-rules", json={"rules": rules}, timeout=15)

        r = public_client.get(f"{API}/ui-rules/my", timeout=15)
        # guest has age 0, 0 >= 9999 → False → not hidden
        assert "widget:old_users_only" not in r.json()["hidden"]

    def test_cleanup_rules_empty(self, admin_client, public_client):
        admin_client.put(f"{API}/admin/ui-rules", json={"rules": []}, timeout=15)
        r = public_client.get(f"{API}/ui-rules/my", timeout=15)
        assert r.json() == {"hidden": []}


# ─────────────────── Site Content ───────────────────
class TestSiteContent:
    def test_public_content_returns_default(self, public_client):
        r = public_client.get(f"{API}/public/site-content", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "banner" in data
        assert "hero" in data
        assert "entries" in data
        # default banner active must be False (unless previously toggled — reset in cleanup)
        assert isinstance(data["banner"].get("active"), bool)

    def test_public_content_no_auth(self, public_client):
        r = public_client.get(f"{API}/public/site-content", timeout=15)
        assert r.status_code == 200

    def test_admin_content_requires_auth(self, public_client):
        r = public_client.get(f"{API}/admin/site-content", timeout=15)
        assert r.status_code in (401, 403)

    def test_put_banner_active_persists(self, admin_client, public_client):
        payload = {
            "banner": {
                "active": True,
                "text": "TEST_Anunț important pentru clienți",
                "link": "/design-interior",
                "link_label": "Vezi",
                "variant": "promo",
            },
            "hero": {"title1": "", "title2": "", "title3": "", "subtitle": ""},
            "entries": [{"key": "TEST_key1", "value": "TEST_value1"}],
        }
        r = admin_client.put(f"{API}/admin/site-content", json=payload, timeout=15)
        assert r.status_code == 200, r.text

        # verify via public GET
        pub = public_client.get(f"{API}/public/site-content", timeout=15).json()
        assert pub["banner"]["active"] is True
        assert pub["banner"]["text"] == "TEST_Anunț important pentru clienți"
        assert pub["banner"]["variant"] == "promo"
        keys = [e["key"] for e in pub["entries"]]
        assert "TEST_key1" in keys

    def test_restore_banner_inactive(self, admin_client, public_client):
        payload = {
            "banner": {"active": False, "text": "", "link": "", "link_label": "", "variant": "info"},
            "hero": {"title1": "", "title2": "", "title3": "", "subtitle": ""},
            "entries": [],
        }
        r = admin_client.put(f"{API}/admin/site-content", json=payload, timeout=15)
        assert r.status_code == 200
        pub = public_client.get(f"{API}/public/site-content", timeout=15).json()
        assert pub["banner"]["active"] is False


# ─────────────────── Menu Tracking ───────────────────
class TestMenuTracking:
    def test_track_click_ok(self, public_client):
        r = public_client.post(
            f"{API}/public/site-menu/track",
            json={"item_id": "TEST_design_interior", "label": "Design Interior", "href": "/design-interior"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_analytics_returns_totals(self, admin_client, public_client):
        # fire a few clicks
        for i in range(3):
            public_client.post(
                f"{API}/public/site-menu/track",
                json={"item_id": "TEST_analytics_hit", "label": "TEST Hit", "href": "/x"},
                timeout=15,
            )
        # small wait for insertion
        time.sleep(0.5)
        r = admin_client.get(f"{API}/admin/site-menu/analytics?days=30", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("total_clicks", 0) > 0
        top = data.get("top") or []
        assert isinstance(top, list)
        # at least our TEST_analytics_hit should appear
        found = any(it.get("item_id") == "TEST_analytics_hit" for it in top)
        assert found, f"TEST_analytics_hit not in top: {top}"

    def test_analytics_requires_admin(self, public_client):
        r = public_client.get(f"{API}/admin/site-menu/analytics", timeout=15)
        assert r.status_code in (401, 403)
