# PROPMANAGE — SEO SEARCH DEMAND VALIDATION

Companion to `plan.md` (SEO Expansion Map). Research + validation + prioritization only — nothing implemented, no app/route/metadata/sitemap/DB changes.

Goal: find the best intersection of **Google search demand × PropManage product data × commercial intent × defensible content × scalable architecture**, and recommend the first implementation batch.

## Method & honesty notes
- Demand and SERP were validated via live Romanian web searches (Sept 2026). Exact monthly search volumes require paid keyword tools and are **not** asserted — they are marked `ESTIMATE` (with basis) or `UNKNOWN`. Relative demand (High/Med/Low) is inferred from SERP richness (number of competing pages, presence of calculators/aggregators, breadth of city coverage) — a defensible proxy, not a measured volume.
- "Owned SERP" = the type of site currently ranking; it tells us how hard entry is and what page type Google rewards.
- Everything is cross-checked against what PropManage actually has (routes, price engine, service×city engine, guides, verified specialists/listings) per the audit.

---

## SERP reality per cluster (validated)

| Cluster | Who owns the SERP now | Demand (proxy) | Entry difficulty | PropManage angle that can win |
|---|---|---|---|---|
| Prices "cât costă X" | Generic content/calculator sites (brig.ro, start-business, playtech, ecalculator, devizrapid, renoveaza) — **no marketplace** | High (many articles + calculators per query) `ESTIMATE` | Medium | Real observed price data + city + "primești oferte reale de la specialiști verificați + escrow" |
| Renovation cost | Same content pattern (financiarul, necesit, brig, infohome, imobiliare imoexpert) | High `ESTIMATE` | Medium | Data + guides + link to price/service pages |
| Service × city ("electrician Cluj") | Individual local service companies + maps/directories | High in supply cities `ESTIMATE` | Medium (per city) | Marketplace/directory of verified specialists (already built) — needs supply |
| Problems ("infiltrații ce faci") | Blogs/informational + insurance/legal (condoflow, lovedeco, pint, asirom, casamagazin) | High `ESTIMATE` | Medium | Genuinely useful problem→component→verified-specialist path + Cartea Casei documentation |
| Verified estate — generic ("apartamente de vânzare Cluj") | **Portals lock it** (imobiliare.ro, storia, olx, blitz, remax, taboo) | Very High `ESTIMATE` | **Very hard — avoid** | Do NOT compete generically |
| Verified estate — niche ("apartamente/imobile verificate") | Sparse; largely PropManage's own category | Low-Med `ESTIMATE` | Low (niche) | Own the "verificat/audit tehnic/digital twin" category; gate on inventory |
| Pre-purchase audit ("verificare apartament înainte de cumpărare", "audit tehnic apartament preț") | Specialized SMBs (homeplanning, imocheck, auditera, homeinspector) — **no portals** | Med `ESTIMATE` (priced 1.200–4.800 RON) | Medium (winnable) | Direct product fit: audit tehnic + imobile verificate + Cartea Casei; strong commercial intent |
| Design interior + city ("amenajări interioare apartament Cluj") | Design studios (renovlies, nikydecor, studioa, idesign, lanadesign) — SMBs | Med-High `ESTIMATE` | Medium | Already have `/design-interior`; competitors use exactly our keywords ("la cheie", "randări 3D") |
| Digital Twin locuință | Emerging/technical (Schneider/ETAP, xplorate, BIM) | Low/emerging `ESTIMATE` | Low but tiny demand | Educational/authority anchor, not volume |
| Cartea tehnică imobil / an construcție | Informational (baniinostri, infopinia) | Med `ESTIMATE` | Low-Med | Bridge to Cartea Casei; informational top-of-funnel |
| House Health / PVI / Twin Maturity (as terms) | No external demand (proprietary terms) | ~Zero external | n/a | Brand pages only — do NOT chase as SEO volume |

---

## 6. PropManage FIT scores (1–5) & 7. Priority formula

