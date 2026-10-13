"""Single place where Rădăcini imports PropManage functionality.

Rădăcini modules must not import PropManage routes/services directly; they go
through this file so the coupling to PropManage stays in one spot.
"""
from db import db  # noqa: F401
from core_utils import serialize_doc  # noqa: F401
from deps import block_in_impersonation, get_current_user  # noqa: F401
from event_bus import emit  # noqa: F401
from services import notify  # noqa: F401


def is_super_admin(user: dict) -> bool:
    """Super-admin PropManage: tratat ca manager în Rădăcini."""
    return user.get("role") == "admin" and user.get("admin_scope") in (None, "", "general")


__all__ = ["db", "serialize_doc", "get_current_user", "block_in_impersonation", "emit", "notify", "is_super_admin"]
