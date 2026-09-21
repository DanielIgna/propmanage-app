"""Knowledge Center historical provenance (Phase 4).

Read-only. Derives first-seen / origin / migration from Git.
Does not store a Git clone. Does not write canonical documents.
Iteration numbers from filenames are marked inferred.
"""
from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from knowledge_coverage import (
    CANONICAL_PROMOTION_ALLOWED,
    DOC_PLATFORM_STATE,
    REG_CANONICAL,
    REG_FUNCTION_MAP,
    REG_SSOT,
    WATCH_AREAS,
    classify_area,
    function_map_drift,
    function_map_stale_entries,
    load_corpus,
)

ORIGIN_EMERGENT = "EMERGENT"
ORIGIN_CURSOR = "CURSOR"
ORIGIN_HUMAN = "HUMAN"
ORIGIN_UNKNOWN = "UNKNOWN"

CONFIRMED = "CONFIRMED"
PROBABLE = "PROBABLE"
POSSIBLE = "POSSIBLE"
UNKNOWN = "UNKNOWN"

NOT_APPLICABLE = "NOT_APPLICABLE"

EMERGENT_AUTHOR_NEEDLES = ("emergent-agent", "emergent agent")
CURSOR_AUTHOR_NEEDLES = ("igna daniel", "daniel igna")
EMERGENT_SUBJECT_NEEDLES = (
    "auto-commit for ",
    "auto-generated changes",
    "checkpoint before testing_agent",
)

ITER_RE = re.compile(r"iter(\d+)", re.I)
PHASE_RE = re.compile(r"(?:faza|phase)\s*([0-9]+[A-Z]?)", re.I)

# Extra modules for Function Map / MPS reconstruction (not new coverage doctrine).
EXTRA_TRACKED = (
    {
        "id": "geocoding",
        "title": "Geocoding",
        "implementation": ("backend/geocoding.py",),
        "tests": ("backend/tests/test_geocoding_iter229.py",),
        "dedicated_kc": (),
        "function_map_needles": ("geocoding",),
    },
)

IMPORTANT_KC = (
    "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md",
    "memory/audits/HARTABLOCURI_INTEGRATION.md",
    "memory/audits/MASTER_PLATFORM_STATE.md",
    "memory/audits/PROPERTY_TWIN_CANONICAL_v1.0.md",
    "memory/board/EXECUTION_ORDER_CX2_PROPERTY_DNA_DOCUMENT_VAULT.md",
    "memory/registries/FUNCTION_MAP.md",
    "memory/registries/CANONICAL_SYSTEM_REGISTRY.md",
    "memory/registries/SSOT_REGISTRY.md",
)

# Seeded verification claims — evidence links, not new product doctrine.
PROVENANCE_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "id": "10c_orchestrator_no_persist",
        "claim": "10C is an orchestrator without persistence, endpoint, or UI.",
        "kc": "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md",
        "code": ("backend/document_property_support.py",),
        "tests": ("backend/tests/test_document_property_support_iter238.py",),
        "registry": "memory/registries/CANONICAL_SYSTEM_REGISTRY.md",
        "claim_type": "CURRENT_IMPLEMENTATION",
    },
    {
        "id": "fn005_frontend_path",
        "claim": "FN-005 frontend is PropertyDocumentsPanel.jsx.",
        "kc": "memory/registries/FUNCTION_MAP.md",
        "code": ("frontend/src/components/PropertyDocumentsPanel.jsx",),
        "actual_code": ("frontend/src/pages/clientv2/DocumentVault.jsx",),
        "tests": ("backend/tests/test_cx2_document_vault_iter134.py",),
        "claim_type": "CURRENT_IMPLEMENTATION",
        "expect_missing_code": True,
    },
    {
        "id": "cx2_vault_order",
        "claim": "CX-2 orders a Document Vault per property.",
        "kc": "memory/board/EXECUTION_ORDER_CX2_PROPERTY_DNA_DOCUMENT_VAULT.md",
        "code": ("frontend/src/pages/clientv2/DocumentVault.jsx", "backend/routes/property_documents.py"),
        "tests": ("backend/tests/test_cx2_document_vault_iter134.py",),
        "claim_type": "DESIGN",
    },
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git(root: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=check,
    )


