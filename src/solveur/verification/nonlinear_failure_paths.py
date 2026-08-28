"""Failure cases for continuation and buckling paths."""

from __future__ import annotations

from solveur.api import solve_model
from solveur.core.buckling import LinearBucklingSolver
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_contracts import NonlinearFailureReason


def _run_arc_length_failure_case() -> dict[str, object]:
    """Verify that a continuation step cap is reported, not silently truncated."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "rubber"}],
        materials={"rubber": {"type": "nonlinear_isotropic_3d", "E": 1000.0, "nu": 0.25, "hardening": 1.0e6}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 10.0}],
        analysis={
            "type": "nonlinear_static",
            "method": "arc_length",
            "load_steps": 5,
            "max_iterations": 50,
            "tolerance": 1.0e-9,
            "max_arc_steps": 1,
            "target_load_factor": 1.0,
        },
    )
    try:
        solve_model(model, enforce_policy=False)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return {
            "name": "arc_length_failure",
            "passed": payload.get("reason") == NonlinearFailureReason.ARC_LENGTH_FAILURE.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": payload.get("reason"),
            "diagnostics": {"solver": "arc_length", **dict(payload.get("diagnostics", {}))},
        }
    return {
        "name": "arc_length_failure",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {"solver": "arc_length"},
    }


def _run_buckling_failure_case() -> dict[str, object]:
    """Verify that an unbracketed tensile preload is classified explicitly."""

    model = FiniteElementModel.from_raw(
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        # Tension keeps the constrained tangent positive definite.  The
        # sparse generalized path therefore declines the problem and the
        # bounded bracket must report BUCKLING_FAILURE.
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis={
            "type": "linear_buckling",
            "method": "eigsh",
            "preload_factor": 1.0,
            "load_increments": 4,
            "initial_factor": 1.0,
            "maximum_factor": 2.0,
        },
    )
    try:
        LinearBucklingSolver().solve(model)
    except NumericalConvergenceError as error:
        payload = error.to_dict()
        return {
            "name": "buckling_failure",
            "passed": payload.get("reason") == NonlinearFailureReason.BUCKLING_FAILURE.value,
            "converged": bool(payload.get("converged", True)),
            "failure_reason": payload.get("reason"),
            "diagnostics": {"solver": "linear_buckling", **dict(payload.get("diagnostics", {}))},
        }
    return {
        "name": "buckling_failure",
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {"solver": "linear_buckling"},
    }
