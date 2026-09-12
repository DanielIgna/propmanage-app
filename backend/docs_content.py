"""PropManage — Training & Onboarding documentation content.

Single source of truth for the in-app Knowledge Base. Each doc is a Python dict
with strict structure so the React viewer and the PDF renderer share the same
schema.

Structure per doc:
    slug, role, title, subtitle, version, updated_at, email_intro,
    sections: [
        { heading: str,
          body: [
            "paragraph string" |
            {type: "h3", text: str} |
            {type: "list", items: [str, ...]} |
            {type: "callout", title: str, body: str, variant: "info|warn|success"} |
            {type: "code", text: str} |
            {type: "image_placeholder", caption: str, animation: "css_pulse|lottie|video", src: str} |
            {type: "steps", items: [{title: str, body: str}, ...]} |
            {type: "screencast", src: str, caption: str}     # MP4/GIF
            {type: "lottie", src: str, caption: str}         # JSON Lottie file under /animations/
          ]
        }, ...
    ],
    faq: [{q: str, a: str}, ...]
"""
from __future__ import annotations

UPDATED = "2026-06-23"

# Re-usable callouts
_CB_ESCROW = {
    "type": "callout", "variant": "info",
    "title": "Plata escrow — protecția ta de bază",
    "body": "Banii pe care îi plătești NU ajung la specialist până când tu nu apeși \"Confirmă finalizare\". Sunt blocați în escrow la PropManage, indisponibili pentru oricine altcineva. Dacă lucrarea nu e bună, deschizi o dispută și banii se rambursează."
}

# Specialist-perspective version (audience-correct: specialist is paid, not paying)
_CB_ESCROW_SPECIALIST = {
    "type": "callout", "variant": "info",
    "title": "Plata escrow — siguranța ta că ești plătit",
    "body": "Clientul alimentează escrow ÎNAINTE să începi lucrarea, iar banii sunt blocați la PropManage. Nu mai există riscul de tipul «lucrez și nu mai sunt plătit». După ce clientul confirmă finalizarea, 95% din sumă ajunge automat în portofelul tău (5% comision platformă, 4% dacă ai badge VERIFIED). În caz de dispută, fondurile rămân blocate până la medierea echipei."
}

# ============================================================================
# 1) CLIENT — Proprietar
# ============================================================================
CLIENT_DOC = {
    "slug": "client",
    "role": "client",
    "title": "Ghid Complet pentru Proprietari (Client)",
    "subtitle": "Cum folosești PropManage pentru a-ți gestiona proprietatea: marketplace specialiști, plăți escrow, Digital Twin, dispute, AI Concierge.",
    "version": "1.0",
    "updated_at": UPDATED,
    "email_intro": "Echipa PropManage îți trimite ghidul oficial pentru utilizarea platformei ca proprietar. Conține tot ce ai de știut: de la postarea primei cereri, la dispute și escrow.",

    "sections": [
        {
            "heading": "1. Ce poți face ca proprietar (Overview)",
            "body": [
                "Ca client pe PropManage ai acces la 4 module principale:",
                {"type": "list", "items": [
                    "**Marketplace** — descoperi specialiști verificați, citești recenzii reale, ceri oferte directe",
                    "**Cereri & Lucrări** — postezi o cerere, primești 3-5 oferte în 24h, alegi cea mai bună",
                    "**Plăți escrow** — plătești în siguranță, banii se eliberează doar după confirmarea ta",
                    "**Digital Twin** — un model 3D al proprietății tale (premium) pe care specialiștii pot marca probleme și soluții vizual",
                    "**AI Concierge** — asistent inteligent care răspunde 24/7 la întrebări despre platformă",
                    "**Dispute & garanție** — protecție 12 luni garanție pe lucrare + echipă de mediere",
                ]},
                _CB_ESCROW,
            ],
        },
        {
            "heading": "2. Primul login & setup (5 minute)",
            "body": [
                {"type": "steps", "items": [
                    {"title": "Creează contul", "body": "Mergi la propmanage.ro/register → completează nume, email, telefon, parolă. Sau folosește \"Login cu Google\" pentru acces instant."},
                    {"title": "Verifică emailul", "body": "Click pe linkul primit pentru a activa contul. Dacă nu îl vezi, verifică folderul Spam."},
                    {"title": "Adaugă o proprietate", "body": "În dashboard → \"Proprietățile mele\" → \"Adaugă proprietate\". Completează: adresă, suprafață, tip (apartament/casă), anul construcției."},
                    {"title": "Setează 2FA (recomandat)", "body": "Profil → Securitate → activează \"Autentificare în 2 pași\" cu Google Authenticator. Adaugă 5 minute de muncă, dar protejează contul pentru totdeauna."},
                    {"title": "Setează preferințe notificări", "body": "Profil → Notificări → alege ce vrei să primești pe email, push, sau ambele."},
                ]},
                {"type": "image_placeholder", "caption": "Tour interactiv primul login (5 pași)", "animation": "css_pulse", "src": "client/onboarding-tour"},
            ],
        },
        {
            "heading": "3. Postează prima cerere (cel mai important flow)",
            "body": [
                "Fluxul standard pentru a obține o lucrare:",
                {"type": "steps", "items": [
                    {"title": "Click \"Cerere nouă\"", "body": "Din dashboard. Modal-ul se deschide."},
                    {"title": "Alege specialitatea", "body": "Electric, Sanitar, HVAC, Zugrăveală, Design Interior, etc. (10 categorii)."},
                    {"title": "Descrie problema", "body": "Scrie 2-3 fraze clare. Ex: \"Am o pată mare de umiditate pe perete în baie. Apare după ce fac duș. Vreau identificare cauză + remediere.\""},
                    {"title": "Adaugă poze (puternic recomandat!)", "body": "1-3 poze cu zona problemă. Cererile cu poze primesc oferte cu 40% mai bune și mai rapid."},
                    {"title": "Setează urgența", "body": "Urgent (24h), Săptămâna asta, Luna asta, Flexibil."},
                    {"title": "Trimite", "body": "Sistemul notifică automat 5-10 specialiști din zona ta care lucrează în specialitatea respectivă. Vei primi oferte în 4-24 ore."},
                ]},
                {"type": "screencast", "src": "client/post-request.mp4", "caption": "Demo: postare cerere de la zero la trimis (38 secunde)"},
                {"type": "callout", "variant": "success",
                 "title": "Pro tip — Lead Fee",
                 "body": "Pentru a vedea telefonul/datele tale de contact, specialistul plătește o taxă de Lead (45 RON). Asta filtrează automat oamenii neserioși — doar specialiștii care chiar vor lucrarea îți contactează."},
            ],
        },
        {
            "heading": "4. Compari oferte și alegi specialistul",
            "body": [
                "După ce specialiștii trimit oferte (5-15 minute - 24 ore), vezi pe rând:",
                {"type": "list", "items": [
                    "**Preț propus** + dacă include sau nu materialele",
                    "**Timp de execuție** estimat",
                    "**Health Score** (algoritm intern PropManage — combinație: reviews, rate de dispute, vechime, portofoliu)",
                    "**Rating + număr recenzii** istorice",
                    "**Badge VERIFIED** (lime) — documente validate manual de echipa noastră",
                    "**Portofoliu** — poze cu lucrări anterioare",
                ]},
                {"type": "callout", "variant": "warn",
                 "title": "Nu alege doar pe baza prețului",
                 "body": "Un specialist cu 30% mai ieftin dar fără recenzii și fără VERIFIED este de cele mai multe ori o capcană. Verifică Health Score, citește recenziile și abia apoi decide. Diferența de 200 RON merită investiția în calitate."},
            ],
        },
        {
            "heading": "5. Plata escrow — cum funcționează",
            "body": [
                "Când accepți oferta, sistemul îți cere să \"alimentezi escrow\":",
                {"type": "steps", "items": [
                    {"title": "Alegi metoda de plată", "body": "Card (Visa/Mastercard) prin Stripe — instant, sau transfer bancar (1-2 zile lucrătoare)."},
                    {"title": "Banii se blochează", "body": "PropManage primește banii în escrow (cont separat de operațiuni). Specialistul primește notificare \"Escrow alimentat\" și are voie să înceapă."},
                    {"title": "Specialistul lucrează", "body": "Comunici prin chat-ul aplicației. Toate mesajele se salvează ca dovadă."},
                    {"title": "Confirmi finalizarea", "body": "Când lucrarea e gata și inspectată, apeși \"Confirm finalizare\" în pagina lucrării. Acesta este momentul când banii pleacă din escrow către specialist."},
                    {"title": "Garanție 12 luni", "body": "Chiar dacă banii sunt eliberați, ai garanție 12 luni pentru manoperă. Orice problemă o semnalezi în aplicație și specialistul e obligat să remedieze gratuit."},
                ]},
                {"type": "lottie", "src": "/animations/escrow-flow.json", "caption": "Animație: cum se mișcă banii prin escrow"},
            ],
        },
        {
            "heading": "6. Disputa — când lucrurile merg prost",
            "body": [
                "Dacă specialistul nu finalizează, finalizează prost, sau apar probleme:",
                {"type": "steps", "items": [
                    {"title": "Strânge dovezi", "body": "Poze, video, mesaje din chat care arată problema. Cu cât mai detaliat, cu atât mediere mai rapidă."},
                    {"title": "Apasă \"Deschide dispută\"", "body": "Pe pagina lucrării. Banii din escrow se îngheață imediat — specialistul NU îi primește."},
                    {"title": "Descrie problema clar", "body": "Explică ce nu e ok, ce ai cerut, ce ai primit. Atașează dovezile."},
                    {"title": "Echipa de mediere intervine", "body": "În maxim 48 ore. Cere și perspectiva specialistului, analizează dovezile."},
                    {"title": "Decizia finală", "body": "Una din 3 variante: (a) rambursare integrală — banii revin pe cardul tău în 3-5 zile; (b) plată parțială (split equitabil); (c) plată completă specialistului (dacă cererea ta e neîntemeiată). În 2025, 67% din dispute s-au decis în favoarea clientului."},
                ]},
            ],
        },
        {
            "heading": "7. Digital Twin (premium) — modelul 3D al proprietății",
            "body": [
                "Premium feature pentru clienții care vor să gestioneze eficient proprietatea:",
                {"type": "list", "items": [
                    "Încarci un model 3D al proprietății (`.glb`/`.gltf` — îți face arhitectul sau topograful)",
                    "Suprapui peste el plan 2D structural (PDF)",
                    "Tu sau specialiștii adăugați marchează **pin-uri** vizual pe model (ex: \"crăpătură perete\", \"priză defectă\")",
                    "Pin-urile au categorie, prioritate, comentarii, status (deschis/în lucru/rezolvat)",
                    "Specialiștii trimit **rapoarte oficiale** cu PDF generat automat (poze + plan + thread comentarii)",
                    "Aprobi raportul cu un click prin link tokenizat — fără login necesar",
                ]},
                {"type": "callout", "variant": "info",
                 "title": "De ce e util",
                 "body": "În loc să tot urci poze și să descrii prin chat unde e problema (\"a doua priză din stânga, pe peretele opus ferestrei\"), pin-ul de pe Twin spune exact unde, ce și de când e problema. Reduce neînțelegerile cu 80%."},
                {"type": "screencast", "src": "client/digital-twin.mp4", "caption": "Demo: navigare 3D + adăugare pin pe modelul casei"},
            ],
        },
        {
            "heading": "8. Comunicarea cu celelalte roluri",
            "body": [
                {"type": "h3", "text": "Cu specialiștii"},
                "Doar prin chat-ul aplicației (NU pe WhatsApp/SMS direct). Asta îți garantează că ai dovezile mesajelor în caz de dispută. Telefonul specialistului apare doar după ce el plătește lead fee-ul.",
                {"type": "h3", "text": "Cu operatorul"},
                "Operatorul (echipa internă PropManage) validează modelele Digital Twin. Comunicarea se face prin sistem de \"non-conformities\" în pagina Twin-ului. Tu primești email + notificare în-app când ai mesaj nou.",
                {"type": "h3", "text": "Cu administratorul"},
                "Pentru probleme generale: contact@propmanage.ro sau butonul \"Help\" din dashboard care deschide AI Concierge. Pentru dispute, există echipa dedicată în-app.",
            ],
        },
        {
            "heading": "9. Edge cases & troubleshooting",
            "body": [
                {"type": "h3", "text": "Specialistul nu răspunde de 48h"},
                "Deschide chat-ul, apasă \"Raportează absență\". Sistemul îi dă 24h să răspundă, după care îți permite să anulezi lucrarea fără penalități.",
                {"type": "h3", "text": "Cardul a fost respins la escrow"},
                "Cauze frecvente: 3D Secure neactiv, fonduri insuficiente, restricție online. Soluție: verifică limita online la bancă (Settings → Plăți online → Activează). Alternativă: transfer bancar din pagina lucrării.",
                {"type": "h3", "text": "Am uitat parola"},
                "Login page → \"Am uitat parola\" → introduci email → primești link reset valabil 60 minute.",
                {"type": "h3", "text": "Nu primesc emailuri de la PropManage"},
                "Verifică folderul Spam. Marchează un email PropManage ca \"Not spam\" — viitoarele vor merge direct în inbox. Verifică și că emailul din profil e corect.",
                {"type": "h3", "text": "Vreau să-mi șterg contul (GDPR)"},
                "Profil → Confidențialitate → \"Cere ștergerea contului\". Procesul durează 30 zile (perioadă în care îți poți răzgândi). După, datele tale sunt șterse complet conform GDPR.",
            ],
        },
        {
            "heading": "10. Best Practices (sfaturile noastre după 1000+ lucrări)",
            "body": [
                {"type": "list", "items": [
                    "**Cere mereu minim 3 oferte.** Diferența între cea mai mică și cea mai mare poate fi 40%. Nu accepta prima ofertă.",
                    "**Citește 5-10 recenzii** ale specialistului ales, nu doar nota. Caută cuvinte cheie: \"punctual\", \"curățenie\", \"respect cuvânt dat\".",
                    "**Cere oferta scrisă** cu preț FIX, înainte de a alimenta escrow. Nu \"preț orientativ\".",
                    "**Plătește prin escrow chiar și pentru lucrări mici** (sub 500 RON). Asigurare gratuită.",
                    "**Inspectează vizual lucrarea ÎNAINTE să confirmi finalizarea.** După confirmare, banii pleacă. Garanția acoperă defectele ascunse, dar e mai ușor să refuzi acum decât să mediezi după.",
                    "**Lasă o recenzie sinceră** — ajuți următorii clienți să aleagă bine. Recenzia poate fi modificată în 30 zile dacă te răzgândești.",
                    "**Folosește chat-ul aplicației, NU WhatsApp.** Mesajele de pe WhatsApp NU sunt dovezi în dispute.",
                    "**Setează urgența realist.** \"Urgent (24h)\" costă 15-25% peste preț. Pentru lucrări care pot aștepta o săptămână, alege \"Flexibil\" și obții discount.",
                ]},
            ],
        },
        {
            "heading": "11. Studii de caz reale",
            "body": [
                {"type": "h3", "text": "Cazul 1: Renovare baie 8 mp în București"},
                "**Buget client**: 5.000 RON. **Ofertă primită**: 7.500 RON. **Cum a economisit**: a cumpărat singur faianța premium de la Hornbach (cu 25% reducere față de prețul taxat de specialist), a negociat manopera la 5.200 RON. **Total final**: 5.180 RON. **Calitate**: 5/5 stele, lucrare în 6 zile.",

                {"type": "h3", "text": "Cazul 2: Dispută rezolvată în 3 zile"},
                "**Lucrare**: zugrăveală apartament 60 mp, 3.500 RON. **Problemă**: după 5 zile au apărut pete de igrasie nedezvelite anterior. Specialistul cerea bani în plus pentru tratament. **Decizia mediere**: igrasia era preexistentă, specialistul nu putea ști. **Rezultat**: split 70% specialist (manoperă deja făcută), 30% rambursare client (pentru re-zugrăveală necesară după tratament). Ambele părți mulțumite.",

                {"type": "h3", "text": "Cazul 3: Folosirea Digital Twin pentru o casă veche"},
                "**Context**: client cu casă din 1968, multiple probleme structurale ascunse. **Soluție**: a încărcat scanare 3D făcută de un topograf (2.500 RON one-time). În 6 luni, 4 specialiști diferiți au lucrat la diferite zone marcând pin-uri pe model. **Avantaj**: noul specialist vede istoricul complet al proprietății înainte de a propune lucrarea — reduce timpul de diagnoză cu 70% și greșelile cu 90%.",
            ],
        },
    ],

    "faq": [
        {"q": "Cât costă să folosesc PropManage ca client?", "a": "**Zero**. Plățile, cererile, marketplace-ul, AI Concierge, totul este gratuit pentru client. Specialistul plătește comisionul de 5% din lucrare. Singurul cost adițional pentru tine: lead fee de 45 RON (opțional, doar dacă vrei ca specialistul să aibă numărul tău de telefon — alternativ comunicați doar prin chat)."},
        {"q": "Pot folosi PropManage fără să am o proprietate înregistrată?", "a": "Nu. Adăugarea unei proprietăți este obligatorie pentru a posta cereri. Asta ne ajută să recomandăm specialiști din zona ta corectă. Procesul durează 2 minute — adresă + suprafață + tip."},
        {"q": "Specialiștii pot vedea adresa exactă a proprietății?", "a": "Doar specialistul ALES (cel a cărui ofertă o accepți) vede adresa completă. Toți ceilalți specialiști care primesc cererea văd doar cartierul / zona. Asta protejează intimitatea ta."},
        {"q": "Ce se întâmplă dacă lucrarea costă mai puțin decât suma blocată în escrow?", "a": "Specialistul ajustează factura finală în aplicație. Diferența se rambursează automat pe cardul tău în 3-5 zile lucrătoare. Ex: ai blocat 3.000 RON, lucrarea a costat 2.700 RON → primești 300 RON înapoi."},
        {"q": "Pot anula o cerere postată?", "a": "Da, atâta timp cât nu ai acceptat încă o ofertă. Apeși \"Anulează\" în pagina cererii. Specialiștii care îți trimiseseră oferte primesc notificare automată. Dacă deja ai acceptat o ofertă și alimentat escrow, anularea necesită acord cu specialistul sau dispută."},
        {"q": "Cum funcționează garanția de 12 luni?", "a": "Începe din ziua confirmării finalizării. În această perioadă, dacă apare un defect cauzat de manoperă (NU de uzură normală sau intervenții externe), apeși \"Cere remediere\" pe pagina lucrării. Specialistul are 48h să răspundă și 7 zile să remedieze gratuit. Dacă refuză, escaladăm la mediere și acoperim noi costul remedierii prin alt specialist."},
        {"q": "Recenzia mea este publică sau anonimă?", "a": "Publică, dar afișată cu prenume + inițială nume (ex: \"Andrei P.\"). Asta crește încrederea pentru viitorii clienți. Conținutul recenziei nu poate fi modificat de specialist sau echipa PropManage — doar tu o poți edita în primele 30 zile."},
        {"q": "Pot avea mai multe proprietăți pe același cont?", "a": "Da, nelimitat. Util dacă ești investitor cu portofoliu de apartamente. Fiecare proprietate are propriul Digital Twin, istoric lucrări, și panou de control separat."},
        {"q": "Datele mele financiare sunt în siguranță?", "a": "Da. Nu stocăm date de card pe serverele PropManage — totul trece direct prin Stripe (PCI-DSS Level 1, cel mai înalt standard de securitate financiară din lume). Vezi doar ultimele 4 cifre + brand-ul cardului în profil. Banii din escrow sunt în cont segregat la BCR."},
        {"q": "Cât durează până primesc primele oferte după ce postez o cerere?", "a": "Median: 47 minute. 80% din cereri primesc prima ofertă în maxim 4 ore. Pentru categorii cu cerere mare (instalator, electrician în orașe mari) — sub 30 minute. Pentru categorii nișate (HVAC industrial, restaurări monumente) — 24-48 ore."},
    ],
}


