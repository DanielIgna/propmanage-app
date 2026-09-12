"""GI-5P Sprint 1 — Property Intelligence Engine (Board approved, spec frozen).

Maturity Score L0–L5 + Registru Active + Predictive Maintenance actuarial (FĂRĂ ML).
Trust Model (Directiva 015): provenance-first, intervale (No Fake Precision), audit-first CTA.
Zero refactor — extinde Value Loop / Revenue Hunter existente.
"""
import logging
import math
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from db import db

logger = logging.getLogger("propmanage.property_intelligence")

LIBRARY_VERSION = "2026.06-v1"

# Bibliotecă actuarială statică, versionată — cele 4 active majore (scope frozen Sprint 1)
ASSET_LIBRARY = {
    "centrala_termica": {
        "label": "Centrală termică",
        "lifespan_years": (12, 15),
        "service_interval_months": 12,
        "replacement_cost_ron": (8000, 12000),
        "work_categories": {"hvac", "clima", "instalatii", "plumbing"},
    },
    "tablou_electric": {
        "label": "Tablou electric",
        "lifespan_years": (25, 30),
        "service_interval_months": 60,
        "replacement_cost_ron": (2500, 4500),
        "work_categories": {"electric", "electricity"},
    },
    "acoperis": {
        "label": "Acoperiș",
        "lifespan_years": (30, 50),
        "service_interval_months": 24,
        "replacement_cost_ron": (30000, 60000),
        "work_categories": {"roofing"},
    },
    "termopane": {
        "label": "Termopane",
        "lifespan_years": (20, 30),
        "service_interval_months": 24,
        "replacement_cost_ron": (12000, 25000),
        "work_categories": {"termopane"},
    },
}

# Directiva 015 — niveluri de încredere oficiale
CONFIDENCE_LABELS = {
    "verified": "Verificat",
    "professional_audit": "Audit profesional",
    "official_document": "Document oficial",
    "owner_declared": "Declarat de proprietar",
    "ai_estimated": "Estimat AI",
    "unknown": "Necunoscut",
}
CONFIDENCE_WIDEN = {"verified": 1.0, "professional_audit": 1.0, "official_document": 1.1,
                    "owner_declared": 1.3, "ai_estimated": 1.5}
WEAK_CONFIDENCE = {"owner_declared", "ai_estimated", "unknown"}

MATURITY_LABELS = ["Înregistrată", "Identificată", "Documentată", "Activă", "Monitorizată", "Predictivă"]

# Fiecare treaptă lipsă = ofertă comercială (Directiva 014: categorii + Audit First)
OFFERS = {
    1: {"key": "identity", "title": "Completează identitatea casei",
        "benefit": "Adresa și detaliile de bază deblochează scorurile corecte ale Twin-ului.",
        "category": "documentation", "cta": "edit_property", "cta_label": "Completează detaliile"},
    2: {"key": "audit", "title": "Programează Audit Tehnic",
        "benefit": "Auditul documentează starea reală a casei — urci la L2 și valoarea documentată (PVI) crește imediat.",
        "category": "technical", "cta": "audit", "cta_label": "Programează Audit Tehnic"},
    3: {"key": "activity", "title": "Ține Twin-ul viu",
        "benefit": "O lucrare sau un eveniment documentat în ultimele 12 luni menține istoricul casei viu.",
        "category": "maintenance", "cta": "wizard", "cta_label": "Creează o cerere"},
    4: {"key": "audit", "title": "Reînnoiește Auditul Tehnic",
        "benefit": "Un audit mai recent de 24 de luni menține monitorizarea activă a casei.",
        "category": "technical", "cta": "audit", "cta_label": "Programează Audit Tehnic"},
    5: {"key": "assets", "title": "Înregistrează activele majore",
        "benefit": "Centrală, tablou electric, acoperiș, termopane — cu ele Twin-ul devine predictiv.",
        "category": "documentation", "cta": "assets", "cta_label": "Adaugă activele"},
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fmt_ron(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


# ============================================================================
# PREDICTIVE MAINTENANCE — metoda actuarială (bibliotecă × vârstă reală × modulatori)
# ============================================================================
def _serviced_recently(asset: dict, reqs: list) -> bool:
    """Modulator: lucrare confirmată în categoria activului în ultimii 3 ani = îngrijire dovedită."""
    cats = ASSET_LIBRARY.get(asset.get("asset_type"), {}).get("work_categories") or set()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * 3)).isoformat()
    return any(r.get("status") == "confirmed" and (r.get("confirmed_at") or "") >= cutoff
               and (r.get("category") or "").lower() in cats for r in reqs)


