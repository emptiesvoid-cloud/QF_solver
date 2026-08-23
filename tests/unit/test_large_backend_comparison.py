from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from scripts.compare_large_backends import _relative_error, _validate_backends, compare_large_backends
from solveur.large.generator import generate_tet4_block


def test_backend_comparison_matches_scipy_and_matrix_free(tmp_path: Path) -> None:
    model_path = tmp_path / "block.h5"
    output = tmp_path / "comparison"
    generate_tet4_block(model_path, nx=1, ny=1, nz=1)

    summary = compare_large_backends(model_path, output, backends=("scipy", "matrix_free"))

    assert summary["status"] == "PASS"
    assert summary["backends_completed"] == ["scipy", "matrix_free"]
    assert summary["comparisons"][0]["status"] == "PASS"
    assert summary["comparisons"][0]["relative_displacement_error"] < 1.0e-7
    assert json.loads((output / "backend_comparison.json").read_text(encoding="utf-8"))["status"] == "PASS"
    assert "matrix_free" in (output / "backend_comparison.md").read_text(encoding="utf-8")


def test_backend_comparison_records_unavailable_optional_backend(tmp_path: Path) -> None:
    model_path = tmp_path / "block.h5"
    output = tmp_path / "comparison"
    generate_tet4_block(model_path, nx=1, ny=1, nz=1)

    summary = compare_large_backends(model_path, output, backends=("scipy", "petsc"))

    assert summary["status"] in {"PARTIAL", "PASS"}
    if any(run["status"] == "SKIP" for run in summary["runs"]):
        assert summary["status"] == "PARTIAL"


def test_backend_comparison_input_contracts() -> None:
    with pytest.raises(ValueError, match="only scipy"):
        _validate_backends(("dense",))
    with pytest.raises(ValueError, match="unique"):
        _validate_backends(("scipy", "SCIPY"))
    with pytest.raises(ValueError, match="different shapes"):
        _relative_error(np.zeros(2), np.zeros(3))
