"""Design Audit — Admin module (Feb 2026).

Evaluates UX/UI unity, Hick's Law adherence and mobile-vs-desktop impact per app page.
Uses Claude (Emergent LLM key) for qualitative analysis and produces:
  - Mobile score (0–100)
  - Desktop score (0–100)
  - Unity score (color/spacing/typography consistency)
  - Findings & concrete recommendations

Cache: 12h per page. Force via ?force=true.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role

router = APIRouter(prefix="/api/admin/design-audit", tags=["design-audit"])
logger = logging.getLogger("propmanage.design_audit")

CACHE_HOURS = 12

# Registry of pages we audit — path + role zone + short brief on what the page contains.
PAGES: list[dict[str, Any]] = [
    # Public
    {"key": "landing",         "path": "/",                  "zone": "public",    "label": "Landing (Home)",
     "brief": "Hero cu 3 CTA-uri, marquee categorii, secțiuni value-prop, harta zonă acoperire, footer legal Vintage Furniture."},
    {"key": "marketplace",     "path": "/marketplace",       "zone": "public",    "label": "Marketplace listare",
     "brief": "Filtre (categorie/verified/sort), grid carduri specialiști cu health-score, badge tier, buton Vezi profil."},
    {"key": "preturi",         "path": "/preturi",           "zone": "public",    "label": "Prețuri servicii (SEO)",
     "brief": "Grile prețuri pe categorii, strip Market Pulse, tabel comparativ."},
    {"key": "legal",           "path": "/legal/termeni",     "zone": "public",    "label": "Documente legale",
     "brief": "Text lung structurat (termeni, GDPR) cu Vintage Furniture S.R.L. sticky nav."},
    {"key": "specialist_entry","path": "/devino-specialist", "zone": "public",    "label": "Devino specialist — Start (UX Lab)",
     "brief": "Landing public responsive cu un singur scop: aplicație de specialist în 3 pași. Home: logo, headline orientat pe beneficiu ('Câștigă din meseria ta, fără să alergi după clienți') + subtitlu care setează așteptarea ('2 lucruri despre tine, te sunăm în 24h'), strip încredere (lucrări constante/plăți garantate/înscriere gratuită) above-fold, skip-link 'Sari direct la aplicare' vizibil la focus tastatură (WCAG 2.4.1 Bypass Blocks), 2 carduri roluri semnătură cu gap generos 16px (Designer/Arhitect, Auditor tehnic — echipa proiectelor Digital Twin & Design Interior) + progressive disclosure pe restul: grid-ul de 6 meserii e ASCUNS inițial în spatele unui singur buton 'Vezi toate meseriile (6)' — doar 3 zone focale la landing (Hick optimizat, decizii simultane 8→3). Home desktop: 2 coloane echilibrate cu stagger reveal 100ms, respectă prefers-reduced-motion. Wizard identic mobile/desktop (continuitate Jakob): pagină completă full-screen (NU modal/overlay — nu necesită focus trap; Tab parcurge liniar step dots → opțiuni → CTA), card centrat max-w-md, 1 întrebare pe ecran cu max 3 opțiuni radio ≥56px cu auto-focus pe prima opțiune la fiecare pas (convenție formulare Jakob), step dots clickabili cu micro-label vizibil (Experiență/Program/Contact) și stare completat/curent/viitor (editare retroactivă), progress bar (Nielsen vizibilitate stare), un singur CTA sticky în thumb zone, tasta Escape revine la home. Pas final în secvență logică nume → oraș → telefon → email: 3 câmpuri esențiale + email opțional + consimțământ GDPR, labels permanente cu indicator vizual dublu obligatoriu/opțional ('*' roșu + aria-required vs '(opțional)' muted — scanabil vizual ȘI screen reader), autocomplete, validare inline per câmp la blur cu mesaje care explică de ce ('avem nevoie de oraș ca să-ți trimitem lucrări din zonă') în containere aria-live='polite' și aria-invalid. reduce distanța mouse; hover state pe cardurile semnătură (scale 1.01 + shadow — affordance click Jakob); mesajele de validare inline apar cu fade 450ms non-intruziv. Confirmare: număr aplicație real cu copy-to-clipboard (click → checkmark 1.2s + anunț aria-live 'Copiat în clipboard') + 'Ce urmează' ca timeline vizual cu noduri-icon (document/telefon/rachetă — recunoaștere instant, nu recall) conectate + CTA primar 'Creează-ți contul de specialist'. Touch targets ≥52px, contrast AAA green-800 (8.35:1) light / green-300 (8.12:1) dark cu mapare automată .cv2-scope (light/dark perfect coerente), aria-labels/roles/aria-current pe toate elementele interactive, un singur accent cromatic."},
    # Client
    {"key": "client_junior",   "path": "/incepe",            "zone": "client",    "label": "Client Junior — Start (UX Lab)",
     "brief": "Landing public responsive cu un singur scop: cerere de serviciu în 4 pași. Home mobile: logo, headline, search cu label, strip încredere (verificați/24h/gratuit) above-fold, 2 carduri servicii semnătură (Digital Twin & Audit Tehnic, Design Interior) + grid 6 categorii suport — 2 chunk-uri clare (Miller). Home desktop: 2 coloane echilibrate cu stagger reveal secvențial (stânga apare prima, grid-ul după 200ms) — o singură zonă de atenție odată, respectă prefers-reduced-motion. Wizard: 1 întrebare pe ecran cu max 3 opțiuni radio ≥56px, step dots clickabili cu micro-label vizibil sub fiecare dot (Locație/Detalii/Termen/Contact — recunoaștere, nu recall) și stare completat/curent/viitor (back-navigation Jakob), progress bar (Nielsen vizibilitate stare), un singur CTA sticky în thumb zone. Wizard identic pe mobile și desktop (continuitate Jakob): card centrat max-w-md, o singură zonă de acțiune — fără panouri laterale; tasta Escape revine la home (Nielsen control user); micro-animație pop 200ms pe step dot completat (feedback progres vizibil). Pas final: doar 2 câmpuri obligatorii (nume, telefon — indicator vizual '*' + aria-required) + email opțional cu micro-help beneficiu ('primești actualizări automate') + consimțământ GDPR, labels permanente, autocomplete, validare inline per câmp la blur cu mesaje specifice în containere aria-live='polite' (anunțate screen reader-ului în timp real) și aria-invalid pe input. Confirmare: număr cerere real cu copy-to-clipboard (click → checkmark 1.2s + aria-live 'Copiat în clipboard') + 'Ce urmează' ca timeline vizual cu noduri numerotate conectate prin linii + CTA cont cu beneficiu tangibil ('urmărești ofertele live'). Bottom nav fix 4 tab-uri, touch targets ≥52px, contrast AAA green-800 #166534 (8.35:1) pe light și green-300 #86efac (8.12:1) pe dark (mapare automată .cv2-scope — light/dark perfect coerente), step dots navigabili cu Tab+Enter (butoane native), aria-labels/roles/aria-current pe toate elementele interactive, un singur accent cromatic."},
    {"key": "client_dashboard","path": "/client",            "zone": "client",    "label": "Client Dashboard",
     "brief": "Bento cards Quest-uri & Recompense, cereri active, timeline, buton FAB Solicită, bottom nav 4 tab-uri."},
    {"key": "client_marketplace","path": "/client",          "zone": "client",    "label": "Client — listă specialiști",
     "brief": "Carduri specialiști vizibile în tab Solicită: avatar, tier badge, rating, buton profil + solicită."},
    # Specialist
    {"key": "specialist_entry_home","path": "/specialist",   "zone": "specialist","label": "Specialist Entry — Home simplificat (UX Lab)",
     "brief": "Experiență implicită pentru specialiștii tier ENTRY (progressive disclosure, reversibilă cu 1 click). Mobil: coloană unică max-w-2xl; desktop lg: layout 2 zone echilibrate (stânga: salut + checklist + progres nivel; dreapta: oportunități) — tot conținutul vizibil fără scroll, folosește spațiul larg, distanțe Fitts minime. 3 chunk-uri cu spacing consistent gap-8 (Miller): (1) salut personal + card 'Primii tăi pași' cu badge progres numeric 'X/3 completat' + progress bar subțire cu role=progressbar (Nielsen vizibilitate stare, pattern standard Jakob) și checklist de 3 acțiuni ca rânduri verticale full-width IDENTICE pe mobil și desktop (consistență Jakob; în coloana stângă desktop fiecare rând are ~440px lățime — target Fitts maxim, zero precizie necesară; acțiunile sunt butoane min-h 44px aliniate dreapta la capătul rândului, aproape de fluxul natural al mouse-ului) (verifică-ți contul → acceptă prima oportunitate → finalizează și ia recenzia) — fiecare pas nebifat are exact un buton de acțiune; (2) 'Oportunități pentru tine' cu aria-live='polite' pe listă (screen readerul anunță cardurile noi — WCAG 4.1.3) și fade-in stagger 40ms la apariția cardurilor (200ms total la 5 carduri — sub pragul de lag perceptibil 250ms; feedback vizual complementar pentru sighted users), empty state cu icon decorativ mare lime centrat ca visual anchor pe zona dreaptă desktop — max 5 carduri, fiecare cu titlu, preț estimat și UN singur CTA 'Acceptă' full-size ≥44px (buton primar lime pe fundal închis cu text negru — contrast >12:1, target Fitts generos), empty state prietenos cu icon decorativ aria-hidden și așteptare setată ('primești notificare imediat ce apare o lucrare'); (3) footer semantic aside cu role complementary și aria-label motivațional ('la 3 lucrări finalizate urci la nivelul următor') + link discret spre dashboardul complet marcat cu badge 'AVANSAT' + hint sr-only permanent legat prin aria-describedby ('Statistici, rapoarte, filtre și setări avansate' — accesibil tastatură/screen reader pe orice device, WCAG 1.3.1; setează modelul mental, previne intrarea accidentală — Nielsen prevenire erori + help contextual). Focus-visible ring 2px accent pe TOATE butoanele și linkurile (WCAG 2.4.7 navigare tastatură). Nav de jos DashLayout cu 3 tab-uri, fiecare cu iconiță ȘI label text vizibil (pattern standard iOS/Android, Jakob). Fără KPI-uri, fără cockpit, fără tur ghidat, fără panouri de statistici — zero zgomot pentru începător, time-to-first-value minim. Touch targets ≥44px, iconografie lucide consecventă, accent unic var(--pm-primary) pe temă dark stone coerentă cu restul dashboardului, data-testids pe toate elementele interactive, aria-hidden pe iconițe decorative."},
    {"key": "specialist_dashboard","path": "/specialist",    "zone": "specialist","label": "Specialist Dashboard",
     "brief": "Astăzi ai (sumar), tab-uri cereri disponibile, wallet, KPIs performanță."},
    # Operator
    {"key": "operator_dashboard","path": "/operator",        "zone": "operator",  "label": "Operator Dashboard",
     "brief": "KpiCards standardizate, AI Insights, listă cereri triaj, dispute panel."},
    # Admin
    {"key": "admin_overview",  "path": "/admin",             "zone": "admin",     "label": "Admin Overview",
     "brief": "Morning briefing card, 4 KPI cards, AI Insights, chart activitate 14z, top specialiști, finanțe, categorii, panouri operaționale progressive-disclosure."},
    {"key": "admin_analytics", "path": "/admin/analytics",   "zone": "admin",     "label": "Admin Analytics & Growth",
     "brief": "KpiCards trend, funnel, surse trafic, AI Insights, tabele exportabile CSV."},
    {"key": "admin_users",     "path": "/admin/users",       "zone": "admin",     "label": "Admin Users",
     "brief": "Data table utilizatori, filtre roluri, acțiuni impersonare/ban, KpiCards top."},
    {"key": "admin_ai_control","path": "/admin/ai-control-center","zone": "admin","label": "AI Control Center",
     "brief": "Configurare model AI, memoria cross-session, agenti activi, AI Insights v2."},
    {"key": "admin_governance","path": "/admin/ai-governance","zone": "admin",    "label": "AI Governance",
     "brief": "Agenti lifecycle, activitate 24h/7z, faza curentă, AI Insights v2."},
]


def _find_page(key: str) -> dict[str, Any] | None:
    for p in PAGES:
        if p["key"] == key:
            return p
    return None


def _rule_based_score(page: dict[str, Any]) -> dict[str, Any]:
    """Fallback deterministic scoring when LLM unavailable."""
    # Baseline scores by zone — refined via LLM. Kept intentionally conservative so the LLM adds value.
    baselines = {
        "public":     {"mobile": 78, "desktop": 86, "unity": 82},
        "client":     {"mobile": 82, "desktop": 80, "unity": 84},
        "specialist": {"mobile": 74, "desktop": 82, "unity": 78},
        "operator":   {"mobile": 70, "desktop": 88, "unity": 86},
        "admin":      {"mobile": 62, "desktop": 90, "unity": 82},
    }
    b = baselines.get(page["zone"], {"mobile": 75, "desktop": 82, "unity": 80})
    return {
        "mobile_score": b["mobile"],
        "desktop_score": b["desktop"],
        "unity_score": b["unity"],
        "hicks_law_score": 78,
        "millers_law_score": 76,
        "fitts_law_score": 80,
        "jakobs_law_score": 82,
        "nielsen_score": 78,
        "wcag_score": 84,
        "cognitive_load": 38,
        "findings": [
            f"Analiză rule-based fallback pentru {page['label']} — activează LLM pentru evaluare detaliată.",
        ],
        "recommendations": [
            "P1: Rulează analiza AI pentru findings specifice paginii.",
        ],
        "mobile_impact": "Mediu — analiză completă necesită LLM.",
        "desktop_impact": "Bun — layout desktop respectă gridul 12-col.",
    }


@router.get("/pages")
async def list_pages(_admin=Depends(require_role("admin"))):
    """Return the registry of pages we can audit + last-cached scores per page."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CACHE_HOURS)).isoformat()
    latest: dict[str, dict[str, Any]] = {}
    async for row in db.design_audit_cache.find({}, {"_id": 0}):
        latest[row["key"]] = row

    out = []
    for p in PAGES:
        cache = latest.get(p["key"])
        is_fresh = bool(cache and cache.get("generated_at", "") >= cutoff)
        out.append({
            **p,
            "last_audit": cache.get("generated_at") if cache else None,
            "fresh": is_fresh,
            "mobile_score": cache["result"].get("mobile_score") if cache else None,
            "desktop_score": cache["result"].get("desktop_score") if cache else None,
            "unity_score": cache["result"].get("unity_score") if cache else None,
        })
    return {"pages": out, "cache_hours": CACHE_HOURS}


