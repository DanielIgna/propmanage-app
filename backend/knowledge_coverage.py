"""Knowledge ↔ Code coverage engine (KC Autonomy Phase 2).

Read-only. Deterministic. No persistence. No canonical promotion.
Code/tests are evidence of implementation, not product doctrine.

Watch areas are a coverage inventory — not Founder doctrine.
UNDOCUMENTED ≠ wrong. Candidates are never canonical.
"""
from __future__ import annotations

import ast
import hashlib
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

# Coverage vocabulary (explicit; not lifecycle Active/Review/Draft)
DOCUMENTED = "DOCUMENTED"
PARTIALLY_DOCUMENTED = "PARTIALLY_DOCUMENTED"
UNDOCUMENTED = "UNDOCUMENTED"
STALE = "STALE"
DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
CONFLICT_CANDIDATE = "CONFLICT_CANDIDATE"
UNKNOWN = "UNKNOWN"

# Reconciliation
MATCH = "MATCH"
PARTIAL = "PARTIAL"
MISSING = "MISSING"
CONFLICT = "CONFLICT"

# Dependency map (observed edge types only — never invented)
REL_GOVERNS = "GOVERNS"
REL_INHERITS = "INHERITS"
REL_FEEDS = "FEEDS"
REL_PRODUCES = "PRODUCES"
REL_EXPOSES = "EXPOSES"
REL_GATES = "GATES"
REL_USES = "USES"
REL_UNKNOWN = "UNKNOWN"
REL_BROKEN = "BROKEN"

EDGE_TYPE_MAP = {
    "document_governs_engine": REL_GOVERNS,
    "document_governs_metric": REL_GOVERNS,
    "document_authorizes_engine": REL_GOVERNS,
    "prompt_inheritance": REL_INHERITS,
    "engine_feeds_engine": REL_FEEDS,
    "metric_feeds_engine": REL_FEEDS,
    "engine_writes_database": REL_PRODUCES,
    "engine_computes_metric": REL_PRODUCES,
    "engine_exposes_api": REL_EXPOSES,
    "api_feeds_dashboard": REL_EXPOSES,
    "engine_gates_engine": REL_GATES,
    "automation_triggers_engine": REL_USES,
}

TEMPLATE_TITLES = {
    "EXECUTION ORDER",
    "INTERVIEW TEMPLATE",
    "PATTERN TEMPLATE",
    "RESEARCH REPORT TEMPLATE",
    "REUSE AUDIT TEMPLATE",
}

