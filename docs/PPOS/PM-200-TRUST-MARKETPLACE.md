# PM-200 — TRUST MARKETPLACE · Design Canonic
Status: APPROVED DESIGN v1.0 · 27 Iun 2026 · Owner: Product Council
Relație: extinde PM-100 (Ecosystem Engine). Implementarea rămâne sub BETA WAR ROOM — acest document e specificația, datele beta dau ordinea.
**Poziționare (Fondator, verbatim)**: *„Nu vrem să devenim cel mai mare marketplace de servicii pentru locuințe. Vrem să devenim cea mai de încredere rețea de proprietari și profesioniști din România."*

---

## 1. REPOZIȚIONAREA MARKETPLACE-ULUI
Conceptul rămâne. Se schimbă promisiunea:
- Vechi: „Specialiști verificați" (verificarea = act administrativ al platformei).
- **Nou: „Marketplace-ul profesioniștilor recomandați de proprietari."** (recomandarea = act de încredere al unui om real care a plătit o lucrare reală).
Diferența strategică: verificarea o dăm noi o singură dată; recomandarea o dau proprietarii în fiecare zi. A doua nu poate fi copiată de competiție.

### Trust Layer pe profilul specialistului (ordinea afișării = ordinea importanței)
1. **❤️ Rebook Score** — „97% ar angaja din nou" (KPI-ul suprem, deasupra stelelor)
2. **Recomandat de N proprietari** (recomandări distincte, doar owneri verificați)
3. Rating mediu ⭐ + număr recenzii (toate Verified Experience)
4. Lucrări finalizate (escrow eliberat)
5. Status verificare (identitate + certificări)
6. Timp mediu de răspuns · Rată de finalizare
7. Portofoliu (generat din lucrări reale, cu acordul ownerilor)
8. Vechime în ecosistem + badge-uri câștigate
Onestitate: sub 3 lucrări → „Nou pe platformă" + data verificării; NICIODATĂ procente pe eșantioane nesemnificative (Rebook se afișează de la ≥5 răspunsuri).

---

## 2. SISTEMUL DE RECENZII EXTINS (4 întrebări, 30 secunde)
La fiecare lucrare finalizată (escrow eliberat), ownerului i se cere O SINGURĂ DATĂ:
1. **Nota lucrării** (1–5 ⭐)
2. **Recenzie text** (opțională, cu foto)
3. **„Ai angaja din nou acest specialist?"** → DA / NU / NU SUNT SIGUR
4. **„L-ai recomanda altui proprietar?"** → DA / NU
Toate 4 alimentează Reputation Score. Întrebările 3–4 sunt binare intenționat: nu se pot „umfla", nu suferă de inflația stelelor (media 4.9 peste tot = zero informație; 78% rebook = informație brutală și utilă).

### REBOOK SCORE (KPI-ul definitoriu)
- Întrebare: *„Dacă ai avea nevoie de același serviciu, ai angaja din nou acest specialist?"* DA / NU / NU SUNT SIGUR.
- Calcul: `Rebook % = DA / (DA + NU + NU SUNT SIGUR)` — „nu sunt sigur" NU e ignorat (e semnal).
- Afișare: **„❤️ 97% ar angaja din nou"** + explicația la tap: *„Procentul proprietarilor care, după o lucrare reală finalizată și plătită, au spus că l-ar angaja din nou."*
- Ierarhie: Rebook > stele în ranking, în cardul de profil și în comparatorul de oferte.

---

## 3. TRUST OPERATING SYSTEM — 7 DIMENSIUNI (câștigat / menținut / pierdut)

