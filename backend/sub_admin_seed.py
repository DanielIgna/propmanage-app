"""Seed 5 demo sub-admin accounts (idempotent, called from server startup).

Accounts created (all `is_demo_sub_admin: True`):
  - testing.admin@propmanage.io    / Test!Demo2026Strong   — scope: testing
  - frontend.admin@propmanage.io   / Front!Demo2026Strong  — scope: frontend
  - backend.admin@propmanage.io    / Back!Demo2026Strong   — scope: backend
  - security.admin@propmanage.io   / Sec!Demo2026Strong    — scope: security
  - marketing.admin@propmanage.io  / Mkt!Demo2026Strong    — scope: marketing (role: marketing_manager)

Super admin (admin@propmanage.io) can reset/change passwords via /api/admin/demo-accounts
using master code 0108.
"""
import logging
from datetime import datetime, timezone

import bcrypt

from db import db

logger = logging.getLogger("propmanage.sub_admin_seed")

# Default credentials (visible to super_admin in UI). Change here = changes the
# "reset to default" target. Keep these strong but memorable for demo recipients.
SUB_ADMINS = [
    {
        "email": "testing.admin@propmanage.io",
        "password": "Test!Demo2026Strong",
        "name": "Testing Admin",
        "role": "admin",
        "admin_scope": "testing",
        "admin_seniority": "senior",
    },
    {
        "email": "frontend.admin@propmanage.io",
        "password": "Front!Demo2026Strong",
        "name": "Frontend Admin",
        "role": "admin",
        "admin_scope": "frontend",
        "admin_seniority": "senior",
    },
    {
        "email": "backend.admin@propmanage.io",
        "password": "Back!Demo2026Strong",
        "name": "Backend Admin",
        "role": "admin",
        "admin_scope": "backend",
        "admin_seniority": "senior",
    },
    {
        "email": "security.admin@propmanage.io",
        "password": "Sec!Demo2026Strong",
        "name": "Security Admin",
        "role": "admin",
        "admin_scope": "security",
        "admin_seniority": "senior",
    },
    {
        "email": "general.admin@propmanage.io",
        "password": "Gen!Demo2026Strong",
        "name": "General Admin",
        "role": "admin",
        "admin_scope": "general",
        "admin_seniority": "senior",
    },
    {
        "email": "marketing.admin@propmanage.io",
        "password": "Mkt!Demo2026Strong",
        "name": "Marketing Admin",
        "role": "marketing_manager",
        "admin_scope": "marketing",
        "admin_seniority": "senior",
    },
]


def get_default_password(email: str) -> str | None:
    for spec in SUB_ADMINS:
        if spec["email"] == email:
            return spec["password"]
    return None


def list_demo_emails() -> list[str]:
    return [s["email"] for s in SUB_ADMINS]


async def seed_sub_admins() -> dict:
    created, updated, skipped = 0, 0, 0
    for spec in SUB_ADMINS:
        try:
            existing = await db.users.find_one({"email": spec["email"]})
            now_iso = datetime.now(timezone.utc).isoformat()
            if existing is None:
                pw_hash = bcrypt.hashpw(spec["password"].encode(), bcrypt.gensalt()).decode()
                doc = {
                    "email": spec["email"],
                    "name": spec["name"],
                    "role": spec["role"],
                    "admin_scope": spec["admin_scope"],
                    "admin_seniority": spec["admin_seniority"],
                    "password_hash": pw_hash,
                    "verified": True,
                    "email_verified": True,
                    "phone_verified": False,
                    "wallet_balance": 0,
                    "tokens": 0,
                    "tier": "",
                    "is_active": True,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                    "is_demo_sub_admin": True,
                    "consent_grandfathered": True,
                    "terms_accepted": True,
                    "privacy_policy_accepted": True,
                }
                await db.users.insert_one(doc)
                created += 1
            else:
                # Idempotent update: only patch scope/seniority/role; leave password alone
                patch = {}
                if existing.get("role") != spec["role"]:
                    patch["role"] = spec["role"]
                if existing.get("admin_scope") != spec["admin_scope"]:
                    patch["admin_scope"] = spec["admin_scope"]
                if existing.get("admin_seniority") != spec["admin_seniority"]:
                    patch["admin_seniority"] = spec["admin_seniority"]
                if not existing.get("is_demo_sub_admin"):
                    patch["is_demo_sub_admin"] = True
                if existing.get("is_active") is False:
                    patch["is_active"] = True
                if patch:
                    patch["updated_at"] = datetime.now(timezone.utc).isoformat()
                    await db.users.update_one({"_id": existing["_id"]}, {"$set": patch})
                    updated += 1
                else:
                    skipped += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[sub_admin_seed] failed for {spec['email']}: {e}")

    # Backfill super admin scope
    try:
        super_admin = await db.users.find_one({"email": "admin@propmanage.io"})
        if super_admin and not super_admin.get("admin_scope"):
            await db.users.update_one(
                {"_id": super_admin["_id"]},
                {"$set": {"admin_scope": "general", "admin_seniority": "senior"}},
            )
    except Exception:  # noqa: BLE001
        pass

    logger.info(f"[sub_admin_seed] created={created} updated={updated} skipped={skipped}")
    return {"created": created, "updated": updated, "skipped": skipped}
