# PropManage — DIGITAL TWIN / PROPERTY DIGITAL MODEL · AUDIT COMPLET (read-only)
Data: 27 August 2026 · Autor: E1 (audit, ZERO modificări de cod) · Cerere: Founder

> Metodă: AUDIT → EVIDENCE → GAP ANALYSIS → TARGET ARCHITECTURE → ROADMAP.
> Fiecare afirmație e ancorată în cod. Nimic nu a fost implementat/refactorizat/șters.

---

## 1. EXECUTIVE SUMMARY

PropManage are DEJA un Digital Twin surprinzător de matur (Nivel 3–5 parțial), nu doar „o imagine 3D". Există:
- Viewer 3D real (three.js / @react-three/fiber) cu layere (structură/electric/plumbing/hvac), X-ray „glass walls", section planes, screenshot capture, plus toggle către **Trimble Connect** (viewer nativ SketchUp) — `DigitalTwinViewer.jsx`.
- Upload de modele cu conversie automată (Blender headless: `.dae/.obj/.fbx/.stl/.ply → .glb`; `.skp` = download-only + CloudConvert opțional) — `digital_twin.py`, `blender_convert.py`, `cloudconvert_client.py`.
- Pini spațiali + ancore + issue-reports + comentarii; planuri 2D (floorplan) — `digital_twin.py`.
- Workflow OPERATOR complet (coadă, editare rooms/assets, validare, publicare, notificări) — `operator_twins.py`.
- Flux de COMANDARE model profesional (audit + twin plătit → draft listing → programare) — `verified_estate.py`.
- AI Twin Q&A ancorat strict în date (modele + planuri + pini), refuză să inventeze — `digital_twin_qa.py`.
- Twin Maturity L0–L5 + PVI — `property_intelligence.py`.
- Documente cu asocieri bogate (cameră, activ, lucrare, specialist) + **versionare** (`version`, `prev_version_id`, `history`) — `property_documents.py`.

