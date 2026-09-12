"""Twin Scheduled Actions — natural-language cron via Twin chat.

Workflow:
1. Twin detects schedule intent in `_detect_schedule_intent()`.
2. The /ask endpoint returns an action_proposal that includes `schedule_info`.
3. After user confirms, /execute-action persists in ``twin_scheduled_actions``
   and registers an APScheduler job (one-shot DateTrigger or recurring CronTrigger).
4. On execution, the job calls the action dispatcher + logs result.

Allowed schedules:
- One-shot: "luni 06:00", "mâine la 9", "în 2 ore"
- Recurring: "în fiecare luni", "în fiecare zi la 06:00", "1 a lunii"

Only super-admins can schedule. Max 20 active schedules per user.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

import pytz
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
import dateparser

from db import db

logger = logging.getLogger("propmanage.twin.schedule")

BUCHAREST_TZ = pytz.timezone("Europe/Bucharest")
MAX_SCHEDULES_PER_USER = 20

# Day-of-week mapping (Romanian)
RO_DOW = {
    "luni": 0, "lun": 0,
    "marți": 1, "marti": 1, "mar": 1,
    "miercuri": 2, "mie": 2,
    "joi": 3,
    "vineri": 4, "vin": 4,
    "sâmbătă": 5, "sambata": 5, "sam": 5,
    "duminică": 6, "duminica": 6, "dum": 6,
}

RECURRING_KEYWORDS = ["fiecare", "saptamanal", "săptămânal", "zilnic", "lunar", "every", "weekly", "daily", "monthly"]


def _detect_schedule_intent(question: str) -> Optional[dict]:
    """Detect when a question contains scheduling info.

    Returns: {kind: 'date'|'cron', when: datetime|dict, label: str} or None.
    """
    q = question.lower().strip()
    is_recurring = any(kw in q for kw in RECURRING_KEYWORDS)

    # Recurring patterns
    if is_recurring:
        # "în fiecare <day_of_week> la HH[:MM]"
        m = re.search(r"(?:fiecare|every)\s+(luni|marți|marti|miercuri|joi|vineri|sâmbătă|sambata|duminică|duminica)\s*(?:la|at)?\s*(\d{1,2})(?::(\d{2}))?", q)
        if m:
            dow = RO_DOW.get(m.group(1))
            hour = int(m.group(2))
            minute = int(m.group(3) or 0)
            if dow is not None and 0 <= hour <= 23:
                return {
                    "kind": "cron",
                    "when": {"day_of_week": dow, "hour": hour, "minute": minute},
                    "label": f"În fiecare {m.group(1)} la {hour:02d}:{minute:02d}",
                }
        # "în fiecare zi la HH[:MM]"
        m = re.search(r"(?:fiecare zi|în fiecare zi|zilnic|daily)\s*(?:la|at)?\s*(\d{1,2})(?::(\d{2}))?", q)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            return {
                "kind": "cron",
                "when": {"hour": hour, "minute": minute},
                "label": f"În fiecare zi la {hour:02d}:{minute:02d}",
            }
        # "1 a lunii la HH:MM" or "în fiecare 1 a lunii"
        m = re.search(r"(?:în fiecare\s+)?(\d{1,2})\s*(?:a lunii|a fiecărei luni|of the month)\s*(?:la|at)?\s*(\d{1,2})?(?::(\d{2}))?", q)
        if m:
            day = int(m.group(1))
            hour = int(m.group(2) or 9)
            minute = int(m.group(3) or 0)
            if 1 <= day <= 28:
                return {
                    "kind": "cron",
                    "when": {"day": day, "hour": hour, "minute": minute},
                    "label": f"În fiecare {day} a lunii la {hour:02d}:{minute:02d}",
                }
        return None

    # One-shot — use dateparser with Romanian locale
    parsed = dateparser.parse(
        q,
        languages=["ro", "en"],
        settings={
            "TIMEZONE": "Europe/Bucharest",
            "RETURN_AS_TIMEZONE_AWARE": True,
            "PREFER_DATES_FROM": "future",
        },
    )
    if parsed:
        # Must be in the future, max 1 year ahead
        now = datetime.now(timezone.utc)
        if parsed <= now or parsed > now + timedelta(days=365):
            return None
        # Make it >= 1 minute in the future to avoid edge cases
        if parsed < now + timedelta(seconds=30):
            return None
        return {
            "kind": "date",
            "when": parsed.isoformat(),
            "label": parsed.astimezone(BUCHAREST_TZ).strftime("%d.%m.%Y %H:%M"),
        }
    return None


async def _run_scheduled_action(schedule_id: str):
    """APScheduler callback — looks up the schedule, dispatches the action."""
    sched = await db.twin_scheduled_actions.find_one({"id": schedule_id, "status": "active"})
    if not sched:
        logger.warning(f"[twin.schedule] {schedule_id} not found or inactive — skipping")
        return

    action_key = sched.get("action_key")
    user_id = sched.get("user_id")
    user_email = sched.get("user_email")

    logger.info(f"[twin.schedule] firing {schedule_id} action={action_key} user={user_email}")
    try:
        from routes.twin import _execute_action
        fake_user = {"id": user_id, "email": user_email}
        result = await _execute_action(action_key, fake_user)
        await db.twin_scheduled_actions.update_one(
            {"id": schedule_id},
            {
                "$set": {"last_run_at": datetime.now(timezone.utc).isoformat(), "last_run_result": result},
                "$inc": {"run_count": 1},
            },
        )
        # One-shot schedules disable themselves after firing
        if sched.get("kind") == "date":
            await db.twin_scheduled_actions.update_one(
                {"id": schedule_id},
                {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}},
            )
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[twin.schedule] {schedule_id} failed: {e}")
        await db.twin_scheduled_actions.update_one(
            {"id": schedule_id},
            {"$set": {"last_error": str(e)[:200], "last_error_at": datetime.now(timezone.utc).isoformat()}},
        )


def _build_trigger(kind: str, when):
    """Build APScheduler trigger from schedule info."""
    if kind == "date":
        return DateTrigger(run_date=datetime.fromisoformat(when))
    if kind == "cron":
        return CronTrigger(**when, timezone=BUCHAREST_TZ)
    raise ValueError(f"Unknown schedule kind: {kind}")


async def register_schedule(
    scheduler,
    schedule_id: str,
    user_id: str,
    user_email: str,
    action_key: str,
    schedule_info: dict,
    question: str,
) -> dict:
    """Persist + register a new scheduled action."""
    # Cap per user (active only)
    active = await db.twin_scheduled_actions.count_documents({"user_id": user_id, "status": "active"})
    if active >= MAX_SCHEDULES_PER_USER:
        raise ValueError(f"Limit atins: max {MAX_SCHEDULES_PER_USER} programări active per user.")

    doc = {
        "id": schedule_id,
        "user_id": user_id,
        "user_email": user_email,
        "action_key": action_key,
        "kind": schedule_info["kind"],
        "when": schedule_info["when"],
        "label": schedule_info["label"],
        "source_question": question,
        "status": "active",
        "run_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.twin_scheduled_actions.insert_one(doc)

    trigger = _build_trigger(schedule_info["kind"], schedule_info["when"])
    scheduler.add_job(
        _run_scheduled_action,
        trigger,
        args=[schedule_id],
        id=f"twin_sched_{schedule_id}",
        replace_existing=True,
        misfire_grace_time=600,
    )
    logger.info(f"[twin.schedule] registered {schedule_id} kind={schedule_info['kind']} label={schedule_info['label']}")
    return doc


async def hydrate_schedules_on_startup(scheduler) -> int:
    """Re-register all active schedules from DB after backend restart."""
    count = 0
    async for sched in db.twin_scheduled_actions.find({"status": "active"}):
        try:
            trigger = _build_trigger(sched["kind"], sched["when"])
            scheduler.add_job(
                _run_scheduled_action,
                trigger,
                args=[sched["id"]],
                id=f"twin_sched_{sched['id']}",
                replace_existing=True,
                misfire_grace_time=600,
            )
            count += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[twin.schedule] hydrate failed for {sched.get('id')}: {e}")
    if count:
        logger.info(f"[twin.schedule] hydrated {count} active schedules from DB")
    return count


async def cancel_schedule(scheduler, schedule_id: str, user_id: str) -> bool:
    """Cancel an active schedule (mark cancelled + remove from scheduler)."""
    sched = await db.twin_scheduled_actions.find_one({"id": schedule_id, "user_id": user_id})
    if not sched:
        return False
    await db.twin_scheduled_actions.update_one(
        {"id": schedule_id},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}},
    )
    try:
        scheduler.remove_job(f"twin_sched_{schedule_id}")
    except Exception:  # noqa: BLE001
        pass
    return True
