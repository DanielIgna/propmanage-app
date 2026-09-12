"""Tests for Demo Accounts Manager (iter76)."""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

SUPER = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
DEMO_ACCOUNTS = [
    ("testing.admin@propmanage.io",  "Test!Demo2026Strong",  "testing",   "admin"),
    ("frontend.admin@propmanage.io", "Front!Demo2026Strong", "frontend",  "admin"),
    ("backend.admin@propmanage.io",  "Back!Demo2026Strong",  "backend",   "admin"),
    ("security.admin@propmanage.io", "Sec!Demo2026Strong",   "security",  "admin"),
    ("general.admin@propmanage.io",  "Gen!Demo2026Strong",   "general",   "admin"),
    ("marketing.admin@propmanage.io","Mkt!Demo2026Strong",   "marketing", "marketing_manager"),
]
MASTER = "0108"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    return r, s


@pytest.fixture(scope="module")
def super_session():
    r, s = _login(SUPER["email"], SUPER["password"])
    if r.status_code != 200:
        pytest.skip(f"Super admin login failed: {r.status_code} {r.text}")
    # ensure all demo accounts at default before test run
    for email, pw, _, _ in DEMO_ACCOUNTS:
        s.post(f"{API}/admin/demo-accounts/reset-password",
               json={"email": email, "master_code": MASTER}, timeout=20)
    yield s


@pytest.fixture(scope="module")
def testing_admin_session():
    r, s = _login("testing.admin@propmanage.io", "Test!Demo2026Strong")
    if r.status_code != 200:
        pytest.skip(f"testing.admin login failed: {r.status_code}")
    return s


# ---------- 1. GET list ----------

def test_list_demo_accounts_as_super(super_session):
    r = super_session.get(f"{API}/admin/demo-accounts", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 6
    by_email = {it["email"]: it for it in data["items"]}
    for email, pw, scope, role in DEMO_ACCOUNTS:
        assert email in by_email, f"missing {email}"
        item = by_email[email]
        assert item["scope"] == scope
        assert item["role"] == role
        assert item["default_password"] == pw
        assert item["exists"] is True


def test_list_demo_accounts_forbidden_for_non_super(testing_admin_session):
    r = testing_admin_session.get(f"{API}/admin/demo-accounts", timeout=20)
    assert r.status_code == 403


# ---------- 2. Login with default passwords ----------

@pytest.mark.parametrize("email,pw,scope,role", DEMO_ACCOUNTS)
def test_demo_default_login(email, pw, scope, role):
    r, _ = _login(email, pw)
    assert r.status_code == 200, f"{email} login failed: {r.status_code} {r.text}"


# ---------- 3. Reset password ----------

def test_reset_password_returns_default(super_session):
    email = "testing.admin@propmanage.io"
    r = super_session.post(f"{API}/admin/demo-accounts/reset-password",
                            json={"email": email, "master_code": MASTER}, timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["new_password"] == "Test!Demo2026Strong"
    # verify login post-reset
    lr, _ = _login(email, "Test!Demo2026Strong")
    assert lr.status_code == 200


def test_reset_wrong_master_code(super_session):
    r = super_session.post(f"{API}/admin/demo-accounts/reset-password",
                            json={"email": "testing.admin@propmanage.io",
                                  "master_code": "9999"}, timeout=20)
    assert r.status_code == 403
    assert "Cod master" in r.text or "master" in r.text.lower()


def test_reset_email_not_in_demo_list(super_session):
    r = super_session.post(f"{API}/admin/demo-accounts/reset-password",
                            json={"email": "stranger@propmanage.io",
                                  "master_code": MASTER}, timeout=20)
    assert r.status_code == 400


# ---------- 4. Set custom password ----------

def test_set_custom_password_and_old_default_revoked(super_session):
    email = "frontend.admin@propmanage.io"
    custom = "CustomPass2026!"
    r = super_session.post(f"{API}/admin/demo-accounts/set-password",
                            json={"email": email, "new_password": custom,
                                  "master_code": MASTER}, timeout=20)
    assert r.status_code == 200, r.text
    # custom login should work
    lr, _ = _login(email, custom)
    assert lr.status_code == 200, f"custom pw login failed: {lr.text}"
    # old default should NOT work
    lr_old, _ = _login(email, "Front!Demo2026Strong")
    assert lr_old.status_code != 200, "Old default still works after set-password!"
    # restore default for downstream tests
    super_session.post(f"{API}/admin/demo-accounts/reset-password",
                       json={"email": email, "master_code": MASTER}, timeout=20)


def test_set_password_weak_no_digits(super_session):
    r = super_session.post(f"{API}/admin/demo-accounts/set-password",
                            json={"email": "backend.admin@propmanage.io",
                                  "new_password": "AllLettersOnly",
                                  "master_code": MASTER}, timeout=20)
    assert r.status_code == 400


def test_set_password_too_short(super_session):
    r = super_session.post(f"{API}/admin/demo-accounts/set-password",
                            json={"email": "backend.admin@propmanage.io",
                                  "new_password": "Ab1!",
                                  "master_code": MASTER}, timeout=20)
    assert r.status_code == 422


def test_set_password_wrong_master(super_session):
    r = super_session.post(f"{API}/admin/demo-accounts/set-password",
                            json={"email": "backend.admin@propmanage.io",
                                  "new_password": "GoodPass2026!",
                                  "master_code": "1234"}, timeout=20)
    assert r.status_code == 403


# ---------- 5. RBAC: non-super forbidden on all 3 endpoints ----------

def test_non_super_forbidden_reset(testing_admin_session):
    r = testing_admin_session.post(f"{API}/admin/demo-accounts/reset-password",
                                   json={"email": "frontend.admin@propmanage.io",
                                         "master_code": MASTER}, timeout=20)
    assert r.status_code == 403


def test_non_super_forbidden_set(testing_admin_session):
    r = testing_admin_session.post(f"{API}/admin/demo-accounts/set-password",
                                   json={"email": "frontend.admin@propmanage.io",
                                         "new_password": "Whatever2026!",
                                         "master_code": MASTER}, timeout=20)
    assert r.status_code == 403


# ---------- 6. Regression: iter73-75 endpoints still work ----------

def test_regression_marketing_dashboard(super_session):
    r = super_session.get(f"{API}/admin/marketing/dashboard", timeout=20)
    assert r.status_code == 200


def test_regression_campaigns_list(super_session):
    r = super_session.get(f"{API}/admin/marketing/campaigns", timeout=20)
    assert r.status_code == 200


def test_regression_perf_summary(super_session):
    r = super_session.get(f"{API}/admin/marketing/performance/summary", timeout=20)
    assert r.status_code == 200
