# PropManage — DIGITAL TWIN / PROFESSIONAL MODEL / PROPERTY KNOWLEDGE · FORENSIC AUDIT v2
Data: 27 Aug 2026 · read-only · ZERO modificări. Supersedează parțial auditul v1 (aceeași zi) cu **verificare în cod + date**.
Standard evidență: `VERIFIED IN CODE` · `PARTIALLY VERIFIED` · `DOCUMENTED NOT VERIFIED` · `NOT FOUND` · `DUPLICATED` · `LEGACY`.

---

## 1. EXECUTIVE SUMMARY
PropManage are DEJA fundația unui Digital Twin viu — pe DOUĂ straturi complementare, nu un singur „3D viewer":
- **Twin 2D structurat, client-facing** (`twins`, **74 docuri** în preview): camere cu ID stabil + geometrie `x/y/w/h`, active poziționate cu `room_id`. `VERIFIED IN CODE` (`operator_twins.py`, `ClientTwinViewer.jsx`).
- **Twin 3D profesional** (`digital_twin_projects` 29 + `models` 26 + `plans` 13 + `pins` 3): three.js + layere (structură/electric/plumbing/hvac) + X-ray + `trimble_embed_url` (SketchUp nativ) + conversie Blender. `VERIFIED IN CODE` (`digital_twin.py`, `DigitalTwinViewer.jsx`).

**Corectură majoră față de v1 și față de MASTER_PLATFORM_STATE**: `twins` NU e „LEGACY junk" — e stratul 2D client cel mai populat (74 docuri, cu geometrie și active poziționate). Eticheta „LEGACY" din governance e **prematură/înșelătoare**. `DUPLICATED` real e altundeva (vezi §5).

**Verdict pe ipoteza Founder**: „PropManage = strat digital care primește/organizează/versionează modelul profesional extern" — **FEZABIL, cu ~70% infrastructură deja existentă**. Lipsesc: metadate/versionare `ProfessionalModel`, referință camere cross-system, populare Property Knowledge Graph.

**Cea mai importantă concluzie pentru decizii**: din cele 6 întrebări din auditul v1, **doar 2–3 sunt decizii de business reale** (vizibilitate model, investiție IFC, gating upload). Restul (twins vs projects, Room/Space, Health↔Twin) sunt **aproape rezolvate de infrastructură** și cer mai mult arhitectură decât decizie de business. Vezi §26 + §31.

---

## 2. WHAT PROPManage ALREADY HAS (`VERIFIED IN CODE`)
Twin 2D (`twins`), Twin 3D (`digital_twin_projects`), viewer three.js + Trimble, conversie Blender/CloudConvert, upload cu layere, pini+issue-reports+comentarii, planuri 2D, operator workflow (queue/edit/validate/publish/notify), comandare profesională plătită (`verified_estate`), AI Twin Q&A, Twin Maturity L0–L5 + PVI, House Health + recomandări, documente versionate cu asocieri, object storage cu mirror, entitlement gating (PREMIUM), Property DNA + kg (schelet, gol).

## 3. WHAT IS ACTUALLY FUNCTIONAL (`VERIFIED IN CODE`)
- Twin 2D client: `GET /api/properties/{id}/twin` → rooms+assets; `ClientTwinViewer.jsx` desenează floorplan din `x/y/w/h`. Date reale: 74 twins.
- Twin 3D: proiecte + upload `.glb/.gltf` nativ; `.dae/.obj/.fbx/.stl/.ply`→`.glb` Blender; viewer three.js cu layere/X-ray/section-planes/capture; Trimble embed. 26 modele, 13 planuri.
- Operator: `operator_twins.py` — upsert rooms/assets, validate (approve/needs_revision), notify owner+specialiști, `twin_unlocked=true`.
- Comandare profesională: `verified_estate.py` — pachet `twin`/`bundle`, plată, gate publish pe `digital_twin_id`, trust A+ necesită twin+audit.
- AI QA: `digital_twin_qa.py` — context din modele+planuri+pini, refuză să inventeze.
- Storage: `storage_service.mirror_dt_file` → copie durabilă object storage (disc ephemeral).

