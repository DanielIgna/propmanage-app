# Rădăcini — registrul deciziilor

Versiune 1.0 · Branch `radacini` · Actualizat: 2026-10-14. Surse: [PLAN.md](PLAN.md), [audit-agro-faza0.md](audit-agro-faza0.md), [audit-admin-roluri.md](audit-admin-roluri.md).

**Cine a decis**
- **Fondator** = decizie consemnată în PLAN.md ca „decizii luate” sau cerută explicit de fondator.
- **Echipa tehnică** = decizie de proiectare luată la scrierea contractelor sprinturilor și la reverificări, în limitele deciziilor fondatorului. Rămâne deschisă la corectare de către fondator.
- **În așteptare** = nu e decisă; apare ca „deschis” în secțiunea de la final.

Regula de întreținere: o decizie nouă primește un rând nou (fără rescrierea istoricului); o decizie schimbată se marchează „înlocuită de D<nr>”.

## Decizii de bază (2026-10-13)

| Nr | Data | Decizie | Motiv | Cine |
|---|---|---|---|---|
| D1 | 2026-10-13 | Rădăcini este un modul în aceeași aplicație PropManage, nu o aplicație separată. | Reutilizăm autentificarea, notificările, evenimentele și infrastructura existentă; evităm duplicatele. | Fondator |
| D2 | 2026-10-13 | Aceleași conturi PropManage (rol `client` + profil Rădăcini), fără rol global nou. | Un singur login, fără migrarea utilizatorilor. | Fondator |
| D3 | 2026-10-13 | MVP fără plăți și fără abonament încasat. Plata se face la ridicare, în afara platformei, sau prin schimb. | Plățile, TVA-ul și taxele cer analiză juridică și fiscală separată. | Fondator |
| D4 | 2026-10-13 | Terenurile stau în colecții noi `radacini_*`, nu în `properties`. | Nu modificăm datele sau schema PropManage. | Fondator |
| D5 | 2026-10-13 | Locația exactă a terenului e publică doar aproximativ (coordonate rotunjite la 2 zecimale). | Protecția proprietarilor. | Fondator |
| D6 | 2026-10-13 | Locația exactă o văd proprietarul, personalul și, după un acord semnat, părțile acordului, cu jurnal de acces. | Acces minim necesar, cu urmă de audit. | Fondator (principiul), echipa tehnică (jurnalul de acces, rundele 1–2) |
| D7 | 2026-10-13 | Operatorul și managerul Rădăcini sunt personal propriu (`radacini_staff`), nu `role=operator` global. Super-adminul PropManage e tratat ca manager. | Rolurile globale dau acces la tot PropManage; zonele operatorului se aplică doar în Rădăcini. | Fondator |
| D8 | 2026-10-13 | Datele de dezvoltare stau în baza comună, doar în `app.radacini_*`, marcate `is_demo` când `RADACINI_MARK_DEMO=true` (doar local). Curățare cu `backend/scripts/radacini_purge_demo.py`. | Un singur mediu de bază de date; separare clară a datelor de test. | Fondator |
| D9 | 2026-10-13 | Proiectele agricole sunt noi (`radacini_projects`), fără modificarea `projects` din PropManage. | Domeniu diferit; nu atingem modulul existent. | Echipa tehnică |
| D10 | 2026-10-13 | Gamification, comunități, gospodării și copii se amână după pilot (S6–S7). | Cer politică pentru minori, GDPR și validare juridică; separare între evidența contribuțiilor și puncte. | Echipa tehnică |

## Decizii de produs din contractele S1–S4 (2026-10-13)

