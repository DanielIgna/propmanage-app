"""GI-4a / Board 011 — Learning Engine backend tests (Sprint iter123).

Testează: /api/admin/learning/{stats,ledger,run}, E2E oportunitate→venit,
dismiss, playbook target, command_center reco toggle, securitate, regresii.
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}

CLIENT_USER_ID = "6a11d70d600be19667009c8e"
CLIENT_PROP_ID = "6a11d70e600be19667009c93"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "propmanage_db")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_user():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def anon():
    return requests.Session()


@pytest.fixture(scope="module")
def mongo_db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


@pytest.fixture(scope="module")
def created_opps(mongo_db):
    """Track opps we insert so we can clean at end."""
    ids = []
    yield ids
    if ids:
        mongo_db.revenue_opportunities.delete_many({"id": {"$in": ids}})
        # cleanup ledger entries linked to these opps
        mongo_db.ai_decision_ledger.delete_many({"opp_id": {"$in": ids}})
        # cleanup any requests we created via accept
        for oid in ids:
            mongo_db.requests.delete_many({"description": {"$regex": "\\[TEST-iter123\\]"}})


def _make_opp(mongo_db, service="digital_twin", label="Digital Twin", value=800.0, title_suffix=""):
    opp_id = uuid.uuid4().hex
    doc = {
        "id": opp_id,
        "property_id": CLIENT_PROP_ID,
        "owner_id": CLIENT_USER_ID,
        "service": service,
        "service_label": label,
        "title": f"[TEST-iter123] Oportunitate {label} {title_suffix}",
        "benefit": "Test benefit iter123",
        "estimated_value_ron": value,
        "status": "active",
        "score": 90,
        "created_at": _now(),
    }
    mongo_db.revenue_opportunities.insert_one(doc)
    return opp_id


# ---------- Security ----------
@pytest.mark.parametrize("path,method", [
    ("/api/admin/learning/stats", "GET"),
    ("/api/admin/learning/ledger", "GET"),
    ("/api/admin/learning/run", "POST"),
])
def test_security_401_anon(anon, path, method):
    r = anon.request(method, f"{BASE}{path}", timeout=15)
    assert r.status_code in (401, 403), f"{path} => {r.status_code}"


@pytest.mark.parametrize("path,method", [
    ("/api/admin/learning/stats", "GET"),
    ("/api/admin/learning/ledger", "GET"),
    ("/api/admin/learning/run", "POST"),
])
def test_security_403_client(client_user, path, method):
    r = client_user.request(method, f"{BASE}{path}", timeout=15)
    assert r.status_code == 403, f"{path} => {r.status_code}"


# ---------- Stats endpoint shape ----------
def test_stats_shape(admin):
    r = admin.get(f"{BASE}/api/admin/learning/stats", timeout=30)
    assert r.status_code == 200, r.text[:200]
    d = r.json()
    for k in ("total_decisions", "decided", "outcomes_by_kind", "outcome_rate_pct",
              "revenue_attributed_ron", "revenue_attributed_30d_ron", "by_type",
              "attribution_model"):
        assert k in d, f"missing {k}"
    assert d["attribution_model"] == "last_touch"
    assert isinstance(d["by_type"], list)
    assert isinstance(d["outcomes_by_kind"], dict)


# ---------- Ledger endpoint ----------
def test_ledger_default(admin):
    r = admin.get(f"{BASE}/api/admin/learning/ledger", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "items" in d and "count" in d
    assert isinstance(d["items"], list)


def test_ledger_filter_opportunity(admin):
    r = admin.get(f"{BASE}/api/admin/learning/ledger?type=opportunity", timeout=30)
    assert r.status_code == 200
    d = r.json()
    for item in d["items"]:
        assert item.get("type") == "opportunity"


# ---------- Run endpoint shape ----------
def test_run_scan_shape(admin):
    r = admin.post(f"{BASE}/api/admin/learning/run", timeout=60)
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    for k in ("processed", "finalized", "outcomes"):
        assert k in d
    assert isinstance(d["outcomes"], dict)


# ---------- E2E accept → request → revenue ----------
def test_e2e_accept_opportunity_creates_ledger_with_target(
    admin, client_user, mongo_db, created_opps
):
    opp_id = _make_opp(mongo_db, title_suffix="accept-e2e")
    created_opps.append(opp_id)

    # Client accepts
    r = client_user.post(f"{BASE}/api/client/opportunities/{opp_id}/accept", timeout=30)
    assert r.status_code == 200, r.text[:300]
    body = r.json()
    assert body.get("ok") is True
    assert "request_id" in body
    request_id = body["request_id"]

    # Verify ledger entry exists with target + request_id
    entry = mongo_db.ai_decision_ledger.find_one({"opp_id": opp_id})
    assert entry is not None, "no ledger entry for opp"
    assert entry.get("type") == "opportunity"
    assert entry.get("action") == "accepted"
    assert entry.get("request_id") == request_id
    tgt = entry.get("target") or {}
    assert tgt.get("user_id") == CLIENT_USER_ID
    assert tgt.get("property_id") == CLIENT_PROP_ID
    assert tgt.get("service") == "digital_twin"

    # Run scan → outcome should be request (not final, since request not confirmed)
    r2 = admin.post(f"{BASE}/api/admin/learning/run", timeout=60)
    assert r2.status_code == 200
    entry2 = mongo_db.ai_decision_ledger.find_one({"opp_id": opp_id})
    outcome = entry2.get("outcome") or {}
    assert outcome.get("kind") == "request", f"expected request, got {outcome}"
    assert outcome.get("final") is False

    # Confirm request in Mongo → escrow_amount 800
    mongo_db.requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "confirmed", "escrow_amount": 800.0}}
    )

    # Re-run → outcome revenue final
    r3 = admin.post(f"{BASE}/api/admin/learning/run", timeout=60)
    assert r3.status_code == 200
    entry3 = mongo_db.ai_decision_ledger.find_one({"opp_id": opp_id})
    outcome3 = entry3.get("outcome") or {}
    assert outcome3.get("kind") == "revenue", f"expected revenue, got {outcome3}"
    assert outcome3.get("final") is True
    assert outcome3.get("revenue_ron", 0) >= 800

    # Stats should reflect revenue
    stats = admin.get(f"{BASE}/api/admin/learning/stats", timeout=30).json()
    assert stats["revenue_attributed_ron"] >= 800
    # 30d attributed should be >0 as well
    assert stats["revenue_attributed_30d_ron"] > 0


# ---------- Dismiss flow ----------
def test_e2e_dismiss_opportunity_no_effect(admin, client_user, mongo_db, created_opps):
    opp_id = _make_opp(mongo_db, service="audit_tehnic", label="Audit Tehnic",
                       value=500.0, title_suffix="dismiss-e2e")
    created_opps.append(opp_id)

    r = client_user.post(f"{BASE}/api/client/opportunities/{opp_id}/dismiss", timeout=30)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    entry = mongo_db.ai_decision_ledger.find_one({"opp_id": opp_id})
    assert entry is not None
    assert entry.get("action") == "dismissed"

    # Run → outcome no_effect final
    r2 = admin.post(f"{BASE}/api/admin/learning/run", timeout=60)
    assert r2.status_code == 200
    entry2 = mongo_db.ai_decision_ledger.find_one({"opp_id": opp_id})
    outcome = entry2.get("outcome") or {}
    assert outcome.get("kind") == "no_effect"
    assert outcome.get("final") is True


# ---------- Playbook target tracking ----------
def test_playbook_ledger_has_target(admin, mongo_db):
    # Ensure marketing intel latest exists
    admin.post(f"{BASE}/api/admin/marketing-intel/run", timeout=90)
    r = admin.get(f"{BASE}/api/admin/marketing-intel/opportunity-queue", timeout=30)
    items = r.json().get("items") or []
    if not items:
        pytest.skip("no queue items for playbook test")
    item = items[0]
    # Bypass 10-min debounce: remove recent playbook for this ref_id
    mongo_db.contact_playbooks.delete_many({"ref_id": item["ref_id"]})
    # Snapshot existing playbook ledger ids (type is "contact_playbook")
    before_ids = {e["ledger_id"] for e in mongo_db.ai_decision_ledger.find(
        {"type": "contact_playbook"}, {"ledger_id": 1})}

    r2 = admin.post(f"{BASE}/api/admin/marketing-intel/playbook",
                    json={"target_type": item["type"], "ref_id": item["ref_id"]},
                    timeout=90)
    assert r2.status_code == 200

    after = list(mongo_db.ai_decision_ledger.find(
        {"type": "contact_playbook", "ledger_id": {"$nin": list(before_ids)}}))
    assert len(after) >= 1, "no new playbook ledger entry"
    new_entry = after[0]
    target = new_entry.get("target") or {}
    # Board 011: new playbook entries MUST have target with visitor_id/user_id or service
    assert any(target.get(k) for k in ("user_id", "visitor_id", "service")), \
        f"playbook ledger missing target: {target}"
    assert new_entry.get("source_agent"), "missing source_agent"


# ---------- Command Center reco toggle → ledger ----------
def test_command_center_toggle_creates_ledger(admin, mongo_db):
    # Ensure recos exist
    latest = admin.get(f"{BASE}/api/admin/command-center/recommendations/latest", timeout=30).json()
    if not latest.get("recommendations"):
        gen = admin.post(f"{BASE}/api/admin/command-center/recommendations", timeout=120)
        assert gen.status_code == 200
        latest = gen.json()
    recos = latest.get("recommendations") or []
    if not recos:
        pytest.skip("no recos available")

    # Ensure idx=0 is currently 'not done' so toggling makes it done
    if recos[0].get("done"):
        admin.post(f"{BASE}/api/admin/command-center/recommendations/toggle",
                   json={"idx": 0}, timeout=15)

    before = {e["ledger_id"] for e in mongo_db.ai_decision_ledger.find(
        {"type": "command_center_reco"}, {"ledger_id": 1})}
    r = admin.post(f"{BASE}/api/admin/command-center/recommendations/toggle",
                   json={"idx": 0}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    if not body.get("done"):
        # toggle again to make done=True
        r = admin.post(f"{BASE}/api/admin/command-center/recommendations/toggle",
                       json={"idx": 0}, timeout=15)
        body = r.json()
    assert body.get("done") is True

    after = list(mongo_db.ai_decision_ledger.find(
        {"type": "command_center_reco", "ledger_id": {"$nin": list(before)}}))
    assert len(after) >= 1
    assert after[0].get("action") == "done"


# ---------- Command Center feed has AI KPIs ----------
def test_command_center_feed_includes_ai_kpis(admin):
    r = admin.get(f"{BASE}/api/admin/command-center/feed", timeout=60)
    assert r.status_code == 200
    d = r.json()
    raw = d.get("raw") or {}
    assert "ai_revenue_attributed_30d" in raw
    assert "ai_decisions_total" in raw
    assert isinstance(raw["ai_decisions_total"], int)
    assert raw["ai_decisions_total"] >= 0


# ---------- Regression ----------
@pytest.mark.parametrize("path", [
    "/api/admin/marketing-intel/latest",
    "/api/admin/lead-intel/stats",
    "/api/admin/growth-intel/latest",
    "/api/admin/ceo",
])
def test_regression(admin, path):
    r = admin.get(f"{BASE}{path}", timeout=60)
    assert r.status_code == 200, f"{path} => {r.status_code}: {r.text[:200]}"
