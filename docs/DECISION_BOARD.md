# DECISION_BOARD.md — PropManage
**Scop:** Product Owner-ul decide. Nimic din acest document nu se implementează fără aprobare explicită per decizie.
**Sursă:** MASTER_PRODUCT_AUDIT_v2.md · Faza 11 (Product Conflicts) + Decision Log
**Data:** Iunie 2026 · **Status:** ÎN AȘTEPTAREA DECIZIILOR OWNER-ULUI

Legendă impact: 🟢 pozitiv · 🟡 neutru/mixt · 🔴 negativ · Cost estimativ în zile-agent de dezvoltare (include testare).

---

## D1 — Consolidarea Admin-ului (106 pagini) vs. Status Quo

**Problema identificată:** Admin-ul are 106 pagini/componente distribuite în 10+ secțiuni de sidebar. Un om nou (angajat, franchisee) nu poate învăța suprafața. Chiar owner-ul navighează predominant prin căutare, nu prin meniu.

**Context:** Fiecare sprint a adăugat 2-4 dashboard-uri noi (Command Center, Business Health, CEO Dashboard, Marketplace Intel, Audit Sentinel, XOS ×4, Self-Driving...). Individual toate sunt justificate; cumulat, încalcă Legea lui Hick exact acolo unde s-a cerut respectarea ei.

**De ce există conflict:** Puterea funcțională (fiecare capacitate are pagina ei, deep-link-abilă) intră în coliziune cu operabilitatea (nimeni nu poate ține în minte 106 destinații). Ambele sunt valori legitime.

### Opțiunea A — Consolidare în 5-7 hub-uri
(Operations · Growth · Intelligence · Experience · System · Finance · People)
**Avantaje:** cognitive load ↓↓; onboarding franchisee de la săptămâni la ore; sidebar-ul redevine hartă mentală; forțează curățenia (paginile moarte ies la iveală); aliniat cu XOS (hub = suprafață configurabilă).
**Dezavantaje:** 2-3 săptămâni fără feature nou vizibil; risc de regresii pe rutare/deep-links; unele fluxuri de nișă devin cu 1 click mai adânci; efort de re-învățare pentru owner (obișnuit cu structura actuală).

### Opțiunea B — Status quo + ⌘K ca interfață primară
**Avantaje:** zero efort; zero risc de regresie; toată puterea rămâne la un search distanță; nimic de re-învățat.
**Dezavantaje:** entropia crește cu fiecare sprint (peste 1 an: 150+ pagini); produsul devine operabil doar de fondator; franciza moștenește haosul; search-ul presupune că știi CE cauți — nu ajută la descoperire.

### Impact
| Dimensiune | Opțiunea A | Opțiunea B |
|---|---|---|
| Product Blueprint | 🟢 respectă §1.5.4 (spații care generează acțiuni) | 🔴 derivă continuă |
| Business | 🟡 pauză de feature-uri 2-3 săpt. | 🟡 zero pe termen scurt, 🔴 lung |
| Experience OS | 🟢 hub-urile devin suprafețe XOS | 🔴 XOS rămâne periferic |
| Marketplace | 🟡 neutru | 🟡 neutru |
| Franchise | 🟢 admin predabil = francizabil | 🔴 blocant la predare |
| UX | 🟢 Hick/Miller respectate | 🔴 se degradează |
| AI | 🟡 neutru | 🟡 neutru |
| Knowledge Graph | 🟡 neutru | 🟡 neutru |
| Scalabilitate | 🟢 structura suportă creștere | 🔴 creștere liniară a haosului |
| Mentenanță | 🟢 după consolidare ↓30% | 🔴 crește cu fiecare pagină |

**Complexitate:** MARE (L) · **Risc:** MEDIU (rutare/deep-links) · **Cost estimativ:** 10-15 zile-agent, eșalonabil în 3 valuri
**Recomandarea AI:** ✅ **Opțiunea A**, eșalonată (întâi regrupare sidebar fără mutare de cod = 2 zile; apoi fuziuni de pagini val cu val).
**Alternativa conservatoare:** B + moratoriu pe pagini admin noi (orice capacitate nouă intră într-un hub existent).

---

