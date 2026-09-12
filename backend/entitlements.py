"""PropManage — Central Entitlement Layer.

Punct unic de adevăr pentru „utilizatorul X are acces la feature Y?".
Reutilizează colecțiile existente `hh_subscriptions` + `hh_plans`.
Nu duplică infrastructura: doar traduce starea existentă a subscription-ului
într-un vocabular de FEATURES + TIERS pe care îl folosesc frontend, backend
și viitoarele module.

Design:
  - Tier-urile actuale recunoscute: FREE, CLIENT_BASIC, CLIENT_PRO, CLIENT_PREMIUM
  - Feature-urile sunt string-uri stabile (ex. "house_health_basic")
  - Mapping-ul TIER → set(features) e centralizat aici (o singură sursă)
  - Admin/operator/franchise_admin au acces TOTAL (bypass entitlement)
  - Specialist rămâne pe fluxul propriu (nu e afectat de acest gate)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException

from db import db
from deps import get_current_user

logger = logging.getLogger("propmanage.entitlements")

# =============================================================================
# TIERS + FEATURES CATALOG (SINGURA SURSĂ)
# =============================================================================
TIER_FREE = "FREE"
TIER_CLIENT_BASIC = "CLIENT_BASIC"
TIER_CLIENT_PRO = "CLIENT_PRO"
TIER_CLIENT_PREMIUM = "CLIENT_PREMIUM"

# Ordine crescătoare (fiecare tier moștenește tot ce e sub el)
TIER_ORDER = [TIER_FREE, TIER_CLIENT_BASIC, TIER_CLIENT_PRO, TIER_CLIENT_PREMIUM]

# --- Specialist tiers (CÂȘTIGATE din experience_tier — NU plătite) -----------
# Reutilizează SSOT-ul existent `experience_tier` (junior→regular→verified→pro).
TIER_SPEC_BASIC = "SPEC_BASIC"        # experience_tier: junior (implicit)
TIER_SPEC_ACTIVE = "SPEC_ACTIVE"      # experience_tier: regular
TIER_SPEC_VERIFIED = "SPEC_VERIFIED"  # experience_tier: verified
TIER_SPEC_PRO = "SPEC_PRO"            # experience_tier: pro

SPEC_TIER_ORDER = [TIER_SPEC_BASIC, TIER_SPEC_ACTIVE, TIER_SPEC_VERIFIED, TIER_SPEC_PRO]

EXPERIENCE_TIER_TO_SPEC = {
    "junior": TIER_SPEC_BASIC,
    "regular": TIER_SPEC_ACTIVE,
    "verified": TIER_SPEC_VERIFIED,
    "pro": TIER_SPEC_PRO,
}

# Mapare slug hh_plans → tier PropManage (nu redenumim datele existente)
PLAN_SLUG_TO_TIER = {
    "basic": TIER_CLIENT_BASIC,
    "pro": TIER_CLIENT_PRO,
    "premium": TIER_CLIENT_PREMIUM,
    "custom": TIER_CLIENT_PRO,  # custom = tratat ca PRO by default
}

# Feature-uri client stabile (identificatori unici — nu se schimbă niciodată)
F_PROPERTY_CREATE = "property_create"
F_PROPERTY_TECHNICAL_RECORD = "property_technical_record"
F_HOUSE_HEALTH_BASIC = "house_health_basic"
F_HOUSE_HEALTH_ADVANCED = "house_health_advanced"
F_DIGITAL_TWIN_ADVANCED = "digital_twin_advanced"
# PREMIUM-only (Property Intelligence) — conform planului admin PREMIUM
F_PROPERTY_INTELLIGENCE = "property_intelligence"
F_PORTFOLIO_MANAGEMENT = "portfolio_management"

# Tier → features acordate (fără moștenire — moștenirea se calculează runtime)
# NOTĂ: Digital Twin complet este PREMIUM-only (planul PRO nu include Digital Twin).
TIER_FEATURES: dict[str, set[str]] = {
    TIER_FREE: {
        F_PROPERTY_CREATE,
        F_PROPERTY_TECHNICAL_RECORD,
    },
    TIER_CLIENT_BASIC: {
        F_HOUSE_HEALTH_BASIC,
    },
    TIER_CLIENT_PRO: {
        F_HOUSE_HEALTH_ADVANCED,
    },
    TIER_CLIENT_PREMIUM: {
        F_DIGITAL_TWIN_ADVANCED,
        F_PROPERTY_INTELLIGENCE,
        F_PORTFOLIO_MANAGEMENT,
    },
}

# --- Specialist features (oglindesc feature_configurator — vocabular unic) ---
F_SPEC_BASIC_DASHBOARD = "spec_basic_dashboard"
F_SPEC_SIMPLE_OFFER = "spec_simple_offer"
F_SPEC_ESSENTIAL_MESSAGES = "spec_essential_messages"
F_SPEC_ADVANCED_FILTERS = "spec_advanced_filters"
F_SPEC_SAVED_SEARCHES = "spec_saved_searches"
F_SPEC_OFFER_TEMPLATES = "spec_offer_templates"
F_SPEC_PRIORITY_MATCHING = "spec_priority_matching"
F_SPEC_BULK_OPERATIONS = "spec_bulk_operations"
F_SPEC_ADVANCED_ANALYTICS = "spec_advanced_analytics"
F_SPEC_EXPORT_REVENUE = "spec_export_revenue"
F_SPEC_PRIORITY_SUPPORT = "spec_priority_support"
F_SPEC_WHITE_LABEL_REPORTS = "spec_white_label_reports"

SPEC_TIER_FEATURES: dict[str, set[str]] = {
    TIER_SPEC_BASIC: {F_SPEC_BASIC_DASHBOARD, F_SPEC_SIMPLE_OFFER, F_SPEC_ESSENTIAL_MESSAGES},
    TIER_SPEC_ACTIVE: {F_SPEC_ADVANCED_FILTERS, F_SPEC_SAVED_SEARCHES, F_SPEC_OFFER_TEMPLATES},
    TIER_SPEC_VERIFIED: {F_SPEC_PRIORITY_MATCHING, F_SPEC_BULK_OPERATIONS, F_SPEC_ADVANCED_ANALYTICS, F_SPEC_EXPORT_REVENUE},
    TIER_SPEC_PRO: {F_SPEC_PRIORITY_SUPPORT, F_SPEC_WHITE_LABEL_REPORTS},
}

# Metadata prezentabil pentru UI (nu e sursă de adevăr, doar helper)
FEATURE_LABELS = {
    F_PROPERTY_CREATE: "Adăugare proprietate",
    F_PROPERTY_TECHNICAL_RECORD: "Dosar Tehnic",
    F_HOUSE_HEALTH_BASIC: "House Health Basic",
    F_HOUSE_HEALTH_ADVANCED: "House Health avansat",
    F_DIGITAL_TWIN_ADVANCED: "Digital Twin complet",
    F_PROPERTY_INTELLIGENCE: "Property Intelligence",
    F_PORTFOLIO_MANAGEMENT: "Management portofoliu",
}

SPEC_FEATURE_LABELS = {
    F_SPEC_BASIC_DASHBOARD: "Dashboard de bază",
    F_SPEC_SIMPLE_OFFER: "Oferte simple",
    F_SPEC_ESSENTIAL_MESSAGES: "Mesaje esențiale",
    F_SPEC_ADVANCED_FILTERS: "Filtre avansate oportunități",
    F_SPEC_SAVED_SEARCHES: "Căutări salvate",
    F_SPEC_OFFER_TEMPLATES: "Șabloane oferte",
    F_SPEC_PRIORITY_MATCHING: "Matching prioritar",
    F_SPEC_BULK_OPERATIONS: "Aplicare în masă",
    F_SPEC_ADVANCED_ANALYTICS: "Analytics business",
    F_SPEC_EXPORT_REVENUE: "Export raport venituri",
    F_SPEC_PRIORITY_SUPPORT: "Support prioritar",
    F_SPEC_WHITE_LABEL_REPORTS: "Rapoarte white-label",
}

# Dicționar unificat pentru validare/mesaje (client + specialist)
ALL_FEATURE_LABELS = {**FEATURE_LABELS, **SPEC_FEATURE_LABELS}

TIER_LABELS = {
    TIER_FREE: "Gratuit",
    TIER_CLIENT_BASIC: "PropManage Basic",
    TIER_CLIENT_PRO: "PropManage Pro",
    TIER_CLIENT_PREMIUM: "PropManage Premium",
    TIER_SPEC_BASIC: "Specialist Basic",
    TIER_SPEC_ACTIVE: "Specialist Activ",
    TIER_SPEC_VERIFIED: "Specialist Verificat",
    TIER_SPEC_PRO: "Specialist Pro",
}


# =============================================================================
# CORE — starea de entitlement pentru un user
# =============================================================================
async def _fetch_active_subscription(user_id: str) -> Optional[dict]:
    """Reutilizează structura existentă hh_subscriptions.

    Semantica statusurilor:
      * active    → plătit, în perioadă activă
      * trial     → trial gratuit valid
      * grace     → plată eșuată, perioadă de grație
      * cancelled → user a cerut anulare, dar acces valabil PÂNĂ la expires_at

    Un abonament e considerat ACCESIBIL doar dacă status ∈ {active, trial, grace, cancelled}
    ȘI expires_at este în viitor (sau lipsește).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    return await db.hh_subscriptions.find_one(
        {
            "user_id": user_id,
            "status": {"$in": ["active", "trial", "grace", "cancelled"]},
            "$or": [
                {"expires_at": {"$gt": now_iso}},
                {"expires_at": None},
                {"expires_at": {"$exists": False}},
            ],
        },
        {"_id": 0},
    )


