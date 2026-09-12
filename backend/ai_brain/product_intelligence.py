"""AI Brain · Product Intelligence Engine (CORE-001).

Canonical Product Graph + Live Product Map: fiecare modul de produs este evaluat
pe dovezi reale din cod (fișiere, endpoint-uri, colecții, teste, feature checks).
Scoruri: Product Completeness Score (0-100, calculat) + Business Value Score
(0-100, ponderi declarate: venit 35% · conversie 25% · retenție 25% · costuri 15%).
Clasificare elemente: activ / experimental / duplicat / neconectat / depreciat /
candidat_reutilizare. Regula 60%: orice implementare nouă extinde existentul.
Snapshot-uri istorice în db.product_map_snapshots + MASTER DISCOVERY REPORT.
"""
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from db import db

APP = Path("/app")
FRONTEND_SRC = APP / "frontend" / "src"

BVS_WEIGHTS = {"revenue": 0.35, "conversion": 0.25, "retention": 0.25, "cost": 0.15}

MODULE_CATALOG = [
    {
        "key": "ai_brain", "name": "AI Brain", "status": "activ",
        "desc": "Ecosistemul de inteligență al platformei: Discovery, Context, Explainability, Mentor, Knowledge Graph, Process, Decision, Adaptive, Collaborative, Certification.",
        "backend": ["backend/ai_brain/core.py", "backend/ai_brain/discovery.py", "backend/ai_brain/graph.py",
                    "backend/ai_brain/process.py", "backend/ai_brain/decision.py", "backend/ai_brain/adaptive.py",
                    "backend/ai_brain/collaboration.py", "backend/ai_brain/certification.py", "backend/routes/ai_brain.py"],
        "frontend": ["frontend/src/pages/admin/AIBrainPage.jsx", "frontend/src/components/KnowledgeExplorer.jsx",
                     "frontend/src/components/ProcessExplorer.jsx", "frontend/src/components/DecisionExplorer.jsx",
                     "frontend/src/components/AdaptiveExplorer.jsx", "frontend/src/components/CollaborationExplorer.jsx",
                     "frontend/src/components/ProductionReadiness.jsx"],
        "collections": ["ai_brain_registry", "ai_brain_runs", "ai_brain_graph_nodes", "ai_brain_graph_edges", "ai_brain_processes"],
        "tests": ["backend/tests/test_iter16*.py"],
        "features": [
            {"label": "Discovery Engine automat", "path": "backend/ai_brain/discovery.py", "pattern": "discover_apis"},
            {"label": "Knowledge Graph construit", "collection": "ai_brain_graph_nodes"},
            {"label": "Certificare v1.0.0", "collection": "ai_brain_certification"},
            {"label": "Mentor + Explainability", "path": "backend/ai_brain/mentor.py"},
        ],
        "bvs": {"retention": 4, "conversion": 2, "revenue": 2, "cost": 9},
    },
    {
        "key": "guardian", "name": "Guardian Kernel", "status": "activ",
        "desc": "Gardienii autonomi de arhitectură și produs — protejează logica de cod și arhitectura canonică.",
        "backend": ["backend/architecture_guardian.py", "backend/product_guardian.py", "backend/journey_guardian.py"],
        "frontend": [],
        "collections": ["architecture_guardian_runs", "product_guardian_runs"],
        "tests": [],
        "features": [
            {"label": "Scor arhitectură calculat", "path": "backend/architecture_guardian.py", "pattern": "architecture_score"},
            {"label": "Scor produs calculat", "path": "backend/product_guardian.py", "pattern": "product_score"},
        ],
        "bvs": {"retention": 3, "conversion": 1, "revenue": 1, "cost": 9},
    },
    {
        "key": "digital_twin", "name": "Digital Twin", "status": "duplicat",
        "desc": "Gemenii digitali ai proprietăților. ATENȚIE: 4 sisteme paralele (properties.dna, twins, digital_twin_projects, hh_*) — necesită unificare (G2).",
        "backend": ["backend/routes/digital_twin.py", "backend/routes/twin.py", "backend/routes/property_dna.py",
                    "backend/routes/operator_twins.py"],
        "frontend": ["frontend/src/pages/DigitalTwinPage.jsx", "frontend/src/components/DigitalTwinViewer.jsx",
                     "frontend/src/pages/ClientTwinViewer.jsx"],
        "collections": ["digital_twin_projects", "twins", "properties"],
        "tests": ["backend/tests/test_*twin*.py", "backend/tests/test_*dna*.py"],
        "features": [
            {"label": "Property DNA (SSOT declarat)", "path": "backend/routes/property_dna.py"},
            {"label": "Twin viewer 3D", "path": "frontend/src/components/DigitalTwinViewer.jsx"},
            {"label": "Colecție twin UNICĂ (unificare G2)", "path": "backend/docs_evidence_missing/unified_twin.py"},
            {"label": "Timeline proprietate", "path": "backend/routes/property_timeline.py"},
        ],
        "bvs": {"retention": 8, "conversion": 6, "revenue": 5, "cost": 3},
    },
    {
        "key": "house_health", "name": "House Health", "status": "activ",
        "desc": "Abonamente premium de sănătate a casei: scoruri, evaluări specialiști, planuri, billing.",
        "backend": ["backend/routes/house_health.py", "backend/routes/house_health_billing.py",
                    "backend/routes/house_health_plans.py", "backend/routes/house_health_recommendations.py"],
        "frontend": ["frontend/src/pages/HouseHealthPage.jsx", "frontend/src/pages/HouseHealthCard.jsx",
                     "frontend/src/pages/HouseHealthUpgradePage.jsx"],
        "collections": ["hh_subscriptions", "hh_scores", "hh_evaluations", "hh_plans"],
        "tests": ["backend/tests/test_*health*.py"],
        "features": [
            {"label": "Scoring config + praguri", "collection": "hh_scoring_config"},
            {"label": "Billing Stripe conectat", "path": "backend/routes/house_health_billing.py", "pattern": "stripe|checkout"},
            {"label": "Abonamente active (date reale)", "collection": "hh_subscriptions"},
            {"label": "Gating pe twin-ul validat (nu DT Pro)", "path": "backend/docs_evidence_missing/hh_twin_gate.py"},
            {"label": "UI billing conectat la abonare", "path": "frontend/src/pages/HouseHealthUpgradePage.jsx", "pattern": "subscribe|checkout|billing"},
        ],
        "bvs": {"retention": 8, "conversion": 6, "revenue": 9, "cost": 2},
    },
    {
        "key": "marketplace_core", "name": "Marketplace Core (Cereri & Oferte)", "status": "activ",
        "desc": "Fluxul central de venit: cereri client → oferte specialiști → acceptare → lucrare → recenzie.",
        "backend": ["backend/routes/requests.py", "backend/routes/marketplace_offers.py", "backend/routes/matching.py"],
        "frontend": ["frontend/src/pages/ClientRequestOffersPage.jsx", "frontend/src/pages/SpecialistDashboard.jsx"],
        "collections": ["requests", "reviews"],
        "tests": ["backend/tests/test_*offer*.py", "backend/tests/test_*request*.py"],
        "features": [
            {"label": "Hybrid ranking + fairness rotation", "path": "backend/routes/marketplace_offers.py", "pattern": "_fairness_boost"},
            {"label": "Lead fee 45 RON + waive la rebooking", "path": "backend/routes/requests.py", "pattern": "lead_fee_waived"},
            {"label": "Cereri directe (direct_specialist_id)", "path": "backend/routes/requests.py", "pattern": "direct_specialist_id"},
            {"label": "Recenzii cu rebook/recommend", "path": "backend/routes/requests.py", "pattern": "would_hire_again"},
        ],
        "bvs": {"retention": 7, "conversion": 9, "revenue": 9, "cost": 3},
    },
    {
        "key": "marketplace_public", "name": "Marketplace Public & Trust", "status": "activ",
        "desc": "Vitrina publică de specialiști cu Trust Layer (rebook %, recomandări, badges).",
        "backend": ["backend/routes/marketplace.py", "backend/routes/trust.py", "backend/routes/public_trust.py"],
        "frontend": ["frontend/src/pages/Marketplace.jsx", "frontend/src/pages/SpecialistProfile.jsx"],
        "collections": ["users"],
        "tests": ["backend/tests/test_trust_growth_iter144.py"],
        "features": [
            {"label": "Trust rollup pe carduri", "path": "backend/routes/marketplace.py", "pattern": "trust"},
            {"label": "Early-access empty state", "path": "frontend/src/pages/Marketplace.jsx", "pattern": "mkt-early-access"},
            {"label": "Filtru defensiv REJECTED/SUSPENDED", "path": "frontend/src/pages/Marketplace.jsx", "pattern": "REJECTED"},
        ],
        "bvs": {"retention": 5, "conversion": 9, "revenue": 7, "cost": 2},
    },
    {
        "key": "fair_price", "name": "FairPrice Engine", "status": "candidat_reutilizare",
        "desc": "NU există motor dedicat. Piese răspândite: fairness ranking (marketplace_offers), praguri HH, prețuri publice CMS. FP-001 le va consolida prin EXTENSIE.",
        "backend": ["backend/routes/fair_price.py"],
        "frontend": [],
        "collections": ["price_benchmarks"],
        "tests": ["backend/tests/test_*fair*.py"],
        "features": [
            {"label": "Fairness în ranking oferte (există — reutilizabil)", "path": "backend/routes/marketplace_offers.py", "pattern": "fairness"},
            {"label": "Praguri de preț House Health (există — reutilizabil)", "path": "backend/routes/house_health_plans.py", "pattern": "thresholds"},
            {"label": "Pagini publice de prețuri (există — reutilizabil)", "path": "frontend/src/pages/PreturiPage.jsx"},
            {"label": "Estimare preț per categorie de lucrare", "path": "backend/routes/fair_price.py", "pattern": "estimate"},
            {"label": "Benchmark prețuri de piață", "collection": "price_benchmarks"},
        ],
        "bvs": {"retention": 6, "conversion": 8, "revenue": 7, "cost": 3},
        "reuse": ["marketplace_offers.py · _fairness_boost + ranking policy", "house_health_plans.py · praguri configurabile",
                  "PreturiPage/PreturiIndex · prezentare publică prețuri", "requests.budget + offers.price · date istorice reale de preț"],
    },
    {
        "key": "loyalty_tiers", "name": "Loyalty & Experience Tiers", "status": "activ",
        "desc": "Progressive disclosure + progresie 7 niveluri specialiști + recompense de loialitate (rebooking 0 RON). Gamification (QuestPanel/TierCelebration) parțial demontată.",
        "backend": ["backend/routes/experience_tiers.py", "backend/routes/tier_milestones.py",
                    "backend/routes/specialist_progression.py", "backend/routes/capability_engine.py"],
        "frontend": ["frontend/src/lib/useTier.js", "frontend/src/components/SpecialistProgressCard.jsx",
                     "frontend/src/lib/QuestPanel.jsx", "frontend/src/lib/TierCelebrationBanner.jsx"],
        "collections": ["experience_tier_history", "capability_catalog"],
        "tests": ["backend/tests/test_phase1*.py"],
        "features": [
            {"label": "Tiers automate cu criterii", "path": "backend/routes/experience_tiers.py", "pattern": "experience_tier"},
            {"label": "Progresie 7 niveluri data-driven", "path": "backend/routes/capability_engine.py", "pattern": "next_requirements"},
            {"label": "Recompensă loialitate: rebooking gratuit", "path": "backend/routes/trusted_specialists.py", "pattern": "lead_fee_waived"},
            {"label": "Vouchere / quests montate în UI", "path": "frontend/src/pages/SpecialistDashboard.jsx", "pattern": "QuestPanel"},
        ],
        "bvs": {"retention": 8, "conversion": 5, "revenue": 6, "cost": 2},
        "reuse": ["experience_tiers.py · motor tiers configurabil", "tier_milestones.py · praguri + celebrări",
                  "lib/QuestPanel + TierCelebrationBanner · UI gamification existent"],
    },
    {
        "key": "referral", "name": "Referral Engine", "status": "activ",
        "desc": "Invitații cu recomandare pe roluri (client/specialist), claim idempotent, link-uri virale WhatsApp.",
        "backend": ["backend/routes/trust_growth.py"],
        "frontend": ["frontend/src/components/ReferralHub.jsx"],
        "collections": ["referral_invites", "recommendations"],
        "tests": ["backend/tests/test_trust_growth_iter144.py"],
        "features": [
            {"label": "Invitații pe roluri + email", "path": "backend/routes/trust_growth.py", "pattern": "referrals/invite"},
            {"label": "Claim idempotent cu recomandare", "path": "backend/routes/trust_growth.py", "pattern": "referrals/claim"},
            {"label": "ReferralHub dual-variant montat", "path": "frontend/src/components/ReferralHub.jsx"},
            {"label": "Recompensă materială la referral (bonus/token)", "path": "backend/docs_evidence_missing/referral_reward.py"},
        ],
        "bvs": {"retention": 6, "conversion": 9, "revenue": 7, "cost": 2},
        "reuse": ["trust_growth.py · fluxul complet invite→claim→notify", "ReferralHub.jsx · UI client+specialist"],
    },
    {
        "key": "tokens_wallet", "name": "Tokens & Wallet", "status": "candidat_reutilizare",
        "desc": "Wallet simplu (wallet_balance pe users + transactions). Fără ledger dedicat, fără tokens de beneficii — fundația PB-001.",
        "backend": ["backend/routes/wallet.py", "backend/routes/payments.py"],
        "frontend": [],
        "collections": ["transactions", "payment_transactions"],
        "tests": [],
        "features": [
            {"label": "Top-up + istoric tranzacții", "path": "backend/routes/wallet.py", "pattern": "wallet/topup"},
            {"label": "Plăți Stripe", "path": "backend/routes/payments.py", "pattern": "stripe"},
            {"label": "Ledger unificat de beneficii/puncte", "path": "backend/docs_evidence_missing/benefits_ledger.py"},
        ],
        "bvs": {"retention": 6, "conversion": 4, "revenue": 8, "cost": 3},
        "reuse": ["wallet.py · balance + tranzacții", "payments.py · integrare Stripe funcțională",
                  "transactions collection · istoric existent"],
    },
    {
        "key": "prop_benefits", "name": "PropBenefits Engine", "status": "planificat", "planned": True,
        "desc": "PB-001 — motorul comercial de beneficii. NU există cod. Se construiește prin EXTENSIE (regula 60%): referral + tiers + wallet + campanii + billing.",
        "backend": ["backend/routes/prop_benefits.py"],
        "frontend": ["frontend/src/components/PropBenefitsHub.jsx"],
        "collections": ["prop_benefits_ledger"],
        "tests": ["backend/tests/test_*benefits*.py"],
        "features": [
            {"label": "Catalog beneficii", "path": "backend/routes/prop_benefits.py", "pattern": "catalog"},
            {"label": "Ledger puncte/beneficii", "collection": "prop_benefits_ledger"},
            {"label": "UI beneficii montat", "path": "frontend/src/components/PropBenefitsHub.jsx"},
        ],
        "bvs": {"retention": 9, "conversion": 8, "revenue": 10, "cost": 3},
        "reuse": ["trust_growth.py · Referral Engine (~80% reutilizabil)", "experience_tiers.py + tier_milestones.py · niveluri (~70%)",
                  "wallet.py + transactions · ledger de bază (~60%)", "community_buildings.py · campanii de grup (~65%)",
                  "house_health_billing.py + payments.py · billing (~70%)", "orchestrator playbooks + notificări (~90%)"],
    },
    {
        "key": "buildings_community", "name": "Buildings & Community", "status": "activ",
        "desc": "Blocuri, campanii comune de mentenanță, workspace administrator, Building Health Score — pilotul celor 13 apartamente.",
        "backend": ["backend/routes/community_buildings.py", "backend/routes/building_admin.py"],
        "frontend": ["frontend/src/components/BuildingHub.jsx", "frontend/src/pages/AdministratorWorkspace.jsx",
                     "frontend/src/components/SpecialistCampaigns.jsx"],
        "collections": ["buildings", "community_campaigns"],
        "tests": ["backend/tests/test_community_buildings_iter146.py", "backend/tests/test_pm_pilot_admin_iter147.py"],
        "features": [
            {"label": "Building Health Score 5 componente", "path": "backend/routes/building_admin.py", "pattern": "compute_building_health"},
            {"label": "Campanii + auto-detecție nightly", "path": "backend/routes/community_buildings.py", "pattern": "campaign_detection_tick"},
            {"label": "Anunțuri + invitații bloc", "path": "backend/routes/building_admin.py", "pattern": "announcements"},
            {"label": "Import Excel/CSV apartamente", "path": "backend/docs_evidence_missing/building_import.py"},
        ],
        "bvs": {"retention": 9, "conversion": 8, "revenue": 8, "cost": 2},
    },
    {
        "key": "property_passport", "name": "Property Passport", "status": "activ",
        "desc": "Pașaport public per proprietate cu QR, trust score verificabil, analytics GDPR-safe, buclă virală.",
        "backend": ["backend/routes/property_passport.py", "backend/routes/passport_analytics.py"],
        "frontend": ["frontend/src/pages/PublicPassportPage.jsx", "frontend/src/pages/clientv2/PassportCard.jsx"],
        "collections": ["passport_events"],
        "tests": ["backend/tests/test_cx3_passport_iter135.py"],
        "features": [
            {"label": "QR + OG social previews", "path": "backend/routes/property_passport.py", "pattern": "qr"},
            {"label": "Analytics + conversii first-touch", "path": "backend/routes/passport_analytics.py", "pattern": "track"},
            {"label": "Privacy toggles server-side", "path": "backend/routes/property_passport.py", "pattern": "privacy"},
        ],
        "bvs": {"retention": 5, "conversion": 8, "revenue": 4, "cost": 1},
    },
    {
        "key": "document_vault", "name": "Document Vault (Cartea Casei)", "status": "activ",
        "desc": "Documente per proprietate pe object storage, completeness score 0-100 din 14 semnale, istoric imutabil.",
        "backend": ["backend/routes/property_documents.py", "backend/storage_client.py"],
        "frontend": ["frontend/src/pages/clientv2/DocumentVault.jsx"],
        "collections": ["property_documents"],
        "tests": ["backend/tests/test_*document*.py"],
        "features": [
            {"label": "Upload multipart + metadate D015", "path": "backend/routes/property_documents.py", "pattern": "upload"},
            {"label": "Completeness Score proprietate", "path": "backend/routes/property_documents.py", "pattern": "completeness"},
            {"label": "Istoric imutabil + versiuni", "path": "backend/routes/property_documents.py", "pattern": "supersedes"},
        ],
        "bvs": {"retention": 8, "conversion": 5, "revenue": 4, "cost": 2},
    },
    {
        "key": "maintenance_calendar", "name": "Calendar Mentenanță", "status": "activ",
        "desc": "Revizii recurente cu template-uri RO, remindere zilnice, cereri directe la specialistul de încredere (0 lei lead).",
        "backend": ["backend/routes/maintenance_calendar.py"],
        "frontend": ["frontend/src/components/MaintenanceCalendar.jsx"],
        "collections": ["maintenance_tasks"],
        "tests": ["backend/tests/test_gbos_growth_iter145.py"],
        "features": [
            {"label": "8 template-uri revizii RO", "path": "backend/routes/maintenance_calendar.py", "pattern": "templates"},
            {"label": "Reminder tick zilnic", "path": "backend/routes/maintenance_calendar.py", "pattern": "maintenance_due_tick"},
            {"label": "Cerere directă 0 lei din task", "path": "backend/routes/maintenance_calendar.py", "pattern": "direct"},
        ],
        "bvs": {"retention": 9, "conversion": 6, "revenue": 8, "cost": 2},
    },
    {
        "key": "trusted_specialists", "name": "Trusted Specialists & Rebooking", "status": "activ",
        "desc": "Specialiștii de încredere ai clientului + rebooking 1-click cu lead fee 0 — venit din repetare.",
        "backend": ["backend/routes/trusted_specialists.py"],
        "frontend": ["frontend/src/components/TrustedSpecialists.jsx", "frontend/src/components/PostJobGrowthLoop.jsx"],
        "collections": ["requests"],
        "tests": ["backend/tests/test_gbos_growth_iter145.py"],
        "features": [
            {"label": "Agregare lucrări + rebook rollup", "path": "backend/routes/trusted_specialists.py", "pattern": "jobs_together"},
            {"label": "Rebook direct cu fee 0", "path": "backend/routes/trusted_specialists.py", "pattern": "rebook"},
            {"label": "Post-Job Growth Loop montat", "path": "frontend/src/components/PostJobGrowthLoop.jsx"},
        ],
        "bvs": {"retention": 8, "conversion": 6, "revenue": 8, "cost": 2},
    },
    {
        "key": "city_partners", "name": "City Partners", "status": "experimental",
        "desc": "Program de parteneriat strategic pe orașe (V1 non-exclusiv): parteneri, lead-uri, onboarding 7 pași.",
        "backend": ["backend/routes/city_partners.py"],
        "frontend": ["frontend/src/pages/admin/CityPartnersPage.jsx", "frontend/src/pages/admin/CityPartnerDetailPage.jsx"],
        "collections": ["city_partners", "city_partner_leads"],
        "tests": [],
        "features": [
            {"label": "CRUD parteneri + onboarding", "path": "backend/routes/city_partners.py", "pattern": "onboarding-step"},
            {"label": "Self-service partener (role)", "path": "backend/routes/city_partners.py", "pattern": "city_partner"},
            {"label": "Comisioane marketplace (V2)", "path": "backend/docs_evidence_missing/partner_commissions.py"},
            {"label": "Parteneri activi (date reale)", "collection": "city_partners"},
        ],
        "bvs": {"retention": 3, "conversion": 5, "revenue": 6, "cost": 4},
    },
    {
        "key": "subscriptions_billing", "name": "Subscriptions & Billing", "status": "activ",
        "desc": "Stripe (test mode — claim LIVE pending), tranzacții, manual payments ledger, Money-Flow Guard.",
        "backend": ["backend/routes/payments.py", "backend/routes/house_health_billing.py", "backend/routes/first_revenue.py"],
        "frontend": ["frontend/src/pages/PaymentSuccess.jsx"],
        "collections": ["payment_transactions"],
        "tests": [],
        "features": [
            {"label": "Stripe checkout integrat", "path": "backend/routes/payments.py", "pattern": "checkout"},
            {"label": "Money-Flow Guard (detecție LIVE/TEST)", "path": "backend/routes/launch_sentinel.py", "pattern": "money"},
            {"label": "e-Factura RO", "path": "backend/docs_evidence_missing/efactura.py"},
        ],
        "bvs": {"retention": 7, "conversion": 6, "revenue": 10, "cost": 4},
    },
    {
        "key": "orchestrator", "name": "Orchestrator & Playbooks", "status": "activ",
        "desc": "Event-driven orchestrator cu 14 playbooks, ledger, semnale de lansare, minutes_saved.",
        "backend": ["backend/orchestrator/engine.py", "backend/orchestrator/playbooks_launch.py", "backend/routes/orchestrator.py"],
        "frontend": [],
        "collections": ["orchestrator_ledger"],
        "tests": [],
        "features": [
            {"label": "Ledger cu playbooks", "collection": "orchestrator_ledger"},
            {"label": "Semnale de lansare (resident/campaign/payment)", "path": "backend/orchestrator/playbooks_launch.py", "pattern": "first_payment"},
        ],
        "bvs": {"retention": 4, "conversion": 3, "revenue": 3, "cost": 8},
    },
]

