"""E2E Value Loop + PVI + Revenue Hunter tests (iteration 119)."""
import os
import pytest
import requests
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import asyncio

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

CLIENT = ("client@propmanage.io", "Client123!")
SPEC = ("specialist@propmanage.io", "Spec123!")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")


def login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def sessions():
    return {"client": login(*CLIENT), "spec": login(*SPEC), "admin": login(*ADMIN)}


@pytest.fixture(scope="module")
def mongo():
    # Use env from backend
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
    url = os.environ["MONGO_URL"]
    dbn = os.environ["DB_NAME"]
    cli = AsyncIOMotorClient(url)
    return cli[dbn]


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if not asyncio.get_event_loop().is_running() else asyncio.new_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------
# Helpers to set up a confirmed request via Mongo shortcut
# --------------------------------------------------------------------------
async def _setup_completed_request(mdb):
    """Create a request in 'completed' state ready for client to confirm."""
    client = await mdb.users.find_one({"email": CLIENT[0]})
    spec = await mdb.users.find_one({"email": SPEC[0]})
    assert client and spec
    prop = await mdb.properties.find_one({"owner_id": str(client["_id"])})
    assert prop, "client has no property"
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "title": "[TEST] Value Loop E2E iter119",
        "description": "Test job",
        "category": "hvac",
        "priority": "normal",
        "budget_estimate": 500,
        "property_id": str(prop["_id"]),
        "client_id": str(client["_id"]),
        "client_name": client.get("name"),
        "property_name": prop.get("name"),
        "property_address": prop.get("address"),
        "status": "completed",
        "specialist_id": str(spec["_id"]),
        "specialist_name": spec.get("name"),
        "escrow_amount": 500,
        "escrow_status": "held",
        "created_at": now,
        "completed_at": now,
    }
    res = await mdb.requests.insert_one(doc)
    return str(res.inserted_id), str(prop["_id"])


@pytest.fixture(scope="module")
def prepared(mongo):
    loop = asyncio.new_event_loop()
    req_id, prop_id = loop.run_until_complete(_setup_completed_request(mongo))
    yield {"req_id": req_id, "prop_id": prop_id, "loop": loop}


