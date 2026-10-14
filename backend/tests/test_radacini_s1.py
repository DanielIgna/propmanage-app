"""Rădăcini S1 — HTTP integration tests (contract: docs/radacini/PLAN.md, "S1 — contract").

Run against a live backend:
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s1.py -q --noconftest

The tests form one ordered scenario (state is carried in the `S` dict); every
parcel created is archived at module teardown. Titles carry a unique TEST-RAD-<hex> tag.
"""
import json
import os
import uuid

import pytest
import requests

# Independent of tests/test_config.py (its isolation gate targets the legacy Mongo suite).
# Rădăcini only writes app.radacini_* tables; demo accounts come from backend/seed.py.
# Run with --noconftest.
API = f"{os.environ['REACT_APP_BACKEND_URL'].rstrip('/')}/api"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "admin@propmanage.io")
ADMIN_PASSWORDS = list(dict.fromkeys([p for p in (os.environ.get("SEED_ADMIN_PASSWORD"), "Admin123!") if p]))
CLIENT_EMAIL, CLIENT_PASSWORD = "client@propmanage.io", "Client123!"
SPECIALIST_EMAIL, SPECIALIST_PASSWORD = "specialist@propmanage.io", "Spec123!"

R = f"{API}/radacini"
TAG = f"TEST-RAD-{uuid.uuid4().hex[:6]}"
TIMEOUT = 20

INTEREST_IDS = {"grow", "consume", "land", "sell", "exchange", "community"}
MODEL_IDS = {"rent", "harvest_share", "fixed_fee", "mixed", "sale", "joint_project"}
WATER_IDS = {"well", "river", "network", "irrigation", "none"}

CLUJ = "Cluj-Napoca"
FLORESTI = "Florești"

# Exact coordinates (more than 2 decimals on purpose)
LAT, LNG = 46.77123, 23.62356

# Shared state across the ordered scenario
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
    """Return data[key] if the response wraps the document, else the document itself."""
    if isinstance(data, dict) and isinstance(data.get(key), dict):
        return data[key]
    return data