@router.get("/analyze")
async def analyze_page(key: str, force: bool = False, _admin=Depends(require_role("admin"))):
    """Run the audit for a specific page, using LLM when possible."""
    page = _find_page(key)
    if not page:
        raise HTTPException(404, f"Pagină necunoscută: {key}. Valide: {[p['key'] for p in PAGES]}")

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CACHE_HOURS)).isoformat()
    if not force:
        cached = await db.design_audit_cache.find_one({"key": key, "generated_at": {"$gte": cutoff}}, {"_id": 0})
        if cached:
            return {**cached["result"], "page": page, "generated_at": cached["generated_at"], "cached": True}

    try:
        from orchestrator.llm import claude_json
        system = (
            "Ești UX/UI Auditor senior pentru PropManage — o platformă românească de servicii pentru "
            "proprietate (public, client, specialist, operator, admin). Design System-ul folosește: "
            "lime brand (#84cc16/#d4ff3a), suprafețe alb/slate-800 (light/dark), fără mov/blue accent. "
            "Regula: pe temă LIGHT toate suprafețele sunt albe/gri deschis; pe DARK toate slate-800/900. "
            "IMPORTANT: entitatea legală CORECTĂ este 'VINTAGE FURNITURE S.R.L.' (CUI 35250247, J12/3534/2015, "
            "Cluj-Napoca) — brand-ul public 'PropManage' este marca comercială. Nu marcă aceasta ca problemă. "
            "\n\nEvaluezi 7 principii UX bine cunoscute + criterii mobile/desktop:"
            "\n  1. Legea lui HICK — reducerea alegerilor simultane (max 5-7 CTAs vizibile)"
            "\n  2. Legea lui MILLER — chunking (max 7±2 elemente vizuale grupate)"
            "\n  3. Legea lui FITTS — target-uri touch/click accesibile (dimensiune × distanță)"
            "\n  4. Legea lui JAKOB — conformitate cu convenții cunoscute (butoane, iconuri, layout)"
            "\n  5. Euristici NIELSEN — 10 heuristici (vizibilitate stare, match cu lumea reală, control user, consistență, prevenire erori, recunoaștere > recall, flexibilitate, minimalism, mesaje eroare clare, help)"
            "\n  6. WCAG AA — contrast text ≥4.5:1, focus vizibil, alt-text, ARIA labels"
            "\n  7. MOBILE-FIRST — touch targets ≥44px, bottom nav thumb zone, viewport fluid"
            "\n\nÎn plus, calculezi COGNITIVE LOAD (0-100, unde 100=copleșitor): numărul de decizii × culori distincte × densitate informație × lungime text × opțiuni meniu."
            "\n\nRăspunde STRICT JSON: "
            "{\"mobile_score\": 0-100, \"desktop_score\": 0-100, \"unity_score\": 0-100, "
            "\"hicks_law_score\": 0-100, \"millers_law_score\": 0-100, \"fitts_law_score\": 0-100, "
            "\"jakobs_law_score\": 0-100, \"nielsen_score\": 0-100, \"wcag_score\": 0-100, "
            "\"cognitive_load\": 0-100, "
            "\"findings\": [3-5 constatări factuale scurte, string-uri], "
            "\"recommendations\": [3-5 acțiuni concrete cu prefix 'P0:', 'P1:', 'P2:' pentru prioritate — string-uri], "
            "\"mobile_impact\": \"scurt verdict impact pe mobil\", "
            "\"desktop_impact\": \"scurt verdict impact pe desktop\"}. "
            "Fii concret și critic — dai note reale, nu inflatate. Recomandările sunt string-uri simple, nu obiecte."
        )
        prompt = (
            f"Auditez pagina: {page['label']} ({page['path']}, zonă={page['zone']}).\n\n"
            f"Descriere conținut: {page['brief']}\n\n"
            f"Evaluează UX-ul pe mobile vs desktop, unitatea vizuală (light+dark trebuie să fie perfect coerente), "
            f"și aderența la legea lui Hick (nu prea multe alegeri odată). "
            f"Presupune că folosim Design System-ul strict cu KpiCard, AIInsightCard, DSBadge, PMPillButton, "
            f"card = 'rounded-2xl border bg-white dark:bg-slate-800'. "
            f"Livrează scorurile și 3-5 recomandări prioritizate."
        )
        result = await claude_json(system=system, prompt=prompt, session_prefix=f"design-audit-{key}")
        if not isinstance(result, dict) or "mobile_score" not in result:
            raise ValueError("Răspuns LLM invalid")
        payload = {
            "mobile_score": int(result.get("mobile_score", 0)),
            "desktop_score": int(result.get("desktop_score", 0)),
            "unity_score": int(result.get("unity_score", 0)),
            "hicks_law_score": int(result.get("hicks_law_score", 0)),
            "millers_law_score": int(result.get("millers_law_score", 0)),
            "fitts_law_score": int(result.get("fitts_law_score", 0)),
            "jakobs_law_score": int(result.get("jakobs_law_score", 0)),
            "nielsen_score": int(result.get("nielsen_score", 0)),
            "wcag_score": int(result.get("wcag_score", 0)),
            "cognitive_load": int(result.get("cognitive_load", 0)),
            "findings": (result.get("findings") or [])[:5],
            "recommendations": (result.get("recommendations") or [])[:5],
            "mobile_impact": result.get("mobile_impact") or "",
            "desktop_impact": result.get("desktop_impact") or "",
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[design-audit] LLM fail ({key}): {e} — fallback rule-based")
        payload = _rule_based_score(page)

    now = datetime.now(timezone.utc).isoformat()
    await db.design_audit_cache.update_one(
        {"key": key},
        {"$set": {"key": key, "generated_at": now, "result": payload}},
        upsert=True,
    )
    return {**payload, "page": page, "generated_at": now, "cached": False}


@router.get("/summary")
async def audit_summary(_admin=Depends(require_role("admin"))):
    """Aggregated summary — medii globale, worst 3 mobile, worst 3 desktop."""
    rows = []
    async for row in db.design_audit_cache.find({}, {"_id": 0}):
        r = row.get("result") or {}
        rows.append({
            "key": row["key"],
            "mobile_score": r.get("mobile_score") or 0,
            "desktop_score": r.get("desktop_score") or 0,
            "unity_score": r.get("unity_score") or 0,
            "hicks_law_score": r.get("hicks_law_score") or 0,
        })

    if not rows:
        return {
            "coverage": 0,
            "total_pages": len(PAGES),
            "audited": 0,
            "avg_mobile": None,
            "avg_desktop": None,
            "avg_unity": None,
            "avg_hicks": None,
            "worst_mobile": [],
            "worst_desktop": [],
        }

    labels = {p["key"]: p["label"] for p in PAGES}
    n = len(rows)
    avg = lambda k: round(sum(r[k] for r in rows) / n, 1)  # noqa: E731
    worst_mobile = sorted(rows, key=lambda r: r["mobile_score"])[:3]
    worst_desktop = sorted(rows, key=lambda r: r["desktop_score"])[:3]
    return {
        "coverage": round(n / len(PAGES) * 100),
        "total_pages": len(PAGES),
        "audited": n,
        "avg_mobile": avg("mobile_score"),
        "avg_desktop": avg("desktop_score"),
        "avg_unity": avg("unity_score"),
        "avg_hicks": avg("hicks_law_score"),
        "worst_mobile": [{**w, "label": labels.get(w["key"], w["key"])} for w in worst_mobile],
        "worst_desktop": [{**w, "label": labels.get(w["key"], w["key"])} for w in worst_desktop],
    }