def compute_eol(asset: dict, serviced_recently: bool = False) -> dict:
    """EOL determinist, cu interval (No Fake Precision) — predicția e recomandare, nu fapt."""
    spec = ASSET_LIBRARY.get(asset.get("asset_type")) or {}
    conf = asset.get("confidence") or "unknown"
    year = asset.get("installed_year")
    base = {
        "asset_type": asset.get("asset_type"),
        "label": asset.get("label") or spec.get("label"),
        "estimated": True,
        "confidence": conf,
        "confidence_label": CONFIDENCE_LABELS.get(conf, conf),
        "library_version": LIBRARY_VERSION,
        "needs_audit": conf in WEAK_CONFIDENCE,
    }
    if not year or conf == "unknown" or not spec:
        return {**base, "status": "hypothesis", "commercial_priority": 3,
                "remaining_label": "Ipoteză — cere audit", "cost_label": None,
                "reason": "Nu cunoaștem vârsta reală sau starea activului.",
                "recommended_action": "Programează Audit Tehnic — confirmă starea reală înainte de orice decizie."}

    age = max(datetime.now(timezone.utc).year - int(year), 0)
    lo, hi = spec["lifespan_years"]
    rem_lo, rem_hi = lo - age, hi - age
    if serviced_recently:
        rem_lo, rem_hi = rem_lo + 1, rem_hi + 1
    # Directiva 015: încredere slabă → interval mai LAT, niciodată precizie falsă
    widen = CONFIDENCE_WIDEN.get(conf, 1.5)
    mid = (rem_lo + rem_hi) / 2
    half = max((rem_hi - rem_lo) / 2 * widen, 1.0)
    rem_lo, rem_hi = math.floor(mid - half), math.ceil(mid + half)

    if rem_hi <= 0:
        status, priority = "overdue", 5
    elif rem_lo <= 2:
        status, priority = "attention", 4
    elif rem_lo <= 5:
        status, priority = "monitor", 2
    else:
        status, priority = "ok", 1

    c_lo, c_hi = spec["replacement_cost_ron"]
    remaining_label = ("Peste durata de referință" if status == "overdue"
                       else f"≈ {max(rem_lo, 0)}–{max(rem_hi, 1)} ani")
    reason = (f"Bibliotecă actuarială {LIBRARY_VERSION}: durată de referință {lo}–{hi} ani, "
              f"vârstă reală ≈ {age} ani"
              + (", întreținere recentă dovedită" if serviced_recently else ""))
    if base["needs_audit"]:
        action = "Programează Audit Tehnic — confirmă starea reală înainte de orice decizie."
    elif status == "overdue":
        action = "Planifică înlocuirea — cere oferte în marketplace."
    elif status == "attention":
        action = "Planifică din timp înlocuirea sau o revizie majoră."
    elif status == "monitor":
        action = "Programează revizia periodică."
    else:
        action = "Nicio acțiune necesară acum."
    return {**base, "status": status, "commercial_priority": priority, "age_years": age,
            "remaining_years": {"min": rem_lo, "max": rem_hi},
            "remaining_label": remaining_label,
            "cost_label": f"≈ {_fmt_ron(c_lo)}–{_fmt_ron(c_hi)} RON",
            "reason": reason, "recommended_action": action}


async def _confirmed_reqs(prop_id: str) -> list:
    return await db.requests.find(
        {"property_id": prop_id, "status": "confirmed"},
        {"category": 1, "status": 1, "confirmed_at": 1}).to_list(200)


async def asset_slots(prop_id: str) -> list:
    """Cele 4 sloturi de active majore — înregistrate sau goale, fiecare cu EOL calculat."""
    assets = {a.get("asset_type"): a for a in await db.property_assets.find(
        {"property_id": prop_id, "status": "active"}).to_list(20)}
    reqs = await _confirmed_reqs(prop_id)
    slots = []
    for atype, spec in ASSET_LIBRARY.items():
        a = assets.get(atype)
        slot = {"asset_type": atype, "label": spec["label"],
                "lifespan_label": f"{spec['lifespan_years'][0]}–{spec['lifespan_years'][1]} ani durată de referință"}
        if a:
            slot["asset"] = {k: a.get(k) for k in ("id", "installed_year", "source", "confidence",
                                                   "verification_status", "last_updated", "updated_by",
                                                   "notes", "created_at")}
            slot["asset"]["confidence_label"] = CONFIDENCE_LABELS.get(a.get("confidence"), a.get("confidence"))
            slot["eol"] = compute_eol(a, _serviced_recently(a, reqs))
        else:
            slot["asset"] = None
            slot["eol"] = None
        slots.append(slot)
    return slots


