# PATTERN_TEMPLATE — Template pentru Documentarea Pattern-urilor de Piață

> **Uz**: copiază și redenumește `PATTERN_<slug>.md` când identifici un pattern cross-interview.
> **Regulă**: un pattern nu se creează după un singur interviu. Minim 2 interviuri care confirmă același semnal.
> **Locație recomandată**: `/app/memory/audits/`.

---

# PATTERN — [Nume Pattern] · Identificat [YYYY-MM-DD]

## 1. Rezumat pattern

- **Descriere într-o singură frază**: [ce anume se repetă la mai mulți președinți]
- **Domeniu de aplicare**: [financiar / comunicare / mentenanță / transparență / etc.]
- **Prima apariție**: [interview_path + data]
- **Data identificării pattern-ului**: [YYYY-MM-DD]

## 2. Interviuri sursă (evidence)

Listează toate interviurile care confirmă acest pattern:

| # | Interview path | Data | Localitate | Confirmă direct |
|---|---|---|---|---|
| 1 | [path] | YYYY-MM-DD | [oraș] | [Y/N + citat scurt] |
| 2 | ... | ... | ... | ... |

## 3. Numărul de confirmări

- **Total interviuri care confirmă**: [N]
- **Diversitate geografică**: [orașe / regiuni]
- **Diversitate demografică**: [tipuri bloc / regim / vechime]

## 4. Nivel actual de validation

Conform metodologiei (V0-V5):

- [ ] V0 — Idee internă
- [ ] V1 — 1 președinte
- [ ] V2 — 5 președinți
- [ ] V3 — 10 președinți
- [ ] V4 — 25 președinți
- [ ] V5 — Implementat în producție

**Nivel actual**: V[N]

## 5. Formulare pattern

**Ce spun președinții** (paraphrase):
> [reformularea sintetică a mesajului comun]

**Ce citate confirmă**:
> "..." — [interviu path]
> "..." — [interviu path]

## 6. Analiza cauzelor

De ce apare acest pattern? Care sunt condițiile subiacente?

- **Cauza 1**: [descriere]
- **Cauza 2**: ...

## 7. Impact estimat

- **Frecvența problemei**: [% aproximat din asociațiile intervievate]
- **Impact business/personal pe utilizator**: [LOW/MEDIUM/HIGH/CRITICAL]
- **Cost al non-rezolvării** (per asociație/an): [dacă cuantificabil]

## 8. Soluții existente în piață

- **Ce fac președinții acum ca să compenseze**: [descriere]
- **Ce soluții alternative există**: [competitori / hărtie / Excel]
- **De ce nu sunt suficiente**: [gap-uri identificate]

## 9. Compatibilitate cu PropManage

- **Module existente relevante** (din MASTER_PLATFORM_STATE):
  - [modul 1] — [rezolvă parțial / total / nu]
  - [modul 2] — ...
- **Gap real identificat**: [dacă există, descris explicit]

## 10. Feature request generat

Dacă pattern-ul justifică un feature nou:

- **Feature title**: [descriere scurtă]
- **User story**: „Ca [rol], vreau să [acțiune], pentru că [motiv]."
- **Acceptance criteria** (draft): [3-5 puncte]
- **Reuse audit needed**: [Y — obligatoriu]

## 11. Recomandare acțiune

- [ ] Continuă research (pattern nu are suficientă validation)
- [ ] Escaladează la Research Report (pattern V3+)
- [ ] Cere Reuse Audit (pattern V3+ care justifică potențial feature)
- [ ] Reject (pattern confirmat dar irelevant pentru PropManage)

## Metadata

- **Owner pattern**: [nume research analyst]
- **Data ultimului update**: [YYYY-MM-DD]
- **Related patterns**: [paths PATTERN_*.md complementare sau contradictorii]
- **Related MASTER sections**: [secțiuni din MASTER_PLATFORM_STATE relevante]
