"""Platform Roadmap — Evolution tracking board for admin.

Tracks every major module: what's built, what remains, priority color coding:
  urgent (red) · priority (yellow) · improvement (green).
Seeded idempotently from MODULE_CATALOG (never overwrites admin edits).
AI Analyzer (Claude) reviews the whole board and returns prioritised recommendations.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/roadmap", tags=["roadmap"])
logger = logging.getLogger("propmanage.roadmap")

PRIORITIES = ["urgent", "priority", "improvement"]
STATUSES = ["planned", "in_progress", "done"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Honest snapshot of what exists in the codebase vs what remains, per module.
MODULE_CATALOG: list[dict[str, Any]] = [
    # ── Design & UI (current sprint) ─────────────────────────────────────────
    {"key": "design_system", "title": "Design System & Tokens", "group": "Design & UI",
     "priority": "improvement", "status": "done", "progress": 100,
     "built": ["Design Tokens (CSS variables) + DesignTokensProvider", "Design Studio (editor live, presets, Design Lock)", "Palette Cascade (5 hex → 20 tokens)", "Eliminare culori hardcoded mov/albastru"],
     "remaining": []},
    {"key": "design_audit", "title": "Design Audit · UX Inspector AI", "group": "Design & UI",
     "priority": "improvement", "status": "done", "progress": 100,
     "built": ["Audit AI per pagină (Claude)", "7 legi UX (Hick, Miller, Fitts, Jakob, Nielsen, WCAG, Mobile-first)", "Cognitive Load Score", "Cache 12h + summary global"],
     "remaining": []},
    {"key": "design_intelligence", "title": "Design Intelligence Engine (P1a/b/c)", "group": "Design & UI",
     "priority": "priority", "status": "done", "progress": 100,
     "built": ["P1a Layout Optimizer AI cu Impact Score", "P1b Component Optimizer AI cu Impact Score", "P1c Evolution Engine (Observe→Propose→Test→Apply)", "Aplicare LIVE tokens + rollback cu snapshot"],
     "remaining": []},
    {"key": "design_builders", "title": "Design Studio Builders (Page/Form/Table/Menu)", "group": "Design & UI",
     "priority": "improvement", "status": "planned", "progress": 5,
     "built": ["Registry module + status placeholder în Design Studio"],
     "remaining": ["Page Builder drag&drop", "Form Builder schema-driven", "Table Builder (coloane/filtre)", "Menu Manager (NAV din DB)", "Developer Mode (inspecție componente + tokens)"]},

    # ── Viziunea 15 module (mesaj 10.07) ─────────────────────────────────────
    {"key": "ai_command_center", "title": "1 · AI Command Center", "group": "AI Core",
     "priority": "urgent", "status": "in_progress", "progress": 35,
     "built": ["Morning Briefing card în Admin Overview", "AI Insights v2 pe mai multe pagini", "Control Tower + Autonomy Engine"],
     "remaining": ["Feed unificat zilnic (cereri noi, abandonuri, escrow neconfirmat, specialiști incompleți)", "Top 5 recomandări AI acționabile cu buton de execuție", "Alerte ⚠ cu praguri configurabile"]},
    {"key": "business_health", "title": "2 · Business Health (scoruri pe departamente)", "group": "AI Core",
     "priority": "urgent", "status": "planned", "progress": 15,
     "built": ["Autonomy Engine cu scor general 94.4", "Admin Healthcheck tehnic"],
     "remaining": ["Tab dedicat cu 8 scoruri: Marketing/Marketplace/Escrow/Specialiști/Suport/Conversii/SEO/Financiar", "Cod culoare VERDE/GALBEN/ROȘU per departament", "Trend istoric per scor"]},
    {"key": "ai_insights_module", "title": "3 · AI Insights după fiecare modul", "group": "AI Core",
     "priority": "priority", "status": "in_progress", "progress": 45,
     "built": ["AI Insights pe Marketing, Analytics, Admin Overview, AI Control", "Marketing Copilot conversațional"],
     "remaining": ["Insights pe Financial (escrow/lead fee/valoare medie)", "Insights pe Marketplace (deficit specialiști per zonă)", "Standardizare AIInsightCard pe TOATE modulele"]},
    {"key": "marketplace_intelligence", "title": "4 · Marketplace Intelligence (cerere vs ofertă)", "group": "Marketplace",
     "priority": "urgent", "status": "in_progress", "progress": 30,
     "built": ["Growth endpoint: underserved counties + categorii în creștere", "Auto-Trigger Scan (creștere ≥30% MoM)"],
     "remaining": ["Vizualizare cerere vs ofertă cu bare de deficit per categorie", "Procent deficit/supraofertă calculat per județ", "Recomandări AI unde să investești"]},
    {"key": "city_analytics", "title": "5 · City Analytics", "group": "Marketplace",
     "priority": "priority", "status": "planned", "progress": 20,
     "built": ["Breakdown by_county în Marketing Dashboard", "Coverage geografic în Strategic Partners"],
     "remaining": ["Pagină dedicată per oraș: cereri/specialiști/contracte/volum RON", "Comparație orașe + recomandare AI campanii locale"]},
    {"key": "specialist_score", "title": "6 · Specialist Score (scor AI compus)", "group": "Scoring",
     "priority": "priority", "status": "in_progress", "progress": 40,
     "built": ["Health-score pe cardurile marketplace", "Specialist Progression + tiers + KYC verified"],
     "remaining": ["Scor AI compus: timp răspuns/acceptare/portofoliu/documente/contracte/escrow", "Breakdown cu stele per criteriu vizibil în admin + profil public"]},
    {"key": "client_score", "title": "7 · Client Score", "group": "Scoring",
     "priority": "improvement", "status": "planned", "progress": 5,
     "built": ["Identitate verificată (KYC infra există)"],
     "remaining": ["Scor client: identitate/plăți/feedback/proiecte finalizate", "Vizibil pentru specialiști la evaluarea cererilor"]},
    {"key": "marketplace_radar", "title": "8 · Marketplace Radar (trenduri 30 zile)", "group": "Marketplace",
     "priority": "priority", "status": "in_progress", "progress": 30,
     "built": ["Auto-Trigger detection creștere MoM per categorie×județ"],
     "remaining": ["Dashboard trenduri ±% pe 30 zile (pompe căldură, fotovoltaice etc.)", "Alertă automată la trend nou detectat"]},
    {"key": "financial_cockpit", "title": "9 · Financial Cockpit", "group": "Financiar",
     "priority": "urgent", "status": "in_progress", "progress": 35,
     "built": ["Secțiune finanțe în Admin Overview", "Wallet + escrow + Stripe checkout House Health"],
     "remaining": ["Cockpit complet: Lead Fee/Escrow/Abonamente/Comisioane/TVA estimat", "Cash Flow + MRR + ARR", "Export contabil"]},
    {"key": "notification_center", "title": "10 · Notification Center AI", "group": "AI Core",
     "priority": "priority", "status": "in_progress", "progress": 25,
     "built": ["Sistem notificări existent (in-app)", "Notificări admin la evenimente cheie (KYC, upload)"],
     "remaining": ["Centru unificat 'Ai N lucruri importante' prioritizat de AI", "Grupare pe severitate + acțiune directă din notificare"]},
    {"key": "automation_center", "title": "11 · Automation Center (reguli dacă→atunci)", "group": "AI Core",
     "priority": "priority", "status": "planned", "progress": 10,
     "built": ["Scheduler infra (APScheduler) + digest săptămânal + Auto-Trigger"],
     "remaining": ["Builder reguli: Dacă [condiție] → [acțiune]", "Reminder cerere 24h, badge Fast Response, email reactivare 30 zile", "Log execuții per regulă"]},
    {"key": "user_timeline", "title": "12 · Timeline complet per utilizator", "group": "Operațiuni",
     "priority": "improvement", "status": "in_progress", "progress": 30,
     "built": ["Demo Activity Log (fiecare acțiune demo user)", "Property Timeline pe imobil"],
     "remaining": ["Timeline vizual per user: cont→verificare→cerere→ofertă→escrow→contract→review", "Accesibil din profilul user în admin"]},
    {"key": "ai_search", "title": "13 · AI Search (limbaj natural)", "group": "AI Core",
     "priority": "improvement", "status": "planned", "progress": 15,
     "built": ["Command Palette Cmd+K cu fuzzy search pe navigație"],
     "remaining": ["Query-uri naturale: 'proiecte peste 20.000 lei', 'specialiști fără portofoliu'", "Parser AI → filtre pe colecții + rezultate live"]},
    {"key": "ceo_dashboard", "title": "14 · CEO Dashboard", "group": "AI Core",
     "priority": "priority", "status": "planned", "progress": 10,
     "built": ["Admin Overview cu KPIs + Morning Briefing (bază de plecare)"],
     "remaining": ["Dashboard separat doar pentru owner: Business Score, Revenue ▲%, Cash Flow, Escrow", "'Ai 3 priorități azi' generat de AI", "Acces restricționat super-admin/owner"]},
    {"key": "autonomy_levels", "title": "15 · Autonomy Level 0-5 (filozofia platformei)", "group": "AI Core",
     "priority": "improvement", "status": "in_progress", "progress": 40,
     "built": ["Autonomy Engine cu tier self-driving (94.4/100)", "Evolution Engine cu aprobare umană (Level 2 pe design)"],
     "remaining": ["Definire formală Level 0-5 per modul", "Level 3: execuție automată acțiuni risc redus (remindere, etichete)", "Level 4: optimizare campanii în limite setate", "Selector nivel per modul în admin"]},

    # ── Pending din fork anterior ────────────────────────────────────────────
    {"key": "phase5_marketplace", "title": "Faza 5 · Marketplace Intelligence & Autonomy 2.0", "group": "Marketplace",
     "priority": "priority", "status": "planned", "progress": 0,
     "built": [],
     "remaining": ["Reluare fază amânată înainte de pivotul pe redesign", "Se suprapune parțial cu modulele 4/8/15 — de consolidat"]},
    {"key": "resend_dns", "title": "Resend · DNS domeniu custom producție", "group": "Infrastructură",
     "priority": "improvement", "status": "in_progress", "progress": 50,
     "built": ["Resend integrat + emailuri funcționale pe domeniul curent"],
     "remaining": ["Configurare DKIM/SPF la registrar (acțiune user)", "Verificare deliverability după migrare"]},

    # ── Viziunea XOS — Experience OS (mesaj 11.06: „platforma care construiește alte platforme") ──
    {"key": "xos_tokens_themes", "title": "XOS · Design Tokens + Theme Manager", "group": "Experience OS",
     "priority": "improvement", "status": "done", "progress": 100,
     "built": ["Design Tokens (colors/spacing/typography/radius/shadow) prin DesignTokensProvider", "Theme Manager: presets Light/Dark/Corporate + teme custom", "Palette Cascade (5 hex → 20 tokens)", "Nimic hardcodat în componentele noi"],
     "remaining": []},
    {"key": "xos_ai_optimizer", "title": "XOS · AI Experience Optimizer", "group": "Experience OS",
     "priority": "improvement", "status": "done", "progress": 100,
     "built": ["= Design Intelligence Engine: Layout + Component Optimizer cu Impact Score", "Evolution Engine: AI propune → admin aprobă → aplicare LIVE + rollback"],
     "remaining": []},
    {"key": "xos_layout_widgets", "title": "XOS · Layout Builder + Widget Manager", "group": "Experience OS",
     "priority": "priority", "status": "planned", "progress": 10,
     "built": ["Component Library unificată (design-system, KpiCard/DSButton reutilizate peste tot)", "Registry componente în Design Studio"],
     "remaining": ["Toate componentele devin widget-uri (activare/dezactivare/mutare/redimensionare)", "Drag & drop pe layout per pagină (Home Client etc.)", "Responsive Builder (desktop/tabletă/telefon per layout)"]},
    {"key": "xos_role_experience", "title": "XOS · Role Experience + Visibility Engine + Dynamic UI Rules", "group": "Experience OS",
     "priority": "priority", "status": "planned", "progress": 15,
     "built": ["Gating pe roluri există hardcodat (client/specialist/admin/sub-admin scoped)", "Progressive disclosure Junior→Verified→Pro (experience tiers)", "ownerOnly/superAdminOnly pe itemii de navigație"],
     "remaining": ["Configurare vizibilitate widget per rol FĂRĂ cod (Client Junior vs Premium văd alte dashboard-uri)", "Reguli dinamice: Dacă [rol/stare] → arată/ascunde [widget]", "Visibility Engine: House Health doar dacă Verified + Twin activ etc."]},
    {"key": "xos_content_manager", "title": "XOS · Content Manager (texte/imagini/CTA/bannere fără cod)", "group": "Experience OS",
     "priority": "priority", "status": "planned", "progress": 5,
     "built": ["Template-uri email editabile din admin"],
     "remaining": ["Toate textele/CTA-urile/bannerele publice scoase din cod → colecție content", "Editor de conținut în admin cu preview", "Prețuri și pachete editabile fără cod"]},
    {"key": "xos_franchise", "title": "XOS · Franchise Experience + White Label (multi-tenant per oraș)", "group": "Experience OS",
     "priority": "improvement", "status": "planned", "progress": 5,
     "built": ["Câmp county pe cereri + specialiști (fundația de segmentare geografică)", "City Analytics per județ"],
     "remaining": ["Model tenant per oraș (Brașov ≠ București: servicii/categorii/taxe/bannere)", "Admin local per franciză cu scope pe oraș", "White Label: logo/culori/domeniu/email per franciză", "Marketplace Modules: activare module per tenant (stil OpenCart)"]},
    {"key": "xos_templates", "title": "XOS · Experience Templates", "group": "Experience OS",
     "priority": "improvement", "status": "planned", "progress": 0,
     "built": [],
     "remaining": ["Template-uri complete de experiență: Marketplace / CRM / Property Manager / Minimal / Senior / Mobile-First", "Schimbare layout complet dintr-un click"]},

    # ── CAO Autonomous Evolution Roadmap (doc: /app/docs/AUTONOMOUS_EVOLUTION_ROADMAP.md) ──
    {"key": "cao_autonomy_p1", "title": "CAO · Self-Healing + Operational Autopilot", "group": "Autonomie",
     "priority": "urgent", "status": "in_progress", "progress": 55,
     "built": ["✅ Scheduler Automation Center (rulare orară automată reguli active)", "✅ Command Center cron 07:00 + email digest fondator", "✅ Alerte → semnal orchestrator (playbook business_alert_router)", "✅ Audit Sentinel (anomaly detector orar pe loguri)", "✅ Human Dependency Index — a 5-a axă Autonomy Engine"],
     "remaining": ["Escalation Judge (agent triaj: rezolv/reîncerc/escaladez)", "Pulse Watcher (KPI delta → alertă push)", "Root-Cause Matcher (incident nou → fix istoric din Bug Memory)", "Smoke FAIL → incident auto pe /status"]},
    {"key": "cao_autonomy_p3", "title": "CAO · Business Automation (Matchmaker + Treasury)", "group": "Autonomie",
     "priority": "priority", "status": "planned", "progress": 0,
     "built": [],
     "remaining": ["Matchmaker Agent: cereri stale → escaladare 3 trepte automată", "Treasury Agent: escrow stale nudges + payment recovery emails", "KYC bandă lărgită (auto-reject <15 cu flags clare)", "Feedback done/ignored → promptul AI învață preferințele fondatorului"]},
]


async def seed_roadmap() -> None:
    """Insert catalog items only if missing — admin edits are never overwritten."""
    for m in MODULE_CATALOG:
        existing = await db.platform_roadmap.find_one({"key": m["key"]})
        if not existing:
            await db.platform_roadmap.insert_one({**m, "notes": "", "updated_at": _now(), "created_at": _now()})


class RoadmapPatch(BaseModel):
    priority: str | None = None
    status: str | None = None
    progress: int | None = None
    notes: str | None = None
    built: list[str] | None = None
    remaining: list[str] | None = None


@router.get("")
async def list_roadmap(_admin=Depends(require_role("admin"))):
    await seed_roadmap()
    items = []
    async for doc in db.platform_roadmap.find({}, {"_id": 0}):
        items.append(doc)
    order = {"urgent": 0, "priority": 1, "improvement": 2}
    items.sort(key=lambda x: (order.get(x.get("priority"), 3), -(x.get("progress") or 0)))
    counts = {"urgent": 0, "priority": 0, "improvement": 0, "done": 0, "in_progress": 0, "planned": 0}
    progress_sum = 0
    for it in items:
        counts[it.get("priority", "improvement")] = counts.get(it.get("priority", "improvement"), 0) + 1
        counts[it.get("status", "planned")] = counts.get(it.get("status", "planned"), 0) + 1
        progress_sum += it.get("progress") or 0
    return {
        "items": items,
        "total": len(items),
        "counts": counts,
        "overall_progress": round(progress_sum / len(items), 1) if items else 0,
    }


@router.patch("/{key}")
async def patch_roadmap(key: str, payload: RoadmapPatch, _admin=Depends(require_role("admin"))):
    patch = payload.model_dump(exclude_none=True)
    if "priority" in patch and patch["priority"] not in PRIORITIES:
        raise HTTPException(400, f"Prioritate invalidă. Valide: {PRIORITIES}")
    if "status" in patch and patch["status"] not in STATUSES:
        raise HTTPException(400, f"Status invalid. Valide: {STATUSES}")
    if "progress" in patch:
        patch["progress"] = max(0, min(100, int(patch["progress"])))
    if not patch:
        raise HTTPException(400, "Nimic de actualizat.")
    patch["updated_at"] = _now()
    res = await db.platform_roadmap.update_one({"key": key}, {"$set": patch})
    if res.matched_count == 0:
        raise HTTPException(404, f"Modul necunoscut: {key}")
    doc = await db.platform_roadmap.find_one({"key": key}, {"_id": 0})
    return doc


@router.post("/analyze")
async def analyze_roadmap(_admin=Depends(require_role("admin"))):
    """AI reviews the entire board and returns prioritised recommendations."""
    await seed_roadmap()
    items = []
    async for doc in db.platform_roadmap.find({}, {"_id": 0}):
        items.append(doc)

    board = "\n".join(
        f"- [{i['priority'].upper()}/{i['status']}/{i.get('progress', 0)}%] {i['title']}: "
        f"construit=({'; '.join(i.get('built') or []) or 'nimic'}) · "
        f"rămas=({'; '.join(i.get('remaining') or []) or 'nimic'})"
        for i in items
    )
    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești CTO-ul virtual al PropManage — platformă românească property services (marketplace, escrow, "
            "AI engines, design system). Primești board-ul de evoluție al platformei (module construite vs rămase, "
            "priorități roșu=urgent/galben=prioritar/verde=îmbunătățire). Analizezi TOT și răspunzi STRICT JSON: "
            "{\"verdict\": str RO ≤300c despre starea generală, "
            "\"top_priorities\": [3-5 str RO — ce să construim SĂPTĂMÂNA asta și de ce, ordonate], "
            "\"quick_wins\": [2-4 str RO — efort mic impact mare], "
            "\"risks\": [2-3 str RO — riscuri dacă amânăm modulele urgente], "
            "\"overlaps\": [str RO — module care se suprapun și pot fi consolidate], "
            "\"suggested_order\": [str — key-urile modulelor în ordinea recomandată de construire, doar cele nefinalizate]}. "
            "Fii concret, pragmatic, orientat pe impact business."
        )
        result = await claude_json(system=system, prompt=f"Board-ul actual:\n{board}", session_prefix="roadmap-analyze")
        payload = {
            "verdict": str(result.get("verdict") or "")[:400],
            "top_priorities": (result.get("top_priorities") or [])[:5],
            "quick_wins": (result.get("quick_wins") or [])[:4],
            "risks": (result.get("risks") or [])[:3],
            "overlaps": (result.get("overlaps") or [])[:4],
            "suggested_order": (result.get("suggested_order") or [])[:20],
            "ai_generated": True,
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[roadmap] LLM fail: {e} — fallback")
        urgent = [i for i in items if i["priority"] == "urgent" and i["status"] != "done"]
        payload = {
            "verdict": "Analiză rule-based (LLM indisponibil). Concentrează-te pe modulele roșii nefinalizate.",
            "top_priorities": [f"Continuă: {i['title']} ({i.get('progress', 0)}%)" for i in urgent][:5],
            "quick_wins": ["Rulează analiza AI pentru recomandări detaliate."],
            "risks": [], "overlaps": [], "suggested_order": [i["key"] for i in urgent],
            "ai_generated": False,
        }

    doc = {"generated_at": _now(), "result": payload}
    await db.platform_roadmap_analysis.update_one({"_id": "latest"}, {"$set": doc}, upsert=True)
    return {**payload, "generated_at": doc["generated_at"]}


@router.get("/analysis/latest")
async def latest_analysis(_admin=Depends(require_role("admin"))):
    doc = await db.platform_roadmap_analysis.find_one({"_id": "latest"})
    if not doc:
        return {"result": None}
    return {"result": doc.get("result"), "generated_at": doc.get("generated_at")}