Sub-scores per keyword family: **Demand, CommercialValue, ProductFit, DataAvailability, Defensibility, Scalability, SEORisk** (SEORisk: 5 = high risk).

**Priority (0–100), explained:**
```
Core = 5×( 0.22·Demand + 0.20·CommercialValue + 0.22·ProductFit
          + 0.18·Defensibility + 0.18·Scalability )        → 0..25 → ×4 = 0..100
Penalty = 6·SEORisk + 4·(5−DataAvailability) + 3·Complexity  (Complexity 1..5)
Priority = round( Core×4 − Penalty , clamped 0..100 )
```
Rationale: ProductFit and Demand weighted highest (a page must both be searched for AND authentically answerable by PropManage); Defensibility/Scalability reward durable, expandable clusters; SEORisk penalized hardest (thin/duplicate/doorway is existential); DataGap and Complexity slow but don't kill.

---

## 8A. TOP SEO OPPORTUNITIES (quality over count — 22 families that pass the bar)

| Rank | Keyword family | Intent | Demand | Comm. | Fit | Scale | Risk | Priority | Recommended page |
|---|---|---|---|---|---|---|---|---|---|
| 1 | verificare apartament/casă înainte de cumpărare | Commercial Inv. | 4 | 5 | 5 | 3 | 2 | ~90 | Hub `/imobile-verificate` + educational + `/ghiduri` (exists, expand) |
| 2 | audit tehnic apartament/locuință preț | Commercial Inv. | 3 | 5 | 5 | 3 | 2 | ~87 | Guide + `/preturi` (audit) + estate hub cross-link |
| 3 | cât costă {lucrare} {oraș} (14 categ.) | Commercial | 5 | 4 | 5 | 5 | 3 | ~86 | `/preturi/:slug` (exists) → add `/preturi/:slug/:city` |
| 4 | {serviciu} {oraș} (electrician/instalator/zugrav/…) | Local/Transactional | 4 | 5 | 4 | 5 | 3 | ~84 | `/marketplace/:service-:city` (exists) — supply-gated |
| 5 | cât costă renovare apartament {2 camere} {an} | Commercial | 5 | 4 | 4 | 4 | 3 | ~80 | Guide + `/preturi` cross-links |
| 6 | amenajări interioare {tip} {oraș} + la cheie | Commercial/Local | 4 | 5 | 5 | 4 | 3 | ~83 | `/design-interior` (exists) + gated subpages |
| 7 | randări 3D fotorealiste / proiect design interior preț | Commercial | 3 | 5 | 5 | 3 | 2 | ~80 | `/design-interior` sections + `/preturi/design-interior` |
| 8 | infiltrații / igrasie / mucegai / umezeală ce faci | Problem/Solution | 5 | 3 | 4 | 4 | 3 | ~76 | `/probleme-casa/:slug` (new) |
| 9 | fisuri pereți / probleme fundație / risc seismic | Problem/Solution | 3 | 3 | 4 | 3 | 3 | ~68 | `/probleme-casa/:slug` (new) |
| 10 | probleme acoperiș / reparație acoperiș / infiltrații acoperiș | Problem/Solution | 4 | 4 | 4 | 4 | 3 | ~75 | Problem page + service (acoperișuri) + city |
| 11 | verificare/întreținere instalație electrică | Commercial Inv. | 3 | 4 | 5 | 3 | 2 | ~78 | `/componente-casa/:slug` + service electric |
| 12 | verificare/revizie instalație sanitară / centrală | Commercial Inv. | 3 | 4 | 5 | 3 | 2 | ~77 | Component + service |
| 13 | termoizolație/fațadă preț | Commercial | 3 | 4 | 4 | 4 | 3 | ~72 | `/preturi/termoizolatii-fatade` (exists) + component |
| 14 | tâmplărie PVC / ferestre preț {oraș} | Commercial | 3 | 4 | 4 | 4 | 3 | ~71 | `/preturi/tamplarie-pvc` (exists) + city |
| 15 | montaj/recondiționare parchet preț | Commercial | 3 | 3 | 4 | 4 | 3 | ~66 | `/preturi/montaj-parchet` (exists) + service×city |
| 16 | gresie & faianță montaj preț | Commercial | 3 | 3 | 4 | 4 | 3 | ~65 | `/preturi/gresie-faianta` (exists) + service×city |
| 17 | apartamente/imobile verificate {oraș} | Property Discovery (niche) | 2 | 5 | 5 | 4 | 3 | ~73 | `/imobile-verificate/:city` (new, inventory-gated) |
| 18 | case verificate / proprietăți verificate | Property Discovery (niche) | 2 | 5 | 5 | 3 | 3 | ~70 | Estate type hubs (inventory-gated) |
| 19 | cum verifici un instalator/zugrav/designer | Informational | 3 | 3 | 4 | 3 | 2 | ~66 | `/ghiduri/:slug` (exists, expand) |
| 20 | cum funcționează escrow lucrări | Informational/Brand | 2 | 4 | 5 | 2 | 1 | ~68 | `/ghiduri` (exists) |
| 21 | cartea tehnică a imobilului / an construcție | Informational | 3 | 3 | 4 | 2 | 2 | ~62 | Educational → Cartea Casei / House Health |
| 22 | digital twin locuință / ce este | Informational/Brand | 2 | 3 | 5 | 2 | 1 | ~60 | `/digital-twin` (exists) |

