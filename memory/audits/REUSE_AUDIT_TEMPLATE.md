# REUSE_AUDIT_TEMPLATE — Template pentru Infrastructure Reuse Audit

> **Uz OBLIGATORIU**: Orice funcționalitate propusă trebuie să aibă un Reuse Audit publicat și aprobat înainte de a intra în ROADMAP.
> **Redenumire**: `AUDIT_<feature_slug>_YYYY-MM-DD.md`.
> **Sursă oficială**: Board Directive „Research-Driven Product Evolution" (2026-07-31).
> **Locație**: `/app/memory/audits/`.

---

# INFRASTRUCTURE REUSE AUDIT — [Feature Name]

## Feature propus

- **Titlu**: [nume clar și scurt]
- **Descriere**: [2-3 fraze]
- **User story**: „Ca [rol], vreau să [acțiune], pentru că [motiv]."
- **Business impact estimat**: [LOW / MEDIUM / HIGH / CRITICAL]

## Evidence (validare)

- **Interviews sursă**: [paths]
- **Patterns sursă**: [paths PATTERN_*.md]
- **Research Report sursă**: [path REPORT_*.md]
- **Validation level**: V[N]

**Regula V**: dacă `validation_level < V2`, audit-ul e rejected automat.

---

## Cele 7 întrebări obligatorii

### 1. Există deja această funcționalitate în PropManage?

- [ ] **DA — complet** → **DECIZIE: REJECT propunerea**. Path modul existent: [link]. Motivul pentru care nu e vizibil pentru utilizator: [discovery / UX / feature flag].
- [ ] **DA — parțial** → detalii mai jos.
- [ ] **NU**.

**Sursă verificată**: `MASTER_PLATFORM_STATE.md` versiunea [data].
**Verified against**: secțiunile 1, 4, 7, 15, 16.

### 2. Există un model similar / adiacent?

- [ ] **DA** → path: [link]. Motivul pentru care nu-l putem reutiliza direct: [text].
- [ ] **NU**.

**Sursă**: `MASTER_PLATFORM_STATE.md` + Ownership Matrix.

### 3. Există API reutilizabil?

- [ ] **DA — reutilizăm 100%** → endpoint(s): [enumerare]
- [ ] **DA — reutilizăm parțial + extindem** → endpoints existente + delta: [text]
- [ ] **NU — trebuie API nou** → justificare: [text]

**Sursă**: `MASTER_PLATFORM_STATE.md` secțiunea 5 (API Inventory).

### 4. Există componente frontend reutilizabile?

- [ ] **DA — reutilizăm** → componente: [enumerare cu paths în `/app/frontend/src/components/**`]
- [ ] **PARȚIAL** → extindere: [text]
- [ ] **NU** → justificare: [text]

**Sursă**: `/app/frontend/src/components/**` + `/pages/**`.

### 5. Există schema DB reutilizabilă?

- [ ] **DA — reutilizăm collections existente** → collections: [enumerare]
- [ ] **EXTINDEM cu câmpuri noi** → collection + câmpuri: [text]
- [ ] **DA — collection nou** → justificare + de ce nu se pot extinde cele existente: [text]

**Sursă**: `MASTER_PLATFORM_STATE.md` secțiunea 6 (Database Inventory).

### 6. Există documentație reutilizabilă?

- [ ] **DA** → docs: [paths]
- [ ] **NU** → trebuie doc nou

**Sursă**: Knowledge Center (`/api/founder/knowledge/tree`).

### 7. Există integrare în Knowledge Graph?

- [ ] **DA** → entity type: [name]
- [ ] **NU** → propus entity type nou: [name + properties]

**Sursă**: `kg_entities` collection + `routes/kg.py`.

---

## Ownership după implementare

- **Owner propus**: [modul + persoană]
- **Consumers așteptați**: [enumerare]
- **Integrare cu Ownership Matrix**: [update necesar Y/N]

## Decizie

- [ ] **REUTILIZĂM 100% EXISTENT** — nu construim nimic nou. Feature-ul se rezolvă prin discovery/UX/education.
- [ ] **EXTINDEM COMPONENTĂ EXISTENTĂ** — specificat în întrebările 1-7.
- [ ] **CONSTRUIM NOU** — justificat prin gap real. **Necesar Board Approval explicit**.

## Justificare decizie

[Text obligatoriu. Minim 3 fraze. Dacă „CONSTRUIM NOU", justificare care confirmă:
- Nu există alt mod
- Reutilizarea nu e fezabilă tehnic sau UX
- Ownership Matrix va fi updated
- Estimare effort dev + ownership post-implementare
]

## Impact asupra MASTER_PLATFORM_STATE

- **Secțiuni afectate** (dacă „CONSTRUIM NOU"):
  - Secțiunea 1: [+1 module dacă e route nou]
  - Secțiunea 5: [+N endpoints]
  - Secțiunea 6: [+N collections]
  - Secțiunea 15: [dacă e componentă monetizare]

## Aprobare

- **Founder / Board Directive necesar**: [DA pentru „CONSTRUIM NOU"]
- **Data aprobare**: [YYYY-MM-DD]
- **Aprobat de**: [nume]
- **Condiții / limitări**: [text opțional]

## Metadata

- **Auditor**: [nume — poate fi founder, research analyst sau E1]
- **Data audit**: [YYYY-MM-DD]
- **Related evidence**: [paths]
- **Status**: [DRAFT / PENDING_APPROVAL / APPROVED / REJECTED / SUPERSEDED]
- **ROADMAP entry link**: [dacă intră în ROADMAP, path către entry]
