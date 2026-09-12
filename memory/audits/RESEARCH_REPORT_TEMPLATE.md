# RESEARCH_REPORT_TEMPLATE — Template pentru Rapoarte de Cercetare Consolidate

> **Uz**: copiază și redenumește `REPORT_<topic>_YYYY-MM-DD.md` când consolidezi pattern-uri într-un raport.
> **Când se scrie**: după acumularea a minim 10 interviuri într-un domeniu specific (financial, comunicare, mentenanță, etc.).
> **Locație recomandată**: `/app/memory/audits/`.

---

# RESEARCH REPORT — [Topic] · [YYYY-MM-DD]

## 1. Executive Summary

- **Tema raportului**: [ex. „Nevoi financiare la asociațiile de proprietari"]
- **Perioadă research**: [YYYY-MM-DD → YYYY-MM-DD]
- **Interviuri consolidate**: [N]
- **Pattern-uri identificate**: [N]
- **Top 3 nevoi validate ≥ V3**: [enumerare]
- **Recomandare finală**: [SCALE / PILOT / REJECT / MORE_RESEARCH]

## 2. Metodologie research

- **Cum au fost selectați președinții**: [criterii sample]
- **Diversitate geografică**: [regiuni acoperite]
- **Diversitate demografică**: [tipuri bloc, dimensiuni, vechime]
- **Bias potențiale**: [ce ne lipsește din sample]

## 3. Interviuri consolidate

Listă cu toate interviurile care contribuie la raport:

| # | Interview path | Data | Localitate | Nr. apartamente |
|---|---|---|---|---|
| 1 | [path] | YYYY-MM-DD | [oraș] | [N] |
| ... | ... | ... | ... | ... |

## 4. Pattern-uri identificate

Pentru fiecare pattern relevant temei:

### Pattern 1: [Nume]
- **Path**: [PATTERN_*.md]
- **Validation level**: V[N]
- **Confirmări**: [N interviuri]
- **Rezumat**: [1-2 fraze]
- **Impact business**: [LOW/MEDIUM/HIGH/CRITICAL]

### Pattern 2: ...

## 5. Feature-uri rezultate

Pentru fiecare pattern care justifică un feature:

| Feature | Pattern sursă | Validation | Reuse audit path | Prioritate propusă |
|---|---|---|---|---|
| [nume feature] | [PATTERN path] | V[N] | [AUDIT path] | [P0/P1/P2/P3] |

## 6. Gap Analysis vs MASTER_PLATFORM_STATE

- **Nevoi complet acoperite** de PropManage: [enumerare + procent]
- **Nevoi parțial acoperite** (necesită extindere existing modules): [enumerare]
- **Nevoi neacoperite** (gap real): [enumerare]

## 7. Reuse Analysis

Pentru fiecare feature nou propus în secțiunea 5:

- **Componente existente reutilizabile**: [enumerare din MASTER]
- **Ce trebuie extins**: [enumerare]
- **Ce trebuie construit de la zero**: [enumerare — trebuie justificat cu Reuse Audit]

## 8. Riscuri identificate

- **Riscuri de piață** (adopție, competitori, timing): [enumerare]
- **Riscuri de execuție** (technical debt, complexitate): [enumerare]
- **Riscuri de model** (revenue, monetization, sustainability): [enumerare]

## 9. Recomandări

Ordinea propusă pentru ROADMAP:

1. **Prioritate P0/P1** (V4+): [enumerare cu justificare]
2. **Prioritate P2** (V3): [enumerare]
3. **Prioritate P3** (V2): [enumerare — backlog]
4. **Nu recomandăm** (V0-V1 sau lipsă evidence): [enumerare cu motiv]

## 10. Next steps

- **Interviuri adiționale necesare**: [câte, pe ce topic, în ce regiuni]
- **Reuse audits de făcut**: [feature-uri care necesită audit înainte de decizie]
- **Board Directives propuse**: [dacă e cazul]
- **Timeline propus pentru implementare**: [luna de start pentru fiecare P0/P1]

## Metadata

- **Autor raport**: [nume research analyst]
- **Reviewed by**: [founder / partener]
- **Data publicării**: [YYYY-MM-DD]
- **Status**: [DRAFT / REVIEWED / APPROVED / SUPERSEDED]
- **Related MASTER_PLATFORM_STATE version**: [data audit master de referință]
