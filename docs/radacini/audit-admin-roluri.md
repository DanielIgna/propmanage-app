# Rădăcini × PropManage — audit Admin, Knowledge Center, roluri și interfețe

Branch: `radacini` · Data: 2026-10-13 · Continuă [audit-agro-faza0.md](audit-agro-faza0.md). **Nu s-a implementat nimic.**
Etichete: CONFIRMAT (văzut în cod) · PARȚIAL · LIPSĂ · NECESITĂ VALIDARE.


> **Erată (2026-10-13, reverificare la nivel de effort ridicat).** Auditul inițial a fost făcut la effort mediu. O reverificare cu dovezi din cod a găsit afirmații greșite sau imprecise, corectate mai jos în text (marcate *[corectat]*):
> - **Evenimentele `radacini.*` NU apar automat în admin.** `event_bus.emit` scrie doar în `activity_events` (`event_bus.py:60-77`). Activitate Live citește `db.events` (`routes/admin_console.py:700`), User Timeline agregă din users/requests/payments/reviews, Notification Center din `command_center_recos`/`audit_anomalies`, iar Automation Center are 3 șabloane fixe. Integrarea cere cod: o filă/sursă Rădăcini.
> - **Acțiunile Rădăcini NU ajung în `admin_actions_log`.** Trebuie apelat explicit `admin_console.audit()` (`admin_audit_log`) sau `sub_admin_deps._log_action`.
> - **Scope-urile sub-adminilor sunt aplicate de un middleware global** (`middleware_scope.py`, ~30 de prefixe `/api/admin/*`), plus `require_admin_scope` în 3 fișiere. Prefixele nemapate trec pentru orice sub-admin, iar `/api/radacini/*` nu e acoperit.
> - **Tabelele `app.radacini_*` nu sunt create prin migrație.** `pgmongo` le creează la prima scriere (`pgmongo.py:783-852`), doar cu index GIN, fără indexuri pe expresii.
> - **Escrow:** doar `requests.py:294` e un flag demo. `routes/payments.py` încasează real prin Stripe Checkout (când cheile sunt reale), iar `projects.py` are tranșe din wallet. Eliberarea e doar evidență internă (`wallet_balance`), fără payout.
> - **Admin:** 15 secțiuni (10 business, 5 infra), 113 intrări (`AdminLayoutMetronic.jsx:90-330`). „Joburi programate” e intrare în Dashboard Business.
> - **Alte precizări:** `models.py` nu are `ROLES` (are `PUBLIC_REGISTER_ROLES`). KC verifică fondatorul la `knowledge_center.py:171`. KYC permite upload doar specialiștilor. Exportul GDPR nu include colecțiile Rădăcini. Quest-urile sunt legate de vouchere și de rolurile client/specialist. XOS are doar suprafața `client_home`. `service_contracts.py` are semnătură pentru ambele părți și mediere de operator. Rate limiting-ul se aplică doar pe `/api/public`, `/api/p`, `/api/track`, `/api/go`.

---

## 1. Rezumat

- **Adminul PropManage e mare:** 2 zone (Business și Infrastructure), 15 secțiuni (10 business, 5 infra), 113 intrări în meniu. *[corectat]*
  - Sursa: `frontend/src/views/admin/AdminLayoutMetronic.jsx:90-345` (`NAV_SECTIONS`).
- **Permisiunile nu se aplică la fel de strict peste tot:**
  - **Zonele și rolurile de admin sunt doar pregătite, nu aplicate**: toți adminii văd ambele zone. Sursa: `backend/routes/admin_zones.py:1-5`.
  - **Scope-urile sub-adminilor** (`testing/frontend/backend/security/ai/ops`) sunt aplicate de un **middleware global** pe ~30 de prefixe `/api/admin/*` (`middleware_scope.py`), plus `require_admin_scope` în 3 fișiere. Prefixele nemapate trec pentru orice sub-admin, iar `/api/radacini/*` nu e acoperit. *[corectat]*
  - Restul rutelor verifică doar `require_role("admin")`.
  - `ownerOnly` / `superAdminOnly` doar ascund intrările din meniu, în frontend.
