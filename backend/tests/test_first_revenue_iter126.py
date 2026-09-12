"""Iter 126 — FIRST REVENUE tests: War Room, mark-sold, VE checkout demo."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://phased-document.preview.emergentagent.com').rstrip('/')
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    return s


# ---------- WAR ROOM ----------

class TestWarRoom:
    def test_war_room_returns_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/war-room")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["mission"] == "FIRST REVENUE"
        for k in ("milestones", "integrations", "pipeline", "blockers", "founder_actions", "dev_actions", "briefing"):
            assert k in d, f"Missing {k}"
        # milestones: 9 items
        assert len(d["milestones"]) == 9
        ids = {m["id"] for m in d["milestones"]}
        for expected in ("first_customer", "first_real_payment", "first_audit_sold",
                         "first_bundle_sold", "first_digital_twin", "first_verified_property",
                         "first_commission", "first_buyer", "first_invoice"):
            assert expected in ids
        for m in d["milestones"]:
            for k in ("id", "label", "done", "at"):
                assert k in m
        # integrations
        for k in ("stripe", "resend", "checkout"):
            assert k in d["integrations"]
        # pipeline
        for k in ("orders_pending", "orders_paid_real", "revenue_real_ron"):
            assert k in d["pipeline"]
        # briefing q1/q2/q3
        assert d["briefing"].get("q1_revenue_today")
        assert d["briefing"].get("q2_trust_today")
        assert d["briefing"].get("q3_simplicity_today")

    def test_war_room_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/war-room")
        assert r.status_code in (401, 403)


# ---------- VE Checkout Demo Regression ----------

class TestVECheckoutDemo:
    def test_checkout_demo_creates_paid_order(self):
        payload = {
            "package": "audit",
            "contact_name": "QA Test",
            "contact_email": "qa@test.ro",
            "property_address": "Str. Test 5, Cluj",
        }
        r = requests.post(f"{BASE_URL}/api/verified-estate/checkout", json=payload,
                          headers={"Origin": BASE_URL})
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("demo_mode") is True
        assert d.get("session_id", "").startswith("cs_demo_ve_")
        sid = d["session_id"]
        # poll status
        r2 = requests.get(f"{BASE_URL}/api/verified-estate/checkout/status/{sid}")
        assert r2.status_code == 200
        assert r2.json().get("status") == "paid"


# ---------- Mark-Sold flow ----------

class TestMarkSold:
    @pytest.fixture(scope="class")
    def published_listing(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=published&limit=200")
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert items, "No published listings available for testing"
        # Prefer one with digital_twin_id starting with 'demo-' (safe demo target)
        target = next((it for it in items if str(it.get("digital_twin_id", "")).startswith("demo-")), items[0])
        return target

    def test_mark_sold_computes_commission_and_hides_public(self, admin_session, published_listing):
        listing_id = published_listing["id"]
        original_status = published_listing["status"]
        # confirm visible publicly
        pub_r = requests.get(f"{BASE_URL}/api/verified-estate/listings?limit=100")
        assert pub_r.status_code == 200
        public_ids_before = {it["id"] for it in pub_r.json().get("items", [])}
        assert listing_id in public_ids_before, "Listing must appear publicly before sale"

        try:
            r = admin_session.post(
                f"{BASE_URL}/api/verified-estate/admin/listings/{listing_id}/mark-sold",
                json={"sale_price_ron": 250000},
            )
            assert r.status_code == 200, r.text[:300]
            body = r.json()
            sale = body.get("sale")
            assert sale, "sale missing"
            # 2.5% of 250000 = 6250
            assert abs(float(sale["commission_gross_ron"]) - 6250.0) < 0.01
            assert "commission_net_ron" in sale
            sale_id = sale["id"]

            # listing hidden publicly
            pub_after = requests.get(f"{BASE_URL}/api/verified-estate/listings?limit=100")
            assert pub_after.status_code == 200
            public_ids_after = {it["id"] for it in pub_after.json().get("items", [])}
            assert listing_id not in public_ids_after

            # sales list contains it
            sr = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/sales")
            assert sr.status_code == 200
            assert any(s["id"] == sale_id for s in sr.json().get("items", []))

            # stats include the new fields
            st = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/stats")
            assert st.status_code == 200
            stats = st.json()
            for k in ("listings_sold", "commission_net_total_ron", "orders_revenue_real_ron", "orders_revenue_demo_ron"):
                assert k in stats, f"Missing stats key {k}"
            assert stats["listings_sold"] >= 1

        finally:
            # Cleanup: revert listing to published, delete sale doc
            try:
                from pymongo import MongoClient
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "propmanage")
                client = MongoClient(mongo_url)
                db = client[db_name]
                from bson import ObjectId
                db.verified_estate_listings.update_one(
                    {"_id": ObjectId(listing_id)},
                    {"$set": {"status": original_status},
                     "$unset": {"sold_at": "", "sale_price_ron": "", "sale_id": "", "commission_net_ron": ""}}
                )
                db.verified_estate_sales.delete_many({"listing_id": listing_id})
                client.close()
            except Exception as e:
                print(f"Cleanup failed: {e}")

    def test_mark_sold_on_draft_returns_400(self, admin_session):
        # Find any non-published listing (or create a draft)
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/listings?status=draft&limit=1")
        assert r.status_code == 200
        items = r.json().get("items", [])
        if not items:
            # create a listing via admin (starts as draft)
            create = admin_session.post(
                f"{BASE_URL}/api/verified-estate/admin/listings",
                json={
                    "title": "TEST_DRAFT_marksold_negative",
                    "city": "Cluj",
                    "price_ron": 100000,
                    "rooms": 2,
                    "surface_sqm": 50,
                    "transaction_type": "sale",
                },
            )
            assert create.status_code == 200, create.text[:300]
            draft_id = create.json()["id"]
        else:
            draft_id = items[0]["id"]

        try:
            r2 = admin_session.post(
                f"{BASE_URL}/api/verified-estate/admin/listings/{draft_id}/mark-sold",
                json={"sale_price_ron": 100000},
            )
            assert r2.status_code == 400
            detail = r2.json().get("detail", "")
            assert "publicate" in str(detail).lower() or "vând" in str(detail).lower(), f"Expected RO msg, got: {detail}"
        finally:
            # cleanup TEST_ draft
            try:
                from pymongo import MongoClient
                from bson import ObjectId
                mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
                db_name = os.environ.get("DB_NAME", "propmanage")
                client = MongoClient(mongo_url)
                db = client[db_name]
                doc = db.verified_estate_listings.find_one({"_id": ObjectId(draft_id)})
                if doc and doc.get("title", "").startswith("TEST_"):
                    db.verified_estate_listings.delete_one({"_id": ObjectId(draft_id)})
                client.close()
            except Exception as e:
                print(f"Cleanup failed: {e}")


class TestVEStatsAndSales:
    def test_admin_sales_list(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/sales")
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "total" in d

    def test_admin_stats_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/verified-estate/admin/stats")
        assert r.status_code == 200
        d = r.json()
        for k in ("listings_sold", "commission_net_total_ron",
                  "orders_revenue_real_ron", "orders_revenue_demo_ron"):
            assert k in d
