"""Meniu de navigare unificat (Desktop + Mobile), administrat din CMS.

Un singur sistem de navigare stocat în DB — colecția `site_menu` (doc key="main").
Public: GET /api/public/site-menu (doar iteme active; vizibilitatea o filtrează frontend-ul).
Admin: GET/PUT /api/admin/site-menu + POST reset la structura implicită.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from db import db
from deps import require_role

router = APIRouter(prefix="/api", tags=["site-menu"])
logger = logging.getLogger("propmanage.site_menu")

# visibility: "all" | "guests" (doar vizitatori) | "auth" (doar autentificați)
# dest_type (servicii): "internal" | "marketplace" | "external" | "none"
MENU_VERSION = 2


def _svc(id, label, href, icon, *, active, category, description, dest_type="internal", providers=None):
    return {
        "id": id, "label": label, "href": href, "icon": icon,
        "active": active, "visible_site": active, "visible_marketplace": dest_type == "marketplace",
        "visibility": "all", "category": category, "description": description,
        "image": "", "dest_type": dest_type, "providers": providers or [], "children": [],
    }


# CONFIG BETA: active DOAR Imobile Verificate, Design Interior, Digital Twin, Mobilier la comandă.
SERVICE_DEFAULTS = [
    _svc("imobile_verificate", "Imobile Verificate", "/imobile-verificate", "BadgeCheck",
         active=True, category="imobiliare", description="Proprietăți cu audit tehnic complet și Digital Twin — cumperi și vinzi cu încredere."),
    _svc("design_interior", "Design Interior", "/design-interior", "Palette",
         active=True, category="proiectare", description="Interior Intelligence — proiectare pe date reale, de la audit la implementare."),
    _svc("digital_twin", "Digital Twin", "/#twin", "Box",
         active=True, category="tehnologie", description="Copia digitală vie a locuinței: trasee ascunse, planuri, materiale, istoric."),
    _svc("mobilier", "Mobilier la comandă", "/servicii/mobilier", "Armchair",
         active=True, category="amenajare", dest_type="external",
         description="Parteneri verificați pentru mobilier la comandă — de la proiect la montaj."),
    _svc("design_exterior", "Design Exterior", "/design-exterior", "Trees",
         active=False, category="proiectare", description="Amenajare exterioară și peisagistică."),
    _svc("arhitectura", "Arhitectură", "/arhitectura", "Compass",
         active=False, category="proiectare", description="Proiectare arhitecturală completă."),
    _svc("constructii", "Construcții", "/marketplace?categorie=constructii", "Hammer",
         active=False, category="executie", dest_type="marketplace", description="Echipe de construcții verificate."),
    _svc("renovari", "Renovări", "/marketplace?categorie=renovari", "Paintbrush",
         active=False, category="executie", dest_type="marketplace", description="Renovări complete sau parțiale."),
    _svc("instalatii", "Instalații", "/marketplace?categorie=instalatii", "Wrench",
         active=False, category="executie", dest_type="marketplace", description="Instalatori autorizați: electric, sanitar, HVAC."),
    _svc("amenajari", "Amenajări", "/marketplace?categorie=amenajari", "Brush",
         active=False, category="executie", dest_type="marketplace", description="Amenajări interioare și exterioare."),
    _svc("specialisti", "Specialiști", "/marketplace", "Users",
         active=False, category="marketplace", dest_type="marketplace",
         description="Marketplace-ul de specialiști verificați — în dezvoltare, se activează din Admin când e complet."),
    _svc("consultanta", "Consultanță", "/marketplace?categorie=consultanta", "MessageCircle",
         active=False, category="servicii", dest_type="marketplace", description="Consultanță tehnică și imobiliară."),
]

DEFAULT_MENU = [
    {"id": "acasa", "label": "Acasă", "href": "/", "icon": "Home", "active": True, "visibility": "all", "children": []},
    {"id": "servicii", "label": "Servicii", "href": "", "icon": "Layers", "active": True, "visibility": "all",
     "children": [dict(s) for s in SERVICE_DEFAULTS]},
    {"id": "proprietari", "label": "Pentru Proprietari", "href": "", "icon": "KeyRound", "active": True, "visibility": "all", "children": [
        {"id": "cum_functioneaza", "label": "Cum funcționează", "href": "/#journey", "icon": "PlayCircle", "active": True, "visibility": "all"},
        {"id": "beneficii", "label": "Beneficii", "href": "/de-ce-noi", "icon": "Sparkles", "active": True, "visibility": "all"},
        {"id": "tarife", "label": "Tarife", "href": "/preturi", "icon": "CircleDollarSign", "active": True, "visibility": "all"},
        {"id": "faq", "label": "Întrebări frecvente", "href": "/#faq", "icon": "HelpCircle", "active": True, "visibility": "all"},
    ]},
    {"id": "companie", "label": "Companie", "href": "", "icon": "Building2", "active": True, "visibility": "all", "children": [
        {"id": "despre", "label": "Despre noi", "href": "/de-ce-noi", "icon": "Info", "active": True, "visibility": "all"},
        {"id": "blog", "label": "Blog", "href": "/community", "icon": "BookOpen", "active": True, "visibility": "all"},
        {"id": "contact", "label": "Contact", "href": "mailto:contact@propmanage.ro", "icon": "Mail", "active": True, "visibility": "all"},
    ]},
    {"id": "cont_guest", "label": "Cont", "href": "", "icon": "UserCircle", "active": True, "visibility": "guests", "children": [
        {"id": "login", "label": "Autentificare", "href": "/login", "icon": "LogIn", "active": True, "visibility": "guests"},
        {"id": "register", "label": "Creează cont", "href": "/register", "icon": "UserPlus", "active": True, "visibility": "guests"},
    ]},
    {"id": "cont_auth", "label": "Contul meu", "href": "", "icon": "UserCircle", "active": True, "visibility": "auth", "children": [
        {"id": "dashboard", "label": "Dashboard", "href": "/dashboard", "icon": "LayoutDashboard", "active": True, "visibility": "auth"},
        {"id": "proiecte", "label": "Proiectele mele", "href": "/dashboard#proiecte", "icon": "FolderKanban", "active": True, "visibility": "auth"},
        {"id": "mesaje", "label": "Mesaje", "href": "/dashboard#mesaje", "icon": "MessageSquare", "active": True, "visibility": "auth"},
        {"id": "notificari", "label": "Notificări", "href": "/dashboard#notificari", "icon": "Bell", "active": True, "visibility": "auth"},
        {"id": "setari", "label": "Setări cont", "href": "/dashboard#setari", "icon": "Settings", "active": True, "visibility": "auth"},
        {"id": "logout", "label": "Logout", "href": "#logout", "icon": "LogOut", "active": True, "visibility": "auth"},
    ]},
]

_ALLOWED_KEYS = {"id", "label", "href", "icon", "active", "visibility", "children",
                 "description", "image", "category", "dest_type", "providers",
                 "visible_site", "visible_marketplace", "page_key"}
_VISIBILITIES = {"all", "guests", "auth"}
_DEST_TYPES = {"internal", "marketplace", "external", "none"}


def _sanitize_providers(providers: list) -> list:
    out = []
    for p in providers or []:
        if not isinstance(p, dict) or not str(p.get("name", "")).strip():
            continue
        try:
            priority = int(p.get("priority") or 0)
        except (TypeError, ValueError):
            priority = 0
        out.append({
            "name": str(p["name"])[:80],
            "logo": str(p.get("logo") or "")[:300],
            "description": str(p.get("description") or "")[:300],
            "url": str(p.get("url") or "")[:300],
            "priority": priority,
            "active": bool(p.get("active", True)),
        })
    return out


def _sanitize_items(items: list, depth: int = 0) -> list:
    if depth > 1:
        return []
    out = []
    for it in items:
        if not isinstance(it, dict) or not str(it.get("label", "")).strip() or not str(it.get("id", "")).strip():
            continue
        clean = {
            "id": str(it["id"])[:60],
            "label": str(it["label"])[:80],
            "href": str(it.get("href") or "")[:300],
            "icon": str(it.get("icon") or "")[:40],
            "active": bool(it.get("active", True)),
            "visibility": it.get("visibility") if it.get("visibility") in _VISIBILITIES else "all",
            "description": str(it.get("description") or "")[:300],
            "image": str(it.get("image") or "")[:300],
            "category": str(it.get("category") or "")[:60],
            "dest_type": it.get("dest_type") if it.get("dest_type") in _DEST_TYPES else "internal",
            "providers": _sanitize_providers(it.get("providers")),
            "visible_site": bool(it.get("visible_site", True)),
            "visible_marketplace": bool(it.get("visible_marketplace", False)),
            "page_key": str(it.get("page_key") or "")[:60],  # optional link to db.pages
            "children": _sanitize_items(it.get("children") or [], depth + 1),
        }
        out.append(clean)
    return out


async def _get_menu_doc() -> dict:
    doc = await db.site_menu.find_one({"key": "main"})
    if not doc:
        doc = {"key": "main", "items": DEFAULT_MENU, "version": MENU_VERSION,
               "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.site_menu.insert_one(dict(doc))
        return doc
    if (doc.get("version") or 1) < MENU_VERSION:
        doc["items"] = _upgrade_items_v2(doc.get("items") or [])
        doc["version"] = MENU_VERSION
        await db.site_menu.update_one(
            {"key": "main"},
            {"$set": {"items": doc["items"], "version": MENU_VERSION,
                      "updated_at": datetime.now(timezone.utc).isoformat(),
                      "updated_by": "migration:service_manager_v2"}})
        logger.info("[site-menu] migrat la v2 (Service Manager + config Beta)")
    return doc


def _upgrade_items_v2(items: list) -> list:
    """v1→v2: adaugă câmpurile Service Manager + aplică config Beta pe grupul «servicii»."""
    defaults = {s["id"]: s for s in SERVICE_DEFAULTS}
    upgraded = _sanitize_items(items)
    for group in upgraded:
        if group.get("id") != "servicii":
            continue
        merged, seen = [], set()
        for child in group.get("children") or []:
            d = defaults.get(child["id"])
            if d:
                merged.append(dict(d))
            else:
                merged.append(child)
            seen.add(child["id"])
        for sid, d in defaults.items():
            if sid not in seen:
                merged.append(dict(d))
        group["children"] = merged
    return upgraded


def _public_items(items: list) -> list:
    out = []
    for it in items:
        # REGULA PLATFORMEI: un serviciu apare public doar dacă e ACTIV și VIZIBIL pe site.
        if not it.get("active", True) or not it.get("visible_site", True):
            continue
        out.append({
            "id": it["id"], "label": it["label"], "href": it.get("href", ""),
            "icon": it.get("icon", ""), "visibility": it.get("visibility", "all"),
            "children": _public_items(it.get("children") or []),
        })
    return out


def _find_service(items: list, service_id: str) -> dict | None:
    for it in items:
        if it.get("id") == service_id:
            return it
        found = _find_service(it.get("children") or [], service_id)
        if found:
            return found
    return None


@router.get("/public/service-visibility")
async def public_service_visibility():
    """Harta de vizibilitate a serviciilor — folosită de frontend pentru gating de rute."""
    doc = await _get_menu_doc()
    services = {}
    for group in doc.get("items") or []:
        if group.get("id") != "servicii":
            continue
        for c in group.get("children") or []:
            services[c["id"]] = {
                "active": bool(c.get("active", True)),
                "visible_site": bool(c.get("visible_site", True)),
                "dest_type": c.get("dest_type", "internal"),
            }
    return {"services": services}


@router.get("/public/services/{service_id}")
async def public_service_detail(service_id: str):
    """Detalii serviciu + provideri externi activi (pagina /servicii/{id})."""
    doc = await _get_menu_doc()
    svc = _find_service(doc.get("items") or [], service_id)
    if not svc or not svc.get("active", True) or not svc.get("visible_site", True):
        raise HTTPException(404, "Serviciu indisponibil.")
    providers = sorted(
        [p for p in (svc.get("providers") or []) if p.get("active", True)],
        key=lambda p: -int(p.get("priority") or 0))
    return {
        "id": svc["id"], "label": svc["label"], "description": svc.get("description", ""),
        "image": svc.get("image", ""), "category": svc.get("category", ""),
        "dest_type": svc.get("dest_type", "internal"), "href": svc.get("href", ""),
        "providers": providers,
    }


@router.get("/public/site-menu")
async def public_site_menu():
    doc = await _get_menu_doc()
    return {"items": _public_items(doc.get("items") or [])}


@router.post("/public/site-menu/track")
async def track_menu_click(request: Request, item_id: str = Body(..., embed=True), label: str = Body("", embed=True), href: str = Body("", embed=True)):
    await db.menu_clicks.insert_one({
        "item_id": str(item_id)[:60], "label": str(label)[:80], "href": str(href)[:300],
        "ts": datetime.now(timezone.utc).isoformat(),
        "authenticated": bool(request.cookies.get("access_token")),
        "tenant_id": "main",
    })
    return {"ok": True}


@router.get("/admin/site-menu/analytics")
async def menu_analytics(days: int = 30, _admin=Depends(require_role("admin"))):
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipeline = [
        {"$match": {"ts": {"$gte": since}}},
        {"$group": {"_id": {"item_id": "$item_id", "label": "$label"}, "clicks": {"$sum": 1},
                    "auth_clicks": {"$sum": {"$cond": ["$authenticated", 1, 0]}}}},
        {"$sort": {"clicks": -1}},
        {"$limit": 20},
    ]
    rows = await db.menu_clicks.aggregate(pipeline).to_list(20)
    total = await db.menu_clicks.count_documents({"ts": {"$gte": since}})
    return {"days": days, "total_clicks": total, "top": [
        {"item_id": r["_id"]["item_id"], "label": r["_id"]["label"], "clicks": r["clicks"], "auth_clicks": r["auth_clicks"]}
        for r in rows
    ]}


@router.post("/admin/site-menu/auto-reorder")
async def set_auto_reorder(enabled: bool = Body(..., embed=True), admin=Depends(require_role("admin"))):
    await db.site_menu.update_one(
        {"key": "main"},
        {"$set": {"auto_reorder": bool(enabled), "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, "auto_reorder": bool(enabled)}


@router.post("/admin/site-menu/auto-reorder/run")
async def run_auto_reorder_now(_admin=Depends(require_role("admin"))):
    result = await menu_popularity_reorder_tick(force=True)
    return {"ok": True, **result}


async def menu_popularity_reorder_tick(force: bool = False) -> dict:
    """Autonomy: reordonează sub-serviciile din grupul «Servicii» după popularitate (click-uri 30z)."""
    from datetime import timedelta
    doc = await db.site_menu.find_one({"key": "main"})
    if not doc:
        return {"status": "skipped", "reason": "no menu"}
    if not force and not doc.get("auto_reorder", True):
        return {"status": "skipped", "reason": "auto_reorder disabled"}
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    rows = await db.menu_clicks.aggregate([
        {"$match": {"ts": {"$gte": since}}},
        {"$group": {"_id": "$item_id", "clicks": {"$sum": 1}}},
    ]).to_list(500)
    clicks = {r["_id"]: r["clicks"] for r in rows}
    items = doc.get("items") or []
    changed = False
    for group in items:
        if group.get("id") != "servicii" or not group.get("children"):
            continue
        old_order = [c["id"] for c in group["children"]]
        group["children"] = sorted(group["children"], key=lambda c: -clicks.get(c["id"], 0))
        new_order = [c["id"] for c in group["children"]]
        changed = old_order != new_order
    if changed:
        await db.site_menu.update_one(
            {"key": "main"},
            {"$set": {"items": items, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": "autonomy:menu_optimizer"}},
        )
    await db.playbook_executions.insert_one({
        "playbook_id": "menu_popularity_optimizer",
        "status": "applied" if changed else "no_change",
        "human_needed": False,
        "detail": {"clicks_30d": clicks, "reordered": changed},
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"[site-menu] popularity reorder: changed={changed}")
    return {"status": "applied" if changed else "no_change", "clicks_30d": clicks}


@router.get("/admin/site-menu")
async def admin_get_menu(_admin=Depends(require_role("admin"))):
    doc = await _get_menu_doc()
    return {"items": doc.get("items") or [], "updated_at": doc.get("updated_at"), "auto_reorder": doc.get("auto_reorder", True)}


@router.put("/admin/site-menu")
async def admin_put_menu(items: list = Body(..., embed=True), admin=Depends(require_role("admin"))):
    clean = _sanitize_items(items)
    if not clean:
        raise HTTPException(400, "Meniul nu poate fi gol.")
    await db.site_menu.update_one(
        {"key": "main"},
        {"$set": {"items": clean, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, "items": clean}


@router.post("/admin/site-menu/reset")
async def admin_reset_menu(admin=Depends(require_role("admin"))):
    await db.site_menu.update_one(
        {"key": "main"},
        {"$set": {"items": DEFAULT_MENU, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": admin.get("email")}},
        upsert=True,
    )
    return {"ok": True, "items": DEFAULT_MENU}
