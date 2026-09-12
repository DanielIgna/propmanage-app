# SPEC P3a — IGIENĂ & ONESTITATE · Specificație completă de implementare
Status: **PRODUCTION-READY · AȘTEAPTĂ APROBAREA FONDATORULUI** · Owner: Product Council · Zero cod până la GO.

## Executive Summary
8 modificări chirurgicale, exclusiv presentation layer, care elimină minciunile și zgomotul din interfață: primul ecran devine liber (fără tur auto/overlay-uri), specialistul vede UN progres adevărat, marketplace-ul public nu mai afișează contra-dovezi de încredere, jargonul de sistem dispare. Niciun API, model de date sau permisiune modificată. Feature-flag & rollback pe fiecare schimbare vizibilă.

**Garanții CTO**: fără endpoint-uri noi · fără migrații · componentele se modifică/ascund, nu se șterg din cod la această fază · testare completă (testing agent frontend + capturi 1920/390) înainte de finish.

---

## Explorarea alternativelor (regula celor 3 soluții)

| Criteriu | A — Conservatoare | B — Echilibrată ✅ | C — Radicală |
|---|---|---|---|
| Descriere | doar ascundere CSS/conditional a elementelor problematice | stare derivată din date + prezentare defensivă + dicționar de traducere (această specificație) | ștergerea componentelor (tur, quests, checklist) + motor de progres nou pe backend |
| Simplitate | 6 (rămân stări moarte) | 9 | 9 |
| Venit | 5 | 8 | 8 |
| Încredere | 5 (minciuna revine la edge-case-uri) | 9 | 9 |
| Productivitate | 6 | 8 | 8 |
| Cost dezvoltare | mic | mic-mediu | mare (backend!) |
| Scalabilitate | 4 | 8 | 9 |
| Mobil | 7 | 9 | 9 |
| Desktop | 6 | 8 | 8 |
| Verdict | respinsă: nu rezolvă cauza (starea) | **RECOMANDATĂ** | respinsă: încalcă regula „doar presentation layer" a P3a; părți din ea devin P3c |

