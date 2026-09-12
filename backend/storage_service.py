"""ST-001 · Storage Service — cote configurabile din DB, tracking utilizare, compresie media.

Tiers: FREE 250MB · House Health 5GB (abonament activ) · Digital Twin 20GB (bucket SEPARAT).
Digital Twin NU consumă cota personală a utilizatorului.
Config: colecția `storage_configs` (editabilă din /admin/storage, zero hardcodare).
Usage: colecția `storage_usage` per user (incremental la upload/delete + recompute retroactiv).
"""
import asyncio
import io
import logging
import mimetypes
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import HTTPException

from db import db

logger = logging.getLogger("propmanage.storage")

MB = 1024 * 1024
CONFIG_ID = "global"
HH_DIR = Path("/app/backend/uploads/house_health")
DT_DIR = Path(os.environ.get("DT_UPLOAD_DIR") or "/app/backend/uploads/digital_twin")

DEFAULT_CONFIG = {
    "id": CONFIG_ID,
    "tiers": {
        "free": {"label": "FREE", "quota_mb": 250},
        "house_health": {"label": "House Health", "quota_mb": 5120},
        "digital_twin": {"label": "Digital Twin", "quota_mb": 20480},
    },
    "file_limits_mb": {
        "document_vault": 25,
        "house_health_doc": 20,
        "house_health_eval": 20,
        "digital_twin_model": 200,
        "digital_twin_plan": 50,
        "docs_ai": 10,
    },
    "warning_thresholds": [80, 95],
    "compression": {
        "images_enabled": True,
        "image_max_dimension": 2560,
        "image_quality": 82,
        "image_min_kb": 200,
        "videos_enabled": True,
        "video_min_mb": 8,
        "video_crf": 28,
        "video_max_height": 1080,
    },
}

_cfg_cache = {"data": None, "at": 0.0}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ufilter(uid: str) -> dict:
    try:
        return {"_id": ObjectId(uid)}
    except Exception:  # noqa: BLE001
        return {"id": uid}


def fmt_bytes(n) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return "0 B"


# ─────────────────────────────── config ───────────────────────────────
def _merge_defaults(doc: dict) -> dict:
    merged = {**DEFAULT_CONFIG, **doc}
    for key in ("tiers", "file_limits_mb", "compression"):
        merged[key] = {**DEFAULT_CONFIG[key], **(doc.get(key) or {})}
    for tk, tv in DEFAULT_CONFIG["tiers"].items():
        merged["tiers"][tk] = {**tv, **(merged["tiers"].get(tk) or {})}
    return merged


async def get_config() -> dict:
    if _cfg_cache["data"] and time.time() - _cfg_cache["at"] < 60:
        return _cfg_cache["data"]
    doc = await db.storage_configs.find_one({"id": CONFIG_ID}, {"_id": 0})
    if not doc:
        doc = {**DEFAULT_CONFIG, "updated_at": _now_iso()}
        await db.storage_configs.update_one({"id": CONFIG_ID}, {"$setOnInsert": doc}, upsert=True)
    else:
        doc = _merge_defaults(doc)
    _cfg_cache["data"] = doc
    _cfg_cache["at"] = time.time()
    return doc


