// Design Interior SEO cluster — real, distinct, useful content (RO).
// Consumed by DesignInteriorPage.jsx. Backend mirror: backend/seo_design.py.
// No fake projects/portfolios/testimonials. Prices are ranges/qualitative only.

const R = {
  hub: { to: "/design-interior", label: "Design interior" },
  pret: { to: "/design-interior/pret", label: "Preț design interior" },
  renovare: { to: "/design-interior/renovare", label: "Design pentru renovare" },
  d3: { to: "/design-interior/3d", label: "Randări 3D / Digital Twin" },
  impl: { to: "/design-interior/implementare", label: "Design cu implementare" },
  apart: { to: "/design-interior/apartament", label: "Design apartament" },
  casa: { to: "/design-interior/casa", label: "Design casă" },
  twin: { to: "/digital-twin", label: "Digital Twin locuință" },
  scor: { to: "/scorul-casei", label: "Scorul casei (audit)" },
  imob: { to: "/imobile-verificate", label: "Imobile verificate" },
  ghidDesigner: { to: "/ghiduri/cum-alegi-designer-interior", label: "Cum alegi un designer interior" },
  ghidCost: { to: "/ghiduri/cost-renovare-apartament-2-camere", label: "Cât costă o renovare" },
};

// ── Commercial + room pages ─────────────────────────────────────────────────
export const DI_PAGES = {
  apartament: {
    cluster: "apartament", tag: "Apartament",
    h1: "Design interior pentru apartament",
    title: "Design interior apartament: proces, costuri și rezultate 2026 | PropManage",
    description: "Cum arată un proiect complet de design interior pentru apartament — de la releveu și concept, la randări 3D, listă de materiale și implementare cu specialiști verificați.",
    intro: "Un proiect de design interior pentru apartament nu înseamnă doar „idei frumoase”. Înseamnă un plan tehnic care ține cont de suprafață, de instalații, de lumina naturală și de bugetul real, astfel încât amenajarea să poată fi executată exact așa cum a fost gândită.",
    sections: [
      { h2: "Ce include un proiect pentru apartament", body: ["Un proiect coerent pornește de la măsurători precise și de la nevoile familiei, apoi transformă totul în documentație clară pentru echipa de execuție."], bullets: ["Releveu și plan de mobilare optimizat pe circulație și depozitare", "Concept vizual + randări 3D pe fiecare cameră", "Planuri tehnice: electrice, sanitare, tavane, finisaje", "Listă de materiale și obiecte cu cantități, pentru bugetare corectă"] },
      { h2: "De la ce suprafață merită", body: ["Designul este util indiferent de metraj: la garsoniere și apartamente mici rezolvă lipsa spațiului, iar la 3-4 camere coordonează multe decizii care altfel se iau haotic pe șantier."] },
      { h2: "Cum lucrează PropManage", body: ["Procesul nostru leagă designul de execuție reală: Design → Audit → Digital Twin → Proiectare → Implementare. Astfel, ceea ce vezi în randare corespunde cu ceea ce se poate construi, iar plățile către specialiști sunt protejate prin escrow."] },
    ],
    faq: [
      { q: "Cât durează un proiect de design pentru apartament?", a: "Un proiect complet pentru un apartament de 2-3 camere durează de obicei 3-6 săptămâni pentru partea de proiectare, în funcție de complexitate și de viteza deciziilor." },
      { q: "Pot primi doar conceptul, fără implementare?", a: "Da. Poți lua doar proiectul de design, sau poți continua cu implementarea la cheie prin specialiști verificați." },
    ],
    related: [R.apart, R.pret, R.renovare, R.d3, R.impl, R.ghidDesigner],
  },
  "apartament-2-camere": {
    cluster: "apartament", tag: "Apartament 2 camere",
    h1: "Design interior apartament 2 camere",
    title: "Design interior apartament 2 camere: idei, plan și costuri | PropManage",
    description: "Amenajare pentru apartament de 2 camere: optimizarea living-ului deschis, zona de noapte, depozitare inteligentă și un proces care duce proiectul până la execuție.",
    intro: "Apartamentul de 2 camere (50-65 mp) este cel mai frecvent tip de locuință din blocurile românești. Provocarea reală este echilibrul dintre o zonă de zi generoasă și un dormitor confortabil, fără să sacrifici depozitarea.",
    sections: [
      { h2: "Deciziile care contează la 2 camere", body: ["La această suprafață fiecare decizie are impact vizibil. Un plan bun rezolvă din start întrebările grele:"], bullets: ["Living deschis către bucătărie sau separat", "Locul pentru dressing / depozitare verticală", "Zona de lucru de acasă, integrată discret", "Trafic și uși care nu „mănâncă” pereți utili"] },
      { h2: "Buget realist", body: ["Un apartament de 2 camere are un cost de amenajare predictibil dacă pornești de la o listă de materiale clară. Vezi cum se structurează costurile în pagina noastră de preț, unde explicăm ce influențează bugetul, fără cifre inventate."] },
      { h2: "De la plan la șantier", body: ["Cu un Digital Twin al apartamentului, modificările se testează digital înainte să coste bani pe șantier. Proiectul rezultat poate fi executat de echipe verificate, cu plăți în escrow."] },
    ],
    faq: [
      { q: "Se poate uni bucătăria cu livingul?", a: "Adesea da, dar depinde dacă peretele este structural. Un audit tehnic sau un Digital Twin clarifică ce se poate demola în siguranță." },
      { q: "Cât costă amenajarea unui apartament de 2 camere?", a: "Costul variază mult cu nivelul finisajelor și cu lucrările de instalații. Pagina de preț explică factorii principali fără să promită sume fixe." },
    ],
    related: [R.apart, R.pret, R.renovare, R.twin, R.ghidCost],
  },
  "apartament-3-camere": {
    cluster: "apartament", tag: "Apartament 3 camere",
    h1: "Design interior apartament 3 camere",
    title: "Design interior apartament 3 camere: zonare și proiect complet | PropManage",
    description: "Amenajare pentru apartament de 3 camere: separarea corectă zi/noapte, camera copilului sau biroul, și un proiect tehnic gata de execuție.",
    intro: "La 3 camere (65-85 mp) apar mai multe funcțiuni: o cameră poate deveni birou, cameră de copil sau cameră de oaspeți. Aici designul înseamnă în primul rând o zonare inteligentă, nu doar decor.",
    sections: [
      { h2: "Zonare zi / noapte", body: ["Un plan bun izolează acustic zona de odihnă de zona socială și tratează holul ca spațiu util, nu pierdut."], bullets: ["Living + dining coerent pentru primit oaspeți", "Dormitor matrimonial cu dressing", "A treia cameră: birou, copil sau flexibilă", "Baie + eventual grup sanitar de serviciu"] },
      { h2: "Coordonarea meseriilor", body: ["La 3 camere cresc numărul de decizii tehnice (electrice, sanitare, climatizare). Proiectul le coordonează astfel încât echipele să nu se blocheze reciproc pe șantier."] },
      { h2: "Procesul PropManage", body: ["Design → Audit → Digital Twin → Proiectare → Implementare. Rezultatul este un proiect care se poate executa fidel, cu specialiști verificați și plăți protejate."] },
    ],
    faq: [
      { q: "Merită un birou separat acasă?", a: "Dacă lucrezi frecvent de acasă, o cameră dedicată sau o nișă bine izolată crește semnificativ confortul și valoarea de utilizare a apartamentului." },
    ],
    related: [R.apart, R.casa, R.pret, R.impl, R.d3],
  },
  "apartament-mic": {
    cluster: "apartament", tag: "Apartament mic / garsonieră",
    h1: "Design interior pentru apartament mic și garsonieră",
    title: "Design interior apartament mic: soluții pentru spații sub 45 mp | PropManage",
    description: "Amenajare pentru garsoniere și apartamente mici: multifuncționalitate, depozitare verticală, lumină și trucuri care fac spațiul să pară mai mare.",
    intro: "În spații mici (sub 45 mp) fiecare centimetru contează. Aici designul face diferența cea mai mare: mobilierul multifuncțional, depozitarea pe verticală și paleta de culori decid dacă locuința pare aglomerată sau aerisită.",
    sections: [
      { h2: "Principii pentru spații mici", body: ["Obiectivul este ca aceeași suprafață să susțină mai multe funcțiuni fără să pară înghesuită."], bullets: ["Mobilier multifuncțional (pat cu depozitare, masă extensibilă)", "Depozitare până în tavan, uși glisante", "Culori deschise și oglinzi pentru adâncime", "Iluminat pe straturi, nu o singură sursă centrală"] },
      { h2: "Greșeli frecvente", body: ["Cele mai costisitoare greșeli sunt mobilierul prea mare, lipsa unui plan de depozitare și subestimarea iluminatului. Un plan de mobilare la scară le previne."] },
      { h2: "Testează înainte să cumperi", body: ["Cu un Digital Twin poți verifica dacă mobilierul chiar încape și cum circulă lumina, înainte să comanzi ceva ce nu se potrivește."] },
    ],
    faq: [
      { q: "Se poate amenaja frumos o garsonieră de 30 mp?", a: "Da. Cheia este planificarea depozitării și zonarea clară a funcțiunilor (dormit, gătit, lucru) în același spațiu deschis." },
    ],
    related: [R.apart, R.pret, R.d3, R.twin],
  },
  "apartament-vechi": {
    cluster: "apartament", tag: "Apartament vechi",
    h1: "Design interior pentru apartament vechi",
    title: "Design interior apartament vechi: renovare, instalații și structură | PropManage",
    description: "Amenajarea unui apartament vechi cere atenție la instalații, structură și izolație. Vezi ce se verifică înainte de design și cum eviți surprizele de pe șantier.",
    intro: "Un apartament vechi (inclusiv cele din blocurile construite înainte de 1990) are un potențial excelent, dar ascunde riscuri: instalații electrice și sanitare uzate, umezeală, pereți neregulați. Aici designul trebuie să pornească de la o evaluare tehnică serioasă.",
    sections: [
      { h2: "Ce se verifică înainte de design", body: ["Într-un apartament vechi, deciziile estetice vin după cele tehnice. Recomandăm o evaluare a stării reale:"], bullets: ["Instalația electrică și tabloul (secțiuni, împământare)", "Coloane și instalații sanitare", "Pereți structurali vs. neportanți", "Umezeală, mucegai, izolație termică și fonică"] },
      { h2: "De ce contează auditul", body: ["Un audit tehnic sau Scorul casei îți spune ce trebuie înlocuit obligatoriu, ca să nu investești în finisaje frumoase peste instalații care vor ceda în 2 ani."] },
      { h2: "Design + renovare, împreună", body: ["La apartamentele vechi, designul și renovarea merg mână în mână. Procesul PropManage integrează auditul și Digital Twin-ul chiar înainte de proiectare."] },
    ],
    faq: [
      { q: "Pot demola pereți într-un apartament vechi de bloc?", a: "Numai după ce se confirmă că nu sunt structurali. Un audit sau Digital Twin cu releveu clarifică acest lucru; demolarea unui perete portant este periculoasă și ilegală fără expertiză." },
      { q: "Merită schimbată toată instalația electrică?", a: "În majoritatea apartamentelor vechi, da — este cea mai frecventă recomandare de siguranță din audituri." },
    ],
    related: [R.renovare, R.scor, R.imob, R.twin, R.ghidCost],
  },
  casa: {
    cluster: "casa", tag: "Casă",
    h1: "Design interior pentru casă",
    title: "Design interior casă: proiect complet pe mai multe niveluri | PropManage",
    description: "Design interior pentru casă: coordonarea nivelurilor, scări, spații generoase și instalații complexe, cu un proces care duce proiectul până la execuție.",
    intro: "O casă oferă libertate mai mare decât un apartament, dar și complexitate mai mare: mai multe niveluri, scări, spații tehnice, uneori grădină sau terasă. Designul unei case înseamnă o viziune unitară pe toate zonele.",
    sections: [
      { h2: "Ce e specific la casă", body: ["Proiectul trebuie să lege coerent parterul social de zona de noapte de la etaj și să integreze spațiile tehnice."], bullets: ["Fluxul parter (zi) → etaj (noapte)", "Scara ca element central de design", "Spații tehnice: centrală, depozitare, spălătorie", "Legătura interior-exterior (terasă, grădină)"] },
      { h2: "Instalații și confort", body: ["La case, sistemele de încălzire, ventilație și eventual automatizare (smart home) trebuie gândite din faza de proiect, nu adăugate ulterior."] },
      { h2: "Procesul complet", body: ["Design → Audit → Digital Twin → Proiectare → Implementare, cu specialiști verificați și plăți în escrow, se aplică integral și la case."] },
    ],
    faq: [
      { q: "Se poate face design doar pentru o parte din casă?", a: "Da, dar recomandăm cel puțin un concept unitar pentru zonele comune, ca stilul să fie coerent între niveluri." },
    ],
    related: [R.hub, R.pret, R.renovare, R.impl, R.d3],
  },
  pret: {
    cluster: "pret", tag: "Preț & cost",
    h1: "Cât costă designul interior? Prețuri și ce le influențează",
    title: "Preț design interior 2026: de ce depinde costul (fără cifre inventate) | PropManage",
    description: "Ce influențează prețul unui proiect de design interior: suprafața, complexitatea, nivelul de detaliu, auditul, Digital Twin-ul și implementarea. Transparent, fără sume promise artificial.",
    intro: "„Cât costă designul interior?” nu are un singur răspuns, pentru că prețul depinde de ce anume incluzi. Mai jos explicăm transparent factorii reali, ca să poți estima corect — fără să inventăm tarife care nu există în oferta ta concretă.",
    sections: [
      { h2: "Ce influențează prețul", body: ["Costul unui proiect variază în funcție de câțiva factori clari:"], bullets: ["Suprafața și numărul de camere", "Nivelul de detaliu (concept vs. proiect tehnic complet)", "Randări 3D și numărul de revizii", "Instalații și modificări structurale", "Dacă include doar designul sau și implementarea"] },
      { h2: "Design simplu vs. proces complet", body: ["Un „concept” (moodboard + plan de mobilare) costă semnificativ mai puțin decât un proiect tehnic complet cu planuri de execuție. Pentru o renovare serioasă, procesul complet economisește bani pe șantier prin evitarea greșelilor."] },
      { h2: "Ce poate include în plus", body: ["Auditul tehnic, Digital Twin-ul și managementul implementării sunt servicii care se adaugă atunci când vrei siguranță maximă că proiectul se execută corect. Fiecare are rolul lui în reducerea riscului."] },
      { h2: "Cum obții un preț real", body: ["Cel mai corect preț vine dintr-o listă de materiale și un scop clar. Postează cererea și primești oferte de la designeri verificați, cu recenzii reale, nu estimări generice."] },
    ],
    faq: [
      { q: "Se plătește designul la mp?", a: "Mulți designeri lucrează cu tarif la mp, alții cu preț pe proiect. Ambele sunt corecte; important este să știi exact ce livrabile primești." },
      { q: "Designul chiar economisește bani?", a: "Da, la lucrări medii și mari: un plan bun previne cumpărături greșite, refaceri și întârzieri pe șantier, care costă adesea mai mult decât proiectul." },
    ],
    related: [R.hub, R.renovare, R.impl, R.d3, R.ghidCost],
  },
  renovare: {
    cluster: "renovare", tag: "Renovare",
    h1: "Design interior pentru renovare: Design → Audit → Digital Twin → Implementare",
    title: "Design interior pentru renovare: procesul corect pas cu pas | PropManage",
    description: "Renovezi un apartament? Ordinea corectă este design + audit + Digital Twin înainte de execuție. Vezi ce se măsoară și se verifică ca să eviți surprizele scumpe.",
    intro: "Renovarea este momentul în care designul aduce cea mai mare valoare — dar și în care greșelile costă cel mai mult. Secretul este ordinea corectă: întâi înțelegi starea reală a locuinței, apoi proiectezi, apoi execuți.",
    sections: [
      { h2: "Ordinea corectă a pașilor", body: ["La PropManage recomandăm un flux clar, care leagă designul de realitatea tehnică a locuinței:"], bullets: ["Design — concept și plan de mobilare", "Audit — starea instalațiilor, structurii, umezelii", "Digital Twin — releveu digital și testarea modificărilor", "Proiectare — planuri tehnice de execuție", "Implementare — echipe verificate, plăți în escrow"] },
      { h2: "Ce se măsoară și se verifică înainte", body: ["Înainte de a sparge un perete sau a comanda mobilă, se verifică ce este structural, ce instalații trebuie înlocuite și unde există umezeală. Vezi Scorul casei pentru o evaluare structurată."] },
      { h2: "De ce contează măsurătorile", body: ["Un releveu precis (parte din Digital Twin) evită cea mai frecventă problemă de pe șantier: mobilierul sau finisajele comandate care nu se potrivesc, pentru că pereții nu erau drepți sau cotele erau greșite."] },
    ],
    faq: [
      { q: "Fac întâi designul sau întâi demolez?", a: "Întâi designul și auditul. Demolarea fără plan duce la costuri suplimentare și, în cazul pereților structurali, la riscuri reale de siguranță." },
      { q: "Ce este un Digital Twin la renovare?", a: "Este o replică digitală a locuinței tale, cu cote reale, pe care testezi modificările înainte să le execuți fizic." },
    ],
    related: [R.scor, R.twin, R.pret, R.impl, R.imob, R.ghidCost],
  },
  "3d": {
    cluster: "3d", tag: "3D & Digital Twin",
    h1: "Design interior 3D și randări realiste",
    title: "Design interior 3D: randări, releveu și Digital Twin | PropManage",
    description: "Vezi apartamentul tău în 3D înainte de execuție: randări realiste, releveu cu cote reale și Digital Twin care leagă designul de șantier.",
    intro: "Randările 3D transformă un plan tehnic în ceva ce poți înțelege imediat: cum arată lumina, cum se combină materialele, cum circuli prin spațiu. Iar când se bazează pe cote reale, devin mai mult decât o imagine — devin un instrument de decizie.",
    sections: [
      { h2: "De la releveu la randare", body: ["O randare utilă pornește de la măsurători corecte, nu de la un plan aproximativ."], bullets: ["Releveu / măsurători precise ale apartamentului", "Modelare 3D pe cotele reale", "Randări foto-realiste pe fiecare cameră", "Testarea materialelor și a culorilor în context"] },
      { h2: "Ce este Digital Twin", body: ["Digital Twin-ul este pasul următor al randării 3D: o replică digitală a locuinței tale, cu date reale, pe care testezi modificări, verifici încadrarea mobilierului și eviți greșelile scumpe. Vezi mai mult pe pagina Digital Twin."] },
      { h2: "De ce contează cotele reale", body: ["O randare frumoasă dar cu cote greșite induce în eroare. Măsurătorile corecte fac diferența dintre „arată bine în imagine” și „se potrivește pe șantier”."] },
    ],
    faq: [
      { q: "Randările 3D sunt exact ca rezultatul final?", a: "Când se bazează pe cote reale și materiale existente, sunt foarte apropiate. Diferențele apar când se folosesc obiecte generice, nu produsele efective." },
    ],
    related: [R.twin, R.hub, R.renovare, R.impl],
  },
  implementare: {
    cluster: "implementare", tag: "Implementare la cheie",
    h1: "Design interior cu implementare la cheie",
    title: "Design interior cu implementare: de la proiect la execuție | PropManage",
    description: "Design interior complet, cu implementare la cheie: proiect + management de execuție cu specialiști verificați și plăți protejate prin escrow.",
    intro: "Un proiect frumos rămâne pe hârtie dacă execuția nu îl respectă. „La cheie” înseamnă că cineva coordonează meseriile, materialele și calendarul, iar tu primești rezultatul din randare — nu o versiune improvizată pe șantier.",
    sections: [
      { h2: "Ce înseamnă „la cheie”", body: ["Implementarea completă acoperă drumul de la proiect la locuința gata de mutat:"], bullets: ["Proiect tehnic de execuție ca punct de plecare", "Echipe verificate pentru fiecare meserie", "Management de proiect și calendar", "Plăți în escrow, eliberate la finalizarea etapelor"] },
      { h2: "De ce escrow", body: ["Plata protejată prin escrow înseamnă că banii se eliberează pe etape acceptate, nu în avans total. Este cel mai important mecanism de siguranță pentru un client care nu vrea să rămână cu lucrarea neterminată."] },
      { h2: "Rolul specialiștilor verificați", body: ["Toate echipele din marketplace-ul PropManage sunt verificate și au recenzii reale. Poți vedea profilurile, portofoliile și evaluările înainte să accepți o ofertă."] },
    ],
    faq: [
      { q: "Trebuie să iau și designul de la voi ca să implementez?", a: "Nu neapărat. Poți veni cu un proiect existent, sau poți parcurge tot procesul, de la design la execuție, într-un singur loc." },
      { q: "Cum sunt protejați banii mei?", a: "Prin escrow: plătești pe etape, iar suma se eliberează specialistului doar după ce accepți lucrarea etapei respective." },
    ],
    related: [R.hub, R.pret, R.renovare, R.imob],
  },
  living: {
    cluster: "camere", tag: "Living",
    h1: "Design interior living",
    title: "Design interior living: amenajare, zonare și lumină | PropManage",
    description: "Amenajarea livingului: zona de relaxare, dining, depozitare și iluminat pe straturi. Idei care funcționează în apartamente și case din România.",
    intro: "Livingul este camera cu cel mai mare trafic și cea mai vizibilă. Un living reușit echilibrează trei zone — relaxare, dining și depozitare — și mizează pe un iluminat gândit pe mai multe straturi.",
    sections: [
      { h2: "Zonele unui living funcțional", body: ["Chiar și într-un spațiu deschis, delimitarea clară a zonelor face camera să funcționeze."], bullets: ["Zona de relaxare (canapea + TV / bibliotecă)", "Zona de dining, dacă e living deschis", "Depozitare care nu aglomerează vizual", "Iluminat: general + ambiental + accent"] },
      { h2: "Greșeli frecvente la living", body: ["Cele mai des întâlnite: o singură sursă de lumină centrală, canapea supradimensionată și lipsa unui punct focal clar."] },
    ],
    faq: [
      { q: "Cum fac un living mic să pară mai mare?", a: "Culori deschise, mobilier pe măsură, oglinzi bine plasate și iluminat pe straturi creează senzația de spațiu." },
    ],
    related: [R.apart, R.hub, R.d3],
  },
  bucatarie: {
    cluster: "camere", tag: "Bucătărie",
    h1: "Design interior bucătărie",
    title: "Design interior bucătărie: triunghiul de lucru și depozitare | PropManage",
    description: "Amenajarea bucătăriei: triunghiul de lucru, depozitare eficientă, instalații și finisaje ușor de întreținut. Soluții pentru bucătării mici și deschise.",
    intro: "Bucătăria este cel mai tehnic spațiu din locuință: aici designul se întâlnește direct cu instalațiile. O bucătărie bună respectă „triunghiul de lucru” (frigider – chiuvetă – plită) și oferă depozitare la îndemână.",
    sections: [
      { h2: "Principii de amenajare", body: ["O bucătărie eficientă se gândește în jurul fluxului de gătit și al depozitării."], bullets: ["Triunghiul de lucru frigider–chiuvetă–plită", "Blat suficient de lucru lângă plită și chiuvetă", "Depozitare până în tavan, sertare vs. uși", "Finisaje rezistente și ușor de curățat"] },
      { h2: "Instalații: gândite din start", body: ["Poziția prizelor, a evacuării și a hotei trebuie decisă în faza de proiect. Mutarea lor ulterioară este scumpă și dezordonată."] },
    ],
    faq: [
      { q: "Bucătărie deschisă sau închisă?", a: "Depinde de stil de viață și de posibilitatea tehnică de a deschide peretele. O bucătărie deschisă câștigă lumină, dar cere o hotă performantă." },
    ],
    related: [R.apart, R.hub, R.renovare],
  },
  dormitor: {
    cluster: "camere", tag: "Dormitor",
    h1: "Design interior dormitor",
    title: "Design interior dormitor: odihnă, depozitare și lumină caldă | PropManage",
    description: "Amenajarea dormitorului: pat corect poziționat, dressing sau depozitare, iluminat cald și confort acustic. Idei pentru dormitoare mici și matrimoniale.",
    intro: "Dormitorul are un singur obiectiv principal: odihna de calitate. Designul lui pune accent pe confort acustic, lumină caldă și o depozitare care ține camera ordonată.",
    sections: [
      { h2: "Ce contează într-un dormitor", body: ["Un dormitor bine gândit combină confortul cu depozitarea, fără să pară aglomerat."], bullets: ["Poziția patului față de ușă și fereastră", "Dressing sau șifonier până în tavan", "Iluminat cald, dimmabil, cu surse locale", "Textile și materiale care reduc zgomotul"] },
    ],
    faq: [
      { q: "Ce culori sunt potrivite pentru dormitor?", a: "Tonuri calde, neutre sau pastelate ajută odihna. Culorile foarte saturate se folosesc mai bine ca accente, nu pe suprafețe mari." },
    ],
    related: [R.apart, R.hub, R.d3],
  },
  baie: {
    cluster: "camere", tag: "Baie",
    h1: "Design interior baie",
    title: "Design interior baie: instalații, finisaje și spații mici | PropManage",
    description: "Amenajarea băii: hidroizolație, instalații corecte, finisaje rezistente la umezeală și soluții inteligente pentru băi mici.",
    intro: "Baia este spațiul cu cele mai multe cerințe tehnice pe metru pătrat: hidroizolație, instalații, ventilație. Un design reușit rezolvă întâi partea tehnică, apoi estetica.",
    sections: [
      { h2: "Partea tehnică, mai întâi", body: ["Într-o baie, greșelile tehnice se plătesc scump (infiltrații la vecini). De aceea ordinea corectă începe cu:"], bullets: ["Hidroizolație corectă înainte de finisaje", "Pante și scurgeri bine calculate", "Ventilație pentru a preveni mucegaiul", "Instalații (apă, canalizare) planificate din start"] },
      { h2: "Băi mici: soluții", body: ["La băile mici, cabina de duș fără cădiță, mobilierul suspendat și gresia de format mare creează senzația de spațiu."] },
    ],
    faq: [
      { q: "Cum previn mucegaiul în baie?", a: "Ventilație corectă (fereastră sau ventilator), hidroizolație bună și materiale potrivite. Vezi și ghidul nostru despre mucegai și igrasie." },
    ],
    related: [R.apart, R.hub, { to: "/probleme-casa/mucegai-igrasie", label: "Mucegai și igrasie: soluții" }],
  },
  birouri: {
    cluster: "comercial", tag: "Design birouri",
    h1: "Design interior birouri",
    title: "Design interior birouri: amenajare spații de lucru funcționale | PropManage",
    description: "Amenajarea birourilor: layout eficient, acustică, lumină, zone de colaborare și branding. Design de spații de lucru care cresc productivitatea, cu implementare la cheie.",
    intro: "Un birou bine gândit influențează direct productivitatea, starea de bine a echipei și imaginea firmei. Designul de birouri echilibrează concentrarea individuală cu colaborarea, într-un layout care susține modul real de lucru.",
    sections: [
      { h2: "Ce rezolvă designul de birouri", body: ["Un proiect de amenajare pentru birouri pornește de la modul în care lucrează echipa, nu de la mobilier."], bullets: ["Layout pe zone: concentrare, colaborare, ședințe, relaxare", "Acustică și reducerea zgomotului în open-space", "Lumină naturală și artificială corect dozată", "Integrarea identității vizuale a firmei", "Trasee logice și densitate optimă a posturilor"] },
      { h2: "Etape și implementare", body: ["Procesul urmează aceeași logică integrată: releveu, concept, proiect tehnic, randări și, opțional, implementare cu specialiști verificați și plată protejată prin escrow."] },
    ],
    faq: [
      { q: "Cât costă amenajarea unui birou?", a: "Se calculează pe metru pătrat și depinde de complexitate, acustică, mobilier și instalații. Un proiect tehnic clar previne costuri suplimentare la execuție." },
      { q: "Amenajați și spații de coworking sau birouri mici?", a: "Da, de la birouri mici și coworking la sedii de firmă. Proiectul se adaptează la numărul de posturi și la modul de lucru al echipei." },
    ],
    related: [R.hub, R.impl, R.d3, { to: "/design-interior/spatii-comerciale", label: "Design spații comerciale" }],
  },
  "spatii-comerciale": {
    cluster: "comercial", tag: "Design spații comerciale",
    h1: "Design interior spații comerciale",
    title: "Design spații comerciale: magazine, HoReCa, showroom-uri | PropManage",
    description: "Amenajarea spațiilor comerciale: magazine, restaurante, cafenele, showroom-uri. Design care crește experiența clientului și vânzările, cu implementare la cheie.",
    intro: "Într-un spațiu comercial, designul nu e doar estetică — este un instrument de vânzare. Un magazin, un restaurant sau un showroom bine amenajat ghidează clientul, comunică brandul și crește timpul petrecut și conversia.",
    sections: [
      { h2: "Ce rezolvă designul comercial", body: ["Un proiect pentru spații comerciale pornește de la experiența clientului și de la obiectivele de business."], bullets: ["Traseul clientului și dispunerea produselor sau a meselor", "Iluminat care pune în valoare produsele sau atmosfera", "Zonarea funcțională: expunere, casă, depozitare, servire", "Materiale rezistente la trafic intens", "Coerență cu identitatea de brand"] },
      { h2: "Etape și implementare", body: ["Releveu, concept, proiect tehnic, randări și, opțional, implementare la cheie cu specialiști verificați. Astfel, randarea corespunde cu ce se execută, iar plățile sunt protejate prin escrow."] },
    ],
    faq: [
      { q: "Amenajați magazine și spații HoReCa?", a: "Da — magazine, showroom-uri, cafenele și restaurante. Fiecare tip are cerințe proprii de flux, iluminat și materiale, tratate în proiectul tehnic." },
      { q: "Cât durează un proiect comercial?", a: "Depinde de suprafață și complexitate. Un concept vine rapid; proiectul tehnic complet și implementarea se planifică în funcție de amploarea lucrărilor." },
    ],
    related: [R.hub, R.impl, R.d3, { to: "/design-interior/birouri", label: "Design interior birouri" }],
  },
};