async def predictions(prop_id: str) -> list:
    reqs = await _confirmed_reqs(prop_id)
    out = []
    for a in await db.property_assets.find({"property_id": prop_id, "status": "active"}).to_list(20):
        if a.get("asset_type") in ASSET_LIBRARY:
            out.append(compute_eol(a, _serviced_recently(a, reqs)))
    return out


async def detect_predictive_candidates(prop_id: str, reqs: list) -> list:
    """Detector Revenue Hunter: active aproape de EOL → oportunități comerciale (Directiva 014).

    Încredere slabă → Audit Tehnic (Audit First / Customer Trust).
    Încredere solidă → înlocuire planificată prin marketplace.
    """
    assets = await db.property_assets.find({"property_id": prop_id, "status": "active"}).to_list(20)
    out = []
    for a in assets:
        spec = ASSET_LIBRARY.get(a.get("asset_type"))
        if not spec:
            continue
        eol = compute_eol(a, _serviced_recently(a, reqs))
        if eol["status"] not in ("overdue", "attention"):
            continue
        label = eol["label"]
        if eol["needs_audit"]:
            out.append({
                "service": "audit_tehnic", "template": "audit_tehnic",
                "value": 800.0, "confidence": 0.8,
                "title": f"Verifică starea reală: {label}",
                "benefit": (f"{label} se apropie de finalul duratei de referință "
                            f"({eol['remaining_label']} — estimat, sursă: {eol['confidence_label']}). "
                            "Un audit tehnic confirmă starea reală înainte de orice decizie."),
                "category": "technical", "commercial_priority": eol["commercial_priority"],
                "commercial_domains": ["technical"],
            })
        else:
            c_lo, c_hi = spec["replacement_cost_ron"]
            out.append({
                "service": f"predictive_{a['asset_type']}", "template": "predictive_maintenance",
                "value": round((c_lo + c_hi) / 2, 2), "confidence": 0.85,
                "title": f"{label}: planifică înlocuirea din timp",
                "benefit": (f"Durată rămasă {eol['remaining_label']} (estimat, {eol['confidence_label']}). "
                            f"Înlocuire planificată {eol['cost_label']} — costuri mai mici decât o avarie."),
                "category": "technical" if eol["status"] == "overdue" else "maintenance",
                "commercial_priority": eol["commercial_priority"],
                "commercial_domains": ["technical"],
            })
    return out


