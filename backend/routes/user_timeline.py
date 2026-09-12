"""User Timeline — cronologia completă a unui utilizator (modulul 12 din viziune).

Agregă evenimente din: users (cont, verificare, ultima activitate), requests
(creare → asignare → escrow → finalizare), payment_transactions, reviews.
"""
import logging
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/user-timeline", tags=["user-timeline"])
logger = logging.getLogger("propmanage.user_timeline")


def _ev(ts: str | None, kind: str, label: str, detail: str = "") -> dict[str, Any] | None:
    if not ts:
        return None
    return {"ts": ts, "kind": kind, "label": label, "detail": detail}


@router.get("/search")
async def search_users(q: str = Query(..., min_length=2), _admin=Depends(require_role("admin"))):
    out = []
    async for u in db.users.find(
        {"$or": [{"email": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}]},
        {"email": 1, "name": 1, "role": 1},
    ).limit(10):
        out.append({"id": str(u["_id"]), "email": u.get("email"), "name": u.get("name"), "role": u.get("role")})
    return {"users": out}


@router.get("/{user_id}")
async def user_timeline(user_id: str, _admin=Depends(require_role("admin"))):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(400, "ID utilizator invalid")
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(404, "Utilizator inexistent")

    events: list[dict[str, Any]] = []
    events.append(_ev(user.get("created_at"), "account", "Cont creat", f"Rol: {user.get('role')}"))
    if user.get("verified"):
        events.append(_ev(user.get("verified_at") or user.get("created_at"), "verify", "Identitate verificată", ""))
    if user.get("fast_response_awarded_at"):
        events.append(_ev(user["fast_response_awarded_at"], "badge", "Badge ⚡ Fast Response acordat", "Automation Center"))
    events.append(_ev(user.get("last_seen"), "activity", "Ultima activitate", ""))

    uid = str(user["_id"])
    role_field = "specialist_id" if user.get("role") == "specialist" else "client_id"
    async for r in db.requests.find({role_field: uid}).sort("created_at", 1).limit(100):
        title = (r.get("title") or r.get("category") or "cerere")[:60]
        events.append(_ev(r.get("created_at"), "request", f"Cerere: {title}", f"Status: {r.get('status')} · {r.get('county') or ''}"))
        if r.get("assigned_at"):
            events.append(_ev(r["assigned_at"], "match", f"Specialist asignat — {title}", ""))
        if r.get("escrow_status") in ("held", "released", "frozen") and r.get("escrow_amount"):
            events.append(_ev(r.get("escrow_funded_at") or r.get("assigned_at") or r.get("created_at"), "escrow",
                             f"Escrow {r['escrow_status']} — {r.get('escrow_amount'):.0f} lei", title))
        if r.get("completed_at"):
            events.append(_ev(r["completed_at"], "complete", f"Lucrare finalizată — {title}", ""))

    if user.get("email"):
        async for p in db.payment_transactions.find({"user_email": user["email"]}).sort("created_at", 1).limit(50):
            events.append(_ev(p.get("created_at"), "payment",
                             f"Plată {p.get('payment_status')} — {p.get('amount'):.0f} {p.get('currency', 'RON').upper()}", ""))

    async for rv in db.reviews.find({"$or": [{"client_id": uid}, {"specialist_id": uid}]}).sort("created_at", 1).limit(30):
        events.append(_ev(rv.get("created_at"), "review", f"Review {'primit' if rv.get('specialist_id') == uid else 'lăsat'} — {rv.get('rating')}★", (rv.get("comment") or "")[:80]))

    events = [e for e in events if e]
    events.sort(key=lambda e: e["ts"])
    return {
        "user": {"id": uid, "email": user.get("email"), "name": user.get("name"), "role": user.get("role"),
                 "verified": bool(user.get("verified")), "county": user.get("county")},
        "events": events,
        "total": len(events),
    }
