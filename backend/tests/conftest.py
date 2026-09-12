"""Session-wide pytest fixtures for PropManage test suite.

Goal: eliminate state leakage between tests by re-baselining demo accounts at
session start. This makes the full pytest suite reliable even after multiple
runs have mutated wallet balances, tokens, escrow, etc.
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD


BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


@pytest.fixture(scope="session", autouse=True)
def reset_demo_state():
    """Idempotently reset demo accounts to their baseline BEFORE the test session
    runs. Safe to call any time — won't destroy non-demo data.
    """
    try:
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
        if r.status_code != 200:
            # Admin login failed — likely backend not reachable; skip silently.
            yield
            return
        r2 = s.post(f"{API}/admin/demo/reset", timeout=20)
        if r2.status_code != 200:
            # Reset endpoint may not be deployed yet — don't block tests.
            print(f"[conftest] demo reset returned {r2.status_code}: {r2.text[:200]}")
    except Exception as e:  # pragma: no cover
        print(f"[conftest] demo reset failed: {e}")
    yield
    # No teardown — the nightly cron handles the next reset.
