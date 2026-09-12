"""Autonomy — Dispute pre-triage (extindere, REUTILIZARE).

OBSERVE (dispute deschise) → CLASSIFY (Claude, reutilizat din orchestrator) →
PRIORITIZE (determinist, explicabil) → PROPOSE (proposal) → HUMAN GATE.

NU rezolvă dispute, NU mișcă bani, NU schimbă stare legală/financiară. Doar adaugă
un strat de analiză pe documentul disputei (`autonomy_triage`) — non-destructiv,
idempotent. Rezolvarea rămâne 100% umană (endpoint admin existent).
"""
import logging
from datetime import datetime, timezone
from bson import ObjectId

from db import db

logger = logging.getLogger("propmanage.autonomy.disputes")

OPEN_STATUSES = ["open", "pending", "in_review"]
# Taxonomie derivată din triaj-ul existent (Claude) — reutilizată, nu inventată.
CATEGORIES = ["no_show", "quality", "price", "communication", "damage", "other"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(dt):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _age_days(dispute: dict) -> float | None:
    d = _parse(dispute.get("created_at"))
    if not d:
        return None
    return round((datetime.now(timezone.utc) - d).total_seconds() / 86400.0, 1)


def _deterministic_triage(dispute: dict, req: dict | None, ai: dict | None) -> dict:
    """Prioritate + risc + evidență, DETERMINIST și EXPLICABIL (fără scoring aleator)."""
    reasons = []
    score = 0.0

    # Semnal: vârstă (cu cât e mai veche, cu atât mai prioritară)
    age = _age_days(dispute)
    if age is not None:
        if age >= 14:
            score += 30; reasons.append(f"veche de {age:.0f} zile (≥14)")
        elif age >= 7:
            score += 18; reasons.append(f"veche de {age:.0f} zile (≥7)")
        elif age >= 3:
            score += 8; reasons.append(f"veche de {age:.0f} zile")

    # Semnal: expunere financiară (escrow blocat)
    escrow = float((req or {}).get("escrow_amount") or 0)
    if escrow >= 2000:
        score += 30; reasons.append(f"escrow ridicat {escrow:.0f} RON")
    elif escrow >= 500:
        score += 18; reasons.append(f"escrow {escrow:.0f} RON")
    elif escrow > 0:
        score += 8; reasons.append(f"escrow {escrow:.0f} RON")

    # Semnal: severitate din triaj-ul AI
    sev = (ai or {}).get("severity")
    if sev == "high":
        score += 25; reasons.append("severitate AI: high")
    elif sev == "medium":
        score += 12; reasons.append("severitate AI: medium")

    # Semnal: cererea încă activă (impact operațional)
    if (req or {}).get("status") in ("assigned", "in_progress"):
        score += 10; reasons.append("cerere încă în lucru")

    # Evidență disponibilă / lipsă
    evidence = dispute.get("evidence_urls") or []
    reason_txt = (dispute.get("reason") or "").strip()
    missing = []
    if not evidence:
        missing.append("fără dovezi atașate (evidence_urls gol)")
    if len(reason_txt) < 20:
        missing.append("motiv prea scurt/vag")
    if not req:
        missing.append("cererea asociată lipsește")

    insufficient = (len(reason_txt) < 20 and not evidence) or not req

    # Prioritate deterministă din scor
    if score >= 55:
        priority = "high"
    elif score >= 25:
        priority = "medium"
    else:
        priority = "low"

    # Confidence = cât de multă informație avem (nu certitudinea rezoluției)
    have = sum([bool(reason_txt and len(reason_txt) >= 20), bool(evidence), bool(req), bool(ai)])
    confidence = round(min(0.95, 0.35 + have * 0.15), 2)
    if insufficient:
        confidence = round(min(confidence, 0.4), 2)

    return {
        "priority": priority,
        "priority_score": round(score, 1),
        "priority_reasons": reasons or ["fără semnale puternice"],
        "confidence": confidence,
        "risk_level": "financial",  # disputele ating bani/escrow → mereu sensibile
        "human_approval_required": True,  # rezolvarea rămâne mereu umană
        "affected_request_id": dispute.get("request_id"),
        "affected_request_title": (req or {}).get("title"),
        "evidence_available": bool(evidence),
        "missing_information": missing,
        "insufficient_information": insufficient,
        "age_days": age,
        "escrow_amount": escrow,
    }


async def triage_one(dispute: dict, *, use_llm: bool = True, force: bool = False) -> dict:
    """Triază o dispută (idempotent). Nu schimbă statusul disputei. Non-destructiv."""
    if dispute.get("autonomy_triage") and not force:
        return {"skipped": True, "reason": "already_triaged"}

    req = None
    if dispute.get("request_id"):
        try:
            req = await db.requests.find_one({"_id": ObjectId(dispute["request_id"])})
        except Exception:  # noqa: BLE001
            req = None

    ai = dispute.get("ai_triage")
    det_pre = _deterministic_triage(dispute, req, ai)

    # LLM doar dacă avem informație suficientă (nu inventăm pe date insuficiente)
    if use_llm and not ai and not det_pre["insufficient_information"]:
        try:
            from orchestrator.playbooks import compute_dispute_triage
            ai = await compute_dispute_triage(dispute, req, test=False)
            await db.disputes.update_one({"_id": dispute["_id"]}, {"$set": {"ai_triage": ai}})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[disputes] LLM triage failed for {dispute.get('_id')}: {e}")
            ai = None

    det = _deterministic_triage(dispute, req, ai)
    category = (ai or {}).get("category") or ("other" if not det["insufficient_information"] else "unclear")

    autonomy_triage = {
        **det,
        "category": category,
        "ai_summary": (ai or {}).get("summary"),
        "ai_proposed_resolution": (ai or {}).get("proposed_resolution"),
        "ai_arguments": (ai or {}).get("arguments") or [],
        "ai_suggested_split": (ai or {}).get("suggested_split") or {},
        "status": "ready_for_human" if not det["insufficient_information"] else "waiting_information",
        "triaged_at": _now(),
        "triaged_by": "autonomy",
        "note": "Propunere AI — rezolvarea disputei rămâne decizie umană (mișcă bani din escrow).",
    }
    await db.disputes.update_one({"_id": dispute["_id"]}, {"$set": {"autonomy_triage": autonomy_triage}})
    return {"skipped": False, "dispute_id": str(dispute["_id"]), "priority": det["priority"],
            "category": category, "status": autonomy_triage["status"]}


async def triage_open_disputes(*, limit: int = 30, use_llm: bool = True, force: bool = False) -> dict:
    """Backfill bounded pe disputele deschise fără triaj. Idempotent."""
    q = {"status": {"$in": OPEN_STATUSES}}
    if not force:
        q["autonomy_triage"] = {"$exists": False}
    triaged = 0
    per_priority = {"high": 0, "medium": 0, "low": 0}
    per_status = {"ready_for_human": 0, "waiting_information": 0}
    async for d in db.disputes.find(q).limit(limit):
        res = await triage_one(d, use_llm=use_llm, force=force)
        if not res.get("skipped"):
            triaged += 1
            per_priority[res["priority"]] = per_priority.get(res["priority"], 0) + 1
            per_status[res["status"]] = per_status.get(res["status"], 0) + 1
    return {"triaged": triaged, "by_priority": per_priority, "by_status": per_status}


# ═══════════════════════ QUEUE + METRICS ═══════════════════════
async def dispute_queue_items(limit: int = 25) -> list[dict]:
    """Proiectează disputele triate în coada Autonomy Activity (NEEDS_HUMAN / WAITING)."""
    items = []
    prio_rank = {"high": 0, "medium": 1, "low": 2}
    docs = [d async for d in db.disputes.find({"status": {"$in": OPEN_STATUSES}}).limit(60)]
    docs.sort(key=lambda d: prio_rank.get((d.get("autonomy_triage") or {}).get("priority"), 3))
    for d in docs[:limit]:
        t = d.get("autonomy_triage")
        if not t:
            items.append({
                "source": "dispute", "category": "NEEDS_HUMAN", "priority": "medium", "confidence": None,
                "proposed_action": "Dispută netriată încă — se triază automat (bounded).",
                "status": "untriaged", "result": None, "timestamp": d.get("created_at"),
                "dispute_id": str(d["_id"]), "escalation_reason": "Necesită triaj + decizie umană."})
            continue
        waiting = t.get("status") == "waiting_information"
        items.append({
            "source": "dispute",
            "category": "WAITING" if waiting else "NEEDS_HUMAN",
            "priority": t.get("priority"),
            "confidence": t.get("confidence"),
            "proposed_action": t.get("ai_proposed_resolution") or t.get("ai_summary") or "Vezi triajul disputei.",
            "status": t.get("status"),
            "result": f"[{t.get('category')}] {t.get('ai_summary') or ''}"[:160],
            "timestamp": t.get("triaged_at"),
            "dispute_id": str(d["_id"]),
            "dispute_category": t.get("category"),
            "missing_information": t.get("missing_information"),
            "escalation_reason": ("Informație insuficientă: " + "; ".join(t.get("missing_information") or []))
                                  if waiting else "Rezoluția mișcă bani din escrow → decizie umană obligatorie.",
        })
    return items


async def dispute_metrics() -> dict:
    total = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}})
    triaged = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}, "autonomy_triage": {"$exists": True}})
    high = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}, "autonomy_triage.priority": "high"})
    medium = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}, "autonomy_triage.priority": "medium"})
    low = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}, "autonomy_triage.priority": "low"})
    waiting = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}, "autonomy_triage.status": "waiting_information"})
    ready = await db.disputes.count_documents({"status": {"$in": OPEN_STATUSES}, "autonomy_triage.status": "ready_for_human"})
    # confidence mediu (doar pe cele triate)
    confs = []
    async for d in db.disputes.find({"status": {"$in": OPEN_STATUSES}, "autonomy_triage": {"$exists": True}}, {"autonomy_triage.confidence": 1}):
        c = (d.get("autonomy_triage") or {}).get("confidence")
        if c is not None:
            confs.append(c)
    avg_conf = round(sum(confs) / len(confs), 2) if confs else None
    # rezolvate DUPĂ recomandare = triate ȘI ulterior rezolvate (verificat, nu doar recomandat)
    resolved_after = await db.disputes.count_documents({"status": "resolved", "autonomy_triage": {"$exists": True}})
    return {
        "disputes_total_open": total,
        "disputes_triaged": triaged,
        "disputes_untriaged": total - triaged,
        "disputes_high_priority": high,
        "disputes_medium_priority": medium,
        "disputes_low_priority": low,
        "disputes_waiting_information": waiting,
        "disputes_ready_for_human_decision": ready,
        "dispute_triage_avg_confidence": avg_conf,
        "disputes_resolved_after_recommendation": resolved_after,
    }
