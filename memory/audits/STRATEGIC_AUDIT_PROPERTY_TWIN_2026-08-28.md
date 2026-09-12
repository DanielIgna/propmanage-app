# PROPManage — STRATEGIC AUDIT & ARCHITECTURE DISCOVERY
## Property Twin 2D/3D + AI-Assisted 3D + Professional Handoff + Partner Ecosystem
**Data:** 28 Aug 2026 · **Mod:** READ-ONLY (zero cod modificat) · **Metodă:** evidence din cod + date LIVE (preview)
**Legendă:** 🟢 EVIDENCE FROM CODE · 🟡 ARCHITECTURAL INFERENCE · 🔵 FUTURE PRODUCT IDEA

> **UPDATE 28 Aug 2026 — STATUS**: Recomandările P0/P1 din acest audit au fost EXECUTATE + P0.1 (Operator Anchor). Verdictul „3D orfan (0/40)" din §1/§4 este REZOLVAT prin P0 (property anchor + backfill SAFE). Statutul LIVE + taxonomia canonică: `PROPERTY_TWIN_CANONICAL_v1.0.md`. Acest audit rămâne referința de EVIDENCE/FEASIBILITY (datat, read-only).

---

## 1. EXECUTIVE VERDICT
PropManage are deja ~70% din *fundația* unui Property Twin Platform (property knowledge, health loop, versionare model, ambele viewere 2D+3D, comerț fee-based), DAR ~0% din generarea AI-3D și are **un gap arhitectural critic de date**: stratul 3D (`digital_twin_projects`/`digital_twin_models`) e **complet deconectat** de proprietăți (0/40 proiecte și 0/41 modele au `property_id`). „Property Twin" ca umbrelă 2D+3D e confirmat conceptual (P1) și pe jumătate real în cod: 2D e legat de proprietate, 3D nu. Restul viziunii (AI-3D, tipologii, product commerce contextual) e neconstruit dar **poate fi construit non-breaking peste infrastructura existentă**, reutilizând: Property DNA, Knowledge Graph (`entity_links`), Trust Model 015 (confidence/provenance), Maturity L0–L5, Value Loop, marketplace fee-engine.

---

## 2. WHAT EXISTS TODAY (🟢)
### Digital Twin — 2 straturi
- **2D structurat** — colecția `twins` (74 docs live) {property_id, status, rooms[{id,name,type,area}], assets[TwinAsset]}. Legată de proprietate. Rute: `operator_twins.py` (`/api/properties/{id}/twin`, `/spaces` P1, operator validate). Viewer FE: `DigitalTwinPlans.jsx`.
- **3D profesional** — `digital_twin_projects` (40), `digital_twin_models` (41), `digital_twin_plans` (21), `digital_twin_pins` (34). Rute: `digital_twin.py` (prefix `/api/digital-twin`, +operator +admin routers). Viewer FE: `DigitalTwinViewer.jsx` (react-three-fiber + drei + three.js: `MultiLayerScene`, X-Ray `FACE_STYLES`, `MeasureMarkers`, `PinSystem`, secțiuni, fallback Trimble Connect iframe). `TwinAIQA.jsx`.
- **Conversie**: `ALLOWED_EXTS = glb,gltf,skp,dae,obj,fbx,stl,ply`. Blender headless: dae/obj/fbx/stl/ply→glb. SKP=download-only (CloudConvert off). `.ifc/.rvt/.dwg/.dxf` NU sunt acceptate.
- **P1 (livrat, în producție)**: metadata ProfessionalModel (source/version/version_label/status/visibility/change_reason/supersedes/superseded_by/object_path), `PATCH supersedes` non-destructiv, `asset_ref` pe TwinAsset, docs `related_model_id`/`related_room_id`, `GET /properties/{id}/spaces`, gate ingest≠PREMIUM, storage → Object Storage.

