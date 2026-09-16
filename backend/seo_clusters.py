"""HartaBlocuri — National SEO Cluster ENGINE (county-agnostic) · READ-ONLY.

Motor de descoperire clustere peste `buildings` + Truth Layer. County-agnostic:
Romania → Județ → Localitate → Cartier → Eră → Tipologie → Project Family → Building.
NU hardcoda județul. Datasetul Cluj populează prima instanță; alt județ = doar date noi.

State machine indexabilitate (data-driven): BLOCKED / CANDIDATE / PREPARED / INDEX / NOINDEX.
Doar clusterele INDEX intră în sitemap. Fără pagini goale/subțiri/doorway. Fără statistici inventate.
NU atinge raw/schema/import/Truth Layer/Marketplace/House Health/Digital Twin/OAuth.
"""
from __future__ import annotations

import re
import time
import unicodedata
from collections import Counter

from db import db
from hartablocuri_read_layer import build_truth_layer

_SITE_URL = None

# Praguri quality gate (substanță reală, anti thin-content)
MIN_INDEX = 30      # substanță solidă → auto-publish INDEX
MIN_PREPARED = 10   # substanță parțială → PREPARED (noindex, publicabil ulterior)

BASE = "/blocuri"

_PLACEHOLDER = {"", "none", "necunoscut", "necunoscuta", "nedeterminat", "n/a", "na",
                "ansambluri noi", "imobile interbelice/antebelice", "de adaugat"}

ERA_LABEL = {
    "comunist 1950-1969": "Comunist timpuriu (1950–1969)",
    "comunist 1968-1979": "Comunist (1968–1979)",
    "comunist 1977-1990": "Comunist târziu (1977–1990)",
    "post-1990": "Post-1990",
    "interbelic/antebelic": "Interbelic / antebelic",
}
FORM_LABEL = {"bara": "Bloc bară", "turn": "Bloc turn", "drept": "Bloc drept",
              "cruce": "Bloc cruce", "mixt": "Bloc mixt"}
TYP_LABEL = {"C1": "Panou prefabricat P+4 (fond comunist)", "C4": "Turn de locuit (regim înalt)"}
TYP_SLUG = {"C1": "panou-prefabricat-p4", "C4": "turn-inalt"}
TYP_LEVEL = {"C1": "L2", "C4": "L2"}

_RELATED_GUIDES = [
    ("riscuri-cumparare-apartament-bloc-vechi", "Riscuri la cumpărarea unui apartament în bloc vechi"),
    ("cartea-casei-istoric-locuinta", "Cartea Casei — istoricul locuinței"),
    ("scorul-casei-ce-masoara", "Scorul Casei — ce măsoară"),
    ("plan-mentenanta-locuinta", "Plan de mentenanță pentru locuință"),
]
_FORWARD_LINKS = [
    {"key": "building_discovery", "label": "Găsește-ți blocul", "href": "/#gaseste-blocul"},
    {"key": "cartea_casei", "label": "Cartea Casei", "href": "/cartea-casei"},
    {"key": "house_health", "label": "House Health (Scorul Casei A→G)", "href": "/scorul-casei"},
    {"key": "audit_specialist", "label": "Audit / Specialiști", "href": "/marketplace"},
    {"key": "digital_twin", "label": "Digital Twin", "href": "/digital-twin"},
]

# Puncte de monetizare (conceptual, folosind infrastructura existentă; fără prețuri noi)
MONETIZATION = {
    "free": {"label": "Informații publice / contextuale", "href": None},
    "lead": {"label": "Creare cont · Adaugă locuința · Cartea Casei", "href": "/cartea-casei"},
    "paid": {"label": "House Health · Audit · Digital Twin · documentație", "href": "/scorul-casei"},
    "specialist": {"label": "Lead specialist · solicitare · serviciu", "href": "/marketplace"},
    "property": {"label": "Servicii pentru asociații · lucrări · mentenanță", "href": "/marketplace"},
}


def _site_url() -> str:
    global _SITE_URL
    if _SITE_URL is None:
        from routes.public import _SITE_URL as s
        _SITE_URL = s
    return _SITE_URL


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def _blocked(v) -> bool:
    return v is None or str(v).strip().lower() in _PLACEHOLDER


