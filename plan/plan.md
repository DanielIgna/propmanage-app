# PROPMANAGE SEO EXPANSION MAP — Audit & Content Architecture

Status: AUDIT + ARCHITECTURE + PRIORITIZATION only. Nothing here is implemented. This document is for approval and to select the first implementation batch. No design, layout, UX, routes, or functionality change as part of this stage.

Guiding principle: not "more keywords" — **more real search intents satisfied by PropManage**, by turning the product's real entities into an indexable knowledge graph:
Property → House/Apartment → Component → Problem → Maintenance → Service → Specialist → Location → Verification → Digital Twin → House Health → History.

---

## 1. Current SEO Inventory

Public, crawlable routes today (grouped by SEO value). "Dynamic" = one URL template generating many pages from real data.

### A. High-value marketing / concept pages (static, server-driven meta)
| URL | Purpose | Intent | Meta source | Schema | Notes |
|---|---|---|---|---|---|
| `/` | Landing (Cartea Casei) | Brand / discovery | Pages Registry `home` + code fallback | — | Client-rendered |
| `/design-interior` | Interior design service hub | Commercial / service | `/interior-design/content` (server) + Pages Registry `interior_design` | JSON-LD, canonical | Already optimized |
| `/imobile-verificate` | Verified listings hub | Discovery / commercial | Pages Registry `estate` | (verify) | Already optimized; static JSX body |
| `/design-exterior`, `/arhitectura` | Service hubs (ServiceHubLanding) | Service | server slug-driven | (verify) | Template already exists |
| `/scorul-casei` | House Health score explainer | Informational / brand | code | (verify) | Concept page |
| `/digital-twin` | Digital Twin explainer | Informational / brand | code | (verify) | Concept page |
| `/checklist-cumparare` | Buying checklist | Informational | code | (verify) | Lead magnet |
| `/de-ce-noi` | Why us | Brand | code | — | |
| `/devino-specialist`, `/devino-francizat` | Recruitment/lead | Transactional (B2B) | code | — | Lead forms |
| `/ghiduri` | Guides index | Informational hub | code | — | Hub |

### B. Existing programmatic / dynamic templates (the engine already partly exists)
| URL template | Generator | Count today | Intent | Schema | In sitemap |
|---|---|---|---|---|---|
| `/marketplace/:slug` | `seo_slugs` (9 services × 22 cities + 9 parents) | ~207 | Service / Service×Location | (verify per page) | Yes |
| `/preturi` + `/preturi/:slug` | `price_seo` (14 categories) | 15 | Commercial ("cât costă X") | FAQPage | Yes |
| `/ghiduri/:slug` | guides data (mirrored in sitemap) | 10 | Informational / Problem-solution | Article + FAQPage | Yes |
| `/specialists/:id` | verified specialists in DB | = #verified | Service / entity | (verify) | Yes (all verified) |
| `/imobile-verificate/:id` | verified estate listings | = #listings | Property entity | (verify) | **No (gap)** |
| `/p/:slug` | public house passport (share) | share-only | — | — | Should stay noindex |

### C. Legal / utility (index low or noindex)
`/privacy`, `/privacy/notices`, `/terms`, `/cookies`, `/trust`, `/status`, `/login`, `/register`, `/verify-email`, `/kyc`, `/auth/callback`.

### D. Private / app routes (must NOT be indexed)
`/client`, `/specialist`, `/administrator`, `/operator`, `/admin/*` (100+ internal dashboards), `/partner/*`, `/projects/:id`, `/contracts/:id`, `/payment-success`, `/house-health/:twinId` (individual private twins), `/dashboard/client-junior`, `/incepe`, `/legal/sign`, `/report-respond/:token`, `/help/:token`.

**Key technical fact:** the app is a client-rendered SPA (CRA). Titles/meta/JSON-LD are injected by JavaScript after a data fetch. This works for Google (it renders JS) but is fragile at programmatic scale and weaker for other crawlers/social scrapers. Server-rendered/prerendered HTML for public SEO routes is the single biggest enabler and is treated as a cross-cutting decision below.

