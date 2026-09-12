"""Marketing Attribution — leagă comportamentul clientului (conversii) de sursa Google Ads.

Read-model REAL peste colecțiile `marketing_attributions` (first-touch per vizitator, populat
din trackerul first-party) și `marketing_conversions` (evenimentele de conversie: sign_up /
first_request / purchase / offer_accepted). Reutilizat de Business Health (dept Marketing) și
de Autonomy Activity. Zero date sintetice — totul derivat din evenimente reale.
"""
import logging
from datetime import datetime, timezone, timedelta

from db import db

logger = logging.getLogger("propmanage.attribution")

CONVERSION_ACTIONS = ["sign_up", "first_request", "offer_accepted", "purchase"]


def _now():
    return datetime.now(timezone.utc)


async def compute_attribution_summary(days: int = 30) -> dict:
    since = (_now() - timedelta(days=days)).isoformat()

    # Vizitatori atribuiți Google Ads (au gclid) în fereastră
    ad_visitors = await db.marketing_attributions.count_documents(
        {"gclid": {"$nin": ["", None]}, "first_seen_at": {"$gte": since}})
    utm_google = await db.marketing_attributions.count_documents(
        {"source": "google", "first_seen_at": {"$gte": since}})

    # Conversii pe acțiune (total + atribuite Google Ads)
    by_action = {}
    for act in CONVERSION_ACTIONS:
        total = await db.marketing_conversions.count_documents({"action": act, "ts": {"$gte": since}})
        ad = await db.marketing_conversions.count_documents({"action": act, "ad_attributed": True, "ts": {"$gte": since}})
        by_action[act] = {"total": total, "ad_attributed": ad}

    total_conv = await db.marketing_conversions.count_documents({"ts": {"$gte": since}})
    ad_conv = await db.marketing_conversions.count_documents({"ad_attributed": True, "ts": {"$gte": since}})

    # Valoare atribuită (ex: escrow finanțat) din conversii purchase ad-attributed
    ad_value = 0.0
    async for c in db.marketing_conversions.find(
        {"action": "purchase", "ad_attributed": True, "ts": {"$gte": since}}, {"value": 1}):
        ad_value += float(c.get("value") or 0)

    # Top campanii (după conversii ad-attributed)
    top = []
    pipe = [
        {"$match": {"ad_attributed": True, "ts": {"$gte": since}}},
        {"$group": {"_id": {"$ifNull": ["$utm_campaign", "(fără campanie)"]}, "conversions": {"$sum": 1}}},
        {"$sort": {"conversions": -1}}, {"$limit": 5},
    ]
    async for r in db.marketing_conversions.aggregate(pipe):
        top.append({"campaign": r["_id"] or "(fără campanie)", "conversions": r["conversions"]})

    # Rata de conversie a traficului Google Ads: sign_up ad-attributed / vizitatori ad
    signups_ad = by_action.get("sign_up", {}).get("ad_attributed", 0)
    ad_signup_rate = round(signups_ad / ad_visitors * 100, 1) if ad_visitors else None

    return {
        "window_days": days,
        "google_ads_id": "AW-18423416296",
        "ad_visitors": ad_visitors,
        "google_source_visitors": utm_google,
        "conversions_total": total_conv,
        "conversions_ad_attributed": ad_conv,
        "conversions_by_action": by_action,
        "ad_attributed_value_ron": round(ad_value, 2),
        "ad_signup_rate_pct": ad_signup_rate,
        "top_campaigns": top,
    }
