"""AI Security Guardian — read-only threat analysis layer.

Reads from existing security collections (NO new infrastructure):
  - audit_log
  - security_events
  - incidents
  - security_rate_buckets
  - users (for unusual login patterns)

Computes:
  - Threat Level (low/medium/high/critical)
  - Security Score (0-100)
  - Active incidents
  - Suspicious IPs
  - AI recommendations (Claude analyzes recent events)

NEVER mutates security state; NEVER blocks IPs automatically. All actions
are suggestions for human admins.
"""
import logging
from datetime import datetime, timezone, timedelta
from collections import Counter

from db import db
from ai_core.provider import call_llm, ecosystem_enabled

logger = logging.getLogger("propmanage.ai_security")


_THREAT_PROMPT = """You are a senior application security analyst for PropManage (Romanian property platform).
Given the recent security events below, identify the top 3 patterns of concern and recommend 3-5 concrete defensive actions.

Output STRICT JSON only (no markdown):
{
  "summary": "1-2 sentences in Romanian describing the current security posture",
  "threat_patterns": [
    {"name": "(short Romanian)", "severity": "low|medium|high|critical", "description": "(Romanian)", "evidence_count": <number>}
  ],
  "recommendations": [
    {"action": "(Romanian, actionable)", "priority": "P0|P1|P2|P3", "category": "auth|api|infra|data|policy"}
  ],
  "score_delta_reason": "(brief Romanian — why the score is what it is)"
}"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hours_ago(h: int) -> str:
    return (_now() - timedelta(hours=h)).isoformat()


async def _collect_recent_events(hours: int = 24) -> dict:
    """Pull a compact snapshot of last N hours from existing security collections."""
    since = _hours_ago(hours)

    events = []
    try:
        cur = db.security_events.find({"created_at": {"$gte": since}}).sort("created_at", -1).limit(200)
        async for e in cur:
            events.append({
                "type": e.get("type"),
                "severity": e.get("severity"),
                "ip": e.get("ip"),
                "endpoint": e.get("endpoint") or e.get("path"),
                "user_email": e.get("user_email"),
                "ts": e.get("created_at"),
            })
    except Exception:  # noqa: BLE001
        pass

    incidents = []
    try:
        cur = db.incidents.find({"status": {"$ne": "resolved"}}).sort("created_at", -1).limit(50)
        async for inc in cur:
            inc.pop("_id", None)
            incidents.append({
                "id": inc.get("id"),
                "title": inc.get("title"),
                "severity": inc.get("severity"),
                "status": inc.get("status"),
                "category": inc.get("category"),
                "created_at": inc.get("created_at"),
            })
    except Exception:  # noqa: BLE001
        pass

    failed_logins = []
    try:
        cur = db.audit_log.find({
            "action": {"$in": ["login_failed", "auth.login_failed", "login.failed"]},
            "created_at": {"$gte": since},
        }).sort("created_at", -1).limit(100)
        async for a in cur:
            failed_logins.append({
                "ip": a.get("ip"),
                "email": a.get("email") or a.get("user_email"),
                "ts": a.get("created_at"),
            })
    except Exception:  # noqa: BLE001
        pass

    return {"events": events, "incidents": incidents, "failed_logins": failed_logins, "since": since, "hours": hours}


_EVENT_PENALTY = {"critical": 8, "high": 4, "medium": 1.5, "low": 0.5}
_INCIDENT_PENALTY = {"critical": 10, "high": 5, "medium": 2}


def _threat_level(score: int) -> str:
    if score >= 85:
        return "low"
    if score >= 65:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"


def _compute_score(snapshot: dict) -> dict:
    """Score 0-100 (higher = safer). Pure heuristic; no LLM."""
    events = snapshot["events"]
    incidents = snapshot["incidents"]
    failed = snapshot["failed_logins"]

    score = 100
    # Penalize by severity
    score -= sum(_EVENT_PENALTY.get((e.get("severity") or "").lower(), 0) for e in events)
    score -= sum(_INCIDENT_PENALTY.get((inc.get("severity") or "medium").lower(), 0) for inc in incidents)

    # Failed login bursts
    ip_counts = Counter(f["ip"] for f in failed if f.get("ip"))
    burst_ips = [ip for ip, n in ip_counts.items() if n >= 5]
    score -= 3 * len(burst_ips)

    score = max(0, min(100, int(round(score))))

    return {
        "score": score,
        "threat_level": _threat_level(score),
        "burst_ips": burst_ips,
        "active_incidents": len(incidents),
        "events_24h": len(events),
        "failed_logins_24h": len(failed),
        "unique_ip_failed": len(ip_counts),
    }


async def overview(hours: int = 24) -> dict:
    """Full security snapshot + heuristic score (no LLM)."""
    snapshot = await _collect_recent_events(hours)
    score = _compute_score(snapshot)

    # Top events by type
    types = Counter(e.get("type") for e in snapshot["events"] if e.get("type"))
    top_types = [{"type": t, "count": n} for t, n in types.most_common(8)]

    # Suspicious IPs (any IP with multiple failed logins OR high-severity events)
    suspicious = {}
    for f in snapshot["failed_logins"]:
        if not f.get("ip"): continue
        suspicious.setdefault(f["ip"], {"ip": f["ip"], "failed_logins": 0, "events": 0})
        suspicious[f["ip"]]["failed_logins"] += 1
    for e in snapshot["events"]:
        ip = e.get("ip")
        if not ip: continue
        suspicious.setdefault(ip, {"ip": ip, "failed_logins": 0, "events": 0})
        suspicious[ip]["events"] += 1
    suspicious_list = sorted(suspicious.values(), key=lambda x: x["failed_logins"] + x["events"], reverse=True)[:10]

    return {
        "score": score["score"],
        "threat_level": score["threat_level"],
        "stats": {k: v for k, v in score.items() if k not in ("score", "threat_level")},
        "top_event_types": top_types,
        "suspicious_ips": suspicious_list,
        "active_incidents": snapshot["incidents"][:10],
        "snapshot_window_hours": hours,
        "snapshot_ts": _now().isoformat(),
    }


async def ai_recommendations(hours: int = 24) -> dict:
    """Use Claude to analyze recent events and propose defensive actions."""
    if not await ecosystem_enabled():
        return {"error": "AI Ecosystem dezactivat"}

    snapshot = await _collect_recent_events(hours)
    if not (snapshot["events"] or snapshot["incidents"] or snapshot["failed_logins"]):
        return {
            "summary": "Niciun eveniment de securitate semnificativ în ultimele 24h. Continuă monitorizarea.",
            "threat_patterns": [],
            "recommendations": [],
            "score_delta_reason": "Lipsă date relevante.",
        }

    # Compact context
    events_summary = "\n".join(
        f"- {e['type']} [{e.get('severity', '?')}] ip={e.get('ip', '?')} ep={e.get('endpoint', '?')}"
        for e in snapshot["events"][:50]
    ) or "(niciun event)"
    incidents_summary = "\n".join(
        f"- {i['title']} [{i.get('severity', '?')}] {i.get('status', '?')}"
        for i in snapshot["incidents"][:20]
    ) or "(niciun incident)"
    failed_summary = "\n".join(
        f"- ip={f.get('ip', '?')} email={f.get('email', '?')}"
        for f in snapshot["failed_logins"][:30]
    ) or "(niciun login eșuat)"

    user_msg = (
        f"## Recent security events ({hours}h)\n{events_summary}\n\n"
        f"## Active incidents\n{incidents_summary}\n\n"
        f"## Failed login attempts\n{failed_summary}\n\n"
        f"Provide JSON output."
    )

    result = await call_llm(_THREAT_PROMPT, user_msg, session_id="sec-guardian")
    if result.get("error"):
        return {"error": result["error"]}

    import json
    text = (result.get("text") or "").strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text[3:]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
    except Exception:
        return {"error": "Nu am putut parsa răspunsul AI", "raw": text[:400]}
    parsed["provider"] = result.get("provider")
    parsed["model"] = result.get("model")
    return parsed


async def log_ai_security_run(result: dict) -> None:
    """Persist a snapshot of the AI security run for memory/learning."""
    try:
        await db.security_ai_runs.insert_one({
            "id": f"sec-{int(_now().timestamp())}",
            "ts": _now().isoformat(),
            "result": result,
        })
    except Exception:  # noqa: BLE001
        pass