Excluded from the top list on purpose (below the bar): generic "apartamente de vânzare {oraș}" (portal-locked), PVI/Twin Maturity (no external demand), problem×micro-neighborhood (no inventory).

---

## 8B. TOP 10 CLUSTERS

1. **Pre-purchase verification / audit tehnic** — reason: highest commercial intent that PropManage answers natively; SERP is winnable SMBs, no portals. Main kw: verificare apartament înainte de cumpărare, audit tehnic apartament preț, inspecție tehnică locuință. Long-tail: "+{oraș}", "+casă", "+cost". Existing: `/imobile-verificate`, guides (audit-tehnic, verificare-apartament). Missing: dedicated audit landing + city variants + price. Opportunity: High. Complexity: Low-Med.
2. **Prices ("cât costă X {oraș} {an}")** — reason: durable long-tail, real data engine already exists, SERP is generic content (beatable with data). Existing: `/preturi/:slug` (14). Missing: per-city URLs, more internal links. Opportunity: High. Complexity: Low.
3. **Service × Location** — reason: local transactional; engine exists (9×22). Missing: 5 categories with price data but no landing; supply gate. Opportunity: High where supply exists. Complexity: Low-Med.
4. **Design interior sub-clusters** — reason: proven commercial demand, competitors validate exact keywords; parent already optimized. Missing: room/type/city gated subpages. Opportunity: High. Complexity: Med.
5. **Problems** — reason: large top-of-funnel; blogs own it, PropManage adds action (specialist + documentation). Existing: partial via guides. Missing: `/probleme-casa` hub + pages. Opportunity: High (traffic), Med (commercial). Complexity: Med (editorial).
6. **Components / systems** — reason: bridges problems↔services↔House Health; commercial-investigation intent (verificare/întreținere {sistem}). Missing: `/componente-casa`. Opportunity: Med-High. Complexity: Med.
7. **Renovation cost / guides** — reason: high-volume informational feeding prices/services. Existing: some guides. Missing: expand editorial. Opportunity: High traffic. Complexity: Low-Med.
8. **Verified estate (niche + local/type hubs)** — reason: own the "verified" category (avoid generic portals). Existing: hub only. Missing: location/type hubs + gated listing detail. Opportunity: Med (supply-bound), high commercial. Complexity: Med.
9. **Maintenance** — reason: recurring informational (calendar, durată de viață, revizie). Existing: scattered. Missing: maintenance hub. Opportunity: Med. Complexity: Med.
10. **House Health / Digital Twin / Cartea Casei (authority)** — reason: brand + internal-link hub, not volume; "cartea tehnică imobil" has real informational demand. Existing: `/scorul-casei`, `/digital-twin`, 1 guide. Missing: small educational cluster. Opportunity: Low-direct/High-authority. Complexity: Low-Med.

