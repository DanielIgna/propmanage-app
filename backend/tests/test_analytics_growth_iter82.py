"""Backend tests for Analytics & Growth (iter82).

Covers:
- Public tracker: POST /api/track, GET /api/track/config
- Campaign redirect: GET /api/go/{code}, GET /api/go/{nonexistent}
- Admin analytics: overview, pages, export.csv (overview/pages/campaigns)
- Admin integrations: GET/PUT /api/admin/analytics/integrations
- Admin campaigns: CRUD + QR PNG + persisted stats after track
"""
import os
import uuid
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
SUPER = {"email": "danieligna1@gmail.com", "password": "0108"}


# ────────────────────────────────── FIXTURES ──────────────────────────────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=SUPER, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def public_session():
    return requests.Session()


# ────────────────────────────────── PUBLIC TRACKER ─────────────────────────────
class TestPublicTracker:
    def test_track_config_returns_clarity_id(self, public_session):
        r = public_session.get(f"{BASE_URL}/api/track/config", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["clarity_id"] == "xj5fspkgjj"
        assert "enabled" in data and data["enabled"] is True
        assert "ga4_id" in data and "meta_pixel_id" in data

    def test_track_ingest_pageview(self, public_session):
        vid = uuid.uuid4().hex
        sid = uuid.uuid4().hex
        body = {
            "visitor_id": vid,
            "session_id": sid,
            "user_role": "",
            "events": [
                {"type": "pageview", "path": "/", "referrer": "", "utm_source": "", "campaign_code": "", "via_qr": False}
            ],
        }
        r = public_session.post(f"{BASE_URL}/api/track", json=body, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["ingested"] == 1

    def test_track_ignores_admin_paths(self, public_session):
        body = {
            "visitor_id": uuid.uuid4().hex,
            "session_id": uuid.uuid4().hex,
            "events": [{"type": "pageview", "path": "/admin/analytics-growth"}],
        }
        r = public_session.post(f"{BASE_URL}/api/track", json=body, timeout=10)
        assert r.status_code == 200
        # Admin paths are filtered → ingested==0
        assert r.json()["ingested"] == 0


# ─────────────────────────────── CAMPAIGN REDIRECT ─────────────────────────────
class TestCampaignRedirect:
    def test_go_nonexistent_redirects_to_root(self, public_session):
        r = public_session.get(f"{BASE_URL}/api/go/DOES_NOT_EXIST_zzz", allow_redirects=False, timeout=10)
        assert r.status_code == 302
        assert r.headers.get("location", "").endswith("/") or r.headers.get("location") == "/"


# ─────────────────────────────── ADMIN INTEGRATIONS ────────────────────────────
class TestIntegrations:
    def test_get_integrations(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/integrations", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["clarity_id"] == "xj5fspkgjj"
        assert "tracker_enabled" in d
        # ga4_id / meta_pixel_id may be absent if never set — frontend handles with `|| ""`

    def test_put_ga4_and_reset(self, admin_session):
        # SET
        r = admin_session.put(
            f"{BASE_URL}/api/admin/analytics/integrations",
            json={"ga4_id": "G-TEST123"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["ga4_id"] == "G-TEST123"

        # VERIFY VIA PUBLIC CONFIG
        pub = requests.get(f"{BASE_URL}/api/track/config", timeout=10)
        assert pub.status_code == 200
        assert pub.json()["ga4_id"] == "G-TEST123"

        # RESET
        r = admin_session.put(
            f"{BASE_URL}/api/admin/analytics/integrations",
            json={"ga4_id": ""},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json()["ga4_id"] == ""

        pub2 = requests.get(f"{BASE_URL}/api/track/config", timeout=10)
        assert pub2.json()["ga4_id"] == ""


# ─────────────────────────────── ADMIN ANALYTICS ───────────────────────────────
class TestAnalyticsOverview:
    @pytest.mark.parametrize("period", ["day", "week", "month"])
    def test_overview_periods(self, admin_session, period):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview?period={period}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "kpi" in d and "sources" in d and "funnel" in d and "series" in d
        for k in ("unique_visitors", "sessions", "accounts_created", "bounce_rate_pct", "avg_session_sec"):
            assert k in d["kpi"]
        assert isinstance(d["series"], list)
        # funnel has 5 steps
        assert len(d["funnel"]) == 5

    def test_pages_report(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/pages?period=week", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)

    def test_export_csv_overview(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/export.csv?report=overview&period=week", timeout=15)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert b"kpi" in r.content or "kpi" in r.text
        assert r.headers.get("content-disposition", "").endswith('.csv"')

    def test_export_csv_campaigns(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/export.csv?report=campaigns", timeout=15)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert b"nume" in r.content or "nume" in r.text

    def test_export_csv_pages(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/export.csv?report=pages&period=week", timeout=15)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")


# ─────────────────────────────── CAMPAIGN CRUD + STATS ─────────────────────────
class TestCampaignFlow:
    """End-to-end: create → shortlink 302 → track → stats reflect → QR → delete."""

    def test_full_flow(self, admin_session):
        # CREATE
        payload = {
            "name": "TEST_QA_iter82",
            "administrator": "QA Bot",
            "association": "AS Test",
            "apartments_count": 10,
            "channel": "whatsapp",
            "recipients_count": 30,
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/growth/campaigns", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        camp = r.json()
        assert camp["name"] == payload["name"]
        assert camp["code"] and len(camp["code"]) <= 6
        assert camp["url"].endswith(f"/api/go/{camp['code']}")
        cid, code = camp["id"], camp["code"]

        try:
            # SHORTLINK REDIRECT
            r = requests.get(f"{BASE_URL}/api/go/{code}", allow_redirects=False, timeout=10)
            assert r.status_code == 302
            loc = r.headers.get("location", "")
            assert f"c={code}" in loc and "utm_source=" in loc and f"utm_campaign={code}" in loc

            # QR redirect
            r2 = requests.get(f"{BASE_URL}/api/go/{code}?qr=1", allow_redirects=False, timeout=10)
            assert r2.status_code == 302
            assert "via_qr=1" in r2.headers.get("location", "")

            # TRACK: simulate visitor coming from the campaign
            vid = uuid.uuid4().hex
            sid = uuid.uuid4().hex
            track_body = {
                "visitor_id": vid,
                "session_id": sid,
                "events": [
                    {"type": "pageview", "path": "/", "utm_source": "whatsapp", "campaign_code": code, "utm_campaign": code},
                    {"type": "heartbeat", "path": "/", "duration_ms": 35000, "campaign_code": code},
                    {"type": "funnel", "funnel_step": "signup_started", "campaign_code": code},
                ],
            }
            tr = requests.post(f"{BASE_URL}/api/track", json=track_body, timeout=10)
            assert tr.status_code == 200 and tr.json()["ingested"] == 3

            # LIST → verify stats
            time.sleep(0.5)
            lst = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns", timeout=10)
            assert lst.status_code == 200
            items = lst.json()["items"]
            found = next((x for x in items if x["id"] == cid), None)
            assert found is not None
            st = found["stats"]
            assert st["recipients"] == 30
            assert st["opened"] >= 2  # from the 2 /api/go hits above
            assert st["unique_visitors"] >= 1
            assert st["over_30s"] >= 1
            assert st["signup_started"] >= 1

            # QR PNG
            qr = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns/{cid}/qr", timeout=10)
            assert qr.status_code == 200
            assert qr.headers.get("content-type") == "image/png"
            assert qr.content[:8] == b"\x89PNG\r\n\x1a\n"

        finally:
            # CLEANUP
            d = admin_session.delete(f"{BASE_URL}/api/admin/growth/campaigns/{cid}", timeout=10)
            assert d.status_code == 200

            # verify gone
            lst2 = admin_session.get(f"{BASE_URL}/api/admin/growth/campaigns", timeout=10)
            assert all(x["id"] != cid for x in lst2.json()["items"])


# ─────────────────────────────── AUTH REGRESSION ───────────────────────────────
class TestAuthGuard:
    def test_admin_endpoints_require_auth(self):
        # Unauthenticated call must be blocked
        r = requests.get(f"{BASE_URL}/api/admin/analytics/overview?period=week", timeout=10)
        assert r.status_code in (401, 403)

        r2 = requests.get(f"{BASE_URL}/api/admin/growth/campaigns", timeout=10)
        assert r2.status_code in (401, 403)
