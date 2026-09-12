"""GI-5P Sprint 1 — Property Intelligence backend tests (iter124).

Testează: Maturity L0-L5 + Audit First, Registru Active (Trust Model 015),
Predictive actuarial (No Fake Precision), detector Revenue Hunter (Directiva 014),
CEO Dashboard KPI, RBAC, regresii Property DNA.
"""
import os
import re
from datetime import datetime, timezone

import pytest
import requests
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
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text[:200]}"
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


@pytest.fixture(scope="module", autouse=True)
def cleanup(mongo_db):
    yield
    mongo_db.property_assets.delete_many({"property_id": CLIENT_PROP_ID})
    mongo_db.revenue_opportunities.delete_many(
        {"property_id": CLIENT_PROP_ID, "service": {"$regex": "^predictive_"}})


# ── Maturity ────────────────────────────────────────────────────────────────
def test_maturity_shape_and_audit_first(client_user):
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/maturity", timeout=30)
    assert r.status_code == 200, r.text[:300]
    m = r.json()
    assert 0 <= m["level"] <= 5
    assert m["level_label"] in m["levels"]
    assert len(m["criteria"]) == 5
    for c in m["criteria"]:
        assert set(c) >= {"level", "label", "ok", "hint"}
    # Directiva 014 — Audit First: sub L2 CTA principal = audit
    if m["level"] < 2:
        assert m["audit_first"] is True
        assert m["next_step"]["cta"] == "audit"
    if m["level"] < 5:
        assert m["next_step"] is not None


def test_maturity_persisted_with_history(client_user, mongo_db):
    client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/maturity", timeout=30)
    prop = mongo_db.properties.find_one({"_id": __import__("bson").ObjectId(CLIENT_PROP_ID)})
    assert "maturity" in prop and "level" in prop["maturity"]
    hist = mongo_db.property_maturity_history.count_documents({"property_id": CLIENT_PROP_ID})
    assert hist >= 1


# ── Asset Registry (Trust Model 015) ────────────────────────────────────────
def test_assets_slots_empty(client_user):
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["library_version"]
    assert len(d["slots"]) == 4
    types = {s["asset_type"] for s in d["slots"]}
    assert types == {"centrala_termica", "tablou_electric", "acoperis", "termopane"}


def test_register_asset_invalid_type(client_user):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "piscina", "installed_year": 2020}, timeout=30)
    assert r.status_code == 400


def test_register_asset_invalid_year(client_user):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "centrala_termica", "installed_year": 1850}, timeout=30)
    assert r.status_code == 400
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "centrala_termica", "installed_year": CUR_YEAR + 1}, timeout=30)
    assert r.status_code == 400


def test_register_asset_client_cannot_claim_audit_confidence(client_user):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "centrala_termica", "installed_year": 2015,
                               "source": "professional_audit"}, timeout=30)
    assert r.status_code == 400


def test_register_asset_ok_with_trust_fields(client_user):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "centrala_termica", "installed_year": CUR_YEAR - 14,
                               "source": "owner_declared"}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    slot = next(s for s in r.json()["slots"] if s["asset_type"] == "centrala_termica")
    a = slot["asset"]
    # Trust Model — Directiva 015
    assert a["source"] == "owner_declared"
    assert a["confidence"] == "owner_declared"
    assert a["verification_status"] == "unverified"
    assert a["last_updated"] and a["updated_by"] == CLIENT["email"]
    eol = slot["eol"]
    assert eol["estimated"] is True
    assert eol["needs_audit"] is True
    assert eol["status"] in ("overdue", "attention", "monitor", "ok")
    # No Fake Precision — interval, nu număr exact
    assert eol["remaining_label"].startswith("≈") or eol["remaining_label"] == "Peste durata de referință"
    assert re.match(r"^≈ [\d.]+–[\d.]+ RON$", eol["cost_label"])
    # Customer Trust — confidence slab → recomandă audit, nu înlocuire
    assert "Audit" in eol["recommended_action"]


def test_asset_hypothesis_without_year(client_user):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "termopane", "source": "owner_declared"}, timeout=30)
    assert r.status_code == 200
    slot = next(s for s in r.json()["slots"] if s["asset_type"] == "termopane")
    assert slot["eol"]["status"] == "hypothesis"
    assert "audit" in slot["eol"]["remaining_label"].lower()


