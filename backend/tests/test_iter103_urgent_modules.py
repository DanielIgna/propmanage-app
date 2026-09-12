"""Iter103 backend tests for 4 URGENT modules.

Modules:
1. AI Command Center (/api/admin/command-center)
2. Business Health (/api/admin/business-health)
3. Marketplace Intelligence (/api/admin/marketplace-intel)
4. Financial Cockpit (/api/admin/financial-cockpit)

Auth is cookie-based; admin@propmanage.io / 1!nasov01ADMIN. RBAC also verified
with client role (403 expected).
"""
import os
import pytest
import requests

# Cookies from /api/auth/login are Secure=true → must use HTTPS. Use external URL.
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT_EMAIL, CLIENT_PASSWORD)


# ═══════════════════════════════════════════════════════════════════════════
# 1. AI Command Center
# ═══════════════════════════════════════════════════════════════════════════
class TestCommandCenter:
    def test_feed_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "generated_at" in data
        assert "stats" in data and isinstance(data["stats"], list)
        assert len(data["stats"]) == 4
        keys = [s["key"] for s in data["stats"]]
        assert set(keys) == {"new_requests", "new_users", "completed", "trend"}
        for s in data["stats"]:
            assert "label" in s and "value" in s and "icon" in s

    def test_feed_warnings(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=15)
        data = r.json()
        assert "warnings" in data
        keys = {w["key"] for w in data["warnings"]}
        # Expect these warning keys given seeded data (escrow held ~21150 lei)
        expected_subset = {"waiting_48h", "escrow_held", "escrow_frozen", "disputes", "incomplete_spec"}
        assert expected_subset.issubset(keys), f"Missing warnings: {expected_subset - keys}"
        # Severities allowed
        for w in data["warnings"]:
            assert w["severity"] in ("high", "medium", "low")
        # escrow_held ~21150
        escrow_w = next(w for w in data["warnings"] if w["key"] == "escrow_held")
        assert "21,150" in escrow_w["label"] or "21150" in escrow_w["label"]

    def test_feed_raw_snapshot(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=15)
        raw = r.json()["raw"]
        for k in ("new_requests_24h", "new_users_24h", "completed_24h",
                  "escrow_held_amount", "escrow_held_count", "escrow_frozen_count",
                  "incomplete_specialists", "open_disputes", "pending_payments"):
            assert k in raw, f"raw missing {k}"
        assert raw["escrow_held_amount"] == pytest.approx(21150, abs=100)

    def test_recommendations_generate(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/command-center/recommendations", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)
        assert 1 <= len(data["recommendations"]) <= 5
        assert "ai_generated" in data
        for rec in data["recommendations"]:
            assert "action" in rec and rec["action"]
            assert "why" in rec
            assert rec["severity"] in ("high", "medium", "low")
            assert "module" in rec

    def test_recommendations_latest_cached(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/command-center/recommendations/latest", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "recommendations" in data
        assert data["recommendations"] is not None
        assert len(data["recommendations"]) >= 1

    def test_rbac_client_forbidden(self, client_session):
        for path in ["/api/admin/command-center/feed",
                     "/api/admin/command-center/recommendations/latest"]:
            r = client_session.get(f"{BASE_URL}{path}", timeout=10)
            assert r.status_code == 403, f"{path} expected 403 got {r.status_code}"
        r = client_session.post(f"{BASE_URL}/api/admin/command-center/recommendations", timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 2. Business Health
# ═══════════════════════════════════════════════════════════════════════════
class TestBusinessHealth:
    EXPECTED_KEYS = {"marketing", "marketplace", "escrow", "specialisti",
                     "suport", "conversii", "seo", "financiar"}

    def test_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/business-health", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "departments" in data
        assert len(data["departments"]) == 8
        keys = {d["key"] for d in data["departments"]}
        assert keys == self.EXPECTED_KEYS
        assert "overall" in data and 0 <= data["overall"] <= 100
        assert data["overall_color"] in ("green", "yellow", "red")

    def test_score_color_consistency(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/business-health", timeout=15)
        for d in r.json()["departments"]:
            score = d["score"]
            color = d["color"]
            assert 0 <= score <= 100
            assert isinstance(d["detail"], str) and d["detail"]
            expected = "green" if score >= 80 else "yellow" if score >= 60 else "red"
            assert color == expected, f"{d['key']}: score={score} → expected {expected}, got {color}"

    def test_rbac_client_forbidden(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/business-health", timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 3. Marketplace Intelligence
# ═══════════════════════════════════════════════════════════════════════════
class TestMarketplaceIntel:
    def test_supply_demand_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/marketplace-intel/supply-demand", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["jobs_per_specialist"] == 4
        assert "window" in data
        assert isinstance(data["categories"], list) and len(data["categories"]) >= 1
        for c in data["categories"]:
            for k in ("key", "label", "demand", "supply", "capacity", "status", "pct"):
                assert k in c, f"category missing {k}"
            assert c["capacity"] == c["supply"] * 4
            assert c["status"] in ("deficit", "surplus", "balanced")
            # Status logic
            if c["status"] == "deficit":
                assert c["demand"] > c["capacity"]

    def test_recommend_generate(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/marketplace-intel/recommend", timeout=60)
        assert r.status_code == 200
        data = r.json()
        assert "summary" in data
        assert isinstance(data["recommendations"], list)
        assert "ai_generated" in data
        for rec in data["recommendations"]:
            assert rec["type"] in ("recruit", "promote", "monitor")
            assert rec["priority"] in ("high", "medium", "low")
            assert rec["action"]

    def test_recommend_latest(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/marketplace-intel/recommend/latest", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("recommendations") is not None

    def test_rbac_client_forbidden(self, client_session):
        for path in ["/api/admin/marketplace-intel/supply-demand",
                     "/api/admin/marketplace-intel/recommend/latest"]:
            r = client_session.get(f"{BASE_URL}{path}", timeout=10)
            assert r.status_code == 403
        r = client_session.post(f"{BASE_URL}/api/admin/marketplace-intel/recommend", timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# 4. Financial Cockpit
# ═══════════════════════════════════════════════════════════════════════════
class TestFinancialCockpit:
    def test_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/financial-cockpit", timeout=15)
        assert r.status_code == 200
        data = r.json()

        # revenue
        rev = data["revenue"]
        for k in ("total_paid", "last_30d", "prev_30d", "growth_pct", "pending_amount"):
            assert k in rev

        # escrow
        esc = data["escrow"]
        for st in ("held", "frozen", "released"):
            assert st in esc
            assert "count" in esc[st] and "amount" in esc[st]
        # ~21150 lei held (as noted in review request)
        assert esc["held"]["amount"] == pytest.approx(21150, abs=200)

        # subs
        subs = data["subscriptions"]
        assert "active" in subs
        assert "mrr_eur" in subs and "mrr_ron" in subs and "arr_ron" in subs
        # ARR must be MRR * 12
        assert subs["arr_ron"] == pytest.approx(subs["mrr_ron"] * 12, rel=0.01)

        # VAT rate
        assert data["vat"]["rate_pct"] == 21
        assert "estimated_30d" in data["vat"]

        # commissions
        assert "commissions" in data

        # cash flow: exactly 30 days
        cf = data["cash_flow_30d"]
        assert isinstance(cf, list) and len(cf) == 30
        for entry in cf:
            assert "date" in entry and "amount" in entry

    def test_rbac_client_forbidden(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/financial-cockpit", timeout=10)
        assert r.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# Regression — iter102 endpoints still work
# ═══════════════════════════════════════════════════════════════════════════
class TestIter102Regression:
    def test_roadmap_loads(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/roadmap", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "modules" in data or "counts" in data

    def test_design_intelligence_targets(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/design-intelligence/targets", timeout=15)
        assert r.status_code == 200
