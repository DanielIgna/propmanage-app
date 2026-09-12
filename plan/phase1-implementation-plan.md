# PROPMANAGE — SEO EXPANSION FOUNDATION · Phase 1 Implementation Plan

Companion to `plan.md` (audit) and `seo-demand-validation.md` (demand). This is the plan to approve before building. Incremental, reversible, no breaking changes, no visual/UX/dashboard changes, no private-data exposure.

Phase‑1 objective: a centralized system that answers **"is this page worth indexing?"** and drives robots + canonical + sitemap + internal-linking from one source of truth, plus the first real editorial cluster (`/probleme-casa`), with an architecture that later scales to problem/component/service/city/property/specialist without rebuild.

---

## A. Scope — three explicit tiers

**BUILD NOW (Phase 1):**
1. Centralized **Indexability Gate** (config-driven; single source of truth).
2. **Sitemap** re-architected to a sitemap-index + child sitemaps; includes only gate‑passing URLs.
3. **Public SEO rendering** for the finite public SEO route set (recommendation below).
4. **Prices**: add `/preturi/{service}/{city}` (indexable only with sufficient data) + one canonical strategy for the legacy `?city=` form.
5. **Problems cluster** `/probleme-casa` + 5 quality pages.
6. **Problem → Component → Service relationship graph** + centralized **internal-linking engine** (no scattered hardcoded links).
7. **Component taxonomy** (canonical, reused — not a parallel one) + `/componente-casa` hub. Individual component pages: see "prepared".
8. **Breadcrumbs + structured data** on public SEO templates where missing.
9. **Technical-SEO safety** rules (404 for unknown slugs, noindex private, canonical for params, expired handling).
10. **Observability**: read-only admin/debug endpoint reporting per-URL SEO status.

**PREPARED (routes/model/gate ready, but indexed only when real data exists):**
- Verified estate: `/imobile-verificate/{city}`, `/{type}-{city}`, `/{id}` — templates + gate + sitemap inclusion of gate‑passing listings only; most likely NOINDEX until inventory/geo supports them.
- Individual component pages under `/componente-casa/{slug}` — taxonomy + hub now; full-content pages become indexable as content is written (otherwise NOINDEX_FOLLOW or link to hub).

**DO NOT IMPLEMENT (P2/P3):** problem×city / component×city mass generation, design×room×city, thousands of property pages, neighborhood SEO, national rollout, mass specialist re-gating, PVI/Twin Maturity content.

---

## B. Indexability Gate (single source of truth)

One centralized module with **externalized thresholds** (one config object/collection, editable without touching templates). Inputs per page: page type + entity references + counts + freshness + content completeness. Output is one of:
- `INDEX` — meta robots index,follow; canonical=self; included in sitemap; eligible as an internal-link target.
- `NOINDEX_FOLLOW` — noindex,follow; excluded from sitemap; still internally linked (crawl path preserved).
- `CANONICAL_TO_PARENT` — index via a canonical pointing to the parent (used for near-duplicates); excluded from sitemap.
- `DO_NOT_GENERATE` — return 404; never generated, never linked, never in sitemap.

The same function is consumed by: page rendering (meta), robots tag, canonical tag, sitemap generation, and the internal-linking engine — guaranteeing consistency.

**Proposed default thresholds (all in the central config, adjustable):**
- Service×city page: `INDEX` if ≥ **3** active specialists in city; else `NOINDEX_FOLLOW`.
- Price city page: `INDEX` if the city has real price data meeting a minimum (≥1 non‑preliminary category or ≥3 services with observations); else redirect/canonical to the category page (no empty city page).
- Estate location/type hub: `INDEX` if ≥ **1** eligible listing; else `NOINDEX_FOLLOW`.
- Estate listing detail: `INDEX` only if published + verified + not expired + has required public content (audit/verification summary + ≥1 public image if images are part of the public experience) + no private data; else `NOINDEX_FOLLOW` or `DO_NOT_GENERATE`.
- Specialist profile: `INDEX` only if verified + non‑deleted + profile completeness (bio + ≥1 service + ≥1 review OR ≥1 portfolio item); else `NOINDEX_FOLLOW`. (Today all verified profiles are indexed regardless — this tightens it; existing profiles that fail simply drop from the sitemap, no URL changes.)
- Editorial pages (problems/components/guides): `INDEX` if content completeness passes (min sections + min unique word count); drafts `NOINDEX_FOLLOW`.
- Data freshness: configurable max age for price rows / listing validity; stale → downgraded.

---

## C. Sitemap architecture

