"""PropManage — GDPR Compliance Pack (Phase 49).

Comprehensive GDPR module covering:
- ROPA (Art. 30) — Records of Processing Activities
- DPIA — Data Protection Impact Assessment for AI features
- Sub-processor list with international transfer status
- Cookie & storage inventory
- Breach response workflow
- DSAR self-service (Art. 15 access, Art. 17 erasure, Art. 20 portability)
- Per-role privacy notices (Art. 13/14) + DPA template
- PDF export for all documents
"""
import os
import io
import json
import logging
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse

from db import db
from deps import require_role, get_current_user

logger = logging.getLogger("propmanage.gdpr")

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])
admin_router = APIRouter(prefix="/api/admin/gdpr", tags=["admin-gdpr"])

COMPANY_NAME = os.environ.get("COMPANY_LEGAL_NAME", "[NUMELE COMPANIEI] SRL")
COMPANY_ADDRESS = os.environ.get("COMPANY_ADDRESS", "[ADRESA SEDIULUI SOCIAL], România")
COMPANY_REGISTRY = os.environ.get("COMPANY_REGISTRY", "[J__/__/____] · CUI [_______]")
DPO_EMAIL = os.environ.get("DPO_EMAIL", "dpo@propmanage.io")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@propmanage.io")

# ============= DEFAULTS (ROPA, sub-processors, cookies, DPIA) =============

DEFAULT_ROPA = [
    {
        "id": "user_accounts",
        "name": "Gestiune conturi utilizatori",
        "purpose": "Crearea și administrarea conturilor pentru Client, Specialist, Operator, Admin.",
        "legal_basis": "Executarea contractului (Art. 6(1)(b) GDPR)",
        "data_subjects": ["clienți", "specialiști", "operatori", "admini"],
        "data_categories": ["nume", "email", "telefon", "hash parolă", "rol", "data creării"],
        "recipients": ["echipa internă PropManage"],
        "transfers": [],
        "retention": "Pe durata existenței contului + 30 zile după ștergere",
        "security": ["criptare la rest", "hash bcrypt parole", "JWT signed tokens", "rate limiting", "2FA opțional"],
    },
    {
        "id": "service_marketplace",
        "name": "Marketplace cereri & specialiști",
        "purpose": "Matching între clienți și specialiști pentru servicii de mentenanță / renovare.",
        "legal_basis": "Executarea contractului + interes legitim (Art. 6(1)(b)(f))",
        "data_subjects": ["clienți", "specialiști"],
        "data_categories": ["adresă proprietate", "descriere lucrare", "fotografii", "buget", "categorie servicii"],
        "recipients": ["specialiști eligibili în categoria & zona cererii"],
        "transfers": [],
        "retention": "5 ani de la finalizarea cererii (justificat fiscal)",
        "security": ["control acces per rol", "vizibilitate limitată per cerere", "audit log"],
    },
    {
        "id": "payments_escrow",
        "name": "Plăți & escrow",
        "purpose": "Procesare plăți client → blocare escrow → eliberare specialist (split 95/5).",
        "legal_basis": "Executarea contractului + obligație legală fiscală (Art. 6(1)(b)(c))",
        "data_subjects": ["clienți", "specialiști"],
        "data_categories": ["sume tranzacții", "ID Stripe", "IBAN payout (specialiști)", "facturi"],
        "recipients": ["Stripe (procesor)", "ANAF (la cerere legală)"],
        "transfers": [{"to": "Stripe (US)", "mechanism": "SCC + Data Privacy Framework"}],
        "retention": "10 ani (obligație legală facturi)",
        "security": ["nu stocăm numere card (PCI compliant prin Stripe)", "TLS 1.3", "webhook signature verification"],
    },
    {
        "id": "ai_concierge",
        "name": "AI Concierge (asistent chat)",
        "purpose": "Asistență conversațională per rol (Client/Specialist/Operator) cu Claude Sonnet 4.5.",
        "legal_basis": "Consimțământ explicit + interes legitim (Art. 6(1)(a)(f))",
        "data_subjects": ["utilizatori autentificați"],
        "data_categories": ["mesaje user (text)", "răspunsuri AI (cu redactare PII automată)", "metadate sesiune"],
        "recipients": ["Anthropic via Emergent Universal Key"],
        "transfers": [{"to": "Anthropic (US)", "mechanism": "SCC + Anthropic Data Processing Addendum"}],
        "retention": "90 zile, apoi anonimizare automată",
        "security": [
            "PII redaction pe output (email, telefon, IBAN, CNP)",
            "prompt-injection filter regex",
            "rate-limit per user (25/h, 200/zi)",
            "fără date sensibile transmise modelului",
        ],
    },
    {
        "id": "ai_security_monitor",
        "name": "Behavioral Security Monitor",
        "purpose": "Detectare boți, VPN, scrapere, anomalii comportamentale pe endpoint-uri AI.",
        "legal_basis": "Interes legitim (Art. 6(1)(f)) — securitate platformă",
        "data_subjects": ["toți vizitatorii"],
        "data_categories": ["adresă IP", "user-agent", "headere edge (CF-IPCountry)", "timestamp"],
        "recipients": ["echipa internă PropManage"],
        "transfers": [],
        "retention": "12 luni",
        "security": ["log encrypted", "acces doar admin", "audit log pentru consultare"],
    },
    {
        "id": "digital_twin",
        "name": "Digital Twin proprietăți",
        "purpose": "Modelare digitală a proprietății (fotografii, plan, telemetrie IoT opțională).",
        "legal_basis": "Consimțământ + executare contract (Art. 6(1)(a)(b))",
        "data_subjects": ["clienți"],
        "data_categories": ["fotografii imobile", "schițe", "date IoT (când activate)", "istoric mentenanță"],
        "recipients": ["operatori validare twin", "specialiști asignați (limitat)"],
        "transfers": [],
        "retention": "Pe durata contului + 3 ani backup",
        "security": ["acces limitat la proprietarul twin-ului", "audit acces", "watermark fotografii partajate"],
    },
    {
        "id": "trust_score",
        "name": "Trust Score specialiști",
        "purpose": "Profilare automată pentru calitate (rating, dispute rate, timp livrare).",
        "legal_basis": "Interes legitim + consimțământ (Art. 6(1)(a)(f))",
        "data_subjects": ["specialiști"],
        "data_categories": ["evaluări clienți", "rate de livrare", "număr dispute", "scor agregat"],
        "recipients": ["clienți (scor public)", "specialiști proprii", "admin"],
        "transfers": [],
        "retention": "Pe durata contului",
        "security": ["formula publică în ToS", "drept de obiecție Art. 22 (profilare)", "review manual la cerere"],
    },
    {
        "id": "notifications_email",
        "name": "Notificări email tranzacționale",
        "purpose": "Notificări escrow, mesaje, alerte, digest admin.",
        "legal_basis": "Executare contract (Art. 6(1)(b))",
        "data_subjects": ["utilizatori autentificați"],
        "data_categories": ["email", "subiect", "conținut email"],
        "recipients": ["Resend (procesor)"],
        "transfers": [{"to": "Resend (US/EU)", "mechanism": "SCC"}],
        "retention": "30 zile pentru audit livrare",
        "security": ["DKIM/SPF/DMARC", "no PII în log meta-data"],
    },
    {
        "id": "demo_leads",
        "name": "Demo leads (formular public)",
        "purpose": "Capture lead-uri prospect de pe landing page pentru programare demonstrație.",
        "legal_basis": "Consimțământ (Art. 6(1)(a)) + interes legitim follow-up",
        "data_subjects": ["vizitatori prospect"],
        "data_categories": ["nume", "email", "telefon/WhatsApp", "companie", "rol", "mesaj"],
        "recipients": ["admin sales PropManage"],
        "transfers": [],
        "retention": "12 luni dacă nu se închide deal-ul; permanent dacă devine client",
        "security": ["formulare TLS", "idempotent per email/zi", "acces admin-only"],
    },
    {
        "id": "audit_log",
        "name": "Audit log activități",
        "purpose": "Tracking modificări critice pentru securitate și conformitate.",
        "legal_basis": "Interes legitim + obligație legală (Art. 6(1)(c)(f))",
        "data_subjects": ["toți utilizatorii"],
        "data_categories": ["acțiune", "user ID", "before/after diff", "timestamp", "IP"],
        "recipients": ["admin"],
        "transfers": [],
        "retention": "24 luni",
        "security": ["append-only design", "imutabil prin role check", "PDF export semnat"],
    },
]


