"""Resend Self-Diagnostics (Board Decision — Option B, pre-Integration Control Center).

Verifică automat: cheie API, config SDK, propagare DNS (MX/SPF/DKIM/DMARC), trimitere reală.
Read-only pe configurație — raportează root cause exact + checklist (Directiva 017).
Va fi absorbit ca "Run Diagnostics" în Integration Control Center.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role
from sub_admin_deps import is_super_admin

logger = logging.getLogger("propmanage.resend_diag")
router = APIRouter(prefix="/api/admin/integrations/resend", tags=["integrations"])

SEND_DOMAIN = "propmanage.ro"
EXPECTED = [
    {"id": "mx_send", "type": "MX", "host": "send", "name": f"send.{SEND_DOMAIN}",
     "expect_contains": "amazonses.com", "value_hint": "feedback-smtp.<regiune>.amazonses.com", "priority": 10},
    {"id": "spf_send", "type": "TXT", "host": "send", "name": f"send.{SEND_DOMAIN}",
     "expect_contains": "include:amazonses.com", "value_hint": "v=spf1 include:amazonses.com ~all", "priority": None},
    {"id": "dkim", "type": "TXT", "host": "resend._domainkey", "name": f"resend._domainkey.{SEND_DOMAIN}",
     "expect_contains": "p=", "value_hint": "p=<cheie DKIM din dashboard Resend>", "priority": None},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dns_probe() -> list:
    import dns.resolver
    res = dns.resolver.Resolver()
    res.timeout, res.lifetime = 5, 8
    checks = []
    for rec in EXPECTED:
        found, ok = [], False
        try:
            for r in res.resolve(rec["name"], rec["type"]):
                txt = str(r).strip('"')
                found.append(txt[:120])
                if rec["expect_contains"] in txt:
                    ok = True
        except Exception:  # noqa: BLE001 — NXDOMAIN/timeout = lipsă
            pass
        checks.append({**{k: rec[k] for k in ("id", "type", "host", "name", "value_hint", "priority")},
                       "found": found, "ok": ok})
    # DMARC — informativ (există deja pe root)
    try:
        dmarc = [str(r).strip('"')[:120] for r in res.resolve(f"_dmarc.{SEND_DOMAIN}", "TXT")]
    except Exception:  # noqa: BLE001
        dmarc = []
    checks.append({"id": "dmarc", "type": "TXT", "host": "_dmarc", "name": f"_dmarc.{SEND_DOMAIN}",
                   "value_hint": "v=DMARC1; p=none;", "priority": None,
                   "found": dmarc, "ok": bool(dmarc), "informational": True})
    return checks


async def run_diagnostics(send_test_to: str | None = None) -> dict:
    from email_service import PROVIDER, SENDER_EMAIL
    key = os.environ.get("RESEND_API_KEY") or ""
    checks = await asyncio.to_thread(_dns_probe)
    required = [c for c in checks if not c.get("informational")]
    dns_ok = all(c["ok"] for c in required)
    missing = [c for c in required if not c["ok"]]

    test_send = None
    if send_test_to:
        try:
            import resend
            resend.api_key = key
            r = await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL, "to": [send_test_to],
                "subject": "[Diagnostics] Test Resend — PropManage",
                "html": "<p>Trimiterea de emailuri tranzacționale de pe propmanage.ro funcționează. ✅</p>",
            })
            test_send = {"ok": True, "id": (r or {}).get("id")}
        except Exception as e:  # noqa: BLE001
            test_send = {"ok": False, "error": str(e)}

    if not key:
        status, root_cause, action = "action_required", "RESEND_API_KEY lipsește din backend/.env", \
            "Adaugă cheia API Resend în backend/.env și repornește backend-ul."
    elif not dns_ok:
        status = "action_required"
        root_cause = f"Domeniul {SEND_DOMAIN} nu e verificat — lipsesc {len(missing)} înregistrări DNS: " \
                     + ", ".join(f"{c['type']} {c['name']}" for c in missing)
        action = "Adaugă înregistrările lipsă la registrar (Rackhost), apoi apasă Verify în resend.com/domains."
    elif test_send and not test_send["ok"]:
        status = "action_required"
        root_cause = f"DNS OK dar trimiterea eșuează: {test_send['error']}"
        action = ("Apasă Verify în resend.com/domains. Dacă eșuează în continuare, cheia API e scoped pe alt "
                  "domeniu — creează una nouă (Full Access sau scoped propmanage.ro) și actualizeaz-o în .env.")
    elif test_send and test_send["ok"]:
        status, root_cause, action = "operational", None, None
    else:
        status, root_cause, action = "warning", "DNS OK — trimiterea reală nu a fost încă testată", \
            "Rulează diagnosticul cu send_test=true pentru confirmare finală."

    report = {
        "integration": "resend", "checked_at": _now(),
        "api_key_present": bool(key), "api_key_prefix": key[:6] if key else None,
        "provider_active": PROVIDER, "sender": SENDER_EMAIL,
        "dns_ok": dns_ok, "dns_checks": checks, "missing_records": missing,
        "test_send": test_send, "status": status, "root_cause": root_cause,
        "recommended_action": action,
    }
    await db.integration_health.update_one(
        {"_id": "resend"}, {"$set": {**report, "_id": "resend"}}, upsert=True)
    return report


@router.get("/diagnostics")
async def resend_diagnostics(send_test: bool = False, admin=Depends(require_role("admin"))):
    if not is_super_admin(admin):
        raise HTTPException(403, "Doar super-admin")
    to = (admin.get("email") if send_test else None)
    return await run_diagnostics(send_test_to=to)
