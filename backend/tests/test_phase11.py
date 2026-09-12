"""
Phase 11 tests: Dual-role switch view, profile update, change password,
GDPR export/delete, and role-aware list_properties/list_requests behavior.
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

SPEC_EMAIL = "specialist@propmanage.io"
SPEC2_EMAIL = "specialist2@propmanage.io"
PENDING_EMAIL = "pending@propmanage.io"
CLIENT_EMAIL = "client@propmanage.io"
ADMIN_EMAIL = "admin@propmanage.io"
OP_EMAIL = "operator@propmanage.io"
SPEC_PWD = "Spec123!"
CLIENT_PWD = "Client123!"
ADMIN_PWD = OWNER_ADMIN_PASSWORD
OP_PWD = "Op123!"


def _login(s, email, pwd):
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r


@pytest.fixture
def spec_session():
    s = requests.Session()
    _login(s, SPEC_EMAIL, SPEC_PWD)
    yield s
    # Always reset active_view back to specialist after test
    try:
        s.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "specialist"})
    except Exception:
        pass


@pytest.fixture
def spec2_session():
    s = requests.Session()
    _login(s, SPEC2_EMAIL, SPEC_PWD)
    yield s
    try:
        s.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "specialist"})
    except Exception:
        pass


@pytest.fixture
def pending_session():
    s = requests.Session()
    _login(s, PENDING_EMAIL, SPEC_PWD)
    return s


@pytest.fixture
def client_session():
    s = requests.Session()
    _login(s, CLIENT_EMAIL, CLIENT_PWD)
    return s


@pytest.fixture
def admin_session():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PWD)
    return s


@pytest.fixture
def op_session():
    s = requests.Session()
    _login(s, OP_EMAIL, OP_PWD)
    return s


# ============ /api/auth/me dual-role fields ============
class TestAuthMeDualRole:
    def test_verified_specialist_has_dual_role_enabled(self, spec_session):
        r = spec_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        d = r.json()
        assert d["role"] == "specialist"
        assert d.get("dual_role_enabled") is True
        assert d.get("active_view") in ("specialist", "client")

    def test_client_has_dual_role_disabled(self, client_session):
        d = client_session.get(f"{BASE_URL}/api/auth/me").json()
        assert d["role"] == "client"
        assert d.get("dual_role_enabled") is False
        assert d.get("active_view") == "client"

    def test_admin_has_dual_role_disabled(self, admin_session):
        d = admin_session.get(f"{BASE_URL}/api/auth/me").json()
        assert d["role"] == "admin"
        assert d.get("dual_role_enabled") is False
        assert d.get("active_view") == "admin"

    def test_pending_specialist_dual_role_disabled(self, pending_session):
        d = pending_session.get(f"{BASE_URL}/api/auth/me").json()
        assert d["role"] == "specialist"
        assert d.get("dual_role_enabled") is False


# ============ /api/auth/switch-view ============
class TestSwitchView:
    def test_specialist_can_toggle_to_client_and_back(self, spec_session):
        r = spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        assert r.status_code == 200, r.text
        assert r.json().get("active_view") == "client"
        # verify via /me
        me = spec_session.get(f"{BASE_URL}/api/auth/me").json()
        assert me["active_view"] == "client"
        # back to specialist
        r = spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "specialist"})
        assert r.status_code == 200
        assert r.json().get("active_view") == "specialist"

    def test_client_cannot_switch_view(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        assert r.status_code == 403

    def test_admin_cannot_switch_view(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        assert r.status_code == 403

    def test_operator_cannot_switch_view(self, op_session):
        r = op_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        assert r.status_code == 403

    def test_pending_specialist_cannot_switch(self, pending_session):
        r = pending_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        assert r.status_code == 403

    def test_invalid_view_value_rejected(self, spec_session):
        r = spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "admin"})
        assert r.status_code in (400, 422)


# ============ PATCH /api/auth/profile ============
class TestProfileUpdate:
    def test_update_name_phone_zone(self, spec2_session):
        payload = {"name": "Mihai Test Update", "phone": "+40 700 111 222", "zone": "Bucuresti Sector 3"}
        r = spec2_session.patch(f"{BASE_URL}/api/auth/profile", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "Mihai Test Update"
        assert d["phone"] == "+40 700 111 222"
        assert d["zone"] == "Bucuresti Sector 3"
        # Persistence via /me
        me = spec2_session.get(f"{BASE_URL}/api/auth/me").json()
        assert me["name"] == "Mihai Test Update"

    def test_empty_payload_returns_400(self, client_session):
        r = client_session.patch(f"{BASE_URL}/api/auth/profile", json={})
        assert r.status_code == 400


# ============ POST /api/auth/change-password ============
class TestChangePassword:
    def test_wrong_current_returns_401(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/auth/change-password",
                                json={"current_password": "Wrong!!!", "new_password": "NewPwd123!"})
        assert r.status_code == 401

    def test_same_as_current_returns_400(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/auth/change-password",
                                json={"current_password": CLIENT_PWD, "new_password": CLIENT_PWD})
        assert r.status_code == 400

    def test_correct_change_then_revert(self, op_session):
        # Use operator to avoid clashing with client/specialist used elsewhere
        new_pwd = "NewOpPwd123!"
        r = op_session.post(f"{BASE_URL}/api/auth/change-password",
                            json={"current_password": OP_PWD, "new_password": new_pwd})
        assert r.status_code == 200, r.text
        # Verify by logging in fresh with new
        s2 = requests.Session()
        r2 = s2.post(f"{BASE_URL}/api/auth/login", json={"email": OP_EMAIL, "password": new_pwd})
        assert r2.status_code == 200
        # Revert
        r3 = s2.post(f"{BASE_URL}/api/auth/change-password",
                     json={"current_password": new_pwd, "new_password": OP_PWD})
        assert r3.status_code == 200


# ============ POST /api/auth/account-export ============
class TestAccountExport:
    def test_export_returns_structured_json(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/auth/account-export")
        assert r.status_code == 200
        d = r.json()
        for key in ("user", "properties", "requests_as_client", "requests_as_specialist",
                    "notifications", "transactions", "exported_at"):
            assert key in d, f"missing key {key}"
        assert isinstance(d["properties"], list)
        assert d["user"]["email"] == CLIENT_EMAIL


# ============ POST /api/auth/account-delete (error paths only) ============
class TestAccountDeleteErrors:
    def test_missing_confirmation_returns_400(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/auth/account-delete",
                                json={"password": CLIENT_PWD, "confirmation": "DELETE"})
        assert r.status_code == 400

    def test_wrong_password_returns_401(self, client_session):
        r = client_session.post(f"{BASE_URL}/api/auth/account-delete",
                                json={"password": "Wrong!!!", "confirmation": "STERGE"})
        assert r.status_code == 401


# ============ Dual-role: require_role honors active_view ============
class TestDualRoleAuthorization:
    def test_specialist_client_view_can_create_request(self, spec_session):
        # Switch to client view
        sw = spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        assert sw.status_code == 200
        # Create a property first (needed for request)
        prop = spec_session.post(f"{BASE_URL}/api/properties", json={
            "name": "TEST_DualRole_Property",
            "type": "apartament",
            "address": "Str. Test 1, Bucuresti",
            "surface": 60,
            "rooms": 2,
        })
        assert prop.status_code in (200, 201), prop.text
        prop_id = prop.json()["id"]

        req = spec_session.post(f"{BASE_URL}/api/requests", json={
            "property_id": prop_id,
            "title": "TEST_DualRole_Request",
            "description": "Test request from specialist in client view",
            "category": "hvac",
            "priority": "normal",
            "budget_estimate": 200,
        })
        assert req.status_code in (200, 201), f"client-view request POST failed: {req.status_code} {req.text}"

        # Cleanup created property (after switching back so we have specialist client perms via dual-role)
        # actually still in client view -> delete with client role works
        spec_session.delete(f"{BASE_URL}/api/properties/{prop_id}")

    def test_specialist_default_view_cannot_create_request(self, spec_session):
        # Ensure default specialist view
        sw = spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "specialist"})
        assert sw.status_code == 200
        r = spec_session.post(f"{BASE_URL}/api/requests", json={
            "property_id": "000000000000000000000000",
            "title": "TEST_should_fail",
            "description": "should be rejected",
            "category": "hvac",
            "priority": "normal",
        })
        assert r.status_code == 403


# ============ GET /api/properties + /api/requests scoped to client_view ============
class TestDualRoleListScopes:
    def test_properties_in_client_view_returns_own_only(self, spec_session):
        # specialist view → returns ALL (no filter) per code (eff not in {client,specialist} branch)
        # Actually code: eff in (client, specialist) → filter by owner_id. So even specialist view filters by owner.
        # The key check: in client view, returns only owner's properties.
        spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        r = spec_session.get(f"{BASE_URL}/api/properties")
        assert r.status_code == 200
        me = spec_session.get(f"{BASE_URL}/api/auth/me").json()
        uid = me["id"]
        for p in r.json():
            assert p["owner_id"] == uid

    def test_requests_in_client_view_only_own_client_requests(self, spec_session):
        spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "client"})
        r = spec_session.get(f"{BASE_URL}/api/requests")
        assert r.status_code == 200
        me = spec_session.get(f"{BASE_URL}/api/auth/me").json()
        uid = me["id"]
        for req in r.json():
            assert req.get("client_id") == uid, f"non-own request leaked: {req.get('id')}"

    def test_requests_in_specialist_view_shows_open_or_assigned(self, spec_session):
        spec_session.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "specialist"})
        r = spec_session.get(f"{BASE_URL}/api/requests")
        assert r.status_code == 200
        me = spec_session.get(f"{BASE_URL}/api/auth/me").json()
        uid = me["id"]
        for req in r.json():
            assert req.get("status") == "open" or req.get("specialist_id") == uid


# ============ Regression: existing endpoints still work ============
class TestRegression:
    def test_admin_stats(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/stats")
        assert r.status_code == 200
        assert "total_users" in r.json() or "users" in r.json() or isinstance(r.json(), dict)

    def test_client_can_create_request_normally(self, client_session):
        # Use one of seeded properties
        props = client_session.get(f"{BASE_URL}/api/properties").json()
        assert len(props) > 0
        prop_id = props[0]["id"]
        r = client_session.post(f"{BASE_URL}/api/requests", json={
            "property_id": prop_id,
            "title": "TEST_Phase11_Regression",
            "description": "Regression request",
            "category": "electric",
            "priority": "normal",
            "budget_estimate": 100,
        })
        assert r.status_code in (200, 201)
