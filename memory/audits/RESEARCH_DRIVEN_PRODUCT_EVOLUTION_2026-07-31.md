# RESEARCH-DRIVEN PRODUCT EVOLUTION — Metodologie Oficială PropManage

> **Referință oficială** pentru toate dezvoltările viitoare.
> **Principiu central**: `RESEARCH → KNOWLEDGE → VALIDATION → PRODUCT` (nu `IDEE → IMPLEMENTARE`).
> **Zero cod nou. Zero UI nouă. Doar metodologie și reutilizare infrastructură existentă.**
> **Data**: 2026-07-31 · **Auditor**: E1 · **Status**: strategy document.

---

## 1. Situația actuală

PropManage are deja o infrastructură remarcabilă pentru knowledge management, dar dezvoltarea produsului urmează în prezent modelul clasic **idea-driven**:

- **Ce există bine**: Knowledge Center (`/api/founder/knowledge`), MASTER_PLATFORM_STATE (SSOT), Ownership Matrix, Dependency Map (implicit prin PATH_RULES), Product Blueprint (`/app/memory/product/*`), 172 route modules, Enterprise Health, AI Governance, Knowledge Graph (`kg_entities`, `kg_edges`), CEO Briefing.
- **Ce lipsește**: nu există un lanț formal de la **research de teren → decizie de produs**. Feature-urile intră direct în ROADMAP fără evidence explicit de piață.
- **Ce se face astăzi**: PRD-ul se scrie din intuiție + feedback informal. Prioritizarea e făcută la nivel executiv fără validare cantitativă din teren.

**Gap identificat**: nu există un mecanism care să transforme conversații cu președinți de asociații (research primar) în intrări structurate care să ajungă mecanic în ROADMAP.

---

## 2. Compatibilitatea cu arhitectura existentă

**Toate cele 4 straturi ale metodologiei RESEARCH → KNOWLEDGE → VALIDATION → PRODUCT pot fi realizate 100% pe infrastructura existentă**, fără module noi:

| Strat | Componentă existentă folosită | Extindere necesară |
|---|---|---|
| RESEARCH (interviuri) | Knowledge Center (docs în `/app/memory/`) | Nou folder `/app/memory/research/interviews/` + convention markdown |
| KNOWLEDGE (pattern-uri) | Knowledge Graph (`kg_entities`, `kg_edges`) | Nou entity type `research_pattern` |
| VALIDATION (scoring) | Enterprise Health formulas_registry (Directiva 151) | Formula nouă `validation_level_avg` |
| PRODUCT (roadmap) | ROADMAP_V2.md + Board Directives + PRD.md | Nou câmp `evidence_from` în entries |

**Verdict compatibilitate**: 🟢 **HIGH**. Nu necesită schema DB nouă, nu necesită componente React noi.

---

## 3. Ce poate fi reutilizat

| Nevoie | Componentă existentă | Cum e reutilizată |
|---|---|---|
| Storage docs research | `/app/memory/` filesystem + `knowledge_center.py` | Nou folder `/app/memory/research/` — auto-visible în Knowledge Center |
| Categorizare research | `PATH_RULES` din `knowledge_center.py` | Adaug rules pentru `research/interviews/`, `research/patterns/`, `research/reports/` |
| Search interviuri | `/api/founder/knowledge/search` | Deja funcțional cross-docs |
| Registry funcționalități validate | Knowledge Graph (`kg_entities` + `kg_edges`) | Entity type nou: `feature_request` cu relații |
| Traceability idee → implementare | Board Resolutions + Execution Orders + PRD.md | Convention: fiecare Board Directive citează evidence path |
| Prioritizare | Enterprise Health scoring | Formula nouă în formulas_registry |
| Cross-reference automatic | AI Copilot + AI Brain graph | Ingest research docs în graph |
| Discovery duplicate | Sprint 1 Consolidation Report + AI Search | Query: „există deja X înainte de a adăuga?" |
| Validation flow | Journey Guardian + Product Guardian | Guards care blochează feature nou fără validation ≥ V1 |
| Reporting | CEO Briefing + Founder Digest | Adaugă bloc „Research Signals" în briefing existent |

