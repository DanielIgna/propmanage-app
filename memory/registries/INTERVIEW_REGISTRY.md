# INTERVIEW REGISTRY

**Artifact Type**: REGISTRY
**Owner**: Fondator (danieligna1@gmail.com)
**Last Review**: 2026-08-14
**Schema**: InterviewID · Date · AssociationBloc · YearBuilt · Apartments · PresidentTenure · Platform · Status · FilePath
**Purpose**: Sursă unică de adevăr pentru toate interviurile validate. Consumat de Research Coverage Matrix (`/admin/research-coverage`).

> Reguli metodologice: (1) intrare doar la status `Validated`; (2) fiecare interviu are file individual; (3) target Fondator: 15-20 Validated interviews înainte de dezghețarea Feature Freeze.

## Schema Fields

| Field | Description |
|---|---|
| InterviewID | Cod unic (AP-NNN pentru Association President). |
| Date | ISO date. |
| AssociationBloc | Denumire scurtă adresă/zonă. |
| YearBuilt | An construcție. |
| Apartments | Nr. apartamente. |
| PresidentTenure | Vechime president. |
| Platform | Platformă existentă declarată (sau —). |
| Status | Validated · Pending · Rejected. |
| FilePath | Cale relativă. |

## Entries

| InterviewID | Date | AssociationBloc | YearBuilt | Apartments | PresidentTenure | Platform | Status | FilePath |
|---|---|---|---|---|---|---|---|---|
| AP-001 | 2026-08-14 | Florești, Cluj (Adrian Popa) | 2019 | 16 | [NECUNOSCUT] | [NECUNOSCUT] | Validated | memory/audits/INTERVIEW_2026-08-14_FLORESTI-CLUJ-AP-001.md |
| AP-002 | 2026-02-06 | Mehedinți (Ilie, P+4, 2 scări) | 1976 | 20 | 40+ ani | — | Validated | memory/audits/INTERVIEW_2026-02-06_MEHEDINTI-ILIE.md |
| AP-003 | 2026-02-06 | Negoiu 8D (Adriana) | 2006 | 13 | ~1 an | — | Validated | memory/audits/INTERVIEW_2026-02-06_NEGOIU-8D.md |
| AP-004 | 2026-08-14 | Negoiu nr. 10 (Mihăilă) | 1975 | 40 | 10+ ani | [NECUNOSCUT] | Validated | memory/audits/INTERVIEW_2026-08-14_NEGOIU-10-AP-004.md |
| AP-005 | 2026-08-14 | Soporului nr. 5 (Bradea) | 2018 | 130 | 7+ ani | [NECUNOSCUT] | Validated | memory/audits/INTERVIEW_2026-08-14_SOPORULUI-5-AP-005.md |
| AP-006 | 2026-08-14 | West Conect / Iulius Mall (Răzvan) | 2019 | 286 | ~4 ani | eBloc | Validated | memory/audits/INTERVIEW_2026-08-14_WEST-CONECT-AP-006.md |
| AP-007 | 2026-08-14 | Kincsö Pál | 2022 | 14 | [NECUNOSCUT] | Bloc Sistem | Validated | memory/audits/INTERVIEW_2026-08-14_KINCSO-PAL-AP-007.md |
| AP-008 | 2026-08-14 | Str. Predeal nr. 34 (Paul Jeican) | 2008 | 10 | [NECUNOSCUT] | [NECUNOSCUT] | Validated | memory/audits/INTERVIEW_2026-08-14_PREDEAL-34-AP-008.md |
| AP-009 | 2026-08-14 | Mehedinți nr. 23 (Sandu Pop) | 1976 | 104 | ~3 ani | eBloc | Validated | memory/audits/INTERVIEW_2026-08-14_MEHEDINTI-23-AP-009.md |
| AP-010 | 2026-08-14 | Mehedinți nr. 17 (Cristian, 5 scări) | 1976 | 104 | [NECUNOSCUT] | [NECUNOSCUT] | Validated | memory/audits/INTERVIEW_2026-08-14_MEHEDINTI-17-AP-010.md |

## Notă structurală
- **AP-008**: 10 apartamente + 5 case (structură mixtă, unicat în cohort).
- **AP-009 și AP-010**: aceeași stradă (Mehedinți), aceeași dimensiune (104 apts), an identic (1976) — DAR asociații distincte (numere diferite, presidenți diferiți). **NU sunt duplicate**.

## Coverage Metrics — actualizate 14 Aug 2026

- **Total Validated Interviews**: **10** / 15-20 (50-67% progress spre target)
- **Feature Freeze**: rămâne ACTIV (dezghețare la ≥3 Validated Pattern Candidate)

### Distribuție pe anul construcției (10 interviuri)
- **Pre-1980**: 4 (40%) — AP-002 (1976), AP-004 (1975), AP-009 (1976), AP-010 (1976)
- **1980-2000**: 0 (**GAP CONFIRMAT**)
- **Post-2000**: 6 (60%) — AP-001 (2019), AP-003 (2006), AP-005 (2018), AP-006 (2019), AP-007 (2022), AP-008 (2008)

### Distribuție pe nr. apartamente
- **≤15**: 2 (20%) — AP-003, AP-007
- **16-30**: 2 (20%) — AP-001, AP-002
- **31-50**: 1 (10%) — AP-004
- **51-100**: 0
- **101-150**: 3 (30%) — AP-005, AP-009, AP-010
- **>150**: 1 (10%) — AP-006 (286)
- **Mixed apt+casă**: 1 (10%) — AP-008 (10+5)

### Distribuție pe vechime președinte
- **[NECUNOSCUT]**: 4 (40%) — AP-001, AP-007, AP-008, AP-010
- **1-3 ani**: 2 (20%) — AP-003 (~1), AP-009 (~3)
- **4-9 ani**: 2 (20%) — AP-005 (7), AP-006 (~4)
- **10+ ani**: 2 (20%) — AP-002 (40+), AP-004 (10+)

### Distribuție pe platformă existentă
- **eBloc**: 2 (20%) — AP-006, AP-009
- **Bloc Sistem**: 1 (10%) — AP-007
- **Fără platformă declarată**: 7 (70%) — AP-001..AP-005, AP-008, AP-010

### Localizare declarată
- **Cluj**: 1 (AP-001 Florești)
- **[NECUNOSCUT / neclar]**: 9 (90%) — semi-anonymized. **GAP MAJOR**.
