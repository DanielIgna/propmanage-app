"""Enterprise Health Engine (Directiva 122) + Formula Registry (Directiva 151).

Scorul de sănătate al întregii companii — 11 domenii strategice, calculat DOAR din
dovezi măsurabile din platformă. Fiecare formulă este înregistrată, versionată,
configurabilă și complet explicabilă (fără formule hardcodate ascunse).
Alert Engine: domeniu sub prag → cauză + impact + top 3 acțiuni + efect estimat.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException

from db import db
from deps import require_role

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/enterprise-health", tags=["enterprise-health"])

BANDS = [
    (95, "world_class", "World Class", "#4ade80"),
    (90, "excellent", "Excellent", "#86efac"),
    (80, "healthy", "Healthy", "#d4ff3a"),
    (70, "needs_attention", "Needs Attention", "#fbbf24"),
    (60, "at_risk", "At Risk", "#fb923c"),
    (0, "critical", "Critical", "#f87171"),
]


def _band(score: float) -> dict:
    for mn, key, label, color in BANDS:
        if score >= mn:
            return {"key": key, "label": label, "color": color}
    return {"key": "critical", "label": "Critical", "color": "#f87171"}


def _clamp(v: float) -> float:
    return round(max(0, min(100, v)), 1)


DOMAIN_LABELS = {
    "product": "Product", "ux": "UX", "operations": "Operations", "growth": "Growth",
    "marketplace": "Marketplace", "customer_trust": "Customer Trust", "knowledge": "Knowledge",
    "revenue": "Revenue", "automation": "Automation", "technical_debt": "Technical Debt",
    "ai_learning": "AI Learning",
}

DEFAULT_FORMULAS = {
    "product": {
        "name": "Product Health",
        "description": "Adopția și completitudinea Digital Twin / Property Intelligence.",
        "business_objective": "Fiecare proprietate să aibă identitate digitală completă (Genome).",
        "formula": "medie ponderată: health_coverage×w + dna_coverage×w + twin_adoption×w",
        "inputs": [
            {"metric": "health_coverage", "label": "% proprietăți cu Health Score", "source": "properties.health_score", "weight": 0.4, "target": 90},
            {"metric": "dna_coverage", "label": "% proprietăți cu DNA v2", "source": "properties.dna_attributes", "weight": 0.3, "target": 90},
            {"metric": "twin_adoption", "label": "% proprietăți cu Twin deblocat", "source": "properties.twin_unlocked", "weight": 0.3, "target": 90},
        ],
    },
    "ux": {
        "name": "UX Health",
        "description": "Calitatea experienței pe paginile publice (Design Audit real).",
        "business_objective": "Effortless decision making pe fiecare pagină (D115).",
        "formula": "medie ponderată: design_audit_avg×w + audit_coverage×w",
        "inputs": [
            {"metric": "design_audit_avg", "label": "Scor mediu Design Audit (mobil+desktop)", "source": "design_audit_cache", "weight": 0.7, "target": 90},
            {"metric": "audit_coverage", "label": "% pagini publice auditate", "source": "design_audit_cache", "weight": 0.3, "target": 100},
        ],
    },
    "operations": {
        "name": "Operations Health",
        "description": "Viteza de execuție operațională: leads contactate, gaps, comenzi urmărite.",
        "business_objective": "Nimic nu intră fără owner, nimic nu iese fără rezultat.",
        "formula": "medie ponderată: leads_contact_rate×w + gap_pressure×w + orders_followup×w",
        "inputs": [
            {"metric": "leads_contact_rate", "label": "% leads deschise contactate (non-NEW)", "source": "leads.stage", "weight": 0.4, "target": 90},
            {"metric": "gap_pressure", "label": "% cereri deschise CU specialist", "source": "specialist_gaps + requests", "weight": 0.3, "target": 90},
            {"metric": "orders_followup", "label": "Comenzi pending neurmărite (penalizare)", "source": "verified_estate_orders", "weight": 0.3, "target": 95},
        ],
    },
    "growth": {
        "name": "Growth Health",
        "description": "Creșterea leads 30z vs 30z anterioare + captură emailuri (Mission 100).",
        "business_objective": "Mission 100: 100 vizitatori, 100 emailuri, 50 leads calificate.",
        "formula": "medie ponderată: lead_growth×w + email_capture×w",
        "inputs": [
            {"metric": "lead_growth", "label": "Creștere leads 30z vs anterior (60+Δ%×0.8)", "source": "leads.created_at", "weight": 0.6, "target": 85},
            {"metric": "email_capture", "label": "Emailuri capturate 30z vs țintă 100", "source": "lead_magnet_leads", "weight": 0.4, "target": 90},
        ],
    },
    "marketplace": {
        "name": "Marketplace Health",
        "description": "Echilibrul cerere-ofertă: fill rate + specialiști verificați.",
        "business_objective": "Fiecare cerere primește specialist rapid (D119).",
        "formula": "medie ponderată: fill_rate×w + verified_rate×w",
        "inputs": [
            {"metric": "fill_rate", "label": "% cereri cu specialist alocat", "source": "requests.specialist_id", "weight": 0.6, "target": 90},
            {"metric": "verified_rate", "label": "% specialiști verificați", "source": "users(role=specialist).verified", "weight": 0.4, "target": 80},
        ],
    },
    "customer_trust": {
        "name": "Customer Trust",
        "description": "Rating mediu, rata de rezolvare a disputelor, prospețimea recenziilor.",
        "business_objective": "Încrederea = capitalul strategic principal (D143).",
        "formula": "medie ponderată: avg_rating×w + dispute_resolution×w + review_freshness×w",
        "inputs": [
            {"metric": "avg_rating", "label": "Rating mediu recenzii (din 5)", "source": "reviews.rating", "weight": 0.5, "target": 95},
            {"metric": "dispute_resolution", "label": "% dispute rezolvate", "source": "disputes.status", "weight": 0.3, "target": 90},
            {"metric": "review_freshness", "label": "Recenzii primite în ultimele 30z", "source": "reviews.created_at", "weight": 0.2, "target": 100},
        ],
    },
    "knowledge": {
        "name": "Knowledge Health",
        "description": "Creșterea memoriei companiei: documente AI, memorii, studii de caz.",
        "business_objective": "Knowledge compounds faster than features (D114).",
        "formula": "medie ponderată: ai_documents×w + ai_memories×w + case_studies×w",
        "inputs": [
            {"metric": "ai_documents", "label": "Documente AI indexate vs țintă 50", "source": "ai_documents", "weight": 0.4, "target": 80},
            {"metric": "ai_memories", "label": "Memorii AI vs țintă 20", "source": "ai_memories", "weight": 0.3, "target": 80},
            {"metric": "case_studies", "label": "Studii de caz (Case Library D112) vs țintă 10", "source": "case_library", "weight": 0.3, "target": 80},
        ],
    },
    "revenue": {
        "name": "Revenue Health",
        "description": "Venit REAL încasat (comenzi plătite + plăți manuale VERIFIED) vs țintă lunară.",
        "business_objective": "First Revenue → venit recurent (Mission 100).",
        "formula": "medie ponderată: real_revenue×w + paying_customers×w",
        "inputs": [
            {"metric": "real_revenue", "label": "Venit real încasat vs țintă 5000 RON", "source": "verified_estate_orders(paid) + manual_payments", "weight": 0.7, "target": 80},
            {"metric": "paying_customers", "label": "Clienți plătitori vs țintă 10", "source": "orders + manual_payments", "weight": 0.3, "target": 80},
        ],
    },
    "automation": {
        "name": "Automation Health",
        "description": "Nivelul de autonomie al platformei (snapshot Autonomy Engine).",
        "business_objective": ">90% platform autonomy (mandat comercial).",
        "formula": "medie ponderată: autonomy_general×w + autonomy_operational×w",
        "inputs": [
            {"metric": "autonomy_general", "label": "Scor autonomie generală", "source": "autonomy_snapshots.scores.general", "weight": 0.7, "target": 90},
            {"metric": "autonomy_operational", "label": "Scor autonomie operațională", "source": "autonomy_snapshots.scores.operational", "weight": 0.3, "target": 90},
        ],
    },
    "technical_debt": {
        "name": "Technical Debt",
        "description": "Sănătatea tehnică: rata de succes smoke tests + AI health scan.",
        "business_objective": "Zero regresii — stabilitate înainte de scalare.",
        "formula": "medie ponderată: smoke_pass_rate×w + ai_health_scan×w",
        "inputs": [
            {"metric": "smoke_pass_rate", "label": "% smoke tests trecute (ultimele 20 rulări)", "source": "smoke_test_runs", "weight": 0.7, "target": 98},
            {"metric": "ai_health_scan", "label": "Scor AI health scan (ultimul)", "source": "admin_ai_health_history", "weight": 0.3, "target": 90},
        ],
    },
    "ai_learning": {
        "name": "AI Learning",
        "description": "Cât învață platforma: outcomes urmărite, volum decizii, scor AI.",
        "business_objective": "AI măsurat prin calitatea deciziilor, nu volum (D118).",
        "formula": "medie ponderată: outcomes_tracked×w + decision_volume×w + autonomy_ai×w",
        "inputs": [
            {"metric": "outcomes_tracked", "label": "% outcomes AI cu rezultat urmărit", "source": "ai_outcomes.kind", "weight": 0.5, "target": 80},
            {"metric": "decision_volume", "label": "Decizii în ledger vs țintă 20", "source": "ai_decision_ledger", "weight": 0.3, "target": 80},
            {"metric": "autonomy_ai", "label": "Scor AI din Autonomy Engine", "source": "autonomy_snapshots.scores.ai", "weight": 0.2, "target": 85},
        ],
    },
}

DOMAIN_IMPACT = {
    "product": "Proprietăți fără identitate digitală completă = valoare percepută mică a Twin-ului → conversie slabă la pachetele plătite.",
    "ux": "Pagini cu scor UX slab pierd vizitatori înainte de conversie → leads mai puține cu același trafic.",
    "operations": "Leads necontactate și cereri fără specialist = venit pierdut direct și încredere erodată.",
    "growth": "Fără creștere de leads, Mission 100 stagnează → pipeline-ul de venit rămâne gol.",
    "marketplace": "Cereri neonorate = clienți care pleacă la concurență și recenzii negative.",
    "customer_trust": "Încrederea scăzută blochează referrals și recenziile — cel mai ieftin canal de creștere.",
    "knowledge": "Fără memorie a companiei, fiecare proiect pornește de la zero — costuri repetate (D112/D114).",
    "revenue": "Venit real sub țintă = pistă financiară scurtă; prioritatea #1 comercială.",
    "automation": "Autonomie scăzută = timpul Founder-ului consumat pe operațiuni în loc de strategie.",
    "technical_debt": "Teste picate = risc de regresii în producție → încredere și venit pierdute.",
    "ai_learning": "AI care nu învață din rezultate repetă recomandări slabe (D124).",
}

METRIC_ACTIONS = {
    "health_coverage": "Rulează scan Property Intelligence pe proprietățile fără Health Score.",
    "dna_coverage": "Completează atributele DNA v2 (an construcție, structură, izolație) din Cartea Casei.",
    "twin_adoption": "Promovează deblocarea Twin la proprietarii activi (CTA în dashboard client).",
    "design_audit_avg": "Aplică recomandările din Design Audit pe paginile cu scor mic.",
    "audit_coverage": "Rulează Design Audit pe toate paginile publice (landing, marketplace, prețuri, legal).",
    "leads_contact_rate": "Contactează leads din stage NEW azi — începe cu cel mai vechi (Operations Center).",
    "gap_pressure": "Alocă specialiști pe gaps din Gap Engine sau recrutează pe categoriile lipsă.",
    "orders_followup": "Urmărește comenzile pending — oferă plată manuală (transfer/cash) din Operations Center.",
    "lead_growth": "Distribuie calculatorul Scorul Casei într-un grup Facebook local (15 min).",
    "email_capture": "Publică lead magnets (Checklist cumpărare + Scorul Casei) pe canale noi.",
    "fill_rate": "Folosește Auto-Match sau alocarea manuală din Gap Engine pentru cererile deschise.",
    "verified_rate": "Verifică specialiștii în așteptare (documente + interviu scurt).",
    "avg_rating": "Rezolvă cauzele recenziilor slabe — analizează pattern-urile din Customer Voice.",
    "dispute_resolution": "Închide disputele deschise — fiecare dispută veche erodează încrederea.",
    "review_freshness": "Cere review de la ultimii clienți serviți (mesaj personal, nu automat).",
    "ai_documents": "Indexează documentele operaționale importante în AI Documents.",
    "ai_memories": "Salvează lecțiile din decizii importante în AI Memories (D132).",
    "case_studies": "Transformă fiecare proiect finalizat în studiu de caz (Case Library D112).",
    "real_revenue": "Concentrează-te pe comenzi plătibile ACUM: audituri + plăți manuale până la Stripe LIVE.",
    "paying_customers": "Convertește leads hot în clienți plătitori — ofertă directă cu deadline.",
    "autonomy_general": "Rulează Autonomy Auto-Tune și rezolvă alertele de autonomie active.",
    "autonomy_operational": "Automatizează pașii manuali detectați în Operations (D144).",
    "smoke_pass_rate": "Repară imediat pașii picați din ultimele smoke test runs.",
    "ai_health_scan": "Rulează AI health scan și aplică sugestiile de reparare.",
    "outcomes_tracked": "Înregistrează rezultatul real (venit/eșec) pentru fiecare recomandare AI aplicată.",
    "decision_volume": "Loghează deciziile importante în AI Decision Ledger pentru învățare.",
    "autonomy_ai": "Îmbunătățește feedback-ul către AI: outcomes + lessons learned.",
}


async def _get_formulas() -> dict:
    """Registry idempotent: seed defaults dacă lipsesc, returnează {key: doc}."""
    now = datetime.now(timezone.utc).isoformat()
    out = {}
    for key, spec in DEFAULT_FORMULAS.items():
        doc = await db.eh_formulas.find_one({"key": key})
        if not doc:
            doc = {
                "key": key, **spec, "normalization": "subscoruri 0-100, medie ponderată, clamp",
                "score_range": [0, 100], "target": 90, "warning_threshold": 80,
                "critical_threshold": 60, "version": 1, "author": "system",
                "status": "active", "versions": [], "created_at": now, "updated_at": now,
            }
            await db.eh_formulas.insert_one(doc)
        out[key] = doc
    return out


async def _collect_metrics() -> dict:
    """Toate metricile brute + subscoruri 0-100, calculate din date reale."""
    now = datetime.now(timezone.utc)
    d30 = (now - timedelta(days=30)).isoformat()
    d60 = (now - timedelta(days=60)).isoformat()
    m = {}

    def put(key, value, score, detail):
        m[key] = {"value": value, "score": _clamp(score), "detail": detail}

    # Product
    props = await db.properties.count_documents({})
    p_health = await db.properties.count_documents({"health_score": {"$exists": True}})
    p_dna = await db.properties.count_documents({"dna_attributes": {"$exists": True, "$ne": {}}})
    p_twin = await db.properties.count_documents({"twin_unlocked": True})
    put("health_coverage", f"{p_health}/{props}", (p_health / props * 100) if props else 0, f"{p_health} din {props} proprietăți au Health Score")
    put("dna_coverage", f"{p_dna}/{props}", (p_dna / props * 100) if props else 0, f"{p_dna} din {props} proprietăți au atribute DNA v2")
    put("twin_adoption", f"{p_twin}/{props}", (p_twin / props * 100) if props else 0, f"{p_twin} din {props} proprietăți au Twin deblocat")

    # UX
    ux_scores = []
    async for row in db.design_audit_cache.find({"key": {"$in": ["landing", "marketplace", "preturi", "legal"]}}):
        r = row.get("result") or {}
        if r.get("mobile_score"):
            ux_scores.append((r["mobile_score"] + r.get("desktop_score", 0)) / 2)
    put("design_audit_avg", round(sum(ux_scores) / len(ux_scores), 1) if ux_scores else None,
        (sum(ux_scores) / len(ux_scores)) if ux_scores else 50, f"{len(ux_scores)} pagini auditate, scor mediu {round(sum(ux_scores)/len(ux_scores),1) if ux_scores else '—'}")
    put("audit_coverage", f"{len(ux_scores)}/4", len(ux_scores) / 4 * 100, f"{len(ux_scores)} din 4 pagini publice cheie auditate")

    # Operations
    open_stages_ex = ("completed", "lost", "won")
    leads_open = await db.leads.count_documents({"stage": {"$nin": list(open_stages_ex)}})
    leads_new = await db.leads.count_documents({"stage": "new"})
    put("leads_contact_rate", f"{leads_open - leads_new}/{leads_open}",
        ((leads_open - leads_new) / leads_open * 100) if leads_open else 100,
        f"{leads_new} leads în stage NEW din {leads_open} deschise")
    open_req = await db.requests.count_documents({"status": {"$nin": ["completed", "cancelled", "closed", "rejected"]}})
    open_gaps = await db.specialist_gaps.count_documents({"status": "open"})
    put("gap_pressure", f"{open_gaps} gaps / {open_req} cereri",
        ((open_req - open_gaps) / open_req * 100) if open_req else 100,
        f"{open_gaps} cereri deschise fără specialist din {open_req}")
    pending_orders = await db.verified_estate_orders.count_documents({"status": "pending", "demo_mode": {"$ne": True}})
    put("orders_followup", pending_orders, 100 - pending_orders * 10, f"{pending_orders} comenzi reale în pending")

    # Growth
    l30 = await db.leads.count_documents({"created_at": {"$gte": d30}})
    lprev = await db.leads.count_documents({"created_at": {"$gte": d60, "$lt": d30}})
    growth = ((l30 - lprev) / lprev * 100) if lprev else (100 if l30 else 0)
    put("lead_growth", f"{l30} vs {lprev}", 60 + growth * 0.8, f"Leads 30z: {l30} vs {lprev} anterior ({growth:+.0f}%)")
    emails30 = await db.lead_magnet_leads.count_documents({"created_at": {"$gte": d30}})
    put("email_capture", f"{emails30}/100", emails30, f"{emails30} emailuri capturate în 30z (țintă 100)")

    # Marketplace
    total_req = await db.requests.count_documents({})
    filled = await db.requests.count_documents({"specialist_id": {"$nin": [None, ""]}})
    put("fill_rate", f"{filled}/{total_req}", (filled / total_req * 100) if total_req else 50, f"{filled} din {total_req} cereri au specialist")
    spec_total = await db.users.count_documents({"role": "specialist"})
    spec_ver = await db.users.count_documents({"role": "specialist", "verified": True})
    put("verified_rate", f"{spec_ver}/{spec_total}", (spec_ver / spec_total * 100) if spec_total else 50, f"{spec_ver} din {spec_total} specialiști verificați")

    # Customer Trust
    rat = await db.reviews.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$rating"}, "n": {"$sum": 1}}}]).to_list(1)
    avg_rating = rat[0]["avg"] if rat else None
    put("avg_rating", round(avg_rating, 2) if avg_rating else None, (avg_rating / 5 * 100) if avg_rating else 50,
        f"Rating mediu {round(avg_rating,2) if avg_rating else '—'} din {rat[0]['n'] if rat else 0} recenzii")
    disp_total = await db.disputes.count_documents({})
    disp_res = await db.disputes.count_documents({"status": {"$in": ["resolved", "closed"]}})
    put("dispute_resolution", f"{disp_res}/{disp_total}", (disp_res / disp_total * 100) if disp_total else 95, f"{disp_res} din {disp_total} dispute rezolvate")
    rev30 = await db.reviews.count_documents({"created_at": {"$gte": d30}})
    put("review_freshness", rev30, 100 if rev30 > 0 else 40, f"{rev30} recenzii în ultimele 30 zile")

    # Knowledge
    n_docs = await db.ai_documents.count_documents({})
    n_mem = await db.ai_memories.count_documents({})
    n_cases = await db.case_library.count_documents({})
    put("ai_documents", n_docs, n_docs / 50 * 100, f"{n_docs} documente AI indexate (țintă 50)")
    put("ai_memories", n_mem, n_mem / 20 * 100, f"{n_mem} memorii AI (țintă 20)")
    put("case_studies", n_cases, n_cases / 10 * 100, f"{n_cases} studii de caz în Case Library (țintă 10)")

    # Revenue — doar bani REALI
    rev_total = 0.0
    payers = set()
    async for o in db.verified_estate_orders.find({"status": "paid", "demo_mode": {"$ne": True}}, {"amount_ron": 1, "contact_email": 1}):
        rev_total += float(o.get("amount_ron") or 0)
        if o.get("contact_email"):
            payers.add(o["contact_email"])
    async for p in db.manual_payments.find({"status": "verified"}, {"amount_ron": 1, "customer_email": 1, "customer_name": 1, "source": 1}):
        if p.get("source") != "verified_estate_order":
            rev_total += float(p.get("amount_ron") or 0)
        payers.add(p.get("customer_email") or p.get("customer_name") or "necunoscut")
    put("real_revenue", f"{rev_total:.0f} RON", rev_total / 5000 * 100, f"{rev_total:.0f} RON venit real încasat (țintă 5000 RON)")
    put("paying_customers", len(payers), len(payers) / 10 * 100, f"{len(payers)} clienți plătitori (țintă 10)")

    # Automation
    snap = await db.autonomy_snapshots.find_one({}, sort=[("_id", -1)])
    sc = (snap or {}).get("scores") or {}
    put("autonomy_general", sc.get("general"), sc.get("general") or 50, f"Autonomie generală: {sc.get('general', '—')} (tier: {(snap or {}).get('tier', '—')})")
    put("autonomy_operational", sc.get("operational"), sc.get("operational") or 50, f"Autonomie operațională: {sc.get('operational', '—')}")

    # Technical Debt
    runs = await db.smoke_test_runs.find({}, {"passed": 1, "total": 1}).sort("_id", -1).limit(20).to_list(20)
    tp = sum(r.get("passed", 0) for r in runs)
    tt = sum(r.get("total", 0) for r in runs)
    put("smoke_pass_rate", f"{tp}/{tt}", (tp / tt * 100) if tt else 75, f"{tp} din {tt} pași smoke test trecuți (ultimele {len(runs)} rulări)")
    ai_h = await db.admin_ai_health_history.find_one({}, sort=[("_id", -1)])
    ai_score = None
    if ai_h:
        ai_score = ai_h.get("score") or ai_h.get("health_score") or ai_h.get("overall")
    put("ai_health_scan", ai_score, ai_score if ai_score is not None else 75, f"Ultimul AI health scan: {ai_score if ai_score is not None else 'indisponibil'}")

    # AI Learning
    out_total = await db.ai_outcomes.count_documents({})
    out_tracked = await db.ai_outcomes.count_documents({"kind": {"$nin": [None, "untracked"]}})
    put("outcomes_tracked", f"{out_tracked}/{out_total}", (out_tracked / out_total * 100) if out_total else 30, f"{out_tracked} din {out_total} outcomes AI urmărite")
    n_ledger = await db.ai_decision_ledger.count_documents({})
    put("decision_volume", n_ledger, n_ledger / 20 * 100, f"{n_ledger} decizii în AI Decision Ledger (țintă 20)")
    put("autonomy_ai", sc.get("ai"), sc.get("ai") or 50, f"Scor AI Autonomy: {sc.get('ai', '—')}")

    return m


def _domain_result(formula: dict, metrics: dict) -> dict:
    inputs = formula.get("inputs") or []
    total_w = sum(i.get("weight", 0) for i in inputs) or 1
    steps, missing = [], 0
    score = 0.0
    for i in inputs:
        mk = i["metric"]
        mm = metrics.get(mk) or {"value": None, "score": 50, "detail": "date indisponibile"}
        if mm["value"] is None:
            missing += 1
        contrib = mm["score"] * i.get("weight", 0) / total_w
        score += contrib
        steps.append({
            "metric": mk, "label": i.get("label", mk), "source": i.get("source", ""),
            "value": mm["value"], "subscore": mm["score"], "weight": i.get("weight", 0),
            "contribution_pts": round(contrib, 1), "detail": mm["detail"], "target": i.get("target", 90),
        })
    positive = [s for s in steps if s["subscore"] >= 80]
    negative = sorted([s for s in steps if s["subscore"] < 80], key=lambda s: s["subscore"])
    confidence = "high" if missing == 0 else ("medium" if missing == 1 else "low")
    return {"score": _clamp(score), "steps": steps, "positive": positive, "negative": negative, "confidence": confidence}


def _build_alert(key: str, formula: dict, result: dict) -> dict:
    warn = formula.get("warning_threshold", 80)
    crit = formula.get("critical_threshold", 60)
    severity = "critical" if result["score"] < crit else "warning"
    negatives = result["negative"][:3] or sorted(result["steps"], key=lambda s: s["subscore"])[:2]
    cause = "; ".join(n["detail"] for n in negatives)
    total_w = sum(s["weight"] for s in result["steps"]) or 1
    actions, effect_pts = [], 0.0
    for n in negatives[:3]:
        act = METRIC_ACTIONS.get(n["metric"], f"Îmbunătățește: {n['label']}")
        gain = (n["target"] - n["subscore"]) * n["weight"] / total_w
        if gain > 0:
            effect_pts += gain
        actions.append({"action": act, "metric": n["label"], "estimated_gain_pts": round(max(0, gain), 1)})
    return {
        "domain": key, "label": DOMAIN_LABELS[key], "score": result["score"], "severity": severity,
        "cause": cause, "business_impact": DOMAIN_IMPACT.get(key, ""),
        "top_actions": actions,
        "estimated_effect": f"+{effect_pts:.1f} puncte {DOMAIN_LABELS[key]} dacă acțiunile sunt implementate",
    }


async def _history_context() -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d30 = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    hist = await db.enterprise_health_history.find({}).sort("date", -1).limit(60).to_list(60)
    previous = next((h for h in hist if h["date"] < today), None)
    old = next((h for h in reversed(hist) if h["date"] >= d30), None)
    series = [{"date": h["date"], "overall": h["overall"]} for h in reversed(hist)][-30:]
    return {"previous": previous, "old30": old, "series": series}


ES_WEIGHTS = {"customer_success": 0.20, "revenue": 0.15, "enterprise_health": 0.15,
              "trust": 0.10, "knowledge": 0.10, "automation": 0.10, "security": 0.05,
              "performance": 0.05, "marketplace_growth": 0.05, "innovation": 0.05}
ES_LABELS = {"customer_success": "Customer Success", "revenue": "Revenue",
             "enterprise_health": "Enterprise Health", "trust": "Trust", "knowledge": "Knowledge",
             "automation": "Automation", "security": "Security", "performance": "Performance",
             "marketplace_growth": "Marketplace Growth", "innovation": "Innovation"}


async def compute_enterprise_score(domain_scores: dict, overall: float) -> dict:
    """Enterprise Score (Operating Agreement) — ponderi Board, surse documentate transparent."""
    snap = await db.autonomy_snapshots.find_one({}, sort=[("_id", -1)])
    sc = (snap or {}).get("scores") or {}
    sources = {
        "customer_success": (domain_scores.get("customer_trust"), "Domeniul Customer Trust (rating, dispute, recenzii)"),
        "revenue": (domain_scores.get("revenue"), "Domeniul Revenue (venit real încasat)"),
        "enterprise_health": (overall, "Media celor 11 domenii de sănătate (D122)"),
        "trust": (domain_scores.get("customer_trust"), "Customer Trust — sursă comună cu Customer Success (documentat)"),
        "knowledge": (domain_scores.get("knowledge"), "Domeniul Knowledge"),
        "automation": (domain_scores.get("automation"), "Domeniul Automation"),
        "security": (sc.get("security"), "Autonomy Engine · scores.security"),
        "performance": (sc.get("technical"), "Autonomy Engine · scores.technical"),
        "marketplace_growth": (domain_scores.get("marketplace"), "Domeniul Marketplace"),
        "innovation": (domain_scores.get("ai_learning"), "Domeniul AI Learning"),
    }
    components, total = [], 0.0
    for k, w in ES_WEIGHTS.items():
        val, source = sources[k]
        v = val if val is not None else 50
        total += v * w
        components.append({"key": k, "label": ES_LABELS[k], "weight": w, "value": round(v, 1),
                           "source": source, "contribution_pts": round(v * w, 1), "estimated": val is None})
    return {"score": _clamp(total), "band": _band(total), "components": components,
            "formula": "20% Customer Success + 15% Revenue + 15% Enterprise Health + 10% Trust + 10% Knowledge + 10% Automation + 5% Security + 5% Performance + 5% Marketplace + 5% Innovation"}


@router.get("")
async def enterprise_health(user=Depends(require_role("admin"))):
    formulas = await _get_formulas()
    metrics = await _collect_metrics()
    ctx = await _history_context()
    prev_scores = (ctx["previous"] or {}).get("scores", {})
    old_scores = (ctx["old30"] or {}).get("scores", {})

    domains, alerts, scores_map = [], [], {}
    for key in DOMAIN_LABELS:
        f = formulas[key]
        if f.get("status") != "active":
            continue
        res = _domain_result(f, metrics)
        scores_map[key] = res["score"]
        domains.append({
            "key": key, "label": DOMAIN_LABELS[key], "score": res["score"],
            "band": _band(res["score"]), "confidence": res["confidence"],
            "previous": prev_scores.get(key), "trend_30d": round(res["score"] - old_scores[key], 1) if key in old_scores else None,
            "warning_threshold": f.get("warning_threshold", 80),
            "top_findings": [s["detail"] for s in res["negative"][:3]] or [s["detail"] for s in res["steps"][:2]],
            "version": f.get("version", 1),
        })
        if res["score"] < f.get("warning_threshold", 80):
            alerts.append(_build_alert(key, f, res))

    overall = _clamp(sum(d["score"] for d in domains) / len(domains)) if domains else 0
    enterprise_score = await compute_enterprise_score(scores_map, overall)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not await db.enterprise_health_history.find_one({"date": today}):
        await db.enterprise_health_history.insert_one({
            "date": today, "overall": overall, "scores": scores_map,
            "enterprise_score": enterprise_score["score"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    return {
        "overall": {"score": overall, "band": _band(overall),
                    "previous": (ctx["previous"] or {}).get("overall"),
                    "trend_30d": round(overall - ctx["old30"]["overall"], 1) if ctx["old30"] else None},
        "enterprise_score": enterprise_score,
        "domains": sorted(domains, key=lambda d: d["score"]),
        "alerts": sorted(alerts, key=lambda a: a["score"]),
        "history": ctx["series"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/formulas")
async def list_formulas(user=Depends(require_role("admin"))):
    formulas = await _get_formulas()
    out = []
    for key, f in formulas.items():
        out.append({k: v for k, v in f.items() if k not in ("_id", "versions")} | {"versions_count": len(f.get("versions", []))})
    return {"formulas": out}


@router.get("/formulas/{key}/explain")
async def explain_formula(key: str, user=Depends(require_role("admin"))):
    formulas = await _get_formulas()
    f = formulas.get(key)
    if not f:
        raise HTTPException(404, "Formulă inexistentă")
    metrics = await _collect_metrics()
    res = _domain_result(f, metrics)
    ctx = await _history_context()
    return {
        "key": key, "label": DOMAIN_LABELS.get(key, key), "name": f.get("name"),
        "description": f.get("description"), "business_objective": f.get("business_objective"),
        "formula": f.get("formula"), "normalization": f.get("normalization"),
        "version": f.get("version"), "status": f.get("status"),
        "warning_threshold": f.get("warning_threshold"), "critical_threshold": f.get("critical_threshold"),
        "score": res["score"], "band": _band(res["score"]), "confidence": res["confidence"],
        "calculation_steps": res["steps"],
        "positive_contributors": [s["detail"] for s in res["positive"]],
        "negative_contributors": [s["detail"] for s in res["negative"]],
        "historical": [{"date": h["date"], "score": h["overall"]} for h in ctx["series"][-10:]],
    }


@router.patch("/formulas/{key}")
async def update_formula(key: str, payload: dict = Body(...), user=Depends(require_role("admin"))):
    f = await db.eh_formulas.find_one({"key": key})
    if not f:
        raise HTTPException(404, "Formulă inexistentă")
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "Motivul modificării este obligatoriu (audit D151)")

    updates, changes = {}, {}
    weights = payload.get("weights")
    if weights:
        valid_metrics = {i["metric"] for i in f.get("inputs", [])}
        new_inputs = []
        for i in f["inputs"]:
            w = weights.get(i["metric"], i["weight"])
            try:
                w = float(w)
            except (TypeError, ValueError):
                raise HTTPException(400, f"Pondere invalidă pentru {i['metric']}")
            if w < 0:
                raise HTTPException(400, "Ponderile trebuie să fie ≥ 0")
            new_inputs.append({**i, "weight": w})
        for mk in weights:
            if mk not in valid_metrics:
                raise HTTPException(400, f"Metrica {mk} nu există în formula {key}")
        if sum(i["weight"] for i in new_inputs) <= 0:
            raise HTTPException(400, "Suma ponderilor trebuie să fie > 0")
        updates["inputs"] = new_inputs
        changes["weights"] = weights
    for fld in ("warning_threshold", "critical_threshold", "target"):
        if payload.get(fld) is not None:
            v = float(payload[fld])
            if not 0 <= v <= 100:
                raise HTTPException(400, f"{fld} trebuie să fie între 0 și 100")
            updates[fld] = v
            changes[fld] = v
    wt = updates.get("warning_threshold", f.get("warning_threshold", 80))
    ct = updates.get("critical_threshold", f.get("critical_threshold", 60))
    if wt <= ct:
        raise HTTPException(400, "Pragul de warning trebuie să fie peste cel critic")
    if payload.get("status") in ("active", "disabled", "archived"):
        updates["status"] = payload["status"]
        changes["status"] = payload["status"]
    if not updates:
        raise HTTPException(400, "Nimic de modificat")

    now = datetime.now(timezone.utc).isoformat()
    prev_snapshot = {k: f.get(k) for k in ("inputs", "warning_threshold", "critical_threshold", "target", "status", "version")}
    new_version = f.get("version", 1) + 1
    await db.eh_formulas.update_one({"key": key}, {
        "$set": {**updates, "version": new_version, "updated_at": now, "author": user.get("email")},
        "$push": {"versions": {**prev_snapshot, "archived_at": now}},
    })
    await db.eh_formula_audit.insert_one({
        "key": key, "by": user.get("email"), "at": now, "reason": reason,
        "prev_version": f.get("version", 1), "new_version": new_version, "changes": changes,
    })
    return {"ok": True, "version": new_version}


@router.post("/formulas/{key}/rollback")
async def rollback_formula(key: str, payload: dict = Body(default={}), user=Depends(require_role("admin"))):
    f = await db.eh_formulas.find_one({"key": key})
    if not f:
        raise HTTPException(404, "Formulă inexistentă")
    versions = f.get("versions") or []
    if not versions:
        raise HTTPException(400, "Nu există versiuni anterioare")
    prev = versions[-1]
    now = datetime.now(timezone.utc).isoformat()
    new_version = f.get("version", 1) + 1
    restore = {k: prev[k] for k in ("inputs", "warning_threshold", "critical_threshold", "target", "status") if k in prev and prev[k] is not None}
    await db.eh_formulas.update_one({"key": key}, {
        "$set": {**restore, "version": new_version, "updated_at": now, "author": user.get("email")},
        "$pop": {"versions": 1},
    })
    await db.eh_formula_audit.insert_one({
        "key": key, "by": user.get("email"), "at": now,
        "reason": (payload.get("reason") or "rollback la versiunea anterioară"),
        "prev_version": f.get("version", 1), "new_version": new_version,
        "changes": {"rollback_to_version": prev.get("version")},
    })
    return {"ok": True, "version": new_version, "restored_version": prev.get("version")}


@router.get("/formulas/{key}/audit")
async def formula_audit(key: str, user=Depends(require_role("admin"))):
    logs = []
    async for a in db.eh_formula_audit.find({"key": key}).sort("at", -1).limit(50):
        logs.append({k: v for k, v in a.items() if k != "_id"})
    return {"audit": logs}
