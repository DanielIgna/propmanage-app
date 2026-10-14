# Rădăcini — plan de implementare

Baze: [audit-agro-faza0.md](audit-agro-faza0.md), [audit-admin-roluri.md](audit-admin-roluri.md).
Decizii luate (2026-10-13): modul în aceeași aplicație; aceleași conturi; MVP fără plăți; terenuri în colecții noi; locația exactă e publică doar aproximativ; operator/manager = personal Rădăcini (`radacini_staff`), nu `role=operator` global; date dev în baza comună, doar în `app.radacini_*`, marcate `is_demo` local.

| Sprint | Conținut | Stare |
|---|---|---|
| S1 | Fundație + Membri + Terenuri + Personal (operator/manager) + coadă de verificare | gata (60 teste API, flux verificat în browser) |
| S2 | Cereri de teren + negociere + acorduri cu versiune | gata (155 teste S1+S2, flux verificat în browser) |
| S3 | Proiect agricol: membri, plan culturi, activități, contribuții | gata (264 teste S1–S3, verificat în browser) |
| S4 | Recoltă + alocare + piață locală (listări, rezervări, schimb) | gata (377 teste S1–S4) |
| S5 | Administrare Rădăcini (KPI, activitate, membri, moderare, GDPR, audit) + intrare în adminul PropManage + Knowledge Center | gata (52 teste; total 519) |
| S6 | Comunități, gospodării, decizii, hartă cu zone, distanță, dispute, pagini publice, fotografii | gata (S6+S7: 65 teste; regresie 519) |
| S7 | Necesar semințe/unelte, lucrări mecanizate și prestatori | gata |
| S8 | Pregătirea pilotului: termeni Rădăcini, onboarding, mobil/PWA, demo extins, dosar jurist, costuri | gata (suită completă: 591 teste) |
| S9 | Composesorate — model demonstrativ (registru, revendicări, documente, ședințe, mandate, petiții, calendar, finanțe, transparență, jurnal) | gata (23 teste S9; suita completă 613) |

---

## S1 — contract

### Reguli comune
- Toate rutele sunt sub `/api/radacini` (router existent `backend/routes/radacini/api.py`, flag `RADACINI_ENABLED`).
- Importuri din PropManage **doar prin** `backend/routes/radacini/bridge.py`.
- Colecții: `radacini_members`, `radacini_parcels`, `radacini_staff`. Niciun alt tabel nu se scrie.
- Fiecare document nou primește `is_demo: true` când `RADACINI_MARK_DEMO=true` (setat local). Script de curățare: `backend/scripts/radacini_purge_demo.py`.
- Datele se întorc cu `serialize_doc`, cu câmpul `id` string. Datele (date-urile calendaristice) sunt în ISO UTC.
- Evenimente prin `event_bus.emit("radacini.<x>", actor=user, payload={...})`.
- „Super-admin” = `role=="admin"` și `admin_scope` în (None, "general"). E tratat ca `manager`.

### Enumerări (`GET /meta`, fără autentificare)
```json
{
  "interests": [{"id":"grow","label":"Vreau să cultiv"},{"id":"consume","label":"Vreau produse locale"},{"id":"land","label":"Am teren"},{"id":"sell","label":"Vând produse"},{"id":"exchange","label":"Schimb produse"},{"id":"community","label":"Comunitate și evenimente"}],
  "offer_models": [{"id":"rent","label":"Arendă / închiriere"},{"id":"harvest_share","label":"Cultivare la parte din recoltă"},{"id":"fixed_fee","label":"Cultivare contra sumă fixă"},{"id":"mixed","label":"Model mixt"},{"id":"sale","label":"Vânzare"},{"id":"joint_project","label":"Proiect comun"}],
  "water_sources": [{"id":"well","label":"Fântână"},{"id":"river","label":"Râu / pârâu"},{"id":"network","label":"Rețea"},{"id":"irrigation","label":"Sistem de irigații"},{"id":"none","label":"Fără sursă cunoscută"}],
  "localities": ["Cluj-Napoca","Florești","Apahida","Baciu","Feleacu","Gilău","Jucu","Bonțida","Gherla","Dej","Turda","Câmpia Turzii","Huedin","Aghireșu","Sânpaul","Chinteni","Vultureni","Ciurila","Tureni","Mociu"]
}
```

### Membri
- `GET /members/me` (auth) → `{exists:false}` sau `{exists:true, member:{id,user_id,interests[],county,locality,bio,created_at,updated_at}}`
- `PUT /members/me` (auth) body `{interests: string[] (≥1, din enum), county: "Cluj", locality: string (din listă), bio?: string ≤500}` → `{member}` (upsert după `user_id`; emite `radacini.member_updated`).

### Terenuri (`radacini_parcels`)
Document: `{id, owner_user_id, title, county, locality, lat, lng, area_m2, access, water_sources[], current_crops[], description, availability_from?, availability_to?, offer:{models[], terms, price_ron_per_year?, harvest_share_percent?}, status, verification?:{by,at,decision,note}, archived_at?, is_demo?, created_at, updated_at}`

Stări: `draft → pending_verification → published | rejected`; `published ↔ paused`; ștergerea = `archived_at`.

| Metodă | Cale | Cine | Reguli |
|---|---|---|---|
| POST | `/parcels` | membru (dacă nu are încă interesul `land`, i se adaugă automat; fără profil → 400 „Completează profilul”) | validări: title 3–120, area_m2 100–10 000 000, lat 43.5–48.5, lng 20–30, locality din listă, offer.models ≥1 din enum, harvest_share_percent 1–90 doar dacă există `harvest_share`; status=`draft` |
| GET | `/parcels/mine` | proprietarul | fără arhivate; sortate după `updated_at` desc |
| GET | `/parcels` | public (fără autentificare) | doar `published`, nearhivate, fără `is_demo` (decât dacă `RADACINI_MARK_DEMO=true`); filtre `locality`, `model`; `limit` ≤ 50, `skip`; **coordonate rotunjite la 2 zecimale**, fără `owner_user_id`, cu `owner_name` = prenumele |
| GET | `/parcels/{id}` | public dacă e `published` (varianta aproximativă); proprietarul, managerul/super-adminul și operatorul **din zonele lui** (sau fără zone) văd tot; părțile unui acord semnat văd varianta aproximativă și dacă terenul e suspendat | 404 altfel |
| PATCH | `/parcels/{id}` | proprietarul, doar în `draft`/`rejected`/`paused` | aceleași validări (preț finit, ≤ 10 000 000); un teren `rejected` editat revine la `draft`; un teren `paused` al cărui conținut/locație se schimbă (title, description, lat, lng, locality, area_m2, access, water_sources, current_crops, offer) revine tot la `draft` și trebuie retrimis la verificare; orice tranziție e atomică (409 dacă starea s-a schimbat între timp) |
| POST | `/parcels/{id}/submit` | proprietarul, din `draft`/`rejected` | → `pending_verification`; emite `radacini.parcel_submitted` |
| POST | `/parcels/{id}/pause` · `/resume` | proprietarul | `published` → `paused` · `paused` → `published` (doar dacă n-a fost editat între timp, adică status încă `paused`, și fără acord activ) |
| DELETE | `/parcels/{id}` | proprietarul | setează `archived_at`; 409 dacă e `pending_verification` sau are acord activ (după finalizarea proiectului terenul e eliberat și poate fi șters) |

### Personal (`radacini_staff`)
Document: `{id, user_id, email, name, role: "operator"|"manager", areas: string[] (localități; gol = toate), created_at, created_by}`
- `GET /staff/me` (auth) → `{is_staff, role, areas}`; super-adminul primește `{is_staff:true, role:"manager", areas:[]}`.
- `GET /staff/queue` (operator/manager) → terenurile `pending_verification`, filtrate pe `areas` pentru operator; include coordonatele exacte și `owner_name`/`owner_email`.
- `POST /staff/parcels/{id}/verify` (operator/manager) body `{decision:"approve"|"reject", note?: string (obligatoriu la reject)}` → `published`/`rejected` + `verification`; notifică proprietarul (`notify`); emite `radacini.parcel_verified`.
- `GET /staff` · `POST /staff` `{email, role, areas[]}` (userul trebuie să existe în `users`) · `DELETE /staff/{user_id}`: doar managerul sau super-adminul.

