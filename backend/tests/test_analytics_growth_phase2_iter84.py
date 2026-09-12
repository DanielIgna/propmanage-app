"""Backend tests for Analytics & Growth PHASE 2 (iter84).

Covers:
- Heatmap: pages + points for /login path
- Bounce: 4 KPI cards summary, series, by_source, entry_pages, 5 duration buckets
- Retention: 8 weekly cohorts + summary
- A/B: full CRUD (create → list → results shape → PATCH stopped → invalid goal 400 → DELETE)
- A/B tracking end-to-end: POST /api/track with 'ab' event → visitor counted in variant A
- Export PDF: 200, application/pdf, non-empty, starts with %PDF
- Regression: unauth 401/403 on all phase-2 endpoints
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


# ─────────────────────────────── HEATMAP ────────────────────────────────
class TestHeatmap:
    def test_seed_clicks_on_login(self, public_session):
        """Seed heatmap data on /login via public tracker."""
        vid = "TEST_hm_" + uuid.uuid4().hex[:12]
        sid = uuid.uuid4().hex
        events = [
            {"type": "pageview", "path": "/login"},
            {"type": "click", "path": "/login", "x_pct": 12.5, "y_pct": 30.0},
            {"type": "click", "path": "/login", "x_pct": 55.0, "y_pct": 60.0},
            {"type": "click", "path": "/login", "x_pct": 75.5, "y_pct": 45.0},
        ]
        r = public_session.post(f"{BASE_URL}/api/track",
                                json={"visitor_id": vid, "session_id": sid, "events": events}, timeout=10)
        assert r.status_code == 200
        assert r.json()["ingested"] == 4

    def test_heatmap_month(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/heatmap?period=month", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "pages" in d and isinstance(d["pages"], list)
        assert "points" in d and isinstance(d["points"], list)
        assert "total_clicks" in d and isinstance(d["total_clicks"], int)
        # points empty when no path filter
        assert d["points"] == []
        # /login should be present (we just seeded)
        paths = [p["path"] for p in d["pages"]]
        assert "/login" in paths, f"Expected /login in {paths}"

    def test_heatmap_with_path(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/heatmap?period=month&path=/login", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["points"], list)
        assert len(d["points"]) >= 3, f"Expected 3+ points, got {len(d['points'])}"
        for p in d["points"]:
            assert "x" in p and "y" in p
            assert 0 <= p["x"] <= 100
            assert 0 <= p["y"] <= 100


# ─────────────────────────────── BOUNCE ─────────────────────────────────
class TestBounce:
    def test_bounce_week_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/bounce?period=week", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # summary — 4 KPIs
        s = d["summary"]
        for k in ("sessions", "bounces", "bounce_rate_pct", "quick_bounce_pct"):
            assert k in s, f"Missing summary.{k}"
        # series is daily
        assert isinstance(d["series"], list)
        if d["series"]:
            for row in d["series"]:
                for k in ("day", "sessions", "bounces", "bounce_pct"):
                    assert k in row
        # by_source list
        assert isinstance(d["by_source"], list)
        # entry_pages list
        assert isinstance(d["entry_pages"], list)
        # duration_buckets exactly 5
        assert isinstance(d["duration_buckets"], list)
        assert len(d["duration_buckets"]) == 5
        expected_buckets = ["<10s", "10-30s", "30-60s", "1-3min", ">3min"]
        actual_buckets = [b["bucket"] for b in d["duration_buckets"]]
        assert actual_buckets == expected_buckets


# ─────────────────────────────── RETENTION ──────────────────────────────
class TestRetention:
    def test_retention_8_cohorts(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/retention?weeks=8", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "cohorts" in d and isinstance(d["cohorts"], list)
        assert len(d["cohorts"]) == 8
        for c in d["cohorts"]:
            assert "cohort_week" in c
            assert "size" in c
            assert "retention" in c and isinstance(c["retention"], list)
            for row in c["retention"]:
                assert "week" in row and "active" in row and "pct" in row
        # summary
        s = d["summary"]
        for k in ("total_visitors", "returning_visitors", "returning_pct"):
            assert k in s

    def test_retention_bounds_validation(self, admin_session):
        # weeks=1 must fail (ge=2)
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/retention?weeks=1", timeout=10)
        assert r.status_code == 422
        # weeks=20 must fail (le=16)
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/retention?weeks=20", timeout=10)
        assert r.status_code == 422


# ─────────────────────────────── A/B TESTING ────────────────────────────
class TestAbTesting:
    def test_full_ab_lifecycle(self, admin_session):
        # CREATE
        payload = {
            "name": "TEST_QA iter84 experiment",
            "page_path": "/login",
            "goal": "account_created",
            "hypothesis": "Buton verde crește conversia",
        }
        r = admin_session.post(f"{BASE_URL}/api/admin/analytics/ab", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        exp = r.json()
        assert exp["name"] == payload["name"]
        assert exp["key"], "Missing auto-slug key"
        assert exp["status"] == "active"
        assert "id" in exp
        eid, ekey = exp["id"], exp["key"]

        try:
            # LIST → shape check + results
            lst = admin_session.get(f"{BASE_URL}/api/admin/analytics/ab", timeout=10)
            assert lst.status_code == 200
            items = lst.json()["items"]
            found = next((x for x in items if x["id"] == eid), None)
            assert found is not None
            res = found["results"]
            for k in ("variants", "uplift_pct", "significance", "winner"):
                assert k in res, f"Missing results.{k}"
            for v in ("A", "B"):
                for kk in ("visitors", "conversions", "rate_pct"):
                    assert kk in res["variants"][v]

            # PATCH → status stopped
            r = admin_session.patch(f"{BASE_URL}/api/admin/analytics/ab/{eid}",
                                    json={"status": "stopped"}, timeout=10)
            assert r.status_code == 200
            assert r.json()["status"] == "stopped"

            # AB TRACKING E2E: send 'ab' event via public /api/track, then verify variant A visitor count increased
            baseline_a = res["variants"]["A"]["visitors"]

            vid = "TEST_ab_" + uuid.uuid4().hex[:12]
            sid = uuid.uuid4().hex
            track_body = {
                "visitor_id": vid,
                "session_id": sid,
                "events": [
                    {"type": "pageview", "path": "/"},
                    {"type": "ab", "ab_key": ekey, "ab_variant": "A", "path": "/"},
                ],
            }
            tr = requests.post(f"{BASE_URL}/api/track", json=track_body, timeout=10)
            assert tr.status_code == 200
            assert tr.json()["ingested"] == 2

            time.sleep(0.7)

            lst2 = admin_session.get(f"{BASE_URL}/api/admin/analytics/ab", timeout=10)
            assert lst2.status_code == 200
            found2 = next((x for x in lst2.json()["items"] if x["id"] == eid), None)
            assert found2 is not None
            new_a = found2["results"]["variants"]["A"]["visitors"]
            assert new_a >= baseline_a + 1, f"Expected A visitors to increase from {baseline_a} to >={baseline_a + 1}, got {new_a}"

        finally:
            # DELETE
            d = admin_session.delete(f"{BASE_URL}/api/admin/analytics/ab/{eid}", timeout=10)
            assert d.status_code == 200
            # verify gone
            lst3 = admin_session.get(f"{BASE_URL}/api/admin/analytics/ab", timeout=10)
            assert all(x["id"] != eid for x in lst3.json()["items"])

    def test_invalid_goal_400(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/analytics/ab",
                               json={"name": "TEST_bad_goal", "goal": "INVALID_GOAL"}, timeout=10)
        assert r.status_code == 400
        assert "Goal" in r.text or "goal" in r.text.lower()

    def test_delete_nonexistent_404(self, admin_session):
        r = admin_session.delete(f"{BASE_URL}/api/admin/analytics/ab/does-not-exist-xyz", timeout=10)
        assert r.status_code == 404


# ─────────────────────────────── EXPORT PDF ─────────────────────────────
class TestExportPDF:
    def test_export_pdf_month(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/export.pdf?period=month", timeout=45)
        assert r.status_code == 200
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct, f"Wrong content-type: {ct}"
        # non-empty & starts with %PDF
        assert len(r.content) > 1000, f"PDF too small: {len(r.content)} bytes"
        assert r.content[:4] == b"%PDF", f"Not a valid PDF: starts with {r.content[:8]}"
        # content-disposition present
        assert "attachment" in r.headers.get("content-disposition", "")


# ─────────────────────────────── AUTH GUARD ─────────────────────────────
class TestAuthGuardPhase2:
    def test_heatmap_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/heatmap?period=month", timeout=10)
        assert r.status_code in (401, 403)

    def test_bounce_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/bounce?period=week", timeout=10)
        assert r.status_code in (401, 403)

    def test_retention_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/retention?weeks=8", timeout=10)
        assert r.status_code in (401, 403)

    def test_ab_list_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/ab", timeout=10)
        assert r.status_code in (401, 403)

    def test_export_pdf_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/analytics/export.pdf?period=month", timeout=10)
        assert r.status_code in (401, 403)
