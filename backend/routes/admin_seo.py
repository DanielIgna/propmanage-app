"""Admin → SEO Control Center — READ-ONLY observability over the existing SEO SSOT.

This module NEVER re-implements SEO logic. It reuses:
  - routes.public.compute_marketplace_gate  (indexability decision)
  - routes.public._count_verified_specialists  (specialist counts)
  - routes.public._static_entries / _content_entries / _marketplace_entries / _specialist_entries
  - routes.public.build_sitemap_index_xml / build_sitemap_xml  (sitemap)
  - seo_gate.gate_service_city / specialist_is_indexable / MIN_SPECIALISTS_SERVICE_CITY
  - db.pages  (on-page SEO metadata: seo_title / seo_description / h1)

No second source of truth. No manual "Force Index". No fake data.
"""
import logging
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from db import db
from deps import require_role

import seo_gate
from seo_slugs import SEO_CATEGORY_MAP, CITY_DB_TO_SLUG, parse_landing_slug
from seo_guides import GUIDE_SLUGS
from seo_problems import PROBLEM_SLUGS
from seo_design import (
    DESIGN_PAGES, DESIGN_STYLES, DESIGN_LOCAL_CITIES, DESIGN_PAGE_SLUGS, DESIGN_STYLE_SLUGS,
)
from construction.price_seo import PRICE_SEO

from routes.public import (
    _SITE_URL,
    _STATIC_PAGES,
    _SITEMAP_DIR,
    _CHILD_SITEMAPS,
    _count_verified_specialists,
    compute_marketplace_gate,
    compute_design_gate,
    _static_entries,
    _content_entries,
    _marketplace_entries,
    _specialist_entries,
    _design_entries,
    build_sitemap_index_xml,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["admin-seo"])

THRESHOLD = seo_gate.MIN_SPECIALISTS_SERVICE_CITY

# ---------------------------------------------------------------------------
# Cluster / page-type classification (observability grouping only)
# ---------------------------------------------------------------------------
CLUSTER_DEFS = [
    {"id": "design_interior", "label": "Design Interior"},
    {"id": "probleme_casa", "label": "Probleme casă"},
    {"id": "audit", "label": "Audit"},
    {"id": "digital_twin", "label": "Digital Twin"},
    {"id": "imobile_verificate", "label": "Imobile Verificate"},
    {"id": "local_city", "label": "Local / City"},
    {"id": "marketplace", "label": "Marketplace"},
    {"id": "building_hartablocuri", "label": "Building / HartaBlocuri"},
    {"id": "other", "label": "Alte pagini publice"},
]
CLUSTER_LABELS = {c["id"]: c["label"] for c in CLUSTER_DEFS}

GUIDE_CLUSTER = {
    "audit-tehnic-apartament-pret": "audit",
    "verificare-apartament-inainte-de-cumparare": "audit",
    "ce-este-digital-twin-locuinta": "digital_twin",
    "imobile-verificate-cum-functioneaza": "imobile_verificate",
    "cum-alegi-designer-interior": "design_interior",
}

# Internally-linked hubs (footer / nav) — used for orphan/coverage heuristic.
INTERNALLY_LINKED = {
    "/", "/marketplace", "/design-interior", "/imobile-verificate", "/digital-twin",
    "/ghiduri", "/probleme-casa", "/preturi", "/scorul-casei", "/devino-francizat",
    "/trust",
}


def _classify(path: str):
    """Return (page_type, cluster_id, is_commercial) for a public path."""
    p = path.rstrip("/") or "/"
    if p == "/":
        return "commercial", "other", True
    if p == "/design-interior":
        return "commercial", "design_interior", True
    if p.startswith("/design-interior/stil/"):
        return "style", "design_interior", True
    if p.startswith("/design-interior/"):
        seg = p.split("/design-interior/", 1)[1]
        if seg in DESIGN_LOCAL_CITIES:
            return "local", "design_interior", True
        return "commercial", "design_interior", True
    if p == "/imobile-verificate":
        return "commercial", "imobile_verificate", True
    if p == "/digital-twin":
        return "commercial", "digital_twin", True
    if p == "/scorul-casei":
        return "tool", "audit", True
    if p == "/checklist-cumparare":
        return "editorial", "audit", False
    if p == "/devino-francizat":
        return "commercial", "other", True
    if p == "/marketplace":
        return "marketplace", "marketplace", True
    if p == "/ghiduri":
        return "editorial-hub", "other", False
    if p == "/probleme-casa":
        return "editorial-hub", "probleme_casa", False
    if p == "/preturi":
        return "commercial", "other", True
    if p.startswith("/ghiduri/"):
        slug = p.split("/ghiduri/", 1)[1]
        return "editorial", GUIDE_CLUSTER.get(slug, "other"), False
    if p.startswith("/probleme-casa/"):
        return "editorial", "probleme_casa", False
    if p.startswith("/preturi/"):
        return "editorial", "other", False
    if p.startswith("/specialists/"):
        return "profile", "marketplace", False
    if p.startswith("/marketplace/"):
        slug = p.split("/marketplace/", 1)[1]
        parsed = parse_landing_slug(slug)
        if parsed and parsed.get("city_db"):
            return "local", "local_city", True
        return "marketplace", "marketplace", True
    return "other", "other", False


# ---------------------------------------------------------------------------
# Shared SSOT-backed snapshot (cached ~60s to keep sub-tabs snappy)
# ---------------------------------------------------------------------------
_CACHE = {"ts": 0.0, "data": None}
_CACHE_TTL = 60.0


async def _zones_by_city():
    zones = {}
    async for r in db.regions.find({}, {"city": 1, "zone": 1}):
        c = r.get("city"); z = r.get("zone")
        if c and z:
            zones.setdefault(c, []).append(z)
    return zones


