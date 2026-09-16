"""Design Interior routing + 'homepage flash' investigation guard (iter 219).

Root cause of the perceived homepage flash on /design-interior is a BENIGN SPA
init artifact: the static index.html shell carries the homepage title/meta/canonical
("Cartea Digitală a Casei Tale"), which is visible for a few hundred ms while the JS
bundle boots — there is NO homepage BODY, NO HTTP redirect, and the URL never changes
to "/". After render, useSEO swaps in the correct DI title/canonical/robots.

This test locks in the deterministic (server + gate + sitemap) layer so that a future
route removal/reorder (which would make the catch-all `Navigate to="/"` genuinely
redirect these URLs to the homepage) is caught.
"""
import os
import re
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}

DI_ROUTES = [
    "/design-interior",
    "/design-interior/apartament",
    "/design-interior/pret",
    "/design-interior/stil/japandi",
    "/design-interior/cluj-napoca",
]


def test_direct_navigation_no_redirect_serves_spa_shell():
    """Direct navigation to DI routes returns 200 SPA shell — no HTTP redirect to homepage."""
    for path in DI_ROUTES:
        r = requests.get(f"{BASE_URL}{path}", timeout=20, allow_redirects=False)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        # SPA shell: empty #root, no homepage BODY rendered server-side
        assert '<div id="root"></div>' in r.text, f"{path}: expected empty SPA root"
        # the only 'Cartea Digitală' occurrences are static <head> meta (homepage default),
        # never rendered homepage body sections
        assert "Harta Casei" not in r.text, f"{path}: homepage body leaked into shell"


def test_gate_editorial_index_vs_gated_city_noindex():
    """Editorial DI pages -> index (self). Local city pages: INDEX if they have
    unique authored content (cluj-napoca), NOINDEX + parent canonical if generic (oradea)."""
    ap = requests.get(f"{API}/public/seo/gate", params={"path": "/design-interior/apartament"}, timeout=15).json()
    assert ap["index"] is True

    # cluj-napoca now has unique authored local content -> INDEX + self-canonical
    cluj = requests.get(f"{API}/public/seo/gate", params={"path": "/design-interior/cluj-napoca"}, timeout=15).json()
    assert cluj["index"] is True

    # oradea has NO authored content -> NOINDEX + canonical to parent
    oradea = requests.get(f"{API}/public/seo/gate", params={"path": "/design-interior/oradea"}, timeout=15).json()
    assert oradea["index"] is False
    assert oradea["canonical"] == "https://propmanage.ro/design-interior"


def test_sitemap_design_has_pages_styles_and_only_content_cities():
    """sitemap-design.xml = 14 pages + 9 styles + ONLY cities with authored content."""
    r = requests.get(f"{API}/public/sitemap-design.xml", timeout=20)
    assert r.status_code == 200 and "<urlset" in r.text
    locs = {re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", r.text)}
    # content + style pages always present
    assert "/design-interior/apartament" in locs
    assert "/design-interior/stil/japandi" in locs
    # cities with authored unique content are present
    assert "/design-interior/cluj-napoca" in locs, "content city should be in sitemap"
    assert "/design-interior/bucuresti" in locs, "content city should be in sitemap"
    # cities WITHOUT authored content must NOT be present
    assert "/design-interior/oradea" not in locs, "generic city must be excluded from sitemap"
    # hub + editorial guide live in OTHER child sitemaps, not the design child
    assert "/design-interior" not in locs, "hub belongs to sitemap-static, not sitemap-design"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.text[:200]}"
    return s


def test_design_cluster_all_indexable_and_in_sitemap(admin):
    """Every design_interior cluster row is indexable and present in SOME sitemap child.
    The cluster is a logical grouping: design pages/styles/content-cities (sitemap-design)
    + the hub /design-interior (sitemap-static) + editorial guides (sitemap-content)."""
    pages = admin.get(f"{API}/admin/seo/pages", timeout=30).json()["pages"]
    di_rows = [p for p in pages if p["cluster"] == "design_interior"]
    urls = {p["url"].replace("https://propmanage.ro", "") for p in di_rows}

    assert all(p["index"] for p in di_rows)
    assert all(p["in_sitemap"] for p in di_rows)

    # hub + editorial guides that live in OTHER child sitemaps
    assert "/design-interior" in urls                          # hub -> sitemap-static
    assert "/ghiduri/cum-alegi-designer-interior" in urls      # guide -> sitemap-content

    sm = requests.get(f"{API}/public/sitemap-design.xml", timeout=20).text
    design_locs = {re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", sm)}
    # everything in the design sitemap is part of the cluster grouping
    assert design_locs.issubset(urls)
    # the extras are the hub + editorial guides (not in the design child)
    extra = urls - design_locs
    assert "/design-interior" in extra
    assert any(u.startswith("/ghiduri/") for u in extra)
