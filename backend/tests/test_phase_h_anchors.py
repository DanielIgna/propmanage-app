"""Phase H: Digital Twin 3D ↔ 2D Pin Anchors — backend API tests.
Tests POST/DELETE anchor endpoints, validation, replacement, permissions, subscription gate.
"""
import os
import io
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")

MINIMAL_PDF = (
    b"%PDF-1.1\n%\xc7\xec\x8f\xa2\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]/Resources<<>>/Contents 4 0 R>>endobj\n"
    b"4 0 obj<</Length 8>>stream\nBT ET\nendstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000018 00000 n \n0000000060 00000 n \n"
    b"0000000108 00000 n \n0000000182 00000 n \n"
    b"trailer<</Size 5/Root 1 0 R>>\nstartxref\n232\n%%EOF\n"
)


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def specialist_session():
    # Grant DT Pro to specialist via admin so we can test the non-owner perms scenarios
    s = _login("specialist@propmanage.io", "Spec123!")
    admin = _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    spec_uid = me.get("id") or me.get("_id") or me.get("user", {}).get("id")
    if spec_uid:
        admin.post(f"{BASE_URL}/api/admin/digital-twin/subscription/grant",
                   json={"user_id": spec_uid, "active": True}, timeout=10)
    s._user_id = spec_uid
    return s


@pytest.fixture(scope="module")
def project_id(admin_session):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_PhaseH_Anchors",
        "description": "Phase H anchor test project",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture(scope="module")
def project_b(admin_session):
    """Second project used to validate cross-project plan rejection."""
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_PhaseH_AnchorsB",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    yield pid
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture(scope="module")
def plan_id(admin_session, project_id):
    files = {"file": ("ph.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    r = admin_session.post(
        f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
        params={"title": "TEST PhaseH Plan", "plan_type": "floorplan"},
        files=files, timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def plan_b_id(admin_session, project_b):
    files = {"file": ("phb.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")}
    r = admin_session.post(
        f"{BASE_URL}/api/digital-twin/projects/{project_b}/plans",
        params={"title": "TEST PhaseH Plan B"},
        files=files, timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture
def pin_id(admin_session, project_id):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "title": "TEST Anchor Pin",
        "category": "defect",
        "priority": "normal",
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# --------- Default empty anchors ----------
class TestDefaults:
    def test_new_pin_has_empty_plan_anchors(self, admin_session, project_id):
        r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
            "position": {"x": 0, "y": 0, "z": 0},
            "title": "TEST Empty Anchors Pin",
        }, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["plan_anchors"] == [], f"plan_anchors should default to []: {d.get('plan_anchors')}"
        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/digital-twin/pins/{d['id']}")


# --------- Create anchor ----------
class TestCreateAnchor:
    def test_create_anchor_success(self, admin_session, pin_id, plan_id, project_id):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.35, "y_pct": 0.42},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert "anchor" in d
        anc = d["anchor"]
        assert anc["plan_id"] == plan_id
        assert anc["page"] == 1
        assert abs(anc["x_pct"] - 0.35) < 1e-9
        assert abs(anc["y_pct"] - 0.42) < 1e-9
        assert "id" in anc
        assert anc["created_by"]
        # Verify persistence via GET /pins
        r2 = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", timeout=10)
        pins = {p["id"]: p for p in r2.json()["items"]}
        assert pin_id in pins
        anchors = pins[pin_id].get("plan_anchors", [])
        assert any(a.get("id") == anc["id"] for a in anchors)

    def test_create_anchor_replaces_same_page(self, admin_session, pin_id, plan_id, project_id):
        # Anchor #1
        r1 = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.10, "y_pct": 0.10},
            timeout=10,
        )
        assert r1.status_code == 200
        # Anchor #2 (same page) replaces #1
        r2 = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.80, "y_pct": 0.80},
            timeout=10,
        )
        assert r2.status_code == 200, r2.text
        # Only one anchor for that (plan_id, page=1)
        anchors_same_page = [a for a in r2.json()["plan_anchors"] if a["plan_id"] == plan_id and a["page"] == 1]
        assert len(anchors_same_page) == 1
        assert abs(anchors_same_page[0]["x_pct"] - 0.80) < 1e-9

    def test_validation_xy_out_of_range(self, admin_session, pin_id, plan_id):
        bad_payloads = [
            {"plan_id": plan_id, "page": 1, "x_pct": 1.5, "y_pct": 0.5},
            {"plan_id": plan_id, "page": 1, "x_pct": -0.1, "y_pct": 0.5},
            {"plan_id": plan_id, "page": 1, "x_pct": 0.5, "y_pct": 1.5},
            {"plan_id": plan_id, "page": 1, "x_pct": 0.5, "y_pct": -0.01},
        ]
        for body in bad_payloads:
            r = admin_session.post(
                f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
                json=body, timeout=10,
            )
            assert r.status_code == 422, f"expected 422 for {body}, got {r.status_code}"

    def test_validation_page_out_of_range(self, admin_session, pin_id, plan_id):
        for bad_page in (0, -1, 201, 1000):
            r = admin_session.post(
                f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
                json={"plan_id": plan_id, "page": bad_page, "x_pct": 0.5, "y_pct": 0.5},
                timeout=10,
            )
            assert r.status_code == 422, f"expected 422 for page={bad_page}, got {r.status_code}"

    def test_plan_id_other_project_404(self, admin_session, pin_id, plan_b_id):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_b_id, "page": 1, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert r.status_code == 404, r.text

    def test_pin_not_found_404(self, admin_session, plan_id):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/nonexistent_pin_zz/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert r.status_code == 404


