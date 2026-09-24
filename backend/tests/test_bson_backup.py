"""Native BSON backup export. Reads the archive on disk, not only HTTP status."""
import asyncio
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import bson
import pytest
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import backup_service
from backup_service import (
    BSON_DUMP_PREFIX,
    BSON_DUMP_RETENTION,
    BSON_RUN_FORMAT,
    LOCAL_RETENTION,
    _prune_bson_dumps,
    _prune_old_backups,
    create_backup,
    create_bson_dump,
    json_backup_run_filter,
    latest_backup_status,
    list_bson_dumps,
)
from db import client
from deps import get_current_user
from routes.admin_backups import download_backup, router


def _detach_motor_loop(loop):
    from db import client as motor_client

    cached = getattr(motor_client, "_io_loop", None)
    if cached is loop or (cached is not None and cached.is_closed()):
        motor_client._io_loop = None


@pytest.fixture(scope="module")
def eloop():
    loop = asyncio.new_event_loop()
    _detach_motor_loop(loop)
    yield loop
    _detach_motor_loop(loop)
    if not loop.is_closed():
        loop.close()


def _run(eloop, coro):
    return eloop.run_until_complete(coro)


@pytest.fixture
def backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_service, "BACKUP_DIR", tmp_path)
    import routes.admin_backups as routes_mod
    monkeypatch.setattr(routes_mod, "BACKUP_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def tiny_db(eloop, monkeypatch):
    name = f"bson_backup_test_{ObjectId()}"
    database = client[name]
    monkeypatch.setattr(backup_service, "db", database)

    def _drop():
        eloop.run_until_complete(client.drop_database(name))

    yield database
    _drop()


def _members(path):
    with tarfile.open(path, "r:gz") as tar:
        return tar.getnames()


def _extract_bson(path, suffix):
    with tarfile.open(path, "r:gz") as tar:
        name = next(n for n in tar.getnames() if n.endswith(suffix))
        return bson.decode_all(tar.extractfile(name).read()), name


def test_bson_archive_preserves_object_id_and_datetime(eloop, backup_dir, tiny_db):
    async def _case():
        oid = ObjectId()
        when = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
        await tiny_db.probe.insert_one({"_id": oid, "when": when, "label": "kept"})
        await tiny_db.probe.create_index("label", unique=True)
        result = await create_bson_dump()
        assert result["ok"] is True
        assert result["filename"].startswith(BSON_DUMP_PREFIX)
        assert result["filename"].endswith(".tar.gz")
        assert result["format"] == BSON_RUN_FORMAT
        archive = backup_dir / result["filename"]
        assert archive.is_file()
        names = _members(archive)
        db_name = tiny_db.name
        assert f"dump/{db_name}/probe.bson" in names
        assert f"dump/{db_name}/probe.metadata.json" in names
        docs, _ = _extract_bson(archive, "/probe.bson")
        assert docs[0]["_id"] == oid
        assert isinstance(docs[0]["_id"], ObjectId)
        stored = docs[0]["when"]
        assert isinstance(stored, datetime)
        assert stored.replace(tzinfo=timezone.utc) == when
        assert docs[0]["label"] == "kept"
        meta_name = f"dump/{db_name}/probe.metadata.json"
        with tarfile.open(archive, "r:gz") as tar:
            raw = tar.extractfile(meta_name).read()
        import json
        meta = json.loads(raw)
        assert meta["uuid"] == ""
        assert any(idx.get("name") == "label_1" and idx.get("unique") is True for idx in meta["indexes"])
        saved = await tiny_db.backup_runs.find_one({"_id": result["filename"]})
        assert saved["format"] == BSON_RUN_FORMAT
        assert list_bson_dumps()[0]["filename"] == result["filename"]

    _run(eloop, _case())


def test_retention_keeps_json_and_bson_apart(backup_dir):
    def _touch(name, mtime):
        path = backup_dir / name
        path.write_bytes(b"x")
        os.utime(path, (mtime, mtime))

    for i in range(LOCAL_RETENTION + 1):
        _touch(f"propmanage-backup-2020-01-{i:02d}.tar.gz", 1_700_000_000 + i)
    for i in range(BSON_DUMP_RETENTION + 1):
        _touch(f"{BSON_DUMP_PREFIX}2020-02-{i:02d}.tar.gz", 1_700_100_000 + i)

    _prune_bson_dumps()
    json_left = list(backup_dir.glob("propmanage-backup-*.tar.gz"))
    bson_left = list(backup_dir.glob(f"{BSON_DUMP_PREFIX}*.tar.gz"))
    assert len(json_left) == LOCAL_RETENTION + 1
    assert len(bson_left) == BSON_DUMP_RETENTION

    _prune_old_backups()
    json_left = list(backup_dir.glob("propmanage-backup-*.tar.gz"))
    bson_left = list(backup_dir.glob(f"{BSON_DUMP_PREFIX}*.tar.gz"))
    assert len(json_left) == LOCAL_RETENTION
    assert len(bson_left) == BSON_DUMP_RETENTION


def test_bson_run_does_not_replace_latest_json_status(eloop, tiny_db):
    async def _case():
        await tiny_db.backup_runs.insert_one({
            "_id": "propmanage-backup-old.tar.gz",
            "ok": True,
            "started_at": "2024-01-01T00:00:00+00:00",
            "filename": "propmanage-backup-old.tar.gz",
            "collections_count": 2,
            "size_mb": 1.0,
        })
        await tiny_db.backup_runs.insert_one({
            "_id": "propmanage-bson-dump-new.tar.gz",
            "ok": True,
            "started_at": "2024-06-01T00:00:00+00:00",
            "filename": "propmanage-bson-dump-new.tar.gz",
            "format": BSON_RUN_FORMAT,
            "collections_count": 9,
            "size_mb": 3.0,
        })
        latest = await latest_backup_status()
        assert latest["filename"] == "propmanage-backup-old.tar.gz"
        assert latest.get("format") != BSON_RUN_FORMAT
        visible = await tiny_db.backup_runs.find_one(json_backup_run_filter(), sort=[("started_at", -1)])
        assert visible["_id"] == "propmanage-backup-old.tar.gz"

    _run(eloop, _case())


def test_json_backup_still_writes_json_archive(eloop, backup_dir, tiny_db):
    async def _case():
        await tiny_db.notes.insert_one({"title": "json-path"})
        result = await create_backup()
        assert result["ok"] is True
        assert result["filename"].startswith("propmanage-backup-")
        names = _members(backup_dir / result["filename"])
        assert "collections/notes.json" in names
        assert "MANIFEST.json" in names
        latest = await latest_backup_status()
        assert latest["filename"] == result["filename"]

    _run(eloop, _case())


def test_failed_dump_leaves_no_listable_archive(eloop, backup_dir, tiny_db, monkeypatch):
    async def _case():
        await tiny_db.probe.insert_one({"_id": ObjectId(), "n": 1})
        held = {}

        def _mkdtemp(prefix=""):
            path = backup_dir / "tmp-hold"
            path.mkdir()
            held["path"] = path
            return str(path)

        def _boom(_doc):
            raise RuntimeError("encode failed")

        monkeypatch.setattr(backup_service.tempfile, "mkdtemp", _mkdtemp)
        monkeypatch.setattr(backup_service.bson, "encode", _boom)
        result = await create_bson_dump()
        assert result["ok"] is False
        assert "encode failed" in result["error"]
        assert list(backup_dir.glob(f"{BSON_DUMP_PREFIX}*.tar.gz")) == []
        assert list(backup_dir.glob("*.partial")) == []
        assert not held["path"].exists()
        assert await tiny_db.backup_runs.count_documents({"format": BSON_RUN_FORMAT}) == 0

    _run(eloop, _case())


def test_concurrent_dumps_do_not_corrupt(eloop, backup_dir, tiny_db):
    async def _case():
        await tiny_db.probe.insert_one({"_id": ObjectId(), "n": 1})
        first, second = await asyncio.gather(create_bson_dump(), create_bson_dump())
        assert first["ok"] is True
        assert second["ok"] is True
        assert first["filename"] != second["filename"]
        archives = list(backup_dir.glob(f"{BSON_DUMP_PREFIX}*.tar.gz"))
        assert len(archives) == 2
        assert list(backup_dir.glob("*.partial")) == []
        for archive in archives:
            docs, _ = _extract_bson(archive, "/probe.bson")
            assert docs[0]["n"] == 1

    _run(eloop, _case())


def _client(role):
    app = FastAPI()
    app.include_router(router)

    async def _user():
        return {"id": "u1", "role": role, "email": f"{role}@example.com"}

    app.dependency_overrides[get_current_user] = _user
    return TestClient(app)


def test_download_auth_and_filename_guards(backup_dir):
    (backup_dir / "propmanage-backup-ok.tar.gz").write_bytes(b"json-archive")
    (backup_dir / f"{BSON_DUMP_PREFIX}ok.tar.gz").write_bytes(b"bson-archive")

    admin = _client("admin")
    client = _client("client")

    assert client.post("/api/admin/backups/dump-bson").status_code == 403
    assert client.get(f"/api/admin/backups/download/{BSON_DUMP_PREFIX}ok.tar.gz").status_code == 403
    assert client.get("/api/admin/backups/download/propmanage-backup-ok.tar.gz").status_code == 403

    bson_resp = admin.get(f"/api/admin/backups/download/{BSON_DUMP_PREFIX}ok.tar.gz")
    json_resp = admin.get("/api/admin/backups/download/propmanage-backup-ok.tar.gz")
    assert bson_resp.status_code == 200
    assert bson_resp.content == b"bson-archive"
    assert json_resp.status_code == 200
    assert json_resp.content == b"json-archive"

    assert admin.get("/api/admin/backups/download/other-prefix.tar.gz").status_code == 400
    admin_user = {"id": "u1", "role": "admin", "email": "admin@example.com"}

    async def _reject(name):
        with pytest.raises(HTTPException) as exc:
            await download_backup(name, admin_user)
        assert exc.value.status_code == 400

    asyncio.run(_reject("../secret.tar.gz"))
    asyncio.run(_reject("propmanage-backup-../x.tar.gz"))
    asyncio.run(_reject("propmanage-backup-a/b.tar.gz"))
    asyncio.run(_reject(f"{BSON_DUMP_PREFIX}../x.tar.gz"))


def test_mongorestore_round_trip_when_available(eloop, backup_dir, tiny_db):
    import shutil
    if shutil.which("mongorestore") is None or shutil.which("mongodump") is None:
        pytest.skip("mongorestore is not installed in this environment")

    async def _case():
        oid = ObjectId()
        when = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        await tiny_db.probe.insert_one({"_id": oid, "when": when, "n": 7})
        result = await create_bson_dump()
        assert result["ok"] is True
        extract = backup_dir / "restored-src"
        extract.mkdir()
        with tarfile.open(backup_dir / result["filename"], "r:gz") as tar:
            tar.extractall(extract, filter="data")
        await tiny_db.probe.drop()
        return extract

    extract = _run(eloop, _case())
    uri = os.environ.get("MONGO_URL")
    assert uri
    import subprocess
    proc = subprocess.run(
        ["mongorestore", f"--uri={uri}", "--drop", str(extract / "dump")],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-500:]

    async def _check():
        doc = await tiny_db.probe.find_one({"n": 7})
        assert doc is not None
        assert isinstance(doc["_id"], ObjectId)
        assert doc["when"].year == 2024

    _run(eloop, _check())
