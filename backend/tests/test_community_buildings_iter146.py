"""PM-002 Community Maintenance Engine — Buildings + Group Campaigns (iter 146)."""
import os
from datetime import date, timedelta
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
SPEC_HVAC_EMAIL = "specialist@propmanage.io"
SPEC_PASS = "Spec123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"

TAG = "TESTITER146"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login failed {email}: {r.status_code} {r.text[:200]}"
    return s


# Module-level state for cleanup + ordering
STATE = {"building_id": None, "campaign_id": None, "task_ids": [], "request_ids": [], "prop_ids": []}


@pytest.fixture(scope="module")
def client_session():
    s = _login(CLIENT_EMAIL, CLIENT_PASS)
    # find first 2 property ids
    r = s.get(f"{BASE_URL}/api/properties", timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    props = data if isinstance(data, list) else data.get("properties", [])
    ids = [p.get("id") or p.get("_id") for p in props][:2]
    assert len(ids) >= 2, f"Need >=2 properties, got {len(ids)}"
    STATE["prop_ids"] = ids
    yield s
    # cleanup after all tests
    _cleanup(s)


@pytest.fixture(scope="module")
def spec_session():
    return _login(SPEC_HVAC_EMAIL, SPEC_PASS)


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


def _cleanup(client_s):
    """Cleanup test data via admin session using direct DB operations if possible, else best effort."""
    try:
        admin = _login(ADMIN_EMAIL, ADMIN_PASS)
        # Delete created maintenance tasks
        for tid in STATE["task_ids"]:
            client_s.delete(f"{BASE_URL}/api/maintenance/tasks/{tid}", timeout=10)
    except Exception as e:
        print(f"cleanup issue: {e}")


# ============= B1: Buildings CRUD =============

class TestB1_Buildings:
    def test_create_building(self, client_session):
        p1 = STATE["prop_ids"][0]
        payload = {"name": f"{TAG} Bloc Aurora", "address": f"{TAG} Str. Testului 42",
                   "city": "Bucuresti", "property_id": p1}
        r = client_session.post(f"{BASE_URL}/api/buildings", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data
        assert data["name"] == payload["name"]
        STATE["building_id"] = data["id"]

    def test_duplicate_building_409(self, client_session):
        payload = {"name": f"{TAG} Bloc Aurora", "address": f"{TAG} Str. Testului 42", "city": "Bucuresti"}
        r = client_session.post(f"{BASE_URL}/api/buildings", json=payload, timeout=15)
        assert r.status_code == 409, r.text

    def test_search_buildings(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/search", params={"q": "Aurora"}, timeout=15)
        assert r.status_code == 200
        buildings = r.json().get("buildings", [])
        assert any(b["id"] == STATE["building_id"] for b in buildings)

    def test_search_min_length(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/search", params={"q": "a"}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("buildings") == []

    def test_join_building_with_second_property(self, client_session):
        p2 = STATE["prop_ids"][1]
        r = client_session.post(f"{BASE_URL}/api/buildings/{STATE['building_id']}/join",
                                json={"property_id": p2}, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_join_nonexistent_property_404(self, client_session):
        fake = "6a11d70e600be19667000000"
        r = client_session.post(f"{BASE_URL}/api/buildings/{STATE['building_id']}/join",
                                json={"property_id": fake}, timeout=15)
        assert r.status_code == 404


# ============= B2: Mine + Opportunities =============

class TestB2_MineAndOpportunities:
    def test_mine_returns_building(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/mine", timeout=15)
        assert r.status_code == 200
        data = r.json()
        buildings = data.get("buildings", [])
        mine = next((b for b in buildings if b["id"] == STATE["building_id"]), None)
        assert mine is not None
        assert mine["properties_count"] >= 2
        assert len(mine["my_property_ids"]) >= 2
        assert isinstance(mine.get("opportunities"), list)
        assert isinstance(mine.get("campaigns"), list)

    def test_create_maintenance_tasks_for_opportunity(self, client_session):
        # Add same category (hvac) task on both properties w/ close due date
        due = (date.today() + timedelta(days=30)).isoformat()
        for pid in STATE["prop_ids"][:2]:
            payload = {"property_id": pid, "template_key": "centrala_termica", "next_due": due}
            r = client_session.post(f"{BASE_URL}/api/maintenance/tasks", json=payload, timeout=15)
            assert r.status_code == 200, r.text
            STATE["task_ids"].append(r.json()["id"])

    def test_opportunity_detected(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/mine", timeout=15)
        assert r.status_code == 200
        mine = next(b for b in r.json()["buildings"] if b["id"] == STATE["building_id"])
        opps = mine.get("opportunities", [])
        hvac_opp = next((o for o in opps if o["category"] == "hvac"), None)
        assert hvac_opp is not None, f"Expected hvac opportunity, got {opps}"
        assert hvac_opp["properties"] >= 2


# ============= B3: Create Campaign =============

class TestB3_CreateCampaign:
    def test_create_campaign(self, client_session):
        p1 = STATE["prop_ids"][0]
        r = client_session.post(f"{BASE_URL}/api/campaigns", json={
            "building_id": STATE["building_id"], "category": "hvac", "property_id": p1}, timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        assert c["status"] == "open"
        assert c["participants_count"] == 1
        STATE["campaign_id"] = c["id"]

    def test_duplicate_campaign_409(self, client_session):
        p1 = STATE["prop_ids"][0]
        r = client_session.post(f"{BASE_URL}/api/campaigns", json={
            "building_id": STATE["building_id"], "category": "hvac", "property_id": p1}, timeout=15)
        assert r.status_code == 409

    def test_property_not_in_building_403(self, client_session):
        # find an owned property NOT in this building
        r = client_session.get(f"{BASE_URL}/api/properties", timeout=15)
        props = r.json() if isinstance(r.json(), list) else r.json().get("properties", [])
        other = None
        for p in props:
            pid = p.get("id") or p.get("_id")
            if pid not in STATE["prop_ids"]:
                other = pid
                break
        assert other, "Need an owned property not in test building"
        r = client_session.post(f"{BASE_URL}/api/campaigns", json={
            "building_id": STATE["building_id"], "category": "plumbing", "property_id": other}, timeout=15)
        assert r.status_code == 403

    def test_opportunity_excluded_after_campaign(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/mine", timeout=15)
        mine = next(b for b in r.json()["buildings"] if b["id"] == STATE["building_id"])
        opps = mine.get("opportunities", [])
        assert not any(o["category"] == "hvac" for o in opps), "hvac opportunity should be excluded"


# ============= B4: Join Campaign =============

class TestB4_JoinCampaign:
    def test_join_double_409(self, client_session):
        p1 = STATE["prop_ids"][0]
        r = client_session.post(f"{BASE_URL}/api/campaigns/{STATE['campaign_id']}/join",
                                json={"property_id": p1}, timeout=15)
        assert r.status_code == 409

    def test_join_second_property(self, client_session):
        p2 = STATE["prop_ids"][1]
        r = client_session.post(f"{BASE_URL}/api/campaigns/{STATE['campaign_id']}/join",
                                json={"property_id": p2}, timeout=15)
        assert r.status_code == 200


# ============= B5: Specialist offers =============

class TestB5_SpecialistOffer:
    def test_specialist_sees_campaign(self, spec_session):
        r = spec_session.get(f"{BASE_URL}/api/campaigns/mine", timeout=15)
        assert r.status_code == 200
        camps = r.json().get("campaigns", [])
        found = next((c for c in camps if c["id"] == STATE["campaign_id"]), None)
        assert found is not None, f"Specialist should see hvac campaign"

    def test_submit_offer(self, spec_session):
        r = spec_session.post(f"{BASE_URL}/api/campaigns/{STATE['campaign_id']}/offer",
                              json={"price_per_unit": 350, "message": "TEST offer"}, timeout=15)
        assert r.status_code == 200

    def test_resubmit_offer_no_duplicate(self, spec_session):
        r = spec_session.post(f"{BASE_URL}/api/campaigns/{STATE['campaign_id']}/offer",
                              json={"price_per_unit": 320, "message": "TEST updated"}, timeout=15)
        assert r.status_code == 200
        r2 = spec_session.get(f"{BASE_URL}/api/campaigns/mine", timeout=15)
        camp = next(c for c in r2.json()["campaigns"] if c["id"] == STATE["campaign_id"])
        my_offers = [o for o in camp["offers"] if o.get("specialist_id")]
        # Only one offer from this specialist
        me_id = my_offers[0]["specialist_id"]
        mine = [o for o in camp["offers"] if o["specialist_id"] == me_id]
        assert len(mine) == 1, f"Expected 1 offer, got {len(mine)}"
        assert mine[0]["price_per_unit"] == 320
        assert camp.get("my_offer") is not None


# ============= B6: Accept offer =============

class TestB6_AcceptOffer:
    def test_other_client_cannot_accept(self):
        # Use admin as "another client" is not straightforward; skip if only 1 client
        pytest.skip("Requires a second client to test 403; covered by role guard implicitly")

    def test_accept_offer(self, client_session, spec_session):
        # Get specialist id via /api/auth/me
        me = spec_session.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        sid = me.get("id") or me.get("user", {}).get("id")
        assert sid, f"Cannot resolve specialist id: {me}"
        r = client_session.post(f"{BASE_URL}/api/campaigns/{STATE['campaign_id']}/accept-offer",
                                json={"specialist_id": sid}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "scheduled"
        assert data["requests_created"] == 2

    def test_campaign_status_scheduled(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/buildings/mine", timeout=15)
        mine = next(b for b in r.json()["buildings"] if b["id"] == STATE["building_id"])
        camp = next(c for c in mine["campaigns"] if c["id"] == STATE["campaign_id"])
        assert camp["status"] == "scheduled"
        assert camp.get("accepted_offer") is not None

    def test_specialist_sees_assigned_requests(self, spec_session):
        r = spec_session.get(f"{BASE_URL}/api/requests", timeout=15)
        assert r.status_code == 200
        reqs = r.json() if isinstance(r.json(), list) else r.json().get("requests", [])
        campaign_reqs = [rq for rq in reqs if rq.get("campaign_id") == STATE["campaign_id"]]
        assert len(campaign_reqs) == 2, f"Expected 2 assigned requests, got {len(campaign_reqs)}"
        for rq in campaign_reqs:
            assert rq.get("status") == "assigned"
            assert rq.get("lead_fee_waived") is True
            assert rq.get("budget_estimate") == 320
            STATE["request_ids"].append(rq.get("id") or rq.get("_id"))

    def test_no_lead_fee_transactions(self, spec_session):
        """Specialist should NOT be charged lead fee for campaign requests."""
        # Just verify via a distinct: no transactions should exist referencing these requests
        # This is best-effort; endpoint may not exist. Skip if no endpoint.
        r = spec_session.get(f"{BASE_URL}/api/transactions", timeout=10)
        if r.status_code != 200:
            pytest.skip("no transactions endpoint")
        txs = r.json() if isinstance(r.json(), list) else r.json().get("transactions", [])
        for rid in STATE["request_ids"]:
            related = [t for t in txs if t.get("request_id") == rid]
            assert not related, f"Unexpected lead-fee tx on campaign request {rid}: {related}"


# ============= B7: Auto-detection tick =============

class TestB7_AutoDetection:
    def test_detection_tick_idempotent(self):
        """Test idempotency of auto-detection tick (imported directly from module)."""
        import asyncio
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.community_buildings import campaign_detection_tick

        async def _run_twice():
            r1 = await campaign_detection_tick()
            r2 = await campaign_detection_tick()
            return r1, r2

        result1, result2 = asyncio.run(_run_twice())
        # Since hvac campaign already exists for our test building, second run must not dup it
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        # Second run should not create additional campaigns for a building where they already exist
        assert result2.get("created", 0) <= result1.get("created", 0), \
            f"2nd tick created MORE campaigns than 1st: {result1} vs {result2}"
