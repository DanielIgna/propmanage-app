"""Autonomy Activity — read-model UNIFICAT peste infrastructura existentă.

NU e un sistem paralel și NU o nouă mașină de stări: doar proiectează artefactele
DEJA existente (admin_ai_findings, admin_todos, admin_approvals, autonomy_loop_runs,
playbook_executions, ai_memories, semnalele de bottleneck din engine) într-o singură
COADĂ de acțiuni + metrici REALE de autonomie.

Categorii (pentru dashboard):
  DID          — autonomia a executat + verificat
  WAITING      — pornit/în curs, așteaptă un pas ulterior (ex: recomandări de materializat)
  FAILED       — a eșuat / neverificat / auto-approve eșuat
  NEEDS_HUMAN  — escaladat la om (aprobare, anomalie audit, regulă oprită, dispută)
  LEARNED      — outcome verificat devenit cunoștință reutilizabilă
  BLOCKED      — blocat de guvernanță (kill-switch OFF)
"""
import logging
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.autonomy.activity")

QUEUE_CAP = 60


def _parse(dt) -> datetime | None:
    if not dt:
        return None
    try:
        s = dt if isinstance(dt, str) else str(dt)
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _minutes_between(a, b) -> float | None:
    da, db_ = _parse(a), _parse(b)
    if not da or not db_:
        return None
    return round(abs((db_ - da).total_seconds()) / 60.0, 1)


