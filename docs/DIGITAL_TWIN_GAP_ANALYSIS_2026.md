# DIGITAL TWIN — GAP ANALYSIS & PRODUCT BLUEPRINT (EO-005A)
**Founder Decision Pack · Iun 2026 · CONFIDENȚIAL — Founder Only**

> Guvernat de Truth Engine (D161): fiecare afirmație are evidență din cod sau este marcată UNKNOWN.
> Clasificare valori: **Measured** (numărat în cod/DB) · **Verified** (citit în cod) · **Estimated** (estimare declarată) · UNKNOWN.
> ZERO cod modificat în acest audit (Execution Rule EO-005). Implementarea = EO-005B, doar după aprobarea Fondatorului.

---

## 0. EXECUTIVE SUMMARY

**Maturitate actuală produs Digital Twin: ~45/100** (Estimated, media ponderată a celor 15 subsisteme din §3).

**Concluzia centrală (Verified prin cod):** PropManage NU are UN Digital Twin — are **PATRU sisteme "twin" fragmentate**, construite în epoci diferite, cu date și acces separate:

| # | Sistem | Colecție DB | Cum se obține | Evidență |
|---|--------|-------------|---------------|----------|
| 1 | **Property DNA / Intelligence Hub** (maturity L0-L5, active, riscuri, PVI) | `properties`, `property_assets` | Gratuit, self-serve în ClientDashboardV2 → tab Proprietate | `routes/property_dna.py`, `routes/property_intelligence.py`, `clientv2/PropertyHubV2.jsx` |
| 2 | **Twin validat de Operator** (camere + active + status approved) | `twins` | Clientul cere, Operatorul completează și validează manual | `routes/operator_twins.py` L43-74, L294-335 |
| 3 | **Digital Twin Pro 3D** (proiecte, modele GLB/Blender/SKP, pins, planuri 2D, rapoarte, QA AI) | `digital_twin_projects`, `digital_twin_models` | Abonament `digital_twin_pro` (flag) | `routes/digital_twin.py` (2.327 linii), `routes/digital_twin_qa.py` |
| 4 | **House Health** (documente, evaluări cu foto, scoring anual) | `hh_*` (scores, evaluations, documents) | Blocat: cere proiect DT Pro activ + abonament HH separat | `routes/house_health.py` L157-180 (`lock_reason: no_twin`) |

**Consecința pentru client:** Constituția Produsului spune "One property. One Digital Twin. Nothing should exist outside it." — realitatea din cod: proprietarul obișnuit (fără abonamente) are acces DOAR la sistemul 1; documentele proprietății sunt imposibil de urcat (blocate în sistemul 4, care cere sistemul 3); memoria proprietății se pierde la vânzare (transfer INEXISTENT în cod).

**Cele 3 încălcări majore ale Constituției Produsului (Verified):**
1. **"A property must never lose its memory"** → nu există NICIUN flux de transfer proprietate. `grep transfer routes/` → 0 rezultate relevante.
2. **"Every document must become part of the Digital Twin"** → nu există document vault la nivel de proprietate. DNA `capabilities.documents` este un proxy fals: numără `twin_assets`, nu documente (`property_dna.py` L148-151).
3. **"Nothing should exist outside it"** → `maintenance_logs` există în DB și sunt validate de operator (`operator_twins.py` L26-42), dar DNA raportează `maintenance: {populated: False}` HARDCODAT (`property_dna.py` L156).

---

## 1. STEP 1 — CAPABILITY MATRIX (ce poate face proprietarul AZI)

Legendă: ✅ Implemented · 🟡 Partial · ❌ Missing · ⛔ Blocked (există dar e blocat de gating) · ❓ UNKNOWN