// ── Style pages (the REAL PropManage style system) ──────────────────────────
const style = (label, h1extra, description, intro, characteristics, spaces, materials, pros, cons, related) => ({
  cluster: "stil", tag: `Stil ${label}`,
  h1: `Design interior stil ${label}`,
  title: `Design interior stil ${label}: caracteristici, materiale și spații | PropManage`,
  description,
  intro,
  sections: [
    { h2: "Caracteristici", body: [`Stilul ${label} se recunoaște prin câteva trăsături clare.`], bullets: characteristics },
    { h2: "Pentru ce spații se potrivește", body: [spaces] },
    { h2: "Materiale, culori și forme", body: [materials] },
    { h2: "Avantaje și limitări", body: ["Ca orice stil, are puncte forte și compromisuri de luat în calcul."], bullets: [...pros.map(p => `Avantaj: ${p}`), ...cons.map(c => `De avut în vedere: ${c}`)] },
    { h2: "Cum abordează PropManage acest stil", body: [`La PropManage, stilul ${label} nu rămâne la nivel de moodboard: îl transformăm în proiect tehnic și, dacă vrei, în implementare cu specialiști verificați. Poți vedea abordarea reală a fiecărui designer în portofoliul lui, cu proiecte proprii — fără exemple inventate.`] },
  ],
  faq: [
    { q: `Stilul ${label} se potrivește apartamentelor mici?`, a: intro.includes("mic") ? "Da, cu adaptări." : `Da, cu adaptări: se păstrează principiile stilului ${label}, dar se ajustează scara mobilierului și paleta pentru spațiul disponibil.` },
  ],
  related: related || [{ to: "/design-interior", label: "Design interior" }, { to: "/design-interior/apartament", label: "Design apartament" }, { to: "/design-interior/3d", label: "Randări 3D" }],
});

