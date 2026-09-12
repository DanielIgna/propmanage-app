"""PropManage — Future Ideas Weekly Digest

Every Monday 09:00 Europe/Bucharest, sends a digest email summarizing:
  - "Stale" proposals: in pending_validation / in_discussion for > 30 days (decision overdue)
  - Recent activity: all decisions made in the last 7 days across all proposals

Helps the founder NOT forget strategic proposals sitting in evaluation limbo.

Config (db.future_ideas_digest_config, singleton _id="config"):
  - enabled: bool
  - recipients: ["email@..."]
  - stale_threshold_days: int (default 30)
  - last_sent_at: ISO

History: db.future_ideas_digest_history (capped 50)
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel, Field

from db import db
from deps import require_role
from email_service import send_email

logger = logging.getLogger("propmanage.future_ideas_digest")
router = APIRouter(prefix="/api/admin/future-ideas-digest", tags=["future-ideas-digest"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Static catalog mirror — matches /app/frontend/src/data/futureIdeas.js (titles only)
# Kept in sync manually; only metadata needed for email rendering.
IDEAS_META = {
    "experience_spaces_v2": {
        "code": "EXP-V2",
        "title": "Experience Spaces — Business Operating System",
    },
    "design_system_atlas": {
        "code": "DS-ATLAS",
        "title": "Design System Unification — PropManage Atlas",
    },
    "marketplace_economics_v2": {
        "code": "MKT-V2",
        "title": "Marketplace Economics V2 — Fee Dinamic + Lead Gating",
    },
}

STATUS_LABELS = {
    "pending_validation": "În evaluare",
    "in_discussion":      "În discuție",
    "approved":           "Aprobat",
    "rejected":           "Respins",
    "on_hold":            "Pe pauză",
}

DEFAULT_CONFIG = {
    "enabled": False,
    "recipients": [],
    "stale_threshold_days": 30,
}


async def _load_config() -> dict:
    doc = await db.future_ideas_digest_config.find_one({"_id": "config"})
    if not doc:
        return {**DEFAULT_CONFIG}
    return {
        "enabled": bool(doc.get("enabled", False)),
        "recipients": list(doc.get("recipients", [])),
        "stale_threshold_days": int(doc.get("stale_threshold_days", 30)),
        "last_sent_at": doc.get("last_sent_at"),
    }


async def _gather_digest_data(stale_days: int = 30) -> dict:
    """Compute stale proposals + recent activity across all ideas."""
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=stale_days)
    activity_cutoff = now - timedelta(days=7)

    stale_items = []
    recent_decisions = []

    async for doc in db.future_ideas_status.find({}):
        idea_id = doc["idea_id"]
        meta = IDEAS_META.get(idea_id, {"code": idea_id, "title": idea_id})
        status = doc.get("status", "pending_validation")

        # Stale check: in evaluation/discussion states for > threshold
        if status in ("pending_validation", "in_discussion"):
            log = doc.get("decision_log", [])
            # Last decision date OR initial created_at
            last_change_iso = (log[-1]["at"] if log else doc.get("created_at") or doc.get("updated_at"))
            if last_change_iso:
                try:
                    last_change = datetime.fromisoformat(last_change_iso.replace("Z", "+00:00"))
                    if last_change < stale_cutoff:
                        stale_items.append({
                            "code": meta["code"],
                            "title": meta["title"],
                            "status": status,
                            "status_label": STATUS_LABELS.get(status, status),
                            "days_stale": (now - last_change).days,
                            "last_change_at": last_change_iso,
                        })
                except Exception:
                    pass

        # Recent decisions: all log entries from last 7 days
        for entry in doc.get("decision_log", []):
            try:
                entry_dt = datetime.fromisoformat(entry["at"].replace("Z", "+00:00"))
                if entry_dt >= activity_cutoff:
                    recent_decisions.append({
                        "code": meta["code"],
                        "title": meta["title"],
                        "at": entry["at"],
                        "by": entry.get("by", ""),
                        "from_status": entry.get("from_status", ""),
                        "to_status": entry.get("to_status", ""),
                        "from_label": STATUS_LABELS.get(entry.get("from_status", ""), entry.get("from_status", "")),
                        "to_label": STATUS_LABELS.get(entry.get("to_status", ""), entry.get("to_status", "")),
                        "reason": entry.get("reason", ""),
                    })
            except Exception:
                pass

    # Also add ideas without ANY status doc (never touched) as stale
    seen_ids = {doc["idea_id"] async for doc in db.future_ideas_status.find({}, {"idea_id": 1})}
    for idea_id, meta in IDEAS_META.items():
        if idea_id not in seen_ids:
            stale_items.append({
                "code": meta["code"],
                "title": meta["title"],
                "status": "pending_validation",
                "status_label": STATUS_LABELS["pending_validation"],
                "days_stale": stale_days,  # at least the threshold
                "last_change_at": None,
            })

    stale_items.sort(key=lambda x: -x["days_stale"])
    recent_decisions.sort(key=lambda x: x["at"], reverse=True)

    return {
        "stale_items": stale_items,
        "recent_decisions": recent_decisions[:20],
        "stale_days_threshold": stale_days,
        "generated_at": now.isoformat(),
    }


def _build_html(data: dict) -> str:
    stale = data["stale_items"]
    recent = data["recent_decisions"]
    threshold = data["stale_days_threshold"]

    stale_rows = ""
    if not stale:
        stale_rows = '<div style="padding:14px;color:#16a34a;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;font-size:13px">✅ Nicio propunere uitată — toate au fost atinse recent. Bravo!</div>'
    else:
        rows = []
        for s in stale:
            rows.append(f"""
            <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:10px;padding:12px;margin-bottom:8px">
              <div style="font-size:10px;letter-spacing:.08em;color:#92400e;text-transform:uppercase">{s['code']} · {s['status_label']}</div>
              <div style="font-size:14px;font-weight:600;color:#451a03;margin-top:2px">{s['title']}</div>
              <div style="font-size:12px;color:#78350f;margin-top:4px">⏰ Stă <strong>{s['days_stale']} zile</strong> fără decizie nouă</div>
            </div>""")
        stale_rows = "".join(rows)

    recent_rows = ""
    if not recent:
        recent_rows = '<div style="padding:14px;color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;font-size:13px;font-style:italic">Nicio decizie luată în ultimele 7 zile.</div>'
    else:
        rows = []
        for r in recent:
            reason_short = (r["reason"] or "")[:200] + ("..." if len(r.get("reason", "")) > 200 else "")
            dt = datetime.fromisoformat(r["at"].replace("Z", "+00:00")).strftime("%d %b · %H:%M")
            rows.append(f"""
            <div style="border-left:3px solid #8b5cf6;padding:10px 12px;margin-bottom:8px;background:#faf5ff">
              <div style="font-size:10px;letter-spacing:.08em;color:#6b21a8;text-transform:uppercase">{r['code']} · {dt}</div>
              <div style="font-size:13px;font-weight:600;color:#1f2937;margin-top:2px">{r['title']}</div>
              <div style="font-size:11px;color:#6b7280;margin-top:4px">{r['from_label']} → <strong style="color:#7c3aed">{r['to_label']}</strong> · {r['by']}</div>
              <div style="font-size:12px;color:#374151;margin-top:6px;font-style:italic">"{reason_short}"</div>
            </div>""")
        recent_rows = "".join(rows)

    today_str = datetime.now(timezone.utc).strftime("%d %b %Y")

    return f"""
