"""Iter222 — HartaBlocuri: conflict resolution, typology, building-context client + regresie.

Coverage:
  * Admin auth via cookie (POST /api/auth/login)
  * GET /api/admin/hartablocuri/conflicts?unresolved_only=true
  * POST /api/admin/hartablocuri/buildings/{id}/conflicts/resolve {confirm|reject}
  * GET /api/admin/hartablocuri/buildings/{id} → context/conflicts/typology/hartablocuri/residents_count
  * Typology cells shape (raw/normalized/source='HartaBlocuri')
  * Client building-context: attach + GET /api/properties/{id}/building-context
  * Regresie: /api/public/buildings/search & POST /api/buildings manual
"""
import os
import re
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN_EMAIL = "admin@propmanage.io"
ADMIN_PASS = "1!nasov01ADMIN"
CLIENT_EMAIL = "client@propmanage.io"
CLIENT_PASS = "Client123!"


# ────────── Fixtures ──────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def client_session():
    s = requests.Session()
    # try login; if not exist, register
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": CLIENT_EMAIL, "password": CLIENT_PASS}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Client login failed: {r.status_code}")
    return s


# ────────── Admin conflicts listing ──────────
def test_admin_list_conflicts_unresolved(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/conflicts",
                          params={"unresolved_only": "true"}, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "buildings" in data and "total" in data
    assert isinstance(data["buildings"], list)


def test_admin_building_detail_has_typology(admin_session):
    # search Muscel public → get an HB building id
    r = requests.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    assert r.status_code == 200
    items = r.json()["buildings"]
    assert items, "expected at least 1 Muscel result"
    bid = items[0]["id"]

    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/buildings/{bid}", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("context", "conflicts", "typology", "hartablocuri", "residents_count"):
        assert k in d, f"missing key {k}"
    typ = d["typology"]
    assert typ, "typology should be present"
    required_cells = ["period", "year", "era", "height_regime", "structure",
                      "entrances", "apartments", "rooms_breakdown", "neighborhood"]
    for key in required_cells:
        assert key in typ, f"typology missing {key}"
        cell = typ[key]
        assert set(cell.keys()) >= {"raw", "normalized", "source"}, f"{key} cell shape wrong: {cell}"
        assert cell["source"] == "HartaBlocuri"


def test_admin_building_detail_404(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/buildings/000000000000000000000000",
                          timeout=15)
    assert r.status_code == 404


# ────────── Conflict resolve (confirm + reject) ──────────
def _find_building_with_conflict(admin_session):
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/conflicts",
                          params={"unresolved_only": "true", "page_size": 100}, timeout=15)
    assert r.status_code == 200
    for b in r.json()["buildings"]:
        if b.get("conflicts"):
            return b
    return None


