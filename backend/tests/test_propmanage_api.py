"""PropManage Backend API tests - auth, properties, requests, marketplace, admin, operator"""
import os
import pytest
import requests
import uuid
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://phased-document.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
SPEC2 = {"email": "specialist2@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
OPERATOR = {"email": "operator@propmanage.io", "password": "Op123!"}


def make_session(creds=None):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    if creds:
        r = s.post(f"{API}/auth/login", json=creds, timeout=15)
        assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture
def reset_demo_state_before_test():
    """Re-baseline demo accounts immediately before a test that asserts exact balances/tokens.
    Use as a per-test fixture for assertions sensitive to mutation by other tests."""
    try:
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=ADMIN, timeout=10)
        if r.status_code == 200:
            s.post(f"{API}/admin/demo/reset", timeout=15)
    except Exception:  # pragma: no cover
        pass


# ========== AUTH ==========
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/")
        assert r.status_code == 200
        assert "PropManage" in r.json().get("message", "")

    def test_login_client(self, reset_demo_state_before_test):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=CLIENT)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == CLIENT["email"]
        assert data["role"] == "client"
        assert data.get("wallet_balance") == 5000.0
        assert data.get("tokens") == 250
        assert "password_hash" not in data
        # httpOnly cookies
        assert "access_token" in s.cookies
        assert "refresh_token" in s.cookies

    def test_login_specialist(self, reset_demo_state_before_test):
        s = make_session(SPEC)
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "specialist"
        assert d.get("wallet_balance") == 800.0
        assert d.get("rating") == 4.9
        assert d.get("verified") is True
        assert d.get("tier") == "VERIFIED"

    def test_login_admin(self):
        s = make_session(ADMIN)
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_login_operator(self):
        s = make_session(OPERATOR)
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "operator"

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"email": "bad@x.com", "password": "wrong"})
        assert r.status_code == 401

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": CLIENT["email"], "password": "WrongPass!"})
        assert r.status_code == 401

    def test_register_new_client(self):
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@propmanage.io"
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "Test1234!", "name": "Test User", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000100",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["email"] == email
        assert d["role"] == "client"
        assert d.get("wallet_balance") == 0.0
        assert "password_hash" not in d
        assert "access_token" in s.cookies

    def test_register_duplicate(self):
        r = requests.post(f"{API}/auth/register", json={
            "email": CLIENT["email"], "password": "X12345!", "name": "X", "role": "client"
        })
        assert r.status_code == 400

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_logout(self):
        s = make_session(CLIENT)
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        # After logout, /auth/me without cookies should fail
        s2 = requests.Session()
        r2 = s2.get(f"{API}/auth/me")
        assert r2.status_code == 401


# ========== PROPERTIES ==========
class TestProperties:
    def test_client_sees_own_property(self):
        s = make_session(CLIENT)
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        assert len(props) >= 1
        assert all(p.get("name") for p in props)
        # Has seed property
        names = [p["name"] for p in props]
        assert "Skyline Loft A4" in names

    def test_admin_sees_all_properties(self):
        s = make_session(ADMIN)
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_specialist_cannot_create_property(self):
        s = make_session(SPEC)
        r = s.post(f"{API}/properties", json={
            "name": "X", "address": "Y", "type": "apartment", "surface": 50.0, "rooms": 2
        })
        assert r.status_code == 403


