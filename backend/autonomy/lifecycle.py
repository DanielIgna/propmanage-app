"""Autonomy — Safe Project Lifecycle (extindere îngustă, controlată).

Tranziții EXPLICITE (nu „update status" generic):
    active     → on_hold    (SAFE, reversibil, NU mișcă bani)   → poate fi autonom
    on_hold    → archived    (MEDIUM, aprobare umană obligatorie) → niciodată auto

Fiecare tranziție validează: tranziție permisă · stare curentă · blocante (escrow/garanție/
task-uri active) · idempotență. După execuție face READ-BACK și scrie în ledger-ul de audit
`project_lifecycle_actions`. Respectă kill-switch-ul existent (`low_risk_autopilot`).
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from db import db

logger = logging.getLogger("propmanage.autonomy.lifecycle")

INACTIVITY_DAYS = 30  # regula existentă `stale_project` — nu inventăm prag nou

# transition → (from_state, to_state, risk_class)
ALLOWED_TRANSITIONS = {
    "active_to_on_hold": ("active", "on_hold", "SAFE"),
    "on_hold_to_archived": ("on_hold", "archived", "MEDIUM"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(dt):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


async def _blockers(proj: dict) -> list[dict]:
    """Blocante REALE, project-scoped (nu inventate). Prezența oricăruia oprește o tranziție sensibilă."""
    blockers = []
    for m in (proj.get("milestones") or []):
        if m.get("status") in ("funded", "warranty_hold"):
            blockers.append({"type": "escrow_active", "detail": f"Tranșă «{m.get('name')}» în stare {m.get('status')} (bani în escrow)."})
        if m.get("warranty_dispute_open"):
            blockers.append({"type": "warranty_dispute", "detail": f"Reclamație de garanție deschisă pe «{m.get('name')}»."})
    pid = str(proj["_id"])
    active_tasks = await db.project_tasks.count_documents({"project_id": pid, "status": {"$nin": ["done"]}})
    if active_tasks > 0:
        blockers.append({"type": "active_tasks", "detail": f"{active_tasks} task-uri active (nefinalizate)."})
    return blockers


async def evaluate_eligibility(proj: dict, transition: str) -> dict:
    """Poate autonomia să facă această tranziție? Determinist + explicabil."""
    if transition not in ALLOWED_TRANSITIONS:
        return {"eligible": False, "reason": "transition_not_allowed", "risk": None, "blockers": []}
    from_state, to_state, risk = ALLOWED_TRANSITIONS[transition]
    signals = []
    if proj.get("status") != from_state:
        return {"eligible": False, "reason": f"wrong_state (e {proj.get('status')}, aștept {from_state})",
                "risk": risk, "from": from_state, "to": to_state, "blockers": []}
    blockers = await _blockers(proj)
    if blockers:
        return {"eligible": False, "reason": "has_blockers", "risk": risk,
                "from": from_state, "to": to_state, "blockers": blockers, "signals": signals}
    if transition == "active_to_on_hold":
        upd = _parse(proj.get("updated_at"))
        if not upd:
            return {"eligible": False, "reason": "no_updated_at", "risk": risk, "from": from_state, "to": to_state, "blockers": []}
        inactive_days = round((datetime.now(timezone.utc) - upd).total_seconds() / 86400.0, 1)
        if inactive_days < INACTIVITY_DAYS:
            return {"eligible": False, "reason": f"not_stale ({inactive_days}z < {INACTIVITY_DAYS}z)",
                    "risk": risk, "from": from_state, "to": to_state, "blockers": [], "inactive_days": inactive_days}
        signals.append(f"inactiv {inactive_days:.0f} zile (≥{INACTIVITY_DAYS})")
        signals.append("fără escrow activ / garanție / task-uri active")
        return {"eligible": True, "reason": "stale_and_clean", "risk": risk, "from": from_state,
                "to": to_state, "blockers": [], "signals": signals, "inactive_days": inactive_days}
    # on_hold → archived: fără blocante, dar tot MEDIUM (aprobare umană)
    signals.append("fără escrow activ / garanție / task-uri active")
    return {"eligible": True, "reason": "clean_for_archive", "risk": risk, "from": from_state,
            "to": to_state, "blockers": [], "signals": signals}


async def _audit(entry: dict) -> None:
    try:
        await db.project_lifecycle_actions.insert_one(entry)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[lifecycle] audit write failed: {e}")


async def transition_project(project_id: str, transition: str, *, actor: dict,
                             autoexec_allowed: bool = True, reason: str = "",
                             human_approved: bool = False) -> dict:
    """Execută o tranziție îngustă, validată, idempotentă, cu read-back + audit.
    Returnează un rezultat structurat (nu ridică excepții pe blocante — le raportează)."""
    if transition not in ALLOWED_TRANSITIONS:
        return {"ok": False, "status": "rejected", "error": "transition_not_allowed"}
    from_state, to_state, risk = ALLOWED_TRANSITIONS[transition]

    try:
        proj = await db.projects.find_one({"_id": ObjectId(project_id)})
    except Exception:  # noqa: BLE001
        return {"ok": False, "status": "rejected", "error": "bad_project_id"}
    if not proj:
        return {"ok": False, "status": "rejected", "error": "project_not_found"}

    prev_status = proj.get("status")
    base_audit = {
        "id": uuid.uuid4().hex, "project_id": project_id, "project_label": proj.get("name") or proj.get("title"),
        "transition": transition, "previous_state": prev_status, "requested_state": to_state,
        "risk": risk, "reason": reason, "actor": actor.get("email") or actor.get("name") or "autonomy",
        "requested_at": _now(),
    }

    # Idempotență: deja în starea țintă
    if prev_status == to_state:
        await _audit({**base_audit, "outcome": "idempotent_noop", "verified": True})
        return {"ok": True, "status": "idempotent", "project_id": project_id, "state": to_state}

    elig = await evaluate_eligibility(proj, transition)
    if not elig["eligible"]:
        await _audit({**base_audit, "outcome": "blocked", "eligibility": elig})
        return {"ok": False, "status": "blocked", "project_id": project_id,
                "reason": elig["reason"], "blockers": elig.get("blockers", []), "eligibility": elig}

    # Risk gating
    if risk == "SAFE":
        if not autoexec_allowed:
            await _audit({**base_audit, "outcome": "blocked_governance", "eligibility": elig})
            return {"ok": False, "status": "blocked_governance", "project_id": project_id,
                    "reason": "low_risk_autopilot OFF"}
    else:  # MEDIUM / HIGH → aprobare umană obligatorie
        if not human_approved:
            await _audit({**base_audit, "outcome": "requires_human_approval", "eligibility": elig})
            return {"ok": False, "status": "requires_human_approval", "project_id": project_id,
                    "risk": risk, "eligibility": elig}

    # EXECUTĂ (mutație îngustă, validată)
    now = _now()
    set_fields = {"status": to_state, "updated_at": now,
                  "lifecycle_previous_status": prev_status,
                  "lifecycle_changed_by": base_audit["actor"],
                  "lifecycle_changed_at": now, "lifecycle_reason": reason}
    if to_state == "archived":
        set_fields["archived_at"] = now
    res = await db.projects.update_one(
        {"_id": ObjectId(project_id), "status": from_state},  # guard: only if still in from_state
        {"$set": set_fields},
    )
    if res.modified_count != 1:
        # cursă / stare schimbată între timp — nu presupunem succesul
        await _audit({**base_audit, "outcome": "execute_no_change", "verified": False})
        return {"ok": False, "status": "execute_failed", "project_id": project_id,
                "reason": "state changed concurrently (guarded update matched 0)"}

    # READ-BACK — nu presupunem că mutația a reușit
    fresh = await db.projects.find_one({"_id": ObjectId(project_id)}, {"status": 1})
    verified = bool(fresh and fresh.get("status") == to_state)
    await _audit({**base_audit, "outcome": "executed", "verified": verified,
                  "actual_state_after": (fresh or {}).get("status"), "executed_at": now,
                  "human_approved": human_approved, "eligibility": elig})
    return {"ok": True, "status": "executed" if verified else "unverified", "project_id": project_id,
            "from": from_state, "to": to_state, "verified": verified, "risk": risk,
            "reversible": (to_state == "on_hold")}


# ═══════════════════════ OBSERVE (pentru loop) ═══════════════════════
async def observe_stale_projects_for_lifecycle(limit: int = 5) -> list[dict]:
    """Proiecte active + stale, eligibile pentru active→on_hold (SAFE). Bounded."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=INACTIVITY_DAYS)).isoformat()
    out = []
    async for p in db.projects.find({"status": "active", "updated_at": {"$lt": cutoff}}).limit(limit):
        elig = await evaluate_eligibility(p, "active_to_on_hold")
        out.append({"project_id": str(p["_id"]), "label": p.get("name") or p.get("title"),
                    "eligibility": elig})
    return out