## 4. WHAT IS PARTIAL / DISCONNECTED (`PARTIALLY VERIFIED`)
- **ProfessionalModel metadata/versionare**: `digital_twin_models` are DOAR `kind/ext/layer_*/uploaded_by/conversion_*`. **NU** `version`, `version_label`, `source`, `visibility`, `validation_status`, `publication_status`, `change_reason`, `superseded_by`, `professional`. `VERIFIED IN CODE` (schema upload). → versionare = DE FACTO (modele multiple) fără semantică.
- **Room/Space cross-system**: camerele au ID stabil DOAR în `twins.rooms[]`; documentele folosesc `room` = **string liber** (nu uuid); `digital_twin_pins`/`projects` NU referă room_id din `twins`. → ancoră comună DECONECTATĂ.
- **Docs ↔ Model**: `property_documents` NU are `related_model_id`/`model_version` (`NOT FOUND`). Documentele nu se pot lega de un model/versiune 3D.
- **Health ↔ Twin**: `value_loop.py` LEAGĂ lucrări→`structure_health/utilities_health/documents_health` (auto parțial), DAR `operator_twins.py:326` setează `structure_health=95` hard-coded și `properties.py:22` default `90`. → semnal sintetic care suprascrie datele reale.
- **Property Knowledge Graph**: `property_dna`=0, `kg`=0 docuri (preview) → schelet neactivat. `PARTIALLY VERIFIED` (rute există, date lipsesc).

## 5. WHAT IS DUPLICATED (`DUPLICATED`)
1. **Active în DOUĂ locuri**: `property_assets` (colecție; folosită de completeness/House Health) vs `twins.assets[]` (embedded, cu `room_id`+`x/y`+`condition`, folosit de twin 2D). **Aceleași active conceptual, două reprezentări** → drift real. `VERIFIED IN CODE + DATA`.
2. **Două pagini operator twin**: `OperatorTwin.jsx` (795? / legacy) vs `OperatorDigitalTwin.jsx` — Blueprint le marchează „dublura" (TD-10). `VERIFIED` (există ambele).
3. **Camere în multiple forme**: `twins.rooms[]` (uuid+geo) vs `documents.room` (string) vs `plans` (area_m2) vs `properties.rooms` (număr). `DUPLICATED` (reprezentări divergente).
4. NU sunt duplicate reale: `twins` (2D) vs `digital_twin_projects` (3D) — **modele diferite**, nu copii.

## 6. WHAT IS LEGACY (`LEGACY`)
- `OperatorTwin.jsx` — marcat legacy în Blueprint (dublură a `OperatorDigitalTwin`). Confirmat FE.
- `twins` marcat „LEGACY" în MASTER_PLATFORM_STATE — **CONTESTAT de dovezi**: 74 docuri active, client-facing. Recomand re-etichetare „2D structured twin (canonical layer)", NU legacy.

## 7. DIGITAL TWIN ARCHITECTURE TODAY (real, din cod)
```
PROPERTY (properties)
 ├─ twins (2D)  ── status/rooms[uuid,x,y,w,h]/assets[room_id,x,y,condition]/model_url  → ClientTwinViewer 2D
 └─ digital_twin_projects (3D) ── trimble_embed_url, model_url(.glb)
      ├─ digital_twin_models  (LAYERE: structure/electric/plumbing/hvac/decor; kind=model/source/archive)
      ├─ digital_twin_plans   (floorplan 2D, area_m2)
      ├─ digital_twin_pins    (spațial + issue-report + comments)  [doar 3 → subutilizat]
      └─ members[client|specialist|architect|viewer]
STORAGE: disc UPLOAD_ROOT (ephemeral) + object storage mirror (durabil)
GATE: /subscription → digital_twin_advanced (PREMIUM); admin/operator bypass
```

## 8. PROFESSIONAL MODEL ARCHITECTURE TODAY
- Distincție ORIGINAL→DERIVED **EXISTĂ parțial**: `kind` = `source`/`archive` (fișier original) vs `model` (vizualizabil); conversie → `.glb`; `model_url` = doar dacă vizualizabil. `PARTIALLY VERIFIED`.
- Trimble Connect (`trimble_embed_url`) = cale reală pentru SketchUp profesional. `VERIFIED`.
- **Lipsă**: entitate/metadate `ProfessionalModel` formală (versiune, sursă, creator profesional, vizibilitate, status publicare, notă versiune, superseded). `NOT FOUND`.

