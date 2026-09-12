"""iter202 — P1 UNIFIED PROPERTY DIGITAL TWIN — backend regression.

Self-provisioning: creates its own anchored 3D projects for the target property and
tears them down, so it does NOT depend on manually seeded demo data.

Covers:
  - GET /api/properties/{id}/digital-twin unified overview shape + values
  - Authz: 403 for foreign FREE user, 404 for bogus property id.
  - GET /api/digital-twin/projects?property_id=... filter.
  - Backward compat: no-filter list returns caller's full projects.
  - Regression: /twin and /spaces still work.
"""
import os
import time
import uuid

import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
HDR = {"X-PM-Client": "propmanage-app"}
PROP_ID = "6a11d70e600be19667009c93"  # Skyline Loft A4, owned by client@propmanage.io


def _login(email: str, password: str) -> requests.Session:
    s = requests.Session()
    s.headers.update(HDR)
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def anchored_projects():
    """Create 2 property-anchored 3D projects (each with a model) and clean them up."""
    s = _login("client@propmanage.io", "Client123!")
    ids = []
    for i in range(2):
        r = s.post(f"{API}/digital-twin/projects",
                   json={"name": f"iter202 anchored {i}", "property_id": PROP_ID})
        assert r.status_code in (200, 201), r.text
        pid = r.json()["id"]
        ids.append(pid)
        up = s.post(f"{API}/digital-twin/projects/{pid}/upload?layer_type=structure",
                    files={"file": ("m.glb", b"glTF-iter202" * 4, "model/gltf-binary")})
        assert up.status_code in (200, 201), up.text
    yield s, ids
    for pid in ids:
        s.delete(f"{API}/digital-twin/projects/{pid}")


def test_unified_overview_shape_and_values(anchored_projects):
    s, ids = anchored_projects
    r = s.get(f"{API}/properties/{PROP_ID}/digital-twin")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["property_id"] == PROP_ID
    t2, t3 = data["twin_2d"], data["twin_3d"]
    assert t2["exists"] is True
    assert t2["status"] == "approved", f"expected approved, got {t2['status']}"
    assert t2["rooms_count"] == 5, f"rooms_count expected 5, got {t2['rooms_count']}"
    assert t2["assets_count"] == 4, f"assets_count expected 4, got {t2['assets_count']}"
    assert t3["exists"] is True
    assert isinstance(t3["projects"], list) and len(t3["projects"]) >= 2
    linked = [p for p in t3["projects"] if p.get("property_link_status") == "linked"]
    assert len(linked) == len(t3["projects"]), "all projects should be linked"
    assert all(p.get("model_url") or p.get("models_count") for p in t3["projects"])
    assert t3["has_model"] is True


def test_authz_403_for_foreign_user():
    email = f"iter202free_{int(time.time())}_{uuid.uuid4().hex[:6]}@example.com"
    s = requests.Session()
    s.headers.update(HDR)
    reg = s.post(f"{API}/auth/register", json={
        "email": email, "password": "TestPass123!", "name": "Iter202 Free",
        "role": "client", "terms_accepted": True, "privacy_policy_accepted": True,
    })
    assert reg.status_code in (200, 201), reg.text
    r = s.get(f"{API}/properties/{PROP_ID}/digital-twin")
    if r.status_code == 401:
        s = _login(email, "TestPass123!")
        r = s.get(f"{API}/properties/{PROP_ID}/digital-twin")
    assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text}"


def test_authz_404_for_bogus_property_id():
    s = _login("client@propmanage.io", "Client123!")
    r = s.get(f"{API}/properties/6a11d70e600be19667009999/digital-twin")
    assert r.status_code == 404, r.text


def test_projects_filter_by_property_id(anchored_projects):
    s, ids = anchored_projects
    r = s.get(f"{API}/digital-twin/projects", params={"property_id": PROP_ID})
    assert r.status_code == 200, r.text
    body = r.json()
    projects = body.get("items") if isinstance(body, dict) else body
    assert isinstance(projects, list) and len(projects) >= 2
    assert all(p.get("property_id") == PROP_ID for p in projects)
    assert all(p.get("property_link_status") == "linked" for p in projects)


def test_projects_list_no_filter_backward_compat(anchored_projects):
    s, ids = anchored_projects
    r = s.get(f"{API}/digital-twin/projects")
    assert r.status_code == 200, r.text
    body = r.json()
    projects = body.get("items") if isinstance(body, dict) else body
    assert isinstance(projects, list) and len(projects) >= 2
    r2 = s.get(f"{API}/digital-twin/projects", params={"property_id": PROP_ID})
    filt = r2.json().get("items") if isinstance(r2.json(), dict) else r2.json()
    assert len(projects) >= len(filt)


def test_regression_twin_and_spaces_endpoints():
    s = _login("client@propmanage.io", "Client123!")
    r_twin = s.get(f"{API}/properties/{PROP_ID}/twin")
    assert r_twin.status_code == 200, r_twin.text
    tw = r_twin.json()
    assert len(tw.get("rooms", [])) == 5
    assert len(tw.get("assets", [])) == 4

    r_sp = s.get(f"{API}/properties/{PROP_ID}/spaces")
    assert r_sp.status_code == 200, r_sp.text
    sp = r_sp.json()
    assert sp.get("count") == 5
    assert all(x.get("source") == "twin_2d" for x in sp.get("spaces", []))
