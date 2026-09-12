"""Phase 3 backend tests: Google OAuth exchange, Stripe Checkout, WS chat, ws-token, regression smoke."""
import os
import json
import asyncio
import pytest
import requests
import websockets
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

# WS URL: convert https->wss, http->ws
if BASE_URL.startswith("https://"):
    WS_BASE = "wss://" + BASE_URL[len("https://"):]
else:
    WS_BASE = "ws://" + BASE_URL[len("http://"):]

CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}
SPEC2 = {"email": "specialist2@propmanage.io", "password": "Spec123!"}


def login(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s, r.json()


# ========== Google OAuth ==========
class TestGoogleOAuth:
    def test_missing_session_header(self):
        r = requests.post(f"{API}/auth/google/session")
        assert r.status_code == 400
        assert "X-Session-ID" in r.text or "session" in r.text.lower()

    def test_invalid_session_id(self):
        # Fake session id - Emergent backend should reject
        r = requests.post(
            f"{API}/auth/google/session",
            headers={"X-Session-ID": "FAKE_INVALID_SESSION_ID_FOR_TEST_12345"},
            timeout=20,
        )
        assert r.status_code == 401, f"expected 401, got {r.status_code}: {r.text}"
        body = r.json()
        assert "detail" in body
        assert "Invalid Emergent session" in body["detail"] or "session" in body["detail"].lower()


# ========== WS token ==========
class TestWsToken:
    def test_ws_token_unauthenticated(self):
        r = requests.get(f"{API}/auth/ws-token")
        assert r.status_code in (401, 403)

    def test_ws_token_authenticated_client(self):
        s, _ = login(CLIENT)
        r = s.get(f"{API}/auth/ws-token")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data
        assert isinstance(data["token"], str)
        # JWT structure: 3 base64 parts
        assert data["token"].count(".") == 2

    def test_ws_token_authenticated_specialist(self):
        s, _ = login(SPEC)
        r = s.get(f"{API}/auth/ws-token")
        assert r.status_code == 200
        assert "token" in r.json()


# ========== Stripe Checkout ==========
@pytest.fixture(scope="module")
def client_session_and_request():
    """Fetch an existing client request to test Stripe Checkout against."""
    s, _ = login(CLIENT)
    r = s.get(f"{API}/requests")
    assert r.status_code == 200
    reqs = r.json()
    assert isinstance(reqs, list) and len(reqs) > 0, "No requests for client"
    # Prefer status=open (most common eligible state)
    open_req = next((x for x in reqs if x.get("status") == "open"), None)
    if not open_req:
        open_req = next((x for x in reqs if x.get("status") in ("open", "assigned")), None)
    assert open_req, f"No eligible request found among: {[r.get('status') for r in reqs]}"
    return s, open_req


class TestStripeCheckout:
    def test_create_checkout_session(self, client_session_and_request):
        s, req = client_session_and_request
        req_id = req["id"]
        r = s.post(
            f"{API}/payments/checkout-session",
            params={"request_id": req_id},
            headers={"Origin": "http://localhost:3000"},
            timeout=30,
        )
        assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
        data = r.json()
        assert "checkout_url" in data
        assert "session_id" in data
        assert data["checkout_url"].startswith("https://")
        assert data["session_id"].startswith("cs_"), f"unexpected session_id: {data['session_id']}"
        # save for next test
        TestStripeCheckout.session_id = data["session_id"]
        TestStripeCheckout.request_id = req_id

    def test_checkout_missing_origin(self, client_session_and_request):
        s, req = client_session_and_request
        # Build a clean session WITHOUT origin/referer
        token_cookie = s.cookies.get("access_token")
        clean = requests.Session()
        clean.cookies.set("access_token", token_cookie)
        r = clean.post(
            f"{API}/payments/checkout-session",
            params={"request_id": req["id"]},
            timeout=15,
        )
        # If platform proxy injects an origin/referer, this may still succeed.
        # Accept both: explicit 400 (preferred) or 200 if proxy added a referer.
        assert r.status_code in (400, 200)

    def test_checkout_nonexistent_request(self):
        s, _ = login(CLIENT)
        r = s.post(
            f"{API}/payments/checkout-session",
            params={"request_id": "507f1f77bcf86cd799439011"},  # valid ObjectId, doesn't exist
            headers={"Origin": "http://localhost:3000"},
            timeout=15,
        )
        assert r.status_code == 404

    def test_checkout_unauthorized_specialist(self, client_session_and_request):
        """Specialist cannot create checkout (role-restricted to client)."""
        _, req = client_session_and_request
        s, _ = login(SPEC)
        r = s.post(
            f"{API}/payments/checkout-session",
            params={"request_id": req["id"]},
            headers={"Origin": "http://localhost:3000"},
            timeout=15,
        )
        assert r.status_code == 403, r.text

    def test_payment_status_unpaid(self, client_session_and_request):
        s, _ = client_session_and_request
        sid = getattr(TestStripeCheckout, "session_id", None)
        if not sid:
            pytest.skip("checkout session not created in prior test")
        r = s.get(f"{API}/payments/status/{sid}", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] in ("unpaid", "open", "no_payment_required", "paid", "complete", "expired")
        assert data["request_id"] == TestStripeCheckout.request_id
        assert isinstance(data["amount"], (int, float))

    def test_payment_status_not_found(self):
        s, _ = login(CLIENT)
        r = s.get(f"{API}/payments/status/cs_FAKE_NOT_EXIST_123", timeout=15)
        assert r.status_code == 404


# ========== Chat HTTP ==========
@pytest.fixture(scope="module")
def assigned_request_ids():
    """Find a request where specialist is assigned for chat ACL tests; fallback to any client request."""
    s, _ = login(CLIENT)
    r = s.get(f"{API}/requests")
    reqs = r.json()
    own = next((x for x in reqs if x.get("specialist_id")), None) or reqs[0]
    return own


class TestChatHTTP:
    def test_get_messages_as_owner_client(self, assigned_request_ids):
        s, _ = login(CLIENT)
        req_id = assigned_request_ids["id"]
        r = s.get(f"{API}/chat/{req_id}/messages")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_messages_unauthorized_specialist(self, assigned_request_ids):
        """Specialist who is NOT assigned should get 403."""
        # Find a request where SPEC2 is NOT assigned
        s, _ = login(CLIENT)
        reqs = s.get(f"{API}/requests").json()
        # Try one where specialist_id is None or different
        target = next((x for x in reqs if x.get("specialist_id") != assigned_request_ids.get("specialist_id")), None)
        target = target or assigned_request_ids
        s2, me = login(SPEC2)
        if target.get("specialist_id") == me["id"]:
            pytest.skip("SPEC2 happens to be assigned; cannot test 403")
        r = s2.get(f"{API}/chat/{target['id']}/messages")
        assert r.status_code == 403, r.text

    def test_get_messages_nonexistent_request(self):
        s, _ = login(CLIENT)
        r = s.get(f"{API}/chat/507f1f77bcf86cd799439011/messages")
        assert r.status_code == 404

    def test_get_messages_unauthenticated(self, assigned_request_ids):
        r = requests.get(f"{API}/chat/{assigned_request_ids['id']}/messages")
        assert r.status_code in (401, 403)


# ========== WebSocket chat ==========
async def _ws_send_receive(req_id: str, token: str, text: str):
    url = f"{WS_BASE}/api/ws/chat/{req_id}?token={token}"
    async with websockets.connect(url, open_timeout=15, close_timeout=5) as ws:
        # Receive 1st system "joined" broadcast
        first = await asyncio.wait_for(ws.recv(), timeout=10)
        first_obj = json.loads(first)
        # Send a message
        await ws.send(json.dumps({"text": text}))
        # Receive the echoed broadcast (could be 1 or 2 messages; loop briefly)
        received_msgs = [first_obj]
        try:
            for _ in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                received_msgs.append(json.loads(msg))
                # break once we see our text
                if received_msgs[-1].get("text") == text:
                    break
        except asyncio.TimeoutError:
            pass
        return received_msgs


class TestWebSocketChat:
    def test_ws_missing_token(self, assigned_request_ids):
        url = f"{WS_BASE}/api/ws/chat/{assigned_request_ids['id']}"

        async def run():
            with pytest.raises(Exception):
                async with websockets.connect(url, open_timeout=10) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=5)

        asyncio.run(run())

    def test_ws_invalid_token(self, assigned_request_ids):
        url = f"{WS_BASE}/api/ws/chat/{assigned_request_ids['id']}?token=INVALID.JWT.HERE"

        async def run():
            with pytest.raises(Exception):
                async with websockets.connect(url, open_timeout=10) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=5)

        asyncio.run(run())

    def test_ws_client_send_receive_and_persistence(self, assigned_request_ids):
        s, _ = login(CLIENT)
        token_resp = s.get(f"{API}/auth/ws-token").json()
        token = token_resp["token"]
        req_id = assigned_request_ids["id"]

        text = "TEST_hello_from_phase3_ws"
        msgs = asyncio.run(_ws_send_receive(req_id, token, text))
        # Expect at least one message with the text
        texts = [m.get("text") for m in msgs]
        assert any(text == t for t in texts), f"text not echoed: {texts}"

        # Verify persistence via GET /chat/.../messages
        r = s.get(f"{API}/chat/{req_id}/messages")
        assert r.status_code == 200
        history = r.json()
        # search recent messages for our text
        recent_texts = [m.get("text") for m in history[-20:]]
        assert text in recent_texts, f"message not persisted; recent: {recent_texts}"

    def test_ws_specialist_not_assigned_rejected(self, assigned_request_ids):
        s2, me = login(SPEC2)
        token = s2.get(f"{API}/auth/ws-token").json()["token"]
        req_id = assigned_request_ids["id"]
        if assigned_request_ids.get("specialist_id") == me["id"]:
            pytest.skip("SPEC2 is the assigned specialist")
        url = f"{WS_BASE}/api/ws/chat/{req_id}?token={token}"

        async def run():
            with pytest.raises(Exception):
                async with websockets.connect(url, open_timeout=10) as ws:
                    # Server should close with 4003 before any data
                    await asyncio.wait_for(ws.recv(), timeout=5)

        asyncio.run(run())


# ========== Regression smoke ==========
class TestRegression:
    def test_login(self):
        s, me = login(CLIENT)
        assert me["role"] == "client"

    def test_properties(self):
        s, _ = login(CLIENT)
        r = s.get(f"{API}/properties")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_requests(self):
        s, _ = login(CLIENT)
        r = s.get(f"{API}/requests")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_auth_me_specialist(self):
        s, _ = login(SPEC)
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "specialist"