# ============================================================================
# 2) SPECIALIST — Furnizor de servicii verificat
# ============================================================================
SPECIALIST_DOC = {
    "slug": "specialist",
    "role": "specialist",
    "title": "Ghid Complet pentru Specialiști",
    "subtitle": "Cum câștigi mai bine pe PropManage: profil optimizat, lead capture, comunicare client, escrow, dispute, best practices.",
    "version": "1.0",
    "updated_at": UPDATED,
    "email_intro": "Bine ai venit în comunitatea PropManage. Ghidul acesta îți arată cum să maximizezi câștigurile și să eviți greșelile clasice ale specialiștilor noi.",
    "sections": [
        {
            "heading": "1. Cum câștigi bani pe PropManage (Overview)",
            "body": [
                "PropManage este un marketplace cu **cerere reală** — clienții postează cereri zilnic și caută activ ofertă. Tu, ca specialist, intri în 3 fluxuri principale de venit:",
                {"type": "list", "items": [
                    "**Lucrări directe** — cereri postate la categoria ta, în zona ta de acoperire",
                    "**Smart Match** — sistemul te recomandă proactiv proprietarilor pe baza Health Score",
                    "**Recomandări organice** — clienții te găsesc pe pagina ta publică (`/specialists/{id}`) via SEO și marketplace",
                ]},
                _CB_ESCROW_SPECIALIST,
                {"type": "callout", "variant": "info", "title": "Costul tău",
                 "body": "Comision platformă: **5%** (4% pentru badge VERIFIED). Lead fee opțional: **45 RON** dacă vrei numărul de telefon al clientului. În rest — gratis: profil, portofoliu, chat, escrow."},
            ],
        },
        {
            "heading": "2. Profil care convertește (cele 7 elemente critice)",
            "body": [
                "Profilurile cu rate de conversie mare (vizitator → contact) au TOATE aceste 7 elemente:",
                {"type": "steps", "items": [
                    {"title": "Avatar profesional", "body": "Poză cap-piept, lumină naturală, NU selfie cu căști sau în mașină. Specialiștii fără poză primesc cu 60% mai puține contactări."},
                    {"title": "Specialitate clară", "body": "O singură specialitate principală (cea în care ești cel mai bun). Adaugi secundare doar dacă chiar excelezi (max 3)."},
                    {"title": "Bio scurt și concret (200-400 caractere)", "body": "Cine ești, câți ani de experiență, ce te diferențiază. NU \"echipă serioasă, prețuri OK\"."},
                    {"title": "Portofoliu cu 8-15 poze", "body": "Înainte/după, detaliu de execuție, finisaje. Specialiștii cu 10+ poze au rating mediu cu 0.4 stele mai mare."},
                    {"title": "Zone de acoperire reale", "body": "Doar zonele unde chiar te deplasezi. Marcaj 5 cartiere în care lucrezi rar = recenzii proaste pentru anulări în ultim moment."},
                    {"title": "Documente uploadate pentru VERIFIED", "body": "CI + certificat fiscal + asigurare răspundere civilă + diplome/atestate. Badge VERIFIED (lime) crește conversia cu 2.5x."},
                    {"title": "Răspunsuri rapide", "body": "Sistemul măsoară response_time mediu. Sub 1h = booster algoritmul, peste 8h = penalizare în ranking."},
                ]},
            ],
        },
        {
            "heading": "3. Cum primești lead-uri și cum răspunzi corect",
            "body": [
                {"type": "h3", "text": "Notificările tale"},
                "Când un client postează o cerere în categoria + zona ta, primești instant: push browser + email + în-app badge. Răspuns în primele **30 minute** = chance maximă să câștigi lucrarea (clienții acceptă oferta primită în primele 2h în 70% din cazuri).",

                {"type": "h3", "text": "Cum scrii o ofertă câștigătoare"},
                {"type": "steps", "items": [
                    {"title": "Citește cererea în întregime", "body": "Inclusiv pozele atașate. Nu trimite \"Salut, sun-mă\". Asta îți pierde 90% din lucrări."},
                    {"title": "Preț FIX, nu \"orientativ\"", "body": "Calculează rapid, scrie preț clar. Dacă nu poți estima fără vizită, scrie \"Vizită de evaluare gratuită, ofertă fixă în 24h\"."},
                    {"title": "Timp realist", "body": "Nu promite 24h dacă știi că ai nevoie de 3 zile. Recenziile proaste vin din termene depășite."},
                    {"title": "Diferențiator scurt", "body": "1-2 fraze de ce TE alege pe tine. Ex: \"Folosesc doar materiale Schneider/Legrand, garanție 24 luni (peste media)\"."},
                    {"title": "Întreabă", "body": "Pune o întrebare clarificatoare. Arată că ai citit și ești specialist."},
                ]},
                {"type": "callout", "variant": "success", "title": "Pro tip",
                 "body": "În ofertă, menționează că plata se face prin escrow. Clienții care nu cunosc platforma sunt mai relaxați când văd asta — îi face să accepte oferta mai ușor."},
            ],
        },
        {
            "heading": "4. Lead Fee — când să plătești și când nu",
            "body": [
                "După ce trimiți o ofertă, clientul o vede dar **NU îți vede telefonul/email-ul direct**. Doar dacă plătești **45 RON Lead Fee**, el primește datele tale de contact.",
                {"type": "h3", "text": "Plătește Lead Fee când:"},
                {"type": "list", "items": [
                    "Cererea valorează **> 1000 RON** (45 RON e <5% din valoare)",
                    "Clientul a răspuns activ la oferta ta cu întrebări concrete",
                    "Lucrarea pare urgentă și ai capacitate să o execuți rapid",
                    "Zona de cerere e în plin centrul tău de operare",
                ]},
                {"type": "h3", "text": "NU plăti Lead Fee când:"},
                {"type": "list", "items": [
                    "Cererea e vagă (\"Vreau să mi se facă ceva pe la apartament\")",
                    "Clientul are 0 cereri anterioare ȘI 0 review-uri lăsate (probabil cont fake)",
                    "Lucrarea < 200 RON (Lead Fee = 22% din valoare, nu merită)",
                    "Cererea are deja 8+ oferte (concurență prea mare)",
                ]},
            ],
        },
        {
            "heading": "5. Escrow — cum primești banii",
            "body": [
                {"type": "steps", "items": [
                    {"title": "Clientul acceptă oferta ta", "body": "Primești notificare \"Oferta acceptată\". Clientul are 48h să alimenteze escrow."},
                    {"title": "Escrow alimentat", "body": "Primești notificare \"Banii sunt blocați\". Ai voie să începi lucrarea în siguranță."},
                    {"title": "Lucrezi", "body": "Comunici prin chat-ul aplicației. Toate mesajele se salvează ca dovadă. NU comunica pe WhatsApp — nu ai protecție în caz de dispută."},
                    {"title": "Finalizezi + ceri confirmare", "body": "Apeși \"Marchează ca finalizat\" în pagina lucrării. Clientul are 7 zile să confirme sau să deschidă dispută."},
                    {"title": "Primești banii", "body": "Dacă clientul confirmă (sau dacă trec 7 zile fără răspuns negativ), banii ajung în portofelul tău PropManage. De acolo îi retragi în cont bancar în 1-3 zile."},
                ]},
                {"type": "callout", "variant": "warn", "title": "NU face niciodată",
                 "body": "Nu cere clientului să plătească pe lângă escrow (\"Lasă cash diferența\"). Asta îți închide contul instant și pierzi acces la viitoare lucrări. Toți banii trec prin platformă, întotdeauna."},
            ],
        },
        {
            "heading": "6. Recenzii — cum primești 5 stele",
            "body": [
                "Recenziile sunt **moneda ta principală** pe platformă. Un specialist cu 4.8★ și 30 recenzii primește 5x mai multe lucrări decât unul cu 5.0★ și 3 recenzii.",
                {"type": "list", "items": [
                    "**Punctualitate** — Cel mai important factor. Întârzieri = -1 stea automat.",
                    "**Curățenie** — La finalul lucrării, lași zona impecabilă. Aspiratorul ăla portabil din mașină e cea mai bună investiție pe care o poți face.",
                    "**Comunicare proactivă** — Update-uri scurte zilnic (\"Azi am terminat tencuielile, mâine începe gletul\"). Clienții stresați devin clienți fericiți.",
                    "**Estimare onestă** — Spune dacă vezi probleme suplimentare ÎNAINTE de a începe, nu după.",
                    "**Mulțumire la final** — Trimite un mesaj scurt: \"Mulțumesc pentru încredere, vă rog să-mi lăsați un feedback dacă a fost ok lucrarea, mă ajută foarte mult.\""
                ]},
                {"type": "callout", "variant": "info", "title": "Ce să faci dacă primești o recenzie nedreaptă",
                 "body": "Răspunde public, calm și echilibrat. NU ataca clientul. Răspunsurile bine scrise la recenzii proaste convertesc 3 din 4 viitori clienți. Dacă recenzia conține minciuni dovedibile, deschide dispută la echipa noastră."},
            ],
        },
        {
            "heading": "7. Dispute — perspectiva specialistului",
            "body": [
                "În 2025, 67% din dispute au fost decise în favoarea clientului. **Cum eviți să fii printre acei 67%:**",
                {"type": "list", "items": [
                    "**Strânge dovezi de la început** — poze înainte/după pentru fiecare etapă. Stochează-le în chat (sunt time-stamped).",
                    "**Cere acceptarea în scris** pentru orice modificare de scope. Mesaj clar: \"Confirmați că adăugăm și schimbarea robinetelor pentru +400 RON?\""
                    " Dacă acceptă, ai dovadă. Dacă refuză, lași robineții.",
                    "**Documentează tot** ce e mai prost decât ai fost informat la sfârșit (zid umed sub gresie, instalație electrică din aluminiu sub tencuială, etc.). În disputa de mediere, asta îți salvează 50%+ din bani.",
                    "**Răspunde rapid la dispute** (în 24h). Specialiștii care răspund în 12h câștigă disputa în 80% din cazuri. Cei care răspund după 48h pierd în 70%.",
                ]},
            ],
        },
        {
            "heading": "8. Plata și retragerea banilor",
            "body": [
                {"type": "list", "items": [
                    "**Wallet PropManage** — banii eliberați din escrow ajung aici instant.",
                    "**Retragere bancară** — \"Retrage\" din pagina Wallet → introduci IBAN → primești în cont în 1-3 zile lucrătoare.",
                    "**Frecvență recomandată** — săptămânal sau bilunar. Nu lăsa mai mult de 10.000 RON în wallet (deși sunt protejați, fluxul tău de cash e mai bun cu retrageri dese).",
                    "**Facturare automată** — la fiecare lucrare finalizată, sistemul generează factură PDF conformă ANAF cu datele tale (PFA / SRL). Le descarci din \"Facturi\" pentru contabilitate.",
                ]},
            ],
        },
        {
            "heading": "9. Best Practices (din top 50 specialiști PropManage)",
            "body": [
                {"type": "list", "items": [
                    "**Activează push notifications**. Lead-urile sub 30 min răspuns primesc 5x rata de acceptare.",
                    "**Răspunde și la cererile pe care nu le iei**. Un \"Mulțumesc, nu pot acum, dar pentru viitor sunt disponibil\" îți crește response_rate (factor în ranking).",
                    "**Cere recenzie după FIECARE lucrare**, chiar și mică. 80% din clienți nu lasă recenzie singuri, doar dacă o ceri.",
                    "**Postează săptămânal în portofoliu**. Nu doar lucrările mari — și cele mici (înlocuit un robinet, schimbat un întrerupător). Arată că lucrezi activ.",
                    "**Refuză lucrările dubioase**. Un client care insistă pe \"fără factură\" sau \"plătesc cash\" e un viitor litigiu garantat.",
                    "**Specializează-te**. Specialiștii care fac DOAR baia (nu \"toate lucrările casnice\") au prețuri 30-40% mai mari și clienți mai relaxați.",
                    "**Trimite poze de progres**. Clientul care primește 1 poză/zi e clientul care lasă 5 stele.",
                ]},
            ],
        },
    ],
    "faq": [
        {"q": "Cât pot câștiga pe lună pe PropManage?", "a": "Specialiștii TOP 10% câștigă **15.000-25.000 RON/lună** (lucrând full-time, cu echipă mică). Median (50% specialiștilor): **4.000-8.000 RON/lună** (part-time + alte canale). Începătorii fără rating: **0-2.000 RON/lună** în primele 3 luni. Depinde 100% de Profile Quality + Response Speed + Geographic Density."},
        {"q": "Cum obțin badge VERIFIED?", "a": "Profil → Documente → upload: CI, certificat fiscal (PFA/SRL activ), polița de răspundere civilă profesională, certificat ANRE (dacă e gaz/electric), diplome/atestate. Echipa noastră validează manual în 24-48h. VERIFIED crește conversia cu 2.5x și reduce comisionul de la 5% la 4%."},
        {"q": "Pot anula o lucrare după ce am acceptat-o?", "a": "Da, dar cu penalități. Anulare în primele 24h: 0 penalty. După 24h, înainte de start: -0.2★ pe profilul tău. După începere: -0.5★ + obligativitate refund integral. Anulare repetitivă (>3 ori în 3 luni) = suspendare cont 30 zile."},
        {"q": "Ce categorii au cea mai mare cerere?", "a": "Top 5 în 2026: **Instalator** (cerere zilnică, 15-20 cereri/zi în București), **Electrician**, **Zugrăveală**, **Mobilă custom (tâmplărie)**, **Service electrocasnice**. Categorii cu marjă mare dar cerere mai mică: HVAC, Design Interior, Restaurări monumente."},
        {"q": "Comisionul de 5% se aplică și la lucrările mici?", "a": "Da, pentru orice tranzacție trecută prin escrow. Minim absolut: 5 RON comision (pentru lucrări sub 100 RON). Pentru lucrări sub 50 RON recomandăm să le treci direct în chat ca \"servicii bonus\" către clienți existenți, fără escrow."},
        {"q": "Pot avea mai mulți colaboratori sub același cont?", "a": "Nu, fiecare specialist are propriul cont. Avantaj: rating-ul tău e protejat de munca proastă a altuia. Dezavantaj: trebuie să-i sub-contractezi separat. Pentru firme cu 5+ angajați, contactează contact@propmanage.ro pentru cont **Business** (multi-seat)."},
        {"q": "Cum mă protejez de clienții care nu plătesc?", "a": "Folosește escrow pentru ORICE lucrare, fără excepție. Banii sunt deja blocați înainte să începi. Dacă clientul refuză să-i alimenteze escrow după ce a acceptat oferta, anulezi automat în 48h și NU pierzi nimic."},
    ],
}

