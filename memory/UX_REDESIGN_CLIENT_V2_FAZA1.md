# PropManage — UX/UI Redesign V2 · FAZA 1
## Information Architecture & UX Strategy — Workspace Client
*Status: PROPUNERE — nimic implementat. Așteaptă aprobarea userului înainte de Faza 2 (Wireframe).*
*Bazat pe audit real al codului: `ClientDashboard.jsx` (939 linii), `DashLayout`, `BottomNav`, `QuestPanel`, `TierProgressWidget`, `HouseHealthCard` + capturi producție.*

---

## 1. AUDITUL PROBLEMELOR UX (ce vede azi un client nou, în ordine, la prima deschidere)

La primul login pe `/client`, ÎNAINTE de orice acțiune, utilizatorul primește simultan:

| # | Element | Tip | Problemă |
|---|---------|-----|----------|
| 1 | Banner confirmare email | alertă | legitim, dar concurează cu tot restul |
| 2 | Tur ghidat (modal 5 pași) | overlay | blochează ecranul înainte ca userul să fi văzut ceva |
| 3 | TierCelebrationBanner | banner | sărbătorește ceva ce userul nu înțelege încă ("tier"?) |
| 4 | QuestPanel "Bun venit — 0/6 pași" | card mare | 6 CTA-uri ("Mergi →") în același card |
| 5 | TierToolsPanel | card | funcții deblocate/blocate — concept intern expus prematur |
| 6 | TierProgressWidget "Progres către VERIFIED 0%" | card | al 3-lea element de gamificare consecutiv |
| 7 | Hero "Ai nevoie de un specialist?" | hero | abia aici apare scopul real al aplicației |
| 8 | QuickServicesGrid (6 categorii + lacăte premium/twin) | grid | ok ca idee, dar cu stări blocate + mesaje de lock |
| 9 | Card proprietate cu 5 micro-butoane | card | selector + Administrează + Timeline + 2FA + Twin — 5 decizii într-un rând de 10px font |
| 10 | Twin CTA (banner amber) + Twin CTA big | 2 carduri | același concept vândut de 2 ori pe același ecran |
| 11 | Cycle preview (escrow) | card | explică un flux financiar înainte de prima cerere |
| 12 | HouseHealthCard | card | feature valoros, dar irelevant fără proprietate/istoric |
| 13 | Wallet top-up bar (preseturi + custom) | bară | i se cere să bage bani înainte să fi cerut ceva |
| 14 | Bula AI Concierge + WhatsApp + cookie banner | flotante | 3 elemente flotante simultan în colț |

**Diagnostic:** 14 blocuri concurente, ~15–20 CTA-uri vizibile, 3 sisteme de gamificare paralele (quest, tier, progress), 2 CTA-uri Twin duplicate, concepte interne (tier, escrow, tokeni) expuse la primul contact. Utilizatorul nu poate răspunde în 3 secunde la "ce fac aici?".

### Încălcări per principiu
- **Hick's Law** — încălcat masiv: ecranul "Solicită" cere simultan ~15 decizii. Rândul proprietății singur are 5 alegeri. QuestPanel are 6.
- **One Primary Action** — nu există: hero-ul "Ai nevoie de un specialist?" e vizual egal cu Twin CTA, HouseHealth și Wallet. Niciun element nu domină.
- **Progressive Disclosure** — inexistent: escrow, 2FA, tier system, tokeni, wallet — toate la suprafață din secunda 1.
- **Miller's Law (7±2)** — 14 blocuri > limita de memorie de lucru; grupurile nu sunt "chunk-uite" pe scopuri.
- **Fitts Law** — butoanele critice (Administrează, Timeline, 2FA, Twin) au font 10px și ținte minuscule; pe mobil sunt greu de atins.
- **Goal Directed Design** — dashboard-ul e organizat pe *feature-uri* (ce a construit echipa), nu pe *obiectivele clientului* (rezolvă o problemă la locuință).
- **Visual Hierarchy / White Space** — glass-cards cu aceeași greutate vizuală, lipite; nimic nu respiră.
- **Mobile First / Thumb Friendly** — BottomNav există (bun!), dar conținutul de deasupra e o coloană desktop comprimată; acțiunea primară nu e în zona degetului mare.

