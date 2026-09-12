# PPOS-011 — ENTERPRISE VISUAL DESIGN SYSTEM
Status: ACTIVE v1.0 · Owner: Product Council · Primit VERBATIM de la Fondator (Iun 2026, în BETA WAR ROOM, înainte de invitarea userilor beta)
Aplicare: exclusiv vizual — FĂRĂ business logic / workflows / navigație / permisiuni / API.

## Standard tipografic DESKTOP (minime obligatorii)
| Element | Mărime | Greutate |
|---|---|---|
| Page Title | 36–42px | 700–800 |
| Section Title | 24–28px | 700 |
| Card Title | 18–20px | 600 |
| Body | 16–18px | — |
| Secondary | 15–16px | — |
| Buttons | 16–18px | — |
| Tables | ≥16px (min 15px admin dens) | — |
| Inputs | 16px | — |
| Labels | 15px | — |
| Statistics | 28–40px | — |
**Never use tiny text on desktop.**

## Spacing
Sistem 8px: 8 / 16 / 24 / 32 / 48 / 64. Niciodată spacing aleator. Whitespace generos între secțiuni majore.

## Carduri
KPI cards = executive: padding mai mare, radius mare, iconuri 44px, numere 28–40px, prioritate vizibilă instant.

## Tabele
Row height mare, hover vizibil, headere clare, ≥15–16px, plăcute la seturi mari de date.

## Butoane
Primary domină vizual (lime plin). Secondary nu concurează. Danger clar distinct.

## Culori & Contrast
Contrast crescut între background / surface / borders / primary / status (success · warning · danger · info · neutral). Toate trec accesibilitatea (AA).

## Ierarhie vizuală per ecran
Hero → Primary Action → Secondary Actions → Information → Details. Nimic nu concurează simultan.

## Benchmark
Stripe · Linear · Notion · ClickUp · GitHub · Figma · Atlassian · Vercel. Desktop = software, nu website.

## Regula scorului
Fiecare pagină primește scor vizual 1–100; polish continuu până când fiecare pagină importantă atinge ≥90/100.

## Implementare (v1.0 — 27 Iun 2026)
- Scope-uri CSS desktop (≥1024px) în `index.css` §PPOS-011: `.cv2-scope` (client V2) · `.pm-shell` (specialist) · `.admin-shell` (admin Metronic) — scale-up global al fonturilor mici (10px→12, 11px→13, xs→14, sm→15.5; admin xs→13.5, sm→15, table 15px + row height + hover).
- Contrast: `--pm-outline` 0.10→0.13, `--pm-outline-strong` 0.18→0.24.
- Titluri pagină: admin lg:text-4xl · specialist lg 40px bold · client lg 38px bold.
- KPI: specialist „Astăzi ai" lg:text-4xl + p-5 · Beta Cockpit/Issues lg:text-3xl.
- Ritm vertical admin: space-y-6 → 2rem pe desktop între secțiuni majore.
Changelog complet: `/app/docs/PPOS/VISUAL_DESIGN_CHANGELOG.md`.
