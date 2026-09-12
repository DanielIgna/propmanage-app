# BOARD DIRECTIVE — Research-Driven Product Evolution

> **Directivă emisă**: 2026-07-31
> **Emitent**: Founder
> **Nivel**: Enterprise (obligatoriu pentru toate viitoarele decizii de produs)
> **Referință metodologie**: `RESEARCH_DRIVEN_PRODUCT_EVOLUTION_2026-07-31.md`

---

## 1. Declarație

Începând cu data acestei directive, PropManage adoptă metodologia oficială **RESEARCH → KNOWLEDGE → VALIDATION → PRODUCT** ca proces obligatoriu pentru orice dezvoltare de produs nouă.

Nu vom mai construi funcționalități pe baza presupunerilor. Construim doar pe bază de dovezi validate din teren.

---

## 2. Documente elevate la statut oficial (SSOT)

| Document | Rol oficial |
|---|---|
| `MASTER_PLATFORM_STATE.md` | SSOT pentru starea reală de implementare a platformei. |
| `RESEARCH_DRIVEN_PRODUCT_EVOLUTION_2026-07-31.md` | SSOT pentru metodologia de dezvoltare validată. |
| Această directivă | SSOT pentru guvernanța acestei metodologii. |
| `Platform Audits` (categorie Knowledge Center) | SSOT pentru toate auditurile și documentele canonice. |

---

## 3. Reguli obligatorii aprobate

1. **Validation Levels (V0-V5)** sunt metodologia oficială de validare.
   - V0-V1: rămân în `Concept`, nu intră în ROADMAP.
   - V2: eligibil pentru backlog (P3).
   - V3 (10+ interviuri): eligibil pentru P2.
   - V4 (25+ interviuri): eligibil pentru P0/P1.
   - V5: implementat și în producție.

2. **Product Requirement Pipeline** este proces oficial:
   ```
   Interviu → Pattern → Validation → Product Requirement → Reuse Audit → Roadmap → Development
   ```

3. **Infrastructure Reuse Audit** este obligatoriu înaintea oricărei dezvoltări noi. Fără audit publicat și aprobat, feature-ul nu intră în ROADMAP.

4. **Excepții aprobate** (pot ocoli metodologia):
   - Bugs critice de producție.
   - Vulnerabilități de securitate.
   - Cerințe legale sau compliance (GDPR, etc.).
   - Operațiuni de infrastructură (deploy, migrare, DevOps).

---

## 4. Ce NU se implementează în această fază

Următoarele componente sunt **explicit interzise** până la acumularea unei baze de 15-20 interviuri validate:

- Research Engine (modul dedicat)
- Automation Engine (pattern-detection automată)
- AI Extraction (auto-clasificare interviuri)
- Workflow automate pentru research
- Dashboard-uri noi
- API-uri noi
- Collections MongoDB noi
- Componente React noi

**Motiv**: aplicăm metodologia recursiv — nu construim infrastructură până când datele nu justifică ROI-ul.

---

## 5. Prioritatea absolută pentru următoarele săptămâni

Obiectivul NU este dezvoltarea de funcționalități. Obiectivul este:

1. Realizarea interviurilor cu președinții de asociații.
2. Identificarea pattern-urilor recurente.
3. Transformarea concluziilor în cerințe de produs.
4. Verificarea reutilizării infrastructurii existente.

---

## 6. Cadrul minimal aprobat

Se aprobă doar următoarele artefacte de documentație (fără cod, fără UI, fără DB):

- Template obligatoriu pentru interviuri: `INTERVIEW_TEMPLATE.md`
- Template pentru documentarea pattern-urilor: `PATTERN_TEMPLATE.md`
- Template pentru rapoarte research: `RESEARCH_REPORT_TEMPLATE.md`
- Template pentru reuse audits: `REUSE_AUDIT_TEMPLATE.md`

Toate localizate în `/app/memory/audits/` — auto-vizibile în Knowledge Center → `Platform Audits`.

---

## 7. Milestones și review

- **T+14 zile**: primul interviu documentat.
- **T+30 zile**: minim 5 interviuri, primul pattern draft.
- **T+60 zile**: minim 10 interviuri, primul Research Report.
- **T+90 zile**: **Board Review obligatoriu**. Evaluare:
  - Câte interviuri realizate?
  - Câte pattern-uri validate?
  - Câte features V3+ identificate?
  - Ce decizii de produs au fost fundamentate pe cercetare vs intuiție?

Dacă la T+90 zile nu există minim 15 interviuri și 3 pattern-uri, metodologia rămâne în forma minimă documentară. NU se investește în automatizare.

---

## 8. Excepții și override

Founder-ul își rezervă dreptul de override doar cu:
- Board Directive nou care justifică excepția.
- Referință explicită la limitările metodologiei.
- Angajament că feature-ul va fi validat retroactiv la V3+ în maxim 60 zile după implementare.

---

## 9. Semnătură

Directivă aprobată de: **Founder (Daniel Igna)**
Data: 2026-07-31
Valabilitate: până la abrogare printr-o directivă explicită viitoare.

**Următoarea revizuire**: T+90 zile.
