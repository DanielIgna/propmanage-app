"""Iteration 151 — PropManage Audit + Service Manager (beta config) backend tests.
Verifies: /api/public/site-menu filter, /api/public/service-visibility, /api/public/services/{id},
admin site-menu fields + providers CRUD, platform rule for specialisti reactivation.
"""
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"

BETA_ACTIVE = {"imobile_verificate", "design_interior", "digital_twin", "mobilier"}
ALL_SERVICES = BETA_ACTIVE | {"design_exterior", "arhitectura", "constructii", "renovari",
                              "instalatii", "amenajari", "specialisti", "consultanta"}


@pytest.fixture(scope="module")
def session():
    return requests.Session()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


# ---------- Public site-menu filtering ----------
class TestPublicSiteMenu:
    def test_services_group_only_beta(self, session):
        r = session.get(f"{BASE_URL}/api/public/site-menu", timeout=10)
        assert r.status_code == 200
        items = r.json().get("items") or []
        servicii = next((g for g in items if g.get("id") == "servicii"), None)
        assert servicii, "grupul 'servicii' lipsește din meniul public"
        ids = {c["id"] for c in servicii.get("children") or []}
        assert ids == BETA_ACTIVE, f"expected only beta 4, got {ids}"


class TestServiceVisibility:
    def test_all_12_services_with_correct_active_flags(self, session):
        r = session.get(f"{BASE_URL}/api/public/service-visibility", timeout=10)
        assert r.status_code == 200
        services = r.json().get("services") or {}
        assert set(services.keys()) == ALL_SERVICES, f"missing/extra services: {set(services.keys()) ^ ALL_SERVICES}"
        for sid, meta in services.items():
            if sid in BETA_ACTIVE:
                assert meta["active"] is True, f"{sid} should be active"
            else:
                assert meta["active"] is False, f"{sid} should be inactive"
        assert services["specialisti"]["active"] is False


class TestServiceDetail:
    def test_mobilier_ok(self, session):
        r = session.get(f"{BASE_URL}/api/public/services/mobilier", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "mobilier"
        assert data["dest_type"] == "external"
        assert isinstance(data["providers"], list)
        # baseline should be empty (no test provider before write)
        # we don't hard-assert empty because state might vary, but ensure list

    def test_specialisti_404(self, session):
        r = session.get(f"{BASE_URL}/api/public/services/specialisti", timeout=10)
        assert r.status_code == 404

    def test_inexistent_404(self, session):
        r = session.get(f"{BASE_URL}/api/public/services/inexistent", timeout=10)
        assert r.status_code == 404


# ---------- Admin: fields present + provider write ----------
class TestAdminSiteMenu:
    def test_admin_get_has_new_fields(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/site-menu", timeout=10)
        assert r.status_code == 200
        items = r.json().get("items") or []
        servicii = next((g for g in items if g.get("id") == "servicii"), None)
        assert servicii
        required = {"description", "category", "image", "dest_type", "providers", "visible_site", "visible_marketplace"}
        for c in servicii["children"]:
            missing = required - set(c.keys())
            assert not missing, f"service {c['id']} missing fields: {missing}"

    def test_provider_add_and_retrieve_then_cleanup(self, admin_session, session):
        # GET current
        r = admin_session.get(f"{BASE_URL}/api/admin/site-menu", timeout=10)
        items = r.json()["items"]
        # inject provider on mobilier
        for group in items:
            if group.get("id") != "servicii":
                continue
            for c in group["children"]:
                if c["id"] == "mobilier":
                    c["providers"] = [{
                        "name": "TEST_ProviderX", "logo": "", "description": "TEST",
                        "url": "https://example.com", "priority": 5, "active": True,
                    }]
        put = admin_session.put(f"{BASE_URL}/api/admin/site-menu", json={"items": items}, timeout=15)
        assert put.status_code == 200

        # verify public endpoint returns provider
        pub = session.get(f"{BASE_URL}/api/public/services/mobilier", timeout=10)
        assert pub.status_code == 200
        provs = pub.json().get("providers") or []
        names = [p["name"] for p in provs]
        assert "TEST_ProviderX" in names

        # CLEANUP: reset providers=[] on mobilier
        r2 = admin_session.get(f"{BASE_URL}/api/admin/site-menu", timeout=10)
        items2 = r2.json()["items"]
        for group in items2:
            if group.get("id") != "servicii":
                continue
            for c in group["children"]:
                if c["id"] == "mobilier":
                    c["providers"] = []
        cleanup = admin_session.put(f"{BASE_URL}/api/admin/site-menu", json={"items": items2}, timeout=15)
        assert cleanup.status_code == 200
        pub2 = session.get(f"{BASE_URL}/api/public/services/mobilier", timeout=10)
        assert pub2.status_code == 200
        assert pub2.json().get("providers") == []


class TestPlatformRuleReactivation:
    def test_specialisti_activation_toggle(self, admin_session, session):
        # activate specialisti
        r = admin_session.get(f"{BASE_URL}/api/admin/site-menu", timeout=10)
        items = r.json()["items"]
        for group in items:
            if group.get("id") != "servicii":
                continue
            for c in group["children"]:
                if c["id"] == "specialisti":
                    c["active"] = True
                    c["visible_site"] = True
        put = admin_session.put(f"{BASE_URL}/api/admin/site-menu", json={"items": items}, timeout=15)
        assert put.status_code == 200

        vis = session.get(f"{BASE_URL}/api/public/service-visibility", timeout=10).json()["services"]
        assert vis["specialisti"]["active"] is True
        assert vis["specialisti"]["visible_site"] is True

        # RESET
        r2 = admin_session.get(f"{BASE_URL}/api/admin/site-menu", timeout=10)
        items2 = r2.json()["items"]
        for group in items2:
            if group.get("id") != "servicii":
                continue
            for c in group["children"]:
                if c["id"] == "specialisti":
                    c["active"] = False
                    c["visible_site"] = False
        put2 = admin_session.put(f"{BASE_URL}/api/admin/site-menu", json={"items": items2}, timeout=15)
        assert put2.status_code == 200

        vis2 = session.get(f"{BASE_URL}/api/public/service-visibility", timeout=10).json()["services"]
        assert vis2["specialisti"]["active"] is False
        # public service detail should return 404 again
        r_detail = session.get(f"{BASE_URL}/api/public/services/specialisti", timeout=10)
        assert r_detail.status_code == 404