# ============================================================================
# 3) OPERATOR — Echipa internă PropManage (validare Twin, mediere ușoară)
# ============================================================================
OPERATOR_DOC = {
    "slug": "operator",
    "role": "operator",
    "title": "Ghid Complet pentru Operatori (Echipa PropManage)",
    "subtitle": "Validare Digital Twin, gestionare non-conformități, comunicare cu clienții și specialiștii, escaladare către admin.",
    "version": "1.0",
    "updated_at": UPDATED,
    "email_intro": "Bine ai venit în echipa de operatori PropManage. Acest ghid îți arată exact ce ai de făcut zilnic, cum prioritizezi și când escaladezi.",
    "sections": [
        {
            "heading": "1. Rolul tău în platformă",
            "body": [
                "Operatorul este **interfața umană** a PropManage. Tu validezi conținutul care intră în platformă și asiguri că totul respectă standardele. Responsabilități principale:",
                {"type": "list", "items": [
                    "**Validare Digital Twin** — verifici că modelele 3D încărcate de clienți sunt valide, complete, conforme",
                    "**Triere non-conformități** — primești raportări de la specialiști despre probleme și le decizi (accept/respinge/escaladează)",
                    "**Mediere disputelor ușoare** (sub 1.000 RON) — disputele complexe merg direct la admin",
                    "**KYC verification** — verifici documentele specialiștilor care cer badge VERIFIED",
                    "**Onboarding asistat** — primești cereri de help de la specialiști noi în prima săptămână",
                ]},
            ],
        },
        {
            "heading": "2. Workflow zilnic (90 min/zi)",
            "body": [
                {"type": "steps", "items": [
                    {"title": "09:00 — Verifici Morning Briefing", "body": "Te loghezi → vezi câte taskuri ai în queue (twin validations, KYC pending, dispute ușoare)."},
                    {"title": "09:15 — Procesezi KYC pending (prioritate)", "body": "Specialiștii noi așteaptă activarea. Verifici documente, marchezi VERIFIED sau respingi cu motiv clar."},
                    {"title": "09:45 — Validare Twin uploads", "body": "Modele 3D noi în queue. Deschizi fiecare → verifici că .glb se încarcă fără erori → verifici că dimensiunile sunt realiste → verifici că nu există conținut neadecvat."},
                    {"title": "10:30 — Dispute ușoare (< 1000 RON)", "body": "Citești ambele perspective, ceri dovezi dacă lipsesc, decizi. Pentru orice peste 1000 RON sau cu complexitate juridică → escaladare admin."},
                    {"title": "Asincron — răspunzi la mesaje", "body": "Verifici inbox-ul în-app la fiecare 2-3 ore. Răspuns standard în max 24h."},
                ]},
            ],
        },
        {
            "heading": "3. Validare Digital Twin — checklist",
            "body": [
                "Pentru fiecare upload de Twin (`/api/admin/twin-validations`), parcurgi:",
                {"type": "list", "items": [
                    "**Fișierul se încarcă** în viewer-ul 3D fără erori console",
                    "**Suprafața declarată** se potrivește cu cea calculată din model (±10% acceptat)",
                    "**Nu sunt detalii ireale** (ex: scări care duc nicăieri, pereți care se intersectează)",
                    "**Pin-urile inițiale** (dacă există) sunt în locații coerente",
                    "**Plan 2D atașat** (PDF) corespunde cu Twin 3D",
                ]},
                {"type": "callout", "variant": "warn", "title": "Respingere — bune practici",
                 "body": "Dacă respingi, scrie motiv CONCRET și ACȚIONABIL: \"Modelul are 3 pereți care se intersectează la coordonatele (5,2,3) și (5,2,4) — re-export și re-upload, te rog\". NU scrie doar \"Model invalid\"."},
            ],
        },
        {
            "heading": "4. Mediere dispute ușoare",
            "body": [
                "Disputele ușoare (sub 1.000 RON valoare totală) sunt responsabilitatea ta. Pașii:",
                {"type": "steps", "items": [
                    {"title": "Citește chat-ul lucrării", "body": "Toate mesajele dintre client și specialist. Identifică unde a apărut divergența."},
                    {"title": "Verifică dovezile uploadate", "body": "Poze înainte/după, screenshots, video. Ambele părți au 48h să le încarce."},
                    {"title": "Pune întrebări dacă e cazul", "body": "Mesaj în threadul de dispute, ambele părți primesc notificare."},
                    {"title": "Decide", "body": "Una din 4 variante: (a) plată integrală specialist (cerere client neîntemeiată), (b) refund integral client, (c) split 70/30 sau 50/50, (d) ESCALADARE admin (dacă nu poți decide clar)."},
                    {"title": "Documentează decizia", "body": "Scrii rezumat clar al motivării. Apare în istoric pentru audit."},
                ]},
                {"type": "callout", "variant": "info", "title": "Când escaladezi",
                 "body": "**Orice sumă > 1.000 RON**, orice **acuzație de fraudă**, orice **vătămare fizică/proprietate**, orice **dezacord neprodus de tine în 7 zile** → escaladare admin via butonul \"Escalate to Admin\"."},
            ],
        },
        {
            "heading": "5. KYC Verification — checklist documente",
            "body": [
                "Pentru fiecare cerere VERIFIED de la un specialist, verifici:",
                {"type": "list", "items": [
                    "**CI** — valabilă, foto clară, datele se citesc",
                    "**Cert fiscal** sau **certificat ONRC** — firmă activă (verifici pe portal.onrc.ro)",
                    "**Polița răspundere civilă profesională** — valabilă la data verificării",
                    "**Diplome/atestate** specifice categoriei (ANRE pentru gaz/electric, ISCIR pentru centrală termică)",
                    "**Adresa de pe documente** = orașul declarat pe profil (sau o explicație plauzibilă)",
                ]},
                {"type": "h3", "text": "Roșu (respingi imediat)"},
                {"type": "list", "items": [
                    "Documente vizibil editate (font diferit, semnături lipite)",
                    "Firmă în insolvență sau lichidare",
                    "Asigurare expirată",
                    "Diplome dubioase (școli inexistente, format suspect)",
                ]},
            ],
        },
        {
            "heading": "6. Comunicare cu părțile",
            "body": [
                {"type": "h3", "text": "Cu clientul"},
                "Folosești în-app messages. Începi mesajele cu \"Bună ziua, sunt [nume], operator PropManage.\" Răspunzi în max 24h. Ton: profesional, empatic, fără jargon tehnic.",
                {"type": "h3", "text": "Cu specialistul"},
                "La fel ca cu clientul, dar puțin mai direct (specialistul e familiar cu termenii platformei). Nu fii prea blând cu specialiștii care încalcă reguli — escaladări frecvente sunt indicator de cont problematic.",
                {"type": "h3", "text": "Cu admin-ul (escaladare)"},
                "Folosești butonul \"Escalate to Admin\" în pagina disputei/lucrării. Scrii rezumat de **maxim 5 fraze**: (1) ce s-a întâmplat, (2) ce am încercat eu, (3) de ce nu pot decide, (4) recomandarea mea, (5) suma în joc.",
            ],
        },
        {
            "heading": "7. KPI-uri pe care le monitorizezi (la tine în profil)",
            "body": [
                {"type": "list", "items": [
                    "**Twin validations** — target: 10+/zi · current month",
                    "**KYC requests procesate** — target: 5+/zi · turnaround < 48h",
                    "**Dispute decise** — target: 100% sub 7 zile",
                    "**Escalări către admin** — sub 15% din total dispute (sub 15% = bun, peste = ai nevoie de training)",
                    "**Satisfaction score** (feedback de la părți) — target: 4.5+/5",
                ]},
            ],
        },
    ],
    "faq": [
        {"q": "Cum diferă rolul operator de rolul admin?", "a": "Operator = execuție zilnică (validări, dispute ușoare, KYC). Admin = decizii strategice + cazuri complexe + acces la console tehnică (Healthcheck, AI Investigator, Backup). Admin poate face tot ce poate operator, dar nu invers."},
        {"q": "Pot vedea datele financiare ale specialiștilor (cifră afaceri)?", "a": "**Nu**. Operatorii NU au acces la wallets, escrow detalii sau facturi. Doar la chat-uri, dovezi vizuale și meta-info (status, dată, sumă globală fără defalcare). Asta protejează privacy specialiștilor și reduce risc de fraudă internă."},
        {"q": "Ce fac dacă găsesc o problemă tehnică (404, 500)?", "a": "Mergi în AI Investigator → \"Submit Finding\" → completezi: ce făceai, ce ai văzut, ce așteptai. Adăugi screenshot. Admin-ul vede în 5 minute prin auto-monitoring."},
        {"q": "Lucrez weekend-uri?", "a": "Nu obligatoriu, dar răspunsurile clienților au target 24h indiferent de zi. Echipa decide rotativ disponibilitate weekend (toggle în profil → \"Disponibil weekend\")."},
        {"q": "Cum mă protejez juridic dacă decid greșit o dispută?", "a": "Toate deciziile operatorilor sunt **revizuibile** de admin în 30 zile. Logarea automată în `audit_log` arată raționamentul tău. Dacă ai documentat corect motivarea, ești protejat juridic — răspunde compania, nu tu personal."},
    ],
}

