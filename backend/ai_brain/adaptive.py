"""AI Brain · Adaptive Intelligence Engine (AIB-008) — învățare FĂRĂ Machine Learning.

Observă comportamentul real (navigație, decizii urmate/ignorate, procese) și îl folosește
EXCLUSIV pentru recalibrarea recomandărilor — zero execuție automată, zero modele opace.
Componente: Decision Feedback Loop (explicit + implicit, din snapshot-urile AIB-007),
User Behavior Learning (db.ai_brain_navigation + feedback), Role Learning (profiluri
agregate pe rol), Process Learning (stats + istoric build-uri), Adaptive Decision Score
(ajustări transparente), Confidence Engine (încredere explicabilă per decizie),
Personal Mentor (insights discrete) și Guardian Feedback (semnale, fără acțiuni).
"""
import uuid
from datetime import datetime, timezone

from db import db

FEEDBACK_ACTIONS = ("accepted", "dismissed", "snoozed", "rejected")
POSITIVE = ("accepted", "followed")
NEGATIVE = ("dismissed", "rejected", "ignored")
IGNORE_THRESHOLD = 5  # generări consecutive fără acțiune → semnal «ignored»


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid(user: dict) -> str:
    return user.get("id") or str(user.get("_id", ""))


async def _record(user: dict, decision: dict | None, decision_id: str, action: str,
                  source: str, time_to_action_s: float | None = None):
    await db.ai_brain_decision_feedback.insert_one({
        "id": uuid.uuid4().hex, "user_id": _uid(user), "role": user.get("role"),
        "decision_id": decision_id,
        "kind": (decision or {}).get("kind"), "title": (decision or {}).get("title"),
        "process_id": (decision or {}).get("process_id"),
        "score": (decision or {}).get("score"),
        "action": action, "source": source,
        "time_to_action_s": round(time_to_action_s) if time_to_action_s else None,
        "ts": _now(),
    })


# ---------------------------------------------------------------------------
# 2 · DECISION FEEDBACK LOOP
# ---------------------------------------------------------------------------
async def record_feedback(user: dict, decision_id: str, action: str) -> dict:
    if action not in FEEDBACK_ACTIONS:
        return {"ok": False, "reason": f"Acțiune invalidă. Permise: {', '.join(FEEDBACK_ACTIONS)}"}
    snap = await db.ai_brain_decisions.find_one({"user_id": _uid(user)}, {"_id": 0})
    d = next((i for i in (snap or {}).get("items", []) if i["id"] == decision_id), None)
    tta = None
    if d and d.get("first_seen_at"):
        try:
            tta = (datetime.now(timezone.utc)
                   - datetime.fromisoformat(d["first_seen_at"])).total_seconds()
        except Exception:  # noqa: BLE001
            pass
    await _record(user, d, decision_id, action, "explicit", tta)
    return {"ok": True, "action": action, "decision_id": decision_id}


async def reconcile_snapshot(user: dict, old_snap: dict | None, new_items: list) -> list:
    """Carry-over first_seen/seen_count + feedback IMPLICIT: decizie dispărută pentru că
    procesul a avansat = «followed»; decizie persistentă ≥N generări = «ignored» (o dată)."""
    now = _now()
    old = {i["id"]: i for i in (old_snap or {}).get("items", [])}
    for d in new_items:
        prev = old.pop(d["id"], None)
        d["first_seen_at"] = (prev or {}).get("first_seen_at") or now
        d["seen_count"] = ((prev or {}).get("seen_count") or 0) + 1
        d["ignored_recorded"] = bool((prev or {}).get("ignored_recorded"))
        if d["seen_count"] >= IGNORE_THRESHOLD and not d["ignored_recorded"]:
            await _record(user, d, d["id"], "ignored", "implicit")
            d["ignored_recorded"] = True
    # deciziile dispărute: verifică dacă procesul a avansat spre tranziția recomandată
    from ai_brain.process import process_state
    for did, prev in list(old.items())[:20]:
        outcome = "expired"
        tta = None
        if prev.get("kind") in ("process_transition", "process_start") and prev.get("process_id"):
            try:
                st = await process_state(user, process_id=prev["process_id"])
                target = ((prev.get("transition") or {}).get("to"))
                if st.get("status") == "completed" or (target and st.get("current_state") == target) \
                        or (prev["kind"] == "process_start" and st.get("status") == "in_progress"):
                    outcome = "followed"
            except Exception:  # noqa: BLE001
                pass
        elif prev.get("kind") == "mentor_action":
            outcome = "followed"  # acțiunile mentor dispar doar când starea DB s-a schimbat
        if outcome == "followed" and prev.get("first_seen_at"):
            try:
                tta = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(prev["first_seen_at"])).total_seconds()
            except Exception:  # noqa: BLE001
                pass
        await _record(user, prev, did, outcome, "implicit", tta)
    return new_items


