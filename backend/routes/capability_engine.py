"""Universal Capability Engine — Track B / Faza D1 (Design Partner Ecosystem).

Orice profesionist e descris prin CAPABILITĂȚI, nu profesii. Catalogul e DATE
(stocat în DB, seed idempotent versionat, editabil ulterior) — zero logică
hardcodată pe profesie. Include: matricea de responsabilitate standard
(LEAD/CO-PARTNER/SUPPORT/CONSULTANT), compatibilitate software, Compatibility
Score 0-100 căutabil și progresie data-driven pe 7 niveluri.
"""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.capability_engine")
router = APIRouter(prefix="/api", tags=["capability_engine"])

CATALOG_VERSION = 1
CAPABILITY_LEVELS = ["beginner", "intermediate", "professional", "expert"]
CAPABILITY_LEVEL_LABELS = {"beginner": "Începător", "intermediate": "Intermediar",
                           "professional": "Profesionist", "expert": "Expert"}
RESPONSIBILITY_LEVELS = {
    "LEAD": "Deține livrarea completă — calitate, comunicare, termene, livrabile",
    "CO_PARTNER": "Lucrează alături de un Lead — expertiză specializată, nu închide singur etapa",
    "SUPPORT": "Asistență tehnică pe task-uri specifice — fără responsabilitate de livrare finală",
    "CONSULTANT": "Doar recomandări — fără execuție, fără responsabilitate de livrare",
}

_P = "PropManage"


def _cap(cid, label, resp=None, reserved=False):
    return {"id": cid, "label": label, "reserved": reserved,
            "responsibility": resp or [["Profesionist", "LEAD"], [_P, "SUPPORT"]]}


CATALOG_PHASES = [
    {"id": "phase_1", "label": "Faza 1 — Consultanță & Evaluare", "capabilities": [
        _cap("consultation", "Consultanță"),
        _cap("measurements", "Măsurători"),
        _cap("technical_advice", "Consiliere tehnică"),
        _cap("technical_audit", "Audit tehnic", [[_P, "LEAD"], ["Profesionist", "SUPPORT"]], reserved=True),
    ]},
    {"id": "phase_2", "label": "Faza 2 — Modelare & Documentație", "capabilities": [
        _cap("modeling_3d", "Modelare 3D", [["Profesionist", "LEAD"], [_P, "SUPPORT"]]),
        _cap("bim", "BIM"),
        _cap("matterport_scan", "Scanare Matterport"),
        _cap("technical_drawings", "Desene tehnice"),
        _cap("visualization", "Vizualizare & Randări"),
        _cap("installation_mapping", "Cartografiere instalații",
             [[_P, "LEAD"], ["Inginer", "CO_PARTNER"], ["Designer", "SUPPORT"]], reserved=True),
        _cap("digital_twin_infrastructure", "Infrastructură Digital Twin",
             [[_P, "LEAD"], ["Designer", "CO_PARTNER"], ["Arhitect", "CO_PARTNER"]], reserved=True),
    ]},
    {"id": "phase_3", "label": "Faza 3 — Design & Specializări", "capabilities": [
        _cap("interior_architecture", "Arhitectură de interior"),
        _cap("interior_design", "Design interior"),
        _cap("moodboards", "Moodboard-uri"),
        _cap("furniture", "Mobilier"),
        _cap("lighting", "Iluminat"),
        _cap("materials", "Materiale"),
        _cap("decor", "Decor"),
        _cap("custom_furniture", "Mobilier la comandă"),
        _cap("kitchen_design", "Design bucătării"),
        _cap("bathroom_design", "Design băi"),
        _cap("commercial_design", "Design comercial"),
        _cap("office_design", "Design birouri"),
        _cap("retail_design", "Design retail"),
        _cap("themed_design", "Design tematic"),
        _cap("hospitality_design", "Design hospitality"),
        _cap("restaurant_design", "Design restaurante"),
        _cap("medical_design", "Design medical"),
        _cap("educational_design", "Design educațional"),
        _cap("children_spaces", "Spații pentru copii"),
        _cap("showroom_design", "Design showroom"),
    ]},
    {"id": "phase_4", "label": "Faza 4 — Implementare", "capabilities": [
        _cap("implementation_support", "Suport implementare",
             [["Project Manager", "LEAD"], ["Designer", "CO_PARTNER"], [_P, "CO_PARTNER"]]),
        _cap("site_visits", "Vizite pe șantier"),
        _cap("execution_supervision", "Supervizare execuție"),
        _cap("material_verification", "Verificare materiale"),
        _cap("designer_assistance", "Asistență de designer"),
        _cap("construction_management", "Management construcție", [[_P, "LEAD"]], reserved=True),
        _cap("quality_inspection", "Inspecție de calitate", [[_P, "LEAD"]], reserved=True),
        _cap("final_acceptance", "Recepție finală", [[_P, "LEAD"]], reserved=True),
    ]},
    {"id": "phase_5", "label": "Faza 5 — Evoluție & Întreținere", "capabilities": [
        _cap("future_updates", "Actualizări viitoare"),
        _cap("redesign", "Redesign"),
        _cap("furniture_changes", "Schimbări de mobilier"),
        _cap("style_evolution", "Evoluție de stil"),
        _cap("seasonal_updates", "Actualizări sezoniere"),
        _cap("house_health", "House Health", [[_P, "LEAD"], ["Profesionist", "CONSULTANT"]], reserved=True),
    ]},
]

