# INTERVIEW_TEMPLATE — Template Obligatoriu pentru Interviuri Președinți Asociații

> **Uz**: copiază acest fișier și redenumește-l `INTERVIEW_YYYY-MM-DD_ASOCIATIE-SLUG.md` când salvezi un interviu.
> **Locație recomandată**: `/app/memory/audits/` (până când folder-ul `/app/memory/research/interviews/` va fi aprobat separat).
> **Reguli**: toate cele 11 secțiuni sunt obligatorii. Nu șterge secțiuni. Dacă o secțiune nu se aplică, scrie "N/A" cu explicație.

---

# INTERVIU — [Nume Asociație / Bloc] · [YYYY-MM-DD]

## 1. Context

- **Intervievator**: [nume]
- **Data + ora**: [YYYY-MM-DD HH:MM]
- **Modalitate**: [față-în-față / online / telefon]
- **Durată**: [minute]
- **Consimțământ înregistrare**: [Y/N]
- **Sursa contactului**: [cum ai ajuns la președinte]

## 2. Profil bloc / asociație

- **Localitate**: [oraș, sector/cartier]
- **Nr. apartamente**: [număr]
- **Anul construcției**: [an]
- **Regim înălțime**: [P+n]
- **Tip proprietate**: [rezidențial / mixt / comercial]
- **Buget lunar mediu asociație**: [RON aproximativ]
- **Sistem management actual**: [Excel / soft dedicat / hârtie / combinație]
- **Nr. specialiști colaboratori (recurenti)**: [număr]
- **Vechime președinte**: [ani]
- **Alte roluri implicate**: [administrator, cenzor, contabil — care sunt și cine ține evidența]

## 3. Probleme identificate

Formatăm ca listă cu impact și frecvență.

- **P1**: [descriere problemă] — frecvență: [zilnic/lunar/anual] — impact: [LOW/MEDIUM/HIGH/CRITICAL] — cost estimat: [RON/an sau ore/lună]
- **P2**: ...
- **P3**: ...

## 4. Riscuri identificate

- **R1**: [risc operațional / financiar / legal / social / de reputație]
- **R2**: ...

## 5. Dovezi (citate directe)

Citate verbatim, marcate cu ghilimele și context.

> "..." — [ce se referea, când în conversație]

> "..." — [context]

## 6. Pattern-uri observate

- **Pattern-uri comune cu alte interviuri anterioare** (cross-reference paths):
  - [nume fișier interviu] — [ce anume se repetă]
- **Pattern-uri noi** (candidate care nu s-au mai văzut):
  - [descriere pattern nou]

## 7. Funcționalități sugerate (de intervievat)

Ce a cerut explicit sau implicit că ar avea nevoie.

- **FR1**: [descriere feature] — verbatim citat: "..."
- **FR2**: ...

## 8. Funcționalități existente în PropManage

Cross-reference cu MASTER_PLATFORM_STATE. Pentru fiecare FR de mai sus, identifică:

- **FR1** → **Deja implementat**: [modul + path în platformă] · [de ce nu-l folosește]
- **FR1** → **Parțial implementat**: [modul + ce lipsește]
- **FR1** → **Nu există**: [gap real]

## 9. Gap Analysis

- **Nevoi acoperite de PropManage**: [%] — [enumerare]
- **Nevoi neacoperite**: [enumerare cu tag]
- **Nevoi aspirationale** (viitor îndepărtat): [enumerare]
- **Nevoi rezolvate deja de alte soluții pe care le folosește**: [enumerare + care soluție]

## 10. Prioritate propusă

- **Business impact**: [LOW / MEDIUM / HIGH / CRITICAL]
- **Effort estimat** (dacă e știut): [XS / S / M / L / XL]
- **Blocher pentru**: [tip user / segment]
- **ROI potențial**: [descriere calitativă]

## 11. Nivel de validare (post-interview)

- **V nivel atins după acest interviu**:
  - Dacă acest interviu este primul care confirmă un pattern → **V1**
  - Dacă confirmă un pattern deja identificat în alte X interviuri → **V(X+1)** (dar maxim V4 până la implementare)
- **Confirmă / infirmă un pattern anterior**: [link path către PATTERN_*.md]
- **Interviuri necesare pentru validation upgrade**: [număr rămas până la V4]

## Metadata

- **Tags**: [asociație, bloc, financiar, mentenanță, comunicare, transparență, ...]
- **Related interviews**: [paths către interviuri conexe]
- **Related patterns**: [paths PATTERN_*.md]
- **Follow-up needed**: [Y/N] + [când / ce se urmărește]
- **Aprobare pentru includere în roadmap**: [PENDING / APPROVED / REJECTED]
