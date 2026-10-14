"""Fotografii Rădăcini (S6-G): teren, anunț, recoltă. JPEG sanitizat (fără EXIF/GPS) în Supabase Storage privat.

`storage_client` e infrastructură comună PropManage, folosită doar prin funcțiile publice
(put_object / get_object / delete_object); de re-exportat prin bridge.py de către coordonator.
"""
import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageOps

import storage_client

from .bridge import db, get_current_user, serialize_doc
from .common import RadaciniRoute, get_optional_user, mark_demo, now_iso, oid_or_404
from .market import _expired
from .parcels import _staff_in_scope
from .projects import load_project, need_coordinator
from .staff import get_staff

log = logging.getLogger(__name__)
router = APIRouter(route_class=RadaciniRoute)

TARGETS = ("parcel", "listing", "harvest")
MAX_BYTES = 5 * 1024 * 1024
MAX_PER_TARGET = 6
MAX_SIDE = 1600
ALLOWED_CT = {"image/jpeg", "image/png", "image/webp"}
INVALID = "Fișier invalid. Sunt acceptate imagini JPEG, PNG sau WebP."

Image.MAX_IMAGE_PIXELS = 50_000_000  # protecție împotriva bombelor de decompresie


def sniff_type(data: bytes) -> Optional[str]:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def sanitize_image(data: bytes) -> tuple[bytes, int, int]:
    """Bytes de imagine → (JPEG fără metadate, lățime, înălțime). ValueError dacă nu e imagine validă."""
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Fotografia depășește 5 MB." if data else INVALID)
    if sniff_type(data) is None:
        raise ValueError(INVALID)
    try:
        with Image.open(io.BytesIO(data)) as im:
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            clean = Image.new("RGB", im.size)  # imagine nouă: fără info/EXIF
            clean.paste(im)
    except Exception:
        raise ValueError(INVALID) from None
    out = io.BytesIO()
    clean.save(out, format="JPEG", quality=82, optimize=True)
    return out.getvalue(), clean.size[0], clean.size[1]


# ----------------------------------------------------------------- acces la țintă

async def _load_target(target_type: str, target_id: str) -> dict:
    if target_type not in TARGETS:
        raise HTTPException(400, "Tip de țintă invalid.")
    coll = {"parcel": db.radacini_parcels, "listing": db.radacini_listings, "harvest": db.radacini_harvests}[target_type]
    doc = await coll.find_one({"_id": oid_or_404(target_id)})
    if not doc or (target_type == "parcel" and doc.get("archived_at")):
        raise HTTPException(404, "Ținta nu există.")
    return doc


async def _owner_access(target_type: str, doc: dict, user: dict) -> bool:
    """Proprietarul parcelei, vânzătorul anunțului, coordonatorul proiectului recoltei."""
    uid = user["id"]
    if target_type == "parcel":
        return doc.get("owner_user_id") == uid
    if target_type == "listing":
        return doc.get("seller_user_id") == uid
    proj = await db.radacini_projects.find_one({"_id": oid_or_404(doc.get("project_id"))}, {"members": 1})
    return any(m.get("user_id") == uid and m.get("role") == "coordinator" for m in (proj or {}).get("members", []))


async def _can_read(target_type: str, doc: dict, user: Optional[dict]) -> bool:
    if target_type == "parcel" and doc.get("status") == "published":
        return True
    if target_type == "listing" and doc.get("status") == "active" and not _expired(doc):
        return True
    if not user:
        return False
    if await _owner_access(target_type, doc, user):
        return True
    if target_type == "parcel":
        staff = await get_staff(user)
        return bool(staff and _staff_in_scope(staff, doc))
    if target_type == "harvest":
        try:
            await load_project(doc["project_id"], user)
            return True
        except HTTPException:
            return False
    return False


def _view(p: dict) -> dict:
    d = serialize_doc(p)
    return {k: d.get(k) for k in ("id", "target_type", "target_id", "width", "height", "size", "created_at")}


