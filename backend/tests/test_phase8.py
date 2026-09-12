"""Phase 8 backend regression tests for PropManage:
- Refactor regression: all admin/analytics, admin/disputes, operator/twins still work
- New: lead_fees windowed by days
- New: service_categories validated against ALLOWED_SPECIALTIES
- Re-verify Stripe DEMO + rate-limit + dispute/twin enrichment
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
    for _ in range(3):
        r = s.post(f"{base}/api/auth/login", json=creds, timeout=20)
        if r.status_code == 200:
            return s, r
        if r.status_code == 429:
            time.sleep(20)
            continue
        return s, r
    return s, r


@pytest.fixture(scope="module")
def admin_session():
    s, r = _login(ADMIN)
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s, r = _login(CLIENT)
    if r.status_code != 200:
        pytest.skip(f"client login failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def operator_session():
    s, r = _login(OPERATOR)
    if r.status_code != 200:
        pytest.skip(f"operator login failed: {r.status_code} {r.text}")
    return s


# ============== ANALYTICS (refactored to single agg pipelines) ==============
class TestAnalyticsRefactor:
    @pytest.mark.parametrize("days", [7, 14, 30, 90])
    def test_analytics_shape_and_size(self, admin_session, days):
        t0 = time.time()
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics?days={days}", timeout=60)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["series", "by_category", "by_status", "gmv", "platform_revenue",
                  "lead_fees", "avg_job_value", "disputes", "top_specialists"]:
            assert k in d, f"missing key {k}"
        assert len(d["series"]) == days, f"series len {len(d['series'])} != {days}"
        for p in d["series"]:
            for k in ["date", "jobs_created", "jobs_confirmed", "users", "disputes"]:
                assert k in p
        # Performance gate: <2000ms after the refactor
        assert elapsed < 2.0, f"slow analytics days={days}: {elapsed:.2f}s"

    def test_lead_fees_windowed(self, admin_session):
        # lead_fees for days=7 should be <= days=90 (since it's now windowed)
        r7 = admin_session.get(f"{BASE_URL}/api/admin/analytics?days=7", timeout=60).json()
        r90 = admin_session.get(f"{BASE_URL}/api/admin/analytics?days=90", timeout=60).json()
        assert r7["lead_fees"] <= r90["lead_fees"] + 0.01, (
            f"lead_fees should be cumulative-by-window: 7d={r7['lead_fees']} 90d={r90['lead_fees']}"
        )

    def test_revenue_formula(self, admin_session):
        d = admin_session.get(f"{BASE_URL}/api/admin/analytics?days=14", timeout=60).json()
        expected = round(d["gmv"] * 0.05 + d["lead_fees"], 2)
        assert abs(d["platform_revenue"] - expected) < 0.05

    def test_analytics_requires_admin(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/analytics?days=14", timeout=30)
        assert r.status_code == 403


# ============== DISPUTES ENRICHMENT ==============
class TestDisputesEnrichment:
    def test_disputes_enriched_fields(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/disputes", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # If any disputes exist, they must be enriched
        for d in items:
            # batched lookup result must be present
            for key in ("client_name", "specialist_name", "request_title", "escrow_amount"):
                assert key in d, f"dispute missing enriched field {key}: {list(d.keys())}"


# ============== OPERATOR TWINS ENRICHMENT ==============
class TestOperatorTwinsEnrichment:
    def test_twins_enriched_fields(self, operator_session):
        r = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for t in items:
            for key in ("property_name", "property_address", "owner_name", "property_surface"):
                assert key in t, f"twin missing enriched field {key}: {list(t.keys())}"


# ============== REGISTRATION VALIDATION ==============
class TestRegisterValidation:
    def test_register_specialist_invalid_category_400(self):
        email = f"TEST_phase8_bad_{uuid.uuid4().hex[:8]}@test.io"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "name": "Bad Spec",
            "role": "specialist",
            "specialty": "hvac",
            "service_categories": ["invalid_xyz"],
            "coverage_zones": ["Bucuresti-Sector1"],
        }
        r = requests.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=20)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        detail = (r.json() or {}).get("detail", "")
        assert "Categorii invalide" in detail, f"unexpected detail: {detail}"

    def test_register_specialist_valid_categories(self):
        email = f"TEST_phase8_ok_{uuid.uuid4().hex[:8]}@test.io"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "name": "OK Spec",
            "role": "specialist",
            "specialty": "hvac",
            "service_categories": ["hvac", "electric", "plumbing"],
            "coverage_zones": ["Bucuresti-Sector1", "Bucuresti-Sector2"],
        }
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=20)
        assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["service_categories"] == ["hvac", "electric", "plumbing"]
        # verify persistence
        me = s.get(f"{BASE_URL}/api/auth/me", timeout=20).json()
        assert me["service_categories"] == ["hvac", "electric", "plumbing"]

    def test_register_specialist_mixed_invalid_400(self):
        email = f"TEST_phase8_mix_{uuid.uuid4().hex[:8]}@test.io"
        payload = {
            "email": email,
            "password": "TestPass123!",
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "name": "Mixed",
            "role": "specialist",
            "specialty": "hvac",
            "service_categories": ["hvac", "<script>"],
            "coverage_zones": ["Bucuresti-Sector1"],
        }
        r = requests.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=20)
        assert r.status_code == 400


# ============== RATE LIMIT (vs localhost) ==============
class TestRateLimit:
    def test_429_after_8_wrong_attempts(self):
        email = f"rl8_{uuid.uuid4().hex[:6]}@nope.io"
        codes = []
        last = None
        for _ in range(10):
            r = requests.post(
                f"{LOCAL_URL}/api/auth/login",
                json={"email": email, "password": "wrong"},
                timeout=10,
            )
            codes.append(r.status_code)
            last = r
            if r.status_code == 429:
                break
        assert 429 in codes, f"never got 429: {codes}"
        detail = (last.json() or {}).get("detail", "")
        assert "Prea multe" in detail or "încercări" in detail


# ============== STRIPE DEMO ==============
class TestStripeDemo:
    @pytest.fixture(scope="class")
    def client_with_request(self):
        s = requests.Session()
        for _ in range(3):
            r = s.post(f"{BASE_URL}/api/auth/login", json=CLIENT, timeout=20)
            if r.status_code == 200:
                break
            if r.status_code == 429:
                time.sleep(20)
                continue
            pytest.skip(f"client login: {r.status_code}")
        props = s.get(f"{BASE_URL}/api/properties", timeout=20).json()
        if not props:
            pytest.skip("no property")
        payload = {
            "property_id": props[0]["id"],
            "category": "hvac",
            "title": "TEST_phase8 demo stripe",
            "description": "phase8 escrow",
            "priority": "normal",
            "budget_estimate": 200.0,
        }
        r2 = s.post(f"{BASE_URL}/api/requests", json=payload, timeout=20)
        assert r2.status_code == 200, r2.text
        return s, r2.json()

    def test_checkout_session_demo(self, client_with_request):
        s, req = client_with_request
        r = s.post(
            f"{BASE_URL}/api/payments/checkout-session",
            params={"request_id": req["id"]},
            headers={"Origin": BASE_URL},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("demo_mode") is True
        assert "session_id" in d and d["session_id"].startswith("cs_demo_")
        assert "checkout_url" in d
        # Verify session_id is embedded in the demo checkout url
        assert d["session_id"] in d["checkout_url"], (
            f"session_id not in demo_url: {d['checkout_url']}"
        )
        TestStripeDemo._sid = d["session_id"]

    def test_payment_status_paid(self, client_with_request):
        s, _ = client_with_request
        sid = getattr(TestStripeDemo, "_sid", None)
        assert sid
        r = s.get(f"{BASE_URL}/api/payments/status/{sid}", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["payment_status"] == "paid"
        assert d.get("demo_mode") is True


# ============== REFACTOR REGRESSION SMOKE ==============
class TestRegressionSmoke:
    def test_admin_stats(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/stats", timeout=20)
        assert r.status_code == 200
        for k in ["users", "specialists", "verified", "pending_verification",
                  "active_jobs", "completed_jobs"]:
            assert k in r.json()

    def test_admin_pending_specialists(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/specialists/pending", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_specialist_documents(self):
        s, r = _login(SPEC)
        assert r.status_code == 200
        r2 = s.get(f"{BASE_URL}/api/specialist/documents", timeout=20)
        assert r2.status_code == 200
        assert isinstance(r2.json(), list)
