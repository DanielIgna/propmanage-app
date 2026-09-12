"""Property Document Vault — Property DNA (Sprint CX-2).

Nu un file manager: memoria permanentă a proprietății. Fiecare document = cunoaștere
structurată (metadate D015 cu proveniență), eveniment în timeline și progres în
Property Completeness Score. Single Source of Truth pentru istoricul proprietății.
"""
import asyncio
import uuid
from collections import Counter
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response

from db import db
from deps import get_current_user
from event_bus import emit
from routes.property_dna import _load_property_for
from storage_client import get_object, put_object
import storage_service

router = APIRouter(prefix="/api", tags=["property_documents"])

CATEGORIES = {
    "act_proprietate": "Act de proprietate",
    "cadastru": "Cadastru / Carte funciară",
    "certificat_energetic": "Certificat energetic",
    "contract": "Contract",
    "factura": "Factură",
    "garantie": "Certificat de garanție",
    "manual": "Manual echipament",
    "plan_tehnic": "Plan / schiță tehnică",
    "raport_inspectie": "Raport inspecție / audit",
    "foto": "Fotografie",
    "video": "Video",
    "altele": "Altele",
}
SYSTEMS = ["electric", "sanitar", "incalzire", "climatizare", "structura", "acoperis", "tamplarie", "finisaje", "altele"]

ALLOWED_EXT = {
    "pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "webp": "image/webp", "gif": "image/gif", "heic": "image/heic",
    "mp4": "video/mp4", "mov": "video/quicktime",
}

DOC_FIELDS = [
    "id", "property_id", "title", "category", "category_label", "filename", "content_type", "size",
    "building_system", "room", "doc_date", "uploaded_at", "author_name", "company", "specialist_id",
    "source", "provenance", "warranty_start", "warranty_end", "supplier", "tags", "notes",
    "related_request_id", "related_asset_id", "related_model_id", "related_room_id", "verification_status", "version", "prev_version_id", "history",
]


def _out(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    d["category_label"] = CATEGORIES.get(d.get("category"), d.get("category"))
    return {k: d.get(k) for k in DOC_FIELDS}


async def _load_doc_for(user: dict, doc_id: str) -> dict:
    try:
        doc = await db.property_documents.find_one({"_id": ObjectId(doc_id), "deleted": {"$ne": True}})
    except Exception:
        doc = None
    if not doc:
        raise HTTPException(404, "Documentul nu există")
    await _load_property_for(user, doc["property_id"])
    return doc


# ── Property Completeness Score (0–100) — semnale REALE, zero estimări ──────
async def _completeness(prop_id: str, prop: dict) -> dict:
    docs = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}
    ).to_list(500)
    cats = Counter(d.get("category") for d in docs)
    photos = cats.get("foto", 0)

    twin = await db.twins.find_one({"property_id": prop_id})
    assets = await db.property_assets.count_documents({"property_id": prop_id, "status": "active"})
    dna_attrs = len([v for v in (prop.get("dna_attributes") or {}).values() if (v or {}).get("value") is not None])
    works_confirmed = await db.requests.count_documents({"property_id": prop_id, "status": "confirmed"})
    warranties = await db.warranties.count_documents({"property_id": prop_id, "status": "active"})
    maint = await db.maintenance_logs.count_documents({"property_id": prop_id})

    items = []

    def add(iid, label, earned, mx, action):
        items.append({"id": iid, "label": label, "earned": earned, "max": mx, "done": earned >= mx, "action": action})

    add("act_proprietate", "Act de proprietate", 10 if cats.get("act_proprietate") else 0, 10, "upload:act_proprietate")
    add("cadastru", "Cadastru / Carte funciară", 6 if cats.get("cadastru") else 0, 6, "upload:cadastru")
    add("certificat_energetic", "Certificat energetic", 6 if cats.get("certificat_energetic") else 0, 6, "upload:certificat_energetic")
    add("plan_tehnic", "Plan / schiță tehnică", 6 if cats.get("plan_tehnic") else 0, 6, "upload:plan_tehnic")
    add("foto", "Fotografii ale casei (min. 3)", 7 if photos >= 3 else (3 if photos else 0), 7, "upload:foto")
    add("garantii_manuale", "Garanții / manuale echipamente", 5 if (cats.get("garantie") or cats.get("manual")) else 0, 5, "upload:garantie")
    add("facturi", "Facturi / contracte lucrări", 5 if (cats.get("factura") or cats.get("contract")) else 0, 5, "upload:factura")
    add("twin", "Digital Twin validat", 12 if (twin or {}).get("status") == "approved" else (5 if twin else 0), 12, "twin")
    add("assets", "Instalații mapate (min. 3)", 12 if assets >= 3 else (6 if assets else 0), 12, "assets")
    add("dna_attrs", "Atribute DNA completate (min. 3)", 6 if dna_attrs >= 3 else (3 if dna_attrs else 0), 6, "dna")
    add("works", "Prima lucrare prin platformă", 10 if works_confirmed else 0, 10, "request")
    add("warranty", "Garanție activă", 5 if warranties else 0, 5, "request")
    add("maintenance", "Jurnal de mentenanță", 5 if maint else 0, 5, "maintenance")
    add("audit", "Raport de inspecție / audit tehnic", 5 if cats.get("raport_inspectie") else 0, 5, "upload:raport_inspectie")

    score = sum(i["earned"] for i in items)
    missing = sorted([i for i in items if not i["done"]], key=lambda i: i["max"] - i["earned"], reverse=True)
    next_step = None
    if missing:
        m = missing[0]
        next_step = {"id": m["id"], "label": m["label"], "action": m["action"], "expected_gain": m["max"] - m["earned"]}
    return {
        "property_id": prop_id, "score": score, "max": 100, "items": items,
        "missing": [{"id": m["id"], "label": m["label"], "gain": m["max"] - m["earned"]} for m in missing[:6]],
        "next_step": next_step, "docs_count": len(docs), "photos_count": photos,
    }


