"""Experience OS (XOS) — Layout Builder, Dynamic UI Rules, Theme & Content Manager.

- xos_layouts: ordinea/vizibilitatea widget-urilor per suprafață (prima: client_home)
- ui_rules: reguli vizuale DACĂ [condiție] ATUNCI [ascunde/arată] element (meniu sau widget)
- site_content: banner anunțuri + override texte hero, editabile din admin
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from db import db
from deps import get_current_user, require_role

router = APIRouter(prefix="/api", tags=["xos"])
logger = logging.getLogger("propmanage.xos")

# ── Widget Registry (Etapa 1.1 — Experience OS Foundation) ───────────────────
# Sursa de adevăr pentru widget-uri e DB (xos_widget_registry), nu codul.
# D6:A — orice widget nou de dashboard intră prin registru.
SURFACE_META = {
    "client_home": {"label": "Dashboard Client · Acasă"},
    "specialist_home": {"label": "Dashboard Specialist · Oportunități"},
}

TENANT = "main"  # D5-C: convenție tenant pe toate colecțiile XOS (migrare completă la primul contract de franciză)

WIDGET_CLASSES = {"CORE", "AI", "AUTONOMY", "BUSINESS", "PREMIUM", "GROWTH", "INFRASTRUCTURE", "EXPERIMENTAL", "LEGACY"}
WIDGET_STATUSES = {"active", "experimental", "legacy"}

DEFAULT_REGISTRY = [
    {"id": "hero", "surface": "client_home", "label": "Hero adaptiv", "desc": "Cardul principal contextual (proprietate / cerere activă / solicită)", "class": "CORE", "status": "active", "roles": ["client"], "implemented": True},
    {"id": "quick_actions", "surface": "client_home", "label": "Acțiuni rapide", "desc": "Grid 4: Solicită, Proprietatea, Lucrări, Întreabă AI", "class": "CORE", "status": "active", "roles": ["client"], "implemented": True},
    {"id": "copilot", "surface": "client_home", "label": "AI Copilot", "desc": "Asistent AI cu sumar și acțiuni recomandate", "class": "AI", "status": "active", "roles": ["client"], "implemented": True},
    {"id": "contextual", "surface": "client_home", "label": "Noutăți pentru tine", "desc": "Carduri contextuale: oferte, plăți, confirmări", "class": "CORE", "status": "active", "roles": ["client"], "implemented": True},
    {"id": "discover", "surface": "client_home", "label": "Descoperă", "desc": "Carusel: Digital Twin, House Health, Ghid întreținere", "class": "GROWTH", "status": "active", "roles": ["client"], "implemented": True},
    {"id": "today_summary", "surface": "specialist_home", "label": "Astăzi ai (KPI)", "desc": "Cereri noi, lucrări în lucru, notificări, încasări luna aceasta", "class": "CORE", "status": "active", "roles": ["specialist"], "implemented": True},
    {"id": "cockpit", "surface": "specialist_home", "label": "Cockpit AI", "desc": "SpecialistCockpit: prioritățile zilei generate de AI", "class": "AI", "status": "active", "roles": ["specialist"], "implemented": True},
    {"id": "quests", "surface": "specialist_home", "label": "Quest-uri", "desc": "Misiuni gamificate (vizibil doar la tier-urile cu quests)", "class": "GROWTH", "status": "active", "roles": ["specialist"], "implemented": True},
    {"id": "tier_tools", "surface": "specialist_home", "label": "Unelte de tier", "desc": "TierToolsPanel: statistici și unelte deblocate de tier", "class": "PREMIUM", "status": "active", "roles": ["specialist"], "implemented": True},
    {"id": "tier_progress", "surface": "specialist_home", "label": "Progres tier", "desc": "Bara de progres către următorul tier", "class": "GROWTH", "status": "active", "roles": ["specialist"], "implemented": True},
]


async def _ensure_registry_seed() -> None:
    now = datetime.now(timezone.utc).isoformat()
    for surface in SURFACE_META:
        if await db.xos_widget_registry.count_documents({"surface": surface}) == 0:
            defaults = [w for w in DEFAULT_REGISTRY if w["surface"] == surface]
            if defaults:
                await db.xos_widget_registry.insert_many(
                    [{**w, "tenant_id": TENANT, "registered_at": now, "registered_by": "seed"} for w in defaults]
                )


async def _registry_widgets(surface: str, only_active: bool = False) -> list:
    await _ensure_registry_seed()
    q = {"surface": surface}
    if only_active:
        q["status"] = "active"
    return await db.xos_widget_registry.find(q, {"_id": 0}).to_list(200)


def _default_layout_from(widgets: list) -> list:
    return [{"id": w["id"], "enabled": True} for w in widgets]


async def _get_layout(surface: str) -> list:
    if surface not in SURFACE_META:
        raise HTTPException(404, "Suprafață necunoscută.")
    widgets = await _registry_widgets(surface, only_active=True)
    valid_ids = {w["id"] for w in widgets}
    doc = await db.xos_layouts.find_one({"surface": surface})
    if not doc:
        return _default_layout_from(widgets)
    items = [i for i in (doc.get("items") or []) if i.get("id") in valid_ids]
    saved_ids = {i["id"] for i in items}
    items += [{"id": w["id"], "enabled": True} for w in widgets if w["id"] not in saved_ids]
    return items


@router.get("/xos/layout/{surface}")
async def public_layout(surface: str):
    return {"surface": surface, "items": await _get_layout(surface)}


@router.get("/admin/xos/surfaces")
async def admin_surfaces(_admin=Depends(require_role("admin"))):
    out = []
    for k, meta in SURFACE_META.items():
        widgets = await _registry_widgets(k, only_active=True)
        out.append({"surface": k, "label": meta["label"], "widgets": widgets, "items": await _get_layout(k)})
    return {"surfaces": out}


@router.put("/admin/xos/layout/{surface}")
async def admin_put_layout(surface: str, items: list = Body(..., embed=True), admin=Depends(require_role("admin"))):
    if surface not in SURFACE_META:
        raise HTTPException(404, "Suprafață necunoscută.")
    widgets = await _registry_widgets(surface, only_active=True)
    valid_ids = {w["id"] for w in widgets}
    clean = [{"id": i["id"], "enabled": bool(i.get("enabled", True))} for i in items if isinstance(i, dict) and i.get("id") in valid_ids]
    if not clean:
        raise HTTPException(400, "Layout gol.")
    await _snapshot_layout(surface, admin.get("email"), reason="pre-save")
    await db.xos_layouts.update_one(
        {"surface": surface},
        {"$set": {"items": clean, "tenant_id": TENANT, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, "items": clean}


async def _snapshot_layout(surface: str, who: str, reason: str = "pre-save") -> None:
    """Sprint 5: istoric versiuni layout (cap 20 per suprafață)."""
    current = await db.xos_layouts.find_one({"surface": surface})
    if not current or not current.get("items"):
        return
    last = await db.xos_layout_history.find_one({"surface": surface}, sort=[("saved_at", -1)])
    if last and last.get("items") == current["items"]:
        return  # dedup: nu consumăm sloturi cu snapshot identic
    await db.xos_layout_history.insert_one({
        "version_id": uuid.uuid4().hex[:10], "surface": surface, "tenant_id": TENANT,
        "items": current["items"], "reason": reason,
        "saved_at": datetime.now(timezone.utc).isoformat(), "saved_by": who,
    })
    ids = [d["_id"] async for d in db.xos_layout_history.find({"surface": surface}, {"_id": 1}).sort("saved_at", -1).skip(20)]
    if ids:
        await db.xos_layout_history.delete_many({"_id": {"$in": ids}})


@router.get("/admin/xos/layout/{surface}/history")
async def admin_layout_history(surface: str, _admin=Depends(require_role("admin"))):
    if surface not in SURFACE_META:
        raise HTTPException(404, "Suprafață necunoscută.")
    versions = await db.xos_layout_history.find({"surface": surface}, {"_id": 0}).sort("saved_at", -1).to_list(20)
    return {"surface": surface, "versions": versions}


@router.post("/admin/xos/layout/{surface}/rollback/{version_id}")
async def admin_layout_rollback(surface: str, version_id: str, admin=Depends(require_role("admin"))):
    v = await db.xos_layout_history.find_one({"surface": surface, "version_id": version_id})
    if not v:
        raise HTTPException(404, "Versiune inexistentă.")
    await _snapshot_layout(surface, admin.get("email"), reason="pre-rollback")
    await db.xos_layouts.update_one(
        {"surface": surface},
        {"$set": {"items": v["items"], "tenant_id": TENANT, "updated_at": datetime.now(timezone.utc).isoformat(),
                  "updated_by": admin.get("email"), "restored_from": version_id}},
        upsert=True,
    )
    return {"ok": True, "items": await _get_layout(surface)}


@router.post("/admin/xos/layout/{surface}/reset")
async def admin_reset_layout(surface: str, _admin=Depends(require_role("admin"))):
    if surface not in SURFACE_META:
        raise HTTPException(404, "Suprafață necunoscută.")
    await db.xos_layouts.delete_one({"surface": surface})
    return {"ok": True, "items": _default_layout_from(await _registry_widgets(surface, only_active=True))}


# ── Widget Registry CRUD (D6:A — nu se șterge, se marchează legacy) ───────────
@router.get("/admin/xos/registry")
async def admin_get_registry(_admin=Depends(require_role("admin"))):
    await _ensure_registry_seed()
    entries = await db.xos_widget_registry.find({}, {"_id": 0}).sort("surface", 1).to_list(500)
    return {"entries": entries, "surfaces": SURFACE_META, "classes": sorted(WIDGET_CLASSES), "statuses": sorted(WIDGET_STATUSES)}


@router.post("/admin/xos/registry")
async def admin_add_registry(payload: dict = Body(...), admin=Depends(require_role("admin"))):
    wid = str(payload.get("id", "")).strip().lower().replace(" ", "_")[:50]
    surface = payload.get("surface")
    if not wid or surface not in SURFACE_META:
        raise HTTPException(400, "id și surface valide sunt obligatorii.")
    if await db.xos_widget_registry.find_one({"id": wid, "surface": surface}):
        raise HTTPException(409, "Widget-ul există deja în registru.")
    entry = {
        "id": wid, "surface": surface,
        "label": str(payload.get("label") or wid)[:80],
        "desc": str(payload.get("desc") or "")[:300],
        "class": payload.get("class") if payload.get("class") in WIDGET_CLASSES else "EXPERIMENTAL",
        "status": payload.get("status") if payload.get("status") in WIDGET_STATUSES else "experimental",
        "roles": [str(r)[:30] for r in (payload.get("roles") or [])][:10],
        "implemented": False,
        "tenant_id": TENANT,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": admin.get("email"),
    }
    await db.xos_widget_registry.insert_one(dict(entry))
    return {"ok": True, "entry": entry}


@router.patch("/admin/xos/registry/{surface}/{widget_id}")
async def admin_patch_registry(surface: str, widget_id: str, payload: dict = Body(...), admin=Depends(require_role("admin"))):
    updates = {}
    if payload.get("class") in WIDGET_CLASSES:
        updates["class"] = payload["class"]
    if payload.get("status") in WIDGET_STATUSES:
        updates["status"] = payload["status"]
    for k in ("label", "desc"):
        if isinstance(payload.get(k), str):
            updates[k] = payload[k][:300]
    if isinstance(payload.get("roles"), list):
        updates["roles"] = [str(r)[:30] for r in payload["roles"]][:10]
    if not updates:
        raise HTTPException(400, "Nimic de actualizat.")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = admin.get("email")
    r = await db.xos_widget_registry.update_one({"id": widget_id, "surface": surface}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(404, "Widget inexistent în registru.")
    return {"ok": True}


# ── Dynamic UI Rules ──────────────────────────────────────────────────────────
_RULE_FIELDS = {"role", "verified", "projects_completed", "account_age_days"}
_RULE_OPS = {"eq", "neq", "gte", "lte"}


def _sanitize_rules(rules: list) -> list:
    out = []
    for r in rules:
        if not isinstance(r, dict) or r.get("target_type") not in ("menu", "widget") or not str(r.get("target_id", "")).strip():
            continue
        conds = []
        for c in r.get("conditions") or []:
            if isinstance(c, dict) and c.get("field") in _RULE_FIELDS and c.get("op") in _RULE_OPS:
                conds.append({"field": c["field"], "op": c["op"], "value": c.get("value")})
        out.append({
            "id": str(r.get("id") or uuid.uuid4().hex[:10]),
            "name": str(r.get("name") or "Regulă")[:100],
            "target_type": r["target_type"],
            "target_id": str(r["target_id"])[:60],
            "action": r.get("action") if r.get("action") in ("hide", "show_if") else "hide",
            "conditions": conds,
            "active": bool(r.get("active", True)),
        })
    return out


async def _get_rules() -> list:
    doc = await db.ui_rules.find_one({"key": "main"})
    return (doc or {}).get("rules") or []


def _cond_match(cond: dict, ctx: dict) -> bool:
    actual = ctx.get(cond["field"])
    val = cond.get("value")
    if cond["field"] == "verified":
        val = str(val).lower() in ("true", "1", "da", "yes")
    elif cond["field"] in ("projects_completed", "account_age_days"):
        try:
            val = float(val)
            actual = float(actual or 0)
        except (TypeError, ValueError):
            return False
    op = cond["op"]
    if op == "eq":
        return actual == val
    if op == "neq":
        return actual != val
    if op == "gte":
        return actual >= val
    if op == "lte":
        return actual <= val
    return False


async def _user_ctx(request: Request) -> dict:
    try:
        user = await get_current_user(request)
    except HTTPException:
        user = None
    if not user:
        return {"role": "guest", "verified": False, "projects_completed": 0, "account_age_days": 0}
    age_days = 0
    try:
        created = datetime.fromisoformat(str(user.get("created_at", "")).replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created).days
    except (ValueError, TypeError):
        pass
    projects = await db.requests.count_documents({"client_id": user.get("id"), "status": "confirmed"})
    return {
        "role": user.get("role", "guest"),
        "verified": bool(user.get("verified")),
        "projects_completed": projects,
        "account_age_days": age_days,
    }


@router.get("/ui-rules/my")
async def my_ui_rules(request: Request):
    rules = [r for r in await _get_rules() if r.get("active")]
    if not rules:
        return {"hidden": []}
    ctx = await _user_ctx(request)
    hidden = []
    for r in rules:
        match = all(_cond_match(c, ctx) for c in r["conditions"]) if r["conditions"] else True
        if (r["action"] == "hide" and match) or (r["action"] == "show_if" and not match):
            hidden.append(f"{r['target_type']}:{r['target_id']}")
    return {"hidden": hidden}


@router.get("/admin/ui-rules")
async def admin_get_rules(_admin=Depends(require_role("admin"))):
    return {"rules": await _get_rules()}


@router.put("/admin/ui-rules")
async def admin_put_rules(rules: list = Body(..., embed=True), admin=Depends(require_role("admin"))):
    clean = _sanitize_rules(rules)
    await db.ui_rules.update_one(
        {"key": "main"},
        {"$set": {"rules": clean, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, "rules": clean}


# ── Role Experience Manager (Etapa 1.3) ───────────────────────────────────────
DEFAULT_PROFILES = {
    "client": {"entry_route": "/client", "default_theme": "system", "layout_surface": "client_home"},
    "specialist": {"entry_route": "/specialist", "default_theme": "system", "layout_surface": "specialist_home"},
    "admin": {"entry_route": "/admin", "default_theme": "system", "layout_surface": ""},
    "franchise_admin": {"entry_route": "/franciza", "default_theme": "system", "layout_surface": ""},
}
_THEMES = {"system", "dark", "light"}


async def _get_profile(role: str) -> dict:
    base = DEFAULT_PROFILES.get(role)
    if base is None:
        raise HTTPException(404, "Rol necunoscut.")
    doc = await db.experience_profiles.find_one({"role": role}, {"_id": 0}) or {}
    return {"role": role, **base, **{k: doc[k] for k in ("entry_route", "default_theme", "layout_surface") if k in doc}}


@router.get("/experience/profile/{role}")
async def public_experience_profile(role: str):
    return await _get_profile(role)


@router.get("/admin/experience-profiles")
async def admin_get_profiles(_admin=Depends(require_role("admin"))):
    return {"profiles": [await _get_profile(r) for r in DEFAULT_PROFILES], "themes": sorted(_THEMES), "surfaces": list(SURFACE_META.keys())}


@router.put("/admin/experience-profiles/{role}")
async def admin_put_profile(role: str, payload: dict = Body(...), admin=Depends(require_role("admin"))):
    if role not in DEFAULT_PROFILES:
        raise HTTPException(404, "Rol necunoscut.")
    updates = {}
    if isinstance(payload.get("entry_route"), str) and payload["entry_route"].startswith("/"):
        updates["entry_route"] = payload["entry_route"][:100]
    if payload.get("default_theme") in _THEMES:
        updates["default_theme"] = payload["default_theme"]
    if payload.get("layout_surface") in SURFACE_META or payload.get("layout_surface") == "":
        updates["layout_surface"] = payload.get("layout_surface")
    if not updates:
        raise HTTPException(400, "Nimic valid de actualizat.")
    await db.experience_profiles.update_one(
        {"role": role},
        {"$set": {**updates, "tenant_id": TENANT, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, "profile": await _get_profile(role)}


# ── Theme & Content Manager ───────────────────────────────────────────────────
DEFAULT_CONTENT = {
    "banner": {"active": False, "text": "🎉 Ofertă de lansare: primul proiect de design interior cu 20% reducere!", "link": "/design-interior", "link_label": "Vezi oferta", "variant": "promo"},
    "hero": {"title1": "", "title2": "", "title3": "", "subtitle": ""},
    "entries": [],
}


async def _get_content() -> dict:
    doc = await db.site_content.find_one({"key": "main"})
    if not doc:
        return dict(DEFAULT_CONTENT)
    return {
        "banner": {**DEFAULT_CONTENT["banner"], **(doc.get("banner") or {})},
        "hero": {**DEFAULT_CONTENT["hero"], **(doc.get("hero") or {})},
        "entries": doc.get("entries") or [],
    }


@router.get("/public/site-content")
async def public_content():
    return await _get_content()


@router.get("/admin/site-content")
async def admin_get_content(_admin=Depends(require_role("admin"))):
    return await _get_content()


@router.put("/admin/site-content")
async def admin_put_content(payload: dict = Body(...), admin=Depends(require_role("admin"))):
    banner = payload.get("banner") or {}
    hero = payload.get("hero") or {}
    entries = [
        {"key": str(e.get("key", ""))[:80], "value": str(e.get("value", ""))[:2000]}
        for e in (payload.get("entries") or []) if isinstance(e, dict) and str(e.get("key", "")).strip()
    ]
    clean = {
        "banner": {
            "active": bool(banner.get("active")),
            "text": str(banner.get("text", ""))[:300],
            "link": str(banner.get("link", ""))[:300],
            "link_label": str(banner.get("link_label", ""))[:60],
            "variant": banner.get("variant") if banner.get("variant") in ("promo", "info", "warning") else "info",
        },
        "hero": {k: str(hero.get(k, ""))[:300] for k in ("title1", "title2", "title3", "subtitle")},
        "entries": entries,
    }
    await db.site_content.update_one(
        {"key": "main"},
        {"$set": {**clean, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, **clean}
