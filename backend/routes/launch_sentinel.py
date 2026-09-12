"""Launch Sentinel — Customer Success Sentinel + Money-Flow Guard (Firul B, protejează lansarea).

Misiune: fiecare agent AI trebuie să aibă impact măsurabil pe lansare, activare sau încasări.
- Funnel „Primii 13": blocuri → apartamente conectate → mentenanță → cereri → plăți.
- CS Sentinel (zilnic 09:30): detectează administratori/blocuri blocate în onboarding și trimite
  remindere concrete (dedupe 72h per bloc+tip), cu escaladare la adminii platformei.
- Money-Flow Guard (zilnic 07:45): Stripe mode, email sender/sandbox, coadă retry — nimeni nu
  pierde bani din cauza unei configurări moarte. Detectează și PRIMA PLATĂ REALĂ (semnal orchestrator).
Reutilizează: buildings, maintenance_tasks, requests, transactions, hh_subscriptions,
orchestrator (emit_signal), ceo_briefing (launch_summary), notifications.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends

from db import db
from deps import require_role
from services import notify
from routes.community_buildings import _building_property_ids, _building_owner_ids

logger = logging.getLogger("propmanage.launch_sentinel")
router = APIRouter(prefix="/api/admin/launch-sentinel", tags=["launch-sentinel"])

NOTIFY_COOLDOWN_H = 72


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago(days: int = 0, hours: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=hours)).isoformat()


# ============================ MONEY-FLOW GUARD ============================

async def money_flow_status() -> dict:
    checks = []
    key = os.environ.get("STRIPE_API_KEY", "")
    if key.startswith("sk_live_"):
        checks.append({"key": "stripe", "label": "Stripe", "status": "ok", "detail": "Cont LIVE — încasările reale funcționează."})
    elif key.startswith("sk_test_") and key != "sk_test_emergent":
        checks.append({"key": "stripe", "label": "Stripe", "status": "critical",
                       "detail": "Stripe în mod TEST — clienții reali NU pot plăti. Claim contul LIVE (acțiune Founder)."})
    else:
        checks.append({"key": "stripe", "label": "Stripe", "status": "critical",
                       "detail": "Stripe în mod DEMO (cheie placeholder) — zero încasări posibile. Claim cont LIVE."})

    sender = os.environ.get("SENDER_EMAIL", "")
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not resend_key:
        checks.append({"key": "email", "label": "Email", "status": "critical",
                       "detail": "Fără provider de email configurat — invitațiile și reminderele NU pleacă."})
    elif "resend.dev" in sender:
        checks.append({"key": "email", "label": "Email", "status": "critical",
                       "detail": f"Sender în SANDBOX ({sender}) — email-urile nu ajung la utilizatori reali. Migrează DNS-ul domeniului."})
    else:
        checks.append({"key": "email", "label": "Email", "status": "ok", "detail": f"Resend activ, sender: {sender}."})

    pending_retries = await db.orchestrator_retry_queue.count_documents({"status": "pending"})
    checks.append({"key": "retry_queue", "label": "Coadă email retry",
                   "status": "warn" if pending_retries > 10 else "ok",
                   "detail": f"{pending_retries} email-uri în așteptare de retry."})

    now = _now()
    active_subs = await db.hh_subscriptions.count_documents({"expires_at": {"$gt": now}})
    lead_rev = 0.0
    async for t in db.transactions.find({"type": "lead_fee", "created_at": {"$gte": _ago(days=30)}}):
        lead_rev += abs(float(t.get("amount") or 0))
    checks.append({"key": "revenue", "label": "Încasări", "status": "ok" if (active_subs or lead_rev) else "warn",
                   "detail": f"{active_subs} abonamente House Health active · {lead_rev:.0f} RON lead fees în 30 zile."})

    critical = [c for c in checks if c["status"] == "critical"]
    return {"checks": checks, "critical_count": len(critical), "ok": len(critical) == 0,
            "active_subscriptions": active_subs, "lead_revenue_30d": round(lead_rev, 2)}


async def money_flow_tick() -> dict:
    """Zilnic 07:45 — persistă starea, alertează adminii DOAR la schimbare de stare sau luni."""
    st = await money_flow_status()
    status_hash = "|".join(f"{c['key']}:{c['status']}" for c in st["checks"])
    prev = await db.cs_money_flow.find_one({"_id": "latest"})
    changed = not prev or prev.get("status_hash") != status_hash
    is_monday = datetime.now(timezone.utc).weekday() == 0
    await db.cs_money_flow.update_one({"_id": "latest"}, {"$set": {
        "status_hash": status_hash, "checks": st["checks"], "critical_count": st["critical_count"],
        "active_subscriptions": st["active_subscriptions"], "lead_revenue_30d": st["lead_revenue_30d"],
        "updated_at": _now()}}, upsert=True)

    if st["critical_count"] and (changed or is_monday):
        details = " · ".join(c["detail"] for c in st["checks"] if c["status"] == "critical")
        for adm in await db.users.find({"role": "admin"}).to_list(10):
            await notify(str(adm["_id"]), f"🚨 Money-Flow Guard: {st['critical_count']} blocaje de încasare",
                         details[:400], type_="money_flow", link="/admin")

    # Prima plată reală → semnal orchestrator (o singură dată; doar cu Stripe LIVE — altfel e demo)
    stripe_ok = any(c["key"] == "stripe" and c["status"] == "ok" for c in st["checks"])
    if stripe_ok and (st["active_subscriptions"] > 0 or st["lead_revenue_30d"] > 0):
        flag = await db.app_settings.find_one({"_id": "launch_first_payment"})
        if not flag:
            await db.app_settings.update_one({"_id": "launch_first_payment"},
                                             {"$set": {"at": _now()}}, upsert=True)
            try:
                from orchestrator.engine import emit_signal
                await emit_signal("first_payment", {"subs": st["active_subscriptions"],
                                                    "lead_revenue_30d": st["lead_revenue_30d"]})
            except Exception as e:  # noqa: BLE001
                logger.warning(f"[launch] first_payment signal failed: {e}")
    return {"critical": st["critical_count"], "changed": changed}


# ============================ FUNNEL „PRIMII 13" ============================

async def compute_launch_funnel() -> dict:
    buildings = [b async for b in db.buildings.find({})]
    per_building, all_owner_ids, connected_total, declared_total = [], set(), 0, 0
    for b in buildings:
        bid = str(b["_id"])
        prop_ids = await _building_property_ids(bid)
        owners = await _building_owner_ids(bid)
        all_owner_ids.update(owners)
        declared = b.get("apartments_total") or 0
        connected_total += len(prop_ids)
        declared_total += declared
        with_task = len(await db.maintenance_tasks.distinct(
            "property_id", {"property_id": {"$in": prop_ids}, "active": True}))
        reqs_30d = await db.requests.count_documents(
            {"property_id": {"$in": prop_ids}, "created_at": {"$gte": _ago(days=30)}})
        per_building.append({
            "id": bid, "name": b["name"], "declared": declared, "connected": len(prop_ids),
            "activation_pct": round(len(prop_ids) / declared * 100) if declared else None,
            "residents": len(owners), "props_with_maintenance": with_task, "requests_30d": reqs_30d,
        })
    now = _now()
    active_subs = await db.hh_subscriptions.count_documents({"expires_at": {"$gt": now}})
    lead_rev = 0.0
    async for t in db.transactions.find({"type": "lead_fee", "created_at": {"$gte": _ago(days=30)}}):
        lead_rev += abs(float(t.get("amount") or 0))
    return {
        "buildings": len(buildings), "connected_apartments": connected_total,
        "declared_apartments": declared_total, "residents": len(all_owner_ids),
        "active_subscriptions": active_subs, "lead_revenue_30d": round(lead_rev, 2),
        "per_building": sorted(per_building, key=lambda x: -(x["connected"])),
    }


# ============================ CS SENTINEL ============================

async def detect_cs_findings() -> list:
    """Cele 6 detecții Customer Success pe blocuri/administratori (doar blocuri mai vechi de praguri)."""
    findings = []
    now_dt = datetime.now(timezone.utc)
    async for b in db.buildings.find({}):
        bid = str(b["_id"])
        name = b["name"]
        admin_id = b.get("administrator_id") or b.get("created_by")
        try:
            age_h = (now_dt - datetime.fromisoformat(b["created_at"])).total_seconds() / 3600
        except Exception:  # noqa: BLE001
            age_h = 999
        prop_ids = await _building_property_ids(bid)
        owners = await _building_owner_ids(bid)

        def add(type_, severity, title, recommendation):
            findings.append({"key": f"{bid}:{type_}", "building_id": bid, "building_name": name,
                             "type": type_, "severity": severity, "target_user_id": admin_id,
                             "title": title, "recommendation": recommendation})

        if age_h > 48 and (not b.get("apartments_total") or len(prop_ids) < 2):
            add("onboarding_incomplete", "high", f"{name}: onboarding neterminat",
                "Completează numărul de apartamente din dashboard și trimite linkul de invitație pe grupul blocului — activarea vecinilor deblochează campaniile comune.")
        if age_h > 168:
            if owners:
                active_member = await db.users.count_documents({
                    "_id": {"$in": [ObjectId(o) for o in owners if ObjectId.is_valid(o)]},
                    "last_seen": {"$gte": _ago(days=7)}})
                if active_member == 0:
                    add("inactive_7d", "high", f"{name}: nimeni nu a intrat de 7 zile",
                        "Publică un anunț util (ex: programul reviziei centralei) — anunțurile notifică toți locatarii și îi readuc în aplicație.")
            if prop_ids:
                reqs = await db.requests.count_documents(
                    {"property_id": {"$in": prop_ids}, "created_at": {"$gte": _ago(days=14)}})
                if reqs == 0:
                    add("no_requests_14d", "medium", f"{name}: nicio cerere în Marketplace de 14 zile",
                        "Pornește o campanie comună din oportunitățile detectate sau adaugă reviziile în calendar — cererile de grup obțin prețuri mai bune.")
                covered = len(await db.maintenance_tasks.distinct(
                    "property_id", {"property_id": {"$in": prop_ids}, "active": True}))
                if covered / len(prop_ids) < 0.5:
                    add("low_maintenance_coverage", "medium", f"{name}: sub 50% apartamente cu plan de mentenanță",
                        "Recomandă vecinilor calendarul de mentenanță (30 sec de configurat) — el alimentează reminderele și campaniile comune.")
            ann = await db.building_announcements.count_documents(
                {"building_id": bid, "created_at": {"$gte": _ago(days=14)}})
            camp = await db.community_campaigns.count_documents(
                {"building_id": bid, "created_at": {"$gte": _ago(days=14)}})
            if ann == 0 and camp == 0:
                add("admin_silent", "medium", f"{name}: fără activitate de administrator de 14 zile",
                    "Un anunț pe săptămână ține comunitatea activă — locatarii activi generează cereri și încasări.")
            if admin_id:
                sub = await db.hh_subscriptions.find_one({"user_id": admin_id, "expires_at": {"$gt": _now()}})
                if not sub:
                    add("subscription_missing", "info", f"{name}: abonament House Health inactiv",
                        "Activează abonamentul House Health pentru monitorizare continuă — primul pas spre venit recurent.")
    return findings


async def cs_sentinel_tick() -> dict:
    """Zilnic 09:30 — upsert findings, notifică ținta (dedupe 72h), rezolvă ce a dispărut."""
    findings = await detect_cs_findings()
    found_keys, notified = set(), 0
    cooldown = _ago(hours=NOTIFY_COOLDOWN_H)
    for f in findings:
        found_keys.add(f["key"])
        prev = await db.cs_findings.find_one({"key": f["key"]})
        await db.cs_findings.update_one({"key": f["key"]}, {
            "$set": {**f, "active": True, "last_seen": _now()},
            "$setOnInsert": {"first_seen": _now()}}, upsert=True)
        last_notified = (prev or {}).get("last_notified_at")
        if f["target_user_id"] and (not last_notified or last_notified < cooldown):
            await notify(f["target_user_id"], f"🛟 {f['title']}", f["recommendation"],
                         type_="cs_sentinel", link="/administrator")
            await db.cs_findings.update_one({"key": f["key"]}, {"$set": {"last_notified_at": _now()}})
            notified += 1
    res = await db.cs_findings.update_many(
        {"active": True, "key": {"$nin": list(found_keys)}},
        {"$set": {"active": False, "resolved_at": _now()}})
    high = [f for f in findings if f["severity"] == "high"]
    if high:
        summary = " · ".join(f["title"] for f in high[:5])
        for adm in await db.users.find({"role": "admin"}).to_list(10):
            await notify(str(adm["_id"]), f"🛟 CS Sentinel: {len(high)} blocuri cer atenție",
                         summary[:400], type_="cs_sentinel", link="/admin")
    logger.info(f"[cs-sentinel] findings={len(findings)} notified={notified} resolved={res.modified_count}")
    return {"findings": len(findings), "notified": notified, "resolved": res.modified_count}


# ============================ CEO BRIEFING HOOK ============================

async def launch_summary() -> dict:
    """Compus în CEO Briefing: 1 linie snapshot + riscuri/oportunități pentru lansare."""
    funnel = await compute_launch_funnel()
    mf = await money_flow_status()
    line = (f"{funnel['buildings']} blocuri · {funnel['connected_apartments']} ap. conectate · "
            f"{funnel['residents']} locatari · {funnel['active_subscriptions']} abonamente · "
            f"{funnel['lead_revenue_30d']:.0f} RON lead fees/30z")
    risks = [{"title": f"Money-Flow: {c['label']}", "severity": "blocker", "why": c["detail"]}
             for c in mf["checks"] if c["status"] == "critical"][:2]
    opportunities = []
    async for f in db.cs_findings.find({"active": True, "severity": {"$in": ["high", "medium"]}}) \
            .sort("last_seen", -1).limit(2):
        opportunities.append({"title": f["title"], "action": f["recommendation"]})
    color = "#ef4444" if mf["critical_count"] else "#d4ff3a"
    return {"line": line, "score": None, "color": color, "funnel": funnel,
            "money_flow": mf, "risks": risks, "opportunities": opportunities}


# ============================ ENDPOINTS (admin) ============================

@router.get("/overview")
async def sentinel_overview(user=Depends(require_role("admin"))):
    funnel = await compute_launch_funnel()
    mf = await money_flow_status()
    findings = [{k: v for k, v in f.items() if k != "_id"} async for f in
                db.cs_findings.find({"active": True}).sort([("severity", 1), ("last_seen", -1)]).limit(50)]
    return {"funnel": funnel, "money_flow": mf, "findings": findings, "generated_at": _now()}


@router.post("/run")
async def sentinel_run(user=Depends(require_role("admin"))):
    cs = await cs_sentinel_tick()
    mf = await money_flow_tick()
    return {"cs": cs, "money_flow": mf}
