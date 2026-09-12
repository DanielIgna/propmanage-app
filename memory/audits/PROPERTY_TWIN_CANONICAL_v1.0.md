# PROPERTY TWIN — DOCUMENT CANONIC (v1.0)

**Artifact Type**: DOCUMENT (canonic, living)
**Owner**: Fondator (danieligna1@gmail.com)
**Status**: CANONICAL — sursa unică de adevăr pentru taxonomia + starea + direcția Property Twin
**Data**: 28 Aug 2026
**Rol**: Reconciliază confuzia 2D/3D/Property Twin și consemnează starea REALĂ după P0 + P1 + P0.1. Reflectă CODUL (dacă apare divergență, codul are prioritate).
**Surse de evidență (NU se dublează aici)**:
- Feasibility & discovery: `audits/STRATEGIC_AUDIT_PROPERTY_TWIN_2026-08-28.md` (READ-ONLY audit datat)
- Build P1: `audits/DIGITAL_TWIN_P1_CONSOLIDATION_2026-08-27.md`
- Forensic anterior: `audits/DIGITAL_TWIN_PROPERTY_MODEL_AUDIT_2026-08-27.md`, `DIGITAL_TWIN_FORENSIC_AUDIT_2026-08-27_v2.md`
- Teste: `backend/tests/test_dt_p0_property_anchor_iter201.py`, `test_dt_p1_unified_iter202.py`, `test_dt_p01_operator_anchor_iter203.py`

---

## 1. TAXONOMIA CANONICĂ — „Property Twin" = umbrelă, NU două produse

**PROPERTY = ancora identității.** Totul se leagă de `property_id`.

**PROPERTY TWIN** este umbrela conceptuală pentru **două reprezentări complementare ale ACELEIAȘI proprietăți**:

| Strat | Colecții | Conținut | Cod | Viewer FE |
|---|---|---|---|---|
| **A · Digital Twin 2D** | `twins` | floorplan, rooms/spaces (uuid stabil), geometrie 2D, assets poziționate, info structurală | `routes/operator_twins.py` (`/api/properties/{id}/twin`, `/spaces`) | `ClientTwinViewer.jsx` (`ClientTwin2DPanel`) |
| **B · Digital Twin 3D** | `digital_twin_projects`, `digital_twin_models`, `digital_twin_plans`, `digital_twin_pins` | GLB/GLTF/SKP, layere 3D, X-Ray, measurements, pins, Trimble/SketchUp, professional models | `routes/digital_twin.py` (`/api/digital-twin/*`, +operator +admin) | `DigitalTwinViewer.jsx` (react-three-fiber) |

**REGULĂ CANONICĂ (decizie Fondator):**
- `twins` (2D) și `digital_twin_projects` (3D) **NU sunt duplicate**, **NU sunt LEGACY**, **NU se migrează, NU se șterg, NU se redenumesc, NU se consolidează**. Sunt cele două straturi ale aceluiași Property Twin.
- Orice document anterior care marchează `twins` ca „LEGACY / candidat de migrare în digital_twin_projects / candidat de consolidare storage" este **DEPRECAT** de acest document canonic.
- UI-ul unificat (`PropertyTwinModal` în `ClientTwinViewer.jsx`) prezintă cele două straturi ca taburi `[Structură 2D]` / `[Model 3D]` pe aceeași proprietate.

---

## 2. STARE LIVRATĂ (DELIVERED / VALIDATED IN PREVIEW)

> **PRODUCTION-VALIDATED (28 Aug 2026).** Toate cele de mai jos sunt implementate, validate în PREVIEW (15/15 teste) ȘI validate LIVE pe `propmanage.ro` (**22/22 live checks PASS** + KG edges confirmate). **PRODUCTION-COMPLETE.**

