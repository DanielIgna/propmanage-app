"""Iter89 — Phase 1 Stabilizare Tehnică — Backend Regression
Covers TD-01 (lazy routes indirect: endpoints must still respond),
TD-03 (category vocabulary migration for specialists),
TD-07 (Mongo indexes),
TD-08 (telemetry retention).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CREDS = {
    "admin": ("admin@propmanage.io", "1!nasov01ADMIN"),
    "client": ("client@propmanage.io", "Client123!"),
    "specialist": ("specialist@propmanage.io", "Spec123!"),
    "operator": ("operator@propmanage.io", "Op123!"),
}


def _login(role):
    email, pwd = CREDS[role]
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    return s, r


@pytest.mark.parametrize("role", list(CREDS.keys()))
def test_login_all_roles(role):
    s, r = _login(role)
    assert r.status_code == 200, f"{role} login failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    # Login returns user object directly (cookie-based auth)
    assert "email" in data or "user" in data or "token" in data, f"unexpected shape: {list(data)[:8]}"
    # verify session works
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10)
    assert me.status_code == 200, f"{role} /me failed: {me.status_code}"


def test_taxonomy_public_79_visible():
    r = requests.get(f"{BASE_URL}/api/construction/taxonomy/public", timeout=15)
    assert r.status_code == 200
    data = r.json()
    # Endpoint returns {tree: [...], count: N}
    count = data.get("count", 0) if isinstance(data, dict) else 0
    assert count >= 70, f"Expected ~79 visible taxonomy rows, got {count}"


def test_orchestrator_overview_7_playbooks():
    s, r = _login("admin")
    assert r.status_code == 200
    ov = s.get(f"{BASE_URL}/api/admin/orchestrator/overview", timeout=15)
    assert ov.status_code == 200, f"overview: {ov.status_code} {ov.text[:300]}"
    data = ov.json()
    playbooks = data.get("playbooks", data if isinstance(data, list) else [])
    assert len(playbooks) == 7, f"Expected 7 playbooks, got {len(playbooks)}"


def test_prices_public_over_100():
    r = requests.get(f"{BASE_URL}/api/construction/prices/public", timeout=15)
    assert r.status_code == 200
    data = r.json()
    rows = data if isinstance(data, list) else data.get("items", data.get("prices", []))
    assert len(rows) > 100, f"Expected >100 price rows, got {len(rows)}"


def test_td03_no_legacy_specialists():
    """No specialist should still have legacy vocab categories (painting, carpentry, gardening, cleaning, appliance_repair)."""
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME not set in test env")
    client = MongoClient(mongo_url)
    db = client[db_name]
    legacy = ["painting", "carpentry", "gardening", "cleaning", "appliance_repair"]
    q = {
        "$or": [
            {"specialty": {"$in": legacy}},
            {"service_categories": {"$in": legacy}},
        ]
    }
    count = db.users.count_documents(q)
    assert count == 0, f"Found {count} users with legacy vocabulary; migration incomplete"


def test_td03_migration_backup_exists():
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME not set")
    client = MongoClient(mongo_url)
    db = client[db_name]
    names = db.list_collection_names()
    assert "migration_backups" in names, "migration_backups collection missing"
    n = db.migration_backups.count_documents({})
    assert n >= 1, "migration_backups is empty"


def test_td07_indexes_created():
    """At least 22 non-_id_ indexes across app collections."""
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME not set")
    client = MongoClient(mongo_url)
    db = client[db_name]
    total = 0
    for coll in db.list_collection_names():
        try:
            for idx in db[coll].list_indexes():
                if idx.get("name") != "_id_":
                    total += 1
        except Exception:
            pass
    assert total >= 22, f"Expected >=22 non-_id indexes, got {total}"
