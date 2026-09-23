"""Specialist Lead Credits — first-activation grant + D2 submit_offer consumption.

Canonical: 135 onboarding / 45 per submit_offer, then 45 RON wallet fallback.
Missing/null lead_credits == 0. No backfill. Not wallet, tokens, vouchers, or entitlements.
Public /accept does not consume credits (D13 residual waived only).
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient

from tests.test_config import CLIENT_EMAIL, CLIENT_PASSWORD

BASE = (os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "propmanage_db")
AUTH_PY = Path(__file__).resolve().parents[1] / "routes" / "auth.py"

BECOME_PAYLOAD = {
    "phone": "+40712345678",
    "service_categories": ["plumbing"],
    "coverage_zones": ["București"],
    "bio": "Lead credits test specialist",
}


def _register(role, **extra):
    s = requests.Session()
    email = f"TEST_lc_{role}_{uuid.uuid4().hex[:10]}@propmanage.io"
    payload = {
        "email": email,
        "password": "TestPass123!",
        "name": f"LC {role.title()}",
        "role": role,
        "terms_accepted": True,
        "privacy_policy_accepted": True,
        **extra,
    }
    if role == "specialist":
        payload.setdefault("phone", "+40712000999")
        payload.setdefault("service_categories", ["plumbing"])
        payload.setdefault("coverage_zones", ["bucuresti-sector1"])
    r = s.post(f"{API}/auth/register", json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text
    return s, r.json()


def _me(s):
    r = s.get(f"{API}/auth/me", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def _credits(user):
    v = user.get("lead_credits")
    return 0 if v is None else int(v)


def _wallet(user):
    return float(user.get("wallet_balance") or 0)


def _tokens(user):
    return int(user.get("tokens") or 0)


def _create_property(client_s):
    r = client_s.post(f"{API}/properties", json={
        "name": "TEST_LC_Prop",
        "address": "Str. Lead Credits 1",
        "type": "apartment",
        "surface": 60.0,
        "rooms": 2,
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _create_request(client_s, property_id, title="TEST_LC_Req"):
    r = client_s.post(f"{API}/requests", json={
        "property_id": property_id,
        "category": "plumbing",
        "title": title,
        "description": "Lead credits acceptance test",
        "priority": "normal",
        "budget_estimate": 200.0,
    }, timeout=15)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _submit_offer(spec_s, req_id, extra=None):
    body = {"message": "LC offer", "proposed_start_date": "2026-10-01", "estimated_hours": 4}
    if extra:
        body.update(extra)
    return spec_s.post(f"{API}/requests/{req_id}/offers", json=body, timeout=20)


def _txs(spec_s):
    r = spec_s.get(f"{API}/transactions", timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


# ---------- 1. Native specialist registration ----------
class TestNativeSpecialistRegistration:
    def test_native_specialist_gets_135_credits_and_zero_wallet(self):
        s, user = _register("specialist")
        assert _wallet(user) == 0.0
        assert _credits(user) == 135
        me = _me(s)
        assert _wallet(me) == 0.0
        assert _credits(me) == 135
        assert _tokens(me) == 0


# ---------- 2. Google / client creation ----------
class TestGoogleCreatedClient:
    def test_native_client_has_zero_lead_credits(self):
        """Google OAuth creates the same client grant boundary: no Lead Credits."""
        s, user = _register("client")
        assert _credits(user) == 0
        assert _wallet(user) == 0.0
        assert _credits(_me(s)) == 0

    def test_google_oauth_insert_sets_zero_lead_credits_not_135(self):
        src = AUTH_PY.read_text()
        assert src.count('"lead_credits": 0') >= 2
        assert '"lead_credits": 135 if data.role == "specialist"' in src
        google_blocks = [b for b in src.split("new_user = {") if '"google_auth": True' in b[:800]]
        assert len(google_blocks) >= 2, "expected two Google OAuth new_user inserts"
        for block in google_blocks:
            head = block[:900]
            assert '"lead_credits": 135' not in head
            assert '"lead_credits": 0' in head


# ---------- 3 + 4. Client → specialist ----------
class TestBecomeSpecialistGrant:
    def test_first_become_specialist_grants_135_wallet_unchanged(self):
        s, user = _register("client")
        assert _credits(user) == 0
        wallet_before = _wallet(user)
        r = s.post(f"{API}/auth/become-specialist", json=BECOME_PAYLOAD, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["role"] == "specialist"
        assert data.get("dual_role_enabled") is True
        assert data.get("specialist_onboarded_at")
        assert _credits(data) == 135
        assert _wallet(data) == wallet_before
        me = _me(s)
        assert _credits(me) == 135
        assert _wallet(me) == wallet_before

    def test_repeated_become_specialist_rejected_no_second_grant(self):
        s, _ = _register("client")
        r1 = s.post(f"{API}/auth/become-specialist", json=BECOME_PAYLOAD, timeout=20)
        assert r1.status_code == 200, r1.text
        assert _credits(r1.json()) == 135
        r2 = s.post(f"{API}/auth/become-specialist", json=BECOME_PAYLOAD, timeout=20)
        assert r2.status_code == 400, r2.text
        assert _credits(_me(s)) == 135


# ---------- 5–11. D2 submit_offer journey ----------
@pytest.fixture(scope="module")
def journey():
    client_s, client = _register("client")
    spec_s, spec = _register("specialist")
    prop_id = _create_property(client_s)
    req_ids = [_create_request(client_s, prop_id, f"TEST_LC_Req_{i}") for i in range(5)]
    return {
        "client_s": client_s,
        "client": client,
        "spec_s": spec_s,
        "spec": spec,
        "prop_id": prop_id,
        "req_ids": req_ids,
    }


def _assert_request_unassigned(session, req_id):
    req = session.get(f"{API}/requests/{req_id}", timeout=15).json()
    assert req["status"] == "open"
    assert not req.get("specialist_id")
    return req


class TestSubmitOfferLeadCreditsThenWallet:
    def test_first_submit_consumes_credits_not_wallet(self, journey):
        spec_s = journey["spec_s"]
        before = _me(spec_s)
        client_tokens = _tokens(_me(journey["client_s"]))
        spec_tokens = _tokens(before)
        assert _credits(before) == 135
        wallet_before = _wallet(before)
        req_id = journey["req_ids"][0]
        r = _submit_offer(spec_s, req_id, extra={"fee_ron": 25, "priority_fee_ron": 10})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("paid_with") == "lead_credit"
        assert body.get("lead_credits_after") == 90
        assert body.get("fee_paid") == 0
        assert body.get("offer_id")
        after = _me(spec_s)
        assert _credits(after) == 90
        assert _wallet(after) == wallet_before
        _assert_request_unassigned(journey["client_s"], req_id)
        credit_txs = [t for t in _txs(spec_s) if t.get("type") == "lead_credit" and t.get("request_id") == req_id]
        assert len(credit_txs) == 1
        assert credit_txs[0].get("currency") == "lead_credits"
        assert credit_txs[0].get("amount") == -45
        assert credit_txs[0].get("remaining") == 90
        assert credit_txs[0].get("offer_id") == body["offer_id"]
        fee_txs = [t for t in _txs(spec_s) if t.get("type") == "lead_fee" and t.get("request_id") == req_id]
        assert fee_txs == []
        stacked = [t for t in _txs(spec_s) if t.get("type") == "marketplace_offer_fee" and t.get("request_id") == req_id]
        assert stacked == []
        assert _tokens(_me(journey["client_s"])) == client_tokens
        assert _tokens(after) == spec_tokens

    def test_second_submit_90_to_45(self, journey):
        spec_s = journey["spec_s"]
        wallet_before = _wallet(_me(spec_s))
        req_id = journey["req_ids"][1]
        r = _submit_offer(spec_s, req_id)
        assert r.status_code == 200, r.text
        after = _me(spec_s)
        assert _credits(after) == 45
        assert _wallet(after) == wallet_before
        _assert_request_unassigned(journey["client_s"], req_id)

    def test_third_submit_45_to_0(self, journey):
        spec_s = journey["spec_s"]
        wallet_before = _wallet(_me(spec_s))
        req_id = journey["req_ids"][2]
        r = _submit_offer(spec_s, req_id)
        assert r.status_code == 200, r.text
        after = _me(spec_s)
        assert _credits(after) == 0
        assert _wallet(after) == wallet_before
        _assert_request_unassigned(journey["client_s"], req_id)

    def test_fourth_submit_charges_wallet_lead_fee(self, journey):
        spec_s = journey["spec_s"]
        before = _me(spec_s)
        assert _credits(before) == 0
        top = spec_s.post(f"{API}/wallet/topup", params={"amount": 100}, timeout=15)
        assert top.status_code == 200, top.text
        wallet_before = _wallet(_me(spec_s))
        assert wallet_before >= 45
        req_id = journey["req_ids"][3]
        r = _submit_offer(spec_s, req_id)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("paid_with") == "wallet"
        after = _me(spec_s)
        assert _credits(after) == 0
        assert _wallet(after) == pytest.approx(wallet_before - 45.0, abs=0.01)
        _assert_request_unassigned(journey["client_s"], req_id)
        fee_txs = [t for t in _txs(spec_s) if t.get("type") == "lead_fee" and t.get("request_id") == req_id]
        assert len(fee_txs) == 1
        assert fee_txs[0].get("currency") == "RON"
        credit_txs = [t for t in _txs(spec_s) if t.get("type") == "lead_credit" and t.get("request_id") == req_id]
        assert credit_txs == []

    def test_no_credits_insufficient_wallet_rejected(self, journey, mongo):
        spec_s = journey["spec_s"]
        spec = _me(spec_s)
        mongo.users.update_one(
            {"_id": ObjectId(spec["id"])},
            {"$set": {"lead_credits": 0, "wallet_balance": 10.0}},
        )
        before = _me(spec_s)
        assert _credits(before) == 0
        assert _wallet(before) == pytest.approx(10.0, abs=0.01)
        client_tokens = _tokens(_me(journey["client_s"]))
        req_id = journey["req_ids"][4]
        r = _submit_offer(spec_s, req_id)
        assert r.status_code == 400, r.text
        after = _me(spec_s)
        assert _credits(after) == 0
        assert _wallet(after) == pytest.approx(10.0, abs=0.01)
        offers = mongo.marketplace_offers.count_documents({"request_id": req_id})
        assert offers == 0
        _assert_request_unassigned(journey["client_s"], req_id)
        assert _tokens(_me(journey["client_s"])) == client_tokens

    def test_public_accept_does_not_consume_credits(self, journey):
        spec_s = journey["spec_s"]
        client_s, _ = _register("client")
        prop_id = _create_property(client_s)
        req_id = _create_request(client_s, prop_id, "TEST_LC_PublicAccept")
        before = _me(spec_s)
        r = spec_s.post(f"{API}/requests/{req_id}/accept", json={}, timeout=20)
        assert r.status_code == 400, r.text
        after = _me(spec_s)
        assert _credits(after) == _credits(before)
        assert _wallet(after) == _wallet(before)
        req = client_s.get(f"{API}/requests/{req_id}", timeout=15).json()
        assert req["status"] == "open"
        assert not req.get("specialist_id")

    def test_fee_waived_consumes_neither(self, mongo):
        client_s, _ = _register("client")
        spec_s, spec = _register("specialist")
        prop_id = _create_property(client_s)
        req_id = _create_request(client_s, prop_id, "TEST_LC_Waived")
        mongo.requests.update_one(
            {"_id": ObjectId(req_id)},
            {"$set": {"lead_fee_waived": True, "direct_specialist_id": spec["id"]}},
        )
        before = _me(spec_s)
        r = spec_s.post(f"{API}/requests/{req_id}/accept", json={}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json().get("paid_with") == "waived"
        after = _me(spec_s)
        assert _credits(after) == _credits(before) == 135
        assert _wallet(after) == _wallet(before)
        req = spec_s.get(f"{API}/requests/{req_id}", timeout=15).json()
        assert req["status"] == "assigned"
        txs = [t for t in _txs(spec_s) if t.get("request_id") == req_id]
        assert txs == []


class TestOfferLostNoRefund:
    def test_losing_offer_does_not_refund_credits(self):
        client_s, _ = _register("client")
        spec_a_s, spec_a = _register("specialist")
        spec_b_s, spec_b = _register("specialist")
        prop_id = _create_property(client_s)
        req_id = _create_request(client_s, prop_id, "TEST_LC_Lose")
        ra = _submit_offer(spec_a_s, req_id)
        rb = _submit_offer(spec_b_s, req_id)
        assert ra.status_code == 200, ra.text
        assert rb.status_code == 200, rb.text
        offer_a = ra.json()["offer_id"]
        acc = client_s.post(f"{API}/requests/{req_id}/offers/{offer_a}/accept", timeout=20)
        assert acc.status_code == 200, acc.text
        after_b = _me(spec_b_s)
        assert _credits(after_b) == 90
        lose_refunds = [
            t for t in _txs(spec_b_s)
            if t.get("request_id") == req_id and t.get("type") == "lead_credit" and t.get("amount", 0) > 0
        ]
        assert lose_refunds == []


# ---------- 12. Profile cannot write lead_credits ----------
class TestLeadCreditsNotClientWritable:
    def test_profile_update_cannot_set_lead_credits(self):
        s, _ = _register("specialist")
        before = _me(s)
        r = s.patch(f"{API}/auth/profile", json={
            "name": "LC Renamed",
            "lead_credits": 9999,
            "wallet_balance": 9999,
            "tokens": 9999,
        }, timeout=15)
        assert r.status_code in (200, 400, 422), r.text
        after = _me(s)
        assert _credits(after) == 135
        assert _wallet(after) == 0.0
        assert _tokens(after) == 0
        if r.status_code == 200:
            assert after.get("name") == "LC Renamed"
        assert _credits(before) == 135


# ---------- 13. Concurrent submit / cap ----------
class TestConcurrentSubmitAtomicity:
    def test_same_specialist_cannot_spend_credits_twice_on_one_request(self):
        client_s, _ = _register("client")
        spec_s, spec = _register("specialist")
        prop_id = _create_property(client_s)
        req_id = _create_request(client_s, prop_id, "TEST_LC_Race")
        other = requests.Session()
        other.cookies.update(spec_s.cookies)

        def _hit(session):
            return _submit_offer(session, req_id)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(_hit, [spec_s, other]))
        codes = sorted(r.status_code for r in results)
        assert codes == [200, 409], [f"{r.status_code}:{r.text[:160]}" for r in results]
        after = _me(spec_s)
        assert _credits(after) == 90
        assert _credits(after) >= 0
        _assert_request_unassigned(client_s, req_id)
        credit_txs = [t for t in _txs(spec_s) if t.get("type") == "lead_credit" and t.get("request_id") == req_id]
        assert len(credit_txs) == 1

    def test_sixth_offer_is_rejected_and_does_not_debit(self):
        client_s, _ = _register("client")
        prop_id = _create_property(client_s)
        req_id = _create_request(client_s, prop_id, "TEST_LC_Cap5")
        for i in range(5):
            spec_s, _ = _register("specialist")
            r = _submit_offer(spec_s, req_id)
            assert r.status_code == 200, r.text
        extra_s, _ = _register("specialist")
        before = _me(extra_s)
        assert _credits(before) == 135
        r = _submit_offer(extra_s, req_id)
        assert r.status_code == 400, r.text
        after = _me(extra_s)
        assert _credits(after) == 135
        assert _wallet(after) == _wallet(before)
        _assert_request_unassigned(client_s, req_id)


# ---------- F. technical insert failure refunds debit ----------
class TestTechnicalInsertFailureRefund:
    def test_debit_reversed_after_simulated_insert_failure(self, mongo):
        import asyncio
        from lead_credits import debit_participation, refund_participation

        credit_uid = ObjectId()
        wallet_uid = ObjectId()
        mongo.users.insert_one({
            "_id": credit_uid,
            "email": f"TEST_lc_refund_{credit_uid}@propmanage.io",
            "role": "specialist",
            "lead_credits": 135,
            "wallet_balance": 0.0,
        })
        mongo.users.insert_one({
            "_id": wallet_uid,
            "email": f"TEST_lc_wrefund_{wallet_uid}@propmanage.io",
            "role": "specialist",
            "lead_credits": 0,
            "wallet_balance": 80.0,
        })

        async def _fail_then_refund():
            credit_debit = await debit_participation(credit_uid)
            assert credit_debit["payment"] == "credit"
            assert credit_debit["remaining_credits"] == 90
            mid = mongo.users.find_one({"_id": credit_uid})
            assert int(mid["lead_credits"]) == 90
            await refund_participation(credit_uid, credit_debit["payment"])

            wallet_debit = await debit_participation(wallet_uid)
            assert wallet_debit["payment"] == "wallet"
            await refund_participation(wallet_uid, wallet_debit["payment"])

        asyncio.run(_fail_then_refund())
        credit_after = mongo.users.find_one({"_id": credit_uid})
        assert int(credit_after["lead_credits"]) == 135
        assert float(credit_after.get("wallet_balance") or 0) == 0.0
        wallet_after = mongo.users.find_one({"_id": wallet_uid})
        assert int(wallet_after.get("lead_credits") or 0) == 0
        assert float(wallet_after["wallet_balance"]) == pytest.approx(80.0, abs=0.01)


# ---------- existing specialists: missing field treated as 0 (demo login) ----------
def test_existing_demo_client_missing_credits_is_zero():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    me = _me(s)
    assert _credits(me) == 0
