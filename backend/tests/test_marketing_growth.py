"""Backend tests for AI Marketing & Growth Department (Phase 1)."""
import os

import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read from frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

API = f"{BASE_URL}/api"

ADMIN_PASSWORDS = [OWNER_ADMIN_PASSWORD, OWNER_ADMIN_PASSWORD]
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


def _login(email: str, passwords):
    if isinstance(passwords, str):
        passwords = [passwords]
    last_resp = None
    for pw in passwords:
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
        last_resp = r
        if r.status_code == 200:
            return s, r
    return None, last_resp


@pytest.fixture(scope="session")
def admin_session():
    s, r = _login("admin@propmanage.io", ADMIN_PASSWORDS)
    if not s:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="session")
def client_session():
    s, r = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    if not s:
        pytest.skip(f"Client login failed: {r.status_code if r else 'n/a'}")
    return s


# ----- Dashboard -----

class TestDashboard:
    def test_dashboard_super_admin(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/dashboard", timeout=30)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        for k in ["users", "clients", "specialists", "financial", "marketplace"]:
            assert k in data, f"missing key {k}"

        # Users sub-keys
        for k in ["total", "new_30d", "active", "inactive", "retention_rate", "churn_rate"]:
            assert k in data["users"], f"missing users.{k}"

        # Clients sub-keys
        for k in ["total", "new_30d", "recurring", "avg_order_value", "estimated_ltv"]:
            assert k in data["clients"]

        # Specialists sub-keys
        for k in ["total", "active", "occupancy_rate", "avg_revenue_per_specialist", "accept_rate"]:
            assert k in data["specialists"]

        # Occupancy capped at 100%
        assert data["specialists"]["occupancy_rate"] <= 100.0, \
            f"Occupancy not capped: {data['specialists']['occupancy_rate']}"

        # Financial sub-keys
        for k in ["total_revenue", "monthly_revenue", "profit_estimated",
                  "taxes_collected", "by_category", "by_county", "daily_last_30d"]:
            assert k in data["financial"]

        # Marketplace
        for k in ["most_ordered", "funnel", "conversion_rate", "abandonment_rate", "completion_rate"]:
            assert k in data["marketplace"]
        for k in ["posted", "assigned", "confirmed", "abandoned"]:
            assert k in data["marketplace"]["funnel"]


# ----- RBAC -----

class TestRBAC:
    def test_dashboard_forbidden_for_client(self, client_session):
        r = client_session.get(f"{API}/admin/marketing/dashboard", timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code}"

    def test_dashboard_anonymous(self):
        r = requests.get(f"{API}/admin/marketing/dashboard", timeout=10)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_insights_forbidden_for_client(self, client_session):
        r = client_session.post(f"{API}/admin/marketing/insights", timeout=15)
        assert r.status_code == 403

    def test_copilot_forbidden_for_client(self, client_session):
        r = client_session.post(f"{API}/admin/marketing/copilot",
                                json={"message": "test"}, timeout=15)
        assert r.status_code == 403

    def test_segments_forbidden_for_client(self, client_session):
        r = client_session.get(f"{API}/admin/marketing/segments", timeout=15)
        assert r.status_code == 403


# ----- Segments -----

class TestSegments:
    def test_segments_buckets(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/segments", timeout=20)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "buckets" in data
        for key in ["vip", "premium", "active_30d", "at_risk", "inactive"]:
            assert key in data["buckets"], f"missing bucket {key}"
            b = data["buckets"][key]
            assert "count" in b and "label" in b and "action" in b


# ----- Forecast -----

class TestForecast:
    def test_forecast_structure(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/forecast", timeout=20)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        # Either has summary+forecast_30d or note (insufficient data)
        if data.get("forecast_30d"):
            assert "summary" in data
            for k in ["expected_revenue_next_30d", "trend", "trend_slope"]:
                assert k in data["summary"]
            assert len(data["forecast_30d"]) == 30
        else:
            assert "note" in data


# ----- Growth -----

class TestGrowth:
    def test_growth_structure(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/growth", timeout=20)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        for k in ["underserved_geo", "high_growth_categories", "new_markets_suggested"]:
            assert k in data
            assert isinstance(data[k], list)


# ----- Future Ideas -----

class TestFutureIdeas:
    def test_future_ideas(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/future-ideas", timeout=15)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "phases" in data
        assert len(data["phases"]) == 3
        phase_names = [p["phase"] for p in data["phases"]]
        assert any("Faza 2" in p for p in phase_names)
        assert any("Faza 3" in p for p in phase_names)
        assert any("Faza 4" in p for p in phase_names)
        for phase in data["phases"]:
            assert "items" in phase
            assert len(phase["items"]) > 0
            for it in phase["items"]:
                assert "priority" in it and it["priority"] in ("P1", "P2", "P3")
                assert "effort_days" in it
                assert "title" in it


# ----- AI: Insights (Claude) -----

class TestAIInsights:
    def test_generate_insights_via_claude(self, admin_session):
        r = admin_session.post(f"{API}/admin/marketing/insights", timeout=60)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "insights" in data
        items = data["insights"]
        assert 4 <= len(items) <= 12, f"got {len(items)} insights"
        for ins in items:
            assert "title" in ins and "body" in ins
            assert "severity" in ins and ins["severity"] in ("info", "warning", "critical")
            assert "category" in ins
            assert len(ins["body"]) <= 250

    def test_recent_insights(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/insights/recent", timeout=15)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "items" in data
        # Should have at least one (we just generated)
        if data["count"] >= 1:
            first = data["items"][0]
            assert "insights" in first or "id" in first
            # Ensure mongo _id stripped
            assert "_id" not in first


# ----- AI: Recommendations (Claude) -----

class TestAIRecommendations:
    def test_generate_recommendations(self, admin_session):
        r = admin_session.post(f"{API}/admin/marketing/recommendations", timeout=60)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "marketing" in data and "business" in data
        assert isinstance(data["marketing"], list)
        assert isinstance(data["business"], list)
        if data["marketing"]:
            m = data["marketing"][0]
            for k in ["action", "audience", "budget_ron", "expected_impact", "priority"]:
                assert k in m
        if data["business"]:
            b = data["business"][0]
            for k in ["action", "why", "priority"]:
                assert k in b


# ----- AI: Copilot (Claude) -----

class TestCopilot:
    def test_copilot_first_message(self, admin_session):
        r = admin_session.post(f"{API}/admin/marketing/copilot",
                               json={"message": "Ce categorii să promovez?"},
                               timeout=60)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert "session_id" in data and data["session_id"]
        assert "reply" in data and isinstance(data["reply"], str) and len(data["reply"]) > 5
        # Stash for context test
        TestCopilot._sid = data["session_id"]

    def test_copilot_followup_same_session(self, admin_session):
        sid = getattr(TestCopilot, "_sid", None)
        if not sid:
            pytest.skip("No session id from prior test")
        r = admin_session.post(f"{API}/admin/marketing/copilot",
                               json={"session_id": sid, "message": "Și pe ce județe?"},
                               timeout=60)
        assert r.status_code == 200, r.text[:500]
        data = r.json()
        assert data["session_id"] == sid

    def test_copilot_history(self, admin_session):
        sid = getattr(TestCopilot, "_sid", None)
        if not sid:
            pytest.skip("No session id")
        r = admin_session.get(f"{API}/admin/marketing/copilot/history",
                              params={"session_id": sid}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "messages" in data
        assert len(data["messages"]) >= 4  # 2 user + 2 assistant
