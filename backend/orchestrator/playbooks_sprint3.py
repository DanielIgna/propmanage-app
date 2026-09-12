"""Autonomy Orchestrator — Sprint 3 playbooks (Blueprint: Autonomy Engine 2.0).

8. pattern_scan       → Pattern Hunter: detectează tipare recurente în date (rule-based)
9. finance_reconcile  → Finance Reconciler: reconciliere zilnică wallets/tranzacții/escrow
10. roadmap_advise    → Roadmap Advisor: Claude propune top 3 priorități de roadmap (săptămânal)
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from db import db

logger = logging.getLogger("propmanage.orchestrator.sprint3")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


# ============================================================================
# 8. PATTERN HUNTER — tipare recurente în datele platformei
# ============================================================================
async def handle_pattern_scan(payload: dict) -> dict:
    from orchestrator.engine import notify_admins
    steps_log = []
    findings = []

    # a) Demand surge: categorii cu cereri 7z > 2× media săptămânală (28z precedente)
    last7, prev28 = {}, {}
    async for row in db.requests.aggregate([
        {"$match": {"created_at": {"$gte": _days_ago(7)}}},
        {"$group": {"_id": "$category", "n": {"$sum": 1}}},
    ]):
        last7[row["_id"]] = row["n"]
    async for row in db.requests.aggregate([
        {"$match": {"created_at": {"$gte": _days_ago(35), "$lt": _days_ago(7)}}},
        {"$group": {"_id": "$category", "n": {"$sum": 1}}},
    ]):
        prev28[row["_id"]] = row["n"]
    for cat, n in last7.items():
        weekly_avg = prev28.get(cat, 0) / 4
        if n >= 3 and n > 2 * max(weekly_avg, 0.5):
            findings.append({
                "kind": "demand_surge", "severity": "info",
                "detail": f"Cerere în creștere pe «{cat}»: {n} cereri/7z vs medie {weekly_avg:.1f}/săpt. Verifică acoperirea cu specialiști.",
            })
    steps_log.append({"action": "scan_demand_surge", "ok": True,
                      "detail": f"{len([f for f in findings if f['kind'] == 'demand_surge'])} categorii cu cerere în creștere"})

    # b) Dispute hotspot: specialiști cu 2 dispute deschise/30z (early-warning, sub pragul Medic)
    from bson import ObjectId
    per_spec = {}
    async for d in db.disputes.find({"status": "open", "created_at": {"$gte": _days_ago(30)}}, {"request_id": 1}):
        try:
            req = await db.requests.find_one({"_id": ObjectId(d["request_id"])}, {"specialist_id": 1})
        except Exception:  # noqa: BLE001
            req = None
        sid = (req or {}).get("specialist_id")
        if sid:
            per_spec[sid] = per_spec.get(sid, 0) + 1
    hotspots = {sid: n for sid, n in per_spec.items() if n == 2}
    for sid, n in list(hotspots.items())[:5]:
        try:
            u = await db.users.find_one({"_id": ObjectId(sid)}, {"name": 1})
        except Exception:  # noqa: BLE001
            u = None
        findings.append({
            "kind": "dispute_hotspot", "severity": "warning",
            "detail": f"Specialist «{(u or {}).get('name') or sid}» are {n} dispute deschise/30z — la o dispută de suspendarea Medic. Recomandă mediere proactivă.",
        })
    steps_log.append({"action": "scan_dispute_hotspots", "ok": True, "detail": f"{len(hotspots)} specialiști în zona de risc"})

    # c) Cerere stagnantă: cereri deschise >7 zile fără specialist asignat
    stale = await db.requests.count_documents({
        "status": "open", "specialist_id": {"$in": [None, ""]}, "created_at": {"$lt": _days_ago(7)},
    })
    if stale:
        findings.append({
            "kind": "stale_demand", "severity": "warning",
            "detail": f"{stale} cereri deschise de peste 7 zile fără specialist — clienți în risc de abandon. Verifică matching-ul.",
        })
    steps_log.append({"action": "scan_stale_demand", "ok": True, "detail": f"{stale} cereri stagnante"})

    # d) Supply gap (Autonomy 2.0): categorii cu cerere reală în 30z dar zero specialiști activi
    demand30 = {}
    async for row in db.requests.aggregate([
        {"$match": {"created_at": {"$gte": _days_ago(30)}}},
        {"$group": {"_id": "$category", "n": {"$sum": 1}}},
    ]):
        if row["_id"]:
            demand30[row["_id"]] = row["n"]
    supply = {}
    async for u in db.users.find(
        {"role": "specialist", "deleted": {"$ne": True}, "banned": {"$ne": True}},
        {"specialty": 1, "service_categories": 1},
    ):
        for c in {u.get("specialty"), *(u.get("service_categories") or [])}:
            if c:
                supply[c] = supply.get(c, 0) + 1
    gaps = [(cat, n) for cat, n in demand30.items() if n >= 3 and supply.get(cat, 0) == 0]
    for cat, n in sorted(gaps, key=lambda x: -x[1])[:3]:
        findings.append({
            "kind": "supply_gap", "severity": "warning",
            "detail": f"Gol de ofertă pe «{cat}»: {n} cereri/30z și ZERO specialiști activi — prioritate de recrutare marketplace.",
        })
    steps_log.append({"action": "scan_supply_gap", "ok": True, "detail": f"{len(gaps)} categorii fără acoperire"})

    # e) Churn risk (Autonomy 2.0): specialiști VERIFIED/PREMIUM inactivi de 21+ zile
    churn_cutoff = _days_ago(21)
    churn = await db.users.find(
        {"role": "specialist", "tier": {"$in": ["VERIFIED", "PREMIUM"]}, "banned": {"$ne": True},
         "deleted": {"$ne": True}, "last_seen": {"$lt": churn_cutoff}},
        {"name": 1, "tier": 1, "last_seen": 1},
    ).sort("last_seen", 1).to_list(50)
    if len(churn) >= 2:
        names = ", ".join((u.get("name") or "—") for u in churn[:3])
        findings.append({
            "kind": "churn_risk", "severity": "warning",
            "detail": f"{len(churn)} specialiști {('VERIFIED/PREMIUM')} inactivi de 21+ zile (ex: {names}) — risc de churn, campanie de reactivare recomandată.",
        })
    steps_log.append({"action": "scan_churn_risk", "ok": True, "detail": f"{len(churn)} specialiști premium inactivi 21z+"})

    if not payload.get("test") and findings:
        await db.pattern_findings.insert_one({
            "id": uuid.uuid4().hex, "ts": _now(), "findings": findings, "trigger": payload.get("trigger", "manual"),
        })
        await notify_admins(
            "🔎 Pattern Hunter: tipare detectate",
            " · ".join(f["detail"][:90] for f in findings[:3]),
            link="/admin/orchestrator",
        )
    steps_log.append({
        "action": "report_findings", "ok": True,
        "detail": f"{len(findings)} tipare" + (" (SIMULARE — fără scriere)" if payload.get("test") else ""),
    })
    return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 20 if findings else 5, "escalate": False}


async def count_orphan_transactions(days: int = 30) -> list:
    """Tranzacții recente cu request_id către cereri inexistente. Returnează listă de _id-uri."""
    from bson import ObjectId
    orphan_ids = []
    async for t in db.transactions.find(
        {"request_id": {"$nin": [None, ""]}, "created_at": {"$gte": _days_ago(days)},
         "reconciliation.status": {"$exists": False}},
        {"request_id": 1},
    ).sort("_id", -1).limit(500):
        rid = t["request_id"]
        found = await db.requests.count_documents({"id": rid}, limit=1)
        if not found:
            try:
                found = await db.requests.count_documents({"_id": ObjectId(rid)}, limit=1)
            except Exception:  # noqa: BLE001
                found = 0
        if not found:
            orphan_ids.append(t["_id"])
    return orphan_ids


# ============================================================================
# 9. FINANCE RECONCILER — reconciliere zilnică
# ============================================================================
async def handle_finance_reconcile(payload: dict) -> dict:
    from orchestrator.engine import notify_admins
    steps_log = []
    issues = []

    # a) Solduri negative
    neg = await db.users.count_documents({"wallet_balance": {"$lt": 0}})
    if neg:
        issues.append(f"{neg} utilizatori cu sold negativ în wallet")
    steps_log.append({"action": "check_negative_balances", "ok": neg == 0, "detail": f"{neg} solduri negative"})

    # b) Tranzacții recente orfane (30z, request_id către cereri inexistente)
    orphans = len(await count_orphan_transactions(30))
    if orphans:
        issues.append(f"{orphans} tranzacții orfane (cereri inexistente) în ultimele 30 zile")
    steps_log.append({"action": "check_orphan_transactions", "ok": orphans == 0, "detail": f"{orphans} tranzacții orfane (30z)"})

    # c) Lucrări confirmate (30z) fără nicio tranzacție asociată
    unpaid = 0
    async for r in db.requests.find({"status": "confirmed", "created_at": {"$gte": _days_ago(30)}}, {"id": 1}).limit(300):
        rid = str(r.get("id") or r["_id"])
        has_tx = await db.transactions.count_documents({"request_id": rid}, limit=1)
        if not has_tx:
            unpaid += 1
    if unpaid:
        issues.append(f"{unpaid} lucrări confirmate (30z) fără tranzacție asociată")
    steps_log.append({"action": "check_confirmed_without_tx", "ok": unpaid == 0, "detail": f"{unpaid} lucrări confirmate fără tranzacție"})

    escalate = bool(issues)
    if escalate and not payload.get("test"):
        await notify_admins("💰 Finance Reconciler: discrepanțe detectate", " · ".join(issues), link="/admin?tab=finance")
    steps_log.append({
        "action": "reconciliation_verdict", "ok": not escalate,
        "detail": ("CURAT — toate verificările au trecut" if not escalate else f"{len(issues)} discrepanțe: {' · '.join(issues)}")
                  + (" (SIMULARE)" if payload.get("test") else ""),
    })
    return {"steps": steps_log, "outcome": "escalated" if escalate else "auto_resolved",
            "minutes_saved": 15, "escalate": escalate}


# ============================================================================
# 10. ROADMAP ADVISOR — Claude propune priorități (săptămânal)
# ============================================================================
async def handle_roadmap_advise(payload: dict) -> dict:
    from orchestrator.engine import notify_admins
    steps_log = []

    ledger = await db.orchestrator_ledger.find(
        {"test": {"$ne": True}, "ts": {"$gte": _days_ago(7)}},
        {"_id": 0, "playbook_name": 1, "outcome": 1, "escalated": 1},
    ).to_list(1000)
    by_pb = {}
    for x in ledger:
        k = x.get("playbook_name") or "—"
        by_pb.setdefault(k, {"runs": 0, "escalated": 0})
        by_pb[k]["runs"] += 1
        by_pb[k]["escalated"] += 1 if x.get("escalated") else 0
    latest_patterns = await db.pattern_findings.find({}, {"_id": 0}).sort("ts", -1).limit(2).to_list(2)
    pulse = {
        "open_requests": await db.requests.count_documents({"status": "open"}),
        "kyc_pending": await db.users.count_documents({"kyc_status": "pending"}),
        "disputes_open": await db.disputes.count_documents({"status": "open"}),
    }
    steps_log.append({"action": "collect_context", "ok": True,
                      "detail": f"{len(ledger)} intrări ledger 7z · {len(latest_patterns)} rapoarte Pattern Hunter · pulse {pulse}"})

    if payload.get("test"):
        steps_log.append({"action": "llm_advise", "ok": True, "detail": "SIMULARE — apelul Claude a fost sărit (mod test)"})
        return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 0, "escalate": False}

    try:
        from orchestrator.llm import claude_json
        context = {
            "playbook_activity_7d": by_pb,
            "pattern_findings": [f for p in latest_patterns for f in p.get("findings", [])][:10],
            "pulse": pulse,
        }
        result = await claude_json(
            system=("Ești Roadmap Advisor pentru PropManage (Property Intelligence OS, marketplace de lucrări + "
                    "administrare imobile din România). Primești activitatea platformei și propui priorități de produs. "
                    "Răspunde STRICT JSON: {\"priorities\": [{\"titlu\": str, \"argument\": str, \"impact\": str}]} — exact 3 priorități, în română."),
            prompt=f"Context săptămânal:\n{context}\n\nPropune top 3 priorități de roadmap pentru săptămâna viitoare.",
            session_prefix="roadmap-advisor",
        )
        priorities = (result or {}).get("priorities") or []
        if not priorities:
            raise ValueError("Claude nu a returnat priorități")
        await db.roadmap_advice.insert_one({
            "id": uuid.uuid4().hex, "ts": _now(), "priorities": priorities[:3], "context_pulse": pulse,
        })
        steps_log.append({"action": "llm_advise", "ok": True,
                          "detail": " · ".join(p.get("titlu", "?") for p in priorities[:3])})
        await notify_admins(
            "🧭 Roadmap Advisor: prioritățile săptămânii",
            " · ".join(p.get("titlu", "?") for p in priorities[:3]),
            link="/admin/orchestrator",
        )
        return {"steps": steps_log, "outcome": "auto_resolved", "minutes_saved": 45, "escalate": False}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[roadmap-advisor] LLM fail: {e}")
        steps_log.append({"action": "llm_advise", "ok": False, "detail": f"Eșec Claude: {e}"})
        return {"steps": steps_log, "outcome": "escalated", "minutes_saved": 0, "escalate": True}


# ============================================================================
# CRONS
# ============================================================================
async def pattern_hunter_cron() -> None:
    """Luni 06:00 — săptămânal."""
    from orchestrator.engine import emit_signal
    await emit_signal("pattern_scan", {"trigger": "cron_mon_0600"})


async def finance_reconciler_cron() -> None:
    """Zilnic 04:50."""
    from orchestrator.engine import emit_signal
    await emit_signal("finance_reconcile", {"trigger": "cron_0450"})


async def roadmap_advisor_cron() -> None:
    """Vineri 09:00 — săptămânal."""
    from orchestrator.engine import emit_signal
    await emit_signal("roadmap_advise", {"trigger": "cron_fri_0900"})


SPRINT3_PLAYBOOKS = {
    "pattern_scan": {
        "id": "pattern_hunter",
        "name": "Pattern Hunter",
        "description": "Săptămânal (luni 06:00): scanează datele pentru tipare recurente — cerere în creștere pe categorii, specialiști aproape de pragul Medic, cereri stagnante fără specialist. Findings → notificare admin + arhivă (~20 min/scan).",
        "handler": handle_pattern_scan,
    },
    "finance_reconcile": {
        "id": "finance_reconciler",
        "name": "Finance Reconciler",
        "description": "Zilnic 04:50: reconciliere financiară — solduri negative, tranzacții orfane, lucrări confirmate fără plată. Curat → ledger; discrepanțe → escaladare cu detalii (~15 min/zi).",
        "handler": handle_finance_reconcile,
    },
    "roadmap_advise": {
        "id": "roadmap_advisor",
        "name": "Roadmap Advisor",
        "description": "Săptămânal (vineri 09:00): Claude analizează activitatea playbook-urilor, tiparele și pulse-ul platformei și propune top 3 priorități de roadmap, salvate + notificate adminilor (~45 min/săpt).",
        "handler": handle_roadmap_advise,
    },
}
