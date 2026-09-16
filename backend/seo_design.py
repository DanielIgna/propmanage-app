"""Canonical Design Interior slug registry (single source of truth for the sitemap).

The editorial/commercial content lives in the frontend data file
(frontend/src/data/designInterior.js); this backend list mirrors the slugs so the
sitemap can emit them and the Admin SEO tooling can recognise/classify them.

- DESIGN_PAGES / DESIGN_STYLES: unique, original, indexable content (always index).
- DESIGN_LOCAL_CITIES: candidate cities for /design-interior/{city}. These are
  GATED at runtime by the EXISTING SSOT gate (verified `interior_design` specialists
  per city ≥ threshold) — no second gate implementation.
"""
from __future__ import annotations

# (slug, lastmod ISO date) — commercial + room pages
DESIGN_PAGES: list[tuple[str, str]] = [
    ("apartament", "2026-06-11"),
    ("apartament-2-camere", "2026-06-11"),
    ("apartament-3-camere", "2026-06-11"),
    ("apartament-mic", "2026-06-11"),
    ("apartament-vechi", "2026-06-11"),
    ("casa", "2026-06-11"),
    ("pret", "2026-06-11"),
    ("renovare", "2026-06-11"),
    ("3d", "2026-06-11"),
    ("implementare", "2026-06-11"),
    ("living", "2026-06-11"),
    ("bucatarie", "2026-06-11"),
    ("dormitor", "2026-06-11"),
    ("baie", "2026-06-11"),
    ("birouri", "2026-06-16"),
    ("spatii-comerciale", "2026-06-16"),
]

# (slug, lastmod) — style landing pages (the REAL PropManage style system)
DESIGN_STYLES: list[tuple[str, str]] = [
    ("modern", "2026-06-11"),
    ("scandinavian", "2026-06-11"),
    ("minimalist", "2026-06-11"),
    ("industrial", "2026-06-11"),
    ("japandi", "2026-06-11"),
    ("mediterranean", "2026-06-11"),
    ("classic", "2026-06-11"),
    ("rustic", "2026-06-11"),
    ("boho", "2026-06-11"),
]

# Candidate cities/zones for local Design Interior pages (valid routes).
DESIGN_LOCAL_CITIES: list[str] = [
    "bucuresti", "cluj-napoca", "brasov", "oradea", "timisoara", "sibiu", "iasi",
    # Cluj metro-area localities + neighborhoods
    "floresti", "baciu", "apahida", "marasti-cluj", "gheorgheni-cluj",
    # București neighborhood + Ilfov localities
    "baneasa", "otopeni", "corbeanca", "buftea", "balotesti",
]

# Local pages with UNIQUE authored content (INDEX). Cities NOT listed here render a
# generic template and stay NOINDEX (canonical → /design-interior).
DESIGN_LOCAL_INDEXABLE: set[str] = {
    "cluj-napoca", "bucuresti", "timisoara", "brasov", "iasi", "sibiu", "oradea",
    "floresti", "baciu", "apahida", "marasti-cluj", "gheorgheni-cluj",
    "baneasa", "otopeni", "corbeanca", "buftea", "balotesti",
}

DESIGN_PAGE_SLUGS = {s for s, _ in DESIGN_PAGES}
DESIGN_STYLE_SLUGS = {s for s, _ in DESIGN_STYLES}
