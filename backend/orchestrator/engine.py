"""Autonomy Orchestrator — cross-module signal dispatcher (Sprint 1).

Flow: emit_signal(kind, payload) → matching playbook cascade → ledger entry
(+ escalation to super-admins only when automation fails).
Collections: orchestrator_signals, orchestrator_ledger, orchestrator_retry_queue,
orchestrator_config (playbook toggles).
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.orchestrator")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _cap_collection(coll, sort_field: str, keep: int) -> None:
    try:
        cur = coll.find({}, {"_id": 1}).sort(sort_field, -1).skip(keep)
        old = [d["_id"] async for d in cur]
        if old:
            await coll.delete_many({"_id": {"$in": old}})
    except Exception:  # noqa: BLE001
        pass


async def _get_super_admins() -> list:
    out = []
    async for u in db.users.find(
        {"role": "admin", "$or": [{"admin_scope": "general"}, {"admin_scope": None}, {"admin_scope": {"$exists": False}}]},
        {"_id": 1, "email": 1, "name": 1},
    ):
        out.append(u)
    return out


async def notify_admins(title: str, body: str, link: str = "/admin/orchestrator", send_emails: bool = False) -> int:
    """In-app + best-effort push to super-admins. Email only when send_emails=True
    (sent with _from_retry=True to avoid re-enqueue loops)."""
    admins = await _get_super_admins()
    sent = 0
    for adm in admins:
        uid = str(adm.get("_id"))
        try:
            await db.notifications.insert_one({
                "user_id": uid,
                "title": title,
                "message": body,
                "type": "orchestrator",
                "link": link,
                "read": False,
                "created_at": _now(),
            })
            sent += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[orchestrator] in-app notify failed: {e}")
        try:
            from services import send_web_push
            await send_web_push(uid, title, body, link)
        except Exception:  # noqa: BLE001
            pass
        if send_emails and adm.get("email"):
            try:
                from email_service import send_email
                html = (
                    f"<div style='font-family:Inter,sans-serif;max-width:560px;margin:0 auto'>"
                    f"<h2 style='color:#7c3aed'>{title}</h2>"
                    f"<p style='color:#334155;font-size:14px;line-height:1.6'>{body}</p>"
                    f"<p style='font-size:13px'><a href='https://propmanage.ro{link}' style='color:#0ea5e9'>Deschide în Orchestrator</a></p>"
                    f"</div>"
                )
                await send_email(adm["email"], title, html, _from_retry=True)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[orchestrator] escalation email failed: {e}")
    return sent


async def is_playbook_enabled(playbook_id: str) -> bool:
    doc = await db.orchestrator_config.find_one({"_id": playbook_id})
    return True if doc is None else bool(doc.get("enabled", True))


async def set_playbook_enabled(playbook_id: str, enabled: bool, by: str = "") -> None:
    await db.orchestrator_config.update_one(
        {"_id": playbook_id},
        {"$set": {"enabled": bool(enabled), "updated_at": _now(), "updated_by": by}},
        upsert=True,
    )


async def write_ledger(entry: dict) -> dict:
    doc = {
        "id": uuid.uuid4().hex,
        "ts": _now(),
        **entry,
    }
    try:
        await db.orchestrator_ledger.insert_one({**doc})
        await _cap_collection(db.orchestrator_ledger, "ts", 500)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[orchestrator] ledger write failed: {e}")
    doc.pop("_id", None)
    return doc


async def emit_signal(kind: str, payload: dict = None) -> dict:
    """Ingest a signal, run its playbook cascade, record the ledger. Never raises."""
    payload = payload or {}
    try:
        await db.orchestrator_signals.insert_one({
            "id": uuid.uuid4().hex,
            "kind": kind,
            "payload": payload,
            "ts": _now(),
        })
        await _cap_collection(db.orchestrator_signals, "ts", 500)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[orchestrator] signal persist failed: {e}")

    from orchestrator.playbooks import PLAYBOOKS
    pb = PLAYBOOKS.get(kind)
    if not pb:
        return {"handled": False, "reason": "no_playbook"}

    if not await is_playbook_enabled(pb["id"]):
        await write_ledger({
            "signal_kind": kind,
            "playbook_id": pb["id"],
            "playbook_name": pb["name"],
            "steps": [],
            "outcome": "skipped_disabled",
            "minutes_saved": 0,
            "escalated": False,
            "test": bool(payload.get("test")),
        })
        return {"handled": False, "reason": "playbook_disabled"}

    # ── Authority Engine (PM-AI-003): nivel 1-5 + Confidence gate ──────────
    from orchestrator.governance import (
        get_authority, compute_confidence, resolve_execution_mode, record_decision,
    )
    authority = await get_authority(pb["id"])
    confidence = await compute_confidence(pb["id"])
    exec_mode = resolve_execution_mode(authority, confidence)

    if exec_mode in ("observe", "recommend"):
        outcome = "observed" if exec_mode == "observe" else "recommended"
        entry = await write_ledger({
            "signal_kind": kind,
            "playbook_id": pb["id"],
            "playbook_name": pb["name"],
            "steps": [{"action": "governance_gate", "ok": True,
                       "detail": f"Nivel autoritate {authority} / încredere {confidence['score']} → mod '{exec_mode}'. Handler NEEXECUTAT."}],
            "outcome": outcome,
            "minutes_saved": 0,
            "escalated": False,
            "authority_level": authority,
            "execution_mode": exec_mode,
            "confidence": confidence["score"],
            "test": bool(payload.get("test")),
        })
        await record_decision({
            "signal_kind": kind, "playbook_id": pb["id"], "playbook_name": pb["name"],
            "authority_level": authority, "execution_mode": exec_mode,
            "confidence": confidence["score"], "decided": outcome,
            "outcome": outcome, "escalated": False,
            "context": {k: str(v)[:200] for k, v in list(payload.items())[:8]},
            "test": bool(payload.get("test")),
        })
        if exec_mode == "recommend":
            reason = ("autoritate nivel 2 (Consilier)" if authority == 2
                      else f"încredere scăzută ({confidence['score']}) — downgrade automat")
            await notify_admins(
                f"🤖 Recomandare AI: {pb['name']}",
                f"Semnalul '{kind}' a fost primit dar NU executat automat ({reason}). "
                f"Aprobă manual sau ridică nivelul de autoritate în Orchestrator.",
                link="/admin/orchestrator",
            )
        return {"handled": True, "ledger": entry, "execution_mode": exec_mode}

    try:
        result = await pb["handler"](payload)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[orchestrator] playbook {pb['id']} crashed: {e}", exc_info=True)
        result = {
            "steps": [{"action": "playbook_execution", "ok": False, "detail": str(e)[:300]}],
            "outcome": "error",
            "minutes_saved": 0,
            "escalate": True,
            "escalation_title": f"🚨 Orchestrator: playbook '{pb['name']}' a eșuat",
            "escalation_body": f"Eroare: {str(e)[:200]}. Semnal: {kind}.",
        }

    escalated = bool(result.get("escalate"))
    entry = await write_ledger({
        "signal_kind": kind,
        "playbook_id": pb["id"],
        "playbook_name": pb["name"],
        "steps": result.get("steps") or [],
        "outcome": result.get("outcome") or "unknown",
        "minutes_saved": result.get("minutes_saved") or 0,
        "escalated": escalated,
        "authority_level": authority,
        "execution_mode": exec_mode,
        "confidence": confidence["score"],
        "test": bool(payload.get("test")),
    })
    await record_decision({
        "signal_kind": kind, "playbook_id": pb["id"], "playbook_name": pb["name"],
        "authority_level": authority, "execution_mode": exec_mode,
        "confidence": confidence["score"], "decided": "executed",
        "outcome": result.get("outcome") or "unknown", "escalated": escalated,
        "context": {k: str(v)[:200] for k, v in list(payload.items())[:8]},
        "test": bool(payload.get("test")),
    })

    if exec_mode == "execute_notify" and not escalated:
        try:
            await notify_admins(
                f"🤖 Executat (supravegheat): {pb['name']}",
                f"Semnalul '{kind}' → rezultat: {result.get('outcome')}. Nivel autoritate 3 — notificare la fiecare rulare.",
            )
        except Exception:  # noqa: BLE001
            pass

    if escalated:
        try:
            await notify_admins(
                result.get("escalation_title") or f"⚠ Orchestrator escalation: {pb['name']}",
                result.get("escalation_body") or "Toate strategiile automate au eșuat. Intervenție umană necesară.",
                link=result.get("escalation_link") or "/admin/orchestrator",
                send_emails=True,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[orchestrator] escalation notify failed: {e}")

    logger.info(f"[orchestrator] {kind} → {pb['id']} → {entry.get('outcome')} (saved ~{entry.get('minutes_saved')}min)")
    return {"handled": True, "ledger": entry}


# ============================================================================
# LEARNING: clasificare erori permanente + deduplicare escaladări (24h)
# Root cause generalizat: erorile de CONFIGURAȚIE nu se rezolvă prin retry.
# ============================================================================
_PERMANENT_ERROR_PATTERNS = (
    "not verified", "domain is not verified", "api key", "unauthorized",
    "forbidden", "invalid from", "invalid sender", "testing email",
    "verify a domain", "account is not activated", "invalid `to` field",
)


def is_permanent_error(detail: str) -> bool:
    d = (detail or "").lower()
    return any(p in d for p in _PERMANENT_ERROR_PATTERNS)


async def absolve_error_class(playbook_id: str, error_class: str, match_query: dict, reason: str) -> int:
    """LEARNING: după generalizarea unui fix pentru o clasă de erori, intrările istorice
    din acea clasă nu mai penalizează scorul de încredere al playbook-ului.
    Ledger-ul rămâne append-only — doar se marchează absolved, nu se șterge nimic."""
    res = await db.orchestrator_ledger.update_many(
        {"playbook_id": playbook_id, "absolved": {"$ne": True}, **match_query},
        {"$set": {"absolved": True, "absolved_at": _now(), "absolved_class": error_class}},
    )
    if res.modified_count:
        await write_ledger({
            "signal_kind": "learning",
            "playbook_id": playbook_id,
            "playbook_name": "Learning Engine",
            "steps": [{"action": "learning_absolution", "ok": True,
                       "detail": f"Clasa de erori '{error_class}' generalizată și fixată — "
                                 f"{res.modified_count} intrări istorice absolvite din calculul încrederii. Motiv: {reason}"}],
            "outcome": "auto_resolved",
            "minutes_saved": 0,
            "escalated": False,
            "test": False,
        })
        logger.info(f"[learning] absolved {res.modified_count} entries for class '{error_class}' ({playbook_id})")
    return res.modified_count


async def escalate_once(dedup_key: str, title: str, message: str, window_hours: int = 24) -> bool:
    """Escaladează o clasă de probleme O SINGURĂ DATĂ pe fereastră; restul doar se numără.

    Returnează True dacă escaladarea a fost trimisă acum (prima din fereastră).
    """
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=window_hours)).isoformat()
    doc = await db.orchestrator_escalation_dedup.find_one({"key": dedup_key})
    if doc and (doc.get("last_escalated_at") or "") >= window_start:
        await db.orchestrator_escalation_dedup.update_one(
            {"key": dedup_key}, {"$inc": {"suppressed_count": 1}, "$set": {"last_seen_at": _now()}})
        return False
    await db.orchestrator_escalation_dedup.update_one(
        {"key": dedup_key},
        {"$set": {"last_escalated_at": _now(), "last_seen_at": _now(), "title": title},
         "$setOnInsert": {"first_seen_at": _now()}, "$inc": {"escalation_count": 1}},
        upsert=True)
    suppressed = (doc or {}).get("suppressed_count") or 0
    suffix = f" (+{suppressed} apariții similare suprimate în ultimele {window_hours}h)" if suppressed else ""
    await notify_admins(title, message + suffix)
    if suppressed:
        await db.orchestrator_escalation_dedup.update_one({"key": dedup_key}, {"$set": {"suppressed_count": 0}})
    return True


# ============================================================================
# RETRY QUEUE (Webhook Retry Guardian executor) — cron tick every 5 min
# ============================================================================
async def orchestrator_retry_tick() -> dict:
    out = {"processed": 0, "sent": 0, "failed_permanent": 0, "rescheduled": 0, "blocked_config": 0}
    now = _now()
    items = [d async for d in db.orchestrator_retry_queue.find(
        {"status": "pending", "next_retry_at": {"$lte": now}}
    ).limit(20)]

    for item in items:
        out["processed"] += 1
        ok, detail = False, ""
        if item.get("kind") == "email":
            try:
                from email_service import send_email
                p = item.get("payload") or {}
                res = await send_email(p.get("to"), p.get("subject") or "", p.get("html") or "", _from_retry=True)
                ok = bool(res.get("ok"))
                detail = str(res.get("id") or res.get("error") or "")[:200]
            except Exception as e:  # noqa: BLE001
                detail = str(e)[:200]

        attempts = int(item.get("attempts") or 0) + 1
        if not ok and is_permanent_error(detail):
            # Eroare de CONFIG (nu tranzientă): oprește retry-ul, păstrează emailul recuperabil,
            # escaladează AGREGAT o dată/24h — nu per email.
            out["blocked_config"] += 1
            await db.orchestrator_retry_queue.update_one(
                {"_id": item["_id"]},
                {"$set": {"status": "blocked_by_config", "attempts": attempts, "last_detail": detail}},
            )
            escalated_now = await escalate_once(
                "email_blocked_by_config",
                "🚨 Emailuri blocate de configurația Resend",
                f"Livrarea emailurilor eșuează cu eroare PERMANENTĂ de configurare: {detail[:140]}. "
                "Verifică domeniul în Resend, apoi rulează «Reia emailurile blocate» din Orchestrator.",
            )
            await write_ledger({
                "signal_kind": "webhook_fail",
                "playbook_id": "webhook_retry_guardian",
                "playbook_name": "Webhook Retry Guardian",
                "steps": [{"action": "block_permanent_error", "ok": True,
                           "detail": f"Eroare permanentă de config detectată — retry oprit, email păstrat recuperabil: {detail[:120]}"}],
                "outcome": "blocked_config",
                "minutes_saved": 5,
                "escalated": escalated_now,
                "test": bool(item.get("test")),
            })
            continue
        if ok:
            out["sent"] += 1
            await db.orchestrator_retry_queue.update_one(
                {"_id": item["_id"]},
                {"$set": {"status": "done", "attempts": attempts, "done_at": _now(), "last_detail": detail}},
            )
            await write_ledger({
                "signal_kind": "webhook_fail",
                "playbook_id": "webhook_retry_guardian",
                "playbook_name": "Webhook Retry Guardian",
                "steps": [{"action": "retry_email_send", "ok": True,
                           "detail": f"Email '{(item.get('payload') or {}).get('subject', '')[:60]}' trimis cu succes la încercarea {attempts}"}],
                "outcome": "auto_resolved",
                "minutes_saved": 10,
                "escalated": False,
                "test": bool(item.get("test")),
            })
        elif attempts >= int(item.get("max_attempts") or 3):
            out["failed_permanent"] += 1
            await db.orchestrator_retry_queue.update_one(
                {"_id": item["_id"]},
                {"$set": {"status": "failed", "attempts": attempts, "last_detail": detail}},
            )
            escalated_now = await escalate_once(
                f"email_retry_exhausted:{(detail or '')[:40]}",
                "🚨 Orchestrator: email nelivrat după 3 încercări",
                f"Email-ul '{(item.get('payload') or {}).get('subject', '')[:80]}' nu a putut fi livrat. Ultima eroare: {detail[:120]}",
            )
            await write_ledger({
                "signal_kind": "webhook_fail",
                "playbook_id": "webhook_retry_guardian",
                "playbook_name": "Webhook Retry Guardian",
                "steps": [{"action": "retry_email_send", "ok": False,
                           "detail": f"Toate cele {attempts} încercări au eșuat: {detail}"}],
                "outcome": "escalated" if escalated_now else "failed_suppressed",
                "minutes_saved": 0,
                "escalated": escalated_now,
                "test": bool(item.get("test")),
            })
        else:
            out["rescheduled"] += 1
            backoff_min = 5 * (2 ** attempts)
            next_at = (datetime.now(timezone.utc) + timedelta(minutes=backoff_min)).isoformat()
            await db.orchestrator_retry_queue.update_one(
                {"_id": item["_id"]},
                {"$set": {"attempts": attempts, "next_retry_at": next_at, "last_detail": detail}},
            )

    if out["processed"]:
        logger.info(f"[orchestrator] retry tick: {out}")
    return out
