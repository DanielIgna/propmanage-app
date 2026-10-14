"""Rădăcini S2 — HTTP integration tests (contract: docs/radacini/PLAN.md, "S2 — contract").

Run against a live backend:
    REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s2.py -q --noconftest

One ordered scenario (state carried in the `S` dict). Roles:
  client      = parcel owner
  specialist  = requester
  admin       = super-admin (read-only in requests/agreements) AND a competing requester
Every parcel carries a unique TEST-RAD-<hex> tag. Parcels with a signed agreement cannot be
archived through the API (expected: they are is_demo and removed by
backend/scripts/radacini_purge_demo.py --apply); all the others are archived at teardown.
"""
import hashlib
import json
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

LEGAL_NOTICE = (
    "Acest acord consemnează înțelegerea dintre părți în platforma Rădăcini. "
    "Nu înlocuiește contractul de arendă/închiriere în forma cerută de lege "
    "și nici înregistrarea acestuia la primărie, unde este cazul."
)
LOST_REASON = "Terenul a fost atribuit altui solicitant."
LEGAL_GATE = "Acest model necesită aviz juridic și nu e încă disponibil în platformă."

PARCEL_AREA = 5000

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
    # The API validates "start >= today" in Europe/Bucharest (the frontend computes local dates).
    return datetime.now(ZoneInfo("Europe/Bucharest")).date()


def _d(days):
    return (_today() + timedelta(days=days)).isoformat()


def _err(r, code):
    """Assert an error response: exact status code and a string `detail`."""
    assert r.status_code == code, f"expected {code}, got {r.status_code}: {r.text[:300]}"
    assert isinstance(r.json().get("detail"), str), r.text[:300]


