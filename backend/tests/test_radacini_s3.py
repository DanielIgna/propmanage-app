"""Rădăcini S3 — HTTP integration tests (contract: docs/radacini/PLAN.md, "S3 — contract").

Run against a live backend:
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s3.py -q --noconftest

One ordered scenario (state carried in the `S` dict). Roles:
  client      = parcel owner            -> project member `owner`
  specialist  = cultivator              -> project member `coordinator`
  admin       = super-admin             -> read access everywhere AND an extra project
                                           participant / coordinator (only 3 demo accounts exist)
Setup creates a 5000 m2 parcel (rent), a 3000 m2 request, accepted and signed by both parties;
the project is created automatically on signing. The parcel carries a unique TEST-RAD-<hex> tag.
While the agreement is active the parcel cannot be archived through the API; completing the project
releases it (paused, no active agreement), after which the owner can archive it.
"""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import requests

# Independent of tests/test_config.py (its isolation gate targets the legacy Mongo suite).
# Run with --noconftest.
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
CLIENT_EMAIL, CLIENT_PASSWORD = "client@propmanage.io", "Client123!"
SPECIALIST_EMAIL, SPECIALIST_PASSWORD = "specialist@propmanage.io", "Spec123!"

R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20

CLUJ = "Cluj-Napoca"
FLORESTI = "Florești"
LAT, LNG = 46.7712, 23.6236

PARCEL_AREA = 5000
PROJECT_AREA = 3000
UNKNOWN_ID = "0" * 24

S = {}
_created_ids = []


# ── helpers ──────────────────────────────────────────────────────────────────

def _accept_terms(s):
    """Termenii Rădăcini (S8) sunt obligatorii pentru acțiuni: contul de test îi acceptă pe cei curenți."""
    docs = s.get(f"{API}/radacini/legal/documents", timeout=TIMEOUT).json().get("items", [])
    for d in docs:
        s.post(f"{API}/radacini/legal/accept", json={"type": d["type"], "version": d["version"]}, timeout=TIMEOUT)


def _login(email, passwords):
    s = requests.Session()
    last = None
    for pwd in passwords:
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT)
        last = r.status_code
        if r.status_code == 200:
            _accept_terms(s)
            return s
    pytest.skip(f"Login failed for {email} (last={last})")


def _unwrap(data, key):
    if isinstance(data, dict) and isinstance(data.get(key), dict):
        return data[key]
    return data


def _items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("items"), list):
            return data["items"]
        for v in data.values():
            if isinstance(v, list):
                return v
    raise AssertionError(f"No list found in response: {str(data)[:200]}")


def _today():
    # The API validates dates in Europe/Bucharest (the frontend computes local dates).
    return datetime.now(ZoneInfo("Europe/Bucharest")).date()


def _d(days):
    return (_today() + timedelta(days=days)).isoformat()


def _err(r, code):
    """Assert an error response: exact status code and a string `detail`."""
    assert r.status_code == code, f"expected {code}, got {r.status_code}: {r.text[:300]}"
    assert isinstance(r.json().get("detail"), str), r.text[:300]


def _4xx(r):
    assert 400 <= r.status_code < 500, f"expected 4xx, got {r.status_code}: {r.text[:300]}"


def _ok(r):
    assert r.status_code in (200, 201, 204), f"expected 2xx, got {r.status_code}: {r.text[:300]}"
    return r


def _parcel_payload(suffix="", **over):
    p = {
        "title": f"{TAG} teren S3 {suffix}".strip(),
        "county": "Cluj",
        "locality": FLORESTI,
        "lat": LAT,
        "lng": LNG,
        "area_m2": PARCEL_AREA,
        "access": "Drum de pământ, acces auto",
        "water_sources": ["well"],
        "current_crops": ["porumb"],
        "description": "Teren de test pentru integrare S3.",
        "offer": {"models": ["rent"], "terms": "Termeni de test", "price_ron_per_year": 1200},
    }
    p.update(over)
    return p


def _request_body(**over):
    p = {
        "model": "rent",
        "area_m2": PROJECT_AREA,
        "start_date": _d(10),
        "end_date": _d(375),
        "price_ron_per_year": 1000,
        "crops": ["porumb"],
        "note": f"{TAG} cerere",
    }
    p.update(over)
    return {k: v for k, v in p.items() if v is not None}