CATALOG_SOFTWARE = [
    {"id": "sketchup", "label": "SketchUp", "tags": ["cad", "format_3d"]},
    {"id": "revit", "label": "Revit", "tags": ["bim", "twin"]},
    {"id": "archicad", "label": "ArchiCAD", "tags": ["bim", "twin"]},
    {"id": "autocad", "label": "AutoCAD", "tags": ["cad", "dwg"]},
    {"id": "3ds_max", "label": "3ds Max", "tags": ["render"]},
    {"id": "blender", "label": "Blender", "tags": ["render", "format_3d"]},
    {"id": "twinmotion", "label": "Twinmotion", "tags": ["render"]},
    {"id": "enscape", "label": "Enscape", "tags": ["render"]},
    {"id": "lumion", "label": "Lumion", "tags": ["render"]},
    {"id": "rhino", "label": "Rhino", "tags": ["cad", "format_3d"]},
    {"id": "vectorworks", "label": "Vectorworks", "tags": ["bim"]},
    {"id": "cinema4d", "label": "Cinema 4D", "tags": ["render"]},
    {"id": "photoshop", "label": "Photoshop", "tags": ["gfx"]},
    {"id": "illustrator", "label": "Illustrator", "tags": ["gfx"]},
    {"id": "indesign", "label": "InDesign", "tags": ["gfx"]},
    {"id": "matterport", "label": "Matterport", "tags": ["matterport", "twin"]},
    {"id": "reality_capture", "label": "Reality Capture", "tags": ["point_cloud", "twin"]},
    {"id": "point_cloud_tools", "label": "Point Cloud", "tags": ["point_cloud", "twin"]},
    {"id": "fmt_dwg", "label": "DWG", "tags": ["dwg"]},
    {"id": "fmt_dxf", "label": "DXF", "tags": ["dwg"]},
    {"id": "fmt_ifc", "label": "IFC", "tags": ["ifc", "bim", "twin"]},
    {"id": "fmt_obj", "label": "OBJ", "tags": ["format_3d"]},
    {"id": "fmt_fbx", "label": "FBX", "tags": ["format_3d"]},
    {"id": "fmt_gltf", "label": "GLTF", "tags": ["format_3d", "twin"]},
    {"id": "fmt_step", "label": "STEP", "tags": ["format_3d"]},
    {"id": "fmt_rvt", "label": "RVT", "tags": ["bim"]},
    {"id": "fmt_skp", "label": "SKP", "tags": ["format_3d"]},
]

SCORE_COMPONENTS = [
    {"id": "bim_ready", "label": "BIM Ready", "points": 20, "tags": ["bim"]},
    {"id": "digital_twin_ready", "label": "Digital Twin Ready", "points": 15, "tags": ["twin"]},
    {"id": "ifc_compatible", "label": "IFC Compatible", "points": 15, "tags": ["ifc"]},
    {"id": "dwg_compatible", "label": "DWG/CAD Compatible", "points": 10, "tags": ["dwg", "cad"]},
    {"id": "matterport_ready", "label": "Matterport Ready", "points": 10, "tags": ["matterport"]},
    {"id": "point_cloud_ready", "label": "Point Cloud Ready", "points": 10, "tags": ["point_cloud"]},
    {"id": "render_3d", "label": "3D & Vizualizare", "points": 10, "tags": ["render", "format_3d"]},
]
VERIFIED_POINTS = 10

LANGUAGE_OPTIONS = ["Română", "Engleză", "Maghiară", "Germană", "Franceză", "Italiană", "Spaniolă"]