---

## 2. Existing Keyword Coverage (what is already owned)

- **Interior design**: design interior, arhitectură de interior, design interior și implementare, amenajări interioare la cheie, randări 3D fotorealiste (done).
- **Verified real estate**: imobile verificate, case de vânzare verificate, apartamente verificate, anunțuri imobiliare cu audit tehnic, proprietăți verificate digital twin (done).
- **Prices (long-tail commercial)**: "cât costă {lucrare} în {oraș} în {an}" across 14 categories (zugrăvit, parchet, gresie/faianță, handyman, gips-carton, HVAC, electrice, sanitare, design interior, construcții/zidărie, acoperișuri, termoizolații/fațade, tâmplărie PVC, amenajări exterioare).
- **Service × location**: electrician / instalator / HVAC / designer interior / tâmplar / zugrav / firmă curățenie / service electrocasnice / grădinar, each × 22 cities.
- **Guides**: renovation cost, choosing a designer/installer/painter, escrow, electrical cost, technical audit, pre-purchase verification, digital twin, verified listings.

Gaps: **problems** (infiltrații, mucegai, fisuri…), **components** (acoperiș, fundație, instalații…), **maintenance** (calendar, inspecții, durată de viață), **property-type × location** and **problem × location**, House Health/PVI/Twin Maturity educational cluster, verified-estate location/category hubs.

---

## 3. Keyword / Search-Intent Matrix (by cluster)

| Cluster | Intent | Keyword family | Example | Existing page | Missing page | Potential | Risk |
|---|---|---|---|---|---|---|---|
| Prices | Commercial | cât costă {lucrare} {oraș} | "cât costă zugrăvit București 2026" | `/preturi/:slug` | `/preturi/:slug/:city` (distinct URLs) | High | Thin per-city if little data |
| Service×Loc | Transactional/Local | {serviciu} {oraș} | "electrician Cluj" | `/marketplace/:slug` | more services / zones | High | Thin if 0 specialists |
| Problems | Problem/solution | "ce faci când ai {problemă}" | "infiltrații acoperiș ce faci" | none | `/probleme-casa/:slug` | High | Needs real content |
| Problem×Loc | Local | {problemă} {oraș} | "reparație infiltrații Cluj" | none | `/probleme-casa/:slug/:city` | Medium | Thin/doorway risk |
| Components | Informational/Commercial | întreținere/verificare {componentă} | "verificare instalație electrică" | none | `/componente-casa/:slug` | Medium-High | Content depth |
| Maintenance | Informational | calendar/durată de viață {sistem} | "cât rezistă un acoperiș" | partial (guides) | maintenance hub + entity pages | Medium | Overlap with guides |
| House Health/PVI/Twin | Informational/Brand | scorul casei, digital twin, PVI | "ce este digital twin locuință" | `/scorul-casei`,`/digital-twin`, 1 guide | educational cluster | Medium (brand) | Low search volume, high authority |
| Verified estate | Discovery/Commercial | imobile/case/apartamente verificate {oraș} | "apartamente verificate Cluj" | `/imobile-verificate` (hub only) | location/type hubs + listing detail | High | Must gate thin listings |
| Design interior sub | Commercial/Local | amenajare {tip} {oraș}, randări 3D | "amenajare apartament Cluj" | `/design-interior` (parent) | room/property-type/location subpages | High | Duplication with parent |
| Specialists | Entity/Service | {nume/serviciu} {oraș} | specialist profile | `/specialists/:id` | gated profiles + service hubs | Medium | Thin profiles = mass thin content |
| Guides/Educational | Informational | how-to, cost, comparison | "cum verifici o casă" | `/ghiduri/:slug` (10) | expand editorial | High | Editorial effort |

---

