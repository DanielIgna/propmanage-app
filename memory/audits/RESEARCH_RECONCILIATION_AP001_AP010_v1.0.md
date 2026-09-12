# RESEARCH RECONCILIATION — Cohorta AP-001 → AP-010

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Classification**: Research Reconciliation — evidence-only, zero fabrication
**Board Directive**: BD-RDPE (Feature Freeze) ACTIV · Building Typology Foundation Audit v1.0 rămâne neschimbat
**Scope**: reanaliza exclusiv a evidence-ului deja existent (AP-001..AP-010 + PATTERN_REGISTRY + PROPMANAGE_PRESIDENT_RESEARCH_COHORT_v1.0.md). Zero raw evidence nou. Zero AP-011+. Zero cod. Zero produs.

**Evidence integrity discipline**: fiecare afirmație în acest document este marcată explicit ca `[EVIDENCE]`, `[INFERENCE]`, `[HYPOTHESIS]`, sau `[UNKNOWN]`.

---

## A. Cohortă analizată

Zece (10) interviuri Validated în infrastructura curentă `/app/memory/audits/`:

| InterviewID | Respondent | Bloc | An | Apts | Vechime președinte | Platformă | Fișier sursă |
|---|---|---|---|---|---|---|---|
| AP-001 | Adrian Popa | Florești, Cluj | 2019 | 16 | [UNKNOWN] | [UNKNOWN] | INTERVIEW_2026-08-14_FLORESTI-CLUJ-AP-001.md |
| AP-002 | Ilie | Mehedinți (P+4, 2 scări) | 1976 | 20 | 40+ ani | — | INTERVIEW_2026-02-06_MEHEDINTI-ILIE.md |
| AP-003 | Adriana | Negoiu 8D | 2006 | 13 | ~1 an | — | INTERVIEW_2026-02-06_NEGOIU-8D.md |
| AP-004 | Mihăilă | Negoiu nr. 10 | 1975 | 40 | 10+ ani | [UNKNOWN] | INTERVIEW_2026-08-14_NEGOIU-10-AP-004.md |
| AP-005 | Bradea | Soporului nr. 5 | 2018 | 130 | 7+ ani | [UNKNOWN] | INTERVIEW_2026-08-14_SOPORULUI-5-AP-005.md |
| AP-006 | Răzvan | West Conect / Iulius Mall | 2019 | 286 | ~4 ani | eBloc | INTERVIEW_2026-08-14_WEST-CONECT-AP-006.md |
| AP-007 | Kincsö Pál | [UNKNOWN] | 2022 | 14 | [UNKNOWN] | Bloc Sistem | INTERVIEW_2026-08-14_KINCSO-PAL-AP-007.md |
| AP-008 | Paul Jeican | Predeal nr. 34 | 2008 | 10 apt + 5 case | [UNKNOWN] | [UNKNOWN] | INTERVIEW_2026-08-14_PREDEAL-34-AP-008.md |
| AP-009 | Sandu Pop | Mehedinți nr. 23 | 1976 | 104 | ~3 ani | eBloc | INTERVIEW_2026-08-14_MEHEDINTI-23-AP-009.md |
| AP-010 | Cristian | Mehedinți nr. 17 (5 scări) | 1976 | 104 | [UNKNOWN] | [UNKNOWN] | INTERVIEW_2026-08-14_MEHEDINTI-17-AP-010.md |

**Confirmare structurală**: AP-009 și AP-010 (aceeași stradă, dimensiuni identice, an identic) sunt **asociații distincte** — nu duplicate. AP-002 partajează strada Mehedinți dar are dimensiune diferită și president diferit. Confirmat de `INTERVIEW_REGISTRY.md`.

---

## B. Evidence coverage — matrice pe 12 arii obligatorii

Legendă: `E` = evidence prezent · `P` = parțial · `U` = UNKNOWN · `—` = nu se aplică

