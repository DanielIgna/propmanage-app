"""Enterprise Knowledge Center — EXECUTION ORDER 002 + Refinements (R2–R4, R7, R8).
Acces exclusiv Founder (OWNER_EMAIL). Read-only asupra guvernanței.

Lifecycle automat (R2/R3): Draft / Review / Active / Archived — derivat EXCLUSIV din evidență:
referenced-by-code (Relationship Registry), verbatim Founder (aprobare), tokens de strategie
neactivată. Health Score (R4) + Quality Gate (R8) calculate din aceleași surse.
Relațiile provin DOAR din data/enterprise_registry.json (Truth Engine D161).
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from deps import require_role

router = APIRouter(prefix="/api/founder/knowledge", tags=["knowledge-center"])

OWNER_EMAILS = {e.strip().lower() for e in os.environ.get("OWNER_EMAIL", "").split(",") if e.strip()}
MEMORY_ROOT = Path("/app/memory")
DOCS_ROOT = Path("/app/docs")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REGISTRY_PATH = DATA_DIR / "enterprise_registry.json"
WIDGETS_PATH = DATA_DIR / "widget_inspector.json"
ARCH_PATH = DATA_DIR / "architecture_blocks.json"

CATEGORY_ORDER = [
    "System Zero", "Constitution", "Board Directives", "Board Resolutions", "Execution Orders",
    "Enterprise Standards", "Enterprise Principles", "Enterprise Playbooks", "Executive Prompts",
    "CEO Mode", "AI Charters", "Enterprise Metrics", "Enterprise Health", "Enterprise Score",
    "Governance", "Strategy", "Roadmaps", "Architecture", "Platform Audits", "Registries", "Digital Twin", "Finance",
    "Case Library", "Memory",
]

PATH_RULES = [
    ("memory/prompts/SYSTEM_ZERO", "System Zero"),
    ("memory/prompts/ENTERPRISE_CEO_MODE", "CEO Mode"),
    ("memory/prompts/", "Executive Prompts"),
    ("memory/constitution/", "Constitution"),
    ("memory/board/directives/", "Board Directives"),
    ("memory/board/BOARD_RESOLUTIONS", "Board Resolutions"),
    ("memory/board/RESOLUTION_", "Board Resolutions"),
    ("memory/board/EXECUTION_ORDER", "Execution Orders"),
    ("memory/board/BOARD_LAWS", "Governance"),
    ("memory/board/BOARD_CHARTERS", "AI Charters"),
    ("memory/board/", "Board Directives"),
    ("memory/metrics/ENTERPRISE_SCORE", "Enterprise Score"),
    ("memory/metrics/ENTERPRISE_HEALTH", "Enterprise Health"),
    ("memory/metrics/", "Enterprise Metrics"),
    ("memory/governance/", "Governance"),
    ("memory/strategy/ROADMAP", "Roadmaps"),
    ("memory/strategy/", "Strategy"),
    ("memory/audits/", "Platform Audits"),
    ("memory/registries/", "Registries"),
]
NAME_RULES = [
    ("ENTERPRISE_STANDARDS", "Enterprise Standards"),
    ("ENTERPRISE_PLAYBOOKS", "Enterprise Playbooks"),
    ("ENTERPRISE_PRINCIPLES", "Enterprise Principles"),
    ("CHARTER", "AI Charters"),
    ("ARCHITECTURE", "Architecture"),
    ("DESIGN_SYSTEM", "Architecture"),
    ("ROADMAP", "Roadmaps"),
    ("PROPERTY_DNA", "Digital Twin"),
    ("PROPERTY_INTELLIGENCE", "Digital Twin"),
    ("GOVERNANCE", "Governance"),
    ("CONSTITUTIA", "Constitution"),
    ("VALUE_OFFICE", "Finance"),
    ("WAR_MAP", "Roadmaps"),
    ("CASE_LIBRARY", "Case Library"),
    ("DECISION_REGISTER", "Governance"),
    ("TECHNICAL_DEBT", "Architecture"),
]

# R3: strategii neactivate rămân Draft până la activare explicită de către Founder
DRAFT_TOKENS = ("GRAND_STRATEGY", "EVOLUTION_ENGINE", "EXPONENTIAL_GROWTH", "ROADMAP", "SCALING_PHASE")
# Documente-nucleu ale memoriei, aprobate implicit de guvernanță (R3: Expected Active)
CORE_ACTIVE_TOKENS = ("MEMORY_RULES", "INDEX.MD", "TEST_CREDENTIALS", "PRD.MD")

# ============================================================
# Enterprise Artifact Types — Infrastructure only (2026-07-31)
# ------------------------------------------------------------
# Prepară platforma pentru multiple tipuri de artefacte în Knowledge Center.
# Reguli:
#   - DOCUMENT rămâne default; NIMIC nu se schimbă pentru documentele existente.
#   - Nu se implementează încă REGISTRY / GRAPH / LEDGER / INDEX / CATALOG.
#   - Extensibil: adăugarea unui nou tip = un rând în PATH_ / NAME_ARTIFACT_TYPE_RULES.
#   - Backward-compatible: consumatorii care ignoră `artifact_type` continuă să funcționeze.
# ============================================================
ARTIFACT_TYPES = ("DOCUMENT", "REGISTRY", "GRAPH", "LEDGER", "INDEX", "CATALOG")
PATH_ARTIFACT_TYPE_RULES: list[tuple[str, str]] = [
    ("memory/registries/", "REGISTRY"),  # Canonical location for enterprise registries (first: SSOT_REGISTRY.md)
]
NAME_ARTIFACT_TYPE_RULES: list[tuple[str, str]] = []  # (uppercase_token, ARTIFACT_TYPE); reserved for future


def _artifact_type(rel: str) -> str:
    """Returnează tipul artefactului pentru o cale. Default DOCUMENT (backward-compatible)."""
    for prefix, atype in PATH_ARTIFACT_TYPE_RULES:
        if rel.startswith(prefix):
            return atype
    name = rel.rsplit("/", 1)[-1].upper()
    for token, atype in NAME_ARTIFACT_TYPE_RULES:
        if token in name:
            return atype
    return "DOCUMENT"


def _require_owner(user: dict) -> None:
    if (user.get("email") or "").lower() not in OWNER_EMAILS:
        raise HTTPException(403, "Enterprise Knowledge Center este disponibil exclusiv Fondatorului.")


def _categorize(rel: str) -> str:
    for prefix, cat in PATH_RULES:
        if rel.startswith(prefix):
            return cat
    name = rel.rsplit("/", 1)[-1].upper()
    for token, cat in NAME_RULES:
        if token in name:
            return cat
    return "Memory"


def _all_files():
    for root, label in ((MEMORY_ROOT, "memory"), (DOCS_ROOT, "docs")):
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            yield p, f"{label}/{p.relative_to(root)}"


def _load_registry() -> dict:
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"nodes": [], "edges": []}


def _reg_ctx() -> dict:
    reg = _load_registry()
    refs, edge_counts = {}, {}
    for n in reg["nodes"]:
        if n.get("ref"):
            refs[n["ref"]] = n["id"]
    for e in reg["edges"]:
        for nid in (e["source"], e["target"]):
            c = edge_counts.setdefault(nid, {"verified": 0, "total": 0})
            c["total"] += 1
            if e.get("verification_status") == "VERIFIED":
                c["verified"] += 1
    return {"reg": reg, "refs": refs, "edge_counts": edge_counts}


def _doc_meta(p: Path, rel: str, ctx: dict | None = None) -> dict:
    try:
        head = p.read_text(encoding="utf-8", errors="replace")[:1200]
    except Exception:  # noqa: BLE001
        head = ""
    title = rel.rsplit("/", 1)[-1]
    for m in re.finditer(r"^#\s*(.+)$", head, re.MULTILINE):
        cand = m.group(1).strip().lstrip("#").strip()
        if re.search(r"[A-Za-z0-9ĂÂÎȘȚăâîșț]", cand):
            title = cand
            break
    vm = re.search(r"(?:VERSION|VERSIUNE)[\s:]*v?([0-9]+(?:\.[0-9]+)?)", head, re.IGNORECASE)
    up = head.upper()
    rel_up = rel.upper()
    pending = "ÎN AȘTEPTAREA TEXTULUI VERBATIM" in up or "PENDING VERBATIM" in up
    founder_verbatim = "VERBATIM" in up and not pending
    updated = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()

    node_id = (ctx or {}).get("refs", {}).get(rel)
    referenced = node_id is not None
    ec = (ctx or {}).get("edge_counts", {}).get(node_id, {"verified": 0, "total": 0})

    # R2/R3 — lifecycle derivat din evidență
    if pending:
        status = "Draft"
    elif any(t in rel_up for t in DRAFT_TOKENS) and not referenced:
        status = "Draft"
    elif "ARCHIVE" in rel_up or "LEGACY_LOG" in rel_up:
        status = "Archived"
    elif referenced or founder_verbatim or any(t in rel_up for t in CORE_ACTIVE_TOKENS):
        status = "Active"
    else:
        status = "Review"

    # R4 — Health Score (doar factori măsurabili)
    h_ref = 35 if referenced else 0
    h_impl = round(min(ec["verified"], 5) / 5 * 25)
    h_ev = 20 if ec["verified"] > 0 else 0
    h_comp = 0 if pending else 20
    health = {"score": h_ref + h_impl + h_ev + h_comp,
              "referenced": h_ref, "implementation": h_impl, "evidence": h_ev, "completeness": h_comp,
              "confidence": "Measured" if referenced else ("Verified" if founder_verbatim else "Estimated")}

    return {
        "path": rel,
        "title": title[:160],
        "category": _categorize(rel),
        "artifact_type": _artifact_type(rel),
        "version": vm.group(1) if vm else "1.0",
        "status": status,
        "pending_verbatim": pending,
        "author": "Founder (verbatim)" if ("VERBATIM" in up) else "Executive Intelligence (derivat)",
        "approver": "Founder" if founder_verbatim else ("Executive Intelligence" if status == "Active" else None),
        "approved_at": updated if status == "Active" else None,
        "referenced_by_os": referenced,
        "registry_node": node_id,
        "health": health,
        "updated": updated,
        "size_bytes": p.stat().st_size,
    }


def _quality_gate(meta: dict, title_counts: Counter) -> dict:
    """R8 — Quality Gate: verificări automate; eșec critic → statusul rămâne Review."""
    name = meta["path"].rsplit("/", 1)[-1]
    checks = {
        "naming_consistency": bool(re.fullmatch(r"[A-Za-z0-9_.\-]+\.md", name)),
        "versioning": bool(meta.get("version")),
        "referenced_by_code": meta["referenced_by_os"],
        "duplicate_detection": title_counts.get(meta["title"], 1) <= 1,
        "not_pending": not meta["pending_verbatim"],
        "truth_engine_validation": meta["health"]["evidence"] > 0 or meta["author"].startswith("Founder"),
    }
    critical_failed = [k for k in ("duplicate_detection", "not_pending") if not checks[k]]
    passed_n = sum(1 for v in checks.values() if v)
    return {"checks": checks, "critical_failed": critical_failed,
            "passed": not critical_failed,
            "quality_score": round(passed_n / len(checks) * 100)}


def _doc_relationships(rel: str, reg: dict) -> dict:
    node = next((n for n in reg["nodes"] if n.get("ref") == rel), None)
    if not node:
        return {"node": None, "depends_on": [], "used_by": [], "note": "UNKNOWN — documentul nu are relații dovedite în registru (Truth Engine: nu inferăm)."}
    names = {n["id"]: n for n in reg["nodes"]}

    def enrich(edge, other_id):
        o = names.get(other_id, {})
        return {**edge, "other_id": other_id, "other_name": o.get("name", other_id),
                "other_type": o.get("type"), "other_ref": o.get("ref")}
    depends = [enrich(e, e["source"]) for e in reg["edges"] if e["target"] == node["id"]]
    used_by = [enrich(e, e["target"]) for e in reg["edges"] if e["source"] == node["id"]]
    return {"node": node, "depends_on": depends, "used_by": used_by, "note": None}


def _safe_resolve(rel: str) -> Path:
    if rel.startswith("memory/"):
        p = (MEMORY_ROOT / rel[len("memory/"):]).resolve()
        root = MEMORY_ROOT
    elif rel.startswith("docs/"):
        p = (DOCS_ROOT / rel[len("docs/"):]).resolve()
        root = DOCS_ROOT
    else:
        raise HTTPException(400, "Cale invalidă.")
    if root not in p.parents or p.suffix != ".md" or not p.exists():
        raise HTTPException(404, "Documentul nu există.")
    return p


def _ref_exists(rel: str) -> bool:
    try:
        _safe_resolve(rel)
        return True
    except HTTPException:
        return False


@router.get("/access")
async def founder_access(user=Depends(require_role("admin"))):
    return {"is_founder": (user.get("email") or "").lower() in OWNER_EMAILS}


@router.get("/artifact-types")
async def knowledge_artifact_types(user=Depends(require_role("admin"))):
    """Enterprise Artifact Type metadata (infrastructure only).

    Returnează:
      - types: enumul complet suportat.
      - default: tipul aplicat când nicio regulă nu match-uiește.
      - rules: regulile active (path + name); goale acum, rezervate viitorului.
      - contract: descriere concisă a fiecărui tip pentru AI context.
    """
    _require_owner(user)
    return {
        "types": list(ARTIFACT_TYPES),
        "default": "DOCUMENT",
        "rules": {
            "path": [{"prefix": p, "type": t} for p, t in PATH_ARTIFACT_TYPE_RULES],
            "name": [{"token": tok, "type": t} for tok, t in NAME_ARTIFACT_TYPE_RULES],
        },
        "contract": {
            "DOCUMENT": "Narrative artifact. Explains concepts, decisions, methodology. Prose-based.",
            "REGISTRY": "Structural artifact. Declares facts (topic → owner). Schema-first. Not implemented yet.",
            "GRAPH": "Relational artifact. Nodes + edges (dependencies, hierarchies). Not implemented yet.",
            "LEDGER": "Append-only artifact. Event / decision trail. Not implemented yet.",
            "INDEX": "Lookup artifact. Fast reverse mapping (name → path). Not implemented yet.",
            "CATALOG": "Enumeration artifact. Curated list with metadata. Not implemented yet.",
        },
        "note": "Infrastructure ready. Only DOCUMENT is populated today; other types remain reserved.",
    }


@router.get("/tree")
async def knowledge_tree(user=Depends(require_role("admin"))):
    _require_owner(user)
    ctx = _reg_ctx()
    docs = [_doc_meta(p, rel, ctx) for p, rel in _all_files()]
    title_counts = Counter(d["title"] for d in docs)
    cats: dict[str, list] = {}
    status_counts: dict[str, int] = {}
    artifact_type_counts: dict[str, int] = {t: 0 for t in ARTIFACT_TYPES}
    for meta in docs:
        gate = _quality_gate(meta, title_counts)
        if meta["status"] == "Active" and not gate["passed"]:
            meta["status"] = "Review"  # R8: gate critic eșuat → Review
        meta["quality"] = gate["quality_score"]
        status_counts[meta["status"]] = status_counts.get(meta["status"], 0) + 1
        atype = meta.get("artifact_type", "DOCUMENT")
        artifact_type_counts[atype] = artifact_type_counts.get(atype, 0) + 1
        cats.setdefault(meta["category"], []).append(meta)
    ordered = [c for c in CATEGORY_ORDER if c in cats] + [c for c in sorted(cats) if c not in CATEGORY_ORDER]
    recent = sorted(docs, key=lambda d: d["updated"], reverse=True)[:8]
    return {"total": len(docs), "status_counts": status_counts,
            "artifact_type_counts": artifact_type_counts, "recent": recent,
            "categories": [{"name": c, "count": len(cats[c]), "docs": cats[c]} for c in ordered]}


_TITLES_CACHE = {"key": None, "counter": Counter()}


def _title_counts(ctx: dict) -> Counter:
    files = list(_all_files())
    key = (len(files), max((p.stat().st_mtime for p, _ in files), default=0))
    if _TITLES_CACHE["key"] != key:
        _TITLES_CACHE["counter"] = Counter(_doc_meta(p, rel, ctx)["title"] for p, rel in files)
        _TITLES_CACHE["key"] = key
    return _TITLES_CACHE["counter"]


@router.get("/doc")
async def knowledge_doc(path: str = Query(...), user=Depends(require_role("admin"))):
    _require_owner(user)
    p = _safe_resolve(path)
    ctx = _reg_ctx()
    meta = _doc_meta(p, path, ctx)
    gate = _quality_gate(meta, _title_counts(ctx))
    if meta["status"] == "Active" and not gate["passed"]:
        meta["status"] = "Review"
    return {"meta": meta, "gate": gate,
            "content": p.read_text(encoding="utf-8", errors="replace"),
            "relationships": _doc_relationships(path, ctx["reg"])}


@router.get("/search")
async def knowledge_search(q: str = Query(..., min_length=2), user=Depends(require_role("admin"))):
    _require_owner(user)
    needle = q.lower()
    ctx = _reg_ctx()
    doc_hits = []
    for p, rel in _all_files():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            continue
        low = text.lower()
        idx = low.find(needle)
        title_hit = needle in rel.lower()
        if idx < 0 and not title_hit:
            continue
        snippet = ""
        if idx >= 0:
            line_start = text.rfind("\n", 0, idx) + 1
            line_end = text.find("\n", idx)
            snippet = text[line_start:line_end if line_end > 0 else idx + 160].strip()[:200]
        meta = _doc_meta(p, rel, ctx)
        doc_hits.append({"path": rel, "title": meta["title"], "category": meta["category"],
                         "status": meta["status"], "snippet": snippet,
                         "occurrences": low.count(needle)})
        if len(doc_hits) >= 50:
            break
    node_hits = [n for n in ctx["reg"]["nodes"]
                 if needle in n["name"].lower() or needle in n.get("ref", "").lower()
                 or needle in n.get("description", "").lower()][:20]
    doc_hits.sort(key=lambda d: -d["occurrences"])
    return {"query": q, "documents": doc_hits, "registry_nodes": node_hits,
            "total": len(doc_hits) + len(node_hits)}


@router.get("/registry")
async def knowledge_registry(user=Depends(require_role("admin"))):
    _require_owner(user)
    reg = _load_registry()
    # R6: dacă evidența (fișierul referit) dispare → relația devine UNKNOWN, niciodată păstrată stale
    missing = {n["id"] for n in reg["nodes"]
               if (n.get("ref") or "").startswith(("memory/", "docs/")) and not _ref_exists(n["ref"])}
    for e in reg["edges"]:
        if e["source"] in missing or e["target"] in missing:
            e["verification_status"] = "UNKNOWN"
            e["confidence"] = "UNKNOWN"
    by_status: dict[str, int] = {}
    for e in reg["edges"]:
        by_status[e["verification_status"]] = by_status.get(e["verification_status"], 0) + 1
    by_type: dict[str, int] = {}
    for n in reg["nodes"]:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1
    return {**reg, "stats": {"nodes": len(reg["nodes"]), "edges": len(reg["edges"]),
                             "edges_by_status": by_status, "nodes_by_type": by_type}}


@router.get("/review")
async def founder_review(user=Depends(require_role("admin"))):
    """R7 — Founder Review Mode: tot ce necesită atenția Fondatorului, calculat live din evidență."""
    _require_owner(user)
    ctx = _reg_ctx()
    docs = [_doc_meta(p, rel, ctx) for p, rel in _all_files()]
    title_counts = Counter(d["title"] for d in docs)
    for d in docs:
        gate = _quality_gate(d, title_counts)
        if d["status"] == "Active" and not gate["passed"]:
            d["status"] = "Review"
        d["quality"] = gate["quality_score"]
    slim = lambda d: {k: d[k] for k in ("path", "title", "category", "status", "quality", "updated")}  # noqa: E731
    pending = [slim(d) for d in docs if d["pending_verbatim"]]
    drafts = [slim(d) for d in docs if d["status"] == "Draft" and not d["pending_verbatim"]]
    review = [slim(d) for d in docs if d["status"] == "Review"]
    duplicates = [slim(d) for d in docs if title_counts[d["title"]] > 1]
    broken_refs = [n for n in ctx["reg"]["nodes"]
                   if (n.get("ref") or "").startswith(("memory/", "docs/")) and not _ref_exists(n["ref"])]
    activation = sorted([d for d in review if d["quality"] >= 60], key=lambda d: -d["quality"])[:10]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pending_verbatim": pending,
        "drafts": drafts,
        "needs_review": review,
        "duplicates": duplicates,
        "broken_relations": broken_refs,
        "activation_suggestions": activation,
        "cleanup_suggestions": duplicates[:10],
        "top_priorities": (
            [{"action": "Retrimite textul verbatim", "count": len(pending)}] if pending else []
        ) + (
            [{"action": "Repară relațiile rupte din registry", "count": len(broken_refs)}] if broken_refs else []
        ) + (
            [{"action": "Revizuiește documentele nereferite", "count": len(review)}] if review else []
        ),
    }


@router.get("/inspector/{widget_id}")
async def inspector_widget(widget_id: str, user=Depends(require_role("admin"))):
    """Dashboard Inspector (Module 4): explică un widget cu evidență din Relationship Registry."""
    _require_owner(user)
    try:
        widgets = json.loads(WIDGETS_PATH.read_text(encoding="utf-8"))["widgets"]
    except Exception:  # noqa: BLE001
        raise HTTPException(500, "Inspector Registry indisponibil.")
    w = next((x for x in widgets if x["id"] == widget_id), None)
    if not w:
        raise HTTPException(404, "Widget necunoscut în Inspector Registry.")
    reg = _load_registry()
    names = {n["id"]: n for n in reg["nodes"]}

    def node(nid):
        return names.get(nid, {"id": nid, "name": nid, "type": None, "ref": None}) if nid else None
    out = dict(w)
    engine_id = w.get("engine")
    out["engine"] = node(engine_id)
    out["api"] = node(w.get("api"))
    out["prompt"] = node(w.get("prompt"))
    for key in ("database", "documents", "related_dashboards"):
        out[key] = [node(i) for i in w.get(key, [])]
    deps = []
    for e in reg["edges"]:
        if engine_id and (e["source"] == engine_id or e["target"] == engine_id):
            deps.append({**e, "source_name": names.get(e["source"], {}).get("name", e["source"]),
                         "target_name": names.get(e["target"], {}).get("name", e["target"])})
    out["dependencies"] = deps
    return out


@router.get("/architecture")
async def architecture_blocks(user=Depends(require_role("admin"))):
    """Architecture Navigator: blocurile platformei, cu fișiere reale din repo."""
    _require_owner(user)
    try:
        return json.loads(ARCH_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        raise HTTPException(500, "Architecture Registry indisponibil.")



# ═══════════════════════ MASTER FUNCTION MAP (Founder) ═══════════════════════
FUNCTION_MAP_PATH = MEMORY_ROOT / "registries" / "FUNCTION_MAP.md"

# Câmpuri parsate per funcție din FUNCTION_MAP.md (bullet-list markdown)
_FN_FIELDS = {
    "category", "subcategory", "lifecycle", "description",
    "frontend", "backend", "api", "db", "engine", "automation",
    "ai involvement", "human decision", "autonomy", "metric",
    "enterprise health domain", "kpi", "verification",
    "test", "production verified", "health", "risk", "owner",
    "knowledge center", "next action",
}


def _parse_function_map() -> dict:
    """Parsează FUNCTION_MAP.md → structură: {functions: [...], summary: {...}, matrix: [...]}.

    Format sursă: fiecare funcție este introdusă cu heading `### FN-XXX · Name`.
    Câmpurile sunt bullet-uri `- **Field**: value`. Matricea este un tabel markdown.
    """
    if not FUNCTION_MAP_PATH.exists():
        return {"functions": [], "matrix": [], "summary": {}, "meta": {}, "error": "FUNCTION_MAP.md not found"}
    text = FUNCTION_MAP_PATH.read_text(encoding="utf-8", errors="replace")

    # meta din frontmatter simplu (linii `**Key**: value` la top, before first ###)
    meta_zone = text.split("\n## ", 1)[0]
    meta = {}
    for m in re.finditer(r"\*\*([^*]+)\*\*:\s*([^\n]+)", meta_zone):
        meta[m.group(1).strip().lower()] = m.group(2).strip()

    # parse fiecare funcție
    functions = []
    for match in re.finditer(r"### (FN-\d+)\s*·?\s*([^\n]+)\n(.*?)(?=\n### FN-|\n---|\Z)",
                             text, re.DOTALL):
        fid, fname, body = match.group(1), match.group(2).strip(), match.group(3)
        fn = {"id": fid, "name": fname}
        # bulleted fields
        for line in body.splitlines():
            m = re.match(r"\s*-\s*\*\*([^*]+)\*\*:\s*(.*)$", line)
            if m:
                key = m.group(1).strip().lower()
                val = m.group(2).strip()
                # normalize keys with spaces → snake_case
                fn[key.replace(" ", "_")] = val
        functions.append(fn)

    # parse matrix (căutăm blocul MATRIX HIGH-LEVEL)
    matrix = []
    matrix_headers = []
    matrix_block = re.search(r"## MATRIX HIGH-LEVEL(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if matrix_block:
        lines = [l for l in matrix_block.group(1).splitlines() if l.strip().startswith("|")]
        # skip header + separator
        for i, line in enumerate(lines):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if i == 0:
                matrix_headers = cells
            elif i == 1:
                continue  # separator
            else:
                if len(cells) == len(matrix_headers):
                    row = dict(zip(matrix_headers, cells))
                    # extract function id from first cell (ex: "FN-001 Analytics&Growth" → id="FN-001")
                    first = cells[0]
                    m = re.match(r"(FN-\d+)", first)
                    if m:
                        row["function_id"] = m.group(1)
                    matrix.append(row)

    # summary
    lifecycle_counts: dict[str, int] = {}
    verification_counts: dict[str, int] = {}
    health_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    autonomy_counts: dict[str, int] = {}

    def _canon(v: str) -> str:
        # ia primul token înainte de " (" pentru bucketing canonic
        return (v.split("(", 1)[0].strip() or "UNKNOWN").upper()

    for fn in functions:
        for key, bucket in (
            ("lifecycle", lifecycle_counts), ("verification", verification_counts),
            ("health", health_counts), ("risk", risk_counts),
            ("category", category_counts), ("autonomy", autonomy_counts),
        ):
            v = _canon(fn.get(key, "UNKNOWN"))
            bucket[v] = bucket.get(v, 0) + 1

    summary = {
        "total": len(functions),
        "lifecycle": lifecycle_counts,
        "verification": verification_counts,
        "health": health_counts,
        "risk": risk_counts,
        "category": category_counts,
        "autonomy": autonomy_counts,
    }
    return {"meta": meta, "functions": functions, "matrix": matrix,
            "matrix_headers": matrix_headers, "summary": summary}


@router.get("/function-map")
async def function_map(user=Depends(require_role("admin"))):
    """Master Function/Capability Map — LIVE view din FUNCTION_MAP.md.

    Read-only. Zero DB. Zero business logic modification. Foloseste ca sursă unicul
    fișier canonic `/app/memory/registries/FUNCTION_MAP.md` (parseat markdown).
    Datele UNKNOWN/UNVERIFIED sunt returnate așa cum sunt — zero fabricație.
    """
    _require_owner(user)
    return _parse_function_map()


@router.get("/function-map/{fn_id}")
async def function_map_detail(fn_id: str, user=Depends(require_role("admin"))):
    """Detaliu individual pentru un Function ID (ex: FN-001)."""
    _require_owner(user)
    data = _parse_function_map()
    fn = next((f for f in data["functions"] if f["id"].upper() == fn_id.upper()), None)
    if not fn:
        raise HTTPException(404, f"Function {fn_id} nu există în FUNCTION_MAP.md")
    matrix_row = next((m for m in data["matrix"] if m.get("function_id") == fn["id"]), None)
    return {"function": fn, "matrix": matrix_row, "meta": data["meta"]}