## 4. Content Gaps (per cluster: exists / missing / build type)

- **Prices**: exists = 14 category pages (city is a query param, non-indexable). Missing = distinct per-city URLs. Build = programmatic, gated by data volume. Should be hub (`/preturi`) → category → category+city.
- **Service×Location**: exists = 9×22 landings. Missing = align with the 14 price categories (5 categories have price pages but no marketplace landing). Build = extend the existing slug map; gate by specialist count.
- **Problems**: exists = nothing (some guides touch it). Missing = a problem cluster. Build = editorial hub + programmatic problem×location later. Should be hub (`/probleme-casa`) → problem → problem+location.
- **Components**: exists = House Health axis chapters conceptually. Missing = component pages. Build = editorial/semi-programmatic from the axis taxonomy.
- **Maintenance**: exists = scattered in guides. Missing = a maintenance hub + lifespan/cost entity pages. Build = editorial + data where available.
- **House Health/PVI/Twin**: exists = 2 concept pages + 1 guide. Missing = a small educational cluster (PVI, Twin Maturity explained). Build = editorial. These are brand/category pages, not mass programmatic.
- **Verified estate**: exists = hub only. Missing = location hubs, property-type hubs, and indexable listing detail pages (with a strict gate). Build = programmatic hubs + gated detail pages.
- **Design interior sub-clusters**: missing = room type (dormitor, bucătărie, living, baie), property type (apartament, casă, garsonieră), and location variants. Build = programmatic subpages under `/design-interior` with unique data/renders, gated to avoid duplicating the parent.
- **Specialists**: exists = all verified profiles indexed. Missing = a quality gate (many may be thin). Build = tighten indexability; add service-hub cross-links.

Pages that should NOT be created: any auto-generated page with no real specialists/listings/data behind it; near-duplicates of the parent; per-neighborhood pages without inventory.

---

## 5. SEO Topic Clusters (authority domains)

1. **Property & ownership** — Cartea Casei, documentare, istoric proprietate.
2. **House problems** — infiltrații, umezeală, mucegai, igrasie, fisuri, fundație, acoperiș, fațadă, electric, sanitar, încălzire/centrală, ferestre, izolație.
3. **House components/systems** — acoperiș, fundație, fațadă, instalații electrice/sanitare, încălzire/centrală, ferestre/uși, termoizolație.
4. **Maintenance** — verificări, inspecții, reparații, calendar, prevenție, durată de viață, estimări de cost.
5. **House Health / PVI / Twin Maturity / Digital Twin** — starea și evoluția proprietății, istoric tehnic (brand + educational).
6. **Verified real estate** — imobile/case/apartamente verificate, audit tehnic, Digital Twin, anunțuri verificate.
7. **Interior design** — design, arhitectură de interior, amenajări la cheie, randări 3D, tipuri de camere/proprietăți.
8. **Services** — electrician, instalator, HVAC, arhitect, designer, acoperișuri, construcții, inspecție etc. (only product-supported).
9. **Specialists** — profiluri, servicii, localizare, reputație, lucrări.
10. **Local** — service/property/problem/specialist × location.

Each cluster maps to real product entities (service categories, cities, specialists, properties, listings, house-health axis), so pages can carry real data — not filler.

---

## 6. Programmatic SEO Opportunities (dimensions & valid combinations)

Dimensions already in data: **service category** (9 marketplace + 14 price), **city** (22), **specialist** (verified), **verified listing** (with type/city), **price data** (category×city×level).
Dimensions to model: **problem**, **component**, **room type**, **property type**.

Valid, product-backed combinations (proposed, gated):
- Service × Location — already live; extend categories/zones.
- Price × Category × City — promote city to a distinct URL where data supports it.
- Property type × Location (verified estate) — apartamente/case verificate {oraș}.
- Design × Room/Property type × Location — amenajare {tip} {oraș}.
- Problem → Component → Service → (Location) — the semantic spine; start editorial, add location later.

