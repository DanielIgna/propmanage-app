"""Iter 156 — Product Guardian (PM-GUARDIAN-003) backend tests (HTTP, sync)."""
import os
from pathlib import Path

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture(scope="module")
def partner_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": "mp.partner.test@propmanage.io", "password": "MpTest123!"}, timeout=15)
    assert r.status_code == 200
    return s


def test_product_guardian_run(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/product-guardian/run", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert 5 <= d["product_score"] <= 100
    assert "ceo_summary" in d
    assert "first_value" in d and "conversion" in d


def test_product_guardian_status(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/product-guardian/status", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["last_run"] is not None
    open_keys = {t["key"] for t in d["open_tasks"]}
    assert "role_no_home:marketplace_partner" not in open_keys, "portalul marketplace_partner există acum"
    assert "role_no_home:marketing_manager" not in open_keys, "marketing_manager mapat la /admin/marketing"


def test_product_guardian_requires_admin():
    r = requests.get(f"{BASE_URL}/api/admin/repair-center/product-guardian/status", timeout=15)
    assert r.status_code in (401, 403)


def test_marketplace_partner_portal_api(partner_session):
    r = partner_session.get(f"{BASE_URL}/api/marketplace-partner/me", timeout=15)
    assert r.status_code == 200
    r = partner_session.get(f"{BASE_URL}/api/marketplace-partner/stats", timeout=15)
    assert r.status_code == 200
    assert "leads_total" in r.json()
    r = partner_session.get(f"{BASE_URL}/api/marketplace-partner/leads", timeout=15)
    assert r.status_code == 200


def test_role_home_mapping_in_auth_jsx():
    auth = Path("/app/frontend/src/pages/Auth.jsx").read_text()
    assert '"/partner/marketplace"' in auth
    assert '"/admin/marketing"' in auth
    app = Path("/app/frontend/src/App.js").read_text()
    assert 'path="/partner/marketplace"' in app
