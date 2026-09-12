# ARCHITECTURE REVIEW — Design Partner Ecosystem / Professional OS / Industry OS
**Autor:** AI CPO · **Data:** 27 Iunie 2026 · **Conform:** regula Architecture Review (EO-043 companion) + Product Decision Filter + EO-026 (ACTIVE) + Anti-Vanity Rule
**Verdict scurt:** ✅ Viziune arhitectural corectă și construibilă FĂRĂ duplicare · ⚠️ CONFLICT DE GUVERNANȚĂ cu EO-026 + EO-043 privind MOMENTUL construcției → necesită decizia Fondatorului (Chief Product Validator).

---

## 1. Cele 10 întrebări obligatorii ale review-ului

| Întrebare | Răspuns | Detaliu |
|---|---|---|
| Duplică o capabilitate existentă? | 🟡 RISC REAL, evitabil | Există deja: `users` (specialiști cu specialty/service_categories/verified/tier), `portfolio.py` (CRUD portofoliu), `specialist_profile.py`, `interior_design.py` (conținut „Interior Intelligence" cu process_phases), marketplace + escrow + reviews, `twins`/`digital_twin_projects`, Knowledge Graph embrionar (`kg/registry`, enterprise_registry). Ecosistemul TREBUIE construit ca EXTENSIE a acestora (capability layer peste `users`, nu colecție nouă de „designeri"). |
| Introduce datorie tehnică? | 🟡 | Dacă se construiește înainte de unificarea twin (G2), Project Twin + responsabilități se vor lega de 4 sisteme twin fragmentate. G2 devine PRE-CONDIȚIE pentru fazele colaborative. |
| Se potrivește ecosistemului? | ✅ | Este chiar formalizarea ecosistemului existent (marketplace→orchestrare). |
| Îmbogățește Digital Twin? | ✅ | Direct: proiectele/materialele/responsabilitățile scriu în istoria proprietății. |
| Reutilizabil? | ✅ | Motorul de capabilități e generic („capabilities, not professions"). |
| Configurabil? | ✅ | Matricea de capabilități + software + certificări = date, nu cod (cerință explicită: „never hardcode profession-specific logic"). |
| Scalează? | ✅ | Modelul e document-based, compatibil Mongo. |
| Are sens în 5 ani? | ✅ | E direcția Industry OS. |
| Altă profesie îl reutilizează? | ✅ | Prin design (capability engine). |
| Păstrează Single Source of Truth? | 🟡 CONDIȚIONAT | DOAR dacă: (a) profilul profesional extinde documentul `users` existent (nu tabel paralel), (b) portofoliul extinde colecția `portfolio` (nu una nouă), (c) matricea de capabilități e un registru unic consumat și de marketplace-ul existent, (d) Reputation Intelligence derivă din date deja existente (requests/reviews/escrow), nu cere input manual duplicat. |

**Concluzie arhitecturală:** construibil corect, cu 4 reguli de implementare de mai sus + G2 ca pre-condiție pentru fazele 3+.

## 2. Maparea pe ce EXISTĂ deja (evitarea duplicării — regula ta nr. 1)

| Cerință din misiuni | Există azi | Strategie |
|---|---|---|
| Designer Public Profile | `specialist_profile.py` + `/specialisti/{id}` | EXTINDE cu capabilities + software + compatibility score |
| Portfolio System | `portfolio.py` (title/category/style/gallery/location/surface) | EXTINDE schema (before/after, 360, budget_range, tags, awards, public/private) |
| Capability Matrix pe 17 etape | `interior_design.py` v2 are `process_phases` (conținutul Interior Intelligence) | Registru nou `capability_catalog` (date, nu cod) legat de etapele existente |
| Verification / Ratings | `verified/tier` + `reviews` + escrow history | REFOLOSEȘTE; Reputation Intelligence = strat de calcul peste datele existente |
| Availability | `availability_status` pe user | EXTINDE cu calendar |
| Collaborative projects / permissions | `requests` (1 specialist/cerere) — NU există multi-actor | NOU (cel mai mare delta) — Project Twin cu roluri+permisiuni |
| AI Matching / Team Builder | `auto-match` existent pe marketplace + Claude integrat | EXTINDE motorul, nu construi altul |
| Styles discovery | `data/ghiduri.js` + landing design interior (static) | REDESIGN pe date reale — dar ONEST abia când există designeri+proiecte reale (altfel pagina afișează zerouri) |
| Knowledge Graph | `kg/registry` + enterprise_registry (46 noduri interne) | EXTINDE modelul de relații existent |
| Material Intelligence | `property_documents` metadate (firmă/garanție) + twin assets | EXTINDE — materialul ca entitate derivată din documente |

## 3. ⚠️ Conflictul de guvernanță (trebuie tranșat de Fondator)

Ordinele TALE active spun:
- **EO-026 (ACTIVE):** „No new major features before learning from reality." Beta NU a început (blocat pe: Stripe LIVE, Resend DNS, invitarea utilizatorilor reali — acțiuni Fondator).
- **EO-043 (ACTIVE):** „The roadmap is driven by evidence. If evidence does not exist, collect evidence first."
- **Anti-Vanity:** „Who asked for it? How many customers need it? If the answer cannot be measured, postpone."

Aplicate onest la Design Partner Ecosystem:
- **Cine a cerut?** Fondatorul (viziune) — zero designeri sau clienți reali intervievați încă.
- **Câți clienți au nevoie?** Nemăsurat — 0 utilizatori beta activi azi; lead-urile de design interior existente sunt puține și demo-poluate.
- **Ce KPI crește?** Ipotetic (supply side + AOV proiecte design) — nemăsurabil fără beta.

**Ca CPO nu pot recomanda construcția integrală acum fără să încalc EO-026/EO-043/Anti-Vanity.** În același timp, viziunea e strategică și corectă — deci NU o resping, o fazez pe dovezi.

## 4. Fazare propusă (evidence-gated)

| Fază | Conținut | Gate de intrare (dovadă necesară) | Efort |
|---|---|---|---|
| **D0 — acum (permis de EO-026)** | Salvare verbatim ✅ · acest review ✅ · **întrebările de validare în beta**: adăugăm 2 întrebări în VoC + interviuri cu 3-5 designeri reali (formular „Devino Design Partner" = landing de măsurare a cererii, efort 0.5 sprint) | niciunul — e colectare de dovezi | XS |
| **D1 — Capability Engine + Profil îmbogățit** | `capability_catalog` generic (faze+servicii, configurabil, cu excluderile PropManage-only) · software compatibility + compatibility score pe userul existent · portofoliu extins · profil public îmbogățit | ≥10 designeri înscriși pe landing SAU decizia strategică a Fondatorului că design = wedge-ul de go-to-market | M (1-2 sprinturi) |
| **D2 — AI Designer Matching + Team Builder** | extinde auto-match + Claude; explicații per recomandare | ≥5 proiecte reale de design cerute de clienți | M |
| **D3 — Proiecte colaborative + Responsibility Matrix + workspaces** | Project Twin multi-actor cu permisiuni | **G2 twin unificat REZOLVAT** + ≥3 proiecte cu ≥2 profesioniști | L |
| **D4 — Professional/Company Twin + Reputation Intelligence + certificări data-driven** | derivate din datele acumulate în D1-D3 | date reale de performanță (≥10 proiecte finalizate) | L |
| **D5 — Knowledge Graph public + Material Intelligence + AI Copilot** | stratul de cunoaștere | volum real de documente/proiecte | XL |

## 5. Recomandarea CPO

**Opțiunea A (recomandată, conformă cu TOATE ordinele tale):** Rămânem pe EO-026 — beta cu utilizatori reali întâi. Executăm DOAR D0 acum (landing „Devino Design Partner" + întrebări VoC) ca să măsurăm cererea pe ambele părți în timpul beta-ului. Ecosistemul intră în roadmap ca EPIC aprobat, cu gate-uri de dovezi per fază.

**Opțiunea B:** Fondatorul decide explicit că Design Partner Ecosystem = pariul strategic de go-to-market (decizie de viziune, permisă de Founder Rule) → construim D1 acum (fără duplicare, pe regulile din §1), în paralel cu beta-ul.

**Opțiunea C (respinsă de CPO):** construcția integrală acum — încalcă EO-026, EO-043, Anti-Vanity și ar amâna cu multe săptămâni contactul cu piața.

**Decizia aparține Fondatorului (Chief Product Validator).**
