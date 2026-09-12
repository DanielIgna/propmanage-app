# PRODUCT AUDIT — PropManage PPOS v1.0
**Chief Product Designer · Product Council** · Iunie 2026 · FAZA 1 (fără cod)

> Mandat: `board/PPOS_PRODUCT_OS_MASTER_DIRECTIVE_MISSIONS.md` (verbatim).
> Metodă: audit LIVE pe preview, cu login real pe **9 stări de rol** (Client Junior/Verified/Premium/activ, Specialist Entry/Verified real, vizitator anonim), desktop 1920 + mobil 390, plus inventar de cod (fișier:linie). Zero presupuneri — doar ce s-a văzut pe ecran.

---

## 0. VERDICT EXECUTIV

**Scor global experiență produs: 68/100.** Gate PPOS: 95. Nicio pagină autentificată nu trece gate-ul.

| Zona | Scor | Verdict |
|---|---|---|
| Landing public | 88 | Aproape de gate — cel mai bun ecran |
| Specialist Entry Home | 86 | **Modelul de urmat** — deja construit corect |
| Pașaport public /p/{slug} | 80 | Bun, timeline necontrolat |
| Client Home (cont nou) | 78 | Hero corect, dar aceeași acțiune apare de 3 ori |
| Imobile Verificate | 74 | Conflict de persona buyer/seller |
| Client Home (client activ) | 72 | 3 CTA-uri primare concurente |
| **Marketplace public** | **58** | Badge „REJECTED" public + rating 5★(0) — trust killer |
| **Property Hub (Proprietăți)** | **55** | 10+ carduri, 5 sisteme de scor concurente |
| **Specialist Dashboard (Verified+)** | **52** | 4 sisteme de progres contradictorii + 9 unelte blocate dominante |

**Cauza rădăcină (confirmă diagnosticul Fondatorului):** problema nu e implementarea, ci **arhitectura de experiență** — fiecare feature livrat și-a adăugat propriul card, propriul scor și propriul CTA, fără o ierarhie a atenției. Rezultatul: dashboardurile mature arată ca un admin panel.

---

## 1. CELE 7 PROBLEME SISTEMICE (transversale, mai importante decât orice pagină)

### S1 · Războiul overlay-urilor la primul login — CRITIC
La prima autentificare, utilizatorul primește SIMULTAN: **(1)** RoleTour modal 5 pași care blochează tot ecranul, **(2)** cookie banner permanent sus cu „Accept toate" (cel mai proeminent buton de pe pagină), **(3)** butonul plutitor „Feedback beta" stânga-jos, **(4)** bula de chat dreapta-jos. Patru elemente concurează înainte ca utilizatorul să fi văzut măcar ecranul. Turul descrie funcții pe care un Junior nu le poate folosi încă („Digital Twin, escrow"). **Încalcă direct regula de 10 secunde.**
- Dovadă: capturi client.verified, client@, specialist@ — toate blocate de tur la primul login.
- Pe mobil 390: „Feedback beta" **se suprapune peste bottom nav** (acoperă primul tab), iar bula de chat acoperă conținut (Copilot / Încasări).

### S2 · Șase sisteme de scor pentru proprietar, fără ierarhie — CRITIC
Pe traseul unui singur proprietar există: Cartea casei **30%** · Profil digital **70%** · **PVI** (scor valoare) · Twin Maturity **L3** · Risc **50/100** · Trust Score pașaport. Șase cifre diferite despre aceeași casă, pe aceeași pagină sau la un click distanță, fără să se explice care contează. Utilizatorul nu poate răspunde la „cum stă casa mea?".
- Dovadă: PropertyHubV2 (capturi + `PropertyHubV2.jsx` — `dna-card`, `pvi-score`, `maturity-card`, `risks-card`, „Cartea casei", „Profil digital 70%").

### S3 · Patru sisteme de progres contradictorii pentru specialist — CRITIC
Specialistul VERIFIED real (27 lucrări active, 3.100 RON încasări luna aceasta) vede simultan: „Ghid de pornire — **Nivel: JUNIOR**" · quest „**Primul lead acceptat 0/1**" · „**Configurare cont specialist: 0/6 pași**" (inclusiv „Trimite prima ofertă") · „**Progres către ADVANCED: 100%**". Sistemul îi spune în același ecran că e începător, că nu a trimis nicio ofertă și că e gata de promovare. **Contradicțiile distrug încrederea** — exact metric-ul pe care platforma îl vinde.
- Dovadă: capturi specialist@ + `SpecialistDashboard.jsx` (WelcomeChecklist, QuestPanel, TierToolsPanel, TierProgressWidget importate și randate împreună, L13-33).

