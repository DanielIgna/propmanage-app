"""
Phase 13 — Onboarding cycle + Digital Twin enrichment tests.

Covers:
- GET /api/properties now returns twin_status field
- Full cycle: register fresh client → add property → request twin → operator approves
- Regression: Phase 12 demo logins still work
"""

import os
import uuid
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
OPERATOR_EMAIL = "operator@propmanage.io"
OPERATOR_PASS = "Op123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD
SPECIALIST_EMAIL = "specialist@propmanage.io"
SPECIALIST_PASS = "Spec123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


@pytest.fixture(scope="module")
def operator_session():
    return _login(OPERATOR_EMAIL, OPERATOR_PASS)


# ============ Demo logins regression (Phase 1-12) ============
class TestDemoLogins:
    def test_demo_logins_all_roles(self):
        for email, pwd in [
            (CLIENT_EMAIL, CLIENT_PASS),
            (SPECIALIST_EMAIL, SPECIALIST_PASS),
            (ADMIN_EMAIL, ADMIN_PASS),
            (OPERATOR_EMAIL, OPERATOR_PASS),
        ]:
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": pwd})
            assert r.status_code == 200, f"Login failed for {email}"


# ============ Phase 13: twin_status enrichment on GET /api/properties ============
class TestTwinStatusEnrichment:
    def test_properties_list_contains_twin_status_field(self, client_session):
        r = client_session.get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        assert isinstance(props, list)
        # All returned properties MUST have twin_status key (None or string)
        for p in props:
            assert "twin_status" in p, f"Property missing twin_status: {p.get('id')}"
            ts = p["twin_status"]
            assert ts is None or ts in ("pending_validation", "approved", "needs_revision"), \
                f"Unexpected twin_status: {ts}"


# ============ Phase 13: Fresh client → empty state → full E2E twin cycle ============
class TestFreshClientFullCycle:
    """Register a brand new client, add a property, request twin, approve via operator."""

    @pytest.fixture(scope="class")
    def fresh_client(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"test_phase13_fresh_{suffix}@test.io"
        password = "Fresh123!"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": email,
            "password": password,
            "name": "TEST_Phase13 Fresh Client",
            "role": "client",
        })
        assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
        return {"session": s, "email": email, "password": password}

    def test_step1_fresh_client_empty_properties(self, fresh_client):
        r = fresh_client["session"].get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        assert isinstance(props, list)
        assert len(props) == 0, "Fresh client should have ZERO properties (empty state)"

    def test_step2_create_property_returns_in_list_with_null_twin(self, fresh_client):
        s = fresh_client["session"]
        payload = {
            "name": "TEST_Phase13_FreshProp",
            "address": "Strada Test 13, București",
            "type": "apartment",
            "surface": 65.0,
            "rooms": 3,
        }
        r = s.post(f"{API}/properties", json=payload)
        assert r.status_code in (200, 201), f"Property create failed: {r.status_code} {r.text}"
        created = r.json()
        assert "id" in created
        fresh_client["prop_id"] = created["id"]

        # GET should now have 1 property with twin_status == None
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        assert len(props) == 1
        assert props[0]["twin_status"] is None, "Brand new property should have twin_status=None"

    def test_step3_request_twin_sets_pending_validation(self, fresh_client):
        s = fresh_client["session"]
        prop_id = fresh_client.get("prop_id")
        assert prop_id, "prop_id missing — previous step failed"
        r = s.post(f"{API}/properties/{prop_id}/twin/request")
        assert r.status_code == 200, f"Twin request failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("ok") is True

        # GET /api/properties should now show twin_status == 'pending_validation'
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        target = next((p for p in props if p["id"] == prop_id), None)
        assert target is not None
        assert target["twin_status"] == "pending_validation", \
            f"Expected pending_validation, got {target['twin_status']}"

    def test_step4_operator_sees_twin_in_list(self, fresh_client, operator_session):
        prop_id = fresh_client.get("prop_id")
        r = operator_session.get(f"{API}/operator/twins")
        assert r.status_code == 200
        twins = r.json()
        match = next((t for t in twins if t.get("property_id") == prop_id), None)
        assert match is not None, f"Operator should see twin for {prop_id}"
        assert match.get("status") == "pending_validation"
        # Verify enrichment fields are present
        assert match.get("property_name") == "TEST_Phase13_FreshProp"

    def test_step5_operator_approves_and_client_sees_approved(self, fresh_client, operator_session):
        prop_id = fresh_client.get("prop_id")
        r = operator_session.post(
            f"{API}/operator/twins/{prop_id}/validate",
            json={"action": "approve", "notes": "Phase 13 auto-test approve"},
        )
        assert r.status_code == 200, f"Approve failed: {r.status_code} {r.text}"

        # Client refresh
        s = fresh_client["session"]
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        target = next((p for p in props if p["id"] == prop_id), None)
        assert target is not None
        assert target["twin_status"] == "approved", \
            f"Expected approved, got {target['twin_status']}"
        # twin_unlocked should also have flipped True
        assert target.get("twin_unlocked") is True, \
            "Property.twin_unlocked should flip True on approve"

    def test_step6_cleanup_fresh_client_data(self, fresh_client):
        """Best-effort cleanup of test data created in this class."""
        s = fresh_client["session"]
        prop_id = fresh_client.get("prop_id")
        if prop_id:
            s.delete(f"{API}/properties/{prop_id}")
        # No user-self-delete endpoint expected; leave user record (TEST_ prefix only on property)


# ============ Phase 13: needs_revision flow ============
class TestNeedsRevisionFlow:
    @pytest.fixture(scope="class")
    def fresh_client_revise(self):
        suffix = uuid.uuid4().hex[:8]
        email = f"test_phase13_rev_{suffix}@test.io"
        password = "Fresh123!"
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": email, "password": password,
            "name": "TEST_Phase13 Revise Client", "role": "client",
        })
        assert r.status_code == 200
        return {"session": s, "email": email}

    def test_needs_revision_then_resubmit(self, fresh_client_revise, operator_session):
        s = fresh_client_revise["session"]
        # Add property
        r = s.post(f"{API}/properties", json={
            "name": "TEST_Phase13_ReviseProp", "address": "Str.",
            "type": "apartment", "surface": 50.0, "rooms": 2,
        })
        assert r.status_code in (200, 201)
        prop_id = r.json()["id"]

        # Request twin
        r = s.post(f"{API}/properties/{prop_id}/twin/request")
        assert r.status_code == 200

        # Operator rejects → needs_revision
        r = operator_session.post(f"{API}/operator/twins/{prop_id}/validate",
                                  json={"action": "request_revision", "notes": "Phase 13 revise test"})
        assert r.status_code == 200

        # Client GET shows needs_revision
        r = s.get(f"{API}/properties")
        target = next((p for p in r.json() if p["id"] == prop_id), None)
        assert target and target["twin_status"] == "needs_revision"

        # Resubmit
        r = s.post(f"{API}/properties/{prop_id}/twin/request")
        assert r.status_code == 200

        # Now pending again
        r = s.get(f"{API}/properties")
        target = next((p for p in r.json() if p["id"] == prop_id), None)
        assert target and target["twin_status"] == "pending_validation"

        # Cleanup
        s.delete(f"{API}/properties/{prop_id}")