KNOWN_DUPLICATES = [
    {"id": "dup_twin_systems", "title": "4 sisteme Digital Twin paralele",
     "elements": ["properties.dna (property_dna.py)", "twins (twin.py, operator)", "digital_twin_projects (digital_twin.py, Pro)", "hh_* (house_health.py)"],
     "impact": "House Health cere proiect DT Pro în loc de twin-ul validat; date fragmentate; scoruri concurente.",
     "recommendation": "Unificare pe digital_twin_projects (gap G2) — migrarea colecției twins + gating HH pe twin-ul real."},
    {"id": "dup_twin_viewers", "title": "4 componente viewer twin în frontend",
     "elements": ["DigitalTwinViewer.jsx", "ClientTwinViewer.jsx", "OperatorTwin.jsx", "OperatorDigitalTwin.jsx"],
     "impact": "Logică de randare duplicată, bug-uri fixate în 4 locuri.",
     "recommendation": "Un viewer canonic cu prop-uri de rol; celelalte devin wrappere subțiri sau se elimină."},
    {"id": "dup_reviews", "title": "2 sisteme de recenzii (v1 + v2)",
     "elements": ["requests.py · ReviewIn (v1)", "reviews_v2.py (multi-dimensional)"],
     "impact": "Câmpurile would_hire_again/would_recommend întreținute în paralel.",
     "recommendation": "Unificare pe reviews_v2 cu adapter pentru v1; NU se rescrie — se extinde v2 (regula 60%)."},
    {"id": "dup_dashboards", "title": "Dashboard-uri legacy vs V2",
     "elements": ["pages/Dashboards.jsx (legacy)", "pages/clientv2/ClientDashboardV2.jsx", "pages/SpecialistDashboard.jsx"],
     "impact": "Cod mort/parțial mort în bundle; confuzie la modificări.",
     "recommendation": "Audit rutele care mai folosesc Dashboards.jsx → retragere controlată."},
]

