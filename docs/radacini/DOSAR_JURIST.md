# Rădăcini — dosar pentru jurist (pilot Cluj)

Versiune 1.0 · 2026-10-14 · Branch `radacini` · Ciornă pentru discuție cu un jurist.

> **Atenție: acest document NU este consultanță juridică.** E o listă de întrebări și o descriere exactă a comportamentului actual al produsului, redactată de echipa tehnică. Referințele la legi sunt marcate **„de verificat”** acolo unde nu suntem siguri; juristul le confirmă sau le corectează. Nimic de aici nu trebuie publicat ca text legal.

## 0. Context

**Ce este Rădăcini.** Un modul din aplicația PropManage (D1) care pune în legătură, în județul Cluj, proprietari de teren, cultivatori și consumatori: terenuri publicate, cereri, acorduri, proiecte agricole, contribuții, recolte, piață locală (vânzare, rezervare, schimb), comunități, gospodării (inclusiv minori), dispute.

**Ce face platforma.** Afișează informații, consemnează înțelegeri între utilizatori (acord cu semnătură electronică simplă), ține evidența contribuțiilor și a recoltei, notifică, moderează, medierează intern disputele.

**Ce NU face platforma (decizii D3, D19, D20).**
- Nu procesează plăți, nu ține bani, nu are escrow. Plata se face la ridicare, direct între părți, în afara platformei.
- Nu are monedă internă, puncte transferabile sau sold de schimb. Contribuțiile sunt o evidență, nu bani sau drepturi (D16).
- Nu vinde ea produse și nu este parte în contractele dintre utilizatori. Se vrea **intermediar de informații**.
- Nu percepe comision sau abonament în pilot.
- Nu oferă investiții colective, vânzare de teren sau proiecte comune cu aport financiar (blocate, vezi secțiunea F).

**Unde sunt datele.** Colecții `radacini_*` în baza comună Supabase (D4). Sursa de adevăr pentru deciziile de produs: `docs/radacini/DECISION_REGISTER.md`; riscuri: `docs/radacini/audit-agro-faza0.md` secțiunea 8.

**Cum citiți secțiunile.** Fiecare are: *Comportament actual* (ce face codul acum, cu fișierul), *Întrebări pentru jurist*, *Recomandare de text / acțiune* acolo unde e cazul.

---

## A. Arendă / închiriere / cultivare la parte

### Comportament actual
- Proprietarul publică un teren; după verificare (`draft → pending_verification → published`, D11) cultivatorii trimit cereri. Modele cerute în `backend/routes/radacini/constants.py` (`OFFER_MODELS`): `rent` (arendă/închiriere), `harvest_share` (cultivare la parte din recoltă), `fixed_fee` (sumă fixă), `mixed`.
- La acceptarea cererii se creează un **acord** (`agreements.py`, `requests.py`), versionat. Câmpurile principale: părți, teren, model, durată, preț/procent, termeni.
- **Nota legală fixă**, afișată pe fiecare acord (`LEGAL_NOTICE` în `constants.py`): „Acest acord consemnează înțelegerea dintre părți în platforma Rădăcini. Nu înlocuiește contractul de arendă/închiriere în forma cerută de lege și nici înregistrarea acestuia la primărie, unde este cazul.”
- **Semnarea**: la „propose” se calculează `terms_hash` (SHA-256 peste termenii canonici + versiune, `compute_terms_hash`); la semnare se verifică că termenii sunt exact cei trimiși. Fiecare semnătură stochează data, **IP** (`_client_ip`, din `x-forwarded-for`) și **user-agent**; IP-ul și UA nu sunt vizibile celeilalte părți (`_PRIVATE_EVIDENCE`). Orice modificare readuce acordul în ciornă și invalidează hash-ul (D12, D13).
- Acord semnat de ambele părți → se creează automat proiectul agricol (D15). La recoltă, pentru `harvest_share`, proprietarul primește automat procentul din acord (D18).
- Blocat în impersonare de admin: semnarea și modificarea acordului (D22).