async def _fetch_last_subscription(user_id: str) -> Optional[dict]:
    """Ultimul document hh_subscriptions al user-ului (indiferent de status/expiry).

    Folosit doar când user-ul e resolv la FREE dar a avut cândva abonament —
    frontend-ul afișează un notice friendly în loc de tăcere.
    """
    return await db.hh_subscriptions.find_one(
        {"user_id": user_id},
        {"_id": 0},
        sort=[("updated_at", -1), ("expires_at", -1)],
    )


def _compute_lifecycle(role: Optional[str], sub_active: Optional[dict], sub_last: Optional[dict]) -> str:
    """Stare de ciclu de viață — orientată UI. Sursa de adevăr rămâne entitlement layer.

    Return: never_subscribed | active | cancelled_grace | expired | admin_bypass
    """
    if role in ("admin", "operator", "franchise_admin"):
        return "admin_bypass"
    if sub_active:
        return "cancelled_grace" if sub_active.get("status") == "cancelled" else "active"
    if sub_last:
        # user a avut cândva abonament, dar acum nu mai are acces
        return "expired"
    return "never_subscribed"


def _tier_from_role_and_sub(role: Optional[str], sub: Optional[dict]) -> str:
    """Admin/operator/franchise_admin primesc automat cel mai înalt tier.
    Specialist e pe canal separat (nu e utilizator plătitor) — tier=FREE tehnic dar
    nu e afectat de gate-urile pentru clienți."""
    if role in ("admin", "operator", "franchise_admin"):
        return TIER_CLIENT_PREMIUM
    if not sub:
        return TIER_FREE
    slug = (sub.get("plan") or "").lower()
    return PLAN_SLUG_TO_TIER.get(slug, TIER_CLIENT_BASIC)


