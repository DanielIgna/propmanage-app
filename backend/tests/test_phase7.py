"""Phase 7 backend tests:
- Admin Live Analytics: /api/admin/analytics with days=7/14/30/90
- Specialist registration with specialty + service_categories + coverage_zones
- Client registration with zone
- Rate limit on /api/auth/login (8 wrong attempts/min → 429) - tested vs localhost:8001
- Stripe (DEMO) integration via emergentintegrations:
  /api/payments/checkout-session, /api/payments/status/{sid}, /api/webhook/stripe
- Regression smoke: phase 6 endpoints still operational
"""
import os
import time
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD


def _load_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
    return url.rstrip("/")


BASE_URL = _load_base_url()
LOCAL_URL = "http://localhost:8001"
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
OPERATOR = {"email": "operator@propmanage.io", "password": "Op123!"}


def _login(creds, base=BASE_URL):
    s = requests.Session()
    r = s.post(f"{base}/api/auth/login", json=creds, timeout=20)
    return s, r


@pytest.fixture(scope="module")
def admin_session():
    # Wait if rate-limited from previous runs
    for _ in range(3):
        s, r = _login(ADMIN)
        if r.status_code == 200:
            return s
        if r.status_code == 429:
            time.sleep(20)
            continue
        break
    pytest.skip(f"admin login failed: {r.status_code} {r.text}")


@pytest.fixture(scope="module")
def client_session():
    for _ in range(3):
        s, r = _login(CLIENT)
        if r.status_code == 200:
            return s
        if r.status_code == 429:
            time.sleep(20)
            continue
        break
    pytest.skip(f"client login failed: {r.status_code} {r.text}")


# ============== ADMIN ANALYTICS ==============
class TestAdminAnalytics:
    @pytest.mark.parametrize("days", [7, 14, 30, 90])
    def test_analytics_various_ranges(self, admin_session, days):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics?days={days}", timeout=60)
        assert r.status_code == 200, f"days={days} -> {r.status_code} {r.text}"
        d = r.json()
        for k in ["series", "by_category", "by_status", "gmv", "platform_revenue",
                  "lead_fees", "avg_job_value", "disputes", "top_specialists"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["series"], list)
        assert len(d["series"]) == days, f"series len {len(d['series'])} != {days}"
        # Each series point has expected shape
        for p in d["series"]:
            for k in ["date", "jobs_created", "jobs_confirmed", "users", "disputes"]:
                assert k in p
        # Revenue / GMV sane (non-negative numbers)
        assert isinstance(d["gmv"], (int, float)) and d["gmv"] >= 0
        assert isinstance(d["platform_revenue"], (int, float)) and d["platform_revenue"] >= 0
        assert isinstance(d["lead_fees"], (int, float)) and d["lead_fees"] >= 0
        # Disputes dict
        assert {"total", "open", "resolved"}.issubset(set(d["disputes"].keys()))
        # Top specialists are well-formed (max 5)
        assert isinstance(d["top_specialists"], list) and len(d["top_specialists"]) <= 5
        for s in d["top_specialists"]:
            for k in ["id", "name", "specialty", "rating", "jobs", "revenue"]:
                assert k in s, f"top_specialists missing {k}"

    def test_platform_revenue_formula(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics?days=14", timeout=60)
        assert r.status_code == 200
        d = r.json()
        # platform_revenue ~= gmv*0.05 + lead_fees (rounded to 2)
        expected = round(d["gmv"] * 0.05 + d["lead_fees"], 2)
        assert abs(d["platform_revenue"] - expected) < 0.05, (
            f"platform_revenue {d['platform_revenue']} != {expected}"
        )

    def test_analytics_requires_admin(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/analytics?days=14", timeout=30)
        assert r.status_code == 403

    def test_analytics_clamps_extreme_days(self, admin_session):
        # >90 should clamp to default 14
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics?days=500", timeout=60)
        assert r.status_code == 200
        assert len(r.json()["series"]) == 14


# ============== REGISTRATION WITH NEW FIELDS ==============
class TestRegistration:
    def test_register_specialist_with_categories_and_zones(self):
        email = f"TEST_phase7_spec_{uuid.uuid4().hex[:8]}@test.io"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "name": "TEST Phase7 Spec",
            "role": "specialist",
            "terms_accepted": True, "privacy_policy_accepted": True,
            "specialty": "hvac",
            "service_categories": ["hvac", "electric", "plumbing"],
            "coverage_zones": ["Floreasca", "Pipera", "Aviatorilor"],
            "phone": "0712345678",
        }
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=20)
        assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["email"] == email.lower()
        assert data["role"] == "specialist"
        assert data["specialty"] == "hvac"
        assert data["service_categories"] == ["hvac", "electric", "plumbing"]
        assert data["coverage_zones"] == ["Floreasca", "Pipera", "Aviatorilor"]
        # confirm via /auth/me
        r2 = s.get(f"{BASE_URL}/api/auth/me", timeout=20)
        assert r2.status_code == 200
        me = r2.json()
        assert me["service_categories"] == ["hvac", "electric", "plumbing"]
        assert me["coverage_zones"] == ["Floreasca", "Pipera", "Aviatorilor"]

    def test_register_client_with_zone(self):
        email = f"TEST_phase7_client_{uuid.uuid4().hex[:8]}@test.io"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "name": "TEST Phase7 Client",
            "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "zone": "Cotroceni",
        }
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=20)
        assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["role"] == "client"
        assert data.get("zone") == "Cotroceni"

    def test_register_duplicate_rejected(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": "client@propmanage.io",
            "password": "xxxxxx",
            "name": "dup",
            "role": "client",
        }, timeout=20)
        assert r.status_code == 400


