# AUDIT TEHNIC & STRATEGIE DE TRANZIȚIE — PropManage AI OS (25 Iul 2026)
Board: CTO Enterprise · AI Architect · SaaS Founder. Fără modificări de cod — doar analiză.
(Copie de arhivă a analizei livrate în chat. Cifrele provin din scanarea reală a codebase-ului.)

## Cifre cheie măsurate
- Backend: ~140 module de rute, 44.480 linii doar în /routes, server.py cu 51 job-uri APScheduler.
- Frontend: 116 rute React, 67 pagini top-level + 108 pagini admin.
- Date: db.users referit de 447 ori, db.requests 207, db.properties DOAR 47.
- Twin fragmentat în 7 colecții: twins, digital_twin_pins(35)/projects(34)/models(19)/plans(14)/comments(9)/qa(2).
- Ledger financiar DUBLU: db.transactions (27) + db.payment_transactions (24).
- Deja există: orchestrator/playbooks (marketplace_medic, pattern_hunter, finance_reconciler), autonomy engine + score,
  morning_command_center cron, auto_match_cron (atribuire automată specialiști), unified_leads (leads_store dual-write),
  KG embrionar (kg/links.py entity_links), ai_governance/agent_registry, warranty_auto_release.
- Escrow: Stripe checkout + demo mode; disputes 100% manual admin; matching = filtru Mongo zonă+categorie fără scoring.
- requests.property_id este deja OBLIGATORIU (RequestIn) — bun. Lead-urile publice (/incepe, city partners, marketplace) NU au proprietate.

## Verdict
Fundația de autonomie există dar e ADMIN-facing (rapoarte pt fondator), nu MARKET-facing (decizii pt clienți/specialiști).
Arhitectura informațională e user-centrică, nu property-centrică. Hipertrofie de suprafețe (116 rute) contrazice Command Center.
Strategie recomandată: Strangler Pattern (deja folosit la unified_leads), NU rescriere big-bang. Producția e live — migrații reversibile.

## Decizii propuse (vezi chat pentru detalii complete)
1. Property-first data layer: colecția `properties` devine agregatul central; toate colecțiile twin consolidate
   sub property_id; un singur ledger financiar; lead-uri publice capătă property stub la conversie.
2. Deprecare/consolidare ~25 suprafețe admin (7 cockpituri paralele → 1 Command Center; QA suite → tooling intern).
3. Command Center = inbox de DECIZII cu aprobare 1-tap pentru 3 roluri, alimentat de agenți.
4. Agenți fază 1: Lead Hunter (Twin→draft cereri), Dispute AI (triaj probe + propunere decizie), Pricing Engine v1.
5. Guardrails: praguri financiare human-in-the-loop, kill-switch per agent (agent_registry), GDPR Art. 22 (intervenție umană
   la decizii automate cu efect juridic/financiar), observabilitate centralizată pt cele 51+ cron jobs.

## Sprint plan aprobat de Board (propus)
- Sprint 1 — Refactoring & Core (property-first, ledger unic, deprecation sweep cu feature flags + redirects, backfill KG).
- Sprint 2 — Autonomy Layer (Command Center decizional multi-rol, primii 3 agenți, governance + audit trail decizii AI).
- Sprint 3 — Partners & Scaling (City Partners B2G cu SLA, Marketplace Partners cu feed produse + comenzi automate,
  hardening multi-tenant, API publică parteneri).

## Status: PREZENTAT UTILIZATORULUI — AȘTEAPTĂ APROBARE. Nu s-a modificat cod.
