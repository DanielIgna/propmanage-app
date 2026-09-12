"""Iteration 63 — Tests for welcome voucher → community welcome post feature.

Covers:
1. Specialist registration auto-creates a forum welcome topic with badge=MEMBER_OF_THE_WEEK,
   tags containing 'welcome_post', badge_expires_at ~7 days ahead.
2. Client registration also auto-creates a welcome topic (auth.py line ~187 runs for all roles).
3. Idempotency: duplicate registration → 400/409 error; only ONE welcome topic per author.
4. No regression on existing community endpoints (topics, stats, like, reply).
"""
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "https://phased-document.preview.emergentagent.com"


def _ts():
    return int(time.time() * 1000)


@pytest.fixture
def api_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _register_specialist(api, email=None, name="Test Specialist Iter63"):
    email = email or f"wv-test-{_ts()}-{uuid.uuid4().hex[:6]}@propmanage.io"
    payload = {
        "email": email,
        "password": "Test123!",
        "terms_accepted": True, "privacy_policy_accepted": True,
        "name": name,
        "role": "specialist",
        "phone": "+40712345678",
        "service_categories": ["hvac"],
        "coverage_zones": ["Bucuresti"],
        "marketing_consent": False,
    }
    r = api.post(f"{BASE_URL}/api/auth/register", json=payload)
    return r, email, name


def _register_client(api, email=None, name="Test Client Iter63"):
    email = email or f"tour-test-{_ts()}-{uuid.uuid4().hex[:6]}@propmanage.io"
    payload = {
        "email": email,
        "password": "Test123!",
        "terms_accepted": True, "privacy_policy_accepted": True,
        "name": name,
        "role": "client",
        "phone": "+40712345678",
        "zone": "Bucuresti",
        "marketing_consent": False,
    }
    r = api.post(f"{BASE_URL}/api/auth/register", json=payload)
    return r, email, name


def _find_welcome_topic_by_author(api, author_name):
    """Search forum topics for one whose author_name matches and tags contain welcome_post."""
    r = api.get(f"{BASE_URL}/api/community/topics", params={"category": "forum"})
    assert r.status_code == 200, f"topics list failed: {r.status_code} {r.text[:200]}"
    items = r.json()
    # API may return list or dict-with-items
    if isinstance(items, dict):
        items = items.get("items") or items.get("topics") or []
    matches = [
        t for t in items
        if (t.get("author_name") == author_name) and ("welcome_post" in (t.get("tags") or []))
    ]
    return matches, items


# ============ TEST: specialist registration → welcome topic ============
class TestSpecialistWelcomeTopic:
    def test_specialist_register_creates_welcome_topic(self, api_client):
        r, email, name = _register_specialist(api_client)
        assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:300]}"
        # Allow brief async tasks to settle
        time.sleep(1.0)
        matches, _all = _find_welcome_topic_by_author(api_client, name)
        assert len(matches) >= 1, f"No welcome topic found for specialist {name}. Total forum topics={len(_all)}"
        topic = matches[0]
        # Title check (loose — starts with 'Salutare')
        assert topic.get("title", "").startswith("Salutare, sunt"), f"unexpected title: {topic.get('title')}"
        # Badge fields
        assert topic.get("badge") == "MEMBER_OF_THE_WEEK", f"badge missing/wrong: {topic.get('badge')}"
        assert "welcome_post" in (topic.get("tags") or [])
        # Expiry ~7 days ahead
        exp = topic.get("badge_expires_at")
        assert exp, "badge_expires_at missing"
        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = exp_dt - now
        assert timedelta(days=6) < delta < timedelta(days=8), f"expiry not ~7d: {delta}"
        # Category must be forum
        assert topic.get("category") == "forum"

    def test_idempotency_duplicate_email_fails(self, api_client):
        unique_name = f"Iter63 Idem {_ts()}"
        r1, email, name = _register_specialist(api_client, name=unique_name)
        assert r1.status_code in (200, 201)
        time.sleep(0.5)
        # re-register same email
        payload = {
            "email": email,
            "password": "Test123!",
            "terms_accepted": True, "privacy_policy_accepted": True,
            "name": name,
            "role": "specialist",
            "phone": "+40712345678",
            "service_categories": ["hvac"],
        }
        r2 = api_client.post(f"{BASE_URL}/api/auth/register", json=payload)
        assert r2.status_code in (400, 409), f"duplicate should fail, got {r2.status_code}"
        # Only ONE welcome topic for that author_name
        time.sleep(0.5)
        matches, _ = _find_welcome_topic_by_author(api_client, name)
        assert len(matches) == 1, f"expected exactly 1 welcome topic, got {len(matches)}"


# ============ TEST: client registration → also creates welcome topic ============
class TestClientWelcomeTopic:
    def test_client_register_creates_welcome_topic(self, api_client):
        r, email, name = _register_client(api_client)
        assert r.status_code in (200, 201), f"client register failed: {r.status_code} {r.text[:300]}"
        time.sleep(1.0)
        matches, _ = _find_welcome_topic_by_author(api_client, name)
        assert len(matches) >= 1, f"No welcome topic found for client {name}"
        topic = matches[0]
        assert topic.get("badge") == "MEMBER_OF_THE_WEEK"
        assert "welcome_post" in (topic.get("tags") or [])
        assert topic.get("author_role") == "client"


# ============ TEST: no regression on community endpoints ============
class TestCommunityRegression:
    def test_stats_endpoint(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/community/stats")
        assert r.status_code == 200
        d = r.json()
        assert "topics_per_category" in d
        assert "total_topics" in d
        assert isinstance(d["total_topics"], int)

    def test_topics_list_forum(self, api_client):
        r = api_client.get(f"{BASE_URL}/api/community/topics", params={"category": "forum"})
        assert r.status_code == 200
        items = r.json()
        if isinstance(items, dict):
            items = items.get("items") or items.get("topics") or []
        assert isinstance(items, list)

    def test_client_login_create_reply_like_flow(self, api_client):
        # Login as existing demo client
        r = api_client.post(f"{BASE_URL}/api/auth/login",
                            json={"email": "client@propmanage.io", "password": "Client123!"})
        assert r.status_code == 200, f"login failed: {r.text[:200]}"
        token = r.json().get("access_token") or r.json().get("token")
        if token:
            api_client.headers.update({"Authorization": f"Bearer {token}"})
        # Create topic
        title = f"TEST_iter63_regression_{_ts()}"
        body = "TEST_iter63 regression body — should not error after welcome-topic feature."
        r = api_client.post(f"{BASE_URL}/api/community/topics",
                            json={"category": "forum", "title": title, "body": body})
        assert r.status_code in (200, 201), f"create topic failed: {r.status_code} {r.text[:300]}"
        topic = r.json()
        topic_id = topic.get("id") or topic.get("_id")
        assert topic_id, "no topic id returned"
        # Reply
        r2 = api_client.post(f"{BASE_URL}/api/community/topics/{topic_id}/replies",
                             json={"body": "TEST_iter63 reply"})
        assert r2.status_code in (200, 201), f"reply failed: {r2.status_code} {r2.text[:200]}"
        # Like (POST /likes/toggle with target_type=topic)
        r3 = api_client.post(f"{BASE_URL}/api/community/likes/toggle",
                             json={"target_type": "topic", "target_id": topic_id})
        assert r3.status_code in (200, 201), f"like failed: {r3.status_code} {r3.text[:200]}"
