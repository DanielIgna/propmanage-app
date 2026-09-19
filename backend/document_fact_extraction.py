"""Faza 8B-1 — deterministic Vault PDF text-layer fact extraction.

Read-only on Buildings/Properties. Facts attach to the document only.
trust_state is always extracted. No OCR, vision, LLM, matching, or review.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any, Optional

from evidence_semantics import EXTRACTED

logger = logging.getLogger("propmanage.vault_extract")

STATUS_NOT_ATTEMPTED = "not_attempted"
STATUS_NO_USABLE_TEXT = "no_usable_text"
STATUS_EXTRACTED = "extracted"
STATUS_FAILED = "failed"

EXTRACTABLE_CATEGORIES = {"cadastru", "act_proprietate", "certificat_energetic"}

SUBJECT_DOCUMENT = "document"
METHOD = "pdf_text"
MIN_TEXT_CHARS = 8

_CAD = "cadastru"
_ACT = "act_proprietate"
_CEC = "certificat_energetic"

_CATEGORY_FACTS = {
    _CAD: {
        "street", "house_number", "locality", "apartment", "stair", "floor",
        "surface_m2", "cf_number", "construction_year",
    },
    _ACT: {
        "street", "house_number", "locality", "apartment", "stair", "floor",
        "surface_m2", "rooms", "deed_number", "issue_date",
    },
    _CEC: {
        "street", "house_number", "locality", "apartment", "surface_m2",
        "energy_class", "certificate_number", "issue_date", "construction_year",
    },
}

_SCOPE = {
    "street": "unit", "house_number": "unit", "locality": "unit",
    "apartment": "unit", "stair": "unit", "floor": "unit",
    "surface_m2": "unit", "rooms": "unit",
    "cf_number": "unit", "deed_number": "unit",
    "energy_class": "unit", "certificate_number": "unit",
    "issue_date": "document",
    "construction_year": "building",
}

# Patterns: (fact_type, regex, group, confidence, value_fn?)
# Page text is searched independently so source_location.page is exact.
_STREET_MARK = r"(?:Aleea|Strada|Str\.|Bd\.|Bulevardul|Calea)"
# Street-name tokens; document/act words cannot sit between the street marker and nr.
_STREET_NAME = (
    r"(?!document\b|act(?:ului)?\b|dosar\b|certificat(?:ul)?\b|contract(?:ul)?\b|cadastral\b)"
    r"[A-Za-zĂÂÎȘȚăâîșț0-9.\-]{1,40}"
)
_STREET = re.compile(
    rf"{_STREET_MARK}\s+[A-Za-zĂÂÎȘȚăâîșț0-9.\- ]{{2,40}}?"
    r"(?=\s+(?:nr\.?|numarul|numărul)\s*\d)",
    re.IGNORECASE,
)
_HOUSE = re.compile(
    rf"{_STREET_MARK}\s+{_STREET_NAME}(?:\s+{_STREET_NAME}){{0,2}}"
    r"\s+(?:nr\.?|numarul|numărul)\s*(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)
_LOCALITY_STOP = (
    r"nr\.?|numarul|numărul|ap(?:artament(?:ul)?)?\.?|sc(?:ara)?\.?|"
    r"et(?:aj)?\.?|suprafata|suprafață|s\.?\s*util|util[aă]|"
    r"clas[aă]|certificat|construit|finalizat|anul|an\s+constructie|"
    r"camere|c\.?\s*f\.?|\bcf\b|carte\s+funciar|act(?:ul)?|"
    r"data|emis|strada|aleea|str\.|bulevardul|calea"
)
_LOCALITY = re.compile(
    r"(?:municipiul|orasanul|ora[sș]ul|comuna|loc\.|localitatea)\s+"
    rf"(.+?)(?=\s+(?:{_LOCALITY_STOP})|\s*$|[.,;:])",
    re.IGNORECASE,
)
_AP = re.compile(r"\b(?:ap|apartament|apartamentul)\.?\s*(\d+[A-Za-z]?)\b", re.IGNORECASE)
_STAIR = re.compile(r"(?:^|[^\w])(?:sc|scara)\.?\s+(\d+|[A-Za-z])\b", re.IGNORECASE)
_FLOOR = re.compile(r"\b(?:et|etaj)\.?\s*(\d+|parter|P)\b", re.IGNORECASE)
_SURFACE = re.compile(
    r"(?:suprafata|suprafață|s\.?\s*util[aă]|util[aă])[:\s]*(\d+(?:[.,]\d+)?)\s*(?:m[p²2]|mp)?"
    r"|(\d+(?:[.,]\d+)?)\s*(?:m[p²2]|mp)\b",
    re.IGNORECASE,
)
_CF = re.compile(
    r"(?:nr\.?\s*)?(?:c\.?\s*f\.?|cf|carte funciar[aă])[:\s]*([0-9][0-9./-]{2,24})",
    re.IGNORECASE,
)
_DEED = re.compile(
    r"(?:nr\.?\s*act(?:ului)?[:\s]*([A-Z0-9][A-Z0-9./-]{2,23})"
    r"|act(?:ul)?\s+(?:de\s+)?proprietate(?:\s+nr\.?)?[:\s]*([A-Z0-9][A-Z0-9./-]{2,23}))",
    re.IGNORECASE,
)
_ENERGY = re.compile(
    r"clas[aă]\s+energetic[aă]\s*[:\s]*([A-G](?:\+|plus)?)",
    re.IGNORECASE,
)
_CERT = re.compile(
    r"(?:certificat(?:ul)?(?:\s+energetic)?|nr\.?\s*ce)\s*(?:nr\.?)?[:\s]*([A-Z0-9][A-Z0-9./-]{3,24})",
    re.IGNORECASE,
)
_YEAR = re.compile(
    r"(?:anul\s+(?:constructiei|construcției|constructor)|an(?:ul)?\s+constructie"
    r"|construit[aă]?\s+in|construit[aă]?\s+în|finalizat[aă]?\s+in|finalizat[aă]?\s+în)"
    r"[:\s]*((?:19|20)\d{2})",
    re.IGNORECASE,
)
_DATE = re.compile(
    r"(?:data(?:\s+emiterii)?|emis[aă]?\s+la)[:\s]*(\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2})",
    re.IGNORECASE,
)
_ROOMS = re.compile(r"(?:nr\.?\s*)?camere[:\s]*(\d{1,2})\b", re.IGNORECASE)


def _norm_surface(raw: str) -> Optional[float]:
    try:
        return round(float(raw.replace(" ", "").replace(",", ".")), 2)
    except ValueError:
        return None


def _norm_year(raw: str) -> Optional[int]:
    try:
        y = int(raw)
    except ValueError:
        return None
    if 1800 <= y <= 2100:
        return y
    return None


def _norm_int(raw: str) -> Optional[int]:
    try:
        return int(raw)
    except ValueError:
        return None


def _pdf_pages(data: bytes) -> list[tuple[int, str]]:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            text = ""
        pages.append((i, text))
    return pages


def _hits(pattern: re.Pattern, text: str, group: int = 1) -> list[str]:
    out = []
    for m in pattern.finditer(text):
        if m.lastindex:
            val = next((m.group(i) for i in range(1, m.lastindex + 1) if m.group(i)), None)
        else:
            val = m.group(0)
        if val:
            out.append(val.strip())
    return out


def _fact(fact_type: str, value: str, page: int, source_document: str, *,
          normalized: Any = None, confidence: str = "high",
          ambiguity: str = "explicit") -> dict:
    return {
        "subject": SUBJECT_DOCUMENT,
        "fact_type": fact_type,
        "value": value,
        "normalized_value": normalized,
        "source_document": source_document,
        "source_location": {"kind": "pdf_page", "page": page},
        "extraction_method": METHOD,
        "extraction_confidence": confidence,
        "trust_state": EXTRACTED,
        "ambiguity": ambiguity,
        "scope_candidate": _SCOPE.get(fact_type, "unknown"),
    }


def _collect_page(text: str, page: int, allowed: set[str], source_document: str) -> list[dict]:
    facts = []

    def add(ft, raw, *, norm=None, conf="high"):
        if ft not in allowed or not raw:
            return
        facts.append(_fact(ft, raw, page, source_document, normalized=norm, confidence=conf))

    if "street" in allowed:
        for m in _STREET.finditer(text):
            add("street", re.sub(r"\s+", " ", m.group(0)).strip())
    # Deed before house: "act … nr. X" is not a street number.
    deed_spans: list[tuple[int, int]] = []
    if "deed_number" in allowed:
        for m in _DEED.finditer(text):
            raw = next((m.group(i) for i in range(1, (m.lastindex or 0) + 1) if m.group(i)), None)
            if raw:
                add("deed_number", raw.strip())
                deed_spans.append(m.span())
    if "house_number" in allowed:
        for m in _HOUSE.finditer(text):
            if any(m.start() < end and m.end() > start for start, end in deed_spans):
                continue
            raw = m.group(1)
            if raw:
                add("house_number", raw, norm=raw.upper().replace(" ", ""))
    if "locality" in allowed:
        for raw in _hits(_LOCALITY, text):
            add("locality", raw.strip())
    if "apartment" in allowed:
        for raw in _hits(_AP, text):
            add("apartment", raw)
    if "stair" in allowed:
        for raw in _hits(_STAIR, text):
            add("stair", raw.upper() if raw.isalpha() else raw)
    if "floor" in allowed:
        for raw in _hits(_FLOOR, text):
            add("floor", raw)
    if "surface_m2" in allowed:
        for m in _SURFACE.finditer(text):
            raw = next((g for g in m.groups() if g), None)
            if not raw:
                continue
            add("surface_m2", raw, norm=_norm_surface(raw))
    if "cf_number" in allowed:
        for raw in _hits(_CF, text):
            add("cf_number", raw)
    if "energy_class" in allowed:
        for raw in _hits(_ENERGY, text):
            add("energy_class", raw.upper().replace("PLUS", "+"), conf="high")
    if "certificate_number" in allowed:
        for raw in _hits(_CERT, text):
            add("certificate_number", raw)
    if "construction_year" in allowed:
        for raw in _hits(_YEAR, text):
            add("construction_year", raw, norm=_norm_year(raw))
    if "issue_date" in allowed:
        for raw in _hits(_DATE, text):
            add("issue_date", raw, norm=None, conf="medium")
    if "rooms" in allowed:
        for raw in _hits(_ROOMS, text):
            add("rooms", raw, norm=_norm_int(raw))
    return facts


def _dedupe_same_page(facts: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for f in facts:
        key = (f["fact_type"], f["source_location"]["page"], str(f.get("normalized_value") or f["value"]).lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _mark_internal_conflicts(facts: list[dict]) -> list[dict]:
    by_type: dict[str, list[str]] = {}
    for f in facts:
        nv = f.get("normalized_value")
        key = str(nv if nv is not None else f["value"]).lower()
        by_type.setdefault(f["fact_type"], []).append(key)
    conflicted = {ft for ft, vals in by_type.items() if len(set(vals)) > 1}
    for f in facts:
        if f["fact_type"] in conflicted:
            f["ambiguity"] = "internal_conflict"
    return facts


def extract_facts_from_pdf_bytes(
    data: bytes,
    *,
    declared_category: str,
    source_document: str,
) -> dict:
    """Pure function. No DB. Returns {extraction_status, extracted_facts}."""
    cat = (declared_category or "").strip()
    if cat not in EXTRACTABLE_CATEGORIES:
        return {"extraction_status": STATUS_NOT_ATTEMPTED, "extracted_facts": []}
    if not data:
        return {"extraction_status": STATUS_NO_USABLE_TEXT, "extracted_facts": []}
    pages = _pdf_pages(data)
    blob = "".join(t for _p, t in pages).strip()
    if len(blob) < MIN_TEXT_CHARS:
        return {"extraction_status": STATUS_NO_USABLE_TEXT, "extracted_facts": []}
    allowed = _CATEGORY_FACTS[cat]
    facts: list[dict] = []
    for page, text in pages:
        if not (text or "").strip():
            continue
        facts.extend(_collect_page(text, page, allowed, source_document))
    facts = _mark_internal_conflicts(_dedupe_same_page(facts))
    return {"extraction_status": STATUS_EXTRACTED, "extracted_facts": facts}


def extract_for_vault_upload(
    data: bytes,
    *,
    content_type: str,
    declared_category: str,
    source_document: str,
) -> dict:
    """Skip non-PDF. Never invent facts from filename/category."""
    ctype = (content_type or "").lower()
    if "pdf" not in ctype:
        return {"extraction_status": STATUS_NOT_ATTEMPTED, "extracted_facts": []}
    try:
        return extract_facts_from_pdf_bytes(
            data, declared_category=declared_category, source_document=source_document,
        )
    except Exception:  # noqa: BLE001
        logger.exception("[vault_extract] failed for %s", source_document)
        return {"extraction_status": STATUS_FAILED, "extracted_facts": []}


VERSION_NON_INHERIT = frozenset({"extracted_facts", "extraction_status"})


def fields_for_new_document_version(parent: dict) -> dict:
    """R3: new artefact. Do not copy extracted facts or extraction_status."""
    return {k: parent.get(k) for k in parent if k != "_id" and k not in VERSION_NON_INHERIT}