### Property Knowledge & Intelligence
- **Property DNA** 🟢 `property_dna.py` — `GET /api/properties/{id}/dna`: proiecție read-only pe Capability Map (identity, health, twin, works, financial, documents, relations(KG), maintenance, sensors, recommendations) + `dna_completeness` % + PVI + timeline. **ACESTA e Property Knowledge Layer-ul deja existent.**
- **Knowledge Graph** 🟢 `kg/links.py` + `routes/kg.py` — colecția `entity_links` {from_type,from_id,rel,to_type,to_id,metadata}. API generic `link()/unlink()/links_of()/backfill()`. Convenție: „orice feature nou scrie legăturile via kg.links.link()". Noduri actuale: property, user, request, dispute, transaction. Rel: owned_by, requested_by, on_property, assigned_to, disputes, pays_for, for_work. Admin-only.
- **Maturity L0–L5** 🟢 `property_intelligence.py` — Înregistrată(0)→Identificată(1)→Documentată(2)→Activă(3)→Monitorizată(4)→Predictivă(5). Criterii binare cumulative (L2=pvi≥40, L4=audited, L5=predictive). „Audit First Rule" (Directiva 014). `refresh_maturity`.
- **Trust Model 015** 🟢 — assets & DNA-attributes cu `source`/`confidence`/`verification_status`: owner_declared → official_document → professional_audit → verified. `CONFIDENCE_LABELS`. **= exact spectrul INFERRED/DOCUMENTED/SPECIALIST-VERIFIED cerut la §7.**
- **Registru Active** 🟢 `property_assets` (SSOT identitate, slot lifecycle replaced/active), **Predictive** actuarial cu disclaimere, **Risk Engine** (`compute_risks`).

### House Health / Value Loop 🟢
- `value_loop.py`: `enrich_on_closure()` — fiecare lucrare CONFIRMATĂ → garanție auto + sănătate bounded (+4 cap 100, `HEALTH_COMPONENT`) + jurnal documentare + evenimente + re-scoring. **Bucla Work→Twin→Health→PVI→History există.**
- `PVI` (Property Value Index 0–100) — 6 componente (twin, works, audit, installations, warranties, identity+KG). Data-driven; `pvi_history`. P1 a eliminat override-ul fals `structure_health=95`.

### Comerț / Ecosistem
- **City Partners** 🟢 `city_partners.py` — CRM parteneri + `city_partner_leads` (stages, revenue), portal partener (`/api/partner/*`: me, leads, stats, copilot/nudges), create-login, onboarding. **NU are catalog de produse, NU are ofertă legată de Twin.**
- **Marketplace Offers** 🟢 `marketplace_offers.py` — specialiști licitează pe cereri: `fee_ron` 5–50 RON, `priority_fee_ron` (sponsored), `ranking_score` = fee·0.35 + rating·0.30 + tier·0.20 + recency·0.10 + fairness·0.05, feature-flag `fee_configs`. Legacy 45 RON/lead. **= mecanica comercială (pay-per-lead + sponsored + ranking) deja probată.**
- **Verified Estate** 🟢 `verified_estate.py` — listări imobiliare premium care CER audit + Digital Twin publicat înainte de vizibilitate. Twin folosit ca poartă de încredere.
- **Abonamente** 🟢 `hh_plans`/`hh_subscriptions` + Stripe (Pricing dinamic livrat anterior).

---

## 3. WHAT CAN BE REUSED
| Nevoie viziune | Infrastructură existentă | Nivel reutilizare |
|---|---|---|
| Property Knowledge Layer (§10) | `property_dna.py` (Capability Map) | 🟢 DIRECT (extindere, nu construcție nouă) |
| Cross-system linking Room↔Asset↔Doc↔Model (§6) | `entity_links` / `kg.link()` | 🟢 DIRECT (doar adaugă node-types + scrie muchii) |
| Confidence INFERRED→VERIFIED (§2,§7) | Trust Model 015 (source/confidence/verification_status) | 🟢 DIRECT (aplică vocabularul la model & instalații) |
| AI-Twin completeness fără sistem paralel (§2) | Maturity L0–L5 + PVI | 🟡 ADAPTARE MEDIE (axă model-completeness distinctă, dar mapabilă pe verified→L5) |
| Health↔Twin loop (§8,§9) | `value_loop.enrich_on_closure` + PVI | 🟢 DIRECT |
| Property History (§8) | `pvi_history` + `activity_events` + DNA timeline + P1 model versioning | 🟡 ADAPTARE MICĂ (leagă versiunile de works/date/cost) |
| Comerț partener (§11–13) | `marketplace_offers` (fee/ranking/sponsored) + `city_partners` | 🟡 ADAPTARE MEDIE (lipsește catalog produse + ofertă pe Twin) |
| Twin ca poartă comercială | `verified_estate` | 🟢 pattern existent |
| 3D rendering (§15) | `DigitalTwinViewer` (react-three-fiber) | 🟢 DIRECT |