# ----------------------------------------------------------------- rute

@router.post("/photos", status_code=201)
async def upload_photo(
    target_type: str = Form(...),
    target_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    target = await _load_target(target_type, target_id)
    if target_type == "harvest":
        project, access, role = await load_project(target["project_id"], user)
        need_coordinator(access, role)
    elif not await _owner_access(target_type, target, user):
        raise HTTPException(403, "Nu poți adăuga fotografii aici.")
    if file.content_type not in ALLOWED_CT:
        raise HTTPException(400, INVALID)
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(400, "Fotografia depășește 5 MB.")
    try:
        jpeg, w, h = sanitize_image(data)
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    tid = str(target["_id"])
    if await db.radacini_photos.count_documents({"target_type": target_type, "target_id": tid}) >= MAX_PER_TARGET:
        raise HTTPException(409, f"Maximum {MAX_PER_TARGET} fotografii.")
    path = f"radacini/{target_type}/{tid}/{uuid.uuid4().hex}.jpg"
    try:
        storage_client.put_object(path, jpeg, "image/jpeg")
    except Exception:
        log.exception("radacini: încărcarea fotografiei a eșuat")
        raise HTTPException(502, "Fotografia nu a putut fi salvată. Încearcă din nou.") from None
    doc = mark_demo({
        "target_type": target_type, "target_id": tid, "path": path, "width": w, "height": h,
        "size": len(jpeg), "uploaded_by": user["id"], "created_at": now_iso(),
    })
    await db.radacini_photos.insert_one(doc)
    return {"photo": _view(doc)}


@router.get("/photos")
async def list_photos(
    target_type: str = Query(...), target_id: str = Query(...), user: Optional[dict] = Depends(get_optional_user),
):
    target = await _load_target(target_type, target_id)
    if not await _can_read(target_type, target, user):
        raise HTTPException(404, "Ținta nu există.")
    rows = await db.radacini_photos.find(
        {"target_type": target_type, "target_id": str(target["_id"])}
    ).sort("created_at", 1).limit(MAX_PER_TARGET).to_list(MAX_PER_TARGET)
    return {"photos": [_view(p) for p in rows]}


async def _load_photo(photo_id: str) -> dict:
    p = await db.radacini_photos.find_one({"_id": oid_or_404(photo_id)})
    if not p:
        raise HTTPException(404, "Fotografia nu există.")
    return p


@router.get("/photos/{photo_id}")
async def get_photo(photo_id: str, user: Optional[dict] = Depends(get_optional_user)):
    p = await _load_photo(photo_id)
    target = await _load_target(p["target_type"], p["target_id"])
    if not await _can_read(p["target_type"], target, user):
        raise HTTPException(404, "Fotografia nu există.")
    try:
        data, _ct = storage_client.get_object(p["path"])
    except Exception:
        log.exception("radacini: citirea fotografiei a eșuat")
        raise HTTPException(404, "Fotografia nu este disponibilă.") from None
    return Response(content=data, media_type="image/jpeg", headers={
        "Cache-Control": "private, max-age=3600", "X-Content-Type-Options": "nosniff"})


@router.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str, user: dict = Depends(get_current_user)):
    p = await _load_photo(photo_id)
    allowed = p.get("uploaded_by") == user["id"]
    if not allowed:
        try:
            target = await _load_target(p["target_type"], p["target_id"])
            allowed = await _owner_access(p["target_type"], target, user)
        except HTTPException:
            allowed = False
    if not allowed:
        raise HTTPException(403, "Nu poți șterge această fotografie.")
    try:
        storage_client.delete_object(p["path"])
    except Exception:
        log.exception("radacini: ștergerea obiectului a eșuat")
        raise HTTPException(502, "Fotografia nu a putut fi ștearsă. Încearcă din nou.") from None
    await db.radacini_photos.delete_one({"_id": p["_id"]})
    return {"ok": True}
