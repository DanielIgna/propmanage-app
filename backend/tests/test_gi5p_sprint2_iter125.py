"""GI-5P Sprint 2 backend tests (iter125): DNA v2 provenance, Health Decay, Risk Engine."""
import os
from datetime import datetime, timedelta, timezone

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST = {"email": "specialist@propmanage.io", "password": "Spec123!"}
CLIENT_PROP_ID = "6a11d70e600be19667009c93"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "propmanage_db")
CUR_YEAR = datetime.now(timezone.utc).year


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, r.text[:200]
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_user():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def specialist():
    return _login(SPECIALIST)


@pytest.fixture(scope="module")
def mongo_db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module")
def decay_prop(client_user, mongo_db):
    """Proprietate dedicată pentru testul de decay — nu atinge datele demo."""
    r = client_user.post(f"{BASE}/api/properties",
                         json={"name": "Test Decay GI5P2", "address": "Str. Test 1", "rooms": 3,
                               "type": "apartament", "surface": 75},
                         timeout=30)
    assert r.status_code == 200, r.text[:300]
    pid = r.json().get("id") or r.json().get("property", {}).get("id")
    assert pid
    old = (datetime.now(timezone.utc) - timedelta(days=240)).isoformat()
    mongo_db.properties.update_one({"_id": ObjectId(pid)}, {"$set": {
        "structure_health": 90, "utilities_health": 82, "documents_health": 60,
        "health_score": 77, "last_enriched_at": old,
        "created_at": old}, "$unset": {"health_decay": ""}})
    yield pid
    mongo_db.properties.delete_one({"_id": ObjectId(pid)})
    mongo_db.health_history.delete_many({"property_id": pid})
    mongo_db.property_maturity_history.delete_many({"property_id": pid})
    mongo_db.revenue_opportunities.delete_many({"property_id": pid})
    mongo_db.revenue_hunter_scans.delete_one({"_id": pid})


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo_db):
    yield
    mongo_db.property_assets.delete_many({"property_id": CLIENT_PROP_ID})
    mongo_db.properties.update_one({"_id": ObjectId(CLIENT_PROP_ID)},
                                   {"$unset": {"dna_attributes": ""}})


# ── DNA v2 atribute cu provenance ───────────────────────────────────────────
def test_dna_attributes_shape(client_user):
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/dna-attributes", timeout=30)
    assert r.status_code == 200
    attrs = r.json()["attributes"]
    assert {a["key"] for a in attrs} == {"year_built", "structure_type", "insulation_type",
                                         "roof_type", "heating_type"}


def test_dna_attributes_validation(client_user):
    bad = [
        {"attributes": {"piscina": "da"}},
        {"attributes": {"year_built": 1500}},
        {"attributes": {"structure_type": "carton"}},
        {"attributes": {"year_built": 1995}, "source": "professional_audit"},
        {"attributes": {}},
    ]
    for body in bad:
        r = client_user.patch(f"{BASE}/api/properties/{CLIENT_PROP_ID}/dna-attributes",
                              json=body, timeout=30)
        assert r.status_code == 400, body


def test_dna_attributes_set_with_provenance(client_user):
    r = client_user.patch(f"{BASE}/api/properties/{CLIENT_PROP_ID}/dna-attributes",
                          json={"attributes": {"year_built": 1995, "structure_type": "caramida"},
                                "source": "owner_declared"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/dna-attributes", timeout=30)
    a = {x["key"]: x for x in r.json()["attributes"]}
    assert a["year_built"]["value"] == 1995
    assert a["year_built"]["source"] == "owner_declared"
    assert a["year_built"]["confidence_label"] == "Declarat de proprietar"
    assert a["year_built"]["last_updated"]
    assert a["structure_type"]["value"] == "caramida"


# ── Risk Engine ─────────────────────────────────────────────────────────────
def test_risks_technical_from_overdue_asset(client_user):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "acoperis", "installed_year": CUR_YEAR - 55,
                               "source": "official_document"}, timeout=30)
    assert r.status_code == 200
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/risks", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["disclaimer"]
    tech = next((x for x in d["risks"] if x["id"] == "tech_acoperis"), None)
    assert tech, [x["id"] for x in d["risks"]]
    assert tech["score"] >= 80 and tech["category"] == "technical"
    assert tech["estimated"] is True and tech["evidence"]
    assert tech["mitigation"]["label"]
    # sortare descrescătoare după scor
    scores = [x["score"] for x in d["risks"]]
    assert scores == sorted(scores, reverse=True)


def test_risk_profile_persisted(client_user, mongo_db):
    client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/risks", timeout=30)
    prop = mongo_db.properties.find_one({"_id": ObjectId(CLIENT_PROP_ID)})
    rp = prop.get("risk_profile")
    assert rp and rp["total"] >= 1 and rp["max_score"] >= 80


# ── Health Decay ────────────────────────────────────────────────────────────
def test_health_decay_applied_via_daily_scan(admin, decay_prop, mongo_db):
    mongo_db.revenue_hunter_scans.delete_one({"_id": decay_prop})
    r = admin.post(f"{BASE}/api/admin/revenue-hunter/run", timeout=120)
    assert r.status_code == 200
    prop = mongo_db.properties.find_one({"_id": ObjectId(decay_prop)})
    assert prop["structure_health"] == 89, prop.get("structure_health")
    assert prop["utilities_health"] == 81
    assert prop["documents_health"] == 59
    assert prop["health_decay"]["points_lost"] == 3
    hist = mongo_db.health_history.find_one({"property_id": decay_prop, "reason": "decay"})
    assert hist and hist["health_score"] == prop["health_score"]


def test_health_decay_idempotent_monthly(admin, decay_prop, mongo_db):
    mongo_db.revenue_hunter_scans.delete_one({"_id": decay_prop})
    r = admin.post(f"{BASE}/api/admin/revenue-hunter/run", timeout=120)
    assert r.status_code == 200
    prop = mongo_db.properties.find_one({"_id": ObjectId(decay_prop)})
    assert prop["structure_health"] == 89  # nu scade a doua oară în aceeași lună
    assert prop["health_decay"]["points_lost"] == 3


def test_decay_generates_maintenance_risk(client_user, decay_prop):
    r = client_user.get(f"{BASE}/api/properties/{decay_prop}/risks", timeout=30)
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["risks"]]
    assert "maint_decay" in ids and "maint_audit" in ids


# ── CEO KPI ─────────────────────────────────────────────────────────────────
def test_ceo_dashboard_risk_kpi(admin):
    r = admin.get(f"{BASE}/api/admin/ceo", timeout=60)
    assert r.status_code == 200
    pr = r.json().get("property_risks")
    assert pr and "active_risks" in pr and pr["active_risks"] >= 1


# ── RBAC + regresie ─────────────────────────────────────────────────────────
def test_rbac_sprint2_endpoints(specialist):
    for ep in ("dna-attributes", "risks"):
        r = specialist.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/{ep}", timeout=30)
        assert r.status_code == 403, f"{ep}: {r.status_code}"


def test_regression_sprint1(client_user):
    for ep in ("maturity", "assets", "predictive", "dna"):
        r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/{ep}", timeout=60)
        assert r.status_code == 200, f"{ep}: {r.status_code}"