### Frontend (`frontend/src/apps/radacini/`)
Navigație: Panou · Terenuri · Terenurile mele · Profil · Operator (doar dacă `staff/me.is_staff`) · Personal (doar manager) · Setări.
- **Panou:** fără profil → card „Completează profilul”; altfel carduri după interese (`land` → numărul de terenuri + „Adaugă teren”; `grow` → „Caută teren”; celelalte → „În curând”).
- **Profil** (`/radacini/profil`): interesele ca opțiuni selectabile, localitatea, bio.
- **Terenuri** (`/radacini/terenuri`): hartă (`PmMarkersMap`) + listă de carduri, filtre localitate/model; detaliu în `/radacini/terenuri/:id`.
- **Terenurile mele** (`/radacini/terenurile-mele`, `/nou`, `/:id/editare`): listă cu badge-uri de stare și acțiuni; formular cu selectare pe hartă (click = punct; centrul implicit Cluj-Napoca 46.7712, 23.6236).
- **Operator** (`/radacini/operator`): coada de verificare cu hartă mică, Aprobă / Respinge cu notă.
- **Personal** (`/radacini/personal`): listă + adăugare după email + ștergere.

---

## S2 — contract: cereri de teren, negociere, acorduri

### Reguli comune (în plus față de S1)
- Colecții noi: `radacini_land_requests`, `radacini_request_messages`, `radacini_agreements`. Sunt aceleași reguli (`is_demo`, `serialize_doc`, evenimente `radacini.*`, mesaje de eroare în română, validare → 400).
- **Atomicitate:** tranzițiile de stare se fac cu `update_one({"_id":…, "status": <stare așteptată>}, …)` și se verifică `modified_count == 1`, altfel 409. Așa evităm dubla acceptare sau dubla semnare.
- **„Părți”** = proprietarul terenului și solicitantul. Personalul Rădăcini (operator în aria lui, manager) și super-adminul pot **citi** cererile și acordurile, dar nu acționează în ele.
- **Expirare:** o cerere activă fără activitate de 30 de zile e tratată ca `expired`. Starea se calculează la citire și se salvează leneș, fără cron (din cauza egress-ului).
- Notificări (`notify`) către cealaltă parte la fiecare acțiune; linkuri `/radacini/cereri/{id}` și `/radacini/acorduri/{id}`.

### Cereri (`radacini_land_requests`)
Document: `{id, parcel_id, owner_user_id, requester_user_id, model, proposal:{area_m2, start_date, end_date, price_ron_per_year?, harvest_share_percent?, crops[], note?}, proposals_history:[{proposal, by_user_id, at}], status, last_activity_at, decided_at?, decline_reason?, agreement_id?, is_demo?, created_at, updated_at}`

Stări: `sent → viewed → negotiating → accepted | declined | withdrawn | expired`.
- `viewed`: setat automat la prima deschidere de către proprietar.
- `negotiating`: după primul mesaj sau prima contrapropunere.

| Metodă | Cale | Cine | Reguli |
|---|---|---|---|
| POST | `/parcels/{id}/requests` | membru, diferit de proprietar (fără profil → 400; i se adaugă interesul `grow`) | terenul trebuie să fie `published` (altfel 409); `model` ∈ `parcel.offer.models`; o singură cerere activă (`sent`/`viewed`/`negotiating`) per solicitant și teren (altfel 409); `area_m2` între 100 și suprafața terenului; `start_date` ≥ azi, `end_date` > `start_date`; `harvest_share_percent` (1–90) obligatoriu doar pentru `harvest_share`, interzis altfel; `note` ≤ 1000 → `{request}` cu status `sent` |
| GET | `/requests/sent` · `/requests/received` | autentificat | `{items}`; fiecare are și `parcel_title`, `parcel_locality`, `counterpart_name` |
| GET | `/requests/{id}` | părți, personal, super-admin | `{request, messages}`, mesajele sortate crescător |
| POST | `/requests/{id}/messages` | părți; nu în stări finale | body `{text}` 1–2000 → `{message}`; cererea devine `negotiating` |
| POST | `/requests/{id}/counter` | părți; nu în stări finale | body = o propunere completă (aceleași validări) → propunerea curentă intră în `proposals_history`; status `negotiating` → `{request}` |
| POST | `/requests/{id}/decline` | proprietar | body `{reason?}` ≤ 500 → `declined` |
| POST | `/requests/{id}/withdraw` | solicitant | → `withdrawn` |
| POST | `/requests/{id}/accept` | proprietar; din `sent`/`viewed`/`negotiating`; terenul încă `published` | atomic (pe `proposal_at`: 409 „Propunerea s-a schimbat între timp.”) → `accepted` + creează acordul v1 în `draft` din propunerea curentă → `{request, agreement}`; proprietarul nu acceptă o propunere scrisă de el însuși (409 „Așteaptă răspunsul solicitantului.”) și nu acceptă dacă terenul are acord activ |

### Acorduri (`radacini_agreements`)
Document: `{id, request_id, parcel_id, parties:[{user_id, role:"owner"|"cultivator", name}], model, terms:{area_m2, start_date, end_date, price_ron_per_year?, harvest_share_percent?, crops[], custom_clauses?, parcel_snapshot:{title, locality, area_m2}}, version, versions_history:[{version, terms, by_user_id, at}], signatures:[{user_id, version, signed_at}], status, legal_notice, signed_at?, cancelled_at?, cancel_reason?, is_demo?, created_at, updated_at}`

Stări: `draft → proposed → signed`; `draft`/`proposed` → `cancelled`.

`legal_notice` (text fix): „Acest acord consemnează înțelegerea dintre părți în platforma Rădăcini. Nu înlocuiește contractul de arendă/închiriere în forma cerută de lege și nici înregistrarea acestuia la primărie, unde este cazul.”

| Metodă | Cale | Cine | Reguli |
|---|---|---|---|
| GET | `/agreements` | autentificat | acordurile în care e parte → `{items}` |
| GET | `/agreements/{id}` | părți, personal, super-admin | `{agreement}` |
| PATCH | `/agreements/{id}` | părți; doar `draft`/`proposed` | body `{terms}` parțial (aceleași validări ca la propunere + `custom_clauses` ≤ 5000) → versiunea veche intră în `versions_history`, `version += 1`, semnăturile se șterg, status `draft` |
| POST | `/agreements/{id}/propose` | părți; din `draft` | → `proposed` (versiunea curentă e înghețată pentru semnare) |
| POST | `/agreements/{id}/sign` | părți; doar `proposed` | body `{version}` trebuie să fie egal cu `version` curentă (altfel 409); o singură semnătură per user și versiune; când toate părțile au semnat versiunea curentă → `signed`, `signed_at`; **terenul** primește `active_agreement_id` și trece în `paused`; celelalte cereri active pe teren → `declined`, cu motivul „Terenul a fost atribuit altui solicitant.”, iar celelalte acorduri `draft`/`proposed` pe același teren → `cancelled`, cu motivul „Terenul a fost atribuit altui acord.” (părțile sunt notificate); dacă după revendicarea terenului acordul nu mai poate fi marcat `signed` → terenul e eliberat și răspunsul e 409; un teren editat între timp (nu `published`/`paused`) nu poate fi revendicat (409) |
| POST | `/agreements/{id}/cancel` | părți; doar `draft`/`proposed` | body `{reason?}` → `cancelled` (cererea rămâne `accepted`; terenul nu se schimbă) |

**Modificare în S1:** `POST /parcels/{id}/resume`, `PATCH` și `DELETE` pe un teren cu `active_agreement_id` → 409 „Terenul are un acord activ.”

### Frontend
- **Detaliu teren:** butonul „Solicită terenul” (doar pentru cei care nu sunt proprietarii, teren `published`) deschide un formular cu model (din oferta terenului), suprafață, perioadă, preț sau procent, culturi și mesaj.
- **`/radacini/cereri`:** file *Trimise* / *Primite*, cu badge-uri de stare (sent=Trimisă, viewed=Văzută, negotiating=În negociere, accepted=Acceptată, declined=Refuzată, withdrawn=Retrasă, expired=Expirată).
- **`/radacini/cereri/:id`:**
  - propunerea curentă și istoricul propunerilor, conversația;
  - acțiunile după rol: Acceptă, Refuză, Contrapropunere, Retrage, Trimite mesaj;
  - link spre acord după acceptare.