| Nr | Data | Decizie | Motiv | Cine |
|---|---|---|---|---|
| D11 | 2026-10-13 | Un teren trece prin verificare (`draft → pending_verification → published \| rejected`); un teren publicat și editat revine la verificare. | Calitatea ofertelor; ce vede publicul a fost verificat. | Echipa tehnică |
| D12 | 2026-10-13 | Tranzițiile de stare sunt atomice (actualizare condiționată, 409 la conflict). | Evită dubla acceptare, dubla semnare și supravânzarea. | Echipa tehnică |
| D13 | 2026-10-13 | Acordul este o consemnare versionată, nu un contract: nota legală fixă îl declară insuficient pentru arendă sau înregistrare la primărie. | Nu înlocuim forma cerută de lege. | Echipa tehnică |
| D14 | 2026-10-13 | O cerere activă fără activitate 30 de zile devine `expired`, calculat la citire (fără cron). | Egress mic; fără joburi periodice. | Echipa tehnică |
| D15 | 2026-10-13 | Proiectul agricol se creează automat când acordul e semnat; cultivatorul e coordonator, proprietarul e `owner`. | Un flux continuu: acord, proiect, activități. | Echipa tehnică |
| D16 | 2026-10-13 | Contribuțiile sunt o evidență append-only, nu bani, puncte sau drepturi; confirmarea o face alt coordonator decât autorul. | Separarea evidenței de drepturile contractuale (principiul 10 din master prompt). | Echipa tehnică |
| D17 | 2026-10-13 | Rotația culturilor doar avertizează (după familia culturii), nu blochează. | Decizia rămâne la cultivator. | Echipa tehnică |
| D18 | 2026-10-13 | Recolta o înregistrează un coordonator și o confirmă proprietarul; alocările se fac doar pe recolte confirmate. La `harvest_share`, proprietarul primește automat procentul din acord. | Împărțirea recoltei urmează acordul semnat. | Echipa tehnică |
| D19 | 2026-10-13 | Piața: orice membru poate publica; preț de referință = mediana prețurilor active (cel puțin 2). Fără monedă internă și fără sold de schimb; schimbul e text liber. | Prețuri transparente, fără valoare transferabilă (cerută de master prompt). | Echipa tehnică |
| D20 | 2026-10-13 | Plata se face la ridicare, direct între părți; platforma nu procesează plăți. | Aliniat cu D3. | Fondator (D3), echipa tehnică (text în interfață) |

## Reverificare și runda de remedieri (2026-10-13 / 2026-10-14)

| Nr | Data | Decizie | Motiv | Cine |
|---|---|---|---|---|
| D21 | 2026-10-13 | Intrare proprie în Rădăcini (`/radacini/login`, titlu „Rădăcini”, `noindex`), fără widget-urile PropManage. | Identitate separată pentru pilot. | Echipa tehnică |
| D22 | 2026-10-13 | În modul impersonare sunt blocate acțiunile cu efect juridic (semnare, modificare acord, evaluare contribuții, cerere de ștergere, moderare). | Un admin nu acționează juridic în numele unui utilizator. | Echipa tehnică |
| D23 | 2026-10-13 | Conturi de test (persone) și comutare de cont, doar local; datele demo și de test nu apar public decât în modul demo. | Demonstrații și teste fără risc pentru date reale. | Echipa tehnică |
| D24 | 2026-10-14 | `RADACINI_ENABLED` și `NEXT_PUBLIC_RADACINI_ENABLED` sunt oprite implicit; se pornesc explicit (local, prin `launch.json`). | Un merge în `main` nu expune modulul. | Echipa tehnică |
| D25 | 2026-10-14 | Poarta juridică: cererile pe modelele `sale` și `joint_project` sunt dezactivate („necesită aviz juridic”); `mixed` permite preț și procent. | Vânzarea și proiectele comune cer analiză juridică (ASF, asociere, coproprietate). | Echipa tehnică, pe baza D3 |
| D26 | 2026-10-14 | GDPR: export al datelor (`/me/export`) și cerere de ștergere cu procesare manuală; nu se șterg automat acorduri semnate sau rezervări în curs. | Obligații de păstrare; ștergerea cere verificare umană. | Echipa tehnică |
| D27 | 2026-10-14 | Acțiunile personalului (verificare, personal, moderare, GDPR) se scriu în jurnalul de audit PropManage (`admin_console.audit`) cu prefixul `radacini.`. | Urmă de audit fără jurnal nou. | Echipa tehnică |
| D28 | 2026-10-14 | Rate limit pe rutele publice `/api/radacini/parcels*` și `/meta` (60/min fără cont, 600/min cu credențiale). | Protecție împotriva extragerii de date. | Echipa tehnică |
| D29 | 2026-10-14 | Notificările Rădăcini au subiect „Rădăcini: …”, link absolut și wrapper propriu; `services.notify` rămâne neschimbat. | Identitate proprie, fără modificarea codului comun. | Echipa tehnică |
| D30 | 2026-10-14 | Migrația `supabase/migrations/*_radacini_collections.sql` (colecții și indexuri) **se aplică pe bază doar cu aprobare**. | Schimbarea bazei comune cere aprobare explicită (principiul 4 din master prompt). | Fondator (regula), echipa tehnică (scriptul) |

