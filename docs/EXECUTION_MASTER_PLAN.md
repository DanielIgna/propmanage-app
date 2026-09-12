# EXECUTION MASTER PLAN — PropManage Commercial Platform 1.0 → 3.0
**Răspuns la Directive 028 + 030 + 031 · Program Director/PMO · Iun 2026**
Program ID: **PGM-1**. Completează MASTER_ROADMAP_2026.md (027+029) cu scope-ul nou aprobat:
Specialist OS (SOS), Multi-Profile, e-Factura, UX friction pass + plan de execuție pe release-uri.

---

## RELEASE PLAN (Step 3, Directive 030)

### R0.8 — „Foundation Complete" · Luna 1 · ~18 credite
Obiectiv business: GI-5P MVP complet (Twin vandabil cu riscuri+predicții) + email live.
| Sprint | Scope | Credite | Dependențe |
|--------|-------|---------|------------|
| **S1** (R0.8-S1) | GI-5P Sprint 2: DNA v2 provenance + Health Decay + Risk Engine (spec aprobat) | 16 | GI-5P S1 ✅ |
| **S2** (R0.8-S2) | Resend live: verificare DNS + test + config prod + docs | 2 | 🔴 USER: DNS Rackhost |
DoD: risc cu dovezi + mitigare CTA pe proprietatea demo; email tranzacțional trimis real.
Rollback: feature-flags pe carduri noi; zero migrații distructive.

### R0.9 — „Commercial Ready" · Luna 2 · ~22 credite
Obiectiv business: MCP tehnic complet — se poate încasa.
| Sprint | Scope | Credite | Dependențe |
|--------|-------|---------|------------|
| **S3** (R0.9-S1) | Commercial hardening: pagină publică prețuri/ofertă audit, checkout polish, Stripe LIVE switch | 10 | 🔴 USER: claim Stripe |
| **S4** (R0.9-S2) | Integration Control Center (017/024: registry, health, diagnostics, test, incidents, CEO card) | 12 | resend_diag ✅ |

### R1.0 — „COMMERCIAL LAUNCH" 🚀 · Luna 3 · ~16 credite
Obiectiv business: PRIMUL CLIENT PLĂTITOR.
| Sprint | Scope | Credite | Dependențe |
|--------|-------|---------|------------|
| **S5** (R1.0-S1) | e-Factura RO + facturare automată (obligație legală venit) | 10 | S3 |
| **S6** (R1.0-S2) | Launch hardening: onboarding oraș pilot, rotire chei, monitoring, checklist producție | 6 | S2, S3 |
NON-COD (USER): 5-10 specialiști reali verificați în orașul pilot.

### R1.1 — „Specialist OS MVP" · Luna 4-5 · ~32 credite
Obiectiv business: specialiștii lucrează INDEPENDENT (Specialist First, 031).
Strategie: EXTINDE dashboardul specialist existent (jobs, oferte, wallet, rating ✅) — zero rescriere.
| Sprint | Scope | Credite |
|--------|-------|---------|
| **S7** (R1.1-S1) | SOS-1: Profil profesional public (portofoliu, galerie, certificate, verificare, zonă acoperire, limbi, pachete de preț) | 12 |
| **S8** (R1.1-S2) | SOS-2: Calendar disponibilitate + booking + lead inbox unificat + response/acceptance/completion rate | 10 |
| **S9** (R1.1-S3) | SOS-3: Oferte (quotes) → contracte → facturi (reuse e-Factura S5) + revenue dashboard specialist | 10 |

### R1.2 — „Marketplace Independence" · Luna 5-6 · ~29 credite
Obiectiv business: marketplace cu supervizare minimă; venit recurent în creștere.
| Sprint | Scope | Credite |
|--------|-------|---------|
| **S10** (R1.2-S1) | GI-4b AI Memory (lecții → Command Center + Playbooks) | 9 |
| **S11** (R1.2-S2) | Multi-Profile Professionals (identități profesionale multiple, portofoliu/recenzii/prețuri/statistici independente, auth comun) | 12 |
| **S12** (R1.2-S3) | Client UX friction pass (Hick/Nielsen/Miller audit + fixuri; mobile-first; minim de decizii per flux) | 8 |

### R2.0 — „AI OPERATING SYSTEM" · Luna 6-9 · ~116 credite
Obiectiv business: >90% autonomie operațională — adminul doar aprobă.
| Sprint | Scope | Credite |
|--------|-------|---------|
| **S13-14** (R2.0-S1/2) | Command Center 2.0 (Directiva 020, 14 secțiuni, include Execution Dashboard software) | 30 |
| **S15** (R2.0-S3) | Mission Mode (021) | 26 |
| **S16** (R2.0-S4) | Adaptive Autonomy (022: Explore/Guide/Assist + clase Safe/Medium/Critical) | 20 |
| **S17** (R2.0-S5) | Autonomy Evolution + Executive Advisor (024+025: timeline, event log, Explain CEO, Forecast, Daily Brief) | 40 |