### Întrebări pentru jurist
1. Contractele de **arendă** (Legea 16/1994, Codul civil — de verificat) cer formă scrisă și înregistrare la consiliul local? Se aplică și pentru loturi mici, grădini, folosință sezonieră?
2. Care este calificarea corectă pentru „cultivare la parte din recoltă” și „sumă fixă”: arendă, locațiune, asociere în participațiune, contract inominat? Depinde de calificare forma cerută?
3. Ce valoare juridică are acordul din platformă (semnătură electronică simplă cu IP, user-agent, dată, hash)? E un **început de probă**, o convenție valabilă pentru durate scurte, sau doar o consemnare? (de verificat: Legea 455/2001 privind semnătura electronică / Regulamentul eIDAS 910/2014.)
4. Poate platforma ghida utilizatorul către contractul-tip și înregistrare fără a presta „consultanță juridică”?
5. Cine răspunde dacă proprietarul nu este de fapt proprietar sau are coproprietari/uzufructuar? Verificăm doar declarativ (poate și staff-ul, la verificarea terenului). Ce verificare minimă ne cere legea sau prudența (extras CF, număr cadastral)?
6. Terenuri agricole extravilane: există **drept de preemțiune** sau alte restricții la arendare către persoane fizice (Legea 17/2014 vizează vânzarea; de verificat dacă are relevanță aici)?
7. Subarendarea: acordul permite cultivatorului să aducă alți membri (contribuții, zile de lucru în comun). E subarendă, mandat sau simplă colaborare?

### Recomandare de text (de validat)
- Păstrăm `LEGAL_NOTICE`, dar cerem jurist să-l întărească: „Acordul din platformă este o consemnare a înțelegerii. Pentru arendare/închiriere, părțile încheie separat contractul în forma cerută de lege și îl înregistrează la consiliul local, unde este cazul. Platforma nu este parte în acord și nu răspunde de executarea lui.”
- Opțional: generare de **model de contract de arendă** (șablon) pe care juristul îl validează, cu câmpurile preluate din acord. Există deja `backend/routes/legal_templates.py` (PropManage), de verificat dacă se poate refolosi.

---

## B. Vânzarea de produse agroalimentare între persoane fizice

### Comportament actual
- Orice membru poate publica un anunț în piață (`market.py`, D19): produs, cantitate, unitate, preț (RON/unitate), modalitate (`sale`, `exchange`, `both`), locul și detaliile de ridicare, perioada de valabilitate (`available_until`; anunțurile expirate dispar din piață).
- **Preț de referință** = mediana prețurilor active (minim 2) — doar informativ (`median_price`, `reference_prices`).
- **Rezervarea** nu e plată: cumpărătorul rezervă, vânzătorul confirmă, **plata se face la ridicare, direct între părți** (D20). Ratingul vânzătorilor există.
- Anunțurile pot proveni din recolta unui proiect (alocare pe recoltă confirmată, `harvests.py`).
- Platforma **nu cere** în prezent dovada că vânzătorul are statut de producător, atestat sau înregistrare sanitar-veterinară. Nu are limite de cantitate sau valoare.
- Moderarea: personalul poate închide un anunț cu motiv (D35).

