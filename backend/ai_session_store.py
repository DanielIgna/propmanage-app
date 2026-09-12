"""ai_session_store — memoria AI unificată (Sprint 2 · 2.3).

Colecția `ai_sessions` {session_id, agent, user_id?, messages[], tenant_id} — agregatorul
tuturor conversațiilor AI. Legacy-ul rămâne motorul per modul (zero risc pe fluxuri live);
sincronizarea rulează periodic (cron 30 min) și e idempotentă ($set complet per sesiune).
Val 2 (viitor): modulele trec pe citire directă din ai_sessions.
"""
import logging
from datetime import datetime, timezone

from db import db

from tenancy import DEFAULT_TENANT as TENANT

logger = logging.getLogger("propmanage.ai_session_store")


async def _upsert_session(agent: str, session_id: str, messages: list, user_id: str = None, created_at: str = None) -> None:
    await db.ai_sessions.update_one(
        {"agent": agent, "session_id": session_id},
        {"$set": {"messages": messages, "user_id": user_id, "tenant_id": TENANT,
                  "updated_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"created_at": created_at or datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )


async def sync_all() -> dict:
    """Idempotent: reconstruiește ai_sessions din cele 4 surse legacy."""
    out = {}
    # 1. concierge_messages: un doc per mesaj → grupare pe session_id
    sessions: dict[str, dict] = {}
    async for m in db.concierge_messages.find({}).sort("created_at", 1):
        sid = m.get("session_id") or "unknown"
        s = sessions.setdefault(sid, {"messages": [], "user_id": m.get("user_id"), "created_at": m.get("created_at")})
        s["messages"].append({"role": m.get("role", "user"), "content": m.get("content", ""), "ts": m.get("created_at")})
    for sid, s in sessions.items():
        await _upsert_session("concierge", sid, s["messages"], s["user_id"], s["created_at"])
    out["concierge"] = len(sessions)

    # 2. marketing_chat_sessions + interior_assistant_sessions: deja session-shaped
    for agent, col in (("marketing", "marketing_chat_sessions"), ("interior_design", "interior_assistant_sessions")):
        n = 0
        async for s in db[col].find({}):
            sid = s.get("session_id") or str(s.get("_id"))
            await _upsert_session(agent, sid, s.get("messages") or [], s.get("user_id"), s.get("created_at"))
            n += 1
        out[agent] = n

    # 3. twin_conversations: Q&A per doc → o sesiune per twin
    twin_sessions: dict[str, dict] = {}
    async for q in db.twin_conversations.find({}).sort("asked_at", 1):
        tid = str(q.get("twin_id") or "general")
        s = twin_sessions.setdefault(tid, {"messages": [], "user_id": q.get("user_id"), "created_at": q.get("asked_at")})
        s["messages"].append({"role": "user", "content": q.get("question", ""), "ts": q.get("asked_at")})
        s["messages"].append({"role": "assistant", "content": q.get("answer", ""), "ts": q.get("asked_at")})
    for tid, s in twin_sessions.items():
        await _upsert_session("twin_qa", f"twin_{tid}", s["messages"], s["user_id"], s["created_at"])
    out["twin_qa"] = len(twin_sessions)
    return out


async def list_sessions(agent: str = None, user_id: str = None, limit: int = 100) -> list:
    q = {}
    if agent:
        q["agent"] = agent
    if user_id:
        q["user_id"] = user_id
    return await db.ai_sessions.find(q, {"_id": 0}).sort("updated_at", -1).to_list(limit)


async def gdpr_delete_user(user_id: str) -> int:
    r = await db.ai_sessions.delete_many({"user_id": user_id})
    return r.deleted_count
