"""Phase 39 — Terminology Audit backend tests.

Validates the /api/admin/qa/term-audit/* endpoints, RBAC, AI fix/apply lifecycle,
cluster seed, and the new TERM-01..05 automation tests.
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login failed {creds['email']}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


# -------------------- BACKEND P0 --------------------

class TestClusters:
    def test_clusters_seeded_5(self, admin_sess):
        r = admin_sess.get(f"{API}/admin/qa/term-audit/clusters", timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        clusters = data["clusters"]
        keys = {c["key"] for c in clusters}
        # Required 5 seed keys
        for k in ("escrow", "specialist", "client", "comision", "trust_score"):
            assert k in keys, f"missing seed cluster {k} in {keys}"
        seeds = [c for c in clusters if c["key"] in ("escrow", "specialist", "client", "comision", "trust_score")]
        for c in seeds:
            assert c.get("is_seed") is True, f"cluster {c['key']} not marked is_seed=true"
            assert isinstance(c.get("variants"), list) and len(c["variants"]) >= 2
            assert c.get("canonical")


class TestScanAndInconsistencies:
    inc_id_for_lifecycle = None

    def test_scan_returns_inconsistencies(self, admin_sess):
        r = admin_sess.post(f"{API}/admin/qa/term-audit/scan", timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert "report" in body and "persisted" in body
        report = body["report"]
        assert report["clusters_checked"] == 5
        assert isinstance(report["by_doc"], dict)
        if report["total_inconsistencies"] == 0:
            pytest.skip("CMS content is already canonical — no term inconsistencies to exercise")
        assert report["total_inconsistencies"] >= 1
        persisted = body["persisted"]
        assert {"added", "already_existing", "total"} <= set(persisted.keys())

    def test_list_open_inconsistencies(self, admin_sess):
        r = admin_sess.get(f"{API}/admin/qa/term-audit/inconsistencies", params={"status": "open"}, timeout=30)
        assert r.status_code == 200
        rows = r.json()["inconsistencies"]
        if not rows:
            pytest.skip("no open term inconsistencies in current CMS content")
        assert len(rows) >= 1
        row = rows[0]
        for field in ("id", "doc_slug", "cluster_key", "canonical", "variants_used", "occurrences"):
            assert field in row, f"missing field {field}"
        assert isinstance(row["variants_used"], list) and len(row["variants_used"]) >= 2
        assert isinstance(row["occurrences"], list) and len(row["occurrences"]) >= 1
        occ0 = row["occurrences"][0]
        for f in ("section_index", "block_index", "terms", "excerpt"):
            assert f in occ0, f"occurrence missing {f}"
        TestScanAndInconsistencies.inc_id_for_lifecycle = row["id"]

    def test_ai_fix_uses_canonical(self, admin_sess):
        inc_id = TestScanAndInconsistencies.inc_id_for_lifecycle
        if not inc_id:
            pytest.skip("no inconsistency available (content already canonical)")
        # Re-fetch to know variants/canonical
        rows = admin_sess.get(f"{API}/admin/qa/term-audit/inconsistencies", timeout=30).json()["inconsistencies"]
        inc = next(x for x in rows if x["id"] == inc_id)
        canonical = inc["canonical"]
        non_canonical_variants = [v for v in inc["variants_used"] if v.lower() != canonical.lower()]

        r = admin_sess.post(
            f"{API}/admin/qa/term-audit/inconsistencies/{inc_id}/ai-fix",
            json={"occurrence_index": 0},
            timeout=90,
        )
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert "error" not in body, f"AI fix returned error: {body}"
        assert "title" in body and "body" in body and body.get("occurrence_index") == 0
        assert len(body["body"]) > 10
        # Body should NOT contain any non-canonical variant
        low = body["body"].lower()
        for v in non_canonical_variants:
            assert v.lower() not in low, f"AI body still contains variant '{v}': {body['body'][:300]}"

        # Idempotency — re-run, still succeeds
        r2 = admin_sess.post(
            f"{API}/admin/qa/term-audit/inconsistencies/{inc_id}/ai-fix",
            json={"occurrence_index": 0},
            timeout=90,
        )
        assert r2.status_code == 200 and "error" not in r2.json()

    def test_apply_fix_lifecycle(self, admin_sess):
        inc_id = TestScanAndInconsistencies.inc_id_for_lifecycle
        rows_before = admin_sess.get(f"{API}/admin/qa/term-audit/inconsistencies", timeout=30).json()["inconsistencies"]
        inc = next((x for x in rows_before if x["id"] == inc_id), None)
        if inc is None:
            pytest.skip("lifecycle inconsistency no longer open (fixed by a previous run)")
        doc_slug = inc["doc_slug"]

        r = admin_sess.post(f"{API}/admin/qa/term-audit/inconsistencies/{inc_id}/apply", json={}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body.get("ok") is True
        ov = body["override"]
        assert ov["doc_slug"] == doc_slug
        assert "section_index" in ov and "block_index" in ov
        assert "patch" in ov and "body" in ov["patch"]

        # Check status changed to fixed
        rows_after = admin_sess.get(f"{API}/admin/qa/term-audit/inconsistencies", timeout=30).json()["inconsistencies"]
        inc_after = next((x for x in rows_after if x["id"] == inc_id), None)
        assert inc_after is not None, "inconsistency vanished after apply"
        assert inc_after["status"] == "fixed"

        # Docs endpoint should still return 200 with the patched block
        rd = admin_sess.get(f"{API}/admin/docs/{doc_slug}", timeout=30)
        assert rd.status_code == 200

    def test_patch_status_dismissed(self, admin_sess):
        rows = admin_sess.get(f"{API}/admin/qa/term-audit/inconsistencies",
                              params={"status": "open"}, timeout=30).json()["inconsistencies"]
        if not rows:
            pytest.skip("no open inconsistencies to dismiss")
        inc_id = rows[0]["id"]
        r = admin_sess.patch(
            f"{API}/admin/qa/term-audit/inconsistencies/{inc_id}/status",
            json={"status": "dismissed"}, timeout=30,
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["inconsistency"]["status"] == "dismissed"

    def test_patch_status_invalid_400(self, admin_sess):
        rows = admin_sess.get(f"{API}/admin/qa/term-audit/inconsistencies", timeout=30).json()["inconsistencies"]
        if not rows:
            pytest.skip("no rows")
        inc_id = rows[0]["id"]
        r = admin_sess.patch(
            f"{API}/admin/qa/term-audit/inconsistencies/{inc_id}/status",
            json={"status": "bogus_state"}, timeout=30,
        )
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:200]}"


# -------------------- BACKEND P1 --------------------

class TestDiscoverAndAddCluster:
    def test_discover(self, admin_sess):
        t0 = time.time()
        r = admin_sess.post(f"{API}/admin/qa/term-audit/discover", timeout=60)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert "proposed" in body, f"discover response missing 'proposed': {body}"
        assert isinstance(body["proposed"], list)
        assert elapsed < 60, f"discover too slow: {elapsed}s"

    def test_add_cluster_and_duplicate(self, admin_sess):
        unique_key = f"test_cluster_{int(time.time())}"
        payload = {
            "key": unique_key,
            "canonical": "termen-test",
            "variants": ["sinonim1", "sinonim2"],
            "description": "Test cluster — Phase 39 automated test",
        }
        r = admin_sess.post(f"{API}/admin/qa/term-audit/clusters", json=payload, timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("ok") is True

        # duplicate → 400
        r2 = admin_sess.post(f"{API}/admin/qa/term-audit/clusters", json=payload, timeout=30)
        assert r2.status_code == 400

        # cleanup
        try:
            from pymongo import MongoClient
            mc = MongoClient(os.environ.get("MONGO_URL"))
            mc[os.environ.get("DB_NAME", "test_database")].term_clusters.delete_one({"key": unique_key})
        except Exception:
            pass


class TestAutomationTerm:
    def test_execute_term_tests(self, admin_sess):
        r = admin_sess.post(
            f"{API}/admin/qa/automation/execute",
            json={"test_codes": ["TERM-01", "TERM-02", "TERM-03", "TERM-04", "TERM-05"]},
            timeout=120,
        )
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        # Should return results array
        results = body.get("results") or body.get("run", {}).get("results") or []
        assert results, f"no results returned: {body}"
        assert len(results) == 5
        for res in results:
            assert "note" in res or "message" in res or "details" in res or "summary" in res, f"result missing note: {res}"


# -------------------- BACKEND P2 — RBAC --------------------

class TestRBAC:
    @pytest.mark.parametrize("method,path,body", [
        ("GET", "/admin/qa/term-audit/clusters", None),
        ("POST", "/admin/qa/term-audit/scan", {}),
        ("GET", "/admin/qa/term-audit/inconsistencies", None),
        ("POST", "/admin/qa/term-audit/discover", {}),
    ])
    def test_client_forbidden(self, client_sess, method, path, body):
        url = f"{API}{path}"
        if method == "GET":
            r = client_sess.get(url, timeout=30)
        else:
            r = client_sess.post(url, json=body or {}, timeout=30)
        assert r.status_code in (401, 403), f"{method} {path} expected 401/403 got {r.status_code}"
