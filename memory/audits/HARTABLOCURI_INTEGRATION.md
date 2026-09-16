# HartaBlocuri Cluj — Integrare ca sursă externă de referință (Building Knowledge)

**Status:** ACTIVE (PREVIEW/BUILT) · Ultima actualizare: 2026-06
**Scope operațional:** EXCLUSIV județul Cluj. NU se extinde la alte județe fără date autorizate separat.
**Principiu:** HartaBlocuri = sursă externă de referință, NU registru exhaustiv, NU sursă de adevăr. Datele rămân „neverificate de PropManage".

---

## 1. Ce este
Bază externă cu ~3.400 blocuri din județul Cluj (predominant fond comunist). Integrată **aditiv** în entitatea `buildings` existentă — o singură entitate Building cu straturi de proveniență, fără sistem paralel.

Nivele distincte păstrate:
1. Date externe HartaBlocuri (`context.external_sources.hartablocuri`)
2. Date introduse manual în PropManage (`context.*`)
3. Date verificate PropManage (`context.verification_status`)
4. Date de la specialiști (ulterior)

## 2. Sursa de date
`/app/backend/data/hartablocuri_cluj.xlsx`, foaia „Detalii blocuri". Exclude rândurile marcate `STERGE` / `DE ADĂUGAT` → 3406 înregistrări utile. Localități multiple: Cluj-Napoca, Turda, Dej, Câmpia Turzii, Gherla, Florești, Huedin, Apahida etc.

