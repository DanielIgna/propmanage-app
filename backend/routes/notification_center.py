"""Notification Center AI — «Ai N lucruri importante», prioritizat, cu ack per admin.

Agregă alertele din Command Center (care includ deja departamentele ROȘII din
Business Health) + recomandările AI nerezolvate. Fiecare item are link direct.
Ack-urile sunt per admin și expiră natural (item nou = key nou sau zi nouă).
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/notification-center", tags=["notification-center"])
logger = logging.getLogger("propmanage.notification_center")

WARNING_LINKS = {
    "waiting_48h": "/admin/command-center",
    "escrow_held": "/admin/financial-cockpit",
    "escrow_frozen": "/admin/financial-cockpit",
    "disputes": "/admin",
    "incomplete_spec": "/admin/users",
    "pending_pay": "/admin/financial-cockpit",
}


@router.get("")
async def notification_center(admin=Depends(require_role("admin"))):
    from routes.command_center import _build_feed
    feed = await _build_feed()

    items = []
    for w in feed["warnings"]:
        items.append({
            "key": w["key"],
            "label": w["label"],
            "severity": w["severity"],
            "link": w.get("link") or WARNING_LINKS.get(w["key"], "/admin"),
            "source": "health" if w["key"].startswith("health_") else "operational",
        })

    recos_doc = await db.command_center_recos.find_one({"_id": "latest"}, {"_id": 0})
    for r in (recos_doc or {}).get("recommendations", []) or []:
        if not r.get("done"):
            items.append({
                "key": f"reco_{r.get('idx', 0)}",
                "label": f"AI: {r.get('action')}",
                "severity": r.get("severity", "medium"),
                "link": r.get("link", "/admin/command-center"),
                "source": "ai_recommendation",
            })

    async for a in db.audit_anomalies.find({"resolved": False}, {"_id": 0}).sort("ts", -1).limit(10):
        items.append({
            "key": f"anomaly_{a['id']}",
            "label": f"🛡 Audit Sentinel: {a['type']} — {a['email']} ({a['detail']})",
            "severity": "high",
            "link": "/admin/command-center",
            "source": "security",
        })

    # Ack-uri per admin, per zi (item-ele se regenerează zilnic)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ack_doc = await db.notification_center_acks.find_one({"admin": admin.get("email"), "date": today})
    acked = set((ack_doc or {}).get("keys", []))
    for it in items:
        it["acked"] = it["key"] in acked

    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda i: (i["acked"], order.get(i["severity"], 3)))
    unacked = [i for i in items if not i["acked"]]
    return {
        "headline": f"Ai {len(unacked)} lucruri importante" if unacked else "Totul e sub control",
        "unacked_count": len(unacked),
        "items": items,
        "generated_at": feed["generated_at"],
    }


@router.post("/ack")
async def ack_item(key: str = Body(..., embed=True), admin=Depends(require_role("admin"))):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.notification_center_acks.update_one(
        {"admin": admin.get("email"), "date": today},
        {"$addToSet": {"keys": key}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True, "key": key}