| Interview | Probleme reale | Workaround | Documentație | Mentenanță | Comunicare | Furnizori | Lucrări | Riscuri | Digitalizare | Soluții deja folosite | Competitor / Platformă | WTP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| AP-001 | U | U | U | U | U | U | U | U | U | U | U | U |
| **AP-002** | **E** | **P** | **E** | **P** | **E** | **P** | **E** | **E** | U | U | E (declared: fără platformă) | U |
| **AP-003** | **E** | **P** | **E** | **E** | **E** | U | **E** | P | U | U | E (declared: fără platformă) | U |
| AP-004 | U | U | U | U | U | U | U | U | U | U | U | U |
| AP-005 | U | U | U | U | U | U | U | U | U | U | U | U |
| AP-006 | U | U | U | U | U | U | U | U | E (folosește eBloc) | E (eBloc) | **E (eBloc user)** | U |
| AP-007 | U | U | U | U | U | U | U | U | E (folosește Bloc Sistem) | E (Bloc Sistem) | **E (Bloc Sistem user)** | U |
| AP-008 | U | U | U | U | U | U | U | U | U | U | U | U |
| AP-009 | U | U | U | U | U | U | U | U | E (folosește eBloc) | E (eBloc) | **E (eBloc user)** | U |
| AP-010 | U | U | U | U | U | U | U | U | U | U | U | U |

**Concluzii de acoperire (evidence-based)**:
- **2/10** interviuri au evidence completă pe majoritatea ariilor (AP-002 și AP-003).
- **3/10** interviuri au evidence pe **exclusiv o singură arie** — Competitor/Platformă (AP-006, AP-007, AP-009).
- **5/10** interviuri sunt profile snapshots pure — evidence exclusiv structural (an, apts, vechime): AP-001, AP-004, AP-005, AP-008, AP-010.
- **0/10** interviuri au evidence explicit pe WTP (nici declarată, nici demonstrată).
- **0/10** interviuri au evidence pe Furnizori (specialist supply) în afară de AP-002 (parțial, pe verificare/încredere).

---

## C. Pattern reconciliation — analiză P-001 → P-014 (13 pattern-uri active)

Metodologie strictă: praguri neschimbate (1=Observation, 2=Emerging, 3+=Validated Candidate).
Zero promovare automată.

### C.1 Pattern reconciliation table