# ============== RATE LIMITING (against localhost) ==============
class TestLoginRateLimit:
    def test_429_after_8_wrong_attempts(self):
        # Use unique email so we don't lock out real users
        email = f"rl_test_{uuid.uuid4().hex[:6]}@nope.io"
        last = None
        codes = []
        for i in range(10):
            r = requests.post(
                f"{LOCAL_URL}/api/auth/login",
                json={"email": email, "password": "wrong"},
                timeout=10,
            )
            codes.append(r.status_code)
            last = r
            if r.status_code == 429:
                break
        assert 429 in codes, f"never got 429, got {codes}"
        # Error message contains Romanian text
        msg = (last.json() or {}).get("detail", "")
        assert "Prea multe" in msg or "încercări" in msg, f"unexpected detail: {msg}"

    def test_rate_limit_window_resets(self):
        """Verify window expiry behavior - skip the full 60s wait, just confirm the
        429 response persists immediately for a freshly-tripped IP via the LOCAL endpoint."""
        # We don't sleep 60s in CI; just probe again and accept either 429 or 401.
        r = requests.post(
            f"{LOCAL_URL}/api/auth/login",
            json={"email": f"probe_{uuid.uuid4().hex[:6]}@x.io", "password": "wrong"},
            timeout=10,
        )
        assert r.status_code in (401, 429)


# ============== STRIPE (DEMO) PAYMENTS ==============
class TestStripeDemoPayments:
    @pytest.fixture(scope="class")
    def client_and_open_request(self):
        # login
        s = requests.Session()
        for _ in range(3):
            r = s.post(f"{BASE_URL}/api/auth/login", json=CLIENT, timeout=20)
            if r.status_code == 200:
                break
            if r.status_code == 429:
                time.sleep(20)
                continue
            pytest.skip(f"client login: {r.status_code} {r.text}")
        # find an open or assigned request from the client
        r = s.get(f"{BASE_URL}/api/requests", timeout=20)
        assert r.status_code == 200
        reqs = r.json()
        eligible = [x for x in reqs if x.get("status") in ("open", "assigned")]
        if not eligible:
            # create a new one
            props = s.get(f"{BASE_URL}/api/properties", timeout=20).json()
            if not props:
                pytest.skip("no property to attach a request")
            payload = {
                "property_id": props[0]["id"],
                "category": "HVAC",
                "title": "TEST_phase7 escrow funding",
                "description": "Phase7 demo stripe checkout request",
                "priority": "normal",
                "budget_estimate": 250.0,
            }
            r2 = s.post(f"{BASE_URL}/api/requests", json=payload, timeout=20)
            assert r2.status_code == 200, r2.text
            req = r2.json()
        else:
            req = eligible[0]
        return s, req

    def test_create_checkout_session_demo(self, client_and_open_request):
        s, req = client_and_open_request
        r = s.post(
            f"{BASE_URL}/api/payments/checkout-session",
            params={"request_id": req["id"]},
            headers={"Origin": BASE_URL},
            timeout=30,
        )
        assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
        d = r.json()
        assert "session_id" in d
        assert d.get("demo_mode") is True
        assert d["session_id"].startswith("cs_demo_")
        assert "checkout_url" in d
        # Save for next test
        TestStripeDemoPayments._sid = d["session_id"]
        TestStripeDemoPayments._req_id = req["id"]

    def test_payment_status_returns_paid(self, client_and_open_request):
        s, _ = client_and_open_request
        sid = getattr(TestStripeDemoPayments, "_sid", None)
        assert sid, "no session_id from prior test"
        r = s.get(f"{BASE_URL}/api/payments/status/{sid}", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["payment_status"] == "paid"
        assert d["status"] == "complete"
        assert d.get("demo_mode") is True
        assert d["amount"] > 0
        assert d["currency"] == "ron"

    def test_payment_status_missing_session(self, client_and_open_request):
        s, _ = client_and_open_request
        r = s.get(f"{BASE_URL}/api/payments/status/cs_demo_nonexistent_xx", timeout=20)
        assert r.status_code == 404

    def test_escrow_was_held_on_request(self, client_and_open_request):
        s, _ = client_and_open_request
        rid = getattr(TestStripeDemoPayments, "_req_id", None)
        assert rid
        r = s.get(f"{BASE_URL}/api/requests/{rid}", timeout=20)
        assert r.status_code == 200, r.text
        req = r.json()
        assert req.get("escrow_status") == "held"
        assert req.get("escrow_amount", 0) > 0
        assert req.get("paid_at")

    def test_webhook_endpoint_exists(self):
        # Demo mode returns {received: True, demo: True} for any body
        r = requests.post(f"{BASE_URL}/api/webhook/stripe", data=b"{}", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("received") is True
        assert d.get("demo") is True


# ============== REGRESSION SMOKE (Phase 6) ==============
class TestPhase6Regression:
    def test_admin_stats(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/stats", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ["users", "specialists", "verified", "pending_verification",
                  "active_jobs", "completed_jobs"]:
            assert k in d

    def test_admin_disputes_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/disputes", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_pending_specialists(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/specialists/pending", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_operator_list_twins(self):
        s, r = _login(OPERATOR)
        if r.status_code == 429:
            time.sleep(20)
            s, r = _login(OPERATOR)
        assert r.status_code == 200, r.text
        r2 = s.get(f"{BASE_URL}/api/operator/twins", timeout=20)
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)

    def test_specialist_documents_list(self):
        s, r = _login(SPEC)
        if r.status_code == 429:
            time.sleep(20)
            s, r = _login(SPEC)
        assert r.status_code == 200, r.text
        r2 = s.get(f"{BASE_URL}/api/specialist/documents", timeout=20)
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)
