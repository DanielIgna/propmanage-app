"""Starea sistemului Rădăcini pentru manageri: baza de date, configurarea de producție, erorile neprevăzute din
ultimele 24 de ore (jurnalul `radacini_errors`, scris de `RadaciniRoute`) și cozile care așteaptă personalul."""
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from .bridge import EMAIL_PROVIDER, db
from .common import ERROR_RETENTION_DAYS, RadaciniRoute
from .staff import require_staff

router = APIRouter(route_class=RadaciniRoute)
_manager = require_staff("manager")
_ERROR_FIELDS = ("at", "method", "route", "error_type", "message")  # proiecție explicită: doar câmpurile afișate


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


@router.get("/admin/system")
async def system_status(ctx: dict = Depends(_manager)):
    t0 = time.perf_counter()
    try:
        await db.radacini_staff.find_one({}, {"_id": 1})
        db_ok, db_ms = True, round((time.perf_counter() - t0) * 1000)
    except Exception:  # noqa: BLE001
        db_ok, db_ms = False, None

    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    errors = await db.radacini_errors.find(
        {"at": {"$gte": since}}, {k: 1 for k in _ERROR_FIELDS}
    ).sort("at", -1).limit(500).to_list(500)
    by_route = Counter(f"{e.get('method')} {e.get('route')}" for e in errors)

    allowed = [e for e in os.environ.get("RADACINI_ALLOWED_EMAILS", "").split(",") if e.strip()]
    config = {
        "enabled": _flag("RADACINI_ENABLED"),
        "closed_beta": bool(allowed),
        "allowed_count": len(allowed),
        "email_provider": EMAIL_PROVIDER,
        "mark_demo": _flag("RADACINI_MARK_DEMO"),
    }
    queues = {
        "reports_open": await db.radacini_reports.count_documents({"status": "open"}),
        "disputes_open": await db.radacini_disputes.count_documents({"status": {"$in": ["open", "in_mediation"]}}),
        "parcels_pending": await db.radacini_parcels.count_documents({"status": "pending_verification"}),
        "deletion_pending": await db.radacini_deletion_requests.count_documents({"status": "pending"}),
    }
    warnings = []
    if not db_ok:
        warnings.append("Baza de date nu răspunde.")
    elif db_ms and db_ms > 1500:
        warnings.append(f"Baza de date răspunde greu ({db_ms} ms).")
    if EMAIL_PROVIDER == "console":
        warnings.append("Emailurile nu se trimit (lipsește RESEND_API_KEY): invitațiile și notificările pe email nu pleacă.")
    if config["mark_demo"]:
        warnings.append("RADACINI_MARK_DEMO e pornit: datele noi sunt marcate ca demo și pot fi șterse de scriptul de curățare.")
    if len(errors) >= 20:
        warnings.append(f"{len(errors)} erori neprevăzute în ultimele 24 de ore.")
    if queues["reports_open"]:
        warnings.append(f"{queues['reports_open']} raportări de conținut așteaptă decizie.")

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "db": {"ok": db_ok, "latency_ms": db_ms},
        "config": config,
        "queues": queues,
        "errors_24h": len(errors),
        "errors_by_route": [{"route": r, "count": n} for r, n in by_route.most_common(10)],
        "recent_errors": [{k: e.get(k) for k in _ERROR_FIELDS} for e in errors[:20]],
        "error_retention_days": ERROR_RETENTION_DAYS,
        "warnings": warnings,
    }
