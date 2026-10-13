# MASTER PROMPT — AGRO-COLABORATIV (cerința inițială a proprietarului produsului)

Analiză de arhitectură, reutilizare PropManage și proiectare a unui ecosistem alimentar comunitar.

## 1. Rolul
Echipă multidisciplinară: Software Architect / CTO, Product Manager, Business Analyst, specialist marketplace-uri și platforme colaborative, specialist GIS și gestionarea terenurilor, specialist sisteme de producție agricolă comunitară, specialist securitate, protecția datelor și guvernanță software. Lucrează pe baza dovezilor din repository; nu presupune că o funcționalitate există doar pentru că e menționată într-un document.

## 2. Context
Platformă care conectează: (1) proprietari de terenuri agricole sau utilizabile; (2) persoane și familii care vor să cultive; (3) cultivatori și producători locali; (4) consumatori care caută alimente accesibile; (5) grupuri care vor să investească în proiecte agricole comune; (6) comunități care organizează activități educaționale și recreative.
Rețea descentralizată de producție și distribuție, România, început în județul Cluj. Trebuie să funcționeze în condiții economice dificile (carburant scump, putere de cumpărare scăzută, lanțuri de aprovizionare perturbate). Nu e o platformă bazată pe frică, ci un sistem practic, educațional, economic și comunitar.

## 3. Reutilizare înainte de dezvoltare
De verificat concret: autentificare și utilizatori; profiluri și permisiuni; marketplace și listări; cereri, oferte, matching; hărți și date geospațiale; notificări și comunicare; sisteme administrative; abonamente și plăți; evidențe și istoric tranzacții; audit, monitorizare, securitate.
Nu crea duplicate. Nu presupune compatibilitate după denumire: verifică implementarea, dependențele, API-urile, modelele de date, permisiunile și starea reală. Separă: infrastructura comună; funcționalitățile agricole noi; ce necesită adaptare; ce nu trebuie reutilizat.

## 4. Business model
**A. Terenuri.** Proprietarul poate alege: închiriere pe perioadă determinată; cultivare pentru un procent din recoltă; cultivare contra sumă fixă; model mixt; vânzare; participare într-un proiect comun (dacă structura juridică permite). Oferta conține: suprafață, locație, acces, surse de apă cunoscute, culturi existente, condiții de utilizare, disponibilitate.
**B. Membri și familii.** Un membru poate avea simultan mai multe interese (cultivă, consumă, oferă teren, vinde, schimbă, participă la proiecte comune); rolurile nu sunt exclusive. De analizat un abonament orientativ de 5 €/lună/membru, cu cont familial și reguli distincte de facturare. Abonamentul NU acordă automat dreptul la o cantitate garantată de alimente.
**C. Comunități agricole.** Grupuri locale în jurul unui teren sau proiect. Planifică: suprafețe cultivate; culturi și rotație; necesar de semințe și unelte; lucrări manuale și mecanizate; program de participare; producție estimată și efectivă; distribuție; schimburi și vânzarea surplusului. Reguli transparente pentru contribuții în bani, muncă, teren și materiale.
**D. Marketplace alimentar.** Vânzare; cumpărare directă de la producători; schimb de produse; oferte mixte (bani + produse); echivalent de schimb; evidența comenzilor și livrărilor; evaluarea tranzacțiilor. Prețuri accesibile și transparente, nu speculă. Fără token financiar, monedă internă sau portofel cu valoare transferabilă fără analiză juridică și tehnică separată.
**E. Investiții colective (etapă ulterioară).** Cumpărare teren; livadă; sere și irigații; depozite; ferme mixte; proiecte piscicole; facilități rurale de recreere și educație. Evidențiază contribuțiile, costurile, deciziile, drepturile, riscurile și regulile de ieșire. Nu presupune că asocierea în participațiune, coproprietatea etc. sunt automat potrivite.

## 5. Experiență interactivă
Prietenoasă pentru familii, copii și tineri. De analizat gamification: hartă interactivă a comunității; terenuri și proiecte ca zone; obiective sezoniere; activități de plantare/întreținere/recoltare; niveluri de experiență; insigne educaționale; progresul comunității; evenimente și zile de lucru voluntare. Punctele de joc separate de drepturile economice reale. Voluntar, fără presiune socială, fără penalizări.