---

## 4. Ce trebuie extins

**Toate extensiile sunt convention-based, nu cod-based:**

| Extensie | Ce presupune | Effort |
|---|---|---|
| Convention markdown pentru interviuri | Template `.md` cu secțiuni obligatorii (Context, Profil bloc, Probleme, etc.) | Doc-only |
| Convention naming | `INTERVIEW_YYYY-MM-DD_NUME-ASOCIATIE.md` | Doc-only |
| PATH_RULES în `knowledge_center.py` | 3 linii noi (research/interviews, research/patterns, research/reports) | 1 line change |
| Enterprise Health formula | `validation_level_avg` calc | Add în formulas_registry |
| Board Directive template | Câmp nou `evidence_paths: []` | Doc-only |
| PRD.md convention | Fiecare feature nou → link către interviu(uri) sursă | Doc-only |
| AI Copilot context | Include research docs în AI Brain graph | Zero cod, doar convention pentru ingest |

---

## 5. Ce lipsește

Lucruri care **NU există** în infrastructură și rămân aspirational (Sprint viitor doar dacă research dovedește nevoie):

- **UI dedicat pentru interviuri** — momentan doar Markdown în `/app/memory/`. Adecvat pentru start.
- **Voice-to-text pentru interviuri** — interviuri se transcriu manual.
- **Auto-pattern-detection** — pattern-urile se extrag manual din interviuri (până la 25+ interviuri, când merită AI-driven).
- **Validation dashboard** — momentan tracking manual în Markdown. Când >50 features în pipeline, poate migra în DB.
- **Correlation engine** — cross-interview pattern detection e manual.

**Regula sfântă**: **NU construim** aceste componente **înainte de a demonstra prin research că merită**. Meta-principiu: aplicăm metodologia recursiv pe metodologia însăși.

---

## 6. Research Knowledge Base — Structură recomandată

**Locație**: `/app/memory/research/interviews/`
**Naming**: `INTERVIEW_YYYY-MM-DD_ASOCIATIE-SLUG.md`
**Template obligatoriu** (fiecare interviu trebuie să conțină aceste 11 secțiuni):

```markdown
# INTERVIU — [Nume Asociație] · [Data]

## 1. Context
- Intervievator:
- Data + ora:
- Modalitate (față-în-față / online / telefon):
- Durată:
- Consimțământ înregistrare: Y/N

## 2. Profil bloc / asociație
- Localitate:
- Nr. apartamente:
- Anul construcției:
- Regim înălțime:
- Tip proprietate (rezidențial / mixt / comercial):
- Buget lunar mediu asociație:
- Sistem management actual (excel / softuri / hârtie):
- Nr. specialiști colaboratori:
- Vechime președinte:

## 3. Probleme identificate
- P1: [descriere problemă] — frecvență / impact / cost estimat
- P2: ...

## 4. Riscuri identificate
- R1: [risc operațional / financiar / legal / social]
- R2: ...

## 5. Dovezi (citate directe)
> "..." (citat literal, marcat cu ghilimele)

## 6. Pattern-uri observate
- Pattern-uri comune cu alte interviuri (cross-reference paths):
- Pattern-uri noi (candidate pattern):

## 7. Funcționalități sugerate (de intervievat)
- FR1: [ce a cerut explicit]
- FR2: ...

## 8. Funcționalități existente în PropManage
- Care sunt deja implementate și pot rezolva:
- Care necesită extindere:
- Care lipsesc complet:

## 9. Gap Analysis
- Nevoi acoperite (%):
- Nevoi neacoperite (listă):
- Nevoi aspirationale (viitor):

## 10. Prioritate propusă
- Business impact: LOW / MEDIUM / HIGH / CRITICAL
- Effort estimat: XS / S / M / L / XL
- Blocker pentru cine: [tip user]

## 11. Nivel de validare (post-interview)
- V0 / V1 / V2 / V3 / V4 / V5 (vezi Validation Engine)
- Confirmă / infirmă un pattern anterior: [link path]

## Metadata
- Tags: [asociație, bloc, financiar, ...]
- Related interviews: [paths]
- Follow-up needed: Y/N + when
```