@router.get("/properties/{prop_id}/completeness")
async def property_completeness(prop_id: str, user: dict = Depends(get_current_user)):
    prop = await _load_property_for(user, prop_id)
    return await _completeness(prop_id, prop)


@router.post("/properties/{prop_id}/documents")
async def upload_document(
    prop_id: str,
    file: UploadFile = File(...),
    title: str = Form(""),
    category: str = Form(...),
    building_system: str = Form(""),
    room: str = Form(""),
    doc_date: str = Form(""),
    company: str = Form(""),
    supplier: str = Form(""),
    warranty_start: str = Form(""),
    warranty_end: str = Form(""),
    tags: str = Form(""),
    notes: str = Form(""),
    related_request_id: str = Form(""),
    related_asset_id: str = Form(""),
    related_model_id: str = Form(""),
    related_room_id: str = Form(""),
    user: dict = Depends(get_current_user),
):
    prop = await _load_property_for(user, prop_id)
    if category not in CATEGORIES:
        raise HTTPException(400, "Categorie invalidă")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Tip de fișier neacceptat (.{ext}). Acceptate: {', '.join(sorted(ALLOWED_EXT))}")
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Fișierul este gol")
    limit = await storage_service.file_limit_bytes("document_vault")
    if len(data) > limit:
        raise HTTPException(413, f"Fișierul depășește limita de {storage_service.fmt_bytes(limit)} per fișier")

    content_type = ALLOWED_EXT[ext]
    compression_meta = None
    if content_type.startswith("image/"):
        data, compression_meta = await storage_service.maybe_compress_image(data, ext)
    owner_id = str(prop.get("owner_id"))
    await storage_service.check_quota(owner_id, len(data), "personal")

    first_upload = await db.property_documents.count_documents({"property_id": prop_id, "deleted": {"$ne": True}}) == 0

    path = f"propmanage/properties/{prop_id}/{uuid.uuid4().hex}.{ext}"
    result = await asyncio.to_thread(put_object, path, data, content_type)

    role = user.get("active_view") or user.get("role")
    source = "specialist" if role == "specialist" else ("platform" if role in ("admin", "operator") else "owner_upload")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "property_id": prop_id,
        "owner_id": str(prop.get("owner_id")),
        "title": (title or "").strip() or (file.filename or "Document").rsplit(".", 1)[0],
        "category": category,
        "filename": file.filename,
        "content_type": content_type,
        "size": len(data),
        "storage_path": result["path"],
        "building_system": building_system or None,
        "room": (room or "").strip() or None,
        "doc_date": (doc_date or "").strip() or None,
        "uploaded_at": now,
        "author_name": user.get("name"),
        "author_id": str(user.get("id")),
        "company": (company or "").strip() or None,
        "specialist_id": str(user.get("id")) if role == "specialist" else None,
        "source": source,
        "provenance": "documented" if role in ("specialist", "admin", "operator") else "declared",
        "warranty_start": (warranty_start or "").strip() or None,
        "warranty_end": (warranty_end or "").strip() or None,
        "supplier": (supplier or "").strip() or None,
        "tags": [t.strip() for t in (tags or "").split(",") if t.strip()],
        "notes": (notes or "").strip() or None,
        "related_request_id": (related_request_id or "").strip() or None,
        "related_asset_id": (related_asset_id or "").strip() or None,
        "related_model_id": (related_model_id or "").strip() or None,
        "related_room_id": (related_room_id or "").strip() or None,
        "verification_status": "verified" if role in ("admin", "operator") else "unverified",
        "version": 1,
        "prev_version_id": None,
        "superseded": False,
        "deleted": False,
        "compression": compression_meta,
        "history": [{"at": now, "by": user.get("name"), "event": "upload"}],
    }
    ins = await db.property_documents.insert_one(doc)
    doc["_id"] = ins.inserted_id

    await storage_service.add_usage(owner_id, len(data), "personal")
    if content_type.startswith("video/"):
        asyncio.create_task(storage_service.compress_vault_video(str(ins.inserted_id)))

    await emit("document.uploaded", property_id=prop_id, actor=user,
               payload={"doc_id": str(ins.inserted_id), "category": category, "title": doc["title"]})
    if doc["warranty_end"]:
        await emit("warranty.registered", property_id=prop_id, actor=user,
                   payload={"doc_id": str(ins.inserted_id), "title": doc["title"], "warranty_end": doc["warranty_end"]})

    compl = await _completeness(prop_id, prop)
    return {"document": _out(doc), "first_upload": first_upload, "completeness": compl}