| Capabilitate | Status | Evidență (cod real) |
|---|---|---|
| Creare cont + login | ✅ | `routes/auth.py`, flux testat în 130+ iterații |
| Adăugare proprietate (nume, adresă, tip, suprafață, camere) | ✅ | `POST /api/properties`, `models.py::PropertyIn` L56; UI `HomeV2.jsx` L164, `SettingsPanel.jsx` L454 |
| Vizualizare dashboard proprietate (DNA card, PVI, capabilities) | ✅ | `GET /properties/{id}/dna` → PVI + delta 6 luni + timeline 30 evenimente; `PropertyHubV2.jsx` `dna-card` |
| Property Maturity L0–L5 cu scară vizuală + CTA audit | ✅ | `GET /properties/{id}/maturity`, `maturity-card`, `maturity-ladder` |
| Registru instalații/active cu an instalare + proveniență (Trust Model D015) | ✅ | `POST /properties/{id}/assets`, slot lifecycle (înlocuire automată), EOL predictions; `assets-card` |
| Atribute DNA (acoperiș, izolație etc.) cu proveniență și confidence | ✅ | `GET/PATCH /properties/{id}/dna-attributes`, validare enum/int |
| Riscuri estimate + mitigare cu 1 click (acceptă oportunitate) | ✅ | `GET /properties/{id}/risks` + `POST /client/opportunities/{id}/accept`; `risks-card` |
| Predictive actuarial (EOL instalații) | ✅ | `GET /properties/{id}/predictive` + disclaimer onest ("recomandări, nu fapte") |
| Solicitare Digital Twin (validare Operator) | ✅ | `POST /properties/{id}/twin/request` → notifică operatorii; statusuri: not_requested→pending→draft→approved/needs_revision |
| Vizualizare twin (camere + active) read-only | ✅ | `GET /properties/{id}/twin`; `ClientTwinViewerModal` în ClientDashboardV2 |
| Cerere specialist → oferte → escrow → confirmare | ✅ | Flux marketplace complet legat de `property_id` (`routes/requests.py` L21) |
| Garanție automată la finalizarea lucrării | ✅ | `value_loop.py::enrich_on_closure` — warranty idempotent per cerere + event `warranty.created` |
| Timeline proprietate (evenimente lucrări) | 🟡 | `GET /properties/{id}/timeline` — DOAR evenimente din `requests`; lipsesc: maintenance logs, documente HH, evaluări, twin 3D |
| Istoric financiar (investiție totală prin platformă) | 🟡 | DNA `financial.total_invested_ron` — doar lucrări confirmate prin escrow; fără facturi externe |
| Upload documente proprietate (acte, CF, certificat energetic) | ⛔ | EXISTĂ doar în House Health (`POST /api/house-health/documents`) — blocat: cere proiect DT Pro (`lock_reason: no_twin`, `house_health.py` L171-176) + abonament. Proprietarul normal NU poate urca niciun document |
| Foto proprietate (galerie) | ❌ | `PropertyIn` nu are câmp photos; foto există doar pe cereri marketplace și evaluări HH |
| Planuri tehnice 2D | ⛔ | `POST /projects/{id}/plans` cu pin anchors — doar în DT Pro (abonament) |
| Model 3D (GLB/Blender/SKP cu conversie) | ⛔ | `digital_twin.py` L304-664 — upload + conversie Blender/SKP→GLB, layere; doar DT Pro. `twins.model_url` = "placeholder for future GLB upload" (`operator_twins.py` L146) |
| Pins/probleme pe model 3D + rapoarte email cu aprobare | ⛔ | `digital_twin.py` L860-1298 — doar DT Pro |
| AI Q&A pe twin (întrebi casa) | ⛔ | `digital_twin_qa.py` — Claude pe contextul proiectului; doar DT Pro, per proiect (nu per proprietate) |
| Evaluări anuale cu foto + scoring (House Health) | ⛔ | `hh_evaluations` + `hh_scores` — dublu-blocat (DT Pro + abonament HH) |
| Jurnal mentenanță | 🟡 | `maintenance_logs` + validare operator EXISTĂ; dar nu apare în DNA (hardcodat False) și nu există UI client de adăugare | 
| Calendar mentenanță + remindere | ❌ | Nu există. Singurele remindere: rapoarte DT Pro nefinalizate (`run_dt_auto_reminders` L1686) |
| Pașaport proprietate (export/share) | ❌ | 0 rezultate în cod |
| Cod QR proprietate | ❌ | 0 rezultate în cod |
| Transfer proprietate (vânzare cu istoric) | ❌ | 0 rezultate în cod — încălcare directă a Constituției ("The memory belongs to the property") |
| Senzori / Smart Home | ❌ | DNA hardcodat `sensors: {populated: False}` |
| Asigurări / Bancă (export dovezi) | ❌ | 0 rezultate în cod |
| Certificat energetic | ❓ | UNKNOWN — nu am găsit câmp dedicat; posibil parțial în dna-attributes |
| Notificări in-app | ✅ | `notify()` folosit în toate fluxurile twin |
| Notificări email | ⛔ | Resend blocat de DNS (P0 extern, acțiune Founder) |
| Permisiuni / membri pe proiect | ⛔ | `add_member` doar DT Pro |
| Mobile | 🟡 | Web responsive (clientv2 mobile-first); fără PWA/aplicație nativă |
| Twin ca motor comercial (Verified Estate) | ✅ | Listing publish CERE `digital_twin_id` (gate_2), Trust Score A+/A/B/C (`verified_estate.py` L227-250) |
| Interior Design AI pe camerele twin-ului | ✅ | `routes/design.py` — gated pe `twin_unlocked` |
| Demo public twin 3D | ✅ | `/demo` — viewer Three.js public (`PublicDemoPage.jsx`) |

