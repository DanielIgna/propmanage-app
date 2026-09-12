"""Follow-up automat pentru lead-uri specialist_entry (Faza 3).

3 momente cheie pentru a reduce timpul de contact <1h și activarea specialistului:
  1. ACK imediat (trimis la /apply)  — confirmare specialistului
  2. Alertă admin instant           — email intern pentru contact rapid
  3. Reminder 1h  (cron)             — dacă lead-ul e încă în stage=new
  4. Nurture 24h (cron)              — activare + ghid portal specialist

Config salvat în namespace `specialist_followup` (settings_store), enabled=False
implicit până la aprobare finală (dry_run activat automat când enabled=False).
Fire-safe: nu aruncă niciodată excepții spre codul de aplicație.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from db import db
from settings_store import get_settings, patch_settings

logger = logging.getLogger("propmanage.specialist_followup")

DEFAULT_CONFIG = {
    "enabled": False,               # switch principal (produce trimiteri reale)
    "ack_enabled": True,            # ack imediat + alertă admin (safe by default)
    "admin_email": "",              # override; gol => ADMIN_NOTIFY_EMAIL/env
    "reminder_delay_minutes": 60,
    "reminder_subject": "Suntem gata să te activăm pe PropManage — următorii pași",
    "nurture_delay_hours": 24,
    "nurture_subject": "Ghid activare specialist PropManage (5 pași · 10 minute)",
    "max_attempts": 2,
    "batch_size": 50,
    # SMS (stub până la integrare Twilio/SMSO). Când sms_enabled=True, se
    # loghează intenția în specialist_followup_log cu status=stub_pending.
    "sms_enabled": False,
    "sms_ack_text": "Salut {first}! Am primit aplicația ta PropManage ({ref}). Te sunăm în ≤60 min. Programează singur/ă: {book_url}",
    "call_booking_url": "",         # gol → derivat din FRONTEND_PUBLIC_URL + /specialist#programare
}

TRADE_LABEL_FALLBACK = {
    "designer_arhitect": "Designer / Arhitect",
    "auditor_tehnic": "Auditor tehnic",
    "instalatii": "Instalații",
    "electric": "Electric",
    "finisaje": "Finisaje",
    "clima": "Climatizare",
    "montaj": "Montaj / Mobilier",
    "curatenie": "Curățenie post-șantier",
}


async def get_config() -> dict:
    saved = await get_settings("specialist_followup")
    return {**DEFAULT_CONFIG, **(saved or {})}


async def update_config(updates: dict, who: str) -> dict:
    clean = {k: v for k, v in updates.items() if k in DEFAULT_CONFIG}
    if clean:
        await patch_settings("specialist_followup", clean, who=who)
    return await get_config()


def _admin_email(cfg: dict) -> str:
    return (cfg.get("admin_email") or "").strip() \
        or os.environ.get("ADMIN_NOTIFY_EMAIL") \
        or os.environ.get("SUPPORT_CONTACT_EMAIL") \
        or "contact@propmanage.ro"


def _first_name(name: str) -> str:
    return (name or "").strip().split(" ")[0] or "bună"


def _trade_label(doc: dict) -> str:
    return doc.get("trade_label") or TRADE_LABEL_FALLBACK.get(doc.get("trade") or "", "specialistul tău")


def _base_url() -> str:
    return (os.environ.get("FRONTEND_PUBLIC_URL") or "https://propmanage.ro").rstrip("/")


def _booking_url(cfg: dict) -> str:
    return (cfg.get("call_booking_url") or "").strip() or f"{_base_url()}/specialist#programare"


async def _send_sms_stub(phone: str, text: str, meta: dict) -> dict:
    """Fire-safe SMS stub. Loghează intenția în DB până când conectăm un
    provider real (Twilio/SMSO). Returnează un status structurat consumat
    de dispatcher."""
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "channel": "sms", "phone": phone, "text": text[:320],
        "status": "stub_pending", "provider": "none", "at": now, **meta,
    }
    try:
        await db.specialist_followup_log.insert_one(entry)
        logger.info(f"[specialist_followup:SMS_STUB] to={phone} text={text[:80]!r}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[specialist_followup] sms stub log fail: {e}")
    return {"ok": False, "provider": "stub", "reason": "sms_provider_not_configured", "at": now}


def _sms_ack_text(cfg: dict, doc: dict) -> str:
    tpl = cfg.get("sms_ack_text") or DEFAULT_CONFIG["sms_ack_text"]
    return tpl.format(
        first=_first_name(doc.get("name")),
        ref=doc.get("request_number", "—"),
        book_url=_booking_url(cfg),
    )[:320]


# ─────────────────────────────── templates ────────────────────────────────────
def _ack_html(doc: dict, cfg: dict | None = None) -> str:
    first = _first_name(doc.get("name"))
    trade = _trade_label(doc)
    base = _base_url()
    book = _booking_url(cfg or {})
    return f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#292524">
  <h2 style="color:#047857">Bine ai venit, {first}!</h2>
  <p>Am primit aplicația ta pentru <strong>{trade}</strong> în orașul <strong>{doc.get('city','—')}</strong>.
     Nr. de referință: <strong>{doc.get('request_number','—')}</strong>.</p>
  <p><strong>Următorii pași</strong>:</p>
  <ol style="line-height:1.7">
    <li>Un coordonator PropManage te sună în <strong>maxim 60 de minute</strong> (Luni–Sâmbătă, 09:00–20:00).</li>
    <li>Îți trimitem 2-3 solicitări reale din zona ta ca să vezi cum funcționează platforma.</li>
    <li>După primul job finalizat, îți activăm portalul complet + insigna de „Specialist verificat".</li>
  </ol>
  <p style="margin:24px 0 12px">
    <a href="{book}" style="background:#047857;color:#fff;padding:12px 26px;border-radius:999px;text-decoration:none;font-weight:bold">📞 Programează tu apelul (2 min)</a>
  </p>
  <p style="margin:12px 0 24px">
    <a href="{base}/specialist" style="background:#0f172a;color:#fff;padding:10px 22px;border-radius:999px;text-decoration:none">Deschide portalul specialist</a>
  </p>
  <p>Preferi WhatsApp? Salvează numărul <strong>0722 000 000</strong> și scrie-ne — răspundem instant în orele de program.</p>
  <p style="color:#78716c;font-size:13px">Echipa PropManage · specialiști verificați · plăți protejate prin escrow</p>
</div>"""


