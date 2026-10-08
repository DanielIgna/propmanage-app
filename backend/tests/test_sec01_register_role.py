"""SEC-01: public registration may create only client or specialist.

Schema checks import models only. Handler checks import the auth route inside
the test body so collecting this file does not open a database client.
"""
import asyncio
from typing import get_args

import pytest
from pydantic import ValidationError

from models import PUBLIC_REGISTER_ROLES, PublicRegisterRole, RegisterIn, Role

_BASE = {
    "email": "sec01@example.com",
    "password": "secret1",
    "name": "SEC01 User",
    "terms_accepted": True,
    "privacy_policy_accepted": True,
}

_PRIVILEGED = (
    "admin",
    "operator",
    "franchise_admin",
    "marketing_manager",
    "super_admin",
)


def test_shared_role_literal_still_includes_controlled_roles():
    assert set(get_args(Role)) == {"client", "specialist", "admin", "operator"}
    assert set(get_args(PublicRegisterRole)) == {"client", "specialist"}
    assert PUBLIC_REGISTER_ROLES == frozenset({"client", "specialist"})


def test_omitted_role_defaults_to_client():
    assert RegisterIn(**_BASE).role == "client"


def test_public_register_accepts_client_and_specialist():
    assert RegisterIn(**_BASE, role="client").role == "client"
    specialist = RegisterIn(
        **_BASE,
        role="specialist",
        phone="+40722111222",
        specialty="hvac",
        service_categories=["hvac"],
    )
    assert specialist.role == "specialist"
    assert specialist.phone == "+40722111222"
    assert specialist.service_categories == ["hvac"]


@pytest.mark.parametrize("role", _PRIVILEGED)
def test_public_register_schema_rejects_privileged_roles(role):
    with pytest.raises(ValidationError):
        RegisterIn(**_BASE, role=role)


class _BoomDB:
    def __getattr__(self, name):
        raise AssertionError(f"database accessed via {name}")


class _Client:
    host = "203.0.113.10"


class _Request:
    client = _Client()
    headers = {"user-agent": "sec01-test"}


class _Inserted:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _Users:
    def __init__(self):
        self.docs = []

    async def find_one(self, query):
        return None

    async def insert_one(self, doc):
        self.docs.append(doc)
        return _Inserted("sec01-user")


class _Consent:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(doc)
        return None


class _DB:
    def __init__(self):
        self.users = _Users()
        self.consent_audit_log = _Consent()


def _auth():
    import routes.auth as auth
    return auth


@pytest.mark.parametrize("role", _PRIVILEGED)
def test_register_rejects_privileged_role_before_database_access(role, monkeypatch):
    auth = _auth()
    monkeypatch.setattr(auth, "db", _BoomDB())
    data = RegisterIn.model_construct(
        email="sec01@example.com",
        password="secret1",
        name="SEC01 User",
        role=role,
        terms_accepted=True,
        privacy_policy_accepted=True,
    )

    async def _call():
        with pytest.raises(auth.HTTPException) as exc:
            await auth.register(data, None, None)
        return exc.value

    error = asyncio.run(_call())
    assert error.status_code == 400


def test_register_persists_only_client_or_specialist(monkeypatch):
    auth = _auth()
    fake = _DB()
    monkeypatch.setattr(auth, "db", fake)

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(auth, "send_template", _noop)
    import docs_service
    import onboarding_emails
    import routes.community as community
    import routes.marketplace_offers as offers
    monkeypatch.setattr(community, "auto_create_welcome_topic", _noop)
    monkeypatch.setattr(offers, "issue_welcome_voucher_for_specialist", _noop)
    monkeypatch.setattr(onboarding_emails, "enqueue_specialist_onboarding", _noop)
    monkeypatch.setattr(docs_service, "email_doc_to_user", _noop)

    from starlette.responses import Response

    async def _register(payload):
        return await auth.register(RegisterIn(**payload), _Request(), Response())

    client = asyncio.run(_register({
        **_BASE,
        "email": "sec01-client@example.com",
        "role": "client",
        "zone": "Bucuresti-Sector1",
    }))
    specialist = asyncio.run(_register({
        **_BASE,
        "email": "sec01-spec@example.com",
        "role": "specialist",
        "phone": "+40722111222",
        "specialty": "hvac",
        "service_categories": ["hvac"],
        "coverage_zones": ["Bucuresti-Sector1"],
    }))

    assert client["role"] == "client"
    assert client["zone"] == "Bucuresti-Sector1"
    assert "password_hash" not in client
    assert specialist["role"] == "specialist"
    assert specialist["service_categories"] == ["hvac"]
    assert specialist["lead_credits"] == 135
    assert [doc["role"] for doc in fake.users.docs] == ["client", "specialist"]
    assert fake.users.docs[0]["lead_credits"] == 0
    assert fake.users.docs[1]["specialty"] == "hvac"
    assert fake.users.docs[1]["tier"] == "ENTRY"


def test_specialist_phone_and_category_still_required_before_insert(monkeypatch):
    auth = _auth()
    fake = _DB()
    monkeypatch.setattr(auth, "db", fake)

    async def _reject(payload):
        with pytest.raises(auth.HTTPException) as exc:
            await auth.register(RegisterIn(**payload), _Request(), None)
        return exc.value.status_code

    missing_phone = asyncio.run(_reject({
        **_BASE,
        "email": "sec01-nophone@example.com",
        "role": "specialist",
        "service_categories": ["hvac"],
    }))
    missing_category = asyncio.run(_reject({
        **_BASE,
        "email": "sec01-nocat@example.com",
        "role": "specialist",
        "phone": "+40722111222",
    }))
    assert missing_phone == 400
    assert missing_category == 400
    assert fake.users.docs == []
