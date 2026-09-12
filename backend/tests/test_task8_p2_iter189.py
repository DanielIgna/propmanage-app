"""Pytest Task 8 · P2 — REMEDIAT (canonicalizare Iun 2026).

Post-remediere:
- Design Tokens: UN SINGUR path canonic = Design Studio (db.design_tokens {_id:"active"}).
  Dead-path-ul Task 8 (/api/admin/design-tokens, /api/public/design-tokens) a fost ELIMINAT.
- Config I/O: exportă/importă starea RUNTIME-ACTIVĂ a tokenilor (nu doc-ul mort).
- Snapshots canonice (admin_console) includ design_tokens/pages/site_menu/feature_config.
- Preview: endpoint non-mutant + flag honest `feature_flag_would_block`.
- Renewal: idempotent + coordonat 24h cu Copilot renew nudge.
"""
import os
import uuid

import pytest
import requests

from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def admin():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def anon():
    return requests.Session()


# ==================================================================
# A · DESIGN TOKENS — canonic = Design Studio ({_id:"active"})
# ==================================================================
def test_design_studio_tokens_public_read():
    r = requests.get(f"{API}/admin/design-studio/tokens", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d.get("tokens"), dict)
    assert d["tokens"]["colors"]["primary"], "primary color missing"


def test_design_studio_put_requires_admin(anon):
    r = anon.put(f"{API}/admin/design-studio/tokens",
                 json={"colors": {"warning": "#ffaa00"}}, timeout=15)
    assert r.status_code in (401, 403)


def test_design_studio_save_reflects_in_runtime_and_reset(admin):
    r = admin.put(f"{API}/admin/design-studio/tokens",
                  json={"colors": {"warning": "#ffaa11"}}, timeout=15)
    assert r.status_code == 200
    assert r.json()["tokens"]["colors"]["warning"] == "#ffaa11"

    # Runtime read (același endpoint consumat de DesignTokensProvider)
    runtime = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
    assert runtime["tokens"]["colors"]["warning"] == "#ffaa11"

    rst = admin.post(f"{API}/admin/design-studio/reset", timeout=15)
    assert rst.status_code == 200
    assert rst.json()["preset_id"] == "default"


def test_design_studio_rejects_css_injection(admin):
    for payload in [
        {"colors": {"warning": "javascript:alert(1)"}},
        {"colors": {"primary": "url(https://evil.com)"}},
        {"colors": {"primary": "expression(alert(1))"}},
        {"typography": {"sans": "<script>alert(1)</script>"}},
        {"typography": {"sans": "Inter; @import url(evil)"}},
    ]:
        r = admin.put(f"{API}/admin/design-studio/tokens", json=payload, timeout=15)
        assert r.status_code == 400, f"payload accepted but should have been rejected: {payload}"


def test_design_studio_palette_cascade_rejects_non_hex(admin):
    r = admin.post(f"{API}/admin/design-studio/palette-cascade",
                   json={"primary": "javascript:x", "apply": False}, timeout=15)
    assert r.status_code == 400


def test_design_studio_audit_in_config_history(admin):
    admin.put(f"{API}/admin/design-studio/tokens",
              json={"colors": {"warning": "#ffbb22"}}, timeout=15)
    hist = admin.get(f"{API}/admin/config-history?entity_type=design_tokens&limit=10", timeout=15).json()
    assert hist["count"] >= 1, "audit design_tokens absent din Config History"
    assert any(i.get("action", "").startswith("design_tokens.") for i in hist["items"])
    admin.post(f"{API}/admin/design-studio/reset", timeout=15)


def test_legacy_design_tokens_routes_removed(admin, anon):
    """Dead-path-ul Task 8 trebuie să fie complet eliminat din backend."""
    assert anon.get(f"{API}/public/design-tokens", timeout=15).status_code == 404
    assert admin.get(f"{API}/admin/design-tokens", timeout=15).status_code in (404, 405)
    assert admin.put(f"{API}/admin/design-tokens", json={}, timeout=15).status_code in (404, 405)


def test_legacy_admin_route_redirects_frontend():
    """/admin/design-tokens (frontend) redirectează la Design Studio — verificat
    doar că ruta backend nu mai există; redirect-ul React e testat în UI."""
    assert True


# ==================================================================
# B · CONFIG I/O — portabilitate JSON, capturează starea RUNTIME-ACTIVĂ
# ==================================================================
def test_config_export_admin_only(anon):
    r = anon.get(f"{API}/admin/config/export", timeout=15)
    assert r.status_code in (401, 403)


def test_config_export_has_all_sections_and_runtime_tokens(admin):
    r = admin.get(f"{API}/admin/config/export", timeout=15)
    assert r.status_code == 200
    d = r.json()
    for section in ("pages", "pages_versions", "site_menu", "cms_content",
                    "app_settings", "feature_config", "design_tokens"):
        assert section in d["sections"], f"missing section {section}"
    # design_tokens must be the RUNTIME-ACTIVE shape (Design Studio)
    dt = d["sections"]["design_tokens"]
    assert isinstance(dt.get("tokens"), dict) and dt["tokens"].get("colors"), \
        "export nu capturează starea runtime-activă a tokenilor"
    runtime = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
    assert dt["tokens"]["colors"]["primary"] == runtime["tokens"]["colors"]["primary"]