## 3. Import (`/app/backend/hartablocuri_import.py`)
- **Idempotent**: cheie `source_record_id` (md5 din nume+adresă+coordonate). Reimport ⇒ 0 blocuri noi. Index sparse pe `source_record_id` + `context.norm_address`.
- **Matching cross-source**: adresă normalizată + proximitate coordonate ≤60m. Adrese placeholder („Strada ?? nr. ?") NU sunt chei de matching → blocuri distincte.
- **Non-destructiv**: completează doar câmpuri goale; diferențele → `context.conflicts[]` (status `review`), fără suprascriere.
- **Rezultat import**: 3404 blocuri noi, 2 conflicte reale, 0 erori. Total `buildings` = 3405.
- Colecție `import_batches`: Batch ID, source, file, total/imported/matched/new/duplicates/conflicts/errors.
- CLI: `python -m hartablocuri_import --file data/hartablocuri_cluj.xlsx [--limit N] [--dry-run]`.

## 4. Proveniență (`context.external_sources.hartablocuri`)
`source_name=HartaBlocuri`, `source_record_id`, `import_batch_id`, `imported_at`, `verification_status=neverificat`, `reference_url`, `raw{...}` (toate câmpurile brute), `plan_urls[]`, `photo_urls[]`.

## 5. Contextul clădirii (`fields` afișate în UI)
nume, adresă, localitate, cartier/UAT, lat/lng, an finalizare, regim înălțime, niveluri, apartamente, distribuție camere, scări, lift, structură, eră/categorie, dezvoltator, finisaje, risc seismic, alte detalii.
- **Planuri**: URL-uri imagini pe hartablocuri.ro (1975 blocuri) → afișate ca thumbnail-uri hotlink (tab nou), cu atribuire „Sursă: HartaBlocuri". NU se copiază local.
- **Poze**: practic absente în fișier (0 blocuri cu poze valide).
- UI: `PropertyTechnicalRecord.jsx > HartaBlocuriCard` cu banner „Date externe HartaBlocuri — neverificate de PropManage".

## 6. Conflicte
`context.conflicts[]` = `{field, propmanage_value, hartablocuri_value, status}`. Rezolvare admin:
- **Confirmă HartaBlocuri** → `context[field]` devine valoarea HartaBlocuri.
- **Respinge** → rămâne valoarea PropManage.
- Ambele valori brute + `context.conflict_history[]` păstrate (nu se șterge originalul HartaBlocuri).

## 7. Typology Engine (DOAR pregătire date, fără activare)
`context.typology` cu `{raw, normalized, source}` pentru: period, year, era, height_regime, structure, entrances, apartments, rooms_breakdown, neighborhood. Pregătit pentru viitoarea „Communist Housing Typology Library". NU activează clasificare/UI.

## 8. Endpoint-uri
**Public** (fără auth): `GET /api/public/buildings/search`, `/cities`, `/{id}`.
**Admin** (`/api/admin/hartablocuri/`): `POST import` (dry_run), `GET batches`, `GET stats`, `GET buildings` (filtre source/status), `GET conflicts`, `GET buildings/{id}`, `POST buildings/{id}/conflicts/resolve`.

## 9. Frontend
- Homepage: `components/BuildingDiscovery.jsx` — „Găsește-ți blocul" → `/register?binvite=<id>`.
- Admin (Import Center, cu mutații): `/admin/hartablocuri` (`pages/admin/HartaBlocuriAdmin.jsx`) — Overview / Loturi Import / Blocuri / Conflicte (nelegat în meniu, unealtă operațională).
- Admin (Observability, READ-ONLY v1): `/admin/harta-blocuri` (`pages/admin/HartaBlocuriObservability.jsx`) — intrare de meniu „HartaBlocuri" în secțiunea IMOBILE (Business Administration). Overview + tabel paginat + search + filtre sursă/status + building detail read-only. Fără mutații. Stare „Acces interzis" pentru non-admin.
- Client: `PropertyTechnicalRecord.jsx` — cardul HartaBlocuri în „Contextul clădirii".

## 10. Flux Client Beta
Homepage → Găsește-ți blocul → selectează bloc → `/register?binvite=<id>` → creează proprietate → Blocul meu (join) → Contextul clădirii (afișează datele HartaBlocuri, sursă + status neverificat). Aceeași entitate Building pentru toți vecinii.

## 11. GARANȚII (ce NU se modifică)
Building Health, Twin Maturity, PVI, Cartea Casei, Digital Twin, formulele existente, datele manuale, auth, join, sistemul de abonamente. Adăugarea manuală de blocuri rămâne complet funcțională. HartaBlocuri NU pune date de bază în spatele abonamentului.

## 12. De validat înainte de SEO programatic per bloc/cartier
Corectitudinea datelor, Contextul clădirii, Admin Import Center, rezolvarea conflictelor și fluxul Client Beta end-to-end.

## 13. Securitate (Security Audit 2026-06 — CONDITIONAL PASS, 0 Critical/High)
- **SEC-001 (rezolvat)**: URL-urile de planuri/poze externe se validează pe **host real** (`hartablocuri.ro` / `www.hartablocuri.ro`), nu substring — respinge `//evil.test/hartablocuri.ro` și `//hartablocuri.ro.evil.com`.
- **SEC-002 (rezolvat)**: `/api/public/buildings/cities` folosește aggregation + cache 5 min (fără scan complet repetat).
- **SEC-003 (rezolvat)**: `POST /admin/hartablocuri/import` constrânge `file_path` la `/app/backend/data` (realpath + extensie .xlsx), eroare generică (fără path traversal / file probing).
- **Hardening**: rezolvarea conflictelor acceptă doar câmpuri din allowlist (`construction_year/floors/number_of_units/neighborhood`) → previne injecția de path în `$set`.
- Controale confirmate OK: admin endpoints cu `require_role('admin')`; `re.escape` pe q/city (anti NoSQL/ReDoS); paginare mărginită; `ObjectId.is_valid`; public whitelist fără `owner_id`/rezidenți/note; fără `dangerouslySetInnerHTML`; scheme URL forțate http/https; `rel="noreferrer nofollow"` + `target=_blank`.
- Deschis (P3, neimplementat acum): rate limiting per-IP pe endpoint-urile publice (doar abuz/cost, nu scurgere de date).

## 14. Truth Layer READ MODEL v1.0 (Faza 1 — 2026-06)
**Principiu:** strat derivat calculat EXCLUSIV la citire. Zero scriere DB, zero modificare raw/schema/import/proveniență. Nicio inferență profesională (L3).
- **Modul pur:** `/app/backend/hartablocuri_read_layer.py` → `build_truth_layer(hb_raw)` (fără efecte secundare). Returnează `None` dacă nu există date HartaBlocuri.
- **Niveluri:** L0 = SOURCE FACT (păstrat exact) · L1 = DERIVED FACT (derivare deterministă). L2 (CANDIDATE) / L3 (PROFESSIONAL) NEintroduse.
- **ERA (L0):** din `raw.era`; valoare validă → `high`; marker necunoscut ("necunoscut"/"de adaugat"/"?"...) → `unknown`; lipsă → `not_available`. NU se estimează din an.
- **FORM (L1):** derivat DOAR din `raw.proiect` → {bara, turn, cruce, drept, mixt, unknown}. keyword unic (bara/turn/cruce/drept) → `high`; ≥2 keyword-uri (ex. „cruce/drept") → `mixt`/`low`; coduri fără formă (cf1, cf1d, „bloc unicat"), „DE ADĂUGAT" → `unknown`; lipsă → `not_available`. Păstrează `form.raw_project`.
- **REGIME (L1):** `derived_floors` din `raw.regim_inaltime` DOAR determinist: „P+N" / „parter + N etaje" → N (`high`). Prefixe tehnice ambigue (S+P+4, D+P+4) → `null`/`unknown`. NU suprascrie niveluri/regim/floors.
- **CARTIER (L0):** exclusiv `raw.neighborhood`; fără inferență din UAT. Lipsă → `not_available`.
- **Provenance:** `source=hartablocuri`, `verification_status=neverificat`, notă „Date externe — neverificate de PropManage".
- **Confidence:** high | medium | low | unknown | not_available.
- **Suprafață:** adăugat `truth_layer` (non-breaking) în `GET /api/public/buildings/{id}` (public) și `GET /api/admin/hartablocuri/buildings/{id}` (admin). Reguli de acces nemodificate.
- **UI minimal:** secțiune „Truth Layer (derivat · read-only)" în modalul read-only din `HartaBlocuriObservability.jsx` (fără refactor). Fără UI public nou.
- **Teste:** `tests/test_hartablocuri_truth_layer_iter224.py` (23/23 pass — ERA/FORM/REGIME/CARTIER/provenance/null-safety).
- **STOP:** BLOCAT în continuare — Project Family, Plan Family, C1/C4, SEO, sitemap, enrichment. Așteaptă aprobare P2.

## 15. Truth Layer READ MODEL v2.0 — Faza 2 (Project Families + Typology Profiles C1/C4) — 2026-06
**Principiu:** extensie strict read-only a Truth Layer. Zero scriere DB, raw/provenance intacte, fără estimări.
- **Project Family (L1)** — `derive_project_family(hb_raw)` normalizează soft codurile „cf" din free-text `raw.proiect`: familie de bază `cf<număr>` (cf1/cf2/cf3), `variants[]` = token-uri complete (cf1d, cf1sd...), `raw_project` păstrat. „cf1?" → `medium`; fără cod cf → `unknown`; familii diferite → `low`; lipsă → `not_available`. Dataset: 2077 clădiri cu familie derivată.
- **Typology Profiles (L2 · CANDIDATE)** — `derive_typology_profiles(hb_raw, truth_layer)` returnează profilurile candidate satisfăcute (doar matched), etichetate `classification=candidate` + disclaimer „Candidate Typology — neverificat de PropManage. Nu este tipologie oficială, certificare sau diagnostic tehnic".
  - **C1** „Panou prefabricat P+4 (fond comunist)": era comunistă + structură panouri/prefabricate + `derived_floors==4`. Confidence `high` (sau `medium` dacă structura conține „posibil"). Dataset: **1120** clădiri.
  - **C4** „Turn de locuit (regim înalt)": `form==turn` + `derived_floors>=10`. Confidence `high`. Dataset: **114** clădiri.