- **`/radacini/acorduri`** și **`/radacini/acorduri/:id`:**
  - termenii, versiunea, istoricul versiunilor, semnăturile, nota legală vizibilă;
  - Editează termenii, Trimite spre semnare, Semnează (cu bifa „Am citit și sunt de acord cu versiunea X”), Anulează;
  - vizualizare de tipărit (`window.print`).
- **Navigație:** Cereri și Acorduri. **Panou:** numărul de cereri primite care așteaptă răspuns.

---

## S3 — contract: proiect agricol (membri, plan culturi, activități, contribuții)

### Decizii
- **Proiectul se creează automat** când acordul devine `signed`: titlul vine din teren, perioada din termeni.
- **Membri inițiali:** cultivatorul ca `coordinator` și proprietarul ca `owner`. Coordonatorul poate invita alți utilizatori existenți (după email) ca `participant` și poate promova un participant la `coordinator`.
- **Contribuțiile nu sunt bani, puncte sau drepturi.** Sunt o evidență, doar adăugare (append-only); corecțiile se fac prin înregistrări noi (`corrects_id`). Tipul „bani” consemnează doar o sumă cheltuită în afara platformei.
- **Confirmarea contribuțiilor o face un coordonator, alta decât autorul.** Contribuțiile unui coordonator le confirmă alt coordonator sau proprietarul.
- **Rotația culturilor:** doar avertizare, după familia culturii, dacă aceeași familie a fost pe același teren în proiectul anterior. Nu blochează nimic.

### Colecții
`radacini_projects`, `radacini_crop_plans`, `radacini_activities`, `radacini_contributions` (aceleași reguli ca în S1/S2).

**Proiect:** `{id, agreement_id, parcel_id, title, locality, area_m2, start_date, end_date, members:[{user_id, name, role:"owner"|"coordinator"|"participant", joined_at}], member_ids[], status:"active"|"completed", completed_at?, created_at, updated_at}`

| Metodă | Cale | Cine | Reguli |
|---|---|---|---|
| GET | `/projects` | autentificat | proiectele în care e membru → `{items}`, cu `role` (rolul meu) și contoare (planuri, activități viitoare, contribuții în așteptare) |
| GET | `/projects/{id}` | membri, personal, super-admin | `{project}` |
| POST | `/projects/{id}/members` | coordonator | `{email}` → utilizator existent (404 altfel), nu e deja membru (409) → `participant` |
| PATCH | `/projects/{id}/members/{user_id}` | coordonator | `{role:"coordinator"\|"participant"}`; rolul `owner` nu se schimbă; trebuie să rămână ≥1 coordonator |
| DELETE | `/projects/{id}/members/{user_id}` | coordonator (sau membrul însuși) | nu se poate elimina `owner`-ul, nici ultimul coordonator, nici o parte a acordului (409) |
| POST | `/projects/{id}/complete` | coordonator | `active` → `completed`; 409 „Există recolte neconfirmate.” dacă mai sunt recolte `recorded`; terenul e eliberat (`active_agreement_id` șters, `paused`) |

**Plan culturi** `{id, project_id, crop, family, area_m2, sow_date, expected_harvest_date?, expected_yield_kg?, notes?, status:"planned"|"sown"|"growing"|"harvested", created_by, created_at, updated_at}`
- `GET /projects/{id}/crops` (membri) → `{items, warnings:[string]}`; `warnings` = rotația + suprafața totală > suprafața proiectului.
- `POST /projects/{id}/crops` · `PATCH /crops/{id}` · `DELETE /crops/{id}` (coordonator): `crop` din `meta.crops` sau text liber (familia → `"other"`); suma suprafețelor ≤ suprafața proiectului (altfel 400); `expected_yield_kg` e etichetat în interfață ca **estimare**.
- `meta.crops`: `[{id, label, family}]`, cu cel puțin roșii, ardei, castraveți, varză, cartofi, ceapă, usturoi, morcovi, fasole, mazăre, porumb, grâu, dovlecei, salată, căpșuni. Familii: solanacee, cucurbitacee, brasicacee, liliacee, leguminoase, umbelifere, cereale, asteracee, rozacee, other.

**Activități** `{id, project_id, type:"planting"|"maintenance"|"irrigation"|"harvest"|"work_day"|"other", title, date, start_time?, duration_h?, slots?, participants:[user_id], crop_plan_id?, status:"scheduled"|"done"|"cancelled", notes?, created_by, created_at, updated_at}`
- `GET /projects/{id}/activities?from=&to=` (membri) → `{items}`, sortate după dată.
- `POST /projects/{id}/activities` · `PATCH /activities/{id}` (coordonator; doar `scheduled`).
- `POST /activities/{id}/join` · `/leave` (orice membru; `slots` e respectat → 409 când e plin; doar `scheduled`).
- `POST /activities/{id}/done` · `/cancel` (coordonator).

**Contribuții** `{id, project_id, member_user_id, member_name, kind:"labor_hours"|"materials"|"money"|"tools"|"land", amount, unit, description, activity_id?, date, status:"logged"|"confirmed"|"disputed", reviewed_by?, reviewed_at?, review_note?, corrects_id?, created_at}`
- `GET /projects/{id}/contributions?member=` (membri) → `{items, totals:[{member_user_id, member_name, kind, unit, confirmed, pending}]}`
- `POST /projects/{id}/contributions` (orice membru, pentru sine): `amount` > 0; unitatea implicită pe tip (`labor_hours` → „ore”, `money` → „RON”, restul text liber ≤ 20); `description` 3–300; `date` ≤ azi.
- `POST /contributions/{id}/review` (coordonator diferit de autor; dacă autorul e singurul coordonator, poate confirma proprietarul) `{decision:"confirm"|"dispute", note?}` (nota e obligatorie la `dispute`); doar din `logged`.
- Nu există PATCH sau DELETE. Corecția = o contribuție nouă cu `corrects_id`, iar cea veche rămâne în istoric.

### Frontend
- **Navigație:** Proiecte. **Panou:** cardul „Proiectele mele” (activitățile următoare + contribuțiile de confirmat).
- **`/radacini/proiecte`:** lista proiectelor.
- **`/radacini/proiecte/:id`**, cu file:
  - *Prezentare* (perioadă, suprafață, link spre acord, următoarele 5 activități, totaluri);
  - *Plan culturi* (tabel + formular, avertizări vizibile, bară de ocupare a suprafeței);
  - *Calendar* (listă pe săptămâni, butoane Particip / Nu mai particip, Marchează făcut);
  - *Contribuții* (formular, listă cu stări, Confirmă / Contestă pentru cine are dreptul, totaluri pe membru);
  - *Membri* (invită după email, schimbă rolul, elimină).
- **Avertisment permanent în fila Contribuții:** „Contribuțiile sunt o evidență a implicării. Nu reprezintă bani, puncte sau drepturi asupra recoltei; împărțirea recoltei urmează acordul semnat.”

### Pagina Progres (dev)
`/radacini/progres`: lista sprinturilor cu stare, ce se poate încerca (linkuri) și conturile demo (doar emailurile; parolele sunt în `backend/seed.py`). Se vede doar când `NODE_ENV !== "production"`.

---

## S4 — contract: recoltă, alocare, piață locală

### Decizii
- **Fără plăți online.** Plata se face la ridicare, în afara platformei, sau prin schimb. Platforma doar consemnează.
- **Recolta** o înregistrează un coordonator și o confirmă proprietarul (`owner`). Dacă proprietarul e și coordonator, confirmarea e automată.
- **Alocarea pornește din acord:** la `harvest_share`, proprietarul primește automat `harvest_share_percent` % (rotunjit la 0,1 kg); la celelalte modele, 0. Restul îl împart coordonatorii între membri. Fiecare primitor confirmă „Primit”.
- **Piața:** orice membru Rădăcini publică produse, nu doar din proiecte. Pe fiecare anunț se arată **prețul de referință** = mediana prețurilor active pentru același produs (normalizat: litere mici, fără diacritice) și aceeași unitate.
- **Fără monedă internă și fără sold de schimb:** „schimbul” e un text liber („ce aș primi în schimb”).

