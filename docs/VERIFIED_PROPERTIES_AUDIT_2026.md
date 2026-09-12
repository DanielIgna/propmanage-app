# 🏛️ AUDIT EXECUTIV — Modulul „Imobile Verificate" (Verified Properties)
**Board Directive 054 · Iunie 2026 · Status: AȘTEAPTĂ APROBARE BOARD (GO/NO-GO)**
**Regulă respectată: ZERO cod scris. Doar audit + estimare.**

---

## 1. DIAGRAMA DE FLUX — Călătoria completă (existent vs. lipsă)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SELLER JOURNEY → PREMIUM SERVICES                        │
└─────────────────────────────────────────────────────────────────────────────┘

 [1] VÂNZĂTOR                [2] AUDIT TEHNIC            [3] IMOBIL VERIFICAT
 ┌──────────────┐            ┌──────────────┐            ┌──────────────────┐
 │ /imobile-    │   plată    │ audit_report │   4 gates  │ Listing publicat │
 │ verificate/  │──────────▶│ + Digital    │──────────▶│ Trust Score A+/A │
 │ sell         │  Stripe    │ Twin + Reco  │  admin OK  │ /imobile-        │
 │ ✅ EXISTĂ    │  ⚠️ DEMO   │ ⚠️ MANUAL    │  ✅ EXISTĂ │ verificate ✅    │
 └──────────────┘            └──────────────┘            └──────────────────┘
        │                                                        │
        │  pachete: Audit 350 RON · Twin 950 RON · Bundle       │ inquiry
        │  + Traseu C: audit imobil extern (Storia/Imobiliare)  ▼
        │  ✅ EXISTĂ                                    ┌──────────────────┐
        │                                               │ [4] VÂNZARE      │
        │                                               │ comision 2.5%    │
        │                                               │ ❌ NU EXISTĂ     │
        │                                               │ (nu există status│
        │                                               │  sold/reserved,  │
        │                                               │  nici facturare) │
        │                                               └──────────────────┘
        │                                                        │
        ▼                                                        ▼
 ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────────────┐
 │ [7] DIGITAL TWIN │◀──│ [6] CARTEA        │◀──│ [5] ONBOARDING CUMPĂRĂTOR│
 │ proiecte 3D, pins│    │ DIGITALĂ A CASEI  │    │ cont nou + transfer      │
 │ conversii, docs  │    │ (Property Book)   │    │ proprietate              │
 │ ✅ EXISTĂ        │    │ ❌ NU EXISTĂ      │    │ ❌ NU EXISTĂ             │
 │ (modul separat,  │    │ (istoric+docs+twin│    │ (inquiry rămâne lead     │
 │  nelegat de      │    │  nu se transferă  │    │  în admin, fără flux     │
 │  listing) ⚠️     │    │  la cumpărător)   │    │  de conversie)           │
 └──────────────────┘    └──────────────────┘    └──────────────────────────┘
        │
        ▼
 ┌──────────────────────────────────────────┐
 │ [8] SERVICII PREMIUM                     │
 │ House Health Plans + Billing ✅ EXISTĂ   │
 │ Marketplace + Concierge ✅ EXISTĂ        │
 │ ⚠️ NELEGATE de fluxul post-vânzare       │
 └──────────────────────────────────────────┘
