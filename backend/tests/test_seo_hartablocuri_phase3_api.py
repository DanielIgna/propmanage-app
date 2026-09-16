"""Phase 3 HartaBlocuri SEO Cluster - API integration tests via external URL."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PWD = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


# ─── Pilot clusters listing ───
def test_hb_clusters_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters", timeout=30)
    assert r.status_code in (401, 403)


def test_hb_clusters_listing(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters", timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_clusters"] == 5
    assert data["prepared"] == 5
    assert data["published"] == 0
    assert data["min_buildings_index"] == 25
    clusters = data["clusters"]
    assert len(clusters) == 5
    slugs = set()
    for c in clusters:
        assert c["index"] is False
        assert c["in_sitemap"] is False
        assert c["published"] is False
        assert c["status"] == "pilot_prepared"
        assert c["indexability"] == "prepared_noindex"
        assert c["aggregates"]["building_count"] > 0, f"cluster {c['id']} has 0 buildings"
        assert c["slug"].startswith("/blocuri/cluj-napoca/")
        assert c["canonical"].endswith(c["slug"])
        slugs.add(c["slug"])
        ct = c["content"]
        assert ct["title"] and ct["meta_title"] and ct["h1"] and ct["intro"]
        assert len(ct["meta_description"]) <= 300
        assert c["provenance"]["source"] == "hartablocuri"
        assert c["provenance"]["verification_status"] == "neverificat"
        joined = " ".join(c["data_limits"]).lower()
        assert "risc seismic" in joined and "clas" in joined  # energy class disclaimer
        hrefs = {l["href"] for l in c["internal_links"]["forward"]}
        assert {"/cartea-casei", "/scorul-casei", "/digital-twin"}.issubset(hrefs)
        assert len(c["internal_links"]["related_guides"]) > 0
    assert len(slugs) == 5


def test_hb_cluster_detail(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters", timeout=60)
    cid = r.json()["clusters"][0]["id"]
    r2 = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters/{cid}", timeout=30)
    assert r2.status_code == 200
    body = r2.json()
    body = body.get("cluster", body)
    assert body["id"] == cid
    assert body["index"] is False and body["in_sitemap"] is False


def test_hb_cluster_detail_unknown(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters/does-not-exist", timeout=30)
    assert r.status_code == 404


def test_hb_cluster_detail_requires_auth():
    r = requests.get(f"{BASE_URL}/api/admin/seo/hartablocuri-clusters/cluj-panou-p4", timeout=30)
    assert r.status_code in (401, 403)


# ─── REGRESSION: existing SEO endpoints ───
def test_seo_clusters_existing_unchanged(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/clusters", timeout=30)
    assert r.status_code == 200
    data = r.json()
    # accept either dict or list shape
    items = data.get("clusters") if isinstance(data, dict) else data
    assert items is not None
    assert len(items) == 9, f"expected 9 clusters, got {len(items)}"
    hb = [c for c in items if c.get("id") == "building_hartablocuri" or c.get("name") == "building_hartablocuri"]
    assert hb, "building_hartablocuri cluster missing"
    hbc = hb[0]
    assert hbc.get("pages", 0) == 0
    assert hbc.get("in_sitemap", 0) == 0


def test_seo_pages(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/pages", timeout=30)
    assert r.status_code == 200
    d = r.json()
    total = d.get("total") if isinstance(d, dict) else len(d)
    assert total and total > 0


def test_seo_overview(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/overview", timeout=30)
    assert r.status_code == 200


def test_seo_alerts(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/seo/alerts", timeout=30)
    assert r.status_code == 200


def test_sitemap_validate(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/seo/sitemap/validate", timeout=30)
    assert r.status_code == 200
    assert r.json().get("valid") is True


# ─── CRITICAL: sitemap has NO /blocuri/ URLs ───
def test_sitemap_no_blocuri_urls():
    r = requests.get(f"{BASE_URL}/sitemap.xml", timeout=30)
    assert r.status_code == 200
    assert "/blocuri/" not in r.text
    # follow child sitemaps if index
    if "<sitemapindex" in r.text:
        import re
        for loc in re.findall(r"<loc>([^<]+)</loc>", r.text):
            rc = requests.get(loc, timeout=30)
            assert rc.status_code == 200
            assert "/blocuri/" not in rc.text, f"blocuri found in {loc}"


# ─── REGRESSION: Truth Layer public ───
def test_public_building_truth_layer():
    r = requests.get(f"{BASE_URL}/api/public/buildings/6aaabeb516469f4cdea48187", timeout=30)
    assert r.status_code == 200
    b = r.json()
    b = b.get("building", b)
    tl = b.get("truth_layer") or b.get("truthLayer")
    assert tl, "truth_layer missing"
    for k in ("era", "form", "regime", "project_family"):
        assert k in tl, f"missing {k}"
    assert "typology_profiles" in tl


def test_public_buildings_search():
    r = requests.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Cluj"}, timeout=30)
    assert r.status_code == 200
