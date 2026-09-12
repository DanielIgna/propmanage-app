"""Lead Magnet Engine — Growth OS Faza G1 (Board Directive 088, aprobat cu condiții).

Public: capturează leads din magneti (Scorul Casei, Checklist cumpărare) →
colecție proprie + sync în leads unificate + email cu rezultatul + notificare admin.
Admin: funnel minimal Sursă→Lead→Comandă (conversion tracking G1.5).
"""
import os
import re
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["lead-magnets"])

EMAIL_RX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

MAGNETS = {
    "health_score": {"label": "Scorul Casei Tale", "estimated_value": 350},
    "buying_checklist": {"label": "Checklist cumpărare apartament", "estimated_value": 350},
}


def _score_verdict(score: int) -> str:
    if score >= 80:
        return "A — Stare excelentă"
    if score >= 60:
        return "B — Stare bună"
    if score >= 40:
        return "C — Necesită atenție"
    return "D — Risc ridicat"


CHECKLIST_HTML = """
<h3>📋 Checklist complet: verificarea apartamentului înainte de cumpărare (25 puncte)</h3>
<p><b>1. Acte & juridic:</b> extras CF actualizat · sarcini/ipoteci · certificat energetic · carte tehnică/planuri · datorii asociație+utilități</p>
<p><b>2. Structură & clădire:</b> fisuri pereți/tavane · risc seismic clădire · stare fațadă/acoperiș · subsol uscat · modificări structurale autorizate</p>
<p><b>3. Instalații:</b> vârsta instalației electrice + împământare · tablou cu siguranțe automate · presiune și culoare apă · țevi (PEX/PPR vs plumb/oțel) · centrală (vârstă+revizie) sau punct termic · verificare gaz la zi</p>
<p><b>4. Interior & finisaje:</b> umiditate/mucegai (colțuri, spatele mobilei) · ferestre și izolare fonică · pardoseli drepte · uși/feronerie · igrasie la baie</p>
<p><b>5. Zonă & costuri:</b> costuri lunare reale (întreținere iarnă!) · vecini/liniște la ore diferite · parcare · dezvoltări viitoare în zonă</p>
<p style="margin-top:14px;"><b>Recomandare:</b> pentru siguranță maximă, comandă un <b>audit tehnic profesionist</b> înainte de semnare — costă 350 RON și poate identifica probleme de zeci de mii de RON.</p>
"""


