"""Specialist onboarding email drip — sends 3 follow-up emails over 7 days.

Day 1: Complete your profile (CI, insurance, photo, zones).
Day 3: First-lead playbook (how to win bids, response time matters).
Day 7: Trust Score growth & long-term tips.

Architecture:
- On specialist registration, schedule 3 rows in db.onboarding_emails with `due_at` UTC.
- A scheduler tick runs every 15 minutes and dispatches all due-and-unsent rows.
- Idempotent: each row has a `sent` flag; failures are retried up to 3 times.
- Unsubscribe-friendly: a single user "onboarding_unsubscribed" flag halts the sequence.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from db import db
from email_service import _layout, send_email, APP_URL

logger = logging.getLogger("propmanage.onboarding")


# ============================================================================
# Templates
# ============================================================================

def tpl_specialist_day1(name: str) -> dict:
    body = f"""
      <p>Bună {name},</p>
      <p>E ziua 1 pe PropManage 🚀. Specialiștii care își <strong style="color:#d4ff3a;">completează profilul în primele 24h</strong> primesc de <strong>3× mai multe leaduri</strong> decât cei cu profil incomplet.</p>
      <p>Iată ce mai ai de bifat:</p>
      <ul style="color:#c8c8cc; padding-left: 18px; margin: 16px 0;">
        <li style="margin-bottom:8px;"><strong>📄 Documente de verificare</strong> — CI, asigurare RCA, certificare profesională (dacă există).</li>
        <li style="margin-bottom:8px;"><strong>📍 Zone de acoperire</strong> — alege orașele/cartierele unde lucrezi. Cu cât mai exact, cu atât mai relevante leadurile.</li>
        <li style="margin-bottom:8px;"><strong>🖼️ Portofoliu foto</strong> — 3-5 poze cu lucrări recente (chiar și pe telefon) cresc trustul cu 60%.</li>
        <li style="margin-bottom:8px;"><strong>💼 Specialități</strong> — bifează toate categoriile în care lucrezi (electric, sanitar, dulgherie…).</li>
      </ul>
      <p style="background:#1a1a1f; border-left:3px solid #d4ff3a; padding:12px 16px; border-radius:10px; color:#c8c8cc;">
        💡 <strong>Pont:</strong> Specialiștii verified apar primii în căutările clienților și au acces la cereri premium.
      </p>
    """
    return {
        "subject": "Ziua 1: completează-ți profilul și primește 3× mai multe leaduri",
        "html": _layout("Profil complet → mai multe leaduri", f"Hi {name}, încă 4 pași până la primul tău lead.", body, f"{APP_URL}/specialist", "Completează profilul")
    }


def tpl_specialist_day3(name: str) -> dict:
    body = f"""
      <p>Bună {name},</p>
      <p>Au trecut 3 zile — sperăm că ai primit deja primele cereri 📩.</p>
      <p><strong>Cum câștigi mai multe leaduri:</strong></p>
      <ul style="color:#c8c8cc; padding-left: 18px; margin: 16px 0;">
        <li style="margin-bottom:8px;"><strong>⚡ Răspunde în mai puțin de 15 minute.</strong> Specialiștii care răspund rapid primesc <strong>5× mai multe contracte</strong>.</li>
        <li style="margin-bottom:8px;"><strong>💬 Pune întrebări specifice.</strong> Clienții vor să simtă că înțelegi problema. „Aveți o fotografie a tabloului?" e mai bun decât „Trimit ofertă".</li>
        <li style="margin-bottom:8px;"><strong>📐 Oferte clare cu trei elemente</strong>: ce intră în preț, durată estimată, garanție.</li>
        <li style="margin-bottom:8px;"><strong>🛡️ Folosește escrow-ul.</strong> Niciodată nu accepta plăți „pe lângă" — pierzi protecția și contul poate fi suspendat.</li>
      </ul>
      <p style="background:#1a1a1f; border-left:3px solid #d4ff3a; padding:12px 16px; border-radius:10px; color:#c8c8cc;">
        📊 <strong>Știai?</strong> Comisionul platformei este de doar 5%. Restul de 95% intră în portofelul tău, eliberat după ce clientul confirmă finalizarea.
      </p>
      <p>Ai întrebări? Răspunde la acest email și un coleg te ajută în 24h.</p>
    """
    return {
        "subject": "Ziua 3: cum câștigi primul tău lead pe PropManage",
        "html": _layout("Playbook primul lead", f"Hi {name}, 4 reguli pentru a câștiga mai des.", body, f"{APP_URL}/specialist", "Vezi leadurile disponibile")
    }


def tpl_specialist_day7(name: str) -> dict:
    body = f"""
      <p>Bună {name},</p>
      <p>Săptămâna 1 e gata 🎉. Acum e momentul să te concentrezi pe <strong style="color:#d4ff3a;">Trust Score</strong> — scorul care decide dacă ești prima sau a zecea opțiune în marketplace.</p>
      <p><strong>Cum crește Trust Score:</strong></p>
      <ul style="color:#c8c8cc; padding-left: 18px; margin: 16px 0;">
        <li style="margin-bottom:8px;"><strong>⭐ Rating ≥ 4.7</strong> din review-urile clienților.</li>
        <li style="margin-bottom:8px;"><strong>📅 Livrare la timp</strong> — termenul stabilit în ofertă vs. data efectivă de finalizare.</li>
        <li style="margin-bottom:8px;"><strong>🔥 Rata de acceptare leaduri</strong> &gt; 70% (acceptă/refuză rapid, nu lăsa cereri să expire).</li>
        <li style="margin-bottom:8px;"><strong>🚫 Zero dispute</strong> deschise împotriva ta în ultimele 90 zile.</li>
        <li style="margin-bottom:8px;"><strong>🆕 Recomandări</strong> — adu colegi specialiști și primești bonus de 100 RON per recomandare verificată.</li>
      </ul>
      <p style="background:#34d39915; border-left:3px solid #34d399; padding:12px 16px; border-radius:10px; color:#c8c8cc;">
        🥇 La <strong>Trust Score &gt; 85</strong>, contul tău primește automat tier <strong>ELITE</strong>: mai multe leaduri, prioritate pe cereri premium și badge vizibil pentru clienți.
      </p>
      <p>Mulțumim că ești parte din comunitatea PropManage. Pentru orice întrebare, suntem aici: <a href="mailto:contact@propmanage.ro" style="color:#d4ff3a;">contact@propmanage.ro</a>.</p>
    """
    return {
        "subject": "Ziua 7: cum îți crești Trust Score și ajungi la tier ELITE",
        "html": _layout("Trust Score & tier ELITE", f"Hi {name}, 5 metrici care contează.", body, f"{APP_URL}/specialist", "Vezi Trust Score-ul tău")
    }


SEQUENCE = [
    {"day": 1, "key": "specialist_day1", "tpl": tpl_specialist_day1},
    {"day": 3, "key": "specialist_day3", "tpl": tpl_specialist_day3},
    {"day": 7, "key": "specialist_day7", "tpl": tpl_specialist_day7},
]


# ============================================================================
# Scheduling
# ============================================================================

async def enqueue_specialist_onboarding(user_id: str, email: str, name: str, *, now: Optional[datetime] = None) -> int:
    """Insert 3 onboarding email rows for a newly-registered specialist.

    Idempotent: if rows already exist for this user, returns 0 without re-inserting.
    Returns the number of rows inserted.
    """
    if not email or not name:
        return 0
    now = now or datetime.now(timezone.utc)
    # Idempotency: don't re-enqueue if already scheduled
    existing = await db.onboarding_emails.find_one({"user_id": user_id})
    if existing:
        return 0
    rows = []
    for step in SEQUENCE:
        rows.append({
            "user_id": user_id,
            "email": email,
            "name": name,
            "step_key": step["key"],
            "day_offset": step["day"],
            "due_at": (now + timedelta(days=step["day"])).isoformat(),
            "sent": False,
            "attempts": 0,
            "last_error": None,
            "sent_at": None,
            "created_at": now.isoformat(),
        })
    await db.onboarding_emails.insert_many(rows)
    logger.info(f"[Onboarding] Enqueued {len(rows)} drip emails for specialist {email}")
    return len(rows)


async def cancel_user_onboarding(user_id: str) -> int:
    """Cancel all pending onboarding emails for a user (e.g. on unsubscribe or account deletion)."""
    res = await db.onboarding_emails.update_many(
        {"user_id": user_id, "sent": False},
        {"$set": {"sent": True, "cancelled": True, "sent_at": datetime.now(timezone.utc).isoformat()}},
    )
    return res.modified_count


# ============================================================================
# Dispatcher (called by APScheduler)
# ============================================================================

MAX_ATTEMPTS = 3


def _build_template(step_key: str, name: str) -> Optional[dict]:
    for step in SEQUENCE:
        if step["key"] == step_key:
            return step["tpl"](name)
    return None


async def dispatch_due_onboarding_emails() -> dict:
    """Send all due onboarding emails. Called every 15 min by the scheduler."""
    now_iso = datetime.now(timezone.utc).isoformat()
    cursor = db.onboarding_emails.find({
        "sent": False,
        "due_at": {"$lte": now_iso},
        "attempts": {"$lt": MAX_ATTEMPTS},
    })
    sent = 0
    failed = 0
    skipped = 0
    async for row in cursor:
        # Skip if the user has been deleted, disabled, or has unsubscribed
        try:
            from bson import ObjectId
            user_doc = await db.users.find_one({"_id": ObjectId(row["user_id"])})
        except Exception:
            user_doc = None
        if not user_doc or user_doc.get("deleted") or user_doc.get("onboarding_unsubscribed"):
            await db.onboarding_emails.update_one(
                {"_id": row["_id"]},
                {"$set": {"sent": True, "skipped": True, "sent_at": now_iso}},
            )
            skipped += 1
            continue
        tpl = _build_template(row["step_key"], row["name"])
        if not tpl:
            failed += 1
            continue
        try:
            await send_email(row["email"], tpl["subject"], tpl["html"])
            await db.onboarding_emails.update_one(
                {"_id": row["_id"]},
                {"$set": {"sent": True, "sent_at": datetime.now(timezone.utc).isoformat()},
                 "$inc": {"attempts": 1}},
            )
            sent += 1
        except Exception as e:  # noqa: BLE001
            await db.onboarding_emails.update_one(
                {"_id": row["_id"]},
                {"$set": {"last_error": str(e)[:500]},
                 "$inc": {"attempts": 1}},
            )
            logger.warning(f"[Onboarding] send failed for {row['email']} step={row['step_key']}: {e}")
            failed += 1
    summary = {"sent": sent, "failed": failed, "skipped": skipped, "at": now_iso}
    if sent or failed:
        logger.info(f"[Onboarding] Dispatch tick: {summary}")
    return summary


async def run_onboarding_dispatch_job():
    """Wrapper for APScheduler — never raises so the scheduler keeps running."""
    try:
        await dispatch_due_onboarding_emails()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[Onboarding] dispatcher crashed: {e}")
