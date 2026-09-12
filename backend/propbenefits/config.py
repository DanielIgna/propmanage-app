"""PropBenefits · Config — totul configurabil de admin FĂRĂ cod (pb_config singleton)."""
from datetime import datetime, timezone

from db import db

CAMPAIGN_KINDS = ["active_benefit", "seasonal", "local", "city_partner", "digital_twin",
                  "audit", "house_health", "fair_price", "community", "referral"]
CAMPAIGN_STATUSES = ["draft", "preparing", "scheduled", "active", "ended"]

DEFAULT_CONFIG = {
    "_id": "pb_config",
    "levels": [
        {"key": "explorer", "name": "Explorer", "rank": 0, "min_points": 0,
         "perks": ["Acces la Beneficiile Active de bază"]},
        {"key": "bronze", "name": "Bronze", "rank": 1, "min_points": 20,
         "perks": ["Prioritate la campaniile locale"]},
        {"key": "silver", "name": "Silver", "rank": 2, "min_points": 40,
         "perks": ["Acces la campaniile sezoniere dedicate"]},
        {"key": "gold", "name": "Gold", "rank": 3, "min_points": 60,
         "perks": ["Prioritate la specialiștii de top", "Beneficii cu valoare mai mare"]},
        {"key": "verified", "name": "Verified", "rank": 4, "min_points": 80,
         "perks": ["Acces la campaniile exclusive Digital Twin"]},
        {"key": "elite", "name": "Elite", "rank": 5, "min_points": 95,
         "perks": ["Acces anticipat la orice campanie", "AI Success Manager prioritar"]},
    ],
    "level_points": {
        "subscription_active": 25, "digital_twin": 15, "documents_5plus": 10,
        "house_health": 10, "completed_jobs_3plus": 15, "referrals_2plus": 10,
        "account_90days": 5, "email_verified": 5, "experience_tier_verified": 5,
        "ambassador": 10,
    },
    "referral_benefit": {
        "enabled": True,
        "trigger": "subscription_or_first_paid_service",
        "inviter": {"benefit_key": "referral_inviter", "value_estimate": 25,
                    "title": "Beneficiu Comunitate: o lună House Health cadou la reînnoire"},
        "invitee": {"benefit_key": "referral_invitee", "value_estimate": 15,
                    "title": "Beneficiu de bun venit: verificare tehnică prioritară"},
        "expires_days": 90,
    },
    "subscription_health_weights": {
        "activity": 20, "documents": 15, "house_health": 15, "digital_twin": 10,
        "campaigns": 10, "benefits_used": 10, "referrals": 10, "ai_usage": 10,
    },
    "notifications": {"success_manager_enabled": True, "max_per_week": 2},
    "recommendation_reward": {
        "enabled": True, "expires_days": 90,
        "benefit": {"benefit_key": "recommendation_reward", "value_estimate": 20,
                    "title": "Beneficiu Comunitate: recomandarea ta a produs o lucrare confirmată"},
    },
    "ambassador": {
        "min_validated": 2, "badge": "Community Ambassador",
        "perks": ["Prioritate la campaniile exclusive", "Acces anticipat la Community Deals",
                  "Puncte de membru suplimentare"],
        "benefit": {"benefit_key": "ambassador_welcome", "value_estimate": 40,
                    "title": "Beneficiu Ambassador: evaluare House Health prioritară pentru casa ta"},
    },
    "ecosystem_targets": {"subscriptions": 100, "twins": 100, "hh_subs": 50,
                          "campaigns_active": 5, "specialists_active": 25,
                          "city_partners": 5, "retention_pct": 60},
    # SH-001 · House Journey & Readiness — praguri configurabile din Admin, zero hardcodare
    "journey": {
        "doc_verified_min_completeness": 60,
        "doc_verified_required_categories": ["act_proprietate", "cadastru", "certificat_energetic"],
        "book_started_min_docs": 1,
        "readiness_weights": {"administrare": 20, "mentenanta": 20, "audit": 20,
                              "finantare": 20, "vanzare": 20},
    },
    # UX-001 · Emotional Engagement — totul configurabil, zero hardcodare
    "engagement": {
        "enabled": True,
        "animations_enabled": True,
        "readiness_celebration_min_delta": 5,
        "milestones": [10, 25, 50, 75, 90, 100],
        "milestone_messages": {
            "10": "Primii pași sunt făcuți — casa ta începe să prindă contur digital.",
            "25": "Un sfert din drum — fundația documentară a casei e pusă.",
            "50": "Jumătate de drum — casa ta e mai pregătită decât majoritatea.",
            "75": "Aproape acolo — documentația casei devine solidă.",
            "90": "Ultimii pași — casa ta e aproape complet pregătită.",
            "100": "Casa ta este complet documentată și pregătită. Felicitări!",
        },
        "level_messages": {
            "2": "Ai început Cartea Casei.",
            "3": "Digital Twin este în dezvoltare.",
            "4": "House Health este activ.",
            "5": "Documentația casei este solidă.",
            "6": "Proprietatea este pregătită pentru verificare.",
            "7": "Proprietatea poate fi publicată prin PropManage.",
        },
        "level_unlocks": {
            "3": "Digital Twin", "4": "House Health", "5": "Consultanță Design Interior",
            "6": "Imobil Verificat", "7": "Publicare prin PropManage",
        },
        "badges": [
            {"id": "first_document", "icon": "📄", "label": "Primul document încărcat", "enabled": True,
             "why": "Ai încărcat primul document în Cartea Casei.",
             "meaning": "Memoria permanentă a casei tale a început să se construiască.",
             "benefit": "Deschide accesul la beneficiile care cer documentație.",
             "next": "Adaugă actul de proprietate și cadastrul."},
            {"id": "first_request", "icon": "📨", "label": "Prima cerere de ofertă", "enabled": True,
             "why": "Ai trimis prima cerere către specialiștii verificați.",
             "meaning": "Casa ta are acces la piața de servicii de încredere.",
             "benefit": "Ofertele primite rămân în istoricul casei.",
             "next": "Confirmă prima lucrare pentru a porni istoricul de mentenanță."},
            {"id": "first_work", "icon": "🔧", "label": "Prima lucrare documentată", "enabled": True,
             "why": "Prima lucrare a fost confirmată prin platformă.",
             "meaning": "Istoricul de mentenanță al casei a început.",
             "benefit": "Crește House Readiness la dimensiunea Mentenanță.",
             "next": "Ține jurnalul de mentenanță la zi."},
            {"id": "twin_active", "icon": "🧊", "label": "Digital Twin activ", "enabled": True,
             "why": "Modelul digital al casei este încărcat.",
             "meaning": "Casa ta poate fi vizualizată și documentată în 3D.",
             "benefit": "Acces la campaniile premium Digital Twin.",
             "next": "Adaugă planurile 2D pentru un geamăn complet."},
            {"id": "house_health_active", "icon": "❤️", "label": "House Health activ", "enabled": True,
             "why": "Scorul de sănătate al casei a fost generat.",
             "meaning": "Știi exact ce merită îngrijit primul în casa ta.",
             "benefit": "5 GB stocare + verificări din campaniile active.",
             "next": "Urmărește recomandările de îngrijire ale casei."},
            {"id": "doc_verified", "icon": "🛡", "label": "Documentație verificată", "enabled": True,
             "why": "Documentele obligatorii (act de proprietate, cadastru/CF, certificat energetic) sunt complete, iar Cartea Casei a atins pragul de completitudine.",
             "meaning": "NU înseamnă că imobilul este perfect — înseamnă că documentația este verificată și transparentă.",
             "benefit": "Reutilizat de FairPrice, Imobile Verificate, Marketplace și AI.",
             "next": "Pornește verificarea prin Imobile Verificate."},
            {"id": "community_ambassador", "icon": "🏅", "label": "Community Ambassador", "enabled": True,
             "why": "Recomandările tale confirmate au construit încrederea comunității.",
             "meaning": "Ești o voce de încredere a comunității PropManage.",
             "benefit": "Beneficiu de ambasador + prioritate la campaniile exclusive.",
             "next": "Continuă să recomanzi specialiștii care merită."},
            {"id": "founding_ambassador", "icon": "🏆", "label": "Founding Ambassador", "enabled": True,
             "why": "Ești printre primii 10 membri care au construit încrederea comunității.",
             "meaning": "Badge unic și permanent — locurile s-au închis definitiv.",
             "benefit": "Statut fondator vizibil în profil și comunitate.",
             "next": "Comunitatea crește pe fundația pusă de tine."},
            {"id": "imobil_verificat", "icon": "✅", "label": "Imobil Verificat", "enabled": True,
             "why": "Informațiile și documentele proprietății au fost verificate de PropManage.",
             "meaning": "Autenticitate și transparență certificate — nivelul proprietății ți-l asumi tu.",
             "benefit": "Încredere maximă pentru cumpărători și parteneri.",
             "next": "Publică proprietatea prin PropManage."},
            {"id": "casa_publicata", "icon": "🏡", "label": "Proprietate publicată prin PropManage", "enabled": True,
             "why": "Anunțul proprietății este publicat în Imobile Verificate.",
             "meaning": "Achievement-ul final al ecosistemului PropManage.",
             "benefit": "Vizibilitate cu certificare de transparență.",
             "next": "FairPrice îți va evalua inteligent proprietatea."},
        ],
    },
}

