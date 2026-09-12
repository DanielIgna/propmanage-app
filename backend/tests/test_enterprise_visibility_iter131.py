"""Enterprise Visibility (Execution Order 002 — V2 Inspector + V3 Explorer + Architecture) tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
FOUNDER = ("danieligna1@gmail.com", "Founder2026!kc")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")

WIDGETS = [
    "ceo.enterprise_status",
    "ceo.one_thing",
    "ceo.autonomous_execution",
    "health.overall",
    "ops.autonomous_followup",
    "warroom.mission100",
]


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def founder():
    return _login(*FOUNDER)


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


# --- Inspector endpoints ---
class TestInspector:
    @pytest.mark.parametrize("widget_id", WIDGETS)
    def test_widget_ok(self, founder, widget_id):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/inspector/{widget_id}", timeout=30)
        assert r.status_code == 200, f"{widget_id}: {r.status_code} {r.text[:200]}"
        d = r.json()
        for field in ("name", "purpose", "business_value", "inputs", "outputs",
                      "engine", "api", "database", "cron", "documents",
                      "related_dashboards", "truth_classification", "dependencies"):
            assert field in d, f"{widget_id} missing field {field}"
        # engine should be resolved to an object with a name
        assert isinstance(d["engine"], dict) and d["engine"].get("name"), f"{widget_id} engine not resolved: {d['engine']}"
        # database is a list, documents is a list
        assert isinstance(d["database"], list)
        assert isinstance(d["documents"], list)
        assert isinstance(d["related_dashboards"], list)
        assert isinstance(d["dependencies"], list)
        # each dependency edge should have source_name/target_name/evidence
        for edge in d["dependencies"]:
            for k in ("source_name", "target_name", "evidence"):
                assert k in edge, f"{widget_id} dep missing {k}: {edge}"

    def test_inexistent_widget_404(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/inspector/does.not.exist", timeout=30)
        assert r.status_code == 404, f"expected 404, got {r.status_code}"

    def test_admin_forbidden(self, admin):
        r = admin.get(f"{BASE_URL}/api/founder/knowledge/inspector/ceo.enterprise_status", timeout=30)
        assert r.status_code == 403

    def test_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/founder/knowledge/inspector/ceo.enterprise_status", timeout=30)
        assert r.status_code in (401, 403)


# --- Architecture endpoint ---
class TestArchitecture:
    EXPECTED_BLOCKS = [
        "system_zero",  # first
        "client",       # last
    ]

    def test_architecture_ok(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/architecture", timeout=30)
        assert r.status_code == 200
        d = r.json()
        blocks = d.get("blocks") if isinstance(d, dict) else d
        assert isinstance(blocks, list)
        assert len(blocks) == 11, f"expected 11 blocks, got {len(blocks)}"
        ids = [b["id"] for b in blocks]
        for req in self.EXPECTED_BLOCKS:
            assert req in ids, f"missing block {req}, got {ids}"
        for b in blocks:
            for field in ("id", "layer", "description", "files", "routes", "api", "database", "next"):
                assert field in b, f"block {b.get('id')} missing {field}"

    def test_admin_forbidden(self, admin):
        r = admin.get(f"{BASE_URL}/api/founder/knowledge/architecture", timeout=30)
        assert r.status_code == 403

    def test_unauth(self):
        r = requests.get(f"{BASE_URL}/api/founder/knowledge/architecture", timeout=30)
        assert r.status_code in (401, 403)


# --- Regression ---
class TestRegression:
    def test_registry_still_46_44(self, founder):
        r = founder.get(f"{BASE_URL}/api/founder/knowledge/registry", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["stats"]["nodes"] == 46
        assert d["stats"]["edges"] == 44

    def test_operations_still_up(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/operations", timeout=30)
        assert r.status_code == 200
