# Rădăcini — evaluarea impactului asupra protecției datelor (DPIA), ciornă

Versiune 0.1 · 2026-10-26 · **Ciornă tehnică pentru jurist sau DPO. Nu e o DPIA finală.** Structura urmează art. 35(7) GDPR. Punctele „de verificat” le confirmă juristul.

## 1. De ce o DPIA
Criterii care ar putea face DPIA obligatorie (de verificat pe lista ANSPDCP):
- **date despre minori** (gospodării);
- **localizarea exactă** a terenurilor (proprietarul e identificabil);
- **evaluare și scor public** (rating pentru vânzători, scor de transparență la composesorate);
- **date despre persoane decedate și moștenitori** (registrul composesoratelor);
- **combinarea surselor** (profil, terenuri, tranzacții, comunități).

Volumul în pilot e mic (sute de persoane). O DPIA e totuși recomandată înainte de beta-ul public.

## 2. Descrierea prelucrării

| Categorie | Date | Scop | Temei (propus) | Cine vede |
|---|---|---|---|---|
| Cont și profil | nume, email, localitate, interese | funcționarea platformei | contract (art. 6(1)(b)) | membrul; numele, alți membri în context |
| Terenuri | titlu, suprafață, **locație exactă**, fotografii | potrivirea proprietarilor cu cultivatorii | contract | public: locație aproximativă (2 zecimale); exact: proprietarul, personalul, părțile unui acord semnat (cu jurnal de acces) |
| Acorduri | termeni, hash, **semnături cu IP și user-agent** | consemnarea înțelegerii, probă | contract + interes legitim (probă) | părțile; IP-ul și user-agent-ul nu sunt vizibile celeilalte părți |
| Piață | anunțuri, rezervări, rating | vânzare sau schimb direct între membri | contract | public: anunțul; rezervarea: părțile |
| Gospodării | **minori: prenume, an naștere, relație** | participare în familie | consimțământ parental (art. 8) | titularul gospodăriei |
| Comunități, dispute, raportări | mesaje, motive, decizii | organizare, mediere, moderare (DSA) | interes legitim + obligație legală (DSA) | părțile și personalul |
| Composesorate | **registru: cote, moștenitori, persoane decedate**, documente, prezență, sume cuvenite | transparența asociației | operator: asociația (obligație statutară sau interes legitim); noi suntem persoană împuternicită | conducerea și cenzorii; membrul vede doar rândul propriu |
| Tehnic | IP pentru limitarea cererilor (în memorie), erori (fără date personale) | securitate | interes legitim | nimeni (IP-ul nu se salvează) |

**Persoane împuternicite și transferuri** (de verificat contractele DPA):
- Supabase: baza de date și stocarea, regiunea **eu-west-1 (Irlanda)**.
- Railway: backend, regiune de verificat.
- Cloudflare: frontend și CDN.
- Resend: email, când e configurat; regiune de verificat.
- Google: autentificare OAuth.
- **OpenStreetMap:** plăcile de hartă se încarcă direct de pe `tile.openstreetmap.org`, deci serverele OSM primesc IP-ul vizitatorului. Politica OSM de utilizare a plăcilor nu permite trafic mare. Pentru beta-ul public: un furnizor cu contract (de exemplu MapTiler sau Stadia) sau plăci servite prin propriul proxy.

## 3. Necesitate și proporționalitate
- **Minimizare:**
  - locația publică e aproximativă;
  - minorii n-au cont și au doar prenume și an de naștere;
  - IP-ul de la semnare nu e vizibil celeilalte părți;
  - în jurnalul de erori nu există date personale.
- **Transparență:** termeni și politică proprii, versionate, cu acceptare consemnată.
- **Drepturi:**
  - export complet al datelor (`/me/export`, care include acum și raportările);
  - cerere de ștergere cu procesare manuală;
  - contestarea deciziilor de moderare, prin pagina „Despre și contact”.
- **Retenție:** vezi `POLITICA_RETENTIE.md`. Multe durate nu au încă ștergere automată.

## 4. Riscuri

| # | Risc | Probabilitate | Gravitate | Măsuri existente | Măsuri propuse |
|---|---|---|---|---|---|
| R1 | Locația exactă a unui teren ajunge la persoane neautorizate (furt, presiune asupra proprietarului) | mică | mare | aproximare publică; acces exact doar după acord; jurnal de acces | alertă proprietarului la fiecare acces exact; retenție 12 luni pentru jurnal |
| R2 | Date ale minorilor folosite abuziv | mică | mare | fără cont, date minime, consimțământ parental consemnat | verificarea calității de părinte (declarativ acum); regula de 18 ani; fără fotografii cu minori (de decis) |
| R3 | Acces neautorizat la cont (parolă slabă, sesiune furată) | medie | medie | autentificare PropManage, Google OAuth; acțiunile juridice blocate în impersonare | 2FA opțional; notificare la autentificare nouă |
| R4 | Personalul vede mai mult decât trebuie | mică | medie | roluri (operator pe arie, manager); jurnal de audit | revizuirea trimestrială a listei de personal |
| R5 | Registrul unui composesorat (moștenitori, decedați) e expus sau contestat | medie | mare | doar demo acum; acces doar conducere și cenzori; jurnal care nu se poate șterge | DPA cu asociația înaintea oricărui registru real; aviz juridic J.1–J.2 |
| R6 | Scorul public de transparență sau ratingul afectează reputația unei persoane | medie | medie | criterii publice și explicate | drept la replică; scor vizibil doar membrilor până la aviz |
| R7 | Transfer în afara SEE prin furnizori | medie | medie | Supabase în UE | verificarea DPA-urilor și a clauzelor contractuale standard (SCC) pentru Railway, Resend, Cloudflare, Google |
| R8 | Incident de securitate nedetectat | mică | mare | jurnal de erori, pagina „Stare sistem”, limită de cereri | procedură de notificare în 72 h (cine, cum, șablon); monitorizare externă a disponibilității |
| R9 | Păstrarea datelor mai mult decât e necesar | mare (acum) | medie | ștergere automată doar pentru erori | job de retenție (vezi politica) |

## 5. Concluzie provizorie
- **Beta închis** (invitați, date reale puține): riscul rezidual e acceptabil dacă se aplică măsurile marcate „existente” și se informează testerii.
- **Beta public:** necesită înainte:
  - R5: fără registre reale;
  - R7: verificarea DPA-urilor;
  - R8: procedura de 72 de ore;
  - R9: job-ul de retenție;
  - furnizor de hărți cu contract;
  - avizul juristului pe secțiunile E și J din dosar.

## 6. De completat de jurist sau DPO
- Este DPIA obligatorie (lista ANSPDCP)? E nevoie de un responsabil cu protecția datelor (DPO)?
- Temeiurile din secțiunea 2: sunt corecte?
- Cine semnează ca operator: entitatea afișată pe pagina „Despre și contact”.
- Data revizuirii: la fiecare funcție nouă care prelucrează date sensibile.
