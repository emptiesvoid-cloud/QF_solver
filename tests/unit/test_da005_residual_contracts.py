from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.dynamic import NewmarkDynamicSolver
from solveur.core.analyses.harmonic import HarmonicResponseSolver
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.solvers.linear import (
    LinearSystemSolver,
    relative_residual_ratio,
    validate_residual_failure_tolerance,
)
from solveur.core.solvers.static import LinearStaticSolver


def _model(analysis_type: str, tolerance_name: str, tolerance: object) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3, "density": 1.0}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis={
            "type": analysis_type,
            "parameters": {tolerance_name: tolerance, "dt": 0.01, "steps": 1, "frequencies_hz": [1.0]},
        },
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), 0.0, -1.0, True, "bad"])
def test_residual_failure_tolerances_must_be_finite_positive_scalars(value: object) -> None:
    with pytest.raises(InputValidationError, match="finite positive number"):
        validate_residual_failure_tolerance({"residual_failure_tolerance": value})


def test_relative_linear_residual_is_not_hidden_by_unit_floor() -> None:
    matrix = csr_matrix([[1.0]])
    rhs = np.asarray([1.0e-12])
    solution = np.asarray([0.0])

    residual, relative = LinearSystemSolver._raw_residual_metrics(matrix, rhs, solution)

    assert residual == pytest.approx(1.0e-12)
    assert relative == pytest.approx(1.0)
    with pytest.raises(NumericalConvergenceError, match=r"relative=1.000000e\+00"):
        LinearSystemSolver._validated_residual_metrics(matrix, rhs, solution, "test", {})


def test_relative_residual_defines_exact_zero_reference() -> None:
    assert relative_residual_ratio(0.0, 0.0) == 0.0
    assert relative_residual_ratio(1.0, 0.0) == float("inf")


@pytest.mark.parametrize(
    ("analysis_type", "tolerance_name", "solver_type"),
    [
        ("linear_static", "residual_failure_tolerance", LinearStaticSolver),
        ("harmonic_response", "harmonic_residual_failure_tolerance", HarmonicResponseSolver),
        ("transient_dynamic", "dynamic_residual_failure_tolerance", NewmarkDynamicSolver),
    ],
)
def test_analysis_routes_reject_nonfinite_residual_limits_before_mesh_work(
    analysis_type: str,
    tolerance_name: str,
    solver_type: type[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _model(analysis_type, tolerance_name, float("nan"))
    solver = solver_type()

    def fail_if_mesh_validation_runs(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Residual input validation must happen before mesh validation.")

    monkeypatch.setattr(solver.validator, "validate", fail_if_mesh_validation_runs)
    with pytest.raises(InputValidationError, match=tolerance_name):
        solver.solve(model)
