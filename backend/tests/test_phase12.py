"""
Phase 12 backend tests: Referral tracking, Web Push (VAPID), Contact form.

Covers:
- POST /api/auth/register accepts referrer_id (and silently ignores invalid)
- GET /api/auth/referral returns stats + URL
- End-to-end referral payout (+500 tokens to sponsor, twin_unlocked, single-use)
- /api/push/vapid-public-key  (public, no auth)
- /api/push/subscribe / /api/push/unsubscribe + idempotent upsert
- /api/support/contact validation + success path
"""

import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

# Mongo direct connection (to verify persistence + flip request states fast)
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "propmanage_db")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
SPECIALIST_EMAIL = "specialist@propmanage.io"
SPECIALIST_PASS = "Spec123!"


# ---------------- helpers ----------------
def _login(session: requests.Session, email: str, password: str):
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()


def _me(session: requests.Session):
    r = session.get(f"{API}/auth/me")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module")
def sponsor():
    s = requests.Session()
    _login(s, CLIENT_EMAIL, CLIENT_PASS)
    me = _me(s)
    return {"session": s, "id": me["id"], "email": me["email"], "name": me["name"]}


@pytest.fixture(scope="module")
def specialist():
    s = requests.Session()
    _login(s, SPECIALIST_EMAIL, SPECIALIST_PASS)
    me = _me(s)
    return {"session": s, "id": me["id"], "email": me["email"], "name": me["name"]}


# ============= VAPID public key =============
class TestVapidPublicKey:
    def test_public_key_no_auth(self):
        r = requests.get(f"{API}/push/vapid-public-key")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "public_key" in data
        # URL-safe base64, ~88 chars
        assert isinstance(data["public_key"], str)
        assert data["public_key"].startswith("B")
        assert 80 <= len(data["public_key"]) <= 100


# ============= Push subscribe / unsubscribe =============
class TestPushSubscribe:
    def _sub(self, idx=0):
        return {
            "endpoint": f"https://fcm.googleapis.com/fcm/send/TEST_phase12_{idx}_{uuid.uuid4().hex[:8]}",
            "keys": {
                "p256dh": "BPx" + "A" * 84,
                "auth": "TESTauthValue123456",
            },
        }

    def test_subscribe_requires_auth(self):
        r = requests.post(f"{API}/push/subscribe", json=self._sub())
        assert r.status_code in (401, 403), r.text

    def test_subscribe_and_idempotent(self, sponsor, db):
        sub = self._sub(idx=1)
        s = sponsor["session"]
        r1 = s.post(f"{API}/push/subscribe", json=sub)
        assert r1.status_code == 200, r1.text
        assert r1.json().get("ok") is True

        # subscribing again with same endpoint should NOT create duplicate
        r2 = s.post(f"{API}/push/subscribe", json=sub)
        assert r2.status_code == 200, r2.text

        cnt = db.push_subscriptions.count_documents({"endpoint": sub["endpoint"]})
        assert cnt == 1, f"expected 1 doc per endpoint, got {cnt}"

        doc = db.push_subscriptions.find_one({"endpoint": sub["endpoint"]})
        assert doc["user_id"] == sponsor["id"]
        assert doc["keys"]["p256dh"] == sub["keys"]["p256dh"]
        assert doc["keys"]["auth"] == sub["keys"]["auth"]

        # cleanup
        r3 = s.post(f"{API}/push/unsubscribe", json=sub)
        assert r3.status_code == 200, r3.text
        assert db.push_subscriptions.count_documents({"endpoint": sub["endpoint"]}) == 0


# ============= /auth/referral stats =============
class TestReferralStats:
    def test_referral_endpoint_shape(self, sponsor):
        r = sponsor["session"].get(f"{API}/auth/referral")
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("user_id", "referred_total", "converted_total", "tokens_per_conversion", "referral_url"):
            assert key in data, f"missing {key} in {data}"
        assert data["user_id"] == sponsor["id"]
        assert data["tokens_per_conversion"] == 500
        assert data["referral_url"].endswith(f"/register?ref={sponsor['id']}")
        assert isinstance(data["referred_total"], int)
        assert isinstance(data["converted_total"], int)


