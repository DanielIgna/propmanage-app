"""UX-001 Emotional Engagement & Achievements — backend regression suite.

Covers: structura summary (10 insigne cu explainability completă, achievement final
„Proprietate publicată prin PropManage", badge „Documentație verificată"), prima rulare
silențioasă, detecție level-up/milestone/readiness_gain prin manipulare de stare,
idempotență, intrări în AI Timeline (copilot_timeline, kind), config Admin E2E, 401, regresii.
"""
import os

import pymongo
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}

BADGE_IDS = ["first_document", "first_request", "first_work", "twin_active", "house_health_active",
             "doc_verified", "community_ambassador", "founding_ambassador", "imobil_verificat", "casa_publicata"]

_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200
    return s


def _uid():
    u = _db.users.find_one({"email": CLIENT["email"]})
    return u.get("id") or str(u["_id"])


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


class TestFirstRunSilent:
    def test_first_run_no_retroactive_events(self, client_sess):
        uid = _uid()
        _db.engagement_state.delete_many({"user_id": uid})
        _db.copilot_timeline.delete_many({"user_id": uid, "kind": {"$exists": True}})
        d = client_sess.get(f"{BASE_URL}/api/engagement/summary", timeout=90).json()
        assert d["enabled"] is True
        assert d["new_events"] == [], "prima rulare trebuie să fie silențioasă"
        assert d["badges_earned_count"] >= 1, "insignele deja câștigate se marchează silențios"


class TestStructure:
    @pytest.fixture(scope="class")
    def summary(self, client_sess):
        return client_sess.get(f"{BASE_URL}/api/engagement/summary", timeout=90).json()

    def test_ten_badges_with_full_explainability(self, summary):
        assert [b["id"] for b in summary["badges"]] == BADGE_IDS
        for b in summary["badges"]:
            for k in ("why", "meaning", "benefit", "next", "icon", "label"):
                assert b.get(k), f"badge {b['id']} fără explainability `{k}`"
            assert isinstance(b["earned"], bool)

    def test_final_achievement_naming(self, summary):
        final = next(b for b in summary["badges"] if b["id"] == "casa_publicata")
        assert final["label"] == "Proprietate publicată prin PropManage"
        assert final["icon"] == "🏡"

    def test_doc_verified_badge_transparency(self, summary):
        dv = next(b for b in summary["badges"] if b["id"] == "doc_verified")
        assert "NU înseamnă că imobilul este perfect" in dv["meaning"]
        assert dv["icon"] == "🛡"

    def test_dashboard_rows(self, summary):
        for k in ("last_achievement", "last_progress", "next_objective", "next_unlock", "milestones", "level"):
            assert k in summary
        assert summary["level"]["current"] >= 1
        nm = summary["milestones"]["next"]
        if nm:
            assert nm["pct"] > summary["milestones"]["readiness"] and nm["message"]

    def test_earned_from_real_signals(self, summary):
        earned = {b["id"]: b["earned"] for b in summary["badges"]}
        assert earned["first_request"] is True, "clientul demo are cereri"
        assert earned["first_work"] is True, "clientul demo are lucrare confirmată"
        assert earned["casa_publicata"] is False


class TestDetection:
    def test_level_up_milestone_and_gain_detected(self, client_sess):
        uid = _uid()
        _db.engagement_state.update_one({"user_id": uid}, {"$set": {
            "last_level": 0, "last_readiness": 0, "milestones_hit": []}})
        d = client_sess.get(f"{BASE_URL}/api/engagement/summary", timeout=90).json()
        types = {e["type"] for e in d["new_events"]}
        assert "level_up" in types, f"level_up nedetectat: {d['new_events']}"
        lvl_ev = next(e for e in d["new_events"] if e["type"] == "level_up")
        assert lvl_ev["title"].startswith("Nivel")
        r = d["milestones"]["readiness"]
        if r >= 10:
            assert "milestone" in types
        if r >= 5:
            assert "readiness_gain" in types

    def test_timeline_entries_created(self, client_sess):
        uid = _uid()
        entries = list(_db.copilot_timeline.find({"user_id": uid, "kind": {"$exists": True}}))
        assert entries, "evenimentele trebuie salvate în AI Timeline"
        kinds = {e["kind"] for e in entries}
        assert "level_up" in kinds
        for e in entries:
            assert e["status"] == "done" and e["title"]
        # apar și în endpoint-ul de timeline existent
        tl = client_sess.get(f"{BASE_URL}/api/copilot/timeline", timeout=30).json()["items"]
        assert any(i.get("kind") for i in tl)

    def test_idempotent_second_call(self, client_sess):
        d = client_sess.get(f"{BASE_URL}/api/engagement/summary", timeout=90).json()
        assert d["new_events"] == [], "al doilea apel nu trebuie să dubleze evenimentele"


class TestAdminConfig:
    def test_engagement_configurable(self, admin_sess, client_sess):
        cfg = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=30).json()
        eng = cfg["engagement"]
        assert len(eng["badges"]) == 10 and eng["milestones"] == [10, 25, 50, 75, 90, 100]
        orig = eng["level_messages"]["2"]
        try:
            eng2 = {**eng, "level_messages": {**eng["level_messages"], "2": "Test UX-001 mesaj"}}
            r = admin_sess.patch(f"{BASE_URL}/api/admin/prop-benefits/config", json={"engagement": eng2}, timeout=30)
            assert r.status_code == 200
            got = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=30).json()
            assert got["engagement"]["level_messages"]["2"] == "Test UX-001 mesaj"
        finally:
            admin_sess.patch(f"{BASE_URL}/api/admin/prop-benefits/config",
                             json={"engagement": {**eng, "level_messages": {**eng["level_messages"], "2": orig}}}, timeout=30)

    def test_disabled_system(self, admin_sess, client_sess):
        cfg = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=30).json()["engagement"]
        try:
            admin_sess.patch(f"{BASE_URL}/api/admin/prop-benefits/config",
                             json={"engagement": {**cfg, "enabled": False}}, timeout=30)
            d = client_sess.get(f"{BASE_URL}/api/engagement/summary", timeout=60).json()
            assert d == {"enabled": False}
        finally:
            admin_sess.patch(f"{BASE_URL}/api/admin/prop-benefits/config",
                             json={"engagement": {**cfg, "enabled": True}}, timeout=30)


class TestSecurityAndRegression:
    def test_requires_auth(self):
        assert requests.get(f"{BASE_URL}/api/engagement/summary", timeout=20).status_code in (401, 403)

    def test_copilot_and_journey_unchanged(self, client_sess):
        d = client_sess.get(f"{BASE_URL}/api/copilot/dashboard", timeout=90).json()
        assert d["house_score"]["score"] >= 0 and d.get("journey")
        j = client_sess.get(f"{BASE_URL}/api/journey/house", timeout=60).json()
        assert len(j["levels"]) == 7
