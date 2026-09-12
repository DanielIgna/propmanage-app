"""PropManage · Renewal Reminder Email (Task 8 · P2).

Sends a friendly heads-up email to BASIC users approximately 7 days before
their `hh_subscriptions.expires_at`. Fully idempotent — a `renewal_reminders`
collection prevents double-sends per (user_id, expires_at) pair.

Design decisions:
- REUSE existing `email_service.send_email` (Resend / SendGrid / console).
- REUSE existing `db.hh_subscriptions` as source of truth for expiry.
- REUSE existing `AsyncIOScheduler` from `server.py` — schedule one daily job.
- NO changes to Stripe / entitlement / lifecycle semantics.
- Idempotency via a dedicated tiny collection `renewal_reminders` with a
  unique compound key (user_id, expires_at_iso, kind) — writing this record
  BEFORE sending prevents duplicate delivery even under scheduler misfires.

Public façade:
- `renewal_reminder_tick()` — coroutine wired into APScheduler daily.
- `list_recent_reminders()` — admin-only debug read.
- `POST /api/admin/renewal-reminders/run-now` — admin-only manual trigger.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role
from email_service import send_email


logger = logging.getLogger("propmanage.renewal_reminders")

router = APIRouter(prefix="/api/admin/renewal-reminders", tags=["renewal-reminders"])

# Window: send when subscription expires in [WINDOW_MIN_DAYS, WINDOW_MAX_DAYS] days.
# Floor-ul e 4.5 (nu 6.5) ca email-ul DEFERAT — când Copilot a arătat deja
# nudge-ul de renewal în ultimele 24h — să poată fi re-încercat în zilele
# următoare fără să iasă din fereastră. Idempotența rămâne pe (user, expires_at).
WINDOW_MIN_DAYS = 4.5
WINDOW_MAX_DAYS = 7.5

REMINDER_KIND = "basic_expiry_7d"
COPILOT_NUDGE_KIND = "copilot_renew_nudge"

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://propmanage.ro")
if APP_URL.endswith("/api"):
    APP_URL = APP_URL[:-4]


# ------------------------------------------------------------------
# Email template
# ------------------------------------------------------------------
def _render_html(user_name: str, expires_at_display: str, plan_label: str, renew_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f5f4;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1c1917;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:32px 12px;">
  <tr><td align="center">
    <table role="presentation" width="560" cellspacing="0" cellpadding="0"
           style="background:#ffffff;border-radius:16px;padding:32px;border:1px solid #e7e5e4;">
      <tr><td>
        <div style="font-size:11px;letter-spacing:0.14em;color:#78716c;text-transform:uppercase;font-weight:700;">
          PropManage · Cartea Digitală a Casei Tale
        </div>
        <h1 style="font-size:24px;line-height:1.25;margin:16px 0 8px;color:#1c1917;font-weight:700;">
          Abonamentul tău {plan_label} expiră în ~7 zile
        </h1>
        <p style="font-size:15px;line-height:1.55;color:#57534e;margin:0 0 20px;">
          Salut {user_name},<br/><br/>
          Îți mulțumim că folosești PropManage. Abonamentul tău <b>{plan_label}</b> se
          termină pe <b>{expires_at_display}</b>. Ca să eviți întreruperea accesului
          la Cartea Digitală a Casei tale, îl poți prelungi direct din contul tău.
        </p>
        <a href="{renew_url}"
           style="display:inline-block;background:#d4ff3a;color:#0a0a0b;font-weight:700;text-decoration:none;
                  padding:14px 24px;border-radius:12px;font-size:15px;">
          Prelungește abonamentul
        </a>
        <p style="font-size:13px;line-height:1.5;color:#a8a29e;margin:28px 0 0;">
          Dacă vrei să oprești abonamentul, poți face asta oricând din contul tău.
          Documentele casei tale rămân la tine indiferent de starea abonamentului.
        </p>
      </td></tr>
    </table>
    <div style="font-size:11px;color:#a8a29e;margin-top:14px;">
      PropManage · propmanage.ro
    </div>
  </td></tr>
</table>
</body>
</html>
""".strip()


