"""Document Intelligence — Phase 3 of AI Ecosystem.

Lets users upload PDF/DOCX/TXT documents (contracts, invoices, regulations, etc.).
Documents are:
  1. Extracted to plain text
  2. Chunked (~800 chars each)
  3. Stored in `ai_documents` (metadata) and `ai_doc_chunks` (chunks with TF-IDF tokens)
  4. Retrievable via semantic search for RAG-style Q&A

For Phase 3 MVP we use BM25-style scoring on tokenized chunks (no external
vector DB). At scale (>50k chunks) we'd migrate to Qdrant / Mongo Atlas Vector.

GDPR: every doc tagged with owner_user_id; admin can reset per-user.
"""
import io
import re
import uuid
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from deps import get_current_user, require_role
from db import db
from ai_core.provider import call_llm, ecosystem_enabled
from ai_core.memory import _tokenize, _score
from ai_core import memory as ai_memory

logger = logging.getLogger("propmanage.docs_ai")

router = APIRouter(prefix="/api/ai-docs", tags=["ai-docs"])

CHUNK_SIZE = 800
import storage_service  # noqa: E402 — ST-001: limită dinamică din storage_configs
SUPPORTED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + size, len(text))
        # Try to end at a sentence boundary
        if end < len(text):
            dot = text.rfind(". ", i, end)
            if dot > i + size // 2:
                end = dot + 2
        chunks.append(text[i:end].strip())
        i = end
    return [c for c in chunks if c]


def _extract_text(content: bytes, kind: str) -> str:
    """Extract plain text. Returns "" on any failure (graceful)."""
    try:
        if kind in ("txt", "md"):
            return content.decode("utf-8", errors="ignore")
        if kind == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content))
                return "\n\n".join((p.extract_text() or "") for p in reader.pages)
            except ImportError:
                logger.warning("[docs_ai] pypdf not installed; PDF text not extracted")
                return ""
        if kind == "docx":
            try:
                from docx import Document
                d = Document(io.BytesIO(content))
                return "\n\n".join(p.text for p in d.paragraphs if p.text.strip())
            except ImportError:
                logger.warning("[docs_ai] python-docx not installed; DOCX not extracted")
                return ""
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[docs_ai.extract] {kind} failed: {e}")
    return ""