Combinations to forbid: problem × neighborhood with no inventory; specialist × unrelated service; any grid cell with zero backing entities; price×city with a single stale observation.

---

## 7. Indexability Gate (proposed rules)

A generated page is `index,follow` only if ALL hold:
- Has ≥1 real backing entity for its exact intent (e.g. ≥3 active specialists for service×city; ≥1 listing for estate location hub; price data from ≥1 non-preliminary category or clearly-labelled preliminary with ≥3 services).
- Has unique, non-templated content beyond swapped tokens (real numbers, local context, entity links).
- Is not a near-duplicate of a parent (if it would duplicate, canonical to the parent instead).
- Meets a minimum content threshold (proposed: ≥1 H1, ≥2 content sections, ≥1 data table or ≥300 words of unique copy, ≥3 internal links).

Otherwise:
- Useful-but-empty (e.g. valid city, few specialists) → `noindex,follow` + keep internally linked, flip to index when it crosses the threshold.
- Near-duplicate → `canonical` to the parent.
- No value / no backing data → not generated at all (404), not a noindex doorway.

Specialist profiles: index only verified + non-deleted + minimum profile completeness (bio + ≥1 service + ≥1 review or portfolio item); otherwise noindex. (Today all verified profiles are indexed regardless of depth — tighten this.)

The gate is computed server-side and expressed via the meta robots tag + sitemap inclusion (only indexable pages go in the sitemap).

---

## 8. Internal Linking Architecture (semantic graph)

Automatic link rules (each edge is bidirectional where it makes sense):
- Problem page → related Component(s) → relevant Service(s) → Service×Location → top Specialists in that city.
- Service page → City variants (service×location) → related Price page → related Guides → relevant Problems it solves.
- Price page → matching Service×Location, related Guides, related Price categories (already has "related").
- Component page → its Problems, its Maintenance items, related Services, House Health axis chapter.
- Verified estate hub → location/type sub-hubs → listing detail → Digital Twin / House Health explainer → "audit tehnic" guide.
- House Health / Digital Twin / PVI → guides + concept pages + verified estate + Cartea Casei.
- Every cluster hub links down to its children; every child links up to its hub and sideways to 3–6 siblings.

Goal: no orphan pages; every indexable node reachable within ~3 clicks from a hub that is itself in the main nav/footer or sitemap.

---

## 9. SEO Page Templates (patterns to standardize)

For each: URL / Title / H1 / meta / intro / H2s / schema / canonical / internal links / index condition.

1. **Hub page** — `/{cluster}` · Title "{Cluster} — {value} | PropManage" · H1 cluster name · intro defines the cluster · H2 = child categories + featured children · schema `CollectionPage`/`BreadcrumbList` · canonical self · links to all children · always index.
2. **Category page** — `/{cluster}/{category}` · Title "{Category} — {benefit} | PropManage" · H1 category · H2 = subtypes, how-it-works, related · schema `BreadcrumbList` (+`Service` where applicable) · index if ≥1 child/entity.
3. **Service page** — `/marketplace/{service}` (exists) · `Service` + `BreadcrumbList` · index.
4. **Service × Location** — `/marketplace/{service}-{city}` (exists) · Title "{Service} {City} — specialiști verificați" · include live count + local context · `Service`+`BreadcrumbList` · index if ≥3 specialists else noindex.
5. **Price page** — `/preturi/{slug}` (exists) and proposed `/preturi/{slug}/{city}` · `FAQPage`+`BreadcrumbList` · index if data present.
6. **Problem page** — `/probleme-casa/{slug}` · Title "{Problemă}: cauze, soluții și cost | PropManage" · H2 = simptome, cauze, soluții, cost orientativ, când chemi specialist · `FAQPage`+`Article`+`BreadcrumbList` · index (editorial).
7. **Component page** — `/componente-casa/{slug}` · H2 = rol, probleme frecvente, întreținere, durată de viață, verificare · `Article`+`BreadcrumbList` · index (editorial/semi-programmatic).
8. **Location page (estate)** — `/imobile-verificate/{city}` (or query→path) · H1 "Imobile verificate {oraș}" · list + local context · `CollectionPage`+`BreadcrumbList` · index if ≥1 listing.
9. **Property-type × Location** — `/imobile-verificate/{type}-{city}` · index if inventory.
10. **Individual entity page** — `/specialists/{id}` (exists), `/imobile-verificate/{id}` (add to sitemap, gated) · `LocalBusiness`/`Person` or `Product`/`Residence` + `BreadcrumbList` + reviews where present · index only if gate passes.
11. **Guide / educational** — `/ghiduri/{slug}` (exists) · `Article`+`FAQPage`+`BreadcrumbList` · index.