# ═══════════════════════ ACTION QUEUE ═══════════════════════
async def build_action_queue() -> dict:
    """Proiectează artefactele existente într-o coadă unică cu:
    source · priority · confidence · proposed_action · status · result · timestamp · escalation_reason."""
    items: list[dict] = []

    # 1) Findings cu acțiune autonomă (loop + knowledge center)
    cur = db.admin_ai_findings.find(
        {"autonomy_action": {"$exists": True}}, {"_id": 0}
    ).sort("last_seen_at", -1).limit(40)
    async for f in cur:
        a = f.get("autonomy_action") or {}
        atype = a.get("type")
        base = {
            "source": f.get("source") or "knowledge_center",
            "priority": "medium" if f.get("severity") == "medium" else "low",
            "confidence": f.get("confidence"),
            "proposed_action": f.get("recommended_action") or f.get("description"),
            "timestamp": a.get("at") or f.get("resolved_at") or f.get("last_seen_at"),
            "finding_key": f.get("composite_key"),
            "route": f.get("affected_route") or f.get("entity_id"),
            "detector": f.get("pattern"),
        }
        if atype == "todo":
            todo = await db.admin_todos.find_one({"id": a.get("todo_id")}, {"_id": 0, "done": 1})
            verified = todo is not None
            items.append({**base, "category": "DID",
                          "status": "executed+verified" if verified else "executed",
                          "result": f"Task de remediere creat ({'verificat' if verified else 'neverificat'}).",
                          "todo_id": a.get("todo_id"), "escalation_reason": None})
        elif atype == "approval":
            ap = await db.admin_approvals.find_one({"id": a.get("approval_id")}, {"_id": 0, "status": 1})
            st = (ap or {}).get("status", "pending")
            items.append({**base, "category": "NEEDS_HUMAN" if st == "pending" else "DID",
                          "status": st,
                          "result": "Așteaptă aprobare umană (MEDIUM/HIGH)." if st == "pending" else f"Aprobare {st}.",
                          "approval_id": a.get("approval_id"),
                          "escalation_reason": "Risc MEDIU/RIDICAT → decizie umană obligatorie." if st == "pending" else None})
        elif atype == "blocked_governance":
            items.append({**base, "category": "BLOCKED", "status": "blocked",
                          "result": "Blocat de guvernanță (autopilot OFF).",
                          "escalation_reason": a.get("reason") or "low_risk_autopilot OFF."})

    # 2) Approvals pending care NU sunt legate de un finding de mai sus
    seen_appr = {i.get("approval_id") for i in items if i.get("approval_id")}
    cur = db.admin_approvals.find({"status": "pending"}, {"_id": 0}).sort("created_at", -1).limit(20)
    async for ap in cur:
        if ap.get("id") in seen_appr:
            continue
        items.append({
            "source": "approval", "priority": "medium", "confidence": None,
            "proposed_action": (ap.get("payload") or {}).get("recommended_action") or ap.get("action"),
            "status": "pending", "category": "NEEDS_HUMAN",
            "result": "Așteaptă aprobare umană.", "timestamp": ap.get("created_at"),
            "approval_id": ap.get("id"), "finding_key": ap.get("finding_key"),
            "escalation_reason": ap.get("reason") or "Necesită aprobare umană.",
        })

    # 3) Semnale de bottleneck (din aceleași surse ca scorul Human Dependency)
    h48 = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # 3a) Cereri >48h — escaladate autonom (DID) vs neescaladate (NEEDS_HUMAN)
    esc = await db.requests.count_documents({"status": {"$in": ["open", "pending"]}, "created_at": {"$lt": h48}, "autonomy_escalated_at": {"$exists": True}})
    not_esc = await db.requests.count_documents({"status": {"$in": ["open", "pending"]}, "created_at": {"$lt": h48}, "autonomy_escalated_at": {"$exists": False}})
    if esc:
        items.append({"source": "request_bottleneck", "priority": "medium", "confidence": 0.9,
                      "proposed_action": "Re-notificare specialiști pentru cereri stale (>24h fără oferte).",
                      "status": "escalated", "category": "DID",
                      "result": f"{esc} cereri escaladate autonom (boost vizibilitate).",
                      "timestamp": None, "escalation_reason": None, "count": esc})
    if not_esc:
        items.append({"source": "request_bottleneck", "priority": "high", "confidence": None,
                      "proposed_action": "Cereri deschise >48h fără procesare autonomă.",
                      "status": "waiting", "category": "NEEDS_HUMAN",
                      "result": f"{not_esc} cereri așteaptă (sub 48h de la escaladare sau au deja oferte).",
                      "timestamp": None, "escalation_reason": "Necesită atenție/decizie umană.", "count": not_esc})

    # 3b) Reguli de automatizare oprite → DOAR escaladare (niciodată auto-repornire)
    rules_off = await db.automation_rules.count_documents({"enabled": False})
    if rules_off:
        items.append({"source": "automation_rule", "priority": "high", "confidence": None,
                      "proposed_action": "Revizuiește regulile de automatizare oprite (repornirea schimbă comportament).",
                      "status": "disabled", "category": "NEEDS_HUMAN",
                      "result": f"{rules_off} reguli oprite.", "timestamp": None,
                      "escalation_reason": "Repornirea unei reguli schimbă comportamentul platformei → decizie umană.", "count": rules_off})

    # 3c) Anomalii audit deschise → DOAR escaladare (sensibil la securitate)
    anomalies = await db.audit_anomalies.count_documents({"resolved": False})
    if anomalies:
        items.append({"source": "audit_anomaly", "priority": "critical", "confidence": None,
                      "proposed_action": "Investighează anomaliile de audit.",
                      "status": "open", "category": "NEEDS_HUMAN",
                      "result": f"{anomalies} anomalii deschise.", "timestamp": None,
                      "escalation_reason": "Sensibil la securitate → niciodată auto-acționat.", "count": anomalies})

    # 3d) Dispute deschise → escaladare
    disputes = await db.disputes.count_documents({"status": {"$in": ["open", "pending", "in_review"]}})
    if disputes:
        items.append({"source": "dispute", "priority": "high", "confidence": None,
                      "proposed_action": "Triază disputele deschise.",
                      "status": "open", "category": "NEEDS_HUMAN",
                      "result": f"{disputes} dispute.", "timestamp": None,
                      "escalation_reason": "Decizie umană (legal/financiar).", "count": disputes})

    # 3e) Recomandări AI pending → auto-materialize le transformă în TODO (WAITING)
    recos_doc = await db.command_center_recos.find_one({"_id": "latest"})
    recos_pending = sum(1 for r in (recos_doc or {}).get("recommendations", []) if not r.get("done")) if recos_doc else 0
    if recos_pending:
        items.append({"source": "ai_recommendation", "priority": "medium", "confidence": None,
                      "proposed_action": "Recomandări AI de materializat în TODO (job zilnic auto-materialize).",
                      "status": "pending_materialization", "category": "WAITING",
                      "result": f"{recos_pending} recomandări în așteptare.", "timestamp": None,
                      "escalation_reason": None, "count": recos_pending})

    # 4) Cunoștințe învățate din outcomes verificate (LEARNED)
    learned_recent = db.ai_memories.find(
        {"source": "verified_outcome"}, {"_id": 0, "summary": 1, "created_at": 1, "meta": 1}
    ).sort("created_at", -1).limit(10)
    async for m in learned_recent:
        items.append({"source": "verified_outcome", "priority": "low", "confidence": None,
                      "proposed_action": m.get("summary"), "status": "learned", "category": "LEARNED",
                      "result": "Memorie operațională reutilizabilă (din outcome verificat).",
                      "timestamp": m.get("created_at"),
                      "finding_key": (m.get("meta") or {}).get("finding_key"), "escalation_reason": None})

    # 5) Eșecuri recente (self-driving jobs cu status error)
    fails = db.playbook_executions.find(
        {"playbook_id": {"$regex": "^self_driving:"}, "status": "error"}, {"_id": 0}
    ).sort("ts", -1).limit(8)
    async for pe in fails:
        items.append({"source": pe.get("playbook_id"), "priority": "high", "confidence": None,
                      "proposed_action": "Job self-driving eșuat — necesită verificare.",
                      "status": "error", "category": "FAILED",
                      "result": str((pe.get("detail") or {}).get("error") or "eroare")[:160],
                      "timestamp": pe.get("ts"), "escalation_reason": "Eșec autonom → verificare umană."})

    # counts + cap
    counts = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    return {"queue": items[:QUEUE_CAP], "counts": counts, "total": len(items)}