def _resolve_features(tier: str) -> set[str]:
    """Un user cu tier X primește toate feature-urile din toate tier-urile ≤ X (pe scara lui)."""
    if tier in SPEC_TIER_ORDER:
        idx = SPEC_TIER_ORDER.index(tier)
        features: set[str] = set()
        for t in SPEC_TIER_ORDER[: idx + 1]:
            features |= SPEC_TIER_FEATURES.get(t, set())
        return features
    if tier not in TIER_ORDER:
        return set(TIER_FEATURES.get(TIER_FREE, set()))
    idx = TIER_ORDER.index(tier)
    features = set()
    for t in TIER_ORDER[: idx + 1]:
        features |= TIER_FEATURES.get(t, set())
    return features


async def get_user_entitlements(user: dict) -> dict:
    """Contract stabil pentru orice caller (route, dependency, admin lookup).

    Returns:
      {
        user_id, role, tier, tier_label,
        subscription: {plan, status, expires_at} sau None,
        features: [feature_ids],
        is_admin_bypass: bool,
        lifecycle: "never_subscribed"|"active"|"cancelled_grace"|"expired"|"admin_bypass",
        last_subscription: {plan, status, expires_at} — doar dacă lifecycle == "expired",
        notice: {kind, message, cta_href} sau None — pentru banner UI
      }
    """
    role = user.get("active_view") or user.get("role")
    is_admin_bypass = role in ("admin", "operator", "franchise_admin")

    # --- Specialist: tier CÂȘTIGAT din experience_tier (nu abonament plătit) ---
    if role == "specialist" and not is_admin_bypass:
        exp = (user.get("experience_tier") or "junior").lower()
        spec_tier = EXPERIENCE_TIER_TO_SPEC.get(exp, TIER_SPEC_BASIC)
        spec_features = _resolve_features(spec_tier)
        return {
            "user_id": str(user["id"]),
            "role": role,
            "tier": spec_tier,
            "tier_label": TIER_LABELS.get(spec_tier, spec_tier),
            "subscription": None,
            "features": sorted(spec_features),
            "is_admin_bypass": False,
            "lifecycle": "specialist_earned",
            "last_subscription": None,
            "notice": None,
            "experience_tier": exp,
        }

    sub_active = None if is_admin_bypass else await _fetch_active_subscription(str(user["id"]))
    tier = _tier_from_role_and_sub(role, sub_active)
    features = _resolve_features(tier)

    sub_last = None
    if not is_admin_bypass and not sub_active:
        sub_last = await _fetch_last_subscription(str(user["id"]))

    lifecycle = _compute_lifecycle(role, sub_active, sub_last)

    notice = None
    if lifecycle == "expired":
        plan_label = TIER_LABELS.get(
            PLAN_SLUG_TO_TIER.get((sub_last or {}).get("plan", "").lower(), TIER_FREE),
            "PropManage",
        )
        notice = {
            "kind": "subscription_expired",
            "message": f"Abonamentul {plan_label} a expirat. Datele tale sunt păstrate — reactivează pentru a debloca funcțiile.",
            "cta_href": "/pricing",
            "cta_label": "Reactivează",
        }
    elif lifecycle == "cancelled_grace" and sub_active:
        exp = sub_active.get("expires_at")
        notice = {
            "kind": "subscription_cancelled",
            "message": f"Abonamentul a fost anulat. Ai acces până la {exp[:10] if exp else 'expirare'}.",
            "cta_href": "/pricing",
            "cta_label": "Reactivează",
        }

    return {
        "user_id": str(user["id"]),
        "role": role,
        "tier": tier,
        "tier_label": TIER_LABELS.get(tier, tier),
        "subscription": (
            {
                "plan": sub_active.get("plan"),
                "status": sub_active.get("status"),
                "expires_at": sub_active.get("expires_at"),
            }
            if sub_active
            else None
        ),
        "features": sorted(features),
        "is_admin_bypass": is_admin_bypass,
        "lifecycle": lifecycle,
        "last_subscription": (
            {
                "plan": sub_last.get("plan"),
                "status": sub_last.get("status"),
                "expires_at": sub_last.get("expires_at"),
            }
            if sub_last
            else None
        ),
        "notice": notice,
    }