### S4 · Funcțiile blocate domină interfața
- Specialist: secțiunea „Unelte avansate" listează **9 unelte cu lacăt** (Filtre, Căutări salvate, Șabloane, Matching prioritar, Aplicare în masă, Support prioritar, Rapoarte white-label...) — un ecran întreg de lucruri pe care nu le poți folosi.
- Property Hub: 10 chips de module din care 3-4 disabled (Documente, Mentenanță, Senzori).
- Client nou: card „Descoperă Digital Twin" (funcție Premium) înainte de a avea măcar o proprietate.
- PPOS: *Hidden is better than disabled.* Max 1 teaser „următoarea deblocare".

### S5 · Aceeași acțiune, repetată de 2-3 ori pe același ecran
- Client nou: „Adaugă proprietatea" apare în **hero CTA + tile-ul «Proprietatea — adaugă prima» + Copilot** (3×).
- Client activ: „Plătește" apare în **hero «Plătește avansul (escrow)» + Noutăți «Plată în așteptare → Plătește»** (2×), plus „Solicită ofertă" (header, lime, primar) și „Vreau ofertă" (upsell, full-width, primar) = **3 CTA-uri primare concurente** pe un ecran.
- Duplicarea navigației: tile-urile Acasă (Lucrări, Proprietatea) duplică tab-urile din header; specialistul are header nav + bottom nav simultan pe desktop.

### S6 · Jargon tehnic netradus în fața clientului
„Ultimele evenimente" pe Property Hub afișează stringuri de sistem: **„Twin dna attribute updated"**, **„Recommendation created"** (engleză, snake-case de event bus). Marketplace public: **„100% reco"**, **„BUN · 50"**, **„EXCELENT · 80"**, **„ENTRY"**. PVI: „PVI ≥ 40 (acum 90)". Clientul nu trebuie să vadă niciodată limbajul intern al sistemului.

### S7 · Date de test și stări imposibile expuse public — TRUST KILLER
- Marketplace public: card „TEST Phase7 Spec" cu badge **„REJECTED"** vizibil oricui; „Ion Popescu ★5 (0)" — **rating 5 cu 0 recenzii**.
- Pașaport public: timeline cu 12+ intrări „TEST_Flow / TEST_AuditReq_..." identice, necolapsate.
- Regula de robustețe: UI-ul nu are voie să afișeze rating fără recenzii, specialiști respinși, sau timeline nelimitat — indiferent de datele din DB. (Curățarea demo la lansare există — EO-026 purge — dar prezentarea trebuie să fie defensivă.)

---

## 2. RĂSPUNSUL LA ÎNTREBAREA PPOS: „CARE ESTE UNICA ACȚIUNE DE AZI?" (per rol)

| Rol | Starea reală | UNICA acțiune azi | Ce vede acum în plus (de eliminat/ascuns) |
|---|---|---|---|
| Client Junior (0 proprietăți) | cont nou | **Adaugă prima proprietate** | tile-uri Solicită/Lucrări/Întreabă AI, Copilot, Descoperă Twin, tur 5 pași |
| Client Junior (1 proprietate, 0 documente) | onboarding | **Adaugă primul document** (apoi: cere audit) | marketplace, upsell design |
| Client Verified (audit/documente) | activ | **Vezi sănătatea casei + următoarea recomandare** | scoruri paralele (PVI/Maturity/Risc separate) |
| Client Premium (twin/abonament) | matur | **Acțiunea din Copilot (1, nu 3)** | tot restul devine secundar |
| Client cu lucrare activă | tranzacție | **Plătește avansul (escrow)** | Solicită ofertă, upsell, Descoperă — toate sub |
| Specialist Entry | 0 joburi | **Verifică-ți contul → acceptă prima oportunitate** | (deja corect — modelul de urmat) |
| Specialist Junior | 1-5 joburi | **Acceptă următoarea oportunitate** | quests multiple, cockpit, unelte blocate |
| Specialist Verified | activ | **Răspunde la cererile noi (1 nouă)** | ghid de pornire, config 0/6, quest „primul lead" |
| Specialist Advanced/Premium/Top | volum | **Pipeline: următoarea lucrare de livrat** | orice element de onboarding |
| Vizitator (landing) | anonim | **Creează contul gratuit** | (corect deja) |
| Cumpărător (Imobile Verificate) | anonim | **Caută/filtrează imobile** | „Vinde-ți imobilul" ca CTA primar |
| Admin | operare | Prioritatea zilei din CEO Briefing | (în afara scope-ului beta; audit separat ulterior) |

