import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def _model(*, increments: int = 10) -> FiniteElementModel:
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip = np.flatnonzero(np.isclose(nodes[:, 0], 2.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UZ", "value": -1.0 / len(tip)} for node in tip],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": increments},
        },
    )


def test_public_geometric_nonlinear_tet4_solve() -> None:
    result = solve_model(_model(), enforce_policy=False)
    assert result.status == "success"
    assert result.analysis == "geometric_nonlinear_static"
    assert result.solver["load_increments"] == 10
    assert result.solver["minimum_det_f"] > 0.99
    assert len(result.element_results) == result.element_count
    assert result.to_dict()["displacements"]


def test_public_geometric_nonlinear_requires_six_increments() -> None:
    with pytest.raises(ValueError, match="at least 6"):
        solve_model(_model(increments=5), enforce_policy=False)


def test_public_geometric_nonlinear_rejects_distributed_loads() -> None:
    model = _model()
    model.distributed_loads = [object()]
    with pytest.raises(InputValidationError, match="nodal dead loads only"):
        solve_model(model, enforce_policy=False)
