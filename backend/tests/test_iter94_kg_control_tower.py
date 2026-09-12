"""Iter94 — KG-0 + Executive Control Tower backend tests (Sprint C)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"

VALID_RELS = {"pays_for", "for_work", "on_property", "requested_by", "assigned_to", "owned_by", "disputes"}
VALID_NODE_TYPES = {"dispute", "property", "request", "transaction", "user"}


@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    # Try both possible admin passwords
    for pwd in ["1!nasov01ADMIN", "Admin123!"]:
        r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": pwd})
        if r.status_code == 200:
            print(f"[admin login OK with password variant]")
            return s
    pytest.fail(f"Admin login failed (both password variants). Last status={r.status_code} body={r.text[:300]}")


@pytest.fixture(scope="session")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD})
    if r.status_code != 200:
        pytest.skip(f"Client login failed: {r.status_code}")
    return s


@pytest.fixture(scope="session")
def anon_session():
    return requests.Session()


# ─────────────────── 1. KG stats ───────────────────
class TestKGStats:
    def test_stats_shape_and_values(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/kg/stats")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total_links" in data
        assert "by_rel" in data
        assert "node_types" in data
        assert isinstance(data["total_links"], int)
        assert data["total_links"] >= 1500, f"Expected ~1625, got {data['total_links']}"
        # by_rel is list of {rel, count}
        rels = {row["rel"] for row in data["by_rel"]}
        assert rels == VALID_RELS, f"Expected {VALID_RELS}, got {rels}"
        assert len(data["by_rel"]) == 7
        # node_types
        nts = set(data["node_types"])
        assert VALID_NODE_TYPES.issubset(nts), f"Expected superset of {VALID_NODE_TYPES}, got {nts}"


# ─────────────────── 2. Backfill idempotent ───────────────────
class TestKGBackfill:
    def test_backfill_idempotent(self, admin_session):
        # Get baseline
        r0 = admin_session.get(f"{BASE_URL}/api/admin/kg/stats")
        assert r0.status_code == 200
        total_before = r0.json()["total_links"]

        # Run backfill
        r1 = admin_session.post(f"{BASE_URL}/api/admin/kg/backfill")
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert "created" in d1
        assert "total_new" in d1
        assert "total_links" in d1
        # Second run should be idempotent
        r2 = admin_session.post(f"{BASE_URL}/api/admin/kg/backfill")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["total_new"] == 0, f"Expected total_new=0 on 2nd run, got {d2['total_new']}"
        assert d2["total_links"] == d1["total_links"], "Total links must not change between runs"
        assert d2["total_links"] == total_before or d2["total_links"] >= total_before


# ─────────────────── 3. Entity walk ───────────────────
class TestKGEntity:
    def test_entity_walk_request(self, admin_session):
        # Pick a from_id from stats
        # We need a request id with requested_by rel — do direct query via /entity endpoint.
        # First get a link via stats + we need a real from_id. Query request entity by iterating.
        # Simplest: get any entity_links via mongo? We use kg/entity/{type}/{id}. Need a real id.
        # Try /api/admin/users to find a client that has a request
        # Better: pick any known request/property. Fall back to failing gracefully.
        # Use /api/admin/kg/entity/{type}/{id} — need id. Grab from /api/admin/requests? Not sure endpoint exists.
        # Fall back: use /api/admin/users to walk user->request via incoming edges.
        r_users = admin_session.get(f"{BASE_URL}/api/admin/users", params={"role": "client", "limit": 200})
        if r_users.status_code != 200:
            pytest.skip(f"cannot list users: {r_users.status_code}")
        users = r_users.json().get("items") or r_users.json()
        if not users:
            pytest.skip("no client users found")

        # Walk the graph starting from a user (iterate up to 50 users)
        request_id = None
        for u in users[:50]:
            uid = u.get("id")
            if not uid:
                continue
            r_u = admin_session.get(f"{BASE_URL}/api/admin/kg/entity/user/{uid}")
            assert r_u.status_code == 200, r_u.text
            data = r_u.json()
            assert data["entity"]["type"] == "user"
            assert data["entity"]["id"] == uid
            # find incoming requested_by (request -> requested_by -> user)
            for edge in data.get("incoming", []):
                if edge.get("rel") == "requested_by" and edge.get("from_type") == "request":
                    request_id = edge["from_id"]
                    break
            if request_id:
                break

        if not request_id:
            pytest.skip("no request linked to any client user found in graph")

        r = admin_session.get(f"{BASE_URL}/api/admin/kg/entity/request/{request_id}")
        assert r.status_code == 200
        d = r.json()
        assert d["entity"]["type"] == "request"
        assert d["entity"]["id"] == request_id
        # outgoing rels — should include requested_by → user
        out_rels = {e["rel"] for e in d["outgoing"]}
        assert "requested_by" in out_rels

    def test_entity_invalid_type_returns_400(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/kg/entity/foo/123")
        assert r.status_code == 400, f"Expected 400 got {r.status_code}: {r.text}"

    def test_entity_rel_filter(self, admin_session):
        # Grab a user id
        r_users = admin_session.get(f"{BASE_URL}/api/admin/users", params={"role": "client", "limit": 1})
        if r_users.status_code != 200 or not (r_users.json().get("items") or r_users.json()):
            pytest.skip("no users")
        items = r_users.json().get("items") or r_users.json()
        uid = items[0]["id"]
        r = admin_session.get(f"{BASE_URL}/api/admin/kg/entity/user/{uid}", params={"rel": "requested_by"})
        assert r.status_code == 200
        d = r.json()
        # all edges (in+out) must be requested_by
        for e in d["outgoing"] + d["incoming"]:
            assert e["rel"] == "requested_by"


# ─────────────────── 4. Control Tower ───────────────────
class TestControlTower:
    def test_control_tower_shape(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/control-tower")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "attention" in d
        assert "pulse" in d
        assert "autonomy_report" in d

        # attention list — up to 5
        assert isinstance(d["attention"], list)
        assert len(d["attention"]) <= 5

        # attention schema per item
        for item in d["attention"]:
            for key in ["id", "severity", "situatie", "propunere", "impact_estimat", "actiune_1tap", "sursa_semnalului", "count"]:
                assert key in item, f"Missing key {key} in attention item {item}"
            assert set(item["actiune_1tap"].keys()) >= {"label", "route"}
            assert isinstance(item["actiune_1tap"]["label"], str)
            assert isinstance(item["actiune_1tap"]["route"], str)
            assert item["severity"] in ["critical", "warning", "info"]

        # attention sorted critical first
        sev_rank = {"critical": 0, "warning": 1, "info": 2}
        prev_rank = -1
        for item in d["attention"]:
            r_cur = sev_rank.get(item["severity"], 3)
            assert r_cur >= prev_rank, f"Attention list not sorted by severity: {d['attention']}"
            prev_rank = r_cur

        # pulse keys
        pulse = d["pulse"]
        for key in ["open_requests", "active_jobs", "kyc_pending", "disputes_open", "retry_failed"]:
            assert key in pulse
            assert isinstance(pulse[key], int)

        # autonomy_report
        ar = d["autonomy_report"]
        for key in ["auto_resolved_7d", "escalated_7d", "hours_saved_7d", "top_playbooks"]:
            assert key in ar
        assert isinstance(ar["top_playbooks"], list)


# ─────────────────── 5. Auth guards ───────────────────
class TestAuthGuards:
    def test_kg_stats_anon_denied(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/kg/stats")
        assert r.status_code in (401, 403), f"Expected 401/403 got {r.status_code}"

    def test_kg_backfill_anon_denied(self, anon_session):
        r = anon_session.post(f"{BASE_URL}/api/admin/kg/backfill")
        assert r.status_code in (401, 403)

    def test_kg_entity_anon_denied(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/kg/entity/user/xxx")
        assert r.status_code in (401, 403)

    def test_control_tower_anon_denied(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/control-tower")
        assert r.status_code in (401, 403)

    def test_kg_stats_client_denied(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/kg/stats")
        assert r.status_code in (401, 403), f"Client should be denied, got {r.status_code}"

    def test_control_tower_client_denied(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/admin/control-tower")
        assert r.status_code in (401, 403), f"Client should be denied, got {r.status_code}"
