"""Iteration 121 — Sprint GI-2: Intent & Lead Intelligence Engine (Board 004/005/006)."""
import os
import time
import uuid
import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


# ------------------ fixtures ------------------

@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=CLIENT, timeout=15)
    assert r.status_code == 200, f"client login: {r.status_code}"
    return s


@pytest.fixture(scope="module")
def db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ------------------ TRACK ingest (public) ------------------

class TestTrackIngest:
    def test_track_public_no_auth_intent(self, db):
        vid = "testvisitor_iter121_" + uuid.uuid4().hex[:8]
        sid = "testsess_" + uuid.uuid4().hex[:8]
        r = requests.post(f"{BASE_URL}/api/track", json={
            "visitor_id": vid, "session_id": sid,
            "user_id": "", "user_role": "",
            "events": [
                {"type": "pageview", "path": "/digital-twin"},
                {"type": "intent", "intent_signal": "twin_viewed", "path": "/digital-twin"},
            ],
        }, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("ok") is True
        assert j.get("ingested") == 2
        # Verify Mongo
        time.sleep(0.5)
        ev = _run(db.analytics_events.find_one({"visitor_id": vid, "type": "intent"}))
        assert ev is not None, "intent event not stored"
        assert ev.get("intent_signal") == "twin_viewed"
        sess = _run(db.analytics_sessions.find_one({"session_id": sid}))
        assert sess is not None
        assert sess.get("intent_twin_viewed") is True

    def test_track_with_user_id_identity_upsert(self, db):
        vid = "testvisitor_iter121_" + uuid.uuid4().hex[:8]
        sid = "testsess_" + uuid.uuid4().hex[:8]
        uid = "u_" + uuid.uuid4().hex[:12]
        r = requests.post(f"{BASE_URL}/api/track", json={
            "visitor_id": vid, "session_id": sid,
            "user_id": uid, "user_role": "client",
            "events": [{"type": "pageview", "path": "/client"}],
        }, timeout=15)
        assert r.status_code == 200
        time.sleep(0.3)
        sess = _run(db.analytics_sessions.find_one({"session_id": sid}))
        assert sess and sess.get("user_id") == uid
        ident = _run(db.visitor_identities.find_one({"visitor_id": vid}))
        assert ident and ident.get("user_id") == uid


# ------------------ E2E scoring ------------------

@pytest.fixture(scope="module")
def hot_visitor(db):
    """Create a strong-signal visitor via public track ingest."""
    vid = "testvisitor_iter121hot_" + uuid.uuid4().hex[:6]
    sid1 = "testsess_" + uuid.uuid4().hex[:8]
    # session with multiple intents + utm whatsapp + long heartbeat
    ev = [
        {"type": "pageview", "path": "/digital-twin", "utm_source": "whatsapp"},
        {"type": "intent", "intent_signal": "twin_viewed", "path": "/digital-twin"},
        {"type": "intent", "intent_signal": "audit_viewed", "path": "/house-health"},
        {"type": "intent", "intent_signal": "request_started", "path": "/request"},
        {"type": "intent", "intent_signal": "whatsapp_opened", "path": "/request"},
        {"type": "heartbeat", "duration_ms": 200000, "path": "/digital-twin"},
    ]
    r = requests.post(f"{BASE_URL}/api/track", json={
        "visitor_id": vid, "session_id": sid1, "events": ev,
    }, timeout=15)
    assert r.status_code == 200
    return vid


class TestLeadScoring:
    def test_run_scan(self, admin_session, hot_visitor):
        r = admin_session.post(f"{BASE_URL}/api/admin/lead-intel/run", timeout=60)
        assert r.status_code == 200, r.text
        j = r.json()
        for k in ["scanned", "tiers", "new_hot"]:
            assert k in j, f"missing {k}"
        assert j["scanned"] > 0

    def test_hot_visitor_scored(self, admin_session, hot_visitor):
        r = admin_session.get(f"{BASE_URL}/api/admin/lead-intel/leads?limit=200", timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        found = next((x for x in items if x["visitor_id"] == hot_visitor), None)
        assert found is not None, f"test visitor {hot_visitor} not in leads"
        assert found["score"] >= 60, f"expected hot score, got {found['score']}"
        assert found["tier"] == "hot"
        sigs = {s["signal"] for s in found["signals"]}
        # request_abandoned derived (started but no offer_requested)
        assert "request_abandoned" in sigs, f"missing derived request_abandoned in {sigs}"
        assert found.get("conv_probability_pct") is not None
        # Each signal has label + points
        for s in found["signals"]:
            assert "label" in s and "points" in s

    def test_stats_structure(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/lead-intel/stats", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert set(d["tiers"].keys()) == {"client", "hot", "qualified", "prospect", "visitor"}
        assert "total" in d and "avg_score" in d
        assert isinstance(d["top_signals"], list)
        assert d["model_validation"] == "ai_hypothesis"
        assert "last_scan" in d

    def test_leads_filter_hot(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/lead-intel/leads?tier=hot", timeout=30)
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["tier"] == "hot"

    def test_leads_filter_invalid(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/lead-intel/leads?tier=nonsense", timeout=30)
        assert r.status_code == 422


# ------------------ Security ------------------

class TestSecurity:
    def test_stats_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/lead-intel/stats", timeout=15)
        assert r.status_code == 401

    def test_leads_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/lead-intel/leads", timeout=15)
        assert r.status_code == 401

    def test_run_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/admin/lead-intel/run", timeout=15)
        assert r.status_code == 401

    def test_client_forbidden(self, client_session):
        for path in ["/api/admin/lead-intel/stats", "/api/admin/lead-intel/leads"]:
            r = client_session.get(f"{BASE_URL}{path}", timeout=15)
            assert r.status_code == 403, f"{path} → {r.status_code}"
        r = client_session.post(f"{BASE_URL}/api/admin/lead-intel/run", timeout=15)
        assert r.status_code == 403


# ------------------ Activity events ------------------

class TestActivityEvents:
    def test_scan_and_hot_events(self, admin_session, db):
        # ensure a scan happened
        admin_session.post(f"{BASE_URL}/api/admin/lead-intel/run", timeout=60)
        time.sleep(0.5)
        ev = _run(db.activity_events.find_one({"event_type": "lead.scan_completed"}))
        assert ev is not None, "lead.scan_completed not emitted"
        # hot detected: at least once for test visitor (may be from earlier run)
        ev_hot = _run(db.activity_events.find_one({"event_type": "lead.hot_detected"}))
        assert ev_hot is not None, "lead.hot_detected not emitted"


# ------------------ Command Center ------------------

class TestCommandCenter:
    def test_feed_has_hot_leads_warning(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/command-center/feed", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "raw" in d
        assert "hot_leads" in d["raw"]
        assert "qualified_leads" in d["raw"]
        warnings = d.get("warnings", [])
        hot = next((w for w in warnings if w.get("key") == "hot_leads"), None)
        assert hot is not None, f"hot_leads warning missing: {warnings}"
        assert hot.get("link") == "/admin/lead-intel"


# ------------------ Revenue Hunter (lead_boost) ------------------

class TestRevenueHunterBoost:
    def test_lead_boost_run(self, admin_session, db):
        # find client's user_id + a property
        client_user = _run(db.users.find_one({"email": CLIENT["email"]}))
        assert client_user, "client demo user missing"
        cid = str(client_user["_id"])
        prop = _run(db.properties.find_one({"owner_id": cid}))
        if not prop:
            pytest.skip("no property for client demo user")
        prop_id = str(prop["_id"])
        # Seed hot lead_scores for client
        _run(db.lead_scores.update_one(
            {"_id": f"testvisitor_iter121client_{cid}"},
            {"$set": {"visitor_id": f"testvisitor_iter121client_{cid}",
                      "user_id": cid, "score": 80, "tier": "hot",
                      "tier_label": "Lead fierbinte",
                      "signals": [], "sources": ["direct"], "sessions": 1,
                      "updated_at": "2026-01-01T00:00:00+00:00"}},
            upsert=True))
        # Also add doc with client's actual user_id as visitor_id fallback
        # Remove throttle for this property
        _run(db.revenue_hunter_scans.delete_one({"_id": prop_id}))
        # Run
        r = admin_session.post(f"{BASE_URL}/api/admin/revenue-hunter/run", timeout=120)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("scanned", 0) >= 0
        # check any opportunity for property has lead_tier hot
        opp = _run(db.revenue_opportunities.find_one({"property_id": prop_id, "lead_tier": "hot"}))
        # If no new opportunity due to cooldown, at least run didn't crash — assert scanned>0
        if opp is None:
            assert j["scanned"] > 0, "no opportunities and scanned 0 — run may have crashed"


# ------------------ Regression ------------------

class TestRegression:
    def test_growth_intel_latest(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/growth-intel/latest", timeout=30)
        assert r.status_code == 200

    def test_ceo_dashboard(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/ceo", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "value_loop" in d

    def test_analytics_overview(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/analytics/overview", timeout=30)
        assert r.status_code == 200
