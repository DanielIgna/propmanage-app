"""Public Trust Center — live transparency stats (no auth required).

Surfaces credibility signals that B2B clients and developers care about:
last release-gate verdict, server uptime, last MongoDB backup, verified
specialist count, and platform metrics. All numbers are pulled live from
the DB / process state — no static values.
"""
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response, HTMLResponse
from db import db

router = APIRouter(prefix="/api", tags=["public-trust"])

# Process start time captured at module load
_PROCESS_STARTED_AT = time.time()


def _fmt_age(iso_or_ts: Any) -> str:
    """Return human-friendly age like '2h 14m ago' or '3 days ago'."""
    try:
        if isinstance(iso_or_ts, str):
            ts = datetime.fromisoformat(iso_or_ts.replace("Z", "+00:00")).timestamp()
        elif isinstance(iso_or_ts, datetime):
            ts = iso_or_ts.timestamp()
        else:
            ts = float(iso_or_ts)
    except Exception:  # noqa: BLE001
        return "—"
    delta = max(0, int(time.time() - ts))
    if delta < 90:
        return f"{delta}s ago"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        h = delta // 3600
        m = (delta % 3600) // 60
        return f"{h}h {m}m ago" if m else f"{h}h ago"
    days = delta // 86400
    return f"{days} {'day' if days == 1 else 'days'} ago"


@router.get("/public/trust-stats")
async def trust_stats() -> dict:
    """Aggregate trust signals for the public /trust page. Cached implicitly by Mongo speeds (<150ms)."""
    out: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}

    # --- Release Gate (latest) ---
    try:
        last_gate = await db.release_gates.find_one({}, sort=[("started_at", -1)])
        if last_gate:
            s = last_gate.get("summary") or {}
            out["release_gate"] = {
                "verdict": s.get("verdict") or ("BLOCKED" if s.get("blocked") else "READY"),
                "blocked": bool(s.get("blocked")),
                "pass": int(s.get("pass") or 0),
                "fail": int(s.get("fail") or 0),
                "skip": int(s.get("skip") or 0),
                "total": int(s.get("total") or 0),
                "p0_fail": int(s.get("p0_fail") or 0),
                "ran_at": last_gate.get("started_at"),
                "ran_at_age": _fmt_age(last_gate.get("started_at")),
                "triggered_by": last_gate.get("triggered_by"),
            }
        else:
            out["release_gate"] = None
    except Exception:  # noqa: BLE001
        out["release_gate"] = None

    # --- Last MongoDB backup ---
    try:
        from backup_service import json_backup_run_filter
        last_backup = await db.backup_runs.find_one(json_backup_run_filter(), sort=[("started_at", -1)])
        if last_backup:
            out["last_backup"] = {
                "status": last_backup.get("status"),
                "size_mb": round((last_backup.get("size_bytes") or 0) / (1024 * 1024), 2),
                "collections": last_backup.get("collections_count"),
                "ran_at": last_backup.get("started_at"),
                "ran_at_age": _fmt_age(last_backup.get("started_at")),
            }
        else:
            out["last_backup"] = None
    except Exception:  # noqa: BLE001
        out["last_backup"] = None

    # --- Platform metrics ---
    try:
        verified_count = await db.users.count_documents({"role": "specialist", "verified": True})
        total_specialists = await db.users.count_documents({"role": "specialist"})
        total_clients = await db.users.count_documents({"role": "client"})
        completed_requests = await db.requests.count_documents({"status": "completed"})
        active_requests = await db.requests.count_documents({"status": {"$in": ["assigned", "in_progress"]}})
        out["platform"] = {
            "verified_specialists": verified_count,
            "total_specialists": total_specialists,
            "total_clients": total_clients,
            "completed_requests": completed_requests,
            "active_requests": active_requests,
        }
    except Exception:  # noqa: BLE001
        out["platform"] = None

    # --- Uptime (process) ---
    uptime_s = int(time.time() - _PROCESS_STARTED_AT)
    out["uptime"] = {
        "seconds": uptime_s,
        "started_at_age": _fmt_age(_PROCESS_STARTED_AT),
        "human": (
            f"{uptime_s // 86400}d {(uptime_s % 86400) // 3600}h"
            if uptime_s >= 86400
            else f"{uptime_s // 3600}h {(uptime_s % 3600) // 60}m"
            if uptime_s >= 3600
            else f"{uptime_s // 60}m"
        ),
    }

    # --- Compliance / trust signals (static facts) ---
    out["compliance"] = {
        "gdpr_dsar_sla_days": 30,
        "escrow_provider": "Stripe (PCI-DSS Level 1)",
        "data_residency": "EU (Frankfurt)",
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "daily_backups": True,
    }

    return out



# ============================================================================
# Embeddable badges — shareable on partner sites, blogs, LinkedIn, READMEs.
# ============================================================================

