"""
Task 3 iter185 — Digital Twin Advanced entitlement gate tests.

Focus:
- F_DIGITAL_TWIN_ADVANCED relocated from CLIENT_PREMIUM to CLIENT_PRO (Premium inherits)
- /api/digital-twin/subscription reports tier + tier_label + cta_href='/pricing'
- Gate returns 402 (Payment Required) semantic instead of 403
- Legacy fallback digital_twin_pro flag still works
- Regression Task 1 + Task 2 (house_health_basic, house_health_advanced, /pricing plans)
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

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


def _register_free_user():
    email = f"free{int(time.time()*1000)}{uuid.uuid4().hex[:4]}@example.com"
    s = requests.Session()
    payload = {
        "email": email,
        "password": "FreePass123!",
        "name": "Free DT Test User",
        "role": "client",
        "terms_accepted": True,
        "privacy_policy_accepted": True,
    }
    r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me.status_code != 200:
        s = _login(email, "FreePass123!")
    return email, s


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    try:
        emails = list(db.users.find({"email": {"$regex": r"^free\d+.*@example\.com$"}}, {"_id": 1}))
        ids = [str(u["_id"]) for u in emails]
        db.users.delete_many({"email": {"$regex": r"^free\d+.*@example\.com$"}})
        if ids:
            db.hh_subscriptions.delete_many({"user_id": {"$in": ids}})
    finally:
        client.close()


@pytest.fixture(scope="module")
def free_user(mongo):
    email, s = _register_free_user()
    u = mongo.users.find_one({"email": email})
    uid = str(u["_id"])
    yield {"email": email, "session": s, "user_id": uid}


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


def _set_subscription(mongo, uid, plan):
    now = datetime.now(timezone.utc)
    mongo.hh_subscriptions.update_one(
        {"user_id": uid},
        {"$set": {
            "user_id": uid,
            "plan": plan,
            "plan_slug": plan,
            "status": "active",
            "expires_at": (now + timedelta(days=30)).isoformat(),
            "started_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }},
        upsert=True,
    )


def _clear_subscription(mongo, uid):
    mongo.hh_subscriptions.delete_many({"user_id": uid})


# ============================================================================
# 1. Client Premium — features include digital_twin_advanced (PREMIUM-only)
# ============================================================================
def test_premium_client_has_digital_twin_advanced_via_inheritance(client_s):
    r = client_s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "CLIENT_PREMIUM", body
    assert "digital_twin_advanced" in body["features"], body["features"]
    # Regression Task 1 + 2 — both HH features still present
    assert "house_health_basic" in body["features"], body["features"]
    assert "house_health_advanced" in body["features"], body["features"]


# ============================================================================
# 2. /digital-twin/subscription for premium → active + entitled + tier + cta
# ============================================================================
def test_dt_subscription_premium(client_s):
    r = client_s.get(f"{BASE_URL}/api/digital-twin/subscription", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active"] is True
    assert body["reason"] == "entitled"
    assert body["tier"] == "CLIENT_PREMIUM"
    assert body["required_feature"] == "digital_twin_advanced"
    assert body["cta_href"] == "/pricing"


# ============================================================================
# 3. POST /digital-twin/projects for premium — must NOT return 402
# ============================================================================
def test_dt_create_project_premium_not_402(client_s):
    r = client_s.post(
        f"{BASE_URL}/api/digital-twin/projects",
        json={"name": "TEST_dt_premium_iter185", "description": "regression check"},
        timeout=20,
    )
    assert r.status_code != 402, r.text
    # Cleanup if created
    if r.status_code in (200, 201):
        pid = r.json().get("id")
        if pid:
            client_s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", timeout=10)


# ============================================================================
# 4. Admin bypass on /digital-twin/subscription
# ============================================================================
def test_dt_subscription_admin_bypass(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/digital-twin/subscription", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active"] is True
    assert body["reason"] == "role_bypass"


# ============================================================================
# 5. FREE user entitlements — no digital_twin_advanced
# ============================================================================
def test_free_user_entitlements(free_user):
    r = free_user["session"].get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tier"] == "FREE", body
    assert "digital_twin_advanced" not in body["features"], body["features"]
    assert "house_health_basic" not in body["features"], body["features"]


# ============================================================================
# 6. /digital-twin/subscription for FREE → inactive + Gratuit + cta
# ============================================================================
def test_dt_subscription_free(free_user):
    r = free_user["session"].get(f"{BASE_URL}/api/digital-twin/subscription", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active"] is False
    assert body["reason"] == "inactive"
    assert body["tier"] == "FREE"
    assert body["tier_label"] == "Gratuit"
    assert body["cta_href"] == "/pricing"


# ============================================================================
# 7. FREE user CAN ingest (bring/store own model) — decizia Fondator #4 (upload NU e blocat)
# ============================================================================
def test_free_user_can_create_project_ingest(free_user):
    r = free_user["session"].post(
        f"{BASE_URL}/api/digital-twin/projects",
        json={"name": "TEST_free_ingest_iter185"},
        timeout=15,
    )
    assert r.status_code in (200, 201), f"ingest should be allowed (decizia #4): {r.status_code} {r.text}"
    pid = r.json().get("id")
    if pid:
        free_user["session"].delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", timeout=10)


# ============================================================================
# 8. FREE user: INGEST allowed (project patch/delete), ADVANCED (pins) still 402
# ============================================================================
def test_free_user_advanced_gated_ingest_allowed(free_user):
    s = free_user["session"]
    # INGEST: patch/delete nonexistent project → NOT 402 (entitlement not required; 404 not-found)
    r = s.patch(f"{BASE_URL}/api/digital-twin/projects/nonexistent-id", json={"name": "XX"}, timeout=10)
    assert r.status_code != 402, r.status_code
    r = s.delete(f"{BASE_URL}/api/digital-twin/projects/nonexistent-id", timeout=10)
    assert r.status_code != 402, r.status_code
    # ADVANCED: pins still require PREMIUM → 402
    r = s.post(
        f"{BASE_URL}/api/digital-twin/projects/nonexistent-id/pins",
        json={"position": {"x": 0, "y": 0, "z": 0}, "title": "abc"},
        timeout=10,
    )
    assert r.status_code == 402, r.status_code
    # PATCH pin
    r = s.patch(f"{BASE_URL}/api/digital-twin/pins/nonexistent-pin", json={"status": "open"}, timeout=10)
    assert r.status_code == 402, r.status_code


# ============================================================================
# 9. Simulate PRO user — Digital Twin is PREMIUM-only → PRO must NOT have it (402)
# ============================================================================
def test_pro_user_gets_digital_twin_advanced(free_user, mongo):
    uid = free_user["user_id"]
    s = free_user["session"]
    _set_subscription(mongo, uid, "pro")
    time.sleep(1.0)
    try:
        r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["tier"] == "CLIENT_PRO", body
        # Digital Twin este PREMIUM-only — PRO NU îl are
        assert "digital_twin_advanced" not in body["features"], body
        assert "house_health_advanced" in body["features"], body

        # INGEST: create project allowed pentru orice user autentificat (decizia #4)
        r2 = s.post(
            f"{BASE_URL}/api/digital-twin/projects",
            json={"name": "TEST_pro_iter185"},
            timeout=15,
        )
        assert r2.status_code != 402, r2.text
        pid = r2.json().get("id") if r2.status_code in (200, 201) else None
        # ADVANCED: Digital Twin necesită PREMIUM — PRO NU are pins → 402
        rp = s.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid or 'nonexistent-id'}/pins",
            json={"position": {"x": 0, "y": 0, "z": 0}, "title": "abc"},
            timeout=10,
        )
        assert rp.status_code == 402, rp.text
        if pid:
            s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", timeout=10)
    finally:
        _clear_subscription(mongo, uid)


# ============================================================================
# 10. Simulate BASIC user — no digital_twin_advanced, POST returns 402
# ============================================================================
def test_basic_user_no_digital_twin(free_user, mongo):
    uid = free_user["user_id"]
    s = free_user["session"]
    _set_subscription(mongo, uid, "basic")
    time.sleep(1.0)
    try:
        r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["tier"] == "CLIENT_BASIC", body
        assert "house_health_basic" in body["features"], body
        assert "digital_twin_advanced" not in body["features"], body

        # INGEST allowed; ADVANCED (pins) gated 402
        r2 = s.post(f"{BASE_URL}/api/digital-twin/projects", json={"name": "TEST_basic_iter185"}, timeout=15)
        assert r2.status_code != 402, r2.text
        pid = r2.json().get("id") if r2.status_code in (200, 201) else None
        rp = s.post(
            f"{BASE_URL}/api/digital-twin/projects/{pid or 'nonexistent-id'}/pins",
            json={"position": {"x": 0, "y": 0, "z": 0}, "title": "abc"},
            timeout=10,
        )
        assert rp.status_code == 402, rp.text
        if pid:
            s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", timeout=10)
    finally:
        _clear_subscription(mongo, uid)


# ============================================================================
# 11. Legacy fallback: user with digital_twin_pro=true and no subscription
# ============================================================================
def test_legacy_digital_twin_pro_flag_still_works(free_user, mongo):
    uid = free_user["user_id"]
    s = free_user["session"]
    # ensure no subscription
    _clear_subscription(mongo, uid)
    # set legacy flag on user
    from bson import ObjectId
    try:
        mongo.users.update_one({"_id": ObjectId(uid)}, {"$set": {"digital_twin_pro": True}})
    except Exception:
        mongo.users.update_one({"id": uid}, {"$set": {"digital_twin_pro": True}})
    time.sleep(0.5)
    try:
        # /subscription should be active (via legacy path)
        r = s.get(f"{BASE_URL}/api/digital-twin/subscription", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["active"] is True, body

        # POST should not be 402
        r2 = s.post(f"{BASE_URL}/api/digital-twin/projects", json={"name": "TEST_legacy_iter185"}, timeout=15)
        assert r2.status_code != 402, r2.text
        if r2.status_code in (200, 201):
            pid = r2.json().get("id")
            if pid:
                s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", timeout=10)
    finally:
        try:
            mongo.users.update_one({"_id": ObjectId(uid)}, {"$set": {"digital_twin_pro": False}})
        except Exception:
            mongo.users.update_one({"id": uid}, {"$set": {"digital_twin_pro": False}})


# ============================================================================
# 12. Regression Task 2 — /pricing checkout basic still works
# ============================================================================
def test_regression_pricing_basic_checkout(free_user, mongo):
    # ensure clean state
    _clear_subscription(mongo, free_user["user_id"])
    s = free_user["session"]
    r = s.post(
        f"{BASE_URL}/api/house-health/checkout-session",
        json={"plan_slug": "basic", "origin_url": BASE_URL},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "session_id" in body and body["session_id"].startswith("cs_"), body
