"""Iteration 92 — SEO Price Pages backend tests (public, no auth)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

EXPECTED_SLUGS = {
    "zugravit", "montaj-parchet", "gresie-faianta", "handyman", "gips-carton",
    "montaj-aer-conditionat", "instalatii-electrice", "instalatii-sanitare",
    "design-interior", "constructii-zidarie", "acoperisuri", "termoizolatii-fatade",
    "tamplarie-pvc", "amenajari-exterioare",
}


# ----------------------------- SEO INDEX -----------------------------
class TestSeoPagesIndex:
    def test_index_returns_14_items(self):
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        items = data["items"]
        assert isinstance(items, list)
        assert len(items) == 14, f"Expected 14 SEO pages, got {len(items)}"

    def test_index_item_shape(self):
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages", timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        required_keys = {"slug", "name", "noun", "price_from", "price_to", "unit_sample", "services_count", "preliminary"}
        slugs_found = set()
        for it in items:
            missing = required_keys - set(it.keys())
            assert not missing, f"Item {it.get('slug')} missing keys: {missing}"
            assert isinstance(it["price_from"], (int, float))
            assert isinstance(it["price_to"], (int, float))
            assert it["price_from"] <= it["price_to"], f"price_from > price_to for {it['slug']}"
            assert it["services_count"] >= 1
            slugs_found.add(it["slug"])
        assert slugs_found == EXPECTED_SLUGS, f"Missing slugs: {EXPECTED_SLUGS - slugs_found}, extra: {slugs_found - EXPECTED_SLUGS}"


# ----------------------------- SEO DETAIL -----------------------------
@pytest.mark.parametrize("slug", ["zugravit", "instalatii-electrice", "montaj-aer-conditionat", "design-interior"])
class TestSeoPageDetail:
    def test_detail_shape(self, slug):
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages/{slug}", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        # Required top-level keys
        for k in ("title", "description", "cities", "default_city", "prices_by_city", "faq", "related", "disclaimer", "year"):
            assert k in d, f"[{slug}] missing key: {k}"
        assert d["year"] == 2026, f"[{slug}] expected year=2026, got {d['year']}"
        # Cities
        assert isinstance(d["cities"], list)
        assert len(d["cities"]) == 3, f"[{slug}] expected 3 cities, got {len(d['cities'])}: {d['cities']}"
        assert set(d["cities"]) == {"București", "Cluj-Napoca", "Timișoara"}, f"[{slug}] cities: {d['cities']}"
        assert d["default_city"] in d["cities"]
        # FAQ 4 items
        assert isinstance(d["faq"], list) and len(d["faq"]) == 4, f"[{slug}] faq length: {len(d['faq'])}"
        for f in d["faq"]:
            assert "q" in f and "a" in f
        # Related 6 items
        assert isinstance(d["related"], list) and len(d["related"]) == 6, f"[{slug}] related length: {len(d['related'])}"
        # Title mentions "Cât costă"
        assert "Cât costă" in d["title"]

    def test_prices_by_city_levels(self, slug):
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages/{slug}", timeout=30)
        assert r.status_code == 200
        d = r.json()
        pbc = d["prices_by_city"]
        assert set(pbc.keys()) == set(d["cities"])
        for city, rows in pbc.items():
            assert isinstance(rows, list) and len(rows) >= 1, f"[{slug}/{city}] no rows"
            for row in rows:
                assert "service" in row and "unit" in row and "levels" in row
                lv = row["levels"]
                assert isinstance(lv, dict)
                # mid and/or expert should have proper structure when present
                for lvl_name in ("mid", "expert"):
                    if lvl_name in lv:
                        for pk in ("price_min", "price_med", "price_max"):
                            assert pk in lv[lvl_name], f"[{slug}/{city}/{row['service']}] {lvl_name} missing {pk}"
                # Requirement: each service has levels.mid AND levels.expert
                assert "mid" in lv, f"[{slug}/{city}/{row['service']}] missing levels.mid"
                assert "expert" in lv, f"[{slug}/{city}/{row['service']}] missing levels.expert"


# ----------------------------- 404 -----------------------------
class TestSeoPageNotFound:
    def test_invalid_slug_returns_404(self):
        r = requests.get(f"{BASE_URL}/api/construction/prices/seo-pages/slug-inexistent", timeout=30)
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text[:200]}"


# ----------------------------- SITEMAP -----------------------------
class TestSitemap:
    def test_sitemap_contains_preturi_urls(self):
        r = requests.get(f"{BASE_URL}/api/public/sitemap.xml", timeout=30)
        assert r.status_code == 200
        body = r.text
        # /preturi index
        assert "/preturi<" in body or "/preturi</loc>" in body
        # All 14 category slugs
        missing = []
        for slug in EXPECTED_SLUGS:
            if f"/preturi/{slug}" not in body:
                missing.append(slug)
        assert not missing, f"Sitemap missing slugs: {missing}"

    def test_sitemap_has_15_preturi_locs(self):
        r = requests.get(f"{BASE_URL}/api/public/sitemap.xml", timeout=30)
        assert r.status_code == 200
        body = r.text
        # Count <loc> entries that include '/preturi'
        import re as _re
        locs = _re.findall(r"<loc>([^<]*/preturi[^<]*)</loc>", body)
        assert len(locs) == 15, f"Expected 15 preturi locs, got {len(locs)}: {locs}"


# ----------------------------- REGRESSION -----------------------------
class TestRegressionPublic:
    def test_landing_still_reachable(self):
        r = requests.get(f"{BASE_URL}/", timeout=30)
        assert r.status_code == 200

    def test_health_ok(self):
        r = requests.get(f"{BASE_URL}/api/health", timeout=30)
        assert r.status_code == 200
        assert r.json().get("status") in ("ok", "degraded")
