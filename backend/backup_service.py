"""PropManage — MongoDB automatic backup service.

Strategy:
  1. Every day at 03:30 Europe/Bucharest, dump all collections to JSON.
  2. Compress to .tar.gz (uses bson.json_util to handle ObjectId/datetime).
  3. Email the archive to ADMIN_EMAILS as attachment (Resend supports ~20MB).
  4. Keep last 7 backups locally in /app/backups/ for fast admin download.
  5. Admin endpoints: list, manual run, download single backup.

The whole thing runs in a thread (compression can be slow) so it doesn't
block the FastAPI event loop.
"""
from __future__ import annotations

import os
import io
import base64
import json
import logging
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import json_util

from db import db

logger = logging.getLogger("propmanage.backup")

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "/app/backups"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Keep last N backups locally (older ones are auto-deleted to save disk)
LOCAL_RETENTION = 7

# Resend attachment safe limit (~20MB hard limit; we cap at 15MB to be safe).
EMAIL_MAX_ATTACHMENT_MB = 15

# Collections we DON'T back up (transient runtime data — no value to restore)
EXCLUDED_COLLECTIONS = {
    "smoke_test_runs",
    "data_integrity_runs",
    "health_pings",
    "rate_limit_attempts",
    # session-like data
}


# ---------------------------------------------------------------------------
# Core backup function
# ---------------------------------------------------------------------------

async def _dump_collection(col_name: str) -> bytes:
    """Dump one collection to BSON-aware JSON bytes."""
    cursor = db[col_name].find({})
    docs = []
    async for d in cursor:
        docs.append(d)
    # json_util handles ObjectId, datetime, Decimal128, etc.
    return json_util.dumps(docs, indent=None).encode("utf-8")


async def create_backup() -> dict:
    """Create a tar.gz backup containing all non-excluded collections.

    Returns: {
        "ok": bool, "filename": str, "path": str, "size_mb": float,
        "collections_count": int, "objects_count": int, "duration_s": float,
        "error": Optional[str]
    }
    """
    started = datetime.now(timezone.utc)
    timestamp = started.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"propmanage-backup-{timestamp}.tar.gz"
    filepath = BACKUP_DIR / filename

    try:
        collections = await db.list_collection_names()
        included = [c for c in collections if c not in EXCLUDED_COLLECTIONS]

        # Build the archive in-memory then write once (avoids partial files).
        buf = io.BytesIO()
        objects_count = 0
        with tarfile.open(fileobj=buf, mode="w:gz", compresslevel=6) as tar:
            # Manifest
            manifest = {
                "created_at": started.isoformat(),
                "db_name": db.name,
                "collections_included": included,
                "collections_excluded": list(EXCLUDED_COLLECTIONS & set(collections)),
                "format": "json (bson-aware via json_util)",
                "restore_hint": "Use bson.json_util.loads on each .json file then insert_many.",
            }
            manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
            mi = tarfile.TarInfo(name="MANIFEST.json")
            mi.size = len(manifest_bytes)
            mi.mtime = int(started.timestamp())
            tar.addfile(mi, io.BytesIO(manifest_bytes))

            # One .json file per collection
            for col in included:
                data = await _dump_collection(col)
                # Count objects (cheap parse just for the count)
                try:
                    objects_count += data.count(b"},{") + (1 if data and data != b"[]" else 0)
                except Exception:  # noqa: BLE001
                    pass
                ti = tarfile.TarInfo(name=f"collections/{col}.json")
                ti.size = len(data)
                ti.mtime = int(started.timestamp())
                tar.addfile(ti, io.BytesIO(data))

        # Write the archive to disk
        buf.seek(0)
        filepath.write_bytes(buf.getvalue())
        size_mb = filepath.stat().st_size / 1024 / 1024

        # Clean up old backups (retention)
        _prune_old_backups()

        duration = (datetime.now(timezone.utc) - started).total_seconds()
        result = {
            "ok": True,
            "filename": filename,
            "path": str(filepath),
            "size_mb": round(size_mb, 2),
            "collections_count": len(included),
            "objects_count": objects_count,
            "duration_s": round(duration, 2),
            "started_at": started.isoformat(),
        }

        # Persist run record for Briefing card / admin UI
        try:
            await db.backup_runs.insert_one({**result, "_id": filename, "delivered_email": False})
        except Exception:  # noqa: BLE001
            pass

        logger.info(f"[Backup] created {filename} · {size_mb:.2f} MB · {len(included)} cols in {duration:.1f}s")
        return result

    except Exception as e:  # noqa: BLE001
        logger.error(f"[Backup] failed: {e}", exc_info=True)
        return {"ok": False, "error": str(e), "started_at": started.isoformat()}


