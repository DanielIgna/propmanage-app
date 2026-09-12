"""Default templates for the 6 mandatory legal contracts.

Each template is plain markdown — admins can extend / override per version via
`POST /api/admin/legal/documents`. The first time the app starts, these templates
are seeded into the `legal_documents` collection (idempotent — by `type` + `version`).
"""

LEGAL_DOC_TYPES = [
    "nda",
    "collaboration",
    "ip_cession",
    "security_policy",
    "infra_access",
    "regulation",
    "city_partner",
    "marketplace_partner",
]

DEFAULT_VERSION = "1.0"

LEGAL_TEMPLATES = {
    "nda": {
        "title": "Acord de Confidențialitate (NDA)",
        "summary": "Obligația de a păstra confidențiale toate informațiile, codul, datele și strategiile platformei PropManage.",
        "body": """# Acord de Confidențialitate (NDA)

**Între** PropManage (denumită în continuare „Platforma") și Colaboratorul semnatar.

## 1. Definiția informațiilor confidențiale
Toate informațiile, codul sursă, documentația, arhitectura, design-ul, datele utilizatorilor, prompturile AI, modelele, strategiile comerciale, financiare și operaționale ale Platformei sunt considerate confidențiale, indiferent de formatul lor.

## 2. Obligații
Colaboratorul se obligă:
- să nu dezvăluie informațiile confidențiale către terți;
- să nu utilizeze informațiile decât pentru îndeplinirea atribuțiilor în cadrul Platformei;
- să protejeze fizic și digital documentele și accesele primite;
- să returneze sau să distrugă toate materialele confidențiale la încetarea colaborării.

## 3. Durata
Obligația de confidențialitate continuă **5 ani** de la încetarea colaborării.

## 4. Sancțiuni
Încălcarea NDA poate atrage răspunderea civilă și penală conform legislației române și europene aplicabile.

## 5. GDPR
Datele personale ale Colaboratorului sunt procesate conform Politicii GDPR a Platformei, disponibilă în secțiunea Compliance.

Prin acceptarea acestui document, Colaboratorul declară că a citit și înțeles obligațiile prevăzute.
""",
    },
    "collaboration": {
        "title": "Contract de Colaborare",
        "summary": "Definește relația operațională, livrabilele, responsabilitățile și absența calității de asociat / acționar.",
        "body": """# Contract de Colaborare

**Între** PropManage și Colaboratorul semnatar.

## 1. Natura colaborării
Colaboratorul prestează servicii de dezvoltare software, QA, consultanță sau alte activități IT conform descrierii rolului din profilul său.

## 2. ✋ Limitare expresă de proprietate
**Colaboratorul NU devine asociat, acționar, coproprietar sau părtaș la profitul companiei.**
Orice recompensă, bonus sau remunerație se realizează exclusiv în baza acestui contract și a documentelor anexate.

## 3. Livrabile și termene
Sunt definite per task / sprint în sistemul intern al Platformei (ToDo Board, IT Collaborators Hub).

## 4. Remunerație
Conform tarifului orar / proiect agreat și înregistrat în profilul Colaboratorului. Recompensele estimate prin scoring intern nu constituie obligații ferme de plată până la îndeplinirea condițiilor contractuale.

## 5. Responsabilități
- Respectarea politicilor de securitate și acces;
- Livrare cod conform standardelor de calitate ale Platformei;
- Acceptare NDA, Cesiune IP, Politică Securitate și Regulament Strategic Contributors.

## 6. Încetare
Oricare parte poate înceta colaborarea cu preaviz de **14 zile**.

## 7. Legea aplicabilă
Contractul este guvernat de legislația română și europeană aplicabilă.
""",
    },
    "ip_cession": {
        "title": "Cesiune Drepturi Patrimoniale de Autor Software",
        "summary": "Toată producția (cod, docs, arhitectură, design, automatizări, AI, prompturi, teste) devine proprietatea exclusivă a Platformei.",
        "body": """# Cesiune Drepturi Patrimoniale de Autor Software

**Cedent:** Colaboratorul semnatar.
**Cesionar:** PropManage.

## 1. Obiectul cesiunii
Cedentul cedează către Cesionar, **exclusiv, irevocabil și pentru întreaga durată legală de protecție**, toate drepturile patrimoniale de autor asupra:
- codului sursă;
- documentației;
- arhitecturii software;
- design-ului UI/UX;
- automatizărilor;
- scripturilor;
- componentelor AI;
- modelelor și prompturilor;
- testelor automate sau manuale;
- documentelor tehnice;
- oricăror lucrări intelectuale produse în cadrul colaborării.

## 2. Întinderea cesiunii
Cesiunea include:
- reproducerea;
- distribuirea;
- modificarea;
- traducerea;
- adaptarea;
- comunicarea publică;
- comercializarea sub orice formă, în orice teritoriu.

## 3. Garanții ale Cedentului
Cedentul declară pe propria răspundere că:
- este autorul exclusiv al lucrărilor cedate;
- lucrările nu încalcă drepturi de autor sau brevete ale unor terți;
- nu există acorduri anterioare care să limiteze cesiunea.

## 4. Remunerație
Cesiunea este parte din remunerația globală convenită în Contractul de Colaborare. Cedentul nu pretinde plăți suplimentare pentru drepturile cedate.

## 5. Drepturi morale
Cedentul își păstrează dreptul moral la paternitatea operei, care va fi consemnat în istoricul intern al Platformei (autor + commit-uri).

## 6. Durata
Cesiunea operează pe durata maximă legală de protecție prevăzută de legislația aplicabilă.
""",
    },
    "security_policy": {
        "title": "Politica de Securitate IT",
        "summary": "Reguli obligatorii de securitate: parole, 2FA, criptare disk, gestionare secrete, raportare incidente.",
        "body": """# Politica de Securitate IT

Această politică este parte integrantă a relației de colaborare.

## 1. Stații de lucru
- Disk criptat (FileVault / BitLocker / LUKS) este obligatoriu;
- Sistem de operare actualizat la zi;
- Antivirus / endpoint protection activ.

## 2. Autentificare
- Parole strong (min 14 caractere, gestor de parole obligatoriu);
- **2FA obligatoriu** pe toate conturile platformei și serviciilor (GitHub, MongoDB, Stripe, Resend, etc.).

## 3. Gestionarea secretelor
- **NICIODATĂ** nu se commit-ează chei API, parole, certificate;
- Secretele se stochează doar în `.env`, vault sau secret manager;
- Rotirea cheilor compromise se face în max 24h.

## 4. Cod și branch
- PR obligatoriu pentru orice modificare în `main`;
- Cod review minim 1 reviewer;
- Nu se rulează cod neaprobat în producție.

## 5. Acces date utilizatori
- Accesul la date personale ale utilizatorilor finali este permis doar pentru investigații documentate;
- Orice export trebuie logat în Audit Log.

## 6. Raportare incidente
- Suspiciune de breșă → notificare IMEDIATĂ (max 1h) către Founder / Security Lead;
- Logging activ în jurnalul intern Bug Memory / Audit Log.

## 7. Sancțiuni
Încălcarea politicii poate duce la revocarea accesului, încetarea contractului și răspundere conform legislației.
""",
    },
    "infra_access": {
        "title": "Politica de Acces la Infrastructură",
        "summary": "Reguli pentru acces la servere, baze de date, repository-uri, third-party services și producție.",
        "body": """# Politica de Acces la Infrastructură

## 1. Principiul „least privilege"
Fiecare colaborator primește **doar accesele minim necesare** pentru rolul său. Accesele suplimentare se solicită explicit și se logează.

## 2. Inventar accese
Accesele active sunt înregistrate în panoul Admin → IT Collaborators Hub și revizuite trimestrial.

## 3. Tipuri de acces
- **Cod**: GitHub repository (read / write per branch);
- **Producție**: doar Tech Lead / DevOps autorizat;
- **Baza de date producție**: doar pentru migrări sau debugging documentat;
- **Third-party** (Stripe, Resend, Twilio, etc.): roluri scoped.

## 4. Revocare
La încetarea colaborării, **toate accesele se revocă în max 24h**:
- Token-uri GitHub;
- Chei SSH;
- Conturi MongoDB;
- API keys third-party;
- Acces VPN / bastion.

## 5. Audit
Toate accesările resurselor critice sunt logate. Reviewul logurilor este lunar.

## 6. Producție
- Nu se modifică direct date producție fără ticket aprobat;
- Snapshot DB înainte de orice migrare;
- Roll-back plan obligatoriu.
""",
    },
    "regulation": {
        "title": "Regulamentul Programului Strategic Contributors",
        "summary": "Cadrul programului de colaboratori strategici: poziții cheie, recompense estimate (non-obligatorii), criterii de promovare.",
        "body": """# Regulamentul Programului Strategic Contributors

## 1. Scop
Programul recunoaște contribuțiile excepționale ale colaboratorilor IT prin acordarea de **poziții operaționale** și **recompense estimate**, fără a conferi drepturi de proprietate.

## 2. Poziții cheie disponibile
Colaboratorii performanți pot primi una sau mai multe dintre următoarele poziții operaționale:
- **Technical Lead** — responsabil arhitectură + cod review;
- **QA Lead** — responsabil strategia de testare;
- **Architecture Reviewer** — review pe schimbări de design;
- **Security Reviewer** — review pe pull-requests cu impact de securitate;
- **Product Advisor** — input strategic pe roadmap;
- **AI Advisor** — input strategic pe componentele AI;
- **Technical Mentor** — mentorat pentru juniori;
- **Community Lead** — relația cu comunitatea de developeri externi.

**Aceste poziții acordă responsabilități și acces operațional, dar NU oferă drepturi de proprietate asupra companiei, acțiuni sau părți sociale.**

## 3. Tipuri de recompense
Platforma poate acorda:
- remunerare imediată (tarif orar / proiect);
- remunerare etapizată (milestones);
- bonusuri condiționate (KPI sprint / OKR);
- recompense viitoare programate;
- beneficii non-financiare (mentorat, certificări, training-uri, conferințe).

## 4. ⚠️ Disclaimer obligatoriu
Toate recompensele estimate sunt afișate cu următorul disclaimer:
> *„Recompensele estimate nu reprezintă obligații ferme de plată până la îndeplinirea condițiilor contractuale."*

## 5. Criterii de promovare
Promovarea în poziții cheie se face în baza:
- consistenței livrărilor (review_score ≥ 8);
- ratei de bug-uri introduse (< 1 / sprint);
- aprobării Founder-ului + 1 super-admin.

## 6. Revocarea pozițiilor
Pozițiile pot fi retrase oricând, cu preaviz de 14 zile, în baza:
- nerespectării politicii de securitate;
- scăderii constante a metricilor de performanță;
- retragerii Colaboratorului din program.

## 7. Conformitate
Programul respectă legislația română și europeană, inclusiv GDPR.
""",
    },
    "city_partner": {
        "title": "Acord Strategic City Partner",
        "summary": "Acord-cadru cu partener local (administrator imobile / dezvoltator / companie locală) — etapa V1: aducere clienți. Funcționalități viitoare doar prin acte adiționale.",
        "body": """# Acord Strategic City Partner

**Între:** PropManage (denumită „Platforma") și Partenerul Local semnatar (denumit „Partener").

## 1. Scop și etapă inițială
Părțile lansează o colaborare strategică pentru dezvoltarea ecosistemului local. **Etapa V1 a colaborării actuale se limitează la următoarele:**
- accesul Partenerului la rețeaua sa proprie de administratori/clienți pentru promovarea Platformei;
- onboarding-ul clienților aduși de Partener în ecosistemul PropManage;
- lansarea serviciului **Digital Twin** ca punct de intrare comun pe piață.

> *„Orice funcționalități sau modele de business viitoare (marketplace, comisioane complexe, specialiști, servicii noi) NU fac parte din colaborarea actuală și pot fi adăugate exclusiv prin acte adiționale negociate separat."*

## 2. ✋ Limitare expresă de proprietate
**Colaborarea este NON-EXCLUSIVĂ.** Partenerul rămâne **independent juridic și operațional** și NU devine asociat, acționar, coproprietar sau părtaș la profitul companiei.

## 3. Ce oferă Platforma
- infrastructură digitală + tehnologia PropManage;
- onboarding-ul administratorilor / clienților aduși;
- suport tehnic și operațional;
- marketing și branding comun (când e cazul);
- dezvoltarea continuă a serviciilor;
- acces la ecosistem.

## 4. Ce oferă Partenerul
- acces la rețeaua proprie de administratori și clienți;
- promovare locală a Platformei (online + offline, în limitele bunei credințe);
- introducerea Platformei în grupurile și comunitățile proprii;
- facilitarea relației cu administratorii de imobile;
- feedback de piață constant.

## 5. Lead management
Pentru fiecare client adus de Partener, Platforma înregistrează în mod transparent:
- sursa și data introducerii;
- partenerul care a făcut introducerea;
- stadiul onboarding-ului;
- conversia;
- venitul generat (după activare).

## 6. Reguli etice
Părțile convin:
- să acționeze cu bună credință;
- să nu utilizeze informațiile primite pentru concurență directă neloială;
- să dezvolte împreună piața locală;
- să analizeze oportunități comune de monetizare;
- să protejeze datele și confidențialitatea clienților, conform GDPR.

## 7. Limitare teritorială (opțională)
Partenerului i se poate acorda o **protecție parțială la nivel de oraș**, condiționată de:
- statusul activ al colaborării;
- îndeplinirea obiectivelor minime stabilite;
- respectarea obligațiilor contractuale;
- contribuția efectivă la dezvoltarea ecosistemului.

În caz contrar, protecția teritorială încetează automat.

## 8. Onboarding (flux standard)
1. prezentare oficială;
2. introducere în ecosistem;
3. prezentare pe grupurile disponibile;
4. invitație către administratori;
5. creare conturi platformă;
6. urmărire social media;
7. activare campanii locale.

## 9. Plan strategic primele 3 luni
- **Faza 1**: Lansare Digital Twin (prezentare + testare piață);
- **Faza 2**: Integrare specialiști verificați (firme/PFA/echipe locale) — *prin act adițional*;
- **Faza 3**: Analiză piață (Digital Twin, mentenanță, amenajări, audituri, servicii tehnice);
- **Faza 4**: Marketplace + sisteme de comisionare — *prin act adițional*.

## 10. Confidențialitate și GDPR
Părțile se obligă reciproc la confidențialitate. Datele personale ale clienților se prelucrează conform GDPR și politicilor de confidențialitate ale Platformei.

## 11. Încetare
Oricare parte poate înceta colaborarea cu preaviz de **30 zile**. Drepturile câștigate până la încetare se păstrează.

## 12. Legea aplicabilă
Acordul este guvernat de legislația română și europeană aplicabilă.

Prin acceptarea acestui acord, Partenerul confirmă că a citit, înțeles și acceptat limitarea expresă a colaborării la **etapa V1** descrisă mai sus.
""",
    },
    "marketplace_partner": {
        "title": "Acord Marketplace Partner",
        "summary": "Cadru de colaborare comercială între PropManage (platformă de intermediere) și partener Marketplace (magazin / depozit / fabrică / distribuitor / producător).",
        "body": """# Acord Marketplace Partner

**Între:** PropManage (denumită „Platforma") și Partenerul Marketplace semnatar.

## 1. Natura colaborării
Părțile încheie o colaborare comercială pentru promovarea produselor și serviciilor Partenerului în ecosistemul digital PropManage.

**Platforma NU comercializează direct produsele.** Platforma funcționează ca:
- generator de lead-uri;
- ecosistem de recomandare;
- canal de promovare;
- marketplace de conectare;
- platformă de colaborare comercială.

Clientul final este direcționat către Partener pentru achiziție.

## 2. ✋ Limitare expresă
Colaborarea este **non-exclusivă**. Partenerul rămâne **independent juridic și operațional**. Nu există asociere, parteneriat societar sau drept asupra companiei.

## 3. Categorii acceptate
Magazine materiale construcții, depozite, fabrici, distribuitori, producători, showroom-uri, furnizori servicii — gresie/faianță, uși, sanitare, mobilier, vopsele, instalații, HVAC, smart home, tâmplărie, acoperișuri, electrocasnice, fotovoltaice, pompe căldură, sisteme securitate etc.

## 4. Nivel partener
Partenerul poate fi încadrat în unul dintre nivelurile:
- **Basic Partner** — profil simplu;
- **Verified Partner** — profil verificat;
- **Premium Partner** — promovare extinsă;
- **Strategic Partner** — campanii comune;
- **Exclusive Partner** — partener unic per categorie/zonă.

## 5. Politici comerciale
Pentru fiecare partener se pot configura:
- discount exclusiv pentru clienții Platformei;
- discount special pentru specialiști;
- promoții dedicate;
- campanii sezoniere;
- cupoane și bonusuri.

## 6. Sistem de comisioane
Comisionarea se poate face prin:
- comision procentual;
- comision fix;
- comision per lead;
- comision per vânzare;
- abonament lunar;
- taxă onboarding;
- taxă promovare;
- taxă administrare colaborare.

Termenii exacti se stabilesc per partener prin act adițional sau pachet activat.

## 7. Pachete de activare
- **Starter** — activare basic;
- **Business** — abonament + reduceri promovare;
- **Premium** — vizibilitate sporită + campanii comune;
- **Enterprise** — exclusivitate teritorială + suport dedicat.

## 8. Beneficii Partener
- profil dedicat în marketplace;
- promovare în Platformă și campanii marketing;
- acces la lead-uri verificate;
- acces la statistici;
- participare în campanii comune;
- promovare pe rețelele sociale ale Platformei;
- branding comun (când este cazul).

## 9. Lead Engine
Pentru fiecare lead generat se înregistrează: sursă, client, partener recomandat, dată, status, valoare estimată, conversie, venit generat.

## 10. Marketing comun
Campanii comune, bannere dedicate, promovare social media, newslettere, evenimente locale, webinarii, lansări de produse — toate prin acord scris prealabil.

## 11. Principii comerciale
Platforma:
- conectează;
- recomandă;
- generează oportunități;
- facilitează colaborarea;
- urmărește performanța;
- monetizează serviciul de intermediere și promovare.

## 12. Reguli etice
- bună credință;
- transparență în facturare și preț;
- nediscriminare între clienți;
- protejarea datelor și confidențialitate;
- respectarea concurenței loiale.

## 13. GDPR
Procesarea datelor clienților se face conform Regulamentului (UE) 2016/679 și politicilor Platformei.

## 14. Încetare
Preaviz de 30 zile pentru oricare parte. Comisioanele câștigate până la încetare se păstrează.

## 15. Legea aplicabilă
Acordul este guvernat de legislația română și europeană aplicabilă.

Prin acceptarea acestui acord, Partenerul confirmă cunoașterea modelului de intermediere descris și acceptă termenii comerciali ai pachetului activat.
""",
    },
}


def list_default_templates() -> list:
    """Return list of (type, payload) for seeding."""
    out = []
    for t in LEGAL_DOC_TYPES:
        tpl = LEGAL_TEMPLATES[t]
        out.append({
            "type": t,
            "version": DEFAULT_VERSION,
            "title": tpl["title"],
            "summary": tpl["summary"],
            "body": tpl["body"],
            "mandatory": True,
            "active": True,
            # audience: which user-type must sign this doc.
            # IT docs -> "it_collaborator"; partner contract -> "city_partner".
            "audience": "city_partner" if t == "city_partner" else ("marketplace_partner" if t == "marketplace_partner" else "it_collaborator"),
        })
    return out