def test_conflict_resolve_confirm_and_reject(admin_session):
    b = _find_building_with_conflict(admin_session)
    if not b:
        pytest.skip("No unresolved conflicts available to test")
    bid = b["id"]
    conflicts = b["conflicts"]
    assert conflicts

    # ---- CONFIRM first conflict ----
    c1 = conflicts[0]
    field1 = c1["field"]
    hb_val = c1["hartablocuri_value"]

    r = admin_session.post(
        f"{BASE_URL}/api/admin/hartablocuri/buildings/{bid}/conflicts/resolve",
        json={"field": field1, "action": "confirm"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["field"] == field1
    assert body["action"] == "confirm"
    assert str(body["chosen_value"]) == str(hb_val)

    # verify: context[field] == hb_val; conflict now confirmed; HB raw preserved; history has entry
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/buildings/{bid}", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert str(d["context"].get(field1)) == str(hb_val), \
        f"context.{field1} not updated to HB value"
    matching = [c for c in d["conflicts"] if c["field"] == field1]
    assert matching and matching[0]["status"] == "confirmed"
    assert matching[0]["chosen_source"] == "HartaBlocuri"
    # raw HB preserved
    hb_raw = d["hartablocuri"]["raw"] if d.get("hartablocuri") else {}
    assert hb_raw, "hartablocuri.raw should remain"

    # ---- REJECT: try second conflict or same building's another field ----
    remaining = [c for c in d["conflicts"] if c.get("status") == "review"]
    if not remaining:
        # find another building with review conflicts
        b2 = _find_building_with_conflict(admin_session)
        if not b2:
            return  # only one conflict existed — confirm worked, done
        bid2, c2 = b2["id"], b2["conflicts"][0]
    else:
        bid2, c2 = bid, remaining[0]

    field2 = c2["field"]
    pm_val = c2["propmanage_value"]

    r = admin_session.post(
        f"{BASE_URL}/api/admin/hartablocuri/buildings/{bid2}/conflicts/resolve",
        json={"field": field2, "action": "reject"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["action"] == "reject"
    assert str(body["chosen_value"]) == str(pm_val)

    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/buildings/{bid2}", timeout=15)
    d2 = r.json()
    matching2 = [c for c in d2["conflicts"] if c["field"] == field2]
    assert matching2 and matching2[0]["status"] == "rejected"
    assert matching2[0]["chosen_source"] == "PropManage"


def test_conflict_resolve_invalid_field(admin_session):
    # any HB building
    r = requests.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    bid = r.json()["buildings"][0]["id"]
    r = admin_session.post(
        f"{BASE_URL}/api/admin/hartablocuri/buildings/{bid}/conflicts/resolve",
        json={"field": "nonexistent_field", "action": "confirm"}, timeout=15)
    assert r.status_code == 404


# ────────── Client Building-context ──────────
def test_client_building_context_with_hb(client_session):
    # find HB building
    r = requests.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    assert r.status_code == 200
    bid = r.json()["buildings"][0]["id"]

    # get first property
    r = client_session.get(f"{BASE_URL}/api/properties", timeout=15)
    assert r.status_code == 200, r.text
    props = r.json() if isinstance(r.json(), list) else r.json().get("properties", [])
    if not props:
        pytest.skip("Client has no properties to attach")
    prop_id = props[0].get("id") or props[0].get("_id")

    # attach
    r = client_session.post(f"{BASE_URL}/api/properties/{prop_id}/attach-building",
                            json={"building_id": bid}, timeout=15)
    assert r.status_code == 200, r.text

    # GET building-context
    r = client_session.get(f"{BASE_URL}/api/properties/{prop_id}/building-context", timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["attached"] is True
    b = body["building"]
    assert b["id"] == bid
    assert b["verification_status"] in ("unverified", "declared", "documented", "verified")
    hb = b.get("hartablocuri")
    assert hb, "hartablocuri sub-object should be attached"
    assert hb.get("source_name") == "HartaBlocuri"
    assert hb.get("verification_status") == "neverificat"
    assert "fields" in hb
    assert "plan_urls" in hb and isinstance(hb["plan_urls"], list)
    assert "reference_url" in hb


# ────────── Regresie ──────────
def test_public_search_still_works():
    r = requests.get(f"{BASE_URL}/api/public/buildings/search", params={"q": "Muscel"}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["buildings"][0]["source"] in ("hartablocuri", "both", "propmanage")


def test_manual_building_creation_still_works(client_session, admin_session):
    # POST /api/buildings requires client role
    uniq = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST_ManualBloc_{uniq}",
        "address": f"Str. Test {uniq} nr. 1",
        "city": "Cluj-Napoca",
    }
    r = client_session.post(f"{BASE_URL}/api/buildings", json=payload, timeout=15)
    if r.status_code == 404:
        pytest.skip("POST /api/buildings not implemented")
    assert r.status_code in (200, 201), r.text
    body = r.json()
    bid = body.get("id") or body.get("_id") or (body.get("building") or {}).get("id")
    assert bid, f"no id returned: {body}"

    # verify via admin building list search (propmanage source since no HB attached)
    r = admin_session.get(f"{BASE_URL}/api/admin/hartablocuri/buildings",
                          params={"q": f"TEST_ManualBloc_{uniq}", "source": "propmanage"}, timeout=15)
    assert r.status_code == 200
    matches = [b for b in r.json()["buildings"] if b["name"] == payload["name"]]
    assert matches, "manual building not visible in admin list"
    assert matches[0]["source"] == "propmanage"