- **Knowledge Center** e accesibil doar fondatorului (`OWNER_EMAIL`). Citește toate fișierele `*.md` din `docs/` și `memory/`, plus un registru JSON de relații (50 de noduri, 49 de muchii).
  - **Documentele Rădăcini din `docs/radacini/` apar deja automat.**
- **Operatorul** e azi un validator de teren pentru PropManage: Digital Twin, neconformități, publicarea imobilelor verificate.
  - Primește **acces complet la funcțiile plătite, fără abonament** (`entitlements.py:204`). Nu trebuie să-i dăm rolul global în Rădăcini.
- **Propunere de bază:** adăugăm o a treia dimensiune, **Produs** (PropManage | Rădăcini), alături de Zonă.
  - Infrastructura rămâne comună.
  - Business-ul se filtrează pe produs.
  - Rolurile Rădăcini (operator, coordonator, manager) sunt **pe produs și pe arie geografică**, nu roluri globale.

---

## 2. Cum funcționează azi accesul în admin

| Nivel | Mecanism | Unde | Status |
|---|---|---|---|
| Rol de utilizator | `user.role` ∈ client / specialist / admin / operator / franchise_admin / marketplace_partner | `deps.py:75`, `entitlements.py:204`, `routes/marketplace_partners.py:17` | CONFIRMAT |
| Super-admin și sub-admini | `admin_scope` (`general` = super-admin) + `admin_seniority` | `sub_admin_deps.py:1-33` | CONFIRMAT · aplicat doar în 3 fișiere |
| Zone și roluri de zonă | 11 roluri predefinite (Business Administrator, Finance Manager, Developer…) | `frontend/src/config/adminZones.js:30-41`, `routes/admin_zones.py` | **PREGĂTIT, NEAPLICAT** |
| Owner / Founder | `ownerOnly` / `superAdminOnly` în meniu; Knowledge Center verifică `OWNER_EMAIL` pe server | `AdminLayoutMetronic.jsx`, `routes/knowledge_center.py:15` | CONFIRMAT (KC pe server; restul doar în interfață) |
| Aprobări și acțiuni critice | aprobări pentru juniori, Founder Gate, jurnalul de impersonare | `admin_approvals.py`, `founder_gate_admin.py`, `impersonation.py` | CONFIRMAT |
| Multi-tenant (franciză) | `X-Tenant-ID` → `user.tenant_id` → `main`; `franchise_admin` vede doar tenantul lui | `tenancy.py:1-6,183` | PARȚIAL (fundație, fără migrare de date) |
| Acces la funcții plătite (entitlements) | nivelurile FREE / CLIENT_BASIC / PRO / PREMIUM → funcții; adminul, operatorul și franciza au acces la tot fără plată | `entitlements.py:1-16` | CONFIRMAT |
| Vizibilitatea interfeței | Page Registry (`allowed_roles/tiers/device/feature_flag`), XOS (layout-uri, reguli DACĂ→ATUNCI), `site_menu` din CMS | `routes/pages_registry.py`, `routes/xos.py`, `routes/site_menu.py` | CONFIRMAT |

**Consecință pentru Rădăcini:** dacă adăugăm acum un „admin Rădăcini” cu `role=admin`, el vede **tot** adminul PropManage. Înainte de a da acces cuiva care nu e fondatorul, trebuie ori aplicate zonele, ori folosit un rol de personal propriu Rădăcini (vezi §7).

---

## 3. Zona Business: fiecare secțiune, ce face și ce înseamnă pentru Rădăcini