def _admin_alert_html(doc: dict) -> str:
    trade = _trade_label(doc)
    base = _base_url()
    return f"""
<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#0f172a">
  <h2 style="color:#b91c1c">⚡ Aplicație specialist nouă — contact în ≤60 min</h2>
  <table style="width:100%;border-collapse:collapse;font-size:14px">
    <tr><td style="padding:6px 0;color:#64748b">Nume</td><td><strong>{doc.get('name','—')}</strong></td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Telefon</td><td><strong>{doc.get('phone','—')}</strong></td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Email</td><td>{doc.get('email','—')}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Oraș</td><td>{doc.get('city','—')}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Meserie</td><td><strong>{trade}</strong></td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Experiență</td><td>{doc.get('experience','—')}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Disponibilitate</td><td>{doc.get('availability','—')}</td></tr>
    <tr><td style="padding:6px 0;color:#64748b">Ref. #</td><td>{doc.get('request_number','—')}</td></tr>
  </table>
  <p style="margin-top:20px">
    <a href="{base}/admin/leads?source=specialist_entry" style="background:#0f172a;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none">Deschide în Admin Leads →</a>
  </p>
</div>"""


def _reminder_html(doc: dict) -> str:
    first = _first_name(doc.get("name"))
    base = _base_url()
    return f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#292524">
  <h2 style="color:#047857">Salut, {first} — suntem gata să te activăm</h2>
  <p>Cererea ta de înscriere ca specialist e activă. Dacă nu ai primit deja apelul nostru, sună-ne direct
     la <strong>0722 000 000</strong> sau răspunde la acest email cu o oră când preferi să te sunăm.</p>
  <p style="margin:24px 0">
    <a href="{base}/specialist" style="background:#047857;color:#fff;padding:12px 26px;border-radius:999px;text-decoration:none;font-weight:bold">Vezi portalul specialist</a>
  </p>
  <p style="color:#78716c;font-size:13px">PropManage · toate mesajele sunt confidențiale · dezabonare oricând.</p>