# ============= Register with referrer_id (valid + invalid) =============
class TestRegisterWithReferrer:
    def test_invalid_referrer_id_silently_ignored(self, db):
        email = f"test_phase12_invalidref_{uuid.uuid4().hex[:8]}@test.io"
        r = requests.post(
            f"{API}/auth/register",
            json={
                "terms_accepted": True, "privacy_policy_accepted": True,
                "email": email,
                "password": "Pass1234!",
                "name": "Invalid Ref Test",
                "role": "client",
                "phone": "0700000001",
                "zone": "Bucuresti",
                "referrer_id": "deadbeef" * 3,  # invalid ObjectId form
            },
        )
        assert r.status_code == 200, f"register should succeed even with bad ref: {r.text}"
        # user should NOT have referrer_id stored
        doc = db.users.find_one({"email": email})
        assert doc is not None
        assert "referrer_id" not in doc or doc.get("referrer_id") is None
        # cleanup
        db.users.delete_one({"_id": doc["_id"]})

    def test_valid_referrer_id_stored(self, sponsor, db):
        email = f"test_phase12_validref_{uuid.uuid4().hex[:8]}@test.io"
        r = requests.post(
            f"{API}/auth/register",
            json={
                "terms_accepted": True, "privacy_policy_accepted": True,
                "email": email,
                "password": "Pass1234!",
                "name": "Valid Ref Test",
                "role": "client",
                "phone": "0700000002",
                "zone": "Bucuresti",
                "referrer_id": sponsor["id"],
            },
        )
        assert r.status_code == 200, r.text
        doc = db.users.find_one({"email": email})
        assert doc is not None
        assert doc.get("referrer_id") == sponsor["id"]
        assert doc.get("referral_bonus_paid") is False
        # cleanup
        db.users.delete_one({"_id": doc["_id"]})


# ============= End-to-end referral payout =============
class TestReferralEndToEnd:
    """Register a referred client → complete a request → sponsor gets +500 tokens, twin unlocked. Single-use."""

    @pytest.fixture(scope="class")
    def referred(self, sponsor, db):
        email = f"test_phase12_referred_{uuid.uuid4().hex[:8]}@test.io"
        password = "Pass1234!"
        sess = requests.Session()
        r = sess.post(
            f"{API}/auth/register",
            json={
                "terms_accepted": True, "privacy_policy_accepted": True,
                "email": email,
                "password": password,
                "name": "Referred E2E",
                "role": "client",
                "phone": "0700000003",
                "zone": "Bucuresti",
                "referrer_id": sponsor["id"],
            },
        )
        assert r.status_code == 200, r.text
        me = _me(sess)
        # give wallet some balance for escrow
        db.users.update_one({"_id": ObjectId(me["id"])}, {"$set": {"wallet_balance": 5000.0}})
        yield {"session": sess, "id": me["id"], "email": email, "password": password}
        # cleanup
        db.requests.delete_many({"client_id": me["id"]})
        db.properties.delete_many({"owner_id": me["id"]})
        db.users.delete_one({"_id": ObjectId(me["id"])})

    def _create_property_and_request(self, referred):
        s = referred["session"]
        r = s.post(
            f"{API}/properties",
            json={"name": "TEST_Phase12_Prop", "address": "Str. Test 1", "type": "apartment", "surface": 60.0, "rooms": 2},
        )
        assert r.status_code == 200, r.text
        prop = r.json()
        prop_id = prop["id"]

        r = s.post(
            f"{API}/requests",
            json={
                "property_id": prop_id,
                "category": "hvac",
                "title": "TEST_Phase12_request",
                "description": "Test description for phase 12 e2e referral",
                "priority": "normal",
                "budget_estimate": 200.0,
            },
        )
        assert r.status_code == 200, r.text
        return prop_id, r.json()["id"]

    def _complete_flow(self, referred, specialist, req_id, db):
        sp = specialist["session"]
        # specialist accepts (charges 45 RON lead fee — ensure wallet has funds)
        db.users.update_one({"_id": ObjectId(specialist["id"])}, {"$set": {"wallet_balance": 5000.0}})
        r = sp.post(f"{API}/requests/{req_id}/accept")
        assert r.status_code == 200, r.text

        # client places escrow
        cl = referred["session"]
        r = cl.post(f"{API}/requests/{req_id}/escrow", params={"amount": 100.0})
        assert r.status_code == 200, r.text

        # specialist starts + completes
        r = sp.post(f"{API}/requests/{req_id}/start")
        assert r.status_code == 200, r.text
        r = sp.post(f"{API}/requests/{req_id}/complete")
        assert r.status_code == 200, r.text

        # client confirms
        r = cl.post(f"{API}/requests/{req_id}/confirm")
        assert r.status_code == 200, r.text

    def test_first_confirm_pays_sponsor_500_tokens(self, sponsor, specialist, referred, db):
        before = db.users.find_one({"_id": ObjectId(sponsor["id"])})
        tokens_before = before.get("tokens", 0)
        tx_before = db.transactions.count_documents({"user_id": sponsor["id"], "type": "referral_bonus"})

        # Ensure sponsor has at least one property without twin unlocked to test twin activation
        any_locked = db.properties.find_one({"owner_id": sponsor["id"], "twin_unlocked": {"$ne": True}})
        if not any_locked:
            db.properties.insert_one({
                "name": "TEST_SponsorProp",
                "address": "Str. Sponsor 1",
                "type": "apartment",
                "surface": 50.0,
                "rooms": 2,
                "owner_id": sponsor["id"],
                "twin_unlocked": False,
            })
            any_locked = db.properties.find_one({"owner_id": sponsor["id"], "twin_unlocked": {"$ne": True}})

        _, req_id = self._create_property_and_request(referred)
        self._complete_flow(referred, specialist, req_id, db)
        time.sleep(0.5)

        after = db.users.find_one({"_id": ObjectId(sponsor["id"])})
        tokens_after = after.get("tokens", 0)
        assert tokens_after - tokens_before == 500, f"expected +500 tokens, got delta {tokens_after - tokens_before}"

        # referred client doc updated
        ref_doc = db.users.find_one({"_id": ObjectId(referred["id"])})
        assert ref_doc.get("referral_bonus_paid") is True

        # transaction recorded
        tx_after = db.transactions.count_documents({"user_id": sponsor["id"], "type": "referral_bonus"})
        assert tx_after == tx_before + 1
        tx = db.transactions.find_one(
            {"user_id": sponsor["id"], "type": "referral_bonus"},
            sort=[("created_at", -1)],
        )
        assert tx["amount"] == 500
        assert tx.get("currency") == "tokens"
        assert tx.get("referred_user_id") == referred["id"]

        # twin unlocked on previously-locked property
        twin = db.properties.find_one({"_id": any_locked["_id"]})
        assert twin.get("twin_unlocked") is True
        assert twin.get("twin_unlocked_via") == "referral"

        # cleanup our seeded TEST_SponsorProp (only if we created it)
        db.properties.delete_many({"owner_id": sponsor["id"], "name": "TEST_SponsorProp"})

    def test_second_confirm_does_not_pay_again(self, sponsor, specialist, referred, db):
        before = db.users.find_one({"_id": ObjectId(sponsor["id"])})
        tokens_before = before.get("tokens", 0)
        tx_before = db.transactions.count_documents({"user_id": sponsor["id"], "type": "referral_bonus"})

        _, req_id = self._create_property_and_request(referred)
        self._complete_flow(referred, specialist, req_id, db)
        time.sleep(0.3)

        after = db.users.find_one({"_id": ObjectId(sponsor["id"])})
        tokens_after = after.get("tokens", 0)
        # client +100 for confirmation goes to client, not sponsor; sponsor should be UNCHANGED
        assert tokens_after == tokens_before, f"sponsor tokens changed on 2nd confirm: {tokens_before} -> {tokens_after}"
        tx_after = db.transactions.count_documents({"user_id": sponsor["id"], "type": "referral_bonus"})
        assert tx_after == tx_before, "second referral_bonus transaction should NOT be created"


