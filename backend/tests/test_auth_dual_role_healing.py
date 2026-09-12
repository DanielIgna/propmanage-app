"""Regression tests for auth dual-role self-healing logic.

Covers the bug where a client had `dual_role_enabled=True, active_view='specialist'`
in the DB without an actual specialist profile, which caused the frontend dashboard
guard to bounce the user to the wrong dashboard.
"""
import asyncio
import os
import requests
from dotenv import load_dotenv
from tests.test_config import OWNER_ADMIN_PASSWORD
load_dotenv('/app/backend/.env')

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, r.text
    return s


def _corrupt_dual_role(email: str):
    async def _do():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = c[os.environ["DB_NAME"]]
        await db.users.update_one(
            {"email": email},
            {"$set": {"dual_role_enabled": True, "active_view": "specialist"},
             "$unset": {"service_categories": "", "coverage_zones": "", "specialist_onboarded_at": "", "specialist_profile_id": ""}},
        )
    asyncio.run(_do())


def _read_user(email: str):
    async def _do():
        from motor.motor_asyncio import AsyncIOMotorClient
        c = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = c[os.environ["DB_NAME"]]
        return await db.users.find_one(
            {"email": email},
            {"role": 1, "active_view": 1, "dual_role_enabled": 1, "_id": 0},
        )
    return asyncio.run(_do())


def test_me_self_heals_invalid_dual_role_state():
    _corrupt_dual_role("client@propmanage.io")
    s = _login("client@propmanage.io", "Client123!")
    r = s.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "client"
    assert body["active_view"] == "client"
    assert body["dual_role_enabled"] is False
    db_state = _read_user("client@propmanage.io")
    assert db_state["dual_role_enabled"] is False
    assert db_state["active_view"] == "client"


def test_switch_view_blocks_without_specialist_profile():
    _corrupt_dual_role("client@propmanage.io")
    s = _login("client@propmanage.io", "Client123!")
    # Re-corrupt after login (cookie issued) to bypass /me self-heal
    _corrupt_dual_role("client@propmanage.io")
    r = s.post(f"{BASE_URL}/api/auth/switch-view", json={"view": "specialist"})
    assert r.status_code == 403, r.text
    db_state = _read_user("client@propmanage.io")
    assert db_state["dual_role_enabled"] is False


def test_admin_login_not_affected():
    s = _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
    r = s.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    assert r.json()["role"] == "admin"


def test_specialist_login_keeps_role():
    s = _login("specialist@propmanage.io", "Spec123!")
    r = s.get(f"{BASE_URL}/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "specialist"
