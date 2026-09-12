# PPOS-005 · Desktop Operating System
Status: Draft v1.0 — SPRE APROBARE · Owner: Product Council · Mandat: PPOS-015 (verbatim în board)

> Principiu: Desktop ≠ Mobile XL. Desktopul e spațiul de LUCRU (analiză, comparație, management, multitasking). Business logic identică; prezentarea se schimbă complet.

---

## 1. AUDIT DESKTOP SEPARAT (1920×800, capturi reale — dovezi în PRODUCT_AUDIT_PPOS_2026.md)

Constatarea centrală: **aproape toate paginile autentificate sunt o coloană mobilă centrată, întinsă pe 1920px.**

| Pagina (desktop) | Lățime utilizată real | Probleme desktop specifice | Scor DESKTOP |
|---|---|---|---|
| Property Hub | ~600px din 1920 (**~31%**) | coloană unică, 6+ ecrane de scroll, zero panouri, formulare inline mereu deschise | **42** |
| Specialist Dashboard | ~1000px centrat | **bottom nav de mobil pe desktop** + header nav simultan; carduri stivuite vertical; zero tabele deși gestionează 27 lucrări | **48** |
| Client Home (nou) | ~880px (hero+copilot) | spațiu mort masiv; nu există panou de context; totul sub fold la conturi active | **58** |
| Client Home (activ) | ~880px | idem + alertele sub tile-uri (informația critică nu rămâne vizibilă) | **60** |
| Marketplace public | ~900px grid 3 col | acceptabil ca browse; filtrele minimale; fără comparație | **68** |
| Imobile Verificate | ~1000px | browse OK; filtrele sub fold; fără sortare vizibilă | **72** |
| Admin (Metronic) | left-nav real | deja workspace; densitate inegală; audit separat ulterior | **75** |
| Pașaport public | coloană conținut | pagină de conținut — coloana e legitimă, dar lateralele pot purta sumarul sticky | **76** |
| Landing | full-width marketing | e pagină de marketing — corect așa | **88** |

**Media desktop autentificat: ~52/100.** Diagnosticul Fondatorului confirmat cu măsurători: mobil întins pe ecran mare.

---

## 2. WORKSPACE MODEL (structura obligatorie a oricărei pagini desktop autentificate)

```
┌────────────────────────────────────────────────────────────┐
│ TOP COMMAND BAR: context (unde sunt) · căutare · acțiune primară · notificări · profil │
├──────────┬─────────────────────────────────┬───────────────┤
│ LEFT NAV │        MAIN WORKSPACE           │ RIGHT CONTEXT │
│ (fix,    │  grid 12 coloane, carduri-unelte│ PANEL (opț.)  │
│ colapsa- │  tabele, liste split view       │ detalii item  │
│ bil)     │                                 │ selectat,     │
│          │                                 │ scor, copilot │
├──────────┴─────────────────────────────────┴───────────────┤
│ BOTTOM STATUS (opțional): stare sistem, progres operații   │
└────────────────────────────────────────────────────────────┘
```
Nicio pagină nu are voie să pară goală. Nicio pagină nu are voie să pară aglomerată.

## 3. REGULI

**Grid System**: container max 1600px · 12 coloane · gutter 24px · breakpoints: <768 mobil (PPOS-006), 768-1279 tabletă (nav colapsată + o coloană+panou), ≥1280 workspace complet, ≥1600 densitate crescută. Interzis: `max-w-2xl mx-auto` ca layout de pagină autentificată pe desktop.

**Navigation**: left nav persistentă (icon+label, colapsabilă la icon), secțiunile rolului; top bar poartă contextul + UN buton primar. Bottom nav = EXCLUSIV mobil. O singură navigație per device.

**Card Rules**: cardul e unealtă — susține o decizie sau dispare; are titlu-decizie, valoarea, și max 1 acțiune; înălțimi aliniate pe rând; niciodată carduri-decorațiuni.

**Table Rules**: orice colecție >5 iteme gestionabilă = tabel/list-view cu: sortare pe coloane · filtre · căutare rapidă · bulk actions (checkbox) · coloane fixe (pin) · meniu contextual (⋯) · navigare tastatură (↑↓ selecție, Enter deschide, / caută) · row → Right Panel (nu pagină nouă).

**Panel Rules**: Right Context Panel 360-420px, închidibil; se deschide la selecție (recunoaștere, nu navigare); conține detaliul + acțiunile itemului; UN panou simultan.

**Sticky Rules**: informația critică (scor, CTA primar, total) rămâne vizibilă la scroll (sticky top bar / sticky summary în panel).

**Information Hierarchy**: stânga-sus = decizia zilei; dreapta = context; densitate crește cu maturitatea rolului (Entry primește calm, Top primește densitate).

---

## 4. REDESIGN PER PAGINĂ (propuneri — spre aprobare)

### 4.1 Specialist Desktop = MISSION CONTROL (ținta principală)
- Top bar: „Astăzi" + KPI strip compact (Cereri noi · În lucru · De încasat · Rating) — mereu vizibil.
- Main: **split view Linear-style** — stânga lista cererilor/lucrărilor (tabel: client, serviciu, buget, stare, vechime; filtre + sortare + bulk), dreapta Right Panel cu detaliul selecției (timeline, chat, acțiuni Acceptă/Propune/Finalizează).
- Sub listă: pipeline sumar (Cockpit) DOAR Advanced+.
- Zero bottom nav pe desktop; zero checklist-uri de onboarding la tier-uri mature (cf. P3a).

### 4.2 Property Hub Desktop = „Casa mea" ca Notion record
- Left sub-nav a casei: Rezumat · Cartea casei (documente = TABEL cu filtre/sortare/bulk) · Twin & Active · Istoric · Pașaport & Partajare.
- Main: secțiunea selectată. Right Panel sticky: **UN scor (Sănătatea casei) + next step + CTA** — vizibil permanent la scroll.
- Formularele (Detalii/Active) devin editare inline pe rând (Airtable-style), nu formular permanent desfășurat.

### 4.3 Client Home Desktop = ghidare cu context
- Main (8 col): Welcome + Next Action hero + Alerts + Recent.
- Right Panel (4 col): starea casei (scor mic + link „Casa mea") + Copilot (1 recomandare).
- Fără tile-uri duplicat; totul deasupra fold-ului la 1920×800.

### 4.4 Marketplace & Imobile Verificate Desktop
- Filtre sticky în stânga (facet panel), rezultate grid/tabel comutabil, sortare vizibilă, comparație (max 3) ca panou. Search-first pentru cumpărător.

### 4.5 Admin Desktop
- Deja left-nav (Metronic). Adoptă: densitate Stripe Admin, tabele cu bulk, search-first (CTRL+K există în backlog). Audit separat DUPĂ rollout client+specialist.

---

## 5. IMPACT ASUPRA FAZELOR
P3b/P3c/P3d livrează fiecare DOUĂ prezentări: desktop workspace (acest document) + mobil task-first (PPOS-006), pe aceleași API-uri. Detaliu efort în `SPEC_DESIGN_ALL_PHASES.md`.
