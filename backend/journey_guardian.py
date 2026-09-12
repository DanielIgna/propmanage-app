"""Customer Journey Guardian — protejează călătoria clientului (WHY→WHAT→HOW→NEXT).

Auditează continuu configurația publică (meniu, flux canonic, servicii, conținut, CTA-uri),
detectează fundături/inconsistențe și creează AUTOMAT task-uri de implementare pentru CTO AI
în db.journey_guardian_tasks (deschidere/închidere automată, fără duplicate).
"""
import logging
import uuid
from datetime import datetime, timezone

from db import db

logger = logging.getLogger("propmanage.journey_guardian")

# Rutele publice cunoscute (sincronizate cu App.js) — destinații valide pentru meniu/flux
PUBLIC_ROUTES = {
    "/", "/imobile-verificate", "/imobile-verificate/sell", "/design-interior",
    "/design-exterior", "/arhitectura", "/marketplace", "/preturi", "/de-ce-noi",
    "/community", "/ghiduri", "/house-health/upgrade", "/house-health", "/login",
    "/register", "/auth", "/dashboard", "/components-v2",
}
PUBLIC_PREFIXES = ("/servicii/", "/preturi/", "/marketplace/", "/ghiduri/", "/imobile-verificate/", "/community/")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _route_ok(href: str) -> bool:
    if not href:
        return True  # grupuri fără destinație
    if href.startswith(("mailto:", "tel:", "http://", "https://", "#")):
        return True
    path = href.split("?")[0].split("#")[0] or "/"
    return path in PUBLIC_ROUTES or path.rstrip("/") in PUBLIC_ROUTES or any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _issue(key, severity, title, detail, affected, expected, impact) -> dict:
    return {"key": key, "severity": severity, "title": title, "detail": detail,
            "affected": affected, "expected": expected, "business_impact": impact}


async def _check_menu(issues: list):
    doc = await db.site_menu.find_one({"key": "main"}) or {}
    services_group = None
    for group in doc.get("items") or []:
        for it in [group] + (group.get("children") or []):
            if it.get("active") and it.get("visible_site", True) and not _route_ok(it.get("href", "")):
                issues.append(_issue(
                    f"menu_dead_link:{it['id']}", "high",
                    f"Link mort în meniul public: {it.get('label')}",
                    f"Itemul activ '{it['id']}' duce la '{it.get('href')}' — rută publică necunoscută.",
                    {"routes": ["/app/backend/routes/site_menu.py"], "components": ["SiteNav.jsx"]},
                    "Orice item activ din meniu duce la o rută publică funcțională.",
                    "Vizitatorii lovesc o pagină inexistentă → pierdere directă de încredere/conversie."))
        if group.get("id") == "servicii":
            services_group = group
    if services_group:
        active = [c for c in services_group.get("children") or []
                  if c.get("active") and c.get("visible_site", True)]
        if not active:
            issues.append(_issue(
                "menu_no_active_services", "critical", "Niciun serviciu activ în meniu",
                "Grupul «Servicii» nu are niciun serviciu activ+vizibil.",
                {"routes": ["/app/backend/routes/site_menu.py"]},
                "Minim un serviciu activ în Beta.", "Website fără ofertă — conversie zero."))
        for c in active:
            if not (c.get("description") or "").strip():
                issues.append(_issue(
                    f"service_no_description:{c['id']}", "medium",
                    f"Serviciu activ fără descriere: {c.get('label')}",
                    "Serviciile active trebuie să explice DE CE există (WHY înainte de PREȚ).",
                    {"components": ["MenuManagerPage.jsx"], "data": ["site_menu"]},
                    "Fiecare serviciu activ are descriere completată în Service Manager.",
                    "Vizitatorul nu înțelege valoarea → ezitare → conversie pierdută."))
            if c.get("dest_type") == "external":
                providers = [p for p in (c.get("providers") or []) if p.get("active")]
                if not providers:
                    issues.append(_issue(
                        f"service_no_providers:{c['id']}", "medium",
                        f"Serviciu extern fără parteneri: {c.get('label')}",
                        f"'{c['id']}' e activ cu dest_type=external dar 0 parteneri activi — pagina /servicii/{c['id']} arată empty state.",
                        {"pages": [f"/servicii/{c['id']}"], "admin": ["Menu Manager → ⚙ Detalii → Parteneri"]},
                        "Minim 1 partener validat cu URL activ.",
                        "Pagina nu poate converti direct — doar lead fallback."))


