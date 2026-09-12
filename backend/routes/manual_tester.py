"""Manual Tester (Admin) — predefined test suites + AI test-case generator.

Endpoints:
    GET  /api/admin/manual-tester/suites         — bundled list of test suites + cases
    POST /api/admin/manual-tester/runs           — save a test-run session (PASS/FAIL/SKIP per case)
    GET  /api/admin/manual-tester/runs           — list past test-runs (last 30)
    POST /api/admin/manual-tester/suggest        — AI generates extra test cases for a topic

The "suites" are hardcoded here so QA stays version-controlled. Admin can
add ad-hoc / AI-suggested cases per run; they're persisted in the run doc.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import require_role

logger = logging.getLogger("propmanage.manual_tester")

router = APIRouter(prefix="/api/admin/manual-tester", tags=["admin-manual-tester"])


# ============================================================================
# PREDEFINED TEST SUITES (Romanian, structured for a human QA-er)
# ============================================================================
SUITES = [
    {
        "id": "auth_roles",
        "name": "Autentificare & Roluri",
        "icon": "🔐",
        "description": "Login, logout, switch view, integritate role în UI.",
        "cases": [
            {
                "id": "auth_login_client",
                "title": "Login ca CLIENT funcționează și afișează dashboard-ul corect",
                "steps": [
                    "Mergi la /login",
                    "Email: client@propmanage.io · Parola: Client123!",
                    "Apasă Login",
                ],
                "expected": "Redirecționare la /client. Header-ul afișează badge 'Client'. URL-ul rămâne /client (NU /specialist).",
            },
            {
                "id": "auth_login_specialist",
                "title": "Login ca SPECIALIST",
                "steps": [
                    "Logout (dacă ești logat)",
                    "Login cu specialist@propmanage.io / Spec123!",
                ],
                "expected": "Redirecționare la /specialist. Header arată badge 'Specialist'.",
            },
            {
                "id": "auth_login_admin",
                "title": "Login ca ADMIN",
                "steps": [
                    "Login cu admin@propmanage.io / parola admin (SEED_ADMIN_PASSWORD din backend/.env)",
                ],
                "expected": "Redirecționare la /admin. Apare sidebar admin cu toate categoriile.",
            },
            {
                "id": "auth_dual_role_consistency",
                "title": "Integritate dual-role (regression bug Feb 2026)",
                "steps": [
                    "Login ca client@propmanage.io",
                    "Verifică în consola browserului: localStorage e gol",
                    "Verifică în Network → /api/auth/me că răspunsul are role='client' și active_view='client'",
                ],
                "expected": "Niciun redirect anormal către /specialist. dual_role_enabled=false pentru contul demo.",
            },
            {
                "id": "auth_logout",
                "title": "Logout curăță sesiunea",
                "steps": [
                    "Fiind logat, apasă pe avatar → Logout",
                    "Încearcă să accesezi direct /client",
                ],
                "expected": "Redirecționare la /login. Niciun acces nu mai e permis fără re-autentificare.",
            },
            {
                "id": "auth_invalid_password",
                "title": "Login cu parolă greșită",
                "steps": [
                    "Mergi la /login",
                    "Email valid + parolă greșită",
                ],
                "expected": "Mesaj eroare clar în română. Niciun cookie nu e setat. Form rămâne pe loc.",
            },
        ],
    },
    {
        "id": "client_dashboard",
        "name": "Dashboard Client",
        "icon": "🏠",
        "description": "Funcționalitățile principale ale clientului.",
        "cases": [
            {
                "id": "client_dash_load",
                "title": "Dashboard se încarcă fără erori",
                "steps": ["Login ca client", "Verifică consola browser"],
                "expected": "Nu apar erori roșii. Toate widget-urile se încarcă (proprietăți, cereri, wallet, House Health card).",
            },
            {
                "id": "client_properties_list",
                "title": "Lista de proprietăți e vizibilă",
                "steps": ["Pe /client, scroll la secțiunea 'Proprietățile tale'"],
                "expected": "Sunt afișate proprietățile clientului cu nume, adresă, fotografii. Buton 'Adaugă proprietate' funcțional.",
            },
            {
                "id": "client_request_create",
                "title": "Creare cerere nouă de servicii",
                "steps": [
                    "Click 'Creează cerere'",
                    "Completează: categorie, titlu, descriere, buget",
                    "Submit",
                ],
                "expected": "Cererea apare în lista 'Cererile mele' cu status 'open'. Apare un toast de confirmare.",
            },
            {
                "id": "client_wallet",
                "title": "Wallet client are sold corect",
                "steps": ["Pe dashboard, verifică widget Wallet"],
                "expected": "Sold afișat în RON. Buton 'Reîncarcă' funcțional.",
            },
        ],
    },
    {
        "id": "house_health_core",
        "name": "House Health · Core",
        "icon": "❤",
        "description": "Modul House Health — Score, Air, Docs, History.",
        "cases": [
            {
                "id": "hh_card_visible",
                "title": "Cardul House Health apare pe dashboard client",
                "steps": ["Login ca client@propmanage.io", "Scroll pe /client"],
                "expected": "Apare un card 'House Health' cu badge subscription, scor, buton 'Deschide modul'.",
            },
            {
                "id": "hh_page_loads",
                "title": "Pagina House Health se deschide",
                "steps": [
                    "Click 'Deschide modul' pe cardul HH",
                    "URL devine /house-health/{twinId}",
                ],
                "expected": "Sidebar cu 9 tab-uri: Scor, Aer, Termic, Umiditate, Electric, Radon, Docs, Istoric, Recomandări. Tema dark.",
            },
            {
                "id": "hh_score_displayed",
                "title": "Tab Scor arată scor + clasificare",
                "steps": ["Tab 'Scor proprietate'"],
                "expected": "Scor /100 vizibil. Badge clasificare (Excellent/Good/Fair/Needs Attention) colorat corect.",
            },
            {
                "id": "hh_docs_upload_local",
                "title": "Upload document local",
                "steps": [
                    "Tab 'Documentație tehnică'",
                    "Mode: 'Fișier local'",
                    "Alege categoria, completează data + descriere",
                    "Selectează un PDF mic (<5MB)",
                    "Adaugă document",
                ],
                "expected": "Documentul apare în listă cu storage='local', mărime kb, link 'Descarcă' funcțional.",
            },
            {
                "id": "hh_docs_upload_link",
                "title": "Upload link extern (Google Drive/Dropbox)",
                "steps": [
                    "Mode: 'Link extern'",
                    "Selectează 'Google Drive'",
                    "Lipește un link valid",
                    "Adaugă",
                ],
                "expected": "Apare în listă cu badge 'link google_drive', buton 'Deschide' care merge la link-ul respectiv.",
            },
            {
                "id": "hh_docs_delete",
                "title": "Ștergere document funcționează",
                "steps": [
                    "Click pe iconița trash pe un document",
                    "Confirm dialog",
                ],
                "expected": "Documentul dispare din listă. Refresh confirmă ștergerea persistentă.",
            },
            {
                "id": "hh_history_timeline",
                "title": "Istoric verificări - timeline",
                "steps": ["Tab 'Istoric verificări'"],
                "expected": "Timeline vertical cu evaluările aprobate + rapoartele HH. Eveniment cel mai recent în top.",
            },
        ],
    },
    {
        "id": "house_health_recommendations",
        "name": "House Health · Recomandări + Marketplace",
        "icon": "💡",
        "description": "F4.2 + F4.4 — recomandări specialist și publicare în marketplace.",
        "cases": [
            {
                "id": "hh_rec_create",
                "title": "Specialist creează o recomandare nouă",
                "steps": [
                    "Login ca specialist@propmanage.io",
                    "Mergi la /house-health/2d0a899472b34e32a8eaf79b88d7c012",
                    "Tab 'Recomandări'",
                    "Click 'Recomandare nouă'",
                    "Completează: evaluare aprobată, titlu, descriere, prioritate URGENT, categorie air, cost 350€, deadline",
                    "Salvează",
                ],
                "expected": "Recomandarea apare în listă cu badge 'URGENT' rose. Specialist vede butoane '✓ Done' și 'trash'.",
            },
            {
                "id": "hh_rec_client_view",
                "title": "Client vede recomandările specialistului",
                "steps": [
                    "Logout din specialist · Login ca client",
                    "Mergi la /house-health/{twinId}",
                    "Tab 'Recomandări'",
                ],
                "expected": "Vede recomandările. NU vede butonul 'Recomandare nouă'. Vede butonul '📢 Publică în marketplace' pe recomandările Urgent/Recomandat.",
            },
            {
                "id": "hh_rec_publish_to_marketplace",
                "title": "Publish to marketplace funcționează",
                "steps": [
                    "Fiind client, click '📢 Publică în marketplace' pe o recomandare urgentă",
                    "Confirm dialog",
                ],
                "expected": "Alert: 'Publicat în marketplace! Request ID: ...'. Recomandarea afișează 'Publicat în marketplace' și butonul de publish dispare.",
            },
            {
                "id": "hh_rec_no_publish_monitor",
                "title": "Recomandare 'Monitorizare' NU poate fi publicată",
                "steps": [
                    "Specialist creează o recomandare cu prioritate 'Monitorizare'",
                    "Client vede recomandarea în tab",
                ],
                "expected": "Butonul '📢 Publică în marketplace' NU apare pe recomandarea cu prioritate Monitorizare.",
            },
        ],
    },
    {
        "id": "house_health_billing",
        "name": "House Health · Abonamente + Stripe",
        "icon": "💳",
        "description": "F4.1 + F4.3 — Plans CRUD, Scoring config, Stripe checkout.",
        "cases": [
            {
                "id": "hh_upgrade_page",
                "title": "Pagina /house-health/upgrade arată 3 planuri",
                "steps": ["Mergi la /house-health/upgrade ca client"],
                "expected": "3 carduri: Basic 9€, Pro 29€ (badge 'Recomandat'), Premium 79€. Features listate. Buton 'Activează acum' pe fiecare.",
            },
            {
                "id": "hh_stripe_redirect",
                "title": "Click pe plan redirecționează la Stripe",
                "steps": [
                    "Pe /house-health/upgrade",
                    "Click 'Activează acum' pe Premium",
                ],
                "expected": "Redirect către checkout.stripe.com/c/pay/... . NU completa plata în test mode — întoarce-te.",
            },
            {
                "id": "hh_admin_plans_crud",
                "title": "Admin: editează prețul unui plan",
                "steps": [
                    "Login ca admin",
                    "Mergi la /admin/house-health",
                    "Tab 'Planuri'",
                    "Click pe creion pe planul 'Basic'",
                    "Schimbă price la 12",
                    "Salvează",
                ],
                "expected": "Planul afișează noul preț. Pe /house-health/upgrade (după refresh) cardul Basic arată 12€.",
            },
            {
                "id": "hh_admin_scoring",
                "title": "Admin: ponderi formula scor — validare 100",
                "steps": [
                    "Pe /admin/house-health → tab 'Formula scor'",
                    "Schimbă o pondere astfel încât suma să fie 99",
                ],
                "expected": "Total se afișează în roșu. Buton 'Salvează' devine disabled. La revenire la 100, devine verde + activ.",
            },
        ],
    },
    {
        "id": "marketplace",
        "name": "Marketplace · Cereri & Oferte",
        "icon": "🛒",
        "description": "Flux complet client→specialist pentru o cerere.",
        "cases": [
            {
                "id": "mp_request_open",
                "title": "Cererea apare pentru specialist",
                "steps": [
                    "Login ca specialist",
                    "Mergi la dashboard sau /specialist/requests",
                ],
                "expected": "Lista de cereri 'open' include cea publicată din House Health (cu badge house_health_source).",
            },
            {
                "id": "mp_offer_create",
                "title": "Specialist face o ofertă",
                "steps": [
                    "Click pe o cerere open",
                    "Completează preț + descriere ofertă",
                    "Trimite",
                ],
                "expected": "Oferta apare în secțiunea ofertelor cererii. Client primește notificare.",
            },
            {
                "id": "mp_offer_accept",
                "title": "Client acceptă o ofertă (+ commission HH se capturează)",
                "steps": [
                    "Login ca client",
                    "Mergi la cererea respectivă",
                    "Click 'Acceptă' pe o ofertă",
                ],
                "expected": "Status devine 'in_progress'. Dacă cererea provine din House Health, audit log are 'commission_captured'.",
            },
        ],
    },
    {
        "id": "admin_panel",
        "name": "Admin Panel",
        "icon": "⚙",
        "description": "Funcționalități admin: Twin Orchestrator, alerte, costuri.",
        "cases": [
            {
                "id": "admin_twin_loaded",
                "title": "Twin Orchestrator se încarcă",
                "steps": ["Login ca admin", "Mergi la /admin/twin"],
                "expected": "Chat interface vizibilă. Lista de Scheduled Actions afișată.",
            },
            {
                "id": "admin_twin_ask",
                "title": "Twin răspunde la o întrebare",
                "steps": [
                    "Pe /admin/twin",
                    "Întreabă: 'Câți utilizatori activi sunt în ultimele 7 zile?'",
                ],
                "expected": "Răspuns coerent în română (cu cifre concrete dacă sunt disponibile).",
            },
            {
                "id": "admin_cost_roi",
                "title": "Card Cost & ROI",
                "steps": ["Pe /admin, scroll la card Cost & ROI"],
                "expected": "Afișează cheltuieli LLM/Stripe/email pe ultimele 30 zile.",
            },
        ],
    },
    {
        "id": "ux_general",
        "name": "UX General",
        "icon": "✨",
        "description": "Probleme generale de UI/UX.",
        "cases": [
            {
                "id": "ux_theme_switcher_visible",
                "title": "Switcher de temă vizibil în header dashboard",
                "steps": [
                    "Login ca client/admin/specialist",
                    "Verifică header-ul dashboard-ului",
                ],
                "expected": "Apare butonul de schimbare temă (icon Sun/Moon). Click → dropdown cu cele 2 teme: Dark (default) + Warm Linen 2026.",
            },
            {
                "id": "ux_theme_warm_linen",
                "title": "Tema 'Warm Linen 2026' aplică background cream",
                "steps": [
                    "Click pe theme switcher → selectează 'Warm Linen 2026'",
                    "Navighează pe /house-health/{twinId}, /admin/manual-tester",
                ],
                "expected": "Background devine cream (#f7f3ec), text negru/taupe, accente emerald închis. Toate paginile arată coerent în tema light. Tranziții fluide.",
            },
            {
                "id": "ux_theme_persistence",
                "title": "Preferința de temă persistă peste refresh",
                "steps": [
                    "Selectează 'Warm Linen 2026'",
                    "Refresh pagina (F5)",
                ],
                "expected": "Tema rămâne 'Warm Linen' după refresh (salvată în localStorage cheia `propmanage_theme`).",
            },
            {
                "id": "ux_dark_mode",
                "title": "Tema dark e implicită pentru utilizatori noi",
                "steps": ["Browser nou / Incognito", "Mergi la /login"],
                "expected": "Background stone-950, tema dark e folosită implicit. Niciun flash de cream la încărcare.",
            },
            {
                "id": "ux_mobile_responsive",
                "title": "Responsiv pe mobile (375px)",
                "steps": [
                    "Deschide DevTools → viewport 375x812",
                    "Navigează: /client, /house-health/{twinId}, /admin",
                ],
                "expected": "Niciun overflow orizontal. Sidebar-uri se transformă în drawer sau tabs swipeable.",
            },
            {
                "id": "ux_cookie_banner",
                "title": "Cookie banner nu blochează interacțiunile",
                "steps": ["Login proaspăt, observă cookie banner-ul"],
                "expected": "Banner-ul nu acoperă butoanele critice. Click pe 'Accept toate' îl face să dispară. În tema light, stilizat coerent.",
            },
            {
                "id": "ux_loading_states",
                "title": "Spinner-uri vs ecran gol",
                "steps": ["Navighează la o pagină care încarcă date"],
                "expected": "Apare un spinner / skeleton, NU ecran gol cu flash de date.",
            },
            {
                "id": "ux_button_contrast",
                "title": "Contrast butoane corect în ambele teme",
                "steps": [
                    "Verifică butoane principale în dark",
                    "Schimbă pe Warm Linen 2026 și re-verifică",
                ],
                "expected": "Toate butoanele au contrast suficient (text vs background). Niciun text invizibil pe propriul background.",
            },
            {
                "id": "ux_focus_states",
                "title": "Focus states vizibile (keyboard nav)",
                "steps": ["Folosește Tab pe orice formular (login, docs upload)"],
                "expected": "Fiecare element focusat are un ring vizibil pe contur. Util pentru navigare cu tastatura.",
            },
        ],
    },
]


# ============================================================================
# ENDPOINTS
# ============================================================================
@router.get("/suites")
async def list_suites(user=Depends(require_role("admin"))):
    """Return all predefined test suites."""
    total = sum(len(s["cases"]) for s in SUITES)
    return {"suites": SUITES, "suite_count": len(SUITES), "total_cases": total}


class TestResultIn(BaseModel):
    case_id: str
    status: str  # pass | fail | skip
    notes: Optional[str] = ""


class TestRunIn(BaseModel):
    suite_id: Optional[str] = None  # None = mixed run across suites
    label: Optional[str] = ""
    environment: Optional[str] = "preview"  # preview | production
    results: List[TestResultIn]


@router.post("/runs")
async def save_run(payload: TestRunIn, user=Depends(require_role("admin"))):
    valid = {"pass", "fail", "skip"}
    for r in payload.results:
        if r.status not in valid:
            raise HTTPException(400, f"Status invalid: {r.status}. Permis: pass/fail/skip.")
    doc = {
        "id": uuid.uuid4().hex,
        "suite_id": payload.suite_id,
        "label": payload.label or "",
        "environment": payload.environment or "preview",
        "tester_user_id": user["id"],
        "tester_email": user.get("email"),
        "results": [r.dict() for r in payload.results],
        "summary": {
            "total": len(payload.results),
            "pass": sum(1 for r in payload.results if r.status == "pass"),
            "fail": sum(1 for r in payload.results if r.status == "fail"),
            "skip": sum(1 for r in payload.results if r.status == "skip"),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.manual_test_runs.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "run": doc}


@router.get("/runs")
async def list_runs(limit: int = 30, user=Depends(require_role("admin"))):
    items = []
    async for r in db.manual_test_runs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit):
        items.append(r)
    return {"items": items, "count": len(items)}


# ============================================================================
# Compounding QA — trends over time
# ============================================================================
@router.get("/trends")
async def trends(days: int = 30, user=Depends(require_role("admin"))):
    """Aggregate per-suite pass-rate trend over the last N days.

    Returns:
      - by_suite: list of {suite_id, suite_name, total_runs, total_cases,
        avg_pass_rate, latest_pass_rate, trend ("up"|"down"|"flat"),
        last_run_at}
      - alerts: list of suites where latest pass-rate dropped >=20 percentage
        points below the 30d average — early warning signal.
      - overall: {total_runs, avg_pass_rate, total_failures}
      - timeline: per-day aggregate {date, pass, fail, skip}
    """
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    suite_meta = {s["id"]: s for s in SUITES}

    # Pull runs once, aggregate in Python (cleaner than nested Mongo pipelines).
    by_suite_runs: dict = {}  # suite_id -> [(pass_rate, created_at, summary)]
    timeline: dict = {}  # date_str -> {"pass": x, "fail": y, "skip": z}
    overall_total_cases = 0
    overall_total_pass = 0
    overall_total_runs = 0
    overall_total_failures = 0

    async for run in db.manual_test_runs.find({"created_at": {"$gte": cutoff}}, {"_id": 0}):
        sid = run.get("suite_id") or "_mixed"
        summary = run.get("summary") or {}
        total = int(summary.get("total") or 0)
        p = int(summary.get("pass") or 0)
        f = int(summary.get("fail") or 0)
        sk = int(summary.get("skip") or 0)
        if total == 0:
            continue
        pass_rate = round(100.0 * p / total, 1)
        by_suite_runs.setdefault(sid, []).append({
            "pass_rate": pass_rate, "created_at": run.get("created_at"),
            "summary": {"total": total, "pass": p, "fail": f, "skip": sk},
            "tester": run.get("tester_email"),
        })
        # Daily timeline
        date_str = (run.get("created_at") or "")[:10]
        d = timeline.setdefault(date_str, {"pass": 0, "fail": 0, "skip": 0})
        d["pass"] += p
        d["fail"] += f
        d["skip"] += sk
        overall_total_cases += total
        overall_total_pass += p
        overall_total_failures += f
        overall_total_runs += 1

    by_suite = []
    alerts = []
    for sid, runs in by_suite_runs.items():
        runs.sort(key=lambda r: r["created_at"] or "")
        rates = [r["pass_rate"] for r in runs]
        avg = round(sum(rates) / len(rates), 1) if rates else 0
        latest = rates[-1] if rates else 0
        first_half = rates[: max(1, len(rates) // 2)]
        second_half = rates[max(1, len(rates) // 2):]
        if second_half and first_half:
            delta = round(sum(second_half) / len(second_half) - sum(first_half) / len(first_half), 1)
        else:
            delta = 0
        trend = "up" if delta > 3 else ("down" if delta < -3 else "flat")
        total_cases = sum(r["summary"]["total"] for r in runs)
        entry = {
            "suite_id": sid,
            "suite_name": (suite_meta.get(sid) or {}).get("name", sid),
            "suite_icon": (suite_meta.get(sid) or {}).get("icon", "🧪"),
            "total_runs": len(runs),
            "total_cases": total_cases,
            "avg_pass_rate": avg,
            "latest_pass_rate": latest,
            "trend": trend,
            "delta_pct": delta,
            "last_run_at": runs[-1]["created_at"],
            "last_tester": runs[-1].get("tester"),
            "history": [{"pass_rate": r["pass_rate"], "at": r["created_at"], "total": r["summary"]["total"]} for r in runs[-20:]],
        }
        by_suite.append(entry)
        # Alert: latest dropped 20+ pts below avg
        if avg >= 50 and latest < avg - 20:
            alerts.append({
                "suite_id": sid,
                "suite_name": entry["suite_name"],
                "avg_pass_rate": avg,
                "latest_pass_rate": latest,
                "severity": "high" if latest < avg - 35 else "medium",
                "message": f"Pass-rate scăzut de la avg {avg}% la {latest}% în ultimul run.",
            })

    by_suite.sort(key=lambda s: s["latest_pass_rate"])
    timeline_list = [{"date": d, **vals} for d, vals in sorted(timeline.items())]

    overall_avg = round(100.0 * overall_total_pass / overall_total_cases, 1) if overall_total_cases else 0

    return {
        "window_days": days,
        "overall": {
            "total_runs": overall_total_runs,
            "total_cases_executed": overall_total_cases,
            "avg_pass_rate": overall_avg,
            "total_failures": overall_total_failures,
        },
        "by_suite": by_suite,
        "alerts": alerts,
        "timeline": timeline_list,
    }


class SuggestIn(BaseModel):
    topic: str
    context: Optional[str] = ""


@router.post("/suggest")
async def suggest_cases(payload: SuggestIn, user=Depends(require_role("admin"))):
    """Use LLM to generate additional test cases for a given topic.

    Topic example: "Twin Orchestrator scheduling", "House Health checkout edge cases".
    """
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise HTTPException(503, "EMERGENT_LLM_KEY nu este configurat.")

    system = (
        "Ești un QA engineer senior pentru o aplicație de management imobiliar (PropManage). "
        "Generezi cazuri de test manuale în română, structurate ca JSON. "
        "Fii pragmatic — focus pe edge cases, integritate de date, fluxuri end-to-end pentru utilizatori reali. "
        "Răspunde DOAR cu un array JSON valid, fără text suplimentar, fără markdown wrapper. "
        "Schema fiecărui caz: { id: string slug, title: string, steps: string[], expected: string }. "
        "Generează între 3 și 6 cazuri relevante pentru topicul cerut."
    )
    prompt = (
        f"Topic: {payload.topic}\n"
        + (f"Context suplimentar:\n{payload.context}\n" if payload.context else "")
        + "\nReturnează JSON array."
    )

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(api_key=key, session_id=f"manual_tester_{uuid.uuid4().hex[:8]}",
                       system_message=system).with_model("anthropic", "claude-sonnet-4-5-20250929")
        raw = await chat.send_message(UserMessage(text=prompt))
        # Try to extract JSON
        import json
        text = (raw or "").strip()
        if text.startswith("```"):
            # strip fenced code
            text = "\n".join(line for line in text.splitlines() if not line.startswith("```"))
        # Find first '[' and last ']'
        i, j = text.find("["), text.rfind("]")
        if i == -1 or j == -1 or j <= i:
            raise HTTPException(502, "AI nu a returnat JSON valid.")
        cases = json.loads(text[i:j + 1])
        # Sanitize
        cleaned = []
        for c in cases[:8]:
            cleaned.append({
                "id": str(c.get("id") or uuid.uuid4().hex[:8])[:64],
                "title": str(c.get("title") or "(fără titlu)")[:200],
                "steps": [str(s)[:300] for s in (c.get("steps") or [])][:10],
                "expected": str(c.get("expected") or "")[:500],
                "ai_suggested": True,
            })
        return {"cases": cleaned, "count": len(cleaned), "raw_topic": payload.topic}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[manual_tester.suggest] failed: {e}")
        raise HTTPException(500, f"Eroare AI: {str(e)[:200]}")
