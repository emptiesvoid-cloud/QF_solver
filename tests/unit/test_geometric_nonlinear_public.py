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


def test_public_geometric_nonlinear_hex8_is_supported() -> None:
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX8", "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded)} for node in loaded],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": 6},
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "success"
    assert result.solver["scope"] == "hex8-total-lagrangian-structural-v1"
    assert result.solver["minimum_det_f"] > 0.99


def test_public_geometric_nonlinear_adaptive_load_steps_are_opt_in() -> None:
    model = _model(increments=6)
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 0.5,
            "min_load_increment": 0.05,
            "max_load_increment": 0.5,
            "max_cutbacks": 4,
        }
    )

    result = solve_model(model, enforce_policy=False)
    data = result.to_dict()

    assert data["solver"]["adaptive_load_steps"] is True
    assert data["solver"]["rejected_increments"] == 0
    assert data["solver"]["increments"][-1]["load_factor"] == pytest.approx(1.0)


@pytest.mark.parametrize("family", ["TET10", "HEX20"])
def test_public_geometric_nonlinear_high_order_families_use_common_tl_assembly(family: str) -> None:
    if family == "TET10":
        corners = np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
        nodes = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    else:
        corners = np.asarray(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
             [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]]
        )
        edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7),
                 (4, 5), (4, 7), (5, 6), (6, 7))
        nodes = np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    model = FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": family, "nodes": list(range(len(nodes))), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0e-4 / len(loaded)} for node in loaded],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": 6, "tolerance": 1.0e-8},
        },
    )

    result = solve_model(model, enforce_policy=False)

    assert result.status == "success"
    assert result.solver["scope"].startswith(family.lower())
    assert result.solver["minimum_det_f"] > 0.99
    assert result.solver["strain_energy"] > 0.0


def test_public_geometric_nonlinear_rejects_distributed_loads() -> None:
    model = _model()
    model.distributed_loads = [object()]
    with pytest.raises(InputValidationError, match="nodal dead loads only"):
        solve_model(model, enforce_policy=False)
