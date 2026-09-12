"""Cross-cutting services: email, in-app notify, web push, activity log."""
import os
import json
import logging
import asyncio
import httpx
from typing import Optional
from datetime import datetime, timezone
from bson import ObjectId

from db import db

logger = logging.getLogger(__name__)

# ============= EMAIL =============
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
SENDGRID_SENDER = os.environ.get("SENDGRID_SENDER", "noreply@propmanage.io")


async def send_email(to_email: str, subject: str, html_body: str):
    """Send email via SendGrid with graceful fallback to console logging."""
    if not SENDGRID_API_KEY or not SENDGRID_API_KEY.startswith("SG."):
        logger.info(f"[EMAIL DEMO] To: {to_email} | Subject: {subject}")
        await db.email_log.insert_one({
            "to": to_email,
            "subject": subject,
            "body": html_body,
            "demo": True,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"status": "demo", "to": to_email}
    try:
        async with httpx.AsyncClient(timeout=10) as cli:
            r = await cli.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": SENDGRID_SENDER, "name": "PropManage"},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_body}],
                }
            )
            await db.email_log.insert_one({
                "to": to_email, "subject": subject,
                "status_code": r.status_code,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            })
            return {"status": "sent" if r.status_code < 300 else "failed", "code": r.status_code}
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return {"status": "error", "error": str(e)}


# ============= WEB PUSH (VAPID) =============
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY_PEM = os.environ.get("VAPID_PRIVATE_KEY_PEM")
VAPID_CLAIM_EMAIL = os.environ.get("VAPID_CLAIM_EMAIL", "mailto:admin@propmanage.io")


async def send_web_push(user_id: str, title: str, message: str, link: Optional[str] = None):
    """Fire-and-forget web push for all this user's subscribed devices."""
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY_PEM:
        return
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        return
    subs = await db.push_subscriptions.find({"user_id": user_id}).to_list(20)
    if not subs:
        return
    payload = json.dumps({"title": title, "message": message, "link": link or "/"})
    private_key = VAPID_PRIVATE_KEY_PEM.replace("\\n", "\n")
    stale_endpoints = []
    for sub in subs:
        try:
            webpush(
                subscription_info={"endpoint": sub["endpoint"], "keys": sub["keys"]},
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
                ttl=86400,
            )
        except WebPushException as e:
            code = getattr(e.response, "status_code", None)
            if code in (404, 410):
                stale_endpoints.append(sub["endpoint"])
            else:
                logging.warning(f"WebPush failed for user {user_id}: {e}")
        except Exception as e:
            logging.warning(f"WebPush error: {e}")
    if stale_endpoints:
        await db.push_subscriptions.delete_many({"endpoint": {"$in": stale_endpoints}})


# ============= IN-APP NOTIFY =============
async def notify(user_id: str, title: str, message: str, type_: str = "info", link: str = None):
    """Create in-app notification + send email + web push."""
    await db.notifications.insert_one({
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": type_,
        "link": link,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user and user.get("email"):
        html = f"<h2>{title}</h2><p>{message}</p>"
        if link:
            html += f'<p><a href="{link}">Vezi detalii</a></p>'
        await send_email(user["email"], f"PropManage: {title}", html)
    asyncio.create_task(send_web_push(user_id, title, message, link))


# ============= ACTIVITY EVENT LOGGING =============
async def log_event(
    request_id: Optional[str],
    event_type: str,
    actor: Optional[dict] = None,
    payload: Optional[dict] = None,
    property_id: Optional[str] = None,
):
    """Append an immutable event. Delegates to the canonical XOS Event Bus (Felia 1)."""
    try:
        from event_bus import emit
        await emit(event_type, request_id=request_id, property_id=property_id, actor=actor, payload=payload)
    except Exception as e:
        logging.warning(f"log_event failed: {e}")