async def _check_canonical_flow(issues: list):
    doc = await db.service_pages.find_one({"slug": "design-interior"}) or {}
    flow = doc.get("canonical_flow") or {}
    steps = flow.get("steps") or []
    if len(steps) != 9:
        issues.append(_issue(
            "canonical_flow_broken", "critical", "Fluxul canonic e incomplet",
            f"canonical_flow are {len(steps)} pași în loc de 9.",
            {"files": ["/app/backend/service_content_design.py"], "components": ["EcosystemFlow.jsx"]},
            "9 pași: Audit → Twin → Planșe → Design → Implementare → Specialiști → Recepție → Twin actualizat → House Health.",
            "Călătoria clientului se rupe pe toate paginile care afișează fluxul."))
    for s in steps:
        if not _route_ok(s.get("href", "")):
            issues.append(_issue(
                f"flow_dead_link:{s.get('key')}", "high",
                f"Pas de flux cu link mort: {s.get('label')}",
                f"Pasul '{s.get('key')}' duce la '{s.get('href')}' — rută necunoscută.",
                {"files": ["/app/backend/service_content_design.py"]},
                "Fiecare pas din flux duce la o destinație validă.", "Click pe flux → 404/confuzie."))
    for section, min_groups in (("audit_full", 4), ("twin_full", 4)):
        data = doc.get(section) or {}
        if len(data.get("groups") or []) < min_groups:
            issues.append(_issue(
                f"content_incomplete:{section}", "critical",
                f"Explicația canonică '{section}' e incompletă",
                f"{section} are {len(data.get('groups') or [])} grupuri (< {min_groups}).",
                {"files": ["/app/backend/service_content_design.py"], "components": ["ServiceDetailModal.jsx"]},
                "Sursa unică de adevăr completă — CTA-urile «Află tot ce include» depind de ea.",
                "Secondary CTA gol → clientul nu înțelege serviciul → nu cumpără."))
    phases = doc.get("process_phases") or []
    total_steps = sum(len(p.get("steps") or []) for p in phases)
    if total_steps != 17:
        issues.append(_issue(
            "process_phases_broken", "critical", "Procesul în 17 etape e incomplet",
            f"process_phases conține {total_steps} pași în loc de 17.",
            {"files": ["/app/backend/service_content_design.py"]},
            "17 etape în 5 faze.", "Promisiunea «17 etape» din CTA devine falsă."))


async def _check_pricing(issues: list):
    doc = await db.service_pages.find_one({"slug": "design-interior"}) or {}
    if not (doc.get("packages") or doc.get("pricing") or doc.get("hero")):
        issues.append(_issue(
            "design_interior_content_missing", "critical",
            "Conținutul Interior Intelligence lipsește",
            "service_pages/design-interior nu are conținut de bază.",
            {"files": ["/app/backend/service_content_design.py"]},
            "Pagina canonică funcțională.", "Punctul central al ecosistemului e gol."))


async def run_journey_guardian(trigger: str = "cron") -> dict:
    issues: list = []
    for check in (_check_menu, _check_canonical_flow, _check_pricing):
        try:
            await check(issues)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[guardian] check {check.__name__} failed: {e}")

    now = _now()
    seen_keys = set()
    new_tasks = 0
    for iss in issues:
        seen_keys.add(iss["key"])
        existing = await db.journey_guardian_tasks.find_one({"key": iss["key"], "status": "open"})
        if existing:
            await db.journey_guardian_tasks.update_one(
                {"_id": existing["_id"]}, {"$set": {"last_seen_at": now, "detail": iss["detail"]}})
        else:
            await db.journey_guardian_tasks.insert_one({
                "id": uuid.uuid4().hex, **iss, "status": "open", "assigned_to": "cto_ai",
                "created_at": now, "last_seen_at": now, "trigger": trigger,
            })
            new_tasks += 1

    res = await db.journey_guardian_tasks.update_many(
        {"status": "open", "key": {"$nin": list(seen_keys) or ["__none__"]}},
        {"$set": {"status": "resolved", "resolved_at": now, "resolved_by": "journey_guardian"}})
    auto_resolved = res.modified_count

    run = {
        "id": uuid.uuid4().hex, "ts": now, "trigger": trigger,
        "issues_found": len(issues), "new_tasks": new_tasks, "auto_resolved": auto_resolved,
        "by_severity": {s: sum(1 for i in issues if i["severity"] == s) for s in ("critical", "high", "medium")},
    }
    await db.journey_guardian_runs.insert_one({**run})

    from orchestrator.engine import write_ledger, notify_admins
    from orchestrator.governance import record_decision
    await write_ledger({
        "signal_kind": "journey_guardian", "playbook_id": "journey_guardian",
        "playbook_name": "Customer Journey Guardian",
        "steps": [{"action": "audit_journey", "ok": run["by_severity"]["critical"] == 0,
                   "detail": f"{len(issues)} probleme ({run['by_severity']}), {new_tasks} task-uri noi pt CTO AI, {auto_resolved} rezolvate automat"}],
        "outcome": "auto_resolved" if run["by_severity"]["critical"] == 0 else "escalated",
        "minutes_saved": 5 + 3 * auto_resolved, "escalated": run["by_severity"]["critical"] > 0, "test": False,
    })
    await record_decision({
        "signal_kind": "journey_guardian", "playbook_id": "journey_guardian",
        "playbook_name": "Customer Journey Guardian", "authority_level": 4,
        "execution_mode": "execute", "confidence": 0.9, "decided": "executed",
        "outcome": "auto_resolved" if not issues else "escalated",
        "escalated": run["by_severity"]["critical"] > 0,
        "context": {"issues": len(issues), "new_tasks": new_tasks}, "test": False,
    })
    if run["by_severity"]["critical"] > 0 and new_tasks:
        crit = [i["title"] for i in issues if i["severity"] == "critical"][:3]
        await notify_admins("🚨 Journey Guardian: probleme critice în călătoria clientului",
                            "; ".join(crit), link="/admin/repair-center")
    logger.info(f"[guardian] run done: {run}")
    run.pop("_id", None)
    return run
