"""Phase 38 — Content Audit + 10 new automation tests + bug fix regression."""
import os
import pytest
import requests
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = OWNER_ADMIN_PASSWORD
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "propmanage_db"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def client_session():
    return _login(CLIENT_EMAIL, CLIENT_PASS)


# ------------------------------------------------------------------
# BACKEND P0 — automation: 24 tests, 10 new pass
# ------------------------------------------------------------------

def test_automation_tests_registry_has_24(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/qa/automation/tests", timeout=20)
    assert r.status_code == 200
    data = r.json()
    tests = data.get("tests") or data.get("items") or data
    if isinstance(tests, dict):
        tests = list(tests.values())
    assert isinstance(tests, list)
    codes = {t.get("code") for t in tests if isinstance(t, dict)}
    assert len(tests) >= 24, f"Expected >=24 tests, got {len(tests)}: codes={sorted(codes)}"
    # CONTENT (5) + LIFECYCLE (5)
    new_codes = [f"DOC-AUDIT-0{i}" for i in range(1, 6)] + [f"LIFECYCLE-0{i}" for i in range(1, 6)]
    missing = [c for c in new_codes if c not in codes]
    assert not missing, f"Missing test codes: {missing}"


def test_automation_execute_all_10_new(admin_session):
    new_codes = [f"DOC-AUDIT-0{i}" for i in range(1, 6)] + [f"LIFECYCLE-0{i}" for i in range(1, 6)]
    r = admin_session.post(
        f"{BASE_URL}/api/admin/qa/automation/execute",
        json={"test_codes": new_codes},
        timeout=60,
    )
    assert r.status_code == 200, f"execute fail: {r.status_code} {r.text[:400]}"
    data = r.json()
    summary = data.get("summary") or {}
    assert summary.get("pass") == 10, f"Expected 10 pass, got summary={summary}, results sample={data.get('results', [])[:2]}"
    assert summary.get("fail") == 0, f"Expected 0 fail, got summary={summary}"


# ------------------------------------------------------------------
# BACKEND P0 — content-audit: scan / conflicts CRUD / ai-fix / apply
# ------------------------------------------------------------------

def test_content_audit_scan_clean(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/admin/qa/content-audit/scan", timeout=30)
    assert r.status_code == 200
    data = r.json()
    # Shape contract
    assert "detected" in data
    assert "added" in data
    assert "already_existing" in data
    assert "total_scanned" in data
    # After the bug fix, should be 0 newly added (escrow fixed)
    assert data["added"] == 0, f"Unexpected new conflicts: {data}"


def test_content_audit_synthetic_conflict_full_lifecycle(admin_session):
    """Insert synthetic conflict directly via motor, then run UI lifecycle."""
    async def _setup():
        client = AsyncIOMotorClient(MONGO_URL)
        dbm = client[DB_NAME]
        from datetime import datetime, timezone
        import uuid
        cid = "test38" + uuid.uuid4().hex[:8]
        await dbm.doc_conflicts.insert_one({
            "id": cid,
            "key": f"specialist::99::99::{cid}",
            "doc_slug": "specialist",
            "doc_role": "specialist",
            "section_index": 99,
            "section_heading": "Synthetic Test Section",
            "block_index": 99,
            "block_excerpt": "Banii pe care îi plătești specialistului sunt protejați în escrow până la finalizarea lucrării. NU ajung la specialist înainte de confirmarea ta.",
            "wrong_audience": "client",
            "severity": "high",
            "hint_counts": {"client": 3, "specialist": 0, "admin": 0},
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "ai_suggested_fix": None,
            "applied_at": None,
        })
        client.close()
        return cid

    async def _cleanup(cid):
        client = AsyncIOMotorClient(MONGO_URL)
        dbm = client[DB_NAME]
        await dbm.doc_conflicts.delete_one({"id": cid})
        await dbm.doc_overrides.delete_many({"section_index": 99, "block_index": 99, "doc_slug": "specialist"})
        client.close()

    cid = asyncio.get_event_loop().run_until_complete(_setup())
    try:
        # 1) list conflicts → should include it
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/content-audit/conflicts", timeout=20)
        assert r.status_code == 200
        rows = r.json().get("conflicts", [])
        assert any(c.get("id") == cid for c in rows), f"Synthetic conflict not in list of {len(rows)}"

        # 2) ai-fix
        r = admin_session.post(f"{BASE_URL}/api/admin/qa/content-audit/conflicts/{cid}/ai-fix", timeout=60)
        assert r.status_code == 200, f"ai-fix HTTP: {r.status_code} {r.text[:300]}"
        ai = r.json()
        assert "error" not in ai, f"ai-fix returned error: {ai}"
        assert ai.get("body"), f"ai-fix has no body: {ai}"
        assert "title" in ai

        # 3) apply with empty body
        r = admin_session.post(
            f"{BASE_URL}/api/admin/qa/content-audit/conflicts/{cid}/apply",
            json={},
            timeout=30,
        )
        assert r.status_code == 200, f"apply HTTP: {r.status_code} {r.text[:300]}"
        assert r.json().get("ok") is True

        # 4) status should now be 'fixed'
        r = admin_session.get(f"{BASE_URL}/api/admin/qa/content-audit/conflicts", timeout=20)
        rows = r.json().get("conflicts", [])
        synth = next((c for c in rows if c.get("id") == cid), None)
        assert synth and synth.get("status") == "fixed", f"Expected status=fixed, got {synth}"

        # 5) GET /api/admin/docs/specialist still works (override is silently skipped if section/block don't exist)
        r = admin_session.get(f"{BASE_URL}/api/admin/docs/specialist", timeout=20)
        assert r.status_code == 200
    finally:
        asyncio.get_event_loop().run_until_complete(_cleanup(cid))


def test_content_audit_status_patch_valid_and_invalid(admin_session):
    """Insert a synthetic conflict, PATCH status, then cleanup."""
    async def _setup():
        client = AsyncIOMotorClient(MONGO_URL)
        dbm = client[DB_NAME]
        from datetime import datetime, timezone
        import uuid
        cid = "test38p" + uuid.uuid4().hex[:8]
        await dbm.doc_conflicts.insert_one({
            "id": cid,
            "key": f"specialist::88::88::{cid}",
            "doc_slug": "specialist",
            "doc_role": "specialist",
            "section_index": 88,
            "section_heading": "Patch test",
            "block_index": 88,
            "block_excerpt": "test body",
            "wrong_audience": "client",
            "severity": "low",
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        client.close()
        return cid

    async def _cleanup(cid):
        client = AsyncIOMotorClient(MONGO_URL)
        dbm = client[DB_NAME]
        await dbm.doc_conflicts.delete_one({"id": cid})
        client.close()

    cid = asyncio.get_event_loop().run_until_complete(_setup())
    try:
        r = admin_session.patch(
            f"{BASE_URL}/api/admin/qa/content-audit/conflicts/{cid}/status",
            json={"status": "dismissed"},
            timeout=20,
        )
        assert r.status_code == 200
        assert r.json()["conflict"]["status"] == "dismissed"

        r = admin_session.patch(
            f"{BASE_URL}/api/admin/qa/content-audit/conflicts/{cid}/status",
            json={"status": "garbage-status"},
            timeout=20,
        )
        assert r.status_code == 400
    finally:
        asyncio.get_event_loop().run_until_complete(_cleanup(cid))


# ------------------------------------------------------------------
# BACKEND P1 — RBAC: client → 403
# ------------------------------------------------------------------

def test_content_audit_rbac_client_forbidden(client_session):
    endpoints = [
        ("POST", "/api/admin/qa/content-audit/scan", {}),
        ("GET", "/api/admin/qa/content-audit/conflicts", None),
        ("POST", "/api/admin/qa/content-audit/conflicts/anything/ai-fix", {}),
        ("POST", "/api/admin/qa/content-audit/conflicts/anything/apply", {}),
        ("PATCH", "/api/admin/qa/content-audit/conflicts/anything/status", {"status": "dismissed"}),
    ]
    for method, path, body in endpoints:
        if method == "GET":
            r = client_session.get(f"{BASE_URL}{path}", timeout=20)
        elif method == "PATCH":
            r = client_session.patch(f"{BASE_URL}{path}", json=body, timeout=20)
        else:
            r = client_session.post(f"{BASE_URL}{path}", json=body or {}, timeout=20)
        assert r.status_code in (401, 403), f"{method} {path} → expected 401/403, got {r.status_code} {r.text[:200]}"


# ------------------------------------------------------------------
# BACKEND P1 — regression: PDF + escrow content
# ------------------------------------------------------------------

def test_specialist_pdf_no_crash(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/docs/specialist/pdf", timeout=60)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf") or r.content[:5] == b"%PDF-"
    assert len(r.content) > 1000


def test_specialist_doc_escrow_audience_correct(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/docs/specialist", timeout=20)
    assert r.status_code == 200
    body_text = r.text.lower()
    # Specialist perspective should NOT contain client-payer perspective
    assert "banii pe care îi plătești" not in body_text, "Specialist doc still has client-perspective wording"
    # Should contain specialist-perspective text
    assert "alimentează escrow" in body_text or "ești plătit" in body_text or "primești" in body_text, \
        "Specialist doc missing specialist-perspective escrow callout"