@router.get("/properties/{prop_id}/documents")
async def list_documents(
    prop_id: str,
    q: str = Query(""),
    category: str = Query(""),
    building_system: str = Query(""),
    room: str = Query(""),
    year: str = Query(""),
    tag: str = Query(""),
    warranty: str = Query(""),
    sort: str = Query("uploaded_at"),
    user: dict = Depends(get_current_user),
):
    await _load_property_for(user, prop_id)
    query = {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}
    if category:
        query["category"] = category
    if building_system:
        query["building_system"] = building_system
    if room:
        query["room"] = {"$regex": room, "$options": "i"}
    if tag:
        query["tags"] = tag
    if year:
        query["$or"] = [{"doc_date": {"$regex": f"^{year}"}}, {"doc_date": None, "uploaded_at": {"$regex": f"^{year}"}}]
    if warranty == "active":
        query["warranty_end"] = {"$gte": datetime.now(timezone.utc).date().isoformat()}
    if q:
        rx = {"$regex": q, "$options": "i"}
        query["$and"] = [{"$or": [{"title": rx}, {"filename": rx}, {"notes": rx}, {"company": rx},
                                  {"supplier": rx}, {"room": rx}, {"tags": rx}]}]
    sort_field = sort if sort in ("uploaded_at", "doc_date", "title", "size") else "uploaded_at"
    docs = await db.property_documents.find(query).sort(sort_field, -1).to_list(300)

    all_docs = await db.property_documents.find(
        {"property_id": prop_id, "deleted": {"$ne": True}, "superseded": {"$ne": True}}, {"category": 1}
    ).to_list(500)
    facets = Counter(d.get("category") for d in all_docs)
    return {
        "documents": [_out(d) for d in docs],
        "total": len(all_docs),
        "facets": [{"category": c, "label": CATEGORIES.get(c, c), "count": n} for c, n in facets.most_common()],
        "categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
        "systems": SYSTEMS,
    }