All templates read meta from Pages Registry where a page key exists, else from a server-computed default for the entity — so the meta pipeline stays centralized and the "already optimized" behavior is preserved.

---

## 10. URL Architecture (reuse first, no breaking changes)

Keep every existing route as-is. New patterns proposed (additive):
```
/design-interior                      (keep)
/imobile-verificate                   (keep, becomes hub)
/imobile-verificate/{city}            (new — location hub)
/imobile-verificate/{type}-{city}     (new — type×location)
/imobile-verificate/{id}              (keep; add to sitemap + gate)
/marketplace/{service}[-{city}]       (keep)
/preturi, /preturi/{slug}             (keep)
/preturi/{slug}/{city}                (new — promote city param to path; 301 the ?city= form to it OR canonical)
/probleme-casa, /probleme-casa/{slug} (new)
/probleme-casa/{slug}/{city}          (new, later, gated)
/componente-casa, /componente-casa/{slug}  (new)
/mentenanta, /mentenanta/{slug}       (new)
/ghiduri, /ghiduri/{slug}             (keep, expand)
/specialists/{id}                     (keep, gate)
```
Rules: no diacritics, lowercase, hyphenated; longest-match parsing (already implemented for marketplace/city); city aliases allowed with one canonical form (e.g. `cluj` → canonical `cluj-napoca`); avoid redirect chains; existing `?city=` price form should either 301 to the path form or set canonical to it (decision below).

---

## 11. Technical SEO Findings

- **Rendering (biggest item):** client-rendered SPA; meta/JSON-LD injected via JS after fetch. Recommend server-rendering or prerendering the public SEO routes so HTML ships with correct title/meta/canonical/JSON-LD and body copy. This is the enabler for scaling programmatic pages reliably (and for social/OG scrapers). Decision required (see below).
- **Sitemap:** dynamic, served at `/sitemap.xml` (root static mirror) and `/api/public/sitemap.xml`; regenerated on startup + daily. Single file (~48KB / ~263 URLs). At scale, move to a **sitemap index** + segmented child sitemaps (by cluster), each < 50k URLs / < 50MB. Only indexable (gate-passing) URLs should be listed.
- **robots.txt:** present; declares `Sitemap: /sitemap.xml`; has AI-bot directives. Keep; ensure private/app routes are disallowed and never in sitemap.
- **Canonical:** present on optimized pages; must be emitted server-side for all templates, especially faceted/query-param variants.
- **Faceted navigation / query params:** marketplace filters, estate filters, price `?city=` create parameter URLs → duplicate risk. Define canonical/noindex rules; prefer path-based canonical targets.
- **Meta source:** Pages Registry (`db.pages.live.*`) with code fallback via the SEO hook — centralized and reusable for new templates.
- **Schema:** FAQPage (prices/guides), Article (guides) exist. Add BreadcrumbList across templates; add Service, CollectionPage, LocalBusiness/Person (specialists), and RealEstate/Residence (listings) where applicable.
- **Estate detail pages** are not in the sitemap (gap) and need a gate before indexing.
- **404 vs soft-404:** ensure non-existent slugs return real 404 (not a 200 empty template) to avoid soft-404s.
- **hreflang:** single language (RO) — not needed now.
- **Data-source sync risk:** guide slugs are duplicated between the sitemap generator and the frontend data file — consolidate to one source to prevent drift as guides grow.

