"""
Tier-specific demo accounts for Admin QA testing.
Idempotent — only creates accounts that don't exist yet.
Allows the admin to test progressive disclosure at each tier level.
"""
import logging
from datetime import datetime, timezone

from db import db
from core_utils import hash_password, verify_password

logger = logging.getLogger(__name__)

# Tier-specific demo profiles
# Specialist tiers: ENTRY < JUNIOR < VERIFIED < ADVANCED < PREMIUM < TOP
# Client tiers: JUNIOR < VERIFIED < PREMIUM
TIER_DEMO_USERS = [
    # ===== CLIENTS =====
    {
        "email": "client.junior@propmanage.io",
        "password": "Demo123!",
        "name": "Andrei Junior (Client nou)",
        "role": "client",
        "tier": "JUNIOR",
        "wallet_balance": 0,
        "tokens": 100,
        "phone": "+40 712 000 001",
        "_seed_tag": "tier_demo_client_junior",
    },
    {
        "email": "client.verified@propmanage.io",
        "password": "Demo123!",
        "name": "Maria Verified (Client verificat)",
        "role": "client",
        "tier": "VERIFIED",
        "wallet_balance": 2000,
        "tokens": 1500,
        "phone": "+40 712 000 002",
        "kyc_status": "approved",
        "_seed_tag": "tier_demo_client_verified",
    },
    {
        "email": "client.premium@propmanage.io",
        "password": "Demo123!",
        "name": "Cristian Premium (Client de top)",
        "role": "client",
        "tier": "PREMIUM",
        "wallet_balance": 8500,
        "tokens": 5000,
        "phone": "+40 712 000 003",
        "kyc_status": "approved",
        "_seed_tag": "tier_demo_client_premium",
    },
    # ===== SPECIALISTS =====
    {
        "email": "spec.entry@propmanage.io",
        "password": "Demo123!",
        "name": "Ion ENTRY (Specialist nou, 0 joburi)",
        "role": "specialist",
        "tier": "ENTRY",
        "verified": False,
        "rating": None,
        "reviews_count": 0,
        "jobs_completed": 0,
        "wallet_balance": 0,
        "specialty": "hvac",
        "phone": "+40 723 000 001",
        "_seed_tag": "tier_demo_spec_entry",
    },
    {
        "email": "spec.junior@propmanage.io",
        "password": "Demo123!",
        "name": "Dragos JUNIOR (1-5 joburi)",
        "role": "specialist",
        "tier": "JUNIOR",
        "verified": False,
        "rating": 4.5,
        "reviews_count": 3,
        "jobs_completed": 3,
        "wallet_balance": 150,
        "specialty": "electric",
        "phone": "+40 723 000 002",
        "_seed_tag": "tier_demo_spec_junior",
    },
    {
        "email": "spec.verified@propmanage.io",
        "password": "Demo123!",
        "name": "Vlad VERIFIED (5+ joburi, KYC OK)",
        "role": "specialist",
        "tier": "VERIFIED",
        "verified": True,
        "rating": 4.7,
        "reviews_count": 8,
        "jobs_completed": 8,
        "wallet_balance": 400,
        "specialty": "plumbing",
        "phone": "+40 723 000 003",
        "_seed_tag": "tier_demo_spec_verified",
    },
    {
        "email": "spec.advanced@propmanage.io",
        "password": "Demo123!",
        "name": "Andrei ADVANCED (20+ joburi)",
        "role": "specialist",
        "tier": "ADVANCED",
        "verified": True,
        "rating": 4.8,
        "reviews_count": 25,
        "jobs_completed": 25,
        "wallet_balance": 1200,
        "specialty": "hvac",
        "phone": "+40 723 000 004",
        "_seed_tag": "tier_demo_spec_advanced",
    },
    {
        "email": "spec.premium@propmanage.io",
        "password": "Demo123!",
        "name": "Daniel PREMIUM (50+ joburi, rating ≥4.7)",
        "role": "specialist",
        "tier": "PREMIUM",
        "verified": True,
        "rating": 4.9,
        "reviews_count": 62,
        "jobs_completed": 62,
        "wallet_balance": 3200,
        "specialty": "interior_design",
        "phone": "+40 723 000 005",
        "_seed_tag": "tier_demo_spec_premium",
    },
    {
        "email": "spec.top@propmanage.io",
        "password": "Demo123!",
        "name": "Robert TOP (Top 5%, 100+ joburi)",
        "role": "specialist",
        "tier": "TOP",
        "verified": True,
        "rating": 5.0,
        "reviews_count": 138,
        "jobs_completed": 138,
        "wallet_balance": 6800,
        "specialty": "interior_design",
        "phone": "+40 723 000 006",
        "_seed_tag": "tier_demo_spec_top",
    },
]


