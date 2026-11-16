"""One bounded post-processing and matrix-solve study per registered J8 nodeid."""

from __future__ import annotations

import pytest

from research.j8_hex8.diagnostics import run_case
from research.j8_hex8.geometry_contrast import run_geometry_contrast

EXPECTED_MATRIX_METHODS = {
    "numpy_direct",
    "scipy_positive_definite",
    "symmetric_diagonal_scaling",
    "scalar_equation_scale_1e-6",
    "scalar_equation_scale_1e6",
    "physical_length_unit_m_to_mm",
    "iterative_refinement",
}


def _diagnostic_assertions(case_key: str, nodeid: str) -> None:
    result = run_case(case_key, nodeid)
    assert result["execution_status"] == "COMPLETED"
    assert result["failed_methods"] == []
    assert result["methods"]
    assert all(method["status"] == "COMPLETED" for method in result["methods"].values())
    expected_methods = set(EXPECTED_MATRIX_METHODS)
    if case_key == "near_degenerate":
        expected_methods.add("mpmath_80_decimal_digits")
    assert set(result["methods"]) == expected_methods


def test_j8_regular_nu04999_recalculation_and_methods(request: pytest.FixtureRequest) -> None:
    _diagnostic_assertions("regular", request.node.nodeid)


def test_j8_near_degenerate_nu0495_recalculation_and_methods(request: pytest.FixtureRequest) -> None:
    _diagnostic_assertions("near_degenerate", request.node.nodeid)


def test_j8_geometry_only_regular_nu0495_nx4_contrast(request: pytest.FixtureRequest) -> None:
    result = run_geometry_contrast(request.node.nodeid)
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert all(result["structural_checks"].values())