# ─────────────────────── EXTRACT FACTS (per clădire) ───────────────────────
def _facts(b: dict) -> dict:
    ctx = b.get("context") or {}
    raw = (ctx.get("external_sources") or {}).get("hartablocuri", {}).get("raw") or {}
    tl = build_truth_layer(raw) or {}
    county = raw.get("judet") or "Cluj"
    locality = b.get("city") or raw.get("city")
    nbh = ctx.get("neighborhood") or raw.get("neighborhood")
    era = (raw.get("era") or "").strip().lower() or None
    form = (tl.get("form") or {}).get("value")
    floors = (tl.get("regime") or {}).get("derived_floors")
    family = (tl.get("project_family") or {}).get("family")
    profiles = [p["code"] for p in (tl.get("typology_profiles") or [])]
    lat = ctx.get("lat") if isinstance(ctx.get("lat"), (int, float)) else raw.get("lat")
    lng = ctx.get("lng") if isinstance(ctx.get("lng"), (int, float)) else raw.get("lng")
    return {
        "id": str(b["_id"]), "name": b.get("name"), "address": b.get("address"),
        "county": county, "locality": locality, "neighborhood": nbh,
        "era": era, "form": form, "floors": floors, "family": family, "profiles": profiles,
        "lat": lat, "lng": lng, "tl": tl,
    }


# ─────────────────────── REGISTRY / DISCOVERY ───────────────────────
class _Cand:
    __slots__ = ("slug", "dim", "level", "county", "locality", "value_label", "value_key",
                 "count", "ids", "era", "floors", "nbh", "family", "form", "conf")

    def __init__(self, slug, dim, level, county, locality, value_label, value_key):
        self.slug = slug; self.dim = dim; self.level = level
        self.county = county; self.locality = locality
        self.value_label = value_label; self.value_key = value_key
        self.count = 0; self.ids = []
        self.era = Counter(); self.floors = Counter(); self.nbh = Counter()
        self.family = Counter(); self.form = Counter(); self.conf = Counter()

    def add(self, f, conf_source):
        self.count += 1
        if len(self.ids) < 8:
            self.ids.append({"id": f["id"], "name": f["name"], "address": f["address"],
                             "lat": f["lat"], "lng": f["lng"]})
        self.era[f["era"] or "necunoscut"] += 1
        self.floors[f["floors"]] += 1
        if f["neighborhood"]:
            self.nbh[f["neighborhood"]] += 1
        if f["family"]:
            self.family[f["family"]] += 1
        if f["form"]:
            self.form[f["form"]] += 1
        # confidence pentru dimensiunea definitorie
        if conf_source == "era":
            self.conf[(f["tl"].get("era") or {}).get("confidence")] += 1
        elif conf_source == "typology":
            profs = f["tl"].get("typology_profiles") or []
            if profs:
                self.conf[profs[0]["confidence"]] += 1
        elif conf_source == "project_family":
            self.conf[(f["tl"].get("project_family") or {}).get("confidence")] += 1
        elif conf_source == "form":
            self.conf[(f["tl"].get("form") or {}).get("confidence")] += 1


def _era_slug(era):
    return "era-" + _slug(era)


def discover(facts: list) -> dict:
    reg: dict[str, _Cand] = {}

    def get(slug, dim, level, county, locality, label, key):
        c = reg.get(slug)
        if c is None:
            c = _Cand(slug, dim, level, county, locality, label, key)
            reg[slug] = c
        return c

    for f in facts:
        county, loc = f["county"], f["locality"]
        if _blocked(county):
            continue
        cs = _slug(county)
        # 1) județ
        get(f"{BASE}/{cs}", "county", "L0", county, None, f"Județul {county}", county).add(f, "era")
        if _blocked(loc):
            continue
        ls = _slug(loc)
        lp = f"{BASE}/{cs}/{ls}"
        # 2) localitate
        get(lp, "locality", "L0", county, loc, loc, loc).add(f, "era")
        # 3) localitate × eră
        if not _blocked(f["era"]):
            get(f"{lp}/{_era_slug(f['era'])}", "locality_era", "L0", county, loc,
                f"{ERA_LABEL.get(f['era'], f['era'])} · {loc}", f["era"]).add(f, "era")
        # 4) localitate × cartier
        if not _blocked(f["neighborhood"]):
            get(f"{lp}/cartier-{_slug(f['neighborhood'])}", "locality_neighborhood", "L0",
                county, loc, f"{f['neighborhood']} · {loc}", f["neighborhood"]).add(f, "era")
        # 5) localitate × formă
        if f["form"] and f["form"] != "unknown":
            get(f"{lp}/{_slug(FORM_LABEL.get(f['form'], f['form']))}", "locality_form", "L1",
                county, loc, f"{FORM_LABEL.get(f['form'], f['form'])} · {loc}", f["form"]).add(f, "form")
        # 6) localitate × project family
        if f["family"]:
            get(f"{lp}/proiect-{_slug(f['family'])}", "locality_project_family", "L1",
                county, loc, f"Familie proiect {f['family']} · {loc}", f["family"]).add(f, "project_family")
        # 7) localitate × tipologie + 8) eră × tipologie (county-wide)
        for code in f["profiles"]:
            get(f"{lp}/tip-{TYP_SLUG.get(code, _slug(code))}", "locality_typology", TYP_LEVEL.get(code, "L2"),
                county, loc, f"{TYP_LABEL.get(code, code)} · {loc}", code).add(f, "typology")
            if not _blocked(f["era"]):
                get(f"{BASE}/{cs}/{_era_slug(f['era'])}/tip-{TYP_SLUG.get(code, _slug(code))}",
                    "era_typology", TYP_LEVEL.get(code, "L2"), county, None,
                    f"{TYP_LABEL.get(code, code)} · {ERA_LABEL.get(f['era'], f['era'])}", code).add(f, "typology")
    return reg