CONSOLIDATION_BASE = [
    {"id": "cons_wallet_ledger", "title": "Ledger unificat Tokens/Wallet pentru PB-001",
     "why": "PropBenefits are nevoie de un ledger canonic de puncte/beneficii. Există wallet_balance + transactions + payment_transactions — se EXTIND într-un serviciu unic.",
     "impact": 5, "risk": 2, "effort": "M", "modules": ["tokens_wallet", "prop_benefits"]},
    {"id": "cons_twin_unification", "title": "Unificare Digital Twin (G2): twins → digital_twin_projects",
     "why": "4 sisteme paralele fragmentează datele; House Health e blocat pe DT Pro în loc de twin-ul validat.",
     "impact": 5, "risk": 4, "effort": "L", "modules": ["digital_twin", "house_health"]},
    {"id": "cons_fair_price", "title": "Consolidare piese pricing → FairPrice Engine (FP-001)",
     "why": "Fairness ranking, praguri HH și prețuri publice există separat — FP-001 le unifică prin extensie, cu date istorice din requests/offers.",
     "impact": 4, "risk": 2, "effort": "M", "modules": ["fair_price", "marketplace_core"]},
    {"id": "cons_reviews_merge", "title": "Unificare recenzii v1/v2",
     "why": "Două scheme de recenzii întreținute în paralel; datele Rebook Score trebuie să curgă dintr-o singură sursă.",
     "impact": 3, "risk": 3, "effort": "M", "modules": ["marketplace_core"]},
    {"id": "cons_twin_viewers", "title": "Consolidare viewere twin (4 → 1 canonic)",
     "why": "Logică de randare duplicată în 4 componente.",
     "impact": 3, "risk": 3, "effort": "M", "modules": ["digital_twin"]},
    {"id": "cons_admin_bundle", "title": "Split bundle admin (main.js ~2.3MB)",
     "why": "Paginile admin încarcă bundle-ul principal; code splitting suplimentar reduce TTI pentru clienți reali.",
     "impact": 3, "risk": 2, "effort": "M", "modules": []},
    {"id": "cons_loyalty_surface", "title": "Decizie gamification: QuestPanel + TierCelebration",
     "why": "Componente funcționale demontate parțial din V2 — se decid: remontare în PB-001 (recomandat) sau eliminare.",
     "impact": 2, "risk": 1, "effort": "S", "modules": ["loyalty_tiers", "prop_benefits"]},
    {"id": "cons_legacy_dashboards", "title": "Retragere Dashboards.jsx legacy",
     "why": "Cod potențial mort după migrarea la V2.",
     "impact": 2, "risk": 3, "effort": "S", "modules": []},
]

