from __future__ import annotations

import numpy as np
import pytest

from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.geometric_nonlinear import GeometricNonlinearStaticSolver, _line_search, _newton_dead_load
from solveur.core.model import FiniteElementModel


def _valid_model(**kwargs) -> FiniteElementModel:
    analysis = {"type": "geometric_nonlinear_static", "method": "newton_raphson", "parameters": kwargs}
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ"]}, {"node": 2, "dofs": ["UX", "UY", "UZ"]}, {"node": 3, "dofs": ["UX", "UY", "UZ"]}],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis=analysis,
    )


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"elements": [{"type": "BEAM2", "nodes": [0, 1], "material": "solid"}]}, "TET4"),
        ({
            "elements": [
                {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "a"},
                {"type": "TET4", "nodes": [0, 1, 2, 3], "material": "b"},
            ],
            "materials": {
                "a": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3},
                "b": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3},
            },
        }, "one homogeneous"),
        ({"materials": {"solid": {"type": "shell_isotropic", "E": 1.0, "nu": 0.3}}}, "isotropic_3d"),
    ],
)
def test_geometric_scope_rejects_unsupported_models(changes, message: str) -> None:
    data = {"elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}], "materials": {"solid": {"type": "isotropic_3d", "E": 1.0, "nu": 0.3}}}
    data.update(changes)
    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=data["elements"], materials=data["materials"], analysis="geometric_nonlinear_static",
    )
    with pytest.raises(InputValidationError, match=message):
        GeometricNonlinearStaticSolver._validate_scope(model)


def test_geometric_scope_rejects_distributed_loads() -> None:
    model = _valid_model()
    model.distributed_loads = [object()]
    with pytest.raises(InputValidationError, match="nodal dead loads"):
        GeometricNonlinearStaticSolver._validate_scope(model)


@pytest.mark.parametrize("parameters, message", [
    ({"tolerance": 0.0}, "tolerance"),
    ({"max_iterations": 1}, "max_iterations"),
])
def test_geometric_solver_rejects_invalid_newton_controls(parameters, message: str) -> None:
    with pytest.raises(InputValidationError, match=message):
        GeometricNonlinearStaticSolver().solve(_valid_model(**parameters))


def test_geometric_newton_requires_constraints() -> None:
    assembly = type("Assembly", (), {"ndof": 2})()
    with pytest.raises(MeshValidationError, match="constrained dofs"):
        _newton_dead_load(assembly, np.zeros(2), np.asarray([], dtype=int), increments=1, tolerance=1.0e-6, max_iterations=2)


def test_geometric_line_search_reports_failed_reduction() -> None:
    class Assembly:
        def assemble(self, trial, tangent_required=False):
            return np.asarray([0.0]), None

    with pytest.raises(NumericalConvergenceError, match="line search"):
        _line_search(Assembly(), np.zeros(1), np.asarray([0]), np.ones(1), np.ones(1), 1.0)

    class InvalidAssembly:
        def assemble(self, trial, tangent_required=False):
            raise ValueError("inverted trial")

    with pytest.raises(NumericalConvergenceError, match="line search"):
        _line_search(InvalidAssembly(), np.zeros(1), np.asarray([0]), np.ones(1), np.ones(1), 1.0)
