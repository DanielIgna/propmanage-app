"""KC Autonomy Phase 4 — historical provenance. No DB. No corpus writes."""
from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

import knowledge_coverage as cov
import knowledge_history as hist
from routes import knowledge_center as kc

REPO = Path(__file__).resolve().parents[2]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


def _init_repo(tmp: Path) -> Path:
    _git(tmp, "init")
    _git(tmp, "config", "user.email", "emergent-agent-e1@example.com")
    _git(tmp, "config", "user.name", "emergent-agent-e1")
    (tmp / "backend").mkdir()
    (tmp / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(tmp, "add", "a.py")
    _git(tmp, "commit", "-m", "auto-commit for 11111111-2222-3333-4444-555555555555")
    return tmp


def test_git_first_seen_and_last_changed(tmp_path):
    repo = _init_repo(tmp_path)
    first = hist.file_git_index(repo, "a.py")
    assert first["state"] == "current"
    assert first["first_seen"]["commit_hash"]
    assert first["first_seen"]["origin"] == hist.ORIGIN_EMERGENT
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "a.py")
    _git(repo, "commit", "-m", "Auto-generated changes")
    again = hist.file_git_index(repo, "a.py")
    assert again["commit_count"] == 2
    assert again["last_changed"]["commit_hash"] != again["first_seen"]["commit_hash"]


def test_renamed_files(tmp_path):
    repo = _init_repo(tmp_path)
    _git(repo, "mv", "a.py", "b.py")
    _git(repo, "commit", "-m", "auto-commit for aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    idx = hist.file_git_index(repo, "b.py")
    assert idx["exists_now"] is True
    assert idx["renamed"] is True
    assert idx["rename_from"] == "a.py"
    assert idx["first_seen"]["commit_hash"]


def test_deleted_files(tmp_path):
    repo = _init_repo(tmp_path)
    _git(repo, "rm", "a.py")
    _git(repo, "commit", "-m", "auto-commit for deadbeef-dead-beef-dead-beefdeadbeef")
    idx = hist.file_git_index(repo, "a.py")
    assert idx["deleted"] is True
    assert idx["state"] == "deleted"
    assert idx["first_seen"] is not None


def test_origin_detection():
    em = hist.classify_origin("emergent-agent-e1", "e@x", "auto-commit for abcd")
    assert em["origin"] == hist.ORIGIN_EMERGENT
    assert em["confidence"] == "high"
    cur = hist.classify_origin("Igna Daniel", "d@x", "fix: align Knowledge Center paths")
    assert cur["origin"] == hist.ORIGIN_CURSOR
    assert cur["confidence"] == "high"
    hum = hist.classify_origin("Ada Popescu", "a@x", "Document vault UX polish")
    assert hum["origin"] == hist.ORIGIN_HUMAN
    unk = hist.classify_origin("", "", "")
    assert unk["origin"] == hist.ORIGIN_UNKNOWN
    # filename must not decide origin
    fake = hist.classify_origin("", "", "")
    assert fake["origin"] != hist.ORIGIN_CURSOR


def test_iteration_is_inferred_from_filename_only():
    info = hist.infer_iteration(["backend/tests/test_claim_matching_iter237.py"])
    assert info["inferred"] is True
    assert info["iteration"] == "iter237"
    assert info["source"] == "filename"
    none = hist.infer_iteration(["backend/evidence_semantics.py"])
    assert none["inferred"] is False
    assert none["iteration"] is None


def test_real_repo_first_seen_12db435():
    idx = hist.file_git_index(REPO, "backend/evidence_semantics.py")
    assert idx["first_seen"]
    assert idx["first_seen"]["commit_hash"].startswith("12db435")
    ten = hist.file_git_index(REPO, "backend/document_property_support.py")
    assert ten["first_seen"]["commit_hash"].startswith("12db435")
    assert hist.classify_origin(
        ten["first_seen"]["author"], ten["first_seen"]["email"], ten["first_seen"]["subject"]
    )["origin"] == hist.ORIGIN_CURSOR


def test_historical_coverage_not_error_before_code():
    report = hist.build_history_report(root=REPO)
    seven = next(a for a in report["areas"] if a["id"] == "evidence_contract_7b")
    assert seven["historical_state_before_code"] == hist.NOT_APPLICABLE
    assert "not a documentation error" in seven["historical_note"]
    assert seven["current_documentation_state"] == cov.PARTIALLY_DOCUMENTED
    assert seven["code_first_seen"]["commit_hash"].startswith("12db435")
    assert seven["iteration"]["inferred"] is True


def test_claim_provenance_10c_and_fn005():
    report = hist.build_history_report(root=REPO)
    by_id = {c["id"]: c for c in report["claims"]}
    ten = by_id["10c_orchestrator_no_persist"]
    assert ten["status"] == "MATCH"
    assert ten["canonical"] is False
    assert "document_property_support.py" in ten["code_paths"][0]
    assert ten["git"]["commit_hash"].startswith("12db435")
    fn = by_id["fn005_frontend_path"]
    assert fn["status"] == "STALE"
    assert fn["missing_code_paths"]
    assert fn["actual_code_paths"]


def test_documentation_latency():
    report = hist.build_history_report(root=REPO)
    ten = next(a for a in report["areas"] if a["id"] == "document_property_support_10c")
    assert ten["latency"]["code_to_kc_mention_days"] == 0
    assert ten["latency"]["code_to_dedicated_kc_days"] == 0
    seven = next(a for a in report["areas"] if a["id"] == "evidence_contract_7b")
    assert seven["latency"]["code_to_dedicated_kc"] == "none"
    assert seven["latency"]["code_to_kc_mention_days"] == 0


def test_function_map_and_mps_drift_not_rewritten():
    report = hist.build_history_report(root=REPO)
    fn = report["function_map_history"]
    assert fn["rewritten"] is False
    assert fn["first_seen"]["commit_hash"]
    assert any(d["id"] == "evidence_contract_7b" for d in fn["proposed_delta"])
    assert fn["fn_005"] and "PropertyDocumentsPanel" in "".join(fn["fn_005"]["missing_paths"])
    mps = report["mps_history"]
    assert mps["rewritten"] is False
    assert mps["living"] == "memory/audits/MASTER_PLATFORM_STATE.md"
    assert mps["implementations_postdating_living_mps"]
    assert any(x["area"] == "evidence_contract_7b" for x in mps["implementations_postdating_living_mps"])


def test_migration_comparison_does_not_invent_loss():
    report = hist.build_history_report(root=REPO)
    mig = report["migration"]
    assert mig["lost_claims"] == []
    assert "lost" not in (mig["cannot_trace"]["note"] or "").lower() or "not called lost" in mig["cannot_trace"]["note"].lower()
    assert "origin" in mig["remotes"] or "emergent" in mig["remotes"]
    assert report["lost_forbidden"] is True


def test_no_destructive_operations():
    before = (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8")
    hist.build_history_report(root=REPO)
    assert (REPO / "memory/registries/FUNCTION_MAP.md").read_text(encoding="utf-8") == before
    assert hist.engine_writes_nothing() is True
    tree = ast.parse(Path(hist.__file__).read_text(encoding="utf-8"))
    attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert "write_text" not in attrs
    assert "unlink" not in attrs


def test_coverage_report_attaches_history():
    report = cov.build_coverage_report(root=REPO)
    assert "history" in report
    assert report["history"]["engine"] == "knowledge_history"
    assert report["canonical_promotion_allowed"] is False


def test_history_endpoint_registered():
    routes = {getattr(r, "path", "") for r in kc.router.routes}
    assert "/api/founder/knowledge/coverage/history" in routes