## 9. ROOM / SPACE ANALYSIS
`VERIFIED`: camere = obiecte embedded în `twins.rooms[]` cu `id`(uuid), `name`, `type`, `area`, `x/y/w/h`. Active `twins.assets[].room_id`. `NOT FOUND`: colecție globală `rooms`; referință room_id din documente/pini/projects.
**Verdict**: camerele EXISTĂ cu ID stabil, dar DOAR în stratul 2D. Nevoia reală = **a face `twins.rooms` ancora canonică** referențiată de docs/pins/works — mai mult arhitectură decât „entitate nouă de la zero".

## 10. OPERATOR WORKFLOW (`VERIFIED IN CODE`)
Poate: coadă, edit rooms/assets 2D, validate (approve/needs_revision), publish (`twin_unlocked`), notify owner+specialiști, upload modele (bypass owner). **Lipsă**: „attach professional model + set version + supersede old + publish 3D" ca flux unic (azi 2D `twins` și 3D `projects` sunt fluxuri separate).

## 11. CLIENT WORKFLOW (`VERIFIED`)
`GET /me/digital-twins` (status+progres), `request_twin_validation`, `ClientTwinViewer` (2D), upload propriu în proiect 3D, viewer 3D, TwinAIQA. **Lipsă**: UX „încarc modelul profesional primit de la arhitect" (format+procesare) ca experiență dedicată.

## 12. KNOWLEDGE CENTER AUDIT (`VERIFIED`)
`knowledge_center.py` = **explorer de documentație internă** (`/app/memory`+`/app/docs`), admin-only (`require_role("admin")`), endpoints tree/doc/search/registry/review/architecture. **NU e per-proprietate, NU e client-facing, NU are embeddings/retrieval AI pe date de proprietate.** → NU e Property Knowledge Layer.

## 13. PROPERTY KNOWLEDGE LAYER AUDIT
`PRODUCT_BLUEPRINT §12` definește „PROPERTY KNOWLEDGE GRAPH" ca avantaj strategic. Tehnic: `property_dna` + `kg` + `ai_brain/graph` există ca rute/colecții DAR **goale în preview** (`property_dna`=0, `kg`=0). `digital_twin_qa._build_context` deja asamblează un context per-proprietate (embrion real de knowledge layer). → `DOCUMENTED NOT VERIFIED` (schelet neactivat) + un embrion funcțional în AI QA.

## 14. DOCUMENTS / ASSETS / WORKS INTEGRATION (`VERIFIED`)
Documente: `room`(string), `related_asset_id`, `related_request_id`, `specialist_id`, `building_system`, `version/prev_version_id/history` — versionare + asocieri SOLIDE. Active: `property_assets` (colecție) **și** `twins.assets[]` (embedded) → DUPLICARE. Works: `requests` legate de proprietate/specialist; `value_loop` mapează works→health.

## 15. DIGITAL TWIN ↔ HEALTH / PVI / MATURITY
- Maturity L0–L5 + PVI: `property_intelligence.py` `VERIFIED`.
- `value_loop.py`: works→dimensiuni health `VERIFIED` (closed-loop PARȚIAL, real).
- `structure_health=95` (twin approve) și `=90` (creare proprietate) = **hard-coded sintetic** `VERIFIED` → suprascrie datele reale. Fix arhitectural: elimină override, lasă value_loop/twin să conducă.

## 16. AI TWIN Q&A AUDIT (`VERIFIED`)
`digital_twin_qa.py`: context din `digital_twin_models`+`plans`(rooms/area_m2)+`pins`(equipment/finishes). Prompt: „Never invent numbers, materials, or brands. Use ONLY context"; „If not in context → «Această informație nu este în Digital Twin-ul curent»". Nu citează sursă/trace explicit (spune tipul de dată, nu ID). `call_llm` via `ai_core.provider` (Emergent). → grounding CORECT; citare/trace = îmbunătățibil.

