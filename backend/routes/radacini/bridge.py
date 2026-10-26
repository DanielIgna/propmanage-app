"""Single place where Rădăcini imports PropManage functionality.

Rădăcini modules must not import PropManage routes/services directly; they go
through this file so the coupling to PropManage stays in one spot.
"""
from db import db  # noqa: F401
from core_utils import serialize_doc  # noqa: F401
from deps import block_in_impersonation, get_current_user  # noqa: F401
from email_service import PROVIDER as EMAIL_PROVIDER, send_email  # noqa: F401
from event_bus import emit  # noqa: F401
from routes.admin_console import audit as admin_audit  # noqa: F401
from services import notify, send_web_push  # noqa: F401


def is_super_admin(user: dict) -> bool:
    """Super-admin PropManage: tratat ca manager în Rădăcini."""
    return user.get("role") == "admin" and user.get("admin_scope") in (None, "", "general")


__all__ = [
    "db", "serialize_doc", "get_current_user", "block_in_impersonation", "emit", "notify",
    "send_web_push", "send_email", "EMAIL_PROVIDER", "admin_audit", "is_super_admin",
]