# ---------------------------------------------------------------------------
# 6+7 · ADAPTIVE DECISION SCORE + CONFIDENCE ENGINE (transparente)
# ---------------------------------------------------------------------------
async def kind_acceptance(role: str, kind: str) -> tuple:
    pos = await db.ai_brain_decision_feedback.count_documents(
        {"role": role, "kind": kind, "action": {"$in": list(POSITIVE)}})
    neg = await db.ai_brain_decision_feedback.count_documents(
        {"role": role, "kind": kind, "action": {"$in": list(NEGATIVE)}})
    n = pos + neg
    return (pos / n if n else 0.5), n


def _confidence(d: dict, rate: float, n: int) -> tuple:
    factors = []
    has_stats = bool(d.get("process_id"))
    data_q = 1.0 if has_stats and d.get("entity") else 0.75 if has_stats else 0.55
    factors.append(f"Calitatea datelor: {'proces + entitate reală' if data_q == 1.0 else 'proces fără entitate' if data_q == 0.75 else 'regulă deterministă fără proces'} ({round(data_q * 100)}%)")
    strength = n / (n + 5)
    history = strength * rate + (1 - strength) * 0.5
    factors.append(f"Istoric feedback ({d.get('kind')}, rolul tău): {n} reacții, "
                   f"{round(rate * 100)}% urmate" if n else "Fără istoric de feedback încă — pornesc neutru (50%)")
    fvals = list((d.get("factors") or {}).values())
    consistency = sum(fvals) / len(fvals) if fvals else 0.5
    factors.append(f"Consistența factorilor de scor: {round(consistency * 100)}%")
    conf = round(100 * (0.40 * data_q + 0.30 * history + 0.30 * consistency))
    return max(5, min(99, conf)), factors


async def enrich_decisions(user: dict, items: list) -> list:
    role = user.get("role") or ""
    uid = _uid(user)
    dismissed_ids = {f["decision_id"] async for f in db.ai_brain_decision_feedback.find(
        {"user_id": uid, "action": {"$in": ["dismissed", "rejected"]}}, {"decision_id": 1}).limit(200)}
    rate_cache: dict = {}
    for d in items:
        kind = d.get("kind")
        if kind not in rate_cache:
            rate_cache[kind] = await kind_acceptance(role, kind)
        rate, n = rate_cache[kind]
        adj, why = 0, []
        if n >= 3:
            delta = round(20 * (rate - 0.5))
            if delta:
                adj += delta
                why.append(f"Utilizatorii cu rolul «{role}» au urmat {round(rate * 100)}% din "
                           f"recomandările de tip {kind} ({n} reacții) → {'+' if delta > 0 else ''}{delta}p.")
        if d.get("seen_count", 0) >= IGNORE_THRESHOLD:
            adj -= 15
            why.append(f"Ai văzut această recomandare de {d['seen_count']} ori fără să acționezi → -15p.")
        if d["id"] in dismissed_ids:
            adj -= 25
            why.append("Ai respins explicit această recomandare anterior → -25p.")
        if d.get("process_id"):
            proc = await db.ai_brain_processes.find_one({"id": d["process_id"]}, {"stats": 1})
            st = (proc or {}).get("stats") or {}
            if st.get("total", 0) >= 5 and st.get("stale_count", 0) / st["total"] < 0.2:
                adj += 5
                why.append("Procesul țintă e eficient (sub 20% stagnare) → +5p.")
        d["base_score"] = d["score"]
        d["score"] = max(0, min(100, d["score"] + adj))
        d["adaptive"] = {"adjustment": adj, "role_acceptance": {"rate": round(rate, 2), "n": n},
                         "reasons": why}
        d["confidence"], d["confidence_factors"] = _confidence(d, rate, n)
    items.sort(key=lambda d: -d["score"])
    return items


