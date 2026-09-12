"""CEO Dashboard — vedere strategică doar pentru super-admin (owner).

Compune Business Health + Financial Cockpit + Command Center feed + Top 3
recomandări AI într-un singur payload. Zero calcule duplicate.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from db import db
from deps import require_role
from sub_admin_deps import is_super_admin

router = APIRouter(prefix="/api/admin/ceo", tags=["ceo-dashboard"])
logger = logging.getLogger("propmanage.ceo")


@router.get("")
async def ceo_dashboard(admin=Depends(require_role("admin"))):
    if not is_super_admin(admin):
        raise HTTPException(403, "CEO Dashboard este disponibil doar pentru super-admin (owner).")

    from routes.business_health import compute_health
    from routes.command_center import _build_feed
    health = await compute_health()
    feed = await _build_feed()
    raw = feed["raw"]

    from routes.financial_cockpit import financial_cockpit
    cockpit = await financial_cockpit(admin)

    from value_loop import value_loop_summary
    vl = await value_loop_summary()

    from property_intelligence import maturity_summary, risk_summary
    maturity = await maturity_summary()
    property_risks = await risk_summary()

    recos_doc = await db.command_center_recos.find_one({"_id": "latest"}, {"_id": 0})
    top3 = (recos_doc or {}).get("recommendations", [])
    top3 = [r for r in top3 if not r.get("done")][:3] if top3 else []

    cash_ok = cockpit["revenue"]["last_30d"] >= cockpit["revenue"]["prev_30d"] * 0.8

    return {
        "business_score": health["overall"],
        "business_color": health["overall_color"],
        "departments": health["departments"],
        "revenue": cockpit["revenue"],
        "cash_flow_status": "OK" if cash_ok else "ATENȚIE",
        "escrow_held": cockpit["escrow"]["held"],
        "mrr_ron": cockpit["subscriptions"]["mrr_ron"],
        "arr_ron": cockpit["subscriptions"]["arr_ron"],
        "new_requests_24h": raw["new_requests_24h"],
        "new_users_24h": raw["new_users_24h"],
        "marketplace_trend_pct": raw["marketplace_trend_pct"],
        "warnings_count": len(feed["warnings"]),
        "value_loop": vl,
        "maturity": maturity,
        "property_risks": property_risks,
        "top_priorities": top3,
        "generated_at": feed["generated_at"],
    }
