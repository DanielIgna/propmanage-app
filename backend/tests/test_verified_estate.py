"""Backend tests for Verified Estate (Imobile Verificate) module.

Covers:
- Public listing browse + filters
- Listing detail (404 for invalid id)
- Inquiry submission
- External audit request
- Pricing endpoint
- Stripe checkout in DEMO mode
- Admin: auth gate, stats, lists (kanban/inquiries/external/orders), publish gate enforcement, archive
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = OWNER_ADMIN_PASSWORD


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def admin_session():
    """Login as admin and return an authenticated session (cookie-based auth)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    # verify cookie session works
    me = s.get(f"{BASE_URL}/api/auth/me")
    if me.status_code != 200 or me.json().get("role") != "admin":
        pytest.skip(f"Admin /me failed: {me.status_code} {me.text[:200]}")
    return s


@pytest.fixture(scope="module")
def admin_headers():
    return {"Content-Type": "application/json"}


# ------------- Public -------------

class TestPublicListings:
    def test_browse_listings(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data
        assert data["total"] >= 2, f"Expected >=2 demo listings, got {data['total']}"
        first = data["items"][0]
        for k in ["title", "city", "price_ron", "rooms", "transaction_type", "trust_score", "recommendations_pct"]:
            assert k in first, f"Missing field {k}"

    def test_filter_sale(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings?transaction_type=sale")
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_filter_rent_zero(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings?transaction_type=rent")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_filter_city(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings?city=București")
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_filter_rooms(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings?rooms=3")
        assert r.status_code == 200
        # only the Aviatorilor 3-camere should match
        assert r.json()["total"] >= 1

    def test_detail_404_invalid(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/listings/not-an-id")
        assert r.status_code == 404

    def test_detail_ok(self, session):
        listings = session.get(f"{BASE_URL}/api/verified-estate/listings").json()["items"]
        lid = listings[0]["id"]
        r = session.get(f"{BASE_URL}/api/verified-estate/listings/{lid}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == lid
        assert data["trust_score"] in ["A+", "A", "B", "C"]


class TestPricing:
    def test_pricing(self, session):
        r = session.get(f"{BASE_URL}/api/verified-estate/pricing")
        assert r.status_code == 200
        data = r.json()
        assert data["audit_ron"] == 350.0
        assert data["twin_ron"] == 950.0
        assert data["commission_pct"] == 2.5
        assert data["bundle_ron"] == 1300.0


class TestInquiry:
    def test_create_inquiry(self, session):
        listings = session.get(f"{BASE_URL}/api/verified-estate/listings").json()["items"]
        lid = listings[0]["id"]
        r = session.post(f"{BASE_URL}/api/verified-estate/inquiries", json={
            "listing_id": lid,
            "name": "TEST_Buyer",
            "email": "test_buyer@example.com",
            "phone": "0700000000",
            "message": "Vreau o vizionare",
            "intent": "buy",
        })
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        assert "inquiry_id" in r.json()

    def test_create_inquiry_bad_listing(self, session):
        r = session.post(f"{BASE_URL}/api/verified-estate/inquiries", json={
            "listing_id": "deadbeefdeadbeefdeadbeef",
            "name": "TEST_Buyer",
            "email": "x@example.com",
            "intent": "viewing",
        })
        assert r.status_code == 404


class TestExternalAudit:
    def test_external_request(self, session):
        r = session.post(f"{BASE_URL}/api/verified-estate/external-audit-request", json={
            "external_listing_url": "https://imobiliare.ro/listing/123",
            "property_address": "Str. Test 123, București",
            "contact_name": "TEST_External",
            "contact_email": "ext@example.com",
            "contact_phone": "0700111222",
            "notes": "Vreau audit",
            "budget_ron": 250000,
        })
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        assert "request_id" in r.json()


class TestCheckoutDemo:
    def test_checkout_demo_bundle(self, session):
        r = session.post(
            f"{BASE_URL}/api/verified-estate/checkout",
            json={
                "package": "bundle",
                "contact_name": "TEST_Seller",
                "contact_email": "seller@example.com",
                "contact_phone": "0701112233",
                "property_address": "Str. Sell 5, București",
                "notes": "Test demo",
            },
            headers={"Origin": BASE_URL, "Content-Type": "application/json"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["demo_mode"] is True
        assert "checkout_url" in data and "paid=1" in data["checkout_url"] and "demo=1" in data["checkout_url"]
        session_id = data["session_id"]
        # status poll
        s = session.get(f"{BASE_URL}/api/verified-estate/checkout/status/{session_id}")
        assert s.status_code == 200
        assert s.json()["status"] == "paid"
        assert s.json()["amount_ron"] == 1300.0


# ------------- Admin -------------

class TestAdminAuthGate:
    def test_admin_endpoints_require_auth(self, session):
        for ep in ["/api/verified-estate/admin/stats",
                   "/api/verified-estate/admin/listings",
                   "/api/verified-estate/admin/inquiries",
                   "/api/verified-estate/admin/external-requests",
                   "/api/verified-estate/admin/orders"]:
            r = session.get(f"{BASE_URL}{ep}")
            assert r.status_code in (401, 403), f"{ep} returned {r.status_code}"


class TestAdminEndpoints:
    def test_stats(self, admin_session):
        session = admin_session
        admin_headers = {}
        r = session.get(f"{BASE_URL}/api/verified-estate/admin/stats", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["listings_total", "listings_published", "listings_draft", "listings_pending_review",
                  "inquiries_new", "external_requests_new", "feature_enabled"]:
            assert k in data
        assert data["listings_published"] >= 2
        assert data["feature_enabled"] is True

    def test_admin_list_all_statuses(self, admin_session):
        session = admin_session
        admin_headers = {}
        r = session.get(f"{BASE_URL}/api/verified-estate/admin/listings", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_admin_list_published(self, admin_session):
        session = admin_session
        admin_headers = {}
        r = session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=published", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_admin_inquiries(self, admin_session):
        session = admin_session
        admin_headers = {}
        r = session.get(f"{BASE_URL}/api/verified-estate/admin/inquiries", headers=admin_headers)
        assert r.status_code == 200
        # We posted at least one in TestInquiry
        assert r.json()["total"] >= 1

    def test_admin_external(self, admin_session):
        session = admin_session
        admin_headers = {}
        r = session.get(f"{BASE_URL}/api/verified-estate/admin/external-requests", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_admin_orders(self, admin_session):
        session = admin_session
        admin_headers = {}
        r = session.get(f"{BASE_URL}/api/verified-estate/admin/orders", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total"] >= 1
        # has demo order
        any_demo = any(it.get("demo_mode") for it in r.json()["items"])
        assert any_demo


class TestAdminGatesEnforcement:
    """Verify publish endpoint enforces the 4 gates."""

    def test_create_draft_without_gates_then_publish_fails(self, admin_session):
        session = admin_session
        admin_headers = {}
        # Create a draft missing audit/twin/recos
        r = session.post(f"{BASE_URL}/api/verified-estate/admin/listings", headers=admin_headers, json={
            "title": "TEST_Draft No Gates",
            "city": "Cluj-Napoca",
            "price_ron": 100000,
            "rooms": 2,
            "surface_sqm": 50,
            "description": "Draft test",
            "transaction_type": "sale",
        })
        assert r.status_code == 200, r.text
        listing = r.json()
        assert listing["status"] == "draft"
        lid = listing["id"]
        # try publish — must fail (gates not met)
        p = session.post(f"{BASE_URL}/api/verified-estate/admin/listings/{lid}/publish", headers=admin_headers)
        assert p.status_code == 400
        # cleanup: archive
        a = session.post(f"{BASE_URL}/api/verified-estate/admin/listings/{lid}/archive", headers=admin_headers)
        assert a.status_code == 200

    def test_archive_published_demo_removes_from_public(self, admin_session):
        session = admin_session
        admin_headers = {}
        # find a published listing
        adm = session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=published",
                          headers=admin_headers).json()
        items = adm["items"]
        if len(items) < 2:
            pytest.skip("Need at least 2 published listings to safely archive one")
        target = items[-1]
        lid = target["id"]
        # archive
        r = session.post(f"{BASE_URL}/api/verified-estate/admin/listings/{lid}/archive", headers=admin_headers)
        assert r.status_code == 200
        # public list should no longer include it
        pub = session.get(f"{BASE_URL}/api/verified-estate/listings").json()
        ids = [x["id"] for x in pub["items"]]
        assert lid not in ids
        # detail returns 404
        d = session.get(f"{BASE_URL}/api/verified-estate/listings/{lid}")
        assert d.status_code == 404
        # restore: re-publish (gates satisfied because demo data has them)
        rp = session.post(f"{BASE_URL}/api/verified-estate/admin/listings/{lid}/publish",
                          headers=admin_headers)
        assert rp.status_code == 200, rp.text
