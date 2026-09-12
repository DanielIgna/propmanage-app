"""PropManage · Page Registry (Configuration Layer, Task 7 P0+P1).

Canonical source of truth for per-page configuration:
- menu_label vs h1 vs seo_title vs og_title (all independent)
- allowed_roles / allowed_tiers / device visibility / feature_flag
- DRAFT → PUBLISH → LIVE workflow with versioning
- Backward fallback to db.cms_content and db.app_settings.seo when the page
  document has empty fields (progressive adoption without breaking existing SEO).

Collections:
- `pages`         : one doc per page key. Fields:
    key (str, unique), route (str, read-only), status, updated_at, updated_by,
    live { menu_label, h1, subtitle, seo_title, seo_description, og_title,
           og_description, allowed_roles[], allowed_tiers[], desktop_visible,
           mobile_visible, feature_flag, version },
    draft { ...same shape, optional }
- `pages_versions`: append-only snapshots per publish (page_key, version,
    snapshot, created_at, created_by, published_at, published_by)

Routes:
- Admin (require_role admin/operator):
    GET    /api/admin/pages
    GET    /api/admin/pages/{key}
    PUT    /api/admin/pages/{key}                 -> writes to draft
    POST   /api/admin/pages/{key}/publish
    POST   /api/admin/pages/{key}/discard-draft
    POST   /api/admin/pages/{key}/reset
    POST   /api/admin/pages/{key}/restore/{version}
    GET    /api/admin/pages/{key}/versions
    GET    /api/admin/config-history
- Public:
    GET    /api/public/pages/{key}                -> resolved LIVE bundle
"""
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role


logger = logging.getLogger("propmanage.pages_registry")

router = APIRouter(prefix="/api/admin", tags=["pages-registry"])
public_router = APIRouter(prefix="/api/public", tags=["pages-registry-public"])


# ------------------------------------------------------------------
# Default page inventory (source-of-truth for reset + first bootstrap).
# ------------------------------------------------------------------
def _p(key: str, route: str, menu_label: str, h1: str, subtitle: str, *,
       seo_title: str = "", seo_description: str = "",
       og_title: str = "", og_description: str = "",
       seo_key: str = "", cms_map: Optional[Dict[str, str]] = None,
       allowed_roles: Optional[List[str]] = None,
       allowed_tiers: Optional[List[str]] = None,
       desktop_visible: bool = True, mobile_visible: bool = True,
       feature_flag: str = "") -> Dict[str, Any]:
    """Compact factory for default page dicts."""
    return {
        "key": key,
        "route": route,
        "seo_key": seo_key,  # legacy key inside app_settings.seo (for backward fallback)
        "cms_map": cms_map or {},  # legacy CMS keys for h1/subtitle backward fallback
        "menu_label": menu_label,
        "h1": h1,
        "subtitle": subtitle,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "og_title": og_title or seo_title,
        "og_description": og_description or seo_description,
        "allowed_roles": allowed_roles or [],  # empty = public
        "allowed_tiers": allowed_tiers or [],
        "desktop_visible": desktop_visible,
        "mobile_visible": mobile_visible,
        "feature_flag": feature_flag,
    }


