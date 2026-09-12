"""PropManage — Morning Briefing Digest (daily admin email).

Aggregates the same data points shown in the in-app Morning Briefing widget
and emails a single consolidated report to ADMIN_EMAILS every morning.

By default the email is sent ONLY when there is something to report:
  - At least one healthcheck integration failing
  - Latest smoke-test FAILED
  - Latest data-integrity scan has issues
  - One or more active (non-resolved) incidents
  - Open AI findings with severity high|warning

Pass force=True to send unconditionally (used by the manual test endpoint).
"""
from __future__ import annotations

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import db
from healthcheck_service import compute_healthcheck_report

logger = logging.getLogger("propmanage.admin_briefing_digest")


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

async def _latest_smoke_test() -> Optional[dict]:
    doc = await db.smoke_test_runs.find_one({}, sort=[("started_at", -1)])
    if doc:
        doc.pop("_id", None)
    return doc


async def _latest_data_integrity() -> Optional[dict]:
    doc = await db.data_integrity_runs.find_one({}, sort=[("started_at", -1)])
    if doc:
        doc.pop("_id", None)
    return doc


async def _active_incidents(days: int = 30) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    cursor = db.incidents.find({"started_at": {"$gte": cutoff}}).sort("started_at", -1)
    items: list[dict] = []
    async for d in cursor:
        d.pop("_id", None)
        items.append(d)
    active = [i for i in items if i.get("status") != "resolved"]
    return {"items": items, "active": active, "total": len(items)}


async def _open_ai_findings() -> dict:
    """Mirror of GET /api/admin/ai/findings?status=open shape."""
    counts_by_sev = {"high": 0, "warning": 0, "low": 0}
    total_open = 0
    top: list[dict] = []
    cursor = db.admin_ai_findings.find({"status": "open"}).sort([
        ("severity", -1), ("occurrences", -1), ("last_seen_at", -1),
    ])
    async for f in cursor:
        sev = f.get("severity") or "low"
        counts_by_sev[sev] = counts_by_sev.get(sev, 0) + 1
        total_open += 1
        if len(top) < 5:
            top.append({
                "label": f.get("label"),
                "entity_label": f.get("entity_label"),
                "severity": sev,
                "occurrences": f.get("occurrences", 1),
            })
    return {"counts": {"open": total_open}, "by_severity": counts_by_sev, "top": top}