---

## 4. WHAT IS MISSING
- 🔴 **Legătura 3D↔Proprietate**: `digital_twin_projects.property_id` opțional, NESETAT (0/40 live). Modelele 3D sunt orfane. (EVIDENCE: query live.)
- 🔴 **AI-assisted 3D generation** (§2): 0 cod (fără massing/procedural/generare). Doar copywriting.
- 🔴 **Tipologii/template** (§4): inexistent (doar un label „tipologie" în technical record).
- 🔴 **Catalog produse partener + ofertă contextuală pe Twin** (§11–12).
- 🟠 **KG nu conține nodurile Twin**: room/space, asset, document, model, model_version, pin, product, offer, health_event — și P1 a scris FK-uri directe, NU muchii KG.
- 🟠 **Import BIM profesional**: `.ifc/.rvt/.dwg/.dxf` neacceptate (P4).
- 🟠 **AI Q&A cu context limitat**: `digital_twin_qa._build_context` citește doar twin (models/plans/pins/comments), NU DNA/documente/works/assets → nu poate răspunde „ce gresie în baia din 2027" (§10).
- 🟠 **Instalații ca strat trasabil** (§7): fără layer dedicat electric/apă/HVAC cu status inferred→verified.
- 🟠 **Versiune model ↔ work/cost/date** (§8): versionarea P1 nu e legată de lucrări.

---

## 5. WHAT IS DUPLICATED / DRIFT RISK
- 🟠 **Identitate activ**: `property_assets` (SSOT) vs `twins.assets[]` — P1 a introdus `asset_ref` (link opțional), dar NU e populat + fără UI. Drift latent.
- 🟠 **Room/Space**: doar în `twins.rooms[]`; `/spaces` P1 le expune, dar nu au reprezentare în KG și nu sunt referite de modelele 3D.
- 🟠 **Două suprafețe operator** `OperatorTwin`(2D) vs `OperatorDigitalTwin`(3D): NU duplicate (straturi diferite) — clarificat prin comentarii P1.
- 🟠 **property_id pe model**: P1 îl copiază din proiect, dar proiectele au null → propagă nul.

---

## 6. WHAT MUST NOT BE TOUCHED (protejat)
Motor House Health / PVI / Maturity; colecțiile `twins` & `digital_twin_projects` (fără migrare/ștergere/redenumire); entitlements/Stripe/`hh_plans`; Auth; Demo/Client Beta/Specialist Beta; operator workflow existent; modelul comercial actual; viewer 3D + Trimble.

---

## 7. WHAT CAN BE BUILT NON-BREAKING
1. Setarea `project.property_id` la creare din proprietate (link 3D↔property) + backfill opțional.
2. Extinderea KG cu node-types Twin + scrierea muchiilor din P1 (asset_ref, related_model_id/room_id) via `kg.link()`.
3. Lărgirea `digital_twin_qa._build_context` cu Property DNA + documente + works (evidence-grounded, read-only).
4. `completeness`/`confidence` pe `digital_twin_models` (reutilizând Trust Model 015) fără sistem de maturitate paralel.
5. Catalog produse partener + ofertă pe „need" reutilizând mecanica `marketplace_offers`.
6. Legarea versiunilor de model de works/date/cost prin `activity_events` + KG.

## 8. WHAT SHOULD BECOME CANONICAL
- **Property DNA** = contractul canonic de citire al proprietății (motoarele AI consumă DNA, nu structura fizică — deja e principiul declarat).
- **`entity_links` (KG)** = sursa canonică a RELAȚIILOR (nu FK-uri împrăștiate).
- **Trust Model 015** = vocabular canonic de încredere pentru ORICE dată (asset, atribut, model, instalație).
- **`property_assets`** = SSOT identitate activ; `twins.assets` = poziționare.
- **Maturity L0–L5 + PVI** = axele canonice de maturitate a proprietății.

---

## READINESS SCORECARD (§19 — fiecare procent justificat de cod)
| # | Capacitate | Readiness | Evidence |
|---|---|---|---|
|1|Model AI-assisted orientativ|**~5%**|0 generator 3D; doar Trust Model pt etichetare|
|2|Upload model profesional|**~85%**|Upload+conversie+metadata+versionare+storage (P1); lipsă IFC/RVT + link property|
|3|Model profesional prin specialist|**~45%**|Operator upload + membru specialist + source/uploaded_by; lipsă flux comandă→livrare→alocare|
|4|Vedere 2D + 3D|**~60%**|Ambele viewere reale; NU sunt conectate (property_id 3D lipsă)|
|5|Conectare model↔camere/active/docs/works|**~30%**|FK-uri P1 + `/spaces` + KG infra; 0/41 modele legate, fără UI, fără muchii KG|
|6|Versiuni + istoric|**~50%**|P1 versioning/supersedes + pvi_history + timeline; nelegat de works/cost|
|7|House Health conectat|**~65%**|`enrich_on_closure`+PVI data-driven; lipsă health pe cameră/activ|
|8|Twin pentru proiecte/renovări|**~55%**|requests+offers+escrow+enrich; lipsă „start project din spațiu"|
|9|Oferte de la City Partners|**~25%**|CRM parteneri + fee-engine; fără catalog/ofertă pe Twin|
|10|Rezultat comercial→doc+istoric|**~55%**|Buclă works completă; buclă produse absentă|
**Overall (ponderat):** ~40–45% din viziunea evolutivă completă; fundații foarte solide, verigi lipsă: link 3D↔property, AI-3D, product commerce contextual.

---

## AI 3D FEASIBILITY (§2)
🔵 Fezabil doar ca modul NOU (nu există nimic). 🟡 Recomandare: model AI = generator EXTERN (LLM/servicii 3D) care produce GLB orientativ, stocat ca `digital_twin_models` cu `source="ai_generated"`, `confidence="inferred"`, `completeness<100`, `visibility=internal`. 100% NU se atinge automat — doar prin `verification_status="verified"` (Trust Model 015) după specialist. Reutilizează integral P1 + Trust Model. Complexitate mare (generare 3D reală), risc mediu (așteptări client). NU necesită sistem de maturitate nou.

## TYPOLOGY FEASIBILITY (§4)
🔵 Neconstruit. 🟡 Fezabil peste `twins.rooms/plans` + un catalog `typologies` (nou) + parametrizare (surface/rooms). Avantaj competitiv real pentru ansambluri repetitive, DAR necesită seed de tipologii + motor de adaptare — NU e trivial. Recomandare: P3+, după ce link-ul 3D↔property e rezolvat.

## PROFESSIONAL MODEL WORKFLOW (§5)
🟢 Parțial gata (upload+versionare+operator). 🟡 Lipsește: acceptare IFC/RVT (P4), flux „comandă serviciu → specialist livrează → operator încarcă → alocă proprietății/clientului" ca stare urmăribilă. Reutilizabil: `requests` + `marketplace_offers` + operator router DT.

## PROPERTY KNOWLEDGE LAYER (§10)
🟢 EXISTĂ ca `property_dna` (nu se confundă cu Knowledge Center admin/`kg.py`). 🟡 De extins: alimentează AI Q&A din DNA; scrie muchiile Twin în KG; expune un „knowledge per property" client-facing.

## HOUSE HEALTH CONNECTION (§9)
🟢 Conectat prin Value Loop (data-driven, fără hard-code după P1). 🟡 De adăugat: semnale de sănătate pe cameră/activ/model, fără a atinge motorul.

## CITY PARTNER / COMMERCE POTENTIAL (§11–12)
🟡 Mecanica există (fee/ranking/sponsored + CRM + portal). 🔵 Lipsește stratul „produs↔spațiu↔ofertă↔execuție↔istoric". Bucla se poate închide reutilizând `marketplace_offers` + `enrich_on_closure`.

## BUSINESS MODEL OPTIONS (§13–14) — doar analiză
Fezabile FĂRĂ redesign major (pattern-uri deja în cod): A fee/lead 🟢, B fee/contact 🟢, E featured/sponsored 🟢 (marketplace_offers), D subscription partener 🟢 (hh_subscriptions). C commission % 🟡 (necesită tracking valoare contract). Digital Twin: A inclus în abonament 🟢, C AI-3D advanced PREMIUM 🟢 (entitlements există), D/E/F professional services ca serviciu 🟡 (necesită flux §5).

## ARCHITECTURE RECOMMENDATION (adaptată la cod real)
```
PROPERTY (properties)                      ← SSOT identitate
 └─ PROPERTY DNA (property_dna)            ← contract canonic de citire  🟢
     ├─ HOUSE HEALTH / PVI / Maturity      ← value_loop + property_intelligence 🟢
     ├─ PROPERTY TWIN
     │    ├─ 2D (twins: rooms/assets)      🟢  ← ancoră Room/Space + asset positioning
     │    └─ 3D (digital_twin_projects)    🟢  ⚠️ trebuie legat prin property_id
     │         └─ models (versionate P1) + [ai_generated | uploaded | professional]
     ├─ KNOWLEDGE GRAPH (entity_links)     🟢  ← RELAȚIILE canonice (de extins cu Twin nodes)
     ├─ DOCUMENTS (property_documents)     🟢  ← related_model_id/room_id (P1)
     ├─ WORKS (requests + value_loop)      🟢  ← enrich_on_closure → History
     └─ COMMERCE
          ├─ SPECIALISTS (marketplace_offers) 🟢
          └─ CITY PARTNERS (+ products/offers) 🟡🔵
```
NU crea sisteme paralele. Canonizează DNA + KG + Trust Model.

## RISKS
- Legarea retroactivă 3D↔property (0/40) fără UI clară → confuzie proprietar.
- Așteptări AI-3D („arată real") vs orientativ → nevoie de etichetare fermă (Trust Model).
- FK-uri P1 + KG paralele → dublă sursă de adevăr pentru relații dacă nu se canonizează KG.
- Product commerce contextual poate „umfla" scope-ul spre home-design software (contra viziunii).

## NON-BREAKING ROADMAP (fără implementare acum)
- **P0 (consolidare)**: setează `project.property_id` la creare + backfill; scrie muchiile P1 (asset/model/room) în KG; canonizează DNA/KG/Trust Model. *Valoare mare, risc mic, dependențe zero.*
- **P1 (aproape gata)**: unificare UX 2D+3D pe aceeași proprietate; AI Q&A extins cu DNA/docs/works. *Risc mic.*
- **P2 (AI-assisted 3D / UX / Knowledge)**: generator GLB orientativ (source=ai_generated, confidence=inferred, completeness); „knowledge per property" client. *Risc mediu, valoare mare.*
- **P3 (Specialist workflow + validare)**: flux comandă→livrare→validare (verified→L5); versiune↔work/cost/istoric vizual; tipologii. *Risc mediu.*
- **P4 (Partner commerce)**: catalog produse partener + ofertă pe need/spațiu + închiderea buclei în History (reutilizează marketplace fee-engine). *Risc mediu-mare.*
- **P5 (BIM/IFC + instalații)**: acceptare `.ifc/.rvt/.dwg` (stocare/atașare/download) + straturi instalații cu status inferred→verified. *Complex, P4/P5.*

## EXACT NEXT DECISION(S) REQUIRED FROM OWNER
1. **P0 link 3D↔property**: aprobi consolidarea non-breaking (setare property_id + backfill + muchii KG) ca prim pas obligatoriu înainte de orice altă etapă?
2. **KG canonic**: relațiile Twin devin canonice în `entity_links` (nu FK-uri împrăștiate)?
3. **AI-3D**: îl tratăm ca generator EXTERN producând GLB orientativ etichetat (Trust Model), fără motor nou de maturitate — DA/NU?
4. **Ordinea**: mergem strict P0→P1→P2→P3→P4→P5, sau prioritizezi comerțul partener (P4) mai devreme?
5. **AI Q&A**: extindem contextul cu Property DNA + documente + works acum (P1), ca AI-ul să răspundă pe dovezi reale?
```
STOP — audit livrat. Zero cod modificat. BUILD doar după aprobarea explicită.
```
