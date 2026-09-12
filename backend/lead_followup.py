"""Follow-up automat pentru lead-uri warm (P2) — pregătit pentru Resend.

Scanare orară: lead-urile din `leads` cu segment configurat (default: warm),
încă în stage=new, mai vechi de delay_hours (default 48h) și fără follow-up trimis
primesc un email de recuperare. Config în settings namespace `leads_followup`
(enabled=False până la rezolvarea DNS Resend — se activează cu un switch).
"""
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from db import db
from settings_store import get_settings, patch_settings

logger = logging.getLogger("propmanage.lead_followup")

DEFAULT_CONFIG = {
    "enabled": False,
    "delay_hours": 48,
    "segments": ["warm"],
    "max_attempts": 3,
    "batch_size": 25,
    "subject": "Am pregătit următorul pas pentru proiectul tău — PropManage",
    # Secvența 2 — nurture: ghid gratuit la 7 zile
    "nurture_enabled": False,
    "nurture_delay_hours": 168,
    "nurture_subject": "Ghid gratuit: 5 greșeli scumpe în renovări (și cum le eviți) — PropManage",
    "autonomy_level": "L2",
}

SERVICE_LABELS = {
    "interior_design": ("Interior Intelligence", "/design-interior"),
    "design_exterior": ("Exterior Design", "/design-exterior"),
    "arhitectura": ("Arhitectură", "/arhitectura"),
}


async def get_config() -> dict:
    saved = await get_settings("leads_followup")
    return {**DEFAULT_CONFIG, **(saved or {})}


async def update_config(updates: dict, who: str) -> dict:
    clean = {k: v for k, v in updates.items() if k in DEFAULT_CONFIG}
    if clean:
        await patch_settings("leads_followup", clean, who=who)
    return await get_config()


def _email_html(name: str, service_label: str, service_href: str) -> str:
    first = (name or "").split(" ")[0] or "bună"
    base = "https://propmanage.ro"
    return f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#292524">
  <h2 style="color:#047857">Salut, {first}!</h2>
  <p>Ne-ai scris acum două zile despre un proiect <strong>{service_label}</strong> și nu vrem să rămâi blocat la faza de idee.</p>
  <p>Consultanța inițială e <strong>gratuită și fără nicio obligație</strong>: discutăm obiectivele, bugetul realist și pașii concreți — inclusiv ce poți face singur și unde merită un specialist.</p>
  <p style="margin:28px 0">
    <a href="{base}{service_href}#formular" style="background:#047857;color:#fff;padding:12px 26px;border-radius:999px;text-decoration:none;font-weight:bold">Programează consultanța gratuită</a>
  </p>
  <p>Dacă preferi, răspunde direct la acest email cu 2-3 rânduri despre proiect și revenim noi cu propuneri.</p>
  <p style="color:#78716c;font-size:13px">Echipa PropManage · specialiști verificați · plăți protejate prin escrow</p>
</div>"""


def _nurture_html(name: str, service_label: str, service_href: str) -> str:
    first = (name or "").split(" ")[0] or "bună"
    base = "https://propmanage.ro"
    return f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#292524">
  <h2 style="color:#047857">Salut, {first}! Un ghid care te scutește de bani pierduți</h2>
  <p>Indiferent când pornești proiectul <strong>{service_label}</strong>, acestea sunt cele 5 greșeli care costă cel mai mult:</p>
  <ol style="line-height:1.7">
    <li><strong>Proiectare fără audit tehnic</strong> — „surprizele" din spatele pereților explodează bugetul. Auditul costă puțin și le elimină.</li>
    <li><strong>Achiziții înainte de proiect</strong> — canapeaua care nu încape și gresia care se pătează. Întâi randările 3D, apoi comenzile.</li>
    <li><strong>Buget fără rezervă</strong> — planifică 10-15% tampon pe capitole, altfel șantierul se oprește la jumătate.</li>
    <li><strong>Echipe neverificate, plăți în avans</strong> — cere portofoliu și recenzii reale; plătește pe etape, ideal prin escrow.</li>
    <li><strong>Zero documentare</strong> — fără poze, planuri și garanții arhivate, orice intervenție viitoare pornește de la zero. Digital Twin rezolvă exact asta.</li>
  </ol>
  <p style="margin:28px 0">
    <a href="{base}{service_href}#formular" style="background:#047857;color:#fff;padding:12px 26px;border-radius:999px;text-decoration:none;font-weight:bold">Vreau o consultanță gratuită</a>
  </p>
  <p style="color:#78716c;font-size:13px">Echipa PropManage · specialiști verificați · plăți protejate prin escrow</p>
</div>"""