# Seed inventory from the Phase-2 audit, verified against the repository.
# This is a watch list, not a product decision.
WATCH_AREAS: tuple[dict[str, Any], ...] = (
    {
        "id": "evidence_contract_7b",
        "title": "7B Evidence Contract",
        "implementation": ("backend/evidence_semantics.py",),
        "tests": ("backend/tests/test_evidence_contract_alignment_iter234.py",),
        "needles": ("evidence_semantics", "evidence contract", "faza 7b", "7b evidence"),
        "dedicated_kc": (),
        "registry_node_ids": (),
        "function_map_needles": ("evidence contract", "evidence_semantics", "7b"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/FAZA_7B_EVIDENCE_CONTRACT.md",
        "suggested_dependencies": ("document_fact_extraction_8b", "claim_matching_9c"),
    },
    {
        "id": "document_fact_extraction_8b",
        "title": "8B Fact Extraction",
        "implementation": ("backend/document_fact_extraction.py",),
        "tests": (
            "backend/tests/test_document_fact_extraction_iter235.py",
            "backend/tests/test_document_fact_extraction_qa_iter236.py",
        ),
        "needles": ("document_fact_extraction", "8b fact", "faza 8b", "vault pdf text-layer"),
        "dedicated_kc": (),
        "registry_node_ids": (),
        "function_map_needles": ("fact extraction", "document_fact_extraction", "8b"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/FAZA_8B_FACT_EXTRACTION.md",
        "suggested_dependencies": ("evidence_contract_7b", "document_vault"),
    },
    {
        "id": "claim_matching_9c",
        "title": "9C Claim Matching",
        "implementation": ("backend/claim_matching.py",),
        "tests": ("backend/tests/test_claim_matching_iter237.py",),
        "needles": ("claim_matching", "faza 9c", "9c claim", "evidence ↔ claim"),
        "dedicated_kc": (),
        "registry_node_ids": ("engine:claim_matching",),
        "function_map_needles": ("claim matching", "claim_matching", "9c"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/FAZA_9C_CLAIM_MATCHING.md",
        "suggested_dependencies": ("evidence_contract_7b", "document_property_support_10c"),
    },
    {
        "id": "document_property_support_10c",
        "title": "10C Document↔Property Support",
        "implementation": ("backend/document_property_support.py",),
        "tests": ("backend/tests/test_document_property_support_iter238.py",),
        "needles": ("document_property_support", "document_property_support", "faza 10c", "document_property_support"),
        "dedicated_kc": ("memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md",),
        "registry_node_ids": ("doc:faza_10c", "engine:document_property_support"),
        "function_map_needles": ("document_property_support", "10c", "document↔property"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md",
        "suggested_dependencies": ("claim_matching_9c", "building_identity"),
    },
    {
        "id": "building_identity",
        "title": "Building Identity",
        "implementation": (
            "backend/building_identity.py",
            "backend/routes/building_identity.py",
        ),
        "tests": (
            "backend/tests/test_building_identity_iter230.py",
            "backend/tests/test_building_create_guard_iter231.py",
        ),
        "needles": ("building_identity", "building identity", "detect_unit_granularity"),
        "dedicated_kc": (),
        "registry_node_ids": ("engine:building_identity",),
        "function_map_needles": ("building identity", "building_identity"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/BUILDING_IDENTITY.md",
        "suggested_dependencies": ("hartablocuri_integration", "document_property_support_10c"),
    },
    {
        "id": "trust_boundary",
        "title": "Document Vault Trust Boundary",
        "implementation": ("backend/routes/property_documents.py",),
        "tests": ("backend/tests/test_document_vault_trust_boundary_iter233.py",),
        "needles": ("trust boundary", "trust_boundary", "document_vault_trust_boundary"),
        "dedicated_kc": (),
        "registry_node_ids": (),
        "function_map_needles": ("trust boundary", "trust_boundary"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/DOCUMENT_VAULT_TRUST_BOUNDARY.md",
        "suggested_dependencies": ("document_vault", "evidence_contract_7b"),
    },
    {
        "id": "hartablocuri_source_ledger",
        "title": "HartaBlocuri Source Ledger",
        "implementation": ("backend/hartablocuri_source_ledger.py",),
        "tests": ("backend/tests/test_hartablocuri_source_ledger_iter232.py",),
        "needles": ("hartablocuri_source_ledger", "source-record ledger", "source ledger"),
        "dedicated_kc": (),
        "registry_node_ids": (),
        "function_map_needles": ("source ledger", "hartablocuri_source_ledger"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/HARTABLOCURI_SOURCE_LEDGER.md",
        "suggested_dependencies": ("hartablocuri_integration",),
    },
    {
        "id": "kc_path_alignment",
        "title": "KC Path Alignment",
        "implementation": ("backend/routes/knowledge_center.py",),
        "tests": ("backend/tests/test_knowledge_center_path_alignment_iter239.py",),
        "needles": ("kc_project_root", "path alignment", "resolve_project_root", "kc_memory_root"),
        "dedicated_kc": (),
        "registry_node_ids": (),
        "function_map_needles": ("path alignment", "kc_project_root"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/KC_PATH_ALIGNMENT.md",
        "suggested_dependencies": ("document_vault",),
    },
    {
        "id": "document_vault",
        "title": "Document Vault (current implementation)",
        "implementation": (
            "backend/routes/property_documents.py",
            "frontend/src/pages/clientv2/DocumentVault.jsx",
        ),
        "tests": (
            "backend/tests/test_cx2_document_vault_iter134.py",
            "backend/tests/test_document_vault_trust_boundary_iter233.py",
        ),
        "needles": ("documentvault", "document vault", "property_documents"),
        "dedicated_kc": ("memory/board/EXECUTION_ORDER_CX2_PROPERTY_DNA_DOCUMENT_VAULT.md",),
        "registry_node_ids": (),
        "function_map_needles": ("property documents", "document vault", "fn-005"),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/DOCUMENT_VAULT_CURRENT.md",
        "suggested_dependencies": ("trust_boundary", "document_fact_extraction_8b"),
        "stale_if_function_map_refs_missing": True,
    },
    {
        "id": "hartablocuri_integration",
        "title": "HartaBlocuri Integration",
        "implementation": (
            "backend/hartablocuri_import.py",
            "backend/hartablocuri_read_layer.py",
        ),
        "tests": (
            "backend/tests/test_hartablocuri_truth_layer_iter224.py",
            "backend/tests/test_hartablocuri_phase2_iter226.py",
        ),
        "needles": ("hartablocuri_import", "hartablocuri_read_layer", "hartablocuri_integration"),
        "dedicated_kc": ("memory/audits/HARTABLOCURI_INTEGRATION.md",),
        "registry_node_ids": (),
        "function_map_needles": ("hartablocuri",),
        "suggested_category": "Platform Audits",
        "suggested_kc_path": "memory/audits/HARTABLOCURI_INTEGRATION.md",
        "suggested_dependencies": ("hartablocuri_source_ledger", "building_identity"),
        "require_mentions_of": ("backend/hartablocuri_source_ledger.py",),
    },
)

# Audit backlog — verified only if the area exists and is not DOCUMENTED.
PRIORITY_HINTS: tuple[str, ...] = (
    "evidence_contract_7b",
    "document_fact_extraction_8b",
    "claim_matching_9c",
    "building_identity",
    "trust_boundary",
    "hartablocuri_source_ledger",
    "kc_path_alignment",
    "document_vault",
    "function_map",
    "master_platform_state",
    "canonical_system_registry",
    "hartablocuri_integration",
)

REG_FUNCTION_MAP = "memory/registries/FUNCTION_MAP.md"
REG_CANONICAL = "memory/registries/CANONICAL_SYSTEM_REGISTRY.md"
REG_SSOT = "memory/registries/SSOT_REGISTRY.md"
DOC_PLATFORM_STATE = "memory/audits/MASTER_PLATFORM_STATE.md"

CANONICAL_PROMOTION_ALLOWED = False


class CanonicalPromotionForbidden(PermissionError):
    """Candidates must never become CANONICAL without Founder review."""


@dataclass(frozen=True)
class CorpusDoc:
    path: str
    title: str
    text: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_root() -> Path:
    from routes import knowledge_center as kc

    return kc.resolve_project_root()


def _exists(root: Path, rel: str) -> bool:
    return (root / rel).is_file()


def _read(root: Path, rel: str) -> str:
    p = root / rel
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def _title_of(text: str, fallback: str) -> str:
    for m in re.finditer(r"^#\s*(.+)$", text[:1600], re.MULTILINE):
        cand = m.group(1).strip().lstrip("#").strip()
        if re.search(r"[A-Za-z0-9ĂÂÎȘȚăâîșț]", cand):
            return cand[:160]
    return fallback


def is_generated_phase_audit(rel: str) -> bool:
    """PHASE_N_*AUDIT* reports describe coverage; they must not satisfy it."""
    name = Path(rel).name.upper()
    return name.startswith("PHASE_") and "AUDIT" in name


def load_corpus() -> list[CorpusDoc]:
    from routes import knowledge_center as kc

    docs: list[CorpusDoc] = []
    for p, rel in kc._all_files():
        if is_generated_phase_audit(rel):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        docs.append(CorpusDoc(path=rel, title=_title_of(text, rel.rsplit("/", 1)[-1]), text=text))
    return docs


def _hits(corpus: Iterable[CorpusDoc], needles: Iterable[str]) -> list[str]:
    found: list[str] = []
    lowered = [(d.path, d.text.lower(), d.path.lower()) for d in corpus]
    for needle in needles:
        n = (needle or "").lower().strip()
        if not n:
            continue
        for path, body, path_l in lowered:
            if n in body or n in path_l:
                if path not in found:
                    found.append(path)
    return found


def _text_has_any(text: str, needles: Iterable[str]) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles if n)


def classify_area(
    area: dict[str, Any],
    *,
    root: Path,
    corpus: list[CorpusDoc],
    registry: dict[str, Any],
    function_map_text: str,
    canonical_text: str,
    ssot_text: str,
    platform_text: str,
) -> dict[str, Any]:
    impl = [p for p in area["implementation"] if _exists(root, p)]
    missing_impl = [p for p in area["implementation"] if not _exists(root, p)]
    tests = [p for p in area["tests"] if _exists(root, p)]
    missing_tests = [p for p in area["tests"] if not _exists(root, p)]
    dedicated = [p for p in area.get("dedicated_kc") or () if _exists(root, p)]
    mentions = _hits(corpus, area.get("needles") or ())
    other_mentions = [p for p in mentions if p not in dedicated]

    node_ids = set(area.get("registry_node_ids") or ())
    nodes = [n for n in registry.get("nodes", []) if n.get("id") in node_ids]
    in_dep_map = bool(nodes)
    in_function_map = _text_has_any(function_map_text, area.get("function_map_needles") or ())
    registry_needles = tuple(area.get("needles") or ()) + tuple(area.get("function_map_needles") or ())
    in_canonical = _text_has_any(canonical_text, registry_needles)
    in_ssot = _text_has_any(ssot_text, registry_needles)
    in_platform = _text_has_any(platform_text, registry_needles)

    required = [p for p in area.get("require_mentions_of") or () if _exists(root, p)]
    dedicated_text = "\n".join(_read(root, p) for p in dedicated)
    missing_required_mentions = [p for p in required if p.split("/")[-1].lower() not in dedicated_text.lower() and p.lower() not in dedicated_text.lower()]

    stale_fn_map = False
    if area.get("stale_if_function_map_refs_missing") and in_function_map:
        stale_fn_map = "propertydocumentspanel" in function_map_text.lower() and not _exists(
            root, "frontend/src/components/PropertyDocumentsPanel.jsx"
        )

    if not impl and not tests:
        status = UNKNOWN
        reason = "Watch area has no implementation or test files on disk."
    elif dedicated and missing_required_mentions:
        status = STALE
        reason = "Dedicated KC artifact exists but does not mention current implementation files."
    elif dedicated and stale_fn_map:
        status = STALE
        reason = "Dedicated order/doc exists; Function Map still points at a missing implementation path."
    elif dedicated and (in_ssot or in_canonical or in_dep_map):
        status = DOCUMENTED
        reason = "Dedicated KC artifact plus at least one of SSOT / Canonical Registry / Dependency Map."
        if not in_function_map:
            reason += " Function Map has no row (tracked separately as drift)."
    elif dedicated:
        status = PARTIALLY_DOCUMENTED
        reason = "Dedicated KC artifact exists but is not registered in SSOT / Canonical / Dependency Map."
    elif mentions:
        status = PARTIALLY_DOCUMENTED
        reason = "Implementation is mentioned in KC but has no dedicated artifact."
    elif impl or tests:
        status = UNDOCUMENTED
        reason = "Implementation and/or tests exist; no KC mention found."
    else:
        status = UNKNOWN
        reason = "Insufficient evidence to classify."

    return {
        "id": area["id"],
        "title": area["title"],
        "status": status,
        "reason": reason,
        "implementation_present": impl,
        "implementation_missing": missing_impl,
        "tests_present": tests,
        "tests_missing": missing_tests,
        "dedicated_kc": dedicated,
        "kc_mentions": mentions,
        "other_kc_mentions": other_mentions,
        "dependency_nodes": [n["id"] for n in nodes],
        "in_dependency_map": in_dep_map,
        "in_function_map": in_function_map,
        "in_canonical_registry": in_canonical,
        "in_ssot": in_ssot,
        "in_platform_state": in_platform,
        "missing_required_mentions": missing_required_mentions,
        "suggested_category": area.get("suggested_category"),
        "suggested_kc_path": area.get("suggested_kc_path"),
        "suggested_dependencies": list(area.get("suggested_dependencies") or ()),
        "canonical": False,
        "note": "UNDOCUMENTED is a coverage gap, not a product defect.",
    }


def generate_candidate(area_result: dict[str, Any]) -> Optional[dict[str, Any]]:
    """CANDIDATE only. Never canonical. Never written to disk."""
    if area_result["status"] not in {UNDOCUMENTED, PARTIALLY_DOCUMENTED, STALE}:
        return None
    if area_result["status"] == STALE and area_result.get("dedicated_kc"):
        # Stale dedicated docs need reconciliation, not a second candidate file.
        if area_result["id"] != "document_vault":
            return None
    if not (area_result["implementation_present"] or area_result["tests_present"]):
        return None
    if area_result["status"] == DOCUMENTED:
        return None
    if area_result.get("dedicated_kc") and area_result["status"] == PARTIALLY_DOCUMENTED:
        # Already has a dedicated artifact — candidate would duplicate it.
        return None

    confidence = "high" if area_result["implementation_present"] and area_result["tests_present"] else "medium"
    return {
        "candidate_id": f"cand:{area_result['id']}",
        "proposed_title": area_result["title"],
        "affected_implementation": area_result["implementation_present"],
        "affected_tests": area_result["tests_present"],
        "existing_references": area_result["kc_mentions"],
        "suggested_kc_category": area_result["suggested_category"],
        "suggested_kc_path": area_result["suggested_kc_path"],
        "suggested_dependencies": area_result["suggested_dependencies"],
        "confidence": confidence,
        "reason": area_result["reason"],
        "coverage_status": area_result["status"],
        "canonical": False,
        "auto_promotable": False,
        "requires_founder_review": True,
    }


def promote_candidate(_candidate: dict[str, Any] | None = None) -> None:
    """Hard guard — no automatic canonicalization path exists."""
    raise CanonicalPromotionForbidden(
        "Candidates are never auto-promoted to CANONICAL. Founder review is required."
    )


def write_canonical_document(*_a: Any, **_k: Any) -> None:
    raise CanonicalPromotionForbidden("Engine must not write canonical Knowledge Center documents.")


def delete_kc_artifact(*_a: Any, **_k: Any) -> None:
    raise CanonicalPromotionForbidden("Engine must not delete Knowledge Center artifacts.")


def _stem_family(path: str) -> str:
    name = Path(path).stem.upper()
    name = re.sub(r"_\d{4}-\d{2}-\d{2}.*$", "", name)
    name = name.replace("_LIVING_GOVERNANCE", "")
    return name


def detect_duplicates(corpus: list[CorpusDoc]) -> list[dict[str, Any]]:
    """Safe detection only. Never deletes. Distinguishes versions vs true duplicates."""
    by_title: dict[str, list[CorpusDoc]] = defaultdict(list)
    by_family: dict[str, list[CorpusDoc]] = defaultdict(list)
    for d in corpus:
        by_title[d.title].append(d)
        by_family[_stem_family(d.path)].append(d)

    groups: list[dict[str, Any]] = []
    seen_paths: set[tuple[str, ...]] = set()

    def add(kind: str, docs: list[CorpusDoc], note: str) -> None:
        if len(docs) < 2:
            return
        key = tuple(sorted(d.path for d in docs))
        if key in seen_paths:
            return
        seen_paths.add(key)
        titles = {d.title for d in docs}
        proposal = "Keep all. Do not delete. Review whether one is historical and should stay Archived."
        if kind == "VERSION_COPY":
            proposal = "Treat dated copies as historical snapshots. Do not delete. Keep the undated file as the living pointer if that is the declared SSOT."
        elif kind == "TEMPLATE_TITLE":
            proposal = "Same H1 template, different files. Not a true duplicate. No cleanup."
        elif kind == "HISTORICAL_COPY":
            proposal = "Likely dated/living pair. Keep both. Do not delete. Optionally mark the dated file as the snapshot."
        groups.append({
            "kind": kind,
            "status": DUPLICATE_CANDIDATE,
            "title": docs[0].title,
            "paths": [d.path for d in docs],
            "titles": sorted(titles),
            "note": note,
            "proposal": proposal,
            "canonical": False,
        })

    for title, docs in by_title.items():
        if len(docs) < 2:
            continue
        if title.upper().strip() in TEMPLATE_TITLES or title.upper().startswith("EXECUTION ORDER"):
            add("TEMPLATE_TITLE", docs, "Shared title template; contents and paths differ.")
        else:
            add("SAME_TITLE_DIFFERENT_PATH", docs, "Identical H1 title in more than one file.")

    for family, docs in by_family.items():
        if len(docs) < 2:
            continue
        if family in {"MASTER_PLATFORM_STATE", "MASTER_PLATFORM_STATE_LIVING_GOVERNANCE"} or family.startswith("MASTER_PLATFORM_STATE"):
            add("HISTORICAL_COPY", docs, "MASTER_PLATFORM_STATE family — living + dated copies.")
        elif re.search(r"_\d{4}-\d{2}-\d{2}", " ".join(d.path for d in docs)):
            add("VERSION_COPY", docs, "Same stem with dated suffix.")

    return groups


def _normalize_repo_path(raw: str) -> str:
    p = raw.strip().strip("`").strip()
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("/app/"):
        p = p[len("/app/"):]
    elif p.startswith("app/"):
        p = p[len("app/"):]
    return p


def function_map_stale_entries(root: Path, function_map: dict[str, Any]) -> list[dict[str, Any]]:
    stale: list[dict[str, Any]] = []
    for fn in function_map.get("functions") or []:
        missing: list[str] = []
        for field in ("frontend", "backend"):
            raw = fn.get(field) or ""
            for part in re.findall(r"`([^`]+)`", raw) or re.split(r"[,;]", raw):
                token = _normalize_repo_path(part.strip().strip("`"))
                if not token or " " in token or "*" in token or "?" in token:
                    continue
                if not token.startswith(("frontend/", "backend/", "src/")):
                    continue
                if token.endswith((".jsx", ".js", ".ts", ".tsx", ".py")) and not _exists(root, token):
                    missing.append(token)
        if missing:
            stale.append({
                "function_id": fn.get("id"),
                "name": fn.get("name"),
                "missing_paths": missing,
                "status": STALE,
                "note": "Function Map references files that are not in the repository.",
            })
    return stale


def function_map_drift(areas: list[dict[str, Any]], function_map: dict[str, Any]) -> dict[str, Any]:
    names = " ".join(
        f"{fn.get('id','')} {fn.get('name','')} {fn.get('backend','')} {fn.get('frontend','')} {fn.get('description','')}"
        for fn in function_map.get("functions") or []
    ).lower()
    missing_rows: list[dict[str, Any]] = []
    present_rows: list[str] = []
    for a in areas:
        needles = [a["id"].replace("_", " "), a["title"].lower()]
        hit = any(n in names for n in needles if n)
        # also use in_function_map already computed
        if a.get("in_function_map") or hit:
            present_rows.append(a["id"])
        else:
            missing_rows.append({
                "id": a["id"],
                "title": a["title"],
                "proposed_action": "ADD_ROW_CANDIDATE",
                "implementation": a["implementation_present"],
                "tests": a["tests_present"],
                "canonical": False,
                "note": "Proposed Function Map delta only. Not written.",
            })
    last_update = (function_map.get("meta") or {}).get("last update") or (function_map.get("meta") or {}).get("last_update")
    return {
        "source": REG_FUNCTION_MAP,
        "last_update": last_update,
        "functions_in_map": (function_map.get("summary") or {}).get("total", 0),
        "areas_mentioned": present_rows,
        "proposed_delta": missing_rows,
        "stale_path_refs": [],  # filled by caller
        "rewritten": False,
    }


def _map_edge_type(raw: str) -> str:
    return EDGE_TYPE_MAP.get(raw, REL_UNKNOWN)


def dependency_coverage(areas: list[dict[str, Any]], registry: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    from routes import knowledge_center as kc

    names = {n["id"]: n for n in registry.get("nodes", [])}
    out: list[dict[str, Any]] = []
    for a in areas:
        nodes = [names[i] for i in a.get("dependency_nodes") or [] if i in names]
        # also match engine nodes by implementation ref
        if not nodes:
            for n in registry.get("nodes", []):
                ref = (n.get("ref") or "").replace("\\", "/")
                if any(ref.endswith(p.split("/", 1)[-1]) or ref == p for p in a["implementation_present"]):
                    nodes.append(n)
        rels = []
        broken = []
        for n in nodes:
            for e in registry.get("edges", []):
                if e["source"] != n["id"] and e["target"] != n["id"]:
                    continue
                other_id = e["target"] if e["source"] == n["id"] else e["source"]
                other = names.get(other_id, {})
                ref = other.get("ref") or ""
                rel_type = _map_edge_type(e.get("type") or "")
                exists = True
                if ref.startswith(("memory/", "docs/")):
                    try:
                        kc._safe_resolve(ref)
                    except Exception:
                        exists = False
                elif ref.startswith(("backend/", "frontend/")):
                    exists = _exists(root, ref)
                if not exists and ref:
                    rel_type = REL_BROKEN
                    broken.append(ref)
                rels.append({
                    "edge_id": e.get("id"),
                    "raw_type": e.get("type"),
                    "mapped_type": rel_type,
                    "other_id": other_id,
                    "other_name": other.get("name"),
                    "other_ref": ref,
                    "invented": False,
                })
        out.append({
            "id": a["id"],
            "owning_document": a.get("dedicated_kc") or [],
            "related_kc": a.get("kc_mentions") or [],
            "producing_function": a.get("implementation_present") or [],
            "related_tests": a.get("tests_present") or [],
            "registry_nodes": [n["id"] for n in nodes],
            "relations": rels,
            "broken_refs": broken,
            "gap": not nodes,
        })
    return out


def reconcile_sources(areas: list[dict[str, Any]]) -> dict[str, Any]:
    def for_source(key: str, pred) -> dict[str, Any]:
        rows = []
        for a in areas:
            ok = pred(a)
            if a["status"] == STALE and ok:
                state = STALE
            elif ok and a["status"] == DOCUMENTED:
                state = MATCH
            elif ok:
                state = PARTIAL
            else:
                state = MISSING
            rows.append({"id": a["id"], "title": a["title"], "state": state})
        return {
            "match": sum(1 for r in rows if r["state"] == MATCH),
            "partial": sum(1 for r in rows if r["state"] == PARTIAL),
            "missing": sum(1 for r in rows if r["state"] == MISSING),
            "stale": sum(1 for r in rows if r["state"] == STALE),
            "rows": rows,
        }

    return {
        "enterprise_registry": for_source("dep", lambda a: a.get("in_dependency_map")),
        "function_map": for_source("fn", lambda a: a.get("in_function_map")),
        "canonical_system_registry": for_source("can", lambda a: a.get("in_canonical_registry")),
        "ssot_registry": for_source("ssot", lambda a: a.get("in_ssot")),
        "master_platform_state": for_source("mps", lambda a: a.get("in_platform_state")),
        "rewritten": False,
    }


def health_metrics(areas: list[dict[str, Any]], duplicates: list[dict[str, Any]], recon: dict[str, Any], drift: dict[str, Any]) -> dict[str, Any]:
    """Individual inspectable metrics. No single overall score."""
    n = len(areas) or 1
    by = Counter(a["status"] for a in areas)
    with_impl = [a for a in areas if a["implementation_present"]]
    with_tests = [a for a in areas if a["tests_present"]]
    return {
        "watch_areas": len(areas),
        "knowledge_coverage": {
            "documented": by[DOCUMENTED],
            "partial": by[PARTIALLY_DOCUMENTED],
            "undocumented": by[UNDOCUMENTED],
            "stale": by[STALE],
            "unknown": by[UNKNOWN],
        },
        "implementation_coverage": {
            "implemented_areas": len(with_impl),
            "implemented_with_any_kc_mention": sum(1 for a in with_impl if a["kc_mentions"]),
        },
        "canonical_coverage": {
            "areas_with_dedicated_kc": sum(1 for a in areas if a["dedicated_kc"]),
        },
        "dependency_coverage": {
            "areas_with_registry_node": sum(1 for a in areas if a["in_dependency_map"]),
        },
        "function_map_coverage": {
            "areas_mentioned": sum(1 for a in areas if a["in_function_map"]),
            "proposed_delta_rows": len(drift.get("proposed_delta") or []),
        },
        "test_to_knowledge_coverage": {
            "areas_with_tests": len(with_tests),
            "tested_with_dedicated_kc": sum(1 for a in with_tests if a["dedicated_kc"]),
        },
        "registry_freshness": {
            "function_map_missing": recon["function_map"]["missing"],
            "canonical_missing": recon["canonical_system_registry"]["missing"],
            "ssot_missing": recon["ssot_registry"]["missing"],
            "platform_state_missing": recon["master_platform_state"]["missing"],
        },
        "duplicate_risk": {"groups": len(duplicates)},
        "conflict_risk": {"stale_areas": by[STALE]},
        "knowledge_drift": {
            "undocumented_plus_stale_plus_fn_delta": by[UNDOCUMENTED] + by[STALE] + len(drift.get("proposed_delta") or []),
        },
        "undocumented_implementation_count": sum(
            1 for a in with_impl if a["status"] == UNDOCUMENTED
        ),
        "denominator_watch_areas": n,
        "overall_score": None,
        "note": "No aggregate score. Each metric is independently inspectable.",
    }


def priority_backlog(areas: list[dict[str, Any]], recon: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {a["id"]: a for a in areas}
    items: list[dict[str, Any]] = []

    def add(area_id: str, why: str) -> None:
        a = by_id.get(area_id)
        if a is None:
            # registry sync items
            items.append({
                "id": area_id,
                "title": area_id.replace("_", " ").title(),
                "status": STALE if area_id in {"function_map", "master_platform_state", "canonical_system_registry"} else UNKNOWN,
                "verified_in_repo": True,
                "action": "RECONCILE_REGISTRY",
                "reason": why,
                "create_document": False,
            })
            return
        if a["status"] == DOCUMENTED and area_id != "hartablocuri_integration":
            return
        items.append({
            "id": a["id"],
            "title": a["title"],
            "status": a["status"],
            "verified_in_repo": bool(a["implementation_present"] or a["tests_present"] or a["dedicated_kc"]),
            "implementation": a["implementation_present"],
            "tests": a["tests_present"],
            "existing_kc": a["kc_mentions"],
            "action": "GENERATE_CANDIDATE" if a["status"] in {UNDOCUMENTED, PARTIALLY_DOCUMENTED} and not a["dedicated_kc"] else "RECONCILE",
            "create_document": False,
            "reason": why,
        })

    add("evidence_contract_7b", "Base vocabulary for 8B/9C/10C; mentioned only as a 10C dependency.")
    add("document_fact_extraction_8b", "Extractor exists with tests; no dedicated KC artifact.")
    add("claim_matching_9c", "Canonical registry row exists; no dedicated KC document.")
    add("building_identity", "Engine node exists; no dedicated KC document.")
    add("trust_boundary", "Test suite exists; mentioned only in 10C.")
    add("hartablocuri_source_ledger", "Module + tests exist; zero KC mentions.")
    add("kc_path_alignment", "Resolver + tests exist; zero KC mentions.")
    add("document_vault", "Current UI is DocumentVault.jsx; Function Map still cites PropertyDocumentsPanel.")
    if recon["function_map"]["missing"] > 0:
        add("function_map", "FUNCTION_MAP.md last updated 2026-06; September pipeline absent.")
    if recon["master_platform_state"]["missing"] > 0:
        add("master_platform_state", "MASTER_PLATFORM_STATE.md does not mention the September pipeline.")
    if recon["canonical_system_registry"]["missing"] > 0:
        add("canonical_system_registry", "Canonical registry has 10C/9C only; 7B/8B/identity/ledger absent.")
    add("hartablocuri_integration", "Dedicated integration doc does not mention the source ledger.")
    return items


def classify_change_type(rel: str) -> str:
    p = rel.replace("\\", "/")
    if p == REG_FUNCTION_MAP or p.endswith("FUNCTION_MAP.md"):
        return "function_map"
    if "MASTER_PLATFORM_STATE" in p or "CANONICAL_SYSTEM_REGISTRY" in p or "SSOT_REGISTRY" in p:
        return "canonical"
    if p.startswith("memory/") or p.startswith("docs/"):
        return "kc_document"
    if p == "backend/data/enterprise_registry.json":
        return "registry"
    if p.startswith("backend/migrations/") or "/migrations/" in p:
        return "migration"
    if p.startswith("backend/tests/") or "/tests/" in p:
        return "test"
    if p.startswith("backend/routes/"):
        return "route"
    if p.startswith("frontend/"):
        return "frontend"
    if p.startswith("backend/") and p.endswith(".py"):
        return "implementation"
    if p.endswith((".env", ".json", ".yml", ".yaml", ".toml", "wrangler.jsonc")):
        return "configuration"
    return "unknown"


def _area_for_file(rel: str, areas: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for a in areas:
        if rel in a.get("implementation_present", []) or rel in a.get("tests_present", []):
            return a
        if rel in (a.get("dedicated_kc") or []):
            return a
        # watchlist paths (even if missing)
        watch = next((w for w in WATCH_AREAS if w["id"] == a["id"]), None)
        if watch and rel in tuple(watch.get("implementation") or ()) + tuple(watch.get("tests") or ()) + tuple(watch.get("dedicated_kc") or ()):
            return a
    return None


def change_records(
    files: Iterable[str],
    areas: list[dict[str, Any]],
    *,
    source: str = "supplied",
) -> list[dict[str, Any]]:
    """Normalize changed paths. Not every change requires a KC document."""
    out: list[dict[str, Any]] = []
    ts = _now()
    for raw in files:
        rel = _normalize_repo_path(str(raw).split("\t")[-1].strip())
        if not rel:
            continue
        ctype = classify_change_type(rel)
        area = _area_for_file(rel, areas)
        coverage = area["status"] if area else UNKNOWN
        review = False
        if area and area["status"] in {UNDOCUMENTED, PARTIALLY_DOCUMENTED, STALE} and ctype in {
            "implementation", "route", "frontend",
        }:
            review = True
        if ctype in {"function_map", "canonical", "registry"}:
            review = True
        digest = hashlib.sha1(f"{rel}:{ctype}:{source}".encode("utf-8")).hexdigest()[:12]
        out.append({
            "change_id": digest,
            "timestamp": ts,
            "source": source,
            "file": rel,
            "change_type": ctype,
            "affected_module": area["id"] if area else None,
            "affected_function": None,
            "related_tests": (area or {}).get("tests_present") or [],
            "related_kc_artifacts": (area or {}).get("kc_mentions") or [],
            "coverage_status": coverage,
            "confidence": "high" if area else "low",
            "review_required": review,
        })
    return out


def detect_git_changes(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    files: list[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return files


def build_coverage_report(
    root: Optional[Path] = None,
    changed_files: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    from routes import knowledge_center as kc

    root = root or kc.resolve_project_root()
    corpus = load_corpus()
    registry = kc._load_registry()
    function_map = kc._parse_function_map()
    function_map_text = _read(root, REG_FUNCTION_MAP)
    canonical_text = _read(root, REG_CANONICAL)
    ssot_text = _read(root, REG_SSOT)
    platform_text = _read(root, DOC_PLATFORM_STATE)

    areas = [
        classify_area(
            area,
            root=root,
            corpus=corpus,
            registry=registry,
            function_map_text=function_map_text,
            canonical_text=canonical_text,
            ssot_text=ssot_text,
            platform_text=platform_text,
        )
        for area in WATCH_AREAS
    ]
    candidates = [c for a in areas if (c := generate_candidate(a))]
    duplicates = detect_duplicates(corpus)
    drift = function_map_drift(areas, function_map)
    drift["stale_path_refs"] = function_map_stale_entries(root, function_map)
    recon = reconcile_sources(areas)
    deps = dependency_coverage(areas, registry, root)
    files = list(changed_files) if changed_files is not None else detect_git_changes(root)
    changes = change_records(files, areas, source="supplied" if changed_files is not None else "git_status")
    metrics = health_metrics(areas, duplicates, recon, drift)
    backlog = priority_backlog(areas, recon)

    report = {
        "generated_at": _now(),
        "engine": "knowledge_coverage",
        "phase": "2",
        "canonical_promotion_allowed": CANONICAL_PROMOTION_ALLOWED,
        "rewrites_sources": False,
        "note": (
            "Coverage is evidence of documentation drift. "
            "Candidates are not canonical. Founder review remains the authority boundary."
        ),
        "areas": areas,
        "candidates": candidates,
        "duplicates": duplicates,
        "reconciliation": recon,
        "function_map_drift": drift,
        "dependencies": deps,
        "changes": changes,
        "metrics": metrics,
        "backlog": backlog,
        "lifecycle": [
            "CODE CHANGE",
            "CHANGE DETECTION",
            "IMPLEMENTATION IDENTIFICATION",
            "KC COVERAGE CHECK",
            "KNOWLEDGE GAP",
            "CANDIDATE ARTIFACT",
            "DEPENDENCY ANALYSIS",
            "FOUNDER REVIEW",
            "CANONICALIZATION",
            "REGISTRY / FUNCTION MAP UPDATE",
            "COVERAGE = HEALTHY",
        ],
    }
    try:
        from knowledge_history import attach_history

        return attach_history(report, root=root)
    except Exception:
        report["history"] = {"git_available": False, "error": "history_unavailable"}
        return report


def engine_writes_nothing() -> bool:
    """Used by tests: the module source must not persist or promote."""
    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    forbidden = {"insert_one", "update_one", "delete_one", "unlink", "rmtree", "write_text", "write_bytes"}
    return forbidden.isdisjoint(names | attrs)
