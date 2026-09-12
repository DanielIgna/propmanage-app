"""Phase I: Digital Twin Issue Report PDF + Email — backend tests.

Also covers two bug fixes:
  (1) PDF page_count populated on upload; anchor endpoint rejects page > page_count.
  (2) Anchor cleanup permissions relaxed to any project member.
"""
import os
import io
import pytest
import requests
from tests.test_config import OWNER_ADMIN_PASSWORD

try:
    from pypdf import PdfWriter
except ImportError:  # pragma: no cover
    PdfWriter = None

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://phased-document.preview.emergentagent.com").rstrip("/")


# ---------------- helpers ----------------

def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return s


def _make_multipage_pdf(pages: int = 3) -> bytes:
    """Generate a tiny multi-page PDF using pypdf (or fallback to single-page minimal)."""
    if PdfWriter is None:
        raise RuntimeError("pypdf not installed")
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=595, height=842)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


# ---------------- fixtures ----------------

@pytest.fixture(scope="module")
def admin_session():
    return _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def client_session():
    return _login("client@propmanage.io", "Client123!")


@pytest.fixture(scope="module")
def specialist_session():
    s = _login("specialist@propmanage.io", "Spec123!")
    admin = _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    uid = me.get("id") or me.get("_id") or (me.get("user") or {}).get("id")
    if uid:
        admin.post(
            f"{BASE_URL}/api/admin/digital-twin/subscription/grant",
            json={"user_id": uid, "active": True}, timeout=10,
        )
    s._user_id = uid
    s._email = me.get("email")
    return s


@pytest.fixture(scope="module")
def specialist2_session():
    s = _login("specialist2@propmanage.io", "Spec123!")
    admin = _login("admin@propmanage.io", OWNER_ADMIN_PASSWORD)
    me = s.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    uid = me.get("id") or me.get("_id") or (me.get("user") or {}).get("id")
    if uid:
        admin.post(
            f"{BASE_URL}/api/admin/digital-twin/subscription/grant",
            json={"user_id": uid, "active": True}, timeout=10,
        )
    s._user_id = uid
    s._email = me.get("email")
    return s


@pytest.fixture(scope="module")
def project_id(admin_session, specialist_session, specialist2_session):
    """Project owned by admin with specialist + specialist2 as members."""
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects", json={
        "name": "TEST_PhaseI_IssueReport",
        "description": "Phase I issue report tests",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    # Add specialists as members
    for spec in (specialist_session, specialist2_session):
        uid = getattr(spec, "_user_id", None)
        if uid:
            admin_session.post(
                f"{BASE_URL}/api/digital-twin/projects/{pid}/members",
                json={"user_id": uid, "role": "specialist"}, timeout=10,
            )
    yield pid
    admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{pid}")


@pytest.fixture(scope="module")
def multipage_plan_id(admin_session, project_id):
    """Upload 3-page PDF; returns (plan_id, page_count)."""
    pdf_bytes = _make_multipage_pdf(3)
    files = {"file": ("multipage.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = admin_session.post(
        f"{BASE_URL}/api/digital-twin/projects/{project_id}/plans",
        params={"title": "TEST PhaseI Plan 3p", "plan_type": "floorplan"},
        files=files, timeout=20,
    )
    assert r.status_code == 200, r.text
    d = r.json()
    return d["id"], d


@pytest.fixture(scope="module")
def pin_id(admin_session, project_id, multipage_plan_id):
    """Pin with one anchor on page 1 of the multipage plan (for plan extract)."""
    plan_id, _ = multipage_plan_id
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
        "position": {"x": 1.0, "y": 2.0, "z": 3.0},
        "title": "TEST PhaseI Pin",
        "description": "Crack in beam near column B3",
        "category": "defect",
        "priority": "high",
    }, timeout=15)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    # Add anchor so plan extract is exercised
    admin_session.post(
        f"{BASE_URL}/api/digital-twin/pins/{pid}/anchors",
        json={"plan_id": plan_id, "page": 1, "x_pct": 0.42, "y_pct": 0.55},
        timeout=10,
    )
    return pid


@pytest.fixture(scope="module")
def pin_no_anchor(admin_session, project_id):
    r = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
        "position": {"x": 0, "y": 0, "z": 0},
        "title": "TEST PhaseI Pin (no anchor)",
        "category": "general",
    }, timeout=15)
    assert r.status_code == 200
    return r.json()["id"]


# 1x1 PNG base64 (transparent) for screenshot
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


