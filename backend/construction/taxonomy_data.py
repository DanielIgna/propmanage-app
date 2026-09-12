"""CIP-A — Nomenclator MVP construcții România (~200 noduri).

Format: (legacy_category, nume_root, [(subcategorie, [servicii])])
`legacy_category` = id-ul flat existent în platformă (specialty / service_categories
pe specialiști + request.category). Root-urile noi (fără specialiști încă) folosesc
propriul slug ca legacy — devin vizibile automat când apare primul specialist verificat.
"""

TAXONOMY = [
    ("zugravit", "Zugrăveli & Finisaje pereți", [
        ("Zugrăveli interioare", ["Vopsea lavabilă", "Vopsea decorativă", "Var / sanitizare", "Stucco venețian"]),
        ("Zugrăveli exterioare", ["Vopsire fațadă", "Vopsire gard / poartă", "Vopsire soclu"]),
        ("Tapet & Decorativ", ["Montaj tapet", "Tapet fotografic", "Profile decorative polistiren"]),
        ("Pregătire suprafețe", ["Glet & șlefuire", "Reparații fisuri", "Amorsare"]),
    ]),
    ("parchet", "Pardoseli", [
        ("Parchet", ["Montaj parchet laminat", "Montaj parchet triplustratificat", "Raschetare & paluxare", "Montaj plinte"]),
        ("Pardoseli tehnice", ["Șapă autonivelantă", "Pardoseală epoxidică", "Covor PVC / linoleum"]),
        ("Pardoseli exterioare", ["Deck lemn / WPC", "Pavaj clincher"]),
    ]),
    ("faianta", "Placări ceramice & Piatră", [
        ("Faianță & Gresie", ["Montaj faianță baie", "Montaj gresie", "Gresie porțelanată mare (60x120+)", "Chituire & finisaje"]),
        ("Piatră naturală", ["Placare travertin", "Placare marmură", "Placare granit"]),
        ("Mozaic & Decor", ["Mozaic sticlă", "Frize decorative"]),
    ]),
    ("handyman", "Handyman & Reparații mici", [
        ("Montaj & Asamblare", ["Asamblare mobilier", "Montaj corpuri iluminat", "Montaj TV / suporți", "Montaj etajere / tablouri"]),
        ("Reparații rapide", ["Reparații uși / balamale", "Reparații mânere / yale", "Silicoane & etanșări"]),
        ("Întreținere curentă", ["Verificări periodice locuință", "Mici lucrări sezoniere"]),
    ]),
    ("gips_carton", "Gips-carton & Compartimentări", [
        ("Pereți & Compartimentări", ["Perete despărțitor gips-carton", "Placare pereți existenți", "Izolare fonică perete"]),
        ("Tavane", ["Tavan casetat", "Tavan fals simplu", "Scafe iluminat LED", "Tavan acustic"]),
        ("Elemente decorative", ["Nișe & rafturi gips-carton", "Arcade & forme speciale"]),
    ]),
    ("hvac", "HVAC & Climatizare", [
        ("Aer condiționat", ["Montaj AC split", "Montaj AC multisplit", "Igienizare AC", "Reparații AC"]),
        ("Încălzire", ["Montaj centrală termică", "Revizie centrală", "Încălzire în pardoseală", "Montaj calorifere"]),
        ("Ventilație", ["Ventilație cu recuperare căldură", "Hote & tubulatură", "Dezumidificare"]),
        ("Pompe de căldură", ["Pompă căldură aer-apă", "Mentenanță pompe căldură"]),
    ]),
    ("electric", "Instalații electrice", [
        ("Instalații interioare", ["Instalație electrică completă", "Înlocuire tablou electric", "Circuite noi prize / iluminat", "Verificare & buletin PRAM"]),
        ("Iluminat", ["Montaj spoturi & LED", "Iluminat arhitectural", "Iluminat exterior / grădină"]),
        ("Curenți slabi", ["Interfon / videointerfon", "Rețea date & WiFi", "Sisteme supraveghere CCTV", "Alarmă antiefracție"]),
        ("Smart Home", ["Automatizări iluminat", "Termostate inteligente", "Prize & senzori smart"]),
    ]),
    ("plumbing", "Instalații sanitare", [
        ("Instalații apă & canal", ["Instalație sanitară completă", "Înlocuire coloane / țevi", "Desfundare canalizare", "Detectare pierderi apă"]),
        ("Obiecte sanitare", ["Montaj vas WC / bideu", "Montaj cadă / cabină duș", "Montaj lavoar & baterii", "Montaj boiler"]),
        ("Filtrare & Tratare apă", ["Filtre apă potabilă", "Dedurizatoare", "Stații hidrofor"]),
    ]),
    ("interior_design", "Design interior & Amenajări", [
        ("Proiectare", ["Concept design & moodboard", "Randări 3D", "Proiect tehnic de execuție", "Consultanță cromatică"]),
        ("Amenajare completă", ["Amenajare apartament la cheie", "Amenajare casă la cheie", "Home staging pentru vânzare"]),
        ("Decorare", ["Selecție mobilier & decor", "Perdele & draperii", "Artă & accesorii"]),
    ]),
    ("constructii", "Construcții & Structuri", [
        ("Zidărie & Structură", ["Zidărie cărămidă / BCA", "Turnare fundații", "Stâlpi & centuri beton", "Consolidări structurale"]),
        ("Demolări", ["Demolare pereți neportanți", "Demolare & debarasare completă", "Decopertări"]),
        ("Extinderi", ["Extindere casă", "Mansardare", "Construcție anexă / garaj"]),
    ]),
    ("acoperisuri", "Acoperișuri & Învelitori", [
        ("Învelitori", ["Montaj țiglă metalică", "Montaj țiglă ceramică", "Membrană / hidroizolație terasă", "Tablă fălțuită"]),
        ("Structură acoperiș", ["Șarpantă lemn", "Reparații șarpantă", "Astereală & folii"]),
        ("Pluviale & Accesorii", ["Jgheaburi & burlane", "Parazăpezi", "Ferestre de mansardă"]),
    ]),
    ("fatade_termoizolatii", "Fațade & Termoizolații", [
        ("Termosistem", ["Termosistem polistiren", "Termosistem vată bazaltică", "Tencuială decorativă"]),
        ("Fațade ventilate", ["Fațadă ventilată HPL / ceramică", "Placări bond / aluminiu"]),
        ("Izolații speciale", ["Izolare pod / mansardă", "Izolare subsol / soclu", "Hidroizolații fundație"]),
    ]),
    ("tamplarie", "Tâmplărie & Ferestre", [
        ("Ferestre & Uși PVC/AL", ["Montaj ferestre PVC", "Montaj tâmplărie aluminiu", "Reglaje & service tâmplărie"]),
        ("Uși interior / exterior", ["Montaj uși interior", "Montaj ușă metalică intrare", "Uși glisante & pliante"]),
        ("Umbrire & Protecție", ["Rulouri exterioare", "Plase insecte", "Jaluzele & pergole"]),
    ]),
    ("amenajari_exterioare", "Amenajări exterioare & Grădină", [
        ("Pavaje & Alei", ["Pavele & borduri", "Alei piatră naturală", "Beton amprentat"]),
        ("Garduri & Porți", ["Gard plasă / panouri", "Gard beton / cărămidă", "Porți auto & automatizări"]),
        ("Grădină & Peisagistică", ["Gazon rulou / semănat", "Sisteme irigații", "Plantări & design peisagistic", "Terase & foișoare"]),
    ]),
]