# --------- Delete anchor ----------
class TestDeleteAnchor:
    def test_delete_anchor_admin(self, admin_session, pin_id, plan_id):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        anchor_id = r.json()["anchor"]["id"]
        rd = admin_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors/{anchor_id}",
            timeout=10,
        )
        assert rd.status_code == 200, rd.text
        # Verify removal
        assert not any(a["id"] == anchor_id for a in rd.json().get("plan_anchors", []))

    def test_delete_anchor_not_found(self, admin_session, pin_id):
        r = admin_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors/nonexistent_anchor_zz",
            timeout=10,
        )
        assert r.status_code == 404

    def test_delete_anchor_non_owner_403(self, admin_session, specialist_session, project_id, plan_id):
        # Create pin as admin
        rp = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
            "position": {"x": 0, "y": 0, "z": 0},
            "title": "TEST Perm Pin",
        }, timeout=10)
        assert rp.status_code == 200
        pin = rp.json()["id"]
        # Add anchor as admin
        ra = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert ra.status_code == 200
        anchor_id = ra.json()["anchor"]["id"]

        # Specialist is not project member yet → 403 on project access (which short-circuits to 403)
        r = specialist_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pin}/anchors/{anchor_id}",
            timeout=10,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"

        # Bug fix (Phase I): adding specialist as member now allows them to delete anchors.
        spec_uid = getattr(specialist_session, "_user_id", None)
        if spec_uid:
            admin_session.post(
                f"{BASE_URL}/api/digital-twin/projects/{project_id}/members",
                json={"user_id": spec_uid, "role": "specialist"}, timeout=10,
            )
            r2 = specialist_session.delete(
                f"{BASE_URL}/api/digital-twin/pins/{pin}/anchors/{anchor_id}",
                timeout=10,
            )
            assert r2.status_code == 200, f"member should now be allowed to delete (bug fix), got {r2.status_code}"

        # Cleanup
        admin_session.delete(f"{BASE_URL}/api/digital-twin/pins/{pin}")


# --------- Subscription gate ----------
class TestSubscriptionGate:
    def test_client_anchor_403(self, client_session, pin_id, plan_id):
        # Client has no DT Pro → 403 on anchor endpoints
        r = client_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert r.status_code == 403, r.text

    def test_client_delete_anchor_403(self, client_session, pin_id):
        r = client_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors/anything",
            timeout=10,
        )
        assert r.status_code == 403