IMPORT_RE = re.compile(
    r"""(?:(?:import|export)\s+(?:[^'";]*?from\s+)?|import\(\s*|require\(\s*)["']([^"']+)["']""")

_cache: dict = {"map": None, "ts": 0.0}
CACHE_TTL = 300


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Frontend reachability (orphan detection)
# ---------------------------------------------------------------------------
def _resolve_import(base_dir: Path, spec: str):
    if spec.startswith("@/"):
        target = (FRONTEND_SRC / spec[2:]).resolve()
    elif spec.startswith("."):
        target = (base_dir / spec).resolve()
    else:
        return None
    for cand in (target, Path(str(target) + ".jsx"), Path(str(target) + ".js"),
                 target / "index.js", target / "index.jsx"):
        if cand.is_file():
            return cand
    return None


def scan_frontend_reachability() -> dict:
    all_files = {p for p in FRONTEND_SRC.rglob("*.js*") if "__tests__" not in str(p) and not p.name.endswith(".test.js")}
    entries = [FRONTEND_SRC / "index.js", FRONTEND_SRC / "App.js"]
    seen, stack = set(), [e for e in entries if e.exists()]
    while stack:
        f = stack.pop()
        if f in seen:
            continue
        seen.add(f)
        text = _read(f)
        for spec in IMPORT_RE.findall(text):
            r = _resolve_import(f.parent, spec)
            if r and r not in seen:
                stack.append(r)
    orphans = []
    for p in sorted(all_files - seen):
        rel = str(p.relative_to(FRONTEND_SRC))
        if rel.startswith("components/ui/") or rel in ("index.js", "setupTests.js", "reportWebVitals.js"):
            continue
        orphans.append(rel)
    return {"total_files": len(all_files), "reachable": len(seen), "orphans": orphans,
            "reachable_set": {str(p.relative_to(FRONTEND_SRC)) for p in seen if str(p).startswith(str(FRONTEND_SRC))}}


