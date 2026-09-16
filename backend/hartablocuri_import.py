"""HartaBlocuri Cluj — external building reference importer (aditiv, non-destructiv).

Reguli:
  * HartaBlocuri = sursă externă de referință, NU sursă de adevăr.
  * Import idempotent: cheia `source_record_id` (hash determinist) → reimportul nu duplică.
  * Matching cu Buildings PropManage existente prin adresă normalizată + coordonate.
    Rezultat obligatoriu: UN singur Building cu 2 surse (PropManage + HartaBlocuri).
  * NU suprascrie date manuale/verificate. Conflictele se marchează pentru review.
  * verification_status pornește mereu "neverificat".
  * NU activează Digital Twin / Building Health / PVI / Twin Maturity / Cartea Casei.

Rulare CLI:
    python -m services.hartablocuri_import --file /tmp/harta.xlsx [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

SOURCE_NAME = "HartaBlocuri"
SOURCE_DATASET = "HartaBlocuri Cluj"
SOURCE_BASE_URL = "https://www.hartablocuri.ro"
EXCLUDED_ERA = {"STERGE", "DE ADĂUGAT", "DE ADAUGAT"}

# Column indices (0-based within the row tuple of sheet "Detalii blocuri")
COL = {
    "nume": 1, "lat": 2, "lng": 3, "judet": 4, "oras": 5, "uat": 6, "adresa": 7,
    "regim": 8, "lift": 9, "scari": 10, "niveluri": 11, "niveluri_locuite": 12,
    "apartamente": 13, "camere_comune": 14, "garsoniere": 15, "doua_camere": 16,
    "trei_camere": 17, "patru_camere": 18, "cinci_camere": 19, "sase_camere": 20,
    "risc_seismic": 25, "an_finalizare": 26, "era": 28, "proiect": 29,
    "dezvoltator": 30, "finisaje": 31, "structura": 32, "alte_detalii": 33,
    "planuri": 34, "poze": 35,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.startswith("="):  # skip Excel formulas / blanks
        return None
    return s


def _norm(s: Optional[str]) -> str:
    """Normalizează pentru matching: fără diacritice, minuscule, fără punctuație."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    repl = {
        r"\bstr\b": "strada", r"\bbd\b": "bulevardul", r"\bb dul\b": "bulevardul",
        r"\bbdul\b": "bulevardul", r"\bblv\b": "bulevardul", r"\bnr\b": "nr",
        r"\bap\b": "ap", r"\bsc\b": "sc",
    }
    for pat, rep in repl.items():
        s = re.sub(pat, rep, s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_year(v) -> Optional[int]:
    s = _clean(v)
    if not s:
        return None
    m = re.search(r"\b(1[789]\d{2}|20\d{2})\b", s)
    if m:
        y = int(m.group(1))
        if 1700 <= y <= 2100:
            return y
    return None


def _parse_int(v) -> Optional[int]:
    s = _clean(v)
    if not s:
        return None
    m = re.search(r"\d+", s)
    return int(m.group(0)) if m else None


def _parse_uat(uat: Optional[str], oras: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """UAT ierarhic: 'municipiu Cluj-Napoca > cartier Gheorgheni > nord' → (city, neighborhood)."""
    city = None
    neighborhood = None
    if uat:
        parts = [p.strip() for p in str(uat).split(">") if p.strip()]
        for p in parts:
            low = p.lower()
            if any(low.startswith(pref) for pref in ("municipiu", "oras", "oraș", "comuna", "comună", "sat")):
                city = re.sub(r"^(municipiu|ora[sș]|comun[aă]|sat)\s+", "", p, flags=re.I).strip()
            elif low.startswith("cartier"):
                neighborhood = re.sub(r"^cartier\s+", "", p, flags=re.I).strip()
    if not city:
        c = _clean(oras)
        # etichete de secțiune, nu orașe reale
        if c and c.lower() not in ("ansambluri noi", "imobile interbelice/antebelice"):
            city = c
    return city, neighborhood


def _extract_urls(html: Optional[str]) -> list[str]:
    if not html:
        return []
    urls = re.findall(r'(?:https?:)?//[^\s"\'<>]+hartablocuri\.ro[^\s"\'<>]*', str(html))
    return sorted({("https:" + u if u.startswith("//") else u) for u in urls})


def parse_workbook(path: str, limit: Optional[int] = None) -> list[dict]:
    """Parsează foaia 'Detalii blocuri' → listă de recorduri normalizate (exclude STERGE/DE ADĂUGAT)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Detalii blocuri"]
    records: list[dict] = []
    for row in ws.iter_rows(values_only=True):
        if len(row) <= COL["poze"]:
            continue
        lat, lng, nume = row[COL["lat"]], row[COL["lng"]], row[COL["nume"]]
        if not (isinstance(lat, (int, float)) and isinstance(lng, (int, float)) and isinstance(nume, str)):
            continue
        era = _clean(row[COL["era"]])
        if era and era.upper() in EXCLUDED_ERA:
            continue
        city, neighborhood = _parse_uat(_clean(row[COL["uat"]]), row[COL["oras"]])
        adresa = _clean(row[COL["adresa"]])
        nume_c = _clean(nume)
        rec = {
            "nume": nume_c,
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
        records.append(rec)
        if limit and len(records) >= limit:
            break
    return records


def _source_record_id(rec: dict) -> str:
    key = "|".join([
        _norm(rec.get("nume")), _norm(rec.get("adresa")),
        f"{rec.get('lat')}", f"{rec.get('lng')}",
    ])
    return "hb_" + hashlib.md5(key.encode("utf-8")).hexdigest()[:20]


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    from math import radians, sin, cos, sqrt, atan2
    r = 6371000.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(1 - a))


# Câmpuri normalizate top-level context ↔ cheie record
_CONTEXT_MAP = {
    "construction_year": "construction_year",
    "floors": "niveluri",
    "number_of_units": "apartamente",
    "neighborhood": "neighborhood",
    "lat": "lat",
    "lng": "lng",
}


def build_external_source(rec: dict, batch_id: str) -> dict:
    """Payload de proveniență HartaBlocuri (raw + normalizat), stocat sub context.external_sources."""
    return {
        "source_name": SOURCE_NAME,
        "source_dataset": SOURCE_DATASET,
        "source_record_id": rec["source_record_id"],
        "import_batch_id": batch_id,
        "imported_at": _now(),
        "verification_status": "neverificat",
        "reference_url": SOURCE_BASE_URL,
        "raw": {
            "nume": rec.get("nume"), "adresa": rec.get("adresa"), "judet": rec.get("judet"),
            "city": rec.get("city"), "neighborhood": rec.get("neighborhood"), "uat": rec.get("uat"),
            "lat": rec.get("lat"), "lng": rec.get("lng"),
            "regim_inaltime": rec.get("regim_inaltime"), "lift": rec.get("lift"),
            "scari": rec.get("scari"), "niveluri": rec.get("niveluri"),
            "niveluri_locuite": rec.get("niveluri_locuite"), "apartamente": rec.get("apartamente"),
            "rooms_breakdown": rec.get("rooms_breakdown"),
            "an_finalizare_raw": rec.get("an_finalizare_raw"), "construction_year": rec.get("construction_year"),
            "era": rec.get("era"), "proiect": rec.get("proiect"), "dezvoltator": rec.get("dezvoltator"),
            "finisaje": rec.get("finisaje"), "structura": rec.get("structura"),
            "alte_detalii": rec.get("alte_detalii"), "risc_seismic": rec.get("risc_seismic"),
            "planuri_raw": rec.get("planuri_raw"), "poze_raw": rec.get("poze_raw"),
        },
        "plan_urls": rec.get("plan_urls") or [],
        "photo_urls": rec.get("photo_urls") or [],
    }


def _reliable_address(adresa: Optional[str]) -> bool:
    """Adresă utilă pentru matching: are număr și nu e placeholder („??", „nr. ?")."""
    if not adresa:
        return False
    if "?" in adresa:
        return False
    return bool(re.search(r"\d", adresa))


async def _find_existing_building(db, rec: dict) -> Optional[dict]:
    """1) match pe source_record_id (idempotent). 2) match PropManage prin adresă+coordonate."""
    sid = rec["source_record_id"]
    hit = await db.buildings.find_one({"context.external_sources.hartablocuri.source_record_id": sid})
    if hit:
        return hit
    # adrese placeholder („Strada ?? nr. ?") NU sunt chei de matching → bloc distinct
    if not _reliable_address(rec.get("adresa")):
        return None
    norm_addr = _norm(rec.get("adresa"))
    if not norm_addr:
        return None
    norm_name = _norm(rec.get("nume"))
    # (a) candidați indexați cu aceeași adresă normalizată
    async for b in db.buildings.find({"context.norm_address": norm_addr}):
        ctx = b.get("context") or {}
        cand_is_hb = bool((ctx.get("external_sources") or {}).get("hartablocuri"))
        blat, blng = ctx.get("lat"), ctx.get("lng")
        has_coords = isinstance(blat, (int, float)) and isinstance(blng, (int, float))
        near = has_coords and _haversine_m(blat, blng, rec["lat"], rec["lng"]) <= 60
        same_name = bool(norm_name) and _norm(b.get("name")) == norm_name
        # același nume + adresă → același bloc DOAR dacă și coordonatele sunt apropiate
        # (nume/adrese placeholder ex. „Bloc număr necunoscut" / „Strada ?? nr. X" pot repeta)
        if same_name and (near or not has_coords):
            return b
        if cand_is_hb:
            continue  # NU uni două blocuri HartaBlocuri distincte de la aceeași adresă
        # candidat PropManage (manual) la aceeași adresă → match cross-source
        if near:
            return b
        if not has_coords and same_name:
            return b
    # (b) buildings PropManage vechi fără norm_address (adresă brută egală, set mic)
    async for b in db.buildings.find({"context.external_sources.hartablocuri": {"$exists": False},
                                      "context.norm_address": {"$exists": False},
                                      "address": {"$exists": True}}):
        if _norm(b.get("address")) != norm_addr:
            continue
        ctx = b.get("context") or {}
        blat, blng = ctx.get("lat"), ctx.get("lng")
        has_coords = isinstance(blat, (int, float)) and isinstance(blng, (int, float))
        if has_coords:
            if _haversine_m(blat, blng, rec["lat"], rec["lng"]) <= 60:
                return b
        elif not norm_name or _norm(b.get("name")) == norm_name:
            return b
    return None


def _merge_context(existing_ctx: dict, rec: dict, ext: dict) -> tuple[dict, list]:
    """Merge non-destructiv. Returnează (context nou, listă conflicte)."""
    ctx = dict(existing_ctx or {})
    conflicts = list(ctx.get("conflicts") or [])
    ext_sources = dict(ctx.get("external_sources") or {})
    ext_sources["hartablocuri"] = ext
    ctx["external_sources"] = ext_sources

    for cfield, rkey in _CONTEXT_MAP.items():
        rval = rec.get(rkey)
        if rval in (None, ""):
            continue
        cur = ctx.get(cfield)
        if cur in (None, ""):
            ctx[cfield] = rval  # completează gol → non-destructiv
        elif str(cur) != str(rval):
            if not any(c.get("field") == cfield and c.get("hartablocuri_value") == rval for c in conflicts):
                conflicts.append({
                    "field": cfield, "propmanage_value": cur, "hartablocuri_value": rval,
                    "source": SOURCE_NAME, "status": "review", "detected_at": _now(),
                })
    if conflicts:
        ctx["conflicts"] = conflicts

    ctx.setdefault("building_type", "block")
    ctx.setdefault("source_type", "external_reference")
    if not ctx.get("source_name"):
        ctx["source_name"] = SOURCE_NAME
    ctx.setdefault("verification_status", "unverified")
    if rec.get("adresa"):
        ctx["norm_address"] = _norm(rec.get("adresa"))
    ctx["updated_at"] = _now()
    return ctx, conflicts


async def import_records(db, records: list[dict], batch_id: str, dry_run: bool = False) -> dict:
    stats = {"total": len(records), "imported": 0, "matched_existing": 0, "new_buildings": 0,
             "duplicates_updated": 0, "conflicts": 0, "errors": 0, "error_samples": []}
    for rec in records:
        try:
            existing = await _find_existing_building(db, rec)
            ext = build_external_source(rec, batch_id)
            if existing:
                had_hb = bool((existing.get("context") or {}).get("external_sources", {}).get("hartablocuri"))
                new_ctx, conflicts = _merge_context(existing.get("context") or {}, rec, ext)
                if not dry_run:
                    await db.buildings.update_one({"_id": existing["_id"]}, {"$set": {"context": new_ctx}})
                stats["imported"] += 1
                if had_hb:
                    stats["duplicates_updated"] += 1
                else:
                    stats["matched_existing"] += 1
                if conflicts:
                    stats["conflicts"] += 1
            else:
                new_ctx, _ = _merge_context({}, rec, ext)
                doc = {
                    "name": rec.get("nume") or "Bloc",
                    "address": rec.get("full_address") or rec.get("adresa"),
                    "city": rec.get("city"),
                    "context": new_ctx,
                    "source": "hartablocuri_import",
                    "import_batch_id": batch_id,
                    "created_at": _now(),
                    "created_by": None,
                    "created_by_name": SOURCE_NAME,
                }
                if not dry_run:
                    await db.buildings.insert_one(doc)
                stats["imported"] += 1
                stats["new_buildings"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            if len(stats["error_samples"]) < 5:
                stats["error_samples"].append(f"{rec.get('nume')}: {e}")
    return stats


async def run_import(file_path: str, limit: Optional[int] = None, dry_run: bool = False,
                     triggered_by: str = "cli") -> dict:
    from db import db
    batch_id = "batch_" + hashlib.md5(f"{file_path}{_now()}".encode()).hexdigest()[:16]
    records = parse_workbook(file_path, limit=limit)
    batch_doc = {
        "batch_id": batch_id, "source_name": SOURCE_NAME, "source_dataset": SOURCE_DATASET,
        "file": file_path.split("/")[-1], "total_records": len(records),
        "status": "running", "dry_run": dry_run, "triggered_by": triggered_by,
        "started_at": _now(),
    }
    if not dry_run:
        await db.buildings.create_index("context.external_sources.hartablocuri.source_record_id",
                                        sparse=True, background=True)
        await db.buildings.create_index("context.norm_address", sparse=True, background=True)
        await db.import_batches.insert_one(dict(batch_doc))
    stats = await import_records(db, records, batch_id, dry_run=dry_run)
    result = {**batch_doc, "status": "completed", "finished_at": _now(), **stats}
    if not dry_run:
        await db.import_batches.update_one({"batch_id": batch_id}, {"$set": {
            "status": "completed", "finished_at": result["finished_at"],
            "imported": stats["imported"], "matched_existing": stats["matched_existing"],
            "new_buildings": stats["new_buildings"], "duplicates_updated": stats["duplicates_updated"],
            "conflicts": stats["conflicts"], "errors": stats["errors"],
            "error_samples": stats["error_samples"],
        }})
    return result


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    res = asyncio.run(run_import(args.file, limit=args.limit, dry_run=args.dry_run))
    import json
    print(json.dumps({k: v for k, v in res.items() if k != "error_samples"}, indent=2, ensure_ascii=False))
    if res.get("error_samples"):
        print("ERROR SAMPLES:", res["error_samples"])


if __name__ == "__main__":
    _main()
