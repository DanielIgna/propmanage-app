"""KC Autonomy Phase 2 — coverage / drift engine. No DB. No corpus writes. No promotion."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

import knowledge_coverage as cov
from routes import knowledge_center as kc

REPO = Path(__file__).resolve().parents[2]


def test_coverage_detects_documented_10c():
    report = cov.build_coverage_report(root=REPO)
    ten = next(a for a in report["areas"] if a["id"] == "document_property_support_10c")
    assert ten["status"] == cov.DOCUMENTED
    assert "memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md" in ten["dedicated_kc"]
    assert ten["implementation_present"]
    assert ten["tests_present"]


def test_generated_phase_audit_is_not_a_coverage_mention():
    assert cov.is_generated_phase_audit("docs/audits/PHASE_6_GOVERNANCE_INTEGRATION_AUDIT.md") is True
    assert cov.is_generated_phase_audit("memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md") is False
    report = cov.build_coverage_report(root=REPO)
    ledger = next(a for a in report["areas"] if a["id"] == "hartablocuri_source_ledger")
    assert all("PHASE_6" not in p for p in ledger["kc_mentions"])
    assert ledger["status"] == cov.UNDOCUMENTED


def test_undocumented_implementation_detection():
    report = cov.build_coverage_report(root=REPO)
    ledger = next(a for a in report["areas"] if a["id"] == "hartablocuri_source_ledger")
    assert ledger["implementation_present"]
    assert ledger["tests_present"]
    assert ledger["kc_mentions"] == []
    assert ledger["status"] == cov.UNDOCUMENTED
    path_align = next(a for a in report["areas"] if a["id"] == "kc_path_alignment")
    assert path_align["status"] == cov.UNDOCUMENTED
    assert path_align["tests_present"]


def test_partial_layers_are_not_wrong():
    report = cov.build_coverage_report(root=REPO)
    by_id = {a["id"]: a for a in report["areas"]}
    assert by_id["evidence_contract_7b"]["status"] == cov.PARTIALLY_DOCUMENTED
    assert by_id["document_fact_extraction_8b"]["status"] == cov.PARTIALLY_DOCUMENTED
    assert by_id["claim_matching_9c"]["status"] == cov.PARTIALLY_DOCUMENTED
    assert by_id["building_identity"]["status"] == cov.PARTIALLY_DOCUMENTED
    for key in ("evidence_contract_7b", "claim_matching_9c"):
        assert by_id[key]["note"]
        assert "not a product defect" in by_id[key]["note"]


def test_stale_registry_and_integration_detection():
    report = cov.build_coverage_report(root=REPO)
    by_id = {a["id"]: a for a in report["areas"]}
    assert by_id["hartablocuri_integration"]["status"] == cov.STALE
    assert any("hartablocuri_source_ledger" in p for p in by_id["hartablocuri_integration"]["missing_required_mentions"])
    assert by_id["document_vault"]["status"] == cov.STALE
    stale_fn = report["function_map_drift"]["stale_path_refs"]
    assert any(s.get("function_id") == "FN-005" for s in stale_fn)
    assert report["reconciliation"]["function_map"]["missing"] >= 1
    assert report["reconciliation"]["master_platform_state"]["missing"] >= 1


def test_duplicate_detection_does_not_delete():
    report = cov.build_coverage_report(root=REPO)
    groups = report["duplicates"]
    assert groups
    families = " ".join(g["kind"] + " " + " ".join(g["paths"]) for g in groups)
    assert "MASTER_PLATFORM_STATE" in families
    assert any(g["kind"] in {"HISTORICAL_COPY", "VERSION_COPY", "SAME_TITLE_DIFFERENT_PATH", "TEMPLATE_TITLE"} for g in groups)
    for g in groups:
        assert "not delete" in g["proposal"].lower() or "No cleanup" in g["proposal"]
        assert g["canonical"] is False
    tree = ast.parse(Path(cov.__file__).read_text(encoding="utf-8"))
    calls = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "unlink" not in calls
    assert "rmtree" not in calls


def test_candidate_generation_is_not_canonical():
    report = cov.build_coverage_report(root=REPO)
    ids = {c["candidate_id"] for c in report["candidates"]}
    assert "cand:hartablocuri_source_ledger" in ids
    assert "cand:evidence_contract_7b" in ids
    assert "cand:document_property_support_10c" not in ids
    for c in report["candidates"]:
        assert c["canonical"] is False
        assert c["auto_promotable"] is False
        assert c["requires_founder_review"] is True
        assert c["suggested_kc_path"].startswith("memory/")


def test_dependency_gap_detection():
    report = cov.build_coverage_report(root=REPO)
    by_id = {d["id"]: d for d in report["dependencies"]}
    ten = by_id["document_property_support_10c"]
    assert ten["registry_nodes"]
    assert any(r["mapped_type"] == cov.REL_GOVERNS for r in ten["relations"])
    assert all(r["invented"] is False for r in ten["relations"])
    ledger = by_id["hartablocuri_source_ledger"]
    assert ledger["gap"] is True
    assert ledger["relations"] == []


def test_function_map_drift_is_a_delta_not_a_rewrite():
    report = cov.build_coverage_report(root=REPO)
    drift = report["function_map_drift"]
    assert drift["rewritten"] is False
    delta_ids = {d["id"] for d in drift["proposed_delta"]}
    assert "evidence_contract_7b" in delta_ids
    assert "hartablocuri_source_ledger" in delta_ids
    for d in drift["proposed_delta"]:
        assert d["canonical"] is False
        assert d["proposed_action"] == "ADD_ROW_CANDIDATE"
    original = (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8")
    assert "Last update**: 2026-06" in original


def test_canonical_promotion_guard():
    with pytest.raises(cov.CanonicalPromotionForbidden):
        cov.promote_candidate({"candidate_id": "cand:x"})
    with pytest.raises(cov.CanonicalPromotionForbidden):
        cov.write_canonical_document("memory/audits/NO.md", "# x")
    with pytest.raises(cov.CanonicalPromotionForbidden):
        cov.delete_kc_artifact("memory/INDEX.md")
    assert cov.CANONICAL_PROMOTION_ALLOWED is False
    report = cov.build_coverage_report(root=REPO)
    assert report["canonical_promotion_allowed"] is False
    assert report["rewrites_sources"] is False


def test_provenance_preservation_and_no_destructive_update():
    before_index = (REPO / "memory/INDEX.md").read_text(encoding="utf-8")
    before_fn = (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8")
    before_reg = (REPO / "backend/data/enterprise_registry.json").read_text(encoding="utf-8")
    cov.build_coverage_report(root=REPO)
    assert (REPO / "memory/INDEX.md").read_text(encoding="utf-8") == before_index
    assert (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8") == before_fn
    assert (REPO / "backend/data/enterprise_registry.json").read_text(encoding="utf-8") == before_reg
    tree = ast.parse(Path(cov.__file__).read_text(encoding="utf-8"))
    writes = {
        type(n).__name__
        for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and n.attr in {"write_text", "write_bytes", "unlink", "mkdir"}
    }
    assert writes == set()
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "insert_one" not in names
    assert "update_one" not in names
    assert cov.engine_writes_nothing() is True


def test_change_records_do_not_require_a_document_for_every_file():
    areas = cov.build_coverage_report(root=REPO)["areas"]
    recs = cov.change_records(
        [
            "backend/evidence_semantics.py",
            "backend/tests/test_evidence_contract_alignment_iter234.py",
            "frontend/src/pages/clientv2/DocumentVault.jsx",
            "memory/registries/FUNCTION_MAP.md",
            "frontend/src/setupProxy.js",
        ],
        areas,
        source="supplied",
    )
    by_file = {r["file"]: r for r in recs}
    assert by_file["backend/evidence_semantics.py"]["change_type"] == "implementation"
    assert by_file["backend/evidence_semantics.py"]["review_required"] is True
    assert by_file["backend/evidence_semantics.py"]["affected_module"] == "evidence_contract_7b"
    assert by_file["backend/tests/test_evidence_contract_alignment_iter234.py"]["change_type"] == "test"
    assert by_file["backend/tests/test_evidence_contract_alignment_iter234.py"]["review_required"] is False
    assert by_file["memory/registries/FUNCTION_MAP.md"]["change_type"] == "function_map"
    assert by_file["memory/registries/FUNCTION_MAP.md"]["review_required"] is True
    assert by_file["frontend/src/setupProxy.js"]["review_required"] is False
    assert by_file["frontend/src/setupProxy.js"]["affected_module"] is None


def test_health_metrics_have_no_overall_score():
    report = cov.build_coverage_report(root=REPO)
    m = report["metrics"]
    assert m["overall_score"] is None
    assert "knowledge_coverage" in m
    assert "undocumented_implementation_count" in m
    assert m["undocumented_implementation_count"] >= 2
    assert report["lifecycle"][0] == "CODE CHANGE"
    assert report["lifecycle"][-1] == "COVERAGE = HEALTHY"
    assert "FOUNDER REVIEW" in report["lifecycle"]


def test_backlog_is_verified_and_does_not_create_docs():
    report = cov.build_coverage_report(root=REPO)
    ids = [b["id"] for b in report["backlog"]]
    assert ids[0] == "evidence_contract_7b"
    assert "hartablocuri_source_ledger" in ids
    assert "document_property_support_10c" not in ids
    for b in report["backlog"]:
        assert b["create_document"] is False
        assert b["verified_in_repo"] is True


def test_kc_lifecycle_and_tree_contract_unchanged():
    src = inspect.getsource(kc._doc_meta)
    assert "Draft" in src and "Review" in src and "Active" in src
    assert kc.PATH_ARTIFACT_TYPE_RULES == [("memory/registries/", "REGISTRY")]
    files = list(kc._all_files())
    assert len(files) >= 300
    assert all(rel.startswith(("memory/", "docs/")) for _, rel in files)


def test_coverage_endpoints_are_founder_only_and_registered():
    routes = {getattr(r, "path", "") for r in kc.router.routes}
    assert "/api/founder/knowledge/coverage" in routes
    assert "/api/founder/knowledge/coverage/changes" in routes
    src = inspect.getsource(kc.knowledge_coverage_report)
    assert "_require_owner" in src
    assert "build_coverage_report" in src
