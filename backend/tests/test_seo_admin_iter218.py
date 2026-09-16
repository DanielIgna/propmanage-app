"""SEO Foundation regression + Admin SEO Control Center (iter 218).

Covers:
  - robots.txt fix: /specialist (dashboard) blocked, /specialists/:id crawlable
  - sitemap ↔ robots consistency (no indexable URL blocked)
  - Indexability Gate acceptance (>=3 -> INDEX, <3 -> NOINDEX + parent canonical)
  - all 8 Admin SEO endpoints + sitemap validate
"""
import os
import re
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


# ── robots.txt matcher (mirrors backend logic) ──────────────────────────────
def _robots_rules(text):
    rules, ua = [], False
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        low = s.lower()
        if low.startswith("user-agent:"):
            ua = s.split(":", 1)[1].strip() == "*"
        elif ua and low.startswith("disallow:"):
            v = s.split(":", 1)[1].strip()
            if v:
                rules.append(v)
    return rules


def _blocks(path, rules):
    for d in rules:
        if d.endswith("$"):
            if path == d[:-1]:
                return True
        elif path.startswith(d):
            return True
    return False


def test_robots_dashboard_blocked_public_profiles_allowed():
    r = requests.get(f"{BASE_URL}/robots.txt", timeout=15)
    assert r.status_code == 200
    rules = _robots_rules(r.text)
    # private specialist dashboard + sub-pages MUST stay blocked
    assert _blocks("/specialist", rules), "dashboard /specialist should be blocked"
    assert _blocks("/specialist/premium-profile", rules)
    assert _blocks("/specialist/capabilities", rules)
    # public specialist PROFILES must remain crawlable (the P0 fix)
    assert not _blocks("/specialists/abc123", rules), "/specialists/:id must be crawlable"
    assert not _blocks("/specialists/64f0aa", rules)
    # sitemap declared
    assert "sitemap:" in r.text.lower()


def test_sitemap_robots_consistency():
    r = requests.get(f"{API}/public/sitemap.xml", timeout=20)
    assert r.status_code == 200 and "<urlset" in r.text
    locs = re.findall(r"<loc>([^<]+)</loc>", r.text)
    rules = _robots_rules(requests.get(f"{BASE_URL}/robots.txt", timeout=15).text)
    blocked = [u for u in locs if _blocks(re.sub(r"^https?://[^/]+", "", u) or "/", rules)]
    assert not blocked, f"sitemap URLs blocked by robots.txt: {blocked[:5]}"
    # specialist profiles are indexable AND now crawlable
    assert any("/specialists/" in u for u in locs), "specialist profiles should be in sitemap"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.text[:200]}"
    return s


def test_admin_seo_overview(admin):
    r = admin.get(f"{API}/admin/seo/overview", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["indexability"]["indexable_urls"] > 0
    assert d["sitemap"]["is_index"] is True
    assert d["sitemap"]["child_count"] == 7  # + sitemap-estate.xml + sitemap-blocuri.xml
    assert d["health"]["gate_ok"] is True


def test_admin_seo_indexability_gate_acceptance(admin):
    r = admin.get(f"{API}/admin/seo/indexability", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["threshold"] == 3
    # every INDEX row has >= threshold; every NOINDEX row has < threshold + canonical to parent
    for row in d["national"] + d["combos"]:
        if row["index"]:
            assert row["verified"] >= row["threshold"], row
        else:
            assert row["verified"] < row["threshold"], row
            assert row["canonical"], f"noindex row missing parent canonical: {row}"
    # at least one national service passes (demo data)
    assert d["summary"]["national_index"] >= 1


def test_admin_seo_inspect_gate_and_robots(admin):
    # <3 verified -> NOINDEX + parent canonical
    r = admin.get(f"{API}/admin/seo/inspect", params={"path": "/marketplace/electrician-bucuresti"}, timeout=20)
    d = r.json()
    assert d["index"] is False
    assert d["canonical"].endswith("/marketplace/electrician")
    assert d["in_sitemap"] is False
    # public specialist profile -> indexable and NOT robots-blocked
    r = admin.get(f"{API}/admin/seo/inspect", params={"path": "/specialists/abc123"}, timeout=20)
    d = r.json()
    assert d["index"] is True
    assert d["robots_txt_blocked"] is False
    # private dashboard -> robots-blocked
    r = admin.get(f"{API}/admin/seo/inspect", params={"path": "/specialist"}, timeout=20)
    assert r.json()["robots_txt_blocked"] is True
    # commercial home -> indexable, in sitemap, has title/H1 (from db.pages SSOT)
    r = admin.get(f"{API}/admin/seo/inspect", params={"path": "/"}, timeout=20)
    d = r.json()
    assert d["index"] is True and d["in_sitemap"] is True and d["title"]


def test_admin_seo_sitemap_and_validate(admin):
    r = admin.get(f"{API}/admin/seo/sitemap", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["root"]["is_index"] is True
    assert len(d["children"]) == 7  # + sitemap-estate.xml + sitemap-blocuri.xml
    assert d["excluded_count"] > 0  # thin content excluded with reasons
    v = admin.post(f"{API}/admin/seo/sitemap/validate", timeout=40)
    assert v.status_code == 200
    vd = v.json()
    assert vd["valid"] is True, vd["checks"]


def test_admin_seo_pages_clusters_alerts_gsc(admin):
    p = admin.get(f"{API}/admin/seo/pages", timeout=30).json()
    assert p["total"] > 0 and p["indexable"] > 0
    c = admin.get(f"{API}/admin/seo/clusters", timeout=30).json()
    ids = {x["id"] for x in c["clusters"]}
    for required in ["design_interior", "probleme_casa", "audit", "digital_twin",
                     "imobile_verificate", "local_city", "marketplace", "building_hartablocuri"]:
        assert required in ids, f"cluster {required} missing"
    a = admin.get(f"{API}/admin/seo/alerts", timeout=30).json()
    assert "critical_count" in a and a["critical_count"] == 0  # foundation healthy
    g = admin.get(f"{API}/admin/seo/gsc", timeout=20).json()
    assert g["connected"] is False and g["metrics"] is None  # no fake data
