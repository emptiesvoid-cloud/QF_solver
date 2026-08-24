from __future__ import annotations

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel


def _coords() -> np.ndarray:
    corners = np.asarray(
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
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])


def _model(analysis: str | dict[str, object], *, nonlinear: bool = False) -> FiniteElementModel:
    coords = _coords()
    fixed_nodes = (0, 3, 4, 7, 9, 10, 15, 17)
    material = (
        {
            "type": "von_mises_elastoplastic_3d",
            "E": 1000.0,
            "nu": 0.3,
            "density": 1.0,
            "yield_stress": 0.02,
            "hardening_modulus": 10.0,
        }
        if nonlinear
        else {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}
    )
    return FiniteElementModel.from_raw(
        nodes=coords.tolist(),
        elements=[{"type": "HEX20", "nodes": list(range(20)), "material": "solid"}],
        materials={"solid": material},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=[{"node": 1, "dof": "UX", "value": 1.0 if not nonlinear else 5.0}],
        analysis=analysis,
    )


def test_hex20_uses_common_static_modal_newmark_and_harmonic_paths() -> None:
    cases = (
        "linear_static",
        {"type": "modal", "modes": 2},
        {"type": "transient_dynamic", "time_step": 0.01, "end_time": 0.02, "beta": 0.25, "gamma": 0.5},
        {"type": "harmonic_response", "frequencies": [1.0]},
    )
    for analysis in cases:
        result = solve_model(_model(analysis))
        assert result.status == "PASS"


def test_hex20_static_postprocessing_recovers_quadratic_gauss_field() -> None:
    result = solve_model(_model("linear_static"))
    element_result = result.element_results[0]
    assert element_result["type"] == "HEX20"
    assert len(element_result["integration_points"]) == 27
    assert len(element_result["nodal_results"]) == 20


def test_hex20_j2_uses_common_newton_raphson_path() -> None:
    analysis = {"type": "nonlinear_static", "method": "newton_raphson", "load_path": [0.25, 0.5, 0.75, 1.0]}
    data = solve_model(_model(analysis, nonlinear=True)).to_dict()
    assert data["status"] == "PASS"
    assert data["analysis"] == "nonlinear_static"
    assert len(data["solver"]["steps"]) == 4
    assert all(step["state_committed"] for step in data["solver"]["steps"])
    assert len(data["material_states"][0]["integration_points"]) == 27
    assert data["element_results"][0]["type"] == "HEX20"
