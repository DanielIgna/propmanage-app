"""Cross-session Persistent Memory.

Stores "memorable facts" per (user_id, scope) so any AI agent can recall them
across separate sessions. Uses MongoDB collection `ai_memories` with simple
TF-IDF-ish relevance scoring (no external vector DB needed at this scale).

GDPR: every memory is tagged with user_id; admin endpoints allow per-user reset.
"""
import re
import uuid
import logging
import math
from collections import Counter
from datetime import datetime, timezone, timedelta

from db import db
from ai_core.provider import call_llm, ecosystem_enabled

logger = logging.getLogger("propmanage.ai_core.memory")

SCOPES = ("concierge", "qa_copilot", "client_agent", "admin_agent", "tech_agent")
_STOPWORDS = set(
    "a si sau de la cu pe in la ca nu un o este sunt era pentru cele cei "
    "the and or of to a in is are was for from by with on at as it that".split()
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DIACRITICS = str.maketrans("ăâîșțĂÂÎȘȚ", "aaistAAIST")
_RO_SUFFIXES = ("ului", "elor", "ilor", "lor", "ele", "ile", "uri", "lui", "ul", "ii", "ea", "ie", "ia")


def _stem(token: str) -> str:
    """Light Romanian stemmer — strip common suffixes if word stays >= 4 chars."""
    if len(token) <= 5:
        return token
    for suf in _RO_SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[:-len(suf)]
    return token


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    text = text.translate(_DIACRITICS)
    toks = re.findall(r"[a-zA-Z0-9]{3,}", text.lower())
    return [_stem(t) for t in toks if t not in _STOPWORDS]


def _score(query_tokens: set, memory_tokens_counter: Counter) -> float:
    if not query_tokens or not memory_tokens_counter:
        return 0.0
    total = sum(memory_tokens_counter.values())
    score = 0.0
    for t in query_tokens:
        tf = memory_tokens_counter.get(t, 0)
        if tf == 0:
            continue
        score += math.log(1 + tf) * (1.0 / math.log(1 + total))
    return score


async def remember(*, user_id, scope, content, summary=None, source=None, ttl_days=180):
    if not await ecosystem_enabled():
        return None
    if not (user_id and content and scope in SCOPES):
        return None
    summary = (summary or content)[:280]
    doc = {
        "id": uuid.uuid4().hex,
        "user_id": str(user_id),
        "scope": scope,
        "content": content[:4000],
        "summary": summary,
        "tokens": _tokenize(content),
        "source": source or scope,
        "created_at": _now_iso(),
        "expires_at": ((datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat() if ttl_days else None),
    }
    try:
        await db.ai_memories.insert_one(doc)
    except Exception as e:
        logger.warning(f"[memory.remember] {e}")
        return None
    return {"id": doc["id"]}


async def recall(*, user_id, query, scope=None, limit=5):
    if not await ecosystem_enabled():
        return []
    if not user_id:
        return []
    flt = {"user_id": str(user_id)}
    if scope:
        flt["scope"] = scope
    flt["$or"] = [{"expires_at": None}, {"expires_at": {"$gt": _now_iso()}}]
    query_tokens = set(_tokenize(query))
    candidates = []
    cursor = db.ai_memories.find(flt).sort("created_at", -1).limit(200)
    async for m in cursor:
        toks_counter = Counter(m.get("tokens") or [])
        s = _score(query_tokens, toks_counter)
        if s > 0:
            candidates.append((s, m))
    candidates.sort(key=lambda x: x[0], reverse=True)
    out = []
    for score, m in candidates[:limit]:
        out.append({
            "id": m["id"],
            "scope": m["scope"],
            "summary": m.get("summary") or m.get("content", "")[:280],
            "content": m.get("content", ""),
            "source": m.get("source"),
            "score": round(score, 3),
            "created_at": m.get("created_at"),
        })
    return out


_EXTRACT_PROMPT = """You are a memory-extractor for an AI assistant working on a property management platform (PropManage Romania).
Given a conversation snippet between user and AI, extract 0-3 atomic facts about the user that would be useful
in FUTURE conversations: preferences, properties they own, problems they've reported, decisions they made,
specialists they liked, budgets, deadlines, etc.

Return STRICT JSON only (no markdown):
{"facts": ["fact 1 in Romanian, max 200 chars", "fact 2", ...]}

Skip generic chitchat. Skip already-obvious info. Skip sensitive data (CNP, IBAN, passwords).
If nothing memorable, return {"facts": []}."""


def _parse_facts(text: str) -> list:
    """Parse the LLM response (strict JSON, possibly fenced in markdown) into a
    list of fact strings. Returns [] on any parse failure."""
    import json
    try:
        t = text.strip()
        if t.startswith("```"):
            t = t.split("```", 2)[1] if t.count("```") >= 2 else t[3:]
            if t.startswith("json"):
                t = t[4:]
            t = t.rsplit("```", 1)[0].strip()
        parsed = json.loads(t)
        return parsed.get("facts") or []
    except Exception:
        return []


async def _store_facts(facts: list, *, user_id, scope, source) -> int:
    """Persist up to 5 extracted facts as memories. Returns stored count."""
    n = 0
    for f in facts[:5]:
        if not f or not isinstance(f, str):
            continue
        ok = await remember(user_id=user_id, scope=scope, content=f, summary=f[:200], source=source)
        if ok:
            n += 1
    return n


async def extract_and_remember(*, user_id, scope, conversation_text, source=None):
    if not await ecosystem_enabled():
        return 0
    if not (user_id and conversation_text and scope in SCOPES):
        return 0
    res = await call_llm(
        system_message=_EXTRACT_PROMPT,
        user_message=conversation_text[:8000],
        session_id=f"mem-extract-{uuid.uuid4().hex[:6]}",
    )
    text = res.get("text") or ""
    if res.get("error") or not text:
        return 0
    facts = _parse_facts(text)
    if not facts:
        return 0
    return await _store_facts(facts, user_id=user_id, scope=scope, source=source)


async def list_user_memories(user_id, limit=50):
    cur = db.ai_memories.find({"user_id": str(user_id)}).sort("created_at", -1).limit(int(limit))
    out = []
    async for m in cur:
        out.append({
            "id": m["id"],
            "scope": m["scope"],
            "summary": m.get("summary", ""),
            "source": m.get("source"),
            "created_at": m.get("created_at"),
            "expires_at": m.get("expires_at"),
        })
    return out


async def delete_memory(memory_id):
    res = await db.ai_memories.delete_one({"id": memory_id})
    return res.deleted_count > 0


async def reset_user_memories(user_id):
    res = await db.ai_memories.delete_many({"user_id": str(user_id)})
    return res.deleted_count


async def stats():
    total = await db.ai_memories.count_documents({})
    by_scope = {}
    for s in SCOPES:
        by_scope[s] = await db.ai_memories.count_documents({"scope": s})
    return {"total": total, "by_scope": by_scope, "scopes_known": list(SCOPES)}