| Secțiune (intrări) | Ce face azi | Pentru Rădăcini | Cum |
|---|---|---|---|
| **Dashboard Business** (≈30: CEO Dashboard, Briefing, Command Center, Notification Center, Business Health, Operations Center, Automation, Control Tower, Activitate Live…) | panouri de executiv și de operare, majoritatea agregate cu AI | **Selectiv** | Refolosim **Notification Center**, **Automation Center** (reguli DACĂ→ATUNCI), **Activitate Live** și **Control Tower** **cu cod de integrare**: `event_bus` scrie doar în `activity_events`, pe care aceste panouri nu îl citesc *[corectat]*. Panourile CEO, Evolution, War Room și PropBenefits nu au legătură cu Rădăcini. |
| **Utilizatori** (Toți userii, User Timeline, Verificare specialiști, KYC, Beta Testers, Progresie, Experience Tiers) | gestionarea conturilor, verificare, niveluri | **Da (Toți userii, Timeline, KYC)**; Progresie și Tiers nu | Același cont; în fișa utilizatorului adăugăm o filă „Rădăcini” (interese, comunități, terenuri). KYC primește un tip de document nou: dovada dreptului asupra terenului. |
| **Cereri & Proiecte** (Proiecte, Dispute & NC, Construction) | fluxurile de servicii pentru casă | **Nu direct** | Rădăcini primește propria secțiune „Proiecte agricole”. Disputele le refolosim mai târziu, ca tipar. |
| **Financiar** (Finanțe & Escrow, Financial Cockpit MRR/ARR) | tranzacții, escrow (doar demo), venit recurent | **Mai târziu** | Cât timp MVP-ul nu are plăți, nu e cazul. Când abonamentul 5 €/lună devine activ: o linie „Rădăcini” în Financial Cockpit. |
| **Marketplace & Parteneri** (Strategic, Marketplace Intel, City Partners, Catalog Materiale, Marketplace Partners) | parteneri comerciali și catalogul lor | **Adaptare (faza 2)** | Tiparul de portal pentru parteneri (`/partner/*`, `marketplace_partner`) e bun pentru furnizori de semințe și unelte, piețe locale, primării și școli. |
| **Imobile** (Imobile Verificate, House Health, Experience Spaces, HartaBlocuri) | domeniul imobiliar | **Nu**; doar tiparul de harta-observabilitate | Terenurile nu stau aici; sunt în secțiunea Rădăcini. |
| **Conținut** (SEO, CMS texte, Template-uri Email, Zone Acoperire, Manual de Operare, Documentație) | conținut și comunicare | **Da** | CMS și email cu prefixul `radacini.*`; în Zone Acoperire adăugăm **comunele din Cluj**; o pagină de SEO public pentru Rădăcini când va exista. |
| **Marketing & Growth** (≈9, cu mult AI) | campanii, intelligence, leads | **Mai târziu** | Campaniile cu declanșare automată se pot folosi pentru onboarding-ul membrilor. Restul nu e pentru pilot. |
| **Suport & Compliance** (Aprobări, GDPR Pack, Trust Score) | conformitate | **Da (GDPR, Aprobări)** | Intrări ROPA și DPIA noi: locația terenurilor, minorii din gospodării. Aprobări pentru verificarea terenurilor. |
| **Statistici & KPI** (Analytics, Growth/Lead Intel, Learning, BI, A/B) | analiză | **Selectiv** | Un set mic de KPI-uri ale pilotului (vezi §8). Restul e prea mult pentru pilot. |

## 4. Zona Infrastructure & Dev: comună, nu se duplică

| Secțiune | Ce face | Pentru Rădăcini |
|---|---|---|
| **Sistem & Configurări** (Setări platformă, Control Administrare, Feature Configurator) | setări globale, flag-uri, quest-uri și vouchere | **Comun.** Flag-ul `RADACINI_ENABLED` se poate muta aici. Quest-urile sezoniere vin în faza 2 de gamification. **Voucherele nu**, pentru că au valoare economică. |
| **Security & Audit** (Audit Log, Impersonări, AI Security, Audit Juridic IT, Sub-admini, Admin Accounts, Founder Gate) | securitate | **Comun.** Acțiunile Rădăcini ajung în jurnalul admin doar dacă apelăm explicit `admin_console.audit()` prin `bridge.py` *[corectat]*. Sub-adminii primesc scope-ul nou `radacini`. |
| **AI & Engineering Lab** (≈14: AI Investigator, Brain, Autonomy, Orchestrator, Design Studio…) | ecosistemul AI intern | **Nu, pentru pilot.** Costă (LLM și egress). Singura excepție utilă mai târziu: un asistent agronomic prin `llm_chat.py`. |
| **Development & QA** (ToDo, Tester manual, QA Copilot, Playbook, Docs, Bug Memory, Demo Tools și Demo Accounts) | dezvoltare | **Comun.** Conturi demo Rădăcini (proprietar, cultivator, consumator, operator) prin Demo Accounts; scenarii Rădăcini în QA Playbook. |
| **IT Collaborators Hub** | echipa IT | **Comun**, fără schimbări. |
| **Joburi programate** (`scheduler_admin`) | cron | **Comun.** Joburi Rădăcini puține: expirarea ofertelor, reamintiri pentru zilele de lucru. Atenție la egress (vezi `e45e4cb`). |

