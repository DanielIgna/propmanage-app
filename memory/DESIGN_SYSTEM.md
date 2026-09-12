# PropManage — Business Design System (Constituția UI)
*Creat: iunie 2026 · Obligatoriu pentru TOATE modulele Business actuale și viitoare.*
*Componente: `/app/frontend/src/design-system/` — orice pagină nouă le refolosește, fără excepții.*

## 1. Ordinea standard a paginii (identică peste tot)
```
Titlu pagină + Subtitlu (via AdminLayoutMetronic title/subtitle)
──────────────
TabBar (navigare secundară)  +  ActionBar (perioadă · CSV · PDF · refresh)
──────────────
KPI Cards (KpiCard)
──────────────
AI Summary (AIInsightCard) — OBLIGATORIU după KPI
──────────────
Grafice (ChartCard)
──────────────
Tabele (DataTable)
──────────────
Acțiuni · Export
```

## 2. Componente obligatorii (import din `design-system`)
| Componentă | Rol | Reguli |
|---|---|---|
| `KpiCard` | icon → titlu → valoare mare → evoluție ±% "vs perioada trecută" | niciodată doar o cifră; `invertTrend` pentru metrici unde scăderea = bine (bounce) |
| `AIInsightCard` | 🧠 AI Insights: bullets + alerts + "Vezi recomandări →" | apare pe ORICE modul: Analytics, Marketplace, Financiar, Escrow, Utilizatori, Cereri |
| `ChartCard` | container standard grafice | recharts + `CHART` tokens (strokeWidth 2, grid "3 3" op. 0.2, tick 10px), culori din `CHART_COLORS` |
| `DataTable` | header sticky, sortare, căutare, export CSV, hover | nicio pagină nu-și mai scrie propriul `<table>` |
| `DSButton` | primary / secondary / ghost / danger / success | DOAR aceste 5 variante |
| `DSBadge` | NEW / AI / BETA / LIVE / ACTIVE / WARNING / ERROR | nu se inventează badge-uri noi |
| `EmptyState` | icon + titlu + hint + CTA | nicio pagină goală |
| `DSSkeleton` | skeleton loading unic | fără spinnere diferite |
| `ActionBar` | perioadă (Azi/7z/30z) · refresh · CSV · PDF | mereu dreapta-sus, același loc |
| `TabBar` | navigare secundară | stil unic activ/inactiv |

## 3. Tokens (din `design-system/tokens.js`)
- **Culori semantice:** verde=succes · albastru=info · portocaliu=atenție · roșu=critic · **mov=AI** · gri=neutru (`SEMANTIC`)
- **Spațiere fixă:** 24px între secțiuni (`space-y-6`) · 16px între carduri (`gap-4`) · 12px în card (`space-y-3`) · 8px label→valoare (`mt-2`)
- **Grid unic:** 12 col desktop/laptop · 6 tabletă · 1 mobil (`GRID12`)
- **Card de bază:** `CARD` = `rounded-2xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800`

## 4. Teme per zonă (decizie strategică)
- **Business/Admin/Operator:** temă slate Metronic (light + dark mode) — acest Design System
- **Client (consumer):** temă deschisă V2 (alb + verde #34C759, stil HomeRun) — validată în UX_REDESIGN_CLIENT_V2_FAZA1.md
- **Specialist:** migrează progresiv la Design System-ul Business (backlog)

## 5. AI peste tot (regulă produs)
Fiecare modul Business trebuie să aibă: **AI Summary** (AIInsightCard) + **AI Recommendations** + **AI Alerts** + **AI Actions**.
Backend pattern: endpoint `/admin/<modul>/insights` → `{bullets, alerts, recommendations}` (v1 rule-based; v2 LLM prin Emergent Key — backlog).

## 6. Implementare de referință
`/app/frontend/src/pages/admin/AnalyticsGrowthPage.jsx` — respectă integral ordinea + componentele. Orice modul nou copiază acest pattern.

## 7. Backlog standardizare (audit ✅/🟡/🔴)
| Modul | Status | Prioritate |
|---|---|---|
| Analytics & Growth | ✅ referință | — |
| Admin Overview / Console | ✅ (iter93) | — |
| Marketplace Partners | ✅ (iter93) | — |
| Financiar / Escrow | ✅ (iter93) | — |
| Utilizatori / Cereri (AdminUsers, AdminApprovals) | ✅ AdminUsers (iter99) · 🟡 AdminApprovals | P2 |
| Specialist Dashboard | ✅ sumar „Astăzi ai" pe DS (iter93) | — |
| Operator Dashboard | ✅ migrat pe DS + AI Insights (iter100) | — |
| BI MoE / Construction Intelligence | ✅ BI MoE (iter99) · 🟡 Construction | P2 |
| Module AI (Control Center, Governance etc.) | 🟡 AI Insights v2 adăugat (iter100) · restyle DS complet P3 | P3 |

*Regulă: nu se dezvoltă pagini individuale. Se refolosesc componentele. Orice PR care introduce un buton/tabel/badge custom în zona Business = respins.*
