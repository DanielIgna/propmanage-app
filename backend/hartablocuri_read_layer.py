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
    return {
        "era": _derive_era(hb_raw),
        "form": _derive_form(hb_raw),
        "regime": _derive_regime(hb_raw),
        "neighborhood": _derive_neighborhood(hb_raw),
        "provenance": {
            "source": "hartablocuri",
            "verification_status": "neverificat",
            "verification_note": "Date externe — neverificate de PropManage",
        },
    }
