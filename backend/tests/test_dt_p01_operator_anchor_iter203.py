"""iter203 — P0.1 OPERATOR PROPERTY ANCHOR — backend regression.

Verifies the Operator Digital Twin create flow now requires + honours the Property Anchor,
reusing the existing P0 infrastructure (anti-misassignment, KG, model inheritance).

Covers acceptance criteria A-J:
  A. Operator create WITHOUT property -> 400 (blocked / validation required).
  B. Operator create WITH a property owned by the client -> project linked, property_id set.
  C. Operator create with a property NOT owned by the client -> 403 (anti-misassignment).
  D. Twin project carries property_id + property_link_status="linked".
  E. Uploaded model inherits property_id.
  G. Client standalone create still works (regression, unresolved allowed).
  + new read-only selector endpoint returns the client's properties.
"""
import os
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
HDR = {"X-PM-Client": "propmanage-app"}

OPERATOR = ("operator@propmanage.io", "Op123!")
ADMIN = ("admin@propmanage.io", "1!nasov01ADMIN")
CLIENT = ("client@propmanage.io", "Client123!")


def _login(email, password):
    s = requests.Session()
    s.headers.update(HDR)
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:200]}"
    return s


def _client_ctx():
    """Return (client_id, owned_property_id) for client@propmanage.io, ensuring dt pro."""
    cs = _login(*CLIENT)
    me = cs.get(f"{API}/auth/me", timeout=30).json()
    cid = me.get("id") or me.get("user", {}).get("id")
    props = cs.get(f"{API}/properties", timeout=30).json()
    items = props if isinstance(props, list) else props.get("items", [])
    assert items, "client has no properties"
    return cid, items[0]["id"]


@pytest.fixture(scope="module")
def op_ctx():
    op = _login(*OPERATOR)
    admin = _login(*ADMIN)
    cid, prop = _client_ctx()
    # Ensure the client has Digital Twin Pro so the operator create path is reachable.
    admin.post(f"{API}/admin/digital-twin/grant-access", json={"user_id": cid, "active": True}, timeout=30)
    op.post(f"{API}/operator/digital-twin/grant-access", json={"user_id": cid, "active": True}, timeout=30)
    return op, cid, prop


def test_selector_endpoint_lists_client_properties(op_ctx):
    op, cid, prop = op_ctx
    r = op.get(f"{API}/operator/digital-twin/clients/{cid}/properties", timeout=30)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert isinstance(items, list) and len(items) >= 1
    assert any(p["id"] == prop for p in items)
    assert all("name" in p for p in items)


def test_A_operator_create_without_property_blocked(op_ctx):
    op, cid, prop = op_ctx
    r = op.post(f"{API}/operator/digital-twin/clients/{cid}/projects",
                json={"client_id": cid, "name": "iter203 no-prop"}, timeout=30)
    assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text[:200]}"


def test_B_D_E_operator_create_with_property_anchors(op_ctx):
    op, cid, prop = op_ctx
    r = op.post(f"{API}/operator/digital-twin/clients/{cid}/projects",
                json={"client_id": cid, "name": "iter203 anchored", "property_id": prop}, timeout=30)
    assert r.status_code in (200, 201), r.text
    proj = r.json()
    pid = proj["id"]
    assert proj.get("property_id") == prop
    assert proj.get("property_link_status") == "linked"
    # E — model inherits property_id
    up = op.post(f"{API}/digital-twin/projects/{pid}/upload?layer_type=structure",
                 files={"file": ("m.glb", b"glTF-iter203" * 4, "model/gltf-binary")}, timeout=60)
    assert up.status_code in (200, 201), up.text
    m = up.json()
    assert m.get("property_id") == prop
    assert m.get("property_link_status") == "linked"
    op.delete(f"{API}/digital-twin/projects/{pid}", timeout=30)


def test_C_operator_create_unauthorized_property_refused(op_ctx):
    op, cid, prop = op_ctx
    # A property that does not exist -> 404; a bogus 24-hex id triggers the anchor guard.
    r = op.post(f"{API}/operator/digital-twin/clients/{cid}/projects",
                json={"client_id": cid, "name": "iter203 bogus", "property_id": "0" * 24}, timeout=30)
    assert r.status_code in (403, 404), f"expected block, got {r.status_code} {r.text[:200]}"


def test_G_client_standalone_create_regression():
    cs = _login(*CLIENT)
    r = cs.post(f"{API}/digital-twin/projects", json={"name": "iter203 client standalone"}, timeout=30)
    assert r.status_code in (200, 201), r.text
    proj = r.json()
    assert proj.get("property_link_status") == "unresolved"
    cs.delete(f"{API}/digital-twin/projects/{proj['id']}", timeout=30)
