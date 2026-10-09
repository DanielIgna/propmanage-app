"""PropManage — Dev Velocity Tracker.

Parses `git log` for the last N days, categorizes changes, asks Claude to
produce a Romanian executive summary, and emails admins weekly.

Weekly cron: Mondays 09:30 Europe/Bucharest (after Morning Briefing).
"""
from __future__ import annotations

import os
import re
import logging
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import db

logger = logging.getLogger("propmanage.dev_velocity")

REPO_DIR = "/app"
CACHE_TTL_MIN = 30  # in-memory cache


# ---------------------------------------------------------------------------
# Git parsing
# ---------------------------------------------------------------------------

def _git(args: list[str]) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", REPO_DIR] + args,
            capture_output=True, text=True, timeout=30,
        )
        return r.stdout if r.returncode == 0 else ""
    except Exception as e:  # noqa: BLE001
        logger.error(f"[DevVelocity] git failed: {e}")
        return ""


def _categorize(path: str) -> str:
    if path.startswith("backend/routes/"):     return "api_endpoints"
    if path.startswith("backend/") and path.endswith(".py"):  return "backend_logic"
    if "/tests/" in path or path.endswith("_test.py") or "/test_" in path:
        return "tests"
    if path.startswith("frontend/src/pages/admin/"):  return "admin_panels"
    if path.startswith("frontend/src/pages/"):    return "frontend_pages"
    if path.startswith("frontend/src/components/"): return "frontend_components"
    if path.startswith("frontend/src/hooks/"):    return "frontend_hooks"
    if path.startswith("frontend/src/utils/") or path.startswith("frontend/src/data/"):
        return "frontend_data"
    if path.startswith("frontend/src/") and path.endswith((".js", ".jsx", ".ts", ".tsx")):
        return "frontend_other"
    if path.endswith((".md", ".txt")) or "PRD" in path or "CHANGELOG" in path:
        return "docs"
    if path.endswith(".env") or "package.json" in path or "requirements.txt" in path:
        return "config"
    return "other"


def _parse_commit_header(line: str) -> dict:
    """Parse a 'COMMIT|sha|date|author|subject' git log line into a dict."""
    parts = line.split("|", 4)
    return {
        "sha": parts[1][:8] if len(parts) > 1 else "",
        "date": parts[2] if len(parts) > 2 else "",
        "author": parts[3] if len(parts) > 3 else "",
        "subject": parts[4] if len(parts) > 4 else "",
        "files": [],
        "added": 0,
        "deleted": 0,
    }


def _parse_numstat_line(line: str) -> Optional[tuple[int, int, str]]:
    """Parse a 'added<tab>deleted<tab>path' numstat line; returns (added, deleted, path) or None."""
    m = re.match(r"^(\S+)\s+(\S+)\s+(.+)$", line.strip())
    if not m:
        return None
    added, deleted, path = m.groups()
    added_n = int(added) if added.isdigit() else 0
    deleted_n = int(deleted) if deleted.isdigit() else 0
    return (added_n, deleted_n, path)


def _aggregate_categories(files_touched: dict) -> dict:
    """Aggregate per-file stats into category buckets (JSON-friendly output)."""
    categories: dict[str, dict] = {}
    for path, info in files_touched.items():
        cat = info["category"]
        c = categories.setdefault(cat, {"files": set(), "added": 0, "deleted": 0, "touches": 0})
        c["files"].add(path)
        c["added"] += info["added"]
        c["deleted"] += info["deleted"]
        c["touches"] += info["touches"]
    for cat in categories:
        categories[cat]["files"] = sorted(categories[cat]["files"])
        categories[cat]["file_count"] = len(categories[cat]["files"])
    return categories