### R2.5 — „BIOS" · Luna 10-11 · ~48 credite
| **S18-19** | BIOS (019: unified timeline, deployment markers, KPI relationships, module explainer, AI Investigator 2.0, A/B assistant) | 34 |
| **S20** | GI-4c Calibrare (gate: ≥30 outcome-uri reale — până atunci există) + GI-5 Constituție executabilă | 14 |

### R3.0 — „BUSINESS DIGITAL TWIN" · Luna 12+ · ~70 credite
| **S21-22** | Business Digital Twin (026) | 40 |
| **S23** | GI-5D Interior Intelligence MVP (linie nouă de venit: design interior) | 30 |

---

## BUGET ACTUALIZAT (include scope nou 028: SOS+Multi-profile+e-Factura+UX = +68 credite)
| | Implementare | Notă |
|---|---|---|
| Minim | ~250 | doar critical path, scope tăiat |
| **Realist** | **~341** | planul de mai sus |
| Maxim | ~470 | cu regresii/schimbări scope |
| +15% contingency | **~392** | recomandat operațional |
| +25% contingency | ~426 | conservator |
| Emergency reserve | +30 | incidente majore |

## TOTAL COST OF OWNERSHIP (Faza 14, Directiva 028)
| Categorie | Lunar | Anual (an 1) |
|-----------|-------|--------------|
| Implementare (dezvoltare, medie) | ~28 credite | **~341 credite** (+buffer 50) |
| Hosting Emergent (app deployat) | **50 credite** | **600 credite** (~$120) |
| Mentenanță + bugfix post-sprint | ~5 credite | ~60 credite |
| LLM (Emergent Universal Key, pay-as-you-go) | $10-30 la start → $50-100 la 100+ clienți | ~$300-800 |
| Email Resend | $0 (free ≤3k/lună) → $20 la scală | $0-240 |
| Stripe | 0 fix; ~1,4%+1,8 RON per tranzacție (cost pe venit) | variabil |
| Domeniu propmanage.ro | deținut | ~$15 |
| Storage/DB/bandwidth/monitoring | incluse în hosting Emergent | 0 |
| Suport clienți | timp fondator → part-time de la ~100 clienți | extern |
| **TOTAL AN 1** | | **~1.000-1.100 credite** + ~$400-1.000 servicii |

## EXECUTION DASHBOARD (Step 5, 030) — decizie de Guardian (031)
Un dashboard software de execuție NU trece Commercial Gate acum (nu accelerează venitul).
Decizie: tracking în **/app/docs/EXECUTION_DASHBOARD.md** (actualizat la fiecare sprint) +
raport executiv după fiecare sprint (Step 8). Versiunea software se integrează în
Command Center 2.0 (S13) — zero duplicare.

## QUALITY GATES (Step 4) — aplicate fiecărui sprint
1 Architecture Review (extensie, nu refactor — 012) · 2 UX Review (design_guidelines + testid) ·
3 Security Review (RBAC, chei .env) · 4 Performance (fără N+1, agregări) · 5 Regression
(testing_agent + suite pytest) · 6 AI Review (015: provenance, No Fake Precision) ·
7 Business Review (016: ce outcome se îmbunătățește) · 8 Commercial Review (014: 90-day rule).

## FINAL EXECUTIVE REPORT (Faza 15, 028)
- **Cât mai e de lucru?** 23 sprinturi / 8 release-uri / ~341 credite realist.
- **Bani de rezervat (12 luni)**: ~400 credite implementare + 600 hosting + ~60 mentenanță ≈ **~1.050-1.100 credite** + $400-1.000 servicii externe.
- **Primul de construit**: S1 (GI-5P S2) ∥ S2 (Resend — după DNS-ul tău) → S3 (comercial).
- **În paralel**: S1∥S2, S3∥S4, S7∥S10, S13∥S16, S18∥S20, S21∥S23 → economie ~30% timp.
- **Poate aștepta**: tot R2.0+ (AI OS, BIOS, BDT, GI-5D) — după clienți plătitori.
- **Lansare comercială**: luna 3 (realist) — condiționată de DNS+Stripe+specialiști pilot (USER).
- **Specialiști independenți**: luna 5 (R1.1 complet).
- **Marketplace cu supervizare minimă**: luna 6 (R1.2).
- **Venit recurent realist**: luna 2-3 (primele abonamente), MRR semnificativ luna 4-6.
- **Cash-flow pozitiv operațional**: ~10-20 clienți plătitori (luna 4-6; costurile operaționale
  sunt mici — investiția reală e dezvoltarea). Cu amortizarea dezvoltării: luna 8-12.
- **>90% autonomie**: luna 9-12 (R2.0 + volum de date reale).
- **Cele mai mari riscuri**: funnel comercial nedovedit (1/94 acceptare pe demo) · blocajele
  USER (DNS/Stripe/specialiști) · calibrare AI pe date demo.
- **Cele mai mari oportunități**: Audit First cu pipeline predictiv deja live · SOS = magnet
  pentru specialiști (rețeaua = șanțul competitiv) · GI-5D = a doua linie de venit.
