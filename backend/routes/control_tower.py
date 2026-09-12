"""Executive Control Tower v1 (Blueprint Phase 2, §2.4).

„Adminul nu mai caută probleme; problemele vin sortate, cu soluția atașată."
- Attention Layer: top decizii care cer om AZI (escaladări, KYC, dispute, categorii fără supply, retry queue)
- Pulse: KPI operaționale
- Autonomy Report: ce a rezolvat platforma singură (retroactiv)
Schema fixă recomandare (Blueprint §8): {situatie, propunere, impact_estimat, actiune_1tap, sursa_semnalului}
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/control-tower", tags=["control-tower"])


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


@router.get("")
async def control_tower(user=Depends(require_role("admin"))):
    attention = []

    # 1. Escaladări orchestrator (7 zile, non-test)
    escalations = await db.orchestrator_ledger.find(
        {"escalated": True, "test": {"$ne": True}, "ts": {"$gte": _iso_days_ago(7)}},
        {"_id": 0, "playbook_name": 1, "signal_kind": 1, "ts": 1},
    ).sort("ts", -1).to_list(50)
    if escalations:
        kinds = {}
        for e in escalations:
            kinds[e.get("playbook_name") or e.get("signal_kind") or "necunoscut"] = kinds.get(e.get("playbook_name") or e.get("signal_kind") or "necunoscut", 0) + 1
        top = max(kinds, key=kinds.get)
        attention.append({
            "id": "orchestrator_escalations", "severity": "critical",
            "situatie": f"{len(escalations)} escaladări din Autonomy Orchestrator în ultimele 7 zile",
            "propunere": f"Revizuiește escaladările — cele mai frecvente: «{top}» ({kinds[top]}×)",
            "impact_estimat": "Deblochezi fluxurile pe care AI-ul nu le poate închide singur",
            "actiune_1tap": {"label": "Deschide Orchestrator", "route": "/admin/orchestrator"},
            "sursa_semnalului": "orchestrator_ledger",
            "count": len(escalations),
        })

    # 2. KYC în așteptare (AI recommendation e deja atașată în coadă)
    kyc_pending = await db.users.count_documents({"kyc_status": "pending"})
    if kyc_pending:
        attention.append({
            "id": "kyc_pending", "severity": "warning",
            "situatie": f"{kyc_pending} verificări KYC așteaptă review uman",
            "propunere": "Aprobă/respinge cu recomandarea AI atașată fiecărui dosar",
            "impact_estimat": "Utilizatori deblocați → conversie mai rapidă în marketplace",
            "actiune_1tap": {"label": "Deschide coada KYC", "route": "/admin?tab=kyc"},
            "sursa_semnalului": "users.kyc_status",
            "count": kyc_pending,
        })

    # 3. Dispute deschise (cu propunerea AI Triage când există)
    disputes_open = await db.disputes.count_documents({"status": "open"})
    if disputes_open:
        triaged = await db.disputes.count_documents({"status": "open", "ai_triage": {"$exists": True}})
        attention.append({
            "id": "disputes_open", "severity": "critical",
            "situatie": f"{disputes_open} dispute deschise așteaptă mediere",
            "propunere": f"{triaged} au deja propunere AI de împărțire (split) — confirmă sau ajustează" if triaged else "Rulează AI Triage pentru propuneri de mediere",
            "impact_estimat": "Escrow deblocat + încredere păstrată de ambele părți",
            "actiune_1tap": {"label": "Deschide Dispute", "route": "/admin?tab=disputes"},
            "sursa_semnalului": "disputes + ai_triage",
            "count": disputes_open,
        })

    # 4. Categorii cu cerere fără supply (hidden-with-potential, CIP-A)
    taxonomy = await db.construction_taxonomy.find({"depth_level": 0}, {"_id": 0, "name": 1, "legacy_category": 1, "is_active": 1}).to_list(100)
    if taxonomy:
        since = _iso_days_ago(90)
        demand = {}
        async for row in db.requests.aggregate([
            {"$match": {"created_at": {"$gte": since}}},
            {"$group": {"_id": "$category", "n": {"$sum": 1}}},
        ]):
            demand[row["_id"]] = row["n"]
        supply = {}
        async for row in db.users.aggregate([
            {"$match": {"role": "specialist", "deleted": {"$ne": True}}},
            {"$group": {"_id": "$specialty", "n": {"$sum": 1}}},
        ]):
            supply[row["_id"]] = row["n"]
        gaps = [
            {"name": t["name"], "requests": demand.get(t.get("legacy_category"), 0)}
            for t in taxonomy
            if demand.get(t.get("legacy_category"), 0) > 0 and supply.get(t.get("legacy_category"), 0) == 0
        ]
        if gaps:
            gaps.sort(key=lambda g: -g["requests"])
            top_gap = gaps[0]
            attention.append({
                "id": "demand_no_supply", "severity": "warning",
                "situatie": f"{len(gaps)} categorii au cerere dar zero specialiști",
                "propunere": f"Pornește recrutare pentru «{top_gap['name']}» ({top_gap['requests']} cereri/90z) — funnel-ul e gata în CIP",
                "impact_estimat": "Cerere pierdută transformată în GMV",
                "actiune_1tap": {"label": "Deschide Construction Intelligence", "route": "/admin/construction"},
                "sursa_semnalului": "construction_taxonomy × requests × users",
                "count": len(gaps),
            })

    # 5. Retry queue blocată (DevOps)
    retry_failed = await db.orchestrator_retry_queue.count_documents({"status": "failed", "test": {"$ne": True}})
    if retry_failed:
        attention.append({
            "id": "retry_failed", "severity": "warning",
            "situatie": f"{retry_failed} acțiuni eșuate definitiv în retry queue",
            "propunere": "Verifică last_detail — cauzele externe (ex: DNS Resend) cer acțiune manuală",
            "impact_estimat": "Notificări/emailuri nelivrate recuperate",
            "actiune_1tap": {"label": "Deschide Orchestrator", "route": "/admin/orchestrator"},
            "sursa_semnalului": "orchestrator_retry_queue",
            "count": retry_failed,
        })

    # 5b. Tranzacții orfane (Finance Reconciler) — prima acțiune „propunere → execuție 1-tap" (Blueprint §8)
    from orchestrator.playbooks_sprint3 import count_orphan_transactions
    orphan_ids = await count_orphan_transactions(30)
    if orphan_ids:
        attention.append({
            "id": "orphan_transactions", "severity": "warning",
            "situatie": f"{len(orphan_ids)} tranzacții orfane (30z) — cereri asociate inexistente",
            "propunere": "Arhivează-le automat cu marcaj de reconciliere (rămân în istoric, ies din alertele zilnice)",
            "impact_estimat": "Reconciliere financiară curată — Finance Reconciler nu mai escaladează",
            "actiune_1tap": {"label": "Repară automat", "api": "/admin/control-tower/actions/reconcile-orphans", "method": "POST"},
            "sursa_semnalului": "Finance Reconciler (playbook 9)",
            "count": len(orphan_ids),
        })

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    attention.sort(key=lambda a: (severity_rank.get(a["severity"], 3), -a["count"]))

    # Pulse
    pulse = {
        "open_requests": await db.requests.count_documents({"status": "open"}),
        "active_jobs": await db.requests.count_documents({"status": {"$in": ["accepted", "in_progress"]}}),
        "kyc_pending": kyc_pending,
        "disputes_open": disputes_open,
        "retry_failed": retry_failed,
    }

    # Autonomy Report (7 zile): ce a rezolvat platforma singură
    ledger = await db.orchestrator_ledger.find(
        {"test": {"$ne": True}, "ts": {"$gte": _iso_days_ago(7)}},
        {"_id": 0, "escalated": 1, "minutes_saved": 1, "playbook_name": 1},
    ).to_list(2000)
    auto_resolved = [x for x in ledger if not x.get("escalated")]
    minutes_saved = sum(x.get("minutes_saved") or 0 for x in auto_resolved)
    by_playbook = {}
    for x in auto_resolved:
        by_playbook[x.get("playbook_name") or "—"] = by_playbook.get(x.get("playbook_name") or "—", 0) + 1
    autonomy_report = {
        "auto_resolved_7d": len(auto_resolved),
        "escalated_7d": len(ledger) - len(auto_resolved),
        "hours_saved_7d": round(minutes_saved / 60, 1),
        "top_playbooks": sorted(
            [{"name": k, "count": v} for k, v in by_playbook.items()], key=lambda x: -x["count"]
        )[:5],
    }

    return {"attention": attention[:5], "pulse": pulse, "autonomy_report": autonomy_report}


@router.post("/actions/reconcile-orphans")
async def reconcile_orphan_transactions(user=Depends(require_role("admin"))):
    """Execuție 1-tap (Blueprint §8): arhivează tranzacțiile orfane cu marcaj de reconciliere."""
    import uuid
    from orchestrator.playbooks_sprint3 import count_orphan_transactions
    orphan_ids = await count_orphan_transactions(30)
    if not orphan_ids:
        return {"repaired": 0, "message": "Nicio tranzacție orfană de reparat."}
    now = datetime.now(timezone.utc).isoformat()
    res = await db.transactions.update_many(
        {"_id": {"$in": orphan_ids}},
        {"$set": {"reconciliation": {"status": "archived_orphan", "ts": now, "by": user.get("email"), "reason": "Cerere asociată inexistentă — arhivat 1-tap din Control Tower"}}},
    )
    await db.orchestrator_ledger.insert_one({
        "id": uuid.uuid4().hex, "ts": now, "playbook_name": "Finance Reconciler",
        "signal_kind": "finance_reconcile", "outcome": "auto_resolved", "escalated": False,
        "minutes_saved": max(5, len(orphan_ids)), "test": False,
        "steps": [{"action": "reconcile_orphans_1tap", "ok": True,
                   "detail": f"{res.modified_count} tranzacții orfane arhivate de {user.get('email')} din Control Tower"}],
    })
    return {"repaired": res.modified_count, "message": f"{res.modified_count} tranzacții orfane arhivate cu marcaj de reconciliere."}