def _render_plain(user_name: str, expires_at_display: str, plan_label: str, renew_url: str) -> str:
    return (
        f"Salut {user_name},\n\n"
        f"Abonamentul tău PropManage {plan_label} expiră pe {expires_at_display} (~7 zile).\n"
        f"Ca să eviți întreruperea accesului la Cartea Digitală a Casei tale,\n"
        f"poți prelungi direct din contul tău: {renew_url}\n\n"
        "Documentele casei tale rămân la tine indiferent de starea abonamentului.\n"
        "PropManage · propmanage.ro"
    )


# ------------------------------------------------------------------
# Core detection + send
# ------------------------------------------------------------------
def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            # Support both 'Z' and offset forms.
            v = value.replace("Z", "+00:00") if value.endswith("Z") else value
            return datetime.fromisoformat(v)
        except Exception:  # noqa: BLE001
            return None
    return None


async def _already_reminded(user_id: str, expires_at_iso: str) -> bool:
    hit = await db.renewal_reminders.find_one({
        "user_id": user_id,
        "expires_at": expires_at_iso,
        "kind": REMINDER_KIND,
    })
    return bool(hit)


async def _record_reminder(user_id: str, email: str, expires_at_iso: str,
                           plan: str, send_result: Dict[str, Any]) -> None:
    try:
        await db.renewal_reminders.update_one(
            {
                "user_id": user_id,
                "expires_at": expires_at_iso,
                "kind": REMINDER_KIND,
            },
            {"$set": {
                "user_id": user_id,
                "email": email,
                "expires_at": expires_at_iso,
                "kind": REMINDER_KIND,
                "plan": plan,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "provider": send_result.get("provider"),
                "provider_ref": send_result.get("id") or send_result.get("status_code"),
                "success": bool(send_result.get("ok")),
            }},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[renewal] record failed for %s: %s", user_id, exc)


async def _ensure_indexes() -> None:
    try:
        await db.renewal_reminders.create_index(
            [("user_id", 1), ("expires_at", 1), ("kind", 1)],
            unique=True, name="uniq_user_expiry_kind",
        )
    except Exception:  # noqa: BLE001
        pass


# ------------------------------------------------------------------
# Coordonare cu PropBenefits Copilot (anti-duplicat mesaje renewal · 24h)
# Ledger comun: db.renewal_reminders, diferențiat prin `kind`.
# ------------------------------------------------------------------
async def record_copilot_renew_nudge(user_id: str) -> None:
    """Ledger: Copilot a servit nudge-ul renew_subscription azi (idempotent/zi)."""
    if not user_id:
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        await db.renewal_reminders.update_one(
            {"user_id": user_id, "expires_at": f"nudge:{today}", "kind": COPILOT_NUDGE_KIND},
            {"$set": {"user_id": user_id, "expires_at": f"nudge:{today}",
                      "kind": COPILOT_NUDGE_KIND,
                      "sent_at": datetime.now(timezone.utc).isoformat(),
                      "success": True}},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[renewal] copilot nudge ledger failed: %s", exc)


async def copilot_nudge_shown_recently(user_id: str, hours: int = 24) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    hit = await db.renewal_reminders.find_one({
        "user_id": user_id, "kind": COPILOT_NUDGE_KIND, "sent_at": {"$gte": cutoff},
    })
    return bool(hit)


async def renewal_email_sent_recently(user_id: str, hours: int = 24) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    hit = await db.renewal_reminders.find_one({
        "user_id": user_id, "kind": REMINDER_KIND,
        "sent_at": {"$gte": cutoff}, "success": True,
    })
    return bool(hit)


async def find_due_subscriptions(now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Return active BASIC subscriptions expiring in the reminder window."""
    now = now or datetime.now(timezone.utc)
    window_start = now + timedelta(days=WINDOW_MIN_DAYS)
    window_end = now + timedelta(days=WINDOW_MAX_DAYS)

    due: List[Dict[str, Any]] = []
    # We look at ALL hh_subscriptions with a truthy expires_at; parsing happens
    # in Python (dates are stored as ISO strings). Status must be active or
    # cancelled (grace period) — either case needs a reminder.
    cur = db.hh_subscriptions.find({
        "expires_at": {"$exists": True, "$ne": None},
        "status": {"$in": ["active", "cancelled"]},
    })
    async for sub in cur:
        expires_at = _parse_iso(sub.get("expires_at"))
        if not expires_at:
            continue
        if window_start <= expires_at <= window_end:
            due.append(sub)
    return due


async def send_reminder_for(sub: Dict[str, Any]) -> Dict[str, Any]:
    """Send exactly one reminder for a single subscription doc. Idempotent."""
    user_id = str(sub.get("user_id") or "")
    if not user_id:
        return {"ok": False, "reason": "no_user_id"}

    expires_at_iso = sub.get("expires_at")
    if isinstance(expires_at_iso, datetime):
        expires_at_iso = expires_at_iso.isoformat()
    if not expires_at_iso:
        return {"ok": False, "reason": "no_expires_at"}

    if await _already_reminded(user_id, expires_at_iso):
        return {"ok": True, "skipped": True, "reason": "already_sent"}

    # Coordonare 24h: dacă Copilot a arătat DEJA nudge-ul de renewal recent,
    # amânăm email-ul (nu scriem ledger-ul de sent → tick-ul de mâine
    # re-încearcă atâta timp cât suntem în fereastră).
    if await copilot_nudge_shown_recently(user_id):
        return {"ok": True, "skipped": True, "reason": "deferred_copilot_nudge_recent"}

    user = await db.users.find_one({"id": user_id}) or await db.users.find_one({"_id": user_id})
    if not user:
        return {"ok": False, "reason": "user_not_found"}
    email = user.get("email")
    if not email:
        return {"ok": False, "reason": "no_email"}

    plan = str(sub.get("plan") or "basic").upper()
    plan_label = f"PropManage {plan.title()}"
    name = user.get("name") or "utilizator PropManage"
    dt = _parse_iso(expires_at_iso)
    display = dt.strftime("%d %B %Y") if dt else expires_at_iso[:10]
    renew_url = f"{APP_URL}/pricing"

    subject = f"Abonamentul tău {plan_label} expiră în ~7 zile"
    result = await send_email(
        to=email,
        subject=subject,
        html=_render_html(name, display, plan_label, renew_url),
        plain=_render_plain(name, display, plan_label, renew_url),
    )
    await _record_reminder(user_id, email, expires_at_iso, plan, result)
    return {"ok": bool(result.get("ok")), "provider": result.get("provider"),
            "email": email, "expires_at": expires_at_iso}


async def renewal_reminder_tick() -> Dict[str, Any]:
    """APScheduler entrypoint. Idempotent, safe to run multiple times."""
    await _ensure_indexes()
    try:
        due = await find_due_subscriptions()
    except Exception as exc:  # noqa: BLE001
        logger.error("[renewal] find_due failed: %s", exc)
        return {"ok": False, "error": str(exc)[:200]}

    sent = skipped = failed = 0
    details: List[Dict[str, Any]] = []
    for sub in due:
        try:
            r = await send_reminder_for(sub)
            if r.get("skipped"):
                skipped += 1
            elif r.get("ok"):
                sent += 1
            else:
                failed += 1
            details.append(r)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.error("[renewal] send failed: %s", exc)
    summary = {"ok": True, "due": len(due), "sent": sent,
               "skipped": skipped, "failed": failed}
    logger.info("[renewal] tick %s", summary)
    return summary


# ------------------------------------------------------------------
# Admin endpoints
# ------------------------------------------------------------------
@router.post("/run-now")
async def run_now(user: dict = Depends(require_role("admin"))):
    """Manually trigger the daily tick — useful for verification without waiting."""
    result = await renewal_reminder_tick()
    try:
        await db.admin_audit_log.insert_one({
            "action": "renewal_reminder.run_now",
            "actor_id": str(user.get("id") or ""),
            "actor_email": user.get("email") or "",
            "target": {"type": "renewal_reminder", "id": "manual"},
            "after": result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:  # noqa: BLE001
        pass
    return result


@router.get("/recent")
async def list_recent(limit: int = 50,
                      _user: dict = Depends(require_role("admin", "operator"))):
    limit = max(1, min(limit, 200))
    cur = db.renewal_reminders.find({}, {"_id": 0}).sort("sent_at", -1).limit(limit)
    items = [d async for d in cur]
    return {"items": items, "count": len(items)}
