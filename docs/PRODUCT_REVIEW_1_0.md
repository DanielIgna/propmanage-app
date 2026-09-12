# AI PRODUCT REVIEW 1.0 — PropManage
**Autor:** AI Chief Product Officer · **Data:** 27 Iunie 2026 · **Clasa dovezilor (D161):** Measured unde e specificat, Estimated/Generated în rest
**Scop:** Evaluarea PRODUSULUI ÎNTREG (nu a sprinturilor individuale), după închiderea CX-1 → CX-3.

---

## 1. Executive Summary

PropManage a trecut, în trei sprinturi CX, de la un „Enterprise OS impresionant pe dinăuntru, dar greu de vândut pe dinafară" la un **produs cu o poveste de client completă și verificabilă**: *casa ta primește memorie (Document Vault), un profil tehnic viu (Property DNA) și o identitate publică de încredere (Pașaportul Casei)*.

**Cele 3 adevăruri esențiale ale acestui review:**
1. **Produsul are acum un motor de achiziție organică** — fiecare pașaport partajat e un asset viral cu CTA spre register. Acesta e primul feature din istoria platformei care aduce utilizatori FĂRĂ buget de marketing.
2. **Bucla de valoare este completă dar nevalidată de piață** — 0 clienți reali plătitori prin Stripe (blocat extern), 450 RON venit real dintr-o singură plată manuală. Tot ce știm despre product-market fit e ipoteză, nu măsurătoare.
3. **Cel mai mare risc nu mai e produsul, ci absența contactului cu piața.** Fiecare săptămână de dezvoltare fără utilizatori reali crește riscul de a construi perfect lucrul greșit.

**Scor maturitate produs: 62/100** (de la ~45/100 la EO-005A). **Recomandare CEO: GO-LIVE GATE înainte de CX-4** (detalii §23).

---

## 2. Current Product Vision

**„Cartea de service a casei tale."** Fiecare proprietate are: memorie (documente), profil tehnic (DNA + Digital Twin), dovezi (lucrări cu plată protejată, garanții, audituri) și identitate publică (Pașaportul cu QR). În jurul acestei cărți: un marketplace de specialiști verificați și, în viitor, transferul integral al istoriei la vânzare.

