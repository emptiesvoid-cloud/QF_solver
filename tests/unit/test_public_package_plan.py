import json
import hashlib
from pathlib import Path

import pytest

from scripts.git_tools import git_run
from scripts.plan_public_package import (
    _relative_path,
    package_input_gaps,
    plan_public_package,
    preview_public_package_worktree,
    scan_selected_payloads,
    select_paths,
)
from scripts.review_vocabulary import FORBIDDEN_TERMS


def _selection(**overrides) -> dict:
    selection = {
        "include_exact": ["README.md"],
        "include_prefixes": ["src/"],
        "exclude_exact": [],
        "forbid_prefixes": ["tests/", "qualification/0_2_9/"],
    }
    selection.update(overrides)
    return selection


@pytest.mark.parametrize("value", ["/root.py", "../file", "src/../file", "src//file", "./file", "x:y", "src\\file"])
def test_paths_are_canonical_and_relative(value: str) -> None:
    with pytest.raises(ValueError):
        _relative_path(value)


def test_selection_is_explicit_and_deterministic() -> None:
    tree = {path: ("100644", "blob") for path in ["src/z.py", "README.md", "src/a.py", "tests/private.py"]}
    assert select_paths(tree, _selection()) == ["README.md", "src/a.py", "src/z.py"]


@pytest.mark.parametrize("selection", [
    _selection(include_exact=["missing.md"]),
    _selection(include_prefixes=["empty/"]),
    _selection(exclude_exact=["absent.py"]),
    _selection(include_exact=["README.md", "README.md"]),
    _selection(include_exact=["README.md", "tests/private.py"]),
])
def test_missing_or_forbidden_scope_fails_closed(selection: dict) -> None:
    tree = {path: ("100644", "blob") for path in ["README.md", "src/main.py", "tests/private.py"]}
    with pytest.raises(ValueError):
        select_paths(tree, selection)


@pytest.mark.parametrize("mode", ["120000", "commit"])
def test_non_regular_entries_are_rejected(mode: str) -> None:
    tree = {"README.md": ("100644", "blob"), "src/link.py": (mode, "blob")}
    with pytest.raises(ValueError, match="non-regular"):
        select_paths(tree, _selection())


def test_case_collisions_are_rejected() -> None:
    tree = {path: ("100644", "blob") for path in ["README.md", "src/a.py", "src/A.py"]}
    with pytest.raises(ValueError, match="collide"):
        select_paths(tree, _selection())


def test_strict_scan_does_not_waive_historical_tokens() -> None:
    path = "qualification/0_2_9/wp06f_closure_contract.json"
    report = scan_selected_payloads({path: FORBIDDEN_TERMS[0].encode()})
    assert report["status"] == "FAIL"
    assert report["findings"][0]["identifier"] == "review_vocabulary"


def test_strict_scan_still_detects_workstation_paths() -> None:
    payload = ("C:/" + "Users/fixture/private/model.json").encode()
    report = scan_selected_payloads({"src/model.py": payload})
    assert report["status"] == "FAIL"
    assert any(row["identifier"] == "workstation_path" for row in report["findings"])


def test_package_inputs_cannot_be_silently_excluded() -> None:
    metadata = b'''[project]
name = "qf-solver"
version = "0.2.8"
readme = "README.md"
license-files = ["LICENSE"]
[tool.setuptools.data-files]
qualification = ["qualification/benchmarks.json"]
'''
    assert package_input_gaps({"pyproject.toml": metadata}) == [
        "LICENSE", "README.md", "qualification/benchmarks.json",
    ]


def test_package_globs_require_all_matching_source_inputs() -> None:
    metadata = b'''[project]
name = "qf-solver"
version = "0.2.8"
[tool.setuptools.data-files]
examples = ["examples/*.json"]
'''
    payloads = {"pyproject.toml": metadata, "examples/a.json": b"{}"}
    sources = [*payloads, "examples/b.json", "examples/nested/c.json"]
    assert package_input_gaps(payloads, source_paths=sources) == ["examples/b.json"]
    payloads["examples/b.json"] = b"{}"
    assert package_input_gaps(payloads, source_paths=sources) == []


def test_package_glob_with_no_source_match_is_not_accepted() -> None:
    metadata = b'''[project]
name = "qf-solver"
version = "0.2.8"
[tool.setuptools.data-files]
examples = ["examples/*.json"]
'''
    assert package_input_gaps({"pyproject.toml": metadata}) == ["examples/*.json"]


