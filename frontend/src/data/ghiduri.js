// Evergreen guide articles — Romanian SEO content for high-volume queries.
// Each article: ~800-1500 words, targets a specific search intent, includes
// FAQ block (drives Google FAQ rich snippets) + 8-12 internal links to
// /marketplace landing pages.
//
// Structure per article:
//   slug, title, h1, description, hero (icon+tag), publishedAt, updatedAt,
//   readMins, sections[{ heading, body[] }], faq[{ q, a }], relatedCity,
//   relatedCategories[], internalLinks[{ label, to }]
//
// Body items: strings (paragraph), or { type: "list", items: [] },
//             or { type: "callout", title, body }

export const GHIDURI = [
  {
    slug: "ce-este-designul-interior",
    title: "Ce este designul interior? Rol, etape și beneficii · Ghid 2026",
    h1: "Ce este designul interior și de ce contează",
    description: "Ce înseamnă designul interior, ce face concret un designer, care sunt etapele unui proiect și când merită să apelezi la unul. Explicat clar, fără jargon.",
    tag: "Bazele designului",
    icon: "BookOpen",
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    readMins: 6,
    sections: [
      {
        heading: "Definiție simplă",
        body: [
          "Designul interior este procesul prin care un spațiu locuibil este planificat astfel încât să fie **funcțional, confortabil și coerent estetic**. Nu înseamnă doar „să arate frumos” — înseamnă decizii despre circulație, lumină, depozitare, materiale și buget, transformate într-un plan care poate fi executat.",
          { type: "callout", title: "Pe scurt", body: "Un designer bun rezolvă mai întâi problemele de funcționalitate (cum folosești spațiul), apoi pe cele estetice (cum arată)." },
        ],
      },
      {
        heading: "Ce face concret un designer de interior",
        body: [
          "Rolul depășește alegerea culorilor. Un proiect complet include:",
          { type: "list", items: [
            "Releveu și analiza spațiului (cote reale, lumină, instalații)",
            "Plan de mobilare optimizat pe circulație și depozitare",
            "Concept vizual și randări 3D",
            "Planuri tehnice pentru echipele de execuție",
            "Listă de materiale și obiecte pentru bugetare corectă",
          ] },
        ],
      },
      {
        heading: "Când merită să apelezi la un designer",
        body: [
          "Designul aduce cea mai mare valoare la renovări și la spații mici sau atipice, unde greșelile costă mult. Chiar și un simplu concept poate preveni cumpărături greșite de mii de lei.",
          "La PropManage, procesul leagă designul de execuția reală: Design → Audit → Digital Twin → Proiectare → Implementare, cu specialiști verificați și plăți protejate prin escrow.",
        ],
      },
    ],
    faq: [
      { q: "Designul interior este scump?", a: "Depinde de ce incluzi. Un concept costă puțin; un proiect tehnic complet costă mai mult, dar economisește bani pe șantier prin evitarea greșelilor. Vezi pagina de preț pentru factorii reali." },
      { q: "Care e diferența dintre design interior și decorare?", a: "Decorarea se ocupă doar de aspect (textile, obiecte, culori). Designul interior include și partea funcțională și tehnică a spațiului." },
    ],
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Design interior — pagina principală", to: "/design-interior" },
      { label: "Cât costă designul interior", to: "/design-interior/pret" },
      { label: "Ce include un proiect de design", to: "/ghiduri/ce-include-un-proiect-de-design-interior" },
      { label: "Cum alegi un designer interior", to: "/ghiduri/cum-alegi-designer-interior" },
    ],
  },
  {
    slug: "design-interior-sau-arhitect",
    title: "Design interior sau arhitect? Ce alegi și când · Ghid 2026",
    h1: "Design interior sau arhitect: de care ai nevoie?",
    description: "Când ai nevoie de un designer de interior și când de un arhitect? Diferențele de rol, ce poate face fiecare și cum lucrează împreună la o renovare.",
    tag: "Comparație",
    icon: "Users",
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    readMins: 6,
    sections: [
      {
        heading: "Diferența de rol",
        body: [
          "Cei doi profesioniști se completează, dar au responsabilități diferite:",
          { type: "list", items: [
            "**Arhitectul** se ocupă de structură, autorizații, modificări de anvelopă și conformitate legală. Este obligatoriu pentru intervenții structurale.",
            "**Designerul de interior** se ocupă de organizarea și amenajarea spațiului interior: funcțiune, mobilare, finisaje, lumină, atmosferă.",
          ] },
        ],
      },
      {
        heading: "Când ai nevoie de arhitect",
        body: [
          "Ai nevoie de arhitect (și, adesea, de expert tehnic) când intervii asupra structurii: demolezi pereți portanți, modifici fațada, extinzi sau schimbi funcțiunea. Aceste lucrări cer proiect și autorizație.",
          { type: "callout", title: "Atenție", body: "Demolarea unui perete structural fără expertiză este periculoasă și ilegală. Un audit sau un Digital Twin cu releveu clarifică ce se poate demola în siguranță." },
        ],
      },
      {
        heading: "Când e suficient un designer",
        body: [
          "Pentru majoritatea amenajărilor de apartament fără modificări structurale, un designer de interior acoperă tot ce ai nevoie: reorganizare, mobilare, finisaje, iluminat și coordonarea execuției.",
        ],
      },
    ],
    faq: [
      { q: "Pot lucra amândoi la același proiect?", a: "Da, și adesea este ideal: arhitectul rezolvă structura și autorizațiile, designerul se ocupă de interior. La PropManage găsești ambele tipuri de specialiști verificați." },
      { q: "Cine decide dacă un perete e structural?", a: "Un inginer/expert tehnic, pe baza proiectului clădirii. Un audit tehnic sau Digital Twin te ajută să identifici din timp aceste aspecte." },
    ],
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "Scorul casei (audit tehnic)", to: "/scorul-casei" },
      { label: "Ce este un Digital Twin", to: "/ghiduri/ce-este-digital-twin-locuinta" },
      { label: "Design interior — pagina principală", to: "/design-interior" },
    ],
  },
  {
    slug: "ce-include-un-proiect-de-design-interior",
    title: "Ce include un proiect de design interior? Livrabile · Ghid 2026",
    h1: "Ce include un proiect de design interior",
    description: "Ce primești concret dintr-un proiect de design interior: de la moodboard și plan de mobilare, la randări 3D, planuri tehnice și listă de materiale. Ce să ceri și ce să verifici.",
    tag: "Livrabile",
    icon: "FileText",
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    readMins: 7,
    sections: [
      {
        heading: "Livrabilele unui proiect complet",
        body: [
          "Un proiect serios de design interior nu este o singură imagine, ci un set de documente pe care echipa de execuție le poate urma:",
          { type: "list", items: [
            "**Concept și moodboard** — direcția de stil și paleta",
            "**Plan de mobilare** la scară, cu cote",
            "**Randări 3D** foto-realiste pe fiecare cameră",
            "**Planuri tehnice** — electrice, sanitare, tavane, pardoseli, finisaje",
            "**Listă de materiale și obiecte** cu cantități și specificații",
          ] },
        ],
      },
      {
        heading: "Concept vs. proiect tehnic complet",
        body: [
          "Un „concept” (moodboard + plan de mobilare) este suficient dacă vrei doar direcția. Pentru o renovare reală ai nevoie de proiectul tehnic complet, altfel echipele improvizează pe șantier — de acolo vin întârzierile și costurile suplimentare.",
        ],
      },
      {
        heading: "Ce să verifici înainte să accepți o ofertă",
        body: [
          "Cere lista exactă a livrabilelor, numărul de revizii incluse și dacă proiectul acoperă și partea de instalații. Vezi și cum se structurează prețul.",
        ],
      },
    ],
    faq: [
      { q: "Câte revizii ar trebui incluse?", a: "De obicei 1-2 revizii pe concept sunt normale. Clarifică din start câte sunt incluse și cât costă cele suplimentare." },
      { q: "Proiectul include și lista de cumpărături?", a: "Un proiect complet include o listă de materiale și obiecte cu cantități, care îți permite să bugetezi corect." },
    ],
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Preț design interior", to: "/design-interior/pret" },
      { label: "Design cu implementare la cheie", to: "/design-interior/implementare" },
      { label: "Randări 3D & Digital Twin", to: "/design-interior/3d" },
      { label: "Design interior — pagina principală", to: "/design-interior" },
    ],
  },
  {
    slug: "de-ce-conteaza-masuratorile-inainte-de-design",
    title: "De ce contează măsurătorile înainte de design interior · Ghid 2026",
    h1: "De ce contează măsurătorile înainte de designul interior",
    description: "Un releveu precis face diferența dintre un proiect care se execută fidel și unul plin de surprize. Ce se măsoară, de ce și cum ajută un Digital Twin.",
    tag: "Releveu & măsurători",
    icon: "Ruler",
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    readMins: 6,
    sections: [
      {
        heading: "Cea mai frecventă greșeală de pe șantier",
        body: [
          "Mobilierul sau finisajele comandate care „nu încap” sunt cel mai des rezultatul unor măsurători aproximative. Pereții nu sunt niciodată perfect drepți, iar câțiva centimetri decid dacă o piesă se montează sau nu.",
          { type: "callout", title: "Regula de aur", body: "Măsoară de două ori, comandă o dată. Un releveu profesionist elimină aproape complet acest risc." },
        ],
      },
      {
        heading: "Ce se măsoară într-un releveu",
        body: [
          { type: "list", items: [
            "Dimensiunile exacte ale fiecărei camere (inclusiv abateri)",
            "Înălțimi, praguri, poziția ușilor și ferestrelor",
            "Poziția instalațiilor (prize, țevi, calorifere, coloane)",
            "Elemente fixe (stâlpi, grinzi, nișe)",
          ] },
        ],
      },
      {
        heading: "Cum ajută un Digital Twin",
        body: [
          "Un Digital Twin este o replică digitală a locuinței, cu cote reale, pe care testezi modificările înainte să le execuți fizic. Astfel verifici încadrarea mobilierului și circulația luminii fără să riști bani pe comenzi greșite.",
        ],
      },
    ],
    faq: [
      { q: "Nu pot măsura singur?", a: "Poți face o estimare, dar pentru comenzi de mobilier pe comandă și pentru proiectul tehnic ai nevoie de un releveu precis, ideal profesionist." },
      { q: "Digital Twin-ul înlocuiește releveul?", a: "Nu, îl include: un Digital Twin bun se construiește pe baza unui releveu precis al locuinței tale." },
    ],
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Randări 3D & Digital Twin", to: "/design-interior/3d" },
      { label: "Ce este un Digital Twin", to: "/ghiduri/ce-este-digital-twin-locuinta" },
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "Digital Twin locuință", to: "/digital-twin" },
    ],
  },
  {
    slug: "cost-renovare-apartament-2-camere",
    title: "Cât costă o renovare apartament 2 camere în România · Ghid 2026",
    h1: "Cât costă o renovare apartament 2 camere în 2026",
    description: "Buget real pentru renovarea unui apartament 2 camere (50-60 mp) în România: prețuri actualizate 2026 pe categorii (electric, sanitar, zugrăveli, parchet). Calculator + checklist.",
    tag: "Cost & Buget",
    icon: "Calculator",
    publishedAt: "2026-02-15",
    updatedAt: "2026-02-29",
    readMins: 9,
    sections: [
      {
        heading: "Răspuns scurt: buget mediu 2026",
        body: [
          "În 2026, o renovare completă a unui apartament cu 2 camere (50-60 mp) în România costă între **18.000 și 45.000 RON**, în funcție de oraș, standard de finisaje și amploarea intervențiilor structurale. Iată cum se împart costurile pe categorii.",
          {
            type: "callout",
            title: "Estimare rapidă",
            body: "Pentru un apartament 2 camere de 55 mp, cu finisaje de calitate medie și fără modificări structurale: buget realist ~28.000 RON manoperă + materiale, fără mobilier."
          }
        ]
      },
      {
        heading: "Defalcare pe categorii de lucrări (50-60 mp)",
        body: [
          "Cifrele de mai jos sunt valori medii observate pe platforma PropManage pentru lucrări finalizate în București, Cluj-Napoca, Timișoara și Iași în T4 2025 și T1 2026. Prețurile includ atât manoperă cât și materiale, însă pot varia ±20% în funcție de calitatea materialelor alese.",
          {
            type: "list",
            items: [
              "**Instalație electrică** (refăcută complet, tablou nou, 12-15 circuite): 4.500-7.500 RON",
              "**Instalație sanitară** (țevi PEX noi, robineți, sifoane, racorduri): 3.000-5.500 RON",
              "**Tencuieli și gleturi** (pereți reparați + pregătire zugrăveală): 2.500-4.500 RON",
              "**Zugrăveli interior** (lavabile premium, 2 mâini, plafoane incluse): 2.200-4.000 RON",
              "**Parchet laminat sau triplu-stratificat** (incl. plinte, prag): 3.500-7.500 RON",
              "**Faianță + gresie baie + bucătărie** (manoperă + adezivi, fără finisaje premium): 2.800-5.000 RON",
              "**Uși interioare noi** (3 bucăți, MDF foliat, montaj inclus): 1.800-3.500 RON",
              "**Curățenie post-construcție**: 600-1.200 RON",
            ]
          },
          "**Total mediu**: ~21.000-38.500 RON pentru un apartament 2 camere standard, fără modificări structurale și fără mobilier nou."
        ]
      },
      {
        heading: "Factori care cresc bugetul",
        body: [
          "Există câteva intervenții care pot crește semnificativ bugetul de bază. Iată ce să anticipezi:",
          {
            type: "list",
            items: [
              "**Demolare ziduri interioare** (open-space): +2.500-4.500 RON (necesită expertiză tehnică pentru zid portant!)",
              "**Mutare obiecte sanitare** (relocare bucătărie sau baie): +3.000-6.000 RON",
              "**Aer condiționat** (2 unități split, instalație ascunsă): +3.500-5.500 RON",
              "**Tâmplărie PVC nouă** (4-5 ferestre, geam termopan): +6.500-12.000 RON",
              "**Termoizolație suplimentară** (rigips + vată minerală pe pereți reci): +2.500-4.000 RON",
              "**Design interior profesionist** (concept + plan execuție + asistență shopping): 6.000-15.000 RON",
            ]
          }
        ]
      },
      {
        heading: "Cum economisești fără să compromiti calitatea",
        body: [
          "**1. Cere minim 3 oferte detaliate.** Diferența între cea mai mică și cea mai mare ofertă pentru aceeași lucrare poate fi de 40-60%. Pe PropManage primești automat 3-5 oferte de la specialiști verificați în 24h.",
          "**2. Negociază pachetul, nu fiecare punct.** Un specialist care primește toate lucrările (electric + sanitar + zugrăveală) îți va reduce mai ușor 10-15% decât dacă te tocmești pe fiecare categorie.",
          "**3. Cumpără tu materialele scumpe.** Parchet, faianță, gresie premium — diferența între prețul de la magazin și prețul taxat de specialist poate fi 25-40%. Specialistul oferă doar manoperă + consumabile.",
          "**4. Programează lucrările iarna.** Specialiștii buni au calendare full vara. Iarna (decembrie-februarie) primești prețuri cu 10-15% mai mici și execuție mai rapidă.",
          "**5. Plătește prin escrow.** Banii rămân blocați pe platformă până confirmi finalizarea. Elimini riscul de a plăti înainte și apoi a fi abandonat la jumătate de lucrare."
        ]
      },
      {
        heading: "Diferențe de preț pe orașe",
        body: [
          "Bugetul total pentru aceeași lucrare diferă cu **15-25%** între orașele mari din România. Iată tendințele 2026:",
          {
            type: "list",
            items: [
              "**București + Cluj-Napoca**: cele mai scumpe, +10-15% peste media națională",
              "**Timișoara + Iași + Brașov**: la media națională",
              "**Sibiu + Oradea + Constanța**: -5-10% sub media națională",
              "**Galați + Craiova + Ploiești**: -10-15% sub media națională"
            ]
          },
          "Această variație reflectă atât diferențe în costurile de viață cât și în concurența locală dintre specialiști."
        ]
      }
    ],
    faq: [
      {
        q: "Cât durează o renovare completă apartament 2 camere?",
        a: "În medie 4-6 săptămâni pentru o renovare standard (fără modificări structurale). Dacă se demolează ziduri sau se mută bucătăria/baia, durata crește la 8-10 săptămâni. Iarna lucrările merg mai repede (specialiștii nu sunt aglomerați)."
      },
      {
        q: "Trebuie să mă mut în timpul renovării?",
        a: "Da, pentru renovări complete (electric + sanitar + finisaje) recomandăm să te muți pentru cel puțin 3-4 săptămâni. Praful și mirosul de vopsea/adezivi fac apartamentul impracticabil. Pentru renovări parțiale (doar finisaje cosmetice) se poate locui zonal."
      },
      {
        q: "Pot să-mi renovez apartamentul fără autorizație?",
        a: "Pentru lucrări interioare care NU afectează structura (zugrăveli, parchet, înlocuit baie/bucătărie, instalații în pereți existenți) nu ai nevoie de autorizație. Pentru orice intervenție pe ziduri portante, balcoane sau modificări de fațadă ai nevoie obligatoriu de autorizație de construire de la primărie."
      },
      {
        q: "Cât costă designul interior pentru un apartament 2 camere?",
        a: "Un concept de design interior profesionist pentru un apartament 2 camere costă între 6.000 și 15.000 RON, în funcție de complexitate. Include randări 3D, planuri tehnice, listă completă de materiale și asistență la shopping. Pe PropManage prețul standard este 2.200 RON/cameră pentru faza de concept."
      },
      {
        q: "Specialiștii de pe PropManage dau garanție pe lucrare?",
        a: "Da, fiecare specialist verificat oferă garanție minimă de 12 luni pentru manoperă. În plus, plata se face prin escrow — banii rămân blocați pe platformă timp de 7 zile după predarea lucrării, perioadă în care poți semnala probleme și obține remediere gratuită."
      }
    ],
    relatedCity: null,
    relatedCategories: ["zugrav", "instalator", "electrician", "tamplar"]
  },

  {
    slug: "cum-alegi-designer-interior",
    title: "Cum alegi un designer interior bun · Ghid complet 2026",
    h1: "Cum alegi un designer interior pentru apartamentul tău",
    description: "Ghid pas-cu-pas: cum verifici portofoliul, cum negociezi tariful, ce contract semnezi și cum eviți cele 5 greșeli costisitoare la angajarea unui designer interior în 2026.",
    tag: "Decizie & Sfaturi",
    icon: "Palette",
    publishedAt: "2026-02-10",
    updatedAt: "2026-02-29",
    readMins: 8,
    sections: [
      {
        heading: "De ce contează alegerea designerului",
        body: [
          "Un designer interior bun nu doar îți face apartamentul frumos — îți economisește **mii de RON** prin evitarea greșelilor de execuție și prin negocierea profesionistă cu furnizorii. Un designer slab poate, dimpotrivă, să te coste 20-30% peste buget și să te lase cu un rezultat care arată bine doar în randări.",
          "Acest ghid te ajută să faci alegerea corectă din prima încercare."
        ]
      },
      {
        heading: "Pasul 1: Verifică portofoliul, nu vorbele",
        body: [
          "Cere să vezi minim **5 proiecte finalizate** ale designerului, fiecare cu poze înainte/după. Atenție la:",
          {
            type: "list",
            items: [
              "**Stiluri variate sau un singur stil repetat?** Un designer versatil se adaptează gusturilor tale. Unul care face mereu același stil te va împinge spre estetica lui, nu a ta.",
              "**Pozele sunt randări 3D sau realizări reale?** Cere fotografii din apartamente locuite, nu doar imagini de catalog.",
              "**Detaliile fac diferența.** Uită-te la îmbinări parchet-perete, la fugile faianței, la cum sunt poziționate prizele. Aici se vede dacă designerul gândește execuția sau doar estetica.",
              "**Referințe de la clienți precedenți.** Cere 2-3 numere de telefon ale clienților ale căror apartamente le-a făcut și sună-i pentru a întreba despre experiență."
            ]
          }
        ]
      },
      {
        heading: "Pasul 2: Înțelege ce primești pentru bani",
        body: [
          "Un proiect complet de design interior include 3 faze distincte. Verifică ce intră în prețul oferit:",
          {
            type: "list",
            items: [
              "**Faza 1 — Concept**: 2-3 variante de moodboard, plan general, randări 3D pentru fiecare cameră. Tarif standard: 2.200 RON/cameră.",
              "**Faza 2 — Plan tehnic execuție**: planuri detaliate pentru toate trade-urile (electric, sanitar, mobilier custom), listă completă materiale cu cantități, schițe de detaliu. Tarif: 1.500-3.000 RON pentru un apartament 2-3 camere.",
              "**Faza 3 — Asistență execuție**: vizite săptămânale pe șantier, comunicare cu specialiștii, achiziție materiale, ajustări on-site. Tarif: 10-15% din valoarea totală a lucrărilor."
            ]
          },
          "**ATENȚIE**: Un designer care îți cere doar 1.500 RON pentru tot apartamentul fie are surprize ascunse, fie nu va livra plan tehnic real."
        ]
      },
      {
        heading: "Pasul 3: Negociază contractul corect",
        body: [
          "Înainte de a semna, asigură-te că în contract sunt prevăzute explicit:",
          {
            type: "list",
            items: [
              "**Termene clare** pentru fiecare fază (ex: concept livrat în max 14 zile de la plata avansului)",
              "**Numărul de revizii incluse** (standard: 2 revizii la concept, 1 revizie la planul tehnic)",
              "**Cine cumpără materialele** și cine păstrează discount-urile de la furnizori (insistă să primești tu reducerile)",
              "**Plata pe faze**, nu integral la început (ideal: 30% avans, 40% la concept aprobat, 30% la livrare finală)",
              "**Penalități pentru întârziere** (minim 1% din valoarea contractului pe săptămână de întârziere)"
            ]
          }
        ]
      },
      {
        heading: "5 greșeli costisitoare de evitat",
        body: [
          "**1. Plata integrală la început.** Niciodată. Plătește pe etape, condiționat de livrabile.",
          "**2. Lipsa unui plan tehnic scris.** Dacă designerul doar îți arată randări fără planuri cu cote, vei avea probleme grave la execuție.",
          "**3. Alegerea pe baza prețului cel mai mic.** Diferența între un designer ieftin și unul bun se materializează în calitatea execuției. O greșeală de design (ex: traseu electric greșit) poate costa 5.000-10.000 RON la refacere.",
          "**4. Schimbări frecvente după aprobarea conceptului.** Fiecare modificare după aprobare are cost suplimentar. Decide-te înainte.",
          "**5. Lipsa unui contract scris.** Toate detaliile (preț, livrabile, termene, penalități) trebuie pe hârtie. Înțelegeri verbale = riscuri."
        ]
      }
    ],
    faq: [
      {
        q: "Cât costă un designer interior pentru un apartament 3 camere în 2026?",
        a: "Pentru un apartament 3 camere (60-80 mp), un proiect complet de design interior costă între 9.000 și 18.000 RON. Include concept (2.200 RON/cameră × 4 spații = ~8.800 RON), plan tehnic (~2.500 RON) și asistență execuție opțională (10-15% din valoarea lucrărilor)."
      },
      {
        q: "Pot face designul singur fără un profesionist?",
        a: "Pentru ajustări cosmetice (vopsele, mobilier mic) — da, sunt suficiente aplicații gratuite ca IKEA Place sau Planner 5D. Pentru renovări complete cu modificări de electric, sanitar sau zidărie — nu, riscul de greșeli costisitoare este foarte mare. Un designer recuperează tariful prin economiile pe care le face la materiale și execuție."
      },
      {
        q: "Cât durează realizarea unui proiect de design interior?",
        a: "Faza de concept (moodboard + randări 3D): 2-3 săptămâni. Plan tehnic detaliat: 1-2 săptămâni suplimentare. Așadar de la prima întâlnire la planuri gata de execuție: 4-6 săptămâni. Execuția propriu-zisă: 4-10 săptămâni în funcție de amploare."
      },
      {
        q: "Designerul cumpără materialele sau eu?",
        a: "Ambele variante sunt valide. Dacă cumpără el, beneficiezi de discount-urile pe care le are la furnizori (-15-25% față de prețul magazinului), însă plătești o taxă de management de 5-10%. Dacă cumperi tu, ai control total și transparență, dar trebuie să te ocupi tu de logistica achizițiilor. Soluție hibridă: el livrează lista detaliată, tu cumperi de la furnizorii săi recomandați."
      },
      {
        q: "Cum verific dacă un designer este verificat pe PropManage?",
        a: "Pe profilul fiecărui designer apare badge-ul \"VERIFIED\" (lime, cu bifă) dacă echipa noastră i-a validat documentele de identitate, certificările profesionale și asigurarea de răspundere civilă. Suplimentar vezi rating-ul real bazat pe recenzii de la clienți care au plătit prin platformă."
      }
    ],
    relatedCity: null,
    relatedCategories: ["design-interior", "tamplar", "zugrav"]
  },

  {
    slug: "cum-verifici-instalator",
    title: "Cum verifici un instalator înainte să-l angajezi · 2026",
    h1: "Cum verifici un instalator înainte să-l angajezi",
    description: "Checklist complet: documente obligatorii, semne că ai de-a face cu un escroc, cum negociezi prețul fix și cum eviți cele 7 capcane clasice la angajarea unui instalator în 2026.",
    tag: "Verificare & Siguranță",
    icon: "ShieldCheck",
    publishedAt: "2026-02-08",
    updatedAt: "2026-02-29",
    readMins: 7,
    sections: [
      {
        heading: "De ce contează verificarea",
        body: [
          "Conform datelor ANPC din 2025, **1 din 4 reclamații** primite în domeniul lucrărilor de construcții vizează instalatori. Cele mai frecvente probleme: lucrări abandonate la jumătate, scurgeri apărute la 2-3 săptămâni după finalizare, prețuri umflate la final față de oferta inițială.",
          "Verificarea corectă te salvează de 90% din aceste probleme."
        ]
      },
      {
        heading: "Documente obligatorii pe care trebuie să le ceri",
        body: [
          "Înainte de a începe orice lucrare, instalatorul trebuie să-ți prezinte:",
          {
            type: "list",
            items: [
              "**Carte de identitate** (foto la nume + CNP — verifici că persoana din față e cea cu care vorbești)",
              "**Certificat fiscal sau PFA activ** (poți verifica gratuit pe portal.onrc.ro că firma există și e activă)",
              "**Polița de răspundere civilă profesională** (obligatorie pentru orice intervenție serioasă — acoperă pagubele dacă strică ceva)",
              "**Certificat de calificare** (curs absolvit, autorizație ANRE pentru instalații de gaz, ISCIR pentru centrale termice)",
              "**Minim 3 referințe** (clienți precedenți cu telefon, pe care îi poți suna direct)"
            ]
          },
          {
            type: "callout",
            title: "Semn de alarmă",
            body: "Dacă instalatorul refuză să-ți arate aceste documente sau spune \"nu am la mine acum, ți le aduc data viitoare\", **NU începe lucrarea**. Caută pe altcineva."
          }
        ]
      },
      {
        heading: "Cele 7 capcane clasice și cum le eviți",
        body: [
          "**1. \"Plătește jumătate acum, restul la final.\"** Plătești cel mult 30% avans, iar restul la finalizare verificată. Niciodată jumătate sau mai mult. Cu plata escrow PropManage banii rămân blocați și sunt eliberați doar după confirmarea ta.",
          "**2. \"Materialele le aduc eu, e mai bine pentru tine.\"** De multe ori instalatorul aduce materiale ieftine și îți facturează la preț de premium. Cere chitanțele pe nume tău sau cumpără tu materialele esențiale.",
          "**3. \"Prețul este orientativ, vedem la final.\"** Niciodată. Cere oferta SCRISĂ cu preț FIX pe lucrare, sau pe oră dacă e intervenție mică. Schimbările apar doar dacă tu ceri lucrări suplimentare.",
          "**4. \"Lucrăm fără bon/factură, mai ieftin.\"** Sună tentant, dar fără factură nu ai dovada lucrării și pierzi orice drept de reclamație. În plus, nu poți beneficia de TVA dedus dacă ești firmă.",
          "**5. \"Nu vă faceți griji, am 20 de ani experiență.\"** Vorbele nu contează. Cere referințe concrete și sună-le. Un instalator real va fi mândru să le ofere.",
          "**6. \"Lucrăm acum, semnăm contract mai târziu.\"** Contractul SE SEMNEAZĂ ÎNAINTE de prima lovitură de cazma. Trebuie să conțină prețul, termenele, garanția, materialele.",
          "**7. \"Pot să fac și gaz, e simplu.\"** Pentru orice intervenție pe instalație de gaz, este obligatorie autorizația ANRE. O lucrare neautorizată poate explica un dosar penal după o explozie. Verifică AUTORIZAȚIA, nu doar \"experiența\"."
        ]
      },
      {
        heading: "Întrebări de pus la prima întâlnire",
        body: [
          "Aceste 5 întrebări îți spun rapid dacă ai în față un profesionist sau un amator:",
          {
            type: "list",
            items: [
              "**\"Câte zile durează lucrarea și ce condiționează termenul?\"** — un profesionist îți va spune exact + factorii care pot întârzia (livrare materiale, surprize tehnice)",
              "**\"Ce garanție îmi oferi în scris?\"** — minim 12 luni pentru manoperă, scrisă în contract",
              "**\"Ce se întâmplă dacă apare o scurgere la o lună după finalizare?\"** — răspuns corect: \"vin gratuit și remediez\". Răspuns greșit: \"te taxez intervenția\"",
              "**\"Cumperi tu materialele sau eu?\"** — orice variantă e ok, dar răspunsul trebuie să fie clar și prețurile transparente",
              "**\"Pot să văd 2 lucrări recente ale tale?\"** — un profesionist real te poate trimite la 2 clienți pe care ai voie să-i suni"
            ]
          }
        ]
      }
    ],
    faq: [
      {
        q: "Cum verific dacă un instalator are autorizație ANRE?",
        a: "Intri pe site-ul ANRE (anre.ro), secțiunea \"Operatori autorizați\", și cauți după nume sau CIF. Dacă persoana sau firma este autorizată, va apărea în registrul public împreună cu tipul de autorizație (montaj sau verificare instalație gaz). Pentru orice lucrare la centrala termică sau țevile de gaz, autorizația este OBLIGATORIE prin lege."
      },
      {
        q: "Cât costă o intervenție de urgență (scurgere) în 2026?",
        a: "Pentru o intervenție de urgență (24h) — diagnostic + remediere scurgere — costul mediu în România în 2026 este 250-450 RON, în funcție de oraș și complexitate. Diagnosticul singur (vizită + identificare problemă, fără reparație) costă 100-180 RON. Atenție la firme care percep \"taxa de deplasare\" suplimentară — întreabă întotdeauna prețul total ÎNAINTE de vizită."
      },
      {
        q: "Ce fac dacă instalatorul abandonează lucrarea la jumătate?",
        a: "Dacă ai plătit prin escrow PropManage, banii sunt blocați și nu se eliberează decât după confirmarea ta. Deschizi o dispută din contul tău, echipa noastră intervine în 48h și fie obligă specialistul să finalizeze, fie îți rambursează banii și îți alocă alt specialist. În afara platformei, ai opțiunea reclamației la ANPC + acțiune în instanță, dar procesul durează 6-12 luni."
      },
      {
        q: "Pot să schimb singur un robinet sau să remediez o scurgere simplă?",
        a: "Pentru lucrări minore (înlocuire robinet de chiuvetă, sifon, garnituri) — da, există tutoriale și nu necesită autorizație. Pentru orice intervenție pe instalația de gaz sau pentru schimbarea boilerului — NU, este ilegal și extrem de periculos. Costul unei vieți este mai mare decât 300 RON de manoperă."
      },
      {
        q: "Cât costă în medie un instalator pe oră în 2026?",
        a: "Tariful orar mediu al unui instalator verificat în România în 2026 este 80-150 RON/oră, în funcție de oraș și complexitate. București și Cluj sunt la capătul superior (120-150 RON/h), orașele mai mici la 80-110 RON/h. Pentru lucrări complete (instalație apartament) se negociază preț per lucrare, nu per oră — cere ofertă scrisă."
      }
    ],
    relatedCity: null,
    relatedCategories: ["instalator", "hvac", "electrician"]
  },

  {
    slug: "cost-instalatie-electrica-apartament",
    title: "Cât costă o instalație electrică completă apartament · 2026",
    h1: "Cât costă o instalație electrică completă în apartament în 2026",
    description: "Preț real pentru refacerea instalației electrice apartament 2-4 camere în România 2026: detalii pe circuite, tablou, manoperă, ANRE. Cum eviți facturile umflate.",
    tag: "Cost & Buget",
    icon: "Zap",
    publishedAt: "2026-02-05",
    updatedAt: "2026-02-29",
    readMins: 7,
    sections: [
      {
        heading: "Răspuns scurt: cât costă în 2026",
        body: [
          "Refacerea completă a instalației electrice într-un apartament costă în 2026 între **4.500 și 9.500 RON**, în funcție de:",
          {
            type: "list",
            items: [
              "Suprafața locuinței (40-80 mp)",
              "Numărul de circuite (12-20 circuite separate pentru un apartament modern)",
              "Calitatea materialelor (Schneider, ABB, Legrand vs branduri ieftine)",
              "Necesitatea de a sparge zidurile (instalație îngropată vs aparentă)",
              "Orașul (București/Cluj cu 15% peste media națională)"
            ]
          }
        ]
      },
      {
        heading: "Defalcare pe componente",
        body: [
          "**1. Tablou electric nou** (cu siguranțe diferențiale și DIF/PE separate pentru fiecare circuit): 800-1.500 RON materiale + 400-700 RON manoperă",
          "**2. Cablu de cupru** (3×2.5mm² pentru prize, 3×1.5mm² pentru iluminat, 3×4mm² pentru aragaz/aer condiționat): 1.200-2.500 RON pentru un apartament 2 camere",
          "**3. Prize și întrerupătoare** (24-40 buc): 600-1.800 RON, în funcție de brand. Schneider și Legrand sunt premium (60-90 RON/buc), Mureș și Energy sunt economy (20-35 RON/buc)",
          "**4. Spargere ziduri + îngropare canale + reparare**: 800-1.500 RON pentru un apartament mediu — DOAR dacă vrei instalație îngropată",
          "**5. Manoperă electrician** (montaj cabluri + conexiuni + verificare): 1.500-3.000 RON",
          "**6. Verificare PRAM + măsurători + buletinul electric obligatoriu**: 350-600 RON. Buletinul electric este OBLIGATORIU pentru a putea racorda apartamentul la rețea după lucrare."
        ]
      },
      {
        heading: "Cum economisești 20-30% fără să compromiți siguranța",
        body: [
          "**1. Cumpără tu cablurile și prizele.** Diferența între prețul de la magazin (Dedeman, Mr. Bricolage) și prețul taxat de electrician poate fi 30-50%. Materialele de calitate (Schneider, Legrand, ABB) costă la fel oriunde — diferența e doar marja electricianului.",
          "**2. Reutilizează tablou + cabluri unde se poate.** Dacă apartamentul are deja un tablou modern cu DIF general și cablu de cupru (nu aluminiu!), poți păstra structura și refaci doar circuitele uzate. Economie: 1.500-2.500 RON.",
          "**3. Alegere apartament cu instalație apareantă** (în jgheaburi de plastic la perete) — elimini costul de spargere ziduri și economisești 800-1.500 RON. Estetic e mai puțin elegant dar funcțional 100%.",
          "**4. Verifică obligatoriu certificatul ANRE.** O lucrare electrică făcută de neautorizat NU va trece verificarea PRAM, iar tu vei fi obligat să refaci totul — costă încă o dată din buzunarul tău."
        ]
      },
      {
        heading: "Semnale că electricianul te înșeală",
        body: [
          "**1. \"Nu îți trebuie tablou nou, e bun cel vechi.\"** Dacă tabloul are siguranțe automate vechi sau (mai grav) siguranțe de tip patron cu fir, ai nevoie de tablou nou. Refuzul de a-l înlocui = el economisește, tu rămâi cu pericol.",
          "**2. \"Cablul de aluminiu e bun, costă mai puțin.\"** Aluminiul nu se mai folosește în România din 2002. Orice electrician care îți propune aluminiu este nepregătit sau încearcă să te înșele.",
          "**3. \"Nu îți trebuie buletin electric, e o cheltuială inutilă.\"** Greșit. Buletinul electric (verificarea PRAM) este obligatoriu legal după refacerea instalației și obligatoriu pentru racordarea la furnizor.",
          "**4. \"Ne descurcăm fără să spargem zidurile.\"** Dacă vrei instalație îngropată (estetic), zidurile TREBUIE sparte. Alternativă: instalație aparentă în jgheaburi. \"Trecere prin podea\" sau \"prin tavanul fals\" = soluții improvizate care vor fi probleme peste 5 ani."
        ]
      }
    ],
    faq: [
      {
        q: "Cât durează refacerea completă a unei instalații electrice apartament 2 camere?",
        a: "Pentru un apartament 2 camere (50-60 mp): 5-8 zile lucrătoare. Etape: ziua 1 — spargere ziduri și marcare circuite; zilele 2-4 — tragere cabluri și montaj prize/întrerupătoare; ziua 5 — montaj tablou și conexiuni; ziua 6 — verificare PRAM + emitere buletin; zilele 7-8 — repararea zidurilor și pregătire pentru zugrăveală."
      },
      {
        q: "Pot să trăiesc în apartament în timpul refacerii instalației electrice?",
        a: "Tehnic da, dar foarte incomod. Vei avea curent disponibil doar pe un singur circuit (de obicei doar la o priză din bucătărie), praf masiv și ferestrele permanent deschise. Recomandăm să te muți pentru 1-2 săptămâni, mai ales dacă ai copii sau persoane în vârstă. Costul a 2 săptămâni de cazare se amortizează prin lucrare făcută corect și rapid."
      },
      {
        q: "De câți ampere am nevoie pentru un apartament 3 camere?",
        a: "Pentru un apartament 3 camere modern (cu aer condiționat, mașină spălat vase, plită cu inducție, cuptor): minim **32A monofazat** sau **3x16A trifazat** dacă ai aragaz electric și aer condiționat pe 2 zone. Pentru un apartament standard fără echipamente mari: 25A monofazat este suficient. Furnizorul tău (Enel/Electrica) îți face evaluarea gratuit la cerere."
      },
      {
        q: "Care este diferența între un tablou cu DIF și unul fără?",
        a: "DIF (Diferențial) este un dispozitiv care decuplează curentul în 0.03 secunde dacă detectează o scurgere către pământ (de exemplu, dacă atingi accidental un cablu sub tensiune). Fără DIF, scurgerea continuă până când circuitul ia foc sau te electrocutează. **DIF-ul este OBLIGATORIU în norma I7/2011 și salvează vieți.** Costul: ~200-350 RON pentru un DIF de calitate. Refuzul electricianului de a-l monta = motiv de înlocuit electricianul."
      },
      {
        q: "Cât costă să adaug o singură priză într-un perete?",
        a: "Pentru adăugarea unei singure prize într-un perete (cu spargere + cablu nou de la cel mai apropiat circuit + reparare zid): 180-320 RON manoperă + 30-60 RON materiale = total 210-380 RON. Dacă circuitul cel mai apropiat este deja la sarcină maximă, poate fi nevoie de un circuit nou (de la tablou) — cost: 400-700 RON. Cere mereu evaluare la fața locului ÎNAINTE de a confirma."
      }
    ],
    relatedCity: null,
    relatedCategories: ["electrician"]
  },

  {
    slug: "cum-functioneaza-escrow-lucrari",
    title: "Cum funcționează plata escrow pentru lucrări de construcție · 2026",
    h1: "Cum funcționează plata escrow pentru lucrări",
    description: "Ghid clar: ce este escrow, cum protejează banii tăi, ce taxe se aplică, când se eliberează plata și cum deschizi o dispută. Toate detaliile despre plata escrow PropManage.",
    tag: "Plăți & Siguranță",
    icon: "Lock",
    publishedAt: "2026-02-12",
    updatedAt: "2026-02-29",
    readMins: 6,
    sections: [
      {
        heading: "Ce este plata escrow și de ce contează",
        body: [
          "**Escrow** este un mecanism prin care banii pentru o lucrare sunt blocați la o terță parte (în cazul nostru, PropManage) până când ambele părți confirmă că lucrarea a fost finalizată conform înțelegerii.",
          "Cu alte cuvinte: tu virezi banii pe platformă, specialistul vede că banii sunt blocați și începe lucrarea în siguranță, iar la final tu confirmi finalizarea și banii ajung automat în portofelul lui.",
          {
            type: "callout",
            title: "Diferență față de plata clasică",
            body: "În metoda clasică tu plătești specialistul direct (cash sau bancă). Dacă apare o problemă, banii sunt deja la el și depinzi de bunăvoința lui ca să rezolve. Cu escrow, tu controlezi când se eliberează banii."
          }
        ]
      },
      {
        heading: "Pașii unei tranzacții escrow PropManage",
        body: [
          "**1. Accepți oferta specialistului** (în chat-ul aplicației, după ce ai văzut prețul total scris)",
          "**2. Virezi suma în escrow** prin card bancar (Visa, Mastercard, Maestro) sau transfer bancar. PropManage blochează imediat banii — specialistul vede notificare \"Escrow alimentat\" dar NU primește banii încă.",
          "**3. Specialistul începe lucrarea** știind că banii sunt protejați.",
          "**4. La finalizare, tu inspectezi lucrarea** și confirmi în aplicație că totul e în regulă.",
          "**5. Banii se eliberează automat** către portofelul specialistului (95% din sumă — diferența de 5% este comisionul platformei). Dacă specialistul a fost validat de tine ca \"VERIFIED\", primește 96%.",
          "**6. Tu primești factură automată** generată de platformă, conformă cu standardele ANAF."
        ]
      },
      {
        heading: "Ce se întâmplă dacă apare o problemă",
        body: [
          "Dacă specialistul nu finalizează lucrarea sau dacă observi probleme, ai 7 zile de la confirmarea predării pentru a deschide o **dispută** din contul tău. Pașii:",
          {
            type: "list",
            items: [
              "**Apeși \"Deschide dispută\"** în pagina lucrării și descrii problema cu poze/video.",
              "**Banii rămân înghețați** în escrow — specialistul NU îi primește.",
              "**Echipa de mediere PropManage** analizează cazul în 48h și solicită ambele perspective.",
              "**Decizia finală** poate fi: rambursare integrală, plată parțială către specialist (split equitabil), sau plată completă către specialist (dacă lucrarea a fost finalizată corect și problema e neîntemeiată).",
              "**Banii se eliberează conform deciziei** automat — nu trebuie să mai faci nicio acțiune."
            ]
          },
          "În 2025, **94%** din disputele de pe PropManage au fost rezolvate în maxim 5 zile, cu 67% finalizate în favoarea clientului (rambursare totală sau parțială)."
        ]
      },
      {
        heading: "Taxe și comisioane",
        body: [
          "Modelul PropManage este transparent — nu există costuri ascunse pentru client:",
          {
            type: "list",
            items: [
              "**Pentru tine (client)**: 0% comision la plată. Plătești exact suma pe care o vede specialistul.",
              "**Pentru specialist**: 5% comision platformă (4% pentru cei cu badge VERIFIED).",
              "**Taxa procesator card** (Stripe): 1.4% + 1 RON, reținută automat din comisionul platformei — nu se adaugă peste prețul tău.",
              "**Plată token discount**: poți reduce până la 50% din valoarea tranzacției folosind tokenii pe care îi câștigi în platformă (1 token = 1 RON discount)."
            ]
          }
        ]
      }
    ],
    faq: [
      {
        q: "Banii din escrow sunt asigurați? Ce se întâmplă dacă PropManage dispare?",
        a: "Banii din escrow sunt păstrați într-un cont segregat la o bancă parteneră (BCR Trust Account), separat complet de capitalul operațional al PropManage. În cazul (extrem de improbabil) al insolvenței companiei, banii pot fi recuperați integral printr-o procedură simplificată — fiind segregați, NU pot fi folosiți pentru a stinge datoriile companiei. Suplimentar, transferurile sunt acoperite de protecția consumatorului oferită de procesatorul Stripe pentru plățile cu cardul."
      },
      {
        q: "Cât durează până banii ajung la specialist după confirmarea mea?",
        a: "După ce apeși \"Confirmă finalizare\", banii se eliberează din escrow în portofelul specialistului în maxim 60 de minute. De acolo, specialistul îi poate retrage în contul lui bancar în 1-3 zile lucrătoare (timpul standard de transfer bancar interbancar). Dacă specialistul are activată retragerea automată zilnică, banii ajung în contul lui în maxim 24h."
      },
      {
        q: "Pot rambursa banii dacă mă răzgândesc înainte ca specialistul să înceapă lucrarea?",
        a: "Da. Atâta timp cât specialistul NU a marcat lucrarea ca \"începută\" în aplicație, poți anula tranzacția cu un click și banii revin automat pe cardul tău în 3-5 zile lucrătoare (depinde de banca emitentă). Dacă lucrarea a fost deja începută, anularea este posibilă doar prin acord cu specialistul sau prin deschiderea unei dispute."
      },
      {
        q: "Pot folosi escrow și pentru lucrări mici (sub 500 RON)?",
        a: "Da, escrow funcționează pentru orice sumă, de la 100 RON la 100.000 RON. Pentru lucrări sub 500 RON unii clienți preferă plata directă pentru simplitate, dar escrow rămâne disponibil — comisionul este același procentual. Recomandăm escrow chiar și pentru lucrări mici dacă nu cunoști specialistul personal."
      },
      {
        q: "Ce se întâmplă dacă lucrarea e finalizată dar apar probleme peste 6 luni?",
        a: "Garanția standard pe lucrare este de 12 luni pentru toate lucrările PropManage. În această perioadă specialistul este obligat să remedieze gratuit orice defect care decurge din execuția lui. Cererea de remediere se face din pagina lucrării (chiar dacă escrow-ul a fost deja eliberat) — sistemul notifică automat specialistul și obține răspuns în 48h. Dacă nu remediază, escaladăm la echipa de mediere și se aplică sancțiuni (suspendare cont, refundare costuri remediere)."
      }
    ],
    relatedCity: null,
    relatedCategories: ["instalator", "electrician", "zugrav", "tamplar"]
  },

  {
    slug: "cum-alegi-zugrav-bun",
    title: "Cum alegi un zugrav bun · Ghid practic 2026",
    h1: "Cum alegi un zugrav bun",
    description: "Cum recunoști un zugrav profesionist, cât costă o zugrăveală în 2026 pe metru pătrat, ce vopsele alegi și 5 greșeli costisitoare de evitat. Ghid complet PropManage.",
    tag: "Decizie & Sfaturi",
    icon: "Brush",
    publishedAt: "2026-02-03",
    updatedAt: "2026-02-29",
    readMins: 6,
    sections: [
      {
        heading: "Ce înseamnă un zugrav profesionist",
        body: [
          "Un zugrav bun nu doar aplică vopsea pe perete — el pregătește suprafața, alege materialele potrivite și execută finisajul astfel încât să nu apară crăpături sau pete în următorii 5-7 ani.",
          "Pe scurt: diferența între un zugrav slab și unul bun se vede peste 2 ani, nu imediat după lucrare."
        ]
      },
      {
        heading: "Cât costă o zugrăveală în 2026",
        body: [
          "Prețul mediu pentru un apartament din România în 2026:",
          {
            type: "list",
            items: [
              "**Manoperă zugrăveală simplă** (lavabilă, 2 mâini): 18-28 RON/mp perete",
              "**Manoperă cu pregătire** (gletuiri, șlefuiri, amorsă): 28-45 RON/mp perete",
              "**Lavabilă premium** (Beckers, Caparol, Tikkurila): 380-650 RON / găleată 15L (acoperă ~120-150 mp)",
              "**Glet de finisaj**: 180-280 RON / sac 25kg (acoperă ~50-70 mp în strat subțire)",
              "**Amorsă**: 80-140 RON / 10L"
            ]
          },
          "**Total pentru un apartament 2 camere (60 mp utili, ~180 mp perete)**: 3.500-7.500 RON, în funcție de pregătirea pereților și calitatea vopselei."
        ]
      },
      {
        heading: "Semnele unui zugrav profesionist",
        body: [
          "**1. Vine la fața locului ÎNAINTE de a-ți da preț.** Un zugrav serios măsoară pereții, verifică ce a fost înainte (vopsea de var? lavabilă? glet vechi?) și abia apoi îți face oferta. Cine îți spune \"30 RON/mp\" la telefon, fără să fi văzut casa, e neserios.",
          "**2. Întreabă ce vopsea vrei.** Un zugrav slab folosește orice — un profesionist te întreabă: \"vrei lavabilă, mat sau lucios? Bachelite sau acril? Premium sau standard?\". Diferența între o lavabilă bună (300 RON/L) și una proastă (60 RON/L) se vede peste 6 luni: cea proastă se șterge la curățare, cea bună rezistă 5+ ani.",
          "**3. Are unelte profesionale.** Pensoane diferite pentru colțuri și mijloc, role cu diametre adaptate, scară telescopică, șapcă/ochelari/folii pentru protecție. Cine vine cu o singură pensoană și o găleată = amator.",
          "**4. Acoperă tot înainte să înceapă.** Mochete, mobilă, parchet, geamuri — toate cu folii sau hârtie. Dacă lasă mobila descoperită \"o ștergem la final\" — fugi.",
          "**5. Lucrează DOAR pe pereți pregătiți.** Refuză să zugravească pe pereți cu cracături, cu vopsea veche care se cojește, fără glet. Un profesionist insistă pe pregătire — un amator zugravește direct ca să termine repede."
        ]
      },
      {
        heading: "Ce vopsea aleg pentru fiecare cameră",
        body: [
          "**Living + dormitoare**: lavabilă mat (efect mai cald, ascunde imperfecțiunile pereților). Acoperire 14-16 mp/L.",
          "**Bucătărie**: lavabilă lucioasă sau semi-lucioasă (rezistă la grăsime, abur, se șterge cu burete). Recomand: Beckers Scotte 20, Caparol Diamant.",
          "**Baie**: lavabilă antimucegai cu aditiv biocid (Tikkurila Luja, Beckers Scotte 5). Lasă pereții să respire dar previne mucegaiul.",
          "**Pereți cu pete vechi (apă, fum)**: ÎNTÂI aplici izolator (Aquasealer, Beckers Fond Iso) — fără el petele vor sângera prin lavabilă oricât de scumpă ar fi.",
          "**Plafon**: vopsea albă mată specifică (mai diluată, acoperă mai bine), aplicată cu rolă cu fir lung. Niciodată lavabilă obișnuită — nu acoperă."
        ]
      },
      {
        heading: "5 greșeli care te costă în 2 ani",
        body: [
          "**1. Sărit peste glet \"ca să economisești 600 RON\".** Pereții vor avea micro-cracături în 6-12 luni, iar lavabila se va decoji. Vei plăti dublu să refaci.",
          "**2. Vopsea ieftină în loc de premium.** Diferența de 800 RON între o vopsea proastă și una bună se amortizează în primul an prin durabilitate.",
          "**3. Plată în avans 100%.** Niciodată. Plătești 30% avans, 70% la finalizare verificată. Cu escrow PropManage e automat — banii sunt blocați și se eliberează la confirmarea ta.",
          "**4. \"Verifică-mi lucrarea cu becul stins\".** Imperfecțiunile (urme de rolă, suprafețe ratate) se văd doar în lumină laterală — cu o lanternă paralel cu peretele. Cere demonstrația.",
          "**5. Lipsa unui contract scris.** Toate detaliile (mp pereți, tip vopsea, numărul de mâini, termen, preț) trebuie pe hârtie. Înțelegerile verbale = sursă de conflict."
        ]
      }
    ],
    faq: [
      {
        q: "Cât durează zugrăveala unui apartament 2 camere?",
        a: "Pentru un apartament 2 camere (~60 mp utili), un zugrav profesionist execută lucrarea în 3-5 zile, depinzând de pregătirea pereților: 1 zi pregătire + amorsă, 1-2 zile gletuiri (cu uscare între straturi), 1-2 zile lavabilă (2 mâini). Dacă pereții sunt deja gletuiți și amorsați, durata se reduce la 2-3 zile."
      },
      {
        q: "Pot să zugravesc singur sau merită angajat un specialist?",
        a: "Pentru un singur perete sau o cameră mică, da — există tutoriale și economisești 1.500-2.500 RON. Pentru un apartament întreg, NU recomandăm: rezultatul amatorist (urme de rolă, plafonuri ratate, colțuri murdare) se vede zilnic și te va deranja. Un profesionist face în 4 zile ce ție ți-ar lua 2 săptămâni + concedii."
      },
      {
        q: "De câte mâini de lavabilă am nevoie?",
        a: "Minim 2 mâini pe perete deja zugrăvit anterior. Pe ziduri noi (după gletuire) sau cu schimbare radicală de culoare (de la închis la deschis): 3 mâini sunt necesare. O singură mână NU acoperă uniform și se va vedea structura veche prin ea — semn de zugrav care încearcă să economisească materiale."
      },
      {
        q: "Câtă vopsea trebuie să cumpăr pentru un apartament 50 mp?",
        a: "Pentru un apartament 50 mp utili (~150 mp suprafață perete) calculezi astfel: 150 mp ÷ 12 mp/L acoperire = 12.5 L per mână. Pentru 2 mâini: ~25 L total. La asta adaugi 10-15% safety margin. Soluție practică: 2 găleți de 15L (=30L) acoperă confortabil cu rezervă pentru retușuri viitoare. Plafonul se calculează separat (12-14 mp/L pentru vopsea de plafon)."
      },
      {
        q: "Ce trebuie să fac eu înainte să vină zugravul?",
        a: "1) Mută mobila la mijlocul camerei (zugravul protejează cu folie). 2) Demontează tablouri, rafturi, aplici. 3) Spală pereții de praf cu o cârpă umedă. 4) Verifică să nu fie scurgeri active (zugravul nu vopsește pe ziduri ude). Restul — pregătire ziduri, amorsă, glet, acoperit pardoseală — face zugravul. NU este nevoie să demontezi parchetul sau să muți frigiderul."
      }
    ],
    relatedCity: null,
    relatedCategories: ["zugrav", "tamplar", "design-interior"]
  },

  {
    slug: "audit-tehnic-apartament-pret",
    title: "Cât costă un audit tehnic de apartament · Preț și ce include · 2026",
    h1: "Cât costă un audit tehnic de apartament în 2026",
    description: "Prețul unui audit tehnic de apartament în România: 2.400 RON. Ce verifică specialistul (electric, sanitar, umiditate, structură), cât durează și când merită să-l comanzi.",
    tag: "Audit Tehnic",
    icon: "ShieldCheck",
    publishedAt: "2026-07-26",
    updatedAt: "2026-07-26",
    readMins: 7,
    sections: [
      {
        heading: "Răspuns scurt: cât costă",
        body: [
          "Un audit tehnic complet de apartament costă pe PropManage **2.400 RON** — preț fix, indiferent de oraș. Auditul durează 60-90 de minute la fața locului și se încheie cu un raport scris cu toate problemele identificate, prioritizate după risc și cost de remediere.",
          {
            type: "callout",
            title: "De ce merită",
            body: "Un singur defect ascuns descoperit la timp (instalație electrică veche, țevi de plumb, igrasie mascată) poate economisi între 5.000 și 40.000 RON. Auditul de 2.400 RON este cea mai ieftină asigurare pe care o poți cumpăra pentru locuința ta."
          }
        ]
      },
      {
        heading: "Ce verifică specialistul, punct cu punct",
        body: [
          {
            type: "list",
            items: [
              "**Instalația electrică**: vârsta tabloului, siguranțe automate, împământare, prize suprasolicitate, circuite subdimensionate",
              "**Instalația sanitară**: materialul țevilor (plumb/oțel vs PEX), presiune, semne de scurgeri, sifoane și racorduri",
              "**Umiditate și igrasie**: măsurători cu umidometru în colțuri, spatele mobilei, băi, pereți exteriori",
              "**Termoviziune** (unde e cazul): punți termice, pierderi de căldură, infiltrații ascunse sub finisaje",
              "**Structură**: fisuri active vs fisuri de finisaj, tasări, starea planșeelor",
              "**Tâmplărie și izolație**: etanșeitate ferestre, condens, izolație pereți",
              "**Centrala termică și gaz**: vârstă, revizii, tiraj, detectoare",
              "**Documentație**: carte tehnică, certificat energetic, autorizații pentru modificări"
            ]
          }
        ]
      },
      {
        heading: "Când merită să comanzi un audit",
        body: [
          "**1. Înainte să cumperi un apartament.** Cel mai frecvent caz — auditul se face la vizionare, înainte de antecontract. Funcționează și pentru apartamente găsite pe Storia sau Imobiliare.ro: comanzi auditul, specialistul merge la vizionare cu tine sau în locul tău.",
          "**2. Înainte să vinzi.** Un apartament cu audit tehnic + raport public se vinde mai repede și la un preț mai bun, pentru că elimină frica cumpărătorului. Pe PropManage, apartamentele auditate primesc statutul de **Imobil Verificat**.",
          "**3. Înainte de o renovare majoră.** Auditul îți spune exact ce trebuie refăcut obligatoriu (instalații) și ce e doar cosmetic — ca să nu îngropi finisaje noi peste probleme vechi.",
          "**4. La probleme recurente.** Igrasie care revine, siguranțe care sar, facturi anormal de mari — auditul găsește cauza, nu simptomul."
        ]
      },
      {
        heading: "Cum se desfășoară pe PropManage",
        body: [
          {
            type: "list",
            items: [
              "**Pasul 1**: Comanzi online auditul (2.400 RON, plată securizată prin Stripe)",
              "**Pasul 2**: Ești contactat în maxim 24h pentru programare",
              "**Pasul 3**: Specialistul verificat vine la adresă (60-90 min)",
              "**Pasul 4**: Primești raportul scris cu probleme + priorități + costuri estimate de remediere",
              "**Pasul 5** (opțional): Poți adăuga Digital Twin (950 RON) — harta digitală completă a locuinței"
            ]
          },
          "Vrei întâi o estimare gratuită? Folosește calculatorul **Scorul Casei Tale** — 12 întrebări, 2 minute, scor instant."
        ]
      }
    ],
    faq: [
      {
        q: "Cât durează un audit tehnic de apartament?",
        a: "60-90 de minute la fața locului pentru un apartament de 2-3 camere. Raportul scris este livrat în maxim 48h de la vizită."
      },
      {
        q: "Pot comanda audit pentru un apartament pe care vreau să-l cumpăr, dar nu e al meu?",
        a: "Da — este cel mai frecvent scenariu. Ai nevoie doar de acordul proprietarului/agenției pentru accesul specialistului la vizionare. Auditul funcționează pentru orice anunț de pe Storia, Imobiliare.ro sau OLX."
      },
      {
        q: "Ce primesc concret la finalul auditului?",
        a: "Un raport scris cu: lista completă a problemelor identificate, fotografii, prioritizarea lor după risc (critic/important/cosmetic), costuri estimative de remediere și recomandări de specialiști verificați pentru fiecare categorie de lucrări."
      },
      {
        q: "Auditul include verificarea actelor apartamentului?",
        a: "Auditul verifică documentația tehnică (carte tehnică, certificat energetic, autorizații pentru modificări structurale). Pentru verificarea juridică (extras CF, sarcini, litigii) recomandăm un avocat sau notarul care se ocupă de tranzacție."
      },
      {
        q: "Care e diferența dintre audit și Digital Twin?",
        a: "Auditul (2.400 RON) = evaluarea stării tehnice cu raport scris. Digital Twin (950 RON) = harta digitală permanentă a locuinței: planuri, instalații mapate, documente, istoric intervenții. Împreună formează pachetul complet pentru un Imobil Verificat."
      }
    ],
    relatedCity: null,
    relatedCategories: ["electrician", "instalator"]
  },

  {
    slug: "verificare-apartament-inainte-de-cumparare",
    title: "Cum verifici un apartament înainte să-l cumperi · Ghid complet 2026",
    h1: "Cum verifici un apartament înainte de cumpărare",
    description: "Ghid complet 2026: cele mai importante verificări înainte să cumperi un apartament — acte, structură, instalații, umiditate, costuri ascunse. Plus checklist gratuit cu 25 de puncte.",
    tag: "Cumpărare",
    icon: "Search",
    publishedAt: "2026-07-26",
    updatedAt: "2026-07-26",
    readMins: 9,
    sections: [
      {
        heading: "Greșeala de 30.000 RON pe care o fac majoritatea cumpărătorilor",
        body: [
          "Majoritatea cumpărătorilor verifică un apartament în 20 de minute, la lumina zilei, cu mobila proprietarului acoperind pereții. Apoi descoperă după mutare: igrasie în spatele dulapului, instalație electrică din 1985, țevi de plumb, vecini zgomotoși. Costul mediu al problemelor descoperite **după** cumpărare, raportat de clienții noștri: **15.000-40.000 RON**.",
          {
            type: "callout",
            title: "Regula de aur",
            body: "Niciun apartament nu se cumpără după o singură vizionare. Minim 2 vizite (una seara), plus o verificare tehnică profesionistă înainte de antecontract."
          }
        ]
      },
      {
        heading: "Verificările pe care le poți face singur",
        body: [
          {
            type: "list",
            items: [
              "**Umiditate**: uită-te în colțurile camerelor, în spatele mobilierului, sub chiuvete. Miros de mucegai = semnal roșu",
              "**Presiunea apei**: deschide toate robinetele simultan. Lasă apa să curgă 2 minute — culoarea ruginie indică țevi vechi de oțel",
              "**Tabloul electric**: siguranțe automate moderne sau siguranțe vechi cu filet? Câte circuite are?",
              "**Ferestre**: închide-le și ascultă zgomotul străzii. Verifică condens între geamuri",
              "**Pereți**: fisuri diagonale la colțurile ușilor/ferestrelor pot indica tasări",
              "**Facturile de iarnă**: cere facturile de întreținere din decembrie-februarie — diferența față de vară îți spune tot despre izolație",
              "**Vecinii**: vizitează la 20:00 într-o zi de lucru. Ascultă"
            ]
          }
        ]
      },
      {
        heading: "Verificările care cer un specialist",
        body: [
          "Ce NU poți verifica singur, oricât de atent ai fi:",
          {
            type: "list",
            items: [
              "**Instalația electrică din pereți** — vârsta reală a cablurilor, împământarea, dimensionarea circuitelor",
              "**Umiditatea ascunsă** — umidometrul detectează igrasia mascată cu vopsea proaspătă (truc frecvent la vânzare!)",
              "**Punțile termice** — camera de termoviziune arată pierderile de căldură invizibile",
              "**Fisurile structurale vs cosmetice** — diferența dintre o reparație de 200 RON și una de 20.000 RON",
              "**Modificările neautorizate** — ziduri demolate fără autorizație = probleme la revânzare și risc structural"
            ]
          },
          "Un **audit tehnic profesionist costă 2.400 RON** și se face la vizionare, înainte de antecontract. Funcționează pentru orice apartament, inclusiv anunțuri de pe Storia sau Imobiliare.ro."
        ]
      },
      {
        heading: "Actele: ce verifici înainte de avans",
        body: [
          {
            type: "list",
            items: [
              "**Extras de Carte Funciară** actualizat (max 30 zile) — proprietar real, sarcini, ipoteci, interdicții",
              "**Certificat energetic** — obligatoriu la vânzare; clasa energetică afectează facturile",
              "**Adeverință de la asociație** — fără datorii la întreținere; întreabă și de restanțe la fondul de reparații",
              "**Risc seismic** — verifică dacă clădirea e în lista clădirilor cu risc (bulina roșie = NU se poate ipoteca)",
              "**Autorizații pentru modificări** — orice zid demolat trebuie să aibă autorizație + proiect"
            ]
          },
          "Descarcă checklist-ul complet cu toate cele **25 de verificări** — interactiv, gratuit, cu explicații pentru fiecare punct."
        ]
      }
    ],
    faq: [
      {
        q: "Cât costă să verific un apartament înainte de cumpărare?",
        a: "Verificările pe care le faci singur sunt gratuite (checklist-ul nostru cu 25 de puncte te ghidează). Un audit tehnic profesionist cu specialist, umidometru și termoviziune costă 2.400 RON pe PropManage — și se amortizează din prima problemă descoperită."
      },
      {
        q: "Pot cere audit tehnic pentru un apartament găsit pe Storia sau Imobiliare.ro?",
        a: "Da. Comanzi auditul online, iar specialistul merge la vizionare (cu tine sau programat cu agentul/proprietarul). Primești raportul înainte să semnezi antecontractul."
      },
      {
        q: "Ce înseamnă bulina roșie la un bloc?",
        a: "Clădire încadrată în clasa I de risc seismic. Băncile NU acordă credit ipotecar pentru aceste apartamente, iar asigurarea e problematică. Verifică lista publicată de primărie înainte de orice discuție de preț."
      },
      {
        q: "Vânzătorul a zugrăvit recent — e semn bun sau rău?",
        a: "Ambele. Poate fi pregătire normală de vânzare, dar vopseaua proaspătă e și cel mai folosit mod de a masca igrasia și fisurile. Exact aici ajută umidometrul specialistului — detectează umiditatea din perete indiferent de vopsea."
      },
      {
        q: "Când e cel mai bun moment pentru a doua vizionare?",
        a: "Seara (19:00-21:00) într-o zi lucrătoare: auzi vecinii reali, vezi traficul, iluminatul public, locurile de parcare rămase. Iarna e ideal — simți instant cât de rece e apartamentul."
      }
    ],
    relatedCity: null,
    relatedCategories: ["electrician", "instalator"]
  },

  {
    slug: "ce-este-digital-twin-locuinta",
    title: "Ce este un Digital Twin al locuinței · Ghid pentru proprietari · 2026",
    h1: "Ce este un Digital Twin al locuinței tale",
    description: "Digital Twin = copia digitală completă a locuinței: planuri, instalații mapate, documente, istoric intervenții. Ce include, cât costă (950 RON) și de ce crește valoarea proprietății.",
    tag: "Digital Twin",
    icon: "Box",
    publishedAt: "2026-07-26",
    updatedAt: "2026-07-26",
    readMins: 6,
    sections: [
      {
        heading: "Pe scurt: copia digitală a casei tale",
        body: [
          "Un **Digital Twin** (geamăn digital) este copia digitală completă a locuinței tale: planurile, instalațiile mapate (unde trec cablurile și țevile prin pereți), toate documentele tehnice, istoricul intervențiilor și starea fiecărui sistem — totul într-un singur loc, accesibil de pe telefon.",
          {
            type: "callout",
            title: "De ce contează",
            body: "Când ai o urgență (țeavă spartă, scurtcircuit), specialistul care vine știe EXACT unde să caute — fără să spargă trei pereți ca să găsească traseul. Când vinzi, cumpărătorul vede negru pe alb ce cumpără."
          }
        ]
      },
      {
        heading: "Ce include Digital Twin-ul pe PropManage",
        body: [
          {
            type: "list",
            items: [
              "**Planurile locuinței** — digitalizate, cu dimensiuni reale per cameră",
              "**Instalațiile mapate** — traseele electrice, sanitare și de încălzire marcate pe plan",
              "**Arhiva de documente** — carte tehnică, certificat energetic, garanții, facturi lucrări, manuale centrale/electrocasnice",
              "**Istoricul intervențiilor** — fiecare reparație și renovare, cu dată, specialist și cost",
              "**Starea sistemelor** — vârsta și starea fiecărei instalații, cu alerte când se apropie de finalul duratei de viață",
              "**Acces controlat** — poți da acces temporar unui specialist sau permanent unui cumpărător"
            ]
          }
        ]
      },
      {
        heading: "Cât costă și cum se face",
        body: [
          "Crearea Digital Twin-ului costă **950 RON** pe PropManage și include vizita unui specialist care măsoară, fotografiază și mapează locuința. Durează 2-3 ore pentru un apartament standard. În pachet cu auditul tehnic (**bundle 1.300 RON**) primești și evaluarea completă a stării tehnice.",
          "**Bonus la vânzare**: dacă vinzi apartamentul prin programul Imobile Verificate, costul Digital Twin-ului se **scade din comisionul de vânzare** — practic îl primești înapoi."
        ]
      },
      {
        heading: "Digital Twin vs. dosarul cu acte de la sertar",
        body: [
          {
            type: "list",
            items: [
              "**Dosarul clasic**: se pierde, se udă, nu e la tine când ai nevoie, nu-l poți trimite specialistului la 22:00 când curge apa",
              "**Digital Twin**: permanent pe telefon, partajabil într-un click, se actualizează la fiecare intervenție, urmează PROPRIETATEA (nu proprietarul) la vânzare",
              "**La vânzare**: apartament cu twin + audit = Imobil Verificat cu Trust Score public — se vinde mai repede și mai scump, pentru că elimină frica cumpărătorului",
              "**La moștenire/închiriere**: toată cunoașterea despre locuință se transferă, nu se pierde"
            ]
          }
        ]
      }
    ],
    faq: [
      {
        q: "Cât durează crearea unui Digital Twin?",
        a: "Vizita de mapare durează 2-3 ore pentru un apartament de 2-3 camere. Twin-ul digital complet este gata în 3-5 zile lucrătoare de la vizită."
      },
      {
        q: "Am nevoie de planurile originale ale apartamentului?",
        a: "Nu e obligatoriu — specialistul măsoară și reconstruiește planul la fața locului. Dacă ai planurile originale (carte tehnică), le digitalizăm și le includem în twin."
      },
      {
        q: "Cine are acces la Digital Twin-ul locuinței mele?",
        a: "Doar tu. Poți acorda acces temporar (ex: unui instalator pentru o intervenție) sau permanent (ex: cumpărătorului la vânzare). Datele sunt găzduite securizat și nu sunt partajate cu terți."
      },
      {
        q: "Ce se întâmplă cu twin-ul când vând apartamentul?",
        a: "Se transferă noului proprietar împreună cu toată istoria locuinței — exact ca o carte de service la mașină. Este unul dintre argumentele care cresc valoarea percepută la vânzare."
      }
    ],
    relatedCity: null,
    relatedCategories: []
  },

  {
    slug: "imobile-verificate-cum-functioneaza",
    title: "Imobile Verificate — cum funcționează · Vânzare fără surprize · 2026",
    h1: "Imobile Verificate: cum funcționează programul",
    description: "Programul Imobile Verificate PropManage: audit tehnic + Digital Twin + Trust Score public. Cum îți vinzi apartamentul mai repede și cum cumperi fără surprize. Comision 2,5%.",
    tag: "Imobile Verificate",
    icon: "ShieldCheck",
    publishedAt: "2026-07-26",
    updatedAt: "2026-07-26",
    readMins: 7,
    sections: [
      {
        heading: "Problema pieței imobiliare din România",
        body: [
          "Pe Storia și Imobiliare.ro, toate anunțurile arată la fel: poze frumoase, „apartament îngrijit\", zero informații verificabile despre starea reală. Cumpărătorul află despre instalația din 1980 și igrasia din baie **după** ce a semnat. Vânzătorul serios n-are cum să demonstreze că apartamentul lui chiar e în stare bună.",
          {
            type: "callout",
            title: "Soluția",
            body: "Imobile Verificate = singurul program din România unde fiecare apartament listat a trecut printr-un audit tehnic profesionist și are Digital Twin. Starea reală, publică, verificabilă."
          }
        ]
      },
      {
        heading: "Cum funcționează pentru vânzători",
        body: [
          {
            type: "list",
            items: [
              "**Pasul 1 — Auditul (2.400 RON)**: specialist verificat evaluează apartamentul: instalații, umiditate, structură, documente",
              "**Pasul 2 — Digital Twin (950 RON)**: locuința e mapată digital — planuri, instalații, arhivă documente",
              "**Pasul 3 — Remedieri**: primești lista problemelor; minim 90% din recomandările critice trebuie rezolvate",
              "**Pasul 4 — Publicare**: apartamentul primește **Trust Score** (A+/A/B) și apare în lista Imobilelor Verificate",
              "**Pasul 5 — Vânzare**: comision de doar **2,5%** la vânzare, din care se SCADE costul Digital Twin-ului"
            ]
          },
          "Pachetul complet (audit + twin) costă **1.300 RON** — și se recuperează prin vânzare mai rapidă, preț mai bun și deducerea twin-ului din comision."
        ]
      },
      {
        heading: "Cum funcționează pentru cumpărători",
        body: [
          "Fiecare Imobil Verificat afișează public: **Trust Score-ul** (A+/A/B), raportul de audit, procentul de recomandări rezolvate și accesul la Digital Twin. Vezi exact ce cumperi, înainte de vizionare.",
          "**Ai găsit un apartament pe Storia care NU e verificat?** Poți comanda auditul nostru pentru orice apartament de pe piață (2.400 RON) — specialistul merge la vizionare și îți spune adevărul despre starea lui, înainte să semnezi."
        ]
      },
      {
        heading: "De ce e diferit de o agenție imobiliară",
        body: [
          {
            type: "list",
            items: [
              "**Agenția clasică**: comision 2-4%, zero verificare tehnică, interesul e să se vândă repede — nu să afli problemele",
              "**Imobile Verificate**: comision 2,5%, verificare tehnică obligatorie ÎNAINTE de listare, problemele se rezolvă înainte de vânzare",
              "**Transparență**: raportul de audit e public — cumpărătorul nu mai negociază pe frică, ci pe fapte",
              "**După vânzare**: cumpărătorul primește Digital Twin-ul cu toată istoria locuinței — onboarding complet în ecosistemul PropManage"
            ]
          }
        ]
      }
    ],
    faq: [
      {
        q: "Cât costă să-mi listez apartamentul ca Imobil Verificat?",
        a: "Pachetul complet costă 3.350 RON (audit tehnic 2.400 + Digital Twin 950). La vânzare se aplică un comision de 2,5%, din care se scade costul Digital Twin-ului — deci twin-ul îl primești practic gratuit."
      },
      {
        q: "Ce este Trust Score-ul?",
        a: "Nota publică a apartamentului (A+, A sau B), calculată din raportul de audit și procentul de recomandări critice rezolvate. A+ înseamnă apartament cu toate sistemele verificate și problemele remediate."
      },
      {
        q: "Ce se întâmplă dacă auditul găsește probleme la apartamentul meu?",
        a: "Primești lista completă cu priorități și costuri estimate. Pentru publicare ca Imobil Verificat trebuie rezolvate minim 90% din recomandările critice — te conectăm cu specialiști verificați pentru remedieri. Alternativ, poți vinde nelistat, dar fără Trust Score."
      },
      {
        q: "Pot cumpăra un apartament care nu e în programul Imobile Verificate?",
        a: "Da — și îți recomandăm să comanzi auditul independent (2.400 RON) pentru orice apartament de pe Storia, Imobiliare.ro sau OLX, înainte de antecontract. Specialistul nostru merge la vizionare și îți livrează raportul în 48h."
      }
    ],
    relatedCity: null,
    relatedCategories: []
  },
  {
    slug: "cat-costa-design-interior-cluj",
    title: "Cât costă designul interior în Cluj-Napoca? · Ghid de prețuri 2026",
    h1: "Cât costă designul interior în Cluj-Napoca",
    description: "Prețurile reale pentru design interior în Cluj: concept, proiect tehnic, randări 3D și implementare. Factorii care influențează costul și cum eviți surprizele.",
    tag: "Prețuri local",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 7,
    sections: [
      {
        heading: "De ce prețul din Cluj e diferit",
        body: [
          "Cluj-Napoca are una dintre cele mai scumpe piețe rezidențiale din țară, împinsă de sectorul IT și de cererea mare. Asta se reflectă și în serviciile de design: cererea ridicată și complexitatea proiectelor (apartamente noi compacte, blocuri vechi de reabilitat) influențează prețul.",
          "Vestea bună: un proiect de design bine făcut **economisește** bani pe șantier, mai ales la un metru pătrat scump — evită cumpărături greșite și refaceri.",
        ],
      },
      {
        heading: "Ce plătești, de fapt",
        body: [
          "Costul se împarte pe etape, iar tu decizi cât de departe mergi:",
          { type: "list", items: [
            "Concept de amenajare — moodboard, paletă, plan de mobilare de bază (cost mic, pe cameră)",
            "Proiect tehnic complet — planuri de execuție, detalii, liste de materiale (calculat pe metru pătrat)",
            "Randări 3D fotorealiste — vezi rezultatul înainte de execuție",
            "Implementare la cheie — coordonare cu specialiști verificați (opțional)",
          ] },
          { type: "callout", title: "Recomandare", body: "Pentru un apartament clujean cere de la început un deviz pe etape. Poți începe doar cu conceptul și decide ulterior dacă mergi la proiect tehnic și implementare." },
        ],
      },
      {
        heading: "Factorii care cresc sau scad costul",
        body: [
          { type: "list", items: [
            "Suprafața și numărul de camere",
            "Starea locuinței (un apartament vechi cere mai multă muncă tehnică)",
            "Nivelul de detaliu al randărilor",
            "Dacă incluzi sau nu implementarea",
          ] },
          "La blocurile vechi din Mărăști, Gheorgheni sau Grigorescu, un **audit tehnic** înainte de a stabili bugetul îți arată ce trebuie refăcut la instalații — și te ferește de surprize costisitoare.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă un concept de design pentru un apartament de 2 camere în Cluj?", a: "Conceptul (fără proiect tehnic) pornește de la câteva sute de lei pe cameră. Prețul exact depinde de designer și de câte variante ceri. Postează o cerere pe PropManage pentru oferte reale de la designeri verificați din Cluj." },
      { q: "Merită proiectul tehnic complet sau e suficient conceptul?", a: "Pentru o simplă redecorare, conceptul poate fi suficient. Pentru o renovare cu intervenții la pereți, instalații sau mobilier pe comandă, proiectul tehnic previne greșeli scumpe pe șantier." },
      { q: "Pot vedea prețurile înainte să mă decid?", a: "Da. Pe PropManage postezi cererea gratuit și primești oferte de la mai mulți designeri verificați, cu portofolii și recenzii — compari fără obligații." },
    ],
    relatedCity: "cluj-napoca",
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Design interior în Cluj-Napoca", to: "/design-interior/cluj-napoca" },
      { label: "Cât costă designul interior (general)", to: "/design-interior/pret" },
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Design interior — pagina principală", to: "/design-interior" },
    ],
  },
  {
    slug: "cum-pregatesti-apartament-renovare",
    title: "Cum pregătești un apartament pentru renovare · Ghid pas cu pas 2026",
    h1: "Cum pregătești un apartament pentru renovare",
    description: "Pașii de pregătire înainte de renovare: evaluarea stării, buget, autorizații, ordinea lucrărilor și cum eviți greșelile costisitoare. Ghid practic.",
    tag: "Renovare",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 8,
    sections: [
      {
        heading: "Începe cu o evaluare corectă a stării",
        body: [
          "Cea mai frecventă greșeală e să începi renovarea de la finisaje (culori, gresie) fără să știi ce e în spatele pereților. Un apartament vechi poate ascunde instalații electrice depășite, țevi corodate sau umezeală.",
          "Un **audit tehnic** sau cel puțin o evaluare a stării îți spune ce trebuie refăcut întâi. Vezi și **Scorul Casei** pentru o imagine rapidă.",
        ],
      },
      {
        heading: "Stabilește bugetul și o rezervă",
        body: [
          "Un buget realist include o rezervă de 10–15% pentru surprize (mai ales la apartamentele vechi). Împarte bugetul pe categorii:",
          { type: "list", items: [
            "Demolări și pregătire",
            "Instalații (electrice, sanitare, termice)",
            "Finisaje (pardoseli, pereți, tavane)",
            "Mobilier și obiecte sanitare",
            "Proiectare și, opțional, coordonare execuție",
          ] },
        ],
      },
      {
        heading: "Respectă ordinea corectă a lucrărilor",
        body: [
          "Ordinea greșită duce la refaceri. Regula de bază: de la structură și instalații către finisaje.",
          { type: "list", items: [
            "1. Demolări și modificări de compartimentare",
            "2. Instalații (trasee electrice, sanitare, încălzire)",
            "3. Tencuieli, șape, hidroizolații",
            "4. Finisaje (pardoseli, faianță, zugrăveli)",
            "5. Montaj mobilier și obiecte",
          ] },
          { type: "callout", title: "De reținut", body: "Un proiect de design făcut ÎNAINTE de renovare stabilește exact unde merg prizele, întrerupătoarele și instalațiile — astfel eviți spargeri ulterioare în pereți proaspăt finisați." },
        ],
      },
    ],
    faq: [
      { q: "Am nevoie de autorizație pentru renovarea apartamentului?", a: "Pentru lucrări interioare fără modificarea structurii de rezistență, de regulă nu. Pentru intervenții pe pereți structurali sau modificări majore, verifică cerințele locale — un specialist te poate ghida." },
      { q: "Cât durează pregătirea înainte de a începe efectiv?", a: "Evaluarea stării, bugetul și proiectul de design pot dura câteva săptămâni, dar economisesc timp și bani pe șantier. Nu sări peste etapa de planificare." },
      { q: "Merită un designer chiar și pentru o renovare mică?", a: "Da — mai ales pentru decizii ireversibile (mutare pereți, instalații). Un concept bine gândit previne cumpărături greșite de mii de lei." },
    ],
    relatedCity: null,
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "Ce verifici înainte de renovare", to: "/ghiduri/ce-verifici-inainte-de-renovare-apartament" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Imobile Verificate", to: "/imobile-verificate" },
      { label: "Design interior apartament vechi", to: "/design-interior/apartament-vechi" },
    ],
  },
  {
    slug: "design-interior-vs-amenajare",
    title: "Design interior vs. amenajare: care e diferența? · Ghid 2026",
    h1: "Design interior vs. amenajare: care este diferența",
    description: "Design interior sau amenajare? Ce include fiecare, când ai nevoie de un proiect complet și când e suficientă o amenajare simplă. Explicat clar.",
    tag: "Comparație",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 6,
    sections: [
      {
        heading: "Două lucruri diferite, des confundate",
        body: [
          "„Amenajare” și „design interior” se folosesc adesea ca sinonime, dar acoperă lucruri diferite. Confuzia poate duce la așteptări greșite și buget subestimat.",
        ],
      },
      {
        heading: "Ce înseamnă amenajarea",
        body: [
          "Amenajarea se referă în general la partea vizibilă și de suprafață: alegerea mobilierului, a textilelor, a culorilor și a decorațiunilor pentru un spațiu care, structural, rămâne neschimbat.",
          { type: "list", items: [
            "Alegerea și dispunerea mobilierului",
            "Textile, obiecte decorative, iluminat decorativ",
            "Paletă de culori și accente",
          ] },
        ],
      },
      {
        heading: "Ce înseamnă designul interior",
        body: [
          "Designul interior este un proces mai amplu, care include și partea funcțională și tehnică: cum circulă oamenii prin spațiu, unde merg instalațiile, cum optimizezi lumina și depozitarea, transformate într-un proiect care poate fi executat.",
          { type: "list", items: [
            "Releveu și analiza spațiului",
            "Plan de mobilare optimizat pe funcțiune și circulație",
            "Planuri tehnice pentru echipele de execuție",
            "Randări 3D și liste de materiale pentru bugetare",
          ] },
          { type: "callout", title: "Pe scurt", body: "Amenajarea se ocupă de cum arată. Designul interior se ocupă de cum funcționează ȘI cum arată — și e esențial la renovări sau spații atipice." },
        ],
      },
    ],
    faq: [
      { q: "Pentru un apartament nou am nevoie de design sau doar de amenajare?", a: "Dacă apartamentul e funcțional și vrei doar să-l mobilezi frumos, amenajarea poate fi suficientă. Dacă vrei să optimizezi compartimentarea, depozitarea sau instalațiile, ai nevoie de design interior." },
      { q: "Designul interior costă mai mult decât amenajarea?", a: "De regulă da, pentru că include partea tehnică. Dar la o renovare economisește bani prin evitarea greșelilor de execuție." },
      { q: "Pot începe cu amenajare și continua cu design?", a: "Ideal e invers: designul stabilește structura, apoi amenajarea adaugă stratul decorativ. Un designer poate acoperi ambele." },
    ],
    relatedCity: null,
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Ce este designul interior", to: "/ghiduri/ce-este-designul-interior" },
      { label: "Ce include un proiect de design", to: "/ghiduri/ce-include-un-proiect-de-design-interior" },
      { label: "Design interior — pagina principală", to: "/design-interior" },
      { label: "Design interior apartament", to: "/design-interior/apartament" },
      { label: "Randări 3D & Digital Twin", to: "/design-interior/3d" },
    ],
  },
  {
    slug: "ce-verifici-inainte-de-renovare-apartament",
    title: "Ce trebuie verificat înainte de renovarea unui apartament · Ghid 2026",
    h1: "Ce trebuie verificat înainte de renovarea unui apartament",
    description: "Checklist tehnic înainte de renovare: instalații, structură, umezeală, izolație și acte. Ce verifici ca să nu ai surprize scumpe pe șantier.",
    tag: "Checklist tehnic",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 7,
    sections: [
      {
        heading: "De ce contează verificarea din start",
        body: [
          "Surprizele descoperite după ce ai început renovarea sunt cele mai scumpe. O verificare atentă înainte de a stabili bugetul îți arată ce e ascuns în spatele finisajelor.",
          "Pentru o evaluare structurată, un **audit tehnic** acoperă sistematic aceste puncte, iar **Digital Twin**-ul îți oferă o imagine 3D a locuinței.",
        ],
      },
      {
        heading: "Checklist tehnic esențial",
        body: [
          { type: "list", items: [
            "Instalația electrică — vechime, secțiune conductori, tablou, împământare",
            "Instalația sanitară — starea țevilor, presiune, scurgeri",
            "Încălzirea — calorifere, centrală, distribuție",
            "Umezeala și igrasia — pete, mucegai, infiltrații (mai ales parter/ultim etaj)",
            "Structura — fisuri în pereți, planeitatea pardoselilor",
            "Izolația termică și fonică — mai ales la apartamentele de colț",
            "Tâmplăria — ferestre, uși, etanșeitate",
          ] },
        ],
      },
      {
        heading: "Actele și situația juridică",
        body: [
          "Înainte de o renovare majoră, verifică dacă intervențiile necesită acordul asociației sau autorizații (mai ales pentru pereți structurali). Pentru pereții de rezistență nu se fac modificări fără aviz de specialitate.",
          { type: "callout", title: "Sfat", body: "Dacă renovezi un apartament pe care abia l-ai cumpărat, cere raportul de audit al locuinței — îți dă lista completă de probleme și priorități înainte să investești în finisaje." },
        ],
      },
    ],
    faq: [
      { q: "Cine poate face verificarea tehnică înainte de renovare?", a: "Un specialist tehnic sau un auditor de locuință. Pe PropManage poți comanda un audit tehnic care acoperă sistematic instalațiile, structura și izolațiile." },
      { q: "Cât costă verificarea față de o renovare greșită?", a: "Verificarea costă o fracțiune din ce ai plăti pentru refacerea unei renovări prost planificate (spargeri în finisaje noi, instalații refăcute). E cea mai bună investiție de la început." },
      { q: "Verificarea e utilă și la un apartament nou?", a: "Da, deși problemele sunt mai puține. Merită să verifici finisajele de la dezvoltator și traseele de instalații înainte de a personaliza." },
    ],
    relatedCity: null,
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Cum pregătești apartamentul pentru renovare", to: "/ghiduri/cum-pregatesti-apartament-renovare" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Imobile Verificate — cum funcționează", to: "/ghiduri/imobile-verificate-cum-functioneaza" },
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "Ce este Digital Twin-ul locuinței", to: "/ghiduri/ce-este-digital-twin-locuinta" },
    ],
  },
  {
    slug: "compartimentare-cost-amenajare",
    title: "Cum influențează compartimentarea costul amenajării · Ghid 2026",
    h1: "Cum influențează compartimentarea costul amenajării",
    description: "Modificarea compartimentării schimbă radical bugetul unei amenajări. Ce înseamnă pereți structurali vs. despărțitori, ce se poate muta și cum planifici corect.",
    tag: "Planificare",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 7,
    sections: [
      {
        heading: "Compartimentarea = una dintre cele mai mari decizii de buget",
        body: [
          "Cum împarți spațiul influențează totul: câtă demolare faci, cât de mult muți instalațiile și cât mobilier pe comandă îți trebuie. O modificare de compartimentare bine gândită poate crește valoarea locuinței; una prost făcută poate scumpi inutil proiectul.",
        ],
      },
      {
        heading: "Pereți structurali vs. pereți despărțitori",
        body: [
          "Distincția e esențială pentru buget și pentru siguranță:",
          { type: "list", items: [
            "Pereții structurali (de rezistență) NU se modifică fără proiect și aviz de specialitate — orice intervenție e costisitoare și reglementată",
            "Pereții despărțitori (nestructurali) se pot muta sau elimina mai ușor, dar implică refacerea instalațiilor și finisajelor din zonă",
          ] },
          { type: "callout", title: "Atenție", body: "Nu dărâma niciodată un perete fără să știi dacă e structural. Un specialist confirmă rolul peretelui înainte de orice demolare." },
        ],
      },
      {
        heading: "Cum planifici ca să controlezi costul",
        body: [
          "Un proiect de design stabilește compartimentarea optimă ÎNAINTE de a începe lucrările, ținând cont de circulație, lumină și instalații. Randările 3D și un Digital Twin te ajută să vezi rezultatul înainte să investești.",
          "Regula practică: cu cât muți mai puțin instalațiile (bucătărie, baie), cu atât costul scade. Repoziționarea băii sau a bucătăriei e printre cele mai scumpe intervenții.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă mutarea unui perete despărțitor?", a: "Depinde de mărime, materiale și dacă trebuie refăcute instalații și finisaje în zonă. Un deviz corect vine dintr-un proiect de design care ia în calcul toate consecințele." },
      { q: "Pot transforma un apartament de 2 camere în open-space?", a: "Adesea da, dacă peretele dintre living și bucătărie nu e structural. Un specialist confirmă, iar un designer optimizează noul spațiu." },
      { q: "De ce e scumpă mutarea băii sau bucătăriei?", a: "Pentru că implică modificarea traseelor de apă, canalizare și ventilație — lucrări tehnice care cer și refacerea hidroizolației și finisajelor." },
    ],
    relatedCity: null,
    relatedCategories: ["interior_design"],
    internalLinks: [
      { label: "Design interior apartament", to: "/design-interior/apartament" },
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "De ce contează măsurătorile înainte de design", to: "/ghiduri/de-ce-conteaza-masuratorile-inainte-de-design" },
      { label: "Randări 3D & Digital Twin", to: "/design-interior/3d" },
      { label: "Cum pregătești apartamentul pentru renovare", to: "/ghiduri/cum-pregatesti-apartament-renovare" },
    ],
  },
  {
    slug: "ce-documente-verifici-cumparare-apartament",
    title: "Ce documente verifici înainte să cumperi un apartament · Ghid 2026",
    h1: "Ce documente trebuie verificate înainte de cumpărarea unui apartament",
    description: "Lista completă de acte de verificat înainte de a cumpăra un apartament: extras de carte funciară, intabulare, sarcini, certificat energetic, situația la asociație.",
    tag: "Cumpărare sigură",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 7,
    sections: [
      {
        heading: "De ce contează documentele",
        body: [
          "O parte din riscurile la cumpărare nu se văd la vizionare — ele sunt în acte. Verificarea documentelor înainte de antecontract te protejează de datorii, sarcini sau litigii moștenite odată cu apartamentul.",
          "Verificarea juridică se completează cu una tehnică: un **audit al locuinței** îți arată starea reală a instalațiilor și structurii. Vezi și programul **Imobile Verificate**, unde apartamentele au deja audit tehnic și Digital Twin.",
        ],
      },
      {
        heading: "Documentele esențiale",
        body: [
          { type: "list", items: [
            "Extras de carte funciară actualizat (proprietar, suprafață, sarcini)",
            "Dovada intabulării și a dreptului de proprietate",
            "Sarcini/ipoteci/interdicții înscrise în CF",
            "Certificatul de performanță energetică",
            "Situația la zi a cheltuielilor de întreținere (fără restanțe)",
            "Actele de identitate ale vânzătorilor și, dacă e cazul, acordul soț/soție",
            "Autorizații pentru eventuale modificări (extinderi, recompartimentări)",
          ] },
          { type: "callout", title: "Atenție", body: "Un extras de carte funciară de informare nu blochează tranzacția. Pentru siguranță, notarul obține un extras pentru autentificare chiar înainte de semnare." },
        ],
      },
      {
        heading: "Documente + verificare tehnică = decizie completă",
        body: [
          "Actele îți spun ce cumperi din punct de vedere juridic; auditul tehnic îți spune ce cumperi din punct de vedere fizic. Împreună îți dau o imagine completă înainte să semnezi.",
        ],
      },
    ],
    faq: [
      { q: "Cine verifică documentele apartamentului?", a: "Notarul verifică situația juridică la autentificare, dar e recomandat să ceri extrasul de carte funciară și situația la asociație din timp. Un avocat te poate ajuta la tranzacții complexe." },
      { q: "Ce e mai important, verificarea juridică sau cea tehnică?", a: "Ambele. Verificarea juridică previne probleme de proprietate și datorii; cea tehnică previne costuri ascunse de reparații. Programul Imobile Verificate le combină." },
      { q: "Pot cumpăra un apartament cu restanțe la întreținere?", a: "Poți, dar restanțele pot trece parțial în sarcina noului proprietar în anumite condiții. Cere situația la zi de la asociație înainte de a semna." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Imobile Verificate — cum funcționează", to: "/imobile-verificate" },
      { label: "Verificare apartament înainte de cumpărare", to: "/ghiduri/verificare-apartament-inainte-de-cumparare" },
      { label: "Ce probleme tehnice urmărești", to: "/ghiduri/probleme-tehnice-apartament-inainte-cumparare" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Audit tehnic apartament: preț", to: "/ghiduri/audit-tehnic-apartament-pret" },
    ],
  },
  {
    slug: "probleme-tehnice-apartament-inainte-cumparare",
    title: "Ce probleme tehnice urmărești înainte să cumperi un apartament · Ghid 2026",
    h1: "Ce probleme tehnice trebuie urmărite înainte de cumpărare",
    description: "Checklist tehnic la vizionare: instalații electrice și sanitare, umezeală, structură, izolație și tâmplărie. Ce semne de alarmă te feresc de costuri ascunse.",
    tag: "Cumpărare sigură",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 8,
    sections: [
      {
        heading: "Ce nu se vede la o vizionare rapidă",
        body: [
          "Un apartament proaspăt zugrăvit poate ascunde probleme costisitoare. Cele mai scumpe defecte sunt cele tehnice — instalații, structură, umezeală — care apar după ce ai cumpărat.",
          "Pentru o evaluare obiectivă, un **audit tehnic** verifică sistematic aceste puncte. În programul **Imobile Verificate**, apartamentele au deja acest audit + un **Digital Twin** al locuinței.",
        ],
      },
      {
        heading: "Checklist la vizionare",
        body: [
          { type: "list", items: [
            "Instalația electrică — tablou, vechime, prize suficiente, împământare",
            "Instalația sanitară — presiune, scurgeri, urme de umezeală sub chiuvete",
            "Umezeală și mucegai — colțuri, pereți exteriori, băi, sub geamuri",
            "Structura — fisuri în pereți, tavane, planeitatea pardoselii",
            "Izolația termică — apartamentele de colț și de la etaje extreme",
            "Tâmplăria — etanșeitate, condens între geamuri",
            "Încălzirea — starea caloriferelor sau a centralei",
          ] },
          { type: "callout", title: "Semnal de alarmă", body: "Pete proaspăt vopsite doar pe anumite porțiuni sau miros de umezeală pot indica infiltrații mascate. Cere să vezi apartamentul și pe vreme umedă, dacă e posibil." },
        ],
      },
      {
        heading: "De la impresie la certitudine",
        body: [
          "O vizionare atentă îți dă o primă impresie; un audit tehnic îți dă certitudinea. Diferența de cost dintre un audit și o reparație majoră neanticipată e uriașă în favoarea auditului.",
        ],
      },
    ],
    faq: [
      { q: "Merită un audit tehnic înainte de a cumpăra?", a: "Da. Costă o fracțiune din prețul unei reparații majore neanticipate (instalații, umezeală, structură) și îți dă o bază de negociere reală." },
      { q: "Pot verifica singur un apartament?", a: "Poți face o verificare de bază cu acest checklist, dar un specialist detectează probleme ascunse (instalații, structură) pe care ochiul neexperimentat le ratează." },
      { q: "Ce înseamnă un imobil deja verificat?", a: "Un apartament din programul Imobile Verificate a trecut printr-un audit tehnic complet și are un Digital Twin — vezi starea reală înainte de vizionarea fizică." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Imobile Verificate", to: "/imobile-verificate" },
      { label: "Ce documente verifici la cumpărare", to: "/ghiduri/ce-documente-verifici-cumparare-apartament" },
      { label: "Riscuri la cumpărarea într-un bloc vechi", to: "/ghiduri/riscuri-cumparare-apartament-bloc-vechi" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Ce este Digital Twin-ul locuinței", to: "/ghiduri/ce-este-digital-twin-locuinta" },
    ],
  },
  {
    slug: "verificare-imobil-digital-twin",
    title: "Cum se leagă verificarea unui imobil de Digital Twin · Ghid 2026",
    h1: "Cum se leagă verificarea unui imobil de Digital Twin",
    description: "Ce este un Digital Twin al locuinței, cum se creează din audit și cum te ajută să vezi starea reală a unui apartament înainte de cumpărare sau renovare.",
    tag: "Digital Twin",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 6,
    sections: [
      {
        heading: "De la audit la Digital Twin",
        body: [
          "Verificarea unui imobil produce date: starea instalațiilor, a structurii, a finisajelor. Un **Digital Twin** transformă aceste date într-o reprezentare digitală a locuinței — o hartă vie a proprietății, nu doar un dosar de hârtii.",
          "Astfel, ce descoperă auditul devine vizibil și ușor de înțeles, iar informația rămâne legată de locuință în timp, în **Cartea Casei**.",
        ],
      },
      {
        heading: "Ce vezi într-un Digital Twin",
        body: [
          { type: "list", items: [
            "Structura și compartimentarea locuinței",
            "Starea sistemelor verificate la audit",
            "Istoricul lucrărilor și al intervențiilor",
            "Documente și rapoarte legate de proprietate",
          ] },
          { type: "callout", title: "De ce contează la cumpărare", body: "Un Digital Twin îți permite să înțelegi apartamentul înainte de vizionarea fizică — vezi starea reală, nu doar fotografiile de prezentare." },
        ],
      },
      {
        heading: "Verificare + Twin = încredere",
        body: [
          "În programul Imobile Verificate, apartamentele publicate au un audit tehnic complet ȘI un Digital Twin. Combinația transformă o promisiune („apartament în stare bună”) într-o dovadă verificabilă.",
        ],
      },
    ],
    faq: [
      { q: "Ce este mai exact un Digital Twin al locuinței?", a: "O reprezentare digitală a apartamentului, care leagă structura, starea sistemelor și documentele într-un singur loc — actualizabilă în timp." },
      { q: "Am nevoie de Digital Twin dacă doar cumpăr?", a: "Te ajută să înțelegi apartamentul înainte de vizionare și îți rămâne util după achiziție, ca bază pentru Cartea Casei și pentru renovări viitoare." },
      { q: "Cum obțin un Digital Twin pentru apartamentul meu?", a: "Se creează în urma unui audit/scanare a locuinței. Pentru apartamentele din Imobile Verificate, twin-ul e inclus în proces." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Imobile Verificate", to: "/imobile-verificate" },
      { label: "Ce este Digital Twin-ul locuinței", to: "/ghiduri/ce-este-digital-twin-locuinta" },
      { label: "Pagina Digital Twin", to: "/digital-twin" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Ce probleme tehnice urmărești", to: "/ghiduri/probleme-tehnice-apartament-inainte-cumparare" },
    ],
  },
  {
    slug: "riscuri-cumparare-apartament-bloc-vechi",
    title: "Riscuri la cumpărarea unui apartament într-un bloc vechi · Ghid 2026",
    h1: "Riscuri la cumpărarea unui apartament într-un bloc vechi",
    description: "Ce riști când cumperi într-un bloc vechi: instalații depășite, risc seismic, izolație slabă, costuri de reabilitare. Cum le verifici și cum le negociezi.",
    tag: "Cumpărare sigură",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 8,
    sections: [
      {
        heading: "Blocurile vechi: farmec și capcane",
        body: [
          "Apartamentele din blocuri vechi pot fi spațioase și bine poziționate, dar vin cu riscuri specifice care nu se văd la o vizionare rapidă. A le cunoaște înainte te ajută să negociezi corect sau să eviți o achiziție proastă.",
        ],
      },
      {
        heading: "Principalele riscuri de verificat",
        body: [
          { type: "list", items: [
            "Risc seismic — verifică dacă blocul e pe lista clădirilor cu risc (mai ales construcțiile dinainte de normele moderne)",
            "Instalații depășite — electrice și sanitare care necesită înlocuire completă",
            "Izolație termică slabă — facturi mari și disconfort",
            "Structura și fisurile — semne de tasare sau degradare",
            "Fondul de reparații al asociației — reabilitări majore care urmează",
            "Umezeală și infiltrații — mai ales la parter și ultimul etaj",
          ] },
          { type: "callout", title: "Cheia deciziei", body: "Un audit tehnic îți spune cât ar costa aducerea apartamentului la o stare bună — o cifră care schimbă complet negocierea prețului." },
        ],
      },
      {
        heading: "Cum te protejezi",
        body: [
          "Comandă un audit tehnic înainte de antecontract, cere situația juridică și fondul de reparații de la asociație, și folosește costul estimat al reparațiilor ca argument de negociere. Programul **Imobile Verificate** oferă apartamente care au trecut deja prin această verificare.",
        ],
      },
    ],
    faq: [
      { q: "Merită să cumpăr într-un bloc vechi?", a: "Poate merita, dacă prețul reflectă starea reală și costul reparațiilor necesare. Un audit tehnic îți dă cifra exactă pentru a decide informat." },
      { q: "Cum aflu dacă blocul are risc seismic?", a: "Există liste publice ale clădirilor încadrate în clase de risc seismic. Verifică adresa înainte de a face o ofertă; un specialist te poate ghida." },
      { q: "Cât cresc costurile ascunse la un apartament vechi?", a: "Depinde de stare, dar reabilitarea instalațiilor, tâmplăriei și finisajelor poate ajunge la o sumă semnificativă. Auditul o estimează înainte să cumperi." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Imobile Verificate", to: "/imobile-verificate" },
      { label: "Ce probleme tehnice urmărești la cumpărare", to: "/ghiduri/probleme-tehnice-apartament-inainte-cumparare" },
      { label: "Ce documente verifici la cumpărare", to: "/ghiduri/ce-documente-verifici-cumparare-apartament" },
      { label: "Design pentru renovare", to: "/design-interior/renovare" },
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
    ],
  },
  {
    slug: "scorul-casei-ce-masoara",
    title: "Scorul Casei: ce măsoară și cum îl îmbunătățești · Ghid 2026",
    h1: "Scorul Casei: ce măsoară și cum îl îmbunătățești",
    description: "Ce este Scorul Casei, ce evaluează (instalații, structură, izolație, documente) și cum îl crești prin mentenanță și lucrări prioritizate. Ghid practic.",
    tag: "Audit locuință",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 6,
    sections: [
      {
        heading: "Ce este Scorul Casei",
        body: [
          "Scorul Casei este o evaluare a stării reale a locuinței tale — o notă care sintetizează cât de bine stau sistemele importante ale casei. Îți arată, dintr-o privire, unde ești și ce merită rezolvat întâi.",
          "Este punctul de plecare pentru un plan de mentenanță realist și pentru orice decizie de renovare sau vânzare.",
        ],
      },
      {
        heading: "Ce evaluează",
        body: [
          { type: "list", items: [
            "Instalațiile electrice și sanitare",
            "Structura și eventualele fisuri sau tasări",
            "Izolația termică și confortul energetic",
            "Umezeala, infiltrațiile și riscul de mucegai",
            "Documentele și istoricul locuinței",
          ] },
          { type: "callout", title: "De reținut", body: "Scorul nu e o notă fixă: se îmbunătățește pe măsură ce rezolvi problemele prioritare. Fiecare lucrare finalizată corect crește scorul." },
        ],
      },
      {
        heading: "Cum îl îmbunătățești",
        body: [
          "Pornește de la recomandările prioritare, rezolvă întâi problemele tehnice (instalații, umezeală), apoi finisajele. Un plan de mentenanță menține scorul ridicat în timp, iar istoricul lucrărilor rămâne în Cartea Casei — util și la o eventuală vânzare.",
        ],
      },
    ],
    faq: [
      { q: "Cum obțin Scorul Casei?", a: "Pornești de la o evaluare a locuinței. Cu cât ai mai multe date verificate (audit tehnic, documente), cu atât scorul e mai precis." },
      { q: "Un scor mai mare crește valoarea locuinței?", a: "Da — o locuință cu sisteme verificate și probleme rezolvate e mai atractivă și mai ușor de vândut, mai ales în programul Imobile Verificate." },
      { q: "Cât de des ar trebui reevaluată casa?", a: "Ideal, odată pe an sau după lucrări importante. Mentenanța regulată menține scorul ridicat și previne problemele scumpe." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Cum îți faci un plan de mentenanță", to: "/ghiduri/plan-mentenanta-locuinta" },
      { label: "Cartea Casei: de ce contează istoricul", to: "/ghiduri/cartea-casei-istoric-locuinta" },
      { label: "Imobile Verificate", to: "/imobile-verificate" },
      { label: "Ce este Digital Twin-ul locuinței", to: "/ghiduri/ce-este-digital-twin-locuinta" },
    ],
  },
  {
    slug: "plan-mentenanta-locuinta",
    title: "Cum îți faci un plan de mentenanță pentru locuință · Ghid 2026",
    h1: "Cum îți faci un plan de mentenanță pentru locuință",
    description: "Un plan de mentenanță simplu îți protejează casa și bugetul: verificări sezoniere, revizii la instalații, prevenirea umezelii. Checklist practic pe tot anul.",
    tag: "Mentenanță",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 7,
    sections: [
      {
        heading: "De ce ai nevoie de un plan",
        body: [
          "Mentenanța reactivă (repari doar când se strică) e cea mai scumpă. Un plan simplu de verificări periodice previne defecțiunile mari și menține Scorul Casei ridicat.",
        ],
      },
      {
        heading: "Checklist sezonier",
        body: [
          { type: "list", items: [
            "Primăvara: verifică acoperișul, jgheaburile, fațada și semnele de umezeală",
            "Vara: revizie la instalația de climatizare și ventilație",
            "Toamna: verifică centrala termică, caloriferele și etanșeitatea tâmplăriei",
            "Iarna: monitorizează condensul, umiditatea și izolația",
            "Anual: revizie electrică și sanitară, curățarea coșurilor/ventilațiilor",
          ] },
          { type: "callout", title: "Sfat", body: "Notează fiecare intervenție (dată, ce s-a făcut, cine). Istoricul devine parte din Cartea Casei și îți crește Scorul." },
        ],
      },
      {
        heading: "De la plan la istoric",
        body: [
          "Un plan de mentenanță aplicat constant transformă casa dintr-o sursă de surprize într-un activ îngrijit. Istoricul lucrărilor, păstrat în Cartea Casei, e util și pentru specialiști, și la o eventuală vânzare.",
        ],
      },
    ],
    faq: [
      { q: "Cât timp îmi ia mentenanța?", a: "Câteva verificări pe sezon, majoritatea rapide. Reviziile la instalații se fac de un specialist o dată pe an. Efortul e mic față de costul unei defecțiuni majore." },
      { q: "Cum leg mentenanța de Scorul Casei?", a: "Fiecare lucrare corect făcută și documentată menține sau crește scorul. Mentenanța regulată e cea mai simplă cale de a păstra un scor bun." },
      { q: "Unde țin evidența lucrărilor?", a: "În Cartea Casei — istoricul locuinței într-un singur loc, accesibil când ai nevoie (reparații, vânzare, garanții)." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Scorul Casei: ce măsoară", to: "/ghiduri/scorul-casei-ce-masoara" },
      { label: "Cartea Casei: de ce contează istoricul", to: "/ghiduri/cartea-casei-istoric-locuinta" },
      { label: "Ce probleme tehnice urmărești", to: "/ghiduri/probleme-tehnice-apartament-inainte-cumparare" },
      { label: "Imobile Verificate", to: "/imobile-verificate" },
    ],
  },
  {
    slug: "cartea-casei-istoric-locuinta",
    title: "Cartea Casei: de ce contează istoricul locuinței · Ghid 2026",
    h1: "Cartea Casei: de ce contează istoricul locuinței",
    description: "Ce este Cartea Casei, de ce merită să păstrezi istoricul lucrărilor și al documentelor și cum te ajută la mentenanță, garanții și vânzare. Ghid practic.",
    tag: "Cartea Casei",
    icon: "BookOpen",
    publishedAt: "2026-06-16",
    updatedAt: "2026-06-16",
    readMins: 6,
    sections: [
      {
        heading: "Ce este Cartea Casei",
        body: [
          "Cartea Casei este istoricul digital al locuinței tale: documente, lucrări, revizii, garanții și starea sistemelor, într-un singur loc. E memoria casei — utilă exact când ai nevoie de ea.",
        ],
      },
      {
        heading: "De ce contează istoricul",
        body: [
          { type: "list", items: [
            "La reparații: specialiștii văd ce s-a făcut și cu ce materiale",
            "La garanții: găsești rapid facturile și termenele",
            "La mentenanță: știi când a fost ultima revizie",
            "La vânzare: un istoric complet crește încrederea și valoarea",
          ] },
          { type: "callout", title: "Legătura cu verificarea", body: "În programul Imobile Verificate, istoricul și starea verificată a locuinței (audit + Digital Twin) devin o dovadă pentru cumpărător, nu doar o promisiune." },
        ],
      },
      {
        heading: "Cum o construiești",
        body: [
          "Adaugă treptat documentele și lucrările pe măsură ce apar. Combinată cu un plan de mentenanță și cu Scorul Casei, Cartea Casei transformă locuința într-un activ îngrijit și transparent.",
        ],
      },
    ],
    faq: [
      { q: "De ce să țin istoricul locuinței?", a: "Pentru că îți economisește timp și bani la reparații, garanții și vânzare, și crește încrederea unui viitor cumpărător." },
      { q: "Cum se leagă Cartea Casei de Scorul Casei?", a: "Scorul reflectă starea; Cartea Casei păstrează istoricul care susține scorul. Împreună dau o imagine completă și credibilă a locuinței." },
      { q: "Ajută la vânzare?", a: "Da. Un istoric complet și un scor bun fac locuința mai atractivă, mai ales listată ca Imobil Verificat cu audit și Digital Twin." },
    ],
    relatedCity: null,
    relatedCategories: [],
    internalLinks: [
      { label: "Verifică Scorul Casei", to: "/scorul-casei" },
      { label: "Scorul Casei: ce măsoară", to: "/ghiduri/scorul-casei-ce-masoara" },
      { label: "Cum îți faci un plan de mentenanță", to: "/ghiduri/plan-mentenanta-locuinta" },
      { label: "Imobile Verificate", to: "/imobile-verificate" },
      { label: "Cum se leagă verificarea de Digital Twin", to: "/ghiduri/verificare-imobil-digital-twin" },
    ],
  }
];

export const getGhidBySlug = (slug) => GHIDURI.find(g => g.slug === slug);
export const getAllGhidSlugs = () => GHIDURI.map(g => g.slug);
