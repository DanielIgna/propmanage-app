# BENCHMARK WORLD-CLASS (recomandări, nu cod)
Status: v1.0 · Owner: Product Council · Regula: nu copiem vizual — copiem calitatea interacțiunii, utilizabilitatea, productivitatea, încrederea.

## 1. Client Home (`/client`)
- **Stripe Dashboard** face mai bine: un „azi" clar (balanță, de făcut), right rail cu context, zero feature-parade. *De ce*: userul financiar vrea decizia, nu tururi. **Adoptăm**: Next Action + panou context dreapta (PPOS-005 §4.3).
- **Notion** face mai bine: calm, o singură tipografie de ierarhie, empty states care învață. **Adoptăm**: empty state = ghid cu UN CTA.
- **Julie Zhuo (onboarding)**: primul ecran arată progresul „casa ta prinde memorie", nu funcțiile.

## 2. Specialist Dashboard (`/specialist`)
- **Linear** face mai bine: list+detail split, viteză, tastatură (j/k, Enter), zero decor. *De ce*: profesionistul procesează volum. **Adoptăm**: Mission Control split view + keyboard nav (PPOS-005 §4.1).
- **ClickUp/Monday** fac mai bine: pipeline vizual pe stări cu bulk actions. **Adoptăm**: vederi salvate + bulk pe cereri.
- **Slack** face mai bine: notificările agregate pe context, nu una câte una. **Adoptăm**: alerts grupate (max 3 + „vezi toate").

## 3. Property Hub („Casa mea")
- **Notion Database / Airtable** fac mai bine: record page cu proprietăți structurate, editare inline, vederi multiple pe aceleași date. *De ce*: casa e un „record" cu sute de atribute — nu 12 carduri de marketing. **Adoptăm**: layout record + tabel documente cu filtre/sortare/bulk + editare inline (PPOS-005 §4.2).
- **GitHub** face mai bine: istoria = timeline compact, colapsat, cu diff-uri („ce s-a schimbat"). **Adoptăm**: Istoric uman colapsat, grupat pe zi.

## 4. Marketplace public + Imobile Verificate
- **Stripe** face mai bine: încrederea prin restraint — niciodată date interne sau stări de moderare publice. **Adoptăm**: prezentare defensivă (P3a-M5).
- **Airtable/Atlassian (filtre)**: facet panel sticky stânga + sortare vizibilă. **Adoptăm**: search-first pentru cumpărător.
- **Figma (multiplayer trust)**: profilurile arată DOVEZI (lucrări, recenzii), nu autodeclarații. **Adoptăm**: badge-uri doar din date verificate (există — Capability Engine).

## 5. Pașaport public (`/p/{slug}`)
- **GitHub README/profile** face mai bine: sumar sus, detaliu colapsat, un CTA de conversie. **Adoptăm**: timeline colapsat la 5 (P3a-M7), CTA viral păstrat.

## 6. Admin
- **Stripe Admin / GitHub Admin / Atlassian**: densitate mare + search-first + command palette + tabele cu totul. **Adoptăm** (fază separată): CTRL+K (deja în backlog OS), densitate tabele.

## 7. Transversal
- **Microsoft 365 / Google Workspace**: consecvența shell-ului — aceeași navigație, aceleași pattern-uri în toate modulele. **Adoptăm**: RoleShell unic (PPOS-007) + un singur design de tabel/panou (PPOS-005).
