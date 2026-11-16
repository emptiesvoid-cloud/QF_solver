"""One bounded post-processing and matrix-solve study per registered J8 nodeid."""

from __future__ import annotations

import pytest

from research.j8_hex8.diagnostics import run_case
from research.j8_hex8.geometry_contrast import run_geometry_contrast


def _diagnostic_assertions(case_key: str, nodeid: str) -> None:
    result = run_case(case_key, nodeid)
    assert result["execution_status"] == "COMPLETED"
    assert result["failed_methods"] == []
    assert result["methods"]
    assert all(method["status"] == "COMPLETED" for method in result["methods"].values())


def test_j8_regular_nu04999_recalculation_and_methods(request: pytest.FixtureRequest) -> None:
    _diagnostic_assertions("regular", request.node.nodeid)


def test_j8_near_degenerate_nu0495_recalculation_and_methods(request: pytest.FixtureRequest) -> None:
    _diagnostic_assertions("near_degenerate", request.node.nodeid)


def test_j8_geometry_only_regular_nu0495_nx4_contrast(request: pytest.FixtureRequest) -> None:
    result = run_geometry_contrast(request.node.nodeid)
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert all(result["structural_checks"].values())