def _expected_terms_hash(ag):
    """sha256 of the canonical JSON {"terms": ..., "version": ...} (spec: docs/radacini/PLAN.md, round 2)."""
    canonical = json.dumps(
        {"terms": ag["terms"], "version": ag["version"]},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sig_of(ag, uid):
    return next(s for s in ag["signatures"] if s["user_id"] == uid)


def _4xx(r):
    assert 400 <= r.status_code < 500, f"expected 4xx, got {r.status_code}: {r.text[:300]}"


def _proposal(**over):
    """A valid 'rent' proposal (flat). Pass key=None to drop a key."""
    p = {
        "area_m2": 1000,
        "start_date": _d(10),
        "end_date": _d(375),
        "price_ron_per_year": 1000,
        "crops": ["porumb"],
        "note": f"{TAG} propunere",
    }
    p.update(over)
    return {k: v for k, v in p.items() if v is not None}


def _request_body(model="rent", **over):
    return {"model": model, **_proposal(**over)}


def _parcel_payload(title_suffix="", **over):
    p = {
        "title": f"{TAG} teren S2 {title_suffix}".strip(),
        "county": "Cluj",
        "locality": FLORESTI,
        "lat": LAT,
        "lng": LNG,
        "area_m2": PARCEL_AREA,
        "access": "Drum de pământ, acces auto",
        "water_sources": ["well"],
        "current_crops": ["porumb"],
        "description": "Teren de test pentru integrare S2.",
        "offer": {
            "models": ["rent", "harvest_share"],
            "terms": "Termeni de test",
            "price_ron_per_year": 1200,
            "harvest_share_percent": 30,
        },
    }
    p.update(over)
    return p


def _create_parcel(owner, suffix="", **over):
    r = owner.post(f"{R}/parcels", json=_parcel_payload(suffix, **over), timeout=TIMEOUT)
    assert r.status_code in (200, 201), r.text
    doc = _unwrap(r.json(), "parcel")
    assert doc.get("id")
    _created_ids.append(doc["id"])
    return doc


def _publish_parcel(owner, admin, suffix="", **over):
    p = _create_parcel(owner, suffix, **over)
    r = owner.post(f"{R}/parcels/{p['id']}/submit", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    r = admin.post(f"{R}/staff/parcels/{p['id']}/verify", json={"decision": "approve"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    r = owner.get(f"{R}/parcels/{p['id']}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    assert _unwrap(r.json(), "parcel")["status"] == "published"
    return p


def _post_request(session, pid, model="rent", **over):
    return session.post(f"{R}/parcels/{pid}/requests", json=_request_body(model, **over), timeout=TIMEOUT)


def _new_request(session, pid, model="rent", **over):
    r = _post_request(session, pid, model, **over)
    assert r.status_code in (200, 201), r.text
    return _unwrap(r.json(), "request")


def _get_request(session, rid):
    r = session.get(f"{R}/requests/{rid}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


def _get_agreement(session, aid):
    r = session.get(f"{R}/agreements/{aid}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return _unwrap(r.json(), "agreement")


def _get_parcel(session, pid):
    r = session.get(f"{R}/parcels/{pid}", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return _unwrap(r.json(), "parcel")


def _ensure_member(session, interests, locality):
    r = session.put(
        f"{R}/members/me",
        json={"interests": interests, "county": "Cluj", "locality": locality},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text


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
    # owner needs `land`, requesters need `grow` (the API also adds them automatically)
    _ensure_member(client, ["land"], FLORESTI)
    _ensure_member(specialist, ["grow"], FLORESTI)
    _ensure_member(admin, ["grow"], CLUJ)


@pytest.fixture(scope="module", autouse=True)
def _cleanup(client, admin, _members):
    yield
    for pid in _created_ids:
        try:
            r = client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
            if r.status_code == 409:
                # pending_verification -> reject then archive. A parcel with an active agreement
                # also answers 409; it is left for radacini_purge_demo.py (expected).
                admin.post(
                    f"{R}/staff/parcels/{pid}/verify",
                    json={"decision": "reject", "note": "cleanup test"},
                    timeout=TIMEOUT,
                )
                client.delete(f"{R}/parcels/{pid}", timeout=TIMEOUT)
        except Exception:
            pass


# ── 0. setup: published parcel + a draft parcel ──────────────────────────────

class TestSetup:
    def test_publish_main_parcel(self, client, admin):
        p = _publish_parcel(client, admin, "main")
        S["pid"] = p["id"]

    def test_create_draft_parcel(self, client):
        p = _create_parcel(client, "draft")
        S["draft_pid"] = p["id"]
        assert _get_parcel(client, p["id"])["status"] == "draft"


# ── 1. request creation ──────────────────────────────────────────────────────

class TestRequestCreate:
    def test_requires_auth(self, anon):
        r = anon.post(f"{R}/parcels/{S['pid']}/requests", json=_request_body(), timeout=TIMEOUT)
        assert r.status_code == 401

    def test_owner_cannot_request_own_parcel(self, client):
        r = _post_request(client, S["pid"])
        _4xx(r)
        assert r.status_code != 401

    def test_model_not_in_offer(self, specialist):
        _err(_post_request(specialist, S["pid"], "fixed_fee"), 400)

    @pytest.mark.parametrize(
        "over",
        [
            {"area_m2": PARCEL_AREA + 1},
            {"area_m2": 99},
            {"start_date": _d(30), "end_date": _d(30)},
            {"start_date": _d(30), "end_date": _d(20)},
            {"start_date": _d(-3), "end_date": _d(100)},
            {"note": "x" * 1001},
            {"crops": "not-a-list"},
            {"price_ron_per_year": 10_000_001},
            {"price_ron_per_year": -5},
        ],
        ids=["area_over_parcel", "area_under_min", "end_equals_start", "end_before_start", "start_in_past",
             "note_too_long", "crops_not_list", "price_over_max", "price_negative"],
    )
    def test_validation_rent(self, specialist, over):
        _err(_post_request(specialist, S["pid"], "rent", **over), 400)

    def test_harvest_share_requires_percent(self, specialist):
        _err(_post_request(specialist, S["pid"], "harvest_share", price_ron_per_year=None), 400)

    @pytest.mark.parametrize("pct", [0, 91, 95])
    def test_harvest_share_percent_range(self, specialist, pct):
        _err(_post_request(specialist, S["pid"], "harvest_share", harvest_share_percent=pct, price_ron_per_year=None), 400)

    def test_percent_forbidden_with_rent(self, specialist):
        _err(_post_request(specialist, S["pid"], "rent", harvest_share_percent=25), 400)

    def test_request_on_non_published_parcel(self, specialist):
        _err(_post_request(specialist, S["draft_pid"]), 409)

    def test_valid_request(self, specialist, client):
        r = _post_request(specialist, S["pid"], "rent", note=f"{TAG} cerere A")
        assert r.status_code in (200, 201), r.text
        req = _unwrap(r.json(), "request")
        assert req["id"]
        assert req["status"] == "sent"
        assert req["parcel_id"] == S["pid"]
        assert req["model"] == "rent"
        assert req["proposal"]["area_m2"] == 1000
        assert req["proposal"]["price_ron_per_year"] == 1000
        assert req["owner_user_id"] and req["requester_user_id"]
        assert req["owner_user_id"] != req["requester_user_id"]
        S["rid"] = req["id"]
        S["owner_uid"] = req["owner_user_id"]
        S["req_uid"] = req["requester_user_id"]
        S["orig_price"] = req["proposal"]["price_ron_per_year"]

    def test_duplicate_active_request(self, specialist):
        _err(_post_request(specialist, S["pid"]), 409)

    def test_competing_request_by_admin(self, admin):
        """Second requester (super-admin with a member profile) on the same parcel; valid harvest_share."""
        r = _post_request(
            admin, S["pid"], "harvest_share",
            harvest_share_percent=25, price_ron_per_year=None, area_m2=800, note=f"{TAG} cerere B",
        )
        assert r.status_code in (200, 201), r.text
        req = _unwrap(r.json(), "request")
        assert req["status"] == "sent"
        assert req["model"] == "harvest_share"
        assert req["proposal"]["harvest_share_percent"] == 25
        S["rid_b"] = req["id"]


# ── 1b. legal gate (sale / joint_project) and the mixed model ───────────────

class TestLegalGateAndMixed:
    def test_setup_parcel_with_all_models(self, client, admin):
        offer = {
            "models": ["rent", "mixed", "sale", "joint_project"],
            "terms": "Termeni de test",
            "price_ron_per_year": 1200,
            "harvest_share_percent": 30,
        }
        p = _publish_parcel(client, admin, "gate", offer=offer)
        S["gate_pid"] = p["id"]
        assert set(_get_parcel(client, p["id"])["offer"]["models"]) == {"rent", "mixed", "sale", "joint_project"}

    @pytest.mark.parametrize("model", ["sale", "joint_project"])
    def test_sale_and_joint_project_blocked(self, specialist, model):
        """Both stay selectable in the parcel offer (display) but a request on them is a 409."""
        r = _post_request(specialist, S["gate_pid"], model)
        _err(r, 409)
        assert r.json()["detail"] == LEGAL_GATE
        # the gate applies before the "model not offered" check
        r = _post_request(specialist, S["pid"], model)
        _err(r, 409)
        assert r.json()["detail"] == LEGAL_GATE

    @pytest.mark.parametrize("pct", [0, 91, 95])
    def test_mixed_percent_range(self, specialist, pct):
        _err(_post_request(specialist, S["gate_pid"], "mixed", harvest_share_percent=pct), 400)

    def test_mixed_with_price_and_percent_ok(self, specialist):
        r = _post_request(specialist, S["gate_pid"], "mixed", harvest_share_percent=25, price_ron_per_year=700)
        assert r.status_code in (200, 201), r.text
        req = _unwrap(r.json(), "request")
        assert req["model"] == "mixed"
        assert req["proposal"]["price_ron_per_year"] == 700
        assert req["proposal"]["harvest_share_percent"] == 25
        w = specialist.post(f"{R}/requests/{req['id']}/withdraw", timeout=TIMEOUT)
        assert w.status_code == 200, w.text

    def test_mixed_percent_optional(self, specialist):
        r = _post_request(specialist, S["gate_pid"], "mixed", price_ron_per_year=900)
        assert r.status_code in (200, 201), r.text
        req = _unwrap(r.json(), "request")
        assert req["proposal"].get("harvest_share_percent") is None
        w = specialist.post(f"{R}/requests/{req['id']}/withdraw", timeout=TIMEOUT)
        assert w.status_code == 200, w.text

    def test_percent_still_forbidden_with_rent(self, specialist):
        _err(_post_request(specialist, S["gate_pid"], "rent", harvest_share_percent=25), 400)

    def test_non_party_sees_rounded_coordinates(self, specialist):
        """A published parcel read by a signed-in non-party keeps the rounded public view."""
        p = _get_parcel(specialist, S["gate_pid"])
        assert p["lat"] == pytest.approx(round(LAT, 2)) and p["lng"] == pytest.approx(round(LNG, 2))
        assert not p.get("exact_location")


# ── 2. visibility ────────────────────────────────────────────────────────────

class TestVisibility:
    def test_anonymous_get_401(self, anon):
        assert anon.get(f"{R}/requests/{S['rid']}", timeout=TIMEOUT).status_code == 401

    def test_lists_require_auth(self, anon):
        assert anon.get(f"{R}/requests/sent", timeout=TIMEOUT).status_code == 401
        assert anon.get(f"{R}/requests/received", timeout=TIMEOUT).status_code == 401

    def test_requester_sees_request(self, specialist):
        d = _get_request(specialist, S["rid"])
        assert d["request"]["id"] == S["rid"]
        assert d["request"]["status"] == "sent"  # owner has not opened it yet
        assert d["messages"] == []

    def test_sent_list(self, specialist, client):
        items = _items(specialist.get(f"{R}/requests/sent", timeout=TIMEOUT).json())
        mine = [i for i in items if i["id"] == S["rid"]]
        assert len(mine) == 1
        assert mine[0]["parcel_title"].startswith(TAG)
        assert mine[0]["parcel_locality"] == FLORESTI
        assert mine[0]["counterpart_name"]
        # the owner did not send it
        owner_sent = _items(client.get(f"{R}/requests/sent", timeout=TIMEOUT).json())
        assert S["rid"] not in [i["id"] for i in owner_sent]

    def test_received_list(self, client, specialist):
        items = _items(client.get(f"{R}/requests/received", timeout=TIMEOUT).json())
        ids = [i["id"] for i in items]
        assert S["rid"] in ids and S["rid_b"] in ids
        mine = next(i for i in items if i["id"] == S["rid"])
        assert mine["parcel_title"].startswith(TAG)
        assert mine["parcel_locality"] == FLORESTI
        assert mine["counterpart_name"]
        req_received = _items(specialist.get(f"{R}/requests/received", timeout=TIMEOUT).json())
        assert S["rid"] not in [i["id"] for i in req_received]

    def test_owner_open_flips_to_viewed(self, client, specialist):
        d = _get_request(client, S["rid"])
        assert d["request"]["status"] == "viewed"
        assert _get_request(specialist, S["rid"])["request"]["status"] == "viewed"

    def test_super_admin_can_read(self, admin):
        d = _get_request(admin, S["rid"])
        assert d["request"]["id"] == S["rid"]


# ── 3. messages ──────────────────────────────────────────────────────────────

class TestMessages:
    def test_requires_auth(self, anon):
        r = anon.post(f"{R}/requests/{S['rid']}/messages", json={"text": "salut"}, timeout=TIMEOUT)
        assert r.status_code == 401

    def test_empty_text(self, specialist):
        _err(specialist.post(f"{R}/requests/{S['rid']}/messages", json={"text": ""}, timeout=TIMEOUT), 400)

    def test_missing_text(self, specialist):
        _err(specialist.post(f"{R}/requests/{S['rid']}/messages", json={}, timeout=TIMEOUT), 400)

    def test_text_too_long(self, specialist):
        r = specialist.post(f"{R}/requests/{S['rid']}/messages", json={"text": "x" * 2001}, timeout=TIMEOUT)
        _err(r, 400)

    def test_non_party_cannot_post(self, admin):
        r = admin.post(f"{R}/requests/{S['rid']}/messages", json={"text": f"{TAG} intrus"}, timeout=TIMEOUT)
        _err(r, 403)

    def test_requester_posts_then_negotiating(self, specialist):
        r = specialist.post(f"{R}/requests/{S['rid']}/messages", json={"text": f"{TAG} mesaj 1"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        m = _unwrap(r.json(), "message")
        assert m["id"] and m["text"] == f"{TAG} mesaj 1"
        assert _get_request(specialist, S["rid"])["request"]["status"] == "negotiating"

    def test_owner_sees_messages_sorted(self, client):
        r = client.post(f"{R}/requests/{S['rid']}/messages", json={"text": f"{TAG} mesaj 2"}, timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        d = _get_request(client, S["rid"])
        assert d["request"]["status"] == "negotiating"
        msgs = d["messages"]
        assert [m["text"] for m in msgs] == [f"{TAG} mesaj 1", f"{TAG} mesaj 2"]
        stamps = [m["created_at"] for m in msgs]
        assert stamps == sorted(stamps)


# ── 4. counter-proposal ──────────────────────────────────────────────────────

class TestCounter:
    def test_requires_auth(self, anon):
        r = anon.post(f"{R}/requests/{S['rid']}/counter", json=_proposal(), timeout=TIMEOUT)
        assert r.status_code == 401

    def test_non_party_forbidden(self, admin):
        r = admin.post(f"{R}/requests/{S['rid']}/counter", json=_proposal(price_ron_per_year=900), timeout=TIMEOUT)
        _err(r, 403)

    @pytest.mark.parametrize(
        "over",
        [
            {"area_m2": PARCEL_AREA + 1},
            {"start_date": _d(30), "end_date": _d(30)},
            {"start_date": _d(-3), "end_date": _d(100)},
            {"harvest_share_percent": 25},  # percent not allowed for a rent request
        ],
        ids=["area_over_parcel", "end_equals_start", "start_in_past", "percent_with_rent"],
    )
    def test_counter_validation(self, client, over):
        _err(client.post(f"{R}/requests/{S['rid']}/counter", json=_proposal(**over), timeout=TIMEOUT), 400)

    def test_owner_counter(self, client):
        r = client.post(
            f"{R}/requests/{S['rid']}/counter",
            json=_proposal(price_ron_per_year=1500, note=f"{TAG} contra"),
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 201), r.text
        req = _unwrap(r.json(), "request")
        assert req["status"] == "negotiating"
        assert req["proposal"]["price_ron_per_year"] == 1500
        assert len(req["proposals_history"]) == 1
        old = req["proposals_history"][0]
        assert old["proposal"]["price_ron_per_year"] == S["orig_price"]
        assert old["by_user_id"] and old["at"]
        # persisted
        got = _get_request(client, S["rid"])["request"]
        assert got["proposal"]["price_ron_per_year"] == 1500
        assert len(got["proposals_history"]) == 1


# ── 5. accept ────────────────────────────────────────────────────────────────

class TestAccept:
    def test_requires_auth(self, anon):
        assert anon.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT).status_code == 401

    def test_requester_cannot_accept(self, specialist):
        _err(specialist.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT), 403)

    def test_super_admin_cannot_accept(self, admin):
        _err(admin.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT), 403)

    def test_owner_cannot_accept_own_counter(self, client):
        """The last proposal (price 1500) was authored by the owner: the requester has to answer first."""
        r = client.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT)
        _err(r, 409)
        assert "Așteaptă răspunsul solicitantului" in r.json()["detail"]
        assert _get_request(client, S["rid"])["request"]["status"] == "negotiating"

    def test_requester_agrees_with_counter(self, specialist):
        r = specialist.post(
            f"{R}/requests/{S['rid']}/counter",
            json=_proposal(price_ron_per_year=1500, note=f"{TAG} de acord"),
            timeout=TIMEOUT,
        )
        assert r.status_code in (200, 201), r.text
        req = _unwrap(r.json(), "request")
        assert req["status"] == "negotiating"
        assert req["proposal_by_user_id"] == S["req_uid"]
        assert len(req["proposals_history"]) == 2

    def test_owner_accepts(self, client):
        r = client.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        req, ag = d["request"], d["agreement"]
        assert req["status"] == "accepted"
        assert req.get("decided_at")
        assert req["agreement_id"] == ag["id"]
        assert ag["status"] == "draft"
        assert ag["version"] == 1
        assert ag["request_id"] == S["rid"] and ag["parcel_id"] == S["pid"]
        assert ag["model"] == "rent"
        assert len(ag["parties"]) == 2
        roles = {p["role"]: p for p in ag["parties"]}
        assert set(roles) == {"owner", "cultivator"}
        assert roles["owner"]["user_id"] == S["owner_uid"]
        assert roles["cultivator"]["user_id"] == S["req_uid"]
        assert all(p["name"] for p in ag["parties"])
        assert ag["legal_notice"] == LEGAL_NOTICE
        assert ag["signatures"] == []
        # terms come from the current (countered) proposal
        assert ag["terms"]["price_ron_per_year"] == 1500
        assert ag["terms"]["area_m2"] == 1000
        assert ag["terms"]["parcel_snapshot"]["title"].startswith(TAG)
        assert ag["terms"]["parcel_snapshot"]["locality"] == FLORESTI
        assert ag["terms"]["parcel_snapshot"]["area_m2"] == PARCEL_AREA
        S["aid"] = ag["id"]

    def test_accept_again_conflict(self, client):
        _err(client.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT), 409)

    def test_message_on_accepted_rejected(self, client, specialist):
        _4xx(client.post(f"{R}/requests/{S['rid']}/messages", json={"text": "dupa acceptare"}, timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/requests/{S['rid']}/messages", json={"text": "dupa acceptare"}, timeout=TIMEOUT))

    def test_counter_on_accepted_rejected(self, client):
        _4xx(client.post(f"{R}/requests/{S['rid']}/counter", json=_proposal(), timeout=TIMEOUT))

    def test_withdraw_on_accepted_rejected(self, specialist):
        _4xx(specialist.post(f"{R}/requests/{S['rid']}/withdraw", timeout=TIMEOUT))

    def test_request_stays_accepted(self, specialist):
        assert _get_request(specialist, S["rid"])["request"]["status"] == "accepted"

    def test_other_request_still_active(self, admin):
        assert _get_request(admin, S["rid_b"])["request"]["status"] in ("sent", "viewed", "negotiating")


# ── 6. agreement lifecycle ───────────────────────────────────────────────────

class TestAgreement:
    def test_requires_auth(self, anon):
        assert anon.get(f"{R}/agreements", timeout=TIMEOUT).status_code == 401
        assert anon.get(f"{R}/agreements/{S['aid']}", timeout=TIMEOUT).status_code == 401

    def test_list_for_both_parties(self, client, specialist, admin):
        for sess in (client, specialist):
            items = _items(sess.get(f"{R}/agreements", timeout=TIMEOUT).json())
            assert S["aid"] in [i["id"] for i in items]
        # list = agreements where the user is a party; super-admin is not one
        admin_items = _items(admin.get(f"{R}/agreements", timeout=TIMEOUT).json())
        assert S["aid"] not in [i["id"] for i in admin_items]

    def test_get_agreement_parties_and_admin(self, client, specialist, admin):
        for sess in (client, specialist, admin):  # super-admin can read
            ag = _get_agreement(sess, S["aid"])
            assert ag["id"] == S["aid"]
            assert ag["legal_notice"] == LEGAL_NOTICE
            assert ag["status"] == "draft"

    def test_sign_while_draft_conflict(self, client):
        _err(client.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 1}, timeout=TIMEOUT), 409)

    def test_super_admin_cannot_act(self, admin):
        _err(admin.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT), 403)
        _err(admin.post(f"{R}/agreements/{S['aid']}/cancel", json={}, timeout=TIMEOUT), 403)
        _err(admin.patch(f"{R}/agreements/{S['aid']}", json={"terms": {"price_ron_per_year": 1}}, timeout=TIMEOUT), 403)

    @pytest.mark.parametrize(
        "terms",
        [
            {"area_m2": PARCEL_AREA + 1},
            {"start_date": _d(30), "end_date": _d(30)},
            {"custom_clauses": "x" * 5001},
            {"price_ron_per_year": 10_000_001},
        ],
        ids=["area_over_parcel", "end_equals_start", "clauses_too_long", "price_over_max"],
    )
    def test_patch_validation(self, client, terms):
        _err(client.patch(f"{R}/agreements/{S['aid']}", json={"terms": terms}, timeout=TIMEOUT), 400)
        ag = _get_agreement(client, S["aid"])
        assert ag["version"] == 1 and ag["status"] == "draft"

    def test_draft_has_no_terms_hash(self, client):
        assert _get_agreement(client, S["aid"]).get("terms_hash") is None

    def test_propose(self, client):
        r = client.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["status"] == "proposed"
        assert len(ag["terms_hash"]) == 64 and int(ag["terms_hash"], 16) >= 0
        assert ag["terms_hash"] == _expected_terms_hash(ag)
        assert _get_agreement(client, S["aid"])["terms_hash"] == ag["terms_hash"]
        S["hash_v1"] = ag["terms_hash"]

    def test_propose_again_conflict(self, client):
        _err(client.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT), 409)

    def test_patch_by_cultivator_bumps_version(self, specialist):
        r = specialist.patch(
            f"{R}/agreements/{S['aid']}",
            json={"terms": {"price_ron_per_year": 1800, "custom_clauses": f"{TAG} clauză"}},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["version"] == 2
        assert ag["status"] == "draft"
        assert ag["signatures"] == []
        assert ag.get("terms_hash") is None  # back to draft: the hash is set again on "propose"
        assert ag["terms"]["price_ron_per_year"] == 1800
        assert ag["terms"]["custom_clauses"] == f"{TAG} clauză"
        assert ag["terms"]["area_m2"] == 1000  # partial patch keeps other terms
        assert len(ag["versions_history"]) == 1
        assert ag["versions_history"][0]["version"] == 1
        assert ag["versions_history"][0]["terms"]["price_ron_per_year"] == 1500

    def test_propose_v2(self, specialist):
        r = specialist.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["status"] == "proposed"
        assert ag["terms_hash"] != S["hash_v1"]
        assert ag["terms_hash"] == _expected_terms_hash(ag)
        S["hash_v2"] = ag["terms_hash"]

    def test_sign_stale_version_conflict(self, client):
        _err(client.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 1}, timeout=TIMEOUT), 409)
        _err(client.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 99}, timeout=TIMEOUT), 409)

    def test_sign_requires_auth_and_party(self, anon, admin):
        assert anon.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 2}, timeout=TIMEOUT).status_code == 401
        _err(admin.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 2}, timeout=TIMEOUT), 403)

    def test_owner_signs_v2_still_proposed(self, client):
        # X-Forwarded-For: the first value is the signer's IP
        r = client.post(
            f"{R}/agreements/{S['aid']}/sign", json={"version": 2},
            headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1", "User-Agent": f"{TAG}-owner-ua/1.0"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["status"] == "proposed"
        assert len(ag["signatures"]) == 1
        assert ag["signatures"][0]["user_id"] == S["owner_uid"]
        assert ag["signatures"][0]["version"] == 2
        assert ag["signatures"][0]["signed_at"]
        assert not ag.get("signed_at")
        # signature evidence is visible to the signer himself
        sig = ag["signatures"][0]
        assert sig["ip"] == "203.0.113.7"
        assert sig["user_agent"] == f"{TAG}-owner-ua/1.0"
        assert sig["terms_hash"] == S["hash_v2"] == ag["terms_hash"] == _expected_terms_hash(ag)

    def test_signature_evidence_hidden_from_counterpart(self, client, specialist, admin):
        """ip / user_agent only for the signer and the super-admin; the terms hash stays visible."""
        for fetch in (
            lambda: _get_agreement(specialist, S["aid"]),
            lambda: next(
                i for i in _items(specialist.get(f"{R}/agreements", timeout=TIMEOUT).json()) if i["id"] == S["aid"]
            ),
        ):
            ag = fetch()
            sig = _sig_of(ag, S["owner_uid"])
            assert "ip" not in sig and "user_agent" not in sig
            assert sig["terms_hash"] == S["hash_v2"] and sig["signed_at"]
            assert ag["terms_hash"] == S["hash_v2"]
        own = _sig_of(_get_agreement(client, S["aid"]), S["owner_uid"])
        assert own["ip"] == "203.0.113.7" and own["user_agent"] == f"{TAG}-owner-ua/1.0"
        adm = _sig_of(_get_agreement(admin, S["aid"]), S["owner_uid"])  # super-admin sees everything
        assert adm["ip"] == "203.0.113.7" and adm["user_agent"] == f"{TAG}-owner-ua/1.0"

    def test_owner_signs_twice_rejected(self, client):
        _4xx(client.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 2}, timeout=TIMEOUT))
        assert len(_get_agreement(client, S["aid"])["signatures"]) == 1

    def test_competing_request_still_active_before_signing(self, admin):
        assert _get_request(admin, S["rid_b"])["request"]["status"] in ("sent", "viewed", "negotiating")

    def test_cultivator_signs_v2_signed(self, specialist):
        long_ua = "UA-" + "x" * 400
        r = specialist.post(
            f"{R}/agreements/{S['aid']}/sign", json={"version": 2}, headers={"User-Agent": long_ua}, timeout=TIMEOUT
        )
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["status"] == "signed"
        assert ag["signed_at"]
        assert len(ag["signatures"]) == 2
        assert {s["user_id"] for s in ag["signatures"]} == {S["owner_uid"], S["req_uid"]}
        assert all(s["version"] == 2 for s in ag["signatures"])
        assert ag["version"] == 2
        # evidence: own ip / truncated user agent; both signatures carry the same terms hash
        mine = _sig_of(ag, S["req_uid"])
        assert isinstance(mine["ip"], str) and mine["ip"]
        assert mine["user_agent"] == long_ua[:300] and len(mine["user_agent"]) == 300
        theirs = _sig_of(ag, S["owner_uid"])
        assert "ip" not in theirs and "user_agent" not in theirs  # the owner's evidence is not exposed
        assert mine["terms_hash"] == theirs["terms_hash"] == S["hash_v2"] == ag["terms_hash"]

    def test_signed_evidence_visibility(self, client, specialist, admin):
        """After both signatures: each party sees only its own evidence, the super-admin sees both."""
        for sess, own_uid, other_uid in (
            (client, S["owner_uid"], S["req_uid"]),
            (specialist, S["req_uid"], S["owner_uid"]),
        ):
            ag = _get_agreement(sess, S["aid"])
            assert ag["status"] == "signed" and ag["terms_hash"] == S["hash_v2"]
            assert _sig_of(ag, own_uid)["ip"] and _sig_of(ag, own_uid)["user_agent"]
            other = _sig_of(ag, other_uid)
            assert "ip" not in other and "user_agent" not in other and other["terms_hash"] == S["hash_v2"]
        ag = _get_agreement(admin, S["aid"])
        assert all(s["ip"] and s["user_agent"] and s["terms_hash"] == S["hash_v2"] for s in ag["signatures"])


