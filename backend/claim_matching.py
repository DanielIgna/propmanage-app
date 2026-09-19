"""Faza 9C — deterministic Evidence ↔ Claim matching.

Pure functions. No DB, routes, persistence, LLM, or Identity Gate.
Match results are comparisons, not trust states.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from building_identity import detect_unit_granularity, parse_query
from evidence_semantics import DECLARED, EXTRACTED, OBSERVED
from hartablocuri_import import _norm

# ── Vocabulary (9B) ────────────────────────────────────────────────────────

EXACT_MATCH = "EXACT_MATCH"
NORMALIZED_MATCH = "NORMALIZED_MATCH"
PARTIAL_MATCH = "PARTIAL_MATCH"
AMBIGUOUS = "AMBIGUOUS"
CONFLICT = "CONFLICT"
NO_MATCH = "NO_MATCH"
NOT_COMPARABLE = "NOT_COMPARABLE"

INTERNAL_CONFLICT = "INTERNAL_CONFLICT"
SOURCE_CONFLICT = "SOURCE_CONFLICT"
IDENTITY_CONFLICT = "IDENTITY_CONFLICT"

PROPERTY_ADDRESS = "PROPERTY_ADDRESS"
PROPERTY_UNIT = "PROPERTY_UNIT"
PROPERTY_STAIR = "PROPERTY_STAIR"
PROPERTY_FLOOR = "PROPERTY_FLOOR"
PROPERTY_SURFACE = "PROPERTY_SURFACE"
BUILDING_ADDRESS = "BUILDING_ADDRESS"
BUILDING_CONSTRUCTION_YEAR = "BUILDING_CONSTRUCTION_YEAR"
BUILDING_STRUCTURE = "BUILDING_STRUCTURE"
BUILDING_STAIRS = "BUILDING_STAIRS"
BUILDING_APARTMENTS = "BUILDING_APARTMENTS"
BUILDING_HEIGHT_REGIME = "BUILDING_HEIGHT_REGIME"
BUILDING_LIFT = "BUILDING_LIFT"
PROPERTY_BUILDING_RELATION = "PROPERTY_BUILDING_RELATION"

SRC_DOCUMENT = "document_extracted_fact"
SRC_HB_PROMOTED = "hartablocuri_promoted"
SRC_GOOGLE = "google_observation"
SRC_CLIENT = "client_declaration"
SRC_PROPERTY_RECORD = "property_record"
SRC_BUILDING_RECORD = "building_record"
SRC_OPERATOR = "operator_input"

_SELF_MATCH_SOURCES = frozenset({SRC_PROPERTY_RECORD, SRC_BUILDING_RECORD})
_LEDGER_MARKERS = frozenset({"excel_row", "source_snapshot_id", "link_status"})

_COMPATIBLE = {
    PROPERTY_ADDRESS: frozenset({"address", "street", "house_number", "locality"}),
    BUILDING_ADDRESS: frozenset({"address", "street", "house_number", "locality"}),
    PROPERTY_UNIT: frozenset({"apartment"}),
    PROPERTY_STAIR: frozenset({"stair"}),
    PROPERTY_FLOOR: frozenset({"floor"}),
    PROPERTY_SURFACE: frozenset({"surface_m2", "surface"}),
    BUILDING_CONSTRUCTION_YEAR: frozenset({"construction_year"}),
    BUILDING_STRUCTURE: frozenset({"structure"}),
    BUILDING_STAIRS: frozenset({"stairs"}),
    BUILDING_APARTMENTS: frozenset({"apartments"}),
    BUILDING_HEIGHT_REGIME: frozenset({"height_regime"}),
    BUILDING_LIFT: frozenset({"lift"}),
    PROPERTY_BUILDING_RELATION: frozenset({"building_ref"}),
}

_UNKNOWN_STRUCTURE = frozenset({
    "necunoscut", "necunoscuta", "n/a", "na", "?", "-", "", "unknown",
})
_LIFT_TRUE = frozenset({"da", "yes", "true", "1", "are lift", "cu lift"})
_LIFT_FALSE = frozenset({"nu", "no", "false", "0", "fara lift", "without", "nu are lift"})
_FLOOR_PARTER = frozenset({"p", "parter", "ground", "groundfloor"})


# ── Data ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Claim:
    claim_id: str
    subject_type: str
    subject_id: str
    claim_type: str
    claimed_value: Any
    normalized_value: Any
    source_context: str


@dataclass(frozen=True)
class Evidence:
    source_type: str
    source_id: str
    subject_type: str
    subject_id: str
    fact_type: str
    raw_value: Any
    normalized_value: Any
    trust_state: str
    provenance: str
    source_location: Optional[dict] = None
    extraction_method: Optional[str] = None
    extraction_confidence: Optional[str] = None

    @property
    def evidence_ref(self) -> str:
        return f"{self.source_type}:{self.source_id}:{self.fact_type}:{self.raw_value}"


@dataclass(frozen=True)
class MatchResult:
    claim_ref: str
    evidence_ref: str
    result: str
    compared_field: str
    claim_normalized: Any
    evidence_normalized: Any
    note: str = ""


@dataclass(frozen=True)
class Conflict:
    conflict_type: str
    claim_ref: Optional[str]
    evidence_refs: tuple
    result: str
    values: tuple
    created_at: Optional[str] = None


def _claim_id(subject_type: str, subject_id: str, claim_type: str) -> str:
    return f"{subject_type}:{subject_id}:{claim_type}"


def _entity_id(snap: dict) -> str:
    if not snap:
        return ""
    return str(snap.get("_id") or snap.get("id") or "")


def _present(val: Any) -> bool:
    return val is not None and str(val).strip() != ""


# ── Field norms (reuse parse_query / _norm; no fourth engine) ───────────────

def _addr(raw: Any, city: Optional[str] = None) -> dict:
    q = parse_query(str(raw or ""), city=city)
    return {
        "raw": str(raw or "").strip(),
        "folded": q["folded"],
        "house": q["house_number"],
        "suffix": (q.get("suffix") or None),
        "tokens": tuple(q.get("street_tokens") or ()),
        "city": _norm(q.get("city") or city or ""),
    }


def _house_parts(raw: Any) -> tuple[Optional[str], Optional[str]]:
    if raw is None:
        return None, None
    text = str(raw).strip()
    m = re.fullmatch(r"(\d+)([A-Za-z])?", text)
    if m:
        return m.group(1), (m.group(2) or "").upper() or None
    parsed = _addr(text)
    return parsed["house"], parsed["suffix"]


def _norm_surface(raw: Any) -> Optional[float]:
    if raw is None or str(raw).strip() == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return round(float(raw), 2)
    s = str(raw).strip().replace(" ", "").replace(",", ".")
    s = re.sub(r"(?:m[p²2]|mp)$", "", s, flags=re.IGNORECASE)
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def _norm_int(raw: Any) -> Optional[int]:
    if raw is None or str(raw).strip() == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    m = re.search(r"-?\d+", str(raw).replace(",", "."))
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def _norm_year(raw: Any) -> Optional[int]:
    y = _norm_int(raw)
    if y is None or not (1800 <= y <= 2100):
        return None
    return y


def _norm_label(raw: Any) -> Optional[str]:
    if not _present(raw):
        return None
    return _norm(str(raw))


def _norm_floor(raw: Any) -> Optional[str]:
    lab = _norm_label(raw)
    if lab is None:
        return None
    if lab in _FLOOR_PARTER:
        return "parter"
    return lab


def _norm_lift(raw: Any) -> Optional[bool]:
    if isinstance(raw, bool):
        return raw
    lab = _norm_label(raw)
    if lab is None:
        return None
    if lab in _LIFT_TRUE:
        return True
    if lab in _LIFT_FALSE:
        return False
    return None


def _street_overlap(a: dict, b: dict) -> bool:
    ta, tb = set(a.get("tokens") or ()), set(b.get("tokens") or ())
    if not ta or not tb:
        return False
    return bool(ta & tb)


# ── Claim materialization (Entity → Claim; missing field = no claim) ───────

def materialize_property_claims(property_snapshot: dict) -> list[Claim]:
    snap = property_snapshot or {}
    sid = _entity_id(snap)
    if not sid:
        return []
    out: list[Claim] = []
    address = snap.get("address")
    city = snap.get("city")
    if _present(address):
        parsed = _addr(address, city)
        out.append(Claim(
            claim_id=_claim_id("property", sid, PROPERTY_ADDRESS),
            subject_type="property", subject_id=sid,
            claim_type=PROPERTY_ADDRESS, claimed_value=str(address).strip(),
            normalized_value=parsed, source_context="properties.address",
        ))
    gran = detect_unit_granularity(snap.get("name"), address)
    link = snap.get("building_link") or {}
    unit = snap.get("apartment") or snap.get("unit") or link.get("apartment_declared") or gran.get("apartment")
    if _present(unit):
        out.append(Claim(
            claim_id=_claim_id("property", sid, PROPERTY_UNIT),
            subject_type="property", subject_id=sid,
            claim_type=PROPERTY_UNIT, claimed_value=str(unit).strip(),
            normalized_value=_norm_label(unit), source_context="properties.unit",
        ))
    stair = snap.get("stair") or snap.get("scara") or link.get("stair_declared") or gran.get("stair")
    if _present(stair):
        out.append(Claim(
            claim_id=_claim_id("property", sid, PROPERTY_STAIR),
            subject_type="property", subject_id=sid,
            claim_type=PROPERTY_STAIR, claimed_value=str(stair).strip(),
            normalized_value=_norm_label(stair), source_context="properties.stair",
        ))
    floor = snap.get("floor") or snap.get("etaj")
    if _present(floor):
        out.append(Claim(
            claim_id=_claim_id("property", sid, PROPERTY_FLOOR),
            subject_type="property", subject_id=sid,
            claim_type=PROPERTY_FLOOR, claimed_value=str(floor).strip(),
            normalized_value=_norm_floor(floor), source_context="properties.floor",
        ))
    if snap.get("surface") is not None and str(snap.get("surface")).strip() != "":
        out.append(Claim(
            claim_id=_claim_id("property", sid, PROPERTY_SURFACE),
            subject_type="property", subject_id=sid,
            claim_type=PROPERTY_SURFACE, claimed_value=snap.get("surface"),
            normalized_value=_norm_surface(snap.get("surface")),
            source_context="properties.surface",
        ))
    return out


def materialize_building_claims(building_snapshot: dict) -> list[Claim]:
    snap = building_snapshot or {}
    sid = _entity_id(snap)
    if not sid:
        return []
    ctx = snap.get("context") or {}
    out: list[Claim] = []
    address = snap.get("address")
    if _present(address):
        parsed = _addr(address, snap.get("city"))
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_ADDRESS),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_ADDRESS, claimed_value=str(address).strip(),
            normalized_value=parsed, source_context="buildings.address",
        ))
    year = ctx.get("construction_year")
    if _present(year):
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_CONSTRUCTION_YEAR),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_CONSTRUCTION_YEAR, claimed_value=year,
            normalized_value=_norm_year(year), source_context="buildings.context.construction_year",
        ))
    structure = ctx.get("building_type") or ctx.get("structure")
    if _present(structure):
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_STRUCTURE),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_STRUCTURE, claimed_value=structure,
            normalized_value=_norm_label(structure), source_context="buildings.context.structure",
        ))
    stairs = ctx.get("stairs") if ctx.get("stairs") is not None else ctx.get("scari")
    if stairs is not None and str(stairs).strip() != "":
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_STAIRS),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_STAIRS, claimed_value=stairs,
            normalized_value=_norm_int(stairs), source_context="buildings.context.stairs",
        ))
    apts = ctx.get("number_of_units")
    if apts is None:
        apts = snap.get("apartments_total")
    if apts is not None and str(apts).strip() != "":
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_APARTMENTS),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_APARTMENTS, claimed_value=apts,
            normalized_value=_norm_int(apts), source_context="buildings.context.number_of_units",
        ))
    regime = ctx.get("height_regime") or ctx.get("regim_inaltime")
    if _present(regime):
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_HEIGHT_REGIME),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_HEIGHT_REGIME, claimed_value=regime,
            normalized_value=_norm_label(regime), source_context="buildings.context.height_regime",
        ))
    if ctx.get("lift") is not None and str(ctx.get("lift")).strip() != "":
        out.append(Claim(
            claim_id=_claim_id("building", sid, BUILDING_LIFT),
            subject_type="building", subject_id=sid,
            claim_type=BUILDING_LIFT, claimed_value=ctx.get("lift"),
            normalized_value=_norm_lift(ctx.get("lift")), source_context="buildings.context.lift",
        ))
    return out


def materialize_relation_claims(property_snapshot: dict,
                                building_link_snapshot: Optional[dict] = None) -> list[Claim]:
    snap = property_snapshot or {}
    sid = _entity_id(snap)
    bid = snap.get("building_id")
    if not sid or not _present(bid):
        return []
    link = building_link_snapshot if building_link_snapshot is not None else (snap.get("building_link") or {})
    return [Claim(
        claim_id=_claim_id("relation", sid, PROPERTY_BUILDING_RELATION),
        subject_type="relation", subject_id=sid,
        claim_type=PROPERTY_BUILDING_RELATION,
        claimed_value=str(bid),
        normalized_value=str(bid),
        source_context="properties.building_id",
    )]


# ── Evidence materialization ───────────────────────────────────────────────

def _doc_fact_norm(fact_type: str, raw: Any, existing: Any) -> Any:
    if existing is not None:
        if fact_type in {"surface_m2", "surface"}:
            return _norm_surface(existing if existing is not None else raw)
        if fact_type == "construction_year":
            return _norm_year(existing if existing is not None else raw)
        return existing
    if fact_type in {"surface_m2", "surface"}:
        return _norm_surface(raw)
    if fact_type == "construction_year":
        return _norm_year(raw)
    if fact_type in {"apartment", "stair"}:
        return _norm_label(raw)
    if fact_type == "floor":
        return _norm_floor(raw)
    if fact_type == "house_number":
        n, sfx = _house_parts(raw)
        return {"house": n, "suffix": sfx}
    if fact_type in {"address", "street", "locality"}:
        return _addr(raw)
    return raw


def materialize_document_evidence(extracted_facts: list, *,
                                  document_id: Optional[str] = None) -> list[Evidence]:
    out: list[Evidence] = []
    for fact in extracted_facts or []:
        if not isinstance(fact, dict):
            continue
        raw = fact.get("value")
        if raw is None:
            continue
        ft = str(fact.get("fact_type") or "")
        src_doc = str(fact.get("source_document") or document_id or "")
        out.append(Evidence(
            source_type=SRC_DOCUMENT,
            source_id=src_doc,
            subject_type="document",
            subject_id=src_doc,
            fact_type=ft,
            raw_value=raw,
            normalized_value=_doc_fact_norm(ft, raw, fact.get("normalized_value")),
            trust_state=EXTRACTED,
            provenance=EXTRACTED,
            source_location=fact.get("source_location"),
            extraction_method=fact.get("extraction_method") or "pdf_text",
            extraction_confidence=fact.get("extraction_confidence"),
        ))
    return out


def _is_unpromoted_ledger(payload: dict) -> bool:
    if not payload:
        return False
    if payload.get("collection") == "hartablocuri_source_records":
        return True
    if payload.get("link_status") == "none" and "excel_row" in payload:
        return True
    if "source_snapshot_id" in payload and "raw" not in payload and "fields" not in payload:
        return True
    return False


def materialize_hartablocuri_evidence(hartablocuri_payload: dict, *,
                                      building_id: Optional[str] = None) -> list[Evidence]:
    payload = hartablocuri_payload or {}
    if _is_unpromoted_ledger(payload):
        return []
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else None
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else None
    src = raw or fields or {}
    if not src:
        return []
    sid = str(building_id or payload.get("building_id") or "")
    source_id = str(payload.get("source_record_id") or sid or "hb")
    pairs = []
    if raw:
        pairs = [
            ("address", src.get("adresa")),
            ("construction_year", src.get("construction_year") or src.get("an_finalizare_raw")),
            ("structure", src.get("structura")),
            ("stairs", src.get("scari")),
            ("apartments", src.get("apartamente")),
            ("height_regime", src.get("regim_inaltime")),
            ("lift", src.get("lift")),
        ]
    else:
        pairs = [
            ("address", src.get("address")),
            ("construction_year", src.get("year_estimated")),
            ("structure", src.get("structure")),
            ("stairs", src.get("stairs")),
            ("apartments", src.get("apartments")),
            ("height_regime", src.get("height_regime")),
            ("lift", src.get("lift")),
        ]
    out: list[Evidence] = []
    for ft, val in pairs:
        if val is None or str(val).strip() == "":
            continue
        if ft == "address":
            nv = _addr(val)
        elif ft == "construction_year":
            nv = _norm_year(val)
        elif ft == "structure":
            nv = _norm_label(val)
        elif ft in {"stairs", "apartments"}:
            nv = _norm_int(val)
        elif ft == "height_regime":
            nv = _norm_label(val)
        elif ft == "lift":
            nv = _norm_lift(val)
        else:
            nv = val
        out.append(Evidence(
            source_type=SRC_HB_PROMOTED,
            source_id=source_id,
            subject_type="building",
            subject_id=sid,
            fact_type=ft,
            raw_value=val,
            normalized_value=nv,
            trust_state=OBSERVED,
            provenance=OBSERVED,
        ))
    return out


def materialize_google_evidence(google_observation: dict, *,
                                source_id: str = "google") -> list[Evidence]:
    obs = google_observation or {}
    fields = obs.get("fields") if isinstance(obs.get("fields"), dict) else {}
    address = (
        obs.get("formatted_address")
        or fields.get("formatted_address")
        or obs.get("query")
        or fields.get("query")
    )
    if not _present(address):
        return []
    return [Evidence(
        source_type=SRC_GOOGLE,
        source_id=str(source_id),
        subject_type="observation",
        subject_id=str(source_id),
        fact_type="address",
        raw_value=str(address).strip(),
        normalized_value=_addr(address),
        trust_state=OBSERVED,
        provenance=OBSERVED,
    )]


def materialize_client_observations(observations: list) -> list[Evidence]:
    out: list[Evidence] = []
    for i, obs in enumerate(observations or []):
        if not isinstance(obs, dict):
            continue
        fields = obs.get("fields") or {}
        oid = str(obs.get("property_id") or obs.get("source_id") or f"client-{i}")
        for ft, key in (("stair", "stair"), ("apartment", "apartment")):
            val = fields.get(key)
            if not _present(val):
                continue
            out.append(Evidence(
                source_type=SRC_CLIENT,
                source_id=oid,
                subject_type="property",
                subject_id=oid,
                fact_type=ft,
                raw_value=val,
                normalized_value=_norm_label(val) if ft != "floor" else _norm_floor(val),
                trust_state=DECLARED,
                provenance=DECLARED,
            ))
    return out


# ── Self-match ─────────────────────────────────────────────────────────────

def is_self_match(claim: Claim, evidence: Evidence) -> bool:
    """Evidence taken from the same Entity state that produced the claim."""
    if evidence.source_type not in _SELF_MATCH_SOURCES:
        return False
    if evidence.subject_id and claim.subject_id and str(evidence.subject_id) == str(claim.subject_id):
        return True
    if evidence.source_id and claim.subject_id and str(evidence.source_id) == str(claim.subject_id):
        return True
    return False


# ── Comparisons ────────────────────────────────────────────────────────────

def _result(claim: Claim, evidence: Evidence, result: str, *,
            compared: str, cnorm: Any, enorm: Any, note: str = "") -> MatchResult:
    return MatchResult(
        claim_ref=claim.claim_id,
        evidence_ref=evidence.evidence_ref,
        result=result,
        compared_field=compared,
        claim_normalized=cnorm,
        evidence_normalized=enorm,
        note=note,
    )


def _scalar_match(claim: Claim, evidence: Evidence, cnorm: Any, enorm: Any, *,
                  compared: str) -> MatchResult:
    if cnorm is None or enorm is None:
        return _result(claim, evidence, NOT_COMPARABLE, compared=compared, cnorm=cnorm, enorm=enorm)
    raw_c, raw_e = str(claim.claimed_value).strip(), str(evidence.raw_value).strip()
    if raw_c == raw_e:
        return _result(claim, evidence, EXACT_MATCH, compared=compared, cnorm=cnorm, enorm=enorm)
    if cnorm == enorm:
        return _result(claim, evidence, NORMALIZED_MATCH, compared=compared, cnorm=cnorm, enorm=enorm)
    return _result(claim, evidence, CONFLICT, compared=compared, cnorm=cnorm, enorm=enorm)


def _compare_house(ch: Optional[str], cs: Optional[str],
                   eh: Optional[str], es: Optional[str]) -> Optional[str]:
    if not ch or not eh:
        return None
    if ch != eh:
        return CONFLICT
    if (cs or None) == (es or None):
        return "same"
    return PARTIAL_MATCH


def _compare_address(claim: Claim, evidence: Evidence) -> MatchResult:
    city = None
    if isinstance(claim.normalized_value, dict):
        ca = claim.normalized_value
    else:
        ca = _addr(claim.claimed_value)
    if evidence.fact_type == "house_number":
        if isinstance(evidence.normalized_value, dict) and "house" in evidence.normalized_value:
            eh, es = evidence.normalized_value.get("house"), evidence.normalized_value.get("suffix")
        else:
            eh, es = _house_parts(evidence.raw_value)
        house = _compare_house(ca.get("house"), ca.get("suffix"), eh, es)
        enorm = {"house": eh, "suffix": es}
        if house is None:
            return _result(claim, evidence, AMBIGUOUS, compared="house_number",
                           cnorm=ca, enorm=enorm, note="missing house number")
        if house == CONFLICT:
            return _result(claim, evidence, CONFLICT, compared="house_number", cnorm=ca, enorm=enorm)
        if house == PARTIAL_MATCH:
            return _result(claim, evidence, PARTIAL_MATCH, compared="house_number",
                           cnorm=ca, enorm=enorm, note="address suffix differs")
        raw_same = str(claim.claimed_value).strip() == str(evidence.raw_value).strip()
        return _result(claim, evidence, EXACT_MATCH if raw_same else NORMALIZED_MATCH,
                       compared="house_number", cnorm=ca, enorm=enorm)

    if evidence.fact_type == "street":
        ea = evidence.normalized_value if isinstance(evidence.normalized_value, dict) else _addr(evidence.raw_value)
        if _street_overlap(ca, ea):
            return _result(claim, evidence, PARTIAL_MATCH, compared="street",
                           cnorm=ca, enorm=ea, note="street only")
        return _result(claim, evidence, NO_MATCH, compared="street", cnorm=ca, enorm=ea)

    if evidence.fact_type == "locality":
        ea = evidence.normalized_value if isinstance(evidence.normalized_value, dict) else _addr(evidence.raw_value)
        ev_city = ea.get("city") or _norm(str(evidence.raw_value))
        cl_city = ca.get("city")
        if not cl_city or not ev_city:
            return _result(claim, evidence, AMBIGUOUS, compared="locality", cnorm=ca, enorm=ea)
        if ev_city in cl_city or cl_city in ev_city:
            return _result(claim, evidence, PARTIAL_MATCH, compared="locality", cnorm=ca, enorm=ea)
        return _result(claim, evidence, CONFLICT, compared="locality", cnorm=ca, enorm=ea)

    ea = evidence.normalized_value if isinstance(evidence.normalized_value, dict) else _addr(evidence.raw_value)
    raw_same = str(claim.claimed_value).strip() == str(evidence.raw_value).strip()
    street = _street_overlap(ca, ea)
    house = _compare_house(ca.get("house"), ca.get("suffix"), ea.get("house"), ea.get("suffix"))
    cities = ca.get("city") and ea.get("city")
    city_ok = True
    if cities:
        city_ok = ca["city"] in ea["city"] or ea["city"] in ca["city"]

    if street and house == CONFLICT:
        return _result(claim, evidence, CONFLICT, compared="address", cnorm=ca, enorm=ea)
    if street and cities and not city_ok:
        return _result(claim, evidence, CONFLICT, compared="locality", cnorm=ca, enorm=ea)
    if street and house == PARTIAL_MATCH:
        return _result(claim, evidence, PARTIAL_MATCH, compared="address",
                       cnorm=ca, enorm=ea, note="address suffix differs")
    if street and house == "same" and city_ok:
        return _result(claim, evidence, EXACT_MATCH if raw_same else NORMALIZED_MATCH,
                       compared="address", cnorm=ca, enorm=ea)
    if street and house is None:
        return _result(claim, evidence, AMBIGUOUS, compared="address",
                       cnorm=ca, enorm=ea, note="missing house number")
    if street:
        return _result(claim, evidence, PARTIAL_MATCH, compared="address", cnorm=ca, enorm=ea)
    return _result(claim, evidence, NO_MATCH, compared="address", cnorm=ca, enorm=ea)


def _compare_structure(claim: Claim, evidence: Evidence) -> MatchResult:
    c = claim.normalized_value if claim.normalized_value is not None else _norm_label(claim.claimed_value)
    e = evidence.normalized_value if evidence.normalized_value is not None else _norm_label(evidence.raw_value)
    if c in _UNKNOWN_STRUCTURE or e in _UNKNOWN_STRUCTURE or not c or not e:
        return _result(claim, evidence, NOT_COMPARABLE, compared="structure", cnorm=c, enorm=e)
    if c == e:
        raw_same = str(claim.claimed_value).strip() == str(evidence.raw_value).strip()
        return _result(claim, evidence, EXACT_MATCH if raw_same else NORMALIZED_MATCH,
                       compared="structure", cnorm=c, enorm=e)
    return _result(claim, evidence, NOT_COMPARABLE, compared="structure",
                   cnorm=c, enorm=e, note="vocabularies not clearly compatible")


def _compare_relation(claim: Claim, evidence: Evidence) -> MatchResult:
    claimed = str(claim.normalized_value or claim.claimed_value)
    ev = str(evidence.normalized_value if evidence.normalized_value is not None else evidence.raw_value)
    if claimed == ev:
        return _result(claim, evidence, EXACT_MATCH, compared="building_id",
                       cnorm=claimed, enorm=ev, note="supports linked building")
    return _result(claim, evidence, CONFLICT, compared="building_id",
                   cnorm=claimed, enorm=ev, note="different building")


def match_claim_evidence(claim: Claim, evidence: Evidence) -> Optional[MatchResult]:
    if is_self_match(claim, evidence):
        return None
    allowed = _COMPATIBLE.get(claim.claim_type)
    if not allowed or evidence.fact_type not in allowed:
        return _result(
            claim, evidence, NOT_COMPARABLE,
            compared=evidence.fact_type or claim.claim_type,
            cnorm=claim.normalized_value, enorm=evidence.normalized_value,
        )
    if claim.claim_type in {PROPERTY_ADDRESS, BUILDING_ADDRESS}:
        return _compare_address(claim, evidence)
    if claim.claim_type == PROPERTY_UNIT:
        return _scalar_match(claim, evidence, claim.normalized_value or _norm_label(claim.claimed_value),
                             evidence.normalized_value or _norm_label(evidence.raw_value),
                             compared="apartment")
    if claim.claim_type == PROPERTY_STAIR:
        return _scalar_match(claim, evidence, claim.normalized_value or _norm_label(claim.claimed_value),
                             evidence.normalized_value or _norm_label(evidence.raw_value),
                             compared="stair")
    if claim.claim_type == PROPERTY_FLOOR:
        return _scalar_match(claim, evidence, claim.normalized_value or _norm_floor(claim.claimed_value),
                             evidence.normalized_value or _norm_floor(evidence.raw_value),
                             compared="floor")
    if claim.claim_type == PROPERTY_SURFACE:
        return _scalar_match(claim, evidence, claim.normalized_value if isinstance(claim.normalized_value, float)
                             else _norm_surface(claim.claimed_value),
                             evidence.normalized_value if isinstance(evidence.normalized_value, float)
                             else _norm_surface(evidence.raw_value),
                             compared="surface")
    if claim.claim_type == BUILDING_CONSTRUCTION_YEAR:
        return _scalar_match(claim, evidence, claim.normalized_value or _norm_year(claim.claimed_value),
                             evidence.normalized_value if isinstance(evidence.normalized_value, int)
                             else _norm_year(evidence.raw_value),
                             compared="construction_year")
    if claim.claim_type == BUILDING_STRUCTURE:
        return _compare_structure(claim, evidence)
    if claim.claim_type in {BUILDING_STAIRS, BUILDING_APARTMENTS}:
        return _scalar_match(claim, evidence, claim.normalized_value if isinstance(claim.normalized_value, int)
                             else _norm_int(claim.claimed_value),
                             evidence.normalized_value if isinstance(evidence.normalized_value, int)
                             else _norm_int(evidence.raw_value),
                             compared=evidence.fact_type)
    if claim.claim_type == BUILDING_HEIGHT_REGIME:
        return _scalar_match(claim, evidence, claim.normalized_value or _norm_label(claim.claimed_value),
                             evidence.normalized_value or _norm_label(evidence.raw_value),
                             compared="height_regime")
    if claim.claim_type == BUILDING_LIFT:
        return _scalar_match(claim, evidence, claim.normalized_value if isinstance(claim.normalized_value, bool)
                             else _norm_lift(claim.claimed_value),
                             evidence.normalized_value if isinstance(evidence.normalized_value, bool)
                             else _norm_lift(evidence.raw_value),
                             compared="lift")
    if claim.claim_type == PROPERTY_BUILDING_RELATION:
        return _compare_relation(claim, evidence)
    return _result(claim, evidence, NOT_COMPARABLE, compared=claim.claim_type,
                   cnorm=claim.normalized_value, enorm=evidence.normalized_value)


def detect_conflicts(claims: list[Claim], evidence: list[Evidence],
                     results: Optional[list[MatchResult]] = None) -> list[Conflict]:
    conflicts: list[Conflict] = []
    by_src: dict[tuple, list[Evidence]] = {}
    for ev in evidence:
        by_src.setdefault((ev.source_id, ev.fact_type), []).append(ev)
    for (_sid, _ft), group in by_src.items():
        norms = []
        for ev in group:
            key = ev.normalized_value if ev.normalized_value is not None else ev.raw_value
            if isinstance(key, dict):
                key = tuple(sorted((k, str(v)) for k, v in key.items()))
            norms.append((key, ev))
        uniq = {n[0] for n in norms}
        if len(uniq) > 1:
            conflicts.append(Conflict(
                conflict_type=INTERNAL_CONFLICT,
                claim_ref=None,
                evidence_refs=tuple(ev.evidence_ref for ev in group),
                result=CONFLICT,
                values=tuple(ev.raw_value for ev in group),
            ))

    results = results if results is not None else []
    by_claim: dict[str, list[MatchResult]] = {}
    for r in results:
        by_claim.setdefault(r.claim_ref, []).append(r)
    claim_map = {c.claim_id: c for c in claims}
    for cid, rs in by_claim.items():
        clash = [r for r in rs if r.result == CONFLICT]
        if len(clash) < 1:
            continue
        ev_by_ref = {e.evidence_ref: e for e in evidence}
        sources = {ev_by_ref[r.evidence_ref].source_type for r in clash if r.evidence_ref in ev_by_ref}
        claim = claim_map.get(cid)
        if claim and claim.claim_type == PROPERTY_BUILDING_RELATION:
            conflicts.append(Conflict(
                conflict_type=IDENTITY_CONFLICT,
                claim_ref=cid,
                evidence_refs=tuple(r.evidence_ref for r in clash),
                result=CONFLICT,
                values=tuple(r.evidence_normalized for r in clash),
            ))
            continue
        if len(sources) >= 1:
            conflicts.append(Conflict(
                conflict_type=SOURCE_CONFLICT,
                claim_ref=cid,
                evidence_refs=tuple(r.evidence_ref for r in clash),
                result=CONFLICT,
                values=tuple(r.evidence_normalized for r in clash),
            ))

    # Distinct evidence sources on the same claim with differing comparable norms
    # even when one side matches the claim (HB 40 vs PTR-originated claim 13).
    for claim in claims:
        if claim.claim_type == PROPERTY_BUILDING_RELATION:
            continue
        allowed = _COMPATIBLE.get(claim.claim_type) or frozenset()
        relevant = [e for e in evidence if e.fact_type in allowed and not is_self_match(claim, e)]
        by_source: dict[str, list[Evidence]] = {}
        for ev in relevant:
            by_source.setdefault(ev.source_type, []).append(ev)
        if len(by_source) < 2:
            continue
        source_norms = {}
        for st, evs in by_source.items():
            source_norms[st] = {str(ev.normalized_value) for ev in evs}
        distinct = set()
        for vals in source_norms.values():
            distinct |= vals
        if len(distinct) > 1:
            refs = tuple(e.evidence_ref for e in relevant)
            already = any(
                c.conflict_type == SOURCE_CONFLICT and c.claim_ref == claim.claim_id
                for c in conflicts
            )
            if not already:
                conflicts.append(Conflict(
                    conflict_type=SOURCE_CONFLICT,
                    claim_ref=claim.claim_id,
                    evidence_refs=refs,
                    result=CONFLICT,
                    values=tuple(sorted(distinct)),
                ))
    return conflicts


def match_claims(claims: list[Claim], evidence: list[Evidence]) -> dict:
    """Pure. No module state. V1/V2 independence = caller supplies the sets."""
    results: list[MatchResult] = []
    for claim in claims:
        for ev in evidence:
            hit = match_claim_evidence(claim, ev)
            if hit is not None:
                results.append(hit)
    conflicts = detect_conflicts(claims, evidence, results)
    return {"matches": results, "conflicts": conflicts}
