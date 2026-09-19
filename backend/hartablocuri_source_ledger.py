"""HartaBlocuri source-record ledger (Faza 1).

SOURCE EVIDENCE only. Does not create or update Buildings.

parse_workbook / EXCLUDED_ERA / import_records / run_import stay untouched.
Re-run on the same source_snapshot_id upserts by (snapshot, excel_row).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from hartablocuri_import import (
    COL,
    EXCLUDED_ERA,
    SOURCE_BASE_URL,
    SOURCE_DATASET,
    SOURCE_NAME,
    _clean,
    _extract_urls,
    _norm,
    _now,
    _parse_int,
    _parse_uat,
    _parse_year,
    _source_record_id,
)

COLLECTION = "hartablocuri_source_records"
SHEET_NAME = "Detalii blocuri"
LINK_STATUS_NONE = "none"

STATUS_IMPORTED = "imported"
STATUS_STERGE = "STERGE"
STATUS_DE_ADAUGAT = "DE_ADĂUGAT"
STATUS_MISSING_NAME = "missing_name"
STATUS_MISSING_COORDINATES = "missing_coordinates"
STATUS_MISSING_NAME_AND_COORDINATES = "missing_name_and_coordinates"
STATUS_EMPTY = "empty"
STATUS_HEADER_OR_META = "header_or_meta"

_HEADER_NAME_LABELS = {"nume", "name"}
_HEADER_LAT_LABELS = {"latitudine", "latitude"}
_META_NAME_MARKERS = (
    "teoalida",
    "baza de date",
    "despre mine",
    "proiectul",
    "studiez arhitectura",
    "interesul meu",
    "destinată folosirii",
    "destinat folosirii",
    "nu revindeți",
    "nu revindeti",
)
_UNKNOWN_STRUCTURE = {"necunoscut", "necunoscuta", "?", "-", "n/a", "na"}
_PLAN_PLACEHOLDER = re.compile(r"nu am", re.I)


def compute_file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_source_snapshot_id(path: str, *, sheet: str = SHEET_NAME, file_sha256: Optional[str] = None) -> str:
    """Deterministic snapshot id: filename stem + sheet slug + file sha256 prefix."""
    file_slug = Path(path).stem
    sheet_slug = _norm(sheet).replace(" ", "-") or "sheet"
    digest = file_sha256 or compute_file_sha256(path)
    return f"{file_slug}_{sheet_slug}_{digest[:12]}"


def _cell(row: tuple, key: str):
    idx = COL[key]
    return row[idx] if len(row) > idx else None


def _nonempty_count(row: tuple) -> int:
    n = 0
    for v in row:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        n += 1
    return n


def _usable_coords(lat, lng) -> bool:
    if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float))):
        return False
    if isinstance(lat, bool) or isinstance(lng, bool):
        return False
    return 44.0 <= float(lat) <= 48.5 and 20.0 <= float(lng) <= 27.0


def _has_numeric_coords(lat, lng) -> bool:
    return (
        isinstance(lat, (int, float)) and not isinstance(lat, bool)
        and isinstance(lng, (int, float)) and not isinstance(lng, bool)
    )


def _has_string_name(nume) -> bool:
    return isinstance(nume, str)


def _serialize_raw_value(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (str, int, float)):
        return v
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)


def raw_row_from_tuple(row: tuple) -> dict:
    """1-based column index → original Excel value (JSON/BSON-safe)."""
    out = {}
    for i, v in enumerate(row, start=1):
        out[str(i)] = _serialize_raw_value(v)
    return out


def _nume_as_text(nume) -> Optional[str]:
    if nume is None:
        return None
    if isinstance(nume, str):
        return _clean(nume)
    if isinstance(nume, bool):
        return None
    if isinstance(nume, (int, float)):
        if isinstance(nume, float) and nume.is_integer():
            return str(int(nume))
        return str(nume).strip()
    s = str(nume).strip()
    return s or None


def _is_header_or_meta(row: tuple, nne: int) -> bool:
    if nne == 0:
        return False
    nume = _cell(row, "nume")
    lat = _cell(row, "lat")
    lng = _cell(row, "lng")
    adresa = _cell(row, "adresa")
    if isinstance(nume, str) and nume.strip().lower() in _HEADER_NAME_LABELS:
        return True
    if isinstance(lat, str) and lat.strip().lower() in _HEADER_LAT_LABELS:
        return True
    if _has_numeric_coords(lat, lng) and not _usable_coords(lat, lng):
        return True
    if _usable_coords(lat, lng):
        return False
    if _clean(adresa):
        return False
    if isinstance(nume, str):
        low = nume.strip().lower()
        if any(m in low for m in _META_NAME_MARKERS):
            return True
        if len(nume.strip()) > 80:
            return True
    return False


def classify_source_status(row: tuple) -> str:
    """Parser-path classes plus header_or_meta. Does not change parse_workbook."""
    nne = _nonempty_count(row)
    if nne == 0:
        return STATUS_EMPTY
    if _is_header_or_meta(row, nne):
        return STATUS_HEADER_OR_META

    lat, lng, nume = _cell(row, "lat"), _cell(row, "lng"), _cell(row, "nume")
    has_coords = _has_numeric_coords(lat, lng)
    has_str_name = _has_string_name(nume)
    era = _clean(_cell(row, "era")) if len(row) > COL["era"] else None
    era_excl = bool(era and era.upper() in EXCLUDED_ERA)

    if not has_coords and not has_str_name:
        return STATUS_MISSING_NAME_AND_COORDINATES
    if not has_coords:
        return STATUS_MISSING_COORDINATES
    if not has_str_name:
        return STATUS_MISSING_NAME
    if era_excl:
        if era.upper() == "STERGE":
            return STATUS_STERGE
        return STATUS_DE_ADAUGAT
    return STATUS_IMPORTED


def parse_eligible_for_row(row: tuple) -> bool:
    """True iff parse_workbook would keep this row. Mirrors parser, does not call it."""
    if len(row) <= COL["poze"]:
        return False
    lat, lng, nume = row[COL["lat"]], row[COL["lng"]], row[COL["nume"]]
    if not (
        isinstance(lat, (int, float))
        and isinstance(lng, (int, float))
        and isinstance(nume, str)
    ):
        return False
    era = _clean(row[COL["era"]])
    if era and era.upper() in EXCLUDED_ERA:
        return False
    return True


def _parser_rec(row: tuple) -> Optional[dict]:
    """Same field construction as parse_workbook, for eligible rows only."""
    if not parse_eligible_for_row(row):
        return None
    lat, lng, nume = row[COL["lat"]], row[COL["lng"]], row[COL["nume"]]
    era = _clean(row[COL["era"]])
    city, neighborhood = _parse_uat(_clean(row[COL["uat"]]), row[COL["oras"]])
    adresa = _clean(row[COL["adresa"]])
    rec = {
        "nume": _clean(nume),
        "adresa": adresa,
        "judet": _clean(row[COL["judet"]]) or "Cluj",
        "city": city,
        "neighborhood": neighborhood,
        "uat": _clean(row[COL["uat"]]),
        "lat": round(float(lat), 6),
        "lng": round(float(lng), 6),
        "regim_inaltime": _clean(row[COL["regim"]]),
        "lift": _clean(row[COL["lift"]]),
        "scari": _parse_int(row[COL["scari"]]),
        "niveluri": _parse_int(row[COL["niveluri"]]),
        "niveluri_locuite": _parse_int(row[COL["niveluri_locuite"]]),
        "apartamente": _parse_int(row[COL["apartamente"]]),
        "rooms_breakdown": {
            "camere_comune": _parse_int(row[COL["camere_comune"]]),
            "garsoniere": _parse_int(row[COL["garsoniere"]]),
            "doua_camere": _parse_int(row[COL["doua_camere"]]),
            "trei_camere": _parse_int(row[COL["trei_camere"]]),
            "patru_camere": _parse_int(row[COL["patru_camere"]]),
            "cinci_camere": _parse_int(row[COL["cinci_camere"]]),
            "sase_camere": _parse_int(row[COL["sase_camere"]]),
        },
        "an_finalizare_raw": _clean(row[COL["an_finalizare"]]),
        "construction_year": _parse_year(row[COL["an_finalizare"]]),
        "era": era,
        "proiect": _clean(row[COL["proiect"]]),
        "dezvoltator": _clean(row[COL["dezvoltator"]]),
        "finisaje": _clean(row[COL["finisaje"]]),
        "structura": _clean(row[COL["structura"]]),
        "alte_detalii": _clean(row[COL["alte_detalii"]]),
        "planuri_raw": _clean(row[COL["planuri"]]),
        "poze_raw": _clean(row[COL["poze"]]),
        "risc_seismic": _clean(row[COL["risc_seismic"]]),
    }
    rec["plan_urls"] = _extract_urls(rec.get("planuri_raw"))
    rec["photo_urls"] = _extract_urls(rec.get("poze_raw"))
    rec["source_record_id"] = _source_record_id(rec)
    rec["full_address"] = ", ".join(x for x in [adresa, city, rec["judet"]] if x)
    return rec


def _parsed_from_row(row: tuple, eligible_rec: Optional[dict]) -> dict:
    nume = _cell(row, "nume")
    lat, lng = _cell(row, "lat"), _cell(row, "lng")
    adresa = _clean(_cell(row, "adresa"))
    era = _clean(_cell(row, "era"))
    city, neighborhood = _parse_uat(_clean(_cell(row, "uat")), _cell(row, "oras"))
    planuri_raw = _clean(_cell(row, "planuri"))
    poze_raw = _clean(_cell(row, "poze"))
    parsed = {
        "nume": eligible_rec.get("nume") if eligible_rec else (_clean(nume) if isinstance(nume, str) else None),
        "nume_as_text": _nume_as_text(nume),
        "adresa": adresa,
        "judet": _clean(_cell(row, "judet")),
        "oras": _clean(_cell(row, "oras")),
        "uat": _clean(_cell(row, "uat")),
        "city": city,
        "neighborhood": neighborhood,
        "norm_address": _norm(adresa),
        "lat": round(float(lat), 6) if _has_numeric_coords(lat, lng) else None,
        "lng": round(float(lng), 6) if _has_numeric_coords(lat, lng) else None,
        "regim_inaltime": _clean(_cell(row, "regim")),
        "lift": _clean(_cell(row, "lift")),
        "scari": _parse_int(_cell(row, "scari")),
        "niveluri": _parse_int(_cell(row, "niveluri")),
        "niveluri_locuite": _parse_int(_cell(row, "niveluri_locuite")),
        "apartamente": _parse_int(_cell(row, "apartamente")),
        "an_finalizare_raw": _clean(_cell(row, "an_finalizare")),
        "construction_year": _parse_year(_cell(row, "an_finalizare")),
        "era": era,
        "proiect": _clean(_cell(row, "proiect")),
        "dezvoltator": _clean(_cell(row, "dezvoltator")),
        "finisaje": _clean(_cell(row, "finisaje")),
        "structura": _clean(_cell(row, "structura")),
        "alte_detalii": _clean(_cell(row, "alte_detalii")),
        "risc_seismic": _clean(_cell(row, "risc_seismic")),
        "planuri_raw": planuri_raw,
        "poze_raw": poze_raw,
        "plan_urls": _extract_urls(planuri_raw),
        "photo_urls": _extract_urls(poze_raw),
    }
    return parsed


def _has_real_plan(planuri_raw, plan_urls: list) -> bool:
    if plan_urls:
        return True
    if not planuri_raw:
        return False
    s = str(planuri_raw)
    if _PLAN_PLACEHOLDER.search(s) and "href" not in s.lower():
        return False
    return bool(re.search(r"https?://|hartablocuri|\.png|\.jpe?g|\.jfif|href=", s, re.I))


def _useful_structure(v) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    if not s:
        return False
    folded = _norm(s)
    return folded not in _UNKNOWN_STRUCTURE and s not in _UNKNOWN_STRUCTURE


def _useful_year(v) -> bool:
    if v is None:
        return False
    s = str(v).strip().lower()
    return bool(s) and "necunoscut" not in s


def compute_valuable_excluded(*, promoted: bool, usable_coords: bool, row: tuple, parsed: dict) -> bool:
    if promoted or not usable_coords:
        return False
    scari_raw = _cell(row, "scari")
    apts_raw = _cell(row, "apartamente")
    has_stairs = isinstance(scari_raw, (int, float)) and not isinstance(scari_raw, bool) and float(scari_raw) > 0
    has_apts = isinstance(apts_raw, (int, float)) and not isinstance(apts_raw, bool) and float(apts_raw) > 0
    return bool(
        _has_real_plan(parsed.get("planuri_raw"), parsed.get("plan_urls") or [])
        or _useful_structure(parsed.get("structura"))
        or has_stairs
        or has_apts
        or _useful_year(_cell(row, "an_finalizare"))
    )


def _row_source_record_id(snapshot_id: str, sheet: str, excel_row: int, raw_row: dict) -> str:
    payload = json.dumps(
        {"snapshot": snapshot_id, "sheet": sheet, "row": excel_row, "raw": raw_row},
        ensure_ascii=False, sort_keys=True, default=str,
    )
    return "hb_row_" + hashlib.md5(payload.encode("utf-8")).hexdigest()[:20]


def build_source_record(
    row: tuple,
    *,
    excel_row: int,
    snapshot_id: str,
    excel_file: str,
    ingested_at: str,
) -> dict:
    status = classify_source_status(row)
    eligible = parse_eligible_for_row(row)
    parser_rec = _parser_rec(row) if eligible else None
    raw_row = raw_row_from_tuple(row)
    parsed = _parsed_from_row(row, parser_rec)
    lat, lng = _cell(row, "lat"), _cell(row, "lng")
    usable = _usable_coords(lat, lng)
    promoted = bool(eligible)
    if parser_rec:
        source_record_id = parser_rec["source_record_id"]
    else:
        source_record_id = _row_source_record_id(snapshot_id, SHEET_NAME, excel_row, raw_row)
    return {
        "source_name": SOURCE_NAME,
        "source_dataset": SOURCE_DATASET,
        "source_snapshot_id": snapshot_id,
        "source_record_id": source_record_id,
        "excel_file": excel_file,
        "excel_sheet": SHEET_NAME,
        "excel_row": excel_row,
        "source_status": status,
        "parse_eligible": eligible,
        "promoted_to_building": promoted,
        "building_id": None,
        "link_status": LINK_STATUS_NONE,
        "raw_row": raw_row,
        "parsed": parsed,
        "coordinates": {
            "lat": parsed.get("lat"),
            "lng": parsed.get("lng"),
            "usable": usable,
        },
        "plans": {
            "planuri_raw": parsed.get("planuri_raw"),
            "plan_urls": parsed.get("plan_urls") or [],
        },
        "photos": {
            "poze_raw": parsed.get("poze_raw"),
            "photo_urls": parsed.get("photo_urls") or [],
        },
        "reference_url": SOURCE_BASE_URL,
        "verification_status": "neverificat",
        "valuable_excluded": compute_valuable_excluded(
            promoted=promoted, usable_coords=usable, row=row, parsed=parsed,
        ),
        "ingested_at": ingested_at,
    }


def iter_hartablocuri_source_rows(
    path: str,
    *,
    snapshot_id: Optional[str] = None,
) -> Iterator[dict]:
    """Yield one ledger document per physical Excel row. Does not write DB."""
    import openpyxl

    excel_file = Path(path).name
    file_sha256 = compute_file_sha256(path)
    snapshot_id = snapshot_id or compute_source_snapshot_id(path, file_sha256=file_sha256)
    ingested_at = _now()
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_NAME]
        excel_row = 0
        for row in ws.iter_rows(values_only=True):
            excel_row += 1
            yield build_source_record(
                tuple(row),
                excel_row=excel_row,
                snapshot_id=snapshot_id,
                excel_file=excel_file,
                ingested_at=ingested_at,
            )
    finally:
        wb.close()


async def ensure_ledger_indexes(db) -> list[str]:
    coll = db[COLLECTION]
    names = []
    names.append(await coll.create_index(
        [("source_snapshot_id", 1), ("excel_row", 1)],
        unique=True, name="snapshot_excel_row_unique",
    ))
    names.append(await coll.create_index(
        [("source_snapshot_id", 1), ("source_record_id", 1)],
        unique=True, name="snapshot_source_record_id_unique",
    ))
    names.append(await coll.create_index("source_record_id", name="source_record_id"))
    names.append(await coll.create_index("source_status", name="source_status"))
    names.append(await coll.create_index("building_id", sparse=True, name="building_id_sparse"))
    return names


async def ingest_source_ledger(db, file_path: str) -> dict:
    """Upsert source evidence only. Never touches buildings / properties / import_batches."""
    from pymongo import ReplaceOne

    path = str(Path(file_path))
    snapshot_id = compute_source_snapshot_id(path)
    await ensure_ledger_indexes(db)
    coll = db[COLLECTION]
    ops = []
    status_counts: dict[str, int] = {}
    physical_rows = 0
    promoted = 0
    valuable = 0
    for doc in iter_hartablocuri_source_rows(path, snapshot_id=snapshot_id):
        physical_rows += 1
        status_counts[doc["source_status"]] = status_counts.get(doc["source_status"], 0) + 1
        if doc["promoted_to_building"]:
            promoted += 1
        if doc["valuable_excluded"]:
            valuable += 1
        ops.append(ReplaceOne(
            {
                "source_snapshot_id": doc["source_snapshot_id"],
                "excel_row": doc["excel_row"],
            },
            doc,
            upsert=True,
        ))
    written = 0
    upserted = 0
    modified = 0
    if ops:
        result = await coll.bulk_write(ops, ordered=False)
        upserted = result.upserted_count or 0
        modified = result.modified_count or 0
        written = upserted + modified + (result.matched_count or 0)
    stored = await coll.count_documents({"source_snapshot_id": snapshot_id})
    return {
        "source_snapshot_id": snapshot_id,
        "excel_file": Path(path).name,
        "excel_sheet": SHEET_NAME,
        "physical_rows": physical_rows,
        "stored": stored,
        "promoted_to_building": promoted,
        "valuable_excluded": valuable,
        "source_status": status_counts,
        "upserted": upserted,
        "modified": modified,
        "bulk_touched": written,
        "collection": COLLECTION,
    }


def _main():
    ap = argparse.ArgumentParser(description="Faza 1 — ingest HartaBlocuri source ledger (no Building writes).")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()
    from db import db

    async def _run():
        stats = await ingest_source_ledger(db, args.file)
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    asyncio.run(_run())


if __name__ == "__main__":
    _main()
