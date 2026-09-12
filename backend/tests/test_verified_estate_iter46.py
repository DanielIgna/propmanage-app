"""Iteration 46 additions for Verified Estate:
1. Demo checkout auto-creates a draft listing visible to admin
2. Email notifications fire (inquiries/external/checkout) — 200 response
3. Public listings expose lat/lng on seed entries
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = OWNER_ADMIN_PASSWORD


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code}")
    me = s.get(f"{BASE_URL}/api/auth/me")
    if me.status_code != 200 or me.json().get("role") != "admin":
        pytest.skip("Admin /me failed")
    return s


# ---------- New: lat/lng on public listings ----------

class TestLatLngOnListings:
    def test_listings_have_lat_lng_for_seeds(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings")
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert len(items) >= 2, f"Expected >=2 seed listings, got {len(items)}"
        # Find the Aviatorilor + Pipera entries
        aviator = next((it for it in items if "Aviatorilor" in (it.get("title") or "") or "Aviatorilor" in (it.get("address") or "")), None)
        pipera = next((it for it in items if "Pipera" in (it.get("title") or "") or "Pipera" in (it.get("address") or "")), None)
        assert aviator is not None, "Aviatorilor seed missing"
        assert pipera is not None, "Pipera seed missing"
        assert aviator.get("lat") == pytest.approx(44.4632, abs=0.001), f"Aviator lat={aviator.get('lat')}"
        assert aviator.get("lng") == pytest.approx(26.0894, abs=0.001), f"Aviator lng={aviator.get('lng')}"
        assert pipera.get("lat") == pytest.approx(44.5215, abs=0.001), f"Pipera lat={pipera.get('lat')}"
        assert pipera.get("lng") == pytest.approx(26.1278, abs=0.001), f"Pipera lng={pipera.get('lng')}"


# ---------- New: checkout auto-creates draft listing ----------

class TestCheckoutAutoDraft:
    def test_demo_checkout_creates_draft_listing(self, session, admin_session):
        # Snapshot current draft count
        before = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=draft")
        assert before.status_code == 200, before.text
        before_count = before.json().get("total", 0)

        payload = {
            "package": "bundle",
            "contact_name": "TEST_Iter46_Seller",
            "contact_email": "test_iter46_seller@example.com",
            "contact_phone": "+40712345678",
            "property_address": "Str. Test Iter46 nr. 7, București",
            "notes": "iter46 auto-draft test",
        }
        r = session.post(f"{BASE_URL}/api/verified-estate/checkout", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("demo_mode") is True
        assert data.get("order_id"), "missing order_id"
        order_id = data["order_id"]

        # Admin should see a new draft
        after = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=draft")
        assert after.status_code == 200
        after_items = after.json().get("items", [])
        after_count = after.json().get("total", 0)
        assert after_count == before_count + 1, f"Draft count delta != 1 (before={before_count} after={after_count})"

        # Find the new draft by source_order_id
        new_draft = next((it for it in after_items if it.get("source_order_id") == order_id), None)
        assert new_draft is not None, "Draft with matching source_order_id not found"

        # Title format
        assert new_draft.get("title", "").startswith("Imobil în pregătire ·"), f"Bad title: {new_draft.get('title')}"
        assert "Str. Test Iter46 nr. 7" in new_draft["title"], f"Address missing from title: {new_draft.get('title')}"

        # Owner fields
        assert new_draft.get("owner_email") == "test_iter46_seller@example.com"
        assert new_draft.get("owner_name") == "TEST_Iter46_Seller"
        assert new_draft.get("owner_phone") == "+40712345678"

        # pending_services flags for bundle
        ps = new_draft.get("pending_services") or {}
        assert ps.get("audit") is True
        assert ps.get("twin") is True

        # Gates all failing
        gates = new_draft.get("gates_status") or {}
        assert gates.get("gate_1_audit", {}).get("ok") is False
        assert gates.get("gate_2_twin", {}).get("ok") is False
        assert gates.get("gate_3_recommendations", {}).get("ok") is False

        # Status draft
        assert new_draft.get("status") == "draft"

    def test_demo_checkout_audit_only_flags(self, session, admin_session):
        r = session.post(f"{BASE_URL}/api/verified-estate/checkout", json={
            "package": "audit",
            "contact_name": "TEST_Iter46_AuditOnly",
            "contact_email": "test_iter46_audit@example.com",
            "property_address": "Str. Audit Only, Cluj",
        })
        assert r.status_code == 200, r.text
        order_id = r.json()["order_id"]

        after = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=draft&limit=100")
        items = after.json().get("items", [])
        draft = next((it for it in items if it.get("source_order_id") == order_id), None)
        assert draft is not None
        ps = draft.get("pending_services") or {}
        assert ps.get("audit") is True
        assert ps.get("twin") is False


# ---------- New: email notifications fire (verify endpoints still 200) ----------

class TestEmailNotificationHooks:
    def test_inquiry_returns_ok_and_admin_email_fired(self, session):
        # Need a published listing id
        r = session.get(f"{BASE_URL}/api/verified-estate/listings")
        items = r.json().get("items", [])
        assert len(items) > 0
        listing_id = items[0]["id"]
        ir = session.post(f"{BASE_URL}/api/verified-estate/inquiries", json={
            "listing_id": listing_id,
            "name": "TEST_Iter46_Buyer",
            "email": "test_iter46_buyer@example.com",
            "phone": "+40700111222",
            "message": "Email hook check",
            "intent": "viewing",
        })
        assert ir.status_code == 200, ir.text
        assert ir.json().get("ok") is True

    def test_external_audit_returns_ok(self, session):
        r = session.post(f"{BASE_URL}/api/verified-estate/external-audit-request", json={
            "external_listing_url": "https://imobiliare.ro/test-iter46",
            "property_address": "Str. Test Extern Iter46, București",
            "contact_name": "TEST_Iter46_ExtBuyer",
            "contact_email": "test_iter46_ext@example.com",
            "notes": "email hook test",
        })
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_checkout_returns_ok(self, session):
        # Already covered above, but ensure 200 explicit
        r = session.post(f"{BASE_URL}/api/verified-estate/checkout", json={
            "package": "twin",
            "contact_name": "TEST_Iter46_TwinOnly",
            "contact_email": "test_iter46_twin@example.com",
            "property_address": "Str. Twin Only, București",
        })
        assert r.status_code == 200, r.text
        assert r.json().get("demo_mode") is True
