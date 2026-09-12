"""Backend tests for AI Marketing Campaigns (Phase 2) — generator, auto-trigger, image studio.

Covers:
- POST /api/admin/marketing/campaigns/generate (with skip_images=True for speed)
- GET  /api/admin/marketing/campaigns
- GET  /api/admin/marketing/campaigns/{id}
- POST /api/admin/marketing/campaigns/{id}/approve
- POST /api/admin/marketing/campaigns/{id}/reject
- POST /api/admin/marketing/auto-triggers/scan (and idempotency)
- GET  /api/admin/marketing/auto-triggers/recent
- RBAC: client gets 403 on all endpoints
"""
import os
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

API = f"{BASE_URL}/api"
ADMIN_PASSWORDS = [OWNER_ADMIN_PASSWORD, OWNER_ADMIN_PASSWORD]
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASSWORD = "Client123!"


def _login(email, passwords):
    if isinstance(passwords, str):
        passwords = [passwords]
    last = None
    for pw in passwords:
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=20)
        last = r
        if r.status_code == 200:
            return s, r
    return None, last


@pytest.fixture(scope="session")
def admin_session():
    s, r = _login("admin@propmanage.io", ADMIN_PASSWORDS)
    if not s:
        pytest.skip(f"Admin login failed: {r.status_code if r else 'n/a'}")
    return s


@pytest.fixture(scope="session")
def client_session():
    s, r = _login(CLIENT_EMAIL, CLIENT_PASSWORD)
    if not s:
        pytest.skip(f"Client login failed: {r.status_code if r else 'n/a'}")
    return s


# Shared state across tests
_state = {"generated_id": None, "existing_id": None}


# ---------- 1. Manual generator (text only — skip images for speed) ----------

class TestGenerateCampaign:
    def test_generate_skip_images(self, admin_session):
        payload = {
            "objective": "leads",
            "service_category": "Curățenie",
            "county": "Iași",
            "budget_ron": 500,
            "skip_images": True,
        }
        r = admin_session.post(f"{API}/admin/marketing/campaigns/generate",
                               json=payload, timeout=90)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        # Core fields
        for k in ["id", "objective", "service_category", "county", "budget_ron",
                  "status", "source", "avatar", "audience", "ad_texts", "cta",
                  "image_prompts", "image_count", "kpis"]:
            assert k in d, f"missing {k}"
        assert d["status"] == "draft"
        assert d["source"] == "manual"
        assert d["objective"] == "leads"
        assert d["budget_ron"] == 500
        assert d["image_count"] == 0
        # Avatar shape
        av = d["avatar"]
        assert isinstance(av, dict)
        for k in ["age_range", "occupation", "pain_points", "motivations"]:
            assert k in av, f"avatar missing {k}"
        # Audience
        au = d["audience"]
        for k in ["targeting", "interests", "exclusions"]:
            assert k in au
        # Ad texts (1..3 variants)
        assert isinstance(d["ad_texts"], list) and 1 <= len(d["ad_texts"]) <= 3
        first = d["ad_texts"][0]
        for k in ["primary_text", "headline", "description"]:
            assert k in first
        # Image prompts
        assert isinstance(d["image_prompts"], list)
        # KPIs
        assert isinstance(d["kpis"], dict) and len(d["kpis"]) > 0

        _state["generated_id"] = d["id"]

    def test_generate_invalid_objective(self, admin_session):
        r = admin_session.post(f"{API}/admin/marketing/campaigns/generate",
                               json={"objective": "BOGUS", "service_category": "X",
                                     "county": "Y", "budget_ron": 500,
                                     "skip_images": True}, timeout=15)
        assert r.status_code == 400

    def test_generate_budget_validation(self, admin_session):
        # Below min (50)
        r = admin_session.post(f"{API}/admin/marketing/campaigns/generate",
                               json={"objective": "leads", "service_category": "X",
                                     "county": "Y", "budget_ron": 10,
                                     "skip_images": True}, timeout=15)
        assert r.status_code == 422  # pydantic validation


# ---------- 2. List + detail ----------

