"""Faza 1 — HartaBlocuri Truth Layer READ MODEL v1.0 (derivare pură, read-only)."""
from hartablocuri_read_layer import build_truth_layer


def _tl(**raw):
    return build_truth_layer(raw)


# ─────────── ERA (L0) ───────────
def test_era_valid_high():
    r = _tl(era="Comunist 1968-1990")["era"]
    assert r["value"] == "Comunist 1968-1990" and r["level"] == "L0" and r["confidence"] == "high"


def test_era_missing_not_available():
    r = _tl(proiect="bara")["era"]
    assert r["value"] is None and r["confidence"] == "not_available"


def test_era_unknown_marker():
    r = _tl(era="necunoscut")["era"]
    assert r["value"] is None and r["confidence"] == "unknown"


def test_era_not_derived_from_year():
    # An prezent, era absentă → NU se estimează era din an
    r = _tl(construction_year=1975, an_finalizare_raw="1975")["era"]
    assert r["value"] is None and r["confidence"] == "not_available"


# ─────────── FORM (L1) ───────────
def test_form_bara_with_code_high():
    r = _tl(proiect="bloc bară cf1d")["form"]
    assert r["value"] == "bara" and r["confidence"] == "high" and r["raw_project"] == "bloc bară cf1d"


def test_form_turn_high():
    r = _tl(proiect="turn P+10")["form"]
    assert r["value"] == "turn" and r["confidence"] == "high"


def test_form_drept_high():
    r = _tl(proiect="bloc drept")["form"]
    assert r["value"] == "drept" and r["confidence"] == "high"


def test_form_cruce_drept_ambiguous_mixt_low():
    r = _tl(proiect="cruce/drept")["form"]
    assert r["value"] == "mixt" and r["confidence"] == "low"


def test_form_code_only_unknown():
    r = _tl(proiect="cf1d")["form"]
    assert r["value"] == "unknown" and r["confidence"] == "unknown"


def test_form_bloc_unicat_unknown():
    r = _tl(proiect="bloc unicat")["form"]
    assert r["value"] == "unknown" and r["confidence"] == "unknown"


def test_form_de_adaugat_unknown():
    r = _tl(proiect="DE ADĂUGAT")["form"]
    assert r["value"] == "unknown" and r["confidence"] == "unknown"


def test_form_missing_not_available():
    r = _tl(era="x")["form"]
    assert r["value"] == "unknown" and r["confidence"] == "not_available" and r["raw_project"] is None


# ─────────── REGIME (L1) ───────────
def test_regime_p_plus_4():
    r = _tl(regim_inaltime="P+4")["regime"]
    assert r["derived_floors"] == 4 and r["confidence"] == "high"


def test_regime_p_plus_10():
    r = _tl(regim_inaltime="P+10")["regime"]
    assert r["derived_floors"] == 10 and r["confidence"] == "high"


def test_regime_parter_plus_etaje():
    r = _tl(regim_inaltime="parter + 4 etaje")["regime"]
    assert r["derived_floors"] == 4 and r["confidence"] == "high"


def test_regime_subsol_ambiguous_unknown():
    r = _tl(regim_inaltime="S+P+4")["regime"]
    assert r["derived_floors"] is None and r["confidence"] == "unknown"


def test_regime_demisol_ambiguous_unknown():
    r = _tl(regim_inaltime="D+P+4")["regime"]
    assert r["derived_floors"] is None and r["confidence"] == "unknown"


def test_regime_missing_not_available():
    r = _tl(era="x")["regime"]
    assert r["derived_floors"] is None and r["confidence"] == "not_available"


def test_regime_no_overwrite_fields():
    # derivarea nu adaugă niveluri/regim/floors — doar derived_floors în read model
    r = _tl(regim_inaltime="P+4", niveluri=99)["regime"]
    assert set(r.keys()) == {"raw", "source_field", "level", "derived_floors", "confidence"}


# ─────────── CARTIER (L0) ───────────
def test_neighborhood_source_fact():
    r = _tl(neighborhood="Gheorgheni")["neighborhood"]
    assert r["value"] == "Gheorgheni" and r["level"] == "L0" and r["confidence"] == "high"


def test_neighborhood_missing_not_available():
    r = _tl(era="x")["neighborhood"]
    assert r["value"] is None and r["confidence"] == "not_available"


# ─────────── PROVENANCE ───────────
def test_provenance_preserved():
    p = _tl(era="x")["provenance"]
    assert p["source"] == "hartablocuri"
    assert p["verification_status"] == "neverificat"
    assert p["verification_note"] == "Date externe — neverificate de PropManage"


# ─────────── NULL SAFETY ───────────
def test_no_hb_returns_none():
    assert build_truth_layer(None) is None
    assert build_truth_layer({}) is None