# ============================================================================
# DIGITAL TWIN MATURITY SCORE — L0-L5, criterii binare cumulative
# ============================================================================
async def compute_maturity(prop: dict) -> dict:
    prop_id = str(prop["_id"])
    identity_ok = bool(prop.get("address")) and bool(prop.get("rooms") or prop.get("surface"))
    pvi_score = (prop.get("pvi") or {}).get("score")
    if pvi_score is None:
        from value_loop import refresh_pvi
        pvi_score = (await refresh_pvi(prop_id, trigger="maturity"))["score"]
    now = datetime.now(timezone.utc)
    cutoff_12m = (now - timedelta(days=365)).isoformat()
    cutoff_24m = (now - timedelta(days=730)).isoformat()
    alive = await db.activity_events.count_documents(
        {"property_id": prop_id, "created_at": {"$gte": cutoff_12m}}) > 0
    if not alive:
        alive = await db.requests.count_documents(
            {"property_id": prop_id, "confirmed_at": {"$gte": cutoff_12m}}) > 0
    audited = await db.hh_evaluations.count_documents(
        {"property_id": prop_id, "created_at": {"$gte": cutoff_24m}}) > 0
    assets = await db.property_assets.find({"property_id": prop_id, "status": "active"}).to_list(20)
    predictable = {a.get("asset_type") for a in assets
                   if a.get("installed_year") and (a.get("confidence") or "unknown") != "unknown"}
    predictive_ok = all(t in predictable for t in ASSET_LIBRARY)

    criteria = [
        {"level": 1, "label": MATURITY_LABELS[1], "ok": identity_ok,
         "hint": "Adresă + camere/suprafață completate"},
        {"level": 2, "label": MATURITY_LABELS[2], "ok": pvi_score >= 40,
         "hint": f"PVI ≥ 40 (acum {pvi_score})"},
        {"level": 3, "label": MATURITY_LABELS[3], "ok": alive,
         "hint": "Cel puțin un eveniment în ultimele 12 luni"},
        {"level": 4, "label": MATURITY_LABELS[4], "ok": audited,
         "hint": "Audit tehnic în ultimele 24 de luni"},
        {"level": 5, "label": MATURITY_LABELS[5], "ok": predictive_ok,
         "hint": f"Active majore înregistrate: {len(predictable)}/{len(ASSET_LIBRARY)}"},
    ]
    level = 0
    for c in criteria:
        if c["ok"]:
            level = c["level"]
        else:
            break
    missing = next((c for c in criteria if not c["ok"]), None)
    audit_first = level < 2  # Directiva 014 — Audit First Rule
    next_step = None
    if missing:
        offer = OFFERS[missing["level"]]
        if audit_first and offer["cta"] != "audit":
            next_step = {**OFFERS[2], "secondary_hint": missing["hint"]}
        else:
            next_step = dict(offer)
        next_step["missing_level"] = missing["level"]
    return {"property_id": prop_id, "level": level, "level_label": MATURITY_LABELS[level],
            "levels": MATURITY_LABELS, "criteria": criteria, "next_step": next_step,
            "audit_first": audit_first, "pvi_score": pvi_score, "computed_at": _now()}


async def refresh_maturity(prop: dict) -> dict:
    """Recalculează Maturity, persistă pe proprietate + istoric la schimbare, emite eveniment."""
    m = await compute_maturity(prop)
    prop_id = m["property_id"]
    prev = (prop.get("maturity") or {}).get("level")
    stored = {"level": m["level"], "level_label": m["level_label"], "computed_at": m["computed_at"]}
    await db.properties.update_one({"_id": ObjectId(prop_id)}, {"$set": {"maturity": stored}})
    if prev != m["level"]:
        await db.property_maturity_history.insert_one(
            {"property_id": prop_id, "from_level": prev, "to_level": m["level"], "ts": m["computed_at"]})
        try:
            from event_bus import emit
            await emit("twin.maturity_changed", property_id=prop_id,
                       payload={"from": prev, "to": m["level"], "label": m["level_label"]})
        except Exception:  # noqa: BLE001
            pass
    return m


# ============================================================================
# GI-5P SPRINT 2 — DNA v2 (atribute cu provenance), Health Decay, Risk Engine
# ============================================================================
DNA_ATTRIBUTES = {
    "year_built": {"label": "Anul construcției", "type": "int", "min": 1800, "max": 2100},
    "structure_type": {"label": "Tip structură", "type": "enum",
                       "options": ["beton", "caramida", "bca", "lemn", "metal", "mixt"]},
    "insulation_type": {"label": "Izolație termică", "type": "enum",
                        "options": ["polistiren", "vata_minerala", "vata_bazaltica", "neizolat", "alta"]},
    "roof_type": {"label": "Tip acoperiș", "type": "enum",
                  "options": ["tigla", "tabla", "membrana", "sindrila", "terasa", "alta"]},
    "heating_type": {"label": "Tip încălzire", "type": "enum",
                     "options": ["centrala_gaz", "centrala_electrica", "termoficare", "pompa_caldura", "lemne", "alta"]},
}

HEALTH_FIELDS = ("structure_health", "utilities_health", "documents_health")
DECAY_FLOOR = 25
DECAY_GRACE_DAYS = 183  # 6 luni fără eveniment dovedit → începe îngrijirea


def _to_dt(v):
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


