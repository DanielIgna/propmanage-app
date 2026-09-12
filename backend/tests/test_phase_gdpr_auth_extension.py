"""GDPR Auth Extension tests — Phase 1/2/3/5
Tests:
 - /api/auth/register with consent gates (terms, privacy, marketing)
 - consent_audit_log entries
 - /api/auth/verify-email (valid, invalid, reuse)
 - /api/auth/resend-verification rate-limit
 - PATCH /api/me/consent
 - POST /api/cookies/consent (anonymous + authenticated)
 - GET /api/admin/users with email_verified/phone_verified/marketing_consent filters
 - Backfill grandfathered seeded users
 - Login regression for 3 seeded accounts
"""
import os
import uuid
import requests
import pytest
from pymongo import MongoClient
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break

MONGO_URL = None
DB_NAME = None
with open("/app/backend/.env") as f:
    for line in f:
        line = line.strip()
        if line.startswith("MONGO_URL="):
            MONGO_URL = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("DB_NAME="):
            DB_NAME = line.split("=", 1)[1].strip().strip('"')

mongo = MongoClient(MONGO_URL)
mdb = mongo[DB_NAME]


@pytest.fixture(scope="module")
def s():
    return requests.Session()


def _unique_email(prefix="phasetest"):
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


# ============ REGISTER CONSENT GATES ============
class TestRegisterConsent:
    def test_register_without_terms_returns_400(self):
        email = _unique_email()
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "Test", "role": "client",
            "terms_accepted": False, "privacy_policy_accepted": True,
        })
        assert r.status_code == 400, r.text
        assert "Termenii" in r.text

    def test_register_without_privacy_returns_400(self):
        email = _unique_email()
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "Test", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": False,
        })
        assert r.status_code == 400, r.text
        assert "Confidențialitate" in r.text or "Politica" in r.text

    def test_register_full_consent_success_and_audit_log(self):
        email = _unique_email()
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "Test User", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True, "marketing_consent": True,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("terms_accepted") is True
        assert data.get("privacy_policy_accepted") is True
        assert data.get("marketing_consent") is True
        assert data.get("email_verified") is False
        assert data.get("phone_verified") is False
        # email_verification_token MUST NOT be in response
        assert "email_verification_token" not in data

        uid = data["id"]
        # Verify 3 audit log entries (terms, privacy, marketing)
        logs = list(mdb.consent_audit_log.find({"user_id": uid}))
        types = {l["consent_type"] for l in logs}
        assert "terms" in types
        assert "privacy" in types
        assert "marketing" in types
        assert all(l.get("source") == "register" for l in logs)


# ============ EMAIL VERIFY ============
class TestEmailVerification:
    def test_verify_email_full_flow(self):
        email = _unique_email("verifytest")
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "V", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True,
        })
        assert r.status_code == 200
        # Grab token from Mongo directly (not exposed in API)
        doc = mdb.users.find_one({"email": email})
        token = doc.get("email_verification_token")
        assert token, "Token missing from DB"

        r1 = requests.get(f"{BASE_URL}/api/auth/verify-email", params={"token": token})
        assert r1.status_code == 200, r1.text
        body = r1.json()
        assert body.get("ok") is True
        assert body.get("verified") is True

        # Second call with same token → 404 (token cleared)
        r2 = requests.get(f"{BASE_URL}/api/auth/verify-email", params={"token": token})
        assert r2.status_code == 404

        # Verify DB updated
        doc2 = mdb.users.find_one({"email": email})
        assert doc2.get("email_verified") is True
        assert "email_verification_token" not in doc2

    def test_verify_email_invalid_token(self):
        r = requests.get(f"{BASE_URL}/api/auth/verify-email",
                         params={"token": "invalidtokenwithlength32abcdefghijkl"})
        assert r.status_code == 404

    def test_resend_verification_and_rate_limit(self, s):
        email = _unique_email("resend")
        r = s.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "R", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True,
        })
        assert r.status_code == 200
        # First resend (cookies already set from register)
        r1 = s.post(f"{BASE_URL}/api/auth/resend-verification")
        assert r1.status_code == 200, r1.text
        assert r1.json().get("sent") is True
        # Second immediate call → 429
        r2 = s.post(f"{BASE_URL}/api/auth/resend-verification")
        assert r2.status_code == 429
        assert "teaptă" in r2.text or "Asteapta" in r2.text or "secunde" in r2.text or "s înainte" in r2.text


