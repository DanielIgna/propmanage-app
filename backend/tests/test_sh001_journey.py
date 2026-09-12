"""SH-001 House Journey & Readiness — backend regression suite.

Covers: journey L1→L7 (structură, statusuri, cerințe explicabile), House Readiness
(5 dimensiuni ponderate din config, missing lists), FairPrice data contract
(fairprice_signals persistate + endpoint), praguri configurabile din Admin,
integrare Copilot (journey + chain + improvements), securitate, regresii.
"""
import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}

LEVEL_KEYS = ["casa_creata", "cartea_casei", "digital_twin", "house_health",
              "doc_verificata", "imobil_verificat", "publicat"]
DIM_KEYS = ["administrare", "mentenanta", "audit", "finantare", "vanzare"]


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def journey(client_sess):
    r = client_sess.get(f"{BASE_URL}/api/journey/house", timeout=60)
    assert r.status_code == 200, r.text[:400]
    return r.json()


class TestJourney:
    def test_seven_levels(self, journey):
        assert [L["key"] for L in journey["levels"]] == LEVEL_KEYS
        for L in journey["levels"]:
            assert L["status"] in ("done", "in_progress", "missing")
            assert 0 <= L["pct"] <= 100
            assert L["requirements"], f"nivelul {L['key']} fără cerințe explicabile"
            for req in L["requirements"]:
                assert "label" in req and "done" in req

    def test_current_level_contiguous(self, journey):
        cur = journey["current_level"]
        assert 0 <= cur <= 7
        for L in journey["levels"][:cur]:
            assert L["status"] == "done"
        # clientul demo are proprietate → minim L1
        assert cur >= 1

    def test_next_level_explainable(self, journey):
        if journey["current_level"] < 7:
            nxt = journey["next_level"]
            assert nxt and nxt["missing"], "next_level trebuie să spună exact ce lipsește"
            assert all(m["label"] for m in nxt["missing"])

    def test_l6_transparency_note(self, journey):
        l6 = next(L for L in journey["levels"] if L["key"] == "imobil_verificat")
        assert "NU e blocată" in (l6.get("note") or ""), "nota de transparență L6 lipsă"


class TestReadiness:
    def test_five_dimensions(self, journey):
        r = journey["readiness"]
        assert 0 <= r["score"] <= 100
        assert [d["key"] for d in r["dimensions"]] == DIM_KEYS
        for d in r["dimensions"]:
            assert 0 <= d["pct"] <= 100
            assert d["weight"] > 0
            for m in d["missing"]:
                assert m["label"]

    def test_weighted_score_matches(self, journey, admin_sess):
        cfg = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=30).json()
        w = cfg["journey"]["readiness_weights"]
        r = journey["readiness"]
        expected = round(sum(d["pct"] * w[d["key"]] for d in r["dimensions"]) / sum(w.values()))
        assert abs(r["score"] - expected) <= 1, "scorul readiness nu respectă ponderile din config"

    def test_documentation_not_perfection(self, journey):
        assert "DOCUMENTATĂ" in journey["readiness"]["note"]


class TestConfigurable:
    def test_journey_config_in_admin(self, admin_sess):
        cfg = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=30).json()
        j = cfg["journey"]
        assert j["doc_verified_min_completeness"] >= 1
        assert isinstance(j["doc_verified_required_categories"], list)
        assert set(j["readiness_weights"]) == set(DIM_KEYS)

    def test_threshold_change_reflected(self, admin_sess, client_sess):
        cfg = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=30).json()
        orig = cfg["journey"]["doc_verified_min_completeness"]
        try:
            r = admin_sess.patch(f"{BASE_URL}/api/admin/prop-benefits/config",
                                 json={"journey": {**cfg["journey"], "doc_verified_min_completeness": 33}}, timeout=30)
            assert r.status_code == 200
            j = client_sess.get(f"{BASE_URL}/api/journey/house", timeout=60).json()
            l5 = next(L for L in j["levels"] if L["key"] == "doc_verificata")
            assert any("33%" in req["label"] for req in l5["requirements"]), "pragul din config nu e folosit"
        finally:
            admin_sess.patch(f"{BASE_URL}/api/admin/prop-benefits/config",
                             json={"journey": {**cfg["journey"], "doc_verified_min_completeness": orig}}, timeout=30)


class TestFairPriceContract:
    def test_signals_endpoint(self, client_sess, journey):
        r = client_sess.get(f"{BASE_URL}/api/fairprice/signals", timeout=60)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("property_id")
        s = d["signals"]
        for k in ("documentare", "verificare", "digital_twin", "house_health",
                  "transparenta", "istoric", "mentenanta"):
            assert k in s and 0 <= s[k] <= 100, f"semnal {k} invalid"
        assert d["journey_level"] == journey["current_level"]
        assert d["readiness_score"] == journey["readiness"]["score"]

    def test_signals_persisted(self, client_sess):
        d = client_sess.get(f"{BASE_URL}/api/fairprice/signals", timeout=60).json()
        assert d.get("updated_at"), "semnalele trebuie persistate în fairprice_signals"


class TestCopilotIntegration:
    @pytest.fixture(scope="class")
    def dash(self, client_sess):
        return client_sess.get(f"{BASE_URL}/api/copilot/dashboard", timeout=90).json()

    def test_copilot_has_journey(self, dash):
        j = dash.get("journey")
        assert j and j["total_levels"] == 7
        assert "current_level" in j and "readiness_score" in j

    def test_chained_recommendation(self, dash):
        na = dash["next_action"]
        chain = na["explain"].get("chain")
        assert chain and len(chain) >= 3, "recomandarea principală trebuie să aibă lanț de efecte"
        assert any("FairPrice" in c for c in chain)

    def test_subscription_improvements(self, dash):
        imp = dash["subscription"].get("improvements")
        assert isinstance(imp, list)
        for i in imp:
            assert i["label"] and i["gain"] > 0


class TestSecurityAndRegression:
    def test_requires_auth(self):
        assert requests.get(f"{BASE_URL}/api/journey/house", timeout=20).status_code in (401, 403)
        assert requests.get(f"{BASE_URL}/api/fairprice/signals", timeout=20).status_code in (401, 403)

    def test_verified_estate_untouched(self):
        r = requests.get(f"{BASE_URL}/api/verified-estate/listings", timeout=30)
        assert r.status_code == 200

    def test_success_manager_unchanged(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/success-manager", timeout=60)
        assert r.status_code == 200 and "next_action" in r.json()