**Bilanț: 14 ✅ · 4 🟡 · 8 ⛔ (există dar blocate de gating fragmentat) · 7 ❌ · 1 ❓** (Measured pe tabelul de mai sus)

---

## 2. STEP 2 — CUSTOMER JOURNEY (fluxul real, cu evidență)

```
Owner → Cont ✅ → Adaugă proprietate ✅ → "Creează Digital Twin" ⚠️ CONFUZ (4 sisteme)
     → Urcă documente ⛔ DEAD END (blocat de 2 abonamente)
     → Mapează instalații ✅ (assets-card, self-serve, excelent)
     → Primește audit ✅ (CTA din maturity/riscuri → revenue opportunity)
     → Cere specialist ✅ → Oferte ✅ → Aprobă ✅ → Istoric ✅ + garanție automată ✅
     → Transferă proprietatea ❌ DEAD END TOTAL
```

**Pain points identificate (Verified):**
1. **"Creează twin" înseamnă 4 lucruri diferite.** Clientul vede: DNA card (gratuit), buton "Solicită twin" (operator, manual), pagina /digital-twin (DT Pro, abonament), card House Health (blocat cu mesajul "disponibil doar proprietăților cu Digital Twin activ" — care de fapt cere proiect DT Pro, NU twin-ul validat de operator!). Interconectarea `twins` ↔ `digital_twin_projects` nu există în cod (HH caută în `digital_twin_projects`, ClientTwinViewer în `twins`).
2. **Documentele = cel mai mare dead end.** Constituția: "Every document must become part of the Digital Twin". Realitate: un proprietar plătitor de audit nu are UNDE să urce actul de proprietate.
3. **Twin-ul operatorului nu scalează.** Fiecare twin cere muncă manuală a unui operator (`operator_save_twin`). La 1.000 de proprietăți fluxul moare. Nu există self-serve.
4. **Timeline incomplet** — promitem "living memory", livrăm doar evenimente marketplace.
5. **Transfer inexistent** — promisiunea fundamentală a produsului ("de la construcție la moștenire") nu are nicio linie de cod.
6. **Dublu gating HH** — ca să-ți evaluezi anual casa trebuie să plătești DT Pro + HH; niciun client real nu va traversa asta.

---

## 3. STEP 3 — DIGITAL TWIN MATURITY (scoruri 0–100, Estimated cu evidență Verified)