## 17. STORAGE / FILES / VERSIONING (`VERIFIED / PARTIALLY`)
- Fișiere model: disc `UPLOAD_ROOT/{project_id}/{stored_as}` (ephemeral la redeploy) + mirror object storage (`mirror_dt_file`) durabil. Risc: referințe pe `/api/digital-twin/files/...` (disc) vs object storage — posibile referințe rupte după redeploy dacă viewer-ul citește discul. `PARTIALLY VERIFIED`.
- Versionare model: DE FACTO (modele multiple/proiect) fără schema versiune/istoric „ce/când/de ce/cine". Documente: versionare reală (`prev_version_id/history`).

## 18. BIM / IFC / SKP / GLB STRATEGY (`VERIFIED`)
`ALLOWED_EXTS = {.glb,.gltf,.skp,.dae,.obj,.fbx,.stl,.ply}`. `.ifc` **NU e acceptat** (doar text în QA doc → `DOCUMENTED NOT VERIFIED`). `.dwg/.dxf/.rvt` `NOT FOUND`. SKP = download-only + Trimble embed (Blender nu-l suportă pe Linux — corect). 
Recomandare pragmatică: **A. Sursă originală stocată**: orice format profesional (skp/ifc/dwg/rvt) = păstrat ca fișier-sursă + link Trimble/download. **B. Convertit web**: glb/gltf (+ dae/obj/fbx/stl/ply via Blender). **C. Downloadable**: skp/ifc/dwg. **D. Viitor**: viewer IFC (decizie de business). **E. Rămâne afară**: authoring/editare CAD.

## 19. RESPONSIBILITY BOUNDARY — Professional vs PropManage vs AI (matrice obligatorie)
| Capability | Professional SW | PropManage | AI |
|---|---|---|---|
| Desen arhitectural / cote exacte | ✅ | ❌ | ❌ |
| Authoring BIM / model structural | ✅ | ❌ | ❌ |
| Trasee electrice/sanitare/HVAC (reale) | ✅ | ❌ | ❌ |
| Model 3D profesional | ✅ creează | ✅ **primește/stochează** | ❌ |
| Vizualizare model | — | ✅ (three.js/Trimble) | ❌ |
| Versionare / istoric model | — | ✅ (de formalizat) | ❌ |
| Documentare proprietate | — | ✅ | asistă |
| Istoric / lifecycle proprietate | — | ✅ | asistă |
| Property Intelligence / Health / PVI | — | ✅ | asistă |
| Knowledge graph / Q&A pe date verificate | — | ✅ | ✅ (grounded) |
| Măsurători/materiale profesionale generate de AI | — | ❌ | ❌ **INTERZIS** |
Principiu blocant: AI NU produce fapte tehnice profesionale; le poate DOAR citi din surse verificate.

## 20. DUPLICATION / DRIFT RISKS
- Active dublate (`property_assets` vs `twins.assets`) — HIGH (drift date).
- Camere în 4 forme — MEDIUM.
- Operator twin FE dublat — LOW.
- Storage disc vs object storage — MEDIUM (referințe rupte post-redeploy).

## 21. GAP ANALYSIS (evidence-graded)
| ID | Gap | Sev | Existing partial | Recomandare |
|---|---|---|---|---|
| G1 | Room/Space ca ancoră cross-system | HIGH | `twins.rooms[]` (uuid+geo) `VERIFIED` | promovează `twins.rooms` la referință canonică; docs/pins → room_id |
| G2 | ProfessionalModel metadata/versionare | HIGH | `digital_twin_models.kind/uploaded_by` `VERIFIED` | adaugă câmpuri pe colecția existentă (NU colecție nouă) |
| G3 | „twins vs projects" | **LOW (reframe)** | ambele funcționale, roluri diferite `VERIFIED` | păstrează ca 2 straturi ale unui Twin; NU migra/șterge |
| G4 | Active dublate | HIGH | 2 reprezentări `VERIFIED` | sursă unică `property_assets`; `twins.assets` = poziționare care referă asset_id |
| G5 | Property Knowledge Layer | MED | `property_dna/kg` goale + QA context `PARTIAL` | asamblează din date existente; populează DNA |
| G6 | Health↔Twin sintetic | MED | `value_loop` real + `95/90` hard-coded `VERIFIED` | elimină override sintetic; data-driven |
| G7 | IFC/BIM | LOW | doar text `DOCUMENTED NOT VERIFIED` | decizie business (viewer IFC vs Trimble) |
| G8 | Docs↔Model link | MED | `NOT FOUND` | adaugă `related_model_id` opțional |
| G9 | Storage referințe | MED | mirror există `PARTIAL` | viewer citește object storage, nu discul |