### Colecții
`radacini_harvests`, `radacini_allocations`, `radacini_listings`, `radacini_reservations`.

**Recoltă** `{id, project_id, crop_plan_id?, crop, quantity_kg, date, note?, recorded_by, status:"recorded"|"confirmed", confirmed_by?, confirmed_at?, created_at}`
- `GET /projects/{id}/harvests` (membri, personal) → `{items, totals:[{crop, quantity_kg}]}`
- `POST /projects/{id}/harvests` (coordonator; proiect activ) `{crop_plan_id?, crop?, quantity_kg>0 (≤ 1 000 000), date ≤ azi, note?}`: `crop` se ia din planul de cultură dacă există `crop_plan_id`. Planul trece în `harvested`. Se notifică proprietarul.
- `POST /harvests/{id}/confirm` (proprietarul; din `recorded`) → `confirmed`. **Alocările se pot face doar pe recolte `confirmed`.**

**Alocare** `{id, harvest_id, project_id, member_user_id, member_name, quantity_kg, basis:"agreement_share"|"manual", status:"allocated"|"received", received_at?, created_by, created_at}`
- La confirmarea recoltei, alocarea `agreement_share` pentru proprietar se creează automat, dacă procentul e > 0.
- `GET /harvests/{id}/allocations` (membri) → `{items, allocated_kg, remaining_kg}`
- `POST /harvests/{id}/allocations` (coordonator) `{member_user_id (membru al proiectului), quantity_kg>0}`: suma ≤ cantitatea recoltei (atomic față de alocările existente; 400 dacă depășește) → `{allocation}`
- `DELETE /allocations/{id}` (coordonator; doar `manual` și doar `allocated`)
- `POST /allocations/{id}/received` (primitorul) → `received`

**Anunț (listing)** `{id, seller_user_id, seller_name, product, product_key, category:"legume"|"fructe"|"cereale"|"lactate"|"ouă"|"miere"|"conserve"|"altele", unit:"kg"|"buc"|"legătură"|"borcan"|"litru", quantity_total, quantity_available, price_ron_per_unit?, mode:"sale"|"exchange"|"both", exchange_for?, locality, pickup_details, available_until?, project_id?, status:"active"|"closed", created_at, updated_at}`
- `GET /listings?locality=&category=&q=&mode=&skip=&limit≤50` (autentificat) → `{items, total}`: doar `active` cu `quantity_available > 0`; fiecare are `reference_price`, adică mediana sau `null` dacă există mai puțin de 2 prețuri.
- `GET /listings/mine` → `{items}` · `GET /listings/{id}` → `{listing}` (cu `reference_price`)
- `POST /listings` (membru) – validări:
  - `product` 2–80;
  - `quantity_total` > 0;
  - `price_ron_per_unit` obligatoriu dacă `mode` ∈ {sale, both} (0 < preț ≤ 10 000);
  - `exchange_for` obligatoriu dacă `mode` ∈ {exchange, both} (3–300);
  - `locality` din listă;
  - `pickup_details` 3–300;
  - `available_until` ≥ azi;
  - `project_id` opțional: vânzătorul trebuie să fie membru al proiectului.
- `PATCH /listings/{id}` (vânzătorul; doar `active`): `quantity_total` nu poate scădea sub cantitatea deja rezervată sau confirmată.
- `POST /listings/{id}/close` (vânzătorul) → `closed`; rezervările `requested` se anulează automat și se notifică cumpărătorii.

**Rezervare** `{id, listing_id, seller_user_id, buyer_user_id, buyer_name, quantity, mode:"cash_on_pickup"|"exchange", exchange_offer?, message?, status:"requested"|"confirmed"|"picked_up"|"cancelled"|"no_show"|"declined", rating?, rating_comment?, created_at, updated_at}`
- `POST /listings/{id}/reservations` (membru ≠ vânzător; anunț `active`): `quantity` între 0 și `quantity_available`; `mode` compatibil cu anunțul; `exchange_offer` obligatoriu la `exchange`; o singură rezervare `requested`/`confirmed` per cumpărător și anunț (409) → `requested`.
- `GET /reservations/mine?role=buyer|seller` → `{items}`, cu `listing_product`, `listing_unit`, `counterpart_name`
- `POST /reservations/{id}/confirm` (vânzătorul; din `requested`): **scade atomic `quantity_available`** (409 dacă nu mai e destulă cantitate) → `confirmed`
- `POST /reservations/{id}/decline` (vânzătorul; din `requested`) → `declined`
- `POST /reservations/{id}/cancel` (cumpărătorul din `requested`/`confirmed`, vânzătorul din `confirmed`): la `confirmed`, cantitatea se returnează în `quantity_available`.
- `POST /reservations/{id}/picked-up` (vânzătorul; din `confirmed`) → `picked_up` · `POST /reservations/{id}/no-show` (vânzătorul; din `confirmed`) → `no_show`; cantitatea se returnează.
- `POST /reservations/{id}/rate` (cumpărătorul; doar `picked_up`, o singură dată) `{rating 1–5, comment? ≤ 300}`
- `GET /sellers/{user_id}/rating` → `{avg, count}` (din rezervările evaluate)

### Frontend
- **Proiect:** fila nouă *Recoltă* (înregistrare, confirmare de către proprietar, alocări pe membri cu bara alocat/rămas, „Am primit”, totaluri pe cultură). Din recoltă se poate publica rapid un anunț în piață, completat cu produsul, cantitatea alocată mie și `project_id`.
- **`/radacini/piata`:** filtre (localitate, categorie, căutare, mod), carduri cu preț/unitate, **preț de referință**, disponibil, vânzător cu rating.
- **`/radacini/piata/:id`:** detaliu + dialogul de rezervare (cantitate, plată la ridicare sau schimb + ce oferi, mesaj).
- **`/radacini/piata/nou`** și **`/radacini/piata/:id/editare`:** formularul anunțului.
- **`/radacini/rezervari`:** file *Cumpăr* / *Vând*, cu acțiuni după stare (Confirmă / Refuză / Ridicat / Nu s-a prezentat / Anulează / Evaluează).
- **Navigație:** Piață, Rezervări. **Panou:** cardul „Vreau produse locale” arată anunțurile noi din localitatea mea; cardul „Vând produse” arată rezervările de confirmat.
- **Text vizibil în piață:** „Plata se face la ridicare, direct între voi. Rădăcini nu procesează plăți.”

---

## Reverificare 2026-10-13 (effort ridicat): remedieri și ce lipsește

Revizuire de cod (backend, frontend) și reverificarea auditurilor față de `master-prompt.md`. Corecțiile la audituri sunt consemnate ca erată în fiecare document.

### Runda 1 de remedieri (aplicată)
- **Securitate și date:**
  - textul utilizatorilor e curățat în emailuri;
  - un teren publicat și editat revine la verificare;
  - operatorul vede detaliile doar în aria lui;
  - datele demo și de test nu apar public decât în modul demo;
  - în modul impersonare, acțiunile cu efect juridic sunt blocate.
- **Concurență:**
  - semnarea eliberează terenul la eșec și anulează acordurile concurente;
  - proiectul se creează o singură dată (upsert);
  - alocarea automată a proprietarului e serializată;
  - cererile și rezervările nu se mai dublează;
  - tranzițiile de stare ale terenului sunt condiționate.
- **Reguli:**
  - terenul se eliberează la finalizarea proiectului;
  - proiectul nu se finalizează cu recolte neconfirmate;
  - părțile acordului nu pot fi eliminate;
  - „azi” se calculează în fusul Europe/Bucharest.
- **Egress:**
  - căutarea în piață folosește token-uri, nu `$regex`;
  - ratingul e agregat pe vânzător;
  - completarea proiectelor citește doar id-uri;
  - notificările pleacă în fundal.
- **Frontend:**
  - pagina Progres e reparată și exclusă din build-ul de producție;
  - 20 de remedieri (date, butoane, cereri redundante, stări de eroare, accesibilitate);
  - **intrarea Rădăcini** e proprie: `/radacini/login`, titlu „Rădăcini”, fără widget-urile PropManage, `noindex`.

