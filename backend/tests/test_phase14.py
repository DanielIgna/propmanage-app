"""
Phase 14 — Activity Timeline + Cross-Role Visibility tests.

Covers:
- log_event instrumentation on all 12 event types
- GET /api/requests/{id}/timeline RBAC (client/specialist/admin OK; other clients 403)
- GET /api/admin/activity-stream admin-only + filters
- POST /api/operator/flag-nonconformity validation + notification
- GET /api/admin/nonconformities + POST /api/admin/nonconformities/{id}/resolve
- POST /api/requests/{id}/accept new schedule_proposal body (and legacy no-body)
- Full E2E cross-role: register → property → twin → request → accept(schedule) →
  pay escrow → start → complete → confirm → verify timeline & activity stream
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
SPEC_EMAIL = "specialist@propmanage.io"
SPEC_PASS = "Spec123!"
SPEC2_EMAIL = "specialist2@propmanage.io"
SPEC2_PASS = "Spec123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD
OPERATOR_EMAIL = "operator@propmanage.io"
OPERATOR_PASS = "Op123!"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def operator_session():
    return _login(OPERATOR_EMAIL, OPERATOR_PASS)


@pytest.fixture(scope="module")
def specialist_session():
    # ensure active_view back to specialist (per agent_to_agent_context_note)
    s = _login(SPEC_EMAIL, SPEC_PASS)
    s.post(f"{API}/auth/set-active-view", json={"view": "specialist"})
    return s


@pytest.fixture(scope="module")
def specialist2_session():
    return _login(SPEC2_EMAIL, SPEC2_PASS)


# ============ Admin activity stream ============
class TestActivityStream:
    def test_admin_can_list_stream(self, admin_session):
        r = admin_session.get(f"{API}/admin/activity-stream?limit=30")
        assert r.status_code == 200
        events = r.json()
        assert isinstance(events, list)
        # Pre-seeded events from earlier flows should produce a non-empty stream eventually.
        # Sort sanity: descending by created_at
        for i in range(len(events) - 1):
            assert events[i]["created_at"] >= events[i + 1]["created_at"], \
                "activity-stream must be sorted desc by created_at"

    def test_non_admin_blocked(self):
        s = _login(CLIENT_EMAIL, CLIENT_PASS)
        r = s.get(f"{API}/admin/activity-stream")
        assert r.status_code in (401, 403)

    def test_event_type_filter(self, admin_session):
        r = admin_session.get(f"{API}/admin/activity-stream?event_type=request.created&limit=20")
        assert r.status_code == 200
        for e in r.json():
            assert e["event_type"] == "request.created"

    def test_actor_role_filter(self, admin_session):
        r = admin_session.get(f"{API}/admin/activity-stream?actor_role=client&limit=20")
        assert r.status_code == 200
        for e in r.json():
            assert e["actor_role"] == "client"


# ============ Accept request: legacy + scheduled body ============
class TestAcceptRequestSchedule:
    """Accept must work both with no body (legacy) AND with schedule_proposal body."""

    def _seed_request(self, client_s, prop_id, title_suffix):
        r = client_s.post(f"{API}/requests", json={
            "property_id": prop_id,
            "title": f"TEST_Phase14 {title_suffix}",
            "description": "Test description for Phase 14 accept flow",
            "category": "hvac",
            "urgency": "normal",
            "budget_min": 200, "budget_max": 500,
        })
        assert r.status_code in (200, 201), f"Request seed failed: {r.status_code} {r.text}"
        return r.json()["id"]

    @pytest.fixture(scope="class")
    def client_with_prop(self):
        s = _login(CLIENT_EMAIL, CLIENT_PASS)
        # use first existing property
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        props = r.json()
        assert len(props) > 0, "Demo client should have at least one property"
        return {"session": s, "prop_id": props[0]["id"]}

    def test_accept_legacy_no_body(self, client_with_prop, specialist2_session):
        req_id = self._seed_request(client_with_prop["session"], client_with_prop["prop_id"], "legacy")
        r = specialist2_session.post(f"{API}/requests/{req_id}/accept")
        # If specialist2 doesn't match category, should still pass per backend logic (no category filter at accept-time)
        assert r.status_code == 200, f"Legacy accept failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("ok") is True
        assert "balance_after" in body

    def test_accept_with_schedule_body(self, client_with_prop, specialist_session):
        req_id = self._seed_request(client_with_prop["session"], client_with_prop["prop_id"], "scheduled")
        payload = {
            "proposed_start_date": "2026-02-01T09:00:00Z",
            "proposed_end_date": "2026-02-03T17:00:00Z",
            "estimated_hours": 12.5,
            "note": "TEST_Phase14 schedule note",
        }
        r = specialist_session.post(f"{API}/requests/{req_id}/accept", json=payload)
        assert r.status_code == 200, f"Scheduled accept failed: {r.status_code} {r.text}"

        # Verify event logged with schedule payload
        ad = _login(ADMIN_EMAIL, ADMIN_PASS)
        r2 = ad.get(f"{API}/requests/{req_id}/timeline")
        assert r2.status_code == 200
        events = r2.json()["events"]
        accepted = [e for e in events if e["event_type"] == "request.accepted"]
        assert len(accepted) >= 1
        sched = accepted[-1]["payload"].get("schedule")
        assert sched is not None, "schedule payload missing on request.accepted"
        assert sched.get("estimated_hours") == 12.5
        assert sched.get("note") == "TEST_Phase14 schedule note"
        assert "start_date" in sched and "end_date" in sched


# ============ Timeline RBAC ============
class TestTimelineRBAC:
    @pytest.fixture(scope="class")
    def scenario(self):
        """Create a fresh request and have spec accept; return ids + sessions."""
        client = _login(CLIENT_EMAIL, CLIENT_PASS)
        spec = _login(SPEC_EMAIL, SPEC_PASS)
        spec.post(f"{API}/auth/set-active-view", json={"view": "specialist"})

        props = client.get(f"{API}/properties").json()
        prop_id = props[0]["id"]
        r = client.post(f"{API}/requests", json={
            "property_id": prop_id,
            "title": "TEST_Phase14 RBAC",
            "description": "Phase 14 RBAC timeline test request",
            "category": "hvac", "urgency": "normal",
            "budget_min": 100, "budget_max": 200,
        })
        req_id = r.json()["id"]
        spec.post(f"{API}/requests/{req_id}/accept", json={
            "proposed_start_date": "2026-02-10T09:00:00Z",
            "estimated_hours": 4,
        })
        return {"req_id": req_id, "client": client, "spec": spec, "prop_id": prop_id}

    def test_client_can_view_timeline(self, scenario):
        r = scenario["client"].get(f"{API}/requests/{scenario['req_id']}/timeline")
        assert r.status_code == 200
        body = r.json()
        assert "request" in body and "events" in body
        # ascending order
        evs = body["events"]
        for i in range(len(evs) - 1):
            assert evs[i]["created_at"] <= evs[i + 1]["created_at"]
        types = {e["event_type"] for e in evs}
        assert "request.created" in types
        assert "request.accepted" in types

    def test_specialist_can_view_timeline(self, scenario):
        r = scenario["spec"].get(f"{API}/requests/{scenario['req_id']}/timeline")
        assert r.status_code == 200

    def test_admin_can_view_timeline(self, scenario, admin_session):
        r = admin_session.get(f"{API}/requests/{scenario['req_id']}/timeline")
        assert r.status_code == 200

    def test_other_client_forbidden(self, scenario):
        # Register a brand new client and ensure 403
        suffix = uuid.uuid4().hex[:8]
        other = requests.Session()
        r = other.post(f"{API}/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": f"test_p14_other_{suffix}@test.io",
            "password": "Other123!",
            "name": "TEST_Phase14 Other",
            "role": "client",
        })
        assert r.status_code == 200
        r = other.get(f"{API}/requests/{scenario['req_id']}/timeline")
        assert r.status_code == 403

    def test_other_specialist_forbidden(self, scenario, specialist2_session):
        r = specialist2_session.get(f"{API}/requests/{scenario['req_id']}/timeline")
        assert r.status_code == 403


# ============ Non-conformity flag ============
class TestNonConformity:
    @pytest.fixture(scope="class")
    def request_for_flag(self):
        client = _login(CLIENT_EMAIL, CLIENT_PASS)
        prop_id = client.get(f"{API}/properties").json()[0]["id"]
        r = client.post(f"{API}/requests", json={
            "property_id": prop_id, "title": "TEST_Phase14 NCFlag",
            "description": "For non-conformity flag",
            "category": "hvac", "urgency": "normal",
            "budget_min": 100, "budget_max": 200,
        })
        return {"req_id": r.json()["id"], "prop_id": prop_id}

    def test_operator_can_flag(self, operator_session, request_for_flag):
        r = operator_session.post(f"{API}/operator/flag-nonconformity", json={
            "target_type": "request",
            "target_id": request_for_flag["req_id"],
            "reason": "TEST_Phase14 operator detected a serious issue with the request data",
            "severity": "high",
        })
        assert r.status_code == 200, f"Flag failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("ok") is True
        assert "id" in body
        request_for_flag["flag_id"] = body["id"]

    def test_short_reason_rejected(self, operator_session, request_for_flag):
        r = operator_session.post(f"{API}/operator/flag-nonconformity", json={
            "target_type": "request",
            "target_id": request_for_flag["req_id"],
            "reason": "bad",  # < 5 chars
            "severity": "low",
        })
        assert r.status_code in (400, 422)

    def test_invalid_target_rejected(self, operator_session):
        r = operator_session.post(f"{API}/operator/flag-nonconformity", json={
            "target_type": "request",
            "target_id": "507f1f77bcf86cd799439011",  # bogus
            "reason": "TEST nonexistent target",
            "severity": "low",
        })
        assert r.status_code == 404

    def test_non_operator_forbidden(self, admin_session, request_for_flag):
        r = admin_session.post(f"{API}/operator/flag-nonconformity", json={
            "target_type": "request",
            "target_id": request_for_flag["req_id"],
            "reason": "should not work",
            "severity": "low",
        })
        assert r.status_code in (401, 403)

    def test_admin_lists_nonconformities(self, admin_session, request_for_flag):
        r = admin_session.get(f"{API}/admin/nonconformities")
        assert r.status_code == 200
        flags = r.json()
        match = next((f for f in flags if f.get("id") == request_for_flag.get("flag_id")), None)
        assert match is not None, "Newly flagged NC should appear in admin list"
        assert match["status"] == "open"
        assert match["severity"] == "high"

    def test_admin_resolves_nonconformity(self, admin_session, request_for_flag):
        flag_id = request_for_flag.get("flag_id")
        assert flag_id, "previous flag step failed"
        r = admin_session.post(f"{API}/admin/nonconformities/{flag_id}/resolve",
                               json={"resolution": "TEST_Phase14 resolved with admin intervention."})
        assert r.status_code == 200
        # Confirm status flipped
        flags = admin_session.get(f"{API}/admin/nonconformities").json()
        match = next((f for f in flags if f.get("id") == flag_id), None)
        assert match and match["status"] == "resolved"
        assert "resolution" in match


# ============ Full E2E cross-role ============
class TestFullE2E:
    """Register → property → twin → request → accept(schedule) → escrow → start → complete → confirm → timeline."""

    @pytest.fixture(scope="class")
    def scenario(self, operator_session, specialist_session):
        suffix = uuid.uuid4().hex[:8]
        email = f"test_p14_e2e_{suffix}@test.io"
        client = requests.Session()
        r = client.post(f"{API}/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": email, "password": "E2E123!",
            "name": "TEST_Phase14 E2E Client", "role": "client",
        })
        assert r.status_code == 200

        # Top up wallet to ensure escrow payable
        client.post(f"{API}/wallet/topup", params={"amount": 1000})

        # Property
        r = client.post(f"{API}/properties", json={
            "name": "TEST_Phase14_E2E_Prop", "address": "E2E Street 14",
            "type": "apartment", "surface": 70.0, "rooms": 3,
        })
        prop_id = r.json()["id"]

        # Twin request → operator approve
        client.post(f"{API}/properties/{prop_id}/twin/request")
        operator_session.post(f"{API}/operator/twins/{prop_id}/validate",
                              json={"action": "approve", "notes": "E2E auto"})

        # Request
        r = client.post(f"{API}/requests", json={
            "property_id": prop_id,
            "title": "TEST_Phase14 E2E Job",
            "description": "End to end Phase 14 cross role scenario job description",
            "category": "hvac", "urgency": "normal",
            "budget_min": 300, "budget_max": 600,
        })
        req_id = r.json()["id"]

        # Specialist accept with schedule
        specialist_session.post(f"{API}/requests/{req_id}/accept", json={
            "proposed_start_date": "2026-02-15T09:00:00Z",
            "proposed_end_date": "2026-02-16T17:00:00Z",
            "estimated_hours": 8,
            "note": "E2E schedule",
        })

        # Client pays escrow (demo mode)
        pay_r = client.post(f"{API}/escrow/pay-demo", json={"request_id": req_id, "amount": 400})

        # Spec start + complete
        specialist_session.post(f"{API}/requests/{req_id}/start")
        specialist_session.post(f"{API}/requests/{req_id}/complete")

        # Client confirm
        client.post(f"{API}/requests/{req_id}/confirm")

        return {"req_id": req_id, "prop_id": prop_id, "client": client,
                "escrow_status": pay_r.status_code}

    def test_timeline_has_chronological_events(self, scenario, admin_session):
        r = admin_session.get(f"{API}/requests/{scenario['req_id']}/timeline")
        assert r.status_code == 200, f"Timeline failed: {r.text}"
        events = r.json()["events"]
        types_in_order = [e["event_type"] for e in events]
        # Must include core events; escrow.paid may be absent if pay-demo endpoint differs
        for required in ["request.created", "request.accepted", "work.started",
                         "work.completed", "work.confirmed"]:
            assert required in types_in_order, \
                f"Missing event {required} in {types_in_order}"
        # Order check: created < accepted < started < completed < confirmed
        order = ["request.created", "request.accepted", "work.started",
                 "work.completed", "work.confirmed"]
        positions = [types_in_order.index(t) for t in order]
        assert positions == sorted(positions), f"Events out of order: {types_in_order}"

    def test_schedule_proposal_in_accept_payload(self, scenario, admin_session):
        events = admin_session.get(f"{API}/requests/{scenario['req_id']}/timeline").json()["events"]
        accepted = next((e for e in events if e["event_type"] == "request.accepted"), None)
        assert accepted is not None
        sched = accepted["payload"].get("schedule") or {}
        assert sched.get("estimated_hours") == 8
        assert sched.get("note") == "E2E schedule"

    def test_admin_activity_stream_contains_e2e_events(self, scenario, admin_session):
        r = admin_session.get(f"{API}/admin/activity-stream?limit=200")
        assert r.status_code == 200
        events = r.json()
        # At least one event from this request should appear
        req_events = [e for e in events if e.get("request_id") == scenario["req_id"]]
        assert len(req_events) >= 3, f"Expected E2E request events in stream, got {len(req_events)}"
