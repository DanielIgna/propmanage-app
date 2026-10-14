"""Rădăcini S6 D/E/F — HTTP integration tests (contract: docs/radacini/PLAN.md, "S6 — contract", D, E, F).

Run against a live backend:
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s6b.py -q --noconftest

Roles: client = parcel owner / listing seller, specialist = buyer (not staff), admin = super-admin (manager).
Everything carries a unique TEST-RAD-<hex> tag; parcels are archived and listings closed at teardown.
"""
import os
import uuid

import pytest
import requests

API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
CLIENT_EMAIL, CLIENT_PASSWORD = "client@propmanage.io", "Client123!"
SPECIALIST_EMAIL, SPECIALIST_PASSWORD = "specialist@propmanage.io", "Spec123!"

R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20

CLUJ, FLORESTI = "Cluj-Napoca", "Florești"
CLUJ_LAT, CLUJ_LNG = 46.77123, 23.62356
FLO_LAT, FLO_LNG = 46.74401, 23.48903

# ~0.85 km2 square around the Cluj point (longitude, latitude)
_SQ = [[23.6200, 46.7700], [23.6300, 46.7700], [23.6300, 46.7780], [23.6200, 46.7780]]
POLY = {"type": "Polygon", "coordinates": [_SQ + [_SQ[0]]]}
POLY_AREA = 650_000  # about right (declared), avoids the 30% warning
BOWTIE = {"type": "Polygon", "coordinates": [[[23.62, 46.77], [23.63, 46.78], [23.63, 46.77], [23.62, 46.78], [23.62, 46.77]]]}

S = {}
_parcels = []
_listings = {}


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


def _parcel_payload(suffix, lat, lng, locality, area=POLY_AREA, **over):
    p = {
        "title": f"{TAG} teren {suffix}",
        "county": "Cluj",
        "locality": locality,
        "lat": lat,
        "lng": lng,
        "area_m2": area,
        "access": "Drum de pământ",
        "water_sources": ["well"],
        "current_crops": [],
        "description": "Teren de test S6.",
        "offer": {"models": ["rent"], "price_ron_per_year": 1000},
    }
    p.update(over)
    return p


def _ensure_member(session, interests, locality):
    r = session.put(
        f"{R}/members/me", json={"interests": interests, "county": "Cluj", "locality": locality}, timeout=TIMEOUT
    )
    assert r.status_code == 200, r.text


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
    _ensure_member(client, ["land", "sell"], CLUJ)
    _ensure_member(specialist, ["grow", "consume"], FLORESTI)
    _ensure_member(admin, ["grow"], CLUJ)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, _members):
    yield
    for lid in list(_listings):
        try:
            client.post(f"{R}/listings/{lid}/close", timeout=TIMEOUT)
        except Exception:
            pass
    for pid in _parcels:
        try:
            client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        except Exception:
            pass


