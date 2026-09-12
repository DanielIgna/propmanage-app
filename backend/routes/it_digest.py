"""IT Sprint Health Digest — weekly AI-powered email about dev-team health.

Composes a Sunday-evening (default 18:00 Europe/Bucharest) digest using the
existing AI Performance Copilot (Claude Sonnet 4.5) and ships it to the founder
via Resend.

Endpoints (super-admin only):
  GET  /api/admin/it-collaborators/digest/settings
  POST /api/admin/it-collaborators/digest/settings
  POST /api/admin/it-collaborators/digest/run         — generate + send NOW
  POST /api/admin/it-collaborators/digest/preview     — render HTML (no send)
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from db import db
from deps import get_current_user
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.it_digest")
router = APIRouter(prefix="/api/admin/it-collaborators/digest", tags=["admin-it-digest"])

SETTINGS_KEY = "it_sprint_digest"

DEFAULT_SETTINGS = {
    "enabled": True,
    "recipient_email": "admin@propmanage.io",
    "day_of_week": "sun",   # apscheduler cron format
    "hour": 18,
    "minute": 0,
    "last_sent_at": None,
    "last_status": None,
    "last_error": None,
}


def _require_super(user: dict) -> None:
    if not is_super_admin(user):
        raise HTTPException(403, "Doar super admin poate gestiona Sprint Health Digest.")


async def _get_settings() -> dict:
    doc = await db.app_settings.find_one({"_id": SETTINGS_KEY})
    if not doc:
        return {**DEFAULT_SETTINGS}
    return {**DEFAULT_SETTINGS, **{k: v for k, v in doc.items() if k != "_id"}}


async def _save_settings(patch: dict) -> dict:
    cur = await _get_settings()
    cur.update(patch)
    cur["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.app_settings.update_one(
        {"_id": SETTINGS_KEY},
        {"$set": cur},
        upsert=True,
    )
    return cur


class DigestSettingsPatch(BaseModel):
    enabled: Optional[bool] = None
    recipient_email: Optional[EmailStr] = None
    day_of_week: Optional[str] = None
    hour: Optional[int] = None
    minute: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Core composer — runs Copilot + renders the HTML body
# ─────────────────────────────────────────────────────────────────────────────
RISK_LABEL = {"low": "Sub control", "medium": "Atenție", "high": "Critic"}
RISK_COLOR = {"low": "#0a8a5f", "medium": "#c2700a", "high": "#bc2c2c"}


async def _compose_digest_html(report: dict) -> tuple[str, str]:
    """Returns (subject, html_body) for a single AI report."""
    from email_service import _layout

    risk = (report.get("risk_level") or "medium").lower()
    risk_lbl = RISK_LABEL.get(risk, "Atenție")
    risk_col = RISK_COLOR.get(risk, "#c2700a")
    score = int(report.get("sprint_risk_score") or 0)
    week = datetime.now(timezone.utc).strftime("%Y-W%V")

    perf_rows = ""
    for t in (report.get("top_performers") or [])[:5]:
        perf_rows += f"""
        <tr><td style="padding:6px 0;border-bottom:1px solid #f0e9d8;">
          <strong style="color:#0a8a5f;">▲ {t.get('name','—')}</strong><br/>
          <span style="color:#5a5a5a;font-size:13px;">{t.get('reason','')}</span>
        </td></tr>"""

    risk_rows = ""
    for t in (report.get("at_risk") or [])[:5]:
        action = t.get("recommended_action") or ""
        action_html = f'<div style="margin-top:4px;padding:6px 10px;background:#fff5e6;border-left:3px solid #c2700a;border-radius:4px;color:#7a4d00;font-size:12px;">➜ {action}</div>' if action else ""
        risk_rows += f"""
        <tr><td style="padding:6px 0;border-bottom:1px solid #f0e9d8;">
          <strong style="color:#bc2c2c;">▼ {t.get('name','—')}</strong><br/>
          <span style="color:#5a5a5a;font-size:13px;">{t.get('reason','')}</span>
          {action_html}
        </td></tr>"""

    rec_list = ""
    for r in (report.get("team_recommendations") or [])[:6]:
        rec_list += f'<li style="margin:4px 0;">{r}</li>'

    body = f"""
    <h1 style="font-family:Georgia,serif;color:#1a1a1a;font-size:24px;margin:0 0 8px 0;">🚦 Sprint Health Digest</h1>
    <p style="color:#5a5a5a;margin:0 0 24px 0;">Săptămâna {week} · raport AI Performance Copilot · {report.get('analyzed_count',0)} colaboratori activi</p>

    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px;">
      <tr>
        <td style="background:{risk_col};color:#fff;padding:18px 20px;border-radius:8px;">
          <div style="font-size:11px;letter-spacing:1.5px;text-transform:uppercase;opacity:.85;">Nivel risc echipă</div>
          <div style="font-size:28px;font-weight:bold;margin-top:4px;">{risk_lbl}</div>
          <div style="font-size:13px;opacity:.92;margin-top:2px;">Sprint Risk Score: <strong>{score}/100</strong></div>
        </td>
      </tr>
    </table>

    <p style="color:#333;line-height:1.55;font-size:14px;">{report.get('summary','')}</p>

    <h3 style="font-family:Georgia,serif;color:#1a1a1a;margin:24px 0 8px 0;">Top performers</h3>
    <table width="100%" cellpadding="0" cellspacing="0" border="0">{perf_rows or '<tr><td style="color:#999;font-size:13px;">—</td></tr>'}</table>

    <h3 style="font-family:Georgia,serif;color:#1a1a1a;margin:24px 0 8px 0;">În atenție</h3>
    <table width="100%" cellpadding="0" cellspacing="0" border="0">{risk_rows or '<tr><td style="color:#999;font-size:13px;">—</td></tr>'}</table>

    {f'<h3 style="font-family:Georgia,serif;color:#1a1a1a;margin:24px 0 8px 0;">Recomandări pentru echipă</h3><ul style="color:#333;line-height:1.6;font-size:14px;padding-left:18px;">{rec_list}</ul>' if rec_list else ''}

    <p style="color:#888;font-size:11px;margin-top:32px;border-top:1px solid #eee;padding-top:12px;">
      Rapoartele estimate de AI nu reprezintă obligații ferme. Decizia finală aparține echipei de conducere.
    </p>
    """
    subject = f"PropManage · Sprint Health Digest · {week} · {risk_lbl}"
    html = _layout(
        title=subject,
        preheader=f"Sprint Risk {score}/100 · {report.get('analyzed_count',0)} colaboratori",
        body_html=body,
        cta_url=f"{os.environ.get('APP_PUBLIC_URL','https://propmanage.ro')}/admin/it-collaborators/copilot",
        cta_label="Deschide AI Copilot",
    )
    return subject, html


async def _run_copilot_now(user_email: str = "system_digest") -> dict:
    """Runs the IT Performance Copilot and returns the AI report."""
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY missing")

    docs = []
    async for d in db.it_collaborators.find({"status": "active"}):
        m = d.get("metrics") or {}
        docs.append({
            "name": d.get("name"),
            "role": d.get("role"),
            "seniority": d.get("seniority"),
            "tech": d.get("tech_stack") or [],
            "bugs_introduced": m.get("bugs_introduced", 0),
            "tasks_completed": m.get("tasks_completed", 0),
            "review_score": m.get("review_score", 0),
            "last_sprint": m.get("last_sprint"),
        })
    if not docs:
        raise RuntimeError("Niciun colaborator activ pentru digest.")

    system = (
        "Ești un Engineering Manager senior. Generezi un raport săptămânal pentru "
        "Founder-ul PropManage despre starea echipei IT. Răspunzi DOAR cu JSON valid: "
        "{summary, risk_level('low'|'medium'|'high'), top_performers:[{name,reason}], "
        "at_risk:[{name,reason,recommended_action}], team_recommendations:[str], "
        "sprint_risk_score(0-100)}. Limba: română. Maxim 5 top + 5 at_risk."
    )
    import json
    prompt = "Metrici echipă pentru raport săptămânal:\n" + json.dumps(docs, ensure_ascii=False, indent=2)

    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=key,
        session_id=f"it_digest_{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    raw = await chat.send_message(UserMessage(text=prompt))
    text = (raw or "").strip()
    if text.startswith("```"):
        text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
    i, j = text.find("{"), text.rfind("}")
    if i == -1 or j <= i:
        raise RuntimeError("AI nu a returnat JSON valid.")
    report = json.loads(text[i:j + 1])
    report["analyzed_count"] = len(docs)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["generated_by"] = user_email
    report["kind"] = "weekly_digest"
    await db.it_copilot_reports.insert_one({**report})
    return report


async def run_weekly_it_sprint_digest():
    """Scheduler entry — runs every Sunday at the configured hour."""
    settings = await _get_settings()
    if not settings.get("enabled", True):
        logger.info("[it_digest] Skipped — disabled in settings.")
        return
    try:
        report = await _run_copilot_now("scheduler")
        subject, html = await _compose_digest_html(report)
        recipient = settings.get("recipient_email") or "admin@propmanage.io"
        from email_service import send_email
        res = await send_email(recipient, subject, html)
        await _save_settings({
            "last_sent_at": datetime.now(timezone.utc).isoformat(),
            "last_status": "ok" if res.get("ok") else "error",
            "last_error": None if res.get("ok") else str(res.get("error"))[:300],
        })
        logger.info(f"[it_digest] Sent to {recipient}: provider={res.get('provider')} ok={res.get('ok')}")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[it_digest] failed: {e}")
        await _save_settings({
            "last_sent_at": datetime.now(timezone.utc).isoformat(),
            "last_status": "error",
            "last_error": str(e)[:300],
        })


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoints
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/settings")
async def get_settings(user=Depends(get_current_user)):
    _require_super(user)
    return await _get_settings()


@router.post("/settings")
async def update_settings(payload: DigestSettingsPatch, user=Depends(get_current_user)):
    _require_super(user)
    patch = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "recipient_email" in patch:
        patch["recipient_email"] = str(patch["recipient_email"]).lower()
    if "hour" in patch:
        h = int(patch["hour"])
        if h < 0 or h > 23:
            raise HTTPException(400, "Ora trebuie să fie 0–23.")
    if "day_of_week" in patch:
        if patch["day_of_week"] not in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}:
            raise HTTPException(400, "day_of_week trebuie să fie mon|tue|wed|thu|fri|sat|sun.")
    updated = await _save_settings(patch)

    # Re-register the scheduler job with the new cron expression
    try:
        from server import scheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz
        scheduler.add_job(
            run_weekly_it_sprint_digest,
            CronTrigger(
                day_of_week=updated["day_of_week"],
                hour=updated["hour"],
                minute=updated.get("minute", 0),
                timezone=pytz.timezone("Europe/Bucharest"),
            ),
            id="it_sprint_digest_weekly",
            replace_existing=True,
            misfire_grace_time=7200,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[it_digest] reschedule failed: {e}")

    return updated


@router.post("/run")
async def run_now(user=Depends(get_current_user)):
    """Generates the digest AND sends the email immediately."""
    _require_super(user)
    try:
        report = await _run_copilot_now(user.get("email") or "manual")
        subject, html = await _compose_digest_html(report)
        settings = await _get_settings()
        recipient = settings.get("recipient_email") or user.get("email") or "admin@propmanage.io"
        from email_service import send_email
        res = await send_email(recipient, subject, html)
        await _save_settings({
            "last_sent_at": datetime.now(timezone.utc).isoformat(),
            "last_status": "ok" if res.get("ok") else "error",
            "last_error": None if res.get("ok") else str(res.get("error"))[:300],
        })
        return {
            "ok": True,
            "sent_to": recipient,
            "provider": res.get("provider"),
            "report": report,
        }
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[it_digest] run failed: {e}")
        raise HTTPException(500, f"Digest failed: {str(e)[:200]}")


@router.post("/preview")
async def preview(user=Depends(get_current_user)):
    """Generates the digest HTML without sending the email."""
    _require_super(user)
    try:
        report = await _run_copilot_now(user.get("email") or "preview")
        subject, html = await _compose_digest_html(report)
        return {"subject": subject, "html": html, "report": report}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Preview failed: {str(e)[:200]}")
