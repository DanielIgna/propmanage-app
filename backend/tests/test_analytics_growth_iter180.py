"""Iter 180 - Analytics Growth extended presets, YoY, campaign-markers, compare."""
import os
import pytest
import requests
from datetime import datetime, timedelta, timezone

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"

PRESETS = ["day", "week", "month", "60d", "90d", "6m", "12m", "ytd", "custom"]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
               timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ────────── Auth guard ──────────
class TestAuth:
    def test_overview_no_auth_forbidden(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/overview?period=week", timeout=10)
        assert r.status_code in (401, 403), f"got {r.status_code}"

    def test_campaign_markers_no_auth_forbidden(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/campaign-markers?period=month", timeout=10)
        assert r.status_code in (401, 403)

    def test_compare_no_auth_forbidden(self):
        r = requests.get(f"{BASE_URL}/api/admin/growth/campaigns/compare?ids=a,b", timeout=10)
        assert r.status_code in (401, 403)


# ────────── Overview presets & granularity ──────────
class TestOverviewPresets:
    @pytest.mark.parametrize("period", PRESETS)
    def test_overview_preset(self, admin_session, period):
        url = f"{BASE_URL}/api/admin/analytics/overview?period={period}"
        if period == "custom":
            today = datetime.now(timezone.utc).date()
            url += f"&date_from={(today - timedelta(days=6)).isoformat()}&date_to={today.isoformat()}"
        r = admin_session.get(url, timeout=20)
        assert r.status_code == 200, f"{period}: {r.status_code} {r.text[:200]}"
        d = r.json()
        for key in ("kpi", "kpi_prev", "series", "sources", "funnel", "granularity", "period"):
            assert key in d, f"{period} missing key {key}"
        # granularity value valid
        assert d["granularity"] in ("day", "week", "month")

    def test_granularity_day_for_short(self, admin_session):
        for p in ("day", "week", "month", "60d"):
            d = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period={p}", timeout=20).json()
            assert d["granularity"] == "day", f"{p} -> {d['granularity']}"

    def test_granularity_week_for_90d_6m(self, admin_session):
        for p in ("90d", "6m"):
            d = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period={p}", timeout=20).json()
            assert d["granularity"] == "week", f"{p} -> {d['granularity']}"

    def test_granularity_month_for_12m_ytd(self, admin_session):
        # ytd depends on how far into year we are - could be day or month.
        d12 = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period=12m", timeout=20).json()
        assert d12["granularity"] == "month"
        # ytd - just ensure valid granularity
        dyt = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period=ytd", timeout=20).json()
        assert dyt["granularity"] in ("day", "week", "month")


# ────────── YoY ──────────
class TestYoY:
    def test_no_yoy_for_short_periods(self, admin_session):
        for p in ("day", "week", "month"):
            d = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period={p}", timeout=20).json()
            assert d.get("kpi_yoy") is None, f"{p} unexpectedly has kpi_yoy"

    def test_yoy_present_for_long_periods(self, admin_session):
        for p in ("60d", "90d", "6m", "12m", "ytd"):
            d = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period={p}", timeout=20).json()
            yoy = d.get("kpi_yoy")
            assert yoy is not None, f"{p} missing kpi_yoy"
            for k in ("unique_visitors", "sessions", "accounts_created", "specialists_signed",
                      "properties_added", "subscriptions", "bounce_rate_pct", "period"):
                assert k in yoy, f"{p} kpi_yoy missing {k}"
            assert "from" in yoy["period"] and "to" in yoy["period"]

    def test_yoy_shifted_365_days(self, admin_session):
        d = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period=60d", timeout=20).json()
        cur_from = datetime.fromisoformat(d["period"]["from"]).date()
        cur_to = datetime.fromisoformat(d["period"]["to"]).date()
        yoy_from = datetime.fromisoformat(d["kpi_yoy"]["period"]["from"]).date()
        yoy_to = datetime.fromisoformat(d["kpi_yoy"]["period"]["to"]).date()
        assert (cur_from - yoy_from).days == 365
        assert (cur_to - yoy_to).days == 365


# ────────── Campaign markers ──────────
class TestCampaignMarkers:
    def test_markers_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/campaign-markers?period=12m", timeout=20)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert "period" in d and "from" in d["period"] and "to" in d["period"]
        assert isinstance(d.get("markers"), list)
        for m in d["markers"]:
            for k in ("id", "code", "name", "channel", "day"):
                assert k in m, f"marker missing {k}"

    def test_markers_supports_all_presets(self, admin_session):
        for p in ("day", "week", "month", "60d", "90d", "6m", "12m", "ytd"):
            r = admin_session.get(f"{BASE_URL}/api/admin/analytics/campaign-markers?period={p}", timeout=20)
            assert r.status_code == 200, f"{p}: {r.status_code}"


# ────────── Compare campaigns ──────────
class TestCompareCampaigns:
    @pytest.fixture(scope="class")
    def two_campaign_ids(self, admin_session):
        # Get existing campaigns
        r = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns", timeout=20)
        assert r.status_code == 200, r.text[:200]
        camps = r.json() if isinstance(r.json(), list) else r.json().get("campaigns", r.json().get("items", []))
        ids = [c["id"] for c in camps if c.get("id")]
        created_id = None
        if len(ids) < 2:
            # Create a second test campaign
            payload = {"name": "TEST_iter180_compare", "channel": "email", "recipients_count": 0}
            r2 = admin_session.post(f"{BASE_URL}/api/admin/growth/campaigns", json=payload, timeout=20)
            assert r2.status_code in (200, 201), f"create campaign failed: {r2.status_code} {r2.text[:200]}"
            created_id = r2.json().get("id")
            assert created_id
            ids.append(created_id)
        yield ids[:2]
        if created_id:
            admin_session.delete(f"{BASE_URL}/api/admin/growth/campaigns/{created_id}", timeout=15)

    def test_compare_success(self, admin_session, two_campaign_ids):
        ids_param = ",".join(two_campaign_ids)
        r = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns/compare?ids={ids_param}&period=12m", timeout=20)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert "period" in d and "campaigns" in d
        assert len(d["campaigns"]) >= 1
        c = d["campaigns"][0]
        for k in ("id", "code", "name", "channel", "recipients", "stats", "series"):
            assert k in c, f"campaign missing {k}"
        for sk in ("unique_visitors", "over_30s", "signup_started", "accounts_created",
                   "subscriptions", "returned_7d", "conversion_pct"):
            assert sk in c["stats"], f"stats missing {sk}"

    def test_compare_400_when_less_than_2(self, admin_session, two_campaign_ids):
        r = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns/compare?ids={two_campaign_ids[0]}", timeout=15)
        assert r.status_code == 400, f"got {r.status_code}"

    def test_compare_400_when_empty(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns/compare?ids=", timeout=15)
        assert r.status_code == 400

    def test_compare_max_3_ids_silently_truncated(self, admin_session, two_campaign_ids):
        # 5 ids -- should not error, should return at most 3 campaigns
        ids_param = ",".join(two_campaign_ids + ["fake1", "fake2", "fake3"])
        r = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns/compare?ids={ids_param}&period=month", timeout=20)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert len(d["campaigns"]) <= 3


# ────────── Other endpoints with new presets ──────────
class TestOtherEndpointsWithNewPresets:
    @pytest.mark.parametrize("period", ["60d", "90d", "6m", "12m", "ytd"])
    def test_pages(self, admin_session, period):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/pages?period={period}", timeout=20)
        assert r.status_code == 200, f"pages {period}: {r.status_code} {r.text[:200]}"

    @pytest.mark.parametrize("period", ["60d", "90d", "6m", "12m", "ytd"])
    def test_insights(self, admin_session, period):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/insights?period={period}", timeout=25)
        assert r.status_code == 200, f"insights {period}: {r.status_code} {r.text[:200]}"

    @pytest.mark.parametrize("period", ["60d", "90d", "6m", "12m", "ytd"])
    def test_export_csv(self, admin_session, period):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/export.csv?period={period}", timeout=25)
        assert r.status_code == 200, f"csv {period}: {r.status_code}"

    @pytest.mark.parametrize("period", ["60d", "90d", "6m", "12m", "ytd"])
    def test_export_pdf(self, admin_session, period):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/export.pdf?period={period}", timeout=30)
        assert r.status_code == 200, f"pdf {period}: {r.status_code}"
