"""Phase 4 backend tests: Property CRUD, Specialist Public Profile, Photo Upload,
Review Flow, Notifications + Email Log fallback."""
import os
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Read from frontend env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

API = f"{BASE_URL}/api"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
SPEC2 = {"email": "specialist2@propmanage.io", "password": "Spec123!"}


# ===== Fixtures =====
def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return s, r.json()


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def specialist_session():
    return _login(SPEC)


@pytest.fixture(scope="module")
def specialist2_session():
    return _login(SPEC2)


@pytest.fixture(scope="module")
def db():
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url:
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith("MONGO_URL="):
                    mongo_url = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("DB_NAME="):
                    db_name = line.split("=", 1)[1].strip().strip('"')
    return MongoClient(mongo_url)[db_name]


# ===== Property CRUD (multi-property) =====
class TestPropertyCRUD:
    def test_create_additional_property(self, client_session):
        s, _ = client_session
        payload = {
            "name": "TEST_Phase4 Villa",
            "address": "Str. Test 100, București",
            "type": "villa",
            "surface": 180.0,
            "rooms": 5,
        }
        r = s.post(f"{API}/properties", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        assert data["name"] == payload["name"]
        assert data["surface"] == 180.0
        assert data["rooms"] == 5
        # Persist for downstream tests
        pytest.prop_id = data["id"]

        # Verify via GET
        g = s.get(f"{API}/properties/{data['id']}", timeout=15)
        assert g.status_code == 200
        assert g.json()["name"] == payload["name"]

    def test_update_own_property(self, client_session):
        s, _ = client_session
        r = s.put(f"{API}/properties/{pytest.prop_id}",
                  json={"name": "TEST_Phase4 Villa Updated", "rooms": 6}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["name"] == "TEST_Phase4 Villa Updated"
        assert data["rooms"] == 6
        # Verify persistence
        g = s.get(f"{API}/properties/{pytest.prop_id}", timeout=15).json()
        assert g["name"] == "TEST_Phase4 Villa Updated"
        assert g["rooms"] == 6

    def test_update_property_not_owned_returns_404(self, specialist_session, client_session, db):
        # Specialist is not 'client' role -> require_role("client") returns 403 first.
        # Use second client account: register a temp client, try to update first client's property.
        sess = requests.Session()
        reg = sess.post(f"{API}/auth/register", json={
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "email": "TEST_phase4_otherclient@propmanage.io",
            "password": "Test123!",
            "name": "Other Client",
            "role": "client",
        }, timeout=15)
        # Either created (200) or already exists (400) -> then login
        if reg.status_code != 200:
            sess = requests.Session()
            lr = sess.post(f"{API}/auth/login", json={
                "email": "TEST_phase4_otherclient@propmanage.io",
                "password": "Test123!",
            }, timeout=15)
            assert lr.status_code == 200, lr.text
        r = sess.put(f"{API}/properties/{pytest.prop_id}",
                     json={"name": "Hacked"}, timeout=15)
        assert r.status_code == 404, f"Expected 404 for non-owner, got {r.status_code}: {r.text}"

    def test_delete_property_blocked_with_active_request(self, client_session, db):
        s, me = client_session
        # Create a fresh property, attach a request to it, then attempt delete -> 400
        cp = s.post(f"{API}/properties", json={
            "name": "TEST_DeleteBlocked", "address": "Str. X",
            "type": "apartment", "surface": 50.0, "rooms": 2,
        }, timeout=15)
        assert cp.status_code == 200
        prop_id = cp.json()["id"]

        # Create open request first
        rq = s.post(f"{API}/requests", json={
            "property_id": prop_id,
            "category": "electric",
            "title": "TEST_Phase4 blocker request",
            "description": "active req",
            "priority": "normal",
            "budget_estimate": 100.0,
        }, timeout=15)
        assert rq.status_code == 200, rq.text
        req_id = rq.json()["id"]

        # 'open' status is NOT in delete-blocking list per server code: {"assigned", "in_progress", "completed"}
        # We need to push the request to 'assigned'. Have specialist accept it.
        sspec, _ = _login(SPEC)
        # Ensure wallet has 45 RON
        acc = sspec.post(f"{API}/requests/{req_id}/accept", timeout=15)
        assert acc.status_code == 200, f"Accept failed: {acc.text}"

        # Now attempt delete -> 400
        d = s.delete(f"{API}/properties/{prop_id}", timeout=15)
        assert d.status_code == 400, f"Expected 400 with active req, got {d.status_code}: {d.text}"
        assert "active" in d.text.lower() or "Cannot delete" in d.text

        # Persist ids for downstream review flow
        pytest.blocked_prop_id = prop_id
        pytest.blocker_req_id = req_id

    def test_delete_property_success_when_no_active_requests(self, client_session):
        s, _ = client_session
        # Create + delete with no requests at all
        cp = s.post(f"{API}/properties", json={
            "name": "TEST_DeleteMe", "address": "Str. Y",
            "type": "apartment", "surface": 40.0, "rooms": 1,
        }, timeout=15)
        assert cp.status_code == 200
        pid = cp.json()["id"]
        d = s.delete(f"{API}/properties/{pid}", timeout=15)
        assert d.status_code == 200, d.text
        # Verify gone
        g = s.get(f"{API}/properties/{pid}", timeout=15)
        assert g.status_code == 404


# ===== Photos in requests =====
class TestPhotoUpload:
    def test_create_request_with_photos(self, client_session, db):
        s, _ = client_session
        # Need a clean property (the test villa is fine)
        # Use the existing pytest.prop_id from TestPropertyCRUD or fetch first prop
        if not hasattr(pytest, "prop_id"):
            props = s.get(f"{API}/properties", timeout=15).json()
            pytest.prop_id = props[0]["id"]
        b64_1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        b64_2 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAAAAAD//gA7Q1JFQVRPUjogZ2QtanBlZw=="
        r = s.post(f"{API}/requests", json={
            "property_id": pytest.prop_id,
            "category": "plumbing",
            "title": "TEST_Phase4 with photos",
            "description": "leak",
            "priority": "normal",
            "budget_estimate": 150.0,
            "photos": [b64_1, b64_2],
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("photos") == [b64_1, b64_2], "photos must be stored in request"
        # Verify persistence in DB
        from bson import ObjectId
        doc = db.requests.find_one({"_id": ObjectId(data["id"])})
        assert doc is not None
        assert doc.get("photos") == [b64_1, b64_2]


# ===== Specialist Public Profile =====
class TestSpecialistProfile:
    def test_public_profile_no_auth(self, db):
        spec = db.users.find_one({"email": "specialist@propmanage.io"})
        spec_id = str(spec["_id"])
        # No auth (fresh session)
        r = requests.get(f"{API}/specialists/{spec_id}/profile", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["id"] == spec_id
        assert data["name"] == "Mihai Ionescu"
        assert data["specialty"] == "hvac"
        assert "rating" in data and isinstance(data["rating"], (int, float))
        assert "reviews_count" in data
        assert "completed_jobs" in data
        assert isinstance(data["specialties"], list)
        assert isinstance(data["reviews"], list)
        # Should NOT leak password
        assert "password_hash" not in data

    def test_profile_404_for_invalid_objectid(self):
        r = requests.get(f"{API}/specialists/not-an-objectid/profile", timeout=15)
        assert r.status_code == 404

    def test_profile_404_for_non_specialist_user(self, db):
        client_user = db.users.find_one({"email": "client@propmanage.io"})
        r = requests.get(f"{API}/specialists/{str(client_user['_id'])}/profile", timeout=15)
        assert r.status_code == 404


# ===== Review Flow =====
class TestReviewFlow:
    def test_full_review_flow_awards_tokens_and_updates_rating(self, client_session, db):
        s, me_client = client_session
        # Use the blocker_req_id from TestPropertyCRUD which is currently 'assigned'
        # Drive to completed/confirmed: start, complete, escrow, confirm, review
        req_id = pytest.blocker_req_id

        sspec, _ = _login(SPEC)
        st = sspec.post(f"{API}/requests/{req_id}/start", timeout=15)
        assert st.status_code == 200, st.text

        # Client puts escrow
        es = s.post(f"{API}/requests/{req_id}/escrow?amount=100", timeout=15)
        assert es.status_code == 200, es.text

        co = sspec.post(f"{API}/requests/{req_id}/complete", timeout=15)
        assert co.status_code == 200, co.text

        cf = s.post(f"{API}/requests/{req_id}/confirm", timeout=15)
        assert cf.status_code == 200, cf.text

        # Capture token balance before review
        me = s.get(f"{API}/auth/me", timeout=15).json()
        tokens_before = me.get("tokens", 0)

        # Capture specialist rating before
        spec_doc = db.users.find_one({"email": "specialist@propmanage.io"})
        rating_before = spec_doc.get("rating") or 5.0
        rev_count_before = spec_doc.get("reviews_count", 0)

        rv = s.post(f"{API}/requests/{req_id}/review", json={
            "job_id": req_id, "rating": 5, "comment": "TEST_excellent",
        }, timeout=15)
        assert rv.status_code == 200, rv.text
        result = rv.json()
        assert "new_rating" in result

        # Verify +20 tokens
        me_after = s.get(f"{API}/auth/me", timeout=15).json()
        assert me_after["tokens"] == tokens_before + 20, \
            f"Expected +20 tokens, got {tokens_before} -> {me_after['tokens']}"

        # Verify rating updated
        spec_doc_after = db.users.find_one({"email": "specialist@propmanage.io"})
        assert spec_doc_after["reviews_count"] == rev_count_before + 1
        # Review was saved
        rev = db.reviews.find_one({"request_id": req_id, "rating": 5, "comment": "TEST_excellent"})
        assert rev is not None


# ===== Notifications =====
class TestNotifications:
    def test_list_notifications_returns_newest_first(self, specialist_session):
        s, _ = specialist_session
        r = s.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 200, r.text
        notifs = r.json()
        assert isinstance(notifs, list)
        # Should have at least one due to "lead" events from earlier request creation
        assert len(notifs) > 0, "specialist should have notifications from lead events"
        # Sorted newest-first
        timestamps = [n["created_at"] for n in notifs]
        assert timestamps == sorted(timestamps, reverse=True), "notifications not sorted desc"
        # Each notif has required keys
        n = notifs[0]
        for key in ("id", "title", "message", "type", "read", "created_at"):
            assert key in n, f"missing {key} in notification"

    def test_mark_notification_read(self, specialist_session, db):
        s, me = specialist_session
        notifs = s.get(f"{API}/notifications", timeout=15).json()
        unread = next((n for n in notifs if not n.get("read")), None)
        if not unread:
            pytest.skip("no unread notification to mark")
        r = s.post(f"{API}/notifications/{unread['id']}/read", timeout=15)
        assert r.status_code == 200, r.text
        # Verify persisted
        from bson import ObjectId
        doc = db.notifications.find_one({"_id": ObjectId(unread["id"])})
        assert doc and doc.get("read") is True

    def test_notification_created_on_request_creation(self, client_session, db):
        """Verify notify() fires for specialists on new request"""
        s, _ = client_session
        props = s.get(f"{API}/properties", timeout=15).json()
        prop_id = props[0]["id"]

        # Count specialist notifs before
        spec = db.users.find_one({"email": "specialist@propmanage.io"})
        spec_id = str(spec["_id"])
        before = db.notifications.count_documents({"user_id": spec_id, "type": "lead"})

        rq = s.post(f"{API}/requests", json={
            "property_id": prop_id,
            "category": "hvac",  # spec1 is hvac
            "title": "TEST_Phase4 notify hvac",
            "description": "test",
            "priority": "normal",
            "budget_estimate": 200.0,
        }, timeout=15)
        assert rq.status_code == 200

        after = db.notifications.count_documents({"user_id": spec_id, "type": "lead"})
        assert after > before, f"Expected new lead notification for hvac specialist (was {before}, now {after})"

    def test_notification_created_on_accept_and_complete(self, client_session, db):
        s, me_client = client_session
        # Build a fresh request, accept, complete -> check 'assignment' and 'completion' notifs for client
        props = s.get(f"{API}/properties", timeout=15).json()
        prop_id = props[0]["id"]
        rq = s.post(f"{API}/requests", json={
            "property_id": prop_id, "category": "hvac",
            "title": "TEST_Phase4 notif chain", "description": "x",
            "priority": "normal", "budget_estimate": 100.0,
        }, timeout=15)
        req_id = rq.json()["id"]
        client_id = me_client["id"]

        sspec, _ = _login(SPEC)
        sspec.post(f"{API}/requests/{req_id}/accept", timeout=15)
        # Expect 'assignment' notif for client
        assert db.notifications.count_documents(
            {"user_id": client_id, "type": "assignment", "title": {"$regex": "Specialist alocat"}}
        ) > 0

        sspec.post(f"{API}/requests/{req_id}/start", timeout=15)
        sspec.post(f"{API}/requests/{req_id}/complete", timeout=15)
        # Expect 'completion' notif for client
        assert db.notifications.count_documents(
            {"user_id": client_id, "type": "completion"}
        ) > 0

        # Escrow + confirm -> 'payment' notif for specialist
        s.post(f"{API}/requests/{req_id}/escrow?amount=100", timeout=15)
        s.post(f"{API}/requests/{req_id}/confirm", timeout=15)
        spec = db.users.find_one({"email": "specialist@propmanage.io"})
        assert db.notifications.count_documents(
            {"user_id": str(spec["_id"]), "type": "payment"}
        ) > 0


# ===== Email log fallback =====
class TestEmailLog:
    def test_email_log_demo_entry_created(self, client_session, db):
        """When SENDGRID_API_KEY not set, every notify() should also add to db.email_log with demo:true"""
        # Trigger a notification by creating a request (specialists get notified -> emails logged)
        before = db.email_log.count_documents({"demo": True})
        s, _ = client_session
        props = s.get(f"{API}/properties", timeout=15).json()
        prop_id = props[0]["id"]
        rq = s.post(f"{API}/requests", json={
            "property_id": prop_id,
            "category": "plumbing",
            "title": "TEST_Phase4 email log",
            "description": "x",
            "priority": "normal",
            "budget_estimate": 50.0,
        }, timeout=15)
        assert rq.status_code == 200
        # Allow a tiny moment for awaits to flush
        import time; time.sleep(0.5)
        after = db.email_log.count_documents({"demo": True})
        assert after > before, f"Expected new email_log demo entry (was {before}, now {after})"

        last = db.email_log.find({"demo": True}).sort("sent_at", -1).limit(1).next()
        assert last.get("to")
        assert last.get("subject", "").startswith("PropManage:")
        assert "<h2>" in last.get("body", "")


# ===== Regression smoke =====
class TestRegression:
    def test_login_me(self, client_session):
        s, me = client_session
        assert me["email"] == CLIENT["email"]
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == CLIENT["email"]

    def test_properties_list(self, client_session):
        s, _ = client_session
        r = s.get(f"{API}/properties", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_requests_list(self, client_session):
        s, _ = client_session
        r = s.get(f"{API}/requests", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_specialists_list(self):
        r = requests.get(f"{API}/specialists", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
