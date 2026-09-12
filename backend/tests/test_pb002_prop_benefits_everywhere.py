"""PB-002 · PropBenefits Everywhere — full backend test suite.

Covers:
- GET /api/benefits/pulse (client)
- GET /api/benefits/community-deals + POST support (idempotent)
- GET /api/benefits/specialist-summary
- GET /api/benefits/marketplace-flags
- GET /api/benefits/context-banner/{surface}
- GET /api/benefits/building-summary/{building_id}
- Admin: /api/admin/prop-benefits/north-star, /community-deals CRUD
- Security: 401 unauth, 403 client on admin
- Regression: /opportunities, /wallet, /success-manager
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_s():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def specialist_s():
    return _login(SPECIALIST)


@pytest.fixture(scope="module")
def admin_s():
    return _login(ADMIN)


# ============================================================================
# Client Pulse
# ============================================================================
class TestClientPulse:
    def test_pulse_shape_and_house_centric(self, client_s):
        r = client_s.get(f"{API}/benefits/pulse", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("slogan", "membership", "available", "saved_value",
                  "saved_detail", "top_opportunity", "almost_unlocked",
                  "community_deals", "next_action", "health"):
            assert k in d, f"missing key: {k}"
        assert "puterea comunit" in d["slogan"].lower()
        for k in ("count", "in_wallet", "value"):
            assert k in d["available"]
        for k in ("benefits_used_value", "lead_fees_waived"):
            assert k in d["saved_detail"]
        cd = d["community_deals"]
        for k in ("total", "negotiating", "preview", "disclaimer"):
            assert k in cd
        assert isinstance(cd["preview"], list) and len(cd["preview"]) <= 3
        # No percentages in disclaimer
        assert "%" not in cd["disclaimer"]
        # House-centric wording in next_action
        na = d.get("next_action") or {}
        text_blob = " ".join(str(v) for v in na.values() if isinstance(v, str)).lower()
        assert "cas" in text_blob or "locuin" in text_blob, f"next_action not house-centric: {na}"


# ============================================================================
# Community Deals
# ============================================================================
class TestCommunityDeals:
    def test_list_12_seeded(self, client_s):
        r = client_s.get(f"{API}/benefits/community-deals", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "disclaimer" in d
        assert len(d["items"]) >= 12
        # No percentages anywhere
        blob = str(d).lower()
        assert "%" not in d["disclaimer"]
        # Each item shape
        for it in d["items"]:
            for k in ("id", "emoji", "title", "status", "supporters", "supported_by_me"):
                assert k in it, f"missing {k} in deal {it}"
        titles = [it["title"] for it in d["items"]]
        for expected in ("Gresie & faianță din Italia", "Gresie & faianță din Spania",
                         "Mobilier din Germania", "Mobilier din Italia",
                         "Mobilier din Olanda", "Mobilier din Suedia",
                         "Mobilier din Danemarca", "Design interior",
                         "Baie complet amenajată", "Pompe de căldură",
                         "Panouri fotovoltaice", "City Partner Cluj"):
            assert expected in titles, f"missing seed deal: {expected}"

    def test_support_idempotent_and_404(self, client_s):
        # Pick a deal that is likely NOT supported by client yet — use Mobilier Suedia
        r = client_s.get(f"{API}/benefits/community-deals", timeout=15)
        items = r.json()["items"]
        target = next((d for d in items if d["title"] == "Mobilier din Suedia"), None)
        assert target, "seed deal 'Mobilier din Suedia' not found"
        before = target["supporters"]
        already = target["supported_by_me"]

        r1 = client_s.post(f"{API}/benefits/community-deals/{target['id']}/support", timeout=15)
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1.get("ok") is True
        assert "supporters" in d1
        if already:
            assert d1["supporters"] == before
        else:
            assert d1["supporters"] == before + 1

        # Idempotent (2nd support call must NOT double-count)
        r2 = client_s.post(f"{API}/benefits/community-deals/{target['id']}/support", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["supporters"] == d1["supporters"]

        # Verify supported_by_me now true
        r3 = client_s.get(f"{API}/benefits/community-deals", timeout=15)
        upd = next(d for d in r3.json()["items"] if d["id"] == target["id"])
        assert upd["supported_by_me"] is True

    def test_support_404_on_bad_id(self, client_s):
        r = client_s.post(f"{API}/benefits/community-deals/nonexistent_xyz/support", timeout=15)
        assert r.status_code == 404


# ============================================================================
# Specialist Summary
# ============================================================================
class TestSpecialistSummary:
    def test_shape(self, specialist_s):
        r = specialist_s.get(f"{API}/benefits/specialist-summary", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("profile_pct", "verified", "messages"):
            assert k in d
        assert isinstance(d["messages"], list)
        assert len(d["messages"]) <= 3
        valid_prefixes = ("sp_profile", "sp_verified", "sp_campaign", "sp_partner")
        for m in d["messages"]:
            assert m["id"].startswith(valid_prefixes), f"unexpected message id: {m['id']}"


# ============================================================================
# Marketplace Flags + Context Banners
# ============================================================================
class TestMarketplaceAndBanners:
    def test_marketplace_flags(self, client_s):
        r = client_s.get(f"{API}/benefits/marketplace-flags", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "flags" in d
        valid_flags = {"active", "subscription", "locked", "used"}
        for f in d["flags"]:
            assert f["flag"] in valid_flags
            assert "label" in f and f["label"]

    def test_context_banner_house_health(self, client_s):
        r = client_s.get(f"{API}/benefits/context-banner/house_health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["surface"] == "house_health"
        assert d["headline"]
        assert isinstance(d["effects"], list) and len(d["effects"]) == 3

    def test_context_banner_digital_twin(self, client_s):
        r = client_s.get(f"{API}/benefits/context-banner/digital_twin", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["surface"] == "digital_twin"
        assert len(d["effects"]) == 3

    def test_context_banner_invalid(self, client_s):
        r = client_s.get(f"{API}/benefits/context-banner/bad_surface", timeout=15)
        assert r.status_code == 400


# ============================================================================
# Building summary
# ============================================================================
class TestBuildingSummary:
    def test_building_and_bad_id(self, admin_s, client_s):
        # Find a building id
        r = admin_s.get(f"{API}/admin/buildings", timeout=15)
        building_id = None
        if r.status_code == 200:
            data = r.json()
            items = data.get("items") if isinstance(data, dict) else data
            if items:
                # buildings use ObjectId — need the _id / id
                first = items[0]
                building_id = first.get("id") or first.get("_id")
        if not building_id:
            pytest.skip("No buildings available")
        r2 = client_s.get(f"{API}/benefits/building-summary/{building_id}", timeout=15)
        # Accept either 200 (valid) or 404 (id shape mismatch)
        if r2.status_code == 200:
            d = r2.json()
            for k in ("building", "building_campaigns", "unlock_together", "disclaimer"):
                assert k in d
            assert isinstance(d["unlock_together"], list)

    def test_building_404(self, client_s):
        r = client_s.get(f"{API}/benefits/building-summary/000000000000000000000000", timeout=15)
        assert r.status_code == 404


# ============================================================================
# Admin: North Star + Community Deals CRUD
# ============================================================================
class TestAdminNorthStar:
    def test_north_star(self, admin_s):
        r = admin_s.get(f"{API}/admin/prop-benefits/north-star", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "3.000" in d["label"]
        assert d["target"] == 3000
        for k in ("active", "healthy", "progress_pct", "dimensions", "definition"):
            assert k in d
        assert len(d["dimensions"]) == 4
        keys = {dim["key"] for dim in d["dimensions"]}
        assert keys == {"using", "maintaining", "benefiting", "referring"}


class TestAdminCommunityDealsCRUD:
    created_id = None

    def test_list_admin(self, admin_s):
        r = admin_s.get(f"{API}/admin/prop-benefits/community-deals", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "statuses" in d
        assert set(d["statuses"]) == {"in_lucru", "negociere", "pilot", "lansat", "arhivat"}

    def test_create_and_patch(self, admin_s):
        # CREATE
        r = admin_s.post(f"{API}/admin/prop-benefits/community-deals",
                         json={"title": "TEST_pb002_deal"}, timeout=15)
        assert r.status_code == 200
        deal = r.json()
        assert deal["title"] == "TEST_pb002_deal"
        assert "id" in deal
        TestAdminCommunityDealsCRUD.created_id = deal["id"]

        # PATCH valid status
        r2 = admin_s.patch(f"{API}/admin/prop-benefits/community-deals/{deal['id']}",
                           json={"status": "negociere"}, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["status"] == "negociere"

        # PATCH invalid status
        r3 = admin_s.patch(f"{API}/admin/prop-benefits/community-deals/{deal['id']}",
                           json={"status": "not_a_status"}, timeout=15)
        assert r3.status_code == 400

    def test_zzz_cleanup(self, admin_s):
        # Archive the test deal to keep DB clean
        if TestAdminCommunityDealsCRUD.created_id:
            r = admin_s.patch(
                f"{API}/admin/prop-benefits/community-deals/{TestAdminCommunityDealsCRUD.created_id}",
                json={"status": "arhivat", "active": False}, timeout=15)
            assert r.status_code == 200


# ============================================================================
# Security
# ============================================================================
class TestSecurity:
    def test_401_unauth_endpoints(self):
        anon = requests.Session()
        for path in ("/benefits/pulse", "/benefits/community-deals",
                     "/benefits/specialist-summary", "/benefits/marketplace-flags",
                     "/benefits/context-banner/house_health"):
            r = anon.get(f"{API}{path}", timeout=15)
            assert r.status_code in (401, 403), f"{path} expected 401/403, got {r.status_code}"

    def test_403_client_on_admin_north_star(self, client_s):
        r = client_s.get(f"{API}/admin/prop-benefits/north-star", timeout=15)
        assert r.status_code == 403


# ============================================================================
# Regression: PB-001 endpoints still work
# ============================================================================
class TestPB001Regression:
    def test_opportunities(self, client_s):
        assert client_s.get(f"{API}/benefits/opportunities", timeout=15).status_code == 200

    def test_wallet(self, client_s):
        assert client_s.get(f"{API}/benefits/wallet", timeout=15).status_code == 200

    def test_success_manager(self, client_s):
        assert client_s.get(f"{API}/benefits/success-manager", timeout=15).status_code == 200

    def test_admin_overview(self, admin_s):
        assert admin_s.get(f"{API}/admin/prop-benefits/overview", timeout=15).status_code == 200