# ============= /support/contact =============
class TestContactForm:
    def test_requires_auth(self):
        r = requests.post(f"{API}/support/contact", json={"subject": "Hello", "message": "Test message body"})
        assert r.status_code in (401, 403)

    def test_validates_min_length(self, sponsor):
        s = sponsor["session"]
        r = s.post(f"{API}/support/contact", json={"subject": "A", "message": "Test message body ok"})
        assert r.status_code == 422
        r = s.post(f"{API}/support/contact", json={"subject": "Subject OK", "message": "x"})
        assert r.status_code == 422

    def test_success(self, sponsor):
        r = sponsor["session"].post(
            f"{API}/support/contact",
            json={"subject": "Test ticket from phase12", "message": "This is a real-looking contact ticket message."},
        )
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True


# ============= Smoke regression =============
class TestRegressionSmoke:
    def test_demo_logins_work(self):
        for email, pw in [(CLIENT_EMAIL, CLIENT_PASS), (SPECIALIST_EMAIL, SPECIALIST_PASS),
                          ("admin@propmanage.io", OWNER_ADMIN_PASSWORD), ("operator@propmanage.io", "Op123!")]:
            s = requests.Session()
            r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
            assert r.status_code == 200, f"{email} login: {r.status_code} {r.text}"

    def test_properties_list_for_client(self, sponsor):
        r = sponsor["session"].get(f"{API}/properties")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)

    def test_requests_list(self, sponsor):
        r = sponsor["session"].get(f"{API}/requests")
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)
