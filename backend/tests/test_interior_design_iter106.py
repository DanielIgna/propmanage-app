"""Interior Design service — end-to-end backend tests (iteration 106).

Covers:
- Public content endpoint (no auth)
- Public lead creation (no auth) + persistence via admin
- Public AI assistant (Emergent LLM / Claude)
- Admin content GET/PUT (auth required)
- Admin leads GET + PATCH status
- Sitemap includes /design-interior
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
           os.environ.get("BACKEND_URL", "").rstrip("/")

if not BASE_URL:
    # fallback for local runs
    with open("/app/frontend/.env") as fh:
        for line in fh:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", "1!nasov01ADMIN")


@pytest.fixture(scope="module")
def anon_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed ({r.status_code}): {r.text[:200]}")
    return s


# Shared state
_state = {}


# ── PUBLIC CONTENT ────────────────────────────────────────────────────────────
class TestPublicContent:
    def test_content_no_auth(self, anon_client):
        r = anon_client.get(f"{BASE_URL}/api/interior-design/content", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        required = ["seo", "hero", "benefits", "steps", "portfolio", "reviews",
                    "faq", "styles", "budgets", "local_cities",
                    "related_services", "seo_article"]
        for key in required:
            assert key in data, f"missing key: {key}"
        assert data["hero"]["h1"].startswith("Design Interior care transformă")
        assert isinstance(data["benefits"], list) and len(data["benefits"]) >= 3
        assert isinstance(data["seo_article"], list) and len(data["seo_article"]) >= 3
        assert data["seo"].get("title")
        assert data["seo"].get("description")


# ── LEAD CREATION ─────────────────────────────────────────────────────────────
class TestLeadCreation:
    def test_create_lead(self, anon_client):
        payload = {
            "name": "TEST_Test Cristina",
            "email": "test_cristina@example.com",
            "phone": "+40712345678",
            "style": "Scandinav",
            "budget": "15.000 – 40.000 lei",
            "surface_mp": 60,
            "rooms": "living + bucătărie",
            "city": "București",
            "message": "TEST_iter106 - Apartament 3 camere, buget mediu.",
            "lead_type": "proiect",
        }
        r = anon_client.post(f"{BASE_URL}/api/interior-design/leads",
                             json=payload, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ok") is True
        assert data.get("lead_id")
        assert isinstance(data["lead_id"], str)
        assert len(data["lead_id"]) >= 6
        _state["lead_id"] = data["lead_id"]
        _state["lead_name"] = payload["name"]

    def test_lead_invalid_email(self, anon_client):
        r = anon_client.post(f"{BASE_URL}/api/interior-design/leads",
                             json={"name": "x", "email": "not-an-email"}, timeout=10)
        assert r.status_code in (400, 422), r.text[:200]


# ── AI ASSISTANT ──────────────────────────────────────────────────────────────
class TestAssistant:
    def test_assistant_answers_ro(self, anon_client):
        r = anon_client.post(
            f"{BASE_URL}/api/interior-design/assistant",
            json={"question": "Cat costa un proiect de design pentru un apartament de 60mp?"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("answer"), "empty answer"
        assert data.get("session_id")
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 20
        _state["session_id"] = data["session_id"]
        # Print for logs
        print(f"\n[AI answer preview]: {data['answer'][:200]}")

    def test_assistant_empty_question(self, anon_client):
        r = anon_client.post(f"{BASE_URL}/api/interior-design/assistant",
                             json={"question": "   "}, timeout=15)
        assert r.status_code == 400


# ── ADMIN AUTH GATE ───────────────────────────────────────────────────────────
class TestAdminAuthGate:
    def test_admin_content_requires_auth(self, anon_client):
        r = anon_client.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=10)
        assert r.status_code in (401, 403)

    def test_admin_leads_requires_auth(self, anon_client):
        r = anon_client.get(f"{BASE_URL}/api/admin/interior-design/leads", timeout=10)
        assert r.status_code in (401, 403)


# ── ADMIN CONTENT ─────────────────────────────────────────────────────────────
class TestAdminContent:
    def test_admin_get_content(self, admin_client):
        r = admin_client.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "hero" in data and "seo" in data

    def test_admin_update_content_persists(self, admin_client):
        # capture original
        orig = admin_client.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=10).json()
        original_order = orig.get("menu_order", 1)
        new_order = 42 if original_order != 42 else 43
        r = admin_client.put(
            f"{BASE_URL}/api/admin/interior-design/content",
            json={"menu_order": new_order}, timeout=15,
        )
        assert r.status_code == 200, r.text[:300]
        # verify via GET
        r2 = admin_client.get(f"{BASE_URL}/api/admin/interior-design/content", timeout=10)
        assert r2.status_code == 200
        assert r2.json().get("menu_order") == new_order
        # restore
        admin_client.put(f"{BASE_URL}/api/admin/interior-design/content",
                         json={"menu_order": original_order}, timeout=10)

    def test_admin_update_rejects_invalid_field(self, admin_client):
        r = admin_client.put(
            f"{BASE_URL}/api/admin/interior-design/content",
            json={"bogus_key": "x"}, timeout=10,
        )
        assert r.status_code == 400


# ── ADMIN LEADS ───────────────────────────────────────────────────────────────
class TestAdminLeads:
    def test_admin_leads_list_contains_test_lead(self, admin_client):
        # ensure a lead exists
        if "lead_id" not in _state:
            pytest.skip("Lead creation didn't run")
        r = admin_client.get(f"{BASE_URL}/api/admin/interior-design/leads", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "leads" in data
        assert isinstance(data["leads"], list)
        assert data.get("total", 0) >= 1
        # find our lead
        ids = [ld.get("id") for ld in data["leads"]]
        assert _state["lead_id"] in ids, f"created lead {_state['lead_id']} not in list"
        # confirm no _id leak
        for ld in data["leads"][:5]:
            assert "_id" not in ld

    def test_admin_patch_lead_status(self, admin_client):
        if "lead_id" not in _state:
            pytest.skip("Lead creation didn't run")
        r = admin_client.patch(
            f"{BASE_URL}/api/admin/interior-design/leads/{_state['lead_id']}",
            json={"status": "contacted"}, timeout=15,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True
        # confirm status changed via list
        r2 = admin_client.get(
            f"{BASE_URL}/api/admin/interior-design/leads?status=contacted", timeout=10)
        assert r2.status_code == 200
        ids = [ld.get("id") for ld in r2.json().get("leads", [])]
        assert _state["lead_id"] in ids

    def test_admin_patch_lead_invalid_status(self, admin_client):
        if "lead_id" not in _state:
            pytest.skip("Lead creation didn't run")
        r = admin_client.patch(
            f"{BASE_URL}/api/admin/interior-design/leads/{_state['lead_id']}",
            json={"status": "not_a_status"}, timeout=10,
        )
        assert r.status_code == 400

    def test_admin_patch_lead_not_found(self, admin_client):
        r = admin_client.patch(
            f"{BASE_URL}/api/admin/interior-design/leads/deadbeefcafe",
            json={"status": "new"}, timeout=10,
        )
        assert r.status_code == 404


# ── SITEMAP ───────────────────────────────────────────────────────────────────
class TestSitemap:
    def test_sitemap_includes_design_interior(self, anon_client):
        r = anon_client.get(f"{BASE_URL}/api/public/sitemap.xml", timeout=15)
        assert r.status_code == 200
        assert "/design-interior" in r.text
