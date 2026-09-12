# PATTERN REGISTRY

**Artifact Type**: REGISTRY
**Owner**: Fondator (danieligna1@gmail.com)
**Last Review**: 2026-02-06
**Schema**: PatternID · Description · Confirmations · Maturity · EvidenceInterviews · Confidence · ConflictingEvidence · Recommendation
**Purpose**: Sursa unică de adevăr pentru toate pattern-urile emise din interviurile de research. Fiecare pattern se maturizează pe măsură ce acumulează confirmări.

> **Metodologie** (obligatorie, aprobată de Fondator):
> - 1 conf = **Observation**
> - 2 conf = **Emerging Pattern**
> - 3-4 conf = **Validated Pattern Candidate** (recomandare pentru Research Report)
> - 5+ conf = **High Confidence Pattern**
> - **Confidence Score** = `confirmations / target(15) × 100`
>   - 0-25% = Low · 25-50% = Medium · 50-75% = Medium-High · 75-100% = High
> - **Contradicții**: NU șterg pattern-ul, marchează `ConflictingEvidence` și reduc Confidence.
> - **Recomandare**: niciun Product Requirement până la nivel Validated Pattern Candidate.

## Schema Fields

| Field | Description |
|---|---|
| PatternID | Cod unic P-NNN. |
| Description | Fraza-rezumat. |
| Confirmations | Nr. total interviuri care confirmă. |
| Maturity | Observation · Emerging Pattern · Validated Pattern Candidate · High Confidence Pattern. |
| EvidenceInterviews | InterviewID-uri (comma-separated). |
| Confidence | Low · Medium · Medium-High · High (bazat pe scoring). |
| ConflictingEvidence | InterviewID-uri care contrazic (dacă există). |
| Recommendation | Product / Research / None. |

## Entries — ordonate după Maturity descrescător apoi PatternID

### Emerging Pattern (2 confirmări — sub Validated Candidate)

| PatternID | Description | Confirmations | Maturity | EvidenceInterviews | Confidence | ConflictingEvidence | Recommendation |
|---|---|---|---|---|---|---|---|
| P-002 | Unstandardized president succession | 2 | Emerging Pattern | AP-002, AP-003 | Low (13%) | — | Research (priority for AP-004) |
| P-003 | WhatsApp as communication channel (nuance: primaritate variabilă cu vârsta) | 2 | Emerging Pattern | AP-002, AP-003 | Low (13%) | — (dar evidence heterogen) | Research |
| P-004 | Preventive maintenance preferred over reactive | 2 | Emerging Pattern | AP-002, AP-003 | Low (13%) | — | Research (priority for AP-004) |
| P-005 | Incident & work traceability absent → legal risk | 2 | Emerging Pattern | AP-002, AP-003 | Low (13%) | — | Research |

### Observation (1 confirmare)

| PatternID | Description | Confirmations | Maturity | EvidenceInterviews | Confidence | ConflictingEvidence | Recommendation |
|---|---|---|---|---|---|---|---|
| P-001 | Infrastructure aging in **post-2000** buildings | 1 | Observation | AP-003 | Low (7%) | — | Research |
| P-006 | Individual water metering requested | 1 | Observation | AP-003 | Low (7%) | — | Research |
| P-007 | Safety equipment gaps triggered by prior incidents | 1 | Observation | AP-003 | Low (7%) | — | Research |
| P-008 | Initial evaluation cost = decision barrier | 1 | Observation | AP-002 | Low (7%) | — | Research |
| P-009 | Market price awareness gap among owners | 1 | Observation | AP-002 | Low (7%) | — | Research |
| P-010 | Specialist trust deficit → verification demand | 1 | Observation | AP-002 | Low (7%) | — | Research |
| P-011 | Insufficient documentation → legal risk | 1 | Observation | AP-002 | Low (7%) | — | Research |
| P-013 | Hybrid legal + digital communication required | 1 | Observation | AP-002 | Low (7%) | — | Research |
| P-014 | Presidents need legal/personal liability protection | 1 | Observation | AP-002 | Low (7%) | — | Research |

## Maturity Summary

| Maturity | Count | % of Total |
|---|---|---|
| Observation | 9 | 69% |
| Emerging Pattern | 4 | 31% |
| Validated Pattern Candidate | 0 | 0% |
| High Confidence Pattern | 0 | 0% |
| Conflicting Evidence | 0 | 0% |
| **TOTAL** | **13** | 100% |

## Research Analytics — Top Themes

### Top-3 problems cross-confirmate (2+ interviuri)
1. **Governance/Documentation** cluster — P-002 (succession) + P-005 (traceability) + P-011 (legal risk) → tema emergentă puternică
2. **Preventive Maintenance** (P-004)
3. **Communication mix** (P-003)

### Top-3 problems în curs de validare (Observation → next stage-gate)
1. **Trust/Verification** cluster — P-008 + P-010 (specialist trust, cost barrier)
2. **Legal Risk / President Protection** cluster — P-011 + P-014
3. **Financial Literacy Gap** — P-009 (locatarii cu prețuri de referință vechi)

### Contradicții
0 (dar 1 nuanță semnalată la P-003 pentru follow-up)

## Approved for Product Blueprint
**NONE** (blocat — niciun pattern nu a atins Validated Pattern Candidate = 3-4 confirmări)

## Approved for next Research Report
**NONE** (methodology impune ≥3 interviuri Validated + ≥1 Validated Pattern Candidate)
