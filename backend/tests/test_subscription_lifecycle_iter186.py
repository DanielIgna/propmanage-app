"""
Task 4 iter186 — Subscription lifecycle handling tests.

Focus:
- GET /api/me/entitlements returns lifecycle + last_subscription + notice
- Lifecycle states: never_subscribed | active | cancelled_grace | expired | admin_bypass
- POST /api/me/subscription/cancel — self-cancel keeps access until expires_at
- Cancel is idempotent (already cancelled → snapshot, no 500)
- Cancel on user without hh_subscriptions → 404
- Regression: expired user data (properties, documents, technical-record) NOT lost
- Regression: paid features (house-health/documents, digital-twin/projects) → 402 for expired user
- Regression Tasks 1-3 remain green
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "propmanage_db")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


def _register_fresh_user(prefix="lifecycle"):
    email = f"{prefix}{int(time.time()*1000)}{uuid.uuid4().hex[:4]}@example.com"
    s = requests.Session()
    payload = {
        "email": email,
        "password": "TestPass123!",
        "name": f"Lifecycle Test {prefix}",
        "role": "client",
        "terms_accepted": True,
        "privacy_policy_accepted": True,
    }
    r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me.status_code != 200:
        s = _login(email, "TestPass123!")
    return email, s


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    # Cleanup: remove test users + their subs + their properties
    try:
        regex = r"^(exp|lifecycle|free)\d+.*@example\.com$"
        users = list(db.users.find({"email": {"$regex": regex}}, {"_id": 1}))
        ids = [str(u["_id"]) for u in users]
        if ids:
            db.hh_subscriptions.delete_many({"user_id": {"$in": ids}})
            db.properties.delete_many({"owner_id": {"$in": ids}})
            db.property_documents.delete_many({"owner_id": {"$in": ids}})
        db.users.delete_many({"email": {"$regex": regex}})
    finally:
        client.close()


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture
def fresh_user(mongo):
    email, s = _register_fresh_user()
    u = mongo.users.find_one({"email": email})
    uid = str(u["_id"])
    return {"email": email, "session": s, "user_id": uid}


def _upsert_sub(mongo, uid, plan="basic", status="active", days=15):
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(days=days)).isoformat()
    mongo.hh_subscriptions.update_one(
        {"user_id": uid},
        {"$set": {
            "user_id": uid,
            "plan": plan,
            "plan_slug": plan,
            "status": status,
            "expires_at": expires,
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }},
        upsert=True,
    )
    return expires


def _age_sub_to_expired(mongo, uid, status="cancelled"):
    """Force expires_at into the past — user will be resolved as expired."""
    now = datetime.now(timezone.utc)
    past = (now - timedelta(days=1)).isoformat()
    mongo.hh_subscriptions.update_one(
        {"user_id": uid},
        {"$set": {
            "expires_at": past,
            "status": status,
            "updated_at": now.isoformat(),
        }},
    )


# ============================================================================
# 1. Existing premium client → lifecycle='active', notice=null
# ============================================================================
def test_client_premium_active_lifecycle(client_s):
    r = client_s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "CLIENT_PREMIUM", body
    assert body["lifecycle"] == "active", body
    assert body["notice"] is None, body
    assert body.get("subscription") is not None
    assert body["subscription"].get("status") == "active"


# ============================================================================
# 2. Admin → lifecycle='admin_bypass'
# ============================================================================
def test_admin_lifecycle_bypass(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lifecycle"] == "admin_bypass", body
    assert body["notice"] is None, body
    assert body["is_admin_bypass"] is True


# ============================================================================
# 3. Fresh FREE user → lifecycle='never_subscribed', last_subscription=null
# ============================================================================
def test_never_subscribed_lifecycle(fresh_user):
    r = fresh_user["session"].get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "FREE", body
    assert body["lifecycle"] == "never_subscribed", body
    assert body["last_subscription"] is None, body
    assert body["notice"] is None, body


# ============================================================================
# 4. Simulated ACTIVE BASIC → lifecycle='active', tier=CLIENT_BASIC, notice=null
# ============================================================================
def test_simulated_active_basic(fresh_user, mongo):
    uid = fresh_user["user_id"]
    _upsert_sub(mongo, uid, plan="basic", status="active", days=15)
    r = fresh_user["session"].get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "CLIENT_BASIC", body
    assert body["lifecycle"] == "active", body
    assert body["notice"] is None, body
    assert "house_health_basic" in body["features"], body


# ============================================================================
# 5. POST /me/subscription/cancel — cancelled_grace lifecycle, access retained
# ============================================================================
def test_self_cancel_moves_to_cancelled_grace(fresh_user, mongo):
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    _upsert_sub(mongo, uid, plan="basic", status="active", days=15)

    r = s.post(f"{BASE_URL}/api/me/subscription/cancel", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lifecycle"] == "cancelled_grace", body
    assert body["tier"] == "CLIENT_BASIC", body  # access retained
    assert "house_health_basic" in body["features"], body
    assert body["notice"] is not None, body
    assert body["notice"]["kind"] == "subscription_cancelled", body["notice"]
    assert body["notice"]["cta_href"] == "/pricing", body["notice"]

    # Verify DB — cancelled_at, cancelled_by set, expires_at unchanged
    doc = mongo.hh_subscriptions.find_one({"user_id": uid})
    assert doc["status"] == "cancelled", doc
    assert doc.get("cancelled_at") is not None
    assert doc.get("cancelled_by") == uid


# ============================================================================
# 6. EXPIRED → lifecycle='expired', tier=FREE, notice.subscription_expired
# ============================================================================
def test_expired_lifecycle_free_tier_with_notice(fresh_user, mongo):
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    _upsert_sub(mongo, uid, plan="basic", status="active", days=15)
    _age_sub_to_expired(mongo, uid, status="cancelled")

    r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lifecycle"] == "expired", body
    assert body["tier"] == "FREE", body
    # FREE features only
    assert "house_health_basic" not in body["features"], body
    assert "property_create" in body["features"], body
    assert "property_technical_record" in body["features"], body
    # last_subscription is populated
    assert body["last_subscription"] is not None, body
    assert body["last_subscription"]["plan"] == "basic"
    assert body["last_subscription"]["status"] == "cancelled"
    assert body["last_subscription"]["expires_at"] is not None
    # notice
    assert body["notice"] is not None, body
    assert body["notice"]["kind"] == "subscription_expired", body["notice"]
    assert body["notice"]["cta_href"] == "/pricing", body["notice"]


# ============================================================================
# 7. REGRESSION — expired user gets 402 on house-health/documents (paid feature)
# ============================================================================
def test_expired_user_402_on_house_health_documents(fresh_user, mongo):
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    _upsert_sub(mongo, uid, plan="basic", status="active", days=15)
    _age_sub_to_expired(mongo, uid, status="cancelled")

    r = s.post(
        f"{BASE_URL}/api/house-health/documents",
        data={
            "twin_project_id": "any-id",
            "category": "revizie",
            "external_link": "https://ex.com/x",
            "external_type": "link",
        },
        timeout=15,
    )
    assert r.status_code == 402, f"expected 402, got {r.status_code}: {r.text}"


# ============================================================================
# 8. REGRESSION — expired user: INGEST allowed (bring/store model), ADVANCED (pins) 402
#    (P1 decizia Fondator #4 — upload/stocare NU e blocat; exploatarea avansată rămâne PREMIUM)
# ============================================================================
def test_expired_user_ingest_ok_advanced_402_digital_twin(fresh_user, mongo):
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    _upsert_sub(mongo, uid, plan="pro", status="active", days=15)
    _age_sub_to_expired(mongo, uid, status="cancelled")

    # INGEST: create own project still allowed after downgrade
    r = s.post(
        f"{BASE_URL}/api/digital-twin/projects",
        json={"name": "TEST_expired_dt_iter186"},
        timeout=15,
    )
    assert r.status_code in (200, 201), f"ingest should be allowed: {r.status_code}: {r.text}"
    pid = r.json().get("id")
    # ADVANCED: pins still gated 402 for downgraded (FREE) user
    rp = s.post(
        f"{BASE_URL}/api/digital-twin/projects/{pid or 'nonexistent-id'}/pins",
        json={"position": {"x": 0, "y": 0, "z": 0}, "title": "abc"},
        timeout=10,
    )
    assert rp.status_code == 402, rp.text
    if pid:
        s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", timeout=10)


# ============================================================================
# 9. REGRESSION — expired user's property GET endpoints still work
# ============================================================================
def test_expired_user_property_data_preserved(fresh_user, mongo):
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    # Create property while user is on ACTIVE plan (basic)
    _upsert_sub(mongo, uid, plan="basic", status="active", days=15)
    prop_payload = {
        "name": "TEST_prop_lifecycle_iter186",
        "address": "Str. Test 1, Bucuresti",
        "type": "apartament",
        "surface": 65.0,
        "rooms": 3,
    }
    rc = s.post(f"{BASE_URL}/api/properties", json=prop_payload, timeout=15)
    assert rc.status_code in (200, 201), rc.text
    prop_id = rc.json()["id"]

    # Age subscription to expired
    _age_sub_to_expired(mongo, uid, status="cancelled")

    # Verify lifecycle = expired
    r_ent = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r_ent.json()["lifecycle"] == "expired"

    # GET property should still work (data preserved)
    r1 = s.get(f"{BASE_URL}/api/properties/{prop_id}", timeout=15)
    assert r1.status_code == 200, f"GET property failed: {r1.status_code} {r1.text}"
    assert r1.json()["id"] == prop_id

    # GET documents list should still work
    r2 = s.get(f"{BASE_URL}/api/properties/{prop_id}/documents", timeout=15)
    assert r2.status_code == 200, f"GET documents failed: {r2.status_code} {r2.text}"

    # GET technical-record should still work
    r3 = s.get(f"{BASE_URL}/api/properties/{prop_id}/technical-record", timeout=15)
    assert r3.status_code == 200, f"GET technical-record failed: {r3.status_code} {r3.text}"


# ============================================================================
# 10. Cancel idempotent — already cancelled/expired returns snapshot, no 500
# ============================================================================
def test_cancel_idempotent_on_cancelled(fresh_user, mongo):
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    _upsert_sub(mongo, uid, plan="basic", status="active", days=15)

    r1 = s.post(f"{BASE_URL}/api/me/subscription/cancel", timeout=15)
    assert r1.status_code == 200, r1.text
    assert r1.json()["lifecycle"] == "cancelled_grace"

    # Second call — should NOT return 500 or 4xx
    r2 = s.post(f"{BASE_URL}/api/me/subscription/cancel", timeout=15)
    assert r2.status_code == 200, f"expected 200 idempotent, got {r2.status_code}: {r2.text}"
    body = r2.json()
    assert body["lifecycle"] == "cancelled_grace", body

    # Also idempotent when already expired
    _age_sub_to_expired(mongo, uid, status="cancelled")
    r3 = s.post(f"{BASE_URL}/api/me/subscription/cancel", timeout=15)
    assert r3.status_code == 200, r3.text
    assert r3.json()["lifecycle"] == "expired"


# ============================================================================
# 11. Cancel returns 404 for user with no hh_subscriptions doc
# ============================================================================
def test_cancel_returns_404_when_no_subscription(fresh_user):
    r = fresh_user["session"].post(f"{BASE_URL}/api/me/subscription/cancel", timeout=15)
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"


# ============================================================================
# 12. REGRESSION Task 1 — /api/me/entitlements shape includes core fields
# ============================================================================
def test_regression_entitlements_shape(client_s):
    r = client_s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200
    body = r.json()
    for k in ("user_id", "role", "tier", "tier_label", "features",
              "is_admin_bypass", "lifecycle", "notice"):
        assert k in body, f"missing {k}: {body}"


# ============================================================================
# 13. REGRESSION Task 2 — Basic checkout still works for FREE user
# ============================================================================
def test_regression_basic_checkout(fresh_user, mongo):
    # ensure no subscription
    mongo.hh_subscriptions.delete_many({"user_id": fresh_user["user_id"]})
    r = fresh_user["session"].post(
        f"{BASE_URL}/api/house-health/checkout-session",
        json={"plan_slug": "basic", "origin_url": BASE_URL},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("session_id", "").startswith("cs_")


# ============================================================================
# 14. cancelled_grace with future expires_at → still has feature access
# ============================================================================
def test_cancelled_grace_status_directly_gives_access(fresh_user, mongo):
    """Set status='cancelled' directly with expires_at in future — should be cancelled_grace."""
    uid = fresh_user["user_id"]
    s = fresh_user["session"]
    _upsert_sub(mongo, uid, plan="basic", status="cancelled", days=10)

    r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["lifecycle"] == "cancelled_grace", body
    assert body["tier"] == "CLIENT_BASIC", body
    assert "house_health_basic" in body["features"], body
    assert body["notice"]["kind"] == "subscription_cancelled"
