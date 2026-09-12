"""House Health F4 tests — Plans CRUD + Scoring config + Recommendations + Marketplace publish.

Mirrors the style of test_house_health.py (live API via requests).
"""
import os
import uuid

import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
TWIN_ID = "2d0a899472b34e32a8eaf79b88d7c012"

CRED = {
    "client": {"email": "client@propmanage.io", "password": "Client123!"},
    "admin": {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD},
    "specialist": {"email": "specialist@propmanage.io", "password": "Spec123!"},
}


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin_s():
    return _login(**CRED["admin"])


@pytest.fixture(scope="module")
def client_s():
    return _login(**CRED["client"])


@pytest.fixture(scope="module")
def spec_s():
    return _login(**CRED["specialist"])


@pytest.fixture(scope="module")
def approved_eval(client_s):
    r = client_s.get(f"{BASE_URL}/api/house-health/evaluations",
                     params={"twin_project_id": TWIN_ID, "status": "approved"})
    items = r.json().get("items", [])
    assert items, "Test relies on at least one approved evaluation"
    return items[0]["id"]


# ============================================================================
# F4.1 — Plans CRUD
# ============================================================================
def test_plans_crud_lifecycle(admin_s):
    slug = f"test_plan_{uuid.uuid4().hex[:8]}"
    r = admin_s.post(f"{BASE_URL}/api/admin/house-health/plans", json={
        "slug": slug, "name": "Test Plan", "price_eur": 19.99,
        "billing_period": "monthly", "trial_days": 7,
        "features": ["a", "b"], "lead_commission_pct": 12, "sort_order": 99,
    })
    assert r.status_code == 200, r.text
    plan_id = r.json()["plan"]["id"]

    # duplicate
    r2 = admin_s.post(f"{BASE_URL}/api/admin/house-health/plans", json={
        "slug": slug, "name": "X", "price_eur": 1, "billing_period": "monthly",
    })
    assert r2.status_code == 409

    # patch
    r3 = admin_s.patch(f"{BASE_URL}/api/admin/house-health/plans/{plan_id}", json={"price_eur": 29.99})
    assert r3.status_code == 200
    assert r3.json()["plan"]["price_eur"] == 29.99

    # archive
    r4 = admin_s.delete(f"{BASE_URL}/api/admin/house-health/plans/{plan_id}")
    assert r4.status_code == 200


def test_plans_admin_only(client_s):
    r = client_s.post(f"{BASE_URL}/api/admin/house-health/plans", json={
        "slug": "x_should_fail", "name": "X", "price_eur": 1, "billing_period": "monthly",
    })
    assert r.status_code == 403


def test_plans_billing_period_validation(admin_s):
    r = admin_s.post(f"{BASE_URL}/api/admin/house-health/plans", json={
        "slug": "bad_bp", "name": "X", "price_eur": 1, "billing_period": "weekly",
    })
    assert r.status_code == 422


# ============================================================================
# F4.1 — Scoring config
# ============================================================================
def test_scoring_config_read(client_s):
    r = client_s.get(f"{BASE_URL}/api/house-health/scoring-config")
    assert r.status_code == 200
    body = r.json()
    assert "weights" in body and "thresholds" in body
    assert abs(sum(body["weights"].values()) - 100) < 0.01


def test_scoring_weights_must_sum_to_100(admin_s):
    r = admin_s.put(f"{BASE_URL}/api/admin/house-health/scoring-config", json={
        "weights": {"air": 10, "thermal": 10, "humidity": 10, "electric": 10, "docs": 10, "maintenance": 10, "radon": 10},
    })
    assert r.status_code == 422


def test_scoring_weights_missing_key(admin_s):
    r = admin_s.put(f"{BASE_URL}/api/admin/house-health/scoring-config", json={
        "weights": {"air": 100, "thermal": 0, "humidity": 0, "electric": 0, "docs": 0, "maintenance": 0},  # no radon
    })
    assert r.status_code == 422


def test_scoring_thresholds_order(admin_s):
    r = admin_s.put(f"{BASE_URL}/api/admin/house-health/scoring-config", json={
        "weights": {"air": 15, "thermal": 20, "humidity": 15, "electric": 15, "docs": 10, "maintenance": 15, "radon": 10},
        "thresholds": {"excellent": 90, "good": 50, "fair": 60},  # fair > good (invalid)
    })
    assert r.status_code == 422


def test_scoring_valid_update_persists(admin_s, client_s):
    new_weights = {"air": 20, "thermal": 20, "humidity": 15, "electric": 15, "docs": 10, "maintenance": 10, "radon": 10}
    r = admin_s.put(f"{BASE_URL}/api/admin/house-health/scoring-config", json={
        "weights": new_weights,
        "thresholds": {"excellent": 92, "good": 78, "fair": 55},
    })
    assert r.status_code == 200
    # client can read latest
    r2 = client_s.get(f"{BASE_URL}/api/house-health/scoring-config")
    body = r2.json()
    for k, v in new_weights.items():
        assert body["weights"][k] == v