| Subsistem | Scor | Explicație |
|---|---|---|
| Identity | 70 | CRUD complet + DNA attributes cu proveniență; lipsesc: foto, geolocație, nr. cadastral/CF |
| Documentation | 20 | Vault universal inexistent; HH documents dublu-blocat; DNA documents = proxy fals |
| Technical Data | 65 | Registru active cu bibliotecă actuarială + proveniență (cel mai matur subsistem self-serve) |
| Plans | 35 | Planuri 2D + anchors există, dar doar în DT Pro |
| Photos | 15 | Doar pe cereri și evaluări HH; galerie proprietate inexistentă |
| Measurements | 25 | Suprafață/camere; camere detaliate doar în twin operator; zero măsurători instrument |
| History | 55 | Timeline works + warranties + activity_events; lipsesc maintenance/HH/documents din flux |
| Maintenance | 30 | Logs + validare operator există; fără calendar, remindere, UI client |
| Marketplace | 80 | Cel mai puternic: flux complet legat de proprietate + garanții + PVI + opportunities |
| AI | 40 | QA pe proiect DT Pro (Claude) + orchestrator admin; Owner AI pe proprietate inexistent |
| Automation | 50 | Event bus + garanție auto + PVI refresh + revenue opportunities; fără automatizări vizibile clientului |
| Transferability | 5 | Inexistent — doar entity_links tehnice |
| Trust | 70 | Proveniență/confidence pe fiecare dată (D015), disclaimere oneste, Trust Score comercial |
| Security | 60 | Owner-checks pe toate rutele property (`_load_property_for`); audit complet de securitate: UNKNOWN |
| Knowledge | 55 | Knowledge graph (entity_links), event bus canonical, biblioteca actuarială |

**Media ponderată (ponderi egale): ~45/100** — produsul are fundații excelente (trust, marketplace, intelligence) și goluri fatale exact pe promisiunile constituționale (documente, memorie, transfer).

---

## 4. STEP 4 — GAP ANALYSIS (clasificat)

### CRITICAL (blochează promisiunea produsului / vânzarea)
| Gap | Tip | De ce e critical |
|---|---|---|
| G1. Document Vault universal per proprietate (acte, CF, certificat energetic, facturi, foto) | Feature+API+DB | Constituție: "Every document..."; e și condiția pentru "property passport"; azi = dead end |
| G2. Unificarea celor 4 sisteme twin într-o singură experiență "Twin-ul proprietății" | UX+Arhitectură | Clientul nu înțelege ce cumpără; HH blocat pe data model greșit |
| G3. Timeline complet al proprietății (works + mentenanță + documente + evaluări + twin) | Feature | "Living memory" e diferențiatorul #1 declarat |
| G4. Transfer proprietate cu păstrarea istoricului | Feature | Promisiunea fondatoare; și momentul comercial cel mai valoros (vânzare = buyer nou = client nou) |

### HIGH
| Gap | Tip |
|---|---|
| G5. Galerie foto proprietate | Feature |
| G6. Calendar mentenanță + remindere pe active (biblioteca EOL există deja!) → cerere specialist cu 1 click | Feature+Automation |
| G7. Property Passport shareable (link public + QR + trust score) | Feature+Growth |
| G8. Owner AI — întreabă-ți casa (reuse pattern `digital_twin_qa` pe datele proprietății, nu ale proiectului) | AI |
| G9. Self-serve twin (fără operator): wizard camere+active la onboarding | UX |
| G10. Maintenance logs în DNA + UI client de jurnal | Fix+Feature |

### MEDIUM
G11. Certificat energetic ca atribut de primă clasă · G12. Geolocație + hartă · G13. Export PDF raport proprietate · G14. Membri/permisiuni pe proprietate (familie, chiriaș, administrator) · G15. PWA mobile · G16. Consolidare model_url twin operator ↔ modele DT Pro · G17. Facturi externe în istoricul financiar

### LOW
G18. Senzori/Smart Home · G19. API bancă/asigurător · G20. Sankey/vederi avansate arhitectură (backlog EO-002)

