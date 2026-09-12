"""Iteration 72 - Strategic Partners Dashboard + AI Cross-Reference Engine.

Tests:
- GET /api/admin/strategic-partners/dashboard          (super admin only)
- GET /api/admin/strategic-partners/unmatched-leads    (super admin only)
- GET /api/admin/strategic-partners/opportunities      (super admin only)
- POST /api/admin/strategic-partners/cross-ref/{lead_id}  (super admin, real Claude)
- RBAC: 403 for non-admin (client) on all endpoints.
- Regression: legacy admin endpoints still respond 200.
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


def _login_session(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    # auth via httpOnly cookies in session
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login_session(ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_sess():
    return _login_session(CLIENT_EMAIL, CLIENT_PASSWORD)


# ----- Dashboard -----
class TestDashboard:
    def test_dashboard_admin_ok(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/strategic-partners/dashboard", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        # structure
        for k in ("city", "marketplace", "totals", "coverage", "cross_ref_unmatched", "generated_at"):
            assert k in body, f"missing key {k}: {body.keys()}"
        for sub in ("total", "active", "onboarding", "leads", "converted", "revenue", "conversion_rate"):
            assert sub in body["city"], f"city.{sub} missing"
            assert sub in body["marketplace"], f"marketplace.{sub} missing"
        assert isinstance(body["coverage"], list)
        assert isinstance(body["totals"]["partners"], int)
        # totals consistency
        assert body["totals"]["partners"] == body["city"]["total"] + body["marketplace"]["total"]
        assert body["totals"]["leads"] == body["city"]["leads"] + body["marketplace"]["leads"]

    def test_dashboard_client_forbidden(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/admin/strategic-partners/dashboard", timeout=30)
        assert r.status_code == 403, r.text

    def test_dashboard_no_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/strategic-partners/dashboard", timeout=30)
        assert r.status_code in (401, 403), r.text


# ----- Unmatched leads -----
class TestUnmatched:
    def test_unmatched_admin_ok(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/strategic-partners/unmatched-leads", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and "count" in body
        assert isinstance(body["items"], list)
        assert body["count"] == len(body["items"])
        if body["items"]:
            sample = body["items"][0]
            for k in ("id", "lead_name", "stage", "city_partner_company", "city"):
                assert k in sample, f"unmatched item missing {k}: {sample}"

    def test_unmatched_client_forbidden(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/admin/strategic-partners/unmatched-leads", timeout=30)
        assert r.status_code == 403


# ----- Opportunities -----
class TestOpportunities:
    def test_opportunities_admin_ok(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/strategic-partners/opportunities", timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and "count" in body
        assert isinstance(body["items"], list)

    def test_opportunities_client_forbidden(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/admin/strategic-partners/opportunities", timeout=30)
        assert r.status_code == 403


# ----- Cross-Reference (real Claude call) -----
class TestCrossRef:
    def test_cross_ref_invalid_id(self, admin_sess):
        r = admin_sess.post(f"{BASE_URL}/api/admin/strategic-partners/cross-ref/not-a-valid-oid", timeout=30)
        assert r.status_code == 400, r.text

    def test_cross_ref_unknown_id(self, admin_sess):
        r = admin_sess.post(f"{BASE_URL}/api/admin/strategic-partners/cross-ref/507f1f77bcf86cd799439011", timeout=30)
        # could be 404 lead inexistent
        assert r.status_code in (404,), r.text

    def test_cross_ref_full_flow(self, admin_sess):
        # 1) Need an unmatched lead
        r = admin_sess.get(f"{BASE_URL}/api/admin/strategic-partners/unmatched-leads", timeout=30)
        assert r.status_code == 200
        items = r.json().get("items") or []
        if not items:
            pytest.skip("No unmatched leads in DB to run real cross-ref test")
        lead_id = items[0]["id"]

        # 2) Call cross-ref (real Claude call up to 30s)
        start = time.time()
        r = admin_sess.post(f"{BASE_URL}/api/admin/strategic-partners/cross-ref/{lead_id}", timeout=90)
        elapsed = time.time() - start
        assert r.status_code == 200, f"cross-ref failed in {elapsed:.1f}s: {r.status_code} {r.text}"
        body = r.json()

        # Schema validation
        for k in ("lead_id", "lead_name", "city_partner_company", "city",
                  "matches", "introduction_email_subject", "introduction_email_body", "generated_at"):
            assert k in body, f"missing key {k}"
        assert body["lead_id"] == lead_id
        assert isinstance(body["matches"], list)
        assert 0 < len(body["matches"]) <= 3, f"expected 1-3 matches, got {len(body['matches'])}"
        for m in body["matches"]:
            for sub in ("marketplace_partner_id", "company", "relevance_score", "reason"):
                assert sub in m, f"match missing {sub}: {m}"
            assert 0 <= m["relevance_score"] <= 100
            assert m["company"]
            assert m["reason"]
        assert body["introduction_email_subject"]
        assert body["introduction_email_body"]
        assert len(body["introduction_email_body"]) <= 800

        # 3) Opportunities should now include this entry
        r2 = admin_sess.get(f"{BASE_URL}/api/admin/strategic-partners/opportunities", timeout=30)
        assert r2.status_code == 200
        opp_ids = [o.get("lead_id") for o in r2.json().get("items", [])]
        assert lead_id in opp_ids, "newly generated cross-ref not present in opportunities feed"

        # 4) The lead should disappear from unmatched
        r3 = admin_sess.get(f"{BASE_URL}/api/admin/strategic-partners/unmatched-leads", timeout=30)
        assert r3.status_code == 200
        unmatched_ids = [it["id"] for it in r3.json().get("items", [])]
        assert lead_id not in unmatched_ids, "lead still listed as unmatched after cross-ref"

    def test_cross_ref_client_forbidden(self, client_sess):
        r = client_sess.post(f"{BASE_URL}/api/admin/strategic-partners/cross-ref/507f1f77bcf86cd799439011", timeout=30)
        assert r.status_code == 403


# ----- Regression: existing admin routes still respond -----
class TestRegression:
    @pytest.mark.parametrize("path", [
        "/api/admin/city-partners",
        "/api/admin/marketplace-partners",
        "/api/admin/it-collaborators",
    ])
    def test_admin_listings_still_ok(self, admin_sess, path):
        r = admin_sess.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
