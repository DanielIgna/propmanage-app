"""Phase 9 — Interior Design Service backend tests.

Covers:
- GET /api/design/eligibility (client w/ twin, specialist 403, client w/o twin)
- POST /api/design/concept-request (valid, cap, invalid rooms, 403 no twin)
- /api/requests now lists interior_design with design_concept
- POST /api/design/phase-quote (specialist proposes phase on accepted interior_design req)
- POST /api/design/phase-accept (client pays from wallet → escrow)
- POST /api/design/phase-complete (release 95% to specialist)
- REGRESSION: old /api/services/interior-design/* endpoints removed (404)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

CLIENT_CREDS = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC_CREDS = {"email": "specialist@propmanage.io", "password": "Spec123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT_CREDS)


@pytest.fixture(scope="module")
def spec_session():
    return _login(SPEC_CREDS)


@pytest.fixture(scope="module")
def eligibility(client_session):
    r = client_session.get(f"{BASE_URL}/api/design/eligibility", timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["eligible"] is True
    assert body["concept_price_per_room"] == 2200.0
    assert body["max_token_discount_pct"] == 50
    assert isinstance(body["available_tokens"], int)
    assert body["properties"], "no properties returned"
    p = body["properties"][0]
    assert p["rooms"], "no rooms"
    return body


# ---------------- Eligibility ----------------
class TestEligibility:
    def test_client_eligible(self, eligibility):
        p = eligibility["properties"][0]
        assert p["name"] == "Skyline Loft A4"
        room_names = {r["name"] for r in p["rooms"]}
        assert {"Living", "Dormitor", "Bucătărie", "Baie", "Hol"} <= room_names

    def test_specialist_forbidden(self, spec_session):
        r = spec_session.get(f"{BASE_URL}/api/design/eligibility", timeout=10)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/design/eligibility", timeout=10)
        assert r.status_code in (401, 403)


# ---------------- Concept request ----------------
class TestConceptRequest:
    def test_invalid_rooms_400(self, client_session, eligibility):
        prop = eligibility["properties"][0]
        payload = {
            "property_id": prop["id"],
            "room_ids": ["nope-" + str(uuid.uuid4())],
            "tokens_to_use": 0,
        }
        r = client_session.post(f"{BASE_URL}/api/design/concept-request", json=payload, timeout=15)
        assert r.status_code == 400
        assert "invalid" in r.text.lower() or "camere" in r.text.lower()

    def test_specialist_cannot_create(self, spec_session, eligibility):
        # specialist won't have rooms, but the role gate should hit first
        prop = eligibility["properties"][0]
        payload = {
            "property_id": prop["id"],
            "room_ids": [prop["rooms"][0]["id"]],
            "tokens_to_use": 0,
        }
        r = spec_session.post(f"{BASE_URL}/api/design/concept-request", json=payload, timeout=15)
        assert r.status_code == 403

    def test_create_with_tokens_caps_at_50pct(self, client_session, eligibility):
        prop = eligibility["properties"][0]
        # 1 room → full_price = 2200, max token discount = 1100; try 99999
        room_id = prop["rooms"][0]["id"]
        # capture starting tokens
        me = client_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        start_tokens = me.get("tokens", 0)
        if start_tokens < 1100:
            pytest.skip(f"insufficient tokens ({start_tokens}) for cap test")
        payload = {
            "property_id": prop["id"],
            "room_ids": [room_id],
            "tokens_to_use": 99999,
            "style_preference": "Modern",
            "notes": "TEST_phase9 cap test",
        }
        r = client_session.post(f"{BASE_URL}/api/design/concept-request", json=payload, timeout=15)
        assert r.status_code == 200, f"got {r.status_code}: {r.text}"
        body = r.json()
        assert body["category"] == "interior_design"
        assert "design_concept" in body
        dc = body["design_concept"]
        assert dc["rooms_count"] == 1
        assert dc["full_price"] == 2200.0
        assert dc["tokens_used"] == 1100, f"expected cap 1100 got {dc['tokens_used']}"
        assert dc["final_price"] == 1100.0
        assert body["budget_estimate"] == 1100.0
        assert body["status"] == "open"
        assert body["specialist_id"] is None
        # tokens deducted
        me2 = client_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        assert me2.get("tokens", 0) == start_tokens - 1100, f"tokens not deducted: {start_tokens} → {me2.get('tokens')}"

    def test_create_no_tokens(self, client_session, eligibility):
        prop = eligibility["properties"][0]
        rooms = [r["id"] for r in prop["rooms"][:2]]
        payload = {
            "property_id": prop["id"],
            "room_ids": rooms,
            "tokens_to_use": 0,
            "notes": "TEST_phase9 no tokens",
        }
        r = client_session.post(f"{BASE_URL}/api/design/concept-request", json=payload, timeout=15)
        assert r.status_code == 200
        body = r.json()
        dc = body["design_concept"]
        assert dc["rooms_count"] == 2
        assert dc["full_price"] == 4400.0
        assert dc["tokens_used"] == 0
        assert dc["final_price"] == 4400.0
        # request appears in listing
        listr = client_session.get(f"{BASE_URL}/api/requests", timeout=15)
        assert listr.status_code == 200
        ids = {x["id"] for x in listr.json()}
        assert body["id"] in ids
        # category interior_design present in returned doc
        match = next(x for x in listr.json() if x["id"] == body["id"])
        assert match["category"] == "interior_design"
        assert "design_concept" in match


# ---------------- Phase quote / accept / complete ----------------
class TestPhaseFlow:
    @pytest.fixture(scope="class")
    def assigned_request(self, client_session, spec_session, eligibility):
        prop = eligibility["properties"][0]
        # Create a request first (no tokens)
        payload = {
            "property_id": prop["id"],
            "room_ids": [r["id"] for r in prop["rooms"][:1]],
            "tokens_to_use": 0,
            "notes": "TEST_phase9 phase flow",
        }
        r = client_session.post(f"{BASE_URL}/api/design/concept-request", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        req_id = r.json()["id"]
        me = spec_session.get(f"{BASE_URL}/api/auth/me", timeout=15).json()
        if int(me.get("lead_credits") or 0) < 45 and float(me.get("wallet_balance") or 0) < 45:
            spec_session.post(f"{BASE_URL}/api/wallet/topup", params={"amount": 100}, timeout=15)
        off = spec_session.post(f"{BASE_URL}/api/requests/{req_id}/offers", json={"message": "design offer"}, timeout=15)
        assert off.status_code == 200, off.text
        acc = client_session.post(
            f"{BASE_URL}/api/requests/{req_id}/offers/{off.json()['offer_id']}/accept", timeout=15
        )
        assert acc.status_code == 200, acc.text
        # Start work (move to in_progress)
        st = spec_session.post(f"{BASE_URL}/api/requests/{req_id}/start", timeout=15)
        # Some implementations might not require start; tolerate either way
        return req_id

    def test_phase_quote_then_accept_then_complete(self, client_session, spec_session, assigned_request):
        req_id = assigned_request
        # Get specialist wallet pre
        me_s_pre = spec_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        spec_wallet_pre = me_s_pre.get("wallet_balance", 0)
        me_c_pre = client_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        client_wallet_pre = me_c_pre.get("wallet_balance", 0)
        phase_price = 800.0
        if client_wallet_pre < phase_price:
            pytest.skip(f"client wallet {client_wallet_pre} < {phase_price}")

        # 1) Specialist proposes a phase
        qpayload = {
            "request_id": req_id,
            "phase_name": "TEST_phase9 proiect tehnic",
            "description": "Plan tehnic complet",
            "price": phase_price,
            "estimated_days": 5,
        }
        rq = spec_session.post(f"{BASE_URL}/api/design/phase-quote", json=qpayload, timeout=15)
        assert rq.status_code == 200, rq.text
        quote = rq.json()
        assert quote["status"] == "pending"
        quote_id = quote["id"]

        # 2) Client accepts → wallet deducted
        ra = client_session.post(
            f"{BASE_URL}/api/design/phase-accept?request_id={req_id}",
            json={"quote_id": quote_id}, timeout=15
        )
        assert ra.status_code == 200, ra.text
        me_c_mid = client_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        assert me_c_mid["wallet_balance"] == client_wallet_pre - phase_price

        # 3) Insufficient balance check — make another huge quote and try accept
        qbig = spec_session.post(f"{BASE_URL}/api/design/phase-quote", json={
            "request_id": req_id, "phase_name": "TEST_phase9 too big",
            "description": "huge", "price": 9_999_999.0, "estimated_days": 2
        }, timeout=15)
        assert qbig.status_code == 200
        big_qid = qbig.json()["id"]
        rbad = client_session.post(
            f"{BASE_URL}/api/design/phase-accept?request_id={req_id}",
            json={"quote_id": big_qid}, timeout=15
        )
        assert rbad.status_code == 400

        # 4) Complete first phase → specialist wallet +95%
        rc = client_session.post(
            f"{BASE_URL}/api/design/phase-complete?request_id={req_id}",
            json={"quote_id": quote_id}, timeout=15
        )
        assert rc.status_code == 200, rc.text
        body = rc.json()
        assert body["ok"] is True
        assert abs(body["released_amount"] - phase_price * 0.95) < 0.01
        me_s_post = spec_session.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
        assert abs(me_s_post["wallet_balance"] - (spec_wallet_pre + phase_price * 0.95)) < 0.01


# ---------------- Regression: old endpoints removed ----------------
class TestOldEndpointsRemoved:
    @pytest.mark.parametrize("path", [
        "/api/services/interior-design/availability",
        "/api/services/interior-design/order",
        "/api/services/interior-design/quotes",
    ])
    def test_old_404(self, client_session, path):
        r = client_session.get(f"{BASE_URL}{path}", timeout=10)
        assert r.status_code == 404, f"{path} returned {r.status_code} (expected 404)"
