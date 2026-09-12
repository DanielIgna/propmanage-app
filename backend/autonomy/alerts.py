"""Autonomy Tier Downgrade Alerts.

Detects when the autonomy tier drops (e.g. self-driving → autonomous) between
two consecutive snapshots and notifies super-admins via push + email.

Tiers (high → low):
    self-driving > autonomous > assisted > manual

Triggered from ``take_autonomy_snapshot`` in routes/autonomy.py after every
snapshot is persisted. Idempotent — if the previous snapshot has the same tier
or there's no previous snapshot, nothing happens.

De-dupes: skips alerting if an alert for the same downgrade pair was already
sent within the last 12 hours (stored in ``autonomy_alerts`` collection).
"""
import logging
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.autonomy.alerts")

TIER_RANK = {"self-driving": 4, "autonomous": 3, "assisted": 2, "manual": 1}

TIER_LABEL = {
    "self-driving": "Self-Driving",
    "autonomous": "Autonomous",
    "assisted": "Assisted",
    "manual": "Manual",
}


async def _get_super_admins() -> list:
    """Return list of super-admin user docs (role=admin AND admin_scope=general)."""
    out = []
    async for u in db.users.find(
        {"role": "admin", "$or": [{"admin_scope": "general"}, {"admin_scope": None}, {"admin_scope": {"$exists": False}}]},
        {"_id": 1, "email": 1, "name": 1},
    ):
        out.append(u)
    return out


def _build_email_html(prev_tier: str, new_tier: str, prev_score: float, new_score: float, breakdown: dict) -> str:
    delta = round(new_score - prev_score, 1)
    delta_str = f"{'+' if delta > 0 else ''}{delta}"
    rows = "".join(
        f"<tr><td style='padding:4px 12px;color:#475569'>{k.capitalize()}</td>"
        f"<td style='padding:4px 12px;text-align:right;font-weight:600'>{v}</td></tr>"
        for k, v in (breakdown or {}).items()
    )
    return f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:560px;margin:0 auto">
  <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:20px;margin-bottom:16px">
    <div style="font-size:11px;letter-spacing:0.1em;color:#b91c1c;font-weight:700;text-transform:uppercase">⚠ Autonomy Tier Downgrade</div>
    <div style="font-size:22px;font-weight:700;color:#7f1d1d;margin-top:6px">
      {TIER_LABEL.get(prev_tier, prev_tier)} → {TIER_LABEL.get(new_tier, new_tier)}
    </div>
    <div style="color:#7f1d1d;margin-top:4px">
      Scor general: <strong>{prev_score} → {new_score}</strong> ({delta_str}pp)
    </div>
  </div>
  <div style="background:#f8fafc;border-radius:12px;padding:16px">
    <div style="font-weight:600;color:#0f172a;margin-bottom:8px">Sub-scoruri curente</div>
    <table style="width:100%;border-collapse:collapse;font-size:14px;color:#0f172a">{rows}</table>
  </div>
  <div style="margin-top:16px;font-size:13px;color:#64748b">
    Investighează în <a href="https://propmanage.ro/admin/autonomy" style="color:#0ea5e9">Autonomy Engine</a>.
    Recomandările prioritizate sunt disponibile imediat în dashboard.
  </div>