# ─────────────────────── QUALITY / STATE ───────────────────────
def _quality_score(c: _Cand) -> int:
    vol = min(1.0, c.count / MIN_INDEX)
    # completitudine: câte distribuții au >1 valoare (diferențiere)
    rich = sum(1 for d in (c.era, c.floors, c.nbh, c.family, c.form) if len([k for k in d if k not in (None, "necunoscut")]) >= 1)
    completeness = min(1.0, rich / 5)
    return int(round(vol * 65 + completeness * 35))


def _state(c: _Cand, score: int) -> tuple[str, bool, bool]:
    if _blocked(c.value_key):
        return "BLOCKED", False, False
    if c.count == 0:
        return "BLOCKED", False, False
    if c.count >= MIN_INDEX and score >= 55:
        return "INDEX", True, True
    if c.count >= MIN_PREPARED:
        return "PREPARED", False, False
    return "CANDIDATE", False, False


# ─────────────────────── MATERIALIZE ───────────────────────
def _dist(counter: Counter, fmt=None, top=6):
    return [{"value": (fmt(k) if fmt else (k if k is not None else "nedeterminat")), "count": v}
            for k, v in counter.most_common(top)]


def _content(c: _Cand, state: str) -> dict:
    n = c.count
    label = c.value_label
    loc_ctx = c.locality or c.county
    cand = " (Candidate Typology · derivat din HartaBlocuri)" if c.level == "L2" else ""
    title = f"{label} — {n} blocuri în baza de referință"
    h1 = label
    meta_title = f"{label} | PropManage HartaBlocuri"
    meta_description = (
        f"{n} blocuri în {loc_ctx} din categoria „{label}” pe baza datelor externe HartaBlocuri "
        f"(neverificate de PropManage). Vezi contextul clădirii și pornește Cartea Casei."
    )[:300]
    intro = (
        f"În baza de referință PropManage sunt {n} blocuri asociate cu „{label}”{cand}. "
        f"Datele provin din sursa externă HartaBlocuri și sunt neverificate de PropManage — le confirmi "
        f"la conectarea apartamentului. Poți prelua contextul clădirii, porni Cartea Casei și evalua "
        f"starea locuinței cu Scorul Casei (House Health A→G)."
    )
    return {
        "title": title, "h1": h1, "meta_title": meta_title, "meta_description": meta_description,
        "intro": intro,
        "what_it_means": "Datele descriu caracteristici observate ale fondului construit (eră, formă, regim, familie de proiect).",
        "what_it_does_not_mean": ("NU reprezintă clasă/performanță energetică, risc seismic, siguranță "
                                  "structurală, necesitate de renovare, eligibilitate de finanțare sau conformitate legală."),
    }