async def update_config(patch: dict, by: str | None = None) -> dict:
    current = await get_config()
    sets = {}
    if isinstance(patch.get("tiers"), dict):
        for tk in DEFAULT_CONFIG["tiers"]:
            tv = patch["tiers"].get(tk)
            if isinstance(tv, dict) and tv.get("quota_mb") is not None:
                q = float(tv["quota_mb"])
                if q < 1:
                    raise HTTPException(400, f"Cota pentru '{tk}' trebuie să fie ≥ 1 MB")
                sets[f"tiers.{tk}.quota_mb"] = q
            if isinstance(tv, dict) and tv.get("label"):
                sets[f"tiers.{tk}.label"] = str(tv["label"])[:60]
    if isinstance(patch.get("file_limits_mb"), dict):
        for cat in DEFAULT_CONFIG["file_limits_mb"]:
            v = patch["file_limits_mb"].get(cat)
            if v is not None:
                v = float(v)
                if v < 0.1:
                    raise HTTPException(400, f"Limita per fișier pentru '{cat}' trebuie să fie ≥ 0.1 MB")
                sets[f"file_limits_mb.{cat}"] = v
    if isinstance(patch.get("warning_thresholds"), list) and len(patch["warning_thresholds"]) == 2:
        thr = sorted(float(x) for x in patch["warning_thresholds"])
        if not (0 < thr[0] < thr[1] <= 100):
            raise HTTPException(400, "Pragurile de avertizare trebuie să fie între 1 și 100 (ex: [80, 95])")
        sets["warning_thresholds"] = thr
    if isinstance(patch.get("compression"), dict):
        for k in DEFAULT_CONFIG["compression"]:
            if k in patch["compression"]:
                v = patch["compression"][k]
                sets[f"compression.{k}"] = bool(v) if k.endswith("_enabled") else float(v)
    if not sets:
        return current
    sets["updated_at"] = _now_iso()
    if by:
        sets["updated_by"] = by
    await db.storage_configs.update_one({"id": CONFIG_ID}, {"$set": sets}, upsert=True)
    _cfg_cache["data"] = None
    return await get_config()


async def file_limit_bytes(category: str) -> int:
    cfg = await get_config()
    mb = cfg["file_limits_mb"].get(category) or DEFAULT_CONFIG["file_limits_mb"].get(category, 25)
    return int(mb * MB)


# ─────────────────────────────── tier + quota ───────────────────────────────
async def user_tier(user_id: str) -> tuple:
    """Returnează (tier_key, label, quota_bytes) pentru bucket-ul personal."""
    cfg = await get_config()
    key = "free"
    sub = await db.hh_subscriptions.find_one({"user_id": user_id, "status": "active"}, {"expires_at": 1})
    if sub and str(sub.get("expires_at") or "") > _now_iso():
        key = "house_health"
    t = cfg["tiers"].get(key) or cfg["tiers"]["free"]
    return key, t.get("label") or key, int((t.get("quota_mb") or 250) * MB)


async def get_usage(user_id: str) -> dict:
    doc = await db.storage_usage.find_one({"user_id": user_id}, {"_id": 0})
    return doc or {"user_id": user_id, "personal_bytes": 0, "digital_twin_bytes": 0, "files_count": 0, "dt_files_count": 0}


async def check_quota(user_id: str, incoming_bytes: int, bucket: str = "personal") -> None:
    """Ridică 413 dacă upload-ul ar depăși cota. DT are bucket separat."""
    cfg = await get_config()
    u = await get_usage(user_id)
    if bucket == "digital_twin":
        quota = int((cfg["tiers"]["digital_twin"].get("quota_mb") or 20480) * MB)
        used = max(0, u.get("digital_twin_bytes") or 0)
        if used + incoming_bytes > quota:
            raise HTTPException(413, f"Cota Digital Twin ({fmt_bytes(quota)}) ar fi depășită — folosit {fmt_bytes(used)}, fișierul are {fmt_bytes(incoming_bytes)}. Șterge modele vechi sau contactează echipa.")
        return
    tier_key, label, quota = await user_tier(user_id)
    used = max(0, u.get("personal_bytes") or 0)
    if used + incoming_bytes > quota:
        hint = " Activează abonamentul House Health pentru 5 GB de stocare." if tier_key == "free" else " Eliberează spațiu ștergând documente sau versiuni vechi."
        raise HTTPException(413, f"Spațiu de stocare insuficient: folosit {fmt_bytes(used)} din {fmt_bytes(quota)} ({label}), fișierul are {fmt_bytes(incoming_bytes)}.{hint}")


async def dt_remaining_bytes(owner_id: str) -> int:
    cfg = await get_config()
    quota = int((cfg["tiers"]["digital_twin"].get("quota_mb") or 20480) * MB)
    u = await get_usage(owner_id)
    return max(0, quota - max(0, u.get("digital_twin_bytes") or 0))


