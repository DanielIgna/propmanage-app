"""UX-001 · Emotional Engagement & Achievement System — compunere pură.

REUTILIZEAZĂ: House Journey (niveluri + readiness) · user_context (semnale) ·
ambassador_status (Community/Founding) · copilot_timeline (AI Timeline existent) ·
config PB (`engagement` — mesaje/praguri/badge-uri, zero hardcodare).

Livrează: Level Up Engine · Achievement Engine (10 insigne cu explainability completă) ·
Progress Celebration · Milestones · Timeline îmbunătățit. Stare per user în `engagement_state`.
Prima rulare e SILENȚIOASĂ (badge-urile deja câștigate se marchează fără animații retroactive).
"""
import logging
from datetime import datetime, timezone

from db import db
from propbenefits.config import get_config
from propbenefits.eligibility import user_context
from propbenefits.house_journey import compute_journey
from propbenefits.trust_engine import ambassador_status

logger = logging.getLogger("propmanage.engagement")


def _iso():
    return datetime.now(timezone.utc).isoformat()


async def _timeline_event(uid: str, action_id: str, title: str, kind: str, effect: str):
    """Intrare elegantă în AI Timeline existent (copilot_timeline) — idempotent."""
    if await db.copilot_timeline.find_one({"user_id": uid, "action_id": action_id}, {"_id": 1}):
        return
    now = _iso()
    await db.copilot_timeline.insert_one({
        "user_id": uid, "action_id": action_id, "title": title, "kind": kind,
        "status": "done", "recommended_at": now, "done_at": now, "effect": effect,
    })


async def _earned_map(uid: str, ctx: dict, journey: dict, amb: dict) -> dict:
    """Fiecare insignă = un semnal REAL din motoarele existente."""
    lvl = {L["key"]: L["status"] for L in journey["levels"]}
    return {
        "first_document": ctx["documents"] > 0,
        "first_request": bool(await db.requests.find_one({"client_id": uid}, {"_id": 1})),
        "first_work": ctx["completed_jobs"] > 0,
        "twin_active": lvl.get("digital_twin") == "done",
        "house_health_active": bool(ctx.get("hh_score")),
        "doc_verified": lvl.get("doc_verificata") == "done",
        "community_ambassador": bool(amb.get("is_ambassador")),
        "founding_ambassador": bool(amb.get("is_founding")),
        "imobil_verificat": lvl.get("imobil_verificat") == "done",
        "casa_publicata": lvl.get("publicat") == "done",
    }


async def engagement_summary(user: dict) -> dict:
    cfg = (await get_config()).get("engagement") or {}
    if not cfg.get("enabled", True):
        return {"enabled": False}
    uid = user.get("id") or str(user.get("_id", ""))
    ctx = await user_context(user)
    journey = await compute_journey(user, ctx=ctx)
    amb = await ambassador_status(uid)
    earned = await _earned_map(uid, ctx, journey, amb)

    state = await db.engagement_state.find_one({"user_id": uid})
    first_run = state is None
    state = state or {}
    now = _iso()
    events = []

    # ── Achievement Engine — insigne noi (prima rulare = silențios) ──
    badges_earned = dict(state.get("badges_earned") or {})
    badge_cfg = [b for b in (cfg.get("badges") or []) if b.get("enabled", True)]
    for b in badge_cfg:
        if earned.get(b["id"]) and b["id"] not in badges_earned:
            badges_earned[b["id"]] = now
            if not first_run:
                events.append({"type": "badge", "id": b["id"], "icon": b.get("icon", "🏆"),
                               "title": b["label"], "message": b.get("why", "")})
                await _timeline_event(uid, f"ux_badge_{b['id']}",
                                      f"{b.get('icon', '🏆')} {b['label']}", "badge", b.get("why", ""))

    # ── Level Up Engine ──
    cur = journey["current_level"]
    prev_level = state.get("last_level")
    if not first_run and prev_level is not None and cur > prev_level:
        for n in range(prev_level + 1, cur + 1):
            msg = (cfg.get("level_messages") or {}).get(str(n), "")
            unlock = (cfg.get("level_unlocks") or {}).get(str(n))
            events.append({"type": "level_up", "level": n, "icon": "🟢",
                           "title": f"Nivel {n} atins", "message": msg, "unlock": unlock})
            effect = f"{msg}" + (f" · Deblocat: {unlock}" if unlock else "")
            await _timeline_event(uid, f"ux_level_{n}", f"🏆 Nivel {n} atins", "level_up", effect)

    # ── Milestones + Progress Celebration (House Readiness) ──
    r = journey["readiness"]["score"]
    hit = set(state.get("milestones_hit") or [])
    for m in sorted(cfg.get("milestones") or []):
        if r >= m and m not in hit:
            hit.add(m)
            if not first_run:
                msg = (cfg.get("milestone_messages") or {}).get(str(m), "")
                events.append({"type": "milestone", "pct": m, "icon": "🎯",
                               "title": f"House Readiness {m}%", "message": msg})
                await _timeline_event(uid, f"ux_milestone_{m}", f"🎯 House Readiness {m}%", "milestone", msg)
    prev_r = state.get("last_readiness")
    min_delta = int(cfg.get("readiness_celebration_min_delta", 5))
    if not first_run and prev_r is not None and r - prev_r >= min_delta:
        delta = r - prev_r
        events.append({"type": "readiness_gain", "delta": delta, "icon": "📈",
                       "title": f"House Readiness +{delta}",
                       "message": f"Casa ta este cu {delta}% mai pregătită decât data trecută."})
        await _timeline_event(uid, f"ux_gain_{prev_r}_{r}", f"📈 House Readiness +{delta}", "milestone",
                              f"Casa ta este cu {delta}% mai pregătită.")

    await db.engagement_state.update_one({"user_id": uid}, {"$set": {
        "user_id": uid, "last_level": cur, "last_readiness": r,
        "badges_earned": badges_earned, "milestones_hit": sorted(hit), "updated_at": now,
    }}, upsert=True)

    # ── Dashboard: ultimul achievement · ultimul progres · următorul obiectiv · următorul unlock ──
    badges_out = [{**{k: b.get(k) for k in ("id", "icon", "label", "why", "meaning", "benefit", "next")},
                   "earned": b["id"] in badges_earned, "earned_at": badges_earned.get(b["id"])}
                  for b in badge_cfg]
    earned_sorted = sorted([b for b in badges_out if b["earned"]], key=lambda b: b["earned_at"] or "", reverse=True)
    last_progress = await db.copilot_timeline.find_one(
        {"user_id": uid, "status": "done"}, {"_id": 0, "signals": 0}, sort=[("done_at", -1)])
    unlocks = cfg.get("level_unlocks") or {}
    next_unlock = next(({"level": n, "label": unlocks[str(n)]} for n in range(cur + 1, 8) if str(n) in unlocks), None)
    next_milestone = next(({"pct": m, "message": (cfg.get("milestone_messages") or {}).get(str(m), "")}
                           for m in sorted(cfg.get("milestones") or []) if r < m), None)

    return {
        "enabled": True,
        "animations_enabled": bool(cfg.get("animations_enabled", True)),
        "new_events": events,
        "badges": badges_out,
        "badges_earned_count": len(earned_sorted),
        "last_achievement": earned_sorted[0] if earned_sorted else None,
        "last_progress": last_progress,
        "next_objective": journey.get("next_level"),
        "next_unlock": next_unlock,
        "milestones": {"hit": sorted(hit), "next": next_milestone, "readiness": r},
        "level": {"current": cur, "label": journey["current_label"]},
        "generated_at": now,
    }
