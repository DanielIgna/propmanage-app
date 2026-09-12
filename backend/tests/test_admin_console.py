"""Backend tests for the new Metronic-style Admin Console (admin_console router)."""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_client():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT)


# ============= AUTH / RBAC =============
class TestAuthRBAC:
    def test_admin_login_sets_cookie(self):
        s = _login(ADMIN)
        cookies = s.cookies.get_dict()
        assert any(k for k in cookies.keys()), f"no cookies set: {cookies}"
        me = s.get(f"{BASE_URL}/api/auth/me")
        assert me.status_code == 200
        assert me.json().get("role") == "admin"

    def test_non_admin_forbidden_on_admin_endpoints(self, client_session):
        endpoints = [
            "/api/admin/cms",
            "/api/admin/email-templates",
            "/api/admin/zones",
            "/api/admin/trust-weights",
            "/api/admin/settings",
            "/api/admin/users",
            "/api/admin/finance/overview",
            "/api/admin/projects",
            "/api/admin/activity-feed-live",
            "/api/admin/search?q=admin",
        ]
        for ep in endpoints:
            r = client_session.get(f"{BASE_URL}{ep}")
            assert r.status_code == 403, f"{ep} expected 403 got {r.status_code}"


# ============= CMS =============
class TestCMS:
    def test_list_cms_returns_25_plus(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/cms")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 25, f"expected >=25 cms entries, got {len(data)}"
        sample = data[0]
        for fld in ("key", "value", "default", "is_overridden"):
            assert fld in sample, f"missing field {fld}"

    def test_upsert_cms_override_and_reset(self, admin_client):
        key = "hero.title1"
        # upsert
        r = admin_client.put(f"{BASE_URL}/api/admin/cms", json={"key": key, "value": "TEST_OVERRIDE"})
        assert r.status_code == 200
        # verify override visible in list
        r = admin_client.get(f"{BASE_URL}/api/admin/cms")
        entry = next(e for e in r.json() if e["key"] == key)
        assert entry["value"] == "TEST_OVERRIDE"
        assert entry["is_overridden"] is True
        # verify in public endpoint
        pub = requests.get(f"{BASE_URL}/api/cms/public")
        assert pub.status_code == 200
        assert pub.json().get(key) == "TEST_OVERRIDE"
        # reset
        r = admin_client.delete(f"{BASE_URL}/api/admin/cms/{key}")
        assert r.status_code == 200
        r = admin_client.get(f"{BASE_URL}/api/admin/cms")
        entry = next(e for e in r.json() if e["key"] == key)
        assert entry["is_overridden"] is False

    def test_cms_public_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/cms/public")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        assert "hero.title1" in data


# ============= EMAIL TEMPLATES =============
class TestEmailTemplates:
    def test_list_returns_5_templates(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/email-templates")
        assert r.status_code == 200
        data = r.json()
        ids = {t["id"] for t in data}
        assert ids >= {"welcome", "dispute_opened", "dispute_resolved", "escrow_funded", "specialist_verified"}

    def test_update_and_reset(self, admin_client):
        tid = "welcome"
        r = admin_client.put(
            f"{BASE_URL}/api/admin/email-templates/{tid}",
            json={"subject": "TEST_SUBJ", "html": "<p>TEST</p>"},
        )
        assert r.status_code == 200
        r = admin_client.get(f"{BASE_URL}/api/admin/email-templates")
        entry = next(t for t in r.json() if t["id"] == tid)
        assert entry["subject"] == "TEST_SUBJ"
        assert entry["is_overridden"] is True
        # reset
        r = admin_client.delete(f"{BASE_URL}/api/admin/email-templates/{tid}")
        assert r.status_code == 200
        r = admin_client.get(f"{BASE_URL}/api/admin/email-templates")
        entry = next(t for t in r.json() if t["id"] == tid)
        assert entry["is_overridden"] is False

    def test_update_unknown_template_404(self, admin_client):
        r = admin_client.put(
            f"{BASE_URL}/api/admin/email-templates/does_not_exist",
            json={"subject": "x", "html": "y"},
        )
        assert r.status_code == 404


# ============= ZONES =============
class TestZones:
    def test_list_zones_170_plus(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/zones")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 170, f"expected >=170 zones, got {len(data)}"
        sources = {z.get("source") for z in data}
        assert "seed" in sources

    def test_add_toggle_remove_custom_zone(self, admin_client):
        # add custom zone
        payload = {"country": "România", "city": "TEST_City", "zone": "TEST_Zone_Custom"}
        r = admin_client.post(f"{BASE_URL}/api/admin/zones", json=payload)
        assert r.status_code == 200, r.text
        zid = r.json()["id"]
        # duplicate fails
        r = admin_client.post(f"{BASE_URL}/api/admin/zones", json=payload)
        assert r.status_code == 400
        # toggle a real seed zone
        zones = admin_client.get(f"{BASE_URL}/api/admin/zones").json()
        seed = next(z for z in zones if z["source"] == "seed")
        seed_payload = {"country": seed["country"], "city": seed["city"], "zone": seed["zone"]}
        r = admin_client.post(f"{BASE_URL}/api/admin/zones/toggle", json=seed_payload)
        assert r.status_code == 200 and r.json()["disabled"] is True
        # toggle back
        r = admin_client.post(f"{BASE_URL}/api/admin/zones/toggle", json=seed_payload)
        assert r.status_code == 200 and r.json()["disabled"] is False
        # remove custom
        r = admin_client.delete(f"{BASE_URL}/api/admin/zones/custom/{zid}")
        assert r.status_code == 200


# ============= TRUST WEIGHTS =============
class TestTrustWeights:
    def test_get_default_sums_to_one(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/trust-weights")
        assert r.status_code == 200
        d = r.json()
        keys = ["on_time", "reviews", "photos", "complaints_penalty", "verification_bonus"]
        s = sum(d[k] for k in keys)
        assert abs(s - 1.0) < 0.01

    def test_put_rejects_bad_sum(self, admin_client):
        r = admin_client.put(f"{BASE_URL}/api/admin/trust-weights", json={
            "on_time": 0.5, "reviews": 0.5, "photos": 0.5,
            "complaints_penalty": 0.0, "verification_bonus": 0.0,
        })
        assert r.status_code == 400

    def test_put_accepts_valid(self, admin_client):
        weights = {"on_time": 0.4, "reviews": 0.3, "photos": 0.1, "complaints_penalty": 0.1, "verification_bonus": 0.1}
        r = admin_client.put(f"{BASE_URL}/api/admin/trust-weights", json=weights)
        assert r.status_code == 200
        # verify persisted
        r = admin_client.get(f"{BASE_URL}/api/admin/trust-weights")
        for k, v in weights.items():
            assert abs(r.json()[k] - v) < 0.001


# ============= SETTINGS =============
class TestSettings:
    def test_get_settings_defaults(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/settings")
        assert r.status_code == 200
        d = r.json()
        for k in ("stripe_live", "resend_live", "platform_commission_pct", "lead_fee_ron",
                  "primary_color", "logo_text", "support_email", "maintenance_mode"):
            assert k in d

    def test_partial_update(self, admin_client):
        r = admin_client.put(f"{BASE_URL}/api/admin/settings", json={"platform_commission_pct": 7.5})
        assert r.status_code == 200
        r = admin_client.get(f"{BASE_URL}/api/admin/settings")
        assert r.json()["platform_commission_pct"] == 7.5
        # reset
        admin_client.put(f"{BASE_URL}/api/admin/settings", json={"platform_commission_pct": 5.0})


# ============= USERS =============
class TestUsers:
    def test_list_filtered(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/users", params={"q": "admin", "role": "admin", "limit": 10})
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d
        for u in d["items"]:
            assert u["role"] == "admin"

    def test_patch_and_ban_unban(self, admin_client):
        # find a non-admin user
        r = admin_client.get(f"{BASE_URL}/api/admin/users", params={"role": "client", "limit": 1})
        items = r.json()["items"]
        if not items:
            pytest.skip("no client users to test")
        uid = items[0]["id"]
        # patch
        r = admin_client.patch(f"{BASE_URL}/api/admin/users/{uid}", json={"tier": "GOLD"})
        assert r.status_code == 200
        # ban
        r = admin_client.post(f"{BASE_URL}/api/admin/users/{uid}/ban")
        assert r.status_code == 200
        # unban
        r = admin_client.post(f"{BASE_URL}/api/admin/users/{uid}/unban")
        assert r.status_code == 200


# ============= SEARCH / FINANCE / PROJECTS / ACTIVITY =============
class TestMisc:
    def test_global_search(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/search", params={"q": "admin"})
        assert r.status_code == 200
        d = r.json()
        for k in ("users", "requests", "projects"):
            assert k in d

    def test_finance_overview(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/finance/overview")
        assert r.status_code == 200
        d = r.json()
        for k in ("total_wallet", "escrow_held", "top_wallets", "tx_by_type"):
            assert k in d
        assert len(d["top_wallets"]) <= 10

    def test_projects_list(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/projects")
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d

    def test_activity_feed(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/activity-feed-live", params={"limit": 12})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ============= CSV EXPORTS =============
class TestCSVExports:
    @pytest.mark.parametrize("path", ["/api/admin/export/users.csv",
                                       "/api/admin/export/transactions.csv",
                                       "/api/admin/export/disputes.csv"])
    def test_csv_export(self, admin_client, path):
        r = admin_client.get(f"{BASE_URL}{path}")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert len(r.text) > 0