---

## 3. AUDIT PER PAGINĂ (scorecard complet)

Format scoruri: Claritate / Simplitate / Încredere / Venit / Mobil / Accesibilitate / Performanță / Sarcină cognitivă → **FINAL**.

### 3.1 · `/client` — Client Home, cont nou (HomeV2.jsx)
- **Scop**: activarea primului pas (proprietate). **User primar**: Client Junior. **Obiectiv business**: activare (North Star: Trusted Properties).
- **CTA primar**: „Adaugă proprietatea" (hero) ✓ corect ales. **CTA secundare concurente**: tile ×4, Copilot, Descoperă.
- **Probleme UX**: S1 (tur+cookie+feedback+chat la primul login), S5 (aceeași acțiune ×3), S4 (Descoperă Twin prematur), „Întreabă AI"/„Solicită" nefolosibile fără proprietate (încalcă „never show features users cannot use").
- **Probleme IA**: coloana Copilot are aceeași greutate vizuală ca hero-ul; ierarhia PPOS (Welcome→Next→Progress→Alerts→Recent→Optional) parțial respectată.
- **Oportunitate venit**: fiecare element eliminat crește probabilitatea finalizării pasului 1 → alimentează funnel-ul audit (prima monetizare).
- **De eliminat (stare Junior)**: tile-urile ×4, Copilot, Descoperă. **De amânat**: turul (devine buton „?" on-demand). **De păstrat**: hero + progres 1/3.
- **Scoruri**: 80/75/85/70/80/75/90/78 → **FINAL 78**

### 3.2 · `/client` — Client activ cu lucrare (HomeV2.jsx)
- **Scop**: finalizarea tranzacției active. **CTA primar corect**: „Plătește avansul (escrow)".
- **Probleme**: S5 — 3 CTA-uri primare (Plătește hero, Solicită ofertă header, Vreau ofertă upsell) + duplicat Plătește în Noutăți; „Lucrări 107 active" (zgomot demo, dar și design: numărul brut nu ajută); upsell-ul „Recomandat pentru casa ta" are CTA vizual identic cu cel tranzacțional.
- **De reordonat**: Noutăți (alerte) trebuie să fie imediat sub hero, înaintea tile-urilor; upsell-ul devine link discret cât timp există o plată în așteptare.
- **De unificat**: hero + item-ul din Noutăți despre aceeași plată = un singur element.
- **Scoruri**: 72/68/82/75/70/72/88/65 → **FINAL 72**

### 3.3 · `/client` tab „Proprietăți" — Property Hub (PropertyHubV2.jsx, 562 linii)
- **Scop declarat**: dashboardul complet al proprietății. **Realitate**: pagină-fluviu cu 10+ carduri de rang egal.
- **Inventar componente (de sus în jos)**: foto+selector · Cartea casei 30% + „Adaugă document" · Pașaportul casei (QR, link, share, confidențialitate, statistici) · card DNA (4 bare 15/15) · 10 chips module (3-4 disabled) · „Profil digital 70%" · Ultimele evenimente (jargon EN — S6) · Twin Maturity L0-L5 · „Reînnoiește Auditul Tehnic" · Riscuri estimate (risc 50/100) · Activele casei (4 sloturi) · Detaliile casei (formular).
- **Probleme**: S2 (5 scoruri pe o pagină), fără un CTA primar unic, fiecare card cu propriul CTA; formularul „Detaliile casei" mereu desfășurat; „Ultimele evenimente" în limbaj de mașină.
- **Justificare per componentă (de ce există / unde merge)**:
  - Cartea casei (scor+next step) → **RĂMÂNE ca element primar UNIC** (e deja formulat ca next-step engine).
  - Pașaport → secțiune colapsată „Partajează casa" (acțiune ocazională, nu zilnică).
  - DNA + Profil digital + PVI + Maturity + Risc → **se CONTOPESC** într-un singur „Scor de sănătate + valoare" cu drill-down (detaliile rămân, ierarhizate).
  - Active + Detalii → secțiune colapsată „Datele casei" (se completează o dată, nu se privește zilnic).
  - Evenimente → „Istoric" (colapsat, tradus uman).
- **Scoruri**: 55/45/75/60/55/65/80/40 → **FINAL 55** · **ținta principală de redesign pentru clienți**

### 3.4 · `/specialist` — Specialist Dashboard, tier VERIFIED+ (SpecialistDashboard.jsx, 546 linii)
- **Scop**: operarea zilnică a specialistului. **Realitate**: admin panel cu tot ce s-a construit vreodată.
- **Inventar**: Ghid de pornire (JUNIOR!) · Recenzii de trimis · „Astăzi ai" 4 stats · Pipeline & Bani COCKPIT (4 metrici + piață) · Business Assistant · Quest-uri ×3 (voucher 30/50/90%) · Unelte avansate (9 blocate — S4) · Progres către ADVANCED 100% · Configurare cont 0/6 · listă cereri + filtre + notificări. Navigare dublă header+bottom pe desktop.
- **Probleme**: S3 (4 sisteme de progres contradictorii — bug de stare, nu doar design: checklist-urile nu citesc realitatea contului), S4, S6.
- **Justificare per componentă**: „Astăzi ai" + prima cerere nouă = nucleul (rămân). Cockpit → doar Advanced+. Quests+Ghid+Config → **UN singur sistem de progres** (tier progress), care dispare complet la VERIFIED+ dacă totul e îndeplinit. Unelte avansate → ascunse; max 1 rând „Următoarea deblocare la nivelul X".
- **Scoruri**: 50/40/60/65/55/65/85/35 → **FINAL 52** · **ținta principală de redesign pentru specialiști**

### 3.5 · `/specialist` — tier ENTRY (SpecialistEntryHome.jsx, 98 linii)
- **Modelul corect, deja în producție**: Salut + „3 pași" + oportunități cu UN CTA „Acceptă" + escape hatch discret „Dashboard complet". Respectă Hick, Miller, progressive disclosure, mobile first.
- Minusuri mici: navigare dublă moștenită; „Feedback beta" peste bottom nav pe mobil (S1).
- **Scoruri**: 90/92/85/80/82/85/90/88 → **FINAL 86** · **standardul pe care îl extindem la toate tier-urile**

### 3.6 · `/` — Landing
- Hero „Cartea de service a casei tale." + 1 CTA „Creează contul gratuit" ✓. Trust chips ✓.
- Probleme: cookie banner-ul lime „Accept toate" este vizual la fel de puternic ca CTA-ul hero și persistă pe toate paginile până la decizie (S1); chat bubble pe landing concurează colțul.
- **Scoruri**: 92/90/90/85/85/85/90/88 → **FINAL 88**

### 3.7 · `/imobile-verificate` — Estate Browse
- Hero puternic („Zero surprize"), dar **conflict de persona**: pagina e pentru CUMPĂRĂTORI, iar CTA-ul primar e „Vinde-ți imobilul cu noi" (persona vânzător). Căutarea — adevărata acțiune primară — e sub fold.
- Carduri: 4 badge-uri suprapuse pe fotografie (VERIFIED TWIN + Trust A+ + 3D Twin + Vânzare) + „100% reco" (jargon — S6).
- **Recomandare**: search-first (filtrele urcă în hero), „Vinde-ți imobilul" devine secundar/persistent discret; max 2 badge-uri pe card (Trust level + Twin), restul în detaliu.
- **Scoruri**: 78/72/82/70/75/75/85/70 → **FINAL 74**

### 3.8 · `/marketplace` — Specialiști verificați (public)
- **CRITIC (S7)**: badge „REJECTED" public, „TEST Phase7 Spec", rating „★5 (0)", jargon „BUN · 50". Pagina care trebuie să vândă încredere afișează contra-dovezi.
- **Reguli de prezentare defensivă (fără schimbări de API)**: nu se afișează specialiști neaprobați; rating-ul apare doar la ≥1 recenzie („Nou pe platformă" altfel); scorurile interne (50/80) nu se afișează public.
- **Scoruri**: 65/70/35/55/70/72/85/60 → **FINAL 58**

### 3.9 · `/p/{slug}` — Pașaportul public al casei
- Structură corectă (validată CX-3 la 92+ pe UI); problema noua: **timeline nelimitat** — 12+ intrări identice fără colaps, iar textul „Lucrare finalizată prin PropManage, cu plată protejată" se repetă identic (zgomot). Colaps la 5 + „Vezi tot istoricul (N)". 
- **Scoruri**: 82/78/85/75/80/82/88/72 → **FINAL 80**

### 3.10 · Alte observații rapide
- **RequestWizard („Solicită")**: 1 scop, ok — de re-verificat la Faza 3.
- **Document Vault**: flux bun (CX-2 validat), rămâne; intră sub secțiunea „Cartea casei".
- **/client Lucrări (JobsV2)** și **Setări**: în afara top-priorităților; auditate la Faza 4 (navigație).
- **Admin**: exclus din beta scope-ul PPOS imediat (utilizatori interni); audit separat după rollout-ul client+specialist.

---

## 4. NOUA ARHITECTURĂ DE INFORMAȚIE (Faza 2 — propunere spre aprobare)

Detaliu complet: `/app/memory/product/02_INFORMATION_ARCHITECTURE.md` + `03_DASHBOARD_OS.md` + `05_PROGRESSIVE_DISCLOSURE.md`. Sinteza:

### 4.1 Ordinea unică a oricărui dashboard (legea PPOS)
`1 Welcome → 2 Next Action (UN CTA) → 3 Progress (UN sistem) → 4 Alerts → 5 Recent → 6 Optional/Descoperă`. Niciodată altă ordine. Un singur element plutitor pe ecran.

### 4.2 Matricea de dezvăluire progresivă (client — bazată pe DATE, nu pe etichete)
| Etapă (dovezi) | Vede | Ascuns |
|---|---|---|
| J0: 0 proprietăți | Welcome + Adaugă proprietatea. Atât. | tot restul |
| J1: proprietate, 0 documente | + Cartea casei (pasul 2: document) | marketplace, AI, twin |
| J2: documente → cere audit | + Solicită audit (pasul 3) | |
| V: audit/verificat | + Sănătatea casei (scor UNIC) + Recomandări + Istoric | |
| P: twin/abonament | + Digital Twin + Marketplace + Mentenanță + Copilot AI | — |

### 4.3 Specialist — un singur sistem de progres
Tier progress (ENTRY→TOP) absoarbe ghidul, quest-urile și „configurare cont": un singur card „Progresul tău", cu maximum următorii 2 pași reali (derivați din starea contului — niciodată „primul lead" pentru cineva cu 27 lucrări). ENTRY home devine șablonul tuturor tier-urilor, la care se adaugă module pe măsură ce se deblochează: Junior (+istoric lucrări), Verified (+cereri noi & recenzii), Advanced (+Cockpit pipeline), Premium/Top (+Capabilități, profil premium, rapoarte). Uneltele blocate: invizibile, cu un singur rând „Următoarea deblocare".

### 4.4 Property Hub → „Casa mea" în 3 straturi
1. **Sus**: UN scor („Sănătatea casei") + UN next step + CTA-ul lui. 
2. **Mijloc**: 3 secțiuni colapsate — „Cartea casei" (documente+pașaport+share) · „Casa în detaliu" (twin, active, date declarate) · „Istoric" (evenimente traduse uman).
3. **Jos**: Descoperă/upsell contextual (max 1).
PVI, Maturity, Risc devin drill-down în „Sănătatea casei" (datele și API-urile rămân neatinse — se schimbă DOAR prezentarea).

### 4.5 Igiena overlay-urilor (prima implementare, quick win)
Tur → buton „?" on-demand (nu se autodeclanșează); cookie banner compact jos, o singură apariție; „Feedback beta" mutat în meniu/Setări pe mobil (nu peste nav); un singur element plutitor: chat-ul. 

---

## 5. FAZAREA IMPLEMENTĂRII (așteaptă GO per fază)

| Faza | Conținut | Efort | Impact |
|---|---|---|---|
| **P3a — Igienă & onestitate** | S1 overlays, S3 fix progres contradictoriu specialist, S7 prezentare defensivă marketplace/pașaport, S6 traduceri jargon | mic | uriaș (trust) |
| **P3b — Client Dashboard OS** | matricea 4.2 pe HomeV2 (stări J0→P), un CTA/ecran | mediu | activare |
| **P3c — Specialist Dashboard OS** | modelul Entry extins pe toate tier-urile, un progres unic | mediu | retenție |
| **P3d — Property Hub „Casa mea"** | restructurarea 4.4 în 3 straturi | mediu-mare | claritate+venit |
| **P4 — Navigație** | eliminarea duplicării header/bottom/tiles | mic | consistență |
| **P5 — Mobile** | thumb-zone, overlap-uri, re-testare 390px | mic | mobile first |
| **P6 — Re-audit & rollout** | re-scoring fiecare pagină, gate 95 | mic | gate |

**Garanții**: zero schimbări de API/DB/permisiuni/logică — exclusiv presentation layer. Feature flag per dashboard (mecanism existent `pm_client_ui`) pentru rollback instant.

---

*Toate scorurile sunt oneste (Truth Engine D161): măsurate pe capturi reale din preview, nu estimate. Scorecard live: `/app/memory/product/audits/PAGE_SCORECARD.md`.*