async def add_usage(user_id: str, delta_bytes: int, bucket: str = "personal", files_delta: int | None = None) -> None:
    if not user_id or not delta_bytes:
        return
    bfield = "digital_twin_bytes" if bucket == "digital_twin" else "personal_bytes"
    ffield = "dt_files_count" if bucket == "digital_twin" else "files_count"
    if files_delta is None:
        files_delta = 1 if delta_bytes > 0 else -1
    await db.storage_usage.update_one(
        {"user_id": user_id},
        {"$inc": {bfield: int(delta_bytes), ffield: files_delta}, "$set": {"updated_at": _now_iso()}},
        upsert=True,
    )


async def quota_status(user_id: str) -> dict | None:
    """Rezumat rapid pentru AI Success Manager. None dacă userul nu ocupă spațiu."""
    cfg = await get_config()
    u = await get_usage(user_id)
    used = max(0, u.get("personal_bytes") or 0)
    if used <= 0:
        return None
    tier_key, label, quota = await user_tier(user_id)
    thr = sorted(cfg.get("warning_thresholds") or [80, 95])
    return {"pct": (used * 100 / quota) if quota else 0.0, "tier": tier_key, "tier_label": label,
            "used_human": fmt_bytes(used), "quota_human": fmt_bytes(quota), "thresholds": thr}


async def usage_snapshot(user: dict) -> dict:
    """Payload complet pentru UI-ul utilizatorului (GET /api/storage/usage)."""
    uid = str(user.get("id"))
    cfg = await get_config()
    tier_key, tier_label, quota = await user_tier(uid)
    u = await get_usage(uid)
    used = max(0, u.get("personal_bytes") or 0)
    pct = round(used * 100 / quota, 1) if quota else 0.0
    thr = sorted(cfg.get("warning_thresholds") or [80, 95])
    warning = "critical" if pct >= thr[1] else ("soft" if pct >= thr[0] else None)
    out = {
        "personal": {
            "tier": tier_key, "tier_label": tier_label,
            "used_bytes": used, "quota_bytes": quota,
            "used_human": fmt_bytes(used), "quota_human": fmt_bytes(quota),
            "pct": pct, "warning": warning, "files_count": max(0, u.get("files_count") or 0),
        },
        "thresholds": thr,
        "upgrade_available": tier_key == "free",
        "generated_at": _now_iso(),
    }
    dt_used = max(0, u.get("digital_twin_bytes") or 0)
    fresh = await db.users.find_one(_ufilter(uid), {"digital_twin_pro": 1})
    if dt_used > 0 or bool(fresh and fresh.get("digital_twin_pro")) or user.get("role") in ("admin", "operator"):
        dt_quota = int((cfg["tiers"]["digital_twin"].get("quota_mb") or 20480) * MB)
        dt_pct = round(dt_used * 100 / dt_quota, 1) if dt_quota else 0.0
        out["digital_twin"] = {
            "used_bytes": dt_used, "quota_bytes": dt_quota,
            "used_human": fmt_bytes(dt_used), "quota_human": fmt_bytes(dt_quota),
            "pct": dt_pct, "files_count": max(0, u.get("dt_files_count") or 0),
            "note": "Cotă separată — Digital Twin nu consumă spațiul tău personal.",
        }
    return out