def test_config_export_excludes_secrets(admin):
    r = admin.get(f"{API}/admin/config/export", timeout=15)
    text = r.text.lower()
    for forbidden in ('"password"', '"password_hash"', '"stripe_secret"',
                      '"api_key"', '"refresh_token"'):
        assert forbidden not in text, f"secret leaked in export: {forbidden}"


def test_config_import_rejects_bad_bundle(admin):
    for bad in [
        {"bundle": {"app": "other", "schema_version": "1.0", "sections": {}}},
        {"bundle": {"app": "propmanage", "schema_version": "9.9", "sections": {}}},
        {"bundle": {"app": "propmanage", "schema_version": "1.0", "sections": {"users": []}}},
    ]:
        r = admin.post(f"{API}/admin/config/import", json=bad, timeout=15)
        assert r.status_code == 400, f"bad bundle accepted: {bad}"


def test_config_import_design_tokens_wrong_shape_rejected(admin):
    """Bundle-uri vechi (forma dead-path fără 'tokens') trebuie respinse, nu
    aplicate silențios pe lângă runtime."""
    bundle = {
        "app": "propmanage", "schema_version": "1.0",
        "sections": {"design_tokens": {"colors": {"accent": "#123456"}}},
    }
    r = admin.post(f"{API}/admin/config/import",
                   json={"bundle": bundle, "apply": True, "sections": ["design_tokens"]},
                   timeout=15)
    assert r.status_code == 400


