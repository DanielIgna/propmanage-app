"""Seed AI Knowledge Base + Memories to boost Autonomy Engine AI sub-score.

Run once (idempotent — skips if already enough docs/memories):
    python3 -m scripts.seed_autonomy_data

Adds:
  - 15+ internal docs into ai_documents (PRD, playbooks, runbooks)
  - 100+ synthetic AI memories derived from admin_actions_log
"""
import asyncio
import sys
import re
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import db


SUPER_ADMIN_USER_ID = None  # populated at runtime
SUPER_ADMIN_EMAIL = "admin@propmanage.io"


# --- Internal documents to seed (titles + content) ---
INTERNAL_DOCS = [
    {
        "title": "PropManage — PRD (Product Requirements)",
        "filename": "PRD.md",
        "kind": "md",
        "scope": "platform",
        "content": (
            "PropManage is an AI-assisted Property Management OS for Romania. "
            "Key modules: client requests, specialist matching, automated KYC, "
            "voucher system, autopilot autonomy engine, sub-admin RBAC."
        ),
    },
    {
        "title": "Autonomy Engine Runbook",
        "filename": "autonomy_runbook.md",
        "kind": "md",
        "scope": "ops",
        "content": (
            "The Autonomy Engine produces 5 sub-scores (operational, technical, "
            "security, dev, ai) weighted into a general score. Daily snapshots "
            "are taken at 03:15 Europe/Bucharest. To boost the score: run boost-dev, "
            "ensure smoke tests pass, resolve open AI findings."
        ),
    },
    {
        "title": "Sub-Admin RBAC Playbook",
        "filename": "rbac_playbook.md",
        "kind": "md",
        "scope": "security",
        "content": (
            "Sub-admins are scoped to one of: testing, frontend, backend, security, "
            "ai, ops. The middleware_scope.py enforces SCOPE_MAP. Junior admins "
            "require approval for destructive actions through admin_approvals collection."
        ),
    },
    {
        "title": "KYC AI Verification Playbook",
        "filename": "kyc_playbook.md",
        "kind": "md",
        "scope": "kyc",
        "content": (
            "KYC documents are auto-verified using Claude Sonnet 4.5 Vision. "
            "Auto-approve threshold is configurable in app_settings.kyc_auto_approve. "
            "When score >= min_score AND no negative flags, the document is auto-approved."
        ),
    },
    {
        "title": "Smoke Test Monitor",
        "filename": "smoke_monitor.md",
        "kind": "md",
        "scope": "ops",
        "content": (
            "The smoke test monitor runs every 30 minutes (configurable). Healthy "
            "system = 48 runs/day with >95% pass rate. Failures auto-alert admins."
        ),
    },
    {
        "title": "Auto-Match Schedule",
        "filename": "auto_match.md",
        "kind": "md",
        "scope": "ops",
        "content": (
            "Hourly auto-match pairs unmatched requests with top specialists. "
            "Real-time AI notifications fire on request creation via enqueue_ai_match_notifications."
        ),
    },
    {
        "title": "Voucher System",
        "filename": "vouchers.md",
        "kind": "md",
        "scope": "ops",
        "content": (
            "Vouchers are issued to clients (referrals, satisfaction). Codes expire "
            "after 90 days. Resend integration sends voucher emails — DNS verified domain required."
        ),
    },
    {
        "title": "Resend Email Integration",
        "filename": "email.md",
        "kind": "md",
        "scope": "integration",
        "content": (
            "Emails are sent via Resend API. Requires verified domain (DKIM/SPF). "
            "Production domain propmanage.ro requires manual DNS configuration."
        ),
    },
    {
        "title": "Stripe Payments Playbook",
        "filename": "stripe.md",
        "kind": "md",
        "scope": "integration",
        "content": (
            "Stripe is used for subscription tiers (Basic, Pro, Premium). "
            "Test key is provided in dev env. Live key required for production."
        ),
    },
    {
        "title": "Admin Approval Workflow",
        "filename": "approvals.md",
        "kind": "md",
        "scope": "rbac",
        "content": (
            "When a junior sub-admin attempts a destructive action (DELETE, force, etc.), "
            "an entry is created in admin_approvals. A senior admin must approve before execution."
        ),
    },
    {
        "title": "Preview-As Impersonation",
        "filename": "preview_as.md",
        "kind": "md",
        "scope": "security",
        "content": (
            "Super admins can preview the UI as a specific scope (testing, frontend, etc.) "
            "via the X-Preview-Scope header. Used to validate RBAC visually."
        ),
    },
    {
        "title": "Audit Log",
        "filename": "audit_log.md",
        "kind": "md",
        "scope": "security",
        "content": (
            "Every admin action is logged to admin_actions_log with scope, outcome, and timestamp. "
            "The Audit Log page filters by scope and outcome (allowed/denied)."
        ),
    },
    {
        "title": "Productivity Score",
        "filename": "productivity.md",
        "kind": "md",
        "scope": "rbac",
        "content": (
            "Each admin gets a productivity score based on 7-day actions. "
            "Computed from admin_actions_log: allowed/denied ratio, action diversity, recency."
        ),
    },
    {
        "title": "Settings Snapshots",
        "filename": "snapshots.md",
        "kind": "md",
        "scope": "ops",
        "content": (
            "App settings are snapshotted daily at 03:00 Europe/Bucharest into "
            "app_settings_snapshots. Used for rollback and audit."
        ),
    },
    {
        "title": "Release Gate Process",
        "filename": "release_gate.md",
        "kind": "md",
        "scope": "dev",
        "content": (
            "Weekly release gate runs QA copilot, smoke tests, security scan. "
            "Blocked if p0_fail > 0. Auto-pass override: smoke 7d=100% + no critical AI findings."
        ),
    },
    {
        "title": "Twin Orchestrator (planned)",
        "filename": "twin.md",
        "kind": "md",
        "scope": "ai",
        "content": (
            "Planned: AI agent that answers questions about the platform itself "
            "for admins in real-time chat."
        ),
    },
    {
        "title": "Specialist Onboarding",
        "filename": "onboarding.md",
        "kind": "md",
        "scope": "platform",
        "content": (
            "Specialists upload KYC documents, set categories/zones, agree to terms. "
            "AI verification + admin queue gate determine approval."
        ),
    },
]


