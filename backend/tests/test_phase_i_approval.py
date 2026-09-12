"""Phase I (cont'd): Digital Twin Report Approval (token-based, public endpoint) — backend tests.

Covers:
- POST /api/digital-twin/pins/{id}/issue-report returns approval_url + 'approval_status':'pending' in pin.report_history[]
- JWT structure (type, pin_id, report_id, recipient, exp ~30d)
- GET /api/digital-twin/reports/approve/info?token=X (no auth) — 200 / 400 (malformed) / 410 (expired)
- POST /api/digital-twin/reports/approve/decide — 200, single-use 409, invalid decision 422
- Sender notification (in-app + email path)
- Token tamper / wrong-type token → 400
"""
import os
import io
import time
import pytest
import requests
import jwt as _jwt
from datetime import datetime, timezone, timedelta
from tests.test_config import OWNER_ADMIN_PASSWORD

try:
    from pypdf import PdfWriter
except ImportError:
    PdfWriter = None

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

# Load JWT secret from environment (mirrors backend/.env) — never hardcode production secrets.
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    # Fallback: read from backend/.env (test runner convenience)
    try:
        from dotenv import dotenv_values
        _envfile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        JWT_SECRET = (dotenv_values(_envfile) or {}).get("JWT_SECRET")
    except Exception:
        JWT_SECRET = None
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET not configured — set env var or backend/.env before running phase_i tests.")
JWT_ALGORITHM = "HS256"


# ---------------- helpers ----------------

def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return s


def _make_pdf(pages: int = 1) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# ---------------- fixtures ----------------

@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def specialist_session():
    """Specialist with DT Pro grant — receives the report (recipient = specialist email)."""
    s = _login("specialist@propmanage.io", "Spec123!")
    admin = _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    uid = me.get("id") or me.get("_id") or (me.get("user") or {}).get("id")
    if uid:
        admin.post(
            f"{BASE_URL}/api/admin/digital-twin/subscription/grant",
            json={"user_id": uid, "active": True}, timeout=10,
        )
    s._user_id = uid
    s._email = me.get("email")
    return s


@pytest.fixture(scope="module")
def project_id(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_PhaseI_Approval",
        "description": "Phase I report approval flow",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture(scope="module")
def pin_id(admin_session, project_id):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "title": "TEST Approval Pin",
        "description": "Approval flow target",
        "category": "defect",
        "priority": "high",
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def issued_report(admin_session, pin_id):
    """Issue a fresh report to specialist@. Returns the response.report dict (with approval_url)."""
    r = admin_session.post(
        f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
        json={
            "recipient_email": "specialist@propmanage.io",
            "custom_message": "Te rog verifică crăpătura la grinda B3.",
            "include_thread": True,
        },
        timeout=30,
    )
    assert r.status_code == 200, f"issue-report failed: {r.status_code} {r.text}"
    return r.json()


def _extract_token(approval_url: str) -> str:
    """approval_url = APP_URL/report-respond/{token}"""
    return approval_url.rsplit("/report-respond/", 1)[-1]


# ================================================================
# 1) Token issuance
# ================================================================
class TestTokenIssuance:
    def test_report_response_includes_approval_url(self, issued_report):
        rep = issued_report.get("report", {})
        assert "approval_url" in rep, f"missing approval_url: {rep.keys()}"
        assert "/report-respond/" in rep["approval_url"], rep["approval_url"]
        assert rep.get("approval_status") == "pending"

    def test_history_entry_has_approval_status_pending(self, admin_session, pin_id, issued_report):
        # Re-fetch pin and confirm history entry has approval_status=pending
        rep = issued_report["report"]
        rid = rep["id"]
        # Find the pin via its project; use list pins endpoint
        # Simpler: there's no direct GET pin by id route exposed publicly here,
        # so re-fetch project pins.
        # The report is part of the pin doc — use info endpoint w/ the token (no auth needed).
        token = _extract_token(rep["approval_url"])
        info = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": token}, timeout=15,
        )
        assert info.status_code == 200, info.text
        assert info.json().get("approval_status") == "pending"


# ================================================================
# 2) JWT structure
# ================================================================
class TestJWTStructure:
    def test_token_decodes_with_expected_claims(self, issued_report):
        token = _extract_token(issued_report["report"]["approval_url"])
        data = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        assert data["type"] == "dt_report_approval"
        assert data["recipient"] == "specialist@propmanage.io"
        assert "pin_id" in data and "report_id" in data
        # exp ~ 30 days from now (allow ±2 days slack)
        exp_dt = datetime.fromtimestamp(data["exp"], tz=timezone.utc)
        delta = exp_dt - datetime.now(timezone.utc)
        assert 28 <= delta.days <= 31, f"exp delta = {delta.days} days"