### Întrebări pentru jurist
1. Un particular care vinde legume/fructe din grădina proprie într-un cadru organizat (aplicație) are nevoie de: înregistrare DSV (de verificat: ordinul/lege aplicabilă pentru „vânzare directă” a produselor primare), **atestat de producător / carnet de comercializare** (de verificat: Legea 145/2014 privind comercializarea produselor din sectorul agricol, atestatul de producător, carnetul de comercializare — de verificat starea actuală), alte autorizații?
2. Există praguri de cantitate/valoare sub care activitatea e considerată ocazională/nu necesită PFA sau atestat? (de verificat)
3. Ce categorii trebuie excluse din piață (carne, lactate, ouă, produse procesate, conserve, miere, produse alcoolice)? Propunem în pilot **doar produse vegetale primare nepreparate**; juristul confirmă.
4. Ce obligații de **informare a consumatorului** are vânzătorul (denumire, origine, preț/unitate) și poate platforma impune câmpuri obligatorii în anunț?
5. Răspunderea pentru siguranța alimentelor și daunele: vânzătorul, platforma, ambii? Ce disclaimer minim cerem?
6. Fiscalitate pentru vânzător (venituri din activități agricole, impozit pe venit, TVA, declarații) — platforma are obligații de raportare (de verificat: DAC7 — Directiva (UE) 2021/514 privind raportarea de către operatorii de platforme digitale; Legea de transpunere în România — **de verificat** dacă pragurile ne vizează, deși nu procesăm plăți).
7. Poate platforma pune în anunț o **bifă** „Declar că dețin autorizațiile necesare” și un câmp opțional pentru număr atestat?

### Recomandare / acțiune
- Până la aviz: restrângem piața la produse vegetale primare, adăugăm declarația de conformitate în termeni și la publicare, afișăm mesajul „Platforma nu verifică autorizațiile vânzătorilor”.

---

## C. Schimb / barter

### Comportament actual
- Anunțurile cu `exchange` sau `both` conțin text liber `exchange_for` (3–300 caractere); rezervarea are `exchange_offer` (3–300) (`market.py`).
- **Nu există monedă internă, sold sau echivalent calculat automat între produse.** Un „echivalent de schimb” afișat, dacă va fi afișat, este **doar informativ** (pe baza prețului de referință) și nu leagă părțile.
- Nu se înregistrează valori monetare pentru schimb.

### Întrebări pentru jurist
1. Schimbul de bunuri între persoane fizice (troc) este tratat fiscal ca vânzare reciprocă? Ce trebuie declarat și de cine (de verificat: Codul fiscal, venituri din alte surse / activități agricole)? Există prag sau scutire pentru schimburi ocazionale de valoare mică?
2. Dacă platforma afișează un „echivalent informativ” în RON, creează asta o obligație sau o evaluare cu efecte fiscale? Trebuie un disclaimer? Propunere: „Valoare orientativă, fără efect juridic sau fiscal”.
3. Se aplică aceleași reguli de siguranță alimentară ca la vânzare (secțiunea B)?
4. Schimbul de **servicii/muncă** (ex. ore de lucru pe teren contra recoltă) poate fi privit ca raport de muncă? Contribuțiile sunt o evidență (D16), dar alocarea recoltei pe contribuții poate fi percepută ca remunerare. Cum evităm calificarea de contract de muncă / activitate nedeclarată (de verificat: zilieri — Legea 52/2011)?

---

## D. Rolul platformei, comerț electronic, DSA, moderare

### Comportament actual
- Platforma este **intermediar de informații**: nu e parte în tranzacții, nu primește bani, nu stochează marfă.
- **Moderare**: staff propriu Rădăcini (`radacini_staff`, D7) verifică terenurile înainte de publicare, închide anunțuri cu motiv de 3–300 caractere (D35), preia dispute. Acțiunile personalului se scriu în jurnalul de audit (D27).
- Rate limit pe rutele publice (D28). Fotografiile încărcate sunt reprocesate (JPEG, max 1600 px, fără EXIF; max 5 MB, max 6 per obiect — `photos.py`).
- Raportarea conținutului de către utilizatori: **nu există încă** un flux dedicat „raportează anunț” (doar disputele și închiderea de către staff). De confirmat dacă e necesar.

