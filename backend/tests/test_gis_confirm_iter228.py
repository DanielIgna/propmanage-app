"""
Iter 228 — GIS map unify + building-confirmation regression tests.
Covers:
 - Public/private boundary for /api/properties/{id}/gis
 - Public HartaBlocuri /api/public/blocuri/map & /api/public/maps/config
 - /api/buildings/search (PTR search) fields
 - sitemap-blocuri.xml
 - Verified estate public listings
"""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PWD = "Client123!"
SPEC_EMAIL = "specialist@propmanage.io"
SPEC_PWD = "Spec123!"
PROP_ID = "6a11d70e600be19667009c93"


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": email, "password": pwd}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT_EMAIL, CLIENT_PWD)


@pytest.fixture(scope="module")
def spec_sess():
    return _login(SPEC_EMAIL, SPEC_PWD)


# ---------- Property GIS boundary ----------
def test_gis_no_auth_returns_401():
    r = requests.get(f"{BASE_URL}/api/properties/{PROP_ID}/gis", timeout=20)
    assert r.status_code == 401, f"expected 401 got {r.status_code}"


def test_gis_non_owner_returns_403(spec_sess):
    r = spec_sess.get(f"{BASE_URL}/api/properties/{PROP_ID}/gis", timeout=20)
    assert r.status_code == 403, f"expected 403 got {r.status_code} body={r.text[:200]}"


def test_gis_owner_returns_location(client_sess):
    r = client_sess.get(f"{BASE_URL}/api/properties/{PROP_ID}/gis", timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    # location may be nested under 'location' or top-level
    loc = data.get("location") or data
    lat = loc.get("lat")
    lng = loc.get("lng")
    assert lat is not None and lng is not None, f"no lat/lng in {data}"
    assert abs(float(lat) - 46.76485) < 0.001, f"lat={lat}"
    assert abs(float(lng) - 23.603) < 0.001, f"lng={lng}"


# ---------- Public HartaBlocuri ----------
def test_public_blocuri_map_aggregated_no_exact_coords():
    r = requests.get(f"{BASE_URL}/api/public/blocuri/map",
                     params={"city": "Cluj-Napoca"}, timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    areas = data.get("areas") if isinstance(data, dict) else data
    assert isinstance(areas, list), f"expected areas list, got {type(areas)}"
    for a in areas:
        if "approximate" in a:
            assert a["approximate"] is True
        # verify centroid does NOT expose exact building coords
        lat = a.get("lat") or a.get("centroid_lat")
        lng = a.get("lng") or a.get("centroid_lng")
        if lat is not None and lng is not None:
            assert not (abs(float(lat) - 46.76485) < 0.0001 and
                        abs(float(lng) - 23.603) < 0.0001), \
                f"exact building coord leaked in {a}"


def test_public_maps_config_fallback():
    r = requests.get(f"{BASE_URL}/api/public/maps/config", timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    assert data.get("provider") == "fallback", f"provider={data.get('provider')}"
    assert data.get("enabled") is False, f"enabled={data.get('enabled')}"
    assert data.get("api_key") in (None, ""), f"api_key leaked={data.get('api_key')}"


# ---------- PTR building search ----------
def test_buildings_search_full_address(client_sess):
    r = client_sess.get(f"{BASE_URL}/api/buildings/search",
                        params={"q": "Aleea Muscel nr. 19"}, timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    items = data.get("results") or data.get("items") or data if isinstance(data, list) else data.get("results", [])
    if isinstance(data, dict) and not items:
        items = data.get("buildings", [])
    assert isinstance(items, list) and len(items) > 0, f"empty results: {data}"
    # find Bloc A1 at Cluj
    target = None
    for it in items:
        name = (it.get("name") or "").lower()
        addr = (it.get("address") or "").lower()
        if "bloc a1" in name or ("aleea muscel" in addr and "19" in addr):
            target = it
            break
    assert target, f"Bloc A1 not found in {items}"
    for k in ("id", "name", "address", "city", "lat", "lng",
              "source", "provenance", "match_confidence"):
        assert k in target, f"missing {k} in {target}"
    assert target["source"] == "hartablocuri"
    assert target["match_confidence"] == "high"
    assert isinstance(target["provenance"], str) and target["provenance"].strip()
    assert abs(float(target["lat"]) - 46.76485) < 0.001
    assert abs(float(target["lng"]) - 23.603) < 0.001


# ---------- SEO sitemap ----------
def test_sitemap_blocuri():
    # sitemap is served at root, not under /api
    r = requests.get(f"{BASE_URL}/sitemap-blocuri.xml", timeout=20)
    assert r.status_code == 200, f"status={r.status_code}"
    body = r.text
    locs = re.findall(r"<loc>", body)
    assert len(locs) >= 30, f"only {len(locs)} <loc> entries"


# ---------- Public verified-estate listings ----------
def test_verified_estate_public_listings():
    r = requests.get(f"{BASE_URL}/api/verified-estate/listings", timeout=20)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    items = data if isinstance(data, list) else (data.get("listings") or data.get("items") or [])
    assert isinstance(items, list) and len(items) > 0, f"no listings: {data}"
    with_coords = [x for x in items if x.get("lat") and x.get("lng")]
    assert len(with_coords) > 0, "no listings have lat/lng"