- **Suprafață extinsă:** `truth_layer.project_family` + `truth_layer.typology_profiles` expuse (non-breaking) în: `GET /api/public/buildings/{id}`, `GET /api/admin/hartablocuri/buildings/{id}`, și `building.truth_layer` din `_serialize_building` (Building Context client: `GET /api/properties/{id}/building-context` + `technical-record`).
- **UI:** (a) Client Building Context `PropertyTechnicalRecord.jsx` → `DerivedContextBlock` în `HartaBlocuriCard` („Context derivat (neverificat)" — Eră/Formă/Regim/Familie + carduri Candidate Typology, disclaimer legal explicit). (b) Observability modal → rânduri Familie proiect + carduri profil. (c) Admin Menu (`AdminLayoutMetronic.jsx`) → „HartaBlocuri · Observability" (/admin/harta-blocuri) + „HartaBlocuri · Import" (/admin/hartablocuri).
- **Teste:** `tests/test_hartablocuri_typology_iter225.py` (project_family + C1/C4 + integrare) — 21 teste. Total Truth Layer: 44/44 unit pass. E2E (iteration_224.json): backend 49/50 (1 skip legitim), frontend 100%, 0 issues.
- **Integritate confirmată:** 3408 total / 3406 HartaBlocuri / 2 PropManage · 0 raw modificate · 0 import · 0 schemă · 0 SEO/sitemap/Marketplace.
- **STOP:** BLOCAT — Plan Family, structure enrichment, SEO programatic, sitemap expansion, import production. Așteaptă aprobare explicită.


## 16. SEO Cluster Foundation — Faza 3 (Pilot, READ-ONLY, NEpublicat) — 2026-06
**Principiu:** layer SEO derivat peste `buildings` + Truth Layer. Zero publicare, zero atingere sitemap/robots/import/raw/schema/Truth Layer/Marketplace/House Health/Digital Twin/OAuth.
- **Modul:** `/app/backend/seo_clusters.py` — `list_pilot_clusters()`, `get_pilot_cluster(id)`, `build_cluster()`, `PILOT_CLUSTERS` (5). Taxonomie: Localitate · Eră · Formă · Typology Profile · Project Family.
- **Clustere pilot (Cluj-Napoca):** cluj-panou-p4 (C1, ~785), cluj-turn-inalt (C4, ~114), cluj-comunist-1977-1990 (~907), cluj-interbelic (~82), cluj-proiect-cf1 (~1124). Toate: `index=False`, `in_sitemap=False`, `published=False`, `status=pilot_prepared`, `indexability=prepared_noindex`.
- **Per cluster:** slug (`/blocuri/<city>/<value>`), canonical self, title/meta_title/meta_description(≤300)/H1/intro din agregate REALE (fără fabricare), distribuții (eră/regim/cartier/familie), confidence, quality_gate (prag ≥25 blocuri, anti thin-content), data_limits (disclaimere risc seismic/clasă energetică/renovare/conformitate — NU se deduc), internal_links (forward: Găsește-ți blocul/Cartea Casei/House Health-Scorul Casei/Audit-Marketplace/Digital Twin; inverse; related_guides reale), provenance (`neverificat`, Typology=Candidate).
- **API admin:** `GET /api/admin/seo/hartablocuri-clusters` + `/{cluster_id}` (require_role admin). Integrate în SEO Control Center existent.
- **Frontend:** sub-tab „HartaBlocuri" în `AdminSEO.jsx` (`HartaBlocuriClustersView`) — banner pilot + carduri cu NOINDEX/PILOT_PREPARED/NU ÎN SITEMAP + detaliu expandabil.
- **Teste:** `tests/test_seo_clusters_iter226.py` (24) + 13 teste API integrare (external URL) — 100% pass. E2E iteration_225.json: backend 100%, frontend 100%, 0 issues.
- **GARANȚIE verificată:** sitemap.xml + child sitemaps NU conțin `/blocuri/` · clusters existente intacte (building_hartablocuri pages=0) · Truth Layer neschimbat · integritate 3408/3406/2.
- **STOP:** publicarea SEO, sitemap expansion, generarea de pagini, indexability changes — BLOCATE până la aprobare explicită (P4).
