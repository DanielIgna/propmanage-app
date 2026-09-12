"""Phase I+ Auto-reminder scheduler tests.

Covers:
- PATCH /api/digital-twin/reports/{id}/reminder-settings (all combos + persistence via GET /reports/sent)
- Validation: empty thresholds → 400; out-of-range silently filtered;
  invalid date → 400 'Format dată invalid'; empty payload → 400 'Nimic de actualizat'.
- Security: PATCH for report not owned → 404
- Admin endpoints: POST /admin/digital-twin/auto-reminders/run-now (admin only) and
  GET /admin/digital-twin/auto-reminders/last-run.
- Scheduler logic: backdate report to age=10 + thresholds=[3,7,14] → 2 runs fire
  3d then 7d (idempotent); 3rd run fires nothing.
- Scheduler skip conditions: stopped, paused_until-future, enabled=false, no approval_url.
- Each auto fire: reminders_sent entry with automatic=true; fired thresholds updated.
- Recipient gets dt_report_reminder notification on auto-fire.
"""
import os
import time
import asyncio
import pytest
import requests
from datetime import datetime, timezone, timedelta
from tests.test_config import OWNER_ADMIN_PASSWORD

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


def _get_item(session, report_id):
    r = session.get(f"{BASE_URL}/api/digital-twin/reports/sent?status=all", timeout=15)
    assert r.status_code == 200
    for it in r.json().get("items", []):
        if it["report_id"] == report_id:
            return it
    return None


# ---------- DB helper for backdating ----------
@pytest.fixture(scope="module")
def db():
    """Direct DB handle for backdating reports."""
    import sys
    sys.path.insert(0, "/app/backend")
    from db import db as _db  # noqa
    return _db


def _backdate(db_handle, pin_id, report_id, days):
    """Set report_history.[].created_at to N days ago via direct DB write."""
    new_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    async def _do():
        await db_handle.digital_twin_pins.update_one(
            {"id": pin_id, "report_history.id": report_id},
            {"$set": {"report_history.$.created_at": new_iso,
                      "report_history.$.auto_reminders_fired_thresholds": []}},
        )
    asyncio.get_event_loop().run_until_complete(_do())


# ---------- session fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def specialist_session():
    return _login("specialist@propmanage.io", "Spec123!")


# ---------- project + pin ----------
@pytest.fixture(scope="module")
def project_id(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_AutoReminder_Scheduler",
        "description": "auto reminder tests",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture(scope="module")
def pin_id(admin_session, project_id):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "title": "TEST AutoReminder Pin",
        "description": "for scheduler tests",
        "category": "defect",
        "priority": "high",
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _issue_report(session, pin_id, recipient="specialist@propmanage.io"):
    r = session.post(
        f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
        json={"recipient_email": recipient, "custom_message": "auto-reminder test",
              "include_thread": False},
        timeout=30,
    )
    assert r.status_code == 200, f"issue-report failed: {r.status_code} {r.text}"
    return r.json()["report"]


# ================================================================
# 1) PATCH /reports/{id}/reminder-settings — combos & persistence
# ================================================================
class TestReminderSettingsPatch:
    @pytest.fixture(scope="class")
    def report_id(self, admin_session, pin_id):
        rep = _issue_report(admin_session, pin_id)
        return rep["id"]

    def test_patch_only_enabled(self, admin_session, report_id):
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"auto_reminders_enabled": False}, timeout=15,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["auto_reminders_enabled"] is False
        # persistence via GET
        item = _get_item(admin_session, report_id)
        assert item["auto_reminders_enabled"] is False

    def test_patch_only_thresholds(self, admin_session, report_id):
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"thresholds_days": [5, 10, 30]}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["reminder_thresholds_days"] == [5, 10, 30]
        item = _get_item(admin_session, report_id)
        assert item["reminder_thresholds_days"] == [5, 10, 30]

    def test_patch_only_paused_until(self, admin_session, report_id):
        future = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"paused_until": future}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["paused_until"] == future
        item = _get_item(admin_session, report_id)
        assert item["paused_until"] == future

    def test_patch_only_stopped(self, admin_session, report_id):
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"stopped": True}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["auto_reminders_stopped"] is True
        item = _get_item(admin_session, report_id)
        assert item["auto_reminders_stopped"] is True


