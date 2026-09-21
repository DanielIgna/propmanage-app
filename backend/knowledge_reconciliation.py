"""Knowledge Center Phase 5 — migration reconciliation baseline.

Read-only. Does not redesign Phase 4. Does not write canonical sources.
Derives three-state evidence from Git. Never marks LOST without a deletion
or a remote-only path that Git can show.
"""
from __future__ import annotations

import ast
import re
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
    detect_duplicates,
    load_corpus,
)
from knowledge_history import (
    CONFIRMED,
    NOT_APPLICABLE,
    UNKNOWN,
    classify_origin,
    file_git_index,
    git_available,
    _git,
)

KIND_PRODUCT_CODE = "PRODUCT_CODE"
KIND_PRODUCT_TEST = "PRODUCT_TEST"
KIND_KNOWLEDGE = "KNOWLEDGE"
KIND_DOCUMENTATION = "DOCUMENTATION"
KIND_REGISTRY = "REGISTRY"
KIND_EMERGENT_TOOLING = "EMERGENT_TOOLING"
KIND_CONFIGURATION = "CONFIGURATION"
KIND_CICD = "CI/CD"
KIND_GENERATED = "GENERATED"
KIND_UNKNOWN = "UNKNOWN"

MIG_SURVIVED = "SURVIVED"
MIG_INTENTIONALLY_REMOVED = "INTENTIONALLY_REMOVED"
MIG_SUPERSEDED = "SUPERSEDED"
MIG_DUPLICATE = "DUPLICATE"
MIG_REMOTE_ONLY = "REMOTE_ONLY"
MIG_UNKNOWN = "UNKNOWN"

LOC_EMERGENT_ONLY = "EMERGENT_ONLY"
LOC_ORIGIN_ONLY = "ORIGIN_ONLY"
LOC_LOCAL_ONLY = "LOCAL_ONLY"
LOC_SHARED = "SHARED"
LOC_DIVERGED = "DIVERGED"
LOC_UNKNOWN = "UNKNOWN"

MATCH = "MATCH"
PARTIAL = "PARTIAL"
MISSING = "MISSING"
STALE = "STALE"
CONFLICT = "CONFLICT"

EMERGENT_REF = "emergent/main"
ORIGIN_REF = "origin/main"
LOCAL_REF = "HEAD"

SIGNIFICANT_PATHS: tuple[str, ...] = (
    "backend/routes/knowledge_center.py",
    "backend/data/enterprise_registry.json",
    "backend/evidence_semantics.py",
    "backend/document_fact_extraction.py",
    "backend/claim_matching.py",
    "backend/document_property_support.py",
    "backend/building_identity.py",
    "backend/routes/building_identity.py",
    "backend/hartablocuri_source_ledger.py",
    "backend/hartablocuri_import.py",
    "backend/hartablocuri_read_layer.py",
    "backend/geocoding.py",
    "backend/backup_service.py",
    "backend/routes/admin_backups.py",
    "backend/routes/property_documents.py",
    "frontend/src/pages/clientv2/DocumentVault.jsx",
    "frontend/src/pages/admin/MorningBriefing.jsx",
    "frontend/src/pages/admin/KnowledgeCenter.jsx",
    "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md",
    "memory/audits/HARTABLOCURI_INTEGRATION.md",
    DOC_PLATFORM_STATE,
    "memory/audits/MASTER_PLATFORM_STATE_2026-07-31.md",
    "memory/audits/MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md",
    "memory/audits/PROPERTY_TWIN_CANONICAL_v1.0.md",
    "memory/board/EXECUTION_ORDER_CX2_PROPERTY_DNA_DOCUMENT_VAULT.md",
    REG_FUNCTION_MAP,
    REG_CANONICAL,
    REG_SSOT,
    "memory/INDEX.md",
    "memory/CHANGELOG.md",
    ".emergent/emergent.yml",
)

CANONICAL_CONFLICT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "mps_family",
        "sources": (
            DOC_PLATFORM_STATE,
            "memory/audits/MASTER_PLATFORM_STATE_2026-07-31.md",
            "memory/audits/MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md",
        ),
        "conflict_type": "LIVING_VS_DATED_SNAPSHOT",
        "what": "Three MASTER_PLATFORM_STATE artifacts can be read as the platform state.",
        "question": "Which file is the living MPS, and are dated copies historical only?",
    },
    {
        "id": "function_map_vs_code",
        "sources": (REG_FUNCTION_MAP, "frontend/src/pages/clientv2/DocumentVault.jsx"),
        "conflict_type": "REGISTRY_PATH_VS_IMPLEMENTATION",
        "what": "FUNCTION_MAP FN-005 cites PropertyDocumentsPanel.jsx; current UI is DocumentVault.jsx.",
        "question": "Is Function Map a living map of current code, or a frozen 2026-06 snapshot?",
    },
    {
        "id": "ssot_vs_canonical_vs_fn",
        "sources": (REG_SSOT, REG_CANONICAL, REG_FUNCTION_MAP),
        "conflict_type": "MULTI_REGISTRY_AUTHORITY",
        "what": "SSOT, Canonical System Registry, and Function Map can each be treated as the capability index.",
        "question": "Which registry is authoritative for current implementation rows?",
    },
    {
        "id": "hartablocuri_split",
        "sources": (
            "memory/audits/HARTABLOCURI_INTEGRATION.md",
            "backend/hartablocuri_source_ledger.py",
        ),
        "conflict_type": "DEDICATED_DOC_BEHIND_CODE",
        "what": "HARTABLOCURI_INTEGRATION.md exists; Source Ledger is implemented and unmentioned.",
        "question": "Update the integration doc, add a dedicated ledger doc, or leave the split?",
    },
    {
        "id": "property_twin_vs_identity",
        "sources": (
            "memory/audits/PROPERTY_TWIN_CANONICAL_v1.0.md",
            "backend/building_identity.py",
        ),
        "conflict_type": "DESIGN_VS_LATER_IMPLEMENTATION",
        "what": "Property Twin canonical predates Building Identity (12db435f).",
        "question": "Is Property Twin still the identity doctrine, or did Building Identity supersede it?",
    },
    {
        "id": "ten_b_design_only",
        "sources": ("memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md",),
        "conflict_type": "DESIGN_SESSION_VS_IMPLEMENTATION_CLAIM",
        "what": "10C names 10B as a design/session contract with no dedicated KC and no 10B module.",
        "question": "Keep 10B as DESIGN, or treat a missing dedicated doc as a gap?",
    },
)

