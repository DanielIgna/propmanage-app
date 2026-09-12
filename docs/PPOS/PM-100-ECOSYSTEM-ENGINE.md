# PM-100 — ECOSYSTEM ENGINE · Design Canonic
Status: APPROVED DESIGN v1.0 · 27 Iun 2026 · Owner: Product Council
Guvernare: implementarea rămâne sub BETA WAR ROOM (feature freeze). Acest document devine **filtrul și roadmap-ul** oricărei funcționalități viitoare.

---

## 0. LEGEA ECOSISTEMULUI (Next Valuable Action — NVA)
> **„Orice funcționalitate nouă trebuie să răspundă la întrebarea: Ce acțiune valoroasă generează în continuare? Dacă nu generează următorul pas în ecosistem, nu se implementează."** — Fondator, verbatim.

Corolare operaționale:
1. Fiecare eveniment din platformă are un câmp conceptual `next_action` — dacă e null, evenimentul e mort și se elimină.
2. Zero interacțiuni false: nicio notificare fără informație nouă, niciun badge fără merit, niciun ranking cumpărat.
3. Valoarea trebuie să fie bilaterală: o buclă care ajută doar platforma (nu owner/specialist) se respinge.

---

## 1. HARTA ACTORILOR & MOTORUL CENTRAL
**Actori**: Proprietari · Specialiști · Companii (post-beta) · Admin.
**Active**: Proprietate → Documente → Digital Twin → Istoric (Timeline) → Pașaport.
**Piețe**: Cereri ↔ Oferte ↔ Escrow ↔ Recenzii ↔ Trust Score ↔ Marketplace ranking.
**Motorul central (flywheel-ul primar)**:
```
Proprietate adăugată → Audit/Scor → Twin → Lipsuri detectate → Cerere →
Specialist potrivit → Lucrare + Escrow → Foto/Document → Twin actualizat →
Istoric îmbogățit → Valoare percepută ↑ → Recenzie → Trust ↑ → Ranking ↑ →
Pașaport partajat → Proprietar nou → (reia)
```
Fiecare rotație completă îmbogățește TREI active simultan: istoria proprietății, reputația specialistului, inteligența platformei.

---

## 2. LIFECYCLE-UL COMPLET AL UNEI PROPRIETĂȚI (Ziua 0 → Anul 5)