async def seed_tier_demo_users():
    """Idempotent seed of tier-specific demo accounts for admin QA testing."""
    # Map new tier (Sprint A) -> legacy experience_tier (used by TierToolsPanel/QuestPanel)
    TIER_TO_EXPERIENCE = {
        "ENTRY": "junior",
        "JUNIOR": "junior",
        "VERIFIED": "verified",
        "ADVANCED": "verified",
        "PREMIUM": "pro",
        "TOP": "pro",
    }
    created = 0
    updated = 0
    for u in TIER_DEMO_USERS:
        experience_tier = TIER_TO_EXPERIENCE.get(u.get("tier"), "junior")
        existing = await db.users.find_one({"email": u["email"]})
        if existing:
            # Update tier/stats only — preserve consents and any data the user may have.
            # `role` este AUTORITAR pentru conturile demo canonice (repară drift, ex. client→specialist pe PROD).
            update_fields = {
                "role": u["role"],
                "tier": u.get("tier"),
                "experience_tier": experience_tier,
                "rating": u.get("rating"),
                "reviews_count": u.get("reviews_count", 0),
                "wallet_balance": float(u.get("wallet_balance", 0)),
                "tokens": int(u.get("tokens", 0)),
                "verified": u.get("verified", False),
                "_tier_demo": True,
                "_seed_tag": u["_seed_tag"],
            }
            if u["role"] == "specialist":
                update_fields["specialty"] = u.get("specialty")
                _cats = [u.get("specialty"), "interior_design"] if u.get("specialty") else []
                update_fields["service_categories"] = list(dict.fromkeys([c for c in _cats if c]))
                update_fields["coverage_zones"] = ["Bucuresti-Sector1", "Bucuresti-Sector2"]
                update_fields["availability_status"] = "available"
                update_fields["jobs_completed"] = u.get("jobs_completed", 0)
            elif u["role"] == "client":
                update_fields["zone"] = existing.get("zone") or "Bucuresti-Sector1"
                update_fields["kyc_status"] = u.get("kyc_status", "pending")
                # curăță atribute de specialist rămase din drift (ex. specialty pe un client)
                update_fields["specialty"] = None
                update_fields["service_categories"] = []
                update_fields["coverage_zones"] = []
                update_fields["availability_status"] = None
            if not verify_password(u["password"], existing["password_hash"]):
                update_fields["password_hash"] = hash_password(u["password"])
            await db.users.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            updated += 1
            continue
        # Create new
        doc = {
            "email": u["email"],
            "password_hash": hash_password(u["password"]),
            "name": u["name"],
            "role": u["role"],
            "phone": u.get("phone", ""),
            "wallet_balance": float(u.get("wallet_balance", 0)),
            "tokens": int(u.get("tokens", 0)),
            "rating": u.get("rating"),
            "reviews_count": u.get("reviews_count", 0),
            "verified": u.get("verified", False),
            "tier": u.get("tier"),
            "specialty": u.get("specialty"),
            "service_categories": list(dict.fromkeys([c for c in ([u.get("specialty"), "interior_design"] if u["role"] == "specialist" and u.get("specialty") else []) if c])),
            "coverage_zones": ["Bucuresti-Sector1", "Bucuresti-Sector2"] if u["role"] == "specialist" else [],
            "availability_status": "available" if u["role"] == "specialist" else None,
            "zone": "Bucuresti-Sector1" if u["role"] == "client" else None,
            "kyc_status": u.get("kyc_status", "pending"),
            "jobs_completed": u.get("jobs_completed", 0),
            # GDPR consents (all true for demo accounts)
            "terms_accepted": True,
            "privacy_policy_accepted": True,
            "marketing_consent": True,
            "consent_at": datetime.now(timezone.utc).isoformat(),
            "phone_verified": True,
            "_tier_demo": True,
            "_seed_tag": u["_seed_tag"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(doc)
        created += 1
    logger.info(f"[tier_demo_seed] created={created} updated={updated}")
    return {"created": created, "updated": updated}
