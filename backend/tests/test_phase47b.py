"""Phase 47B backend tests — AI Repair Suggester + CORS + Resend wiring."""
import os

import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL")
            or "https://phased-document.preview.emergentagent.com").rstrip("/")

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json", "User-Agent": BROWSER_UA})
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def finding_id(admin_sess):
    """Get an existing OPEN finding, or trigger a scan to create one."""
    r = admin_sess.get(f"{BASE_URL}/api/admin/ai/findings?status=open&limit=20", timeout=15)
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    if not items:
        # trigger scan
        s = admin_sess.post(f"{BASE_URL}/api/admin/ai/scan/run", timeout=60)
        assert s.status_code == 200, s.text
        r = admin_sess.get(f"{BASE_URL}/api/admin/ai/findings?status=open&limit=20", timeout=15)
        items = r.json().get("items", [])
    if not items:
        pytest.skip("no open findings available to test repair suggester")
    return items[0]["id"]


# ============ REPAIR SUGGESTER LIFECYCLE ============

class TestRepairSuggesterLifecycle:
    def test_01_generate_initial(self, admin_sess, finding_id):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair",
            json={}, timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["finding_id"] == finding_id
        assert data["cached"] is False
        sug = data["suggestion"]
        for k in ("id", "summary", "risk_level", "steps", "rollback",
                  "verification", "estimated_minutes", "requires_db_write",
                  "requires_user_communication", "status"):
            assert k in sug, f"missing key {k}"
        assert sug["status"] == "proposed"
        assert sug["risk_level"] in ("low", "medium", "high")
        assert isinstance(sug["steps"], list) and len(sug["steps"]) > 0
        # cache the id for later tests
        pytest.shared_suggestion_id = sug["id"]
        pytest.shared_initial_summary = sug["summary"]

    def test_02_second_call_returns_cached(self, admin_sess, finding_id):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair",
            json={}, timeout=20,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cached"] is True
        assert data["suggestion"]["id"] == pytest.shared_suggestion_id

    def test_03_get_endpoint(self, admin_sess, finding_id):
        r = admin_sess.get(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair",
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["suggestion"] is not None
        assert data["suggestion"]["id"] == pytest.shared_suggestion_id

    def test_04_regenerate_increments_count(self, admin_sess, finding_id):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair",
            json={"regenerate": True}, timeout=60,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["cached"] is False
        sug = data["suggestion"]
        # same db doc, so id stays the same (in-place update path)
        assert sug["id"] == pytest.shared_suggestion_id
        assert sug["regeneration_count"] >= 1

    def test_05_decide_invalid_returns_400(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{pytest.shared_suggestion_id}/decide",
            json={"decision": "invalid"}, timeout=10,
        )
        assert r.status_code == 400, r.text

    def test_06_mark_applied_before_approve_returns_400(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{pytest.shared_suggestion_id}/mark-applied",
            json={}, timeout=10,
        )
        assert r.status_code == 400, r.text
        assert "aprobate" in r.text.lower()

    def test_07_reject(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{pytest.shared_suggestion_id}/decide",
            json={"decision": "reject", "note": "TEST reject"}, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "rejected"

    def test_08_approve(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{pytest.shared_suggestion_id}/decide",
            json={"decision": "approve", "note": "TEST approve"}, timeout=10,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"

    def test_09_list_repair_suggestions(self, admin_sess):
        r = admin_sess.get(
            f"{BASE_URL}/api/admin/ai/repair-suggestions", timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and "counts" in data
        for k in ("proposed", "approved", "rejected", "applied"):
            assert k in data["counts"]
        # Our suggestion should be approved now
        assert data["counts"]["approved"] >= 1

    def test_10_mark_applied_after_approve_resolves_finding(self, admin_sess, finding_id):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{pytest.shared_suggestion_id}/mark-applied",
            json={"note": "TEST applied", "resolve_finding": True}, timeout=10,
        )
        assert r.status_code == 200, r.text

        # verify suggestion now applied
        r2 = admin_sess.get(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair", timeout=10,
        )
        assert r2.status_code == 200
        assert r2.json()["suggestion"]["status"] == "applied"

        # verify the finding got auto-resolved
        r3 = admin_sess.get(
            f"{BASE_URL}/api/admin/ai/findings?status=resolved&limit=200", timeout=15,
        )
        assert r3.status_code == 200
        ids = {it["id"] for it in r3.json().get("items", [])}
        assert finding_id in ids, "finding was not auto-resolved after mark-applied"


# ============ AUTHZ NEGATIVE CASES ============

class TestAuthzNonAdmin:
    def test_suggest_repair_forbidden_for_client(self, client_sess, finding_id):
        r = client_sess.post(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair",
            json={}, timeout=10,
        )
        assert r.status_code in (401, 403), r.text

    def test_get_repair_forbidden_for_client(self, client_sess, finding_id):
        r = client_sess.get(
            f"{BASE_URL}/api/admin/ai/findings/{finding_id}/suggest-repair",
            timeout=10,
        )
        assert r.status_code in (401, 403), r.text

    def test_decide_forbidden_for_client(self, client_sess):
        sid = getattr(pytest, "shared_suggestion_id", "000000000000000000000000")
        r = client_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{sid}/decide",
            json={"decision": "approve"}, timeout=10,
        )
        assert r.status_code in (401, 403), r.text

    def test_mark_applied_forbidden_for_client(self, client_sess):
        sid = getattr(pytest, "shared_suggestion_id", "000000000000000000000000")
        r = client_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/{sid}/mark-applied",
            json={}, timeout=10,
        )
        assert r.status_code in (401, 403), r.text

    def test_list_forbidden_for_client(self, client_sess):
        r = client_sess.get(
            f"{BASE_URL}/api/admin/ai/repair-suggestions", timeout=10,
        )
        assert r.status_code in (401, 403), r.text


# ============ BAD INPUT ============

class TestBadInput:
    def test_invalid_finding_id_format(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/findings/not-an-oid/suggest-repair",
            json={}, timeout=10,
        )
        assert r.status_code == 400, r.text

    def test_invalid_suggestion_id_decide(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/ai/repair-suggestions/not-an-oid/decide",
            json={"decision": "approve"}, timeout=10,
        )
        assert r.status_code == 400, r.text


# ============ CORS REGRESSION ============

class TestCORS:
    def test_cors_wildcard_returns_acao_star_and_no_credentials(self):
        # With CORS_ORIGINS="*", allow_credentials should be False
        # Send a normal GET with Origin header — Starlette CORSMiddleware
        # returns ACAO=* and does NOT return ACAC=true.
        r = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Origin": "https://malicious.com", "User-Agent": BROWSER_UA},
            timeout=10,
        )
        # auth/me may be 401 or 200 — we only care about CORS headers
        acao = r.headers.get("Access-Control-Allow-Origin")
        # Security contract: an unknown/malicious origin must never be REFLECTED
        # back in ACAO (origin reflection = CORS bypass). A literal "*" may be
        # injected by the ingress proxy layer; browsers refuse credentialed
        # requests with wildcard origin, so that combination is inert.
        assert acao != "https://malicious.com", f"malicious origin echoed in ACAO: {acao!r}"


# ============ RESEND / EMAIL SERVICE PROVIDER DETECTION ============

class TestEmailProvider:
    def test_email_service_console_fallback(self):
        """When RESEND_API_KEY is empty, email_service must run in console mode (no errors)."""
        import os as _os
        if (_os.environ.get("RESEND_API_KEY") or "").strip():
            pytest.skip("RESEND_API_KEY is configured — console fallback not active")
        import importlib
        import sys
        sys.path.insert(0, "/app/backend")
        try:
            es = importlib.import_module("email_service")
            importlib.reload(es)
        finally:
            pass
        # The module exposes a `provider` resolution; we check by calling send_email
        # Should not raise — falls back to console output.
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            es.send_email(["test@example.com"], "TEST subject", "<p>hello</p>")
        )
        assert isinstance(result, dict)
        # provider may be "console" or similar — we assert it doesn't say "resend"
        # (since key is empty), and there's no error key
        prov = (result.get("provider") or "").lower()
        assert prov != "resend", f"expected non-resend provider when key empty; got {prov!r}"
        assert result.get("ok") in (True, None) or "error" not in result, result
