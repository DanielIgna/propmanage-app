"""Iter91 — Business Design System backend tests for Analytics & Growth.

Covers:
  1. GET /api/admin/analytics/overview?period={day|week|month} → returns new
     `kpi_prev` object alongside `kpi` with the 8 mandatory keys.
  2. GET /api/admin/analytics/insights?period=week → returns
     {bullets, alerts, recommendations}.
  3. Auth: non-admin (client) → 403; anonymous → 401/403.

Auth is cookie-based (login sets httpOnly cookie; response has no top-level token).
"""
import pytest
import requests
from tests.test_config import (
    API,
    ADMIN_EMAIL,
    ADMIN_PASSWORDS,
    CLIENT_EMAIL,
    CLIENT_PASSWORD,
)

REQUIRED_KPI_KEYS = {
    "unique_visitors",
    "sessions",
    "accounts_created",
    "specialists_signed",
    "properties_added",
    "specialist_requests",
    "subscriptions",
    "bounce_rate_pct",
}


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_session():
    """Cookie-based admin session. Tries each candidate password."""
    s = requests.Session()
    last_status = None
    for pwd in ADMIN_PASSWORDS:
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": pwd}, timeout=15)
        last_status = r.status_code
        if r.status_code == 200:
            return s
    pytest.skip(f"Admin login failed with all candidates (last={last_status})")


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Client login failed ({r.status_code})")
    return s


# ── analytics overview: kpi_prev added ───────────────────────────────────────

class TestAnalyticsOverviewKpiPrev:
    @pytest.mark.parametrize("period", ["day", "week", "month"])
    def test_overview_returns_kpi_and_kpi_prev(self, admin_session, period):
        r = admin_session.get(f"{API}/admin/analytics/overview", params={"period": period}, timeout=20)
        assert r.status_code == 200, f"period={period} status={r.status_code} body={r.text[:200]}"
        data = r.json()

        # Base structure
        assert "kpi" in data, f"missing kpi in response keys: {list(data.keys())}"
        assert "kpi_prev" in data, f"missing kpi_prev in response keys: {list(data.keys())}"
        assert "period" in data
        assert "series" in data
        assert "sources" in data
        assert "funnel" in data

        # kpi content
        kpi = data["kpi"]
        assert isinstance(kpi, dict)
        missing = REQUIRED_KPI_KEYS - set(kpi.keys())
        assert not missing, f"kpi missing keys: {missing}"

        # kpi_prev content — same 8 mandatory keys
        kpi_prev = data["kpi_prev"]
        assert isinstance(kpi_prev, dict)
        missing_prev = REQUIRED_KPI_KEYS - set(kpi_prev.keys())
        assert not missing_prev, f"kpi_prev missing keys: {missing_prev}"

        # Types are numeric
        for k in REQUIRED_KPI_KEYS:
            assert isinstance(kpi[k], (int, float)), f"kpi[{k}] not numeric: {type(kpi[k])}"
            assert isinstance(kpi_prev[k], (int, float)), f"kpi_prev[{k}] not numeric: {type(kpi_prev[k])}"

    def test_overview_period_range_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/overview", params={"period": "week"}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "from" in d["period"] and "to" in d["period"]
        # week = 7 days
        assert len(d["series"]) == 7, f"expected 7-day series, got {len(d['series'])}"

    def test_overview_requires_auth(self):
        r = requests.get(f"{API}/admin/analytics/overview?period=week", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_overview_forbidden_for_client(self, client_session):
        r = client_session.get(f"{API}/admin/analytics/overview?period=week", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 for client, got {r.status_code}"


# ── analytics insights: NEW endpoint ─────────────────────────────────────────

class TestAnalyticsInsights:
    def test_insights_shape(self, admin_session):
        r = admin_session.get(f"{API}/admin/analytics/insights?period=week", timeout=20)
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:200]}"
        d = r.json()
        assert set(d.keys()) >= {"bullets", "alerts", "recommendations"}, f"keys={list(d.keys())}"
        assert isinstance(d["bullets"], list)
        assert isinstance(d["alerts"], list)
        assert isinstance(d["recommendations"], list)
        # Each element must be a string (rule-based sentences)
        for it in d["bullets"] + d["alerts"] + d["recommendations"]:
            assert isinstance(it, str)

    @pytest.mark.parametrize("period", ["day", "week", "month"])
    def test_insights_all_periods(self, admin_session, period):
        r = admin_session.get(f"{API}/admin/analytics/insights", params={"period": period}, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d.get("bullets"), list)
        assert isinstance(d.get("alerts"), list)
        assert isinstance(d.get("recommendations"), list)

    def test_insights_requires_admin_auth(self):
        r = requests.get(f"{API}/admin/analytics/insights?period=week", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 anon, got {r.status_code}"

    def test_insights_forbidden_for_client(self, client_session):
        r = client_session.get(f"{API}/admin/analytics/insights?period=week", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 for client, got {r.status_code}"
