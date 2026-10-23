"""Hash-bound safety registration for the isolated E01 numerical tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REVIEWED_NUMERICAL_TESTS = {
    "tests/unit/test_wp_e01m_hencky_material_point.py": (
        "cdd2651e9427c0e64284a75671d83d4f14cdd916a979759be0422f44dde84bfc",
        "NumPy-only experimental Hencky material-point objectivity and energy checks, including local TET4/HEX8 force algebra; no global assembly, public solver, Newton, native FEM, Gmsh initialization, worker, subprocess, network, or filesystem write",
    ),
    "tests/unit/test_wp_e01q_hencky_tangent.py": (
        "a99bcc6ea32bff3e2a669d2923380033f23e587aab95f612ab4047f98b7d7b50",
        "isolated Hencky material-point tangent actions with Decimal diagonal references, centered PK1 differences, covariance, Hessian symmetry, and input refusals; no FEM assembly, public solver, Newton, native FEM, Gmsh initialization, worker, subprocess, network, or filesystem write",
    ),
}


def _repository_relative_path(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
    except ValueError:
        return None


@pytest.hookimpl(tryfirst=True)
def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> None:
    """Reject changed registered modules before pytest imports their test code."""
    relative_path = _repository_relative_path(file_path)
    binding = REVIEWED_NUMERICAL_TESTS.get(relative_path or "")
    if binding is None:
        return None

    expected_sha256, _rationale = binding
    actual_sha256 = hashlib.sha256(file_path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256:
        raise pytest.UsageError(
            f"E01 numerical test hash mismatch for {relative_path}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    return None


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply the reviewed numerical-unit classification to exact registered files."""
    for item in items:
        relative_path = _repository_relative_path(Path(str(item.path)))
        if relative_path in REVIEWED_NUMERICAL_TESTS:
            item.add_marker(pytest.mark.numerical_unit)
