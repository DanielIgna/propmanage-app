"""KG-1 — Platform Entity Registry (Sprint 4 · Knowledge Graph Foundation).

Catalogul central al TUTUROR entităților platformei: colecția `kg_entity_registry`
{entity_type, label_ro, collection, tier, id_field, module, rels_out[], status}.
Sursa de adevăr pentru tipurile de noduri KG + guvernanță (ce entități există,
în ce colecții trăiesc, ce tier de tenancy au). Seed idempotent, entități noi
se adaugă DOAR prin registru (regula de guvernanță G1).
"""
import logging
from datetime import datetime, timezone

from db import db
from tenancy import classify_collection

logger = logging.getLogger("propmanage.kg.registry")

# entity_type → (label_ro, collection, id_field, module, rels_out)
CORE_ENTITIES = {
    "tenant":     ("Francizat / Tenant", "tenants", "slug", "tenancy", []),
    "user":       ("Utilizator", "users", "_id", "auth", ["owned_by:tenant"]),
    "property":   ("Proprietate", "properties", "id", "properties", ["owned_by:user"]),
    "request":    ("Cerere de lucrare", "requests", "id", "requests", ["requested_by:user", "on_property:property", "assigned_to:user"]),
    "transaction": ("Tranzacție", "transactions", "id", "wallet", ["pays_for:request"]),
    "payment":    ("Plată Stripe", "payment_transactions", "id", "payments", ["pays_for:request"]),
    "review":     ("Recenzie", "reviews", "id", "trust", ["for_work:request"]),
    "dispute":    ("Dispută", "disputes", "id", "disputes", ["disputes:request"]),
    "notification": ("Notificare", "notifications", "id", "notifications", ["owned_by:user"]),
    "lead":       ("Lead (unificat)", "leads", "id", "leads_store", ["owned_by:tenant"]),
    "ai_session": ("Sesiune AI (unificată)", "ai_sessions", "session_id", "ai_session_store", ["owned_by:user"]),
    "conversation": ("Conversație chat", "chat_messages", "id", "chat", ["for_work:request"]),
    "twin":       ("Digital Twin", "twins", "id", "digital_twin", ["on_property:property"]),
    "twin_project": ("Proiect Digital Twin", "digital_twin_projects", "id", "digital_twin", ["on_property:property"]),
    "project":    ("Proiect", "projects", "id", "projects", ["on_property:property", "owned_by:user"]),
    "phase":      ("Fază de proiect", "project_tasks", "id", "projects", ["for_work:project"]),
    "hh_plan":    ("Plan House Health", "hh_plans", "id", "house_health", ["on_property:property"]),
    "community_topic": ("Subiect comunitate", "community_topics", "id", "community", ["owned_by:user"]),
    "estate_listing": ("Listare Verified Estate", "verified_estate_listings", "id", "verified_estate", ["owned_by:user"]),
    "voucher":    ("Voucher", "vouchers", "id", "vouchers", ["owned_by:user"]),
    "quest":      ("Quest gamification", "quests", "id", "quests", []),
    "service_contract": ("Contract de servicii", "service_contracts", "id", "contracts", ["owned_by:user"]),
    "settings":   ("Configurare (unificată)", "settings", "namespace", "settings_store", ["owned_by:tenant"]),
    "service_page": ("Pagină de serviciu", "service_pages", "slug", "interior_design", ["owned_by:tenant"]),
    "xos_widget": ("Widget XOS", "xos_widget_registry", "widget_id", "xos", []),
    "experience_profile": ("Profil de experiență", "experience_profiles", "role", "xos", []),
    "site_menu":  ("Meniu site (CMS)", "site_menu", "_id", "site_menu", ["owned_by:tenant"]),
}


async def seed_registry() -> dict:
    """Idempotent: inserează entitățile de bază; nu suprascrie modificările admin."""
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    for etype, (label, col, id_field, module, rels) in CORE_ENTITIES.items():
        r = await db.kg_entity_registry.update_one(
            {"entity_type": etype},
            {"$setOnInsert": {
                "entity_type": etype, "label_ro": label, "collection": col,
                "tier": classify_collection(col), "id_field": id_field,
                "module": module, "rels_out": rels, "status": "active",
                "created_at": now, "updated_at": now,
            }},
            upsert=True,
        )
        created += 1 if r.upserted_id else 0
    await db.kg_entity_registry.create_index("entity_type", unique=True)
    return {"seeded": created, "total": len(CORE_ENTITIES)}


async def list_registry(with_counts: bool = True) -> list:
    items = await db.kg_entity_registry.find({}, {"_id": 0}).sort("entity_type", 1).to_list(200)
    if with_counts:
        for it in items:
            it["live_docs"] = await db[it["collection"]].count_documents({})
    return items


async def registered_types() -> set:
    return {d["entity_type"] async for d in db.kg_entity_registry.find({"status": "active"}, {"entity_type": 1})}


async def governance_report() -> dict:
    """Raport unificat: registru vs colecții T1 neînregistrate + statistici graf + tenancy."""
    from kg.links import kg_stats
    from tenancy import TIER1_TENANT_SCOPED, coverage_report

    items = await list_registry(with_counts=False)
    registered_cols = {it["collection"] for it in items}
    existing = set(await db.list_collection_names())
    unregistered_t1 = sorted((TIER1_TENANT_SCOPED & existing) - registered_cols)
    cov = await coverage_report()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entities_registered": len(items),
        "unregistered_t1_collections": unregistered_t1,
        "graph": await kg_stats(),
        "tenancy": cov["totals"],
        "rules": [
            "G1: orice entitate nouă se declară în kg_entity_registry înainte de a primi colecție",
            "G2: orice feature nou scrie muchiile create via kg.links.link()",
            "G3: nicio colecție nouă fără tier de tenancy (tenancy.classify_collection)",
        ],
    }