Move from a single file to an index + segmented children, listing **only gate‑passing (`INDEX`) URLs**:
```
/sitemap.xml                → the index (or 301/alias to /sitemap-index.xml)
/sitemaps/sitemap-pages.xml
/sitemaps/sitemap-marketplace.xml
/sitemaps/sitemap-prices.xml
/sitemaps/sitemap-guides.xml
/sitemaps/sitemap-specialists.xml
/sitemaps/sitemap-estates.xml
/sitemaps/sitemap-problems.xml
/sitemaps/sitemap-components.xml
```
- Children are generated only when they have ≥1 eligible URL (empty segments omitted from the index).
- Reuses the existing file-writer + daily-regeneration pattern; robots.txt keeps pointing at the root sitemap. **Backward compatibility:** `/sitemap.xml` remains valid (becomes the index or continues to resolve). No breaking change to what Search Console already has.
- Private/app routes, noindex, canonical‑to‑parent, expired, and gate‑failing URLs are never listed.

---

## D. Public SEO rendering (recommended: prerender, not SSR)

Findings: the app is CRA (CRACO) + React 19 SPA; meta/JSON‑LD is injected client‑side after a data fetch; K8s ingress sends only `/api/*` to the backend (so per‑route backend SSR of frontend paths isn't available), and there is no SSR/prerender tooling today. Full SSR migration is out of scope and forbidden.

**Recommendation (lowest risk, reversible, non‑invasive): build‑time/scheduled prerendering of the FINITE public SEO route set only.**
- Prerender the finite public routes (existing hubs `/design-interior`, `/imobile-verificate`, `/marketplace/*`, `/preturi/*`, `/ghiduri/*`, plus new `/probleme-casa/*`, `/componente-casa` hub, concept pages) into static HTML that ships correct `<head>` (title, meta description, canonical, robots, JSON‑LD), `<h1>` and essential above‑the‑fold content, then boots the existing SPA bundle for full interactivity (progressive enhancement — no behavioral/visual change).
- **Large dynamic sets stay as they are in Phase 1** (`/specialists/:id`, `/imobile-verificate/:id`): keep the current JS‑injected meta (Google renders JS); they graduate to prerender in P2. This keeps Phase 1 bounded.
- Fully reversible: remove the prerendered snapshots → the app falls back to today's SPA + JS meta. Nothing about the private app, dashboards, or existing URLs changes.
- Production‑serving assumption to confirm: the production static host serves nested `index.html` files at clean paths (standard). If it does not, the fallback is the current JS‑meta behavior (still functional for Google).

This is the "prefer prerendering over SSR" path the brief asks for, scoped to public SEO routes only.

---

## E. Prices — `/preturi/{service}/{city}` + `?city=` strategy

- Add the nested route; the city page renders from the existing price engine (real observations for that city) and is **indexed only if the city meets the data gate** — no empty city pages.
- Legacy `?city=` handling (single canonical strategy): audit every current internal use of `?city=` first, update those links to the clean path, then **301** `/preturi/{slug}?city=x` → `/preturi/{slug}/{city}` when the city qualifies, else 301 → `/preturi/{slug}`. No redirect chains; the clean path is the sole canonical. Existing `/preturi` and `/preturi/{slug}` are unchanged.

---

## F. Problems cluster (first real editorial cluster)

- `/probleme-casa` hub + 5 pages: `/probleme-casa/infiltratii`, `/mucegai`, `/igrasie`, `/fisuri`, `/umezeala`.
- **Cannibalization decision:** keep `infiltratii`, `mucegai`, `igrasie`, `fisuri` as distinct pages (distinct RO search intents, distinct causes/solutions), with `umezeala` as the umbrella that links down to `mucegai`/`igrasie`/`infiltratii`. Content is strongly differentiated per page; if two pages would end up near‑duplicate, the weaker one is consolidated and set `CANONICAL_TO_PARENT` (umezeala). (Adjustable — see decisions.)
- Each page follows the quality structure from the brief (H1, intro, ce înseamnă, cum recunoști, cauze, ce verifici, ce faci imediat, când chemi specialist, ce tip de specialist, costuri orientative *only if real data*, cum documentezi în PropManage, probleme/componente/servicii/ghiduri asociate, FAQ). Original, useful, PropManage‑specific; no keyword stuffing; costs shown only when backed by real price data.
- Content is server‑driven and versioned (reuses the existing `content_version` mechanism) so SEO copy can change without touching design.

---

## G. Problem → Component → Service graph + internal-linking engine

- A centralized relationship model (config/data, not scattered JSX): each entity (problem/component/service/guide/price/city) declares `related_components[]`, `related_services[]`, `related_problems[]`, `related_guides[]`, `related_prices[]`.
- One internal-linking helper reads these relations and renders link blocks on any template; adding a relation later requires no page refactor. Goal: **no orphan SEO pages** — every gate‑passing page links up to its hub and sideways to related nodes; the linking helper skips non‑`INDEX` targets (or links to the nearest indexable ancestor).
- Phase 1 wires: Problem → Component → Service → (city/specialist/price/guide) where those targets already exist and pass the gate. Local (×city) expansion is deferred but the relations already carry the city dimension.

---

## H. Component taxonomy (ONE canonical taxonomy — reuse, don't fork)

- The House Health A→G axis is a **narrative** framework (identity/documentation/energy/health/systems/works/twin), not a physical‑component list. So the canonical SEO **component** taxonomy (acoperiș, fundație, fațadă, instalație electrică, instalație sanitară, încălzire/centrală, ferestre/uși, termoizolație) is defined **once** and each component maps to: an existing **service category** (reusing `seo_slugs`/`price_seo`: electric, plumbing, hvac, acoperisuri, fatade_termoizolatii, tamplarie, constructii…), the relevant **House Health chapter** (narrative bridge), and related problems.
- This is a single SSOT that *references* existing taxonomies rather than inventing a parallel one. `/componente-casa` hub is built now; individual component pages are indexed only when they carry real, unique content (otherwise NOINDEX_FOLLOW / link to hub).

---

## I. Breadcrumbs & structured data

- Add `BreadcrumbList` (generated from the URL/relationship structure) to public SEO templates where missing (e.g., PropManage → Probleme casă → Infiltrații).
- Schema per template, only where the page truly represents it: BreadcrumbList (all), Article + FAQPage (problems/guides), Service (service/marketplace), CollectionPage (hubs), LocalBusiness/Person (specialists), Residence/real‑estate type (listings). Existing JSON‑LD (prices FAQPage, guides Article, design interior) is preserved. **No fabricated reviews/ratings/prices** — structured data only reflects real page content.

---

## J. Technical‑SEO safety (must‑pass)

- Unknown slug → **404** (not 200 + empty template) for `/probleme-casa/*`, `/preturi/*`, `/imobile-verificate/*`, `/marketplace/*`, `/componente-casa/*`.
- Expired/removed listing → not indexable (noindex or 410); dropped from sitemap.
- Duplicate/param URLs (filters, sorting, pagination, query params) → one canonical target (clean path); faceted params noindex or canonical‑to‑base per explicit rules.
- Private/app routes (`/client`, `/specialist`, `/administrator`, `/operator`, `/admin/*`, `/partner/*`, `/projects/:id`, `/contracts/:id`, `/payment-success`, `/house-health/:twinId`, `/p/:slug`, tokened routes) → remain NOINDEX and absent from sitemap.

---

## K. Content versioning & observability

- Keep the existing `content_version` mechanism for server‑driven SEO content; a version bump invalidates/upgrades content without any design change. Not removed.
- Observability (no new visual dashboard): a **read‑only admin/debug endpoint** that, per SEO URL, reports: URL, INDEX/NOINDEX decision, canonical, sitemap‑included (y/n), entity count, content_version, schema type(s), last updated. Used to verify the gate and catch regressions.

---

## L. Acceptance tests (run before finishing)

- **Existing (no regression):** `/design-interior`, `/imobile-verificate`, `/marketplace/*`, `/preturi/*`, `/ghiduri/*`, `/specialists/*` — unchanged design, URLs, title/description/H1/canonical/robots/JSON‑LD still present and correct; still in sitemap where applicable.
- **New:** `/probleme-casa`, `/probleme-casa/infiltratii|mucegai|igrasie|fisuri|umezeala` — HTTP 200, correct title/description/H1/canonical/robots, valid JSON‑LD (BreadcrumbList + Article/FAQPage), internal links present, in the problems sitemap, no design regression.
- **Negative:** `/probleme-casa/nonexistent`, `/imobile-verificate/nonexistent`, `/preturi/nonexistent` → **404** (not empty 200); not in sitemap.
- **Gate:** a service×city with <3 specialists and a price city with no data render NOINDEX/redirect and are absent from the sitemap; a private route is NOINDEX and absent.
- **Prices:** `/preturi/{slug}/{city}` indexable only with data; `?city=` 301s to the clean path (no chains).

---

## M. Decisions made (confirm or adjust)

1. **Rendering:** build‑time/scheduled **prerendering of finite public SEO routes only**; large dynamic sets (`/specialists/:id`, `/imobile-verificate/:id`) keep current JS meta in Phase 1. (Recommended lowest‑risk, reversible.) — confirm, or require prerender for dynamic sets now too.
2. **Problems pages:** 5 distinct pages with `umezeala` as umbrella; consolidate igrasie↔mucegai only if content would be near‑duplicate. — confirm, or force a merge.
3. **`?city=`:** 301 legacy query form → clean path (or → category page if city lacks data). — confirm.
4. **Gate default thresholds** (≥3 specialists; ≥1 listing; specialist completeness = bio+service+review/portfolio; editorial min sections/words; price/listing freshness) — confirm or set exact numbers.
5. **Components in Phase 1 = taxonomy + hub only** (individual component pages indexed later when they have real content). — confirm, or require the 5 component pages now.
6. **Geo gating** uses the approved order (Cluj‑Napoca, București, Timișoara, Iași, Brașov, Constanța, then national); pages for cities without real data are not generated. — confirm.

Nothing is built until this is approved.