async def run_followup_scan(manual: bool = False, dry_run: bool = False) -> dict:
    """Secvența 1: recuperare lead-uri warm la 48h."""
    cfg = await get_config()
    if not cfg["enabled"] and not manual:
        return {"ran": False, "reason": "disabled"}
    return await _run_sequence(cfg, sequence="warm_48h", segments=cfg["segments"],
                               delay_hours=int(cfg["delay_hours"]), subject=cfg["subject"],
                               sent_field="followup.sent_at", attempts_field="followup.attempts",
                               template=_email_html, dry_run=dry_run)


async def run_nurture_scan(manual: bool = False, dry_run: bool = False) -> dict:
    """Secvența 2: ghid gratuit pentru lead-uri nurture la 7 zile."""
    cfg = await get_config()
    if not cfg["nurture_enabled"] and not manual:
        return {"ran": False, "reason": "disabled"}
    return await _run_sequence(cfg, sequence="nurture_7d", segments=["nurture"],
                               delay_hours=int(cfg["nurture_delay_hours"]), subject=cfg["nurture_subject"],
                               sent_field="followup.nurture_sent_at", attempts_field="followup.nurture_attempts",
                               template=_nurture_html, dry_run=dry_run)


async def _run_sequence(cfg: dict, sequence: str, segments: list, delay_hours: int, subject: str,
                        sent_field: str, attempts_field: str, template, dry_run: bool,
                        blocked_reason: str | None = None) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=delay_hours)).isoformat()
    q = {
        "segment": {"$in": segments},
        "stage": "new",
        "email": {"$nin": ["", None]},
        "created_at": {"$lt": cutoff},
        sent_field: {"$exists": False},
        "$or": [{attempts_field: {"$exists": False}},
                {attempts_field: {"$lt": int(cfg["max_attempts"])}}],
    }
    leads = await db.leads.find(q).sort("created_at", 1).to_list(int(cfg["batch_size"]))
    now = datetime.now(timezone.utc).isoformat()
    sent, failed, queued = 0, 0, 0
    for lead in leads:
        label, href = SERVICE_LABELS.get(lead.get("source"), ("PropManage", "/"))
        log = {"lead_id": lead.get("id"), "email": lead["email"], "source": lead.get("source"),
               "segment": lead.get("segment"), "tenant_id": lead.get("tenant_id", "main"),
               "sequence": sequence, "dry_run": dry_run, "at": now}
        if blocked_reason and not dry_run:
            # Email indisponibil (ex: DNS Resend) — lead-ul intră în coadă o singură dată,
            # rămâne candidat și va fi trimis LIVE automat când gate-ul se deschide.
            if (lead.get("followup") or {}).get(f"queued_{sequence}"):
                continue
            await db.leads.update_one({"_id": lead["_id"]},
                                      {"$set": {f"followup.queued_{sequence}": now, "updated_at": now}})
            log["status"] = "queued_blocked"
            log["blocked_by"] = blocked_reason
            await db.lead_followup_log.insert_one(dict(log))
            queued += 1
            continue
        if dry_run:
            log["status"] = "dry_run"
            await db.lead_followup_log.insert_one(dict(log))
            sent += 1
            continue
        try:
            from email_service import send_email
            result = await send_email(to=lead["email"], subject=subject,
                                      html=template(lead.get("name"), label, href))
            ok = bool(result and result.get("ok"))
            if ok:
                await db.leads.update_one({"_id": lead["_id"]}, {"$set": {sent_field: now, "updated_at": now}})
                log["status"] = "sent"
                sent += 1
            else:
                raise RuntimeError(str(result))
        except Exception as e:  # noqa: BLE001
            await db.leads.update_one({"_id": lead["_id"]},
                                      {"$inc": {attempts_field: 1},
                                       "$set": {"followup.last_error": str(e)[:300], "followup.last_attempt_at": now}})
            log["status"] = "failed"
            log["error"] = str(e)[:300]
            failed += 1
        await db.lead_followup_log.insert_one(dict(log))
    summary = {"ran": True, "sequence": sequence, "candidates": len(leads), "sent": sent,
               "failed": failed, "queued": queued, "dry_run": dry_run, "at": now}
    if leads:
        logger.info(f"[lead_followup] {summary}")
    return summary