def _items(data):
    """Extract a list of documents from a list-or-envelope response."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items", "parcels", "staff", "queue", "results", "data"):
            if isinstance(data.get(k), list):
                return data[k]
        for v in data.values():
            if isinstance(v, list):
                return v
    raise AssertionError(f"No list found in response: {str(data)[:200]}")


def _parcel_payload(title_suffix="", locality=CLUJ, **over):
    p = {
        "title": f"{TAG} teren {title_suffix}".strip(),
        "county": "Cluj",
        "locality": locality,
        "lat": LAT,
        "lng": LNG,
        "area_m2": 1500,
        "access": "Drum de pământ, acces auto",
        "water_sources": ["well"],
        "current_crops": ["porumb"],
        "description": "Teren de test pentru integrare.",
        "offer": {"models": ["rent"], "terms": "Termeni de test", "price_ron_per_year": 1200},
    }
    p.update(over)
    return p


def _create_parcel(session, **kw):
    r = session.post(f"{R}/parcels", json=_parcel_payload(**kw), timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    doc = _unwrap(r.json(), "parcel")
    assert doc.get("id")
    _created_ids.append(doc["id"])
    return doc


def _public_find(pid, **params):
    """Search the anonymous public list (paging) for a parcel id; return the doc or None."""
    anon = requests.Session()
    skip = 0
    for _ in range(10):
        q = dict(params, limit=50, skip=skip)
        r = anon.get(f"{R}/parcels", params=q, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        items = _items(r.json())
        for it in items:
            if it.get("id") == pid:
                return it
        if len(items) < 50:
            return None
        skip += 50
    return None


def _owner_get(session, pid):
    r = session.get(f"{R}/parcels/{pid}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return _unwrap(r.json(), "parcel")


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


@pytest.fixture(scope="module")
def specialist_id(specialist):
    r = specialist.get(f"{API}/auth/me", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    me = r.json()
    me = me.get("user", me) if isinstance(me, dict) else me
    uid = me.get("id") or me.get("user_id")
    assert uid
    return uid


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, admin, specialist_id):
    # Make sure the specialist is not left over as staff from a previous failed run
    admin.delete(f"{R}/staff/{specialist_id}", timeout=TIMEOUT)
    yield
    # Teardown: staff, then parcels
    try:
        admin.delete(f"{R}/staff/{specialist_id}", timeout=TIMEOUT)
    except Exception:
        pass
    for pid in _created_ids:
        try:
            r = client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
            if r.status_code == 409:  # still pending_verification: reject, then archive
                admin.post(
                    f"{R}/staff/parcels/{pid}/verify",
                    json={"decision": "reject", "note": "cleanup test"},
                    timeout=TIMEOUT,
                )
                client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        except Exception:
            pass


# ── 1. meta ──────────────────────────────────────────────────────────────────

class TestMeta:
    def test_meta_public(self, anon):
        r = anon.get(f"{R}/meta", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert INTEREST_IDS <= {i["id"] for i in d["interests"]}
        assert MODEL_IDS <= {i["id"] for i in d["offer_models"]}
        # legal gate: sale / joint_project stay listed (display) but cannot be requested yet
        requestable = {i["id"]: i.get("requestable") for i in d["offer_models"]}
        assert requestable["sale"] is False and requestable["joint_project"] is False
        assert all(requestable[m] is True for m in ("rent", "harvest_share", "fixed_fee", "mixed"))
        assert WATER_IDS <= {i["id"] for i in d["water_sources"]}
        assert CLUJ in d["localities"]
        assert FLORESTI in d["localities"]


# ── 2. members ───────────────────────────────────────────────────────────────

class TestMembers:
    def test_me_requires_auth(self, anon):
        assert anon.get(f"{R}/members/me", timeout=TIMEOUT).status_code == 401

    def test_put_requires_auth(self, anon):
        r = anon.put(
            f"{R}/members/me",
            json={"interests": ["grow"], "county": "Cluj", "locality": CLUJ},
            timeout=TIMEOUT,
        )
        assert r.status_code == 401

    @pytest.mark.parametrize(
        "body",
        [
            {"interests": [], "county": "Cluj", "locality": CLUJ},
            {"interests": ["nope"], "county": "Cluj", "locality": CLUJ},
            {"interests": ["grow"], "county": "Cluj", "locality": "Atlantida"},
            {"interests": ["grow"], "county": "Cluj", "locality": CLUJ, "bio": "x" * 501},
        ],
        ids=["empty_interests", "unknown_interest", "bad_locality", "bio_too_long"],
    )
    def test_put_validation(self, client, body):
        r = client.put(f"{R}/members/me", json=body, timeout=TIMEOUT)
        assert r.status_code in (400, 422), r.text

    def test_put_valid_then_get(self, client):
        body = {
            "interests": ["grow", "consume"],
            "county": "Cluj",
            "locality": CLUJ,
            "bio": f"{TAG} bio",
        }
        r = client.put(f"{R}/members/me", json=body, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        m = _unwrap(r.json(), "member")
        assert set(m["interests"]) == {"grow", "consume"}

        r = client.get(f"{R}/members/me", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert d["exists"] is True
        member = d["member"]
        assert set(member["interests"]) == {"grow", "consume"}
        assert member["locality"] == CLUJ
        assert member["county"] == "Cluj"
        assert member["id"] and member["user_id"]


# ── 3. parcels as client ─────────────────────────────────────────────────────

class TestParcelFlow:
    def test_create_requires_auth(self, anon):
        r = anon.post(f"{R}/parcels", json=_parcel_payload(), timeout=TIMEOUT)
        assert r.status_code == 401

    @pytest.mark.parametrize(
        "over",
        [
            {"area_m2": 50},
            {"lat": 10},
            {"lng": 5},
            {"title": "ab"},
            {"locality": "Atlantida"},
            {"offer": {"models": [], "terms": "x"}},
            {"offer": {"models": ["rent"], "terms": "x", "harvest_share_percent": 30}},
            {"offer": {"models": ["harvest_share"], "terms": "x", "harvest_share_percent": 95}},
            {"offer": {"models": ["harvest_share"], "terms": "x"}},
            {"offer": {"models": ["mixed"], "terms": "x", "price_ron_per_year": 100, "harvest_share_percent": 95}},
            {"offer": {"models": ["mixed"], "terms": "x", "harvest_share_percent": 0}},
            {"offer": {"models": ["rent"], "terms": "x", "price_ron_per_year": 10_000_001}},
            {"offer": {"models": ["rent"], "terms": "x", "price_ron_per_year": -1}},
        ],
        ids=[
            "area_too_small", "lat_out_of_range", "lng_out_of_range", "title_too_short",
            "bad_locality", "models_empty", "share_percent_without_model", "share_percent_too_high",
            "share_percent_missing", "mixed_percent_too_high", "mixed_percent_zero",
            "price_over_max", "price_negative",
        ],
    )
    def test_create_invalid(self, client, over):
        r = client.post(f"{R}/parcels", json=_parcel_payload("invalid", **over), timeout=TIMEOUT)
        if r.status_code in (200, 201):  # track so teardown archives it, then fail
            _created_ids.append(_unwrap(r.json(), "parcel").get("id"))
        assert 400 <= r.status_code < 500, r.text

    @pytest.mark.parametrize("literal", ["NaN", "Infinity", "1e999"])
    def test_create_non_finite_price_400(self, client, literal):
        """JSON non-finite numbers (NaN/Infinity) must not pass as a price."""
        raw = json.dumps(_parcel_payload("nan")).replace('"price_ron_per_year": 1200', f'"price_ron_per_year": {literal}')
        assert f'"price_ron_per_year": {literal}' in raw
        r = client.post(f"{R}/parcels", data=raw, headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
        if r.status_code in (200, 201):
            _created_ids.append(_unwrap(r.json(), "parcel").get("id"))
        assert r.status_code == 400, r.text
        assert isinstance(r.json().get("detail"), str)

    def test_create_valid(self, client):
        doc = _create_parcel(client, title_suffix="principal")
        S["pid"] = doc["id"]
        assert doc["status"] == "draft"
        assert doc["locality"] == CLUJ
        assert doc["area_m2"] == 1500
        assert doc["lat"] == pytest.approx(LAT)
        assert doc["lng"] == pytest.approx(LNG)
        assert doc["offer"]["models"] == ["rent"]
        # `land` is added to the member interests automatically
        r = client.get(f"{R}/members/me", timeout=TIMEOUT)
        assert "land" in r.json()["member"]["interests"]

    def test_create_mixed_offer_price_and_percent(self, client):
        """`mixed` may combine a yearly price with a harvest percent (percent optional, 1-90)."""
        offer = {"models": ["mixed"], "terms": "Termeni mixt", "price_ron_per_year": 800, "harvest_share_percent": 20}
        doc = _create_parcel(client, title_suffix="mixt", offer=offer)
        assert doc["offer"]["models"] == ["mixed"]
        assert doc["offer"]["price_ron_per_year"] == 800
        assert doc["offer"]["harvest_share_percent"] == 20
        # percent is optional with `mixed`
        doc2 = _create_parcel(client, title_suffix="mixt fara procent",
                              offer={"models": ["mixed"], "terms": "x", "price_ron_per_year": 500})
        assert doc2["offer"].get("harvest_share_percent") is None

    def test_mine_contains_it(self, client):
        r = client.get(f"{R}/parcels/mine", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        items = _items(r.json())
        assert S["pid"] in [p["id"] for p in items]
        # sorted by updated_at desc
        stamps = [p["updated_at"] for p in items if p.get("updated_at")]
        assert stamps == sorted(stamps, reverse=True)

    def test_mine_requires_auth(self, anon):
        assert anon.get(f"{R}/parcels/mine", timeout=TIMEOUT).status_code == 401

    def test_draft_hidden_from_anonymous(self, anon):
        r = anon.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 404

    def test_draft_visible_to_owner(self, client):
        d = _owner_get(client, S["pid"])
        assert d["status"] == "draft"
        assert d["lat"] == pytest.approx(LAT)  # owner sees exact coordinates

    def test_patch_in_draft(self, client):
        new_title = f"{TAG} teren editat"
        r = client.patch(
            f"{R}/parcels/{S['pid']}",
            json=_parcel_payload("editat", area_m2=2000),
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = _owner_get(client, S["pid"])
        assert d["title"] == new_title
        assert d["area_m2"] == 2000
        assert d["status"] == "draft"

    def test_patch_invalid_rejected(self, client):
        r = client.patch(
            f"{R}/parcels/{S['pid']}",
            json=_parcel_payload("editat", area_m2=10),
            timeout=TIMEOUT,
        )
        assert 400 <= r.status_code < 500

    def test_submit(self, client):
        r = client.post(f"{R}/parcels/{S['pid']}/submit", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["pid"])["status"] == "pending_verification"

    def test_patch_while_pending_fails(self, client):
        r = client.patch(f"{R}/parcels/{S['pid']}", json=_parcel_payload("x"), timeout=TIMEOUT)
        assert 400 <= r.status_code < 500
        assert _owner_get(client, S["pid"])["status"] == "pending_verification"

    def test_delete_while_pending_409(self, client):
        r = client.delete(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 409, r.text


# ── 4. staff endpoints as a non-staff user ───────────────────────────────────

class TestNonStaff:
    def test_staff_me_requires_auth(self, anon):
        assert anon.get(f"{R}/staff/me", timeout=TIMEOUT).status_code == 401

    def test_staff_me_false(self, specialist):
        r = specialist.get(f"{R}/staff/me", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json()["is_staff"] is False

    def test_queue_forbidden(self, specialist):
        assert specialist.get(f"{R}/staff/queue", timeout=TIMEOUT).status_code == 403

    def test_verify_forbidden(self, specialist):
        r = specialist.post(
            f"{R}/staff/parcels/{S['pid']}/verify",
            json={"decision": "approve"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 403

    def test_client_is_not_staff(self, client):
        r = client.get(f"{R}/staff/me", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["is_staff"] is False

    def test_staff_list_forbidden(self, specialist):
        assert specialist.get(f"{R}/staff", timeout=TIMEOUT).status_code == 403


# ── 5. staff as super-admin (acts as manager) ────────────────────────────────

class TestAdminVerification:
    def test_staff_me_manager(self, admin):
        r = admin.get(f"{R}/staff/me", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["is_staff"] is True
        assert d["role"] == "manager"
        assert d["areas"] == []

    def test_queue_has_parcel_with_exact_coordinates(self, admin):
        r = admin.get(f"{R}/staff/queue", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        match = [p for p in _items(r.json()) if p["id"] == S["pid"]]
        assert match, "pending parcel missing from the queue"
        p = match[0]
        assert p["lat"] == pytest.approx(LAT)
        assert p["lng"] == pytest.approx(LNG)
        assert p["status"] == "pending_verification"
        assert p.get("owner_name")
        assert p.get("owner_email")

    def test_reject_requires_note(self, admin):
        for body in ({"decision": "reject"}, {"decision": "reject", "note": ""}):
            r = admin.post(f"{R}/staff/parcels/{S['pid']}/verify", json=body, timeout=TIMEOUT)
            assert 400 <= r.status_code < 500, r.text

    def test_invalid_decision(self, admin):
        r = admin.post(
            f"{R}/staff/parcels/{S['pid']}/verify", json={"decision": "maybe"}, timeout=TIMEOUT
        )
        assert 400 <= r.status_code < 500

    def test_still_pending_after_failed_attempts(self, client):
        assert _owner_get(client, S["pid"])["status"] == "pending_verification"

    def test_reject_with_note(self, admin, client):
        r = admin.post(
            f"{R}/staff/parcels/{S['pid']}/verify",
            json={"decision": "reject", "note": f"{TAG} lipsesc detalii"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = _owner_get(client, S["pid"])
        assert d["status"] == "rejected"
        assert d["verification"]["decision"] == "reject"
        assert TAG in d["verification"]["note"]
        assert d["verification"]["by"] and d["verification"]["at"]

    def test_rejected_not_in_queue(self, admin):
        r = admin.get(f"{R}/staff/queue", timeout=TIMEOUT)
        assert S["pid"] not in [p["id"] for p in _items(r.json())]

    def test_owner_edit_reverts_to_draft(self, client):
        r = client.patch(f"{R}/parcels/{S['pid']}", json=_parcel_payload("corectat"), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["pid"])["status"] == "draft"

    def test_resubmit(self, client):
        r = client.post(f"{R}/parcels/{S['pid']}/submit", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["pid"])["status"] == "pending_verification"

    def test_approve(self, admin, client):
        r = admin.post(
            f"{R}/staff/parcels/{S['pid']}/verify",
            json={"decision": "approve"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        d = _owner_get(client, S["pid"])
        assert d["status"] == "published"
        assert d["verification"]["decision"] == "approve"

    def test_verify_already_published_fails(self, admin):
        r = admin.post(
            f"{R}/staff/parcels/{S['pid']}/verify", json={"decision": "approve"}, timeout=TIMEOUT
        )
        assert 400 <= r.status_code < 500


# ── 6. public list ───────────────────────────────────────────────────────────

class TestPublicList:
    def test_published_visible_with_rounded_coords(self, anon):
        doc = _public_find(S["pid"], locality=CLUJ)
        assert doc is not None, "published parcel not in the public list"
        assert doc["lat"] == pytest.approx(round(LAT, 2), abs=1e-9)
        assert doc["lng"] == pytest.approx(round(LNG, 2), abs=1e-9)
        assert "owner_user_id" not in doc
        assert "owner_email" not in doc
        assert doc.get("owner_name")

    def test_public_detail_rounded(self, anon):
        r = anon.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = _unwrap(r.json(), "parcel")
        assert d["lat"] == pytest.approx(round(LAT, 2), abs=1e-9)
        assert d["lng"] == pytest.approx(round(LNG, 2), abs=1e-9)
        assert "owner_user_id" not in d

    def test_owner_detail_exact(self, client):
        d = _owner_get(client, S["pid"])
        assert d["lat"] == pytest.approx(LAT)
        assert d["lng"] == pytest.approx(LNG)

    def test_filter_locality(self, anon):
        assert _public_find(S["pid"], locality=CLUJ) is not None
        assert _public_find(S["pid"], locality=FLORESTI) is None
        r = anon.get(f"{R}/parcels", params={"locality": CLUJ, "limit": 50}, timeout=TIMEOUT)
        assert all(p["locality"] == CLUJ for p in _items(r.json()))

    def test_filter_model(self, anon):
        assert _public_find(S["pid"], model="rent") is not None
        assert _public_find(S["pid"], model="sale") is None

    def test_limit_over_50(self, anon):
        r = anon.get(f"{R}/parcels", params={"limit": 51}, timeout=TIMEOUT)
        if r.status_code == 200:
            assert len(_items(r.json())) <= 50
        else:
            assert 400 <= r.status_code < 500

    def test_limit_skip(self, anon):
        r = anon.get(f"{R}/parcels", params={"limit": 1, "skip": 0}, timeout=TIMEOUT)
        assert r.status_code == 200
        assert len(_items(r.json())) <= 1

    def test_only_published_in_public_list(self, anon):
        r = anon.get(f"{R}/parcels", params={"limit": 50}, timeout=TIMEOUT)
        assert all(p.get("status", "published") == "published" for p in _items(r.json()))


# ── 7. pause / resume / ownership ────────────────────────────────────────────

class TestPauseResumeOwnership:
    def test_pause_hides(self, client, anon):
        r = client.post(f"{R}/parcels/{S['pid']}/pause", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["pid"])["status"] == "paused"
        assert _public_find(S["pid"], locality=CLUJ) is None
        assert anon.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT).status_code == 404

    def test_other_user_cannot_touch_paused(self, specialist):
        pid = S["pid"]
        for call in (
            lambda: specialist.patch(f"{R}/parcels/{pid}", json=_parcel_payload("hack"), timeout=TIMEOUT),
            lambda: specialist.post(f"{R}/parcels/{pid}/submit", timeout=TIMEOUT),
            lambda: specialist.post(f"{R}/parcels/{pid}/resume", timeout=TIMEOUT),
            lambda: specialist.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT),
        ):
            assert call().status_code in (403, 404)

    def test_resume_shows_again(self, client):
        r = client.post(f"{R}/parcels/{S['pid']}/resume", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["pid"])["status"] == "published"
        assert _public_find(S["pid"], locality=CLUJ) is not None

    def test_other_user_cannot_touch_published(self, specialist):
        pid = S["pid"]
        for call in (
            lambda: specialist.patch(f"{R}/parcels/{pid}", json=_parcel_payload("hack"), timeout=TIMEOUT),
            lambda: specialist.post(f"{R}/parcels/{pid}/submit", timeout=TIMEOUT),
            lambda: specialist.post(f"{R}/parcels/{pid}/pause", timeout=TIMEOUT),
            lambda: specialist.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT),
        ):
            assert call().status_code in (403, 404)

    def test_other_user_not_in_mine(self, specialist):
        r = specialist.get(f"{R}/parcels/mine", timeout=TIMEOUT)
        assert r.status_code == 200
        assert S["pid"] not in [p["id"] for p in _items(r.json())]

    def test_still_published_after_foreign_attempts(self, client):
        assert _owner_get(client, S["pid"])["status"] == "published"

    def test_delete_archives(self, client, anon):
        extra = _create_parcel(client, title_suffix="de sters")
        r = client.delete(f"{R}/parcels/{extra['id']}", timeout=TIMEOUT)
        assert r.status_code in (200, 204), r.text
        mine = client.get(f"{R}/parcels/mine", timeout=TIMEOUT)
        assert extra["id"] not in [p["id"] for p in _items(mine.json())]
        assert anon.get(f"{R}/parcels/{extra['id']}", timeout=TIMEOUT).status_code == 404


# ── 7b. a paused parcel edited in content/location must be re-verified ───────

class TestPausedEditReverification:
    def test_setup_published_then_paused(self, client, admin):
        p = _create_parcel(client, title_suffix="reverificare")
        S["rv"] = p["id"]
        assert client.post(f"{R}/parcels/{p['id']}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{p['id']}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert client.post(f"{R}/parcels/{p['id']}/pause", timeout=TIMEOUT).status_code == 200
        assert _owner_get(client, p["id"])["status"] == "paused"

    def test_same_values_keep_paused(self, client):
        before = _owner_get(client, S["rv"])
        r = client.patch(f"{R}/parcels/{S['rv']}", json={"title": before["title"]}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["rv"])["status"] == "paused"

    def test_availability_only_keeps_paused(self, client):
        r = client.patch(
            f"{R}/parcels/{S['rv']}",
            json={"availability_from": "2031-01-01", "availability_to": "2031-12-31"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["rv"])["status"] == "paused"

    def test_content_edit_moves_to_draft(self, client, anon):
        r = client.patch(f"{R}/parcels/{S['rv']}", json={"description": f"{TAG} descriere schimbata"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "parcel")["status"] == "draft"
        assert _owner_get(client, S["rv"])["status"] == "draft"
        assert anon.get(f"{R}/parcels/{S['rv']}", timeout=TIMEOUT).status_code == 404

    def test_cannot_resume_edited_parcel(self, client):
        r = client.post(f"{R}/parcels/{S['rv']}/resume", timeout=TIMEOUT)
        assert r.status_code == 409, r.text
        assert _owner_get(client, S["rv"])["status"] == "draft"

    def test_location_edit_on_paused_moves_to_draft(self, client, admin):
        # back to paused through the normal path (resubmit, approve, pause), then change the location
        assert client.post(f"{R}/parcels/{S['rv']}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{S['rv']}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert client.post(f"{R}/parcels/{S['rv']}/pause", timeout=TIMEOUT).status_code == 200
        r = client.patch(f"{R}/parcels/{S['rv']}", json={"lat": 46.8, "lng": 23.7}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["rv"])["status"] == "draft"

    def test_resubmit_after_edit_and_publish(self, client, admin, anon):
        assert client.post(f"{R}/parcels/{S['rv']}/submit", timeout=TIMEOUT).status_code == 200
        r = admin.post(f"{R}/staff/parcels/{S['rv']}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _owner_get(client, S["rv"])["status"] == "published"
        assert anon.get(f"{R}/parcels/{S['rv']}", timeout=TIMEOUT).status_code == 200

    def test_double_verify_conflict(self, admin):
        """The parcel is no longer pending: a second verification (even a stale one) is a 409."""
        r = admin.post(f"{R}/staff/parcels/{S['rv']}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
        assert r.status_code == 409, r.text
        assert isinstance(r.json().get("detail"), str)


# ── 8. staff management + operator area filtering ────────────────────────────

class TestStaffManagement:
    def test_staff_crud_and_area_filter(self, admin, client, specialist, specialist_id):
        # Specialist cannot manage staff
        r = specialist.post(
            f"{R}/staff",
            json={"email": SPECIALIST_EMAIL, "role": "manager", "areas": []},
            timeout=TIMEOUT,
        )
        assert r.status_code == 403

        # Two pending parcels: one in Cluj-Napoca, one in Florești
        cluj = _create_parcel(client, title_suffix="coada-cluj", locality=CLUJ)
        flo = _create_parcel(client, title_suffix="coada-floresti", locality=FLORESTI)
        for p in (cluj, flo):
            r = client.post(f"{R}/parcels/{p['id']}/submit", timeout=TIMEOUT)
            assert r.status_code == 200, r.text

        try:
            # Admin adds the specialist as operator for Florești
            r = admin.post(
                f"{R}/staff",
                json={"email": SPECIALIST_EMAIL, "role": "operator", "areas": [FLORESTI]},
                timeout=TIMEOUT,
            )
            assert r.status_code in (200, 201), r.text
            rec = _unwrap(r.json(), "staff")
            assert rec.get("user_id") == specialist_id
            assert rec["role"] == "operator"

            # Listed for admin
            r = admin.get(f"{R}/staff", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            assert specialist_id in [s["user_id"] for s in _items(r.json())]

            # Unknown email is rejected
            r = admin.post(
                f"{R}/staff",
                json={"email": f"nimeni-{uuid.uuid4().hex[:6]}@example.invalid", "role": "operator", "areas": []},
                timeout=TIMEOUT,
            )
            assert 400 <= r.status_code < 500

            # Specialist is now operator with areas
            r = specialist.get(f"{R}/staff/me", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            me = r.json()
            assert me["is_staff"] is True
            assert me["role"] == "operator"
            assert me["areas"] == [FLORESTI]

            # Operator queue shows only Florești
            r = specialist.get(f"{R}/staff/queue", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            q = _items(r.json())
            ids = [p["id"] for p in q]
            assert flo["id"] in ids
            assert cluj["id"] not in ids
            assert all(p["locality"] == FLORESTI for p in q)

            # Admin queue (manager, all areas) shows both
            r = admin.get(f"{R}/staff/queue", timeout=TIMEOUT)
            admin_ids = [p["id"] for p in _items(r.json())]
            assert flo["id"] in admin_ids and cluj["id"] in admin_ids

            # Operator sees the full (owner e-mail) view only inside their areas; outside, a pending parcel is a 404
            r = specialist.get(f"{R}/parcels/{flo['id']}", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            assert _unwrap(r.json(), "parcel").get("owner_email")
            assert specialist.get(f"{R}/parcels/{cluj['id']}", timeout=TIMEOUT).status_code == 404
            assert admin.get(f"{R}/parcels/{cluj['id']}", timeout=TIMEOUT).status_code == 200

            # Operator may not manage staff, nor verify outside their areas
            r = specialist.post(
                f"{R}/staff",
                json={"email": CLIENT_EMAIL, "role": "operator", "areas": []},
                timeout=TIMEOUT,
            )
            assert r.status_code == 403
            assert specialist.get(f"{R}/staff", timeout=TIMEOUT).status_code == 403
            r = specialist.post(
                f"{R}/staff/parcels/{cluj['id']}/verify",
                json={"decision": "reject", "note": f"{TAG} in afara zonei"},
                timeout=TIMEOUT,
            )
            assert r.status_code in (403, 404)
            assert _owner_get(client, cluj["id"])["status"] == "pending_verification"

            # Operator can verify in their area
            r = specialist.post(
                f"{R}/staff/parcels/{flo['id']}/verify",
                json={"decision": "reject", "note": f"{TAG} test operator"},
                timeout=TIMEOUT,
            )
            assert r.status_code == 200, r.text
            assert _owner_get(client, flo["id"])["status"] == "rejected"
        finally:
            # Remove staff (manager/super-admin only)
            r = admin.delete(f"{R}/staff/{specialist_id}", timeout=TIMEOUT)
            assert r.status_code in (200, 204), r.text

        r = specialist.get(f"{R}/staff/me", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["is_staff"] is False
        assert specialist.get(f"{R}/staff/queue", timeout=TIMEOUT).status_code == 403
        # Teardown fixture rejects the still-pending Cluj parcel and archives all parcels.