# ─────────────────────────────── recompute retroactiv ───────────────────────────────
async def recompute_all() -> dict:
    """Agregă retroactiv spațiul ocupat de fiecare user din toate colecțiile media."""
    per_user: dict = {}

    def bump(uid, nbytes, bucket="personal"):
        if not uid:
            return
        uid = str(uid)
        e = per_user.setdefault(uid, {"personal_bytes": 0, "digital_twin_bytes": 0, "files_count": 0, "dt_files_count": 0})
        if bucket == "digital_twin":
            e["digital_twin_bytes"] += int(nbytes or 0)
            e["dt_files_count"] += 1
        else:
            e["personal_bytes"] += int(nbytes or 0)
            e["files_count"] += 1

    async for d in db.property_documents.find({"deleted": {"$ne": True}}, {"owner_id": 1, "size": 1}):
        bump(d.get("owner_id"), d.get("size"))
    async for d in db.hh_documents.find({"storage": {"$in": ["local", "object"]}}, {"user_id": 1, "size_bytes": 1}):
        bump(d.get("user_id"), d.get("size_bytes"))
    async for e in db.hh_evaluations.find({"attachments.0": {"$exists": True}}, {"specialist_id": 1, "attachments": 1}):
        for a in e.get("attachments") or []:
            bump(a.get("uploaded_by") or e.get("specialist_id"), a.get("size_bytes"))
    async for d in db.ai_documents.find({}, {"owner_user_id": 1, "size_bytes": 1}):
        bump(d.get("owner_user_id"), d.get("size_bytes"))

    owners = {}
    async for p in db.digital_twin_projects.find({}, {"id": 1, "owner_id": 1}):
        owners[p.get("id")] = p.get("owner_id")
    async for m in db.digital_twin_models.find({}, {"project_id": 1, "size_bytes": 1}):
        bump(owners.get(m.get("project_id")), m.get("size_bytes"), "digital_twin")
    async for pl in db.digital_twin_plans.find({}, {"project_id": 1, "size_bytes": 1}):
        bump(owners.get(pl.get("project_id")), pl.get("size_bytes"), "digital_twin")

    now = _now_iso()
    await db.storage_usage.delete_many({})
    if per_user:
        await db.storage_usage.insert_many([
            {"user_id": uid, **vals, "computed_at": now, "updated_at": now} for uid, vals in per_user.items()
        ])
    await db.storage_meta.update_one({"id": "init"}, {"$set": {"recompute_done": True, "at": now}}, upsert=True)
    totals = {
        "users": len(per_user),
        "personal_bytes": sum(v["personal_bytes"] for v in per_user.values()),
        "digital_twin_bytes": sum(v["digital_twin_bytes"] for v in per_user.values()),
        "files": sum(v["files_count"] + v["dt_files_count"] for v in per_user.values()),
    }
    logger.info(f"[storage] recompute: {totals}")
    return {"ok": True, **totals, "personal_human": fmt_bytes(totals["personal_bytes"]),
            "digital_twin_human": fmt_bytes(totals["digital_twin_bytes"]), "computed_at": now}


async def ensure_initial_recompute() -> None:
    meta = await db.storage_meta.find_one({"id": "init"}, {"recompute_done": 1})
    if meta and meta.get("recompute_done"):
        return
    prev = await db.storage_meta.find_one_and_update(
        {"id": "init"}, {"$set": {"recompute_done": True, "at": _now_iso()}}, upsert=True,
    )
    if prev and prev.get("recompute_done"):
        return
    await recompute_all()


# ─────────────────────────────── compresie imagini ───────────────────────────────
def _compress_image_sync(data: bytes, ext: str, cfg: dict):
    from PIL import Image, ImageOps
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    maxd = int(cfg.get("image_max_dimension") or 2560)
    if max(img.size) > maxd:
        img.thumbnail((maxd, maxd))
    buf = io.BytesIO()
    quality = int(cfg.get("image_quality") or 82)
    if ext in ("jpg", "jpeg"):
        img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    elif ext == "png":
        img.save(buf, "PNG", optimize=True)
    elif ext == "webp":
        img.save(buf, "WEBP", quality=quality, method=4)
    else:
        return data, None
    out = buf.getvalue()
    if len(out) < len(data) * 0.9:
        return out, {"original_bytes": len(data), "compressed_bytes": len(out),
                     "saved_bytes": len(data) - len(out), "method": f"pillow_{ext}"}
    return data, None


async def maybe_compress_image(data: bytes, ext: str):
    """Compresie automată la upload (jpg/png/webp). Returnează (bytes, meta|None)."""
    cfg = (await get_config())["compression"]
    ext = (ext or "").lower().lstrip(".")
    if not cfg.get("images_enabled") or ext not in ("jpg", "jpeg", "png", "webp"):
        return data, None
    if len(data) < int(cfg.get("image_min_kb") or 200) * 1024:
        return data, None
    try:
        return await asyncio.to_thread(_compress_image_sync, data, ext, cfg)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[storage] image compression skipped: {e}")
        return data, None