| Pattern ID | Definiție (rezumat) | Evidence sources | Confirmări actuale | Evidence literal / summary | Confidence | Suficient pentru next stage? | Ce lipsește pentru next stage |
|---|---|---|---|---|---|---|---|
| P-001 | Infrastructure aging la blocurile post-2000 | AP-003 | **1** | „Cablarea între etaje nu poate fi extinsă — tubulatura este obturată/blocată" (AP-003, 2006). | Low (7%) | NU | O a doua confirmare independentă din alt bloc post-2000 (AP-001 2019, AP-005 2018, AP-006 2019, AP-007 2022, AP-008 2008 — toate profile-only). |
| P-002 | Succesiune președinte nestandardizată | AP-002, AP-003 | **2** | „Documentele au fost preluate de la fostul președinte" + „NU există procedură standard de predare-primire" (AP-003); confirmat implicit prin lipsă documente în AP-002. | Low (13%) | NU | O a treia confirmare independentă. Candidatele naturale: AP-004 (10+ ani experiență), AP-005 (7+ ani) — ambele profile-only actual. |
| P-003 | WhatsApp ca canal de comunicare (cu nuanță generațională) | AP-002, AP-003 | **2** | AP-003: „WhatsApp + Avizier". AP-002: „telefon, WhatsApp, avizier (telefon menționat primul)". **Nuanță documentată**: primaritate variabilă cu vârsta președintelui. | Low (13%) | NU | A treia confirmare + follow-up explicit pe generație / vârstă / experiență. |
| P-004 | Mentenanță preventivă preferată în locul reactivei | AP-002, AP-003 | **2** | AP-002: „reparații preventive · igienizare · infrastructură comună · mentenanță etapizată" (priorități declarate). AP-003: „Refacerea fațadei · Termoizolație mai bună" (priorități declarate). | Low (13%) | NU | A treia confirmare. Candidați naturali: AP-004..AP-010 (profile-only). |
| P-005 | Absența trasabilității incidentelor/lucrărilor → risc legal | AP-002, AP-003 | **2** | AP-002: „Lipsa trasabilității lucrărilor · Lipsa dovezilor executării lucrărilor". AP-003: „Monitorizarea eficienței dezinsecției — nu există sistem". | Low (13%) | NU | A treia confirmare. Follow-up dedicate la interviuri viitoare. |
| P-006 | Cerere contorizare individuală apă | AP-003 | **1** | „Contorizare individuală apă — motivat de eliminarea conflictelor și responsabilizare individuală" (AP-003). | Low (7%) | NU | A doua confirmare independentă. |
| P-007 | Goluri echipament siguranță declanșate de incidente | AP-003 | **1** | „Stingătoare — motivat de incident anterior cu materiale inflamabile" (AP-003). | Low (7%) | NU | A doua confirmare independentă. |
| P-008 | Costul evaluării inițiale = barieră decizională | AP-002 | **1** | „Specialiștii cer ~150 lei doar pentru deplasare și ofertare. Președintele consideră 30-40 lei ca rezonabil" (AP-002). | Low (7%) | NU | A doua confirmare independentă. Follow-up specific: „câte oferte ai cerut ultima dată? cât a costat evaluarea?" |
| P-009 | Gap conștientizare prețuri actuale piață | AP-002 | **1** | „Locatarii se raportează la prețurile de acum 20 ani → refuză aprobarea investițiilor la prețuri actuale" (AP-002). | Low (7%) | NU | A doua confirmare. |
| P-010 | Deficit încredere specialiști → cerere verificare | AP-002 | **1** | „Recomandări pentru materiale nepotrivite; diferențe majore între oferta inițială și costul final" (AP-002). | Low (7%) | NU | A doua confirmare. |
| P-011 | Documentare insuficientă → risc juridic | AP-002 | **1** | „Au existat procese în instanță între proprietari și asociație. Cauza declarată: Lipsa documentelor și a transparenței" (AP-002). | Low (7%) | NU | A doua confirmare — potențial din AP-004..AP-010 dacă interviu detaliat. |
| P-013 | Comunicare digitală + mecanisme conforme legislației (Adunare Generală + quorum) | AP-002 | **1** | „Hotărâri importante: necesită Adunări Generale și respectarea pragului legal (quorum)" (AP-002). | Low (7%) | NU | A doua confirmare. |
| P-014 | Președinții au nevoie de protecție juridică/răspundere | AP-002 | **1** | „Litigii civile · Amenzi pentru președinte (răspundere personală)" (AP-002). | Low (7%) | NU | A doua confirmare. Candidați cu experiență lungă (AP-004 10+ ani, AP-005 7+ ani, AP-002 40+ ani deja consolidat). |

### C.2 Distribuție maturitate (după reconciliere)

| Maturity | Count | Δ vs registry actual |
|---|---|---|
| Observation (1 conf) | 9 | 0 |
| Emerging Pattern (2 conf) | 4 | 0 |
| Validated Pattern Candidate (3+ conf) | **0** | **0** |
| High Confidence Pattern (5+ conf) | 0 | 0 |
| **TOTAL** | **13** | 0 |

**Consecință metodologică cheie**: adăugarea AP-001, AP-004..AP-010 la cohortă **NU a modificat niciun număr de confirmări** — pentru că aceste 8 interviuri sunt profile snapshots fără evidence pe patterns. Statisticile din PATTERN_REGISTRY reflectă corect realitatea evidence.

---

## D. Pattern-uri cu **2 confirmări** (Emerging — necesită a treia confirmare)

Patru pattern-uri:

1. **P-002** — Succesiune președinte nestandardizată. **2 confirmări — a treia confirmare independentă este necesară.**
2. **P-003** — WhatsApp ca comunicare (cu nuanță generațională). **2 confirmări — a treia confirmare independentă este necesară.**
3. **P-004** — Mentenanță preventivă preferată. **2 confirmări — a treia confirmare independentă este necesară.**
4. **P-005** — Trasabilitate incidente absentă → risc legal. **2 confirmări — a treia confirmare independentă este necesară.**

**Notă**: toate 4 sunt susținute de AP-002 + AP-003 (aceeași pereche). Zero pattern-uri au 2 confirmări din interviuri diferite decât AP-002 + AP-003.

