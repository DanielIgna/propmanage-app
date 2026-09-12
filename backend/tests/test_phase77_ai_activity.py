"""Phase 77 — AI Activity Stream unified timeline endpoint.

Verifies:
  - GET /api/admin/ai-activity returns {items, count, hours, summary:{by_kind,by_severity}}
  - Sorted descending by ts
  - Defaults hours=72, limit=60
  - Query param bounds (hours 1..720, limit 5..200)
  - Admin-only (client → 403)
  - Resilience: bad query still returns 422 (validation), endpoint shouldn't 500
  - Regression: autonomy/score, auto-match/preview, auto-match/schedule, login
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(session, creds):
    r = session.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    return r


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = _login(s, ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = _login(s, CLIENT)
    if r.status_code != 200:
        pytest.skip(f"client login failed: {r.status_code} {r.text}")
    return s


# ----- AuthZ -----
class TestAuthz:
    def test_anonymous_401(self):
        r = requests.get(f"{BASE_URL}/api/admin/ai-activity", timeout=10)
        assert r.status_code in (401, 403)

    def test_client_403(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/ai-activity", timeout=10)
        assert r.status_code == 403


# ----- Shape & defaults -----
class TestShape:
    def test_default_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity", timeout=20)
        assert r.status_code == 200
        body = r.json()
        for key in ("items", "count", "hours", "summary"):
            assert key in body, f"missing key {key}"
        assert body["hours"] == 72
        assert isinstance(body["items"], list)
        assert body["count"] == len(body["items"])
        assert "by_kind" in body["summary"]
        assert "by_severity" in body["summary"]
        for sev in ("info", "success", "warning", "critical"):
            assert sev in body["summary"]["by_severity"]

    def test_items_have_required_fields(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) > 0, "Expected events in 30-day window given seeded collections"
        required = {"kind", "ts", "title", "summary", "severity", "icon", "meta", "source"}
        for ev in items:
            missing = required - set(ev.keys())
            assert not missing, f"event missing fields: {missing}"
            assert ev["severity"] in ("info", "success", "warning", "critical")

    def test_sorted_desc_by_ts(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        items = r.json()["items"]
        ts_list = [e["ts"] for e in items if e.get("ts")]
        assert ts_list == sorted(ts_list, reverse=True), "items must be sorted desc by ts"

    def test_limit_respected(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=5", timeout=20)
        body = r.json()
        assert len(body["items"]) <= 5
        assert body["count"] == len(body["items"])

    def test_hours_window_filters(self, admin_session):
        r1 = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=1&limit=200", timeout=20)
        r720 = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        assert r1.status_code == 200 and r720.status_code == 200
        # 1h window should have <= 720h window
        assert r1.json()["count"] <= r720.json()["count"]
        assert r1.json()["hours"] == 1

    def test_summary_counts_match_items(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        body = r.json()
        items = body["items"]
        # by_kind sum must equal count
        by_kind_sum = sum(body["summary"]["by_kind"].values())
        assert by_kind_sum == body["count"]
        # by_severity sum must equal count (every event has a severity in the 4-set)
        by_sev_sum = sum(body["summary"]["by_severity"].values())
        assert by_sev_sum == body["count"]
        # spot-check by_kind matches actual
        observed = {}
        for e in items:
            observed[e["kind"]] = observed.get(e["kind"], 0) + 1
        assert observed == body["summary"]["by_kind"]


# ----- Query validation -----
class TestValidation:
    def test_hours_too_low(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=0", timeout=10)
        assert r.status_code == 422

    def test_hours_too_high(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=721", timeout=10)
        assert r.status_code == 422

    def test_limit_too_low(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?limit=4", timeout=10)
        assert r.status_code == 422

    def test_limit_too_high(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?limit=201", timeout=10)
        assert r.status_code == 422


# ----- Severity mapping -----
class TestSeverityMapping:
    def test_known_kinds_present(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        kinds = set(r.json()["summary"]["by_kind"].keys())
        # We expect at least these to show up given seeded data
        expected_any = {
            "autonomy.snapshot", "auto_match.run", "ai.finding.detected",
            "ai.finding.resolved", "ai.scan.completed", "smoke_test.run",
            "settings.snapshot", "security.scan",
        }
        # At least 4 of them should appear
        assert len(kinds & expected_any) >= 4, f"only saw kinds={kinds}"

    def test_smoke_test_severity_mapping(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        for ev in r.json()["items"]:
            if ev["kind"] == "smoke_test.run":
                ok = ev.get("meta", {}).get("ok")
                if ok is True:
                    assert ev["severity"] == "success"
                elif ok is False:
                    assert ev["severity"] == "critical"

    def test_autonomy_snapshot_severity(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        for ev in r.json()["items"]:
            if ev["kind"] == "autonomy.snapshot":
                g = ev.get("meta", {}).get("general", 0)
                expected = "success" if g >= 75 else "info"
                assert ev["severity"] == expected

    def test_finding_resolved_is_success(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ai-activity?hours=720&limit=200", timeout=20)
        for ev in r.json()["items"]:
            if ev["kind"] == "ai.finding.resolved":
                assert ev["severity"] == "success"


# ----- Regression -----
class TestRegression:
    def test_autonomy_score(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/autonomy/score", timeout=15)
        assert r.status_code == 200

    def test_auto_match_preview(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/auto-match/preview", json={}, timeout=15)
        assert r.status_code == 200

    def test_auto_match_schedule(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/auto-match/schedule", timeout=15)
        assert r.status_code == 200

    def test_login_still_works(self):
        s = requests.Session()
        r = _login(s, ADMIN)
        assert r.status_code == 200
