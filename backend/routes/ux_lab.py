"""UX Lab — Client Junior & Specialist Entry (experiment autonom, Jun 2026).

- POST /api/public/client-junior/request  — cerere reală → unified leads (source=client_junior)
- POST /api/public/ux-lab/event           — telemetrie funnel anonimă (conversie, drop-off)
- GET  /api/admin/ux-lab/metrics          — conversie, drop-off pe pași, time-to-value
"""
import re
import secrets
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, HTTPException, Depends

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.ux_lab")
router = APIRouter(prefix="/api", tags=["ux-lab"])

EMAIL_RX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# Valoare estimată lead per categorie (triaj pipeline)
CATEGORY_VALUES = {
    "digital_twin": 1500,
    "design_interior": 8000,
    "zugraveli": 6000,
    "instalatii": 1500,
    "electric": 1000,
    "clima": 700,
    "montaj": 500,
    "curatenie": 400,
}


@router.post("/public/client-junior/request")
async def client_junior_request(payload: dict = Body(...)):
    """Public — no auth. Cerere Client Junior → client_junior_requests + unified leads."""
    name = (payload.get("name") or "").strip()[:120]
    phone = (payload.get("phone") or "").strip()[:32]
    email = (payload.get("email") or "").strip().lower()[:160]
    category = (payload.get("category") or "").strip()[:60]
    category_label = (payload.get("category_label") or "").strip()[:120]
    answers = payload.get("answers") or {}
    consent = bool(payload.get("consent"))

    if not name or len(name) < 3:
        raise HTTPException(400, "Numele este obligatoriu (min. 3 caractere).")
    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) < 9:
        raise HTTPException(400, "Număr de telefon valid este obligatoriu.")
    if email and not EMAIL_RX.match(email):
        raise HTTPException(400, "Adresa de email nu este validă.")
    if not consent:
        raise HTTPException(400, "Consimțământul GDPR este obligatoriu.")
    if not category:
        raise HTTPException(400, "Categoria de serviciu este obligatorie.")
    answers = {str(k)[:40]: str(v)[:160] for k, v in answers.items()} if isinstance(answers, dict) else {}

    now_iso = datetime.now(timezone.utc).isoformat()
    request_number = f"CJ-{secrets.token_hex(3).upper()}"
    doc = {
        "name": name,
        "phone": phone,
        "phone_digits": phone_digits,
        "email": email,
        "category": category,
        "category_label": category_label,
        "answers": answers,
        "consent": consent,
        "estimated_value": CATEGORY_VALUES.get(category, 500),
        "request_number": request_number,
        "status": "new",
        "tenant_id": "main",
        "created_at": now_iso,
        "source": "client_junior",
    }

    from leads_store import sync_lead

    # Idempotent pe (telefon + categorie + zi)
    day = now_iso[:10]
    existing = await db.client_junior_requests.find_one(
        {"phone_digits": phone_digits, "category": category, "created_at": {"$regex": f"^{day}"}}
    )
    if existing:
        await db.client_junior_requests.update_one(
            {"_id": existing["_id"]},
            {"$set": {**{k: v for k, v in doc.items() if k not in ("created_at", "request_number")},
                      "updated_at": now_iso}},
        )
        await sync_lead("client_junior", {**existing, **doc, "request_number": existing["request_number"],
                                          "id": str(existing["_id"])})
        return {"ok": True, "deduped": True, "request_number": existing["request_number"]}

    ins = await db.client_junior_requests.insert_one(doc)
    await sync_lead("client_junior", {**doc, "id": str(ins.inserted_id)})
    logger.info(f"[ux-lab] cerere client junior: {category} / {request_number}")
    return {"ok": True, "request_number": request_number}


# ── Specialist Entry — aplicație publică (aduce profesioniști) ───────────────
TRADE_VALUES = {
    "designer_arhitect": 2000,
    "auditor_tehnic": 2000,
    "instalatii": 800,
    "electric": 800,
    "finisaje": 800,
    "clima": 800,
    "montaj": 600,
    "curatenie": 500,
}