---

## E. Pattern-uri cu **3+ confirmări** (Validated Pattern Candidate)

**ZERO (0) pattern-uri au 3+ confirmări.**

**NEVALIDAT ÎNCĂ pentru toate cele 13 pattern-uri conform pragului metodologic Validated Pattern Candidate (≥3 confirmări independente).**

---

## F. Pattern-uri care rămân nevalidate

Toate 13 pattern-uri: **NEVALIDAT ÎNCĂ**.

Motivul unic și comun: 8/10 interviuri sunt profile-only și nu au produs evidence explicit pe niciuna din ariile obligatorii pentru contribuție la patterns.

Aceasta **nu** invalidează pattern-urile. Le lasă la stadiul actual: 9 la Observation, 4 la Emerging.

---

## G. Contradicții

Aplic regula: „diferența între respondenți nu este automat contradicție; poate indica segmentare".

### G.1 Contradicții reale identificate
**Zero (0) contradicții reale** între AP-001 → AP-010 pe evidence-ul existent.

### G.2 Nuanțe / diferențe candidate segmentare (nu contradicții)

| # | Diferență observată | Interviuri implicate | Interpretare (evidence-only) |
|---|---|---|---|
| N1 | Canal comunicare — telefon menționat primar vs. WhatsApp+Avizier only | AP-002 (telefon+WA+avizier), AP-003 (WA+avizier) | [INFERENCE] posibilă corelație cu vârsta/generația președintelui (AP-002 40+ ani exp, AP-003 ~1 an). **NU** e contradicție. Nuanță documentată deja în P-003. Requires follow-up. |
| N2 | Platformă adoptată vs. bloc mare | AP-006 (eBloc, XL 286), AP-007 (Bloc Sistem, XS 14), AP-009 (eBloc, LARGE 104) | [HYPOTHESIS falsified partial] AP-007 (bloc mic cu Bloc Sistem) contrazice ipoteza „doar blocurile mari adoptă platforme". eBloc apare la XL post-2000 ȘI large pre-1980 → multi-segment. |
| N3 | Documentație parțială (AP-003) vs. lipsă avansată (AP-002) | AP-002, AP-003 | [EVIDENCE] Ambele confirmă gap documentație. Nuanța: AP-002 este cel mai vechi bloc din pereche (1976 vs 2006) și are cel mai mare gap. NU contradicție → susține P-002 și P-011. |
| N4 | Investiții structurale (anvelopare AP-002) vs. mentenanță spații comune (AP-003 parcări/gresie/balustrade) | AP-002 (structural), AP-003 (cosmetic) | [INFERENCE] posibilă corelație cu vârsta blocului (1976 vs 2006). Structural intervention pentru bloc vechi, mentenanță pentru bloc nou. NU contradicție → segmentare posibilă. |

**Notă contradicții pentru profile-only**: AP-001, AP-004, AP-005, AP-008, AP-010 nu au evidence care să contrazică sau să susțină nimic. Silenzia de evidence ≠ contradicție.

---

## H. Competitive evidence — AP-006 (Răzvan · eBloc)

Analiză strictă evidence-only din `INTERVIEW_2026-08-14_WEST-CONECT-AP-006.md`.

### H.1 Ce EVIDENCE există
- **Foloseste** eBloc [EVIDENCE]
- Bloc XL: 286 apartamente (cel mai mare din cohortă) [EVIDENCE]
- An construcție 2019 [EVIDENCE]
- Zonă: West Conect / Iulius Mall [EVIDENCE]
- Vechime președinte: ~4 ani [EVIDENCE]

### H.2 Ce funcționalități percepe că are eBloc
**[UNKNOWN]** — zero evidence în interviu. Nu s-a chestionat.

### H.3 Ce problemă consideră deja rezolvată prin eBloc
**[UNKNOWN]** — zero evidence.

### H.4 Ce consideră că PropManage nu aduce în plus
**[UNKNOWN]** — comparația nu s-a făcut în interviu. Nu există evidence directă că respondentul a comparat cele două platforme.

