"""Iteration 71 — Marketplace Partners Ecosystem + AI City Copilot Nudges."""
import os
import uuid
import requests
import pytest
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

ADMIN = ("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
CITY_PARTNER = ("ion@blocadmin.ro", "owKT6oOYMIyOSM!1A")
SUB_ADMIN = ("testing.admin@propmanage.io", "TestAdmin123!")
CLIENT = ("client@propmanage.io", "Client123!")
IT_DEV = ("dev1@team.com", "Dev1Pass!")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {email}: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="session")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def city_partner():
    return _login(*CITY_PARTNER)


@pytest.fixture(scope="session")
def sub_admin():
    return _login(*SUB_ADMIN)


@pytest.fixture(scope="session")
def client_user():
    return _login(*CLIENT)


@pytest.fixture(scope="session")
def created_partner(admin):
    payload = {
        "company": f"TEST_Mkt_{uuid.uuid4().hex[:8]}",
        "cui": "RO12345678",
        "contact_name": "Test Contact",
        "contact_email": f"test_mkt_{uuid.uuid4().hex[:8]}@example.com",
        "contact_phone": "+40712345678",
        "city": "Cluj-Napoca",
        "categories": ["Gresie și faianță", "Sanitare"],
        "zones": ["Cluj", "Bihor"],
        "tier": "verified",
        "status": "prospect",
        "package": "business",
    }
    r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ─── CRUD ──────────────────────────────────────────────────────────────
class TestMarketplaceCRUD:
    def test_create_partner_valid(self, created_partner):
        assert "id" in created_partner
        assert created_partner["tier"] == "verified"
        assert created_partner["status"] == "prospect"
        assert created_partner["package"] == "business"
        assert "Sanitare" in created_partner["categories"]

    def test_create_partner_invalid_tier(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners", json={
            "company": "TEST_Bad", "contact_name": "X Y",
            "contact_email": f"bad_{uuid.uuid4().hex[:6]}@e.com",
            "city": "Cluj-Napoca", "tier": "INVALID", "status": "prospect",
        }, timeout=15)
        assert r.status_code == 400

    def test_create_partner_invalid_status(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners", json={
            "company": "TEST_Bad", "contact_name": "X Y",
            "contact_email": f"bad_{uuid.uuid4().hex[:6]}@e.com",
            "city": "Cluj-Napoca", "tier": "basic", "status": "INVALID",
        }, timeout=15)
        assert r.status_code == 400

    def test_create_partner_invalid_package(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners", json={
            "company": "TEST_Bad", "contact_name": "X Y",
            "contact_email": f"bad_{uuid.uuid4().hex[:6]}@e.com",
            "city": "Cluj-Napoca", "tier": "basic", "status": "prospect",
            "package": "INVALID",
        }, timeout=15)
        assert r.status_code == 400

    def test_duplicate_email_409(self, admin, created_partner):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners", json={
            "company": "TEST_Dup", "contact_name": "X Y",
            "contact_email": created_partner["contact_email"],
            "city": "Cluj-Napoca", "tier": "basic", "status": "prospect",
        }, timeout=15)
        assert r.status_code == 409

    def test_list_partners(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/marketplace-partners", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and isinstance(body["items"], list)

    def test_list_with_filter(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/marketplace-partners?status=prospect", timeout=15)
        assert r.status_code == 200

    def test_get_partner(self, admin, created_partner):
        r = admin.get(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}", timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == created_partner["id"]

    def test_patch_partner(self, admin, created_partner):
        r = admin.patch(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}",
                        json={"status": "active", "notes": "Updated"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_stats(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/marketplace-partners/stats", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_partners", "by_status", "by_tier", "total_leads",
                  "leads_by_stage", "total_revenue", "top_categories",
                  "available_categories", "tiers", "packages"]:
            assert k in d, f"missing {k}"
        assert len(d["available_categories"]) >= 20

    def test_commissions(self, admin, created_partner):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}/commissions",
                       json={"type": "percent", "percent": 7.5, "monthly_subscription": 199}, timeout=15)
        assert r.status_code == 200
        assert r.json()["commissions"].get("percent") == 7.5

    def test_policies(self, admin, created_partner):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}/policies",
                       json={"client_discount_pct": 5, "promotions": ["promo1"]}, timeout=15)
        assert r.status_code == 200
        assert r.json()["policies"].get("client_discount_pct") == 5


# ─── Leads ─────────────────────────────────────────────────────────────
class TestMarketplaceLeads:
    def test_create_and_list_lead(self, admin, created_partner):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}/leads",
                       json={"lead_name": "TEST_Lead", "lead_email": "l@e.com",
                             "product_category": "Sanitare", "stage": "new",
                             "estimated_value": 1500}, timeout=15)
        assert r.status_code == 200, r.text
        lead = r.json()
        assert lead["stage"] == "new"
        assert lead["estimated_value"] == 1500

        r2 = admin.get(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}/leads", timeout=15)
        assert r2.status_code == 200
        assert any(l["id"] == lead["id"] for l in r2.json()["items"])

        # patch lead
        r3 = admin.patch(f"{BASE_URL}/api/admin/marketplace-partners/leads/{lead['id']}",
                         json={"stage": "qualified"}, timeout=15)
        assert r3.status_code == 200
        assert r3.json()["stage"] == "qualified"


