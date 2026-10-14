# Modulul „Composesorate” în Rădăcini — structura logică (S9, model demonstrativ)

Baza: `ANALIZA_INITIALA.md`, `ANALIZA_STATUT_CIUNCA.md`, `ANALIZA_REGISTRU_SI_PROIECTE.md`, `CONTEXT_COMPOSESORATE.md`.

## 1. Scop
Un instrument care face composesoratul **transparent, verificabil și activ**:
1. **Fiecare membru și moștenitor** își vede cota, sursa ei, documentele și banii cuveniți, și poate cere informații.
2. **Conducerea** își face treaba la vedere: convocări cu dovadă, documente publicate, termene urmărite. Fiecare acțiune lasă o urmă care nu se poate șterge.
3. **Membrii** au instrumentele din statut: petiții pentru AGA extraordinară sau pentru puncte pe ordinea de zi, mandate, contestare în termen.
4. **Composesoratul se leagă de economia Rădăcini:** terenuri, proiecte cu participare voluntară, piață, prestatori.

**Principiu:** puterea vine din **reguli vizibile și urme care nu se pot șterge**, nu din persoanele aflate în funcție.

## 2. Structura (entități)
| Entitate | Ce conține | Cine vede |
|---|---|---|
| **Asociație** (`radacini_associations`) | nume, tip (composesorat/obște/asociație pastorală), localități, date juridice (CUI opțional, judecătorie), **reguli statutare configurabile**, patrimoniu (CF, topo, ha, categorie), organe (CA, cenzori) | public: nume, localități, suprafață, scor de transparență · membri: tot |
| **Registru** (`radacini_assoc_members`) | cod membru (M001…), nume afișat, **cote**, **sursele cotelor** („Nr 372 = 0,20”), stare (necunoscut → contactat → confirmat → activ · decedat · moștenitor în curs), funcție (membru, președinte, vicepreședinte, secretar, casier, responsabil silvic, cenzor), legătura cu contul (după revendicare) | membrul își vede rândul · CA, cenzorii și operatorul văd registrul |
| **Revendicări** (`radacini_assoc_claims`) | „sunt eu” / „sunt moștenitor”, dovezi încărcate (certificat de moștenitor, act), decizie motivată | solicitantul, CA, cenzorii |
| **Documente** (`radacini_assoc_documents`) | tip (statut, PV AGA, PV CA, bilanț, raport cenzori, contract, CF, hotărâre, convocator, altul), fișier privat, **amprentă SHA-256**, versiuni (doar adăugare, fără ștergere), **jurnal de consultare** | după vizibilitate: membri sau CA |
| **Ședințe** (`radacini_assoc_meetings`) | AGA ordinară/extraordinară, ședință CA; dată, loc, ordine de zi, materiale, **convocare cu jurnal de livrare și confirmări**, prezență (membri + mandate), **cvorum calculat**, hotărâri cu **termen de contestare** | membri (AGA), membri + CA (registrul CA e consultabil de toți, cf. art. 22(2) Ciunca) |
| **Mandate** (`radacini_assoc_mandates`) | mandant → mandatar, pentru o ședință; verificarea limitelor (cel mult 5 membri, cel mult 5% din voturi) | părțile, CA |
| **Petiții** (`radacini_assoc_petitions`) | AGA extraordinară (prag 1/4 din membri sau 1/4 din cote) sau punct pe ordinea de zi (prag 1/10 din membri, cu ≥5 zile înainte); semnături; prag atins → notificare și termen | membri |
| **Calendar statutar** (`radacini_assoc_obligations`) | obligații generate din reguli: AGA până la 30.04 și 30.11, bilanț până la 31.03, buget în noiembrie, plan de pășunat în octombrie, verificări trimestriale ale cenzorilor, actualizarea anuală a registrului; stare „la timp / întârziat / ratat” + documentul-dovadă | membri |
| **Finanțe** (`radacini_assoc_finance`) | sinteză anuală venituri/cheltuieli pe categorii, **repartizarea profitului** (procente din statut), **sume cuvenite pe membru**, stare plată, **data prescrierii** (5 ani) | membrul își vede suma · toți văd sinteza |
| **Cereri de informații** (`radacini_assoc_requests`) | întrebare sau cerere de act, termen de răspuns (implicit 30 de zile), răspuns + document | solicitantul, CA |
| **Jurnal de răspundere** | fiecare scriere a CA sau a operatorului: cine, ce, când, valoarea anterioară | membri (rezumat), cenzori (complet) |

**Scorul de transparență** (public și pentru membri) se calculează din:
- obligațiile la timp (%);
- documentele obligatorii publicate (statut, ultimul PV AGA, ultimul bilanț, raportul cenzorilor);
- cererile de informații răspunse în termen (%);
- participarea (cotele reprezentate de membri activi, %).

## 3. Roluri
- **Vizitator:** pagina publică a asociației (fără date personale).
- **Utilizator care revendică:** caută asociația, revendică un rând din registru sau calitatea de moștenitor.
- **Membru verificat:** cota proprie, documente, ședințe, petiții, mandate, cereri, sumele cuvenite, scorul de transparență.
- **Conducere (CA):** președinte, vicepreședinte, secretar, casier, responsabil silvic. Gestionează registrul și revendicările, documentele, ședințele, finanțele, răspunsurile. **Totul intră în jurnal.**
- **Cenzori:** citesc tot, inclusiv jurnalul complet; își publică rapoartele.
- **Operator Rădăcini:** onboarding asistat, digitalizarea documentelor, mediere. Acționează doar la cererea asociației și apare în jurnal.

## 4. Legături cu ecosistemul Rădăcini
| Rădăcini | Composesorat |
|---|---|
| **Terenuri** | elementele de patrimoniu pot fi legate de un teren Rădăcini (ofertă publică de pășunat sau arendă, cu aprobare CA consemnată) |
| **Proiecte + contribuții + recoltă** | proiecte cu participare voluntară pe suprafețe ale asociației (modelul zmeurului din Rîșca); alocare pe cotă, pe contribuție sau mixt |
| **Piață** | anunțuri ale asociației (produse, drepturi de pășunat, lemn de foc pentru membri, ca informare) |
| **Comunități + decizii** | comunitatea asociației pentru anunțuri și **sondaje consultative** (nu înlocuiesc votul AGA) |
| **Prestatori** | agronomi, mecanizare, servicii silvice |
| **Notificări** | convocări, documente noi, termene, petiții, prescrieri |
| **Fotografii / storage privat** | documente scanate, dovezi pentru revendicări |
| **GDPR export** | include apartenența la asociații |
| **Administrare** | lista asociațiilor, onboarding, indicatori |

## 5. Ce intră în modelul demonstrativ (S9)
Toate cele de mai sus, la nivel funcțional de bază, plus un **„Composesorat Demo”** generat cu date fictive:
- ~60 de membri cu cote fracționare și surse de cote;
- 3 stări de participare;
- documente exemplu;
- o AGA cu cvorum neîntrunit la prima convocare;
- o petiție în curs;
- obligații întârziate;
- sume cuvenite aproape de prescriere.

Așa modelul arată exact problemele și soluțiile.

**În afara S9:** importul unui registru real (doar cu acordul organelor), vot oficial electronic (după jurist și modificarea statutului), plăți ale dividendelor.