# ============ PATCH /me/consent ============
class TestConsentPatch:
    def test_update_marketing_consent(self):
        email = _unique_email("consupd")
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "C", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True, "marketing_consent": True,
        })
        assert r.status_code == 200
        uid = r.json()["id"]
        # Patch marketing_consent false
        r1 = s.patch(f"{BASE_URL}/api/me/consent", json={"marketing_consent": False})
        assert r1.status_code == 200, r1.text
        # Verify DB
        doc = mdb.users.find_one({"email": email})
        assert doc.get("marketing_consent") is False
        # Verify audit log has settings-source entry
        log = mdb.consent_audit_log.find_one(
            {"user_id": uid, "source": "settings", "consent_type": "marketing"}
        )
        assert log is not None
        assert log["accepted"] is False


# ============ COOKIE CONSENT ============
class TestCookieConsent:
    def test_anonymous_cookie_consent(self):
        r = requests.post(f"{BASE_URL}/api/cookies/consent", json={
            "analytics_cookies_accepted": True,
            "marketing_cookies_accepted": False,
        })
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_authenticated_cookie_consent_updates_user(self):
        email = _unique_email("cook")
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/register", json={
            "phone": "+40712000999",
            "email": email, "password": "Pass123!", "name": "K", "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True,
        })
        assert r.status_code == 200
        r1 = s.post(f"{BASE_URL}/api/cookies/consent", json={
            "functional_cookies_accepted": True,
            "analytics_cookies_accepted": True,
            "marketing_cookies_accepted": False,
        })
        assert r1.status_code == 200
        doc = mdb.users.find_one({"email": email})
        assert doc.get("functional_cookies_accepted") is True
        assert doc.get("analytics_cookies_accepted") is True
        assert doc.get("marketing_cookies_accepted") is False


# ============ ADMIN USERS FILTERS ============
class TestAdminUsersFilters:
    @pytest.fixture(scope="class")
    def admin_session(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD
        })
        assert r.status_code == 200, f"Admin login failed: {r.text}"
        return s

    def test_filter_email_verified_false(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/users", params={"email_verified": False})
        assert r.status_code == 200, r.text
        data = r.json()
        items = data.get("items", data if isinstance(data, list) else [])
        # all returned items must have email_verified=false
        for u in items:
            assert u.get("email_verified") is False, f"User leaked: {u.get('email')}"

    def test_filter_phone_verified_true(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/users", params={"phone_verified": True})
        assert r.status_code == 200
        items = r.json().get("items", r.json() if isinstance(r.json(), list) else [])
        for u in items:
            assert u.get("phone_verified") is True

    def test_filter_marketing_consent_true(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/users", params={"marketing_consent": True})
        assert r.status_code == 200
        items = r.json().get("items", r.json() if isinstance(r.json(), list) else [])
        for u in items:
            assert u.get("marketing_consent") is True


# ============ BACKFILL CHECK ============
class TestBackfill:
    @pytest.mark.parametrize("email", [
        "admin@propmanage.io",
        "client@propmanage.io",
        "specialist@propmanage.io",
    ])
    def test_seeded_users_grandfathered(self, email):
        doc = mdb.users.find_one({"email": email})
        assert doc is not None, f"{email} not seeded"
        assert doc.get("email_verified") is True, f"{email} email_verified missing/false"
        assert doc.get("terms_accepted") is True
        assert doc.get("privacy_policy_accepted") is True
        assert doc.get("consent_grandfathered") is True


# ============ LOGIN REGRESSION ============
class TestLoginRegression:
    @pytest.mark.parametrize("email,password", [
        ("admin@propmanage.io", OWNER_ADMIN_PASSWORD),
        ("client@propmanage.io", "Client123!"),
        ("specialist@propmanage.io", "Spec123!"),
    ])
    def test_login_succeeds(self, email, password):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, f"Login failed for {email}: {r.text}"
        # /me works
        r2 = s.get(f"{BASE_URL}/api/auth/me")
        assert r2.status_code == 200
        assert r2.json().get("email") == email
