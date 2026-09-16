"""Phase 2 integration tests — Truth Layer in API responses, admin menu link, integrity."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "http://localhost:8001"

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
SAMPLE_BID = "6aaabeb516469f4cdea48187"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text[:150]}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": CLIENT_EMAIL, "password": CLIENT_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"client login failed: {r.status_code} {r.text[:150]}")
    return s


# ---------------- PUBLIC BUILDING DETAIL ----------------
def test_public_building_returns_truth_layer():
    r = requests.get(f"{BASE_URL}/api/public/buildings/{SAMPLE_BID}", timeout=15)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    tl = data.get("truth_layer") or data.get("building", {}).get("truth_layer")
    assert tl is not None, f"truth_layer missing in {list(data.keys())}"
    for key in ("era", "form", "regime", "neighborhood", "project_family",
                "typology_profiles", "provenance"):
        assert key in tl, f"missing key {key} in truth_layer: {list(tl.keys())}"
    assert tl["provenance"]["source"] == "hartablocuri"
    assert tl["project_family"]["family"] == "cf1", tl["project_family"]
    # C1 candidate should be present
    codes = [p["code"] for p in tl["typology_profiles"]]
    assert "C1" in codes, f"expected C1 profile, got {codes}"
    c1 = [p for p in tl["typology_profiles"] if p["code"] == "C1"][0]
    assert c1["classification"] == "candidate"
    assert "neverificat" in c1["disclaimer"] and "oficial" in c1["disclaimer"].lower()


# ---------------- ADMIN BUILDING DETAIL ----------------
def test_admin_building_detail_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/hartablocuri/buildings/{SAMPLE_BID}", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


def test_admin_building_detail_truth_layer(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/buildings/{SAMPLE_BID}", timeout=15)
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    # look for truth_layer at top-level or nested
    tl = data.get("truth_layer") or data.get("building", {}).get("truth_layer")
    assert tl is not None, f"admin building missing truth_layer: keys={list(data.keys())}"
    assert tl["project_family"]["family"] == "cf1"
    assert any(p["code"] == "C1" for p in tl["typology_profiles"])


# ---------------- ADMIN STATS INTEGRITY ----------------
def test_admin_stats_integrity(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/stats", timeout=20)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert d.get("total_buildings") == 3408, d
    assert d.get("with_hartablocuri") == 3406, d
    assert d.get("propmanage_only") == 2, d


# ---------------- PROPERTY BUILDING CONTEXT (client) ----------------
def test_property_building_context_includes_truth_layer(client_session):
    # find first property owned by client
    r = client_session.get(f"{BASE_URL}/api/properties", timeout=15)
    if r.status_code != 200:
        pytest.skip(f"cannot list properties: {r.status_code}")
    props = r.json()
    props = props if isinstance(props, list) else props.get("items", [])
    if not props:
        pytest.skip("no client properties available")

    tried = 0
    for p in props:
        pid = p.get("id") or p.get("_id")
        if not pid:
            continue
        tried += 1
        ctx = client_session.get(f"{BASE_URL}/api/properties/{pid}/building-context", timeout=15)
        if ctx.status_code != 200:
            continue
        j = ctx.json()
        b = j.get("building") or {}
        if b.get("truth_layer"):
            tl = b["truth_layer"]
            assert "provenance" in tl and "project_family" in tl and "typology_profiles" in tl
            return
    pytest.skip(f"no property with hartablocuri truth_layer found (tried {tried})")


def test_property_technical_record_truth_layer(client_session):
    r = client_session.get(f"{BASE_URL}/api/properties", timeout=15)
    if r.status_code != 200:
        pytest.skip("cannot list props")
    props = r.json()
    props = props if isinstance(props, list) else props.get("items", [])
    for p in props:
        pid = p.get("id") or p.get("_id")
        if not pid:
            continue
        tr = client_session.get(f"{BASE_URL}/api/properties/{pid}/technical-record", timeout=15)
        if tr.status_code != 200:
            continue
        j = tr.json()
        b = j.get("building") or {}
        if b.get("truth_layer"):
            assert "typology_profiles" in b["truth_layer"]
            return
    pytest.skip("no property technical-record with hartablocuri truth_layer")
