"""Phase 78 — Weekly AI Briefing tests.

Covers: auth gates, config GET/PUT (incl. invalid-email filter + 400 on non-list),
send-now (empty config skip, override, force), history list, scheduled job direct invocation
(disabled skip + enabled execution path), and regression checks on neighboring admin endpoints.
"""
import os
import asyncio
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


# ---------- fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=CLIENT, timeout=15)
    assert r.status_code == 200, f"client login failed: {r.status_code} {r.text}"
    return s


# ---------- AuthZ ----------
class TestAuth:
    def test_anon_get_config_401(self):
        r = requests.get(f"{API}/admin/ai-weekly-briefing/config", timeout=10)
        assert r.status_code in (401, 403)

    def test_client_get_config_403(self, client_session):
        r = client_session.get(f"{API}/admin/ai-weekly-briefing/config", timeout=10)
        assert r.status_code == 403

    def test_admin_get_config_200(self, admin_session):
        r = admin_session.get(f"{API}/admin/ai-weekly-briefing/config", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "enabled" in d and "recipients" in d
        assert isinstance(d["recipients"], list)


# ---------- Config PUT ----------
class TestConfigPut:
    def test_put_persists_enabled_and_recipients(self, admin_session):
        payload = {"enabled": True, "recipients": ["admin@propmanage.io"]}
        r = admin_session.put(f"{API}/admin/ai-weekly-briefing/config", json=payload, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["enabled"] is True
        assert "admin@propmanage.io" in d["recipients"]
        # verify persistence via GET
        g = admin_session.get(f"{API}/admin/ai-weekly-briefing/config", timeout=10).json()
        assert g["enabled"] is True
        assert "admin@propmanage.io" in g["recipients"]

    def test_invalid_emails_filtered(self, admin_session):
        payload = {"recipients": ["good@x.com", "no-at-sign", "no-dot@nope", "ok2@a.b"]}
        r = admin_session.put(f"{API}/admin/ai-weekly-briefing/config", json=payload, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert set(d["recipients"]) == {"good@x.com", "ok2@a.b"}, d["recipients"]

    def test_non_list_recipients_400(self, admin_session):
        r = admin_session.put(
            f"{API}/admin/ai-weekly-briefing/config",
            json={"recipients": "admin@propmanage.io"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_restore_recipients(self, admin_session):
        # restore recipient for downstream send-now tests
        r = admin_session.put(
            f"{API}/admin/ai-weekly-briefing/config",
            json={"enabled": True, "recipients": ["admin@propmanage.io"]},
            timeout=10,
        )
        assert r.status_code == 200
        assert "admin@propmanage.io" in r.json()["recipients"]


# ---------- Send Now ----------
class TestSendNow:
    def test_no_recipients_skipped(self, admin_session):
        # temporarily clear recipients
        admin_session.put(
            f"{API}/admin/ai-weekly-briefing/config",
            json={"recipients": []},
            timeout=10,
        )
        r = admin_session.post(
            f"{API}/admin/ai-weekly-briefing/send-now", json={}, timeout=30
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("skipped") == "no_recipients", d

    def test_send_with_override(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/ai-weekly-briefing/send-now",
            json={"recipients": ["admin@propmanage.io"]},
            timeout=90,
        )
        assert r.status_code == 200
        d = r.json()
        assert "skipped" not in d, d
        assert d.get("ok") is True, d
        assert d.get("forced") is True
        assert d.get("recipients") == ["admin@propmanage.io"]
        assert "sent_at" in d and "subject" in d
        assert isinstance(d.get("summary_text"), str) and len(d["summary_text"]) > 0
        stats = d.get("stats") or {}
        for key in (
            "events_count", "by_kind", "auto_match_assigned",
            "findings_resolved", "findings_detected",
            "smoke_pass", "smoke_fail", "autonomy",
        ):
            assert key in stats, f"missing stats.{key}"
        assert "current" in stats["autonomy"]
        assert "week_ago" in stats["autonomy"]
        assert "current_tier" in stats["autonomy"]
        assert "general" in stats["autonomy"]["current"]

    def test_last_sent_at_populated(self, admin_session):
        cfg = admin_session.get(f"{API}/admin/ai-weekly-briefing/config", timeout=10).json()
        assert cfg.get("last_sent_at"), cfg

    def test_non_list_recipients_in_body_400(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/ai-weekly-briefing/send-now",
            json={"recipients": "admin@propmanage.io"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_send_uses_configured_recipients_when_empty_body(self, admin_session):
        # restore configured recipient first
        admin_session.put(
            f"{API}/admin/ai-weekly-briefing/config",
            json={"enabled": True, "recipients": ["admin@propmanage.io"]},
            timeout=10,
        )
        r = admin_session.post(
            f"{API}/admin/ai-weekly-briefing/send-now", json={}, timeout=90
        )
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True
        assert d.get("recipients") == ["admin@propmanage.io"]


# ---------- History ----------
class TestHistory:
    def test_history_listed_sorted_desc(self, admin_session):
        r = admin_session.get(
            f"{API}/admin/ai-weekly-briefing/history", params={"limit": 10}, timeout=10
        )
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "count" in d
        assert d["count"] == len(d["items"])
        assert d["count"] >= 1
        # sorted desc by sent_at
        sa = [it["sent_at"] for it in d["items"]]
        assert sa == sorted(sa, reverse=True), sa
        first = d["items"][0]
        for k in ("sent_at", "recipients", "subject", "ok", "summary_text", "stats"):
            assert k in first, f"missing history field {k}"
        assert "_id" not in first

    def test_history_client_403(self, client_session):
        r = client_session.get(f"{API}/admin/ai-weekly-briefing/history", timeout=10)
        assert r.status_code == 403


# ---------- Scheduled job direct invocation ----------
class TestSchedulerJob:
    def test_disabled_skip(self, admin_session):
        # set disabled
        admin_session.put(
            f"{API}/admin/ai-weekly-briefing/config",
            json={"enabled": False, "recipients": ["admin@propmanage.io"]},
            timeout=10,
        )
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.ai_weekly_briefing import run_weekly_briefing_job
        res = asyncio.get_event_loop().run_until_complete(run_weekly_briefing_job())
        assert res.get("skipped") == "disabled", res

    def test_enabled_executes(self, admin_session):
        admin_session.put(
            f"{API}/admin/ai-weekly-briefing/config",
            json={"enabled": True, "recipients": ["admin@propmanage.io"]},
            timeout=10,
        )
        # snapshot history count
        before = admin_session.get(
            f"{API}/admin/ai-weekly-briefing/history", params={"limit": 50}, timeout=10
        ).json()["count"]
        import sys
        sys.path.insert(0, "/app/backend")
        from routes.ai_weekly_briefing import run_weekly_briefing_job
        res = asyncio.get_event_loop().run_until_complete(run_weekly_briefing_job())
        assert "skipped" not in res, res
        assert res.get("ok") is True, res
        assert res.get("forced") is False  # job calls force=False
        after = admin_session.get(
            f"{API}/admin/ai-weekly-briefing/history", params={"limit": 50}, timeout=10
        ).json()["count"]
        assert after >= min(before + 1, 50)


# ---------- Regression on neighboring endpoints ----------
class TestRegression:
    def test_ai_activity(self, admin_session):
        r = admin_session.get(f"{API}/admin/ai-activity", timeout=15)
        assert r.status_code == 200

    def test_autonomy_score(self, admin_session):
        r = admin_session.get(f"{API}/admin/autonomy/score", timeout=15)
        assert r.status_code == 200

    def test_auto_match_preview(self, admin_session):
        r = admin_session.post(f"{API}/admin/auto-match/preview", json={}, timeout=15)
        assert r.status_code == 200

    def test_auto_match_schedule(self, admin_session):
        r = admin_session.get(f"{API}/admin/auto-match/schedule", timeout=15)
        assert r.status_code == 200

    def test_login_still_works(self):
        r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=15)
        assert r.status_code == 200
