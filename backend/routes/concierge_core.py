"""PropManage — AI Concierge shared core: PII redaction, safety filters, rate limit, settings."""
import os
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import db

logger = logging.getLogger("propmanage.concierge.core")

# ============= PII REDACTION =============
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(r"(?<!\w)(\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}(?!\w)")
IBAN_REGEX = re.compile(r"\bRO\d{2}[A-Z]{4}\d{16}\b", re.IGNORECASE)
CNP_REGEX = re.compile(r"\b[1-8]\d{12}\b")


def _redact_pii(text: str) -> str:
    if not text:
        return text
    text = EMAIL_REGEX.sub("[email redactat]", text)
    text = IBAN_REGEX.sub("[IBAN redactat]", text)
    text = CNP_REGEX.sub("[CNP redactat]", text)

    def _phone_repl(m):
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) >= 9:
            return "[telefon redactat]"
        return m.group(0)
    text = PHONE_REGEX.sub(_phone_repl, text)
    return text


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
DEFAULT_MODEL_PROVIDER = "anthropic"
DEFAULT_MODEL_NAME = "claude-sonnet-4-6"


# ============= SAFETY FILTERS =============
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|messages)",
    r"you\s+are\s+now\s+(a|an)\s+\w+(?!\s+(assistant|agent))",
    r"system\s*:\s*",
    r"</?\s*(system|admin|root|sudo)\s*>",
    r"reveal\s+(your\s+|the\s+)?(prompt|instructions|system\s+message|guidelines)",
    r"act\s+as\s+(a\s+)?(different|another)\s+\w+",
    r"pretend\s+(you\s+are|to\s+be)",
    r"roleplay\s+as",
    r"\bDAN\b|\bjailbreak\b",
    r"developer\s+mode",
    r"\\n\\nHuman:|\\n\\nAssistant:",
    r"<\|im_(start|end)\|>",
]

SENSITIVE_REQUEST_PATTERNS = [
    r"(d[aă][- ]?mi|arat[aă][- ]?mi|spune[- ]?mi)\s+(parola|password|token|api[ _-]?key|cheia)",
    r"(arat[aă]|listeaz[aă]|toți|toate)\s+(useri|utilizatori|clienți|specialiști|operatori)",
    r"care\s+(este|sunt)\s+(comisionul|marja|profitul|venitul)",
    r"(structur[aă]|schema)\s+(baz[aă]\s+date|database|db)",
    r"select\s+\*\s+from",
    r"drop\s+(table|database)",
    r"\bunion\s+select\b",
    r"<script[^>]*>",
    r"javascript:\s*",
    r"on(click|error|load)\s*=",
]

DEFAULT_ESCALATION_TRIGGERS = [
    "plângere", "reclamație", "reclamatie",
    "refund", "bani înapoi", "bani inapoi",
    "problemă legală", "problema legala", "instanță", "avocat", "tribunal",
    "ștergere cont", "stergere cont", "gdpr", "ștergeți contul",
    "hack", "spart cont", "fraudă", "frauda", "furat",
    "discriminare", "abuz", "hărțuire", "hartuire",
    "bug critic", "platforma nu funcționează", "platforma nu functioneaza",
]


def _check_prompt_injection(text: str) -> Optional[str]:
    low = text.lower()
    for p in PROMPT_INJECTION_PATTERNS:
        if re.search(p, low, re.IGNORECASE):
            return p
    return None


def _check_sensitive_request(text: str) -> Optional[str]:
    low = text.lower()
    for p in SENSITIVE_REQUEST_PATTERNS:
        if re.search(p, low, re.IGNORECASE):
            return p
    return None


def _check_escalation(text: str, triggers: list) -> Optional[str]:
    low = text.lower()
    for t in triggers:
        if t.lower() in low:
            return t
    return None


async def _rate_limit_check(user_id: str, window_minutes: int = 5, max_messages: int = 30) -> bool:
    """Returns True if user is within limits, False if exceeded."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    count = await db.concierge_messages.count_documents({
        "user_id": user_id,
        "role": "user",
        "created_at": {"$gte": cutoff},
    })
    return count < max_messages


async def _record_block(user_id: str, user_role: str, message: str, reason: str, severity: str = "warning"):
    """Record a concierge block in admin_ai_findings for visibility."""
    composite_key = f"concierge_abuse::{user_id}::{reason[:50]}"
    existing = await db.admin_ai_findings.find_one({"composite_key": composite_key})
    now_iso = datetime.now(timezone.utc).isoformat()
    if existing:
        await db.admin_ai_findings.update_one(
            {"_id": existing["_id"]},
            {"$set": {"last_seen_at": now_iso, "context.last_message": message[:200]},
             "$inc": {"occurrences": 1}},
        )
    else:
        await db.admin_ai_findings.insert_one({
            "composite_key": composite_key,
            "pattern": "concierge_abuse_blocked",
            "label": f"Mesaj blocat concierge — {reason}",
            "severity": severity,
            "description": "Userul a încercat un mesaj suspect/prompt injection în chat",
            "entity_type": "user",
            "entity_id": user_id,
            "entity_label": f"{user_role} · {user_id[:8]}",
            "context": {"reason": reason, "last_message": message[:200], "user_role": user_role},
            "status": "open",
            "first_seen_at": now_iso,
            "last_seen_at": now_iso,
            "occurrences": 1,
        })


async def _get_settings() -> dict:
    doc = await db.concierge_settings.find_one({"_id": "global"})
    if not doc:
        return {
            "enabled_roles": ["client", "specialist", "operator"],
            "escalation_triggers": DEFAULT_ESCALATION_TRIGGERS,
            "support_email": os.environ.get("ADMIN_EMAIL", "support@propmanage.io"),
            "blocked_users": [],
        }
    return {
        "enabled_roles": doc.get("enabled_roles", ["client", "specialist", "operator"]),
        "escalation_triggers": doc.get("escalation_triggers", DEFAULT_ESCALATION_TRIGGERS),
        "support_email": doc.get("support_email", os.environ.get("ADMIN_EMAIL", "support@propmanage.io")),
        "blocked_users": doc.get("blocked_users", []),
    }