```

**Legendă**: ✅ funcțional · ⚠️ parțial/manual · ❌ inexistent

---

## 2. CE EXISTĂ DEJA (inventar tehnic — REUSE BEFORE REBUILD)

### Backend — `/app/backend/routes/verified_estate.py` (818 linii, modul izolat)
| Capabilitate | Endpoint | Status |
|---|---|---|
| Listare publică cu filtre (oraș, preț, camere) | `GET /api/verified-estate/listings` | ✅ |
| Detaliu listing publicat | `GET /listings/{id}` | ✅ |
| Cerere vizionare/cumpărare (buyer inquiry) | `POST /inquiries` + email admin | ✅ |
| Audit imobil EXTERN (Traseu C — Storia/Imobiliare.ro) | `POST /external-audit-request` | ✅ |
| Prețuri publice (350/950 RON + 2.5%) | `GET /pricing` (configurabil app_settings) | ✅ |
| Checkout Stripe (audit/twin/bundle) | `POST /checkout` + `GET /checkout/status` | ⚠️ doar DEMO |
| Admin: CRUD + publish cu 4 Gates + arhivare | `POST/PATCH /admin/listings/*` | ✅ |
| Admin: inquiries, external requests, orders, stats | `GET /admin/*` | ✅ |
| Auto-creare draft listing după plată | `_create_draft_listing_from_order` | ✅ |
| Email drip (comenzi pending) + newsletter săptămânal | `email_sequences.py` | ✅ |
| Seed 2 listinguri demo | la startup | ✅ |

**Cele 4 Gates (enforced la publish)**: 1️⃣ audit_report_id · 2️⃣ digital_twin_id · 3️⃣ ≥90% recomandări acceptate · 4️⃣ aprobare admin. + Trust Score derivat (A+/A/B/C).

**Colecții DB**: `verified_estate_listings`, `verified_estate_inquiries`, `verified_estate_external_requests`, `verified_estate_orders`.

### Frontend — `/app/frontend/src/pages/verified-estate/` (5 pagini, 1.275 linii)
| Pagină | Rută | Status |
|---|---|---|
| EstateBrowse (grilă + filtre + hartă) | `/imobile-verificate` | ✅ |
| EstateDetail (galerie, gates, twin, inquiry form) | `/imobile-verificate/:id` | ✅ (⚠️ buton Twin → `/demo` placeholder) |
| SellMyProperty (landing vânzător + checkout) | `/imobile-verificate/sell` | ✅ |
| VerifiedEstateAdmin (Kanban cu Gates + Publish) | `/admin/imobile-verificate` | ✅ |
| EstateMapView | component | ✅ |

data-testid complete pe toate paginile · design coerent cu brandul (dark + lime).

---

## 3. GOLURI IDENTIFICATE (blocante comerciale)

| # | Gol | Impact comercial | Severitate |
|---|---|---|---|
| G1 | **Webhook Stripe LIVE nu procesează comenzile Verified Estate** — `/api/webhook/stripe` (payments.py:209) actualizează doar escrow `payment_transactions`. Pe Stripe REAL, comanda rămâne `pending` pentru totdeauna. Plățile funcționează DOAR în mod DEMO. | 🔴 Blocant total pentru venit real | **P0** |
| G2 | **Fluxul de VÂNZARE inexistent** — nu există status `sold/reserved`, calcul comision 2.5%, nici înregistrare tranzacție de închidere. | 🔴 Comisionul (venitul principal) nu poate fi încasat/urmărit | **P0** |
| G3 | **Audit tehnic = câmpuri manuale** — `audit_report_id/url` sunt text liber; nu există entitate raport de audit, checklist recomandări, sau atribuire auditor. Gate 3 (% recomandări) se introduce manual. | 🟠 Scalare imposibilă, risc de eroare umană | **P1** |
| G4 | **Onboarding cumpărător inexistent** — inquiry-ul rămâne lead în admin; nu există conversie → cont client → transfer proprietate. | 🟠 Pierdem clientul recurent (LTV) | **P1** |
| G5 | **Cartea Digitală a Casei inexistentă** — istoric, documente, twin nu se transferă la noul proprietar. | 🟠 Diferențiatorul-cheie al platformei lipsește | **P1** |
| G6 | **Twin pe pagina de detaliu = link `/demo`** — nu deschide twin-ul real al proprietății. | 🟡 Promisiune neonorată în UX | **P2** |
| G7 | Servicii Premium (House Health, deja funcționale) nu se atașează automat post-predare. | 🟡 Venit recurent neactivat | **P2** |

---

## 4. ESTIMARE EFORT & PLAN DE FAZE (reuse maxim, zero refactor)

| Fază | Conținut | Reuse | Efort estimat | Deblocheză |
|---|---|---|---|---|
| **A — Comercial LIVE** (P0) | G1: webhook Stripe pt. `verified_estate_orders` + G2: status `sold` + calcul comision + jurnal tranzacție | payments.py webhook existent, order model existent | **~1 sprint (15–20 credite)** | 💰 Venit real imediat (350–1.300 RON/comandă + 2.5% comision) |
| **B — Audit Workflow** (P1) | G3: entitate raport audit + checklist recomandări → alimentează automat Gate 3 | house_health evaluations pattern, property_dna | ~1–1.5 sprinturi (20–25 credite) | Scalare operațională, agenți pot lucra fără dev |
| **C — Handover** (P1) | G4+G5: inquiry→cont cumpărător + transfer proprietate + Cartea Digitală (docs+istoric+twin reasignate) | auth/register existent, digital_twin projects+members, user_timeline | ~1.5–2 sprinturi (30–35 credite) | LTV: clientul cumpărător intră în ecosistem |
| **D — Premium Attach** (P2) | G6+G7: twin real pe detaliu + ofertă House Health la handover | house_health_plans + billing complet funcționale | ~0.5 sprint (8–10 credite) | Venit recurent (abonamente) |

**Total drum complet: ~4–5 sprinturi (~75–90 credite).**
**Minim comercial viabil = doar Faza A.**

---

## 5. SCORURI EXECUTIVE

| Indicator | Scor | Notă |
|---|---|---|
| **Commercial Readiness** | **62%** | Achiziție + moderare + pricing gata; bucla de monetizare LIVE ruptă (G1/G2) |
| **UX Score** | **7/10** | Coerent cu brandul, gates vizibile în Kanban; twin placeholder pe detaliu |
| **Reuse Score** | **9/10** | Modul izolat, colecții proprii, zero refactor necesar |
| **Risc tehnic** | **SCĂZUT** | Feature flag existent (`FEATURE_VERIFIED_ESTATE`), fără dependențe fragile |

## 6. ROI ESTIMAT (per imobil verificat vândut)

- Pachet Bundle: **1.300 RON** (audit 350 + twin 950)
- Comision 2.5% la un imobil mediu de 300.000 RON: **7.500 RON**
- **Total per tranzacție: ~8.800 RON** + LTV abonament House Health post-predare (~29–99 RON/lună)
- Faza A (15–20 credite) se amortizează la **prima comandă reală**.

## 7. RECOMANDAREA CEO/CTO către BOARD

**GO pe Faza A imediat** (dependentă și de activarea Stripe LIVE — blocker existent la user).
Fazele B–D secvențial, fiecare cu GO separat după validare comercială.

---
*Document generat conform Board Directive 054. Niciun rând de cod nu a fost scris.*
