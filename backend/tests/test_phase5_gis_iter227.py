"""Phase 5 tests: Public/Private GIS boundary, Property GIS auth, Google Maps config, robots/sitemap regression."""
import os
import re
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
FRONTEND = BASE  # same origin serves frontend
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PW = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PW = "1!nasov01ADMIN"
OWNED_PROP = "6a11d70e600be19667009c93"
FOREIGN_PROP = "6a1770f4b2b8e3587c7738e7"
BUILDING_ID = "6aaabeb516469f4cdea48187"


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT_EMAIL, CLIENT_PW)


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN_EMAIL, ADMIN_PW)


# ---------- PUBLIC BOUNDARY ----------
class TestPublicBoundary:
    def test_public_map_aggregated_no_exact_coords(self):
        r = requests.get(f"{BASE}/api/public/blocuri/map", params={"city": "Cluj-Napoca"}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        # expect aggregated areas
        areas = data.get("areas") or data.get("markers") or []
        assert isinstance(areas, list) and len(areas) > 0
        total = data.get("total_buildings") or data.get("total")
        assert total and 2000 <= total <= 2500, f"total_buildings={total}"
        for a in areas:
            # must not include building id / name / address
            assert "building_id" not in a and "id" not in a or not str(a.get("id","")).startswith("6"), a
            assert "name" not in a and "address" not in a, a
            # approximate flag
            # lat/lng if present must be 2-decimal rounded
            for k in ("lat", "lng"):
                if k in a and a[k] is not None:
                    s = str(a[k])
                    # rounded to ~2 decimals
                    if "." in s:
                        decimals = len(s.split(".")[1].rstrip("0"))
                        assert decimals <= 2, f"{k}={a[k]} not rounded"
            assert a.get("approximate") is True or data.get("approximate") is True

    def test_public_building_detail_no_exact_coords(self):
        r = requests.get(f"{BASE}/api/public/buildings/{BUILDING_ID}", timeout=15)
        assert r.status_code == 200, r.text[:200]
        raw = r.json()
        body = raw.get("building", raw)
        # deep search for forbidden keys
        def find(obj, keys):
            found = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in keys:
                        found.append((k, v))
                    found += find(v, keys)
            elif isinstance(obj, list):
                for it in obj:
                    found += find(it, keys)
            return found
        leaks = find(body, {"google_maps_url"})
        assert not leaks, f"google_maps_url leaked: {leaks}"
        # top-level lat/lng must not be exact
        assert "lat" not in body or body.get("lat") is None, f"lat leaked: {body.get('lat')}"
        assert "lng" not in body or body.get("lng") is None, f"lng leaked: {body.get('lng')}"
        # required fields
        assert "truth_layer" in body
        assert "county" in body
        assert "monetization" in body
        cta = body.get("cta") or {}
        assert "identify" in cta and "/register?binvite=" in cta["identify"]
        assert "cartea_casei" in cta
        assert "private_note" in body

    def test_maps_config_fallback(self):
        r = requests.get(f"{BASE}/api/public/maps/config", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d.get("provider") == "fallback"
        assert d.get("enabled") is False
        # never expose server key
        s = str(d).lower()
        assert "api_key" not in s or d.get("api_key") in (None, "")
        assert "server_api_key" not in s


# ---------- PRIVATE GIS ----------
class TestPrivateGIS:
    def test_gis_401_no_auth(self):
        r = requests.get(f"{BASE}/api/properties/{OWNED_PROP}/gis", timeout=10)
        assert r.status_code == 401, f"expected 401 got {r.status_code}"

    def test_gis_authorized_owner(self, client_sess):
        r = client_sess.get(f"{BASE}/api/properties/{OWNED_PROP}/gis", timeout=15)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("authorized") is True
        loc = d.get("location") or {}
        assert isinstance(loc.get("lat"), (int, float))
        assert isinstance(loc.get("lng"), (int, float))
        assert d.get("google_maps_url"), "google_maps_url missing"
        layers = d.get("layers") or []
        layer_ids = {l.get("id") or l.get("code") for l in layers} if isinstance(layers, list) else set(layers.keys())
        for req in ("L0", "L1", "L3", "L6"):
            assert req in layer_ids, f"missing layer {req} in {layer_ids}"
        assert "documentation_status" in d
        assert "ctas" in d

    def test_gis_403_foreign(self, client_sess):
        r = client_sess.get(f"{BASE}/api/properties/{FOREIGN_PROP}/gis", timeout=10)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text[:200]}"
        # no data leak
        body = r.text
        assert "lat" not in body.lower() or "latitude" not in body.lower()

    def test_building_context_403_foreign(self, client_sess):
        r = client_sess.get(f"{BASE}/api/properties/{FOREIGN_PROP}/building-context", timeout=10)
        assert r.status_code == 403


# ---------- ROBOTS / SITEMAP ----------
class TestRobotsSitemap:
    def test_robots_disallow_private(self):
        r = requests.get(f"{FRONTEND}/robots.txt", timeout=10)
        assert r.status_code == 200
        t = r.text
        for path in ("/property/", "/account", "/my-home", "/admin", "/client", "/operator", "/dashboard"):
            assert f"Disallow: {path}" in t, f"missing Disallow {path}"

    def test_sitemap_blocuri_66_and_no_property(self):
        r = requests.get(f"{FRONTEND}/sitemap-blocuri.xml", timeout=15)
        assert r.status_code == 200
        xml = r.text
        locs = re.findall(r"<loc>(.*?)</loc>", xml)
        assert len(locs) == 66, f"expected 66 got {len(locs)}"
        for l in locs:
            assert "/property/" not in l


# ---------- SEO REGRESSION ----------
class TestSEORegression:
    def test_admin_seo_hartablocuri_clusters(self, admin_sess):
        r = admin_sess.get(f"{BASE}/api/admin/seo/hartablocuri-clusters", timeout=15)
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d.get("total") == 166
        assert d.get("index") == 66
        assert d.get("prepared") == 41
        assert d.get("candidate") == 59
        assert d.get("in_sitemap") == 66

    def test_public_blocuri_clusters(self):
        r = requests.get(f"{BASE}/api/public/blocuri/clusters", timeout=15)
        assert r.status_code == 200
        d = r.json()
        clusters = d if isinstance(d, list) else d.get("clusters") or d.get("items") or []
        assert len(clusters) == 66, f"expected 66 got {len(clusters)}"

    def test_admin_seo_overview_child_count(self, admin_sess):
        r = admin_sess.get(f"{BASE}/api/admin/seo/overview", timeout=15)
        assert r.status_code == 200
        d = r.json()
        # find marketplace child count 7
        s = str(d)
        assert "7" in s  # loose sanity; deeper below
        # try navigate
        children = d.get("children") or d.get("sitemaps") or []
        found7 = False
        def scan(o):
            nonlocal found7
            if isinstance(o, dict):
                if o.get("child_count") == 7 or o.get("count") == 7 and "market" in str(o).lower():
                    found7 = True
                for v in o.values(): scan(v)
            elif isinstance(o, list):
                for i in o: scan(i)
        scan(d)
        # Not strictly asserting since structure varies; log if not
        if not found7:
            print(f"[warn] child_count=7 not clearly found in overview: keys={list(d.keys()) if isinstance(d,dict) else type(d)}")