---

## 5. STEP 5 — PRODUCT BLUEPRINT (per gap major)

| | Current State | Desired State | Business Value | Complexitate | Efort (Est.) | Dependențe |
|---|---|---|---|---|---|---|
| **G1 Document Vault** | 0 documente urcabile de owner | Upload/list/download/delete + tip document + proveniență D015; alimentează DNA documents REAL | Deblochează pașaport + audit + încredere; primul "wow" gratuit | Medie (object storage) | 1 sprint | Integrare object storage (playbook există la Emergent) |
| **G2 Twin unificat** | 4 sisteme, 3 colecții | O pagină "Twin" per proprietate: DNA+active+riscuri+documente+timeline+3D (dacă există)+HH (dacă abonat) | Claritate ofertă → conversie; HH deblocat pe twin-ul real | Medie (doar UI + 2 fix-uri backend: HH lock + DNA maintenance) | 1 sprint | G1 recomandat înainte |
| **G3 Timeline complet** | Doar works | Toate evenimentele: docs, mentenanță, evaluări, twin, garanții — sursă unică `activity_events` | "Living memory" devine demonstrabil în vânzări | Mică (event bus există) | 0.5 sprint | G1 |
| **G4 Transfer** | Inexistent | Flux: owner inițiază → buyer acceptă cu cont → proprietatea+twin+istoric se mută, financiarul vechi se anonimizează (GDPR) | Diferențiator unic pe piață; loop de achiziție clienți noi | Medie | 1 sprint | G2 |
| **G6 Maintenance Calendar** | EOL predictions există fără acțiune | Calendar din biblioteca actuarială + remindere + "Cere specialist" 1-click → marketplace | Revenue direct recurent (fiecare reminder = lead marketplace) | Mică-Medie | 1 sprint | Email (Resend DNS — Founder) |
| **G7 Property Passport** | Inexistent | Pagină publică read-only cu QR: scor, date verificate cu confidence, istoric selectiv | Growth viral + instrument de vânzare imobiliară; sinergie Verified Estate | Mică | 0.5 sprint | G1+G3 |
| **G8 Owner AI** | QA doar pe proiect DT Pro | Chat pe proprietate (DNA+assets+risks+timeline+docs), cu Truth classification în răspunsuri | Retenție + diferențiator AI onest | Mică (reuse `digital_twin_qa` pattern + Emergent LLM key) | 0.5 sprint | G1-G3 pentru context bogat |

Owner pentru toate: Executive Intelligence (implementare) + Founder (aprobare/preț). Success metrics propuse per feature în §7.

---

## 6. STEP 6 — SPRINT ROADMAP (fiecare sprint = funcționalitate vizibilă clientului)

| Sprint | Livrabil client-visible | Gap-uri |
|---|---|---|
| **S1 — "Casa ta are memorie"** | Document Vault (upload acte/foto/facturi cu tip + proveniență) + galerie foto + documente în DNA și timeline | G1, G5, parțial G3 |
| **S2 — "Un singur Twin"** | Pagina Twin unificată per proprietate (DNA+active+riscuri+docs+timeline+3D/HH condiționat); fix HH lock pe twin real; maintenance în DNA + jurnal client | G2, G10, G3 complet |
| **S3 — "Pașaportul casei"** | Property Passport public cu QR + trust score + share (WhatsApp/link) — sinergie cu share-ul viral existent de la /scorul-casei | G7 |
| **S4 — "Casa își cere singură mentenanța"** | Calendar mentenanță din EOL + remindere + cerere specialist 1-click | G6 |
| **S5 — "Casa nu-și pierde memoria"** | Transfer proprietate cu istoric (vânzare/moștenire) + vedere buyer | G4 |
| **S6 — "Întreabă-ți casa"** | Owner AI chat pe twin + raport lunar automat pe email | G8 |

Estimare totală: **~5–6 sesiuni de lucru** (Estimated, confidence medie — bazat pe vitezele istorice din PRD: 1 sprint ≈ 1 sesiune cu testare completă).

