"""KC Autonomy Phase 5 — migration reconciliation. No corpus writes."""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

import knowledge_reconciliation as rec
from routes import knowledge_center as kc

REPO = Path(__file__).resolve().parents[2]


def _has_ref(ref: str) -> bool:
    r = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", ref], capture_output=True)
    return r.returncode == 0


requires_remotes = pytest.mark.skipif(
    not (_has_ref("emergent/main") and _has_ref("origin/main")),
    reason="emergent/main and origin/main refs required",
)


@requires_remotes
def test_five_emergent_only_commits():
    hashes = rec.exclusive_commit_hashes(REPO, rec.EMERGENT_REF, rec.LOCAL_REF)
    assert len(hashes) == 5
    assert hashes[0].startswith("eadb12e")
    assert hashes[-1].startswith("2f71a85")
    inspected = [rec.inspect_commit(REPO, h) for h in hashes]
    subjects = [c["subject"] for c in inspected]
    assert any("Dump BSON" in s for s in subjects)
    assert any("Descarcă dump BSON" in s for s in subjects)
    assert sum("Auto-generated changes" in s for s in subjects) == 3
    bson = next(c for c in inspected if "Dump BSON nativ" in c["subject"])
    assert "backend/backup_service.py" in bson["files_modified"]
    assert "backend/routes/admin_backups.py" in bson["files_modified"]
    assert rec.KIND_PRODUCT_CODE in bson["kinds"]
    assert rec.KIND_KNOWLEDGE in bson["kinds"]
    assert bson["migration_state"] == rec.MIG_REMOTE_ONLY
    assert bson["lost"] is False
    assert bson["likely_origin"] == "EMERGENT"
    assert bson["parent"].startswith("0953203")
    tooling = [c for c in inspected if c["files_modified"] == [".emergent/emergent.yml"]]
    assert len(tooling) == 3
    for c in tooling:
        assert c["kinds"] == [rec.KIND_EMERGENT_TOOLING]
        assert c["migration_state"] in {rec.MIG_REMOTE_ONLY, rec.MIG_INTENTIONALLY_REMOVED}
        assert c["lost"] is False
    button = next(c for c in inspected if "Descarcă dump BSON" in c["subject"])
    assert "frontend/src/pages/admin/MorningBriefing.jsx" in button["files_modified"]
    assert button["migration_state"] == rec.MIG_REMOTE_ONLY


@requires_remotes
def test_local_only_commits_vs_origin():
    hashes = rec.exclusive_commit_hashes(REPO, rec.LOCAL_REF, rec.ORIGIN_REF)
    assert len(hashes) == 2
    assert hashes[0].startswith("b03a9ba")
    assert hashes[1].startswith("12db435")
    align = rec.inspect_commit(REPO, hashes[0])
    assert "backend/tests/test_knowledge_center_path_alignment_iter239.py" in align["files_added"]
    assert rec.KIND_PRODUCT_CODE in align["kinds"]
    assert rec.KIND_PRODUCT_TEST in align["kinds"]
    ev = rec.inspect_commit(REPO, hashes[1])
    assert "backend/evidence_semantics.py" in ev["files_added"]
    assert "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md" in ev["files_added"]
    assert rec.KIND_KNOWLEDGE in ev["kinds"]
    assert ev["likely_origin"] == "CURSOR"


@requires_remotes
def test_three_state_comparison():
    files = rec.file_level_baseline(REPO, rec.SIGNIFICANT_PATHS)
    matrix = rec.three_state_matrix(REPO, files)
    c = matrix["commits"]
    assert c["local_HEAD"].startswith("12db435")
    assert c["emergent_main"].startswith("2f71a85")
    assert c["origin_main"].startswith("252f562")
    assert len(c["emergent_only"]) == 5
    assert c["origin_only"] == []
    assert len(c["local_not_on_origin"]) == 2
    assert c["relation_vs_origin"] == "LOCAL_AHEAD"
    assert c["relation_vs_emergent"] == "DIVERGED"
    assert matrix["files"]["emergent_not_local"]
    assert all(p.startswith(".emergent/") for p in matrix["files"]["emergent_not_local"])
    assert matrix["files"]["origin_not_local"] == []
    assert "backend/evidence_semantics.py" in matrix["files"]["local_not_origin"]
    assert "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md" in matrix["files"]["local_not_origin"]
    ledger = next(s for s in files if s["path"].endswith("hartablocuri_source_ledger.py"))
    assert ledger["location"] == rec.LOC_LOCAL_ONLY
    assert ledger["present_local"] is True
    assert ledger["present_emergent"] is False
    assert ledger["present_origin"] is False
    backup = next(s for s in files if s["path"] == "backend/backup_service.py")
    assert backup["location"] == rec.LOC_DIVERGED
    assert backup["blobs"]["local"] != backup["blobs"]["emergent"]
    tool = next(s for s in files if s["path"] == ".emergent/emergent.yml")
    assert tool["location"] == rec.LOC_EMERGENT_ONLY
    assert tool["migration_state"] == rec.MIG_INTENTIONALLY_REMOVED
    assert tool["lost"] is False