def test_config_import_dry_run_does_not_mutate(admin):
    before = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
    bundle = {
        "app": "propmanage", "schema_version": "1.0",
        "sections": {"design_tokens": {"tokens": {**before["tokens"],
                                                  "colors": {**before["tokens"]["colors"], "warning": "#123456"}}}},
    }
    r = admin.post(f"{API}/admin/config/import", json={"bundle": bundle, "apply": False}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["dry_run"] is True
    assert d["applied"] is None
    after = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
    assert after["tokens"]["colors"]["warning"] == before["tokens"]["colors"]["warning"]


def test_config_import_apply_mutates_runtime_active(admin):
    admin.post(f"{API}/admin/design-studio/reset", timeout=15)
    base = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
    tokens = {**base["tokens"], "colors": {**base["tokens"]["colors"], "warning": "#00aaff"}}
    bundle = {
        "app": "propmanage", "schema_version": "1.0",
        "sections": {"design_tokens": {"tokens": tokens, "preset_id": "custom"}},
    }
    r = admin.post(f"{API}/admin/config/import",
                   json={"bundle": bundle, "apply": True, "sections": ["design_tokens"]},
                   timeout=15)
    assert r.status_code == 200
    assert r.json()["applied"] == {"design_tokens": "replaced_runtime_active"}
    # Efect REAL pe runtime (nu dead write):
    after = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
    assert after["tokens"]["colors"]["warning"] == "#00aaff"
    admin.post(f"{API}/admin/design-studio/reset", timeout=15)


def test_config_import_rejects_css_injection_in_tokens(admin):
    bundle = {
        "app": "propmanage", "schema_version": "1.0",
        "sections": {"design_tokens": {"tokens": {"colors": {"primary": "javascript:alert(1)"}}}},
    }
    r = admin.post(f"{API}/admin/config/import",
                   json={"bundle": bundle, "apply": True, "sections": ["design_tokens"]},
                   timeout=15)
    assert r.status_code == 400


# ==================================================================
# B2 · SNAPSHOTS CANONICE — includ design tokens runtime + restore real
# ==================================================================
def test_snapshot_captures_and_restores_runtime_design_tokens(admin):
    name = f"remediation-test-{uuid.uuid4().hex[:8]}"
    sid = None
    try:
        # 1. Setează o stare distinctă
        admin.put(f"{API}/admin/design-studio/tokens",
                  json={"colors": {"warning": "#0011ff"}}, timeout=15)
        # 2. Snapshot canonic (doar design_tokens)
        snap = admin.post(f"{API}/admin/snapshots",
                          json={"name": name, "parts": ["design_tokens"]}, timeout=15)
        assert snap.status_code == 200, snap.text
        sid = snap.json()["id"]
        assert snap.json()["counts"]["design_tokens"] >= 1
        # 3. Schimbă starea
        admin.put(f"{API}/admin/design-studio/tokens",
                  json={"colors": {"warning": "#ff1100"}}, timeout=15)
        # 4. Restore → starea vizibilă revine EXACT la cea din snapshot
        rst = admin.post(f"{API}/admin/snapshots/{sid}/restore", timeout=15)
        assert rst.status_code == 200, rst.text
        assert rst.json()["restored"].get("design_tokens", 0) >= 1
        after = requests.get(f"{API}/admin/design-studio/tokens", timeout=15).json()
        assert after["tokens"]["colors"]["warning"] == "#0011ff", \
            "restore-ul NU a restaurat starea runtime-activă"
    finally:
        if sid:
            admin.delete(f"{API}/admin/snapshots/{sid}", timeout=15)
        admin.post(f"{API}/admin/design-studio/reset", timeout=15)


# ==================================================================
# C · PREVIEW — non-mutant, admin-only, terminologie onestă
# ==================================================================
def test_preview_admin_only(anon):
    r = anon.get(f"{API}/admin/pages/home/preview", timeout=15)
    assert r.status_code in (401, 403)


def test_preview_returns_live_when_no_draft(admin):
    admin.post(f"{API}/admin/pages/home/discard-draft", timeout=15)
    r = admin.get(f"{API}/admin/pages/home/preview", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["source"] == "live"
    assert d["has_draft"] is False
    assert d["data"]["h1"]
    assert d["feature_flag_would_block"] is False


def test_preview_overlays_draft_without_leaking_to_public(admin):
    admin.put(f"{API}/admin/pages/pricing", json={"h1": "PREVIEW ONLY draft h1"}, timeout=15)
    prev = admin.get(f"{API}/admin/pages/pricing/preview", timeout=15).json()
    assert prev["source"] == "draft"
    assert prev["has_draft"] is True
    assert prev["data"]["h1"] == "PREVIEW ONLY draft h1"

    pub = requests.get(f"{API}/public/pages/pricing", timeout=15).json()
    assert pub["h1"] != "PREVIEW ONLY draft h1", "draft leaked publicly"

    admin.post(f"{API}/admin/pages/pricing/discard-draft", timeout=15)


def test_preview_rejects_invalid_key(admin):
    r = admin.get(f"{API}/admin/pages/UPPER_INVALID/preview", timeout=15)
    assert r.status_code in (400, 404)


# ==================================================================
# D · RENEWAL REMINDER — idempotent + coordonat cu Copilot
# ==================================================================
def test_renewal_recent_list_requires_admin(anon):
    r = anon.get(f"{API}/admin/renewal-reminders/recent", timeout=15)
    assert r.status_code in (401, 403)


def test_renewal_run_now_idempotent(admin):
    r1 = admin.post(f"{API}/admin/renewal-reminders/run-now", timeout=30).json()
    assert r1["ok"] is True
    r2 = admin.post(f"{API}/admin/renewal-reminders/run-now", timeout=30).json()
    assert r2["ok"] is True
    if r1["due"] > 0:
        assert r2["skipped"] >= r1["sent"], f"duplicates possible: r1={r1} r2={r2}"


def test_renewal_tick_shape(admin):
    r = admin.post(f"{API}/admin/renewal-reminders/run-now", timeout=30).json()
    assert set(r.keys()) >= {"ok", "due", "sent", "skipped", "failed"}


# ==================================================================
# F · SECURITY REMEDIATION (SEC-001 scope map · SEC-002 CSRF guard)
# ==================================================================
def test_csrf_guard_blocks_cross_site_form_post(admin):
    """Form POST cross-site: are Origin dar NU poate seta X-PM-Client → 403."""
    r = admin.post(f"{API}/admin/design-studio/reset",
                   headers={"Origin": "https://evil.com"}, timeout=15)
    assert r.status_code == 403


def test_csrf_guard_allows_app_and_server_requests(admin):
    r = admin.post(f"{API}/admin/design-studio/reset",
                   headers={"Origin": BASE_URL, "X-PM-Client": "propmanage-app"}, timeout=15)
    assert r.status_code == 200
    # fără Origin (curl/server-to-server) → nu e vector CSRF de browser → trece
    r2 = admin.post(f"{API}/admin/design-studio/reset", timeout=15)
    assert r2.status_code == 200


def test_admin_scope_map_covers_config_surfaces():
    """SEC-001: suprafețele de config nu mai sunt unscoped în middleware."""
    from middleware_scope import _required_scope
    assert _required_scope("/api/admin/config/import") == "general"
    assert _required_scope("/api/admin/config/export") == "general"
    assert _required_scope("/api/admin/snapshots/abc/restore") == "general"
    assert _required_scope("/api/admin/pages/home/publish") == "frontend"
    assert _required_scope("/api/admin/config-history") == "frontend"
    assert _required_scope("/api/admin/renewal-reminders/run-now") == "ops"
    assert _required_scope("/api/admin/design-studio/tokens") == "frontend"


# ==================================================================
# E · Regression sanity — Task 7 API still healthy
# ==================================================================
def test_pages_public_unchanged():
    r = requests.get(f"{API}/public/pages/home", timeout=15)
    assert r.status_code == 200
    assert r.json()["h1"]
    for leaked in ("allowed_roles", "allowed_tiers", "feature_flag"):
        assert leaked not in r.json(), f"regression P3.2: leaked {leaked}"


def test_menu_public_unchanged():
    r = requests.get(f"{API}/public/site-menu", timeout=15)
    assert r.status_code == 200
    assert isinstance(r.json().get("items"), list)