**De ce funcționează**: fiecare interviu devine un doc `.md` în `/app/memory/research/interviews/` → auto-visible în Knowledge Center → indexat în AI Brain (dacă e adăugat la ingest) → searchable prin `/api/founder/knowledge/search`.

**Statutul de „cunoaștere reutilizabilă"**: fiecare interviu este atomic (un obiect self-contained) DAR poate fi cross-referenced prin `Related interviews` field. Astfel se construiește un graph mental al problemelor de piață, fără sistem paralel.

---

## 7. Validation Engine — Structură recomandată

**Locație**: convention aplicată în interviuri + în Board Directives + în PRD.md.
**NU necesită modul cod dedicat momentan.**

**Nivelurile oficiale**:

| Nivel | Definiție | Evidence obligatoriu | Când poate intra în ROADMAP? |
|---|---|---|---|
| **V0** | Idee internă | Nici o evidență externă | ❌ NU intră în ROADMAP |
| **V1** | Confirmat de 1 președinte | 1 interviu cu quote direct | ❌ Doar în „Concept" folder |
| **V2** | Confirmat de 5 președinți | 5 interviuri cu pattern comun | ✅ Poate intra în P3 (backlog) |
| **V3** | Confirmat de 10 președinți | 10 interviuri + Research Report | ✅ Poate intra în P2 |
| **V4** | Confirmat de 25 președinți | 25 interviuri + Cross-city sample | ✅ Poate intra în P1 |
| **V5** | Implementat în producție | Feature live + evidence usage (analytics) | ✅ Menționat ca „shipped" |

**Regula de aur**: **niciun feature nu urcă la P0/P1 în ROADMAP fără V3 minimum**.
**Excepții**: bugs critice, security, compliance legal — au propriul flow (Directive Framework).

**Cum se calculează în Enterprise Health** (formulă propusă în `formulas_registry`):

```
validation_level_avg = weighted_avg(feature.validation_level for feature in active_roadmap)
- V0 = 0 points
- V1 = 20 points
- V2 = 40 points
- V3 = 60 points  
- V4 = 80 points
- V5 = 100 points

Threshold healthy: validation_level_avg >= 65 (majoritatea ROADMAP să fie V3+)
```

**Storage**: fiecare feature în ROADMAP capătă câmp nou `validation_level: V0|V1|V2|V3|V4|V5` și `evidence_paths: [interview1.md, interview2.md, ...]`. Zero cod backend nou — Knowledge Center deja parsează frontmatter în MD dacă adăugăm parsare simplă (opțional).

**Guvernanță**: Product Guardian sau Journey Guardian pot avea o regulă viitoare: „nu accepta PR pentru feature nou dacă `validation_level < V2`". Deocamdată, aplicație manuală prin PR review.

---

## 8. Product Requirements Pipeline — Flux oficial

