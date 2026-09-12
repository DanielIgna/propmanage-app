"""iter77 — Admin Accounts Manager tests.
Covers list/block-toggle/change-role/change-password + general.admin seed.
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

SUPER_EMAIL = "admin@propmanage.io"
SUPER_PASS = OWNER_ADMIN_PASSWORD
NON_SUPER_EMAIL = "testing.admin@propmanage.io"
NON_SUPER_PASS = "Test!Demo2026Strong"
GENERAL_EMAIL = "general.admin@propmanage.io"
GENERAL_DEFAULT_PASS = "Gen!Demo2026Strong"
TEMP_EMAIL = "temp.admin@propmanage.io"  # may not exist; tests will conditionally skip
MASTER = "0108"


def _login(email, password, session=None):
    s = session or requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    return r, s


@pytest.fixture(scope="session")
def super_token():
    r, s = _login(SUPER_EMAIL, SUPER_PASS)
    assert r.status_code == 200, f"Super admin login failed: {r.status_code} {r.text}"
    return s  # session with auth cookies


@pytest.fixture(scope="session")
def non_super_token():
    r, s = _login(NON_SUPER_EMAIL, NON_SUPER_PASS)
    if r.status_code != 200:
        pytest.skip(f"Non-super demo login failed ({r.status_code})")
    return s


def H(s):
    # Return session itself as a "client" — using session.cookies for auth.
    return s


# ---------- Seed verification ----------

def test_general_admin_seeded_and_can_login():
    r, _ = _login(GENERAL_EMAIL, GENERAL_DEFAULT_PASS)
    assert r.status_code == 200, f"general.admin login failed: {r.status_code} {r.text}"
    data = r.json()
    user = data
    assert user.get("email") == GENERAL_EMAIL
    assert user.get("role") in ("admin", "super_admin"), f"Unexpected role: {user.get('role')}"


def test_demo_accounts_now_six_includes_general(super_token):
    r = super_token.get(f"{BASE_URL}/api/admin/demo-accounts")
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or data.get("accounts") or []
    emails = [i.get("email") for i in items]
    assert GENERAL_EMAIL in emails, f"general.admin missing from demo list: {emails}"
    assert len(emails) >= 6, f"Expected 6+ demo accounts, got {len(emails)}: {emails}"


# ---------- GET /api/admin/admin-accounts ----------

def test_list_admins_super_ok(super_token):
    r = super_token.get(f"{BASE_URL}/api/admin/admin-accounts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body and isinstance(body["items"], list)
    assert SUPER_EMAIL in (body.get("protected_emails") or [])
    assert isinstance(body.get("allowed_roles"), list) and len(body["allowed_roles"]) > 0
    assert isinstance(body.get("allowed_scopes"), list) and len(body["allowed_scopes"]) > 0
    # Item shape check
    sample = body["items"][0]
    for k in ("email", "name", "role", "scope", "seniority", "is_active",
              "is_demo_sub_admin", "is_protected", "last_login_at", "created_at"):
        assert k in sample, f"Missing key {k} in item"
    emails = [it["email"] for it in body["items"]]
    # Should include the protected admin
    assert SUPER_EMAIL in emails
    assert GENERAL_EMAIL in emails
    # protected flag set correctly
    protected_row = next(it for it in body["items"] if it["email"] == SUPER_EMAIL)
    assert protected_row["is_protected"] is True


def test_list_admins_non_super_forbidden(non_super_token):
    r = non_super_token.get(f"{BASE_URL}/api/admin/admin-accounts")
    assert r.status_code == 403, r.text
    body = r.json()
    msg = body.get("detail") or body.get("message") or ""
    assert "super-admin" in msg.lower() or "doar super" in msg.lower()


# ---------- Block-toggle ----------

def test_block_toggle_protected_email(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                      json={"email": SUPER_EMAIL, "master_code": MASTER})
    assert r.status_code == 400, r.text
    assert "protejat" in (r.json().get("detail") or "").lower()


def test_block_toggle_wrong_code(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                      json={"email": GENERAL_EMAIL, "master_code": "9999"})
    assert r.status_code == 403, r.text
    assert "incorect" in (r.json().get("detail") or "").lower()


def test_block_toggle_flip_and_restore(super_token):
    # Use general.admin as test target since temp.admin may not exist
    target = GENERAL_EMAIL
    # First flip
    r1 = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                       json={"email": target, "master_code": MASTER})
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1.get("ok") is True
    state1 = b1.get("is_active")
    # Second flip restores
    r2 = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                       json={"email": target, "master_code": MASTER})
    assert r2.status_code == 200
    state2 = r2.json().get("is_active")
    assert state1 != state2, f"Expected flip; got {state1} -> {state2}"
    # Ensure end state is active=True (reset if not)
    if state2 is False:
        r3 = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                           json={"email": target, "master_code": MASTER})
        assert r3.status_code == 200
        assert r3.json().get("is_active") is True


# ---------- Change role ----------

def test_change_role_protected_blocked(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                      json={"email": SUPER_EMAIL, "new_role": "operator",
                            "new_scope": "ops", "master_code": MASTER})
    assert r.status_code == 400, r.text
    assert "protejat" in (r.json().get("detail") or "").lower()


def test_change_role_invalid_role(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                      json={"email": GENERAL_EMAIL, "new_role": "bogus_role",
                            "new_scope": "general", "master_code": MASTER})
    assert r.status_code == 400
    assert "rol" in (r.json().get("detail") or "").lower()


def test_change_role_invalid_scope(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                      json={"email": GENERAL_EMAIL, "new_role": "admin",
                            "new_scope": "not_a_scope", "master_code": MASTER})
    assert r.status_code == 400
    assert "scope" in (r.json().get("detail") or "").lower()


def test_change_role_success_and_restore(super_token):
    # Change general.admin to operator/ops, then back to admin/general
    r1 = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                       json={"email": GENERAL_EMAIL, "new_role": "operator",
                             "new_scope": "ops", "master_code": MASTER})
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["new_role"] == "operator" and b1["new_scope"] == "ops"

    # Verify via admin-accounts list (DB source of truth)
    lst = super_token.get(f"{BASE_URL}/api/admin/admin-accounts")
    assert lst.status_code == 200
    row = next((it for it in lst.json()["items"] if it["email"] == GENERAL_EMAIL), None)
    assert row is not None, "general.admin missing from list after role change"
    assert row["role"] == "operator", f"Role did not persist: {row['role']} (scope={row['scope']})"
    assert row["scope"] == "ops"

    # Restore
    r2 = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                       json={"email": GENERAL_EMAIL, "new_role": "admin",
                             "new_scope": "general", "master_code": MASTER})
    assert r2.status_code == 200
    assert r2.json()["new_role"] == "admin"


# ---------- Change password ----------

def test_change_password_weak_no_digits(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-password",
                      json={"email": GENERAL_EMAIL,
                            "new_password": "NoDigitsHere",
                            "master_code": MASTER})
    assert r.status_code == 400, r.text
    assert "cifr" in (r.json().get("detail") or "").lower() or "litere" in (r.json().get("detail") or "").lower()


def test_change_password_too_short(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-password",
                      json={"email": GENERAL_EMAIL,
                            "new_password": "Sh0rt",
                            "master_code": MASTER})
    assert r.status_code == 422, r.text


def test_change_password_success_and_login(super_token):
    new_pw = "NewPass2026!"
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-password",
                      json={"email": GENERAL_EMAIL,
                            "new_password": new_pw,
                            "master_code": MASTER})
    assert r.status_code == 200, r.text
    # Login with new
    lr, _ = _login(GENERAL_EMAIL, new_pw)
    assert lr.status_code == 200, f"Login with new pw failed: {lr.status_code} {lr.text}"
    # Restore to default via demo-accounts reset (idempotent)
    rst = super_token.post(f"{BASE_URL}/api/admin/demo-accounts/reset-password",
                       json={"email": GENERAL_EMAIL, "master_code": MASTER})
    # Reset endpoint may or may not exist for general.admin. If not, set it back via change-password.
    if rst.status_code != 200:
        r2 = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-password",
                           json={"email": GENERAL_EMAIL,
                                 "new_password": GENERAL_DEFAULT_PASS,
                                 "master_code": MASTER})
        assert r2.status_code == 200
    # Verify default restored
    lr2, _ = _login(GENERAL_EMAIL, GENERAL_DEFAULT_PASS)
    assert lr2.status_code == 200


def test_change_password_wrong_master(super_token):
    r = super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-password",
                      json={"email": GENERAL_EMAIL,
                            "new_password": "Whatever123!",
                            "master_code": "0000"})
    assert r.status_code == 403


# ---------- Non-super forbidden on writes ----------

def test_non_super_cannot_block(non_super_token):
    r = non_super_token.post(f"{BASE_URL}/api/admin/admin-accounts/block-toggle",
                      json={"email": GENERAL_EMAIL, "master_code": MASTER})
    assert r.status_code == 403


def test_non_super_cannot_change_role(non_super_token):
    r = non_super_token.post(f"{BASE_URL}/api/admin/admin-accounts/change-role",
                      json={"email": GENERAL_EMAIL, "new_role": "operator",
                            "new_scope": "ops", "master_code": MASTER})
    assert r.status_code == 403


# ---------- Regression iter75 (marketing perf) ----------

def test_regression_marketing_perf_summary(super_token):
    r = super_token.get(f"{BASE_URL}/api/admin/marketing/performance/summary")
    # Should respond 200 or 404 if endpoint renamed; we want 200
    assert r.status_code == 200, f"Regression failed: {r.status_code} {r.text[:200]}"