@router.post("/public/lead-magnet")
async def submit_lead_magnet(payload: dict = Body(...)):
    """Public — no auth. Capturează un lead dintr-un magnet + trimite rezultatul pe email."""
    magnet = (payload.get("magnet") or "").strip()
    if magnet not in MAGNETS:
        raise HTTPException(400, "Magnet necunoscut.")
    name = (payload.get("name") or "").strip()[:120]
    email = (payload.get("email") or "").strip().lower()[:160]
    phone = (payload.get("phone") or "").strip()[:32]
    city = (payload.get("city") or "").strip()[:80]
    consent = bool(payload.get("consent"))
    score = payload.get("score")
    answers = payload.get("answers") or {}
    risks = payload.get("risks") or []

    if not name or not EMAIL_RX.match(email):
        raise HTTPException(400, "Nume și email valid sunt obligatorii.")
    if not consent:
        raise HTTPException(400, "Consimțământul GDPR este obligatoriu.")
    if magnet == "health_score":
        try:
            score = max(0, min(100, int(score)))
        except (TypeError, ValueError):
            raise HTTPException(400, "Scor invalid.")

    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "magnet": magnet,
        "name": name,
        "email": email,
        "phone": phone,
        "city": city,
        "score": score if magnet == "health_score" else None,
        "risks": [str(r)[:200] for r in risks][:6],
        "answers": {str(k)[:40]: str(v)[:120] for k, v in dict(answers).items()} if isinstance(answers, dict) else {},
        "consent": consent,
        "status": "new",
        "estimated_value": MAGNETS[magnet]["estimated_value"],
        "created_at": now_iso,
        "source": "lead_magnet",
    }

    day = now_iso[:10]
    existing = await db.lead_magnet_leads.find_one(
        {"email": email, "magnet": magnet, "created_at": {"$regex": f"^{day}"}}
    )
    from leads_store import sync_lead
    if existing:
        await db.lead_magnet_leads.update_one(
            {"_id": existing["_id"]},
            {"$set": {**{k: v for k, v in doc.items() if k != "created_at"}, "updated_at": now_iso}},
        )
        await sync_lead("lead_magnet", {**existing, **doc, "id": str(existing["_id"])})
        return {"ok": True, "deduped": True}

    ins = await db.lead_magnet_leads.insert_one(doc)
    await sync_lead("lead_magnet", {**doc, "id": str(ins.inserted_id)})

    # Email către utilizator cu rezultatul (valoare reală — 094e Trust)
    try:
        from email_service import _layout, send_email as _send_email  # type: ignore
        if magnet == "health_score":
            verdict = _score_verdict(score)
            risks_html = "".join(f"<li style='margin:4px 0;'>⚠️ {r}</li>" for r in doc["risks"]) or "<li>Nu am identificat riscuri majore din răspunsurile tale. 👏</li>"
            body = f"""
              <p>Salut {name},</p>
              <p>Scorul de sănătate al locuinței tale este:</p>
              <div style="background:#1a1a1f; border-radius:12px; padding:18px; text-align:center; margin:12px 0;">
                <div style="font-size:42px; font-weight:bold; color:#d4ff3a;">{score}/100</div>
                <div style="color:#fff; margin-top:4px;">{verdict}</div>
              </div>
              <p><b>Principalele riscuri identificate:</b></p>
              <ul style="color:#e8e8ec;">{risks_html}</ul>
              <p>Scorul este orientativ, calculat din răspunsurile tale. Pentru o evaluare exactă (cu verificări instrumentale: termoviziune, prize, tablou, umiditate), recomandăm un <b>audit tehnic profesionist — 350 RON</b>.</p>
              <p><a href="https://propmanage.ro/imobile-verificate/sell" style="background:#d4ff3a; color:#000; padding:10px 22px; border-radius:999px; text-decoration:none; font-weight:bold;">Programează auditul →</a></p>
            """
            subject = f"Scorul casei tale: {score}/100 · {verdict}"
        else:
            body = f"""
              <p>Salut {name},</p>
              <p>Iată checklist-ul complet cu cele 25 de verificări esențiale înainte de cumpărarea unui apartament:</p>
              {CHECKLIST_HTML}
              <p><a href="https://propmanage.ro/imobile-verificate/sell" style="background:#d4ff3a; color:#000; padding:10px 22px; border-radius:999px; text-decoration:none; font-weight:bold;">Comandă audit înainte de cumpărare →</a></p>
            """
            subject = "Checklist-ul tău: 25 de verificări înainte să cumperi apartamentul"
        html = _layout(title=MAGNETS[magnet]["label"], preheader=subject, body_html=body)
        await _send_email([email], subject, html)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[LeadMagnet] user email failed: {e}")

    # Notificare scurtă admin
    try:
        from email_service import _layout, send_email as _send_email  # type: ignore
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@propmanage.io")
        info = f"Scor: {score}/100" if magnet == "health_score" else "Checklist descărcat"
        html = _layout(
            title="🧲 Lead nou din Lead Magnet",
            preheader=f"{name} · {MAGNETS[magnet]['label']}",
            body_html=f"<p><b>{name}</b> ({email}, {phone or 'fără tel'}, {city or 'oraș n/a'})<br/>Magnet: <b>{MAGNETS[magnet]['label']}</b> · {info}<br/>Lead-ul apare în <b>Admin → Unified Leads</b>.</p>",
        )
        await _send_email([admin_email], f"[Lead Magnet] {name} · {MAGNETS[magnet]['label']}", html)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[LeadMagnet] admin notify failed: {e}")

    return {"ok": True, "deduped": False}


@router.get("/admin/growth/funnel")
async def growth_funnel(days: int = 30, user=Depends(require_role("admin"))):
    """Conversion tracking minimal (G1.5): Vizitatori → Leads → Comenzi VE."""
    days = max(1, min(days, 90))
    now = datetime.now(timezone.utc)
    since_dt = now - timedelta(days=days)
    since_iso = since_dt.isoformat()

    rows = await db.analytics_events.aggregate([
        {"$match": {"ts": {"$gte": since_iso}}},
        {"$group": {"_id": "$visitor_id"}},
        {"$count": "n"},
    ]).to_list(1)
    visitors = rows[0]["n"] if rows else 0

    leads_by_source = {}
    async for r in db.leads.aggregate([
        {"$match": {"created_at": {"$gte": since_iso}}},
        {"$group": {"_id": "$source", "n": {"$sum": 1}}},
        {"$sort": {"n": -1}},
    ]):
        leads_by_source[r["_id"] or "necunoscut"] = r["n"]
    leads_total = sum(leads_by_source.values())

    orders_total = await db.verified_estate_orders.count_documents({"created_at": {"$gte": since_dt}})
    orders_paid = await db.verified_estate_orders.count_documents({"created_at": {"$gte": since_dt}, "status": "paid"})
    magnet_leads = await db.lead_magnet_leads.count_documents({"created_at": {"$gte": since_iso}})

    return {
        "days": days,
        "visitors": visitors,
        "leads_total": leads_total,
        "leads_by_source": leads_by_source,
        "lead_magnet_leads": magnet_leads,
        "ve_orders": orders_total,
        "ve_orders_paid": orders_paid,
        "visitor_to_lead_pct": round(leads_total / visitors * 100, 1) if visitors else None,
        "lead_to_order_pct": round(orders_total / leads_total * 100, 1) if leads_total else None,
    }
