"""Phase 5 backend tests: AI Assistant (Claude Haiku 4.5), 2FA TOTP, Public Marketplace,
Search/Filter on requests, Property Timeline, plus regression smoke."""
import os
import time
import base64
import pytest
import requests
import pyotp
from tests.test_config import OWNER_ADMIN_PASSWORD

def _load_base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if not url:
        # fallback: read from frontend/.env
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass
    return url.rstrip("/")


BASE_URL = _load_base_url()
assert BASE_URL, "REACT_APP_BACKEND_URL not set"

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}


def _login(creds, totp_code=None):
    s = requests.Session()
    body = dict(creds)
    if totp_code:
        body["totp_code"] = totp_code
    r = s.post(f"{BASE_URL}/api/auth/login", json=body, timeout=20)
    return s, r


@pytest.fixture(scope="module")
def client_session():
    s, r = _login(CLIENT)
    assert r.status_code == 200, f"client login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def spec_session():
    s, r = _login(SPEC)
    assert r.status_code == 200, f"spec login failed: {r.status_code} {r.text}"
    return s


# ============ AI ASSISTANT ============

class TestAIChat:
    def test_ai_chat_hvac_diagnosis(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/ai/chat",
            json={"message": "AC nu mai răcește în living"},
            timeout=60,
        )
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert "reply" in data and isinstance(data["reply"], str) and len(data["reply"]) > 0
        assert "session_id" in data and data["session_id"]
        reply_lower = data["reply"].lower()
        # Should mention HVAC category and/or priority/buget hints
        has_hvac = "hvac" in reply_lower or "ac" in reply_lower or "aer" in reply_lower or "climatizare" in reply_lower
        assert has_hvac, f"reply lacks HVAC context: {data['reply'][:300]}"

    def test_ai_chat_multi_turn_session(self, client_session):
        sid = f"TEST_phase5_session_{int(time.time())}"
        r1 = client_session.post(
            f"{BASE_URL}/api/ai/chat",
            json={"message": "Mă cheamă Ion și am o problemă la centrală termică.", "session_id": sid},
            timeout=60,
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["session_id"] == sid

        r2 = client_session.post(
            f"{BASE_URL}/api/ai/chat",
            json={"message": "Cum mă cheamă? Răspunde scurt cu numele meu.", "session_id": sid},
            timeout=60,
        )
        assert r2.status_code == 200, r2.text
        reply2 = r2.json()["reply"].lower()
        assert "ion" in reply2, f"context not maintained: {reply2[:300]}"

    def test_ai_history(self, client_session):
        sid = f"TEST_phase5_hist_{int(time.time())}"
        client_session.post(
            f"{BASE_URL}/api/ai/chat",
            json={"message": "Salut!", "session_id": sid},
            timeout=60,
        )
        r = client_session.get(f"{BASE_URL}/api/ai/history", params={"session_id": sid}, timeout=20)
        assert r.status_code == 200
        msgs = r.json()
        assert isinstance(msgs, list)
        assert len(msgs) >= 2  # user + assistant
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


# ============ 2FA ============

class TestTwoFA:
    def test_full_2fa_lifecycle(self, client_session):
        # Status before
        r = client_session.get(f"{BASE_URL}/api/auth/2fa/status", timeout=10)
        assert r.status_code == 200
        initial_enabled = r.json().get("enabled", False)
        # If already enabled from prior run, disable first (try common secret? skip - we don't have it)
        if initial_enabled:
            pytest.skip("2FA already enabled from prior run; cannot reset without secret")

        # Setup
        r = client_session.post(f"{BASE_URL}/api/auth/2fa/setup", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "secret" in body and len(body["secret"]) >= 16
        assert "otp_uri" in body and body["otp_uri"].startswith("otpauth://")
        assert "qr_code" in body and body["qr_code"].startswith("data:image/png;base64,")
        # Validate base64 PNG decodes
        b64part = body["qr_code"].split(",", 1)[1]
        png = base64.b64decode(b64part)
        assert png[:8] == b"\x89PNG\r\n\x1a\n", "qr_code is not a valid PNG"
        secret = body["secret"]

        # Verify with wrong code -> 401
        r = client_session.post(
            f"{BASE_URL}/api/auth/2fa/verify", json={"code": "000000"}, timeout=10
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code} {r.text}"

        # Verify with valid code
        valid_code = pyotp.TOTP(secret).now()
        r = client_session.post(
            f"{BASE_URL}/api/auth/2fa/verify", json={"code": valid_code}, timeout=10
        )
        assert r.status_code == 200, r.text
        assert r.json().get("enabled") is True

        # Status now enabled
        r = client_session.get(f"{BASE_URL}/api/auth/2fa/status", timeout=10)
        assert r.status_code == 200
        assert r.json().get("enabled") is True

        # Login WITHOUT totp_code -> should NOT succeed; expect non-200 with totp_required hint
        _, r_nocode = _login(CLIENT)
        assert r_nocode.status_code != 200, (
            f"login should fail when 2FA enabled and no code provided: {r_nocode.status_code}"
        )
        # FastAPI HTTPException(202, dict) raises as status 202 with the dict in detail
        try:
            body = r_nocode.json()
        except Exception:
            body = {}
        detail_blob = str(body)
        assert "totp_required" in detail_blob, f"expected totp_required marker: {body}"

        # Login WITH valid totp_code -> success
        time.sleep(1)  # ensure not same window edge
        valid_code = pyotp.TOTP(secret).now()
        _, r_ok = _login(CLIENT, totp_code=valid_code)
        assert r_ok.status_code == 200, f"login with valid totp failed: {r_ok.status_code} {r_ok.text}"

        # Disable with invalid code -> 401
        r = client_session.post(
            f"{BASE_URL}/api/auth/2fa/disable", json={"code": "000000"}, timeout=10
        )
        assert r.status_code == 401

        # Disable with valid code -> ok
        valid_code = pyotp.TOTP(secret).now()
        r = client_session.post(
            f"{BASE_URL}/api/auth/2fa/disable", json={"code": valid_code}, timeout=10
        )
        assert r.status_code == 200, r.text
        assert r.json().get("enabled") is False

        # Status disabled
        r = client_session.get(f"{BASE_URL}/api/auth/2fa/status", timeout=10)
        assert r.json().get("enabled") is False

        # Login without code now works again
        _, r_plain = _login(CLIENT)
        assert r_plain.status_code == 200


# ============ PUBLIC MARKETPLACE ============

class TestMarketplace:
    def test_public_no_auth(self):
        # Use bare requests, no cookies
        r = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=15)
        assert r.status_code == 200, r.text
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        item = items[0]
        for k in ("id", "name", "specialty", "rating", "reviews_count", "verified"):
            assert k in item, f"missing key {k} in {item}"
        # ObjectId should be excluded -> 'id' is str
        assert isinstance(item["id"], str)
        assert "_id" not in item

    def test_filter_category_and_verified(self):
        r = requests.get(
            f"{BASE_URL}/api/marketplace/specialists",
            params={"category": "hvac", "verified_only": "true"},
            timeout=15,
        )
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        for s in items:
            assert s["specialty"] == "hvac", f"category filter broken: {s}"
            assert s["verified"] is True, f"verified filter broken: {s}"

    def test_sort_by_reviews(self):
        r = requests.get(
            f"{BASE_URL}/api/marketplace/specialists",
            params={"sort": "reviews"},
            timeout=15,
        )
        assert r.status_code == 200
        items = r.json()
        if len(items) >= 2:
            counts = [s.get("reviews_count", 0) for s in items]
            assert counts == sorted(counts, reverse=True), f"reviews sort broken: {counts}"

    def test_sort_by_rating(self):
        r = requests.get(
            f"{BASE_URL}/api/marketplace/specialists",
            params={"sort": "rating"},
            timeout=15,
        )
        assert r.status_code == 200

    def test_sort_recent(self):
        r = requests.get(
            f"{BASE_URL}/api/marketplace/specialists",
            params={"sort": "recent"},
            timeout=15,
        )
        assert r.status_code == 200


# ============ SEARCH/FILTER REQUESTS ============

class TestRequestSearch:
    @pytest.fixture(scope="class")
    def seed_request(self, client_session):
        # Get a property for the client
        r = client_session.get(f"{BASE_URL}/api/properties", timeout=15)
        assert r.status_code == 200
        props = r.json()
        if not props:
            # Create one
            r2 = client_session.post(
                f"{BASE_URL}/api/properties",
                json={"label": "TEST_phase5_prop", "address": "Str Test 1", "type": "apartment", "surface": 50},
                timeout=15,
            )
            assert r2.status_code in (200, 201), r2.text
            prop_id = r2.json()["id"]
        else:
            prop_id = props[0]["id"]
        # Create a HVAC request mentioning 'centrala'
        r3 = client_session.post(
            f"{BASE_URL}/api/requests",
            json={
                "property_id": prop_id,
                "title": "TEST_phase5 centrala termica nu pornește",
                "description": "Centrala merge intermitent",
                "category": "hvac",
                "priority": "urgent",
            },
            timeout=15,
        )
        assert r3.status_code in (200, 201), r3.text
        return r3.json()["id"], prop_id

    def test_search_q_only(self, client_session, seed_request):
        r = client_session.get(
            f"{BASE_URL}/api/requests", params={"q": "centrala"}, timeout=15
        )
        assert r.status_code == 200
        items = r.json()
        assert any("centrala" in i.get("title", "").lower() for i in items), "search 'centrala' returned nothing"

    def test_search_q_and_category_status(self, client_session, seed_request):
        r = client_session.get(
            f"{BASE_URL}/api/requests",
            params={"q": "centrala", "category": "hvac", "status": "open"},
            timeout=15,
        )
        assert r.status_code == 200
        items = r.json()
        for i in items:
            assert i.get("category") == "hvac"
            assert i.get("status") == "open"

    def test_filter_priority(self, client_session, seed_request):
        r = client_session.get(
            f"{BASE_URL}/api/requests", params={"priority": "urgent"}, timeout=15
        )
        assert r.status_code == 200
        items = r.json()
        for i in items:
            assert i.get("priority") == "urgent"


# ============ PROPERTY TIMELINE ============

class TestTimeline:
    def test_timeline_structure(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties", timeout=15)
        props = r.json()
        if not props:
            pytest.skip("no property to test timeline")
        prop_id = props[0]["id"]
        r2 = client_session.get(f"{BASE_URL}/api/properties/{prop_id}/timeline", timeout=15)
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert "property" in data and "events" in data and "total" in data
        assert isinstance(data["events"], list)
        assert data["total"] == len(data["events"])
        # property should not leak _id
        assert "_id" not in data["property"]
        assert "id" in data["property"]
        # Events have expected fields
        if data["events"]:
            e = data["events"][0]
            assert "type" in e and "timestamp" in e
            assert e["type"] in {"request_created", "specialist_assigned", "work_completed", "confirmed"}
        # Sort: newest first
        ts = [e.get("timestamp", "") for e in data["events"]]
        assert ts == sorted(ts, reverse=True), "events not sorted newest-first"

    def test_timeline_404(self, client_session):
        r = client_session.get(
            f"{BASE_URL}/api/properties/507f1f77bcf86cd799439011/timeline", timeout=15
        )
        assert r.status_code == 404


# ============ REGRESSION ============

class TestRegression:
    def test_login_without_2fa_works(self):
        _, r = _login(SPEC)
        assert r.status_code == 200

    def test_auth_me(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == CLIENT["email"]

    def test_properties_list(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/properties", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_specialists_authenticated(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/specialists", timeout=10)
        assert r.status_code == 200

    def test_specialist_public_profile(self):
        # Get any specialist id from marketplace
        items = requests.get(f"{BASE_URL}/api/marketplace/specialists", timeout=10).json()
        if not items:
            pytest.skip("no specialists")
        sid = items[0]["id"]
        r = requests.get(f"{BASE_URL}/api/specialists/{sid}/profile", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("rating", "reviews_count"):
            assert k in data

    def test_notifications(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
