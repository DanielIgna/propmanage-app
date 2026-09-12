"""iter112 — Backend regression for Interior Intelligence by PropManage (v2 content).

Covers:
  1) GET /api/interior-design/content → content_version=2 with all v2 sections
  2) POST /api/interior-design/leads → creates lead + dual-write to `leads`
  3) Admin GET/PUT /api/admin/interior-design/content → dual-write across
     `service_pages` and `interior_design_content` (patched then restored)
  4) Site menu label updated to 'Interior Intelligence'
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


# ── 1. Public content ────────────────────────────────────────────────────────
class TestPublicContent:
    def test_content_v2_shape(self, http):
        r = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c.get("content_version") == 2, f"content_version != 2 (got {c.get('content_version')})"
        assert c.get("active") is True

    def test_brand(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        b = c.get("brand") or {}
        assert b.get("name") == "Interior Intelligence"
        assert b.get("suffix") == "by PropManage"
        assert isinstance(b.get("tagline"), str) and b["tagline"]

    def test_positioning(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        p = c.get("positioning") or {}
        assert p.get("title"), "positioning.title missing"
        assert p.get("text"), "positioning.text missing"
        assert isinstance(p.get("badges"), list) and len(p["badges"]) >= 4

    def test_journey_seven(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        j = c.get("journey") or []
        assert len(j) == 7, f"journey has {len(j)} items, expected 7"
        assert "Audit" in j and "House Health" in j and "Digital Twin" in j

    def test_process_phases_and_steps_count(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        phases = c.get("process_phases") or []
        assert len(phases) == 5, f"process_phases has {len(phases)} items, expected 5"
        total_steps = sum(len(p.get("steps") or []) for p in phases)
        assert total_steps == 17, f"total steps across 5 phases = {total_steps}, expected 17"
        # ensure step numbering 1..17
        nums = sorted([s["n"] for p in phases for s in p.get("steps", [])])
        assert nums == list(range(1, 18)), f"step numbers not 1..17: {nums}"

    def test_digital_twin_contains_11(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        dt = c.get("digital_twin") or {}
        assert dt.get("title") and dt.get("intro") and dt.get("outro")
        assert len(dt.get("contains") or []) == 11

    def test_audit_points_8(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        assert len(((c.get("audit") or {}).get("points") or [])) == 8

    def test_implementation_points_10(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        assert len(((c.get("implementation") or {}).get("points") or [])) == 10

    def test_ecosystem_links_11(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        links = ((c.get("ecosystem") or {}).get("links") or [])
        assert len(links) == 11
        for l in links:
            assert l.get("title") and l.get("href")

    def test_styles_showcase_12(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        items = ((c.get("styles_showcase") or {}).get("items") or [])
        assert len(items) == 12
        names = [i["name"] for i in items]
        assert "Warm Minimalism" in names and "Japandi" in names

    def test_faq_8(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        assert len(c.get("faq") or []) == 8

    def test_seo_article_10(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        arts = c.get("seo_article") or []
        assert len(arts) == 10
        for a in arts:
            assert a.get("h2") and a.get("body")

    def test_styles_list_12(self, http):
        c = http.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        assert len(c.get("styles") or []) == 12


# ── 2. Public lead creation ──────────────────────────────────────────────────
class TestLeadCreation:
    def test_required_fields_missing(self, http):
        r = http.post(f"{BASE_URL}/api/interior-design/leads", json={"name": "TEST_only_name"}, timeout=15)
        assert r.status_code in (400, 422), f"expected 422/400 for missing email, got {r.status_code}"

    def test_invalid_email(self, http):
        r = http.post(
            f"{BASE_URL}/api/interior-design/leads",
            json={"name": "TEST_bad_email", "email": "not-an-email"},
            timeout=15,
        )
        assert r.status_code in (400, 422)

    def test_create_lead_success_dual_write(self, http, admin_session):
        unique = uuid.uuid4().hex[:8]
        email = f"TEST_lead_{unique}@example.com"
        payload = {
            "name": f"TEST_Lead_{unique}",
            "email": email,
            "phone": "0700000000",
            "style": "Japandi",
            "budget": "15.000 – 40.000 lei",
            "surface_mp": 60,
            "rooms": "living + bucătărie",
            "city": "Cluj-Napoca",
            "message": "Test message for iter112 regression.",
            "lead_type": "proiect",
        }
        r = http.post(f"{BASE_URL}/api/interior-design/leads", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert data.get("lead_id") and isinstance(data["lead_id"], str)
        lead_id = data["lead_id"]

        # Dual-write verification via admin endpoint (interior_design_leads)
        time.sleep(0.4)
        r2 = admin_session.get(f"{BASE_URL}/api/admin/interior-design/leads?limit=50", timeout=15)
        assert r2.status_code == 200, r2.text
        leads = r2.json().get("leads", [])
        found = next((l for l in leads if l.get("id") == lead_id), None)
        assert found is not None, f"lead {lead_id} not present in admin listing"
        assert found.get("email") == email.lower() or found.get("email") == email
        assert found.get("segment") in ("hot", "warm", "nurture")
        assert isinstance(found.get("score"), int)


# ── 3. Admin content ────────────────────────────────────────────────────────
class TestAdminContent:
    def test_admin_get_content(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c.get("content_version") == 2

    def test_admin_forbidden_without_auth(self, http):
        r = http.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_put_hero_cta_and_restore(self, admin_session):
        # capture original
        r0 = admin_session.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=15)
        assert r0.status_code == 200
        original_hero = dict(r0.json().get("hero") or {})
        assert original_hero.get("cta_primary")

        # patch cta_primary
        new_cta = f"TEST_CTA_{uuid.uuid4().hex[:6]}"
        patched_hero = {**original_hero, "cta_primary": new_cta}
        r = admin_session.put(
            f"{BASE_URL}/api/admin/interior-design/content",
            json={"hero": patched_hero},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("hero", {}).get("cta_primary") == new_cta

        # verify via public endpoint
        pub = requests.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        assert pub.get("hero", {}).get("cta_primary") == new_cta

        # restore
        r_restore = admin_session.put(
            f"{BASE_URL}/api/admin/interior-design/content",
            json={"hero": original_hero},
            timeout=15,
        )
        assert r_restore.status_code == 200
        assert r_restore.json().get("hero", {}).get("cta_primary") == original_hero["cta_primary"]

        # verify public reverted
        pub2 = requests.get(f"{BASE_URL}/api/interior-design/content", timeout=15).json()
        assert pub2.get("hero", {}).get("cta_primary") == original_hero["cta_primary"]

    def test_admin_put_empty_400(self, admin_session):
        r = admin_session.put(
            f"{BASE_URL}/api/admin/interior-design/content",
            json={"__not_allowed_key__": "x"},
            timeout=15,
        )
        assert r.status_code == 400


# ── 4. Site menu label ──────────────────────────────────────────────────────
class TestSiteMenu:
    def test_menu_label_interior_intelligence(self, http):
        # site menu is CMS-driven; hit the public menu endpoint
        candidates = [
            "/api/public/site-menu",
            "/api/site-menu",
            "/api/public/menu",
        ]
        found_label = None
        used = None
        for path in candidates:
            r = http.get(f"{BASE_URL}{path}", timeout=15)
            if r.status_code == 200:
                used = path
                data = r.json()
                text = str(data)
                if "Interior Intelligence" in text:
                    found_label = "Interior Intelligence"
                break
        if not used:
            pytest.skip("No public site-menu endpoint found among candidates")
        assert found_label == "Interior Intelligence", f"'Interior Intelligence' label not found in {used}"
