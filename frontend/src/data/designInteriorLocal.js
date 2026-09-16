// Local Design Interior content — UNIQUE, factual per-city editorial content.
// A city page is INDEX only if it appears here with distinct, useful content.
// Cities NOT present here render a minimal template and stay NOINDEX (canonical
// to /design-interior). No invented designers, projects, clients or addresses.
//
// Structure per city:
//   { name, intro, sections[{ h2, body[], bullets[] }], faq[{ q, a }], related[{ to, label }] }

export const DI_LOCAL_CONTENT = {
  "cluj-napoca": {
    name: "Cluj-Napoca",
    intro:
      "Cluj-Napoca are una dintre cele mai dinamice piețe rezidențiale din România, împinsă de sectorul IT și de universități. Aici designul interior nu înseamnă doar estetică: înseamnă să scoți maximum dintr-un apartament nou, adesea compact, sau să reabilitezi un bloc mai vechi din centru. Pe PropManage lucrezi cu designeri verificați, iar proiectul se leagă direct de execuție: Design → Audit → Digital Twin → Implementare, cu plată protejată prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în Cluj",
        body: [
          "Fondul locativ clujean e împărțit între câteva categorii cu nevoi foarte diferite. Un proiect bun pornește de la ce ai concret, nu de la un moodboard generic.",
        ],
        bullets: [
          "**Apartamente noi** în zone precum Bună Ziua, Sopor, Borhanci sau Florești — adesea suprafețe mici, cu open-space și necesar mare de depozitare",
          "**Blocuri din perioada comunistă** în Mărăști, Gheorgheni, Zorilor, Grigorescu — compartimentări rigide care cer regândite pentru lumină și circulație",
          "**Apartamente în clădiri interbelice** din centru și Andrei Mureșanu — tavane înalte, dar instalații și izolații care necesită atenție",
          "**Case și vile** în Făget, Gruia sau comunele limitrofe (Florești, Apahida) — proiecte mai ample, cu logică de zi/noapte",
        ],
      },
      {
        h2: "Nevoi și provocări specifice pieței din Cluj",
        body: [
          "Prețul pe metru pătrat ridicat din Cluj schimbă prioritățile: fiecare metru contează, iar greșelile de amenajare costă mult. Cele mai frecvente cerințe pe care le vedem:",
        ],
        bullets: [
          "Birou de acasă (home office) integrat, pentru cei care lucrează în IT sau remote",
          "Depozitare până în tavan și soluții pentru apartamente de 1–2 camere",
          "Izolație fonică între apartamente și către casa scării, în blocurile noi",
          "Reabilitarea instalațiilor înainte de finisaje, în blocurile vechi",
        ],
      },
      {
        h2: "Cum lucrăm în Cluj-Napoca",
        body: [
          "Procesul e același indiferent de zonă, dar adaptat la locuința ta reală. Începem cu releveul și analiza spațiului, apoi conceptul și randările, iar dacă vrei mergem până la implementare cu specialiști verificați.",
          "Pentru apartamentele mai vechi recomandăm un **audit tehnic** înainte de a stabili bugetul de finisaje — ca să nu descoperi surprize (instalații, umezeală) după ce ai turnat șapa. Vezi și **Scorul Casei** pentru o evaluare rapidă a stării locuinței.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Cluj-Napoca?", a: "Un concept de amenajare pornește de la câteva sute de lei pe cameră, iar un proiect tehnic complet se calculează pe metru pătrat. Prețul depinde de suprafață, complexitate și dacă incluzi randări 3D. Vezi ghidul detaliat despre cât costă designul interior în Cluj." },
      { q: "Găsesc designeri verificați activi în Cluj?", a: "Da. Pe pagina de mai jos vezi designerii verificați care acoperă zona Cluj-Napoca, cu portofolii și recenzii reale. Dacă lista e scurtă la un moment dat, poți posta o cerere și îți aducem oferte de la designeri care lucrează în zonă." },
      { q: "Merită designul interior pentru un apartament mic din Cluj?", a: "Mai ales pentru un apartament mic. Aici un metru prost folosit se simte imediat, iar un designer bun rezolvă depozitarea, circulația și lumina cu un buget bine țintit." },
    ],
    related: [
      { to: "/ghiduri/cat-costa-design-interior-cluj", label: "Cât costă designul interior în Cluj?" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate din Cluj" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "bucuresti": {
    name: "București",
    intro:
      "Bucureștiul este cea mai mare și mai variată piață rezidențială din România — de la apartamente interbelice din Cotroceni și Dorobanți, la blocuri comuniste din Titan sau Drumul Taberei, până la ansambluri noi din Pipera și Băneasa. Fiecare tip de locuință cere o altă abordare de design. Pe PropManage lucrezi cu designeri verificați, iar proiectul se leagă de execuția reală prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în București",
        body: [
          "Diversitatea fondului locativ bucureștean e cea mai mare provocare — și cea mai mare oportunitate — pentru un proiect de design.",
        ],
        bullets: [
          "**Apartamente interbelice** (Cotroceni, Dorobanți, Armenească) — tavane înalte, parchet original, dar instalații de refăcut",
          "**Blocuri din anii '70–'80** (Titan, Berceni, Drumul Taberei, Militari) — compartimentări mici care cer optimizare",
          "**Ansambluri noi** (Pipera, Băneasa, Sisești, Politehnica) — open-space și necesar de personalizare a finisajelor",
          "**Garsoniere și studiouri** — piață mare de închiriere, unde amenajarea inteligentă crește valoarea",
        ],
      },
      {
        h2: "Nevoi și provocări specifice Bucureștiului",
        body: [
          "Zgomotul urban, traficul și diversitatea clădirilor aduc cerințe recurente pe care le rezolvăm din faza de proiect:",
        ],
        bullets: [
          "Izolație fonică și termică, mai ales la apartamentele vechi și la parter/ultimul etaj",
          "Optimizarea spațiilor mici pentru închiriere sau primul apartament",
          "Refacerea instalațiilor electrice și sanitare în clădirile vechi, înainte de finisaje",
          "Soluții de depozitare pentru locuințe fără debara sau boxă",
        ],
      },
      {
        h2: "Cum lucrăm în București",
        body: [
          "De la releveu și concept, la randări 3D și, opțional, implementare la cheie cu specialiști verificați. Pentru apartamentele vechi, un **audit tehnic** înainte de finisaje previne surprizele costisitoare (umezeală, instalații învechite).",
          "Dacă plănuiești și o achiziție, vezi programul **Imobile Verificate** — apartamente cu audit tehnic și Digital Twin, ca să știi exact ce cumperi înainte să amenajezi.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în București?", a: "Un concept pornește de la câteva sute de lei pe cameră; un proiect tehnic complet se calculează pe metru pătrat și crește cu complexitatea și randările 3D. Vezi pagina de preț pentru factorii reali." },
      { q: "Aveți designeri verificați în București?", a: "Da, Bucureștiul are cei mai mulți designeri verificați din rețea. Vezi mai jos profilurile active, cu portofolii și recenzii reale, sau postează o cerere pentru oferte." },
      { q: "Merită să fac audit înainte de amenajare la un apartament vechi?", a: "Da. La clădirile interbelice și la blocurile vechi, auditul tehnic îți arată ce trebuie refăcut la instalații și izolații înainte de finisaje — și îți protejează bugetul." },
    ],
    related: [
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/apartament-vechi", label: "Design apartament vechi" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate din București" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "timisoara": {
    name: "Timișoara",
    intro:
      "Timișoara îmbină un centru istoric de patrimoniu — cu arhitectură secession și austro-ungară în Cetate, Fabric și Iosefin — cu ansambluri rezidențiale noi în Dumbrăvița și Giroc. Designul interior aici oscilează între restaurarea apartamentelor cu tavane înalte și amenajarea locuințelor moderne. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în Timișoara",
        body: [
          "Fondul locativ timișorean e marcat de contrastul dintre clădirile istorice din centru și dezvoltările noi de la marginea orașului.",
        ],
        bullets: [
          "**Apartamente în clădiri istorice** (Cetate, Iosefin, Fabric) — tavane înalte, tâmplărie de epocă, uși duble; cer respect pentru caracterul clădirii",
          "**Blocuri din perioada comunistă** (Circumvalațiunii, Girocului, Soarelui) — compartimentări de optimizat",
          "**Ansambluri noi** (Dumbrăvița, Giroc, Torontalului) — finisaje și open-space de personalizat",
          "**Case** în zonele rezidențiale și comunele limitrofe",
        ],
      },
      {
        h2: "Nevoi și provocări specifice Timișoarei",
        body: [
          "Patrimoniul istoric aduce cerințe aparte, iar zonele noi au nevoile lor:",
        ],
        bullets: [
          "Valorificarea tavanelor înalte și a luminii în apartamentele din centru, fără a strica elementele de epocă",
          "Refacerea instalațiilor și izolării în clădirile vechi, unde intervențiile sunt sensibile",
          "Amenajarea eficientă a apartamentelor noi din Dumbrăvița și Giroc",
          "Soluții de încălzire și izolare pentru spațiile generoase de epocă",
        ],
      },
      {
        h2: "Cum lucrăm în Timișoara",
        body: [
          "Pornim de la releveu și concept, cu atenție la caracterul clădirii, apoi randări 3D și, opțional, implementare cu specialiști verificați. La apartamentele de epocă recomandăm un **audit tehnic** înainte de finisaje.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Timișoara?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat. Apartamentele de epocă pot necesita etape suplimentare (relevee detaliate), reflectate în preț." },
      { q: "Se poate amenaja modern un apartament de epocă din centrul Timișoarei?", a: "Da, cu echilibru: se păstrează elementele valoroase (tâmplărie, stucaturi, tavane înalte) și se adaugă confort și funcțiuni moderne. Un designer bun face această tranziție fără să strice caracterul clădirii." },
      { q: "Găsesc designeri verificați în Timișoara?", a: "Vezi mai jos designerii verificați care acoperă zona. Dacă lista e scurtă, poți posta o cerere și primești oferte de la specialiști din regiune." },
    ],
    related: [
      { to: "/design-interior/apartament-vechi", label: "Design apartament vechi" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "brasov": {
    name: "Brașov",
    intro:
      "Brașovul combină un centru istoric săsesc de patrimoniu cu blocuri din perioada comunistă și zone rezidențiale la poalele munților. Aproprierea de munte și turismul aduc o cerere aparte: amenajări cu accent natural și locuințe gândite și pentru închiriere. Pe PropManage lucrezi cu designeri verificați, cu proiectul legat de execuția reală prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în Brașov",
        body: [
          "Fondul locativ brașovean e variat, de la case istorice în Schei la apartamente în cartiere dense și locuințe noi spre munte.",
        ],
        bullets: [
          "**Apartamente și case în centrul istoric** (Centrul Vechi, Schei) — caracter aparte, elemente de patrimoniu",
          "**Blocuri comuniste** (Astra, Răcădău, Tractorul, Noua) — compartimentări de optimizat",
          "**Locuințe noi și case** spre Poiana Brașov, Bartolomeu, Stupini — proiecte cu accent pe confort și natură",
          "**Apartamente pentru închiriere turistică** — amenajare durabilă și ușor de întreținut",
        ],
      },
      {
        h2: "Nevoi și provocări specifice Brașovului",
        body: [
          "Clima montană și turismul modelează cerințele frecvente:",
        ],
        bullets: [
          "Izolație termică bună și încălzire eficientă, dat fiind clima mai rece",
          "Materiale naturale (lemn, piatră) care se potrivesc cadrului montan",
          "Amenajări rezistente și practice pentru apartamentele închiriate turiștilor",
          "Optimizarea locuințelor din blocurile din Răcădău și Astra",
        ],
      },
      {
        h2: "Cum lucrăm în Brașov",
        body: [
          "De la releveu și concept, la randări 3D și implementare cu specialiști verificați. Pentru locuințele mai vechi sau destinate închirierii, un **audit tehnic** înainte de finisaje ajută la un buget realist și la o amenajare durabilă.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Brașov?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Ce stil se potrivește unei locuințe brașovene spre munte?", a: "Stilurile cu materiale naturale — rustic, mediteranean cald sau scandinav — funcționează bine în cadru montan. Un designer adaptează stilul la locuință și la buget, fără clișee." },
      { q: "Aveți designeri verificați în Brașov?", a: "Vezi mai jos designerii verificați care acoperă zona Brașov. Poți vedea portofoliile și recenziile lor sau posta o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/stil/rustic", label: "Design interior stil rustic" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "iasi": {
    name: "Iași",
    intro:
      "Iașiul, capitala culturală a Moldovei și unul dintre cele mai mari centre universitare din țară, are o piață rezidențială modelată de studenți, tineri profesioniști și de un fond locativ variat — de la clădiri istorice în Copou, la blocuri dense în Tătărași și ansambluri noi spre Bucium. Pe PropManage lucrezi cu designeri verificați, iar proiectul se leagă de execuție prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în Iași",
        body: [
          "Fondul locativ ieșean acoperă extreme: apartamente istorice în zona universitară și blocuri comuniste dense, dar și dezvoltări noi pe dealurile din jur.",
        ],
        bullets: [
          "**Apartamente în zona Copou** — aproape de universitate, unele în clădiri vechi cu caracter",
          "**Blocuri comuniste** în Tătărași, Păcurari, Nicolina, Alexandru cel Bun — compartimentări de optimizat",
          "**Ansambluri noi** în zona Palas, Bucium, Aurel Vlaicu — finisaje și open-space de personalizat",
          "**Garsoniere pentru închiriere studențească** — amenajare practică și rezistentă",
        ],
      },
      {
        h2: "Nevoi și provocări specifice Iașiului",
        body: [
          "Populația studențească mare și terenul deluros aduc cerințe recurente:",
        ],
        bullets: [
          "Amenajări funcționale și durabile pentru apartamente închiriate studenților",
          "Optimizarea spațiilor mici din blocurile din Tătărași și Nicolina",
          "Depozitare inteligentă și birou de acasă pentru tineri profesioniști",
          "Reabilitarea instalațiilor în clădirile vechi din zona centrală",
        ],
      },
      {
        h2: "Cum lucrăm în Iași",
        body: [
          "De la releveu și concept, la randări 3D și, opțional, implementare cu specialiști verificați. Pentru apartamentele destinate închirierii sau pentru clădirile mai vechi, un **audit tehnic** înainte de finisaje ajută la un buget realist.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Iași?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Merită designul pentru un apartament de închiriat studenților?", a: "Da — o amenajare practică, durabilă și ușor de întreținut reduce uzura și crește atractivitatea. Un designer optimizează depozitarea și rezistența finisajelor cu buget controlat." },
      { q: "Aveți designeri verificați în Iași?", a: "Vezi mai jos designerii verificați care acoperă zona Iași. Poți vedea portofoliile și recenziile lor sau posta o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/apartament-mic", label: "Design apartament mic" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "sibiu": {
    name: "Sibiu",
    intro:
      "Sibiul are unul dintre cele mai bine păstrate centre istorice săsești din România, cu Orașul de Sus și Orașul de Jos, moștenire germană și un turism puternic. Aici designul interior echilibrează respectul pentru patrimoniu cu confortul modern, în apartamente istorice, blocuri comuniste și case noi spre Șelimbăr. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în Sibiu",
        body: [
          "Contrastul dintre centrul istoric și zonele rezidențiale noi definește proiectele sibiene.",
        ],
        bullets: [
          "**Apartamente și case în centrul istoric** (Orașul de Sus, Orașul de Jos) — caracter aparte, elemente de patrimoniu de respectat",
          "**Blocuri comuniste** în Ștrand, Hipodrom, Vasile Aaron — compartimentări de optimizat",
          "**Locuințe noi** în Șelimbăr, Calea Cisnădiei — finisaje de personalizat",
          "**Apartamente pentru închiriere turistică** — Sibiul e o destinație căutată",
        ],
      },
      {
        h2: "Nevoi și provocări specifice Sibiului",
        body: [
          "Patrimoniul și turismul modelează cerințele frecvente:",
        ],
        bullets: [
          "Restaurarea cu grijă a apartamentelor din centrul istoric, fără a strica elementele de epocă",
          "Amenajări durabile pentru apartamentele închiriate turiștilor",
          "Izolație termică bună pentru clima mai rece din zona montană apropiată",
          "Estetică inspirată de moștenirea germană, sobră și funcțională",
        ],
      },
      {
        h2: "Cum lucrăm în Sibiu",
        body: [
          "Pornim de la releveu și concept, cu atenție la caracterul clădirii, apoi randări 3D și, opțional, implementare cu specialiști verificați. La imobilele de patrimoniu, un **audit tehnic** înainte de finisaje e recomandat.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Sibiu?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat. Imobilele de patrimoniu pot necesita relevee detaliate, reflectate în preț." },
      { q: "Pot amenaja modern un apartament din centrul istoric al Sibiului?", a: "Da, cu echilibru: se păstrează elementele valoroase și se adaugă confort modern. Un designer bun face tranziția fără să afecteze caracterul clădirii." },
      { q: "Aveți designeri verificați în Sibiu?", a: "Vezi mai jos designerii verificați care acoperă zona. Dacă lista e scurtă, poți posta o cerere și primești oferte de la specialiști din regiune." },
    ],
    related: [
      { to: "/design-interior/apartament-vechi", label: "Design apartament vechi" },
      { to: "/design-interior/stil/classic", label: "Design interior stil clasic" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "oradea": {
    name: "Oradea",
    intro:
      "Oradea e recunoscută pentru arhitectura sa Art Nouveau (Secession) recent restaurată și moștenirea austro-ungară a centrului. Piața rezidențială combină apartamente în clădiri de patrimoniu cu blocuri comuniste în Rogerius și dezvoltări noi în Iosia. Turismul balnear și proximitatea de graniță adaugă cerințe aparte. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce tipuri de locuințe amenajăm în Oradea",
        body: [
          "Patrimoniul Art Nouveau și zonele noi coexistă în fondul locativ orădean.",
        ],
        bullets: [
          "**Apartamente în clădiri Art Nouveau / de epocă** din centru — detalii decorative, tavane înalte, de tratat cu respect",
          "**Blocuri comuniste** în Rogerius, Nufărul, Velența — compartimentări de optimizat",
          "**Locuințe noi** în Iosia, Oncea, spre Sânmartin — finisaje de personalizat",
          "**Apartamente pentru închiriere** (turism balnear Băile Felix) — amenajare durabilă",
        ],
      },
      {
        h2: "Nevoi și provocări specifice Oradei",
        body: [
          "Patrimoniul arhitectural și turismul balnear aduc cerințe frecvente:",
        ],
        bullets: [
          "Restaurarea atentă a apartamentelor de epocă, păstrând detaliile Art Nouveau",
          "Amenajări durabile pentru apartamentele închiriate în zona balneară",
          "Optimizarea locuințelor din blocurile din Rogerius și Nufărul",
          "Reabilitarea instalațiilor în clădirile vechi, înainte de finisaje",
        ],
      },
      {
        h2: "Cum lucrăm în Oradea",
        body: [
          "De la releveu și concept, cu atenție la caracterul clădirii, la randări 3D și, opțional, implementare cu specialiști verificați. La imobilele de patrimoniu recomandăm un **audit tehnic** înainte de finisaje.",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Oradea?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Se poate păstra caracterul Art Nouveau al unui apartament orădean?", a: "Da — un designer bun păstrează detaliile de epocă valoroase (stucaturi, tâmplărie, tavane înalte) și adaugă confort modern, fără să strice identitatea clădirii." },
      { q: "Aveți designeri verificați în Oradea?", a: "Vezi mai jos designerii verificați care acoperă zona. Poți vedea portofoliile și recenziile lor sau posta o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/apartament-vechi", label: "Design apartament vechi" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "floresti": {
    name: "Florești (Cluj)",
    intro:
      "Florești este cea mai mare comună din România și principala zonă de expansiune rezidențială a Clujului, cu mii de apartamente noi construite în ultimul deceniu. Este aleasă mai ales de tineri și familii care lucrează în Cluj-Napoca. Aici designul interior înseamnă, în cea mai mare parte, optimizarea apartamentelor noi, adesea compacte. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Florești",
        body: ["Fondul locativ este dominat de ansambluri noi, cu apartamente care cer soluții inteligente de spațiu."],
        bullets: [
          "Apartamente noi de 1-2-3 camere în ansambluri rezidențiale",
          "Open-space living-bucătărie de organizat funcțional",
          "Necesar mare de depozitare la suprafețe mici",
          "Amenajări pentru tineri navetiști și familii tinere",
        ],
      },
      {
        h2: "Nevoi specifice zonei Florești",
        body: ["Fiind o comună-dormitor cu apartamente în general compacte, prioritatea e maximizarea fiecărui metru pătrat."],
        bullets: [
          "Birou de acasă integrat pentru cei care lucrează remote sau în IT",
          "Depozitare până în tavan și mobilier pe comandă",
          "Zonă de zi deschisă, dar bine delimitată funcțional",
        ],
      },
    ],
    faq: [
      { q: "Merită designul interior pentru un apartament nou din Florești?", a: "Mai ales pentru un apartament compact dintr-un ansamblu nou. Un designer optimizează depozitarea, circulația și zona de zi, evitând cumpărături greșite de mobilier." },
      { q: "Găsesc designeri care lucrează în Florești?", a: "Da, mulți designeri din Cluj acoperă și Florești. Postează o cerere și primești oferte de la specialiști verificați care lucrează în zonă." },
    ],
    related: [
      { to: "/design-interior/cluj-napoca", label: "Design interior Cluj-Napoca" },
      { to: "/design-interior/apartament-mic", label: "Design apartament mic" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "baciu": {
    name: "Baciu (Cluj)",
    intro:
      "Baciu este o comună aflată la nord-vest de Cluj-Napoca, cu o creștere rezidențială accentuată în ultimii ani. Combină case individuale cu ansambluri noi de apartamente, într-un ritm mai liniștit decât orașul. Designul interior aici acoperă atât apartamente noi, cât și case. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Baciu",
        body: ["Zona are un mix echilibrat de locuințe noi și case, fiecare cu nevoi diferite de amenajare."],
        bullets: [
          "Apartamente noi în ansambluri rezidențiale",
          "Case individuale cu logică zi/noapte",
          "Amenajări pentru familii care caută liniște lângă Cluj",
        ],
      },
      {
        h2: "Nevoi specifice zonei Baciu",
        body: ["Proximitatea de Cluj și tipul locuințelor influențează cerințele."],
        bullets: [
          "Optimizarea apartamentelor noi și a caselor pe două niveluri",
          "Soluții practice de depozitare și confort pentru familii",
          "Coerență între design, buget și execuție",
        ],
      },
    ],
    faq: [
      { q: "Se amenajează case în Baciu, nu doar apartamente?", a: "Da. Casele individuale sunt frecvente în zonă și beneficiază de un proiect de design care organizează zonele de zi și noapte și optimizează circulația." },
      { q: "Aveți designeri care lucrează în Baciu?", a: "Designerii verificați din Cluj acoperă și zona Baciu. Postează o cerere pentru oferte reale." },
    ],
    related: [
      { to: "/design-interior/cluj-napoca", label: "Design interior Cluj-Napoca" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
    ],
  },

  "apahida": {
    name: "Apahida (Cluj)",
    intro:
      "Apahida este o comună aflată la est de Cluj-Napoca, cu o dezvoltare rezidențială și industrială importantă. Aici găsești case individuale și ansambluri noi, într-o zonă bine conectată la oraș. Designul interior acoperă atât locuințe noi, cât și case de familie. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Apahida",
        body: ["Zona combină ansambluri rezidențiale noi cu case, fiecare cu propriile cerințe."],
        bullets: [
          "Apartamente noi în ansambluri",
          "Case individuale și duplexuri",
          "Amenajări pentru familii care lucrează în Cluj",
        ],
      },
      {
        h2: "Nevoi specifice zonei Apahida",
        body: ["Tipul locuințelor și conexiunea cu orașul modelează prioritățile."],
        bullets: [
          "Organizarea eficientă a caselor pe niveluri",
          "Depozitare și funcționalitate pentru familii",
          "Legătura clară între proiect și execuție",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Apahida?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Găsesc designeri pentru Apahida?", a: "Da, designerii verificați din zona Cluj acoperă și Apahida. Postează o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/cluj-napoca", label: "Design interior Cluj-Napoca" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "marasti-cluj": {
    name: "Mărăști (Cluj-Napoca)",
    intro:
      "Mărăști este unul dintre cele mai dense și mai bine conectate cartiere din Cluj-Napoca, cu blocuri din perioada comunistă și zone comerciale active. Aici designul interior înseamnă în principal optimizarea apartamentelor din blocuri, cu compartimentări rigide de regândit. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Mărăști",
        body: ["Cartierul e dominat de apartamente în blocuri, cu potențial mare de optimizare."],
        bullets: [
          "Apartamente în blocuri anii 70-80, cu compartimentări rigide",
          "Garsoniere și apartamente de 2-3 camere de reorganizat",
          "Spații mici unde lumina și depozitarea sunt cruciale",
        ],
      },
      {
        h2: "Nevoi specifice cartierului Mărăști",
        body: ["Fondul locativ mai vechi cere atenție la partea tehnică înainte de finisaje."],
        bullets: [
          "Reabilitarea instalațiilor electrice și sanitare",
          "Reorganizarea compartimentării pentru lumină și circulație",
          "Izolație fonică între apartamente",
        ],
      },
    ],
    faq: [
      { q: "Merită renovarea unui apartament vechi din Mărăști?", a: "Da, dacă pornești de la o evaluare corectă a stării. Un audit tehnic înainte de finisaje îți arată ce trebuie refăcut la instalații și te ferește de surprize." },
      { q: "Aveți designeri în zona Mărăști?", a: "Designerii verificați din Cluj acoperă toate cartierele, inclusiv Mărăști. Postează o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/cluj-napoca", label: "Design interior Cluj-Napoca" },
      { to: "/design-interior/apartament-vechi", label: "Design apartament vechi" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "gheorgheni-cluj": {
    name: "Gheorgheni (Cluj-Napoca)",
    intro:
      "Gheorgheni este un cartier rezidențial consacrat din Cluj-Napoca, cu blocuri din anii 70-80, spații verzi și proximitate față de zone comerciale importante. Aici designul interior se concentrează pe modernizarea apartamentelor din blocuri, păstrând confortul cartierului. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Gheorgheni",
        body: ["Cartierul are un fond locativ matur, cu apartamente care beneficiază de modernizare."],
        bullets: [
          "Apartamente în blocuri anii 70-80, solide dar de modernizat",
          "Apartamente de 2-3 camere de reorganizat funcțional",
          "Amenajări pentru familii stabile și profesioniști",
        ],
      },
      {
        h2: "Nevoi specifice cartierului Gheorgheni",
        body: ["Modernizarea apartamentelor mature cere atenție la instalații și finisaje."],
        bullets: [
          "Actualizarea instalațiilor înainte de finisaje noi",
          "Optimizarea depozitării și a zonei de zi",
          "Confort termic și fonic",
        ],
      },
    ],
    faq: [
      { q: "Cât costă modernizarea unui apartament în Gheorgheni?", a: "Depinde de suprafață și de intervenții. Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat." },
      { q: "Aveți designeri în Gheorgheni?", a: "Da, designerii verificați din Cluj acoperă și cartierul Gheorgheni. Postează o cerere pentru oferte reale." },
    ],
    related: [
      { to: "/design-interior/cluj-napoca", label: "Design interior Cluj-Napoca" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
    ],
  },

  "baneasa": {
    name: "Băneasa (București)",
    intro:
      "Băneasa este o zonă premium din nordul Bucureștiului, cunoscută pentru vile, ansambluri rezidențiale de lux și proximitatea față de pădure și aeroport. Aici designul interior lucrează cu spații generoase și cerințe ridicate de finisaj. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Băneasa",
        body: ["Zona are locuințe premium, de la apartamente în ansambluri noi la vile."],
        bullets: [
          "Vile și case individuale cu suprafețe generoase",
          "Apartamente în ansambluri rezidențiale de lux",
          "Cerințe ridicate de finisaje și materiale",
        ],
      },
      {
        h2: "Nevoi specifice zonei Băneasa",
        body: ["Standardul premium al zonei aduce cerințe aparte."],
        bullets: [
          "Materiale nobile și detalii de calitate",
          "Integrare smart-home și confort acustic",
          "Coerență între concept, randări și execuție impecabilă",
        ],
      },
    ],
    faq: [
      { q: "Ce buget presupune designul într-o vilă din Băneasa?", a: "Proiectul se calculează pe metru pătrat și crește cu nivelul de detaliu și cu materialele alese. Pentru spații mari și finisaje premium, un proiect tehnic complet este esențial." },
      { q: "Aveți designeri pentru zona Băneasa?", a: "Da, designerii verificați din București acoperă și Băneasa. Postează o cerere pentru oferte de la specialiști cu portofolii reale." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/stil/classic", label: "Design interior stil clasic" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
    ],
  },

  "otopeni": {
    name: "Otopeni (Ilfov)",
    intro:
      "Otopeni, oraș aflat imediat la nord de București și cunoscut pentru aeroportul internațional, are o piață rezidențială premium în creștere, cu case și ansambluri noi. Designul interior aici acoperă locuințe moderne, adesea pentru familii și profesioniști. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Otopeni",
        body: ["Fondul locativ este dominat de locuințe noi și case individuale."],
        bullets: [
          "Case individuale și duplexuri noi",
          "Apartamente în ansambluri rezidențiale moderne",
          "Amenajări pentru familii și profesioniști",
        ],
      },
      {
        h2: "Nevoi specifice zonei Otopeni",
        body: ["Locuințele noi cer personalizarea finisajelor și organizarea funcțională."],
        bullets: [
          "Organizarea zonelor de zi și noapte în case",
          "Personalizarea finisajelor la apartamentele noi",
          "Confort acustic, dat fiind traficul aerian din zonă",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Otopeni?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Aveți designeri pentru Otopeni?", a: "Da, designerii verificați din București acoperă și Otopeni. Postează o cerere pentru oferte reale." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "corbeanca": {
    name: "Corbeanca (Ilfov)",
    intro:
      "Corbeanca este o comună premium din Ilfov, la nord de București, apreciată pentru densitatea mică, vilele spantioase și mediul verde. Designul interior aici lucrează în principal cu case de familie și proprietăți generoase. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Corbeanca",
        body: ["Zona este dominată de case și vile individuale, cu suprafețe mari."],
        bullets: [
          "Vile și case individuale cu curte",
          "Spații generoase de zi și zone de relaxare",
          "Cerințe ridicate de confort și finisaje",
        ],
      },
      {
        h2: "Nevoi specifice zonei Corbeanca",
        body: ["Locuințele mari din mediu verde aduc cerințe aparte."],
        bullets: [
          "Legătura dintre interior și grădină/curte",
          "Materiale naturale și confort termic",
          "Organizarea logică a caselor pe niveluri",
        ],
      },
    ],
    faq: [
      { q: "Ce presupune designul unei vile în Corbeanca?", a: "Un proiect pentru o vilă include organizarea pe niveluri, zonele de zi și noapte, relația cu curtea și un plan de finisaje. Prețul se calculează pe metru pătrat." },
      { q: "Aveți designeri pentru Corbeanca?", a: "Da, designerii verificați din București acoperă și Corbeanca. Postează o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/stil/rustic", label: "Design interior stil rustic" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
    ],
  },

  "buftea": {
    name: "Buftea (Ilfov)",
    intro:
      "Buftea este un oraș din Ilfov, la nord-vest de București, cu un fond locativ variat, de la case la apartamente, și o zonă cunoscută pentru studiourile de film. Piața este mai accesibilă decât în zonele premium din nord. Designul interior acoperă atât apartamente, cât și case. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Buftea",
        body: ["Zona are un mix de locuințe, de la apartamente la case de familie."],
        bullets: [
          "Apartamente în blocuri și ansambluri",
          "Case individuale de familie",
          "Amenajări practice, cu buget echilibrat",
        ],
      },
      {
        h2: "Nevoi specifice zonei Buftea",
        body: ["Diversitatea locuințelor cere abordări adaptate."],
        bullets: [
          "Optimizarea apartamentelor și organizarea caselor",
          "Soluții practice de depozitare",
          "Echilibru între cost, funcționalitate și estetică",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Buftea?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Aveți designeri pentru Buftea?", a: "Da, designerii verificați din zona București-Ilfov acoperă și Buftea. Postează o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "balotesti": {
    name: "Balotești (Ilfov)",
    intro:
      "Balotești este o comună din Ilfov, situată pe DN1 la nord de București, cu o dezvoltare rezidențială în creștere și proximitate față de aeroport. Designul interior aici acoperă case și ansambluri noi, pentru familii care caută liniște lângă oraș. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Balotești",
        body: ["Zona combină ansambluri noi cu case individuale."],
        bullets: [
          "Case și duplexuri în ansambluri rezidențiale",
          "Apartamente noi de personalizat",
          "Amenajări pentru familii care fac naveta spre București",
        ],
      },
      {
        h2: "Nevoi specifice zonei Balotești",
        body: ["Locuințele noi și poziția pe DN1 modelează cerințele."],
        bullets: [
          "Organizarea funcțională a caselor pe niveluri",
          "Personalizarea finisajelor la locuințele noi",
          "Confort și izolație pentru locuit permanent",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Balotești?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și complexitate." },
      { q: "Aveți designeri pentru Balotești?", a: "Da, designerii verificați din zona București-Ilfov acoperă și Balotești. Postează o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/casa", label: "Design interior casă" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
    ],
  },

  "militari": {
    name: "Militari (București)",
    intro:
      "Militari este unul dintre cele mai populate cartiere din vestul Bucureștiului (sectorul 6), cu blocuri dense din perioada comunistă și, la limita cu Ilfov, ansambluri noi precum Militari Residence. Aici designul interior înseamnă în principal optimizarea apartamentelor compacte și modernizarea locuințelor din blocuri. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Militari",
        body: ["Fondul locativ combină blocuri consacrate cu ansambluri noi la marginea orașului."],
        bullets: [
          "Apartamente în blocuri (Gorjului, Lujerului, Veteranilor, Apusului) de optimizat",
          "Apartamente noi în ansamblurile de la limita cu Ilfov",
          "Garsoniere și apartamente de 2 camere pentru navetiști",
          "Necesar mare de depozitare la suprafețe mici",
        ],
      },
      {
        h2: "Nevoi specifice cartierului Militari",
        body: ["Densitatea și tipul apartamentelor modelează prioritățile."],
        bullets: [
          "Reabilitarea instalațiilor în blocurile mai vechi înainte de finisaje",
          "Optimizarea apartamentelor compacte din ansamblurile noi",
          "Izolație fonică, dat fiind traficul intens din zonă",
        ],
      },
    ],
    faq: [
      { q: "Merită designul interior pentru un apartament din Militari?", a: "Da, mai ales pentru apartamentele compacte. Un designer optimizează depozitarea, circulația și lumina, evitând cumpărături greșite de mobilier." },
      { q: "Aveți designeri în zona Militari?", a: "Designerii verificați din București acoperă și Militari. Postează o cerere pentru oferte reale." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/apartament-mic", label: "Design apartament mic" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
    ],
  },

  "titan": {
    name: "Titan (București)",
    intro:
      "Titan este unul dintre cele mai mari și mai verzi cartiere din estul Bucureștiului (sectorul 3), cu blocuri din anii 60-80 și Parcul Titan (IOR) în centru. Fondul locativ matur și spațiile verzi îl fac popular pentru familii. Aici designul interior se concentrează pe modernizarea apartamentelor din blocuri. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Titan",
        body: ["Cartierul are un fond locativ solid, cu apartamente care beneficiază de modernizare."],
        bullets: [
          "Apartamente în blocuri anii 60-80, solide dar de actualizat",
          "Apartamente de 2-3 camere de reorganizat funcțional",
          "Amenajări pentru familii, aproape de parc și zone verzi",
          "Modernizări de băi și bucătării",
        ],
      },
      {
        h2: "Nevoi specifice cartierului Titan",
        body: ["Fondul locativ matur cere atenție la instalații și finisaje."],
        bullets: [
          "Actualizarea instalațiilor electrice și sanitare înainte de finisaje",
          "Optimizarea depozitării și a zonei de zi",
          "Confort termic și fonic în apartamentele vechi",
        ],
      },
    ],
    faq: [
      { q: "Cât costă modernizarea unui apartament în Titan?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat, în funcție de suprafață și intervenții." },
      { q: "Aveți designeri în Titan?", a: "Da, designerii verificați din București acoperă și cartierul Titan. Postează o cerere pentru oferte." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei tale" },
    ],
  },

  "pipera": {
    name: "Pipera (București)",
    intro:
      "Pipera este principalul hub de business din nordul Bucureștiului și una dintre cele mai active zone rezidențiale noi, cu ansambluri moderne alese mai ales de tineri profesioniști din corporate și IT. Aici designul interior înseamnă personalizarea apartamentelor noi, adesea compacte, cu accent pe funcționalitate. Pe PropManage lucrezi cu designeri verificați, cu proiect legat de execuție prin escrow.",
    sections: [
      {
        h2: "Ce amenajăm în Pipera",
        body: ["Fondul locativ e dominat de apartamente noi din ansambluri rezidențiale."],
        bullets: [
          "Apartamente noi de 1-2-3 camere în ansambluri moderne",
          "Open-space living-bucătărie de organizat funcțional",
          "Studiouri și apartamente pentru tineri profesioniști",
          "Personalizarea finisajelor la predarea de la dezvoltator",
        ],
      },
      {
        h2: "Nevoi specifice zonei Pipera",
        body: ["Profilul tânăr și corporate al zonei aduce cerințe recurente."],
        bullets: [
          "Birou de acasă integrat pentru cei care lucrează remote sau hibrid",
          "Depozitare inteligentă la suprafețe compacte",
          "Izolație fonică, dat fiind densitatea și traficul din zonă",
        ],
      },
    ],
    faq: [
      { q: "Cât costă designul interior în Pipera?", a: "Un concept pornește de la câteva sute de lei pe cameră; proiectul tehnic complet se calculează pe metru pătrat. Personalizarea finisajelor la un apartament nou beneficiază mult de un proiect din faza de predare." },
      { q: "Aveți designeri în Pipera?", a: "Da, designerii verificați din București acoperă și zona Pipera. Postează o cerere pentru oferte reale." },
    ],
    related: [
      { to: "/design-interior/bucuresti", label: "Design interior București" },
      { to: "/design-interior/apartament", label: "Design interior apartament" },
      { to: "/design-interior/apartament-mic", label: "Design apartament mic" },
      { to: "/design-interior/3d", label: "Randări 3D / Digital Twin" },
    ],
  },
};

export const DI_LOCAL_INDEXABLE = Object.keys(DI_LOCAL_CONTENT);
export const getLocalContent = (slug) => DI_LOCAL_CONTENT[slug] || null;
