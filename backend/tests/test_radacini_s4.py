"""Rădăcini S4 — HTTP integration tests (contract: docs/radacini/PLAN.md, "S4 — contract").

Run against a live backend:
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s4.py -q --noconftest

One ordered scenario (state carried in the `S` dict). Roles:
  client      = parcel owner            -> project member `owner`, listing seller/buyer
  specialist  = cultivator              -> project member `coordinator`, main listing seller
  admin       = super-admin             -> project `participant`, harvest share receiver and buyer
                                           (only 3 demo accounts exist)
Setup: 5000 m2 parcel (harvest_share 30%), 3000 m2 request, signed by both -> project created
automatically; a crop plan "roșii" 1000 m2 is added by the coordinator, admin is invited.
Everything carries a unique TEST-RAD-<hex> tag (parcel title, listing products). Listings are closed
at teardown; the signed parcel is left for backend/scripts/radacini_purge_demo.py --apply.
"""
from zoneinfo import ZoneInfo
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

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
SHARE_PCT = 30
UNKNOWN_ID = "0" * 24

S = {}
_created_ids = []
_listings = {}  # listing id -> seller session (closed at teardown)


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
    # The API validates dates against "today" in Europe/Bucharest (like the frontend).
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


def _kg(value, expected):
    assert value == pytest.approx(expected, abs=0.01), f"{value} != {expected}"


def _parcel_payload(suffix="", **over):
    p = {
        "title": f"{TAG} teren S4 {suffix}".strip(),
        "county": "Cluj",
        "locality": FLORESTI,
        "lat": LAT,
        "lng": LNG,
        "area_m2": PARCEL_AREA,
        "access": "Drum de pământ, acces auto",
        "water_sources": ["well"],
        "current_crops": ["porumb"],
        "description": "Teren de test pentru integrare S4.",
        "offer": {"models": ["harvest_share"], "terms": "Termeni de test", "harvest_share_percent": SHARE_PCT},
    }
    p.update(over)
    return p