### Runda 2 (aplicată 2026-10-14; migrația — doar colecțiile, fără indexuri btree — aplicată pe baza comună pe 2026-10-14)
1. `RADACINI_ENABLED` și `NEXT_PUBLIC_RADACINI_ENABLED` **oprite implicit** (pornite doar local, prin `launch.json`), ca un merge în `main` să nu expună modulul.
2. **Migrație** `supabase/migrations/*_radacini_collections.sql`: `app.create_collection` pentru toate colecțiile `radacini_*` + indexuri pe expresii (user_id, parcel_id, project_id, listing_id, status). **Se aplică pe bază doar cu aprobare.**
3. **Poarta juridică:** cererile pe modelele `sale` și `joint_project` sunt dezactivate („necesită aviz juridic”); `mixed` permite preț și procent. Termeni de membru cu clauza „fără cantitate garantată”, prin mecanismul versionat din `legal.py`.
4. **Locația exactă** pentru părțile unui acord semnat (decizia 6), cu jurnal de acces.
5. **GDPR:** `GET /api/radacini/me/export` (toate datele Rădăcini ale utilizatorului) și cerere de ștergere; ROPA/DPIA pentru locație și minori.
6. **Audit:** acțiunile personalului (verificare, personal, moderare) trec prin `admin_console.audit()` (prin `bridge.py`).
7. **Rate limit** pe rutele publice `/api/radacini/parcels*` și `/meta`.
8. **Notificări Rădăcini:** subiect „Rădăcini: …”, link absolut, fără „PropManage:” (wrapper propriu peste email/push, fără modificarea `services.notify`).
9. **Dovada semnăturii:** IP, user-agent și hash-ul termenilor pe fiecare semnătură; PDF server-side (reportlab, cu fonturi DejaVu în imagine) mai târziu.

### Ce lipsește față de cerințe și unde intră
| Cerință (master prompt) | Stare | Decizie |
|---|---|---|
| Gospodării / cont familial, copii | lipsă | S6, după politica pentru minori (GDPR, consimțământ parental) |
| Comunități agricole (modulul 3), decizii/voturi | lipsă | S6 |
| Necesar de semințe și unelte, inventar | lipsă | S7 |
| Lucrări mecanizate prin specialiști PropManage (Capability Engine) | lipsă | S7 |
| Producție estimată vs efectivă (raport) | parțial | S5 (rapid: comparație în Prezentare proiect) |
| Echivalent de schimb, oferte mixte bani + produse | parțial (text liber) | rămâne text în pilot; fără valoare transferabilă (juridic) |
| Comenzi și livrări | parțial (ridicare personală) | amânat după pilot |
| Abonament 5 €/lună, facturare familie | amânat | după pilot; analiză TVA, taxe Stripe pe sume mici, termeni „fără cantitate garantată” |
| Investiții colective | amânat | necesită aviz juridic (ASF, asociere, coproprietate) |
| Gamification | amânat | după pilot; colecție separată, fără legătură cu drepturile |
| Hartă cu terenuri/proiecte ca zone (poligoane) | lipsă | S6 |
| Matching / căutare după distanță | lipsă | S6 (filtru pe rază, fără PostGIS în pilot) |
| Operator: mod asistat, martor la recoltă, puncte de ridicare, neconformități | parțial (doar verificare) | S5–S6 |
| Dispute și mediere (contribuții contestate, neprezentări, recoltă) | lipsă | S6 (tiparul `disputes.py` + medierea operatorului) |
| Pagini publice fără cont (hartă terenuri, piață) | lipsă | S6 (SSR) |
| Fotografii teren/recoltă | lipsă | S6 (Supabase Storage, privat pentru documente) |
| Integrare admin, KPI, Knowledge Center | lipsă | S5 |
| Costuri în euro (Maps, email, Stripe, juridic) | lipsă | de completat înainte de pilot |

### Rularea testelor Rădăcini
`cd backend && ./venv/bin/python -m scripts.radacini_purge_demo --tests-only --apply`, apoi `REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/test_radacini_s1.py tests/test_radacini_s2.py tests/test_radacini_s3.py tests/test_radacini_s4.py -q --noconftest` (serverul local trebuie pornit; testele scriu în `app.radacini_*` din baza comună). Numărul raportat (377) include cazurile parametrizate (354 de funcții `test_*`).

---

## S5 — contract: administrarea Rădăcini

### Decizii
- **Administrarea stă în aplicația Rădăcini:** secțiunea `/radacini/admin/*`, vizibilă doar personalului cu rol `manager` (inclusiv super-adminul). Nu în adminul PropManage, care are 113 intrări și nu aplică permisiuni pe zone.
- **În adminul PropManage** se adaugă o singură intrare, „Rădăcini” (zona business), care deschide `/radacini/admin`. Modificarea e minimă, în `AdminLayoutMetronic.jsx`.
- **Fluxul de activitate** se citește din `activity_events` (filtrat `radacini.*`): acolo scrie deja `event_bus`. Nu se modifică panourile PropManage.
- **KPI-urile** sunt calculate la cerere, cu proiecții și limite, plus un cache în memorie de 5 minute (egress).
- **Knowledge Center:** noduri `radacini:*` în `backend/data/enterprise_registry.json` și `docs/radacini/DECISION_REGISTER.md`.

### Backend (`/api/radacini/admin/*`, doar `manager`)
- `GET /admin/kpis` → `{members, members_by_interest{}, parcels_by_status{}, requests_by_status{}, agreements_signed, projects_active, harvest_kg_confirmed, listings_active, reservations_by_status{}, pending_verification, open_deletion_requests, generated_at}`
- `GET /admin/activity?limit≤100&before=` → evenimentele `radacini.*` din `activity_events`, cu numele actorului (fără email), cele mai noi primele.
- `GET /admin/members?q=&interest=&locality=&skip&limit≤50` → membri cu nume, localitate, interese, număr de terenuri, proiecte și anunțuri.
- `GET /admin/parcels?status=&locality=` · `GET /admin/listings?status=` · `POST /admin/listings/{id}/close` (moderare, cu motiv; notifică vânzătorul; audit).
- `GET /admin/deletion-requests` · `POST /admin/deletion-requests/{id}/resolve` `{decision:"done"|"rejected", note}`. Ștergerea efectivă e manuală în pilot; aici se marchează și se notifică.
- `GET /admin/audit?limit` → intrările de audit Rădăcini (din jurnalul admin, filtrate pe acțiunile `radacini.*`).

### Frontend (`/radacini/admin`, navigația „Administrare”, doar manager)
- **Prezentare:** carduri KPI (membri, terenuri pe stări, cereri, acorduri semnate, proiecte active, kg recoltate, anunțuri active, rezervări) și grafice simple.
- **Activitate:** fluxul evenimentelor, cu filtru pe tip.
- **Membri:** tabel cu căutare și filtre.
- **Moderare:** terenuri pe stări (link spre coada operatorului) și anunțuri, cu închidere motivată.
- **Cereri GDPR:** listă și rezolvare.
- **Personal și Conturi de test:** linkuri spre paginile existente.

---

## S6 — contract: comunități, gospodării, decizii, hartă, distanță, dispute, pagini publice, fotografii

### Reguli comune (în plus față de S1–S5)
- Colecții noi: `radacini_communities`, `radacini_community_members`, `radacini_community_posts`, `radacini_households`, `radacini_consents`, `radacini_decisions`, `radacini_disputes`, `radacini_photos`. Aceleași reguli: `is_demo`, mesaje în română, validare → 400, 409 la conflict, notificări prin `safe_notify`, audit prin `audit_staff` pentru acțiunile personalului.
- **Integrarea în fișierele comune ale modulului** (`api.py`, `frontend/src/apps/radacini/{api.js,routes.jsx,config.js}`) o face coordonatorul. Fiecare parte își are propriul fișier de rute backend și propriul `api_<parte>.js` în frontend.
- După crearea colecțiilor se actualizează migrația (`app.create_collection`), care se aplică idempotent.