DEFAULT_SUB_PROCESSORS = [
    {
        "id": "stripe",
        "name": "Stripe Payments Europe Ltd",
        "purpose": "Procesare plăți & escrow",
        "country": "Irlanda (entitate UE) + US (data processing)",
        "transfer_mechanism": "SCC + EU-US Data Privacy Framework",
        "dpa_url": "https://stripe.com/legal/dpa",
        "status": "active",
    },
    {
        "id": "anthropic_emergent",
        "name": "Anthropic via Emergent Universal Key",
        "purpose": "Motor LLM pentru AI Concierge + Investigator",
        "country": "Statele Unite",
        "transfer_mechanism": "SCC (Standard Contractual Clauses)",
        "dpa_url": "https://www.anthropic.com/legal/data-processing-addendum",
        "status": "active",
    },
    {
        "id": "resend",
        "name": "Resend",
        "purpose": "Livrare emailuri tranzacționale",
        "country": "UE / US (multi-region)",
        "transfer_mechanism": "SCC",
        "dpa_url": "https://resend.com/legal/dpa",
        "status": "ready_to_activate",
    },
    {
        "id": "mongodb",
        "name": "MongoDB Atlas",
        "purpose": "Bază de date principală",
        "country": "UE (Frankfurt)",
        "transfer_mechanism": "Hosting în UE — nu sunt transferuri către țări terțe",
        "dpa_url": "https://www.mongodb.com/legal/privacy-policy",
        "status": "active",
    },
    {
        "id": "emergent",
        "name": "Emergent Platform",
        "purpose": "Infrastructură hosting + proxy LLM",
        "country": "US/EU",
        "transfer_mechanism": "SCC",
        "dpa_url": "https://emergent.sh/legal",
        "status": "active",
    },
]


DEFAULT_COOKIES = [
    {"name": "pm_session", "purpose": "Autentificare JWT", "type": "necesar", "duration": "7 zile", "first_party": True},
    {"name": "pm_theme", "purpose": "Preferință light/dark", "type": "necesar", "duration": "Persistent", "first_party": True},
    {"name": "pm_concierge_session", "purpose": "Persistă sesiune chat Concierge", "type": "funcțional", "duration": "Session", "first_party": True},
    {"name": "pm_promo_dismissed", "purpose": "Banner promo skip", "type": "preferință", "duration": "Session", "first_party": True},
    {"name": "pm_demo_mode_dismissed", "purpose": "Banner demo mode skip", "type": "preferință", "duration": "Session", "first_party": True},
]


