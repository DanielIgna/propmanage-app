"""PropBenefits · Opportunity Engine (PB-001.3) + AI Recommendation.

NU afișează reduceri — afișează OPORTUNITĂȚI. AI Recommendation decide CUI îi este
afișată fiecare oportunitate (targeting determinist + explicabil, nu tuturor):
eligibilitate × relevanță contextuală (twin, HH, oraș, nivel, urgență expirare).
"""
from datetime import datetime, timezone

from propbenefits import eligibility, membership, campaigns, ledger

KIND_LABEL = {
    "active_benefit": "Beneficiu Activ", "seasonal": "Beneficiu Sezonier",
    "local": "Beneficiu Local", "city_partner": "Beneficiu Partener Local",
    "digital_twin": "Beneficiu Digital Twin", "audit": "Beneficiu Audit",
    "house_health": "Beneficiu House Health", "fair_price": "Beneficiu FairPrice",
    "community": "Beneficiu Comunitate", "referral": "Beneficiu Comunitate",
}


def _relevance(c: dict, ctx: dict, level_rank: int) -> tuple:
    """Scor de relevanță explicabil — de ce ÎI este afișată această oportunitate."""
    score = int(c.get("priority", 3)) * 10
    why = []
    kind = c.get("kind")
    if kind == "house_health" and ctx["subscription_active"]:
        score += 15
        why.append("Ai abonament activ — beneficiul e inclus pentru tine.")
    if kind in ("digital_twin", "audit") and ctx["twins"] > 0:
        score += 15
        why.append("Ai Digital Twin activ — acces la campaniile exclusive.")
    if kind in ("local", "city_partner") and c.get("city") and c["city"].lower() in ctx["cities"]:
        score += 12
        why.append(f"Disponibil în orașul tău ({c['city']}).")
    if kind == "community":
        score += 5
        why.append("Crește comunitatea din jurul casei tale.")
    if c.get("ends_at"):
        try:
            days_left = (datetime.fromisoformat(c["ends_at"].replace("Z", "+00:00"))
                         - datetime.now(timezone.utc)).days
            if 0 <= days_left <= 7:
                score += 8
                why.append(f"Se încheie în {days_left} zile.")
        except Exception:  # noqa: BLE001
            pass
    score += level_rank * 2
    if not why:
        why.append("Se potrivește profilului proprietății tale.")
    return score, why


async def feed(user: dict, limit: int = 6) -> dict:
    ctx = await eligibility.user_context(user)
    mem = await membership.compute_membership(ctx)
    ranks = await membership.level_ranks()
    items, locked = [], []
    for c in await campaigns.active_campaigns():
        ev = eligibility.evaluate(ctx, c.get("eligibility") or {}, mem["level"]["rank"], ranks)
        already = await ledger.user_claims_for_campaign(ctx["uid"], c["id"]) if c.get("max_per_user") else 0
        base = {
            "campaign_id": c["id"], "title": c["title"], "description": c.get("description", ""),
            "kind": c["kind"], "kind_label": KIND_LABEL.get(c["kind"], "Beneficiu"),
            "benefit_title": (c.get("benefit") or {}).get("title"),
            "value_estimate": (c.get("benefit") or {}).get("value_estimate", 0),
            "ends_at": c.get("ends_at"), "auto_granted": c.get("kind") == "community",
        }
        if ev["eligible"] and (not c.get("max_per_user") or already < c["max_per_user"]):
            score, why = _relevance(c, ctx, mem["level"]["rank"])
            items.append({**base, "relevance": score, "why": why})
        elif ev["failed"]:
            locked.append({**base, "unlock": [f["label"] for f in ev["failed"]][:2]})
    items.sort(key=lambda i: -i["relevance"])
    wallet = await ledger.wallet_summary(ctx["uid"])
    return {
        "opportunities": items[:limit],
        "locked": locked[:3],
        "membership": mem,
        "wallet_counts": wallet["counts"],
        "wallet_value": wallet["total_value_available"],
    }
