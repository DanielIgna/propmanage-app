"""Iter100 — HartaBlocuri integration (public discovery + admin control)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://phased-document.preview.emergentagent.com"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def anon():
    return requests.Session()


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


# ============== PUBLIC ==============

def test_public_search_muscel(anon):
    r = anon.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "buildings" in data and "total" in data
    assert isinstance(data["buildings"], list)
    if data["buildings"]:
        b = data["buildings"][0]
        for k in ("id", "name", "address", "city", "neighborhood", "source", "source_label", "verification_note"):
            assert k in b, f"missing field {k} in {b}"


def test_public_search_short_query_empty(anon):
    r = anon.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "a"}, timeout=15)
    assert r.status_code == 200
    assert r.json()["buildings"] == []


def test_public_search_city_filter(anon):
    r = anon.get(f"{BASE_URL}/api/public/buildings/search", params={"city": "Cluj-Napoca", "limit": 5}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0


def test_public_cities(anon):
    r = anon.get(f"{BASE_URL}/api/public/buildings/cities", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "cities" in data and isinstance(data["cities"], list)
    assert len(data["cities"]) >= 1
    # Cluj-Napoca cel mai mare
    top = data["cities"][0]
    assert "name" in top and "count" in top
    assert top["count"] >= 1


def test_public_building_detail(anon):
    # First find one
    r = anon.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    ids = [b["id"] for b in r.json().get("buildings", [])]
    if not ids:
        pytest.skip("No Muscel building available")
    r2 = anon.get(f"{BASE_URL}/api/public/buildings/{ids[0]}", timeout=15)
    assert r2.status_code == 200
    b = r2.json()["building"]
    assert b["id"] == ids[0]
    # hartablocuri sub-object may exist
    if b.get("hartablocuri"):
        for k in ("era", "structura", "regim_inaltime", "reference_url"):
            assert k in b["hartablocuri"]


def test_public_building_detail_invalid(anon):
    r = anon.get(f"{BASE_URL}/api/public/buildings/notavalidid", timeout=15)
    assert r.status_code == 404


# ============== ADMIN ==============

def test_admin_auth_required_stats(anon):
    r = anon.get(f"{BASE_URL}/api/admin/hartablocuri/stats", timeout=15)
    assert r.status_code in (401, 403)


def test_admin_auth_required_batches(anon):
    r = anon.get(f"{BASE_URL}/api/admin/hartablocuri/batches", timeout=15)
    assert r.status_code in (401, 403)


def test_admin_auth_required_import(anon):
    r = anon.post(f"{BASE_URL}/api/admin/hartablocuri/import", json={"dry_run": True, "limit": 5}, timeout=15)
    assert r.status_code in (401, 403)


def test_admin_stats(admin):
    r = admin.get(f"{BASE_URL}/api/admin/hartablocuri/stats", timeout=15)
    assert r.status_code == 200
    d = r.json()
    for k in ("total_buildings", "with_hartablocuri", "hartablocuri_only", "matched_both_sources", "propmanage_only", "with_conflicts"):
        assert k in d
    assert d["total_buildings"] >= 3000
    assert d["with_hartablocuri"] >= 3000
    # >=2 conflicts expected per review
    assert d["with_conflicts"] >= 2, f"Expected >=2 conflicts, got {d['with_conflicts']}"


def test_admin_batches(admin):
    r = admin.get(f"{BASE_URL}/api/admin/hartablocuri/batches", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "batches" in d and isinstance(d["batches"], list)
    if d["batches"]:
        b = d["batches"][0]
        for k in ("total_records", "new_buildings", "duplicates_updated", "conflicts"):
            assert k in b, f"missing {k} in batch {b}"


def test_admin_buildings_filter_source_hartablocuri(admin):
    r = admin.get(f"{BASE_URL}/api/admin/hartablocuri/buildings",
                  params={"source": "hartablocuri", "page": 1, "page_size": 25}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] > 0
    assert d["page"] == 1 and d["page_size"] == 25
    for b in d["buildings"]:
        assert b["source"] in ("hartablocuri", "both")


def test_admin_buildings_filter_status_conflict(admin):
    r = admin.get(f"{BASE_URL}/api/admin/hartablocuri/buildings",
                  params={"status": "conflict", "page": 1, "page_size": 25}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d["buildings"], list)


def test_admin_import_idempotent_dry_run(admin):
    r = admin.post(f"{BASE_URL}/api/admin/hartablocuri/import",
                   json={"dry_run": True, "limit": 20}, timeout=60)
    assert r.status_code == 200, f"Import failed: {r.text[:300]}"
    d = r.json()
    # Expect no new, since data already imported
    assert d.get("new_buildings", 0) == 0, f"Expected 0 new_buildings, got {d.get('new_buildings')}"
    assert d.get("duplicates_updated", 0) >= 1