# ── 7. effects of the signature ──────────────────────────────────────────────

class TestAfterSigned:
    def test_parcel_paused_with_active_agreement(self, client, anon):
        p = _get_parcel(client, S["pid"])
        assert p["status"] == "paused"
        assert p["active_agreement_id"] == S["aid"]
        # paused -> no longer public
        assert anon.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT).status_code == 404

    def test_cultivator_reads_exact_location_of_paused_parcel(self, specialist, anon):
        """Parties of a signed agreement see the exact coordinates (the read is logged server-side)."""
        r = specialist.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        p = _unwrap(r.json(), "parcel")
        assert p["status"] == "paused"
        assert p["exact_location"] is True
        assert p["lat"] == pytest.approx(LAT) and p["lng"] == pytest.approx(LNG)
        assert p["locality"] == FLORESTI and p["access"]
        assert not {"owner_user_id", "active_agreement_id", "verification", "owner_email"} & set(p)
        assert anon.get(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT).status_code == 404

    def test_resume_conflict(self, client):
        r = client.post(f"{R}/parcels/{S['pid']}/resume", timeout=TIMEOUT)
        _err(r, 409)
        assert "acord activ" in r.json()["detail"]
        assert _get_parcel(client, S["pid"])["status"] == "paused"

    def test_patch_parcel_conflict(self, client):
        r = client.patch(f"{R}/parcels/{S['pid']}", json={"description": f"{TAG} modificat"}, timeout=TIMEOUT)
        _err(r, 409)
        assert "acord activ" in r.json()["detail"]

    def test_delete_parcel_conflict(self, client):
        r = client.delete(f"{R}/parcels/{S['pid']}", timeout=TIMEOUT)
        _err(r, 409)
        assert "acord activ" in r.json()["detail"]
        assert _get_parcel(client, S["pid"]).get("archived_at") in (None, "")

    def test_new_request_on_paused_parcel(self, specialist):
        _err(_post_request(specialist, S["pid"]), 409)

    def test_patch_signed_agreement_rejected(self, client):
        _4xx(client.patch(f"{R}/agreements/{S['aid']}", json={"terms": {"price_ron_per_year": 1}}, timeout=TIMEOUT))
        assert _get_agreement(client, S["aid"])["version"] == 2

    def test_cancel_signed_rejected(self, client, specialist):
        _4xx(client.post(f"{R}/agreements/{S['aid']}/cancel", json={"reason": "tarziu"}, timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/agreements/{S['aid']}/cancel", json={}, timeout=TIMEOUT))
        assert _get_agreement(client, S["aid"])["status"] == "signed"

    def test_propose_and_sign_signed_rejected(self, client):
        _4xx(client.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT))
        _4xx(client.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 2}, timeout=TIMEOUT))

    def test_competing_request_declined(self, admin, client):
        for sess in (admin, client):
            req = _get_request(sess, S["rid_b"])["request"]
            assert req["status"] == "declined"
            assert req["decline_reason"] == LOST_REASON
        assert _get_request(admin, S["rid"])["request"]["status"] == "accepted"

    def test_declined_competing_request_is_final(self, admin, client):
        _4xx(admin.post(f"{R}/requests/{S['rid_b']}/withdraw", timeout=TIMEOUT))
        _4xx(admin.post(f"{R}/requests/{S['rid_b']}/messages", json={"text": "inca aici?"}, timeout=TIMEOUT))
        _4xx(client.post(f"{R}/requests/{S['rid_b']}/accept", timeout=TIMEOUT))