# ---------------------------------------------------------------------------
# 3 · USER BEHAVIOR LEARNING
# ---------------------------------------------------------------------------
async def build_user_profile(user: dict) -> dict:
    uid = _uid(user)
    events = [e async for e in db.ai_brain_navigation.find(
        {"user_id": uid}, {"_id": 0}).sort("ts", -1).limit(300)]
    modules: dict = {}
    bigrams: dict = {}
    day_first: dict = {}
    for e in reversed(events):
        m = modules.setdefault(e["module"], {"module": e["module"], "visits": 0, "time_ms": 0})
        m["visits"] += 1
        m["time_ms"] += e.get("duration_ms") or 0
        day = e["ts"][:10]
        day_first.setdefault(day, e["module"])
    prev = None
    for e in reversed(events):
        if prev and prev != e["module"]:
            bigrams[(prev, e["module"])] = bigrams.get((prev, e["module"]), 0) + 1
        prev = e["module"]
    starts: dict = {}
    for m in day_first.values():
        starts[m] = starts.get(m, 0) + 1
    usual_start = max(starts, key=starts.get) if starts else None

    fb: dict = {}
    async for d in db.ai_brain_decision_feedback.aggregate([
            {"$match": {"user_id": uid}},
            {"$group": {"_id": "$action", "n": {"$sum": 1}}}]):
        fb[d["_id"]] = d["n"]
    ignored_kinds = [d["_id"] async for d in db.ai_brain_decision_feedback.aggregate([
        {"$match": {"user_id": uid, "action": {"$in": list(NEGATIVE)}}},
        {"$group": {"_id": "$kind", "n": {"$sum": 1}}}, {"$sort": {"n": -1}}, {"$limit": 3}])]

    snap = await db.ai_brain_decisions.find_one({"user_id": uid}, {"_id": 0})
    stuck = [{"title": i["title"], "seen_count": i.get("seen_count", 1)}
             for i in (snap or {}).get("items", []) if i.get("seen_count", 0) >= IGNORE_THRESHOLD]
    return {
        "user_id": uid, "role": user.get("role"),
        "top_modules": sorted(modules.values(), key=lambda m: -m["visits"])[:5],
        "usual_start_module": usual_start,
        "common_flows": [{"from": a, "to": b, "count": c}
                         for (a, b), c in sorted(bigrams.items(), key=lambda kv: -kv[1])[:5]],
        "feedback": fb,
        "followed": sum(fb.get(a, 0) for a in POSITIVE),
        "ignored": sum(fb.get(a, 0) for a in NEGATIVE),
        "ignored_kinds": ignored_kinds,
        "persistent_recommendations": stuck,
        "total_navigation_events": len(events),
        "built_at": _now(),
    }


