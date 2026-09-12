"""Phase G — Workflow notifications tests.
Covers pin created, pin status changed, comment added, model uploaded, plan uploaded.
Each event must (1) persist an in-app notification doc for stakeholders (excluding actor),
and (2) NOT notify the actor for their own action.
"""
import os
import time
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@propmanage.io", "password": OWNER_ADMIN_PASSWORD}
SPEC = {"email": "specialist@propmanage.io", "password": "Spec123!"}

# Minimal valid-ish files (~bytes)
MIN_GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 100  # 108 bytes, magic + dummy
MIN_PDF = (
    b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Resources<<>>>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000018 00000 n \n0000000061 00000 n \n0000000110 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n180\n%%EOF\n"
)


def _login(s, creds):
    r = s.post(f"{API}/auth/login", json=creds)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    # Some endpoints return {token,user}, others rely on cookies. Always fetch /me.
    me = s.get(f"{API}/auth/me")
    assert me.status_code == 200, f"/auth/me failed: {me.status_code} {me.text}"
    return data, me.json()


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    _, user = _login(s, ADMIN)
    return s, user


@pytest.fixture(scope="module")
def spec_session():
    s = requests.Session()
    _, user = _login(s, SPEC)
    return s, user


@pytest.fixture(scope="module")
def project_and_grant(admin_session, spec_session):
    s_admin, admin_user = admin_session
    s_spec, spec_user = spec_session

    # Grant DT Pro to specialist
    g = s_admin.post(
        f"{API}/admin/digital-twin/subscription/grant",
        json={"user_id": spec_user["id"], "active": True},
    )
    assert g.status_code == 200, g.text

    # Create fresh DT project
    name = f"TEST_PhaseG_{int(time.time())}"
    r = s_admin.post(f"{API}/digital-twin/projects", json={"name": name, "description": "Phase G workflow"})
    assert r.status_code == 200, r.text
    proj = r.json()
    pid = proj["id"]

    # Add specialist as member
    m = s_admin.post(
        f"{API}/digital-twin/projects/{pid}/members",
        json={"user_id": spec_user["id"], "role": "specialist"},
    )
    assert m.status_code == 200, m.text

    yield pid, admin_user, spec_user

    # cleanup
    s_admin.delete(f"{API}/digital-twin/projects/{pid}")


def _notif_count(session, hint_in_title=None, hint_in_type=None):
    """Return number of matching unread notifications for the session user."""
    r = session.get(f"{API}/notifications")
    assert r.status_code == 200, r.text
    docs = r.json()
    if hint_in_title is None and hint_in_type is None:
        return len(docs)
    n = 0
    for d in docs:
        t = (d.get("title") or "")
        ty = (d.get("type") or "")
        if hint_in_title and hint_in_title.lower() in t.lower():
            n += 1
        elif hint_in_type and hint_in_type in ty:
            n += 1
    return n


# -------- Pin created --------
def test_pin_created_notifies_specialist_not_admin(admin_session, spec_session, project_and_grant):
    pid, _, _ = project_and_grant
    s_admin, _ = admin_session
    s_spec, _ = spec_session

    before_spec_dt = _notif_count(s_spec, hint_in_type="dt_pin")
    before_admin_dt = _notif_count(s_admin, hint_in_type="dt_pin")

    payload = {
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "title": "Crăpătură perete sud",
        "priority": "high",
        "category": "structural",
    }
    r = s_admin.post(f"{API}/digital-twin/projects/{pid}/pins", json=payload)
    assert r.status_code == 200, r.text
    pin = r.json()
    assert pin["title"] == payload["title"]

    time.sleep(1)  # async create_task
    after_spec_dt = _notif_count(s_spec, hint_in_type="dt_pin")
    after_admin_dt = _notif_count(s_admin, hint_in_type="dt_pin")

    assert after_spec_dt == before_spec_dt + 1, "Specialist should receive 1 new dt_pin notification"
    assert after_admin_dt == before_admin_dt, "Admin (actor) should NOT receive notification"

    # save pin id for next tests via class attribute on the module
    pytest.PIN_ID = pin["id"]
    pytest.PIN_TITLE = pin["title"]