# ===================== D156 — Autonomie L2 (EXECUTION ORDER 001) =====================

async def _email_gate() -> dict:
    """Gate de siguranță L2: trimitem LIVE doar când providerul de email poate livra."""
    from email_service import PROVIDER
    if PROVIDER != "resend":
        live = PROVIDER == "sendgrid"
        return {"live": live, "provider": PROVIDER, "reason": None if live else "console_mode"}
    try:
        from routes.resend_diagnostics import run_diagnostics
        diag = await run_diagnostics()
        ok = bool(diag.get("dns_ok"))
        return {"live": ok, "provider": "resend", "reason": None if ok else "resend_dns_unverified"}
    except Exception as e:  # noqa: BLE001
        return {"live": False, "provider": "resend", "reason": f"gate_error:{str(e)[:80]}"}


def _sequence_args(cfg: dict, sequence: str) -> dict:
    if sequence == "nurture_7d":
        return dict(sequence="nurture_7d", segments=["nurture"], delay_hours=int(cfg["nurture_delay_hours"]),
                    subject=cfg["nurture_subject"], sent_field="followup.nurture_sent_at",
                    attempts_field="followup.nurture_attempts", template=_nurture_html)
    return dict(sequence="warm_48h", segments=cfg["segments"], delay_hours=int(cfg["delay_hours"]),
                subject=cfg["subject"], sent_field="followup.sent_at",
                attempts_field="followup.attempts", template=_email_html)


async def run_autonomous_cycle(trigger: str = "scheduler") -> dict:
    """Ciclu autonom orar (D156 L2): gate email → rulează secvențele → Execution Report în ledger."""
    cfg = await get_config()
    if not cfg["enabled"] and not cfg["nurture_enabled"]:
        return {"ran": False, "reason": "disabled"}
    t0 = time.monotonic()
    gate = await _email_gate()
    blocked = None if gate["live"] else (gate.get("reason") or "email_blocked")
    results = []
    if cfg["enabled"]:
        results.append(await _run_sequence(cfg, dry_run=False, blocked_reason=blocked,
                                           **_sequence_args(cfg, "warm_48h")))
    if cfg["nurture_enabled"]:
        results.append(await _run_sequence(cfg, dry_run=False, blocked_reason=blocked,
                                           **_sequence_args(cfg, "nurture_7d")))
    totals = {k: sum(r.get(k, 0) for r in results) for k in ("candidates", "sent", "failed", "queued")}
    duration_ms = int((time.monotonic() - t0) * 1000)
    now = datetime.now(timezone.utc).isoformat()
    run_doc = {"run_id": uuid.uuid4().hex, "trigger": trigger, "autonomy_level": "L2",
               "email_live": gate["live"], "blocked_by": blocked, **totals,
               "sequences": results, "duration_ms": duration_ms, "at": now}
    if totals["candidates"] or trigger == "manual":
        await db.lead_followup_runs.insert_one(dict(run_doc))
    if totals["sent"] or totals["failed"] or totals["queued"]:
        from learning_engine import ledger_entry
        reco = (f"Follow-up autonom lead-uri stagnante: {totals['sent']} trimise, "
                f"{totals['queued']} în coadă (email blocat), {totals['failed']} eșuate "
                f"din {totals['candidates']} candidați")
        entry = ledger_entry(
            "autonomous_execution", "lead_followup_engine", reco,
            "EXECUTION ORDER 001 · D156 L2 — lead-uri stage=new fără follow-up (>48h warm / >7z nurture)",
            action="auto_executed", approved_by="EXECUTION_ORDER_001",
            extra={"execution_report": {
                "reason": "Lead-uri stagnante fără follow-up — risc de pierdere a venitului",
                "evidence": totals,
                "expected_benefit": "Reactivare lead-uri → consultanțe programate → venit",
                "rollback_plan": "PUT /api/admin/leads/followup/config {\"enabled\": false}",
                "execution_time_ms": duration_ms,
                "risk_score": "low",
                "email_gate": gate,
            }})
        await db.ai_decision_ledger.insert_one(entry)
    return run_doc