# ---------- Schemas ----------
class AskDocIn(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    doc_id: Optional[str] = None  # If set, limit search to this document
    top_k: int = Field(default=4, ge=1, le=10)
    inline_context: Optional[str] = Field(default=None, max_length=40000)
    inline_context_label: Optional[str] = Field(default=None, max_length=100)


# ---------- Endpoints ----------
@router.post("/upload")
async def upload_doc(
    file: UploadFile = File(...),
    title: str = Form(default=""),
    user: dict = Depends(get_current_user),
):
    """Upload + extract + chunk + index a document. Returns metadata + chunk count."""
    if not await ecosystem_enabled():
        raise HTTPException(503, "AI Ecosystem is disabled. Enable from /admin/ai-control.")

    ctype = file.content_type or ""
    kind = SUPPORTED_TYPES.get(ctype)
    if not kind:
        raise HTTPException(400, f"Unsupported type {ctype}. Allowed: PDF, DOCX, TXT, MD")

    content = await file.read()
    limit = await storage_service.file_limit_bytes("docs_ai")
    if len(content) > limit:
        raise HTTPException(413, f"File too large ({len(content) // 1024 // 1024} MB > {limit // 1024 // 1024} MB max)")
    await storage_service.check_quota(user.get("id"), len(content), "personal")

    text = _extract_text(content, kind)
    if not text or len(text.strip()) < 20:
        raise HTTPException(422, "Could not extract usable text from this file.")

    chunks = _chunk_text(text)
    doc_id = uuid.uuid4().hex

    doc_meta = {
        "id": doc_id,
        "owner_user_id": user.get("id"),
        "owner_email": user.get("email"),
        "title": (title or file.filename or "Document").strip()[:200],
        "filename": file.filename,
        "kind": kind,
        "size_bytes": len(content),
        "chunk_count": len(chunks),
        "char_count": len(text),
        "created_at": _now_iso(),
    }
    await db.ai_documents.insert_one(doc_meta)
    await storage_service.add_usage(user.get("id"), len(content), "personal")

    # Index chunks
    chunk_docs = []
    for i, c in enumerate(chunks):
        chunk_docs.append({
            "id": uuid.uuid4().hex,
            "doc_id": doc_id,
            "owner_user_id": user.get("id"),
            "owner_email": user.get("email"),
            "idx": i,
            "text": c,
            "tokens": _tokenize(c),
            "created_at": _now_iso(),
        })
    if chunk_docs:
        await db.ai_doc_chunks.insert_many(chunk_docs)

    doc_meta.pop("_id", None)
    return doc_meta


@router.get("/list")
async def list_docs(limit: int = 50, user: dict = Depends(get_current_user)):
    """List documents owned by the current user (admin sees all)."""
    flt = {} if user.get("role") == "admin" else {"owner_user_id": user.get("id")}
    cur = db.ai_documents.find(flt).sort("created_at", -1).limit(int(limit))
    items = []
    async for d in cur:
        d.pop("_id", None)
        items.append(d)
    return {"items": items, "total": len(items)}


@router.delete("/{doc_id}")
async def delete_doc(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.ai_documents.find_one({"id": doc_id})
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.get("owner_user_id") != user.get("id") and user.get("role") != "admin":
        raise HTTPException(403, "Access denied")
    await db.ai_doc_chunks.delete_many({"doc_id": doc_id})
    await db.ai_documents.delete_one({"id": doc_id})
    await storage_service.add_usage(doc.get("owner_user_id"), -(doc.get("size_bytes") or 0), "personal")
    return {"deleted": True}


@router.post("/ask")
async def ask_docs(payload: AskDocIn, user: dict = Depends(get_current_user)):
    """RAG-style Q&A over user's documents.

    Steps:
      1. Tokenize question.
      2. Score all chunks (filtered by owner) using BM25-like scoring.
      3. Take top_k chunks.
      4. Build a prompt with chunks as context, ask Claude.
      5. Return answer + sources.
    """
    if not await ecosystem_enabled():
        return {"answer": "Ecosistemul AI este dezactivat.", "sources": []}

    # ---- inline-context mode ----
    # When caller passes `inline_context` (e.g. Admin Manual injection from the
    # Docs page), skip RAG over user docs and answer strictly from that text.
    if payload.inline_context:
        label = payload.inline_context_label or "Manual Admin PropManage"
        system = (
            "You are PropManage's admin assistant. Answer in Romanian, "
            f"using ONLY the provided '{label}' text as source of truth. "
            "If the answer is NOT explicitly in the text, reply: "
            "'Nu am găsit informația în manual. Întreabă echipa de dezvoltare.' "
            "Be concise (max 6 propoziții), friendly, no jargon. "
            "When you quote a section, mention its title in italic (ex: *Autonomy Engine*)."
        )
        user_msg = (
            f"## {label}\n{payload.inline_context}\n\n"
            f"## Întrebare admin\n{payload.question}"
        )
        result = await call_llm(system, user_msg, session_id=f"manual-{uuid.uuid4().hex[:6]}")
        answer = result.get("text") or "Nu am putut răspunde acum."
        return {
            "answer": answer,
            "sources": [{"doc_title": label, "kind": "inline_manual"}],
            "provider": result.get("provider"),
            "model": result.get("model"),
            "mode": "inline_context",
        }
    # ---- end inline-context mode ----

    query_tokens = set(_tokenize(payload.question))
    if not query_tokens:
        raise HTTPException(400, "Question too short or unsearchable")

    flt = {"owner_user_id": user.get("id")} if user.get("role") != "admin" else {}
    if payload.doc_id:
        flt["doc_id"] = payload.doc_id

    # Score chunks
    scored = []
    cur = db.ai_doc_chunks.find(flt).limit(2000)
    async for ch in cur:
        toks = Counter(ch.get("tokens") or [])
        s = _score(query_tokens, toks)
        if s > 0:
            scored.append((s, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: payload.top_k]

    if not top:
        return {
            "answer": "Nu am găsit informații relevante în documentele tale pentru această întrebare. Încarcă documente mai întâi sau formulează altfel întrebarea.",
            "sources": [],
        }

    # Build context with source markers
    context_parts = []
    sources = []
    for s, ch in top:
        doc = await db.ai_documents.find_one({"id": ch["doc_id"]}, {"title": 1, "_id": 0})
        title = doc.get("title", "Document") if doc else "Document"
        marker = f"[Sursa: {title}, fragment #{ch['idx']}]"
        context_parts.append(f"{marker}\n{ch['text']}")
        sources.append({"doc_id": ch["doc_id"], "doc_title": title, "chunk_idx": ch["idx"], "score": round(s, 3)})

    system = (
        "You are an expert document analyst for PropManage. Answer in Romanian. "
        "Use ONLY the provided document fragments to answer. Cite source markers like [Sursa: ..., fragment #N]. "
        "If the answer is NOT in the fragments, say: 'Nu am găsit informația în documentele încărcate.' "
        "Never invent facts or numbers."
    )
    user_msg = "## Document fragments\n" + "\n\n---\n\n".join(context_parts) + f"\n\n## Question\n{payload.question}"

    result = await call_llm(system, user_msg, session_id=f"docs-rag-{uuid.uuid4().hex[:6]}")
    answer = result.get("text") or "Nu am putut răspunde acum."
    if result.get("error"):
        logger.warning(f"[docs_ai.ask] LLM error: {result['error']}")

    # Persist a memory of useful Q&A
    try:
        await ai_memory.remember(
            user_id=user.get("email") or user.get("id"),
            scope="client_agent",
            content=f"Doc Q '{payload.question[:140]}' → {answer[:200]}",
            summary=f"Doc Q: {payload.question[:200]}",
            source="docs_ai",
        )
    except Exception:  # noqa: BLE001
        pass

    return {"answer": answer, "sources": sources, "provider": result.get("provider"), "model": result.get("model")}


@router.get("/stats")
async def stats(user: dict = Depends(require_role("admin"))):
    total_docs = await db.ai_documents.count_documents({})
    total_chunks = await db.ai_doc_chunks.count_documents({})
    by_kind = {}
    for k in SUPPORTED_TYPES.values():
        by_kind[k] = await db.ai_documents.count_documents({"kind": k})
    return {"total_documents": total_docs, "total_chunks": total_chunks, "by_kind": by_kind}