---

## 8C. QUICK WINS (page + data + infra already exist — only SEO expansion needed)

1. **`/preturi/:slug` (14 pages)** — already live with real data + FAQ schema. Win: strengthen titles/meta per category (year+city), add BreadcrumbList, tighten internal links to matching service×city. No new pages.
2. **`/marketplace/:service[-city]` (~207)** — already generated + in sitemap. Win: ensure per-page meta/canonical + supply-based noindex on empty cities; add City/Service breadcrumbs.
3. **`/design-interior`** — already optimized; win: add `/preturi/design-interior` and designer×city cross-links; enrich with "amenajare apartament/casă" sections.
4. **`/ghiduri` (10 guides)** — already indexed with schema. Win: internal-link guides ⇄ prices ⇄ services ⇄ (future) problems; expand 3–4 high-intent guides (audit tehnic, verificare apartament {oraș}).
5. **`/imobile-verificate` hub** — already optimized; win: add gated `/imobile-verificate/:id` to sitemap and location hubs when inventory exists.
6. **Sitemap/canonical hygiene** — single low-risk technical pass (from audit P0): index-only-gated URLs, add estate detail, consolidate guide-slug source.

These require no new templates and carry near-zero UX risk.

---

## 8D. PROGRAMMATIC SEO OPPORTUNITIES (which combinations to scale)

| Combination | Demand | Data exists? | Worth indexing? | Gate |
|---|---|---|---|---|
| SERVICE × CITY | High (supply cities) | Yes (specialists + `seo_slugs`) | Yes, selectively | ≥3 active specialists in city; else noindex,follow |
| PRICE × CATEGORY × CITY | High long-tail | Yes (price observations by city) | Yes | ≥1 non-preliminary category OR ≥3 services with data; label preliminary |
| PROPERTY TYPE × CITY (estate) | Med (niche) | Only if listings | Yes, inventory-bound | ≥1 verified listing of that type in city |
| PROPERTY × LOCATION (listing detail) | Med | Yes (listings) | Yes, gated | Verified + published + audit summary + photos/twin; expired→410/noindex |
| PROBLEM × CITY | Med | Partial (specialists mapped to service) | Later, selectively | Problem maps to a service with ≥3 specialists in city; else keep national problem page only |
| COMPONENT × CITY | Low-Med | Partial | Later / rarely | Prefer national component page; city only if strong service supply |
| DESIGN TYPE × PROPERTY TYPE × CITY | Med-High | Partial (designers + city) | Yes, gated | Unique content per combo + ≥1 designer in city; else canonical to parent |

Principle: scale a combination only when the deepest dimension still has a real backing entity and unique content. Never emit an empty grid cell as an indexable page.

---

## 8E. CONTENT THAT SHOULD NOT BE BUILT

- **Generic property discovery** ("apartamente/case de vânzare {oraș}") — portal-locked (imobiliare.ro, storia, olx, blitz, remax); unwinnable and off-mission. Only pursue the "verificate/audit" niche.
- **PVI / Twin Maturity as SEO targets** — proprietary terms with ~zero external search demand. Keep as in-product/brand concepts, not indexable volume plays.
- **Problem × micro-neighborhood / component × every city** — doorway/thin risk with no inventory. Keep national pages; expand to city only where supply justifies.
- **Specialist profiles at scale without a quality gate** — mass-indexing thin profiles = sitewide thin-content risk. Index only complete, verified profiles.
- **Per-listing pages for expired/removed/draft listings** — noindex/410, never keep as stale indexables.
- **Auto-spun "cât costă" pages for categories with no price data** — 404, not an empty template.
- **Duplicating `/design-interior` as near-identical city pages without unique local content** — canonical to parent instead.
- **Any location page with no real local signals** (0 specialists, 0 listings, 0 price rows).

