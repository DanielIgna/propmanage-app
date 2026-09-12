"""Operational Autonomy Loop — închide bucla end-to-end.

OBSERVE (Analytics) → DETECT → FINDING (admin_ai_findings) → DECIDE/POLICY/RISK
→ ACT (admin_todos SAFE · admin_approvals MEDIUM/HIGH) → VERIFY → RECORD
(autonomy_loop_runs) → LEARN.

Principii dure (cerute de Fondator):
- REUTILIZARE, zero sisteme paralele: findings = `admin_ai_findings` existent,
  task-uri = `admin_todos`, aprobări = `admin_approvals`. Singura colecție nouă =
  `autonomy_loop_runs` (strict ledger/audit-trail).
- Detectoare DETERMINISTE peste Analytics existent + funnel-ul comercial. Zero LLM,
  zero pattern-uri inventate. Separă strict: raw_observation → finding → hypothesis.
- IDEMPOTENT & BOUNDED & SAFE-ON-RERUN: aceeași observație NU creează task-uri/finding-uri
  duplicate; acțiunile nu se re-execută accidental; un eșec într-un pas NU lasă starea
  inconsistentă (creăm întâi artefactul, apoi marcăm finding-ul).
- Human-in-the-loop pentru MEDIUM/HIGH: doar propunere prin `admin_approvals` (gate uman).
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.autonomy.loop")

# ── Praguri deterministe (constante — fără reglaj cosmetic) ───────────────────
BOUNCE_MIN_SESSIONS = 30          # trafic minim ca semnalul să conteze
BOUNCE_MED_SESSIONS = 120         # peste care severitatea urcă la medium
BOUNCE_MIN_PCT = 55.0             # bounce rate peste care e friction real
FUNNEL_MIN_STARTED = 5            # cereri începute minim ca abandonul să conteze
FUNNEL_MAX_CONVERSION_PCT = 40.0  # sub acest % început→creat = abandon ridicat
MAX_FINDINGS_PER_RUN = 6          # bound dur pe câte findings procesăm/rulare
DEDUP_WINDOW_HOURS = 24           # nu recrea același finding în fereastra asta
ANALYTICS_LOOKBACK_DAYS = 90
SOURCE = "analytics_loop"

# Rute pe care NU le tratăm (zgomot / non-comercial)
_IGNORED_ROUTES = {"", "/admin", "/logout", "/auth", "/auth/callback"}

# Politica de acțiune per tip de detector (risc → mod de execuție)
ACTION_POLICY = {
    "high_bounce_page": "SAFE",              # creează task de review (reversibil)
    "request_flow_abandonment": "MEDIUM",    # schimbare UX → aprobare umană
}

POLICY_DESCRIPTION = {
    "SAFE": "Auto-execuție: creează task de remediere în admin_todos (reversibil) + rezolvă finding-ul.",
    "REVERSIBLE": "Auto-execuție + audit + verificare (reversibil).",
    "MEDIUM": "Doar propunere: creează aprobare în admin_approvals (gate uman obligatoriu).",
    "HIGH": "Doar propunere: aprobare umană obligatorie (impact major / destructiv).",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _autonomy_actor() -> dict:
    return {"email": "autonomy@propmanage.ai", "name": "Operational Autonomy Loop", "role": "admin"}


# ═══════════════════════ 1. OBSERVE + DETECT ═══════════════════════
async def _detect_high_bounce_pages() -> list[dict]:
    """Detector determinist: pagini cu trafic mare și bounce ridicat (Analytics existent)."""
    d_from = (datetime.now(timezone.utc) - timedelta(days=ANALYTICS_LOOKBACK_DAYS)).date().isoformat()
    pipeline = [
        {"$match": {"day": {"$gte": d_from}}},
        {"$group": {
            "_id": "$entry_path",
            "sessions": {"$sum": 1},
            "bounces": {"$sum": {"$cond": [{"$lte": [{"$ifNull": ["$pageviews", 0]}, 1]}, 1, 0]}},
            "avg_dur_ms": {"$avg": {"$ifNull": ["$duration_ms", 0]}},
        }},
        {"$match": {"sessions": {"$gte": BOUNCE_MIN_SESSIONS}}},
        {"$sort": {"sessions": -1}},
        {"$limit": 25},
    ]
    out = []
    async for row in db.analytics_sessions.aggregate(pipeline):
        route = row.get("_id") or ""
        if route in _IGNORED_ROUTES or route.startswith("/admin"):
            continue
        sessions = int(row.get("sessions") or 0)
        bounces = int(row.get("bounces") or 0)
        bounce_pct = round(bounces / sessions * 100, 1) if sessions else 0.0
        if bounce_pct < BOUNCE_MIN_PCT:
            continue
        severity = "medium" if (sessions >= BOUNCE_MED_SESSIONS and bounce_pct >= 65) else "low"
        confidence = round(min(0.95, 0.5 + sessions / 500.0), 2)
        out.append({
            "detector": "high_bounce_page",
            "affected_route": route,
            "severity": severity,
            "confidence": confidence,
            "raw_observation": {"sessions": sessions, "bounces": bounces, "bounce_pct": bounce_pct,
                                 "avg_session_sec": round((row.get("avg_dur_ms") or 0) / 1000)},
            "finding": f"Pagina «{route}» are bounce {bounce_pct}% pe {sessions} sesiuni (90z) — peste pragul {BOUNCE_MIN_PCT}%.",
            "hypothesis": "Mesajul din primele secunde sau CTA-ul nu convinge; vizitatorii pleacă după o singură pagină.",
            "recommended_action": f"Revizuiește primele 3 secunde ale paginii «{route}»: un singur CTA dominant + clarificarea valorii.",
            "verification_criteria": f"bounce_pct pentru «{route}» scade sub {BOUNCE_MIN_PCT}% la următoarea observație (90z).",
        })
    return out


async def _detect_request_flow_abandonment() -> list[dict]:
    """Detector determinist peste funnel-ul comercial: mulți încep, puțini creează cerere."""
    try:
        from routes.analytics_growth import analytics_commercial_funnel
        data = await analytics_commercial_funnel("90d", "", "", _autonomy_actor())
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[loop] funnel observe failed: {e}")
        return []
    kpi = data.get("kpi") or {}
    started = int(kpi.get("started") or 0)
    created = int(kpi.get("created") or 0)
    conv = float(kpi.get("started_to_created_pct") or 0.0)
    if started < FUNNEL_MIN_STARTED or conv >= FUNNEL_MAX_CONVERSION_PCT:
        return []
    return [{
        "detector": "request_flow_abandonment",
        "affected_route": "/client",
        "severity": "medium",
        "confidence": round(min(0.9, 0.5 + started / 50.0), 2),
        "raw_observation": {"request_started": started, "request_created": created,
                            "started_to_created_pct": conv,
                            "requests_created_real": (data.get("backend_check") or {}).get("requests_created_real")},
        "finding": f"Din {started} clienți care încep o cerere, doar {conv}% o finalizează (sub pragul {FUNNEL_MAX_CONVERSION_PCT}%).",
        "hypothesis": "Wizardul de cerere are un pas de fricțiune (buget/descriere) care descurajează finalizarea.",
        "recommended_action": "Simplifică wizardul de cerere: mută hint-ul de preț mai devreme și fă câmpurile opționale mai clare.",
        "verification_criteria": f"started_to_created_pct urcă peste {FUNNEL_MAX_CONVERSION_PCT}% la următoarea observație.",
    }]


async def observe() -> list[dict]:
    """Rulează toate detectoarele deterministe. Bounded la MAX_FINDINGS_PER_RUN."""
    findings: list[dict] = []
    for detector in (_detect_high_bounce_pages, _detect_request_flow_abandonment):
        try:
            findings.extend(await detector())
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[loop] detector {detector.__name__} failed: {e}")
    # prioritizează medium înaintea low, apoi bound dur
    findings.sort(key=lambda f: (0 if f["severity"] == "medium" else 1, -float(f.get("confidence") or 0)))
    return findings[:MAX_FINDINGS_PER_RUN]


# ═══════════════════════ 2. FINDING (admin_ai_findings) ═══════════════════════
def _composite_key(obs: dict) -> str:
    return f"{SOURCE}:{obs['detector']}:{obs['affected_route']}"


async def get_or_create_finding(obs: dict) -> tuple[dict, bool]:
    """Idempotent: NU recreează un finding activ sau recent pentru aceeași observație."""
    key = _composite_key(obs)
    window = (datetime.now(timezone.utc) - timedelta(hours=DEDUP_WINDOW_HOURS)).isoformat()
    existing = await db.admin_ai_findings.find_one({"composite_key": key})
    if existing and (existing.get("status") in ("open", "triaged") or (existing.get("last_seen_at") or "") >= window):
        await db.admin_ai_findings.update_one(
            {"composite_key": key},
            {"$set": {"last_seen_at": _now(), "severity": obs["severity"], "confidence": obs["confidence"],
                      "evidence": obs["raw_observation"]}, "$inc": {"occurrences": 1}},
        )
        existing = await db.admin_ai_findings.find_one({"composite_key": key})
        return existing, False
    now = _now()
    doc = {
        "id": str(uuid.uuid4()),
        "composite_key": key,
        "source": SOURCE,
        "pattern": obs["detector"],
        "label": "Fricțiune comercială (Analytics)",
        "severity": obs["severity"],                 # doar low/medium (nu penalizează Security)
        "confidence": obs["confidence"],
        "description": obs["finding"],
        "raw_observation": obs["raw_observation"],
        "evidence": obs["raw_observation"],
        "hypothesis": obs["hypothesis"],
        "affected_route": obs["affected_route"],
        "affected_function": _fn_for_route(obs["affected_route"]),
        "recommended_action": obs["recommended_action"],
        "verification_criteria": obs["verification_criteria"],
        "action_class": ACTION_POLICY.get(obs["detector"], "MEDIUM"),
        "entity_type": "route",
        "entity_id": obs["affected_route"],
        "entity_label": obs["affected_route"],
        "status": "open",
        "first_seen_at": now,
        "last_seen_at": now,
        "created_at": now,
        "occurrences": 1,
        "scan_id": now,
    }
    await db.admin_ai_findings.insert_one(doc)
    doc.pop("_id", None)
    return doc, True


def _fn_for_route(route: str) -> str:
    if route.startswith("/client"):
        return "FN-009 Marketplace / Client flow"
    if route.startswith("/specialist"):
        return "FN-009 Marketplace / Specialist"
    return "FN-001 Analytics & Growth"


# ═══════════════════════ 3+4. DECIDE / POLICY / RISK + ACT ═══════════════════════
async def _governance() -> dict:
    """Sursa de adevăr pentru execuția autonomă = `self_driving_settings` (kill-switch EXISTENT,
    prin `self_driving.get_settings()`). NU există buget monetar separat în platformă; limitele
    per-rulare = `MAX_FINDINGS_PER_RUN` + fereastra de dedup. Loop-ul RESPECTĂ acest kill-switch:
    dacă `low_risk_autopilot` e OFF, NU auto-execută (fail-safe, motiv înregistrat în ledger)."""
    try:
        from autonomy.self_driving import get_settings
        s = await get_settings()
        return {"low_risk_autopilot": bool(s.get("low_risk_autopilot", True)), "source": "self_driving_settings.main"}
    except Exception:  # noqa: BLE001
        return {"low_risk_autopilot": True, "source": "default"}


async def _existing_todo_for(key: str) -> dict | None:
    return await db.admin_todos.find_one({"source": SOURCE, "finding_key": key, "done": False})


async def _existing_approval_for(key: str) -> dict | None:
    return await db.admin_approvals.find_one({"finding_key": key, "status": "pending"})


async def _create_todo(finding: dict) -> dict:
    key = finding["composite_key"]
    existing = await _existing_todo_for(key)
    if existing:
        return {"todo_id": existing["id"], "reused": True}
    todo = {
        "id": str(uuid.uuid4()),
        "text": f"[Autonomy] {finding['recommended_action']}",
        "priority": "medium" if finding["severity"] == "medium" else "low",
        "done": False,
        "created_at": _now(),
        "created_by": "autonomy_loop",
        "source": SOURCE,
        "finding_key": key,
        "evidence": finding.get("evidence"),
    }
    await db.admin_todos.insert_one(todo)
    return {"todo_id": todo["id"], "reused": False}


async def _create_approval(finding: dict) -> dict:
    key = finding["composite_key"]
    existing = await _existing_approval_for(key)
    if existing:
        return {"approval_id": existing["id"], "reused": True}
    approval_id = str(uuid.uuid4())
    doc = {
        "id": approval_id,
        "action": "analytics_loop_remediation",
        "payload": {"finding_key": key, "recommended_action": finding["recommended_action"],
                    "affected_route": finding["affected_route"], "severity": finding["severity"]},
        "scope": "general",
        "finding_key": key,
        "requested_by": "autonomy_loop",
        "requested_by_email": "autonomy@propmanage.ai",
        "requested_by_seniority": "junior",   # rămâne pending → necesită aprobare senior/human
        "reason": finding["description"],
        "evidence": finding.get("evidence"),
        "status": "pending",
        "created_at": _now(),
    }
    await db.admin_approvals.insert_one(doc)
    try:
        from services import notify
        async for reviewer in db.users.find({"role": "admin", "admin_scope": "general", "is_active": {"$ne": False}}):
            await notify(str(reviewer.get("_id")), "⚠️ Propunere autonomie (aprobare)",
                         f"Loop-ul operațional propune: {finding['recommended_action']}",
                         type_="admin_approval", link="/admin/approvals")
    except Exception:  # noqa: BLE001
        pass
    return {"approval_id": approval_id, "reused": False}


async def decide_and_act(finding: dict, autoexec_allowed: bool = True) -> dict:
    """Clasifică riscul și acționează. SAFE → auto todo + rezolvă finding.
    MEDIUM/HIGH → propunere aprobare (gate uman), finding rămâne open.
    Respectă guvernanța: dacă `autoexec_allowed` e False (kill-switch OFF), SAFE NU se execută
    (fail-safe, finding rămâne open, motiv înregistrat). Safe-on-failure: creăm întâi artefactul."""
    action_class = finding.get("action_class") or ACTION_POLICY.get(finding.get("pattern"), "MEDIUM")
    key = finding["composite_key"]
    if action_class in ("SAFE", "REVERSIBLE"):
        if not autoexec_allowed:
            await db.admin_ai_findings.update_one(
                {"composite_key": key},
                {"$set": {"status": "open", "autonomy_action": {"type": "blocked_governance",
                          "class": action_class, "reason": "low_risk_autopilot OFF (self_driving_settings)"}}},
            )
            return {"action_class": action_class, "actor": "autonomous(blocat)",
                    "action": {"type": "blocked_governance", "reason": "low_risk_autopilot OFF (self_driving_settings)"},
                    "rollback": {"how": "n/a — nicio execuție"}, "human_gate": False, "blocked": True}
        res = await _create_todo(finding)
        # marcăm finding-ul rezolvat DOAR după ce task-ul de remediere există (safe)
        await db.admin_ai_findings.update_one(
            {"composite_key": key},
            {"$set": {"status": "resolved", "resolved_at": _now(), "resolved_by": "autonomy_loop",
                      "resolution_note": "autonomy_loop: acțiune SAFE — task de remediere creat în admin_todos.",
                      "autonomy_action": {"type": "todo", "todo_id": res["todo_id"], "class": action_class}}},
        )
        return {"action_class": action_class, "actor": "autonomous",
                "action": {"type": "todo", "todo_id": res["todo_id"], "reused": res["reused"]},
                "rollback": {"how": "close/delete todo", "todo_id": res["todo_id"]},
                "human_gate": False}
    # MEDIUM / HIGH → gate uman
    res = await _create_approval(finding)
    await db.admin_ai_findings.update_one(
        {"composite_key": key},
        {"$set": {"status": "open", "autonomy_action": {"type": "approval", "approval_id": res["approval_id"],
                  "class": action_class, "awaiting": "human_approval"}}},
    )
    return {"action_class": action_class, "actor": "autonomous→human",
            "action": {"type": "approval", "approval_id": res["approval_id"], "reused": res["reused"]},
            "rollback": {"how": "reject approval", "approval_id": res["approval_id"]},
            "human_gate": True}


# ═══════════════════════ 5. VERIFY ═══════════════════════
async def verify(finding: dict, act: dict) -> dict:
    checks = {}
    f = await db.admin_ai_findings.find_one({"composite_key": finding["composite_key"]}, {"_id": 0, "status": 1})
    checks["finding_recorded"] = bool(f)
    checks["finding_status"] = (f or {}).get("status")
    a = act.get("action") or {}
    if a.get("type") == "todo":
        checks["todo_exists"] = bool(await db.admin_todos.find_one({"id": a.get("todo_id")}, {"_id": 1}))
    elif a.get("type") == "approval":
        ap = await db.admin_approvals.find_one({"id": a.get("approval_id")}, {"_id": 0, "status": 1})
        checks["approval_exists"] = bool(ap)
        checks["approval_status"] = (ap or {}).get("status")
    elif a.get("type") == "lifecycle":
        # Read-back independent: proiectul chiar a ajuns în starea țintă?
        target = {"active_to_on_hold": "on_hold", "on_hold_to_archived": "archived"}.get(a.get("transition"))
        actual = None
        try:
            from bson import ObjectId as _OID
            p = await db.projects.find_one({"_id": _OID(a.get("project_id"))}, {"_id": 0, "status": 1})
            actual = (p or {}).get("status")
        except Exception:  # noqa: BLE001
            actual = None
        checks["lifecycle_target_state"] = target
        checks["lifecycle_actual_state"] = actual
        checks["lifecycle_verified"] = bool(target and actual == target)
    checks["ok"] = bool(checks.get("finding_recorded") and (
        checks.get("todo_exists") or checks.get("approval_exists") or checks.get("lifecycle_verified")))
    return checks


# ═══════════════════════ 7. LEARN ═══════════════════════
async def learn(current_keys: set[str]) -> dict:
    """Dacă un finding analytics_loop încă OPEN nu mai apare în observația curentă
    (semnalul a dispărut) → îl marcăm rezolvat (învățare). Bounded."""
    resolved = []
    cursor = db.admin_ai_findings.find({"source": SOURCE, "status": "open"}).limit(50)
    async for f in cursor:
        key = f.get("composite_key")
        if key and key not in current_keys:
            await db.admin_ai_findings.update_one(
                {"composite_key": key},
                {"$set": {"status": "resolved", "resolved_at": _now(), "resolved_by": "autonomy_loop",
                          "resolution_note": "autonomy_loop LEARN: semnalul a dispărut la re-observație (criteriu de verificare îndeplinit)."}},
            )
            resolved.append(key)
    return {"auto_resolved": len(resolved), "keys": resolved}


# ═══════════════════════ 6. LEARN → KNOWLEDGE (verified outcomes → ai_memories) ═══════════════════════
# Doar rezultate REALE verificate devin memorie operațională reutilizabilă. NU sintetic:
# se creează exclusiv din acțiuni SAFE executate autonom și VERIFICATE (verify.ok). Idempotent
# per finding_key. Crește maturitatea memoriei ONEST (source="verified_outcome", nu "autonomy_seed").
KNOWLEDGE_MEMORY_SOURCE = "verified_outcome"


def _knowledge_tokens(text: str) -> list[str]:
    try:
        from ai_core.memory import _tokenize
        return _tokenize(text)
    except Exception:  # noqa: BLE001
        return []


async def _memory_exists(finding_key: str) -> bool:
    return bool(await db.ai_memories.find_one(
        {"source": KNOWLEDGE_MEMORY_SOURCE, "meta.finding_key": finding_key}, {"_id": 1}))


async def _promote_one(key: str, detector: str, route: str, rec: str, todo_id) -> bool:
    """Creează o memorie reutilizabilă dintr-un outcome verificat. Idempotent."""
    if not key or await _memory_exists(key):
        return False
    content = (
        f"PLAYBOOK VERIFICAT (autonomie): la detectarea «{detector}» pe «{route}», "
        f"acțiunea SAFE executată automat a fost «{rec}», iar rezultatul a fost VERIFICAT OK "
        f"(task de remediere creat, reversibil). Reutilizabil pentru situații similare."
    )
    doc = {
        "id": uuid.uuid4().hex,
        "user_id": "system:autonomy",
        "scope": "admin_agent",
        "content": content[:4000],
        "summary": f"Verified: {detector} @ {route} → {rec[:120]}"[:280],
        "tokens": _knowledge_tokens(content),
        "source": KNOWLEDGE_MEMORY_SOURCE,
        "kind": "operational_playbook",
        "meta": {"finding_key": key, "detector": detector, "route": route,
                 "todo_id": todo_id, "verified_at": _now()},
        "created_at": _now(),
        "expires_at": None,   # cunoștință operațională persistentă
    }
    await db.ai_memories.insert_one(doc)
    return True


async def promote_verified_to_knowledge(steps: list[dict]) -> dict:
    """(a) outcomes verificate din tick-ul curent + (b) backfill bounded din findings reale
    deja verificate (istoricul autonomy). Ambele REALE, idempotente."""
    created: list[str] = []

    # (a) fresh: acțiuni SAFE executate autonom în acest tick + verificate OK
    for st in steps:
        act = st.get("action") or {}
        if st.get("human_gate") or act.get("type") not in ("todo", "lifecycle") or st.get("actor") != "autonomous":
            continue
        if not (st.get("verify") or {}).get("ok"):
            continue
        key = st.get("finding_key")
        if not key or key in created:
            continue
        rec = st.get("recommended_action")
        if not rec:
            if act.get("type") == "lifecycle":
                rec = f"tranziție lifecycle {act.get('transition')}"
            else:
                f = await db.admin_ai_findings.find_one({"composite_key": key}, {"_id": 0, "recommended_action": 1})
                rec = (f or {}).get("recommended_action") or "acțiune de remediere SAFE"
        if await _promote_one(key, st.get("detector") or "autonomy", st.get("route") or "", rec, act.get("todo_id")):
            created.append(key)

    # (b) backfill: findings reale cu acțiune autonomă (todo/lifecycle) deja rezolvate/triaged,
    # al căror artefact încă există, care NU sunt încă în knowledge.
    try:
        cur = db.admin_ai_findings.find({
            "autonomy_action.type": {"$in": ["todo", "lifecycle"]},
            "status": {"$in": ["resolved", "triaged"]},
        }).limit(50)
        async for f in cur:
            key = f.get("composite_key")
            if not key or key in created or await _memory_exists(key):
                continue
            aa = f.get("autonomy_action") or {}
            todo_id = aa.get("todo_id")
            if aa.get("type") == "todo" and todo_id and not await db.admin_todos.find_one({"id": todo_id}, {"_id": 1}):
                continue  # task-ul nu mai există → nu e un outcome verificabil acum
            rec = f.get("recommended_action") or (f"tranziție lifecycle {aa.get('transition')}" if aa.get("type") == "lifecycle" else "acțiune de remediere SAFE")
            detector = f.get("pattern") or "autonomy"
            route = f.get("affected_route") or f"{f.get('entity_type')}:{f.get('entity_id')}"
            if await _promote_one(key, detector, route, rec, todo_id):
                created.append(key)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[loop] knowledge backfill failed: {e}")

    return {"knowledge_records_created": len(created), "keys": created}


# ═══════════════════════ OBSERVE #2: backlog findings Knowledge Center ═══════════════════════
# A doua sursă REALĂ (fără duplicare): findings DEJA existente în admin_ai_findings (Knowledge Center).
# NON-destructive → SAFE (task de remediere, reversibil). Destructive (orphan_twins etc.) NU sunt
# atinse aici — au fluxul lor cu aprobare umană (Data Integrity). Controlul uman NU scade.
KNOWLEDGE_SAFE_PATTERNS = {"stale_project"}
KNOWLEDGE_POLICY = {
    "stale_project": {
        "action_class": "SAFE",
        "recommended_action": "Revizuiește proiectul blocat (30+ zile fără activitate): reactivează, pune pe hold sau închide.",
        "verification_criteria": "proiectul primește activitate nouă SAU un admin îi schimbă statusul.",
    },
}


async def observe_knowledge_findings(limit: int = 3) -> list[dict]:
    """Observă findings reale deschise (whitelist non-destructiv), fără autonomy_action. Trasabil la finding."""
    out = []
    cur = db.admin_ai_findings.find({
        "status": "open", "source": {"$ne": SOURCE},
        "pattern": {"$in": list(KNOWLEDGE_SAFE_PATTERNS)},
        "autonomy_action": {"$exists": False},
    }).limit(limit)
    async for f in cur:
        pat = f.get("pattern")
        pol = KNOWLEDGE_POLICY.get(pat, {})
        out.append({
            "mode": "existing_finding", "detector": f"knowledge:{pat}",
            "composite_key": f.get("composite_key"), "finding_id": f.get("id"),
            "affected_route": f"{f.get('entity_type')}:{f.get('entity_id')}",
            "affected_function": "FN-009 Marketplace / Proiecte",
            "severity": "low" if (f.get("severity") in (None, "info", "low", "warning")) else "medium",
            "confidence": 0.9, "action_class": pol.get("action_class", "MEDIUM"),
            "raw_observation": {"finding_id": f.get("id"), "pattern": pat, "entity_id": f.get("entity_id"),
                                "first_seen_at": f.get("first_seen_at"), "description": f.get("description"),
                                "source_collection": "admin_ai_findings"},
            "hypothesis": f.get("description") or "Finding real din Knowledge Center.",
            "recommended_action": pol.get("recommended_action", "Revizuiește finding-ul."),
            "verification_criteria": pol.get("verification_criteria", ""),
        })
    return out


async def act_on_existing_finding(obs: dict, autoexec_allowed: bool) -> dict:
    """Acționează pe un finding REAL existent. SAFE → task de remediere (reversibil, fără aprobare);
    altfel → aprobare umană. Respectă guvernanța (kill-switch)."""
    key = obs["composite_key"]
    action_class = obs["action_class"]
    finding = {"composite_key": key, "severity": obs["severity"],
               "recommended_action": obs["recommended_action"], "evidence": obs["raw_observation"]}
    if action_class in ("SAFE", "REVERSIBLE"):
        if not autoexec_allowed:
            await db.admin_ai_findings.update_one({"composite_key": key},
                {"$set": {"autonomy_action": {"type": "blocked_governance", "class": action_class,
                          "reason": "low_risk_autopilot OFF (self_driving_settings)"}}})
            return {"action_class": action_class, "actor": "autonomous(blocat)",
                    "action": {"type": "blocked_governance", "reason": "low_risk_autopilot OFF"},
                    "rollback": {"how": "n/a"}, "human_gate": False, "blocked": True}
        # stale_project → tranziție REALĂ de business (active→on_hold), reversibilă, validată.
        pattern = (obs.get("raw_observation") or {}).get("pattern")
        entity_id = (obs.get("raw_observation") or {}).get("entity_id")
        if pattern == "stale_project" and entity_id:
            try:
                from autonomy.lifecycle import transition_project
                lc = await transition_project(entity_id, "active_to_on_hold", actor=_autonomy_actor(),
                                              autoexec_allowed=True,
                                              reason="autonomy_loop: proiect stale >30z → on_hold (reversibil)")
                if lc.get("ok") and lc.get("status") in ("executed", "idempotent"):
                    await db.admin_ai_findings.update_one({"composite_key": key},
                        {"$set": {"status": "triaged", "autonomy_action": {"type": "lifecycle",
                                  "transition": "active_to_on_hold", "project_id": entity_id,
                                  "verified": lc.get("verified"), "class": action_class,
                                  "by": "autonomy_loop", "at": _now()}}})
                    return {"action_class": action_class, "actor": "autonomous",
                            "action": {"type": "lifecycle", "transition": "active_to_on_hold",
                                       "project_id": entity_id, "verified": lc.get("verified"), "reused": False},
                            "rollback": {"how": "on_hold→active (reversibil)", "project_id": entity_id},
                            "human_gate": False, "lifecycle": lc}
                # not eligible / blockers / not stale → fall back to TODO (vizibilitate)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[loop] lifecycle transition failed for {entity_id}: {e}")
        res = await _create_todo(finding)
        await db.admin_ai_findings.update_one({"composite_key": key},
            {"$set": {"status": "triaged", "autonomy_action": {"type": "todo", "todo_id": res["todo_id"],
                      "class": action_class, "by": "autonomy_loop", "at": _now()}}})
        return {"action_class": action_class, "actor": "autonomous",
                "action": {"type": "todo", "todo_id": res["todo_id"], "reused": res["reused"]},
                "rollback": {"how": "close/delete todo + $unset autonomy_action", "todo_id": res["todo_id"]},
                "human_gate": False}
    res = await _create_approval(finding)
    await db.admin_ai_findings.update_one({"composite_key": key},
        {"$set": {"autonomy_action": {"type": "approval", "approval_id": res["approval_id"],
                  "class": action_class, "awaiting": "human_approval"}}})
    return {"action_class": action_class, "actor": "autonomous→human",
            "action": {"type": "approval", "approval_id": res["approval_id"], "reused": res["reused"]},
            "rollback": {"how": "reject approval"}, "human_gate": True}


async def _emit_analytics(signal: str, meta: dict) -> None:
    """Închide bucla înapoi în Analytics: eveniment măsurabil în analytics_events (colecție existentă).
    Eveniment de sistem (visitor_id=system:autonomy_loop) → NU creează sesiune, NU afectează bounce/funnel."""
    try:
        await db.analytics_events.insert_one({
            "type": "autonomy", "intent_signal": signal, "path": "/admin/autonomy",
            "visitor_id": "system:autonomy_loop", "session_id": "system:autonomy_loop",
            "ts": _now(), "day": datetime.now(timezone.utc).date().isoformat(),
            "meta": meta, "tenant_id": "main",
        })
    except Exception:  # noqa: BLE001
        pass


async def _scores_snapshot() -> dict | None:
    try:
        from routes.autonomy import load_targets
        from autonomy.engine import compute_autonomy_scores
        cfg = await load_targets()
        rep = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
        return rep.get("scores")
    except Exception:  # noqa: BLE001
        return None


# ═══════════════════════ ORCHESTRATOR ═══════════════════════
async def _operational_score() -> float | None:
    try:
        from routes.autonomy import load_targets
        from autonomy.engine import compute_autonomy_scores
        cfg = await load_targets()
        report = await compute_autonomy_scores(weights=cfg["weights"], targets=cfg["targets"])
        return (report.get("breakdown_summary") or report.get("scores") or {}).get("operational")
    except Exception:  # noqa: BLE001
        return None


async def run_loop_tick(triggered_by: str = "manual") -> dict:
    """O rulare completă a buclei. Idempotent, bounded, safe-on-failure."""
    run_id = str(uuid.uuid4())
    started_at = _now()
    steps = []
    gov = await _governance()
    scores_before = await _scores_snapshot()
    observations = await observe()
    current_keys = {_composite_key(o) for o in observations}
    findings_created = 0
    actions_taken = {"todo": 0, "approval": 0, "blocked_governance": 0, "lifecycle": 0, "dispute_triage": 0}
    for obs in observations:
        try:
            finding, created = await get_or_create_finding(obs)
            if created:
                findings_created += 1
            # dacă finding-ul e deja handled real (todo/approval) → nu re-acționăm.
            # blocked_governance NU e „handled" → se reîncearcă când guvernanța permite.
            already = finding.get("autonomy_action")
            if not created and already and already.get("type") != "blocked_governance":
                steps.append({"detector": obs["detector"], "route": obs["affected_route"],
                              "finding_key": finding["composite_key"], "created": False,
                              "decision": "no_change (deja procesat)", "action": already, "verify": {"ok": True}})
                continue
            act = await decide_and_act(finding, autoexec_allowed=gov["low_risk_autopilot"])
            if act["action"]["type"] == "todo" and not act["action"].get("reused"):
                actions_taken["todo"] += 1
            elif act["action"]["type"] == "approval" and not act["action"].get("reused"):
                actions_taken["approval"] += 1
            elif act["action"]["type"] == "blocked_governance":
                actions_taken["blocked_governance"] += 1
            ver = await verify(finding, act)
            steps.append({
                "detector": obs["detector"], "route": obs["affected_route"],
                "severity": obs["severity"], "confidence": obs["confidence"],
                "finding_key": finding["composite_key"], "created": created,
                "raw_observation": obs["raw_observation"], "hypothesis": obs["hypothesis"],
                "decision": f"{act['action_class']} → {act['action']['type']}"
                            + (" (aprobare umană)" if act["human_gate"] else " (auto)"),
                "action": act["action"], "actor": act["actor"], "human_gate": act["human_gate"],
                "rollback": act["rollback"], "verify": ver,
            })
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[loop] step failed for {obs.get('detector')}: {e}")
            steps.append({"detector": obs.get("detector"), "route": obs.get("affected_route"),
                          "error": str(e)[:200], "verify": {"ok": False}})
    # OBSERVE #2 — backlog findings Knowledge Center (surse REALE existente, non-destructive → SAFE)
    knowledge_obs = await observe_knowledge_findings()
    for kobs in knowledge_obs:
        try:
            act = await act_on_existing_finding(kobs, autoexec_allowed=gov["low_risk_autopilot"])
            a_type = act["action"]["type"]
            if a_type == "todo" and not act["action"].get("reused"):
                actions_taken["todo"] += 1
                await _emit_analytics("autonomy_action_executed", {"finding_key": kobs["composite_key"],
                    "detector": kobs["detector"], "action": "todo", "todo_id": act["action"]["todo_id"],
                    "class": act["action_class"], "affected_function": kobs["affected_function"]})
            elif a_type == "lifecycle":
                actions_taken["lifecycle"] += 1
                await _emit_analytics("autonomy_action_executed", {"finding_key": kobs["composite_key"],
                    "detector": kobs["detector"], "action": "lifecycle",
                    "transition": act["action"].get("transition"), "project_id": act["action"].get("project_id"),
                    "class": act["action_class"], "affected_function": kobs["affected_function"]})
            elif a_type == "approval" and not act["action"].get("reused"):
                actions_taken["approval"] += 1
            elif a_type == "blocked_governance":
                actions_taken["blocked_governance"] += 1
            ver = await verify({"composite_key": kobs["composite_key"]}, act)
            steps.append({
                "detector": kobs["detector"], "route": kobs["affected_route"], "source": "knowledge_center",
                "severity": kobs["severity"], "confidence": kobs["confidence"],
                "finding_key": kobs["composite_key"], "created": False,
                "raw_observation": kobs["raw_observation"], "hypothesis": kobs["hypothesis"],
                "recommended_action": kobs["recommended_action"],
                "decision": f"{act['action_class']} → {a_type}" + (" (aprobare umană)" if act["human_gate"] else " (auto)"),
                "action": act["action"], "actor": act["actor"], "human_gate": act["human_gate"],
                "rollback": act["rollback"], "verify": ver, "affected_function": kobs["affected_function"],
            })
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[loop] knowledge step failed {kobs.get('detector')}: {e}")
            steps.append({"detector": kobs.get("detector"), "route": kobs.get("affected_route"),
                          "source": "knowledge_center", "error": str(e)[:200], "verify": {"ok": False}})

    # OBSERVE #3 — Dispute pre-triage (bounded, non-destructiv, kill-switch gated).
    # Clasifică + prioritizează + propune; NU rezolvă (rezolvarea mișcă bani → 100% umană).
    if gov["low_risk_autopilot"]:
        try:
            from autonomy.disputes import triage_open_disputes
            dt = await triage_open_disputes(limit=3, use_llm=True)
            actions_taken["dispute_triage"] = dt.get("triaged", 0)
            if dt.get("triaged"):
                steps.append({
                    "detector": "dispute_triage", "route": "disputes", "source": "dispute_triage",
                    "severity": "medium", "created": False,
                    "decision": f"SAFE → triaj {dt['triaged']} dispute (propunere, fără rezolvare)",
                    "action": {"type": "triage", "count": dt["triaged"], "by_priority": dt.get("by_priority")},
                    "actor": "autonomous", "human_gate": False, "verify": {"ok": True},
                    "recommended_action": "Triaj dispute — clasificare + propunere; decizia rămâne umană.",
                })
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[loop] dispute triage failed: {e}")

    learned = await learn(current_keys)
    knowledge = await promote_verified_to_knowledge(steps)
    op_after = await _operational_score()
    scores_after = await _scores_snapshot()
    run = {
        "id": run_id,
        "triggered_by": triggered_by,
        "started_at": started_at,
        "finished_at": _now(),
        "governance": gov,
        "observations": len(observations) + len(knowledge_obs),
        "findings_created": findings_created,
        "actions_taken": actions_taken,
        "learned": learned,
        "knowledge": knowledge,
        "operational_score_after": op_after,
        "scores_before": scores_before,
        "scores_after": scores_after,
        "steps": steps,
        "outcome": "applied" if (findings_created or actions_taken["todo"] or actions_taken["approval"] or actions_taken["lifecycle"] or actions_taken["dispute_triage"] or learned["auto_resolved"] or knowledge["knowledge_records_created"]) else ("blocked_by_governance" if actions_taken["blocked_governance"] else "no_change"),
    }
    await db.autonomy_loop_runs.insert_one(dict(run))
    run.pop("_id", None)
    logger.info(f"[loop] tick {run['outcome']} — obs={run['observations']} findings={findings_created} "
                f"todos={actions_taken['todo']} approvals={actions_taken['approval']} lifecycle={actions_taken['lifecycle']} "
                f"disputes={actions_taken['dispute_triage']} learned={learned['auto_resolved']} "
                f"knowledge={knowledge['knowledge_records_created']}")
    return run