# ============================================================================
# 4) ADMIN — Cu acces complet, console tehnice, decizii strategice
# ============================================================================
ADMIN_DOC = {
    "slug": "admin",
    "role": "admin",
    "title": "Ghid Complet pentru Administratori",
    "subtitle": "Autonomy Engine, Twin Orchestrator, Auto-Tune, Sub-Admin RBAC, KYC AI, Cost & ROI, Smoke Tests, Backup, GDPR.",
    "version": "2.0",
    "updated_at": UPDATED,
    "email_intro": "Bine ai venit ca administrator PropManage. Acest ghid acoperă toate uneltele tale și fluxurile zilnice/săptămânale/lunare — inclusiv noul sistem self-driving (Autonomy Engine + Twin Orchestrator).",
    "sections": [
        {
            "heading": "1. Ce poți face ca admin",
            "body": [
                "Admin-ul PropManage are acces TOTAL la platformă. Pe lângă super-admin, există acum și **sub-admini cu scope** (testing, frontend, backend, security, ai, ops) care văd doar feature-urile relevante și au nevoie de aprobare pentru acțiuni distructive.",
                {"type": "list", "items": [
                    "**Self-Healing & Autonomy** — verifici tier-ul (self-driving / autonomous / assisted / manual), apeși Auto-Tune când scorul scade, monitorizezi cron-uri (vezi §2)",
                    "**Twin Orchestrator** — chat AI super-admin pentru întrebări live + executare acțiuni cu confirmare (§3)",
                    "**Monitoring** — verifici Morning Briefing zilnic, Cost & ROI Tracker, Autopilot Activity",
                    "**Sub-Admin RBAC** — adaugi/promovezi sub-admini, aprobi acțiuni junior",
                    "**Mediere complexă** — dispute > 1.000 RON, cazuri cu acuzații serioase",
                    "**KYC AI** — review queue (auto-aprobări AI Vision Claude Sonnet 4.5 cu threshold configurabil)",
                    "**GDPR** — gestionezi DSAR (export/delete), aprobi impersonările",
                    "**Securitate** — review AI Findings, suspendări conturi, blocare IP",
                    "**Configurare platformă** — feature flags, pricing changes, schedules",
                ]},
            ],
        },
        {
            "heading": "2. Autonomy Engine & Self-Healing Platform (NEW v2.0)",
            "body": [
                "PropManage rulează acum în mod **self-driving** — un set de cron-uri + AI keep automatically scor-ul ≥ 90/100 fără intervenție.",
                {"type": "h3", "text": "Autonomy Score (0-100) cu 5 sub-dimensiuni"},
                {"type": "list", "items": [
                    "**Operational** (țintă 95) — auto-matching, lifecycle requests, scheduler health",
                    "**Technical** (țintă 85) — smoke tests, snapshots, release gates",
                    "**Security** (țintă 90) — OAuth, findings critice, GDPR",
                    "**DEV** (țintă 75) — quality gates, QA findings, stabilitate",
                    "**AI** (țintă 80) — findings închise, memorie, knowledge base",
                ]},
                "Tier-uri: ≥90 self-driving · ≥75 autonomous · ≥60 assisted · <60 manual. Vezi `/admin/autonomy`.",
                {"type": "h3", "text": "Butoane în pagina Autonomy"},
                {"type": "list", "items": [
                    "**✨ Auto-Tune to Self-Driving** (recomandat) — orchestrator one-click: seed AI knowledge + repair + concierge + dismiss findings + snapshot. ~5s",
                    "**Boost DEV** (violet) — Release Gate background + dismiss findings stale",
                    "**Boost AI** (cyan) — Seed knowledge base + memorii sintetice",
                    "**Snapshot acum** — forțează un snapshot nou",
                    "**Refresh** — invalidează cache",
                ]},
                {"type": "h3", "text": "Cron-uri self-healing (toate Europe/Bucharest)"},
                {"type": "list", "items": [
                    "Zilnic 03:15 — autonomy snapshot",
                    "Zilnic 03:30 — MongoDB backup (email admin)",
                    "Zilnic 04:15 — autopilot sweep (dismiss findings vechi)",
                    "**Lun 04:00 — Auto-Tune adaptiv** (escalare automată dacă tier ≠ self-driving + email confirmare)",
                    "**Lun 09:30 — Founders' Digest** (email cu KPI-uri 7 zile)",
                    "La 15 min — health ping · La 30 min — smoke test E2E",
                    "Real-time — tier downgrade alerts (push + email super-admini)",
                ]},
                {"type": "callout", "variant": "success", "title": "Tier Downgrade Alerts",
                 "body": "Când tier-ul scade (ex: self-driving → autonomous), super-admini primesc instant push + email. Alertele de test sunt marcate cu badge 🧪 TEST (amber) și ascunse din UI default; bifează \"Arată test\" în panou pentru a le vedea."},
            ],
        },
        {
            "heading": "3. Twin Orchestrator (NEW v2.0) — creierul platformei",
            "body": [
                "Chat AI super-admin la `/admin/twin`. Răspunde la întrebări în română citind live din `autonomy_snapshots`, `autopilot_runs`, `admin_actions_log`, `autonomy_alerts`, AI Health, counts platformă. Powered by Claude Sonnet 4.5.",
                {"type": "h3", "text": "Exemple întrebări (read-only)"},
                {"type": "list", "items": [
                    "„Care e tier-ul curent și de ce?\"",
                    "„Câți admini au făcut acțiuni denied astăzi?\"",
                    "„Ce ar trebui să fac ca scorul DEV să crească?\"",
                    "„A scăzut scorul săptămâna asta?\"",
                ]},
                {"type": "h3", "text": "Twin Action Mode — execută acțiuni cu confirmare"},
                "Când scrii o comandă imperativă (verb + acțiune), Twin propune un buton de confirmare cu token TTL 5min single-use. Acțiuni allowed: `auto_tune`, `send_founder_digest`, `boost_dev`, `take_snapshot`.",
                {"type": "code", "text": "Twin, rulează Auto-Tune acum\nTwin, trimite digest către admin\nTwin, ia un snapshot"},
                {"type": "h3", "text": "Twin Scheduled Actions — natural-language cron"},
                "Twin acceptă programări (recurente sau one-shot). Persistate în `twin_scheduled_actions` + APScheduler dynamic jobs. Max 20 active/user.",
                {"type": "code", "text": "Twin, rulează Auto-Tune în fiecare luni la 06:00\nTwin, trimite digest în fiecare 1 a lunii la 09:00\nTwin, ia un snapshot mâine la 09:00"},
                {"type": "callout", "variant": "info", "title": "Programări active",
                 "body": "Vezi lista jos pe pagina `/admin/twin` cu badge \"recurent\"/\"o dată\" + buton Anulează. Schedules sunt re-hydrated automat după restart backend."},
            ],
        },
        {
            "heading": "4. Cost & ROI Tracker (NEW v2.0)",
            "body": [
                "Card pe `/admin` care arată cât timp & bani salvează Autopilot vs ce ar fi făcut admin-i manual. Default rata 150 RON/h (Romanian admin median, configurabilă prin `?hourly_rate=`).",
                {"type": "h3", "text": "Surse contorizate (per event)"},
                {"type": "list", "items": [
                    "Auto-Tune run × 30 min",
                    "Daily sweep × 10 min",
                    "Cerere auto-asignată AI × 5 min",
                    "QA finding auto-rezolvat × 5 min",
                    "KYC auto-aprobat (AI Vision) × 15 min",
                    "AI top-match notification × 3 min",
                ]},
                "Selector window: 7 / 30 / 90 / 365 zile. Hero KPI-uri: bani salvați, ore salvate, evenimente automate.",
            ],
        },
        {
            "heading": "5. Sub-Admin RBAC (NEW v2.0)",
            "body": [
                "Sub-admini scoped pe un departament: testing, frontend, backend, security, ai, ops. Middleware `middleware_scope.py` enforce SCOPE_MAP pe routes.",
                {"type": "h3", "text": "Cum adaugi un sub-admin"},
                {"type": "steps", "items": [
                    {"title": "Mergi la `/admin/sub-admins`", "body": "Vezi lista existentă + buton \"Adaugă sub-admin\""},
                    {"title": "Setează scope + seniority", "body": "Junior = necesită aprobare super-admin pentru destructive. Senior = poate executa direct"},
                    {"title": "Sub-adminul primește email cu parolă temporară", "body": "Pattern: `{scope}.admin@propmanage.io` / `SubAdmin123!`"},
                ]},
                {"type": "h3", "text": "Aprobări (Junior admin)"},
                "Acțiuni destructive (DELETE, force) ale junior-ilor creează entries în `admin_approvals`. Super-admin aprobă/respinge din `/admin/approvals`.",
                {"type": "h3", "text": "Preview As — vezi platforma ca alt scope"},
                "Super-admin → header X-Preview-Scope=`testing` (ex) → UI ascunde ce nu se vede pentru testing scope. Folosit pentru validare RBAC.",
            ],
        },
        {
            "heading": "6. KYC AI Verification (NEW v2.0)",
            "body": [
                "Specialiștii încarcă ID + selfie. Sistemul rulează automat **Claude Sonnet 4.5 Vision** care returnează JSON cu `match_score` + flag-uri (poor, blur_high, mismatch, suspicious, fake, etc.).",
                {"type": "h3", "text": "Auto-Approve Threshold"},
                "Configurat în `/admin/kyc-queue` cu slider min_score (50-100, default 92) + toggle \"blochează pe flag-uri negative\". Când scor ≥ threshold AND zero flag-uri → user.verified=true automat + push notification.",
                {"type": "h3", "text": "Manual review queue"},
                "`/admin/kyc-queue` → cazurile borderline (scor < threshold sau cu flag-uri). Apeși Approve/Reject + comentariu.",
            ],
        },
        {
            "heading": "7. Morning Briefing — primul lucru dimineața",
            "body": [
                "Te loghezi la propmanage.ro/admin → primul card vizibil este **Morning Briefing** cu 6 tile-uri:",
                {"type": "list", "items": [
                    "**Integrări externe** (Healthcheck) — Mongo, LLM, Email, Stripe, OAuth, VAPID, Admin Emails",
                    "**Smoke Test E2E** — ultimul test E2E pe 4 roluri (client, specialist, operator, admin)",
                    "**Integritate date** — orphan twins, escrow mismatches, missing payments",
                    "**Incidente publice** — câte sunt active pe status page (last 30 zile)",
                    "**AI Findings** — câte findings deschise are AI Investigator",
                    "**Backup DB** — vârsta ultimului backup (< 36h = ok, > 72h = fail)",
                ]},
                {"type": "callout", "variant": "info", "title": "Acțiune zilnică",
                 "body": "Dacă TOATE 6 tiles sunt verzi (ok), nu trebuie să faci nimic — închizi tab-ul. Dacă vezi galben/roșu pe oricare, click pe \"Detalii\" → vezi exact ce s-a întâmplat și acționezi."},
            ],
        },
        {
            "heading": "8. AI Investigator — auditorul tău automat",
            "body": [
                "AI Investigator scanează zilnic codul + logs + DB pentru a detecta probleme. Findings categorizate pe severitate: **high** (acțiune imediată), **warning** (cod review), **low** (improvement suggestion).",
                {"type": "h3", "text": "Cum acționezi pe findings"},
                {"type": "steps", "items": [
                    {"title": "Sortezi pe severitate", "body": "Filtrezi pe \"high\" → vezi toate findings critice deschise."},
                    {"title": "Investighezi", "body": "Click pe finding → vezi: ce, unde (file:line), de ce e problemă, recomandare AI."},
                    {"title": "Acționezi", "body": "Variante: (a) **Resolve** (problemă rezolvată sau nu e problemă reală), (b) **Snooze** (revii peste 30 zile), (c) **Escalate to Dev** (trimiți pe email developer-ului tău)."},
                    {"title": "Documentezi în comentariu", "body": "Scrii ce ai făcut. Aud trail păstrat pentru viitor."},
                ]},
                {"type": "callout", "variant": "success", "title": "Self-Healing acoperă acest pas",
                 "body": "Auto-Tune săptămânal + autopilot daily sweep dismissează findings low/medium vechi automat. Tu intervii doar pe HIGH/CRITICAL."},
            ],
        },
        {
            "heading": "9. Console tehnice — când să le folosești",
            "body": [
                {"type": "h3", "text": "Smoke Test (`/admin/smoke-test`)"},
                "Verifică automat la 30 min că flow-ul E2E funcționează. Dacă pică, primești email instant. Acțiune: vezi în Logs cauza, redirect către dev sau resolve dacă a fost flaky.",

                {"type": "h3", "text": "Healthcheck (`/admin/healthcheck`)"},
                "Pinguiește toate serviciile externe. Dacă Resend/Stripe pică, vezi instant. Acțiune: refresh manual pentru a vedea recovery, sau intervenție direct cu provider-ul.",

                {"type": "h3", "text": "Data Integrity (`/admin/data-integrity`)"},
                "Scanează DB pentru inconsistențe (orphan, mismatches). Rulează lunar manual. Dacă găsește issues, ai opțiunea \"Auto-fix\" pentru cele safe, sau manual review pentru cele complexe.",

                {"type": "h3", "text": "Backup (`/admin/backups`)"},
                "Listă backup-uri locale + buton manual \"Backup acum\". Cron zilnic 03:30 trimite și pe email. Acțiune: nimic, doar verifici că tile-ul Briefing e verde.",

                {"type": "h3", "text": "Audit Log (`/admin/audit-log`)"},
                "Toate acțiunile admin (inclusiv impersonări). Folosit pentru GDPR + securitate internă.",
            ],
        },
        {
            "heading": "10. GDPR Compliance Pack",
            "body": [
                {"type": "list", "items": [
                    "**DSAR Export** — un user cere copia datelor sale. Tu apeși \"Generate Export\" → primește PDF + JSON în 30 zile. Tracking în `dsar_requests`.",
                    "**DSAR Delete** — user cere ștergere cont. 30 zile perioadă de gândire, apoi soft-delete (date pseudonimizate, păstrăm tranzacții financiare 5 ani conform legii)."
                    " Tu confirmi în pagina cererii.",
                    "**Impersonation** — vezi platforma prin ochii unui user. **Logat în `audit_log`**, vizibil clientului în profil. Folosește DOAR pentru debugging/support, nu pentru curiozitate.",
                    "**Consent banner** — gestionat automat. Tu vezi rate de accept în `/admin/gdpr-stats`.",
                ]},
                {"type": "callout", "variant": "warn", "title": "GDPR risc",
                 "body": "Orice impersonare neînregistrată = potențială amendă ANSPDCP până la 20M EUR. Sistemul nostru logează AUTOMAT, dar dacă găsești o bypass, raportează imediat."},
            ],
        },
        {
            "heading": "11. Dispute complexe — cum mediezi",
            "body": [
                "Pentru orice dispută > 1.000 RON sau escaladare de la operator:",
                {"type": "steps", "items": [
                    {"title": "Citește tot threadul + notele operatorului", "body": "Înțelegi context complet. Notele operatorului spun unde a blocat."},
                    {"title": "Verifică dovezi", "body": "Toate pozele, mesajele, log-urile escrow. Caută inconsistențe."},
                    {"title": "Întreabă părțile direct", "body": "Mesaj formal: \"Bună ziua, sunt [nume], admin PropManage. Voi decide cazul vostru. Înainte de asta, vă rog răspundeți la X, Y, Z\"."},
                    {"title": "Decide echitabil", "body": "Nu te grăbi. Cazurile complexe au impact reputațional MARE. Mai bine 5 zile bine decisă decât 1 zi greșit."},
                    {"title": "Comunică decizia", "body": "Mesaj separat fiecăruia. Explicarea motivării. Drept de apel: 7 zile (la un terț neutru — un alt admin)."},
                ]},
            ],
        },
        {
            "heading": "12. Suspendări conturi & escaladări de securitate",
            "body": [
                "Când e ok să suspenzi un cont:",
                {"type": "list", "items": [
                    "**Fraudă dovedită** (documente false, recenzii cumpărate) — suspendare permanentă",
                    "**> 3 dispute pierdute consecutiv** — suspendare 30 zile + review profil",
                    "**Hărțuire/limbaj agresiv** dovedit în chat — suspendare 7 zile prima oară, permanentă a 2-a",
                    "**Tentativă de înconjurare escrow** (\"plătește-mă cash direct\") — suspendare 14 zile + warning",
                    "**Activitate suspectă** (login 50+ țări în 24h) — suspendare automată + cerere verificare 2FA",
                ]},
                {"type": "callout", "variant": "info", "title": "Right to be informed",
                 "body": "Orice suspendare trebuie comunicată user-ului cu (a) motiv concret, (b) durată, (c) drept de apel. Lipsa oricăruia = nulitate juridică."},
            ],
        },
        {
            "heading": "13. Configurare platformă",
            "body": [
                {"type": "list", "items": [
                    "**Feature flags** (`/admin/feature-flags`) — activezi/dezactivezi feature-uri pentru % din useri (A/B testing)",
                    "**Pricing** (`/admin/pricing-config`) — comision, lead fee, prețuri tier-uri",
                    "**Schedules** (`/admin/schedules`) — modifici sau dezactivezi cron jobs (smoke test, backup, briefing)",
                    "**Email templates** (`/admin/email-templates`) — preview + edit dintre cele 30+ template-uri",
                    "**Announcements** (`/admin/announcements`) — banner global vizibil pe site (ex: \"Mentenanță planificată 03:00-04:00\")",
                ]},
            ],
        },
        {
            "heading": "14. Comunicare publică (incidents + newsletter)",
            "body": [
                {"type": "h3", "text": "Incident management"},
                "Când ceva pică (Stripe down, Mongo replication, etc.), creezi un incident: `/admin/incidents` → \"Create new\". Apare instant pe `/status` public. Updates regulare la fiecare 30 min până e \"resolved\".",

                {"type": "h3", "text": "Newsletter & anunțuri"},
                "Pentru anunțuri majore (nou feature, schimbare prețuri), folosești Resend bulk send. Maxim 1 email/lună la toți useri ca să nu fii marcat spam.",
            ],
        },
        {
            "heading": "15. Comenzi rapide & shortcut-uri",
            "body": [
                {"type": "code", "text": "# Login admin\ncurl -c /tmp/cookies.txt -X POST $API_URL/api/auth/login -d '{\"email\":\"admin@propmanage.io\",\"password\":\"$SEED_ADMIN_PASSWORD\"}'\n\n# Status global\ncurl -b /tmp/cookies.txt $API_URL/api/admin/healthcheck/run\n\n# Force backup\ncurl -b /tmp/cookies.txt -X POST $API_URL/api/admin/backups/run\n\n# Auto-Tune one-click (urcă tier-ul la self-driving)\ncurl -b /tmp/cookies.txt -X POST $API_URL/api/admin/autonomy/auto-tune\n\n# Trimite Founders' Digest acum\ncurl -b /tmp/cookies.txt -X POST $API_URL/api/admin/autonomy/founder-digest/send-now\n\n# Snapshot Autonomy\ncurl -b /tmp/cookies.txt -X POST $API_URL/api/admin/autonomy/snapshot\n\n# Twin ask\ncurl -b /tmp/cookies.txt -X POST $API_URL/api/admin/twin/ask -d '{\"question\":\"care e tier-ul?\"}'\n\n# Search docs\ncurl -b /tmp/cookies.txt \"$API_URL/api/admin/docs/admin/search?q=autonomy\""},
                {"type": "h3", "text": "Hotkeys UI"},
                {"type": "list", "items": [
                    "**⌘K / Ctrl+K** în Admin → Docs — search instant",
                    "**ESC** — închide orice modal",
                    "**Shift + ?** — afișează lista de hotkeys (in development)",
                ]},
            ],
        },
        {
            "heading": "16. Cum adaugi un alt admin",
            "body": [
                {"type": "steps", "items": [
                    {"title": "Adaugă email în whitelist", "body": "Editezi `backend/.env` → `ADMIN_WHITELIST=existing@propmanage.io,nou-admin@example.com` → restart backend."},
                    {"title": "Persoana respectivă se înregistrează", "body": "Merge la `/register` și creează cont normal. Sistemul detectează emailul în whitelist și activează rol admin automat."},
                    {"title": "Trimite documentația", "body": "Admin → Docs → Send → introduce emailul lui → bifează \"Include PDF\" → trimite. Va primi instant ghidul Admin v1.0."},
                    {"title": "Adaugă în ADMIN_EMAILS", "body": "Pentru ca să primească și el Morning Briefing + alertele automate, editezi `ADMIN_EMAILS` env (lista CSV)."},
                    {"title": "Activează 2FA", "body": "OBLIGATORIU pentru admini. Profil → Securitate → \"Activează 2FA\" → scanează QR cu Google Authenticator."},
                ]},
            ],
        },
    ],
    "faq": [
        {"q": "Ce e Autonomy Engine și de ce-mi pasă?", "a": "Un sistem care monitorizează 5 sub-scoruri (operational, technical, security, dev, ai) și calculează tier-ul platformei (self-driving / autonomous / assisted / manual). Țintă: ≥90 self-driving. Vezi `/admin/autonomy`."},
        {"q": "Ce face Auto-Tune to Self-Driving?", "a": "În ~5s: seed-ează AI knowledge base, repair decisions, concierge traffic + dismiss QA findings stale + snapshot nou. Idempotent. Rulează automat în fiecare luni 04:00 (cron) și manual din pagină."},
        {"q": "Cum vorbesc cu Twin?", "a": "Mergi la `/admin/twin`. Întrebări READ-ONLY răspunde direct. Pentru comenzi (\"Twin, rulează Auto-Tune\") apare buton de confirmare cu token 5min. Pentru programări (\"...în fiecare luni la 06:00\") se adaugă la `twin_scheduled_actions`."},
        {"q": "Cum schimb threshold KYC auto-approve?", "a": "`/admin/kyc-queue` → buton settings → slider min_score (50-100). Recomand 92. Combinat cu toggle „blochează pe flag-uri negative\"."},
        {"q": "Cum verific dacă un admin nou primește emailurile automate?", "a": "Verifică `ADMIN_EMAILS` în `backend/.env`. Apoi în admin panel apasă \"Test email\" pe Morning Briefing → toți admins primesc email. Dacă unul nu primește, verifică spam folder + că emailul e corect scris (case-insensitive)."},
        {"q": "Ce fac dacă uit parola admin?", "a": "Reset normal prin email (la fel ca user). Dacă pierzi accesul la emailul admin (catastrofă), poți folosi SSH pe server → rulezi script direct pe DB: `python3 -c \"...\"` pentru a seta o parolă nouă bcrypt. Detalii în `backend/scripts/admin_password_reset.py`. Parolele admin curente sunt în `/app/memory/test_credentials.md`."},
        {"q": "Pot avea 2 admini conectați simultan?", "a": "Da, nelimitat. Toate acțiunile sunt logate cu user_id în audit_log. Singurul caz în care apar conflicte: dacă ambii editează același user simultan — al doilea primește eroare \"Resource modified, please refresh\"."},
        {"q": "Cum fac rollback la o versiune anterioară a platformei?", "a": "Folosește butonul **Rollback** din Emergent UI (este GRATIS, nu costă credite). NU rula `git reset` manual. Rollback restaurează cod + DB la un checkpoint anterior."},
        {"q": "Care e SLA-ul meu ca admin?", "a": "Pentru alerte HIGH severity (smoke test fail, Stripe down): răspuns în 30 min. Pentru WARNING: răspuns în 4h. Pentru INFO: răspuns în 48h. Pentru cereri de la useri: răspuns în 24h. Self-Healing acoperă LOW automat."},
        {"q": "Cum monitorizez sănătatea platformei când sunt în vacanță?", "a": "1) Founders' Digest săptămânal îl primești pe email (Luni 09:30). 2) Tier downgrade alerts vin instant push + email. 3) Auto-Tune adaptiv (Luni 04:00) repară automat dacă tier-ul scade. Practic, platforma se autorepară fără tine — verifici emailul la întoarcere."},
        {"q": "Ce sunt alertele cu badge 🧪 TEST?", "a": "Alerte sintetice generate când cineva apasă „Trimite test alert\" pentru a verifica că push + email funcționează. Sunt ascunse din UI default; bifează „Arată test\" în panou pentru a le vedea. NU înseamnă că platforma chiar a căzut."},
        {"q": "Cum anulez o programare Twin?", "a": "`/admin/twin` → panou „Programări active\" jos → buton „Anulează\" pe row. Status devine `cancelled` în DB + jobul e removed din APScheduler."},
        {"q": "Pot oprii rapoartele automate pe email?", "a": "Da, dezactivezi temporar din `/admin/schedules`. Toggle pe \"morning_briefing_digest\", \"daily_mongodb_backup\", \"weekly_dev_velocity\", \"founder_digest_weekly\". NU recomandăm să le ții oprite > 7 zile."},
    ],
}

