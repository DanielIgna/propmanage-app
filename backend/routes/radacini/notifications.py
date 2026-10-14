"""Notificări Rădăcini: aceleași trei canale ca `services.notify` (în aplicație, email, push web), dar cu
identitate proprie — subiect „Rădăcini: …”, text escape-uit în HTML și link ABSOLUT către aplicație.
`services.notify` nu se modifică (e partajat cu PropManage)."""
import asyncio
import html
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

from .bridge import db, send_email, send_web_push

log = logging.getLogger(__name__)

SUBJECT_PREFIX = "Rădăcini: "
# Prima variabilă setată (și validă) dă baza linkurilor din email. Fără niciuna, emailul pleacă fără link
# (nu inventăm un domeniu). `RADACINI_PUBLIC_URL` permite un domeniu propriu pentru Rădăcini.
_BASE_URL_VARS = ("RADACINI_PUBLIC_URL", "APP_PUBLIC_URL", "FRONTEND_PUBLIC_URL", "FRONTEND_URL")
_PUSH_TASKS: set = set()  # referințe tari: asyncio ține doar referințe slabe la task-uri


def public_base_url() -> Optional[str]:
    for var in _BASE_URL_VARS:
        value = (os.environ.get(var) or "").strip().rstrip("/")
        if value.startswith(("http://", "https://")):
            return value
    return None


def internal_path(link: Optional[str]) -> Optional[str]:
    """Doar căi interne (încep cu un singur „/”, fără spații, ghilimele sau paranteze unghiulare)."""
    if isinstance(link, str) and link.startswith("/") and not link.startswith("//") \
            and not any(c in link for c in ' "\'<>\\\r\n\t'):
        return link
    return None


def absolute_link(link: Optional[str]) -> Optional[str]:
    path, base = internal_path(link), public_base_url()
    return f"{base}{path}" if path and base else None


def build_email(title: str, message: str, link: Optional[str]) -> tuple[str, str]:
    """(html, text). Titlul și mesajul sunt escape-uite; linkul (dacă există) e absolut și escape-uit."""
    url = absolute_link(link)
    safe_title = html.escape(title or "")
    safe_message = html.escape(message or "").replace("\n", "<br>")
    body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#1c1917;line-height:1.5">'
        f'<h2 style="margin:0 0 12px;color:#166534">{safe_title}</h2>'
        f'<p style="margin:0 0 16px">{safe_message}</p>'
    )
    text = f"{title}\n\n{message}"
    if url:
        body += (
            f'<p style="margin:0 0 16px"><a href="{html.escape(url, quote=True)}" '
            'style="color:#166534;font-weight:bold">Deschide în Rădăcini</a></p>'
        )
        text += f"\n\n{url}"
    body += '<p style="margin:24px 0 0;color:#78716c;font-size:12px">Rădăcini — agricultură de proximitate.</p></div>'
    return body, text


async def _send_email(user_id: str, title: str, message: str, link: Optional[str]) -> None:
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)}, {"email": 1, "is_demo_account": 1})
    except Exception:  # noqa: BLE001 — id invalid
        return
    # Conturile de test (@test.radacini.ro) nu au căsuță reală: nu trimitem email către ele.
    if not user or not user.get("email") or user.get("is_demo_account"):
        return
    body, text = build_email(title, message, link)
    await send_email(user["email"], f"{SUBJECT_PREFIX}{title}", body, text)


async def radacini_notify(user_id: str, title: str, message: str, link: Optional[str] = None, type_: str = "info") -> None:
    """Notificare în aplicație (colecția `notifications`, aceeași formă ca `services.notify`) + email + push web.
    Emailul și push-ul sunt „best effort”: o eroare la ele nu anulează notificarea din aplicație."""
    user_id = str(user_id)
    await db.notifications.insert_one({
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": type_,
        "link": link,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        await _send_email(user_id, title, message, link)
    except Exception:  # noqa: BLE001
        log.warning("radacini: emailul de notificare nu a putut fi trimis", exc_info=True)
    try:
        task = asyncio.create_task(send_web_push(user_id, f"{SUBJECT_PREFIX}{title}", message, link))
        _PUSH_TASKS.add(task)
        task.add_done_callback(_PUSH_TASKS.discard)
    except Exception:  # noqa: BLE001
        log.warning("radacini: push-ul nu a putut fi programat", exc_info=True)