@router.get("/documents/{doc_id}")
async def document_detail(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await _load_doc_for(user, doc_id)
    versions = []
    cur = doc
    while cur and cur.get("prev_version_id") and len(versions) < 20:
        prev = None
        try:
            prev = await db.property_documents.find_one({"_id": ObjectId(cur["prev_version_id"])})
        except Exception:
            prev = None
        if prev:
            versions.append({"id": str(prev["_id"]), "version": prev.get("version"), "uploaded_at": prev.get("uploaded_at"), "size": prev.get("size")})
        cur = prev
    return {"document": _out(doc), "previous_versions": versions}


@router.get("/documents/{doc_id}/file")
async def document_file(doc_id: str, download: int = Query(0), user: dict = Depends(get_current_user)):
    doc = await _load_doc_for(user, doc_id)
    data, ct = await asyncio.to_thread(get_object, doc["storage_path"])
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{doc.get("filename") or "document"}"'
    return Response(content=data, media_type=doc.get("content_type") or ct, headers=headers)


EDITABLE = ["title", "category", "building_system", "room", "doc_date", "company", "supplier",
            "warranty_start", "warranty_end", "tags", "notes", "related_model_id", "related_room_id"]


@router.patch("/documents/{doc_id}")
async def update_document(doc_id: str, body: dict = Body(...), user: dict = Depends(get_current_user)):
    doc = await _load_doc_for(user, doc_id)
    changes = {}
    for k in EDITABLE:
        if k in body and body[k] != doc.get(k):
            if k == "category" and body[k] not in CATEGORIES:
                raise HTTPException(400, "Categorie invalidă")
            changes[k] = {"old": doc.get(k), "new": body[k]}
    if not changes:
        return {"document": _out(doc)}
    sets = {k: v["new"] for k, v in changes.items()}
    entry = {"at": datetime.now(timezone.utc).isoformat(), "by": user.get("name"), "event": "edit",
             "changes": {k: [v["old"], v["new"]] for k, v in changes.items()}}
    await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": sets, "$push": {"history": entry}})
    doc.update(sets)
    doc.setdefault("history", []).append(entry)
    return {"document": _out(doc)}


@router.post("/documents/{doc_id}/version")
async def upload_new_version(doc_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    doc = await _load_doc_for(user, doc_id)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Tip de fișier neacceptat")
    data = await file.read()
    limit = await storage_service.file_limit_bytes("document_vault")
    if not data or len(data) > limit:
        raise HTTPException(413, f"Fișier gol sau peste {storage_service.fmt_bytes(limit)}")
    if ALLOWED_EXT[ext].startswith("image/"):
        data, _cm = await storage_service.maybe_compress_image(data, ext)
    await storage_service.check_quota(str(doc.get("owner_id")), len(data), "personal")
    path = f"propmanage/properties/{doc['property_id']}/{uuid.uuid4().hex}.{ext}"
    result = await asyncio.to_thread(put_object, path, data, ALLOWED_EXT[ext])
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {**{k: doc.get(k) for k in doc if k != "_id"}}
    new_doc.update({
        "filename": file.filename, "content_type": ALLOWED_EXT[ext], "size": len(data),
        "storage_path": result["path"], "uploaded_at": now, "version": (doc.get("version") or 1) + 1,
        "prev_version_id": str(doc["_id"]), "superseded": False,
        "history": [{"at": now, "by": user.get("name"), "event": f"versiune nouă (v{(doc.get('version') or 1) + 1})"}],
    })
    ins = await db.property_documents.insert_one(new_doc)
    new_doc["_id"] = ins.inserted_id
    await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": {"superseded": True}})
    await storage_service.add_usage(str(doc.get("owner_id")), len(data), "personal")
    if ALLOWED_EXT[ext].startswith("video/"):
        asyncio.create_task(storage_service.compress_vault_video(str(ins.inserted_id)))
    await emit("document.updated", property_id=doc["property_id"], actor=user,
               payload={"doc_id": str(ins.inserted_id), "title": new_doc.get("title"), "version": new_doc["version"]})
    return {"document": _out(new_doc)}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await _load_doc_for(user, doc_id)
    entry = {"at": datetime.now(timezone.utc).isoformat(), "by": user.get("name"), "event": "delete"}
    await db.property_documents.update_one({"_id": doc["_id"]}, {"$set": {"deleted": True}, "$push": {"history": entry}})
    await storage_service.add_usage(str(doc.get("owner_id")), -(doc.get("size") or 0), "personal")
    return {"ok": True}
