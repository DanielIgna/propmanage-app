"""PropManage · Configuration Import / Export (Task 8 · P2).

Portable JSON bundle across configuration surfaces already governed by the
Configuration Layer. Uses ONLY existing collections; introduces no new schema
for storage. Every mutation goes through `admin_audit_log`.

Exported sections (safe, portable):
- pages (canonical `db.pages` documents, WITHOUT the `_id` field)
- pages_versions (append-only snapshots — informational only)
- site_menu (single doc `key="main"`)
- cms_content (public content fragments)
- app_settings (SEO + social + pricing + company)
- feature_config (feature × role × tier)
- design_tokens (starea RUNTIME-ACTIVĂ: db.design_tokens {_id:"active"} — Design Studio)

ROL ÎN ARHITECTURĂ (post-remediere Iun 2026):
- config_io = strat de PORTABILITATE JSON brut (migrare între medii / backup fișier).
- Snapshot-urile canonice in-DB rămân în admin_console.py (db.admin_snapshots).
- app_settings are și snapshot automat zilnic separat (settings_snapshots.py).
- Disaster recovery full-DB = admin_backups.py (mongodump).
- Precedența completă e documentată în /app/memory/audits/MASTER_PLATFORM_STATE.md.

Explicitly EXCLUDED (never exported):
- users, sessions, hh_subscriptions, hh_transactions, payment records
- passwords / password_hash / tokens / secrets
- files uploaded by users, KYC docs
- private personal data of any kind

Import is DRY-RUN by default. `apply=true` is the only path that mutates.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import require_role
from routes.design_studio import _reject_dangerous_deep


logger = logging.getLogger("propmanage.config_io")

router = APIRouter(prefix="/api/admin/config", tags=["config-io"])

SCHEMA_VERSION = "1.0"

# Whitelist of top-level sections the import/export knows how to handle.
EXPORTABLE_SECTIONS = [
    "pages",
    "pages_versions",
    "site_menu",
    "cms_content",
    "app_settings",
    "feature_config",
    "design_tokens",
]

# Fields we strip from every exported doc as a defense-in-depth even though
# these collections should not contain such fields.
_ALWAYS_STRIP = {"_id", "password", "password_hash", "secret", "api_key",
                 "stripe_secret", "token", "refresh_token", "access_token"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_sensitive(doc: dict) -> dict:
    """Recursive strip — nested secrets are removed too (defense-in-depth)."""
    out: Dict[str, Any] = {}
    for k, v in doc.items():
        if k in _ALWAYS_STRIP:
            continue
        if isinstance(v, dict):
            out[k] = _strip_sensitive(v)
        elif isinstance(v, list):
            out[k] = [_strip_sensitive(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


async def _load_section(name: str) -> Any:
    """Read a section from Mongo. Returns list or dict depending on shape."""
    if name == "pages":
        cur = db.pages.find({}, {"_id": 0})
        return [_strip_sensitive(d) async for d in cur]
    if name == "pages_versions":
        cur = db.pages_versions.find({}, {"_id": 0}).sort("published_at", -1).limit(200)
        return [_strip_sensitive(d) async for d in cur]
    if name == "site_menu":
        doc = await db.site_menu.find_one({"key": "main"}, {"_id": 0})
        return doc or {}
    if name == "cms_content":
        cur = db.cms_content.find({}, {"_id": 0})
        return [_strip_sensitive(d) async for d in cur]
    if name == "app_settings":
        doc = await db.app_settings.find_one({"_id": "app_settings"}, {"_id": 0})
        return doc or {}
    if name == "feature_config":
        doc = await db.feature_config.find_one({"_id": "config"}, {"_id": 0})
        return doc or {}
    if name == "design_tokens":
        # RUNTIME-ACTIVE tokens — the doc Design Studio writes and the frontend consumes.
        doc = await db.design_tokens.find_one({"_id": "active"}, {"_id": 0})
        return doc or {}
    return None


async def _audit(action: str, user: dict, target_id: str,
                 before: Optional[dict] = None, after: Optional[dict] = None):
    try:
        await db.admin_audit_log.insert_one({
            "action": action,
            "actor_id": str(user.get("id") or user.get("_id") or ""),
            "actor_name": user.get("name") or user.get("email") or "",
            "actor_email": user.get("email") or "",
            "target": {"type": "config_io", "id": target_id, "label": action},
            "before": before,
            "after": after,
            "created_at": _now(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("[config_io] audit failed: %s", exc)


# ------------------------------------------------------------------
# EXPORT
# ------------------------------------------------------------------
@router.get("/export")
async def export_config(user: dict = Depends(require_role("admin"))):
    """Return a full JSON bundle of the Configuration Layer for backup/migration.

    Sensitive fields are stripped defensively at every level.
    """
    sections: Dict[str, Any] = {}
    for name in EXPORTABLE_SECTIONS:
        sections[name] = await _load_section(name)

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": _now(),
        "exported_by": str(user.get("email") or ""),
        "app": "propmanage",
        "environment": "preview_or_prod",  # do not leak actual env name
        "sections": sections,
        "counts": {
            "pages": len(sections["pages"]) if isinstance(sections["pages"], list) else 0,
            "pages_versions": len(sections["pages_versions"]) if isinstance(sections["pages_versions"], list) else 0,
            "cms_content": len(sections["cms_content"]) if isinstance(sections["cms_content"], list) else 0,
        },
    }
    await _audit("config.export", user, "bundle", after={"counts": bundle["counts"]})
    return bundle


# ------------------------------------------------------------------
# IMPORT (dry-run by default; apply=true mutates)
# ------------------------------------------------------------------
class ImportRequest(BaseModel):
    bundle: Dict[str, Any]
    apply: bool = False
    sections: Optional[List[str]] = None  # subset to apply; default = all safe sections


def _validate_bundle(bundle: dict) -> None:
    if not isinstance(bundle, dict):
        raise HTTPException(400, "bundle must be a JSON object")
    if bundle.get("app") != "propmanage":
        raise HTTPException(400, "bundle.app must be 'propmanage'")
    sv = bundle.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise HTTPException(400, f"unsupported schema_version: {sv!r} (expected {SCHEMA_VERSION!r})")
    sections = bundle.get("sections")
    if not isinstance(sections, dict):
        raise HTTPException(400, "bundle.sections must be an object")
    # reject any unknown top-level section
    unknown = [k for k in sections.keys() if k not in EXPORTABLE_SECTIONS]
    if unknown:
        raise HTTPException(400, f"unknown/unsafe sections in bundle: {unknown}")


def _sanitize_docs(section: str, value: Any) -> Any:
    """Defense-in-depth: strip forbidden fields and reject unknown top-level shapes."""
    if isinstance(value, list):
        return [_strip_sensitive(v) if isinstance(v, dict) else v for v in value]
    if isinstance(value, dict):
        return _strip_sensitive(value)
    return value


async def _plan_and_apply(bundle: dict, sections_filter: Optional[List[str]],
                          apply: bool, user: dict) -> Dict[str, Any]:
    plan: Dict[str, Any] = {}
    applied_summary: Dict[str, Any] = {}
    errors: List[Dict[str, str]] = []

    incoming = bundle["sections"]
    keys = [k for k in EXPORTABLE_SECTIONS if k in incoming]
    if sections_filter:
        keys = [k for k in keys if k in sections_filter]

    for name in keys:
      try:
        raw = _sanitize_docs(name, incoming[name])
        _reject_dangerous_deep(raw)  # SEC-003: uniform pe TOATE secțiunile importate

        if name == "pages" and isinstance(raw, list):
            existing_keys = {d["key"] async for d in db.pages.find({}, {"key": 1})}
            incoming_keys = {d.get("key") for d in raw if isinstance(d, dict) and d.get("key")}
            plan[name] = {
                "to_upsert": sorted(list(incoming_keys)),
                "would_leave_existing": sorted(list(existing_keys - incoming_keys)),
                "count": len(incoming_keys),
            }
            if apply:
                for d in raw:
                    if not isinstance(d, dict) or not d.get("key"):
                        continue
                    await db.pages.update_one(
                        {"key": d["key"]},
                        {"$set": {**d, "updated_at": _now(),
                                  "updated_by": str(user.get("email") or "import")}},
                        upsert=True,
                    )
                applied_summary[name] = len(incoming_keys)

        elif name == "cms_content" and isinstance(raw, list):
            plan[name] = {"to_upsert": len(raw)}
            if apply:
                for d in raw:
                    if not isinstance(d, dict) or not d.get("key"):
                        continue
                    await db.cms_content.update_one(
                        {"key": d["key"]},
                        {"$set": {**d, "updated_at": _now(),
                                  "updated_by": str(user.get("email") or "import")}},
                        upsert=True,
                    )
                applied_summary[name] = len(raw)

        elif name == "site_menu" and isinstance(raw, dict) and raw:
            plan[name] = {"replace_key": raw.get("key") or "main",
                          "items_count": len(raw.get("items") or [])}
            if apply:
                await db.site_menu.update_one(
                    {"key": raw.get("key") or "main"},
                    {"$set": {**raw, "updated_at": _now(),
                              "updated_by": str(user.get("email") or "import")}},
                    upsert=True,
                )
                applied_summary[name] = plan[name]["items_count"]

        elif name == "app_settings" and isinstance(raw, dict) and raw:
            plan[name] = {"replace": True, "keys": sorted(list(raw.keys()))[:20]}
            if apply:
                await db.app_settings.update_one(
                    {"_id": "app_settings"},
                    {"$set": {**raw, "updated_at": _now(),
                              "updated_by": str(user.get("email") or "import")}},
                    upsert=True,
                )
                applied_summary[name] = "replaced"

        elif name == "feature_config" and isinstance(raw, dict) and raw:
            plan[name] = {"replace": True, "features_count": len(raw.get("features") or [])}
            if apply:
                await db.feature_config.update_one(
                    {"_id": "config"},
                    {"$set": {**raw, "updated_at": _now(),
                              "updated_by": str(user.get("email") or "import")}},
                    upsert=True,
                )
                applied_summary[name] = plan[name]["features_count"]

        elif name == "design_tokens" and isinstance(raw, dict) and raw:
            tokens = raw.get("tokens")
            if not isinstance(tokens, dict) or not tokens:
                raise HTTPException(400, "design_tokens: bundle-ul trebuie să conțină obiectul 'tokens' "
                                          "(forma runtime-activă exportată de Design Studio)")
            _reject_dangerous_deep(tokens)
            plan[name] = {"replace": True, "target": '_id:"active"',
                          "sections": sorted(list(tokens.keys()))[:20]}
            if apply:
                await db.design_tokens.update_one(
                    {"_id": "active"},
                    {"$set": {"tokens": tokens,
                              "preset_id": raw.get("preset_id") or "imported",
                              "updated_at": _now(),
                              "updated_by": str(user.get("email") or "import")}},
                    upsert=True,
                )
                applied_summary[name] = "replaced_runtime_active"

        elif name == "pages_versions":
            # NEVER re-import history — it must remain append-only via publish flow.
            plan[name] = {"skipped_reason": "pages_versions is append-only history, never imported"}
      except HTTPException:
        raise  # validation errors → 400 vizibil, fără mutații ascunse
      except Exception as exc:  # noqa: BLE001
        logger.error("[config_io] section %s failed: %s", name, exc)
        errors.append({"section": name, "error": str(exc)[:300]})

    return {
        "dry_run": not apply,
        "plan": plan,
        "applied": applied_summary if apply else None,
        "errors": errors,
    }


@router.post("/import")
async def import_config(body: ImportRequest, user: dict = Depends(require_role("admin"))):
    """Validate + preview an import bundle (dry-run by default).

    Only when `apply=true` will the endpoint actually mutate configuration. Every
    apply action is audited. Never touches users, subscriptions or secrets.
    """
    _validate_bundle(body.bundle)
    if body.apply:
        # Pas de validare completă (dry-run intern) ÎNAINTE de orice mutație —
        # un bundle invalid nu poate lăsa importul aplicat pe jumătate.
        await _plan_and_apply(body.bundle, body.sections, False, user)
    result = await _plan_and_apply(body.bundle, body.sections, body.apply, user)
    await _audit(
        "config.import.apply" if body.apply else "config.import.dry_run",
        user, "bundle",
        before={"schema_version": body.bundle.get("schema_version")},
        after={"plan_keys": sorted(list((result.get("plan") or {}).keys())),
               "applied": result.get("applied"),
               "errors": result.get("errors") or None},
    )
    if body.apply and result.get("errors"):
        # NO false-success: dacă o secțiune a eșuat, operațiunea eșuează vizibil.
        raise HTTPException(500, detail={
            "message": "Import parțial eșuat — verifică secțiunile raportate",
            "failed_sections": result["errors"],
            "applied": result.get("applied"),
        })
    return {"ok": True, **result}
