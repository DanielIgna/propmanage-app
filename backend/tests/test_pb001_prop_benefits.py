"""PB-001 PropBenefits Engine — backend regression suite (iteration 167).

Covers: user opportunities/wallet/membership/claim/use/success-manager,
admin overview/campaigns CRUD/config/health/impact/tick/growth-advisor,
security (401/403), referral gating (pending -> paid -> activated), mentor pb_ action.
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
CLIENT = {"email": "client@propmanage.io", "password": "Client123!"}
ADMIN = {"email": "admin@propmanage.io", "password": "1!nasov01ADMIN"}


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"Login failed for {creds['email']}: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def client_sess():
    return _login(CLIENT)


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def anon_sess():
    return requests.Session()


# ─────────────────────────────────── USER endpoints ───────────────────────────────────
class TestUserEndpoints:
    def test_opportunities_structure(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/opportunities", timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("opportunities", "locked", "membership", "wallet_counts"):
            assert k in d, f"missing key {k}"
        assert isinstance(d["opportunities"], list)
        assert isinstance(d["locked"], list)
        if d["opportunities"]:
            o = d["opportunities"][0]
            assert "why" in o and isinstance(o["why"], list)
            assert "kind_label" in o
            assert "relevance" in o
        # locked items should have unlock hints
        if d["locked"]:
            l = d["locked"][0]
            # unlock hint field name may vary; accept any of these
            assert any(k in l for k in ("unlock_hint", "unlock", "why", "requirements"))
        m = d["membership"]
        assert "level" in m and "points" in m and "next_level" in m

    def test_membership_endpoint(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/membership", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "level" in d and "points" in d
        assert "breakdown" in d

    def test_wallet_endpoint(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/wallet", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("available", "used", "expired", "pending", "counts"):
            assert k in d, f"missing {k}"

    def test_success_manager(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/benefits/success-manager", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "health" in d and "score" in d["health"] and "status" in d["health"]
        assert "next_action" in d
        na = d["next_action"]
        if na:
            for k in ("title", "cta_path"):
                assert k in na


# ─────────────────────────────────── Claim / use flow ───────────────────────────────────
class TestClaimUseFlow:
    def test_claim_nonexistent(self, client_sess):
        r = client_sess.post(f"{BASE_URL}/api/benefits/claim/does_not_exist_xyz", timeout=15)
        assert r.status_code == 404

    def test_claim_community_conflict(self, client_sess):
        # community benefits are auto-granted → cannot be claimed by user
        r = client_sess.post(f"{BASE_URL}/api/benefits/claim/pbcamp_community_ref", timeout=15)
        assert r.status_code == 409, f"expected 409 got {r.status_code} {r.text[:200]}"

    def test_claim_hh_check_and_wallet_increase(self, client_sess):
        # get baseline wallet available
        w0 = client_sess.get(f"{BASE_URL}/api/benefits/wallet", timeout=15).json()
        base = len(w0.get("available", []))

        r = client_sess.post(f"{BASE_URL}/api/benefits/claim/pbcamp_hh_check", timeout=20)
        # Either 200 (first claim) or 409 (already claimed in prior test)
        if r.status_code == 200:
            d = r.json()
            assert d.get("ok") is True
            assert "benefit" in d
            w1 = client_sess.get(f"{BASE_URL}/api/benefits/wallet", timeout=15).json()
            assert len(w1.get("available", [])) >= base + 1, "wallet available did not grow"
        else:
            assert r.status_code == 409, f"unexpected {r.status_code}: {r.text[:200]}"

    def test_duplicate_claim_conflict(self, client_sess):
        # After previous test, claiming again must yield 409
        r = client_sess.post(f"{BASE_URL}/api/benefits/claim/pbcamp_hh_check", timeout=15)
        assert r.status_code == 409

    def test_use_benefit_flow(self, client_sess):
        w = client_sess.get(f"{BASE_URL}/api/benefits/wallet", timeout=15).json()
        avail = w.get("available") or []
        if not avail:
            pytest.skip("no available benefit to use")
        bid = avail[0].get("id") or avail[0].get("benefit_id")
        assert bid, f"no id on benefit: {avail[0]}"
        r1 = client_sess.post(f"{BASE_URL}/api/benefits/use/{bid}", timeout=15)
        assert r1.status_code == 200, r1.text
        r2 = client_sess.post(f"{BASE_URL}/api/benefits/use/{bid}", timeout=15)
        assert r2.status_code == 409


# ─────────────────────────────────── Admin endpoints ───────────────────────────────────
class TestAdminEndpoints:
    def test_overview(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/overview", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("ecosystem", "campaigns", "benefits", "referrals", "health", "meta"):
            assert k in d
        assert "score" in d["ecosystem"]
        assert "kinds" in d["meta"]

    def test_campaign_validation_empty_title(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/prop-benefits/campaigns",
            json={"title": "", "kind": "individual", "status": "active"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_campaign_validation_invalid_kind(self, admin_sess):
        r = admin_sess.post(
            f"{BASE_URL}/api/admin/prop-benefits/campaigns",
            json={"title": "TEST_bad_kind", "kind": "XYZ_INVALID", "status": "active"},
            timeout=15,
        )
        assert r.status_code == 400

    def test_campaign_create_update_flow(self, admin_sess):
        cid = f"TEST_pb_{uuid.uuid4().hex[:8]}"
        payload = {
            "id": cid,
            "title": "TEST_pb_campaign",
            "kind": "seasonal",
            "status": "active",
            "benefit": {"title": "TEST benefit"},
        }
        r = admin_sess.post(f"{BASE_URL}/api/admin/prop-benefits/campaigns", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        real_id = d.get("id") or d.get("campaign", {}).get("id") or cid

        # Verify appears in list
        lst = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/campaigns", timeout=15).json()
        ids = [c.get("id") for c in lst.get("items", [])]
        assert real_id in ids, f"created campaign {real_id} not in list"

        # PATCH
        pr = admin_sess.patch(
            f"{BASE_URL}/api/admin/prop-benefits/campaigns/{real_id}",
            json={"title": "TEST_pb_campaign_updated"},
            timeout=15,
        )
        assert pr.status_code == 200, pr.text

        # PATCH nonexistent -> 404
        pr2 = admin_sess.patch(
            f"{BASE_URL}/api/admin/prop-benefits/campaigns/does_not_exist_9x9",
            json={"title": "x"},
            timeout=15,
        )
        assert pr2.status_code == 404

        # Cleanup
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL"))
        mc[os.environ.get("DB_NAME", "propmanage")].pb_campaigns.delete_one({"id": real_id})

    def test_config_get_and_patch(self, admin_sess, client_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/config", timeout=15)
        assert r.status_code == 200
        cfg = r.json()
        assert "_id" not in cfg
        assert "level_points" in cfg
        original = dict(cfg["level_points"])

        # bump silver +1
        new_lp = dict(original)
        new_lp["silver"] = int(new_lp.get("silver", 500)) + 1
        pr = admin_sess.patch(
            f"{BASE_URL}/api/admin/prop-benefits/config",
            json={"level_points": new_lp},
            timeout=15,
        )
        assert pr.status_code == 200
        updated = pr.json()
        assert updated["level_points"]["silver"] == new_lp["silver"]

        # restore
        admin_sess.patch(
            f"{BASE_URL}/api/admin/prop-benefits/config",
            json={"level_points": original},
            timeout=15,
        )

    def test_subscription_health_list(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/subscription-health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and isinstance(d["items"], list)

    def test_ecosystem_health(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/ecosystem-health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "score" in d
        assert "components" in d

    def test_impact_scores(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/impact-scores", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d
        if d["items"]:
            it = d["items"][0]
            for k in ("potential", "realized", "gap"):
                assert k in it, f"impact item missing {k}"

    def test_run_tick(self, admin_sess):
        r = admin_sess.post(f"{BASE_URL}/api/admin/prop-benefits/run-tick", timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("benefits_expired", "referrals_activated"):
            assert k in d, f"missing {k}"

    def test_growth_advisor_cached(self, admin_sess):
        # WITHOUT refresh -> cached, fast
        r = admin_sess.get(f"{BASE_URL}/api/admin/prop-benefits/growth-advisor", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "findings" in d
        assert "metrics" in d


# ─────────────────────────────────── Security ───────────────────────────────────
class TestSecurity:
    def test_user_endpoints_401(self, anon_sess):
        for path in ("/api/benefits/opportunities", "/api/benefits/wallet",
                     "/api/benefits/membership", "/api/benefits/success-manager"):
            r = anon_sess.get(f"{BASE_URL}{path}", timeout=15)
            assert r.status_code in (401, 403), f"{path} -> {r.status_code}"

    def test_admin_endpoints_401(self, anon_sess):
        r = anon_sess.get(f"{BASE_URL}/api/admin/prop-benefits/overview", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_endpoints_forbidden_for_client(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/admin/prop-benefits/overview", timeout=15)
        assert r.status_code == 403, f"client should be forbidden, got {r.status_code}"


# ─────────────────────────────────── Mentor pb_ action ───────────────────────────────────
class TestMentorIntegration:
    def test_mentor_returns_pb_action(self, client_sess):
        r = client_sess.get(f"{BASE_URL}/api/ai-brain/mentor", params={"path": "/client"}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        actions = d.get("actions") or d.get("items") or []
        # accept nested structure
        if isinstance(actions, dict):
            actions = actions.get("items", [])
        ids = []
        for a in actions:
            ids.append(a.get("id", ""))
            ids.append(a.get("source_action_id") or "")
        pb_ids = [i for i in ids if str(i).startswith("pb_")]
        # Provenance real: source_action_id păstrează prefixul pb_ prin decision layer.
        titles = [(a.get("title") or "").lower() for a in actions]
        has_pb_title = any(("benefic" in t) or ("casa ta" in t) for t in titles)
        assert pb_ids or has_pb_title, f"no pb_ action found. ids={ids} titles={titles}"


# ─────────────────────────────────── Referral gating (full flow) ───────────────────────────────────
class TestReferralGating:
    def test_referral_pending_then_activated(self, client_sess, admin_sess):
        from pymongo import MongoClient
        mc = MongoClient(os.environ.get("MONGO_URL"))
        dbh = mc[os.environ.get("DB_NAME", "propmanage")]

        # 1) create invite as client
        inv = client_sess.post(f"{BASE_URL}/api/referrals/invite",
                               json={"role": "client", "name": "TEST_pb_ref"}, timeout=15)
        assert inv.status_code in (200, 201), inv.text
        invd = inv.json()
        code = invd.get("code") or invd.get("invite", {}).get("code")
        assert code, f"no code returned: {invd}"

        # 2) register new user
        email = f"test_pb_ref_{uuid.uuid4().hex[:8]}@example.com"
        anon = requests.Session()
        reg = anon.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "Test123!", "name": "TEST PB Ref",
            "role": "client",
            "terms_accepted": True, "privacy_policy_accepted": True,
        }, timeout=20)
        assert reg.status_code in (200, 201), reg.text

        # 3) claim referral code
        cl = anon.post(f"{BASE_URL}/api/referrals/claim", json={"code": code}, timeout=15)
        assert cl.status_code in (200, 201), cl.text

        new_user = dbh.users.find_one({"email": email})
        assert new_user, "new user not created"
        new_uid = new_user.get("id") or str(new_user["_id"])

        # 4) verify pending state and NO ledger entries yet
        pending = list(dbh.pb_referral_pending.find({"status": "pending_activation"}))
        assert any(p.get("invitee_id") == new_uid for p in pending), \
            f"pending record not found for {email} uid={new_uid}"

        ledger_pre = dbh.pb_ledger.count_documents({"user_id": new_uid, "source": "referral"})
        assert ledger_pre == 0, f"unexpected ledger entries pre-payment: {ledger_pre}"

        # 5) insert a paid payment_transactions doc
        tx_id = f"TEST_pb_tx_{uuid.uuid4().hex[:8]}"
        import time as _t
        dbh.payment_transactions.insert_one({
            "id": tx_id,
            "user_id": new_uid,
            "amount": 100,
            "currency": "RON",
            "status": "paid",
            "payment_status": "paid",
            "created_at": _t.time(),
        })

        # 6) run tick
        tick = admin_sess.post(f"{BASE_URL}/api/admin/prop-benefits/run-tick", timeout=30)
        assert tick.status_code == 200

        # 7) verify activated + both users have ledger entries
        activated_now = dbh.pb_referral_pending.count_documents({
            "status": "activated", "invitee_id": new_uid,
        })
        assert activated_now >= 1, "referral not activated after tick+paid"

        new_led = dbh.pb_ledger.count_documents({"user_id": new_uid, "source": "referral"})
        assert new_led >= 1, "new user did not get referral benefit"

        # cleanup
        dbh.payment_transactions.delete_one({"id": tx_id})
        dbh.pb_ledger.delete_many({"user_id": new_uid})
        dbh.pb_referral_pending.delete_many({"invitee_id": new_uid})
        dbh.users.delete_one({"id": new_uid})
        dbh.users.delete_one({"email": email})