async def user_has_feature(user: dict, feature: str) -> bool:
    ent = await get_user_entitlements(user)
    return feature in set(ent["features"])


# =============================================================================
# FASTAPI DEPENDENCY — protecție API centralizată
# =============================================================================
def require_entitlement(feature: str):
    """Folosit ca dependency FastAPI:
        @router.post(...)
        async def endpoint(user=Depends(require_entitlement(F_HOUSE_HEALTH_BASIC))):
            ...
    """
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if not feature or feature not in ALL_FEATURE_LABELS:
            # feature necunoscut → nu blocăm silențios, dar log
            logger.warning("require_entitlement: feature necunoscut %r", feature)
        ent = await get_user_entitlements(user)
        if feature in set(ent["features"]):
            return user
        feat_label = ALL_FEATURE_LABELS.get(feature, feature)
        raise HTTPException(
            status_code=402,  # Payment Required — semantic corect pentru gating
            detail={
                "error": "entitlement_required",
                "feature": feature,
                "feature_label": feat_label,
                "current_tier": ent["tier"],
                "current_tier_label": ent["tier_label"],
                "message": f"„{feat_label}” nu este inclus în planul tău actual ({ent['tier_label']}). Fă upgrade pentru a accesa această funcție.",
            },
        )
    return _dep


def get_tier_catalog() -> dict:
    """Snapshot al catalogului tier→features (folosit de admin UI / debug)."""
    return {
        "tiers": [
            {"id": t, "label": TIER_LABELS[t], "features": sorted(TIER_FEATURES.get(t, set()))}
            for t in TIER_ORDER
        ],
        "specialist_tiers": [
            {"id": t, "label": TIER_LABELS[t], "features": sorted(SPEC_TIER_FEATURES.get(t, set()))}
            for t in SPEC_TIER_ORDER
        ],
        "features": [
            {"id": f, "label": lbl}
            for f, lbl in ALL_FEATURE_LABELS.items()
        ],
    }