### H.5 Ce NU știm încă (research gaps AP-006)
1. Ce features eBloc oferă și cum le folosește Răzvan
2. Ce features eBloc lipsesc din percepția lui Răzvan
3. Ce prețuri plătește pentru eBloc (WTP demonstrated indirect)
4. Care sunt frustrările reale cu eBloc, dacă există
5. Cum a ales eBloc (proces decizional)
6. Cine deține relația cu eBloc — el sau administratorul
7. Cine îl influențează în decizia de a schimba platforma (dacă vreodată)
8. Care sunt problemele reale în asociație (probleme, workaround, documentație, mentenanță, comunicare, furnizori, lucrări, riscuri) — zero evidence pe niciuna
9. Willingness to pay pentru orice platformă (declarat, demonstrat)
10. Nivelul de digitalizare al comunicării cu proprietarii (WhatsApp? eBloc chat? Email?)

### H.6 Întrebări obligatorii pentru follow-up AP-006
- „De cât timp folosești eBloc?"
- „Care sunt cele 3 lucruri pe care le folosești zilnic în eBloc?"
- „Care sunt cele 3 lucruri pe care ai vrea să le facă și nu le face?"
- „Cât plătește asociația pe lună/an pentru eBloc?"
- „Cine a decis să adoptați eBloc și când?"
- „Cum comunici cu proprietarii — prin eBloc sau prin WhatsApp/telefon?"
- „Când ai avut ultima problemă majoră în bloc? Cum ai gestionat-o prin eBloc?"
- „Dacă ar apărea o platformă mai bună, ce ar trebui să facă mai bine pentru a te muta?"
- „Ce plătești ca administrator asociație vs. ce beneficiu returnează eBloc proprietarilor?"

**Rezultat**: **COMPETITIVE / POSITIONING EVIDENCE = INSUFICIENT.** Zero Product Requirement derivabil.

### H.7 Notă structurală
eBloc apare la **2** interviuri (AP-006 XL 2019, AP-009 large 1976). Bloc Sistem apare la **1** interviu (AP-007 XS 2022). Total 3/10 asociații cu platformă declarată. **7/10 fără platformă declarată** — market predominant NON-virgin la nivel de așteptare, dar posibil virgin la nivel de adopție reală. **[UNKNOWN]** dacă cele 7 fără platformă declarată chiar nu folosesc nimic sau folosesc informal (Excel, WhatsApp, hârtie).

---

## I. WTP status

Regulă strictă: „ar fi util" sau „aș folosi" NU se interpretează ca willingness-to-pay.

### I.1 Distribuție WTP pe cohortă

| Interview | WTP DECLARED | WTP DEMONSTRATED | WTP UNKNOWN |
|---|---|---|---|
| AP-001 | — | — | ✓ |
| AP-002 | — | — | ✓ |
| AP-003 | — | — | ✓ |
| AP-004 | — | — | ✓ |
| AP-005 | — | — | ✓ |
| AP-006 | — | — (folosește eBloc dar preț necunoscut) | ✓ |
| AP-007 | — | — (folosește Bloc Sistem dar preț necunoscut) | ✓ |
| AP-008 | — | — | ✓ |
| AP-009 | — | — (folosește eBloc dar preț necunoscut) | ✓ |
| AP-010 | — | — | ✓ |
| **TOTAL** | **0/10** | **0/10** | **10/10** |

### I.2 Ce evidence există pe cost-related discussions

- **AP-002**: menționează 150 lei per evaluare oferta specialist ca „prohibitiv" și consideră 30-40 lei rezonabil. **Notă**: acesta este preț percepție **pentru specialist supply**, NU WTP pentru o platformă software. Nu se transformă în WTP.
- **AP-003**: menționează priorități de investiție (stingătoare, contorizare, fațadă) dacă ar exista buget suplimentar. **Notă**: acesta este buget capital pentru asociație, NU WTP pentru software. Nu se transformă în WTP.
- **AP-006, AP-007, AP-009**: folosesc deja platforme (eBloc / Bloc Sistem) — există WTP demonstrated **implicit** pentru concurenți, dar prețul plătit este [UNKNOWN]. Nu se poate cuantifica.

