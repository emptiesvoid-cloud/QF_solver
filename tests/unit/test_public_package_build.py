"""Package-candidate tooling guards; synthetic inputs only, no solver campaign."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts.git_tools import git_run
from scripts.verify_public_package import (
    REQUIRED_TOOLS, archive_payloads, digest, frozen_inputs, installed_probe_command, verify_archives,
)


def _archives(root: Path, selected: dict[str, bytes], *, extra: str | None = None, version: str = "0.2.8") -> None:
    root.mkdir()
    with zipfile.ZipFile(root / "qf_solver-0.2.8-py3-none-any.whl", "w") as archive:
        for name, payload in selected.items():
            if name.startswith("src/"):
                archive.writestr(name.removeprefix("src/"), payload)
            elif name.startswith(("qualification/", "examples/", "requirements/")):
                archive.writestr("qf_solver-0.2.8.data/data/" + name, payload)
        archive.writestr("qf_solver-0.2.8.dist-info/METADATA", f"Name: qf-solver\nVersion: {version}\n")
        if extra:
            archive.writestr(extra, "unexpected")
    with tarfile.open(root / "qf_solver-0.2.8.tar.gz", "w:gz") as archive:
        payloads = selected | {"PKG-INFO": f"Name: qf-solver\nVersion: {version}\n".encode()}
        if extra:
            payloads[extra] = b"unexpected"
        for name, payload in payloads.items():
            info = tarfile.TarInfo("qf_solver-0.2.8/" + name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


@pytest.fixture
def selected() -> dict[str, bytes]:
    return {"src/qf_solver/__init__.py": b"# module\n", "README.md": b"Owner review\n",
            "qualification/benchmarks.json": b"{}", "examples/model.json": b"{}"}


def test_actual_archives_cover_every_selected_byte(tmp_path: Path, selected: dict[str, bytes]) -> None:
    _archives(tmp_path / "dist", selected)
    result = verify_archives(tmp_path / "dist", selected, "0.2.8")
    assert result["status"] == "PASS"
    assert result["selected_files"] == 4
    assert result["wheel_modules"] == 1
    assert all(scan["status"] == "PASS" for scan in result["scans"].values())


@pytest.mark.parametrize("extra", ["tests/private.py", "qualification/0_2_9/private.json", "src/private.py"])
def test_undeclared_archive_payload_is_not_accepted(tmp_path: Path, selected: dict[str, bytes], extra: str) -> None:
    _archives(tmp_path / "dist", selected, extra=extra)
    with pytest.raises(ValueError, match="content mismatch"):
        verify_archives(tmp_path / "dist", selected, "0.2.8")


def test_changed_installed_module_is_not_a_matching_archive(tmp_path: Path, selected: dict[str, bytes]) -> None:
    _archives(tmp_path / "dist", selected)
    selected["src/qf_solver/__init__.py"] = b"changed"
    with pytest.raises(ValueError, match="content mismatch"):
        verify_archives(tmp_path / "dist", selected, "0.2.8")


def test_nested_example_is_required_in_both_archives(tmp_path: Path, selected: dict[str, bytes]) -> None:
    selected["examples/vnv_026_g06/hex8_mesh_01.json"] = b'{"mesh": "fixture"}'
    _archives(tmp_path / "dist", selected)
    assert verify_archives(tmp_path / "dist", selected, "0.2.8")["status"] == "PASS"
    with zipfile.ZipFile(tmp_path / "dist/qf_solver-0.2.8-py3-none-any.whl", "w") as archive:
        archive.writestr("qf_solver/__init__.py", selected["src/qf_solver/__init__.py"])
        archive.writestr("qf_solver-0.2.8.dist-info/METADATA", "Version: 0.2.8\n")
    with pytest.raises(ValueError, match="examples/vnv_026_g06/hex8_mesh_01.json"):
        verify_archives(tmp_path / "dist", selected, "0.2.8")


def test_wrong_package_version_fails_closed(tmp_path: Path, selected: dict[str, bytes]) -> None:
    _archives(tmp_path / "dist", selected, version="9.9.9")
    with pytest.raises(ValueError, match="version mismatch"):
        verify_archives(tmp_path / "dist", selected, "0.2.8")


def test_scanner_is_not_weakened_for_selected_binaries(tmp_path: Path, selected: dict[str, bytes]) -> None:
    selected["README.md"] = ("C:/" + "Users/fixture/private/file").encode()
    _archives(tmp_path / "dist", selected)
    with pytest.raises(ValueError, match="content mismatch"):
        verify_archives(tmp_path / "dist", selected, "0.2.8")


@pytest.mark.parametrize("name", ["../escape.py", "/absolute.py", "src//duplicate.py"])
def test_archive_traversal_is_rejected(tmp_path: Path, name: str) -> None:
    path = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(name, b"payload")
    with pytest.raises(ValueError):
        archive_payloads(path, wheel=True)


def test_archive_case_aliases_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("A.py", b"payload")
        archive.writestr("a.py", b"payload")
    with pytest.raises(ValueError, match="colliding"):
        archive_payloads(path, wheel=True)


def test_source_archive_symlink_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo("package/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../escape"
        archive.addfile(info)
    with pytest.raises(ValueError, match="non-regular"):
        archive_payloads(path, wheel=False)


def test_probe_uses_safe_path_without_hiding_declared_dependency_sites(tmp_path: Path) -> None:
    command = installed_probe_command(tmp_path / "python", tmp_path / "probe.py", tmp_path / "mapping.json",
                                      "0.2.8", tmp_path / "result.json")
    if sys.version_info >= (3, 11):
        assert command[:3] == [str(tmp_path / "python"), "-P", str(tmp_path / "probe.py")]
    else:
        assert command[0:2] == [str(tmp_path / "python"), "-c"]
    assert "-I" not in command
    assert command[-2:] == ["--output", str(tmp_path / "result.json")]


def test_python310_safe_path_bootstrap_excludes_checkout_and_cwd_but_keeps_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = tmp_path / "checkout"
    scripts = checkout / "scripts"
    scripts.mkdir(parents=True)
    probe = scripts / "probe.py"
    probe.write_text(
        "import json, sys\n"
        "from pathlib import Path\n"
        "Path(sys.argv[sys.argv.index('--output') + 1]).write_text("
        "json.dumps({'sys_path': sys.path, 'cwd': str(Path.cwd()), 'probe': __file__}))\n",
        encoding="utf-8",
    )
    dependency_site = tmp_path / "declared-dependencies"
    dependency_site.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr("scripts.verify_public_package.sys.version_info", (3, 10))

    for index, cwd in enumerate((checkout, outside)):
        output = tmp_path / f"probe-{index}.json"
        command = installed_probe_command(Path(sys.executable), probe, tmp_path / "mapping.json",
                                          "0.2.8", output)
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(dependency_site)
        completed = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=True, check=False)

        assert completed.returncode == 0, completed.stderr
        observed = json.loads(output.read_text(encoding="utf-8"))
        paths = [Path(entry).resolve() for entry in observed["sys_path"] if entry]
        assert str(dependency_site.resolve()) in {str(path) for path in paths}
        assert all(checkout.resolve() not in (path, *path.parents) for path in paths)
        assert all(cwd.resolve() not in (path, *path.parents) for path in paths)


def test_audit_runner_rejects_unsupported_interpreters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.verify_public_package.sys.version_info", (3, 9))
    with pytest.raises(ValueError, match="Python 3.10"):
        installed_probe_command(tmp_path / "python", tmp_path / "probe.py", tmp_path / "mapping.json",
                                "0.2.8", tmp_path / "result.json")


@pytest.fixture
def frozen_fixture(tmp_path: Path) -> tuple[Path, Path]:
    for args in (["init"], ["config", "user.name", "Fixture"], ["config", "user.email", "fixture@example.org"],
                 ["config", "core.autocrlf", "false"]):
        git_run(args, cwd=tmp_path, check=True)
    payloads = {"README.md": b"Owner review\n", "src/model.py": b"# source\n",
                "pyproject.toml": b'[project]\nname="qf-solver"\nversion="0.2.8"\n'}
    payloads.update({name: b"# synthetic tooling\n" for name in REQUIRED_TOOLS})
    for name, payload in payloads.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    git_run(["add", "."], cwd=tmp_path, check=True)
    git_run(["commit", "-m", "source fixture"], cwd=tmp_path, check=True)
    source = git_run(["rev-parse", "HEAD"], cwd=tmp_path, check=True, text=True).stdout.strip()
    contract = {"status": "FROZEN_CANDIDATE_BUILD", "source_sha": source, "package_version": "0.2.8",
                "package_build_allowed": True, "publication_allowed": False,
                "structural_solves_allowed": False, "whole_repository_gate_waivers_allowed": False,
                "tool_bindings": {name: digest(payloads[name]) for name in REQUIRED_TOOLS},
                "selection": {"include_exact": ["README.md", "pyproject.toml"], "include_prefixes": ["src/"],
                              "exclude_exact": [], "forbid_prefixes": ["tests/"]}}
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    git_run(["add", "contract.json"], cwd=tmp_path, check=True)
    git_run(["commit", "-m", "prospective contract fixture"], cwd=tmp_path, check=True)
    return tmp_path, path


def test_only_committed_prospective_inputs_are_used(frozen_fixture: tuple[Path, Path]) -> None:
    root, path = frozen_fixture
    contract, payloads, mapping, execution = frozen_inputs(root, path)
    assert contract["source_sha"] != execution
    assert payloads["src/model.py"] == b"# source\n"
    assert len(mapping) == 3


@pytest.mark.parametrize("name", ["README.md", "scripts/verify_public_package.py", "untracked.json"])
def test_dirty_execution_is_rejected(frozen_fixture: tuple[Path, Path], name: str) -> None:
    root, path = frozen_fixture
    (root / name).write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="clean"):
        frozen_inputs(root, path)


def test_a_committed_post_freeze_source_change_is_rejected(frozen_fixture: tuple[Path, Path]) -> None:
    root, path = frozen_fixture
    (root / "README.md").write_text("changed", encoding="utf-8")
    git_run(["add", "README.md"], cwd=root, check=True)
    git_run(["commit", "-m", "changed source fixture"], cwd=root, check=True)
    with pytest.raises(ValueError, match="changed after"):
        frozen_inputs(root, path)


@pytest.mark.parametrize("field,value", [("status", "PREPARATION_ONLY"), ("publication_allowed", True),
                                        ("whole_repository_gate_waivers_allowed", True), ("structural_solves_allowed", True)])
def test_build_does_not_broaden_its_authority(frozen_fixture: tuple[Path, Path], field: str, value: object) -> None:
    root, path = frozen_fixture
    contract = json.loads(path.read_text())
    contract[field] = value
    path.write_text(json.dumps(contract))
    git_run(["add", "contract.json"], cwd=root, check=True)
    git_run(["commit", "-m", "invalid contract fixture"], cwd=root, check=True)
    with pytest.raises(ValueError, match="does not authorize"):
        frozen_inputs(root, path)


def test_incomplete_tool_binding_is_rejected(frozen_fixture: tuple[Path, Path]) -> None:
    root, path = frozen_fixture
    contract = json.loads(path.read_text())
    del contract["tool_bindings"]["scripts/probe_installed_package.py"]
    path.write_text(json.dumps(contract))
    git_run(["add", "contract.json"], cwd=root, check=True)
    git_run(["commit", "-m", "missing binding fixture"], cwd=root, check=True)
    with pytest.raises(ValueError, match="Every build"):
        frozen_inputs(root, path)