# ── 9. withdraw / decline on a fresh parcel ──────────────────────────────────

class TestWithdrawDecline:
    def test_setup(self, client, admin, specialist):
        p = _publish_parcel(client, admin, "wd", area_m2=3000)
        S["pid2"] = p["id"]
        req = _new_request(specialist, p["id"], area_m2=500, note=f"{TAG} cerere retragere")
        S["rid2"] = req["id"]
        assert req["status"] == "sent"

    def test_owner_cannot_withdraw(self, client):
        _err(client.post(f"{R}/requests/{S['rid2']}/withdraw", timeout=TIMEOUT), 403)

    def test_requester_withdraws(self, specialist):
        r = specialist.post(f"{R}/requests/{S['rid2']}/withdraw", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "request")["status"] == "withdrawn"
        assert _get_request(specialist, S["rid2"])["request"]["status"] == "withdrawn"

    def test_actions_after_withdraw_rejected(self, client, specialist):
        rid = S["rid2"]
        _4xx(specialist.post(f"{R}/requests/{rid}/withdraw", timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/requests/{rid}/messages", json={"text": "mai e valabil?"}, timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/requests/{rid}/counter", json=_proposal(), timeout=TIMEOUT))
        _4xx(client.post(f"{R}/requests/{rid}/messages", json={"text": "?"}, timeout=TIMEOUT))
        _4xx(client.post(f"{R}/requests/{rid}/decline", json={"reason": "tarziu"}, timeout=TIMEOUT))
        _4xx(client.post(f"{R}/requests/{rid}/accept", timeout=TIMEOUT))
        assert _get_request(client, rid)["request"]["status"] == "withdrawn"

    def test_new_request_after_withdraw(self, specialist):
        req = _new_request(specialist, S["pid2"], area_m2=600, note=f"{TAG} cerere decline")
        assert req["status"] == "sent"
        assert req["id"] != S["rid2"]
        S["rid3"] = req["id"]

    def test_requester_cannot_decline(self, specialist):
        _err(specialist.post(f"{R}/requests/{S['rid3']}/decline", json={"reason": "x"}, timeout=TIMEOUT), 403)

    def test_decline_reason_too_long(self, client):
        _err(client.post(f"{R}/requests/{S['rid3']}/decline", json={"reason": "x" * 501}, timeout=TIMEOUT), 400)

    def test_owner_declines_with_reason(self, client, specialist):
        reason = f"{TAG} nu se potrivește"
        r = client.post(f"{R}/requests/{S['rid3']}/decline", json={"reason": reason}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        req = _unwrap(r.json(), "request")
        assert req["status"] == "declined"
        assert req["decline_reason"] == reason
        got = _get_request(specialist, S["rid3"])["request"]
        assert got["status"] == "declined" and got["decline_reason"] == reason
        assert got.get("decided_at")

    def test_actions_after_decline_rejected(self, client, specialist):
        rid = S["rid3"]
        _4xx(client.post(f"{R}/requests/{rid}/decline", json={}, timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/requests/{rid}/withdraw", timeout=TIMEOUT))
        _4xx(specialist.post(f"{R}/requests/{rid}/messages", json={"text": "te rog"}, timeout=TIMEOUT))
        _4xx(client.post(f"{R}/requests/{rid}/accept", timeout=TIMEOUT))


# ── 10. cancel flow ──────────────────────────────────────────────────────────

class TestCancelFlow:
    def test_setup_accept(self, client, admin, specialist):
        p = _publish_parcel(client, admin, "cancel", area_m2=2500)
        S["pid3"] = p["id"]
        req = _new_request(specialist, p["id"], area_m2=700, note=f"{TAG} cerere anulare")
        r = client.post(f"{R}/requests/{req['id']}/accept", timeout=TIMEOUT)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d["request"]["status"] == "accepted"
        assert d["agreement"]["status"] == "draft" and d["agreement"]["version"] == 1
        S["rid4"], S["aid4"] = req["id"], d["agreement"]["id"]

    def test_cancel_requires_auth_and_party(self, anon, admin):
        assert anon.post(f"{R}/agreements/{S['aid4']}/cancel", json={}, timeout=TIMEOUT).status_code == 401
        _err(admin.post(f"{R}/agreements/{S['aid4']}/cancel", json={}, timeout=TIMEOUT), 403)

    def test_cancel_draft(self, specialist, client):
        r = specialist.post(f"{R}/agreements/{S['aid4']}/cancel", json={"reason": f"{TAG} renunț"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ag = _unwrap(r.json(), "agreement")
        assert ag["status"] == "cancelled"
        assert ag["cancelled_at"]
        assert ag["cancel_reason"] == f"{TAG} renunț"
        assert _get_agreement(client, S["aid4"])["status"] == "cancelled"

    def test_request_stays_accepted_parcel_unchanged(self, client):
        assert _get_request(client, S["rid4"])["request"]["status"] == "accepted"
        p = _get_parcel(client, S["pid3"])
        assert p["status"] == "published"
        assert not p.get("active_agreement_id")

    def test_actions_after_cancel_rejected(self, client, specialist):
        _err(client.post(f"{R}/agreements/{S['aid4']}/cancel", json={}, timeout=TIMEOUT), 409)
        _4xx(client.post(f"{R}/agreements/{S['aid4']}/propose", timeout=TIMEOUT))
        _4xx(client.post(f"{R}/agreements/{S['aid4']}/sign", json={"version": 1}, timeout=TIMEOUT))
        _4xx(specialist.patch(f"{R}/agreements/{S['aid4']}", json={"terms": {"price_ron_per_year": 10}}, timeout=TIMEOUT))

    def test_cancel_proposed(self, client, admin, specialist):
        """Cancel is also allowed from `proposed` (separate parcel/request/agreement)."""
        p = _publish_parcel(client, admin, "cancel-proposed", area_m2=2000)
        req = _new_request(specialist, p["id"], area_m2=300, note=f"{TAG} cerere anulare 2")
        d = client.post(f"{R}/requests/{req['id']}/accept", timeout=TIMEOUT).json()
        aid = d["agreement"]["id"]
        r = client.post(f"{R}/agreements/{aid}/propose", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r = client.post(f"{R}/agreements/{aid}/cancel", json={}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "agreement")["status"] == "cancelled"
        assert _get_parcel(client, p["id"])["status"] == "published"


# ── 11. impersonation: an admin acting as a user cannot decide on their behalf ──

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


def _blocked(r):
    _err(r, 403)
    assert "impersonare" in r.json()["detail"]


class TestImpersonationBlocked:
    def test_owner_decisions_blocked(self):
        s = _impersonate(S["owner_uid"])
        try:
            _blocked(s.post(f"{R}/parcels/{S['draft_pid']}/submit", timeout=TIMEOUT))
            _blocked(s.delete(f"{R}/parcels/{S['draft_pid']}", timeout=TIMEOUT))
            _blocked(s.post(f"{R}/requests/{S['rid']}/accept", timeout=TIMEOUT))
            _blocked(s.post(f"{R}/requests/{S['rid']}/decline", json={}, timeout=TIMEOUT))
            _blocked(s.post(f"{R}/agreements/{S['aid']}/propose", timeout=TIMEOUT))
            _blocked(s.post(f"{R}/agreements/{S['aid']}/sign", json={"version": 1}, timeout=TIMEOUT))
            _blocked(s.post(f"{R}/agreements/{S['aid']}/cancel", json={}, timeout=TIMEOUT))
            _blocked(s.patch(f"{R}/agreements/{S['aid']}", json={"terms": {"price_ron_per_year": 1}}, timeout=TIMEOUT))
        finally:
            s.post(f"{API}/admin/stop-impersonation", timeout=TIMEOUT)

    def test_requester_decisions_blocked(self):
        s = _impersonate(S["req_uid"])
        try:
            _blocked(s.post(f"{R}/parcels/{S['pid']}/requests", json=_request_body(), timeout=TIMEOUT))
            _blocked(s.post(f"{R}/requests/{S['rid']}/withdraw", timeout=TIMEOUT))
            _blocked(s.post(f"{R}/requests/{S['rid']}/counter", json=_proposal(), timeout=TIMEOUT))
        finally:
            s.post(f"{API}/admin/stop-impersonation", timeout=TIMEOUT)

    def test_nothing_changed(self, client):
        assert _get_parcel(client, S["draft_pid"])["status"] == "draft"
        assert _get_request(client, S["rid"])["request"]["status"] == "accepted"


# ── 12. signing: competing agreements, edited parcel ─────────────────────────

class TestCompetingAgreements:
    def test_setup_two_accepted_requests(self, client, admin, specialist):
        p = _publish_parcel(client, admin, "competing", area_m2=4000)
        S["pidc"] = p["id"]
        r1 = _new_request(specialist, p["id"], area_m2=500, note=f"{TAG} cerere C1")
        r2 = _new_request(admin, p["id"], area_m2=600, note=f"{TAG} cerere C2")
        for key, req in (("1", r1), ("2", r2)):
            r = client.post(f"{R}/requests/{req['id']}/accept", timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            S[f"aidc{key}"] = r.json()["agreement"]["id"]
        assert S["aidc1"] != S["aidc2"]

    def test_patch_with_unchanged_start_date_allowed(self, client):
        ag = _get_agreement(client, S["aidc1"])
        r = client.patch(
            f"{R}/agreements/{S['aidc1']}",
            json={"terms": {"start_date": ag["terms"]["start_date"], "price_ron_per_year": 900}},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        assert _unwrap(r.json(), "agreement")["version"] == 2

    def test_propose_both_and_sign_first(self, client, specialist):
        # the second agreement is proposed too (proposed agreements are cancelled on assignment as well)
        assert client.post(f"{R}/agreements/{S['aidc2']}/propose", timeout=TIMEOUT).status_code == 200
        assert client.post(f"{R}/agreements/{S['aidc1']}/propose", timeout=TIMEOUT).status_code == 200
        for sess in (client, specialist):
            r = sess.post(f"{R}/agreements/{S['aidc1']}/sign", json={"version": 2}, timeout=TIMEOUT)
            assert r.status_code == 200, r.text
        assert _get_agreement(client, S["aidc1"])["status"] == "signed"

    def test_competing_agreement_cancelled(self, client, admin):
        for sess in (client, admin):
            ag = _get_agreement(sess, S["aidc2"])
            assert ag["status"] == "cancelled"
            assert ag["cancel_reason"] == "Terenul a fost atribuit altui acord."
            assert ag["cancelled_at"]

    def test_cancelled_agreement_cannot_be_signed(self, admin, client):
        _4xx(client.post(f"{R}/agreements/{S['aidc2']}/sign", json={"version": 1}, timeout=TIMEOUT))
        _4xx(admin.post(f"{R}/agreements/{S['aidc2']}/sign", json={"version": 1}, timeout=TIMEOUT))
        assert _get_parcel(client, S["pidc"])["active_agreement_id"] == S["aidc1"]


class TestSignWithEditedParcel:
    def test_setup_owner_signs_then_edits_parcel(self, client, admin, specialist):
        p = _publish_parcel(client, admin, "edited-after-accept", area_m2=2000)
        S["pide"] = p["id"]
        req = _new_request(specialist, p["id"], area_m2=300, note=f"{TAG} cerere editare")
        r = client.post(f"{R}/requests/{req['id']}/accept", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        S["aide"] = r.json()["agreement"]["id"]
        assert client.post(f"{R}/agreements/{S['aide']}/propose", timeout=TIMEOUT).status_code == 200
        r = client.post(f"{R}/agreements/{S['aide']}/sign", json={"version": 1}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        # the owner pauses the parcel and changes its content: it goes back to draft (re-verification needed)
        assert client.post(f"{R}/parcels/{p['id']}/pause", timeout=TIMEOUT).status_code == 200
        r = client.patch(f"{R}/parcels/{p['id']}", json={"description": f"{TAG} editat dupa acceptare"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert _get_parcel(client, p["id"])["status"] == "draft"

    def test_cultivator_cannot_sign_unverified_parcel(self, client, specialist):
        _err(specialist.post(f"{R}/agreements/{S['aide']}/sign", json={"version": 1}, timeout=TIMEOUT), 409)
        ag = _get_agreement(client, S["aide"])
        assert ag["status"] == "proposed" and len(ag["signatures"]) == 1
        assert not _get_parcel(client, S["pide"]).get("active_agreement_id")

    def test_cancel_agreement(self, client):
        r = client.post(f"{R}/agreements/{S['aide']}/cancel", json={}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text


# ── 13. concurrency ──────────────────────────────────────────────────────────

class TestRequestRace:
    def test_parallel_duplicate_requests_create_one(self, client, admin, specialist):
        p = _publish_parcel(client, admin, "race", area_m2=2000)

        def go(i):
            return _post_request(specialist, p["id"], area_m2=300, note=f"{TAG} race {i}").status_code

        with ThreadPoolExecutor(max_workers=5) as ex:
            codes = list(ex.map(go, range(5)))
        assert len([c for c in codes if c in (200, 201)]) == 1, codes
        assert all(c == 409 for c in codes if c not in (200, 201)), codes
        sent = _items(specialist.get(f"{R}/requests/sent", timeout=TIMEOUT).json())
        assert len([i for i in sent if i["parcel_id"] == p["id"]]) == 1