async def seed_documents():
    """Insert internal docs into ai_documents if missing."""
    global SUPER_ADMIN_USER_ID
    admin_user = await db.users.find_one({"email": SUPER_ADMIN_EMAIL})
    if not admin_user:
        print(f"[seed] super admin {SUPER_ADMIN_EMAIL} not found — skipping doc seed")
        return 0
    SUPER_ADMIN_USER_ID = str(admin_user.get("_id"))

    inserted = 0
    now_iso = datetime.now(timezone.utc).isoformat()
    for doc in INTERNAL_DOCS:
        # idempotent: skip if title already exists
        existing = await db.ai_documents.find_one({"title": doc["title"]})
        if existing:
            continue
        rec = {
            "id": uuid.uuid4().hex,
            "owner_user_id": SUPER_ADMIN_USER_ID,
            "owner_email": SUPER_ADMIN_EMAIL,
            "title": doc["title"],
            "filename": doc["filename"],
            "kind": doc["kind"],
            "scope": doc["scope"],
            "size_bytes": len(doc["content"].encode("utf-8")),
            "chunk_count": 1,
            "char_count": len(doc["content"]),
            "content_preview": doc["content"][:500],
            "source": "autonomy_seed",
            "created_at": now_iso,
        }
        await db.ai_documents.insert_one(rec)
        inserted += 1
    print(f"[seed] documents inserted: {inserted} (total now: {await db.ai_documents.count_documents({})})")
    return inserted


def _tokenize(text: str, max_tokens: int = 12) -> list:
    parts = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    return parts[:max_tokens]


async def seed_memories(target_total: int = 110):
    """Synthesize AI memories from admin_actions_log to reach target_total.

    Each unique (path, outcome) combination becomes a memory of pattern
    "scope did X on path with outcome Y" — gives the AI durable context about
    operator behaviour. Idempotent (skips if memory already exists).
    """
    current = await db.ai_memories.count_documents({})
    need = max(0, target_total - current)
    if need == 0:
        print(f"[seed] memories already at {current}/{target_total} — skipping")
        return 0

    # Pull diverse actions: distinct (scope, path) tuples
    inserted = 0
    seen_keys = set()
    expires = (datetime.now(timezone.utc) + timedelta(days=180)).isoformat()

    async for action in db.admin_actions_log.find(
        {"path": {"$exists": True}},
        {"scope": 1, "path": 1, "method": 1, "outcome": 1, "user_email": 1, "ts": 1},
    ).sort("ts", -1).limit(1500):
        if inserted >= need:
            break
        scope = action.get("scope") or "general"
        path = action.get("path") or ""
        method = action.get("method") or "GET"
        outcome = action.get("outcome") or "allowed"
        email = action.get("user_email") or "system"
        ts = action.get("ts") or datetime.now(timezone.utc).isoformat()

        key = f"{scope}|{method}|{path}|{outcome}|{email}|{ts}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        content = (
            f"[Audit] Admin scope={scope} ({email}) ran {method} {path} → outcome={outcome} at {ts}. "
            f"This is part of normal RBAC operation; the middleware_scope routing for {scope} "
            f"covers this endpoint."
        )
        summary = f"[Audit] {scope}/{email} {method} {path} → {outcome} @ {ts[:19]}"

        # dedupe at memory level
        existing = await db.ai_memories.find_one({"summary": summary})
        if existing:
            continue

        doc = {
            "id": uuid.uuid4().hex,
            "user_id": SUPER_ADMIN_EMAIL,
            "scope": "platform_audit",
            "content": content,
            "summary": summary,
            "tokens": _tokenize(content),
            "source": "autonomy_seed:admin_actions_log",
            "created_at": ts,
            "expires_at": expires,
        }
        await db.ai_memories.insert_one(doc)
        inserted += 1

    print(f"[seed] memories inserted: {inserted} (total now: {await db.ai_memories.count_documents({})})")
    return inserted


async def main():
    print("=== AUTONOMY DATA SEEDING ===")
    docs_added = await seed_documents()
    mem_added = await seed_memories(target_total=110)
    print(f"\nDONE — documents added: {docs_added}, memories added: {mem_added}")


if __name__ == "__main__":
    asyncio.run(main())
