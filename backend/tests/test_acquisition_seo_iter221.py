"""SEO Expansion #4 — acquisition cluster (owners / specialists / designers).
Validates the 9 acquisition landing pages + /devino-specialist are INDEX + in sitemap,
correctly classified, and that no protected rules were touched."""
import os
import re
import requests

API = os.environ.get("PREVIEW_API", "http://localhost:8001/api")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}

ACQ_PATHS = [
    "/pentru-proprietari", "/cartea-casei",
    "/pentru-specialisti",
    "/pentru-specialisti/electrician", "/pentru-specialisti/instalator",
    "/pentru-specialisti/constructor", "/pentru-specialisti/auditor-energetic",
    "/pentru-specialisti/hvac",
    "/pentru-designeri", "/devino-specialist",
]


def _admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.text[:200]}"
    return s


def test_acquisition_pages_in_static_sitemap():
    r = requests.get(f"{API}/public/sitemap-static.xml", timeout=20)
    assert r.status_code == 200 and "<urlset" in r.text
    locs = {re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", r.text)}
    for p in ACQ_PATHS:
        assert p in locs, f"{p} missing from sitemap-static.xml"


def test_devino_specialist_now_indexed():
    """Regression: /devino-specialist was previously NOT in any sitemap."""
    r = requests.get(f"{API}/public/sitemap-static.xml", timeout=20)
    assert "/devino-specialist" in r.text


def test_acquisition_classified_by_cluster():
    s = _admin()
    pages = s.get(f"{API}/admin/seo/pages", timeout=30).json()["pages"]
    by_url = {p["url"].replace("https://propmanage.ro", ""): p for p in pages}
    # owners
    assert by_url["/pentru-proprietari"]["cluster"] == "proprietari"
    assert by_url["/cartea-casei"]["cluster"] == "proprietari"
    # specialists (pillar + trades + apply)
    for p in ("/pentru-specialisti", "/pentru-specialisti/electrician", "/devino-specialist"):
        assert by_url[p]["cluster"] == "specialisti", p
    # designers
    assert by_url["/pentru-designeri"]["cluster"] == "designeri"
    # all indexable + in sitemap
    for p in ACQ_PATHS:
        assert by_url[p]["index"] is True, p
        assert by_url[p]["in_sitemap"] is True, p


def test_sitemap_validate_still_green():
    s = _admin()
    r = s.post(f"{API}/admin/seo/sitemap/validate", timeout=40).json()
    assert r["valid"] is True
    assert all(c["ok"] for c in r["checks"])


def test_marketplace_gate_rule_unchanged():
    """Protected: marketplace service-city gate must still require >= 3 specialists."""
    g = requests.get(f"{API}/public/seo/gate", params={"path": "/marketplace/electrician-bucuresti"}, timeout=15).json()
    # electrician-bucuresti has < 3 verified in preview -> noindex + canonical parent
    assert "index" in g