# ============================================================================
# F4.2 — Recommendations
# ============================================================================
def test_recommendation_client_cannot_create(client_s, approved_eval):
    r = client_s.post(f"{BASE_URL}/api/house-health/recommendations", json={
        "evaluation_id": approved_eval, "title": "TEST_should_fail", "priority": "recommended",
    })
    assert r.status_code == 403


def test_recommendation_specialist_lifecycle(spec_s, client_s, admin_s, approved_eval):
    # specialist creates
    r = spec_s.post(f"{BASE_URL}/api/house-health/recommendations", json={
        "evaluation_id": approved_eval, "title": "TEST_F42_lifecycle",
        "description": "test", "priority": "recommended", "category": "thermal",
        "estimated_cost_eur": 100,
    })
    assert r.status_code == 200, r.text
    rec_id = r.json()["recommendation"]["id"]

    # client lists for own twin
    r2 = client_s.get(f"{BASE_URL}/api/house-health/recommendations", params={"twin_project_id": TWIN_ID})
    assert r2.status_code == 200
    assert any(x["id"] == rec_id for x in r2.json()["items"])

    # client without twin_project_id → 400
    r3 = client_s.get(f"{BASE_URL}/api/house-health/recommendations")
    assert r3.status_code == 400

    # specialist patches own → 200
    r4 = spec_s.patch(f"{BASE_URL}/api/house-health/recommendations/{rec_id}", json={"status": "done"})
    assert r4.status_code == 200

    # client cannot patch
    r5 = client_s.patch(f"{BASE_URL}/api/house-health/recommendations/{rec_id}", json={"status": "dismissed"})
    assert r5.status_code == 403

    # admin can patch
    r6 = admin_s.patch(f"{BASE_URL}/api/house-health/recommendations/{rec_id}", json={"status": "dismissed"})
    assert r6.status_code == 200

    # cleanup
    spec_s.delete(f"{BASE_URL}/api/house-health/recommendations/{rec_id}")


def test_recommendation_invalid_priority(spec_s, approved_eval):
    r = spec_s.post(f"{BASE_URL}/api/house-health/recommendations", json={
        "evaluation_id": approved_eval, "title": "X", "priority": "invalid",
    })
    assert r.status_code == 422


# ============================================================================
# F4.4 — Marketplace publish
# ============================================================================
def test_publish_urgent_to_marketplace(spec_s, client_s, approved_eval):
    r = spec_s.post(f"{BASE_URL}/api/house-health/recommendations", json={
        "evaluation_id": approved_eval, "title": "TEST_F44_publish_full",
        "priority": "urgent", "category": "electric", "estimated_cost_eur": 500,
    })
    rec_id = r.json()["recommendation"]["id"]

    r2 = client_s.post(f"{BASE_URL}/api/house-health/recommendations/{rec_id}/publish-to-marketplace",
                       json={"budget_estimate": 500})
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["ok"] is True
    assert body["commission_pct"] >= 0
    assert body["request_id"]

    # double publish → 409
    r3 = client_s.post(f"{BASE_URL}/api/house-health/recommendations/{rec_id}/publish-to-marketplace", json={})
    assert r3.status_code == 409

    # stats — client view shows the request
    r4 = client_s.get(f"{BASE_URL}/api/house-health/marketplace-stats")
    assert r4.status_code == 200
    assert r4.json()["role"] == "client"
    assert any(x["request_id"] == body["request_id"] for x in r4.json()["items"])


def test_publish_monitor_priority_rejected(spec_s, client_s, approved_eval):
    r = spec_s.post(f"{BASE_URL}/api/house-health/recommendations", json={
        "evaluation_id": approved_eval, "title": "TEST_F44_monitor",
        "priority": "monitor",
    })
    rec_id = r.json()["recommendation"]["id"]
    r2 = client_s.post(f"{BASE_URL}/api/house-health/recommendations/{rec_id}/publish-to-marketplace", json={})
    assert r2.status_code == 400
    spec_s.delete(f"{BASE_URL}/api/house-health/recommendations/{rec_id}")


def test_publish_non_owner_blocked(spec_s, approved_eval):
    r = spec_s.post(f"{BASE_URL}/api/house-health/recommendations", json={
        "evaluation_id": approved_eval, "title": "TEST_F44_non_owner",
        "priority": "urgent",
    })
    rec_id = r.json()["recommendation"]["id"]
    # specialist (not the twin owner) attempts publish
    r2 = spec_s.post(f"{BASE_URL}/api/house-health/recommendations/{rec_id}/publish-to-marketplace", json={})
    assert r2.status_code == 403
    spec_s.delete(f"{BASE_URL}/api/house-health/recommendations/{rec_id}")


def test_admin_marketplace_stats(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/house-health/marketplace-stats")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert "total_published" in body
    assert "by_status" in body
