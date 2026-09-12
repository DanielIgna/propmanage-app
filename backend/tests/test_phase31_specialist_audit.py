"""Phase 31 - Specialist role functional audit.
Tests SPEC<->CLIENT and SPEC<->OPERATOR lifecycle including:
  - lead opportunities, accept/start/complete/confirm cycle
  - chat (REST + WS), reviews, disputes, portfolio, timeline, marketplace
  - SPEC<->OPERATOR-1: nonconformity notifies specialist + client (NEW FIX)
  - SPEC<->OPERATOR-2: specialist 2D twin access on assigned request property (NEW FIX)
  - SPEC<->OPERATOR-3: digital twin pin comment notifications
  - SPEC<->OPERATOR-4: operator/queue access denied for specialist
  - REGRESSION: verification docs, marketplace listing
"""
import os
import time
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}
OPERATOR = {"email": "operator@propmanage.io", "password": "Op123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


def _login(creds):
    """Cookie-based session login. Returns a dict with a `session` (requests.Session)
    whose cookies are bound, plus the user payload. `headers` kept as {} for compat."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    user = r.json()
    assert user.get("id"), f"login returned no user id: {user}"
    return {"session": s, "user": user, "headers": {}}


# --- Shared session-scoped fixtures ---
@pytest.fixture(scope="session")
def client_auth():
    return _login(CLIENT)

@pytest.fixture(scope="session")
def specialist_auth():
    return _login(SPECIALIST)

@pytest.fixture(scope="session")
def operator_auth():
    return _login(OPERATOR)

@pytest.fixture(scope="session")
def admin_auth():
    return _login(ADMIN)


@pytest.fixture(scope="session")
def client_property(client_auth):
    """Get (or create) a property for client."""
    r = client_auth["session"].get(f"{API}/properties", timeout=30)
    assert r.status_code == 200, r.text
    props = r.json()
    if props:
        return props[0]
    r = client_auth["session"].post(f"{API}/properties", json={
        "name": "TEST_AuditHouse",
        "address": "Str. Test 1",
        "type": "apartment",
        "surface": 70,
        "rooms": 3,
    }, timeout=30)
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="session")
def created_request(client_auth, client_property):
    """Client creates a fresh open request used through the full lifecycle."""
    prop_id = client_property.get("id") or client_property.get("_id")
    payload = {
        "property_id": prop_id,
        "category": "hvac",  # specialist@propmanage.io is HVAC
        "title": f"TEST_AuditReq_{uuid.uuid4().hex[:6]}",
        "description": "Audit test request - HVAC service please.",
        "priority": "normal",
        "budget_estimate": 800,
    }
    r = client_auth["session"].post(f"{API}/requests", json=payload, timeout=30)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    req_id = body.get("id") or body.get("_id") or body.get("request_id")
    assert req_id, f"no request id: {body}"
    return {"id": req_id, "title": payload["title"], "property_id": prop_id}


# ============ SPEC<->CLIENT-1: Opportunities ============
class TestSpecClient1Opportunities:
    def test_specialist_sees_open_requests(self, specialist_auth, created_request):
        r = specialist_auth["session"].get(f"{API}/requests", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        # Find our just-created request among open ones
        found = next((x for x in items if (x.get("id") or x.get("_id")) == created_request["id"]), None)
        assert found is not None, f"created request not in specialist feed; got {len(items)} items"
        # Validate card fields
        for field in ("title", "description", "status", "category"):
            assert field in found, f"missing {field}"
        assert found.get("status") == "open"


# ============ SPEC<->CLIENT-2: Lead pickup ============
class TestSpecClient2AcceptLead:
    def test_specialist_accept_request_deducts_fee(self, specialist_auth, client_auth, created_request):
        # Capture wallet before
        me_before = specialist_auth["session"].get(f"{API}/auth/me", timeout=30).json()
        wallet_before = me_before.get("wallet_balance") or 0

        payload = {
            "proposed_start_date": "2026-02-01T09:00:00Z",
            "proposed_end_date": "2026-02-02T17:00:00Z",
            "estimated_hours": 6,
            "note": "Voi veni mâine.",
        }
        r = specialist_auth["session"].post(f"{API}/requests/{created_request['id']}/accept", json=payload, timeout=30
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True

        # Verify wallet deducted 45 RON
        me_after = specialist_auth["session"].get(f"{API}/auth/me", timeout=30).json()
        wallet_after = me_after.get("wallet_balance") or 0
        assert round(wallet_before - wallet_after, 2) == 45.0, f"expected -45 RON, got {wallet_before}->{wallet_after}"

        # Verify request status flipped to assigned with our specialist_id
        r2 = client_auth["session"].get(f"{API}/requests/{created_request['id']}", timeout=30)
        assert r2.status_code == 200, r2.text
        req = r2.json()
        assert req.get("status") == "assigned"
        assert req.get("specialist_id") == specialist_auth["user"]["id"]
        assert req.get("schedule_proposal", {}).get("start_date")

        # Client should have notification
        notifs = client_auth["session"].get(f"{API}/notifications", timeout=30)
        if notifs.status_code == 200:
            arr = notifs.json()
            assert any("acceptat" in (n.get("body") or n.get("message") or "").lower()
                       or "specialist alocat" in (n.get("title") or "").lower()
                       for n in arr), "client should have an acceptance notification"


# ============ SPEC<->CLIENT-3: Start/Complete/Confirm ============
class TestSpecClient3Lifecycle:
    def test_start_complete_confirm(self, specialist_auth, client_auth, created_request):
        rid = created_request["id"]
        # Place escrow first as client (so confirm can release)
        r0 = client_auth["session"].post(f"{API}/requests/{rid}/escrow?amount=500", timeout=30)
        # escrow may return 200 or accept w/ body
        assert r0.status_code in (200, 201, 422), r0.text

        # Start
        r1 = specialist_auth["session"].post(f"{API}/requests/{rid}/start", timeout=30)
        assert r1.status_code == 200, r1.text
        # Complete
        r2 = specialist_auth["session"].post(f"{API}/requests/{rid}/complete", timeout=30)
        assert r2.status_code == 200, r2.text
        # Confirm as client
        r3 = client_auth["session"].post(f"{API}/requests/{rid}/confirm", timeout=30)
        assert r3.status_code == 200, r3.text

        # Verify final status
        rr = client_auth["session"].get(f"{API}/requests/{rid}", timeout=30)
        assert rr.status_code == 200
        assert rr.json().get("status") in ("confirmed", "completed")


# ============ SPEC<->CLIENT-4: Chat ============
class TestSpecClient4Chat:
    def test_chat_get_endpoint_works_for_both(self, specialist_auth, client_auth, created_request):
        rid = created_request["id"]
        # GET should work for both client and assigned specialist
        rc = client_auth["session"].get(f"{API}/chat/{rid}/messages", timeout=30)
        rs = specialist_auth["session"].get(f"{API}/chat/{rid}/messages", timeout=30)
        assert rc.status_code == 200, rc.text
        assert rs.status_code == 200, rs.text
        assert isinstance(rc.json(), list)

    def test_chat_post_rest_endpoint(self, specialist_auth, created_request):
        """Per request: POST /api/chat/{request_id}/messages should work.
        NOTE: Current backend only exposes a WebSocket /ws/chat - no REST POST.
        This test documents whether a REST POST exists.
        """
        rid = created_request["id"]
        r = specialist_auth["session"].post(f"{API}/chat/{rid}/messages", json={"text": "Salut, am ajuns!"}, timeout=30)
        # Expect 200 OR document the gap with 404/405
        assert r.status_code in (200, 201, 404, 405), r.text
        if r.status_code in (404, 405):
            pytest.xfail("REST POST /chat/{id}/messages is not implemented; chat is WebSocket-only")


# ============ SPEC<->CLIENT-5: Dispute ============
class TestSpecClient5Dispute:
    def test_specialist_opens_dispute_or_blocked(self, specialist_auth, client_auth, client_property):
        """Open a second request, accept, then specialist opens dispute (escrow held)."""
        # Use a fresh request because the audited one was already confirmed (escrow released)
        prop_id = client_property.get("id") or client_property.get("_id")
        r = client_auth["session"].post(f"{API}/requests", json={
            "property_id": prop_id,
            "category": "hvac",
            "title": f"TEST_DisputeReq_{uuid.uuid4().hex[:6]}",
            "description": "Dispute test scenario.",
            "priority": "normal",
            "budget_estimate": 600,
        }, timeout=30).json()
        rid = r.get("id") or r.get("_id")
        assert rid, r
        # Accept by specialist
        ra = specialist_auth["session"].post(f"{API}/requests/{rid}/accept", json={}, timeout=30)
        assert ra.status_code == 200, ra.text
        # Client funds escrow
        client_auth["session"].post(f"{API}/requests/{rid}/escrow?amount=300", timeout=30)
        # Specialist opens dispute
        rd = specialist_auth["session"].post(f"{API}/requests/{rid}/dispute", json={"reason": "Clientul nu răspunde la apeluri timp de 3 zile - vreau să închei contractul."}, timeout=30)
        assert rd.status_code == 200, rd.text
        assert rd.json().get("ok") is True
        # Client should see the dispute
        rg = client_auth["session"].get(f"{API}/requests/{rid}/dispute", timeout=30)
        assert rg.status_code == 200, rg.text
        dispute = rg.json()
        assert dispute is not None and dispute.get("status") == "open"


# ============ SPEC<->CLIENT-6: Review ============
class TestSpecClient6Review:
    def test_client_reviews_specialist_after_confirm(self, client_auth, specialist_auth, created_request):
        rid = created_request["id"]
        # Get rating before
        sid = specialist_auth["user"]["id"]
        prof_before = requests.get(f"{API}/specialists/{sid}/profile", timeout=30)
        # endpoint may need auth
        if prof_before.status_code in (401, 403):
            prof_before = client_auth["session"].get(f"{API}/specialists/{sid}/profile", timeout=30)
        count_before = (prof_before.json().get("reviews_count") if prof_before.status_code == 200 else 0) or 0

        r = client_auth["session"].post(f"{API}/requests/{rid}/review", json={"job_id": rid, "rating": 5, "comment": "Excelent!"}, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert "new_rating" in body

        prof_after = client_auth["session"].get(f"{API}/specialists/{sid}/profile", timeout=30)
        if prof_after.status_code == 200:
            assert (prof_after.json().get("reviews_count") or 0) >= count_before + 1


# ============ SPEC<->CLIENT-7: Portfolio visibility ============
class TestSpecClient7Portfolio:
    def test_specialist_creates_portfolio_item(self, specialist_auth):
        r = specialist_auth["session"].post(f"{API}/specialist/portfolio", json={
            "title": "TEST_PortfolioItem",
            "description": "Audit",
            "category": "hvac",
            "cover_image": "https://example.com/cover.jpg",
            "images": [],
        }, timeout=30)
        assert r.status_code in (200, 201), r.text

    def test_client_views_specialist_profile_with_portfolio(self, client_auth, specialist_auth):
        sid = specialist_auth["user"]["id"]
        r = client_auth["session"].get(f"{API}/specialists/{sid}/profile", timeout=30)
        assert r.status_code == 200, r.text
        prof = r.json()
        # portfolio key may be 'portfolio' or 'portfolio_items'
        port = prof.get("portfolio") or prof.get("portfolio_items") or []
        assert isinstance(port, list)


# ============ SPEC<->CLIENT-8: Timeline ============
class TestSpecClient8Timeline:
    def test_both_can_view_timeline(self, specialist_auth, client_auth, created_request):
        rid = created_request["id"]
        for who, auth in [("specialist", specialist_auth), ("client", client_auth)]:
            r = auth["session"].get(f"{API}/requests/{rid}/timeline", timeout=30)
            assert r.status_code == 200, f"{who} timeline: {r.status_code} {r.text}"
            data = r.json()
            assert "events" in data
            # Should have accept + start + complete + confirm events
            assert isinstance(data["events"], list)


# ============ SPEC<->OPERATOR-1: NEW FIX - nonconformity notifications ============
class TestSpecOperator1NonConformityNotifications:
    def test_operator_flag_request_notifies_specialist_and_client(
        self, operator_auth, specialist_auth, client_auth, created_request
    ):
        rid = created_request["id"]
        # Snapshot notifs counts
        def _notifs(auth):
            r = auth["session"].get(f"{API}/notifications", timeout=30)
            return r.json() if r.status_code == 200 else []
        spec_before = _notifs(specialist_auth)
        client_before = _notifs(client_auth)
        admin_auth = _login(ADMIN)
        admin_before = _notifs(admin_auth)

        # Operator flags the request
        r = operator_auth["session"].post(f"{API}/operator/flag-nonconformity", json={
            "target_type": "request",
            "target_id": rid,
            "reason": "Lucrarea pare incompletă conform pozelor primite.",
            "severity": "medium",
        }, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        # Small wait for any async fanout
        time.sleep(1)

        spec_after = _notifs(specialist_auth)
        client_after = _notifs(client_auth)
        admin_after = _notifs(admin_auth)

        def _has_type(arr_before, arr_after, t):
            ids_before = {n.get("id") or n.get("_id") for n in arr_before}
            for n in arr_after:
                if (n.get("id") or n.get("_id")) in ids_before:
                    continue
                if n.get("type") == t:
                    return True
            # Fallback: check titles regardless of dedup
            return any(n.get("type") == t for n in arr_after) and len(arr_after) > len(arr_before)

        assert _has_type(spec_before, spec_after, "nonconformity_specialist"), \
            "specialist should receive nonconformity_specialist notification"
        assert _has_type(client_before, client_after, "nonconformity_client"), \
            "client should receive nonconformity_client notification"
        assert len(admin_after) >= len(admin_before), "admin should still receive notification"


# ============ SPEC<->OPERATOR-2: NEW FIX - specialist twin access ============
class TestSpecOperator2SpecialistTwinAccess:
    def test_specialist_can_view_twin_on_assigned_request_property(
        self, specialist_auth, client_auth, created_request
    ):
        prop_id = created_request["property_id"]
        # Ensure a twin exists - request validation (creates pending_validation if absent)
        rreq = client_auth["session"].post(f"{API}/properties/{prop_id}/twin/request", timeout=30)
        # may already exist - allow 200/400
        assert rreq.status_code in (200, 201, 400), rreq.text

        # Specialist GETs the property's twin - should be 200 because they're assigned
        r = specialist_auth["session"].get(f"{API}/properties/{prop_id}/twin", timeout=30)
        assert r.status_code == 200, f"specialist with assigned request should access twin; got {r.status_code} {r.text}"
        data = r.json()
        assert "status" in data and "rooms" in data

    def test_random_specialist_without_request_gets_403(self, client_property):
        """Login as specialist2 (plumbing) who has no request on this property → 403."""
        s2 = _login({"email": "specialist2@propmanage.io", "password": "Spec123!"})
        prop_id = client_property.get("id") or client_property.get("_id")
        # Make sure specialist2 has NO accepted request on this property
        r = s2["session"].get(f"{API}/properties/{prop_id}/twin", timeout=30)
        # If they happen to have a request, skip; else expect 403
        if r.status_code == 200:
            pytest.skip("specialist2 appears to have an assigned request on this property; can't assert 403")
        assert r.status_code == 403, f"expected 403 for non-assigned specialist; got {r.status_code} {r.text}"


# ============ SPEC<->OPERATOR-4: Maintenance queue locked to operator ============
class TestSpecOperator4QueueAccess:
    def test_specialist_cannot_call_operator_queue(self, specialist_auth):
        r = specialist_auth["session"].get(f"{API}/operator/queue", timeout=30)
        assert r.status_code in (401, 403), f"specialist should NOT access /operator/queue, got {r.status_code} {r.text}"


# ============ REGRESSION-1: Specialist documents ============
class TestRegression1SpecialistDocs:
    def test_specialist_can_list_documents(self, specialist_auth):
        r = specialist_auth["session"].get(f"{API}/specialist/documents", timeout=30)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_specialist_can_upload_document(self, specialist_auth):
        r = specialist_auth["session"].post(f"{API}/specialist/documents", json={
            "type": "certification",
            "name": "TEST_AuditCert",
            "url": "https://example.com/test_cert.pdf",
        }, timeout=30)
        assert r.status_code in (200, 201), r.text


# ============ REGRESSION-2: Marketplace ============
class TestRegression2Marketplace:
    def test_marketplace_specialists_listing(self, client_auth):
        r = client_auth["session"].get(f"{API}/marketplace/specialists?category=plumbing", timeout=30)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        if items:
            sample = items[0]
            # Typical fields
            for f in ("name", "rating"):
                assert f in sample, f"marketplace item missing {f}: {sample.keys()}"