### I.3 WTP evidence care lipsește
1. Preț plătit pentru eBloc (AP-006, AP-009) — chiar în lei/lună sau lei/apartament/lună
2. Preț plătit pentru Bloc Sistem (AP-007)
3. Buget lunar total al asociației pentru servicii digitale
4. Cine plătește (asociația, președintele, administratorul, proprietarii individual)
5. Willingness to switch (cu ce preț ar plăti pentru PropManage vs. actual)
6. Willingness to pay declared pentru cele 7 asociații fără platformă
7. Preț de referință pe care respondenții ar considera „acceptabil"

**Concluzie**: **WTP evidence = BLOCANT ABSOLUT pentru business case**. Zero interviuri au chestionat direct. Toate viitoarele interviuri trebuie să conțină minim 3 întrebări WTP structurate.

---

## J. Research gaps

Nu suprapun gaps deja documentate în `INTERVIEW_REGISTRY.md`. Sintetizez toate gaps active identificate prin această reconciliere.

### J.1 Evidence gaps la nivel de interviu (per cohortă)

| Gap | Detaliu | Impact |
|---|---|---|
| G1 | **8/10 interviuri = profile-only** (AP-001, AP-004..AP-010 fără evidence pe probleme/workaround/docs/mentenanță/comunicare/furnizori/lucrări/riscuri/digitalizare) | **Blocant absolut** pentru orice promovare pattern |
| G2 | **Localizare precisă 9/10 UNKNOWN** | Blocant pentru cross-check Building Typology + cross-check regional |
| G3 | **Vechime președinte 4/10 UNKNOWN** (AP-001, AP-007, AP-008, AP-010) | Blocant pentru testarea corelației generație → comunicare (P-003 nuanță) |
| G4 | **Furnizori / specialist supply 9/10 UNKNOWN** (evidence parțial doar la AP-002) | Blocant pentru validarea P-010 (trust deficit) și P-008 (cost barrier) |

### J.2 Pattern-level evidence gaps

| Gap | Pattern afectat | Ce lipsește |
|---|---|---|
| G5 | P-001 (Infra aging post-2000) | 5 blocuri post-2000 în cohortă (AP-001, AP-005, AP-006, AP-007, AP-008) — toate profile-only. Zero au fost chestionate despre infrastructură tehnică. |
| G6 | P-002 (Succession) | 4 președinți cu vechime cunoscută 1-3 ani (AP-003, AP-009) și 10+ (AP-002, AP-004) — doar AP-002+AP-003 au evidence. AP-004 (10+ ani exp) este candidat natural pentru follow-up. |
| G7 | P-006 (Water metering) | Evidence exclusiv AP-003. Zero follow-up structurat pe subiect. |
| G8 | P-007 (Safety equipment) | Idem — evidence exclusiv AP-003. |
| G9 | P-008..P-014 | Evidence exclusiv AP-002. Toate 7 pattern-uri au nevoie de a doua confirmare. |

### J.3 Segmentation gaps

| Gap | Detaliu |
|---|---|
| G10 | **Interval construcție 1980-2000**: 0 clădiri în cohortă. GAP CONFIRMAT în INTERVIEW_REGISTRY. |
| G11 | **51-100 apartamente**: 0 clădiri (bucket lipsă între 40 și 104). |
| G12 | **Asociații mixte apt+casă**: 1 caz outlier (AP-008), profile-only. Guvernanță diferită neconfirmată. |
| G13 | **Asociații cu buget lunar cunoscut**: 0 din 10 (câmp `Buget lunar mediu asociație` = N/A în toate template-urile). |

### J.4 Competitor / platformă gaps

| Gap | Detaliu |
|---|---|
| G14 | eBloc feature-set percepție = [UNKNOWN] la ambele evidence-uri (AP-006, AP-009). |
| G15 | Bloc Sistem feature-set percepție = [UNKNOWN] (AP-007). |
| G16 | Zero evidence pe alte platforme concurente (Property Vista, Home365, Homerun, admin.eu, admicom.ro, etc.). |
| G17 | Cele 7 „fără platformă declarată" — [UNKNOWN] dacă folosesc informal Excel / WhatsApp / hârtie. |

