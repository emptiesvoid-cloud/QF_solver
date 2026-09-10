"""Fast regression guards for the 0.2.8 release-surface corrections."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _without_h5py_environment(tmp_path: Path) -> dict[str, str]:
    (tmp_path / "h5py.py").write_text("raise ImportError('h5py blocked by release-surface test')\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(ROOT / "src")))
    return environment


def test_base_import_does_not_require_h5py(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "-c", "import qf_solver; print(qf_solver.__version__)"],
        cwd=tmp_path,
        env=_without_h5py_environment(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout.strip() == "0.2.8"


def test_hdf5_api_fails_typed_and_closed_without_h5py(tmp_path: Path) -> None:
    script = """
from qf_solver import InfrastructureError, load_mixed_results_hdf5
try:
    load_mixed_results_hdf5('unused.h5')
except InfrastructureError as exc:
    assert "qf-solver[hdf5]" in str(exc)
else:
    raise AssertionError("missing h5py was accepted")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=_without_h5py_environment(tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_hdf5_api_smoke_with_optional_dependency() -> None:
    pytest.importorskip("h5py")
    from qf_solver import load_mixed_results_hdf5

    path = ROOT / "qualification/0_2_8/wp13_06_scalable_mixed_post/mixed_result_main.h5"
    result = load_mixed_results_hdf5(path, families=("WEDGE6",), fields=("von_mises",), region_id=0)
    assert result["schema_version"] == "1.0"
    assert set(result["element_blocks"]) == {"WEDGE6"}


def test_version_registry_and_public_docs_are_aligned() -> None:
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
        import tomli as tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    from solveur.version import __version__

    assert project["version"] == __version__ == "0.2.8"
    assert project["optional-dependencies"]["hdf5"] == ["h5py>=3.10"]
    assert 'version: "0.2.8"' in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    registry = json.loads((ROOT / "qualification/0_2_8/consolidated_registry.json").read_text(encoding="utf-8"))
    assert registry["combination_registry"]["state_counts"] == {
        "QUALIFIED_BOUNDED": 32,
        "EXPERIMENTAL": 14,
        "NOT_QUALIFIED": 0,
    }
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "qualification/0_2_8/consolidated_registry.json" in readme
    assert "Mixed distributed PETSc/MPI" in readme and "`NOT_VALIDATED`" in readme
    assert "WEDGE6 static | `QUALIFIED_BOUNDED`" in readme
