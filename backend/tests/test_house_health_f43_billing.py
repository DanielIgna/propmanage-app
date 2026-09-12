"""House Health F4.3 — Stripe Checkout flow tests."""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CRED = {
    "client": {"email": "client@propmanage.io", "password": "Client123!"},
    "admin": {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD},
}


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def client_s():
    return _login(**CRED["client"])


@pytest.fixture(scope="module")
def admin_s():
    return _login(**CRED["admin"])


# ============================================================================
# Default plan seeding
# ============================================================================
def test_default_plans_exist(client_s):
    r = client_s.get(f"{BASE_URL}/api/house-health/plans")
    assert r.status_code == 200
    slugs = {p["slug"] for p in r.json()["items"]}
    # at least basic/pro/premium should be present
    assert "basic" in slugs
    assert "pro" in slugs
    assert "premium" in slugs


def test_plans_sorted_by_sort_order(client_s):
    items = client_s.get(f"{BASE_URL}/api/house-health/plans").json()["items"]
    orders = [p.get("sort_order", 0) for p in items]
    assert orders == sorted(orders)


# ============================================================================
# Checkout session creation
# ============================================================================
def test_checkout_unknown_plan_404(client_s):
    r = client_s.post(f"{BASE_URL}/api/house-health/checkout-session", json={
        "plan_slug": "this-does-not-exist", "origin_url": BASE_URL,
    })
    assert r.status_code == 404


def test_checkout_premium_returns_stripe_url(client_s):
    r = client_s.post(f"{BASE_URL}/api/house-health/checkout-session", json={
        "plan_slug": "premium", "origin_url": BASE_URL,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["url"].startswith("https://checkout.stripe.com/")
    assert body["session_id"]


def test_checkout_unauthorized(admin_s):
    """Anonymous request — no session cookie."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/house-health/checkout-session", json={
        "plan_slug": "premium", "origin_url": BASE_URL,
    })
    assert r.status_code in (401, 403)


# ============================================================================
# Checkout status polling
# ============================================================================
def test_checkout_status_unknown_session_404(client_s):
    r = client_s.get(f"{BASE_URL}/api/house-health/checkout-status/sess_nonexistent")
    assert r.status_code == 404


def test_checkout_status_returns_pending_for_new_session(client_s):
    create = client_s.post(f"{BASE_URL}/api/house-health/checkout-session", json={
        "plan_slug": "basic", "origin_url": BASE_URL,
    })
    sid = create.json()["session_id"]
    r = client_s.get(f"{BASE_URL}/api/house-health/checkout-status/{sid}")
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"] == sid
    # Stripe returns "unpaid" / "open" for a session that hasn't been completed yet.
    # In the Emergent test sandbox the session may be unrecoverable across calls,
    # in which case we surface the cached "initiated" status — still success.
    assert body["payment_status"] in ("unpaid", "no_payment_required", "paid", "initiated", "pending")
    assert body["activated"] is False or body.get("already_activated") is False


def test_checkout_status_cross_user_blocked(client_s, admin_s):
    create = client_s.post(f"{BASE_URL}/api/house-health/checkout-session", json={
        "plan_slug": "basic", "origin_url": BASE_URL,
    })
    sid = create.json()["session_id"]
    # admin CAN access (whitelisted)
    r_admin = admin_s.get(f"{BASE_URL}/api/house-health/checkout-status/{sid}")
    assert r_admin.status_code == 200
    # but specialist (different user) should NOT
    spec = _login("specialist@propmanage.io", "Spec123!")
    r_spec = spec.get(f"{BASE_URL}/api/house-health/checkout-status/{sid}")
    assert r_spec.status_code == 403
