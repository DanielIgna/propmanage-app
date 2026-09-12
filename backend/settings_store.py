"""settings_store — motorul unic de configurare (Sprint 2 · 2.2, strangler pattern).

Colecția unificată: `settings` {namespace, key, value, tenant_id}.
- Citire: nou → fallback legacy (nimic nu se strică pentru consumatorii nemigrați).
- Scriere: DUAL-WRITE (nou + legacy) în tranziție — cei 28+ de cititori legacy rămân corecți.
"""
import logging
from datetime import datetime, timezone

from db import db

from tenancy import DEFAULT_TENANT as TENANT

logger = logging.getLogger("propmanage.settings_store")

# namespace → (colecție legacy, filtru, extractor, writer)
_LEGACY = {
    "app": ("app_settings", {"_id": "app_settings"}),
    "security": ("security_config", {"_id": "global"}),
    "platform": ("platform_config", {"key": "settings"}),
    "tiers": ("platform_settings", {"_id": "incident_spike_alert"}),
}


async def get_settings(namespace: str, key: str = "main") -> dict:
    doc = await db.settings.find_one({"namespace": namespace, "key": key})
    if doc:
        return doc.get("value") or {}
    legacy = _LEGACY.get(namespace)
    if legacy:
        col, q = legacy
        ldoc = await db[col].find_one(q)
        if ldoc:
            return {k: v for k, v in ldoc.items() if k not in ("_id", "key")}
    return {}


async def put_settings(namespace: str, value: dict, who: str = "system", key: str = "main") -> None:
    now = datetime.now(timezone.utc).isoformat()
    await db.settings.update_one(
        {"namespace": namespace, "key": key},
        {"$set": {"value": value, "tenant_id": TENANT, "updated_at": now, "updated_by": who}},
        upsert=True,
    )
    legacy = _LEGACY.get(namespace)
    if legacy:  # dual-write: legacy rămâne sincron pentru consumatorii nemigrați
        col, q = legacy
        try:
            await db[col].update_one(q, {"$set": value}, upsert=True)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[settings_store] legacy dual-write fail ({namespace}): {e}")


async def patch_settings(namespace: str, updates: dict, who: str = "system", key: str = "main") -> dict:
    """Merge parțial (dot-keys suportate de Mongo la legacy; la nou facem merge în value)."""
    current = await get_settings(namespace, key)
    merged = dict(current)
    for k, v in updates.items():
        if "." in k:
            top, sub = k.split(".", 1)
            merged.setdefault(top, {})
            if isinstance(merged[top], dict):
                merged[top][sub] = v
        else:
            merged[k] = v
    await put_settings(namespace, merged, who, key)
    return merged


async def migrate_all() -> dict:
    out = {}
    for ns, (col, q) in _LEGACY.items():
        ldoc = await db[col].find_one(q)
        if ldoc:
            value = {k: v for k, v in ldoc.items() if k not in ("_id", "key")}
            existing = await db.settings.find_one({"namespace": ns, "key": "main"})
            if not existing:
                await db.settings.update_one(
                    {"namespace": ns, "key": "main"},
                    {"$set": {"value": value, "tenant_id": TENANT,
                              "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": "migration"}},
                    upsert=True,
                )
            out[ns] = "migrated" if not existing else "exists"
        else:
            out[ns] = "no_legacy"
    return out