def _materialize(c: _Cand) -> dict:
    score = _quality_score(c)
    state, index, in_sitemap = _state(c, score)
    path = c.slug
    aggregates = {
        "building_count": c.count,
        "era_distribution": _dist(c.era),
        "floors_distribution": _dist(c.floors, fmt=lambda k: f"P+{k}" if isinstance(k, int) else "nedeterminat"),
        "neighborhood_distribution": _dist(c.nbh, top=8),
        "project_family_distribution": _dist(c.family),
        "form_distribution": _dist(c.form),
        "confidence": {k: v for k, v in c.conf.items() if k},
        "sample_buildings": c.ids[:6],
    }
    out = {
        "id": _slug(path.replace(BASE + "/", "")),
        "cluster": "building_hartablocuri",
        "dimension": c.dim,
        "level": c.level,
        "county": c.county,
        "locality": c.locality,
        "value_label": c.value_label,
        "slug": path,
        "url": path,
        "canonical": f"{_site_url()}{path}",
        "state": state,
        "index": index,
        "in_sitemap": in_sitemap,
        "quality_score": score,
        "quality_gate": {"passes": state in ("INDEX", "PREPARED"),
                         "min_index": MIN_INDEX, "min_prepared": MIN_PREPARED},
        "index_reason": _reason(state, c.count, score),
        "building_count": c.count,
        "aggregates": aggregates,
        "provenance": {
            "source": "hartablocuri", "verification_status": "neverificat",
            "verification_note": "Date externe — neverificate de PropManage",
            "typology_note": "Candidate Typology · derivat din HartaBlocuri" if c.level == "L2" else None,
        },
        "data_limits": [
            "Date externe HartaBlocuri — neverificate de PropManage.",
            "Typology Profile este clasificare candidate (L2), nu tipologie oficială sau certificare.",
            "Nu se deduc clasă/performanță energetică, risc seismic, siguranță structurală, "
            "necesitate de renovare, eligibilitate de finanțare sau conformitate legală.",
        ],
        "internal_links": {
            "forward": _FORWARD_LINKS,
            "related_guides": [{"slug": s, "title": t, "href": f"/ghiduri/{s}"} for s, t in _RELATED_GUIDES],
            "building_context_samples": [
                {"building_id": s["id"], "name": s["name"], "href": f"{BASE}/cladire/{s['id']}"} for s in c.ids[:6]
            ],
            "parents": _parents(path),
        },
        "monetization": MONETIZATION,
    }
    if state in ("INDEX", "PREPARED"):
        out["content"] = _content(c, state)
    return out


def _reason(state, count, score):
    if state == "INDEX":
        return f"substanță solidă — {count} blocuri (≥{MIN_INDEX}), scor {score} → publicat"
    if state == "PREPARED":
        return f"substanță parțială — {count} blocuri ({MIN_PREPARED}–{MIN_INDEX - 1}) → pregătit, noindex"
    if state == "BLOCKED":
        return "valoare placeholder/necunoscută → exclus"
    return f"substanță insuficientă — {count} blocuri (<{MIN_PREPARED}) → candidate, noindex"


def _parents(path: str) -> list:
    segs = path.strip("/").split("/")  # blocuri, county, locality, leaf...
    parents = []
    acc = ""
    for s in segs[:-1]:
        acc += "/" + s
        if acc != BASE:
            parents.append(acc)
    return parents


# ─────────────────────── CACHE + PUBLIC API ───────────────────────
_CACHE = {"ts": 0.0, "clusters": None}
_TTL = 120.0


async def _load_facts() -> list:
    return [_facts(b) async for b in db.buildings.find({"context.external_sources.hartablocuri": {"$exists": True}})]


async def all_clusters(force: bool = False) -> list:
    now = time.time()
    if not force and _CACHE["clusters"] is not None and (now - _CACHE["ts"]) < _TTL:
        return _CACHE["clusters"]
    facts = await _load_facts()
    reg = discover(facts)
    clusters = [_materialize(c) for c in reg.values()]
    clusters.sort(key=lambda x: (-x["building_count"], x["slug"]))
    _CACHE["clusters"] = clusters
    _CACHE["ts"] = now
    return clusters


async def summary() -> dict:
    clusters = await all_clusters()
    by_state = Counter(c["state"] for c in clusters)
    return {
        "total": len(clusters),
        "by_state": dict(by_state),
        "index": by_state["INDEX"], "prepared": by_state["PREPARED"],
        "candidate": by_state["CANDIDATE"], "noindex": by_state["NOINDEX"],
        "blocked": by_state["BLOCKED"],
        "in_sitemap": sum(1 for c in clusters if c["in_sitemap"]),
        "min_index": MIN_INDEX, "min_prepared": MIN_PREPARED,
        "counties": sorted({c["county"] for c in clusters if c["county"]}),
    }


async def index_cluster_urls() -> list[str]:
    return [c["slug"] for c in await all_clusters() if c["in_sitemap"]]


async def get_cluster_by_slug(slug: str) -> dict | None:
    slug = "/" + slug.strip("/")
    for c in await all_clusters():
        if c["slug"] == slug:
            return c
    return None


async def list_clusters(state: str = None, county: str = None, dimension: str = None,
                        limit: int = 500) -> list:
    out = []
    for c in await all_clusters():
        if state and c["state"] != state:
            continue
        if county and _slug(c["county"] or "") != _slug(county):
            continue
        if dimension and c["dimension"] != dimension:
            continue
        out.append(c)
        if len(out) >= limit:
            break
    return out