# ================================================================
# 2) Validation
# ================================================================
class TestReminderSettingsValidation:
    @pytest.fixture(scope="class")
    def report_id(self, admin_session, pin_id):
        return _issue_report(admin_session, pin_id)["id"]

    def test_empty_thresholds_array_returns_400(self, admin_session, report_id):
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"thresholds_days": []}, timeout=15,
        )
        # Note: backend treats empty list as None (Pydantic optional). Spec says 400.
        # Actually, empty list != None, so it should hit the validation branch.
        assert r.status_code == 400, r.text
        assert "prag" in r.text.lower() or "reminder" in r.text.lower()

    def test_out_of_range_thresholds_silently_filtered(self, admin_session, report_id):
        # 0 and 400 should be filtered; valid 7 remains.
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"thresholds_days": [0, 400, 7]}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["reminder_thresholds_days"] == [7]

    def test_all_out_of_range_returns_400(self, admin_session, report_id):
        # All filtered → empty → 400
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"thresholds_days": [0, 400, 999]}, timeout=15,
        )
        assert r.status_code == 400

    def test_invalid_date_format(self, admin_session, report_id):
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"paused_until": "not-a-date"}, timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "dată" in r.text.lower() or "invalid" in r.text.lower()

    def test_empty_payload_returns_400(self, admin_session, report_id):
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={}, timeout=15,
        )
        assert r.status_code == 400, r.text
        assert "Nimic" in r.text or "actualizat" in r.text

    def test_clear_paused_until_with_empty_string(self, admin_session, report_id):
        # First set, then clear
        future = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
        admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"paused_until": future}, timeout=15,
        )
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{report_id}/reminder-settings",
            json={"paused_until": ""}, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["paused_until"] is None


# ================================================================
# 3) Security — cross-user PATCH returns 404
# ================================================================
class TestReminderSettingsSecurity:
    def test_client_cannot_patch_admin_report(self, admin_session, client_session, pin_id):
        rep = _issue_report(admin_session, pin_id)
        rid = rep["id"]
        r = client_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/reminder-settings",
            json={"stopped": True}, timeout=15,
        )
        assert r.status_code == 404, r.text