# ─── Create-login + portal ─────────────────────────────────────────────
class TestMarketplacePortal:
    def test_create_login_and_portal(self, admin, created_partner):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}/create-login", timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        # Either fresh-created or already linked
        if body.get("created"):
            assert "temp_password" in body
            temp_pw = body["temp_password"]
            email = body["email"]

            # Login as marketplace_partner
            s = requests.Session()
            lr = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": temp_pw}, timeout=20)
            assert lr.status_code == 200, lr.text

            # /me
            me = s.get(f"{BASE_URL}/api/marketplace-partner/me", timeout=15)
            assert me.status_code == 200
            assert me.json()["partner"]["id"] == created_partner["id"]

            # Create a lead via portal
            cl = s.post(f"{BASE_URL}/api/marketplace-partner/leads",
                        json={"lead_name": "TEST_PortalLead", "stage": "new"}, timeout=15)
            assert cl.status_code == 200
            assert cl.json()["source"] == "marketplace_portal"

            # /leads only theirs
            leads = s.get(f"{BASE_URL}/api/marketplace-partner/leads", timeout=15)
            assert leads.status_code == 200

            # /stats
            stats = s.get(f"{BASE_URL}/api/marketplace-partner/stats", timeout=15)
            assert stats.status_code == 200
            sd = stats.json()
            assert "leads_total" in sd and "leads_by_stage" in sd

            # RBAC: marketplace_partner blocked on /api/admin/*
            rb = s.get(f"{BASE_URL}/api/admin/marketplace-partners", timeout=15)
            assert rb.status_code == 403


# ─── RBAC ──────────────────────────────────────────────────────────────
class TestRBAC:
    def test_sub_admin_blocked_admin(self, sub_admin):
        r = sub_admin.get(f"{BASE_URL}/api/admin/marketplace-partners", timeout=15)
        assert r.status_code == 403

    def test_sub_admin_blocked_stats(self, sub_admin):
        r = sub_admin.get(f"{BASE_URL}/api/admin/marketplace-partners/stats", timeout=15)
        assert r.status_code == 403

    def test_client_blocked_admin(self, client_user):
        r = client_user.get(f"{BASE_URL}/api/admin/marketplace-partners", timeout=15)
        assert r.status_code == 403


# ─── City Partner Copilot Nudges ───────────────────────────────────────
class TestCityCopilotNudges:
    def test_nudges_for_city_partner(self, city_partner):
        r = city_partner.post(f"{BASE_URL}/api/partner/copilot/nudges", timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "nudges" in body
        assert "generated_at" in body
        assert len(body["nudges"]) >= 1
        n0 = body["nudges"][0]
        for k in ["title", "body", "priority"]:
            assert k in n0

    def test_nudges_forbidden_admin(self, admin):
        r = admin.post(f"{BASE_URL}/api/partner/copilot/nudges", timeout=20)
        assert r.status_code == 403

    def test_nudges_forbidden_client(self, client_user):
        r = client_user.post(f"{BASE_URL}/api/partner/copilot/nudges", timeout=20)
        assert r.status_code == 403


# ─── Legal Audit (regression + new marketplace_partner template) ───────
class TestLegalAudit:
    def test_city_partner_legal_compliant(self, city_partner):
        r = city_partner.get(f"{BASE_URL}/api/legal/me/status", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("compliant") is True
        assert d.get("required") == [] or len(d.get("required") or []) == 0


# ─── AI Marketplace Copilot Analyze (slow) ─────────────────────────────
class TestMarketplaceCopilot:
    def test_analyze(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners/copilot/analyze", timeout=120)
        # Could be 404 if no active partners — but we created one
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["summary", "hot_categories", "top_converters", "underperformers",
                  "pricing_recommendations", "commercial_opportunities", "growth_score",
                  "analyzed_count", "generated_at"]:
            assert k in d, f"missing {k}"


# ─── Presentation generation (slow) ────────────────────────────────────
class TestPresentation:
    def test_presentation(self, admin, created_partner):
        r = admin.post(f"{BASE_URL}/api/admin/marketplace-partners/{created_partner['id']}/presentation",
                       timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["partner_id", "partner_company", "slides", "key_takeaway",
                  "estimated_opportunity_text"]:
            assert k in d
        assert len(d["slides"]) >= 5
        s0 = d["slides"][0]
        assert "title" in s0 and "bullets" in s0
        assert len(s0["bullets"]) <= 4
