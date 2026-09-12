"""
Iter 138 — Launch Readiness Run 1: Visitor + Owner + Buyer journeys.
End-to-end backend validation of the flows a real user would follow on the
preview URL. Reports every step PASS/FAIL, does not stop at first failure.
"""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PWD = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PWD = "1!nasov01ADMIN"

PROTECTED_SLUG = "gbegxfyz9m"  # do NOT touch


# ------------------------------ fixtures ------------------------------

@pytest.fixture(scope="module")
def new_client_email():
    return f"TEST_iter138_{uuid.uuid4().hex[:10]}@gmail.com"


@pytest.fixture(scope="module")
def new_client_creds(new_client_email):
    return {"email": new_client_email, "password": "TestPwd123!", "name": "Test Iter138"}


@pytest.fixture(scope="module")
def new_client_session(new_client_creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/register", json={
        "email": new_client_creds["email"],
        "password": new_client_creds["password"],
        "name": new_client_creds["name"],
        "role": "client",
        "phone": "0712345678",
        "terms_accepted": True,
        "privacy_policy_accepted": True,
        "marketing_consent": False,
    }, timeout=30)
    assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code}")
    return s


# ------------------------------ VISITOR ------------------------------

class TestVisitorJourney:

    def test_landing_health(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code in (200, 404), r.status_code

    def test_register_new_client(self, new_client_session, new_client_creds):
        # register was performed in fixture; verify /auth/me returns user
        r = new_client_session.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert (data.get("email") or "").lower() == new_client_creds["email"].lower()
        assert data.get("role") == "client"

    def test_logout_and_relogin(self, new_client_creds):
        s = requests.Session()
        # login
        r = s.post(f"{BASE_URL}/api/auth/login", json={
            "email": new_client_creds["email"],
            "password": new_client_creds["password"],
        }, timeout=15)
        assert r.status_code == 200, r.text[:300]
        # logout
        rl = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert rl.status_code in (200, 204)
        # me should now be 401
        rme = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert rme.status_code in (401, 403)
        # re-login
        r2 = s.post(f"{BASE_URL}/api/auth/login", json={
            "email": new_client_creds["email"],
            "password": new_client_creds["password"],
        }, timeout=15)
        assert r2.status_code == 200

    def test_register_empty_body_returns_validation_error(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={}, timeout=15)
        assert r.status_code in (400, 422), r.status_code

    def test_register_without_terms_rejected(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"TEST_notos_{uuid.uuid4().hex[:6]}@gmail.com",
            "password": "TestPwd123!",
            "name": "No Terms",
            "role": "client",
            "terms_accepted": False,
            "privacy_policy_accepted": True,
        }, timeout=15)
        assert r.status_code == 400


# ------------------------------ OWNER ------------------------------

