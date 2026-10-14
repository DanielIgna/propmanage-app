"""Rădăcini S7 — HTTP integration tests (needs, providers, service requests).

Run against a live backend:
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s7.py -q --noconftest

Setup as in test_radacini_s3.py: specialist = project coordinator, client = owner, admin = provider.
All data carries a TEST-RAD-<hex> tag.
"""
import os
import uuid
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

def _login(email, passwords):
    s = requests.Session()
    last = None
    for pwd in passwords:
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd}, timeout=TIMEOUT)
        last = r.status_code
        if r.status_code == 200:
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
        "title": f"{TAG} teren S7 {suffix}".strip(),
        "county": "Cluj",
        "locality": FLORESTI,
        "lat": LAT,
        "lng": LNG,
        "area_m2": PARCEL_AREA,
        "access": "Drum de pământ, acces auto",
        "water_sources": ["well"],
        "current_crops": ["porumb"],
        "description": "Teren de test pentru integrare S7.",
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


# ── 1. needs ─────────────────────────────────────────────────────────────────

def _need_body(**over):
    b = {"kind": "seeds", "item": f"{TAG} semințe", "quantity": 10, "unit": "kg"}
    b.update(over)
    return b


class TestNeeds:
    def test_create_coordinator_only(self, specialist, client):
        _err(client.post(f"{_pr()}/needs", json=_need_body(), timeout=TIMEOUT), 403)
        _err(specialist.post(f"{_pr()}/needs", json=_need_body(quantity=0), timeout=TIMEOUT), 400)
        _err(specialist.post(f"{_pr()}/needs", json=_need_body(kind="x"), timeout=TIMEOUT), 400)
        r = _ok(specialist.post(f"{_pr()}/needs", json=_need_body(), timeout=TIMEOUT))
        n = _unwrap(r.json(), "need")
        assert n["status"] == "needed" and n["pledges"] == []
        S["need_id"] = n["id"]
        r = _ok(specialist.get(f"{_pr()}/needs", timeout=TIMEOUT))
        assert any(i["id"] == S["need_id"] for i in _items(r.json()))

    def test_pledge_over_quantity_400(self, client):
        _err(client.post(f"{R}/needs/{S['need_id']}/pledge", json={"quantity": 11}, timeout=TIMEOUT), 400)
        _err(client.post(f"{R}/needs/{S['need_id']}/pledge", json={"quantity": 0}, timeout=TIMEOUT), 400)

    def test_pledges_and_sum_cap(self, client, specialist):
        _ok(client.post(f"{R}/needs/{S['need_id']}/pledge", json={"quantity": 4}, timeout=TIMEOUT))
        r = _ok(specialist.post(f"{R}/needs/{S['need_id']}/pledge", json={"quantity": 6}, timeout=TIMEOUT))
        n = _unwrap(r.json(), "need")
        assert n["pledged_total"] == 10 and len(n["pledges"]) == 2
        # fully pledged (still "needed" until fulfilled): any further pledge exceeds the quantity → 400 per contract
        _err(client.post(f"{R}/needs/{S['need_id']}/pledge", json={"quantity": 1}, timeout=TIMEOUT), 400)

    def test_fulfil_creates_contribution_idempotent(self, client, specialist):
        base = f"{R}/needs/{S['need_id']}"
        # only the pledger can fulfil
        n = next(i for i in _items(client.get(f"{_pr()}/needs", timeout=TIMEOUT).json()) if i["id"] == S["need_id"])
        idx_client = next(p["index"] for p in n["pledges"] if p["mine"])
        idx_spec = next(p["index"] for p in n["pledges"] if not p["mine"])
        _err(specialist.post(f"{base}/pledges/{idx_client}/fulfilled", timeout=TIMEOUT), 403)
        _err(client.post(f"{base}/pledges/99/fulfilled", timeout=TIMEOUT), 404)
        r = _ok(client.post(f"{base}/pledges/{idx_client}/fulfilled", timeout=TIMEOUT))
        n = _unwrap(r.json(), "need")
        assert n["status"] == "needed" and n["fulfilled_total"] == 4
        # idempotent: second call does not create a second contribution
        _ok(client.post(f"{base}/pledges/{idx_client}/fulfilled", timeout=TIMEOUT))
        data = _contributions(client, member=S["client_uid"])
        mine = [c for c in data["items"] if c.get("need_id") == S["need_id"]]
        assert len(mine) == 1
        assert mine[0]["kind"] == "materials" and mine[0]["status"] == "logged" and mine[0]["amount"] == 4
        S["idx_spec"] = idx_spec

    def test_covered(self, specialist):
        base = f"{R}/needs/{S['need_id']}"
        r = _ok(specialist.post(f"{base}/pledges/{S['idx_spec']}/fulfilled", timeout=TIMEOUT))
        n = _unwrap(r.json(), "need")
        assert n["status"] == "covered" and n["fulfilled_total"] == 10
        _err(specialist.post(f"{base}/cancel", timeout=TIMEOUT), 409)

    def test_cancel(self, specialist, client):
        n = _unwrap(_ok(specialist.post(f"{_pr()}/needs", json=_need_body(kind="tools", item=f"{TAG} tarnacop"), timeout=TIMEOUT)).json(), "need")
        _err(client.post(f"{R}/needs/{n['id']}/cancel", timeout=TIMEOUT), 403)
        r = _ok(specialist.post(f"{R}/needs/{n['id']}/cancel", timeout=TIMEOUT))
        assert _unwrap(r.json(), "need")["status"] == "cancelled"
        _err(client.post(f"{R}/needs/{n['id']}/pledge", json={"quantity": 1}, timeout=TIMEOUT), 409)


