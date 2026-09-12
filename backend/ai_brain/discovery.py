"""AI Brain · Discovery Engine — analizează automat aplicația reală (zero liste hardcodate).

Surse: codul frontend (App.js, pages/, components/), codul backend (routes/*.py, module),
baza de date (users.role, site_menu) și registrul de routere (routes.register.ALL_ROUTERS).
Reutilizează ai_core.code_index pentru inventarul de fișiere.
"""
import re
from pathlib import Path

from db import db

FRONTEND_SRC = Path("/app/frontend/src")
BACKEND_DIR = Path("/app/backend")

ENDPOINT_RE = re.compile(r"@(\w+)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']")
ROUTER_RE = re.compile(r"(\w+)\s*=\s*APIRouter\(([^)]*)\)")


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Frontend: rute + pagini + componente
# ---------------------------------------------------------------------------
def discover_routes() -> list:
    app = _read(FRONTEND_SRC / "App.js")
    lazy = set(re.findall(r"const\s+(\w+)\s*=\s*lazy\(", app))
    routes = []
    for m in re.finditer(r'<Route\s+path="([^"]+)"\s+element=\{<(\w+)', app):
        path, comp = m.groups()
        routes.append({"path": path, "component": comp, "lazy": comp in lazy})
    return routes


def discover_pages() -> list:
    pages = []
    for p in sorted((FRONTEND_SRC / "pages").rglob("*.jsx")):
        pages.append({"file": str(p.relative_to(FRONTEND_SRC)), "name": p.stem,
                      "area": p.relative_to(FRONTEND_SRC / "pages").parts[0] if p.parent != FRONTEND_SRC / "pages" else "root"})
    return pages


def discover_components() -> dict:
    app_components, ui_components = [], []
    for p in sorted((FRONTEND_SRC / "components").rglob("*.jsx")):
        rel = str(p.relative_to(FRONTEND_SRC))
        (ui_components if "components/ui/" in rel else app_components).append(p.stem)
    return {"app": app_components, "ui": ui_components}


# ---------------------------------------------------------------------------
# Backend: API-uri + servicii + module
# ---------------------------------------------------------------------------
def discover_apis() -> list:
    apis = []
    for p in sorted((BACKEND_DIR / "routes").glob("*.py")):
        text = _read(p)
        prefixes = {}
        for var, args in ROUTER_RE.findall(text):
            pm = re.search(r"prefix\s*=\s*[\"']([^\"']+)[\"']", args)
            prefixes[var] = pm.group(1) if pm else ""
        for m in ENDPOINT_RE.finditer(text):
            var, meth, path = m.groups()
            window = text[m.end():m.end() + 400]
            rm = re.search(r"require_role\(\s*[\"'](\w+)[\"']", window)
            guard = rm.group(1) if rm else ("authenticated" if "get_current_user" in window else "public")
            apis.append({"method": meth.upper(), "path": f"{prefixes.get(var, '')}{path}",
                         "file": p.name, "guard": guard})
    return apis


def discover_services() -> list:
    services = []
    for p in sorted(BACKEND_DIR.glob("*.py")):
        if p.stem in ("__init__",):
            continue
        first = _read(p).lstrip()[:200]
        doc = first[3:first.find("\n")].strip() if first.startswith('"""') else ""
        services.append({"name": p.stem, "kind": "module", "summary": doc[:120]})
    for d in sorted(BACKEND_DIR.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.name not in ("tests", "routes", "__pycache__"):
            services.append({"name": d.name, "kind": "package", "summary": ""})
    return services


def discover_modules(apis: list, routes: list) -> list:
    groups: dict = {}
    for a in apis:
        seg = (a["path"].split("/") + ["", ""])[2] or "root"
        g = groups.setdefault(seg, {"name": seg, "endpoints": 0, "frontend_routes": 0})
        g["endpoints"] += 1
    for r in routes:
        seg = (r["path"].split("/") + [""])[1] or "root"
        g = groups.setdefault(seg, {"name": seg, "endpoints": 0, "frontend_routes": 0})
        g["frontend_routes"] += 1
    return sorted(groups.values(), key=lambda g: -(g["endpoints"] + g["frontend_routes"]))


# ---------------------------------------------------------------------------
# Roluri + permisiuni + meniuri (DB + cod)
# ---------------------------------------------------------------------------
async def discover_roles(apis: list) -> dict:
    db_roles = [r for r in await db.users.distinct("role") if r]
    counts = {}
    for role in db_roles:
        counts[role] = await db.users.count_documents({"role": role})
    guarded = sorted({a["guard"] for a in apis if a["guard"] not in ("public", "authenticated")})
    permissions = {}
    for a in apis:
        permissions[a["guard"]] = permissions.get(a["guard"], 0) + 1
    return {"db_roles": counts, "guarded_roles": guarded,
            "all": sorted(set(db_roles) | set(guarded)), "endpoint_guards": permissions}


async def discover_menus() -> list:
    menu = await db.site_menu.find_one({"key": "main"}) or {}
    items = []
    for group in menu.get("items") or []:
        items.append({"id": group.get("id"), "label": group.get("label"),
                      "children": [{"id": c.get("id"), "label": c.get("label"),
                                    "enabled": c.get("enabled", True)} for c in group.get("children") or []]})
    return items
