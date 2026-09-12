"""Conținut — Arhitectură (hub CMS-driven, service_pages slug=arhitectura)."""
from typing import Any

DEFAULT_CONTENT: dict[str, Any] = {
    "content_version": 1,
    "active": True,
    "seo": {
        "title": "Arhitectură — Proiecte Case, Autorizații, Extinderi & Mansardări | PropManage",
        "description": "Servicii complete de arhitectură: proiecte de case, documentații pentru autorizația de construire (DTAC), extinderi, mansardări, recompartimentări. Arhitecți cu drept de semnătură, în Cluj, Transilvania și toată România.",
        "canonical": "/arhitectura",
        "keywords": ["arhitect", "proiect casă", "autorizație de construire", "DTAC", "proiect arhitectură",
                     "extindere casă", "mansardare", "recompartimentare", "arhitect Cluj", "proiect casă România"],
    },
    "brand": {"name": "Arhitectură", "suffix": "by PropManage", "tagline": "De la idee la autorizație și execuție"},
    "hero": {
        "h1": "Arhitectură: proiecte, autorizații & execuție",
        "subtitle": "Case noi, extinderi, mansardări, recompartimentări — cu arhitecți cu drept de semnătură, documentație completă pentru autorizare și management de implementare. Un singur partener de la schiță la recepție.",
        "cta_primary": "Programează consultanța",
        "cta_secondary": "Cere ofertă",
    },
    "journey": ["Consultanță", "Studiu fezabilitate", "Anteproiect", "DTAC / Autorizare", "Proiect tehnic", "Execuție", "Recepție"],
    "positioning": {
        "title": "Proiecte oriunde în România",
        "text": "Documentațiile și proiectarea se realizează pentru orice localitate din țară, cu arhitecți parteneri cu drept de semnătură. Căutăm activ proiecte în Cluj-Napoca și Transilvania, unde oferim și supraveghere de șantier.",
        "badges": ["Acoperire națională", "Focus: Cluj-Napoca & Transilvania", "Arhitecți cu drept de semnătură", "Escrow"],
    },
    "benefits": [
        {"title": "Documentație completă", "text": "Certificat de urbanism, avize, DTAC, proiect tehnic — ghidați pas cu pas prin birocrație."},
        {"title": "Arhitecți verificați", "text": "Drept de semnătură OAR, portofoliu și recenzii verificate."},
        {"title": "Proiectare pe date reale", "text": "Releveu, scanare și audit tehnic înaintea proiectării — zero surprize."},
        {"title": "Buget controlat", "text": "Estimări de execuție pe capitole încă din faza de anteproiect."},
        {"title": "Management de implementare", "text": "Coordonăm execuția cu echipe verificate și plăți în escrow."},
        {"title": "Conectat la Interior & Exterior", "text": "Arhitectura, interiorul și exteriorul — un singur proces, în aceeași platformă."},
    ],
    "process_phases": [
        {"phase": "Definire", "intro": "Clarificăm ce se poate construi și cu ce buget.", "steps": [
            {"n": 1, "title": "Consultanță inițială", "text": "Obiective, teren/imobil existent, buget, termene. Prima discuție e gratuită."},
            {"n": 2, "title": "Studiu de fezabilitate", "text": "Analiza urbanistică (CU, POT/CUT), constrângeri tehnice și estimare de buget."},
            {"n": 3, "title": "Releveu / măsurători", "text": "Ridicarea exactă a existentului — baza oricărei intervenții corecte."},
        ]},
        {"phase": "Proiectare & Autorizare", "intro": "De la anteproiect la autorizația de construire.", "steps": [
            {"n": 4, "title": "Anteproiect & concept", "text": "Planuri, volumetrie, fațade — variante discutate și randate 3D."},
            {"n": 5, "title": "Avize & documentații", "text": "Certificat de urbanism, avize de la utilități și instituții."},
            {"n": 6, "title": "DTAC & autorizare", "text": "Documentația tehnică pentru autorizația de construire, depusă și urmărită."},
            {"n": 7, "title": "Proiect tehnic & detalii", "text": "PT + DE: structură, instalații, detalii de execuție — documentația pe care se construiește."},
        ]},
        {"phase": "Execuție", "intro": "Proiectul devine construcție, sub control.", "steps": [
            {"n": 8, "title": "Selecția constructorului", "text": "Cereri de ofertă către echipe verificate, comparare transparentă."},
            {"n": 9, "title": "Urmărire de șantier", "text": "Vizite de șantier, verificarea conformității cu proiectul, situații de lucrări."},
            {"n": 10, "title": "Recepție & carte tehnică", "text": "Recepția lucrării și arhivarea documentației în Digital Twin."},
        ]},
    ],
    "highlight": {
        "title": "Arhitectul potrivit + procesul potrivit",
        "intro": "Un proiect de arhitectură reușit înseamnă mai mult decât planuri frumoase: înseamnă autorizare fără blocaje, buget realist și execuție conformă. Platforma conectează arhitecți cu drept de semnătură, ingineri de structură și instalații, constructori verificați și management de proiect — într-un singur flux.",
        "items": ["Case noi", "Extinderi", "Mansardări", "Recompartimentări", "Schimbări de destinație",
                  "Documentații DTAC/DALI", "Proiecte tehnice complete", "Urmărire de șantier"],
        "outro": "De la certificatul de urbanism la recepția finală — totul documentat, totul într-un singur loc.",
    },
    "implementation": {
        "title": "Nu te lăsăm singur cu autorizația în mână.",
        "intro": "După autorizare, coordonăm execuția cu echipe verificate și plăți protejate prin escrow.",
        "points": ["Selecția constructorilor verificați", "Cereri de ofertă comparate", "Contracte și situații de lucrări",
                   "Urmărirea etapelor în platformă", "Vizite și verificări de șantier", "Comunicare centralizată",
                   "Documente și garanții arhivate", "Recepție și carte tehnică"],
    },
    "ecosystem": {
        "title": "Parte din același ecosistem",
        "intro": "Arhitectura se conectează natural cu restul platformei.",
        "links": [
            {"title": "Interior Intelligence", "text": "Design interior, arhitectură de interior & implementare.", "href": "/design-interior"},
            {"title": "Design Exterior", "text": "Peisagistică, terase, fațade.", "href": "/design-exterior"},
            {"title": "Marketplace", "text": "Cereri de ofertă pentru execuție.", "href": "/marketplace"},
            {"title": "Digital Twin", "text": "Cartea tehnică digitală a construcției.", "href": "/#twin"},
            {"title": "House Health", "text": "Monitorizarea construcției după recepție.", "href": "/house-health"},
            {"title": "Escrow", "text": "Plăți protejate pe etape.", "href": "/preturi"},
        ],
    },
    "faq": [
        {"q": "Cât costă un proiect de arhitectură?", "a": "Pentru case noi, proiectele complete (arhitectură + structură + instalații, faza DTAC+PT) se situează orientativ între 25 și 60 lei/mp construit, în funcție de complexitate. Documentațiile pentru extinderi și mansardări se ofertează per proiect. Primești oferte exacte gratuit."},
        {"q": "Cât durează obținerea autorizației de construire?", "a": "Realist: 3-6 luni de la demararea documentației, în funcție de localitate și avize (certificat de urbanism ~30 zile, avize 30-60 zile, autorizația ~30 zile de la depunerea completă). Urmărim tot procesul pentru tine."},
        {"q": "Pot construi fără autorizație o extindere mică?", "a": "Nu recomandăm niciodată. Aproape orice extindere sau modificare structurală cere autorizație; lucrările neautorizate blochează vânzarea, intabularea și asigurarea imobilului, și pot atrage amenzi și demolare."},
        {"q": "Aveți și ingineri de structură și instalații?", "a": "Da — proiectul complet include arhitectură, rezistență și instalații, cu specialiști verificați care lucrează coordonat în aceeași platformă."},
        {"q": "Lucrați în orașul meu?", "a": "Documentațiile și proiectarea se fac pentru orice localitate din România. Pentru urmărire de șantier avem acoperire directă în Cluj-Napoca și Transilvania, iar în rest colaborăm cu diriginți de șantier locali verificați."},
    ],
    "budgets": ["sub 15.000 lei", "15.000 – 40.000 lei", "40.000 – 100.000 lei", "peste 100.000 lei"],
    "local_cities": ["Cluj-Napoca", "București", "Brașov", "Sibiu", "Timișoara", "Iași", "Oradea"],
    "seo_article": [
        {"h2": "De ce ai nevoie de arhitect, nu doar de un proiect tip", "body": "Proiectele tip par ieftine până ajung pe terenul real: orientare greșită față de soare, fundații nepotrivite solului, POT/CUT depășite, compartimentări care nu se potrivesc familiei tale. Arhitectul proiectează pentru terenul, bugetul și viața ta — iar diferența de cost față de un proiect tip se recuperează din erorile evitate și din valoarea finală a imobilului."},
        {"h2": "Drumul complet al unei autorizații de construire", "body": "1) Certificatul de urbanism stabilește ce și cât poți construi. 2) Avizele (utilități, mediu, sănătate publică, pompieri unde e cazul) se obțin pe baza documentației tehnice. 3) DTAC — documentația tehnică pentru autorizația de construire — se depune la primărie. 4) După autorizare urmează proiectul tehnic și detaliile de execuție, anunțul de începere a lucrărilor și cartea tehnică a construcției. Procesul are zeci de pași mărunți — platforma îi urmărește pe toți, cu documentele arhivate central."},
        {"h2": "Extinderi și mansardări — capcanele frecvente", "body": "Extinderile par simple, dar ridică probleme reale: structura existentă trebuie expertizată, fundațiile vechi rar suportă etaje noi, iar vecinătățile impun retrageri. Mansardările cer verificarea șarpantei și a planșeului, plus autorizație aproape întotdeauna. Auditul tehnic făcut înaintea proiectării — parte din procesul nostru standard — elimină surprizele care explodează bugetele."},
        {"h2": "Arhitectură + Interior + Exterior — un singur proces", "body": "Cea mai eficientă construcție este cea proiectată integrat: arhitectura definește volumele și structura, designul de interior definește funcțiunile și finisajele, iar designul exterior leagă casa de teren. Pe PropManage cele trei discipline lucrează pe aceleași date — releveu, Digital Twin, buget comun — iar tu ai un singur punct de contact și plăți protejate prin escrow pe fiecare etapă."},
    ],
}