class TestOwnerJourney:

    def test_create_property(self, new_client_session):
        r = new_client_session.post(f"{BASE_URL}/api/properties", json={
            "name": "TEST Iter138 Property",
            "type": "apartment",
            "surface": 65,
            "rooms": 3,
            "address": "Str. Test 1, Cluj-Napoca",
        }, timeout=20)
        assert r.status_code in (200, 201), r.text[:400]
        data = r.json()
        pid = data.get("id") or data.get("_id") or data.get("property_id")
        assert pid, f"no property id in response: {data}"
        pytest.property_id = pid  # stash for later tests

    def test_property_appears_in_list(self, new_client_session):
        r = new_client_session.get(f"{BASE_URL}/api/properties", timeout=15)
        assert r.status_code == 200, r.text[:200]
        items = r.json()
        if isinstance(items, dict):
            items = items.get("items") or items.get("properties") or []
        ids = [str(p.get("id") or p.get("_id")) for p in items]
        assert str(pytest.property_id) in ids

    def test_upload_photo_document(self, new_client_session):
        pid = pytest.property_id
        # 1x1 PNG bytes
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\xdc\xcc\x8bR\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        files = {"file": ("test.png", png, "image/png")}
        data = {"category": "foto", "title": "TEST photo"}
        r = new_client_session.post(f"{BASE_URL}/api/properties/{pid}/documents", files=files, data=data, timeout=30)
        assert r.status_code in (200, 201), r.text[:400]
        body = r.json()
        doc = body.get("document") or body
        assert doc.get("id") or doc.get("document_id") or doc.get("_id")

    def test_upload_pdf_document(self, new_client_session):
        pid = pytest.property_id
        pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
        files = {"file": ("factura.pdf", pdf, "application/pdf")}
        data = {"category": "factura", "title": "TEST factura"}
        r = new_client_session.post(f"{BASE_URL}/api/properties/{pid}/documents", files=files, data=data, timeout=30)
        assert r.status_code in (200, 201), r.text[:400]

    def test_documents_appear_in_vault(self, new_client_session):
        pid = pytest.property_id
        r = new_client_session.get(f"{BASE_URL}/api/properties/{pid}/documents", timeout=15)
        assert r.status_code == 200
        docs = r.json()
        if isinstance(docs, dict):
            docs = docs.get("items") or docs.get("documents") or []
        assert len(docs) >= 2, f"expected >=2 docs, got {len(docs)}"

    def test_completeness_score(self, new_client_session):
        pid = pytest.property_id
        r = new_client_session.get(f"{BASE_URL}/api/properties/{pid}/completeness", timeout=15)
        assert r.status_code == 200
        assert "score" in r.json() or "completeness" in r.json() or "percentage" in r.json()

    def test_passport_enable_and_public(self, new_client_session):
        pid = pytest.property_id
        r = new_client_session.post(f"{BASE_URL}/api/properties/{pid}/passport/enable", timeout=15)
        assert r.status_code in (200, 201), r.text[:300]
        data = r.json()
        slug = data.get("slug") or (data.get("passport") or {}).get("slug")
        assert slug, f"no slug: {data}"
        pytest.passport_slug = slug
        # public endpoint should load
        r_pub = requests.get(f"{BASE_URL}/api/p/{slug}", timeout=15)
        assert r_pub.status_code == 200, f"public passport failed: {r_pub.status_code}"

    def test_protected_slug_still_alive(self):
        # DO NOT touch, just verify it's still 200
        r = requests.get(f"{BASE_URL}/api/p/{PROTECTED_SLUG}", timeout=15)
        assert r.status_code == 200, f"Protected slug {PROTECTED_SLUG} broken: {r.status_code}"

    def test_external_audit_request(self):
        # Public endpoint — sell/audit flow
        r = requests.post(f"{BASE_URL}/api/verified-estate/external-audit-request", json={
            "external_listing_url": "https://example.com/listing/123",
            "property_address": "Str. TEST 5, Cluj",
            "contact_name": "TEST Iter138 Owner",
            "contact_email": f"TEST_iter138_sell_{uuid.uuid4().hex[:6]}@gmail.com".lower(),
            "contact_phone": "0712345678",
            "notes": "iter138 owner sell test",
            "budget_ron": 100000,
        }, timeout=15)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

    def test_admin_can_see_external_request(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/external-requests", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        # at least one recent TEST_ contact_email exists
        assert any("test_iter138_sell_" in (i.get("contact_email") or "") for i in items[:50]), \
            "external audit request not visible to admin"


# ------------------------------ BUYER ------------------------------

class TestBuyerJourney:

    def test_public_listings_load(self):
        r = requests.get(f"{BASE_URL}/api/verified-estate/listings", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "items" in data and "total" in data
        pytest.listings = data["items"]

    def test_listing_filters_change_results(self):
        r_all = requests.get(f"{BASE_URL}/api/verified-estate/listings", timeout=15)
        r_sale = requests.get(f"{BASE_URL}/api/verified-estate/listings", params={"transaction_type": "sale"}, timeout=15)
        r_rent = requests.get(f"{BASE_URL}/api/verified-estate/listings", params={"transaction_type": "rent"}, timeout=15)
        assert r_all.status_code == r_sale.status_code == r_rent.status_code == 200
        # results should not exceed all
        assert r_sale.json()["total"] <= r_all.json()["total"]
        assert r_rent.json()["total"] <= r_all.json()["total"]

    def test_listing_price_filter(self):
        r = requests.get(f"{BASE_URL}/api/verified-estate/listings", params={"price_min": 1, "price_max": 999999999}, timeout=15)
        assert r.status_code == 200

    def test_listing_detail(self):
        if not getattr(pytest, "listings", None):
            pytest.skip("no published listings")
        first = pytest.listings[0]
        lid = first.get("id") or first.get("_id")
        r = requests.get(f"{BASE_URL}/api/verified-estate/listings/{lid}", timeout=15)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        # must include enough detail so page is not a dead-end
        assert data.get("title") or data.get("id")

    def test_send_inquiry(self):
        if not getattr(pytest, "listings", None):
            pytest.skip("no published listings")
        lid = pytest.listings[0].get("id") or pytest.listings[0].get("_id")
        pytest.inquiry_email = f"TEST_iter138_buyer_{uuid.uuid4().hex[:6]}@gmail.com"
        r = requests.post(f"{BASE_URL}/api/verified-estate/inquiries", json={
            "listing_id": lid,
            "name": "TEST Iter138 Buyer",
            "email": pytest.inquiry_email,
            "phone": "0712345678",
            "message": "iter138 buyer inquiry test",
            "intent": "viewing",
        }, timeout=15)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

    def test_inquiry_visible_to_admin(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/inquiries", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert any(i.get("email") == getattr(pytest, "inquiry_email", "").lower() for i in items[:30]), \
            "inquiry not visible to admin"

    def test_pricing_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/verified-estate/pricing", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for k in ("audit_ron", "twin_ron", "commission_pct", "currency"):
            assert k in data, f"missing {k}"

    def test_checkout_returns_url_or_demo(self):
        r = requests.post(f"{BASE_URL}/api/verified-estate/checkout", json={
            "package": "audit",
            "contact_name": "TEST Iter138 Buyer",
            "contact_email": f"TEST_iter138_co_{uuid.uuid4().hex[:6]}@gmail.com",
            "contact_phone": "0712345678",
            "property_address": "Str. TEST 9, Cluj",
            "notes": "iter138 checkout test",
        }, timeout=30)
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        # Either Stripe URL or a demo redirect URL — both are OK (not a dead-end)
        assert (data.get("checkout_url") or data.get("url") or data.get("session_url")), \
            f"no checkout url in response: {data}"


# --------------- Public pages dead-end hunt (frontend loads) ---------------

class TestPublicPagesLoad:

    @pytest.mark.parametrize("path", [
        "/",
        "/imobile-verificate",
        "/imobile-verificate/sell",
        "/register",
        "/login",
        f"/p/{PROTECTED_SLUG}",
    ])
    def test_frontend_page_loads(self, path):
        r = requests.get(f"{BASE_URL}{path}", timeout=20, allow_redirects=True)
        # SPA — everything should return 200 with the shell
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        assert "<html" in r.text.lower() or "<!doctype" in r.text.lower()