DPIA_DOC = {
    "title": "Data Protection Impact Assessment — PropManage AI Layer",
    "version": "1.0",
    "scope": "Procesele de profilare automată din AI Concierge, Behavioral Security Monitor și Trust Score scoring.",
    "high_risk_factors": [
        "Decizii automate care afectează experiența user-ului (block / scoring / refuz)",
        "Procesare la scară (toate request-urile)",
        "Profilare comportamentală (block rate, abuse counter)",
        "Date trimise către procesori în țări terțe (Anthropic-US)",
    ],
    "mitigations": [
        "Niciun act automat ireversibil — adminul aprobă acțiunile critice (Repair Suggester)",
        "PII redaction automată pe output LLM",
        "Drept de obiecție Art. 22 (review manual la cerere)",
        "Rate limiting + cap zilnic per user pentru a preveni cost-exfiltration",
        "Audit log complet pentru consultare DPO",
        "SCC semnate cu toți procesorii (Anthropic, Stripe)",
    ],
    "residual_risk": "Scăzut — toate deciziile au override uman, datele LLM nu se folosesc pentru antrenare modelelor.",
    "review_frequency": "Anual sau la orice modificare materială a procesului AI",
}


BREACH_CHECKLIST = [
    {"step": 1, "name": "Detectare & containment (0-2h)", "actions": [
        "Identifică sursa breach-ului (acces neautorizat, scurgere DB, etc.)",
        "Izolează componenta afectată (revoke tokens, blochează endpoint, ia DB snapshot pentru forensic)",
        "Documentează ora exactă a detectării",
    ]},
    {"step": 2, "name": "Evaluare gravitate (2-12h)", "actions": [
        "Câți utilizatori afectați?",
        "Ce categorii de date au fost expuse (PII, financiar, sănătate)?",
        "Există risc semnificativ pentru drepturile vizate?",
    ]},
    {"step": 3, "name": "Notificare ANSPDCP (până la 72h)", "actions": [
        "Completează formularul oficial pe portal ANSPDCP",
        "Furnizează: natura breach, categorii vizate, măsuri luate, contact DPO",
        "Salvează numărul de înregistrare",
    ]},
    {"step": 4, "name": "Notificare utilizatori afectați (fără întârziere)", "actions": [
        "Doar dacă risc ridicat pentru drepturi",
        "Email direct + în-app banner + post pe /status",
        "Include: ce s-a întâmplat, ce date, ce facem, ce pot face ei",
    ]},
    {"step": 5, "name": "Remediere & lessons learned (max 30 zile)", "actions": [
        "Fix tehnic permanent + DPIA review",
        "Post-mortem documentat în GDPR audit log",
        "Update ROPA dacă procesul s-a schimbat",
    ]},
]


# ============= DOC STORAGE HELPERS =============

async def _get_doc(collection: str, default):
    doc = await db[collection].find_one({"_id": "global"})
    if not doc:
        return default
    items = doc.get("items", default)
    return items