### P0 — PROPERTY ANCHOR · PRODUCTION-VALIDATED (28 Aug 2026, live 22/22)
Leagă stratul 3D (anterior orfan: 0/40 proiecte aveau `property_id`) de proprietate.
- `create_project` (client) + `operator_create_project_for_client` acceptă/validează `property_id` cu **anti-misassignment** (`_resolve_property_anchor`, owner-verified) → `property_link_status` (linked / unresolved).
- Modelele moștenesc `property_id` + status la upload.
- `PATCH /api/digital-twin/projects/{id}/property` — ancorează manual un proiect unresolved + cascadează pe modele (non-destructiv).
- **KG**: muchii semantice `property -has_twin_project-> twin_project` și `-has_twin_model-> twin_model` via `kg.link()` (FK păstrat pentru integritate; KG = traversare).
- **Backfill SAFE (admin)**: `POST /api/admin/digital-twin/backfill-property-links` — idempotent, **ZERO auto-assignment** (proiectele fără corespondent determinist → `unresolved`).
- **Trust/provenance readiness** pe modele: `confidence` (inferred/documented/verified) + `verification_status` (owner_declared/official_document/professional_audit/verified) + `completeness` (0–100). Vocabular pregătit pentru AI-3D/import FĂRĂ maturity nou.
- **FE client**: selector „Proprietate" în modalul de creare.
- **Testare**: `test_dt_p0_property_anchor_iter201.py` — 4/4 PASS (ancorare, anti-misassignment 403/404, backfill zero auto-assign, moștenire + trust).
- **NU s-a atins**: motorul House Health/PVI/Maturity, Property DNA, Auth, Stripe, entitlements, Demo/Beta.

### P1 — EXPERIENȚA UNIFICATĂ PROPERTY DIGITAL TWIN · PRODUCTION-VALIDATED (28 Aug 2026, live 22/22)
Unifică straturile 2D + 3D sub o singură experiență centrată pe proprietate.
- `GET /api/properties/{id}/digital-twin` — overview unificat: `twin_2d {exists,status,rooms_count,assets_count,project_id}` + `twin_3d {exists,has_model,projects[{id,name,model_url,models_count,property_link_status,updated_at}]}`. Authz oglindește `/twin` + `/spaces` (owner OR admin/operator OR specialist asignat).
- `GET /api/digital-twin/projects?property_id=...` — filtru pe proprietate (răspuns cheie `items`). Fără filtru = backward-compatible.
- **FE**: `PropertyTwinModal` (în `ClientTwinViewer.jsx`) cu taburi `[Structură 2D]` / `[Model 3D]`, înlocuind UI-ul fragmentat din `SettingsPanel.jsx`. `ViewerErrorBoundary` menține modalul viu la un GLB placeholder/corupt (fallback grațios, fără runtime overlay).
- P1 anterior (consolidare metadata): ProfessionalModel metadata/versionare (`supersedes` non-destructiv), `asset_ref`, docs `related_model_id/related_room_id`, `/spaces`, gate `ingest ≠ PREMIUM`, storage → Object Storage. Vezi `DIGITAL_TWIN_P1_CONSOLIDATION_2026-08-27.md`.
- **Testare**: `test_dt_p1_unified_iter202.py` — 6/6 PASS (overview shape+values, authz 403/404, filtru property_id, backward-compat, regresie `/twin` + `/spaces`).

### P0.1 — OPERATOR PROPERTY ANCHOR · PRODUCTION-VALIDATED (28 Aug 2026, live 22/22)
Elimină ultima sursă de orfanare: fluxul OPERATOR de creare Digital Twin nu avea selector de proprietate în UI.
- **Backend** (`digital_twin.py`): `property_id` devine **OBLIGATORIU** pe endpoint-ul operator (`POST /api/operator/digital-twin/clients/{id}/projects`) → 400 dacă lipsește. Ancorarea reutilizează integral P0 (`_resolve_property_anchor(owner_id=client_id)` anti-misassignment + KG + moștenire modele). Fluxul CLIENT rămâne neschimbat (standalone permis).
- **Backend NOU (read-only)**: `GET /api/operator/digital-twin/clients/{id}/properties` — listează proprietățile clientului pentru selector (reutilizează `db.properties` SSOT, NU creează sistem nou de identitate/linking).
- **FE** (`OperatorDigitalTwin.jsx` · `CreateProjectModal`): selector `[Proprietate ▼]` (Property Anchor) sus în modal; submit dezactivat până la selecție; mesaj când clientul nu are proprietăți.
- **Testare**: `test_dt_p01_operator_anchor_iter203.py` — 5/5 PASS (selector endpoint, create fără property → 400, create cu property → linked + moștenire, property neautorizat → 403/404, regresie client standalone). Regresie totală P0+P1+P0.1: **15/15 PASS**.
- **NU s-a construit** sistem de roluri operator/specialist (rămâne FUTURE PROFESSIONAL WORKFLOW, §6).