</div>"""


def _nurture_html(doc: dict) -> str:
    first = _first_name(doc.get("name"))
    base = _base_url()
    return f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#292524">
  <h2 style="color:#047857">Ghid rapid de activare — 5 pași, ~10 minute</h2>
  <p>Salut, {first}! Ca să primești primele solicitări reale, îți pregătim contul cu 5 pași scurți:</p>
  <ol style="line-height:1.8">
    <li>Verificare telefon &amp; email (60 sec).</li>
    <li>2-3 poze din proiecte anterioare (nu contează dacă sunt din telefon).</li>
    <li>Zonele în care poți lucra (bifezi din listă).</li>
    <li>Tarife orientative (le poți schimba oricând).</li>
    <li>GDPR &amp; termeni platformă (bifă).</li>
  </ol>
  <p style="margin:24px 0">
    <a href="{base}/specialist" style="background:#047857;color:#fff;padding:12px 26px;border-radius:999px;text-decoration:none;font-weight:bold">Începe activarea (10 min)</a>
  </p>
  <p>După activare primești automat solicitările potrivite pentru meseria ta. Fără abonament, fără taxe ascunse.</p>
  <p style="color:#78716c;font-size:13px">PropManage · plăți escrow · comision transparent · dezabonare oricând.</p>
</div>"""


# ────────────────────────── acțiuni instantanee ───────────────────────────────
async def send_immediate_ack(doc: dict) -> dict:
    """Trimite (a) confirmare specialistului + (b) alertă admin + (c) SMS opțional.
    Fire-safe: nu aruncă niciodată excepții spre codul care apelează."""
    cfg = await get_config()
    if not cfg.get("ack_enabled"):
        return {"ok": False, "reason": "ack_disabled"}
    now = datetime.now(timezone.utc).isoformat()
    out = {"ack_specialist": False, "alert_admin": False, "sms": None, "at": now}
    try:
        from email_service import send_email
        # 1) Ack specialistului (doar dacă are email)
        if doc.get("email") and cfg.get("enabled"):
            r = await send_email(to=doc["email"], subject="Aplicația ta la PropManage · următorii pași",
                                 html=_ack_html(doc, cfg))
            out["ack_specialist"] = bool(r and r.get("ok"))
        elif doc.get("email"):
            # când enabled=False, doar loghezi (nu trimite email real)
            out["ack_specialist"] = "dry_run"
        # 2) Alertă admin (mereu, dacă ack_enabled)
        admin = _admin_email(cfg)
        if cfg.get("enabled"):
            r2 = await send_email(to=admin, subject=f"[Specialist ⚡] Aplicație nouă · {doc.get('city','—')} · {_trade_label(doc)}",
                                  html=_admin_alert_html(doc))
            out["alert_admin"] = bool(r2 and r2.get("ok"))
        else:
            out["alert_admin"] = "dry_run"
        # 3) SMS de bun venit (stub până integrăm Twilio/SMSO)
        if cfg.get("sms_enabled") and doc.get("phone"):
            sms_res = await _send_sms_stub(
                doc["phone"], _sms_ack_text(cfg, doc),
                {"sequence": "sms_ack_instant", "lead_id": doc.get("id"),
                 "request_number": doc.get("request_number"),
                 "tenant_id": doc.get("tenant_id", "main"),
                 "dry_run": not cfg.get("enabled")},
            )
            out["sms"] = sms_res.get("provider")
        await db.specialist_followup_log.insert_one({
            "sequence": "ack_instant",
            "lead_id": doc.get("id"),
            "request_number": doc.get("request_number"),
            "email": doc.get("email"),
            "phone": doc.get("phone"),
            "admin": admin,
            "result": out,
            "dry_run": not cfg.get("enabled"),
            "at": now,
        })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[specialist_followup] ack failed: {e}")
        out["error"] = str(e)[:200]
    return out