# ---------------- Bug Fix 1: page_count validation ----------------
class TestBugFix1PageCount:
    def test_plan_upload_sets_page_count(self, multipage_plan_id):
        _, plan_doc = multipage_plan_id
        assert plan_doc.get("page_count") == 3, f"Expected page_count=3, got {plan_doc.get('page_count')}"

    def test_anchor_with_page_within_range_ok(self, admin_session, pin_id, multipage_plan_id):
        plan_id, _ = multipage_plan_id
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 3, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert r.status_code == 200, r.text
        # cleanup the page-3 anchor so other tests aren't affected
        aid = r.json()["anchor"]["id"]
        admin_session.delete(f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors/{aid}", timeout=10)

    def test_anchor_with_page_out_of_range_400(self, admin_session, pin_id, multipage_plan_id):
        plan_id, _ = multipage_plan_id
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/anchors",
            json={"plan_id": plan_id, "page": 99, "x_pct": 0.5, "y_pct": 0.5},
            timeout=10,
        )
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"
        body = r.json()
        msg = (body.get("detail") or body.get("message") or "").lower()
        assert "pagina" in msg or "page" in msg or "99" in msg, f"unexpected error msg: {body}"


# ---------------- Bug Fix 2: relaxed anchor cleanup permissions ----------------
class TestBugFix2AnchorDeletePermissions:
    def test_member_can_delete_other_members_anchor(
        self, admin_session, specialist_session, specialist2_session,
        project_id, multipage_plan_id,
    ):
        plan_id, _ = multipage_plan_id
        # specialist (member) creates a pin + anchor
        rp = specialist_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
            "position": {"x": 5, "y": 5, "z": 5},
            "title": "TEST PhaseI Perm Pin",
        }, timeout=10)
        assert rp.status_code == 200, rp.text
        pid = rp.json()["id"]
        ra = specialist_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pid}/anchors",
            json={"plan_id": plan_id, "page": 2, "x_pct": 0.3, "y_pct": 0.3},
            timeout=10,
        )
        assert ra.status_code == 200, ra.text
        anchor_id = ra.json()["anchor"]["id"]

        # specialist2 (different member, NOT creator/owner) should now be allowed to delete it
        rd = specialist2_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pid}/anchors/{anchor_id}",
            timeout=10,
        )
        assert rd.status_code == 200, f"expected 200 (bug fix) got {rd.status_code}: {rd.text}"
        # Confirm removed
        assert not any(a["id"] == anchor_id for a in rd.json().get("plan_anchors", []))
        # Cleanup pin
        admin_session.delete(f"{BASE_URL}/api/digital-twin/pins/{pid}")

    def test_non_member_still_403(self, admin_session, client_session, project_id, multipage_plan_id):
        # Grant DT Pro to client first so subscription gate doesn't trigger before access gate.
        # Without DT Pro, we'd see 403 from _ensure_dt_access regardless. The point of THIS test
        # is the _ensure_project_access gate. Use admin to make an anchor and have client (no member)
        # try to delete — we expect 403 (either from dt access OR project access; both are correct).
        plan_id, _ = multipage_plan_id
        rp = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", json={
            "position": {"x": 0, "y": 0, "z": 0}, "title": "TEST PhaseI NonMember Pin",
        }, timeout=10)
        pid = rp.json()["id"]
        ra = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pid}/anchors",
            json={"plan_id": plan_id, "page": 1, "x_pct": 0.1, "y_pct": 0.1},
            timeout=10,
        )
        anchor_id = ra.json()["anchor"]["id"]
        r = client_session.delete(
            f"{BASE_URL}/api/digital-twin/pins/{pid}/anchors/{anchor_id}",
            timeout=10,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"
        admin_session.delete(f"{BASE_URL}/api/digital-twin/pins/{pid}")


# ---------------- Phase I: Issue Report send ----------------
class TestIssueReportSend:
    def test_send_with_recipient_and_screenshot(self, admin_session, project_id, pin_id):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={
                "recipient_email": "specialist@propmanage.io",
                "custom_message": "Vă rog inspectați urgent.",
                "screenshot_3d": f"data:image/png;base64,{TINY_PNG_B64}",
                "include_thread": True,
            },
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("ok") is True
        rep = d.get("report") or {}
        assert rep.get("recipient_email") == "specialist@propmanage.io"
        assert rep.get("sender_name")
        assert rep.get("has_screenshot") is True
        assert rep.get("has_plan_extract") is True, "anchor exists so plan extract should be true"
        assert rep.get("pdf_size_bytes", 0) > 1000, f"PDF too small: {rep.get('pdf_size_bytes')}"
        assert "id" in rep

    def test_pin_report_history_grows(self, admin_session, project_id, pin_id):
        # Snapshot count
        r0 = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", timeout=10)
        pins = {p["id"]: p for p in r0.json()["items"]}
        before = len(pins[pin_id].get("report_history") or [])
        # Send
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={"recipient_email": "specialist@propmanage.io", "custom_message": "second"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        # Re-fetch
        r1 = admin_session.get(f"{BASE_URL}/api/digital-twin/projects/{project_id}/pins", timeout=10)
        pins = {p["id"]: p for p in r1.json()["items"]}
        after = len(pins[pin_id].get("report_history") or [])
        assert after == before + 1, f"report_history should grow by 1, before={before} after={after}"

    def test_send_no_recipient_uses_owner(self, admin_session, pin_id):
        # admin is owner of TEST_PhaseI project — should fallback to admin's email
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={"custom_message": "fallback to owner"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("recipient_email") == "admin@propmanage.io", f"unexpected recipient: {d.get('recipient_email')}"

    def test_send_no_screenshot_succeeds(self, admin_session, pin_id):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={
                "recipient_email": "specialist@propmanage.io",
                "custom_message": "no screenshot",
            },
            timeout=60,
        )
        assert r.status_code == 200, r.text
        rep = r.json().get("report") or {}
        assert rep.get("has_screenshot") is False

    def test_send_no_anchor_has_plan_extract_false(self, admin_session, pin_no_anchor):
        r = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_no_anchor}/issue-report",
            json={"recipient_email": "specialist@propmanage.io", "custom_message": "no anchor"},
            timeout=60,
        )
        assert r.status_code == 200, r.text
        rep = r.json().get("report") or {}
        assert rep.get("has_plan_extract") is False

    def test_subscription_gate_403(self, client_session, pin_id):
        r = client_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={"recipient_email": "x@y.com", "custom_message": "x"},
            timeout=15,
        )
        assert r.status_code == 403, f"client without DT Pro should get 403: {r.status_code} {r.text}"

    def test_non_member_with_dt_pro_403(self, specialist2_session, admin_session, project_id):
        """Remove specialist2 from project, then try — must 403 on project access."""
        uid = getattr(specialist2_session, "_user_id", None)
        if not uid:
            pytest.skip("no specialist2 uid")
        # Make a temporary new project that specialist2 is NOT member of
        rp = admin_session.post(f"{BASE_URL}/api/digital-twin/projects",
                                json={"name": "TEST_PhaseI_Excl"}, timeout=10)
        excl_pid = rp.json()["id"]
        try:
            # Create pin
            rp2 = admin_session.post(f"{BASE_URL}/api/digital-twin/projects/{excl_pid}/pins",
                                     json={"position": {"x": 0, "y": 0, "z": 0}, "title": "TEST Excl Pin"},
                                     timeout=10)
            excl_pin = rp2.json()["id"]
            r = specialist2_session.post(
                f"{BASE_URL}/api/digital-twin/pins/{excl_pin}/issue-report",
                json={"custom_message": "should fail"}, timeout=15,
            )
            assert r.status_code == 403, f"non-member should 403, got {r.status_code}: {r.text}"
        finally:
            admin_session.delete(f"{BASE_URL}/api/digital-twin/projects/{excl_pid}")