def test_plan_uses_committed_blobs_without_touching_a_dirty_worktree(tmp_path: Path) -> None:
    for args in (["init"], ["config", "user.name", "Fixture"], ["config", "user.email", "fixture@example.org"]):
        git_run(args, cwd=tmp_path, check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("Owner review", encoding="utf-8")
    (tmp_path / "src/model.py").write_text("# source\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="qf-solver"\nversion="0.2.8"\n', encoding="utf-8")
    git_run(["add", "."], cwd=tmp_path, check=True)
    git_run(["commit", "-m", "fixture"], cwd=tmp_path, check=True)
    source = git_run(["rev-parse", "HEAD"], cwd=tmp_path, check=True, text=True).stdout.strip()
    contract_path = tmp_path / "draft.json"
    contract = {
        "status": "PREPARATION_ONLY", "source_sha": source,
        "selection": _selection(include_exact=["README.md", "pyproject.toml"]),
    }
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    (tmp_path / "README.md").write_text("local edits must stay", encoding="utf-8")
    before = git_run(["status", "--porcelain"], cwd=tmp_path, check=True).stdout
    report = plan_public_package(tmp_path, contract_path)
    assert report["status"] == "PREPARATION_ONLY"
    assert report["formal_execution_authorized"] is False
    assert report["whole_repository_gates_changed"] is False
    assert report["publication_performed"] is False
    assert report["missing_package_inputs"] == []
    assert report["selected_files"] == 3
    readme_row = next(row for row in report["mapping"] if row["path"] == "README.md")
    assert readme_row["sha256"] == hashlib.sha256(b"Owner review").hexdigest()
    assert report == plan_public_package(tmp_path, contract_path)
    assert git_run(["status", "--porcelain"], cwd=tmp_path, check=True).stdout == before
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "local edits must stay"
    contract["status"] = "EXECUTION_AUTHORIZED"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(ValueError, match="preparation contracts only"):
        plan_public_package(tmp_path, contract_path)


@pytest.fixture
def preview_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Synthetic package selection only; not a source-qualification contract."""
    for args in (["init"], ["config", "user.name", "Fixture"], ["config", "user.email", "fixture@example.org"], ["config", "core.autocrlf", "false"]):
        git_run(args, cwd=tmp_path, check=True)
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("Owner review\n", encoding="utf-8")
    (tmp_path / "src/model.py").write_text("# initial source\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="qf-solver"\nversion="0.2.8"\n', encoding="utf-8")
    git_run(["add", "."], cwd=tmp_path, check=True)
    git_run(["commit", "-m", "fixture"], cwd=tmp_path, check=True)
    source = git_run(["rev-parse", "HEAD"], cwd=tmp_path, check=True, text=True).stdout.strip()
    contract_path = tmp_path / "draft.json"
    contract_path.write_text(json.dumps({
        "status": "PREPARATION_ONLY", "source_sha": source,
        "selection": _selection(include_exact=["README.md", "pyproject.toml"]),
    }), encoding="utf-8")
    return tmp_path, contract_path


def test_preview_distinguishes_current_bytes_from_frozen_source(preview_fixture: tuple[Path, Path]) -> None:
    root, contract = preview_fixture
    (root / "README.md").write_text("analyzer report\n", encoding="utf-8")
    before = git_run(["status", "--porcelain"], cwd=root, check=True).stdout
    frozen = plan_public_package(root, contract)
    current = preview_public_package_worktree(root, contract)
    assert frozen["mapping"][0]["sha256"] != current["mapping"][0]["worktree_sha256"]
    assert current["status"] == "PASS_PREPARATION_WORKTREE_PREVIEW"
    assert current["changed_or_new_selected_files"] == ["README.md"]
    assert current["evidence_kind"] == "CURRENT_BYTES_PREVIEW_NOT_FORMAL_EXECUTION"
    assert current["formal_execution_authorized"] is False
    assert current["whole_repository_gates_changed"] is False
    assert current["archive_or_package_build_performed"] is False
    assert current == preview_public_package_worktree(root, contract)
    assert git_run(["status", "--porcelain"], cwd=root, check=True).stdout == before


def test_preview_reports_new_selected_source_without_fabricating_git_binding(preview_fixture: tuple[Path, Path]) -> None:
    root, contract = preview_fixture
    (root / "src/new.py").write_text("# candidate source\n", encoding="utf-8")
    report = preview_public_package_worktree(root, contract)
    row = next(row for row in report["mapping"] if row["path"] == "src/new.py")
    assert row["absent_from_preparation_baseline"] is True
    assert row["preparation_baseline_git_blob"] is None
    assert report["formal_execution_authorized"] is False


def test_preview_is_not_an_escape_from_strict_scans(preview_fixture: tuple[Path, Path]) -> None:
    root, contract = preview_fixture
    (root / "README.md").write_text("C:/" + "Users/fixture/private/model.json\n", encoding="utf-8")
    report = preview_public_package_worktree(root, contract)
    assert report["status"] == "FAIL_CLOSED_PREPARATION_PREVIEW"
    assert any(row["identifier"] == "workstation_path" for row in report["public_source_scan"]["findings"])


def test_preview_cannot_silently_drop_a_missing_selected_file(preview_fixture: tuple[Path, Path]) -> None:
    root, contract = preview_fixture
    (root / "src/model.py").unlink()
    with pytest.raises(FileNotFoundError):
        preview_public_package_worktree(root, contract)


def test_preview_cannot_be_treated_as_an_execution_authorization(preview_fixture: tuple[Path, Path]) -> None:
    root, contract = preview_fixture
    data = json.loads(contract.read_text(encoding="utf-8"))
    data["status"] = "EXECUTION_AUTHORIZED"
    contract.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="preparation contracts only"):
        preview_public_package_worktree(root, contract)
