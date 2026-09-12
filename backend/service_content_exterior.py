"""Conținut — Design Exterior (hub CMS-driven, service_pages slug=design-exterior)."""
from typing import Any

DEFAULT_CONTENT: dict[str, Any] = {
    "content_version": 1,
    "active": True,
    "seo": {
        "title": "Design Exterior & Amenajări Exterioare — Peisagistică, Terase, Fațade | PropManage",
        "description": "Design exterior complet: peisagistică, amenajare curte și grădină, terase, fațade, iluminat exterior și irigații. Proiectare + implementare cu specialiști verificați, în Cluj, Transilvania și toată România.",
        "canonical": "/design-exterior",
        "keywords": ["design exterior", "amenajări exterioare", "peisagistică", "amenajare curte", "amenajare grădină",
                     "design terasă", "fațade case", "iluminat exterior", "sisteme irigații", "landscape design România"],
    },
    "brand": {"name": "Exterior Design", "suffix": "by PropManage", "tagline": "Curtea, grădina și fațada — proiectate ca un întreg"},
    "hero": {
        "h1": "Design Exterior & Amenajări Exterioare",
        "subtitle": "Peisagistică, terase, fațade, iluminat și irigații — proiectate împreună, nu bucată cu bucată. De la conceptul 3D la implementare cu echipe verificate, cu plăți protejate prin escrow.",
        "cta_primary": "Programează consultanța",
        "cta_secondary": "Cere ofertă",
    },
    "journey": ["Consultanță", "Măsurători", "Concept 3D", "Proiect tehnic", "Implementare", "Recepție", "Întreținere"],
    "positioning": {
        "title": "Proiecte oriunde în România",
        "text": "Proiectăm remote pe bază de planuri, fotografii și scanări, iar pentru implementare coordonăm echipe locale verificate. Căutăm activ proiecte în Cluj-Napoca și Transilvania, unde putem gestiona lucrări complete de la concept la recepție.",
        "badges": ["Acoperire națională", "Focus: Cluj-Napoca & Transilvania", "Echipe verificate", "Escrow"],
    },
    "benefits": [
        {"title": "Un singur proiect coerent", "text": "Curtea, terasa, fațada și iluminatul gândite împreună — nu improvizații succesive."},
        {"title": "Concept 3D înainte de săpătură", "text": "Vezi randările înainte să comanzi prima piatră sau plantă."},
        {"title": "Specialiști verificați", "text": "Peisagiști, constructori de terase și electricieni din rețeaua verificată."},
        {"title": "Plăți protejate prin escrow", "text": "Banii se eliberează doar după ce aprobi fiecare etapă."},
        {"title": "Plan de întreținere", "text": "Grădina primește calendar de întreținere sezonieră — nu o lași să moară după recepție."},
        {"title": "Conectat la Digital Twin", "text": "Exteriorul intră în copia digitală a proprietății: planuri, instalații, garanții."},
    ],
    "process_phases": [
        {"phase": "Proiectare", "intro": "De la teren la concept vizual.", "steps": [
            {"n": 1, "title": "Consultanță & analiză teren", "text": "Orientare, sol, pante, vecinătăți, stil dorit și buget."},
            {"n": 2, "title": "Măsurători & releveu", "text": "Ridicarea exactă a terenului și a construcțiilor existente."},
            {"n": 3, "title": "Concept & randări 3D", "text": "Zonificare, circulații, plantări, terase, iluminat — vizualizate fotorealist."},
            {"n": 4, "title": "Proiect tehnic & bugetare", "text": "Planuri de execuție, liste de plante și materiale, buget pe capitole."},
        ]},
        {"phase": "Implementare", "intro": "Execuție coordonată, nu șantier lăsat de izbeliște.", "steps": [
            {"n": 5, "title": "Selecția echipelor", "text": "Cereri de ofertă către specialiști verificați, comparare transparentă."},
            {"n": 6, "title": "Execuție pe etape", "text": "Terasamente, hardscape, instalații (irigații, iluminat), plantări."},
            {"n": 7, "title": "Verificare & recepție", "text": "Controale de calitate documentate și recepție formală."},
        ]},
        {"phase": "Viață lungă", "intro": "Exteriorul e viu — are nevoie de plan.", "steps": [
            {"n": 8, "title": "Calendar de întreținere", "text": "Tăieri, fertilizări, pornirea/oprirea irigațiilor — planificate sezonier."},
            {"n": 9, "title": "Actualizare Digital Twin", "text": "Planurile și instalațiile exterioare intră în dosarul digital al proprietății."},
        ]},
    ],
    "highlight": {
        "title": "Exteriorul și interiorul — aceeași proprietate, același proces",
        "intro": "Design Exterior folosește aceeași fundație ca Interior Intelligence: audit, măsurători, Digital Twin, specialiști verificați și management de implementare. Dacă renovezi și interiorul, cele două proiecte se coordonează în aceeași platformă.",
        "items": ["Peisagistică & plantări", "Terase & pergole", "Fațade & finisaje exterioare", "Alei & pavaje",
                  "Iluminat arhitectural", "Sisteme de irigații", "Garduri & împrejmuiri", "Mobilier de exterior"],
        "outro": "Un singur partener pentru toată proprietatea — în interior și în exterior.",
    },
    "implementation": {
        "title": "Nu doar proiectul. Și execuția.",
        "intro": "Coordonăm implementarea completă cu echipe verificate și plăți protejate prin escrow.",
        "points": ["Selecția specialiștilor verificați", "Cereri de ofertă comparate transparent", "Management de proiect",
                   "Urmărirea etapelor în platformă", "Verificarea calității", "Comunicare centralizată",
                   "Documente și garanții arhivate", "Recepția lucrării"],
    },
    "ecosystem": {
        "title": "Parte din același ecosistem",
        "intro": "Fiecare etapă e conectată la platforma PropManage.",
        "links": [
            {"title": "Interior Intelligence", "text": "Design interior, arhitectură & implementare.", "href": "/design-interior"},
            {"title": "Arhitectură", "text": "Proiecte autorizate, extinderi, case noi.", "href": "/arhitectura"},
            {"title": "Marketplace", "text": "Cereri de ofertă pentru orice lucrare.", "href": "/marketplace"},
            {"title": "Digital Twin", "text": "Copia digitală completă a proprietății.", "href": "/#twin"},
            {"title": "House Health", "text": "Monitorizare și întreținere planificată.", "href": "/house-health"},
            {"title": "Escrow", "text": "Plăți protejate pe etape.", "href": "/preturi"},
        ],
    },
    "faq": [
        {"q": "Cât costă un proiect de design exterior?", "a": "Proiectele de concept pentru curți pornesc de la 15-25 lei/mp de teren amenajat, iar proiectele complete cu randări 3D, plan de plantare și proiect de irigații/iluminat ajung la 30-60 lei/mp. Primești oferte exacte gratuit, după completarea formularului."},
        {"q": "Lucrați și iarna?", "a": "Proiectarea se face tot anul. Implementarea se planifică sezonier: hardscape (terase, alei, garduri) se poate executa aproape tot anul, plantările se programează primăvara și toamna."},
        {"q": "Pot face doar o parte din proiect?", "a": "Da, procesul e modular — poți începe cu terasa sau doar cu iluminatul. Recomandăm însă conceptul de ansamblu întâi, ca fiecare etapă viitoare să se așeze într-un plan coerent."},
        {"q": "Cum sunt protejate plățile?", "a": "Prin escrow: banii sunt blocați în platformă și se eliberează către echipe doar după ce aprobi fiecare etapă executată."},
        {"q": "Lucrați în orașul meu?", "a": "Da — proiectăm remote în toată România, iar pentru execuție coordonăm echipe locale verificate. În Cluj-Napoca și Transilvania oferim procesul complet cu prezență la fața locului."},
    ],
    "budgets": ["sub 10.000 lei", "10.000 – 30.000 lei", "30.000 – 80.000 lei", "peste 80.000 lei"],
    "local_cities": ["Cluj-Napoca", "București", "Brașov", "Sibiu", "Timișoara", "Iași", "Oradea"],
    "seo_article": [
        {"h2": "Ce cuprinde designul exterior profesionist", "body": "Designul exterior tratează curtea, grădina, terasa și fațada ca un sistem unitar: zonificare funcțională (relaxare, dining, joacă, utilitar), circulații, vegetație adaptată solului și orientării, hardscape (pavaje, ziduri, pergole), iluminat arhitectural și irigații. Diferența dintre o curte „umplută cu plante” și una proiectată se vede în fiecare sezon: mai puțină întreținere, mai multă utilizare reală a spațiului și o valoare de proprietate vizibil mai mare."},
        {"h2": "De ce începi cu un concept de ansamblu", "body": "Cea mai frecventă greșeală în amenajările exterioare este execuția pe bucăți fără plan: întâi terasa, apoi gazonul, apoi se sapă totul înapoi pentru irigații și cabluri de iluminat. Conceptul de ansamblu stabilește de la început traseele tehnice, cotele, zonele plantate și materialele — astfel încât fiecare etapă executată să nu fie demolată de următoarea. Costul proiectării se recuperează de regulă doar din săpăturile evitate."},
        {"h2": "Peisagistică adaptată climei din România", "body": "Plantele frumoase în catalog nu supraviețuiesc automat în clima locală. Un plan de plantare profesionist ține cont de zona de rusticitate, expunerea la soare și vânt, tipul de sol și consumul de apă. În Transilvania recomandăm de regulă specii rezistente la îngheț și amplitudini termice, cu irigare eficientă prin picurare — grădina rămâne verde cu costuri de întreținere controlate."},
        {"h2": "Terase, pergole și fațade — hardscape care durează", "body": "Partea construită a exteriorului cere aceleași rigori ca o casă: fundații corecte sub pavaje, pante de scurgere, hidroizolații la terase, lemn tratat sau compozit la pergole, finisaje de fațadă compatibile cu suportul. Pe PropManage, execuția este făcută de echipe verificate, cu verificări de calitate documentate pe fiecare etapă și garanții arhivate în Digital Twin."},
    ],
}