### A. Comunități (`communities.py`)
- **Comunitate:** `{id, name 3–80, locality (din listă), description ≤1000, visibility:"open"|"closed", created_by, members_count, created_at}`. Creatorul devine `coordinator`.
- **Membru:** `radacini_community_members {community_id, user_id, name (prenume), role:"coordinator"|"member", status:"active"|"pending", joined_at}`, unic pe (community, user), prin upsert.
- **Rute:**
  - `GET /communities?locality=&q=` (autentificat) și `GET /communities/{id}`, cu rolul meu;
  - `POST /communities`;
  - `POST /communities/{id}/join` (open → `active`, closed → `pending`) și `/leave` (ultimul coordonator nu poate pleca);
  - `POST /communities/{id}/members/{uid}/approve|reject|promote` (doar coordonator).
- **Anunțuri:** `GET/POST /communities/{id}/posts` (membri activi; text 1–2000; coordonatorul poate fixa unul sus) și `DELETE /posts/{id}` (autorul sau coordonatorul).

### B. Gospodării și consimțământ (`households.py`)
- **Gospodărie:** `{id, name, owner_user_id, members:[{user_id?, name, relation, is_minor, birth_year?}], created_at}`. Un utilizator e titular al cel mult unei gospodării.
- **Minorii** nu au cont: doar prenume și anul nașterii. Adăugarea lor cere `parental_consent: true`, înregistrat în `radacini_consents {user_id, kind:"minor_data", subject_name, version:"2026-10", at, ip, user_agent}`.
- **Adulții** se adaugă după email (cont existent). Contul primește o invitație, pe care o acceptă (`POST /households/{id}/accept`).
- **Rute:** `GET /households/mine` · `POST /households` · `POST /households/{id}/members` · `DELETE /households/{id}/members/{index_or_uid}` · `POST /households/{id}/accept`.
- **GDPR:** exportul (`gdpr.py`) include gospodăria și consimțămintele.

### C. Decizii și vot (`decisions.py`)
- **Decizie:** `{id, scope:"community"|"project", scope_id, question 5–200, options[2–6], closes_at (în viitor), created_by, status:"open"|"closed", votes:[{user_id, option_index, at}]}`.
- **Cine:** creează un coordonator al comunității sau proiectului; votează orice membru activ, o singură dată (atomic). Rezultatele sunt vizibile după ce ai votat sau după închidere; se închide automat la citire după `closes_at`.
- **Rute:** `GET /decisions?scope=&scope_id=` · `POST /decisions` · `POST /decisions/{id}/vote` · `POST /decisions/{id}/close` (creatorul).

### D. Hartă cu zone și distanță (`parcels.py`, `geo.py`)
- **Poligon:** terenul primește opțional `geometry` (GeoJSON Polygon, 3–100 de vârfuri, în limitele României, fără auto-intersecție simplă). Se calculează `geometry_area_m2` (formula sferică), iar dacă diferă cu peste 30% de `area_m2` apare doar un avertisment.
- **Cine vede poligonul:** proprietarul, părțile unui acord semnat și personalul pe aria lui. Publicul vede tot cercul aproximativ.
- **Căutare după distanță:** `GET /parcels?near=lat,lng&radius_km=1–100`. Filtrul folosește un dreptunghi pe lat/lng (`$gte/$lte`, tradus în SQL), apoi distanța reală calculată în Python. Fiecare rezultat are `distance_km`, calculat pe coordonatele rotunjite; sortarea e după distanță. Același parametru e disponibil la `GET /listings`, pe localitate: centrele localităților din Cluj sunt în `constants.LOCALITY_CENTERS`.

### E. Dispute și mediere (`disputes.py`)
- **Dispută:** `{id, scope_type:"contribution"|"reservation"|"harvest"|"agreement", scope_id, opened_by, against_user_id, reason 10–1000, status:"open"|"in_mediation"|"resolved"|"rejected", mediator_user_id?, messages:[{user_id, text, at}], resolution?, locality, created_at}`.
- **Cine deschide:** doar părțile obiectului disputat (contestatarul contribuției, cumpărătorul sau vânzătorul rezervării, proprietarul sau coordonatorul recoltei, părțile acordului). Pe un obiect poate exista o singură dispută deschisă.
- **Mediere:** personalul o preia (operator pe arie sau manager) → `in_mediation`. Mesajele le scriu părțile și mediatorul. Mediatorul o închide cu rezoluția (`resolved`/`rejected`, notă obligatorie). Totul trece prin audit și notificări.
- **Rute:** `POST /disputes` · `GET /disputes/mine` · `GET /disputes/{id}` · `POST /disputes/{id}/messages` · `GET /staff/disputes` · `POST /disputes/{id}/take` · `POST /disputes/{id}/resolve`.

### F. Pagini publice fără cont
- **Backend:** `GET /public/listings` (rate limit; doar anunțuri active nedemo; prenume vânzător; fără `pickup_details`) și `GET /public/communities` (doar `open`; fără membri).
- **Frontend:** rute în afara layout-ului autentificat: `/radacini/descopera` (prezentare + hartă cu terenuri aproximative + piață + comunități, cu butoanele „Intră” / „Creează cont”). Pagina e `noindex` în pilot; indexarea se decide la lansare.

### G. Fotografii (`photos.py`)
- **Încărcare:** `POST /photos` (multipart: `target_type:"parcel"|"listing"|"harvest"`, `target_id`, fișier). Pot încărca doar proprietarul terenului, vânzătorul, respectiv coordonatorul proiectului.
- **Fișiere acceptate:** jpeg, png sau webp, ≤5 MB, maximum 6 pe țintă. Serverul **elimină metadatele EXIF (inclusiv GPS)**, redimensionează la cel mult 1600 px și salvează JPEG în Supabase Storage (`storage_client.put_object`, cale `radacini/<target_type>/<id>/<uuid>.jpg`).
- **Afișare:** `GET /photos/{id}` (stream; drepturi de citire ca la țintă; terenurile și anunțurile publicate sunt publice) și `DELETE /photos/{id}` (cel care a încărcat sau proprietarul țintei).

---

## S7 — contract: necesar de semințe și unelte, lucrări mecanizate

### A. Necesar pe proiect (`needs.py`)
- **Necesar:** `radacini_project_needs {id, project_id, kind:"seeds"|"tools"|"materials"|"service", item 2–80, quantity>0, unit, status:"needed"|"covered"|"cancelled", pledges:[{user_id, name, quantity, at, fulfilled:false}], created_by}`.
- **Cine:** coordonatorul adaugă și anulează; membrii promit cantități (atomic, suma ≤ necesar), apoi marchează „adus”. La „adus” se creează automat o contribuție `materials`/`tools` în `logged`, cu legătură spre necesar. Necesarul devine `covered` când suma promisiunilor aduse ≥ cantitate.
- **Rute:** `GET/POST /projects/{id}/needs` · `POST /needs/{id}/pledge` · `POST /needs/{id}/pledges/{i}/fulfilled` · `POST /needs/{id}/cancel`.

### B. Lucrări mecanizate și prestatori (`service_requests.py`)
- **Prestator:** `radacini_providers {user_id, name, services[] din constants.SERVICE_TYPES (arat, discuit, frezat, semănat mecanizat, irigații, transport, consultanță agronomică, tratamente), localities[], note, active}`. Orice utilizator PropManage poate deveni prestator; specialiștii PropManage sunt invitați să se înscrie.
- **Cerere de lucrare:** `radacini_service_requests {id, project_id, service_type, description, area_m2?, window_from, window_to, locality, status:"open"|"assigned"|"done"|"cancelled", offers:[{provider_user_id, name, price_ron_indicative?, message, at}], assigned_provider_user_id?}`.
- **Fluxul:**
  - coordonatorul creează cererea;
  - prestatorii activi cu serviciul și localitatea potrivite sunt notificați;
  - prestatorii trimit ofertă (una per prestator);
  - coordonatorul alege una (`assigned`), apoi marchează `done`, cu evaluare 1–5 a prestatorului.
- **Fără plăți în platformă:** prețul e orientativ, iar plata se face direct.
- **Rute:** `GET/PUT /providers/me` · `GET /providers?service=&locality=` · `GET/POST /projects/{id}/service-requests` · `GET /service-requests/open` (pentru prestatori) · `POST /service-requests/{id}/offers` · `POST /service-requests/{id}/assign` · `POST /service-requests/{id}/done` · `POST /service-requests/{id}/cancel`.
- Legătura cu Capability Engine (`routes/capability_engine.py`) rămâne pentru după pilot: catalogul de capabilități agricole e date comune.