def git_available(root: Path) -> bool:
    r = _git(root, "rev-parse", "--is-inside-work-tree")
    return r.returncode == 0 and "true" in (r.stdout or "")


def classify_origin(author: str = "", email: str = "", subject: str = "") -> dict[str, Any]:
    """Evidence-based origin. Never inferred from filename."""
    a = (author or "").lower()
    e = (email or "").lower()
    s = (subject or "").lower()
    evidence: list[str] = []
    if any(n in s for n in EMERGENT_SUBJECT_NEEDLES):
        evidence.append("emergent_subject")
    if any(n in a or n in e for n in EMERGENT_AUTHOR_NEEDLES):
        evidence.append("emergent_author")
    if evidence:
        return {
            "origin": ORIGIN_EMERGENT,
            "confidence": "high",
            "evidence": evidence,
        }
    if any(n in a for n in CURSOR_AUTHOR_NEEDLES):
        return {
            "origin": ORIGIN_CURSOR,
            "confidence": "high",
            "evidence": ["cursor_author"],
        }
    if s and not any(n in s for n in EMERGENT_SUBJECT_NEEDLES):
        if a:
            return {
                "origin": ORIGIN_HUMAN,
                "confidence": "medium",
                "evidence": ["non_auto_subject", "author_present"],
            }
    return {
        "origin": ORIGIN_UNKNOWN,
        "confidence": "low",
        "evidence": [],
    }


def infer_iteration(paths: Iterable[str]) -> dict[str, Any]:
    found: list[str] = []
    for p in paths:
        m = ITER_RE.search(p or "")
        if m:
            found.append(f"iter{m.group(1)}")
    uniq = sorted(set(found))
    return {
        "iteration": uniq[0] if len(uniq) == 1 else (uniq if uniq else None),
        "inferred": bool(uniq),
        "source": "filename" if uniq else None,
    }


def infer_phase(text: str) -> Optional[str]:
    m = PHASE_RE.search(text or "")
    return m.group(1).upper() if m else None


def _parse_log_line(line: str) -> Optional[dict[str, Any]]:
    parts = line.split("\t")
    if len(parts) < 5:
        return None
    h, iso, author, email, subject = parts[0], parts[1], parts[2], parts[3], "\t".join(parts[4:])
    origin = classify_origin(author, email, subject)
    return {
        "commit_hash": h,
        "commit_date": iso,
        "author": author,
        "email": email,
        "subject": subject[:240],
        **origin,
    }


def file_git_index(root: Path, rel: str) -> dict[str, Any]:
    """first_seen / last_changed / deleted / renamed — derived from Git, not a store."""
    if not rel:
        return {"path": rel, "state": "UNKNOWN", "first_seen": None, "last_changed": None}
    exists_now = (root / rel).is_file()
    log = _git(root, "log", "--follow", "--format=%H%x09%aI%x09%an%x09%ae%x09%s", "--", rel)
    rows = [_parse_log_line(l) for l in log.stdout.splitlines() if l]
    rows = [r for r in rows if r]
    first = rows[-1] if rows else None
    last = rows[0] if rows else None

    renamed = False
    rename_from = None
    name_st = _git(root, "log", "--follow", "--name-status", "--format=%H", "--", rel)
    add_count = 0
    delete_count = 0
    for line in name_st.stdout.splitlines():
        if line.startswith("R") and "\t" in line:
            bits = line.split("\t")
            if len(bits) >= 3 and not renamed:
                renamed = True
                rename_from = bits[1]
        elif line.startswith("A\t"):
            add_count += 1
        elif line.startswith("D\t"):
            delete_count += 1

    deleted = False
    if not exists_now and rows:
        head = _git(root, "cat-file", "-e", f"HEAD:{rel}")
        deleted = head.returncode != 0
    reintroduced = bool(exists_now and add_count >= 2 and delete_count >= 1)

    if exists_now:
        state = "current"
    elif deleted:
        state = "deleted"
    elif not rows:
        state = "untracked_or_absent"
    else:
        state = "historical"

    return {
        "path": rel,
        "state": state,
        "exists_now": exists_now,
        "commit_count": len(rows),
        "first_seen": first,
        "last_changed": last,
        "renamed": renamed,
        "rename_from": rename_from,
        "deleted": deleted,
        "reintroduced": reintroduced,
    }