class TestListCampaigns:
    def test_list_returns_no_base64(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/campaigns", timeout=20)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        assert "items" in d and "count" in d
        # Every item should NOT have an "images" key (it's projected out)
        for it in d["items"]:
            assert "images" not in it, "list endpoint must not return base64 images"
            for k in ["id", "status", "service_category", "county", "budget_ron",
                      "image_count"]:
                assert k in it
        # Find an existing campaign to use later (any draft)
        for it in d["items"]:
            if it["status"] in ("draft", "auto_draft"):
                _state["existing_id"] = it["id"]
                break

    def test_list_filter_by_status(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/campaigns",
                              params={"status": "draft"}, timeout=15)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["status"] == "draft"

    def test_detail_includes_images_field(self, admin_session):
        cid = _state["generated_id"]
        if not cid:
            pytest.skip("no generated id")
        r = admin_session.get(f"{API}/admin/marketing/campaigns/{cid}", timeout=20)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        assert d["id"] == cid
        # "images" key present (may be empty list since we skipped)
        assert "images" in d
        assert isinstance(d["images"], list)
        # Each image, if any, must be a data URI
        for img in d["images"]:
            assert "data_uri" in img
            assert img["data_uri"].startswith("data:image/")
            assert ";base64," in img["data_uri"]

    def test_detail_invalid_id(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/campaigns/not_an_oid", timeout=10)
        assert r.status_code == 400

    def test_detail_not_found(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/campaigns/507f1f77bcf86cd799439011",
                              timeout=10)
        assert r.status_code == 404


# ---------- 3. Approve / Reject ----------

class TestApproveReject:
    def test_approve_persists(self, admin_session):
        # Use generated campaign (status=draft)
        cid = _state["generated_id"]
        if not cid:
            pytest.skip("no generated id")
        r = admin_session.post(f"{API}/admin/marketing/campaigns/{cid}/approve",
                               timeout=15)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        assert d.get("status") == "approved"
        # Verify persistence via GET
        g = admin_session.get(f"{API}/admin/marketing/campaigns/{cid}", timeout=10)
        assert g.status_code == 200
        full = g.json()
        assert full["status"] == "approved"
        assert full.get("approved_at")
        assert full.get("approved_by")

    def test_reject_existing_draft(self, admin_session):
        # Find another draft/auto_draft to reject
        r = admin_session.get(f"{API}/admin/marketing/campaigns", timeout=15)
        target = None
        for it in r.json()["items"]:
            if it["status"] in ("draft", "auto_draft") and it["id"] != _state["generated_id"]:
                target = it["id"]
                break
        if not target:
            pytest.skip("no other draft to reject")
        rj = admin_session.post(f"{API}/admin/marketing/campaigns/{target}/reject",
                                timeout=15)
        assert rj.status_code == 200
        assert rj.json().get("status") == "rejected"
        # Verify
        g = admin_session.get(f"{API}/admin/marketing/campaigns/{target}", timeout=10)
        assert g.json()["status"] == "rejected"
        assert g.json().get("rejected_at")

    def test_approve_nonexistent(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/marketing/campaigns/507f1f77bcf86cd799439011/approve",
            timeout=10)
        assert r.status_code == 404

    def test_approve_invalid_id(self, admin_session):
        r = admin_session.post(
            f"{API}/admin/marketing/campaigns/not_oid/approve", timeout=10)
        assert r.status_code == 400


# ---------- 4. Auto-trigger scan ----------

class TestAutoTrigger:
    def test_scan_runs(self, admin_session):
        r = admin_session.post(f"{API}/admin/marketing/auto-triggers/scan",
                               timeout=180)
        assert r.status_code == 200, r.text[:500]
        d = r.json()
        for k in ["triggers_detected", "drafts_created",
                  "skipped_recent_duplicate", "created", "skipped",
                  "scanned_at"]:
            assert k in d, f"missing {k}"
        assert isinstance(d["created"], list)
        assert isinstance(d["skipped"], list)
        TestAutoTrigger._first_run = d

    def test_scan_idempotent(self, admin_session):
        first = getattr(TestAutoTrigger, "_first_run", None)
        if first is None:
            pytest.skip("first scan missing")
        r = admin_session.post(f"{API}/admin/marketing/auto-triggers/scan",
                               timeout=180)
        assert r.status_code == 200
        d = r.json()
        # If first run created any, second should now skip them
        if first["drafts_created"] > 0:
            assert d["skipped_recent_duplicate"] >= first["drafts_created"], \
                f"idempotency broken: first created {first['drafts_created']}, " \
                f"second only skipped {d['skipped_recent_duplicate']}"
            assert d["drafts_created"] == 0 or \
                d["triggers_detected"] > first["triggers_detected"]

    def test_recent_auto_triggers(self, admin_session):
        r = admin_session.get(f"{API}/admin/marketing/auto-triggers/recent",
                              timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "count" in d
        for it in d["items"]:
            assert it["source"] == "auto_trigger"
            assert "images" not in it  # projection


# ---------- 5. RBAC ----------

class TestRBACCampaigns:
    def test_generate_forbidden_client(self, client_session):
        r = client_session.post(f"{API}/admin/marketing/campaigns/generate",
                                json={"objective": "leads",
                                      "service_category": "X",
                                      "county": "Y",
                                      "budget_ron": 500,
                                      "skip_images": True}, timeout=15)
        assert r.status_code == 403

    def test_list_forbidden_client(self, client_session):
        r = client_session.get(f"{API}/admin/marketing/campaigns", timeout=10)
        assert r.status_code == 403

    def test_scan_forbidden_client(self, client_session):
        r = client_session.post(f"{API}/admin/marketing/auto-triggers/scan",
                                timeout=15)
        assert r.status_code == 403

    def test_recent_forbidden_client(self, client_session):
        r = client_session.get(f"{API}/admin/marketing/auto-triggers/recent",
                               timeout=10)
        assert r.status_code == 403

    def test_anonymous_403(self):
        r = requests.get(f"{API}/admin/marketing/campaigns", timeout=10)
        assert r.status_code in (401, 403)
