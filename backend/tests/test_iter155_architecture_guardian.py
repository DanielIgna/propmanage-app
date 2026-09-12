"""Iter 155 — Architecture Guardian (PM-GUARDIAN-001/002) backend tests (HTTP, sync)."""
import os
import re
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


def test_guardian_run_endpoint(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/repair-center/architecture-guardian/run", timeout=120)
    assert r.status_code == 200
    d = r.json()
    assert 5 <= d["architecture_score"] <= 100
    assert d["files_scanned"] > 100


def test_guardian_status_endpoint(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/repair-center/architecture-guardian/status", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["last_run"] is not None
    assert isinstance(d["open_tasks"], list)
    assert isinstance(d["architecture_score"], int)


def test_guardian_requires_admin():
    r = requests.get(f"{BASE_URL}/api/admin/repair-center/architecture-guardian/status", timeout=15)
    assert r.status_code in (401, 403)


def test_no_duplicate_stripe_webhook():
    seen = {}
    for p in Path("/app/backend/routes").glob("*.py"):
        text = p.read_text(errors="ignore")
        prefixes = dict(re.findall(r"(\w+)\s*=\s*APIRouter\([^)]*prefix\s*=\s*[\"']([^\"']+)[\"']", text))
        for m in re.finditer(r"@(\w+)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", text):
            var, meth, path = m.groups()
            full = f"{meth.upper()} {prefixes.get(var, '')}{path}"
            seen.setdefault(full, []).append(p.name)
    dupes = {k: v for k, v in seen.items() if len(v) > 1}
    assert not dupes, f"Endpoint-uri duplicate: {dupes}"


def test_canonical_client_dashboard_only():
    assert not Path("/app/frontend/src/pages/ClientDashboard.jsx").exists()
    assert not Path("/app/frontend/src/pages/clientv2/ClientDashboardSwitch.jsx").exists()
    assert Path("/app/frontend/src/pages/clientv2/ClientDashboardV2.jsx").exists()


def test_house_health_webhook_wired_in_canonical_handler():
    text = Path("/app/backend/routes/payments.py").read_text()
    assert "_activate_subscription_if_paid" in text
    hh = Path("/app/backend/routes/house_health_billing.py").read_text()
    assert "webhook_router" not in hh