## 6. Sarcina: audit și arhitectură (fără implementare în prima etapă)
- **Faza 0 — Audit:** arhitectura reală, stack, module, entități și relații, API-uri, autentificare și permisiuni, marketplace, matching, GIS, plăți și abonamente, infrastructură administrativă, teste, riscuri de securitate, limitări de reutilizare. Dovezi concrete (căi, componente, modele, endpoint-uri, teste). Marcaj: CONFIRMAT / PARȚIAL CONFIRMAT / NECONFIRMAT / LIPSĂ / NECESITĂ VALIDARE. Documentația nu e dovadă suficientă a comportamentului la rulare.
- **Faza 1 — Matricea de reutilizare:** Funcționalitate agricolă | Componentă PropManage | Dovezi | Modificări | Riscuri | Decizie (reutilizare directă / adaptare / dezvoltare nouă / amânare / nerecomandată).
- **Faza 2 — Arhitectura produsului:** module 1 Identity & Membership, 2 Land Registry, 3 Agricultural Communities, 4 Projects & Agreements, 5 Crop Planning, 6 Work Coordination, 7 Harvest & Allocation, 8 Food Marketplace, 9 Barter & Exchange, 10 Orders & Logistics, 11 Shared Investment Projects, 12 Gamification & Education, 13 Administration & Audit. Ce intră în MVP, ce se reutilizează, ce se amână. Fără microservicii impuse.
- **Faza 3 — Modelul de date:** utilizatori și gospodării; membri și comunități; terenuri și drepturi de utilizare; oferte și cereri; proiecte și participanți; acorduri și obligații; culturi și cicluri; activități și contribuții; producție și distribuție; produse și listări; comenzi și schimburi; plăți și evidențe financiare; proiecte de investiții; decizii și audit. Chei, cardinalități, constrângeri, istoric, reguli de acces.
- **Faza 4 — Business logic:** fluxuri A publicare teren; B cerere de utilizare; C negociere, acord, începerea proiectului; D planificare culturi și rotație; E lucrări și contribuții; F recoltare, măsurare, distribuție; G vânzare și schimb; H plata abonamentului; I achiziție colectivă / facilitate comună. Pentru fiecare: stări, actori autorizați, validări, erori, prevenirea conflictelor.
- **Faza 5 — API și frontend:** endpoint-uri, contracte, permisiuni, pagini, dashboard-uri pe roluri, interacțiuni mobile, notificări, scenarii de eroare, criterii de acceptare.
- **Faza 6 — Planul MVP:** Epic / Story / Task, criterii de acceptare, dependențe, estimări, riscuri, teste. Ciclul: Proprietar → teren → cultivator → acord → proiect → activități → recoltă → distribuție sau schimb. Pilot Cluj.

## 7. Principii obligatorii
1. Nu rescrie PropManage. 2. Fără duplicate. 3. Nu modifica infrastructura comună fără justificare și aprobare. 4. Nu schimba schema bazei de date fără analiza impactului și strategie de migrare. 5. Nu modifica datele existente ale utilizatorilor. 6. Nu modifica funcționalități fără legătură. 7. Fără plăți, tokenuri sau investiții colective fără analiză juridică. 8. Nu promite producție garantată. 9. Protecția datelor, autorizare, acces minim necesar. 10. Separare între evidența contribuțiilor, drepturile contractuale și punctele de gamification. 11. Distinge fapte confirmate, ipoteze și propuneri. 12. Fără deploy sau publish.

## 8. Livrabilele primei etape
1 rezumat executiv; 2 arhitectura PropManage; 3 inventarul componentelor reutilizabile; 4 matricea de reutilizare; 5 arhitectura agricolă; 6 modelul conceptual de date; 7 diagrama relațiilor dintre module; 8 fluxurile business; 9 riscuri tehnice și juridice; 10 definiția MVP; 11 backlog inițial; 12 estimarea efortului și a costurilor; 13 lista deciziilor pentru proprietarul produsului.

## Cerințe ulterioare ale proprietarului (în aceeași sesiune)
- Audit al adminului: zonele Business și Infrastructure/Dev, Knowledge Center și restul modulelor; cum se conectează; ce interfață are clientul, ce vede și ce poate integra cel care vine; rolul operatorului.
- Manager Rădăcini separat de adminul PropManage (deocamdată proprietarul e singurul manager).
- Interfața să arate ca PropManage; preview local pentru a urmări dezvoltarea.