---

## 3. PRINCIPII CANONICE DE DATE (neschimbate — reafirmate)

| Concept | Rol canonic | Implementare |
|---|---|---|
| **PROPERTY** | Ancora identității | `properties` (SSOT) |
| **Property DNA** | Knowledge/read model al proprietății (motoarele AI citesc DNA, nu structura fizică) | `property_dna.py` (`GET /api/properties/{id}/dna`) |
| **entity_links / KG** | Relațiile canonice (semantice) | `kg/links.py`, `entity_links` |
| **property_assets** | SSOT identitate activ (ONE ASSET IDENTITY + MULTIPLE CONTEXTS) | `property_assets`; `twins.assets[].asset_ref` = poziționare/link opțional |
| **Trust Model 015** | Provenance + confidence + verification pentru ORICE dată | `source` / `confidence` / `verification_status` |
| **Maturity L0–L5 + PVI** | Axele canonice de maturitate a proprietății | `property_intelligence.py`, `pvi_history` |
| **House Health / Value Loop** | Motor existent — NU se reconstruiește | `value_loop.enrich_on_closure`, House Health engine |
| **Digital Twin (2D+3D)** | Reprezentarea spațială/structurală + strat operațional al proprietății | vezi §1 |
| **Professional Model** | Sursă profesională: uploaded / ai-generated / operator-created / specialist-created / specialist-validated — FĂRĂ sistem paralel de maturitate | `digital_twin_models` (metadata P1 + Trust Model) |

---

## 4. LIMITA TRUST / PROFESIONAL (obligatoriu)

**PropManage NU construiește software CAD/BIM profesional și NU pretinde să înlocuiască arhitectul/specialistul.**

Progresie de încredere a unui model (fără maturitate paralelă, reutilizează Trust Model 015):

```
INFERRED  →  DOCUMENTED  →  PROFESSIONAL REVIEW  →  VERIFIED
```

Un model **AI-generated / AI-assisted** poate fi: orientativ, estimativ, `inferred`, util pentru explorare, documentare, pregătirea unei intervenții, comunicarea client↔specialist.

Un astfel de model **NU** trebuie prezentat ca: plan tehnic autorizat · documentație de execuție · ridicare profesională certificată · BIM profesional verificat · traseu de instalații confirmat · măsurătoare profesională (dacă sursa nu e profesională).

**AI-ul nu setează niciodată `verified` automat.** `verified` se obține DOAR prin validare profesională (specialist/arhitect/inginer/inspector, roluri viitoare).

---

## 5. DIRECȚIE VIITOARE — DOCUMENTATĂ, NU IMPLEMENTATĂ

> Următoarele sunt direcții de produs consemnate ca principii de arhitectură extensibilă. **NU sunt implementate.** Nimic din arhitectura actuală nu le blochează. Nu se pornește niciun BUILD fără aprobare explicită Fondator.

### 5.1 AI-3D — AI-ASSISTED PROPERTY MODEL (nu simplu generator de imagini)
Un model de **date + geometrie** care evoluează progresiv pe măsură ce primește input:
- **Inputuri posibile (păstrate în arhitectură)**: plan 2D cu cote · PDF/imagine plan · JPG/PNG design · scanare LiDAR / room scan telefon · fotografii · documente de măsurare · model profesional (arhitect/designer) · alte surse vizuale compatibile.
- **Capacități viitoare**: interpretare plan → identificare camere/spații → extragere geometrie → generare reprezentare 3D → GLB/GLTF → păstrare sursă/confidence/completeness/versiuni/istoric → legare la Property + camere + active → intervenție ulterioară a specialistului.
- **Recomandare tehnică (din audit)**: generator EXTERN (LLM / servicii 3D) → GLB orientativ stocat ca `digital_twin_models` cu `source="ai_generated"`, `confidence="inferred"`, `completeness<100`, `visibility=internal`. Reutilizează integral P1 + Trust Model. FĂRĂ motor de maturitate nou.