---

## 5. Knowledge Center: ce este și cum îl folosim

| Fapt | Dovadă | Status |
|---|---|---|
| Acces exclusiv fondator, verificat pe server | `routes/knowledge_center.py:171` *[corectat]* | CONFIRMAT |
| Citește recursiv `docs/**/*.md` și `memory/**/*.md`; în producție, `docs/` și `memory/` sunt copiate în imagine | `knowledge_center.py:187-191`, `backend/Dockerfile:25-26` | CONFIRMAT |
| Starea documentelor (Draft → Review → Active → Archived) e calculată din evidențe: referințe din cod, aprobarea fondatorului | `knowledge_center.py:3-6` | CONFIRMAT (n-am testat la rulare) |
| Registrul de relații e un JSON editat manual: 50 de noduri, 49 de muchii | `backend/data/enterprise_registry.json` | CONFIRMAT |
| Function map, coverage și istoric | endpoint-urile `/api/founder/knowledge/*` (15) | CONFIRMAT |

**Propunere**
1. Ținem toată documentația Rădăcini în `docs/radacini/`; e deja vizibilă în KC. Adăugăm `DECISION_REGISTER` pentru Rădăcini (cele 9 decizii din primul audit).
2. Adăugăm în `enterprise_registry.json` noduri `radacini:*` (module, colecții, rute) și muchii spre infrastructura comună (`auth`, `notifications`, `kyc`, `event_bus`). Așa harta arhitecturii arată legăturile reale.
3. Etichetăm nodurile cu `product: propmanage|radacini`, ca filtrarea să meargă în KC și Enterprise Explorer.
4. KC rămâne doar al fondatorului. Pentru echipa Rădăcini folosim **Documentație & Training** (`/admin/documentation`) cu un ghid de operare pentru pilot.

---

## 6. Roluri și interfețe: cine ce vede și ce poate face

Principiul: **un singur cont, mai multe „pălării”.** Rolul global PropManage nu se schimbă. Ce face cineva în Rădăcini vine din *interese* (pentru membri) și din *atribuiri cu arie* (pentru personal).

| Cine | Cum îl identificăm | Interfața | Ce vede | Ce poate face | Refolosește |
|---|---|---|---|---|---|
| **Vizitator** | nelogat | pagini publice `/radacini/*` (SSR) | hartă cu terenuri (locație aproximativă), comunități, evenimente, produse disponibile | să se înscrie; să rezerve după cont | SSR, `PmMap`, SEO |
| **Membru** | `client` + `radacini_members.interests[]` | `/radacini` (shell-ul existent) | panou adaptat intereselor: *Cultiv* / *Consum* / *Am teren* / *Vând-schimb* / *Comunitate* | își alege interesele, gospodăria, comunitatea | Auth, XOS și Page Registry pentru vizibilitate |
| **Proprietar teren** | interesul `land` + KYC aprobat pentru teren | fila „Terenurile mele” | terenurile lui, cererile, acordurile, proiectele de pe teren, partea din recoltă | publică, acceptă sau refuză, semnează, primește alocarea | KYC adaptat, `PmMap`, notificări |
| **Cultivator** | interesul `grow` | „Proiectele mele” | proiecte, plan de culturi, calendar, contribuțiile lui | cere teren, înregistrează activități și contribuții | tiparul de proiecte și de calendar |
| **Consumator** | interesul `consume` | „Piața locală” | listări din apropiere, rezervări, istoric | rezervă, ridică, evaluează | notificări, recenzii (adaptat) |
| **Coordonator comunitate / proiect** | atribuire în `radacini_project_members.role=coordinator` sau în comunitate | aceleași pagini, cu acțiuni suplimentare | tot proiectul sau comunitatea | confirmă contribuții, măsoară recolta, organizează zile de lucru, propune decizii | — |
| **Specialist agricol** (agronom, mecanizator) | `specialist` PropManage + capabilități agricole | portalul specialist existent + o filă Rădăcini | cereri de lucrări din proiectele agricole | ofertă, execuție, recenzie | **Capability Engine** (`routes/capability_engine.py`) și fluxul cereri/oferte, în faza 2 |
| **Partener** (furnizor, piață, primărie, școală) | `marketplace_partner` sau un tip nou de partener | `/partner/*` | comunitățile din aria lui, nevoi agregate (semințe, unelte) | oferte, evenimente educaționale | portalul de parteneri, în faza 2 |
| **Operator Rădăcini** | `radacini_staff{role:operator, area:[comune]}` | `/radacini/operator` | coada de verificări din aria lui | vezi §7 | tiparul `operator_twins` (coadă, validare) |
| **Manager Rădăcini** | sub-admin `admin_scope=radacini` | admin, secțiunea Rădăcini | toate datele Rădăcini, fără restul PropManage | moderare, aprobări, configurare, KPI-uri | sub-admini, aprobări, audit |
| **Super-admin (tu)** | `admin_scope=general` | tot adminul | tot | tot | — |