def _request_body(**over):
    p = {
        "model": "harvest_share",
        "area_m2": PROJECT_AREA,
        "start_date": _d(10),
        "end_date": _d(375),
        "harvest_share_percent": SHARE_PCT,
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


def _plist_project(item):
    """Project fields from a /projects list item (flat, or nested under `project`)."""
    return item["project"] if isinstance(item.get("project"), dict) else item


def _pr(): return f"{R}/projects/{S['project_id']}"


# harvests / allocations

def _harvest_body(**over):
    b = {"quantity_kg": 10, "date": _d(0), "note": f"{TAG} recoltă"}
    b.update(over)
    return b


def _record(session, **over):
    return session.post(f"{_pr()}/harvests", json=_harvest_body(**over), timeout=TIMEOUT)


def _harvests(session):
    r = session.get(f"{_pr()}/harvests", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


def _harvest_total(data, crop):
    for t in data["totals"]:
        if t["crop"].lower() == crop.lower():
            return t["quantity_kg"]
    return None


def _confirm_harvest(session, hid):
    return session.post(f"{R}/harvests/{hid}/confirm", timeout=TIMEOUT)


def _allocs(session, hid):
    r = session.get(f"{R}/harvests/{hid}/allocations", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


def _allocate(session, hid, uid, kg):
    return session.post(
        f"{R}/harvests/{hid}/allocations",
        json={"member_user_id": uid, "quantity_kg": kg},
        timeout=TIMEOUT,
    )


def _alloc_of(data, uid, basis=None):
    for a in _items(data):
        if a["member_user_id"] == uid and (basis is None or a["basis"] == basis):
            return a
    return None


# listings / reservations

def _listing_body(**over):
    b = {
        "product": f"{TAG} roșii",
        "category": "legume",
        "unit": "kg",
        "quantity_total": 20,
        "price_ron_per_unit": 8,
        "mode": "both",
        "exchange_for": "Ouă de țară sau miere",
        "locality": FLORESTI,
        "pickup_details": "Ridicare de la poartă, după ora 17",
    }
    b.update(over)
    return {k: v for k, v in b.items() if v is not None}


def _create_listing(session, **over):
    r = session.post(f"{R}/listings", json=_listing_body(**over), timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    ls = _unwrap(r.json(), "listing")
    _listings[ls["id"]] = session
    return ls


def _get_listing(session, lid):
    r = session.get(f"{R}/listings/{lid}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return _unwrap(r.json(), "listing")


def _avail(session, lid):
    return _get_listing(session, lid)["quantity_available"]


def _reserve(session, lid, qty, mode="cash_on_pickup", **over):
    body = {"quantity": qty, "mode": mode}
    body.update(over)
    return session.post(f"{R}/listings/{lid}/reservations", json=body, timeout=TIMEOUT)


def _new_reservation(session, lid, qty, mode="cash_on_pickup", **over):
    r = _reserve(session, lid, qty, mode, **over)
    assert r.status_code in (200, 201), r.text
    res = _unwrap(r.json(), "reservation")
    assert res["status"] == "requested"
    return res


def _act(session, rid, action, **json):
    return session.post(f"{R}/reservations/{rid}/{action}", json=json or None, timeout=TIMEOUT)


def _res_status(r):
    assert r.status_code == 200, r.text
    return _unwrap(r.json(), "reservation")["status"]


def _mine(session, role):
    r = session.get(f"{R}/reservations/mine", params={"role": role}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return _items(r.json())


def _seller_rating(session, uid):
    r = session.get(f"{R}/sellers/{uid}/rating", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


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
    _ensure_member(client, ["land", "consume"], FLORESTI)
    _ensure_member(specialist, ["grow", "sell"], FLORESTI)
    _ensure_member(admin, ["grow", "consume"], CLUJ)
    S["client_uid"] = _my_user_id(client)
    S["specialist_uid"] = _my_user_id(specialist)
    S["admin_uid"] = _my_user_id(admin)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, admin, _members):
    yield
    for lid, sess in list(_listings.items()):
        try:
            sess.post(f"{R}/listings/{lid}/close", timeout=TIMEOUT)
        except Exception:
            pass
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


# ── 0. setup: parcel -> request -> agreement signed -> project -> crop plan ──

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
        assert _unwrap(r.json(), "agreement")["status"] == "signed"

    def test_project_created_automatically(self, specialist):
        r = specialist.get(f"{R}/projects", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        found = [_plist_project(i) for i in _items(r.json()) if _plist_project(i).get("agreement_id") == S["aid"]]
        assert len(found) == 1, "exactly one project must exist for the signed agreement"
        S["project_id"] = found[0]["id"]
        assert found[0]["status"] == "active"

    def test_invite_admin_participant(self, specialist):
        r = specialist.post(f"{_pr()}/members", json={"email": ADMIN_EMAIL}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text

    def test_coordinator_adds_crop_plan(self, anon, specialist):
        crops = anon.get(f"{R}/meta", timeout=TIMEOUT).json()["crops"]
        tomato = [c for c in crops if "roșii" in c["label"].lower()]
        assert tomato, "meta.crops must contain 'Roșii'"
        S["tomato_id"] = tomato[0]["id"]
        r = specialist.post(
            f"{_pr()}/crops",
            json={"crop": S["tomato_id"], "area_m2": 1000, "sow_date": _d(20), "notes": TAG},
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 201), r.text
        c = _unwrap(r.json(), "crop")
        S["crop_plan_id"] = c["id"]
        S["crop_plan_crop"] = c["crop"]
        assert c["status"] == "planned"


# ── 1. harvests ──────────────────────────────────────────────────────────────

class TestHarvests:
    def test_anonymous_401(self, anon):
        assert anon.get(f"{_pr()}/harvests", timeout=TIMEOUT).status_code == 401
        assert anon.post(f"{_pr()}/harvests", json=_harvest_body(crop="porumb"), timeout=TIMEOUT).status_code == 401

    def test_participant_cannot_record(self, admin):
        _err(_record(admin, crop_plan_id=S["crop_plan_id"], quantity_kg=100), 403)

    def test_owner_not_coordinator_cannot_record(self, client):
        _err(_record(client, crop_plan_id=S["crop_plan_id"], quantity_kg=100), 403)

    def test_future_date_400(self, specialist):
        _err(_record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=100, date=_d(1)), 400)

    def test_invalid_date_400(self, specialist):
        _err(_record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=100, date="ieri"), 400)

    def test_quantity_zero_400(self, specialist):
        _err(_record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=0), 400)

    def test_quantity_negative_400(self, specialist):
        _err(_record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=-5), 400)

    def test_quantity_too_large_400(self, specialist):
        _err(_record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=1_000_001), 400)

    def test_quantity_rounds_to_zero_400(self, specialist):
        # validat DUPĂ rotunjirea la 0,001: 0,0004 devine 0
        _err(_record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=0.0004), 400)

    def test_missing_crop_and_plan_400(self, specialist):
        _err(_record(specialist, quantity_kg=10), 400)

    def test_unknown_crop_plan_4xx(self, specialist):
        _4xx(_record(specialist, crop_plan_id=UNKNOWN_ID, quantity_kg=10))

    def test_unknown_project_404(self, specialist):
        r = specialist.post(f"{R}/projects/{UNKNOWN_ID}/harvests", json=_harvest_body(crop="porumb"), timeout=TIMEOUT)
        _err(r, 404)

    def test_coordinator_records_with_crop_plan(self, specialist):
        r = _record(specialist, crop_plan_id=S["crop_plan_id"], quantity_kg=100)
        assert r.status_code in (200, 201), r.text
        h = _unwrap(r.json(), "harvest")
        S["h1"] = h["id"]
        assert h["status"] == "recorded"
        assert h["project_id"] == S["project_id"]
        assert h["crop_plan_id"] == S["crop_plan_id"]
        assert h["crop"] == S["crop_plan_crop"]
        _kg(h["quantity_kg"], 100)
        assert str(h["date"])[:10] == _d(0)
        assert h["recorded_by"] == S["specialist_uid"]

    def test_crop_plan_becomes_harvested(self, specialist):
        r = specialist.get(f"{_pr()}/crops", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        plan = next(c for c in _items(r.json()) if c["id"] == S["crop_plan_id"])
        assert plan["status"] == "harvested"

    def test_list_for_members_and_admin(self, client, specialist, admin):
        for s in (client, specialist, admin):
            data = _harvests(s)
            assert any(h["id"] == S["h1"] for h in _items(data))
            assert isinstance(data["totals"], list)

    def test_allocation_before_confirm_4xx(self, specialist):
        _4xx(_allocate(specialist, S["h1"], S["admin_uid"], 10))

    def test_coordinator_cannot_confirm(self, specialist):
        _err(_confirm_harvest(specialist, S["h1"]), 403)

    def test_participant_cannot_confirm(self, admin):
        _err(_confirm_harvest(admin, S["h1"]), 403)

    def test_confirm_unknown_404(self, client):
        _err(_confirm_harvest(client, UNKNOWN_ID), 404)

    def test_owner_confirms(self, client):
        r = _confirm_harvest(client, S["h1"])
        assert r.status_code == 200, r.text
        h = _unwrap(r.json(), "harvest")
        assert h["status"] == "confirmed"
        assert h["confirmed_by"] == S["client_uid"]
        assert h.get("confirmed_at")

    def test_confirm_again_409(self, client):
        _err(_confirm_harvest(client, S["h1"]), 409)

    def test_totals_after_confirm(self, specialist):
        data = _harvests(specialist)
        _kg(_harvest_total(data, S["crop_plan_crop"]), 100)

    def test_automatic_owner_allocation(self, client):
        data = _allocs(client, S["h1"])
        a = _alloc_of(data, S["client_uid"])
        assert a is not None, "owner must get an automatic allocation"
        assert a["basis"] == "agreement_share"
        assert a["status"] == "allocated"
        assert a["harvest_id"] == S["h1"]
        _kg(a["quantity_kg"], 100 * SHARE_PCT / 100)
        S["a_owner"] = a["id"]

    def test_allocations_totals(self, specialist, admin):
        for s in (specialist, admin):
            data = _allocs(s, S["h1"])
            _kg(data["allocated_kg"], 30)
            _kg(data["remaining_kg"], 70)

    def test_second_harvest_free_text_crop_and_rounding(self, specialist, client):
        r = _record(specialist, crop="porumb", quantity_kg=33.3)
        assert r.status_code in (200, 201), r.text
        h = _unwrap(r.json(), "harvest")
        S["h2"] = h["id"]
        assert h["crop"].lower() == "porumb"  # „porumb” e în meta.crops → se salvează eticheta „Porumb”
        assert h.get("crop_plan_id") in (None, "")
        r = _confirm_harvest(client, S["h2"])
        assert r.status_code == 200, r.text
        data = _allocs(client, S["h2"])
        a = _alloc_of(data, S["client_uid"], "agreement_share")
        assert a is not None
        _kg(a["quantity_kg"], 10.0)  # 33.3 * 30% = 9.99 -> rounded to 0.1 kg
        assert _harvest_total(_harvests(client), "porumb") == pytest.approx(33.3, abs=0.01)


# ── 2. allocations ───────────────────────────────────────────────────────────

class TestAllocations:
    def test_anonymous_401(self, anon):
        assert anon.get(f"{R}/harvests/{S['h1']}/allocations", timeout=TIMEOUT).status_code == 401

    def test_participant_cannot_allocate(self, admin):
        _err(_allocate(admin, S["h1"], S["admin_uid"], 5), 403)

    def test_owner_cannot_allocate(self, client):
        _err(_allocate(client, S["h1"], S["client_uid"], 5), 403)

    def test_quantity_zero_400(self, specialist):
        _err(_allocate(specialist, S["h1"], S["admin_uid"], 0), 400)

    def test_quantity_rounds_to_zero_400(self, specialist):
        _err(_allocate(specialist, S["h1"], S["admin_uid"], 0.0004), 400)

    def test_unknown_member_4xx(self, specialist):
        _4xx(_allocate(specialist, S["h1"], UNKNOWN_ID, 5))

    def test_unknown_harvest_404(self, specialist):
        _err(_allocate(specialist, UNKNOWN_ID, S["admin_uid"], 5), 404)

    def test_allocate_50_to_admin(self, specialist):
        r = _allocate(specialist, S["h1"], S["admin_uid"], 50)
        assert r.status_code in (200, 201), r.text
        a = _unwrap(r.json(), "allocation")
        S["a_admin"] = a["id"]
        assert a["basis"] == "manual"
        assert a["status"] == "allocated"
        assert a["member_user_id"] == S["admin_uid"]
        assert a["member_name"]
        _kg(a["quantity_kg"], 50)
        assert a["created_by"] == S["specialist_uid"]
        data = _allocs(specialist, S["h1"])
        _kg(data["allocated_kg"], 80)
        _kg(data["remaining_kg"], 20)

    def test_exceeding_remaining_400(self, specialist):
        _err(_allocate(specialist, S["h1"], S["admin_uid"], 25), 400)
        data = _allocs(specialist, S["h1"])
        _kg(data["allocated_kg"], 80)

    def test_allocate_20_to_specialist(self, specialist):
        r = _allocate(specialist, S["h1"], S["specialist_uid"], 20)
        assert r.status_code in (200, 201), r.text
        S["a_spec"] = _unwrap(r.json(), "allocation")["id"]
        data = _allocs(specialist, S["h1"])
        _kg(data["allocated_kg"], 100)
        _kg(data["remaining_kg"], 0)

    def test_nothing_left_400(self, specialist):
        _err(_allocate(specialist, S["h1"], S["admin_uid"], 0.5), 400)

    def test_cannot_delete_agreement_share(self, specialist):
        _4xx(specialist.delete(f"{R}/allocations/{S['a_owner']}", timeout=TIMEOUT))
        assert _alloc_of(_allocs(specialist, S["h1"]), S["client_uid"], "agreement_share") is not None

    def test_participant_cannot_delete(self, admin):
        _err(admin.delete(f"{R}/allocations/{S['a_spec']}", timeout=TIMEOUT), 403)

    def test_delete_manual_allocated(self, specialist):
        _ok(specialist.delete(f"{R}/allocations/{S['a_spec']}", timeout=TIMEOUT))
        data = _allocs(specialist, S["h1"])
        assert all(a["id"] != S["a_spec"] for a in _items(data))
        _kg(data["allocated_kg"], 80)
        _kg(data["remaining_kg"], 20)

    def test_delete_unknown_404(self, specialist):
        _err(specialist.delete(f"{R}/allocations/{UNKNOWN_ID}", timeout=TIMEOUT), 404)

    def test_received_by_other_member_403(self, specialist, client):
        _err(specialist.post(f"{R}/allocations/{S['a_admin']}/received", timeout=TIMEOUT), 403)
        _err(client.post(f"{R}/allocations/{S['a_admin']}/received", timeout=TIMEOUT), 403)

    def test_received_unknown_404(self, admin):
        _err(admin.post(f"{R}/allocations/{UNKNOWN_ID}/received", timeout=TIMEOUT), 404)

    def test_recipient_marks_received(self, admin):
        r = admin.post(f"{R}/allocations/{S['a_admin']}/received", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        a = _unwrap(r.json(), "allocation")
        assert a["status"] == "received"
        assert a.get("received_at")

    def test_cannot_delete_received(self, specialist):
        _4xx(specialist.delete(f"{R}/allocations/{S['a_admin']}", timeout=TIMEOUT))
        a = _alloc_of(_allocs(specialist, S["h1"]), S["admin_uid"])
        assert a is not None and a["status"] == "received"


# ── 3. listings ──────────────────────────────────────────────────────────────

class TestListings:
    def test_anonymous_401(self, anon):
        assert anon.get(f"{R}/listings", timeout=TIMEOUT).status_code == 401
        assert anon.post(f"{R}/listings", json=_listing_body(), timeout=TIMEOUT).status_code == 401

    def test_sale_without_price_400(self, specialist):
        r = specialist.post(f"{R}/listings", json=_listing_body(mode="sale", price_ron_per_unit=None), timeout=TIMEOUT)
        _err(r, 400)

    def test_both_without_price_400(self, specialist):
        r = specialist.post(f"{R}/listings", json=_listing_body(mode="both", price_ron_per_unit=None), timeout=TIMEOUT)
        _err(r, 400)

    def test_price_out_of_range_400(self, specialist):
        for price in (0, -1, 10_001):
            r = specialist.post(f"{R}/listings", json=_listing_body(price_ron_per_unit=price), timeout=TIMEOUT)
            _err(r, 400)

    def test_exchange_without_exchange_for_400(self, specialist):
        r = specialist.post(
            f"{R}/listings",
            json=_listing_body(mode="exchange", price_ron_per_unit=None, exchange_for=None),
            timeout=TIMEOUT,
        )
        _err(r, 400)

    def test_both_without_exchange_for_400(self, specialist):
        r = specialist.post(f"{R}/listings", json=_listing_body(mode="both", exchange_for=None), timeout=TIMEOUT)
        _err(r, 400)

    def test_unknown_locality_400(self, specialist):
        _err(specialist.post(f"{R}/listings", json=_listing_body(locality="Atlantida"), timeout=TIMEOUT), 400)

    def test_available_until_past_400(self, specialist):
        _err(specialist.post(f"{R}/listings", json=_listing_body(available_until=_d(-1)), timeout=TIMEOUT), 400)

    def test_product_too_short_400(self, specialist):
        _err(specialist.post(f"{R}/listings", json=_listing_body(product="a"), timeout=TIMEOUT), 400)

    def test_quantity_zero_400(self, specialist):
        _err(specialist.post(f"{R}/listings", json=_listing_body(quantity_total=0), timeout=TIMEOUT), 400)

    def test_quantity_and_price_rounding_to_zero_400(self, specialist):
        _err(specialist.post(f"{R}/listings", json=_listing_body(quantity_total=0.0004), timeout=TIMEOUT), 400)
        _err(specialist.post(f"{R}/listings", json=_listing_body(price_ron_per_unit=0.004), timeout=TIMEOUT), 400)
        _err(specialist.post(f"{R}/listings", json=_listing_body(quantity_total=1_000_001), timeout=TIMEOUT), 400)

    def test_pickup_details_too_short_400(self, specialist):
        _err(specialist.post(f"{R}/listings", json=_listing_body(pickup_details="a"), timeout=TIMEOUT), 400)

    def test_project_id_not_member_4xx(self, specialist):
        _4xx(specialist.post(f"{R}/listings", json=_listing_body(project_id=UNKNOWN_ID), timeout=TIMEOUT))

    def test_listing_with_project_id(self, specialist):
        ls = _create_listing(
            specialist,
            product=f"{TAG} porumb proiect",
            unit="kg",
            quantity_total=5,
            project_id=S["project_id"],
            available_until=_d(30),
        )
        assert ls["project_id"] == S["project_id"]
        assert ls["status"] == "active"

    def test_single_listing_reference_price_null(self, specialist):
        ls = _create_listing(specialist, product=f"{TAG} castraveți unic", category="legume", price_ron_per_unit=7)
        S["l_single"] = ls["id"]
        assert ls.get("reference_price") is None
        assert _get_listing(specialist, ls["id"]).get("reference_price") is None

    def test_create_l1(self, specialist):
        ls = _create_listing(specialist)
        S["l1"] = ls["id"]
        assert ls["seller_user_id"] == S["specialist_uid"]
        assert ls["seller_name"]
        assert ls["product"] == f"{TAG} roșii"
        assert ls["product_key"] and ls["product_key"] == ls["product_key"].lower()
        assert ls["status"] == "active"
        assert ls["quantity_total"] == 20 and ls["quantity_available"] == 20
        assert ls["mode"] == "both"
        assert ls["locality"] == FLORESTI
        assert ls["exchange_for"]
        assert ls.get("reference_price") is None  # only one price so far

    def test_create_l2_same_product_sets_reference_price(self, client, specialist):
        ls = _create_listing(
            client, locality=CLUJ, mode="sale", exchange_for=None, price_ron_per_unit=10,
        )
        S["l2"] = ls["id"]
        assert ls["seller_user_id"] == S["client_uid"]
        assert ls["reference_price"] == pytest.approx(9.0)
        assert _get_listing(client, S["l1"])["reference_price"] == pytest.approx(9.0)
        assert _get_listing(specialist, S["l2"])["reference_price"] == pytest.approx(9.0)

    def test_other_unit_not_in_median(self, client, specialist):
        ls = _create_listing(client, unit="buc", price_ron_per_unit=100, mode="sale", exchange_for=None, locality=CLUJ)
        S["l_buc"] = ls["id"]
        assert ls.get("reference_price") is None
        assert _get_listing(specialist, S["l1"])["reference_price"] == pytest.approx(9.0)

    def test_list_filters(self, admin):
        r = admin.get(f"{R}/listings", params={"q": TAG, "limit": 50}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        ids = {i["id"] for i in _items(data)}
        assert {S["l1"], S["l2"], S["l_single"], S["l_buc"]} <= ids
        assert data["total"] >= 4
        item = next(i for i in _items(data) if i["id"] == S["l1"])
        assert item["reference_price"] == pytest.approx(9.0)
        r = admin.get(f"{R}/listings", params={"q": TAG, "locality": FLORESTI, "limit": 50}, timeout=TIMEOUT)
        ids = {i["id"] for i in _items(r.json())}
        assert S["l1"] in ids and S["l2"] not in ids
        r = admin.get(f"{R}/listings", params={"q": TAG, "category": "fructe", "limit": 50}, timeout=TIMEOUT)
        assert S["l1"] not in {i["id"] for i in _items(r.json())}
        r = admin.get(f"{R}/listings", params={"q": TAG, "limit": 1}, timeout=TIMEOUT)
        assert len(_items(r.json())) == 1

    def test_search_by_word_and_prefix(self, admin, specialist):
        ls = _create_listing(specialist, product=f"{TAG} Tomate cherry", category="legume", price_ron_per_unit=12)
        S["l_search"] = ls["id"]

        def found(q):
            r = admin.get(f"{R}/listings", params={"q": q, "limit": 50}, timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            return ls["id"] in {i["id"] for i in _items(r.json())}

        assert found(f"{TAG} tomate")            # cuvânt întreg
        assert found(f"{TAG} TOMATE")            # fără diferență de majuscule
        assert found(f"{TAG} cherr")             # prefix de cel puțin 3 litere
        assert found(f"{TAG} tom cher")          # toate cuvintele trebuie să se potrivească
        assert not found(f"{TAG} tomate banane")  # un cuvânt care nu există în anunț
        assert not found(f"{TAG} xyzabc")

    def test_seller_name_first_name_only_for_others(self, admin, specialist):
        r = admin.get(f"{R}/listings", params={"q": TAG, "limit": 50}, timeout=TIMEOUT)
        item = next(i for i in _items(r.json()) if i["id"] == S["l1"])
        assert item["seller_name"] and len(item["seller_name"].split()) == 1
        own = _get_listing(specialist, S["l1"])  # vânzătorul își vede numele întreg
        assert own["seller_name"].startswith(item["seller_name"])
        assert "product_tokens" not in item

    def test_mine(self, specialist, client):
        r = specialist.get(f"{R}/listings/mine", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ids = {i["id"] for i in _items(r.json())}
        assert S["l1"] in ids and S["l2"] not in ids
        r = client.get(f"{R}/listings/mine", timeout=TIMEOUT)
        ids = {i["id"] for i in _items(r.json())}
        assert S["l2"] in ids and S["l1"] not in ids

    def test_get_unknown_404(self, client):
        _err(client.get(f"{R}/listings/{UNKNOWN_ID}", timeout=TIMEOUT), 404)


# ── 4. reservations ──────────────────────────────────────────────────────────

class TestReservations:
    def test_anonymous_401(self, anon):
        assert anon.post(f"{R}/listings/{S['l1']}/reservations", json={"quantity": 1, "mode": "cash_on_pickup"},
                         timeout=TIMEOUT).status_code == 401
        assert anon.get(f"{R}/reservations/mine", timeout=TIMEOUT).status_code == 401

    def test_seller_cannot_reserve_own_4xx(self, specialist):
        _4xx(_reserve(specialist, S["l1"], 1))

    def test_unknown_listing_404(self, admin):
        _err(_reserve(admin, UNKNOWN_ID, 1), 404)

    def test_quantity_validation_400(self, client):
        _err(_reserve(client, S["l1"], 0), 400)
        _err(_reserve(client, S["l1"], -2), 400)
        _err(_reserve(client, S["l1"], 21), 400)  # more than available (20)
        _err(_reserve(client, S["l1"], 0.0004), 400)  # rotunjit la 0

    def test_exchange_without_offer_400(self, client):
        _err(_reserve(client, S["l1"], 3, "exchange"), 400)

    def test_mode_incompatible_with_listing_400(self, specialist):
        # L2 is sale-only
        _err(_reserve(specialist, S["l2"], 1, "exchange", exchange_offer="Ouă"), 400)

    def test_invalid_mode_400(self, client):
        _err(_reserve(client, S["l1"], 1, "bitcoin"), 400)

    def test_admin_reserves_5_cash(self, admin):
        res = _new_reservation(admin, S["l1"], 5, message=f"{TAG} rezervare")
        S["r_admin1"] = res["id"]
        assert res["listing_id"] == S["l1"]
        assert res["buyer_user_id"] == S["admin_uid"]
        assert res["seller_user_id"] == S["specialist_uid"]
        assert res["buyer_name"]
        assert res["mode"] == "cash_on_pickup"
        assert res["quantity"] == 5
        assert _avail(admin, S["l1"]) == 20  # decreases only on confirm

    def test_second_active_reservation_409(self, admin):
        _err(_reserve(admin, S["l1"], 1), 409)

    def test_client_reserves_18_exchange(self, client):
        res = _new_reservation(client, S["l1"], 18, "exchange", exchange_offer="Un coș cu mere și miere")
        S["r_client1"] = res["id"]
        assert res["mode"] == "exchange"
        assert res["exchange_offer"]
        assert res["status"] == "requested"

    def test_my_reservations_lists(self, admin, specialist):
        buyer = _mine(admin, "buyer")
        item = next(i for i in buyer if i["id"] == S["r_admin1"])
        assert TAG in item["listing_product"]
        assert item["listing_unit"] == "kg"
        assert item["counterpart_name"]
        seller = _mine(specialist, "seller")
        ids = {i["id"] for i in seller}
        assert {S["r_admin1"], S["r_client1"]} <= ids
        assert all(i["counterpart_name"] for i in seller if i["id"] in (S["r_admin1"], S["r_client1"]))
        assert S["r_admin1"] not in {i["id"] for i in _mine(specialist, "buyer")}

    def test_buyer_cannot_confirm(self, admin):
        _err(_act(admin, S["r_admin1"], "confirm"), 403)

    def test_other_member_cannot_confirm(self, client):
        _4xx(_act(client, S["r_admin1"], "confirm"))

    def test_seller_cannot_cancel_requested(self, specialist):
        _4xx(_act(specialist, S["r_admin1"], "cancel"))
        assert _mine(specialist, "seller")  # still reachable
        item = next(i for i in _mine(specialist, "seller") if i["id"] == S["r_admin1"])
        assert item["status"] == "requested"

    def test_seller_confirms_admin(self, specialist, admin):
        r = _act(specialist, S["r_admin1"], "confirm")
        assert _res_status(r) == "confirmed"
        assert _avail(admin, S["l1"]) == 15

    def test_confirm_again_409(self, specialist):
        _err(_act(specialist, S["r_admin1"], "confirm"), 409)

    def test_confirm_client_not_enough_409(self, specialist, admin):
        _err(_act(specialist, S["r_client1"], "confirm"), 409)
        assert _avail(admin, S["l1"]) == 15

    def test_decline_client(self, specialist, client):
        assert _res_status(_act(specialist, S["r_client1"], "decline")) == "declined"
        item = next(i for i in _mine(client, "buyer") if i["id"] == S["r_client1"])
        assert item["status"] == "declined"
        _err(_act(specialist, S["r_client1"], "decline"), 409)

    def test_buyer_cancels_confirmed_restores_quantity(self, admin):
        assert _res_status(_act(admin, S["r_admin1"], "cancel")) == "cancelled"
        assert _avail(admin, S["l1"]) == 20
        _err(_act(admin, S["r_admin1"], "cancel"), 409)

    def test_admin_reserves_again_and_gets_picked_up(self, admin, specialist, client):
        res = _new_reservation(admin, S["l1"], 4)
        S["r_admin2"] = res["id"]
        assert _res_status(_act(specialist, S["r_admin2"], "confirm")) == "confirmed"
        assert _avail(admin, S["l1"]) == 16
        # only the seller marks pickup
        _err(_act(admin, S["r_admin2"], "picked-up"), 403)
        assert _res_status(_act(specialist, S["r_admin2"], "picked-up")) == "picked_up"
        assert _avail(admin, S["l1"]) == 16  # stays reduced
        _err(_act(specialist, S["r_admin2"], "no-show"), 409)

    def test_rating_before_pickup_rejected(self, client, specialist):
        res = _new_reservation(client, S["l1"], 2)
        S["r_client2"] = res["id"]
        _4xx(_act(client, S["r_client2"], "rate", rating=5))
        # clean up: seller declines it so the buyer is free again
        assert _res_status(_act(specialist, S["r_client2"], "decline")) == "declined"

    def test_rate_validation(self, admin):
        _err(_act(admin, S["r_admin2"], "rate", rating=0), 400)
        _err(_act(admin, S["r_admin2"], "rate", rating=6), 400)
        _err(_act(admin, S["r_admin2"], "rate", rating=5, comment="x" * 301), 400)

    def test_only_buyer_can_rate(self, specialist, client):
        _err(_act(specialist, S["r_admin2"], "rate", rating=5), 403)
        _4xx(_act(client, S["r_admin2"], "rate", rating=5))

    def test_admin_rates_5(self, admin):
        r = _act(admin, S["r_admin2"], "rate", rating=5, comment=f"{TAG} super")
        assert r.status_code == 200, r.text
        res = _unwrap(r.json(), "reservation")
        assert res["rating"] == 5
        assert res["rating_comment"] == f"{TAG} super"
        assert res["status"] == "picked_up"

    def test_rate_again_rejected(self, admin):
        _4xx(_act(admin, S["r_admin2"], "rate", rating=1))
        item = next(i for i in _mine(admin, "buyer") if i["id"] == S["r_admin2"])
        assert item["rating"] == 5

    def test_seller_rating(self, client):
        data = _seller_rating(client, S["specialist_uid"])
        assert data["avg"] == pytest.approx(5.0)
        assert data["count"] == 1

    def test_seller_rating_without_ratings(self, client):
        data = _seller_rating(client, S["admin_uid"])
        assert data["count"] == 0

    def test_seller_cancel_confirmed_restores_quantity(self, admin, specialist):
        res = _new_reservation(admin, S["l1"], 3)
        assert _res_status(_act(specialist, res["id"], "confirm")) == "confirmed"
        assert _avail(admin, S["l1"]) == 13
        assert _res_status(_act(specialist, res["id"], "cancel")) == "cancelled"
        assert _avail(admin, S["l1"]) == 16

    def test_no_show_restores_quantity(self, client, specialist):
        res = _new_reservation(client, S["l1"], 6)
        S["r_client3"] = res["id"]
        assert _res_status(_act(specialist, S["r_client3"], "confirm")) == "confirmed"
        assert _avail(client, S["l1"]) == 10
        assert _res_status(_act(specialist, S["r_client3"], "no-show")) == "no_show"
        assert _avail(client, S["l1"]) == 16
        _4xx(_act(client, S["r_client3"], "rate", rating=3))
        _err(_act(specialist, S["r_client3"], "picked-up"), 409)

    def test_no_show_does_not_count_in_rating(self, client):
        data = _seller_rating(client, S["specialist_uid"])
        assert data["count"] == 1


# ── 5. listing PATCH / close ─────────────────────────────────────────────────

class TestListingPatchAndClose:
    def test_setup_l3(self, specialist, client, admin):
        ls = _create_listing(specialist, product=f"{TAG} ardei", unit="kg", quantity_total=10,
                             price_ron_per_unit=5, mode="sale", exchange_for=None)
        S["l3"] = ls["id"]
        res = _new_reservation(client, S["l3"], 4)
        S["r_l3_client"] = res["id"]
        assert _res_status(_act(specialist, S["r_l3_client"], "confirm")) == "confirmed"
        assert _avail(client, S["l3"]) == 6
        res = _new_reservation(admin, S["l3"], 2)
        S["r_l3_admin"] = res["id"]

    def test_non_seller_cannot_patch(self, client):
        r = client.patch(f"{R}/listings/{S['l3']}", json={"quantity_total": 20}, timeout=TIMEOUT)
        _err(r, 403)

    def test_lower_total_below_confirmed_400(self, specialist):
        r = specialist.patch(f"{R}/listings/{S['l3']}", json={"quantity_total": 3}, timeout=TIMEOUT)
        _err(r, 400)
        assert _get_listing(specialist, S["l3"])["quantity_total"] == 10

    def test_invalid_patch_values_400(self, specialist):
        _err(specialist.patch(f"{R}/listings/{S['l3']}", json={"quantity_total": 0}, timeout=TIMEOUT), 400)
        _err(specialist.patch(f"{R}/listings/{S['l3']}", json={"price_ron_per_unit": -1}, timeout=TIMEOUT), 400)

    def test_patch_unknown_404(self, specialist):
        _err(specialist.patch(f"{R}/listings/{UNKNOWN_ID}", json={"quantity_total": 5}, timeout=TIMEOUT), 404)

    def test_patch_ok(self, specialist):
        r = specialist.patch(
            f"{R}/listings/{S['l3']}",
            json={"quantity_total": 12, "price_ron_per_unit": 6},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        ls = _unwrap(r.json(), "listing")
        assert ls["quantity_total"] == 12
        assert ls["price_ron_per_unit"] == 6

    def test_non_seller_cannot_close(self, client):
        _err(client.post(f"{R}/listings/{S['l3']}/close", timeout=TIMEOUT), 403)

    def test_visible_before_close(self, admin):
        r = admin.get(f"{R}/listings", params={"q": TAG, "limit": 50}, timeout=TIMEOUT)
        assert S["l3"] in {i["id"] for i in _items(r.json())}

    def test_close(self, specialist, admin):
        r = specialist.post(f"{R}/listings/{S['l3']}/close", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "listing")["status"] == "closed"
        # requested reservations are cancelled automatically
        item = next(i for i in _mine(admin, "buyer") if i["id"] == S["r_l3_admin"])
        assert item["status"] == "cancelled"

    def test_closed_not_in_public_list(self, admin):
        r = admin.get(f"{R}/listings", params={"q": TAG, "limit": 50}, timeout=TIMEOUT)
        ids = {i["id"] for i in _items(r.json())}
        assert S["l3"] not in ids
        assert S["l1"] in ids

    def test_reserve_on_closed_4xx(self, admin):
        _4xx(_reserve(admin, S["l3"], 1))

    def test_patch_or_close_closed_4xx(self, specialist):
        _4xx(specialist.patch(f"{R}/listings/{S['l3']}", json={"quantity_total": 20}, timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/listings/{S['l3']}/close", timeout=TIMEOUT))


# ── 5b. hardening: serialization, PATCH rules, visibility ────────────────────

class TestHardening:
    def test_setup_l4(self, specialist):
        ls = _create_listing(specialist, product=f"{TAG} cartofi", unit="kg", quantity_total=10,
                             price_ron_per_unit=3, mode="sale", exchange_for=None)
        S["l4"] = ls["id"]

    def test_double_click_reservation_one_wins(self, client):
        with ThreadPoolExecutor(max_workers=2) as pool:
            rs = list(pool.map(lambda _: _reserve(client, S["l4"], 2), range(2)))
        codes = sorted(r.status_code for r in rs)
        assert codes[0] in (200, 201) and codes[1] == 409, [(r.status_code, r.text[:120]) for r in rs]
        ok = next(r for r in rs if r.status_code in (200, 201))
        S["r_l4"] = _unwrap(ok.json(), "reservation")["id"]
        active = [i for i in _mine(client, "buyer") if i["listing_id"] == S["l4"] and i["status"] == "requested"]
        assert len(active) == 1

    def test_patch_unit_with_requested_reservation_409(self, specialist):
        r = specialist.patch(f"{R}/listings/{S['l4']}", json={"unit": "buc"}, timeout=TIMEOUT)
        _err(r, 409)
        assert _get_listing(specialist, S["l4"])["unit"] == "kg"

    def test_patch_mode_with_requested_reservation_409(self, specialist):
        r = specialist.patch(
            f"{R}/listings/{S['l4']}", json={"mode": "exchange", "exchange_for": "Ouă de țară"}, timeout=TIMEOUT
        )
        _err(r, 409)
        assert _get_listing(specialist, S["l4"])["mode"] == "sale"

    def test_patch_total_counts_requested_reservations(self, specialist):
        # 2 kg sunt doar „requested”, dar tot rezervate
        _err(specialist.patch(f"{R}/listings/{S['l4']}", json={"quantity_total": 1}, timeout=TIMEOUT), 400)
        r = specialist.patch(f"{R}/listings/{S['l4']}", json={"quantity_total": 2}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ls = _unwrap(r.json(), "listing")
        assert ls["quantity_total"] == 2 and ls["quantity_available"] == 2
        r = specialist.patch(f"{R}/listings/{S['l4']}", json={"quantity_total": 10}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text

    def test_patch_unit_allowed_after_decline(self, specialist):
        assert _res_status(_act(specialist, S["r_l4"], "decline")) == "declined"
        r = specialist.patch(f"{R}/listings/{S['l4']}", json={"unit": "buc"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "listing")["unit"] == "buc"

    def test_closed_listing_visible_only_to_seller_and_reservers(self, specialist, client, admin):
        # client a rezervat din l4 (acum refuzată) → vede anunțul închis; admin nu are nicio legătură cu el
        r = specialist.post(f"{R}/listings/{S['l4']}/close", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _get_listing(specialist, S["l4"])["status"] == "closed"
        assert _get_listing(client, S["l4"])["status"] == "closed"
        _err(admin.get(f"{R}/listings/{S['l4']}", timeout=TIMEOUT), 404)

    def test_closed_without_reservation_404(self, specialist, admin):
        ls = _create_listing(specialist, product=f"{TAG} gutui", quantity_total=3)
        assert _get_listing(admin, ls["id"])["status"] == "active"
        assert specialist.post(f"{R}/listings/{ls['id']}/close", timeout=TIMEOUT).status_code == 200
        _err(admin.get(f"{R}/listings/{ls['id']}", timeout=TIMEOUT), 404)
        assert _get_listing(specialist, ls["id"])["status"] == "closed"


class TestPureHelpers:
    """Funcții pure din backend (fără HTTP); sar dacă modulele nu pot fi importate din directorul curent."""

    @staticmethod
    def _mods():
        backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if backend not in sys.path:
            sys.path.insert(0, backend)
        try:
            from routes.radacini import harvests, market
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"backend nu poate fi importat: {exc}")
        return harvests, market

    def test_owner_share_rounding_and_min_q(self):
        harvests, _ = self._mods()
        assert harvests.owner_share(100, 30) == 30.0
        assert harvests.owner_share(33.3, 30) == 10.0       # 9,99 → 10,0
        assert harvests.owner_share(0.05, 100) == 0.05      # round(0,05; 1)=0,1 > q → min(q)
        assert harvests.owner_share(10, 150) == 10.0        # niciodată peste recoltă
        assert harvests.owner_share(0.04, 30) == pytest.approx(0.012)  # 0,1 kg ar da 0: se păstrează valoarea exactă

    def test_quantity_validated_after_rounding(self):
        harvests, market = self._mods()
        assert harvests._checked_qty(0.0006, "x") == 0.001
        for bad in (0.0004, 0, -1, float("nan"), float("inf"), 1_000_001):
            with pytest.raises(ValueError):
                harvests._checked_qty(bad, "x")
        for bad in (0.0004, float("nan"), float("inf"), 1_000_001):
            with pytest.raises(ValueError):
                market._checked_qty(bad)

    def test_product_tokens_words_and_prefixes(self):
        _, market = self._mods()
        tokens = market.product_tokens("Roșii cherry")
        assert tokens[:2] == ["rosii", "cherry"]
        assert {"ros", "rosi", "cher", "cherr"} <= set(tokens)
        assert "ro" not in tokens
        assert len(market.product_tokens(f"{'a' * 25} {'b' * 30} {'c' * 30}")) <= 40  # plafon de intrări
        assert market.search_tokens("Roșii CHER") == ["rosii", "cher"]
        assert market.search_tokens("ro") == ["ro"]


# ── 6. completed project ─────────────────────────────────────────────────────

class TestCompletedProject:
    def test_complete_project(self, specialist):
        r = specialist.post(f"{_pr()}/complete", timeout=TIMEOUT)
        assert r.status_code == 200, r.text

    def test_record_harvest_409(self, specialist):
        _err(_record(specialist, crop="porumb", quantity_kg=10), 409)

    def test_recipient_can_still_mark_received(self, client):
        r = client.post(f"{R}/allocations/{S['a_owner']}/received", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "allocation")["status"] == "received"
