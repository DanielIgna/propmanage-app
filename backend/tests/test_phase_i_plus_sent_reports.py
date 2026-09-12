"""Phase I+ — Sent Reports Dashboard + Reminder endpoints.

Covers:
- GET /api/digital-twin/reports/sent (no filter, +counters)
- Filters: status=pending|confirmed|needs_changes|all and overdue_only=true
- Sender scoping (client sees only its own reports)
- POST /api/digital-twin/reports/{report_id}/remind happy path
  - returns reminder object with required keys
  - reminders_sent appended (reminder_count++ in subsequent GET)
- 409 for non-pending report
- 404 for report not owned by current user
- 400 for note > 1000 chars
- In-app notification of type 'dt_report_reminder' delivered to recipient (if known user)
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

try:
    from pypdf import PdfWriter
except ImportError:
    PdfWriter = None

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://phased-document.preview.emergentagent.com",
).rstrip("/")


# ---------- helpers ----------
def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return s


def _extract_token(url):
    return url.rsplit("/report-respond/", 1)[-1]


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def specialist_session():
    """Specialist (recipient of admin's reports). Needed for notification check."""
    s = _login("specialist@propmanage.io", "Spec123!")
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    s._email = me.get("email")
    return s


@pytest.fixture(scope="module")
def project_id(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_PhaseIplus_SentReports",
        "description": "Sent reports dashboard tests",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture(scope="module")
def pin_id(admin_session, project_id):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "title": "TEST SentReports Pin",
        "description": "for sent reports dashboard tests",
        "category": "defect",
        "priority": "high",
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _issue(session, pin_id, recipient="specialist@propmanage.io", msg="m"):
    r = session.post(
        f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
        json={"recipient_email": recipient, "custom_message": msg, "include_thread": False},
        timeout=30,
    )
    assert r.status_code == 200, f"issue-report failed: {r.status_code} {r.text}"
    return r.json()


def _decide(token, decision, comment="ok"):
    r = requests.post(
        f"{BASE_URL}/api/digital-twin/reports/approve/decide",
        json={"token": token, "decision": decision, "comment": comment},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def fresh_report_ids(admin_session, pin_id):
    """Create 3 fresh reports for admin: one pending, one confirmed, one needs_changes."""
    pending = _issue(admin_session, pin_id, msg="pending-r")
    confirmed = _issue(admin_session, pin_id, msg="confirmed-r")
    nc = _issue(admin_session, pin_id, msg="nc-r")

    _decide(_extract_token(confirmed["report"]["approval_url"]), "confirmed", "OK")
    _decide(_extract_token(nc["report"]["approval_url"]), "needs_changes", "schimbă")

    time.sleep(0.5)
    return {
        "pending_id": pending["report"]["id"],
        "confirmed_id": confirmed["report"]["id"],
        "nc_id": nc["report"]["id"],
    }


# ================================================================
# 1) GET /reports/sent — basic
# ================================================================
class TestSentReportsList:
    def test_list_returns_items_and_counters(self, admin_session, fresh_report_ids):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and isinstance(body["items"], list)
        assert "counters" in body
        for k in ("total", "pending", "confirmed", "needs_changes", "overdue"):
            assert k in body["counters"], f"missing counter {k}"
            assert isinstance(body["counters"][k], int)
        # Items belonging to our 3 fresh reports must be present
        ids = {i["report_id"] for i in body["items"]}
        for k in ("pending_id", "confirmed_id", "nc_id"):
            assert fresh_report_ids[k] in ids, f"{k}={fresh_report_ids[k]} not in {ids}"

    def test_item_shape(self, admin_session, fresh_report_ids):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent", timeout=15)
        body = r.json()
        item = next(i for i in body["items"] if i["report_id"] == fresh_report_ids["pending_id"])
        for k in (
            "report_id", "pin_id", "pin_title", "project_name", "recipient_email",
            "approval_status", "age_days", "is_overdue", "reminder_count", "approval_url",
        ):
            assert k in item, f"missing key {k} in item {item.keys()}"
        assert item["approval_status"] == "pending"
        assert item["is_overdue"] is False  # just created
        assert isinstance(item["age_days"], int) and item["age_days"] >= 0
        assert item["reminder_count"] == 0
        assert "/report-respond/" in (item["approval_url"] or "")
        assert item["project_name"] == "TEST_PhaseIplus_SentReports"


# ================================================================
# 2) Filters
# ================================================================
class TestSentReportsFilters:
    def test_filter_status_pending(self, admin_session, fresh_report_ids):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=pending", timeout=15)
        assert r.status_code == 200
        body = r.json()
        for i in body["items"]:
            assert i["approval_status"] == "pending", i
        assert fresh_report_ids["pending_id"] in {i["report_id"] for i in body["items"]}

    def test_filter_status_confirmed(self, admin_session, fresh_report_ids):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=confirmed", timeout=15)
        assert r.status_code == 200
        body = r.json()
        for i in body["items"]:
            assert i["approval_status"] == "confirmed", i
        assert fresh_report_ids["confirmed_id"] in {i["report_id"] for i in body["items"]}

    def test_filter_status_needs_changes(self, admin_session, fresh_report_ids):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=needs_changes", timeout=15)
        assert r.status_code == 200
        for i in r.json()["items"]:
            assert i["approval_status"] == "needs_changes", i

    def test_filter_status_all(self, admin_session, fresh_report_ids):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=all", timeout=15)
        assert r.status_code == 200
        body = r.json()
        statuses = {i["approval_status"] for i in body["items"]}
        # Should contain at least pending + the resolved ones
        assert "pending" in statuses
        assert "confirmed" in statuses or "needs_changes" in statuses

    def test_filter_overdue_only(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?overdue_only=true", timeout=15)
        assert r.status_code == 200
        body = r.json()
        for i in body["items"]:
            assert i["is_overdue"] is True
            assert i["approval_status"] == "pending"
            assert i["age_days"] >= 7


# ================================================================
# 3) Sender scoping — client only sees its own reports
# ================================================================
class TestSenderScoping:
    def test_client_does_not_see_admin_reports(self, client_session, fresh_report_ids):
        r = client_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=all", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        ids = {i["report_id"] for i in body["items"]}
        for k in ("pending_id", "confirmed_id", "nc_id"):
            assert fresh_report_ids[k] not in ids, (
                f"client must not see admin report {k}={fresh_report_ids[k]}"
            )


# ================================================================
# 4) Reminder endpoint — success
# ================================================================
class TestReminderSuccess:
    def test_remind_pending_returns_reminder_and_increments_counter(self, admin_session, fresh_report_ids):
        rid = fresh_report_ids["pending_id"]

        # Capture initial reminder_count
        r0 = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=pending", timeout=15)
        item0 = next(i for i in r0.json()["items"] if i["report_id"] == rid)
        before = item0["reminder_count"]

        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/remind",
            json={"note": "Te rog, e urgent."},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        rem = body.get("reminder") or {}
        for k in ("id", "sent_at", "sent_by", "note", "days_pending_at_send"):
            assert k in rem, f"missing key {k} in reminder {rem}"
        assert rem["note"] == "Te rog, e urgent."

        # Verify list reflects incremented reminder_count
        r2 = admin_session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=pending", timeout=15)
        item2 = next(i for i in r2.json()["items"] if i["report_id"] == rid)
        assert item2["reminder_count"] == before + 1, f"expected {before+1} got {item2['reminder_count']}"


# ================================================================
# 5) Reminder endpoint — errors
# ================================================================
class TestReminderErrors:
    def test_remind_confirmed_returns_409(self, admin_session, fresh_report_ids):
        rid = fresh_report_ids["confirmed_id"]
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/remind",
            json={"note": "n/a"}, timeout=20,
        )
        assert r.status_code == 409, f"expected 409 got {r.status_code}: {r.text}"
        assert "deja" in (r.json().get("detail") or "").lower()

    def test_remind_needs_changes_returns_409(self, admin_session, fresh_report_ids):
        rid = fresh_report_ids["nc_id"]
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/remind",
            json={}, timeout=20,
        )
        assert r.status_code == 409, f"expected 409 got {r.status_code}: {r.text}"

    def test_remind_not_owner_returns_404(self, client_session, fresh_report_ids):
        """client@ is NOT the sender of admin's pending report → 404."""
        rid = fresh_report_ids["pending_id"]
        r = client_session.post(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/remind",
            json={"note": "hacker"}, timeout=20,
        )
        assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text}"
        assert "expeditorul" in (r.json().get("detail") or "").lower() or "inexistent" in (r.json().get("detail") or "").lower()

    def test_remind_note_too_long_returns_400(self, admin_session, fresh_report_ids):
        rid = fresh_report_ids["pending_id"]
        long_note = "x" * 1001
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/remind",
            json={"note": long_note}, timeout=20,
        )
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


# ================================================================
# 6) In-app notification for recipient
# ================================================================
class TestRecipientNotification:
    def test_recipient_receives_dt_report_reminder_notification(self, admin_session, specialist_session, fresh_report_ids):
        rid = fresh_report_ids["pending_id"]

        # Capture specialist notifications before
        b = specialist_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert b.status_code == 200, b.text
        before_payload = b.json()
        before = before_payload if isinstance(before_payload, list) else before_payload.get("items", [])
        before_ids = {n.get("id") or n.get("_id") for n in before}

        # Send reminder
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/remind",
            json={"note": "notif test"}, timeout=20,
        )
        assert r.status_code == 200, r.text

        time.sleep(1.0)

        a = specialist_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        assert a.status_code == 200
        after_payload = a.json()
        after = after_payload if isinstance(after_payload, list) else after_payload.get("items", [])
        new = [n for n in after if (n.get("id") or n.get("_id")) not in before_ids]
        reminders = [n for n in new if n.get("type") == "dt_report_reminder"]
        assert len(reminders) >= 1, f"expected at least one dt_report_reminder notification; new={new}"