async def _save_doc(collection: str, items, actor_id: str):
    await db[collection].update_one(
        {"_id": "global"},
        {"$set": {"items": items, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": actor_id}},
        upsert=True,
    )


# ============= USER-FACING DSAR =============

@router.get("/me/export")
async def dsar_export(user: dict = Depends(get_current_user)):
    """Art. 15 — full data export for the authenticated user."""
    uid = user["id"]
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_id": uid,
        "rights_summary": {
            "access": "Art. 15 GDPR — vezi datele tale aici.",
            "rectification": "Art. 16 — corectează în setări sau scrie la " + DPO_EMAIL,
            "erasure": "Art. 17 — solicită ștergere via /api/gdpr/me/erasure-request",
            "portability": "Art. 20 — acest export e structurat JSON, importabil.",
            "objection": "Art. 21 — scrie la " + DPO_EMAIL,
        },
        "account": None,
        "requests": [],
        "projects": [],
        "concierge_messages_count": 0,
        "notifications_count": 0,
        "wallet": None,
        "payments_count": 0,
    }
    # Account
    try:
        acc = await db.users.find_one({"_id": ObjectId(uid)})
        if acc:
            out["account"] = {
                "email": acc.get("email"), "name": acc.get("name"), "role": acc.get("role"),
                "phone": acc.get("phone"), "created_at": str(acc.get("_id").generation_time),
                "tutorial_seen": bool(acc.get("tutorial_seen")), "wallet_balance": acc.get("wallet_balance"),
                "rating": acc.get("rating"), "review_count": acc.get("review_count"),
            }
    except InvalidId:
        pass
    # Requests
    async for r in db.requests.find({"$or": [{"client_id": uid}, {"specialist_id": uid}]}).limit(500):
        out["requests"].append({
            "id": str(r["_id"]), "title": r.get("title"), "status": r.get("status"),
            "category": r.get("category"), "created_at": r.get("created_at"),
            "escrow_amount": r.get("escrow_amount"), "escrow_status": r.get("escrow_status"),
        })
    # Projects
    async for p in db.projects.find({"$or": [{"client_id": uid}, {"designer_id": uid}]}).limit(200):
        out["projects"].append({
            "id": str(p["_id"]), "name": p.get("name"), "total_budget": p.get("total_budget"),
            "milestones_count": len(p.get("milestones") or []),
        })
    # Concierge & notifs counts
    out["concierge_messages_count"] = await db.concierge_messages.count_documents({"user_id": uid})
    out["ai_sessions_count"] = await db.ai_sessions.count_documents({"user_id": uid})
    out["notifications_count"] = await db.notifications.count_documents({"user_id": uid})
    out["payments_count"] = await db.payments.count_documents({"$or": [{"user_id": uid}, {"client_id": uid}, {"specialist_id": uid}]})
    return out


@router.post("/me/erasure-request")
async def dsar_erasure(payload: dict = Body(default={}), user: dict = Depends(get_current_user)):
    """Art. 17 — submit erasure request to admin review queue."""
    reason = (payload.get("reason") or "").strip()[:500]
    confirm = bool(payload.get("confirm"))
    if not confirm:
        raise HTTPException(400, "Confirm explicit cu confirm:true.")
    # Idempotent: prevent multiple pending requests
    existing = await db.dsar_requests.find_one({"user_id": user["id"], "type": "erasure", "status": {"$in": ["new", "in_review"]}})
    if existing:
        return {"ok": True, "deduped": True, "id": str(existing["_id"])}
    doc = {
        "user_id": user["id"], "user_email": user.get("email"), "user_role": user.get("role"),
        "type": "erasure",
        "reason": reason,
        "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sla_due_at": (datetime.now(timezone.utc).replace(microsecond=0).isoformat()),  # 30d below
    }
    from datetime import timedelta as _td
    doc["sla_due_at"] = (datetime.now(timezone.utc) + _td(days=30)).isoformat()
    res = await db.dsar_requests.insert_one(doc)
    return {"ok": True, "id": str(res.inserted_id), "sla_due_at": doc["sla_due_at"]}


@router.get("/me/consents")
async def my_consents(user: dict = Depends(get_current_user)):
    """Track explicit consents (privacy, terms, marketing). Read from users doc."""
    try:
        u = await db.users.find_one({"_id": ObjectId(user["id"])}, {"consents": 1, "tutorial_seen": 1, "created_at": 1})
    except InvalidId:
        u = None
    consents = (u or {}).get("consents") or {}
    return {
        "user_id": user["id"],
        "consents": consents,
        "account_created_at": str((u or {}).get("created_at") or ""),
        "implicit_consents": {
            "terms_at_signup": True,
            "privacy_at_signup": True,
        },
    }


@router.post("/me/consents")
async def set_consent(payload: dict = Body(...), user: dict = Depends(get_current_user)):
    """User updates a granular consent (e.g. marketing_email)."""
    key = (payload.get("key") or "").strip()[:60]
    value = bool(payload.get("value"))
    if not key:
        raise HTTPException(400, "key required")
    now = datetime.now(timezone.utc).isoformat()
    try:
        await db.users.update_one(
            {"_id": ObjectId(user["id"])},
            {"$set": {f"consents.{key}": {"value": value, "updated_at": now}}},
        )
    except InvalidId:
        raise HTTPException(400, "Invalid user")
    return {"ok": True, key: value}


# ============= PUBLIC GDPR ENDPOINTS =============

@router.get("/documents/{doc_type}")
async def get_public_document(doc_type: str):
    """Public read-only access to ROPA, sub-processors, cookies, DPIA, breach plan."""
    if doc_type == "ropa":
        return {"items": await _get_doc("gdpr_ropa", DEFAULT_ROPA)}
    if doc_type == "sub-processors":
        return {"items": await _get_doc("gdpr_sub_processors", DEFAULT_SUB_PROCESSORS)}
    if doc_type == "cookies":
        return {"items": await _get_doc("gdpr_cookies", DEFAULT_COOKIES)}
    if doc_type == "dpia":
        return DPIA_DOC
    if doc_type == "breach-plan":
        return {"steps": BREACH_CHECKLIST}
    if doc_type == "company":
        return {"name": COMPANY_NAME, "address": COMPANY_ADDRESS, "registry": COMPANY_REGISTRY, "dpo_email": DPO_EMAIL}
    raise HTTPException(404, "Unknown document")


# ============= ADMIN GDPR CONTROL =============

@admin_router.get("/dsar")
async def admin_list_dsars(status: str = None, user: dict = Depends(require_role("admin"))):
    filt = {}
    if status and status != "all":
        filt["status"] = status
    cursor = db.dsar_requests.find(filt).sort("created_at", -1).limit(200)
    items = []
    async for d in cursor:
        d["_id"] = str(d["_id"])
        items.append(d)
    counts = {
        "new": await db.dsar_requests.count_documents({"status": "new"}),
        "in_review": await db.dsar_requests.count_documents({"status": "in_review"}),
        "completed": await db.dsar_requests.count_documents({"status": "completed"}),
        "rejected": await db.dsar_requests.count_documents({"status": "rejected"}),
    }
    counts["total"] = sum(counts.values())
    return {"items": items, "counts": counts}


@admin_router.patch("/dsar/{req_id}")
async def admin_update_dsar(req_id: str, payload: dict = Body(...), user: dict = Depends(require_role("admin"))):
    try:
        oid = ObjectId(req_id)
    except InvalidId:
        raise HTTPException(400, "Invalid id")
    allowed = {"status", "admin_notes", "outcome"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if "status" in updates and updates["status"] not in {"new", "in_review", "completed", "rejected"}:
        raise HTTPException(400, "Invalid status")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    updates["updated_by"] = user["id"]
    res = await db.dsar_requests.update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(404, "Not found")
    # Audit
    await db.gdpr_audit.insert_one({
        "kind": "dsar_update",
        "dsar_id": req_id,
        "actor": user["id"],
        "changes": updates,
        "created_at": updates["updated_at"],
    })
    return {"ok": True}


@admin_router.get("/ropa")
async def admin_get_ropa(user: dict = Depends(require_role("admin"))):
    return {"items": await _get_doc("gdpr_ropa", DEFAULT_ROPA)}


@admin_router.put("/ropa")
async def admin_put_ropa(payload: dict = Body(...), user: dict = Depends(require_role("admin"))):
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise HTTPException(400, "items must be list")
    await _save_doc("gdpr_ropa", items, user["id"])
    await db.gdpr_audit.insert_one({
        "kind": "ropa_update", "actor": user["id"], "count": len(items),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "count": len(items)}


@admin_router.get("/sub-processors")
async def admin_get_subs(user: dict = Depends(require_role("admin"))):
    return {"items": await _get_doc("gdpr_sub_processors", DEFAULT_SUB_PROCESSORS)}


@admin_router.put("/sub-processors")
async def admin_put_subs(payload: dict = Body(...), user: dict = Depends(require_role("admin"))):
    items = payload.get("items") or []
    await _save_doc("gdpr_sub_processors", items, user["id"])
    return {"ok": True}


@admin_router.get("/cookies")
async def admin_get_cookies(user: dict = Depends(require_role("admin"))):
    return {"items": await _get_doc("gdpr_cookies", DEFAULT_COOKIES)}


@admin_router.put("/cookies")
async def admin_put_cookies(payload: dict = Body(...), user: dict = Depends(require_role("admin"))):
    items = payload.get("items") or []
    await _save_doc("gdpr_cookies", items, user["id"])
    return {"ok": True}


@admin_router.post("/breach-drill")
async def log_breach_drill(payload: dict = Body(...), user: dict = Depends(require_role("admin"))):
    """Log a breach response drill (used for DPO audits / certifications)."""
    scenario = (payload.get("scenario") or "Test drill").strip()[:300]
    steps_done = payload.get("steps_done") or []
    duration_minutes = max(0, int(payload.get("duration_minutes") or 0))
    notes = (payload.get("notes") or "").strip()[:1000]
    doc = {
        "scenario": scenario, "steps_done": steps_done, "duration_minutes": duration_minutes, "notes": notes,
        "actor": user["id"], "actor_name": user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await db.gdpr_breach_drills.insert_one(doc)
    return {"ok": True, "id": str(res.inserted_id)}


@admin_router.get("/breach-drill")
async def list_breach_drills(user: dict = Depends(require_role("admin"))):
    cursor = db.gdpr_breach_drills.find({}).sort("created_at", -1).limit(50)
    items = []
    async for d in cursor:
        d["_id"] = str(d["_id"])
        items.append(d)
    return {"items": items}


@admin_router.get("/audit")
async def gdpr_audit(limit: int = Query(100, le=500), user: dict = Depends(require_role("admin"))):
    cursor = db.gdpr_audit.find({}).sort("created_at", -1).limit(limit)
    items = []
    async for d in cursor:
        d["_id"] = str(d["_id"])
        items.append(d)
    return {"items": items}


# ============= PDF EXPORTS =============

def _build_pdf_styles():
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    BASE = "Helvetica"; BOLD = "Helvetica-Bold"
    dejavu_paths = {
        "DejaVu": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVu-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    }
    if os.path.exists(dejavu_paths["DejaVu"]):
        try:
            for name, path in dejavu_paths.items():
                if os.path.exists(path) and name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
            BASE = "DejaVu"
            BOLD = "DejaVu-Bold" if os.path.exists(dejavu_paths["DejaVu-Bold"]) else "DejaVu"
        except Exception:  # noqa: BLE001
            pass

    base_styles = getSampleStyleSheet()
    styles = {
        "h1": ParagraphStyle("h1", parent=base_styles["Heading1"], fontName=BOLD, fontSize=22, spaceAfter=12, textColor=colors.HexColor("#0a0a0b")),
        "h2": ParagraphStyle("h2", parent=base_styles["Heading2"], fontName=BOLD, fontSize=14, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#0a0a0b")),
        "h3": ParagraphStyle("h3", parent=base_styles["Heading3"], fontName=BOLD, fontSize=11, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#444")),
        "body": ParagraphStyle("body", parent=base_styles["BodyText"], fontName=BASE, fontSize=9.5, leading=13, spaceAfter=4),
        "small": ParagraphStyle("small", parent=base_styles["BodyText"], fontName=BASE, fontSize=8, leading=11, textColor=colors.HexColor("#666")),
        "label": ParagraphStyle("label", parent=base_styles["BodyText"], fontName=BOLD, fontSize=8, leading=11, textColor=colors.HexColor("#888")),
    }
    return styles, BASE, BOLD


async def _build_ropa_pdf() -> io.BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    styles, BASE, BOLD = _build_pdf_styles()
    ropa = await _get_doc("gdpr_ropa", DEFAULT_ROPA)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm, title="ROPA — PropManage")
    story = []
    story.append(Paragraph("Registru al Activităților de Prelucrare (ROPA)", styles["h1"]))
    story.append(Paragraph(f"Operator: <b>{COMPANY_NAME}</b> · {COMPANY_ADDRESS} · {COMPANY_REGISTRY}", styles["body"]))
    story.append(Paragraph(f"DPO contact: <b>{DPO_EMAIL}</b> · Document generat: {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')} UTC", styles["small"]))
    story.append(Paragraph("Conform Art. 30 GDPR — toate activitățile de prelucrare sunt documentate mai jos.", styles["small"]))
    story.append(Spacer(1, 0.5*cm))

    for act in ropa:
        story.append(Paragraph(f"{act.get('name', '—')}", styles["h2"]))
        rows = [
            ["Scop", act.get("purpose", "")],
            ["Temei legal", act.get("legal_basis", "")],
            ["Categorii vizați", ", ".join(act.get("data_subjects", []))],
            ["Categorii date", ", ".join(act.get("data_categories", []))],
            ["Destinatari", ", ".join(act.get("recipients", []))],
            ["Retenție", act.get("retention", "")],
            ["Securitate", "; ".join(act.get("security", []))],
        ]
        if act.get("transfers"):
            rows.append(["Transferuri internaționale", "; ".join([f"{t.get('to')} ({t.get('mechanism')})" for t in act["transfers"]])])
        t = Table([[Paragraph(f"<b>{k}</b>", styles["body"]), Paragraph(v, styles["body"])] for k, v in rows], colWidths=[4*cm, 12.5*cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e5e5")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f7f7f7")),
            ("INNERPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    doc.build(story)
    buf.seek(0)
    return buf


async def _build_privacy_notice_pdf(role: str) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    styles, BASE, BOLD = _build_pdf_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=1.8*cm, title=f"Privacy Notice — {role}")
    story = []

    title_map = {
        "client": "Notificare Confidențialitate — Client",
        "specialist": "Notificare Confidențialitate — Specialist",
        "operator": "Notificare Confidențialitate — Operator",
        "visitor": "Notificare Confidențialitate — Vizitator",
        "dpa": "Acord Procesare Date (DPA) — Client B2B",
    }
    story.append(Paragraph(title_map.get(role, "Privacy Notice"), styles["h1"]))
    story.append(Paragraph(f"Operator: <b>{COMPANY_NAME}</b> · DPO: <b>{DPO_EMAIL}</b>", styles["small"]))
    story.append(Paragraph(f"Versiune: 1.0 · Data: {datetime.now(timezone.utc).strftime('%d.%m.%Y')}", styles["small"]))
    story.append(Spacer(1, 0.5*cm))

    content = _per_role_content(role)
    for section in content:
        story.append(Paragraph(section["title"], styles["h2"]))
        for para in section["paragraphs"]:
            story.append(Paragraph(para, styles["body"]))
        if section.get("bullets"):
            for b in section["bullets"]:
                story.append(Paragraph(f"• {b}", styles["body"]))
        story.append(Spacer(1, 0.2*cm))

    doc.build(story)
    buf.seek(0)
    return buf


def _per_role_content(role: str):
    common_footer = [
        {"title": "Drepturile tale (GDPR Art. 15-22)",
         "paragraphs": ["Ai dreptul de acces, rectificare, ștergere, restricționare, portabilitate, obiecție și de a nu fi supus unor decizii automate (cu excepția cazurilor permise expres)."],
         "bullets": [
             "Acces — cere o copie a datelor tale.",
             "Rectificare — corectează date inexacte.",
             "Ștergere — dreptul de a fi uitat (cu excepții legale).",
             "Portabilitate — primește datele în format JSON / CSV.",
             "Obiecție — opune-te procesării pentru anumite scopuri.",
             "Plângere ANSPDCP — www.dataprotection.ro.",
         ]},
        {"title": "Cum exerciți drepturile",
         "paragraphs": [
             f"Cerere directă către DPO: <b>{DPO_EMAIL}</b>",
             "Self-service: Setări cont → Datele mele → Export / Ștergere",
             "Răspuns garantat în maxim 30 zile.",
         ]},
    ]
    if role == "client":
        return [
            {"title": "Cine ești în relația cu noi", "paragraphs": [
                f"Ești <b>Client</b> al platformei PropManage, operată de {COMPANY_NAME}. Folosești platforma pentru a-ți gestiona proprietățile, lansa cereri către specialiști și efectua plăți escrow.",
            ]},
            {"title": "Ce date colectăm de la tine", "paragraphs": [], "bullets": [
                "Cont: nume, email, telefon, hash parolă, rol.",
                "Proprietăți: adresă, fotografii, plan, telemetrie IoT (opțional).",
                "Tranzacții: sume, status escrow, facturi (10 ani retenție fiscală).",
                "Mesaje cu specialiști și AI Concierge (90 zile).",
                "Logs tehnice: IP, user-agent (12 luni, anti-fraudă).",
            ]},
            {"title": "Temeiul legal", "paragraphs": [
                "Executare contract (Art. 6(1)(b)) pentru servicii principale; consimțământ explicit pentru AI Concierge; obligație legală pentru facturi (Art. 6(1)(c))."
            ]},
            {"title": "Cu cine partajăm", "paragraphs": [], "bullets": [
                "Specialiști asignați — doar datele necesare pentru cererea ta.",
                "Stripe (procesare plăți, US, SCC).",
                "Anthropic (AI Concierge, US, SCC, fără PII).",
                "Resend (notificări email).",
                "Autorități la cerere legală formală.",
            ]},
        ] + common_footer
    if role == "specialist":
        return [
            {"title": "Cine ești în relația cu noi", "paragraphs": [
                f"Ești <b>Specialist</b> verificat al platformei {COMPANY_NAME}. Oferi servicii contra cost clienților matchate prin marketplace.",
            ]},
            {"title": "Ce date colectăm de la tine", "paragraphs": [], "bullets": [
                "Profil public: nume profesional, fotografie, zona de acoperire, categorii servicii, evaluări.",
                "Documente verificare: act identitate, certificate calificare (acces strict admin).",
                "IBAN pentru payout (criptat la rest).",
                "Trust Score — calcul automat din rating, dispute, timp livrare (vezi DPIA pentru detalii).",
                "Lead-fee tranzacții: 45 RON / lead acceptat.",
                "Conversații cu clienți și AI Concierge.",
            ]},
            {"title": "Profilare automată (Art. 22)", "paragraphs": [
                "Trust Score este o decizie semi-automatizată care afectează vizibilitatea ta în marketplace. Ai dreptul de a cere review manual și de a contesta scorul prin DPO.",
            ]},
            {"title": "Temeiul legal", "paragraphs": [
                "Executare contract de prestări servicii; obligații fiscale pentru facturi; interes legitim pentru Trust Score și securitate platformă."
            ]},
        ] + common_footer
    if role == "operator":
        return [
            {"title": "Cine ești în relația cu noi", "paragraphs": [
                f"Ești <b>Operator</b> intern al platformei — validezi Digital Twin-urile clienților și raportezi incidente. Relația este de tip <b>angajat / colaborator</b>.",
            ]},
            {"title": "Ce date colectăm de la tine", "paragraphs": [], "bullets": [
                "Cont angajat: nume, email corporat, rol, ore activitate.",
                "Acțiuni efectuate: validări twin, decizii conformitate, comentarii.",
                "Log de audit dedicat — orice validare e tracked imutabil.",
            ]},
            {"title": "Datele clienților accesate", "paragraphs": [
                "În calitate de operator, ai acces tehnic la fotografii și planuri ale proprietăților. Este interzis să folosești aceste date în afara scopului de validare. Orice acces e logged și auditat.",
            ]},
            {"title": "Temeiul legal", "paragraphs": [
                "Executare contract muncă/colaborare; interes legitim pentru audit acces."
            ]},
        ] + common_footer
    if role == "visitor":
        return [
            {"title": "Cine ești în relația cu noi", "paragraphs": [
                f"Ești <b>Vizitator</b> pe site-ul {COMPANY_NAME} fără cont. Nu ai obligația de a-ți crea cont pentru a vizita pagini publice.",
            ]},
            {"title": "Ce colectăm de la tine", "paragraphs": [], "bullets": [
                "Cookies necesare (autentificare, preferințe UI) — fără consent banner pentru cele strict necesare.",
                "Dacă completezi formular „Programează demo”: nume, email, telefon/WhatsApp opțional, companie.",
                "Logs tehnice anonime (IP în formă agregată pentru rate limiting).",
            ]},
            {"title": "Ce NU facem", "paragraphs": [], "bullets": [
                "NU folosim cookies de tracking publicitar.",
                "NU vindem datele tale către terți.",
                "NU folosim Google Analytics / Facebook Pixel fără consimțământ explicit.",
            ]},
            {"title": "Retenție", "paragraphs": [
                "Demo leads: 12 luni; logs tehnice: 12 luni; cookies necesare: durata sesiunii sau persistente conform inventarului public."
            ]},
        ] + common_footer
    if role == "dpa":
        return [
            {"title": "Acord de Procesare a Datelor (DPA)", "paragraphs": [
                f"Acest acord se încheie între <b>{COMPANY_NAME}</b> ('Procesator') și clientul B2B ('Operator de Date'), conform Art. 28 GDPR.",
            ]},
            {"title": "1. Obiectul prelucrării", "paragraphs": [
                "Procesatorul oferă infrastructură SaaS pentru gestiunea proprietăților. Operatorul de Date păstrează controlul deplin asupra datelor înregistrate în platformă."
            ]},
            {"title": "2. Durata", "paragraphs": ["Pe durata contractului principal + 30 zile pentru ștergere."]},
            {"title": "3. Natura și scopul", "paragraphs": ["Stocare, procesare, agregare statistică, livrare prin interfața platformei."]},
            {"title": "4. Categorii de date și vizați", "paragraphs": ["Vezi ROPA atașat — disponibil la cerere."]},
            {"title": "5. Obligațiile Procesatorului", "paragraphs": [], "bullets": [
                "Procesează datele doar conform instrucțiunilor scrise.",
                "Asigură confidențialitatea personalului.",
                "Aplică măsuri tehnice și organizatorice adecvate (Art. 32).",
                "Notifică breach-uri în max 48h.",
                "Asistă Operatorul de Date în răspunsul la DSAR-uri.",
                "Returnează / șterge datele la finalul contractului.",
                "Acceptă audit anual al Operatorului de Date.",
            ]},
            {"title": "6. Sub-procesori", "paragraphs": [
                "Lista actualizată la /api/gdpr/documents/sub-processors. Operatorul de Date are dreptul de a obiecta în 14 zile de la notificarea unui nou sub-procesor."
            ]},
            {"title": "7. Transferuri internaționale", "paragraphs": [
                "Toate transferurile către țări terțe sunt acoperite de SCC + măsuri suplimentare conform Schrems II."
            ]},
            {"title": "8. Semnături", "paragraphs": [
                "Procesator: ______________________  ·  Operator de Date: ______________________  ·  Data: ____________"
            ]},
        ]
    return common_footer


@router.get("/pdf/ropa")
async def pdf_ropa(user: dict = Depends(get_current_user)):
    buf = await _build_ropa_pdf()
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=propmanage_ropa.pdf"})


@router.get("/pdf/notice/{role}")
async def pdf_notice(role: str):
    if role not in {"client", "specialist", "operator", "visitor", "dpa"}:
        raise HTTPException(404, "Unknown role")
    buf = await _build_privacy_notice_pdf(role)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=propmanage_notice_{role}.pdf"})


@router.get("/pdf/bundle")
async def pdf_bundle(user: dict = Depends(require_role("admin"))):
    """Package E — ZIP bundle with all DPO PDFs (ROPA + DPIA + 5 notices)."""
    import zipfile
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        # ROPA
        ropa_buf = await _build_ropa_pdf()
        z.writestr("01_ROPA_Art30.pdf", ropa_buf.getvalue())
        # DPIA
        dpia_buf = await _build_dpia_pdf_buffer()
        z.writestr("02_DPIA_AI_Layer.pdf", dpia_buf.getvalue())
        # Notices
        for role in ("client", "specialist", "operator", "visitor", "dpa"):
            buf = await _build_privacy_notice_pdf(role)
            z.writestr(f"03_Notice_{role}.pdf", buf.getvalue())
        # Sub-processors JSON (no PDF dedicated yet; ship JSON for transparency)
        subs = await _get_doc("gdpr_sub_processors", DEFAULT_SUB_PROCESSORS)
        cookies = await _get_doc("gdpr_cookies", DEFAULT_COOKIES)
        z.writestr("04_sub_processors.json", json.dumps(subs, ensure_ascii=False, indent=2))
        z.writestr("05_cookies_inventory.json", json.dumps(cookies, ensure_ascii=False, indent=2))
        z.writestr("06_breach_plan.json", json.dumps(BREACH_CHECKLIST, ensure_ascii=False, indent=2))
        readme = (
            f"PropManage — DPO Compliance Bundle\n"
            f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
            f"Operator: {COMPANY_NAME}\n"
            f"DPO: {DPO_EMAIL}\n\n"
            f"Contents:\n"
            f"  01_ROPA_Art30.pdf      — Registru Activități Prelucrare (Art. 30)\n"
            f"  02_DPIA_AI_Layer.pdf   — Data Protection Impact Assessment (AI)\n"
            f"  03_Notice_client.pdf   — Privacy Notice pentru Client\n"
            f"  03_Notice_specialist.pdf\n"
            f"  03_Notice_operator.pdf\n"
            f"  03_Notice_visitor.pdf\n"
            f"  03_Notice_dpa.pdf      — Data Processing Agreement (B2B)\n"
            f"  04_sub_processors.json — Lista sub-procesatori (JSON)\n"
            f"  05_cookies_inventory.json\n"
            f"  06_breach_plan.json    — Checklist 72h\n"
        )
        z.writestr("README.txt", readme)
    zbuf.seek(0)
    # Audit log
    await db.gdpr_audit.insert_one({
        "kind": "bundle_export", "actor": user["id"], "actor_name": user.get("name"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return StreamingResponse(zbuf, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=propmanage_gdpr_bundle.zip"})


async def _build_dpia_pdf_buffer() -> io.BytesIO:
    """Extracted helper so bundle can reuse without HTTP layer."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    styles, BASE, BOLD = _build_pdf_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=1.8*cm, title="DPIA — PropManage AI")
    story = [
        Paragraph(DPIA_DOC["title"], styles["h1"]),
        Paragraph(f"Versiune {DPIA_DOC['version']} · Operator: {COMPANY_NAME} · DPO: {DPO_EMAIL}", styles["small"]),
        Spacer(1, 0.4*cm),
        Paragraph("1. Scop", styles["h2"]),
        Paragraph(DPIA_DOC["scope"], styles["body"]),
        Paragraph("2. Factori de risc ridicat", styles["h2"]),
    ]
    for f in DPIA_DOC["high_risk_factors"]:
        story.append(Paragraph(f"• {f}", styles["body"]))
    story.append(Paragraph("3. Măsuri de atenuare", styles["h2"]))
    for m in DPIA_DOC["mitigations"]:
        story.append(Paragraph(f"• {m}", styles["body"]))
    story.append(Paragraph("4. Risc rezidual", styles["h2"]))
    story.append(Paragraph(DPIA_DOC["residual_risk"], styles["body"]))
    story.append(Paragraph("5. Frecvență de revizuire", styles["h2"]))
    story.append(Paragraph(DPIA_DOC["review_frequency"], styles["body"]))
    doc.build(story)
    buf.seek(0)
    return buf


@router.get("/pdf/dpia")
async def pdf_dpia():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    styles, BASE, BOLD = _build_pdf_styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.8*cm, bottomMargin=1.8*cm, title="DPIA — PropManage AI")
    story = [
        Paragraph(DPIA_DOC["title"], styles["h1"]),
        Paragraph(f"Versiune {DPIA_DOC['version']} · Operator: {COMPANY_NAME} · DPO: {DPO_EMAIL}", styles["small"]),
        Spacer(1, 0.4*cm),
        Paragraph("1. Scop", styles["h2"]),
        Paragraph(DPIA_DOC["scope"], styles["body"]),
        Paragraph("2. Factori de risc ridicat", styles["h2"]),
    ]
    for f in DPIA_DOC["high_risk_factors"]:
        story.append(Paragraph(f"• {f}", styles["body"]))
    story.append(Paragraph("3. Măsuri de atenuare", styles["h2"]))
    for m in DPIA_DOC["mitigations"]:
        story.append(Paragraph(f"• {m}", styles["body"]))
    story.append(Paragraph("4. Risc rezidual", styles["h2"]))
    story.append(Paragraph(DPIA_DOC["residual_risk"], styles["body"]))
    story.append(Paragraph("5. Frecvență de revizuire", styles["h2"]))
    story.append(Paragraph(DPIA_DOC["review_frequency"], styles["body"]))
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=propmanage_dpia.pdf"})
