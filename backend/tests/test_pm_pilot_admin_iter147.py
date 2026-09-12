"""PM-PILOT-001 / PM-ADMIN-001 — Administrator Workspace, Building Dashboard, Health Score, Announcements."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"
SPEC_EMAIL = "specialist@propmanage.io"
SPEC_PASS = "Spec123!"


def _login(session: requests.Session, email: str, password: str) -> dict:
    r = session.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="module")
def client_sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    me = _login(s, CLIENT_EMAIL, CLIENT_PASS)
    s.me = me.get("user") or me
    return s


@pytest.fixture(scope="module")
def spec_sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    me = _login(s, SPEC_EMAIL, SPEC_PASS)
    s.me = me.get("user") or me
    return s


@pytest.fixture(scope="module")
def client_property_id(client_sess):
    r = client_sess.get(f"{API}/properties", timeout=20)
    assert r.status_code == 200
    props = r.json() if isinstance(r.json(), list) else r.json().get("properties") or []
    assert props, "no client properties"
    # Find one without building_id preferably
    pref = next((p for p in props if not p.get("building_id")), props[0])
    return pref["id"] if "id" in pref else str(pref.get("_id"))


@pytest.fixture(scope="module")
def created_building(client_sess, client_property_id):
    name = f"[TEST] Bloc Iter147 {uuid.uuid4().hex[:6]}"
    r = client_sess.post(f"{API}/buildings", json={
        "name": name, "address": f"Str. Testarilor {uuid.uuid4().hex[:5]}", "city": "București",
        "property_id": client_property_id,
    }, timeout=20)
    assert r.status_code == 200, f"create building failed: {r.status_code} {r.text[:300]}"
    data = r.json()
    bid = data["id"]
    yield {"id": bid, "name": name, "property_id": client_property_id}
    # cleanup
    try:
        # unset building_id on the property
        pass
    except Exception:
        pass


# ============= P1 =============
class TestP1CreateAndPatch:
    def test_create_sets_administrator(self, client_sess, created_building):
        # verify via /buildings/mine that is_admin=True
        r = client_sess.get(f"{API}/buildings/mine", timeout=20)
        assert r.status_code == 200
        buildings = r.json()["buildings"]
        b = next((x for x in buildings if x["id"] == created_building["id"]), None)
        assert b is not None, "created building not in /buildings/mine"
        assert b["is_admin"] is True

    def test_patch_success(self, client_sess, created_building):
        bid = created_building["id"]
        r = client_sess.patch(f"{API}/buildings/{bid}", json={
            "apartments_total": 40, "floors": 10, "construction_year": 1998
        }, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["apartments_total"] == 40
        assert data["floors"] == 10
        assert data["construction_year"] == 1998

    def test_patch_empty_body_400(self, client_sess, created_building):
        r = client_sess.patch(f"{API}/buildings/{created_building['id']}", json={}, timeout=20)
        assert r.status_code == 400

    def test_patch_403_for_other_user(self, spec_sess, created_building):
        r = spec_sess.patch(f"{API}/buildings/{created_building['id']}", json={"floors": 5}, timeout=20)
        assert r.status_code == 403


# ============= P2 =============
class TestP2Portfolio:
    def test_portfolio_contains_building(self, client_sess, created_building):
        r = client_sess.get(f"{API}/admin-workspace/portfolio", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "totals" in data and "buildings" in data
        totals = data["totals"]
        for k in ["buildings", "apartments", "residents", "green", "yellow", "red"]:
            assert k in totals
        b = next((x for x in data["buildings"] if x["id"] == created_building["id"]), None)
        assert b is not None
        for k in ["properties_count", "members_count", "open_requests", "overdue_tasks",
                  "active_campaigns", "health"]:
            assert k in b
        assert "score" in b["health"] and "status" in b["health"] and "components" in b["health"]
        assert len(b["health"]["components"]) == 5

    def test_portfolio_empty_for_non_admin(self, spec_sess):
        r = spec_sess.get(f"{API}/admin-workspace/portfolio", timeout=20)
        assert r.status_code == 200
        # specialist may have zero admin buildings
        assert isinstance(r.json().get("buildings"), list)


# ============= P3 Health Score =============
class TestP3Health:
    def test_health_components_structure(self, client_sess, created_building):
        r = client_sess.get(f"{API}/buildings/{created_building['id']}/dashboard", timeout=20)
        assert r.status_code == 200, r.text
        health = r.json()["health"]
        keys = {c["key"] for c in health["components"]}
        assert keys == {"coverage", "punctuality", "responsiveness", "activation", "community"}
        weights = sum(c["weight"] for c in health["components"])
        assert weights == 100
        for c in health["components"]:
            assert "detail" in c and isinstance(c["detail"], str)

    def test_health_changes_with_announcement(self, client_sess, created_building):
        r0 = client_sess.get(f"{API}/buildings/{created_building['id']}/dashboard", timeout=20)
        comm0 = next(c for c in r0.json()["health"]["components"] if c["key"] == "community")["value"]
        r = client_sess.post(f"{API}/buildings/{created_building['id']}/announcements", json={
            "title": "[TEST] Health boost", "body": "Verificam impactul asupra scorului comunitar."
        }, timeout=20)
        assert r.status_code == 200
        time.sleep(0.5)
        r2 = client_sess.get(f"{API}/buildings/{created_building['id']}/dashboard", timeout=20)
        comm1 = next(c for c in r2.json()["health"]["components"] if c["key"] == "community")["value"]
        assert comm1 >= comm0, f"community expected to increase or stay, got {comm0}->{comm1}"


# ============= P4 Dashboard access =============
class TestP4Dashboard:
    def test_admin_access(self, client_sess, created_building):
        r = client_sess.get(f"{API}/buildings/{created_building['id']}/dashboard", timeout=20)
        assert r.status_code == 200
        data = r.json()
        for k in ["apartments", "upcoming_maintenance", "opportunities", "campaigns",
                  "announcements", "invite_link", "is_admin"]:
            assert k in data
        assert data["is_admin"] is True
        assert "/register?binvite=" in data["invite_link"]
        for a in data["apartments"]:
            # first name only, no space (Romanian first names are single tokens)
            assert " " not in (a["owner_first_name"] or ""), \
                f"owner_first_name should be first name only: {a['owner_first_name']}"

    def test_non_member_403(self, spec_sess, created_building):
        r = spec_sess.get(f"{API}/buildings/{created_building['id']}/dashboard", timeout=20)
        assert r.status_code == 403


# ============= P5 Announcements =============
class TestP5Announcements:
    def test_admin_creates_announcement(self, client_sess, created_building):
        r = client_sess.post(f"{API}/buildings/{created_building['id']}/announcements", json={
            "title": "[TEST] Anunț oficial", "body": "Corp anunț de test iter147."
        }, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["title"] == "[TEST] Anunț oficial"

    def test_admin_lists(self, client_sess, created_building):
        r = client_sess.get(f"{API}/buildings/{created_building['id']}/announcements", timeout=20)
        assert r.status_code == 200
        anns = r.json()["announcements"]
        assert any(a["title"] == "[TEST] Anunț oficial" for a in anns)

    def test_non_member_403_list(self, spec_sess, created_building):
        r = spec_sess.get(f"{API}/buildings/{created_building['id']}/announcements", timeout=20)
        assert r.status_code == 403

    def test_non_member_403_create(self, spec_sess, created_building):
        r = spec_sess.post(f"{API}/buildings/{created_building['id']}/announcements", json={
            "title": "[TEST] not allowed", "body": "should be 403"
        }, timeout=20)
        assert r.status_code == 403


# ============= P6 Preview =============
class TestP6Preview:
    def test_preview_accessible_to_any_user(self, spec_sess, created_building):
        r = spec_sess.get(f"{API}/buildings/{created_building['id']}/preview", timeout=20)
        assert r.status_code == 200
        data = r.json()
        for k in ["id", "name", "address", "members_count"]:
            assert k in data
        # Sensitive fields should NOT be exposed
        for sensitive in ["administrator_id", "created_by", "apartments_total", "floors", "construction_year"]:
            assert sensitive not in data, f"preview should not expose {sensitive}"


# ============= P7 /buildings/mine =============
class TestP7Mine:
    def test_mine_has_is_admin_and_announcements(self, client_sess, created_building):
        r = client_sess.get(f"{API}/buildings/mine", timeout=20)
        assert r.status_code == 200
        b = next((x for x in r.json()["buildings"] if x["id"] == created_building["id"]), None)
        assert b is not None
        assert b["is_admin"] is True
        assert "announcements" in b
        assert len(b["announcements"]) <= 3


# ============= CLEANUP =============
def test_zzz_cleanup(client_sess, created_building):
    """Cleanup all test data: unset building_id, delete announcements + building."""
    from pymongo import MongoClient
    import os as _os
    mongo_url = _os.environ.get("MONGO_URL")
    db_name = _os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        # try backend .env
        with open("/app/backend/.env") as f:
            for line in f:
                if line.startswith("MONGO_URL="):
                    mongo_url = line.split("=", 1)[1].strip()
                elif line.startswith("DB_NAME="):
                    db_name = line.split("=", 1)[1].strip()
    mc = MongoClient(mongo_url)
    db = mc[db_name]
    from bson import ObjectId
    bid = created_building["id"]
    db.properties.update_many({"building_id": bid}, {"$unset": {"building_id": ""}})
    db.building_announcements.delete_many({"building_id": bid})
    db.community_campaigns.delete_many({"building_id": bid})
    db.buildings.delete_one({"_id": ObjectId(bid)})
    # cleanup notifications produced by our test announcements
    db.notifications.delete_many({"type": "building_announcement",
                                  "title": {"$regex": r"\[TEST\]"}})
    print(f"Cleaned building {bid}")
