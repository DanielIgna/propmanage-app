"""EO-026 Go-Live/Public Beta Gate — Passport Analytics + Beta Cockpit + VoC + Purge + OG/QR regression."""
import os
import uuid
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
SLUG = "gbegxfyz9m"
PROP_ID = "6a11d70e600be19667009c93"
CLIENT = ("client@propmanage.io", "Client123!")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")
IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
BOT_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_session():
    return _login(*CLIENT)


@pytest.fixture(scope="module")
def admin_session():
    return _login(*ADMIN)


# ==================== PASSPORT TRACKING ====================
class TestPassportTracking:
    def test_track_view_qr(self):
        vid = uuid.uuid4().hex
        r = requests.post(
            f"{BASE}/api/public/passport/{SLUG}/track",
            json={"visitor_id": vid, "event": "view", "src": "qr"},
            headers={"User-Agent": IPHONE_UA}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_track_leave_duration(self):
        vid = uuid.uuid4().hex
        r = requests.post(
            f"{BASE}/api/public/passport/{SLUG}/track",
            json={"visitor_id": vid, "event": "leave", "duration_s": 42},
            timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_track_share_wa(self):
        vid = uuid.uuid4().hex
        r = requests.post(
            f"{BASE}/api/public/passport/{SLUG}/track",
            json={"visitor_id": vid, "event": "share", "src": "wa"}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_track_cta_click(self):
        vid = uuid.uuid4().hex
        r = requests.post(
            f"{BASE}/api/public/passport/{SLUG}/track",
            json={"visitor_id": vid, "event": "cta_click"}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_track_invalid_event_400(self):
        r = requests.post(
            f"{BASE}/api/public/passport/{SLUG}/track",
            json={"visitor_id": "abcdefgh", "event": "hack"}, timeout=10)
        assert r.status_code == 400

    def test_track_nonexistent_slug_404(self):
        r = requests.post(
            f"{BASE}/api/public/passport/zzzz_no_such_slug/track",
            json={"visitor_id": "abcdefgh", "event": "view"}, timeout=10)
        assert r.status_code == 404

    def test_track_bot_ua_skipped(self):
        r = requests.post(
            f"{BASE}/api/public/passport/{SLUG}/track",
            json={"visitor_id": "botvisitor1", "event": "view"},
            headers={"User-Agent": BOT_UA}, timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert j.get("ok") is True
        assert j.get("skipped") == "bot"


# ==================== OWNER ANALYTICS ====================
class TestOwnerAnalytics:
    def test_owner_analytics_ok(self, client_session):
        r = client_session.get(f"{BASE}/api/properties/{PROP_ID}/passport/analytics?days=30", timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        for k in ["views", "unique_visitors", "qr_scans", "shares", "cta_clicks", "registers",
                  "properties_created", "avg_read_s", "bounce_rate_pct",
                  "sources", "devices", "countries", "browsers", "daily"]:
            assert k in j, f"missing {k}"
        assert j["views"] >= 1
        assert j["qr_scans"] >= 1
        assert j["shares"] >= 1
        # device iphone / safari present
        devs = {d["key"] for d in j["devices"]}
        brs = {b["key"] for b in j["browsers"]}
        assert "mobile" in devs, f"expected mobile device, got {devs}"
        assert "Safari" in brs, f"expected Safari browser, got {brs}"

    def test_owner_analytics_no_auth_401(self):
        r = requests.get(f"{BASE}/api/properties/{PROP_ID}/passport/analytics", timeout=10)
        assert r.status_code in (401, 403)

    def test_owner_analytics_wrong_user_blocked(self):
        # register a fresh non-owner user, expect 403/404
        email = f"test.stranger.{uuid.uuid4().hex[:8]}@gmail.com"
        s = requests.Session()
        rr = s.post(f"{BASE}/api/auth/register",
                    json={"email": email, "password": "TestPass123!", "name": "Stranger",
                          "role": "client", "terms_accepted": True, "privacy_policy_accepted": True},
                    timeout=15)
        assert rr.status_code in (200, 201), rr.text
        r = s.get(f"{BASE}/api/properties/{PROP_ID}/passport/analytics", timeout=10)
        assert r.status_code in (403, 404), r.status_code


# ==================== CONVERSION ====================
class TestConversion:
    def test_register_and_attribute(self):
        email = f"test.eo026.{uuid.uuid4().hex[:8]}@gmail.com"
        s = requests.Session()
        r = s.post(f"{BASE}/api/auth/register",
                   json={"email": email, "password": "TestPass123!", "name": "EO026 Test",
                         "role": "client", "terms_accepted": True, "privacy_policy_accepted": True},
                   timeout=15)
        assert r.status_code in (200, 201), r.text
        vid = "conv" + uuid.uuid4().hex
        r2 = s.post(f"{BASE}/api/track/passport-conversion",
                    json={"slug": SLUG, "visitor_id": vid}, timeout=10)
        assert r2.status_code == 200, r2.text
        j2 = r2.json()
        assert j2.get("ok") is True
        assert j2.get("attributed") is True
        # second call - dedup
        r3 = s.post(f"{BASE}/api/track/passport-conversion",
                    json={"slug": SLUG, "visitor_id": vid}, timeout=10)
        assert r3.status_code == 200
        assert r3.json().get("already") is True


# ==================== BETA COCKPIT ====================
class TestBetaCockpit:
    def test_overview_admin(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/beta/overview?days=30", timeout=20)
        assert r.status_code == 200, r.text
        j = r.json()
        for k in ["visitors", "registrations", "owner_funnel", "specialist_funnel",
                  "passports", "ttfv_minutes_median", "support_requests", "voc", "gates"]:
            assert k in j, f"missing {k}"
        assert len(j["owner_funnel"]) == 6
        assert len(j["specialist_funnel"]) == 5
        assert len(j["gates"]) == 4
        # Real users only - no @propmanage.io in registrations bucket
        # (owner_funnel counts should be based on real users)
        for g in j["gates"]:
            assert "target_pct" in g and "actual_pct" in g and "passed" in g

    def test_overview_client_forbidden(self, client_session):
        r = client_session.get(f"{BASE}/api/admin/beta/overview", timeout=10)
        assert r.status_code == 403


# ==================== VOICE OF CUSTOMER ====================
class TestVoC:
    def test_submit_feedback_ok(self, client_session):
        r = client_session.post(f"{BASE}/api/feedback/beta",
                                json={"easy": "yes", "trust": "high", "recommend": True,
                                      "why": "Great tool for property owners"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_submit_feedback_empty_400(self, client_session):
        r = client_session.post(f"{BASE}/api/feedback/beta", json={}, timeout=10)
        assert r.status_code == 400

    def test_admin_list_feedback(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/beta/feedback", timeout=10)
        assert r.status_code == 200
        j = r.json()
        assert "items" in j
        assert isinstance(j["items"], list)
        # Must include client@propmanage.io feedback from previous test
        emails = {i.get("user_email") for i in j["items"]}
        assert CLIENT[0] in emails

    def test_client_forbidden_on_admin_feedback(self, client_session):
        r = client_session.get(f"{BASE}/api/admin/beta/feedback", timeout=10)
        assert r.status_code == 403

    def test_feedback_dedup_same_day(self, client_session):
        # second submit same day → update, not duplicate
        r1 = client_session.post(f"{BASE}/api/feedback/beta",
                                 json={"easy": "updated_value", "recommend": True}, timeout=10)
        assert r1.status_code == 200


# ==================== PURGE DEMO (DRY-RUN ONLY) ====================
class TestPurgeDemo:
    def test_purge_dry_run_ok(self, admin_session):
        r = admin_session.post(f"{BASE}/api/admin/beta/purge-demo",
                               json={"master_code": "0108", "dry_run": True}, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["dry_run"] is True
        c = j["counts"]
        for k in ["users", "properties", "requests", "documents", "twins", "portfolio"]:
            assert k in c

    def test_purge_wrong_code_400(self, admin_session):
        r = admin_session.post(f"{BASE}/api/admin/beta/purge-demo",
                               json={"master_code": "wrong", "dry_run": True}, timeout=10)
        assert r.status_code == 400

    def test_purge_client_forbidden(self, client_session):
        r = client_session.post(f"{BASE}/api/admin/beta/purge-demo",
                                json={"master_code": "0108", "dry_run": True}, timeout=10)
        assert r.status_code == 403


# ==================== OG SHARE + QR (REGRESSION) ====================
class TestOgQrRegression:
    def test_og_share_browser_redirect(self):
        r = requests.get(f"{BASE}/api/p/{SLUG}?src=wa",
                         headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120"},
                         allow_redirects=False, timeout=10)
        assert r.status_code in (302, 307)
        loc = r.headers.get("location", "")
        assert f"/p/{SLUG}" in loc
        assert "src=wa" in loc

    def test_og_share_bot_html(self):
        r = requests.get(f"{BASE}/api/p/{SLUG}?src=wa",
                         headers={"User-Agent": BOT_UA}, allow_redirects=False, timeout=10)
        assert r.status_code == 200
        html = r.text
        assert "og:" in html.lower()

    def test_qr_png(self):
        r = requests.get(f"{BASE}/api/public/passport/{SLUG}/qr.png", timeout=10)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert len(r.content) > 100
