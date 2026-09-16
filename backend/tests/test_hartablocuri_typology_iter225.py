"""Faza 2 — Project Families + Typology Profiles C1/C4 (derivare pură, read-only)."""
from hartablocuri_read_layer import (
    build_truth_layer, derive_project_family, derive_typology_profiles,
)


def _pf(proiect):
    return derive_project_family({"proiect": proiect})


# ─────────── PROJECT FAMILY ───────────
def test_pf_cf1_high():
    r = _pf("bloc unicat cf1")
    assert r["family"] == "cf1" and r["confidence"] == "high" and r["raw_project"] == "bloc unicat cf1"


def test_pf_cf1d_variant_high():
    r = _pf("1978-1986 bloc cruce/drept cf1d (pc33 pc33)")
    assert r["family"] == "cf1" and "cf1d" in r["variants"] and r["confidence"] == "high"


def test_pf_cf1sd_high():
    r = _pf("1960-1964 bloc bară cărămidă cf1sd scară față 19x12m")
    assert r["family"] == "cf1" and "cf1sd" in r["variants"] and r["confidence"] == "high"


def test_pf_cf3sd_high():
    r = _pf("cf3sd 18x9m")
    assert r["family"] == "cf3" and "cf3sd" in r["variants"]


def test_pf_uncertain_marker_medium():
    r = _pf("1978-1986 bloc cruce/drept cf1? cu balcoane (pa34 pa34)")
    assert r["family"] == "cf1" and r["confidence"] == "medium"


def test_pf_no_code_unknown():
    r = _pf("bloc unicat decalat 233")
    assert r["family"] is None and r["confidence"] == "unknown"


def test_pf_de_adaugat_unknown():
    r = _pf("de adăugat")
    assert r["family"] is None and r["confidence"] == "unknown"


def test_pf_missing_not_available():
    r = _pf(None)
    assert r["family"] is None and r["confidence"] == "not_available"


def test_pf_multiple_families_ambiguous_low():
    r = _pf("bloc cf1 langa cf2 mixt")
    assert r["family"] is None and r["confidence"] == "low"


def test_pf_raw_preserved():
    raw = "cf3sd 18x9m"
    assert _pf(raw)["raw_project"] == raw


# ─────────── TYPOLOGY PROFILES C1 ───────────
def _tp(**raw):
    tl = build_truth_layer(raw)
    return {p["code"]: p for p in derive_typology_profiles(raw, tl)}


def test_c1_match_high():
    p = _tp(era="comunist 1977-1990", structura="panouri prefabricate", regim_inaltime="P+4")
    assert "C1" in p and p["C1"]["confidence"] == "high" and p["C1"]["classification"] == "candidate"


def test_c1_variant_medium():
    p = _tp(era="comunist 1968-1979", structura="panouri prefabricate, posibil cadre la interior", regim_inaltime="P+4")
    assert "C1" in p and p["C1"]["confidence"] == "medium"


def test_c1_no_match_wrong_regime():
    p = _tp(era="comunist 1977-1990", structura="panouri prefabricate", regim_inaltime="P+10")
    assert "C1" not in p


def test_c1_no_match_not_panel():
    p = _tp(era="comunist 1977-1990", structura="cărămidă fără stâlpi de beton", regim_inaltime="P+4")
    assert "C1" not in p


def test_c1_no_match_not_comunist():
    p = _tp(era="post-1990", structura="panouri prefabricate", regim_inaltime="P+4")
    assert "C1" not in p


# ─────────── TYPOLOGY PROFILES C4 ───────────
def test_c4_match_high():
    p = _tp(era="comunist 1985-1990", proiect="1985-1990 turn patrat unic in cluj 21x21m", regim_inaltime="P+10")
    assert "C4" in p and p["C4"]["confidence"] == "high"


def test_c4_no_match_low_rise():
    p = _tp(era="comunist 1977-1990", proiect="bloc turn", regim_inaltime="P+4")
    assert "C4" not in p


def test_c4_no_match_not_turn():
    p = _tp(era="comunist 1977-1990", proiect="bloc bară", regim_inaltime="P+10")
    assert "C4" not in p


def test_profiles_disclaimer_present():
    p = _tp(era="comunist 1977-1990", structura="panouri prefabricate", regim_inaltime="P+4")
    assert "neverificat" in p["C1"]["disclaimer"] and "oficială" in p["C1"]["disclaimer"]


def test_no_profiles_when_no_criteria():
    assert derive_typology_profiles({"era": "post-1990"}, build_truth_layer({"era": "post-1990"})) == []


# ─────────── INTEGRATION IN TRUTH LAYER ───────────
def test_truth_layer_includes_new_fields():
    tl = build_truth_layer({"era": "comunist 1977-1990", "structura": "panouri prefabricate",
                            "regim_inaltime": "P+4", "proiect": "cf1d"})
    assert "project_family" in tl and "typology_profiles" in tl
    assert tl["project_family"]["family"] == "cf1"
    assert any(p["code"] == "C1" for p in tl["typology_profiles"])