**Cum construim interfața membrului**
- Un singur panou `/radacini` cu **carduri care apar după interese.** Varianta cu XOS (`radacini_home`) **cere modificare în cod comun**, pentru că registrul XOS are doar `client_home` *[corectat]*. Implementat: cardurile sunt alese în cod după interese, fără XOS.
- **Mod asistat:** un operator poate crea anunțul unui proprietar în vârstă, cu acordul lui înregistrat. La țară asta contează mult.
- Pe mobil: mai întâi telefonul, cu acțiunile mari la vedere (marchează activitatea, fotografiază recolta, confirmă ridicarea).

---

## 7. Operatorul: azi și în Rădăcini

**Azi (CONFIRMAT)**
- `operator_twins.py`: coadă de validare, validarea log-urilor, creare și validare de Digital Twin.
- `operator.py`: semnalează neconformități, pe care adminul le rezolvă.
- `verified_estate.py`: creează și publică anunțuri de imobile verificate (13 endpoint-uri cu `admin|operator`).
- Interfață `/operator` (`App.js:394`).
- **Bypass total al accesului la funcții plătite** (`entitlements.py:204`).

**Rolul propus în Rădăcini: „operator de teren”, verigă de încredere locală**
1. **Verifică terenul:** vizită sau apel, poze, confirmă suprafața, accesul și apa. Starea terenului devine `verified`.
2. **Onboarding asistat:** creează terenul sau oferta în numele proprietarului, cu consimțământ înregistrat.
3. **Martor la măsurarea recoltei,** când părțile o cer. Reduce conflictele la împărțire.
4. **Puncte de ridicare:** le validează și le ține la zi.
5. **Neconformități:** semnalează probleme (teren abandonat, nerespectarea acordului) spre managerul Rădăcini; tiparul vine din `operator.py`.

**Implementare recomandată:** colecția `radacini_staff` (rol + arie de comune) și o dependență `require_radacini_staff("operator")`. **Nu** folosim `role=operator` global: ar da acces la Digital Twin și la imobilele verificate, plus acces gratuit la funcțiile plătite din PropManage.

---

## 8. Cum le conectăm: soluții propuse

1. **Dimensiunea „Produs” în admin**
   - `product` se adaugă în `NAV_SECTIONS`, nu doar `zone`.
   - În antet apare un comutator **Produs: PropManage | Rădăcini**, independent de comutatorul Business | Infra.
   - Infra arată la fel pentru ambele produse.
   - Pentru Rădăcini, zona Business conține doar secțiunea sau secțiunile Rădăcini, plus cele comune: Utilizatori, Conținut, Suport & Compliance.
2. **Secțiunea admin „Rădăcini” (zona business), 6 intrări:**
   - Membri & Comunități;
   - Terenuri & Verificări (coada operatorilor);
   - Proiecte & Acorduri;
   - Recoltă & Piață;
   - Personal (operatori, coordonatori, arii);
   - KPI-urile pilotului: terenuri publicate și verificate, acorduri semnate, proiecte active, kg recoltate, rezervări finalizate, membri activi.