<html><body style="margin:0;background:#f6f7f9;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1f2937">
<div style="max-width:640px;margin:0 auto;padding:24px">
  <div style="background:#fff;border-radius:16px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)">

    <div style="border-bottom:1px solid #e5e7eb;padding-bottom:14px;margin-bottom:18px">
      <div style="font-size:11px;letter-spacing:.1em;color:#7c3aed;text-transform:uppercase">PropManage · Idei Viitoare</div>
      <div style="font-size:22px;font-weight:700;margin-top:4px">Digest săptămânal · {today_str}</div>
      <div style="font-size:13px;color:#6b7280;margin-top:4px">Propuneri uitate &amp; activitate recentă · 7 zile</div>
    </div>

    <div style="margin-bottom:24px">
      <div style="font-size:14px;font-weight:600;color:#1f2937;margin-bottom:10px">
        ⏰ Propuneri fără decizie de &gt; {threshold} zile ({len(stale)})
      </div>
      {stale_rows}
    </div>

    <div style="margin-bottom:24px">
      <div style="font-size:14px;font-weight:600;color:#1f2937;margin-bottom:10px">
        📋 Activitate recentă (ultimele 7 zile) — {len(recent)} decizii
      </div>
      {recent_rows}
    </div>

    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:14px;text-align:center;margin-bottom:14px">
      <div style="font-size:13px;color:#0c4a6e;margin-bottom:8px">Deschide catalogul pentru a marca deciziile pending:</div>
      <a href="https://propmanage.ro/admin/future-ideas" style="display:inline-block;background:#8b5cf6;color:#fff;text-decoration:none;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600">Vezi Idei Viitoare →</a>
    </div>

    <div style="padding-top:14px;border-top:1px solid #e5e7eb;font-size:11px;color:#9ca3af;text-align:center">
      Trimis automat lunea 09:00 (Europe/Bucharest) · Dezactivează din Admin → Settings
    </div>
  </div>
