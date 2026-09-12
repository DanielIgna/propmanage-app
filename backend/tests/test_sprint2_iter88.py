"""Iter88 — Sprint 2 (Dispute AI Triage + KYC AI recommendation + Marketplace Medic)
+ CIP-B (Price Observatory) — backend regression tests.

Covers:
- Orchestrator overview shows 7 playbooks + simulate/{kind} for all 7 (auto_resolved outcome)
- Dispute AI Triage (REAL LLM Claude): client opens dispute → async Claude call
  populates ai_triage {category, severity, summary, proposed_resolution, arguments[3], suggested_split}
  visible via GET /api/admin/disputes. Cleanup: delete test dispute + revert request.
- Marketplace Medic: setting medic_suspended=true excludes specialist from marketplace list.
- KYC: verifies simulate/kyc_prevalidated writes ledger + notification.
- Price Observatory: public 132 rows, filters, admin POST validation, aggregate trust upgrade
  after 2nd observation, CSV import/export, DELETE cleanup.
"""
import os
import time
import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPECIALIST2_EMAIL = "specialist2@propmanage.io"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "propmanage_db")


# ---------- FIXTURES ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=CLIENT, timeout=30)
    assert r.status_code == 200, f"client login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def mongo():
    c = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    yield c[DB_NAME]
    c.close()


# ---------- ORCHESTRATOR: 7 PLAYBOOKS ----------
class TestOrchestrator7:
    def test_overview_has_7_playbooks(self, admin_session):
        r = admin_session.get(f"{API}/admin/orchestrator/overview", timeout=30)
        assert r.status_code == 200
        data = r.json()
        ids = {pb["id"] for pb in data["playbooks"]}
        expected = {
            "smoke_fail_to_qa", "autonomy_reflex", "webhook_retry_guardian",
            "category_visibility_gate", "dispute_ai_triage",
            "kyc_prevalidation_reporter", "marketplace_medic",
        }
        assert expected.issubset(ids), f"Missing playbooks. Got: {ids}"
        assert len(data["playbooks"]) == 7, f"Expected 7 playbooks, got {len(data['playbooks'])}"

    @pytest.mark.parametrize("kind", [
        "smoke_fail", "autonomy_score_drop", "webhook_fail",
        "category_visibility_refresh", "dispute_opened",
        "kyc_prevalidated", "marketplace_medic_scan",
    ])
    def test_simulate_kind_auto_resolved(self, admin_session, kind):
        r = admin_session.post(f"{API}/admin/orchestrator/simulate/{kind}", timeout=45)
        assert r.status_code == 200, f"{kind} → {r.status_code}: {r.text[:200]}"
        data = r.json()
        assert data.get("handled") is True
        ledger = data.get("ledger") or {}
        # webhook_fail → retry_scheduled; all others → auto_resolved
        allowed_outcomes = {"auto_resolved", "retry_scheduled"}
        assert ledger.get("outcome") in allowed_outcomes, f"{kind} ledger outcome={ledger.get('outcome')}: {data}"
        # Every simulate should write ledger — check via GET
        led = admin_session.get(f"{API}/admin/orchestrator/ledger?limit=5", timeout=15)
        assert led.status_code == 200


