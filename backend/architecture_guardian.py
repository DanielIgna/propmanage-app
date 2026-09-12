"""Architecture Guardian — PM-GUARDIAN-001/002: impune arhitectura canonică permanent.

Scanează static codul real (/app/frontend/src + /app/backend) și detectează:
implementări paralele (V2/New/Old/Legacy), componente moarte, lazy imports nerutate,
rute către componente inexistente, switch-uri temporare pe localStorage, feature flags
abandonate, importuri circulare, API-uri duplicate, TODO-uri acumulate.

Risc REDUS + fix la nivel de date → reparat automat (ex. chei stale în app_settings).
Risc MEDIU/MARE → task CTO în db.architecture_guardian_tasks (upsert pe key, auto-resolve
când problema dispare — același lifecycle ca Journey Guardian). Recurența unei probleme
rezolvate anterior = regresie de clasă → severitate crescută + intrare de learning în ledger.
"""
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from db import db

logger = logging.getLogger("propmanage.architecture_guardian")

FRONTEND_SRC = Path("/app/frontend/src")
BACKEND_DIR = Path("/app/backend")

PARALLEL_SUFFIXES = ("V2", "V3", "V4", "New", "Old", "Legacy", "Copy")
BENIGN_LS_PARTS = (
    "token", "theme", "lang", "i18n", "seen", "dismiss", "cookie", "consent", "banner",
    "tour", "tutorial", "draft", "cache", "ab_", "invite", "checklist", "collapse",
    "recent", "fav", "zone", "scope", "hint", "done", "visitor", "attr", "identity",
    "ref", "vid", "session", "fb", "onboard",
)
SWITCH_HINT = re.compile(r"(ui$|_ui|mode|legacy|variant|switch|full|version)", re.I)
IMPORT_RE = re.compile(r"""(?:from\s+["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\))""")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def _issue(key, severity, risk, title, detail, expected, impact, plan="") -> dict:
    return {"key": key, "severity": severity, "risk": risk, "title": title, "detail": detail,
            "expected": expected, "business_impact": impact, "migration_plan": plan}


def _frontend_files() -> list:
    return [p for p in FRONTEND_SRC.rglob("*") if p.suffix in (".js", ".jsx") and "node_modules" not in p.parts]


def _build_ref_index(files: list) -> dict:
    """basename(fără extensie) → set de fișiere care îl importă (relativ sau alias @/)."""
    refs: dict = {}
    for f in files:
        for m in IMPORT_RE.finditer(_read(f)):
            spec = m.group(1) or m.group(2) or ""
            if not (spec.startswith(".") or spec.startswith("@/")):
                continue
            base = re.sub(r"\.(jsx?|tsx?)$", "", spec.split("/")[-1])
            if base:
                refs.setdefault(base, set()).add(str(f))
    return refs


# ============================================================================
# CHECKS
# ============================================================================
def check_parallel_naming(files, issues):
    names = {p.stem: p for p in files if p.suffix == ".jsx"}
    for stem, p in names.items():
        for suf in PARALLEL_SUFFIXES:
            if stem.endswith(suf) and len(stem) > len(suf) and stem[:-len(suf)] in names:
                base = stem[:-len(suf)]
                issues.append(_issue(
                    f"parallel_impl:{base}", "high", "medium",
                    f"Implementare paralelă: {base} + {stem}",
                    f"Există '{names[base].relative_to(FRONTEND_SRC)}' ȘI '{p.relative_to(FRONTEND_SRC)}' — două implementări pentru același concept.",
                    "O singură implementare canonică per funcționalitate.",
                    "Preview ≠ Live, funcționalități care 'dispar' după deploy, mentenanță dublă.",
                    f"Alege canonicul, mută rutele/importurile către el, șterge '{base if len(_read(names[base])) < len(_read(p)) else stem}'."))


def check_dead_components(files, refs, issues):
    protected = {"App", "index", "setupTests", "reportWebVitals", "auth", "i18n", "ab"}
    for p in files:
        rel = p.relative_to(FRONTEND_SRC)
        parts = rel.parts
        if parts[0] not in ("pages", "components") or "ui" in parts or p.suffix != ".jsx":
            continue
        if p.stem in protected:
            continue
        if not (refs.get(p.stem, set()) - {str(p)}):
            issues.append(_issue(
                f"dead_component:{rel}", "medium", "low",
                f"Componentă moartă: {p.stem}",
                f"'{rel}' nu e importată de niciun alt fișier (nici static, nici lazy).",
                "Zero fișiere neimportate în pages/ și components/.",
                "Cod fantomă — pare implementat dar nu rulează nicăieri; derutează dezvoltarea.",
                f"Șterge fișierul '{rel}' (verifică întâi git log pentru context)."))