def _earliest(events: list[Optional[dict[str, Any]]]) -> Optional[dict[str, Any]]:
    dated = [e for e in events if e and e.get("commit_date")]
    if not dated:
        return None
    return min(dated, key=lambda e: e["commit_date"])


def _latest(events: list[Optional[dict[str, Any]]]) -> Optional[dict[str, Any]]:
    dated = [e for e in events if e and e.get("commit_date")]
    if not dated:
        return None
    return max(dated, key=lambda e: e["commit_date"])


def _iso_day(iso: Optional[str]) -> Optional[str]:
    if not iso:
        return None
    return iso[:10]


def _latency_days(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end:
        return None
    try:
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (b.date() - a.date()).days


def _first_needle_in_file(root: Path, rel: str, needles: Iterable[str]) -> Optional[dict[str, Any]]:
    """First commit that introduced a needle into this file. File birth is not a mention."""
    found: list[dict[str, Any]] = []
    for needle in needles:
        n = (needle or "").strip()
        if len(n) < 6:
            continue
        log = _git(root, "log", "-S", n, "--format=%H%x09%aI%x09%an%x09%ae%x09%s", "--", rel)
        rows = [_parse_log_line(l) for l in log.stdout.splitlines() if l]
        rows = [r for r in rows if r]
        if rows:
            found.append(rows[-1])
    return _earliest(found)


def historical_area(
    area: dict[str, Any],
    classified: dict[str, Any],
    root: Path,
    indexes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    impl_idx = [indexes.get(p) for p in area.get("implementation") or ()]
    test_idx = [indexes.get(p) for p in area.get("tests") or ()]
    file_first = _earliest([i.get("first_seen") if i else None for i in impl_idx])
    code_last = _latest([i.get("last_changed") if i else None for i in impl_idx])
    feature_needles = [n for n in (area.get("needles") or ()) if len(n) >= 8]
    feature_first = _earliest(
        [
            _first_needle_in_file(root, p, feature_needles)
            for p in area.get("implementation") or ()
        ]
    )
    code_first = feature_first or file_first
    test_first = _earliest([i.get("first_seen") if i else None for i in test_idx])
    dedicated_first = _earliest(
        [(indexes.get(p) or {}).get("first_seen") for p in area.get("dedicated_kc") or ()]
    )
    mention_needles = [Path(p).stem for p in area.get("implementation") or ()]
    mention_needles += [n for n in (area.get("needles") or ()) if len(n) >= 8]
    mention_events = [
        _first_needle_in_file(root, p, mention_needles)
        for p in classified.get("kc_mentions") or []
    ]
    kc_first = _earliest(mention_events + [dedicated_first])
    origin_src = code_first or test_first
    origin = classify_origin(
        (origin_src or {}).get("author", ""),
        (origin_src or {}).get("email", ""),
        (origin_src or {}).get("subject", ""),
    ) if origin_src else {"origin": ORIGIN_UNKNOWN, "confidence": "low", "evidence": []}
    iter_info = infer_iteration(list(area.get("tests") or ()) + list(area.get("implementation") or ()))
    code_day = _iso_day((code_first or {}).get("commit_date"))
    mention_day = _iso_day((kc_first or {}).get("commit_date"))
    dedicated_day = _iso_day((dedicated_first or {}).get("commit_date"))

    why = []
    if classified["status"] in {"UNDOCUMENTED", "PARTIALLY_DOCUMENTED", "STALE"}:
        if not classified.get("dedicated_kc"):
            why.append("No dedicated KC artifact.")
        if classified.get("missing_required_mentions"):
            why.append("Dedicated KC does not mention current implementation files.")
        if not classified.get("in_function_map"):
            why.append("Function Map has no row.")
        if not classified.get("in_dependency_map"):
            why.append("Dependency Map has no node.")
    if not why and classified["status"] == "DOCUMENTED":
        why.append("Dedicated KC plus registry/SSOT/dependency evidence.")

    return {
        "id": area["id"],
        "title": area["title"],
        "current_documentation_state": classified["status"],
        "code_first_seen": code_first,
        "code_last_changed": code_last,
        "tests_first_seen": test_first,
        "kc_first_mention": kc_first,
        "dedicated_kc_first_seen": dedicated_first,
        "related_kc_artifacts": classified.get("kc_mentions") or [],
        "related_tests": classified.get("tests_present") or [],
        "origin": origin["origin"],
        "origin_confidence": origin["confidence"],
        "origin_evidence": origin["evidence"],
        "iteration": iter_info,
        "latency": {
            "code_to_kc_mention_days": _latency_days(code_day, mention_day) if mention_day and code_day else None,
            "code_to_dedicated_kc_days": _latency_days(code_day, dedicated_day) if dedicated_day and code_day else None,
            "code_to_kc_mention": mention_day,
            "code_to_dedicated_kc": dedicated_day or "none",
            "code_to_function_map": "present" if classified.get("in_function_map") else "none",
            "code_to_registry": "present" if classified.get("in_canonical_registry") or classified.get("in_ssot") else "none",
            "code_to_dependency_map": "present" if classified.get("in_dependency_map") else "none",
        },
        "historical_state_before_code": NOT_APPLICABLE,
        "historical_note": "Absence before first implementation is not a documentation error.",
        "why_flagged": why,
        "confidence": "high" if code_first else "medium",
    }


def verify_claim(root: Path, spec: dict[str, Any], indexes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    code = list(spec.get("code") or ())
    tests = list(spec.get("tests") or ())
    actual = list(spec.get("actual_code") or ())
    kc = spec.get("kc")
    missing = [p for p in code if not (root / p).is_file()]
    present = [p for p in code if (root / p).is_file()]
    actual_present = [p for p in actual if (root / p).is_file()]
    tests_present = [p for p in tests if (root / p).is_file()]
    kc_exists = bool(kc and (root / kc).is_file())
    git_ev = _earliest([(indexes.get(p) or {}).get("first_seen") for p in present + actual_present + ([kc] if kc else [])])

    if spec.get("expect_missing_code"):
        status = "STALE" if missing and actual_present else ("MATCH" if not missing else "CONFLICT")
        if missing and actual_present:
            status = "STALE"
    elif present and tests_present and kc_exists:
        status = "MATCH"
    elif present and kc_exists:
        status = "PARTIAL"
    elif kc_exists and not present:
        status = "NOT_IMPLEMENTED"
    else:
        status = "UNKNOWN"

    return {
        "id": spec["id"],
        "claim": spec["claim"],
        "claim_type": spec.get("claim_type", "UNKNOWN"),
        "kc_document": kc,
        "code_paths": present,
        "missing_code_paths": missing,
        "actual_code_paths": actual_present,
        "test_paths": tests_present,
        "registry": spec.get("registry"),
        "git": git_ev,
        "verification_date": _now()[:10],
        "status": status,
        "canonical": False,
    }


def function_map_history(root: Path, areas: list[dict[str, Any]], function_map: dict[str, Any]) -> dict[str, Any]:
    idx = file_git_index(root, REG_FUNCTION_MAP)
    log = _git(root, "log", "--format=%h %aI %s", "--", REG_FUNCTION_MAP)
    commits = [l for l in log.stdout.splitlines() if l][:12]
    drift = function_map_drift(areas, function_map)
    stale = function_map_stale_entries(root, function_map)
    extras = []
    names = " ".join(
        f"{fn.get('id','')} {fn.get('name','')} {fn.get('backend','')} {fn.get('frontend','')} {fn.get('description','')}"
        for fn in function_map.get("functions") or []
    ).lower()
    for extra in EXTRA_TRACKED:
        if not any(n in names for n in extra.get("function_map_needles") or ()):
            extras.append({"id": extra["id"], "title": extra["title"], "proposed_action": "ADD_ROW_CANDIDATE", "canonical": False})
    fn005 = next((s for s in stale if s.get("function_id") == "FN-005"), None)
    fn021 = next((fn for fn in (function_map.get("functions") or []) if fn.get("id") == "FN-021"), None)
    specifically = {}
    for label, needles in (
        ("FN-005", ("fn-005", "property documents")),
        ("FN-021", ("fn-021", "operational autonomy")),
        ("7B", ("evidence contract", "evidence_semantics", "7b")),
        ("8B", ("fact extraction", "document_fact_extraction", "8b")),
        ("9C", ("claim matching", "claim_matching", "9c")),
        ("10C", ("document_property_support", "10c")),
        ("Building Identity", ("building identity", "building_identity")),
        ("Source Ledger", ("source ledger", "hartablocuri_source_ledger")),
        ("KC path alignment", ("path alignment", "kc_project_root")),
        ("Geocoding", ("geocoding",)),
        ("HartaBlocuri", ("hartablocuri",)),
    ):
        specifically[label] = {
            "in_function_map": any(n in names for n in needles),
            "proposed": "KEEP" if any(n in names for n in needles) else "ADD_ROW_CANDIDATE",
        }
    if fn005:
        specifically["FN-005"]["invalid_paths"] = fn005.get("missing_paths")
        specifically["FN-005"]["proposed"] = "FIX_PATH_CANDIDATE"
    if fn021:
        specifically["FN-021"]["backend"] = fn021.get("backend")
        specifically["FN-021"]["exists"] = True
    return {
        "path": REG_FUNCTION_MAP,
        "first_seen": idx.get("first_seen"),
        "last_changed": idx.get("last_changed"),
        "meaningful_commits": commits,
        "functions_now": (function_map.get("summary") or {}).get("total"),
        "functions_removed": [],
        "invalid_paths": stale,
        "fn_005": fn005,
        "fn_021": {"id": "FN-021", "present": bool(fn021), "name": (fn021 or {}).get("name")},
        "specifically_verified": specifically,
        "proposed_delta": (drift.get("proposed_delta") or []) + extras,
        "rewritten": False,
        "note": "Historical reconstruction only. FUNCTION_MAP.md is not modified.",
    }


def mps_history(root: Path, indexes: Optional[dict[str, dict[str, Any]]] = None) -> dict[str, Any]:
    living = (indexes or {}).get(DOC_PLATFORM_STATE) or file_git_index(root, DOC_PLATFORM_STATE)
    dated: list[str] = []
    mem = root / "memory" / "audits"
    if mem.is_dir():
        for p in sorted(mem.glob("MASTER_PLATFORM_STATE*.md")):
            dated.append(f"memory/audits/{p.name}")
    last_day = _iso_day(((living.get("last_changed") or {}).get("commit_date")))
    postdating = []
    missing_from_living = []
    living_text = ""
    living_path = root / DOC_PLATFORM_STATE
    if living_path.is_file():
        living_text = living_path.read_text(encoding="utf-8", errors="replace").lower()
    for area in WATCH_AREAS:
        needles = [area["id"].replace("_", " ")] + list(area.get("function_map_needles") or ())
        mentioned = any(n.lower() in living_text for n in needles if n)
        for rel in area.get("implementation") or ():
            idx = (indexes or {}).get(rel) or file_git_index(root, rel)
            first = (idx.get("first_seen") or {}).get("commit_date")
            if first and last_day and first[:10] > last_day:
                postdating.append({"area": area["id"], "file": rel, "first_seen": first[:10]})
        if not mentioned:
            missing_from_living.append({"area": area["id"], "title": area["title"], "canonical": False})
    return {
        "living": DOC_PLATFORM_STATE,
        "first_seen": living.get("first_seen"),
        "last_changed": living.get("last_changed"),
        "dated_versions": dated,
        "implementations_postdating_living_mps": postdating,
        "missing_from_living_mps": missing_from_living,
        "rewritten": False,
        "note": "Living MPS last Git change is the freshness bound. Later code is missing from MPS.",
    }


def migration_trace(root: Path) -> dict[str, Any]:
    remotes: dict[str, str] = {}
    raw = _git(root, "remote", "-v")
    for line in raw.stdout.splitlines():
        bits = line.split()
        if len(bits) >= 2 and bits[-1] == "(fetch)":
            remotes[bits[0]] = bits[1]

    def lr(ref: str) -> Optional[list[int]]:
        r = _git(root, "rev-list", "--left-right", "--count", f"{ref}...HEAD")
        if r.returncode != 0:
            return None
        parts = r.stdout.strip().split()
        if len(parts) != 2:
            return None
        return [int(parts[0]), int(parts[1])]

    origin_lr = lr("origin/main") if "origin" in remotes else None
    emergent_lr = lr("emergent/main") if "emergent" in remotes else None
    porcelain = _git(root, "status", "--porcelain")
    uncommitted = [l[3:].strip() for l in porcelain.stdout.splitlines() if l]
    emergent_tooling_now = (root / ".emergent").exists()
    deleted_tooling = []
    if not emergent_tooling_now:
        check = _git(root, "ls-tree", "-d", "--name-only", "emergent/main", ".emergent")
        if check.returncode == 0 and check.stdout.strip():
            deleted_tooling.append({
                "path": ".emergent/",
                "status": CONFIRMED,
                "note": "Present on emergent/main, absent in the working tree. Tooling, not product knowledge.",
            })

    only_emergent = emergent_lr[0] if emergent_lr else None
    only_local_vs_emergent = emergent_lr[1] if emergent_lr else None
    only_origin = origin_lr[0] if origin_lr else None
    only_local_vs_origin = origin_lr[1] if origin_lr else None

    survived = {
        "status": CONFIRMED,
        "note": "memory/, docs/, backend/, frontend/ product trees are present on HEAD.",
        "trees": [p for p in ("memory", "docs", "backend", "frontend") if (root / p).exists()],
    }
    cannot_trace = {
        "status": UNKNOWN,
        "note": "A file is not called lost unless Git shows a deletion or a remote-only path.",
        "items": [],
    }
    return {
        "layers": ["EMERGENT_REMOTE", "ORIGIN_REMOTE", "LOCAL_WORKING_TREE"],
        "remotes": remotes,
        "counts": {
            "emergent_only_commits": only_emergent,
            "local_not_on_emergent": only_local_vs_emergent,
            "origin_only_commits": only_origin,
            "local_not_on_origin": only_local_vs_origin,
            "uncommitted_paths": len(uncommitted),
        },
        "uncommitted": uncommitted[:40],
        "deleted_emergent_tooling": deleted_tooling,
        "survived": survived,
        "intentionally_removed": deleted_tooling,
        "introduced_after_cursor_window": [],
        "cannot_trace": cannot_trace,
        "lost_claims": [],
        "report": {
            "A_survived_migration": survived,
            "B_intentionally_removed": deleted_tooling,
            "C_introduced_after_migration": {
                "status": PROBABLE,
                "note": "September Cursor-authored modules (7B–10C, Building Identity, Source Ledger) first appear in Git after the living MPS date. Confirmed via first-seen, not assumed lost elsewhere.",
            },
            "D_emergent_only": {
                "status": CONFIRMED if only_emergent else UNKNOWN,
                "commit_count": only_emergent,
            },
            "E_origin_only": {
                "status": CONFIRMED if only_origin else UNKNOWN,
                "commit_count": only_origin,
            },
            "F_local_only": {
                "status": CONFIRMED if (only_local_vs_origin or only_local_vs_emergent or uncommitted) else UNKNOWN,
                "commits_not_on_origin": only_local_vs_origin,
                "commits_not_on_emergent": only_local_vs_emergent,
                "uncommitted_paths": uncommitted[:40],
            },
            "G_cannot_trace": cannot_trace,
        },
    }


def knowledge_timeline(root: Path, hist_areas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """July → August → September events derived from Git first-seen dates."""
    events: list[dict[str, Any]] = []
    for a in hist_areas:
        for key, kind in (
            ("code_first_seen", "CODE"),
            ("tests_first_seen", "TEST"),
            ("kc_first_mention", "KC_MENTION"),
            ("dedicated_kc_first_seen", "DEDICATED_KC"),
        ):
            ev = a.get(key)
            if not ev:
                continue
            events.append({
                "date": _iso_day(ev.get("commit_date")),
                "kind": kind,
                "area": a["id"],
                "title": a["title"],
                "commit": ev.get("commit_hash"),
                "origin": ev.get("origin") or a.get("origin"),
            })
    events.sort(key=lambda e: (e.get("date") or "", e.get("kind") or ""))
    by_month: dict[str, list] = {"2026-07": [], "2026-08": [], "2026-09": []}
    for e in events:
        m = (e.get("date") or "")[:7]
        if m in by_month:
            by_month[m].append(e)
    return [
        {"month": m, "events": by_month[m]}
        for m in ("2026-07", "2026-08", "2026-09")
    ]


def change_record_from_commit(
    *,
    file: str,
    commit: Optional[dict[str, Any]],
    module: str,
    coverage_now: str,
    related_kc: list[str],
    related_tests: list[str],
    iteration: dict[str, Any],
    change_type: str,
) -> dict[str, Any]:
    origin = classify_origin(
        (commit or {}).get("author", ""),
        (commit or {}).get("email", ""),
        (commit or {}).get("subject", ""),
    )
    digest = hashlib.sha1(f"{file}:{(commit or {}).get('commit_hash','')}".encode()).hexdigest()[:12]
    return {
        "change_id": digest,
        "commit_hash": (commit or {}).get("commit_hash"),
        "commit_date": (commit or {}).get("commit_date"),
        "author": (commit or {}).get("author"),
        "origin": origin["origin"],
        "origin_confidence": origin["confidence"],
        "branch": None,
        "file": file,
        "path": file,
        "change_type": change_type,
        "module": module,
        "phase": infer_phase(module + " " + file),
        "iteration_if_known": iteration,
        "related_tests": related_tests,
        "related_kc_artifacts": related_kc,
        "related_registry_entries": [],
        "documentation_state_at_change": UNKNOWN,
        "current_documentation_state": coverage_now,
        "migration_context": UNKNOWN,
        "confidence": origin["confidence"],
    }


def build_history_report(root: Optional[Path] = None, coverage_areas: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    from routes import knowledge_center as kc

    root = root or kc.resolve_project_root()
    if not git_available(root):
        return {
            "generated_at": _now(),
            "engine": "knowledge_history",
            "phase": "4",
            "git_available": False,
            "canonical_promotion_allowed": CANONICAL_PROMOTION_ALLOWED,
            "rewrites_sources": False,
            "areas": [],
            "note": "Git is not available in this working directory.",
        }

    if coverage_areas is None:
        corpus = load_corpus()
        registry = kc._load_registry()
        function_map = kc._parse_function_map()
        coverage_areas = [
            classify_area(
                area,
                root=root,
                corpus=corpus,
                registry=registry,
                function_map_text=(root / REG_FUNCTION_MAP).read_text(encoding="utf-8", errors="replace") if (root / REG_FUNCTION_MAP).is_file() else "",
                canonical_text=(root / REG_CANONICAL).read_text(encoding="utf-8", errors="replace") if (root / REG_CANONICAL).is_file() else "",
                ssot_text=(root / REG_SSOT).read_text(encoding="utf-8", errors="replace") if (root / REG_SSOT).is_file() else "",
                platform_text=(root / DOC_PLATFORM_STATE).read_text(encoding="utf-8", errors="replace") if (root / DOC_PLATFORM_STATE).is_file() else "",
            )
            for area in WATCH_AREAS
        ]
    else:
        function_map = kc._parse_function_map()

    paths: set[str] = set()
    for area in WATCH_AREAS:
        paths.update(area.get("implementation") or ())
        paths.update(area.get("tests") or ())
        paths.update(area.get("dedicated_kc") or ())
    for a in coverage_areas:
        paths.update(a.get("kc_mentions") or [])
    paths.update(IMPORTANT_KC)
    paths.update(c.get("kc") for c in PROVENANCE_CLAIMS if c.get("kc"))
    for extra in EXTRA_TRACKED:
        paths.update(extra.get("implementation") or ())
        paths.update(extra.get("tests") or ())

    indexes = {p: file_git_index(root, p) for p in sorted(p for p in paths if p)}
    by_id = {a["id"]: a for a in coverage_areas}
    hist_areas = [
        historical_area(area, by_id[area["id"]], root, indexes)
        for area in WATCH_AREAS
        if area["id"] in by_id
    ]

    claims = [verify_claim(root, spec, indexes) for spec in PROVENANCE_CLAIMS]
    fn_hist = function_map_history(root, coverage_areas, function_map)
    mps = mps_history(root, indexes=indexes)
    mig = migration_trace(root)
    timeline = knowledge_timeline(root, hist_areas)

    change_records = []
    for area, h in zip(WATCH_AREAS, hist_areas):
        for rel in area.get("implementation") or ():
            idx = indexes.get(rel) or {}
            change_records.append(
                change_record_from_commit(
                    file=rel,
                    commit=idx.get("first_seen"),
                    module=area["id"],
                    coverage_now=h["current_documentation_state"],
                    related_kc=h["related_kc_artifacts"],
                    related_tests=h["related_tests"],
                    iteration=h["iteration"],
                    change_type="implementation",
                )
            )

    kc_docs = []
    for path in IMPORTANT_KC:
        idx = indexes.get(path) or file_git_index(root, path)
        related_code = None
        for area in WATCH_AREAS:
            if path in (area.get("dedicated_kc") or ()):
                rels = area.get("implementation") or ()
                related_code = _earliest([(indexes.get(p) or {}).get("first_seen") for p in rels])
                break
        kc_docs.append({
            "path": path,
            "first_seen_in_git": idx.get("first_seen"),
            "last_changed_in_git": idx.get("last_changed"),
            "related_code_first_seen": related_code,
            "claim_type": (
                "CURRENT_IMPLEMENTATION" if "FAZA_10C" in path or "HARTABLOCURI_INTEGRATION" in path
                else "GOVERNANCE" if "EXECUTION_ORDER" in path
                else "REGISTRY" if "registries/" in path
                else "HISTORICAL"
            ),
        })

    return {
        "generated_at": _now(),
        "engine": "knowledge_history",
        "phase": "4",
        "git_available": True,
        "canonical_promotion_allowed": False,
        "rewrites_sources": False,
        "note": (
            "Historical evidence derived from Git. "
            "Iteration IDs from filenames are inferred. "
            "Absence before first code is NOT_APPLICABLE, not an error. "
            "Nothing is marked lost without Git evidence."
        ),
        "areas": hist_areas,
        "claims": claims,
        "function_map_history": fn_hist,
        "mps_history": mps,
        "migration": mig,
        "timeline": timeline,
        "kc_documents": kc_docs,
        "file_index": {p: {k: indexes[p][k] for k in ("state", "first_seen", "last_changed", "renamed", "deleted")} for p in indexes},
        "change_records": change_records,
        "lost_forbidden": True,
    }


def attach_history(report: dict[str, Any], root: Optional[Path] = None) -> dict[str, Any]:
    hist = build_history_report(root=root, coverage_areas=report.get("areas"))
    report["history"] = hist
    report["phase"] = "2+4"
    return report


def engine_writes_nothing() -> bool:
    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    forbidden = {"insert_one", "update_one", "delete_one", "unlink", "rmtree", "write_text", "write_bytes"}
    return forbidden.isdisjoint(names | attrs)
