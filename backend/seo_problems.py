"""Canonical problem-slug registry (single source of truth for the sitemap).

The editorial content lives in the frontend data file (frontend/src/data/problemeCasa.js);
this backend list mirrors the slugs so the sitemap can emit them. Problem pages are
editorial with unique content → always indexable (per SEO gate §7).
When adding a problem page, add its slug + lastmod here too.
"""
from __future__ import annotations

# (slug, lastmod ISO date)
PROBLEM_SLUGS: list[tuple[str, str]] = [
    ("infiltratii-acoperis", "2026-06-11"),
    ("mucegai-igrasie", "2026-06-11"),
    ("fisuri-pereti", "2026-06-11"),
    ("umezeala-pereti", "2026-06-11"),
    ("probleme-acoperis", "2026-06-11"),
]
