# STRATEGIC KNOWLEDGE DOMAINS CHARTER

**Artifact Type**: DOCUMENT
**Version**: v1.0
**Date**: 2026-02-06
**Owner**: Fondator (danieligna1@gmail.com)
**Status**: ACTIVE
**Classification**: Strategic Charter — governance for cross-domain research
**Precedence**: This charter is authoritative for any future research on Building Context or Regulatory Diagnostics. Any convergence attempt must reference this document.

---

## 1. Purpose

Acest charter stabilește **regula de separare între trei domenii de cunoaștere distincte** pe care PropManage le investighează sau le va investiga. Scopul principal este să **prevină contaminarea conceptuală** între ele și să **protejeze vision-ul original PropManage** de a fi înghițit de o direcție de cercetare nouă înainte de validare.

---

## 2. The Three Knowledge Domains

### 2.1 Domain A — PropManage Core (Property / Property Memory)
> **Ce știu despre proprietatea mea?**

Perimetru: Digital Twin · Cartea Tehnică Digitală · documentație · active · instalații · istoricul intervențiilor · mentenanță · House Health · Property Value Index (PVI) · riscuri · recomandări · specialiști · lucrări · marketplace · documente · evoluția proprietății.

Rol: memoria tehnică și operațională a unei proprietăți individuale, verificate.

**Nu trebuie atinsă. Este vision-ul PropManage.**

### 2.2 Domain B — Building Context (External Reference)
> **În ce clădire / ansamblu / context fizic se află proprietatea mea?**

Perimetru: bloc · an construcție · tipologie · număr apartamente · context clădire · relația apartament → clădire · surse externe (HartaBlocuri).

Rol: date de referință externe, folosite pentru context, NU pentru adevăr verificat.

**Regula strictă: `Reference ≠ Verified`.** Nicio informație din Domain B nu devine automat adevăr al Domain A.

### 2.3 Domain C — Regulatory Diagnostics (Legal & Transaction)
> **Ce trebuie să fie cunoscut/verificat/realizat pentru ca proprietatea să poată fi tranzacționată, evaluată sau considerată conformă?**

Perimetru: DDT · DPE · energie · CO₂ · plumb · azbest · gaz · electricitate · canalizare · termite · riscuri naturale/tehnologice · documente tranzacție · valabilitate · jurisdicție · statut legal/reglementar.

Rol: evidence tehnică generată în context legal/tranzacțional.

**Regula strictă: NU se convertește automat în feature PropManage.** Se cercetează, se validează, apoi (posibil) se integrează.

---

## 3. Non-Convergence Rules (INVARIANT)

Următoarele afirmații NU se pot face în niciun document strategic sau tehnic PropManage până la finalizarea Strategic Convergence Audit:

- ❌ „PropManage va deveni platformă DDT"
- ❌ „HartaBlocuri va fi integrată în PropManage"
- ❌ „Digital Twin + HartaBlocuri + DDT vor forma un singur modul"
- ❌ „Regulatory Diagnostics este noul core al produsului"
- ❌ „PropManage este platforma de tranzacție imobiliară"

**Toate acestea sunt concluzii premature.**

---

## 4. Provenance Rule (canonical)

Orice fapt din Domain B sau C care se propagă către o proprietate individuală (Domain A) trebuie să poarte:

```
{
  value:               <ce afirmă>,
  source:              <cine/ce este sursa>,
  source_type:         Reference | Official | Reported | Observed | Verified,
  date:                <când s-a produs>,
  confidence:          low | medium | high,
  verification_status: verified | unverified,
  jurisdiction:        <RO | FR | EU | ...>  (pentru Domain C)
}
```

Fără provenance complet, un fapt din Domain B/C **nu are voie** să înlocuiască un fapt Verified din Domain A.

Referință: `BUILDING_TYPOLOGY_FOUNDATION_AUDIT_v1.0.md` §3.9-3.13 pentru definiții canonice.