def _ensure_member(session, interests, locality):
    r = session.put(
        f"{R}/members/me",
        json={"interests": interests, "county": "Cluj", "locality": locality},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text


def _my_user_id(session):
    r = session.get(f"{R}/members/me", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["member"]["user_id"]


def _project(session, pid=None):
    r = session.get(f"{R}/projects/{pid or S['project_id']}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return _unwrap(r.json(), "project")


def _member_of(project, uid):
    for m in project.get("members", []):
        if m["user_id"] == uid:
            return m
    return None


def _role_of(project, uid):
    m = _member_of(project, uid)
    return m["role"] if m else None


def _plist_project(item):
    """Project fields from a /projects list item (flat, or nested under `project`)."""
    return item["project"] if isinstance(item.get("project"), dict) else item


def _pr(): return f"{R}/projects/{S['project_id']}"


def _invite(session, email):
    return session.post(f"{_pr()}/members", json={"email": email}, timeout=TIMEOUT)


def _set_role(session, uid, role):
    return session.patch(f"{_pr()}/members/{uid}", json={"role": role}, timeout=TIMEOUT)


def _crop_body(crop_id, area, **over):
    b = {"crop": crop_id, "area_m2": area, "sow_date": _d(20)}
    b.update(over)
    return b


def _activity_body(**over):
    b = {"type": "work_day", "title": f"{TAG} activitate", "date": _d(5)}
    b.update(over)
    return b


def _new_activity(session, **over):
    r = session.post(f"{_pr()}/activities", json=_activity_body(**over), timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    return _unwrap(r.json(), "activity")


def _get_activity(session, aid):
    r = session.get(f"{_pr()}/activities", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    for a in _items(r.json()):
        if a["id"] == aid:
            return a
    raise AssertionError(f"activity {aid} not in list")


def _contrib_body(kind="labor_hours", amount=3, **over):
    b = {"kind": kind, "amount": amount, "description": f"{TAG} contribuție", "date": _d(-1)}
    b.update(over)
    return b


def _log_contribution(session, **kw):
    over = {k: v for k, v in kw.items() if k not in ("kind", "amount")}
    r = session.post(
        f"{_pr()}/contributions",
        json=_contrib_body(kw.get("kind", "labor_hours"), kw.get("amount", 3), **over),
        timeout=TIMEOUT,
    )
    return r


def _new_contribution(session, **kw):
    r = _log_contribution(session, **kw)
    assert r.status_code in (200, 201), r.text
    return _unwrap(r.json(), "contribution")


def _review(session, cid, decision, note=None):
    body = {"decision": decision}
    if note is not None:
        body["note"] = note
    return session.post(f"{R}/contributions/{cid}/review", json=body, timeout=TIMEOUT)


def _contributions(session, member=None):
    params = {"member": member} if member else None
    r = session.get(f"{_pr()}/contributions", params=params, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


def _total(data, uid, kind, unit=None):
    for t in data["totals"]:
        if t["member_user_id"] == uid and t["kind"] == kind and (unit is None or t["unit"] == unit):
            return t
    return None


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def anon():
    return requests.Session()


@pytest.fixture(scope="module")
def client():
    return _login(CLIENT_EMAIL, [CLIENT_PASSWORD])


@pytest.fixture(scope="module")
def specialist():
    return _login(SPECIALIST_EMAIL, [SPECIALIST_PASSWORD])


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PASSWORDS)


@pytest.fixture(scope="module", autouse=True)
def _members(client, specialist, admin):
    _ensure_member(client, ["land"], FLORESTI)
    _ensure_member(specialist, ["grow"], FLORESTI)
    _ensure_member(admin, ["grow"], CLUJ)
    S["client_uid"] = _my_user_id(client)
    S["specialist_uid"] = _my_user_id(specialist)
    S["admin_uid"] = _my_user_id(admin)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, admin, _members):
    yield
    for pid in _created_ids:
        try:
            r = client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
            if r.status_code == 409:
                # a parcel with an active agreement answers 409; it is left for
                # radacini_purge_demo.py (expected).
                admin.post(
                    f"{R}/staff/parcels/{pid}/verify",
                    json={"decision": "reject", "note": "cleanup test"},
                    timeout=TIMEOUT,
                )
                client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        except Exception:
            pass


# ── 0. setup: parcel -> request -> agreement signed -> project ───────────────

class TestSetup:
    def test_publish_parcel(self, client, admin):
        r = client.post(f"{R}/parcels", json=_parcel_payload("main"), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        pid = _unwrap(r.json(), "parcel")["id"]
        _created_ids.append(pid)
        S["pid"] = pid
        assert client.post(f"{R}/parcels/{pid}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{pid}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = client.get(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        assert _unwrap(r.json(), "parcel")["status"] == "published"

    def test_request_accept(self, client, specialist):
        r = specialist.post(f"{R}/parcels/{S['pid']}/requests", json=_request_body(), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        S["rid"] = _unwrap(r.json(), "request")["id"]
        r = client.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        S["aid"] = _unwrap(r.json(), "agreement")["id"]

    def test_propose_and_sign(self, client, specialist):
        r = client.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = client.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 1}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = specialist.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 1}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["status"] == "signed"

    def test_project_created_automatically(self, specialist):
        r = specialist.get(f"{R}/projects", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        found = [_plist_project(i) for i in _items(r.json()) if _plist_project(i).get("agreement_id") == S["aid"]]
        assert len(found) == 1, "exactly one project must exist for the signed agreement"
        p = found[0]
        S["project_id"] = p["id"]
        assert p["parcel_id"] == S["pid"]
        assert p["status"] == "active"
        assert TAG in p["title"]
        assert p["locality"] == FLORESTI
        assert p["area_m2"] == PROJECT_AREA
        assert str(p["start_date"])[:10] == _d(10)
        assert str(p["end_date"])[:10] == _d(375)

    def test_initial_members(self, specialist):
        p = _project(specialist)
        assert _role_of(p, S["specialist_uid"]) == "coordinator"
        assert _role_of(p, S["client_uid"]) == "owner"
        assert len(p["members"]) == 2
        assert set(p["member_ids"]) == {S["specialist_uid"], S["client_uid"]}
        assert all(m.get("name") and m.get("joined_at") for m in p["members"])


# ── 1. projects: list / detail / access ──────────────────────────────────────

class TestProjects:
    def test_anonymous_401(self, anon):
        assert anon.get(f"{R}/projects", timeout=TIMEOUT).status_code == 401
        assert anon.get(f"{R}/projects/{S['project_id']}", timeout=TIMEOUT).status_code == 401

    def test_list_specialist_has_role(self, specialist):
        r = specialist.get(f"{R}/projects", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        item = next(i for i in _items(r.json()) if _plist_project(i)["id"] == S["project_id"])
        assert item["role"] == "coordinator"

    def test_list_owner_has_role(self, client):
        r = client.get(f"{R}/projects", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        item = next(i for i in _items(r.json()) if _plist_project(i)["id"] == S["project_id"])
        assert item["role"] == "owner"

    def test_list_excludes_non_member(self, admin):
        r = admin.get(f"{R}/projects", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert all(_plist_project(i)["id"] != S["project_id"] for i in _items(r.json()))

    def test_detail_members(self, client, specialist):
        for s in (client, specialist):
            p = _project(s)
            assert p["id"] == S["project_id"]
            assert p["agreement_id"] == S["aid"]

    def test_detail_super_admin_can_read(self, admin):
        p = _project(admin)
        assert p["id"] == S["project_id"]

    def test_detail_unknown_404(self, client):
        _err(client.get(f"{R}/projects/{UNKNOWN_ID}", timeout=TIMEOUT), 404)

    def test_non_member_cannot_write(self, admin):
        # admin is not (yet) a member: it may read, but must not act
        r = admin.post(f"{_pr()}/crops", json=_crop_body("porumb", 100), timeout=TIMEOUT)
        assert r.status_code in (403, 404), r.text
        r = admin.post(f"{_pr()}/contributions", json=_contrib_body(), timeout=TIMEOUT)
        assert r.status_code in (403, 404), r.text
        r = admin.post(f"{_pr()}/complete", timeout=TIMEOUT)
        assert r.status_code in (403, 404), r.text


# ── 2. members ───────────────────────────────────────────────────────────────

class TestMembers:
    def test_owner_cannot_invite(self, client):
        _err(_invite(client, ADMIN_EMAIL), 403)

    def test_anonymous_cannot_invite(self, anon):
        assert _invite(anon, ADMIN_EMAIL).status_code == 401

    def test_invite_requires_email(self, specialist):
        _err(specialist.post(f"{_pr()}/members", json={}, timeout=TIMEOUT), 400)

    def test_invite_unknown_email_404(self, specialist):
        _err(_invite(specialist, f"nu-exista-{uuid.uuid4().hex[:8]}@example.com"), 404)

    def test_coordinator_invites_admin(self, specialist):
        _ok(_invite(specialist, ADMIN_EMAIL))
        p = _project(specialist)
        assert _role_of(p, S["admin_uid"]) == "participant"
        assert S["admin_uid"] in p["member_ids"]

    def test_invite_again_409(self, specialist):
        _err(_invite(specialist, ADMIN_EMAIL), 409)

    def test_invite_existing_member_409(self, specialist):
        _err(_invite(specialist, CLIENT_EMAIL), 409)
        _err(_invite(specialist, SPECIALIST_EMAIL), 409)

    def test_participant_appears_in_list(self, admin):
        r = admin.get(f"{R}/projects", timeout=TIMEOUT)
        item = next(i for i in _items(r.json()) if _plist_project(i)["id"] == S["project_id"])
        assert item["role"] == "participant"

    def test_participant_cannot_manage_members(self, admin):
        _err(_set_role(admin, S["admin_uid"], "coordinator"), 403)
        _err(admin.delete(f"{_pr()}/members/{S['specialist_uid']}", timeout=TIMEOUT), 403)
        _err(_invite(admin, CLIENT_EMAIL), 403)

    def test_owner_cannot_change_roles(self, client):
        _err(_set_role(client, S["admin_uid"], "coordinator"), 403)

    def test_patch_invalid_role_400(self, specialist):
        _err(_set_role(specialist, S["admin_uid"], "owner"), 400)
        _err(_set_role(specialist, S["admin_uid"], "boss"), 400)

    def test_patch_unknown_member_404(self, specialist):
        _err(_set_role(specialist, UNKNOWN_ID, "participant"), 404)

    def test_owner_role_cannot_change(self, specialist):
        _4xx(_set_role(specialist, S["client_uid"], "participant"))
        _4xx(_set_role(specialist, S["client_uid"], "coordinator"))
        assert _role_of(_project(specialist), S["client_uid"]) == "owner"

    def test_promote_admin(self, specialist):
        _ok(_set_role(specialist, S["admin_uid"], "coordinator"))
        assert _role_of(_project(specialist), S["admin_uid"]) == "coordinator"

    def test_agreement_parties_cannot_be_removed(self, specialist, admin):
        # admin is a coordinator here, so the "last coordinator" rule does not apply: only the party rule does
        for sess in (admin, specialist):
            r = sess.delete(f"{_pr()}/members/{S['specialist_uid']}", timeout=TIMEOUT)
            _err(r, 409)
            assert "Părțile acordului" in r.json()["detail"]
        p = _project(specialist)
        assert _role_of(p, S["specialist_uid"]) == "coordinator"
        assert _role_of(p, S["client_uid"]) == "owner"

    def test_demote_specialist_while_another_coordinator_remains(self, specialist, admin):
        _ok(_set_role(specialist, S["specialist_uid"], "participant"))
        assert _role_of(_project(admin), S["specialist_uid"]) == "participant"
        # specialist is no longer a coordinator, admin restores the role
        _err(_set_role(specialist, S["specialist_uid"], "coordinator"), 403)
        _ok(_set_role(admin, S["specialist_uid"], "coordinator"))
        assert _role_of(_project(admin), S["specialist_uid"]) == "coordinator"

    def test_demote_admin_back(self, specialist):
        _ok(_set_role(specialist, S["admin_uid"], "participant"))
        assert _role_of(_project(specialist), S["admin_uid"]) == "participant"

    def test_cannot_remove_owner(self, specialist):
        _4xx(specialist.delete(f"{_pr()}/members/{S['client_uid']}", timeout=TIMEOUT))
        assert _role_of(_project(specialist), S["client_uid"]) == "owner"

    def test_owner_cannot_remove_self(self, client):
        _4xx(client.delete(f"{_pr()}/members/{S['client_uid']}", timeout=TIMEOUT))
        assert _role_of(_project(client), S["client_uid"]) == "owner"

    def test_cannot_remove_or_demote_last_coordinator(self, specialist):
        # specialist is the only coordinator now
        _4xx(specialist.delete(f"{_pr()}/members/{S['specialist_uid']}", timeout=TIMEOUT))
        _4xx(_set_role(specialist, S["specialist_uid"], "participant"))
        assert _role_of(_project(specialist), S["specialist_uid"]) == "coordinator"

    def test_admin_leaves_then_reinvited(self, specialist, admin):
        _ok(admin.delete(f"{_pr()}/members/{S['admin_uid']}", timeout=TIMEOUT))
        p = _project(specialist)
        assert _member_of(p, S["admin_uid"]) is None
        assert S["admin_uid"] not in p["member_ids"]
        # still readable as super-admin
        assert _project(admin)["id"] == S["project_id"]
        # re-invite as participant for the next sections
        _ok(_invite(specialist, ADMIN_EMAIL))
        assert _role_of(_project(specialist), S["admin_uid"]) == "participant"


# ── 3. crop plan ─────────────────────────────────────────────────────────────

class TestCrops:
    def test_meta_crops(self, anon):
        r = anon.get(f"{R}/meta", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        crops = r.json()["crops"]
        assert isinstance(crops, list) and len(crops) >= 15
        assert all({"id", "label", "family"} <= set(c) for c in crops)
        tomato = [c for c in crops if "roșii" in c["label"].lower()]
        assert tomato, "meta.crops must contain 'Roșii'"
        assert tomato[0]["family"] == "solanacee"
        labels = " ".join(c["label"].lower() for c in crops)
        for word in ("ardei", "castraveți", "varză", "cartofi", "ceapă", "usturoi", "morcovi", "fasole",
                     "mazăre", "porumb", "grâu", "dovlecei", "salată", "căpșuni"):
            assert word in labels, f"missing crop {word}"
        families = {c["family"] for c in crops}
        assert families <= {"solanacee", "cucurbitacee", "brasicacee", "liliacee", "leguminoase",
                            "umbelifere", "cereale", "asteracee", "rozacee", "other"}
        S["tomato_id"] = tomato[0]["id"]
        S["other_crop_id"] = next(c["id"] for c in crops if c["id"] != S["tomato_id"] and "porumb" in c["label"].lower())

    def test_anonymous_401(self, anon):
        assert anon.get(f"{_pr()}/crops", timeout=TIMEOUT).status_code == 401

    def test_empty_list_has_warnings_key(self, client):
        r = client.get(f"{_pr()}/crops", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert _items(data) == []
        assert isinstance(data["warnings"], list)

    def test_participant_cannot_create(self, admin):
        _err(admin.post(f"{_pr()}/crops", json=_crop_body(S["tomato_id"], 500), timeout=TIMEOUT), 403)

    def test_owner_cannot_create(self, client):
        _err(client.post(f"{_pr()}/crops", json=_crop_body(S["tomato_id"], 500), timeout=TIMEOUT), 403)

    def test_validation(self, specialist):
        for body in (
            _crop_body(S["tomato_id"], 0),
            _crop_body(S["tomato_id"], -5),
            _crop_body(S["tomato_id"], "mult"),
            _crop_body(S["tomato_id"], 100, sow_date="ieri"),
            _crop_body("", 100),
            _crop_body(S["tomato_id"], 100, expected_yield_kg=-1),
        ):
            _err(specialist.post(f"{_pr()}/crops", json=body, timeout=TIMEOUT), 400)
        r = specialist.post(f"{_pr()}/crops", json={"area_m2": 100, "sow_date": _d(5)}, timeout=TIMEOUT)
        _err(r, 400)

    def test_create_first(self, specialist):
        r = specialist.post(
            f"{_pr()}/crops",
            json=_crop_body(S["tomato_id"], 2000, expected_harvest_date=_d(120), expected_yield_kg=800, notes=TAG),
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 201), r.text
        c = _unwrap(r.json(), "crop")
        S["crop1"] = c["id"]
        assert c["project_id"] == S["project_id"]
        assert c["family"] == "solanacee"
        assert c["area_m2"] == 2000
        assert c["status"] == "planned"
        assert c["created_by"] == S["specialist_uid"]
        assert c["expected_yield_kg"] == 800

    def test_second_exceeds_project_area_400(self, specialist):
        _err(specialist.post(f"{_pr()}/crops", json=_crop_body(S["other_crop_id"], 1500), timeout=TIMEOUT), 400)

    def test_patch_participant_403(self, admin):
        _err(admin.patch(f"{R}/crops/{S['crop1']}", json={"area_m2": 1000}, timeout=TIMEOUT), 403)

    def test_patch_unknown_404(self, specialist):
        _err(specialist.patch(f"{R}/crops/{UNKNOWN_ID}", json={"area_m2": 1000}, timeout=TIMEOUT), 404)

    def test_patch_first_to_1000(self, specialist):
        r = specialist.patch(f"{R}/crops/{S['crop1']}", json={"area_m2": 1000}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "crop")["area_m2"] == 1000

    def test_patch_invalid_400(self, specialist):
        _err(specialist.patch(f"{R}/crops/{S['crop1']}", json={"area_m2": 0}, timeout=TIMEOUT), 400)
        _err(specialist.patch(f"{R}/crops/{S['crop1']}", json={"status": "inexistent"}, timeout=TIMEOUT), 400)

    def test_patch_status(self, specialist):
        r = specialist.patch(f"{R}/crops/{S['crop1']}", json={"status": "sown"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "crop")["status"] == "sown"

    def test_create_second_now_fits(self, specialist):
        r = specialist.post(f"{_pr()}/crops", json=_crop_body(S["other_crop_id"], 1500), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        c = _unwrap(r.json(), "crop")
        S["crop2"] = c["id"]
        assert c["family"] == "cereale"

    def test_free_text_crop_family_other(self, specialist):
        r = specialist.post(f"{_pr()}/crops", json=_crop_body(f"{TAG} plantă rară", 100), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        c = _unwrap(r.json(), "crop")
        assert c["family"] == "other"
        S["crop_free"] = c["id"]

    def test_patch_over_total_400(self, specialist):
        # 1000 + 1500 + 100 = 2600; growing the second to 2500 would give 3600 > 3000
        _err(specialist.patch(f"{R}/crops/{S['crop2']}", json={"area_m2": 2500}, timeout=TIMEOUT), 400)

    def test_list_members_and_warnings(self, client, admin, specialist):
        for s in (client, admin, specialist):
            r = s.get(f"{_pr()}/crops", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            data = r.json()
            ids = {c["id"] for c in _items(data)}
            assert {S["crop1"], S["crop2"], S["crop_free"]} <= ids
            assert isinstance(data["warnings"], list)  # may be empty (no earlier project on this parcel)
            assert all(isinstance(w, str) for w in data["warnings"])

    def test_delete_participant_403(self, admin):
        _err(admin.delete(f"{R}/crops/{S['crop_free']}", timeout=TIMEOUT), 403)

    def test_delete(self, specialist):
        _ok(specialist.delete(f"{R}/crops/{S['crop_free']}", timeout=TIMEOUT))
        r = specialist.get(f"{_pr()}/crops", timeout=TIMEOUT)
        assert S["crop_free"] not in {c["id"] for c in _items(r.json())}
        _err(specialist.delete(f"{R}/crops/{S['crop_free']}", timeout=TIMEOUT), 404)


# ── 4. activities ────────────────────────────────────────────────────────────

class TestActivities:
    def test_anonymous_401(self, anon):
        assert anon.get(f"{_pr()}/activities", timeout=TIMEOUT).status_code == 401

    def test_participant_cannot_create(self, admin):
        _err(admin.post(f"{_pr()}/activities", json=_activity_body(), timeout=TIMEOUT), 403)

    def test_owner_cannot_create(self, client):
        _err(client.post(f"{_pr()}/activities", json=_activity_body(), timeout=TIMEOUT), 403)

    def test_validation(self, specialist):
        for body in (
            _activity_body(type="nu-exista"),
            _activity_body(title=""),
            _activity_body(date="mâine"),
            _activity_body(slots=0),
            _activity_body(duration_h=-1),
        ):
            _err(specialist.post(f"{_pr()}/activities", json=body, timeout=TIMEOUT), 400)

    def test_create_with_slot(self, specialist):
        a = _new_activity(
            specialist, title=f"{TAG} zi de lucru", slots=1, start_time="09:00", duration_h=2,
            crop_plan_id=S["crop1"], notes="note", date=_d(5),
        )
        S["act1"] = a["id"]
        assert a["project_id"] == S["project_id"]
        assert a["status"] == "scheduled"
        assert a["participants"] == []
        assert a["slots"] == 1
        assert a["created_by"] == S["specialist_uid"]
        assert a["crop_plan_id"] == S["crop1"]

    def test_list_sorted_and_filtered(self, specialist, client):
        a_early = _new_activity(specialist, title=f"{TAG} devreme", type="planting", date=_d(2))
        S["act_early"] = a_early["id"]
        r = client.get(f"{_pr()}/activities", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        items = _items(r.json())
        dates = [str(a["date"])[:10] for a in items]
        assert dates == sorted(dates)
        ids = [a["id"] for a in items]
        assert ids.index(S["act_early"]) < ids.index(S["act1"])
        # from/to filters
        r = client.get(f"{_pr()}/activities", params={"from": _d(4), "to": _d(6)}, timeout=TIMEOUT)
        ids = {a["id"] for a in _items(r.json())}
        assert S["act1"] in ids and S["act_early"] not in ids
        r = client.get(f"{_pr()}/activities", params={"from": _d(300)}, timeout=TIMEOUT)
        assert not ({S["act1"], S["act_early"]} & {a["id"] for a in _items(r.json())})

    def test_participant_joins(self, admin):
        r = admin.post(f"{R}/activities/{S['act1']}/join", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert S["admin_uid"] in _get_activity(admin, S["act1"])["participants"]

    def test_join_twice_rejected(self, admin):
        _4xx(admin.post(f"{R}/activities/{S['act1']}/join", timeout=TIMEOUT))

    def test_owner_join_full_409(self, client):
        _err(client.post(f"{R}/activities/{S['act1']}/join", timeout=TIMEOUT), 409)

    def test_join_unknown_404(self, client):
        _err(client.post(f"{R}/activities/{UNKNOWN_ID}/join", timeout=TIMEOUT), 404)

    def test_participant_leaves(self, admin):
        r = admin.post(f"{R}/activities/{S['act1']}/leave", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert S["admin_uid"] not in _get_activity(admin, S["act1"])["participants"]

    def test_owner_joins_after_slot_freed(self, client):
        r = client.post(f"{R}/activities/{S['act1']}/join", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert S["client_uid"] in _get_activity(client, S["act1"])["participants"]

    def test_participant_cannot_patch(self, admin):
        _err(admin.patch(f"{R}/activities/{S['act1']}", json={"title": "x" * 5}, timeout=TIMEOUT), 403)

    def test_participant_cannot_done_or_cancel(self, admin):
        _err(admin.post(f"{R}/activities/{S['act1']}/done", timeout=TIMEOUT), 403)
        _err(admin.post(f"{R}/activities/{S['act1']}/cancel", timeout=TIMEOUT), 403)

    def test_coordinator_patches(self, specialist):
        r = specialist.patch(
            f"{R}/activities/{S['act1']}", json={"title": f"{TAG} zi de lucru (editată)", "duration_h": 3},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        a = _unwrap(r.json(), "activity")
        assert a["title"].endswith("(editată)")
        assert a["duration_h"] == 3

    def test_patch_invalid_400(self, specialist):
        _err(specialist.patch(f"{R}/activities/{S['act1']}", json={"date": "mâine"}, timeout=TIMEOUT), 400)

    def test_done(self, specialist):
        r = specialist.post(f"{R}/activities/{S['act1']}/done", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "activity")["status"] == "done"
        assert _get_activity(specialist, S["act1"])["status"] == "done"

    def test_done_activity_is_frozen(self, specialist, admin):
        _4xx(admin.post(f"{R}/activities/{S['act1']}/join", timeout=TIMEOUT))
        _4xx(admin.post(f"{R}/activities/{S['act1']}/leave", timeout=TIMEOUT))
        _4xx(specialist.patch(f"{R}/activities/{S['act1']}", json={"title": f"{TAG} nou"}, timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/activities/{S['act1']}/done", timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/activities/{S['act1']}/cancel", timeout=TIMEOUT))

    def test_cancel_other(self, specialist, admin):
        r = specialist.post(f"{R}/activities/{S['act_early']}/cancel", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "activity")["status"] == "cancelled"
        _4xx(admin.post(f"{R}/activities/{S['act_early']}/join", timeout=TIMEOUT))
        _4xx(specialist.patch(f"{R}/activities/{S['act_early']}", json={"title": f"{TAG} nou"}, timeout=TIMEOUT))


# ── 5. contributions ─────────────────────────────────────────────────────────

class TestContributions:
    def test_anonymous_401(self, anon):
        assert anon.get(f"{_pr()}/contributions", timeout=TIMEOUT).status_code == 401
        assert anon.post(f"{_pr()}/contributions", json=_contrib_body(), timeout=TIMEOUT).status_code == 401

    def test_warning_text_not_required_but_empty_list_ok(self, client):
        data = _contributions(client)
        assert isinstance(data["items"], list)
        assert isinstance(data["totals"], list)

    def test_coordinator_logs_labor_hours_default_unit(self, specialist):
        c = _new_contribution(specialist, kind="labor_hours", amount=3, activity_id=S["act1"])
        S["c_spec"] = c["id"]
        assert c["project_id"] == S["project_id"]
        assert c["member_user_id"] == S["specialist_uid"]
        assert c["member_name"]
        assert c["kind"] == "labor_hours"
        assert c["amount"] == 3
        assert c["unit"] == "ore"
        assert c["status"] == "logged"
        assert c["activity_id"] == S["act1"]
        assert not c.get("reviewed_by")

    def test_money_default_unit(self, client):
        c = _new_contribution(client, kind="money", amount=50)
        S["c_money"] = c["id"]
        assert c["unit"] == "RON"
        assert c["member_user_id"] == S["client_uid"]

    def test_validation(self, specialist):
        for r in (
            _log_contribution(specialist, date=_d(5)),                       # future date
            _log_contribution(specialist, amount=0),                         # amount must be > 0
            _log_contribution(specialist, amount=-2),
            _log_contribution(specialist, amount="mult"),
            _log_contribution(specialist, kind="bani"),                      # unknown kind
            _log_contribution(specialist, description="ab"),                 # < 3 chars
            _log_contribution(specialist, description="x" * 301),            # > 300 chars
            _log_contribution(specialist, kind="tools", amount=1, unit="u" * 21),  # unit > 20 chars
            _log_contribution(specialist, date="ieri"),
        ):
            _err(r, 400)

    def test_free_text_unit_for_materials(self, specialist):
        c = _new_contribution(specialist, kind="tools", amount=2, unit="buc")
        assert c["unit"] == "buc"

    def test_today_is_allowed(self, specialist):
        _new_contribution(specialist, kind="labor_hours", amount=1, date=_d(0))

    def test_author_cannot_review_own(self, specialist):
        _4xx(_review(specialist, S["c_spec"], "confirm"))
        r = _log_contribution(specialist, kind="labor_hours", amount=1)
        assert r.status_code in (200, 201)

    def test_participant_cannot_review(self, admin):
        _err(_review(admin, S["c_spec"], "confirm"), 403)

    def test_anonymous_cannot_review(self, anon):
        assert _review(anon, S["c_spec"], "confirm").status_code == 401

    def test_review_unknown_404(self, specialist):
        _err(_review(specialist, UNKNOWN_ID, "confirm"), 404)

    def test_review_invalid_decision_400(self, client):
        _err(_review(client, S["c_spec"], "poate"), 400)

    def test_owner_confirms_sole_coordinator_contribution(self, client):
        # specialist is the only coordinator -> the owner may confirm their contribution
        r = _review(client, S["c_spec"], "confirm", note="ok")
        assert r.status_code == 200, r.text
        c = _unwrap(r.json(), "contribution")
        assert c["status"] == "confirmed"
        assert c["reviewed_by"] == S["client_uid"]
        assert c["reviewed_at"]
        assert c["review_note"] == "ok"

    def test_review_again_409(self, client, specialist):
        _err(_review(client, S["c_spec"], "confirm"), 409)
        _err(_review(client, S["c_spec"], "dispute", note="nu"), 409)

    def test_admin_logs_materials(self, admin):
        c = _new_contribution(admin, kind="materials", amount=10, unit="kg", description=f"{TAG} semințe")
        S["c_a1"] = c["id"]
        assert c["member_user_id"] == S["admin_uid"]
        assert c["unit"] == "kg"
        assert c["status"] == "logged"

    def test_owner_cannot_review_participant_contribution(self, client):
        # the author is not a coordinator, so the owner-fallback does not apply
        _err(_review(client, S["c_a1"], "confirm"), 403)

    def test_author_participant_cannot_review_own(self, admin):
        _err(_review(admin, S["c_a1"], "confirm"), 403)

    def test_dispute_requires_note(self, specialist):
        _err(_review(specialist, S["c_a1"], "dispute"), 400)
        _err(_review(specialist, S["c_a1"], "dispute", note=""), 400)
        assert _contributions(specialist)["items"]  # untouched, still readable

    def test_dispute_with_note(self, specialist):
        r = _review(specialist, S["c_a1"], "dispute", note="Cantitatea nu corespunde bonului.")
        assert r.status_code == 200, r.text
        c = _unwrap(r.json(), "contribution")
        assert c["status"] == "disputed"
        assert c["reviewed_by"] == S["specialist_uid"]
        assert c["review_note"] == "Cantitatea nu corespunde bonului."

    def test_review_disputed_again_409(self, specialist):
        _err(_review(specialist, S["c_a1"], "confirm"), 409)
        _err(_review(specialist, S["c_a1"], "dispute", note="din nou"), 409)

    def test_correction_with_corrects_id(self, admin):
        c = _new_contribution(admin, kind="materials", amount=8, unit="kg",
                              description=f"{TAG} semințe (corecție)", corrects_id=S["c_a1"])
        S["c_a2"] = c["id"]
        assert c["corrects_id"] == S["c_a1"]
        assert c["status"] == "logged"
        # the old entry stays in history
        items = {i["id"]: i for i in _contributions(admin)["items"]}
        assert items[S["c_a1"]]["status"] == "disputed"
        assert items[S["c_a2"]]["corrects_id"] == S["c_a1"]

    def test_correction_unknown_target_rejected(self, admin):
        _4xx(_log_contribution(admin, kind="materials", amount=1, unit="kg", corrects_id=UNKNOWN_ID))

    def test_pending_entry(self, admin):
        c = _new_contribution(admin, kind="materials", amount=5, unit="kg", description=f"{TAG} îngrășământ")
        S["c_a3"] = c["id"]

    def test_confirm_correction(self, specialist):
        r = _review(specialist, S["c_a2"], "confirm")
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "contribution")["status"] == "confirmed"

    def test_totals(self, client):
        data = _contributions(client)
        # specialist: 3 h confirmed by the owner; the two other logged entries (1 h, 1 h) and
        # the tools entry are pending
        spec = _total(data, S["specialist_uid"], "labor_hours", "ore")
        assert spec is not None
        assert spec["confirmed"] == 3
        assert spec["pending"] == 2
        assert spec["member_name"]
        # admin / materials / kg: disputed + corrected entry (10) excluded, correction (8) confirmed,
        # the other logged entry (5) is pending
        adm = _total(data, S["admin_uid"], "materials", "kg")
        assert adm is not None
        assert adm["confirmed"] == 8
        assert adm["pending"] == 5
        # client money stays pending
        money = _total(data, S["client_uid"], "money", "RON")
        assert money is not None
        assert money["confirmed"] == 0 and money["pending"] == 50

    def test_member_filter(self, client):
        data = _contributions(client, member=S["admin_uid"])
        ids = {i["id"] for i in data["items"]}
        assert {S["c_a1"], S["c_a2"], S["c_a3"]} <= ids
        assert S["c_spec"] not in ids
        assert all(i["member_user_id"] == S["admin_uid"] for i in data["items"])

    def test_list_visible_to_all_members(self, admin, specialist):
        for s in (admin, specialist):
            ids = {i["id"] for i in _contributions(s)["items"]}
            assert {S["c_spec"], S["c_a1"], S["c_a2"], S["c_money"]} <= ids

    def test_pending_review_by_coordinator_of_owner_contribution(self, specialist):
        # coordinator (not the author) confirms the owner's money entry
        r = _review(specialist, S["c_money"], "confirm")
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "contribution")["status"] == "confirmed"

    def test_no_patch_or_delete(self, specialist, client):
        for s in (specialist, client):
            r = s.patch(f"{R}/contributions/{S['c_a3']}", json={"amount": 99}, timeout=TIMEOUT)
            assert r.status_code in (404, 405), r.text
            r = s.delete(f"{R}/contributions/{S['c_a3']}", timeout=TIMEOUT)
            assert r.status_code in (404, 405), r.text
        items = {i["id"]: i for i in _contributions(specialist)["items"]}
        assert items[S["c_a3"]]["amount"] == 5


# ── 5b. impersonation: an admin acting as a member cannot act on their behalf ──

def _impersonate(target_uid):
    s = _login(ADMIN_EMAIL, ADMIN_PASSWORDS)
    r = s.post(
        f"{API}/admin/impersonate",
        json={"user_id": target_uid, "reason": "test Radacini: actiuni blocate in impersonare"},
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        pytest.skip(f"impersonation unavailable in this environment ({r.status_code})")
    return s


class TestImpersonationBlocked:
    def test_contributions_and_completion_blocked(self, specialist):
        s = _impersonate(S["specialist_uid"])
        try:
            for r in (
                _log_contribution(s),
                _review(s, UNKNOWN_ID, "confirm"),
                s.post(f"{_pr()}/complete", timeout=TIMEOUT),
            ):
                _err(r, 403)
                assert "impersonare" in r.json()["detail"]
        finally:
            s.post(f"{API}/admin/stop-impersonation", timeout=TIMEOUT)
        assert _project(specialist)["status"] == "active"


# ── 6. project completion ────────────────────────────────────────────────────

class TestComplete:
    def test_anonymous_401(self, anon):
        assert anon.post(f"{_pr()}/complete", timeout=TIMEOUT).status_code == 401

    def test_participant_403(self, admin):
        _err(admin.post(f"{_pr()}/complete", timeout=TIMEOUT), 403)

    def test_owner_403(self, client):
        _err(client.post(f"{_pr()}/complete", timeout=TIMEOUT), 403)

    def test_still_active(self, specialist):
        assert _project(specialist)["status"] == "active"

    def test_complete_unknown_404(self, specialist):
        _err(specialist.post(f"{R}/projects/{UNKNOWN_ID}/complete", timeout=TIMEOUT), 404)

    def test_coordinator_completes(self, specialist):
        r = specialist.post(f"{_pr()}/complete", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        p = _unwrap(r.json(), "project")
        assert p["status"] == "completed"
        assert p["completed_at"]

    def test_status_persisted(self, client):
        p = _project(client)
        assert p["status"] == "completed"
        assert p["completed_at"]

    def test_parcel_released_to_owner(self, client):
        r = client.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        p = _unwrap(r.json(), "parcel")
        assert p["status"] == "paused"
        assert not p.get("active_agreement_id")

    def test_cultivator_still_reads_parcel_approximately(self, specialist, anon):
        r = specialist.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        p = _unwrap(r.json(), "parcel")
        assert p["lat"] == pytest.approx(round(LAT, 2))
        assert "owner_user_id" not in p
        assert anon.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT).status_code == 404

    def test_owner_can_archive_released_parcel(self, client):
        r = client.delete(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert client.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT).status_code == 404

    def test_complete_again_409(self, specialist):
        _err(specialist.post(f"{_pr()}/complete", timeout=TIMEOUT), 409)

    def test_listed_as_completed(self, specialist):
        r = specialist.get(f"{R}/projects", timeout=TIMEOUT)
        item = next(i for i in _items(r.json()) if _plist_project(i)["id"] == S["project_id"])
        assert _plist_project(item)["status"] == "completed"


# ── 7. parallel signing, harvest guard, parcel release ───────────────────────

class TestParallelSigningAndCompletion:
    def test_setup_proposed_agreement(self, client, admin, specialist):
        r = client.post(f"{R}/parcels", json=_parcel_payload("parallel", area_m2=4000), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        pid = _unwrap(r.json(), "parcel")["id"]
        _created_ids.append(pid)
        S["pid2"] = pid
        assert client.post(f"{R}/parcels/{pid}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{pid}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = specialist.post(f"{R}/parcels/{pid}/requests", json=_request_body(area_m2=1000), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        rid = _unwrap(r.json(), "request")["id"]
        r = client.post(f"{R}/requests/{rid}/accept", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        S["aid2"] = _unwrap(r.json(), "agreement")["id"]
        assert client.post(f"{R}/agreements/{S['aid2']}/propose", timeout=TIMEOUT).status_code == 200

    def test_parallel_signing_yields_one_signed_agreement_and_one_project(self, client, specialist):
        def sign(sess):
            return sess.post(f"{R}/agreements/{S['aid2']}/sign", json={"version": 1}, timeout=TIMEOUT).status_code

        with ThreadPoolExecutor(max_workers=2) as ex:
            codes = list(ex.map(sign, (client, specialist)))
        assert codes == [200, 200], codes
        r = client.get(f"{R}/agreements/{S['aid2']}", timeout=TIMEOUT)
        assert _unwrap(r.json(), "agreement")["status"] == "signed"
        r = client.get(f"{R}/parcels/{S['pid2']}", timeout=TIMEOUT)
        assert _unwrap(r.json(), "parcel")["active_agreement_id"] == S["aid2"]
        items = [_plist_project(i) for i in _items(specialist.get(f"{R}/projects", timeout=TIMEOUT).json())]
        mine = [p for p in items if p.get("agreement_id") == S["aid2"]]
        assert len(mine) == 1, "exactly one project per signed agreement"
        S["project2"] = mine[0]["id"]

    def test_complete_blocked_by_unconfirmed_harvest(self, client, specialist):
        pr = f"{R}/projects/{S['project2']}"
        r = specialist.post(f"{pr}/harvests", json={"crop": "porumb", "quantity_kg": 10}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        harvest = _unwrap(r.json(), "harvest")
        assert harvest["status"] == "recorded"  # recorded by the cultivator, awaiting the owner
        r = specialist.post(f"{pr}/complete", timeout=TIMEOUT)
        _err(r, 409)
        assert "recolte neconfirmate" in r.json()["detail"]
        r = client.post(f"{R}/harvests/{harvest['id']}/confirm", timeout=TIMEOUT)
        assert r.status_code == 200, r.text

    def test_complete_releases_parcel(self, client, specialist):
        r = specialist.post(f"{R}/projects/{S['project2']}/complete", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = client.get(f"{R}/parcels/{S['pid2']}", timeout=TIMEOUT)
        p = _unwrap(r.json(), "parcel")
        assert p["status"] == "paused" and not p.get("active_agreement_id")
        # the owner can resume it (published again) and archive it
        assert client.post(f"{R}/parcels/{S['pid2']}/resume", timeout=TIMEOUT).status_code == 200
        assert client.delete(f"{R}/parcels/{S['pid2']}", timeout=TIMEOUT).status_code == 200