### Frontend S6/S7
- **Pagini noi:** Comunități (listă, detaliu cu anunțuri, membri, decizii), Gospodăria mea, Dispute (ale mele + coada de mediere pentru personal), Prestator (profilul meu + lucrări deschise).
- **Fila Necesar** în proiect și **fila Lucrări** în proiect (cereri de lucrări + oferte).
- **Hartă:** desenare de poligon în formularul terenului și afișarea poligonului; filtru „lângă mine / lângă localitate + rază” în Terenuri și Piață.
- **Fotografii:** galerie și încărcare pe teren, anunț și recoltă.
- **Buton „Deschide o dispută”** pe contribuții, rezervări, recolte și acorduri.
- **Pagina publică** `/radacini/descopera`.

---

## S8 — contract: pregătirea pilotului (Cluj)

### Decizii
- **Termenii Rădăcini sunt separați de cei PropManage.** Poarta legală PropManage (`LegalGate`, `legal_documents` cu `mandatory`) se aplică tuturor utilizatorilor PropManage. Documentele Rădăcini stau deci în colecții proprii, după același model: versiune, acceptare cu IP, user-agent și dată, istoric.
- **Acceptarea termenilor curenți e obligatorie** pentru acțiunile cu efect: publicare teren, cerere, semnare, anunț, rezervare, înscriere în proiect/comunitate. Navigarea și citirea rămân libere.
- **Textele** sunt redactate de echipa tehnică ca **draft pentru jurist** (marcat vizibil „Versiune pilot — în revizuire juridică”). Includ: rolul platformei (intermediar de informații, fără plăți), „fără producție sau cantitate garantată”, acorduri care nu înlocuiesc contractul de arendă și înregistrarea la primărie, schimbul fără valoare monetară, reguli pentru minori, date de localizare, dispute și mediere, moderare.
- **PWA:** un manifest separat pentru `/radacini` (nume „Rădăcini”, iconițe, `start_url: /radacini`, `scope: /radacini/`). **Fără service worker nou**, ca să nu interfereze cu `sw.js` existent din PropManage. Pozele pot fi făcute direct din cameră (`capture="environment"`).

### Backend (`legal_terms.py`)
- `radacini_legal_documents {type:"terms"|"privacy", version, title, body (markdown), summary, active, created_at}`; un seed idempotent cu versiunea `2026-10-pilot`, ambele documente.
- `radacini_legal_acceptances {user_id, type, version, accepted_at, ip, user_agent, revoked_at?}`.
- **Rute:**
  - `GET /legal/documents` (public): documentele active;
  - `GET /legal/me` → `{required:[{type,version}], accepted:[…], ok:bool}`;
  - `POST /legal/accept {type, version}`, blocat în impersonare;
  - admin (manager): `GET /admin/legal/acceptances?type=&version=`.
- **Dependența `require_terms`**, aplicată pe rutele de acțiune enumerate mai sus: 428 „Acceptă termenii Rădăcini pentru a continua.”, cu `detail.code = "terms_required"`. Conturile de test (`is_demo_account`) acceptă automat la `ensure`. Testele existente își acceptă termenii în setup.
- **GDPR:** exportul include acceptările.

### Onboarding (`members.py` + frontend)
- `radacini_members.onboarding {completed_at?, steps_done[]}`.
- `POST /members/me/onboarding {step}` · `POST /members/me/onboarding/complete`.
- **Frontend:** la prima intrare, un ghid în 3–4 pași:
  1. acceptarea termenilor;
  2. alegerea intereselor și a localității;
  3. ce poți face, după interese, cu linkuri directe;
  4. opțional, notificări.

  Poate fi reluat din Setări.

### Frontend
- Pagina `/radacini/termeni` (public: termeni + confidențialitate, cu versiune și eticheta „în revizuire juridică”).
- Dialogul global „Acceptă termenii” se deschide automat la răspunsul 428 (interceptor în modulul Rădăcini) și reia acțiunea după acceptare.
- **Mobil:** bara de navigare jos pe ecrane mici (Panou, Terenuri, Piață, Proiecte, Meniu), butoane de minimum 44 px, galeria foto cu `capture`.
- **Manifest PWA** pentru `/radacini` (din `frontend/public`, fără a atinge manifestul PropManage) și meta `theme-color` pe paginile Rădăcini.

### Demo extins (`test_accounts.py`)
Scenariul generat include și: o comunitate deschisă (Florești) cu anunțuri și o decizie în vot, gospodăria Mariei (un adult, un minor cu consimțământ), o dispută în mediere (rezervare), necesar pe proiect cu promisiuni, un prestator (Vasile) și o cerere de lucrare cu ofertă, plus termenii acceptați pentru toate conturile de test.

### Documente
- `docs/radacini/DOSAR_JURIST.md`: întrebările juridice concrete, cu trimitere la funcțiile din aplicație. Acoperă arenda și înregistrarea, vânzarea de alimente (DSV), barterul și fiscalitatea, rolul de intermediar, GDPR (localizare, minori, consimțăminte), investițiile colective (ASF), disputele și răspunderea, plus termenii pilot de revizuit.
- `docs/radacini/COSTURI_PILOT.md`: estimări în euro pe lună pentru pilot (100–500 de membri), cu ipoteze explicite: Supabase (DB, egress, storage), Railway, Cloudflare, Google Maps/Geocoding (sau OSM gratuit), email, jurist (estimare de piață, de validat).

---

## S9 — contract: modulul Composesorate (model demonstrativ)

Structura logică și motivarea: `docs/radacini/composesorate/MODUL_DESIGN.md`. **Doar date fictive în S9.** Funcțiile digitale completează procedurile din statut; voturile din aplicație sunt consultative.

### Reguli comune
- Prefix `/api/radacini/assoc`. Colecții `radacini_assoc_*`, plus `radacini_associations`.
- **Rol în asociație:** membru verificat (rând din registru legat de `user_id`), CA (`council_role` ∈ president, vice_president, secretary, cashier, forest_pasture), cenzor (`censor`). **Super-adminul Rădăcini și managerul** au acces de operator: pot crea asociații și vedea tot. **Operatorul** are acces doar la asociațiile la care a fost asignat de manager.
- **Jurnalul de răspundere:** orice scriere a CA, a operatorului sau a managerului adaugă `radacini_assoc_audit {association_id, actor_user_id, actor_role, action, target_type, target_id, before?, after?, at}`. Jurnalul e **doar cu adăugare** și nu are ruta de ștergere. Membrii văd un rezumat (acțiune, rol, dată), cenzorii și managerii îl văd complet.
- **Documentele** sunt fișiere private în Supabase Storage (`radacini/assoc/<id>/docs/<uuid>.<ext>`, pdf/jpeg/png/webp, ≤10 MB), cu SHA-256 calculat pe server. Nu se șterg; se adaugă o versiune nouă (`replaces_id`). Fiecare descărcare se înregistrează în `radacini_assoc_doc_access`.
- **Notificări** prin `safe_notify`; conturile de test nu primesc email. Acțiunile cu efect juridic blochează impersonarea.

### Reguli statutare configurabile (`association.rules`)
Implicit, valorile din statutul Ciunca:

```json
{"aga_months_deadlines": ["04-30", "11-30"], "balance_deadline": "03-31", "budget_month": 11, "pasture_plan_deadline": "10-31",
 "convocation_days": 15, "quorum_first": "majority_shares", "second_convocation_day": 7,
 "major_quorum": {"members_majority": true, "shares_fraction": 0.6667},
 "extraordinary_petition": {"members_fraction": 0.25, "shares_fraction": 0.25},
 "agenda_petition": {"members_fraction": 0.10, "days_before": 5},
 "proxy_limits": {"max_members": 5, "max_shares_fraction": 0.05},
 "max_member_shares_fraction": 0.05, "contest_days": 15, "prescription_years": 5,
 "profit_split": {"council_max": 0.10, "reserve_max": 0.20, "charity_max": 0.20, "investment_max": 0.20},
 "info_request_days": 30, "censor_check_months": [3, 6, 9, 12]}
```

