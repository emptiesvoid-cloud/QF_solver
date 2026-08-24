from __future__ import annotations

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel


def _hex8_model(analysis: str | dict[str, object]) -> FiniteElementModel:
    nodes = np.asarray(
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
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX8", "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 210.0e9, "nu": 0.3, "density": 7800.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in (0, 3, 4, 7)],
        loads=[{"node": 1, "dof": "UX", "value": 1.0}],
        analysis=analysis,
    )


def test_hex8_uses_the_common_static_modal_dynamic_and_harmonic_paths() -> None:
    cases = (
        "linear_static",
        {"type": "modal", "modes": 2},
        {"type": "transient_dynamic", "time_step": 0.01, "end_time": 0.02, "beta": 0.25, "gamma": 0.5},
        {"type": "harmonic_response", "frequencies": [1.0]},
    )
    for analysis in cases:
        result = solve_model(_hex8_model(analysis))
        assert result.status == "PASS"


def test_hex8_static_postprocessing_contains_all_gauss_points() -> None:
    result = solve_model(_hex8_model("linear_static"))
    element_result = result.element_results[0]
    assert element_result["type"] == "HEX8"
    assert len(element_result["integration_points"]) == 8
    assert len(element_result["nodal_results"]) == 8
