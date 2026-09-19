"""KC path alignment — same Git SSOT locally and under /app. No DB. No corpus writes."""
from __future__ import annotations

import ast
import inspect
import json
import os
from pathlib import Path

import pytest

from routes import knowledge_center as kc

REPO = Path(__file__).resolve().parents[2]


def _count_md(root: Path) -> int:
    if not root.is_dir():
        return 0
    return sum(1 for _ in root.rglob("*.md"))


def test_detected_repo_root_has_memory_and_docs():
    root = kc.resolve_project_root()
    assert root.resolve() == REPO.resolve()
    assert (root / "memory").is_dir()
    assert (root / "docs").is_dir()


def test_app_absent_falls_back_to_repository_root():
    assert not Path("/app").exists()
    assert kc.resolve_project_root().resolve() == REPO.resolve()
    assert kc.resolve_memory_root().resolve() == (REPO / "memory").resolve()
    assert kc.resolve_docs_root().resolve() == (REPO / "docs").resolve()


def test_emergent_style_project_root_via_env(tmp_path, monkeypatch):
    app = tmp_path / "app"
    (app / "memory").mkdir(parents=True)
    (app / "docs").mkdir(parents=True)
    (app / "memory" / "note.md").write_text("# Note\n", encoding="utf-8")
    (app / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    monkeypatch.setenv("KC_PROJECT_ROOT", str(app))
    assert kc.resolve_project_root().resolve() == app.resolve()
    assert kc.resolve_memory_root().resolve() == (app / "memory").resolve()
    assert kc.resolve_docs_root().resolve() == (app / "docs").resolve()
    rels = {rel for _, rel in kc._all_files()}
    assert rels == {"memory/note.md", "docs/guide.md"}


def test_custom_memory_and_docs_env(tmp_path, monkeypatch):
    mem = tmp_path / "custom_memory"
    docs = tmp_path / "custom_docs"
    mem.mkdir()
    docs.mkdir()
    (mem / "a.md").write_text("# A\n", encoding="utf-8")
    (docs / "b.md").write_text("# B\n", encoding="utf-8")
    monkeypatch.setenv("KC_MEMORY_ROOT", str(mem))
    monkeypatch.setenv("KC_DOCS_ROOT", str(docs))
    assert kc.resolve_memory_root().resolve() == mem.resolve()
    assert kc.resolve_docs_root().resolve() == docs.resolve()
    rels = sorted(rel for _, rel in kc._all_files())
    assert rels == ["docs/b.md", "memory/a.md"]


def test_missing_memory_is_skipped(tmp_path, monkeypatch):
    root = tmp_path / "only_docs"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "x.md").write_text("# X\n", encoding="utf-8")
    monkeypatch.setenv("KC_PROJECT_ROOT", str(root))
    monkeypatch.delenv("KC_MEMORY_ROOT", raising=False)
    monkeypatch.delenv("KC_DOCS_ROOT", raising=False)
    rels = [rel for _, rel in kc._all_files()]
    assert rels == ["docs/x.md"]
    assert not kc.resolve_memory_root().exists()


def test_missing_docs_is_skipped(tmp_path, monkeypatch):
    root = tmp_path / "only_memory"
    (root / "memory").mkdir(parents=True)
    (root / "memory" / "y.md").write_text("# Y\n", encoding="utf-8")
    monkeypatch.setenv("KC_PROJECT_ROOT", str(root))
    monkeypatch.delenv("KC_MEMORY_ROOT", raising=False)
    monkeypatch.delenv("KC_DOCS_ROOT", raising=False)
    rels = [rel for _, rel in kc._all_files()]
    assert rels == ["memory/y.md"]


def test_combined_scan_when_both_exist(tmp_path, monkeypatch):
    root = tmp_path / "both"
    (root / "memory").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)
    (root / "memory" / "m.md").write_text("# M\n", encoding="utf-8")
    (root / "docs" / "d.md").write_text("# D\n", encoding="utf-8")
    monkeypatch.setenv("KC_PROJECT_ROOT", str(root))
    rels = {rel for _, rel in kc._all_files()}
    assert rels == {"memory/m.md", "docs/d.md"}