# ---------------------------------------------------------------------------
# Feature checks + completeness
# ---------------------------------------------------------------------------
async def _check_feature(feat: dict) -> bool:
    if "collection" in feat:
        try:
            return await db[feat["collection"]].count_documents({}, limit=1) > 0
        except Exception:  # noqa: BLE001
            return False
    if "glob" in feat:
        return any(APP.glob(feat["glob"]))
    p = APP / feat["path"]
    if not p.is_file():
        return False
    if "pattern" in feat:
        return re.search(feat["pattern"], _read(p), re.IGNORECASE) is not None
    return True


def _count_endpoints(backend_files: list) -> int:
    ep_re = re.compile(r"@\w+\.(get|post|put|patch|delete)\(")
    n = 0
    for f in backend_files:
        p = APP / f
        if p.is_file():
            n += len(ep_re.findall(_read(p)))
        elif p.is_dir():
            for sub in p.glob("*.py"):
                n += len(ep_re.findall(_read(sub)))
    return n


async def _evaluate_module(mod: dict, reachable: set) -> dict:
    possible, achieved = 0.0, 0.0
    signals = {}

    backend = mod.get("backend") or []
    if backend:
        exist = [f for f in backend if (APP / f).exists()]
        possible += 25
        achieved += 25 * len(exist) / len(backend)
        signals["backend"] = {"declared": len(backend), "found": len(exist),
                              "endpoints": _count_endpoints(exist)}

    frontend = mod.get("frontend") or []
    if frontend:
        exist_f = [f for f in frontend if (APP / f).exists()]
        possible += 20
        achieved += 20 * len(exist_f) / len(frontend)
        rel_paths = [f.replace("frontend/src/", "") for f in exist_f]
        mounted = [r for r in rel_paths if r in reachable]
        possible += 10
        achieved += 10 * (len(mounted) / len(rel_paths)) if rel_paths else 0
        signals["frontend"] = {"declared": len(frontend), "found": len(exist_f),
                               "mounted": len(mounted),
                               "unmounted": [r for r in rel_paths if r not in reachable]}

    cols = mod.get("collections") or []
    if cols:
        possible += 15
        with_data = []
        for c in cols:
            try:
                if await db[c].count_documents({}, limit=1) > 0:
                    with_data.append(c)
            except Exception:  # noqa: BLE001
                pass
        achieved += 15 * len(with_data) / len(cols)
        signals["data"] = {"declared": len(cols), "with_data": len(with_data),
                           "empty": [c for c in cols if c not in with_data]}

    tests = mod.get("tests") or []
    if tests:
        possible += 10
        found_tests = [str(p.relative_to(APP)) for g in tests for p in APP.glob(g)]
        achieved += 10 if found_tests else 0
        signals["tests"] = {"found": len(found_tests)}

    feats = mod.get("features") or []
    feat_results = []
    if feats:
        possible += 20
        ok = 0
        for f in feats:
            passed = await _check_feature(f)
            ok += 1 if passed else 0
            feat_results.append({"label": f["label"], "ok": passed})
        achieved += 20 * ok / len(feats)

    completeness = round(100 * achieved / possible) if possible else 0
    b = mod["bvs"]
    bvs = round((b["revenue"] * BVS_WEIGHTS["revenue"] + b["conversion"] * BVS_WEIGHTS["conversion"]
                 + b["retention"] * BVS_WEIGHTS["retention"] + b["cost"] * BVS_WEIGHTS["cost"]) * 10)
    return {
        "key": mod["key"], "name": mod["name"], "desc": mod["desc"], "status": mod["status"],
        "planned": mod.get("planned", False),
        "completeness": completeness, "business_value": bvs,
        "priority_index": round(bvs * (100 - completeness) / 100),
        "signals": signals, "features": feat_results,
        "bvs_breakdown": b, "reuse": mod.get("reuse") or [],
        "elements": {"backend": backend, "frontend": frontend, "collections": cols},
    }