export const DI_STYLES = {
  modern: style("modern", "", "Design interior stil modern: linii curate, funcționalitate și accente contemporane. Caracteristici, materiale și spații potrivite.", "Stilul modern mizează pe linii simple, funcționalitate și un decor lipsit de excese. Este cel mai versatil stil pentru apartamentele și casele contemporane din România.", ["Linii drepte, forme geometrice clare", "Paletă neutră cu accente puternice", "Suprafețe netede, minim decorativism", "Tehnologie integrată discret"], "Se potrivește aproape oricărui spațiu: apartamente noi, case contemporane, dar și apartamente vechi renovate.", "Alb, gri, negru și tonuri neutre, cu accente în culori tari sau materiale precum sticla, metalul și lemnul lucios.", ["Versatil și ușor de combinat", "Aspect curat, aerisit", "Se adaptează bugetelor variate"], ["Poate părea rece fără accente calde", "Cere ordine pentru a arăta bine"]),
  scandinavian: style("scandinav", "", "Design interior stil scandinav: lumină, lemn deschis și confort funcțional. Ideal pentru apartamente luminoase.", "Stilul scandinav (nordic) aduce lumină, căldură naturală și funcționalitate. Este foarte iubit în România pentru că face spațiile mici să pară mai mari și mai calde.", ["Paletă deschisă, alb + lemn natural", "Lumină naturală valorificată maxim", "Textile calde (lână, in)", "Funcționalitate și simplitate"], "Excelent pentru apartamente mici și medii, dar și pentru case care vor un aer cald și primitor.", "Alb, bej, gri deschis, lemn de mesteacăn/stejar deschis, textile naturale și verde din plante.", ["Face spațiile să pară mai mari și mai luminoase", "Cald și primitor", "Ușor de întreținut"], ["Paleta deschisă cere curățenie frecventă", "Poate deveni monoton fără texturi"]),
  minimalist: style("minimalist", "", "Design interior minimalist: mai puțin, dar mai bine. Ordine, depozitare ascunsă și linii pure.", "Minimalismul înseamnă „mai puțin, dar mai bine”: spații ordonate, depozitare ascunsă și obiecte alese cu grijă. Ideal pentru cine caută liniște vizuală.", ["Suprafețe libere, fără dezordine", "Depozitare integrată, ascunsă", "Paletă restrânsă", "Fiecare obiect are un rol"], "Perfect pentru cei care vor calm vizual; funcționează în orice suprafață dacă depozitarea e bine gândită.", "Neutre monocrome, o singură esență de lemn, materiale mate și texturi discrete.", ["Aspect calm, elegant, atemporal", "Ușor de întreținut vizual"], ["Cere disciplină de ordine", "Depozitarea ascunsă poate crește costul mobilierului"]),
  industrial: style("industrial", "", "Design interior industrial: cărămidă aparentă, metal și beton. Caracter puternic pentru spații generoase.", "Stilul industrial aduce caracter brut: cărămidă aparentă, metal, beton și instalații lăsate la vedere. Se potrivește spațiilor cu înălțime și lumină bună.", ["Materiale brute la vedere (beton, cărămidă, metal)", "Instalații expuse intenționat", "Paletă închisă, tonuri de gri și maro", "Mobilier robust"], "Ideal pentru loft-uri, apartamente cu tavane înalte și spații deschise generoase.", "Beton, cărămidă, metal negru, lemn masiv și piele, cu accente Edison la iluminat.", ["Caracter puternic, personalitate", "Rezistent și practic"], ["Poate părea rece", "Nu e ideal pentru spații mici sau întunecate"]),
  japandi: style("japandi", "", "Design interior stil Japandi: eleganța japoneză întâlnește confortul scandinav. Liniște, lemn și materiale naturale.", "Japandi combină minimalismul japonez cu căldura scandinavă: linii curate, materiale naturale și o atmosferă calmă, echilibrată. Este unul dintre cele mai căutate stiluri contemporane.", ["Echilibru între minimalism și căldură", "Materiale naturale și texturi", "Paletă calmă, pământie", "Mobilier jos, cu linii simple"], "Excelent pentru cei care vor liniște și rafinament; funcționează în apartamente și case deopotrivă.", "Lemn cald, tonuri pământii, negru mat pentru accente, in, bumbac și ceramică artizanală.", ["Atmosferă calmă, echilibrată", "Elegant și atemporal"], ["Necesită atenție la calitatea materialelor", "Cere ordine pentru efectul dorit"]),
  mediterranean: style("mediteranean", "", "Design interior stil mediteranean: lumină caldă, texturi naturale și un aer relaxat de vacanță.", "Stilul mediteranean aduce senzația de vacanță însorită: pereți texturați, tonuri calde, terracotta și materiale naturale. Este primitor și plin de viață.", ["Tonuri calde: teracotă, ocru, albastru", "Pereți texturați, tencuieli naturale", "Materiale naturale: piatră, lemn, ceramică", "Multe plante și lumină"], "Se potrivește caselor și apartamentelor luminoase, în special cu terase și spații care primesc soare.", "Terracotta, alb var, albastru marin, piatră naturală, lemn și ceramică pictată manual.", ["Cald, primitor, plin de viață", "Materiale naturale, durabile"], ["Paleta caldă nu place tuturor", "Anumite finisaje cer întreținere"]),
  classic: style("clasic", "", "Design interior stil clasic: proporții echilibrate, materiale nobile și eleganță atemporală.", "Stilul clasic mizează pe proporții echilibrate, simetrie, materiale nobile și detalii rafinate. Este alegerea celor care vor eleganță durabilă, nu tendințe trecătoare.", ["Simetrie și proporții echilibrate", "Detalii decorative (profiluri, lambriuri)", "Materiale nobile", "Paletă rafinată, sobră"], "Se potrivește apartamentelor spațioase și caselor unde se dorește un aer elegant, formal.", "Lemn masiv, marmură, textile bogate, tonuri crem, auriu și nuanțe profunde ca accent.", ["Elegant, atemporal", "Percepție de valoare ridicată"], ["Necesită spațiu pentru a respira", "Costuri mai mari la materiale și detalii"]),
  rustic: style("rustic", "", "Design interior stil rustic: lemn masiv, materiale naturale și căldură autentică de casă tradițională.", "Stilul rustic aduce căldura casei tradiționale: lemn masiv, piatră, materiale naturale și o atmosferă primitoare, autentică. Ideal pentru case și cabane.", ["Lemn masiv la vedere", "Materiale naturale, texturi brute", "Tonuri calde, pământii", "Obiecte handmade, autentice"], "Perfect pentru case, cabane și spații care vor o atmosferă caldă, tradițională.", "Lemn masiv, piatră naturală, fier forjat, textile naturale și tonuri de maro, verde și crem.", ["Cald, autentic, primitor", "Materiale durabile"], ["Mai greu de aplicat în apartamente moderne mici", "Lemnul masiv cere întreținere"]),
  boho: style("boho", "", "Design interior stil boho: culoare, texturi mixte și personalitate liberă. Un stil expresiv și relaxat.", "Stilul boho (bohemian) este expresiv și liber: amestecă texturi, culori și obiecte cu poveste. Este pentru cei care vor personalitate, nu reguli stricte.", ["Amestec de texturi și modele", "Culori calde și naturale", "Multe plante și obiecte handmade", "Atmosferă relaxată, liberă"], "Se potrivește celor care vor un spațiu personal, plin de caracter; funcționează bine în apartamente luminoase.", "Textile naturale, ratan, macrame, lemn, plante și o paletă caldă cu accente colorate.", ["Personal, cald, plin de viață", "Permite obiecte cu poveste"], ["Poate deveni aglomerat fără echilibru", "Cere gust pentru a nu părea dezordonat"]),
};

export const DI_LOCAL_CITIES = {
  bucuresti: "București", "cluj-napoca": "Cluj-Napoca", brasov: "Brașov",
  oradea: "Oradea", timisoara: "Timișoara", sibiu: "Sibiu", iasi: "Iași",
  floresti: "Florești (Cluj)", baciu: "Baciu (Cluj)", apahida: "Apahida (Cluj)",
  "marasti-cluj": "Mărăști (Cluj-Napoca)", "gheorgheni-cluj": "Gheorgheni (Cluj-Napoca)",
  baneasa: "Băneasa (București)", otopeni: "Otopeni (Ilfov)", corbeanca: "Corbeanca (Ilfov)",
  buftea: "Buftea (Ilfov)", balotesti: "Balotești (Ilfov)",
};

export const getDesignPage = (slug) => DI_PAGES[slug] || null;
export const getDesignStyle = (slug) => DI_STYLES[slug] || null;