DEFAULT_PAGES: List[Dict[str, Any]] = [
    _p("home", "/", "Acasă",
       h1="Cartea Digitală a Casei Tale.",
       subtitle="Documentele casei, istoricul lucrărilor, mentenanța și specialiștii verificați — într-un singur loc.",
       seo_title="PropManage — Cartea Digitală a Casei Tale · Documente, istoric, specialiști",
       seo_description="Cartea Digitală a Casei Tale — documentele proprietății, istoricul lucrărilor, mentenanța și specialiștii verificați ai casei, într-un singur loc.",
       seo_key="home",
       cms_map={"h1": "hero.title1", "subtitle": "hero.subtitle"}),

    _p("pricing", "/pricing", "Tarife",
       h1="Un plan. Fără complicații.",
       subtitle="Cont gratuit pentru începători. Când vrei să folosești House Health, activezi Basic. Fără angajament pe termen lung.",
       seo_title="PropManage · Tarife — Plan Basic 9€/lună",
       seo_description="Cont gratuit + planul Basic 9€/lună pentru House Health complet. Activezi când vrei, oprești când vrei.",
       seo_key="pricing"),

    _p("whyus", "/de-ce-noi", "De ce noi",
       h1="De ce există PropManage?",
       subtitle="Pentru că fiecare casă merită o memorie digitală structurată — și fiecare proprietar merită specialiști în care poate avea încredere.",
       seo_title="De ce PropManage · Misiunea din spatele Cărții Digitale a Casei",
       seo_description="PropManage aduce transparență, control și memorie tehnică pentru fiecare locuință — de la documente la specialiști verificați.",
       seo_key="whyus"),

    _p("estate", "/imobile-verificate", "Imobile Verificate",
       h1="Proprietăți cu audit tehnic și Digital Twin.",
       subtitle="Cumperi și vinzi cu încredere: fiecare listare are audit tehnic complet și replica digitală a proprietății.",
       seo_title="Imobile Verificate · Audit tehnic + Digital Twin",
       seo_description="Imobile verificate cu audit tehnic complet și replica digitală 3D. Cumperi cu încredere, vinzi cu credibilitate.",
       seo_key="estate"),

    _p("sell", "/imobile-verificate/sell", "Vinde-ți imobilul",
       h1="Vinde-ți imobilul cu credibilitate.",
       subtitle="Listează-ți proprietatea cu audit tehnic complet și Digital Twin — vinzi mai repede, la un preț real.",
       seo_title="Vinde-ți imobilul · Cu audit tehnic și Digital Twin",
       seo_description="Listează-ți proprietatea cu credibilitate — audit tehnic complet, Digital Twin 3D și comision transparent 2.5%.",
       seo_key="sell"),

    _p("marketplace", "/marketplace", "Marketplace specialiști",
       h1="Marketplace de specialiști verificați.",
       subtitle="Alege specialiști cu documente verificate, cu istoric real și cu recenzii pe fiecare intervenție.",
       seo_title="Marketplace Specialiști · Verificați, cu istoric real",
       seo_description="Instalatori, electricieni, zugravi, designeri — cu documente verificate, istoric transparent și recenzii reale."),

    _p("interior_design", "/design-interior", "Design Interior",
       h1="Interior Intelligence.",
       subtitle="Proiectare pe date reale, de la audit la implementare — cu specialiști și materiale verificate.",
       seo_title="Design Interior · Interior Intelligence PropManage",
       seo_description="Proiectare de interior pe date reale, de la audit la implementare. Materiale, specialiști și buget transparent.",
       seo_key="interior_design"),

    _p("design_exterior", "/design-exterior", "Design Exterior",
       h1="Amenajare exterioară.",
       subtitle="Peisagistică, grădini și spații exterioare — cu proiect, buget și specialiști verificați.",
       seo_title="Design Exterior · Amenajare curte și grădină",
       seo_description="Design exterior, peisagistică și amenajare curte — cu proiect, buget și specialiști verificați."),

    _p("arhitectura", "/arhitectura", "Arhitectură",
       h1="Proiectare arhitecturală completă.",
       subtitle="De la ideea inițială la autorizația de construire — cu arhitecți verificați.",
       seo_title="Arhitectură · Proiectare completă cu arhitecți verificați",
       seo_description="Proiectare arhitecturală de la concept la autorizație, cu arhitecți verificați pe PropManage."),

    _p("digital_twin", "/digital-twin", "Digital Twin",
       h1="Copia digitală vie a locuinței tale.",
       subtitle="Trasee ascunse, planuri, materiale, istoric — într-un Digital Twin care evoluează odată cu proprietatea.",
       seo_title="Digital Twin · Replica digitală a proprietății",
       seo_description="Digital Twin PropManage: trasee ascunse, planuri, materiale și istoric — replica digitală vie a proprietății tale."),

    _p("community", "/community", "Comunitate",
       h1="Comunitate PropManage.",
       subtitle="Discuții cu alți proprietari, sfaturi de la specialiști, articole utile despre casă.",
       seo_title="Comunitate PropManage · Proprietari și specialiști",
       seo_description="Comunitate PropManage: proprietari, specialiști, sfaturi și povești despre administrarea proprietății."),

    _p("demo", "/demo", "Vezi cum funcționează",
       h1="Un tur ghidat prin PropManage.",
       subtitle="Vezi cum arată dashboard-ul, Digital Twin, Cartea Digitală și marketplace-ul — fără cont.",
       seo_title="Demo · Cum funcționează PropManage",
       seo_description="Tur ghidat prin PropManage: dashboard, Digital Twin, Cartea Digitală a Casei și marketplace de specialiști."),

    _p("login", "/login", "Autentificare",
       h1="Bine ai revenit.",
       subtitle="Autentifică-te pentru a accesa Cartea Digitală a Casei tale.",
       seo_title="Autentificare · PropManage",
       seo_description="Autentifică-te în PropManage pentru a-ți accesa Cartea Digitală a Casei și dashboard-ul.",
       desktop_visible=True, mobile_visible=True),

    _p("register", "/register", "Creează cont",
       h1="Deschide-ți Cartea Digitală a Casei.",
       subtitle="Cont gratuit. Îți adaugi casa într-un minut și începi să acumulezi documente, lucrări și istoric.",
       seo_title="Creează cont gratuit · PropManage",
       seo_description="Creează cont gratuit PropManage și deschide-ți Cartea Digitală a Casei. Fără card bancar, fără angajament."),

    _p("devino_specialist", "/devino-specialist", "Devino specialist",
       h1="Devino specialist verificat PropManage.",
       subtitle="Acces la clienți reali, plăți protejate, istoric public verificabil — cu documentele tale la vedere.",
       seo_title="Devino specialist PropManage · Verificat, cu istoric",
       seo_description="Aplicație pentru specialiști: verificare documente, acces la clienți reali și plăți protejate prin Stripe."),

    _p("devino_francizat", "/devino-francizat", "Devino francizat",
       h1="PropManage · Franciza locală.",
       subtitle="Deschide un teritoriu PropManage în orașul tău — cu suport tehnic, brand și playbook.",
       seo_title="Devino francizat PropManage · Teritorii disponibile",
       seo_description="Franciza PropManage: deschide un teritoriu local cu suport tehnic, brand consacrat și playbook complet."),

    _p("privacy", "/privacy", "Politica de confidențialitate",
       h1="Politica de confidențialitate.",
       subtitle="Cum îți colectăm, folosim și protejăm datele — pe scurt și în text integral.",
       seo_title="Politica de confidențialitate · PropManage",
       seo_description="Politica de confidențialitate PropManage — GDPR-compliant, transparent, pe scurt și integral."),

    _p("terms", "/terms", "Termeni și condiții",
       h1="Termeni și condiții.",
       subtitle="Regulile de folosire ale platformei PropManage.",
       seo_title="Termeni și condiții · PropManage",
       seo_description="Termeni și condiții de utilizare a platformei PropManage."),

    _p("cookies", "/cookies", "Politica cookie",
       h1="Politica de cookie.",
       subtitle="Ce cookie-uri folosim și cum le poți controla.",
       seo_title="Politica de cookie · PropManage",
       seo_description="Ce cookie-uri folosește PropManage și cum le poți gestiona."),

    _p("trust", "/trust", "Trust Center",
       h1="Trust Center.",
       subtitle="Cum protejăm datele, cum funcționează plățile și cum verificăm specialiștii.",
       seo_title="Trust Center · Securitate, plăți, verificări",
       seo_description="Trust Center PropManage — securitate, plăți protejate și verificarea specialiștilor."),
]