**Ipoteza Founder-ului („PropManage = stratul digital care primește, organizează, conectează și versionează modelul profesional") este FEZABILĂ și în mare parte deja schițată în cod.** Nu trebuie construit de la zero; trebuie **consolidat, conectat și clarificat**.

**Riscul #1 = DUPLICARE/DRIFT**, deja semnalat în `MASTER_PLATFORM_STATE.md`:
- 5 colecții twin paralele (`digital_twin_projects` vs `twins` LEGACY, + `models`/`plans`/`pins`).
- 3 „knowledge graphs" paralele (`knowledge_center` docs + `kg` + `ai_brain/graph`).
- Storage fragmentat (disc local `UPLOAD_ROOT` + object storage).
- FE duplicat (`OperatorTwin` vs `OperatorDigitalTwin`).

**Lipsuri reale**: entitate `Room/Space` de prim rang (identificatori stabili globali); metadate/versionare formalizată pentru „Professional Model"; suport real IFC/BIM/DWG (azi doar menționate, nu acceptate la upload); un „Property Knowledge Layer" per-proprietate orientat spre client (azi Knowledge Center = explorer de docs interne, admin-only).

---

## 2. CURRENT STATE (ce există astăzi)

| Zonă | Stare | Sursă |
|---|---|---|
| Digital Twin 3D project | ✅ FUNCȚIONEAZĂ | `routes/digital_twin.py` (101KB), `components/DigitalTwinViewer.jsx` |
| Twin lightweight (rooms/assets) | ✅ FUNCȚIONEAZĂ (marcat LEGACY) | `routes/operator_twins.py`, colecția `twins` |
| Operator workflow | ✅ FUNCȚIONEAZĂ | `operator_twins.py`, `OperatorTwin.jsx`/`OperatorDigitalTwin.jsx` |
| Conversie modele | ✅ FUNCȚIONEAZĂ (Blender) · 🟡 SKP via CloudConvert (off) | `blender_convert.py`, `cloudconvert_client.py` |
| Comandare model profesional | ✅ FUNCȚIONEAZĂ | `verified_estate.py` (audit+twin paid order) |
| AI Twin Q&A | ✅ FUNCȚIONEAZĂ | `digital_twin_qa.py` |
| Twin Maturity L0–L5 + PVI | ✅ FUNCȚIONEAZĂ | `property_intelligence.py` |
| House Health + Risks + Recommendations | ✅ FUNCȚIONEAZĂ | `house_health*.py`, `hh_*` |
| Documente + versionare + asocieri | ✅ FUNCȚIONEAZĂ | `property_documents.py` |
| Active (property_assets) | ✅ FUNCȚIONEAZĂ (fără poziție proprie) | `property_intelligence.py`, `property_documents.py` |
| Knowledge Center | ✅ FUNCȚIONEAZĂ dar = explorer docs interne (admin) | `routes/knowledge_center.py` |
| Object storage | ✅ · 🟡 fragmentat cu disc local | `storage_service.py`, `storage_client.py` |

---

## 3. DIGITAL TWIN — CURRENT STATE (detaliat)

**Există (evidence `digital_twin.py`):**
- `POST /projects`, members cu roluri `specialist|client|architect|viewer`.
- `POST /projects/{id}/upload` cu `layer_type` (structure/electric/plumbing/hvac/decor/other) → **multi-layer scene** (X-ray). Owner SAU admin/operator pot încărca.
- Modele (`digital_twin_models`): `kind` (archive/source/model), `uploaded_by/name/role`, `conversion_status/percent/engine`, `format`. Multiple modele/proiect = versionare de facto (dar nu semantică „v1/v2/motiv").
- Pini (`digital_twin_pins`) + ancore + `issue-report` (flux public approve/decide) + comentarii → poziționare spațială + closed-loop pe probleme.
- Planuri 2D (`digital_twin_plans`, `plan_type=floorplan`).
- `GET /subscription` → gate entitlement (402) — acum PREMIUM-only (`F_DIGITAL_TWIN_ADVANCED`).
- Viewer: `@react-three/fiber` + `drei` + `three`; section planes; capture PNG; **toggle Trimble Connect (SketchUp nativ)**.

**Nivele acoperite**: L0 identitate ✅ · L1 profil ✅ · L2 structurat (parțial — rooms/assets embedded, nu entități) 🟡 · L3 vizual 2D/3D ✅ · L4 professional model (upload glb/skp + Trimble) 🟡 (fără IFC/BIM real) · L5 living twin (pini/issue/comments/maintenance/health) 🟡 (buclă nu e complet închisă automat).

---

## 4. PROFESSIONAL DIGITAL TWIN BOUNDARY

**PropManage NU e software de arhitectură — corect.** Codul respectă deja limita:
- `.skp` = **download-only** (Blender nu suportă SKP pe Linux — comentat explicit în `blender_convert.py`), vizualizabil doar via Trimble Connect iframe.
- AI Twin QA refuză să inventeze cote/materiale (`digital_twin_qa.py`: „Never invent numbers, materials, or brands").
- Modelarea exactă (pereți/structură/trasee) rămâne responsabilitatea specialistului cu software profesional.

**Rol corect PropManage = strat digital care primește / stochează / indexează / conectează / versionează / face accesibil modelul profesional.** Fezabil azi pentru `.glb/.gltf` (nativ) + `.skp` (Trimble/descărcare); **NU** pentru IFC/BIM/DWG (nesuportate real).

---

## 5. DATA MODEL AUDIT

Lanțul dorit `PROPERTY → BUILDING → FLOOR → ROOM → ELEMENT → ASSET → DOCUMENT → MAINTENANCE → SPECIALIST → MODEL VERSION`:

| Nivel | Există? | Evidence / Notă |
|---|---|---|
| PROPERTY | ✅ | `properties` collection |
| BUILDING/HOUSE | 🟡 | `building_admin.py` (floors), dar nu ca entitate consumată de twin |
| FLOOR | 🟡 | `floors` numeric în PTR/building; nu entitate |
| ROOM/SPACE | 🟠 **fără entitate globală** | embedded în `twins.rooms[]`, string `room` pe documente, `area_m2` în planuri; **fără ID stabil global** |
| ELEMENT | 🟡 | pini pe model (`digital_twin_pins`) = element spațial |
| ASSET | ✅ (fără poziție proprie) | `property_assets`; poziția vine din pini |
| DOCUMENT | ✅ + versionare | `property_documents` (`room`, `related_asset_id`, `related_request_id`, `specialist_id`, `version`, `prev_version_id`, `history`) |
| MAINTENANCE | ✅ | `maintenance_logs`, `maintenance_tasks` |
| SPECIALIST | ✅ | `users(role=specialist)`, membership în proiecte twin |
| MODEL VERSION | 🟡 de facto | modele multiple/proiect, dar fără schema `ProfessionalModel{version, source, status, visibility, reason}` formală |

**`ProfessionalModel` formal NU există ca entitate dedicată** — datele sunt împrăștiate în `digital_twin_models` (fișier/conversie) + `twins.model_url`. Recomandare: NU crea colecție nouă; **formalizează metadatele pe `digital_twin_models`** (adaugă `source`, `visibility`, `version_label`, `change_reason`, `professional=true`).

---

## 6. DOCUMENT / MODEL UPLOAD AUDIT

- **Documente**: `property_documents.py` — upload cu `category`, `room`, `building_system`, `related_asset_id`, `related_request_id`, `specialist_id`, versionare (`version/prev_version_id/history`). ✅ Solid.
- **Modele 3D**: `ALLOWED_EXTS = {.glb,.gltf,.skp,.dae,.obj,.fbx,.stl,.ply}`. Conversie Blender → glb; SKP → CloudConvert (dezactivat) + download/Trimble.
- **IFC/BIM**: menționat în `digital_twin_qa.py` („GLB/IFC/SKP") dar **NU în `ALLOWED_EXTS`** → practic NEACCEPTAT. 🟠 GAP între doc și implementare.
- **DWG/DXF/RVT**: NEsuportate.
- **Storage**: disc local `UPLOAD_ROOT/{project_id}` + object storage (`storage_service`) → 🟡 fragmentat (semnalat în MASTER_PLATFORM_STATE).

---

## 7. CLIENT WORKFLOW

Există (evidence `operator_twins.py::my_digital_twins`, `digital_twin.py`):
- Client vede twin-urile proprietăților (`GET /me/digital-twins`) cu `status` + `status_label` + progres.
- `request_twin_validation` (client cere validare).
- Upload propriu în proiect (owner poate încărca — `upload_model` verifică `owner_id`).
- Viewer 3D + pini + issue-report.

Lipsă: un flux ghidat „client încarcă model profesional primit de la arhitect" (UI dedicat cu selectare format + status procesare) — parțial acoperit de upload generic, dar nu ca experiență „professional model".

---

## 8. OPERATOR WORKFLOW

✅ **Există și e funcțional** (`operator_twins.py`):
- `GET /operator/queue`, `GET /operator/twins`, `GET /operator/twins/{prop_id}`.
- `POST /operator/twins/{prop_id}` (upsert rooms/assets/model_url/notes).
- `POST /operator/twins/{prop_id}/validate` (approve/needs_revision → setează `twin_unlocked=true`, `structure_health=95`, notifică owner + specialiști).
- Upload model pe orice proiect (admin/operator bypass owner check în `upload_model`).

Lipsă: „select client + property + attach professional model + set version + publish" ca UN flux coerent (azi e împărțit între `twins` lightweight și `digital_twin_projects`).

---

## 9. SPECIALIST WORKFLOW

- Specialistul poate fi membru în proiect (`role=specialist|architect`) și poate încărca (dacă owner sau via membership/permission).
- Poate primi task-uri (requests/marketplace), poate livra documentație (documente cu `specialist_id`).
- Issue-reports approve/decide = buclă specialist→client.

Lipsă: flux explicit „specialist livrează MODEL profesional atașat comenzii clientului" (azi merge prin upload generic + verified_estate order, dar nu ca handoff formal specialist→property).

---

## 10. KNOWLEDGE CENTER AUDIT

**Constatare importantă**: `routes/knowledge_center.py` = **explorer de documentație internă** (citește `/app/memory` + `/app/docs`, admin-only: `require_role("admin")`). Endpoints: `/tree`, `/doc`, `/search`, `/registry`, `/review`, `/architecture`, `/inspector`. NU e un „Property Knowledge Layer" per-proprietate, orientat spre client.

**Property Knowledge Layer** (ce vrea Founder-ul) există parțial DISPERSAT:
- `kg` collection + `ai_brain/graph` (2 grafuri) — semnalate DRIFT în MASTER_PLATFORM_STATE (D6).
- `digital_twin_qa.py` construiește deja context per-proprietate din modele+planuri+pini (embrion de knowledge layer semantic).

→ Property Knowledge Layer = **de asamblat din existent (documents+assets+pins+maintenance+twin+health)**, NU de construit de la zero, și de NU confundat cu Knowledge Center (docs interne).

---

## 11. MASTER_PLATFORM_STATE ALIGNMENT

`MASTER_PLATFORM_STATE.md` (44KB, 24 Aug — CURENT) confirmă și e sursă canonică:
- „Digital Twin | 5 collections (`digital_twin_projects/models/plans/pins/twins`) + `twin_schedule` | ✅ IMPLEMENTAT · 🟡 storage fragmentat".
- `twins` = 🟠 **LEGACY** (candidat migrare în `digital_twin_projects`).
- `digital_twin_models`/`plans` = 🟡 candidat merge.
- Knowledge: 3 grafuri paralele → „Knowledge Layer consolidat" = P2 (M7).
- „Twin storage consolidat" = P2 (M5).

**IMPLEMENTATION ↔ MASTER_PLATFORM_STATE GAP**: niciun conflict major; documentul ANTICIPEAZĂ deja consolidările necesare. Twin gate a fost mutat de la PRO la PREMIUM (27 Aug, această sesiune) — de reflectat la următorul refresh al documentului.

---

## 12. PRODUCT ARCHITECTURE BLUEPRINT ALIGNMENT

`PRODUCT_BLUEPRINT.md` (validat de owner, v1.1, Iulie 2026):
- §12 **PROPERTY KNOWLEDGE GRAPH** = avantajul competitiv pe termen lung → **exact „Property Knowledge Layer"** pe care îl descrii acum. Deci direcția e DEJA în blueprint-ul validat.
- Strat 1 DATE: `Digital Twin → House Health → Audit` (buclă).
- „Twin light (5 min, ghidat)" în onboarding.
- Legacy declarat: `OperatorTwin (dublura)`, `ClientDashboard V1`.
- PREMIUM = „Digital Twin avansat".

**Aliniere bună.** Blueprint-ul susține ipoteza; nu inventez versiune finală — doar semnalez ce trebuie clarificat (secțiunea 29).

---

## 13. ROOMPLANNER / VISUAL 3D ANALYSIS (matrice)

| Element RoomPlanner | Verdict PropManage | Motiv |
|---|---|---|
| Vizualizare 3D | **REUTILIZABIL** | avem three.js viewer |
| Poziționare mobilier / obiecte | **ADAPTABIL** | pini există; plasare obiecte = extensie |
| Camere/dimensiuni | **ADAPTABIL** | `area_m2` în planuri; lipsă entitate Room globală |
| Catalog obiecte + search + categorii | **DOAR INSPIRAȚIE** | nu avem catalog 3D de mobilier |
| Modele 2D/3D | **REUTILIZABIL** | planuri + modele glb |
| Fotografiere / visual search | **NU ESTE RELEVANT (acum)** | out of scope faza curentă |
| Relația obiect↔spațiu | **ADAPTABIL** | via pini→room, dacă Room devine entitate |
| Model BIM profesional | **NU TREBUIE CONFUNDAT** | rămâne la specialist |

---

## 14. HOUSE HEALTH ↔ DIGITAL TWIN RELATIONSHIP

Buclă dorită: problemă → recomandare → specialist → intervenție → rezultat → document → update twin → health recalculat.

Stare azi:
- Recomandări (`hh_recommendations`), lucrări (`requests`), documente, House Health score — TOATE există.
- Twin issue-reports (pini) + comments = semnal de problemă legat de spațiu.
- `operator_validate_twin` setează `structure_health=95` la aprobare (legătură twin→health, dar hard-codată).
- **Bucla NU e închisă automat**: nu există un orchestrator care, la finalizarea unei lucrări, să actualizeze twin-ul ȘI să recalculeze health cu proveniență. 🟠 GAP (closed-loop).

---

## 15. TWIN MATURITY ANALYSIS

`property_intelligence.py` are deja L0–L5: Înregistrată → Identificată → Documentată → Activă → Monitorizată → Predictivă, cu criterii (PVI≥40, audit, assets≥3, activitate). **Susține direct** modelul „Twin 0–5" propus. Recomandare: NU crea a doua scară; **mapează Twin 0–5 pe Maturity L0–L5 existent** (adaugă doar „nivel professional model prezent" ca semnal, nu scară nouă). Se leagă natural de A→G (harta casei) livrat recent.

---

## 16. AI CAPABILITIES VS PROFESSIONAL CAPABILITIES

**AI poate (și parțial deja face)**: interpretare documente, extragere metadate, clasificare, Q&A pe twin (`digital_twin_qa.py`), rezumate, recomandări (House Health), identificare lipsuri (`completeness.next_step`), context semantic per-proprietate.
**AI NU înlocuiește**: arhitect, inginer, releveu, modelare BIM, validare structurală, trasee reale prin pereți. Codul respectă deja limita (refuză să inventeze).
**Posibilități (doar menționate, nu echivalent profesional)**: auto-tag pe pini, auto-clasificare planuri, comparare versiuni model, detectare inconsistențe doc↔twin.

---

## 17. GAP ANALYSIS (prioritizat)

| # | Gap | Severitate | Dovadă |
|---|---|---|---|
| G1 | **Entitate Room/Space globală** cu ID stabil (ancoră pentru docs/assets/pins/works) | HIGH | rooms doar embedded/string |
| G2 | **`ProfessionalModel` metadata/versionare formală** (source, visibility, version_label, change_reason, professional flag) | HIGH | date dispersate în `digital_twin_models`+`twins.model_url` |
| G3 | **Duplicare twin**: `twins` (LEGACY) vs `digital_twin_projects` | MEDIUM | MASTER_PLATFORM_STATE D5 |
| G4 | **Storage fragmentat** (disc local + object storage) | MEDIUM | `UPLOAD_ROOT` + `storage_service` |
| G5 | **Property Knowledge Layer per-proprietate** (client-facing) neasamblat; 3 grafuri paralele | MEDIUM | knowledge_center vs kg vs ai_brain/graph |
| G6 | **Closed-loop Health↔Twin** neautomatizat | MEDIUM | `structure_health=95` hard-coded |
| G7 | **IFC/BIM real** (doar menționat, neacceptat) | LOW/OPTIONAL | ALLOWED_EXTS fără .ifc |
| G8 | **FE duplicat** OperatorTwin vs OperatorDigitalTwin | LOW | Blueprint TD-10 |
| G9 | **Flux „professional model" coerent** (client & operator & specialist) | MEDIUM | împărțit între `twins` și `projects` |

---

## 18. REUSABLE COMPONENTS (nu reconstrui)

DigitalTwinViewer (three.js + Trimble), `digital_twin.py` (projects/models/pins/plans/upload/conversie), `operator_twins.py` (operator flow), `verified_estate.py` (comandare), `digital_twin_qa.py` (AI layer), `property_documents.py` (versionare + asocieri), `property_intelligence.py` (Maturity+PVI), House Health engine, object storage (`storage_service`), Blender/CloudConvert conversie.

## 19. COMPONENTS THAT NEED REFACTORING (consolidare, NU acum)

`twins` → merge în `digital_twin_projects` (M5). `digital_twin_models`+`plans` → consolidare. Storage → o singură sursă (object storage). OperatorTwin vs OperatorDigitalTwin → o singură pagină. Knowledge graphs (kg + ai_brain/graph) → un singur Property Knowledge Layer (M7).

## 20. MISSING COMPONENTS (de construit, după decizie)

Entitate Room/Space; schema/UI ProfessionalModel + versionare semantică (v1/motiv/autor/publish); flux „professional model handoff" (client/operator/specialist); closed-loop Health↔Twin orchestrator; (opțional) suport IFC.

---

## 21. MATRICEA FINALĂ

| Feature/Capability | Current State | Source | Reusable? | Adapt? | Rebuild? | Missing? | Dependencies | Priority | Phase |
|---|---|---|---|---|---|---|---|---|---|
| Property Profile | FUNCȚIONEAZĂ | `properties` | ✅ | – | – | – | – | – | – |
| Rooms/Spaces | PARȚIAL (embedded/string) | `twins.rooms`, docs `room`, plans | 🟡 | ✅ | – | ✅ entitate globală | Property | HIGH | P1 |
| Assets | FUNCȚIONEAZĂ (fără poziție) | `property_assets` | ✅ | ✅ (pin link) | – | poziție proprie | Rooms/Pins | MED | P2 |
| Documents | FUNCȚIONEAZĂ + versionare | `property_documents.py` | ✅ | – | – | – | – | – | – |
| Photos | FUNCȚIONEAZĂ | `property_documents` (foto), twin capture | ✅ | – | – | – | – | – | – |
| 2D Plan | FUNCȚIONEAZĂ | `digital_twin_plans` | ✅ | ✅ (room link) | – | – | Rooms | MED | P2 |
| 3D Visualization | FUNCȚIONEAZĂ | `DigitalTwinViewer.jsx` (three.js) | ✅ | – | – | – | – | – | – |
| Digital Twin | FUNCȚIONEAZĂ (L3–L5 parțial) | `digital_twin.py` | ✅ | ✅ | – | closed-loop | Health/Docs | HIGH | P1 |
| Professional Model Upload | PARȚIAL | `digital_twin.py` upload | ✅ | ✅ (metadata) | – | flux coerent | Storage | HIGH | P1 |
| SKP | PARȚIAL (download-only + Trimble) | `blender_convert.py`, viewer Trimble | ✅ | ✅ | – | – | CloudConvert | MED | P2 |
| BIM / IFC | MENȚIONAT, NEACCEPTAT | `digital_twin_qa` (doar text) | – | 🟡 | – | ✅ suport real | viewer IFC | LOW | P3 |
| CAD (DWG/DXF/RVT) | NEsuportat | – | – | – | – | ✅ (opțional) | conversie | LOW | P3+ |
| Model Versioning | DE FACTO (fără semantică) | `digital_twin_models` multiple | 🟡 | ✅ | – | schema formală | ProfessionalModel | HIGH | P1 |
| Model Viewer | FUNCȚIONEAZĂ | `DigitalTwinViewer.jsx` | ✅ | – | – | – | – | – | – |
| Model Metadata | PARȚIAL | `digital_twin_models` (uploaded_by/kind/format) | ✅ | ✅ | – | source/visibility/version | – | HIGH | P1 |
| Client Upload | FUNCȚIONEAZĂ (generic) | `upload_model` (owner) | ✅ | ✅ (UI dedicat) | – | UX „professional" | – | MED | P2 |
| Operator Upload | FUNCȚIONEAZĂ | `operator_twins.py` + upload bypass | ✅ | ✅ | – | flux unificat | – | MED | P1 |
| Specialist Upload | PARȚIAL | membership + `specialist_id` docs | 🟡 | ✅ | – | handoff formal | – | MED | P2 |
| Knowledge Center | FUNCȚIONEAZĂ (docs interne, admin) | `knowledge_center.py` | ✅ | – | – | ≠ property layer | – | – | – |
| Property Knowledge Layer | DISPERSAT | `kg`, `ai_brain/graph`, `digital_twin_qa` | 🟡 | ✅ | – | asamblare | Twin/Docs/Health | MED | P2/M7 |
| House Health | FUNCȚIONEAZĂ | `house_health*.py` | ✅ | – | – | – | – | – | – |
| PVI | FUNCȚIONEAZĂ | `property_intelligence.py` | ✅ | – | – | – | – | – | – |
| Twin Maturity | FUNCȚIONEAZĂ (L0–L5) | `property_intelligence.py` | ✅ | ✅ (map Twin0–5) | – | – | – | LOW | P1 |
| Maintenance | FUNCȚIONEAZĂ | `maintenance_logs/tasks` | ✅ | – | – | – | – | – | – |
| Risks | FUNCȚIONEAZĂ | `hh_recommendations` | ✅ | – | – | – | – | – | – |
| Recommendations | FUNCȚIONEAZĂ | House Health | ✅ | – | – | – | – | – | – |
| Intervention | FUNCȚIONEAZĂ | `requests` | ✅ | ✅ (link twin) | – | closed-loop | Twin | MED | P2 |
| History | FUNCȚIONEAZĂ | doc history, twin status, milestones | ✅ | ✅ | – | version timeline UI | ProfessionalModel | MED | P2 |
| AI Layer | FUNCȚIONEAZĂ | `digital_twin_qa.py`, ai_core | ✅ | ✅ | – | – | Knowledge Layer | MED | P2 |
| Permissions | FUNCȚIONEAZĂ | roles + `entitlements.py` + membership | ✅ | ✅ | – | operator publish rules | – | MED | P1 |
| Audit Trail | FUNCȚIONEAZĂ | `log_event`, `impersonation_logs`, uploaded_by | ✅ | ✅ | – | model version trail | – | LOW | P2 |

---

## 22. ARCHITECTURE RISKS
Duplicare twin (5 colecții) → confuzie „care e SSOT". Storage fragmentat → fișiere orfane / limite inconsistente. 3 knowledge graphs → drift semantic.

## 23. DATA RISKS
Rooms fără ID stabil → asocieri fragile (string matching pe `room`). Model versioning fără schema → pierderea trasabilității „ce s-a schimbat/când/de ce". `structure_health=95` hard-coded → date de sănătate nereale.

## 24. UX RISKS
Client poate vedea 2 experiențe twin (lightweight vs 3D project) → inconsistență. Upload „professional model" fără UX dedicat → confuzie format/procesare. OperatorTwin dublat.

## 25. SECURITY / PERMISSION RISKS
Upload bypass owner pentru admin/operator (corect, dar trebuie audit trail pe fiecare publish). Vizibilitate model (public/privat) neformalizată → risc expunere model profesional. Rutele publice de report approve — de verificat rate-limit/token (există `twin_action_tokens`).

---

## 26. RECOMMENDED TARGET ARCHITECTURE (propunere, NU implementare)

```
PROPERTY (SSOT)
 ├─ ROOMS/SPACES (entitate nouă, ID stabil)  ← ancoră comună
 ├─ ASSETS (link Room + Pin)
 ├─ DOCUMENTS (versionate; link Room/Asset/Work/Specialist) [există]
 ├─ DIGITAL TWIN PROJECT (SSOT twin — absoarbe `twins` LEGACY)
 │    ├─ MODELS (glb/skp…) + ProfessionalModel metadata (version/source/visibility/reason)
 │    ├─ PLANS 2D (link Room)
 │    ├─ PINS (link Room/Asset/Issue)
 │    └─ VIEWER (three.js + Trimble)
 ├─ MAINTENANCE / INTERVENTION (link Room/Asset → update Twin + Health)
 ├─ HOUSE HEALTH / PVI / MATURITY (consumă Twin+Docs)
 └─ PROPERTY KNOWLEDGE LAYER (asamblat: Docs+Assets+Pins+Maintenance+Twin+Health → AI context)
STORAGE: object storage unic. PERMISSIONS: entitlements + membership + operator publish + audit trail.
```

## 27. PROPOSED DIGITAL TWIN EVOLUTION (map pe existent)
Twin0=profil → Twin1=rooms+assets+docs → Twin2=plan 2D → Twin3=model 3D → Twin4=professional model (glb/skp/Trimble) → Twin5=living (health+maintenance+versiuni). **= Maturity L0–L5 existent + semnal „professional model prezent".**

## 28. PHASED IMPLEMENTATION ROADMAP (propunere)
- **P1 (fundație, non-breaking)**: entitate Room/Space; `ProfessionalModel` metadata pe `digital_twin_models` (source/visibility/version_label/reason/professional); flux operator „attach + publish" unificat; audit trail model.
- **P2 (conectare)**: link Rooms↔Assets↔Pins↔Docs↔Plans; UX client „professional model"; closed-loop Health↔Twin (la finalizare lucrare → update twin + recompute health); Property Knowledge Layer v1 (asamblare + AI context).
- **P3 (consolidare — deja în MASTER_PLATFORM_STATE M5/M7)**: migrare `twins`→`projects`; storage unic; merge FE OperatorTwin; (opțional) suport IFC/viewer IFC.

## 29. OPEN QUESTIONS / DECISIONS REQUIRED
1. `twins` (LEGACY) — migrăm în `digital_twin_projects` acum sau păstrăm până după stabilizare?
2. Room/Space — entitate globală nouă (recomandat) sau rămâne embedded?
3. Vizibilitate ProfessionalModel — cine vede (client/specialist/operator/public pașaport)?
4. IFC/BIM — investiție reală (viewer IFC) sau rămâne doar glb/skp + Trimble?
5. „Professional model" = parte din PREMIUM (entitlement) sau serviciu plătit separat (verified_estate)?
6. Closed-loop Health↔Twin — automat (orchestrator) sau semi-manual (operator confirmă)?

## 30. FINAL RECOMMENDATION
Ipoteza e **VALIDATĂ de cod**: PropManage POATE fi stratul digital care primește/organizează/conectează/versionează modelul profesional — fundamentul există deja (viewer 3D, upload+conversie, operator flow, comandare, AI QA, maturity, documente versionate). **Direcția corectă = CONSOLIDARE + CONECTARE + 2 entități noi (Room, ProfessionalModel metadata)**, NU reconstrucție. Prioritate P1 = Room/Space + ProfessionalModel metadata + flux operator unificat (non-breaking, reutilizează tot). NU construi software de arhitectură; păstrează limita profesională deja respectată în cod. NIMIC nu se implementează până la aprobarea Founder-ului pe deciziile din §29.

---
*Audit read-only. Zero modificări. Aliniat cu MASTER_PLATFORM_STATE (24 Aug) + PRODUCT_BLUEPRINT v1.1 §12.*
