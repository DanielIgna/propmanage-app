"""Iter104 backend tests — Interconnect (Command Center ↔ Business Health)
+ 4 yellow modules (Automation Center, CEO Dashboard, Notification Center,
Financial Cockpit AI Insights) + county support + Business Health history.

Auth cookie-based:
  - super admin:  admin@propmanage.io / 1!nasov01ADMIN
  - scoped admin: testing.admin@propmanage.io / Test!Demo2026Strong (scope=testing)
  - client:       client@propmanage.io / Client123!
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
SCOPED_ADMIN = {"email": "testing.admin@propmanage.io", "password": "Test!Demo2026Strong"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed {creds['email']}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def scoped_s():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=SCOPED_ADMIN, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"scoped admin login unavailable: {r.status_code}")
    return s


# ═══════════════════════════════════════════════════════════════════════════
# 1. Command Center ↔ Business Health interconnect
# ═══════════════════════════════════════════════════════════════════════════
class TestInterconnect:
    def test_feed_has_health_overall_and_red_warnings(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "health_overall" in data
        assert data["health_overall_color"] in ("green", "yellow", "red")
        # cross-check red_departments in raw
        assert "raw" in data and "red_departments" in data["raw"]
        red_keys = [d["key"] for d in data["raw"]["red_departments"]]
        # health_* warnings for every red dept
        health_warnings = [w for w in data["warnings"] if w["key"].startswith("health_")]
        assert len(health_warnings) == len(red_keys)
        for w in health_warnings:
            assert w["severity"] == "high"
            assert w["link"] == "/admin/business-health"
            # key format health_<dept>
            assert w["key"].replace("health_", "") in red_keys

    def test_business_health_colors_match_feed_red(self, admin_s):
        bh = admin_s.get(f"{BASE_URL}/api/admin/business-health", timeout=15).json()
        red_from_bh = sorted([d["key"] for d in bh["departments"] if d["color"] == "red"])
        feed = admin_s.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=15).json()
        red_from_feed = sorted([d["key"] for d in feed["raw"]["red_departments"]])
        assert red_from_bh == red_from_feed


# ═══════════════════════════════════════════════════════════════════════════
# 2. Recommendations toggle
# ═══════════════════════════════════════════════════════════════════════════
class TestRecommendationsToggle:
    def test_recos_have_idx_link_done(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/admin/command-center/recommendations", timeout=90)
        assert r.status_code == 200
        recos = r.json()["recommendations"]
        assert len(recos) >= 1
        for i, rec in enumerate(recos):
            assert rec["idx"] == i
            assert "link" in rec and rec["link"].startswith("/admin")
            assert rec["done"] is False

    def test_toggle_flips_and_persists(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/admin/command-center/recommendations/toggle",
                         json={"idx": 0}, timeout=15)
        assert r.status_code == 200
        assert r.json()["done"] is True
        # persisted?
        latest = admin_s.get(f"{BASE_URL}/api/admin/command-center/recommendations/latest").json()
        assert latest["recommendations"][0]["done"] is True
        # flip back
        r2 = admin_s.post(f"{BASE_URL}/api/admin/command-center/recommendations/toggle",
                          json={"idx": 0}, timeout=15)
        assert r2.json()["done"] is False

    def test_toggle_invalid_idx_400(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/admin/command-center/recommendations/toggle",
                         json={"idx": 9999}, timeout=15)
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
# 3. Business Health history
# ═══════════════════════════════════════════════════════════════════════════
class TestBusinessHealthHistory:
    def test_snapshot_and_history(self, admin_s):
        # trigger snapshot
        admin_s.get(f"{BASE_URL}/api/admin/business-health", timeout=15)
        r = admin_s.get(f"{BASE_URL}/api/admin/business-health/history?days=30", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["history"], list)
        assert len(data["history"]) >= 1
        row = data["history"][0]
        assert "date" in row and "overall" in row and "scores" in row


# ═══════════════════════════════════════════════════════════════════════════
# 4. Marketplace Intel by-county
# ═══════════════════════════════════════════════════════════════════════════
class TestByCounty:
    def test_by_county_structure(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/marketplace-intel/by-county", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["counties"], list)
        assert len(data["counties"]) == 7  # backfilled 7 Romanian counties
        names = {c["county"] for c in data["counties"]}
        expected = {"Cluj", "București", "Ilfov", "Brașov", "Timiș", "Iași", "Constanța"}
        assert expected == names, f"missing counties: {expected - names}"
        for c in data["counties"]:
            for k in ("county", "demand", "supply", "capacity", "status", "pct"):
                assert k in c
            assert c["capacity"] == c["supply"] * 4 * 3  # 90d window


# ═══════════════════════════════════════════════════════════════════════════
# 5. County persistence on requests
# ═══════════════════════════════════════════════════════════════════════════
class TestRequestCounty:
    def test_client_can_create_request_with_county(self, client_s):
        # need a property first — try to fetch client's own props
        rp = client_s.get(f"{BASE_URL}/api/properties", timeout=10)
        if rp.status_code != 200 or not rp.json():
            pytest.skip("no client properties available for request creation")
        prop_id = rp.json()[0].get("id") or rp.json()[0].get("_id")
        if not prop_id:
            pytest.skip("property missing id")
        payload = {
            "property_id": prop_id,
            "title": "TEST_iter104 county",
            "description": "test",
            "category": "electric",
            "county": "Cluj",
        }
        r = client_s.post(f"{BASE_URL}/api/requests", json=payload, timeout=15)
        # accept 200/201
        assert r.status_code in (200, 201), r.text[:200]
        data = r.json()
        assert data.get("county") == "Cluj"


# ═══════════════════════════════════════════════════════════════════════════
# 6. Financial Cockpit AI Insights
# ═══════════════════════════════════════════════════════════════════════════
class TestFinancialInsights:
    def test_generate_insights(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/admin/financial-cockpit/insights", timeout=90)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["insights"], list)
        assert len(data["insights"]) >= 1
        for i in data["insights"]:
            assert "title" in i and "body" in i
            assert i["severity"] in ("positive", "neutral", "warning")
        assert "ai_generated" in data

    def test_latest_insights_cached(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/financial-cockpit/insights/latest", timeout=15)
        assert r.status_code == 200
        assert r.json().get("insights") is not None


# ═══════════════════════════════════════════════════════════════════════════
# 7. Automation Center
# ═══════════════════════════════════════════════════════════════════════════
class TestAutomation:
    KEYS = {"request_reminder", "fast_response_badge", "client_reactivation"}

    def test_rules_seeded(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/automation/rules", timeout=15)
        assert r.status_code == 200
        rules = r.json()["rules"]
        keys = {r["key"] for r in rules}
        assert self.KEYS.issubset(keys)
        rr = next(x for x in rules if x["key"] == "request_reminder")
        assert rr["param"] == 24 or rr["param_default"] == 24
        # defaults enabled=False
        # (may have been toggled by earlier tests → don't assert)

    def test_patch_enabled_and_param_clamping(self, admin_s):
        # enable
        r1 = admin_s.patch(f"{BASE_URL}/api/admin/automation/rules/request_reminder",
                           json={"enabled": True}, timeout=15)
        assert r1.status_code == 200
        assert r1.json()["enabled"] is True
        # clamp param above max
        r2 = admin_s.patch(f"{BASE_URL}/api/admin/automation/rules/request_reminder",
                           json={"param": 999}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["param"] == 168  # clamped to max
        # set reasonable value
        admin_s.patch(f"{BASE_URL}/api/admin/automation/rules/request_reminder",
                      json={"param": 48}, timeout=15)

    def test_patch_unknown_rule_404(self, admin_s):
        r = admin_s.patch(f"{BASE_URL}/api/admin/automation/rules/nope_no_way",
                          json={"enabled": True}, timeout=15)
        assert r.status_code == 404

    def test_run_request_reminder(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/admin/automation/rules/request_reminder/run", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "matched" in data and "actions" in data
        # runs_count incremented
        rules = admin_s.get(f"{BASE_URL}/api/admin/automation/rules").json()["rules"]
        rr = next(x for x in rules if x["key"] == "request_reminder")
        assert rr["runs_count"] >= 1
        assert rr["last_run_at"] is not None

    def test_run_fast_response_badge(self, admin_s):
        r = admin_s.post(f"{BASE_URL}/api/admin/automation/rules/fast_response_badge/run", timeout=30)
        assert r.status_code == 200
        assert "matched" in r.json()

    def test_run_client_reactivation_idempotent(self, admin_s):
        r1 = admin_s.post(f"{BASE_URL}/api/admin/automation/rules/client_reactivation/run", timeout=30).json()
        r2 = admin_s.post(f"{BASE_URL}/api/admin/automation/rules/client_reactivation/run", timeout=30).json()
        assert r1.get("matched", 0) >= 0
        # second run should not queue same emails again (idempotent)
        assert r2.get("matched", 0) == 0 or r2.get("matched", 0) <= r1.get("matched", 0)

    def test_executions_log(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/automation/executions", timeout=15)
        assert r.status_code == 200
        execs = r.json()["executions"]
        assert isinstance(execs, list) and len(execs) >= 1
        for e in execs[:3]:
            assert "rule_key" in e and "matched" in e and "ran_at" in e

    def test_rbac_client(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/admin/automation/rules", timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 8. CEO Dashboard
# ═══════════════════════════════════════════════════════════════════════════
class TestCEO:
    REQUIRED = {"business_score", "revenue", "cash_flow_status", "escrow_held",
                "mrr_ron", "arr_ron", "new_requests_24h",
                "marketplace_trend_pct", "warnings_count", "top_priorities",
                "departments"}

    def test_super_admin_200(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/ceo", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert self.REQUIRED.issubset(set(data.keys()))
        assert 0 <= data["business_score"] <= 100
        assert len(data["departments"]) == 8
        assert isinstance(data["top_priorities"], list)
        assert len(data["top_priorities"]) <= 3

    def test_scoped_admin_403(self, scoped_s):
        r = scoped_s.get(f"{BASE_URL}/api/admin/ceo", timeout=15)
        assert r.status_code == 403

    def test_client_403(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/admin/ceo", timeout=15)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 9. Notification Center
# ═══════════════════════════════════════════════════════════════════════════
class TestNotificationCenter:
    def test_structure(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/notification-center", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "headline" in data
        assert isinstance(data["items"], list)
        assert "unacked_count" in data
        assert len(data["items"]) >= 1
        # source values
        sources = {i["source"] for i in data["items"]}
        assert sources.issubset({"operational", "health", "ai_recommendation"})
        for it in data["items"]:
            assert "key" in it and "label" in it and "severity" in it and "link" in it and "acked" in it

    def test_ack_marks_and_reduces_unacked(self, admin_s):
        pre = admin_s.get(f"{BASE_URL}/api/admin/notification-center").json()
        unacked_before = pre["unacked_count"]
        target = next((i["key"] for i in pre["items"] if not i["acked"]), None)
        if not target:
            pytest.skip("nothing to ack")
        r = admin_s.post(f"{BASE_URL}/api/admin/notification-center/ack",
                         json={"key": target}, timeout=15)
        assert r.status_code == 200
        post = admin_s.get(f"{BASE_URL}/api/admin/notification-center").json()
        # target now acked
        target_item = next(i for i in post["items"] if i["key"] == target)
        assert target_item["acked"] is True
        assert post["unacked_count"] <= unacked_before - 1 + 1  # allow for regen fluctuation
        # strictly: decreased by 1 assuming set was stable
        assert post["unacked_count"] < unacked_before

    def test_rbac_client(self, client_s):
        r = client_s.get(f"{BASE_URL}/api/admin/notification-center", timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 10. Regression — iter103 endpoints still work
# ═══════════════════════════════════════════════════════════════════════════
class TestRegression:
    def test_roadmap(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/roadmap", timeout=15)
        assert r.status_code == 200

    def test_design_intelligence(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/admin/design-intelligence/targets", timeout=15)
        assert r.status_code == 200