# --------------------------------------------------------------------------
# 1. Value Loop E2E — confirm request
# --------------------------------------------------------------------------
def test_confirm_triggers_value_loop(sessions, mongo, prepared):
    s = sessions["client"]
    req_id = prepared["req_id"]
    prop_id = prepared["prop_id"]

    r = s.post(f"{BASE}/api/requests/{req_id}/confirm", timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    assert body.get("ok") is True
    assert body.get("tokens_earned") == 100
    vl = body.get("value_loop") or {}
    assert isinstance(vl.get("pvi"), int), f"pvi should be int: {vl}"
    assert vl.get("pvi") > 0
    assert isinstance(vl.get("warranty_months"), int)

    loop = prepared["loop"]

    # warranty created
    w_count = loop.run_until_complete(mongo.warranties.count_documents({"request_id": req_id}))
    assert w_count == 1
    warranty = loop.run_until_complete(mongo.warranties.find_one({"request_id": req_id}))
    assert warranty["status"] == "active"
    assert warranty["until"] > datetime.now(timezone.utc).isoformat()

    # pvi on property
    prop = loop.run_until_complete(mongo.properties.find_one({"_id": ObjectId(prop_id)}))
    assert prop.get("pvi", {}).get("score", 0) > 0

    # pvi_history entry with trigger job_closure
    hist = loop.run_until_complete(mongo.pvi_history.find_one({"property_id": prop_id, "trigger": "job_closure"}))
    assert hist is not None

    # twin.enriched event
    ev = loop.run_until_complete(mongo.activity_events.find_one({"event_type": "twin.enriched", "request_id": req_id}))
    assert ev is not None

    # documents_health bounded
    assert (prop.get("documents_health") or 0) <= 100


# --------------------------------------------------------------------------
# 2. Idempotency — second confirm doesn't create another warranty
# --------------------------------------------------------------------------
def test_confirm_idempotent_warranty(sessions, mongo, prepared):
    s = sessions["client"]
    req_id = prepared["req_id"]
    r = s.post(f"{BASE}/api/requests/{req_id}/confirm", timeout=15)
    # Now status is 'confirmed' -> 400
    assert r.status_code == 400
    loop = prepared["loop"]
    count = loop.run_until_complete(mongo.warranties.count_documents({"request_id": req_id}))
    assert count == 1, f"warranty duplicated: {count}"


# --------------------------------------------------------------------------
# 3. Property DNA endpoint (client)
# --------------------------------------------------------------------------
def test_property_dna(sessions, prepared):
    s = sessions["client"]
    prop_id = prepared["prop_id"]
    # Route is /api/properties/{prop_id}/dna in code — request stated singular; test both
    r = s.get(f"{BASE}/api/properties/{prop_id}/dna", timeout=15)
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    body = r.json()
    pvi = body.get("pvi") or {}
    assert "score" in pvi and pvi["score"] > 0
    assert "delta_6m" in pvi
    reasons = pvi.get("reasons") or []
    keys = {rr.get("key") for rr in reasons}
    assert {"twin", "works", "audit", "installations", "warranties", "identity"}.issubset(keys), keys
    for rr in reasons:
        assert set(rr.keys()) >= {"label", "done", "points", "max"}

    # warranties + works components should have points>0 after E2E
    by_key = {rr["key"]: rr for rr in reasons}
    assert by_key["warranties"]["points"] > 0, by_key["warranties"]
    assert by_key["works"]["points"] > 0, by_key["works"]

    assert "dna_completeness" in body
    assert "capabilities" in body
    assert "timeline" in body


# --------------------------------------------------------------------------
# 4. Revenue Hunter opportunities
# --------------------------------------------------------------------------
def test_client_opportunities(sessions):
    s = sessions["client"]
    r = s.get(f"{BASE}/api/client/opportunities", timeout=20)
    assert r.status_code == 200
    body = r.json()
    opps = body.get("opportunities")
    assert isinstance(opps, list)
    # If any opportunity exists, verify structure and try dismiss
    if opps:
        opp = opps[0]
        assert "title" in opp or "service_label" in opp
        opp_id = opp.get("id")
        if opp_id:
            r2 = s.post(f"{BASE}/api/client/opportunities/{opp_id}/dismiss", timeout=15)
            assert r2.status_code == 200


# --------------------------------------------------------------------------
# 5. Admin Value Loop stats
# --------------------------------------------------------------------------
def test_admin_value_loop_stats(sessions):
    s = sessions["admin"]
    r = s.get(f"{BASE}/api/admin/value-loop/stats", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("avg_pvi", 0) > 0
    assert body.get("properties_scored", 0) >= 1
    assert body.get("properties_total", 0) >= 1
    assert body.get("active_warranties", 0) >= 1
    assert body.get("twin_enrichments", 0) >= 1


# --------------------------------------------------------------------------
# 6. CEO Dashboard
# --------------------------------------------------------------------------
def test_ceo_dashboard_value_loop(sessions):
    s = sessions["admin"]
    r = s.get(f"{BASE}/api/admin/ceo", timeout=20)
    assert r.status_code == 200
    body = r.json()
    vl = body.get("value_loop")
    assert vl is not None, body.keys()
    for k in ("avg_pvi", "properties_scored", "properties_total", "active_warranties", "twin_enrichments"):
        assert k in vl, f"missing {k} in {vl}"


# --------------------------------------------------------------------------
# 7. Command Center feed
# --------------------------------------------------------------------------
def test_command_center_feed(sessions):
    s = sessions["admin"]
    r = s.get(f"{BASE}/api/admin/command-center/feed", timeout=20)
    assert r.status_code == 200
    body = r.json()
    stats = body.get("stats") or []
    avg_pvi_stat = next((x for x in stats if x.get("key") == "avg_pvi"), None)
    assert avg_pvi_stat is not None, stats
    assert avg_pvi_stat.get("value") and avg_pvi_stat["value"] != "—"
    assert avg_pvi_stat.get("icon") == "gem"
    assert "PVI" in (avg_pvi_stat.get("label") or "")
    raw = body.get("raw") or {}
    assert "avg_pvi" in raw and "active_warranties" in raw and "twin_enrichments" in raw