# ---------------------------------------------------------------------------
# Product map (live) + graph
# ---------------------------------------------------------------------------
async def build_product_map() -> dict:
    reach = scan_frontend_reachability()
    modules = [await _evaluate_module(m, reach["reachable_set"]) for m in MODULE_CATALOG]

    col_owner: dict = {}
    for m in MODULE_CATALOG:
        for c in m.get("collections") or []:
            col_owner.setdefault(c, []).append(m["key"])
    relations = []
    for c, owners in col_owner.items():
        if len(owners) > 1:
            for i in range(len(owners)):
                for j in range(i + 1, len(owners)):
                    relations.append({"source": owners[i], "target": owners[j],
                                      "via": f"colecția {c}", "type": "shared_data"})
    for m in MODULE_CATALOG:
        for r in m.get("reuse") or []:
            relations.append({"source": m["key"], "target": r.split("·")[0].strip(),
                              "via": r, "type": "reuse_candidate"})

    roadmap = list(CONSOLIDATION_BASE)
    if reach["orphans"]:
        roadmap.append({"id": "cons_orphans", "title": f"Curățenie {len(reach['orphans'])} fișiere frontend neconectate",
                        "why": "Fișiere neimportate din App.js — cod mort sau componente demontate (listă în tab-ul Neconectate).",
                        "impact": 2, "risk": 1, "effort": "S", "modules": []})
    roadmap.sort(key=lambda r: -(r["impact"] * 2 - r["risk"]))

    active = [m for m in modules if not m["planned"]]
    avg = round(sum(m["completeness"] for m in active) / len(active)) if active else 0
    return {
        "generated_at": _now(),
        "totals": {
            "modules": len(modules),
            "avg_completeness": avg,
            "orphans": len(reach["orphans"]),
            "duplicates": len(KNOWN_DUPLICATES),
            "frontend_files": reach["total_files"],
            "frontend_reachable": reach["reachable"],
        },
        "modules": sorted(modules, key=lambda m: -m["priority_index"]),
        "orphans": reach["orphans"][:300],
        "duplicates": KNOWN_DUPLICATES,
        "relations": relations,
        "consolidation_roadmap": roadmap,
        "rules": {
            "reuse_60": "Regula 60%: dacă o implementare există în proporție de peste 60%, se REUTILIZEAZĂ și se EXTINDE — nu se rescrie.",
            "bvs_weights": BVS_WEIGHTS,
        },
        "next_epics": ["PB-001 · PropBenefits Engine Foundation", "FP-001 · FairPrice Engine", "HH-Next · House Health Subscriptions"],
    }