async def _orchestrator_last_24h() -> dict:
    """Autonomy Orchestrator activity in the last 24h (ledger summary)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    entries = [d async for d in db.orchestrator_ledger.find({"ts": {"$gte": cutoff}}, {"_id": 0})]
    return {
        "actions": len(entries),
        "minutes_saved": sum(e.get("minutes_saved") or 0 for e in entries),
        "auto_resolved": sum(1 for e in entries if e.get("outcome") == "auto_resolved"),
        "escalated": sum(1 for e in entries if e.get("escalated")),
    }


async def _latest_backup() -> Optional[dict]:
    """Latest DB backup run metadata for the Briefing tile."""
    doc = await db.backup_runs.find_one({}, sort=[("started_at", -1)])
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


def _healthcheck_tone(healthcheck: dict) -> str:
    s = healthcheck.get("summary", {})
    if s.get("critical_failed", 0) > 0:
        return "fail"
    if s.get("warnings_failed", 0) > 0:
        return "warn"
    return "ok"


def _smoke_tone(smoke: Optional[dict]) -> str:
    if not smoke:
        return "idle"
    return "ok" if smoke.get("ok") else "fail"


def _integrity_tone(integrity: Optional[dict]) -> str:
    if not integrity:
        return "idle"
    s = integrity.get("summary", {})
    if s.get("critical_failed", 0) > 0:
        return "fail"
    if s.get("total_issues_found", 0) > 0:
        return "warn"
    return "ok"


def _incidents_tone(incidents: dict) -> str:
    if not incidents["active"]:
        return "ok"
    severity_score = {"critical": 3, "major": 2, "minor": 1}
    worst = max(
        (severity_score.get(i.get("severity"), 0) for i in incidents["active"]),
        default=0,
    )
    return "fail" if worst >= 3 else "warn"


def _findings_tone(findings: dict) -> str:
    if findings["counts"]["open"] == 0:
        return "ok"
    by_sev = findings.get("by_severity", {})
    if by_sev.get("high", 0) > 0:
        return "fail"
    return "warn"


def _backup_tone(backup: Optional[dict]) -> str:
    if not backup:
        return "fail"
    try:
        last_ts = datetime.fromisoformat(backup.get("started_at", "").replace("Z", "+00:00"))
        age_h = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600
        if not backup.get("ok") or age_h > 72:
            return "fail"
        if age_h > 36:
            return "warn"
        return "ok"
    except Exception:  # noqa: BLE001
        return "warn"


def _orchestrator_tone(orch: dict) -> str:
    if orch.get("escalated", 0) > 0:
        return "warn"
    if orch.get("actions", 0) == 0:
        return "idle"
    return "ok"


async def compute_briefing_payload() -> dict:
    """Build the full briefing payload (data only, no rendering)."""
    healthcheck = await compute_healthcheck_report()
    smoke = await _latest_smoke_test()
    integrity = await _latest_data_integrity()
    incidents = await _active_incidents(days=30)
    findings = await _open_ai_findings()
    backup = await _latest_backup()
    orchestrator = await _orchestrator_last_24h()

    tones = {
        "hc": _healthcheck_tone(healthcheck),
        "smoke": _smoke_tone(smoke),
        "integ": _integrity_tone(integrity),
        "inc": _incidents_tone(incidents),
        "fi": _findings_tone(findings),
        "backup": _backup_tone(backup),
        "orch": _orchestrator_tone(orchestrator),
    }
    has_fail = any(t == "fail" for t in tones.values())
    has_warn = any(t == "warn" for t in tones.values())
    overall = "fail" if has_fail else ("warn" if has_warn else "ok")

    return {
        "overall": overall,
        "healthcheck": {"tone": tones["hc"], "report": healthcheck},
        "smoke": {"tone": tones["smoke"], "report": smoke},
        "integrity": {"tone": tones["integ"], "report": integrity},
        "incidents": {"tone": tones["inc"], **incidents},
        "findings": {"tone": tones["fi"], **findings},
        "backup": {"tone": tones["backup"], "report": backup},
        "orchestrator": {"tone": tones["orch"], **orchestrator},
    }


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

_TONE_COLORS = {
    "ok":   ("#10b981", "Toate sistemele OK"),
    "warn": ("#f59e0b", "Avertizări"),
    "fail": ("#ef4444", "Probleme critice"),
    "idle": ("#94a3b8", "Inactiv"),
}

_TILE_LABEL = {
    "healthcheck": "Integrări externe",
    "smoke": "Smoke Test E2E",
    "integrity": "Integritate date",
    "incidents": "Incidente publice",
    "findings": "AI Findings",
    "orchestrator": "Autonomy Orchestrator",
}


def _headline_healthcheck(section: dict) -> tuple[str, str]:
    s = (section.get("report") or {}).get("summary", {})
    p_t = f"{s.get('passed', 0)}/{s.get('total', 0)}"
    if s.get("critical_failed", 0) > 0:
        return (f"{s['critical_failed']} integrare critică jos", f"{p_t} OK")
    if s.get("warnings_failed", 0) > 0:
        return (f"{s['warnings_failed']} cu avertizare", f"{p_t} OK")
    return ("Toate integrările OK", f"{p_t} verificate")


def _headline_smoke(section: dict) -> tuple[str, str]:
    last = section.get("report")
    if not last:
        return ("Niciun test rulat", "Activează monitorul în AI Investigator")
    when = last.get("started_at", "")[:16].replace("T", " ")
    if last.get("ok"):
        return (f"{last.get('passed', last.get('total'))}/{last.get('total')} PASS", when)
    return (f"{last.get('failed', 0)} pași eșuați din {last.get('total', 0)}", when)


def _headline_integrity(section: dict) -> tuple[str, str]:
    last = section.get("report")
    if not last:
        return ("Niciun scan rulat", "Rulează din AI Investigator")
    s = last.get("summary", {})
    when = (last.get("started_at") or "")[:16].replace("T", " ")
    if s.get("critical_failed", 0) > 0:
        return (f"{s['critical_failed']} verificări critice eșuate", when)
    if s.get("total_issues_found", 0) > 0:
        return (f"{s['total_issues_found']} probleme detectate", when)
    return ("Toate verificările OK", when)


def _headline_incidents(section: dict) -> tuple[str, str]:
    active = section.get("active", [])
    total = section.get("total", 0)
    if not active:
        return ("Niciun incident activ", f"{total} închise în ultimele 30 zile")
    plural = "e" if len(active) > 1 else ""
    return (
        f"{len(active)} incident{plural} activ{plural}",
        f"Cel mai grav: {active[0].get('title', '—')}",
    )


def _headline_findings(section: dict) -> tuple[str, str]:
    open_count = section.get("counts", {}).get("open", 0)
    by_sev = section.get("by_severity", {})
    if open_count == 0:
        return ("Niciun finding deschis", "Platforma e curată")
    if by_sev.get("high", 0) > 0:
        return (f"{by_sev['high']} findings critice", f"{open_count} deschise total")
    if by_sev.get("warning", 0) > 0:
        return (f"{by_sev['warning']} warnings", f"{open_count} deschise total")
    return (f"{open_count} findings deschise", "Verifică AI Investigator")


def _headline_orchestrator(section: dict) -> tuple[str, str]:
    actions = section.get("actions", 0)
    if actions == 0:
        return ("Nicio situație de gestionat", "Zi liniștită — 0 semnale în ultimele 24h")
    escalated = section.get("escalated", 0)
    minutes = section.get("minutes_saved", 0)
    headline = f"{section.get('auto_resolved', 0)}/{actions} situații rezolvate automat (~{minutes} min salvate)"
    sub = f"{escalated} escaladate la om" if escalated else "0 escaladări — a mers fără intervenție umană"
    return (headline, sub)


_HEADLINE_DISPATCH = {
    "healthcheck": _headline_healthcheck,
    "smoke": _headline_smoke,
    "integrity": _headline_integrity,
    "incidents": _headline_incidents,
    "findings": _headline_findings,
    "orchestrator": _headline_orchestrator,
}


def _tile_headline(key: str, section: dict) -> tuple[str, str]:
    """Return (headline, sub) for a system tile in the email."""
    handler = _HEADLINE_DISPATCH.get(key)
    return handler(section) if handler else ("—", "")


def _render_briefing_html(payload: dict, app_url: str) -> str:
    overall = payload["overall"]
    overall_color, overall_label = _TONE_COLORS.get(overall, _TONE_COLORS["idle"])
    overall_msg = {
        "fail": "Atenție necesară — există probleme critice care impun acțiune.",
        "warn": "Câteva avertizări — verifică detaliile mai jos.",
        "ok":   "Toate sistemele funcționează normal. Zi liniștită!",
    }.get(overall, "Status indisponibil.")

    rows = ""
    for key in ("orchestrator", "healthcheck", "smoke", "integrity", "incidents", "findings"):
        section = payload.get(key, {})
        tone = section.get("tone", "idle")
        color, _ = _TONE_COLORS.get(tone, _TONE_COLORS["idle"])
        headline, sub = _tile_headline(key, section)
        rows += f"""
          <tr>
            <td style="padding:10px 14px; border-bottom:1px solid #2a2a30; vertical-align:top; width:170px;">
              <div style="font-size:10px; text-transform:uppercase; letter-spacing:0.8px; color:#888893;">{_TILE_LABEL[key]}</div>
            </td>
            <td style="padding:10px 14px; border-bottom:1px solid #2a2a30; vertical-align:top;">
              <div style="color:#ffffff; font-size:14px; font-weight:600;">{headline}</div>
              <div style="color:#a8a8b0; font-size:12px; margin-top:2px;">{sub}</div>
            </td>
            <td style="padding:10px 14px; border-bottom:1px solid #2a2a30; vertical-align:top; text-align:right;">
              <span style="display:inline-block; padding:3px 10px; border-radius:999px; background:{color}22; color:{color}; font-size:10px; font-weight:700; letter-spacing:0.5px; text-transform:uppercase;">{tone}</span>
            </td>
          </tr>
        """

    today_str = datetime.now(timezone.utc).strftime("%d %b %Y")

    return f"""
      <p style="color:#c8c8cc;">Bună dimineața,</p>
      <p style="color:#c8c8cc;">Iată briefing-ul automat <strong>PropManage</strong> pentru <strong>{today_str}</strong>:</p>

      <div style="background:{overall_color}15; border:1px solid {overall_color}44; border-radius:14px; padding:16px 18px; margin:18px 0;">
        <div style="font-size:11px; text-transform:uppercase; letter-spacing:1px; color:{overall_color}; font-weight:700; margin-bottom:6px;">Stare generală · {overall_label}</div>
        <div style="color:#ffffff; font-size:15px;">{overall_msg}</div>
      </div>

      <table border="0" cellpadding="0" cellspacing="0" style="width:100%; background:#1a1a1f; border-radius:14px; margin:18px 0; overflow:hidden;">
        {rows}
      </table>

      <p style="color:#a8a8b0; font-size:13px;">Deschide consola admin pentru detalii complete:</p>
      <p>
        <a href="{app_url}/admin" style="display:inline-block; padding:12px 22px; background:#d4ff3a; color:#0a0a0b; text-decoration:none; border-radius:999px; font-weight:700; font-size:13px; letter-spacing:0.3px;">
          Deschide Morning Briefing
        </a>
      </p>
      <p style="color:#666; font-size:11px; margin-top:18px;">
        Acest email este trimis automat zilnic la 09:00 (Europe/Bucharest), <strong>doar când există avertizări sau erori</strong>.
        Pentru a-l opri, scoate adresa ta din ADMIN_EMAILS în setările deployment-ului.
      </p>
    """


# ---------------------------------------------------------------------------
# Sender
# ---------------------------------------------------------------------------

def _admin_recipients() -> list[str]:
    raw = os.environ.get("ADMIN_EMAILS", "") or os.environ.get("ADMIN_EMAIL", "")
    return [e.strip() for e in raw.split(",") if e.strip()]


async def send_morning_briefing_email(force: bool = False) -> dict:
    """Compose & send the morning briefing email.

    Returns a result dict: {sent: bool, reason: str, overall: str, recipients: int}.
    """
    payload = await compute_briefing_payload()
    overall = payload["overall"]

    if not force and overall == "ok":
        logger.info("[MorningBriefing] overall=ok and not forced — skipping email")
        return {"sent": False, "reason": "all_ok", "overall": overall, "recipients": 0}

    recipients = _admin_recipients()
    if not recipients:
        logger.warning("[MorningBriefing] no ADMIN_EMAILS configured — skipping")
        return {"sent": False, "reason": "no_recipients", "overall": overall, "recipients": 0}

    app_url = os.environ.get("APP_PUBLIC_URL", "https://propmanage.ro")
    from email_service import _layout, send_email  # lazy to avoid load-order issues
    body_html = _render_briefing_html(payload, app_url)

    subject_emoji = {"fail": "🚨", "warn": "⚠️", "ok": "✅"}.get(overall, "📊")
    subject = f"{subject_emoji} PropManage Morning Briefing · {datetime.now(timezone.utc).strftime('%d %b')}"
    html = _layout(
        title="Morning Briefing",
        preheader=f"Stare generală: {overall.upper()}",
        body_html=body_html,
        cta_url=f"{app_url}/admin",
        cta_label="Vezi în Admin",
    )

    sent_count = 0
    for r in recipients:
        try:
            res = await send_email(r, subject, html)
            if res.get("ok"):
                sent_count += 1
        except Exception as e:  # noqa: BLE001
            logger.error(f"[MorningBriefing] send to {r} failed: {e}")

    logger.info(f"[MorningBriefing] sent overall={overall} to {sent_count}/{len(recipients)} admin(s)")
    return {
        "sent": sent_count > 0,
        "reason": "delivered" if sent_count > 0 else "all_failed",
        "overall": overall,
        "recipients": sent_count,
        "total_recipients": len(recipients),
    }


async def run_morning_briefing_job() -> None:
    """APScheduler entrypoint — fire-and-forget, never raises."""
    try:
        await send_morning_briefing_email(force=False)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[MorningBriefing][cron] failed: {e}")
