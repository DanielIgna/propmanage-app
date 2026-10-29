# Rădăcini — plan de lucru autonom (27.10.2026 18:00 → 30.10.2026 20:00)

Rulat de task-ul programat `radacini-autonom`, din 2 în 2 ore. Fiecare rulare citește fișierul acesta, ia **primul punct nebifat**, îl face, îl testează, îl bifează (cu data și commit-ul) și trece la următorul, până se termină creditul. Rularea următoare continuă de unde a rămas.

## Reguli (obligatorii la fiecare rulare)
- Branch-ul `radacini`. Se fac **commit și push doar pe `radacini`**. Interzis: merge în `main`, deploy, modificări pe Railway sau Cloudflare, migrații SQL, setări Supabase.
- Nu atinge `project-x` și nu opri procesul de pe portul 3000. Serverele pornesc din `.claude/launch.json` (`backend`, `dev`; dev-ul își alege singur alt port).
- Baza de date e comună cu producția (egress Supabase peste cotă): teste țintite. **Suita completă cel mult o dată pe zi.** După teste: `./venv/bin/python -m scripts.radacini_purge_demo --tests-only --apply`. Composesoratul demo „Valea Verde” și scenariul demo rămân.
- Testele: `cd backend && REACT_APP_BACKEND_URL=http://localhost:8001 ./venv/bin/python -m pytest tests/<fișier> --noconftest -q`. Backend-ul nu are reload: după modificări pe backend, repornește-l.
- Încarcă skill-ul `propmanage` la început. Răspunsurile și documentele sunt în română. Fără date personale reale în repo.
- Dacă un punct cere o decizie a fondatorului, notează întrebarea în „Întrebări pentru fondator” și treci mai departe.
- Lacăt: dacă `.claude/autonom.lock` e mai nou de 3 ore, oprește-te (rulează altă sesiune). Altfel scrie în el ora curentă și șterge-l la final.

## Puncte
- [ ] (parțial 29.10: interogările verificate, două optimizări făcute; blocat: măsurarea cu `radacini_load_test` cere backend, pornirea refuzată) **A1. Performanță `/radacini/projects`:** mai puține interogări pe cerere (fără N+1, `$in` pe loturi). Apoi `/listings` și `/admin/system`. Măsoară înainte și după cu `scripts.radacini_load_test --levels 5 --per-user 3` și notează rezultatele în `TEST_INCARCARE.md`.
- [x] **A2. Job de retenție:** `scripts/radacini_retention.py`, implicit **doar raport** (`--apply` pentru ștergere), după `POLITICA_RETENTIE.md`. Include regula de 18 ani pentru minori (doar raport) și conturile inactive. Teste pe date `TEST-RAD-`. Nu se înregistrează în scheduler.
- [x] (testat fără backend, cu jurnal și notificări simulate) **A3. Notificare la accesul locației exacte** (DPIA R1): proprietarul e anunțat când altcineva vede locația exactă, cel mult o dată pe zi pentru aceeași persoană și același teren. Plus test.
- [x] (verificat prin build; verificarea în browser a rămas nefăcută, serverul dev a fost refuzat) **A4. Plăci de hartă configurabile:** `NEXT_PUBLIC_RADACINI_TILE_URL` și `NEXT_PUBLIC_RADACINI_TILE_ATTRIBUTION`, implicit OSM. Notă în `DPIA_CIORNA.md`.
- [ ] (blocat: serverul dev nu a putut fi pornit; 29.10 seara: verificare statică făcută, un tabel reparat) **A5. Verificare pe mobil (375 px)** a tuturor paginilor Rădăcini în browser: fără scroll orizontal, butoane de cel puțin 44 px, dialoguri care încap pe ecran. Repară ce găsești.
- [x] (fără verificare în browser: serverul dev a fost refuzat; verificat prin build) **A6. Accesibilitate:** etichete pe câmpuri, `aria-label` pe butoanele doar cu icon, focus vizibil, contrast. Doar în `frontend/src/apps/radacini`.
- [x] **A7. Build de producție frontend:** `cd frontend && NEXT_DIST_DIR=.next-build npx next build`. Repară erorile sau avertismentele Rădăcini și șterge apoi `.next-build`.
- [x] **A8. Review al codului** din commit-urile `54fd357..HEAD` (corectitudine și securitate: lista albă, raportări, monitorizare, pagina operator). Repară problemele confirmate.
- [x] (testul HTTP scris, se sare fără backend; verificat pe funcții și prin build) **A9. Composesorate, vizibilitatea scorului:** regulă per asociație, scor „public” sau „doar membri” (implicit public), cu test (vezi DPIA R6).
- [x] **A10. Ghid pentru beta:** `docs/radacini/GHID_BETA.md` cu:
  - ce testează invitații și cum raportează probleme;
  - textul emailului de invitație;
  - pașii fondatorului pe Railway: `RADACINI_ENABLED`, `RADACINI_ALLOWED_EMAILS`, `RADACINI_OPERATOR_*`, `RESEND_API_KEY`, opțional `PG_POOL_MAX` și portul 6543.
  
  Apoi actualizezi `ROADMAP.md` și `PLAN.md`.