def check_app_routes(files, issues):
    app = _read(FRONTEND_SRC / "App.js")
    lazy_names = re.findall(r"const\s+(\w+)\s*=\s*lazy\(", app)
    defined = set(lazy_names)
    defined |= set(re.findall(r"(?:const|function)\s+(\w+)\s*[=(]", app))
    for m in re.finditer(r"import\s+\{([^}]+)\}\s+from", app):
        defined |= {n.strip().split(" as ")[-1] for n in m.group(1).split(",") if n.strip()}
    defined |= set(re.findall(r"import\s+(\w+)\s*(?:,|\s+from)", app))

    for n in lazy_names:
        if f"<{n}" not in app:
            issues.append(_issue(
                f"unrouted_lazy:{n}", "medium", "low",
                f"Import lazy nerutat: {n}",
                f"App.js declară lazy '{n}' dar nu-l randează în nicio rută.",
                "Fiecare lazy import din App.js e folosit într-o rută.",
                "Bundle chunk generat degeaba + semnal de implementare abandonată.",
                f"Șterge declarația lazy '{n}' din App.js sau ruteaz-o."))
    for n in set(re.findall(r"element=\{<(\w+)", app)):
        if n not in defined and n not in ("Navigate", "Suspense"):
            issues.append(_issue(
                f"dead_route:{n}", "critical", "medium",
                f"Rută cu componentă nedefinită: {n}",
                f"App.js rutează <{n}> dar componenta nu e importată/definită.",
                "Fiecare rută încarcă o componentă existentă.",
                "Pagina crapă la runtime — user lovește ecran alb.", ""))


def check_temp_switches(files, issues):
    for p in files:
        parts = p.relative_to(FRONTEND_SRC).parts
        if parts[0] not in ("pages", "components"):
            continue
        for m in re.finditer(r"localStorage\.getItem\(\s*[\"']([\w\-.]+)[\"']\s*\)", _read(p)):
            key = m.group(1)
            if any(b in key.lower() for b in BENIGN_LS_PARTS):
                continue
            if SWITCH_HINT.search(key):
                issues.append(_issue(
                    f"temp_switch:{key}", "medium", "medium",
                    f"Switch temporar pe localStorage: '{key}'",
                    f"'{p.relative_to(FRONTEND_SRC)}' schimbă comportamentul pe baza localStorage('{key}') — starea diferă per browser.",
                    "Comportamentul e controlat de backend (tier/permisiuni/feature flags), nu de localStorage.",
                    "Clasa de bug Preview ≠ Live: doi utilizatori văd ecrane diferite pe același deploy.",
                    f"Mută decizia în backend sau elimină switch-ul; curăță cheia '{key}'."))


def check_feature_flags(issues):
    model = _read(BACKEND_DIR / "routes" / "app_settings.py")
    flags = re.findall(r"^\s{4}(enable_\w+)\s*:", model, re.M)
    if not flags:
        return
    hay = []
    for p in list(BACKEND_DIR.rglob("*.py")) + _frontend_files():
        if "tests" in p.parts or p.name == "app_settings.py":
            continue
        hay.append(_read(p))
    blob = "\n".join(hay)
    for flag in flags:
        if flag not in blob:
            issues.append(_issue(
                f"abandoned_flag:{flag}", "medium", "low",
                f"Feature flag abandonat: {flag}",
                f"'{flag}' e definit în modelul app_settings dar nu e citit nicăieri în cod.",
                "Fiecare feature flag definit are cel puțin un consumator.",
                "Config mort care sugerează funcționalitate inexistentă.",
                f"Șterge câmpul '{flag}' din SiteSettings (routes/app_settings.py)."))


