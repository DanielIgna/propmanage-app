"""Playbooks de lansare (Firul B) — semnale din modulele de creștere → acțiuni + ledger.

resident_joined     — vecin conectat la bloc → administratorul află imediat (momentum de activare)
campaign_scheduled  — campanie convertită în lucrări → adminii platformei văd conversia
first_payment       — PRIMA plată reală → sărbătorită cu email către toți adminii (o singură dată)
"""
import logging

from bson import ObjectId

from db import db
from orchestrator.engine import notify_admins
from services import notify

logger = logging.getLogger("propmanage.playbooks_launch")


async def handle_resident_joined(payload: dict) -> dict:
    bid = payload.get("building_id")
    steps = []
    b = await db.buildings.find_one({"_id": ObjectId(bid)}) if bid and ObjectId.is_valid(bid) else None
    if not b:
        return {"steps": [{"action": "lookup_building", "ok": False}], "outcome": "noop", "minutes_saved": 0}
    admin_id = b.get("administrator_id") or b.get("created_by")
    connected = await db.properties.count_documents({"building_id": bid})
    declared = b.get("apartments_total") or 0
    if admin_id and admin_id != payload.get("owner_id"):
        pct = f" ({round(connected / declared * 100)}% activare)" if declared else ""
        await notify(admin_id, f"🏢 Vecin nou conectat în {b['name']}",
                     f"{connected}{f'/{declared}' if declared else ''} apartamente conectate{pct}. Fiecare vecin activ crește puterea campaniilor comune.",
                     type_="building", link="/administrator")
        steps.append({"action": "notify_building_admin", "ok": True})
    return {"steps": steps, "outcome": "notified", "minutes_saved": 5}


async def handle_campaign_scheduled(payload: dict) -> dict:
    n = payload.get("requests_created") or 0
    title = payload.get("title") or "Campanie comună"
    sent = await notify_admins(
        f"💶 Campanie convertită: {title}",
        f"{n} lucrări directe create dintr-o singură acceptare — marketplace-ul de grup funcționează.",
        link="/admin")
    return {"steps": [{"action": "notify_admins", "ok": True, "detail": f"{sent} admini"}],
            "outcome": "notified", "minutes_saved": 15}


async def handle_first_payment(payload: dict) -> dict:
    subs = payload.get("subs") or 0
    rev = payload.get("lead_revenue_30d") or 0
    sent = await notify_admins(
        "🎉 PRIMA PLATĂ REALĂ pe PropManage",
        f"{subs} abonamente active · {rev} RON lead fees în 30 zile. Momentul zero al companiei — cere feedback și un review clientului!",
        link="/admin", send_emails=True)
    return {"steps": [{"action": "celebrate_first_payment", "ok": True, "detail": f"{sent} admini emailați"}],
            "outcome": "notified", "minutes_saved": 0}


LAUNCH_PLAYBOOKS = {
    "resident_joined": {
        "id": "launch_resident_welcome",
        "name": "Launch: Vecin Conectat",
        "description": "La conectarea unui vecin la bloc: administratorul e anunțat imediat cu procentul de activare — menține momentum-ul de onboarding (~5 min/eveniment).",
        "handler": handle_resident_joined,
    },
    "campaign_scheduled": {
        "id": "launch_campaign_tracker",
        "name": "Launch: Campanie Convertită",
        "description": "La acceptarea unei oferte de grup: adminii platformei văd conversia (N lucrări dintr-un click) — dovada de piață e urmărită automat (~15 min/campanie).",
        "handler": handle_campaign_scheduled,
    },
    "first_payment": {
        "id": "launch_first_payment",
        "name": "Launch: Prima Plată Reală",
        "description": "Money-Flow Guard detectează prima încasare reală (abonament sau lead fee) → email către toți adminii, o singură dată. Momentul zero al companiei.",
        "handler": handle_first_payment,
    },
}