3. **Aplicarea permisiunilor** (precondiție înainte de orice manager Rădăcini care nu e fondatorul):
   - `radacini` intră în `ALLOWED_SCOPES` (`sub_admin_deps.py:28`);
   - toate rutele admin Rădăcini folosesc `require_admin_scope("radacini","general")`;
   - adăugăm rolul de zonă `radacini_manager` (Business, product=radacini) și **activăm verificarea zonelor pe server**, măcar pentru rutele noi.
4. **Bus-ul de evenimente:** fiecare acțiune Rădăcini emite `radacini.*` prin `event_bus.py`, dar evenimentele ajung doar în `activity_events` *[corectat]*. Pentru Activitate Live, User Timeline sau Notification Center e nevoie de o sursă nouă, adică modificare aprobată în cod comun, sau de un flux propriu în secțiunea admin Rădăcini (recomandat).
5. **Meniu și interfață configurabile:** `site_menu` cu cheia `radacini` (meniu separat), Page Registry pentru paginile Rădăcini, XOS pentru cardurile din panou.
6. **Knowledge Center:** nodurile din registru și eticheta `product`, ca în §5.
7. **Legături între produse, alese conștient:**
   - specialist PropManage ↔ lucrări agricole (Capability Engine);
   - un proprietar de casă care e și proprietar de teren (același cont).
   - **Nu legăm:** Digital Twin, House Health, Experience Tiers, Lead Credits, AI Lab.
8. **Multi-tenant mai târziu:** tenancy rămâne pentru franciză. Extinderea în alte județe se face prin `area` la personal și comunități, nu prin tenant. Se reevaluează după pilot (NECESITĂ VALIDARE).

---

## 9. Riscuri

- **Permisiunile admin nu sunt aplicate** (zonele sunt doar pregătite, scope-urile verificate în 3 fișiere). Un admin nou vede tot. **Trebuie rezolvat înainte de a angaja sau invita un manager Rădăcini.**
- **Bypass-ul operatorului:** dacă refolosim `role=operator`, dăm acces gratuit la funcțiile plătite și la date PropManage.
- **Prea multe panouri:** adminul are deja 113 intrări *[corectat]*. Rădăcini trebuie să rămână la ~6, ca să nu fie greu de folosit.
- **Egress și cost:** panourile agregate și AI-ul citesc mult din baza de date. Pentru Rădăcini folosim KPI-uri calculate incremental sau la cerere, nu la fiecare afișare.
- **KC depinde de un registru JSON editat manual.** Dacă nu-l ținem la zi, harta minte.

---

## 10. Plan propus (după aprobare)

| Pas | Ce | Efort orientativ |
|---|---|---|
| A0 | Scope `radacini`, `require_admin_scope` pe rutele noi, colecția `radacini_staff` + dependența de verificare | 1–2 zile |
| A1 | Dimensiunea Produs în admin (comutator + filtrare `NAV_SECTIONS`) | 1–2 zile |
| A2 | Secțiunea admin Rădăcini (6 intrări, la început goale, cu KPI-uri) | 2–3 zile |
| A3 | Interfața operatorului de teren (coadă + verificare + mod asistat) | 3–4 zile |
| A4 | Panoul membrului după interese (XOS `radacini_home` + Page Registry) | 2–3 zile |
| A5 | Evenimente `radacini.*`, Timeline, Notification Center | 1–2 zile |
| A6 | Noduri Rădăcini în Knowledge Center + Decision Register | 0,5–1 zi |
| A7 (precondiție pentru personal extern) | Aplicarea zonelor admin pe server | 2–4 zile (atinge PropManage, cere aprobare separată) |

## 11. Decizii pentru tine

1. Adăugăm dimensiunea **Produs** în admin, cu comutator?
2. Operatorul Rădăcini e **personal pe arie** (`radacini_staff`) și nu primește `role=operator` global?
3. Aplicăm acum permisiunile pe zone (A7), înainte de primul manager Rădăcini care nu ești tu?
4. Activăm **modul asistat** (operatorul publică în numele proprietarului)?
5. Specialiștii PropManage pot oferi lucrări agricole, prin Capability Engine, în faza 2?
6. Knowledge Center rămâne doar al tău, iar echipa primește Documentație & Training?