**Fluxul complet mapa infrastructura existentă**:

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. INTERVIU                                                         │
│    Locație: /app/memory/research/interviews/                        │
│    Template: obligatoriu (11 secțiuni)                             │
│    Owner: research analyst (founder / delegat)                     │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. KNOWLEDGE BASE                                                   │
│    Auto: fișierul apare în Knowledge Center                        │
│    Categorie: „Research" (nouă, adaug în PATH_RULES)              │
│    Search: /api/founder/knowledge/search deja funcțional          │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. PATTERN DETECTION (după 5+ interviuri)                          │
│    Locație: /app/memory/research/patterns/PATTERN_<slug>.md        │
│    Manual până la 25+ interviuri, apoi eligible AI-assisted        │
│    Convention: PATTERN doc referă interview paths ca evidență     │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 4. RESEARCH REPORT                                                  │
│    Locație: /app/memory/research/reports/REPORT_<topic>_<date>.md  │
│    Consolidează patterns + prioritizare + validation level        │
│    Owner: research analyst                                          │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 5. INFRASTRUCTURE REUSE AUDIT (obligatoriu)                        │
│    Check: există deja funcționalitate? API? model DB? component?  │
│    Sursă: MASTER_PLATFORM_STATE + Ownership Matrix + Sprint 1 Rep │
│    Output: 1-page memo cu answer YES/NO + link către SSOT         │
│    Locație: /app/memory/research/reuse_audits/AUDIT_<feature>.md  │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 6. PRODUCT REQUIREMENT (PRD entry)                                  │
│    Adaugă în /app/memory/PRD.md                                    │
│    Câmpuri obligatorii: validation_level, evidence_paths,          │
│    reuse_audit_path, business_impact, effort                       │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 7. ROADMAP                                                          │
│    Adaugă în /app/memory/board/ROADMAP_V2.md                       │
│    Priority determined de validation_level + business_impact       │
│    Board Directive/Resolution obligatoriu pentru P0/P1             │
└─────────────────────────────┬──────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────────┐
│ 8. IMPLEMENTARE                                                     │
│    Sprint execution normal (E1 agent + review flow existent)       │
│    La finalizare: validation_level = V5, MASTER_PLATFORM_STATE     │
│    reflectă noul status                                             │
└────────────────────────────────────────────────────────────────────┘
```

**Reutilizare infrastructură**: 100% — TOATE cele 8 pași folosesc doar `/app/memory/` + Knowledge Center + docs existente. Zero componente noi.

---

## 9. Infrastructure Reuse Audit — Structură recomandată

**Locație**: `/app/memory/research/reuse_audits/AUDIT_<feature_slug>_<date>.md`
**Template obligatoriu** (răspuns explicit la 7 întrebări):

```markdown
# Infrastructure Reuse Audit — [Feature Name]

## Feature propus
[Descriere scurtă în 2-3 fraze]

## Evidence
- Interviews: [paths]
- Research Report: [path]
- Validation level: V<n>

## 7 întrebări obligatorii

### 1. Există deja această funcționalitate?
- [ ] YES → path: [linkul către modul + reason nu este suficient]
- [ ] NO
- [ ] PARȚIAL → [ce lipsește]

### 2. Există un model similar?
- [ ] YES → [modelul + reason nu se poate reutiliza]
- [ ] NO
- Sursa verificată: MASTER_PLATFORM_STATE + Ownership Matrix + Sprint 1 Report

### 3. Există API reutilizabil?
- [ ] YES → endpoints existente: [list]
- [ ] NO
- Sursa verificată: MASTER_PLATFORM_STATE secțiunea 5 (API Inventory)