async def get_product_map(refresh: bool = False) -> dict:
    if not refresh and _cache["map"] and time.monotonic() - _cache["ts"] < CACHE_TTL:
        return _cache["map"]
    m = await build_product_map()
    _cache["map"], _cache["ts"] = m, time.monotonic()
    return m


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------
async def save_snapshot(label: str, created_by: str) -> dict:
    m = await get_product_map(refresh=True)
    snap = {"id": uuid.uuid4().hex, "label": label or f"Snapshot {_now()[:10]}",
            "created_by": created_by, "created_at": _now(), "map": m}
    await db.product_map_snapshots.insert_one({**snap})
    return {"id": snap["id"], "label": snap["label"], "created_at": snap["created_at"],
            "totals": m["totals"]}


async def list_snapshots() -> list:
    out = []
    async for d in db.product_map_snapshots.find({}, {"_id": 0, "id": 1, "label": 1, "created_at": 1,
                                                      "created_by": 1, "map.totals": 1}).sort("created_at", -1).limit(50):
        out.append({"id": d["id"], "label": d["label"], "created_at": d["created_at"],
                    "created_by": d.get("created_by"), "totals": (d.get("map") or {}).get("totals")})
    return out


async def compare_snapshots(a: str, b: str) -> dict:
    da = await db.product_map_snapshots.find_one({"id": a}, {"_id": 0})
    dbb = await db.product_map_snapshots.find_one({"id": b}, {"_id": 0})
    if not da or not dbb:
        return {"error": "Snapshot inexistent."}
    ma = {m["key"]: m for m in da["map"]["modules"]}
    mb = {m["key"]: m for m in dbb["map"]["modules"]}
    deltas = []
    for k in sorted(set(ma) | set(mb)):
        ca = ma.get(k, {}).get("completeness")
        cb = mb.get(k, {}).get("completeness")
        deltas.append({"key": k, "name": (mb.get(k) or ma.get(k))["name"],
                       "a": ca, "b": cb,
                       "delta": (cb - ca) if (ca is not None and cb is not None) else None})
    return {"a": {"id": a, "label": da["label"], "created_at": da["created_at"], "totals": da["map"]["totals"]},
            "b": {"id": b, "label": dbb["label"], "created_at": dbb["created_at"], "totals": dbb["map"]["totals"]},
            "modules": deltas}


