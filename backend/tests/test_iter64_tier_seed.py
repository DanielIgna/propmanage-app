"""Iter64 - Verify tier demo seed accounts via /api/admin/users."""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD

# 9 tier demo accounts
TIER_USERS = [
    # (email, role, tier, verified, reviews_count, jobs_completed)
    ("client.junior@propmanage.io", "client", "JUNIOR", None, None, None),
    ("client.verified@propmanage.io", "client", "VERIFIED", None, None, None),
    ("client.premium@propmanage.io", "client", "PREMIUM", None, None, None),
    ("spec.entry@propmanage.io", "specialist", "ENTRY", False, 0, 0),
    ("spec.junior@propmanage.io", "specialist", "JUNIOR", False, 3, 3),
    ("spec.verified@propmanage.io", "specialist", "VERIFIED", True, 8, 8),
    ("spec.advanced@propmanage.io", "specialist", "ADVANCED", True, 25, 25),
    ("spec.premium@propmanage.io", "specialist", "PREMIUM", True, 62, 62),
    ("spec.top@propmanage.io", "specialist", "TOP", True, 138, 138),
]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.mark.parametrize("email,role,tier,verified,reviews,jobs", TIER_USERS)
def test_tier_user_present(admin_session, email, role, tier, verified, reviews, jobs):
    r = admin_session.get(f"{BASE_URL}/api/admin/users", params={"q": email, "limit": 5}, timeout=15)
    assert r.status_code == 200, f"admin/users failed: {r.text[:200]}"
    items = r.json().get("items", [])
    matches = [u for u in items if u.get("email") == email]
    assert len(matches) == 1, f"expected exactly 1 user for {email}, got {len(matches)}: {[u.get('email') for u in items]}"
    u = matches[0]
    assert u["role"] == role, f"role mismatch for {email}: {u.get('role')}"
    assert u.get("tier") == tier, f"tier mismatch for {email}: got {u.get('tier')} expected {tier}"
    if verified is not None:
        assert bool(u.get("verified")) == verified, f"verified mismatch for {email}: {u.get('verified')}"
    if reviews is not None:
        assert int(u.get("reviews_count", 0)) == reviews, f"reviews mismatch for {email}: {u.get('reviews_count')}"
    if jobs is not None:
        assert int(u.get("jobs_completed", 0)) == jobs, f"jobs mismatch for {email}: {u.get('jobs_completed')}"


@pytest.mark.parametrize("email", [u[0] for u in TIER_USERS])
def test_tier_user_login_with_demo_pass(email):
    """Each tier demo account must accept Demo123! password."""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "Demo123!"}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:200]}"
    data = r.json()
    # login may return user fields at top-level or nested under "user"
    email_out = data.get("email") or data.get("user", {}).get("email")
    assert email_out == email, f"login response missing email for {email}: {list(data.keys())[:10]}"


def test_regression_base_demo_logins():
    """Base demo accounts unchanged: specialist@propmanage.io and client@propmanage.io."""
    for email, pwd in [("specialist@propmanage.io", "Spec123!"), ("client@propmanage.io", "Client123!")]:
        r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
        assert r.status_code == 200, f"regression login failed: {email}: {r.text[:200]}"