# ── 2. providers ─────────────────────────────────────────────────────────────

class TestProviders:
    def test_service_types(self, admin):
        r = _ok(admin.get(f"{R}/service-types", timeout=TIMEOUT))
        ids = {i["id"] for i in _items(r.json())}
        assert "arat" in ids and len(ids) == 8

    def test_validation(self, admin):
        for body in (
            {"services": [], "localities": [FLORESTI]},
            {"services": ["zbor"], "localities": [FLORESTI]},
            {"services": ["arat"], "localities": []},
            {"services": ["arat"], "localities": ["Atlantida"]},
        ):
            _err(admin.put(f"{R}/providers/me", json=body, timeout=TIMEOUT), 400)

    def test_upsert_and_list(self, admin):
        body = {"services": ["arat", "discuit"], "localities": [FLORESTI, CLUJ], "note": f"{TAG} prestator", "active": True}
        p = _unwrap(_ok(admin.put(f"{R}/providers/me", json=body, timeout=TIMEOUT)).json(), "provider")
        assert set(p["services"]) == {"arat", "discuit"}
        p2 = _unwrap(_ok(admin.put(f"{R}/providers/me", json=body, timeout=TIMEOUT)).json(), "provider")
        assert p2["id"] == p["id"]
        r = _ok(admin.get(f"{R}/providers/me", timeout=TIMEOUT))
        assert r.json()["exists"] is True
        r = _ok(admin.get(f"{R}/providers", params={"service": "arat", "locality": FLORESTI}, timeout=TIMEOUT))
        assert any(i["id"] == p["id"] for i in _items(r.json()))
        r = _ok(admin.get(f"{R}/providers", params={"service": "tratamente"}, timeout=TIMEOUT))
        assert all(i["id"] != p["id"] for i in _items(r.json()))
        S["rating_before"] = (p2["rating_count"], p2["rating_avg"])


# ── 3. service requests ──────────────────────────────────────────────────────

def _sr_body(**over):
    b = {"service_type": "arat", "description": f"{TAG} arat 3000 m2", "area_m2": 3000,
         "window_from": _d(5), "window_to": _d(20), "locality": FLORESTI}
    b.update(over)
    return b