### Ce e deja BUN (păstrăm)
- BottomNav cu 4 zone (Solicită / Lucrările mele / Notificări / Setări) — aliniat cu Hick's Law; validat și de prototipul Client Junior.
- QuickServicesGrid ca *concept* (categorii vizuale) — trebuie doar promovat și curățat de lacăte.
- Empty-state "Începe cu prima ta proprietate" — direcție corectă, dar concurată de restul zgomotului.
- Fluxul Client Junior (/dashboard/client-junior) — deja validat ca model de flux "o întrebare pe ecran".

---

## 2. STRATEGIA: de la "panou de feature-uri" la "panou de acțiuni"

**Principiu central:** Clientul are UN job: *"am o problemă/un plan la locuință → găsesc pe cineva de încredere să-l rezolve"*. Tot restul (Twin, HouseHealth, Wallet, Escrow, Tokeni, Timeline, Documente) sunt **instrumente de suport** care apar CONTEXTUAL, în momentul din flux în care devin utile — nu înainte.

**Regula de aur propusă:** *Home = 1 hero + 4 acțiuni + 1 zonă contextuală. Orice altceva trăiește la al doilea tap.*

---

## 3. PROGRESSIVE DISCLOSURE — harta deciziilor

### RĂMÂNE pe Home (primele 5 secunde)
| Element | Justificare |
|---|---|
| Salut + context ("Bună, Daniel · Ap. Aviației") | orientare: *unde sunt* |
| **Hero Card adaptiv** (vezi §6) | răspunde la *ce fac acum* — UNICA acțiune primară |
| **4 acțiuni principale** (grid 2×2, thumb-zone) | Solicită serviciu · Proprietatea mea · Lucrări active (cu badge) · Ajutor/AI |
| Zonă contextuală (max 1–2 carduri) | DOAR ce e relevant azi: ofertă nouă primită, plată în așteptare, lucrare în derulare |

### SE MUTĂ pe pagini secundare (1 tap distanță)
| Element | Destinație nouă | De ce |
|---|---|---|
| Wallet + top-up + tokeni | "Proprietatea mea" → secțiune Plăți / sau Setări → Portofel | banii devin relevanți abia la acceptarea unei oferte; atunci fluxul de plată îl aduce automat aici |
| Digital Twin (ambele CTA-uri) | pagina Proprietății (un singur card "Locuința ta în 3D") | e un feature al *proprietății*, nu al home-ului; un singur punct de intrare |
| HouseHealthCard | pagina Proprietății | scor despre casă → lângă casă |
| Timeline proprietate | pagina Proprietății | istoricul aparține proprietății |
| 2FA | Setări → Securitate | zero justificare pe home |
| Escrow "cycle preview" | inline în fluxul de plată al unei cereri | explici escrow exact când userul plătește — nu înainte |
| Documente | pagina Proprietății → Documente | context, nu home |
| TierToolsPanel + TierProgressWidget | Setări → Nivelul contului (o singură pagină de progres) | gamificarea devine pull, nu push |

### APARE DOAR CONTEXTUAL (0 taps — dar numai când condiția e adevărată)
| Element | Condiția de afișare |
|---|---|
| Banner confirmare email | doar el + hero; restul gamificării ascunsă până la confirmare |
| QuestPanel (checklist onboarding) | comprimat într-un singur rând de progres în Hero Card "user nou"; expandabil |
| Celebrare tier | toast/confetti o singură dată, la momentul promovării — nu banner persistent |
| "Ai 2 oferte noi" | doar când există oferte necitite → devine cardul contextual #1 |
| "Plată în așteptare" | doar când o lucrare așteaptă escrow → card contextual cu CTA unic |
| Cerere recenzie | doar după confirmarea unei lucrări |
| Tur ghidat | NU la primul login; oferit ca link discret "Fă turul" în Hero, după primele 10 sec |

