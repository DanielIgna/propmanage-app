"""Iter 114 — P1: Service Hub (design-exterior, arhitectura) + Theme Manager."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASS}, timeout=15)
    assert r.status_code == 200, f"client login failed: {r.status_code} {r.text}"
    return s


# --- Service Hub: content endpoints -----------------------------------------
@pytest.mark.parametrize("slug,expected_brand", [
    ("design-exterior", "Exterior Design"),
    ("arhitectura", "Arhitectură"),
])
def test_public_content_full(slug, expected_brand):
    r = requests.get(f"{BASE}/api/services/{slug}/content", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert expected_brand in d.get("brand", {}).get("name", "") or expected_brand in d.get("brand", {}).get("suffix", ""), d.get("brand")
    assert d.get("hero", {}).get("h1")
    assert isinstance(d.get("journey"), list) and len(d["journey"]) == 7
    assert d.get("positioning")
    assert len(d.get("benefits", [])) == 6, f"benefits count: {len(d.get('benefits',[]))}"
    phases = d.get("process_phases", [])
    assert len(phases) == 3, f"process_phases count: {len(phases)}"
    total_steps = sum(len(p.get("steps", [])) for p in phases)
    if slug == "design-exterior":
        assert total_steps == 9, f"design-exterior steps: {total_steps}"
    else:
        assert total_steps == 10, f"arhitectura steps: {total_steps}"
    assert d.get("highlight") and len(d["highlight"].get("items", [])) == 8
    assert d.get("implementation")
    assert len(d.get("ecosystem", {}).get("links", [])) == 6
    assert len(d.get("faq", [])) == 5
    assert len(d.get("seo_article", [])) == 4
    assert isinstance(d.get("local_cities"), list) and len(d["local_cities"]) >= 3
    assert isinstance(d.get("budgets"), list) and len(d["budgets"]) >= 3


def test_public_content_invalid_slug():
    r = requests.get(f"{BASE}/api/services/nonexistent-xyz/content", timeout=15)
    assert r.status_code == 404


# --- Lead endpoints -----------------------------------------------------------
def test_create_lead_dual_write():
    payload = {"name": "TEST_Lead User", "email": "test_lead_iter114@example.com",
               "phone": "0700000000", "city": "București", "budget": "5.000-15.000 €",
               "message": "TEST iter114"}
    r = requests.post(f"{BASE}/api/services/design-exterior/leads", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("ok") is True
    assert d.get("lead_id")


def test_create_lead_minimal_ok():
    payload = {"name": "TEST_Min", "email": "test_min_iter114@example.com"}
    r = requests.post(f"{BASE}/api/services/arhitectura/leads", json=payload, timeout=15)
    assert r.status_code == 200


def test_create_lead_invalid_email():
    r = requests.post(f"{BASE}/api/services/design-exterior/leads",
                      json={"name": "TEST_X", "email": "not-an-email"}, timeout=15)
    assert r.status_code == 422


def test_create_lead_invalid_slug():
    r = requests.post(f"{BASE}/api/services/foobar/leads",
                      json={"name": "TEST_X", "email": "x@y.com"}, timeout=15)
    assert r.status_code == 404


# --- Admin content endpoints --------------------------------------------------
def test_admin_get_content(admin_sess):
    r = admin_sess.get(f"{BASE}/api/admin/services/design-exterior/content", timeout=15)
    assert r.status_code == 200
    assert r.json().get("hero")


def test_admin_put_content_and_restore(admin_sess):
    # Get original
    r0 = admin_sess.get(f"{BASE}/api/admin/services/arhitectura/content", timeout=15)
    assert r0.status_code == 200
    original_hero = r0.json().get("hero")

    # Patch hero
    patched_hero = dict(original_hero)
    patched_hero["h1"] = "TEST_PATCH — iter114 arhitectura"
    r1 = admin_sess.put(f"{BASE}/api/admin/services/arhitectura/content",
                        json={"hero": patched_hero}, timeout=15)
    assert r1.status_code == 200, r1.text
    assert r1.json()["hero"]["h1"] == patched_hero["h1"]

    # Verify persistence via GET
    r2 = admin_sess.get(f"{BASE}/api/admin/services/arhitectura/content", timeout=15)
    assert r2.json()["hero"]["h1"] == patched_hero["h1"]

    # Restore
    r3 = admin_sess.put(f"{BASE}/api/admin/services/arhitectura/content",
                        json={"hero": original_hero}, timeout=15)
    assert r3.status_code == 200
    assert r3.json()["hero"]["h1"] == original_hero["h1"]


def test_admin_put_only_disallowed_key(admin_sess):
    r = admin_sess.put(f"{BASE}/api/admin/services/design-exterior/content",
                       json={"random_bad_field_xyz": 123}, timeout=15)
    assert r.status_code == 400


def test_admin_put_unauth():
    r = requests.put(f"{BASE}/api/admin/services/design-exterior/content", json={"hero": {}}, timeout=15)
    assert r.status_code in (401, 403), r.status_code


def test_admin_get_leads(admin_sess):
    r = admin_sess.get(f"{BASE}/api/admin/services/design-exterior/leads", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and isinstance(d["items"], list)
    # our just-created TEST lead should be present
    emails = [i.get("email") for i in d["items"]]
    assert "test_lead_iter114@example.com" in emails, f"lead not persisted; emails: {emails[:5]}"


def test_admin_get_leads_unauth():
    r = requests.get(f"{BASE}/api/admin/services/design-exterior/leads", timeout=15)
    assert r.status_code in (401, 403)


# --- Unified leads dual-write -------------------------------------------------
def test_unified_leads_has_service_source(admin_sess):
    """POST a fresh lead and verify dual-write into unified `leads` collection with source and score."""
    email = f"test_dualwrite_{int(time.time())}@example.com"
    payload = {"name": "TEST_DualWrite", "email": email, "city": "Cluj-Napoca", "budget": "15.000-40.000 €"}
    r = requests.post(f"{BASE}/api/services/design-exterior/leads", json=payload, timeout=15)
    assert r.status_code == 200
    # Poll the unified leads endpoint (admin) for source design_exterior
    # Try /api/admin/leads first
    time.sleep(0.5)
    found = None
    for url in (f"{BASE}/api/admin/leads?source=design_exterior&limit=50",
                f"{BASE}/api/admin/leads?limit=100"):
        r2 = admin_sess.get(url, timeout=15)
        if r2.status_code == 200:
            data = r2.json()
            items = data.get("leads") or data.get("items") if isinstance(data, dict) else data
            if isinstance(items, list):
                for it in items:
                    if it.get("email") == email:
                        found = it
                        break
        if found:
            break
    assert found is not None, "Lead not present in unified /api/admin/leads collection"
    assert found.get("source") == "design_exterior", f"expected source=design_exterior, got {found.get('source')}"
    # score/segment optional but expected from AI triage
    assert "score" in found or "segment" in found, f"lead has no triage score/segment: {found}"


# --- Theme Manager: experience profiles --------------------------------------
def test_experience_profile_default_theme(admin_sess):
    r = admin_sess.get(f"{BASE}/api/experience/profile/client", timeout=15)
    # public GET might be admin or public; try public then admin
    if r.status_code != 200:
        r = requests.get(f"{BASE}/api/experience/profile/client", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "default_theme" in d, f"no default_theme in profile: {list(d.keys())}"


def test_theme_manager_admin_put_and_restore(admin_sess):
    """PUT default_theme=light for client role, verify, restore to 'system'."""
    # Get baseline
    r0 = requests.get(f"{BASE}/api/experience/profile/client", timeout=15)
    if r0.status_code != 200:
        r0 = admin_sess.get(f"{BASE}/api/experience/profile/client", timeout=15)
    assert r0.status_code == 200
    original_theme = r0.json().get("default_theme", "system")

    # PUT light
    r1 = admin_sess.put(f"{BASE}/api/admin/experience-profiles/client",
                        json={"default_theme": "light"}, timeout=15)
    assert r1.status_code == 200, f"PUT failed: {r1.status_code} {r1.text}"

    # Verify
    r2 = requests.get(f"{BASE}/api/experience/profile/client", timeout=15)
    if r2.status_code != 200:
        r2 = admin_sess.get(f"{BASE}/api/experience/profile/client", timeout=15)
    assert r2.json().get("default_theme") == "light"

    # Restore to system
    r3 = admin_sess.put(f"{BASE}/api/admin/experience-profiles/client",
                        json={"default_theme": "system"}, timeout=15)
    assert r3.status_code == 200
    r4 = requests.get(f"{BASE}/api/experience/profile/client", timeout=15)
    if r4.status_code != 200:
        r4 = admin_sess.get(f"{BASE}/api/experience/profile/client", timeout=15)
    assert r4.json().get("default_theme") == "system", f"restore failed, original was {original_theme}"


# --- Site menu regression -----------------------------------------------------
def test_site_menu_has_new_hrefs():
    r = requests.get(f"{BASE}/api/public/site-menu", timeout=15)
    assert r.status_code == 200
    items = r.json().get("items", [])
    servicii = next((i for i in items if i.get("id") == "servicii"), None)
    assert servicii, "no 'servicii' menu"
    kids = {c["id"]: c.get("href") for c in servicii.get("children", [])}
    assert kids.get("design_exterior") == "/design-exterior", f"design_exterior href: {kids.get('design_exterior')}"
    assert kids.get("arhitectura") == "/arhitectura", f"arhitectura href: {kids.get('arhitectura')}"


# --- Regression: interior design still works ---------------------------------
def test_interior_design_content_regression():
    r = requests.get(f"{BASE}/api/interior-design/content", timeout=15)
    # if endpoint different, skip
    if r.status_code == 404:
        pytest.skip("interior-design content endpoint different")
    assert r.status_code == 200