### Întrebări pentru jurist
1. Statut: **furnizor de servicii ale societății informaționale** (Legea 365/2002 privind comerțul electronic — de verificat) sau „platformă online” în sensul **Regulamentului (UE) 2022/2065 (DSA)**? Ce obligații se aplică unei platforme mici în pilot (puncte de contact, mecanism de notificare și acțiune, motivarea restricțiilor)? Există scutiri pentru microîntreprinderi (de verificat art. 19 DSA).
2. Condiții pentru **răspunderea limitată** a găzduitorului (art. 6 DSA / art. 14–15 Legea 365/2002 — de verificat): cât de activă poate fi moderarea (verificare teren, preț de referință, mediere) fără a pierde statutul de intermediar neutru?
3. Ca facilitator între consumator și vânzător neprofesionist: se aplică protecția consumatorilor (OUG 34/2014, Legea 363/2007 — de verificat)? Trebuie să informăm explicit că vânzătorul este un particular și consumatorul nu beneficiază de drepturile față de un comerciant?
4. Informații obligatorii despre operator (identitate, adresă, contact) pe site; **termeni și condiții** conforme; ANPC/SOL (platforma europeană de soluționare online a litigiilor — de verificat dacă mai e relevantă).
5. Operatorul platformei: persoană juridică? Cine semnează termenii (PropManage / o entitate nouă)? Răspunderea fondatorului.
6. Trebuie asigurare de răspundere civilă pentru platformă?

---

## E. GDPR

### Comportament actual
- **Locația terenurilor**: publică doar aproximativ (coordonate rotunjite la 2 zecimale, D5). Locația exactă o văd: proprietarul, personalul și, **după un acord semnat**, părțile acordului (D6). Fiecare citire a locației exacte de către altcineva decât proprietarul se scrie în `radacini_location_access_log` (`parcels.py`, `_log_location_access`). Lista din administrare arată doar coordonate rotunjite (D37).
- **Minori** (`households.py`): gospodăria are un titular și membri. Un minor nu are cont (nu are e-mail); se stochează doar **prenumele (1–40 caractere)**, relația, **anul nașterii**. La adăugare este obligatoriu `parental_consent=true`; se înregistrează în `radacini_consents` (`kind: minor_data`, versiune consimțământ, dată, IP, user-agent). Dacă înregistrarea consimțământului eșuează, minorul nu e adăugat.
- **Vârsta**: pragul de **16 ani** pentru consimțământul propriu în România (Legea 190/2018, art. 8 din GDPR — de verificat) nu este aplicat tehnic; produsul consideră minor orice membru fără e-mail. De clarificat: ce se întâmplă între 14 și 18 ani, când un tânăr poate avea cont propriu.
- **Consimțăminte Rădăcini**: termeni și politică de confidențialitate proprii, versionate, cu acceptare și istoric (planificat S8, versiunea `2026-10-pilot`; acceptare cu IP, user-agent, dată).
- **Drepturile persoanei vizate**: `GET /me/export` (`gdpr.py`) exportă datele utilizatorului din colecțiile Rădăcini, inclusiv accesările locației proprii; `POST /me/delete-request` creează o **cerere de ștergere cu procesare manuală** (D26, D36): personalul o marchează `done`/`rejected` cu motiv. **Nu se șterg automat** acorduri semnate sau rezervări în curs.
- **Retenție**: nu există încă o politică formală pe durate (acorduri, jurnal acces, contribuții, dispute, consimțăminte). De definit.
- **Fotografii**: EXIF eliminat la încărcare (`photos.py`); pozele pot arăta persoane (inclusiv minori) sau terenuri.
- Jurnalul de audit al personalului: `admin_console.audit` cu prefixul `radacini.` (D27).