- [ ] (blocat: cere backend pornit) **A11. Regresie completă** (o singură dată): repari ce pică, apoi faci curățarea.
- [x] (29.10; se actualizează dacă rulările următoare deblochează A1, A5, A11) **A12. Final:** rezumat în secțiunea „Jurnal” de mai jos și actualizarea memoriei `radacini-state.md`.

## Întrebări pentru fondator
- (completat de rulări)
- Rularea programată nu a putut porni serverele (`backend`, `dev`): pornirea a fost refuzată. Pentru A1, A3, A5, A9, A11 trebuie permisă pornirea lor din `.claude/launch.json` (sau un backend lăsat pornit pe 8001).
- Beta închis: cu `RADACINI_ALLOWED_EMAILS` setat, și paginile publice (`/public/listings`, `/public/communities`) cer cont din listă. E dorit așa sau le lăsăm deschise vizitatorilor?
- Retenția: activăm jobul (`--apply` + scheduler) doar după avizul juristului pe durate?

## Jurnal
- 2026-10-26: plan creat; punctele 1–5 de beta au fost făcute în `54fd357` și `f4ff6a1`.
- 2026-10-28: A2 (job de retenție, doar raport implicit; raport pe datele reale: 0 de expirat), A4 (plăci configurabile), A7 (build de producție fără erori), A10 (`GHID_BETA.md`). A1, A3 blocate: backend-ul nu a putut fi pornit. Commit `d684eec`.
- 2026-10-28: A6 (`Field` leagă automat eticheta de câmp sau marchează grupul cu `role="group"`: 28 de câmpuri reparate; contrast pe Login; butoanele-icon și focusul erau deja în regulă). A8 (review `54fd357..HEAD`): jurnalul de erori salva mesajul brut al excepției (putea conține emailuri, ID-uri, valori) → acum se curăță (`scrub_error_message`, test nou). Restul (lista albă, raportări, monitorizare, operator) fără probleme confirmate. Build de producție curat. Commit `13c1665`. A9, A11 blocate (backend); A12 rămâne pentru ultima rulare.
- 2026-10-28 13:10: rulare fără progres pe cod. Pornirea `backend` a fost refuzată din nou și nu rula nimic pe 8001. A1, A3, A5, A9, A11 rămân blocate (cer servere pornite). A12 rămâne pentru ultima rulare.
- 2026-10-29: A9 (regula `score_visibility` în regulile asociației, implicit „public”; cu „members” scorul dispare din lista publică, din detaliu pentru străini, iar `/transparency` dă 403; UI afișează „Scor vizibil doar membrilor”). Test nou `test_radacini_score_visibility.py`: 3 teste pe funcții verzi, testul HTTP sărit (backend-ul refuzat din nou). Build de producție curat. A1 neatins: `/projects` folosește deja `$in` pe loturi, iar măsurarea cere backend.
- 2026-10-29: A3 (la prima citire din zi a locației exacte de către cultivator sau personal, proprietarul primește notificare cu rolul, fără identitate; nicio notificare dacă jurnalul nu se scrie). Test nou `test_radacini_location_notify.py` (6 teste, fără backend). DPIA R1 actualizat.
- 2026-10-29 13:50: A1 parțial, fără backend (pornirea `backend` și `dev` refuzată din nou). Revizuire: `/projects`, `/listings` și `/admin/system` nu au N+1 (`$in` pe loturi, agregate pe 100 de vânzători). Optimizări: `/projects` filtrează activitățile viitoare în SQL (nu mai încarcă activitățile trecute; verificat pe baza reală: același rezultat ca filtrul Python), `/admin/system` citește jurnalul de erori cu proiecție explicită. Măsurătorile din `TEST_INCARCARE.md` rămân de făcut. A5, A11 blocate (servere). A12: rezumat de mai jos și memoria actualizată.
- 2026-10-29 22:00: pornirea `backend` și `dev` refuzată din nou; nimic pe 8001 (3010 e alt proiect). A5 static: căutare de lățimi fixe peste 375 px și tabele fără derulare în `apps/radacini`; singura problemă găsită, tabelul „Patrimoniu” din `OverviewTab.jsx` (5 coloane), e acum în container `overflow-x-auto`. Restul tabelelor erau deja încadrate. A1 (măsurare), A5 (în browser), A11 rămân blocate.
- **Rezumat final (A12):** făcute A2, A3, A4, A6, A7, A8, A9, A10, A12; A1 parțial. Rămân A1 (măsurare), A5 (mobil 375 px în browser), A11 (regresie completă): toate cer serverele `backend`/`dev`, a căror pornire e refuzată în rulările programate. Commit-uri: `d684eec`, `13c1665`, `7d988bc`, `7f195c1`, `5449195`, `8894fca` și cel al acestei rulări.