# ---------- DISPUTE AI TRIAGE (REAL LLM) ----------
class TestDisputeAITriage:
    def test_dispute_triage_real_claude(self, client_session, admin_session, mongo):
        # Find a request assigned/in_progress owned by client, not disputed
        me = client_session.get(f"{API}/auth/me", timeout=15).json()
        client_id = me.get("id")
        assert client_id

        candidate = mongo.requests.find_one({
            "client_id": client_id,
            "status": {"$in": ["assigned", "in_progress"]},
            "$or": [{"disputed": {"$exists": False}}, {"disputed": False}],
            "escrow_status": {"$ne": "released"},
        })
        if not candidate:
            pytest.skip("No eligible client request (assigned/in_progress without dispute) found in DB")

        req_id = str(candidate["_id"])
        original_escrow_status = candidate.get("escrow_status", "held")
        original_disputed = candidate.get("disputed", False)

        # Open dispute
        reason = (
            "Specialistul nu s-a prezentat la 3 programări succesive și nu răspunde la telefon "
            "de 5 zile. Vreau restituirea integrală a sumei din escrow."
        )
        r = client_session.post(
            f"{API}/requests/{req_id}/dispute",
            json={"reason": reason, "evidence_urls": []},
            timeout=30,
        )
        assert r.status_code == 200, f"dispute open failed: {r.status_code} {r.text[:300]}"
        dispute_id = r.json().get("id")
        assert dispute_id

        try:
            # Poll admin listing for ai_triage populated (Claude ~15-25s)
            triage = None
            for _ in range(15):  # up to ~45s
                time.sleep(3)
                lst = admin_session.get(f"{API}/admin/disputes", timeout=20)
                assert lst.status_code == 200
                found = next((d for d in lst.json() if d.get("id") == dispute_id), None)
                if found and found.get("ai_triage"):
                    triage = found["ai_triage"]
                    break

            assert triage is not None, "ai_triage not populated within 45s"
            # Shape assertions
            assert triage.get("category") in {
                "no_show", "quality", "price", "communication", "damage", "other"
            }, f"unexpected category: {triage.get('category')}"
            assert triage.get("severity") in {"low", "medium", "high"}
            assert isinstance(triage.get("summary"), str) and len(triage["summary"]) > 0
            assert isinstance(triage.get("proposed_resolution"), str) and len(triage["proposed_resolution"]) > 0
            args = triage.get("arguments") or []
            assert isinstance(args, list) and len(args) == 3, f"expected 3 arguments, got {len(args)}"
            split = triage.get("suggested_split") or {}
            assert "client_pct" in split and "specialist_pct" in split, f"missing split keys: {split}"
        finally:
            # CLEANUP: delete dispute and revert request state
            try:
                mongo.disputes.delete_one({"_id": ObjectId(dispute_id)})
            except Exception:
                pass
            mongo.requests.update_one(
                {"_id": ObjectId(req_id)},
                {"$set": {"disputed": original_disputed, "escrow_status": original_escrow_status}},
            )


# ---------- MARKETPLACE MEDIC filter ----------
class TestMarketplaceMedic:
    def test_medic_suspended_hides_from_marketplace(self, mongo, admin_session):
        spec = mongo.users.find_one({"email": SPECIALIST2_EMAIL, "role": "specialist"})
        if not spec:
            pytest.skip("specialist2@propmanage.io not found")
        spec_id = str(spec["_id"])
        original = spec.get("medic_suspended", False)

        try:
            # Baseline: specialist visible (filter by plumbing since marketplace caps at 100)
            r = requests.get(f"{API}/marketplace/specialists?category=plumbing", timeout=15)
            assert r.status_code == 200
            ids_before = {s["id"] for s in r.json()}
            assert spec_id in ids_before, "specialist2 not in baseline plumbing marketplace listing"

            # Set medic_suspended=true
            mongo.users.update_one({"_id": spec["_id"]}, {"$set": {"medic_suspended": True}})

            # Verify absence
            r2 = requests.get(f"{API}/marketplace/specialists?category=plumbing", timeout=15)
            assert r2.status_code == 200
            ids_after = {s["id"] for s in r2.json()}
            assert spec_id not in ids_after, "specialist2 STILL in marketplace after medic_suspended=true"
        finally:
            mongo.users.update_one({"_id": spec["_id"]}, {"$set": {"medic_suspended": original}})


# ---------- KYC prevalidation via simulate ----------
class TestKycPrevalidateSimulate:
    def test_kyc_simulate_writes_ledger(self, admin_session):
        # Baseline ledger count
        before_resp = admin_session.get(f"{API}/admin/orchestrator/ledger?limit=200", timeout=15).json()
        before = before_resp.get("items", before_resp) if isinstance(before_resp, dict) else before_resp
        n_before = len([x for x in before if x.get("playbook_id") == "kyc_prevalidation_reporter"])

        r = admin_session.post(f"{API}/admin/orchestrator/simulate/kyc_prevalidated", timeout=30)
        assert r.status_code == 200
        ledger = r.json().get("ledger") or {}
        assert ledger.get("outcome") == "auto_resolved"

        after_resp = admin_session.get(f"{API}/admin/orchestrator/ledger?limit=200", timeout=15).json()
        after = after_resp.get("items", after_resp) if isinstance(after_resp, dict) else after_resp
        n_after = len([x for x in after if x.get("playbook_id") == "kyc_prevalidation_reporter"])
        assert n_after > n_before, f"ledger did not grow: {n_before}→{n_after}"


