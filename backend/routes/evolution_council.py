"""AI 27 — Enterprise Evolution Council (ședință automată, nu AI individual).

În fiecare noapte (23:45) toate departamentele AI răspund împreună la 5 întrebări:
1. Ce s-a îmbunătățit azi? 2. Ce s-a înrăutățit? 3. Ce ar trebui oprit?
4. Ce ar trebui automatizat următorul? 5. Care e acțiunea cu cel mai mare ROI mâine?
Rezultatul: UN SINGUR raport executiv (Rezoluția 002/003), persistat zilnic.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from db import db
from deps import require_role
from routes.enterprise_health import DOMAIN_LABELS, _collect_metrics, _domain_result, _get_formulas

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/evolution-council", tags=["evolution-council"])


async def run_evolution_council(actor: str = "scheduler") -> dict:
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Scoruri curente (reuse Enterprise Health D122)
    formulas = await _get_formulas()
    metrics = await _collect_metrics()
    scores = {}
    for key in DOMAIN_LABELS:
        f = formulas[key]
        if f.get("status") == "active":
            scores[key] = _domain_result(f, metrics)["score"]
    overall = round(sum(scores.values()) / len(scores), 1) if scores else 0

    prev = await db.enterprise_health_history.find_one({"date": {"$lt": today}}, sort=[("date", -1)])
    prev_scores = (prev or {}).get("scores", {})
    prev_overall = (prev or {}).get("overall")

    # Activitate operațională de azi
    pays_today, pays_sum = 0, 0.0
    async for p in db.manual_payments.find({"status": "verified", "verified_at": {"$gte": today}}, {"amount_ron": 1}):
        pays_today += 1
        pays_sum += float(p.get("amount_ron") or 0)
    gaps_assigned = await db.specialist_gaps.count_documents({"status": "assigned", "assigned_at": {"$gte": today}})
    gaps_opened = await db.specialist_gaps.count_documents({"detected_at": {"$gte": today}, "status": "open"})
    leads_new_today = await db.leads.count_documents({"created_at": {"$gte": today}})
    leads_moved = await db.leads.count_documents({"updated_at": {"$gte": today}, "stage": {"$ne": "new"}})
    win = await db.daily_wins.find_one({"day": today})
    stale_new = await db.leads.count_documents({"stage": "new"})
    pending_orders = await db.verified_estate_orders.count_documents({"status": "pending", "demo_mode": {"$ne": True}})
    completed_req = await db.requests.count_documents({"status": "completed"})
    case_studies = await db.case_library.count_documents({})

    # Q1 — Ce s-a îmbunătățit azi?
    improved = [f"{DOMAIN_LABELS[k]}: {prev_scores[k]} → {v} (+{round(v - prev_scores[k], 1)})"
                for k, v in scores.items() if k in prev_scores and v - prev_scores[k] > 0.5]
    if pays_today:
        improved.append(f"{pays_today} plăți VERIFIED azi ({pays_sum:.0f} RON venit real)")
    if gaps_assigned:
        improved.append(f"{gaps_assigned} gaps rezolvate prin alocare de specialiști")
    if leads_new_today:
        improved.append(f"{leads_new_today} leads noi intrate în pipeline")
    if leads_moved:
        improved.append(f"{leads_moved} leads avansate în pipeline azi")
    if win:
        improved.append(f"One Win: {win.get('text')}")
    if not improved:
        improved = ["Nicio îmbunătățire măsurabilă azi — zi fără execuție comercială."]

    # Q2 — Ce s-a înrăutățit?
    worsened = [f"{DOMAIN_LABELS[k]}: {prev_scores[k]} → {v} ({round(v - prev_scores[k], 1)})"
                for k, v in scores.items() if k in prev_scores and v - prev_scores[k] < -0.5]
    if gaps_opened:
        worsened.append(f"{gaps_opened} cereri noi fără specialist (gaps deschise azi)")
    if stale_new:
        worsened.append(f"{stale_new} leads stagnează în stage NEW fără contact")
    if not worsened:
        worsened = ["Nimic măsurabil nu s-a înrăutățit azi."]

    # Q3 — Ce ar trebui oprit?
    stop = []
    if scores.get("revenue", 100) < 60:
        stop.append("Orice lucru care nu duce direct la primul venit (feature-building, polish intern) — Revenue e critic.")
    if gaps_assigned == 0 and await db.specialist_gaps.count_documents({"status": "open"}) > 0:
        stop.append("Așteptarea pasivă pe gaps — candidații sunt deja calculați în Gap Engine, alocă azi.")
    if not stop:
        stop.append("Nimic de oprit — focusul este corect aliniat.")

    # Q4 — Ce ar trebui automatizat următorul?
    automate = []
    if stale_new >= 3:
        automate.append(f"Follow-up automat pentru cele {stale_new} leads NEW (email/SMS la 24h de la intrare).")
    if pending_orders:
        automate.append(f"Reminder automat de plată pentru {pending_orders} comenzi pending (cu instrucțiuni plată manuală).")
    if completed_req and case_studies == 0:
        automate.append(f"Generarea de studii de caz din cele {completed_req} proiecte finalizate (Case Library D112).")
    automate = automate[:2] or ["Nimic urgent — automatizările existente acoperă fluxul curent."]

    # Q5 — Acțiunea cu cel mai mare ROI mâine (reuse CEO Briefing D152)
    tomorrow_action = None
    try:
        from routes.ceo_briefing import ceo_briefing
        briefing = await ceo_briefing(user=None)
        ot = briefing["one_thing"]
        tomorrow_action = {"action": ot["action"], "expected_roi": ot["expected_roi"],
                           "expected_rot": ot["expected_rot"], "confidence_pct": ot["confidence_pct"]}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[Council] ceo_briefing reuse failed: {e}")
        tomorrow_action = {"action": "Contactează leads-urile hot și oferă plată manuală.",
                           "expected_roi": "Primul venit real", "expected_rot": "~2 ore", "confidence_pct": 75}

    report = {
        "day": today,
        "generated_at": now.isoformat(),
        "actor": actor,
        "participants": ["Orchestrator", "CTO", "COO", "CFO", "CMO", "Revenue", "Customer Voice", "QA", "Knowledge", "Evolution"],
        "health": {"overall": overall, "previous_overall": prev_overall,
                   "delta": round(overall - prev_overall, 1) if prev_overall is not None else None},
        "improved": improved[:6],
        "worsened": worsened[:6],
        "stop": stop[:3],
        "automate_next": automate,
        "tomorrow_top_action": tomorrow_action,
    }
    await db.evolution_council_reports.update_one({"day": today}, {"$set": report}, upsert=True)
    logger.info(f"[Council] Evolution Council report generated for {today} (actor={actor})")
    return report


@router.get("")
async def get_council(user=Depends(require_role("admin"))):
    latest = await db.evolution_council_reports.find_one({}, sort=[("day", -1)])
    if latest:
        latest.pop("_id", None)
    history = []
    async for r in db.evolution_council_reports.find({}).sort("day", -1).limit(7):
        r.pop("_id", None)
        history.append(r)
    return {"latest": latest, "history": history}


@router.post("/run")
async def run_now(user=Depends(require_role("admin"))):
    report = await run_evolution_council(actor=user.get("email") or "admin")
    return {"ok": True, "report": report}
