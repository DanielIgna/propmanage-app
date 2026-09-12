"""Phase 6 backend tests: Admin Dashboard Workflows (Specialist Documents Validation,
Disputes Open & Resolve), and Operator Digital Twin endpoints. Plus regression smoke."""
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
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
PENDING = {"email": "pending@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
OPERATOR = {"email": "operator@propmanage.io", "password": "Op123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    return s, r


@pytest.fixture(scope="module")
def admin_session():
    s, r = _login(ADMIN)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s, r = _login(CLIENT)
    assert r.status_code == 200, f"client login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def spec_session():
    s, r = _login(SPEC)
    assert r.status_code == 200, f"spec login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def pending_spec_session():
    s, r = _login(PENDING)
    assert r.status_code == 200, f"pending login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def operator_session():
    s, r = _login(OPERATOR)
    assert r.status_code == 200, f"operator login failed: {r.status_code} {r.text}"
    return s


# ============ SPECIALIST DOCUMENTS (self-upload) ============

class TestSpecialistDocuments:
    def test_list_my_documents(self, pending_spec_session):
        r = pending_spec_session.get(f"{BASE_URL}/api/specialist/documents", timeout=15)
        assert r.status_code == 200, r.text
        docs = r.json()
        assert isinstance(docs, list)
        # Pending spec seeded with 3 documents
        assert len(docs) >= 3, f"pending spec should have >=3 seeded docs, got {len(docs)}"
        types = {d.get("type") for d in docs}
        # At least one of id_card / certification / insurance
        assert any(t in types for t in ("id_card", "certification", "insurance")), types

    def test_upload_and_delete_document(self, spec_session):
        # Upload
        payload = {
            "type": "certification",
            "name": f"TEST_phase6_cert_{int(time.time())}",
            "url": "data:application/pdf;base64,JVBERi0xLjQK",  # fake tiny pdf
        }
        r = spec_session.post(f"{BASE_URL}/api/specialist/documents", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        doc = r.json()
        assert doc.get("id") and doc.get("status") == "pending"
        assert doc.get("type") == "certification"
        doc_id = doc["id"]

        # Verify it's listed
        r2 = spec_session.get(f"{BASE_URL}/api/specialist/documents", timeout=15)
        assert r2.status_code == 200
        ids = [d.get("id") for d in r2.json()]
        assert doc_id in ids

        # Delete
        r3 = spec_session.delete(f"{BASE_URL}/api/specialist/documents/{doc_id}", timeout=15)
        assert r3.status_code == 200

        # Verify gone
        r4 = spec_session.get(f"{BASE_URL}/api/specialist/documents", timeout=15)
        assert doc_id not in [d.get("id") for d in r4.json()]

    def test_upload_requires_specialist_role(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/specialist/documents",
            json={"type": "id_card", "name": "x", "url": "data:,"},
            timeout=10,
        )
        assert r.status_code in (401, 403)


# ============ ADMIN SPECIALIST VERIFICATION ============

class TestAdminSpecialistFlow:
    def test_pending_specialists_includes_pending_user(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/specialists/pending", timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1
        emails = [i.get("email") for i in items]
        assert "pending@propmanage.io" in emails, emails
        # no leaked _id
        for i in items:
            assert "_id" not in i and i.get("id"), i

    def test_admin_specialist_detail_has_documents(self, admin_session):
        # Find pending spec id
        r = admin_session.get(f"{BASE_URL}/api/admin/specialists/pending", timeout=15)
        assert r.status_code == 200
        pending = next(i for i in r.json() if i.get("email") == "pending@propmanage.io")
        spec_id = pending["id"]

        r2 = admin_session.get(f"{BASE_URL}/api/admin/specialists/{spec_id}", timeout=15)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data.get("email") == "pending@propmanage.io"
        docs = data.get("documents") or []
        assert len(docs) >= 3, f"expected 3 seeded docs, got {len(docs)}"

    def test_admin_review_individual_document(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/specialists/pending", timeout=15)
        pending = next(i for i in r.json() if i.get("email") == "pending@propmanage.io")
        spec_id = pending["id"]
        # Get docs
        r2 = admin_session.get(f"{BASE_URL}/api/admin/specialists/{spec_id}", timeout=15)
        docs = r2.json().get("documents") or []
        # Find a doc still pending; if all reviewed (idempotency from prior runs), pick any
        doc = next((d for d in docs if d.get("status") == "pending"), docs[0])
        doc_id = doc["id"]
        r3 = admin_session.post(
            f"{BASE_URL}/api/admin/specialists/{spec_id}/documents/{doc_id}/review",
            json={"status": "approved", "reason": "TEST_phase6 looks legit"},
            timeout=15,
        )
        assert r3.status_code == 200, r3.text
        # Verify persisted
        r4 = admin_session.get(f"{BASE_URL}/api/admin/specialists/{spec_id}", timeout=15)
        d2 = next(d for d in r4.json().get("documents", []) if d.get("id") == doc_id)
        assert d2.get("status") == "approved"
        assert d2.get("validated_at")

    def test_admin_review_nonexistent_doc_404(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/specialists/pending", timeout=15)
        pending = next(i for i in r.json() if i.get("email") == "pending@propmanage.io")
        spec_id = pending["id"]
        r2 = admin_session.post(
            f"{BASE_URL}/api/admin/specialists/{spec_id}/documents/does-not-exist/review",
            json={"status": "approved"},
            timeout=10,
        )
        assert r2.status_code == 404

    def test_admin_reject_requires_role(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/admin/specialists/507f1f77bcf86cd799439011/reject",
            json={"reason": "TEST_phase6 unauthorized"},
            timeout=10,
        )
        assert r.status_code in (401, 403)


# ============ DISPUTES ============

def _ensure_active_request_with_escrow(client_session, spec_session):
    """Find or create an in_progress request with escrow held, return req_id + client + spec ids."""
    # First check existing pool
    r = client_session.get(f"{BASE_URL}/api/requests", timeout=15)
    assert r.status_code == 200
    for req in r.json():
        if req.get("status") in ("assigned", "in_progress", "completed") and not req.get("disputed"):
            # Pre-existing job we can use
            return req["id"]
    # else create fresh end-to-end
    props = client_session.get(f"{BASE_URL}/api/properties", timeout=15).json()
    if not props:
        cr = client_session.post(
            f"{BASE_URL}/api/properties",
            json={"label": "TEST_phase6_prop", "address": "Str D 1", "type": "apartment", "surface": 60},
            timeout=15,
        )
        prop_id = cr.json()["id"]
    else:
        prop_id = props[0]["id"]
    rreq = client_session.post(
        f"{BASE_URL}/api/requests",
        json={
            "property_id": prop_id,
            "title": f"TEST_phase6 dispute job {uuid.uuid4().hex[:6]}",
            "description": "test dispute flow",
            "category": "hvac",
            "priority": "high",
        },
        timeout=15,
    )
    assert rreq.status_code in (200, 201), rreq.text
    req_id = rreq.json()["id"]
    # Specialist accepts (pays 45 RON lead fee)
    ra = spec_session.post(f"{BASE_URL}/api/requests/{req_id}/accept", timeout=15)
    assert ra.status_code == 200, ra.text
    # Client funds escrow
    re = client_session.post(
        f"{BASE_URL}/api/requests/{req_id}/escrow", params={"amount": 300}, timeout=15
    )
    assert re.status_code == 200, re.text
    # Specialist starts
    rs = spec_session.post(f"{BASE_URL}/api/requests/{req_id}/start", timeout=15)
    assert rs.status_code == 200, rs.text
    return req_id


class TestDisputes:
    def test_open_dispute_as_client(self, client_session, spec_session):
        req_id = _ensure_active_request_with_escrow(client_session, spec_session)
        # Skip if already disputed
        rd = client_session.get(f"{BASE_URL}/api/requests/{req_id}/dispute", timeout=10)
        if rd.status_code == 200 and rd.json():
            pytest.skip("dispute already exists on this request")
        r = client_session.post(
            f"{BASE_URL}/api/requests/{req_id}/dispute",
            json={"reason": "TEST_phase6 lucrarea nu este conformă cu specificațiile"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("id")
        # Verify request flagged
        all_reqs = client_session.get(f"{BASE_URL}/api/requests", timeout=15).json()
        req = next(x for x in all_reqs if x["id"] == req_id)
        assert req.get("disputed") is True
        assert req.get("escrow_status") == "frozen"
        # Duplicate open should fail
        r2 = client_session.post(
            f"{BASE_URL}/api/requests/{req_id}/dispute",
            json={"reason": "TEST_phase6 duplicate attempt"},
            timeout=10,
        )
        assert r2.status_code == 400

    def test_open_dispute_unauthorized_user_403(self, client_session, spec_session):
        # third party (operator) tries to open dispute on someone else's req
        op_s, _ = _login(OPERATOR)
        # any request id
        reqs = client_session.get(f"{BASE_URL}/api/requests", timeout=10).json()
        if not reqs:
            pytest.skip("no requests available")
        req_id = reqs[0]["id"]
        r = op_s.post(
            f"{BASE_URL}/api/requests/{req_id}/dispute",
            json={"reason": "TEST_phase6 outsider attempt to dispute"},
            timeout=10,
        )
        assert r.status_code in (403, 400)

    def test_admin_lists_disputes_enriched(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/disputes", timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        if not items:
            pytest.skip("no disputes seeded/created yet")
        # Find an open one for enrichment check (or any)
        d = next((x for x in items if x.get("status") == "open"), items[0])
        # Enrichment keys
        for k in ("request_title", "client_name", "specialist_name", "escrow_amount"):
            assert k in d, f"missing enrichment key {k} in dispute: {d}"
        assert "_id" not in d and d.get("id")

    def test_admin_resolve_dispute_split(self, admin_session, client_session, spec_session):
        # Get an open dispute (create one if needed)
        items = admin_session.get(f"{BASE_URL}/api/admin/disputes", timeout=15).json()
        open_d = next((x for x in items if x.get("status") == "open"), None)
        if not open_d:
            # Create a new disputed job
            req_id = _ensure_active_request_with_escrow(client_session, spec_session)
            cs_open = client_session.post(
                f"{BASE_URL}/api/requests/{req_id}/dispute",
                json={"reason": "TEST_phase6 need resolve flow"},
                timeout=15,
            )
            assert cs_open.status_code == 200, cs_open.text
            items = admin_session.get(f"{BASE_URL}/api/admin/disputes", timeout=15).json()
            open_d = next(x for x in items if x.get("status") == "open")
        dispute_id = open_d["id"]
        amount = float(open_d.get("escrow_amount") or 0)

        # Resolve as split 60/40
        r = admin_session.post(
            f"{BASE_URL}/api/admin/disputes/{dispute_id}/resolve",
            json={"resolution": "split", "client_pct": 60, "notes": "TEST_phase6 60/40"},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        if amount > 0:
            expected_client = amount * 0.60
            expected_spec = (amount - expected_client) * 0.95
            assert abs(body["client_amount"] - expected_client) < 0.01, body
            assert abs(body["specialist_amount"] - expected_spec) < 0.01, body
        # Resolving again should 400
        r2 = admin_session.post(
            f"{BASE_URL}/api/admin/disputes/{dispute_id}/resolve",
            json={"resolution": "refund_client"},
            timeout=10,
        )
        assert r2.status_code == 400


# ============ OPERATOR DIGITAL TWIN ============

class TestOperatorTwin:
    def test_list_twins_enriched(self, operator_session):
        r = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 1, "expected seeded twin"
        # Find Skyline Loft A4 pending twin (or first)
        twin = next((t for t in items if "Skyline" in (t.get("property_name") or "")), items[0])
        for k in ("property_id", "status", "property_name"):
            assert k in twin, f"missing {k} in {twin}"
        assert "_id" not in twin

    def test_get_twin_by_property(self, operator_session):
        items = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=15).json()
        prop_id = items[0]["property_id"]
        r = operator_session.get(f"{BASE_URL}/api/operator/twins/{prop_id}", timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t.get("property_id") == prop_id
        assert "rooms" in t and "assets" in t

    def test_get_twin_for_property_without_twin_returns_empty_draft(self, operator_session, client_session):
        # Find a client property that has no twin
        twins = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=15).json()
        twin_props = {t["property_id"] for t in twins}
        props = client_session.get(f"{BASE_URL}/api/properties", timeout=10).json()
        target = next((p for p in props if p["id"] not in twin_props), None)
        if not target:
            pytest.skip("all client properties already have twins")
        r = operator_session.get(f"{BASE_URL}/api/operator/twins/{target['id']}", timeout=15)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t.get("status") == "draft"
        assert t["rooms"] == [] and t["assets"] == []

    def test_save_twin_persistence(self, operator_session):
        items = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=15).json()
        prop_id = items[0]["property_id"]
        # Fetch current twin to preserve and add a TEST_ asset
        current = operator_session.get(f"{BASE_URL}/api/operator/twins/{prop_id}", timeout=15).json()
        rooms = current.get("rooms") or []
        assets = current.get("assets") or []
        new_asset_id = f"test_phase6_asset_{uuid.uuid4().hex[:6]}"
        assets_payload = assets + [{
            "id": new_asset_id,
            "type": "lighting",
            "name": "TEST_phase6 lampa",
            "x": 10, "y": 10,
            "condition": "good",
        }]
        # Rooms must have valid types per pydantic
        rooms_payload = []
        for r_ in rooms:
            rooms_payload.append({
                "id": r_.get("id"),
                "name": r_.get("name", ""),
                "type": r_.get("type", "other"),
                "area": r_.get("area", 0),
                "x": r_.get("x", 0), "y": r_.get("y", 0),
                "w": r_.get("w", 100), "h": r_.get("h", 100),
            })
        payload = {"rooms": rooms_payload, "assets": assets_payload, "notes": "TEST_phase6"}
        r = operator_session.post(f"{BASE_URL}/api/operator/twins/{prop_id}", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        # Verify persisted
        r2 = operator_session.get(f"{BASE_URL}/api/operator/twins/{prop_id}", timeout=15)
        twin = r2.json()
        ids = [a.get("id") for a in twin.get("assets", [])]
        assert new_asset_id in ids, ids

    def test_request_twin_validation_as_client(self, client_session, operator_session):
        props = client_session.get(f"{BASE_URL}/api/properties", timeout=10).json()
        if not props:
            pytest.skip("no properties")
        prop_id = props[0]["id"]
        r = client_session.post(f"{BASE_URL}/api/properties/{prop_id}/twin/request", timeout=15)
        assert r.status_code == 200, r.text
        # Verify operator now sees it pending
        twins = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=15).json()
        match = next((t for t in twins if t.get("property_id") == prop_id), None)
        assert match is not None
        assert match.get("status") == "pending_validation"

    def test_validate_twin_approve_unlocks_property(self, operator_session, client_session):
        # Pick a twin that is pending_validation
        twins = operator_session.get(f"{BASE_URL}/api/operator/twins", timeout=15).json()
        pending_twin = next((t for t in twins if t.get("status") == "pending_validation"), None)
        if not pending_twin:
            pytest.skip("no pending twin")
        prop_id = pending_twin["property_id"]
        r = operator_session.post(
            f"{BASE_URL}/api/operator/twins/{prop_id}/validate",
            json={"action": "approve", "notes": "TEST_phase6 approved"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        # Re-fetch twin
        t2 = operator_session.get(f"{BASE_URL}/api/operator/twins/{prop_id}", timeout=15).json()
        assert t2.get("status") == "approved"

    def test_validate_twin_request_revision(self, operator_session, client_session):
        # Re-request validation on any property to set up another pending twin
        props = client_session.get(f"{BASE_URL}/api/properties", timeout=10).json()
        if not props:
            pytest.skip("no properties")
        prop_id = props[0]["id"]
        client_session.post(f"{BASE_URL}/api/properties/{prop_id}/twin/request", timeout=15)
        r = operator_session.post(
            f"{BASE_URL}/api/operator/twins/{prop_id}/validate",
            json={"action": "request_revision", "notes": "TEST_phase6 needs more rooms"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        t = operator_session.get(f"{BASE_URL}/api/operator/twins/{prop_id}", timeout=15).json()
        assert t.get("status") == "needs_revision"

    def test_operator_endpoints_require_role(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/operator/twins", timeout=10)
        assert r.status_code in (401, 403)


# ============ REGRESSION SMOKE ============

class TestRegression:
    def test_auth_me_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN["email"]

    def test_properties_list_client(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_requests_list_client(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/requests", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_marketplace_public(self):
        r = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_notifications_list(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert r.status_code == 200

    def test_admin_stats(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/stats", timeout=10)
        assert r.status_code == 200
        for k in ("users", "specialists", "verified", "pending_verification"):
            assert k in r.json()