def _prune_old_backups():
    """Delete all .tar.gz files in BACKUP_DIR except the LOCAL_RETENTION newest."""
    try:
        files = sorted(BACKUP_DIR.glob("propmanage-backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[LOCAL_RETENTION:]:
            try:
                old.unlink()
                logger.info(f"[Backup] pruned old file: {old.name}")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[Backup] prune failed for {old.name}: {e}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Backup] prune scan failed: {e}")


def list_local_backups() -> list[dict]:
    """List current local backup files (newest first)."""
    try:
        files = sorted(BACKUP_DIR.glob("propmanage-backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        return [
            {
                "filename": f.name,
                "size_mb": round(f.stat().st_size / 1024 / 1024, 2),
                "created_at": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            }
            for f in files
        ]
    except Exception as e:  # noqa: BLE001
        logger.error(f"[Backup] list failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

async def email_backup(filepath: str, size_mb: float, meta: dict) -> dict:
    """Email the backup archive to ADMIN_EMAILS. Skips if too large."""
    from email_service import _layout  # lazy import

    recipients_raw = os.environ.get("ADMIN_EMAILS", "") or os.environ.get("ADMIN_EMAIL", "")
    recipients = [e.strip() for e in recipients_raw.split(",") if e.strip()]
    if not recipients:
        return {"sent": False, "reason": "no_recipients"}

    fp = Path(filepath)
    if not fp.exists():
        return {"sent": False, "reason": "file_missing"}

    if size_mb > EMAIL_MAX_ATTACHMENT_MB:
        # Send a notification WITHOUT attachment but with link to admin panel
        app_url = os.environ.get("APP_PUBLIC_URL", "https://propmanage.ro")
        html = _layout(
            title="Backup zilnic creat (prea mare pentru email)",
            preheader=f"{size_mb:.1f} MB — descarcă manual",
            body_html=f"""
              <p>Backup-ul zilnic <strong>{fp.name}</strong> a fost creat cu succes
              ({size_mb:.1f} MB, {meta.get('collections_count')} colecții, {meta.get('objects_count')} obiecte).</p>
              <p>Fișierul depășește limita de {EMAIL_MAX_ATTACHMENT_MB} MB pentru atașamente email.
              Îl poți descărca din panoul de administrare:</p>
              <p>
                <a href="{app_url}/admin?tab=backups" style="display:inline-block; padding:12px 22px; background:#d4ff3a; color:#0a0a0b; text-decoration:none; border-radius:999px; font-weight:700;">
                  Deschide Admin → Backups
                </a>
              </p>
            """,
            cta_url=f"{app_url}/admin",
            cta_label="Vezi Admin",
        )
        from email_service import send_email
        sent = 0
        for r in recipients:
            res = await send_email(r, f"PropManage Backup {fp.name} ({size_mb:.1f} MB)", html)
            if res.get("ok"):
                sent += 1
        return {"sent": sent > 0, "reason": "too_large_link_sent", "recipients": sent}

    # Read and base64-encode for Resend attachment format
    content_b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
    attachments = [{
        "filename": fp.name,
        "content": content_b64,
        "type": "application/gzip",
    }]

    today_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    html = _layout(
        title=f"Backup zilnic PropManage · {today_str}",
        preheader=f"{size_mb:.1f} MB · {meta.get('collections_count')} colecții",
        body_html=f"""
          <p>Bună dimineața,</p>
          <p>Backup-ul zilnic al bazei de date PropManage este atașat acestui email.</p>
          <table border="0" cellpadding="0" cellspacing="0" style="width:100%; background:#1a1a1f; border-radius:14px; padding:18px; margin:18px 0;">
            <tr><td style="font-size:11px; color:#888893; text-transform:uppercase; letter-spacing:0.5px; padding-bottom:4px;">Fișier</td></tr>
            <tr><td style="font-family:monospace; color:#d4ff3a; font-size:13px; padding-bottom:14px;">{fp.name}</td></tr>
            <tr><td style="font-size:11px; color:#888893; text-transform:uppercase; letter-spacing:0.5px; padding-bottom:4px;">Detalii</td></tr>
            <tr><td style="color:#e5e5e5; font-size:13px;">
              {size_mb:.2f} MB · {meta.get('collections_count')} colecții · {meta.get('objects_count')} obiecte
            </td></tr>
          </table>
          <p style="color:#a8a8b0; font-size:13px;">
            <strong>Cum restaurezi:</strong> dezarhivează cu <code>tar -xzf {fp.name}</code>.
            Vei obține un folder <code>collections/</code> cu un fișier <code>.json</code> per colecție
            și un <code>MANIFEST.json</code> cu metadata. Conține ObjectId-uri serializate cu
            <code>bson.json_util</code> — restaurarea se face cu un script Python care apelează
            <code>json_util.loads()</code> pe fiecare fișier.
          </p>
          <p style="color:#666; font-size:11px; margin-top:18px;">
            Acest email este trimis automat zilnic la 03:30 (Europe/Bucharest). Păstrează-l în Gmail
            pentru retention automat — Google îți oferă 15 GB gratuit, mai mult decât suficient
            pentru zeci de luni de backup-uri.
          </p>
        """,
    )

    sent_count = 0
    for r in recipients:
        try:
            from email_service import send_email
            res = await send_email(
                r,
                f"📦 PropManage Backup · {today_str} ({size_mb:.1f} MB)",
                html,
                attachments=attachments,
            )
            if res.get("ok"):
                sent_count += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"[Backup] email to {r} failed: {e}")

    # Mark in DB
    try:
        await db.backup_runs.update_one(
            {"_id": fp.name},
            {"$set": {"delivered_email": sent_count > 0, "email_recipients": sent_count}},
        )
    except Exception:  # noqa: BLE001
        pass

    return {"sent": sent_count > 0, "recipients": sent_count, "total_recipients": len(recipients)}


# ---------------------------------------------------------------------------
# Scheduler entrypoint
# ---------------------------------------------------------------------------

async def run_daily_backup_job() -> None:
    """Cron entrypoint — never raises."""
    try:
        result = await create_backup()
        if not result.get("ok"):
            logger.error(f"[Backup][cron] create failed: {result.get('error')}")
            return
        email_res = await email_backup(result["path"], result["size_mb"], result)
        logger.info(f"[Backup][cron] done · email={email_res}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[Backup][cron] unhandled: {e}", exc_info=True)


async def latest_backup_status() -> Optional[dict]:
    """For Morning Briefing — last backup metadata."""
    doc = await db.backup_runs.find_one({}, sort=[("started_at", -1)])
    if not doc:
        return None
    doc.pop("_id", None)
    return doc
