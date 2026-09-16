"""Phase 4 HartaBlocuri National SEO + Map + Business Engine — API integration tests."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"
SAMPLE_BUILDING_ID = "6aaabeb516469f4cdea48187"
INDEX_SLUG = "/blocuri/cluj/cluj-napoca"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed {r.status_code}: {r.text[:200]}"
    return s


# ---------- Admin: hartablocuri-clusters summary ----------
class TestAdminHartaClusters:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters", timeout=30)
        assert r.status_code in (401, 403)

    def test_summary(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters", timeout=30)
        assert r.status_code == 200
        data = r.json()
        s = data.get("summary") or data
        assert s.get("total") == 166, f"total {s.get('total')}"
        assert s.get("index") == 66
        assert s.get("prepared") == 41
        assert s.get("candidate") == 59
        assert s.get("blocked") == 0
        assert s.get("in_sitemap") == 66
        assert "Cluj" in (s.get("counties") or [])
        clusters = data.get("clusters", [])
        assert len(clusters) == 166
        # county-agnostic slugs
        for c in clusters[:20]:
            slug = c.get("slug") or c.get("canonical") or ""
            assert slug.startswith("/blocuri/cluj"), f"bad slug {slug}"

    def test_state_guarantee(self, admin_session):
        """Only INDEX has index=true AND in_sitemap=true."""
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters", timeout=30)
        clusters = r.json().get("clusters", [])
        for c in clusters:
            st = c.get("state")
            idx = c.get("index")
            sm = c.get("in_sitemap")
            if st == "INDEX":
                assert idx is True and sm is True, f"INDEX cluster missing flags: {c.get('slug')}"
            else:
                assert idx is False and sm is False, f"{st} cluster leaked: {c.get('slug')} idx={idx} sm={sm}"

    def test_filter_state_index(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters?state=INDEX", timeout=30)
        assert r.status_code == 200
        cs = r.json().get("clusters", [])
        assert len(cs) == 66
        assert all(c.get("state") == "INDEX" for c in cs)

    def test_filter_state_prepared(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters?state=PREPARED", timeout=30)
        cs = r.json().get("clusters", [])
        assert len(cs) == 41

    def test_filter_county(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters?county=Cluj", timeout=30)
        assert r.status_code == 200
        assert len(r.json().get("clusters", [])) == 166

    def test_filter_dimension(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters?dimension=locality_typology", timeout=30)
        assert r.status_code == 200
        cs = r.json().get("clusters", [])
        assert len(cs) > 0
        assert all(c.get("dimension") == "locality_typology" for c in cs)


# ---------- Admin: cluster detail ----------
class TestAdminClusterDetail:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters/detail?slug={INDEX_SLUG}", timeout=30)
        assert r.status_code in (401, 403)

    def test_detail_index(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters/detail?slug={INDEX_SLUG}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        cl = d.get("cluster") or d
        assert cl.get("state") == "INDEX"
        assert cl.get("content") is not None
        assert cl.get("aggregates") is not None or cl.get("stats") is not None

    def test_detail_unknown(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters/detail?slug=/blocuri/xx/nope-nope", timeout=30)
        assert r.status_code == 404


# ---------- Public: Map config ----------
class TestPublicMap:
    def test_maps_config(self):
        r = requests.get(f"{BASE_URL}/api/public/maps/config", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("provider") == "fallback"
        assert d.get("enabled") is False
        assert d.get("fallback") is True

    def test_map_markers(self):
        r = requests.get(f"{BASE_URL}/api/public/blocuri/map?city=Cluj-Napoca&limit=5000", timeout=30)
        assert r.status_code == 200
        d = r.json()
        markers = d.get("markers") or d.get("items") or []
        assert 2200 <= len(markers) <= 2320, f"markers count {len(markers)}"
        m0 = markers[0]
        assert "lat" in m0 and "lng" in m0
        assert m0.get("href", "").startswith("/blocuri/cladire/")

    def test_map_filter_typology(self):
        r = requests.get(f"{BASE_URL}/api/public/blocuri/map?typology=C1&limit=5000", timeout=30)
        assert r.status_code == 200
        markers = r.json().get("markers") or r.json().get("items") or []
        assert 1080 <= len(markers) <= 1160, f"C1 markers {len(markers)}"


# ---------- Public clusters ----------
class TestPublicClusters:
    def test_only_index(self):
        r = requests.get(f"{BASE_URL}/api/public/blocuri/clusters", timeout=30)
        assert r.status_code == 200
        cs = r.json().get("clusters") or r.json().get("items") or []
        assert len(cs) == 66

    def test_public_cluster_index_ok(self):
        r = requests.get(f"{BASE_URL}/api/public/blocuri/cluster?slug={INDEX_SLUG}", timeout=30)
        assert r.status_code == 200

    def test_public_cluster_non_index_404(self):
        # Try a few candidate slugs to find a non-INDEX one
        for slug in ["/blocuri/cluj/gilau", "/blocuri/cluj/floresti-c2", "/blocuri/cluj/apahida"]:
            r = requests.get(f"{BASE_URL}/api/public/blocuri/cluster?slug={slug}", timeout=30)
            if r.status_code == 404:
                return
        pytest.fail("No non-INDEX slug returned 404")


# ---------- Public building detail ----------
class TestPublicBuilding:
    def test_building_enriched(self):
        r = requests.get(f"{BASE_URL}/api/public/buildings/{SAMPLE_BUILDING_ID}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        b = d.get("building") or d
        assert b.get("truth_layer") is not None
        assert b.get("lat") is not None
        assert b.get("lng") is not None
        assert b.get("county") is not None
        assert b.get("monetization") is not None
        assert b.get("cta") is not None
        assert b.get("google_maps_url") is not None


# ---------- Sitemap ----------
class TestSitemap:
    def test_sitemap_blocuri(self):
        r = requests.get(f"{BASE_URL}/api/public/sitemap-blocuri.xml", timeout=30)
        assert r.status_code == 200
        xml = r.text
        locs = re.findall(r"<loc>([^<]+)</loc>", xml)
        assert len(locs) == 66, f"sitemap-blocuri.xml has {len(locs)} locs"
        for l in locs:
            assert "/blocuri/cluj" in l, f"non-cluj loc: {l}"

    def test_sitemap_index_has_blocuri(self):
        r = requests.get(f"{BASE_URL}/api/public/sitemap-index.xml", timeout=30)
        assert r.status_code == 200
        xml = r.text
        assert "sitemap-blocuri.xml" in xml
        # 7 children
        locs = re.findall(r"<loc>([^<]+)</loc>", xml)
        assert len(locs) == 7, f"sitemap-index children: {len(locs)}"

    def test_marketplace_unchanged(self):
        r = requests.get(f"{BASE_URL}/api/public/sitemap-marketplace.xml", timeout=30)
        assert r.status_code == 200
        locs = re.findall(r"<loc>", r.text)
        assert len(locs) == 7, f"marketplace regressed: {len(locs)}"


# ---------- Regression ----------
class TestRegression:
    def test_seo_overview(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/overview", timeout=30)
        assert r.status_code == 200
        d = r.json()
        sm = d.get("sitemap") or {}
        assert sm.get("child_count") == 7, f"child_count={sm.get('child_count')}"
        health = d.get("health") or {}
        assert health.get("gate_ok") is True

    def test_sitemap_validate(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/seo/sitemap/validate", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("valid") is True

    def test_legacy_clusters(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/seo/clusters", timeout=30)
        assert r.status_code == 200
        cs = r.json().get("clusters") or r.json().get("items") or []
        assert len(cs) == 9, f"legacy clusters {len(cs)}"