# ============================================================================
# 5) QA / Manual Testing Playbook
# ============================================================================
QA_DOC = {
    "slug": "qa-testing",
    "role": "qa",
    "title": "Manual Testing Playbook PropManage",
    "subtitle": "100+ scenarii de testare end-to-end, organizate pe rol și prioritate. Pentru echipa QA internă, înainte de fiecare release.",
    "version": "1.0",
    "updated_at": UPDATED,
    "email_intro": "Acesta este playbook-ul oficial QA PropManage. Conține toate testele manuale obligatorii înainte de fiecare release în producție.",
    "sections": [
        {
            "heading": "1. Cum folosești acest playbook",
            "body": [
                "Înainte de fiecare deploy major în producție, parcurgi TOATE testele marcate **P0** (must-pass) și **P1** (should-pass). Testele **P2** sunt opționale dar recomandate lunar.",
                {"type": "list", "items": [
                    "**P0 (must-pass)** — blocant pentru release. Dacă un P0 pică, NU se face deploy.",
                    "**P1 (should-pass)** — non-blocant, dar dacă > 3 pică, escaladare la admin.",
                    "**P2 (nice-to-have)** — verificare lunară.",
                ]},
                {"type": "callout", "variant": "info", "title": "Format raport",
                 "body": "După fiecare sesiune QA, completezi un raport simplu: data, versiune testată, P0 fail, P1 fail, observații. Salvezi în Drive/Notion + trimiți pe email admin."},
                {"type": "h3", "text": "Convenții"},
                {"type": "list", "items": [
                    "**Test cu \"variațiuni\"** — testează cu Romanian diacritics (ăâîșț), spații extra, copy-paste, emoji, caractere speciale ($%&\"'<>), texte foarte lungi, texte goale, doar spații.",
                    "**Test pe device-uri** — Chrome desktop + iOS Safari + Android Chrome. Min 3 device-uri/test.",
                    "**Test pe conexiune slabă** — Chrome DevTools → Network → \"Slow 3G\" pentru flow-uri critice.",
                ]},
            ],
        },
        {
            "heading": "2. CLIENT — 30 scenarii test",
            "body": [
                {"type": "h3", "text": "Onboarding (P0)"},
                {"type": "list", "items": [
                    "**C-01** Înregistrare cu email nou + parolă validă → verifică inbox primește welcome email + ghid Client v1.0 ca PDF atașat",
                    "**C-02** Înregistrare cu email deja existent → mesaj clar \"Acest email există deja, vrei să te conectezi?\"",
                    "**C-03** Înregistrare cu parolă < 8 caractere → mesaj eroar specific",
                    "**C-04** Înregistrare cu nume conținând diacritice (Ăăâîșț) → numele se salvează corect",
                    "**C-05** Login cu Google OAuth → cont nou creat automat + ghid trimis pe email",
                    "**C-06** Reset parolă: cere → primește email → click link → setează parolă nouă → login funcționează",
                    "**C-07** Reset parolă: link expirat (>60 min) → eroare \"Link expirat, cere unul nou\"",
                    "**C-08** Login cu 10 încercări greșite → cont temporar suspendat 15 min cu mesaj clar",
                ]},
                {"type": "h3", "text": "Proprietate + Cerere (P0)"},
                {"type": "list", "items": [
                    "**C-09** Adaugă proprietate cu toate câmpurile completate → apare în listă",
                    "**C-10** Adaugă proprietate fără adresă → eroare validare specifică",
                    "**C-11** Postează cerere cu poze (3 imagini) → cererea apare în listă cu poze vizibile",
                    "**C-12** Postează cerere cu poză > 10MB → eroare \"Imagine prea mare\"",
                    "**C-13** Postează cerere cu descrieri foarte lungi (5000 caractere) → se salvează complet",
                    "**C-14** Postează cerere fără categorie → forțează selecție",
                    "**C-15** Anulează cerere postată → status \"Anulată\", specialiști notificați",
                ]},
                {"type": "h3", "text": "Escrow + Plăți (P0)"},
                {"type": "list", "items": [
                    "**C-16** Acceptă ofertă → buton \"Alimentează Escrow\" vizibil",
                    "**C-17** Plată cu card test Stripe (4242 4242 4242 4242) → escrow status \"Active\"",
                    "**C-18** Plată cu card refuzat (4000 0000 0000 0002) → eroare specifică + retry",
                    "**C-19** Plată cu 3D Secure necesar → flow se completează corect",
                    "**C-20** Confirmă finalizare lucrare → escrow eliberat, status \"Closed\", review form apare",
                ]},
                {"type": "h3", "text": "Dispute + Garanție (P1)"},
                {"type": "list", "items": [
                    "**C-21** Deschide dispută cu poze (5 imagini) + descriere → status \"In mediation\"",
                    "**C-22** Adaugă răspuns în threadul de dispută → specialistul primește notificare",
                    "**C-23** Cere remediere în perioada de garanție (12 luni) → specialistul primește notificare",
                ]},
                {"type": "h3", "text": "Digital Twin (P1 — doar dacă e premium)"},
                {"type": "list", "items": [
                    "**C-24** Upload .glb 5MB → modelul se încarcă în viewer 3D fără erori",
                    "**C-25** Upload .glb 100MB → mesaj \"Fișier prea mare, max 50MB\"",
                    "**C-26** Adaugă pin pe model → coordonate salvate, vizibil la refresh",
                    "**C-27** Aprobă raport tokenizat (fără login) → status raport \"Approved\"",
                ]},
                {"type": "h3", "text": "Edge cases (P2)"},
                {"type": "list", "items": [
                    "**C-28** Logout din toate tab-urile deschise → toate sesiunile pică",
                    "**C-29** Ștergere cont (GDPR) → flow 30 zile delay, opțiune cancel",
                    "**C-30** Multi-language fallback (browser EN) → toate textele rămân în RO",
                ]},
            ],
        },
        {
            "heading": "3. SPECIALIST — 25 scenarii test",
            "body": [
                {"type": "h3", "text": "Profil & Onboarding (P0)"},
                {"type": "list", "items": [
                    "**S-01** Înregistrare ca specialist → primește ghid Specialist v1.0 pe email",
                    "**S-02** Upload documente KYC (CI + cert fiscal + asigurare) → status \"Pending verification\"",
                    "**S-03** După aprobare manuală operator → badge VERIFIED apare pe profil",
                    "**S-04** Upload poze portofoliu (10 imagini) → toate vizibile, comprimate corect",
                    "**S-05** Setează zone de acoperire (5 sectoare București) → primesc lead-uri doar din ele",
                    "**S-06** Setează specialitate primară + 2 secundare → apar corect pe profil public",
                ]},
                {"type": "h3", "text": "Lead Capture (P0)"},
                {"type": "list", "items": [
                    "**S-07** Apar lead-uri noi în categoria mea (instalator) → notificare push + email",
                    "**S-08** Nu apar lead-uri din categorii ne-setate (ex: HVAC dacă sunt instalator) → corect filtrate",
                    "**S-09** Trimite ofertă cu preț + descriere → apare la client în 1 secundă",
                    "**S-10** Nu pot trimite > 1 ofertă la aceeași cerere → enforce",
                    "**S-11** Plătește Lead Fee 45 RON → primește numărul de telefon al clientului",
                ]},
                {"type": "h3", "text": "Lucrare activă (P0)"},
                {"type": "list", "items": [
                    "**S-12** Ofertă acceptată + escrow alimentat → primesc notificare \"Banii sunt blocați, începe lucrarea\"",
                    "**S-13** Trimit poze de progres în chat → se afișează la client",
                    "**S-14** Marchez ca finalizat → client primește 7 zile de inspecție",
                    "**S-15** Client confirmă → banii apar în wallet în max 60 min",
                    "**S-16** Client NU confirmă în 7 zile → auto-release la zi 8",
                ]},
                {"type": "h3", "text": "Plăți și Wallet (P0)"},
                {"type": "list", "items": [
                    "**S-17** Wallet arată balanță corectă după 3 lucrări consecutive",
                    "**S-18** Retragere bancară (IBAN valid) → status \"Processing\", funds în 1-3 zile",
                    "**S-19** Retragere cu IBAN invalid → eroare validare",
                    "**S-20** Factură PDF generată automat per lucrare → conformă ANAF (CUI, TVA dacă aplicabil)",
                ]},
                {"type": "h3", "text": "Dispute & recenzii (P1)"},
                {"type": "list", "items": [
                    "**S-21** Răspund la disputa client în 24h → escrow rămâne înghețat",
                    "**S-22** Răspund la o recenzie negativă public → răspunsul apare pe profil",
                    "**S-23** Cer remediere de la client (cazuri rare) → trigger workflow special",
                ]},
                {"type": "h3", "text": "Edge cases (P2)"},
                {"type": "list", "items": [
                    "**S-24** Anulare cu 24h înainte → fără penalty",
                    "**S-25** Anulare la mijlocul lucrării → -0.5★ + refund obligatoriu",
                ]},
            ],
        },
        {
            "heading": "4. OPERATOR — 15 scenarii test",
            "body": [
                {"type": "list", "items": [
                    "**O-01** Login ca operator → vede doar tab-urile operator (NU console tehnice admin)",
                    "**O-02** Listează KYC pending → cele mai vechi sus",
                    "**O-03** Aprobă KYC valid → user primește badge VERIFIED + email confirmare",
                    "**O-04** Respinge KYC cu motiv → user primește email cu motivul",
                    "**O-05** Listează Twin pending → toate cu preview model 3D",
                    "**O-06** Aprobă Twin valid → status \"Approved\", apare la client",
                    "**O-07** Respinge Twin cu motiv detaliat → notificare client",
                    "**O-08** Citește dispută < 1000 RON → poate decide",
                    "**O-09** Decide dispută \"Refund client\" → escrow returnează banii pe card",
                    "**O-10** Decide dispută \"Split 70/30\" → escrow împarte corect",
                    "**O-11** Decide dispută \"Pay specialist\" → escrow eliberează către specialist",
                    "**O-12** Escaladează dispută complexă > 1000 RON → admin primește notificare",
                    "**O-13** NU poate accesa /admin/backups, /admin/healthcheck (forbidden) → 403",
                    "**O-14** Caută user pe email → găsește, dar fără date financiare",
                    "**O-15** Logout → sesiune închisă, redirect login",
                ]},
            ],
        },
        {
            "heading": "5. ADMIN — 25 scenarii test",
            "body": [
                {"type": "h3", "text": "Monitoring & Dashboards (P0)"},
                {"type": "list", "items": [
                    "**A-01** Login admin → Morning Briefing apare cu 6 tiles populate",
                    "**A-02** Click \"Test email\" → primesc email de briefing în max 30 secunde",
                    "**A-03** Click \"Raport săptămânal\" → primesc Dev Velocity în max 60 secunde",
                    "**A-04** Healthcheck → toate 7 servicii afișate cu status",
                    "**A-05** Smoke test history → ultimele 50 runs vizibile",
                ]},
                {"type": "h3", "text": "AI Investigator (P0)"},
                {"type": "list", "items": [
                    "**A-06** Listează findings open → sortate pe severitate desc",
                    "**A-07** Marchez finding ca \"Resolved\" + comentariu → audit log",
                    "**A-08** Snooze finding 30 zile → dispare temporar, revine după",
                ]},
                {"type": "h3", "text": "Backup (P0)"},
                {"type": "list", "items": [
                    "**A-09** Click \"Backup acum\" → fișier nou apare în listă în 5 secunde",
                    "**A-10** Download backup .tar.gz → arhivă validă cu MANIFEST + collections/*.json",
                    "**A-11** Email cu backup ajunge în inbox cu PDF attachment ≤15MB",
                ]},
                {"type": "h3", "text": "Documentație & Training (P1)"},
                {"type": "list", "items": [
                    "**A-12** Listează 6 docs (Client, Specialist, Operator, Admin, QA, Architecture)",
                    "**A-13** Preview Client doc → renderează toate secțiunile + FAQ + animații",
                    "**A-14** Download Client PDF → format A4 cu brand, sectiuni clare",
                    "**A-15** Copy Markdown to clipboard → paste în Notion arată identic",
                    "**A-16** Trimite doc la 1 email custom → ajunge cu PDF + link tokenizat",
                    "**A-17** Bulk send la rol \"specialist\" verified_only → max 500 destinatari",
                    "**A-18** Cmd+K → search \"escrow\" → 10+ rezultate, click pe oricare deschide preview",
                    "**A-19** Link tokenizat /help/{token} fără login → vede doc complet",
                    "**A-20** Link tokenizat expirat (>30 zile) → eroare friendly",
                ]},
                {"type": "h3", "text": "Dispute complexe + GDPR (P1)"},
                {"type": "list", "items": [
                    "**A-21** Decide dispută > 1000 RON → escrow se ajustează corect",
                    "**A-22** Generează DSAR export pentru un user → PDF cu toate datele",
                    "**A-23** Impersonate user → logat în audit_log + banner vizibil",
                    "**A-24** Suspendă cont cu motiv → user primește email + nu se mai poate loga",
                ]},
                {"type": "h3", "text": "Edge cases (P2)"},
                {"type": "list", "items": [
                    "**A-25** Rollback platformă din UI Emergent → recovery complet în 5 min",
                ]},
            ],
        },
        {
            "heading": "6. PUBLIC (no auth) — 10 scenarii test",
            "body": [
                {"type": "list", "items": [
                    "**P-01** Landing page se încarcă < 3 sec (Lighthouse mobile)",
                    "**P-02** `/marketplace` listează specialiști, paginate, filter pe categorie funcționează",
                    "**P-03** `/marketplace/electrician-bucuresti` arată DOAR electricieni din București (filter automat)",
                    "**P-04** `/specialists/{id}` profil public încărcă fără login",
                    "**P-05** `/ghiduri` listează 6 articole",
                    "**P-06** `/ghiduri/cost-renovare-apartament-2-camere` se încarcă cu FAQ + JSON-LD",
                    "**P-07** `/status` arată healthcheck live + incidents",
                    "**P-08** `/api/public/sitemap.xml` returnează 229 URL-uri",
                    "**P-09** robots.txt blochează /admin/*",
                    "**P-10** Cookie consent banner apare la prima vizită",
                ]},
            ],
        },
        {
            "heading": "7. Sesiune QA — checklist final",
            "body": [
                "După parcurgerea tuturor testelor, completează raportul:",
                {"type": "code", "text": "Raport QA — [DATA]\nVersiune testată: [VERSION_SHA]\nTester: [NUME]\n\n## Rezultate\n- P0 PASS: X/Y  ❌ FAIL: [list]\n- P1 PASS: X/Y  ❌ FAIL: [list]\n- P2 PASS: X/Y  ❌ FAIL: [list]\n\n## Observații\n[Free text — comportamente ciudate, propuneri îmbunătățire]\n\n## Recomandare\n[ ] DEPLOY APPROVED (toate P0 PASS)\n[ ] DEPLOY BLOCKED (motiv: ...)"},
                "Trimite raportul pe email la admin@propmanage.io + arhivează în Drive.",
            ],
        },
    ],
    "faq": [
        {"q": "Cât durează o sesiune QA completă?", "a": "Pentru toate 105 teste P0+P1+P2: aproximativ 4-6 ore pentru un tester experimentat. Doar P0 (must-pass): 2-3 ore. Recomandăm să distribui pe 2 zile pentru a evita oboseala (greșeli de detecție)."},
        {"q": "Pot automatiza o parte din teste?", "a": "Da, ~60% pot fi acoperite cu Playwright/Cypress. Toate P0 din secțiunea Public + 70% din Client + 50% din Admin. Restul (Operator dispute, KYC manual, Twin upload) sunt manual din cauza componentei vizuale."},
        {"q": "Ce fac dacă un test e ambiguu?", "a": "Marchezi ca \"INCONCLUSIVE\" + descrii observația. Admin decide dacă e bug sau spec neclar. NU marca \"PASS\" la nesigur."},
        {"q": "Cum testez pe iOS Safari fără Mac?", "a": "Folosește BrowserStack ($29/lună) sau Sauce Labs ($39/lună) pentru remote testing. Pentru bugete mici: Emulator Safari Tehnic Preview pe Linux (limitat dar gratis)."},
        {"q": "Câte teste trebuie să adaug pe lună?", "a": "1-2 teste noi per feature nou release-uit. NU adăuga teste pentru fiecare bug fix (faci regresie pe testele existente). Țintă: <130 total teste până la finalul anului (mentenanță sustenabilă)."},
    ],
}