---

## 5. Convergence Gate

Convergența A+B+C într-un model produs unificat este AUTORIZATĂ **numai** după toate condițiile de mai jos:

1. ✅ HartaBlocuri Source Value Audit finalizat (Domain B)
2. ✅ France DDT/DPE Reference Audit finalizat (Domain C reference)
3. ✅ Romania Property Transaction Regulatory Audit finalizat (Domain C RO)
4. ✅ Cohort research ≥ 15 interviuri validate (per BD-RDPE)
5. ✅ ≥ 3 Validated Pattern Candidates specifice pe DDT-driven demand în RO
6. ✅ Legal review complet (GDPR + data ownership + regulatory lock-in risk)
7. ✅ Strategic Convergence Audit v1.0 documentat
8. ✅ Board Directive explicit de convergență

Până atunci: **Separation Before Convergence · Evidence Before Integration**.

---

## 6. Enterprise Knowledge Center Structure

Structura autoritativă în EKC:

```
ENTERPRISE KNOWLEDGE CENTER
│
├── PRODUCT KNOWLEDGE
│   └── PropManage Core (Product Blueprint · Property DNA · Function Map)
│
├── KNOWLEDGE DOMAINS
│   ├── Domain A — Property / PropManage Core
│   ├── Domain B — Building Context
│   │   └── HartaBlocuri = research/source candidate
│   └── Domain C — Regulatory Diagnostics
│       └── DDT / DPE = research/source candidate
│
├── RESEARCH INTELLIGENCE
│   ├── Interviews (AP-001..AP-010 → AP-011+)
│   ├── Observations
│   ├── Emerging Patterns
│   ├── Validated Patterns
│   ├── Research Reports
│   └── Evidence / Provenance
│
└── STRATEGIC CONVERGENCE
    └── (goală — numai după validare completă)
```

---

## 7. HartaBlocuri Positioning (canonical)

- **HartaBlocuri = Research Asset / Building Context Pilot Source**
- **NU** = infrastructură critică PropManage
- **NU** = adevăr despre proprietăți
- **DA** = potențială Reference Data source (cu provenance explicit)

Bugetul de research pentru HartaBlocuri Cluj (~180 €, ~3600 blocuri) este AUTORIZAT dacă și numai dacă Founder decide pilot explicit după HartaBlocuri Source Value Audit v1.0.

---

## 8. Framework Metodologic (invariant)

Toate cele 3 domenii urmează același pipeline (BD-RDPE):

```
Interview → Observation → Emerging Pattern → Validated Pattern → Research Report → Blueprint → Roadmap → Build
```

**Zero abateri** de la pipeline. Nici o direcție (nici Domain B, nici Domain C) nu poate „sări" etape de validare.

---

## 9. Ordinea auditurilor de cercetare (autorizată)

1. ✅ `HARTABLOCURI_SOURCE_VALUE_AUDIT_v1.0.md` — Domain B source pilot
2. ✅ `REGULATORY_DIAGNOSTICS_FRANCE_REFERENCE_AUDIT_v1.0.md` — Domain C reference model
3. ✅ `ROMANIA_PROPERTY_TRANSACTION_REGULATORY_AUDIT_v1.0.md` — Domain C RO reality
4. ⏸️ `STRATEGIC_CONVERGENCE_AUDIT_v1.0.md` — DOAR după (1)+(2)+(3) livrate

---

## 10. Final Principle

> **PropManage Core rămâne vision-ul central. Building Context și Regulatory Diagnostics sunt research directions care pot deveni entry points sau layers ADIȚIONALE, dar NICIODATĂ înlocuitoare.**
>
> **Optionalitatea strategică este proprietatea cea mai valoroasă a PropManage. Nu se sacrifică pentru convergență prematură.**

---

**End of STRATEGIC_KNOWLEDGE_DOMAINS_CHARTER_v1.0.**