### Ziua 0 — Nașterea digitală
| Eveniment | Generează automat |
|---|---|
| Cont creat | UN pas ghidat: „Adaugă proprietatea" (nimic altceva — zero zgomot) |
| Proprietate adăugată | ① recomandare audit tehnic („Scorul Casei" intern, 2 min) ② pasul 2: primul document ③ scor Sănătatea casei = baseline |
| Primul document | ① celebrare „casa are memorie" ② +% completeness cu pasul următor afișat ③ eveniment în Timeline |

### Săptămâna 1 — Fundația
| Audit completat | ① creează/îmbogățește Digital Twin ② detectează lipsuri de mentenanță → propune 1-3 cereri concrete (nu generice) ③ generează lista documentelor lipsă (carte funciară, certificat energetic, PV instalații) |
| Twin creat | ① scor maturitate twin ② riscuri identificate → remindere programate (nu instant, la momentul potrivit) |
| Prima cerere trimisă | ① notifică DOAR specialiștii cu capabilități potrivite din zonă ② owner vede „cererea ta a ajuns la N specialiști verificați" (transparență, nu vanitate) |

### Luna 1 — Primul ciclu de valoare
| Ofertă primită | comparator de oferte + istoric specialist (recenzii REALE sau „Nou pe platformă" onest) |
| Lucrare finalizată (escrow eliberat) | ① foto lucrare → Twin update ② document/garanție → Cartea casei ③ eveniment în Timeline ④ cerere de recenzie (o singură dată) ⑤ dacă lucrarea e recurentă (ex. revizie centrală) → propune reminder anual |
| Recenzie lăsată | Trust Score specialist ↑ → ranking organic ↑ (buclă către ecosistem) |

### Anul 1 — Ritmul
- Calendar de mentenanță derivat din Twin (vârsta instalațiilor + tipul proprietății): revizie centrală (anual), verificare instalație electrică, curățare jgheaburi, rovinietă tehnică a casei.
- Fiecare reminder = cerere pre-completată cu 1 click → hrănește marketplace-ul CU CERERE REALĂ.
- Certificat energetic aproape de expirare → reminder + specialiști autorizați.
- Asigurare: reminder reînnoire cu istoricul atașabil (dosarul casei scade prima — valoare monetară concretă).
- Raport anual „Anul casei tale": ce s-a făcut, cât a costat, ce urmează, evoluția scorului. (Un email/an care chiar merită deschis.)

### Anii 2–5 — Activul digital matur
- Istoric complet = **pașaport valoros la vânzare/închiriere**: partajare cu QR către cumpărători/chiriași → fiecare partajare e canal de achiziție (buclă virală).
- Valoarea documentată: „casele cu istoric complet se vând mai ușor și mai scump" — PVI evoluează pe dovezi, nu pe estimări.
- Transfer de proprietate cu istoric (post-beta S5): noul proprietar devine utilizator cu casa deja „inteligentă" — cea mai puternică buclă de retenție inter-generațională.
- Twin-ul devine mai deștept cu fiecare lucrare: după 5 ani știe vârsta fiecărei instalații, istoricul defecțiunilor, costul total de întreținere/an.

**Regula de aur**: proprietatea devine mai inteligentă cu FIECARE eveniment; niciun eveniment nu moare fără să programeze următorul.

---

## 3. LIFECYCLE-UL COMPLET AL SPECIALISTULUI (Înregistrare → Autoritate)

### Etapa 0 — ENTRY (ziua 0–7)
- Înregistrare → UN pas: completează capabilitățile (serviciile stăpânite) → matching-ul pornește imediat.
- Verificare identitate + certificări (KYC existent) → badge „Verificat" = prima monedă de încredere.
- Onest by design: profil nou = „Nou pe platformă", NU rating fabricat.

### Etapa 1 — VERIFIED (prima lună)
- Primește oportunități potrivite pe capabilități + zonă; răspunsul rapid e răsplătit organic (time-to-first-offer intră în trust).
- Primele 3 lucrări = perioada de fondare a reputației: recenzii reale + foto înainte/după → portofoliu construit DIN lucrări, nu din upload-uri decorative.
- Portofoliul se auto-construiește: fiecare lucrare finalizată cu foto devine intrare de portofoliu (cu acordul ownerului).

### Etapa 2 — ADVANCED (luni 2–6)
- Trust Score compus TRANSPARENT (formula publică): recenzii (40%) + finalizare la timp (20%) + rată de răspuns (15%) + clienți repetați (15%) + vechime+volum (10%). Fără nicio componentă plătită.
- Deblochează: cockpit pipeline, statistici de business (venit/lună, rată câștig oferte, timp mediu răspuns vs. media pieței).
- Clienți repetați: ownerul care revine primește „specialiștii tăi" — rebooking cu 1 click → specialistul își construiește carte de clienți.

### Etapa 3 — TRUSTED (luni 6–18)
- **Contracte de mentenanță**: din lucrările recurente, platforma propune AMBELOR părți un contract anual (revizie centrală, întreținere HVAC) — venit predictibil pentru specialist, grijă zero pentru owner. Cea mai valoroasă buclă B2B2C.
- AI recommendations pentru specialist: „cererea X se potrivește 92% cu istoricul tău", „în zona ta cererea pe HVAC crește — adaugă capabilitatea".
- Poate fi recomandat de alți specialiști (referral profesional) pentru capabilități complementare — echipe organice.

### Etapa 4 — AUTHORITY (anul 2+)
- Top organic în marketplace pe nișa+zona lui (câștigat, necumpărat).
- Business analytics complet: sezonalitate, valoare medie lucrare, LTV client, comparație anonimizată cu piața.
- Devine magnet de cereri directe prin profil public + portofoliu → aduce SINGUR clienți pe platformă (buclă de achiziție inversă).

### Garanții anti-pay-to-win (constituționale)
1. Ranking-ul NU se poate cumpăra — niciun slot plătit în listă fără etichetă explicită și separată.
2. Promovarea plătită (dacă va exista) = doar vizibilitate marcată „Sponsorizat", NICIODATĂ amestecată în scorul de încredere.
3. Recenziile pot veni doar din lucrări cu escrow finalizat (imposibil de fabricat).
4. Decăderea trust-ului: inactivitate/anulări repetate scad organic scorul — locul din față trebuie apărat prin calitate.

---

## 4. OWNER ENGAGEMENT ENGINE — „fiecare vizită are valoare"

**Principiu**: nu chemăm userul cu notificări; îl întâmpinăm cu informație nouă REALĂ când vine. Notificarea push/email există DOAR când inacțiunea costă (expirări, riscuri, plăți).

### Sursele de valoare la fiecare vizită (ierarhizate)
1. **Starea tranzacției active** (dacă există) — întotdeauna primul.
2. **Pasul următor al casei** (completeness/next step) — mereu unul singur, concret, cu câștigul afișat.
3. **Remindere de mentenanță** ajunse la scadență (din Twin, nu generice).
4. **Evoluția valorii/scorului** — DOAR când s-a schimbat ceva (nou document, lucrare, piață): „PVI +3% după renovarea băii".
5. **Recomandări de îmbunătățire** cu ROI estimat (energie, izolație) — max 1 pe vizită.
6. **Expirări legale**: certificat energetic, asigurare, verificare centrală (obligație legală la 2 ani în RO).
7. **Specialiști noi verificați în zona ta** — doar dacă acoperă un lipsă din calendarul casei tale.
8. **Noutăți comunitate/ghiduri** — ultimul, niciodată deasupra acțiunilor casei.

### Reguli anti-abandon & anti-spam
- Frecvența email: max 1 digest/săptămână + evenimente tranzacționale. Zero „ne e dor de tine".
- Fiecare notificare răspunde la NVA: ce acțiune valoroasă declanșează? Altfel nu se trimite.
- Dacă ownerul nu are nimic nou: dashboardul spune onest „Totul e în regulă cu casa ta — următoarea verificare: [data]" — liniștea e și ea valoare (încredere).

---

## 5. MARKETPLACE INTELIGENT — „niciodată gol, niciodată manipulat"

### Anti-cold-start (secvența de lansare)
1. Un singur oraș; întâi proprietari cu cereri REALE, apoi specialiști recrutați PE cererile existente (nu invers).
2. Sub N specialiști reali → pagina publică devine „Early Access: aplică ca specialist / lasă cererea" (fix P0-3 din RC review) — nu listă goală, nu date fake.
3. Cereri fără ofertă în 48h → escaladare admin (matchmaking manual în beta) + sugestie owner: lărgește zona/bugetul.

### Prioritizare organică (formulă publică, auditabilă)
`rank = trust_score × match_capabilități × proximitate × disponibilitate` — fără variabile plătite. Egalitate → cel mai rapid la răspuns.

### Mecanisme de auto-îmbunătățire zilnică
- **Echilibrarea cererii**: exces de cereri pe o nișă/zonă → platforma le semnalează specialiștilor din nișe adiacente + recomandă adăugarea capabilității (cu certificare unde e legal necesar).
- **Gruparea cererilor apropiate**: 3 cereri de fațadă pe aceeași stradă → specialistul primește „pachet de zonă" (deplasare unică → preț mai bun pentru toți — valoare bilaterală reală).
- **Alternative oneste**: niciun specialist disponibil → propune: alt interval, nișă adiacentă verificată, sau „te anunțăm când apare" (waitlist care chiar anunță).
- **Anti-spam ofertare**: oferta cere mesaj specific cererii (nu template); rata de oferte ignorate scade organic vizibilitatea ofertantului-spam.
- **Detectarea găurilor de ofertă**: heatmap cereri fără acoperire → ținte de recrutare specialiști (creștere condusă de cerere, nu de vanitate).

---

## 6. ECOSYSTEM DASHBOARD (design — extinde Beta Cockpit, NU dublează)

### KPI-urile de sănătate (nu vanitate, nu venit)
| # | KPI | Definiție strictă |
|---|---|---|
| 1 | Active Owners | ≥1 acțiune de valoare în 30z (nu doar login) |
| 2 | Active Specialists | ≥1 ofertă/lucrare în 30z |
| 3 | Properties Added | proprietăți reale noi /săpt |
| 4 | Digital Twins | twins cu maturitate >0 |
| 5 | Twin Completeness | mediana completitudinii |
| 6 | Requests Created | cereri reale /săpt |
| 7 | Offers per Request | mediană (sănătatea lichidității!) |
| 8 | Avg Response Time | cerere → prima ofertă |
| 9 | Marketplace Conversion | cereri → lucrări plătite |
| 10 | Avg Completion Time | acceptare → finalizare |
| 11 | Jobs Completed | lucrări cu escrow eliberat /săpt |
| 12 | Repeat Customers | % owneri cu ≥2 lucrări |
| 13 | Maintenance Contracts | contracte recurente active |
| 14 | Trust Growth | Δ trust mediu specialiști /lună |
| 15 | Recommendation Rate | % VoC „da, recomand" + share-uri pașaport |

### Graful de influență (care KPI mișcă ce KPI)
```
Properties Added → Twins → Twin Completeness → Requests Created
Requests Created → Offers/Request → Response Time ↓ → Marketplace Conversion ↑
Conversion ↑ → Jobs Completed → (Twin Completeness ↑) + (Trust Growth ↑)
Trust Growth → Repeat Customers → Maintenance Contracts → Requests (recurente) ↑
Jobs Completed → Recommendation Rate → NEW Owners (Properties Added ↑)  ← bucla se închide
Active Specialists ↔ Offers/Request (echilibru: prea puțini = response time ↑; prea mulți = win-rate ↓ → churn specialiști)
```
**Indicatorul suprem**: *Ecosystem Momentum* = rotații complete de flywheel /săpt (proprietate→cerere→lucrare→document→recenzie). O singură cifră care spune dacă ecosistemul respiră.

---

## 7. PM-107 — CELE 100+ BUCLE NATURALE
Format: **Trigger → Acțiunea următoare → Valoarea reală**. Toate bilaterale, zero fake engagement.

### A. Proprietate & Documente (1–15)
1. Cont creat → un singur pas ghidat → activare fără confuzie.
2. Proprietate adăugată → recomandare audit 2 min → baseline scor.
3. Audit completat → twin creat → casa devine măsurabilă.
4. Primul document → pasul următor cu +% afișat → progres concret.
5. Document „certificat energetic" încărcat → data expirării extrasă → reminder programat.
6. Document garanție lucrare → reminder înainte de expirarea garanției → owner nu pierde bani.
7. Carte funciară lipsă detectată → ghid pas-cu-pas obținere → document nou.
8. 5+ documente → propunere organizare pe categorii → regăsire rapidă.
9. Completeness 100% pe categorie → deblocare raport „dosarul complet al casei" → valoare la vânzare.
10. Document ilizibil/expirat → cerere de reîncărcare → arhivă mereu validă.
11. Foto proprietate adăugată → twin vizual îmbogățit → pașaport mai atractiv.
12. Adresă completată → matching specialiști pe zonă → oferte relevante.
13. An construcție completat → riscuri specifice vârstei → calendar mentenanță corect.
14. Suprafață/camere completate → estimări de cost mai precise la cereri → oferte mai corecte.
15. Istoric importat (facturi vechi) → timeline retroactiv → valoare din prima zi.

### B. Digital Twin & Mentenanță (16–35)
16. Twin detectează instalație veche → recomandare inspecție → prevenție reală.
17. Inspecție făcută → raport în Cartea casei → twin maturitate ↑.
18. Revizie centrală înregistrată → reminder automat anul următor → obligație legală acoperită.
19. Lucrare finalizată → foto → twin actualizat → istoric vizual.
20. 3 defecțiuni pe aceeași instalație → recomandare înlocuire cu calcul cost reparații vs. nou → decizie informată.
21. Sezon (toamnă) + twin cu centrală → reminder revizie ÎNAINTE de sezonul rece → cerere la timp, nu în criză.
22. Risc umiditate detectat → recomandare verificare hidroizolație → prevenirea daunei mari.
23. Vârsta acoperișului > prag → inspecție recomandată → cerere reală.
24. Consum energetic mare (certificat clasa E) → recomandări eficientizare cu ROI → lucrări de valoare mare.
25. Mentenanță făcută la timp constant → scor Sănătate ↑ → primă asigurare potențial mai mică.
26. Mentenanță ratată → scor ↓ vizibil cu explicație → motivație de recuperare onestă.
27. Twin complet → raport anual auto-generat → documentul care „vinde" platforma familiei.
28. Instalație nouă montată → garanție + manual în Cartea casei → zero hârtii pierdute.
29. Apartament în bloc → riscuri comune (coloane, acoperiș) semnalate → cereri grupabile cu vecinii.
30. Lucrare DIY înregistrată de owner → twin update manual → istoricul rămâne complet.
31. Contor/index înregistrat periodic → trend consum → detectare anomalii (pierderi apă).
32. Aparat electrocasnic adăugat (assets) → reminder întreținere specifică → viață mai lungă a activelor.
33. Twin maturitate 100% → badge „Casă complet digitalizată" pe pașaport → diferențiere la vânzare.
34. Renovare majoră planificată → checklist documente+specialiști+etape → proiect ghidat.
35. Post-renovare → re-audit recomandat → scor recalculat pe dovezi.

### C. Cereri, Oferte & Marketplace (36–55)
36. Reminder scadent → cerere pre-completată 1-click → fricțiune zero.
37. Cerere creată → notificare DOAR specialiștilor compatibili → zero spam, response time mic.
38. Cerere fără ofertă 48h → escaladare + sugestii owner → nicio cerere moartă.
39. Ofertă primită → comparator cu istoric verificabil → decizie încrezătoare.
40. Ofertă acceptată → escrow → siguranță ambele părți.
41. Escrow finalizat → cerere de recenzie unică → trust alimentat doar din realitate.
42. Cereri similare în zonă → pachet de zonă pentru specialist → preț mai bun pentru toți.
43. Cerere respinsă de toți → analiză motiv (buget/descriere) → coaching owner la re-postare.
44. Sezon de vârf pe nișă → avertizare owner „programează din timp" → cereri distribuite, nu în criză.
45. Specialist indisponibil → propune fereastra următoare sau alternativă verificată → cererea nu moare.
46. Lucrare de urgență (prioritate) → specialiștii cu răspuns rapid notificați primii → SLA organic.
47. Deviz depășit în lucru → aprobare explicită owner în app → zero surprize la plată (încredere).
48. Chat activ pe lucrare → istoric decizii salvat → probe în caz de dispută.
49. Dispută deschisă → mediere cu istoricul complet (chat+foto+deviz) → rezolvare pe dovezi.
50. Lucrare finalizată în altă nișă necesară (electricianul vede țeavă spartă) → recomandă cerere nouă → cross-sell natural, cu valoare.
51. Owner mulțumit → „specialiștii tăi" cu rebooking 1-click → clienți repetați.
52. 2+ lucrări recurente cu același specialist → propunere contract mentenanță ambelor părți → predictibilitate.
53. Heatmap cereri neacoperite → recrutare specialiști țintită → ofertă crescută unde doare.
54. Specialist nou verificat în zonă → anunțat DOAR ownerilor cu lipsuri pe nișa lui → prima lucrare vine repede.
55. Recenzie cu foto → intrare de portofoliu (cu acord) → profil care se construiește singur.

### D. Trust, Recenzii & Calitate (56–70)
56. Recenzie lăsată → trust ↑ → ranking organic ↑.
57. Trust ↑ → mai multe oportunități relevante → venit ↑ → retenție specialist.
58. Răspuns rapid constant → componenta response în trust ↑ → avantaj câștigat.
59. Anulări repetate → trust ↓ cu explicație → autocorecție comportament.
60. Recenzie negativă → drept la replică public + plan de remediere → corectitudine vizibilă.
61. Remediere confirmată de owner → nota contextualizată → a doua șansă meritată.
62. Inactivitate 90z → trust decay lent → topul rămâne viu, nu fosilizat.
63. Certificare nouă încărcată → capabilitate deblocată după validare → ofertă legală și sigură.
64. Trust prag TRUSTED atins → deblocare contracte mentenanță → calitatea devine business.
65. Formula trust publică → specialistul știe exact ce să îmbunătățească → meritocrație transparentă.
66. Owner verificat (telefon/identitate) → cererile lui marcate „owner verificat" → specialiștii ofertează cu încredere.
67. Istoric plăți la timp owner → încredere reciprocă vizibilă → oferte mai bune.
68. Review-bombing detectat (pattern) → verificare escrow-only → imunitate la fraudă.
69. Specialist recomandă alt specialist (nișă complementară) → echipe organice → proiecte mari posibile.
70. Echipă cu 3+ proiecte comune → profil de echipă → cereri complexe deblocate.

### E. Creștere & Viralitate (71–85)
71. Pașaport partajat cu QR la vânzare → cumpărătorul vede istoricul → cont nou + transfer istoric.
72. Chiriaș primește acces limitat (utilități, contacte) → cunoaște platforma → viitor owner-user.
73. „Scorul Casei" public completat → cont pentru salvarea raportului → lead calificat.
74. Raport anual al casei → share cu familia → utilizatori noi din încredere personală.
75. Lucrare reușită → owner recomandă vecinului cu aceeași problemă → cerere nouă din word-of-mouth.
76. Pachet de zonă (42) → vecinii fără cont invitați să se alăture cererii → achiziție prin economie reală.
77. Specialist își pune profilul PropManage în ofertele offline → clienții lui devin owneri pe platformă → achiziție inversă.
78. Agent imobiliar cere pașaportul → vede valoarea → recomandă vânzătorilor următori.
79. Notar/bancă acceptă dosarul digital → legitimitate instituțională → standard de piață.
80. Transfer proprietate cu istoric → noul owner activ din ziua 1 → retenție inter-generațională.
81. Ghid public SEO (ex. „verificarea centralei") → cititor → calculator scor → cont.
82. Recenziile publice indexabile → SEO local per nișă+oraș → cereri organice.
83. Studiu anual „starea caselor din RO" din date agregate anonime → PR → autoritate de brand.
84. Owner cu 2+ proprietăți → invitat să administreze tot portofoliul → expansiune în cont.
85. Companie mică (5+ proprietăți) → cont business (post-beta) → segment B2B deschis natural.

### F. Financiar & Valoare (86–95)
86. Lucrare plătită → cost înregistrat în istoric → cost total de proprietate transparent.
87. Istoric costuri → buget anual recomandat pe casă → planificare financiară reală.
88. PVI ↑ după renovare documentată → dovadă pentru preț de vânzare → bani reali la exit.
89. Dosar complet → primă de asigurare negociabilă cu dovezi → economie anuală.
90. Deviz mediu pe nișă (date agregate) → owner știe prețul corect → încredere în ofertare.
91. Specialist vede prețul mediu de piață → ofertă competitivă calibrată → win-rate ↑.
92. Escrow multi-etape la proiecte mari → risc redus ambele părți → proiecte mari migrate pe platformă.
93. Wallet cu sold → plăți instant la finalizare → specialiștii preferă platforma.
94. e-Factura automată (post-beta) → contabilitate zero-effort specialist → lock-in prin utilitate.
95. Raport fiscal anual specialist → declarații ușoare → retenție profesională.

### G. Inteligență & Date (96–105)
96. Fiecare lucrare → twin mai precis → recomandări mai bune pentru TOATE casele similare (network effect de date).
97. Copilot AI antrenat pe istoricul casei → răspunsuri specifice („când am schimbat boilerul?") → utilitate zilnică.
98. Pattern defecțiuni pe model de centrală → alertă proactivă ownerilor cu același model → prevenție la scară.
99. Sezonalitate cereri → predicție & pre-alocare specialiști → response time mic iarna.
100. VoC beta → issue board → fix → changelog public „ați cerut, am făcut" → încredere în evoluție.
101. Cereri eșuate analizate → îmbunătățirea formularlui de cerere → conversie ↑ pentru toți.
102. Timeline complet → AI Property Story („povestea casei") → document emoțional la vânzare.
103. Date agregate anonime pe cartier → „sănătatea cartierului" → context valoros la cumpărare.
104. Specialiștii buni atrag cereri → datele lor de succes devin ghiduri de bune practici → nivelul pieței ↑.
105. Fiecare rotație de flywheel → Ecosystem Momentum măsurat → deciziile de produs conduse de sănătatea reală.

### BUCLE RESPINSE (fake engagement — interzise constituțional)
- ✗ Streak-uri de login („ai intrat 7 zile la rând!") — vanitate fără valoare.
- ✗ Badge-uri fără acoperire în realitate (colecționabile decorative).
- ✗ Notificări „ne e dor de tine" / „vezi ce ai ratat".
- ✗ Ranking plătit amestecat în trust.
- ✗ Recenzii stimulate cu discount (cumpărate).
- ✗ Leaderboard public specialiști pe volum (încurajează cantitate, nu calitate).
- ✗ Puncte/monede virtuale fără valoare de utilizare reală.

---

## 8. GAP ANALYSIS & SECVENȚIERE (ce există vs. ce lipsește)

### Există DEJA (validat în beta candidate)
Onboarding ghidat (2) · completeness+next step (4) · twin+maturitate (3,16) · riscuri (22) · cereri→matching capabilități (37) · escrow (40) · recenzii escrow-only (41,68) · pașaport+QR (71) · Scorul Casei public (73) · capabilities editor (63) · wallet (93) · timeline (102 parțial) · VoC+issue board (100) · Beta Cockpit (bazele §6).

### De construit POST-BETA (ordonate prin NVA + date reale)
- **P0 post-beta**: Calendar mentenanță din twin (18,21,36 — CX-4, motorul cererilor recurente) · Ecosystem Dashboard §6 (extinde cockpit) · rebooking „specialiștii tăi" (51).
- **P1**: contracte mentenanță (52,64) · pachete de zonă (42,76) · raport anual al casei (27,74) · trust score compus transparent cu decay (56-65) · alerte proactive pe pattern (98).
- **P2**: transfer proprietate cu istoric (80) · portofoliu/B2B (84,85) · e-Factura (94) · AI Property Story (102) · echipe de specialiști (69,70).
- **Condiție de intrare pentru ORICE item**: răspunsul la NVA + un KPI din §6 pe care îl mișcă măsurabil.

### Regula de guvernare
În BETA WAR ROOM nu se implementează nimic din acest document. După primele 2-4 săptămâni de beta, datele reale (funnel + VoC + Ecosystem Momentum) decid ordinea finală — designul de față e harta, utilizatorii sunt busola.