### J.5 WTP gaps (rezumat)

Vezi §I.3. Toate 7 subpuncte sunt gap.

---

## K. Next interview priorities

Prioritizare strictă pe baza gaps (nu features).

### K.1 Prioritate 1 — Completare evidence la interviurile deja logate

**Justificare**: 8/10 interviuri sunt profile-only. Cel mai eficient acțiuni pentru a crește N pe fiecare pattern = follow-up detaliat pe interviuri existente, nu interviuri noi.

**Ordinea recomandată** (bazată pe potențial de contribuție la Emerging → Validated):

| Rang | Interview | De ce prioritar | Ce va confirma/infirma |
|---|---|---|---|
| 1 | **AP-006 follow-up (Răzvan · eBloc)** | Singurul competitor active user cu potențial de contribuție directă la Positioning + WTP demonstrated | eBloc feature-set, prețul plătit, motive schimbare potențial, plus ariile obligatorii comune |
| 2 | **AP-004 follow-up (Mihăilă · Negoiu 10, 1975, 40 apts, 10+ ani exp)** | Vechime președinte 10+ ani = candidat natural pentru P-002 (succession), P-011 (legal risk), P-014 (protecție) | P-002 → 3 conf (Validated Candidate); P-011 → 2 conf (Emerging); P-014 → 2 conf (Emerging) |
| 3 | **AP-009 follow-up (Sandu Pop · Mehedinți 23, 1976, 104 apts, ~3 ani, eBloc)** | eBloc user + bloc vechi + large size = combinație unică. Multi-segment competitor confirmation. | Pattern-uri legate de: docs old buildings, upgrade infrastructure, plus competitive perspective distinct de AP-006 |
| 4 | **AP-005 follow-up (Bradea · Soporului 5, 2018, 130 apts, 7+ ani)** | Bloc post-2000 large + president 7+ ani = potențial second confirmation pentru P-001 (infra aging post-2000) și P-002 | P-001 → 2 conf (Emerging); P-002 → 3 conf potențial |
| 5 | **AP-007 follow-up (Kincsö Pál · 2022, 14 apts, Bloc Sistem)** | Al doilea competitor. Contradice ipoteza „platformele = doar la blocuri mari". | Bloc Sistem feature-set + WTP + motivația adoptării la bloc mic |
| 6 | **AP-010 follow-up (Cristian · Mehedinți 17, 1976, 104 apts, 5 scări)** | Comparație directă same-context cu AP-009 → same building context, potentially different governance | Same-structural-context governance variance |
| 7 | AP-001 (Adrian Popa) și AP-008 (Paul Jeican) | Necesare pentru cohort completion, dar prioritate mai mică decât 1-6 | Cohort completeness |

### K.2 Prioritate 2 — Cazuri noi cu criterii stricte

Doar dacă follow-up-urile de la K.1 nu sunt fezabile pe termen scurt. Criteriile pentru un AP-011+:

**Criteriu obligatoriu 1**: bloc **construit 1980-2000** (închide G10, interval cu 0 evidence).
**Criteriu obligatoriu 2**: chestionare WTP structurată (declarat + demonstrat + explicit despre plata pentru eBloc/Bloc Sistem/alte platforme).
**Criteriu obligatoriu 3**: cele 12 arii obligatorii chestionate integral.

### K.3 Prioritate 3 — WTP evidence structurat

**Toate viitoarele interviuri (follow-up sau nou)** trebuie să conțină:
- „Cât plătește asociația pe lună pentru comunicare / administrare digitală / soft?"
- „Cine plătește (asociația, președintele, administratorul, proprietarii)?"
- „Care este prețul maxim rezonabil pentru astfel de soluție (lei/apartament/lună)?"
- „Dacă platforma existentă (dacă există) ar dispărea mâine, ai plăti cu 20% mai mult sau ai renunța?"

### K.4 Prioritate 4 — Templat de follow-up