# ═══════════════════════ REAL AUTONOMY METRICS ═══════════════════════
async def compute_activity_metrics(days: int = 90) -> dict:
    """Metrici REALE, derivate STRICT din ledgerele existente (fără inventare)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    autonomous_total = autonomous_verified = autonomous_failures = 0
    human_escalations = blocked = 0
    loop_runs = 0

    async for run in db.autonomy_loop_runs.find({"started_at": {"$gte": since}}, {"_id": 0, "steps": 1}):
        loop_runs += 1
        for st in run.get("steps") or []:
            act = st.get("action") or {}
            atype = act.get("type")
            if atype == "blocked_governance":
                blocked += 1
                continue
            if st.get("human_gate"):
                human_escalations += 1
                continue
            # acțiune autonomă (SAFE todo) — numărăm doar execuțiile propriu-zise (nu reused/no_change)
            if atype == "todo" and st.get("actor") == "autonomous":
                autonomous_total += 1
                if (st.get("verify") or {}).get("ok"):
                    autonomous_verified += 1
                else:
                    autonomous_failures += 1
            elif st.get("error"):
                autonomous_failures += 1

    # Self-driving jobs (autonome, non-loop): aplicate vs eșuate
    sd_applied = await db.playbook_executions.count_documents({"playbook_id": {"$regex": "^self_driving:"}, "status": "applied", "ts": {"$gte": since}})
    sd_errors = await db.playbook_executions.count_documents({"playbook_id": {"$regex": "^self_driving:"}, "status": "error", "ts": {"$gte": since}})

    # Recomandări (aprobări = propuneri MEDIUM executate/pending/respinse)
    rec_executed = await db.admin_approvals.count_documents({"status": {"$in": ["executed", "approved"]}})
    rec_pending = await db.admin_approvals.count_documents({"status": "pending"})
    rec_rejected = await db.admin_approvals.count_documents({"status": "rejected"})
    # verificate = aprobările executate al căror finding e rezolvat
    rec_verified = 0
    async for ap in db.admin_approvals.find({"status": {"$in": ["executed", "approved"]}}, {"_id": 0, "finding_key": 1}):
        key = ap.get("finding_key")
        if key:
            f = await db.admin_ai_findings.find_one({"composite_key": key, "status": "resolved"}, {"_id": 1})
            if f:
                rec_verified += 1

    # Reversări = aprobări respinse + auto-approve eșuate (note „eșuat")
    reversal_failed = await db.admin_approvals.count_documents({"status": "pending", "note": {"$regex": "eșuat|failed", "$options": "i"}})
    actions_requiring_reversal = rec_rejected + reversal_failed

    # Timp mediu de rezolvare (findings rezolvate autonom)
    durations = []
    async for f in db.admin_ai_findings.find(
        {"autonomy_action": {"$exists": True}, "status": {"$in": ["resolved", "triaged"]}, "resolved_at": {"$exists": True}},
        {"_id": 0, "first_seen_at": 1, "resolved_at": 1},
    ).limit(200):
        d = _minutes_between(f.get("first_seen_at"), f.get("resolved_at"))
        if d is not None:
            durations.append(d)
    avg_resolution_min = round(sum(durations) / len(durations), 1) if durations else None

    knowledge_records = await db.ai_memories.count_documents({"source": "verified_outcome"})

    total_actions = autonomous_total + sd_applied
    resolution_rate = round(autonomous_verified / autonomous_total * 100, 1) if autonomous_total else None
    escalation_denom = autonomous_total + human_escalations + blocked
    escalation_rate = round(human_escalations / escalation_denom * 100, 1) if escalation_denom else None

    return {
        "window_days": days,
        "loop_runs": loop_runs,
        "autonomous_actions_total": total_actions,
        "autonomous_actions_loop": autonomous_total,
        "self_driving_actions_applied": sd_applied,
        "autonomous_actions_verified": autonomous_verified,
        "autonomous_resolution_rate_pct": resolution_rate,
        "human_escalations": human_escalations,
        "human_escalation_rate_pct": escalation_rate,
        "autonomous_failures": autonomous_failures + sd_errors,
        "blocked_by_governance": blocked,
        "actions_requiring_reversal": actions_requiring_reversal,
        "avg_resolution_time_min": avg_resolution_min,
        "recommendations_executed": rec_executed,
        "recommendations_verified": rec_verified,
        "recommendations_pending": rec_pending,
        "recommendations_rejected": rec_rejected,
        "knowledge_records_from_verified_outcomes": knowledge_records,
    }


async def get_activity() -> dict:
    """Read-model unificat: metrici + coadă. Include extinderile dispute + lifecycle
    (aceeași coadă unică — fără al 2-lea sistem)."""
    from autonomy import disputes as D
    from autonomy import lifecycle as LC

    base = await build_action_queue()
    metrics = await compute_activity_metrics()

    dispute_items = await D.dispute_queue_items()
    lifecycle_items = await LC.lifecycle_queue_items()
    # înlocuim placeholder-ul agregat de dispute (din bottleneck) cu itemii triați reali
    queue = [it for it in base["queue"] if it.get("source") != "dispute"] + dispute_items + lifecycle_items

    counts = {}
    for it in queue:
        counts[it["category"]] = counts.get(it["category"], 0) + 1

    metrics["disputes"] = await D.dispute_metrics()
    metrics["lifecycle"] = await LC.lifecycle_metrics()
    try:
        from routes.attribution import compute_attribution_summary
        metrics["attribution"] = await compute_attribution_summary(30)
    except Exception:  # noqa: BLE001
        metrics["attribution"] = None

    return {"metrics": metrics, "queue": queue[:QUEUE_CAP + 40], "counts": counts, "total": len(queue)}
