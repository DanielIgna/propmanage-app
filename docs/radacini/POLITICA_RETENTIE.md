# Rădăcini — politica de retenție a datelor (ciornă pentru jurist)

Versiune 0.1 · 2026-10-26 · **Ciornă tehnică, nu consultanță juridică.** Duratele sunt propuneri. Juristul le confirmă sau le corectează (vezi `DOSAR_JURIST.md`, E.5–E.6). Coloana „Stare” arată ce face codul **acum**.

## Principii
1. Păstrăm datele **doar cât e nevoie** pentru scopul lor, plus termenul în care pot fi necesare ca probă (prescripție) sau pentru obligații legale.
2. După expirare: **ștergere** sau **anonimizare** (numele și contactul se înlocuiesc, cifrele agregate rămân pentru statistici).
3. Cererea de ștergere a contului (`POST /me/delete-request`) se procesează manual. Păstrăm doar ce e listat mai jos ca „păstrat după ștergere”, cu motivul.
4. Copiile de siguranță (backup Supabase) se rotesc automat. Ce s-a șters dispare din ele la expirarea ciclului de backup (de confirmat ciclul planului Supabase).

## Durate propuse

| Date | Unde | Durată propusă | Păstrat după ștergerea contului? | Stare |
|---|---|---|---|---|
| Profil membru (nume, localitate, interese) | `radacini_members` | cât există contul | nu | manual (cerere de ștergere) |
| Cont inactiv | toate | după **24 de luni** fără autentificare: notificare, apoi anonimizare după 30 de zile | — | **neimplementat** |
| Terenuri publicate (inclusiv locația exactă) | `radacini_parcels` | cât există contul. Terenurile arhivate: 24 de luni | nu, cu excepția celor legate de acorduri semnate (se anonimizează) | manual |
| Jurnalul de acces la locația exactă | `radacini_location_access_log` | **12 luni** | nu | **neimplementat** |
| Cereri de teren și mesaje (fără acord) | `radacini_land_requests`, `radacini_request_messages` | 24 de luni de la ultima activitate | nu | **neimplementat** |
| Acorduri semnate (termeni, hash, semnături cu IP și user-agent) | `radacini_agreements` | **3 ani de la încetare** (prescripția generală; de verificat: 5 ani dacă au relevanță fiscală) | da, ca probă (temei: interes legitim, apărarea unui drept) | manual |
| Proiecte, contribuții, recolte | `radacini_projects`, `radacini_contributions`, `radacini_harvests` | 3 ani de la închiderea proiectului | anonimizat (fără nume) | **neimplementat** |
| Anunțuri de piață expirate sau închise | `radacini_listings` | 24 de luni | nu | **neimplementat** |
| Rezervări finalizate | `radacini_reservations` | 3 ani (probă a tranzacției) | da, anonimizat parțial | **neimplementat** |
| Dispute | `radacini_disputes` | 3 ani de la închidere | da, ca probă | manual |
| Raportări de conținut (DSA) și decizii | `radacini_reports` | **2 ani** de la decizie (termenul de contestare DSA e de 6 luni, plus marjă) | da, fără datele raportorului după 2 ani | **neimplementat** |
| Consimțăminte (termeni, consimțământ parental) | `radacini_consents`, acceptări termeni | cât există contul + 3 ani (dovada consimțământului) | da | manual |
| Gospodării și minori (prenume, an naștere, relație) | `radacini_households` | până la retragerea consimțământului, ieșirea din gospodărie sau **18 ani**: atunci invităm minorul să-și facă cont propriu, altfel ștergem | nu | **neimplementat** (regula de 18 ani) |
| Fotografii | storage + `radacini_photos` | cât există obiectul (teren, anunț, proiect) | nu | parțial (la ștergerea obiectului) |
| Notificări în aplicație | `notifications` | 12 luni | nu | **neimplementat** |
| Jurnalul de audit al personalului | `admin_console.audit` (`radacini.*`) | 3 ani | da (acțiunile personalului, nu ale membrului) | manual |
| Erori neprevăzute ale sistemului (doar ruta și tipul erorii) | `radacini_errors` | **14 zile** | — | **implementat** (ștergere automată) |
| Cereri de ștergere (evidență) | `radacini_deletion_requests` | 3 ani de la procesare | da (dovada procesării) | manual |
| Exportul datelor (fișier) | descărcat de utilizator, nu se păstrează pe server | — | — | implementat |

### Composesorate (S9, doar demo acum)
| Date | Durată propusă | Observații |
|---|---|---|
| Registrul de membri și moștenitori | stabilită de **asociație** (operatorul datelor), probabil cât există asociația | Noi suntem persoană împuternicită (DPA). De confirmat în `DOSAR_JURIST.md` J.1–J.2 |
| Documente (statut, PV, bilanțuri) și amprentele lor | cât există asociația (arhivă) | Versiunile nu se șterg intenționat (transparență) |
| Jurnalul de răspundere | permanent, cât există asociația | De confirmat: cum îl împăcăm cu dreptul la ștergere (J.11) |
| Revendicări respinse și dovezile lor | 3 ani de la decizie | Dovezile (certificate) sunt date sensibile: acces doar pentru conducere și cenzori |

## Ce trebuie implementat după aviz
1. Un job zilnic `radacini_retention`, rulat pe Railway în profilul de joburi „lite”, care aplică duratele marcate „neimplementat”. Fiecare rulare scrie un rezumat în jurnalul de audit.
2. Regula de 18 ani pentru minori: notificare titularului cu 30 de zile înainte.
3. Notificarea conturilor inactive.
4. Un text scurt în politica de confidențialitate, cu tabelul de mai sus simplificat.

## Jobul de retenție (2026-10-28, neactivat)
`backend/scripts/radacini_retention.py`. Implicit **doar raport**; `--apply` șterge sau anonimizează. Nu e în scheduler: se activează doar după avizul juristului. Reguli implementate:
- jurnalul de acces la locația exactă: ștergere după 12 luni;
- cereri de teren încheiate fără acord (cu mesajele lor): ștergere după 24 de luni;
- anunțuri închise sau expirate fără rezervări: ștergere după 24 de luni (cele cu rezervări rămân, ca probă);
- raportări DSA rezolvate: după 2 ani se șterg ID-ul și numele raportorului;
- notificările Rădăcini din aplicație (link `/radacini…`) ale membrilor: ștergere după 12 luni;
- minori care au împlinit 18 ani și conturi inactive de 24 de luni: **doar raport**, mereu (notificarea prealabilă nu e implementată).

Cu `--apply`, fiecare rulare scrie un rezumat în jurnalul de audit (`radacini.retention_run`). Test: `tests/test_radacini_retention.py` (direct pe bază, fără backend).

## Întrebări pentru jurist
1. Sunt corecte cele 3 ani pentru acorduri, dispute și rezervări (prescripția generală din Codul civil)? Unde se aplică 5 sau 10 ani (fiscal, contabil)?
2. Putem păstra acordurile semnate după cererea de ștergere, invocând interesul legitim (probă)? În ce formă: integral sau pseudonimizat?
3. Pentru minori: e corectă ștergerea la 18 ani dacă nu își fac cont? Ce facem cu fotografiile în care apar?
4. Jurnalul de răspundere al composesoratului poate fi permanent?