# ========== REQUESTS / MARKETPLACE FLOW ==========
class TestRequests:
    def test_client_sees_own_requests(self):
        s = make_session(CLIENT)
        r = s.get(f"{API}/requests")
        assert r.status_code == 200
        reqs = r.json()
        assert len(reqs) >= 3  # seed has 3
        assert all(req["client_id"] for req in reqs)

    def test_specialist_sees_open_and_assigned(self):
        s = make_session(SPEC)
        r = s.get(f"{API}/requests")
        assert r.status_code == 200
        reqs = r.json()
        # All should be open OR assigned to this specialist
        for req in reqs:
            assert req["status"] == "open" or req.get("specialist_id")

    def test_admin_sees_all_requests(self):
        s = make_session(ADMIN)
        r = s.get(f"{API}/requests")
        assert r.status_code == 200

    def test_create_request_as_client(self):
        s = make_session(CLIENT)
        props = s.get(f"{API}/properties").json()
        prop_id = props[0]["id"]
        r = s.post(f"{API}/requests", json={
            "property_id": prop_id, "category": "electric",
            "title": "TEST_Request", "description": "Test description",
            "priority": "normal", "budget_estimate": 100.0
        })
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "open"
        assert d["category"] == "electric"
        assert d["client_id"]
        # Verify GET returns it
        r2 = s.get(f"{API}/requests/{d['id']}")
        assert r2.status_code == 200
        assert r2.json()["title"] == "TEST_Request"

    def test_specialist_cannot_create_request(self):
        s = make_session(SPEC)
        r = s.post(f"{API}/requests", json={
            "property_id": "000000000000000000000000", "category": "x",
            "title": "t", "description": "d"
        })
        assert r.status_code == 403


# ========== FULL MARKETPLACE FLOW: accept -> start -> complete -> confirm ==========
class TestMarketplaceFlow:
    @pytest.fixture(scope="class")
    def created_request(self):
        s = make_session(CLIENT)
        props = s.get(f"{API}/properties").json()
        prop_id = props[0]["id"]
        r = s.post(f"{API}/requests", json={
            "property_id": prop_id, "category": "plumbing",
            "title": "TEST_Flow", "description": "End to end flow test",
            "priority": "normal", "budget_estimate": 300.0
        })
        assert r.status_code == 200
        return {"id": r.json()["id"], "property_id": prop_id}

    def test_specialist_accept_deducts_wallet(self, created_request):
        s = make_session(SPEC2)  # use spec2 to avoid balance issues if reruns
        me_before = s.get(f"{API}/auth/me").json()
        bal_before = me_before.get("wallet_balance", 0)
        if bal_before < 45:
            pytest.skip("Insufficient balance on spec2 to test accept")

        r = s.post(f"{API}/requests/{created_request['id']}/accept")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True

        me_after = s.get(f"{API}/auth/me").json()
        assert me_after["wallet_balance"] == pytest.approx(bal_before - 45.0, abs=0.01)

        # Verify request status
        req = s.get(f"{API}/requests/{created_request['id']}").json()
        assert req["status"] == "assigned"
        assert req["specialist_id"]

    def test_accept_already_assigned_fails(self, created_request):
        s = make_session(SPEC)
        r = s.post(f"{API}/requests/{created_request['id']}/accept")
        assert r.status_code == 400

    def test_client_places_escrow(self, created_request):
        s = make_session(CLIENT)
        r = s.post(f"{API}/requests/{created_request['id']}/escrow?amount=300")
        assert r.status_code == 200
        assert r.json()["amount"] == 300
        req = s.get(f"{API}/requests/{created_request['id']}").json()
        assert req["escrow_amount"] == 300
        assert req.get("escrow_status") == "held"

    def test_specialist_start(self, created_request):
        s = make_session(SPEC2)
        r = s.post(f"{API}/requests/{created_request['id']}/start")
        assert r.status_code == 200
        req = s.get(f"{API}/requests/{created_request['id']}").json()
        assert req["status"] == "in_progress"

    def test_specialist_complete(self, created_request):
        s = make_session(SPEC2)
        r = s.post(f"{API}/requests/{created_request['id']}/complete")
        assert r.status_code == 200
        req = s.get(f"{API}/requests/{created_request['id']}").json()
        assert req["status"] == "completed"

    def test_client_confirm_releases_escrow_and_tokens(self, created_request):
        s = make_session(CLIENT)
        me_before = s.get(f"{API}/auth/me").json()
        tokens_before = me_before.get("tokens", 0)
        prop_before = s.get(f"{API}/properties/{created_request['property_id']}").json()
        health_before = prop_before.get("health_score", 0)

        # Get specialist balance before
        ss = make_session(SPEC2)
        spec_before = ss.get(f"{API}/auth/me").json()
        spec_bal_before = spec_before.get("wallet_balance", 0)

        r = s.post(f"{API}/requests/{created_request['id']}/confirm")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tokens_earned"] == 100

        me_after = s.get(f"{API}/auth/me").json()
        assert me_after["tokens"] == tokens_before + 100

        # Property health +5
        prop_after = s.get(f"{API}/properties/{created_request['property_id']}").json()
        assert prop_after["health_score"] == health_before + 5

        # Specialist got 95% of 300 = 285
        spec_after = ss.get(f"{API}/auth/me").json()
        assert spec_after["wallet_balance"] == pytest.approx(spec_bal_before + 285.0, abs=0.01)

        # Status confirmed
        req = s.get(f"{API}/requests/{created_request['id']}").json()
        assert req["status"] == "confirmed"
        assert req.get("escrow_status") == "released"