### 5.2 PROFESSIONAL HANDOFF (extensibilitate păstrată)
```
Client / date existente → AI-assisted (draft orientativ) → Operator → Specialist/Arhitect
   → corecții → validare → VERIFIED Professional Model → parte din Property Twin
```
Roluri viitoare posibile: arhitect · designer · inginer · specialist instalații · validator · inspector. Formate profesionale viitoare: GLB · SKP · IFC · RVT · DWG/DXF. PropManage poate stoca/atașa rezultatele fără a deveni CAD. **Rolurile NU se implementează acum.**

### 5.3 DESIGN AI (strat de explorare peste Twin)
După existența unui Twin 3D: concepte de design, stiluri, finisaje, materiale, texturi, mobilier, variante de amenajare — **legate de model + camere/spații**, nu imagini independente. **Design AI ≠ Professional CAD.**

### 5.4 AI KNOWLEDGE LAYER (Q&A pe dovezi)
AI Q&A extins progresiv cu: Property DNA · Twin · camere/spații · active · documente · lucrări · istoric · maintenance · PVI · Health · relații KG. AI-ul răspunde DOAR pe baza datelor disponibile, indică incertitudinea, **NU inventează** cote/materiale/trasee. (Azi `digital_twin_qa._build_context` citește doar geometria Twin — extindere viitoare.)

### 5.5 PROPERTY HISTORY (Twin = obiect istoric evolutiv)
```
Model v1 → v2 → renovare → model actualizat → instalații → lucrări → documente → costuri → specialist → validare
```
Twin-ul nu este doar un viewer 3D; este reprezentarea evolutivă a proprietății (reutilizează versioning P1 + `pvi_history` + `activity_events` + DNA timeline; legare viitoare versiune↔work/cost/dată).

### 5.6 PARTNER / COMMERCE ECOSYSTEM (doar direcție)
```
Property Twin → Room/Space → Need → Product/Service → City Partner → Offer → Execution → Documentation → Twin history
```
Exemplu: „60 mp gresie + 90 mp parchet + o canapea" → nevoia/contextul spațiului → City Partner vede cererea (reguli comerciale) → produse/ofertă → fee/comision/sponsored (model comercial decis ulterior). Reutilizează mecanica `marketplace_offers` (fee/ranking/sponsored) + `city_partners` + `enrich_on_closure`. **NU se implementează catalogul; NU se modifică marketplace-ul existent.**

### 5.7 SUBSCRIPTION / PRODUCT VISION
Digital Twin = **componentă de valoare a abonamentului** (nu exclusiv serviciu profesional plătit separat). Clientul își construiește progresiv proprietatea digitală: încarcă documente → vede planul → vede Twin-ul → primește model orientativ → urmărește evoluția → păstrează istoric → adaugă lucrări/active → folosește AI → cere validare profesională → explorează produse/servicii. Serviciile profesionale pot exista PESTE această fundație.

### 5.8 FUTURE PROFESSIONAL WORKFLOW (Operator → roluri)
Aripa Operator va evolua către un sistem bazat pe roluri (Operator · Arhitect · Specialist · Validator · Inspector · Designer). Backend-ul P0/P0.1 este deja pregătit pentru property anchoring. **Lipsa unui sistem de roluri NU e un blocker arhitectural acum** — este FUTURE PROFESSIONAL WORKFLOW.

---

## 6. CE NU SE IMPLEMENTEAZĂ ACUM (backlog, gated de aprobare Fondator)
AI-3D generator · LiDAR pipeline · room scanning · image-to-3D · Design AI · product catalog · City Partner commerce · IFC/RVT viewer · BIM authoring · CAD editor · specialist/architect role system · advanced Operator architecture. Toate = documentate ca direcție, **ne-blocate** de arhitectura actuală.

---

