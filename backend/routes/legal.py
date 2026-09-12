"""Legal Documents & Collaborator Contracts module.

Implements the legal framework for Strategic Contributors (IT collaborators):
- 6 mandatory document templates (NDA, Collaboration, IP Cession, Security, Infra, Regulation)
- Per-user signature tracking with IP + UA + version
- Compliance status endpoint (used by frontend gate)
- Admin audit endpoint (all collaborators × contract status)

Collections:
  legal_documents { _id, type, version, title, summary, body, mandatory, active, created_at, updated_at, created_by }
  collaborator_contracts { _id, user_id, user_email, document_id, document_type, document_version,
                           status (pending|accepted|expired|revoked), accepted_at, signature_method,
                           signature_name, ip_address, user_agent, expires_at }
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin
from legal_templates import LEGAL_DOC_TYPES, list_default_templates

logger = logging.getLogger("propmanage.legal")

router = APIRouter(prefix="/api/legal", tags=["legal"])
admin_router = APIRouter(prefix="/api/admin/legal", tags=["admin-legal"])

ALLOWED_TYPES = set(LEGAL_DOC_TYPES)
ALLOWED_STATUSES = {"pending", "accepted", "expired", "revoked"}


# ─────────────────────────────────────────────────────────────────────────────
# Seeder
# ─────────────────────────────────────────────────────────────────────────────
async def seed_default_legal_documents() -> dict:
    """Idempotent: insert any missing default templates and backfill `audience`."""
    inserted = 0
    for tpl in list_default_templates():
        existing = await db.legal_documents.find_one({"type": tpl["type"], "version": tpl["version"]})
        if existing:
            # Backfill audience on existing legacy rows
            if "audience" not in existing:
                await db.legal_documents.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"audience": tpl["audience"]}},
                )
            continue
        doc = {
            **tpl,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "system_seed",
        }
        await db.legal_documents.insert_one(doc)
        inserted += 1
    logger.info(f"[legal] seed_default_legal_documents inserted={inserted}")
    return {"inserted": inserted, "total": len(LEGAL_DOC_TYPES)}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _doc_out(d: dict) -> dict:
    if not d:
        return d
    return {
        "id": str(d.get("_id")),
        "type": d.get("type"),
        "version": d.get("version"),
        "title": d.get("title"),
        "summary": d.get("summary"),
        "body": d.get("body"),
        "mandatory": bool(d.get("mandatory")),
        "active": bool(d.get("active")),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


def _contract_out(c: dict, doc: dict | None = None) -> dict:
    if not c:
        return c
    out = {
        "id": str(c.get("_id")),
        "document_id": str(c.get("document_id")) if c.get("document_id") else None,
        "document_type": c.get("document_type"),
        "document_version": c.get("document_version"),
        "user_id": str(c.get("user_id")) if c.get("user_id") else None,
        "user_email": c.get("user_email"),
        "status": c.get("status"),
        "accepted_at": c.get("accepted_at"),
        "signature_method": c.get("signature_method"),
        "signature_name": c.get("signature_name"),
        "expires_at": c.get("expires_at"),
        "ip_address": c.get("ip_address"),
    }
    if doc:
        out["document_title"] = doc.get("title")
        out["document_summary"] = doc.get("summary")
    return out


async def _active_mandatory_documents(audience: str = "it_collaborator") -> list:
    """Returns active mandatory docs scoped to the given audience.

    Documents without an explicit `audience` are treated as `it_collaborator`
    for backwards compatibility.
    """
    cur = db.legal_documents.find({
        "mandatory": True,
        "active": True,
        "$or": [
            {"audience": audience},
            {"audience": {"$exists": False}} if audience == "it_collaborator" else {"audience": "__never__"},
        ],
    })
    return [d async for d in cur]


async def _is_strategic_contributor(user: dict) -> bool:
    """A user is a strategic contributor if they:
    - have an `it_collaborator` linked by email, OR
    - have role 'specialist' / 'admin' with explicit flag user.is_strategic_contributor
    """
    if user.get("is_strategic_contributor"):
        return True
    email = (user.get("email") or "").lower()
    if not email:
        return False
    match = await db.it_collaborators.find_one({"email": email, "status": {"$ne": "archived"}})
    return bool(match)


# ─────────────────────────────────────────────────────────────────────────────
# Public-ish: read documents & sign
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/documents")
async def list_documents(active_only: bool = True, user=Depends(get_current_user)):
    """List all currently active legal documents (visible to any logged-in user)."""
    q = {}
    if active_only:
        q["active"] = True
    cur = db.legal_documents.find(q).sort([("type", 1), ("version", -1)])
    items = [_doc_out(d) async for d in cur]
    return {"items": items, "count": len(items)}


@router.get("/documents/{doc_type}")
async def get_document_by_type(doc_type: str, user=Depends(get_current_user)):
    """Get the latest active document for a given type."""
    if doc_type not in ALLOWED_TYPES:
        raise HTTPException(404, f"Tip document necunoscut: {doc_type}")
    doc = await db.legal_documents.find_one({"type": doc_type, "active": True}, sort=[("version", -1)])
    if not doc:
        raise HTTPException(404, f"Niciun document activ pentru tipul {doc_type}.")
    return _doc_out(doc)


class AcceptPayload(BaseModel):
    document_id: str
    agreed: bool = Field(..., description="Must be true to accept")
    signature_name: str = Field(min_length=2, max_length=120)


@router.post("/me/accept")
async def accept_document(payload: AcceptPayload, request: Request, user=Depends(get_current_user)):
    """Sign a legal document. Records IP, UA, version, timestamp."""
    if not payload.agreed:
        raise HTTPException(400, "Trebuie să bifezi că ești de acord.")
    try:
        doc_oid = ObjectId(payload.document_id)
    except Exception:
        raise HTTPException(400, "document_id invalid.")
    doc = await db.legal_documents.find_one({"_id": doc_oid})
    if not doc:
        raise HTTPException(404, "Document inexistent.")
    if not doc.get("active"):
        raise HTTPException(400, "Documentul nu mai este activ.")

    user_email = (user.get("email") or "").lower()
    # Revoke older acceptances of same doc_type (so audit shows current version only)
    await db.collaborator_contracts.update_many(
        {
            "user_email": user_email,
            "document_type": doc["type"],
            "status": "accepted",
            "document_version": {"$ne": doc.get("version")},
        },
        {"$set": {"status": "expired", "expired_at": datetime.now(timezone.utc).isoformat()}},
    )

    contract = {
        "user_id": str(user.get("_id") or user.get("id") or ""),
        "user_email": user_email,
        "document_id": doc["_id"],
        "document_type": doc["type"],
        "document_version": doc.get("version"),
        "status": "accepted",
        "accepted_at": datetime.now(timezone.utc).isoformat(),
        "signature_method": "click_typed_name",
        "signature_name": payload.signature_name.strip(),
        "ip_address": (request.client.host if request.client else None),
        "user_agent": request.headers.get("user-agent", "")[:300],
        "expires_at": None,
    }
    res = await db.collaborator_contracts.insert_one(contract)
    contract["_id"] = res.inserted_id
    return _contract_out(contract, doc)


@router.get("/me/status")
async def my_legal_status(user=Depends(get_current_user)):
    """Returns the current user's compliance status for IT documents.

    For city_partner users, IT documents are NOT mandatory — see /api/partner/legal/status.
    """
    if user.get("role") == "city_partner" or user.get("role") == "marketplace_partner":
        # City / Marketplace partners have their own contract flow — IT gate skipped
        return {
            "is_strategic_contributor": False,
            "compliant": True,
            "required": [],
            "signed": [],
            "pending": [],
            "expired": [],
        }
    is_strategic = await _is_strategic_contributor(user)
    docs = await _active_mandatory_documents()
    user_email = (user.get("email") or "").lower()

    # Latest accepted contract per doc_type
    signed_map: dict[str, dict] = {}
    cur = db.collaborator_contracts.find({"user_email": user_email, "status": "accepted"})
    async for c in cur:
        signed_map[c["document_type"]] = c

    pending = []
    signed = []
    expired = []
    for d in docs:
        c = signed_map.get(d["type"])
        if not c:
            pending.append({
                "document_id": str(d["_id"]),
                "type": d["type"],
                "title": d["title"],
                "summary": d.get("summary"),
                "version": d.get("version"),
            })
            continue
        if c.get("document_version") != d.get("version"):
            expired.append({
                "document_id": str(d["_id"]),
                "type": d["type"],
                "title": d["title"],
                "summary": d.get("summary"),
                "signed_version": c.get("document_version"),
                "current_version": d.get("version"),
            })
        else:
            signed.append(_contract_out(c, d))

    compliant = is_strategic and not pending and not expired
    if not is_strategic:
        # Non-strategic contributors are compliant by default — but we still
        # surface the docs so they can sign voluntarily if desired.
        compliant = True

    return {
        "is_strategic_contributor": is_strategic,
        "compliant": compliant,
        "required": [d["type"] for d in docs],
        "signed": signed,
        "pending": pending,
        "expired": expired,
    }


@router.get("/partner/status")
async def partner_legal_status(user=Depends(get_current_user)):
    """Returns the city_partner user's compliance status for the partner contract."""
    if user.get("role") != "city_partner":
        return {"applicable": False, "compliant": True, "pending": [], "signed": []}
    docs = await _active_mandatory_documents(audience="city_partner")
    user_email = (user.get("email") or "").lower()
    signed_map = {}
    cur = db.collaborator_contracts.find({"user_email": user_email, "status": "accepted"})
    async for c in cur:
        signed_map[c["document_type"]] = c
    pending = []
    signed = []
    for d in docs:
        c = signed_map.get(d["type"])
        if not c or c.get("document_version") != d.get("version"):
            pending.append({
                "document_id": str(d["_id"]),
                "type": d["type"],
                "title": d["title"],
                "summary": d.get("summary"),
                "version": d.get("version"),
            })
        else:
            signed.append(_contract_out(c, d))
    return {
        "applicable": True,
        "compliant": not pending,
        "pending": pending,
        "signed": signed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Admin endpoints
# ─────────────────────────────────────────────────────────────────────────────
def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin poate gestiona documentele legale.")


class DocumentPayload(BaseModel):
    type: str
    version: str
    title: str
    summary: Optional[str] = None
    body: str
    mandatory: bool = True
    active: bool = True


class DocumentPatch(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    body: Optional[str] = None
    mandatory: Optional[bool] = None
    active: Optional[bool] = None


@admin_router.post("/documents")
async def create_document(payload: DocumentPayload, user=Depends(get_current_user)):
    _require_super(user)
    if payload.type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Tip invalid. Permis: {sorted(ALLOWED_TYPES)}")
    existing = await db.legal_documents.find_one({"type": payload.type, "version": payload.version})
    if existing:
        raise HTTPException(409, f"Există deja {payload.type} v{payload.version}.")
    # Deactivate previous versions of the same type when a new one becomes active
    if payload.active:
        await db.legal_documents.update_many(
            {"type": payload.type, "active": True},
            {"$set": {"active": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
    doc = {
        **payload.dict(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": user.get("email"),
    }
    res = await db.legal_documents.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _doc_out(doc)


@admin_router.patch("/documents/{doc_id}")
async def patch_document(doc_id: str, payload: DocumentPatch, user=Depends(get_current_user)):
    _require_super(user)
    try:
        oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "ID invalid.")
    update = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await db.legal_documents.find_one_and_update({"_id": oid}, {"$set": update}, return_document=True)
    if not res:
        raise HTTPException(404, "Document inexistent.")
    return _doc_out(res)


@admin_router.post("/seed")
async def reseed_defaults(user=Depends(get_current_user)):
    """Re-runs the seeder for default templates (idempotent)."""
    _require_super(user)
    return await seed_default_legal_documents()


@admin_router.get("/audit")
async def audit_contracts(
    user=Depends(get_current_user),
    only_non_compliant: bool = False,
):
    """Returns compliance audit per IT collaborator.

    For each active IT collaborator, lists all required docs + signed/pending state.
    """
    _require_super(user)
    docs = await _active_mandatory_documents()
    required_types = [d["type"] for d in docs]
    doc_by_type = {d["type"]: d for d in docs}

    collabs = []
    async for c in db.it_collaborators.find({"status": {"$ne": "archived"}}):
        email = (c.get("email") or "").lower()
        signed_map = {}
        cur = db.collaborator_contracts.find({"user_email": email, "status": "accepted"})
        async for sc in cur:
            signed_map[sc["document_type"]] = sc
        per_doc = []
        compliant = True
        for t in required_types:
            sc = signed_map.get(t)
            current_v = doc_by_type[t].get("version")
            if not sc:
                compliant = False
                per_doc.append({"type": t, "status": "missing", "title": doc_by_type[t]["title"]})
            elif sc.get("document_version") != current_v:
                compliant = False
                per_doc.append({
                    "type": t, "status": "outdated",
                    "title": doc_by_type[t]["title"],
                    "signed_version": sc.get("document_version"),
                    "current_version": current_v,
                    "signed_at": sc.get("accepted_at"),
                })
            else:
                per_doc.append({
                    "type": t, "status": "ok",
                    "title": doc_by_type[t]["title"],
                    "version": current_v,
                    "signed_at": sc.get("accepted_at"),
                })
        row = {
            "collaborator_id": str(c.get("_id")),
            "name": c.get("name"),
            "email": email,
            "role": c.get("role"),
            "seniority": c.get("seniority"),
            "status": c.get("status"),
            "compliant": compliant,
            "documents": per_doc,
        }
        if only_non_compliant and compliant:
            continue
        collabs.append(row)
    return {"items": collabs, "count": len(collabs), "required_types": required_types}


@admin_router.get("/contracts/{user_email}")
async def get_user_contracts(user_email: str, user=Depends(get_current_user)):
    """Get ALL contracts (any status) for a given user email."""
    _require_super(user)
    cur = db.collaborator_contracts.find({"user_email": user_email.lower()}).sort("accepted_at", -1)
    items = []
    async for c in cur:
        # fetch doc for title
        doc = None
        if c.get("document_id"):
            doc = await db.legal_documents.find_one({"_id": c["document_id"]})
        items.append(_contract_out(c, doc))
    return {"items": items, "count": len(items)}
