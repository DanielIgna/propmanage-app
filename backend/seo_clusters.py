"""HartaBlocuri — SEO Cluster Foundation (Faza 3) · READ-ONLY.

Layer SEO derivat peste `buildings` + Truth Layer. NU publică pagini, NU atinge
sitemap/robots/import/raw/schema. Agregă date REALE în clustere cu substanță și
pregătește metadata pentru viitoare pagini de cluster (fără indexare automată).

Taxonomie SEO (read-only): Localitate · Eră · Formă · Typology Profile · Project Family.
Provenance păstrat: „Date externe — neverificate de PropManage." Typology = Candidate.
NU deduce clasă energetică / risc seismic / renovare / conformitate legală.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

from db import db
from hartablocuri_read_layer import build_truth_layer

_SITE_URL = None  # rezolvat lazy din routes.public pentru a evita import circular

# Prag minim de substanță pentru eligibilitate index (calitate, anti thin-content)
MIN_BUILDINGS_INDEX = 25

# Ghiduri relevante pentru linking semantic (există în seo_guides / sitemap)
_RELATED_GUIDES = [
    ("riscuri-cumparare-apartament-bloc-vechi", "Riscuri la cumpărarea unui apartament în bloc vechi"),
    ("cartea-casei-istoric-locuinta", "Cartea Casei — istoricul locuinței"),
    ("scorul-casei-ce-masoara", "Scorul Casei — ce măsoară"),
    ("plan-mentenanta-locuinta", "Plan de mentenanță pentru locuință"),
]

# Linking semantic PropManage (forward). Ținte reale, publice.
_FORWARD_LINKS = [
    {"key": "building_discovery", "label": "Găsește-ți blocul", "href": "/#gaseste-blocul"},
    {"key": "cartea_casei", "label": "Cartea Casei", "href": "/cartea-casei"},
    {"key": "house_health", "label": "House Health (Scorul Casei A→G)", "href": "/scorul-casei"},
    {"key": "audit_specialist", "label": "Audit / Specialiști", "href": "/marketplace"},
    {"key": "digital_twin", "label": "Digital Twin", "href": "/digital-twin"},
]


def _site_url() -> str:
    global _SITE_URL
    if _SITE_URL is None:
        from routes.public import _SITE_URL as s
        _SITE_URL = s
    return _SITE_URL


def _slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


# ─────────────────── DEFINIȚII CLUSTERE PILOT (5) ───────────────────
# Fiecare pilot: locality (db+slug), dimension, value label/slug, matcher(raw, tl)->bool.
_CLUJ = {"db": "Cluj-Napoca", "slug": "cluj-napoca", "label": "Cluj-Napoca"}


def _m_c1(raw, tl):
    return any(p["code"] == "C1" for p in (tl.get("typology_profiles") or []))


def _m_c4(raw, tl):
    return any(p["code"] == "C4" for p in (tl.get("typology_profiles") or []))


def _m_era(value):
    def f(raw, tl):
        return (raw.get("era") or "").strip().lower() == value
    return f


def _m_family(fam):
    def f(raw, tl):
        return (tl.get("project_family") or {}).get("family") == fam
    return f


PILOT_CLUSTERS = [
    {
        "id": "cluj-panou-p4", "locality": _CLUJ, "dimension": "typology_profile",
        "value_label": "Panou prefabricat P+4 (fond comunist)", "value_slug": "panou-prefabricat-p4",
        "classification_level": "L2", "confidence_source": "typology",
        "matcher": _m_c1,
        "intro_lead": "blocuri din panouri prefabricate, regim P+4, tipice fondului locativ comunist",
    },
    {
        "id": "cluj-turn-inalt", "locality": _CLUJ, "dimension": "typology_profile",
        "value_label": "Turn de locuit (regim înalt)", "value_slug": "turn-inalt",
        "classification_level": "L2", "confidence_source": "typology",
        "matcher": _m_c4,
        "intro_lead": "blocuri tip turn cu regim înalt (P+10 sau mai mult)",
    },
    {
        "id": "cluj-comunist-1977-1990", "locality": _CLUJ, "dimension": "era",
        "value_label": "Eră comunistă 1977–1990", "value_slug": "comunist-1977-1990",
        "classification_level": "L0", "confidence_source": "era",
        "matcher": _m_era("comunist 1977-1990"),
        "intro_lead": "blocuri construite în perioada comunistă târzie (1977–1990)",
    },
    {
        "id": "cluj-interbelic", "locality": _CLUJ, "dimension": "era",
        "value_label": "Eră interbelică / antebelică", "value_slug": "interbelic-antebelic",
        "classification_level": "L0", "confidence_source": "era",
        "matcher": _m_era("interbelic/antebelic"),
        "intro_lead": "imobile din perioada interbelică / antebelică",
    },
    {
        "id": "cluj-proiect-cf1", "locality": _CLUJ, "dimension": "project_family",
        "value_label": "Familie de proiect cf1", "value_slug": "proiect-cf1",
        "classification_level": "L1", "confidence_source": "project_family",
        "matcher": _m_family("cf1"),
        "intro_lead": "blocuri din familia de proiect cf1 (cod de proiect normalizat soft)",
    },
]


def _slug_path(cdef: dict) -> str:
    return f"/blocuri/{cdef['locality']['slug']}/{cdef['value_slug']}"


def _confidence_summary(items: list, source: str) -> dict:
    c = Counter()
    for tl in items:
        if source == "typology":
            profs = tl.get("typology_profiles") or []
            c[profs[0]["confidence"]] += 1 if profs else 0
        elif source == "era":
            c[(tl.get("era") or {}).get("confidence")] += 1
        elif source == "project_family":
            c[(tl.get("project_family") or {}).get("confidence")] += 1
    return {k: v for k, v in c.items() if k}


async def _load_hb_buildings():
    """Încarcă blocurile HartaBlocuri (read-only) + Truth Layer derivat la citire."""
    out = []
    async for b in db.buildings.find({"context.external_sources.hartablocuri": {"$exists": True}}):
        raw = ((b.get("context") or {}).get("external_sources") or {}).get("hartablocuri", {}).get("raw") or {}
        city = b.get("city") or raw.get("city")
        out.append({"id": str(b["_id"]), "city": city, "raw": raw,
                    "tl": build_truth_layer(raw), "neighborhood": (b.get("context") or {}).get("neighborhood") or raw.get("neighborhood")})
    return out


def _aggregate(cdef: dict, buildings: list) -> dict:
    loc_db = cdef["locality"]["db"]
    loc_norm = _slugify(loc_db)
    matched = []
    for b in buildings:
        if _slugify(b["city"] or "") != loc_norm:
            continue
        if cdef["matcher"](b["raw"], b["tl"]):
            matched.append(b)
    count = len(matched)
    tls = [b["tl"] for b in matched]
    era_dist = Counter((b["raw"].get("era") or "necunoscut") for b in matched)
    form_dist = Counter((b["tl"]["form"]["value"]) for b in matched)
    floors_dist = Counter((b["tl"]["regime"]["derived_floors"]) for b in matched)
    nbh_dist = Counter((b["neighborhood"] or "necunoscut") for b in matched)
    family_dist = Counter((b["tl"]["project_family"]["family"] or "necunoscut") for b in matched)
    return {
        "building_count": count,
        "localities": [{"name": loc_db, "count": count}],
        "era_distribution": [{"value": k, "count": v} for k, v in era_dist.most_common(6)],
        "form_distribution": [{"value": k, "count": v} for k, v in form_dist.most_common(6)],
        "floors_distribution": [{"value": (f"P+{k}" if isinstance(k, int) else "nedeterminat"), "count": v}
                                for k, v in floors_dist.most_common(6)],
        "neighborhood_distribution": [{"value": k, "count": v} for k, v in nbh_dist.most_common(8)],
        "project_family_distribution": [{"value": k, "count": v} for k, v in family_dist.most_common(6)],
        "confidence": _confidence_summary(tls, cdef["confidence_source"]),
        "sample_building_ids": [b["id"] for b in matched[:6]],
    }


def _build_content(cdef: dict, agg: dict) -> dict:
    loc = cdef["locality"]["label"]
    n = agg["building_count"]
    vlabel = cdef["value_label"]
    lead = cdef["intro_lead"]
    is_candidate = cdef["classification_level"] == "L2"
    cand_tag = " (Candidate Typology · derivat din HartaBlocuri)" if is_candidate else ""
    title = f"{vlabel} în {loc} — {n} blocuri în baza de referință"
    meta_title = f"{vlabel} · {loc} | PropManage"
    meta_description = (
        f"{n} blocuri din {loc} identificate ca {lead}, pe baza datelor externe HartaBlocuri "
        f"(neverificate de PropManage). Vezi contextul clădirii și pornește Cartea Casei."
    )[:300]
    h1 = f"{vlabel} în {loc}"
    intro = (
        f"În baza de referință PropManage pentru {loc} sunt {n} blocuri identificate ca {lead}{cand_tag}. "
        f"Datele provin din sursa externă HartaBlocuri și sunt neverificate de PropManage — le confirmi tu "
        f"la conectarea apartamentului. Poți prelua contextul clădirii, porni Cartea Casei și evalua "
        f"starea locuinței cu Scorul Casei (House Health A→G)."
    )
    return {"title": title, "meta_title": meta_title, "meta_description": meta_description,
            "h1": h1, "intro": intro}


def _quality_gate(agg: dict) -> dict:
    n = agg["building_count"]
    passes = n >= MIN_BUILDINGS_INDEX and len(agg["localities"]) >= 1
    reason = (f"{n} blocuri (≥{MIN_BUILDINGS_INDEX})" if passes
              else f"doar {n} blocuri (<{MIN_BUILDINGS_INDEX}) — risc thin content")
    return {"passes": passes, "min_buildings": MIN_BUILDINGS_INDEX, "reason": reason}


def build_cluster(cdef: dict, buildings: list) -> dict:
    agg = _aggregate(cdef, buildings)
    content = _build_content(cdef, agg)
    gate = _quality_gate(agg)
    path = _slug_path(cdef)
    canonical = f"{_site_url()}{path}"
    # PILOT: pregătit, NEpublicat. Nu intră în sitemap, indexabilitate reținută până la aprobare.
    index_state = "prepared_noindex"
    index_reason = (f"pilot pregătit — {gate['reason']}; neaprobat pentru publicare"
                    if gate["passes"]
                    else f"pilot pregătit — {gate['reason']}; neeligibil index")
    return {
        "id": cdef["id"],
        "cluster": "building_hartablocuri",
        "dimension": cdef["dimension"],
        "value_label": cdef["value_label"],
        "locality": cdef["locality"]["label"],
        "slug": path,
        "url": path,
        "canonical": canonical,
        "classification_level": cdef["classification_level"],
        "provenance": {
            "source": "hartablocuri",
            "verification_status": "neverificat",
            "verification_note": "Date externe — neverificate de PropManage",
            "typology_note": ("Candidate Typology · derivat din HartaBlocuri"
                              if cdef["classification_level"] == "L2" else None),
        },
        "content": content,
        "aggregates": agg,
        "data_limits": [
            "Date externe HartaBlocuri — neverificate de PropManage.",
            "Typology Profile este clasificare candidate (L2), nu tipologie oficială sau certificare.",
            "Nu se deduc clasă energetică, risc seismic, siguranță structurală, necesitate de renovare "
            "sau conformitate legală din aceste date.",
        ],
        "internal_links": {
            "forward": _FORWARD_LINKS,
            "inverse": [
                {"from": "/probleme-casa", "reason": "hub editorial → cluster relevant"},
                {"from": "/ghiduri", "reason": "ghiduri relevante → cluster"},
            ],
            "related_guides": [{"slug": s, "title": t, "href": f"/ghiduri/{s}"} for s, t in _RELATED_GUIDES],
            "building_context_samples": [
                {"building_id": bid, "href": f"/register?binvite={bid}"}
                for bid in agg["sample_building_ids"]
            ],
        },
        "quality_gate": gate,
        "index": False,               # PILOT — niciodată index automat
        "indexability": index_state,
        "index_reason": index_reason,
        "in_sitemap": False,          # NU se publică în sitemap
        "published": False,
        "status": "pilot_prepared",
    }


async def list_pilot_clusters() -> dict:
    buildings = await _load_hb_buildings()
    clusters = [build_cluster(c, buildings) for c in PILOT_CLUSTERS]
    return {
        "generated_at": None,
        "total_clusters": len(clusters),
        "published": 0,
        "prepared": len(clusters),
        "min_buildings_index": MIN_BUILDINGS_INDEX,
        "note": ("Clustere pilot pregătite (read-only). Neindexate, absente din sitemap. "
                 "Publicarea necesită aprobare explicită."),
        "clusters": clusters,
    }


async def get_pilot_cluster(cluster_id: str) -> dict | None:
    buildings = await _load_hb_buildings()
    cdef = next((c for c in PILOT_CLUSTERS if c["id"] == cluster_id), None)
    if not cdef:
        return None
    return build_cluster(cdef, buildings)


def pilot_slugs() -> list[str]:
    return [_slug_path(c) for c in PILOT_CLUSTERS]
