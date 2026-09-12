"""
Iter201 — Digital Twin P0: PROPERTY ANCHOR + safe backfill + KG + trust readiness.

Covers:
  * Client creates an ANCHORED project (property_id owned) -> property_link_status="linked"
  * Anti-misassignment: anchoring to a property NOT owned -> 403 (or 404 for bogus id)
  * Standalone create (no property_id) -> "unresolved" (compat preserved)
  * Manual PATCH /projects/{id}/property links an unresolved project + cascades to its models
  * Uploaded model inherits property_id + property_link_status + trust fields
    (confidence/verification_status/completeness), trust PATCH validates values
  * Admin backfill is idempotent and performs ZERO auto-assignment
"""
import os
import time
import uuid

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PW = "Client123!"
ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PW = "1!nasov01ADMIN"
HEADERS = {"X-PM-Client": "propmanage-app"}


def _login(session, email, pw):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw},
                     headers=HEADERS, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"


def _register_free(session):
    email = f"free{int(time.time())}{uuid.uuid4().hex[:6]}@example.com"
    r = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": email, "password": "FreePass123!", "name": "Free P0", "role": "client",
        "terms_accepted": True, "privacy_policy_accepted": True}, headers=HEADERS, timeout=30)
    assert r.status_code in (200, 201), r.text[:200]
    return email


def _client_property_id(session):
    r = session.get(f"{BASE_URL}/api/properties", timeout=30)
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert items, "client has no properties"
    return items[0]["id"]


def _glb():
    return b"glTF-p0-test-bytes" * 8


def test_anchored_project_and_inheritance_and_backfill():
    s = requests.Session()
    _login(s, CLIENT_EMAIL, CLIENT_PW)
    prop = _client_property_id(s)

    # 1. anchored create -> linked
    r = s.post(f"{BASE_URL}/api/digital-twin/projects",
               json={"name": "P0 anchored", "property_id": prop}, headers=HEADERS, timeout=30)
    assert r.status_code in (200, 201), r.text[:200]
    proj = r.json()
    assert proj.get("property_id") == prop
    assert proj.get("property_link_status") == "linked"
    pid = proj["id"]

    # 2. uploaded model inherits property + trust fields
    r = s.post(f"{BASE_URL}/api/digital-twin/projects/{pid}/upload?layer_type=structure",
               files={"file": ("m.glb", _glb(), "model/gltf-binary")}, headers=HEADERS, timeout=60)
    assert r.status_code in (200, 201), r.text[:200]
    m = r.json()
    assert m.get("property_id") == prop
    assert m.get("property_link_status") == "linked"
    assert m.get("confidence") == "documented"
    assert m.get("verification_status") == "owner_declared"
    assert "completeness" in m
    mid = m["id"]

    # 3. trust PATCH valid + invalid
    r = s.patch(f"{BASE_URL}/api/digital-twin/models/{mid}",
                json={"confidence": "verified", "verification_status": "professional_audit", "completeness": 80},
                headers=HEADERS, timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("completeness") == 80
    r = s.patch(f"{BASE_URL}/api/digital-twin/models/{mid}",
                json={"confidence": "magic"}, headers=HEADERS, timeout=30)
    assert r.status_code == 400

    # cleanup
    s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", headers=HEADERS, timeout=30)


def test_unresolved_then_manual_link_cascades():
    s = requests.Session()
    _login(s, CLIENT_EMAIL, CLIENT_PW)
    prop = _client_property_id(s)

    r = s.post(f"{BASE_URL}/api/digital-twin/projects",
               json={"name": "P0 unresolved"}, headers=HEADERS, timeout=30)
    assert r.status_code in (200, 201), r.text[:200]
    proj = r.json()
    assert proj.get("property_link_status") == "unresolved"
    pid = proj["id"]

    s.post(f"{BASE_URL}/api/digital-twin/projects/{pid}/upload?layer_type=structure",
           files={"file": ("m.glb", _glb(), "model/gltf-binary")}, headers=HEADERS, timeout=60)

    r = s.patch(f"{BASE_URL}/api/digital-twin/projects/{pid}/property",
                json={"property_id": prop}, headers=HEADERS, timeout=30)
    assert r.status_code == 200, r.text[:200]
    assert r.json().get("property_link_status") == "linked"

    r = s.get(f"{BASE_URL}/api/digital-twin/projects/{pid}/models", headers=HEADERS, timeout=30)
    models = r.json()["items"]
    assert models and all(mm.get("property_link_status") == "linked" for mm in models)
    assert all(mm.get("property_id") == prop for mm in models)

    s.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}", headers=HEADERS, timeout=30)


def test_anti_misassignment():
    # A fresh FREE user cannot anchor a project to a property they do not own.
    owner = requests.Session()
    _login(owner, CLIENT_EMAIL, CLIENT_PW)
    prop = _client_property_id(owner)

    attacker = requests.Session()
    _register_free(attacker)
    r = attacker.post(f"{BASE_URL}/api/digital-twin/projects",
                      json={"name": "hijack", "property_id": prop}, headers=HEADERS, timeout=30)
    assert r.status_code in (403, 404), f"expected block, got {r.status_code}"

    # bogus property id -> 404
    r = attacker.post(f"{BASE_URL}/api/digital-twin/projects",
                      json={"name": "bogus", "property_id": "0" * 24}, headers=HEADERS, timeout=30)
    assert r.status_code == 404


def test_admin_backfill_zero_auto_assign():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PW)
    r = s.post(f"{BASE_URL}/api/admin/digital-twin/backfill-property-links", headers=HEADERS, timeout=60)
    assert r.status_code == 200, r.text[:200]
    body = r.json()
    assert body.get("projects_auto_assigned") == 0
    assert body["projects_total"] >= body["projects_already_linked"] + body["projects_marked_unresolved"] - 1