---

## 9. RECOMMENDED FIRST SEO IMPLEMENTATION BATCH (for approval — not implemented)

### MUST BUILD NOW (5)
1. **Technical foundation + Indexability Gate (P0 enabler)**
   - Template/URL: cross-cutting (canonical + robots-meta server-side; sitemap-index listing only gate-passing URLs; add gated estate detail; consolidate guide-slug source).
   - Intent: all. Reason: makes existing + future pages reliably indexable; prevents thin/duplicate. Data: existing entity counts. Dev: shared gate service + sitemap segmentation. Upside: compounding across every cluster. Risk: Low. Priority: P0.
2. **Prices — promote city to indexable URLs (`/preturi/:slug/:city`)**
   - Keyword: "cât costă {lucrare} {oraș} {an}". Intent: commercial. Reason: real data engine exists; SERP beatable with data; huge long-tail. Data: price observations by city (exists). Dev: new city route reusing the price builder + canonical from `?city=`. Upside: High. Risk: Low-Med (gate empty cities). Priority: P0/P1.
3. **Pre-purchase audit / verification landing + guide expansion**
   - URL: dedicated audit landing under the estate/house-health area + expand `/ghiduri` (audit tehnic, verificare apartament {oraș}). Keyword: "verificare apartament înainte de cumpărare", "audit tehnic apartament preț". Intent: commercial investigation. Reason: highest commercial fit, winnable SMB SERP, bridges estate↔house health. Data: exists (audit/verification product + prices). Dev: 1 landing + 2–3 guides + schema + internal links. Upside: High. Risk: Low. Priority: P1.
4. **Problems cluster hub + first 5 problem pages** (`/probleme-casa` + infiltrații, igrasie/mucegai, umezeală, fisuri, probleme acoperiș)
   - Intent: problem/solution (top-of-funnel). Reason: large demand; PropManage differentiates with the problem→component→verified-specialist→escrow path. Data: services/specialists mapping exists; content editorial. Dev: hub + 5 editorial pages + schema + gate + internal links. Upside: High traffic, Med commercial. Risk: Med (editorial quality). Priority: P1.
5. **Service × Location coverage completion (supply-gated)**
   - Extend the existing engine to the price categories missing a marketplace landing (acoperișuri, construcții/zidărie, termoizolații/fațade, gips-carton, amenajări exterioare) where product-supported; apply the supply gate. Intent: local/transactional. Data: specialists (exists). Dev: extend slug map + gate. Upside: High in supply cities. Risk: Med (thin without supply). Priority: P1.

### BUILD LATER (P2/P3)
- Components cluster (`/componente-casa`) + component×service links.
- Design interior room/type/city gated subpages.
- Verified estate location + type hubs; gated listing-detail indexing at scale.
- Maintenance hub; House Health/PVI/Digital Twin educational authority cluster.
- Problem×city / component×city (only where supply justifies).
- (Cross-cutting decision) Server-side rendering/prerender for public SEO routes — recommended before aggressive P2 programmatic scaling.

### DO NOT BUILD
- Generic property-discovery pages competing with portals.
- PVI / Twin Maturity as SEO volume targets.
- Any programmatic grid cell without backing entities; thin specialist profiles; stale/expired listing pages; empty location/price pages.

---

## Decisions to confirm before implementation
1. Approve the 5 MUST-BUILD-NOW items as the first batch (or move items between NOW / LATER).
2. City rollout for #2/#5: start Cluj-Napoca + top-6 (București, Timișoara, Iași, Brașov, Constanța) then expand — confirm.
3. Rendering: confirm whether server-side rendering/prerender for public routes is approved as the P1 enabler (affects how far #2/#4/#5 scale). Assumption if unanswered: proceed client-rendered for the first batch, revisit before P2.
4. Indexability Gate thresholds (≥3 specialists for service×city; ≥1 listing for estate hubs; profile completeness for specialists) — confirm or adjust.

Nothing is implemented until these are approved.