## D2 — Design System Gate obligatoriu vs. Viteză de livrare

**Problema identificată:** 3 sisteme de butoane, 2 surse pentru aceeași culoare (#d4ff3a hardcodat în ~40 fișiere vs `--pm-primary`), dark hardcodat pe 21 pagini (reparat prin CSS override = paliativ), ≥4 stiluri de card.

**Context:** Paginile se nasc mai repede decât se tokenizează. Palette Cascade (motorul de white-label) există și funcționează, dar re-temează doar ~60% din suprafață.

**De ce există conflict:** Viteza de livrare AI-driven (avantajul competitiv al dezvoltării) vs. coerența vizuală (condiția white-label). Fiecare gate încetinește; fiecare scurtătură adâncește datoria.

### Opțiunea A — Gate strict: nicio pagină nouă fără tokens + componente din registry
**Avantaje:** datoria încetează să crească; white-label devine real (schimbi 5 culori → tot produsul se re-temează); consistență automată; QA vizual mai simplu.
**Dezavantaje:** fiecare livrare +10-15% timp; necesită definirea clară a registry-ului întâi (3-4 zile); frustrant la prototipare rapidă.

### Opțiunea B — Livrezi rapid, tokenizezi în valuri retroactive
**Avantaje:** viteză maximă pe feature-uri; curățenia se face când există timp.
**Dezavantaje:** „când există timp" = rar; fiecare val de curățenie costă mai mult decât precedentul (s-a văzut: fix-ul light-mode a cerut override-uri CSS globale în loc de 1 linie per pagină); white-label rămâne promisiune.

### Impact
| Dimensiune | A | B |
|---|---|---|
| Product Blueprint | 🟢 | 🔴 anti-pattern feature factory |
| Business | 🟡 -10-15% viteză | 🟢 scurt / 🔴 lung |
| Experience OS | 🟢 Theme Manager real | 🔴 |
| Marketplace | 🟡 | 🟡 |
| Franchise | 🟢 condiție white-label | 🔴 blocant |
| UX | 🟢 consistență | 🔴 |
| AI | 🟡 | 🟡 |
| Knowledge Graph | 🟡 | 🟡 |
| Scalabilitate | 🟢 | 🔴 |
| Mentenanță | 🟢 un singur loc de schimbat | 🔴 |

**Complexitate:** MEDIE (gate = proces; sweep-ul retroactiv = MARE) · **Risc:** SCĂZUT (gate) / MEDIU (sweep) · **Cost:** gate 0 zile (regulă) + sweep tokens 5-8 zile
**Recomandarea AI:** ✅ **Opțiunea A** — gate imediat (cost zero) + sweep-ul #d4ff3a→tokens ca task de consolidare.
**Alternativa conservatoare:** gate doar pe pagini publice (unde contează white-label), admin rămâne relaxat.

---

## D3 — Secvențiere: Cash (Marketplace) vs. Șanț competitiv (Date)

**Problema identificată:** Venitul pe termen scurt vine din marketplace (lichiditate: doar 16/372 specialiști verificați = 4%); identitatea și apărarea pe termen lung vin din date (twin + health + istoric). Resursele nu ajung pentru ambele simultan.

**Context:** Blueprint-ul definește datele ca produs și marketplace-ul ca și consecință. Realitatea financiară cere cashflow. Nu e conflict de viziune, ci de ORDINE.

**De ce există conflict:** Fiecare lună investită în date fără venit arde pistă; fiecare lună investită doar în marketplace apropie produsul de „încă un OLX de servicii" (anti-viziunea explicită).

### Opțiunea A — Focus 100% lichiditate (recrutare specialiști, SEO servicii, funnel leads)
**Avantaje:** cashflow; validare de piață; masa critică activează buclele (reviews, escrow, gamification devin utile); datele de tranzacții REALE alimentează Observatory.
**Dezavantaje:** riscă identitatea (6-12 luni doar marketplace = marketplace); competitorii de date nu dorm; amână Property Copilot (diferențiatorul).

### Opțiunea B — Focus șanț (property_id linkage, Knowledge Graph, Property Copilot)
**Avantaje:** avantaj necopiabil (3 ani de istoric structurat); primul „casa se întreține singură" real de pe piață.
**Dezavantaje:** arde bani fără venit imediat; datele fără utilizatori = șanț în jurul unei cetăți goale.

### Impact
| Dimensiune | A | B |
|---|---|---|
| Product Blueprint | 🟡 permis ca etapă | 🟢 litera viziunii |
| Business | 🟢 venit acum | 🔴 venit amânat |
| Experience OS | 🟡 | 🟡 |
| Marketplace | 🟢 rezolvă blocajul #1 (supply) | 🔴 stagnează |
| Franchise | 🟢 franciza se vinde pe cifre, nu pe viziune | 🟡 |
| UX | 🟡 | 🟢 Copilot = wow |
| AI | 🟡 | 🟢 KG deblochează AI real |
| Knowledge Graph | 🟡 tranzacțiile produc date | 🟢 direct |
| Scalabilitate | 🟡 | 🟢 |
| Mentenanță | 🟡 | 🟡 |

**Complexitate:** A = MEDIE · B = MARE · **Risc:** A = identitate · B = pistă financiară · **Cost:** A: 5-8 zile · B: 12-20 zile
**Recomandarea AI:** ✅ **A întâi, B imediat după** (exact Roadmap-ul propus: Faza B → Faza C), CU convenția property_id activă din prima zi (costă ~0 pe inserturi noi și pregătește B).
**Alternativa conservatoare:** 70% A / 30% B în paralel (mai lent pe ambele, dar fără pariu total).

---

## D4 — Extinderea Auto-Approve (Autonomie 90%+) vs. Răspundere

**Problema identificată:** Self-Driving aprobă azi doar acțiuni din whitelist low-risk. HDI-ul se plafonează (~85) pentru că acțiunile cu impact (bani, dispute, KYC) cer om.

**Context:** Există deja: whitelist configurabil, rollback-safe pe eșec, ledger complet. Escrow și dispute au implicații legale reale.

**De ce există conflict:** Fiecare procent de autonomie peste ~85 se cumpără cu risc pe acțiuni tot mai puțin reversibile. O singură eroare pe bani reali distruge încrederea câștigată de 1.000 de automatizări corecte.

### Opțiunea A — Extinzi auto-approve la tot ce e tehnic reversibil
**Avantaje:** HDI 90+; owner-ul aproape complet eliberat; demonstrația supremă a produsului („platforma se conduce singură").
**Dezavantaje:** definiția „reversibil" e alunecoasă (un email greșit trimis nu se retrage); expunere legală pe KYC/plăți; auditul devine post-factum.

### Opțiunea B — Pragul actual + creșterea VOLUMULUI de acțiuni mici automate
**Avantaje:** risc constant; 90% atins prin lărgirea bazei (mai multe tipuri de acțiuni mărunte), nu prin adâncirea riscului; fiecare automatizare nouă e izolat testabilă.
**Dezavantaje:** HDI crește mai lent; unele fricțiuni umane rămân (aprobare dispute, KYC final).

### Impact
| Dimensiune | A | B |
|---|---|---|
| Product Blueprint | 🟡 §1.5.3 spune „execută unde are permisiuni" | 🟢 aceeași literă, prudent |
| Business | 🟢 cost operare ↓ | 🟢 cost operare ↓ mai lent |
| Experience OS | 🟡 | 🟡 |
| Marketplace | 🔴 o eroare pe escrow = încredere pierdută | 🟢 |
| Franchise | 🟡 franchisee-ul vrea control, nu magie | 🟢 |
| UX | 🟡 | 🟡 |
| AI | 🟢 | 🟢 |
| Knowledge Graph | 🟡 | 🟡 |
| Scalabilitate | 🟢 | 🟢 |
| Mentenanță | 🔴 incidente rare dar grave | 🟢 |

**Complexitate:** A = MEDIE · B = MICĂ/continuă · **Risc:** A = MARE (legal/reputațional) · B = SCĂZUT · **Cost:** A: 3-5 zile + asigurare juridică · B: 1-2 zile per automatizare nouă
**Recomandarea AI:** ✅ **Opțiunea B** — ireversibil ≠ automatizabil. 90% prin volum, nu prin miză.
**Alternativa conservatoare:** B este deja varianta conservatoare; ultra-conservator = îngheț la whitelist-ul actual.

---

## D5 — tenant_id acum (retrofit timpuriu) vs. la primul contract de franciză

**Problema identificată:** 217 colecții fără `tenant_id`/`city_id` pe entitățile core. Franciza cere izolare pe oraș. Retrofit-ul devine exponențial mai scump cu fiecare colecție nouă.

**Context:** Există deja un pattern extensibil (`middleware_scope` pe admin RBAC). Nu există încă niciun contract de franciză semnat.

**De ce există conflict:** Munca de multi-tenancy e invizibilă pentru utilizatori (nu vinde nimic azi) dar definește viteza de reacție la primul contract (2-3 luni de refactor dacă nu e pregătită).

### Opțiunea A — Retrofit acum (tenant_id peste tot + scoping middleware)
**Avantaje:** costul minim posibil (crește cu fiecare săptămână); primul contract se onorează în zile, nu luni; forțează disciplina pe toate inserturile noi.
**Dezavantaje:** 10-15 zile de muncă fără niciun beneficiu vizibil; risc de regresii pe query-uri (fiecare find() trebuie scoped); poate fi prematur dacă modelul de franciză se schimbă.

### Opțiunea B — Amâni integral până la primul contract semnat
**Avantaje:** efort just-in-time; zero munca speculativă; modelul de franciză va fi cunoscut exact.
**Dezavantaje:** primul contract așteaptă 2-3 luni de refactor (risc de pierdere a contractului); între timp fiecare colecție nouă adâncește groapa.

### Opțiunea C (hibrid identificat de board) — „A-light"
Convenție OBLIGATORIE: orice colecție/insert NOU primește `tenant_id: "main"` de azi + planul de migrare scris; migrarea efectivă la contract.
**Avantaje:** cost ~zero pe flux nou; oprește adâncirea gropii; migrarea rămasă e finită și cunoscută. **Dezavantaje:** groapa existentă rămâne până la contract.

### Impact (A vs B vs C)
| Dimensiune | A | B | C |
|---|---|---|---|
| Product Blueprint | 🟢 | 🟡 | 🟢 |
| Business | 🔴 2 săpt. invizibile | 🟢 azi / 🔴 la contract | 🟢 |
| Experience OS | 🟡 | 🟡 | 🟡 |
| Marketplace | 🟡 | 🟡 | 🟡 |
| Franchise | 🟢🟢 | 🔴 | 🟢 |
| UX | 🟡 | 🟡 | 🟡 |
| AI | 🟡 reguli AI per tenant devin posibile | 🔴 | 🟡 |
| Knowledge Graph | 🟢 scoping curat | 🟡 | 🟢 |
| Scalabilitate | 🟢🟢 | 🔴 | 🟢 |
| Mentenanță | 🟡 inițial ↑, apoi ↓ | 🔴 la retrofit | 🟢 |

**Complexitate:** A = XL · B = 0 azi/XL mâine · C = S · **Risc:** A = MEDIU (regresii query) · B = MARE (business) · C = SCĂZUT · **Cost:** A: 10-15 zile · B: 0 → 20-30 zile sub presiune · C: 1 zi (convenție+plan) + migrare la contract
**Recomandarea AI:** ✅ **Opțiunea C** (A-light).
**Alternativa conservatoare:** B (dar board-ul o consideră cea mai scumpă pe termen lung).

---

## D6 — XOS Widget Registry obligatoriu vs. widget-uri hardcodate rapide

**Problema identificată:** E mai rapid să scrii un panou React nou decât să-l înregistrezi ca widget XOS. Dovadă concretă: SelfDrivingPanel (livrat recent) e hardcodat în AutonomyEnginePage, nu e widget în registru.

**Context:** XOS Layout Builder funcționează pe registrul `client_home` (5 widget-uri). Dacă widget-urile noi îl ocolesc, builderul rămâne un demo pe o singură suprafață.

**De ce există conflict:** Din nou viteză vs. arhitectură — dar aici mizele sunt existențiale pentru XOS: un builder pe care nimeni nu-l alimentează moare.

### Opțiunea A — Regulă: orice widget/panou nou de dashboard intră prin registrul XOS
**Avantaje:** builderul devine real și crește organic; franciza primește configurabilitate gratis; fiecare widget e automat reordonabil/ascundibil per rol.
**Dezavantaje:** +0,5-1 zi per widget (definire registru, suprafață, props serializabile); unele panouri complexe (cu state greu) se pretează greu la registru.

### Opțiunea B — Hardcodezi și migrezi „mai târziu"
**Avantaje:** viteză maximă. **Dezavantaje:** „mai târziu" = niciodată (istoric dovedit); XOS rămâne la 5 widget-uri; datoria de migrare crește.

### Impact
| Dimensiune | A | B |
|---|---|---|
| Product Blueprint | 🟢 | 🔴 |
| Business | 🟡 ușor mai lent | 🟢 scurt / 🔴 lung |
| Experience OS | 🟢🟢 condiție de existență | 🔴 XOS moare |
| Marketplace | 🟡 | 🟡 |
| Franchise | 🟢 | 🔴 |
| UX | 🟢 consistență | 🟡 |
| AI | 🟢 AI Experience Optimizer va avea pe ce opera | 🔴 |
| Knowledge Graph | 🟡 | 🟡 |
| Scalabilitate | 🟢 | 🔴 |
| Mentenanță | 🟢 | 🔴 |

**Complexitate:** MICĂ (regulă) + MEDIE (extindere registru la 2-3 suprafețe) · **Risc:** SCĂZUT · **Cost:** regulă 0 + infrastructura multi-suprafață 3-5 zile
**Recomandarea AI:** ✅ **Opțiunea A**, cu excepție documentată pentru panourile de administrare pură (ex: Menu Manager însuși nu trebuie să fie widget).
**Alternativa conservatoare:** A doar pentru dashboard-urile utilizatorilor finali (client/specialist), admin exceptat.

---

## D7 — Community & Token Economy: pivot, îngheț sau sunset

**Problema identificată:** Două module complet construite care nu participă la bucla de date (Blueprint §1.5.2): Community (forum generic) și Token Economy/Gamification (mecanică fără lichiditate care s-o alimenteze).

**Context:** Ambele au fost construite devreme, pe ipoteza unei mase de utilizatori care încă nu există (16 specialiști verificați, sute de utilizatori, nu mii).

**De ce există conflict:** Cost de mentenanță și suprafață UX ocupată ACUM vs. valoare potențială VIITOARE. Ștergerea pare pierdere (sunk cost); păstrarea costă atenție și întreținere.

### Opțiunea A — Pivot (re-ancorare la proprietăți)
Community → „întrebări despre casa mea" legate de Twin/Health; Tokens → sink-uri reale (reduceri la servicii, boost vizibilitate specialist).
**Avantaje:** modulele intră în buclă; investiția existentă se valorifică. **Dezavantaje:** efort nou (5-8 zile) pe module nedovedite; poate fi tot prematur.

### Opțiunea B — Îngheț (nimic nou, re-evaluare la 1.000 utilizatori activi)
**Avantaje:** zero efort; opțiunile rămân deschise; atenția merge pe lichiditate. **Dezavantaje:** module vizibile dar moarte pot afecta percepția („oraș fantomă"); codul îmbătrânește.

### Opțiunea C — Sunset (ascundere din UI, cod păstrat)
**Avantaje:** UX curat; -2 destinații din meniu; reactivabil oricând. **Dezavantaje:** pare regres; utilizatorii existenți (dacă sunt) pierd funcția.

### Impact (A/B/C)
| Dimensiune | A | B | C |
|---|---|---|---|
| Product Blueprint | 🟢 intră în buclă | 🟡 | 🟢 anti-feature-factory |
| Business | 🟡 | 🟢 focus | 🟢 focus |
| Experience OS | 🟡 | 🟡 | 🟢 mai puține suprafețe |
| Marketplace | 🟢 tokens ca boost | 🟡 | 🟡 |
| Franchise | 🟡 | 🟡 | 🟢 mai puțin de predat |
| UX | 🟡 | 🔴 oraș fantomă | 🟢 |
| AI | 🟡 | 🟡 | 🟡 |
| Knowledge Graph | 🟢 (varianta A la community) | 🟡 | 🟡 |
| Scalabilitate | 🟡 | 🟡 | 🟢 |
| Mentenanță | 🔴 crește | 🟡 | 🟢 scade |

**Complexitate:** A = MEDIE · B = 0 · C = MICĂ · **Risc:** toate SCĂZUT · **Cost:** A: 5-8 zile · B: 0 · C: 0,5 zile
**Recomandarea AI:** ✅ **B pentru Token Economy** (îngheț + re-evaluare la 1.000 utilizatori) și **C pentru Community** (ascundere din meniu prin Menu Manager — reversibil în 30 secunde, fără cod).
**Alternativa conservatoare:** B pentru ambele.

---

# TABEL COMPARATIV FINAL

| ID | Decizie | 🤖 Recomandarea AI | 🛡️ Alternativa conservatoare | Cost rec. AI | Risc rec. AI | Blocant pt. franciză? |
|---|---|---|---|---|---|---|
| **D1** | Consolidare admin | **A — hub-uri, eșalonat** | B + moratoriu pagini noi | 10-15 z (3 valuri) | MEDIU | DA (predabilitate) |
| **D2** | Design System gate | **A — gate imediat + sweep tokens** | Gate doar pe public | 0 + 5-8 z sweep | SCĂZUT | DA (white-label) |
| **D3** | Cash vs Date | **A apoi B (Faza B→C din roadmap)** | 70/30 în paralel | 5-8 z (A) | identitate (gestionabil) | Indirect |
| **D4** | Auto-approve extins | **B — volum, nu miză** | B (identică) | 1-2 z/automatizare | SCĂZUT | NU |
| **D5** | tenant_id | **C — A-light (convenție acum, migrare la contract)** | B (amânare totală) | 1 z + plan | SCĂZUT | DA (definițional) |
| **D6** | XOS registry | **A — obligatoriu cu excepții documentate** | A doar pt. useri finali | 0 + 3-5 z infra | SCĂZUT | DA (configurabilitate) |
| **D7** | Community/Tokens | **B (tokens) + C (community, via Menu Manager)** | B pentru ambele | 0,5 z | SCĂZUT | NU |

**Observația board-ului asupra întregului pachet:** D2, D5-C, D6 și D7 au cost aproape zero și risc scăzut — sunt „semnături", nu proiecte. D1 și D3 sunt singurele care consumă sprinturi întregi. Dacă se aprobă pachetul recomandat integral, el se mapează natural pe planul de sprinturi propus de owner pentru Platform Core Initiative:

```
Sprint 1 · Experience OS Foundation        → activează D6 (registry) + D2 (gate)
Sprint 2 · Consolidare Config/Content/AI/Leads → pregătește D1 (primul val)
Sprint 3 · Tenant Foundation               → execută D5-C (convenție + plan, fără migrare)
Sprint 4 · Knowledge Graph + Governance    → property_id linkage + registrul platformei
Sprint 5 · Experience Configuration Center → editorul vizual (doar după 1-4)
(D3 rulează transversal: Quick Wins de lichiditate se pot strecura între sprinturi dacă owner-ul decide)
(D4 și D7 = decizii de politică, se aplică în orice sprint cu cost minim)
```

---
# FORMULAR DE DECIZIE (completat de Product Owner — 11 Iunie 2026)
| ID | Decizia mea (A/B/C) | Observații |
|---|---|---|
| D1 | ✅ A | Consolidare admin în hub-uri, eșalonat |
| D2 | ✅ A | Design System gate imediat + sweep tokens la consolidare |
| D3 | ✅ A | Cash întâi (Faza B), apoi Date (Faza C) — cu convenția property_id activă |
| D4 | ✅ B | Autonomie prin volum, nu prin miză; whitelist doar reversibile |
| D5 | ✅ C | A-light: tenant_id pe inserturi noi + plan; migrare la primul contract |
| D6 | ✅ A | XOS Widget Registry obligatoriu, cu excepții documentate pt. admin pur |
| D7 | ✅ B+C | Tokens: îngheț (re-eval la 1.000 useri) · Community: ascundere via Menu Manager |

**Status: DECIZIILE SUNT RATIFICATE. Implementarea începe cu Sprint 1 — Experience OS Foundation.**