---

## 12. Local SEO Architecture

- **Service × Location** — live (`/marketplace/{service}-{city}`), 9 services × 22 cities. Extend to the 14 price categories; gate by specialist count per city.
- **Price × City** — promote to distinct URLs where data supports.
- **Property-type × Location** — verified estate location/type hubs.
- **Problem × Location** — later, only where there are specialists to solve it in that city.
- City taxonomy is centralized (22 cities, alias support). Recommend a **city-first rollout** (Cluj-Napoca — company HQ — then top 6: București, Timișoara, Iași, Brașov, Constanța, Cluj) to avoid launching thousands of thin city pages at once.
- Each location page must include real local signals (specialist count, real price ranges, listings) to avoid doorway classification.

---

## 13. Imobile Verificate SEO Architecture

- `/imobile-verificate` = hub (keep). Add:
  - Location hubs `/imobile-verificate/{city}` — index if ≥1 listing.
  - Property-type×location `/imobile-verificate/{type}-{city}` — index if inventory.
  - Listing detail `/imobile-verificate/{id}` — add to sitemap, **gated**: index only listings that are actually verified/published with sufficient content (audit summary, Digital Twin, photos); noindex drafts/thin/expired.
- Schema: CollectionPage on hubs, Residence/Product + BreadcrumbList + offer/price where public on detail.
- Do NOT index every listing indiscriminately; expired/removed listings → noindex or 410.

---

## 14. Design Interior SEO Expansion

Parent `/design-interior` stays. Add gated subpages only where content is genuinely unique:
- Room types: dormitor, living, bucătărie, baie, birou.
- Property types: apartament, casă, garsonieră, penthouse.
- Location variants: design interior {oraș}.
- Format options: amenajare la cheie, randări 3D fotorealiste (as sections/subpages).
Each subpage needs unique copy + relevant renders/examples; otherwise canonical to the parent. Cross-link to `/preturi/design-interior`, relevant guides, and specialists (designeri interior × city).

---

## 15. House Health / Digital Twin SEO Opportunities

- Brand/category pages (keep/expand): `/scorul-casei`, `/digital-twin`.
- Educational cluster (new, editorial, low volume but high authority + internal-link hub): what is House Health, what is PVI (Property Value Index), what is Twin Maturity, technical history/documentation of a property.
- These pages anchor the semantic graph (linked from problems, components, verified estate, Cartea Casei) more than they chase volume.
- Individual `/house-health/:twinId` stays private/noindex.

---

## 16. Service / Specialist SEO Opportunities

- Service hubs: `/marketplace/{service}` (+ `/design-exterior`, `/arhitectura`, `/design-interior`). Add missing categories that have price data but no marketplace landing (acoperișuri, construcții/zidărie, termoizolații/fațade, gips-carton, amenajări exterioare) — if product-supported.
- Specialist profiles: index only gate-passing profiles; enrich with services, city, reviews, portfolio; cross-link from the relevant service×location page.
- Clear separation: public indexable = verified + complete profiles and service hubs; private/noindex = dashboards, applications, incomplete profiles.

---

## 17. Pages That Should NOT Be Indexed

- All `/admin/*`, `/client`, `/specialist`, `/administrator`, `/operator`, `/partner/*`.
- `/projects/:id`, `/contracts/:id`, `/payment-success`, `/legal/sign`, `/kyc`, `/auth/callback`, `/verify-email`.
- `/house-health/:twinId` (individual private twins), `/p/:slug` (private share passports), `/help/:token`, `/report-respond/:token`.
- Any generated page failing the Indexability Gate (thin, duplicate, no backing entity).
- Query-parameter/faceted variants (canonical to the clean path).