### A. Asociații, registru, revendicări (`assoc_core.py`)
- `POST /assoc` (manager): `{name, type, localities[], description, legal{cui?, court?, registered_at?}, rules?, patrimony[{cf, topo, area_ha, category, toponym}]}`.
- `GET /assoc` (public, fără date personale): nume, localități, suprafață totală, număr de membri, scor de transparență. `GET /assoc/{id}` (public + secțiunile mele, dacă sunt membru) · `PATCH /assoc/{id}` (CA/manager).
- `GET /assoc/{id}/me` → rolul meu, rândul meu din registru (cote, surse), revendicările mele.
- **Registru:**
  - `GET /assoc/{id}/members` (CA, cenzori, operator): filtre pe stare și căutare;
  - `POST /assoc/{id}/members` (CA): un rând;
  - `POST /assoc/{id}/members/import` (CA/manager): CSV cu `code,name,shares,sources,status,locality`, validat, cu raport de erori;
  - `PATCH /assoc/{id}/members/{mid}` (CA): stare, cote, surse, funcție; schimbarea cotelor cere `reason` + `document_id` opțional.
- **Participare:** `GET /assoc/{id}/participation` → `{total_shares, members_count, active_members, active_shares, unknown_shares, deceased_unresolved, quorum_needed_shares, gap_to_quorum, by_status{}}`.
- **Revendicări:**
  - `POST /assoc/{id}/claims` (utilizator autentificat): `{kind:"self"|"heir", member_code?, name_on_record?, relation?, note, document_ids[]}`;
  - `GET /assoc/{id}/claims` (CA) · `GET /assoc/claims/mine`;
  - `POST /assoc/claims/{cid}/decide` (CA: `{decision:"approve"|"reject", note (obligatorie la reject), member_id?}`). La aprobare: `self` leagă `user_id` de rândul existent și îl trece în `confirmed`; `heir` creează un rând nou cu `status: heir_pending` până la decizia AGA.

### B. Documente, ședințe, mandate, petiții, cereri (`assoc_governance.py`)
- **Documente:**
  - `POST /assoc/{id}/documents` (CA/operator, multipart): `type, title, date, visibility (members|council), replaces_id?`;
  - `GET /assoc/{id}/documents` (după vizibilitate);
  - `GET /assoc/documents/{did}/file` (stream, înregistrează accesul);
  - `GET /assoc/documents/{did}/access-log` (CA, cenzori).
- **Ședințe:**
  - `POST /assoc/{id}/meetings` (CA): `{kind:"aga_ordinary"|"aga_extraordinary"|"council", date, place, agenda[{title, details}], material_ids[]}`;
  - `POST /meetings/{mid}/convene` (CA): trimite notificări tuturor membrilor activi/confirmați; înregistrează `convocations[{member_id, channel, sent_at, delivered?, read_at?}]`; avertizare dacă `date - azi < convocation_days`; cere ca CA să consemneze și trimiterea prin recomandată, cu dovadă încărcată;
  - `POST /meetings/{mid}/ack` (membru): confirmă primirea;
  - `POST /meetings/{mid}/attendance` (CA): `{present_member_ids[], mandates_ids[]}` → calculează `represented_shares`, `quorum_met` (prima convocare: majoritatea cotelor; a doua convocare, din ziua 7: fără cvorum, **marcat vizibil „ținută fără cvorum (art. 9(2))”**);
  - `POST /meetings/{mid}/decisions` (CA): `[{title, result_text, votes_for?, votes_against?, abstentions?}]` + `minutes_document_id` → `contest_until = date + contest_days`;
  - `GET /assoc/{id}/meetings` · `GET /meetings/{mid}`.
- **Mandate:**
  - `POST /meetings/{mid}/mandates` (membru): `{representative_member_id, document_id?}`. Reprezentantul trebuie să fie membru; limitele `proxy_limits` sunt verificate pe ședință → 409 la depășire.
  - `DELETE /mandates/{id}` (mandantul, înainte de ședință).
- **Petiții:**
  - `POST /assoc/{id}/petitions` (membru): `{kind:"extraordinary_aga"|"agenda_item", title, text, meeting_id? (la agenda_item)}`;
  - `POST /petitions/{pid}/sign` (membru, o singură dată);
  - `GET /assoc/{id}/petitions` → semnături (număr de membri, cote), prag, `threshold_met`; la atingerea pragului se notifică președintele și CA, iar termenul de răspuns e 10 zile pentru AGA extraordinară;
  - `POST /petitions/{pid}/respond` (CA).
- **Cereri de informații:**
  - `POST /assoc/{id}/requests` (membru) `{subject, text}` → `due_at = +info_request_days`;
  - `POST /requests/{rid}/answer` (CA) `{text, document_id?}`;
  - `GET /assoc/{id}/requests` (CA: toate; membru: ale lui) — întârziatele sunt marcate.

### C. Calendar, finanțe, transparență, jurnal, demo (`assoc_accountability.py`)
- **Calendar:**
  - `GET /assoc/{id}/obligations?year=` → generate din `rules` pentru anul cerut, plus starea calculată din dovezi (AGA ținută în termen = ședință AGA ordinară cu data ≤ deadline; bilanț = document `balance` cu data ≤ 31.03; raport cenzori trimestrial = document `censor_report` în trimestru);
  - `POST /obligations/{key}/evidence` (CA) pentru dovezi manuale.
- **Finanțe:**
  - `POST /assoc/{id}/finance/years` (CA/casier): `{year, revenues{category: amount}, expenses{…}, net_profit, split{council, reserve, charity, investment, members}}`, validat față de `profit_split` maxim;
  - `POST /finance/years/{y}/distribute` → calculează sumele per membru, proporțional cu cotele, cu `prescribes_at = AGA date + prescription_years`;
  - `GET /assoc/{id}/finance` (membri: sinteză + sumele mele; CA: tot) · `POST /distributions/{id}/paid` (casier).
  - Alertă (la citire și în panoul membrului) pentru sume neridicate cu mai puțin de 12 luni până la prescriere.
- **Transparență:** `GET /assoc/{id}/transparency` → scor 0–100 și componentele (obligații, documente obligatorii, cereri în termen, participare).
- **Jurnal:** `GET /assoc/{id}/audit` (cenzori/manager: complet; membri: rezumat).
- **Demo:**
  - `POST /assoc/demo/seed` (super-admin): creează „Composesoratul Demo Valea Verde” (fictiv) cu ~60 de membri fictivi, cote fracționare (1/12, 1/15…), surse „Nr X = …”, cu stări mixte (~10% activi); 3 conturi de test legate (Ion = președinte, Maria = membru confirmat, Andrei = moștenitor în curs), cenzorul Vasile; documente exemplu (fișiere text/pdf generate); o AGA din trecut ținută la a doua convocare fără cvorum; o AGA viitoare convocată; o petiție în curs; obligații întârziate; un an financiar cu sume aproape de prescriere; o cerere de informații restantă;
  - `POST /assoc/demo/reset` · totul e marcat `demo_seed: true`.

### Frontend (`frontend/src/apps/radacini/pages/composesorate/`)
- **Navigație:** „Composesorate” (lista mea + căutare publică).
- **Pagina asociației** (`/radacini/composesorate/:id`), cu file:
  - **Prezentare:** scor de transparență, patrimoniu, organe, următoarea ședință, alerte;
  - **Cota mea:** cote, surse, documentele mele, sumele cuvenite cu prescrierea, revendicări;
  - **Registru** (CA/cenzori): tabel, import CSV, panou de participare;
  - **Documente:** listă după tip, versiuni, hash vizibil, jurnal de acces pentru CA;
  - **Ședințe:** convocare cu confirmări, prezență, cvorum, hotărâri cu termen de contestare;
  - **Petiții**, **Cereri**, **Calendar**, **Finanțe**, **Jurnal**.
- **Pagini dedicate:** „Revendică / Sunt moștenitor” și un ghid scurt pentru membri vârstnici, cu texte mari și pași simpli.
- **Panou:** cardul „Composesoratele mele” (alerte: convocări neconfirmate, sume aproape de prescriere, petiții).
- **Administrare:** fila „Composesorate” (listă, creare, asignare operatori).