### Întrebări pentru jurist
1. Temeiurile prelucrării per categorie: contract (acord), interes legitim (moderare, securitate), consimțământ (notificări marketing, minori). Cine e **operatorul** (vezi D.5) și există asociați/persoane împuternicite (Supabase, Railway, Cloudflare, furnizor de e-mail)? Transferuri în afara SEE (de verificat: regiunea proiectului Supabase, DPA-uri, clauze contractuale standard).
2. **Localizarea exactă** a terenului: dată personală (proprietar identificabil)? Este corect modelul „aproximativ public / exact după acord / jurnal de acces”? Cât timp păstrăm jurnalul de acces?
3. **Minori**: consimțământul titularului de gospodărie e valid ca „consimțământ parental”? Cum verificăm calitatea de părinte/tutore (declarativ vs. dovadă)? Prenume + an naștere sunt suficiente, minime? Ce facem la majorat sau la vârsta de 16 ani (cont propriu, retragerea consimțământului)? Sunt permise fotografii ale minorilor?
4. **DPIA** (art. 35 GDPR): este necesară (date ale minorilor, localizare, prelucrare la scară mică)? Există listă ANSPDCP de operațiuni care cer DPIA (de verificat). Este necesar un **responsabil cu protecția datelor (DPO)**?
5. **Retenție**: perioade recomandate pentru acorduri semnate (prescripție — Codul civil), jurnal de acces, dispute, contabilitate, cereri de ștergere, conturi inactive.
6. **Ștergere**: ce păstrăm legitim după cererea de ștergere (acorduri, dispute, obligații fiscale)? Se pot pseudonimiza datele în loc să fie șterse?
7. **Informare** (art. 13): textul politicii Rădăcini trebuie revizuit; e nevoie de ROPA (registrul activităților de prelucrare) actualizat — PropManage are `routes/gdpr.py` cu ROPA/DPIA/DSAR generale; Rădăcini adaugă prelucrări noi (locație, minori) — de completat intrările.
8. Notificarea încălcărilor de securitate (72 h): procedură existentă? Cine o conduce?
9. **Comunități și gospodării**: vizibilitatea numelor între membri (prenume doar, `_first_name`). E suficient?
10. Cookie-uri / PWA: banner conform (ePrivacy — de verificat).

---

## F. Investiții colective, proiect comun, vânzare de teren

### De ce sunt blocate
- Modelele `sale` și `joint_project` pot fi **afișate** în oferta unui teren, dar cererile pe ele sunt respinse cu 409 și mesajul „Acest model necesită aviz juridic și nu e încă disponibil în platformă.” (`LEGAL_GATE_MESSAGE`, `REQUESTABLE_MODEL_IDS` în `constants.py`; D25).
- Nu există mecanism de colectare de fonduri, cote de participare, dividende sau investiții. Contribuțiile și alocările de recoltă sunt evidențe, nu instrumente financiare (D16, D18).
- Investițiile colective au fost explicit amânate (`audit-agro-faza0.md`: „Amânare”; ASF, crowdfunding, fiscal).

### Întrebări pentru jurist
1. Ce trebuie să **nu** facă platforma ca să rămână în afara reglementărilor privind piața de capital și crowdfunding (ASF; Regulamentul (UE) 2020/1503 privind furnizorii europeni de servicii de finanțare participativă — de verificat; Legea 24/2017 — de verificat)? Cum sunt tratate cota din recoltă și finanțarea proiectului de către mai mulți membri?
2. Un „proiect comun” (mai mulți membri cultivă împreună, împart cheltuieli și recoltă) poate fi asociere simplă / societate civilă / asociere în participațiune? Ce document minim e necesar?
3. **Vânzarea de teren** prin platformă: doar publicitate (anunț) fără mediere? Preempțiune, notar, restricții pentru terenuri agricole extravilane (Legea 17/2014 — de verificat). Rămâne blocat?
4. Condițiile pentru deblocare ulterioară și textele cerute.

---

## G. Dispute și mediere

### Comportament actual
- Buton „Deschide o dispută” pe contribuții, rezervări, recolte și acorduri (`disputes.py`, S6). Poate deschide doar o parte a obiectului.
- Personalul (operator pe arie sau manager) **preia** disputa și o **închide cu o rezoluție motivată**; părțile sunt notificate. Acțiunile sunt auditate.
- Rezoluția **nu este obligatorie** juridic și nu execută nimic automat (nu se mută bani; nu există bani în platformă). Nu modifică un acord semnat decât prin acțiunile obișnuite ale părților.
- Rezoluția internă nu impune limite de timp; nu există termen de răspuns.