# -------- Pin status changed --------
def test_pin_status_change_notifies_admin_author(admin_session, spec_session, project_and_grant):
    pid, _, _ = project_and_grant
    s_admin, _ = admin_session
    s_spec, _ = spec_session
    pin_id = pytest.PIN_ID

    before_admin = _notif_count(s_admin, hint_in_type="dt_pin_status")
    before_spec = _notif_count(s_spec, hint_in_type="dt_pin_status")

    # Specialist resolves the pin
    r = s_spec.patch(f"{API}/digital-twin/pins/{pin_id}", json={"status": "resolved"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "resolved"

    time.sleep(1)
    after_admin = _notif_count(s_admin, hint_in_type="dt_pin_status")
    after_spec = _notif_count(s_spec, hint_in_type="dt_pin_status")

    # admin is project owner AND original author → must get notified
    assert after_admin >= before_admin + 1, "Admin (owner+author) should be notified of status change"
    # specialist is actor → no notification
    assert after_spec == before_spec, "Specialist (actor) should NOT be notified"


# -------- Comment added --------
def test_comment_added_notifies_admin(admin_session, spec_session, project_and_grant):
    pid, _, _ = project_and_grant
    s_admin, _ = admin_session
    s_spec, _ = spec_session
    pin_id = pytest.PIN_ID

    before_admin = _notif_count(s_admin, hint_in_type="dt_comment")
    before_spec = _notif_count(s_spec, hint_in_type="dt_comment")

    r = s_spec.post(f"{API}/digital-twin/pins/{pin_id}/comments", json={"message": "Confirm rezolvarea pe teren."})
    assert r.status_code == 200, r.text

    time.sleep(1)
    after_admin = _notif_count(s_admin, hint_in_type="dt_comment")
    after_spec = _notif_count(s_spec, hint_in_type="dt_comment")

    assert after_admin >= before_admin + 1, "Admin should receive comment notification"
    assert after_spec == before_spec, "Specialist (actor) should NOT receive"

    # Verify title contains 'Răspuns pe pin'
    r2 = s_admin.get(f"{API}/notifications")
    assert any("Răspuns pe pin" in (n.get("title") or "") for n in r2.json()), "Title should contain 'Răspuns pe pin'"


# -------- Model uploaded --------
def test_model_upload_notifies_specialist(admin_session, spec_session, project_and_grant):
    pid, _, _ = project_and_grant
    s_admin, _ = admin_session
    s_spec, _ = spec_session

    before_spec = _notif_count(s_spec, hint_in_type="dt_model")
    before_admin = _notif_count(s_admin, hint_in_type="dt_model")

    files = {"file": ("phaseg.glb", MIN_GLB, "model/gltf-binary")}
    r = s_admin.post(f"{API}/digital-twin/projects/{pid}/upload", files=files)
    assert r.status_code == 200, f"Model upload failed: {r.status_code} {r.text}"

    time.sleep(1)
    after_spec = _notif_count(s_spec, hint_in_type="dt_model")
    after_admin = _notif_count(s_admin, hint_in_type="dt_model")

    assert after_spec == before_spec + 1, "Specialist should be notified of model upload"
    assert after_admin == before_admin, "Admin (actor) should NOT be notified"

    # Verify title contains 'Model 3D actualizat'
    r2 = s_spec.get(f"{API}/notifications")
    assert any("Model 3D actualizat" in (n.get("title") or "") for n in r2.json())


# -------- Plan uploaded --------
def test_plan_upload_notifies_specialist(admin_session, spec_session, project_and_grant):
    pid, _, _ = project_and_grant
    s_admin, _ = admin_session
    s_spec, _ = spec_session

    before_spec = _notif_count(s_spec, hint_in_type="dt_plan")
    before_admin = _notif_count(s_admin, hint_in_type="dt_plan")

    files = {"file": ("plan.pdf", MIN_PDF, "application/pdf")}
    r = s_admin.post(
        f"{API}/digital-twin/projects/{pid}/plans",
        params={"title": "Test PhaseG", "plan_type": "floorplan"},
        files=files,
    )
    assert r.status_code == 200, r.text

    time.sleep(1)
    after_spec = _notif_count(s_spec, hint_in_type="dt_plan")
    after_admin = _notif_count(s_admin, hint_in_type="dt_plan")

    assert after_spec == before_spec + 1, "Specialist should receive plan upload notification"
    assert after_admin == before_admin, "Admin (actor) should NOT receive"

    # title contains 'Plan 2D nou'
    r2 = s_spec.get(f"{API}/notifications")
    assert any("Plan 2D nou" in (n.get("title") or "") for n in r2.json())


# -------- Negative: actor never gets notified for own action --------
def test_actor_never_self_notified(admin_session, spec_session, project_and_grant):
    """Admin posts a comment on the pin — admin (actor) must not be self-notified."""
    pid, _, _ = project_and_grant
    s_admin, _ = admin_session
    pin_id = pytest.PIN_ID

    before_admin_comment = _notif_count(s_admin, hint_in_type="dt_comment")
    r = s_admin.post(f"{API}/digital-twin/pins/{pin_id}/comments", json={"message": "Mulțumesc pentru confirmare."})
    assert r.status_code == 200
    time.sleep(1)
    after_admin_comment = _notif_count(s_admin, hint_in_type="dt_comment")
    assert after_admin_comment == before_admin_comment, "Admin (actor) should not receive a self-notification on comment"