# ========== ADMIN ==========
class TestAdmin:
    def test_admin_stats(self):
        s = make_session(ADMIN)
        r = s.get(f"{API}/admin/stats")
        assert r.status_code == 200
        d = r.json()
        for k in ["users", "specialists", "verified", "pending_verification", "active_jobs", "completed_jobs"]:
            assert k in d
            assert isinstance(d[k], int)
        assert d["specialists"] >= 2

    def test_pending_specialists(self):
        s = make_session(ADMIN)
        r = s.get(f"{API}/admin/specialists/pending")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_client_cannot_access_admin_stats(self):
        s = make_session(CLIENT)
        r = s.get(f"{API}/admin/stats")
        assert r.status_code == 403

    def test_specialist_cannot_access_admin(self):
        s = make_session(SPEC)
        r = s.get(f"{API}/admin/specialists/pending")
        assert r.status_code == 403

    def test_admin_verify_specialist(self):
        # Register an unverified specialist, then admin verifies
        email = f"specnew_{uuid.uuid4().hex[:6]}@propmanage.io"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "email": email, "password": "Test1234!", "name": "New Spec", "role": "specialist",
            "service_categories": ["handyman"], "coverage_zones": ["bucuresti-sector1"],
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000101",
        })
        assert r.status_code == 200
        spec_id = r.json()["id"]
        assert r.json().get("verified") is False

        a = make_session(ADMIN)
        rv = a.post(f"{API}/admin/specialists/{spec_id}/verify")
        assert rv.status_code == 200

        # Confirm by logging in as that specialist
        s2 = make_session({"email": email, "password": "Test1234!"})
        me = s2.get(f"{API}/auth/me").json()
        assert me["verified"] is True
        assert me["tier"] == "VERIFIED"


# ========== OPERATOR ==========
class TestOperator:
    def test_operator_queue(self):
        s = make_session(OPERATOR)
        r = s.get(f"{API}/operator/queue")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_client_cannot_access_operator(self):
        s = make_session(CLIENT)
        r = s.get(f"{API}/operator/queue")
        assert r.status_code == 403


# ========== WALLET / TRANSACTIONS ==========
class TestWallet:
    def test_wallet_topup(self):
        s = make_session(SPEC)
        me_before = s.get(f"{API}/auth/me").json()
        bal_before = me_before["wallet_balance"]
        r = s.post(f"{API}/wallet/topup?amount=50")
        assert r.status_code == 200
        me_after = s.get(f"{API}/auth/me").json()
        assert me_after["wallet_balance"] == pytest.approx(bal_before + 50, abs=0.01)

    def test_topup_invalid(self):
        s = make_session(CLIENT)
        r = s.post(f"{API}/wallet/topup?amount=0")
        assert r.status_code == 400
        r2 = s.post(f"{API}/wallet/topup?amount=99999")
        assert r2.status_code == 400

    def test_transactions_list(self):
        s = make_session(SPEC)
        r = s.get(f"{API}/transactions")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ========== SEED IDEMPOTENCY ==========
class TestSeed:
    def test_all_demo_accounts_login(self):
        for creds in [CLIENT, SPEC, SPEC2, ADMIN, OPERATOR]:
            r = requests.post(f"{API}/auth/login", json=creds)
            assert r.status_code == 200, f"login failed for {creds['email']}"