def test_patch_asset_updates_trust_fields(client_user):
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets", timeout=30)
    slot = next(s for s in r.json()["slots"] if s["asset_type"] == "centrala_termica")
    aid = slot["asset"]["id"]
    before = slot["asset"]["last_updated"]
    r = client_user.patch(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets/{aid}",
                          json={"installed_year": CUR_YEAR - 5, "source": "official_document"}, timeout=30)
    assert r.status_code == 200
    slot = next(s for s in r.json()["slots"] if s["asset_type"] == "centrala_termica")
    assert slot["asset"]["installed_year"] == CUR_YEAR - 5
    assert slot["asset"]["confidence"] == "official_document"
    assert slot["asset"]["last_updated"] >= before


def test_replace_asset_keeps_history(client_user, mongo_db):
    r = client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                         json={"asset_type": "centrala_termica", "installed_year": CUR_YEAR,
                               "source": "official_document"}, timeout=30)
    assert r.status_code == 200
    replaced = mongo_db.property_assets.count_documents(
        {"property_id": CLIENT_PROP_ID, "asset_type": "centrala_termica", "status": "replaced"})
    active = mongo_db.property_assets.count_documents(
        {"property_id": CLIENT_PROP_ID, "asset_type": "centrala_termica", "status": "active"})
    assert replaced >= 1 and active == 1


# ── Predictive ──────────────────────────────────────────────────────────────
def test_predictive_endpoint(client_user):
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/predictive", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["disclaimer"]
    assert len(d["predictions"]) >= 1
    for p in d["predictions"]:
        assert p["estimated"] is True
        assert p["confidence_label"]
        assert p["recommended_action"]
        assert p["library_version"] == d["library_version"]


# ── Revenue Hunter integration (Directiva 014) ──────────────────────────────
def test_revenue_hunter_predictive_detector(admin, client_user, mongo_db):
    # activ vechi cu încredere solidă → oportunitate predictive planificată
    client_user.post(f"{BASE}/api/properties/{CLIENT_PROP_ID}/assets",
                     json={"asset_type": "acoperis", "installed_year": CUR_YEAR - 55,
                           "source": "official_document"}, timeout=30)
    # reset throttle + cooldown + loc liber pentru oportunități noi
    mongo_db.revenue_hunter_scans.delete_one({"_id": CLIENT_PROP_ID})
    mongo_db.revenue_opportunities.delete_many({"property_id": CLIENT_PROP_ID})
    r = admin.post(f"{BASE}/api/admin/revenue-hunter/run", timeout=120)
    assert r.status_code == 200, r.text[:300]
    opp = mongo_db.revenue_opportunities.find_one(
        {"property_id": CLIENT_PROP_ID, "service": "predictive_acoperis"})
    assert opp, "predictive opportunity not created"
    # Directiva 014: categorie + prioritate comercială + domenii
    assert opp["category"] == "technical"
    assert opp["commercial_priority"] == 5
    assert opp["commercial_domains"] == ["technical"]
    assert "≈" in opp["benefit"]  # No Fake Precision în copy


def test_all_new_opportunities_have_commercial_fields(mongo_db):
    for opp in mongo_db.revenue_opportunities.find({"property_id": CLIENT_PROP_ID}):
        assert opp.get("category"), opp.get("service")
        assert 1 <= opp.get("commercial_priority", 0) <= 5
        assert isinstance(opp.get("commercial_domains"), list)


# ── CEO Dashboard KPI ───────────────────────────────────────────────────────
def test_ceo_dashboard_maturity_kpi(admin):
    r = admin.get(f"{BASE}/api/admin/ceo", timeout=60)
    assert r.status_code == 200
    mat = r.json().get("maturity")
    assert mat and set(mat) >= {"avg_level", "distribution", "scanned", "total"}
    assert mat["scanned"] >= 1


# ── RBAC ────────────────────────────────────────────────────────────────────
def test_rbac_specialist_forbidden(specialist):
    for ep in ("maturity", "assets", "predictive"):
        r = specialist.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/{ep}", timeout=30)
        assert r.status_code == 403, f"{ep}: {r.status_code}"


def test_rbac_anon_unauthorized():
    r = requests.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/maturity", timeout=30)
    assert r.status_code in (401, 403)


# ── Regression ──────────────────────────────────────────────────────────────
def test_regression_property_dna(client_user):
    r = client_user.get(f"{BASE}/api/properties/{CLIENT_PROP_ID}/dna", timeout=60)
    assert r.status_code == 200
    d = r.json()
    assert "pvi" in d and "capabilities" in d


def test_regression_client_opportunities(client_user):
    r = client_user.get(f"{BASE}/api/client/opportunities", timeout=30)
    assert r.status_code == 200