## S5 — administrare (2026-10-14)

| Nr | Data | Decizie | Motiv | Cine |
|---|---|---|---|---|
| D31 | 2026-10-14 | Administrarea stă în aplicația Rădăcini (`/radacini/admin/*`), doar pentru managerul Rădăcini (inclusiv super-adminul). | Adminul PropManage are 113 intrări și nu aplică permisiuni pe zone. | Echipa tehnică (înlocuiește propunerea A1/A2 din audit-admin-roluri.md) |
| D32 | 2026-10-14 | În adminul PropManage se adaugă o singură intrare, „Rădăcini”, care deschide `/radacini/admin`. | Modificare minimă în codul comun. | Echipa tehnică |
| D33 | 2026-10-14 | Fluxul de activitate se citește din `activity_events` (tipuri `radacini.*`), fără modificarea panourilor PropManage. | Reutilizăm `event_bus`; fără sursă nouă. | Echipa tehnică |
| D34 | 2026-10-14 | KPI-urile se calculează la cerere, cu numărări exacte și un cache în memorie de 5 minute. | Egress mic în Supabase. | Echipa tehnică |
| D35 | 2026-10-14 | Moderarea anunțurilor: închidere cu motiv (3–300 caractere), notificarea vânzătorului, audit. Motivul nu se salvează pe anunț, pentru că îl pot citi și cumpărătorii cu rezervare. | Datele de moderare ajung doar la cine trebuie. | Echipa tehnică |
| D36 | 2026-10-14 | Cererile de ștergere se rezolvă manual în pilot; în administrare se marchează `done` sau `rejected` (respingerea cere motiv) și utilizatorul e notificat. | Ștergerea efectivă cere verificarea obligațiilor legale. | Echipa tehnică, pe baza D26 |
| D37 | 2026-10-14 | Lista de terenuri din administrare arată coordonate rotunjite; locația exactă se citește doar prin detaliul terenului, care o jurnalizează. | Aliniat cu D5 și D6; o listă nu generează zeci de intrări de jurnal. | Echipa tehnică |
| D38 | 2026-10-14 | Knowledge Center: noduri `radacini:*` în `enterprise_registry.json` și acest registru. KC rămâne doar al fondatorului. | Harta arhitecturii arată legăturile reale. | Echipa tehnică |

## Deschis (neluat)

| Subiect | Ce lipsește | Cine decide |
|---|---|---|
| Consultanță juridică (arendă, vânzare de alimente, barter, GDPR minori) | Aviz înainte de deblocarea modelelor `sale` și `joint_project` și înainte de S6 | Fondator |
| Aplicarea migrației de colecții pe baza comună | Aprobare explicită (D30) | Fondator |
| Aplicarea zonelor admin pe server pentru personal extern (A7) | Aprobare separată; atinge codul PropManage | Fondator |
| Mod asistat al operatorului (publică în numele proprietarului) | Decizie de produs | Fondator |
| Specialiști PropManage pentru lucrări agricole (Capability Engine) | S7 | Fondator |
| Abonament, facturare familie, taxe Stripe pe sume mici | După pilot | Fondator |
| Costuri în euro (Maps, email, Stripe, juridic) | De completat înainte de pilot | Fondator |
