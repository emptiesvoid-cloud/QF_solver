from __future__ import annotations

import pytest

import solveur.core.analyses.buckling as buckling_analysis
import solveur.core.analyses.geometric_nonlinear as geometric_analysis
from solveur.api import solve_model
from solveur.core.analyses.buckling import LinearBucklingSolver
from solveur.core.analyses.geometric_nonlinear import GeometricNonlinearStaticSolver
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel


def _model(analysis: str, *, with_spring: bool) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": -1.0}],
        springs=(
            [{"node_a": 1, "dofs": ["UX"], "stiffness": 10.0}]
            if with_spring
            else []
        ),
        analysis={"type": analysis, "method": "newton_raphson" if analysis == "geometric_nonlinear_static" else "eigsh"},
    )


def _fail_if_called(*_args: object, **_kwargs: object) -> None:
    pytest.fail("A spring-rejected route continued to mesh validation or assembly.")


def test_geometric_nonlinear_rejects_springs_before_validation_or_assembly(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _model("geometric_nonlinear_static", with_spring=True)
    monkeypatch.setattr(geometric_analysis.MeshValidator, "validate", _fail_if_called)
    monkeypatch.setattr(geometric_analysis, "build_total_lagrangian_assembly", _fail_if_called)

    with pytest.raises(InputValidationError, match="does not support discrete springs"):
        solve_model(model, enforce_policy=False)


def test_linear_buckling_rejects_springs_before_validation_or_assembly(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _model("linear_buckling", with_spring=True)
    monkeypatch.setattr(buckling_analysis.MeshValidator, "validate", _fail_if_called)
    monkeypatch.setattr(buckling_analysis, "build_total_lagrangian_assembly", _fail_if_called)

    with pytest.raises(InputValidationError, match="does not support discrete springs"):
        solve_model(model, enforce_policy=False)


def test_spring_free_models_remain_inside_both_existing_scopes() -> None:
    GeometricNonlinearStaticSolver._validate_scope(_model("geometric_nonlinear_static", with_spring=False))
    LinearBucklingSolver._validate_scope(_model("linear_buckling", with_spring=False))