class TestServiceRequests:
    def test_create_rules(self, client, specialist):
        _err(client.post(f"{_pr()}/service-requests", json=_sr_body(), timeout=TIMEOUT), 403)
        _err(specialist.post(f"{_pr()}/service-requests", json=_sr_body(service_type="zbor"), timeout=TIMEOUT), 400)
        _err(specialist.post(f"{_pr()}/service-requests", json=_sr_body(window_from=_d(9), window_to=_d(3)), timeout=TIMEOUT), 400)
        r = _ok(specialist.post(f"{_pr()}/service-requests", json=_sr_body(), timeout=TIMEOUT))
        req = _unwrap(r.json(), "request")
        assert req["status"] == "open" and req["offers"] == []
        S["sr"] = req["id"]

    def test_open_for_provider(self, admin, specialist):
        r = _ok(admin.get(f"{R}/service-requests/open", timeout=TIMEOUT))
        assert any(i["id"] == S["sr"] for i in _items(r.json()))

    def test_offer_and_duplicate(self, admin, specialist):
        base = f"{R}/service-requests/{S['sr']}"
        _err(specialist.post(f"{base}/offers", json={"message": "x"}, timeout=TIMEOUT), 403)
        _err(admin.post(f"{base}/offers", json={"price_ron_indicative": -1}, timeout=TIMEOUT), 400)
        _err(admin.post(f"{base}/offers", json={"price_ron_indicative": 2e6}, timeout=TIMEOUT), 400)
        _ok(admin.post(f"{base}/offers", json={"price_ron_indicative": 450, "message": f"{TAG} ofertă"}, timeout=TIMEOUT))
        _err(admin.post(f"{base}/offers", json={"price_ron_indicative": 400}, timeout=TIMEOUT), 409)
        r = _ok(specialist.get(f"{_pr()}/service-requests", timeout=TIMEOUT))
        req = next(i for i in _items(r.json()) if i["id"] == S["sr"])
        assert len(req["offers"]) == 1 and req["offers"][0]["provider_user_id"] == S["admin_uid"]

    def test_assign(self, specialist, client):
        base = f"{R}/service-requests/{S['sr']}"
        _err(client.post(f"{base}/assign", json={"provider_user_id": S["admin_uid"]}, timeout=TIMEOUT), 403)
        _err(specialist.post(f"{base}/assign", json={"provider_user_id": S["client_uid"]}, timeout=TIMEOUT), 400)
        _err(specialist.post(f"{base}/done", json={"rating": 5}, timeout=TIMEOUT), 409)
        r = _ok(specialist.post(f"{base}/assign", json={"provider_user_id": S["admin_uid"]}, timeout=TIMEOUT))
        assert _unwrap(r.json(), "request")["status"] == "assigned"
        _err(specialist.post(f"{base}/assign", json={"provider_user_id": S["admin_uid"]}, timeout=TIMEOUT), 409)

    def test_done_with_rating(self, specialist, admin):
        base = f"{R}/service-requests/{S['sr']}"
        _err(specialist.post(f"{base}/done", json={"rating": 0}, timeout=TIMEOUT), 400)
        _err(specialist.post(f"{base}/done", json={"rating": 6}, timeout=TIMEOUT), 400)
        r = _ok(specialist.post(f"{base}/done", json={"rating": 4, "comment": "ok"}, timeout=TIMEOUT))
        req = _unwrap(r.json(), "request")
        assert req["status"] == "done" and req["rating"] == 4
        _err(specialist.post(f"{base}/done", json={"rating": 4}, timeout=TIMEOUT), 409)
        _err(specialist.post(f"{base}/cancel", timeout=TIMEOUT), 409)

    def test_provider_rating_aggregated(self, admin):
        p = _unwrap(_ok(admin.get(f"{R}/providers/me", timeout=TIMEOUT)).json(), "provider")
        before_count, _ = S["rating_before"]
        assert p["rating_count"] == before_count + 1
        assert p["rating_avg"] is not None

    def test_cancel_assigned_and_open(self, specialist, admin):
        r = _ok(specialist.post(f"{_pr()}/service-requests", json=_sr_body(service_type="discuit"), timeout=TIMEOUT))
        rid = _unwrap(r.json(), "request")["id"]
        _ok(admin.post(f"{R}/service-requests/{rid}/offers", json={}, timeout=TIMEOUT))
        _ok(specialist.post(f"{R}/service-requests/{rid}/assign", json={"provider_user_id": S["admin_uid"]}, timeout=TIMEOUT))
        r = _ok(specialist.post(f"{R}/service-requests/{rid}/cancel", timeout=TIMEOUT))
        assert _unwrap(r.json(), "request")["status"] == "cancelled"
        r = _ok(specialist.post(f"{_pr()}/service-requests", json=_sr_body(service_type="discuit"), timeout=TIMEOUT))
        rid2 = _unwrap(r.json(), "request")["id"]
        assert _unwrap(_ok(specialist.post(f"{R}/service-requests/{rid2}/cancel", timeout=TIMEOUT)).json(), "request")["status"] == "cancelled"
        _err(admin.post(f"{R}/service-requests/{rid2}/offers", json={}, timeout=TIMEOUT), 409)