@router.post("/public/specialist-entry/apply")
async def specialist_entry_apply(payload: dict = Body(...)):
    """Public — no auth. Aplicație specialist → specialist_entry_applications + unified leads."""
    name = (payload.get("name") or "").strip()[:120]
    phone = (payload.get("phone") or "").strip()[:32]
    email = (payload.get("email") or "").strip().lower()[:160]
    city = (payload.get("city") or "").strip()[:80]
    trade = (payload.get("trade") or "").strip()[:60]
    trade_label = (payload.get("trade_label") or "").strip()[:120]
    experience = (payload.get("experience") or "").strip()[:120]
    availability = (payload.get("availability") or "").strip()[:120]
    consent = bool(payload.get("consent"))

    if not name or len(name) < 3:
        raise HTTPException(400, "Numele este obligatoriu (min. 3 caractere).")
    phone_digits = re.sub(r"\D", "", phone)
    if len(phone_digits) < 9:
        raise HTTPException(400, "Număr de telefon valid este obligatoriu.")
    if email and not EMAIL_RX.match(email):
        raise HTTPException(400, "Adresa de email nu este validă.")
    if not city:
        raise HTTPException(400, "Orașul este obligatoriu.")
    if not trade:
        raise HTTPException(400, "Meseria este obligatorie.")
    if not consent:
        raise HTTPException(400, "Consimțământul GDPR este obligatoriu.")

    now_iso = datetime.now(timezone.utc).isoformat()
    request_number = f"SE-{secrets.token_hex(3).upper()}"
    doc = {
        "name": name,
        "phone": phone,
        "phone_digits": phone_digits,
        "email": email,
        "city": city,
        "trade": trade,
        "trade_label": trade_label,
        "experience": experience,
        "availability": availability,
        "consent": consent,
        "estimated_value": TRADE_VALUES.get(trade, 500),
        "request_number": request_number,
        "status": "new",
        "tenant_id": "main",
        "created_at": now_iso,
        "source": "specialist_entry",
    }

    from leads_store import sync_lead

    day = now_iso[:10]
    existing = await db.specialist_entry_applications.find_one(
        {"phone_digits": phone_digits, "created_at": {"$regex": f"^{day}"}}
    )
    if existing:
        await db.specialist_entry_applications.update_one(
            {"_id": existing["_id"]},
            {"$set": {**{k: v for k, v in doc.items() if k not in ("created_at", "request_number")},
                      "updated_at": now_iso}},
        )
        await sync_lead("specialist_entry", {**existing, **doc, "request_number": existing["request_number"],
                                             "id": str(existing["_id"])})
        return {"ok": True, "deduped": True, "request_number": existing["request_number"]}

    ins = await db.specialist_entry_applications.insert_one(doc)
    lead_doc = {**doc, "id": str(ins.inserted_id)}
    await sync_lead("specialist_entry", lead_doc)
    # Faza 3 — ack instant + alertă admin (fire-safe; dry_run când enabled=False)
    try:
        from specialist_followup import send_immediate_ack
        await send_immediate_ack(lead_doc)
    except Exception as _e:  # noqa: BLE001
        logger.warning(f"[ux-lab] specialist ack failed: {_e}")
    logger.info(f"[ux-lab] aplicație specialist entry: {trade} / {request_number}")
    return {"ok": True, "request_number": request_number}


# ── Telemetrie funnel ─────────────────────────────────────────────────────────
ALLOWED_EVENTS = {
    "cj_view", "cj_flow_start", "cj_step", "cj_contact_view", "cj_submitted",
    "se_view", "se_flow_start", "se_step", "se_submitted",
}


@router.post("/public/ux-lab/event")
async def ux_lab_event(payload: dict = Body(...)):
    """Public — telemetrie anonimă. Fire-safe, nu aruncă niciodată 4xx pe evenimente invalide."""
    session_id = str(payload.get("session_id") or "")[:32]
    role = str(payload.get("role") or "")[:32]
    event = str(payload.get("event") or "")[:48]
    if not session_id or event not in ALLOWED_EVENTS:
        return {"ok": False}
    meta = payload.get("meta") or {}
    meta = {str(k)[:40]: str(v)[:160] for k, v in meta.items()} if isinstance(meta, dict) else {}
    await db.ux_lab_events.insert_one({
        "session_id": session_id, "role": role, "event": event, "meta": meta,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True}


@router.get("/admin/ux-lab/metrics")
async def ux_lab_metrics(days: int = 30, _admin=Depends(require_role("admin"))):
    """Funnels UX Lab (client_junior + specialist_entry): vizite → start → trimitere, drop-off, time-to-value."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    events = await db.ux_lab_events.find({"ts": {"$gte": since}}, {"_id": 0}).to_list(20000)

    def sessions(evt: str) -> set:
        return {e["session_id"] for e in events if e["event"] == evt}

    def build_funnel(prefix: str) -> dict:
        views, starts, submits = sessions(f"{prefix}_view"), sessions(f"{prefix}_flow_start"), sessions(f"{prefix}_submitted")
        step_counts: dict[str, int] = {}
        for e in events:
            if e["event"] == f"{prefix}_step":
                step = (e.get("meta") or {}).get("step", "?")
                step_counts[step] = step_counts.get(step, 0) + 1
        ttv = []
        for sid in submits:
            ts_all = sorted(e["ts"] for e in events if e["session_id"] == sid)
            ts_submit = min((e["ts"] for e in events if e["session_id"] == sid and e["event"] == f"{prefix}_submitted"), default=None)
            if ts_all and ts_submit:
                try:
                    delta = (datetime.fromisoformat(ts_submit) - datetime.fromisoformat(ts_all[0])).total_seconds()
                    if 0 <= delta < 3600:
                        ttv.append(delta)
                except ValueError:
                    pass
        return {
            "views": len(views),
            "flow_starts": len(starts),
            "submits": len(submits),
            "start_rate": round(len(starts) / len(views) * 100, 1) if views else None,
            "conversion_rate": round(len(submits) / len(views) * 100, 1) if views else None,
            "step_completions": step_counts,
            "avg_time_to_value_sec": round(sum(ttv) / len(ttv), 1) if ttv else None,
        }

    cj = build_funnel("cj")
    se = build_funnel("se")
    total_cj = await db.client_junior_requests.count_documents({"created_at": {"$gte": since}})
    total_se = await db.specialist_entry_applications.count_documents({"created_at": {"$gte": since}})
    return {
        "days": days,
        "funnels": {
            "client_junior": {**cj, "total_requests": total_cj},
            "specialist_entry": {**se, "total_requests": total_se},
        },
    }