</div>
""".strip()


async def _detect_downgrade(current_snapshot: dict) -> dict:
    """Compare current snapshot vs previous one. Returns either
    {skip: reason} or {prev_tier, new_tier, prev_score, new_score}."""
    new_tier = current_snapshot.get("tier")
    new_score = (current_snapshot.get("scores") or {}).get("general")
    if not new_tier or new_score is None:
        return {"skip": "missing_tier_or_score"}

    # Find the most recent snapshot BEFORE this one (skip the one we just inserted)
    cursor = db.autonomy_snapshots.find(
        {"timestamp": {"$lt": current_snapshot.get("timestamp")}},
        {"tier": 1, "scores": 1, "timestamp": 1},
    ).sort("timestamp", -1).limit(1)
    prev_list = [d async for d in cursor]
    if not prev_list:
        return {"skip": "no_previous_snapshot"}
    prev = prev_list[0]
    prev_tier = prev.get("tier") or "manual"
    prev_score = (prev.get("scores") or {}).get("general") or 0

    if TIER_RANK.get(new_tier, 0) >= TIER_RANK.get(prev_tier, 0):
        return {"skip": "no_downgrade", "prev_tier": prev_tier, "new_tier": new_tier}

    # De-dupe: skip if same downgrade pair was alerted in the last 12h
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
    recent = await db.autonomy_alerts.find_one({
        "prev_tier": prev_tier,
        "new_tier": new_tier,
        "sent_at": {"$gte": cutoff},
    })
    if recent:
        return {"skip": "deduped_recent_alert"}

    return {"prev_tier": prev_tier, "new_tier": new_tier,
            "prev_score": prev_score, "new_score": new_score}


async def _notify_admin(adm: dict, title: str, body: str, email_html: str) -> tuple:
    """Send in-app + push + email to one admin. Returns (pushed, emailed)."""
    from services import send_email, send_web_push
    uid = str(adm.get("_id"))
    email = adm.get("email")
    pushed = emailed = 0
    # 1) In-app notification (direct insert to avoid notify's generic email)
    try:
        await db.notifications.insert_one({
            "user_id": uid,
            "title": title,
            "message": body,
            "type": "autonomy_tier_downgrade",
            "link": "/admin/autonomy",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        pushed = 1
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autonomy.alert] in-app insert failed for {email}: {e}")
    # 2) Web push (best-effort)
    try:
        await send_web_push(uid, title, body, "/admin/autonomy")
    except Exception:  # noqa: BLE001
        pass
    # 3) Rich email
    if email:
        try:
            await send_email(email, title, email_html)
            emailed = 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[autonomy.alert] email failed for {email}: {e}")
    return pushed, emailed


async def _persist_alert(alert_doc: dict) -> None:
    """Store the alert (audit + de-dupe source) and cap collection at 200 docs."""
    try:
        await db.autonomy_alerts.insert_one({**alert_doc})
        cur = db.autonomy_alerts.find({}, {"_id": 1}).sort("sent_at", -1).skip(200)
        old = [d["_id"] async for d in cur]
        if old:
            await db.autonomy_alerts.delete_many({"_id": {"$in": old}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autonomy.alert] persist failed: {e}")


async def check_and_alert_tier_downgrade(current_snapshot: dict) -> dict:
    """Compare current snapshot vs prev and alert on downgrade.

    Args:
        current_snapshot: dict returned by take_autonomy_snapshot() containing
            ``tier`` and ``scores.general`` and ``breakdown_summary``.

    Returns:
        dict: {alerted: bool, reason: str, downgrade: optional dict}
    """
    detection = await _detect_downgrade(current_snapshot)
    if "skip" in detection:
        reason = detection.pop("skip")
        return {"alerted": False, "reason": reason, **detection}

    prev_tier, new_tier = detection["prev_tier"], detection["new_tier"]
    prev_score, new_score = detection["prev_score"], detection["new_score"]

    # Build & dispatch
    breakdown = current_snapshot.get("breakdown_summary") or {}
    super_admins = await _get_super_admins()
    sent_email_count = 0
    sent_push_count = 0

    title = f"⚠ Autonomy tier downgrade: {TIER_LABEL.get(prev_tier, prev_tier)} → {TIER_LABEL.get(new_tier, new_tier)}"
    body = (
        f"Scorul general a scăzut de la {prev_score} la {new_score}. "
        f"Verifică recomandările în Autonomy Engine."
    )
    email_html = _build_email_html(prev_tier, new_tier, prev_score, new_score, breakdown)

    try:
        for adm in super_admins:
            pushed, emailed = await _notify_admin(adm, title, body, email_html)
            sent_push_count += pushed
            sent_email_count += emailed
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[autonomy.alert] dispatch error: {e}")

    alert_doc = {
        "prev_tier": prev_tier,
        "new_tier": new_tier,
        "prev_score": prev_score,
        "new_score": new_score,
        "delta": round(new_score - prev_score, 1),
        "recipients": [a.get("email") for a in super_admins if a.get("email")],
        "push_count": sent_push_count,
        "email_count": sent_email_count,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    await _persist_alert(alert_doc)

    alert_doc.pop("_id", None)
    logger.info(
        f"[autonomy.alert] DOWNGRADE {prev_tier}→{new_tier} "
        f"({prev_score}→{new_score}) sent to {sent_push_count} push / {sent_email_count} email"
    )
    return {"alerted": True, "downgrade": alert_doc}