Viziunea e coerentă și diferențiată — niciun competitor RO nu leagă documentele + istoricul verificat + marketplace + profil public de încredere într-un singur obiect („casa"). Constituția produsului (Property DNA = Single Source of Truth) este respectată de la CX-2 încoace.

## 3. Customer Value (proprietari)

| Valoare | Stare | Dovadă |
|---|---|---|
| Onboarding zero-fricțiune (register → proprietate → primul document în ~2 min) | ✅ LIVRAT | CX-1/CX-2, re-audit 90–92/100 pe tot funnel-ul |
| „Casa ta are memorie" — vault permanent, istoric imutabil, versiuni | ✅ LIVRAT | CX-2, 12/12 teste |
| Scoruri care ghidează („Property Completeness" cu next-step + expected gain) | ✅ LIVRAT | 14 semnale reale |
| Identitate publică la vânzare/închiriere (Pașaport + QR + trust score) | ✅ LIVRAT | CX-3, 21/21 teste, security 100% |
| Mentenanță proactivă (calendar, remindere) | ⛔ ABSENT | CX-4 planificat |
| Transfer al istoriei la vânzare | ⛔ ABSENT | 0 linii de cod — promisiune constituțională neonorată |

**Verdict:** valoarea de *arhivare + dovadă* e completă; valoarea de *recurență* (motivul să revii lunar) încă lipsește. Fără CX-4, produsul riscă utilizare de tip „set and forget".

## 4. Specialist Value

- ✅ Funnel de înscriere refăcut (CX-1: `/devino-specialist` cu temă reparată, CTA clar), follow-up automat email/SMS-stub, lead-uri cu plată per lead (45 RON), escrow, badge-uri.
- 🟡 Dashboard specialist scorat **75/100** la auditul de conversie — sub gate-ul 90, exclus explicit din scope CX-1 (planificat CX-5).
- ⛔ Specialistul nu beneficiază încă de Pașaport/DNA: lucrările lui apar în istoricul casei, dar el nu are un „profil de dovezi" echivalent (portofoliu verificat = feature de retenție pentru supply).

**Verdict:** partea de cerere (owners) a fost modernizată 3 sprinturi la rând; partea de ofertă (specialiști) a rămas o generație în urmă. Un marketplace dezechilibrat se golește pe partea neglijată.

## 5. Marketplace Value

- ✅ Lanțul cerere→match→escrow→confirmare→review este cel mai complet flux din platformă (Experience Architecture: „singurul lanț aproape complet").
- ✅ Lucrările confirmate alimentează REAL Trust Score-ul pașaportului („Lucrări cu dovadă" +20) — marketplace-ul și cartea casei se întăresc reciproc. Acesta e cel mai valoros efect de compunere din produs.
- 🟡 Matching-ul e funcțional dar simplu; Gap Records + assign manual în Operations Center acoperă golurile.
- ⛔ Zero tranzacții reale (Stripe LIVE blocat).

## 6. Digital Twin Maturity — **58/100** (de la 45)

| Subsistem | Stare |
|---|---|
| Property DNA (atribute + capabilities) | ✅ real, documents/maintenance reparate în CX-2 |
| Document Vault | ✅ real (Object Storage, metadate D015, versiuni, istoric imutabil) |
| Twin operator (validare structură) | ✅ funcțional, alimentează trust score |
| **Fragmentarea celor 4 sisteme twin (G2)** | ⛔ NEREZOLVAT — properties/DNA · twins operator · digital_twin_projects Pro · hh_* rămân separate; House Health cere încă proiect DT Pro, nu twin-ul validat |
| Sensors / IoT | ⛔ absent (corect amânat) |
| model_url 3D | ⛔ placeholder |

**Cel mai urgent din zona twin:** G2 (unificare + un singur gating) — datorie de arhitectură care va scumpi fiecare feature viitor construit deasupra.

## 7. Property DNA Maturity — **70/100**

Capabilities REALE (documents, maintenance, works, warranties), timeline de evenimente funcțional, completeness score cu 14 semnale, atribute declarate cu proveniență. Lipsesc: îmbogățire automată din documente (OCR/AI extraction — azi totul e introdus manual), sensors, și consumul DNA-ului de către House Health (vezi G2).

## 8. Trust Architecture — **78/100**

- ✅ Trust Score public 100% verificabil, cu explicații per factor (nimic declarativ) — aliniat Truth Engine D161.
- ✅ Escrow + plăți protejate + specialiști verificați + istoric imutabil + provenance pe documente (declared vs documented).
- ✅ Security validată 100% pe suprafața publică nouă (zero scurgeri PII, privacy server-side).
- 🟡 „Verificat de platformă" e azi în practică echivalent cu „adăugat de specialist" — nu există încă un flux formal de verificare umană/audit plătit LIVE.
- ⛔ Fără rate limiting pe endpoint-urile publice (TD-07) — risc de scraping pe pașapoarte.

## 9. UX/CX Scores (Measured — audituri cu capturi)

| Suprafață | Scor | Sursă |
|---|---|---|
| Landing + funnel register | 90–92 | CONVERSION_AUDIT re-audit CX-1 |
| First-run client + HeroDoc „Pasul 2 din 3" | 92 | CX2_EXPERIENCE_AUDIT |
| Document Vault (upload/căutare/detaliu) | ≥90 | CX2_EXPERIENCE_AUDIT |
| Pașaport public desktop/mobile | 92/92 | CX3_EXPERIENCE_AUDIT |
| Dashboard specialist | **75** | în afara scope-ului CX-1→3, țintă CX-5 |
| Admin/Enterprise OS | n/a | uz intern, nu intră în gate |

## 10. Product Strengths
1. **Obiect de produs unic:** „cartea casei" — greu de copiat pentru că cere marketplace + escrow + storage + scoruri simultan.
2. **Efect de compunere:** fiecare lucrare/document crește trust score-ul → pașaportul devine mai valoros → mai multe share-uri → mai mulți owneri.
3. **Onestitate structurală:** toate scorurile derivă din dovezi; niciun număr fabricat public (verificat și reparat în CX-1).
4. **Viteză de execuție cu calitate:** 3 sprinturi CX în serie, toate cu gate ≥90 și teste 100%.
5. **Fundament operațional matur:** Operations Center, leads unificate, follow-up autonom, health engines — fabrica funcționează.

## 11. Product Weaknesses
1. **Zero validare de piață** — nicio ipoteză de preț/valoare testată pe clienți reali.
2. **Asimetrie owner/specialist** — supply side neglijată 3 sprinturi.
3. **Fără motiv de revenire lunară** — lipsește calendarul de mentenanță (retenția e ipotetică).
4. **Datorie G2 (4 sisteme twin)** — taxează fiecare feature viitor.
5. **Datele demo poluează platforma** (1.232 utilizatori, 137 proprietăți majoritar seed) — periculos la lansare (TD-02).

## 12. Remaining Gaps (top, din G1–G20 + noi)
- **G4 Transfer proprietate** — 0 cod; promisiunea publică de pe pașaport („se transferă integral noului proprietar") trebuie onorată. ⚠️ De la CX-3, această promisiune e AFIȘATĂ PUBLIC — gapul a devenit angajament.
- **G2 Twin unificat** — arhitectural, pre-condiție pentru House Health corect.
- **Calendar mentenanță (CX-4)** — motorul de retenție.
- **Analytics pe pașaport** — nu măsurăm vizualizări/scanări QR/conversii register din pașaport; bucla virală există dar e OARBĂ.
- **Verificare formală a documentelor** — fluxul „verified de platformă" plătit.

## 13. Technical Debt (relevant pentru scale)
| Item | Severitate |
|---|---|
| TD-02: retragere date demo înainte de lansare | **P0 la go-live** |
| TD-07: rate limiting endpoint-uri publice (acum include și pașaportul) | P1 |
| G2: fragmentare twin | P1 arhitectural |
| TD-04: e-Factura (obligație legală B2B RO la facturare) | P1 legal |
| Migrare imagini base64 → storage (campanii marketing) | P2 |

## 14. Business Risks
1. **Stripe LIVE + Resend DNS blocate (acțiune Fondator)** — fără ele, orice lansare e teatru: nu putem încasa și nu putem trimite emailuri. *Cel mai mare risc de business e administrativ, nu tehnic.*
2. **e-Factura** — facturare B2B fără conformitate = risc legal direct la primul client business.
3. **Monetizare nevalidată** — twin gratuit + audit plătit + abonament e o ipoteză; prețurile n-au atins niciodată un client real.
4. **Cost de oportunitate** — capacitatea de execuție consumată pe features noi în loc de learning de piață.

## 15. Adoption Risks
1. **Comportament nou cerut** — „cartea casei" nu e o categorie existentă în mintea proprietarului RO; educația pieței cade pe landing + pașaport + ghiduri SEO.
2. **Cold-start pe valoare** — un pașaport cu 0 documente arată gol; HeroDoc „Pasul 2 din 3" atenuează, dar primele 10 minute decid totul.
3. **Cold-start pe marketplace** — fără specialiști activi în orașul clientului, cererea moare; Gap Records ajută operațional dar nu scalează.
4. **Încrederea în platformă nouă cu date sensibile** (acte de proprietate) — Trust Center + GDPR există, dar dovada socială lipsește (0 recenzii reale).

## 16. Top 10 Highest Impact Features (ordonate după impact × valoare client × trust × adopție)
1. **Passport Analytics + contor scanări QR** (S) — face bucla virală măsurabilă; fără asta nu știm dacă cel mai promițător canal funcționează. *Impact: learning maxim / efort minim.*
2. **CX-4 Calendar mentenanță + remindere email** (M) — motivul revenirii lunare; alimentează DNA + trust score + cerere marketplace. *Motorul de retenție.*
3. **Curățenie date demo + seed de producție** (S) — pre-condiție go-live (TD-02).
4. **CX-5 Specialist Experience** (M) — dashboard 75→90, portofoliu public de lucrări verificate (pașaportul specialistului) — echilibrează marketplace-ul.
5. **Transfer proprietate cu istoric (G4)** (M) — onorează promisiunea publică de pe pașaport; moment natural de plată (taxă de transfer).
6. **Twin unificat (G2)** (M) — plătește datoria arhitecturală, deblochează House Health corect.
7. **e-Factura RO** (M) — deblochează legal facturarea B2B.
8. **AI Document Extraction** (M) — poză la factură → categorie/dată/firmă/garanție completate automat; reduce fricțiunea principală din CX-2.
9. **Rate limiting + hardening public** (S) — TD-07, acum suprafață publică mai mare.
10. **Owner AI Assistant (CX-6)** (L) — „întreabă-ți casa orice"; diferențiator puternic dar DUPĂ ce există date reale de consumat.

## 17. Features care trebuie AMÂNATE (explicit)
- **IoT / senzori smart home** — zero cerere validată; scump; DNA-ul nu are încă consumatori pentru date real-time.
- **National Property Index / insights publice** — cu <50 audituri reale ar publica date false (încălcare Truth Engine).
- **Extindere franciză / multi-oraș** — înainte de 1 oraș funcțional e distragere.
- **Enterprise OS tooling suplimentar** (Inspector V2 extins, Story Mode etc.) — fabrica e suficient de bună; produsul are nevoie de clienți, nu de mai multă introspecție.
- **Marketplace Radar/optimizări avansate matching** — volumul actual (199 cereri, majoritar demo) nu justifică.

## 18. Updated North Star Metrics

**North Star: Trusted Properties** = proprietăți cu Trust Score ≥50 **și** pașaport public activ.
- Azi (Measured): **2 pașapoarte active**, ambele interne. Baseline real: **0**.

Metrici de gardă (guardrails):
| Metric | Azi | Țintă beta (90 zile) |
|---|---|---|
| Trusted Properties | 0 reale | 25 |
| Owneri activați (≥1 document în 7 zile de la register) | n/a | 40% |
| Scanări/vizualizări pașaport → register (viral loop) | nemăsurat | măsurat + ≥5% |
| Venit real încasat | 450 RON (manual) | primele 10 plăți Stripe LIVE |
| Specialiști activi (≥1 lead acceptat/lună) | 0 reali | 10 |

## 19. Updated Product Maturity Score — **62/100** (de la ~45)

| Dimensiune | EO-005A | Azi | Notă |
|---|---|---|---|
| Onboarding & conversie | 55 | **91** | audit cu capturi, gate 90 trecut |
| Document Vault / memorie | 0 | **85** | complet; lipsă: AI extraction, verificare formală |
| Property DNA | 45 | **70** | capabilities reale; G2 rămas |
| Digital Twin | 45 | **58** | fragmentare nerezolvată |
| Trust & Passport | 10 | **85** | livrat CX-3, security 100% |
| Marketplace | 70 | **72** | funcțional; supply side în urmă |
| Retenție / recurență | 15 | **20** | calendarul lipsește — cea mai slabă dimensiune |
| Monetizare | 25 | **30** | fluxuri gata, zero validare LIVE |
| Legal & compliance | 40 | **45** | GDPR ok; e-Factura lipsă |
| **TOTAL ponderat** | **~45** | **62** | |

## 20. Updated Roadmap (propunere)

```
FAZA 0 — GO-LIVE GATE (1 sprint, în paralel cu acțiunile Fondatorului)
  ├─ Fondator: Stripe LIVE claim + Resend DNS (blockere din Iulie!)
  ├─ Agent: curățenie date demo (TD-02) + rate limiting public (TD-07)
  └─ Agent: Passport Analytics (vizualizări + scanări QR + conversii register)

CX-4 — Calendar mentenanță + remindere (motorul de retenție)
CX-5 — Specialist Experience (dashboard 90 + portofoliu verificat)
G4  — Transfer proprietate cu istoric (+ moment de monetizare)
G2  — Twin unificat (datorie arhitecturală)
P1  — e-Factura RO (înainte de primul client B2B)
CX-6 — Owner AI (după ce există date reale)
```

## 21. Readiness (Estimated, confidence 75%)

| Prag | Readiness | Ce lipsește |
|---|---|---|
| **Public beta** | **80%** — 2–3 săptămâni | Stripe LIVE, Resend DNS, curățenie demo, analytics pașaport |
| **Clienți plătitori** | **70%** | + validare preț pe 5–10 clienți reali, e-Factura pentru B2B |
| **Scaling** | **40%** | + retenție dovedită (CX-4 măsurat), supply side sănătos (CX-5), G2 plătit, dovezi sociale |

## 22. Ce s-a schimbat fundamental după CX-1→3 (valoarea celor 3 sprinturi, ca întreg)
Înainte: platformă cu funcții multe și poveste neclară. Acum: **un lanț de valoare narativ complet** — *„Adaugi casa (1 min) → îi dai memorie (primul document) → primești scoruri oneste → o dovedești lumii (pașaport + QR)"*. Fiecare pas alimentează următorul și fiecare pas a trecut un gate măsurat ≥90. Produsul a căpătat, pentru prima dată, un **mecanism de creștere endogen** (pașaportul viral) și o **promisiune publică** (transferul istoriei) care obligă roadmap-ul.

## 23. CEO Recommendation — „Dacă aș fi CPO la PropManage, ce aș construi următorul și de ce"

**Aș construi cel mai mic lucru care pune produsul în fața a 10 proprietari reali: GO-LIVE GATE + Passport Analytics. Abia apoi CX-4.**

Motivare pe criteriile cerute:
- **Impact măsurabil:** Analytics pe pașaport transformă singurul canal de achiziție organică din „speranță" în „număr" (scanări, vizualizări, conversii). Costă zile, nu săptămâni.
- **Valoare pentru client:** clientul real care folosește vault-ul + pașaportul ne va spune în 2 săptămâni mai mult decât orice audit intern în 2 luni.
- **Trust:** curățenia datelor demo e o condiție de onestitate — nu putem afișa „încredere verificabilă" pe o platformă populată cu utilizatori fictivi.
- **Adopție:** blockerele Stripe/Resend sunt singurele lucruri pe care doar Fondatorul le poate face; orice sprint care începe fără ele mărește stiva de features nevalidate.
- **Scalabilitate pe termen lung:** CX-4 (mentenanță) rămâne pariul corect de retenție și îl recomand IMEDIAT după gate — dar retenția se măsoară doar pe utilizatori reali, deci ordinea Gate → CX-4 e singura care face CX-4 măsurabil.

**Formula recomandată:** *1 sprint GO-LIVE GATE (agent: analytics + curățenie + hardening; Fondator: Stripe + DNS) → beta privată cu 10 proprietari reali → CX-4 măsurat pe ei.*

**Decizia rămâne a Fondatorului:** dacă blockerele externe nu pot fi rezolvate în următoarele 2 săptămâni, atunci CX-4 primul e acceptabil — dar cu Passport Analytics inclus obligatoriu, ca să nu mai zburăm orb.

---
*Review generat conform EO-006 (Customer Experience First), EO-007 (AI CPO), D161 (Truth Engine). Toate cifrele marcate Measured provin din DB-ul live sau din rapoartele de testare; scorurile de maturitate sunt clasă Estimated cu confidence 75%.*