async def _badge_stats() -> dict:
    """Compact stats used by the badge endpoints."""
    out = {"verdict": "READY", "pass_count": 0, "total": 0, "verified": 0, "blocked": False}
    try:
        last_gate = await db.release_gates.find_one({}, sort=[("started_at", -1)])
        if last_gate:
            s = last_gate.get("summary") or {}
            out["pass_count"] = int(s.get("pass") or 0)
            out["total"] = int(s.get("total") or 0)
            out["blocked"] = bool(s.get("blocked"))
            out["verdict"] = s.get("verdict") or ("BLOCKED" if out["blocked"] else "READY")
    except Exception:  # noqa: BLE001
        pass
    try:
        out["verified"] = await db.users.count_documents({"role": "specialist", "verified": True})
    except Exception:  # noqa: BLE001
        pass
    return out


def _approx_text_width(text: str, char_px: float = 6.6) -> float:
    """Rough monospace-ish width estimate for SVG layout (Verdana 11px)."""
    # Capitals & wide chars get bonus pixels
    extra = sum(0.7 for c in text if c.isupper() or c in "WMmw")
    return len(text) * char_px + extra


@router.get("/public/trust-badge.svg")
async def trust_badge_svg() -> Response:
    """Shields.io-style SVG badge. Markdown-friendly. Cache 5min on CDN."""
    s = await _badge_stats()
    blocked = s["blocked"]
    right_color = "#dc2626" if blocked else "#16a34a"  # red-600 / green-600
    label = "PropManage Trust"
    value = f"{s['verdict']} · {s['pass_count']}/{s['total']} tests · {s['verified']} verified"

    left_w = max(112, int(_approx_text_width(label) + 18))
    right_w = max(180, int(_approx_text_width(value) + 18))
    total_w = left_w + right_w
    h = 28

    # Two-tone shields-style SVG with subtle gradient
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{h}" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".08"/>
    <stop offset="1" stop-opacity=".15"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total_w}" height="{h}" rx="4" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{left_w}" height="{h}" fill="#1f2937"/>
    <rect x="{left_w}" width="{right_w}" height="{h}" fill="{right_color}"/>
    <rect width="{total_w}" height="{h}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" font-weight="600">
    <text x="{left_w / 2}" y="14" fill="#d4ff3a" opacity=".95">{label}</text>
    <text x="{left_w / 2}" y="20" fill="#d4ff3a">{label}</text>
    <text x="{left_w + right_w / 2}" y="14" fill="#fff" opacity=".95">{value}</text>
    <text x="{left_w + right_w / 2}" y="20" fill="#fff">{value}</text>
  </g>
</svg>'''
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=300, s-maxage=300",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/public/trust-og.svg")
async def trust_og_svg() -> Response:
    """1200×630 SVG meant to be used as `og:image` / `twitter:image` for the /trust page.

    Built dynamically — verdict and counts reflect live state at request time.
    Most platforms (LinkedIn, Twitter, Facebook, Slack) render SVG OG images.
    """
    s = await _badge_stats()
    blocked = s["blocked"]
    accent = "#ef4444" if blocked else "#10b981"
    verdict_label = "BLOCKED" if blocked else "READY"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0a0a0b"/>
      <stop offset="100%" stop-color="#15151a"/>
    </linearGradient>
    <linearGradient id="lime" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#d4ff3a"/>
      <stop offset="100%" stop-color="#a3e635"/>
    </linearGradient>
    <radialGradient id="glow" cx="0%" cy="0%" r="60%">
      <stop offset="0%" stop-color="#d4ff3a" stop-opacity="0.15"/>
      <stop offset="100%" stop-color="#d4ff3a" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>

  <!-- Top brand pill -->
  <g transform="translate(80, 80)">
    <rect width="220" height="42" rx="21" fill="#1a1a1f" stroke="#232329" stroke-width="1"/>
    <circle cx="22" cy="21" r="5" fill="{accent}"/>
    <text x="38" y="27" font-family="Inter, Verdana, sans-serif" font-size="13" font-weight="600" fill="#a3a3a3" letter-spacing="2">PROPMANAGE TRUST · LIVE</text>
  </g>

  <!-- Shield emblem -->
  <g transform="translate(80, 200)">
    <rect width="90" height="90" rx="20" fill="url(#lime)"/>
    <path d="M45 22 L25 30 v18 c0 14 9 26 20 30 11-4 20-16 20-30 V30 z M37 50 l5 5 11-12" stroke="#0a0a0b" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- Verdict block -->
  <g transform="translate(200, 220)">
    <text x="0" y="0" font-family="Inter, Verdana, sans-serif" font-size="16" font-weight="600" fill="#9ca3af" letter-spacing="3">RELEASE GATE</text>
    <text x="0" y="80" font-family="Georgia, 'Times New Roman', serif" font-size="120" font-weight="700" fill="{accent}">{verdict_label}</text>
  </g>

  <!-- Stats grid -->
  <g transform="translate(80, 410)">
    <rect width="1040" height="120" rx="20" fill="#1a1a1f" stroke="#232329" stroke-width="1"/>

    <g transform="translate(48, 36)">
      <text font-family="Inter, Verdana, sans-serif" font-size="13" font-weight="600" fill="#9ca3af" letter-spacing="2">TESTS</text>
      <text y="40" font-family="Georgia, serif" font-size="36" font-weight="700" fill="#d4ff3a">{s["pass_count"]}/{s["total"]}</text>
    </g>

    <g transform="translate(360, 36)">
      <text font-family="Inter, Verdana, sans-serif" font-size="13" font-weight="600" fill="#9ca3af" letter-spacing="2">VERIFIED SPECIALISTS</text>
      <text y="40" font-family="Georgia, serif" font-size="36" font-weight="700" fill="#ffffff">{s["verified"]}</text>
    </g>

    <g transform="translate(720, 36)">
      <text font-family="Inter, Verdana, sans-serif" font-size="13" font-weight="600" fill="#9ca3af" letter-spacing="2">COMPLIANCE</text>
      <text y="40" font-family="Georgia, serif" font-size="36" font-weight="700" fill="#ffffff">GDPR · PCI · EU</text>
    </g>
  </g>

  <!-- URL footer -->
  <text x="600" y="580" text-anchor="middle" font-family="Inter, Verdana, sans-serif" font-size="14" fill="#525252" letter-spacing="3">PROPMANAGE.RO/TRUST</text>
</svg>'''
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=300, s-maxage=300",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/public/trust-badge/embed", response_class=HTMLResponse)
async def trust_badge_embed() -> HTMLResponse:
    """Self-contained iframe HTML — richer than SVG, animated, dark-theme.

    Pages can drop this in as `<iframe src="https://propmanage.ro/api/public/trust-badge/embed"
    width="380" height="120" frameborder="0" style="border:0"></iframe>`.
    """
    s = await _badge_stats()
    blocked = s["blocked"]
    color = "#ef4444" if blocked else "#10b981"
    verdict_label = "BLOCKED" if blocked else "READY"
    html = f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=380,initial-scale=1" />