# ────────────────────────── cron sequences ───────────────────────────────────
async def _run_specialist_sequence(cfg: dict, sequence: str, delay_seconds: int, subject: str,
                                   sent_field: str, attempts_field: str, template, dry_run: bool) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=delay_seconds)).isoformat()
    q = {
        "source": "specialist_entry",
        "stage": "new",
        "email": {"$nin": ["", None]},
        "created_at": {"$lt": cutoff},
        sent_field: {"$exists": False},
        "$or": [{attempts_field: {"$exists": False}},
                {attempts_field: {"$lt": int(cfg["max_attempts"])}}],
    }
    leads = await db.leads.find(q).sort("created_at", 1).to_list(int(cfg["batch_size"]))
    now = datetime.now(timezone.utc).isoformat()
    sent, failed = 0, 0
    for lead in leads:
        log = {"lead_id": lead.get("id"), "email": lead["email"],
               "source": lead.get("source"), "sequence": sequence,
               "tenant_id": lead.get("tenant_id", "main"),
               "dry_run": dry_run, "at": now}
        # Reunim doc-ul complet (din meta + root) pentru template
        doc = {**(lead.get("meta") or {}), **lead, "id": lead.get("id") or str(lead.get("_id"))}
        if dry_run:
            log["status"] = "dry_run"
            await db.specialist_followup_log.insert_one(dict(log))
            sent += 1
            continue
        try:
            from email_service import send_email
            result = await send_email(to=lead["email"], subject=subject, html=template(doc))
            ok = bool(result and result.get("ok"))
            if ok:
                await db.leads.update_one({"_id": lead["_id"]},
                                          {"$set": {sent_field: now, "updated_at": now}})
                log["status"] = "sent"
                sent += 1
            else:
                raise RuntimeError(str(result))
        except Exception as e:  # noqa: BLE001
            await db.leads.update_one({"_id": lead["_id"]},
                                      {"$inc": {attempts_field: 1},
                                       "$set": {"specialist_followup.last_error": str(e)[:300],
                                                "specialist_followup.last_attempt_at": now}})
            log["status"] = "failed"
            log["error"] = str(e)[:300]
            failed += 1
        await db.specialist_followup_log.insert_one(dict(log))
    summary = {"ran": True, "sequence": sequence, "candidates": len(leads),
               "sent": sent, "failed": failed, "dry_run": dry_run, "at": now}
    if leads:
        logger.info(f"[specialist_followup] {summary}")
    return summary


async def run_reminder_scan(manual: bool = False, dry_run: bool = False) -> dict:
    """Reminder 1h — lead-uri specialist_entry încă în stage=new."""
    cfg = await get_config()
    effective_dry = dry_run or not cfg.get("enabled")
    if not cfg.get("enabled") and not manual:
        return {"ran": False, "reason": "disabled"}
    return await _run_specialist_sequence(
        cfg, sequence="specialist_reminder_1h",
        delay_seconds=int(cfg["reminder_delay_minutes"]) * 60,
        subject=cfg["reminder_subject"],
        sent_field="specialist_followup.reminder_sent_at",
        attempts_field="specialist_followup.reminder_attempts",
        template=_reminder_html, dry_run=effective_dry,
    )


async def run_nurture_scan(manual: bool = False, dry_run: bool = False) -> dict:
    """Nurture 24h — activare portal specialist."""
    cfg = await get_config()
    effective_dry = dry_run or not cfg.get("enabled")
    if not cfg.get("enabled") and not manual:
        return {"ran": False, "reason": "disabled"}
    return await _run_specialist_sequence(
        cfg, sequence="specialist_nurture_24h",
        delay_seconds=int(cfg["nurture_delay_hours"]) * 3600,
        subject=cfg["nurture_subject"],
        sent_field="specialist_followup.nurture_sent_at",
        attempts_field="specialist_followup.nurture_attempts",
        template=_nurture_html, dry_run=effective_dry,
    )


async def run_all_sequences() -> dict:
    """Tick unic pentru scheduler."""
    r1 = await run_reminder_scan()
    r2 = await run_nurture_scan()
    return {"reminder": r1, "nurture": r2}