def _publish(client, admin, payload):
    r = client.post(f"{R}/parcels", json=payload, timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    pid = _unwrap(r.json(), "parcel")["id"]
    _parcels.append(pid)
    assert client.post(f"{R}/parcels/{pid}/submit", timeout=TIMEOUT).status_code == 200
    r = admin.post(f"{R}/staff/parcels/{pid}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return pid


# ── D. polygon ───────────────────────────────────────────────────────────────

class TestPolygon:
    def test_invalid_polygons_400(self, client):
        bad = [
            BOWTIE,
            {"type": "Point", "coordinates": [23.6, 46.7]},
            {"type": "Polygon", "coordinates": [[[23.62, 46.77], [23.63, 46.77], [23.62, 46.77]]]},  # 2 vertices
            {"type": "Polygon", "coordinates": [[[100, 10], [101, 10], [101, 11], [100, 10]]]},  # outside Romania
            {"type": "Polygon", "coordinates": [[[23.6 + i * 0.0001, 46.77 + (i % 2) * 0.0001] for i in range(101)]]},
        ]
        for geom in bad:
            r = client.post(f"{R}/parcels", json=_parcel_payload("bad", CLUJ_LAT, CLUJ_LNG, CLUJ, geometry=geom), timeout=TIMEOUT)
            assert r.status_code == 400, f"{geom} -> {r.status_code} {r.text[:200]}"
            assert isinstance(r.json().get("detail"), str)

    def test_valid_polygon_stored_with_area(self, client):
        r = client.post(f"{R}/parcels", json=_parcel_payload("poly", CLUJ_LAT, CLUJ_LNG, CLUJ, geometry=POLY), timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        assert "geometry_warning" not in r.json()
        parcel = _unwrap(r.json(), "parcel")
        _parcels.append(parcel["id"])
        S["poly_pid"] = parcel["id"]
        assert parcel["geometry"]["type"] == "Polygon"
        assert 400_000 < parcel["geometry_area_m2"] < 900_000

    def test_area_mismatch_warning(self, client):
        r = client.post(
            f"{R}/parcels", json=_parcel_payload("warn", CLUJ_LAT, CLUJ_LNG, CLUJ, area=1000, geometry=POLY), timeout=TIMEOUT
        )
        assert r.status_code in (200, 201), r.text
        _parcels.append(_unwrap(r.json(), "parcel")["id"])
        assert isinstance(r.json().get("geometry_warning"), str)

    def test_patch_geometry_invalid_400(self, client):
        r = client.patch(f"{R}/parcels/{S['poly_pid']}", json={"geometry": BOWTIE}, timeout=TIMEOUT)
        assert r.status_code == 400, r.text

    def test_owner_sees_geometry_public_does_not(self, client, admin, anon):
        pid = S["poly_pid"]
        r = client.get(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        assert _unwrap(r.json(), "parcel").get("geometry")
        assert client.post(f"{R}/parcels/{pid}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{pid}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = anon.get(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        pub = _unwrap(r.json(), "parcel")
        assert "geometry" not in pub and "geometry_area_m2" not in pub
        assert '"geometry":' not in r.text and '"geometry_area_m2"' not in r.text  # only has_geometry is public
        r = anon.get(f"{R}/parcels", params={"limit": 50}, timeout=TIMEOUT)
        assert all("geometry" not in p for p in r.json()["items"])


# ── D. distance search ───────────────────────────────────────────────────────

class TestNear:
    def test_near_sorted_by_distance(self, client, admin, anon):
        near_pid = _publish(client, admin, _parcel_payload("near", CLUJ_LAT, CLUJ_LNG, CLUJ))
        far_pid = _publish(client, admin, _parcel_payload("far", FLO_LAT, FLO_LNG, FLORESTI))
        r = anon.get(
            f"{R}/parcels", params={"near": f"{CLUJ_LAT},{CLUJ_LNG}", "radius_km": 25, "limit": 50}, timeout=TIMEOUT
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        dists = [i["distance_km"] for i in items]
        assert dists == sorted(dists)
        ids = [i["id"] for i in items]
        assert near_pid in ids and far_pid in ids
        assert ids.index(near_pid) < ids.index(far_pid)
        far = items[ids.index(far_pid)]
        assert 9 <= far["distance_km"] <= 13
        assert far["lat"] == round(far["lat"], 2)  # public coordinates stay rounded

    def test_small_radius_excludes_far(self, client, anon):
        r = anon.get(f"{R}/parcels", params={"near": f"{CLUJ_LAT},{CLUJ_LNG}", "radius_km": 2, "limit": 50}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert all(i["distance_km"] <= 2 for i in r.json()["items"])

    def test_bad_radius_and_near_400(self, anon):
        for params in (
            {"near": "46.77,23.62", "radius_km": 0},
            {"near": "46.77,23.62", "radius_km": 101},
            {"near": "46.77,23.62", "radius_km": 0.5},
            {"near": "abc", "radius_km": 10},
            {"near": "10,10", "radius_km": 10},
            {"radius_km": 10},
        ):
            r = anon.get(f"{R}/parcels", params=params, timeout=TIMEOUT)
            assert r.status_code == 400, f"{params} -> {r.status_code} {r.text[:200]}"

    def test_listings_near_locality(self, client, specialist):
        body = {
            "product": f"{TAG} mere", "category": "fructe", "unit": "kg", "quantity_total": 10,
            "price_ron_per_unit": 5, "mode": "sale", "locality": FLORESTI, "pickup_details": "La poartă, după 17",
        }
        r = client.post(f"{R}/listings", json=body, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        lid = _unwrap(r.json(), "listing")["id"]
        _listings[lid] = client
        r = specialist.get(f"{R}/listings", params={"near_locality": CLUJ, "radius_km": 20, "q": TAG}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        item = next(i for i in r.json()["items"] if i["id"] == lid)
        assert 9 <= item["distance_km"] <= 13
        r = specialist.get(f"{R}/listings", params={"near_locality": CLUJ, "radius_km": 2, "q": TAG}, timeout=TIMEOUT)
        assert all(i["id"] != lid for i in r.json()["items"])
        for params in ({"near_locality": "Nicăieri", "radius_km": 10}, {"near_locality": CLUJ, "radius_km": 500}):
            assert specialist.get(f"{R}/listings", params=params, timeout=TIMEOUT).status_code == 400


# ── E. disputes ──────────────────────────────────────────────────────────────

class TestDisputes:
    def test_setup_reservation(self, client, specialist):
        body = {
            "product": f"{TAG} roșii", "category": "legume", "unit": "kg", "quantity_total": 20,
            "price_ron_per_unit": 8, "mode": "sale", "locality": CLUJ, "pickup_details": "La poartă, după 17",
        }
        r = client.post(f"{R}/listings", json=body, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        lid = _unwrap(r.json(), "listing")["id"]
        _listings[lid] = client
        S["lid"] = lid
        r = specialist.post(f"{R}/listings/{lid}/reservations", json={"quantity": 2, "mode": "cash_on_pickup"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        S["rid"] = _unwrap(r.json(), "reservation")["id"]

    def test_validation(self, client):
        for body in (
            {"scope_type": "reservation", "scope_id": S["rid"], "reason": "scurt"},
            {"scope_type": "altceva", "scope_id": S["rid"], "reason": "Motiv suficient de lung"},
        ):
            assert client.post(f"{R}/disputes", json=body, timeout=TIMEOUT).status_code == 400
        r = client.post(f"{R}/disputes", json={"scope_type": "reservation", "scope_id": "0" * 24, "reason": "Motiv suficient de lung"}, timeout=TIMEOUT)
        assert r.status_code == 404

    def test_non_party_cannot_open(self, admin):
        r = admin.post(f"{R}/disputes", json={"scope_type": "reservation", "scope_id": S["rid"], "reason": f"{TAG} nu sunt parte"}, timeout=TIMEOUT)
        assert r.status_code == 403, r.text

    def test_party_opens_and_duplicate_409(self, client, specialist):
        r = client.post(f"{R}/disputes", json={"scope_type": "reservation", "scope_id": S["rid"], "reason": f"{TAG} nu s-a prezentat"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        d = _unwrap(r.json(), "dispute")
        assert d["status"] == "open" and d["scope_type"] == "reservation"
        S["did"] = d["id"]
        r = specialist.post(f"{R}/disputes", json={"scope_type": "reservation", "scope_id": S["rid"], "reason": f"{TAG} dublura"}, timeout=TIMEOUT)
        assert r.status_code == 409, r.text

    def test_mine_and_get(self, client, specialist, admin):
        for s in (client, specialist):
            r = s.get(f"{R}/disputes/mine", timeout=TIMEOUT)
            assert r.status_code == 200
            assert any(i["id"] == S["did"] for i in r.json()["items"])
            assert s.get(f"{R}/disputes/{S['did']}", timeout=TIMEOUT).status_code == 200

    def test_take_by_non_staff_403(self, specialist):
        r = specialist.post(f"{R}/disputes/{S['did']}/take", timeout=TIMEOUT)
        assert r.status_code == 403, r.text

    def test_staff_queue_and_take(self, admin):
        r = admin.get(f"{R}/staff/disputes", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert any(i["id"] == S["did"] for i in r.json()["items"])
        r = admin.post(f"{R}/disputes/{S['did']}/take", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "dispute")["status"] == "in_mediation"
        assert admin.post(f"{R}/disputes/{S['did']}/take", timeout=TIMEOUT).status_code == 409

    def test_messages(self, client, specialist, admin):
        r = specialist.post(f"{R}/disputes/{S['did']}/messages", json={"text": f"{TAG} am fost acolo"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert admin.post(f"{R}/disputes/{S['did']}/messages", json={"text": "Mediator: vă rog detalii"}, timeout=TIMEOUT).status_code == 200
        r = client.get(f"{R}/disputes/{S['did']}", timeout=TIMEOUT)
        assert len(_unwrap(r.json(), "dispute")["messages"]) == 2
        assert client.post(f"{R}/disputes/{S['did']}/messages", json={"text": "  "}, timeout=TIMEOUT).status_code == 400

    def test_resolve(self, client, specialist, admin):
        assert specialist.post(f"{R}/disputes/{S['did']}/resolve", json={"decision": "resolved", "note": "x" * 5}, timeout=TIMEOUT).status_code == 403
        assert admin.post(f"{R}/disputes/{S['did']}/resolve", json={"decision": "resolved"}, timeout=TIMEOUT).status_code == 400
        assert admin.post(f"{R}/disputes/{S['did']}/resolve", json={"decision": "resolved", "note": " "}, timeout=TIMEOUT).status_code == 400
        r = admin.post(f"{R}/disputes/{S['did']}/resolve", json={"decision": "resolved", "note": f"{TAG} părțile s-au înțeles"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = _unwrap(r.json(), "dispute")
        assert d["status"] == "resolved" and d["resolution"]["note"]
        assert admin.post(f"{R}/disputes/{S['did']}/resolve", json={"decision": "resolved", "note": "din nou"}, timeout=TIMEOUT).status_code == 409
        assert client.post(f"{R}/disputes/{S['did']}/messages", json={"text": "târziu"}, timeout=TIMEOUT).status_code == 409


# ── F. public endpoints ──────────────────────────────────────────────────────

class TestPublic:
    def test_public_listings_anonymous(self, anon):
        r = anon.get(f"{R}/public/listings", params={"q": TAG, "limit": 50}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        mine = [i for i in items if i["id"] == S["lid"]]
        assert mine, "active test listing must be public"
        item = mine[0]
        assert "pickup_details" not in item and "is_mine" not in item and "seller_user_id" not in item
        assert " " not in item["seller_name"]  # first name only
        assert "pickup_details" not in r.text

    def test_public_listings_filters_and_limit(self, anon):
        r = anon.get(f"{R}/public/listings", params={"locality": CLUJ, "category": "legume", "q": TAG}, timeout=TIMEOUT)
        assert r.status_code == 200 and any(i["id"] == S["lid"] for i in r.json()["items"])
        assert anon.get(f"{R}/public/listings", params={"limit": 51}, timeout=TIMEOUT).status_code == 400
        assert anon.get(f"{R}/public/listings", params={"category": "nu-exista"}, timeout=TIMEOUT).status_code == 400

    def test_public_communities_anonymous(self, anon):
        r = anon.get(f"{R}/public/communities", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        for c in r.json()["items"]:
            assert set(c) == {"id", "name", "locality", "description", "members_count"}