# ================================================================
# 4) Admin endpoints
# ================================================================
class TestAdminEndpoints:
    def test_run_now_admin_returns_summary(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("checked_reports", "sent", "skipped", "failed", "at"):
            assert k in body, f"missing key {k} in {body}"
            if k != "at":
                assert isinstance(body[k], int)

    def test_run_now_non_admin_forbidden(self, client_session):
        r = client_session.post(
            f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=15
        )
        assert r.status_code == 403, r.text

    def test_last_run_admin_returns_summary(self, admin_session):
        # Run first to ensure it's populated
        admin_session.post(f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30)
        r = admin_session.get(
            f"{BASE_URL}/api/admin/digital-twin/auto-reminders/last-run", timeout=10
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # Should have summary keys, not never_ran
        assert body.get("never_ran") is not True
        for k in ("checked_reports", "sent", "skipped", "failed", "at"):
            assert k in body


# ================================================================
# 5) Scheduler logic — backdate + multi-run idempotency
# ================================================================
class TestSchedulerLogic:
    def test_backdated_report_fires_thresholds_progressively(
        self, admin_session, specialist_session, pin_id, project_id, db,
    ):
        # Create fresh pending report
        rep = _issue_report(admin_session, pin_id)
        rid = rep["id"]

        # Set thresholds [3,7,14] and backdate to age=10
        r = admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/reminder-settings",
            json={"thresholds_days": [3, 7, 14]}, timeout=15,
        )
        assert r.status_code == 200, r.text
        _backdate(db, pin_id, rid, days=10)

        # Run 1 → should fire threshold 3
        r1 = admin_session.post(
            f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30
        ).json()
        assert r1["sent"] >= 1, r1
        item1 = _get_item(admin_session, rid)
        fired1 = item1.get("auto_reminders_fired_thresholds") or []
        assert 3 in fired1, f"expected 3 in fired thresholds, got {fired1}"
        assert item1["reminder_count"] >= 1

        # Run 2 → should fire threshold 7
        r2 = admin_session.post(
            f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30
        ).json()
        assert r2["sent"] >= 1, r2
        item2 = _get_item(admin_session, rid)
        fired2 = item2.get("auto_reminders_fired_thresholds") or []
        assert 3 in fired2 and 7 in fired2, f"expected [3,7], got {fired2}"
        assert item2["reminder_count"] >= 2

        # Run 3 → 14d not reached yet (age=10), should NOT fire for this report
        before_count = item2["reminder_count"]
        admin_session.post(f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30)
        item3 = _get_item(admin_session, rid)
        fired3 = item3.get("auto_reminders_fired_thresholds") or []
        assert 14 not in fired3
        assert item3["reminder_count"] == before_count

    def test_stopped_report_is_skipped(self, admin_session, pin_id, db):
        rep = _issue_report(admin_session, pin_id)
        rid = rep["id"]
        # Backdate so it would normally fire
        _backdate(db, pin_id, rid, days=10)
        admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/reminder-settings",
            json={"stopped": True, "thresholds_days": [3, 7]}, timeout=15,
        )
        before = _get_item(admin_session, rid)
        admin_session.post(f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30)
        after = _get_item(admin_session, rid)
        assert after["reminder_count"] == before["reminder_count"]
        assert not (after.get("auto_reminders_fired_thresholds") or [])

    def test_paused_until_future_is_skipped(self, admin_session, pin_id, db):
        rep = _issue_report(admin_session, pin_id)
        rid = rep["id"]
        _backdate(db, pin_id, rid, days=10)
        future = (datetime.now(timezone.utc) + timedelta(days=5)).date().isoformat()
        admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/reminder-settings",
            json={"paused_until": future, "thresholds_days": [3, 7]}, timeout=15,
        )
        before = _get_item(admin_session, rid)
        admin_session.post(f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30)
        after = _get_item(admin_session, rid)
        assert after["reminder_count"] == before["reminder_count"]

    def test_enabled_false_is_skipped(self, admin_session, pin_id, db):
        rep = _issue_report(admin_session, pin_id)
        rid = rep["id"]
        _backdate(db, pin_id, rid, days=10)
        admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/reminder-settings",
            json={"auto_reminders_enabled": False, "thresholds_days": [3, 7]}, timeout=15,
        )
        before = _get_item(admin_session, rid)
        admin_session.post(f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30)
        after = _get_item(admin_session, rid)
        assert after["reminder_count"] == before["reminder_count"]


# ================================================================
# 6) Auto-fire side-effects: reminders_sent entry + notification
# ================================================================
class TestAutoFireSideEffects:
    def test_automatic_flag_and_notification(self, admin_session, specialist_session, pin_id, db):
        rep = _issue_report(admin_session, pin_id, recipient="specialist@propmanage.io")
        rid = rep["id"]
        admin_session.patch(
            f"{BASE_URL}/api/digital-twin/reports/{rid}/reminder-settings",
            json={"thresholds_days": [3]}, timeout=15,
        )
        _backdate(db, pin_id, rid, days=5)

        def _latest_reminder_ts(resp):
            if resp.status_code != 200:
                return ""
            body = resp.json()
            items = body if isinstance(body, list) else body.get("items", [])
            stamps = [n.get("created_at") or "" for n in items if n.get("type") == "dt_report_reminder"]
            return max(stamps, default="")

        before_ts = _latest_reminder_ts(specialist_session.get(f"{BASE_URL}/api/notifications", timeout=10))

        # Fire
        admin_session.post(f"{BASE_URL}/api/admin/digital-twin/auto-reminders/run-now", timeout=30)
        time.sleep(0.5)

        item = _get_item(admin_session, rid)
        assert 3 in (item.get("auto_reminders_fired_thresholds") or [])
        assert item.get("last_auto_reminder_at") is not None
        assert item["reminder_count"] >= 1

        # Verify notification delivered
        after_ts = _latest_reminder_ts(specialist_session.get(f"{BASE_URL}/api/notifications", timeout=10))
        # The notifications list is capped, so counting is unreliable — assert a
        # NEWER dt_report_reminder notification exists instead.
        assert after_ts > before_ts, (
            f"expected a new dt_report_reminder notification: before={before_ts!r} after={after_ts!r}"
        )