def test_file_level_migration_classification():
    assert rec.classify_path_kind(".emergent/emergent.yml") == rec.KIND_EMERGENT_TOOLING
    assert rec.classify_path_kind("backend/evidence_semantics.py") == rec.KIND_PRODUCT_CODE
    assert rec.classify_path_kind("backend/tests/test_claim_matching_iter237.py") == rec.KIND_PRODUCT_TEST
    assert rec.classify_path_kind("memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md") == rec.KIND_KNOWLEDGE
    assert rec.classify_path_kind("memory/registries/FUNCTION_MAP.md") == rec.KIND_REGISTRY
    assert rec.classify_path_kind("docs/MASTER_ROADMAP_2026.md") == rec.KIND_DOCUMENTATION
    assert rec.classify_path_kind(".github/workflows/smoke-test.yml") == rec.KIND_CICD
    assert rec.classify_path_kind("frontend/public/sitemap.xml") == rec.KIND_GENERATED
    assert rec.classify_path_kind("cf-site/index.html") == rec.KIND_GENERATED


def test_working_tree_classification():
    wt = rec.working_tree_classification(REPO)
    paths = {r["path"]: r for r in wt["rows"]}
    assert "backend/knowledge_coverage.py" in paths
    assert paths["backend/knowledge_coverage.py"]["bucket"] == "phase2"
    assert paths["backend/knowledge_history.py"]["bucket"] == "phase4"
    assert paths["backend/knowledge_history.py"]["untracked"] is True
    assert paths["backend/tests/test_knowledge_coverage_iter240.py"]["bucket"] == "phase2"
    assert paths["backend/tests/test_knowledge_history_iter241.py"]["bucket"] == "phase4"
    recon = "backend/knowledge_reconciliation.py"
    if recon in paths:
        assert paths[recon]["bucket"] == "phase5"
    assert paths["frontend/src/pages/admin/KnowledgeCenter.jsx"]["bucket"] == "phase2"
    sitemaps = [p for p in paths if p.startswith("frontend/public/sitemap")]
    assert sitemaps
    assert all(paths[p]["bucket"] == "generated" for p in sitemaps)
    assert "lost" not in str(wt).lower() or "not" in wt["note"].lower()


@requires_remotes
def test_canonical_conflict_detection():
    conflicts = rec.canonical_conflicts(REPO)
    ids = {c["id"] for c in conflicts}
    assert "mps_family" in ids
    assert "function_map_vs_code" in ids
    assert "ten_b_design_only" in ids
    assert "hartablocuri_split" in ids
    for c in conflicts:
        assert c["winner_chosen"] is False
        assert c["canonicalized"] is False
        assert c["founder_decision_required"]


@requires_remotes
def test_baseline_classification():
    report = rec.build_reconciliation_report(root=REPO)
    by_id = {r["id"]: r for r in report["kc_baseline"]}
    assert by_id["document_property_support_10c"]["reconciliation"] == rec.MATCH
    assert by_id["evidence_contract_7b"]["reconciliation"] == rec.PARTIAL
    assert by_id["hartablocuri_source_ledger"]["reconciliation"] == rec.MISSING
    assert by_id["hartablocuri_integration"]["reconciliation"] == rec.STALE
    assert by_id["document_vault"]["reconciliation"] == rec.STALE
    docs = report["documentation_baseline"]
    assert "document_property_support_10c" in docs["A_implemented_documented"]
    assert "evidence_contract_7b" in docs["B_implemented_partial"]
    assert "hartablocuri_source_ledger" in docs["C_implemented_undocumented"]
    assert any("10B" in x for x in docs["D_documented_design_not_implemented"])
    pvk = {x["item"]: x for x in report["product_vs_knowledge"]}
    assert pvk["10B Document↔Property Contract"]["implementation_fact"] is False
    assert pvk["10B Document↔Property Contract"]["design_decision"] is True
    assert "Do not convert" in pvk["10B Document↔Property Contract"]["do_not_convert"]
    assert all(c["lost"] is False for c in report["emergent_only_commits"])
    assert report["lost_forbidden"] is True
    assert report["rewrites_sources"] is False
    qids = {q["id"] for q in report["founder_decision_queue"]}
    assert "fn_lifecycle" in qids and "commit_phase24" in qids and "bson_dump_remote" in qids


def test_no_destructive_operations():
    before_fn = (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8")
    before_mps = (REPO / "memory/audits/MASTER_PLATFORM_STATE.md").read_text(encoding="utf-8")
    before_ssot = (REPO / "memory/registries/SSOT_REGISTRY.md").read_text(encoding="utf-8")
    rec.working_tree_classification(REPO)
    rec.classify_path_kind("memory/registries/FUNCTION_MAP.md")
    assert (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8") == before_fn
    assert (REPO / "memory/audits/MASTER_PLATFORM_STATE.md").read_text(encoding="utf-8") == before_mps
    assert (REPO / "memory/registries/SSOT_REGISTRY.md").read_text(encoding="utf-8") == before_ssot
    assert rec.engine_writes_nothing() is True
    tree = ast.parse(Path(rec.__file__).read_text(encoding="utf-8"))
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "write_text" not in attrs
    assert "unlink" not in attrs
    assert "rmtree" not in attrs


def test_reconciliation_endpoint_registered():
    routes = {getattr(r, "path", "") for r in kc.router.routes}
    assert "/api/founder/knowledge/coverage/reconciliation" in routes
