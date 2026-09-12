"""ST-001 Storage & Media — backend regression suite.

Covers: user usage endpoint, admin config GET/PUT (dinamice, nu hardcodate),
overview, recompute retroactiv, migrare status, enforcement limite per fișier,
tracking la upload/delete în Document Vault, securitate 401/403.
"""
import io
import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def anon_sess():
    return requests.Session()


class TestUserUsage:
    def test_usage_structure(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/storage/usage", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        p = d["personal"]
        for k in ("tier", "tier_label", "used_bytes", "quota_bytes", "used_human", "quota_human", "pct", "files_count"):
            assert k in p, f"missing personal.{k}"
        assert p["tier"] in ("free", "house_health")
        assert p["quota_bytes"] > 0
        assert "thresholds" in d and len(d["thresholds"]) == 2
        assert "upgrade_available" in d

    def test_usage_dt_bucket_separate(self, client_sess):
        """client@propmanage.io are digital_twin_pro → bucket DT separat vizibil."""
        d = client_sess.get(f"{BASE_URL}/api/storage/usage", timeout=30).json()
        assert "digital_twin" in d, "DT bucket missing for dt_pro user"
        dt = d["digital_twin"]
        assert dt["quota_bytes"] > 0
        # DT nu consumă cota personală: bucket-uri distincte
        assert dt["used_bytes"] >= 0
        assert "note" in dt

    def test_usage_requires_auth(self, anon_sess):
        r = anon_sess.get(f"{BASE_URL}/api/storage/usage", timeout=20)
        assert r.status_code in (401, 403)


class TestAdminConfig:
    def test_config_defaults(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/storage/config", timeout=30)
        assert r.status_code == 200, r.text
        cfg = r.json()
        assert cfg["tiers"]["free"]["quota_mb"] >= 1
        assert set(cfg["file_limits_mb"]) >= {"document_vault", "house_health_doc", "digital_twin_model", "digital_twin_plan", "docs_ai"}
        assert len(cfg["warning_thresholds"]) == 2
        assert "compression" in cfg

    def test_config_update_and_restore(self, admin_sess):
        orig = admin_sess.get(f"{BASE_URL}/api/admin/storage/config", timeout=30).json()
        orig_limit = orig["file_limits_mb"]["document_vault"]
        r = admin_sess.put(f"{BASE_URL}/api/admin/storage/config",
                           json={"file_limits_mb": {"document_vault": 7}}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["file_limits_mb"]["document_vault"] == 7
        # restore
        r2 = admin_sess.put(f"{BASE_URL}/api/admin/storage/config",
                            json={"file_limits_mb": {"document_vault": orig_limit}}, timeout=30)
        assert r2.status_code == 200
        assert r2.json()["file_limits_mb"]["document_vault"] == orig_limit

    def test_config_validation(self, admin_sess):
        r = admin_sess.put(f"{BASE_URL}/api/admin/storage/config",
                           json={"tiers": {"free": {"quota_mb": 0}}}, timeout=30)
        assert r.status_code == 400

    def test_config_forbidden_for_client(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/admin/storage/config", timeout=20)
        assert r.status_code in (401, 403)

    def test_overview_structure(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/storage/overview", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("totals", "top_users", "modules", "migration", "config", "disk"):
            assert k in d, f"missing {k}"
        mod_ids = {m["id"] for m in d["modules"]}
        assert {"document_vault", "house_health", "digital_twin", "docs_ai"} <= mod_ids

    def test_recompute(self, admin_sess):
        r = admin_sess.post(f"{BASE_URL}/api/admin/storage/recompute", timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["users"] >= 0
        # DT bytes trebuie să existe separat (26 modele + 13 planuri în demo)
        assert d["digital_twin_bytes"] >= 0

    def test_migrate_status(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/storage/migrate/status", timeout=30)
        assert r.status_code == 200
        assert "status" in r.json()


class TestEnforcementVault:
    """Limite dinamice + tracking usage pe Document Vault (E2E cu quota reală)."""

    @pytest.fixture(scope="class")
    def prop_id(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/properties", timeout=30)
        if r.status_code != 200 or not r.json():
            pytest.skip("Clientul demo nu are proprietăți")
        items = r.json()
        if isinstance(items, dict):
            items = items.get("properties") or items.get("items") or []
        if not items:
            pytest.skip("Clientul demo nu are proprietăți")
        return items[0]["id"]

    def test_upload_over_limit_rejected(self, client_sess, admin_sess, prop_id):
        orig = admin_sess.get(f"{BASE_URL}/api/admin/storage/config", timeout=30).json()
        orig_limit = orig["file_limits_mb"]["document_vault"]
        try:
            admin_sess.put(f"{BASE_URL}/api/admin/storage/config",
                           json={"file_limits_mb": {"document_vault": 0.5}}, timeout=30)
            big = b"x" * (700 * 1024)  # 0.7MB > 0.5MB
            r = client_sess.post(
                f"{BASE_URL}/api/properties/{prop_id}/documents",
                files={"file": ("test_st001.pdf", io.BytesIO(big), "application/pdf")},
                data={"category": "altele", "title": "ST-001 limit test"},
                timeout=60,
            )
            assert r.status_code == 413, f"expected 413, got {r.status_code}: {r.text[:200]}"
        finally:
            admin_sess.put(f"{BASE_URL}/api/admin/storage/config",
                           json={"file_limits_mb": {"document_vault": orig_limit}}, timeout=30)

    def test_upload_tracks_usage_and_delete_frees(self, client_sess, prop_id):
        before = client_sess.get(f"{BASE_URL}/api/storage/usage", timeout=30).json()["personal"]["used_bytes"]
        payload = b"%PDF-1.4 st001 usage tracking test " + b"y" * 4096
        r = client_sess.post(
            f"{BASE_URL}/api/properties/{prop_id}/documents",
            files={"file": ("st001_track.pdf", io.BytesIO(payload), "application/pdf")},
            data={"category": "altele", "title": "ST-001 tracking"},
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        doc_id = r.json()["document"]["id"]
        after = client_sess.get(f"{BASE_URL}/api/storage/usage", timeout=30).json()["personal"]["used_bytes"]
        assert after == before + len(payload), f"usage not incremented: {before} -> {after}"
        # delete → scade
        rd = client_sess.delete(f"{BASE_URL}/api/documents/{doc_id}", timeout=30)
        assert rd.status_code == 200
        final = client_sess.get(f"{BASE_URL}/api/storage/usage", timeout=30).json()["personal"]["used_bytes"]
        assert final == before, f"usage not freed on delete: {before} -> {final}"


class TestSuccessManagerIntegration:
    def test_success_manager_still_works(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/success-manager", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "next_action" in d