async def _get_catalog() -> dict:
    doc = await db.capability_catalog.find_one({"_id": "catalog"})
    if not doc or int(doc.get("version") or 0) < CATALOG_VERSION:
        doc = {"_id": "catalog", "version": CATALOG_VERSION, "phases": CATALOG_PHASES,
               "software": CATALOG_SOFTWARE, "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.capability_catalog.replace_one({"_id": "catalog"}, doc, upsert=True)
    return doc


def _catalog_maps(catalog: dict):
    caps = {c["id"]: c for ph in catalog["phases"] for c in ph["capabilities"]}
    soft = {s["id"]: s for s in catalog["software"]}
    return caps, soft


def compute_compatibility(software_ids: list, verified: bool, catalog: dict) -> dict:
    _, soft = _catalog_maps(catalog)
    tags = set()
    for sid in software_ids or []:
        tags.update(soft.get(sid, {}).get("tags") or [])
    badges, score = [], 0
    for c in SCORE_COMPONENTS:
        earned = bool(tags.intersection(c["tags"]))
        if earned:
            score += c["points"]
        badges.append({"id": c["id"], "label": c["label"], "points": c["points"], "earned": earned})
    badges.append({"id": "propmanage_verified", "label": "PropManage Verified",
                   "points": VERIFIED_POINTS, "earned": bool(verified)})
    if verified:
        score += VERIFIED_POINTS
    return {"score": min(score, 100), "badges": badges,
            "computed_at": datetime.now(timezone.utc).isoformat()}


async def _progression(u: dict) -> dict:
    uid = str(u["_id"])
    completed = await db.requests.count_documents({"specialist_id": uid, "status": "confirmed"})
    disputes = await db.requests.count_documents({"specialist_id": uid, "disputed": True})
    portfolio_n = await db.portfolio.count_documents({"specialist_id": uid})
    m = {
        "verified": bool(u.get("verified")), "tier": u.get("tier") or "ENTRY",
        "rating": float(u.get("rating") or 0), "reviews": int(u.get("reviews_count") or 0),
        "completed": completed, "disputes": disputes, "portfolio": portfolio_n,
        "caps": len(u.get("capabilities") or []),
        "comp": int(((u.get("compatibility") or {}).get("score")) or 0),
    }
    ladder = [
        (1, "Înregistrat", []),
        (2, "Verificat", [("Cont verificat de platformă", m["verified"])]),
        (3, "De încredere", [("≥3 recenzii", m["reviews"] >= 3), ("Rating ≥4.0", m["rating"] >= 4.0),
                             ("≥3 lucrări finalizate", m["completed"] >= 3)]),
        (4, "Premium", [("Tier PREMIUM sau ≥10 lucrări cu rating ≥4.5",
                         m["tier"] == "PREMIUM" or (m["completed"] >= 10 and m["rating"] >= 4.5))]),
        (5, "Expert", [("≥25 lucrări finalizate", m["completed"] >= 25),
                       ("≥5 capabilități definite", m["caps"] >= 5),
                       ("Compatibilitate ≥50", m["comp"] >= 50)]),
        (6, "Master Partner", [("≥50 lucrări finalizate", m["completed"] >= 50), ("Rating ≥4.7", m["rating"] >= 4.7)]),
        (7, "PropManage Certified", [("Compatibilitate ≥80", m["comp"] >= 80),
                                     ("≥5 proiecte în portofoliu", m["portfolio"] >= 5),
                                     ("Zero dispute", m["disputes"] == 0)]),
    ]
    level, name, next_req = 1, "Înregistrat", []
    for lvl, lbl, checks in ladder:
        if all(ok for _, ok in checks):
            level, name = lvl, lbl
        else:
            next_req = [{"label": t, "met": ok} for t, ok in checks]
            break
    return {"level": level, "name": name, "max_level": 7,
            "next_level": min(level + 1, 7) if level < 7 else None,
            "next_requirements": next_req, "metrics": m}


def _own_payload(u: dict, catalog: dict) -> dict:
    caps_map, soft_map = _catalog_maps(catalog)
    caps = []
    for c in u.get("capabilities") or []:
        meta = caps_map.get(c.get("id"))
        if meta:
            caps.append({"id": c["id"], "label": meta["label"], "level": c.get("level"),
                         "level_label": CAPABILITY_LEVEL_LABELS.get(c.get("level"), c.get("level"))})
    software = [{"id": s, "label": soft_map[s]["label"]} for s in (u.get("software") or []) if s in soft_map]
    return {"capabilities": caps, "software": software, "languages": u.get("languages") or [],
            "compatibility": u.get("compatibility") or compute_compatibility([], bool(u.get("verified")), catalog)}


# ── Endpoints ────────────────────────────────────────────────────────────────
@router.get("/capabilities/catalog")
async def capability_catalog():
    catalog = await _get_catalog()
    return {"version": catalog["version"], "phases": catalog["phases"], "software": catalog["software"],
            "levels": [{"id": k, "label": v} for k, v in CAPABILITY_LEVEL_LABELS.items()],
            "responsibility_levels": [{"id": k, "label": v} for k, v in RESPONSIBILITY_LEVELS.items()],
            "languages": LANGUAGE_OPTIONS,
            "score_components": SCORE_COMPONENTS + [{"id": "propmanage_verified", "label": "PropManage Verified",
                                                     "points": VERIFIED_POINTS}]}


@router.get("/capabilities/responsibility-matrix")
async def responsibility_matrix():
    """Matricea standard de responsabilitate — clientul știe mereu cine răspunde de fiecare etapă."""
    catalog = await _get_catalog()
    rows = []
    for ph in catalog["phases"]:
        for c in ph["capabilities"]:
            rows.append({"capability": c["id"], "label": c["label"], "phase": ph["label"],
                         "reserved": c["reserved"],
                         "actors": [{"actor": a, "level": lv, "level_label": RESPONSIBILITY_LEVELS.get(lv, lv)}
                                    for a, lv in c["responsibility"]]})
    return {"rows": rows, "levels": RESPONSIBILITY_LEVELS}


@router.get("/professional/capabilities")
async def my_capabilities(user: dict = Depends(require_role("specialist"))):
    catalog = await _get_catalog()
    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    payload = _own_payload(u, catalog)
    payload["progression"] = await _progression(u)
    return payload


@router.put("/professional/capabilities")
async def set_capabilities(body: dict = Body(...), user: dict = Depends(require_role("specialist"))):
    catalog = await _get_catalog()
    caps_map, soft_map = _catalog_maps(catalog)

    capabilities = []
    for c in (body.get("capabilities") or [])[:60]:
        cid, level = str(c.get("id") or ""), str(c.get("level") or "professional")
        meta = caps_map.get(cid)
        if not meta:
            raise HTTPException(400, f"Capabilitate necunoscută: {cid}")
        if meta["reserved"]:
            raise HTTPException(400, f"'{meta['label']}' este responsabilitatea PropManage și nu poate fi revendicată")
        if level not in CAPABILITY_LEVELS:
            raise HTTPException(400, f"Nivel invalid: {level}")
        capabilities.append({"id": cid, "level": level})

    software = []
    for sid in (body.get("software") or [])[:40]:
        if str(sid) not in soft_map:
            raise HTTPException(400, f"Software necunoscut: {sid}")
        software.append(str(sid))

    languages = [str(l)[:30] for l in (body.get("languages") or [])[:10]]

    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    compatibility = compute_compatibility(software, bool(u.get("verified")), catalog)
    await db.users.update_one({"_id": u["_id"]}, {"$set": {
        "capabilities": capabilities, "software": software, "languages": languages,
        "compatibility": compatibility,
        "capabilities_updated_at": datetime.now(timezone.utc).isoformat(),
    }})
    u.update({"capabilities": capabilities, "software": software,
              "languages": languages, "compatibility": compatibility})
    payload = _own_payload(u, catalog)
    payload["progression"] = await _progression(u)
    payload["message"] = "Capabilitățile au fost salvate"
    return payload


@router.get("/specialists/{spec_id}/capabilities")
async def public_capabilities(spec_id: str):
    try:
        u = await db.users.find_one({"_id": ObjectId(spec_id), "role": "specialist"})
    except Exception:
        raise HTTPException(404, "Specialist inexistent")
    if not u:
        raise HTTPException(404, "Specialist inexistent")
    catalog = await _get_catalog()
    caps_map, _ = _catalog_maps(catalog)
    phase_of = {c["id"]: ph["label"] for ph in catalog["phases"] for c in ph["capabilities"]}
    payload = _own_payload(u, catalog)
    for c in payload["capabilities"]:
        c["phase"] = phase_of.get(c["id"], "")
    payload["progression"] = await _progression(u)
    payload["progression"].pop("metrics", None)
    return payload


@router.get("/capabilities/find")
async def find_professionals(capability: str = "", software: str = "", min_score: int = 0, limit: int = 20):
    """Căutare pe capabilități + Compatibility Score (fundația AI Matching — Best Match, nu Nearest Match)."""
    q = {"role": "specialist"}
    if capability:
        q["capabilities.id"] = capability
    if software:
        q["software"] = software
    if min_score:
        q["compatibility.score"] = {"$gte": max(0, min(int(min_score), 100))}
    rows = await db.users.find(
        q, {"name": 1, "specialty": 1, "verified": 1, "tier": 1, "rating": 1,
            "reviews_count": 1, "compatibility.score": 1, "capabilities": 1}
    ).sort([("compatibility.score", -1), ("rating", -1)]).to_list(max(1, min(limit, 50)))
    return {"results": [{
        "id": str(r["_id"]), "name": r.get("name"), "specialty": r.get("specialty"),
        "verified": bool(r.get("verified")), "tier": r.get("tier"),
        "rating": r.get("rating"), "reviews_count": r.get("reviews_count") or 0,
        "compatibility_score": ((r.get("compatibility") or {}).get("score")) or 0,
        "capabilities_count": len(r.get("capabilities") or []),
    } for r in rows], "count": len(rows)}