def collect_velocity(days: int = 7) -> dict:
    """Parse git log for the last N days, return categorized stats + commits list."""
    since = f"{days} days ago"
    raw = _git(["log", f"--since={since}", "--pretty=format:COMMIT|%H|%ai|%an|%s", "--numstat"])
    if not raw:
        return {"days": days, "commits": [], "totals": {}, "categories": {}, "files_changed": []}

    commits: list[dict] = []
    current: Optional[dict] = None
    files_touched: dict[str, dict] = {}

    for line in raw.split("\n"):
        if line.startswith("COMMIT|"):
            if current:
                commits.append(current)
            current = _parse_commit_header(line)
            continue
        if not (line.strip() and current):
            continue
        parsed = _parse_numstat_line(line)
        if not parsed:
            continue
        added_n, deleted_n, path = parsed
        current["files"].append(path)
        current["added"] += added_n
        current["deleted"] += deleted_n
        f = files_touched.setdefault(path, {"category": _categorize(path), "added": 0, "deleted": 0, "touches": 0})
        f["added"] += added_n
        f["deleted"] += deleted_n
        f["touches"] += 1
    if current:
        commits.append(current)

    totals = {
        "commits": len(commits),
        "files_changed": len(files_touched),
        "lines_added": sum(c["added"] for c in commits),
        "lines_deleted": sum(c["deleted"] for c in commits),
        "authors": len({c["author"] for c in commits if c["author"]}),
    }
    files_changed = sorted(
        [{"path": p, **i} for p, i in files_touched.items()],
        key=lambda x: -x["touches"],
    )[:15]

    return {
        "days": days,
        "since": (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d"),
        "until": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "totals": totals,
        "categories": _aggregate_categories(files_touched),
        "files_changed": files_changed,
        "commits": commits[:30],  # cap for transport
    }


# ---------------------------------------------------------------------------
# AI summary (Claude via Emergent LLM key)
# ---------------------------------------------------------------------------

async def ai_summary(stats: dict) -> str:
    """Ask Claude to produce a Romanian executive summary of the week's velocity."""
    try:
        from llm_chat import LlmChat, UserMessage
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[DevVelocity] llm_chat import failed: {e}")
        return _fallback_summary(stats)

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return _fallback_summary(stats)

    cats = stats.get("categories", {})
    totals = stats.get("totals", {})
    commits = stats.get("commits", [])
    cat_lines = []
    for name, info in cats.items():
        cat_lines.append(f"- {name}: {info['file_count']} fișiere, +{info['added']}/-{info['deleted']} linii")
    commit_subjects = "\n".join(f"- [{c['sha']}] {c['subject']}" for c in commits[:20])

    prompt = f"""Ești un asistent care scrie rapoarte săptămânale de dezvoltare pentru CEO-ul PropManage (non-tehnic).

Datele din ultimele {stats['days']} zile ({stats['since']} → {stats['until']}):

TOTAL:
- {totals.get('commits', 0)} commits
- {totals.get('files_changed', 0)} fișiere modificate
- +{totals.get('lines_added', 0)} / -{totals.get('lines_deleted', 0)} linii
- {totals.get('authors', 0)} contribuitor(i)

CATEGORII:
{chr(10).join(cat_lines)}

PRINCIPALELE COMMIT-URI:
{commit_subjects}

Scrie un raport executiv în română, MAXIM 200 de cuvinte, structurat astfel:
1. **Headline** — o frază de impact (ce s-a făcut săptămâna asta).
2. **Highlights** — 3-5 bullets concrete (ce funcționalități noi, ce s-a îmbunătățit, ce s-a curățat).
3. **Velocitate** — interpretarea numerelor (mult/normal/încet pentru o săptămână).
4. **Recomandare** — 1 frază: pe ce să se concentreze săptămâna viitoare bazat pe ce a rămas pe Backlog.

Stil: direct, fără jargon, fără emojis, fără markdown peste 2 niveluri. Ca un raport pentru board.
"""

    try:
        chat = LlmChat(
            api_key=key,
            session_id=f"dev_velocity_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            system_message="Ești un asistent expert în analiză tehnică și raportare executivă. Răspunzi doar în română."
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        response = await chat.send_message(UserMessage(text=prompt))
        return (response or "").strip() or _fallback_summary(stats)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[DevVelocity] AI summary failed: {e}")
        return _fallback_summary(stats)


def _fallback_summary(stats: dict) -> str:
    t = stats.get("totals", {})
    cats = stats.get("categories", {})
    parts = [
        f"**Săptămâna {stats.get('since', '')} — {stats.get('until', '')}**",
        "",
        f"S-au făcut **{t.get('commits', 0)} commit-uri** în {t.get('files_changed', 0)} fișiere "
        f"(+{t.get('lines_added', 0)}/-{t.get('lines_deleted', 0)} linii).",
        "",
        "**Distribuție pe categorii:**",
    ]
    for name, info in sorted(cats.items(), key=lambda x: -x[1]["file_count"]):
        parts.append(f"- {name}: {info['file_count']} fișiere")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------

async def send_weekly_velocity_email(force: bool = False) -> dict:
    """Compose + send weekly velocity report to admins."""
    stats = collect_velocity(days=7)
    if not force and stats["totals"].get("commits", 0) == 0:
        return {"sent": False, "reason": "no_commits_this_week"}

    summary = await ai_summary(stats)

    recipients_raw = os.environ.get("ADMIN_EMAILS", "") or os.environ.get("ADMIN_EMAIL", "")
    recipients = [e.strip() for e in recipients_raw.split(",") if e.strip()]
    if not recipients:
        return {"sent": False, "reason": "no_recipients"}

    # Format HTML
    t = stats["totals"]
    cats = stats["categories"]
    cat_rows = ""
    for name, info in sorted(cats.items(), key=lambda x: -x[1]["file_count"]):
        cat_rows += f"""<tr>
          <td style="padding:8px 12px; border-bottom:1px solid #2a2a30; color:#c8c8cc;">{name}</td>
          <td style="padding:8px 12px; border-bottom:1px solid #2a2a30; color:#d4ff3a; text-align:right; font-family:monospace;">{info['file_count']} fișiere</td>
          <td style="padding:8px 12px; border-bottom:1px solid #2a2a30; color:#888; text-align:right; font-family:monospace;">+{info['added']}/-{info['deleted']}</td>
        </tr>"""

    # Convert summary's **bold** to <b> for HTML email
    summary_html = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", summary).replace("\n", "<br/>")

    from email_service import _layout, send_email

    body_html = f"""
      <p>Bună dimineața,</p>
      <p>Iată raportul săptămânal de dezvoltare PropManage <strong>({stats['since']} → {stats['until']})</strong>:</p>

      <div style="background:#1a1a1f; border-radius:14px; padding:18px; margin:18px 0;">
        <div style="font-size:11px; color:#888893; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">Analiza AI</div>
        <div style="color:#e5e5e5; font-size:14px; line-height:1.7;">{summary_html}</div>
      </div>

      <div style="display:flex; gap:12px; margin:20px 0;">
        <div style="flex:1; background:#1a1a1f; border-radius:12px; padding:14px; text-align:center;">
          <div style="font-size:26px; font-weight:700; color:#d4ff3a;">{t.get('commits', 0)}</div>
          <div style="font-size:10px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">commit-uri</div>
        </div>
        <div style="flex:1; background:#1a1a1f; border-radius:12px; padding:14px; text-align:center;">
          <div style="font-size:26px; font-weight:700; color:#d4ff3a;">{t.get('files_changed', 0)}</div>
          <div style="font-size:10px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">fișiere</div>
        </div>
        <div style="flex:1; background:#1a1a1f; border-radius:12px; padding:14px; text-align:center;">
          <div style="font-size:26px; font-weight:700; color:#7cb342;">+{t.get('lines_added', 0)}</div>
          <div style="font-size:10px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">linii adăugate</div>
        </div>
        <div style="flex:1; background:#1a1a1f; border-radius:12px; padding:14px; text-align:center;">
          <div style="font-size:26px; font-weight:700; color:#ef4444;">-{t.get('lines_deleted', 0)}</div>
          <div style="font-size:10px; color:#888; text-transform:uppercase; letter-spacing:0.5px;">linii șterse</div>
        </div>
      </div>

      <div style="margin:20px 0;">
        <div style="font-size:11px; color:#888893; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:8px;">Distribuție pe categorii</div>
        <table border="0" cellpadding="0" cellspacing="0" style="width:100%; background:#1a1a1f; border-radius:12px; overflow:hidden;">
          {cat_rows}
        </table>
      </div>

      <p style="color:#666; font-size:11px; margin-top:20px;">Raport generat automat luni dimineața. Pentru a-l opri, dezactivează schedulerul "weekly_dev_velocity" din admin.</p>
    """

    html = _layout(
        title="Dev Velocity Weekly",
        preheader=f"{t.get('commits', 0)} commits · {t.get('files_changed', 0)} fișiere",
        body_html=body_html,
    )

    week_label = datetime.now(timezone.utc).strftime("Săpt %V · %d %b %Y")
    subject = f"📊 PropManage Dev Velocity · {week_label}"
    sent = 0
    for r in recipients:
        res = await send_email(r, subject, html)
        if res.get("ok"):
            sent += 1

    # Persist run record
    try:
        await db.dev_velocity_runs.insert_one({
            "week_since": stats["since"],
            "week_until": stats["until"],
            "totals": stats["totals"],
            "categories_summary": {k: v["file_count"] for k, v in stats["categories"].items()},
            "summary": summary,
            "sent_to": sent,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:  # noqa: BLE001
        pass

    return {"sent": sent > 0, "recipients": sent, "total_recipients": len(recipients), "stats": stats["totals"]}


async def run_weekly_velocity_job() -> None:
    """APScheduler entrypoint — never raises."""
    try:
        await send_weekly_velocity_email(force=False)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[DevVelocity][cron] failed: {e}")
