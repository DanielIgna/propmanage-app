# Composesorate — analiză internă inițială (Faza 0)

> Document de lucru intern. Nu e consultanță juridică. Referințele legale sunt marcate **„de verificat”** până le confirmă juristul. Analiza completă (Faza 1) se face pe documentele reale trimise de fondator, anonimizate.

## 1. Ce sunt (înțelegerea de pornire)
- **Forme asociative istorice de proprietate în comun:** pădure, pășune, uneori teren agricol. Sunt frecvente în Transilvania și au origini în secolul XIX (în jurul anilor 1890). Membrii au adus bani sau terenuri, iar suprafețele au fost comasate și administrate împreună.
- **Membrii dețin cote-părți (drepturi), nu parcele delimitate.** Veniturile, de exemplu din exploatarea lemnului sau din arendarea pășunii, se împart pe cote.
- **Istoric:** au fost desființate în perioada comunistă și reconstituite după 1990–2000 prin legile fondului funciar (Legea 1/2000, „forme asociative”; Legea 18/1991; Legea 247/2005 — **de verificat** articolele exacte). Au personalitate juridică prin înscriere la judecătorie și funcționează după un **statut**.
- **Pădurile** lor intră sub Codul silvic (Legea 46/2008 — **de verificat**): administrare sau servicii silvice prin ocol silvic, amenajament silvic, autorizații de exploatare, trasabilitatea lemnului (SUMAL). **Pășunile** au regim propriu (OUG 34/2013 — **de verificat**).
- **Organe tipice:** Adunarea Generală a membrilor, comitetul sau consiliul de conducere (președinte, membri, **secretar**), comisia de cenzori. Documente tipice: statut, tabelul nominal al membrilor cu cotele, procese-verbale, bilanț și registre contabile, contracte, extrase de carte funciară.

## 2. Problemele observate de fondator (context din experiența directă)
Fondatorul a fost secretar, este membru în administrare și membru moștenitor.
1. **Lipsă de transparență:** actele și deciziile ședințelor nu ajung la toți membrii; convocările și procesele-verbale nu sunt publicate sau ușor de consultat.
2. **Membri vârstnici, moștenitori neînscriși:** drepturile trec la moștenitori abia după deces și după succesiune. Tabelul membrilor rămâne neactualizat, iar moștenitorii nu știu ce drepturi au sau cum le revendică.
3. **Inactivitate sau faliment:** unele composesorate nu mai au activitate, altele sunt aproape de faliment.
4. **Abuzuri:** unii membri din conducere îi dezinformează pe ceilalți (decizii luate fără informarea reală a membrilor, venituri neclare, contracte dezavantajoase).
5. **Constrângeri legale** care „blochează” inițiativa: regimul silvic, al pășunilor, cvorumuri greu de întrunit, lipsa actelor de proprietate actualizate.
6. **Izolare de piață:** chiar când produc sau au ce închiria (pășune, lemn, teren), nu comunică transparent nici cu membrii, nici cu piața.

### 2.1 Observații suplimentare ale fondatorului (2026-10-14)
- **Datele membrilor nu sunt actualizate**, mai ales domiciliile noilor membri și ale moștenitorilor. Convocarea și informarea nu ajung la ei.
- **Majoritatea membrilor nu au văzut niciodată actele.** Le văd doar la ședințe.
- **Ședințele sunt rare:** o dată la 1–2 ani. După experiența fondatorului, uneori sunt organizate cu informare minimă, ca să fie prezenți cât mai puțini membri, ceea ce permite decizii în interesul unor persoane cu interese ascunse.
- **Conducere fără competențe digitale** și, în cazul observat, fără bună-voință. Aceasta poate fi influențată de alții să ia decizii dăunătoare.
- **Cazul de referință** e un composesorat **semifuncțional**, din care fac parte fondatorul. Modulul, după ce e bine documentat, va fi prezentat și **composesoratelor funcționale**, care sunt partenerii mai probabili pentru pilot.

### 2.2 Cerințe care rezultă (de rafinat în Faza 1)
1. **Cont pentru fiecare membru și moștenitor,** cu acces la datele proprii: cotă, istoric, documentele care îl privesc.
2. **Actualizarea datelor de contact de către membru,** cu validare de către secretariat și istoric. Rezolvă domiciliile neactualizate.
3. **Portal de comunicare:** anunțuri, documente publicate pentru toți membrii, cu data publicării și jurnal de consultare.
4. **Notificări automate** (email, SMS, în aplicație) la convocări, documente noi și hotărâri, cu **dovada trimiterii și a primirii**. Ședința nu mai poate fi organizată „pe furiș”.
5. **Cereri ale membrilor:** cere un act sau o informație, încarcă un document (de exemplu certificat de moștenitor), urmărește stadiul cererii. Termene de răspuns vizibile.
6. **Gestionare comună transparentă:** ordinea de zi și materialele publicate înainte de ședință, procesul-verbal publicat după, venituri și cheltuieli explicate.
7. **Simplitate pentru vârstnici și pentru o conducere fără experiență tehnică:** operatorul Rădăcini poate digitaliza documentele și face onboarding asistat.
8. **Neutralitate:** platforma servește toți membrii. Acțiunile conducerii sunt consemnate (cine a publicat, cine a modificat, când), iar nimeni nu poate șterge urmele.