# ---------- PRICE OBSERVATORY ----------
class TestPriceObservatoryPublic:
    def test_public_prices_132_rows(self):
        r = requests.get(f"{API}/construction/prices/public", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 132, f"expected 132 rows, got {data['count']}"
        for item in data["items"][:5]:
            assert item["trust_grade"] == "C"
            assert item["preliminary"] is True
        assert "disclaimer" in data

    def test_public_prices_filter_category(self):
        r = requests.get(f"{API}/construction/prices/public?category=zugravit", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 12, f"expected 12 zugravit rows, got {data['count']}"
        assert all(i["category"] == "zugravit" for i in data["items"])

    def test_public_prices_filter_city(self):
        r = requests.get(f"{API}/construction/prices/public?city=Cluj-Napoca", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] > 0
        assert all(i["city"] == "Cluj-Napoca" for i in data["items"])


class TestPriceObservatoryAdmin:
    def test_add_validation_invalid_unit(self, admin_session):
        r = admin_session.post(f"{API}/construction/prices", json={
            "category": "zugravit", "service": "TEST_INVALID_UNIT",
            "city": "București", "unit": "invalid_unit",
            "price_min": 10, "price_med": 20, "price_max": 30,
        }, timeout=15)
        assert r.status_code == 400

    def test_add_validation_min_gt_med(self, admin_session):
        r = admin_session.post(f"{API}/construction/prices", json={
            "category": "zugravit", "service": "TEST_INVALID_RANGE",
            "city": "București", "unit": "mp",
            "price_min": 50, "price_med": 20, "price_max": 100,
        }, timeout=15)
        assert r.status_code == 400

    def test_add_observation_upgrades_trust(self, admin_session):
        """Adding a 2nd admin_manual observation on an existing seed combo → trust upgrades to B, preliminary=false."""
        # Pick a seed combo (zugravit, Vopsea lavabilă (2 straturi), București, mp, mid)
        payload = {
            "category": "zugravit",
            "service": "Vopsea lavabilă (2 straturi)",
            "city": "București",
            "unit": "mp",
            "price_min": 15, "price_med": 20, "price_max": 30,
            "experience_level": "mid",
            "notes": "TEST_iter88",
        }
        r = admin_session.post(f"{API}/construction/prices", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        obs_id = r.json()["id"]

        try:
            # Public aggregate should now show 2 observations, trust=B, preliminary=false
            pub = requests.get(
                f"{API}/construction/prices/public?category=zugravit&city=București",
                timeout=15,
            ).json()
            match = next(
                (i for i in pub["items"] if i["service"] == "Vopsea lavabilă (2 straturi)"
                 and i["city"] == "București" and i["experience_level"] == "mid"),
                None,
            )
            assert match, "combo not found in aggregate"
            assert match["observations"] == 2, f"expected 2 obs, got {match['observations']}"
            assert match["trust_grade"] == "B"
            assert match["preliminary"] is False
        finally:
            d = admin_session.delete(f"{API}/construction/prices/{obs_id}", timeout=15)
            assert d.status_code == 200


class TestPriceObservatoryCSV:
    def test_import_csv_valid_and_invalid_rows(self, admin_session):
        csv_text = (
            "category,service,city,unit,price_min,price_med,price_max,experience_level\n"
            "zugravit,TEST_iter88_csv_valid1,București,mp,10,15,25,mid\n"
            "faianta,TEST_iter88_csv_valid2,Timișoara,mp,55,80,120,expert\n"
            "invalid_row_missing,,București,mp,10,15,25,mid\n"
        )
        r = admin_session.post(f"{API}/construction/prices/import-csv",
                               json={"csv": csv_text}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["imported"] == 2, f"expected 2 imported, got {data['imported']}"
        assert len(data["errors"]) >= 1, "expected at least 1 error row"

        # Cleanup: fetch and delete the 2 TEST_ rows
        listing = admin_session.get(f"{API}/construction/prices?limit=500", timeout=15).json()
        for it in listing.get("items", []):
            if str(it.get("service", "")).startswith("TEST_iter88_csv"):
                admin_session.delete(f"{API}/construction/prices/{it['id']}", timeout=15)

    def test_export_csv_has_header(self, admin_session):
        r = admin_session.get(f"{API}/construction/prices/export", timeout=20)
        assert r.status_code == 200
        text = r.content.decode("utf-8-sig")
        first_line = text.splitlines()[0]
        assert "category" in first_line and "service" in first_line and "city" in first_line


# ---------- REGRESSION SMOKE ----------
class TestRegression:
    def test_admin_score_still_ok(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=15)
        assert r.status_code == 200

    def test_public_taxonomy_still_ok(self):
        r = requests.get(f"{API}/construction/taxonomy/public", timeout=15)
        assert r.status_code == 200
        assert r.json()["count"] > 0