CURSOR_ERA: tuple[dict[str, Any], ...] = (
    {"hash": "743ca6e", "role": "MIGRATION_SUPPORT", "label": "Remove .emergent tooling; GitHub Actions smoke cwd"},
    {"hash": "4a52574", "role": "LOCAL_SETUP", "label": "Backup/storage paths + vendored emergentintegrations"},
    {"hash": "be6499d", "role": "PRODUCT_CODE", "label": "Non-blocking geocoding"},
    {"hash": "dabade5", "role": "MIGRATION_SUPPORT", "label": "Cloudflare Workers / Yarn 4 Wrangler"},
    {"hash": "4215961", "role": "MIGRATION_SUPPORT", "label": "Static Workers assets"},
    {"hash": "283ba7d", "role": "MIGRATION_SUPPORT", "label": "Pages SPA fallback"},
    {"hash": "ca51924", "role": "MIGRATION_SUPPORT", "label": "Full React app on Cloudflare Pages (generated cf-site)"},
    {"hash": "252f562", "role": "MIGRATION_SUPPORT", "label": "Pages Functions /api proxy"},
    {"hash": "b03a9ba", "role": "KNOWLEDGE_INFRASTRUCTURE", "label": "KC path alignment"},
    {"hash": "12db435f", "role": "CURSOR_DEVELOPMENT", "label": "Evidence stack 7B–10C / identity / ledger / 10C KC"},
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_path_kind(path: str) -> str:
    p = (path or "").replace("\\", "/")
    if p.startswith(".emergent/"):
        return KIND_EMERGENT_TOOLING
    if p.startswith("memory/registries/") or p.endswith("enterprise_registry.json"):
        return KIND_REGISTRY
    if p.startswith("memory/"):
        return KIND_KNOWLEDGE
    if p.startswith("docs/"):
        return KIND_DOCUMENTATION
    if "/tests/" in p or p.startswith("backend/tests/"):
        return KIND_PRODUCT_TEST
    if p.startswith(("backend/", "frontend/src/")):
        return KIND_PRODUCT_CODE
    if p.startswith(".github/") or p in {"wrangler.jsonc", "worker/index.js"} or p.startswith("functions/"):
        return KIND_CICD
    if p.startswith(("cf-site/", "static/", "frontend/public/sitemap")) or p in {
        "asset-manifest.json",
        "index.html",
        "_redirects",
        "sw.js",
    }:
        return KIND_GENERATED
    if p in {".gitignore", ".yarnrc.yml", "frontend/src/setupProxy.js", "package.json", "yarn.lock"}:
        return KIND_CONFIGURATION
    return KIND_UNKNOWN


def exclusive_commit_hashes(root: Path, present_in: str, absent_from: str) -> list[str]:
    r = _git(root, "rev-list", "--reverse", f"{absent_from}..{present_in}")
    if r.returncode != 0:
        return []
    return [l.strip() for l in r.stdout.splitlines() if l.strip()]


def _blob(root: Path, ref: str, path: str) -> Optional[str]:
    r = _git(root, "rev-parse", f"{ref}:{path}")
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip() or None


def _exists_at(root: Path, ref: str, path: str) -> bool:
    return _blob(root, ref, path) is not None


def inspect_commit(root: Path, commit: str) -> dict[str, Any]:
    meta = _git(root, "show", "-s", "--format=%H%x09%aI%x09%an%x09%ae%x09%s%x09%P", commit)
    parts = (meta.stdout or "").strip().split("\t")
    if len(parts) < 6:
        return {"commit_hash": commit, "error": "unreadable"}
    h, iso, author, email, subject, parents = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
    origin = classify_origin(author, email, subject)
    ns = _git(root, "show", "--name-status", "--format=", commit)
    num = _git(root, "show", "--numstat", "--format=", commit)
    added, modified, deleted, renames = [], [], [], []
    files: list[dict[str, Any]] = []
    for line in ns.stdout.splitlines():
        if not line.strip():
            continue
        bits = line.split("\t")
        status, path = bits[0], bits[-1]
        kind = classify_path_kind(path)
        rec = {"status": status, "path": path, "kind": kind, "rename_from": bits[1] if status.startswith("R") and len(bits) >= 3 else None}
        files.append(rec)
        if status.startswith("A"):
            added.append(path)
        elif status.startswith("D"):
            deleted.append(path)
        elif status.startswith("R"):
            renames.append({"from": bits[1], "to": path, "status": status})
        else:
            modified.append(path)

    numstat: dict[str, dict[str, int]] = {}
    for line in num.stdout.splitlines():
        bits = line.split("\t")
        if len(bits) >= 3 and bits[0] != "-":
            try:
                numstat[bits[2]] = {"added": int(bits[0]), "deleted": int(bits[1])}
            except ValueError:
                continue

    kinds = sorted({f["kind"] for f in files})
    modules, kc, registries, tests = [], [], [], []
    for f in files:
        p = f["path"]
        if p.startswith("backend/tests/"):
            tests.append(p)
        if p.startswith("memory/registries/") or p.endswith("enterprise_registry.json"):
            registries.append(p)
        if p.startswith("memory/") or p.startswith("docs/"):
            kc.append(p)
        if p.startswith("backend/") and "/tests/" not in p:
            modules.append(p)
        if p.startswith("frontend/src/"):
            modules.append(p)

    classified_files = []
    for f in files:
        p = f["path"]
        local_blob = _blob(root, LOCAL_REF, p)
        commit_blob = _blob(root, h, p) if not f["status"].startswith("D") else None
        if f["status"].startswith("D") and not _exists_at(root, LOCAL_REF, p):
            mig = MIG_INTENTIONALLY_REMOVED if p.startswith(".emergent/") else MIG_REMOTE_ONLY
        elif f["status"].startswith("D"):
            mig = MIG_SUPERSEDED
        elif local_blob and commit_blob and local_blob == commit_blob:
            mig = MIG_SURVIVED
        elif local_blob and commit_blob and local_blob != commit_blob:
            mig = MIG_SUPERSEDED
        elif not local_blob and commit_blob:
            mig = MIG_REMOTE_ONLY
        elif not local_blob and f["status"].startswith("A"):
            mig = MIG_REMOTE_ONLY
        else:
            mig = MIG_UNKNOWN
        # Product hunks that never landed locally stay REMOTE_ONLY even if the host file exists.
        if mig == MIG_SUPERSEDED and p in {
            "backend/backup_service.py",
            "backend/routes/admin_backups.py",
            "frontend/src/pages/admin/MorningBriefing.jsx",
        }:
            text = (root / p).read_text(encoding="utf-8", errors="replace") if (root / p).is_file() else ""
            if "create_bson_dump" not in text and "dump-bson" not in text:
                mig = MIG_REMOTE_ONLY
        classified_files.append({**f, "migration_state": mig, "numstat": numstat.get(p)})

    states = {c["migration_state"] for c in classified_files}
    if states == {MIG_REMOTE_ONLY} or (MIG_REMOTE_ONLY in states and MIG_INTENTIONALLY_REMOVED in states and len(states) <= 2):
        commit_mig = MIG_REMOTE_ONLY if MIG_REMOTE_ONLY in states else MIG_INTENTIONALLY_REMOVED
    elif states == {MIG_INTENTIONALLY_REMOVED}:
        commit_mig = MIG_INTENTIONALLY_REMOVED
    elif states == {MIG_SURVIVED}:
        commit_mig = MIG_SURVIVED
    elif MIG_REMOTE_ONLY in states and MIG_SUPERSEDED in states:
        commit_mig = MIG_REMOTE_ONLY
    else:
        commit_mig = next(iter(states)) if len(states) == 1 else MIG_UNKNOWN

    return {
        "commit_hash": h,
        "commit_date": iso,
        "author": author,
        "email": email,
        "subject": subject,
        "parent": parents.split()[0] if parents else None,
        "parents": parents.split(),
        "files_added": added,
        "files_modified": modified,
        "files_deleted": deleted,
        "renames": renames,
        "affected_modules": modules,
        "affected_KC": kc,
        "affected_registries": registries,
        "affected_tests": tests,
        "kinds": kinds,
        "files": classified_files,
        "likely_origin": origin["origin"],
        "confidence": origin["confidence"],
        "origin_evidence": origin["evidence"],
        "migration_state": commit_mig,
        "lost": False,
    }


def three_state_presence(root: Path, path: str) -> dict[str, Any]:
    blobs = {
        "emergent": _blob(root, EMERGENT_REF, path),
        "origin": _blob(root, ORIGIN_REF, path),
        "local": _blob(root, LOCAL_REF, path),
    }
    present = {k: v is not None for k, v in blobs.items()}
    n = sum(present.values())
    uniq = {v for v in blobs.values() if v}
    if n == 0:
        loc = LOC_UNKNOWN
    elif n == 1:
        loc = LOC_EMERGENT_ONLY if present["emergent"] else LOC_ORIGIN_ONLY if present["origin"] else LOC_LOCAL_ONLY
    elif n == 3 and len(uniq) == 1:
        loc = LOC_SHARED
    elif n >= 2 and len(uniq) > 1:
        loc = LOC_DIVERGED
    elif n == 2 and len(uniq) == 1:
        loc = LOC_SHARED
    else:
        loc = LOC_UNKNOWN
    return {"path": path, "blobs": blobs, "present": present, "location": loc}


def working_tree_classification(root: Path) -> dict[str, Any]:
    porcelain = _git(root, "status", "--porcelain")
    buckets = {"phase2": [], "phase4": [], "phase5": [], "unrelated": [], "generated": [], "temporary": []}
    rows = []
    for line in porcelain.stdout.splitlines():
        if not line:
            continue
        code, path = line[:2], line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        kind = classify_path_kind(path)
        if path in {
            "backend/knowledge_coverage.py",
            "backend/tests/test_knowledge_coverage_iter240.py",
        } or (path.endswith("KnowledgeCenter.jsx") and code.strip() == "M"):
            bucket = "phase2"
        elif path in {
            "backend/knowledge_history.py",
            "backend/tests/test_knowledge_history_iter241.py",
        }:
            bucket = "phase4"
        elif path in {
            "backend/knowledge_reconciliation.py",
            "backend/tests/test_knowledge_reconciliation_iter242.py",
        }:
            bucket = "phase5"
        elif path == "backend/routes/knowledge_center.py":
            bucket = "phase2"  # coverage/history/reconciliation API wiring
        elif path.startswith("frontend/public/sitemap"):
            bucket = "generated"
        elif path.endswith((".pyc", ".tmp", ".DS_Store")) or "/__pycache__/" in path:
            bucket = "temporary"
        else:
            bucket = "unrelated"
        rec = {"path": path, "index_status": code, "kind": kind, "bucket": bucket, "untracked": code.strip().startswith("?")}
        rows.append(rec)
        buckets[bucket].append(path)
    return {
        "rows": rows,
        "buckets": buckets,
        "counts": {k: len(v) for k, v in buckets.items()},
        "note": "Working tree is not modified by this engine.",
    }


def file_level_baseline(root: Path, paths: Iterable[str]) -> list[dict[str, Any]]:
    out = []
    for path in paths:
        idx = file_git_index(root, path)
        loc = three_state_presence(root, path)
        deleted = bool(idx.get("deleted"))
        renamed = bool(idx.get("renamed"))
        mig = MIG_UNKNOWN
        if loc["location"] == LOC_SHARED:
            mig = MIG_SURVIVED
        elif loc["location"] == LOC_DIVERGED:
            mig = MIG_SUPERSEDED
        elif loc["location"] == LOC_EMERGENT_ONLY:
            mig = MIG_INTENTIONALLY_REMOVED if path.startswith(".emergent/") else MIG_REMOTE_ONLY
        elif loc["location"] == LOC_LOCAL_ONLY:
            mig = MIG_SURVIVED
        elif loc["location"] == LOC_ORIGIN_ONLY:
            mig = MIG_REMOTE_ONLY
        if deleted and not loc["present"]["local"]:
            mig = MIG_INTENTIONALLY_REMOVED if path.startswith(".emergent/") else MIG_REMOTE_ONLY
        out.append({
            "path": path,
            "kind": classify_path_kind(path),
            "first_seen": idx.get("first_seen"),
            "last_changed": idx.get("last_changed"),
            "deleted": deleted,
            "renamed": renamed,
            "rename_from": idx.get("rename_from"),
            "present_local": loc["present"]["local"],
            "present_origin": loc["present"]["origin"],
            "present_emergent": loc["present"]["emergent"],
            "blobs": loc["blobs"],
            "location": loc["location"],
            "migration_state": mig,
            "lost": False,
        })
    return out


def _coverage_areas(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from routes import knowledge_center as kc

    corpus = load_corpus()
    registry = kc._load_registry()
    function_map = kc._parse_function_map()
    areas = [
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
    return areas, function_map


def kc_reconciliation_baseline(root: Path, areas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for a in areas:
        impl = a.get("implementation_present") or []
        tests = a.get("tests_present") or []
        firsts = [file_git_index(root, p).get("first_seen") for p in impl]
        lasts = [file_git_index(root, p).get("last_changed") for p in impl]
        firsts = [x for x in firsts if x]
        lasts = [x for x in lasts if x]
        loc_states = [three_state_presence(root, p)["location"] for p in impl]
        if a["status"] == "DOCUMENTED":
            recon = MATCH
        elif a["status"] == "PARTIALLY_DOCUMENTED":
            recon = PARTIAL
        elif a["status"] == "UNDOCUMENTED":
            recon = MISSING
        elif a["status"] == "STALE":
            recon = STALE
        else:
            recon = UNKNOWN
        mig = MIG_SURVIVED if impl and all(s in {LOC_SHARED, LOC_DIVERGED, LOC_LOCAL_ONLY} for s in loc_states) else MIG_UNKNOWN
        if impl and all(s == LOC_LOCAL_ONLY for s in loc_states):
            mig = MIG_SURVIVED
        rows.append({
            "id": a["id"],
            "title": a["title"],
            "kc_artifact": (a.get("dedicated_kc") or a.get("kc_mentions") or [None])[0],
            "code_evidence": impl,
            "test_evidence": tests,
            "registry": a.get("in_canonical_registry") or a.get("in_ssot"),
            "dependency": a.get("in_dependency_map"),
            "function_map": a.get("in_function_map"),
            "git_first_seen": min(firsts, key=lambda x: x.get("commit_date") or "") if firsts else None,
            "git_last_changed": max(lasts, key=lambda x: x.get("commit_date") or "") if lasts else None,
            "current_status": a["status"],
            "reconciliation": recon,
            "migration_status": mig,
            "claim_category": "IMPLEMENTATION_FACT" if impl else "UNKNOWN",
            "canonical": False,
        })
    return rows


def canonical_conflicts(root: Path) -> list[dict[str, Any]]:
    rows = []
    for spec in CANONICAL_CONFLICT_SPECS:
        sources = []
        for p in spec["sources"]:
            idx = file_git_index(root, p)
            sources.append({
                "path": p,
                "exists": (root / p).exists(),
                "first_seen": (idx or {}).get("first_seen"),
                "last_changed": (idx or {}).get("last_changed"),
                "kind": classify_path_kind(p),
            })
        rows.append({
            "id": spec["id"],
            "source_a": sources[0] if sources else None,
            "source_b": sources[1] if len(sources) > 1 else None,
            "sources": sources,
            "what_each_claims": spec["what"],
            "conflict_type": spec["conflict_type"],
            "founder_decision_required": spec["question"],
            "winner_chosen": False,
            "canonicalized": False,
        })
    corpus = load_corpus()
    dups = detect_duplicates(corpus)
    for g in dups:
        if g.get("kind") in {"HISTORICAL_COPY", "VERSION_COPY"}:
            rows.append({
                "id": f"dup:{g['kind']}:{g['paths'][0]}",
                "source_a": {"path": g["paths"][0], "exists": True},
                "source_b": {"path": g["paths"][1], "exists": True} if len(g["paths"]) > 1 else None,
                "sources": [{"path": p, "exists": True} for p in g["paths"]],
                "what_each_claims": g.get("note"),
                "conflict_type": g["kind"],
                "founder_decision_required": g.get("proposal"),
                "winner_chosen": False,
                "canonicalized": False,
            })
    return rows


def documentation_baseline(areas: list[dict[str, Any]]) -> dict[str, list[str]]:
    buckets = {
        "A_implemented_documented": [],
        "B_implemented_partial": [],
        "C_implemented_undocumented": [],
        "D_documented_design_not_implemented": ["10B Document↔Property Contract — cited in FAZA_10C as design/session; no module, no dedicated KC, no tests"],
        "E_roadmap": ["CX-2 execution order remains GOVERNANCE/DESIGN, not a current-implementation certificate"],
        "F_historical": [
            "memory/audits/MASTER_PLATFORM_STATE_2026-07-31.md",
            "memory/audits/MASTER_PLATFORM_STATE_LIVING_GOVERNANCE_2026-07-31.md",
        ],
        "G_stale": [],
        "H_conflicting": ["MPS family", "FN-005 path vs DocumentVault", "HartaBlocuri integration vs Source Ledger"],
    }
    for a in areas:
        has_impl = bool(a.get("implementation_present"))
        st = a["status"]
        if has_impl and st == "DOCUMENTED":
            buckets["A_implemented_documented"].append(a["id"])
        elif has_impl and st == "PARTIALLY_DOCUMENTED":
            buckets["B_implemented_partial"].append(a["id"])
        elif has_impl and st == "UNDOCUMENTED":
            buckets["C_implemented_undocumented"].append(a["id"])
        elif has_impl and st == "STALE":
            buckets["G_stale"].append(a["id"])
        elif not has_impl and (a.get("dedicated_kc") or a.get("kc_mentions")):
            buckets["D_documented_design_not_implemented"].append(a["id"])
    return buckets


def product_vs_knowledge() -> list[dict[str, Any]]:
    return [
        {"item": "7B Evidence Contract", "implementation_fact": True, "knowledge_claim": "Mentioned as 10C dependency", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": "Partial mention ≠ dedicated 7B doctrine"},
        {"item": "8B Fact Extraction", "implementation_fact": True, "knowledge_claim": "Mentioned as 10C dependency", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": "Partial mention ≠ dedicated 8B doctrine"},
        {"item": "9C Claim Matching", "implementation_fact": True, "knowledge_claim": "Registry node exists; no dedicated KC", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": "Registry row ≠ dedicated 9C document"},
        {"item": "10C Document↔Property Support", "implementation_fact": True, "knowledge_claim": "Dedicated FAZA_10C MATCH", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": None},
        {"item": "10B Document↔Property Contract", "implementation_fact": False, "knowledge_claim": "Named in FAZA_10C as design/session", "design_decision": True, "roadmap": False, "governance": False, "historical": False, "do_not_convert": "Do not convert 10B into 'implemented'"},
        {"item": "Building Identity", "implementation_fact": True, "knowledge_claim": "Mention only", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": None},
        {"item": "Source Ledger", "implementation_fact": True, "knowledge_claim": False, "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": "Code without KC is UNDOCUMENTED, not a doctrine"},
        {"item": "Document Vault", "implementation_fact": True, "knowledge_claim": "CX-2 order + FN-005", "design_decision": False, "roadmap": False, "governance": True, "historical": False, "do_not_convert": "Order is GOVERNANCE; FN-005 path is STALE"},
        {"item": "HartaBlocuri Integration", "implementation_fact": True, "knowledge_claim": "Dedicated doc STALE vs ledger", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": None},
        {"item": "BSON dump (emergent-only)", "implementation_fact": True, "knowledge_claim": "CHANGELOG on emergent", "design_decision": False, "roadmap": False, "governance": False, "historical": False, "do_not_convert": "REMOTE_ONLY on emergent/main — not LOST"},
        {"item": "Property Twin Canonical v1.0", "implementation_fact": False, "knowledge_claim": True, "design_decision": True, "roadmap": False, "governance": False, "historical": True, "do_not_convert": "Historical/design record, not current identity code"},
        {"item": "FUNCTION_MAP.md", "implementation_fact": False, "knowledge_claim": True, "design_decision": False, "roadmap": False, "governance": True, "historical": True, "do_not_convert": "Do not treat last-update 2026-06 as current September inventory"},
        {"item": "Living MPS", "implementation_fact": False, "knowledge_claim": True, "design_decision": False, "roadmap": False, "governance": True, "historical": True, "do_not_convert": "Last Git write 2026-08-28 is not a September certificate"},
    ]


def classify_local_commit_role(subject: str, files: list[str]) -> dict[str, Any]:
    joined = " ".join(files).lower()
    s = (subject or "").lower()
    labels = []
    if any(p.startswith(".emergent/") or "wrangler" in p or p.startswith("cf-site/") or p.startswith("functions/") for p in files):
        labels.append("MIGRATION_SUPPORT")
    if any(p.startswith("backend/") and "/tests/" not in p and "knowledge_" not in p for p in files):
        labels.append("PRODUCT_CODE")
    if any("knowledge" in p or p.startswith("memory/") for p in files):
        labels.append("KNOWLEDGE_INFRASTRUCTURE")
    if any(p.startswith("backend/tests/") for p in files):
        labels.append("PRODUCT_TEST")
    if any(p.startswith(("frontend/src/setupProxy", "backend/vendor/", ".github/")) for p in files):
        labels.append("LOCAL_SETUP")
    if re.search(r"cloudflare|pages|wrangler|workers", s):
        labels.append("MIGRATION_SUPPORT")
    if re.search(r"knowledge center|evidence|path align", s):
        labels.append("CURSOR_DEVELOPMENT")
    return {"roles": sorted(set(labels)) or ["UNKNOWN"]}


def september_cursor_baseline(root: Path, local_not_emergent: list[dict[str, Any]], working: dict[str, Any]) -> list[dict[str, Any]]:
    by_prefix = {c["commit_hash"][:7]: c for c in local_not_emergent}
    by_prefix.update({c["commit_hash"][:8]: c for c in local_not_emergent})
    rows = []
    for spec in CURSOR_ERA:
        c = None
        for k, v in by_prefix.items():
            if v["commit_hash"].startswith(spec["hash"]):
                c = v
                break
        on_origin = False
        on_emergent = False
        if c:
            on_origin = _git(root, "merge-base", "--is-ancestor", c["commit_hash"], ORIGIN_REF).returncode == 0
            on_emergent = _git(root, "merge-base", "--is-ancestor", c["commit_hash"], EMERGENT_REF).returncode == 0
        rows.append({
            "commit": spec["hash"],
            "full_hash": (c or {}).get("commit_hash"),
            "role": spec["role"],
            "label": spec["label"],
            "code": (c or {}).get("affected_modules") or [],
            "tests": (c or {}).get("affected_tests") or [],
            "kc": (c or {}).get("affected_KC") or [],
            "registry": (c or {}).get("affected_registries") or [],
            "on_origin": on_origin,
            "on_emergent": on_emergent,
            "push_status": (
                "on_origin_not_emergent" if on_origin and not on_emergent
                else "local_only" if c and not on_origin and not on_emergent
                else "unknown"
            ),
            "migration_role": spec["role"],
        })
    rows.append({
        "commit": "WORKING_TREE",
        "role": "KNOWLEDGE_INFRASTRUCTURE",
        "label": "Uncommitted Phase 2 coverage + Phase 4 history (+ Phase 5 reconciliation if present)",
        "code": working["buckets"]["phase2"] + working["buckets"]["phase4"] + working["buckets"]["phase5"],
        "tests": [p for p in working["buckets"]["phase2"] + working["buckets"]["phase4"] + working["buckets"]["phase5"] if "/tests/" in p],
        "kc": [],
        "registry": [],
        "on_origin": False,
        "on_emergent": False,
        "push_status": "uncommitted",
        "migration_role": "KNOWLEDGE_INFRASTRUCTURE",
    })
    return rows


def autonomy_capability_baseline() -> list[dict[str, Any]]:
    return [
        {"capability": "CHANGE", "status": "IMPLEMENTED", "evidence": "Phase 2 change_records + git status; Phase 5 working_tree_classification"},
        {"capability": "CODE → KC", "status": "IMPLEMENTED", "evidence": "Phase 2 classify_area / coverage statuses"},
        {"capability": "KC → CODE", "status": "PARTIAL", "evidence": "Phase 4 kc_documents + claims; not a full reverse index of every KC file"},
        {"capability": "GIT HISTORY", "status": "IMPLEMENTED", "evidence": "Phase 4 file_git_index / pickaxe / origin"},
        {"capability": "MIGRATION", "status": "IMPLEMENTED", "evidence": "Phase 5 three-state + exclusive commits + file-level baseline"},
        {"capability": "REGISTRY DRIFT", "status": "PARTIAL", "evidence": "Phase 2 in_canonical/in_ssot flags; no first-mention date per node"},
        {"capability": "FUNCTION DRIFT", "status": "IMPLEMENTED", "evidence": "Phase 2/4 proposed_delta + stale path refs; not written"},
        {"capability": "DEPENDENCY GAPS", "status": "IMPLEMENTED", "evidence": "Phase 2 dependency_coverage from enterprise_registry.json only"},
        {"capability": "PROVENANCE", "status": "PARTIAL", "evidence": "Phase 4 seeded claims; not a full knowledge graph"},
        {"capability": "CANONICAL PROMOTION", "status": "MISSING", "evidence": "Explicitly forbidden. Founder review remains the boundary."},
        {"capability": "AUTONOMOUS REWRITE", "status": "MISSING", "evidence": "No writer. Phase 5 baseline only."},
    ]


def founder_decision_queue() -> list[dict[str, Any]]:
    return [
        {"id": "fn_lifecycle", "question": "Is FUNCTION_MAP.md a living map or a frozen 2026-06 snapshot?", "evidence": "Last Git change 2026-08-28; FN-005 path missing; no 7B–10C rows", "affected_sources": [REG_FUNCTION_MAP], "possible_states": ["LIVING", "HISTORICAL", "HYBRID"], "what_would_change": "Living → Founder-authored delta rows. Historical → stop flagging missing September rows as map defects."},
        {"id": "mps_policy", "question": "Which MASTER_PLATFORM_STATE file is living, and must September code be represented?", "evidence": "Living file last Git 2026-08-28; dated 2026-07-31 copies remain", "affected_sources": [DOC_PLATFORM_STATE, "memory/audits/MASTER_PLATFORM_STATE_2026-07-31.md"], "possible_states": ["UPDATE_LIVING", "CUT_NEW_DATED", "DECLARE_HISTORICAL"], "what_would_change": "Update living → September modules enter MPS. Historical → coverage stops treating MPS silence as staleness of the product."},
        {"id": "ten_b_status", "question": "What is the canonical status of 10B?", "evidence": "FAZA_10C cites 10B as design/session; no module, no dedicated KC, no tests", "affected_sources": ["memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md"], "possible_states": ["DESIGN", "SUPERSEDED_BY_10C", "TO_BE_DOCUMENTED"], "what_would_change": "DESIGN → leave as-is. Documented → new artifact (future phase). Implemented → would require code that does not exist."},
        {"id": "hartablocuri_split", "question": "Should Source Ledger live inside HARTABLOCURI_INTEGRATION.md or have a dedicated artifact?", "evidence": "Ledger implemented 2026-09-19; integration doc 2026-09-16 does not mention it", "affected_sources": ["memory/audits/HARTABLOCURI_INTEGRATION.md", "backend/hartablocuri_source_ledger.py"], "possible_states": ["UPDATE_INTEGRATION", "DEDICATED_LEDGER_DOC", "LEAVE_SPLIT"], "what_would_change": "Either a Founder-authored edit of the integration doc or a new dedicated doc. This phase writes neither."},
        {"id": "dep_map_scope", "question": "Must every watch area have a Dependency Map node?", "evidence": "7B/8B/ledger/path-alignment/vault have no enterprise_registry nodes", "affected_sources": ["backend/data/enterprise_registry.json"], "possible_states": ["EXPAND_MAP", "WATCHLIST_ONLY", "DOCUMENTED_SUBSET"], "what_would_change": "Expand → new registry nodes (Founder). Watchlist-only → UNDOCUMENTED dep gaps are not defects."},
        {"id": "doc_7b", "question": "Create a dedicated 7B KC artifact?", "evidence": "Code+tests 2026-09-19; mention in 10C only", "affected_sources": ["backend/evidence_semantics.py"], "possible_states": ["CREATE", "KEEP_AS_MENTION", "FOLD_INTO_10C"], "what_would_change": "Create is a future Founder-authored document. This phase does not create it."},
        {"id": "doc_8b", "question": "Create a dedicated 8B KC artifact?", "evidence": "Code+tests 2026-09-19; mention in 10C only", "affected_sources": ["backend/document_fact_extraction.py"], "possible_states": ["CREATE", "KEEP_AS_MENTION", "FOLD_INTO_10C"], "what_would_change": "Same as 7B — future phase."},
        {"id": "doc_9c", "question": "Create a dedicated 9C KC artifact?", "evidence": "Code+tests+registry node; no dedicated KC", "affected_sources": ["backend/claim_matching.py", REG_CANONICAL], "possible_states": ["CREATE", "KEEP_REGISTRY_ONLY"], "what_would_change": "Future Founder-authored document."},
        {"id": "doc_identity", "question": "Create a dedicated Building Identity KC artifact?", "evidence": "Code+tests+dep node; mention only", "affected_sources": ["backend/building_identity.py"], "possible_states": ["CREATE", "FOLD_INTO_TWIN", "KEEP_AS_MENTION"], "what_would_change": "Touches Property Twin vs identity conflict."},
        {"id": "doc_ledger", "question": "Create a dedicated Source Ledger KC artifact?", "evidence": "Implemented+tested; UNDOCUMENTED", "affected_sources": ["backend/hartablocuri_source_ledger.py"], "possible_states": ["CREATE", "UPDATE_INTEGRATION"], "what_would_change": "Same split as hartablocuri_split."},
        {"id": "doc_path_align", "question": "Document KC path alignment?", "evidence": "b03a9ba + iter239; UNDOCUMENTED", "affected_sources": ["backend/routes/knowledge_center.py"], "possible_states": ["CREATE", "TREAT_AS_INFRA"], "what_would_change": "Infra-only → coverage stops listing it as a product gap."},
        {"id": "commit_phase24", "question": "Should Phase 2/4 (and 5) infrastructure now be committed?", "evidence": "Untracked knowledge_coverage.py, knowledge_history.py, tests; dirty KnowledgeCenter.jsx and knowledge_center.py; generated sitemaps also dirty", "affected_sources": ["backend/knowledge_coverage.py", "backend/knowledge_history.py", "frontend/src/pages/admin/KnowledgeCenter.jsx"], "possible_states": ["COMMIT_ENGINE_ONLY", "COMMIT_ENGINE_AND_UI", "LEAVE_UNCOMMITTED"], "what_would_change": "Commit makes coverage/history recoverable; does not canonicalize product docs. Sitemaps are generated and may be excluded."},
        {"id": "bson_dump_remote", "question": "Bring Emergent BSON dump (eadb12e + b7715cc) into local main?", "evidence": "Product diffs exist only on emergent/main; local backup_service.py lacks create_bson_dump", "affected_sources": ["backend/backup_service.py", "backend/routes/admin_backups.py", "frontend/src/pages/admin/MorningBriefing.jsx"], "possible_states": ["CHERRY_PICK", "REIMPLEMENT", "LEAVE_ON_EMERGENT"], "what_would_change": "Cherry-pick is a product change (future). Leaving it is REMOTE_ONLY, not LOST."},
    ]


def three_state_matrix(root: Path, significant: list[dict[str, Any]]) -> dict[str, Any]:
    local = (_git(root, "rev-parse", LOCAL_REF).stdout or "").strip()
    emergent = (_git(root, "rev-parse", EMERGENT_REF).stdout or "").strip()
    origin = (_git(root, "rev-parse", ORIGIN_REF).stdout or "").strip()
    mb_e = (_git(root, "merge-base", LOCAL_REF, EMERGENT_REF).stdout or "").strip()
    mb_o = (_git(root, "merge-base", LOCAL_REF, ORIGIN_REF).stdout or "").strip()
    e_only = exclusive_commit_hashes(root, EMERGENT_REF, LOCAL_REF)
    o_only = exclusive_commit_hashes(root, ORIGIN_REF, LOCAL_REF)
    l_not_e = exclusive_commit_hashes(root, LOCAL_REF, EMERGENT_REF)
    l_not_o = exclusive_commit_hashes(root, LOCAL_REF, ORIGIN_REF)

    def files(ref: str) -> set[str]:
        r = _git(root, "ls-tree", "-r", "--name-only", ref)
        return set(r.stdout.splitlines()) if r.returncode == 0 else set()

    fe, fo, fl = files(EMERGENT_REF), files(ORIGIN_REF), files(LOCAL_REF)
    dirs = ("memory", "docs", "backend", "frontend", "memory/registries", "memory/audits", ".emergent")
    dir_matrix = {}
    for d in dirs:
        dir_matrix[d] = {
            "emergent": any(p == d or p.startswith(d + "/") for p in fe),
            "origin": any(p == d or p.startswith(d + "/") for p in fo),
            "local": any(p == d or p.startswith(d + "/") for p in fl),
        }
    return {
        "commits": {
            "local_HEAD": local,
            "emergent_main": emergent,
            "origin_main": origin,
            "merge_base_emergent": mb_e,
            "merge_base_origin": mb_o,
            "emergent_only": e_only,
            "origin_only": o_only,
            "local_not_on_emergent": l_not_e,
            "local_not_on_origin": l_not_o,
            "relation_vs_origin": "LOCAL_AHEAD" if o_only == [] and l_not_o else "DIVERGED" if o_only and l_not_o else "UNKNOWN",
            "relation_vs_emergent": "DIVERGED",
        },
        "files": {
            "counts": {"emergent": len(fe), "origin": len(fo), "local": len(fl)},
            "emergent_not_local": sorted(fe - fl),
            "origin_not_local": sorted(fo - fl),
            "local_not_origin": sorted(fl - fo),
            "local_not_emergent_product": sorted(
                p for p in (fl - fe)
                if p.startswith(("backend/", "frontend/src/", "memory/", "docs/")) and not p.startswith("cf-site/")
            ),
        },
        "directories": dir_matrix,
        "significant": significant,
    }


def build_reconciliation_report(root: Optional[Path] = None) -> dict[str, Any]:
    from routes import knowledge_center as kc

    root = root or kc.resolve_project_root()
    if not git_available(root):
        return {
            "generated_at": _now(),
            "engine": "knowledge_reconciliation",
            "phase": "5",
            "git_available": False,
            "rewrites_sources": False,
            "canonical_promotion_allowed": CANONICAL_PROMOTION_ALLOWED,
        }

    emergent_only = [inspect_commit(root, h) for h in exclusive_commit_hashes(root, EMERGENT_REF, LOCAL_REF)]
    local_not_origin = [inspect_commit(root, h) for h in exclusive_commit_hashes(root, LOCAL_REF, ORIGIN_REF)]
    local_not_emergent = [inspect_commit(root, h) for h in exclusive_commit_hashes(root, LOCAL_REF, EMERGENT_REF)]
    for c in local_not_origin + local_not_emergent:
        c["roles"] = classify_local_commit_role(c.get("subject") or "", c.get("files_added", []) + c.get("files_modified", []) + c.get("files_deleted", []))["roles"]

    working = working_tree_classification(root)
    files = file_level_baseline(root, SIGNIFICANT_PATHS)
    matrix = three_state_matrix(root, files)
    areas, _fm = _coverage_areas(root)
    baseline = kc_reconciliation_baseline(root, areas)
    conflicts = canonical_conflicts(root)
    docs = documentation_baseline(areas)
    sep = september_cursor_baseline(root, local_not_emergent, working)

    return {
        "generated_at": _now(),
        "engine": "knowledge_reconciliation",
        "phase": "5",
        "git_available": True,
        "rewrites_sources": False,
        "canonical_promotion_allowed": False,
        "lost_forbidden": True,
        "note": (
            "Forensic reconciliation baseline. "
            "No canonical document is rewritten. "
            "Nothing is marked lost without Git evidence."
        ),
        "emergent_only_commits": emergent_only,
        "local_not_on_origin": local_not_origin,
        "local_not_on_emergent": local_not_emergent,
        "three_state": matrix,
        "working_tree": working,
        "file_level": files,
        "kc_baseline": baseline,
        "canonical_conflicts": conflicts,
        "documentation_baseline": docs,
        "product_vs_knowledge": product_vs_knowledge(),
        "september_cursor": sep,
        "autonomy": autonomy_capability_baseline(),
        "founder_decision_queue": founder_decision_queue(),
    }


def engine_writes_nothing() -> bool:
    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    forbidden = {"insert_one", "update_one", "delete_one", "unlink", "rmtree", "write_text", "write_bytes"}
    return forbidden.isdisjoint(names | attrs)
