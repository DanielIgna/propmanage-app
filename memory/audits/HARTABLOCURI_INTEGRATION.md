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