| Dimensiune | Se câștigă prin | Se menține prin | Se pierde prin |
|---|---|---|---|
| **Owner Trust** | proprietate înregistrată, identitate verificată, prima lucrare plătită, documente verificate, twin existent, vechime activă | plăți la timp, comunicare civilizată, recenzii oneste | dispute abuzive, anulări repetate, recenzii-șantaj (detectate la mediere) |
| **Specialist Trust** | verificare KYC+certificări, lucrări finalizate, rebook, recomandări, răspuns rapid, garanții onorate | activitate constantă, punctualitate, calitate repetată | anulări, dispute pierdute, garanții refuzate, inactivitate (decay lent) |
| **Property Trust** | documente verificate, audit, twin complet, istoric mentenanță neîntrerupt | mentenanță la zi, evenimente înregistrate | găuri de istoric, documente expirate |
| **Document Trust** | sursă verificabilă (emitent, dată), validare admin/AI, corelare cu evenimente | valabilitate în termen | expirare, inconsistență cu istoricul |
| **Marketplace Trust** | tranzacții escrow finalizate, dispute puține, Verified Experience % ridicat | lichiditate sănătoasă (oferte/cerere), response time mic | fraudă detectată, spam de ofertare |
| **Digital Twin Trust** | date introduse din lucrări reale (nu declarative), foto, rapoarte de inspecție | actualizare la fiecare eveniment | date declarative vechi necontrazise/neconfirmate |
| **Community Trust** | recomandări între owneri, mentori activi, campanii de cartier reușite | reciprocitate constantă | abuz de invitații (anti-spam) |
**Legea comună**: fiecare dimensiune se acumulează în timp, nu se cumpără, nu se transferă, și DECADE lent în absența acțiunilor reale. Fiecare feature nou trebuie să declare ce dimensiune mișcă (regula NVA din PM-100 + regula Trust din PM-200).

---