## Council Review (PPOS-020)
1. **Steve Jobs ar elimina**: turul auto complet („dacă produsul are nevoie de tur ca să fie înțeles, problema e produsul") și lista de unelte blocate. → adoptat (M1, M4d).
2. **Jony Ive ar simplifica**: un singur element plutitor, liniște vizuală la primul ecran. → adoptat (M2, M3).
3. **Dieter Rams ar elimina**: orice element care nu susține o decizie azi: quest-uri irelevante, „Ghid de pornire" la conturi mature. → adoptat (M4).
4. **Jakob Nielsen ar îmbunătăți**: euristica #1 (vizibilitatea stării reale) — checklist-urile care mint sunt defect de gradul 0; + match between system & real world (jargonul M6). → adoptat.
5. **Don Norman ar reproiecta**: maparea stării contului → interfață (interfața ca oglindă a realității, nu a istoriei livrărilor). → esența M4.
6. **Marty Cagan ar contesta**: „aveți dovezi că turul aduce activare?" Nu avem date (analytics nu măsoară tour completion). Decizie: on-demand + măsurăm din Passport/Beta Analytics existente. → adoptat, fără a construi analytics noi acum.
7. **Stripe ar optimiza**: încrederea publică — zero stări interne pe suprafețe publice (M5), CTA de plată unic (M8).
8. **Linear ar optimiza**: viteza percepută — mai puține elemente la primul paint; skeleton-urile existente rămân.
9. **Notion ar optimiza**: ierarhia empty-state-urilor și tonul uman al istoricului (M6, M7).
10. **Recomandarea finală a Consiliului**: **GO UNANIM pe Soluția B**, cu condiția testării de regresie pe fluxurile de login/legal gate și pe recompensele quest (care rămân intacte în backend).

Approval Status: Consiliu ✅ UNANIM · **Fondator: PENDING**.

---

## MODIFICĂRILE (M1–M8)

### M1 · Turul ghidat devine on-demand
- **Pagini afectate**: `/client`, `/specialist` (primul login). **Componente**: `pages/RoleTour.jsx`, montarea lui în `App.js`; header-ele dashboardurilor.
- **De ce există azi**: onboarding educațional adăugat când platforma avea puține ghidaje in-context.
- **De ce se schimbă**: blochează 100% din primul ecran (S1); descrie funcții pe care Juniorul nu le poate folosi; dublează acum hero-ul Next Action care ghidează deja.
- **Comportament nou**: turul NU se autodeclanșează niciodată. În header apare butonul „?" (Ajutor) — deschide același RoleTour existent. La primul login, „?" primește un tooltip discret, nemodal („Ghidul e aici oricând"), care dispare la primul click oriunde. Flag-ul localStorage existent se păstrează.
- **Acceptance criteria**: cont nou → zero modal la primul login; „?" vizibil în header desktop+mobil (≥44px); turul se deschide din „?" și se finalizează normal; legal gate/login/logout neafectate.
- **Wireframe**: header dreapta: `[🔔] [?] [avatar]`; tooltip ancorat sub „?", max 220px, auto-dismiss.

### M2 · Cookie banner compact
- **Pagini**: global. **Componentă**: `components/CookieBanner.jsx` (montat în `App.js` L1709).
- **De ce există azi**: conformitate GDPR — bară full-width sus cu „Accept toate" lime (cel mai proeminent element de pe orice pagină).
- **De ce se schimbă**: fură ierarhia vizuală de la CTA-ul real pe TOATE paginile până la decizie (Fitts + hierarchy); pe mobil ocupă zona de titlu.
- **Comportament nou**: card compact jos-stânga (max 360px desktop; full-width bottom-sheet subțire pe mobil, deasupra bottom nav-ului fără a-l acoperi), stil neutru (butoane egale vizual: Accept toate / Refuz / Setări), apare o singură dată, alegerile persistă (logica existentă rămâne).
- **Acceptance**: pe 1920 și 390 nu acoperă navigația/CTA-ul hero; contrastul textului AA; alegerea persistă la refresh; link-ul /cookies rămâne.
- **Wireframe**: colț stânga-jos, card cu 2 rânduri text + 3 acțiuni pe un rând.

### M3 · „Feedback beta" mutat din zona plutitoare
- **Pagini**: `/client`, `/specialist`. **Componentă**: `components/BetaFeedbackWidget.jsx`.
- **De ce există azi**: colectare VoC pentru EO-026 — buton plutitor stânga-jos.
- **De ce se schimbă**: pe mobil SE SUPRAPUNE peste bottom nav (dovadă în audit); al 2-lea element plutitor (încalcă regula 1-floating).
- **Comportament nou**: desktop — intrare „Feedback beta" în meniul de profil/Setări + un link discret în footerul dashboardului; mobil — intrare în tab-ul Setări, cu badge „beta". Sheet-ul de feedback existent (6 întrebări) rămâne identic.
- **Acceptance**: mobil 390: niciun element nu atinge bottom nav; feedback-ul se poate trimite în continuare complet (dedupe/zi păstrat); desktop: max 1 element plutitor (chat).

### M4 · UN singur sistem de progres pentru specialist (fix-ul contradicțiilor)
- **Pagina**: `/specialist`. **Componente**: `SpecialistDashboard.jsx` + `components/WelcomeChecklist.jsx` („Configurare cont 0/6") + `lib/QuestPanel.jsx` (`/api/me/quests`) + bannerul „Ghid de pornire" + `lib/TierToolsPanel.jsx` („Unelte avansate" cu 9 blocate) + `components/TierProgressWidget.jsx`.
- **De ce există azi**: 4 feature-uri de ghidare livrate în sprinturi diferite, fiecare cu propria stare; „Ghid de pornire" citește câmpul legacy `experience_tier` (junior/verified/pro), în timp ce profilul afișează `tier` (ENTRY→TOP) — de aici „Nivel: JUNIOR" la un cont VERIFIED. Checklist-ul 0/6 nu citește datele contului.
- **De ce se schimbă**: patru surse de adevăr care se contrazic pe același ecran = defect critic de încredere (Nielsen #1).
- **Comportament nou** (doar prezentare):
  a) Apare UN card „Progresul tău" (slot 3) care afișează: tier-ul canonic (`user.tier`), progresul către următorul tier (logica `TierProgressWidget` există) și **maximum următorii 2 pași reali**, derivați din datele deja prezente în frontend: verified, jobs_completed, rating, reviews_count, service_categories, portofoliu.
  b) Pașii/quest-urile deja îndeplinite de realitate NU se afișează (ex. quest „Primul lead" e ascuns dacă `jobs_completed ≥ 1` — recompensele și API-ul quests rămân neatinse în backend; e doar filtrare de prezentare).
  c) „Ghid de pornire" și „Configurare cont 0/6" dispar pentru conturile care au depășit etapa (căsuțe derivate: profil completat, verified, servicii configurate, ofertă trimisă etc.); pentru conturi noi, conținutul lor se contopește în cardul unic.
  d) „Unelte avansate": lista blocată dispare; rămâne UN rând: „🔓 Următoarea deblocare: {prima unealtă} — la nivelul {tier}". Uneltele DEBLOCATE rămân accesibile de unde sunt azi.
  e) Cardul dispare COMPLET când totul e îndeplinit (TOP / totul bifat).
- **Acceptance**: specialist@ (VERIFIED, 27 lucrări): nu mai vede „Ghid de pornire JUNIOR", „Configurare 0/6", quest „Primul lead 0/1", lista de 9 blocate; vede cel mult „Progresul tău: VERIFIED → ADVANCED (100%)". spec.entry: vede Entry Home neschimbat (3 pași). spec.junior: cardul unic cu 2 pași reali. Voucher-ele câștigate rămân vizibile în locul lor actual. Zero apeluri API noi.
- **Wireframe**: card unic: titlu „Progresul tău" · badge tier · bară → next tier · 2 rânduri de pași cu CTA „Mergi" · rând „Următoarea deblocare".

### M5 · Marketplace public — prezentare defensivă
- **Pagina**: `/marketplace`. **Componenta**: `PublicMarketplace` (App.js) / cardul de specialist.
- **De ce există azi**: cardul afișează tot ce știe sistemul (rating, tier, scor intern, status).
- **De ce se schimbă**: vizitatorii văd „REJECTED", „TEST Phase7 Spec", „★5 (0)", „BUN · 50" — contra-dovezi pe pagina care vinde încredere (S7).
- **Comportament nou** (reguli de randare, fără schimbare de API): specialiștii cu status de moderare negativ sau neaprobați NU se randează; rating-ul apare doar dacă `reviews_count ≥ 1`, altfel chip „Nou pe platformă"; scorurile interne (50/80, „BUN/EXCELENT") nu se afișează public; max 2 badge-uri per card (verificare + specializare); numele de test nu se pot filtra sigur în frontend → nota: curățarea reală vine din purge-ul demo la lansare (EO-026), aici doar regulile de robustețe.
- **Acceptance**: zero apariții „REJECTED"/scoruri interne în DOM public; niciun card cu ★N (0); cardurile aprobate se afișează normal cu „Vezi profil".

