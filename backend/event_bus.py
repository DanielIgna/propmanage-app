"""XOS Event Bus — fluxul canonic de evenimente al ecosistemului (Sprint 1 / Felia 1).

Un singur punct de emisie pentru toate evenimentele (Prompt 003: Mission Control primește Event-uri).
- vocabular pe capabilități (Prompt 005: Capability Map)
- property_id derivat automat din request când lipsește (Legea 2: totul gravitează în jurul Twin-ului)
- stocare canonică în activity_events (reutilizare, nu colecție nouă — Legea 14)
- forward către orchestrator când există un playbook înregistrat pentru acest tip
Best-effort: nu aruncă niciodată excepții către apelant.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from db import db

logger = logging.getLogger("propmanage.event_bus")

# Capability Map (Prompt 005): prefix event_type → capabilitate Property DNA
CAPABILITY_MAP = {
    "request": "works", "offer": "works", "job": "works", "work": "works", "review": "works",
    "dispute": "works",
    "escrow": "financial", "payment": "financial", "wallet": "financial", "invoice": "financial",
    "warranty": "financial", "subscription": "financial",
    "twin": "twin", "dt": "twin", "model": "twin", "scan": "twin",
    "hh": "health", "health": "health", "audit": "health",
    "document": "documents", "kyc": "documents", "contract": "documents",
    "property": "identity",
    "sensor": "sensors", "alarm": "sensors",
    "recommendation": "recommendations", "ai": "recommendations", "copilot": "recommendations",
    "maintenance": "maintenance", "schedule": "maintenance",
    "lead": "marketplace", "partner": "marketplace", "campaign": "marketplace",
}


def capability_of(event_type: str) -> str:
    head = (event_type or "").replace("_", ".").split(".")[0]
    return CAPABILITY_MAP.get(head, "timeline")


async def emit(
    event_type: str,
    request_id: Optional[str] = None,
    property_id: Optional[str] = None,
    actor: Optional[dict] = None,
    payload: Optional[dict] = None,
) -> None:
    """Emisia canonică a unui eveniment. Never raises."""
    # Legea 2: leagă evenimentul de proprietate ori de câte ori e posibil
    if not property_id and request_id:
        try:
            req = await db.requests.find_one({"_id": ObjectId(request_id)}, {"property_id": 1})
            property_id = req.get("property_id") if req else None
        except Exception:  # noqa: BLE001
            property_id = None

    doc = {
        "request_id": request_id,
        "property_id": property_id,
        "event_type": event_type,
        "capability": capability_of(event_type),
        "actor_id": actor.get("id") if actor else None,
        "actor_name": actor.get("name") if actor else "System",
        "actor_role": (actor.get("active_view") or actor.get("role")) if actor else "system",
        "payload": payload or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await db.activity_events.insert_one(doc)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"event_bus emit failed ({event_type}): {e}")

    # Forward către orchestrator dacă există playbook pentru acest tip de semnal
    try:
        from orchestrator.playbooks import PLAYBOOKS
        if event_type in PLAYBOOKS:
            from orchestrator.engine import emit_signal
            await emit_signal(event_type, {**(payload or {}), "request_id": request_id, "property_id": property_id})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"event_bus orchestrator forward failed ({event_type}): {e}")