## 4. REPUTATION SCORE — formula transparentă (0–100, publică, explicată punct cu punct)
| Componentă | Pondere | Cum se calculează (pe scurt, afișat userului) |
|---|---|---|
| ❤️ Rebook Score | **22%** | % DA din „ai angaja din nou?" (min. 5 răspunsuri) |
| Recenzii Verified Experience | 18% | media notelor DOAR din lucrări escrow confirmate bilateral |
| Recomandări owneri verificați | 14% | nr. proprietari distincți care l-ar recomanda, ponderat cu vechimea ownerului |
| Clienți repetați | 10% | % owneri care au revenit la el |
| Lucrări finalizate + vechime | 10% | volum cu randament descrescător (log) — vechii nu devin de neatins |
| Calitate răspuns | 8% | timp mediu răspuns + rata ofertelor personalizate (nu template) |
| Punctualitate | 6% | respectarea termenelor confirmată la finalizare |
| Garanții onorate | 6% | intervenții în garanție rezolvate/total solicitate |
| Verificare + portofoliu | 6% | KYC, certificări valabile, portofoliu din lucrări reale |
| Rată dispute | **penalizator −0…−15** | dispute pierdute/total lucrări |
**Reguli anti-black-box**: formula e publicată în profil („De ce e acest scor?"); orice schimbare de ponderi se anunță public cu 30 zile înainte; specialistul își vede exact componentele și ce să îmbunătățească. **Anti-popularitate-de-moment**: componentele pe termen lung (rebook, repetați, garanții, vechime) = 54% din scor.

---

## 5. VERIFIED EXPERIENCE (badge-ul care ucide recenziile anonime)
O recenzie primește ✅ **Experiență Verificată** DOAR dacă toate 4 sunt adevărate:
1. cererea de lucrare a existat în platformă; 2. ownerul e verificat; 3. specialistul a finalizat lucrarea; 4. AMBII au confirmat finalizarea (escrow eliberat).
Afișare: recenziile Verified Experience apar primele, cu badge; cele fără (importate/istorice) apar separat, marcate onest. În marketing: „aici nu există recenzii anonime — fiecare recenzie e o lucrare plătită și confirmată de ambele părți."

## 6. VERIFICAREA OWNERILOR (cine are voie să influențeze trust-ul)
Niveluri (cumulative, cu badge-uri):
- **L1 Cont confirmat** (email+telefon) → poate cere oferte; NU influențează trust.
- **L2 Proprietar înregistrat** (proprietate cu adresă) → recenziile lui contează cu pondere 0.6.
- **L3 Proprietar verificat** (identitate SAU document de proprietate verificat) → pondere 1.0 + badge „Proprietar verificat".
- **L4 Proprietar activ** (≥1 lucrare escrow finalizată) → pondere 1.2; recomandările lui apar ca „de la un proprietar cu lucrări reale".
- **L5 Proprietar veteran** (≥12 luni activitate + ≥3 lucrări + twin existent) → pondere 1.5 + eligibil Community Mentor.
**Anti-fraudă recomandări**: cont nou (<30 zile) = pondere 0 până la L2; graful detectează cluster-uri (N conturi noi care recomandă același specialist → carantină + verificare); recomandarea cere lucrare plătită SAU declarație explicită „l-am angajat personal" cu răspundere (limitată la 1/categorie/an fără escrow); schimbul de recomandări între specialiști (A recomandă B, B recomandă A, fără lucrări încrucișate reale) = semnal de fraudă.

## 7. TRUST BADGES (toate câștigate, niciodată cumpărate)
| Badge | Criteriu exact (public) |
|---|---|
| 🏅 Recomandat de Proprietari | ≥10 recomandări de la owneri L3+ distincți |
| ❤️ Would Hire Again 95%+ | Rebook ≥95% pe ≥20 răspunsuri |
| 🔨 100 Lucrări Finalizate | 100 escrow eliberate (trepte: 10/25/50/100/250) |
| ✅ Profesionist Verificat | KYC + certificări valabile |
| ⚡ Răspuns Rapid | mediană răspuns <2h pe ultimele 90 zile |
| 🏠 Digital Twin Contributor | ≥25 lucrări cu foto/date care au actualizat twin-uri |
| 🎓 Community Mentor | L5/AUTHORITY care a ghidat ≥5 specialiști noi cu rezultate |
| 🤝 Partener pe Termen Lung | ≥3 contracte mentenanță active ≥1 an |
Reguli: criteriile publice; badge-ul se PIERDE când criteriul nu mai e îndeplinit (nu e trofeu, e stare); zero badge-uri decorative.

## 8. REȚEAUA DE RECOMANDĂRI (graful de încredere)
Noduri: Owner · Specialist · Proprietate · Lucrare. Muchii: a angajat · a recomandat · a lucrat la · a actualizat twin.
- **Anul 1**: graful e rar — folosit doar pentru Verified Experience și anti-fraudă (cluster detection).
- **Anii 2–3**: „specialiști recomandați de proprietari ca tine" (agregat: aceeași zonă + tip proprietate + tip lucrare) — NICIODATĂ „vecinul X l-a angajat" (privat).
- **Anii 3–5**: trust propagat cu atenuare: recomandarea unui owner L5 cu istoric impecabil cântărește mai mult; lanțurile scurte (owner→specialist→owner comun) cresc încrederea afișată agregat.
- **Confidențialitate constituțională**: se expun DOAR agregate („recomandat de 14 proprietari verificați din Cluj"), niciodată identități fără consimțământ explicit per-recomandare.

## 9. „SPECIALIȘTII MEI DE ÎNCREDERE" (pagina relației pe termen lung)
Fiecare owner își construiește reteaua personală, legată de proprietate:
- Auto-populată din lucrări finalizate (cu opțiune de eliminare); organizată pe categorii (electrician, instalator, HVAC, zugrav, arhitect, designer, curățenie, securitate, grădinar).
- Acțiuni per specialist: **Cheamă din nou** (cerere pre-completată direct către el) · **Programează mentenanța** (propune contract) · **Recomandă-l** (către alt owner sau public pe profil) · **Partajează cu familia** (soț/soție/copii văd aceeași rețea a casei).
- La transfer de proprietate: noul owner poate primi rețeaua casei (cu acordul specialiștilor) — casa vine cu oamenii ei de încredere.
- Efect ecosistem: transformă tranzacția în relație; alimentează direct buclele 51–52 din PM-100 (rebooking + contracte mentenanță).

## 10. PROPERTY HEALTH SCORE (profilul de calitate al casei — consolidare)
Un singur scor 0–100 (deja existent ca „Sănătatea casei"), acum cu componente publice pentru owner: documente (25) + mentenanță la zi (25) + audit/twin completeness (20) + îmbunătățiri energetice (15) + lucrări cu specialiști verificați (15). Fiecare acțiune finalizată arată explicit „+X puncte"; scorul decade DOAR când apar restanțe reale (mentenanță depășită, documente expirate) — niciodată artificial. Scorul apare pe pașaport → devine monedă la vânzare/închiriere/asigurare.

## 11. COMMUNITY CHALLENGES (contribuție, nu gamification goală)
Provocări legate EXCLUSIV de acțiuni cu valoare reală: completează profilul casei · încarcă documentele esențiale · creează twin-ul · completează istoricul de mentenanță · recomandă UN specialist cu care ai lucrat efectiv.
Recompense cu valoare reală: reducere la twin premium/audit profesional · luni de membership premium · funcții exclusive (rapoarte avansate) · recunoaștere în comunitate (badge Mentor).
Interdicții: fără streak-uri, fără puncte fără acoperire, fără provocări de tip „invită 10 prieteni" (spamul e respins constituțional — invitațiile apar doar ca opțiune în momente de satisfacție reală, vezi §12).

## 12. GROWTH ENGINE ORGANIC — 50 DE BUCLE DE ACHIZIȚIE (zero spam, zero ads dependency)
Format: moment real → invitație naturală → valoare pentru AMBELE părți.
**Familie & prieteni (1–10)**: 1. Raport anual al casei → share familiei → conturi din încredere personală. 2. Partajarea rețelei „specialiștii mei" cu familia → membrii devin useri. 3. Lucrare reușită + foto → owner trimite prietenului cu aceeași problemă cererea pre-completată. 4. Părinte configurează casa copilului la mutare → cont nou cu istoric din prima zi. 5. Moștenire/donație imobil → transfer istoric → noul owner devine user. 6. Soț/soție co-administrator → al doilea cont activ pe aceeași casă. 7. Prieten cere „știi un instalator bun?" → owner trimite profilul cu Rebook Score → vizitator→cont. 8. Nuntă/mutare în casă nouă → checklist „casa nouă" partajabil → cuplu nou pe platformă. 9. Owner veteran devine Mentor → onboarding-ul făcut de om, nu de reclamă. 10. Cadou: „abonament carte digitală a casei" pentru părinți → seniori aduși de copii.
**Vecini & cartier (11–20)**: 11. Pachet de zonă (3 fațade pe aceeași stradă) → vecinii fără cont invitați la preț mai bun. 12. Problemă comună de bloc (coloană, acoperiș) → cerere colectivă → toți semnatarii devin useri. 13. Campanie locală de mentenanță (revizii de toamnă în cartier) → înscriere cu cont. 14. „Specialiști recomandați în cartierul tău" (agregat) → pagină publică locală → SEO → conturi. 15. Eveniment de cartier (întâlnire HOA) → demo pașaport → administratori interesați (post-beta B2B). 16. Vecinul vede lucrarea în desfășurare (banner discret „lucrare gestionată prin PropManage" — DOAR cu acordul ownerului) → scanează QR. 17. Grup de cumpărături comune (centrale, panouri) → discount de grup → membri noi. 18. Harta anonimizată „case digitalizate în zona ta" → efect de normă socială reală, fără identități. 19. Proiect comun (gard, alee comună) → co-finanțare prin escrow → ambii vecini useri. 20. Alertă de zonă reală (grindină) → ghid verificare acoperiș → cereri + conturi noi.
**Tranzacții imobiliare (21–30)**: 21. Pașaport partajat cumpărătorului → cont la achiziție. 22. Chiriaș cu acces limitat → viitor owner-user. 23. Agent imobiliar folosește pașaportul la listare → vânzătorii următori cer același dosar. 24. Anunț de vânzare cu badge „istoric complet PropManage" → cumpărătorii întreabă ce e → organic. 25. Notar primește dosarul digital → recomandă instituțional. 26. Bancă/evaluator cere istoricul la creditare → owner îl generează → instituția îl cere și altora. 27. Asigurător primește dosarul la subscriere → primă mai bună → asigurătorul devine canal. 28. Firmă de mutări partajează checklist „casa nouă" → clienții ei devin useri. 29. Dezvoltator predă apartamente noi cu profil PropManage pre-populat → sute de owneri dintr-o predare. 30. Evaluare post-cumpărare (audit de achiziție) → primul serviciu plătit al noului owner.
**Specialiști ca ambasadori (31–40)**: 31. Specialistul își pune profilul cu Rebook Score în ofertele offline → clienții lui devin owneri. 32. QR pe factura/ștampila specialistului → „vezi recenziile mele verificate". 33. Specialistul cere recenzie clientului din afara platformei → clientul intră să o lase → cont owner. 34. Echipe organice (electrician+instalator) → fiecare își aduce clientela. 35. Specialist mută portofoliul istoric pe platformă → clienții vechi invitați să confirme lucrările → conturi. 36. Garanția lucrării se activează în platformă → clientul offline trebuie să-și facă cont → owner nou cu istoric început. 37. Specialistul recomandă coleg pentru nișa adiacentă → colegul se înscrie pe cereri reale. 38. Cursuri/certificări listate → școlile profesionale trimit absolvenți verificabili. 39. Specialist AUTHORITY dă interviu/ghid public → autoritate → cereri directe. 40. Furnizorii de materiale văd volumul → parteneriate → clienții lor B2C invitați.
**Conținut & instituțional (41–50)**: 41. „Scorul Casei" public → raport → cont (deja live). 42. Ghiduri SEO practice (verificarea centralei, umiditate) → calculator → cont. 43. Studiu anual „Starea caselor din România" (date agregate) → presă → val de conturi. 44. Recenziile Verified Experience indexabile → SEO local pe nișă+oraș. 45. Template gratuit „dosarul casei" descărcabil → jumătate din valoare → contul o completează. 46. Parteneriat primării/ANL pe educație de mentenanță → legitimitate → conturi. 47. Webinar sezonier („pregătește casa de iarnă") → checklist în cont. 48. API pașaport pentru portaluri imobiliare → badge „istoric verificat" pe anunțuri → trafic calificat. 49. Program universitar (facultăți de instalații) → generația nouă intră direct în ecosistem. 50. Fiecare email tranzacțional (ofertă, escrow, garanție) trimis unui non-user (ex. co-proprietar) → valoare imediată + cont opțional — NICIODATĂ newsletter nesolicitat.
**Bucle RESPINSE**: invitații în masă din agenda telefonului · recompense pentru invitații fără valoare (spam plătit) · dark patterns („prietenul tău te-a provocat") · cumpărare de recenzii/recomandări · orice buclă în care partea invitată nu primește valoare imediată.

## 13. NEIGHBOURHOOD ECOSYSTEMS (orașe, apoi cartiere)
Faza 1 (post-beta): pagini agregate per oraș — specialiști recomandați local + cereri deschise anonimizate. Faza 2: campanii locale de mentenanță sezonieră + pachete de zonă. Faza 3: proiecte comune cu escrow multi-parte (HOA light) + evenimente. Principiu: densitatea bate acoperirea — un cartier care duduie valorează mai mult decât 10 orașe moarte; expansiunea urmează harta cererii (PM-100 §5).

## 14. GAP ANALYSIS & SECVENȚIERE POST-BETA
**Există deja**: recenzii escrow-only (=fundamentul Verified Experience) · verificare KYC specialiști · pașaport+QR · Sănătatea casei · timeline · capabilities matching · „Nou pe platformă" onest.
**De construit (ordinea prin NVA + date beta)**:
- **Val 1 (imediat post-beta)**: întrebările 3–4 la recenzie (rebook+recommend — schimbare mică, valoare enormă; de colectat DIN PRIMA ZI ca să existe istoric) · afișare Rebook pe profil (de la ≥5 răspunsuri) · pagina „Specialiștii mei" (rebooking).
- **Val 2**: Reputation Score transparent complet + badge-uri (primele 4) · niveluri verificare owneri L1–L5 · Verified Experience badge public.
- **Val 3**: graful de recomandări + anti-fraudă cluster · challenges · neighbourhood faza 1.
**Notă de onestitate**: Rebook Score cere volum — în beta se COLECTEAZĂ, nu se afișează. Primele profiluri arată „Nou pe platformă" + verificare, exact ca acum. Trust-ul nu se grăbește; asta e chiar teza documentului.