DEFAULT_MAP = {p["key"]: p for p in DEFAULT_PAGES}
STATUS_ALLOWED = {"active", "hidden", "draft"}
DEVICE_KEYS = {"desktop_visible", "mobile_visible"}
TEXT_FIELDS = {"menu_label", "h1", "subtitle", "seo_title", "seo_description",
               "og_title", "og_description", "feature_flag"}
LIST_FIELDS = {"allowed_roles", "allowed_tiers"}
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,60}$")


# ------------------------------------------------------------------
# Audit + persistence helpers.
# ------------------------------------------------------------------
async def _audit(action: str, user: dict, page_key: str,
                 before: Optional[dict] = None, after: Optional[dict] = None):
    """Reuses the existing admin_audit_log collection (no duplicate audit system)."""
    try:
        await db.admin_audit_log.insert_one({
            "action": action,
            "actor_id": str(user.get("id") or user.get("_id") or ""),
            "actor_name": user.get("name") or user.get("email") or "",
            "actor_email": user.get("email") or "",
            "target": {"type": "page", "id": page_key, "label": page_key},
            "before": before,
            "after": after,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:  # noqa: BLE001
        logger.warning("[pages] audit insert failed: %s", exc)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_live() -> dict:
    return {
        "menu_label": "", "h1": "", "subtitle": "",
        "seo_title": "", "seo_description": "",
        "og_title": "", "og_description": "",
        "allowed_roles": [], "allowed_tiers": [],
        "desktop_visible": True, "mobile_visible": True,
        "feature_flag": "", "version": 0,
    }


def _live_from_default(default: dict) -> dict:
    """Convert a DEFAULT_PAGES entry into an editable LIVE bundle."""
    return {
        "menu_label": default.get("menu_label", ""),
        "h1": default.get("h1", ""),
        "subtitle": default.get("subtitle", ""),
        "seo_title": default.get("seo_title", ""),
        "seo_description": default.get("seo_description", ""),
        "og_title": default.get("og_title", ""),
        "og_description": default.get("og_description", ""),
        "allowed_roles": list(default.get("allowed_roles") or []),
        "allowed_tiers": list(default.get("allowed_tiers") or []),
        "desktop_visible": bool(default.get("desktop_visible", True)),
        "mobile_visible": bool(default.get("mobile_visible", True)),
        "feature_flag": default.get("feature_flag", ""),
        "version": 1,
    }


async def _bootstrap_if_empty() -> None:
    count = await db.pages.count_documents({})
    if count > 0:
        # Ensure the concurrent-publish safety index exists (P3.1) — cheap idempotent op.
        try:
            await db.pages_versions.create_index(
                [("page_key", 1), ("version", 1)], unique=True, name="uniq_page_version"
            )
        except Exception:  # noqa: BLE001
            pass
        return
    now = _now()
    docs = []
    for d in DEFAULT_PAGES:
        docs.append({
            "key": d["key"],
            "route": d["route"],
            "status": "active",
            "seo_key": d.get("seo_key", ""),
            "cms_map": d.get("cms_map", {}),
            "live": _live_from_default(d),
            "draft": None,
            "created_at": now,
            "updated_at": now,
            "updated_by": "bootstrap",
        })
    if docs:
        await db.pages.insert_many(docs)
        # Create unique index on pages_versions so concurrent publish cannot
        # duplicate a version number silently (P3.1).
        try:
            await db.pages_versions.create_index(
                [("page_key", 1), ("version", 1)], unique=True, name="uniq_page_version"
            )
        except Exception:  # noqa: BLE001
            pass
        logger.info("[pages] bootstrap seeded %d pages", len(docs))


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _sanitize_patch(patch: dict) -> dict:
    """Whitelist + type-coerce fields inside the LIVE/DRAFT shape."""
    out: dict = {}
    for f in TEXT_FIELDS:
        if f in patch:
            out[f] = str(patch[f] or "")[:400]
    for f in LIST_FIELDS:
        if f in patch:
            v = patch[f]
            if isinstance(v, list):
                out[f] = [str(x)[:40] for x in v if isinstance(x, (str, int))]
    for f in DEVICE_KEYS:
        if f in patch:
            out[f] = bool(patch[f])
    if "status" in patch and patch["status"] in STATUS_ALLOWED:
        out["_status"] = patch["status"]  # promoted at page-doc level, not inside live/draft
    return out


# ------------------------------------------------------------------
# Public resolver (LIVE + backward fallback to CMS + app_settings).
# ------------------------------------------------------------------
async def _resolve_public(page: dict) -> dict:
    """Merge LIVE + backward CMS/app_settings fallbacks, respecting feature_flag.

    Security:
    - If feature_flag is set AND its state is False, the public resolver signals
      a 404 to the caller by returning None. The caller endpoint MUST 404 in that
      case. (SEC-002 fix.)
    - The public payload NEVER exposes `allowed_roles`, `allowed_tiers` or the
      internal `feature_flag` key name — those are admin-only access rules. (P3.2)
    """
    live = page.get("live") or _empty_live()

    # CMS fallback for h1/subtitle when live is empty (backward compat).
    cms_map = page.get("cms_map") or {}
    cms_snapshot: dict = {}
    if cms_map:
        keys = list(cms_map.values())
        async for row in db.cms_content.find({"key": {"$in": keys}}):
            cms_snapshot[row["key"]] = row.get("value")

    # app_settings fallback for SEO (backward compat).
    seo_key = page.get("seo_key") or ""
    app_seo: dict = {}
    if seo_key:
        app_settings_doc = await db.app_settings.find_one({"_id": "app_settings"}) or {}
        app_seo = (app_settings_doc.get("seo") or {})

    def _pick(field: str, fallback_from_cms: str = "", fallback_from_seo: str = "") -> str:
        v = (live.get(field) or "").strip()
        if v:
            return v
        if fallback_from_cms:
            cms_key = cms_map.get(field) or ""
            if cms_key and cms_snapshot.get(cms_key):
                return str(cms_snapshot.get(cms_key))
        if fallback_from_seo and seo_key:
            return str(app_seo.get(f"{seo_key}_{fallback_from_seo}") or "")
        return ""

    # Feature flag gate — SEC-002: when flag exists and is OFF, refuse to serve.
    ff = (live.get("feature_flag") or "").strip()
    if ff:
        cfg = await db.feature_config.find_one({"_id": "config"}) or {}
        feats = cfg.get("features") or []
        found = next((f for f in feats if f.get("key") == ff), None)
        if found is not None and not bool(found.get("enabled", True)):
            return None  # public MUST 404

    h1 = _pick("h1", fallback_from_cms="h1")
    subtitle = _pick("subtitle", fallback_from_cms="subtitle")
    seo_title = _pick("seo_title", fallback_from_seo="title")
    seo_description = _pick("seo_description", fallback_from_seo="description")
    og_title = (live.get("og_title") or "").strip() or seo_title
    og_description = (live.get("og_description") or "").strip() or seo_description

    # P3.2: strip internal access rules from public payload.
    return {
        "key": page.get("key"),
        "route": page.get("route"),
        "status": page.get("status", "active"),
        "menu_label": live.get("menu_label") or "",
        "h1": h1,
        "subtitle": subtitle,
        "seo_title": seo_title,
        "seo_description": seo_description,
        "og_title": og_title,
        "og_description": og_description,
        "desktop_visible": bool(live.get("desktop_visible", True)),
        "mobile_visible": bool(live.get("mobile_visible", True)),
        "version": live.get("version", 0),
        "updated_at": page.get("updated_at"),
    }


# ==================================================================
# Admin endpoints
# ==================================================================
class PagePatch(BaseModel):
    menu_label: Optional[str] = None
    h1: Optional[str] = None
    subtitle: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    allowed_tiers: Optional[List[str]] = None
    desktop_visible: Optional[bool] = None
    mobile_visible: Optional[bool] = None
    feature_flag: Optional[str] = None
    status: Optional[str] = Field(default=None, description="active | hidden | draft")


@router.get("/pages")
async def list_pages(status: Optional[str] = None,
                     _user: dict = Depends(require_role("admin", "operator"))):
    await _bootstrap_if_empty()
    q: dict = {}
    if status and status in STATUS_ALLOWED:
        q["status"] = status
    cur = db.pages.find(q, {"_id": 0}).sort("key", 1)
    items = [d async for d in cur]
    return {"items": items, "count": len(items)}


@router.get("/pages/{key}")
async def get_page(key: str, user: dict = Depends(require_role("admin", "operator"))):
    await _bootstrap_if_empty()
    page = await db.pages.find_one({"key": key}, {"_id": 0})
    if not page:
        raise HTTPException(404, f"Page not found: {key}")
    return page


@router.put("/pages/{key}")
async def update_page_draft(key: str, patch: PagePatch,
                            user: dict = Depends(require_role("admin", "operator"))):
    """Writes into the DRAFT slot. LIVE stays untouched until publish."""
    await _bootstrap_if_empty()
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, f"Page not found: {key}")

    incoming = _sanitize_patch(patch.model_dump(exclude_none=True))
    if not incoming:
        raise HTTPException(400, "No editable fields provided")

    status_change = incoming.pop("_status", None)

    # Merge into current draft (or seed draft from live).
    current_draft = page.get("draft") or {**(page.get("live") or _empty_live())}
    for k, v in incoming.items():
        current_draft[k] = v

    update_set = {
        "draft": current_draft,
        "updated_at": _now(),
        "updated_by": str(user.get("email") or user.get("id") or ""),
    }
    if status_change:
        update_set["status"] = status_change

    await db.pages.update_one({"key": key}, {"$set": update_set})
    await _audit("page.draft.update", user, key,
                 before={"draft": page.get("draft")},
                 after={"draft": current_draft, "status_change": status_change})
    fresh = await db.pages.find_one({"key": key}, {"_id": 0})
    return {"ok": True, "page": fresh, "has_draft": True}


@router.post("/pages/{key}/discard-draft")
async def discard_draft(key: str, user: dict = Depends(require_role("admin", "operator"))):
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, f"Page not found: {key}")
    if not page.get("draft"):
        return {"ok": True, "no_draft": True}
    await db.pages.update_one(
        {"key": key},
        {"$set": {"draft": None, "updated_at": _now(),
                  "updated_by": str(user.get("email") or "")}},
    )
    await _audit("page.draft.discard", user, key,
                 before={"draft": page.get("draft")}, after={"draft": None})
    return {"ok": True, "discarded": True}