# ---------------------------------------------------------------------------
# 4 · ROLE LEARNING — profiluri agregate pe rol
# ---------------------------------------------------------------------------
async def role_profiles() -> list:
    out = []
    roles = [r for r in await db.users.distinct("role") if r]
    for role in roles:
        mods: dict = {}
        async for d in db.ai_brain_navigation.aggregate([
                {"$match": {"role": role}},
                {"$group": {"_id": "$module", "visits": {"$sum": 1},
                            "time_ms": {"$sum": {"$ifNull": ["$duration_ms", 0]}}}},
                {"$sort": {"visits": -1}}, {"$limit": 5}]):
            mods[d["_id"]] = {"visits": d["visits"], "time_ms": d["time_ms"]}
        fb: dict = {}
        async for d in db.ai_brain_decision_feedback.aggregate([
                {"$match": {"role": role}},
                {"$group": {"_id": "$action", "n": {"$sum": 1}}}]):
            fb[d["_id"]] = d["n"]
        pos = sum(fb.get(a, 0) for a in POSITIVE)
        neg = sum(fb.get(a, 0) for a in NEGATIVE)
        out.append({
            "role": role,
            "users": await db.users.count_documents({"role": role}),
            "top_modules": [{"module": k, **v} for k, v in mods.items()],
            "feedback": fb, "followed": pos, "ignored": neg,
            "acceptance_rate": round(pos / (pos + neg), 2) if pos + neg else None,
        })
    return sorted(out, key=lambda r: -r["users"])


# ---------------------------------------------------------------------------
# 5 · PROCESS LEARNING (+ istoric pentru degradare)
# ---------------------------------------------------------------------------
async def snapshot_process_stats(run_id: str):
    """Apelat la fiecare build_processes — istoric pentru detectarea degradării."""
    now = _now()
    docs = []
    async for p in db.ai_brain_processes.find({"kind": "business", "stats": {"$ne": None}},
                                              {"id": 1, "stats": 1}):
        st = p["stats"]
        docs.append({"process_id": p["id"], "total": st.get("total", 0),
                     "stale": st.get("stale_count", 0), "active": st.get("active", 0),
                     "run_id": run_id, "ts": now})
    if docs:
        await db.ai_brain_process_stats_history.insert_many(docs)


async def process_learning() -> dict:
    bottlenecks, delayed, abandoned, efficient, unused = [], [], [], [], []
    async for p in db.ai_brain_processes.find({"kind": "business"}, {"_id": 0}):
        st = p.get("stats") or {}
        total = st.get("total", 0)
        for a in (st.get("abandon_points") or [])[:2]:
            bottlenecks.append({"process": p["name"], "state": a["state"], "stuck": a["stuck"]})
        for field, hours in sorted((st.get("avg_hours_from_start") or {}).items(),
                                   key=lambda kv: -kv[1])[:1]:
            if hours > 72:
                delayed.append({"process": p["name"], "stage": field, "avg_hours": hours})
        if total >= 5:
            ratio = st.get("stale_count", 0) / total
            if ratio > 0.5:
                abandoned.append({"process": p["name"], "stale": st["stale_count"],
                                  "total": total, "ratio": round(ratio, 2)})
            elif ratio < 0.2:
                efficient.append({"process": p["name"], "total": total, "ratio": round(ratio, 2)})
        if total >= 10:
            seen = set((st.get("by_status") or {}))
            for s in p.get("steps", []):
                if s not in seen and s not in p.get("initial_states", []):
                    unused.append({"process": p["name"], "state": s,
                                   "note": "definită în cod, 0 instanțe au atins-o vreodată"})
    # degradare: comparație cu penultimul snapshot
    degradations = []
    pids = await db.ai_brain_process_stats_history.distinct("process_id")
    for pid in pids:
        hist = [h async for h in db.ai_brain_process_stats_history.find(
            {"process_id": pid}, {"_id": 0}).sort("ts", -1).limit(2)]
        if len(hist) == 2 and hist[0]["total"] >= 10 and hist[1]["total"]:
            r_now = hist[0]["stale"] / hist[0]["total"]
            r_prev = hist[1]["stale"] / hist[1]["total"]
            if r_now - r_prev > 0.15:
                degradations.append({"process_id": pid,
                                     "stale_ratio_now": round(r_now, 2),
                                     "stale_ratio_before": round(r_prev, 2)})
    return {"bottlenecks": sorted(bottlenecks, key=lambda b: -b["stuck"])[:8],
            "delayed_stages": delayed[:6], "abandoned_processes": abandoned[:6],
            "efficient_processes": efficient[:6], "possibly_unused_states": unused[:8],
            "degradations": degradations[:6]}


