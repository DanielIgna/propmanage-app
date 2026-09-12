"""
Task 2 iter184 — Pricing / Basic 9€ commercial flow tests.

Focus:
- Fresh FREE user creation via /api/auth/register
- POST /api/house-health/checkout-session with plan_slug='basic'
- 404 on unknown plan slug
- GET /api/house-health/checkout-status/{sid}
- Simulated activation via direct hh_subscriptions upsert -> entitlements = CLIENT_BASIC
- Regression: client@ (premium), admin@ (bypass)
- Regression: house-health dashboard no longer locked=no_subscription after activation
"""
import os
import re
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
        "name": "Free Test User",
        "role": "client",
        "terms_accepted": True,
        "privacy_policy_accepted": True,
    }
    r = s.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=15)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text}"
    # Ensure session by logging in (register might not auto-login)
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if me.status_code != 200:
        s = _login(email, "FreePass123!")
    return email, s


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    # Cleanup ophrans at end
    try:
        # Delete test users
        emails = list(db.users.find({"email": {"$regex": r"^free\d+.*@example\.com$"}}, {"email": 1, "id": 1}))
        ids = [str(u.get("_id")) for u in emails if u.get("_id")]
        db.users.delete_many({"email": {"$regex": r"^free\d+.*@example\.com$"}})
        if ids:
            db.hh_subscriptions.delete_many({"user_id": {"$in": ids}})
    finally:
        client.close()


@pytest.fixture(scope="module")
def free_user(mongo):
    email, s = _register_free_user()
    # fetch user_id — user records use MongoDB _id serialized to string as 'id'
    u = mongo.users.find_one({"email": email})
    uid = str(u.get("_id")) if u else None
    yield {"email": email, "session": s, "user_id": uid}


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


# ---------------------------------------------------------------------------
# 1. Public /pricing page loads (frontend route, but we can check backend does not require auth for entitlements? No — the page uses hook. Skip static HTML check.)
#    Instead test that no auth is required for the front-end route -- covered via playwright.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Basic plan exists & is 9 EUR
# ---------------------------------------------------------------------------
def test_basic_plan_exists_and_is_9_eur(client_s):
    r = client_s.get(f"{BASE_URL}/api/house-health/plans")
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    basic = next((p for p in items if p.get("slug") == "basic"), None)
    assert basic is not None, "No 'basic' plan found"
    assert float(basic.get("price_eur", 0)) == 9.0
    assert basic.get("active", True) is True


# ---------------------------------------------------------------------------
# 3. Checkout session (basic) for FREE user
# ---------------------------------------------------------------------------
def test_checkout_session_basic_free_user(free_user):
    s = free_user["session"]
    r = s.post(
        f"{BASE_URL}/api/house-health/checkout-session",
        json={"plan_slug": "basic", "origin_url": BASE_URL},
        timeout=20,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    assert "session_id" in body
    assert re.match(r"^cs_(test|live)_", body["session_id"]), body["session_id"]
    assert "checkout.stripe.com" in body.get("url", ""), body.get("url")


# ---------------------------------------------------------------------------
# 4. Unknown plan -> 404
# ---------------------------------------------------------------------------
def test_checkout_session_unknown_plan_404(free_user):
    s = free_user["session"]
    r = s.post(
        f"{BASE_URL}/api/house-health/checkout-session",
        json={"plan_slug": "does-not-exist-zzz", "origin_url": BASE_URL},
        timeout=15,
    )
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# 5. Checkout status endpoint
# ---------------------------------------------------------------------------
def test_checkout_status_valid_and_unknown(free_user):
    s = free_user["session"]
    # valid
    r = s.post(
        f"{BASE_URL}/api/house-health/checkout-session",
        json={"plan_slug": "basic", "origin_url": BASE_URL},
        timeout=20,
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]
    r2 = s.get(f"{BASE_URL}/api/house-health/checkout-status/{sid}", timeout=15)
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert "payment_status" in body
    assert "status" in body or "payment_status" in body

    # unknown
    r3 = s.get(f"{BASE_URL}/api/house-health/checkout-status/cs_test_fakebogus_zzz_404", timeout=15)
    assert r3.status_code == 404


# ---------------------------------------------------------------------------
# 6. Simulate activation -> tier = CLIENT_BASIC + house_health_basic feature
# ---------------------------------------------------------------------------
def test_simulated_activation_sets_client_basic(free_user, mongo):
    s = free_user["session"]
    uid = free_user["user_id"]
    assert uid, "user_id missing for free_user"

    # Upsert an active basic subscription — entitlements query uses ISO string comparison
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    expires_iso = (now + timedelta(days=30)).isoformat()
    mongo.hh_subscriptions.update_one(
        {"user_id": uid},
        {
            "$set": {
                "user_id": uid,
                "plan": "basic",
                "plan_slug": "basic",
                "status": "active",
                "expires_at": expires_iso,
                "started_at": now_iso,
                "updated_at": now_iso,
            }
        },
        upsert=True,
    )

    # Give backend a moment (entitlement cache typically short)
    time.sleep(1.5)

    r = s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tier") == "CLIENT_BASIC", f"expected CLIENT_BASIC, got {body.get('tier')} :: {body}"
    features = body.get("features", [])
    assert "house_health_basic" in features, f"features missing house_health_basic: {features}"


# ---------------------------------------------------------------------------
# 7. After activation, dashboard is NOT locked with no_subscription
# ---------------------------------------------------------------------------
def test_dashboard_not_locked_by_subscription_after_activation(free_user):
    s = free_user["session"]
    r = s.get(f"{BASE_URL}/api/house-health/dashboard", timeout=20)
    # May be 200 with locked=no_twin, or 200 with data. But must NOT be locked=no_subscription.
    assert r.status_code in (200, 403, 404), r.text
    if r.status_code == 200:
        body = r.json()
        lock = body.get("lock_reason") or body.get("locked_reason")
        assert lock != "no_subscription", f"still locked by no_subscription: {body}"


# ---------------------------------------------------------------------------
# 8. Regression: existing client premium
# ---------------------------------------------------------------------------
def test_regression_client_premium(client_s):
    r = client_s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tier") == "CLIENT_PREMIUM", body
    assert body.get("is_admin_bypass") is False


# ---------------------------------------------------------------------------
# 9. Regression: admin bypass
# ---------------------------------------------------------------------------
def test_regression_admin_bypass(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/me/entitlements", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("tier") == "CLIENT_PREMIUM", body
    assert body.get("is_admin_bypass") is True


# ---------------------------------------------------------------------------
# 10. Unauthenticated /checkout-session -> 401/403
# ---------------------------------------------------------------------------
def test_checkout_session_requires_auth():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/house-health/checkout-session",
        json={"plan_slug": "basic", "origin_url": BASE_URL},
        timeout=15,
    )
    assert r.status_code in (401, 403), r.status_code