## 7. RISKS
- **HIGH**: niciunul introdus de P0/P1/P0.1 (15/15 teste PASS, zero regresii pe module protejate).
- **MEDIUM**: (1) așteptări AI-3D „arată real" vs orientativ → etichetare fermă Trust Model (mitigat prin vocabular deja livrat; devine relevant doar la BUILD AI-3D). (2) FK-uri P1 + KG paralele → dublă sursă pentru relații dacă KG nu e canonizat (mitigat: KG declarat canonic aici; FK păstrat doar pentru integritate). (3) proiecte 3D `unresolved` istorice (40, artefacte demo) — rămân neatribuite prin regula ZERO auto-assign; se pot ancora manual via PATCH.
- **Mod de lucru**: BUILD → TEST → DOCUMENT → STOP. Fără audit-loop. La orice schimbare HIGH/MEDIUM reală → STOP + raport Fondator.

---

## 8. PRODUCTION READINESS — PRODUCTION-COMPLETE (28 Aug 2026)
- **P0 + P1 + P0.1**: implementate, validate în PREVIEW (15/15) ȘI validate LIVE pe `propmanage.ro` → **PRODUCTION-COMPLETE**.
- **LIVE VALIDATION (22/22 PASS)**, script `backend/tests/live_validate_prod_dt.py`:
  - **P0**: create Twin ancorat → `property_id` corect + `linked`; model moștenește `property_id` + trust (confidence=documented, verification_status=owner_declared); anti-misassignment bogus → 404; **KG** `property -has_twin_project-> twin_project` + `-has_twin_model-> twin_model` confirmate live (admin `/api/admin/kg/entity/property/{id}`).
  - **P0.1**: selector operator (`GET /clients/{id}/properties` → 10 proprietăți); create fără property → 400; cu property → `linked` + moștenire model; property neautorizat → 404.
  - **P1**: overview unificat (`twin_2d` approved 5 camere/4 assets + `twin_3d`); filtru `?property_id`; regresie `/twin` + `/spaces` (count=5); authz bogus → 404.
  - **Property DNA** intact (dna_completeness, capabilities, pvi, timeline); **regresie**: Auth (client/operator/admin 200), entitlements (tier=FREE), House Health plans + dashboard, Stripe pricing source — toate OK.
- **Notă LOW (data hygiene, pre-existent)**: ștergerea unui proiect NU curăță muchiile KG (append-only traversal; FK separat) → muchii KG „dangling" către proiecte șterse. Comportament pre-existent, NU regresie P0.1; de curățat eventual într-un job de mentenanță (backlog).


---

## 9. NEXT STAGE I / II / III — DELIVERED IN PREVIEW (Knowledge Sync · Iun 2026)

> **CLASIFICARE STRICTĂ DE STARE.** Tot ce urmează este **BUILT & DELIVERED IN PREVIEW**, validat prin `testing_agent` + curl E2E, cu **regresie intactă** pe funcțiile anterioare. **NU este DEPLOYED în producție** — necesită **redeploy explicit de către Fondator** pentru a ajunge LIVE pe `propmanage.ro`. Doar P0/P1/P0.1 (Property Anchor, §2) sunt PRODUCTION-LIVE. NU confunda PREVIEW cu PRODUCTION. NU confunda BUILT cu DEPLOYED.
>
> Sursa de adevăr rămâne CODUL. Acest capitol consolidează, pentru continuitate, funcționalitățile construite incremental (non-breaking, fără rebuild) peste fundația Digital Twin 3D.

### 9.1 INVENTAR FUNCȚIONALITĂȚI LIVRATE (grupate pe etape)

**NEXT STAGE I — Fundația 3D + AI orientativ + Q&A + ancorare + mobil**
1. **Upload 3D multi-format (Client)**: `.skp` · `.dae` · `.obj` · `.fbx` · `.stl` · `.ply` · `.glb` · `.gltf`, cu progres și polling conversie unde e cazul. (⚠️ vezi §9.6 limitarea `.skp`.)
2. **AI-3D orientativ / inferred**: model AI generat, marcat clar „Orientativ AI · neverificat"; nu înlocuiește modelul profesional; viewer + flux Operator. Dacă proiectul nu e ancorat corect, endpoint-ul returnează **400** (nu inventează asocierea).
3. **Property Q&A (grounded)**: chat în viewer; răspunsuri STRICT pe dovezile reale ale proprietății (DNA / documente / lucrări); fără halucinații; în română.
4. **Ancorare istorică**: proiectele vechi se ancorează MANUAL; **ZERO auto-assign**; o proprietate = un singur owner; integritatea proprietății respectată.
5. **Mobile Demo 3D**: responsive la 390/375px, fără overflow orizontal, controale touch; desktop neafectat.