## 3. Ipoteze de lucru (de validat pe documente)
| # | Ipoteză | Cum o validăm |
|---|---|---|
| H1 | Problema principală e **informația**, nu tehnologia: membrii nu au acces la documente și decizii | Procese-verbale și convocatoare, comparate cu cine a fost informat și cum |
| H2 | Registrul membrilor e neactualizat (decedați, moștenitori neînscriși, cote neclare) | Tabelul membrilor (anonimizat) + statutul (cum se transmit cotele) |
| H3 | Cvorumul AGA e greu de întrunit (vârstnici, membri plecați) | Procesele-verbale: prezență, procuri, amânări |
| H4 | Veniturile și cheltuielile nu sunt prezentate pe înțelesul membrilor | Bilanțuri, rapoarte ale cenzorilor, contracte de vânzare sau arendare |
| H5 | Există resurse nevalorificate (pășuni, teren agricol, produse) care ar putea fi oferite transparent pe piața Rădăcini | Situația suprafețelor (CF, amenajament), contracte existente |
| H6 | Statutul permite (sau nu) comunicarea, convocarea și votul la distanță | Statutul + legislația aplicabilă (juristul) |

## 4. Direcții de soluție (doar idei, înainte de documente)
- **Registrul digital al membrilor și al cotelor**, cu istoric (transmiteri succesorale, cereri de înscriere a moștenitorilor cu acte). Doar membrii își văd datele; conducerea vede registrul.
- **Arhiva de documente pentru membri:** statut, procese-verbale, hotărâri, bilanțuri, contracte, fiecare cu data publicării și jurnal de cine a deschis documentul. E dovada transparenței.
- **Convocări AGA cu dovada comunicării:** notificare, email sau SMS, plus confirmare de primire. Ordinea de zi și materialele sunt publicate înainte de ședință.
- **Vot și procuri:** în funcție de ce permite statutul și legea. Poate fi doar consultativ la început (sondaj) și oficial ulterior, numai dacă juristul confirmă.
- **Transparența veniturilor:** prezentare simplă pe surse (lemn, pășune, arendă) și pe cheltuieli, cu documentele justificative atașate.
- **Ghid pentru moștenitori:** ce acte trebuie, unde se depun, stadiul cererii.
- **Conectarea la piață:** oferte publice ale composesoratului (închiriere de pășune, arendă de teren, produse, servicii), prin modulele existente Rădăcini (terenuri, piață, prestatori), cu aprobarea conducerii consemnată.
- **Rolul operatorului Rădăcini:** onboarding asistat pentru vârstnici, digitalizarea documentelor pe hârtie, mediere.

## 5. Riscuri de luat în calcul
- **Date personale sensibile:** CNP, adrese, succesiuni, decese. Accesul trebuie restrâns, cu jurnal de acces. Documentele se trimit **anonimizate** pentru analiză.
- **Conflicte între membri și conducere:** platforma trebuie să fie neutră, cu reguli clare de cine vede și ce face.
- **Validitate juridică:** convocarea, votul și publicarea electronică sunt valabile doar dacă statutul și legea o permit. Până la confirmare, funcțiile digitale sunt complementare, nu înlocuiesc procedura oficială.
- **Conflict de interese:** fondatorul e și membru în conducere și moștenitor. Proiectarea trebuie să protejeze **toți** membrii, nu o anumită conducere.
- **Pădurea:** exploatarea și vânzarea lemnului sunt strict reglementate. Platforma doar informează și nu intermediază vânzări de masă lemnoasă fără analiză juridică.

## 6. Documentele de care am nevoie (pentru Faza 1)
**Important:** anonimizează înainte de trimitere. Șterge sau acoperă CNP-uri, serii de buletin, adrese exacte, telefoane, semnături și datele bancare. Numele membrilor pot fi înlocuite cu inițiale sau coduri (M1, M2…).

**Esențiale**
1. **Statutul** composesoratului (versiunea în vigoare și modificările).
2. **Actul de constituire sau reconstituire** și hotărârea judecătorească de înscriere (personalitate juridică).
3. **Tabelul nominal al membrilor cu cotele** (anonimizat), plus orice evidență a transmiterilor succesorale sau cereri de înscriere a moștenitorilor.
4. **Procese-verbale ale AGA și ale comitetului** din ultimii 3–5 ani, plus convocatoarele (cum s-a făcut convocarea, cine a fost prezent, procuri, cvorum).
5. **Bilanțuri, rapoarte ale cenzorilor, situații de venituri și cheltuieli** din ultimii 3–5 ani.

**Utile**
6. **Contractele:** ocol silvic (administrare sau servicii), arendă sau închiriere de pășune sau teren, vânzare de masă lemnoasă, alte prestări.
7. **Situația suprafețelor:** extrase CF, amenajament silvic (rezumat), hărți.
8. **Exemple de probleme**, anonimizate: sesizări, contestații, corespondență, litigii, cereri ale moștenitorilor rămase fără răspuns.
9. **Cum circulă azi informația:** avizier, telefon, poștă, adunări. Ce funcționează și ce nu.
10. Dacă ai acces la **2–3 composesorate diferite** (unul activ, unul inactiv, unul cu probleme), documentele de bază de la fiecare ajută la găsirea tiparelor comune.

**Format:** PDF, poze sau scanări sunt în regulă. Se pun într-un folder local, de exemplu `docs/radacini/composesorate/surse/`. Acest folder **nu se pune în git**, pentru că poate conține date personale. Îl adaug în `.gitignore` când îl creezi.

## 7. Ce urmează după ce primesc documentele
1. **Analiză pe documente:** tipare de guvernanță, puncte de blocaj, unde se pierde transparența, cum se transmit drepturile.
2. **Harta actorilor și a fluxurilor:** membru, moștenitor, conducere, cenzori, ocol silvic, judecătorie, OCPI, piață.
3. **Cadrul legal,** sub formă de întrebări pentru jurist (completăm `DOSAR_JURIST.md`).
4. **Propunerea de modul:** funcții pe faze, MVP, ce se poate face legal digital, cum se leagă de piața Rădăcini.
5. **Aprobarea ta**, apoi implementarea.
