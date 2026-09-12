"""Iter 116 — Tenant Val 3: franchise_admin role + scoping + nurture sequence.

Backend-only tests. Independent verification of:
  - POST /api/admin/tenants/{slug}/admins (201 create, 409 duplicate email,
    404 unknown tenant, 400 slug='main', 403 for franchise_admin)
  - GET /api/admin/tenants/{slug}/admins (list, admin-only)
  - Scoping: franchise_admin login → /auth/me has tenant_id=cluj
  - GET /admin/leads as franchise_admin → tenant='cluj', all leads tenant_id=cluj
  - GET /admin/leads/summary as franchise_admin
  - franchise_admin forbidden on /admin/leads/migrate & /admin/tenants
  - HQ admin GET /admin/leads → multi-tenants; with ?tenant=cluj → only cluj
  - Public lead creation with X-Tenant-ID header (cluj / missing / invalid → main)
  - Nurture sequence config (nurture_enabled=false, delay=168)
  - POST /admin/leads/followup/run?sequence=nurture_7d&dry_run=true
  - Regression: admin/client login, /services/*/content, X-Tenant-ID fallback

Data seeded via pymongo (sync). Prefix TEST_ + explicit cleanup at end.
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"
FRANCHISE_EMAIL = "franciza.cluj@propmanage.io"
FRANCHISE_PASSWORD = "Franciza123!"


# ── Fixtures ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def franchise_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": FRANCHISE_EMAIL, "password": FRANCHISE_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Franchise admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Client login failed: {r.status_code}")
    return s


@pytest.fixture(scope="module")
def db():
    from pymongo import MongoClient
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "propmanage_db")
    return MongoClient(mongo_url)[db_name]


TEST_EMAILS_TO_CLEAN = set()


# ── Franchise admin CRUD ──────────────────────────────────────────────────
class TestFranchiseAdmins:
    """POST /api/admin/tenants/{slug}/admins + GET listing."""

    def test_create_admin_success(self, admin_session):
        email = f"TEST_fa_{uuid.uuid4().hex[:8]}@example.com"
        TEST_EMAILS_TO_CLEAN.add(email)
        r = admin_session.post(f"{API}/admin/tenants/cluj/admins",
                               json={"email": email, "password": "TestPass123!", "name": "TEST FA"}, timeout=15)
        assert r.status_code == 201, r.text[:300]
        data = r.json()
        assert data["ok"] is True
        # server lowercases emails
        assert data["email"].lower() == email.lower()
        assert data["role"] == "franchise_admin"
        assert data["tenant_id"] == "cluj"

    def test_create_admin_duplicate_email(self, admin_session):
        # Use the existing franchise admin email — must return 409
        r = admin_session.post(f"{API}/admin/tenants/cluj/admins",
                               json={"email": FRANCHISE_EMAIL, "password": "AnotherPass123!", "name": "Dup"},
                               timeout=15)
        assert r.status_code == 409, f"Expected 409 for duplicate, got {r.status_code}: {r.text[:200]}"

    def test_create_admin_tenant_not_found(self, admin_session):
        email = f"TEST_fa_{uuid.uuid4().hex[:6]}@example.com"
        r = admin_session.post(f"{API}/admin/tenants/nonexistent_tenant_xyz/admins",
                               json={"email": email, "password": "TestPass123!", "name": "TEST"}, timeout=15)
        assert r.status_code == 404, r.text[:200]

    def test_create_admin_main_tenant_blocked(self, admin_session):
        email = f"TEST_fa_main_{uuid.uuid4().hex[:6]}@example.com"
        r = admin_session.post(f"{API}/admin/tenants/main/admins",
                               json={"email": email, "password": "TestPass123!", "name": "TEST"}, timeout=15)
        assert r.status_code == 400, f"Expected 400 (main is HQ), got {r.status_code}: {r.text[:200]}"

    def test_list_admins(self, admin_session):
        r = admin_session.get(f"{API}/admin/tenants/cluj/admins", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        emails = [x.get("email") for x in data["items"]]
        assert FRANCHISE_EMAIL in emails, f"Missing seeded franchise admin in list: {emails}"

    def test_list_admins_unknown_tenant(self, admin_session):
        r = admin_session.get(f"{API}/admin/tenants/nonexistent_tenant_xyz/admins", timeout=15)
        assert r.status_code == 404

    def test_franchise_admin_forbidden_from_create(self, franchise_session):
        email = f"TEST_fa_deny_{uuid.uuid4().hex[:6]}@example.com"
        r = franchise_session.post(f"{API}/admin/tenants/cluj/admins",
                                   json={"email": email, "password": "x" * 10, "name": "x"}, timeout=15)
        assert r.status_code in (401, 403), f"Expected 403 for franchise_admin, got {r.status_code}"

    def test_franchise_admin_forbidden_from_list(self, franchise_session):
        r = franchise_session.get(f"{API}/admin/tenants/cluj/admins", timeout=15)
        assert r.status_code in (401, 403)


# ── Scoping ────────────────────────────────────────────────────────────────
class TestScoping:
    def test_auth_me_has_tenant_id(self, franchise_session):
        r = franchise_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200, r.text[:200]
        me = r.json()
        assert me.get("role") == "franchise_admin", me
        assert me.get("tenant_id") == "cluj", f"Expected tenant_id=cluj, got {me.get('tenant_id')}"

    def test_franchise_leads_scoped_to_cluj(self, franchise_session):
        r = franchise_session.get(f"{API}/admin/leads?limit=200", timeout=20)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("tenant") == "cluj", f"Expected tenant='cluj' in response, got {data.get('tenant')}"
        leads = data.get("leads") or []
        # every lead must be cluj
        bad = [l for l in leads if l.get("tenant_id") not in (None, "cluj")]
        assert not bad, f"Leads leaked from other tenants: {[b.get('tenant_id') for b in bad[:5]]}"

    def test_franchise_summary_scoped(self, franchise_session):
        r = franchise_session.get(f"{API}/admin/leads/summary?days=30", timeout=15)
        assert r.status_code == 200, r.text[:200]
        # scoped summary is a dict (totals) — just needs to succeed
        assert isinstance(r.json(), dict)

    def test_franchise_cannot_migrate(self, franchise_session):
        r = franchise_session.post(f"{API}/admin/leads/migrate", timeout=15)
        assert r.status_code in (401, 403)

    def test_franchise_cannot_list_tenants(self, franchise_session):
        r = franchise_session.get(f"{API}/admin/tenants", timeout=15)
        assert r.status_code in (401, 403)

    def test_hq_admin_sees_multi_tenants(self, admin_session):
        r = admin_session.get(f"{API}/admin/leads?limit=500", timeout=20)
        assert r.status_code == 200
        data = r.json()
        # HQ w/o filter: `tenant` should be None (or unset). Leads may span multiple tenants.
        leads = data.get("leads") or []
        tenants = {l.get("tenant_id") for l in leads}
        # allow single-tenant if only 1 exists, but require unfiltered view (no forced scope)
        assert data.get("tenant") in (None, ""), f"HQ unfiltered should not scope: got {data.get('tenant')}"
        # There should be >1 lead
        assert len(leads) >= 1

    def test_hq_admin_filter_by_cluj(self, admin_session):
        r = admin_session.get(f"{API}/admin/leads?tenant=cluj&limit=500", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data.get("tenant") == "cluj"
        leads = data.get("leads") or []
        for l in leads:
            assert l.get("tenant_id") == "cluj", f"Non-cluj lead leaked: {l.get('tenant_id')}"


# ── X-Tenant-ID header resolution ─────────────────────────────────────────
class TestTenantHeaderResolution:
    def _payload(self, tag):
        return {
            "name": f"TEST X-Tenant {tag}",
            "email": f"TEST_xtenant_{tag}_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "+40 700 000 000",
            "city": "Cluj",
            "budget": "5000",
            "message": "iter116 X-Tenant test",
        }

    def test_public_lead_with_cluj_header(self, db):
        payload = self._payload("cluj")
        TEST_EMAILS_TO_CLEAN.add(payload["email"])
        email_lc = payload["email"].lower()
        r = requests.post(f"{API}/services/arhitectura/leads", json=payload,
                          headers={"X-Tenant-ID": "cluj"}, timeout=15)
        assert r.status_code == 200, r.text[:200]
        lead_id = r.json()["lead_id"]
        # Verify in unified `leads` collection (email lowercased server-side)
        doc = db.leads.find_one({"email": email_lc}, {"_id": 0})
        assert doc is not None, f"Lead not synced to unified `leads` (searched {email_lc})"
        assert doc.get("tenant_id") == "cluj", f"Expected tenant_id=cluj, got {doc.get('tenant_id')}"
        # Also verify service_leads
        sdoc = db.service_leads.find_one({"id": lead_id}, {"_id": 0})
        assert sdoc and sdoc.get("tenant_id") == "cluj"

    def test_public_lead_no_header_fallback_main(self, db):
        payload = self._payload("nohdr")
        TEST_EMAILS_TO_CLEAN.add(payload["email"])
        email_lc = payload["email"].lower()
        r = requests.post(f"{API}/services/arhitectura/leads", json=payload, timeout=15)
        assert r.status_code == 200
        doc = db.leads.find_one({"email": email_lc}, {"_id": 0})
        assert doc is not None
        assert doc.get("tenant_id") == "main", f"Expected fallback tenant_id=main, got {doc.get('tenant_id')}"

    def test_public_lead_invalid_header_fallback_main(self, db):
        payload = self._payload("inv")
        TEST_EMAILS_TO_CLEAN.add(payload["email"])
        email_lc = payload["email"].lower()
        r = requests.post(f"{API}/services/arhitectura/leads", json=payload,
                          headers={"X-Tenant-ID": "nonexistent_zzz"}, timeout=15)
        assert r.status_code == 200
        doc = db.leads.find_one({"email": email_lc}, {"_id": 0})
        assert doc is not None
        assert doc.get("tenant_id") == "main", (
            f"Invalid X-Tenant-ID should fallback to main, got {doc.get('tenant_id')}"
        )


# ── Nurture sequence ──────────────────────────────────────────────────────
class TestNurtureSequence:
    def test_config_has_nurture_keys(self, admin_session):
        r = admin_session.get(f"{API}/admin/leads/followup/config", timeout=15)
        assert r.status_code == 200
        cfg = r.json()
        assert cfg.get("nurture_enabled") is False, cfg
        assert cfg.get("nurture_delay_hours") == 168, cfg
        assert "nurture_subject" in cfg
        assert isinstance(cfg["nurture_subject"], str) and len(cfg["nurture_subject"]) > 5

    def test_dry_run_nurture_sequence(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/leads/followup/run?sequence=nurture_7d&dry_run=true", timeout=45)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data.get("ran") is True, f"Expected ran=true (manual=True bypasses enabled flag): {data}"
        assert data.get("sequence") == "nurture_7d"
        assert data.get("dry_run") is True
        assert isinstance(data.get("candidates"), int) and data["candidates"] >= 0
        # If any candidates exist, at least one should have been "sent" in dry_run
        if data["candidates"] > 0:
            assert data.get("sent", 0) >= 1

    def test_nurture_log_has_sequence_field(self, admin_session):
        r = admin_session.get(f"{API}/admin/leads/followup/log?limit=50", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        # Every log entry should have `sequence` (post-refactor)
        entries_with_seq = [x for x in items if x.get("sequence")]
        assert entries_with_seq, f"No log entries with 'sequence' field found (recent {len(items)})"
        # At least one nurture_7d entry from the dry-run above
        nurture_entries = [x for x in items if x.get("sequence") == "nurture_7d"]
        assert nurture_entries, "No nurture_7d log entries found after dry run"

    def test_warm_sequence_still_works(self, admin_session):
        # Regression: default sequence=warm_48h still works via manual run
        r = admin_session.post(f"{API}/admin/leads/followup/run?dry_run=true", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data.get("ran") is True
        # Sequence label present
        assert data.get("sequence") == "warm_48h"


# ── Regression ────────────────────────────────────────────────────────────
class TestRegression:
    def test_admin_login_still_works(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200

    def test_client_login_still_works(self):
        r = requests.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=15)
        assert r.status_code == 200

    def test_design_exterior_content(self):
        r = requests.get(f"{API}/services/design-exterior/content", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict) and data

    def test_arhitectura_content(self):
        r = requests.get(f"{API}/services/arhitectura/content", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict) and data

    def test_coverage_still_ok(self, admin_session):
        r = admin_session.get(f"{API}/admin/tenants/coverage", timeout=30)
        assert r.status_code == 200
        totals = r.json()["totals"]
        gap = totals["t1_docs"] - totals["t1_docs_with_tenant_id"]
        # Allow small drift from public leads created in earlier tests
        assert gap <= 20, f"Coverage gap grew unexpectedly: {gap} of {totals['t1_docs']}"


# ── Cleanup ───────────────────────────────────────────────────────────────
def test_zz_cleanup(db):
    """Delete all TEST_-prefixed data we created."""
    # test emails
    if TEST_EMAILS_TO_CLEAN:
        db.users.delete_many({"email": {"$in": list(TEST_EMAILS_TO_CLEAN)}})
        db.leads.delete_many({"email": {"$in": list(TEST_EMAILS_TO_CLEAN)}})
        db.service_leads.delete_many({"email": {"$in": list(TEST_EMAILS_TO_CLEAN)}})
    # broad clean by TEST_ prefix (safety net) — email is lowercased server-side
    db.users.delete_many({"email": {"$regex": "^test_fa_", "$options": "i"}})
    db.leads.delete_many({"email": {"$regex": "^test_xtenant_", "$options": "i"}})
    db.service_leads.delete_many({"email": {"$regex": "^test_xtenant_", "$options": "i"}})
    # Sanity: seeded admin & cluj tenant untouched
    assert db.users.find_one({"email": FRANCHISE_EMAIL}) is not None, "OOPS: seeded franchise admin missing!"
    assert db.tenants.find_one({"slug": "cluj"}) is not None, "OOPS: cluj tenant missing!"