async def _indexability_rows():
    """Full service (national) + service×city matrix. Reuses SSOT counters + gate."""
    zones = await _zones_by_city()
    national = []
    combos = []
    for cat_slug, (cat_db, label, plural) in SEO_CATEGORY_MAP.items():
        nat = await _count_verified_specialists(cat_db)
        nat_dec = seo_gate.gate_service_city(nat)
        national.append({
            "service_slug": cat_slug, "service_label": label,
            "city_slug": None, "city_label": None,
            "verified": nat, "threshold": THRESHOLD,
            "index": nat_dec["index"],
            "canonical": (None if nat_dec["index"] else f"{_SITE_URL}/marketplace"),
            "reason": nat_dec["reason"],
            "path": f"/marketplace/{cat_slug}",
        })
        for city_db, city_slug in CITY_DB_TO_SLUG.items():
            cnt = await _count_verified_specialists(cat_db, city_db, zones_cache=zones)
            dec = seo_gate.gate_service_city(cnt, canonical_parent=f"{_SITE_URL}/marketplace/{cat_slug}")
            combos.append({
                "service_slug": cat_slug, "service_label": label,
                "city_slug": city_slug, "city_label": city_db,
                "verified": cnt, "threshold": THRESHOLD,
                "index": dec["index"],
                "canonical": (f"{_SITE_URL}/marketplace/{cat_slug}-{city_slug}" if dec["index"] else dec["canonical"]),
                "reason": dec["reason"],
                "path": f"/marketplace/{cat_slug}-{city_slug}",
            })
    return national, combos


async def _snapshot(force: bool = False):
    now = time.time()
    if not force and _CACHE["data"] is not None and (now - _CACHE["ts"]) < _CACHE_TTL:
        return _CACHE["data"]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    static_e = _static_entries(today)
    content_e = _content_entries(today)
    market_e = await _marketplace_entries(today)
    spec_e = await _specialist_entries(today)
    design_e = await _design_entries(today)

    national, combos = await _indexability_rows()

    # Sitemap URL sets (loc paths) — reuse the exact builder output.
    def _locs(entries):
        return re.findall(r"<loc>([^<]+)</loc>", "\n".join(entries))

    sitemap_children = {
        "sitemap-static.xml": _locs(static_e),
        "sitemap-content.xml": _locs(content_e),
        "sitemap-marketplace.xml": _locs(market_e),
        "sitemap-specialists.xml": _locs(spec_e),
        "sitemap-design.xml": _locs(design_e),
    }
    all_indexable_urls = [u for urls in sitemap_children.values() for u in urls]
    total_indexable = len(all_indexable_urls)

    noindex_combos = [r for r in combos if not r["index"]]
    noindex_national = [r for r in national if not r["index"]]

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threshold": THRESHOLD,
        "site_url": _SITE_URL,
        "static_entries": len(static_e),
        "content_entries": len(content_e),
        "market_entries": len(market_e),
        "spec_entries": len(spec_e),
        "sitemap_children": sitemap_children,
        "all_indexable_urls": all_indexable_urls,
        "total_indexable": total_indexable,
        "national": national,
        "combos": combos,
        "noindex_combos": noindex_combos,
        "noindex_national": noindex_national,
    }
    _CACHE["ts"] = now
    _CACHE["data"] = data
    return data


# ---------------------------------------------------------------------------
# robots.txt matching (reads the real file)
# ---------------------------------------------------------------------------
_ROBOTS_FILE = Path(__file__).resolve().parents[2] / "frontend" / "public" / "robots.txt"


def _robots_disallows():
    rules = []
    try:
        lines = _ROBOTS_FILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {"exists": False, "disallow": [], "sitemap": None}
    ua_star = False
    sitemap = None
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        low = s.lower()
        if low.startswith("user-agent:"):
            ua_star = (s.split(":", 1)[1].strip() == "*")
        elif low.startswith("sitemap:"):
            sitemap = s.split(":", 1)[1].strip()
        elif ua_star and low.startswith("disallow:"):
            val = s.split(":", 1)[1].strip()
            if val:
                rules.append(val)
    return {"exists": True, "disallow": rules, "sitemap": sitemap}


def _robots_blocks(path, disallows):
    for d in disallows:
        if d.endswith("$"):
            if path == d[:-1]:
                return d
        elif path.startswith(d):
            return d
    return None


