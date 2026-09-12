"""Tests for iteration 69 — Sprint Health Digest + Legal Sprint 1.

Covers:
  - /api/admin/it-collaborators/digest/* (settings GET/POST, run, RBAC)
  - /api/legal/* (documents, sign, me/status)
  - /api/admin/legal/* (audit, contracts/{email}, documents POST/PATCH, seed)
"""
import os
import uuid
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

SUPER = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
SUB = {"email": "testing.admin@propmanage.io", "password": "TestAdmin123!"}
DEV = {"email": "dev1@team.com", "password": "Dev1Pass!"}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {email}: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def super_session():
    return _login(SUPER["email"], SUPER["password"])


@pytest.fixture(scope="module")
def sub_session():
    return _login(SUB["email"], SUB["password"])


@pytest.fixture(scope="module")
def dev_session():
    return _login(DEV["email"], DEV["password"])


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT["email"], CLIENT["password"])


# ─────────────────────────────────────────────────────────────────────────────
# DIGEST endpoints
# ─────────────────────────────────────────────────────────────────────────────
class TestDigestSettings:
    def test_get_settings_super(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/digest/settings", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("enabled", "recipient_email", "day_of_week", "hour", "minute"):
            assert k in data, f"missing {k}"
        assert isinstance(data["enabled"], bool)
        assert 0 <= int(data["hour"]) <= 23

    def test_get_settings_subadmin_403(self, sub_session):
        r = sub_session.get(f"{BASE_URL}/api/admin/it-collaborators/digest/settings", timeout=15)
        assert r.status_code == 403, r.text

    def test_post_settings_valid(self, super_session):
        # Set to specific values
        payload = {"enabled": True, "recipient_email": "admin@propmanage.io",
                   "day_of_week": "sun", "hour": 18, "minute": 0}
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators/digest/settings",
                               json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["day_of_week"] == "sun"
        assert int(data["hour"]) == 18
        # Verify persistence via GET
        r2 = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/digest/settings", timeout=15)
        assert r2.json()["hour"] == 18

    def test_post_settings_invalid_hour(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators/digest/settings",
                               json={"hour": 25}, timeout=15)
        assert r.status_code == 400, r.text

    def test_post_settings_invalid_day(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators/digest/settings",
                               json={"day_of_week": "xxx"}, timeout=15)
        assert r.status_code == 400, r.text

    def test_post_settings_subadmin_403(self, sub_session):
        r = sub_session.post(f"{BASE_URL}/api/admin/it-collaborators/digest/settings",
                             json={"enabled": False}, timeout=15)
        assert r.status_code == 403


class TestDigestRun:
    def test_run_subadmin_403(self, sub_session):
        r = sub_session.post(f"{BASE_URL}/api/admin/it-collaborators/digest/run", timeout=15)
        assert r.status_code == 403, r.text

    @pytest.mark.slow
    def test_run_super_ok(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/it-collaborators/digest/run", timeout=120)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert "sent_to" in data and "@" in data["sent_to"]
        assert "provider" in data
        report = data.get("report") or {}
        for k in ("summary", "risk_level", "sprint_risk_score",
                  "top_performers", "at_risk", "team_recommendations",
                  "analyzed_count", "generated_at"):
            assert k in report, f"report missing {k}"
        # Verify last_sent_at persisted
        s2 = super_session.get(f"{BASE_URL}/api/admin/it-collaborators/digest/settings", timeout=15).json()
        assert s2.get("last_sent_at") is not None
        assert s2.get("last_status") in ("ok", "error")


# ─────────────────────────────────────────────────────────────────────────────
# LEGAL — public-ish user endpoints
# ─────────────────────────────────────────────────────────────────────────────
EXPECTED_TYPES = {"nda", "collaboration", "ip_cession", "security_policy", "infra_access", "regulation", "marketplace_partner"}


class TestLegalDocuments:
    def test_list_documents_returns_6(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/legal/documents", timeout=15)
        assert r.status_code == 200, r.text
        items = r.json().get("items", [])
        types = {it["type"] for it in items if it.get("active")}
        assert EXPECTED_TYPES.issubset(types), f"missing types: {EXPECTED_TYPES - types}"
        for it in items:
            if it["type"] in EXPECTED_TYPES and it["active"]:
                assert it["mandatory"] is True

    def test_get_document_by_type(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/legal/documents/nda", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["type"] == "nda"
        assert d["body"]
        assert d["active"] is True

    def test_get_document_unknown_404(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/legal/documents/unknown_xyz", timeout=15)
        assert r.status_code == 404


class TestLegalSignAndStatus:
    def test_non_strategic_user_compliant_true(self, client_session):
        r = client_session.get(f"{BASE_URL}/api/legal/me/status", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_strategic_contributor"] is False
        assert data["compliant"] is True

    def test_strategic_status_required_six(self, dev_session):
        r = dev_session.get(f"{BASE_URL}/api/legal/me/status", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_strategic_contributor"] is True
        assert set(data["required"]) == EXPECTED_TYPES
        total = len(data["signed"]) + len(data["pending"])
        assert total == len(EXPECTED_TYPES), f"expected {len(EXPECTED_TYPES)} total, got signed={len(data['signed'])} pending={len(data['pending'])}"

    def test_accept_agreed_false_returns_400(self, dev_session):
        # get a doc id
        r = dev_session.get(f"{BASE_URL}/api/legal/documents/regulation", timeout=15)
        doc_id = r.json()["id"]
        r2 = dev_session.post(f"{BASE_URL}/api/legal/me/accept",
                              json={"document_id": doc_id, "agreed": False,
                                    "signature_name": "Dev One"}, timeout=15)
        assert r2.status_code == 400

    def test_accept_invalid_document_id_404(self, dev_session):
        # 24-hex but unlikely to exist
        bogus = "0" * 24
        r = dev_session.post(f"{BASE_URL}/api/legal/me/accept",
                             json={"document_id": bogus, "agreed": True,
                                   "signature_name": "Dev One"}, timeout=15)
        assert r.status_code == 404

    def test_sign_all_pending_makes_compliant(self, dev_session):
        # Get current pending list (may already be signed from previous runs)
        r = dev_session.get(f"{BASE_URL}/api/legal/me/status", timeout=15)
        status = r.json()
        pending = status["pending"]
        before_signed = len(status["signed"])
        for p in pending:
            r2 = dev_session.post(f"{BASE_URL}/api/legal/me/accept",
                                  json={"document_id": p["document_id"], "agreed": True,
                                        "signature_name": "Dev One"}, timeout=15)
            assert r2.status_code == 200, f"sign failed for {p['type']}: {r2.text}"
            body = r2.json()
            assert body["status"] == "accepted"
            assert body["signature_name"] == "Dev One"
            assert body["document_type"] == p["type"]
        # Now should be compliant
        r3 = dev_session.get(f"{BASE_URL}/api/legal/me/status", timeout=15).json()
        assert len(r3["pending"]) == 0
        assert len(r3["signed"]) >= max(6, before_signed)
        assert r3["compliant"] is True


# ─────────────────────────────────────────────────────────────────────────────
# LEGAL ADMIN endpoints
# ─────────────────────────────────────────────────────────────────────────────
class TestLegalAdmin:
    def test_audit_super(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/legal/audit", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert set(data["required_types"]) == EXPECTED_TYPES
        assert isinstance(data["items"], list)
        if data["items"]:
            row = data["items"][0]
            for k in ("collaborator_id", "name", "email", "role", "compliant", "documents"):
                assert k in row
            for d in row["documents"]:
                assert d["status"] in ("ok", "missing", "outdated")

    def test_audit_subadmin_403(self, sub_session):
        r = sub_session.get(f"{BASE_URL}/api/admin/legal/audit", timeout=15)
        assert r.status_code == 403

    def test_audit_only_non_compliant_filter(self, super_session):
        all_r = super_session.get(f"{BASE_URL}/api/admin/legal/audit", timeout=15).json()
        only_nc = super_session.get(f"{BASE_URL}/api/admin/legal/audit?only_non_compliant=true",
                                    timeout=15).json()
        # filtered count <= total count
        assert only_nc["count"] <= all_r["count"]
        for row in only_nc["items"]:
            assert row["compliant"] is False

    def test_contracts_by_email_super(self, super_session):
        r = super_session.get(f"{BASE_URL}/api/admin/legal/contracts/dev1@team.com", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data["items"], list)
        # After previous tests, dev1 should have signatures
        if data["items"]:
            for c in data["items"]:
                assert "document_type" in c
                assert "status" in c

    def test_contracts_by_email_subadmin_403(self, sub_session):
        r = sub_session.get(f"{BASE_URL}/api/admin/legal/contracts/dev1@team.com", timeout=15)
        assert r.status_code == 403

    def test_create_new_version_deactivates_old(self, super_session):
        ver = f"test{uuid.uuid4().hex[:6]}"
        payload = {
            "type": "nda", "version": ver, "title": "NDA TEST",
            "summary": "test", "body": "# Test", "mandatory": True, "active": True,
        }
        r = super_session.post(f"{BASE_URL}/api/admin/legal/documents", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        new_doc = r.json()
        assert new_doc["version"] == ver
        assert new_doc["active"] is True
        # GET active for nda should now return the new version
        r2 = super_session.get(f"{BASE_URL}/api/legal/documents/nda", timeout=15).json()
        assert r2["version"] == ver

        # Duplicate same type+version => 409
        r3 = super_session.post(f"{BASE_URL}/api/admin/legal/documents", json=payload, timeout=15)
        assert r3.status_code == 409

        # PATCH it
        r4 = super_session.patch(f"{BASE_URL}/api/admin/legal/documents/{new_doc['id']}",
                                 json={"title": "NDA TEST patched"}, timeout=15)
        assert r4.status_code == 200
        assert r4.json()["title"] == "NDA TEST patched"

        # Restore: deactivate test version and re-activate v1.0 via direct admin call
        # Use POST seed to be idempotent (won't reactivate v1.0 because it already exists deactivated)
        # We re-activate v1.0 manually via PATCH
        r5 = super_session.get(f"{BASE_URL}/api/legal/documents?active_only=false", timeout=15).json()
        v1 = next((d for d in r5["items"] if d["type"] == "nda" and d["version"] == "1.0"), None)
        # Deactivate the test version first
        super_session.patch(f"{BASE_URL}/api/admin/legal/documents/{new_doc['id']}",
                            json={"active": False}, timeout=15)
        if v1:
            super_session.patch(f"{BASE_URL}/api/admin/legal/documents/{v1['id']}",
                                json={"active": True}, timeout=15)

    def test_seed_idempotent(self, super_session):
        r = super_session.post(f"{BASE_URL}/api/admin/legal/seed", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # All defaults already exist => inserted should be 0
        assert data["inserted"] == 0
        assert data["total"] >= len(EXPECTED_TYPES)

    def test_create_document_subadmin_403(self, sub_session):
        r = sub_session.post(f"{BASE_URL}/api/admin/legal/documents",
                             json={"type": "nda", "version": "9.9", "title": "x", "body": "x"},
                             timeout=15)
        assert r.status_code == 403