---

## 4. NOUA ARHITECTURĂ INFORMAȚIONALĂ

```
CLIENT WORKSPACE
│
├── 🏠 ACASĂ (home = panou de acțiuni)
│     Header slim → Hero Card adaptiv → 4 acțiuni → Contextual (0–2 carduri)
│
├── ➕ SOLICITĂ (fluxul validat Client Junior)
│     Search → Categorii → wizard 1-întrebare/ecran → confirmare
│     (Design Interior = categorie premium, cu explicație inline, nu lacăt mut)
│
├── 🔧 LUCRĂRILE MELE
│     Listă cu status vizual (pași: ofertă → acceptat → în lucru → finalizat)
│     Detaliu lucrare = TOT contextul ei: chat, oferte, plată/escrow (explicat aici),
│     faze design, timeline, dispută, recenzie
│
├── 🏡 PROPRIETATEA MEA (noul hub al "instrumentelor")
│     Card proprietate mare → Digital Twin (1 intrare) → House Health →
│     Timeline → Documente → Plăți & Portofel → +Adaugă proprietate
│
└── ⚙️ SETĂRI
      Profil · Securitate (2FA) · Notificări · Nivelul contului (tier/questuri) · Portofel (alias)
```

**Navigare: exact 5 destinații.** Mobil = bottom nav (Acasă · Solicită(central, accentuat) · Lucrări · Proprietate · Setări). Desktop = aceleași 5 în sidebar/topbar — derivat, nu regândit.
*Notă:* "Notificări" iese din nav (era una din cele 4 zone) → devine iconiță clopoțel în header + feed în Acasă/contextual. Justificare: notificările nu sunt o *destinație-scop*, sunt un semnal; badge-urile de pe "Lucrări" preiau rolul.

---

## 5. HOME PAGE — primele 5 secunde

**Ce VEDE:** 1) unde e ("Bună, Daniel · Ap. Aviației"), 2) starea lui într-o singură propoziție (Hero), 3) UN buton dominant, 4) 4 tile-uri mari de acțiune, 5) maxim 2 carduri contextuale. Total: ~6 elemente, 1 acțiune primară.

**Ce NU vede:** wallet/top-up, tokeni, escrow, tier/quest-uri desfășurate, 2FA, Twin CTA duplicat, HouseHealth, timeline, statistici, tur ghidat forțat. Toate există — la un tap, în contextul potrivit.

---

## 6. HERO CARD — 3 variante adaptive (starea userului decide, nu layout-ul)

**A. Utilizator NOU (fără proprietate)**
- Mesaj: "Hai să pornim: adaugă prima ta proprietate" + micro-progres discret ("pasul 1 din 3")
- CTA unic: **[Adaugă proprietatea]**
- De ce: fără proprietate, 80% din platformă e inertă; orice alt CTA e zgomot. Înlocuiește QuestPanel+TierProgress+TierTools cu UN pas clar. (Goal-Directed + One Primary Action)

**B. Utilizator CU proprietate, FĂRĂ lucrare activă**
- Mesaj: "Totul e în regulă la Ap. Aviației" + 1 sugestie blândă (ex. scor House Health ca link, nu card)
- CTA unic: **[Solicită un serviciu]**
- De ce: starea "sănătoasă" e liniștitoare (Revolut-style "balance ok"), iar unica acțiune cu valoare de business e cererea de serviciu. Aici Hero devine motorul de conversie.

**C. Utilizator CU lucrare activă**
- Mesaj: statusul lucrării ca progres vizual ("Zugrăvit living — 2 oferte primite" / "în lucru, zi 3")
- CTA unic: **[Vezi ofertele]** / **[Deschide lucrarea]**
- De ce: când există o tranzacție în curs, ea E jobul userului (model Uber: cursa activă ocupă ecranul). Reduce și time-to-decision pe oferte → conversie mai rapidă.

