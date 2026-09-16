// Acquisition SEO landing pages — owners, specialists (pillar + trades), designers.
// Public landings that explain the experience and send users to free signup.
// NO Client Beta dashboard exposure. Each page has unique, non-templated content.

const CTA_OWNER = { label: "Creează gratuit Casa mea", to: "/register" };
const CTA_SPECIALIST = { label: "Înregistrează-te gratuit ca specialist", to: "/devino-specialist" };
const CTA_DESIGNER = { label: "Devino designer de interior pe PropManage", to: "/devino-specialist" };

export const ACQUISITION_PAGES = {
  // ── A. PROPRIETARI ─────────────────────────────────────────────────────────
  "proprietari": {
    audience: "owner",
    path: "/pentru-proprietari",
    badge: "Pentru proprietari",
    h1: "Platforma pentru proprietari de locuințe",
    title: "PropManage pentru proprietari: Casa mea gratuit, documente și mentenanță",
    description: "Adu-ți locuința în PropManage: organizează documentele, urmărește Scorul Casei, creează un Digital Twin și primești oferte de la specialiști verificați. Cont gratuit.",
    intro: "PropManage îți transformă locuința într-un activ îngrijit și transparent. Îți ții documentele la un loc, urmărești starea casei, primești oferte de la specialiști verificați și pregătești locuința pentru vânzare — totul dintr-un cont gratuit.",
    cta: CTA_OWNER,
    sections: [
      {
        h2: "Ce poți face gratuit ca proprietar",
        body: ["Contul de proprietar îți dă controlul asupra locuinței, fără costuri de start."],
        bullets: [
          "Organizezi documentele locuinței într-un singur loc (acte, garanții, facturi)",
          "Urmărești Scorul Casei — o evaluare a stării reale a locuinței",
          "Creezi un Digital Twin al proprietății",
          "Ții istoricul lucrărilor în Cartea Casei",
          "Primești oferte de la specialiști verificați, cu plată protejată prin escrow",
        ],
      },
      {
        h2: "Pregătește-ți locuința pentru vânzare",
        body: ["O locuință cu documente ordonate, un scor bun și un istoric complet se vinde mai repede și mai încrezător. Programul Imobile Verificate transformă starea verificată a casei într-o dovadă pentru cumpărător, nu doar o promisiune."],
      },
      {
        h2: "Cum începi în 3 pași",
        body: [],
        bullets: [
          "1. Creezi gratuit contul și adaugi locuința",
          "2. Completezi datele și, opțional, comanzi un audit sau un Digital Twin",
          "3. Primești oferte de la specialiști și îți gestionezi casa dintr-un loc",
        ],
      },
    ],
    faq: [
      { q: "Costă ceva să îmi creez contul de proprietar?", a: "Nu. Contul și adăugarea locuinței sunt gratuite. Plătești doar serviciile pe care le comanzi (audit, lucrări), cu plată protejată prin escrow." },
      { q: "Ce este Scorul Casei?", a: "O evaluare a stării reale a locuinței — instalații, structură, izolație, documente. Îți arată ce merită rezolvat întâi și crește pe măsură ce faci lucrări." },
      { q: "Cum primesc oferte de la specialiști?", a: "Postezi o cerere, iar specialiștii verificați îți trimit oferte. Compari profiluri, portofolii și recenzii înainte de a alege, iar plata e protejată." },
    ],
    related: [
      { to: "/cartea-casei", label: "Cartea Casei: istoricul locuinței" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei" },
      { to: "/digital-twin", label: "Digital Twin pentru proprietate" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/ghiduri", label: "Ghiduri pentru proprietari" },
    ],
  },

  "cartea-casei": {
    audience: "owner",
    path: "/cartea-casei",
    badge: "Cartea Casei",
    h1: "Cartea Casei: istoricul digital al locuinței tale",
    title: "Cartea Casei: istoricul locuinței într-un singur loc | PropManage",
    description: "Cartea Casei păstrează documentele, lucrările, reviziile și garanțiile locuinței tale. Utilă la mentenanță, garanții și vânzare. Începe gratuit.",
    intro: "Cartea Casei este memoria locuinței tale: documente, lucrări, revizii, garanții și starea sistemelor, într-un singur loc. Când ai nevoie de o informație — la o reparație, o garanție sau o vânzare — o găsești imediat.",
    cta: CTA_OWNER,
    sections: [
      {
        h2: "Ce conține Cartea Casei",
        body: ["Un istoric structurat al locuinței, construit treptat, pe măsură ce apar documente și lucrări."],
        bullets: [
          "Documentele proprietății și actele importante",
          "Istoricul lucrărilor și al reviziilor, cu materiale și executanți",
          "Garanțiile și termenele lor",
          "Starea sistemelor și rezultatele auditurilor",
        ],
      },
      {
        h2: "De ce contează istoricul",
        body: ["La reparații, specialiștii văd ce s-a făcut. La garanții, găsești rapid facturile. La mentenanță, știi când a fost ultima revizie. La vânzare, un istoric complet crește încrederea și valoarea locuinței."],
      },
    ],
    faq: [
      { q: "Cum construiesc Cartea Casei?", a: "Adaugi treptat documentele și lucrările din contul gratuit de proprietar. Combinată cu Scorul Casei și cu un plan de mentenanță, devine o imagine completă a locuinței." },
      { q: "Mă ajută la vânzare?", a: "Da. Un istoric complet și un scor bun fac locuința mai atractivă, mai ales listată ca Imobil Verificat cu audit și Digital Twin." },
      { q: "Costă ceva?", a: "Contul de proprietar și Cartea Casei sunt gratuite. Plătești doar serviciile pe care le comanzi." },
    ],
    related: [
      { to: "/pentru-proprietari", label: "Platforma pentru proprietari" },
      { to: "/ghiduri/cartea-casei-istoric-locuinta", label: "Ghid: de ce contează istoricul" },
      { to: "/scorul-casei", label: "Verifică Scorul Casei" },
      { to: "/ghiduri/plan-mentenanta-locuinta", label: "Ghid: plan de mentenanță" },
    ],
  },

  // ── B. SPECIALIȘTI ─────────────────────────────────────────────────────────
  "specialisti": {
    audience: "specialist",
    path: "/pentru-specialisti",
    badge: "Pentru specialiști",
    h1: "Găsește clienți ca specialist pe PropManage",
    title: "Devino specialist PropManage: primești clienți, gratuit | Înregistrare",
    description: "Înregistrează-te gratuit ca specialist și primești cereri reale de la proprietari. Profil verificat, plată protejată prin escrow, fără costuri de start.",
    intro: "PropManage îți aduce clienți fără să îi cauți la rece. Proprietarii postează cereri, iar tu primești lead-uri relevante pentru meseria ta. Profilul verificat îți crește încrederea, iar plata e protejată prin escrow.",
    cta: CTA_SPECIALIST,
    sections: [
      {
        h2: "De ce să te înregistrezi pe PropManage",
        body: ["O platformă care leagă proprietarii de specialiști verificați, cu reguli clare."],
        bullets: [
          "Primești cereri reale de la proprietari din zona ta",
          "Îți construiești un profil verificat, cu portofoliu și recenzii",
          "Plată protejată prin escrow — muncești cu siguranța că ești plătit",
          "Fără costuri de start pentru înregistrare",
        ],
      },
      {
        h2: "Cum primești clienți",
        body: ["Proprietarul descrie lucrarea, tu trimiți o ofertă, iar dacă e acceptată, execuția și plata sunt gestionate transparent. Recenziile reale te ajută să câștigi următoarele proiecte."],
      },
      {
        h2: "Verificare și încredere",
        body: ["Profilul verificat te diferențiază. Proprietarii aleg cu mai multă încredere un specialist verificat, cu portofoliu și istoric de recenzii, decât un contact anonim."],
      },
    ],
    faq: [
      { q: "Cât costă să mă înregistrez ca specialist?", a: "Înregistrarea este gratuită. Îți creezi profilul și începi să primești cereri fără costuri de start." },
      { q: "Ce meserii sunt acceptate?", a: "O gamă largă — de la electricieni, instalatori și constructori, la auditori energetici și specialiști HVAC. Vezi paginile dedicate fiecărei meserii." },
      { q: "Cum sunt plătit?", a: "Prin escrow: banii sunt protejați, iar tu muncești cu siguranța plății la finalizarea etapelor convenite." },
    ],
    related: [
      { to: "/pentru-specialisti/electrician", label: "Electrician pe PropManage" },
      { to: "/pentru-specialisti/instalator", label: "Instalator pe PropManage" },
      { to: "/pentru-specialisti/constructor", label: "Constructor pe PropManage" },
      { to: "/pentru-specialisti/auditor-energetic", label: "Auditor energetic pe PropManage" },
      { to: "/pentru-specialisti/hvac", label: "Specialist HVAC pe PropManage" },
    ],
  },

  "specialist-electrician": {
    audience: "specialist",
    path: "/pentru-specialisti/electrician",
    badge: "Electrician",
    h1: "Electrician pe PropManage: primești clienți în zona ta",
    title: "Electrician PropManage: găsește clienți, înregistrare gratuită",
    description: "Ești electrician? Înregistrează-te gratuit pe PropManage și primești cereri pentru tablouri, circuite, prize, avarii și verificări. Plată protejată prin escrow.",
    intro: "Ca electrician pe PropManage primești cereri concrete de la proprietari: de la instalații complete în renovări, la avarii și verificări de siguranță. Fără să cauți clienți la rece — ei vin la tine.",
    cta: CTA_SPECIALIST,
    sections: [
      {
        h2: "Ce lucrări primești ca electrician",
        body: ["Cererile acoperă întreg spectrul lucrărilor electrice rezidențiale."],
        bullets: [
          "Instalații electrice complete în renovări și apartamente noi",
          "Înlocuirea tabloului electric și a circuitelor vechi",
          "Prize, întrerupătoare, corpuri de iluminat",
          "Avarii și intervenții urgente",
          "Verificări de siguranță și punere la pământ",
        ],
      },
      {
        h2: "De ce cererea e constantă",
        body: ["Multe apartamente din blocuri vechi au instalații depășite care necesită înlocuire înainte de finisaje. Renovările generează sistematic lucrări electrice, iar proprietarii caută un electrician de încredere, verificat."],
      },
    ],
    faq: [
      { q: "Ce tip de clienți primesc?", a: "Proprietari care renovează, care au avarii sau care vor verificări de siguranță — cereri concrete, nu simple curioase." },
      { q: "Trebuie să am autorizări?", a: "Pentru anumite lucrări electrice sunt necesare autorizări specifice. Profilul verificat îți crește credibilitatea în fața proprietarilor." },
      { q: "Costă înregistrarea?", a: "Nu, înregistrarea ca specialist este gratuită." },
    ],
    related: [
      { to: "/pentru-specialisti", label: "Toate meseriile pe PropManage" },
      { to: "/pentru-specialisti/instalator", label: "Instalator pe PropManage" },
      { to: "/pentru-specialisti/hvac", label: "Specialist HVAC pe PropManage" },
      { to: "/marketplace", label: "Marketplace specialiști" },
    ],
  },

  "specialist-instalator": {
    audience: "specialist",
    path: "/pentru-specialisti/instalator",
    badge: "Instalator",
    h1: "Instalator pe PropManage: cereri pentru instalații sanitare și termice",
    title: "Instalator PropManage: găsește clienți, înregistrare gratuită",
    description: "Ești instalator sanitar sau termic? Înregistrează-te gratuit și primești cereri pentru băi, centrale, scurgeri și avarii. Plată protejată prin escrow.",
    intro: "Ca instalator pe PropManage primești cereri pentru lucrări sanitare și termice — de la amenajarea băilor și montajul centralelor, la avarii și scurgeri. Proprietarii verificați vin la tine cu proiecte concrete.",
    cta: CTA_SPECIALIST,
    sections: [
      {
        h2: "Ce lucrări primești ca instalator",
        body: ["Cererile acoperă instalațiile sanitare și termice ale locuinței."],
        bullets: [
          "Instalații sanitare complete în renovări de băi și bucătării",
          "Montaj și service centrale termice",
          "Repararea scurgerilor și a țevilor corodate",
          "Obiecte sanitare, baterii, sisteme de filtrare",
          "Avarii și intervenții urgente",
        ],
      },
      {
        h2: "De ce cererea e mare",
        body: ["Renovarea băilor și înlocuirea instalațiilor vechi sunt printre cele mai frecvente lucrări în apartamentele din blocuri. Proprietarii caută un instalator verificat, ca să evite refacerile costisitoare."],
      },
    ],
    faq: [
      { q: "Primesc și lucrări de urgență?", a: "Da. Avariile (scurgeri, defecțiuni la centrală) sunt cereri frecvente, pe lângă lucrările planificate din renovări." },
      { q: "Cum îmi construiesc reputația?", a: "Prin recenzii reale de la proprietari. Un istoric bun te ajută să câștigi mai multe proiecte." },
      { q: "Costă înregistrarea?", a: "Nu, înregistrarea ca specialist este gratuită." },
    ],
    related: [
      { to: "/pentru-specialisti", label: "Toate meseriile pe PropManage" },
      { to: "/pentru-specialisti/electrician", label: "Electrician pe PropManage" },
      { to: "/pentru-specialisti/hvac", label: "Specialist HVAC pe PropManage" },
      { to: "/marketplace", label: "Marketplace specialiști" },
    ],
  },

  "specialist-constructor": {
    audience: "specialist",
    path: "/pentru-specialisti/constructor",
    badge: "Constructor",
    h1: "Constructor pe PropManage: cereri pentru renovări și amenajări",
    title: "Constructor PropManage: găsește clienți pentru renovări | Gratuit",
    description: "Firmă de construcții sau constructor? Înregistrează-te gratuit și primești cereri pentru renovări la cheie, finisaje și amenajări. Plată protejată prin escrow.",
    intro: "Ca constructor pe PropManage primești cereri pentru renovări la cheie, finisaje și amenajări complete. Proprietarii au adesea și un proiect de design gata, iar plata e protejată prin escrow pe etape.",
    cta: CTA_SPECIALIST,
    sections: [
      {
        h2: "Ce lucrări primești ca constructor",
        body: ["Cererile merg de la lucrări punctuale la renovări complete."],
        bullets: [
          "Renovări complete de apartamente și case",
          "Finisaje: gresie, faianță, parchet, zugrăveli, glet",
          "Recompartimentări (pereți nestructurali)",
          "Amenajări la cheie, coordonate cu proiectul de design",
          "Lucrări de reabilitare la imobile vechi",
        ],
      },
      {
        h2: "Avantajul lucrului cu un proiect de design",
        body: ["Multe cereri vin cu un proiect de design deja făcut, ceea ce înseamnă specificații clare, mai puține surprize și o execuție mai predictibilă. Plata pe etape prin escrow reduce riscul pentru ambele părți."],
      },
    ],
    faq: [
      { q: "Primesc renovări complete sau doar lucrări mici?", a: "Ambele. De la finisaje punctuale la renovări la cheie. Poți alege proiectele care ți se potrivesc." },
      { q: "Cum funcționează plata pe etape?", a: "Prin escrow: banii sunt eliberați pe măsură ce etapele convenite sunt finalizate, protejând atât proprietarul, cât și pe tine." },
      { q: "Costă înregistrarea?", a: "Nu, înregistrarea ca specialist este gratuită." },
    ],
    related: [
      { to: "/pentru-specialisti", label: "Toate meseriile pe PropManage" },
      { to: "/design-interior/renovare", label: "Design pentru renovare" },
      { to: "/pentru-specialisti/instalator", label: "Instalator pe PropManage" },
      { to: "/marketplace", label: "Marketplace specialiști" },
    ],
  },

  "specialist-auditor-energetic": {
    audience: "specialist",
    path: "/pentru-specialisti/auditor-energetic",
    badge: "Auditor energetic",
    h1: "Auditor energetic pe PropManage: cereri pentru certificate și audituri",
    title: "Auditor energetic PropManage: găsește clienți | Înregistrare gratuită",
    description: "Ești auditor energetic? Înregistrează-te gratuit și primești cereri pentru certificate energetice, audituri și consultanță de eficiență. Escrow inclus.",
    intro: "Ca auditor energetic pe PropManage primești cereri pentru certificate de performanță energetică, audituri și consultanță de eficiență. Munca ta se leagă direct de Scorul Casei și de programul Imobile Verificate.",
    cta: CTA_SPECIALIST,
    sections: [
      {
        h2: "Ce lucrări primești ca auditor energetic",
        body: ["Cererile acoperă evaluarea și îmbunătățirea eficienței energetice a locuințelor."],
        bullets: [
          "Certificate de performanță energetică pentru vânzare sau închiriere",
          "Audituri energetice și recomandări de eficientizare",
          "Consultanță pentru izolație și reducerea facturilor",
          "Evaluări care alimentează Scorul Casei",
        ],
      },
      {
        h2: "Legătura cu Scorul Casei și Imobile Verificate",
        body: ["Evaluarea energetică e o componentă importantă a stării unei locuințe. Pe PropManage, munca ta contribuie la Scorul Casei și susține transparența în programul Imobile Verificate — o valoare vizibilă pentru proprietari."],
      },
    ],
    faq: [
      { q: "Ce cereri primesc cel mai des?", a: "Certificate energetice cerute la vânzare sau închiriere și audituri pentru proprietari care vor să reducă facturile sau să crească valoarea locuinței." },
      { q: "Cum ajută profilul verificat?", a: "Proprietarii au încredere mai mare într-un auditor verificat, cu recenzii reale. Asta se traduce în mai multe cereri." },
      { q: "Costă înregistrarea?", a: "Nu, înregistrarea ca specialist este gratuită." },
    ],
    related: [
      { to: "/pentru-specialisti", label: "Toate meseriile pe PropManage" },
      { to: "/scorul-casei", label: "Scorul Casei" },
      { to: "/imobile-verificate", label: "Imobile Verificate" },
      { to: "/pentru-specialisti/hvac", label: "Specialist HVAC pe PropManage" },
    ],
  },

  "specialist-hvac": {
    audience: "specialist",
    path: "/pentru-specialisti/hvac",
    badge: "HVAC",
    h1: "Specialist HVAC pe PropManage: climatizare, ventilație, pompe de căldură",
    title: "Specialist HVAC PropManage: găsește clienți | Înregistrare gratuită",
    description: "Ești specialist HVAC? Înregistrează-te gratuit și primești cereri pentru montaj și service de climatizare, ventilație și pompe de căldură. Escrow inclus.",
    intro: "Ca specialist HVAC pe PropManage primești cereri pentru montaj și service de aer condiționat, ventilație și pompe de căldură. Cererea crește odată cu interesul pentru confort și eficiență energetică.",
    cta: CTA_SPECIALIST,
    sections: [
      {
        h2: "Ce lucrări primești ca specialist HVAC",
        body: ["Cererile acoperă sistemele de climatizare și ventilație rezidențiale."],
        bullets: [
          "Montaj și service aer condiționat",
          "Sisteme de ventilație și recuperare de căldură",
          "Pompe de căldură pentru încălzire eficientă",
          "Întreținere periodică și igienizare",
          "Consultanță pentru soluții eficiente energetic",
        ],
      },
      {
        h2: "De ce cererea crește",
        body: ["Verile tot mai calde și accentul pe eficiență energetică au făcut din climatizare și pompele de căldură investiții tot mai frecvente. Proprietarii caută un specialist HVAC verificat pentru montaj corect și service periodic."],
      },
    ],
    faq: [
      { q: "Primesc și contracte de întreținere?", a: "Da. Pe lângă montaj, service-ul periodic și igienizarea sunt cereri recurente, cu potențial de clienți pe termen lung." },
      { q: "Cum mă diferențiez?", a: "Prin profilul verificat și recenziile reale. Proprietarii aleg cu mai multă încredere un specialist verificat." },
      { q: "Costă înregistrarea?", a: "Nu, înregistrarea ca specialist este gratuită." },
    ],
    related: [
      { to: "/pentru-specialisti", label: "Toate meseriile pe PropManage" },
      { to: "/pentru-specialisti/auditor-energetic", label: "Auditor energetic pe PropManage" },
      { to: "/pentru-specialisti/instalator", label: "Instalator pe PropManage" },
      { to: "/marketplace", label: "Marketplace specialiști" },
    ],
  },

  // ── C. DESIGNERI (recrutare) ─────────────────────────────────────────────────
  "designeri": {
    audience: "designer",
    path: "/pentru-designeri",
    badge: "Pentru designeri",
    h1: "Devino designer de interior pe PropManage",
    title: "Designer de interior pe PropManage: primești cereri de la proprietari",
    description: "Ești designer de interior? Înregistrează-te gratuit și primești cereri reale de la proprietari. Profil verificat, portofoliu, proiect legat de execuție și escrow.",
    intro: "Pe PropManage nu îți cauți clienții la rece — proprietarii care vor design interior vin la tine cu cereri concrete. Îți construiești un profil verificat cu portofoliu, iar proiectul tău se leagă de execuție, cu plată protejată prin escrow.",
    cta: CTA_DESIGNER,
    sections: [
      {
        h2: "De ce PropManage pentru designeri",
        body: ["O platformă gândită să lege designul de execuția reală, nu doar de imagini frumoase."],
        bullets: [
          "Primești cereri de la proprietari pentru apartamente, case și renovări",
          "Profil verificat cu portofoliu și recenzii reale",
          "Proiectul tău se leagă de audit, Digital Twin și implementare",
          "Plată protejată prin escrow",
          "Vizibilitate în paginile comerciale de design interior",
        ],
      },
      {
        h2: "Ce cereri primești",
        body: ["Concepte de amenajare, proiecte tehnice complete, randări 3D și proiecte de renovare — de la apartamente compacte la case și spații comerciale. Cererile vin din întreaga rețea, inclusiv din paginile locale de design interior."],
      },
      {
        h2: "Cum începi",
        body: ["Te înregistrezi gratuit, îți completezi profilul și portofoliul, treci prin verificare și începi să primești cereri relevante. Recenziile reale te ajută să câștigi următoarele proiecte."],
      },
    ],
    faq: [
      { q: "Prin ce se deosebește de a-mi căuta singur clienții?", a: "Proprietarii vin la tine cu cereri deja formulate. Nu faci prospectare la rece — te concentrezi pe proiecte, iar platforma gestionează transparent oferta, contractul și plata." },
      { q: "Cum mă înregistrez ca designer?", a: "Prin fluxul de înregistrare ca specialist, alegând designul interior. Este gratuit, iar profilul verificat îți crește credibilitatea." },
      { q: "Cum sunt plătit?", a: "Prin escrow: plata e protejată și eliberată pe etapele convenite ale proiectului." },
    ],
    related: [
      { to: "/design-interior", label: "Design interior (paginile comerciale)" },
      { to: "/pentru-specialisti", label: "Alte meserii pe PropManage" },
      { to: "/marketplace", label: "Marketplace specialiști" },
      { to: "/design-interior/pret", label: "Cât costă designul interior" },
    ],
  },
};

export const getAcqByPath = (pathname) =>
  Object.values(ACQUISITION_PAGES).find((p) => p.path === pathname) || null;

export const getAcqById = (id) => ACQUISITION_PAGES[id] || null;

// All acquisition landing paths that should be INDEX + in sitemap.
export const ACQUISITION_PATHS = Object.values(ACQUISITION_PAGES).map((p) => p.path);