async def apply_health_decay(prop: dict) -> dict | None:
    """Decay temporal determinist: −1 pct/component/lună după 6 luni fără întreținere dovedită.

    Idempotent lunar. Podea 25. Creșterea rămâne DOAR prin evenimente dovedite (value_loop).
    """
    prop_id = str(prop["_id"])
    if not any(isinstance(prop.get(f), (int, float)) for f in HEALTH_FIELDS):
        return None
    now = datetime.now(timezone.utc)
    decay_state = prop.get("health_decay") or {}
    last_applied = _to_dt(decay_state.get("last_applied"))
    if last_applied and (now - last_applied).days < 28:
        return None
    last_event = _to_dt(prop.get("last_enriched_at"))
    ev = await db.hh_evaluations.find_one({"property_id": prop_id}, sort=[("created_at", -1)])
    if ev:
        ev_dt = _to_dt(ev.get("created_at"))
        if ev_dt and (not last_event or ev_dt > last_event):
            last_event = ev_dt
    if not last_event:
        last_event = _to_dt(prop.get("created_at"))
    if last_event and (now - last_event).days < DECAY_GRACE_DAYS:
        return None

    sets = {}
    for f in HEALTH_FIELDS:
        v = prop.get(f)
        if isinstance(v, (int, float)) and v > DECAY_FLOOR:
            sets[f] = max(DECAY_FLOOR, round(v - 1))
    if not sets:
        return None
    merged = {**prop, **sets}
    parts = [merged.get(f) for f in HEALTH_FIELDS if isinstance(merged.get(f), (int, float))]
    sets["health_score"] = min(100, round(sum(parts) / len(parts)))
    sets["health_decay"] = {"last_applied": _now(),
                            "points_lost": (decay_state.get("points_lost") or 0) + len([f for f in sets if f in HEALTH_FIELDS])}
    await db.properties.update_one({"_id": ObjectId(prop_id)}, {"$set": sets})
    await db.health_history.insert_one({
        "property_id": prop_id, "ts": _now(), "reason": "decay",
        "components": {f: sets[f] for f in HEALTH_FIELDS if f in sets},
        "health_score": sets["health_score"],
        "note": "Îngrijire: fără eveniment de întreținere dovedit în ultimele 6 luni",
    })
    try:
        from event_bus import emit
        await emit("health.decayed", property_id=prop_id,
                   payload={"health_score": sets["health_score"], "trigger": "decay"})
    except Exception:  # noqa: BLE001
        pass
    return sets


RISK_CATEGORY_LABELS = {"technical": "Tehnic", "maintenance": "Întreținere", "legal": "Juridic & Documente"}


