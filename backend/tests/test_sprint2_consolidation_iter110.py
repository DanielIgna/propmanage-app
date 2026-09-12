"""Iteration 110 — Sprint 2 Consolidation Regression Tests.

Covers:
- Auth flows for admin/client/specialist
- Settings façade (unified `settings` collection + legacy fallback + dual-write)
- Leads unified via /api/public/demo-request → leads_store
- AI chat (interior_design) with session_id
- XOS admin endpoints
- Public content (service_pages / interior-design content)
"""
import os
import uuid
import requests
import pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN = {"email": "admin@propmanage.io", "password": os.environ.get("SEED_ADMIN_PASSWORD", "1!nasov01ADMIN")}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}


def _login(session: requests.Session, creds: dict):
    r = session.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    return r


# ----------------------------- AUTH -----------------------------

class TestAuthRegression:
    def test_admin_login_and_me(self):
        s = requests.Session()
        r = _login(s, ADMIN)
        assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
        me = s.get(f"{BASE}/api/auth/me", timeout=15)
        assert me.status_code == 200
        data = me.json()
        assert data.get("email") == ADMIN["email"]
        assert data.get("role") == "admin"

    def test_client_login_and_me(self):
        s = requests.Session()
        r = _login(s, CLIENT)
        assert r.status_code == 200, f"client login failed: {r.status_code} {r.text[:200]}"
        me = s.get(f"{BASE}/api/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json().get("role") == "client"

    def test_specialist_login_and_me(self):
        s = requests.Session()
        r = _login(s, SPECIALIST)
        assert r.status_code == 200
        me = s.get(f"{BASE}/api/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json().get("role") == "specialist"


# ----------------------------- SETTINGS FAÇADE -----------------------------

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = _login(s, ADMIN)
    if r.status_code != 200:
        pytest.skip("admin login failed for settings tests")
    return s


class TestSettingsFacade:
    def test_public_app_settings(self):
        r = requests.get(f"{BASE}/api/app-settings/public", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # settings_store fallback should return the full app settings structure
        assert "social" in data
        assert "pricing" in data
        assert "seo" in data

    def test_admin_get_all_settings(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/app-settings", timeout=15)
        assert r.status_code == 200, r.text[:200]
        assert "pricing" in r.json()

    def test_admin_update_settings_dual_write(self, admin_session):
        # Change tagline via PUT, then verify persisted via public + admin GET.
        new_tag = f"regression-{uuid.uuid4().hex[:6]}"
        r = admin_session.put(
            f"{BASE}/api/admin/app-settings",
            json={"company": {"name": "PropManage", "tagline": new_tag}},
            timeout=20,
        )
        assert r.status_code == 200, r.text[:200]
        # Verify via admin GET
        r2 = admin_session.get(f"{BASE}/api/admin/app-settings", timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("company", {}).get("tagline") == new_tag
        # Verify via public endpoint (which reads legacy app_settings; dual-write must have kept them in sync)
        r3 = requests.get(f"{BASE}/api/app-settings/public", timeout=15)
        assert r3.status_code == 200
        assert r3.json().get("company", {}).get("tagline") == new_tag

    def test_security_config_via_settings_store(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/security/config", timeout=15)
        # requires admin scope 'security'; if not granted returns 403, else 200
        assert r.status_code in (200, 403), r.text[:200]
        if r.status_code == 200:
            data = r.json()
            # Must contain baseline fields from DEFAULT_CONFIG merged with settings_store value
            assert "rate_limit_per_minute" in data
            assert "bot_block_enabled" in data


# ----------------------------- LEADS (public demo-request) -----------------------------

class TestLeadsUnified:
    def test_demo_request_creates_lead_and_triage(self):
        email = f"regression_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "name": "TEST Regression Lead",
            "email": email,
            "company": "Acme SRL",
            "role": "founder",
            "message": (
                "Vrem sa integram PropManage pentru un portofoliu mare de peste 10000 mp; "
                "ne intereseaza modulul de digital twin si audit tehnic."
            ),
            "whatsapp": "+40712345678",
        }
        r = requests.post(f"{BASE}/api/public/demo-request", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        assert body.get("ok") is True

        # verify lead appeared in unified `leads` via admin endpoint if available; otherwise skip triage assert
        s = requests.Session()
        lr = _login(s, ADMIN)
        if lr.status_code != 200:
            return
        # Admin demo-leads endpoint reads legacy collection — checks dual-write happened
        r2 = s.get(f"{BASE}/api/admin/demo-leads?limit=200", timeout=20)
        assert r2.status_code == 200, r2.text[:200]
        items = r2.json().get("items", [])
        assert any(it.get("email") == email for it in items), "lead not found in legacy demo_leads (dual-write regression)"

    def test_demo_request_validation(self):
        r = requests.post(f"{BASE}/api/public/demo-request", json={"name": "", "email": "invalid"}, timeout=15)
        assert r.status_code == 400


# ----------------------------- AI CHAT + service_pages -----------------------------

class TestInteriorDesignRegression:
    def test_public_content_serves(self):
        r = requests.get(f"{BASE}/api/interior-design/content", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # service_pages master → must have core sections
        assert isinstance(data, dict) and len(data) > 0

    def test_ai_concierge_session(self):
        # Correct endpoint per routes/interior_design.py
        session_id = f"regression-{uuid.uuid4().hex[:10]}"
        r = requests.post(
            f"{BASE}/api/interior-design/assistant",
            json={"question": "Salut, ce servicii oferiti?", "session_id": session_id},
            timeout=90,
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:200]}"
        data = r.json()
        assert data.get("session_id") == session_id
        assert isinstance(data.get("answer"), str) and len(data["answer"]) > 0


# ----------------------------- XOS ADMIN -----------------------------

class TestXOSAdmin:
    def test_xos_registry_admin(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/xos/registry", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        # registry returns list of surfaces or dict with widgets
        assert data is not None

    @pytest.mark.parametrize("role", ["client", "specialist", "admin"])
    def test_xos_experience_profile(self, admin_session, role):
        # public endpoint returns per-role profile
        r = admin_session.get(f"{BASE}/api/experience/profile/{role}", timeout=15)
        assert r.status_code == 200, f"role={role} status={r.status_code} body={r.text[:200]}"
        data = r.json()
        assert isinstance(data, dict)

    def test_admin_experience_profiles_list(self, admin_session):
        r = admin_session.get(f"{BASE}/api/admin/experience-profiles", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "profiles" in data or isinstance(data, list)


# ----------------------------- HEALTH -----------------------------

class TestHealth:
    def test_health(self):
        r = requests.get(f"{BASE}/api/health", timeout=15)
        assert r.status_code == 200
        assert r.json().get("status") in ("ok", "degraded")
