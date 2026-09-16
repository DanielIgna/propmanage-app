"""BNR EUR/RON exchange rate service.

RON is the source of truth. EUR is a derived, read-only display value computed
from the official BNR daily reference rate (https://www.bnr.ro/nbrfxrates.xml).

- Persistent cache in Mongo collection `bnr_exchange_rates` (keyed by rate_date).
- Lazy daily refresh: first read of the day attempts a fresh BNR fetch; on
  failure the last valid BNR rate is kept (never invented, never hardcoded).
- If no valid rate exists at all -> returns None (caller hides EUR).
"""
import logging
import re
from datetime import datetime, timezone

import httpx

from db import db

logger = logging.getLogger("propmanage.bnr")

BNR_URL = "https://www.bnr.ro/nbrfxrates.xml"
COLLECTION = "bnr_exchange_rates"
CURRENCY = "EUR"

_CUBE_DATE_RE = re.compile(r'Cube\s+date="([0-9]{4}-[0-9]{2}-[0-9]{2})"')
_EUR_RATE_RE = re.compile(r'<Rate\s+currency="EUR"([^>]*)>([0-9.]+)</Rate>')
_MULT_RE = re.compile(r'multiplier="([0-9]+)"')


def _parse_bnr_xml(text: str):
    """Extract (rate_date, eur_ron_rate) from BNR nbrfxrates.xml content.
    Returns None if the payload is not the expected XML (e.g. WAF HTML page)."""
    if "currency=\"EUR\"" not in text:
        return None
    m_date = _CUBE_DATE_RE.search(text)
    m_rate = _EUR_RATE_RE.search(text)
    if not (m_date and m_rate):
        return None
    attrs, value = m_rate.group(1), m_rate.group(2)
    try:
        rate = float(value)
    except ValueError:
        return None
    mult = _MULT_RE.search(attrs)
    if mult:
        rate = rate / float(mult.group(1))
    if rate <= 0:
        return None
    return m_date.group(1), round(rate, 4)


async def _fetch_from_bnr():
    """Fetch + parse the official BNR reference rate. Returns dict or None."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as cli:
            resp = await cli.get(BNR_URL, headers={"Accept": "application/xml"})
        if resp.status_code != 200:
            return None
        parsed = _parse_bnr_xml(resp.text)
        if not parsed:
            logger.info("[bnr] payload not parseable (likely blocked/WAF) — keeping cache")
            return None
        rate_date, rate = parsed
        return {"currency": CURRENCY, "rate": rate, "source": "BNR", "rate_date": rate_date}
    except Exception as e:  # noqa: BLE001
        logger.info(f"[bnr] fetch failed: {type(e).__name__} — keeping cache")
        return None


async def _latest_cached():
    return await db[COLLECTION].find_one(sort=[("fetched_at", -1)])


async def _upsert(rate_doc: dict):
    now_iso = datetime.now(timezone.utc).isoformat()
    rate_doc = {**rate_doc, "fetched_at": now_iso}
    await db[COLLECTION].update_one(
        {"rate_date": rate_doc["rate_date"], "currency": CURRENCY},
        {"$set": rate_doc},
        upsert=True,
    )
    return rate_doc


def _fetched_today(doc: dict) -> bool:
    fa = doc.get("fetched_at")
    if not fa:
        return False
    try:
        d = datetime.fromisoformat(fa)
    except ValueError:
        return False
    return d.date() == datetime.now(timezone.utc).date()


async def get_eur_ron_rate(force_refresh: bool = False):
    """Return the current BNR EUR/RON rate info (cached, daily refresh, fallback).

    Shape: {currency, rate, source: 'BNR', rate_date, fetched_at, stale: bool}
    or None when no valid rate is available (caller must hide EUR)."""
    cached = await _latest_cached()
    # Reuse today's cache — avoids repeat BNR requests within the same day.
    if cached and not force_refresh and _fetched_today(cached):
        return {**cached, "stale": False}
    # Daily refresh attempt (or forced).
    fresh = await _fetch_from_bnr()
    if fresh:
        saved = await _upsert(fresh)
        return {**saved, "stale": False}
    # Fallback: last valid BNR rate (never invented).
    if cached:
        return {**cached, "stale": True}
    return None


async def seed_rate(rate: float, rate_date: str) -> dict:
    """One-time seed of a REAL BNR rate (source='BNR'). Not hardcoded in code."""
    return await _upsert({"currency": CURRENCY, "rate": round(float(rate), 4),
                          "source": "BNR", "rate_date": rate_date})


def compute_price_eur(price_ron, rate) -> float:
    """price_eur = price_ron / eur_ron_bnr. RON stays source of truth."""
    if price_ron is None or not rate:
        return None
    try:
        return round(float(price_ron) / float(rate), 2)
    except (ValueError, ZeroDivisionError):
        return None