</div>
</body></html>""".strip()


async def send_digest(force: bool = False, override_recipients: Optional[list] = None) -> dict:
    """Generate + send the digest. Called by scheduler or manual trigger."""
    cfg = await _load_config()
    if not force and not cfg["enabled"]:
        return {"skipped": "disabled"}
    recipients = override_recipients or cfg["recipients"]
    if not recipients:
        return {"skipped": "no_recipients"}

    data = await _gather_digest_data(cfg["stale_threshold_days"])
    html = _build_html(data)
    n_stale = len(data["stale_items"])
    n_recent = len(data["recent_decisions"])
    subject = f"PropManage · Digest Idei Viitoare · {n_stale} uitate, {n_recent} decizii recente"

    try:
        await send_email(recipients, subject, html)
        sent_ok = True
        error = None
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[future_ideas_digest] email send failed: {e}")
        sent_ok = False
        error = str(e)[:200]

    now_iso = datetime.now(timezone.utc).isoformat()
    if sent_ok:
        await db.future_ideas_digest_config.update_one(
            {"_id": "config"}, {"$set": {"last_sent_at": now_iso}}, upsert=True,
        )

    history_doc = {
        "sent_at": now_iso,
        "recipients": recipients,
        "subject": subject,
        "ok": sent_ok,
        "error": error,
        "n_stale": n_stale,
        "n_recent": n_recent,
        "forced": bool(force),
    }
    try:
        await db.future_ideas_digest_history.insert_one(history_doc)
        # cap at 50
        cur = db.future_ideas_digest_history.find({}, {"_id": 1}).sort("sent_at", -1).skip(50)
        old = [d["_id"] async for d in cur]
        if old:
            await db.future_ideas_digest_history.delete_many({"_id": {"$in": old}})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[future_ideas_digest] history persist failed: {e}")

    history_doc.pop("_id", None)
    return history_doc


async def run_future_ideas_digest_job() -> dict:
    """APScheduler entrypoint — Mondays 09:00 Europe/Bucharest."""
    logger.info("[future_ideas_digest] scheduled run started")
    result = await send_digest(force=False)
    logger.info(f"[future_ideas_digest] scheduled run done: {result.get('subject') or result.get('skipped')}")
    return result


# ----------------------------------------------------------------------
# API endpoints
# ----------------------------------------------------------------------

class ConfigPatch(BaseModel):
    enabled: Optional[bool] = None
    recipients: Optional[list] = None
    stale_threshold_days: Optional[int] = Field(default=None, ge=7, le=365)


class SendNowPayload(BaseModel):
    recipients: Optional[list] = None


@router.get("/config")
async def get_config(user=Depends(require_role("admin"))):
    return await _load_config()


@router.put("/config")
async def update_config(patch: ConfigPatch, user=Depends(require_role("admin"))):
    update = {}
    if patch.enabled is not None:
        update["enabled"] = patch.enabled
    if patch.recipients is not None:
        valid = [e.strip() for e in patch.recipients if isinstance(e, str) and EMAIL_RE.match(e.strip())]
        update["recipients"] = valid
    if patch.stale_threshold_days is not None:
        update["stale_threshold_days"] = int(patch.stale_threshold_days)
    if update:
        await db.future_ideas_digest_config.update_one(
            {"_id": "config"}, {"$set": update}, upsert=True,
        )
    return await _load_config()


@router.get("/preview")
async def preview_digest(user=Depends(require_role("admin"))):
    """Returns digest data WITHOUT sending email — for UI preview."""
    cfg = await _load_config()
    data = await _gather_digest_data(cfg["stale_threshold_days"])
    html = _build_html(data)
    return {"data": data, "html": html}


@router.post("/send-now")
async def send_now(payload: SendNowPayload = Body(default=None), user=Depends(require_role("admin"))):
    """Force send the digest immediately (admin-triggered)."""
    overrides = payload.recipients if payload else None
    result = await send_digest(force=True, override_recipients=overrides)
    return result


@router.get("/history")
async def get_history(limit: int = 20, user=Depends(require_role("admin"))):
    cursor = db.future_ideas_digest_history.find({}).sort("sent_at", -1).limit(limit)
    items = []
    async for d in cursor:
        d.pop("_id", None)
        items.append(d)
    return {"items": items}