### M6 · Dicționar de traducere pentru evenimente & jargon
- **Pagini**: Casa mea (`clientv2/PropertyHubV2.jsx` — „Ultimele evenimente"), `/imobile-verificate` (chip „100% reco").
- **De ce există azi**: timeline-ul randează direct tipul evenimentului din event bus.
- **De ce se schimbă**: „Twin dna attribute updated" nu e limbaj de client (S6).
- **Comportament nou**: mapă de prezentare tip_eveniment → etichetă RO umană („Detalii actualizate în cartea casei", „Recomandare nouă pentru casa ta", „Document adăugat", „Specialist alocat"); fallback generic „Actualizare în cartea casei"; „100% reco" → „Recomandări implementate 100%".
- **Acceptance**: zero stringuri englezești/snake_case în UI-ul proprietarului pe Casa mea; evenimente consecutive identice se grupează („×3").

### M7 · Timeline pașaport public colapsat
- **Pagina**: `/p/{slug}`. **Componenta**: `PublicPassportPage.jsx` (secțiunea timeline).
- **De ce există azi**: dovada istoricului — randează toate evenimentele.
- **De ce se schimbă**: 12+ intrări identice consecutive = zgomot care diluează dovada (S7/Miller).
- **Comportament nou**: primele 5 evenimente + buton „Vezi tot istoricul (N)" (expand in-place); intrările consecutive cu descriere identică se grupează cu contor.
- **Acceptance**: pașaportul anonim afișează ≤5 iteme inițial; expand-ul arată tot; SEO/OG neafectate (randarea OG pentru boți e separată, pe backend — neatinsă).

### M8 · Dedupe CTA de plată (client activ)
- **Pagina**: `/client` Acasă. **Componenta**: `clientv2/HomeV2.jsx` (hero „Lucrare activă" + lista „Noutăți pentru tine").
- **De ce există azi**: hero-ul și Noutățile se generează din surse diferite și afișează aceeași plată.
- **De ce se schimbă**: același CTA de 2× (S5); în plus, cât există plată în așteptare, „Solicită ofertă" din header rămâne buton primar concurent.
- **Comportament nou**: dacă hero-ul afișează o acțiune de plată/confirmare, itemul identic din Noutăți nu se mai randează; cât timp există tranzacție activă în hero, butonul header „Solicită ofertă" trece pe stil secundar (outline). Nimic nu dispare funcțional.
- **Acceptance**: client@ vede plata O SINGURĂ dată (hero); după plată, Noutățile revin normal; header-ul revine primar când nu există tranzacție activă.

---

## Plan de testare (înainte de finish)
1. Testing agent (frontend): conturi spec.entry / spec.junior / specialist@ / client.junior / client@ + anonim pe /marketplace și /p/gbegxfyz9m — criteriile de acceptare de mai sus, desktop 1920 + mobil 390.
2. Regresie: login/logout/legal gate, trimitere feedback beta din noul loc, quest rewards (voucher-ele rămân), plata escrow din hero.
3. Capturi before/after pentru fiecare M + re-scoring paginilor în PAGE_SCORECARD.

## Riscuri & mitigări
| Risc | Mitigare |
|---|---|
| Descoperirea funcțiilor scade fără tur auto | „?" permanent + tooltip primul login; hero-ul Next Action ghidează oricum |
| Filtrarea marketplace scade nr. de specialiști afișați | dispar doar neaprobații/test; la lansare purge-ul demo rezolvă sursa |
| Derivarea pașilor din date diferă de starea backend a quest-urilor | doar prezentare; recompensele/endpointurile neatinse; test cu date reale |
| Cookie compliance | opțiunile rămân identice (Accept/Refuz/Setări), doar poziția/stilul se schimbă |
| Obiceiuri utilizatori beta | schimbările sunt eliminări de zgomot, nu mutări de funcții; rollback per componentă |

## Efort & impact
Efort total: **1 sesiune** (M1-M3, M6-M8 = S; M4, M5 = M). Impact business: încredere beta + activare + time-to-cash. Îmbunătățiri scor estimate: Specialist 52→~70 · Marketplace 58→~80 · Pașaport 80→~85 · Client activ 72→~76 · Property Hub 55→~60 · media 68→~75.