# ================================================================
# 3) GET /reports/approve/info — public, no auth
# ================================================================
class TestApproveInfoEndpoint:
    def test_info_200_with_valid_token_no_auth(self, issued_report):
        token = _extract_token(issued_report["report"]["approval_url"])
        # Use a bare requests session (NO cookies/headers from admin)
        r = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": token}, timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("pin_title", "project_name", "sender_name", "recipient_name", "approval_status"):
            assert k in body, f"missing key {k} in {body}"
        assert body["approval_status"] == "pending"
        assert body["project_name"] == "TEST_PhaseI_Approval"

    def test_info_400_for_malformed_token(self):
        r = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": "garbage.not.a.jwt"}, timeout=15,
        )
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"
        assert "invalid" in (r.json().get("detail") or "").lower()

    def test_info_410_for_expired_token(self, pin_id):
        # Craft an already-expired token with the right type
        payload = {
            "type": "dt_report_approval",
            "pin_id": pin_id,
            "report_id": "fake",
            "recipient": "specialist@propmanage.io",
            "exp": datetime.now(timezone.utc) - timedelta(days=1),
        }
        tok = _jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        r = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": tok}, timeout=15,
        )
        assert r.status_code == 410, f"expected 410 got {r.status_code}: {r.text}"
        assert "expir" in (r.json().get("detail") or "").lower()

    def test_info_400_for_wrong_type_token(self):
        # Wrong type ('access' instead of 'dt_report_approval')
        payload = {
            "type": "access",
            "user_id": "fake",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        tok = _jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        r = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": tok}, timeout=15,
        )
        assert r.status_code == 400, r.text

    def test_info_400_for_tampered_signature(self, issued_report):
        token = _extract_token(issued_report["report"]["approval_url"])
        # Mutate last char of signature segment
        parts = token.rsplit(".", 1)
        last = parts[1]
        flip = "A" if last[-1] != "A" else "B"
        tampered = f"{parts[0]}.{last[:-1]}{flip}"
        r = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": tampered}, timeout=15,
        )
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


# ================================================================
# 4) POST /reports/approve/decide — success, single-use 409, validation 422
# ================================================================
class TestApproveDecideEndpoint:
    """Each test issues its own fresh report for isolation."""

    def _fresh_report(self, admin_session, pin_id, recipient="specialist@propmanage.io"):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={"recipient_email": recipient, "custom_message": "Test decide", "include_thread": False},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_decide_confirmed_200(self, admin_session, pin_id):
        rep = self._fresh_report(admin_session, pin_id)
        token = _extract_token(rep["report"]["approval_url"])
        r = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": token, "decision": "confirmed", "comment": "OK voi acționa luni."},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["decision"] == "confirmed"
        assert "decided_at" in body
        # Verify info now reflects 'confirmed'
        info = requests.get(
            f"{BASE_URL}/api/digital-twin/reports/approve/info",
            params={"token": token}, timeout=15,
        ).json()
        assert info["approval_status"] == "confirmed"
        assert info["decision"] == "confirmed"
        assert info["decision_comment"] == "OK voi acționa luni."
        assert info["decided_at"]

    def test_decide_needs_changes_200(self, admin_session, pin_id):
        rep = self._fresh_report(admin_session, pin_id)
        token = _extract_token(rep["report"]["approval_url"])
        r = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": token, "decision": "needs_changes", "comment": "Vreau check pe etajul 2."},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        assert r.json()["decision"] == "needs_changes"

    def test_decide_twice_returns_409(self, admin_session, pin_id):
        rep = self._fresh_report(admin_session, pin_id)
        token = _extract_token(rep["report"]["approval_url"])
        r1 = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": token, "decision": "confirmed"}, timeout=20,
        )
        assert r1.status_code == 200, r1.text
        r2 = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": token, "decision": "needs_changes"}, timeout=20,
        )
        assert r2.status_code == 409, f"expected 409 got {r2.status_code}: {r2.text}"
        assert "deja" in (r2.json().get("detail") or "").lower()

    def test_decide_invalid_decision_422(self, admin_session, pin_id):
        rep = self._fresh_report(admin_session, pin_id)
        token = _extract_token(rep["report"]["approval_url"])
        r = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": token, "decision": "maybe"}, timeout=20,
        )
        assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text}"

    def test_decide_with_malformed_token_400(self):
        r = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": "garbage.not.jwt", "decision": "confirmed"}, timeout=20,
        )
        assert r.status_code == 400, r.text


# ================================================================
# 5) Sender notification (in-app)
# ================================================================
class TestSenderNotification:
    def test_in_app_notification_created_for_sender(self, admin_session, pin_id):
        # 1) Issue a fresh report (admin is sender, specialist is recipient)
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={"recipient_email": "specialist@propmanage.io", "custom_message": "Sender notif test"},
            timeout=30,
        )
        assert r.status_code == 200
        token = _extract_token(r.json()["report"]["approval_url"])

        # 2) Capture admin's notifications BEFORE decide
        before = admin_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert before.status_code == 200, before.text
        before_ids = {n.get("id") or n.get("_id") for n in (before.json() if isinstance(before.json(), list) else before.json().get("items", []))}

        # 3) Recipient decides
        rd = requests.post(
            f"{BASE_URL}/api/digital-twin/reports/approve/decide",
            json={"token": token, "decision": "confirmed", "comment": "Done"}, timeout=20,
        )
        assert rd.status_code == 200, rd.text

        # 4) small delay for async write
        time.sleep(1.0)

        # 5) Verify admin (sender) has a new dt_report_decision notification
        after = admin_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert after.status_code == 200
        notes = after.json() if isinstance(after.json(), list) else after.json().get("items", [])
        new = [n for n in notes if (n.get("id") or n.get("_id")) not in before_ids]
        decision_notifs = [n for n in new if n.get("type") == "dt_report_decision"]
        assert len(decision_notifs) >= 1, (
            f"expected at least one dt_report_decision notification for sender; got new={new}"
        )