# ─────────────────────────────── compresie video (ffmpeg static) ───────────────────────────────
def _ffmpeg_exe() -> str | None:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def _compress_video_sync(data: bytes, cfg: dict):
    exe = _ffmpeg_exe()
    if not exe:
        return None, None
    crf = int(cfg.get("video_crf") or 28)
    maxh = int(cfg.get("video_max_height") or 1080)
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "in.bin"
        dst = Path(td) / "out.mp4"
        src.write_bytes(data)
        cmd = [exe, "-y", "-i", str(src), "-vf", f"scale=-2:'min({maxh},ih)'",
               "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
               "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(dst)]
        r = subprocess.run(cmd, capture_output=True, timeout=900)
        if r.returncode != 0 or not dst.exists():
            logger.warning(f"[storage] ffmpeg failed: {r.stderr[-300:] if r.stderr else 'no output'}")
            return None, None
        out = dst.read_bytes()
    if len(out) < len(data) * 0.9:
        return out, {"original_bytes": len(data), "compressed_bytes": len(out),
                     "saved_bytes": len(data) - len(out), "method": f"ffmpeg_h264_crf{crf}"}
    return None, None


async def compress_vault_video(doc_id: str) -> None:
    """Background: comprimă un video din Document Vault și înlocuiește obiectul stocat."""
    from storage_client import get_object, put_object
    cfg = (await get_config())["compression"]
    if not cfg.get("videos_enabled") or not _ffmpeg_exe():
        return
    try:
        doc = await db.property_documents.find_one({"_id": ObjectId(doc_id)})
    except Exception:  # noqa: BLE001
        return
    if not doc or not (doc.get("content_type") or "").startswith("video/"):
        return
    if (doc.get("compression") or {}).get("status") in ("running", "done"):
        return
    if (doc.get("size") or 0) < float(cfg.get("video_min_mb") or 8) * MB:
        return
    await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": {"compression": {"status": "running"}}})
    try:
        data, _ = await asyncio.to_thread(get_object, doc["storage_path"])
        out, meta = await asyncio.to_thread(_compress_video_sync, data, cfg)
        if not out:
            await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": {"compression": {"status": "skipped"}}})
            return
        base, _sep, _old = doc["storage_path"].rpartition(".")
        new_path = f"{base or doc['storage_path']}_c.mp4"
        await asyncio.to_thread(put_object, new_path, out, "video/mp4")
        delta = len(out) - (doc.get("size") or len(data))
        await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": {
            "storage_path": new_path, "size": len(out), "content_type": "video/mp4",
            "compression": {"status": "done", **meta},
        }})
        await add_usage(str(doc.get("owner_id")), delta, "personal", files_delta=0)
        logger.info(f"[storage] video {doc_id} comprimat: {fmt_bytes(meta['saved_bytes'])} economisiți")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[storage] video compression failed for {doc_id}: {e}")
        await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": {"compression": {"status": "failed"}}})


# ─────────────────────────────── Digital Twin: mirror durabil + restore ───────────────────────────────
def _guess_ct(name: str) -> str:
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