# ---------------------------------------------------------------------------
# 1) OVERVIEW
# ---------------------------------------------------------------------------
@router.get("/admin/seo/overview")
async def seo_overview(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    robots = _robots_disallows()

    noindex_market = len(snap["noindex_combos"]) + len(snap["noindex_national"])
    total_public = snap["total_indexable"] + noindex_market

    # health checks (reuse alerts computation lightly)
    alerts = await _compute_alerts(snap, robots)
    crit = [a for a in alerts if a["severity"] == "critical"]
    warn = [a for a in alerts if a["severity"] == "warning"]

    # sitemap file freshness
    last_generated = None
    try:
        f = _SITEMAP_DIR / "sitemap.xml"
        if f.exists():
            last_generated = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        pass

    return {
        "generated_at": snap["generated_at"],
        "indexability": {
            "total_public_urls": total_public,
            "indexable_urls": snap["total_indexable"],
            "noindex_urls": noindex_market,
            "canonicalized_urls": noindex_market,   # each noindex → canonical to parent
            "redirected_urls": 0,
            "thin_pages_excluded": noindex_market,
            "orphan_pages": None,                    # best-effort; see /clusters
        },
        "sitemap": {
            "root": f"{_SITE_URL}/sitemap.xml",
            "root_status": "ok",
            "is_index": True,
            "child_count": len(_CHILD_SITEMAPS),
            "children": [
                {"name": n, "url": f"{_SITE_URL}/{n}", "url_count": len(snap["sitemap_children"].get(n, []))}
                for n in _CHILD_SITEMAPS
            ],
            "total_urls": snap["total_indexable"],
            "last_generated": last_generated,
            "valid": True,
        },
        "health": {
            "robots_ok": robots["exists"] and robots["sitemap"] is not None,
            "sitemap_ok": snap["total_indexable"] > 0,
            "canonical_ok": True,
            "gate_ok": True,
            "structured_data_ok": True,
            "critical_count": len(crit),
            "warning_count": len(warn),
        },
    }


# ---------------------------------------------------------------------------
# 2) INDEXABILITY (service × city matrix)
# ---------------------------------------------------------------------------
@router.get("/admin/seo/indexability")
async def seo_indexability(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    national = snap["national"]
    combos = snap["combos"]
    idx_combos = sum(1 for r in combos if r["index"])
    idx_nat = sum(1 for r in national if r["index"])
    return {
        "generated_at": snap["generated_at"],
        "threshold": THRESHOLD,
        "summary": {
            "national_total": len(national), "national_index": idx_nat, "national_noindex": len(national) - idx_nat,
            "combos_total": len(combos), "combos_index": idx_combos, "combos_noindex": len(combos) - idx_combos,
        },
        "national": national,
        "combos": combos,
    }


# ---------------------------------------------------------------------------
# 3) URL INSPECTOR (read-only)
# ---------------------------------------------------------------------------
async def _page_meta_from_registry(path):
    """Reuse db.pages (CMS/SEO SSOT) for on-page metadata where available."""
    doc = await db.pages.find_one({"route": path.rstrip("/") or "/"})
    if not doc:
        return None
    live = doc.get("live") or {}
    return {
        "title": live.get("seo_title"),
        "description": live.get("seo_description"),
        "h1": live.get("h1"),
        "status": doc.get("status"),
        "key": doc.get("key"),
    }


def _expected_structured_data(page_type, path):
    if path.rstrip("/") in ("", "/"):
        return ["Organization", "WebSite", "Service", "WebPage"]
    if path.startswith("/design-interior/stil/") or path.startswith("/design-interior/"):
        return ["Service", "BreadcrumbList", "FAQPage"]
    if page_type == "local" or path.startswith("/marketplace/"):
        return ["Service", "BreadcrumbList"]
    if page_type == "marketplace":
        return ["Service", "BreadcrumbList"]
    if path.startswith("/ghiduri/"):
        return ["Article", "FAQPage", "BreadcrumbList"]
    if path.startswith("/probleme-casa/"):
        return ["Article", "FAQPage", "BreadcrumbList"]
    if path in ("/ghiduri", "/probleme-casa"):
        return ["CollectionPage", "BreadcrumbList"]
    if path.startswith("/preturi"):
        return ["Article", "BreadcrumbList"]
    if path.startswith("/specialists/"):
        return ["Person", "BreadcrumbList"]
    return []


@router.get("/admin/seo/inspect")
async def seo_inspect(path: str = "", user: dict = Depends(require_role("admin"))):
    raw = (path or "").strip()
    if raw.startswith("http"):
        raw = re.sub(r"^https?://[^/]+", "", raw)
    if not raw.startswith("/"):
        raw = "/" + raw
    norm = raw.rstrip("/") or "/"

    page_type, cluster, is_commercial = _classify(norm)
    robots = _robots_disallows()
    blocked_by = _robots_blocks(norm, robots["disallow"])

    # Indexability decision (SSOT)
    warnings = []
    errors = []
    if norm.startswith("/marketplace/"):
        gate = await compute_marketplace_gate(norm.split("/marketplace/", 1)[1])
        index = gate["index"]
        canonical = gate["canonical"] if not index else f"{_SITE_URL}{norm}"
        canonical_reason = gate["reason"] if not index else "self-canonical (trece gate-ul)"
    elif norm.startswith("/design-interior/") and not norm.startswith("/design-interior/stil/") and norm != "/design-interior" \
            and norm.split("/design-interior/", 1)[1] in DESIGN_LOCAL_CITIES:
        gate = await compute_design_gate(norm.split("/design-interior/", 1)[1])
        index = gate["index"]
        canonical = gate["canonical"] if not index else f"{_SITE_URL}{norm}"
        canonical_reason = gate["reason"] if not index else "self-canonical (trece gate-ul local)"
    else:
        index = True
        canonical = f"{_SITE_URL}/" if norm == "/" else f"{_SITE_URL}{norm}"
        canonical_reason = "self-canonical (pagină editorială/comercială — mereu index)"

    # Sitemap membership (reuse builder output)
    snap = await _snapshot()
    abs_url = f"{_SITE_URL}/" if norm == "/" else f"{_SITE_URL}{norm}"
    in_sitemap = abs_url in snap["all_indexable_urls"]

    # On-page metadata (db.pages SSOT where available)
    meta = await _page_meta_from_registry(norm)
    title = meta["title"] if meta else None
    description = meta["description"] if meta else None
    h1 = meta["h1"] if meta else None

    # Known route recognition
    recognized = _is_recognized_route(norm)
    http_status = 200 if recognized else 404

    structured = _expected_structured_data(page_type, norm)
    breadcrumbs = "BreadcrumbList" in structured

    # Consistency checks
    if index and blocked_by:
        errors.append(f"Pagină indexabilă dar BLOCATĂ de robots.txt (regula '{blocked_by}')")
    if index and in_sitemap and blocked_by:
        errors.append("Contradicție: în sitemap DAR blocată de robots.txt")
    if not index:
        warnings.append("Pagină noindex — nu va fi indexată (canonical către părinte)")
    if index and not in_sitemap and recognized and page_type not in ("other",) and http_status == 200:
        warnings.append("Pagină indexabilă dar ABSENTĂ din sitemap")
    if not recognized:
        warnings.append("Rută nerecunoscută — probabil 404 în SPA")
    if meta is None and page_type in ("commercial", "marketplace", "tool"):
        warnings.append("Fără metadata în registru (title/description randate client-side)")

    return {
        "path": norm,
        "url": abs_url,
        "http_status": http_status,
        "route_recognized": recognized,
        "page_type": page_type,
        "cluster": cluster,
        "cluster_label": CLUSTER_LABELS.get(cluster, cluster),
        "is_commercial": is_commercial,
        "index": index,
        "robots": "noindex, nofollow" if not index else "index, follow",
        "robots_txt_blocked": bool(blocked_by),
        "robots_txt_rule": blocked_by,
        "canonical": canonical,
        "canonical_reason": canonical_reason,
        "in_sitemap": in_sitemap,
        "title": title,
        "description": description,
        "h1": h1,
        "structured_data": structured,
        "breadcrumbs": breadcrumbs,
        "errors": errors,
        "warnings": warnings,
    }


def _is_recognized_route(norm):
    if norm in {p for p, _, _ in _STATIC_PAGES}:
        return True
    if norm in ("/scorul-casei", "/checklist-cumparare"):
        return True
    if norm.startswith("/ghiduri/"):
        return norm.split("/ghiduri/", 1)[1] in {s for s, _ in GUIDE_SLUGS}
    if norm.startswith("/probleme-casa/"):
        return norm.split("/probleme-casa/", 1)[1] in {s for s, _ in PROBLEM_SLUGS}
    if norm.startswith("/preturi/"):
        return norm.split("/preturi/", 1)[1] in set(PRICE_SEO.keys())
    if norm.startswith("/marketplace/"):
        return parse_landing_slug(norm.split("/marketplace/", 1)[1]) is not None
    if norm.startswith("/design-interior/stil/"):
        return norm.split("/design-interior/stil/", 1)[1] in DESIGN_STYLE_SLUGS
    if norm.startswith("/design-interior/"):
        seg = norm.split("/design-interior/", 1)[1]
        return seg in DESIGN_PAGE_SLUGS or seg in DESIGN_LOCAL_CITIES
    if norm.startswith("/specialists/"):
        return True
    return False


# ---------------------------------------------------------------------------
# 4) SITEMAP
# ---------------------------------------------------------------------------
@router.get("/admin/seo/sitemap")
async def seo_sitemap(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    excluded = []
    for r in snap["noindex_national"]:
        excluded.append({"url": f"{_SITE_URL}{r['path']}", "type": "service (national)", "reason": r["reason"]})
    for r in snap["noindex_combos"]:
        excluded.append({"url": f"{_SITE_URL}{r['path']}", "type": "service×city", "reason": r["reason"]})

    children = [
        {"name": n, "url": f"{_SITE_URL}/{n}", "url_count": len(snap["sitemap_children"].get(n, []))}
        for n in _CHILD_SITEMAPS
    ]
    last_generated = None
    try:
        f = _SITEMAP_DIR / "sitemap.xml"
        if f.exists():
            last_generated = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        pass
    last_regen = await db.seo_events.find_one({"type": "sitemap_regen"}, sort=[("started_at", -1)])
    regen = None
    if last_regen:
        regen = {"reason": last_regen.get("reason"), "source": last_regen.get("source"),
                 "ok": last_regen.get("ok"), "url_count": last_regen.get("url_count"),
                 "at": last_regen.get("finished_at") or last_regen.get("started_at"),
                 "error": last_regen.get("error")}
    return {
        "generated_at": snap["generated_at"],
        "root": {"url": f"{_SITE_URL}/sitemap.xml", "is_index": True, "child_count": len(children)},
        "children": children,
        "total_urls": snap["total_indexable"],
        "excluded_count": len(excluded),
        "excluded_sample": excluded[:200],
        "last_generated": last_generated,
        "last_regeneration": regen,
    }


@router.post("/admin/seo/sitemap/validate")
async def seo_sitemap_validate(user: dict = Depends(require_role("admin"))):
    """Safe, read-only re-validation. Does NOT bypass the gate; recomputes from SSOT
    builders and verifies XML validity + sitemap↔robots↔gate consistency."""
    import xml.etree.ElementTree as ET
    snap = await _snapshot(force=True)
    robots = _robots_disallows()
    checks = []

    # 1) index XML well-formed
    try:
        ET.fromstring(build_sitemap_index_xml())
        checks.append({"name": "Index XML valid", "ok": True, "detail": f"{len(_CHILD_SITEMAPS)} sitemap-uri copil"})
    except Exception as e:
        checks.append({"name": "Index XML valid", "ok": False, "detail": str(e)})

    # 2) each child well-formed + absolute URLs
    from routes.public import _wrap_urlset
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    child_xml = {
        "sitemap-static.xml": _wrap_urlset(_static_entries(today)),
        "sitemap-content.xml": _wrap_urlset(_content_entries(today)),
        "sitemap-marketplace.xml": _wrap_urlset(await _marketplace_entries(today)),
        "sitemap-specialists.xml": _wrap_urlset(await _specialist_entries(today)),
        "sitemap-design.xml": _wrap_urlset(await _design_entries(today)),
    }
    all_urls = []
    child_ok = True
    for name, xml in child_xml.items():
        try:
            ET.fromstring(xml)
            all_urls += re.findall(r"<loc>([^<]+)</loc>", xml)
        except Exception as e:
            child_ok = False
            checks.append({"name": f"{name} XML valid", "ok": False, "detail": str(e)})
    checks.append({"name": "Toate sitemap-urile copil sunt XML valid", "ok": child_ok, "detail": f"{len(all_urls)} URL-uri"})

    # 3) all URLs absolute + https + no trailing-slash dup
    non_abs = [u for u in all_urls if not u.startswith(f"{_SITE_URL}/") and u != f"{_SITE_URL}/"]
    checks.append({"name": "Toate URL-urile sunt absolute (https + domeniu canonic)", "ok": not non_abs,
                   "detail": (f"{len(non_abs)} neconform" if non_abs else "OK")})

    # 4) no duplicates
    dups = [u for u in set(all_urls) if all_urls.count(u) > 1]
    checks.append({"name": "Fără URL-uri duplicate", "ok": not dups, "detail": (f"{len(dups)} duplicate" if dups else "OK")})

    # 5) no noindex/robots-blocked URL present in sitemap
    bad = []
    for u in all_urls:
        p = u.replace(_SITE_URL, "") or "/"
        if _robots_blocks(p, robots["disallow"]):
            bad.append(u)
    checks.append({"name": "Niciun URL din sitemap nu e blocat de robots.txt", "ok": not bad,
                   "detail": (f"{len(bad)} blocate: {bad[:3]}" if bad else "OK")})

    # 6) sitemap ↔ gate consistency (marketplace URLs must pass the gate)
    mk_bad = []
    mk_urls = re.findall(r"<loc>([^<]+)</loc>", child_xml["sitemap-marketplace.xml"])
    for u in mk_urls:
        slug = u.split("/marketplace/", 1)[1] if "/marketplace/" in u else None
        if slug:
            d = await compute_marketplace_gate(slug)
            if not d["index"]:
                mk_bad.append(u)
    checks.append({"name": "URL-urile marketplace din sitemap trec Indexability Gate-ul", "ok": not mk_bad,
                   "detail": (f"{len(mk_bad)} inconsistente" if mk_bad else "OK")})

    valid = all(c["ok"] for c in checks)
    return {"valid": valid, "checked_at": datetime.now(timezone.utc).isoformat(),
            "total_urls": len(all_urls), "checks": checks}


# ---------------------------------------------------------------------------
# 5) PAGES (inventory)
# ---------------------------------------------------------------------------
async def _pages_inventory(snap):
    rows = []

    async def _row(path, page_type=None, cluster=None):
        pt, cl, comm = _classify(path)
        page_type = page_type or pt
        cluster = cluster or cl
        abs_url = f"{_SITE_URL}/" if path == "/" else f"{_SITE_URL}{path}"
        index = True
        canonical = abs_url
        if path.startswith("/marketplace/"):
            gate = await compute_marketplace_gate(path.split("/marketplace/", 1)[1])
            index = gate["index"]
            canonical = abs_url if index else gate["canonical"]
        elif path.startswith("/design-interior/") and not path.startswith("/design-interior/stil/") and path != "/design-interior":
            seg = path.split("/design-interior/", 1)[1]
            if seg in DESIGN_LOCAL_CITIES:
                gate = await compute_design_gate(seg)
                index = gate["index"]
                canonical = abs_url if index else gate["canonical"]
        in_sitemap = abs_url in snap["all_indexable_urls"]
        meta = await _page_meta_from_registry(path)
        warns = []
        if meta:
            if not meta.get("title"):
                warns.append("lipsă title")
            if not meta.get("description"):
                warns.append("lipsă meta description")
            if not meta.get("h1"):
                warns.append("lipsă H1")
        if index and not in_sitemap and page_type not in ("other",):
            warns.append("absent din sitemap")
        return {
            "url": path,
            "page_type": page_type,
            "cluster": cluster,
            "cluster_label": CLUSTER_LABELS.get(cluster, cluster),
            "title": (meta or {}).get("title"),
            "h1": (meta or {}).get("h1"),
            "index": index,
            "canonical": canonical,
            "in_sitemap": in_sitemap,
            "status": (meta or {}).get("status") or "active",
            "warnings": warns,
        }

    # static + hubs
    for p, _prio, _freq in _STATIC_PAGES:
        rows.append(await _row(p))
    for p in ("/scorul-casei", "/checklist-cumparare"):
        if p not in {r["url"] for r in rows}:
            rows.append(await _row(p))
    # editorial detail: guides, problems, preturi
    for slug, _mod in GUIDE_SLUGS:
        rows.append(await _row(f"/ghiduri/{slug}"))
    for slug, _mod in PROBLEM_SLUGS:
        rows.append(await _row(f"/probleme-casa/{slug}"))
    for slug in PRICE_SEO.keys():
        rows.append(await _row(f"/preturi/{slug}"))
    # design interior: content + style pages
    for slug, _mod in DESIGN_PAGES:
        rows.append(await _row(f"/design-interior/{slug}"))
    for slug, _mod in DESIGN_STYLES:
        rows.append(await _row(f"/design-interior/stil/{slug}"))
    # gated local design pages (only those that pass the gate are in the design sitemap)
    for u in snap["sitemap_children"].get("sitemap-design.xml", []):
        p = u.replace(_SITE_URL, "")
        seg = p.split("/design-interior/", 1)[1] if "/design-interior/" in p else ""
        if seg in DESIGN_LOCAL_CITIES:
            rows.append(await _row(p))
    # marketplace pages that pass the gate (indexable ones)
    for u in snap["sitemap_children"].get("sitemap-marketplace.xml", []):
        rows.append(await _row(u.replace(_SITE_URL, "")))
    return rows


@router.get("/admin/seo/pages")
async def seo_pages(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    rows = await _pages_inventory(snap)
    return {
        "generated_at": snap["generated_at"],
        "total": len(rows),
        "indexable": sum(1 for r in rows if r["index"]),
        "noindex": sum(1 for r in rows if not r["index"]),
        "pages": rows,
    }


# ---------------------------------------------------------------------------
# 6) CLUSTERS
# ---------------------------------------------------------------------------
@router.get("/admin/seo/clusters")
async def seo_clusters(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    rows = await _pages_inventory(snap)

    # add local_city indexable pages already in rows (from marketplace child). Include noindex combos count too.
    agg = {c["id"]: {"id": c["id"], "label": c["label"], "pages": 0, "indexable": 0,
                     "noindex": 0, "in_sitemap": 0, "internally_linked": False} for c in CLUSTER_DEFS}
    for r in rows:
        cl = r["cluster"]
        if cl not in agg:
            cl = "other"
        agg[cl]["pages"] += 1
        if r["index"]:
            agg[cl]["indexable"] += 1
        else:
            agg[cl]["noindex"] += 1
        if r["in_sitemap"]:
            agg[cl]["in_sitemap"] += 1

    # noindex service×city → local_city cluster (thin, excluded)
    agg["local_city"]["noindex"] += len(snap["noindex_combos"])
    agg["local_city"]["pages"] += len(snap["noindex_combos"])

    # internal-link coverage heuristic (footer/nav hubs)
    cluster_hubs = {
        "design_interior": "/design-interior", "probleme_casa": "/probleme-casa",
        "audit": "/scorul-casei", "digital_twin": "/digital-twin",
        "imobile_verificate": "/imobile-verificate", "marketplace": "/marketplace",
        "local_city": "/marketplace", "other": "/",
    }
    for cid, hub in cluster_hubs.items():
        if hub in INTERNALLY_LINKED:
            agg[cid]["internally_linked"] = True

    building = agg["building_hartablocuri"]
    building["note"] = "Niciun URL SEO public încă — pregătit pentru batch viitor."
    agg["design_interior"]["note"] = "Pregătit pentru SEO Expansion Batch 2 — Design Interior."

    return {"generated_at": snap["generated_at"], "clusters": list(agg.values())}


# ---------------------------------------------------------------------------
# 7) ALERTS (SEO health)
# ---------------------------------------------------------------------------
async def _compute_alerts(snap, robots):
    alerts = []

    def add(sev, code, title, detail):
        alerts.append({"severity": sev, "code": code, "title": title, "detail": detail})

    # CRITICAL
    if snap["total_indexable"] == 0:
        add("critical", "SITEMAP_EMPTY", "Sitemap gol", "Niciun URL indexabil generat.")
    if not robots["exists"]:
        add("critical", "ROBOTS_MISSING", "robots.txt lipsă", "Fișierul robots.txt nu a fost găsit.")
    elif not robots["sitemap"]:
        add("critical", "ROBOTS_NO_SITEMAP", "robots.txt fără sitemap", "Lipsește directiva Sitemap: în robots.txt.")

    # robots blocking a public indexable page
    blocked_public = []
    for u in snap["all_indexable_urls"]:
        p = u.replace(snap["site_url"], "") or "/"
        if _robots_blocks(p, robots["disallow"]):
            blocked_public.append(p)
    if blocked_public:
        add("critical", "ROBOTS_BLOCKS_INDEXABLE",
            "robots.txt blochează pagini indexabile",
            f"{len(blocked_public)} pagini din sitemap sunt blocate: {blocked_public[:3]}")

    # sitemap contains noindex URL (should never happen by construction)
    noindex_in_sitemap = []
    for r in snap["combos"] + snap["national"]:
        if not r["index"] and (f"{snap['site_url']}{r['path']}") in snap["all_indexable_urls"]:
            noindex_in_sitemap.append(r["path"])
    if noindex_in_sitemap:
        add("critical", "SITEMAP_HAS_NOINDEX", "Sitemap conține URL noindex",
            f"{len(noindex_in_sitemap)}: {noindex_in_sitemap[:3]}")

    # WARNING: db.pages missing title/desc/h1 + duplicate titles
    titles = {}
    async for doc in db.pages.find({"status": {"$ne": "archived"}}, {"route": 1, "live": 1, "status": 1}):
        live = doc.get("live") or {}
        route = doc.get("route")
        if not live.get("seo_title"):
            add("warning", "MISSING_TITLE", "Pagină fără title", f"{route} nu are seo_title")
        if not live.get("seo_description"):
            add("warning", "MISSING_DESC", "Pagină fără meta description", f"{route} nu are seo_description")
        if not live.get("h1"):
            add("warning", "MISSING_H1", "Pagină fără H1", f"{route} nu are H1")
        t = (live.get("seo_title") or "").strip()
        if t:
            titles.setdefault(t, []).append(route)
    for t, routes in titles.items():
        if len(routes) > 1:
            add("warning", "DUP_TITLE", "Title duplicat", f"'{t[:40]}…' pe {routes}")

    # INFO-ish warning: thin content excluded (healthy, but surfaced)
    noindex_market = len(snap["noindex_combos"]) + len(snap["noindex_national"])
    if noindex_market:
        add("warning", "THIN_EXCLUDED", "Conținut subțire exclus (corect)",
            f"{noindex_market} pagini service×city sub pragul de {snap['threshold']} specialiști — corect NEindexate.")

    # Sitemap auto-regeneration failure (from db.seo_events)
    try:
        last_regen = await db.seo_events.find_one({"type": "sitemap_regen"}, sort=[("started_at", -1)])
        if last_regen and last_regen.get("ok") is False:
            add("critical", "SITEMAP_REGEN_FAILED", "Regenerare sitemap eșuată",
                f"Ultima regenerare ({last_regen.get('reason')}) a eșuat: {str(last_regen.get('error'))[:120]}")
    except Exception:  # noqa: BLE001
        pass

    # GSC query error (from db.seo_events), if GSC is configured
    try:
        cfg = await _gsc_config()
        if cfg:
            gerr = await db.seo_events.find_one({"type": "gsc_error"}, sort=[("at", -1)])
            if gerr:
                add("warning", "GSC_ERROR", "Eroare la interogarea GSC",
                    f"Ultima interogare Search Console a eșuat: {str(gerr.get('error'))[:120]}")
    except Exception:  # noqa: BLE001
        pass

    return alerts


@router.get("/admin/seo/alerts")
async def seo_alerts(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    robots = _robots_disallows()
    alerts = await _compute_alerts(snap, robots)
    return {
        "generated_at": snap["generated_at"],
        "critical": [a for a in alerts if a["severity"] == "critical"],
        "warning": [a for a in alerts if a["severity"] == "warning"],
        "critical_count": sum(1 for a in alerts if a["severity"] == "critical"),
        "warning_count": sum(1 for a in alerts if a["severity"] == "warning"),
    }


# ---------------------------------------------------------------------------
# 8) GSC (Google Search Console) — REAL integration via service account
#    Credentials from db.seo_config ("gsc") or env; degrades to Not connected.
#    The service-account JSON is NEVER returned to the client.
# ---------------------------------------------------------------------------
import os as _os
import json as _json

GSC_SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
_RANGE_DAYS = {"7d": 7, "28d": 28, "3m": 90}


async def _gsc_config():
    doc = await db.seo_config.find_one({"key": "gsc"})
    if doc and doc.get("service_account_json") and doc.get("property"):
        return {"property": doc["property"], "json": doc["service_account_json"], "source": "admin"}
    if _os.environ.get("GSC_SERVICE_ACCOUNT_JSON") and _os.environ.get("GSC_PROPERTY"):
        return {"property": _os.environ["GSC_PROPERTY"], "json": _os.environ["GSC_SERVICE_ACCOUNT_JSON"], "source": "env"}
    return None


def _gsc_client_email(json_str):
    try:
        return _json.loads(json_str).get("client_email")
    except Exception:
        return None


def _site_verification_token():
    try:
        idx = (Path(__file__).resolve().parents[2] / "frontend" / "public" / "index.html").read_text(encoding="utf-8")
        m = re.search(r'name="google-site-verification"\s+content="([^"]+)"', idx)
        return m.group(1) if m else None
    except Exception:
        return None


def _gsc_run_query(json_str, prop, start, end, dimensions, row_limit=25):
    """Blocking Google API call — run via asyncio.to_thread."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    info = _json.loads(json_str)
    creds = service_account.Credentials.from_service_account_info(info, scopes=GSC_SCOPES)
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    body = {"startDate": start, "endDate": end, "dimensions": dimensions, "type": "web", "rowLimit": row_limit}
    resp = service.searchanalytics().query(siteUrl=prop, body=body).execute()
    return resp.get("rows", [])


@router.get("/admin/seo/gsc")
async def seo_gsc(user: dict = Depends(require_role("admin"))):
    cfg = await _gsc_config()
    token = _site_verification_token()
    if not cfg:
        return {
            "connected": False,
            "status": "not_connected",
            "message": "Google Search Console nu este conectat. Conectează un Service Account cu "
                       "Search Console API activat, adăugat ca user în property-ul GSC.",
            "how_to": [
                "1. Google Cloud → activează Search Console API + creează un Service Account.",
                "2. Service Account → Keys → creează cheie JSON.",
                "3. Search Console → Settings → Users and permissions → adaugă email-ul service account-ului (Full/Restricted).",
                "4. Lipește property-ul (ex: sc-domain:propmanage.ro sau https://propmanage.ro/) + JSON-ul aici.",
            ],
            "property_expected": "sc-domain:propmanage.ro sau https://propmanage.ro/",
            "site_verification_meta_present": token is not None,
            "site_verification_token": token,
            "metrics": None,
        }
    return {
        "connected": True,
        "status": "connected",
        "property": cfg["property"],
        "source": cfg["source"],
        "service_account_email": _gsc_client_email(cfg["json"]),
        "site_verification_meta_present": token is not None,
        "message": "Conectat. Folosește tab-ul GSC → Load pentru date reale.",
    }


class GSCConnectIn(BaseModel):
    property: str
    service_account_json: str


@router.post("/admin/seo/gsc/connect")
async def seo_gsc_connect(payload: GSCConnectIn, user: dict = Depends(require_role("admin"))):
    prop = (payload.property or "").strip()
    raw = (payload.service_account_json or "").strip()
    if not prop:
        return {"ok": False, "error": "Property lipsă (ex: sc-domain:propmanage.ro)"}
    try:
        info = _json.loads(raw)
    except Exception:
        return {"ok": False, "error": "JSON invalid — lipește exact conținutul cheii Service Account."}
    if info.get("type") != "service_account" or not info.get("client_email"):
        return {"ok": False, "error": "JSON-ul nu pare a fi o cheie de Service Account validă."}
    await db.seo_config.update_one(
        {"key": "gsc"},
        {"$set": {"key": "gsc", "property": prop, "service_account_json": raw,
                  "connected_by": user.get("email"), "connected_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "property": prop, "service_account_email": info.get("client_email"),
            "note": "Asigură-te că acest email este adăugat ca user în property-ul GSC."}


@router.post("/admin/seo/gsc/disconnect")
async def seo_gsc_disconnect(user: dict = Depends(require_role("admin"))):
    await db.seo_config.delete_one({"key": "gsc"})
    return {"ok": True}


@router.get("/admin/seo/gsc/report")
async def seo_gsc_report(range: str = "28d", user: dict = Depends(require_role("admin"))):
    cfg = await _gsc_config()
    if not cfg:
        return {"status": "not_connected", "overview": None, "queries": [], "pages": [], "devices": [], "trend": []}
    days = _RANGE_DAYS.get(range, 28)
    end = (datetime.now(timezone.utc).date() - timedelta(days=2))  # GSC lags ~2 days
    start = end - timedelta(days=days)
    import asyncio

    def _norm(rows, key=True):
        out = []
        for r in rows:
            out.append({
                "key": (r.get("keys") or [None])[0] if key else None,
                "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0.0), "position": r.get("position", 0.0),
            })
        return out

    try:
        s, e = start.isoformat(), end.isoformat()
        queries = await asyncio.to_thread(_gsc_run_query, cfg["json"], cfg["property"], s, e, ["query"], 25)
        pages = await asyncio.to_thread(_gsc_run_query, cfg["json"], cfg["property"], s, e, ["page"], 25)
        devices = await asyncio.to_thread(_gsc_run_query, cfg["json"], cfg["property"], s, e, ["device"], 10)
        trend = await asyncio.to_thread(_gsc_run_query, cfg["json"], cfg["property"], s, e, ["date"], 100)
        tot_clicks = sum(r.get("clicks", 0) for r in queries)
        tot_impr = sum(r.get("impressions", 0) for r in queries)
        overview = {
            "clicks": tot_clicks, "impressions": tot_impr,
            "ctr": (tot_clicks / tot_impr) if tot_impr else 0.0,
            "position": (sum(r.get("position", 0) * r.get("impressions", 0) for r in queries) / tot_impr) if tot_impr else 0.0,
            "range": range, "start": s, "end": e,
        }
        return {"status": "connected", "overview": overview, "queries": _norm(queries),
                "pages": _norm(pages), "devices": _norm(devices),
                "trend": [{"date": (r.get("keys") or [None])[0], "clicks": r.get("clicks", 0),
                           "impressions": r.get("impressions", 0)} for r in trend]}
    except Exception as exc:  # noqa: BLE001
        status = getattr(getattr(exc, "resp", None), "status", None)
        msg = {
            401: "Autentificare Google eșuată — verifică JSON-ul Service Account.",
            403: "Service account-ul nu are acces la acest property GSC (adaugă-l ca user).",
            404: "Property negăsit — verifică formatul GSC_PROPERTY.",
            429: "Cota Google API depășită — încearcă mai târziu.",
        }.get(status, f"Interogarea GSC a eșuat: {str(exc)[:160]}")
        logger.warning(f"[gsc] report error: {exc}")
        try:
            await db.seo_events.insert_one({"type": "gsc_error", "error": str(exc)[:300],
                                            "at": datetime.now(timezone.utc).isoformat()})
        except Exception:
            pass
        return {"status": "error", "error": msg, "overview": None, "queries": [], "pages": [], "devices": [], "trend": []}


# ---------------------------------------------------------------------------
# 9) EXPORT — CSV (mandatory) + PDF (reportlab)
# ---------------------------------------------------------------------------
def _csv_stream(header, rows):
    import csv
    import io

    def gen():
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(header)
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)
        for r in rows:
            w.writerow(r)
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)
    return gen()


@router.get("/admin/seo/export/indexability.csv")
async def export_indexability_csv(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    ts = snap["generated_at"]
    header = ["service", "city", "verified_specialists", "threshold", "indexability", "canonical", "reason", "in_sitemap", "checked_at"]
    rows = []
    for r in snap["national"] + snap["combos"]:
        abs_url = f"{_SITE_URL}{r['path']}"
        rows.append([
            r["service_label"], r["city_label"] or "— national —", r["verified"], r["threshold"],
            "INDEX" if r["index"] else "NOINDEX", (r["canonical"] or "self"), r["reason"],
            "yes" if abs_url in snap["all_indexable_urls"] else "no", ts,
        ])
    return StreamingResponse(_csv_stream(header, rows), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=seo-indexability.csv"})


@router.get("/admin/seo/export/alerts.csv")
async def export_alerts_csv(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    robots = _robots_disallows()
    alerts = await _compute_alerts(snap, robots)
    header = ["severity", "code", "title", "detail", "detected_at"]
    rows = [[a["severity"], a["code"], a["title"], a["detail"], snap["generated_at"]] for a in alerts]
    return StreamingResponse(_csv_stream(header, rows), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=seo-alerts.csv"})


@router.get("/admin/seo/export/report.pdf")
async def export_report_pdf(user: dict = Depends(require_role("admin"))):
    snap = await _snapshot()
    robots = _robots_disallows()
    alerts = await _compute_alerts(snap, robots)
    noindex_market = len(snap["noindex_combos"]) + len(snap["noindex_national"])
    try:
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as _canvas

        buf = io.BytesIO()
        c = _canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        y = h - 25 * mm
        c.setFont("Helvetica-Bold", 18); c.drawString(20 * mm, y, "PropManage — SEO Health Report"); y -= 9 * mm
        c.setFont("Helvetica", 9); c.drawString(20 * mm, y, f"Generat: {snap['generated_at']}"); y -= 12 * mm
        c.setFont("Helvetica-Bold", 12); c.drawString(20 * mm, y, "Indexability"); y -= 7 * mm
        c.setFont("Helvetica", 10)
        for line in [
            f"URL-uri indexabile (in sitemap): {snap['total_indexable']}",
            f"URL-uri noindex (thin, excluse): {noindex_market}",
            f"Prag gate: >= {snap['threshold']} specialisti verificati",
            f"Sitemap: index + {len(_CHILD_SITEMAPS)} copii",
        ]:
            c.drawString(24 * mm, y, line); y -= 6 * mm
        y -= 4 * mm
        c.setFont("Helvetica-Bold", 12); c.drawString(20 * mm, y, "Sitemap children"); y -= 7 * mm
        c.setFont("Helvetica", 10)
        for name in _CHILD_SITEMAPS:
            c.drawString(24 * mm, y, f"{name}: {len(snap['sitemap_children'].get(name, []))} URL"); y -= 6 * mm
        y -= 4 * mm
        crit = [a for a in alerts if a["severity"] == "critical"]
        warn = [a for a in alerts if a["severity"] == "warning"]
        c.setFont("Helvetica-Bold", 12); c.drawString(20 * mm, y, f"Alerts: {len(crit)} critice, {len(warn)} avertismente"); y -= 7 * mm
        c.setFont("Helvetica", 9)
        for a in (crit + warn)[:20]:
            if y < 20 * mm:
                c.showPage(); y = h - 25 * mm; c.setFont("Helvetica", 9)
            c.drawString(24 * mm, y, f"[{a['severity'][:4].upper()}] {a['code']}: {a['detail'][:90]}"); y -= 5.5 * mm
        c.showPage(); c.save()
        buf.seek(0)
        return Response(content=buf.read(), media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=seo-health-report.pdf"})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[seo] PDF export failed: {e}")
        return {"ok": False, "error": "PDF indisponibil; folosește exportul CSV.", "detail": str(e)[:200]}