---

## 18. Priority Roadmap (P0 → P3)

**P0 — Quick wins (high impact, low risk, no new pages of substance):**
- Confirm/emit robots meta + canonical server-side on all existing public templates; ensure all private/app routes are disallowed and absent from sitemap.
- Add BreadcrumbList schema to existing templates (prices, guides, service, design interior, estate).
- Move sitemap to a sitemap-index structure and list only gate-passing URLs; add verified estate detail pages (gated) that are currently missing.
- Consolidate the guide-slug source of truth (remove sitemap/frontend drift).
- Rationale: strengthens indexing of what already exists; near-zero UX risk.

**P1 — High value (build first real new clusters):**
- Problem cluster hub + a first set of editorial problem pages (infiltrații, mucegai/igrasie, fisuri, acoperiș, umezeală) with FAQ/Article schema and links into services/specialists.
- Component cluster hub + first component pages (acoperiș, instalație electrică, instalație sanitară, fațadă/termoizolație, ferestre) from the House Health axis.
- Extend service×location to the price categories that lack marketplace landings (gated).
- Promote price `?city=` to indexable `/preturi/{slug}/{city}` for cities with real data.
- Rationale: opens net-new, high-intent surface backed by real data/editorial.

**P2 — Programmatic expansion (multiplies surface, needs the gate + rendering):**
- Verified estate location + property-type×location hubs; gated listing detail indexing.
- Design interior room/property-type/location subpages (gated, unique content).
- Problem×location and component×location where specialists exist.
- City-first rollout (Cluj → top 6 → national) to control thin-content risk.
- Rationale: scale only after the gate and (ideally) server rendering are in place.

**P3 — Advanced:**
- House Health/PVI/Twin educational cluster as an authority hub.
- Automated internal-linking engine across the full graph.
- Freshness signals (real requests/prices/specialist counts) surfaced on pages and in lastmod.
- Rationale: authority + defensibility; lower direct volume.

---

## 19. Recommended First Implementation Batch (for approval)

Proposed scope for the first build (deliberately small, high-confidence, no design changes):

1. **P0 technical foundation:** server-side canonical + robots-meta on all public templates; sitemap-index + gate-filtered URLs; add gated verified-estate detail pages to sitemap; consolidate guide-slug source; BreadcrumbList schema on existing templates.
2. **Indexability Gate (shared service):** one server-side function that decides index/noindex/canonical per page from real entity counts, used by templates + sitemap.
3. **First real new cluster — Problems (P1):** `/probleme-casa` hub + 5 editorial problem pages, fully cross-linked to relevant services/specialists/guides, with schema and the gate applied.
4. **Extend service×location** to price categories missing a marketplace landing (gated, reuse existing engine).

Explicitly excluded from the first batch: mass programmatic estate/design subpages, problem×location, specialist-profile re-gating at scale — these wait for P2 after the gate + rendering decision.

---

## Decisions the user should confirm (these change the plan)

1. **Rendering approach for public SEO routes.** Options: (a) add prerendering/SSR for public routes only (recommended — most reliable for programmatic scale and social scrapers); (b) stay client-rendered and rely on Google JS rendering (cheaper, riskier at scale). This gates how aggressively P2 can be pursued. Assumption if no answer: pursue (a) as a P0/P1 enabler.
2. **Geographic rollout.** Assumption: Cluj-Napoca first, then top-6 cities, then national — to avoid thin city pages. Confirm or provide a target-city list.
3. **Price `?city=` URLs.** Assumption: introduce `/preturi/{slug}/{city}` and canonical/301 the query-param form to it. Confirm.
4. **Indexability Gate thresholds.** Proposed defaults above (e.g. ≥3 specialists for service×city; profile completeness for specialists). Confirm or adjust numbers.
5. **First batch scope** (section 19) — approve as-is, or move items in/out.

Nothing is implemented until the above are approved.
