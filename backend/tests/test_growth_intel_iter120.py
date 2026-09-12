"""Iteration 120 — Growth Intelligence (Sprint GI-1, Board 004/005/006) tests."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CLIENT, timeout=15)
    assert r.status_code == 200, f"client login failed: {r.status_code}"
    return s


# ============ Growth Intelligence: POST /run ============
class TestGrowthRun:
    def test_run_scan_structure(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/growth-intel/run", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["generated_at", "trigger", "period_days", "kpi_snapshot",
                  "ux_problems", "abandon_pages", "journeys", "behavior", "recommendations"]:
            assert k in d, f"missing key {k}"
        assert d["trigger"] == "manual"
        kpi = d["kpi_snapshot"]
        for k in ["sessions", "visitors", "bounce_rate_pct", "avg_pvi", "active_opportunities"]:
            assert k in kpi, f"missing kpi.{k}"
        assert kpi["sessions"] > 0, "should have real sessions"
        # behavior structure
        b = d["behavior"]
        for k in ["sample_sessions", "best_post_time", "best_whatsapp_time",
                  "source_comparison", "top_service", "opportunity_conversion"]:
            assert k in b, f"missing behavior.{k}"
        assert b["sample_sessions"] > 0
        # recommendations
        assert isinstance(d["recommendations"], list) and len(d["recommendations"]) > 0
        valid_cats = {"ux", "marketing", "comercial", "operational", "ceo"}
        valid_vals = {"confirmed_real", "partially_confirmed", "ai_hypothesis", "rejected"}
        for r_ in d["recommendations"]:
            for k in ["id", "title", "why", "category", "validation", "evidence", "kpi"]:
                assert k in r_, f"reco missing {k}: {r_}"
            assert r_["category"] in valid_cats, f"bad category: {r_['category']}"
            assert r_["validation"] in valid_vals, f"bad validation: {r_['validation']}"

    def test_validation_logic_board006(self, admin_session):
        """Board 006: sample>=20 => confirmed/partial; sample<20 => ai_hypothesis."""
        r = admin_session.post(f"{BASE_URL}/api/admin/growth-intel/run", timeout=60)
        d = r.json()
        b = d["behavior"]
        # best_whatsapp_time cu weight mic (few WA sessions) trebuie să fie ai_hypothesis
        bwt = b["best_whatsapp_time"]
        if bwt.get("sample", 0) < 20:
            assert bwt["validation"] == "ai_hypothesis", \
                f"WA sample={bwt.get('sample')} => expected ai_hypothesis, got {bwt['validation']}"
        # ux problems: verifică regula
        for p in d["ux_problems"]:
            if p["sample"] >= 20:
                assert p["validation"] in ("confirmed_real", "partially_confirmed")
            else:
                assert p["validation"] == "ai_hypothesis"


# ============ GET /latest ============
class TestGrowthLatest:
    def test_latest_returns_persisted(self, admin_session):
        # ensure a run exists
        admin_session.post(f"{BASE_URL}/api/admin/growth-intel/run", timeout=60)
        r = admin_session.get(f"{BASE_URL}/api/admin/growth-intel/latest", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "kpi_snapshot" in d and "recommendations" in d
        assert "_id" not in d  # must be stripped


# ============ GET /behavior ============
class TestBehaviorEndpoint:
    def test_behavior_default(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/growth-intel/behavior?days=60", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["sample_sessions"] > 0

    def test_behavior_validation_days_too_low(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/growth-intel/behavior?days=5", timeout=15)
        assert r.status_code == 422, f"expected 422 got {r.status_code}"


# ============ Security ============
class TestSecurity:
    def test_no_auth_run(self):
        r = requests.post(f"{BASE_URL}/api/admin/growth-intel/run", timeout=15)
        assert r.status_code in (401, 403), f"got {r.status_code}"

    def test_no_auth_latest(self):
        r = requests.get(f"{BASE_URL}/api/admin/growth-intel/latest", timeout=15)
        assert r.status_code in (401, 403)

    def test_no_auth_behavior(self):
        r = requests.get(f"{BASE_URL}/api/admin/growth-intel/behavior", timeout=15)
        assert r.status_code in (401, 403)

    def test_client_forbidden_run(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/admin/growth-intel/run", timeout=15)
        assert r.status_code in (401, 403), f"client got {r.status_code}"

    def test_client_forbidden_latest(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/growth-intel/latest", timeout=15)
        assert r.status_code in (401, 403)

    def test_client_forbidden_behavior(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/growth-intel/behavior", timeout=15)
        assert r.status_code in (401, 403)


# ============ Event bus emission ============
class TestEventEmission:
    def test_growth_scan_event(self, admin_session):
        admin_session.post(f"{BASE_URL}/api/admin/growth-intel/run", timeout=60)
        # activity_events endpoint (common pattern)
        r = admin_session.get(f"{BASE_URL}/api/admin/activity/events?limit=50", timeout=15)
        if r.status_code != 200:
            # try alt endpoint
            r = admin_session.get(f"{BASE_URL}/api/admin/activity-events?limit=50", timeout=15)
        if r.status_code == 200:
            data = r.json()
            events = data if isinstance(data, list) else data.get("events", data.get("items", []))
            types = [e.get("type") or e.get("event") for e in events]
            assert any(t == "growth.scan_completed" for t in types), f"event not found in {types[:20]}"
        else:
            pytest.skip(f"activity endpoint not found: {r.status_code}")


# ============ Command Center integration ============
class TestCommandCenterIntegration:
    def test_recommendations_have_category(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/command-center/recommendations", timeout=45)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ai_generated") is True, f"expected ai_generated=True, got {d.get('ai_generated')}"
        recs = d.get("recommendations", [])
        assert len(recs) > 0
        for rec in recs:
            assert "category" in rec, f"reco missing category: {rec}"

    def test_command_center_feed_regression(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=20)
        assert r.status_code == 200


# ============ Regressions ============
class TestRegressions:
    def test_ceo_endpoint(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ceo", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "value_loop" in d, f"missing value_loop key: {list(d.keys())[:20]}"

    def test_value_loop_stats(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/value-loop/stats", timeout=20)
        assert r.status_code == 200