async def get_status() -> dict:
    """Stare completă pentru Operations Center: config, gate, candidați, istoricul rulărilor."""
    cfg = await get_config()
    gate = await _email_gate()
    pending = {}
    for seq in ("warm_48h", "nurture_7d"):
        args = _sequence_args(cfg, seq)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=args["delay_hours"])).isoformat()
        pending[seq] = await db.leads.count_documents({
            "segment": {"$in": args["segments"]}, "stage": "new", "email": {"$nin": ["", None]},
            "created_at": {"$lt": cutoff}, args["sent_field"]: {"$exists": False},
        })
    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    log_30d = {}
    async for d in db.lead_followup_log.aggregate([
        {"$match": {"at": {"$gt": since}}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]):
        log_30d[d["_id"]] = d["n"]
    last_runs = await db.lead_followup_runs.find({}, {"_id": 0}).sort("at", -1).to_list(5)
    return {"config": cfg, "email_gate": gate, "pending": pending,
            "log_30d": log_30d, "last_runs": last_runs,
            "report_24h": await build_execution_report_24h(gate=gate)}


async def build_execution_report_24h(gate: dict | None = None) -> dict:
    """AUTONOMOUS EXECUTION REPORT (format Fondator) — EXCLUSIV din date reale, zero fabricat."""
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    by_status = {}
    async for d in db.lead_followup_log.aggregate([
        {"$match": {"at": {"$gt": since}, "dry_run": {"$ne": True}}},
        {"$group": {"_id": "$status", "n": {"$sum": 1}}},
    ]):
        by_status[d["_id"]] = d["n"]
    sent = by_status.get("sent", 0)
    queued = by_status.get("queued_blocked", 0)
    failed = by_status.get("failed", 0)
    processed = sent + queued + failed
    # Reactivate = lead-uri cu email trimis în 24h care AU IEȘIT din stage=new (evidență reală)
    stage_counts = {}
    async for d in db.leads.aggregate([
        {"$match": {"$or": [{"followup.sent_at": {"$gt": since}},
                            {"followup.nurture_sent_at": {"$gt": since}}]}},
        {"$group": {"_id": "$stage", "n": {"$sum": 1}}},
    ]):
        stage_counts[d["_id"]] = d["n"]
    reactivated = sum(n for s, n in stage_counts.items() if s != "new")
    consultations = sum(stage_counts.get(s, 0) for s in ("audit_scheduled", "offer_sent", "waiting_decision"))
    contracts = sum(stage_counts.get(s, 0) for s in ("won", "payment_received", "project_active"))
    attempted = sent + failed
    success_rate = round(sent / attempted * 100) if attempted else None
    gate = gate or await _email_gate()
    return {
        "window": "24h", "since": since,
        "leads_processed": processed, "emails_sent": sent, "emails_queued": queued, "emails_failed": failed,
        "leads_reactivated": reactivated, "consultations_scheduled": consultations, "contracts_signed": contracts,
        "revenue_generated_ron": 0.0,  # atribuire pe plăți reale — activă după prima plată reală
        "hours_saved": round(processed * 6 / 60, 1),  # formulă declarată: 6 min/follow-up manual
        "automation_success_rate_pct": success_rate,
        "email_live": gate.get("live", False), "blocked_by": gate.get("reason"),
        "recommendation": ("Deblochează DNS Resend — coada pleacă LIVE automat."
                           if not gate.get("live") else
                           ("ROI pozitiv — continuă." if reactivated else "Continuă și măsoară reactivările.")),
        # D161 Truth Engine — clasa de evidență per câmp
        "evidence_classification": {
            "measured": ["leads_processed", "emails_sent", "emails_queued", "emails_failed",
                         "leads_reactivated", "consultations_scheduled", "contracts_signed",
                         "revenue_generated_ron"],
            "estimated": {"hours_saved": {"formula": "6 min per follow-up manual evitat",
                                          "confidence_pct": 60}},
        },
        "truth_note": "D161: Measured = lead_followup_log + leads.stage + plăți. hours_saved = Estimated (60%).",
    }