## 22. REUSABLE EXISTING INFRASTRUCTURE
| Component | Status | Reuse? | Cum | Risc |
|---|---|---|---|---|
| `DigitalTwinViewer.jsx` (three.js+Trimble) | FUNCȚIONAL | ✅ | viewer canonic 3D | scăzut |
| `digital_twin.py` projects/models/pins/plans | FUNCȚIONAL | ✅ | extinde metadate model | mediu (fișier 101KB) |
| `twins` + `ClientTwinViewer` (2D) | FUNCȚIONAL | ✅ | stratul 2D + ancoră camere | scăzut |
| `operator_twins.py` | FUNCȚIONAL | ✅ | flux operator | scăzut |
| `verified_estate.py` | FUNCȚIONAL | ✅ | comandare + gate publish | scăzut |
| `digital_twin_qa.py` + `ai_core` | FUNCȚIONAL | ✅ | knowledge layer AI | scăzut |
| `property_documents.py` | FUNCȚIONAL | ✅ | versionare + asocieri | scăzut |
| `value_loop.py` | FUNCȚIONAL | ✅ | closed-loop health | scăzut |
| `storage_service` (mirror OS) | FUNCȚIONAL | ✅ | sursă unică fișiere | scăzut |
| `property_intelligence` (Maturity/PVI) | FUNCȚIONAL | ✅ | Twin 0–5 = Maturity L0–L5 | scăzut |
| `property_dna`/`kg` | SCHELET GOL | 🟡 | populează, nu reconstrui | mediu |

## 23. PROTECTED INFRASTRUCTURE (NU atinge)
Demo, Client Beta, Specialist Beta, Operator workflow existent, `twins` (74 docuri live), `digital_twin_projects` + date, entitlements/Stripe/auth, House Health engine, governance (MASTER_PLATFORM_STATE, Blueprint), rutele/scheme existente. Orice atingere = risc regresie.

## 24. RECOMMENDED TARGET ARCHITECTURE (propunere, NU implementare)
```
PROPERTY (SSOT)
 ├─ ROOMS/SPACES  ← din twins.rooms, promovat la ancoră canonică (uuid)
 ├─ ASSETS (property_assets = SSOT; poziția {room_id,x,y} referă asset_id)
 ├─ DOCUMENTS (versionate; +related_model_id opțional)
 ├─ PROPERTY TWIN (umbrelă)
 │    ├─ 2D structured layer (twins: rooms/assets)   [client]
 │    └─ 3D professional layer (projects: models+plans+pins+Trimble)
 │         └─ ProfessionalModel metadata (version/source/visibility/status/reason)
 ├─ WORKS/INTERVENTIONS → value_loop → HEALTH/PVI (data-driven, fără 95/90 hard-coded)
 └─ PROPERTY KNOWLEDGE LAYER (asamblat: docs+assets+rooms+pins+works+health → AI QA)
STORAGE: object storage unic. VIZIBILITATE: entitlement + membership + operator publish + audit trail.
```

## 25. NON-BREAKING ROADMAP
- **P0** — Deciziile din §31 (owner).
- **P1 (fundații, non-breaking)**: metadate `ProfessionalModel` pe `digital_twin_models`; `related_model_id` opțional pe documente; audit trail model (deja `uploaded_by`); referință `room_id` opțională (docs/pins) fără a rupe `room` string.
- **P2 (integrare)**: sursă unică active (`twins.assets` → referă `property_assets`); elimină `structure_health=95/90` (data-driven via value_loop); UX client „professional model"; populează Property Knowledge Layer din date existente + trace în AI QA.
- **P3 (consolidare)**: unifică FE OperatorTwin/OperatorDigitalTwin; viewer citește exclusiv object storage; „umbrelă Property Twin" în UI peste cele 2 straturi.
- **P4 (avansat, opțional)**: suport IFC + viewer IFC (DOAR dacă business o cere; altfel rămâne Trimble/glb).