@router.post("/pages/{key}/publish")
async def publish_page(key: str, user: dict = Depends(require_role("admin", "operator"))):
    """Publishes DRAFT → LIVE and creates a version snapshot in pages_versions."""
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, f"Page not found: {key}")
    draft = page.get("draft")
    if not draft:
        raise HTTPException(400, "Nothing to publish — draft is empty")

    live = {**(page.get("live") or _empty_live()), **draft}
    # Version increments monotonically from current LIVE, never resets on restore.
    current_live_version = int((page.get("live") or {}).get("version") or 0)
    live["version"] = current_live_version + 1

    # Snapshot old live BEFORE overwriting.
    old_live = page.get("live") or None
    now = _now()
    await db.pages_versions.insert_one({
        "page_key": key,
        "version": int((old_live or {}).get("version") or 0),
        "snapshot": old_live,
        "created_at": page.get("updated_at"),
        "created_by": page.get("updated_by"),
        "published_at": now,
        "published_by": str(user.get("email") or user.get("id") or ""),
    })

    await db.pages.update_one(
        {"key": key},
        {"$set": {"live": live, "draft": None, "status": "active",
                  "updated_at": now,
                  "updated_by": str(user.get("email") or "")}},
    )
    await _audit("page.publish", user, key,
                 before={"live": old_live}, after={"live": live})
    fresh = await db.pages.find_one({"key": key}, {"_id": 0})
    return {"ok": True, "page": fresh, "version": live["version"]}