# ---------------------------------------------------------------------------
# 8 · PERSONAL MENTOR — insights discrete din comportamentul real
# ---------------------------------------------------------------------------
async def personal_insights(user: dict, path: str = "") -> list:
    profile = await build_user_profile(user)
    out = []
    if profile["usual_start_module"] and profile["total_navigation_events"] >= 10:
        out.append({"kind": "usual_start",
                    "text": f"Observ că de obicei începi cu «{profile['usual_start_module']}» — "
                            "îți pregătesc recomandările în consecință."})
    followed, ignored = profile["followed"], profile["ignored"]
    if followed + ignored >= 3:
        if followed > ignored:
            out.append({"kind": "feedback_positive",
                        "text": f"Ai urmat {followed} din ultimele {followed + ignored} recomandări — "
                                "continui să le calibrez după acțiunile tale."})
        else:
            out.append({"kind": "feedback_negative",
                        "text": f"Ai ignorat {ignored} din ultimele {followed + ignored} recomandări — "
                                "le-am scăzut prioritatea și caut altele mai utile."})
    if profile["persistent_recommendations"] and len(out) < 2:
        p0 = profile["persistent_recommendations"][0]
        out.append({"kind": "often_skipped",
                    "text": f"«{p0['title']}» e un pas frecvent omis de utilizatorii aflați în aceeași "
                            "situație — cei care îl fac avansează vizibil mai repede."})
    return out[:2]


# ---------------------------------------------------------------------------
# 9 · ADAPTIVE INTELLIGENCE DASHBOARD (admin)
# ---------------------------------------------------------------------------
async def adaptive_overview() -> dict:
    totals: dict = {}
    async for d in db.ai_brain_decision_feedback.aggregate([
            {"$group": {"_id": "$action", "n": {"$sum": 1}}}]):
        totals[d["_id"]] = d["n"]
    by_kind = []
    async for d in db.ai_brain_decision_feedback.aggregate([
            {"$match": {"kind": {"$ne": None}}},
            {"$group": {"_id": {"kind": "$kind", "action": "$action"}, "n": {"$sum": 1}}}]):
        by_kind.append(d)
    kinds: dict = {}
    for d in by_kind:
        k = d["_id"]["kind"]
        kinds.setdefault(k, {"kind": k, "followed": 0, "ignored": 0})
        if d["_id"]["action"] in POSITIVE:
            kinds[k]["followed"] += d["n"]
        elif d["_id"]["action"] in NEGATIVE:
            kinds[k]["ignored"] += d["n"]
    recalibrations = []
    for k, v in kinds.items():
        n = v["followed"] + v["ignored"]
        if n >= 3:
            rate = v["followed"] / n
            delta = round(20 * (rate - 0.5))
            if delta:
                recalibrations.append({"kind": k, "n": n, "acceptance": round(rate, 2),
                                       "score_adjustment": delta})
    confidences = []
    async for snap in db.ai_brain_decisions.find({}, {"items.confidence": 1}).limit(100):
        confidences.extend([i["confidence"] for i in snap.get("items", []) if i.get("confidence")])
    avg_time: dict = {}
    async for d in db.ai_brain_decision_feedback.aggregate([
            {"$match": {"action": {"$in": list(POSITIVE)}, "time_to_action_s": {"$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$time_to_action_s"}, "n": {"$sum": 1}}}]):
        avg_time = {"avg_seconds": round(d["avg"]), "n": d["n"]}
    return {
        "feedback_totals": totals,
        "followed": sum(totals.get(a, 0) for a in POSITIVE),
        "ignored": sum(totals.get(a, 0) for a in NEGATIVE),
        "by_kind": sorted(kinds.values(), key=lambda k: -(k["followed"] + k["ignored"])),
        "recalibrations": recalibrations,
        "avg_confidence": round(sum(confidences) / len(confidences)) if confidences else None,
        "decisions_tracked": len(confidences),
        "avg_time_to_action": avg_time or None,
        "generated_at": _now(),
    }