### Întrebări pentru jurist
1. Cum se formulează în termeni că **medierea internă** nu e „mediere” în sensul **Legii 192/2006** (de verificat: mediator autorizat) și nu înlocuiește instanța sau medierea legală? Putem folosi cuvântul „mediere” în UI sau „soluționare amiabilă / facilitare”?
2. Riscul ca staff-ul să fie privit ca mediator sau ca arbitru (clauze de arbitraj — de verificat Codul de procedură civilă). Ce spunem despre confidențialitate și conflict de interese?
3. Răspunderea platformei pentru rezoluții greșite; limitare prin termeni.
4. Competența teritorială/legea aplicabilă; clauza de soluționare a litigiilor în termeni.
5. Păstrarea probelor (acord, hash, IP, istoric dispută) și furnizarea lor la cerere oficială.

---

## H. Termenii pilot (versiunea `2026-10-pilot`) — ce trebuie revizuit

### Stare
Conform PLAN.md S8: termenii și politica Rădăcini sunt documente **separate de cele PropManage**, redactate de echipa tehnică ca ciornă („Versiune pilot — în revizuire juridică”), cu acceptare obligatorie pentru acțiunile cu efect (publicare teren, cerere, semnare, anunț, rezervare, înscriere), cu istoric (versiune, IP, user-agent, dată). Textul se află în colecția `radacini_legal_documents` (implementare în S8).

### Puncte de revizuit (listă)
1. **Părțile și operatorul**: identificare, contact, rol („intermediar de informații”).
2. **Fără plăți / fără garanții**: „fără producție sau cantitate garantată”, plata la ridicare.
3. **Acordurile**: valoarea lor, nota că nu înlocuiesc contractul de arendă și înregistrarea.
4. **Vânzare și schimb**: produse permise, declarații ale vânzătorului, responsabilitate, fiscalitate la schimb.
5. **Conținut al utilizatorilor**: licență, interdicții, fotografii, moderare, suspendare.
6. **Minori**: reguli, consimțământ parental, vârsta minimă a unui cont propriu.
7. **Date de localizare**: tratarea aproximativă/exactă, jurnal de acces.
8. **Dispute și mediere**: caracter facilitator, nu obligatoriu.
9. **Limitarea răspunderii** și despăgubiri; legea aplicabilă; instanța competentă.
10. **Modificarea termenilor**: cum se notifică versiunile noi (reaccept obligatoriu).
11. **Politica de confidențialitate**: temeiuri, retenție, destinatari, transferuri, drepturi, contact DPO/operator.
12. **Încetare și ștergere cont**: ce se păstrează.
13. Termenii **PropManage** existenți (LegalGate) vs. cei Rădăcini: suprapuneri sau contradicții.

---

## I. Livrabile cerute juristului
- Răspunsuri scurte la întrebările de mai sus, cu prioritate: A (arendă/înregistrare), B (DSV/atestat), E (minori, DPIA), D (statut platformă), F (rămân blocate?).
- Termeni și politică revizuite (versiune finală).
- Lista de modificări de produs obligatorii înainte de pilot (câmpuri, bife, texte).
- Estimare de onorariu și timp (vezi `COSTURI_PILOT.md`).

## Anexă — hartă rapidă produs → fișier
| Subiect | Fișier |
|---|---|
| Modele de ofertă, poarta juridică, `LEGAL_NOTICE` | `backend/routes/radacini/constants.py` |
| Acorduri, hash, semnătură (IP/UA) | `backend/routes/radacini/agreements.py`, `requests.py` |
| Piață, preț de referință, schimb | `backend/routes/radacini/market.py` |
| Recolte și alocări | `backend/routes/radacini/harvests.py` |
| Gospodării, minori, consimțământ parental | `backend/routes/radacini/households.py` |
| Dispute | `backend/routes/radacini/disputes.py` |
| Fotografii | `backend/routes/radacini/photos.py` |
| Export, ștergere | `backend/routes/radacini/gdpr.py` |
| Jurnal acces locație | `backend/routes/radacini/parcels.py` (`_log_location_access`) |
| Decizii | `docs/radacini/DECISION_REGISTER.md` |
