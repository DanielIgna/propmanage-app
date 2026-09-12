# PropManage — DIGITAL TWIN · P1 CONSOLIDARE (BUILD) · 27 Aug 2026
Decizii Fondator confirmate → implementare non-breaking. Supersedează secțiunea „OWNER DECISIONS" din auditul v2.

> **UPDATE 28 Aug 2026**: după P1 au urmat **P0 (Property Anchor)** + **P0.1 (Operator Anchor)**. Statutul canonic curent + taxonomia unificată (2D+3D): `PROPERTY_TWIN_CANONICAL_v1.0.md`.

## DECIZII APLICATE
- **Property Twin = umbrelă cu 2 straturi complementare**: `twins` (2D structurat, client) + `digital_twin_projects` (3D profesional). NU migrate, NU șterse, NU redenumite.
- **Vizibilitate model** (#2): default `internal` (owner + operator + specialist asignat). `public` = opt-in explicit (pașaportul public NU expune modelul implicit).
- **IFC/BIM** (#3): DEFERRED (P4). Rămânem pe GLB/GLTF + SKP/Trimble + formatele existente. IFC = stocat/atașabil/descărcabil când e permis (backlog viewer).
- **Upload model propriu** (#4): NU mai e blocat de PREMIUM. Orice user autentificat poate aduce/stoca/versiona modelul (ingest). Vizualizarea/exploatarea AVANSATĂ rămâne PREMIUM.
- **Room/Space** (#5): NU se creează entitate nouă. `twins.rooms[]` (uuid stabil) = ancoră canonică, expusă read-only via `GET /api/properties/{id}/spaces`.
- **Active** (#6): `property_assets` = SSOT identitate. `twins.assets[].asset_ref` = link opțional către identitatea canonică (ONE ASSET IDENTITY + MULTIPLE CONTEXTS). Fără migrare destructivă.
- **ProfessionalModel metadata** (#7): extindere aditivă pe `digital_twin_models`.
- **Health↔Twin** (#8): eliminat DOAR override-ul sintetic `structure_health=95` la aprobarea twin. Default-ul `90` la creare rămâne (baseline motor House Health — neatins per „NU modificăm motorul").
- **Docs↔Model** (#9): `property_documents` + `related_model_id`, `related_room_id` (opționale). Fără DMS nou.
- **Operator UI** (#11): analiză → NU sunt duplicate. Vezi mai jos.

## MODIFICĂRI (fișiere)
Backend:
- `routes/digital_twin.py`:
  - `_ensure_dt_ingest_access()` NOU (ingest fără PREMIUM); swap pe: create/list/get/update/delete project, upload model, upload plan, list models/plans, serve model/plan, PATCH/DELETE model, PATCH/DELETE plan, conversion status. PREMIUM (`_ensure_dt_access`) PĂSTRAT pe: members, pins/anchors/issue-report, comments, retry conversii, AI Q&A.
  - Upload model_doc: +`property_id, source, version, version_label, status, visibility(internal), change_reason, supersedes, superseded_by`.
  - `_LayerUpdateIn` + `PATCH /models/{id}`: acceptă metadata + versionare; `supersedes=<id>` marchează vechiul model `superseded_by`+`status=superseded` (non-destructiv). Validare `status`/`visibility`.
  - `/subscription`: +`can_ingest:true`.
  - **Storage (deploy-readiness, forțat de gate)**: upload model+plan scriu DIRECT în Emergent Object Storage (`store_dt_bytes`), disc = cache; `serve_model_file` + conversii (`ensure_dt_local`) fac restore la cerere; GLB convertit e persistat durabil (`object_path`).
- `storage_service.py`: `dt_object_path`, `store_dt_bytes`, `ensure_dt_local` (NOI).
- `models.py`: `TwinAsset.asset_ref: Optional[str]`.
- `routes/operator_twins.py`: eliminat `structure_health:95` la approve; NOU `GET /api/properties/{id}/spaces`.
- `routes/property_documents.py`: `related_model_id`, `related_room_id` (DOC_FIELDS + upload form + EDITABLE).
Frontend:
- `OperatorTwin.jsx` / `OperatorDigitalTwin.jsx`: comentarii de clarificare (2D vs 3D al aceluiași Property Twin). ZERO schimbare de comportament.

## OPERATOR UI — ANALIZĂ (#11, non-breaking)
`OperatorTwin.jsx` (tab `twins`) editează stratul **2D** (`twins`: rooms/assets/validate). `OperatorDigitalTwin.jsx` (tab `dt_pro`) gestionează stratul **3D** (`digital_twin_projects`: modele/planuri/pins). NU sunt duplicate — sunt cele două suprafețe operator ale aceluiași Property Twin. Recomandare (P2/P3, opțional): re-etichetare UI „Property Twin · 2D" / „Property Twin · 3D". Fără ștergere/merge de cod.

## VERIFICARE (self-test e2e, preview)
- FREE: subscription `active:false, can_ingest:true`; create project ✅; upload model 200 ✅; list models 200 ✅; pin → 402 ✅ (PREMIUM intact).
- PREMIUM: upload → metadata (source/version/status/visibility/change_reason/object_path) ✅; serve model 200 (restore-aware) ✅; PATCH version_label+visibility ✅; visibility invalid → 400 ✅; supersedes → v1 `superseded` (păstrat) ✅.
- `/spaces` → 5 camere canonice cu uuid ✅.
- Document upload + GET → `related_model_id`+`related_room_id` persistă ✅.
- `structure_health:95` eliminat complet ✅. `TwinAsset.asset_ref` serializează ✅.
- Object Storage round-trip (store→restore→bytes) ✅.

## RĂMAS (nu în P1)
- UX client „adu modelul profesional" (FREE) = P2 (audit §25). Backend gata; UI de expus.
- IFC viewer = P4. Property Knowledge Layer populare = P2.
