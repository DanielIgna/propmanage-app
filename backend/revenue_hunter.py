"""Revenue Hunter Engine — primul agent comercial (Sprint 2 / Felia 1, Board Review 001).

Transformă starea Property DNA în OPORTUNITĂȚI COMERCIALE pentru serviciile monetizabile:
Digital Twin · Audit Tehnic · Design Interior · Design Tematic.

Principii respectate:
- Prompt 003 (ierarhia de cost): detectori pe REGULI, zero apeluri LLM în v1.
- Prompt 002: nu contactează clientul direct — doar recomandări in-app; aprobarea = click-ul clientului.
- Board Review 001: indicatorii tehnici sunt traduși în BENEFICII (siguranță, economie, confort,
  documentație, valoare) — niciodată procente.
- Guardrails: max 3 oportunități active / proprietate, cooldown 30 zile / (proprietate, serviciu),
  kill-switch prin orchestrator_config (id: revenue_hunter).
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.revenue_hunter")

AGENT_ID = "revenue_hunter"
COOLDOWN_DAYS = 30
MAX_ACTIVE_PER_PROPERTY = 3
SCAN_THROTTLE_HOURS = 12

# Serviciile monetizabile (Board Review 001) — copy în limbaj de beneficii, nu procente
SERVICES = {
    "digital_twin": {
        "label": "Digital Twin",
        "title": "Casa ta, în 3D — documentație completă",
        "benefit": "Primești modelul digital al locuinței: planuri, instalații și dosar tehnic care cresc valoarea proprietății la vânzare.",
        "value": 1500.0,
        "category": "other",
    },
    "audit_tehnic": {
        "label": "Audit Tehnic",
        "title": "Verifică sănătatea reală a casei",
        "benefit": "Un audit tehnic îți arată exact starea instalațiilor și structurii — previi reparațiile scumpe și dormi liniștit.",
        "value": 800.0,
        "category": "other",
    },
    "design_interior": {
        "label": "Design Interior",
        "title": "Transformă renovarea în confort",
        "benefit": "Designerii noștri îți gândesc spațiul cap-coadă: concept, materiale, execuție — confort zilnic și valoare adăugată.",
        "value": 2200.0,  # per cameră — ajustat la scan
        "category": "interior_design",
    },
    "design_tematic": {
        "label": "Design Tematic",
        "title": "Design tematic pe modelul 3D al casei",
        "benefit": "Folosim Digital Twin-ul existent ca să simulăm stiluri și amenajări — vezi rezultatul înainte să cheltui.",
        "value": 1500.0,
        "category": "interior_design",
    },
    "predictive_maintenance": {
        "label": "Mentenanță Predictivă",
        "title": "Planifică din timp, evită urgențele",
        "benefit": "Un activ aproape de finalul duratei de viață se înlocuiește planificat, nu în criză — costuri mai mici și zero surprize.",
        "value": 0.0,
        "category": "maintenance",
    },
}

# Directiva 014 — Commercial Execution: (categorie, prioritate comercială 1-5, domenii)
COMMERCIAL_META = {
    "digital_twin": ("documentation", 3, ["technical"]),
    "audit_tehnic": ("technical", 4, ["technical"]),
    "design_interior": ("interior", 2, ["interior"]),
    "design_tematic": ("interior", 2, ["interior"]),
    "predictive_maintenance": ("maintenance", 3, ["technical"]),
}

_RENOV_CATS = {"painting", "zugravit", "parchet", "faianta", "gips_carton", "interior_design"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def is_enabled() -> bool:
    from orchestrator.engine import is_playbook_enabled
    return await is_playbook_enabled(AGENT_ID)


async def _detect(prop: dict, twin: dict, reqs: list) -> list:
    """Detectorii rule-based → listă de candidați (service, value, confidence)."""
    cands = []
    rooms = int(prop.get("rooms") or 0)

    # 1. Digital Twin — proprietăți fără twin (documentație + valoare)
    if not twin and not prop.get("twin_unlocked"):
        cands.append(("digital_twin", SERVICES["digital_twin"]["value"], 0.9))

    # 2. Audit Tehnic — sănătate necunoscută sau scăzută (siguranță + economie)
    hs = prop.get("health_score")
    util = prop.get("utilities_health")
    struct = prop.get("structure_health")
    if hs is None or (util is not None and util < 60) or (struct is not None and struct < 60):
        cands.append(("audit_tehnic", SERVICES["audit_tehnic"]["value"], 0.8))

    # 3. Design Interior — renovare recentă confirmată (momentul perfect pentru amenajare)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    recent_renov = any(
        r.get("status") == "confirmed" and (r.get("confirmed_at") or "") >= cutoff
        and (r.get("category") or "") in _RENOV_CATS
        for r in reqs
    )
    if recent_renov:
        cands.append(("design_interior", SERVICES["design_interior"]["value"] * max(rooms, 1), 0.85))
    # 4. Design Tematic — are twin, nu are proiect de design (valorifică investiția în twin)
    elif twin and (twin.get("status") in ("approved", "validated") or prop.get("twin_unlocked")):
        cands.append(("design_tematic", SERVICES["design_tematic"]["value"], 0.7))

    return cands


async def scan_property(prop: dict) -> int:
    """Scanează o proprietate → creează oportunități noi (respectând guardrails). Returnează nr. create."""
    prop_id = str(prop["_id"])
    owner_id = prop.get("owner_id")
    if not owner_id:
        return 0

    active = await db.revenue_opportunities.count_documents({"property_id": prop_id, "status": "active"})
    if active >= MAX_ACTIVE_PER_PROPERTY:
        return 0

    # GI-2: Intent & Lead Intelligence — boost de prioritate pentru lead-uri fierbinți
    lead = await db.lead_scores.find_one({"user_id": owner_id}, {"tier": 1, "score": 1})
    lead_tier = (lead or {}).get("tier")
    lead_boost = {"hot": 1.5, "qualified": 1.2}.get(lead_tier, 1.0)

    cooldown_cutoff = (datetime.now(timezone.utc) - timedelta(days=COOLDOWN_DAYS)).isoformat()
    recent_services = set()
    async for o in db.revenue_opportunities.find(
        {"property_id": prop_id, "created_at": {"$gte": cooldown_cutoff}}, {"service": 1}
    ):
        recent_services.add(o.get("service"))

    twin = await db.twins.find_one({"property_id": prop_id})
    reqs = await db.requests.find({"property_id": prop_id}).sort("created_at", -1).to_list(100)

    candidates = [{"service": s, "value": v, "confidence": c}
                  for s, v, c in await _detect(prop, twin, reqs)]
    # GI-5P: detector predictiv — active aproape de EOL (bibliotecă actuarială)
    try:
        from property_intelligence import detect_predictive_candidates
        candidates += await detect_predictive_candidates(prop_id, reqs)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[revenue_hunter] predictive detect failed: {e}")

    created = 0
    for cand in candidates:
        service = cand["service"]
        if service in recent_services or active + created >= MAX_ACTIVE_PER_PROPERTY:
            continue
        meta = SERVICES.get(cand.get("template") or service) or {}
        category, priority, domains = COMMERCIAL_META.get(
            cand.get("template") or service, ("technical", 3, ["technical"]))
        priority = int(cand.get("commercial_priority") or priority)
        value, confidence = cand["value"], cand["confidence"]
        opp = {
            "id": uuid.uuid4().hex,
            "agent": AGENT_ID,
            "property_id": prop_id,
            "property_name": prop.get("name"),
            "owner_id": owner_id,
            "service": service,
            "service_label": cand.get("service_label") or meta.get("label"),
            "title": cand.get("title") or meta.get("title"),
            "benefit": cand.get("benefit") or meta.get("benefit"),
            "estimated_value_ron": round(value, 2),
            # prioritizare: valoare × încredere × intent (GI-2) × prioritate comercială (Directiva 014)
            "score": round(value * confidence * lead_boost * (0.8 + 0.1 * priority), 2),
            "category": cand.get("category") or category,
            "commercial_priority": priority,
            "commercial_domains": cand.get("commercial_domains") or domains,
            "lead_tier": lead_tier,
            "status": "active",
            "created_at": _now(),
        }
        await db.revenue_opportunities.insert_one({**opp})
        created += 1
        try:
            from event_bus import emit
            await emit("recommendation.created", property_id=prop_id,
                       payload={"service": service, "value": value, "agent": AGENT_ID, "opp_id": opp["id"]})
        except Exception:  # noqa: BLE001
            pass
    return created


async def scan_property_throttled(prop: dict) -> int:
    """Lazy scan cu throttle (max 1 scan / SCAN_THROTTLE_HOURS / proprietate)."""
    prop_id = str(prop["_id"])
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=SCAN_THROTTLE_HOURS)).isoformat()
    last = await db.revenue_hunter_scans.find_one({"_id": prop_id})
    if last and (last.get("ts") or "") >= cutoff:
        return 0
    await db.revenue_hunter_scans.update_one({"_id": prop_id}, {"$set": {"ts": _now()}}, upsert=True)
    created = await scan_property(prop)
    # GI-5P: decay + maturity + profil de risc se împrospătează cu scanarea zilnică (reuse cron)
    try:
        from property_intelligence import apply_health_decay, refresh_maturity, refresh_risk_profile
        decayed = await apply_health_decay(prop)
        if decayed:
            prop = {**prop, **decayed}
        await refresh_maturity(prop)
        await refresh_risk_profile(prop)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[revenue_hunter] intelligence refresh failed: {e}")
    return created


async def run_revenue_hunter_tick(limit: int = 500) -> dict:
    """Cron zilnic: scanează proprietățile. Respectă kill-switch-ul."""
    if not await is_enabled():
        logger.info("[revenue_hunter] disabled via kill-switch — skipping tick")
        return {"enabled": False, "scanned": 0, "created": 0}
    scanned = created = 0
    # GI-2: lead-urile fierbinți/calificate primele — proprietățile lor se scanează prioritar
    hot_owner_ids = [d["user_id"] async for d in db.lead_scores.find(
        {"tier": {"$in": ["hot", "qualified"]}, "user_id": {"$nin": [None, ""]}}, {"user_id": 1}
    ).sort("score", -1).limit(100)]
    seen_props = set()
    for owner_id in hot_owner_ids:
        async for prop in db.properties.find({"owner_id": owner_id}):
            seen_props.add(str(prop["_id"]))
            scanned += 1
            try:
                created += await scan_property_throttled(prop)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[revenue_hunter] hot-lead scan failed for {prop.get('_id')}: {e}")
    async for prop in db.properties.find({}).limit(limit):
        if str(prop["_id"]) in seen_props:
            continue
        scanned += 1
        try:
            created += await scan_property_throttled(prop)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[revenue_hunter] scan failed for {prop.get('_id')}: {e}")
    logger.info(f"[revenue_hunter] tick: scanned={scanned} created={created}")
    return {"enabled": True, "scanned": scanned, "created": created}
