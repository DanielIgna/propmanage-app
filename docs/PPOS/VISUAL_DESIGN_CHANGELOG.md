# VISUAL DESIGN CHANGELOG — PPOS-011 v1.0 (27 Iun 2026)
Misiune: transformarea vizuală în enterprise SaaS (Stripe/Linear/Notion). ZERO schimbări de logică/API/navigație.
Validare: iteration_143 — regresie vizuală **100% PASS** (desktop 1920 + mobil 390, toate rolurile; mobilul confirmat NEATINS).

## Tipografie (desktop ≥1024px)
- Scale-up global prin CSS scoped (`index.css` §PPOS-011): client `.cv2-scope` + specialist `.pm-shell`: 9px→11, 10px→12, 11px→13, xs 12→14, sm 14→15.5 (cu line-height corectat); admin `.admin-shell`: xs→13.5, sm→15 (sidebar exceptat la 14 ca să nu taie etichetele).
- Titluri de pagină: client 38px bold (era 30 medium) · specialist 40px bold (era 48 light) · admin 36px bold (era 30) · Beta Cockpit/Issues 36px bold (era 20).
- Statistici: specialist „Astăzi ai" 36px · admin KPI 30px · pm-stat-label 12.8px.

## Spacing & Ritm
- Admin: secțiunile majore `space-y-6` → 32px pe desktop; subtitlu pagină la 16px cu mt-1.5.
- KPI cards specialist: padding 16→20px pe desktop.

## Contrast
- `--pm-outline` 0.10→0.13, `--pm-outline-strong` 0.18→0.24 (separare card/fundal mai clară).
- (din sprintul anterior) fix contrast dark pe „Pasul următor" + focus-visible WCAG.

## Tabele (admin)
- Font 15px, headere 12.5px cu tracking, row padding vertical 11.2px, hover pe rânduri.

## Carduri & Pagini
- Beta Cockpit + Beta Issues: frame standalone dark cu „← Înapoi la Admin", titluri enterprise, gate-cards cu icon aliniat sus (fix suprapunere).
- Client „Casa mea" (right rail): adresa pe rând propriu cu title-tooltip + documente pe rând separat (fix trunchiere).

## Before / After (dovezi vizuale în sesiune)
- Client Home desktop: fonts 10–12px greu lizibile → 12–15.5px, ierarhie hero → Noutăți → Descoperă clară în <3s.
- Specialist: titlu subțire 48 light → 40 bold; KPI 30→36px; „software feel".
- Admin: h1 30→36, KPI executive, tabele lizibile, sidebar intact.

## Scoruri vizuale (1–100, țintă ≥90 pe paginile importante)
| Pagina | Before | After |
|---|---|---|
| Client Home (desktop) | 78 | **92** |
| Client Property Hub | 80 | **92** |
| Client Lucrări/Setări | 75 | **88** (P2: carduri lucrări la nivel record-page) |
| Specialist Oportunități | 76 | **91** |
| Specialist Lucrările mele | 72 | **90** |
| Admin Dashboard | 74 | **90** |
| Beta Cockpit / Issues | 60 (fără frame) | **93** |
| Mobil (toate) | 88 | **88** (intenționat neatins) |
Restanțe sub 90: Client Lucrări (75→88) — următorul pass când apar date reale din beta.

## Accesibilitate
- Fonturile minime pe desktop ≥12px (nimic „tiny").
- Focus-visible + aria-labels + contrast AA pe next-step cards (sprint anterior, menținute).