@router.post("/pages/{key}/reset")
async def reset_page(key: str, user: dict = Depends(require_role("admin"))):
    """Revert page to seed defaults (LIVE + clears DRAFT). Records a version snapshot first."""
    if key not in DEFAULT_MAP:
        raise HTTPException(404, f"No default template for page: {key}")
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, f"Page not found: {key}")
    default = DEFAULT_MAP[key]
    fresh_live = _live_from_default(default)
    # snapshot current live
    await db.pages_versions.insert_one({
        "page_key": key,
        "version": int((page.get("live") or {}).get("version") or 0),
        "snapshot": page.get("live"),
        "created_at": page.get("updated_at"),
        "created_by": page.get("updated_by"),
        "published_at": _now(),
        "published_by": str(user.get("email") or "reset"),
        "note": "reset-to-defaults",
    })
    fresh_live["version"] = int((page.get("live") or {}).get("version") or 0) + 1
    await db.pages.update_one(
        {"key": key},
        {"$set": {"live": fresh_live, "draft": None, "status": "active",
                  "seo_key": default.get("seo_key", ""),
                  "cms_map": default.get("cms_map", {}),
                  "updated_at": _now(),
                  "updated_by": str(user.get("email") or "")}},
    )
    await _audit("page.reset", user, key, after={"live": fresh_live})
    return {"ok": True, "page": await db.pages.find_one({"key": key}, {"_id": 0})}