### 4. Există componente frontend reutilizabile?
- [ ] YES → components: [list]
- [ ] NO
- Sursa verificată: /app/frontend/src/components/**

### 5. Există schema DB reutilizabilă?
- [ ] YES → collections: [list]
- [ ] NO
- Sursa verificată: MASTER_PLATFORM_STATE secțiunea 6 (Database Inventory)

### 6. Există documentație reutilizabilă?
- [ ] YES → docs: [paths]
- [ ] NO
- Sursa verificată: Knowledge Center

### 7. Există integrare în Knowledge Graph?
- [ ] YES → entity type: [name]
- [ ] NO

## Decizie
- [ ] REUTILIZĂM 100% existent (nu construim nimic nou)
- [ ] EXTINDEM componentă existentă (specificat mai jos)
- [ ] CONSTRUIM NOU (justificat prin gap real)

## Justificare
[Text obligatoriu; dacă construim nou, minim 3 fraze de justificare + confirmare Ownership Matrix update]

## Aprobare
- Founder / Board Directive: [required for BUILD NEW]
- Data aprobare:
```

**Integrare în flux**: **audit-ul e blocker mandatory** înainte de a intra în PRD. Nu poți sări peste. Dacă audit-ul concludează „REUTILIZĂM 100%", nu se scrie PRD nou — se folosește feature-ul existent.

**Automatizabil**: AI Copilot poate genera draft-ul de audit citind MASTER_PLATFORM_STATE și feature description. Founder review + approve. Effort agent: ~5 min per audit.

---

## 10. Impact asupra Knowledge Center

**Zero cod schimbat cu excepția a 3 linii în `PATH_RULES`**:

```python
PATH_RULES = [
    # ... existing rules ...
    ("memory/research/interviews/", "Research"),
    ("memory/research/patterns/", "Research"),
    ("memory/research/reports/", "Research"),
    ("memory/research/reuse_audits/", "Research"),
]
```

**Efect**:
- Nouă categorie "Research" apare în Knowledge Center tree la `/admin/knowledge-center`.
- Toate documentele research devin searchable prin API existent.
- AI Copilot le poate cita ca sursă când răspunde la întrebări.
- Zero UI nouă.

**Considerații de scaling**: cand vor fi >100 interviuri, Knowledge Center începe să fie lent pe filesystem glob. Solution (viitor, doar dacă necesar): migrare la MongoDB collection `research_docs` cu adaptor. Momentan filesystem este perfect.

---

## 11. Impact asupra Dependency Map

**Efect direct**: fiecare Research Report și PRD entry va adăuga edges noi în:
- MASTER_PLATFORM_STATE → Research Report (evidence-of relation)
- PRD → Research Report → Interviews (justified-by chain)
- ROADMAP → PRD → Research Report (traceable chain)

**Cum apare**: în header-ul fiecărui doc canonic există „Relații cu alte documente oficiale". Cu adăugarea research/, dependency map crește organic.

**Nu necesită schemă nouă**. Poate fi extras vizual manual sau prin AI Brain graph ingest.

---

## 12. Impact asupra Product Blueprint

Product Blueprint (`/app/memory/product/*`) devine target-ul spre care evoluează produsul.

**Regula nouă**: fiecare update în Product Blueprint trebuie să citeze:
- **Sursa validată**: minimum V3 (10+ interviuri).
- **Reuse audit**: link către audit-ul care justifică.
- **Impact assessment**: pe ce dashboard-uri / engines existente.

**Efect asupra Blueprint Compliance score** (propus în Living Governance):
- Când Blueprint reflectă doar features V3+, compliance score devine mai realist.
- Când Blueprint conține features V0-V1 (aspirational), compliance rămâne artificial mic (bine — semnalizează over-promise).

**Nu se modifică documentele Blueprint existente** — se adaugă doar convention pentru viitor.

---

## 13. Impact asupra Platform Audits

**MASTER_PLATFORM_STATE viitor va conține secțiunea nouă**:

```markdown
## X. Research-Driven Evolution Status
- Interviews conducted this quarter: [count]
- Patterns identified: [count]
- Reports published: [count]
- Reuse audits: [count]
- Features by validation level:
  - V0: [count]
  - V1: [count]
  - V2: [count]
  - V3: [count]
  - V4: [count]
  - V5 (shipped): [count]
- Validation Level Average: [%]
- Blueprint Coverage validated: [%]
```

**Efect**: audit-ul viitor va putea raporta cantitativ dacă platforma evoluează pe research sau pe intuiție.

**Delta vizibil între audit-uri**: creșterea numărului de V5 (shipped validated) vs V0 (assumed) este KPI direct al reușitei metodologiei.

---

## 14. Impact asupra Knowledge Graph

**Nou entity type**: `research_signal` cu proprietăți:
- `source_interviews: [path1, path2, ...]`
- `validation_level: V0|...|V5`
- `related_feature: <kg_entity_id>`
- `business_impact: LOW|MEDIUM|HIGH|CRITICAL`

**Nou edge type**: `evidence_of` — leagă `feature_request` de `research_signal`.

**Cum se populează**: manual la început (founder / research analyst updatează). Când sunt >50 signals, AI Brain poate ingest automat.

**Efect**: query în AI Copilot devine puternic — „arată-mi toate feature-urile care au evidence-of ≥ V3" returnează exact ROADMAP validat.

**Zero schema DB nouă** — `kg_entities` are deja `properties: dict` flexibil.

---

## 15. Impact asupra AI Copilot

**Cea mai mare mișcare de valoare din această metodologie.**

AI Copilot devine **conversational research consultant**:

| Query utilizator | Sursă răspuns |
|---|---|
| „Ce au spus președinții despre facturi?" | Research interviews (searched via `/api/founder/knowledge/search`) |
| „Care e cea mai validată nevoie neacoperită?" | Research reports + Reuse audits |
| „Există deja X înainte de a-l construi?" | MASTER_PLATFORM_STATE + Reuse audit template |
| „Ce feature din ROADMAP are cea mai mică validation?" | ROADMAP + validation_level field |
| „Ce interviuri contrazic feature-ul propus X?" | Cross-reference automatic |

**Ce trebuie făcut**: adaugă research folder la lista de docs ingerate de AI Brain (dacă are RAG). Zero cod nou dacă AI Brain deja citește `/app/memory/**`.

---

## 16. Roadmap în faze

### Faza 0 — DECLARAȚIE (imediat, 0 ore de dev)
✅ Acest document publicat în Knowledge Center.
- Founder validează metodologia.
- Convention agreed: `RESEARCH → KNOWLEDGE → VALIDATION → PRODUCT`.

### Faza 1 — INFRASTRUCTURE PREPARE (1 oră)
- Creez folder `/app/memory/research/` cu 4 sub-foldere (interviews, patterns, reports, reuse_audits).
- Adaug 4 PATH_RULES în `knowledge_center.py` pentru vizibilitate.
- Creez template `INTERVIEW_TEMPLATE.md` și `REUSE_AUDIT_TEMPLATE.md` în fiecare sub-folder ca ghid.

### Faza 2 — PRIMUL INTERVIU (după Founder decide când)
- Founder / research analyst intervievează primul președinte.
- Documentul urmează template-ul.
- Se salvează. Auto-apare în Knowledge Center → categoria „Research".

### Faza 3 — PATTERN DETECTION (după 5 interviuri)
- Primul pattern doc scris manual.
- Cross-references între interviuri.
- Primul V2 apare.

### Faza 4 — RESEARCH REPORT (după 10 interviuri)
- Primul report agregat.
- Primul V3 posibil.
- Primul PRD justificat prin research (nu prin intuiție).

### Faza 5 — REUSE AUDITS (start imediat + retroactive)
- Fiecare feature în lucru primește reuse audit (chiar retroactiv pe feature-urile existente în ROADMAP).
- Founder aprobă „BUILD NEW" doar dacă audit-ul concludează gap real.

### Faza 6 — VALIDATION SCORING ÎN ENTERPRISE HEALTH (după Sprint 2 existent)
- Formula `validation_level_avg` adăugată în formulas_registry.
- Bloc „Research Signals" în CEO Briefing.
- Score vizibil în Enterprise Health Page.

### Faza 7 — LIVING GOVERNANCE (după 25+ interviuri)
- MASTER_PLATFORM_STATE viitor include secțiunea Research-Driven Evolution.
- Founder decide dacă trece la Faza 8.

### Faza 8 — AI-ASSISTED (opțional, doar dacă necesar)
- AI Brain ingest automat research docs.
- Auto-suggest patterns.
- Auto-generate reuse audit drafts.

**Timeline realist**: Faza 0-1 (imediat) · Faza 2-4 (2-3 luni de research activ) · Faza 5-6 (paralel cu research) · Faza 7 (după quarter Q3-Q4 2026) · Faza 8 (când există masa critică de date).

---

## 17. Complexitate

| Fază | Effort tehnic | Effort operațional | Effort strategic |
|---|---|---|---|
| Faza 0 | 0h | 1h (founder review) | 2h (validare metodologie) |
| Faza 1 | 1h (3 linii cod în knowledge_center + creare foldere + templates) | 0h | 0h |
| Faza 2 | 0h | 2h per interviu | 0h |
| Faza 3 | 0h | 4h scriere primul pattern | 2h validation |
| Faza 4 | 0h | 8h primul report | 4h prioritizare |
| Faza 5 | 0h | 30min per feature (audit) | 0h |
| Faza 6 | 2h (adăugare formula în formulas_registry) | 1h (integrare CEO Briefing) | 0h |
| Faza 7 | 0h (doc update) | 4h (audit E1) | 4h |
| Faza 8 | 3-5 zile (dacă se implementează) | 0h | 0h |

**Total dev effort la Faza 0-7**: ~3-5 ore cod cumulate. Restul e operațional și strategic.

---

## 18. Riscuri

| Risc | Probabilitate | Impact | Mitigație |
|---|---|---|---|
| **Research nu se face** (rămâne la Faza 0) | HIGH | HIGH | Founder își face un committment public în Board Directive. Primul interviu în ≤14 zile de la publicare doc. |
| Interviuri fără template → date non-comparabile | MEDIUM | HIGH | Template obligatoriu. PR review pentru fiecare interviu la început. |
| Validation levels contestate | MEDIUM | LOW | Definiție clară în acest doc. Board Directive dacă apare debate. |
| Reuse audits false-negative → construim ceva ce exista | MEDIUM | MEDIUM | Sursa oficială e MASTER_PLATFORM_STATE. Actualizare regulată. AI Copilot verifică. |
| Reuse audits false-positive → nu construim ce e nevoie | LOW | HIGH | Audit-ul cere justificare explicită și founder approval pentru BUILD NEW. |
| Bias în selectarea președinților intervievați | HIGH | HIGH | Founder documentează selecția (city, size, tip proprietate) în fiecare research report. Sample diversificat obligatoriu la V4. |
| ROADMAP devine paralizat („nu putem construi până nu avem V3") | MEDIUM | HIGH | Excepții clare: bugs, security, compliance. Board Directive poate face override cu justificare. |
| Knowledge Center devine lent la >100 docs | LOW | MEDIUM | Filesystem scaling limit ~500 docs. Migrare la MongoDB doar dacă atins. |
| Metodologia devine ritual bureaucratic | MEDIUM | HIGH | Board Review anual: ce ROI a adus? Ajustare. |

---

## 19. Recomandarea finală

**Adoptă metodologia RESEARCH → KNOWLEDGE → VALIDATION → PRODUCT ca metodologie oficială PropManage**, cu următoarele condiții:

1. **Publicare imediată** a acestui document în Knowledge Center (auto — deja în audits/).
2. **Board Directive** care declară acest doc referință oficială (poate fi generat de founder ca `board/directives/DIRECTIVE_RESEARCH_DRIVEN_EVOLUTION.md`).
3. **Faza 1 execution** — creare foldere + PATH_RULES + templates (1 oră E1).
4. **Primul interviu în ≤14 zile** — founder commitment.
5. **Retroactive Reuse Audit** pe top 5 features din ROADMAP curent — validate existing pipeline.
6. **Board Review la 90 zile** — rapoartez metric-uri: interviuri făcute, patterns identificate, features cu V3+, decizii bazate pe research vs intuiție.
7. **Fără built-out prematur** — Faza 8 (AI-assisted) NU se face până când datele nu justifică ROI.

**Regula sacră**: **NU CONSTRUIM METODOLOGIA MAI COMPLEX DECÂT REZULTATELE**. Dacă în 90 zile nu avem 15+ interviuri și 3+ patterns concrete, metodologia rămâne minimă (Markdown + Knowledge Center) — nu se investește în UI, dashboards, AI-driven pattern detection.

**Valoare așteptată**:
- Reduce risc de over-build cu 40-60% (features validate first).
- Crește product-market fit (ceea ce ne dorim: PMF).
- Creează asset unic în piață: baza de cunoștințe validate din teren despre asociații de proprietari din România — greu de replicat de competitori.
- Devine story pentru investitori / parteneri: „construim doar ce e validat de 25+ președinți".

---

## Metadata

- **Versiune**: 2026-07-31
- **Referință oficială pentru**: toate dezvoltările PropManage începând cu Q3 2026.
- **Related docs**:
  - MASTER_PLATFORM_STATE.md (SSOT platformă)
  - MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md (governance viu)
  - PRD.md (product requirements)
  - board/ROADMAP_V2.md (roadmap)
  - product/00_PRODUCT_CONSTITUTION.md (constitution)
- **Status**: STRATEGY (aprobare founder pentru execuție Faza 1).
- **Next review**: 90 zile după Faza 1 completed.