## 26. VERDICT PE CELE 6 DECIZII (business real vs deja rezolvat de infra)
| # (v1) | Întrebare | Verdict pe dovezi | Cine decide |
|---|---|---|---|
| D1 | migrăm `twins`→`projects`? | **APROAPE REZOLVAT de infra** — sunt 2 straturi diferite (2D client vs 3D profesional), NU duplicate. NU migra. | Arhitectură (confirmare „umbrelă") |
| D2 | entitate Room/Space? | **APROAPE REZOLVAT** — camere există cu uuid+geo în `twins`; nevoie = referință cross-system. | Arhitectură (scop minim) |
| D3 | vizibilitate ProfessionalModel | **DECIZIE DE BUSINESS REALĂ** — nu există câmp `visibility`; cine vede (client/specialist/operator/pașaport public). | **Owner** |
| D4 | IFC/BIM real | **DECIZIE DE BUSINESS REALĂ** — investiție viewer IFC vs rămânem glb/skp+Trimble. | **Owner** |
| D5 | professional model = PREMIUM vs plătit | **PARȚIAL REZOLVAT** — PREMIUM = acces la twin (există); `verified_estate` = plătești crearea profesională (există). Decizie mică: upload model propriu e gated PREMIUM sau liber? | Owner (light) |
| D6 | closed-loop Health↔Twin | **APROAPE REZOLVAT** — `value_loop` există; de eliminat override-urile sintetice `95/90`. | Arhitectură |
→ **Doar D3 + D4 (și light D5) sunt decizii de business reale.** Restul = arhitectură non-breaking, cu fundație existentă.

## 27. RISKS
Data drift (active dublate); referințe fișiere post-redeploy (disc); date health sintetice (95/90) induc decizii greșite; Property Knowledge Graph gol = promisiune nesusținută dacă e expus clientului; expunere model profesional fără câmp `visibility`.

## 28. FINAL RECOMMENDATION
Ipoteza Founder e **validată de cod și date**: ~70% există. Direcția = **consolidare + conectare + formalizare metadate model**, NU reconstrucție și NU authoring CAD/BIM. Cel mai important: **twins (2D) și digital_twin_projects (3D) sunt straturi complementare ale UNUI Property Twin** — de unificat conceptual (umbrelă), nu de șters. Prioritate P1 = metadate/versionare `ProfessionalModel` + referință camere/model, totul non-breaking. Nu implementa până la deciziile owner (§31).

---

## 31. OWNER DECISIONS REQUIRED BEFORE IMPLEMENTATION
1. **Vizibilitate model profesional** — cine vede modelul (client / specialist / operator / pașaport public)? *De ce contează*: fără câmp `visibility`, riscăm expunere. *Recomandare*: default client+operator+specialist-asignat; opt-in pașaport public. *Afectează*: `digital_twin_models`, viewer, pașaport. *Blochează P1?* Da (definește schema metadata).
2. **IFC/BIM** — investim într-un viewer IFC sau rămânem pe `.glb` + `.skp`(Trimble)? *De ce*: efort mare, valoare incertă acum. *Recomandare*: **NU acum** — stocăm IFC ca sursă descărcabilă, vizualizare via glb/Trimble; IFC viewer = P4 doar la cerere. *Afectează*: format strategy. *Blochează P1?* Nu.
3. **Gating upload model propriu** — clientul care are deja un model profesional îl poate încărca liber sau doar pe PREMIUM? *Recomandare*: vizualizare avansată = PREMIUM (deja); încărcarea/stocarea modelului = permisă și mai jos, ca să nu blocăm aducerea datelor. *Afectează*: `entitlements`, upload. *Blochează P1?* Parțial.
4. **Umbrelă „Property Twin"** — confirmi că `twins`(2D) + `digital_twin_projects`(3D) devin două straturi ale unui singur Twin (fără ștergere/migrare acum)? *Recomandare*: DA. *Afectează*: doar naming/UI viitor. *Blochează P1?* Nu, dar ghidează P1.

*Decizii care NU necesită owner (le rezolvă arhitectura)*: eliminarea `structure_health=95/90`, sursă unică active, referință `room_id`, citire din object storage, populare knowledge layer.

---
*Forensic audit v2 · read-only · aliniat MASTER_PLATFORM_STATE (24 Aug, cu corectura „twins ≠ legacy") + PRODUCT_BLUEPRINT v1.1 §12. Nimic implementat.*
