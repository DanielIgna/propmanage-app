"""Shared Indexability Gate (SEO) — single source of truth deciding whether a public
page is index/noindex and, if noindex, what to canonical to. Computed server-side from
REAL backing-entity counts and used by both the sitemap generator and (via API) templates.

Approved defaults (SEO Expansion plan §7):
  - service × city   → index only if >= MIN_SPECIALISTS_SERVICE_CITY active specialists
  - estate loc. hub  → index only if >= MIN_LISTINGS_ESTATE_HUB published listings
  - estate detail    → index only if the listing is published (passed all gates)
  - specialist page  → index only if verified, not deleted, has a specialty + a trust signal
  - editorial (problems/guides/components) → always index (real, unique content)

Only gate-passing URLs are emitted in the sitemap.
"""
from __future__ import annotations

MIN_SPECIALISTS_SERVICE_CITY = 3
MIN_LISTINGS_ESTATE_HUB = 1


def decision(index: bool, canonical: str | None = None, reason: str = "") -> dict:
    return {"index": bool(index), "canonical": canonical, "reason": reason}


def gate_service_city(specialist_count: int, canonical_parent: str | None = None) -> dict:
    if specialist_count >= MIN_SPECIALISTS_SERVICE_CITY:
        return decision(True, reason=f"{specialist_count} specialiști")
    return decision(False, canonical=canonical_parent,
                    reason=f"doar {specialist_count} specialiști (<{MIN_SPECIALISTS_SERVICE_CITY})")


def gate_estate_hub(listing_count: int) -> dict:
    return decision(listing_count >= MIN_LISTINGS_ESTATE_HUB,
                    reason=f"{listing_count} anunțuri")


def listing_is_indexable(listing: dict) -> bool:
    """Only published verified-estate listings are indexable (drafts/expired/removed are not)."""
    if not listing:
        return False
    if listing.get("deleted"):
        return False
    return (listing.get("status") or "").lower() == "published"


def specialist_is_indexable(u: dict) -> bool:
    """Verified, non-deleted, has a specialty and at least one trust signal
    (reviews or rating). Keeps thin/empty profiles out of the index."""
    if not u:
        return False
    if not u.get("verified") or u.get("deleted"):
        return False
    has_specialty = bool(u.get("specialty") or u.get("specialties") or u.get("services") or u.get("service_categories"))
    reviews = int(u.get("reviews_count") or u.get("review_count") or 0)
    has_signal = reviews > 0 or float(u.get("rating") or 0) > 0 or bool(u.get("bio") or u.get("about") or u.get("portfolio"))
    return bool(has_specialty and has_signal)