async def mirror_dt_file(kind: str, doc_id: str) -> None:
    """Copie durabilă în Emergent Object Storage (discul local se pierde la redeploy)."""
    from storage_client import put_object
    coll = db.digital_twin_models if kind == "model" else db.digital_twin_plans
    doc = await coll.find_one({"id": doc_id})
    if not doc or doc.get("object_path"):
        return
    sub = "plans/" if kind == "plan" else ""
    fp = DT_DIR / doc["project_id"] / "plans" / doc["stored_as"] if kind == "plan" else DT_DIR / doc["project_id"] / doc["stored_as"]
    if not fp.exists():
        return
    path = f"propmanage/digital_twin/{doc['project_id']}/{sub}{doc['stored_as']}"
    try:
        data = fp.read_bytes()
        ct = "application/pdf" if kind == "plan" else _guess_ct(doc["stored_as"])
        await asyncio.to_thread(put_object, path, data, ct)
        await coll.update_one({"id": doc_id}, {"$set": {"object_path": path}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[storage] DT mirror failed for {kind} {doc_id}: {e}")


def dt_object_path(kind: str, project_id: str, stored_as: str) -> str:
    sub = "plans/" if kind == "plan" else ""
    return f"propmanage/digital_twin/{project_id}/{sub}{stored_as}"


async def store_dt_bytes(kind: str, project_id: str, stored_as: str, data: bytes, content_type: str) -> str:
    """Persistă un fișier Digital Twin DIRECT în Emergent Object Storage (durabil la redeploy).

    Discul pod-local e folosit doar drept cache la cerere (vezi ensure_dt_local / restore_dt_file).
    Retry bounded (3 încercări) pentru 5xx tranzitorii din upstream — upload-ul e user-facing.
    """
    from storage_client import put_object
    path = dt_object_path(kind, project_id, stored_as)
    last_err = None
    for attempt in range(3):
        try:
            await asyncio.to_thread(put_object, path, data, content_type)
            return path
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning(f"[storage] store_dt_bytes attempt {attempt + 1}/3 failed for {path}: {e}")
            await asyncio.sleep(0.6 * (attempt + 1))
    raise last_err


async def ensure_dt_local(kind: str, project_id: str, stored_as: str):
    """Întoarce calea locală (cache) a unui fișier DT; îl readuce din Object Storage dacă lipsește."""
    dirp = (DT_DIR / project_id / "plans") if kind == "plan" else (DT_DIR / project_id)
    fp = dirp / stored_as
    if fp.exists():
        return fp
    return await restore_dt_file(kind, project_id, stored_as)


async def restore_dt_file(kind: str, project_id: str, filename: str):
    """Fallback la servire: readuce fișierul de pe object storage pe disc (cache)."""
    from storage_client import get_object
    coll = db.digital_twin_models if kind == "model" else db.digital_twin_plans
    doc = await coll.find_one({"project_id": project_id, "stored_as": filename}, {"object_path": 1})
    if not doc or not doc.get("object_path"):
        return None
    try:
        data, _ = await asyncio.to_thread(get_object, doc["object_path"])
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[storage] DT restore failed {project_id}/{filename}: {e}")
        return None
    dirp = (DT_DIR / project_id / "plans") if kind == "plan" else (DT_DIR / project_id)
    dirp.mkdir(parents=True, exist_ok=True)
    fp = dirp / filename
    fp.write_bytes(data)
    return fp


# ─────────────────────────────── migrare disc → object storage ───────────────────────────────
async def migration_status() -> dict:
    doc = await db.storage_migrations.find_one({"id": "st001"}, {"_id": 0})
    return doc or {"id": "st001", "status": "not_started"}


async def start_migration() -> dict:
    doc = await db.storage_migrations.find_one({"id": "st001"}, {"status": 1})
    if doc and doc.get("status") == "running":
        return {"ok": False, "status": "running", "detail": "Migrarea rulează deja."}
    await db.storage_migrations.update_one({"id": "st001"}, {"$set": {
        "id": "st001", "status": "running", "started_at": _now_iso(), "finished_at": None,
        "hh_docs": 0, "hh_evals": 0, "dt_models": 0, "dt_plans": 0, "bytes_moved": 0, "errors": [],
    }}, upsert=True)
    asyncio.create_task(_run_migration())
    return {"ok": True, "status": "running"}


async def _run_migration() -> None:
    from storage_client import put_object

    async def _inc(field, nbytes=0):
        await db.storage_migrations.update_one({"id": "st001"}, {"$inc": {field: 1, "bytes_moved": int(nbytes)}})

    async def _err(msg):
        logger.warning(f"[storage] migration error: {msg}")
        await db.storage_migrations.update_one({"id": "st001"}, {"$push": {"errors": str(msg)[:300]}})

    try:
        # 1) House Health docs: mutare completă local → object (+ștergere disc)
        async for d in db.hh_documents.find({"storage": "local"}):
            try:
                files = list(HH_DIR.glob(f"{d['id']}_*"))
                if not files:
                    continue
                fp = files[0]
                path = f"propmanage/house_health/{d['id']}/{fp.name}"
                await asyncio.to_thread(put_object, path, fp.read_bytes(), d.get("mime") or _guess_ct(fp.name))
                await db.hh_documents.update_one({"id": d["id"]}, {"$set": {"storage": "object", "object_path": path}})
                fp.unlink(missing_ok=True)
                await _inc("hh_docs", d.get("size_bytes") or 0)
            except Exception as e:  # noqa: BLE001
                await _err(f"hh_doc {d.get('id')}: {e}")

        # 2) House Health evaluation attachments
        async for e in db.hh_evaluations.find({"attachments.0": {"$exists": True}}):
            for a in e.get("attachments") or []:
                if a.get("object_path"):
                    continue
                try:
                    files = list(HH_DIR.glob(f"eval_{e['id']}_{a['id']}_*"))
                    if not files:
                        continue
                    fp = files[0]
                    path = f"propmanage/house_health/eval/{e['id']}/{fp.name}"
                    await asyncio.to_thread(put_object, path, fp.read_bytes(), a.get("mime") or _guess_ct(fp.name))
                    await db.hh_evaluations.update_one({"id": e["id"], "attachments.id": a["id"]},
                                                       {"$set": {"attachments.$.object_path": path}})
                    fp.unlink(missing_ok=True)
                    await _inc("hh_evals", a.get("size_bytes") or 0)
                except Exception as ex:  # noqa: BLE001
                    await _err(f"hh_eval {e.get('id')}/{a.get('id')}: {ex}")

        # 3) Digital Twin: mirror durabil (discul rămâne cache pentru viewer + Blender)
        async for m in db.digital_twin_models.find({"object_path": {"$exists": False}}):
            try:
                fp = DT_DIR / m["project_id"] / m["stored_as"]
                if not fp.exists():
                    continue
                path = f"propmanage/digital_twin/{m['project_id']}/{m['stored_as']}"
                await asyncio.to_thread(put_object, path, fp.read_bytes(), _guess_ct(m["stored_as"]))
                await db.digital_twin_models.update_one({"id": m["id"]}, {"$set": {"object_path": path}})
                await _inc("dt_models", m.get("size_bytes") or 0)
            except Exception as e:  # noqa: BLE001
                await _err(f"dt_model {m.get('id')}: {e}")

        async for p in db.digital_twin_plans.find({"object_path": {"$exists": False}}):
            try:
                fp = DT_DIR / p["project_id"] / "plans" / p["stored_as"]
                if not fp.exists():
                    continue
                path = f"propmanage/digital_twin/{p['project_id']}/plans/{p['stored_as']}"
                await asyncio.to_thread(put_object, path, fp.read_bytes(), "application/pdf")
                await db.digital_twin_plans.update_one({"id": p["id"]}, {"$set": {"object_path": path}})
                await _inc("dt_plans", p.get("size_bytes") or 0)
            except Exception as e:  # noqa: BLE001
                await _err(f"dt_plan {p.get('id')}: {e}")

        await db.storage_migrations.update_one({"id": "st001"}, {"$set": {"status": "done", "finished_at": _now_iso()}})
        logger.info("[storage] migration ST-001 done")
    except Exception as e:  # noqa: BLE001
        await db.storage_migrations.update_one({"id": "st001"}, {"$set": {"status": "failed", "finished_at": _now_iso()}})
        await _err(f"fatal: {e}")


# ─────────────────────────────── admin overview ───────────────────────────────
def _dir_bytes(path: Path) -> int:
    total = 0
    if path.exists():
        for root, _dirs, files in os.walk(path):
            for f in files:
                try:
                    total += (Path(root) / f).stat().st_size
                except OSError:
                    pass
    return total


async def _agg(coll, match, size_field):
    r = await coll.aggregate([
        {"$match": match},
        {"$group": {"_id": None, "bytes": {"$sum": f"${size_field}"}, "count": {"$sum": 1}}},
    ]).to_list(1)
    return (int(r[0].get("bytes") or 0), r[0]["count"]) if r else (0, 0)


async def admin_overview() -> dict:
    cfg = await get_config()
    t = await db.storage_usage.aggregate([{"$group": {
        "_id": None, "personal": {"$sum": "$personal_bytes"}, "dt": {"$sum": "$digital_twin_bytes"},
        "files": {"$sum": "$files_count"}, "dt_files": {"$sum": "$dt_files_count"}, "users": {"$sum": 1},
    }}]).to_list(1)
    totals = t[0] if t else {"personal": 0, "dt": 0, "files": 0, "dt_files": 0, "users": 0}
    totals.pop("_id", None)

    top = await db.storage_usage.find({}, {"_id": 0}).sort("personal_bytes", -1).to_list(20)
    for row in top:
        usr = await db.users.find_one(_ufilter(row["user_id"]), {"email": 1, "name": 1})
        row["email"] = (usr or {}).get("email")
        row["name"] = (usr or {}).get("name")
        tk, lbl, quota = await user_tier(row["user_id"])
        row["tier"] = tk
        row["tier_label"] = lbl
        row["quota_bytes"] = quota
        row["pct"] = round(max(0, row.get("personal_bytes") or 0) * 100 / quota, 1) if quota else 0
        row["personal_human"] = fmt_bytes(row.get("personal_bytes"))
        row["dt_human"] = fmt_bytes(row.get("digital_twin_bytes"))

    vault_b, vault_c = await _agg(db.property_documents, {"deleted": {"$ne": True}}, "size")
    hh_b, hh_c = await _agg(db.hh_documents, {"storage": {"$in": ["local", "object"]}}, "size_bytes")
    ev = await db.hh_evaluations.aggregate([
        {"$unwind": "$attachments"},
        {"$group": {"_id": None, "bytes": {"$sum": "$attachments.size_bytes"}, "count": {"$sum": 1}}},
    ]).to_list(1)
    ev_b, ev_c = (int(ev[0].get("bytes") or 0), ev[0]["count"]) if ev else (0, 0)
    dtm_b, dtm_c = await _agg(db.digital_twin_models, {}, "size_bytes")
    dtp_b, dtp_c = await _agg(db.digital_twin_plans, {}, "size_bytes")
    ai_b, ai_c = await _agg(db.ai_documents, {}, "size_bytes")
    hh_migrated = await db.hh_documents.count_documents({"storage": "object"})
    dt_mirrored = await db.digital_twin_models.count_documents({"object_path": {"$exists": True}}) + \
        await db.digital_twin_plans.count_documents({"object_path": {"$exists": True}})

    modules = [
        {"id": "document_vault", "label": "Document Vault (Cartea casei)", "bytes": vault_b, "count": vault_c, "provider": "Emergent Object Storage"},
        {"id": "house_health", "label": "House Health · documente", "bytes": hh_b, "count": hh_c, "provider": f"Object Storage ({hh_migrated}/{hh_c} migrate)"},
        {"id": "house_health_eval", "label": "House Health · evaluări", "bytes": ev_b, "count": ev_c, "provider": "Object Storage + disc"},
        {"id": "digital_twin", "label": "Digital Twin · modele 3D + planuri", "bytes": dtm_b + dtp_b, "count": dtm_c + dtp_c, "provider": f"Disc + mirror Object Storage ({dt_mirrored}/{dtm_c + dtp_c})"},
        {"id": "docs_ai", "label": "Docs AI (RAG)", "bytes": ai_b, "count": ai_c, "provider": "MongoDB (text extras)"},
    ]
    for m in modules:
        m["human"] = fmt_bytes(m["bytes"])

    return {
        "totals": {**totals, "personal_human": fmt_bytes(totals.get("personal") or 0),
                   "dt_human": fmt_bytes(totals.get("dt") or 0)},
        "top_users": top,
        "modules": modules,
        "disk": {"house_health_bytes": _dir_bytes(HH_DIR), "digital_twin_bytes": _dir_bytes(DT_DIR),
                 "house_health_human": fmt_bytes(_dir_bytes(HH_DIR)), "digital_twin_human": fmt_bytes(_dir_bytes(DT_DIR))},
        "migration": await migration_status(),
        "config": cfg,
        "video_compression_available": bool(_ffmpeg_exe()),
        "generated_at": _now_iso(),
    }
