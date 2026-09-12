"""
Phase 33 — Backend tests for newly added features:
1. Knowledge Base Phase 2/3 PDFs and Markdown rendering (no reportlab crash)
2. Specialist Onboarding Email Drip (queue, dispatch-now, cancel)
3. Interactive QA Playbook (template, runs CRUD, AI suggester, markdown)
4. Authorization guards on admin/qa + admin/onboarding endpoints
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

# Load from frontend .env if not in environ
_url = os.environ.get("REACT_APP_BACKEND_URL")
if not _url:
    try:
        with open("/app/frontend/.env") as _f:
            for _ln in _f:
                if _ln.startswith("REACT_APP_BACKEND_URL="):
                    _url = _ln.split("=", 1)[1].strip()
                    break
    except Exception:
        pass
BASE_URL = (_url or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASSWORD = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"

DOC_SLUGS = ["specialist", "operator", "admin", "qa-testing"]


# -------- fixtures --------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="session")
def client_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": CLIENT_EMAIL, "password": CLIENT_PASSWORD})
    if r.status_code != 200:
        pytest.skip("Client login failed")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# -------- 1. Knowledge Base PDFs + Markdown --------
class TestKnowledgeBasePhased:
    @pytest.mark.parametrize("slug", DOC_SLUGS)
    def test_pdf_renders(self, admin_session, slug):
        r = admin_session.get(f"{API}/admin/docs/{slug}/pdf")
        assert r.status_code == 200, f"PDF {slug}: {r.status_code} {r.text[:200]}"
        assert len(r.content) > 1000, f"PDF {slug} too small: {len(r.content)} bytes"
        assert r.content[:4] == b"%PDF", f"PDF {slug} bad magic: {r.content[:8]}"

    @pytest.mark.parametrize("slug", DOC_SLUGS)
    def test_markdown_renders(self, admin_session, slug):
        r = admin_session.get(f"{API}/admin/docs/{slug}/markdown")
        assert r.status_code == 200, f"MD {slug}: {r.status_code} {r.text[:200]}"
        body = r.text
        assert len(body) > 500, f"MD {slug} too short: {len(body)} chars"


# -------- 2. Onboarding email drip --------
class TestOnboardingDrip:
    spec_email = None
    spec_user_id = None

    def test_register_specialist_enqueues_3_rows(self, admin_session):
        ts = int(time.time())
        TestOnboardingDrip.spec_email = f"spec_auto_{ts}@test.com"
        payload = {
            "email": TestOnboardingDrip.spec_email,
            "password": "Test1234!",
            "terms_accepted": True, "privacy_policy_accepted": True, "phone": "+40712000999",
            "name": "Auto Test Specialist",
            "role": "specialist",
            "service_categories": ["electric"],
            "coverage_zones": ["Bucuresti"],
        }
        r = requests.post(f"{API}/auth/register", json=payload)
        assert r.status_code in (200, 201), f"Register: {r.status_code} {r.text[:300]}"
        body = r.json()
        TestOnboardingDrip.spec_user_id = (
            body.get("user", {}).get("id") or body.get("id") or body.get("user_id")
        )
        # Confirm enqueued rows
        time.sleep(1.0)
        r2 = admin_session.get(f"{API}/admin/onboarding/queue")
        assert r2.status_code == 200, f"queue: {r2.status_code} {r2.text[:200]}"
        data = r2.json()
        rows = data.get("recent") or data.get("rows") or data.get("items") or data.get("queue") or (data if isinstance(data, list) else [])
        my_rows = [
            x for x in rows
            if (x.get("email") == TestOnboardingDrip.spec_email)
            or (x.get("user_id") and x["user_id"] == TestOnboardingDrip.spec_user_id)
        ]
        assert len(my_rows) >= 3, f"Expected >=3 onboarding rows, got {len(my_rows)} (total {len(rows)})"
        offsets = sorted([r.get("day_offset") for r in my_rows[:3]])
        assert offsets == [1, 3, 7], f"day_offsets mismatch: {offsets}"
        for x in my_rows[:3]:
            assert x.get("sent") in (False, None, 0), f"row sent flag wrong: {x}"

    def test_dispatch_now_returns_summary(self, admin_session):
        r = admin_session.post(f"{API}/admin/onboarding/dispatch-now", json={})
        assert r.status_code == 200, f"dispatch-now: {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("ok") is True, f"ok flag missing: {body}"
        # summary present
        summ = body.get("summary") or body
        assert "sent" in summ or "dispatched" in summ or "processed" in summ or "count" in summ, f"summary missing: {body}"

    def test_cancel_user_rows(self, admin_session):
        if not TestOnboardingDrip.spec_user_id:
            pytest.skip("no specialist user_id from prior test")
        uid = TestOnboardingDrip.spec_user_id
        r = admin_session.post(f"{API}/admin/onboarding/cancel/{uid}", json={})
        assert r.status_code == 200, f"cancel: {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body.get("ok") is True
        assert body.get("cancelled_rows", 0) >= 0


# -------- 3. QA Playbook --------
class TestQAPlaybook:
    run_id = None
    first_check_id = None

    def test_checklist_template_105_items(self, admin_session):
        r = admin_session.get(f"{API}/admin/qa/checklist/template")
        assert r.status_code == 200, f"template: {r.status_code} {r.text[:200]}"
        body = r.json()
        items = body.get("items") or body.get("checks") or []
        assert len(items) == 105, f"expected 105 items, got {len(items)}"
        stats = body.get("stats") or {}
        by_prio = stats.get("by_priority") or {}
        for k in ("P0", "P1", "P2"):
            assert k in by_prio, f"missing priority {k} in stats: {by_prio}"
        by_cat = stats.get("by_category") or {}
        for cat in ("CLIENT", "SPECIALIST", "OPERATOR", "ADMIN"):
            assert cat in by_cat, f"missing category {cat} in stats: {by_cat}"

    def test_create_run_has_105_pending(self, admin_session):
        r = admin_session.post(f"{API}/admin/qa/runs", json={"name": "Test Run Auto", "version": "v1"})
        assert r.status_code in (200, 201), f"create run: {r.status_code} {r.text[:300]}"
        body = r.json()
        run_obj = body.get("run") or body
        TestQAPlaybook.run_id = run_obj.get("run_id") or run_obj.get("id") or run_obj.get("_id")
        assert TestQAPlaybook.run_id, f"missing run id: {body}"
        checks = run_obj.get("checks") or []
        assert len(checks) == 105, f"expected 105 checks, got {len(checks)}"
        assert all(c.get("status") == "pending" for c in checks), "not all pending"
        TestQAPlaybook.first_check_id = checks[0].get("id") or checks[0].get("code") or checks[0].get("check_id")

    def test_patch_check_updates_summary(self, admin_session):
        if not TestQAPlaybook.run_id or not TestQAPlaybook.first_check_id:
            pytest.skip("missing run/check id")
        r = admin_session.patch(
            f"{API}/admin/qa/runs/{TestQAPlaybook.run_id}/check/{TestQAPlaybook.first_check_id}",
            json={"status": "pass", "note": "works"},
        )
        assert r.status_code == 200, f"patch: {r.status_code} {r.text[:300]}"
        body = r.json()
        summ = body.get("summary") or body
        closed = summ.get("closed") or summ.get("done")
        by_status = summ.get("by_status") or {}
        assert (closed and closed >= 1) or by_status.get("pass", 0) >= 1, f"summary not updated: {body}"

    def test_run_markdown(self, admin_session):
        if not TestQAPlaybook.run_id:
            pytest.skip("missing run id")
        r = admin_session.get(f"{API}/admin/qa/runs/{TestQAPlaybook.run_id}/markdown")
        assert r.status_code == 200, f"md: {r.status_code} {r.text[:200]}"
        ct = r.headers.get("content-type", "")
        assert "markdown" in ct or "text/plain" in ct, f"content-type: {ct}"
        assert len(r.text) > 200, f"md too short: {len(r.text)}"

    def test_ai_suggest(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/qa/ai-suggest",
            json={"feature": "Onboarding email drip pentru specialisti", "context": "Resend, scheduler 15min"},
            timeout=90,
        )
        assert r.status_code == 200, f"ai-suggest: {r.status_code} {r.text[:300]}"
        body = r.json()
        items = body.get("items") or body.get("suggestions") or []
        assert len(items) >= 6, f"expected >=6 suggestions, got {len(items)}"
        provider = body.get("provider") or ""
        assert "claude" in provider.lower() or "sonnet" in provider.lower(), f"provider: {provider}"
        for it in items[:3]:
            assert it.get("code"), f"item missing code: {it}"
            assert it.get("priority") in ("P0", "P1", "P2"), f"item priority: {it.get('priority')}"
            assert it.get("category"), f"item missing category: {it}"
            assert it.get("description"), f"item missing description: {it}"

    def test_close_run(self, admin_session):
        if not TestQAPlaybook.run_id:
            pytest.skip("missing run id")
        r = admin_session.post(f"{API}/admin/qa/runs/{TestQAPlaybook.run_id}/close", json={})
        assert r.status_code == 200, f"close: {r.status_code} {r.text[:300]}"
        # Verify by GET
        r2 = admin_session.get(f"{API}/admin/qa/runs/{TestQAPlaybook.run_id}")
        assert r2.status_code == 200
        body = r2.json()
        run_obj = body.get("run") or body
        assert run_obj.get("closed_at") is not None, f"closed_at not set: {run_obj.get('closed_at')}"


# -------- 4. Auth guards --------
class TestAuthGuards:
    def test_non_admin_blocked_qa(self, client_session):
        r = client_session.get(f"{API}/admin/qa/checklist/template")
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_non_admin_blocked_onboarding(self, client_session):
        r = client_session.get(f"{API}/admin/onboarding/queue")
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


# -------- 5. Cleanup --------
class TestCleanup:
    def test_cleanup_qa_runs(self, admin_session):
        # best effort delete created runs; tolerated if endpoint missing
        if TestQAPlaybook.run_id:
            admin_session.delete(f"{API}/admin/qa/runs/{TestQAPlaybook.run_id}")
