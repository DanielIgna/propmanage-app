"""Iteration 70 — Strategic City Partnership Program tests."""
import os
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

SUPER_ADMIN = ("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
SUB_ADMIN = ("testing.admin@propmanage.io", "TestAdmin123!")
CLIENT = ("client@propmanage.io", "Client123!")
PARTNER1 = ("ion@blocadmin.ro", "owKT6oOYMIyOSM!1A")


def _login(email, password):
    """Returns a requests.Session with login cookies set, or None on failure."""
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    if r.status_code != 200:
        return None
    return s


def _headers(_session):
    return {"Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    t = _login(*SUPER_ADMIN)
    if not t:
        pytest.skip("super admin login failed")
    return t


@pytest.fixture(scope="module")
def sub_admin_token():
    return _login(*SUB_ADMIN)


@pytest.fixture(scope="module")
def client_token():
    return _login(*CLIENT)


@pytest.fixture(scope="module")
def partner1_token():
    return _login(*PARTNER1)


@pytest.fixture(scope="module")
def new_partner(admin_token):
    """Create a fresh partner + login for RBAC tests."""
    unique = uuid.uuid4().hex[:8]
    payload = {
        "company": f"TEST_Partner_{unique}",
        "contact_name": "Test Partner",
        "contact_email": f"TEST_partner_{unique}@test.io",
        "city": "Cluj-Napoca",
        "units_managed": 50,
        "growth_rate": "10%",
        "portfolio_type": "residential",
        "status": "onboarding",
    }
    r = admin_token.post(f"{BASE_URL}/api/admin/city-partners", json=payload, timeout=20)
    assert r.status_code == 200, r.text
    partner = r.json()
    # Create login
    r2 = admin_token.post(
        f"{BASE_URL}/api/admin/city-partners/{partner['id']}/create-login", timeout=20,
    )
    assert r2.status_code == 200, r2.text
    login = r2.json()
    yield {"partner": partner, "login": login, "email": payload["contact_email"]}


# ─── CRUD ────────────────────────────────────────────────────────────────────
class TestPartnerCRUD:
    def test_create_partner_valid(self, admin_token, new_partner):
        p = new_partner["partner"]
        assert p["id"]
        assert p["status"] == "onboarding"
        assert p["contact_email"].startswith("test_partner_")
        assert p["onboarding_step"] == 0

    def test_create_partner_invalid_status(self, admin_token):
        payload = {
            "company": f"TEST_X_{uuid.uuid4().hex[:6]}", "contact_name": "Bogus",
            "contact_email": f"TEST_x_{uuid.uuid4().hex[:6]}@t.io", "city": "Bucuresti",
            "status": "BOGUS",
        }
        r = admin_token.post(f"{BASE_URL}/api/admin/city-partners", json=payload, timeout=20)
        assert r.status_code == 400

    def test_create_partner_duplicate_email(self, admin_token, new_partner):
        payload = {
            "company": "TEST_dup", "contact_name": "Dup Person",
            "contact_email": new_partner["email"], "city": "Bucuresti",
        }
        r = admin_token.post(f"{BASE_URL}/api/admin/city-partners", json=payload, timeout=20)
        assert r.status_code == 409

    def test_list_partners(self, admin_token):
        r = admin_token.get(f"{BASE_URL}/api/admin/city-partners", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        assert "count" in data

    def test_list_with_status_filter(self, admin_token):
        r = admin_token.get(f"{BASE_URL}/api/admin/city-partners?status=onboarding", timeout=20)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["status"] == "onboarding"

    def test_get_partner_detail(self, admin_token, new_partner):
        pid = new_partner["partner"]["id"]
        r = admin_token.get(f"{BASE_URL}/api/admin/city-partners/{pid}", timeout=20)
        assert r.status_code == 200
        assert r.json()["id"] == pid

    def test_patch_partner(self, admin_token, new_partner):
        pid = new_partner["partner"]["id"]
        r = admin_token.patch(
            f"{BASE_URL}/api/admin/city-partners/{pid}",
            json={"notes": "Updated by test", "growth_rate": "25%"}, timeout=20,
        )
        assert r.status_code == 200
        assert r.json()["growth_rate"] == "25%"

    def test_global_stats(self, admin_token):
        r = admin_token.get(f"{BASE_URL}/api/admin/city-partners/stats", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ["total_partners", "by_status", "total_leads", "leads_by_stage", "top_partners"]:
            assert k in d


# ─── Onboarding wizard ──────────────────────────────────────────────────────
class TestOnboarding:
    def test_step_advance(self, admin_token, new_partner):
        pid = new_partner["partner"]["id"]
        r = admin_token.post(
            f"{BASE_URL}/api/admin/city-partners/{pid}/onboarding-step",
            json={"step": 3}, timeout=20,
        )
        assert r.status_code == 200
        assert r.json()["onboarding_step"] == 3
        assert r.json()["onboarding_complete"] is False

    def test_step_7_auto_promote(self, admin_token, new_partner):
        pid = new_partner["partner"]["id"]
        r = admin_token.post(
            f"{BASE_URL}/api/admin/city-partners/{pid}/onboarding-step",
            json={"step": 7}, timeout=20,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["onboarding_step"] == 7
        assert d["onboarding_complete"] is True
        assert d["status"] == "active", f"expected status=active, got {d['status']}"


# ─── Leads (admin side) ─────────────────────────────────────────────────────
class TestAdminLeads:
    def test_create_lead(self, admin_token, new_partner):
        pid = new_partner["partner"]["id"]
        r = admin_token.post(
            f"{BASE_URL}/api/admin/city-partners/{pid}/leads",
            json={"lead_name": "TEST_LeadA", "lead_email": "leada@test.io"}, timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["stage"] == "introduced"
        new_partner["lead_id"] = d["id"]

    def test_list_leads(self, admin_token, new_partner):
        pid = new_partner["partner"]["id"]
        r = admin_token.get(f"{BASE_URL}/api/admin/city-partners/{pid}/leads", timeout=20)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_patch_lead_to_converted(self, admin_token, new_partner):
        lid = new_partner.get("lead_id")
        assert lid
        r = admin_token.patch(
            f"{BASE_URL}/api/admin/city-partners/leads/{lid}",
            json={"stage": "converted", "revenue_generated": 500}, timeout=20,
        )
        assert r.status_code == 200
        d = r.json()
        assert d["stage"] == "converted"
        assert d["conversion_date"] is not None
        assert d["revenue_generated"] == 500


# ─── Partner Portal ─────────────────────────────────────────────────────────
class TestPartnerPortal:
    def test_partner_login_new(self, new_partner):
        login = new_partner["login"]
        tok = _login(login["email"], login["temp_password"])
        assert tok, "fresh partner login failed"
        new_partner["token"] = tok

    def test_partner_me(self, new_partner):
        tok = new_partner.get("token")
        r = tok.get(f"{BASE_URL}/api/partner/me", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "partner" in d
        assert "onboarding_steps" in d and len(d["onboarding_steps"]) == 7
        assert "user" in d

    def test_partner_leads_empty_initially(self, new_partner):
        tok = new_partner.get("token")
        r = tok.get(f"{BASE_URL}/api/partner/leads", timeout=20)
        assert r.status_code == 200
        # New partner has 1 lead created by admin in TestAdminLeads
        assert r.json()["count"] >= 1

    def test_partner_create_lead(self, new_partner):
        tok = new_partner.get("token")
        r = tok.post(
            f"{BASE_URL}/api/partner/leads",
            json={"lead_name": "TEST_PortalLead", "lead_email": "portal@test.io"}, timeout=20,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["source"] == "partner_portal"
        assert d["stage"] == "introduced"

    def test_partner_stats(self, new_partner):
        tok = new_partner.get("token")
        r = tok.get(f"{BASE_URL}/api/partner/stats", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ["leads_total", "leads_by_stage", "revenue_generated", "conversion_rate", "partner"]:
            assert k in d
        assert d["partner"]["onboarding_steps_total"] == 7


# ─── RBAC ────────────────────────────────────────────────────────────────────
class TestRBAC:
    def test_sub_admin_blocked_admin_endpoint(self, sub_admin_token):
        if not sub_admin_token:
            pytest.skip("sub admin login failed")
        r = sub_admin_token.get(f"{BASE_URL}/api/admin/city-partners", timeout=20)
        assert r.status_code == 403

    def test_client_blocked_partner_endpoint(self, client_token):
        if not client_token:
            pytest.skip("client login failed")
        r = client_token.get(f"{BASE_URL}/api/partner/me", timeout=20)
        assert r.status_code == 403

    def test_client_blocked_partner_leads(self, client_token):
        if not client_token:
            pytest.skip()
        r = client_token.get(f"{BASE_URL}/api/partner/leads", timeout=20)
        assert r.status_code == 403

    def test_partner_cannot_see_other_partner_leads(self, partner1_token, new_partner):
        """partner1 (ion@) and the new test partner should not see each other's leads."""
        if not partner1_token:
            pytest.skip("partner1 login failed")
        r = partner1_token.get(f"{BASE_URL}/api/partner/leads", timeout=20)
        assert r.status_code == 200
        own_leads = r.json()["items"]
        # None of partner1's leads should belong to new_partner
        new_pid = new_partner["partner"]["id"]
        for lead in own_leads:
            assert lead["partner_id"] != new_pid, "RBAC LEAK — partner1 can see new_partner's leads"


# ─── Legal integration ──────────────────────────────────────────────────────
class TestLegal:
    def test_partner_legal_status(self, new_partner):
        tok = new_partner.get("token")
        if not tok:
            pytest.skip()
        # /me/status should NOT pollute city_partner with the 6 IT docs
        r = tok.get(f"{BASE_URL}/api/legal/me/status", timeout=20)
        assert r.status_code == 200
        d = r.json()
        # Should be compliant=True with required=[] for fresh city_partner OR have only city_partner doc
        required = d.get("required", [])
        for req in required:
            assert "ip_cession" not in str(req).lower() and "nda" not in str(req).lower(), \
                f"city_partner /me/status polluted with IT docs: {req}"

    def test_legal_partner_status_endpoint(self, new_partner):
        tok = new_partner.get("token")
        if not tok:
            pytest.skip()
        r = tok.get(f"{BASE_URL}/api/legal/partner/status", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("applicable") is True
        assert "compliant" in d
        assert "pending" in d
        assert "signed" in d

    def test_it_collaborator_still_sees_it_docs(self):
        """Regression: dev1@team.com still sees 6 IT docs not city_partner."""
        tok = _login("dev1@team.com", "Dev1Pass!")
        if not tok:
            pytest.skip("dev1 login failed")
        r = tok.get(f"{BASE_URL}/api/legal/me/status", timeout=20)
        assert r.status_code == 200
        d = r.json()
        # Combined required+signed should reference IT docs but NOT city_partner
        all_keys = []
        for collection in ["required", "signed", "pending"]:
            for item in d.get(collection, []) or []:
                all_keys.append(str(item).lower())
        joined = " ".join(all_keys)
        assert "city_partner" not in joined, "IT collaborator polluted with city_partner doc"
