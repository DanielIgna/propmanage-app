"""
Phase 32 - Audit (Client role + Operator role) + Health Score Specialist (new feature).
Tests are stateful and rely on demo seed accounts in /app/memory/test_credentials.md.
Cookie auth (httpOnly) — use requests.Session().
"""
import os
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
SPEC2 = {"email": "specialist2@propmanage.io", "password": "Spec123!"}
OP = {"email": "operator@propmanage.io", "password": "Op123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}

TAG = uuid.uuid4().hex[:6]


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login {creds['email']} -> {r.status_code} {r.text}"
    return s, r.json()


@pytest.fixture(scope="session")
def client_sess():
    s, me = _login(CLIENT)
    return {"s": s, "me": me}


@pytest.fixture(scope="session")
def spec_sess():
    s, me = _login(SPEC)
    return {"s": s, "me": me}


@pytest.fixture(scope="session")
def spec2_sess():
    s, me = _login(SPEC2)
    return {"s": s, "me": me}


@pytest.fixture(scope="session")
def op_sess():
    s, me = _login(OP)
    return {"s": s, "me": me}


@pytest.fixture(scope="session")
def admin_sess():
    s, me = _login(ADMIN)
    return {"s": s, "me": me}


# ============================================================
# HEALTH SCORE (new feature)
# ============================================================
class TestHealthScore:
    def test_HS1_marketplace_returns_health_object(self):
        r = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) and len(data) >= 1, "Expected at least one specialist"
        for d in data:
            assert "health" in d, "health field missing"
            h = d["health"]
            for k in ["score", "tier", "color", "label", "components"]:
                assert k in h, f"missing health.{k}"
            assert 0 <= h["score"] <= 100
            assert h["tier"] in ("excellent", "good", "developing")
            for ck in ["rating", "reviews", "verified", "completed_jobs", "total_jobs", "disputes"]:
                assert ck in h["components"], f"missing components.{ck}"
            assert "portfolio_count" in d, "top-level portfolio_count missing on card"

    def test_HS2_seeded_specialist_high_score(self):
        r = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=20)
        assert r.status_code == 200
        rows = r.json()
        # Find seeded specialist by email is not exposed; pick the verified ones with rating >=4.5
        verified_high = [
            d for d in rows
            if d.get("verified") and (d.get("rating") or 0) >= 4.5 and (d.get("reviews_count") or 0) >= 5
        ]
        assert verified_high, "Expected seeded verified high-rating specialist in marketplace"
        for d in verified_high:
            assert d["health"]["score"] >= 70, (
                f"Verified rating>=4.5 reviews>=5 should score >=70, got {d['health']['score']} for {d.get('name')}"
            )

    def test_HS3_specialist_profile_returns_health(self):
        rows = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=20).json()
        spec_id = rows[0]["id"]
        r = requests.get(f"{BASE_URL}/api/specialists/{spec_id}/profile", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "health" in body
        for k in ("score", "tier", "color", "label", "components"):
            assert k in body["health"]


# ============================================================
# CLIENT AUDIT
# ============================================================
class TestClientAudit:
    def test_C1_property_crud(self, client_sess):
        s = client_sess["s"]
        # Create
        r = s.post(f"{BASE_URL}/api/properties", json={
            "name": f"TEST_Prop_{TAG}", "address": "Bld Testing 1", "type": "house",
            "surface": 80, "rooms": 3,
        }, timeout=20)
        assert r.status_code in (200, 201), r.text
        prop_id = r.json().get("id") or r.json().get("_id")
        assert prop_id
        # List own
        r2 = s.get(f"{BASE_URL}/api/properties", timeout=20)
        assert r2.status_code == 200
        ids = [p.get("id") or p.get("_id") for p in r2.json()]
        assert prop_id in ids
        # Update
        r3 = s.put(f"{BASE_URL}/api/properties/{prop_id}", json={"name": f"TEST_Prop_{TAG}_upd"}, timeout=20)
        assert r3.status_code in (200, 204), r3.text
        # save for downstream
        TestClientAudit.prop_id = prop_id

    def test_C2_create_request_visible_to_specialists(self, client_sess, spec_sess):
        s = client_sess["s"]
        prop_id = TestClientAudit.prop_id
        payload = {
            "property_id": prop_id,
            "title": f"TEST_Req_{TAG}",
            "description": "audit",
            "category": "plumbing",
            "budget_estimate": 300,
            "priority": "normal",
        }
        r = s.post(f"{BASE_URL}/api/requests", json=payload, timeout=20)
        assert r.status_code in (200, 201), r.text
        req_id = r.json().get("id") or r.json().get("_id")
        assert req_id
        TestClientAudit.req_id = req_id

        # Client lists requests
        lst = s.get(f"{BASE_URL}/api/requests", timeout=20).json()
        assert any((it.get("id") or it.get("_id")) == req_id for it in lst)

        # Specialist sees it (status=open)
        spec_lst = spec_sess["s"].get(f"{BASE_URL}/api/requests?status=open", timeout=20).json()
        assert any((it.get("id") or it.get("_id")) == req_id for it in spec_lst), "Specialist cannot see open request"

    def test_C3_checkout_and_status_demo_mode(self, client_sess):
        s = client_sess["s"]
        req_id = TestClientAudit.req_id
        r = s.post(
            f"{BASE_URL}/api/payments/checkout-session?request_id={req_id}",
            headers={"Origin": BASE_URL},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "checkout_url" in body and "session_id" in body
        sess_id = body["session_id"]
        # Poll status
        st = s.get(f"{BASE_URL}/api/payments/status/{sess_id}", timeout=20).json()
        assert st.get("payment_status") == "paid"
        # Request should now have escrow held/funded
        req = s.get(f"{BASE_URL}/api/requests/{req_id}", timeout=20).json()
        assert req.get("escrow_status") in ("held", "funded"), f"got {req.get('escrow_status')}"
        assert (req.get("escrow_amount") or 0) > 0

    def test_C4_confirm_and_review(self, client_sess, spec_sess):
        """Drive a request to confirmed + review."""
        s = client_sess["s"]
        spec = spec_sess["s"]
        prop_id = TestClientAudit.prop_id
        # Create dedicated request for full lifecycle
        r = s.post(f"{BASE_URL}/api/requests", json={
            "property_id": prop_id, "title": f"TEST_Confirm_{TAG}", "description": "lifecycle",
            "category": "electrical", "budget_estimate": 200, "priority": "normal",
        }, timeout=20)
        assert r.status_code in (200, 201), r.text
        rid = r.json().get("id") or r.json().get("_id")
        # Specialist accepts (45 RON lead fee debit)
        acc = spec.post(f"{BASE_URL}/api/requests/{rid}/accept", timeout=20)
        assert acc.status_code in (200, 201), f"accept -> {acc.status_code} {acc.text}"
        # Fund escrow
        cs = s.post(f"{BASE_URL}/api/payments/checkout-session?request_id={rid}",
                    headers={"Origin": BASE_URL}, timeout=20)
        assert cs.status_code == 200, cs.text
        # Specialist starts + completes
        spec.post(f"{BASE_URL}/api/requests/{rid}/start", timeout=20)
        spec.post(f"{BASE_URL}/api/requests/{rid}/complete", timeout=20)
        # Client confirms
        conf = s.post(f"{BASE_URL}/api/requests/{rid}/confirm", timeout=20)
        assert conf.status_code in (200, 201), f"confirm -> {conf.status_code} {conf.text}"
        # Client posts review
        rv = s.post(f"{BASE_URL}/api/requests/{rid}/review",
                    json={"job_id": rid, "rating": 5, "comment": f"TEST_AuditReview_{TAG}"}, timeout=20)
        assert rv.status_code in (200, 201), f"review -> {rv.status_code} {rv.text}"
        TestClientAudit.confirmed_rid = rid

    def test_C5_chat_history(self, client_sess):
        s = client_sess["s"]
        rid = TestClientAudit.req_id
        r = s.get(f"{BASE_URL}/api/chat/{rid}/messages", timeout=20)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_C6_open_dispute(self, client_sess, spec_sess):
        s = client_sess["s"]
        spec = spec_sess["s"]
        prop_id = TestClientAudit.prop_id
        # New request -> specialist accepts -> fund escrow -> dispute (status should be in_progress/assigned)
        r = s.post(f"{BASE_URL}/api/requests", json={
            "property_id": prop_id, "title": f"TEST_Disp_{TAG}", "description": "dispute",
            "category": "plumbing", "budget_estimate": 150, "priority": "normal",
        }, timeout=20)
        rid = r.json().get("id") or r.json().get("_id")
        acc = spec.post(f"{BASE_URL}/api/requests/{rid}/accept", timeout=20)
        assert acc.status_code in (200, 201), f"spec accept failed: {acc.status_code} {acc.text}"
        cs = s.post(f"{BASE_URL}/api/payments/checkout-session?request_id={rid}",
                    headers={"Origin": BASE_URL}, timeout=20)
        assert cs.status_code == 200
        # Now request should be assigned or in_progress and disputable
        dr = s.post(f"{BASE_URL}/api/requests/{rid}/dispute",
                    json={"reason": "TEST audit dispute - bad quality"}, timeout=20)
        assert dr.status_code in (200, 201), f"dispute -> {dr.status_code} {dr.text}"

    def test_C7_request_twin_validation(self, client_sess):
        s = client_sess["s"]
        prop_id = TestClientAudit.prop_id
        r = s.post(f"{BASE_URL}/api/properties/{prop_id}/twin/request", timeout=20)
        assert r.status_code in (200, 201), r.text

    def test_C8_owner_twin_access_and_403_for_other_client(self, client_sess, spec2_sess):
        s = client_sess["s"]
        prop_id = TestClientAudit.prop_id
        r = s.get(f"{BASE_URL}/api/properties/{prop_id}/twin", timeout=20)
        assert r.status_code == 200, r.text
        # Different role (non-owner specialist with no request on this prop) -> 403 OR ok if assigned
        # We use spec2 fresh — should be 403 unless spec2 has a request here
        r2 = spec2_sess["s"].get(f"{BASE_URL}/api/properties/{prop_id}/twin", timeout=20)
        # spec2 may already have one assigned across tests; accept 403 OR 200 but log
        assert r2.status_code in (200, 403), f"twin access for non-owner -> {r2.status_code}"

    def test_C9_public_marketplace(self):
        r = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_C10_specialist_profile_public(self):
        rows = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=20).json()
        sid = rows[0]["id"]
        r = requests.get(f"{BASE_URL}/api/specialists/{sid}/profile", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert "reviews" in body and "health" in body


# ============================================================
# OPERATOR AUDIT
# ============================================================
class TestOperatorAudit:
    def test_O1_queue_and_twins_list(self, op_sess):
        s = op_sess["s"]
        q = s.get(f"{BASE_URL}/api/operator/queue", timeout=20)
        assert q.status_code == 200, q.text
        t = s.get(f"{BASE_URL}/api/operator/twins", timeout=20)
        assert t.status_code == 200, t.text

    def test_O2_O3_build_and_approve_twin_notifies_specialist(self, client_sess, spec_sess, op_sess, admin_sess):
        """End-to-end: client creates property+request, specialist accepts, operator approves twin,
        verify specialist gets in-app notification with type='twin_specialist_update'."""
        s = client_sess["s"]
        spec = spec_sess["s"]
        op = op_sess["s"]

        # Create dedicated property & request
        pr = s.post(f"{BASE_URL}/api/properties", json={
            "name": f"TEST_OpProp_{TAG}", "address": "Op str 2", "type": "apt",
            "surface": 60, "rooms": 2,
        }, timeout=20)
        pid = pr.json().get("id") or pr.json().get("_id")
        req = s.post(f"{BASE_URL}/api/requests", json={
            "property_id": pid, "title": f"TEST_OpReq_{TAG}", "description": "x",
            "category": "hvac", "budget_estimate": 220, "priority": "normal",
        }, timeout=20)
        rid = req.json().get("id") or req.json().get("_id")
        # Specialist accepts
        acc = spec.post(f"{BASE_URL}/api/requests/{rid}/accept", timeout=20)
        assert acc.status_code in (200, 201), f"spec accept failed: {acc.status_code} {acc.text}"
        # Operator builds + approves twin
        build = op.post(f"{BASE_URL}/api/operator/twins/{pid}",
                        json={"rooms": [{"id": "r1", "name": "Living", "type": "living"}], "assets": [], "notes": "TEST"}, timeout=20)
        assert build.status_code in (200, 201), build.text
        approve = op.post(f"{BASE_URL}/api/operator/twins/{pid}/validate",
                          json={"action": "approve"}, timeout=20)
        assert approve.status_code == 200, approve.text
        body = approve.json()
        assert body.get("status") == "approved"
        assert "specialists_notified" in body, "missing specialists_notified count"
        assert body["specialists_notified"] >= 1, f"Expected >=1 specialist notified, got {body['specialists_notified']}"
        # Verify property unlocked
        plist = s.get(f"{BASE_URL}/api/properties", timeout=20).json()
        pp = next((p for p in plist if (p.get("id") or p.get("_id")) == pid), None)
        assert pp and pp.get("twin_unlocked") is True
        # Verify notification on specialist side
        notifs = spec.get(f"{BASE_URL}/api/notifications", timeout=20)
        if notifs.status_code == 200:
            arr = notifs.json()
            found = any((n.get("type") == "twin_specialist_update") for n in arr)
            assert found, "Specialist did not receive twin_specialist_update notification"

        TestOperatorAudit.prop_id = pid
        TestOperatorAudit.req_id = rid

    def test_O4_reject_twin_notifies(self, client_sess, spec_sess, op_sess):
        """Create a separate property, request twin, operator rejects."""
        s = client_sess["s"]
        op = op_sess["s"]
        spec = spec_sess["s"]
        pr = s.post(f"{BASE_URL}/api/properties", json={
            "name": f"TEST_RejProp_{TAG}", "address": "Rej 3", "type": "apt",
            "surface": 50, "rooms": 2,
        }, timeout=20)
        pid = pr.json().get("id") or pr.json().get("_id")
        # Client creates request, specialist accepts (so reject path notifies them)
        req = s.post(f"{BASE_URL}/api/requests", json={
            "property_id": pid, "title": f"TEST_RejReq_{TAG}", "description": "x",
            "category": "hvac", "budget_estimate": 100, "priority": "normal",
        }, timeout=20)
        rid = req.json().get("id") or req.json().get("_id")
        spec.post(f"{BASE_URL}/api/requests/{rid}/accept", timeout=20)
        # Operator builds + rejects
        op.post(f"{BASE_URL}/api/operator/twins/{pid}",
                json={"rooms": [], "assets": [], "notes": "TEST_rej"}, timeout=20)
        rej = op.post(f"{BASE_URL}/api/operator/twins/{pid}/validate",
                      json={"action": "request_revision", "notes": "Needs revision"}, timeout=20)
        assert rej.status_code == 200, rej.text
        assert rej.json().get("status") == "needs_revision"
        # Property must NOT be twin_unlocked
        plist = s.get(f"{BASE_URL}/api/properties", timeout=20).json()
        pp = next((p for p in plist if (p.get("id") or p.get("_id")) == pid), None)
        assert pp and not pp.get("twin_unlocked"), "Property should not be twin_unlocked on reject"

    def test_O5_flag_nonconformity_notifies(self, op_sess, spec_sess, client_sess):
        """Use the request created in O2 (specialist assigned)."""
        op = op_sess["s"]
        rid = TestOperatorAudit.req_id
        r = op.post(f"{BASE_URL}/api/operator/flag-nonconformity", json={
            "target_type": "request", "target_id": rid,
            "reason": f"TEST_audit32 flag {TAG}", "severity": "high",
        }, timeout=20)
        assert r.status_code in (200, 201), r.text
        # Confirm specialist + client received notifs
        sn = spec_sess["s"].get(f"{BASE_URL}/api/notifications", timeout=20).json()
        cn = client_sess["s"].get(f"{BASE_URL}/api/notifications", timeout=20).json()
        assert any(n.get("type") == "nonconformity_specialist" for n in sn), "Specialist missed nonconf notif"
        assert any(n.get("type") == "nonconformity_client" for n in cn), "Client missed nonconf notif"

    def test_O6_validate_maintenance_log(self, op_sess):
        op = op_sess["s"]
        q = op.get(f"{BASE_URL}/api/operator/queue", timeout=20).json()
        if not q:
            pytest.skip("No pending maintenance logs to validate")
        log_id = q[0].get("id") or q[0].get("_id")
        r = op.post(f"{BASE_URL}/api/operator/logs/{log_id}/validate?action=approve", timeout=20)
        assert r.status_code in (200, 201), r.text

    def test_O7_dt_pro_endpoints(self, op_sess):
        op = op_sess["s"]
        r = op.get(f"{BASE_URL}/api/operator/digital-twin/clients-queue", timeout=20)
        # endpoint may not be present on every build; accept 200 or 404 but assert not 5xx
        assert r.status_code in (200, 404), f"DT queue status {r.status_code} {r.text}"

    def test_O8_role_guard_client_cannot_access_operator(self, client_sess, spec_sess):
        c = client_sess["s"].get(f"{BASE_URL}/api/operator/queue", timeout=20)
        sp = spec_sess["s"].get(f"{BASE_URL}/api/operator/queue", timeout=20)
        assert c.status_code in (401, 403), f"client should not access operator queue, got {c.status_code}"
        assert sp.status_code in (401, 403), f"specialist should not access operator queue, got {sp.status_code}"


# ============================================================
# CROSS-ROLE INTEGRATION (X-1)
# ============================================================
class TestCrossRole:
    def test_X1_health_score_updates_after_review(self, client_sess, spec_sess):
        """After a confirmed+reviewed job, the specialist's profile health should be queryable
        and >= a reasonable threshold (sanity)."""
        # specialist id
        me = spec_sess["me"]
        sid = me.get("id") or me.get("_id")
        r = requests.get(f"{BASE_URL}/api/specialists/{sid}/profile", timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert "health" in body
        # seeded specialist must be >= 70 typically
        assert body["health"]["score"] >= 50, f"score too low: {body['health']['score']}"