# ---------------------------------------------------------------------------
# MASTER DISCOVERY REPORT
# ---------------------------------------------------------------------------
STATUS_RO = {"activ": "Activ", "experimental": "Experimental", "duplicat": "Duplicat",
             "neconectat": "Neconectat", "depreciat": "Depreciat",
             "candidat_reutilizare": "Candidat reutilizare", "planificat": "Planificat"}


async def generate_report() -> dict:
    m = await get_product_map(refresh=True)
    t = m["totals"]
    lines = [
        "# MASTER DISCOVERY REPORT — CORE-001",
        f"\n*Generat: {m['generated_at']} · Live Product Map · AI Brain Product Intelligence Engine*\n",
        "## 1. Rezumat executiv",
        f"- **{t['modules']} module de produs** cartografiate canonic · completitudine medie **{t['avg_completeness']}%**.",
        f"- **{t['orphans']} fișiere frontend neconectate** (neimportate din App.js) · **{t['duplicates']} zone de duplicare** identificate.",
        f"- Frontend: {t['frontend_reachable']}/{t['frontend_files']} fișiere accesibile din rădăcina aplicației.",
        f"- {m['rules']['reuse_60']}",
        "- Ordinea aprobată post-CORE-001: " + " → ".join(m["next_epics"]) + ".",
        "\n## 2. Product Completeness × Business Value (per modul)",
        "\n| Modul | Status | Completeness | Business Value | Priority Index |",
        "|---|---|---|---|---|",
    ]
    for mod in m["modules"]:
        lines.append(f"| {mod['name']} | {STATUS_RO.get(mod['status'], mod['status'])} | "
                     f"{mod['completeness']}% | {mod['business_value']} | {mod['priority_index']} |")
    lines.append("\n*Priority Index = Business Value × (100 − Completeness) / 100 — unde merită investit timpul de dezvoltare.*")

    lines.append("\n## 3. Detaliu module (dovezi)")
    for mod in m["modules"]:
        lines.append(f"\n### {mod['name']} — {mod['completeness']}% · BVS {mod['business_value']}")
        lines.append(mod["desc"])
        sig = mod["signals"]
        if "backend" in sig:
            lines.append(f"- Backend: {sig['backend']['found']}/{sig['backend']['declared']} fișiere · {sig['backend']['endpoints']} endpoint-uri")
        if "frontend" in sig:
            fr = sig["frontend"]
            lines.append(f"- Frontend: {fr['found']}/{fr['declared']} fișiere · {fr['mounted']} montate"
                         + (f" · nemontate: {', '.join(fr['unmounted'])}" if fr["unmounted"] else ""))
        if "data" in sig:
            lines.append(f"- Date: {sig['data']['with_data']}/{sig['data']['declared']} colecții cu date"
                         + (f" · goale: {', '.join(sig['data']['empty'])}" if sig["data"]["empty"] else ""))
        for f in mod["features"]:
            lines.append(f"  - {'✅' if f['ok'] else '❌'} {f['label']}")
        if mod["reuse"]:
            lines.append("- **Candidat reutilizare (regula 60%)**: " + " · ".join(mod["reuse"]))

    lines.append("\n## 4. Duplicate identificate")
    for d in m["duplicates"]:
        lines.append(f"\n### {d['title']}")
        lines.append("- Elemente: " + " · ".join(d["elements"]))
        lines.append(f"- Impact: {d['impact']}")
        lines.append(f"- Recomandare: {d['recommendation']}")

    lines.append(f"\n## 5. Fișiere frontend neconectate ({t['orphans']})")
    for o in m["orphans"]:
        lines.append(f"- `{o}`")

    lines.append("\n## 6. Roadmap de Consolidare (impact × risc)")
    lines.append("\n| # | Acțiune | Impact | Risc | Efort | De ce |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(m["consolidation_roadmap"], 1):
        lines.append(f"| {i} | {r['title']} | {r['impact']}/5 | {r['risk']}/5 | {r['effort']} | {r['why']} |")

    pb = next((x for x in m["modules"] if x["key"] == "prop_benefits"), None)
    lines.append("\n## 7. Pregătire PB-001 — PropBenefits Engine")
    lines.append("PB-001 se construiește prin **EXTENSIE**, nu de la zero. Active reutilizabile:")
    for r in (pb or {}).get("reuse", []):
        lines.append(f"- {r}")
    lines.append("\n*Raport generat automat de AI Brain · Product Intelligence Engine (CORE-001). "
                 "Live Product Map se recalculează la fiecare accesare; snapshot-urile păstrează istoricul.*")

    md = "\n".join(lines)
    try:
        (APP / "docs" / "CORE001_MASTER_DISCOVERY_REPORT.md").write_text(md, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    return {"markdown": md, "generated_at": m["generated_at"], "totals": t}