---

## 7. STEP 7 — MVP: "versiunea minimă pentru care un client PLĂTEȘTE"

**Răspuns direct:** Clientul plătește pentru ÎNCREDERE DOVEDIBILĂ, nu pentru software. MVP-ul plătibil = **Twin cu documente + audit verificat + pașaport partajabil**, pentru că e singurul pachet care îi crește valoarea proprietății la vânzare (beneficiu bănesc concret).

- **Must Have**: S1 (documente+foto) · S2 (twin unificat) · audit tehnic plătit (EXISTĂ ✅ — verified_estate) · S3 (pașaport)
- **Should Have**: S4 (calendar mentenanță) · timeline complet · email-uri funcționale (Resend — Founder)
- **Nice to Have**: S6 (Owner AI) · export PDF · membri familie
- **Future**: S5 poate glisa aici dacă vânzările cer altceva · 3D self-serve · senzori · API bancă/asigurări · PWA

**Monetizare propusă (Estimated, necesită validare Founder):** Twin de bază GRATUIT (achiziție + date) → Audit plătit (există, 450 RON încasați deja) → abonament "Twin Complet" (HH re-poziționat pe twin-ul real, un singur gating, nu două).

---

## 8. STEP 8 — COMPETITIVE REVIEW (vs. viziunea din Product Constitution)

**Puncte forte (Verified):**
- Trust Model D015 aplicat REAL pe date (proveniență + confidence pe fiecare activ/atribut) — rar în piață, aliniat perfect cu Truth Engine.
- Marketplace-ul ca "execution layer" al twin-ului e deja construit end-to-end (cerere→escrow→garanție→PVI).
- PVI + maturity ladder + risk engine = mecanică de progres care educă clientul.
- Twin-ul e deja gate comercial în Verified Estate (Trust Score).

**Puncte slabe:**
- Promisiunea constituțională centrală (memoria documentară + transferabilitate) nu există.
- Fragmentarea celor 4 sisteme face oferta neinteligibilă.
- Dependența de operator pentru twin blochează scalarea.

**Avantaje competitive de apărat:** proveniența datelor (nimeni nu clasifică onest Measured/Estimated) · marketplace integrat · garanții automate legate de proprietate.
**Diferențiatori lipsă:** pașaportul partajabil (nimeni nu-l are în RO) · transferul cu istoric ("cartea de service a casei" — analogie auto care vinde singură).

---

## 9. STEP 9 — FOUNDER DECISION PACK

**Top gaps**: vezi §4 (G1–G20, ordonate). **Top oportunități**: fiecare sprint din §6 + monetizarea din §7.

**Impact estimat (toate Estimated, confidence 50-60%):**
- S1+S2+S3 → oferta devine vandabilă către primii 10 clienți de audit (target Mission 100: 10 audituri reale).
- S4 → fiecare proprietate cu active mapate generează 2-4 lead-uri marketplace/an (biblioteca EOL le programează).
- S3 pașaport → canal organic nou (fiecare pașaport partajat = landing page cu brand).
- Venit potențial 12 luni: UNKNOWN cu onestitate — pre-revenue, fără date de conversie reale; singura cifră Measured: 450 RON încasați istoric pe audit.

**Riscuri:** transferul (S5) atinge GDPR (anonimizare financiar vechi) — necesită atenție juridică; object storage (S1) = integrare nouă; Resend DNS rămâne blocker pentru S4 remindere email (acțiune Founder).

**DECIZIE CERUTĂ FONDATORULUI (EO-005B):**
1. Aprobi roadmap-ul S1–S6 așa cum e ordonat? (recomandarea mea: DA, începe cu S1)
2. Aprobi re-poziționarea House Health pe twin-ul real (un singur gating) în S2?
3. Confirmi monetizarea: twin de bază gratuit + audit plătit + un singur abonament?

*Semnat: Executive Intelligence · Sursa de adevăr: exclusiv codul din /app la data auditului.*