# ---------------- Phase I: In-app notification ----------------
class TestIssueReportNotification:
    def test_notification_created_for_known_user(self, admin_session, specialist_session, pin_id):
        # Snapshot notifications for specialist
        r0 = specialist_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        before = []
        if r0.status_code == 200:
            data = r0.json()
            before = data.get("items") if isinstance(data, dict) else data
            before = before or []
        # Send report
        rs = admin_session.post(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report",
            json={"recipient_email": specialist_session._email, "custom_message": "notif test"},
            timeout=60,
        )
        assert rs.status_code == 200, rs.text
        # Re-fetch
        r1 = specialist_session.get(f"{BASE_URL}/api/notifications", timeout=10)
        if r1.status_code != 200:
            pytest.skip(f"/api/notifications not available: {r1.status_code}")
        data1 = r1.json()
        items = data1.get("items") if isinstance(data1, dict) else data1
        items = items or []
        # Find a dt_issue_report notification
        dt_notifs = [n for n in items if (n.get("type") == "dt_issue_report")]
        assert len(dt_notifs) > 0, f"no dt_issue_report notification found among {len(items)} items"
        # Check title
        latest = dt_notifs[0]
        title = latest.get("title", "")
        assert "Raport problemă" in title or "Raport" in title, f"unexpected title: {title}"


# ---------------- Phase I: Preview ----------------
class TestIssueReportPreview:
    def test_preview_returns_inline_pdf(self, admin_session, pin_id):
        r = admin_session.get(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report/preview",
            timeout=60,
        )
        assert r.status_code == 200, r.text[:300]
        ct = r.headers.get("Content-Type", "")
        assert "application/pdf" in ct, f"expected application/pdf got {ct}"
        cd = r.headers.get("Content-Disposition", "")
        assert "inline" in cd.lower(), f"expected inline disposition, got: {cd}"
        # PDF magic header
        assert r.content[:4] == b"%PDF", f"not a PDF: {r.content[:20]!r}"
        assert len(r.content) > 1000

    def test_preview_subscription_gate(self, client_session, pin_id):
        r = client_session.get(
            f"{BASE_URL}/api/digital-twin/pins/{pin_id}/issue-report/preview",
            timeout=15,
        )
        assert r.status_code == 403, f"expected 403 got {r.status_code}"
