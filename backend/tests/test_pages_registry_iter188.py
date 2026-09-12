"""Pytest for Page Registry (Task 7 P0+P1) — sync via requests, aligned with existing suite.

Covers:
- bootstrap seed of pages
- list + get + PUT draft + publish + discard + restore + reset
- LIVE vs DRAFT separation (public endpoint always returns LIVE)
- monotonically increasing version (never resets on restore→publish)
- backward fallback to app_settings.seo
- config-history unified view
- site_menu.page_key backward compatibility (menu still saves + public still loads)
- public key validator
"""
import os
from datetime import datetime, timezone

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


# ------------------------------------------------------------------
# Bootstrap + list
# ------------------------------------------------------------------
def test_bootstrap_and_list(admin):
    r = admin.get(f"{API}/admin/pages", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 15, data
    keys = {p["key"] for p in data["items"]}
    for expected in ["home", "pricing", "whyus", "estate", "digital_twin",
                     "marketplace", "login", "register", "privacy", "terms"]:
        assert expected in keys, f"missing seed key: {expected}"
    for p in data["items"]:
        assert p["status"] in {"active", "hidden", "draft"}
        assert p["route"].startswith("/")


def test_public_endpoint_returns_live_only(admin):
    # baseline LIVE
    r = requests.get(f"{API}/public/pages/home", timeout=15)
    assert r.status_code == 200
    baseline = r.json()

    # write a draft that changes seo_title
    dr = admin.put(f"{API}/admin/pages/home", json={"seo_title": "DRAFT ONLY — should not be public"}, timeout=15)
    assert dr.status_code == 200
    assert dr.json()["has_draft"] is True

    # public still returns LIVE
    r2 = requests.get(f"{API}/public/pages/home", timeout=15)
    assert r2.status_code == 200
    assert r2.json()["seo_title"] == baseline["seo_title"], "PUBLIC leaked DRAFT"

    admin.post(f"{API}/admin/pages/home/discard-draft", timeout=15)


def test_publish_creates_version_and_updates_live(admin):
    key = "pricing"
    baseline = requests.get(f"{API}/public/pages/{key}", timeout=15).json()
    baseline_version = baseline["version"]

    new_title = f"Test SEO {datetime.now(timezone.utc).isoformat()}"
    r = admin.put(f"{API}/admin/pages/{key}", json={"seo_title": new_title}, timeout=15)
    assert r.status_code == 200

    pub = admin.post(f"{API}/admin/pages/{key}/publish", timeout=15)
    assert pub.status_code == 200
    body = pub.json()
    assert body["ok"] is True
    assert body["version"] == baseline_version + 1

    live = requests.get(f"{API}/public/pages/{key}", timeout=15).json()
    assert live["seo_title"] == new_title
    assert live["version"] == baseline_version + 1

    vh = admin.get(f"{API}/admin/pages/{key}/versions", timeout=15)
    assert vh.status_code == 200
    assert vh.json()["count"] >= 1

    # Monotonic version on restore→publish.
    prev_version = vh.json()["items"][0]["version"]
    restore = admin.post(f"{API}/admin/pages/{key}/restore/{prev_version}", timeout=15)
    assert restore.status_code == 200
    assert restore.json()["restored_into_draft"] is True

    pub2 = admin.post(f"{API}/admin/pages/{key}/publish", timeout=15)
    assert pub2.status_code == 200
    assert pub2.json()["version"] == baseline_version + 2, "version must NOT reset on restore→publish"


def test_discard_draft(admin):
    admin.put(f"{API}/admin/pages/whyus", json={"h1": "TEMP DRAFT"}, timeout=15)
    d = admin.post(f"{API}/admin/pages/whyus/discard-draft", timeout=15)
    assert d.status_code == 200
    assert d.json()["ok"] is True
    p = admin.get(f"{API}/admin/pages/whyus", timeout=15).json()
    assert p["draft"] is None


def test_reset_page_to_defaults(admin):
    key = "estate"
    admin.put(f"{API}/admin/pages/{key}", json={"h1": "MUTATED"}, timeout=15)
    admin.post(f"{API}/admin/pages/{key}/publish", timeout=15)
    live = requests.get(f"{API}/public/pages/{key}", timeout=15).json()
    assert live["h1"] == "MUTATED"

    r = admin.post(f"{API}/admin/pages/{key}/reset", timeout=15)
    assert r.status_code == 200
    live2 = requests.get(f"{API}/public/pages/{key}", timeout=15).json()
    assert live2["h1"] != "MUTATED"


def test_backward_fallback_to_app_settings(admin):
    """When LIVE.seo_title is empty but seo_key exists, fallback to app_settings.seo.home_title."""
    key = "home"
    admin.put(f"{API}/admin/pages/{key}", json={"seo_title": ""}, timeout=15)
    admin.post(f"{API}/admin/pages/{key}/publish", timeout=15)

    live = requests.get(f"{API}/public/pages/{key}", timeout=15).json()
    assert live["seo_title"], "backward fallback to app_settings failed"

    admin.post(f"{API}/admin/pages/{key}/reset", timeout=15)


def test_role_tier_device_visibility(admin):
    r = admin.put(f"{API}/admin/pages/marketplace", json={
        "allowed_roles": ["client", "specialist"],
        "allowed_tiers": ["verified", "pro"],
        "desktop_visible": True,
        "mobile_visible": False,
    }, timeout=15)
    assert r.status_code == 200
    fresh = admin.get(f"{API}/admin/pages/marketplace", timeout=15).json()
    d = fresh["draft"]
    assert d["allowed_roles"] == ["client", "specialist"]
    assert d["allowed_tiers"] == ["verified", "pro"]
    assert d["mobile_visible"] is False

    admin.post(f"{API}/admin/pages/marketplace/discard-draft", timeout=15)


def test_config_history_view(admin):
    admin.put(f"{API}/admin/pages/community", json={"h1": "hist test"}, timeout=15)
    r = admin.get(f"{API}/admin/config-history?limit=5&entity_type=page", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    for item in data["items"]:
        assert item["target"]["type"] == "page"
    admin.post(f"{API}/admin/pages/community/discard-draft", timeout=15)


def test_menu_page_key_backward_compat(admin):
    """site_menu items may or may not have page_key. Adding one must not break menu load."""
    menu = admin.get(f"{API}/admin/site-menu", timeout=15).json()
    items = menu["items"]
    changed = False
    for group in items:
        for child in (group.get("children") or []):
            if not child.get("page_key"):
                child["page_key"] = "home"
                changed = True
                break
        if changed:
            break
    if changed:
        r = admin.put(f"{API}/admin/site-menu", json={"items": items}, timeout=15)
        assert r.status_code == 200

    pub = requests.get(f"{API}/public/site-menu", timeout=15)
    assert pub.status_code == 200
    assert pub.json()["items"]


def test_public_key_validator():
    """Invalid page keys must not resolve — either 400 or 404."""
    r = requests.get(f"{API}/public/pages/../etc/passwd", timeout=15)
    assert r.status_code in (400, 404)
    r2 = requests.get(f"{API}/public/pages/UPPERCASE", timeout=15)
    assert r2.status_code in (400, 404)


# ------------------------------------------------------------------
# Task 7.1 · Security fixes
# ------------------------------------------------------------------
def test_sec001_config_history_scope_enforced_with_actor(admin):
    """SEC-001: config-history MUST always constrain to config-surface target types,
    even when caller supplies an `actor` filter (previous bug: actor filter bypassed scope).
    """
    r = admin.get(f"{API}/admin/config-history?limit=50&actor=admin@propmanage.io", timeout=15)
    assert r.status_code == 200
    data = r.json()
    allowed = {"page", "cms_key", "menu", "app_settings", "feature", "feature_config",
               "design_tokens", "config_io", "snapshot", "renewal_reminder"}
    for item in data["items"]:
        t = (item.get("target") or {}).get("type")
        assert t in allowed, f"config-history leaked non-config entry with target.type={t!r}"


def test_sec002_feature_flag_off_page_returns_404(admin):
    """SEC-002: a public page whose feature_flag is OFF in feature_config MUST 404."""
    # 1. Publish a page with feature_flag pointing at a known key.
    flag_key = "client_early_access"  # exists in DEFAULT_FEATURES; we'll toggle OFF.
    admin.put(f"{API}/admin/pages/community", json={"feature_flag": flag_key}, timeout=15)
    admin.post(f"{API}/admin/pages/community/publish", timeout=15)

    # 2. Toggle the feature flag OFF.
    r_flag = admin.put(f"{API}/admin/feature-configurator/config/feature",
                       json={"key": flag_key, "enabled": False}, timeout=15)
    assert r_flag.status_code == 200

    # 3. Public MUST 404.
    pub = requests.get(f"{API}/public/pages/community", timeout=15)
    assert pub.status_code == 404, f"feature_flag OFF page still exposed publicly: {pub.status_code}"

    # 4. Cleanup: turn feature back ON and unset flag.
    admin.put(f"{API}/admin/feature-configurator/config/feature",
              json={"key": flag_key, "enabled": True}, timeout=15)
    admin.put(f"{API}/admin/pages/community", json={"feature_flag": ""}, timeout=15)
    admin.post(f"{API}/admin/pages/community/publish", timeout=15)


def test_p3_public_payload_omits_access_rules():
    """Public payload MUST NOT expose internal access rules (allowed_roles,
    allowed_tiers, feature_flag key name)."""
    r = requests.get(f"{API}/public/pages/home", timeout=15)
    assert r.status_code == 200
    data = r.json()
    for leaked in ("allowed_roles", "allowed_tiers", "feature_flag", "feature_flag_state"):
        assert leaked not in data, f"public payload leaked '{leaked}'"
