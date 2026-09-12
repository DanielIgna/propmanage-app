// Problem cluster content for /probleme-casa/:slug (SEO — problem/solution intent).
// Mirrors the structure of data/ghiduri.js so the page can reuse the same block renderer.
// Each problem links down to relevant services (marketplace), prices and guides.
//
// block types: string | { type:"list", items:[] } | { type:"callout", title, body }

export const PROBLEME = [
  {
    slug: "infiltratii-acoperis",
    tag: "Acoperiș & izolații",
    title: "Infiltrații la acoperiș: cauze, soluții și cost 2026 | PropManage",
    h1: "Infiltrații la acoperiș: de ce apar și cum le rezolvi definitiv",
    description:
      "Ai pete de umezeală în tavan sau apă care picură din pod? Vezi cauzele reale ale infiltrațiilor la acoperiș, soluțiile corecte, costul orientativ și când trebuie să chemi un specialist verificat.",
    readMins: 6,
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    relatedCategories: ["acoperisuri", "instalator"],
    relatedGuides: ["audit-tehnic-apartament-pret", "ce-este-digital-twin-locuinta"],
    relatedProblems: ["probleme-acoperis", "umezeala-pereti", "mucegai-igrasie"],
    sections: [
      {
        heading: "Simptome — cum recunoști o infiltrație",
        body: [
          "O infiltrație la acoperiș rareori apare exact deasupra sursei. Apa migrează pe grinzi, folie sau tencuială și iese la câțiva metri distanță, ceea ce face diagnosticul dificil fără o inspecție corectă.",
          { type: "list", items: [
            "**Pete maronii sau gălbui** pe tavan sau pe partea de sus a pereților, care se măresc după ploaie.",
            "**Tencuială umflată, coșcovită sau care cade** în zona podului sau a ultimului etaj.",
            "**Miros de umezeală** persistent în pod sau în camerele de sub terasă.",
            "**Apă care picură** vizibil în timpul sau imediat după ploi puternice ori la topirea zăpezii.",
          ] },
        ],
      },
      {
        heading: "Cauze frecvente",
        body: [
          "Infiltrațiile au aproape întotdeauna o cauză mecanică precisă. Cele mai des întâlnite sunt:",
          { type: "list", items: [
            "**Țigle sau tablă deteriorate / deplasate** de vânt, grindină sau uzură.",
            "**Șorțuri și racorduri neetanșe** în jurul coșului, lucarnelor sau ventilațiilor.",
            "**Jgheaburi și burlane înfundate** care fac apa să se întoarcă sub învelitoare.",
            "**Membrana hidroizolantă îmbătrânită** la terasele necirculabile (bitum crăpat, rosturi desfăcute).",
            "**Condens în pod** din cauza unei ventilații insuficiente — se confundă des cu o infiltrație.",
          ] },
          { type: "callout", title: "Atenție", body: "Nu vopsi peste pată înainte de a opri sursa. Vopseaua ascunde problema câteva luni, dar umezeala continuă să degradeze structura și favorizează mucegaiul." },
        ],
      },
      {
        heading: "Soluții — de la reparație punctuală la refacere",
        body: [
          "Soluția corectă depinde de amploarea problemei și de vechimea învelitorii:",
          { type: "list", items: [
            "**Reparație punctuală** — înlocuirea țiglelor sparte și reetanșarea racordurilor, când învelitoarea este în rest sănătoasă.",
            "**Refacerea șorțurilor și a hidroizolației locale** la coș, lucarne și dolii.",
            "**Curățarea și corectarea pantei jgheaburilor**, plus montarea de opritoare de zăpadă unde e cazul.",
            "**Refacerea completă a învelitorii** când peste 20-30% este degradată sau structura lemnoasă a fost afectată.",
          ] },
          "Indiferent de soluție, cere întotdeauna documentarea lucrării (foto înainte/după, materiale folosite). În Cartea Casei din PropManage aceste dovezi rămân atașate proprietății pentru viitor.",
        ],
      },
      {
        heading: "Cost orientativ și când chemi specialistul",
        body: [
          "Costul variază mult în funcție de acces, tip de învelitoare și amploare. O reparație punctuală este semnificativ mai ieftină decât o refacere, motiv pentru care intervenția rapidă economisește bani.",
          { type: "list", items: [
            "**Chemi specialistul imediat** dacă apa pică activ, dacă pata crește vizibil sau dacă apar semne de mucegai.",
            "**Ceri o inspecție tehnică** înainte de a cumpăra o casă cu acoperiș vechi — o infiltrație ascunsă poate însemna costuri mari.",
          ] },
          "Pe PropManage poți cere oferte de la specialiști verificați în acoperișuri, cu plată protejată prin escrow — banii se eliberează doar după ce confirmi lucrarea.",
        ],
      },
    ],
    faq: [
      { q: "De ce apare pata de umezeală în alt loc decât unde plouă?", a: "Apa se deplasează pe grinzi, folii și tencuială înainte să iasă la vedere. De aceea diagnosticul corect cere o inspecție a întregii zone, nu doar a punctului unde vezi pata." },
      { q: "Pot repara singur o infiltrație la acoperiș?", a: "Poți curăța jgheaburile, dar identificarea sursei și reetanșarea racordurilor cer experiență și lucru în siguranță la înălțime. O reparație greșită maschează problema temporar." },
      { q: "Cât de repede trebuie să intervin?", a: "Cât mai repede. Umezeala degradează structura lemnoasă și favorizează mucegaiul; o reparație punctuală făcută la timp costă mult mai puțin decât o refacere ulterioară." },
    ],
  },
  {
    slug: "mucegai-igrasie",
    tag: "Umezeală & sănătatea casei",
    title: "Mucegai și igrasie: cauze, soluții și prevenție | PropManage",
    h1: "Mucegai și igrasie: cum le elimini definitiv, nu doar la suprafață",
    description:
      "Pete negre în colțuri, miros de mucegai, tencuială care se desprinde? Vezi cauzele reale ale mucegaiului și igrasiei, soluțiile care le elimină definitiv, costul orientativ și când chemi un specialist.",
    readMins: 6,
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    relatedCategories: ["zugrav", "termoizolatii"],
    relatedGuides: ["cum-alegi-zugrav-bun", "audit-tehnic-apartament-pret"],
    relatedProblems: ["umezeala-pereti", "infiltratii-acoperis", "fisuri-pereti"],
    sections: [
      {
        heading: "Simptome",
        body: [
          "Mucegaiul și igrasia sunt semne că un perete stă umed constant. Tratată doar cosmetic, problema revine în câteva luni.",
          { type: "list", items: [
            "**Pete negre, verzi sau gri** în colțuri, în spatele mobilei sau lângă ferestre.",
            "**Miros persistent de umezeală**, mai puternic în camerele nordice sau slab ventilate.",
            "**Tencuială și vopsea care se desprind**, tapet dezlipit la bază.",
            "**Igrasie** — o bandă umedă la partea de jos a peretelui, care urcă din fundație.",
          ] },
        ],
      },
      {
        heading: "Cauze frecvente",
        body: [
          { type: "list", items: [
            "**Punți termice** — colțuri și buiandrugi reci unde condensează vaporii din aer.",
            "**Ventilație insuficientă** — geamuri termopan fără aerisire, băi și bucătării fără evacuare.",
            "**Infiltrații** din acoperiș, terasă sau instalații sanitare defecte.",
            "**Igrasie ascendentă** — lipsa unei hidroizolații orizontale la baza pereților.",
            "**Termoizolație lipsă sau incorectă** pe fațadă.",
          ] },
          { type: "callout", title: "Important", body: "Mucegaiul nu este doar o problemă estetică — sporii afectează calitatea aerului și sănătatea. Elimină cauza umezelii, nu doar pata." },
        ],
      },
      {
        heading: "Soluții durabile",
        body: [
          { type: "list", items: [
            "**Corectarea sursei de umezeală** — reparația infiltrației, a instalației sau a hidroizolației (pasul obligatoriu).",
            "**Îmbunătățirea ventilației** — grile de aerisire, ventilație mecanică în baie/bucătărie.",
            "**Tratament antifungic** al zonelor afectate, apoi tencuială și vopsea permeabilă la vapori.",
            "**Termoizolarea punților termice** pentru a elimina condensul.",
            "**Hidroizolație împotriva igrasiei** la baza pereților, unde este cazul.",
          ] },
          "Ordinea contează: mai întâi cauza, apoi finisajul. Altfel refaci zugrăveala degeaba.",
        ],
      },
      {
        heading: "Cost orientativ și când chemi specialistul",
        body: [
          "Un tratament cosmetic e ieftin, dar temporar. Rezolvarea cauzei (termoizolație, ventilație, hidroizolație) costă mai mult, însă oprește problema definitiv.",
          "Chemi un specialist când mucegaiul revine după curățare, când suprafața afectată este mare sau când apare igrasia. Pe PropManage găsești zugravi și firme de termoizolații verificate, cu recenzii reale și plată escrow.",
        ],
      },
    ],
    faq: [
      { q: "De ce revine mucegaiul după ce l-am curățat?", a: "Pentru că a fost tratată doar pata, nu cauza. Atâta timp cât peretele rămâne umed (punte termică, ventilație slabă sau infiltrație), sporii se dezvoltă din nou." },
      { q: "Diferența dintre mucegai și igrasie?", a: "Mucegaiul apare din condensul de suprafață (colțuri reci, ventilație slabă). Igrasia este umezeala care urcă din fundație prin capilaritate, în lipsa unei hidroizolații orizontale." },
      { q: "Este periculos mucegaiul din casă?", a: "Da. Sporii afectează calitatea aerului și pot agrava afecțiuni respiratorii. De aceea eliminarea cauzei este importantă, nu doar acoperirea petei." },
    ],
  },
  {
    slug: "fisuri-pereti",
    tag: "Structură & pereți",
    title: "Fisuri în pereți: sunt periculoase? Cauze și soluții | PropManage",
    h1: "Fisuri în pereți: care sunt normale și care cer un specialist",
    description:
      "Ai fisuri în pereți și nu știi dacă sunt periculoase? Vezi diferența dintre fisurile superficiale și cele structurale, cauzele lor, soluțiile corecte și când trebuie o expertiză tehnică.",
    readMins: 5,
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    relatedCategories: ["constructii", "zugrav"],
    relatedGuides: ["audit-tehnic-apartament-pret", "verificare-apartament-inainte-de-cumparare"],
    relatedProblems: ["umezeala-pereti", "infiltratii-acoperis"],
    sections: [
      {
        heading: "Simptome — fisuri superficiale vs. structurale",
        body: [
          "Nu toate fisurile sunt periculoase, dar unele semnalează probleme structurale serioase. Iată cum le deosebești:",
          { type: "list", items: [
            "**Fisuri fine, sub 1 mm**, în tencuială sau glet — de obicei superficiale (contracția materialelor).",
            "**Fisuri în „scară”** pe zidărie, la 45°, mai late la un capăt — pot indica tasarea fundației.",
            "**Fisuri orizontale** în pereți portanți sau la îmbinări planșeu-perete — semn de alarmă.",
            "**Fisuri care se lărgesc în timp** sau prin care intră aer/apă — necesită evaluare urgentă.",
          ] },
        ],
      },
      {
        heading: "Cauze frecvente",
        body: [
          { type: "list", items: [
            "**Contracția normală** a tencuielii și gletului la construcțiile noi.",
            "**Tasări diferențiate ale fundației** (teren, infiltrații în sol, lucrări vecine).",
            "**Dilatații termice** la fațade fără rosturi.",
            "**Vibrații și lucrări structurale** improvizate (spargeri în pereți portanți).",
            "**Umezeala** care slăbește aderența finisajelor.",
          ] },
          { type: "callout", title: "Semnal de alarmă", body: "Fisurile orizontale în pereți portanți, cele care se lărgesc rapid sau apar după o intervenție structurală trebuie evaluate de un inginer/expert înainte de orice reparație cosmetică." },
        ],
      },
      {
        heading: "Soluții",
        body: [
          { type: "list", items: [
            "**Fisuri superficiale** — chituire, plasă de armare pe zonă, glet și revopsire.",
            "**Fisuri pe rosturi/îmbinări** — bandă de armare elastică care preia micile mișcări.",
            "**Fisuri structurale** — mai întâi expertiză tehnică, apoi soluția de consolidare recomandată; abia la final finisajul.",
          ] },
          "Documentează evoluția fisurii (foto cu dată) — ajută specialistul să stabilească dacă este activă sau stabilizată.",
        ],
      },
      {
        heading: "Când chemi specialistul",
        body: [
          "Cheamă un specialist în construcții sau un expert tehnic dacă fisura este orizontală într-un perete portant, dacă se lărgește vizibil sau dacă apare după cutremur ori lucrări. Pentru fisurile cosmetice, un zugrav bun rezolvă rapid.",
          "Pe PropManage poți compara oferte de la specialiști verificați și poți păstra expertiza tehnică în Cartea Casei.",
        ],
      },
    ],
    faq: [
      { q: "Toate fisurile din pereți sunt periculoase?", a: "Nu. Fisurile fine din tencuială/glet sunt de obicei superficiale. Devin îngrijorătoare cele orizontale în pereți portanți, cele în „scară” pe zidărie și cele care se lărgesc în timp." },
      { q: "Cum știu dacă o fisură este activă?", a: "Marchează capetele și lățimea și fotografiază cu dată timp de câteva săptămâni. Dacă se extinde, este activă și necesită evaluare tehnică." },
      { q: "Pot doar să chituiesc și să vopsesc?", a: "Doar pentru fisuri superficiale. Dacă e structurală, finisajul va crăpa din nou; întâi se rezolvă cauza, apoi finisajul." },
    ],
  },
  {
    slug: "umezeala-pereti",
    tag: "Umezeală & sănătatea casei",
    title: "Umezeală în pereți și condens: cauze și soluții 2026 | PropManage",
    h1: "Umezeală în pereți: de la condens la igrasie, cum o rezolvi",
    description:
      "Pereți reci și umezi, condens pe geamuri, senzație de umezeală în casă? Vezi cauzele umezelii din pereți, soluțiile pe termen lung, rolul ventilației și termoizolației și când chemi un specialist.",
    readMins: 5,
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    relatedCategories: ["termoizolatii", "instalator"],
    relatedGuides: ["audit-tehnic-apartament-pret", "cum-verifici-instalator"],
    relatedProblems: ["mucegai-igrasie", "infiltratii-acoperis", "fisuri-pereti"],
    sections: [
      {
        heading: "Simptome",
        body: [
          { type: "list", items: [
            "**Condens pe geamuri** dimineața și pereți reci la atingere.",
            "**Senzație de umezeală** și aer greu, mai ales în camerele nordice.",
            "**Pete și mucegai** în colțuri și în spatele mobilei lipite de pereții exteriori.",
            "**Bandă umedă** la baza pereților (igrasie ascendentă).",
          ] },
        ],
      },
      {
        heading: "Cauze frecvente",
        body: [
          { type: "list", items: [
            "**Ventilație insuficientă** — termopane etanșe fără aerisire controlată.",
            "**Punți termice** și lipsa termoizolației pe fațadă.",
            "**Igrasie** din fundație în lipsa hidroizolației orizontale.",
            "**Infiltrații** din acoperiș, terasă sau instalații sanitare.",
            "**Surse interioare de vapori** — gătit, uscarea rufelor în casă, dușuri fără evacuare.",
          ] },
        ],
      },
      {
        heading: "Soluții pe termen lung",
        body: [
          { type: "list", items: [
            "**Ventilație corectă** — aerisire regulată sau ventilație mecanică cu recuperare de căldură.",
            "**Termoizolarea fațadei** și tratarea punților termice pentru a elimina condensul.",
            "**Hidroizolație** împotriva igrasiei ascendente, acolo unde e cazul.",
            "**Repararea infiltrațiilor și a instalațiilor** care aduc apă în pereți.",
            "**Finisaje permeabile la vapori** după rezolvarea cauzei.",
          ] },
          { type: "callout", title: "Sfat", body: "Un higrometru ieftin îți arată umiditatea din cameră. Peste 60% constant înseamnă risc de condens și mucegai — semn că ai nevoie de ventilație sau termoizolație." },
        ],
      },
      {
        heading: "Cost orientativ și când chemi specialistul",
        body: [
          "Măsurile de ventilație sunt ieftine; termoizolația și hidroizolația sunt investiții mai mari, dar elimină problema definitiv și reduc factura la încălzire.",
          "Chemi un specialist în termoizolații sau un instalator când umezeala persistă după aerisire, când apare mucegai recurent sau igrasie. Pe PropManage ceri oferte de la specialiști verificați, cu plată escrow.",
        ],
      },
    ],
    faq: [
      { q: "De ce am condens pe geamuri după ce am schimbat termopanele?", a: "Termopanele etanșe opresc aerisirea naturală. Fără ventilație controlată, vaporii rămân în casă și condensează pe suprafețele reci. Soluția e aerisirea regulată sau ventilația mecanică." },
      { q: "Termoizolația rezolvă umezeala?", a: "Termoizolația elimină punțile termice și condensul asociat, dar trebuie combinată cu ventilație corectă. Dacă umezeala vine din fundație (igrasie) sau infiltrații, se tratează separat." },
      { q: "Umezeala îmi crește factura la încălzire?", a: "Da. Un perete umed conduce căldura mult mai repede decât unul uscat, așa că pierzi energie și plătești mai mult." },
    ],
  },
  {
    slug: "probleme-acoperis",
    tag: "Acoperiș & izolații",
    title: "Probleme frecvente la acoperiș: semne, cauze și soluții | PropManage",
    h1: "Probleme frecvente la acoperiș și cum le previi",
    description:
      "De la țigle deplasate la jgheaburi înfundate și condens în pod — vezi cele mai frecvente probleme la acoperiș, cum le recunoști din timp, ce soluții există și când e nevoie de un specialist verificat.",
    readMins: 6,
    publishedAt: "2026-06-11",
    updatedAt: "2026-06-11",
    relatedCategories: ["acoperisuri", "termoizolatii"],
    relatedGuides: ["audit-tehnic-apartament-pret", "verificare-apartament-inainte-de-cumparare"],
    relatedProblems: ["infiltratii-acoperis", "umezeala-pereti"],
    sections: [
      {
        heading: "Cele mai frecvente probleme",
        body: [
          "Acoperișul este prima linie de apărare a casei, dar și cel mai neglijat sistem — pentru că nu îl vezi zilnic. Cele mai frecvente probleme sunt:",
          { type: "list", items: [
            "**Țigle/tablă deplasate sau sparte** de vânt și grindină.",
            "**Jgheaburi și burlane înfundate** cu frunze, care duc la infiltrații.",
            "**Șorțuri și racorduri neetanșe** la coș, lucarne și ventilații.",
            "**Condens în pod** din ventilație insuficientă.",
            "**Structură lemnoasă atacată** de umezeală sau insecte.",
          ] },
        ],
      },
      {
        heading: "Cum le recunoști din timp",
        body: [
          "O inspecție vizuală de două ori pe an (primăvara și toamna) și după furtuni previne majoritatea problemelor costisitoare.",
          { type: "list", items: [
            "Verifică din pod, pe timp de zi, dacă vezi lumină prin învelitoare.",
            "Urmărește petele de umezeală pe grinzi și astereală.",
            "Curăță jgheaburile și verifică scurgerea apei.",
            "După grindină, controlează dacă sunt țigle crăpate sau deplasate.",
          ] },
          { type: "callout", title: "Prevenție", body: "O inspecție și o curățare periodică costă puțin, dar previn infiltrațiile care degradează structura și finisajele — reparate ulterior cu costuri mult mai mari." },
        ],
      },
      {
        heading: "Soluții și mentenanță",
        body: [
          { type: "list", items: [
            "**Înlocuirea elementelor deteriorate** și reetanșarea racordurilor.",
            "**Curățarea și corectarea jgheaburilor**, montarea de parazăpezi.",
            "**Îmbunătățirea ventilației podului** pentru a elimina condensul.",
            "**Tratarea structurii lemnoase** împotriva umezelii și insectelor.",
            "**Plan de mentenanță** documentat, cu inspecții periodice.",
          ] },
          "Toate intervențiile pot fi documentate în Cartea Casei PropManage, ca istoricul tehnic al acoperișului să rămână la proprietate.",
        ],
      },
      {
        heading: "Când chemi specialistul",
        body: [
          "Cheamă un specialist în acoperișuri pentru orice lucrare la înălțime, după furtuni cu pagube vizibile sau când apar infiltrații. Lucrul pe acoperiș este periculos și cere echipament și experiență.",
          "Pe PropManage compari oferte de la specialiști verificați în acoperișuri, cu recenzii reale și plată protejată prin escrow.",
        ],
      },
    ],
    faq: [
      { q: "Cât de des trebuie verificat acoperișul?", a: "Ideal de două ori pe an — primăvara și toamna — și după furtuni sau grindină. O inspecție regulată previne infiltrațiile costisitoare." },
      { q: "Pot urca singur pe acoperiș?", a: "Nu este recomandat. Lucrul la înălțime este periculos și cere echipament de siguranță. O evaluare din pod poate fi făcută, dar intervențiile le lași unui specialist." },
      { q: "Cât rezistă un acoperiș?", a: "Depinde de material: învelitorile moderne pot dura 30-50 de ani cu mentenanță corectă, dar jgheaburile, șorțurile și hidroizolația necesită verificări mai dese." },
    ],
  },
];

export const getProblemaBySlug = (slug) => PROBLEME.find((p) => p.slug === slug) || null;
