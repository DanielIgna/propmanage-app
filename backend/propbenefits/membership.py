"""PropBenefits · Membership Levels (PB-001.6) — niveluri derivate din date, nu asignate manual.

REUSE (CORE-001): experience_tier existent = semnal, nu se rescrie sistemul de tiers.
Nivelurile oferă prioritate + acces la campanii, NU reduceri automate.
"""
from propbenefits.config import get_config


def _points(ctx: dict, weights: dict) -> tuple:
    detail = []

    def add(key, ok):
        pts = int(weights.get(key, 0))
        detail.append({"key": key, "ok": bool(ok), "points": pts if ok else 0, "max": pts})

    add("subscription_active", ctx["subscription_active"])
    add("digital_twin", ctx["twins"] > 0)
    add("documents_5plus", ctx["documents"] >= 5)
    add("house_health", ctx["hh_score"])
    add("completed_jobs_3plus", ctx["completed_jobs"] >= 3)
    add("referrals_2plus", ctx["referrals_claimed"] >= 2)
    add("account_90days", ctx["account_days"] >= 90)
    add("email_verified", ctx["email_verified"])
    add("experience_tier_verified", ctx["experience_tier"] in ("verified", "pro"))
    add("ambassador", ctx.get("is_ambassador"))
    total = sum(d["points"] for d in detail)
    return total, detail


async def compute_membership(ctx: dict) -> dict:
    cfg = await get_config()
    total, detail = _points(ctx, cfg["level_points"])
    levels = sorted(cfg["levels"], key=lambda l: l["min_points"])
    current = levels[0]
    for lv in levels:
        if total >= lv["min_points"]:
            current = lv
    nxt = next((lv for lv in levels if lv["min_points"] > total), None)
    return {
        "points": total,
        "level": {"key": current["key"], "name": current["name"], "rank": current["rank"],
                  "perks": current.get("perks", [])},
        "next_level": ({"key": nxt["key"], "name": nxt["name"], "min_points": nxt["min_points"],
                        "points_needed": nxt["min_points"] - total} if nxt else None),
        "breakdown": detail,
    }


async def level_ranks() -> dict:
    cfg = await get_config()
    return {lv["key"]: lv["rank"] for lv in cfg["levels"]}
