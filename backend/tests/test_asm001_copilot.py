"""ASM-001 Copilotul Casei — backend regression suite.

Covers: dashboard structure completă (Scorul Casei explicabil, rezumat, next action cu
explainability, checklist, progres, beneficii, comunitate cu Founding Ambassador,
storage ST-001, subscription health), timeline (înregistrare + istoric), securitate 401,
regresii success-manager / pulse / ambassador.
"""
import os

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def dashboard(client_sess):
    r = client_sess.get(f"{BASE_URL}/api/copilot/dashboard", timeout=90)
    assert r.status_code == 200, r.text[:400]
    return r.json()


class TestDashboardStructure:
    def test_all_sections_present(self, dashboard):
        for k in ("house_score", "summary", "next_action", "checklist", "progress",
                  "benefits", "community", "storage", "subscription", "timeline"):
            assert k in dashboard, f"missing section {k}"

    def test_house_score_explicabil(self, dashboard):
        hs = dashboard["house_score"]
        assert 0 <= hs["score"] <= 100
        keys = {i["key"] for i in hs["items"]}
        assert keys == {"cartea_casei", "digital_twin", "house_health", "mentenanta",
                        "beneficii", "comunitate", "progres"}
        assert sum(i["max"] for i in hs["items"]) == 100
        for i in hs["items"]:
            assert 0 <= i["points"] <= i["max"]

    def test_next_action_explainability(self, dashboard):
        na = dashboard["next_action"]
        assert na, "clientul demo trebuie să aibă o acțiune recomandată"
        ex = na.get("explain")
        assert ex, "explainability lipsă"
        for k in ("why", "gain", "unlocks", "duration", "house_impact"):
            assert ex.get(k), f"explain.{k} lipsă"
        # acțiunile secundare au și ele explain
        for a in dashboard.get("secondary") or []:
            assert a.get("explain")

    def test_summary_house_centric(self, dashboard):
        s = dashboard["summary"]
        assert s.get("text") and len(s["text"]) > 30
        assert s.get("source") in ("ai", "ai_cached", "deterministic")

    def test_checklist(self, dashboard):
        cl = dashboard["checklist"]
        assert cl["total"] == 5
        ids = [s["id"] for s in cl["steps"]]
        assert ids == ["create_book", "first_document", "first_benefit", "discover_deals", "first_request"]
        # clientul demo are proprietate → primul pas bifat; restul reflectă semnale reale
        assert cl["steps"][0]["done"] is True
        assert all(isinstance(s["done"], bool) for s in cl["steps"])
        assert cl["done"] == sum(1 for s in cl["steps"] if s["done"])

    def test_progress(self, dashboard):
        p = dashboard["progress"]
        assert 0 <= p["book"]["pct"] <= 100
        assert 0 <= p["twin"]["pct"] <= 100
        assert p["membership"].get("level")

    def test_benefits_section(self, dashboard):
        b = dashboard["benefits"]
        for k in ("available", "expiring_soon", "almost_unlocked", "used"):
            assert k in b

    def test_community_founding_ambassador(self, dashboard):
        c = dashboard["community"]
        amb = c["ambassador"]
        for k in ("is_ambassador", "is_founding", "founding_badge", "founding_slots_left", "threshold"):
            assert k in amb, f"ambassador.{k} lipsă"
        assert amb["founding_badge"] == "Founding Ambassador"
        assert 0 <= amb["founding_slots_left"] <= 10
        assert "deals_needing_support" in c and isinstance(c["deals_needing_support"], list)

    def test_storage_st001_reuse(self, dashboard):
        st = dashboard["storage"]
        assert st and "personal" in st
        p = st["personal"]
        assert p["quota_bytes"] > 0 and "pct" in p and "tier_label" in p

    def test_subscription_health(self, dashboard):
        sub = dashboard["subscription"]
        assert 0 <= sub["score"] <= 100
        assert sub["status"] in ("healthy", "watch", "at_risk")
        assert isinstance(sub["factors"], list) and len(sub["factors"]) == 8


class TestTimeline:
    def test_recommendation_logged(self, client_sess, dashboard):
        """Dashboard-ul loghează recomandarea top în timeline."""
        r = client_sess.get(f"{BASE_URL}/api/copilot/timeline", timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        assert items, "timeline gol după generarea dashboard-ului"
        top_id = dashboard["next_action"]["id"]
        assert any(e["action_id"] == top_id for e in items)
        for e in items:
            assert e["status"] in ("recommended", "done")

    def test_dashboard_idempotent_no_duplicates(self, client_sess):
        """Două generări consecutive NU dublează intrarea recomandată activă."""
        client_sess.get(f"{BASE_URL}/api/copilot/dashboard", timeout=90)
        items = client_sess.get(f"{BASE_URL}/api/copilot/timeline", timeout=30).json()["items"]
        active = [e for e in items if e["status"] == "recommended"]
        ids = [e["action_id"] for e in active]
        assert len(ids) == len(set(ids)), f"duplicate în timeline: {ids}"


class TestSecurityAndRegression:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/copilot/dashboard", timeout=20)
        assert r.status_code in (401, 403)
        r2 = requests.get(f"{BASE_URL}/api/copilot/timeline", timeout=20)
        assert r2.status_code in (401, 403)

    def test_success_manager_unchanged(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/success-manager", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "next_action" in d and "health" in d

    def test_pulse_unchanged(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/pulse", timeout=60)
        assert r.status_code == 200
        assert "next_action" in r.json()

    def test_ambassador_endpoint_extended(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/ambassador", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "is_founding" in d and "founding_slots_left" in d
        # câmpurile vechi rămân (regresie AmbassadorCard)
        for k in ("is_ambassador", "validated", "threshold", "badge"):
            assert k in d