SEED_CAMPAIGNS = [
    {"id": "pbcamp_hh_check", "title": "Verificare centrală gratuită",
     "description": "Beneficiu Activ pentru membrii cu abonament: o verificare a centralei termice inclusă, realizată de un specialist verificat.",
     "kind": "house_health", "status": "active", "priority": 4,
     "budget_total": 500, "max_claims": 20, "max_per_user": 1,
     "eligibility": {"subscription_active": True},
     "estimated_impact": {"activation": 7, "retention": 9, "conversion": 5},
     "benefit": {"benefit_key": "hh_boiler_check", "title": "Verificare centrală gratuită",
                 "value_estimate": 25, "expires_days": 60,
                 "instructions": "Programează verificarea din Calendarul de mentenanță — specialistul vine gratuit."}},
    {"id": "pbcamp_twin_audit", "title": "Audit Digital Twin cu beneficiu de membru -70%",
     "description": "Oportunitate exclusivă: audit tehnic complet al locuinței cu acoperire de 70% din valoare pentru membrii cu Digital Twin activ.",
     "kind": "audit", "status": "active", "priority": 5,
     "budget_total": 1000, "max_claims": 10, "max_per_user": 1,
     "eligibility": {"has_digital_twin": True},
     "estimated_impact": {"activation": 8, "retention": 8, "conversion": 7},
     "benefit": {"benefit_key": "twin_audit_70", "title": "Audit Digital Twin acoperit 70%",
                 "value_estimate": 100, "expires_days": 45,
                 "instructions": "Auditul se programează cu un specialist certificat PropManage."}},
    {"id": "pbcamp_design_consult", "title": "Consultanță Design Interior",
     "description": "Beneficiu sezonier: o sesiune de consultanță de design interior pentru proprietarii cu Cartea Casei începută.",
     "kind": "seasonal", "status": "active", "priority": 3,
     "budget_total": 300, "max_claims": 15, "max_per_user": 1,
     "eligibility": {"min_documents": 1},
     "estimated_impact": {"activation": 5, "retention": 6, "conversion": 6},
     "benefit": {"benefit_key": "design_consult", "title": "Sesiune consultanță design interior",
                 "value_estimate": 20, "expires_days": 60,
                 "instructions": "Sesiunea se ține online cu un designer partener."}},
    {"id": "pbcamp_community_ref", "title": "Beneficiu Comunitate — adu un vecin",
     "description": "Când vecinul invitat de tine își activează abonamentul sau primul serviciu plătit, amândoi primiți un beneficiu de comunitate.",
     "kind": "community", "status": "active", "priority": 4,
     "budget_total": 0, "max_claims": 0, "max_per_user": 0,
     "eligibility": {},
     "estimated_impact": {"activation": 6, "retention": 7, "conversion": 9},
     "benefit": {"benefit_key": "referral_inviter", "title": "Beneficiu Comunitate",
                 "value_estimate": 25, "expires_days": 90,
                 "instructions": "Se acordă automat la activarea vecinului — trimite invitația din Setări → Invită și câștigă."}},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_config() -> dict:
    doc = await db.pb_config.find_one({"_id": "pb_config"})
    if not doc:
        doc = {**DEFAULT_CONFIG, "updated_at": _now()}
        await db.pb_config.insert_one(doc)
    # cheile noi din DEFAULT se completează automat pe config-urile existente
    missing = {k: v for k, v in DEFAULT_CONFIG.items() if k not in doc}
    if missing:
        await db.pb_config.update_one({"_id": "pb_config"}, {"$set": missing})
        doc.update(missing)
    return doc


async def update_config(patch: dict, updated_by: str) -> dict:
    allowed = {"levels", "level_points", "referral_benefit", "subscription_health_weights",
               "notifications", "ecosystem_targets", "recommendation_reward", "ambassador", "journey",
               "engagement"}
    clean = {k: v for k, v in patch.items() if k in allowed}
    if not clean:
        raise ValueError("Nicio cheie validă de configurare.")
    if "levels" in clean:
        if not isinstance(clean["levels"], list) or len(clean["levels"]) < 2:
            raise ValueError("levels trebuie să fie o listă cu minimum 2 niveluri.")
        for lv in clean["levels"]:
            if not all(k in lv for k in ("key", "name", "rank", "min_points")):
                raise ValueError("Fiecare nivel necesită key, name, rank, min_points.")
    clean["updated_at"] = _now()
    clean["updated_by"] = updated_by
    await db.pb_config.update_one({"_id": "pb_config"}, {"$set": clean}, upsert=True)
    return await get_config()


async def ensure_seed():
    await get_config()
    for c in SEED_CAMPAIGNS:
        exists = await db.pb_campaigns.find_one({"id": c["id"]}, {"_id": 1})
        if not exists:
            await db.pb_campaigns.insert_one({**c, "budget_used": 0, "claims_count": 0,
                                              "city": c.get("city"), "starts_at": None, "ends_at": None,
                                              "created_by": "seed", "created_at": _now(), "updated_at": _now()})