# ═══════════════════════ QUEUE + METRICS ═══════════════════════
async def lifecycle_queue_items(limit: int = 15) -> list[dict]:
    """Acțiuni de lifecycle recente din ledger → coada Autonomy Activity."""
    items = []
    async for a in db.project_lifecycle_actions.find({}, {"_id": 0}).sort("requested_at", -1).limit(limit):
        outcome = a.get("outcome")
        cat = {"executed": "DID", "idempotent_noop": "DID", "requires_human_approval": "NEEDS_HUMAN",
               "blocked": "NEEDS_HUMAN", "blocked_governance": "BLOCKED"}.get(outcome, "FAILED")
        items.append({
            "source": "project_lifecycle", "category": cat, "priority": "medium",
            "confidence": None,
            "proposed_action": f"{a.get('transition')} · «{a.get('project_label')}»",
            "status": outcome, "timestamp": a.get("requested_at"),
            "result": f"{a.get('previous_state')} → {a.get('actual_state_after') or a.get('requested_state')}"
                      + (" (verificat)" if a.get("verified") else ""),
            "project_id": a.get("project_id"),
            "escalation_reason": ("; ".join(b.get("detail", "") for b in (a.get("eligibility") or {}).get("blockers", []))
                                  or ("Arhivarea necesită aprobare umană." if outcome == "requires_human_approval" else None)),
        })
    return items


async def lifecycle_metrics() -> dict:
    total = await db.project_lifecycle_actions.count_documents({})
    executed = await db.project_lifecycle_actions.count_documents({"outcome": "executed", "verified": True})
    on_hold_auto = await db.project_lifecycle_actions.count_documents({"transition": "active_to_on_hold", "outcome": "executed", "verified": True})
    archived_via_approval = await db.project_lifecycle_actions.count_documents({"transition": "on_hold_to_archived", "outcome": "executed", "verified": True})
    awaiting_approval = await db.project_lifecycle_actions.count_documents({"outcome": "requires_human_approval"})
    blocked = await db.project_lifecycle_actions.count_documents({"outcome": {"$in": ["blocked", "blocked_governance"]}})
    return {
        "lifecycle_actions_total": total,
        "lifecycle_executed_verified": executed,
        "lifecycle_on_hold_autonomous": on_hold_auto,
        "lifecycle_archived_after_approval": archived_via_approval,
        "lifecycle_awaiting_human_approval": awaiting_approval,
        "lifecycle_blocked": blocked,
    }