*(variantă implicită D, opțională: email neconfirmat → Hero = confirmarea emailului, restul estompat)*

---

## 7. WIREFRAME TEXTUAL — Acasă (Mobile First)

```
┌──────────────────────────────────────┐
│ HEADER (slim, 56px)                  │  Scop: orientare. Prioritate: P2
│  Avatar · "Bună, Daniel"             │  Fără: tier badge, toggle-uri, RO/EN
│  🔔 (badge)          Ap. Aviației ▾  │  (mutate în Setări)
├──────────────────────────────────────┤
│ HERO CARD (≈35% din viewport)        │  Scop: starea mea + UNICA acțiune
│  [varianta A/B/C după stare]         │  Prioritate: P0
│  Titlu mare · 1 frază · 1 CTA plin   │  Thumb: CTA în jumătatea de jos a cardului
├──────────────────────────────────────┤
│ 4 ACȚIUNI PRINCIPALE (grid 2×2)      │  Scop: rutele frecvente. P1
│  ➕ Solicită   │  🏡 Proprietatea    │  Tile-uri mari (≥96px), icon+label,
│  🔧 Lucrări(2) │  💬 Întreabă AI     │  fără text secundar. Fitts-friendly.
├──────────────────────────────────────┤
│ CONTEXTUAL (0–2 carduri, condițional)│  Scop: "ce s-a întâmplat nou". P1
│  ex: "2 oferte noi la Zugrăvit" →    │  Dacă nu există nimic nou: NIMIC.
│  ex: "Plată în așteptare" →          │  White space > umplutură.
├──────────────────────────────────────┤
│ DESCOPERĂ (opțional, sub fold)       │  Scop: educare pasivă. P3
│  1 carusel discret: House Health /   │  Un singur rând, dismissible,
│  Digital Twin / Ghiduri              │  max 1 promo pe sesiune.
├──────────────────────────────────────┤
│ BOTTOM NAV (5, fix, thumb-zone)      │  Acasă · [➕ Solicită accent] ·      │
│                                      │  Lucrări · Proprietate · Setări      │
└──────────────────────────────────────┘
```

**Desktop (derivat, nu regândit):** aceeași ordine verticală; nav-ul devine sidebar stânga; Hero + 4 acțiuni pe un rând superior; contextualul în coloană dreaptă. Nicio funcție în plus față de mobil — doar re-așezare.

**Pagina "Proprietatea mea" (wireframe scurt):** foto/nume proprietate → rând stări (Health score · Twin status · documente) → listă instrumente (Twin, Timeline, Documente, Plăți & Portofel) → adaugă proprietate. Un singur CTA per instrument.

---

## 8. REZUMATUL DECIZIILOR (de aprobat / ajustat)

1. Home devine panou de acțiuni: 1 Hero adaptiv (3 variante) + 4 acțiuni + contextual. ✔/✘
2. Navigare la 5 elemente; Notificările ies din nav → clopoțel în header. ✔/✘
3. Wallet/tokeni/escrow dispar de pe Home → apar în fluxul de plată + Proprietate/Setări. ✔/✘
4. Twin + HouseHealth + Timeline + Documente se consolidează în hub-ul "Proprietatea mea". ✔/✘
5. Gamificarea (quest/tier) se comprimă: 1 rând de progres în Hero (user nou) + pagină dedicată în Setări; celebrări = toast unic. ✔/✘
6. Turul ghidat nu mai blochează primul login. ✔/✘
7. Fluxul "Solicită" preia modelul validat Client Junior (o întrebare/ecran). ✔/✘

**Fazele următoare:** Faza 2 = wireframe vizual pe rută de test (fără a atinge `/client`) · Faza 3 = UI design · Faza 4 = implementare + migrare controlată. Nimic nu se implementează fără aprobarea acestui document.
