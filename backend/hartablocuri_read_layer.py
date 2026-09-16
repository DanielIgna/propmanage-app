"""HartaBlocuri — Truth Layer READ MODEL v1.0 (Faza 1).

Funcție PURĂ de derivare, calculată LA CITIRE. NU scrie în DB, NU modifică raw
data, schema, importul sau proveniența. Nu produce inferență profesională (L3).

Niveluri:
  L0 = SOURCE FACT      (valoare brută, păstrată exact)
  L1 = DERIVED FACT     (derivare deterministă din raw)
  (L2 CANDIDATE / L3 PROFESSIONAL — NEintroduse în această fază)

Confidence: high | medium | low | unknown | not_available
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

# Markere care apar explicit ca „valoare necunoscută" în sursă (≠ câmp lipsă)
_UNKNOWN_MARKERS = {"necunoscut", "necunoscuta", "nedeterminat", "nedeterminata",
                    "de adaugat", "n/a", "na", "?", "-", "nespecificat"}

# Keyword-uri de formă (după eliminarea diacriticelor)
_FORM_KEYWORDS = {
    "bara": "bara",
    "turn": "turn",
    "cruce": "cruce",
    "drept": "drept",
}


def _strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm(v) -> str:
    if v is None:
        return ""
    return _strip_diacritics(str(v)).strip().lower()


# ─────────────────────────── ERA (L0) ───────────────────────────

def _derive_era(raw: dict) -> dict:
    val = raw.get("era")
    if val is None or str(val).strip() == "":
        return {"value": None, "source_field": "era", "level": "L0", "confidence": "not_available"}
    if _norm(val) in _UNKNOWN_MARKERS:
        return {"value": None, "source_field": "era", "level": "L0", "confidence": "unknown"}
    # SOURCE FACT — păstrat exact, fără transformare
    return {"value": str(val).strip(), "source_field": "era", "level": "L0", "confidence": "high"}


# ─────────────────────────── FORM (L1) ───────────────────────────

def _derive_form(raw: dict) -> dict:
    proiect = raw.get("proiect")
    base = {"source_field": "proiect", "level": "L1", "raw_project": (str(proiect).strip() if proiect not in (None, "") else None)}
    if proiect is None or str(proiect).strip() == "":
        return {**base, "value": "unknown", "confidence": "not_available"}
    n = _norm(proiect)
    if n in _UNKNOWN_MARKERS:
        return {**base, "value": "unknown", "confidence": "unknown"}
    found = [form for kw, form in _FORM_KEYWORDS.items() if re.search(rf"\b{kw}\b", n)]
    found = sorted(set(found))
    if len(found) == 1:
        return {**base, "value": found[0], "confidence": "high"}
    if len(found) > 1:
        # combinație ambiguă (ex: „cruce/drept") — nu o separăm automat
        return {**base, "value": "mixt", "confidence": "low"}
    # coduri fără formă clară (cf1, cf1d, cf3sd 18x9m, bloc unicat) → necunoscut
    return {**base, "value": "unknown", "confidence": "unknown"}


# ────────────────────────── REGIME (L1) ──────────────────────────

def _derive_regime(raw: dict) -> dict:
    val = raw.get("regim_inaltime")
    base = {"raw": (str(val).strip() if val not in (None, "") else None),
            "source_field": "regim_inaltime", "level": "L1"}
    if val is None or str(val).strip() == "":
        return {**base, "derived_floors": None, "confidence": "not_available"}
    n = _norm(val)
    # „parter + N etaje" → N (determinist)
    m = re.match(r"^\s*parter\s*\+\s*(\d+)", n)
    if m:
        return {**base, "derived_floors": int(m.group(1)), "confidence": "high"}
    # „P+N" curat, la început (fără prefix tehnic S/D/M) → N
    m = re.match(r"^\s*p\s*\+\s*(\d+)", n)
    if m:
        return {**base, "derived_floors": int(m.group(1)), "confidence": "high"}
    # prefixe tehnice înainte de P (S+P+4, D+P+4, 2S+P+4, M+P+…) → ambiguu
    if re.search(r"\+\s*p\b", n) or re.search(r"^\s*[a-z0-9]*[sdm]\s*\+\s*p", n):
        return {**base, "derived_floors": None, "confidence": "unknown"}
    return {**base, "derived_floors": None, "confidence": "unknown"}


# ─────────────────────────── CARTIER (L0) ───────────────────────────

def _derive_neighborhood(raw: dict) -> dict:
    # DOAR source fact — fără inferență din UAT/localitate
    val = raw.get("neighborhood")
    if val is None or str(val).strip() == "":
        return {"value": None, "source_field": "neighborhood", "level": "L0", "confidence": "not_available"}
    return {"value": str(val).strip(), "source_field": "neighborhood", "level": "L0", "confidence": "high"}


def build_truth_layer(hb_raw: Optional[dict]) -> Optional[dict]:
    """Construiește Truth Layer READ MODEL din raw-ul HartaBlocuri.

    Returnează None dacă nu există date HartaBlocuri (nimic de derivat).
    Funcție pură: nu are efecte secundare, nu atinge DB.
    """
    if not hb_raw:
        return None
    era = _derive_era(hb_raw)
    form = _derive_form(hb_raw)
    regime = _derive_regime(hb_raw)
    neighborhood = _derive_neighborhood(hb_raw)
    project_family = derive_project_family(hb_raw)
    tl = {
        "era": era,
        "form": form,
        "regime": regime,
        "neighborhood": neighborhood,
        "project_family": project_family,
        "provenance": {
            "source": "hartablocuri",
            "verification_status": "neverificat",
            "verification_note": "Date externe — neverificate de PropManage",
        },
    }
    tl["typology_profiles"] = derive_typology_profiles(hb_raw, tl)
    return tl


# ───────────────────── PROJECT FAMILY (L1) ─────────────────────
# Normalizare soft a codurilor de proiect „cf" (cf1, cf1d, cf1sd, cf2, cf3sd...).
# Familia de bază = cf + număr; variantele (sufixe literale) se păstrează.
# RAW rămâne intact; ambiguitatea → unknown (fără estimare).

def derive_project_family(hb_raw: dict) -> dict:
    proiect = hb_raw.get("proiect")
    base = {"source_field": "proiect", "level": "L1",
            "raw_project": (str(proiect).strip() if proiect not in (None, "") else None)}
    if proiect is None or str(proiect).strip() == "":
        return {**base, "family": None, "variants": [], "confidence": "not_available"}
    n = _norm(proiect)
    if n in _UNKNOWN_MARKERS:
        return {**base, "family": None, "variants": [], "confidence": "unknown"}
    tokens = re.findall(r"cf\d+[a-z]*", n)
    if not tokens:
        # proiect prezent dar fără cod „cf" clar (ex. „cub", „bara cu coridor exterior")
        return {**base, "family": None, "variants": [], "confidence": "unknown"}
    uncertain = bool(re.search(r"cf\d+[a-z]*\s*\?", n))  # ex. „cf1?"
    families = sorted({re.match(r"cf\d+", t).group(0) for t in tokens})
    variants = sorted(set(tokens))
    if len(families) == 1:
        return {**base, "family": families[0], "variants": variants,
                "confidence": ("medium" if uncertain else "high")}
    # coduri din familii diferite → ambiguu, nu estimăm
    return {**base, "family": None, "variants": variants, "confidence": "low"}


# ─────────────────── TYPOLOGY PROFILES (L2 · CANDIDATE) ───────────────────
# Profiluri candidate derivate din faptele Truth Layer deja validate.
# NU sunt tipologii oficiale, certificări sau diagnostice tehnice.

_DISCLAIMER_TL = ("Candidate Typology — derivat din HartaBlocuri, neverificat de PropManage. "
                  "Nu este o tipologie oficială, certificare sau diagnostic tehnic.")

_PROFILE_C1 = {
    "code": "C1",
    "label": "Panou prefabricat P+4 (fond comunist)",
    "description": "Bloc din panouri prefabricate, regim P+4, tipic fondului locativ comunist.",
}
_PROFILE_C4 = {
    "code": "C4",
    "label": "Turn de locuit (regim înalt)",
    "description": "Bloc tip turn, regim înalt (P+10 sau mai mult).",
}


def derive_typology_profiles(hb_raw: dict, truth_layer: Optional[dict] = None) -> list:
    """Returnează profilurile candidate (C1/C4) pe care le satisface clădirea.
    Folosește EXCLUSIV faptele validate (era L0, formă L1, regim L1, structură raw).
    """
    tl = truth_layer or {}
    era = _norm(hb_raw.get("era"))
    struct = _norm(hb_raw.get("structura"))
    form = (tl.get("form") or {}).get("value")
    floors = (tl.get("regime") or {}).get("derived_floors")
    comunist = "comunist" in era
    is_panel = ("panou" in struct) or ("prefabric" in struct)
    profiles = []
    # C1 — panou prefabricat, era comunistă, regim P+4 (determinist)
    if comunist and is_panel and floors == 4:
        profiles.append({
            **_PROFILE_C1, "matched": True, "level": "L2", "classification": "candidate",
            "confidence": ("medium" if "posibil" in struct else "high"),
            "criteria_met": ["era comunistă", "structură panouri prefabricate", "regim P+4 (determinist)"],
            "disclaimer": _DISCLAIMER_TL,
        })
    # C4 — turn de locuit, regim înalt (≥ P+10, determinist)
    if form == "turn" and floors is not None and floors >= 10:
        profiles.append({
            **_PROFILE_C4, "matched": True, "level": "L2", "classification": "candidate",
            "confidence": "high",
            "criteria_met": ["formă turn (din proiect)", "regim ≥ P+10 (determinist)"]
                            + (["era comunistă"] if comunist else []),
            "disclaimer": _DISCLAIMER_TL,
        })
    return profiles