@router.get("/pages/{key}/versions")
async def list_versions(key: str, limit: int = 20,
                        _user: dict = Depends(require_role("admin", "operator"))):
    limit = max(1, min(limit, 50))
    cur = db.pages_versions.find({"page_key": key}, {"_id": 0}).sort("published_at", -1).limit(limit)
    items = [d async for d in cur]
    return {"items": items, "count": len(items)}


@router.get("/pages/{key}/preview")
async def admin_preview(key: str,
                        user: dict = Depends(require_role("admin", "operator"))):
    """Preview overlay: returns the page as it would look AFTER publish.

    Merges DRAFT over LIVE (if a draft exists) and resolves the same fallback
    chain as the public endpoint, WITHOUT touching LIVE state and WITHOUT
    exposing internal access rules. Admin/operator authorization only.
    """
    await _bootstrap_if_empty()
    if not KEY_RE.match(key):
        raise HTTPException(400, "Invalid page key")
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, "Page not found")

    draft = page.get("draft")
    live = page.get("live") or _empty_live()
    if draft:
        # Simulate publish: LIVE ← LIVE ∪ DRAFT (draft wins per field).
        simulated = {**live, **draft}
    else:
        simulated = live

    # Temporarily rebind live for the resolver, then restore.
    resolved_page = {**page, "live": simulated, "status": "active"}
    resolved = await _resolve_public(resolved_page)
    # Feature-flag OFF → resolver returns None (public would get 404). Preview
    # must still show the admin what the page WOULD look like, so we rebuild it
    # below and mark honestly that the flag currently blocks the public page.
    flag_blocked = resolved is None
    if resolved is None:
        # Rebuild without feature-flag suppression by inlining the logic.
        cms_map = page.get("cms_map") or {}
        seo_key = page.get("seo_key") or ""
        app_settings_doc = await db.app_settings.find_one({"_id": "app_settings"}) or {}
        app_seo = (app_settings_doc.get("seo") or {})
        cms_snapshot: dict = {}
        if cms_map:
            async for row in db.cms_content.find({"key": {"$in": list(cms_map.values())}}):
                cms_snapshot[row["key"]] = row.get("value")

        def _pick(field: str, cms_field: str = "", seo_field: str = "") -> str:
            v = (simulated.get(field) or "").strip()
            if v:
                return v
            if cms_field and cms_map.get(field) and cms_snapshot.get(cms_map[field]):
                return str(cms_snapshot.get(cms_map[field]))
            if seo_field and seo_key:
                return str(app_seo.get(f"{seo_key}_{seo_field}") or "")
            return ""

        h1 = _pick("h1", "h1")
        subtitle = _pick("subtitle", "subtitle")
        seo_title = _pick("seo_title", seo_field="title")
        seo_description = _pick("seo_description", seo_field="description")
        og_title = (simulated.get("og_title") or "").strip() or seo_title
        og_description = (simulated.get("og_description") or "").strip() or seo_description
        resolved = {
            "key": page.get("key"),
            "route": page.get("route"),
            "status": page.get("status", "active"),
            "menu_label": simulated.get("menu_label") or "",
            "h1": h1, "subtitle": subtitle,
            "seo_title": seo_title, "seo_description": seo_description,
            "og_title": og_title, "og_description": og_description,
            "desktop_visible": bool(simulated.get("desktop_visible", True)),
            "mobile_visible": bool(simulated.get("mobile_visible", True)),
            "version": simulated.get("version", 0),
            "updated_at": page.get("updated_at"),
        }

    return {
        "ok": True,
        "preview": True,
        "source": "draft" if draft else "live",
        "has_draft": bool(draft),
        "feature_flag_would_block": flag_blocked,
        "data": resolved,
    }


