"""Canonical guide-slug registry (single source of truth for the sitemap).

Kept here (backend) so the sitemap generator no longer hardcodes an inline list that
could drift from the frontend content file (frontend/src/data/ghiduri.js). When a guide
is added, add its slug + lastmod here as well. This removes the sitemap/frontend drift
flagged in the SEO audit (§11).
"""
from __future__ import annotations

# (slug, lastmod ISO date)
GUIDE_SLUGS: list[tuple[str, str]] = [
    ("ce-este-designul-interior", "2026-06-11"),
    ("design-interior-sau-arhitect", "2026-06-11"),
    ("ce-include-un-proiect-de-design-interior", "2026-06-11"),
    ("de-ce-conteaza-masuratorile-inainte-de-design", "2026-06-11"),
    ("cost-renovare-apartament-2-camere", "2026-02-29"),
    ("cum-alegi-designer-interior", "2026-02-29"),
    ("cum-verifici-instalator", "2026-02-29"),
    ("cost-instalatie-electrica-apartament", "2026-02-29"),
    ("cum-functioneaza-escrow-lucrari", "2026-02-29"),
    ("cum-alegi-zugrav-bun", "2026-02-29"),
    ("audit-tehnic-apartament-pret", "2026-07-26"),
    ("verificare-apartament-inainte-de-cumparare", "2026-07-26"),
    ("ce-este-digital-twin-locuinta", "2026-07-26"),
    ("imobile-verificate-cum-functioneaza", "2026-07-26"),
    ("cat-costa-design-interior-cluj", "2026-06-16"),
    ("cum-pregatesti-apartament-renovare", "2026-06-16"),
    ("design-interior-vs-amenajare", "2026-06-16"),
    ("ce-verifici-inainte-de-renovare-apartament", "2026-06-16"),
    ("compartimentare-cost-amenajare", "2026-06-16"),
    ("ce-documente-verifici-cumparare-apartament", "2026-06-16"),
    ("probleme-tehnice-apartament-inainte-cumparare", "2026-06-16"),
    ("verificare-imobil-digital-twin", "2026-06-16"),
    ("riscuri-cumparare-apartament-bloc-vechi", "2026-06-16"),
]