# ============================================================================
# 6) ARCHITECTURE — Technical reference (Frontend + Backend + Infrastructure)
# ============================================================================
ARCHITECTURE_DOC = {
    "slug": "architecture",
    "role": "admin",
    "title": "Arhitectură Platformă — Referință Tehnică",
    "subtitle": "Documentație Frontend + Backend + Infrastructure + Securitate. Pentru developeri, admini tehnici și auditori.",
    "version": "1.0",
    "updated_at": UPDATED,
    "email_intro": "Acesta este documentul tehnic oficial al platformei PropManage — arhitectură, stack, convenții, integrări.",
    "sections": [
        {
            "heading": "1. Stack-ul tehnologic",
            "body": [
                {"type": "list", "items": [
                    "**Frontend**: React 19 + React Router 7 + Tailwind CSS + shadcn/ui + Framer Motion + axios",
                    "**Backend**: FastAPI (Python 3.11) + Motor (MongoDB async driver) + APScheduler + reportlab",
                    "**Database**: MongoDB 7 (single replica set, segregated escrow collection)",
                    "**Auth**: JWT (HS256) cu refresh tokens + Google OAuth (Emergent-managed) + cookie SameSite=None;Secure pentru cross-domain",
                    "**LLM**: Claude Sonnet 4.5 via Emergent Universal Key (emergentintegrations library)",
                    "**Payments**: Stripe (test key în preview, requires sk_live_... în producție)",
                    "**Email**: Resend (HTML + atașamente PDF/tar.gz)",
                    "**Hosting**: Emergent Kubernetes (preview + custom domain `propmanage.ro`)",
                    "**Push**: VAPID Web Push (browsers desktop + mobile)",
                ]},
                {"type": "callout", "variant": "info", "title": "Stack-ul real (verificat)",
                 "body": "Versiunile exacte sunt în `frontend/package.json` și `backend/requirements.txt`. Nu rescrie aceste fișiere — folosește `yarn add` și `pip freeze`."},
            ],
        },
        {
            "heading": "2. Structura proiectului (/app)",
            "body": [
                {"type": "code", "text": "/app/\n├── backend/\n│   ├── server.py            # FastAPI app + lifecycle + scheduler wiring\n│   ├── db.py                # Motor client (singleton)\n│   ├── deps.py              # require_role, auth dependencies\n│   ├── models.py            # Pydantic + PyObjectId base\n│   ├── auth.py              # JWT + password hashing + OAuth\n│   ├── services.py          # send_email + VAPID + shared helpers\n│   ├── email_service.py     # Resend integration + branded layout\n│   ├── docs_content.py      # Knowledge Base content (this lives here!)\n│   ├── docs_service.py      # PDF render + tokenized share\n│   ├── docs_search.py       # Markdown export + FT search\n│   ├── backup_service.py    # MongoDB daily backup → email\n│   ├── admin_briefing_digest.py  # Morning Briefing aggregator + cron\n│   ├── seo_slugs.py         # SEO landing-page slug maps\n│   ├── routes/              # All API endpoints (~30 routers)\n│   │   ├── auth.py, marketplace.py, public.py\n│   │   ├── escrow.py, disputes.py, twin.py\n│   │   ├── admin_*.py       # 15+ admin consoles\n│   │   ├── docs_routes.py   # /admin/docs/* + /help/{token}\n│   │   ├── admin_smoketest.py, admin_healthcheck.py\n│   │   ├── admin_data_integrity.py, admin_backups.py\n│   │   └── incidents.py     # Public status page\n│   └── requirements.txt\n│\n├── frontend/\n│   ├── src/\n│   │   ├── App.js           # Router + global providers\n│   │   ├── auth.jsx         # useAuth() + AuthProvider\n│   │   ├── hooks/useSEO.js  # Dynamic <head> per route\n│   │   ├── utils/seoSlugs.js\n│   │   ├── components/\n│   │   │   ├── ui/          # shadcn/ui primitives\n│   │   │   ├── DocViewer.jsx  # Shared doc renderer\n│   │   │   └── ... (~60 components)\n│   │   ├── pages/\n│   │   │   ├── Dashboards.jsx, Marketplace.jsx\n│   │   │   ├── MarketplaceLanding.jsx  # /marketplace/:slug SEO\n│   │   │   ├── GhiduriIndex.jsx, GhidPage.jsx  # blog\n│   │   │   ├── HelpPage.jsx  # /help/:token (public docs)\n│   │   │   └── admin/        # 20+ admin panels\n│   │   │       ├── AdminConsole.jsx  # router\n│   │   │       ├── AdminLayoutMetronic.jsx  # sidebar + topbar\n│   │   │       ├── AdminDocs.jsx  # docs management\n│   │   │       ├── MorningBriefing.jsx\n│   │   │       └── ...\n│   │   ├── data/ghiduri.js  # blog articles\n│   │   └── index.css        # Tailwind + custom\n│   └── package.json\n│\n└── memory/\n    ├── PRD.md               # Product spec + changelog\n    └── test_credentials.md  # Test accounts"},
            ],
        },
        {
            "heading": "3. Backend — convenții API",
            "body": [
                {"type": "list", "items": [
                    "**Toate rutele backend trebuie prefixate cu `/api`** (Kubernetes ingress routează `/api/*` → port 8001).",
                    "**Auth dependency**: `Depends(require_role(\"admin\"))` sau `require_role(\"client\")`. Multi-role: `require_any_role(\"admin\", \"operator\")`.",
                    "**Env vars**: doar prin `os.environ.get(\"KEY\")` — fără default values (fail fast la deploy).",
                    "**MongoDB**: NU returna documente raw. Folosește `BaseDocument.from_mongo(doc)` / `instance.to_mongo()`. ObjectId → `PyObjectId` annotated type.",
                    "**Datetime**: `datetime.now(timezone.utc)`, NEVER `datetime.utcnow()`.",
                    "**Erori**: `raise HTTPException(status_code, \"Message in Romanian\")`. Mesajele user-facing sunt în RO.",
                    "**Logging**: `logging.getLogger(\"propmanage.<module>\")`. Nu folosi `print()`.",
                    "**Async**: toate handler-ele FastAPI sunt `async def`. I/O folosește `await` (Motor, httpx).",
                    "**Background jobs**: APScheduler (Bucharest TZ). Toate joburile au try/except wrapping — never raise.",
                ]},
                {"type": "h3", "text": "Schedulers active"},
                {"type": "list", "items": [
                    "`smoke_test_monitor` — la fiecare 30 min, testează flow E2E multi-rol, alertează la FAIL",
                    "`morning_briefing_digest` — zilnic 09:00, email digest dacă overall != ok",
                    "`daily_mongodb_backup` — zilnic 03:30, backup tar.gz → email admini cu PDF attached",
                ]},
            ],
        },
        {
            "heading": "4. Frontend — convenții React",
            "body": [
                {"type": "list", "items": [
                    "**Routing**: React Router 7 cu `<Routes>` și `<Route>` în `App.js`. Public routes (marketplace, ghiduri, help) NU au require-auth wrapper.",
                    "**State global**: `useAuth()` din `auth.jsx`. State local: `useState`. Cross-component: `window.dispatchEvent(new CustomEvent('propmanage:...'))`.",
                    "**API calls**: `axios.get(`${API}/admin/...`)` cu cookies automate (`withCredentials=true` global). `API = ${REACT_APP_BACKEND_URL}/api`.",
                    "**SEO**: `useSEO({title, description, canonical, jsonLd, noindex})` din `hooks/useSEO.js`. Setează `<head>` dinamic.",
                    "**Data test IDs**: TOATE elementele interactive au `data-testid=\"kebab-case-name\"`.",
                    "**UI primitives**: doar din `components/ui/` (shadcn). NU instala alte component libraries.",
                    "**Toasts**: `import { toast } from \"sonner\"; toast.success/error(...)`.",
                    "**Animations**: Framer Motion pentru transitions. Tailwind animate classes pentru CSS. Lottie via CDN lazy load.",
                    "**Componente**: <50 linii ideal. Export named pentru componente, default pentru pagini.",
                ]},
                {"type": "h3", "text": "Pattern: Admin panel nou"},
                "Adaugi în `AdminLayoutMetronic.jsx` la `MENU_SECTIONS` un item, în `AdminConsole.jsx` mapezi `active === \"newtab\"` la componenta ta, creezi `pages/admin/AdminNew.jsx` care exportă `AdminNew` și folosește `<AdminCard>` wrapper.",
            ],
        },
        {
            "heading": "5. Database — colecții MongoDB",
            "body": [
                {"type": "h3", "text": "Core entities"},
                {"type": "list", "items": [
                    "**users** — `{role, email, password_hash, name, phone, verified, tier, rating, reviews_count, coverage_zones, service_categories, deleted, created_at}`. Index unique pe `email`.",
                    "**properties** — proprietățile clienților (`owner_id, address, city, type, area_sqm`)",
                    "**requests** — cererile postate (`client_id, category, description, photos, urgency, status`)",
                    "**proposals** — ofertele specialiștilor pe cereri",
                    "**jobs** — lucrările active (status: pending|in_progress|completed|disputed|refunded)",
                    "**escrow** — tranzacțiile cu stare bani (segregated account, Stripe payment intent)",
                    "**disputes** — `{job_id, opened_by, reason, evidence_urls, resolution, mediator_id}`",
                    "**reviews** — `{job_id, author_id, target_id, rating, text, editable_until}`",
                ]},
                {"type": "h3", "text": "Digital Twin + Operational"},
                {"type": "list", "items": [
                    "**twins**, **twin_pins**, **twin_reports** — modulul 3D",
                    "**smoke_test_runs**, **data_integrity_runs**, **backup_runs** — monitoring",
                    "**incidents** — public status page",
                    "**admin_ai_findings** — AI Investigator",
                    "**docs_share_tokens**, **docs_send_events** — Knowledge Base",
                    "**audit_log** — GDPR compliance",
                ]},
                {"type": "callout", "variant": "warn", "title": "MongoDB rules",
                 "body": "Nu adăuga câmpuri direct din endpoint fără validare. Folosește Pydantic models. ObjectId NU e JSON-serializable raw — folosește `PyObjectId` + `BaseDocument`."},
            ],
        },
        {
            "heading": "6. Integrări externe",
            "body": [
                {"type": "list", "items": [
                    "**Resend** (email) — `RESEND_API_KEY`. Tranzacționale + digest-uri admin + docs sending. Limită attachment ~20MB (cap intern 15MB).",
                    "**Stripe** (plăți) — `STRIPE_API_KEY`. Test în preview, live în prod când `sk_live_*` setat. Plăți prin escrow segregat.",
                    "**Emergent LLM Key** (Claude Sonnet 4.5) — `EMERGENT_LLM_KEY`. AI Concierge + AI Investigator + Smart Match.",
                    "**Google OAuth** (Emergent-managed) — `GOOGLE_OAUTH_*`. Redirect → `/auth/google/callback` → JWT.",
                    "**VAPID Web Push** — `VAPID_PUBLIC_KEY` + `VAPID_PRIVATE_KEY`. Push browser.",
                ]},
            ],
        },
        {
            "heading": "7. Securitate",
            "body": [
                {"type": "list", "items": [
                    "**Cookie auth**: `HttpOnly + Secure + SameSite=None`. Refresh rotation la 12h.",
                    "**Password**: bcrypt cost 12. Reset tokens 60 min, one-time use.",
                    "**Rate limiting**: login 8/min per IP. Lockout 15 min după 10 fail consecutive.",
                    "**2FA**: TOTP (Google Authenticator) opțional general, obligatoriu admin.",
                    "**GDPR**: consent banner, DSAR endpoints, impersonation log, audit complet.",
                    "**Path traversal**: backup downloads validează prefix + safe chars.",
                    "**Prompt injection**: AI Concierge guard input + output filtering.",
                    "**Disallow paths**: `/admin/*`, `/api/admin/*`, callbacks blocate în robots.txt.",
                ]},
            ],
        },
        {
            "heading": "8. Environment & Deploy",
            "body": [
                {"type": "h3", "text": "Env vars critice"},
                {"type": "list", "items": [
                    "**Backend** (`/app/backend/.env`): `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, `RESEND_API_KEY`, `STRIPE_API_KEY`, `EMERGENT_LLM_KEY`, `GOOGLE_OAUTH_*`, `VAPID_*`, `ADMIN_EMAILS`, `APP_PUBLIC_URL`, `SENDER_EMAIL`",
                    "**Frontend** (`/app/frontend/.env`): `REACT_APP_BACKEND_URL`",
                ]},
                {"type": "h3", "text": "Restart servicii"},
                {"type": "code", "text": "sudo supervisorctl restart backend\nsudo supervisorctl restart frontend\n# Hot reload activ — restart doar pentru .env/dependency installs"},
                {"type": "h3", "text": "Logs"},
                {"type": "code", "text": "tail -n 100 /var/log/supervisor/backend.err.log"},
                {"type": "callout", "variant": "warn", "title": "Producție vs Preview",
                 "body": "Variabilele env din preview sunt SEPARATE de producție. `RESEND_API_KEY`, `STRIPE_API_KEY`, `JWT_SECRET` se setează în Emergent Deployment Secrets, nu în `.env` din repo."},
            ],
        },
        {
            "heading": "9. SEO & Marketing",
            "body": [
                {"type": "list", "items": [
                    "**Sitemap dinamic**: `GET /api/public/sitemap.xml` → 229 URL-uri (statice + ghiduri + 198 city landings + verified specialists).",
                    "**robots.txt**: sitemap link + Disallow paths private.",
                    "**JSON-LD global**: Organization + WebSite + Service în `index.html`.",
                    "**JSON-LD per pagină**: Article/Service/Person/AggregateRating/BreadcrumbList via `useSEO`.",
                    "**Internal linking**: marketplace landings cross-link + către ghiduri. Ghiduri linkează către marketplace.",
                    "**Romanian-first**: `<html lang=\"ro\">`, `og:locale=ro_RO`, geo.region=RO.",
                ]},
            ],
        },
        {
            "heading": "10. Monitorizare & Observability",
            "body": [
                {"type": "list", "items": [
                    "**Morning Briefing** (top admin dashboard) — 6 tile-uri (healthcheck, smoke test, data integrity, incidents, AI findings, backup).",
                    "**Smoke Test** — E2E flow multi-rol, la 30 min, alert email pe fail.",
                    "**Healthcheck** — probes: Mongo, LLM, Resend, Stripe, OAuth, VAPID, admin emails.",
                    "**Data Integrity Scanner** — orphan twins, escrow mismatches, missing payments.",
                    "**Public Status Page** — `/status` (live healthcheck + incident history 30 zile).",
                    "**Audit Log** — toate acțiunile admin (GDPR).",
                ]},
                {"type": "callout", "variant": "success", "title": "Proactive mode",
                 "body": "Sistemul alertează pe email DOAR când e ceva în neregulă — briefing zilnic 09:00, instant pe smoke test failure. Inbox curat în zilele bune."},
            ],
        },
        {
            "heading": "11. Knowledge Base intern (acest sistem)",
            "body": [
                {"type": "list", "items": [
                    "**Content**: Python dict în `backend/docs_content.py` — single source, fără DB migrări.",
                    "**Schema bloc**: paragraph, list, callout, steps, code, h3, image_placeholder, screencast, lottie.",
                    "**Render**: PDF (reportlab), Markdown (custom converter), HTML (DocViewer.jsx).",
                    "**Distribuție**: email cu PDF + link tokenizat 30 zile, auto-onboarding, bulk send pe rol.",
                    "**Search**: full-text local cu diacritic normalization, `Cmd+K` în admin docs panel.",
                ]},
                {"type": "h3", "text": "Cum adaugi un doc nou"},
                {"type": "code", "text": "# 1. Editezi backend/docs_content.py — adaugi un dict NEW_DOC\nNEW_DOC = {\n    \"slug\": \"my-new-doc\",\n    \"role\": \"admin\",\n    \"title\": \"...\",\n    \"subtitle\": \"...\",\n    \"version\": \"1.0\",\n    \"updated_at\": \"2026-XX-XX\",\n    \"sections\": [{\"heading\": \"...\", \"body\": [...]}],\n    \"faq\": [{\"q\": \"...\", \"a\": \"...\"}],\n}\n\n# 2. Înregistrezi în DOCS_CONTENT\nDOCS_CONTENT[\"my-new-doc\"] = NEW_DOC\n\n# 3. Hot reload — apare automat în Admin → Documentație & Training"},
            ],
        },
    ],
    "faq": [
        {"q": "Cum schimb conținutul unui doc existent?", "a": "Editezi direct `backend/docs_content.py` și salvezi. Hot reload preia în 2-3 secunde. Nu necesită restart backend pentru schimbări de dict-uri."},
        {"q": "Cum adaug imagini/animații?", "a": "**CSS pulse** — `{\"type\": \"image_placeholder\", \"caption\": \"...\", \"src\": \"identifier\"}`. **MP4/GIF** — fișier în `/app/frontend/public/animations/`, referință `{\"type\": \"screencast\", \"src\": \"/animations/my.mp4\"}`. **Lottie** — creezi pe lottiefiles.com, descarci JSON, `{\"type\": \"lottie\", \"src\": \"/animations/my.json\"}`."},
        {"q": "Cum debugez o eroare 500 din producție?", "a": "1. Reproduce în preview. 2. `tail -n 200 /var/log/supervisor/backend.err.log` în preview. 3. Dacă apare doar în prod (env-related), verifică Emergent Deployment Secrets. 4. Pentru DNS/SSL issues, contactează Emergent Support."},
        {"q": "Cum adaug un endpoint nou?", "a": "1. Router în `routes/my_module.py` cu `prefix=\"/api/my-prefix\"`. 2. Importi în `server.py`, `app.include_router(...)`. 3. `Depends(require_role(\"admin\"))` pentru protecție. 4. Testezi cu `curl -b /tmp/cookies.txt ${API_URL}/api/my-prefix/...`."},
        {"q": "Care e diferența între preview și producție?", "a": "**Preview** = dev environment (URL `*.emergentagent.com`). Modificările instant. **Producție** = `https://propmanage.ro`. Cod actualizat doar la redeploy. Env vars în 2 locuri (Emergent Deployment Secrets vs `.env`). DB separat."},
        {"q": "Cum fac rollback la o versiune anterioară?", "a": "Emergent are funcția **Rollback** în UI care nu costă credite. Folosește-o, nu rula `git reset` manual (păstrează `.git` și `.emergent` intacte)."},
        {"q": "De ce documentația e în Python, nu în .md?", "a": "Pentru că (1) e single-source pentru PDF/HTML/MD, (2) versionarea în cod, (3) Pydantic-like validare schema, (4) hot reload instant, (5) search structural (heading vs body vs FAQ)."},
    ],
}


# ============================================================================
# REGISTRY
# ============================================================================
DOCS_CONTENT = {
    "client": CLIENT_DOC,
    "specialist": SPECIALIST_DOC,
    "operator": OPERATOR_DOC,
    "admin": ADMIN_DOC,
    "qa-testing": QA_DOC,
    "architecture": ARCHITECTURE_DOC,
}


def get_doc(slug: str) -> dict | None:
    return DOCS_CONTENT.get(slug)


def all_doc_meta() -> list[dict]:
    """Lightweight list (no body) for admin UI listing."""
    out = []
    for slug, d in DOCS_CONTENT.items():
        out.append({
            "slug": slug,
            "role": d["role"],
            "title": d["title"],
            "subtitle": d["subtitle"],
            "version": d["version"],
            "updated_at": d["updated_at"],
            "sections_count": len(d.get("sections", [])),
            "faq_count": len(d.get("faq", [])),
        })
    return out
