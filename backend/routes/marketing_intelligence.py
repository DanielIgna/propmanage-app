"""Marketing Intelligence+ API — Board 007 / GI-3.
Recomandări executive + Opportunity Queue + AI Contact Playbook (omul aprobă).
Toate deciziile operatorului intră în ai_decision_ledger (fundația Learning Engine GI-4).
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/marketing-intel", tags=["marketing-intelligence"])
logger = logging.getLogger("propmanage.marketing_intel.api")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/latest")
async def latest_insights(user: dict = Depends(require_role("admin"))):
    doc = await db.marketing_insights.find_one({"_id": "latest"})
    if not doc:
        from marketing_intelligence import run_marketing_scan
        return await run_marketing_scan(trigger="first_view")
    doc.pop("_id", None)
    return doc


@router.post("/run")
async def run_scan(user: dict = Depends(require_role("admin"))):
    from marketing_intelligence import run_marketing_scan
    return await run_marketing_scan(trigger="manual")


@router.get("/opportunity-queue")
async def opportunity_queue(user: dict = Depends(require_role("admin"))):
    from marketing_intelligence import build_opportunity_queue
    items = await build_opportunity_queue(30)
    return {"items": items, "count": len(items),
            "total_value_ron": round(sum(i["value_ron"] for i in items), 2)}


# ============================================================================
# AI CONTACT PLAYBOOK — AI recomandă, omul aprobă (Board 007)
# ============================================================================
class PlaybookIn(BaseModel):
    target_type: str  # opportunity | lead
    ref_id: str = Field(min_length=1, max_length=80)


@router.post("/playbook")
async def generate_playbook(body: PlaybookIn, user: dict = Depends(require_role("admin"))):
    if body.target_type not in ("opportunity", "lead"):
        raise HTTPException(400, "target_type invalid")
    # debounce cost LLM: refolosește playbook-ul generat recent pentru același target, nedecis încă
    from datetime import timedelta
    recent_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    existing = await db.contact_playbooks.find_one(
        {"ref_id": body.ref_id, "status": "generated", "created_at": {"$gte": recent_cutoff}}, {"_id": 0})
    if existing:
        return existing
    # context real: semnale lead + serviciu + valoare
    lead = opp = None
    if body.target_type == "opportunity":
        opp = await db.revenue_opportunities.find_one({"id": body.ref_id})
        if not opp:
            raise HTTPException(404, "Oportunitate inexistentă")
        if opp.get("owner_id"):
            lead = await db.lead_scores.find_one({"user_id": opp["owner_id"]})
    else:
        lead = await db.lead_scores.find_one({"visitor_id": body.ref_id})
        if not lead:
            raise HTTPException(404, "Lead inexistent")

    signals = [s["label"] for s in ((lead or {}).get("signals") or [])]
    service_label = (opp or {}).get("service_label") or "Audit Tehnic"
    benefit = (opp or {}).get("benefit") or ""
    name = (lead or {}).get("user_name") or (opp or {}).get("property_name") or ""
    why = signals[:6] or ["Oportunitate comercială activă generată de Revenue Hunter"]

    content = None
    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești consultantul de comunicare al PropManage (platformă românească de servicii pentru proprietate). "
            "Primești contextul unui lead și generezi mesaje calde, în limbaj de BENEFICII, fără presiune de vânzare, "
            "ton prietenos-profesionist, în română. Răspunde STRICT JSON: "
            "{\"whatsapp_message\": str ≤400c cu emoji moderat, \"email_subject\": str ≤70c, "
            "\"email_body\": str ≤700c, \"notification_text\": str ≤140c}."
        )
        prompt = (
            f"Lead: {name or 'proprietar'} · serviciu recomandat: {service_label}. "
            f"Beneficiu serviciu: {benefit or 'documentare și valoare pentru proprietate'}. "
            f"Semnale reale de intenție: {'; '.join(why)}. "
            "Personalizează mesajul pe semnale (ex: dacă a abandonat o cerere, oferă ajutor să o finalizeze)."
        )
        result = await claude_json(system=system, prompt=prompt, session_prefix="contact-playbook")
        if result.get("whatsapp_message"):
            content = {k: str(result.get(k) or "")[:800] for k in
                       ("whatsapp_message", "email_subject", "email_body", "notification_text")}
            ai_generated = True
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[playbook] LLM fail: {e} — fallback")
    if not content:
        content = {
            "whatsapp_message": f"Bună{', ' + name if name else ''}! 👋 Am observat interesul tău pentru {service_label} pe PropManage. "
                                f"Îți putem pregăti o ofertă fără obligații — răspunde aici și te ghidăm pas cu pas.",
            "email_subject": f"{service_label} pentru locuința ta — următorul pas simplu",
            "email_body": f"Bună{', ' + name if name else ''},\n\nAi explorat recent {service_label} pe PropManage. "
                          f"{benefit}\n\nDacă vrei, îți pregătim o ofertă personalizată — durează 2 minute.\n\nEchipa PropManage",
            "notification_text": f"Oferta ta pentru {service_label} te așteaptă — un pas și e gata.",
        }
        ai_generated = False

    pid = uuid.uuid4().hex
    playbook = {
        "id": pid, "target_type": body.target_type, "ref_id": body.ref_id,
        "lead_name": name, "service_label": service_label, "why": why,
        "content": content, "ai_generated": ai_generated,
        "status": "generated", "created_by": user.get("email"), "created_at": _now(),
    }
    await db.contact_playbooks.insert_one({**playbook})
    # AI Decision Ledger (GI-4a): recomandarea așteaptă decizia omului; target → Outcome Tracker
    await db.ai_decision_ledger.insert_one({
        "ledger_id": uuid.uuid4().hex, "type": "contact_playbook", "playbook_id": pid,
        "source_agent": "marketing_intelligence",
        "recommendation": f"Contactează {name or 'lead-ul'} pentru {service_label}",
        "reason": "; ".join(why), "confidence": "ai_hypothesis",
        "status": "pending", "created_at": _now(),
        "target": {"visitor_id": (lead or {}).get("visitor_id"),
                   "user_id": (lead or {}).get("user_id") or (opp or {}).get("owner_id"),
                   "service": (opp or {}).get("service")},
    })
    return playbook


class PlaybookDecision(BaseModel):
    action: str  # sent | edited | ignored
    final_message: str = ""


@router.post("/playbook/{pid}/decision")
async def playbook_decision(pid: str, body: PlaybookDecision, user: dict = Depends(require_role("admin"))):
    if body.action not in ("sent", "edited", "ignored"):
        raise HTTPException(400, "Acțiune invalidă (sent|edited|ignored)")
    pb = await db.contact_playbooks.find_one({"id": pid})
    if not pb:
        raise HTTPException(404, "Playbook inexistent")
    updates = {"status": body.action, "decided_by": user.get("email"), "decided_at": _now()}
    if body.final_message:
        updates["final_message"] = body.final_message[:1200]
    await db.contact_playbooks.update_one({"id": pid}, {"$set": updates})
    await db.ai_decision_ledger.update_one(
        {"playbook_id": pid},
        {"$set": {"status": "decided", "action": body.action, "approved_by": user.get("email"),
                  "decided_at": _now(), "result": "pending_outcome"}},
    )
    try:
        from event_bus import emit
        await emit("playbook.decision", payload={"playbook_id": pid, "action": body.action,
                                                 "by": user.get("email")})
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "id": pid, "status": body.action}


@router.get("/playbooks")
async def list_playbooks(limit: int = 30, user: dict = Depends(require_role("admin"))):
    docs = await db.contact_playbooks.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 100))
    return {"items": docs, "count": len(docs)}