def check_circular_imports(files, issues):
    def resolve(spec: str, src: Path):
        base = (FRONTEND_SRC / spec[2:]) if spec.startswith("@/") else (src.parent / spec)
        for suffix in ("", ".js", ".jsx"):
            cand = Path(str(base) + suffix)
            if cand.is_file():
                return cand.resolve()
        return None

    edges: dict = {}
    for f in files:
        for m in IMPORT_RE.finditer(_read(f)):
            spec = m.group(1) or m.group(2) or ""
            if spec.startswith(".") or spec.startswith("@/"):
                t = resolve(spec, f)
                if t:
                    edges.setdefault(f.resolve(), set()).add(t)
    reported = set()
    for a, targets in edges.items():
        for b in targets:
            if a in edges.get(b, set()):
                pair = tuple(sorted([str(a), str(b)]))
                if pair in reported:
                    continue
                reported.add(pair)
                ra, rb = Path(pair[0]).name, Path(pair[1]).name
                issues.append(_issue(
                    f"circular_import:{ra}<->{rb}", "high", "medium",
                    f"Import circular: {ra} ↔ {rb}",
                    f"'{pair[0]}' și '{pair[1]}' se importă reciproc.",
                    "Graf de importuri aciclic.",
                    "Bundle-uri fragile, ordinea de inițializare nedeterministă, bug-uri greu de reprodus.",
                    "Extrage partea comună într-un modul separat importat de ambele."))


def check_duplicate_api(issues):
    seen: dict = {}
    for p in (BACKEND_DIR / "routes").glob("*.py"):
        text = _read(p)
        prefixes = dict(re.findall(r"(\w+)\s*=\s*APIRouter\([^)]*prefix\s*=\s*[\"']([^\"']+)[\"']", text))
        for m in re.finditer(r"@(\w+)\.(get|post|put|patch|delete)\(\s*[\"']([^\"']+)[\"']", text):
            var, meth, path = m.groups()
            full = f"{meth.upper()} {prefixes.get(var, '')}{path}"
            seen.setdefault(full, []).append(p.name)
    for full, sources in seen.items():
        if len(sources) > 1:
            issues.append(_issue(
                f"duplicate_api:{full}", "high", "medium",
                f"Endpoint duplicat: {full}",
                f"Definit de {len(sources)} ori în: {', '.join(sorted(set(sources)))}. FastAPI servește doar primul înregistrat — restul sunt cod mort înșelător.",
                "Un singur handler per (metodă, cale).",
                "Modifici handler-ul greșit și 'fix-ul' nu apare niciodată în producție.",
                "Păstrează un singur handler; șterge sau redenumește-le pe celelalte."))


def check_stale_todos(issues):
    count = 0
    for p in _frontend_files() + [q for q in BACKEND_DIR.rglob("*.py") if "tests" not in q.parts]:
        count += len(re.findall(r"\b(TODO|FIXME)\b", _read(p)))
    if count > 60:
        issues.append(_issue(
            "stale_todos", "low", "low",
            f"{count} TODO/FIXME acumulate în cod",
            f"Numărul de markere TODO/FIXME ({count}) a depășit pragul de 60.",
            "Sub 60 de markere — restul devin task-uri sau se șterg.",
            "Datorie ascunsă care nu apare în niciun backlog.",
            "Triage: transformă în task-uri reale sau șterge markerele obsolete."))


# ============================================================================
# AUTO-REPAIR (doar risc REDUS, la nivel de date)
# ============================================================================
async def _autofix_stale_settings_keys() -> list:
    actions = []
    model = _read(BACKEND_DIR / "routes" / "app_settings.py")
    defined = set(re.findall(r"^\s{4}(enable_\w+)\s*:", model, re.M))
    doc = await db.app_settings.find_one({"_id": "app_settings"}) or {}
    stale = [k for k in doc if k.startswith("enable_") and k not in defined]
    if stale:
        await db.app_settings.update_one({"_id": "app_settings"}, {"$unset": {k: "" for k in stale}})
        actions.append({"action": "unset_stale_settings_keys", "ok": True,
                        "detail": f"Chei orfane eliminate din app_settings (flag-uri care nu mai există în model): {stale}"})
    return actions