**NEXT STAGE II — Design AI + validare + sugestii + ancorare în masă + reziliență + comparație + ofertă + notificare + materiale**
6. **AI Design Concepts**: wizard (stil + buget + materiale) → paletă + plan materiale + buget ESTIMATIV + render AI (infra Gemini Nano Banana / Emergent LLM) + strat 3D colorat orientativ. Rezultate marcate „Orientativ AI · neverificat".
7. **Validare profesională**: `inferred → în validare → verified`, tranziție DOAR prin acțiune explicită a profesionistului; istoric păstrat; coadă de validare în Operator.
8. **Q&A Suggestions**: sugestii generate STRICT din dovezile reale ale proprietății (pipeline grounded).
9. **Ancorare în masă (bulk anchoring)**: multi-select DOAR între proiecte ale ACELUIAȘI owner; preview obligatoriu; confirmare explicită; **ZERO auto-assign**; ancorarea individuală rămâne disponibilă.
10. **ViewerErrorBoundary**: un model 3D defect NU prăbușește ruta (fallback grațios).
11. **Comparație Concepte AI**: două concepte side-by-side (render, stil, paletă, materiale, buget estimativ, plan, status validare); responsive mobil. Componentă `ConceptComparison.jsx`.
12. **Ofertă din Concept Validat**: concept `verified` → cerere REALĂ în `db.requests` (fluxul marketplace existent), precompletată cu proprietate + buget + materiale; confirmare explicită client. `POST /api/digital-twin/design-concepts/{cid}/request-offer` (guard: 400 dacă neverificat / fără confirm; idempotent). Testat iter207 (95%) → fix UX → iter208 (100%).
13. **Notificare Validare**: la `confirm`/`reject`, proprietarul e notificat automat (in-app + email prin `notify()`), cu motivul respingerii când există. Se notifică și cel care a cerut validarea (dacă diferă).
14. **Materiale reale + preț orientativ**: materialele conceptului se mapează la produse reale din catalogul City Partners; fallback pe prețuri reale de piață (`price_observations`); dacă nu există potrivire → **„preț orientativ indisponibil"**. `GET /api/digital-twin/design-concepts/{cid}/materials`. **ZERO produse/prețuri inventate.**

