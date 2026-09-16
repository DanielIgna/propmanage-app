"""Iter223 — HartaBlocuri Observability (READ-ONLY) tests."""
import os
import re
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT)


# --- Auth guard ---
def test_stats_requires_admin(client_s):
    r = client_s.get(f"{BASE}/api/admin/hartablocuri/stats", timeout=15)
    assert r.status_code == 403


def test_list_requires_admin(client_s):
    r = client_s.get(f"{BASE}/api/admin/hartablocuri/buildings", timeout=15)
    assert r.status_code == 403


def test_detail_requires_admin(client_s):
    # random ObjectId-like
    r = client_s.get(f"{BASE}/api/admin/hartablocuri/buildings/6aaab20641ed4e462d83b767", timeout=15)
    assert r.status_code == 403


# --- Stats overview ---
def test_stats_overview_counts(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/hartablocuri/stats", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ["total_buildings", "with_hartablocuri", "propmanage_only",
              "localities", "neighborhoods", "with_construction_year",
              "with_floors", "with_units", "incomplete", "matched_both_sources"]:
        assert k in d, f"missing key: {k}"
        assert isinstance(d[k], int) and d[k] >= 0
    # DB expected state per problem statement
    assert d["total_buildings"] >= 3400, f"expected ~3407, got {d['total_buildings']}"
    assert d["with_hartablocuri"] >= 3400
    assert d["propmanage_only"] >= 1
    # Consistency check
    assert d["with_hartablocuri"] + d["propmanage_only"] == d["total_buildings"]
    print(f"Stats: total={d['total_buildings']} hb={d['with_hartablocuri']} pm={d['propmanage_only']} "
          f"loc={d['localities']} nbh={d['neighborhoods']} incomplete={d['incomplete']}")


# --- Buildings list ---
def test_list_default_pagination(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "buildings" in d and "total" in d and "page" in d and "page_size" in d
    assert d["page"] == 1 and d["page_size"] == 25
    assert d["total"] >= 3400
    assert len(d["buildings"]) <= 25
    b = d["buildings"][0]
    for k in ["id", "name", "address", "city", "neighborhood",
              "construction_year", "floors", "units", "source",
              "verification_status", "residents_count"]:
        assert k in b, f"missing field {k} in building"


def test_list_source_filter_hartablocuri(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings",
                    params={"source": "hartablocuri", "page_size": 10}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for b in d["buildings"]:
        assert b["source"] in ("hartablocuri", "both")


def test_list_source_filter_propmanage(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings",
                    params={"source": "propmanage", "page_size": 10}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for b in d["buildings"]:
        assert b["source"] == "propmanage"


def test_list_search_q(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings",
                    params={"q": "Muscel", "page_size": 5}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    # verify at least one row mentions Muscel
    joined = " ".join((b.get("address") or "") + " " + (b.get("name") or "") for b in d["buildings"])
    assert re.search("muscel", joined, re.I)


def test_list_pagination_page2(admin_s):
    r1 = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings",
                     params={"page": 1, "page_size": 5}, timeout=30)
    r2 = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings",
                     params={"page": 2, "page_size": 5}, timeout=30)
    assert r1.status_code == 200 and r2.status_code == 200
    ids1 = {b["id"] for b in r1.json()["buildings"]}
    ids2 = {b["id"] for b in r2.json()["buildings"]}
    assert not (ids1 & ids2), "page 2 must not overlap page 1"


# --- Detail ---
def test_building_detail(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings",
                    params={"source": "hartablocuri", "page_size": 1}, timeout=30)
    assert r.status_code == 200
    bid = r.json()["buildings"][0]["id"]
    d = admin_s.get(f"{BASE}/api/admin/hartablocuri/buildings/{bid}", timeout=15)
    assert d.status_code == 200
    j = d.json()
    for k in ["id", "name", "address", "context", "source", "verification_status", "residents_count"]:
        assert k in j
    # hartablocuri key present (may be None for pm-only)
    assert "hartablocuri" in j


# --- Regressions ---
def test_regression_public_search():
    r = requests.get(f"{BASE}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1 and len(d["buildings"]) >= 1


def test_regression_sitemap_no_building_urls():
    r = requests.get(f"{BASE}/api/public/sitemap.xml", timeout=20)
    assert r.status_code == 200
    body = r.text
    # No building-specific public routes should be added
    for bad in ["/blocuri/", "/cladiri/", "/cluj/bloc/"]:
        assert bad not in body, f"unexpected building URL prefix {bad} present in sitemap"
    n_urls = body.count("<loc>")
    print(f"Sitemap URLs: {n_urls}")
    assert n_urls < 3000, f"sitemap size exploded to {n_urls} — likely includes HB buildings"


def test_regression_seo_overview(admin_s):
    r = admin_s.get(f"{BASE}/api/admin/seo/overview", timeout=20)
    assert r.status_code == 200