Recomand actualizarea **conceptuală** a `INTERVIEW_TEMPLATE.md` (nu forced modification — sugestie pentru fondator) cu:
- Secțiune obligatorie WTP (declared / demonstrated / unknown)
- Secțiune obligatorie Competitor / Platformă (chiar și „nu folosesc nimic" este evidence)
- Secțiune Furnizori / Specialist Supply

**NU se implementează în acest sprint** — este propunere metodologică pentru fondator.

---

## L. Typology research implications — evidence-based only

Regulă strictă: nu se pornește Pilot Typology. Building Typology Foundation Audit v1.0 rămâne neschimbat. Această secțiune verifică doar dacă evidence-ul existent susține sau infirmă vocabularul canonic al auditului.

### L.1 Evidence care susține conceptul de Typology (fără implementare)

| Observație | Interpretare | Status |
|---|---|---|
| AP-009 și AP-010 = același an (1976), aceeași dimensiune (104 apts), aceeași stradă | [EVIDENCE] două clădiri **candidat** aceeași tipologie/variant, dar guvernanță potențial diferită | Susține separarea `TYPOLOGY ≠ BUILDING INSTANCE` din audit §3.3 |
| AP-002 (1976, 20 apts) vs. AP-004 (1975, 40 apts) vs. AP-009/010 (1976, 104 apts) | [EVIDENCE] posibil aceeași **Typology Family** (post-1975), dar dimensiuni diferite → **Typology Variants** | Susține conceptul de Family + Variant din audit §3.4-3.5 |
| AP-003 (2006, 13) vs. AP-001 (2019, 16) vs. AP-007 (2022, 14) | [EVIDENCE] blocuri mici post-2000, ani diferiți → potențial Family „post-2000 rezidențial mic" | Susține conceptul de Family |
| AP-006 (2019, 286) — outlier XL | [EVIDENCE] potențial Family diferită de „post-2000 rezidențial mic" | Susține varianță în Family post-2000 |

### L.2 Evidence care nu susține niciun pas implementațional

- Zero evidence Reference Data auditat.
- Zero evidence Official Documentation colectat pentru vreo clădire.
- Adresă precisă lipsește 9/10.
- Reference Plans, Reference Apartments, Reference 3D = 0% acoperire.

### L.3 Concluzie
Vocabularul canonic din Building Typology Foundation Audit v1.0 este **consistent** cu evidence-ul existent — dar evidence-ul rămâne **insuficient** pentru orice pas implementațional. Decision Gate `A. NOT READY` rămâne valabil.

**Nici o modificare** la Building Typology Foundation Audit v1.0.

---

## M. Metodologie — confirmări finale (contractuale)

- **NEW INTERVIEWS**: **0**
- **NEW FEATURES**: **0**
- **BLUEPRINT CHANGE**: **NO**
- **ROADMAP CHANGE**: **NO**
- **BACKEND CHANGE**: **NO**
- **FRONTEND CHANGE**: **NO**
- **DATABASE CHANGE**: **NO**
- **API CHANGE**: **NO**
- **TYPOLOGY PILOT**: **NOT STARTED**
- **METHODOLOGY CHANGE**: **NO**
- **HARTABLOCURI IMPORT**: **NOT PERFORMED**
- **BUILDING TYPOLOGY FOUNDATION AUDIT v1.0**: **UNCHANGED**

Pattern promotion: **0 patterns promoted**. Pragurile metodologice rămân intacte (1 → 2 → 3+ → 5+).

Pipeline conservat:
```
Interview → Observation → Emerging Pattern → Validated Pattern Candidate → Research Report → Blueprint → Audit → Roadmap → Pilot → Build
```

---

## N. Deliverable Log

Acest sprint produce **un singur artefact**:
- `/app/memory/audits/RESEARCH_RECONCILIATION_AP001_AP010_v1.0.md` (acest document)

Nu se creează alte fișiere. Nu se modifică `INTERVIEW_REGISTRY.md`. Nu se modifică `PATTERN_REGISTRY.md`. Nu se modifică pattern files `/app/memory/audits/PATTERN_*.md`. Nu se atinge cod. Nu se modifică `PROPMANAGE_PRESIDENT_RESEARCH_COHORT_v1.0.md`.

---

**End of RESEARCH_RECONCILIATION_AP001_AP010_v1.0.**