def test_registry_classification_unchanged():
    assert kc.PATH_ARTIFACT_TYPE_RULES == [("memory/registries/", "REGISTRY")]
    assert kc.NAME_ARTIFACT_TYPE_RULES == []
    assert kc._artifact_type("memory/registries/SSOT_REGISTRY.md") == "REGISTRY"
    assert kc._artifact_type("memory/audits/FAZA_10C_DOCUMENT_PROPERTY_SUPPORT.md") == "DOCUMENT"
    assert kc._artifact_type("docs/OPERATING_MANUAL.md") == "DOCUMENT"
    assert "GRAPH" not in {kc._artifact_type(rel) for _, rel in kc._all_files()}


def test_status_classification_unchanged():
    src = inspect.getsource(kc._doc_meta)
    assert "Draft" in src and "Review" in src and "Active" in src and "Archived" in src
    assert "DRAFT_TOKENS" in inspect.getsource(kc)
    assert "CORE_ACTIVE_TOKENS" in inspect.getsource(kc)
    pending = {"_id": "x"}
    # lifecycle still derived from evidence, not a DB field
    tree = ast.parse(inspect.getsource(kc))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "insert_one" not in names


def test_no_db_dependency():
    src = inspect.getsource(kc)
    assert "from db" not in src
    assert "import db" not in src
    assert "pymongo" not in src
    assert "insert_one" not in src
    assert "update_one" not in src


def test_nul_env_is_rejected():
    assert kc._as_existing_or_candidate_dir("/tmp/ok\x00/evil") is None


def test_env_file_is_not_used_as_root(tmp_path, monkeypatch):
    f = tmp_path / "not_a_dir"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setenv("KC_MEMORY_ROOT", str(f))
    assert kc.resolve_memory_root().resolve() == (REPO / "memory").resolve()


def test_safe_resolve_rejects_traversal():
    with pytest.raises(Exception) as ei:
        kc._safe_resolve("memory/../docs/OPERATING_MANUAL.md")
    assert ei.value.status_code in {400, 404}
    with pytest.raises(Exception) as ej:
        kc._safe_resolve("../../etc/passwd")
    assert ej.value.status_code == 400


def test_api_paths_are_relative_not_absolute():
    files = list(kc._all_files())
    assert files
    for _p, rel in files[:20]:
        assert rel.startswith(("memory/", "docs/"))
        assert not rel.startswith("/")
        assert "/Users/" not in rel
        assert not rel.startswith("/app/")


def test_workspace_scan_matches_real_corpus():
    expected = _count_md(REPO / "memory") + _count_md(REPO / "docs")
    got = list(kc._all_files())
    assert len(got) == expected
    assert expected > 0
    types = [kc._artifact_type(rel) for _, rel in got]
    assert types.count("REGISTRY") == sum(
        1 for _, rel in got if rel.startswith("memory/registries/")
    )
    assert types.count("DOCUMENT") == expected - types.count("REGISTRY")


def test_registry_json_path_independent_of_kc_roots(monkeypatch, tmp_path):
    monkeypatch.setenv("KC_PROJECT_ROOT", str(tmp_path))
    assert kc.REGISTRY_PATH.exists()
    assert kc.REGISTRY_PATH.parent.name == "data"
    data = kc._load_registry()
    assert "nodes" in data and "edges" in data
    assert len(data["nodes"]) >= 1


def test_doc_retrieval_memory_and_docs():
    mem = kc._safe_resolve("memory/INDEX.md")
    docs = kc._safe_resolve("docs/OPERATING_MANUAL.md")
    assert mem.is_file() and mem.suffix == ".md"
    assert docs.is_file() and docs.suffix == ".md"
    assert mem.read_text(encoding="utf-8", errors="replace")
    assert docs.read_text(encoding="utf-8", errors="replace")


def test_function_map_follows_memory_root():
    p = kc._function_map_path()
    assert p.name == "FUNCTION_MAP.md"
    assert p.parent.name == "registries"
    assert p.exists()