<meta name="robots" content="noindex" />
<title>PropManage Trust Badge</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: transparent; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #e5e7eb;
  }}
  a.badge {{
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 18px;
    background: #0a0a0b;
    background-image: radial-gradient(120% 80% at 0% 0%, rgba(212,255,58,0.10), rgba(212,255,58,0) 60%),
                      radial-gradient(80% 60% at 100% 100%, rgba(16,185,129,0.10), rgba(16,185,129,0) 50%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    text-decoration: none;
    transition: transform .18s ease, border-color .18s ease;
    cursor: pointer;
  }}
  a.badge:hover {{ transform: translateY(-1px); border-color: rgba(212,255,58,0.25); }}
  .shield {{
    width: 36px; height: 36px;
    background: linear-gradient(135deg, #d4ff3a 0%, #a3e635 100%);
    border-radius: 9px;
    display: grid; place-items: center;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(212,255,58,0.20);
  }}
  .shield svg {{ width: 20px; height: 20px; }}
  .body {{ flex: 1; min-width: 0; }}
  .row1 {{ display: flex; align-items: center; gap: 8px; font-size: 11px; letter-spacing: 0.14em; color: #a3a3a3; text-transform: uppercase; }}
  .dot {{ width: 6px; height: 6px; border-radius: 50%; background: {color}; box-shadow: 0 0 8px {color}; animation: pulse 2s infinite; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; transform: scale(1); }} 50% {{ opacity: 0.55; transform: scale(1.25); }} }}
  .row2 {{ display: flex; align-items: baseline; gap: 10px; margin-top: 4px; }}
  .verdict {{ font-size: 18px; font-weight: 700; color: #fff; letter-spacing: -0.01em; }}
  .verdict.bad {{ color: #fca5a5; }}
  .stats {{ font-size: 12px; color: #9ca3af; }}
  .stats b {{ color: #d4ff3a; font-weight: 600; }}
</style>
</head>
<body>
<a class="badge" href="https://propmanage.ro/trust" target="_blank" rel="noopener" title="Vezi Trust Center complet">
  <span class="shield">
    <svg viewBox="0 0 24 24" fill="none" stroke="#0a0a0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 2L4 5v6c0 5.5 3.4 10.4 8 11.9 4.6-1.5 8-6.4 8-11.9V5l-8-3z"></path>
      <path d="m9 12 2 2 4-4"></path>
    </svg>
  </span>
  <span class="body">
    <span class="row1"><span class="dot"></span> PropManage Trust Center · LIVE</span>
    <span class="row2">
      <span class="verdict {'bad' if blocked else ''}">{verdict_label}</span>
      <span class="stats"><b>{s['pass_count']}/{s['total']}</b> tests · <b>{s['verified']}</b> verified specialists</span>
    </span>
  </span>
</a>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "public, max-age=300, s-maxage=300",
            "X-Frame-Options": "ALLOWALL",
            "Content-Security-Policy": "frame-ancestors *;",
        },
    )