async def compute_risks(prop: dict) -> list:
    """Risc = probabilitate × impact, determinist, cu DOVEZI + mitigare comercială (Directiva 014)."""
    prop_id = str(prop["_id"])
    risks = []
    reqs = await _confirmed_reqs(prop_id)

    # 1. TEHNIC — active la finalul duratei de referință (reuse Sprint 1)
    for a in await db.property_assets.find({"property_id": prop_id, "status": "active"}).to_list(20):
        if a.get("asset_type") not in ASSET_LIBRARY:
            continue
        eol = compute_eol(a, _serviced_recently(a, reqs))
        if eol["status"] not in ("overdue", "attention"):
            continue
        high = eol["status"] == "overdue"
        risks.append({
            "id": f"tech_{a['asset_type']}", "category": "technical",
            "category_label": RISK_CATEGORY_LABELS["technical"],
            "title": (f"{eol['label']}: risc de avarie" if high
                      else f"{eol['label']}: aproape de finalul duratei de viață"),
            "probability": "ridicată" if high else "medie",
            "impact_label": eol.get("cost_label") or "necunoscut fără verificare",
            "score": 85 if high else 60,
            "estimated": True, "confidence": eol["confidence"],
            "confidence_label": eol["confidence_label"],
            "evidence": [eol["reason"], f"Durată rămasă: {eol['remaining_label']}"],
            "mitigation": {"cta": "audit" if eol["needs_audit"] else "wizard",
                           "label": ("Programează Audit Tehnic" if eol["needs_audit"]
                                     else "Cere oferte de înlocuire")},
        })

    # 2. ÎNTREȚINERE — audit vechi / decay activ
    cutoff_24m = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()
    audited = await db.hh_evaluations.count_documents(
        {"property_id": prop_id, "created_at": {"$gte": cutoff_24m}}) > 0
    if not audited:
        risks.append({
            "id": "maint_audit", "category": "maintenance",
            "category_label": RISK_CATEGORY_LABELS["maintenance"],
            "title": "Stare tehnică neverificată de un profesionist",
            "probability": "medie", "impact_label": "necunoscut fără verificare",
            "score": 50, "estimated": True, "confidence": "unknown",
            "confidence_label": CONFIDENCE_LABELS["unknown"],
            "evidence": ["Fără audit tehnic în ultimele 24 de luni"],
            "mitigation": {"cta": "audit", "label": "Programează Audit Tehnic"},
        })
    decay_state = prop.get("health_decay") or {}
    if decay_state.get("points_lost"):
        risks.append({
            "id": "maint_decay", "category": "maintenance",
            "category_label": RISK_CATEGORY_LABELS["maintenance"],
            "title": "Casa are nevoie de îngrijire",
            "probability": "medie", "impact_label": "sănătatea documentată scade lent",
            "score": 40, "estimated": True, "confidence": "verified",
            "confidence_label": CONFIDENCE_LABELS["verified"],
            "evidence": [f"Sănătatea a scăzut cu {decay_state['points_lost']} puncte — "
                         "fără întreținere dovedită în ultimele 6 luni"],
            "mitigation": {"cta": "wizard", "label": "Programează o lucrare sau o revizie"},
        })

    # 3. JURIDIC & DOCUMENTE
    identity_ok = bool(prop.get("address")) and bool(prop.get("rooms") or prop.get("surface"))
    if not identity_ok:
        risks.append({
            "id": "legal_identity", "category": "legal",
            "category_label": RISK_CATEGORY_LABELS["legal"],
            "title": "Identitatea proprietății este incompletă",
            "probability": "certă", "impact_label": "scoruri și oferte imprecise",
            "score": 45, "estimated": False, "confidence": "verified",
            "confidence_label": CONFIDENCE_LABELS["verified"],
            "evidence": ["Lipsesc adresa sau camerele/suprafața"],
            "mitigation": {"cta": "edit_property", "label": "Completează detaliile"},
        })
    dh = prop.get("documents_health")
    if isinstance(dh, (int, float)) and dh < 50:
        risks.append({
            "id": "legal_docs", "category": "legal",
            "category_label": RISK_CATEGORY_LABELS["legal"],
            "title": "Documentație subțire pentru vânzare sau asigurare",
            "probability": "medie", "impact_label": "valoare percepută mai mică la tranzacționare",
            "score": 42, "estimated": True, "confidence": "verified",
            "confidence_label": CONFIDENCE_LABELS["verified"],
            "evidence": [f"Sănătatea documentară e {round(dh)}/100 — puține dovezi arhivate"],
            "mitigation": {"cta": "audit", "label": "Programează Audit Tehnic (documentează starea)"},
        })

    risks.sort(key=lambda r: -r["score"])
    return risks


async def refresh_risk_profile(prop: dict, risks: list | None = None) -> dict:
    if risks is None:
        risks = await compute_risks(prop)
    profile = {"total": len(risks),
               "max_score": max((r["score"] for r in risks), default=0),
               "top_category": risks[0]["category"] if risks else None,
               "top_title": risks[0]["title"] if risks else None,
               "computed_at": _now()}
    await db.properties.update_one({"_id": ObjectId(str(prop["_id"]))},
                                   {"$set": {"risk_profile": profile}})
    return profile


async def risk_summary() -> dict:
    """KPI CEO: riscuri active totale + proprietăți cu risc critic (score ≥ 80)."""
    out = {"active_risks": 0, "critical_properties": 0}
    async for d in db.properties.aggregate([
        {"$match": {"risk_profile.total": {"$gt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": "$risk_profile.total"},
                    "critical": {"$sum": {"$cond": [{"$gte": ["$risk_profile.max_score", 80]}, 1, 0]}}}},
    ]):
        out = {"active_risks": d["total"], "critical_properties": d["critical"]}
    return out


async def maturity_summary() -> dict:
    """KPI strategic: Maturity mediu + distribuție — pentru CEO Dashboard / Mission Control."""
    dist = {str(i): 0 for i in range(6)}
    scanned, weighted = 0, 0
    async for d in db.properties.aggregate([
        {"$match": {"maturity.level": {"$exists": True}}},
        {"$group": {"_id": "$maturity.level", "n": {"$sum": 1}}},
    ]):
        lvl = int(d["_id"] or 0)
        dist[str(lvl)] = d["n"]
        scanned += d["n"]
        weighted += lvl * d["n"]
    total = await db.properties.estimated_document_count()
    return {"avg_level": round(weighted / scanned, 2) if scanned else 0,
            "distribution": dist, "scanned": scanned, "total": total}