**NEXT STAGE III — Catalog admin + câștigător + concept public + ofertă cu poze** (build unic, testat iter209 Feature 1/2/3 = 100% + iter210 Feature 4 vizual = 100%)
15. **Catalog Materiale (admin)**: pagină `/admin/city-partner-products` (super-admin), CRUD complet (nume, brand, categorie, unitate, preț min/max, monedă, tag-uri, link, partener City Partner, activ). Catalog **GOL implicit**. Backend `products_admin_router` (`/api/admin/city-partner-products`), colecție `city_partner_products`. Feature #14 preferă acum produsul de partener, cu fallback pe piață.
16. **Alegere Câștigătoare**: `PreferButton` (⭐ „Alege ca preferat") în comparație/studio; **single-winner impus server-side** (`POST /api/digital-twin/projects/{pid}/design-concepts/{cid}/prefer`); pentru concept `verified`, buton combinat „Alege și cere ofertă" (prefer + ofertă, cu O confirmare — NU zero-tap, decizie de siguranță).
17. **Concept în Pașaport**: toggle confidențialitate `show_design_concept` (**opt-in, implicit OFF**); doar conceptele `verified` apar pe pașaportul public `/p/{slug}`; poartă de siguranță verificată (OFF → `design_concept=None` + render **404**). Render public: `GET /api/public/passport/{slug}/design-concept-render`.
18. **Ofertă cu Poze**: la „Cere ofertă", render-ul AI al conceptului se atașează automat cererii (`concept_render_url`, `dt_concept_render_path`); specialistul îl vede în lead (`SpecialistDashboard`, thumbnail 1408×768 confirmat vizual). Servit prin `GET /api/requests/{req_id}/concept-render` (auth, vizibil oricui poate vedea cererea).

### 9.2 FIȘIERE & ARTEFACTE CANONICE (Next Stage II/III)
- BE: `routes/digital_twin.py` (design concepts, materials, request-offer, prefer, notificări în `validate_model`), `routes/requests.py` (`/requests/{id}/concept-render`), `routes/property_passport.py` (`show_design_concept`, `design_concept` în payload public, render public), `routes/city_partners.py` (`products_admin_router`), `routes/register.py`.
- FE: `components/ConceptComparison.jsx` (comparație + `PreferButton` + `RequestOfferButton` + `ConceptMaterials`), `components/DesignConceptStudio.jsx`, `components/DigitalTwinViewer.jsx`, `pages/admin/CityPartnerProductsPage.jsx`, `pages/PublicPassportPage.jsx`, `pages/clientv2/PassportCard.jsx`, `pages/SpecialistDashboard.jsx`, `App.js`, `pages/admin/AdminLayoutMetronic.jsx`.
- Colecții noi: `city_partner_products` (goală). Câmpuri concept noi: `preferred`, `offer_request_id`. Câmpuri request noi: `source="digital_twin_concept"`, `concept_id`, `dt_project_id`, `dt_model_id`, `concept_render_url`, `dt_concept_render_path`.

### 9.3 REGULI CANONICE DE INTEGRITATE (reafirmate — obligatorii)
1. **AI ≠ verificare profesională**; `inferred ≠ verified`. Un model AI NU devine profesional prin simpla generare.
2. Numai **profesionistul** poate face tranziția explicită la `verified`. **AI-ul NU setează niciodată `verified` automat.**
3. **ZERO produse City Partners inventate.** **ZERO prețuri inventate.** Fără date reale → **„preț orientativ indisponibil"**.
4. **ZERO specialiști inventați.** **ZERO oferte false.**
5. **ZERO auto-assignment** pentru proprietăți/proiecte.
6. Cererea de ofertă din concept e permisă **DOAR** pentru concept `verified`.
7. O proprietate are **un singur owner**. Ancorarea în masă e limitată la proiectele **aceluiași owner**.
8. Acțiunile care produc schimbări reale (ofertă, ancorare) necesită **confirmare explicită**.
9. Q&A rămâne **grounded** în dovezile proprietății; indică incertitudinea; nu inventează cote/materiale/trasee.
10. Publicarea în Pașaport este **opt-in**; conceptul public trebuie să fie `verified`.
11. Nu transforma niciodată o estimare AI într-un fapt profesional.

### 9.4 DECIZIA CITY PARTNER PRODUCTS (arhitectură canonică)
- Catalog **administrat de super-admin**; produse **reale**, introduse manual; poate fi **gol inițial**.
- Un produs trebuie să aparțină (opțional) unui **City Partner real**; prețurile sunt cele introduse/confirmate de admin.
- Ordinea de rezolvare a prețului pentru un material de concept: **(a)** produs City Partner potrivit → **(b)** fallback pe benchmark-uri / prețuri reale de piață → **(c)** dacă nu există niciunul: **„preț orientativ indisponibil"**.
- Model comercial (fee/comision/sponsored/catalog complet) — **NEDECIS, direcție viitoare** (vezi §5.6). NU s-a modificat marketplace-ul existent.

### 9.5 FLUXUL STRATEGIC DE PRODUS (direcție — NU tot e implementat)
```
CONCEPT AI → VALIDARE PROFESIONALĂ → ALEGERE CLIENT → MATERIALE REALE → CERERE OFERTĂ
  → SPECIALIST VERIFICAT → EXECUȚIE → DOCUMENTARE → DIGITAL TWIN / PAȘAPORT
```
- Implementat până la **CERERE OFERTĂ** (+ atașare render, + concept în pașaport). **EXECUȚIE / DOCUMENTARE / bucla completă înapoi în Twin** = **direcție viitoare, NU implementată**.

### 9.6 KNOWN ISSUE — `.skp` / Trimble Connect (LIMITARE DE WORKFLOW, NU „fully supported")
- **Stare reală**: upload `.skp` **funcționează** (fișier stocat intact ca arhivă descărcabilă, `conversion_status="unsupported"`, fără crash / fără eroare roșie). UI: „SketchUp (doar descărcabil; exportă `.dae` pentru viewer)".
- **NU este vizualizabil 3D** server-side: nu există pipeline Blender/CloudConvert pentru `.skp` → `.glb` în infra curentă.
- **Trimble Connect**: interfața cere un URL valid Trimble Connect / SketchUp. Un link **Google Drive NU este** link Trimble Connect și este respins CORECT. Nu se confundă storage-ul Google Drive cu viewer-ul Trimble Connect/SketchUp; integrarea trebuie să valideze tipul corect de URL.
- **NU marca `.skp` ca „fully supported"** până când un fișier `.skp` real este încărcat ȘI poate fi efectiv vizualizat în Digital Twin.
- **Direcție de rezolvare (viitor)**: conversie reală `.skp` → format vizualizabil · SAU integrare validă Trimble Connect · SAU altă soluție tehnică robustă. (Vezi și `BUGS.md` BUG #005.)

### 9.7 STARE TESTARE (PREVIEW, NU PRODUCTION)
- Next Stage II: `testing_agent` iter207 (95%) → fix UX (offer-lock în studio) → **iter208 (100%)**; backend curl E2E.
- Next Stage III: **iter209 (Feature 1/2/3 = 100%)** + **iter210 (Feature 4 vizual = 100%)**; backend curl E2E (inclusiv poarta de siguranță pașaport OFF → 404); date de test curățate.
- Regresia Next Stage I + P0/P1/P0.1 = intactă. Rezultatele sunt din **PREVIEW** — NU reprezintă validare de producție.

### 9.8 NEXT ROADMAP — APROBAT CA DIRECȚIE, **NU IMPLEMENTAT**
> Următoarele NU sunt livrate. Se păstrează ca roadmap; nu le marca drept implementate.
- **A. Import Catalog** — import CSV/Excel pentru încărcarea în masă a produselor City Partners (azi doar CRUD manual).
- **B. Materiale în Ofertă** — lista de materiale + prețurile incluse STRUCTURAT (line-items/deviz) direct în cererea de ofertă (azi doar text liber în descriere).
- **C. Insignă Pașaport** — badge „Amenajare planificată" pentru conceptele validate (azi există secțiunea de concept, nu un badge dedicat).
- **D. Comparație partajabilă** — link prin care clientul trimite comparația a două concepte familiei/unui specialist pentru feedback/vot.
- **Nuanță F (un singur tap)**: „Alege și cere ofertă" e implementat cu **o confirmare** (decizie de siguranță). Varianta strict zero-tap NU e implementată.
- **J.** Orice extindere ulterioară trebuie să păstreze separarea **AI / verified**.

### 9.9 CONFLICT MARCAT PENTRU DECIZIE UMANĂ (governance)
- În directiva de sincronizare, lista „NEXT ACTION ITEMS — NU SUNT ÎNCĂ IMPLEMENTATE" (secțiunea 10 a mesajului) a inclus itemi care, conform CODULUI + testelor, sunt **DEJA LIVRAȚI ÎN PREVIEW**: „Alegerea câștigătorului din comparație" (#16), „Concept validat în Pașaport" (#17), „Notificare client la validare/respingere" (#13), „Materiale de la parteneri cu prețuri reale" (#14), parțial „Ofertă din concept cu un singur tap" (#12/#16, cu o confirmare). Am consemnat starea REALĂ pe baza codului (sursa de adevăr). **De confirmat de Fondator** dacă lista de roadmap trebuie redusă doar la itemii genuini rămași (A/B/C/D + nuanța zero-tap). NU s-a inventat nicio rezolvare — s-a reconciliat cu codul verificat.
