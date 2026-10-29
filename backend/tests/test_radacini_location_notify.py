"""Rădăcini — proprietarul e anunțat când altcineva vede locația exactă (DPIA R1), cel mult o dată pe zi
pentru aceeași persoană și același teren. Fără backend și fără bază: jurnalul și notificările sunt simulate.

    ./venv/bin/python -m pytest tests/test_radacini_location_notify.py -q --noconftest
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from routes.radacini import parcels


class FakeLog:
    def __init__(self):
        self.rows = []

    async def find_one(self, flt, proj=None):
        for r in self.rows:
            if r["parcel_id"] == flt["parcel_id"] and r["user_id"] == flt["user_id"] and r["at"] >= flt["at"]["$gte"]:
                return r
        return None

    async def insert_one(self, doc):
        self.rows.append(dict(doc))


class FakeDb:
    def __init__(self):
        self.radacini_location_access_log = FakeLog()


@pytest.fixture
def env(monkeypatch):
    db, sent = FakeDb(), []

    async def notify(user_id, title, message, link=None, type_="info"):
        sent.append({"user_id": user_id, "title": title, "message": message, "link": link})

    monkeypatch.setattr(parcels, "db", db)
    monkeypatch.setattr(parcels, "safe_notify", notify)
    return db, sent


PARCEL = {"_id": "p1", "owner_user_id": "owner", "title": "TEST-RAD-teren"}


def run(coro):
    return asyncio.run(coro)


def test_first_access_of_day_notifies_owner(env):
    db, sent = env
    assert run(parcels._log_location_access(PARCEL, "cult", "ag1", "cultivator")) is True
    assert len(sent) == 1 and sent[0]["user_id"] == "owner"
    assert sent[0]["link"] == "/radacini/terenuri/p1"
    assert "Cultivatorul" in sent[0]["message"] and "cult" not in sent[0]["message"].split()
    # a doua citire în aceeași zi: jurnalizată, fără notificare nouă
    assert run(parcels._log_location_access(PARCEL, "cult", "ag1", "cultivator")) is True
    assert len(db.radacini_location_access_log.rows) == 2 and len(sent) == 1


def test_other_person_or_parcel_notifies_again(env):
    _, sent = env
    run(parcels._log_location_access(PARCEL, "cult", "ag1", "cultivator"))
    run(parcels._log_location_access(PARCEL, "staff1", None, "staff"))
    run(parcels._log_location_access({**PARCEL, "_id": "p2"}, "cult", "ag2", "cultivator"))
    assert len(sent) == 3
    assert "Personalul" in sent[1]["message"]


def test_access_from_yesterday_does_not_suppress(env):
    db, sent = env
    yesterday = (datetime.fromisoformat(parcels._bucharest_day_start_iso()) - timedelta(minutes=1)).isoformat()
    db.radacini_location_access_log.rows.append({"parcel_id": "p1", "user_id": "cult", "at": yesterday})
    run(parcels._log_location_access(PARCEL, "cult", "ag1", "cultivator"))
    assert len(sent) == 1


def test_owner_never_notified_about_self(env):
    _, sent = env
    run(parcels._log_location_access(PARCEL, "owner", None, "staff"))
    assert sent == []


def test_log_failure_means_no_notification(env, monkeypatch):
    db, sent = env

    async def boom(doc):
        raise RuntimeError("db down")

    monkeypatch.setattr(db.radacini_location_access_log, "insert_one", boom)
    assert run(parcels._log_location_access(PARCEL, "cult", "ag1", "cultivator")) is False
    assert sent == []


def test_day_start_is_utc_iso():
    start = datetime.fromisoformat(parcels._bucharest_day_start_iso())
    assert start.tzinfo is not None and start.utcoffset() == timedelta(0)
    assert datetime.now(timezone.utc) - start < timedelta(days=1)