@router.post("/pages/{key}/restore/{version}")
async def restore_version(key: str, version: int,
                          user: dict = Depends(require_role("admin"))):
    """Restore = create a NEW draft from a previous version snapshot.
    Does NOT delete history — publishing that draft will create yet another version.
    """
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, f"Page not found: {key}")
    ver = await db.pages_versions.find_one({"page_key": key, "version": int(version)})
    if not ver or not ver.get("snapshot"):
        raise HTTPException(404, f"Version not found: {version}")
    snap = ver["snapshot"]
    await db.pages.update_one(
        {"key": key},
        {"$set": {"draft": snap, "updated_at": _now(),
                  "updated_by": str(user.get("email") or "restore")}},
    )
    await _audit("page.restore", user, key,
                 before={"live": page.get("live")}, after={"draft_from_version": version})
    return {"ok": True, "restored_into_draft": True, "version": version}


@router.get("/config-history")
async def config_history(limit: int = 50, entity_type: Optional[str] = None,
                         actor: Optional[str] = None,
                         _user: dict = Depends(require_role("admin", "operator"))):
    """Unified admin config history (VIEW over admin_audit_log). No new audit system.

    Security: the config-surface allowlist is ALWAYS applied, even when the caller
    supplies `actor` or `entity_type` filters. This prevents an operator from using
    the actor filter as an escape hatch to read non-config audit entries (SEC-001).
    """
    limit = max(1, min(limit, 200))
    config_types = ["page", "cms_key", "menu", "app_settings", "feature",
                    "feature_config", "design_tokens", "config_io", "snapshot",
                    "renewal_reminder"]
    q: dict = {}
    if entity_type and entity_type in config_types:
        q["target.type"] = entity_type
    else:
        q["target.type"] = {"$in": config_types}
    if actor:
        q["actor_email"] = actor
    cur = db.admin_audit_log.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    items = [d async for d in cur]
    return {"items": items, "count": len(items)}


# ==================================================================
# Public endpoint (LIVE resolved bundle)
# ==================================================================
@public_router.get("/pages/{key}")
async def public_get_page(key: str):
    await _bootstrap_if_empty()
    if not KEY_RE.match(key):
        raise HTTPException(400, "Invalid page key")
    page = await db.pages.find_one({"key": key})
    if not page:
        raise HTTPException(404, "Page not found")
    if page.get("status") != "active":
        # Hide draft/hidden pages from public consumers.
        raise HTTPException(404, "Page not published")
    resolved = await _resolve_public(page)
    if resolved is None:
        # Feature flag OFF — refuse (SEC-002).
        raise HTTPException(404, "Page not available")
    return resolved
