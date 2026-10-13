# Rădăcini — plan de implementare

Baze: [audit-agro-faza0.md](audit-agro-faza0.md), [audit-admin-roluri.md](audit-admin-roluri.md).
Decizii luate (2026-10-13): modul în aceeași aplicație; aceleași conturi; MVP fără plăți; terenuri în colecții noi; locația exactă e publică doar aproximativ; operator/manager = personal Rădăcini (`radacini_staff`), nu `role=operator` global; date dev în baza comună, doar în `app.radacini_*`, marcate `is_demo` local.

| Sprint | Conținut | Stare |
|---|---|---|
| S1 | Fundație + Membri + Terenuri + Personal (operator/manager) + coadă de verificare | gata local (60 teste API, flux verificat în browser), necommis |
| S2 | Cereri de teren + negociere + acorduri cu versiune | — |
| S3 | Proiect agricol: membri, plan culturi, activități, contribuții | — |
| S4 | Recoltă + alocare + piață locală (listări, rezervări, schimb) | — |
| S5 | Admin: comutator Produs, secțiune Rădăcini, KPI, noduri Knowledge Center | — |

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
| GET | `/parcels` | public (fără autentificare) | doar `published`, nearhivate; filtre `locality`, `model`; `limit` ≤ 50, `skip`; **coordonate rotunjite la 2 zecimale**, fără `owner_user_id`, cu `owner_name` = prenumele |
| GET | `/parcels/{id}` | public dacă e `published` (varianta aproximativă); proprietarul, personalul sau super-adminul văd tot | 404 altfel |
| PATCH | `/parcels/{id}` | proprietarul, doar în `draft`/`rejected`/`paused` | aceleași validări; un teren `rejected` editat revine la `draft` |
| POST | `/parcels/{id}/submit` | proprietarul, din `draft`/`rejected` | → `pending_verification`; emite `radacini.parcel_submitted` |
| POST | `/parcels/{id}/pause` · `/resume` | proprietarul | `published` → `paused` · `paused` → `published` |
| DELETE | `/parcels/{id}` | proprietarul | setează `archived_at`; 409 dacă e `pending_verification` |

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