# ============================================================================
# RUN
# ============================================================================
async def run_architecture_guardian(trigger: str = "cron") -> dict:
    files = _frontend_files()
    refs = _build_ref_index(files)
    issues: list = []
    for check in (lambda i: check_parallel_naming(files, i),
                  lambda i: check_dead_components(files, refs, i),
                  lambda i: check_app_routes(files, i),
                  lambda i: check_temp_switches(files, i),
                  lambda i: check_circular_imports(files, i)):
        try:
            check(issues)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[arch-guardian] check failed: {e}")
    for acheck in (check_feature_flags, check_duplicate_api, check_stale_todos):
        try:
            acheck(issues)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[arch-guardian] check {acheck.__name__} failed: {e}")

    ignores = {d["key"] async for d in db.architecture_guardian_ignores.find({}, {"key": 1})}
    issues = [i for i in issues if i["key"] not in ignores]

    auto_actions = []
    try:
        auto_actions = await _autofix_stale_settings_keys()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[arch-guardian] autofix failed: {e}")

    now = _now()
    seen_keys, new_tasks, regressions = set(), 0, 0
    for iss in issues:
        seen_keys.add(iss["key"])
        existing = await db.architecture_guardian_tasks.find_one({"key": iss["key"], "status": "open"})
        if existing:
            await db.architecture_guardian_tasks.update_one(
                {"_id": existing["_id"]}, {"$set": {"last_seen_at": now, "detail": iss["detail"]}})
            continue
        prev = await db.architecture_guardian_tasks.find_one(
            {"key": iss["key"], "status": "resolved"}, sort=[("resolved_at", -1)])
        recurrence = (prev.get("recurrence", 0) + 1) if prev else 0
        if recurrence:
            regressions += 1
            iss["severity"] = "critical" if iss["severity"] in ("high", "critical") else "high"
        await db.architecture_guardian_tasks.insert_one({
            "id": uuid.uuid4().hex, **iss, "status": "open", "assigned_to": "cto_ai",
            "recurrence": recurrence, "created_at": now, "last_seen_at": now, "trigger": trigger,
        })
        new_tasks += 1

    res = await db.architecture_guardian_tasks.update_many(
        {"status": "open", "key": {"$nin": list(seen_keys) or ["__none__"]}},
        {"$set": {"status": "resolved", "resolved_at": now, "resolved_by": "architecture_guardian"}})
    auto_resolved = res.modified_count

    by_sev = {s: sum(1 for i in issues if i["severity"] == s) for s in ("critical", "high", "medium", "low")}
    score = max(5, 100 - 15 * by_sev["critical"] - 8 * by_sev["high"] - 3 * by_sev["medium"] - 1 * by_sev["low"])
    run = {
        "id": uuid.uuid4().hex, "ts": now, "trigger": trigger,
        "files_scanned": len(files), "issues_found": len(issues), "new_tasks": new_tasks,
        "auto_resolved": auto_resolved, "auto_repairs": auto_actions, "regressions": regressions,
        "by_severity": by_sev, "architecture_score": score,
    }
    await db.architecture_guardian_runs.insert_one({**run})

    from orchestrator.engine import write_ledger, notify_admins
    from orchestrator.governance import record_decision
    await write_ledger({
        "signal_kind": "architecture_guardian", "playbook_id": "architecture_guardian",
        "playbook_name": "Architecture Guardian",
        "steps": [{"action": "audit_architecture", "ok": by_sev["critical"] == 0,
                   "detail": f"{len(files)} fișiere scanate, {len(issues)} probleme ({by_sev}), scor arhitectură {score}/100, "
                             f"{new_tasks} task-uri noi CTO, {auto_resolved} auto-rezolvate, {len(auto_actions)} reparații automate"
                             + (f", {regressions} REGRESII de clasă (learning)" if regressions else "")}],
        "outcome": "auto_resolved" if by_sev["critical"] == 0 else "escalated",
        "minutes_saved": 10 + 3 * auto_resolved + 5 * len(auto_actions),
        "escalated": by_sev["critical"] > 0, "test": False,
    })
    await record_decision({
        "signal_kind": "architecture_guardian", "playbook_id": "architecture_guardian",
        "playbook_name": "Architecture Guardian", "authority_level": 4,
        "execution_mode": "execute", "confidence": 0.9, "decided": "executed",
        "outcome": "auto_resolved" if by_sev["critical"] == 0 else "escalated",
        "escalated": by_sev["critical"] > 0,
        "context": {"issues": len(issues), "score": score, "new_tasks": new_tasks}, "test": False,
    })
    if regressions:
        await write_ledger({
            "signal_kind": "learning", "playbook_id": "architecture_guardian",
            "playbook_name": "Learning Engine",
            "steps": [{"action": "class_regression_detected", "ok": False,
                       "detail": f"{regressions} probleme de arhitectură rezolvate anterior au REAPĂRUT — severitate crescută automat."}],
            "outcome": "escalated", "minutes_saved": 0, "escalated": True, "test": False,
        })
    if by_sev["critical"] > 0 and new_tasks:
        crit = [i["title"] for i in issues if i["severity"] == "critical"][:3]
        await notify_admins("🚨 Architecture Guardian: probleme critice de arhitectură",
                            "; ".join(crit), link="/admin/repair-center")
    logger.info(f"[arch-guardian] run done: score={score}, issues={len(issues)}, new={new_tasks}, resolved={auto_resolved}")
    run.pop("_id", None)
    return run
